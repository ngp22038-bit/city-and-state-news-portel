from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, Count, F, ExpressionWrapper, FloatField
from .forms import LoginForm, SignupForm
from django.conf import settings


# ── Home View ──────────────────────────────────────────────────────────────────
def home_view(request):
    from news.models import Article, Bookmark
    from django.db.models import ExpressionWrapper, FloatField

    featured   = Article.objects.prefetch_related('media').order_by('-views_count').first()
    latest     = Article.objects.prefetch_related('media').order_by('-created_at')[:8]
    trending   = Article.objects.annotate(
        score=ExpressionWrapper(
            F('views_count') * 0.5 + Count('comment') * 3,
            output_field=FloatField()
        )
    ).order_by('-score')[:6]
    city_news  = Article.objects.filter(city__isnull=False).exclude(city='').order_by('-created_at')[:4]
    state_news = Article.objects.filter(state__isnull=False).exclude(state='').order_by('-created_at')[:4]

    # distinct cities & states for selector
    cities  = Article.objects.values_list('city',  flat=True).distinct().exclude(city__isnull=True).exclude(city='')
    states  = Article.objects.values_list('state', flat=True).distinct().exclude(state__isnull=True).exclude(state='')
    categories = Article.objects.values_list('category', flat=True).distinct().exclude(category__isnull=True)

    bookmarked_ids = set()
    if request.user.is_authenticated:
        bookmarked_ids = set(Bookmark.objects.filter(user=request.user).values_list('article_id', flat=True))

    context = {
        'featured':       featured,
        'latest':         latest,
        'trending':       trending,
        'city_news':      city_news,
        'state_news':     state_news,
        'cities':         cities,
        'states':         states,
        'categories':     categories,
        'bookmarked_ids': bookmarked_ids,
    }
    return render(request, 'core/home.html', context)


# ── City Page ──────────────────────────────────────────────────────────────────
def city_view(request, city_name):
    from news.models import Article
    articles = Article.objects.filter(city__iexact=city_name).prefetch_related('media').order_by('-created_at')
    cities   = Article.objects.values_list('city', flat=True).distinct().exclude(city__isnull=True).exclude(city='')
    context  = {'articles': articles, 'city_name': city_name, 'cities': cities}
    return render(request, 'core/city_news.html', context)


# ── State Page ─────────────────────────────────────────────────────────────────
def state_view(request, state_name):
    from news.models import Article
    articles   = Article.objects.filter(state__iexact=state_name).prefetch_related('media').order_by('-created_at')
    categories = articles.values_list('category', flat=True).distinct().exclude(category__isnull=True)
    states     = Article.objects.values_list('state', flat=True).distinct().exclude(state__isnull=True).exclude(state='')
    context    = {'articles': articles, 'state_name': state_name, 'categories': categories, 'states': states}
    return render(request, 'core/state_news.html', context)


# ── Article Detail ─────────────────────────────────────────────────────────────
def article_detail_view(request, article_id):
    from news.models import Article, Comment, Bookmark, ReadingHistory
    article  = get_object_or_404(Article.objects.prefetch_related('media', 'comment_set'), id=article_id)

    # increment views
    Article.objects.filter(id=article_id).update(views_count=F('views_count') + 1)

    # track reading history
    if request.user.is_authenticated:
        ReadingHistory.objects.update_or_create(user=request.user, article=article)

    related  = Article.objects.filter(
        Q(category=article.category) | Q(city=article.city)
    ).exclude(id=article_id).order_by('-created_at')[:4]

    comments = article.comment_set.filter(status='Visible').order_by('-comment_date')
    is_saved = False
    if request.user.is_authenticated:
        is_saved = Bookmark.objects.filter(user=request.user, article=article).exists()

    # handle comment POST
    if request.method == 'POST' and request.user.is_authenticated:
        text = request.POST.get('comment_text', '').strip()
        if text:
            Comment.objects.create(user=request.user, article=article, comment_text=text)
            messages.success(request, 'Comment posted.')
            return redirect('article_detail', article_id=article_id)

    context = {
        'article':  article,
        'related':  related,
        'comments': comments,
        'is_saved': is_saved,
    }
    return render(request, 'core/article_detail.html', context)


# ── Dashboard ──────────────────────────────────────────────────────────────────
@login_required
def dashboard_view(request):
    if request.user.role == "owner":
        return redirect('owner_dashboard')
    return redirect('user_dashboard')


# ── Signup ─────────────────────────────────────────────────────────────────────
def signup_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Account created successfully!")
        return redirect('owner_dashboard' if user.role == "owner" else 'user_dashboard')
    return render(request, 'core/signup.html', {'form': form})


# ── Login ──────────────────────────────────────────────────────────────────────
def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = authenticate(request,
                            username=form.cleaned_data['email'],
                            password=form.cleaned_data['password'])
        if user:
            login(request, user)
            messages.success(request, "Login successful!")
            return redirect('owner_dashboard' if user.role == "owner" else 'user_dashboard')
        messages.error(request, "Invalid email or password")
    return render(request, 'core/login.html', {'form': form})


# ── Logout ─────────────────────────────────────────────────────────────────────
@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect('login')