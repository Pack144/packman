from django import forms

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Field, Layout, Row
from localflavor.us.models import STATE_CHOICES

from .models import Address, PhoneNumber


class AddressFormHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.disable_csrf = True
        self.form_show_labels = False
        self.form_tag = False
        self.help_text_inline = False
        self.layout = Layout(
            Row(
                Column(
                    Row(
                        Column("type", css_class="col-md-3"),
                    ),
                    "street",
                    "street2",
                    Row(
                        Column(Field("city"), css_class="col-md-6"),
                        Column(
                            Field("state"),
                            css_class="col-md-3",
                        ),
                        Column(Field("zip_code"), css_class="col-md-3"),
                    ),
                    "published",
                    Field("uuid", type="hidden"),
                    Field("member", type="hidden"),
                    Field("DELETE", type="hidden"),
                ),
                css_class="address-dynamic-form mb-3",
            ),
        )
        self.render_required_fields = True


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        exclude = ("member", "venue", "date_added")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            if visible.field.widget.__class__ == forms.widgets.TextInput:
                visible.field.widget.attrs["placeholder"] = visible.label
        self.helper = AddressFormHelper(self)
        self.fields["state"].choices = STATE_CHOICES + ((None, self.fields["state"].label),)


class PhoneNumberFormHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.disable_csrf = True
        self.form_show_labels = False
        self.form_tag = False
        self.layout = Layout(
            Row(
                Column(
                    Row(
                        Column(
                            Field("type", css_class="form-select"),
                            css_class="col-md-3",
                        ),
                        Column(Field("number")),
                    ),
                    "published",
                    Field("uuid", type="hidden"),
                    Field("member", type="hidden"),
                    Field("DELETE", type="hidden"),
                ),
                css_class="phonenumber-dynamic-form mb-3",
            ),
        )


class PhoneNumberForm(forms.ModelForm):
    class Meta:
        model = PhoneNumber
        exclude = ("member", "venue", "date_added")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            if visible.field.widget.__class__ == forms.widgets.TextInput:
                visible.field.widget.attrs["placeholder"] = visible.label
        self.helper = PhoneNumberFormHelper(self)
