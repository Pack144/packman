import csv
import decimal

from django.http import StreamingHttpResponse, HttpResponse
from django.utils import timezone, dateparse

from packman.campaigns.models import Campaign, Order, PrizePoint, PrizeSelection
from packman.dens.models import Membership


class Echo:
    """An object that implements just the write method of the file-like
    interface.
    """

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


def turn_in_night_report(request):
    if request.GET.get("campaign"):
        campaign = Campaign.objects.get_by_natural_key(request.GET.get("campaign"))
    else:
        campaign = Campaign.objects.current()

    report_date = timezone.now()
    report_name = f"Campaign Report ({report_date.month}-{report_date.day}-{report_date.year}).csv"

    echo_buffer = Echo()
    writer = csv.writer(echo_buffer)

    return StreamingHttpResponse(
        (writer.writerow(row) for row in report_rows(campaign)),
        content_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={report_name}"},
    )


def report_rows(campaign):
    cubs = Membership.objects.prefetch_related("scout", "den", "den__quotas").filter(year_assigned=campaign.year)

    orders = Order.objects.filter(campaign=campaign)
    yield [
        "Cub",
        "Den",
        "Order Count",
        "Total",
        "Quota",
        "Achieved",
        "Amount Owed",
        "Prize Points Earned",
        "Prize Points Spent",
        "Points Remaining",
    ]

    for cub in cubs:
        yield generate_cub_row(cub, orders, campaign)


def generate_cub_row(cub, orders, campaign):
    cub_orders = orders.filter(seller__den_memberships=cub)
    total = cub_orders.totaled()["totaled"]
    quota = cub.den.quotas.current().target

    # calculate points earned
    if total < quota:
        points_earned = 0
    elif total <= 2000:
        points_earned = PrizePoint.objects.filter(earned_at__lte=total).order_by("-earned_at").first().value
    else:
        points_earned = PrizePoint.objects.order_by("earned_at").last().value + int(
            (total - PrizePoint.objects.order_by("earned_at").last().earned_at) / 100
        )

    points_spent = PrizeSelection.objects.filter(
        cub=cub.scout, campaign=campaign
    ).calculate_total_points_spent()["spent"]
    points_remaining = points_earned - points_spent

    # TODO: Don't hard-code the minimum if quota unmet
    met_quota = total >= quota
    if not met_quota:
        shortfall = quota - total
        owed = total + shortfall * decimal.Decimal("0.65")
    else:
        owed = total

    return [
        cub.scout,
        cub.den,
        cub_orders.count(),
        total,
        quota,
        met_quota,
        owed.quantize(decimal.Decimal(".01")),
        points_earned,
        points_spent,
        points_remaining,
    ]


def generate_weekly_report(request):
    if request.GET.get("end"):
        end_date = dateparse.parse_date(request.GET.get("end"))
    else:
        end_date = timezone.now()

    if request.GET.get("end"):
        begin_date = dateparse.parse_date(request.GET.get("begin"))
    else:
        begin_date = end_date - timezone.timedelta(days=7)

    report_name = f"Campaign Weekly Report (from {begin_date.month}-{begin_date.day}-{begin_date.year} to {end_date.month}-{end_date.day}-{end_date.year}).csv"
    field_names = ["Cub", "Den", "Order Count", "Total Sales"]

    orders = Order.objects.filter(date_added__gte=begin_date, date_added__lte=end_date)
    members = Membership.objects.prefetch_related("scout", "den").filter(scout__orders__in=orders).distinct().order_by("den")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f"attachment; filename={report_name}"
    writer = csv.writer(response)
    writer.writerow(field_names)

    for cub in members:
        cub_orders = orders.filter(seller__den_memberships=cub)
        writer.writerow([cub.scout, cub.den, cub_orders.count(), cub_orders.totaled()["totaled"]])

    return response
