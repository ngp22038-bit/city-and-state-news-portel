from django.db import models
from django.utils import timezone
from core.models import User

# Create your models here.

class Article(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    category = models.CharField(max_length=100, null=True)
    city = models.CharField(max_length=100, null=True)
    state = models.CharField(max_length=100, null=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    views_count = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class ArticleMedia(models.Model):
    MEDIA_TYPE_CHOICES = (
        ('Image', 'Image'),
        ('Video', 'Video'),
        ('Infographic', 'Infographic'),
    )

    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='media')
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPE_CHOICES)
    media_upload = models.FileField(upload_to='article_media/', blank=True, null=True)
    media_url = models.URLField(max_length=500, blank=True, null=True, help_text="Automatically generated file path or enter media URL")
    uploaded_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.article.title} - {self.media_type}"

class Reaction(models.Model):
    REACTION_CHOICES = (
        ('Like', 'Like'),
        ('Dislike', 'Dislike'),
        ('Love', 'Love'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    reaction_type = models.CharField(max_length=20, choices=REACTION_CHOICES)
    rating = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.email} - {self.reaction_type} on {self.article.title}"

class Comment(models.Model):
    STATUS_CHOICES = (
        ('Visible', 'Visible'),
        ('Removed', 'Removed'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    comment_text = models.TextField()
    comment_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Visible')

    def __str__(self):
        return f"Comment by {self.user.email} on {self.article.title}"

class NewsTip(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Reviewed', 'Reviewed'),
        ('Published', 'Published'),
    )
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} bookmarked {self.article.title}"


class FakeNewsReport(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Reviewed', 'Reviewed'),
        ('Removed', 'Removed'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report on {self.article.title}"


class ReadingHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reading_history')
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'article')
        ordering = ['-read_at']

    def __str__(self):
        return f"{self.user.email} read {self.article.title}"


class AdPayment(models.Model):
    PAYMENT_METHOD_CHOICES = (
        ('Card', 'Card'),
        ('UPI', 'UPI'),
        ('Netbanking', 'Netbanking'),
        ('Paytm Wallet', 'Paytm Wallet'),
        ('PhonePe', 'PhonePe'),
        ('Google Pay', 'Google Pay'),
        ('QR Payment', 'QR Payment'),
        ('Razorpay Gateway', 'Razorpay Gateway'),
    )
    PLAN_CHOICES = (
        ('Basic', 'Basic Plan - ₹500'),
        ('Standard', 'Standard Plan - ₹2000'),
        ('Premium', 'Premium Plan - ₹5000'),
    )
    advertiser = models.ForeignKey(User, on_delete=models.CASCADE)
    ad_title = models.CharField(max_length=255)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default='Completed')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ad: {self.ad_title} by {self.advertiser.email}"
