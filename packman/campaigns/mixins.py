from functools import cached_property

from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _

from .models import Campaign


class CampaignOrderPeriodMixin:
    allowed_tabs = set()
    default_tab = None

    @cached_property
    def latest_campaign(self):
        return Campaign.objects.select_related("year").latest()

    @cached_property
    def viewing_campaign(self):
        campaign_year = self.kwargs.get("campaign")
        if campaign_year is None:
            return self.latest_campaign

        return get_object_or_404(
            Campaign.objects.select_related("year"),
            year_id=campaign_year,
        )

    def get_campaign_context(self):
        return {
            "available": Campaign.objects.select_related("year").all(),
            "viewing": self.viewing_campaign,
        }

    def get_selected_tab(self):
        selected_tab = self.request.GET.get("tab", self.default_tab)
        return selected_tab if selected_tab in self.allowed_tabs else self.default_tab

    def get_selected_week(self, campaign_weeks):
        selected_week_number = self.request.GET.get("week")
        if not selected_week_number:
            return None

        try:
            selected_week_number = int(selected_week_number)
        except ValueError as error:
            raise Http404("Unknown campaign week") from error

        if not 1 <= selected_week_number <= len(campaign_weeks):
            raise Http404("Unknown campaign week")

        return campaign_weeks[selected_week_number - 1]

    def get_week_context(self, campaign_weeks):
        return {
            "weeks": campaign_weeks,
            "selected_week": self.get_selected_week(campaign_weeks),
        }

    def filter_orders_by_week(self, orders, selected_week):
        if selected_week is None:
            return orders

        return orders.filter(
            date_added__gte=selected_week["start_at"],
            date_added__lt=selected_week["end_at"],
        )


class UserIsSellerFamilyTest(UserPassesTestMixin):
    permission_denied_message = _(
        "You are not authorized to view this page. You must be a member of the seller's family."
    )

    def test_func(self):
        if self.request.user.is_authenticated:
            self.object = self.get_object()
            return self.request.user.family == self.object.seller.family
