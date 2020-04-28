from django.urls import path

from .views import CommitteeDetail, CommitteesList


urlpatterns = [
    path(
        '',
        CommitteesList.as_view(),
        name='committees_list'
    ),
    path(
        '<int:year>/',
        CommitteesList.as_view(),
        name='committees_list_by_year'
    ),
    path(
        '<slug:slug>/',
        CommitteeDetail.as_view(),
        name='committee_detail'
    ),
    path(
        '<slug:slug>/<int:year>/',
        CommitteeDetail.as_view(),
        name='committee_detail_by_year'
    ),
]
