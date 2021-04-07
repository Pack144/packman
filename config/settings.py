"""
Django settings for packman project.

Generated by 'django-admin startproject' using Django 2.2.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""
from pathlib import Path

import environ

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = Path(__file__).resolve().parent.parent
APPS_DIR = BASE_DIR / "packman"

env = environ.Env()
env_file = BASE_DIR / ".env"
if env_file.is_file():
    env.read_env(str(env_file))


# GENERAL
# ------------------------------------------------------------------------------
# SECURITY WARNING: keep the secret key used in production secret!
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="w98b46*7+i8+6$_3n(jfa6(7*j3%v*^u#at2$qknbgt4_eu_vg",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool("DJANGO_DEBUG", False)

# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

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
    "debug_toolbar",
    "django_extensions",
    "django_ical",
    "dynamic_formsets",
    "easy_thumbnails",
    "localflavor",
    "phonenumber_field",
    "tempus_dominus",
    "tinymce",
    # Local apps
    "packman.address_book.apps.AddressBookConfig",
    "packman.calendars.apps.CalendarsConfig",
    "packman.committees.apps.CommitteesConfig",
    "packman.core.apps.CoreConfig",
    "packman.dens.apps.DensConfig",
    "packman.documents.apps.DocumentsConfig",
    "packman.membership.apps.MembershipConfig",
    "packman.pages.apps.PagesConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.admindocs.middleware.XViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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
# https://docs.djangoproject.com/en/3.0/howto/deployment/wsgi/
# -----------------------------------------------------------------------------
WSGI_APPLICATION = "config.wsgi.application"

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases
# -----------------------------------------------------------------------------
DATABASES = {"default": env.db("DATABASE_URL", default="sqlite:///db.sqlite3")}

# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    "default": env.cache("CACHE_URL", default="locmemcache://"),
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
# https://docs.djangoproject.com/en/3.1/ref/contrib/sites/#enabling-the-sites-framework
# -----------------------------------------------------------------------------
SITE_ID = 1

# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/
# -----------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"

TIME_ZONE = "America/Los_Angeles"

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/
# -----------------------------------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [
    BASE_DIR / "node_modules",
    APPS_DIR / "static",
]
STATIC_ROOT = env("DJANGO_STATIC_ROOT", default=BASE_DIR / "static_files")
MEDIA_URL = "/media/"
MEDIA_ROOT = env("DJANGO_MEDIA_ROOT", default=BASE_DIR / "media")

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "pages:home"
LOGOUT_REDIRECT_URL = "pages:home"

# Used by apps such as debug_toolbar to determine from what IP addresses requests to display
# -----------------------------------------------------------------------------
INTERNAL_IPS = [
    "127.0.0.1",
]

# Easy Thumbnails
# https://easy-thumbnails.readthedocs.io/en/latest/usage/#thumbnail-aliases
# -----------------------------------------------------------------------------
THUMBNAIL_ALIASES = {
    "": {
        "80x80": {
            "size": (80, 80),
            "crop": "smart",
        },
        "320x320": {
            "size": (320, 320),
            "crop": "smart",
        },
    },
    "membership": {
        "thumbnail": {
            "size": (80, 80),
            "crop": "smart",
            "quality": 90,
        },
        "card": {
            "size": (320, 320),
            "crop": "smart",
            "quality": 90,
        },
    },
}
THUMBNAIL_SUBDIR = "thumbs"

# django-crispy-forms
# http://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
# -----------------------------------------------------------------------------
CRISPY_TEMPLATE_PACK = "bootstrap4"
CRISPY_FAIL_SILENTLY = not DEBUG

# django-phonenumber-field
# https://github.com/stefanfoulis/django-phonenumber-field
# -----------------------------------------------------------------------------
PHONENUMBER_DEFAULT_REGION = "US"
PHONENUMBER_DEFAULT_FORMAT = "NATIONAL"

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/3.0/ref/settings/#session-cookie-httponly
SESSION_COOKIE_HTTPONLY = env.bool("DJANGO_SESSION_COOKIE_HTTPONLY", default=True)
# https://docs.djangoproject.com/en/3.0/ref/settings/#csrf-cookie-httponly
CSRF_COOKIE_HTTPONLY = env.bool("CSRF_COOKIE_HTTPONLY", default=True)
# https://docs.djangoproject.com/en/3.0/ref/settings/#secure-browser-xss-filter
SECURE_BROWSER_XSS_FILTER = env.bool("SECURE_BROWSER_XSS_FILTER", default=True)
# https://docs.djangoproject.com/en/3.0/ref/settings/#x-frame-options
X_FRAME_OPTIONS = "DENY"
# https://docs.djangoproject.com/en/3.0/ref/middleware/#x-content-type-options-nosniff
SECURE_CONTENT_TYPE_NOSNIFF = env.bool(
    "DJANGO_SECURE_CONTENT_TYPE_NOSNIFF", default=True
)
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-seconds
# TODO: set this to 60 seconds first and then to 518400 once you prove the former works
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=60)
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-include-subdomains
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True
)
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-preload
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-secure
SESSION_COOKIE_SECURE = env.bool("DJANGO_SESSION_COOKIE_SECURE", default=True)
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-secure
CSRF_COOKIE_SECURE = env.bool("DJANGO_CSRF_COOKIE_SECURE", default=True)
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-ssl-redirect
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=False)

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
            "format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s"
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
AUTH_USER_MODEL = "membership.Adult"

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
TINYMCE_JS_URL = f"{STATIC_URL}tinymce/tinymce.min.js"
TINYMCE_DEFAULT_CONFIG = {
    "theme": "silver",
    "height": 600,
    "menubar": False,
    "plugins": "preview paste importcss searchreplace autolink autosave save directionality code visualblocks visualchars fullscreen image link media template codesample table charmap hr pagebreak nonbreaking anchor toc insertdatetime advlist lists wordcount imagetools textpattern noneditable help charmap quickbars emoticons",
    "toolbar": "undo redo | bold italic underline strikethrough | fontselect fontsizeselect formatselect | alignleft aligncenter alignright alignjustify | outdent indent |  numlist bullist | forecolor backcolor removeformat | charmap emoticons | fullscreen  preview save print | insertfile image media template link anchor codesample code",
    "imgagetools_cors_hosts": ALLOWED_HOSTS,
}

# django-tempus-dominus
# https://tempusdominus.github.io/bootstrap-4/
# https://github.com/FlipperPA/django-tempus-dominus
# -----------------------------------------------------------------------------
TEMPUS_DOMINUS_INCLUDE_ASSETS = False  # We'll use Yarn for this

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
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
# https://django-environ.readthedocs.io/en/latest/#email-settings
EMAIL_CONFIG = env.email_url("DJANGO_EMAIL_URL", default="consolemail://")
vars().update(EMAIL_CONFIG)

# https://docs.djangoproject.com/en/dev/ref/settings/#default-from-email
DEFAULT_FROM_EMAIL = env(
    "DJANGO_DEFAULT_FROM_EMAIL", default=f"{PACK_NAME} <noreply@{PACK_DOMAIN_NAME}>"
)
# https://docs.djangoproject.com/en/dev/ref/settings/#server-email
SERVER_EMAIL = env("DJANGO_SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = env(
    "DJANGO_EMAIL_SUBJECT_PREFIX", default=f"[{PACK_SHORTNAME}] "
)
# https://django-environ.readthedocs.io/en/latest/#nested-lists
ADMINS = [x.split(":") for x in env.list("DJANGO_ADMINS", default=[])]
MANAGERS = ADMINS
