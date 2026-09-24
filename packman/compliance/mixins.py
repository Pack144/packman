from django.contrib.auth.mixins import UserPassesTestMixin
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from packman.calendars.models import PackYear
from packman.committees.leadership import leads_a_den


class UserIsOwnFamilyOrLeadershipTest(UserPassesTestMixin):
    """
    Families may see their own requirements; leadership may see anyone's.

    Modelled on campaigns.mixins.UserIsSellerFamilyTest.
    """

    permission_denied_message = _("You may only view your own family's requirements.")

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.has_perm("compliance.view_all_records"):
            return True

        self.object = self.get_object()
        return bool(user.family_id) and user.family_id == self.object.pk


class UserLeadsADenTest(UserPassesTestMixin):
    """
    Only Adults leading a den this Pack Year may open the den dashboard.

    compliance.view_all_records is deliberately not a way in. Packs commonly
    attach it to the committee den leaders sit on, and honouring it here would
    hand every den leader every den; pack leadership who hold it already have
    the pack-wide dashboard.
    """

    permission_denied_message = _("You may only view the requirements of a den you lead.")

    def test_func(self):
        return leads_a_den(self.request.user)


class PackYearContextMixin:
    """
    Supplies the year switcher, following the available/current/viewing shape
    that campaigns.views.OrderListView established.

    The year comes from an optional URL kwarg so that every page has a stable,
    linkable address for a given year. Each view names the route its switcher
    should link to, since they take different kwargs.
    """

    year_url_name = None

    def get_year_url_kwargs(self):
        """Extra kwargs the switcher route needs besides the year itself."""
        return {}

    def get_pack_years(self):
        current = PackYear.objects.current()
        viewing = current

        if "year" in self.kwargs:
            viewing = PackYear.objects.filter(year=self.kwargs["year"]).first() or current

        available = PackYear.objects.filter(requirement_record__isnull=False).distinct()
        if self.year_url_name:
            extra = self.get_year_url_kwargs()
            available = [
                {"year": year, "url": reverse(self.year_url_name, kwargs={**extra, "year": year.year})}
                for year in available
            ]

        return {"available": available, "current": current, "viewing": viewing}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["years"] = self.get_pack_years()
        return context
