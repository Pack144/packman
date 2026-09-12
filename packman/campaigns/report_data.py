import decimal
from dataclasses import dataclass

from django.db.models import Count, DecimalField, F, Prefetch, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils.translation import gettext as _

from packman.campaigns.models import PrizePoint, PrizeSelection
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


def _money_cell(value, kind="currency"):
    return ReportCell(value, kind=kind)


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


def build_cub_report(campaign, orders, include_campaign_fields):
    memberships = Membership.objects.filter(year_assigned=campaign.year).select_related("scout", "den")
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

            if total < quota:
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
