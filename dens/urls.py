from django.urls import path

from .views import DenDetailView, DensListView

app_name = 'dens'
urlpatterns = [
    path('', DensListView.as_view(), name='list'),
    path('<int:pk>/', DenDetailView.as_view(), name='detail'),
]
