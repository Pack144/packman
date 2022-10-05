from django.contrib import admin
from django.db.models import Count, Q
from django.utils.translation import gettext_lazy as _

from packman.calendars.models import PackYear
from packman.committees.models import CommitteeMember

from .models import Den, Membership, Rank


class AnimalRankListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _("ranks")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "ranks"

    def lookups(self, request, model_admin):
        return (
            ("lions", _("Lions")),
            ("tigers", _("Tigers")),
            ("wolves", _("Wolves")),
            ("bears", _("Bears")),
            ("jr_webes", _("Jr. Webelos")),
            ("sr_webes", _("Sr. Webelos")),
            ("animals", _("Animal Ranks")),
            ("webelos", _("Webelos")),
            ("arrow", _("Arrow of Light")),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value provided in the query
         string and retrievable via `self.value()`.
        """
        if self.value() == "lions":
            return queryset.filter(rank__rank__exact=Rank.RankChoices.LION)
        if self.value() == "tigers":
            return queryset.filter(rank__rank__exact=Rank.RankChoices.TIGER)
        if self.value() == "wolves":
            return queryset.filter(rank__rank__exact=Rank.RankChoices.WOLF)
        if self.value() == "bears":
            return queryset.filter(rank__rank__exact=Rank.RankChoices.BEAR)
        if self.value() == "jr_webes":
            return queryset.filter(rank__rank__exact=Rank.RankChoices.JR_WEBE)
        if self.value() == "sr_webes":
            return queryset.filter(rank__rank__exact=Rank.RankChoices.SR_WEBE)
        if self.value() == "animals":
            return queryset.filter(rank__rank__lte=Rank.RankChoices.BEAR)
        if self.value() == "webelos":
            return queryset.filter(rank__rank__gte=Rank.RankChoices.JR_WEBE)
        if self.value() == "arrow":
            return queryset.filter(rank__rank__exact=Rank.RankChoices.ARROW)


class LeadershipAdmin(admin.TabularInline):
    model = CommitteeMember
    classes = ["collapse"]
    exclude = ["date_added", "committee", "position"]
    autocomplete_fields = ["member"]
    extra = 0
    verbose_name = _("Leadership")
    verbose_name_plural = _("Leaders")


class MembershipAdmin(admin.TabularInline):
    model = Membership
    autocomplete_fields = ["scout"]
    exclude = ["date_added"]
    extra = 0


@admin.register(Den)
class DenAdmin(admin.ModelAdmin):
    inlines = [LeadershipAdmin, MembershipAdmin]
    list_display = (
        "number",
        "cubs_count",
        "cubs_count_next_year",
        "rank",
        "get_rank_category",
    )
    list_filter = (AnimalRankListFilter,)
    search_fields = (
        "number",
        "rank__rank",
        "scouts__first_name",
        "scouts__nickname",
        "scouts__last_name",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _cubs_count=Count(
                "scouts",
                filter=Q(scouts__year_assigned=PackYear.get_current_pack_year()),
            ),
            _cubs_count_next_year=Count("scouts", filter=Q(scouts__year_assigned=PackYear.objects.next())),
        )
        return queryset

    def cubs_count(self, obj):
        return obj._cubs_count

    cubs_count.admin_order_field = "_cubs_count"
    cubs_count.short_description = _("# of cubs")

    @admin.display(description=_("# of Cubs next year"), ordering="_cubs_count_next_year")
    def cubs_count_next_year(self, obj):
        return obj._cubs_count_next_year


@admin.register(Rank)
class RankAdmin(admin.ModelAdmin):
    list_display = (
        "rank",
        "description",
    )
    search_fields = ("rank",)
