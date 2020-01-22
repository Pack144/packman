from django import forms
from django.utils.translation import ugettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field
from localflavor.us.models import STATE_CHOICES

from .models import Address, PhoneNumber


class AddressFormHelper(FormHelper):

    def __init__(self, *args, **kwargs):
        super(AddressFormHelper, self).__init__(*args, **kwargs)
        self.disable_csrf = True
        self.form_show_labels = False
        self.form_tag = False
        self.help_text_inline = True
        self.layout = Layout(
            Field('type', css_class='col-4'),
            'street',
            'street2',
            Row(
                Column('city', css_class='col-md-6'),
                Column('state', css_class='col-md-3'),
                Column('zip_code', css_class='col-md-3')
            ),
            'published',
            Field('id', type='hidden'),
            Field('member', type='hidden'),
        )
        self.render_required_fields = True


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        exclude = ('member', 'venue', 'date_added')

    def __init__(self, *args, **kwargs):
        super(AddressForm, self).__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if field.widget.__class__ == forms.widgets.TextInput:
                field.widget.attrs['placeholder'] = field.label
        self.helper = AddressFormHelper(self)
        self.fields['state'].choices = STATE_CHOICES + ((None, _('Choose a state')),)


class PhoneNumberFormHelper(FormHelper):

    def __init__(self, *args, **kwargs):
        super(PhoneNumberFormHelper, self).__init__(*args, **kwargs)
        self.disable_csrf = True
        self.form_show_labels = False
        self.form_tag = False
        self.help_text_inline = True
        self.layout = Layout(
            Row(
                Column('number', css_class='col-md-6'),
                Column('type', css_class='col-md-2'),
            ),
            Field('published'),
            Field('id', type='hidden'),
            Field('member', type='hidden'),
        )
        self.render_required_fields = True


class PhoneNumberForm(forms.ModelForm):
    class Meta:
        model = PhoneNumber
        exclude = ('member', 'venue', 'date_added')

    def __init__(self, *args, **kwargs):
        super(PhoneNumberForm, self).__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if field.widget.__class__ == forms.widgets.TextInput:
                field.widget.attrs['placeholder'] = field.label
        self.helper = PhoneNumberFormHelper(self)
