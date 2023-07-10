from __future__ import annotations

from http import HTTPStatus

from django.contrib.admin.sites import AdminSite, all_sites
from django.contrib.auth import get_user_model
from django.db.models import Model
from django.test import TestCase
from django.urls import reverse

from unittest_parametrize import ParametrizedTestCase, param, parametrize

User = get_user_model()

each_model_admin = parametrize(
    "site,model,model_admin",
    [
        param(
            site,
            model,
            model_admin,
            id=f"{site.name}_{str(model_admin).replace('.', '_')}",
        )
        for site in all_sites
        for model, model_admin in site._registry.items()
    ],
)


class ModelAdminTests(ParametrizedTestCase, TestCase):
    user: User

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(email="admin@example.com", password="test")  # nosec B106

    def setUp(self):
        self.client.force_login(self.user)

    def make_url(self, site: AdminSite, model: type[Model], page: str) -> str:
        return reverse(f"{site.name}:{model._meta.app_label}_{model._meta.model_name}_{page}")

    @each_model_admin
    def test_changelist(self, site, model, model_admin):
        url = self.make_url(site, model, "changelist")
        response = self.client.get(url, {"q": "example.com"})
        self.assertEqual(response.status_code, HTTPStatus.OK)

    @each_model_admin
    def test_add(self, site, model, model_admin):
        url = self.make_url(site, model, "add")
        response = self.client.get(url)
        self.assertIn(
            response.status_code,
            (
                HTTPStatus.OK,
                HTTPStatus.FORBIDDEN,  # some admin classes blanket disallow "add"
            ),
        )
