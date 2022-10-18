from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from packman.committees.models import CommitteeMember

from .models import Den, Membership, Rank


class RankCategoryFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _("category")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "category"

    def lookups(self, request, model_admin):
        return (
            ("animals", _("Animal Ranks")),
            ("webelos", _("Webelos")),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value provided in the query
         string and retrievable via `self.value()`.
        """
        if self.value() == "animals":
            return queryset.animals()
        if self.value() == "webelos":
            return queryset.webelos()


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
        "__str__",
        "cubs_count",
        "cubs_count_next_year",
        "rank",
        "get_rank_category",
    )
    list_filter = (RankCategoryFilter,"rank__rank")
    ordering = ["number"]
    search_fields = (
        "number",
        "rank__rank",
        "scouts__first_name",
        "scouts__nickname",
        "scouts__last_name",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.counting_members()

    @admin.display(description=_("Current Cubs"), ordering="current_count")
    def cubs_count(self, obj):
        return obj.current_count

    @admin.display(description=_("Incoming Cubs"), ordering="upcoming_count")
    def cubs_count_next_year(self, obj):
        return obj.upcoming_count


@admin.register(Rank)
class RankAdmin(admin.ModelAdmin):
    list_display = (
        "rank",
        "description",
    )
    search_fields = ("rank",)
