import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from packman.calendars.models import PackYear

from .forms import CustomerForm, OrderForm, OrderItemFormSet, SimpleCustomerForm
from .mixins import UserIsSellerFamilyTest
from .models import Campaign, Order, Prize, Product, OrderItem, Customer
from .utils import email_receipt


class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = "campaigns/order_list.html"

    def get_queryset(self):
        campaign = (
            Campaign.objects.get(year=PackYear.get_pack_year(self.kwargs["campaign"])["end_date"].year)
            if "campaign" in self.kwargs
            else Campaign.objects.current()
        )

        return (
            super().get_queryset().prefetch_related("items").filter(seller__family=self.request.user.family,
                                                                    campaign=campaign).order_by(
                "-seller__date_of_birth", "date_added")
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["campaigns"] = {
            "available": Campaign.objects.filter(orders__seller__family=self.request.user.family).distinct(),
            "current": Campaign.objects.current(),
            "viewing": (
                Campaign.objects.get(year=PackYear.get_pack_year(self.kwargs["campaign"])["end_date"].year)
                if "campaign" in self.kwargs
                else Campaign.objects.current()
            ),
        }
        return context


class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = "campaigns/customer_form.html"


class OrderCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Order
    form_class = OrderForm
    success_message = _("Your order was successful.")
    template_name = "campaigns/order_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["product_list"] = Product.objects.current()

        if self.request.POST:
            context["customer_form"] = CustomerForm(self.request.POST)
            context["items_formset"] = OrderItemFormSet(self.request.POST)
        else:
            context["customer_form"] = CustomerForm()
            context["items_formset"] = OrderItemFormSet()
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        if "cub" in self.request.GET:
            initial["seller"] = self.request.GET.get("cub")
        return initial

    def form_valid(self, form):
        context = self.get_context_data(form=form)
        customer_form = context["customer_form"]
        items_formset = context["items_formset"]
        if customer_form.is_valid() and items_formset.is_valid():
            form.instance.customer = customer_form.save()
            self.object = form.save()
            items_formset.instance = self.object
            items_formset.save()
            if self.object.customer.email:
                email_receipt(self.object)
            return super().form_valid(form)
        return super().form_invalid(form)


class OrderUpdateView(UserIsSellerFamilyTest, SuccessMessageMixin, UpdateView):
    model = Order
    form_class = OrderForm
    success_message = _("You order was updated successfully.")
    template_name = "campaigns/order_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["product_list"] = Product.objects.filter(campaign=Campaign.get_latest()).prefetch_related(
            Prefetch("orders", queryset=OrderItem.objects.filter(order=self.object)))
        if self.request.POST:
            context["customer_form"] = CustomerForm(self.request.POST, instance=self.object.customer)
            context["items_formset"] = OrderItemFormSet(self.request.POST, instance=self.object)
        else:
            context["customer_form"] = CustomerForm(instance=self.object.customer)
            context["items_formset"] = OrderItemFormSet(instance=self.object)
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        context = self.get_context_data(form=form)
        customer_form = context["customer_form"]
        items_formset = context["items_formset"]
        if customer_form.is_valid() and items_formset.is_valid():
            form.instance.customer = customer_form.save()
            self.object = form.save()

            items_formset.instance = self.object
            items_formset.save()
            if self.object.items.exists() or self.object.donation:
                return super().form_valid(form)
            else:
                form.add_error(None, ValidationError(_("You haven't ordered anything."), code="incomplete"))
                return super().form_invalid(form)
        return super().form_invalid(form)


class OrderDeleteView(UserIsSellerFamilyTest, DeleteView):
    model = Order
    template_name = "campaigns/order_confirm_delete.html"
    success_url = reverse_lazy("campaigns:order_list")

    def delete(self, request, *args, **kwargs):
        message = _("The order has been successfully deleted.") % {"page": self.get_object()}
        messages.success(request, message, "danger")
        return super().delete(request, *args, **kwargs)


class OrderDetailView(DetailView):
    model = Order
    template_name = "campaigns/order_detail.html"


class PrizeListView(LoginRequiredMixin, ListView):
    model = Prize
    template_name = "campaigns/prize_list.html"

    def get_queryset(self):
        return super().get_queryset().filter(campaign=Campaign.objects.latest())


class ProductListView(ListView):
    model = Product
    template_name = "campaigns/product_list.html"

    def get_queryset(self):
        return super().get_queryset().filter(campaign=Campaign.objects.current())


@login_required
def update_order(request):
    data = json.loads(request.body)
    action = data["action"]
    order = Order.objects.get(pk=data["orderId"])

    if action == "mark_paid":
        order.date_paid = timezone.now()
    elif action == "mark_unpaid":
        order.date_paid = None
    elif action == "mark_delivered":
        order.date_delivered = timezone.now()
    elif action == "mark_undelivered":
        order.date_delivered = None

    order.save()
    response = {"action": action, "order": order.pk}
    return JsonResponse(response)
