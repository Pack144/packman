from django.urls import path

from . import feeds, views

app_name = "calendars"
urlpatterns = [
    path("", views.EventListView.as_view(), name="list"),
    path("<uuid:pk>/", views.EventDetailView.as_view(), name="detail"),
    path("<uuid:pk>/edit/", views.EventUpdateView.as_view(), name="update"),
    path("<uuid:pk>/delete/", views.EventDeleteView.as_view(), name="delete"),
    path("add/", views.EventCreateView.as_view(), name="create"),
    path("archive/", views.EventArchiveView.as_view(), name="archive"),
    path("feed/<uuid:family_uuid>.ics", feeds.EventFeed(), name="feed"),
]
