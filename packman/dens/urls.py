from django.urls import path

from . import views

app_name = "dens"
urlpatterns = [
    path("", views.DensListView.as_view(), name="list"),
    path("<int:pk>/", views.DenDetailView.as_view(), name="detail"),
]
