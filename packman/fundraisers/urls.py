from django.urls import path

from .views import OrderCreateView, OrderDeleteView, OrderDetailView, OrderListView, OrderUpdateView

app_name = "fundraisers"
urlpatterns = [
    path("", OrderListView.as_view(), name="order_list"),
    path("orders/new/", OrderCreateView.as_view(), name="order_create"),
    path("orders/<uuid:pk>/", OrderDetailView.as_view(), name="order_detail"),
    path("orders/<uuid:pk>/edit/", OrderUpdateView.as_view(), name="order_update"),
    path("orders/<uuid:pk>/delete/", OrderDeleteView.as_view(), name="order_delete"),
]
