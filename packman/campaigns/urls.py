from django.urls import path, re_path

from .reports import generate_weekly_report, turn_in_night_report
from .views import (
    OrderCreateView,
    OrderDeleteView,
    OrderDetailView,
    OrderListView,
    OrderReportView,
    OrderSlipView,
    OrderUpdateView,
    PlaceMarkerTemplateView,
    PrizeSelectionReportView,
    PrizeSelectionView,
    ProductListView,
    PullSheetTemplateView,
    update_order,
    update_prize_selection,
)

app_name = "campaigns"
urlpatterns = [
    path("", OrderListView.as_view(), name="order_list"),
    path("api/v1/update_order", update_order, name="api_update"),
    path("api/v1/update_prize_selection", update_prize_selection, name="api_update_prize_selection"),
    path("new/", OrderCreateView.as_view(), name="order_create"),
    path("products/", ProductListView.as_view(), name="product_list"),
    path("prizes/", PrizeSelectionView.as_view(), name="prize_selection"),
    path("<int:campaign>/", OrderListView.as_view(), name="order_list_by_campaign"),
    path("<uuid:pk>/", OrderDetailView.as_view(), name="order_detail"),
    path("<uuid:pk>/edit/", OrderUpdateView.as_view(), name="order_update"),
    path("<uuid:pk>/delete/", OrderDeleteView.as_view(), name="order_delete"),
    path("reports/", OrderReportView.as_view(), name="order_report"),
    path("reports/order_slips/", OrderSlipView.as_view(), name="order_slips"),
    path("reports/place_markers/", PlaceMarkerTemplateView.as_view(), name="place_markers"),
    path("reports/prize_selections/", PrizeSelectionReportView.as_view(), name="prize_selection_report"),
    path("reports/pull_sheets/", PullSheetTemplateView.as_view(), name="pull_sheets"),
    path("reports/turn_in_night/", turn_in_night_report, name="turn_in_night"),
    path("reports/weekly/", generate_weekly_report, name="weekly_report"),
    re_path(r"^reports/(?P<campaign>[0-9]{4})/", OrderReportView.as_view(), name="order_report_by_campaign"),
]
