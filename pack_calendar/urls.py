from django.urls import path

from .views import EventListView, EventDetailView
from .feeds import EventFeed

urlpatterns = [
    path('', EventListView.as_view(), name='event_list'),
    path('feed/pack_calendar.ics', EventFeed(), name='event_feed'),
    path('<uuid:pk>/', EventDetailView.as_view(), name='event_detail')
]
