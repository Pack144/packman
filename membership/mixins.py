from django.contrib.auth.mixins import UserPassesTestMixin


class ActiveMemberTestMixin(UserPassesTestMixin):
    """ Parents with active cubs should be allowed to view this page """
    def test_func(self):
        if self.request.user.is_authenticated:
            return self.request.user.profile.is_active


class ContributorTestMixin(UserPassesTestMixin):
    """ Contributors should be allowed to view this page """
    def test_func(self):
        if self.request.user.is_authenticated:
            return self.request.user.profile.role == 'C'


class ActiveMemberOrContributorTestMixin(UserPassesTestMixin):
    """ Parents with active cubs should be allowed to view this page """
    def test_func(self):
        if self.request.user.is_authenticated:
            if self.request.user.profile.is_active:
                return True
            elif self.request.user.profile.role == 'C':
                return True
