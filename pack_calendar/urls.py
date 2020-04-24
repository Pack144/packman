from django.urls import path

from .views import EventListView, EventDetailView
from .feeds import EventFeed

urlpatterns = [
    path('', EventListView.as_view(), name='event_list'),
    path('<uuid:pk>/', EventDetailView.as_view(), name='event_detail'),
    path(f'feed/<uuid:family>/{EventFeed.file_name}', EventFeed(), name='event_feed'),
]
