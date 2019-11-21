from django.urls import path

from .views import MemberListView, ParentListView, ParentCreateView, ParentDetailView, ParentUpdateView
from .views import ScoutListView, ScoutCreateView, ScoutDetailView, ScoutUpdateView, FamilyUpdateView

urlpatterns = [
    path('', MemberListView.as_view(), name='member_list'),
    path('my-family/', FamilyUpdateView.as_view(), name='family_update'),
    path('parents/', ParentListView.as_view(), name='parent_list'),
    path('parents/add/', ParentCreateView.as_view(), name='parent_create'),
    path('parents/<uuid:pk>/', ParentDetailView.as_view(), name='parent_detail'),
    path('parents/<uuid:pk>/update/', ParentUpdateView.as_view(), name='parent_update'),
    path('scouts/', ScoutListView.as_view(), name='scout_list'),
    path('scouts/add/', ScoutCreateView.as_view(), name='scout_create'),
    path('scouts/<uuid:pk>/', ScoutDetailView.as_view(), name='scout_detail'),
    path('scouts/<uuid:pk>/update/', ScoutUpdateView.as_view(), name='scout_update'),
]
