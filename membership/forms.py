from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from .models import Account, Parent, Scout


class AccountChangeForm(UserChangeForm):

    class Meta(UserChangeForm):
        model = Account
        fields = ('email',)


class AccountCreationForm(UserCreationForm):

    class Meta(UserCreationForm):
        model = Account
        fields = ('email', )


class ParentForm(forms.ModelForm):

    class Meta:
        model = Parent
        exclude = ('children', 'role', )


class ScoutForm(forms.ModelForm):

    class Meta:
        model = Scout
        exclude = ('status', 'start_date', )
