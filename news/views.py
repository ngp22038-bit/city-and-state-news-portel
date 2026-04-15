from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F, Count, Q, ExpressionWrapper, FloatField, Sum
from django.http import JsonResponse
from django.core.cache import cache
from core.models import User
from .models import Article, FakeNewsReport, AdPayment, Reaction, Comment, Bookmark, ReadingHistory
import urllib.request, json, urllib.parse
from django.conf import settings
import razorpay
import traceback
from django.views.decorators.csrf import csrf_exempt
def owner_dashboard(request):
    cities = Article.objects.values_list('city',  flat=True).distinct().exclude(city__isnull=True).exclude(city='')
    states = Article.objects.values_list('state', flat=True).distinct().exclude(state__isnull=True).exclude(state='')
    return render(request, 'owner_dashboard.html', {'cities': cities, 'states': states})

def user_dashboard(request):
    latest_news = Article.objects.order_by('-created_at')[:6]
    trending_news = Article.objects.annotate(
        trending_score=ExpressionWrapper(
            F('views_count') * 0.5 +
            Count('reaction', filter=Q(reaction__reaction_type='Like')) * 2.0 +
            Count('comment') * 3.0,
            output_field=FloatField()
        )
    ).order_by('-trending_score')[:8]

    local_news = []
    state_news = []
    recommended_news = []
    saved_articles = []
    reading_history = []
    saved_count = 0
    comments_count = 0
    articles_read_count = 0
    bookmarked_ids = set()

    if request.user.is_authenticated:
        # City news
        city_q = Q()
        if request.user.preferred_city:
            city_q |= Q(city__icontains=request.user.preferred_city)
        elif request.user.city:
            city_q |= Q(city__icontains=request.user.city)
        if city_q:
            local_news = Article.objects.filter(city_q).order_by('-created_at')[:4]

        # State news
        state_q = Q()
        if request.user.preferred_state:
            state_q |= Q(state__icontains=request.user.preferred_state)
        elif request.user.state:
            state_q |= Q(state__icontains=request.user.state)
        if state_q:
            state_news = Article.objects.filter(state_q).order_by('-created_at')[:4]

        # Recommendations based on reading history categories
        read_categories = ReadingHistory.objects.filter(user=request.user).values_list('article__category', flat=True)
        if read_categories:
            recommended_news = Article.objects.filter(category__in=read_categories).exclude(
                id__in=ReadingHistory.objects.filter(user=request.user).values_list('article_id', flat=True)
            ).order_by('-views_count')[:4]
        if not recommended_news:
            recommended_news = Article.objects.filter(views_count__gte=1).order_by('-views_count')[:4]

        saved_articles = Bookmark.objects.filter(user=request.user).select_related('article').order_by('-created_at')[:5]
        saved_count = Bookmark.objects.filter(user=request.user).count()
        comments_count = Comment.objects.filter(user=request.user).count()
        reading_history = ReadingHistory.objects.filter(user=request.user).select_related('article')[:5]
        articles_read_count = ReadingHistory.objects.filter(user=request.user).count()
        bookmarked_ids = set(Bookmark.objects.filter(user=request.user).values_list('article_id', flat=True))

    categories = Article.objects.values_list('category', flat=True).distinct().exclude(category__isnull=True)
    cities     = Article.objects.values_list('city',     flat=True).distinct().exclude(city__isnull=True).exclude(city='')
    states     = Article.objects.values_list('state',    flat=True).distinct().exclude(state__isnull=True).exclude(state='')

    context = {
        'latest_news': latest_news,
        'trending_news': trending_news,
        'local_news': local_news,
        'state_news': state_news,
        'recommended_news': recommended_news,
        'saved_articles': saved_articles,
        'reading_history': reading_history,
        'saved_count': saved_count,
        'comments_count': comments_count,
        'articles_read_count': articles_read_count,
        'bookmarked_ids': bookmarked_ids,
        'categories': categories,
        'cities':     cities,
        'states':     states,
    }
    return render(request, 'user_dashboard.html', context)


def reader_search(request):
    """AJAX endpoint for search + filter in reader panel."""
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    date_filter = request.GET.get('date', '')
    city = request.GET.get('city', '')

    from django.utils import timezone
    import datetime

    articles = Article.objects.all()

    if q:
        articles = articles.filter(Q(title__icontains=q) | Q(content__icontains=q))
    if category:
        articles = articles.filter(category__icontains=category)
    if city:
        articles = articles.filter(Q(city__icontains=city) | Q(state__icontains=city))
    if date_filter == 'today':
        articles = articles.filter(created_at__date=timezone.now().date())
    elif date_filter == 'week':
        articles = articles.filter(created_at__gte=timezone.now() - datetime.timedelta(days=7))
    elif date_filter == 'month':
        articles = articles.filter(created_at__gte=timezone.now() - datetime.timedelta(days=30))

    articles = articles.order_by('-created_at')[:12]

    data = []
    for a in articles:
        data.append({
            'id': a.id,
            'title': a.title,
            'category': a.category or 'General',
            'city': a.city or '',
            'state': a.state or '',
            'views_count': a.views_count,
            'created_at': a.created_at.strftime('%b %d, %Y'),
            'excerpt': a.content[:120] + '...' if len(a.content) > 120 else a.content,
        })
    return JsonResponse({'articles': data})

# ── Live News Page ─────────────────────────────────────────────────────────────
GNEWS_API_KEY = 'YOUR_GNEWS_API_KEY'   # replace with real key from gnews.io
FALLBACK_IMG  = 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=600'

def _fetch_gnews(query='India', category='', max_results=12):
    """Fetch from GNews API with 5-min cache."""
    cache_key = f'gnews_{query}_{category}_{max_results}'
    cached    = cache.get(cache_key)
    if cached:
        return cached

    try:
        params = {
            'q':        query,
            'lang':     'en',
            'country':  'in',
            'max':      max_results,
            'apikey':   GNEWS_API_KEY,
        }
        if category:
            params['topic'] = category
        url  = 'https://gnews.io/api/v4/search?' + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=6) as r:
            data = json.loads(r.read())
        articles = data.get('articles', [])
        cache.set(cache_key, articles, 300)   # cache 5 minutes
        return articles
    except Exception:
        return []


def live_news(request):
    category = request.GET.get('category', '')
    city     = request.GET.get('city', 'India')
    query    = city if city else 'India'

    external = _fetch_gnews(query=query, category=category, max_results=12)

    # Also pull internal DB articles
    internal_qs = Article.objects.prefetch_related('media').order_by('-created_at')
    if city and city != 'India':
        internal_qs = internal_qs.filter(Q(city__icontains=city) | Q(state__icontains=city))
    if category:
        internal_qs = internal_qs.filter(category__icontains=category)
    internal = list(internal_qs[:6])

    cities  = Article.objects.values_list('city',  flat=True).distinct().exclude(city__isnull=True).exclude(city='')
    states  = Article.objects.values_list('state', flat=True).distinct().exclude(state__isnull=True).exclude(state='')

    categories = ['business', 'sports', 'technology', 'health', 'politics', 'entertainment']

    context = {
        'external':    external,
        'internal':    internal,
        'cities':      cities,
        'states':      states,
        'categories':  categories,
        'active_cat':  category,
        'active_city': city,
        'fallback_img': FALLBACK_IMG,
    }
    return render(request, 'live_news.html', context)


def live_news_api(request):
    """AJAX endpoint — returns fresh external news as JSON."""
    category = request.GET.get('category', '')
    city     = request.GET.get('city', 'India')
    articles = _fetch_gnews(query=city or 'India', category=category, max_results=12)
    return JsonResponse({'articles': articles, 'fallback': FALLBACK_IMG})


def add_article(request):
    from .models import Article
    default_cats = ['Politics', 'Sports', 'Technology', 'Business', 'Entertainment', 'Education', 'Health', 'Crime', 'Weather', 'Jobs', 'Events']
    db_cats = list(Article.objects.values_list('category', flat=True).distinct().exclude(category__isnull=True).exclude(category=''))
    db_cats_lower = [c.lower() for c in db_cats]
    for d in default_cats:
        if d.lower() not in db_cats_lower:
            db_cats.append(d)
    categories = db_cats
    cities = list(Article.objects.values_list('city', flat=True).distinct().exclude(city__isnull=True).exclude(city=''))
    states = list(Article.objects.values_list('state', flat=True).distinct().exclude(state__isnull=True).exclude(state=''))
    default_states = ['Gujarat', 'Maharashtra', 'Rajasthan', 'Delhi', 'Karnataka', 'Tamil Nadu', 'Uttar Pradesh', 'West Bengal', 'Punjab', 'Madhya Pradesh']
    states_lower = [s.lower() for s in states]
    for s in default_states:
        if s.lower() not in states_lower:
            states.append(s)

    if request.method == 'POST':
        title       = request.POST.get('title', '').strip()
        content     = request.POST.get('content', '').strip()
        category    = request.POST.get('category', '').strip()
        city        = request.POST.get('city', '').strip()
        state       = request.POST.get('state', '').strip()

        if title and content:
            author = request.user if request.user.is_authenticated else None
            if author:
                action = request.POST.get('action', 'draft')
                Article.objects.create(
                    title=title,
                    content=content,
                    category=category or None,
                    city=city or None,
                    state=state or None,
                    author=author,
                    is_published=(action == 'publish'),
                )
                if action == 'publish':
                    messages.success(request, 'Article published successfully.')
                else:
                    messages.success(request, 'Article saved as draft.')
                return redirect('manage_articles')
            else:
                messages.error(request, 'You must be logged in to publish an article.')
        else:
            messages.error(request, 'Title and content are required.')

    return render(request, 'add_article.html', {'categories': categories, 'cities': cities, 'states': states})

from .forms import PaymentForm

def add_payment(request):
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            # Process the payment logic here
            pass # Currently just displaying the form based on user request
    else:
        form = PaymentForm()
    
    return render(request, 'add_payment.html', {'form': form})

@csrf_exempt
def create_razorpay_order(request):
    """Creates a Razorpay Order and returns the order_id for checkout popup"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            amount = float(data.get('amount', 0))
            if amount <= 0:
                return JsonResponse({'error': 'Invalid amount'}, status=400)

            # Amount in paise (multiply by 100)
            amount_in_paise = int(amount * 100)

            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            payment_data = {
                "amount": amount_in_paise,
                "currency": "INR",
                "receipt": f"rcpt_{request.user.id if request.user.is_authenticated else 'guest'}",
            }
            order = client.order.create(data=payment_data)
            return JsonResponse({
                'order_id': order['id'],
                'amount':   amount_in_paise,
                'key':      settings.RAZORPAY_KEY_ID,
            })
        except Exception as e:
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request'}, status=400)


def payment_success(request):
    """Verify Razorpay signature and save subscription (AJAX call)."""
    if request.method == 'POST':
        try:
            data        = json.loads(request.body)
            payment_id  = data.get('razorpay_payment_id', '')
            order_id    = data.get('razorpay_order_id', '')
            signature   = data.get('razorpay_signature', '')
            plan_name   = data.get('plan_name', 'Premium')
            amount      = data.get('amount', 0)

            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            client.utility.verify_payment_signature({
                'razorpay_order_id':   order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature':  signature,
            })

            if request.user.is_authenticated:
                from django.utils import timezone
                import datetime
                from .models import Subscription
                Subscription.objects.update_or_create(
                    user=request.user,
                    defaults={
                        'plan':                plan_name,
                        'amount':              amount,
                        'razorpay_order_id':   order_id,
                        'razorpay_payment_id': payment_id,
                        'status':              'Active',
                        'expires_at':          timezone.now() + datetime.timedelta(days=30),
                    }
                )

            return JsonResponse({'status': 'Payment Successful', 'payment_id': payment_id})

        except razorpay.errors.SignatureVerificationError:
            return JsonResponse({'error': 'Signature verification failed'}, status=400)
        except Exception as e:
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt  # Razorpay POSTs here after 3DS/OTP — no browser CSRF cookie available
def payment_callback(request):
    """
    Razorpay redirects the browser here (POST) after 3DS / OTP authentication.
    Verifies signature, saves subscription, renders success page.
    """
    if request.method == 'POST':
        try:
            payment_id = request.POST.get('razorpay_payment_id', '')
            order_id   = request.POST.get('razorpay_order_id', '')
            signature  = request.POST.get('razorpay_signature', '')
            plan_name  = request.GET.get('plan', 'Premium')
            amount     = request.GET.get('amount', '0')

            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            client.utility.verify_payment_signature({
                'razorpay_order_id':   order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature':  signature,
            })

            if request.user.is_authenticated:
                from django.utils import timezone
                import datetime
                from .models import Subscription
                Subscription.objects.update_or_create(
                    user=request.user,
                    defaults={
                        'plan':                plan_name,
                        'amount':              float(amount),
                        'razorpay_order_id':   order_id,
                        'razorpay_payment_id': payment_id,
                        'status':              'Active',
                        'expires_at':          timezone.now() + datetime.timedelta(days=30),
                    }
                )

            return render(request, 'payment_done.html', {
                'payment_id': payment_id,
                'plan':       plan_name,
                'amount':     amount,
                'success':    True,
            })

        except razorpay.errors.SignatureVerificationError:
            return render(request, 'payment_done.html', {
                'success': False,
                'error':   'Payment verification failed. Please contact support.',
            })
        except Exception as e:
            traceback.print_exc()
            return render(request, 'payment_done.html', {
                'success': False,
                'error':   str(e),
            })

    return redirect('add_payment')

def manage_articles(request):
    from django.core.paginator import Paginator

    qs = Article.objects.select_related('author').prefetch_related('media').all()

    # Filters
    q        = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    status   = request.GET.get('status', '')
    sort     = request.GET.get('sort', '-created_at')

    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(content__icontains=q))
    if category:
        qs = qs.filter(category__icontains=category)
    # Article status based on is_published field
    if status == 'published':
        qs = qs.filter(is_published=True)
    elif status == 'draft':
        qs = qs.filter(is_published=False)

    sort_map = {
        'latest': '-created_at',
        'oldest': 'created_at',
        'views': '-views_count',
        'az': 'title',
    }
    qs = qs.order_by(sort_map.get(sort, '-created_at'))

    total_articles  = Article.objects.count()
    total_views     = Article.objects.aggregate(tv=Sum('views_count'))['tv'] or 0
    published_count = Article.objects.filter(is_published=True).count()
    draft_count     = Article.objects.filter(is_published=False).count()
    categories      = Article.objects.values_list('category', flat=True).distinct().exclude(category__isnull=True)

    paginator   = Paginator(qs, 10)
    page_number = request.GET.get('page', 1)
    page_obj    = paginator.get_page(page_number)

    # Sort pinned articles to top on page 1
    pinned_ids = request.session.get('pinned_articles', [])
    articles_list = list(page_obj)
    if pinned_ids and int(page_number) == 1:
        pinned = [a for a in articles_list if a.id in pinned_ids]
        rest   = [a for a in articles_list if a.id not in pinned_ids]
        articles_list = pinned + rest

    # trending threshold: top 20% by views
    trending_threshold = 10

    bookmarked_ids = set()
    if request.user.is_authenticated:
        bookmarked_ids = set(Bookmark.objects.filter(user=request.user).values_list('article_id', flat=True))

    context = {
        'page_obj':          page_obj,
        'articles':          articles_list,
        'pinned_ids':        pinned_ids,
        'bookmarked_ids':    bookmarked_ids,
        'total_articles':    total_articles,
        'total_views':       total_views,
        'published_count':   published_count,
        'draft_count':       draft_count,
        'categories':        categories,
        'trending_threshold': trending_threshold,
        'q':        q,
        'category': category,
        'status':   status,
        'sort':     sort,
        'cities':   Article.objects.values_list('city', flat=True).distinct().exclude(city__isnull=True).exclude(city=''),
        'states':   Article.objects.values_list('state', flat=True).distinct().exclude(state__isnull=True).exclude(state=''),
    }
    return render(request, 'manage_articles.html', context)

def analytics(request):
    total_views = sum(article.views_count for article in Article.objects.all())
    total_articles = Article.objects.count()
    avg_views = total_views // total_articles if total_articles > 0 else 0
    top_articles = Article.objects.order_by('-views_count')[:5]
    cities = Article.objects.values_list('city', flat=True).distinct().exclude(city__isnull=True).exclude(city='')
    states = Article.objects.values_list('state', flat=True).distinct().exclude(state__isnull=True).exclude(state='')
    context = {
        'total_views': total_views,
        'total_articles': total_articles,
        'avg_views': avg_views,
        'top_articles': top_articles,
        'cities': cities,
        'states': states,
    }
    return render(request, 'analytics.html', context)

def admin_analytics_dashboard(request):
    total_articles = Article.objects.count()
    total_users = User.objects.count()
    total_comments = Comment.objects.count()
    total_reactions = Reaction.objects.count()
    
    active_ads = AdPayment.objects.filter(status='Completed').count()
    revenue_dict = AdPayment.objects.filter(status='Completed').aggregate(total_rev=Sum('amount'))
    total_revenue = revenue_dict['total_rev'] or 0

    cities  = Article.objects.values_list('city',  flat=True).distinct().exclude(city__isnull=True).exclude(city='')
    states  = Article.objects.values_list('state', flat=True).distinct().exclude(state__isnull=True).exclude(state='')

    context = {
        'total_articles': total_articles,
        'total_users': total_users,
        'total_comments': total_comments,
        'total_reactions': total_reactions,
        'active_ads': active_ads,
        'total_revenue': total_revenue,
        'cities': cities,
        'states': states,
    }
    return render(request, 'admin_analytics.html', context)

@login_required
def edit_article(request, article_id):
    article = get_object_or_404(Article, id=article_id)

    default_cats = ['Politics', 'Sports', 'Technology', 'Business', 'Entertainment', 'Education', 'Health', 'Crime', 'Weather', 'Jobs', 'Events']
    db_cats = list(Article.objects.values_list('category', flat=True).distinct().exclude(category__isnull=True).exclude(category=''))
    db_cats_lower = [c.lower() for c in db_cats]
    for d in default_cats:
        if d.lower() not in db_cats_lower:
            db_cats.append(d)

    cities = list(Article.objects.values_list('city', flat=True).distinct().exclude(city__isnull=True).exclude(city=''))
    states = list(Article.objects.values_list('state', flat=True).distinct().exclude(state__isnull=True).exclude(state=''))
    default_states = ['Gujarat', 'Maharashtra', 'Rajasthan', 'Delhi', 'Karnataka', 'Tamil Nadu', 'Uttar Pradesh', 'West Bengal', 'Punjab', 'Madhya Pradesh']
    states_lower = [s.lower() for s in states]
    for s in default_states:
        if s.lower() not in states_lower:
            states.append(s)

    if request.method == 'POST':
        title    = request.POST.get('title', '').strip()
        content  = request.POST.get('content', '').strip()
        category = request.POST.get('category', '').strip()
        city     = request.POST.get('city', '').strip()
        state    = request.POST.get('state', '').strip()
        if title and content:
            article.title    = title
            article.content  = content
            article.category = category or None
            article.city     = city or None
            article.state    = state or None
            article.save()
            messages.success(request, 'Article updated successfully.')
            return redirect('manage_articles')
        else:
            messages.error(request, 'Title and content are required.')

    return render(request, 'edit_article.html', {
        'article':    article,
        'categories': db_cats,
        'cities':     cities,
        'states':     states,
    })


def pin_article(request, article_id):
    """AJAX — toggle pinned state stored in session."""
    if request.method == 'POST':
        pinned = request.session.get('pinned_articles', [])
        if article_id in pinned:
            pinned.remove(article_id)
            is_pinned = False
        else:
            pinned.insert(0, article_id)
            is_pinned = True
        request.session['pinned_articles'] = pinned
        return JsonResponse({'pinned': is_pinned})
    return JsonResponse({'error': 'POST required'}, status=405)


@login_required
def delete_article(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    if request.method == 'POST':
        article.delete()
        messages.success(request, 'Article deleted successfully.')
    return redirect('manage_articles')


def all_city_news(request):
    """Landing page showing all articles grouped/filtered by city."""
    from django.core.paginator import Paginator
    city_filter = request.GET.get('city', '')
    q           = request.GET.get('q', '').strip()

    articles = Article.objects.filter(
        city__isnull=False
    ).exclude(city='').prefetch_related('media').order_by('-created_at')

    if city_filter:
        articles = articles.filter(city__iexact=city_filter)
    if q:
        articles = articles.filter(Q(title__icontains=q) | Q(content__icontains=q))

    paginator = Paginator(articles, 9)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    cities = Article.objects.values_list('city', flat=True).distinct().exclude(city__isnull=True).exclude(city='').order_by('city')
    states = Article.objects.values_list('state', flat=True).distinct().exclude(state__isnull=True).exclude(state='')

    return render(request, 'all_city_news.html', {
        'articles':     page_obj,
        'cities':       cities,
        'states':       states,
        'city_filter':  city_filter,
        'q':            q,
        'total':        articles.count(),
    })


def search_articles(request):
    from django.core.paginator import Paginator
    query = request.GET.get('q', '').strip()
    results = Article.objects.none()

    if query:
        results = Article.objects.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(category__icontains=query)
        ).prefetch_related('media').order_by('-created_at')

    total = results.count()
    paginator = Paginator(results, 10)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    cities = Article.objects.values_list('city', flat=True).distinct().exclude(city__isnull=True).exclude(city='')
    states = Article.objects.values_list('state', flat=True).distinct().exclude(state__isnull=True).exclude(state='')

    return render(request, 'search_results.html', {
        'query':    query,
        'results':  results,
        'q':        query,
        'page_obj': page_obj,
        'total':    total,
        'cities':   cities,
        'states':   states,
    })


def all_state_news(request):
    """Landing page showing all articles grouped/filtered by state."""
    from django.core.paginator import Paginator
    state_filter = request.GET.get('state', '')
    q            = request.GET.get('q', '').strip()

    articles = Article.objects.filter(
        state__isnull=False
    ).exclude(state='').prefetch_related('media').order_by('-created_at')

    if state_filter:
        articles = articles.filter(state__iexact=state_filter)
    if q:
        articles = articles.filter(Q(title__icontains=q) | Q(content__icontains=q))

    paginator = Paginator(articles, 9)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    cities = Article.objects.values_list('city', flat=True).distinct().exclude(city__isnull=True).exclude(city='')
    states = Article.objects.values_list('state', flat=True).distinct().exclude(state__isnull=True).exclude(state='').order_by('state')

    return render(request, 'all_state_news.html', {
        'articles':     page_obj,
        'states':       states,
        'cities':       cities,
        'state_filter': state_filter,
        'q':            q,
        'total':        articles.count(),
    })


def category_view(request, category_name):
    from django.core.paginator import Paginator

    articles = Article.objects.filter(
        category__iexact=category_name
    ).prefetch_related('media').order_by('-views_count', '-created_at')

    total     = articles.count()
    paginator = Paginator(articles, 9)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    cities = Article.objects.values_list('city',  flat=True).distinct().exclude(city__isnull=True).exclude(city='')
    states = Article.objects.values_list('state', flat=True).distinct().exclude(state__isnull=True).exclude(state='')

    return render(request, 'category.html', {
        'articles':      page_obj,
        'category_name': category_name,
        'total':         total,
        'cities':        cities,
        'states':        states,
    })


@login_required
def report_fake_news(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    if request.method == 'POST':
        reason = request.POST.get('reason')
        if reason:
            FakeNewsReport.objects.create(
                user=request.user,
                article=article,
                reason=reason
            )
            messages.success(request, 'Thank you for your report. It has been submitted for review.')
            return redirect('user_dashboard')
    return render(request, 'report_fake_news.html', {'article': article})

@login_required
def bookmark_article(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    bookmark, created = Bookmark.objects.get_or_create(user=request.user, article=article)
    if not created:
        bookmark.delete()
        bookmarked = False
    else:
        bookmarked = True
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.method == 'POST':
        return JsonResponse({'bookmarked': bookmarked})
    return redirect('user_dashboard')