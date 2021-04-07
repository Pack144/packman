from django.urls import path

from .views import CommitteeDetail, CommitteesList

app_name = "committees"
urlpatterns = [
    path("", CommitteesList.as_view(), name="list"),
    path("<int:year>/", CommitteesList.as_view(), name="list_by_year"),
    path("<slug:slug>/", CommitteeDetail.as_view(), name="detail"),
    path("<slug:slug>/<int:year>/", CommitteeDetail.as_view(), name="detail_by_year"),
]
