from django.urls import path

from .views import (MemberList, AdultList, AdultCreate, AdultDetail, AdultUpdate,
                    ScoutList, ScoutCreate, ScoutDetail, ScoutUpdate, FamilyUpdate,
                    MemberSearchResultsList)

urlpatterns = [
    path('', MemberList.as_view(), name='member_list'),
    path('my-family/', FamilyUpdate.as_view(), name='family_update'),
    path('adults/', AdultList.as_view(), name='parent_list'),
    path('adult/add/', AdultCreate.as_view(), name='parent_create'),
    path('adults/<slug:slug>/', AdultDetail.as_view(), name='parent_detail'),
    path('adult/<uuid:pk>/update/', AdultUpdate.as_view(), name='parent_update'),
    path('cubs/', ScoutList.as_view(), name='scout_list'),
    path('cub/add/', ScoutCreate.as_view(), name='scout_create'),
    path('cubs/<slug:slug>/', ScoutDetail.as_view(), name='scout_detail'),
    path('cub/<uuid:pk>/update/', ScoutUpdate.as_view(), name='scout_update'),
    path('search/', MemberSearchResultsList.as_view(), name='member_search_results'),
]
