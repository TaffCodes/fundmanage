# tradefund_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from landing import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('staff_dashboard/', include('landing.dashboard_urls', namespace='staff_dashboard')), # Renamed for clarity
    path('u/', include('landing.user_dashboard_urls', namespace='user_dashboard')),      # NEW User Dashboard URLs
    path('', include('landing.urls', namespace='landing')),
    path('api/notifications/unread-count/', views.unread_notification_count, name='unread_notification_count'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)