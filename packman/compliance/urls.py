from django.urls import path

from . import views

app_name = "compliance"

urlpatterns = [
    path("", views.ComplianceDashboardView.as_view(), name="dashboard"),
    path("<int:year>/", views.ComplianceDashboardView.as_view(), name="dashboard_by_year"),
    path("my-family/", views.MyFamilyComplianceView.as_view(), name="my_family"),
    path("my-family/<int:year>/", views.MyFamilyComplianceView.as_view(), name="my_family_by_year"),
    path("family/<uuid:pk>/", views.FamilyComplianceView.as_view(), name="family_detail"),
    path("family/<uuid:pk>/<int:year>/", views.FamilyComplianceView.as_view(), name="family_detail_by_year"),
    path("requirement/<slug:slug>/", views.RequirementRosterView.as_view(), name="roster"),
    path("requirement/<slug:slug>/<int:year>/", views.RequirementRosterView.as_view(), name="roster_by_year"),
]
