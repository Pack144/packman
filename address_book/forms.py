from django import forms

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field

from .models import Address, PhoneNumber


class AddressForm(forms.ModelForm):

    class Meta:
        model = Address
        exclude = ('member', 'date_added')

    def __init__(self, *args, **kwargs):
        super(AddressForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_id = 'address_form'
        self.helper.form_tag = False
        self.render_required_fields = True
        self.helper.layout = Layout(
            'street',
            'street2',
            Row(
                Column('city', css_class='col-md-5'),
                Column('state', css_class='col-md-3'),
                Column('zip_code', css_class='col-md-4')
            ),
            Row(
                Column('type'),
                Column('published'),
            ),
            Field('id', type='hidden'),
            Field('member', type='hidden'),
        )


class PhoneNumberForm(forms.ModelForm):

    class Meta:
        model = PhoneNumber
        exclude = ('member', 'date_added')

    def __init__(self, *args, **kwargs):
        super(PhoneNumberForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_id = 'phonenumber_form'
        self.helper.form_tag = False
        self.render_required_fields = True
        self.helper.layout = Layout(
            Row(
                Column('number', css_class='col-md-6'),
                Column('type', css_class='col-md-2'),
                Column('published', css_class='col-md-4'),
            ),
            Field('id', type='hidden'),
            Field('member', type='hidden'),
        )
