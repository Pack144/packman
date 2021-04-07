from django.urls import path

from .views import (
    AboutPageView,
    ContactPageView,
    PageUpdateView,
    PageDetailView,
    HistoryPageView,
    HomePageView,
    SignUpPageView,
)

app_name = "pages"
urlpatterns = [
    path(
        "",
        HomePageView.as_view(),
        name="home",
    ),
    path("about/", AboutPageView.as_view(), name="about"),
    path("history/", HistoryPageView.as_view(), name="history"),
    path("signup/", SignUpPageView.as_view(), name="signup"),
    path("contact-us/", ContactPageView.as_view(), name="contact"),
    path("<slug:slug>/", PageDetailView.as_view(), name="detail"),
    path("<slug:slug>/edit", PageUpdateView.as_view(), name="update"),
]
