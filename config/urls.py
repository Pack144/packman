"""config URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views import defaults as default_views
from django.views.generic import RedirectView

urlpatterns = [
    # Django admin
    path("administration/doc/", include("django.contrib.admindocs.urls")),
    path("administration/", admin.site.urls),
    # Account management
    path("members/", include("django.contrib.auth.urls")),
    path(
        ".well-known/change-password/",
        RedirectView.as_view(pattern_name="password_change"),
    ),
    # Third party apps
    path("t/", include("tinymce.urls")),
    # Local Apps
    path("committees/", include("packman.committees.urls")),
    path("dens/", include("packman.dens.urls")),
    path("documents/", include("packman.documents.urls")),
    path("calendar/", include("packman.calendars.urls")),
    path("mail/", include("packman.mail.urls")),
    path("members/", include("packman.membership.urls")),
    path("", include("packman.pages.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ] + urlpatterns
