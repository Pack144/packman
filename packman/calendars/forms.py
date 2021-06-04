from django import forms
from django.urls import reverse

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Field, Layout, Row
from tempus_dominus.widgets import DateTimePicker
from tinymce.widgets import TinyMCE

from .models import Event


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "name",
            "status",
            "venue",
            "location",
            "start",
            "end",
            "description",
            "category",
            "attachments",
            "published",
        ]
        widgets = {
            "description": TinyMCE(mce_attrs={"link_list ": reverse("link_list", urlconf="packman.pages.urls")}),
            "start": DateTimePicker(attrs={"append": "fa fa-calendar"}),
            "end": DateTimePicker(attrs={"append": "fa fa-calendar"}),
            "status": forms.RadioSelect,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column(Field("name", css_class="form-control-lg"), css_class="col-md-8"),
                Column("status"),
            ),
            Row(
                Column("venue"),
                Column("location"),
            ),
            Row(
                Column("start"),
                Column("end"),
            ),
            "description",
            "attachments",
            Row(
                Column("category"),
                Column("published"),
            ),
        )
