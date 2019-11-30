from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit, Row, Column

from .models import Account, Member, Parent, Scout


class AccountChangeForm(UserChangeForm):

    class Meta(UserChangeForm):
        model = Account
        fields = ('email',)


class AccountCreationForm(UserCreationForm):

    class Meta(UserCreationForm):
        model = Account
        fields = ('email', )


class MemberForm(forms.ModelForm):

    class Meta:
        model = Member
        fields = ('__all__')

    def __init__(self, *args, **kwargs):
        super(MemberForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)


class ParentForm(forms.ModelForm):

    class Meta:
        model = Parent
        exclude = ('children', 'role', )

    def __init__(self, *args, **kwargs):
        super(ParentForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Row(
                Column('first_name'),
                Column('middle_name'),
                Column('last_name'),
                css_class='form-row'
            ),
            Row(
                Column('nickname'),
            ),
            ButtonHolder(
                Submit('submit', 'Update')
            )
        )


class ScoutForm(forms.ModelForm):

    class Meta:
        model = Scout
        exclude = ('status', 'start_date', )

    def __init__(self, *args, **kwargs):
        super(ScoutForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
