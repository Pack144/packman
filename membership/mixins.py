from django.contrib.auth.mixins import UserPassesTestMixin

from .models import AdultMember


class ActiveMemberTest(UserPassesTestMixin):
    """ Parents with active cubs should be allowed to view this page """
    def test_func(self):
        if self.request.user.is_authenticated:
            return self.request.user.active


class ContributorTest(UserPassesTestMixin):
    """ Contributors should be allowed to view this page """
    def test_func(self):
        if self.request.user.is_authenticated:
            return self.request.user.role == AdultMember.CONTRIBUTOR


class ActiveMemberOrContributorTest(UserPassesTestMixin):
    """ Parents with active cubs should be allowed to view this page """
    def test_func(self):
        if self.request.user.is_authenticated:
            if self.request.user.active or self.request.user.role == AdultMember.CONTRIBUTOR:
                return True
