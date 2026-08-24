import csv
import decimal
import io
from http import HTTPStatus

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from packman.calendars.factories import PackYearFactory
from packman.campaigns.models import Campaign, Order, PrizePoint, Quota
from packman.campaigns.reports import generate_weekly_report, report_rows, turn_in_night_report
from packman.dens.factories import DenFactory, MembershipFactory
from packman.membership.factories import AdultFactory, CompleteFamilyFactory, ScoutFactory


class CampaignReportTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.current_year = PackYearFactory(year=2026)
        self.previous_year = PackYearFactory(year=2025)
        self.previous_campaign = self.create_campaign(self.previous_year, timezone.datetime(2025, 9, 1).date())
        self.current_campaign = self.create_campaign(self.current_year, timezone.datetime(2026, 9, 1).date())

        content_type = ContentType.objects.get_for_model(Campaign)
        self.permission = Permission.objects.get(codename="generate_order_report", content_type=content_type)
        self.authorized_user = AdultFactory()
        self.authorized_user.user_permissions.add(self.permission)

    def create_campaign(self, year, ordering_opens):
        return Campaign.objects.create(
            year=year,
            ordering_opens=ordering_opens,
            ordering_closes=ordering_opens + timezone.timedelta(days=30),
            delivery_available=ordering_opens + timezone.timedelta(days=45),
            prize_window_opens=ordering_opens + timezone.timedelta(days=45),
            prize_window_closes=ordering_opens + timezone.timedelta(days=60),
        )

    def _authorized_request(self, path):
        request = self.factory.get(path)
        request.user = self.authorized_user
        return request

    def test_weekly_report_only_includes_latest_campaign_orders_and_members(self):
        current_member = MembershipFactory(year_assigned=self.current_year)
        previous_member = MembershipFactory(year_assigned=self.previous_year)
        Order.objects.create(
            campaign=self.current_campaign, seller=current_member.scout, donation=decimal.Decimal("25.00")
        )
        Order.objects.create(
            campaign=self.previous_campaign, seller=previous_member.scout, donation=decimal.Decimal("50.00")
        )

        response = generate_weekly_report(self._authorized_request("/reports/weekly/"))
        rows = list(csv.reader(io.StringIO(response.content.decode())))

        self.assertEqual(rows[0], ["Cub", "Den", "Order Count", "Total Sales"])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][0], str(current_member.scout))
        self.assertEqual(rows[1][1], str(current_member.den))
        self.assertEqual(rows[1][2:], ["1", "25"])

    def test_weekly_report_uses_the_den_assigned_for_the_campaign_year(self):
        # A scout who moved dens between pack years must be reported under the
        # den they belonged to during the campaign's year, not their den from
        # any other year (and not necessarily their "current" den).
        scout = ScoutFactory()
        old_den = DenFactory()
        new_den = DenFactory()
        MembershipFactory(scout=scout, den=old_den, year_assigned=self.previous_year)
        MembershipFactory(scout=scout, den=new_den, year_assigned=self.current_year)
        Order.objects.create(campaign=self.current_campaign, seller=scout, donation=decimal.Decimal("10.00"))

        response = generate_weekly_report(self._authorized_request("/reports/weekly/"))
        rows = list(csv.reader(io.StringIO(response.content.decode())))

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][0], str(scout))
        self.assertEqual(rows[1][1], str(new_den))

    def test_campaign_report_uses_campaign_quota_and_tiered_prize_points(self):
        member = MembershipFactory(year_assigned=self.current_year)
        Quota.objects.create(campaign=self.current_campaign, den=member.den, target=decimal.Decimal("100.00"))
        Quota.objects.create(campaign=self.previous_campaign, den=member.den, target=decimal.Decimal("4000.00"))
        PrizePoint.objects.create(earned_at=decimal.Decimal("1000.00"), value=10)
        PrizePoint.objects.create(earned_at=decimal.Decimal("2000.00"), value=25)
        Order.objects.create(campaign=self.current_campaign, seller=member.scout, donation=decimal.Decimal("4000.00"))

        row = list(report_rows(self.current_campaign))[1]

        self.assertEqual(row[4], decimal.Decimal("100.00"))
        self.assertEqual(row[7], 55)

    def test_turn_in_night_report_falls_back_to_latest_campaign_when_none_is_current(self):
        # No campaign's ordering window covers "now", so Campaign.objects.current()
        # returns None; the report must still succeed by using the latest campaign.
        self.assertIsNone(Campaign.objects.current())

        response = turn_in_night_report(self._authorized_request("/reports/turn_in_night/"))
        content = b"".join(response.streaming_content)
        rows = list(csv.reader(io.StringIO(content.decode())))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(rows[0][0], "Cub")


class CampaignReportAccessControlTestCase(TestCase):
    """Ensure the weekly and turn-in-night reports require the same
    ``campaigns.generate_order_report`` permission as the other reports
    views (e.g. ``OrderReportView``)."""

    def setUp(self):
        current_year = PackYearFactory(year=2026)
        Campaign.objects.create(
            year=current_year,
            ordering_opens=timezone.datetime(2026, 9, 1).date(),
            ordering_closes=timezone.datetime(2026, 10, 1).date(),
            delivery_available=timezone.datetime(2026, 10, 15).date(),
            prize_window_opens=timezone.datetime(2026, 10, 15).date(),
            prize_window_closes=timezone.datetime(2026, 10, 30).date(),
        )

        content_type = ContentType.objects.get_for_model(Campaign)
        self.permission = Permission.objects.get(codename="generate_order_report", content_type=content_type)

    def test_weekly_report_redirects_anonymous_user_to_login(self):
        url = reverse("campaigns:weekly_report")
        login_url = f"{reverse('login')}?next={url}"
        response = self.client.get(url)

        self.assertRedirects(response, login_url)

    def test_weekly_report_denies_member_without_permission(self):
        member = CompleteFamilyFactory(active_children=1).adults.first()
        self.client.force_login(member)
        response = self.client.get(reverse("campaigns:weekly_report"))

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_weekly_report_allows_member_with_permission(self):
        member = AdultFactory()
        member.user_permissions.add(self.permission)
        self.client.force_login(member)
        response = self.client.get(reverse("campaigns:weekly_report"))

        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_turn_in_night_report_redirects_anonymous_user_to_login(self):
        url = reverse("campaigns:turn_in_night")
        login_url = f"{reverse('login')}?next={url}"
        response = self.client.get(url)

        self.assertRedirects(response, login_url)

    def test_turn_in_night_report_denies_member_without_permission(self):
        member = CompleteFamilyFactory(active_children=1).adults.first()
        self.client.force_login(member)
        response = self.client.get(reverse("campaigns:turn_in_night"))

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_turn_in_night_report_allows_member_with_permission(self):
        member = AdultFactory()
        member.user_permissions.add(self.permission)
        self.client.force_login(member)
        response = self.client.get(reverse("campaigns:turn_in_night"))

        self.assertEqual(response.status_code, HTTPStatus.OK)
