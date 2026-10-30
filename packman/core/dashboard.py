from django.contrib import admin
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from packman.calendars.models import Event, PackYear
from packman.dens.models import Den, Rank
from packman.membership.models import Adult, Family, Scout


def _visible_admin(request, model):
    model_admin = admin.site.get_model_admin(model)
    if model_admin.has_module_permission(request) and model_admin.has_view_or_change_permission(request):
        return model_admin
    return None


def pack_dashboard(request, context):
    now = timezone.now()
    year_admin = _visible_admin(request, PackYear)
    context.update(
        dashboard_cards=[],
        den_rows=[],
        cub_total=None,
        pack_year=None,
        pack_year_url=None,
        pack_year_list_url=reverse("admin:calendars_packyear_changelist") if year_admin else None,
    )
    try:
        year = PackYear.objects.for_date(timezone.localdate(now))
    except PackYear.DoesNotExist:
        context["pack_year_error"] = _(
            "No Pack Year covers today. Set up the current Pack Year to see pack statistics."
        )
        return context
    except PackYear.MultipleObjectsReturned:
        context["pack_year_error"] = _(
            "More than one Pack Year covers today. Correct the overlapping dates to see pack statistics."
        )
        return context

    context["pack_year"] = year
    if year_admin and year_admin.get_queryset(request).filter(pk=year.pk).exists():
        if year_admin.has_view_or_change_permission(request, year):
            context["pack_year_url"] = reverse("admin:calendars_packyear_change", args=[year.pk])

    for model, title in ((Scout, _("Cubs")), (Adult, _("Adults")), (Family, _("Active Families"))):
        model_admin = _visible_admin(request, model)
        if model_admin is None:
            continue
        queryset = model_admin.get_queryset(request)
        count = queryset.active_in(year).count()
        url = reverse(
            f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist",
            query={"active_in": year.pk},
        )
        context["dashboard_cards"].append({"title": title, "value": count, "url": url})
        if model is Scout:
            context["cub_total"] = count
            rows = list(queryset.counts_by_den(year))
            den_admin = _visible_admin(request, Den)
            den_links = {}
            if den_admin:
                for den in den_admin.get_queryset(request).filter(pk__in=[row["den_number"] for row in rows]):
                    if den_admin.has_view_or_change_permission(request, den):
                        den_links[den.pk] = reverse("admin:dens_den_change", args=[den.pk])
            rank_labels = dict(Rank.RankChoices.choices)
            for row in rows:
                context["den_rows"].append(
                    {
                        "name": _("Den %(number)s") % {"number": row["den_number"]},
                        "url": den_links.get(row["den_number"]),
                        "rank": rank_labels.get(row["rank"], _("No rank assigned")),
                        "count": row["cub_count"],
                        "cubs_url": reverse(
                            "admin:membership_scout_changelist",
                            query={"active_in": year.pk, "den": row["den_number"]},
                        ),
                    }
                )

    event_admin = _visible_admin(request, Event)
    if event_admin:
        statuses = (Event.CONFIRMED, Event.TENTATIVE)
        remaining = event_admin.get_queryset(request).filter(
            start__gte=now, start__date__lte=year.end_date, status__in=statuses
        )
        events_url = reverse(
            "admin:calendars_event_changelist",
            query={
                "start__gte": now.isoformat(),
                "start__date__lte": year.end_date.isoformat(),
                "status__in": ",".join(statuses),
            },
        )
        context["dashboard_cards"].append(
            {"title": _("Remaining Events"), "value": remaining.count(), "url": events_url}
        )
    return context
