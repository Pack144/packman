import decimal
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.db.models import Count, Prefetch, Sum, Q
from django.db.models.functions import Coalesce, TruncDate
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, TemplateView, UpdateView

from packman.calendars.models import PackYear
from packman.dens.models import Den, Membership
from packman.membership.models import Scout

from .forms import CustomerForm, OrderForm, OrderItemFormSet, PrizeSelectionForm
from .mixins import UserIsSellerFamilyTest
from .models import Campaign, Order, OrderItem, Prize, PrizePoint, PrizeSelection, Product, Quota
from .utils import email_receipt


class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = "campaigns/order_list.html"

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.request.GET.get("filter") == "delivered":
            queryset = queryset.delivered()
        elif self.request.GET.get("filter") == "undelivered":
            queryset = queryset.undelivered()

        campaign = (
            Campaign.objects.get(year=PackYear.get_pack_year(self.kwargs["campaign"])["end_date"].year)
            if "campaign" in self.kwargs
            else Campaign.objects.current()
        )

        if self.request.user.family.is_seperated:
            queryset = queryset.filter(recorded_by=self.request.user)

        return (
            queryset.prefetch_related("seller", "customer", "recorded_by")
            .calculate_total()
            .filter(seller__family=self.request.user.family, campaign=campaign)
            .order_by("-seller__date_of_birth", "date_added")
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["campaigns"] = {
            "available": Campaign.objects.filter(Q(orders__seller__family=self.request.user.family) | Q(year=PackYear.objects.current())).distinct().order_by("-ordering_opens"),
            "current": Campaign.objects.current(),
            "viewing": (
                Campaign.objects.get(year=PackYear.get_pack_year(self.kwargs["campaign"])["end_date"].year)
                if "campaign" in self.kwargs
                else Campaign.objects.current()
            ),
        }
        return context


class OrderReportView(PermissionRequiredMixin, TemplateView):
    permission_required = "campaigns.generate_order_report"
    template_name = "campaigns/order_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["campaigns"] = {
            "available": Campaign.objects.filter(orders__seller__family=self.request.user.family).distinct(),
            "current": Campaign.objects.current(),
            "viewing": (
                Campaign.objects.get(year=PackYear.get_pack_year(int(self.kwargs["campaign"]))["end_date"].year)
                if "campaign" in self.kwargs
                else Campaign.objects.current()
            ),
        }
        orders = Order.objects.calculate_total().filter(campaign=context["campaigns"]["viewing"])
        context["report"] = {
            "count": orders.count(),
            "total": orders.totaled()["totaled"],
            "days": orders.annotate(date=TruncDate("date_added"))
            .order_by("date")
            .values("date")
            .annotate(count=Count("date"), order_total=Coalesce(Sum("total"), decimal.Decimal(0.00)))
            .values("date", "count", "order_total"),
        }
        return context


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
            form.instance.recorded_by = self.request.user
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
            Prefetch("orders", queryset=OrderItem.objects.filter(order=self.object))
        )
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


class PrizeSelectionView(LoginRequiredMixin, FormView):
    form_class = PrizeSelectionForm
    success_message = _("You prize selections were updated successfully.")
    template_name = "campaigns/prize_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        cubs = self.request.user.family.children.active()
        orders = (
            Order.objects.prefetch_related("seller")
            .calculate_total()
            .filter(seller__in=cubs, campaign=Campaign.objects.latest())
        )

        cub_list = []

        for cub in cubs:
            quota = Quota.objects.get(den=cub.current_den, campaign=Campaign.objects.latest()).target
            total = orders.filter(seller=cub).totaled()["totaled"]
            if total < quota:
                points_earned = 0
            elif total <= 2000:
                points_earned = PrizePoint.objects.filter(earned_at__lte=total).order_by("-earned_at").first().value
            else:
                points_earned = PrizePoint.objects.order_by("earned_at").last().value + int(
                    (total - PrizePoint.objects.order_by("earned_at").last().earned_at) / 100
                )
            points_spent = PrizeSelection.objects.filter(
                campaign=Campaign.objects.latest(), cub=cub
            ).calculate_total_points_spent()["spent"]

            # points_spent = PrizeSelection.objects.filter(campaign=Campaign.objects.current(), cub=cub).aggregate(
            #     spent=Coalesce(Sum("prize__points"), 0))["spent"]
            cub_list.append(
                {
                    "name": cub.short_name,
                    "pk": cub.pk,
                    "quota": quota,
                    "total": total,
                    "points": {
                        "earned": points_earned,
                        "spent": points_spent,
                        "remaining": points_earned - points_spent,
                    },
                }
            )

        context["prize_list"] = Prize.objects.filter(campaign=Campaign.objects.latest())
        context["cub_list"] = cub_list
        context["total"] = orders.totaled()["totaled"]
        return context


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


@login_required
def update_prize_selection(request):
    data = json.loads(request.body)
    action = data["action"]
    prize = Prize.objects.get(pk=data["prize"])
    cub = Scout.objects.get(pk=data["cub"])

    if action == "add":
        selection, created = PrizeSelection.objects.get_or_create(
            prize=prize,
            cub=cub,
        )
        if not created:
            selection.quantity += 1
            selection.save()

    elif action == "remove":
        selection = PrizeSelection.objects.get(
            prize=prize,
            cub=cub,
        )
        if selection.quantity <= 1:
            selection.delete()
        else:
            selection.quantity -= 1
            selection.save()

    response = {"action": action, "prize": prize.pk, "cub": cub.pk, "quantity": selection.quantity if selection else 0}
    return JsonResponse(response)


class PlaceMarkerTemplateView(PermissionRequiredMixin, TemplateView):
    permission_required = "campaigns.generate_order_report"
    template_name = "campaigns/reports/place_markers.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cub_list"] = (
            Membership.objects.filter(year_assigned=PackYear.objects.current(), scout__status=Scout.ACTIVE)
            .select_related("den", "scout")
            .order_by("den", "scout")
        )
        return context


class PullSheetTemplateView(PermissionRequiredMixin, TemplateView):
    permission_required = "campaigns.generate_order_report"
    template_name = "campaigns/reports/pull_sheets.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["den_list"] = (
            Den.objects.prefetch_related("campaigns")
            .filter(scouts__year_assigned=PackYear.get_current_pack_year())
            .distinct()
        )
        return context


class PrizeSelectionReportView(PermissionRequiredMixin, TemplateView):
    permission_required = "campaigns.generate_order_report"
    template_name = "campaigns/reports/prize_selections.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_campaign = Campaign.objects.current()
        context["prize_selections"] = PrizeSelection.objects.filter(campaign=current_campaign).order_by("cub")
        context["prizes"] = Prize.objects.filter(campaign=current_campaign).calculate_quantity()
        return context


class OrderSlipView(PermissionRequiredMixin, TemplateView):
    permission_required = "campaigns.generate_order_report"
    template_name = "campaigns/reports/order_slips.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        campaign = Campaign.objects.latest()
        context["order_list"] = (
            Order.objects.filter(campaign=campaign, item__isnull=False)
            .distinct()
            .calculate_total()
            .select_related("seller", "customer")
            .prefetch_related("items", "items__product")
            .order_by("seller")
        )
        return context
