from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import signup_view, login_view, home_view, dashboard_view, logout_view, city_view, state_view, article_detail_view
from news.views import add_payment

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth
    path('signup/',  signup_view,  name='signup'),
    path('login/',   login_view,   name='login'),
    path('logout/',  logout_view,  name='logout'),

    # Home & Dashboard
    path('',          home_view,      name='home'),
    path('dashboard/', dashboard_view, name='dashboard'),

    # Public portal pages
    path('city/<str:city_name>/',   city_view,           name='city_news'),
    path('state/<str:state_name>/', state_view,          name='state_news'),
    path('article/<int:article_id>/', article_detail_view, name='article_detail'),

    # News App
    path('news/', include('news.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)