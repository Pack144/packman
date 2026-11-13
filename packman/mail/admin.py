from django.contrib import admin, messages
from django.contrib.auth import get_permission_codename
from django.utils.translation import gettext as _

from tinymce.models import HTMLField
from tinymce.widgets import TinyMCE
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action
from unfold.widgets import UnfoldAdminSelectWidget

from .forms import MessageDistributionForm, MessageForm, MessageRecipientForm
from .models import (
    Attachment,
    DistributionList,
    EmailAddress,
    ListSettings,
    Message,
    MessageDistribution,
    MessageRecipient,
)


class AttachmentInline(TabularInline):
    model = Attachment
    extra = 0


class EmailAddressInline(TabularInline):
    model = EmailAddress
    extra = 0
    min_num = 1


class MessageDistributionInline(TabularInline):
    model = MessageDistribution
    autocomplete_fields = ("distribution_list",)
    extra = 0
    form = MessageDistributionForm

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        kwargs["widget"] = UnfoldAdminSelectWidget
        return super().formfield_for_choice_field(db_field, request, **kwargs)


class MessageRecipientInline(TabularInline):
    model = MessageRecipient
    autocomplete_fields = ("recipient",)
    classes = ["collapse"]
    extra = 0
    form = MessageRecipientForm


@admin.register(DistributionList)
class DistributionListAdmin(ModelAdmin):
    fieldsets = [
        (None, {"fields": ("name", "is_all")}),
        (_("Selections"), {"fields": ("dens", "committees"), "classes": ("collapse",)}),
    ]
    filter_horizontal = ("committees", "dens")
    inlines = [EmailAddressInline]
    list_display = ("name", "get_email_addresses", "get_selections", "is_all")
    list_filter = ("is_all", "dens", "committees")
    search_fields = ("name", "addresses__address", "committees__name", "dens__number")

    @admin.display(description=_("selections"))
    def get_selections(self, obj):
        den_list = ", ".join(str(d) for d in obj.dens.all())
        committee_list = ", ".join(str(c) for c in obj.committees.all())
        if den_list and committee_list:
            return ", ".join((den_list, committee_list))
        elif den_list:
            return den_list
        elif committee_list:
            return committee_list

    @admin.display(description=_("email addresses"))
    def get_email_addresses(self, obj):
        return ", ".join(str(e) for e in obj.addresses.all())


@admin.register(Message)
class MessageAdmin(ModelAdmin):
    formfield_overrides = {HTMLField: {"widget": TinyMCE}}
    actions_submit_line = ["save_and_send"]
    date_hierarchy = "last_updated"
    fieldsets = [
        (None, {"fields": ("author", "subject", "body")}),
        (_("Metadata"), {"fields": (("last_updated", "date_sent"), ("thread", "parent")), "classes": ("collapse",)}),
    ]
    form = MessageForm
    list_display = ("author", "subject", "last_updated", "sent")
    list_display_links = ("author", "subject", "last_updated")
    list_filter = ("distribution_lists",)
    inlines = (MessageDistributionInline, MessageRecipientInline, AttachmentInline)
    search_fields = ("subject", "body")
    readonly_fields = ("author", "thread", "date_sent", "last_updated", "parent")

    def save_model(self, request, obj, form, change):
        obj.author = request.user
        super().save_model(request, obj, form, change)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        if object_id is None:
            extra_context = {
                **(extra_context or {}),
                "actions_submit_line": self.get_actions_submit_line(request, None),
            }
        return super().changeform_view(request, object_id, form_url, extra_context)

    @action(description=_("Save and send"), permissions=["send"], icon="send")
    def save_and_send(self, request, obj):
        # Unfold invokes submit-line actions before Django saves inline formsets.
        obj._send_after_related = True

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if getattr(form.instance, "_send_after_related", False):
            form.instance.send()
            self.message_user(request, _("The message was sent successfully."), messages.SUCCESS)

    def has_send_permission(self, request, object_id=None):
        if object_id is None:
            return self.has_add_permission(request) and self.has_change_permission(request)
        obj = self.get_object(request, object_id)
        return obj is not None and self.has_change_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        #  Start with Django's default has_change_permission() method.
        opts = self.opts
        codename = get_permission_codename("change", opts)

        # Pause to determine whether the user is either the author or if
        # the Message has been sent.
        if obj and obj.author != request.user:
            return False
        if obj and obj.date_sent:
            return False

        # Do the thing that Django does after checking our special case.
        return request.user.has_perm(f"{opts.app_label}.{codename}")

    def has_delete_permission(self, request, obj=None):
        #  Start with Django's default has_delete_permission() method.
        opts = self.opts
        codename = get_permission_codename("delete", opts)

        # Pause to determine whether the user is either the author or if
        # the Message has been sent.
        if obj and obj.author != request.user:
            return False
        if obj and obj.date_sent:
            return False

        # Do the thing that Django does after checking our special case.
        return request.user.has_perm(f"{opts.app_label}.{codename}")

    def has_view_permission(self, request, obj=None):
        #  Start with Django's default has_view_permission() method.
        opts = self.opts
        codename = get_permission_codename("view", opts)

        # Pause to determine whether the user is either the author or a
        # recipient of a Message that has been sent.
        if obj:
            return bool((obj.author == request.user) or (obj.date_sent and request.user in obj.recipients.all()))

        # Do the thing that Django does after checking our special case,
        # except we're going to skip the check on whether the user has
        # change permission as that cannot be expressed using the standard
        # permissions model.
        return request.user.has_perm(f"{opts.app_label}.{codename}")


@admin.register(ListSettings)
class ListSettingsAdmin(ModelAdmin):
    list_display = ("list_id", "name", "subject_prefix", "from_name", "from_email")
    list_display_links = ("list_id", "name", "subject_prefix", "from_name", "from_email")
