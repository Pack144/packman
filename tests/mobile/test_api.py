from django.urls import reverse

from packman.address_book.models import PhoneNumber

from .base import MobileDirectoryTestCase


class HomeAPITestCase(MobileDirectoryTestCase):
    def test_anonymous_is_forbidden(self):
        response = self.client.get(reverse("mobile:api-home"))
        self.assertEqual(response.status_code, 403)

    def test_returns_the_signed_in_users_family(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("mobile:api-home"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["family"]["name"], self.family.name)
        self.assertEqual(len(data["family"]["children"]), 1)
        self.assertEqual(data["family"]["children"][0]["name"], self.scout.short_name)


class MyDensAPITestCase(MobileDirectoryTestCase):
    def test_returns_the_dens_for_the_users_own_cubs(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("mobile:api-dens-mine"))
        self.assertEqual(response.status_code, 200)
        dens = response.json()["dens"]
        self.assertEqual(len(dens), 1)
        self.assertEqual(dens[0]["number"], self.den.number)
        self.assertEqual(dens[0]["rank"], "Wolf")
        self.assertEqual(len(dens[0]["roster"]), 1)
        self.assertEqual(dens[0]["roster"][0]["scout"]["name"], self.scout.short_name)
        self.assertEqual(len(dens[0]["leaders"]), 1)
        self.assertEqual(dens[0]["leaders"][0]["name"], self.leader.get_full_name())


class DenListAPITestCase(MobileDirectoryTestCase):
    def test_flags_the_users_own_den(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("mobile:api-dens"))
        self.assertEqual(response.status_code, 200)
        dens = response.json()["dens"]
        mine = next(d for d in dens if d["number"] == self.den.number)
        self.assertTrue(mine["is_mine"])
        self.assertEqual(mine["my_cub"], self.scout.short_name)


class DenDetailAPITestCase(MobileDirectoryTestCase):
    def test_returns_roster_and_leaders(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("mobile:api-den-detail", args=[self.den.number]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["number"], self.den.number)
        self.assertEqual(len(data["roster"]), 1)

    def test_unknown_den_is_404(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("mobile:api-den-detail", args=[9999]))
        self.assertEqual(response.status_code, 404)


class SearchAPITestCase(MobileDirectoryTestCase):
    def test_finds_the_cub_by_name(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("mobile:api-search"), {"q": self.scout.first_name})
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertTrue(any(r["slug"] == self.scout.slug and r["type"] == "cub" for r in results))

    def test_empty_query_returns_no_results(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("mobile:api-search"), {"q": ""})
        self.assertEqual(response.json()["results"], [])


class MemberDetailAPITestCase(MobileDirectoryTestCase):
    def test_scout_profile_lists_parent(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("mobile:api-member-detail", args=[self.scout.slug]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["is_scout"])
        self.assertIn(self.parent.slug, [f["slug"] for f in data["family"]])

    def test_unpublished_email_is_hidden(self):
        self.parent.is_published = False
        self.parent.save()
        self.client.force_login(self.parent)
        response = self.client.get(reverse("mobile:api-member-detail", args=[self.parent.slug]))
        self.assertEqual(response.json()["emails"], [])

    def test_unpublished_phone_number_is_hidden(self):
        PhoneNumber.objects.create(number="+15105551234", member=self.parent, published=False)
        PhoneNumber.objects.create(number="+15105554321", member=self.parent, published=True)
        self.client.force_login(self.parent)
        response = self.client.get(reverse("mobile:api-member-detail", args=[self.parent.slug]))
        phone_numbers = response.json()["phone_numbers"]
        self.assertEqual(len(phone_numbers), 1)

    def test_member_outside_visibility_scope_is_404(self):
        from packman.membership.factories import AdultFactory, FamilyFactory
        from packman.membership.models import Adult

        stranger = AdultFactory(family=FamilyFactory(), role=Adult.PARENT)  # no active scouts
        self.client.force_login(self.parent)
        response = self.client.get(reverse("mobile:api-member-detail", args=[stranger.slug]))
        self.assertEqual(response.status_code, 404)
