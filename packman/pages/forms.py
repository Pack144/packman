import logging

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.utils.translation import gettext as _

from tinymce.widgets import TinyMCE

from packman.core.exceptions import SpamDetected

from .models import ContentBlock, Page

logger = logging.getLogger(__name__)


class ContactForm(forms.Form):
    from_name = forms.CharField(
        label=_("Your Name"),
        help_text=_("What is your name"),
        max_length=254,
        widget=forms.TextInput(attrs={"autocomplete": "name", "placeholder": "Your Name"}),
        required=True,
    )
    from_email = forms.EmailField(
        label=_("Your E-mail"),
        help_text=_("How can we get a hold of you"),
        max_length=254,
        widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "email@example.com"}),
        required=True,
    )
    url = forms.URLField(
        # A fake field to catch spambots using the form. May also be read by screen readers.
        label=_("Webpage"),
        help_text=_("Optionally give us your website"),
        widget=forms.URLInput(attrs={"autocomplete": "off", "placeholder": "https://example.com"}),
        required=False,
    )
    subject = forms.CharField(
        label=_("Subject"),
        help_text=_("Briefly describe the reason you are contacting us"),
        max_length=998,
        widget=forms.TextInput(attrs={"placeholder": "Message subject"}),
        required=True,
    )
    message = forms.CharField(
        label=_("Message"),
        widget=forms.Textarea(attrs={"placeholder": "Your message"}),
        required=True,
    )

    def clean_url(self):
        url = self.cleaned_data.get("url")
        if url:
            raise SpamDetected(
                _(
                    "Invalid input detected on this form. If you believe you received this message "
                    "in error, please you may check your query and try again."
                )
            )

    def send_mail(self):
        from_address = f"{self.cleaned_data['from_name']} <{self.cleaned_data['from_email']}>"
        email = EmailMessage(
            subject=f"{settings.EMAIL_SUBJECT_PREFIX}{self.cleaned_data['subject']}",
            body=f"We have received the following message from {from_address}:\n\n{self.cleaned_data['message']}",
            to=[f"{a[0]} <{a[1]}>" for a in settings.MANAGERS],
            reply_to=[from_address],
        )
        logger.info(f"Sending email from {email.reply_to} with the subject '{email.subject}' to '{email.to}'")
        email.send()


class ContentBlockForm(forms.ModelForm):
    class Meta:
        model = ContentBlock
        fields = ("heading", "bookmark", "visibility", "body", "order")
        widgets = {
            "body": TinyMCE(mce_attrs={"link_list": "api/v1/pages/link_list/"}),
            "visibility": forms.RadioSelect,
            "order": forms.HiddenInput,
        }


ContentBlockFormSet = forms.inlineformset_factory(
    Page,
    ContentBlock,
    form=ContentBlockForm,
    can_delete=True,
    # can_order=True,
    extra=0,
    min_num=1,
)


class PageForm(forms.ModelForm):
    class Meta:
        model = Page
        fields = ("title", "slug", "nav_placement")


class PageOrderFormSet(forms.BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_orders = dict(self.get_queryset().values_list("pk", "order"))

    def clean(self):
        super().clean()
        if any(self.errors) or not any("order" in form.changed_data for form in self.forms):
            return

        forms = sorted(self.forms, key=lambda form: form.cleaned_data["order"])
        if [form.cleaned_data["order"] for form in forms] != list(range(len(forms))):
            raise ValidationError(_("Reload the page and reorder the pages again."))
        pks = [form.instance.pk for form in forms]
        if len(set(pks)) != len(pks) or set(pks) != set(self.original_orders):
            raise ValidationError(_("Reload the page and reorder the pages again."))

        # Unfold numbers visible rows from zero; preserve their slots among hidden/paginated pages.
        for form, order in zip(forms, sorted(self.original_orders.values()), strict=True):
            form.cleaned_data["order"] = form.instance.order = order
            if order != self.original_orders[form.instance.pk] and "order" not in form.changed_data:
                form.changed_data.append("order")

        # Existing pages can share an order value. Keep the full sequence intact while breaking ties.
        pages = list(self.ordering_queryset.order_by("order", "title", "pk"))
        if len({page.order for page in pages}) != len(pages):
            visible_positions = [index for index, page in enumerate(pages) if page.pk in self.original_orders]
            for position, form in zip(visible_positions, forms, strict=True):
                pages[position] = form.instance
            orders = {page.pk: index for index, page in enumerate(pages)}
            for page in pages:
                page.order = orders[page.pk]
            for form in forms:
                form.cleaned_data["order"] = form.instance.order = orders[form.instance.pk]
                if "order" not in form.changed_data:
                    form.changed_data.append("order")
            forms[0].instance._normalized_page_orders = pages
