from django.urls import path

from .views import (
    HomePageView, AboutPageView, HistoryPageView, SignUpPageView,
    DynamicPageView, DynamicPageUpdateView, ContactPageView
)

app_name = 'pages'
urlpatterns = [
    path(
        '',
        HomePageView.as_view(),
        name='home',
    ),
    path(
        'about/',
        AboutPageView.as_view(),
        name='about'
    ),
    path(
        'history/',
        HistoryPageView.as_view(),
        name='history'
    ),
    path(
        'signup/',
        SignUpPageView.as_view(),
        name='signup'
    ),
    path(
        'contact-us/',
        ContactPageView.as_view(),
        name='contact'
    ),
    path(
        '<slug:slug>/',
        DynamicPageView.as_view(),
        name='dynamic_page'
    ),
    path(
        '<slug:slug>/edit',
        DynamicPageUpdateView.as_view(),
        name='dynamic_page_update'
    ),
]
