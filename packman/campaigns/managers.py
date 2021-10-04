import decimal

from django.db import models
from django.db.models import F, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone


class CampaignQuerySet(models.QuerySet):
    def current(self):
        try:
            return (
                self.get(ordering_opens__lte=timezone.now(), ordering_closes__gte=timezone.now())
                or models.QuerySet.none()
            )
        except self.model.DoesNotExist:
            return None


class OrderQuerySet(models.QuerySet):
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


class QuotaQuerySet(models.QuerySet):
    def current(self):
        return self.get(campaign=self.model.campaign.field.related_model.objects.current()) or models.QuerySet.none()
