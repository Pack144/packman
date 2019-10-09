from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import Account


class AccountChangeForm(UserChangeForm):

    class Meta(UserChangeForm):
        model = Account
        fields = ('email',)


class AccountCreationForm(UserCreationForm):

    class Meta(UserCreationForm):
        model = Account
        fields = ('email', )

