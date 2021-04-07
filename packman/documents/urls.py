from django.urls import path

from . import views

app_name = "documents"
urlpatterns = [
    path("", views.DocumentListView.as_view(), name="list"),
]
