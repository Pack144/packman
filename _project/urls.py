"""_project URL Configuration

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
from django.urls import path, include
from django.views import defaults as default_views


urlpatterns = [
    # Django admin
    path('pack-administration/', admin.site.urls),

    # Account management
    path('members/', include('allauth.urls')),

    # Local Apps
    path('dens/', include('dens.urls')),
    path('documents/', include('documents.urls')),
    path('events/', include('pack_calendar.urls')),
    path('members/', include('membership.urls')),
    path('', include('pages.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
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
