"""
Django settings for the multi-tenant Jabstir Welfare Group platform.
Configured for Kenya (EAT timezone) with PostgreSQL schema-based isolation.
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# --- SECURITY WARNINGS ---
# Keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-your-secure-development-key-replace-in-production'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Allows routing for any subdomains on localhost (e.g., jabstir.localhost)
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '192.168.100.8', '.localhost']


# --- MULTI-TENANT APPLICATION CONFIGURATION ---

# Shared apps are global and reside ONLY in the 'public' database schema.
SHARED_APPS = [
    'django_tenants',  # mandatory
    'customers',       # your tenant-mapping app

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    'rest_framework',  # <--- Add here for public/shared access if needed
]

TENANT_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    
    'rest_framework',  # <--- Add here so DRF templates load in tenant schemas
    'welfare',         # your welfare management app
]

# Combined INSTALLED_APPS as required by django-tenants
INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

# Tell the system where our Client and Domain models are defined
TENANT_MODEL = 'customers.Client'
TENANT_DOMAIN_MODEL = 'customers.Domain'


# --- MIDDLEWARE ---
MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',  # Mandatory: Must be at the very top!
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# --- POSTGRESQL MULTI-TENANT DATABASE CONFIGURATION ---

DATABASES = {
    'default': {
        # Using django_tenants' custom PostgreSQL engine
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': 'welfare_db',
        'USER': 'postgres',
        'PASSWORD': 'admin123',  # <-- Enter your local PostgreSQL password here
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}

# Router that syncs shared apps to public schema and tenant apps to tenant schemas
DATABASE_ROUTERS = (
    'django_tenants.routers.TenantSyncRouter',
)


# --- PASSWORD VALIDATION ---
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


# --- INTERNATIONALIZATION & KENYA TIMEZONE SETTINGS ---
LANGUAGE_CODE = 'en-us'

# Set timezone to East Africa Time (EAT)
TIME_ZONE = 'Africa/Nairobi'

USE_I18N = True
USE_TZ = True


# --- STATIC FILES (CSS, JavaScript, Images) ---
STATIC_URL = 'static/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
