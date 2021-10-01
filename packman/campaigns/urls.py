from django.urls import path

from .views import OrderCreateView, OrderDeleteView, OrderDetailView, OrderListView, OrderUpdateView, ProductListView, update_order

app_name = "campaigns"
urlpatterns = [
    path("", ProductListView.as_view(), name="product_list"),
    path("orders/", OrderListView.as_view(), name="order_list"),
    path("orders/<int:year>/", OrderListView.as_view(), name="order_list_by_year"),
    path("orders/new/", OrderCreateView.as_view(), name="order_create"),
    path("orders/<uuid:pk>/", OrderDetailView.as_view(), name="order_detail"),
    path("orders/<uuid:pk>/edit/", OrderUpdateView.as_view(), name="order_update"),
    path("orders/<uuid:pk>/delete/", OrderDeleteView.as_view(), name="order_delete"),
    path("api/v1/update_order", update_order, name="api_update"),
]
