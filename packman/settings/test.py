from .base import *

print(f"Using settings '{__name__}'")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

# https://docs.djangoproject.com/en/3.2/ref/settings/#password-hashers
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# https://docs.djangoproject.com/en/3.2/ref/contrib/staticfiles/
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# http://whitenoise.evans.io/en/stable/django.html#whitenoise-makes-my-tests-run-slow
WHITENOISE_AUTOREFRESH = True
