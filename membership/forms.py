from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit, Row, Column

from address_book.forms import AddressForm, PhoneNumberForm

from .models import Account, Family, Member, Parent, Scout

AddressFormSet = forms.formset_factory(AddressForm, extra=0, can_delete=True)
PhoneNumberFormSet = forms.formset_factory(PhoneNumberForm, extra=0, can_delete=True)


class AccountChangeForm(UserChangeForm):

    class Meta(UserChangeForm):
        model = Account
        fields = ('email',)


class AccountCreationForm(UserCreationForm):

    class Meta(UserCreationForm):
        model = Account
        fields = ('email', )


class FamilyForm(forms.ModelForm):

    class Meta:
        model = Family
        fields = '__all__'

    parents = forms.ModelMultipleChoiceField(queryset=Parent.objects.all(), required=False)
    children = forms.ModelMultipleChoiceField(queryset=Scout.objects.all(), required=False)

    def __init__(self, *args, **kwargs):
        super(FamilyForm, self).__init__(*args, **kwargs)
        if self.instance:
            self.fields['parents'].initial = self.instance.parents.all()
            self.fields['children'].initial = self.instance.children.all()

    def save(self, *args, **kwargs):
        # FIXME: 'commit' argument is not handled
        # TODO: Wrap reassignments into transaction
        # NOTE: Previously assigned Foos are silently reset
        instance = super(FamilyForm, self).save(commit=False)
        self.fields['parents'].initial.update(family=None)
        self.fields['children'].initial.update(family=None)
        self.cleaned_data['parents'].update(family=instance)
        self.cleaned_data['children'].update(family=instance)
        return instance


class MemberForm(forms.ModelForm):

    class Meta:
        model = Member
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(MemberForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)


class ParentForm(forms.ModelForm):

    class Meta:
        model = Parent
        exclude = ('role', )


class ScoutForm(forms.ModelForm):

    class Meta:
        model = Scout
        exclude = ('start_date', 'status', 'den', )

    def __init__(self, *args, **kwargs):
        super(ScoutForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
