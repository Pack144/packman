from django import forms
from django.forms import widgets
from django.forms.models import inlineformset_factory
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field
from crispy_forms.bootstrap import FormActions, InlineRadios, AppendedText
from tempus_dominus.widgets import DatePicker

from address_book.forms import AddressForm, PhoneNumberForm
from address_book.models import Address, PhoneNumber

from .models import Adult, Scout, Family

AddressFormSet = inlineformset_factory(
    Adult,
    Address,
    form=AddressForm,
    can_delete=True,
    extra=1,
)
PhoneNumberFormSet = inlineformset_factory(
    Adult,
    PhoneNumber,
    form=PhoneNumberForm,
    can_delete=True,
    extra=1,
)


class AdminAdultChange(UserChangeForm):
    class Meta:
        model = Adult
        fields = '__all__'


class AdminAdultCreation(UserCreationForm):
    class Meta:
        model = Adult
        fields = '__all__'


class AdultCreation(UserCreationForm):
    class Meta:
        model = Adult
        fields = (
            'first_name', 'middle_name', 'last_name', 'suffix', 'nickname',
            'email', 'is_published', 'gender', 'role', 'photo'
        )
        widgets = {
            'photo': widgets.FileInput,
        }

    def __init__(self, *args, **kwargs):
        super(AdultCreation, self).__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if field.widget.__class__ == forms.widgets.TextInput or field.widget.__class__ == forms.widgets.EmailInput:
                field.widget.attrs['placeholder'] = field.label
        self.fields['password1'].required = False
        self.fields['password2'].required = False
        self.fields['role'].choices = (
            (Adult.PARENT, _("Parent")),
            (Adult.GUARDIAN, _("Guardian")),
        )
        self.helper = FormHelper(self)
        self.helper.form_id = 'parent_update'
        self.helper.form_tag = False
        self.helper.form_show_labels = False
        self.helper.help_text_inline = True
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='col-md-4', ),
                Column('middle_name', css_class='col-md-2 text-truncate'),
                Column('last_name', css_class='col-md-5'),
                Column('suffix', css_class='col-md-1'),
            ),
            'nickname',
            Row(
                Column('email'),
                Column('is_published'),
            ),
            Row(
                Column(InlineRadios('gender')),
                Column(InlineRadios('role')),
            ),
            'photo',
        )


class FamilyForm(forms.ModelForm):
    class Meta:
        model = Family
        fields = '__all__'

    adults = forms.ModelMultipleChoiceField(
        queryset=Adult.objects.all(),
        required=False,
    )
    children = forms.ModelMultipleChoiceField(
        queryset=Scout.objects.all(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super(FamilyForm, self).__init__(*args, **kwargs)
        if self.instance:
            self.fields['adults'].initial = self.instance.adults.all()
            self.fields['children'].initial = self.instance.children.all()

    def save(self, *args, **kwargs):
        # FIXME: 'commit' argument is not handled
        # TODO: Wrap reassignments into transaction
        # NOTE: Previously assigned Foos are silently reset
        instance = super(FamilyForm, self).save(commit=False)
        self.fields['adults'].initial.update(family=None)
        self.fields['children'].initial.update(family=None)
        self.cleaned_data['adults'].update(family=instance)
        self.cleaned_data['children'].update(family=instance)
        return instance


class AdultForm(forms.ModelForm):
    class Meta:
        model = Adult
        fields = (
            'first_name', 'middle_name', 'last_name', 'suffix', 'nickname',
            'email', 'is_published', 'gender', 'role', 'photo'
        )
        widgets = {
            'photo': widgets.FileInput,
        }

    def __init__(self, *args, **kwargs):
        super(AdultForm, self).__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if field.widget.__class__ == forms.widgets.TextInput or field.widget.__class__ == forms.widgets.EmailInput:
                field.widget.attrs['placeholder'] = field.label
        self.fields['role'].choices = (
            (Adult.PARENT, _("Parent")),
            (Adult.GUARDIAN, _("Guardian")),
        )
        self.helper = FormHelper(self)
        self.helper.form_id = 'parent_update'
        self.helper.form_tag = False
        self.helper.form_show_labels = False
        self.render_required_fields = True
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
            ),
            Row(
                Column(InlineRadios('gender')),
                Column(InlineRadios('role')),
            ),
            'photo',
        )


class ScoutForm(forms.ModelForm):
    class Meta:
        model = Scout
        fields = (
            'first_name',
            'middle_name',
            'nickname',
            'last_name',
            'suffix',
            'gender',
            'date_of_birth',
            'photo',
            'school',
            'started_school',
            'reference',
            'member_comments',
        )
        widgets = {
            'date_of_birth': DatePicker(
                options={
                    'maxDate': str(timezone.now()),
                    'minDate': str(timezone.now().replace(
                        year=timezone.now().year - 13)
                    ),
                    'defaultDate': str(timezone.now().replace(
                        year=timezone.now().year - 6)
                    ),
                },
                attrs={
                    'append': 'far fa-calendar-alt',
                    'icon_toggle': True,
                    'placeholder': _("Birthday")
                },
            ),
            'photo': widgets.FileInput,
        }

    def __init__(self, *args, **kwargs):
        super(ScoutForm, self).__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if field.widget.__class__ == forms.widgets.TextInput:
                field.widget.attrs['placeholder'] = field.label
        self.helper = FormHelper(self)
        self.helper.form_id = 'scout_update'
        self.helper.form_show_labels = True
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
            Field('photo'),
            Row(
                Column(
                    Field('school', css_class='custom-select'),
                    css_class='col-md-8',
                ),
                Column(
                    AppendedText('started_school', 'grade'),
                    css_class='col-md-4',
                ),
            ),
            'reference',
            'member_comments',
            FormActions(
                Submit('save', 'Submit', css_class='btn-success btn-lg'),
            ),
        )


class SignupForm(UserCreationForm):
    class Meta:
        model = Adult
        fields = (
            'first_name',
            'middle_name',
            'last_name',
            'suffix',
            'nickname',
            'email',
            'is_published',
            'gender',
            'role',
            'photo'
        )
        widgets = {
            'gender': widgets.RadioSelect,
            'role': widgets.RadioSelect,
            'photo': widgets.FileInput
        }

    def __init__(self, *args, **kwargs):
        super(SignupForm, self).__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if field.widget.__class__ == forms.widgets.TextInput or field.widget.__class__ == forms.widgets.EmailInput:
                field.widget.attrs['placeholder'] = field.label
        self.fields['role'].choices = (
            (Adult.PARENT, _('Parent')),
            (Adult.GUARDIAN, _('Guardian')),
        )
        self.helper = FormHelper(self)
        self.helper.form_id = 'parent_update'
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='col-md-4'),
                Column('middle_name', css_class='col-md-2 text-truncate'),
                Column('last_name', css_class='col-md-5'),
                Column('suffix', css_class='col-md-1'),
            ),
            'nickname',
            Row(
                Column('email', autofocus=None),
                Column('is_published'),
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
        user.is_published = self.cleaned_data['is_published']
        user.family = FamilyForm.objects.create()
        user.save()
        return user
