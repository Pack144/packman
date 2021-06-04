from django.contrib.auth.mixins import UserPassesTestMixin

from .models import Adult


class ActiveMemberTest(UserPassesTestMixin):
    """Parents with active cubs should be allowed to view this page"""

    def test_func(self):
        if self.request.user.is_authenticated:
            return self.request.user.active()


class ContributorTest(UserPassesTestMixin):
    """Contributors should be allowed to view this page"""

    def test_func(self):
        if self.request.user.is_authenticated:
            return self.request.user.role == Adult.CONTRIBUTOR


class ActiveMemberOrContributorTest(UserPassesTestMixin):
    """Parents with active cubs should be allowed to view this page"""

    def test_func(self):
        if self.request.user.is_authenticated and (
            self.request.user.active() or self.request.user.role == Adult.CONTRIBUTOR
        ):
            return True
