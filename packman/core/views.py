import platform
import sys
from importlib.metadata import distributions
from urllib.parse import quote

import django
from django.contrib import admin
from django.core.exceptions import SuspiciousOperation
from django.db import connection
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _


def system_info(request):
    # OS
    try:
        os_release = platform.freedesktop_os_release()
        os_name = os_release.get("PRETTY_NAME", platform.platform())
    except AttributeError, OSError:
        os_name = platform.platform()

    # Database
    db_vendor = connection.vendor
    with connection.cursor() as cursor:
        if db_vendor == "postgresql":
            cursor.execute("SELECT version()")
            db_version = cursor.fetchone()[0]
        elif db_vendor == "sqlite":
            cursor.execute("SELECT sqlite_version()")
            db_version = f"SQLite {cursor.fetchone()[0]}"
        elif db_vendor == "mysql":
            cursor.execute("SELECT VERSION()")
            db_version = f"MySQL {cursor.fetchone()[0]}"
        else:
            db_version = db_vendor

    packages = sorted(
        ((d.metadata["Name"], d.metadata["Version"]) for d in distributions()),
        key=lambda x: x[0].lower(),
    )

    context = {
        **admin.site.each_context(request),
        "title": _("System Information"),
        "python_version": sys.version,
        "django_version": django.__version__,
        "os_name": os_name,
        "db_vendor": db_vendor,
        "db_version": db_version,
        "packages": packages,
    }
    return render(request, "admin/system_info.html", context)


def legacy_admin_redirect(request, path=""):
    if path.startswith("/") or "\\" in path or any(part in (".", "..") for part in path.split("/")):
        raise SuspiciousOperation("Invalid legacy admin redirect path.")
    target = f"{reverse('admin:index')}{quote(path, safe='/')}"
    if query := request.META.get("QUERY_STRING"):
        target = f"{target}?{query}"
    if not url_has_allowed_host_and_scheme(target, allowed_hosts=set()):
        raise SuspiciousOperation("Unsafe legacy admin redirect destination.")
    return redirect(target, permanent=True, preserve_request=True)
