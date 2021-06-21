from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission


class CommitteePermissionsBackend(ModelBackend):
    def _get_group_permissions(self, user_obj):
        """
        Return a set of permission strings for the user `user_obj` based
        on the committees they belong to.
        """
        recent_committees = user_obj.committees.recent()
        if recent_committees.filter(are_superusers=True):
            return Permission.objects.all()
        return Permission.objects.filter(committee__in=recent_committees)
