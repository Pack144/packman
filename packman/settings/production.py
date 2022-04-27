from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("DJANGO_SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/stable/ref/settings/#csrf-cookie-httponly
CSRF_COOKIE_HTTPONLY = env.bool("DJANGO_CSRF_COOKIE_HTTPONLY", default=True)
# https://docs.djangoproject.com/en/stable/ref/settings/#csrf-cookie-secure
CSRF_COOKIE_SECURE = env.bool("DJANGO_CSRF_COOKIE_SECURE", default=True)
# https://docs.djangoproject.com/en/stable/ref/settings/#secure-browser-xss-filter
SECURE_BROWSER_XSS_FILTER = env.bool("DJANGO_SECURE_BROWSER_XSS_FILTER", default=True)
# https://docs.djangoproject.com/en/stable/ref/middleware/#x-content-type-options-nosniff
SECURE_CONTENT_TYPE_NOSNIFF = env.bool("DJANGO_SECURE_CONTENT_TYPE_NOSNIFF", default=True)
# https://docs.djangoproject.com/en/stable/ref/settings/#secure-hsts-include-subdomains
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)
# https://docs.djangoproject.com/en/stable/ref/settings/#secure-hsts-preload
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)
# https://docs.djangoproject.com/en/stable/ref/settings/#secure-hsts-seconds
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=60)
# https://docs.djangoproject.com/en/stable/ref/settings/#secure-ssl-redirect
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=False)
# https://docs.djangoproject.com/en/stable/ref/settings/#session-cookie-httponly
SESSION_COOKIE_HTTPONLY = env.bool("DJANGO_SESSION_COOKIE_HTTPONLY", default=True)
# https://docs.djangoproject.com/en/stable/ref/settings/#session-cookie-secure
SESSION_COOKIE_SECURE = env.bool("DJANGO_SESSION_COOKIE_SECURE", default=True)
