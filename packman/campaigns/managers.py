import decimal

from django.db import models
Ifrom django.db.models import Count, F, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone


class CampaignQuerySet(models.QuerySet):
    def current(self):
        today = timezone.now()
        try:
            return (
                self.get(ordering_opens__lte=today, ordering_closes__gte=today - timezone.timedelta(days=90))
                or models.QuerySet.none()
            )
        except self.model.DoesNotExist:
            return None

    def calculate_amount_owed(self):
        return self.model.orders.field.model.objects.filter(
            campaign=OuterRef("pk").order_by().calculate_total().values("total")
        )


class OrderQuerySet(models.QuerySet):

    def products(self):
        return self.model.items.rel.related_model.product.field.related_model.objects.filter(order__order__in=self)

    def donations_total(self):
        return self.aggregate(
            total=Sum("donation"),
        )

    def products_total(self):
        return self.product_total().aggregate(total=Sum("product_total"))

    def product_total(self):
        return self.annotate(
            product_total=Coalesce(
                Sum(
                    F("item__product__price") * F("item__quantity"),
                    output_field=models.DecimalField(),
                ),
                decimal.Decimal(0.00),
            ),
        )

    def calculate_subtotal(self):
        items = self.model.items.field.model.objects.filter(order=OuterRef("pk")).order_by().values("order")
        return self.annotate(subtotal=Coalesce(Subquery(items.calculate_cost().values("cost")), decimal.Decimal(0.00)))

    def calculate_total(self):
        return self.calculate_subtotal().annotate(total=F("subtotal") + Coalesce(F("donation"), decimal.Decimal(0.00)))

    def calculate_prize_points(self):
        return self.calculate_total().aggregate(prize_points=Sum(F("total") - 550))

    def totaled(self):
        return self.calculate_total().aggregate(totaled=Coalesce(Sum("total"), decimal.Decimal(0.00)))

    def with_total(self):

        return self.annotate(
            total=Sum(
                F("donation")
                + Subquery(
                    self.model.items.field.model.objects.filter(order=OuterRef("pk"))
                    .calculate_subtotal()
                    .values("subtotal")[:1]
                ),
                output_field=models.DecimalField(0.00),
            )
        )

    def totals(self):
        totals = self.aggregate(
            donations=Sum("donation", distinct=True),
            products=Coalesce(
                Sum(F("item__product__price") * F("item__quantity"), output_field=models.DecimalField()),
                decimal.Decimal(0.00),
            ),
        )
        totals.update(total=totals["donations"] + totals["products"])
        return totals

    def current_campaign(self):
        return self.filter(campaign=self.model.campaign.field.related_model.objects.current())

    def latest_campaign(self):
        return self.filter(campaign=self.model.campaign.field.related_model.objects.latest())


class OrderItemQuerySet(models.QuerySet):
    def calculate_cost(self):
        return self.annotate(
            cost=Sum(F("product__price") * F("quantity"), output_field=models.DecimalField(decimal_places=2))
        )

    def calculate_subtotal(self):
        return self.calculate_cost().aggregate(subtotal=Sum("cost"))

    def with_total(self):
        return self.annotate(
            total=Coalesce(
                Sum(F("product__price") * F("quantity"), output_field=models.DecimalField()), decimal.Decimal(0.00)
            )
        )

    def counted(self):
        return self.aggregate(count=Coalesce(Sum("quantity"), 0))

    def totaled(self):
        return self.with_total().aggregate(totaled=Sum("total"))

    def current_campaign(self):
        return self.filter(order__in=self.model.order.field.related_model.objects.current_campaign())

    def latest_campaign(self):
        return self.filter(order__in=self.model.order.field.related_model.objects.latest_campaign())


class ProductQuerySet(models.QuerySet):
    def current(self):
        return self.filter(campaign=self.model.campaign.field.related_model.objects.current())

    def quantity(self):
        return self.annotate(ordered_quantity=Sum("order__quantity")).order_by("category", "sort_order", "name")

    def count_orders(self):
        return self.annotate(order_count=Count("order"))


class QuotaQuerySet(models.QuerySet):
    def current(self):
        return self.get(campaign=self.model.campaign.field.related_model.objects.current()) or models.QuerySet.none()


class PrizeQuerySet(models.QuerySet):
    def calculate_quantity(self):
        return self.annotate(quantity=Sum("prize_selection__quantity"))


class PrizeSelectionQuerySet(models.QuerySet):
    def calculate_points(self):
        return self.annotate(
            points=Coalesce(Sum(F("prize__points") * F("quantity")), 0)
        )

    def calculate_total_points_spent(self):
        return self.calculate_points().aggregate(spent=Coalesce(Sum("points"), 0))

    def current(self):
        return self.filter(campaign=self.model.campaign.field.related_model.objects.latest())
