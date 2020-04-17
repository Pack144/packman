import re

from django import forms

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
            Row(
                Column(
                    Field('street'),
                    Field('street2'),
                    Row(
                        Column('city', css_class='col-md-6'),
                        Column('state', css_class='col-md-3'),
                        Column('zip_code', css_class='col-md-3')
                    ),
                    Row(
                        Field('type'),
                        Field('published'),
                    ),
                    Field('uuid', type='hidden'),
                    Field('member', type='hidden'),
                ),
                Column(
                    Field('DELETE'),
                    css_class='col-1'
                ),
                css_class="address-dynamic-form mb-4"
            )
        )
        self.render_required_fields = True


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        exclude = ('member', 'venue', 'date_added')

    def __init__(self, *args, **kwargs):
        super(AddressForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            if visible.field.widget.__class__ == forms.widgets.TextInput:
                visible.field.widget.attrs['placeholder'] = visible.label
        self.helper = AddressFormHelper(self)
        self.fields['state'].choices = STATE_CHOICES + ((None, self.fields['state'].label),)


class PhoneNumberFormHelper(FormHelper):

    def __init__(self, *args, **kwargs):
        super(PhoneNumberFormHelper, self).__init__(*args, **kwargs)

        formtag_prefix = re.sub('-[0-9]+$', '', kwargs.get('prefix', ''))

        self.disable_csrf = True
        self.form_show_labels = False
        self.form_tag = False
        self.help_text_inline = True
        self.layout = Layout(
            Row(
                Column(
                    Field('number'),
                    Row(
                        Field('type'),
                        Field('published'),
                    ),
                    Field('uuid', type='hidden'),
                    Field('member', type='hidden'),
                ),
                Column(
                    Field('DELETE'),
                    css_class='col-1'
                ),
                css_class="phonenumber-dynamic-form mb-4"
            ),
        )


class PhoneNumberForm(forms.ModelForm):
    class Meta:
        model = PhoneNumber
        exclude = ('member', 'venue', 'date_added')

    def __init__(self, *args, **kwargs):
        super(PhoneNumberForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            if visible.field.widget.__class__ == forms.widgets.TextInput:
                visible.field.widget.attrs['placeholder'] = visible.label
        self.helper = PhoneNumberFormHelper(self)
