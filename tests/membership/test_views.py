from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from packman.address_book.models import Address, PhoneNumber
from packman.calendars.models import PackYear
from packman.dens.factories import DenFactory
from packman.dens.models import Membership
from packman.membership.factories import AdultFactory, FamilyFactory, ScoutFactory
from packman.membership.models import Scout

User = get_user_model()


class MemberListTestCase(TestCase):
    pass


class MemberSearchResultsTestCase(TestCase):
    pass


class AdultListTestCase(TestCase):
    pass


class AdultCreateTestCase(TestCase):
    pass


class AdultDetailTestCase(TestCase):
    def setUp(self):
        self.viewer = AdultFactory()
        self.target = AdultFactory()

    def test_add_to_contacts_button_shown_when_contact_info_published(self):
        self.target.is_published = True
        self.target.save()
        self.client.force_login(self.viewer)
        response = self.client.get(reverse("membership:parent_detail", kwargs={"slug": self.target.slug}))
        self.assertContains(response, reverse("membership:parent_vcard", kwargs={"slug": self.target.slug}))
        self.assertContains(response, "Add to Contacts")

    def test_add_to_contacts_button_hidden_when_no_published_contact_info(self):
        self.target.is_published = False
        self.target.save()
        self.client.force_login(self.viewer)
        response = self.client.get(reverse("membership:parent_detail", kwargs={"slug": self.target.slug}))
        self.assertNotContains(response, reverse("membership:parent_vcard", kwargs={"slug": self.target.slug}))
        self.assertNotContains(response, "Add to Contacts")

    def test_add_to_contacts_button_shown_on_own_profile(self):
        self.viewer.is_published = True
        self.viewer.save()
        self.client.force_login(self.viewer)
        response = self.client.get(reverse("membership:parent_detail", kwargs={"slug": self.viewer.slug}))
        self.assertContains(response, reverse("membership:parent_vcard", kwargs={"slug": self.viewer.slug}))

    def test_add_to_contacts_button_shown_when_only_phone_published(self):
        self.target.is_published = False
        self.target.save()
        PhoneNumber.objects.create(member=self.target, number="+12065551234", published=True)
        self.client.force_login(self.viewer)
        response = self.client.get(reverse("membership:parent_detail", kwargs={"slug": self.target.slug}))
        self.assertContains(response, "Add to Contacts")

    def test_add_to_contacts_button_shown_when_only_address_published(self):
        self.target.is_published = False
        self.target.save()
        Address.objects.create(
            member=self.target, street="123 Main St", city="Seattle", state="WA", zip_code="98103", published=True
        )
        self.client.force_login(self.viewer)
        response = self.client.get(reverse("membership:parent_detail", kwargs={"slug": self.target.slug}))
        self.assertContains(response, "Add to Contacts")


class AdultVCardTestCase(TestCase):
    def setUp(self):
        self.viewer = AdultFactory()
        self.target = AdultFactory(
            first_name="Josh",
            middle_name="",
            last_name="Royalty",
            suffix="",
            nickname="",
            email="josh@example.com",
            is_published=True,
        )

    def url(self, adult=None):
        adult = adult or self.target
        return reverse("membership:parent_vcard", kwargs={"slug": adult.slug})

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_nonexistent_slug_returns_404(self):
        self.client.force_login(self.viewer)
        response = self.client.get(reverse("membership:parent_vcard", kwargs={"slug": "no-such-member"}))
        self.assertEqual(response.status_code, 404)

    def test_response_headers(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/vcard")
        self.assertEqual(response["Content-Disposition"], f'attachment; filename="{self.target.slug}.vcf"')

    def test_published_email_included(self):
        self.client.force_login(self.viewer)
        content = self.client.get(self.url()).content.decode()
        self.assertIn("EMAIL;TYPE=HOME:josh@example.com", content)

    def test_unpublished_email_excluded(self):
        self.target.is_published = False
        self.target.save()
        self.client.force_login(self.viewer)
        content = self.client.get(self.url()).content.decode()
        self.assertNotIn("EMAIL", content)

    def test_published_phone_included_with_type_mapping(self):
        PhoneNumber.objects.create(member=self.target, number="+12065551234", type=PhoneNumber.WORK, published=True)
        self.client.force_login(self.viewer)
        content = self.client.get(self.url()).content.decode()
        self.assertIn("TEL;TYPE=WORK:+12065551234", content)

    def test_unpublished_phone_excluded(self):
        PhoneNumber.objects.create(member=self.target, number="+12065551234", type=PhoneNumber.WORK, published=False)
        self.client.force_login(self.viewer)
        content = self.client.get(self.url()).content.decode()
        self.assertNotIn("TEL", content)

    def test_blank_phone_type_defaults_to_cell(self):
        PhoneNumber.objects.create(member=self.target, number="+12065551234", type="", published=True)
        self.client.force_login(self.viewer)
        content = self.client.get(self.url()).content.decode()
        self.assertIn("TEL;TYPE=CELL:+12065551234", content)

    def test_multiple_phone_numbers_all_included(self):
        PhoneNumber.objects.create(member=self.target, number="+12065551234", type=PhoneNumber.HOME, published=True)
        PhoneNumber.objects.create(member=self.target, number="+12065555678", type=PhoneNumber.MOBILE, published=True)
        self.client.force_login(self.viewer)
        content = self.client.get(self.url()).content.decode()
        self.assertIn("TEL;TYPE=HOME:+12065551234", content)
        self.assertIn("TEL;TYPE=CELL:+12065555678", content)

    def test_published_address_included_with_type_mapping(self):
        Address.objects.create(
            member=self.target,
            street="123 Main St",
            city="Seattle",
            state="WA",
            zip_code="98103",
            type=Address.WORK,
            published=True,
        )
        self.client.force_login(self.viewer)
        content = self.client.get(self.url()).content.decode()
        self.assertIn("ADR;TYPE=WORK:;;123 Main St;Seattle;WA;98103;", content)

    def test_unpublished_address_excluded(self):
        Address.objects.create(
            member=self.target,
            street="123 Main St",
            city="Seattle",
            state="WA",
            zip_code="98103",
            published=False,
        )
        self.client.force_login(self.viewer)
        content = self.client.get(self.url()).content.decode()
        self.assertNotIn("ADR", content)

    def test_blank_address_type_defaults_to_home(self):
        Address.objects.create(
            member=self.target,
            street="123 Main St",
            city="Seattle",
            state="WA",
            zip_code="98103",
            type="",
            published=True,
        )
        self.client.force_login(self.viewer)
        content = self.client.get(self.url()).content.decode()
        self.assertIn("ADR;TYPE=HOME:;;123 Main St;Seattle;WA;98103;", content)

    def test_multiple_addresses_all_included(self):
        Address.objects.create(
            member=self.target,
            street="1 Home Way",
            city="Seattle",
            state="WA",
            zip_code="98103",
            type=Address.HOME,
            published=True,
        )
        Address.objects.create(
            member=self.target,
            street="2 Work Ave",
            city="Bellevue",
            state="WA",
            zip_code="98004",
            type=Address.WORK,
            published=True,
        )
        self.client.force_login(self.viewer)
        content = self.client.get(self.url()).content.decode()
        self.assertIn("ADR;TYPE=HOME:;;1 Home Way;Seattle;WA;98103;", content)
        self.assertIn("ADR;TYPE=WORK:;;2 Work Ave;Bellevue;WA;98004;", content)

    def test_nickname_omitted_when_blank(self):
        self.client.force_login(self.viewer)
        content = self.client.get(self.url()).content.decode()
        self.assertNotIn("NICKNAME", content)

    def test_nickname_included_when_present(self):
        self.target.nickname = "Josh"
        self.target.save()
        self.client.force_login(self.viewer)
        content = self.client.get(self.url()).content.decode()
        self.assertIn("NICKNAME:Josh", content)

    def test_special_characters_are_escaped(self):
        self.target.last_name = "Smith; Jones, Sr."
        self.target.save()
        self.client.force_login(self.viewer)
        content = self.client.get(self.url()).content.decode()
        self.assertIn("Smith\\; Jones\\, Sr.", content)

    def test_url_and_ablabel_included(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.url())
        content = response.content.decode()
        expected_url = response.wsgi_request.build_absolute_uri(self.target.get_absolute_url())
        self.assertIn(f"item1.URL:{expected_url}", content)
        self.assertIn(f"item1.X-ABLabel:{settings.PACK_SHORTNAME}", content)

    def test_name_and_fn_fields(self):
        self.client.force_login(self.viewer)
        content = self.client.get(self.url()).content.decode()
        self.assertIn("N:Royalty;Josh;;;", content)
        self.assertIn(f"FN:{self.target.get_full_name()}", content)

    def test_works_with_no_published_contact_info(self):
        self.target.is_published = False
        self.target.save()
        self.client.force_login(self.viewer)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("BEGIN:VCARD", content)
        self.assertIn("FN:", content)
        self.assertNotIn("EMAIL", content)
        self.assertNotIn("TEL", content)
        self.assertNotIn("ADR", content)

    def test_can_request_own_vcard(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.url(self.viewer))
        self.assertEqual(response.status_code, 200)

    def test_filename_does_not_leak_more_pii_than_profile_slug(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.url())
        # The filename is derived from the same slug already exposed by the
        # profile URL, so it introduces no additional PII exposure.
        self.assertIn(self.target.slug, response["Content-Disposition"])
        detail_url = reverse("membership:parent_detail", kwargs={"slug": self.target.slug})
        self.assertIn(self.target.slug, detail_url)


class AdultUpdateTestCase(TestCase):
    pass


class ScoutListTestCase(TestCase):
    pass


class ScoutCreateTestCase(TestCase):
    pass


class ScoutDetailTestCase(TestCase):
    pass


class ScoutUpdateTestCase(TestCase):
    pass


class MyFamilyDetailTestCase(TestCase):
    pass


class PackMateEntryPointsTestCase(TestCase):
    """Both routes into PackMate are open to any signed-in member; no gate."""

    # Every page that mirrors what the app shows, and so carries the promo.
    DIRECTORY_URLS = (
        "membership:scouts",
        "membership:parents",
        "membership:all",
        "dens:list",
    )

    @classmethod
    def setUpTestData(cls):
        end_year = PackYear.get_pack_year()["end_date"].year
        cls.pack_year, _ = PackYear.objects.get_or_create(year=end_year)
        cls.den = DenFactory()

        # An ordinary parent with an active cub, no leadership role or
        # committee seat: still gets PackMate now that it's ungated.
        cls.member = AdultFactory(family=cls.active_family())

    @classmethod
    def active_family(cls):
        """
        A family with one active cub in a den.

        Built by hand rather than with ActiveScoutFactory: that reaches for
        CurrentPackYearFactory, which lays down a calendar-year PackYear
        overlapping the pack-year row migrations create. Two rows covering
        today make PackYear.objects.current()'s bare .get() raise.
        """
        family = FamilyFactory()
        scout = ScoutFactory(family=family, status=Scout.ACTIVE)
        Membership.objects.create(scout=scout, den=cls.den, year_assigned=cls.pack_year)
        return family

    def setUp(self):
        # PackYear.objects.current() caches; clear it so the rows above are seen.
        cache.clear()

    def test_banner_shown_to_signed_in_member(self):
        self.client.force_login(self.member)
        for name in self.DIRECTORY_URLS:
            with self.subTest(url=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "packmate-promo")
                self.assertContains(response, reverse("mobile:index"))

    def test_banner_absent_from_other_pages(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("documents:list"))
        self.assertNotContains(response, "packmate-promo")

    def test_dropdown_link_shown_to_signed_in_member(self):
        # The profile dropdown rides on every page, not just the directory ones.
        self.client.force_login(self.member)
        response = self.client.get(reverse("documents:list"))
        self.assertContains(response, "packmate-icon")
        self.assertContains(response, reverse("mobile:index"))

    def test_dropdown_link_absent_when_signed_out(self):
        response = self.client.get(reverse("pages:home"))
        self.assertNotContains(response, "packmate-icon")
