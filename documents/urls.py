from django.urls import path

from .views import DocumentListView

urlpatterns = [
    path('', DocumentListView.as_view(), name='document_list'),
]
