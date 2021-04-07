from django.urls import path

from . import views

app_name = "committees"
urlpatterns = [
    path("", views.CommitteesList.as_view(), name="list"),
    path("<int:year>/", views.CommitteesList.as_view(), name="list_by_year"),
    path("<slug:slug>/", views.CommitteeDetail.as_view(), name="detail"),
    path("<slug:slug>/<int:year>/", views.CommitteeDetail.as_view(), name="detail_by_year"),
]
