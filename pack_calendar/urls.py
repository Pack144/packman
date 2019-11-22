from django.urls import path

from .views import EventListView

urlpatterns = [
    path('', EventListView.as_view(), name='event_list'),
]
