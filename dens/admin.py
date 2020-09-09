from django.contrib import admin
from django.db.models import Count, Q
from django.utils.translation import gettext_lazy as _

from committees import models
from pack_calendar.models import PackYear

from .models import Den, Membership, Rank


class AnimalRankListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _("ranks")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'ranks'

    def lookups(self, request, model_admin):
        return (
            ('bobcats', _("Bobcats")),
            ('tigers', _("Tigers")),
            ('wolves', _("Wolves")),
            ('bears', _("Bears")),
            ('jr_webes', _("Jr. Webelos")),
            ('sr_webes', _("Sr. Webelos")),
            ('animals', _("Animal Ranks")),
            ('webelos', _("Webelos")),
            ('arrow', _("Arrow of Light")),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value provided in the query
         string and retrievable via `self.value()`.
        """
        if self.value() == 'bobcats':
            return queryset.filter(
                rank__rank__exact=Rank.BOBCAT
            )
        if self.value() == 'tigers':
            return queryset.filter(
                rank__rank__exact=Rank.TIGER
            )
        if self.value() == 'wolves':
            return queryset.filter(
                rank__rank__exact=Rank.WOLF
            )
        if self.value() == 'bears':
            return queryset.filter(
                rank__rank__exact=Rank.BEAR
            )
        if self.value() == 'jr_webes':
            return queryset.filter(
                rank__rank__exact=Rank.JR_WEBE
            )
        if self.value() == 'sr_webes':
            return queryset.filter(
                rank__rank__exact=Rank.SR_WEBE
            )
        if self.value() == 'animals':
            return queryset.filter(
                rank__rank__lte=Rank.BEAR
            )
        if self.value() == 'webelos':
            return queryset.filter(
                rank__rank__gte=Rank.JR_WEBE
            )
        if self.value() == 'arrow':
            return queryset.filter(
                rank__rank__exact=Rank.ARROW
            )


class LeadershipAdmin(admin.TabularInline):
    model = models.Membership
    classes = ['collapse']
    exclude = ['date_added', 'committee', 'position']
    autocomplete_fields = ['member']
    extra = 0
    verbose_name = _("Leadership")
    verbose_name_plural = _("Leaders")


class MembershipAdmin(admin.TabularInline):
    model = Membership
    autocomplete_fields = ['scout']
    exclude = ['date_added']
    extra = 0


@admin.register(Den)
class DenAdmin(admin.ModelAdmin):
    inlines = [LeadershipAdmin, MembershipAdmin]
    list_display = (
        'number',
        'cubs_count',
        'rank',
        'get_rank_category',
    )
    list_filter = (AnimalRankListFilter, )
    search_fields = (
        'number',
        'rank__rank',
        'scouts__first_name',
        'scouts__nickname',
        'scouts__last_name',
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _cubs_count=Count('scouts', filter=Q(scouts__year_assigned=PackYear.get_current_pack_year())),
        )
        return queryset

    def cubs_count(self, obj):
        return obj._cubs_count

    cubs_count.admin_order_field = '_cubs_count'
    cubs_count.short_description = _("# of cubs")


@admin.register(Rank)
class RankAdmin(admin.ModelAdmin):
    list_display = ('rank', 'description', )
    search_fields = ('rank', )
