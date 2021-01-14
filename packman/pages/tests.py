from django.test import TestCase
from django.urls import resolve, reverse

from .views import AboutPageView, HistoryPageView, HomePageView, SignUpPageView


class AboutPageTests(TestCase):

    def setUp(self):
        url = reverse('pages:about')
        self.response = self.client.get(url)

    def test_aboutpage_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_aboutpage_template(self):
        self.assertTemplateUsed(self.response, 'pages/about_page.html')

    def test_aboutpage_url_resolves_aboutpageview(self):
        view = resolve('/about/')
        self.assertEqual(
            view.func.__name__,
            AboutPageView.as_view().__name__
        )


class HomePageTests(TestCase):

    def setUp(self):
        url = reverse('pages:home')
        self.response = self.client.get(url)

    def test_homepage_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_homepage_template(self):
        self.assertTemplateUsed(self.response, 'pages/home_page.html')

    def test_homepage_url_resolves_homepageview(self):  # new
        view = resolve('/')
        self.assertEqual(
            view.func.__name__,
            HomePageView.as_view().__name__
        )


class HistoryPageTests(TestCase):

    def setUp(self):
        url = reverse('pages:history')
        self.response = self.client.get(url)

    def test_historypage_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_historypage_template(self):
        self.assertTemplateUsed(self.response, 'pages/history_page.html')

    def test_historypage_url_resolves_historypageview(self):
        view = resolve('/history/')
        self.assertEqual(
            view.func.__name__,
            HistoryPageView.as_view().__name__
        )


class SignUpPageTests(TestCase):

    def setUp(self):
        url = reverse('pages:signup')
        self.response = self.client.get(url)

    def test_signuppage_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_signuppage_template(self):
        self.assertTemplateUsed(self.response, 'pages/signup_page.html')

    def test_signuppage_url_resolves_signuppageview(self):
        view = resolve('/signup/')
        self.assertEqual(
            view.func.__name__,
            SignUpPageView.as_view().__name__
        )
