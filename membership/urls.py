from django.urls import path

from .views import (MemberList, AdultMemberList, AdultMemberCreate, AdultMemberDetail, AdultMemberUpdate,
                    ChildMemberList, ChildMemberCreate, ChildMemberDetail, ChildMemberUpdate, FamilyUpdate,
                    MemberSearchResultsList)

urlpatterns = [
    path('', MemberList.as_view(), name='member_list'),
    path('my-family/', FamilyUpdate.as_view(), name='family_update'),
    path('adults/', AdultMemberList.as_view(), name='parent_list'),
    path('adult/add/', AdultMemberCreate.as_view(), name='parent_create'),
    path('adults/<slug:slug>/', AdultMemberDetail.as_view(), name='parent_detail'),
    path('adult/<uuid:pk>/update/', AdultMemberUpdate.as_view(), name='parent_update'),
    path('cubs/', ChildMemberList.as_view(), name='scout_list'),
    path('cub/add/', ChildMemberCreate.as_view(), name='scout_create'),
    path('cubs/<slug:slug>/', ChildMemberDetail.as_view(), name='scout_detail'),
    path('cub/<uuid:pk>/update/', ChildMemberUpdate.as_view(), name='scout_update'),
    path('search/', MemberSearchResultsList.as_view(), name='member_search_results'),
]
