from rest_framework.permissions import BasePermission

from packman.membership.models import Adult


class IsActiveMemberOrContributor(BasePermission):
    """
    Mirrors packman.membership.mixins.ActiveMemberOrContributorTest: only
    parents with active cubs, or contributors, may use the Pack Directory.
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(user.is_authenticated and (user.active() or user.role == Adult.CONTRIBUTOR))
