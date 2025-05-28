import os
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-^8%p=ll$ts70^5uy%*o1yikphc74#2zkbi==)35z5$5^)txza4')

DEBUG = True # Set to False in production

PORT = int(os.environ.get('PORT', 8000))

ALLOWED_HOSTS = [
    'fundmanage.onrender.com',
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    'ftmotradefund.com',
]

# CSRF settings for production
CSRF_TRUSTED_ORIGINS = [
    'https://fundmanage.onrender.com',
    'http://localhost:8000',
    '0.0.0.0',
    'localhost',
    'https://ftmotradefund.com',
]

# # Make this dynamic based on allowed hosts
# if os.environ.get('CSRF_TRUSTED_ORIGINS'):
#     CSRF_TRUSTED_ORIGINS.extend(
#         os.environ.get('CSRF_TRUSTED_ORIGINS').split(',')
#     )
# else:
#     # Automatically add all allowed hosts with https://
#     for host in ALLOWED_HOSTS:
#         if host not in ['127.0.0.1', 'localhost']:
#             if not host.startswith(('http://', 'https://')):
#                 CSRF_TRUSTED_ORIGINS.append(f'https://{host}')


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    
    
    # Your apps
    'landing.apps.LandingConfig',
    'landing.templatetags.custom_filters',

    # Third-party apps
    'allauth',
    'allauth.account',
    'allauth.socialaccount', # Optional, if you want social login later
    'django.contrib.sites',  # Required by allauth
    'widget_tweaks',         # For easier form styling in templates

     # Custom template filters
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware', # Add this for allauth
]

ROOT_URLCONF = 'tradefund_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request', # Required by allauth
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'landing.context_processors.staff_dashboard_context',
                'landing.context_processors.unread_notifications_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'tradefund_project.wsgi.application'



tmpPostgres = urlparse(os.getenv("DATABASE_URL"))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': tmpPostgres.path.replace('/', ''),
        'USER': tmpPostgres.username,
        'PASSWORD': tmpPostgres.password,
        'HOST': tmpPostgres.hostname,
        'PORT': 5432,
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi' # Or your preferred timezone
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/
STATIC_URL = '/static/'
# STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')] # For project-wide static files

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django Allauth settings
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend', # Default
    'allauth.account.auth_backends.AuthenticationBackend', # Allauth specific
]

SITE_ID = 1 # Required by allauth

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False # Using email as the primary identifier
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_VERIFICATION = 'mandatory' # 'optional' or 'none'
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGOUT_ON_GET = True # For simplicity, but POST is safer for logout
LOGIN_REDIRECT_URL = '/' # Redirect to home page after login
ACCOUNT_LOGOUT_REDIRECT_URL = '/' # Redirect to home page after logout
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 3
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = True # Good practice
ACCOUNT_FORMS = {'signup': 'landing.forms.CustomSignupForm'}
ACCOUNT_ADAPTER = 'allauth.account.adapter.DefaultAccountAdapter'
ACCOUNT_SESSION_REMEMBER = True # Remembers user session by default
# ACCOUNT_LOGIN_ATTEMPTS_LIMIT = 5
# ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT = 300 # 5 minutes



# Email configuration
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)

# Allauth configuration
ACCOUNT_EMAIL_VERIFICATION = os.environ.get('ACCOUNT_EMAIL_VERIFICATION', 'mandatory')
LOGIN_REDIRECT_URL = os.environ.get('LOGIN_REDIRECT_URL', '/u/')
ACCOUNT_LOGOUT_REDIRECT_URL = os.environ.get('ACCOUNT_LOGOUT_REDIRECT_URL', '/')

# Media files (uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

TEMPLATE_DEBUG = os.environ.get('TEMPLATE_DEBUG', 'True') == 'True'
