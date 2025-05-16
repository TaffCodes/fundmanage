from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),  # Allauth URLs
    path('dashboard/', include('landing.dashboard_urls', namespace='dashboard')), # New Dashboard URLs
    path('', include('landing.urls', namespace='landing')), # Your landing app URLs
]