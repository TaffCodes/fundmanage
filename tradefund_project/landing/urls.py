from django.urls import path
from . import views

app_name = 'landing'

urlpatterns = [
    path('', views.home_page, name='home'),
    # path('terms/', views.terms_page, name='terms'),
    # path('privacy/', views.privacy_page, name='privacy'),
]