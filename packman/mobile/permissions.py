from rest_framework.permissions import BasePermission

from packman.membership.mixins import is_active_member_or_contributor


class IsActiveMemberOrContributor(BasePermission):
    """
    Shares packman.membership.mixins.is_active_member_or_contributor with the
    shell's ActiveMemberOrContributorTest: only parents with active cubs, or
    contributors, may use the Pack Directory.
    """

    def has_permission(self, request, view):
        return is_active_member_or_contributor(request.user)
