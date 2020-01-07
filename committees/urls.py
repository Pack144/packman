from django.urls import path

from . import views


urlpatterns = [
    path('', views.CommitteesList.as_view(), name='committees_list'),
    path('<slug:slug>/', views.CommitteeDetail.as_view(), name='committee_detail'),
]
