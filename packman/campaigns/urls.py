from django.urls import path, re_path

from .views import (
    OrderCreateView,
    OrderDeleteView,
    OrderDetailView,
    OrderListView,
    OrderUpdateView,
    OrderReportView,
    ProductListView,
    update_order,
    PrizeListView, PrizeSelectionView, update_prize_selection,
)

app_name = "campaigns"
urlpatterns = [
    path("", OrderListView.as_view(), name="order_list"),
    path("api/v1/update_order", update_order, name="api_update"),
    path("api/v1/update_prize_selection", update_prize_selection, name="api_update_prize_selection"),
    path("new/", OrderCreateView.as_view(), name="order_create"),
    path("products/", ProductListView.as_view(), name="product_list"),
    path("prizes/", PrizeListView.as_view(), name="prize_list"),
    path("prize/selection/", PrizeSelectionView.as_view(), name="prize_selection"),
    path("prize/selection/<slug:slug>/", PrizeSelectionView.as_view(), name="prize_selection"),
    path("<int:campaign>/", OrderListView.as_view(), name="order_list_by_campaign"),
    path("<uuid:pk>/", OrderDetailView.as_view(), name="order_detail"),
    path("<uuid:pk>/edit/", OrderUpdateView.as_view(), name="order_update"),
    path("<uuid:pk>/delete/", OrderDeleteView.as_view(), name="order_delete"),
    path("reports/", OrderReportView.as_view(), name="order_report"),
    re_path(r"^reports/(?P<campaign>[0-9]{4})/", OrderReportView.as_view(), name="order_report_by_campaign"),
]
