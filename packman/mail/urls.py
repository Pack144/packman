from django.urls import path

from .views import MessageDetailView


app_name = "mail"
urlpatterns = [
    path("<uuid:pk>/", MessageDetailView.as_view(), name="detail"),
]
