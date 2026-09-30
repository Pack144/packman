import decimal
from dataclasses import dataclass

from django.db.models import Case, Count, DecimalField, Exists, F, OuterRef, Prefetch, Q, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils.translation import gettext as _

from packman.campaigns.models import CampaignScout, OrderItem, PrizePoint, PrizeSelection, Product
from packman.dens.models import Membership


@dataclass(frozen=True)
class ReportColumn:
    label: str


@dataclass(frozen=True)
class ReportCell:
    value: object
    kind: str = "text"
    url: str | None = None
    sort_value: object | None = None

    @property
    def effective_sort_value(self):
        return self.value if self.sort_value is None else self.sort_value


@dataclass(frozen=True)
class TabularReport:
    columns: tuple[ReportColumn, ...]
    rows: tuple[tuple[ReportCell, ...], ...]
    default_sort_index: int
    default_sort_direction: str = "ascending"


MONEY_OUTPUT_FIELD = DecimalField(max_digits=12, decimal_places=2)
ZERO_MONEY = Value(decimal.Decimal("0.00"), output_field=MONEY_OUTPUT_FIELD)
WEIGHT_OUTPUT_FIELD = DecimalField(max_digits=14, decimal_places=4)
ZERO_WEIGHT = Value(decimal.Decimal("0.0000"), output_field=WEIGHT_OUTPUT_FIELD)

CUB_COLUMNS = (
    ReportColumn(_("Cub")),
    ReportColumn(_("Den")),
    ReportColumn(_("Order Count")),
    ReportColumn(_("Total Sales")),
    ReportColumn(_("Eligible Total")),
)
CUB_CAMPAIGN_COLUMNS = (
    ReportColumn(_("Quota")),
    ReportColumn(_("Achieved")),
    ReportColumn(_("Amount Owed")),
    ReportColumn(_("Prize Points Earned")),
    ReportColumn(_("Prize Points Spent")),
    ReportColumn(_("Points Remaining")),
)
PRODUCT_COLUMNS = (ReportColumn(_("Product")), ReportColumn(_("Quantity Ordered")))
PRIZE_TOTAL_COLUMNS = (ReportColumn(_("Prize")), ReportColumn(_("Quantity")))
PRIZE_CUB_COLUMNS = (
    ReportColumn(_("Den")),
    ReportColumn(_("Cub")),
    ReportColumn(_("Prize")),
    ReportColumn(_("Quantity")),
)
DEN_COLUMNS = (
    ReportColumn(_("Den #")),
    ReportColumn(_("Total Sales")),
    ReportColumn(_("Total Orders")),
    ReportColumn(_("Total Weight")),
    ReportColumn(_("Member Count")),
    ReportColumn(_("Adjusted Member Count")),
    ReportColumn(_("Average Sales")),
    ReportColumn(_("Average Orders")),
    ReportColumn(_("Average Weight")),
)


def _money_cell(value, kind="currency"):
    return ReportCell(value, kind=kind)


def format_weight(pounds):
    return f"{pounds:,.1f}lb"


def _order_metrics_by_seller(orders):
    return {
        row["seller_id"]: row
        for row in (
            orders.calculate_total()
            .values("seller_id")
            .annotate(
                order_count=Count("pk"),
                total_sales=Coalesce(Sum("total"), ZERO_MONEY),
                eligible_total=Coalesce(
                    Sum("total", filter=~Q(award_ineligible=True), output_field=MONEY_OUTPUT_FIELD),
                    ZERO_MONEY,
                ),
            )
        )
    }


def _weight_metrics_by_seller(orders):
    weight_per_item = Case(
        When(
            product__weight__isnull=False,
            product__unit=Product.WeightUnit.OUNCE,
            then=F("product__weight") * Value(decimal.Decimal("0.0625"), output_field=WEIGHT_OUTPUT_FIELD),
        ),
        When(
            product__weight__isnull=False,
            product__unit=Product.WeightUnit.POUND,
            then=F("product__weight"),
        ),
        default=Value(decimal.Decimal("0.0000")),
        output_field=WEIGHT_OUTPUT_FIELD,
    )
    return {
        row["order__seller_id"]: row["total_weight"]
        for row in (
            OrderItem.objects.filter(order__in=orders)
            .values("order__seller_id")
            .annotate(
                total_weight=Coalesce(
                    Sum(weight_per_item * F("quantity"), output_field=WEIGHT_OUTPUT_FIELD),
                    ZERO_WEIGHT,
                )
            )
        )
    }


def get_den_metrics(campaign, orders, memberships=None):
    """Aggregate campaign order and weight metrics by den, including empty-selling members."""
    if memberships is None:
        memberships = Membership.objects.filter(year_assigned=campaign.year)

    memberships = memberships.select_related("den").annotate(
        campaign_exempt=Exists(
            CampaignScout.objects.filter(campaign=campaign, scout_id=OuterRef("scout_id"), exempt=True)
        )
    )
    order_metrics = _order_metrics_by_seller(orders)
    weight_metrics = _weight_metrics_by_seller(orders)
    den_metrics = {}

    for membership in memberships:
        metrics = den_metrics.setdefault(
            membership.den_id,
            {
                "den": membership.den,
                "member_count": 0,
                "adjusted_member_count": 0,
                "total_sales": decimal.Decimal("0.00"),
                "total_orders": 0,
                "total_weight": decimal.Decimal("0.0000"),
                "adjusted_sales": decimal.Decimal("0.00"),
                "adjusted_orders": 0,
                "adjusted_weight": decimal.Decimal("0.0000"),
            },
        )
        seller_orders = order_metrics.get(
            membership.scout_id,
            {"order_count": 0, "total_sales": decimal.Decimal("0.00")},
        )
        seller_weight = weight_metrics.get(membership.scout_id, decimal.Decimal("0.0000"))

        metrics["member_count"] += 1
        metrics["total_sales"] += seller_orders["total_sales"]
        metrics["total_orders"] += seller_orders["order_count"]
        metrics["total_weight"] += seller_weight
        if not membership.campaign_exempt:
            metrics["adjusted_member_count"] += 1
            metrics["adjusted_sales"] += seller_orders["total_sales"]
            metrics["adjusted_orders"] += seller_orders["order_count"]
            metrics["adjusted_weight"] += seller_weight

    for metrics in den_metrics.values():
        adjusted_count = metrics["adjusted_member_count"]
        metrics["average_sales"] = (
            (metrics["adjusted_sales"] / adjusted_count).quantize(decimal.Decimal("0.01"))
            if adjusted_count
            else decimal.Decimal("0.00")
        )
        metrics["average_orders"] = (
            (decimal.Decimal(metrics["adjusted_orders"]) / adjusted_count).quantize(decimal.Decimal("0.01"))
            if adjusted_count
            else decimal.Decimal("0.00")
        )
        metrics["average_weight"] = (
            (metrics["adjusted_weight"] / adjusted_count).quantize(decimal.Decimal("0.0001"))
            if adjusted_count
            else decimal.Decimal("0.0000")
        )

    return sorted(den_metrics.values(), key=lambda metrics: metrics["den"].number)


def build_den_report(campaign, orders):
    rows = []
    for metrics in get_den_metrics(campaign, orders):
        rows.append(
            (
                ReportCell(metrics["den"].number, kind="number"),
                _money_cell(metrics["total_sales"]),
                ReportCell(metrics["total_orders"], kind="number"),
                ReportCell(
                    format_weight(metrics["total_weight"]),
                    kind="weight",
                    sort_value=metrics["total_weight"],
                ),
                ReportCell(metrics["member_count"], kind="number"),
                ReportCell(metrics["adjusted_member_count"], kind="number"),
                _money_cell(metrics["average_sales"]),
                ReportCell(metrics["average_orders"], kind="number"),
                ReportCell(
                    format_weight(metrics["average_weight"]),
                    kind="weight",
                    sort_value=metrics["average_weight"],
                ),
            )
        )

    return TabularReport(
        columns=DEN_COLUMNS,
        rows=tuple(rows),
        default_sort_index=0,
    )


def build_cub_report(campaign, orders, include_campaign_fields):
    memberships = Membership.objects.filter(year_assigned=campaign.year).select_related("scout", "den")
    if include_campaign_fields:
        memberships = memberships.annotate(
            campaign_exempt=Exists(
                CampaignScout.objects.filter(campaign=campaign, scout_id=OuterRef("scout_id"), exempt=True)
            )
        )
    order_metrics = _order_metrics_by_seller(orders)
    quotas = dict(campaign.quota_set.values_list("den_id", "target")) if include_campaign_fields else {}
    points_spent = (
        {
            row["cub_id"]: row["spent"]
            for row in (
                PrizeSelection.objects.filter(campaign=campaign)
                .values("cub_id")
                .annotate(spent=Coalesce(Sum(F("prize__points") * F("quantity")), 0))
            )
        }
        if include_campaign_fields
        else {}
    )
    prize_point_tiers = tuple(PrizePoint.objects.order_by("earned_at")) if include_campaign_fields else ()

    rows = []
    for membership in memberships:
        metrics = order_metrics.get(
            membership.scout_id,
            {
                "order_count": 0,
                "total_sales": decimal.Decimal("0.00"),
                "eligible_total": decimal.Decimal("0.00"),
            },
        )
        total = metrics["total_sales"]
        eligible_total = metrics["eligible_total"]
        cells = [
            ReportCell(membership.scout),
            ReportCell(membership.den, sort_value=membership.den.number),
            ReportCell(metrics["order_count"], kind="number"),
            _money_cell(total),
            _money_cell(eligible_total),
        ]

        if include_campaign_fields:
            quota = quotas.get(membership.den_id, decimal.Decimal("0.00"))
            points_earned = PrizePoint.calculate_earned_points(
                eligible_total,
                quota,
                prize_points=prize_point_tiers,
            )
            spent = points_spent.get(membership.scout_id, 0)
            achieved = eligible_total >= quota

            if membership.campaign_exempt:
                amount_owed = total
            elif total < quota:
                amount_owed = total + (quota - total) * decimal.Decimal("0.65")
            else:
                amount_owed = total

            cells.extend(
                (
                    _money_cell(quota, kind="whole_currency"),
                    ReportCell(achieved, kind="boolean"),
                    _money_cell(amount_owed.quantize(decimal.Decimal(".01"))),
                    ReportCell(points_earned, kind="number"),
                    ReportCell(spent, kind="number"),
                    ReportCell(points_earned - spent, kind="number"),
                )
            )

        rows.append(tuple(cells))

    columns = CUB_COLUMNS + (CUB_CAMPAIGN_COLUMNS if include_campaign_fields else ())
    default_sort_index = 4
    rows.sort(key=lambda row: row[default_sort_index].value, reverse=True)
    return TabularReport(
        columns=columns,
        rows=tuple(rows),
        default_sort_index=default_sort_index,
        default_sort_direction="descending",
    )


def build_product_report(products):
    return TabularReport(
        columns=PRODUCT_COLUMNS,
        rows=tuple(
            (
                ReportCell(product.name),
                ReportCell(product.quantity_ordered or 0, kind="number"),
            )
            for product in products
        ),
        default_sort_index=1,
        default_sort_direction="descending",
    )


def get_product_report(campaign, orders):
    return build_product_report(campaign.products.quantity(orders).order_by("-quantity_ordered", "name"))


def build_prize_totals_report(prizes):
    return TabularReport(
        columns=PRIZE_TOTAL_COLUMNS,
        rows=tuple(
            (
                ReportCell(prize.name, url=prize.url),
                ReportCell(prize.quantity, kind="number"),
            )
            for prize in prizes
            if prize.quantity
        ),
        default_sort_index=1,
        default_sort_direction="descending",
    )


def get_prize_totals_report(campaign):
    return build_prize_totals_report(campaign.prizes.calculate_quantity().order_by("-quantity", "name"))


def build_prize_selections_report(prize_selections):
    rows = []
    for selection in prize_selections:
        membership = selection.cub.report_memberships[0] if selection.cub.report_memberships else None
        rows.append(
            (
                ReportCell(membership.den.number if membership else ""),
                ReportCell(selection.cub),
                ReportCell(selection.prize),
                ReportCell(selection.quantity, kind="number"),
            )
        )

    rows.sort(key=lambda row: str(row[1].value).casefold())
    return TabularReport(columns=PRIZE_CUB_COLUMNS, rows=tuple(rows), default_sort_index=1)


def get_prize_selections_report(campaign):
    memberships = Membership.objects.filter(year_assigned=campaign.year).select_related("den")
    selections = (
        PrizeSelection.objects.filter(campaign=campaign)
        .select_related("cub", "prize")
        .prefetch_related(
            Prefetch(
                "cub__den_memberships",
                queryset=memberships,
                to_attr="report_memberships",
            )
        )
        .order_by("cub")
    )
    return build_prize_selections_report(selections)
