from django.urls import path

from .views import EventListView, EventDetailView
from .feeds import EventFeed

app_name = 'calendars'
urlpatterns = [
    path(
        '',
        EventListView.as_view(),
        name='list'
    ),
    path(
        '<uuid:pk>/',
        EventDetailView.as_view(),
        name='detail'
    ),
    path(
        'feed/<uuid:family_uuid>.ics',
        EventFeed(),
        name='feed'
    ),
]
