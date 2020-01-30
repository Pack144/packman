from django.urls import path

from .views import HomePageView, AboutPageView, HistoryPageView, SignUpPageView, DynamicPageView, DynamicPageUpdateView

urlpatterns = [
    path('', HomePageView.as_view(), name='home_page'),
    path('about/', AboutPageView.as_view(), name='about_page'),
    path('history/', HistoryPageView.as_view(), name='history_page'),
    path('signup/', SignUpPageView.as_view(), name='signup'),
    path('<slug:slug>/', DynamicPageView.as_view(), name='dynamic_page'),
    path('<slug:slug>/edit', DynamicPageUpdateView.as_view(), name='dynamic_page_update'),
]
