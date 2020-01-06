from django import forms
from django.forms import widgets
from django.forms.models import inlineformset_factory
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from allauth.account.forms import SignupForm as AllauthSignupForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field
from crispy_forms.bootstrap import FormActions, InlineRadios
from tempus_dominus.widgets import DatePicker

from address_book.forms import AddressForm, PhoneNumberForm
from address_book.models import Address, PhoneNumber

from .models import Member, AdultMember, ChildMember, Family

AddressFormSet = inlineformset_factory(AdultMember, Address, form=AddressForm, can_delete=True, extra=1)
PhoneNumberFormSet = inlineformset_factory(AdultMember, PhoneNumber, form=PhoneNumberForm, can_delete=True, extra=1)


class AdultMemberChange(UserChangeForm):
    class Meta:
        model = AdultMember
        fields = '__all__'


class AdultMemberCreation(UserCreationForm):
    class Meta:
        model = AdultMember
        fields = ('first_name', 'middle_name', 'last_name', 'suffix', 'nickname', 'email', 'is_published',
                  'is_subscribed', 'gender', 'role', 'photo')
        widgets = {
            'photo': widgets.FileInput,
        }

    def __init__(self, *args, **kwargs):
        super(AdultMemberCreation, self).__init__(*args, **kwargs)
        self.fields['password1'].required = False
        self.fields['password2'].required = False
        self.fields['role'].choices = (
            (AdultMember.PARENT, _('Parent')),
            (AdultMember.GUARDIAN, _('Guardian')),
        )
        self.helper = FormHelper(self)
        self.helper.form_id = 'parent_update'
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='col-md-4'),
                Column('middle_name', css_class='col-md-2 text-truncate'),
                Column('last_name', css_class='col-md-5'),
                Column('suffix', css_class='col-md-1'),
            ),
            'nickname',
            Row(
                Column('email'),
                Column('is_published'),
                Column('is_subscribed'),
            ),
            Row(
                Column(InlineRadios('gender')),
                Column(InlineRadios('role')),
            ),
            'photo',
            FormActions(
                Submit('save', 'Add Member', css_class='btn-success'),
            ),
        )


class Family(forms.ModelForm):
    class Meta:
        model = Family
        fields = '__all__'

    adults = forms.ModelMultipleChoiceField(queryset=AdultMember.objects.all(), required=False)
    children = forms.ModelMultipleChoiceField(queryset=ChildMember.objects.all(), required=False)

    def __init__(self, *args, **kwargs):
        super(Family, self).__init__(*args, **kwargs)
        if self.instance:
            self.fields['adults'].initial = self.instance.adults.all()
            self.fields['children'].initial = self.instance.children.all()

    def save(self, *args, **kwargs):
        # FIXME: 'commit' argument is not handled
        # TODO: Wrap reassignments into transaction
        # NOTE: Previously assigned Foos are silently reset
        instance = super(Family, self).save(commit=False)
        self.fields['adults'].initial.update(family=None)
        self.fields['children'].initial.update(family=None)
        self.cleaned_data['adults'].update(family=instance)
        self.cleaned_data['children'].update(family=instance)
        return instance


class AdultMemberForm(forms.ModelForm):
    class Meta:
        model = AdultMember
        fields = ('first_name', 'middle_name', 'last_name', 'suffix', 'nickname', 'email', 'is_published',
                  'is_subscribed', 'gender', 'role', 'photo')
        widgets = {
            'photo': widgets.FileInput,
        }

    def __init__(self, *args, **kwargs):
        super(AdultMemberForm, self).__init__(*args, **kwargs)
        self.fields['role'].choices = (
            (AdultMember.PARENT, _('Parent')),
            (AdultMember.GUARDIAN, _('Guardian')),
        )
        self.helper = FormHelper(self)
        self.helper.form_id = 'parent_update'
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='col-md-4'),
                Column('middle_name', css_class='col-md-2 text-truncate'),
                Column('last_name', css_class='col-md-5'),
                Column('suffix', css_class='col-md-1'),
            ),
            'nickname',
            Row(
                Column('email'),
                Column('is_published'),
                Column('is_subscribed'),
            ),
            Row(
                Column(InlineRadios('gender')),
                Column(InlineRadios('role')),
            ),
            'photo',
            FormActions(
                Submit('save', 'Save', css_class='btn-success'),
            ),
        )


class ChildMemberForm(forms.ModelForm):
    class Meta:
        model = ChildMember
        exclude = ('started_pack', 'status', 'den', 'family', 'pack_comments')
        widgets = {
            'date_of_birth': DatePicker(
                options={
                    'maxDate': str(timezone.now()),
                    'minDate': str(timezone.now().replace(year=timezone.now().year - 13)),
                    'defaultDate': str(timezone.now().replace(year=timezone.now().year - 6)),
                },
                attrs={
                    'append': 'far fa-calendar-alt',
                    'icon_toggle': True,
                },
            ),
            'photo': widgets.FileInput,
        }

    def __init__(self, *args, **kwargs):
        super(ChildMemberForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_id = 'scout_update'
        self.helper.render_required_fields = True
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='col-md-4'),
                Column('middle_name', css_class='col-md-2 text-truncate'),
                Column('last_name', css_class='col-md-5'),
                Column('suffix', css_class='col-md-1'),
            ),
            'nickname',
            InlineRadios('gender'),
            Field('date_of_birth', css_class='col-md-3'),
            'photo',
            Row(
                Column('school', css_class='col-md-8'),
                Column('started_school', css_class='col-md-4'),
            ),
            'reference',
            'member_comments',
            FormActions(
                Submit('save', 'Submit', css_class='btn-success'),
            ),
        )


class SignupForm(AllauthSignupForm, UserCreationForm):
    class Meta:
        model = AdultMember
        fields = ('first_name', 'middle_name', 'last_name', 'suffix', 'nickname', 'email', 'is_published',
                  'is_subscribed', 'gender', 'role', 'photo')
        widgets = {'gender': widgets.RadioSelect, 'role': widgets.RadioSelect, 'photo': widgets.FileInput}

    def __init__(self, *args, **kwargs):
        super(SignupForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_id = 'parent_update'
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='col-md-4'),
                Column('middle_name', css_class='col-md-2 text-truncate'),
                Column('last_name', css_class='col-md-5'),
                Column('suffix', css_class='col-md-1'),
            ),
            'nickname',
            Row(
                Column('email'),
                Column('is_published'),
                Column('is_subscribed'),
            ),
            Row(
                Column('password1'),
                Column('password2'),
            ),
            Row(
                Column(InlineRadios('gender')),
                Column(InlineRadios('role')),
            ),
            'photo',
            FormActions(
                Submit('save', 'Sign me up!', css_class='btn-success btn-lg'),
            ),
        )

    def signup(self, request, user):
        user.first_name = self.cleaned_data['first_name']
        user.middle_name = self.cleaned_data['middle_name']
        user.last_name = self.cleaned_data['last_name']
        user.suffix = self.cleaned_data['suffix']
        user.nickname = self.cleaned_data['nickname']
        user.gender = self.cleaned_data['gender']
        user.role = self.cleaned_data['role']
        user.photo = self.cleaned_data['photo']
        user.email = self.cleaned_data['email']
        user.is_subscribed = self.cleaned_data['is_subscribed']
        user.is_published = self.cleaned_data['is_published']
        user.family = Family.objects.create()
        user.save()
        return user

