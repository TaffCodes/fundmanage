# landing/dashboard_urls.py
from django.urls import path
from . import views # Assuming views.py contains your dashboard views

app_name = 'dashboard' # Namespace for dashboard URLs

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('users/all/', views.dashboard_all_users, name='all_users'),
    path('users/tier/<str:tier_key>/', views.dashboard_users_by_tier, name='users_by_tier'),
]