from django import forms
from django.forms import widgets

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field

from .models import Address, PhoneNumber


class AddressForm(forms.ModelForm):

    class Meta:
        model = Address
        exclude = ('member', 'venue', 'date_added')

    def __init__(self, *args, **kwargs):
        super(AddressForm, self).__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if field.widget.__class__ == forms.widgets.TextInput:
                field.widget.attrs['placeholder'] = field.label
        self.fields['state'].widget.empty_value = 'State'
        self.helper = FormHelper(self)
        self.helper.disable_csrf = True
        self.helper.form_show_labels = False
        self.helper.form_tag = False
        self.helper.help_text_inline = True
        self.render_required_fields = True
        self.helper.layout = Layout(
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


class PhoneNumberForm(forms.ModelForm):

    class Meta:
        model = PhoneNumber
        exclude = ('member', 'venue', 'date_added')

    def __init__(self, *args, **kwargs):
        super(PhoneNumberForm, self).__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if field.widget.__class__ == forms.widgets.TextInput:
                field.widget.attrs['placeholder'] = field.label
        self.helper = FormHelper(self)
        self.helper.disable_csrf = True
        self.helper.form_show_labels = False
        self.helper.form_tag = False
        self.helper.help_text_inline = True
        self.render_required_fields = True
        self.helper.layout = Layout(
            Row(
                Column('number', css_class='col-md-6'),
                Column('type', css_class='col-md-2'),
            ),
            Field('published'),
            Field('id', type='hidden'),
            Field('member', type='hidden'),
        )
