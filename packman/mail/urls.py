from django.urls import path

from .views import (
    MessageArchiveView,
    MessageCreateView,
    MessageDetailView,
    MessageDraftsView,
    MessageInboxView,
    MessageSentView,
    MessageTrashView,
    MessageUpdateView,
)

app_name = "mail"
urlpatterns = [
    path("", MessageInboxView.as_view(), name="inbox"),
    path("compose/", MessageCreateView.as_view(), name="create"),
    path("sent/", MessageSentView.as_view(), name="sent"),
    path("archives/", MessageArchiveView.as_view(), name="archives"),
    path("trash/", MessageTrashView.as_view(), name="trash"),
    path("drafts/", MessageDraftsView.as_view(), name="drafts"),
    path("<uuid:pk>/", MessageDetailView.as_view(), name="detail"),
    path("<uuid:pk>/edit/", MessageUpdateView.as_view(), name="update"),
]
