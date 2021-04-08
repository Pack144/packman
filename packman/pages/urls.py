from django.urls import path

from . import views


app_name = "pages"
urlpatterns = [
    path("", views.HomePageView.as_view(), name="home",),
    path("about/", views.AboutPageView.as_view(), name="about"),
    path("history/", views.HistoryPageView.as_view(), name="history"),
    path("signup/", views.SignUpPageView.as_view(), name="signup"),
    path("contact-us/", views.ContactPageView.as_view(), name="contact"),
    path("<slug:slug>/", views.PageDetailView.as_view(), name="detail"),
    path("<slug:slug>/edit", views.PageUpdateView.as_view(), name="update"),
    path("api/v1/pages/link_list/", views.get_link_list, name="link_list"),
]
