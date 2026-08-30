from django.urls import path

from . import api, views

app_name = "mobile"
urlpatterns = [
    path("", views.AppShellView.as_view(), name="index"),
    path("sw.js", views.ServiceWorkerView.as_view(), name="service-worker"),
    path("manifest.webmanifest", views.WebManifestView.as_view(), name="manifest"),
    path("api/pack_directory/", api.DirectoryView.as_view(), name="api-directory"),
    path("api/event/", api.EventView.as_view(), name="api-event"),
    path("api/requirements/", api.RequirementsView.as_view(), name="api-requirements"),
]
