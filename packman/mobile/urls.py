from django.urls import path

from . import api, views

app_name = "mobile"
urlpatterns = [
    path("", views.AppShellView.as_view(), name="index"),
    path("sw.js", views.ServiceWorkerView.as_view(), name="service-worker"),
    path("manifest.webmanifest", views.WebManifestView.as_view(), name="manifest"),
    path("api/home/", api.HomeView.as_view(), name="api-home"),
    path("api/dens/mine/", api.MyDensView.as_view(), name="api-dens-mine"),
    path("api/dens/", api.DenListView.as_view(), name="api-dens"),
    path("api/dens/<int:number>/", api.DenDetailView.as_view(), name="api-den-detail"),
    path("api/search/", api.SearchView.as_view(), name="api-search"),
    path("api/members/<slug:slug>/", api.MemberDetailView.as_view(), name="api-member-detail"),
]
