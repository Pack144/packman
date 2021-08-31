from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .models import Order


class OrderListView(LoginRequiredMixin, ListView):
    model = Order


class OrderCreateView(LoginRequiredMixin, CreateView):
    model = Order


class OrderUpdateView(LoginRequiredMixin, UpdateView):
    model = Order


class OrderDeleteView(LoginRequiredMixin, DeleteView):
    model = Order


class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
