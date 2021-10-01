from django.urls import path

from .views import OrderCreateView, OrderDeleteView, OrderDetailView, OrderListView, OrderUpdateView, ProductListView, update_order

app_name = "campaigns"
urlpatterns = [
    path("", OrderListView.as_view(), name="order_list"),
    path("<int:year>/", OrderListView.as_view(), name="order_list_by_year"),
    path("new/", OrderCreateView.as_view(), name="order_create"),
    path("<uuid:pk>/", OrderDetailView.as_view(), name="order_detail"),
    path("<uuid:pk>/edit/", OrderUpdateView.as_view(), name="order_update"),
    path("<uuid:pk>/delete/", OrderDeleteView.as_view(), name="order_delete"),
    path("products/", ProductListView.as_view(), name="product_list"),
    path("api/v1/update_order", update_order, name="api_update"),
]
