from .base import *

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/stable/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="django-insecure-c#p2tsup@!p3yjxxoi9dbk)xb_iq1e5*_x&n)d$!*hc8@wuh*f",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DJANGO_DEBUG", default=True)

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

# Django Extensions
# https://django-extensions.readthedocs.io/en/latest/
INSTALLED_APPS += ["django_extensions"]

# Django Debug Toolbar
# https://django-debug-toolbar.readthedocs.io/en/latest/
INSTALLED_APPS += ["debug_toolbar"]
MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
INTERNAL_IPS = env.list("INTERNAL_IPS", default=["127.0.0.1"])

# Whitenoise
# http://whitenoise.evans.io/en/latest/django.html#using-whitenoise-in-development
INSTALLED_APPS += ["whitenoise.runserver_nostatic"]

# Crispy Forms
CRISPY_FAIL_SILENTLY = not DEBUG
