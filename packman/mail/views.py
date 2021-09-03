from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DetailView, ListView, UpdateView, DeleteView

from .forms import AttachmentForm, MessageDistributionFormSet, MessageForm
from .models import Mailbox, Message, Attachment
from .utils import get_mailbox_counts


class MessageCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = Message
    form_class = MessageForm
    template_name = "mail/message_form.html"
    success_message = _("Your message <strong>%(subject)s</strong> was %(action)s successfully.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["mailbox"] = ""
        context["mail_count"] = get_mailbox_counts(self.request.user)

        if self.request.POST:
            context["attachments_form"] = AttachmentForm(self.request.POST, self.request.FILES)
            context["dl_formset"] = MessageDistributionFormSet(self.request.POST, prefix="to_field")
        else:
            context["attachments_form"] = AttachmentForm()
            context["dl_formset"] = MessageDistributionFormSet(prefix="to_field")
        return context

    def form_valid(self, form):
        context = self.get_context_data(form=form)
        dl_formset = context["dl_formset"]
        attachments_form = context["attachments_form"]
        files = self.request.FILES.getlist("attachments")

        if attachments_form.is_valid() and dl_formset.is_valid():
            form.instance.author = self.request.user
            obj = form.save()

            # Save the files
            for file in files:
                Attachment.objects.create(message=obj, filename=file)

            # Save the distribution lists
            dl_formset.instance = obj
            dl_formset.save()

            return super().form_valid(form)

        return super().form_invalid(form)

    def get_success_url(self):
        """Return the appropriate URL for save vs. send."""
        if "_save" in self.request.POST:
            return reverse_lazy("mail:update", kwargs={"pk": self.object.uuid})

        self.object.send()
        return reverse_lazy("mail:inbox")

    def get_success_message(self, cleaned_data):
        return self.success_message % dict(cleaned_data, action=_("sent") if self.object.date_sent else _("saved"))


class MessageUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Message
    form_class = MessageForm
    template_name = "mail/message_form.html"
    success_message = _("Your message <strong>%(subject)s</strong> was %(action)s successfully.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["mailbox"] = Mailbox.DRAFTS
        context["mail_count"] = get_mailbox_counts(self.request.user, context["mailbox"])
        context["message_list"] = Message.objects.drafts(self.request.user)
        if self.request.POST:
            context["attachments_form"] = AttachmentForm(self.request.POST, self.request.FILES)
            context["dl_formset"] = MessageDistributionFormSet(
                self.request.POST, prefix="to_field", instance=self.object
            )
        else:
            context["attachments_form"] = AttachmentForm(self.request.POST, self.request.FILES)
            context["dl_formset"] = MessageDistributionFormSet(prefix="to_field", instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data(form=form)
        dl_formset = context["dl_formset"]
        attachments_form = context["attachments_form"]
        files = self.request.FILES.getlist("attachments")

        if attachments_form.is_valid() and dl_formset.is_valid():
            form.instance.author = self.request.user
            obj = form.save()

            # Save the new files
            for file in files:
                Attachment.objects.create(message=obj, filename=file)

            # Save the distribution lists
            dl_formset.instance = obj
            dl_formset.save()

            return super().form_valid(form)

        return super().form_invalid(form)

    def get_success_url(self):
        """Return the appropriate URL for save vs. send."""
        if "_save" in self.request.POST:
            return reverse_lazy("mail:update", kwargs={"pk": self.object.uuid})

        self.object.send()
        return reverse_lazy("mail:inbox")

    def get_success_message(self, cleaned_data):
        return self.success_message % dict(cleaned_data, action=_("sent") if self.object.date_sent else _("saved"))


class MessageDetailView(LoginRequiredMixin, DetailView):

    model = Message
    template_name = "mail/message_detail.html"

    def get_queryset(self):
        return super().get_queryset().with_receipts(self.request.user)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if self.request.user in obj.recipients.all():
            obj.mark_read(recipient=self.request.user)
            return obj
        elif obj.author == self.request.user:
            return obj
        else:
            raise Http404(
                _("No %(verbose_name)s found matching the query") % {"verbose_name": queryset.model._meta.verbose_name}
            )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object.author == self.request.user:
            context["mailbox"] = Mailbox.SENT if self.object.date_sent else Mailbox.DRAFTS
        else:
            context["mailbox"] = self.object.message_recipients.get(recipient=self.request.user).get_mailbox()
        context["message_list"] = Message.objects.in_mailbox(self.request.user, context["mailbox"])
        context["mail_count"] = get_mailbox_counts(self.request.user, context["mailbox"])
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if "_archive" in request.POST:
            self.object.mark_archived(request.user)

        if "_delete" in request.POST:
            self.object.mark_deleted(request.user)

        if "_unarchive" in request.POST:
            self.object.mark_unarchived(request.user)

        if "_undelete" in request.POST:
            self.object.mark_undeleted(request.user)

        return HttpResponseRedirect(self.object.get_absolute_url())


class MessageDeleteView(LoginRequiredMixin, DeleteView):
    model = Message
    success_url = reverse_lazy("mail:drafts")
    template_name = "mail/message_confirm_delete.html"

    def delete(self, request, *args, **kwargs):
        self.object == self.get_object()
        if self.request.user == self.object.author and not self.object.date_sent:
            success_message = _("Your message <strong>%(subject)s</strong> was deleted successfully.") % {
                "subject": self.get_object()
            }
            messages.success(request, success_message, "danger")
            return super().delete(request, *args, **kwargs)


class MessageListView(LoginRequiredMixin, ListView):

    model = Message
    template_name = "mail/message_list.html"


class MessageInboxView(MessageListView):

    model = Message
    template_name = "mail/message_list.html"

    def get_queryset(self):
        return super().get_queryset().in_inbox(recipient=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["mailbox"] = Mailbox.INBOX
        context["mail_count"] = get_mailbox_counts(self.request.user, context["mailbox"])
        return context


class MessageDraftsView(MessageListView):

    model = Message
    template_name = "mail/message_list.html"

    def get_queryset(self):
        return super().get_queryset().drafts(author=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["mailbox"] = Mailbox.DRAFTS
        context["mail_count"] = get_mailbox_counts(self.request.user, context["mailbox"])
        return context


class MessageSentView(MessageListView):

    model = Message
    template_name = "mail/message_list.html"

    def get_queryset(self):
        return super().get_queryset().sent(author=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["mailbox"] = Mailbox.SENT
        context["mail_count"] = get_mailbox_counts(self.request.user, context["mailbox"])
        return context


class MessageArchiveView(MessageListView):

    model = Message
    template_name = "mail/message_list.html"

    def get_queryset(self):
        return super().get_queryset().archived(recipient=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["mailbox"] = Mailbox.ARCHIVES
        context["mail_count"] = get_mailbox_counts(self.request.user, context["mailbox"])
        return context


class MessageTrashView(MessageListView):

    model = Message
    template_name = "mail/message_list.html"

    def get_queryset(self):
        return super().get_queryset().deleted(recipient=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["mailbox"] = Mailbox.TRASH
        context["mail_count"] = get_mailbox_counts(self.request.user, context["mailbox"])
        return context
