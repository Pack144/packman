"""
Django settings for packman project.

Generated by 'django-admin startproject' using Django 2.2.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""
from builtins import ImportError

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'w98b46*7+i8+6$_3n(jfa6(7*j3%v*^u#at2$qknbgt4_eu_vg'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    # Built-in Django apps
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Third party packages
    'crispy_forms',
    'debug_toolbar',
    'django_ical',
    'dynamic_formsets',
    'easy_thumbnails',
    'localflavor',
    'phonenumber_field',
    'tempus_dominus',
    'tinymce',

    # Local apps
    'address_book.apps.AddressBookConfig',
    'committees.apps.CommitteesConfig',
    'dens.apps.DensConfig',
    'documents.apps.DocumentsConfig',
    'membership.apps.MembershipConfig',
    'pack_calendar.apps.PackCalendarConfig',
    'pages.apps.PagesConfig',
    'polls.apps.PollsConfig',
    'post_office.apps.PostOfficeConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.admindocs.middleware.XViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'pages.context_processors.navbar_items',
            ],
        },
    },
]

# WSGI
# https://docs.djangoproject.com/en/3.0/howto/deployment/wsgi/
# -----------------------------------------------------------------------------
WSGI_APPLICATION = 'config.wsgi.application'

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases
# -----------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators
# -----------------------------------------------------------------------------
PASSWORD_HASHERS = [
    # https://docs.djangoproject.com/en/3.0/topics/auth/passwords/#using-argon2-with-django
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

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
# https://docs.djangoproject.com/en/3.0/topics/i18n/
# -----------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/Los_Angeles'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/
# -----------------------------------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'node_modules'),
    os.path.join(BASE_DIR, 'static'),
]
STATIC_ROOT = os.path.join(BASE_DIR, 'static_files')
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home_page'
LOGOUT_REDIRECT_URL = 'home_page'

# Email settings for development environment
# https://docs.djangoproject.com/en/3.0/topics/email/#console-backend
# Override for production
# -----------------------------------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Used by apps such as debug_toolbar to determine from what IP addresses requests to display
# -----------------------------------------------------------------------------
INTERNAL_IPS = [
    '127.0.0.1',
]

# Easy Thumbnails
# https://easy-thumbnails.readthedocs.io/en/latest/usage/#thumbnail-aliases
# -----------------------------------------------------------------------------
THUMBNAIL_ALIASES = {
    'membership': {
        'thumbnail': {
            'size': (80, 80),
            'crop': 'smart',
            'quality': 90,
        },
        'card': {
            'size': (320, 320),
            'crop': 'smart',
            'quality': 90,
        }
    },
}

# django-crispy-forms
# http://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
# -----------------------------------------------------------------------------
CRISPY_TEMPLATE_PACK = 'bootstrap4'
CRISPY_FAIL_SILENTLY = not DEBUG

# django-phonenumber-field
# https://github.com/stefanfoulis/django-phonenumber-field
# -----------------------------------------------------------------------------
PHONENUMBER_DEFAULT_REGION = 'US'
PHONENUMBER_DEFAULT_FORMAT = 'NATIONAL'

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/3.0/ref/settings/#session-cookie-httponly
SESSION_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/3.0/ref/settings/#csrf-cookie-httponly
CSRF_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/3.0/ref/settings/#secure-browser-xss-filter
SECURE_BROWSER_XSS_FILTER = True
# https://docs.djangoproject.com/en/3.0/ref/settings/#x-frame-options
X_FRAME_OPTIONS = 'DENY'
# https://docs.djangoproject.com/en/3.0/ref/middleware/#x-content-type-options-nosniff
SECURE_CONTENT_TYPE_NOSNIFF = True

# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/3.0/ref/settings/#logging
# See https://docs.djangoproject.com/en/3.0/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}},
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s "
                      "%(process)d %(thread)d %(message)s"
        }
    },
    "handlers": {
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"level": "INFO", "handlers": ["console"]},
    "loggers": {
        "django.request": {
            "handlers": ["mail_admins"],
            "level": "ERROR",
            "propagate": True,
        },
        "django.security.DisallowedHost": {
            "level": "ERROR",
            "handlers": ["console", "mail_admins"],
            "propagate": True,
        },
    },
}

# Custom User Model
# https://docs.djangoproject.com/en/3.0/topics/auth/customizing/#auth-custom-user
# -----------------------------------------------------------------------------
AUTH_USER_MODEL = 'membership.Adult'


# django-tinymce
# https://django-tinymce.readthedocs.io/en/latest/installation.html#configuration
# -----------------------------------------------------------------------------
# TINYMCE_DEFAULT_CONFIG = {
#     'branding': False,
#     'height': 500,
#     'menubar': False,
#     'skin': 'oxide-dark',
#     'content_css': 'dark',
#
# }
TINYMCE_INCLUDE_JQUERY = False


# django-tempus-dominus
# https://tempusdominus.github.io/bootstrap-4/
# https://github.com/FlipperPA/django-tempus-dominus
# -----------------------------------------------------------------------------
TEMPUS_DOMINUS_INCLUDE_ASSETS = False  # We'll use Yarn for this


# When does the site start a new year of scouting? Typically, this would be when
# cubs advance to the next rank.
# -----------------------------------------------------------------------------
PACK_YEAR_BEGIN_MONTH = 9  # September
PACK_YEAR_BEGIN_DAY = 1  # 1st
PACK_NAME = 'Cub Scouts Pack 144'
PACK_SHORTNAME = 'Pack 144'
PACK_TAGLINE = 'Since 1929'
PACK_LOCATION = 'Seattle, Washington'


# Allow for a private local_settings.py file to override anything in this settings.py
# local_settings.py is not included in the project and will not be part of the git repository
# use it to store your production settings such as SECRET_KEY, DEBUG, DATABASES, EMAIL_BACKEND, etc.
try:
    from .local_settings import *
except ImportError:
    pass
