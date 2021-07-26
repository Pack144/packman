from django.contrib import admin, messages
from django.contrib.admin.utils import quote
from django.contrib.auth import get_permission_codename
from django.urls import reverse
from django.utils.html import format_html
from django.utils.http import urlquote
from django.utils.translation import gettext as _

from .forms import MessageForm, MessageDistributionForm, MessageRecipientForm
from .models import (
    Attachment,
    DistributionList,
    EmailAddress,
    Message,
    MessageDistribution,
    MessageRecipient,
    ListSettings,
)


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0


class EmailAddressInline(admin.TabularInline):
    model = EmailAddress
    extra = 0
    min_num = 1


class MessageDistributionInline(admin.TabularInline):
    model = MessageDistribution
    autocomplete_fields = ("distribution_list",)
    extra = 0
    form = MessageDistributionForm


class MessageRecipientInline(admin.TabularInline):
    model = MessageRecipient
    autocomplete_fields = ("recipient",)
    classes = ["collapse"]
    extra = 0
    form = MessageRecipientForm


@admin.register(DistributionList)
class DistributionListAdmin(admin.ModelAdmin):
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
class MessageAdmin(admin.ModelAdmin):
    change_form_template = "admin/message_change_form.html"
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

    def response_add(self, request, obj, post_url_continue=None):
        # Add a "Send" button to the message add page
        opts = obj._meta
        obj_url = reverse(
            "admin:%s_%s_change" % (opts.app_label, opts.model_name),
            args=(quote(obj.pk),),
            current_app=self.admin_site.name,
        )
        # Add a link to the object's change form if the user can edit the obj.
        if self.has_change_permission(request, obj):
            obj_repr = format_html('<a href="{}">{}</a>', urlquote(obj_url), obj)
        else:
            obj_repr = str(obj)
        msg_dict = {
            "name": opts.verbose_name,
            "obj": obj_repr,
        }

        if "_send" in request.POST:
            obj.send()
            msg = format_html(_("The {name} “{obj}” was sent successfully."), **msg_dict)
            self.message_user(request, msg, messages.SUCCESS)
            return self.response_post_save_add(request, obj)

        return super().response_add(request, obj, post_url_continue)

    def response_change(self, request, obj):
        # Add a "Send" button to the message change page
        opts = self.model._meta
        msg_dict = {
            "name": opts.verbose_name,
            "obj": format_html('<a href="{}">{}</a>', urlquote(request.path), obj),
        }
        if "_send" in request.POST:
            obj.send()
            msg = format_html(_("The {name} “{obj}” was sent successfully."), **msg_dict)
            self.message_user(request, msg, messages.SUCCESS)
            return self.response_post_save_change(request, obj)

        return super().response_change(request, obj)

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
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))

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
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))

    def has_view_permission(self, request, obj=None):
        #  Start with Django's default has_view_permission() method.
        opts = self.opts
        codename = get_permission_codename("view", opts)

        # Pause to determine whether the user is either the author or a
        # recipient of a Message that has been sent.
        if obj and obj.author != request.user:
            return False
        if obj and obj.date_sent and request.user not in obj.recipients.all():
            return False

        # Do the thing that Django does after checking our special case,
        # except we're going to skip the check on whether the user has
        # change permission as that cannot be expressed using the standard
        # permissions model.
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))


@admin.register(ListSettings)
class ListSettingsAdmin(admin.ModelAdmin):
    list_display = ("list_id", "name", "subject_prefix", "from_name", "from_email")
    list_display_links = ("list_id", "name", "subject_prefix", "from_name", "from_email")
