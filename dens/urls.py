from django.urls import path

from .views import DenDetailView, DensListView

path('dens/', DensListView.as_view(), name='dens-list'),
path('den/<int:pk>', DenDetailView.as_view(), name='den-detail'),
