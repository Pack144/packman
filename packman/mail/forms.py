from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _

from tinymce.widgets import TinyMCE

from .models import Message, MessageDistribution, MessageRecipient
from .rendering import EDITOR_STYLE


class AttachmentForm(forms.Form):
    attachments = forms.FileField(required=False, widget=forms.ClearableFileInput())


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ("subject", "body")
        widgets = {"body": TinyMCE(mce_attrs={"content_style": EDITOR_STYLE, "height": 320, "min_height": 320})}
        help_texts = {"body": _("Enter starts a paragraph; Shift+Enter starts a single line.")}


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
