import decimal
import json
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.db.models import Count, Prefetch, Q, Sum
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

    def _get_viewing_campaign(self):
        if "campaign" in self.kwargs:
            return Campaign.objects.get(year=PackYear.get_pack_year(self.kwargs["campaign"])["end_date"].year)
        current = Campaign.objects.current()
        if current:
            return current
        # No campaign is currently open for ordering (e.g. the gap between one
        # campaign closing and next year's opening) — fall back to the most
        # recently *started* campaign instead, never one that hasn't opened
        # yet.
        return Campaign.objects.filter(ordering_opens__lte=timezone.now()).order_by("-ordering_opens").first()

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.request.GET.get("filter") == "delivered":
            queryset = queryset.delivered()
        elif self.request.GET.get("filter") == "undelivered":
            queryset = queryset.undelivered()

        campaign = self._get_viewing_campaign()

        if self.request.user.family.is_seperated:
            queryset = queryset.filter(recorded_by=self.request.user)

        queryset = (
            queryset.prefetch_related("seller", "customer", "recorded_by")
            .calculate_total()
            .filter(seller__family=self.request.user.family, campaign=campaign)
            .order_by("date_added")
        )

        seller = self.request.GET.get("seller")
        if seller:
            queryset = queryset.filter(seller__pk=seller)

        return queryset

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        viewing = self._get_viewing_campaign()
        context["campaigns"] = {
            "available": Campaign.objects.filter(
                Q(orders__seller__family=self.request.user.family) | Q(year=PackYear.objects.current())
            )
            .distinct()
            .order_by("-ordering_opens"),
            "current": Campaign.objects.current(),
            "viewing": viewing,
        }
        if viewing == context["campaigns"]["current"]:
            # Always show active scouts for the current campaign, even
            # before they have any orders yet, so a new cub can be added.
            # Active scouts must have a den membership for the campaign's
            # year — otherwise they don't yet have a quota to show progress
            # against and rendering quota_progress for them would error.
            sellers = Scout.objects.filter(
                Q(
                    family=self.request.user.family,
                    status=Scout.ACTIVE,
                    den_memberships__year_assigned=viewing.year,
                )
                | Q(family=self.request.user.family, orders__campaign=viewing)
            )
        elif viewing:
            # Past (or not-yet-open) campaigns only show scouts who actually
            # sold something.
            sellers = Scout.objects.filter(family=self.request.user.family, orders__campaign=viewing)
        else:
            # No campaign has ever opened for this pack.
            sellers = Scout.objects.none()
        context["sellers"] = sellers.distinct().order_by("-date_of_birth")
        selected_seller = self.request.GET.get("seller")
        context["selected_seller"] = context["sellers"].filter(pk=selected_seller).first() if selected_seller else None
        # Whether to show the seller column/filter is based on how many cubs were
        # actually part of the pack that campaign year, not just how many have
        # placed an order so far.
        context["family_scout_count"] = (
            Scout.objects.filter(family=self.request.user.family, den_memberships__year_assigned=viewing.year)
            .distinct()
            .count()
            if viewing
            else 0
        )
        return context


class OrderReportView(LoginRequiredMixin, TemplateView):
    permission_required = "campaigns.generate_order_report"
    template_name = "campaigns/order_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["campaigns"] = {
            "available": Campaign.objects.all(),
            "current": Campaign.objects.current(),
            "viewing": (
                Campaign.objects.get(year=PackYear.get_pack_year(int(self.kwargs["campaign"]))["end_date"].year)
                if "campaign" in self.kwargs
                else Campaign.objects.latest()
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


class OrderLeaderboardView(LoginRequiredMixin, TemplateView):
    template_name = "campaigns/order_leaderboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["campaigns"] = {
            "available": Campaign.objects.all(),
            "current": Campaign.objects.current(),
            "viewing": (
                Campaign.objects.get(year=PackYear.get_pack_year(int(self.kwargs["campaign"]))["end_date"].year)
                if "campaign" in self.kwargs
                else Campaign.objects.latest()
            ),
        }

        orders = Order.objects.calculate_total().filter(campaign=context["campaigns"]["viewing"])
        cubs = Membership.objects.prefetch_related("scout", "den").filter(
            year_assigned=PackYear.objects.current(), scout__status=Membership.scout.field.related_model.ACTIVE
        )
        dens = Den.objects.filter(scouts__year_assigned=PackYear.objects.current()).distinct()

        # get all order totals for each cub
        all_cubs = []
        for cub in cubs:
            total = orders.filter(seller=cub.scout).totaled()["totaled"]
            all_cubs.append(
                {
                    "name": cub.scout.get_full_name(),
                    "den": cub.den.number,
                    "orders": orders.filter(seller=cub.scout).count(),
                    "total": total,
                }
            )

        # remove hidden sellers from Den 6
        all_cubs = [cub for cub in all_cubs if cub["den"] != 6]

        # sort cubs in descending order of orders and output the top 10
        all_cubs.sort(key=lambda x: x["orders"], reverse=True)
        context["top_orders"] = all_cubs[:10]

        # sort cubs in descending order of total and output the top 10
        all_cubs.sort(key=lambda x: x["total"], reverse=True)
        context["top_sellers"] = all_cubs[:10]

        # add all cubs with > 0 orders and not in Den 6m and sort in descending order of total
        all_cubs.sort(key=lambda x: x["total"], reverse=True)

        # in final week, show all sellers, else obfuscate $0 sellers
        if (Campaign.objects.current().ordering_closes - date.today()).days < 7:
            context["all_sellers"] = all_cubs
        else:
            context["all_sellers"] = [cub for cub in all_cubs if cub["orders"] > 0]

        # hide leaderboard in final days, to keep the surprise of the winner
        if (Campaign.objects.current().ordering_closes - date.today()).days < 5:
            context["hide_leaderboard"] = True
            context["days_left"] = (Campaign.objects.current().ordering_closes - date.today()).days

        # total up orders for each den from all_cubs and sort from most to least
        all_dens = []
        for den in dens:
            # skip Den 6 for hidden orders and special pack sponsors
            if den.number == 6:
                continue

            # find the top seller for this den
            top_seller = max([cub for cub in all_cubs if cub["den"] == den.number], key=lambda x: x["total"])

            # get all den totals
            total = sum([cub["total"] for cub in all_cubs if cub["den"] == den.number])
            all_dens.append(
                {
                    "name": den.number,
                    "orders": sum([cub["orders"] for cub in all_cubs if cub["den"] == den.number]),
                    "total": total,
                    "top_seller": top_seller["name"],
                }
            )
        all_dens.sort(key=lambda x: x["total"], reverse=True)

        context["dens"] = all_dens

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

    def form_valid(self, form):
        message = _("The order has been successfully deleted.") % {"page": self.object}
        messages.success(self.request, message, "danger")
        return super().form_valid(form)


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
            .filter(scouts__year_assigned=PackYear.objects.current())
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
        order_list = (
            Order.objects.filter(campaign=campaign, item__isnull=False)
            .distinct()
            .calculate_total()
            .select_related("seller", "customer")
            .prefetch_related("items", "items__product")
            .order_by("seller__current_den")
        )

        # sort the order list by seller current_den
        context["order_list"] = list(order_list.all())
        context["order_list"].sort(key=lambda x: x.seller.current_den.number if x.seller.current_den else 666)

        return context
