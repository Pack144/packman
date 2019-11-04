from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from .models import Account, Scout


class AccountChangeForm(UserChangeForm):

    class Meta(UserChangeForm):
        model = Account
        fields = ('email',)


class AccountCreationForm(UserCreationForm):

    class Meta(UserCreationForm):
        model = Account
        fields = ('email', )


class ScoutForm(forms.ModelForm):

    class Meta:
        model = Scout
        fields = ('__all__')