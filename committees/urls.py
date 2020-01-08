from django.urls import path

from . import views


urlpatterns = [
    path('', views.CommitteesList.as_view(), name='committees_list'),
    path('<int:year>/', views.CommitteesList.as_view(), name='committees_list_by_year'),
    path('<slug:slug>/', views.CommitteeDetail.as_view(), name='committee_detail'),
    path('<slug:slug>/<int:year>/', views.CommitteeDetail.as_view(), name='committee_detail_by_year'),
]
