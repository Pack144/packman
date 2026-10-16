from django import forms
from django.forms import inlineformset_factory

from .models import Message, MessageDistribution, MessageRecipient


class AttachmentForm(forms.Form):
    attachments = forms.FileField(required=False, widget=forms.ClearableFileInput())


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ("subject", "body")


class MessageDistributionForm(forms.ModelForm):
    class Meta:
        model = MessageDistribution
        fields = ("delivery", "distribution_list")
        widgets = {
            "delivery": forms.Select(attrs={"class": "form-select"}),
            "distribution_list": forms.Select(attrs={"class": "form-select"}),
        }


class MessageRecipientForm(forms.ModelForm):
    class Meta:
        model = MessageRecipient
        fields = ("delivery", "recipient")


MessageDistributionFormSet = inlineformset_factory(
    Message, MessageDistribution, form=MessageDistributionForm, extra=0, min_num=1, can_delete=False
)
