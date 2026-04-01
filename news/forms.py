from django import forms
from django.utils import timezone
from .models import ArticleMedia, Article
from core.models import User

class ArticleMediaForm(forms.ModelForm):
    class Meta:
        model = ArticleMedia
        fields = ['article', 'media_type', 'media_upload', 'media_url', 'uploaded_date']
        widgets = {
            'article': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Select related article'}),
            'media_type': forms.Select(attrs={'class': 'form-control'}),
            'media_upload': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'media_url': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Automatically generated file path or enter media URL'}),
            'uploaded_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        media_type = cleaned_data.get('media_type')
        media_upload = cleaned_data.get('media_upload')

        if media_upload and media_type:
            file_name = media_upload.name.lower()
            if media_type == 'Image':
                if not (file_name.endswith('.jpg') or file_name.endswith('.jpeg') or file_name.endswith('.png')):
                    self.add_error('media_upload', 'For Image type, only JPG, JPEG, and PNG formats are supported.')
            elif media_type == 'Video':
                if not (file_name.endswith('.mp4') or file_name.endswith('.avi')):
                    self.add_error('media_upload', 'For Video type, only MP4 and AVI formats are supported.')
            elif media_type == 'Infographic':
                if not (file_name.endswith('.png') or file_name.endswith('.svg')):
                    self.add_error('media_upload', 'For Infographic type, only PNG and SVG formats are supported.')
        
        return cleaned_data

class CommentForm(forms.Form):
    STATUS_CHOICES = (
        ('Visible', 'Visible'),
        ('Removed', 'Removed'),
    )

    article_id = forms.ModelChoiceField(
        queryset=Article.objects.all(),
        empty_label='Select related article',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    user_id = forms.ModelChoiceField(
        queryset=User.objects.all(),
        empty_label='Select user who commented',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    comment_text = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter the comment content'})
    )
    comment_date = forms.DateTimeField(
        initial=timezone.now,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'})
    )
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class ReactionForm(forms.Form):
    REACTION_CHOICES = (
        ('Like', '👍 Like'),
        ('Dislike', '👎 Dislike'),
        ('Love', '❤️ Love'),
    )

    article_id = forms.ModelChoiceField(
        queryset=Article.objects.all(),
        empty_label='Select related article',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    user_id = forms.ModelChoiceField(
        queryset=User.objects.all(),
        empty_label='Select user reacting',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    reaction_type = forms.ChoiceField(
        choices=REACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    rating = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5, 'type': 'number'})
    )

class NewsTipForm(forms.Form):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Reviewed', 'Reviewed'),
        ('Published', 'Published'),
    )

    user_id = forms.ModelChoiceField(
        queryset=User.objects.all(),
        empty_label='Select user who submitted the tip',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    title = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter the news tip title'})
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Write the details of the news tip'})
    )
    location = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter City / State'})
    )
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class AdvertiserForm(forms.Form):
    BUSINESS_TYPE_CHOICES = (
        ('Technology', 'Technology'),
        ('Retail', 'Retail'),
        ('Education', 'Education'),
        ('Finance', 'Finance'),
        ('Healthcare', 'Healthcare'),
        ('Entertainment', 'Entertainment'),
    )
    
    VERIFIED_CHOICES = (
        (True, 'Verified'),
        (False, 'Not Verified'),
    )

    advertiser_id = forms.ModelChoiceField(
        queryset=User.objects.all(),
        empty_label='Select user account for advertiser',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    company_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter advertiser company name'})
    )
    business_type = forms.ChoiceField(
        choices=BUSINESS_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    verified = forms.ChoiceField(
        choices=VERIFIED_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class AdvertisementForm(forms.Form):
    PLACEMENT_CHOICES = (
        ('Homepage', 'Homepage'),
        ('Sidebar', 'Sidebar'),
        ('Article Page', 'Article Page'),
    )

    STATUS_CHOICES = (
        ('Active', 'Active'),
        ('Expired', 'Expired'),
    )

    advertiser_id = forms.ModelChoiceField(
        queryset=User.objects.all(), # Note: Should ideally map to an Advertiser model if one exists, using User for now as requested
        empty_label='Select advertiser company',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    ad_title = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter advertisement title'})
    )
    placement = forms.ChoiceField(
        choices=PLACEMENT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    ad_status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    clicks = forms.IntegerField(
        initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'type': 'number'})
    )

class PaymentForm(forms.Form):
    PAYMENT_METHOD_CHOICES = (
        ('Traditional Methods', (
            ('Card', '💳 Card / Debit / Credit'),
            ('UPI', '📱 UPI'),
            ('Netbanking', '🏦 Netbanking'),
        )),
        ('Wallet Payments', (
            ('Paytm Wallet', 'Paytm Wallet'),
            ('PhonePe Wallet', 'PhonePe Wallet'),
            ('Amazon Pay', 'Amazon Pay'),
            ('Google Pay Wallet', 'Google Pay Wallet'),
        )),
        ('QR Code Payment', (
            ('Dynamic QR', 'Dynamic QR Payment'),
            ('Scan & Pay', 'Scan & Pay'),
        )),
        ('Subscription Credit', (
            ('Account Credit', 'Use Account Credit / Wallet Balance'),
        )),
        ('Cryptocurrency', (
            ('Bitcoin', 'Bitcoin (BTC)'),
            ('Ethereum', 'Ethereum (ETH)'),
            ('USDT', 'Tether (USDT)'),
        )),
        ('Payment Gateway', (
            ('Razorpay', 'Razorpay'),
            ('Stripe', 'Stripe'),
            ('PayPal', 'PayPal'),
        ))
    )

    PAYMENT_PLAN_CHOICES = (
        ('Basic', 'Basic Plan – ₹500'),
        ('Standard', 'Standard Plan – ₹2000'),
        ('Premium', 'Premium Plan – ₹5000'),
    )

    PAYMENT_STATUS_CHOICES = (
        ('Success', '✅ Success'),
        ('Failed', '❌ Failed'),
    )

    advertiser_id = forms.ModelChoiceField(
        queryset=User.objects.all(), # Note: Should ideally map to an Advertiser model if one exists, using User for now as requested
        empty_label='Select advertiser',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    payment_plan = forms.ChoiceField(
        choices=PAYMENT_PLAN_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    payment_date = forms.DateTimeField(
        initial=timezone.now,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'})
    )
    payment_status = forms.ChoiceField(
        choices=PAYMENT_STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class ReportForm(forms.Form):
    REPORT_TYPE_CHOICES = (
        ('Views Report', '👁 Views Report'),
        ('Ads Performance Report', '📢 Ads Performance Report'),
        ('Engagement Report', '💬 Engagement Report'),
    )

    report_type = forms.ChoiceField(
        choices=REPORT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    generated_by = forms.ModelChoiceField(
        queryset=User.objects.filter(is_staff=True), # Fetching admins/staff from the User table
        empty_label='Select admin generating the report',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    report_date = forms.DateTimeField(
        initial=timezone.now,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'})
    )
    report_data = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter report summary and analysis details'})
    )
