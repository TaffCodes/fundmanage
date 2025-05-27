import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-^8%p=ll$ts70^5uy%*o1yikphc74#2zkbi==)35z5$5^)txza4'

DEBUG = True # Set to False in production

ALLOWED_HOSTS = [] # Add your domain in production, e.g., ['www.tradefund.com', 'tradefund.com']


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


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
DATABASES = {
    # 'default': {
    #     'ENGINE': 'django.db.backends.sqlite3',
    #     'NAME': BASE_DIR / 'db.sqlite3',
    # }
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'tradefund',
        'USER': 'postgres',
        'PASSWORD': '123345.',
        'HOST': 'localhost',
        'PORT': '5432',
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

# Email settings (for development, emails print to console)
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'mauyaroy@gmail.com'
# EMAIL_HOST_PASSWORD = 'zmql bvsz jlib txof'
# DEFAULT_FROM_EMAIL = 'mauyaroy@gmail.com'

# Email settings for production (replace with your actual email settings)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'mail.privateemail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'support@ftmotradefund.com'
EMAIL_HOST_PASSWORD = 'iamnyaregar44'
DEFAULT_FROM_EMAIL = 'support@ftmotradefund.com'

LOGIN_REDIRECT_URL = '/u/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/'

# Media files (uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

TEMPLATE_DEBUG = True # Set to False in production