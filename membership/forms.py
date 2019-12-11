from django import forms
from django.forms import widgets
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, Row, Column, Button, HTML, Field
from crispy_forms.bootstrap import FormActions, InlineRadios
from tempus_dominus.widgets import DatePicker

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
        fields = ('email',)


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
    gender = forms.ChoiceField(choices=Member.GENDER_CHOICES)

    class Meta:
        model = Member
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(MemberForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_id = 'member_update'
        self.helper.form_action = 'family_update'

        self.helper.layout = Layout(
            Fieldset(
                _('Name'),
                Row(
                    Column('first_name'),
                    Column('middle_name'),
                    Column('last_name'),
                    Column('suffix'),
                    css_class='form-row',
                ),
                Row('nickname', css_class='form-row'),
            ),
            'photo',
            InlineRadios('gender'),
            FormActions(
                Submit('save', 'Submit', css_class='btn-success'),
                Button('cancel', 'Cancel', css_class='btn-danger')
            )
        )


class ParentForm(forms.ModelForm):
    gender = forms.ChoiceField(choices=Member.GENDER_CHOICES)
    photo = forms.ImageField(widget=widgets.FileInput, required=False)

    class Meta:
        model = Parent
        exclude = ('role', 'family')

    def __init__(self, *args, **kwargs):
        super(ParentForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_id = 'parent_update'
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='col-md-4'),
                Column('middle_name', css_class='col-md-2'),
                Column('last_name', css_class='col-md-5'),
                Column('suffix', css_class='col-md-1'),
                css_class='form-row',
            ),
            'nickname',
            InlineRadios('gender'),
            'photo',
            Field('account', type='hidden'),
            Field('family', type='hidden'),
            FormActions(
                Submit('save', 'Submit', css_class='btn-success'),
                Button('cancel', 'Cancel', css_class='btn-danger')
            ),
        )


class ScoutForm(forms.ModelForm):
    birthday = forms.DateField(
        widget=DatePicker(
            options={
                'maxDate': str(timezone.now()),
                'minDate': str(timezone.now().replace(year=timezone.now().year - 13)),
            },
        ),
        initial=timezone.now().replace(year=timezone.now().year - 6),
    )
    gender = forms.ChoiceField(choices=Member.GENDER_CHOICES)
    photo = forms.ImageField(widget=widgets.FileInput, initial=Scout.photo)

    class Meta:
        model = Scout
        exclude = ('start_date', 'status', 'den', 'family')

    def __init__(self, *args, **kwargs):
        super(ScoutForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_id = 'scout_update'
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='col-md-4'),
                Column('middle_name', css_class='col-md-2'),
                Column('last_name', css_class='col-md-5'),
                Column('suffix', css_class='col-md-1'),
                css_class='form-row',
            ),
            'nickname',
            InlineRadios('gender'),
            'birthday',
            'photo',
            Row(
                Column('school', css_class='col-md-8'),
                Column('year_started_kindergarten', css_class='col-md-4'),
            ),
            'referral',
            'comments',
            FormActions(
                Submit('save', 'Submit', css_class='btn-success'),
                Button('cancel', 'Cancel', css_class='btn-danger')
            ),
        )
