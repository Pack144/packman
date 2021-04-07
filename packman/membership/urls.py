from django.urls import path

from .views import (
    AdultCreate,
    AdultDetail,
    AdultList,
    AdultUpdate,
    MemberList,
    MyFamilyDetail,
    MemberSearchResultsList,
    ScoutCreate,
    ScoutDetail,
    ScoutList,
    ScoutUpdate,
)

app_name = "membership"
urlpatterns = [
    path(
        "",
        MemberList.as_view(),
        name="all",
    ),
    path(
        "adults/",
        AdultList.as_view(),
        name="parents",
    ),
    path(
        "adult/add/",
        AdultCreate.as_view(),
        name="parent_create",
    ),
    path(
        "adults/<slug:slug>/",
        AdultDetail.as_view(),
        name="parent_detail",
    ),
    path(
        "adult/<uuid:pk>/update/",
        AdultUpdate.as_view(),
        name="parent_update",
    ),
    path(
        "cubs/",
        ScoutList.as_view(),
        name="scouts",
    ),
    path(
        "cub/add/",
        ScoutCreate.as_view(),
        name="scout_create",
    ),
    path(
        "cubs/<slug:slug>/",
        ScoutDetail.as_view(),
        name="scout_detail",
    ),
    path(
        "cub/<uuid:pk>/update/",
        ScoutUpdate.as_view(),
        name="scout_update",
    ),
    path(
        "search/",
        MemberSearchResultsList.as_view(),
        name="search_results",
    ),
    path("my-family/", MyFamilyDetail.as_view(), name="my-family"),
]
