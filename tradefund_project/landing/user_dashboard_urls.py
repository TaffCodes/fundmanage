# landing/user_dashboard_urls.py
from django.urls import path
from . import views # Assuming views.py contains your user dashboard views
from django.conf import settings
# from django.conf.urls.static import static

app_name = 'user_dashboard'

urlpatterns = [
    path('', views.user_dashboard_main, name='home'),
    path('user_pay_for_tier/', views.user_pay_for_tier, name='user_pay_for_tier'),
    path('transactions/', views.user_transaction_history, name='transactions'),
    path('settings/', views.user_settings_page, name='settings'),
    path('settings/profile/', views.user_profile_update, name='profile_update'),
    path('my_trader/', views.user_trader_details_view, name='my_trader_details'),
    path('api/portfolio-history/', views.portfolio_history_api, name='portfolio_history_api'),
    path('notifications/', views.user_notifications_view, name='notifications'),
    path('notifications/mark-read/<int:notification_id>/', views.mark_notification_as_read_api, name='mark_notification_read_api'),
    path('documents/', views.user_documents_view, name='documents'),
    path('kyc/', views.user_kyc_view, name='kyc'),
    path('settings/notification-preferences/', views.user_notification_preferences_view, name='notification_preferences'),
    path('test-template/', views.test_template, name='test_template'),
    path('reinvest/', views.user_reinvest_funds_view, name='reinvest_funds'),
    path('api/notifications/unread-count/', views.unread_notification_count, name='unread_notification_count'),
]