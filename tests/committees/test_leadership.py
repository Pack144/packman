from django.core.cache import cache
from django.test import TestCase

from packman.calendars.factories import CurrentPackYearFactory, PackYearFactory
from packman.calendars.models import PackYear
from packman.committees.factories import (
    AkelaFactory,
    AssistantAkelaFactory,
    CommitteeFactory,
    CommitteeMemberFactory,
    DenLeaderFactory,
    LeadershipCommitteeFactory,
)
from packman.committees.leadership import leadership_title, leads_or_serves_on
from packman.membership.factories import ActiveScoutFactory, AdultFactory


class LeadsOrServesOnTestCase(TestCase):
    """
    leads_or_serves_on() is asked on every page render and must never raise.
    """

    def setUp(self):
        cache.clear()

    def test_leader_leads(self):
        CurrentPackYearFactory()
        akela = AkelaFactory()
        self.assertTrue(leads_or_serves_on(akela.member))

    def test_ordinary_committee_member_does_not_lead(self):
        CurrentPackYearFactory()
        assignment = CommitteeMemberFactory(committee=CommitteeFactory(name="Popcorn", slug="popcorn"))
        self.assertFalse(leads_or_serves_on(assignment.member))

    def test_ordinary_committee_member_serves_on_a_named_committee(self):
        CurrentPackYearFactory()
        assignment = CommitteeMemberFactory(committee=CommitteeFactory(name="Popcorn", slug="popcorn"))
        self.assertTrue(leads_or_serves_on(assignment.member, ["popcorn"]))

    def test_anonymous_and_cubs_never_lead(self):
        CurrentPackYearFactory()
        self.assertFalse(leads_or_serves_on(None))
        self.assertFalse(leads_or_serves_on(ActiveScoutFactory()))

    def test_no_pack_year_covers_today(self):
        """A pack with no current year loses the promo banner, not the whole site."""
        adult = AdultFactory()
        # Migrations seed the current year (dens.0002 evaluates a callable
        # default that calls get_or_create), so it has to be cleared here.
        PackYear.objects.all().delete()
        cache.clear()

        with self.assertRaises(PackYear.DoesNotExist):
            PackYear.objects.current()
        self.assertFalse(leads_or_serves_on(adult))

    def test_overlapping_pack_years(self):
        """Nothing stops the admin entering two years that both cover today."""
        current = CurrentPackYearFactory()
        PackYearFactory(
            year=current.year - 1,
            start_date=current.start_date,
            end_date=current.end_date,
        )
        cache.clear()

        with self.assertRaises(PackYear.MultipleObjectsReturned):
            PackYear.objects.current()
        self.assertFalse(leads_or_serves_on(AdultFactory()))


class LeadershipTitleTestCase(TestCase):
    def setUp(self):
        cache.clear()

    def test_titles_come_from_the_position(self):
        CurrentPackYearFactory()
        self.assertEqual(leadership_title(AkelaFactory().member), "Akela")
        self.assertEqual(leadership_title(AssistantAkelaFactory().member), "Assistant Akela")
        self.assertEqual(leadership_title(DenLeaderFactory().member), "Den Leader")

    def test_akela_outranks_a_den_they_also_lead(self):
        CurrentPackYearFactory()
        adult = AdultFactory()
        AkelaFactory(member=adult)
        DenLeaderFactory(member=adult, committee=CommitteeFactory(name="Dens", slug="dens"))
        self.assertEqual(leadership_title(adult), "Akela")

    def test_title_falls_back_to_the_committee_name(self):
        """A pack may record the title on a leadership committee instead."""
        CurrentPackYearFactory()
        assignment = CommitteeMemberFactory(
            committee=LeadershipCommitteeFactory(name="Den Leaders", slug="den-leaders")
        )
        self.assertEqual(leadership_title(assignment.member), "Den Leader")

    def test_no_title_without_an_assignment(self):
        CurrentPackYearFactory()
        self.assertIsNone(leadership_title(AdultFactory()))
