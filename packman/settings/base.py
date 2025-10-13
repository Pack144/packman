"""
Django settings for packman project.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

from email.utils import getaddresses
from pathlib import Path

import environ

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
APPS_DIR = Path(__file__).resolve().parent.parent

# 12factor
# https://www.12factor.net
# https://django-environ.readthedocs.io/en/latest
env = environ.Env()
dot_env = BASE_DIR / ".env"
if dot_env.is_file():
    env.read_env(str(dot_env))


# Application definition
# -----------------------------------------------------------------------------

INSTALLED_APPS = [
    # Built-in Django apps
    "django.contrib.admin",
    "django.contrib.admindocs",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sites",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Third party packages
    "crispy_forms",
    "crispy_bootstrap5",
    "django_ical",
    "dynamic_formsets",
    "easy_thumbnails",
    "localflavor",
    "phonenumber_field",
    "tinymce",
    "whitenoise",
    # Local apps
    "packman.address_book",
    "packman.calendars",
    "packman.campaigns",
    "packman.committees",
    "packman.core",
    "packman.dens",
    "packman.documents",
    "packman.mail",
    "packman.membership",
    "packman.pages",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # https://whitenoise.readthedocs.io/en/stable/django.html#enable-whitenoise
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.admindocs.middleware.XViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "packman.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            APPS_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "packman.pages.context_processors.populate_navbar",
            ],
        },
    },
]


# WSGI
# https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/
# -----------------------------------------------------------------------------

WSGI_APPLICATION = "packman.wsgi.application"


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases
# -----------------------------------------------------------------------------

DATABASES = {"default": env.db("DATABASE_URL", default="sqlite:///db.sqlite3")}


# CACHES
# https://docs.djangoproject.com/en/3.2/ref/settings/#caches
# ------------------------------------------------------------------------------

CACHES = {
    "default": env.cache("CACHE_URL", default="locmemcache://"),
}


# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators
# -----------------------------------------------------------------------------

PASSWORD_HASHERS = [
    # https://docs.djangoproject.com/en/3.2/topics/auth/passwords/#using-argon2-with-django
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Sites Framework
# https://docs.djangoproject.com/en/3.2/ref/contrib/sites/#enabling-the-sites-framework
# -----------------------------------------------------------------------------

SITE_ID = 1


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/
# -----------------------------------------------------------------------------

LANGUAGE_CODE = env("LANGUAGE_CODE", default="en-us")

LOCALE_PATHS = [BASE_DIR / "locale"]

TIME_ZONE = env("TIME_ZONE", default="UTC")

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/
# -----------------------------------------------------------------------------

STATIC_ROOT = env("DJANGO_STATIC_ROOT", default=BASE_DIR / "static_files")
STATIC_URL = "/static/"
STATICFILES_DIRS = [APPS_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# User uploaded files
# https://docs.djangoproject.com/en/3.2/topics/files/
# -----------------------------------------------------------------------------

MEDIA_URL = "/media/"
MEDIA_ROOT = env("DJANGO_MEDIA_ROOT", default=BASE_DIR / "media")


# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field
# -----------------------------------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Easy Thumbnails
# https://easy-thumbnails.readthedocs.io/en/3.2/usage/#thumbnail-aliases
# -----------------------------------------------------------------------------
THUMBNAIL_ALIASES = {
    "": {
        "320x320": {
            "size": (320, 320),
            "crop": "smart",
        },
    },
}
THUMBNAIL_DEFAULT_OPTIONS = {"crop": "smart"}
THUMBNAIL_SUBDIR = "thumbs"


# django-crispy-forms
# http://django-crispy-forms.readthedocs.io/en/3.2/install.html#template-packs
# -----------------------------------------------------------------------------

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"


# django-phonenumber-field
# https://github.com/stefanfoulis/django-phonenumber-field
# -----------------------------------------------------------------------------

PHONENUMBER_DEFAULT_REGION = "US"
PHONENUMBER_DEFAULT_FORMAT = "NATIONAL"


# LOGGING
# https://docs.djangoproject.com/en/3.2/ref/settings/#logging
# See https://docs.djangoproject.com/en/3.2/topics/logging for
# more details on how to customize your logging configuration.
# ------------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
        "spam_detected": {"()": "packman.core.logging.filters.ExcludeSpamDetected"},
    },
    "formatters": {"verbose": {"format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s"}},
    "handlers": {
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            # "formatter": "verbose",
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
# https://docs.djangoproject.com/en/3.2/topics/auth/customizing/#auth-custom-user
# -----------------------------------------------------------------------------

AUTH_USER_MODEL = "membership.Adult"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "pages:home"
LOGOUT_REDIRECT_URL = "pages:home"


# Authentication Backends
# https://docs.djangoproject.com/en/3.2/topics/auth/customizing/#specifying-authentication-backends
# -----------------------------------------------------------------------------

AUTHENTICATION_BACKENDS = [
    "packman.committees.backends.CommitteePermissionsBackend",
    "django.contrib.auth.backends.ModelBackend",
]


# django-tinymce
# https://django-tinymce.readthedocs.io/en/stable/installation.html#configuration
# -----------------------------------------------------------------------------

TINYMCE_DEFAULT_CONFIG = {
    "convert_urls": False,
    "default_link_target": "_blank",
    "height": "100%",
    "width": "100%",
    "imgagetools_cors_hosts": env("DJANGO_ALLOWED_HOSTS", default=[]),
    "link_quicklink": True,
    "link_title": False,
    "menubar": False,
    "plugins": "autoresize emoticons hr link lists table image imagetools media",
    "statusbar": False,
    "toolbar": "formatselect | bold italic underline strikethrough | alignleft aligncenter alignright | bullist numlist outdent indent | image media table | link unlink | removeformat",
}


# When does the site start a new year of scouting? Typically, this would be when
# cubs advance to the next rank.
# -----------------------------------------------------------------------------

PACK_YEAR_BEGIN_MONTH = env.int("PACK_YEAR_BEGIN_MONTH", default=9)  # September
PACK_YEAR_BEGIN_DAY = env.int("PACK_YEAR_BEGIN_DAY", default=1)  # 1st
PACK_DOMAIN_NAME = env("PACK_DOMAIN_NAME", default="example.com")
PACK_NAME = env("PACK_NAME", default="One Awesome Cub Scouts Pack")
PACK_SHORTNAME = env("PACK_SHORTNAME", default="Cub Pack")
PACK_TAGLINE = env("PACK_TAGLINE", default="We're Awesome")
PACK_LOCATION = env("PACK_LOCATION", default="United States of America")


# EMAIL
# https://docs.djangoproject.com/en/3.2/ref/settings/#email-backend
# https://django-environ.readthedocs.io/en/3.2/#email-settings
# ------------------------------------------------------------------------------

EMAIL_CONFIG = env.email_url("DJANGO_EMAIL_URL", default="consolemail://")
vars().update(EMAIL_CONFIG)

# https://docs.djangoproject.com/en/3.2/ref/settings/#default-from-email
DEFAULT_FROM_EMAIL = env("DJANGO_DEFAULT_FROM_EMAIL", default=f"{PACK_NAME} <noreply@{PACK_DOMAIN_NAME}>")

# https://docs.djangoproject.com/en/3.2/ref/settings/#server-email
SERVER_EMAIL = env("DJANGO_SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)

# https://docs.djangoproject.com/en/3.2/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = env("DJANGO_EMAIL_SUBJECT_PREFIX", default=f"[{PACK_SHORTNAME}] ")

# https://django-environ.readthedocs.io/en/3.2/#nested-lists
ADMINS = getaddresses([env("DJANGO_ADMINS", default="[]")])
MANAGERS = ADMINS
