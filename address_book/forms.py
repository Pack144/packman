from django import forms

from .models import Address, PhoneNumber


class AddressForm(forms.ModelForm):

    class Meta:
        model = Address
        fields = '__all__'


class PhoneNumberForm(forms.ModelForm):

    class Meta:
        model = PhoneNumber
        fields = '__all__'
