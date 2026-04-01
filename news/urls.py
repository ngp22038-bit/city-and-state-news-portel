from django.urls import path
from django.views.generic import RedirectView
from .views import (owner_dashboard, user_dashboard, add_article, add_payment,
                    manage_articles, delete_article, edit_article, pin_article,
                    analytics, admin_analytics_dashboard,
                    report_fake_news, bookmark_article, reader_search,
                    live_news, live_news_api, category_view,
                    all_city_news, all_state_news, search_articles)

urlpatterns = [
    path('owner/', owner_dashboard, name='owner_dashboard'),
    path('user/', user_dashboard, name='user_dashboard'),

    # Redirects for old/mistyped URLs
    path('owner_dashboard/', RedirectView.as_view(pattern_name='owner_dashboard', permanent=False)),
    path('user_dashboard/',  RedirectView.as_view(pattern_name='user_dashboard',  permanent=False)),

    path('add-article/', add_article, name='add_article'),
    path('edit-article/<int:article_id>/', edit_article, name='edit_article'),
    path('pin-article/<int:article_id>/', pin_article, name='pin_article'),
    path('add-payment/', add_payment, name='add_payment'),
    path('manage-articles/', manage_articles, name='manage_articles'),
    path('delete-article/<int:article_id>/', delete_article, name='delete_article'),
    path('analytics/', analytics, name='analytics'),
    path('admin-analytics/', admin_analytics_dashboard, name='admin_analytics'),
    path('report-fake-news/<int:article_id>/', report_fake_news, name='report_fake_news'),
    path('bookmark/<int:article_id>/', bookmark_article, name='bookmark_article'),
    path('search/', reader_search, name='reader_search'),
    path('search-results/', search_articles, name='search_articles'),
    path('live/', live_news, name='live_news'),
    path('live/api/', live_news_api, name='live_news_api'),
    path('category/<str:category_name>/', category_view, name='category'),
    path('city/', all_city_news, name='all_city_news'),
    path('state/', all_state_news, name='all_state_news'),
]