from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import CustomerForm, OrderForm, OrderItemFormSet
from .mixins import UserIsSellerFamilyTest
from .models import Campaign, Order, Prize, Product


class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = "campaigns/order_list.html"

    def get_queryset(self):
        return (
            super().get_queryset().filter(seller__family=self.request.user.family, campaign=Campaign.objects.latest())
        )


class OrderCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Order
    form_class = OrderForm
    success_message = _("Your order was successful.")
    template_name = "campaigns/order_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["product_list"] = Product.objects.filter(campaign=Campaign.get_latest())
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

    def form_valid(self, form):
        context = self.get_context_data(form=form)
        customer_form = context["customer_form"]
        items_formset = context["items_formset"]
        if customer_form.is_valid() and items_formset.is_valid():
            form.instance.customer = customer_form.save()
            self.object = form.save()
            items_formset.instance = self.object
            items_formset.save()
            return super().form_valid(form)
        return super().form_invalid(form)


class OrderUpdateView(UserIsSellerFamilyTest, SuccessMessageMixin, UpdateView):
    model = Order
    form_class = OrderForm
    success_message = _("You order was updated successfully.")
    template_name = "campaigns/order_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["product_list"] = Product.objects.filter(campaign=Campaign.get_latest())
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
            return super().form_valid(form)
        return super().form_invalid(form)


class OrderDeleteView(UserIsSellerFamilyTest, DeleteView):
    model = Order


class OrderDetailView(UserIsSellerFamilyTest, DetailView):
    model = Order
    template_name = "campaigns/order_detail.html"


class PrizeListView(LoginRequiredMixin, ListView):
    model = Prize
    template_name = "campaigns/prize_list.html"

    def get_queryset(self):
        return super().get_queryset().filter(campaign=Campaign.objects.latest())
