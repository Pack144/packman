from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.core.mail import send_mail
from django.forms import widgets
from django.forms.models import inlineformset_factory
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from crispy_forms.bootstrap import AppendedText, FormActions, InlineRadios
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Field, Fieldset, Layout, Row, Submit

from packman.address_book.forms import AddressForm, PhoneNumberForm
from packman.address_book.models import Address, PhoneNumber

from .models import Adult, Family, Scout

AddressFormSet = inlineformset_factory(
    Adult,
    Address,
    form=AddressForm,
    can_delete=True,
    min_num=1,
    extra=0,
)

PhoneNumberFormSet = inlineformset_factory(
    Adult,
    PhoneNumber,
    form=PhoneNumberForm,
    can_delete=True,
    min_num=1,
    extra=0,
)


class AdminAdultChange(UserChangeForm):
    class Meta:
        model = Adult
        fields = "__all__"


class AdminAdultCreation(UserCreationForm):
    class Meta:
        model = Adult
        fields = "__all__"


class FamilyForm(forms.ModelForm):
    class Meta:
        model = Family
        fields = "__all__"

    adults = forms.ModelMultipleChoiceField(
        queryset=Adult.objects.all(),
        required=False,
    )
    children = forms.ModelMultipleChoiceField(
        queryset=Scout.objects.all(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields["adults"].initial = self.instance.adults.all()
            self.fields["children"].initial = self.instance.children.all()

    def save(self, *args, **kwargs):
        # FIXME: 'commit' argument is not handled
        # TODO: Wrap reassignments into transaction
        # NOTE: Previously assigned Foos are silently reset
        instance = super().save(commit=False)
        self.fields["adults"].initial.update(family=None)
        self.fields["children"].initial.update(family=None)
        self.cleaned_data["adults"].update(family=instance)
        self.cleaned_data["children"].update(family=instance)
        return instance


class AdultCreation(UserCreationForm):
    class Meta:
        model = Adult
        fields = (
            "first_name",
            "middle_name",
            "last_name",
            "suffix",
            "nickname",
            "email",
            "is_published",
            "gender",
            "role",
            "photo",
        )
        widgets = {
            "gender": widgets.RadioSelect,
            "photo": widgets.FileInput,
            "role": widgets.RadioSelect,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if field.widget.__class__ in [
                forms.widgets.TextInput,
                forms.widgets.EmailInput,
            ]:
                field.widget.attrs["placeholder"] = field.label
        self.fields["password1"].required = False
        self.fields["password2"].required = False
        self.fields["role"].choices = (
            (Adult.PARENT, _("Parent")),
            (Adult.GUARDIAN, _("Guardian")),
        )
        self.helper = FormHelper(self)
        self.helper.form_id = "parent_update"
        self.helper.form_tag = False
        # self.helper.form_show_labels = False
        self.helper.help_text_inline = True
        self.helper.layout = Layout(
            Row(
                Column(
                    "first_name",
                    css_class="col-md-4",
                ),
                Column("middle_name", css_class="col-md-2 text-truncate"),
                Column("last_name", css_class="col-md-5"),
                Column("suffix", css_class="col-md-1"),
            ),
            "nickname",
            Row(
                Column("email"),
                Column("is_published"),
            ),
            Row(
                Column(InlineRadios("gender")),
                Column(InlineRadios("role")),
            ),
        )


class AdultForm(forms.ModelForm):
    class Meta:
        model = Adult
        fields = (
            "first_name",
            "middle_name",
            "last_name",
            "suffix",
            "nickname",
            "email",
            "is_published",
            "gender",
            "role",
            "photo",
        )
        widgets = {
            "gender": widgets.RadioSelect,
            "role": widgets.RadioSelect,
            "photo": widgets.FileInput,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if field.widget.__class__ in [
                forms.widgets.TextInput,
                forms.widgets.EmailInput,
            ]:
                field.widget.attrs["placeholder"] = field.label
        self.fields["role"].choices = (
            (Adult.PARENT, _("Parent")),
            (Adult.GUARDIAN, _("Guardian")),
        )
        self.helper = FormHelper(self)
        self.helper.form_id = "parent_update"
        self.helper.form_tag = False
        self.render_required_fields = True
        self.helper.layout = Layout(
            Row(
                Column("first_name", css_class="col-md-4"),
                Column("middle_name", css_class="col-md-2 text-truncate"),
                Column("last_name", css_class="col-md-5"),
                Column("suffix", css_class="col-md-1"),
            ),
            "nickname",
            Row(
                Column("email"),
                Column("is_published"),
            ),
            Row(
                Column("gender"),
                Column("role"),
            ),
        )


class ScoutForm(forms.ModelForm):
    class Meta:
        model = Scout
        fields = (
            "first_name",
            "middle_name",
            "nickname",
            "last_name",
            "suffix",
            "gender",
            "date_of_birth",
            "photo",
            "school",
            "started_school",
            "reference",
            "member_comments",
        )
        widgets = {
            "date_of_birth": widgets.DateInput(
                attrs={
                    "type": "date",
                    "min": str(timezone.now().replace(year=timezone.now().year - 18).date()),
                    "max": str(timezone.now().date()),
                }
            ),
            "gender": widgets.RadioSelect,
            "photo": widgets.FileInput,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if field.widget.__class__ == forms.widgets.TextInput:
                field.widget.attrs["placeholder"] = field.label
        self.helper = FormHelper(self)
        self.helper.form_id = "scout_update"
        self.helper.form_tag = False
        self.helper.render_required_fields = True
        self.helper.layout = Layout(
            Row(
                Column("first_name", css_class="col-md-4"),
                Column("middle_name", css_class="col-md-2 text-truncate"),
                Column("last_name", css_class="col-md-5"),
                Column("suffix", css_class="col-md-1"),
            ),
            "nickname",
            Row(
                Column(InlineRadios("gender")),
                Column("date_of_birth", css_class="col-md-4"),
            ),
            Row(
                Column(
                    Field("school"),
                    css_class="col-md-8",
                ),
                Column(
                    AppendedText("started_school", "grade"),
                    css_class="col-md-4",
                    min=timezone.now().year - 18,
                    max=timezone.now().year,
                ),
            ),
            "reference",
            "member_comments",
            FormActions(
                Submit("save", "Submit", css_class="btn-success btn-lg"),
            ),
        )

    def notify_membership(self, submitter):
        """
        TODO: remove hard-coded addresses & message body
        Send an e-mail to the membership committee notifying them of a new
        application to review.
        """
        subject = (
            f"[{settings.PACK_SHORTNAME}] New member application - "
            f"{self.cleaned_data['first_name']} {self.cleaned_data['last_name']}"
        )
        message = (
            "Hello Membership Committee,\n"
            "\n"
            f"This email confirms that {self.cleaned_data['first_name']} "
            f"{self.cleaned_data['last_name']}, has applied for membership in "
            f"{settings.PACK_NAME}. Please login to pack144.org at your "
            "earliest convenience to review their application."
        )
        to_field = ("Membership Committee <membership@pack144.org>",)
        from_field = "Cub Scouts Pack 144 <noreply@pack144.org>"
        send_mail(
            subject=subject,
            message=message,
            from_email=from_field,
            recipient_list=to_field,
        )

    def send_confirmation_email(self, submitter):
        """
        TODO: remove hard-coded addresses & message body
        Send an e-mail to the cub's parent confirming their application has
        has been received.
        """
        subject = (
            f"[{settings.PACK_SHORTNAME}] New member application - "
            f"{self.cleaned_data['first_name']} {self.cleaned_data['last_name']}"
        )

        message = (
            f"Hello {submitter},\n"
            "\n"
            "This email confirms the receipt of "
            f"{self.cleaned_data['first_name']}'s application to join Pack "
            "144.\nPlease note that receipt of your application does not "
            "guarantee membership to the Pack. You will be\n be notified "
            "ASAP of the status of your application.\n"
            "\n"
            "If you have any questions in the mean time, please contact us at "
            "membership@pack144.org."
        )

        to_field = (f"{submitter} <{submitter.email}>",)
        from_field = "Cub Scouts Pack 144 <noreply@pack144.org>"
        send_mail(
            subject=subject,
            message=message,
            from_email=from_field,
            recipient_list=to_field,
        )


class SignupForm(UserCreationForm):
    class Meta:
        model = Adult
        fields = (
            "first_name",
            "middle_name",
            "last_name",
            "suffix",
            "nickname",
            "email",
            "is_published",
            "gender",
            "role",
            "photo",
        )
        widgets = {
            "gender": widgets.RadioSelect,
            "role": widgets.RadioSelect,
            "photo": widgets.FileInput,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if field.widget.__class__ in [
                forms.widgets.TextInput,
                forms.widgets.EmailInput,
            ]:
                field.widget.attrs["placeholder"] = field.label
        self.fields["role"].choices = (
            (Adult.PARENT, _("Parent")),
            (Adult.GUARDIAN, _("Guardian")),
        )
        self.fields["email"].widget.attrs["autofocus"] = False
        self.helper = FormHelper(self)
        self.helper.form_id = "parent_update"
        self.helper.form_tag = False
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            Fieldset(
                _("Your Details"),
                Row(
                    Column("first_name", css_class="col-md-4"),
                    Column("middle_name", css_class="col-md-2 text-truncate"),
                    Column("last_name", css_class="col-md-5"),
                    Column("suffix", css_class="col-md-1"),
                ),
                Row(
                    Column("nickname", css_class="col-md-4"),
                ),
                Row(
                    Column(InlineRadios("gender")),
                    Column(InlineRadios("role")),
                ),
            ),
            Fieldset(
                _("Email"),
                Row(
                    Column("email"),
                    Column("is_published"),
                ),
            ),
            Fieldset(
                _("Password"),
                Row(
                    Column("password1"),
                    Column("password2"),
                ),
            ),
            Fieldset(
                _("Photo"),
                Row(
                    Column("photo", css_class="col-md-6"),
                ),
            ),
        )

    #
    # def signup(self, request, user):
    #     user.first_name = self.cleaned_data['first_name']
    #     user.middle_name = self.cleaned_data['middle_name']
    #     user.last_name = self.cleaned_data['last_name']
    #     user.suffix = self.cleaned_data['suffix']
    #     user.nickname = self.cleaned_data['nickname']
    #     user.gender = self.cleaned_data['gender']
    #     user.role = self.cleaned_data['role']
    #     user.photo = self.cleaned_data['photo']
    #     user.email = self.cleaned_data['email']
    #     user.is_published = self.cleaned_data['is_published']
    #     user.family = Family.objects.create()
    #     user.save()
    #     return user
