from django.urls import path

from . import views

app_name = "membership"
urlpatterns = [
    path("", views.MemberList.as_view(), name="all"),
    path("adults/", views.AdultList.as_view(), name="parents"),
    path("adult/add/", views.AdultCreate.as_view(), name="parent_create"),
    path("adults/<slug:slug>/", views.AdultDetail.as_view(), name="parent_detail"),
    path("adult/<uuid:pk>/update/", views.AdultUpdate.as_view(), name="parent_update"),
    path("cubs/", views.ScoutList.as_view(), name="scouts"),
    path("cub/add/", views.ScoutCreate.as_view(), name="scout_create"),
    path("cubs/<slug:slug>/", views.ScoutDetail.as_view(), name="scout_detail"),
    path("cub/<uuid:pk>/update/", views.ScoutUpdate.as_view(), name="scout_update"),
    path("search/", views.MemberSearchResultsList.as_view(), name="search_results"),
    path("my-family/", views.MyFamilyDetail.as_view(), name="my-family"),
]
