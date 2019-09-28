from django.urls import path

from .views import MemberDetailView, MemberListView, MemberUpdateView, ParentListView, ParentCreateView, \
    ScoutListView, ScoutCreateView

urlpatterns = [
    path('', MemberListView.as_view(), name='member_list'),
    path('<int:pk>', MemberDetailView.as_view(), name='member_detail'),
    path('<int:pk>/update/', MemberUpdateView.as_view(), name='member_update'),
    path('parents/', ParentListView.as_view(), name='parent_list'),
    path('parents/add/', ParentCreateView.as_view(), name='parent_create'),
    path('scouts/', ScoutListView.as_view(), name='scout_list'),
    path('scouts/add/', ScoutCreateView.as_view(), name='scout_add'),
]
