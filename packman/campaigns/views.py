import decimal
import json
from datetime import datetime, time
from math import ceil

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
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from packman.calendars.models import PackYear
from packman.dens.models import Den, Membership
from packman.membership.models import Scout

from .forms import CustomerForm, OrderForm, OrderItemFormSet, PrizeSelectionForm
from .mixins import CampaignOrderPeriodMixin, UserIsSellerFamilyTest
from .models import Campaign, Order, OrderItem, Prize, PrizePoint, PrizeSelection, Product, Quota
from .report_data import (
    build_cub_report,
    get_prize_selections_report,
    get_prize_totals_report,
    get_product_report,
)
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
            # Ineligible orders are surfaced for review in All Cubs, not in an individual cub's order list.
            queryset = queryset.award_eligible()

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


class OrderReportView(CampaignOrderPeriodMixin, PermissionRequiredMixin, TemplateView):
    permission_required = "campaigns.generate_order_report"
    template_name = "campaigns/order_report.html"
    allowed_tabs = {"sales", "products", "cubs", "prize-selections", "packing-night"}
    default_tab = "sales"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_tab = self.get_selected_tab()
        context["campaigns"] = self.get_campaign_context()
        context["selected_tab"] = selected_tab

        if selected_tab == "sales":
            context.update(self.get_sales_context())
        elif selected_tab == "products":
            context.update(self.get_products_context())
        elif selected_tab == "cubs":
            context.update(self.get_cub_context())
        elif selected_tab == "prize-selections":
            context.update(self.get_prize_selection_context())

        return context

    def get_order_period(self):
        week_context = self.get_week_context(self.viewing_campaign.get_ordering_week_windows())
        orders = Order.objects.filter(campaign=self.viewing_campaign)
        orders = self.filter_orders_by_week(orders, week_context["selected_week"])
        return week_context, orders

    def get_sales_context(self):
        week_context, orders = self.get_order_period()
        week_context["sales"] = self.get_sales_report(orders, week_context["selected_week"])
        return week_context

    def get_products_context(self):
        week_context, orders = self.get_order_period()
        week_context["product_report"] = get_product_report(self.viewing_campaign, orders)
        return week_context

    def get_cub_context(self):
        week_context, orders = self.get_order_period()
        week_context["cub_report"] = build_cub_report(
            self.viewing_campaign,
            orders,
            include_campaign_fields=week_context["selected_week"] is None,
        )
        return week_context

    def get_prize_selection_context(self):
        return {
            "prize_totals_report": get_prize_totals_report(self.viewing_campaign),
            "prize_selections_report": get_prize_selections_report(self.viewing_campaign),
        }

    def get_sales_report(self, orders, selected_week):
        orders = orders.calculate_total()

        daily_totals = {
            day["date"]: day
            for day in (
                orders.annotate(date=TruncDate("date_added"))
                .order_by("date")
                .values("date")
                .annotate(count=Count("date"), order_total=Coalesce(Sum("total"), decimal.Decimal(0.00)))
                .values("date", "count", "order_total")
            )
        }
        period_start_at = (
            selected_week["start_at"] if selected_week else timezone.localtime(self.viewing_campaign.ordering_opens)
        )
        period_end_at = (
            selected_week["end_at"] if selected_week else timezone.localtime(self.viewing_campaign.ordering_closes)
        )
        period_start = period_start_at.date()
        period_end = (period_end_at - timezone.timedelta(microseconds=1)).date()
        report_days = []
        report_date = period_start
        while report_date <= period_end:
            report_days.append(
                daily_totals.get(
                    report_date,
                    {
                        "date": report_date,
                        "count": 0,
                        "order_total": decimal.Decimal(0.00),
                    },
                )
            )
            report_date += timezone.timedelta(days=1)

        return {
            "count": orders.count(),
            "total": orders.totaled()["totaled"],
            "days": report_days,
        }


class OrderLeaderboardView(CampaignOrderPeriodMixin, LoginRequiredMixin, TemplateView):
    template_name = "campaigns/order_leaderboard.html"
    allowed_tabs = {"top-sales", "top-orders", "dens", "all-sellers"}
    default_tab = "top-sales"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        viewing_campaign = self.viewing_campaign

        # 1. Campaign navigation is always available, including while leaderboard results are hidden.
        context["campaigns"] = self.get_campaign_context()
        # Den ranks are not stored historically; they follow current-year membership, which can roll over before the
        # next campaign is created.
        context["show_den_rank_badges"] = viewing_campaign.year_id == PackYear.objects.current().pk

        now = timezone.now()
        campaign_start_at = timezone.localtime(viewing_campaign.ordering_opens)
        campaign_end_at = timezone.localtime(viewing_campaign.ordering_closes)

        # 2. Round up so a campaign ending partway through a week still gets a complete final window.
        campaign_week_count = viewing_campaign.get_ordering_week_count()
        final_week_end_at = campaign_start_at + timezone.timedelta(weeks=campaign_week_count)
        # Results become visible at midnight after the final weekly window ends:
        # Wednesday 5:00 PM -> Wednesday date -> add one day -> Thursday date
        # -> combine with 00:00 -> Thursday 12:00 AM.
        leaderboard_reveal_at = timezone.make_aware(
            datetime.combine(final_week_end_at.date() + timezone.timedelta(days=1), time.min)
        )

        # 3. A campaign remains active through midnight after its final weekly window ends.
        viewing_active_campaign = campaign_start_at <= now < leaderboard_reveal_at

        # 4. During the final stretch, hide results to avoid spoiling the winner announcement surprise.
        if viewing_active_campaign and now >= campaign_end_at - timezone.timedelta(days=5):
            context.update(
                {
                    "hide_leaderboard": True,
                    "hide_week_selector": True,
                    "now": now,
                    "campaign_end_at": campaign_end_at,
                    "leaderboard_reveal_at": leaderboard_reveal_at,
                }
            )
            return context

        # 5-6. Build every historical week, or only the active campaign weeks reached so far.
        if viewing_active_campaign:
            campaign_weeks = viewing_campaign.get_ordering_week_windows(
                ceil((now - campaign_start_at) / timezone.timedelta(weeks=1))
            )
        else:
            campaign_weeks = viewing_campaign.get_ordering_week_windows()

        # 7.1. Validate a selected week; no selection leaves the campaign totals unfiltered.
        context.update(self.get_week_context(campaign_weeks))
        selected_week = context["selected_week"]
        context["selected_tab"] = self.get_selected_tab()

        # 7.2. A selected active week shows countdowns until midnight after its window ends.
        if selected_week and viewing_active_campaign:
            week_reveal_at = timezone.make_aware(
                datetime.combine(selected_week["end_at"].date() + timezone.timedelta(days=1), time.min)
            )
            if now < week_reveal_at:
                context.update(
                    {
                        "hide_leaderboard": True,
                        "now": now,
                        "week_reveal_at": week_reveal_at,
                    }
                )
                return context

        # 7.3. Use all campaign orders unless a visible weekly window was selected.
        # Leaderboard rankings exclude explicitly ineligible orders, unlike operational reports.
        orders = Order.objects.award_eligible().calculate_total().filter(campaign=viewing_campaign)
        orders = self.filter_orders_by_week(orders, selected_week)

        cubs = Membership.objects.select_related("scout", "den", "den__rank").filter(
            year_assigned=viewing_campaign.year
        )
        if viewing_active_campaign:
            cubs = cubs.filter(scout__status=Membership.scout.field.related_model.ACTIVE)
        dens = Den.objects.select_related("rank").filter(scouts__in=cubs).distinct()

        # get all order totals for each cub
        all_cubs = []
        for cub in cubs:
            total = orders.filter(seller=cub.scout).totaled()["totaled"]
            all_cubs.append(
                {
                    "scout": cub.scout,
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

        # In the current campaign's final week, show all sellers; otherwise omit $0 sellers.
        if viewing_active_campaign and (campaign_end_at - now).days < 7:
            context["all_sellers"] = all_cubs
        else:
            context["all_sellers"] = [cub for cub in all_cubs if cub["orders"] > 0]

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
                    "rank": den.rank,
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
            # Prize totals exclude explicitly ineligible orders, which remain part of campaign reports.
            .award_eligible()
            .calculate_total()
            .filter(seller__in=cubs, campaign=Campaign.objects.latest())
        )

        cub_list = []

        for cub in cubs:
            quota = Quota.objects.get(den=cub.current_den, campaign=Campaign.objects.latest()).target
            total = orders.filter(seller=cub).totaled()["totaled"]
            points_earned = PrizePoint.calculate_earned_points(total, quota)
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
