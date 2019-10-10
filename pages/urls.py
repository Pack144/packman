from django.urls import path

from .views import HomePageView, AboutPageView, HistoryPageView

urlpatterns = [
    path('', HomePageView.as_view(), name='home_page'),
    path('about/', AboutPageView.as_view(), name='about_page'),
    path('history/', HistoryPageView.as_view(), name='history_page'),
]
