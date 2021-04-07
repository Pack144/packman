from django.urls import path

from . import feeds, views

app_name = "calendars"
urlpatterns = [
    path("", views.EventListView.as_view(), name="list"),
    path("<uuid:pk>/", views.EventDetailView.as_view(), name="detail"),
    path("archive/", views.EventArchiveView.as_view(), name="archive"),
    path("feed/<uuid:family_uuid>.ics", feeds.EventFeed(), name="feed"),
]
