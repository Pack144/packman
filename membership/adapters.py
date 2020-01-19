from allauth.account.adapter import DefaultAccountAdapter

from membership.models import Family


class MemberAdapter(DefaultAccountAdapter):

    def save_user(self, request, user, form, commit=True):
        """
        This is called when saving user via allauth registration.
        We override this to set additional data on user object.
        """
        # Do not persist the user yet so we pass commit=False
        # (last argument)
        user = super(MemberAdapter, self).save_user(request, user, form, commit=False)
        user.middle_name = form.cleaned_data['middle_name']
        user.suffix = form.cleaned_data['suffix']
        user.nickname = form.cleaned_data['nickname']
        user.gender = form.cleaned_data['gender']
        user.role = form.cleaned_data['role']
        user.photo = form.cleaned_data['photo']
        user.is_published = form.cleaned_data['is_published']
        user.family = Family.objects.create()

        user.save()
