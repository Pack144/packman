from django.urls import path

from .views import MessageDetailView, MessageCreateView, MessageInboxView, MessageUpdateView

app_name = "mail"
urlpatterns = [
    path("", MessageInboxView.as_view(), name="inbox"),
    path("compose/", MessageCreateView.as_view(), name="create"),
    path("<uuid:pk>/", MessageDetailView.as_view(), name="detail"),
    path("<uuid:pk>/edit/", MessageUpdateView.as_view(), name="update"),
]
