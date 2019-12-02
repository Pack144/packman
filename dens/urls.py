from django.urls import path

from .views import DenDetailView, DensListView

urlpatterns = [
    path('', DensListView.as_view(), name='dens_list'),
    path('<int:pk>/', DenDetailView.as_view(), name='den_detail'),
]
