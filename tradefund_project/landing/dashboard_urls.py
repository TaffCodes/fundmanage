# landing/dashboard_urls.py
from django.urls import path
from . import views # Assuming views.py contains your dashboard views

app_name = 'dashboard' # Namespace for dashboard URLs

urlpatterns = [
    path('', views.staff_dashboard_home, name='home'),
    path('users/all/', views.staff_all_users_list, name='all_users'),
    path('users/tier/<str:tier_key>/', views.staff_users_by_tier_list, name='users_by_tier'),
    path('traders/', views.staff_trader_list_view, name='trader_list'),
    path('announcements/', views.staff_platform_announcements_list_view, name='announcement_list'),
    path('kyc_review/', views.staff_kyc_review_list_view, name='kyc_review_list'),
    path('user-documents/', views.staff_user_documents_overview_view, name='user_documents_overview'),
]