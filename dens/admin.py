from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Den, Rank


class AnimalRankListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('ranks')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'ranks'

    def lookups(self, request, model_admin):
        return (
            ('tigers', _('Tigers')),
            ('wolves', _('Wolves')),
            ('bears', _('Bears')),
            ('jr_weebs', _('Jr. Webelos')),
            ('sr_weebs', _('Sr. Webelos')),
            ('animals', _('Animal Ranks')),
            ('webelos', _('Webelos')),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        if self.value() == 'tigers':
            return queryset.filter(rank__exact=2)
        if self.value() == 'wolves':
            return queryset.filter(rank__exact=3)
        if self.value() == 'bears':
            return queryset.filter(rank__exact=4)
        if self.value() == 'jr_weebs':
            return queryset.filter(rank__exact=5)
        if self.value() == 'sr_weebs':
            return queryset.filter(rank__exact=6)
        if self.value() == 'animals':
            return queryset.filter(rank__lte=4)
        if self.value() == 'webelos':
            return queryset.filter(rank__gte=5)


@admin.register(Den)
class DenAdmin(admin.ModelAdmin):
    list_display = ('number', 'rank', )
    list_filter = ('rank', AnimalRankListFilter, )


admin.site.register(Rank)
