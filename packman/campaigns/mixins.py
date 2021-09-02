from django.contrib.auth.mixins import UserPassesTestMixin
from django.utils.translation import gettext as _


class UserIsSellerFamilyTest(UserPassesTestMixin):

    permission_denied_message = _(
        "You are not authorized to view this page. You must be a member of the seller's family."
    )

    def test_func(self):
        if self.request.user.is_authenticated:
            self.object = self.get_object()
            return self.request.user.family == self.object.seller.family
