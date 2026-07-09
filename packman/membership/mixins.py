from django.contrib.auth.mixins import UserPassesTestMixin

from .models import Adult


def is_active_member_or_contributor(user):
    """Parents with active cubs, or contributors, may view the Pack Directory."""
    return bool(user.is_authenticated and (user.active() or user.role == Adult.CONTRIBUTOR))


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
        return is_active_member_or_contributor(self.request.user)
