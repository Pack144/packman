from django.urls import path

from .views import DenDetailView, DensListView

path('dens/', DensListView.as_view(), name='dens_list'),
path('den/<int:pk>', DenDetailView.as_view(), name='den_detail'),
