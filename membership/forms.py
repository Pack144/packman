from django.contrib.auth.forms import UserChangeForm

from django_registration.forms import RegistrationForm

from .models import Account


class AccountCreationForm(RegistrationForm):
    class Meta(RegistrationForm.Meta):
        model = Account
        fields = ('email',)


class AccountChangeForm(UserChangeForm):
    class Meta:
        model = Account
        fields = ('email',)
