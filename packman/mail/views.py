from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import Http404
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import DetailView, ListView, CreateView, UpdateView

from .forms import MessageForm, MessageDistributionFormSet
from .models import Message


class MessageCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = Message
    form_class = MessageForm
    template_name = "mail/message_form.html"
    success_message = _("Your message <strong>%(subject)s</strong> was %(action)s successfully.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["to_formset"] = MessageDistributionFormSet(self.request.POST, prefix="to_field")
            context["cc_formset"] = MessageDistributionFormSet(self.request.POST, prefix="cc_field")
        else:
            context["to_formset"] = MessageDistributionFormSet(prefix="to_field")
            context["cc_formset"] = MessageDistributionFormSet(prefix="cc_field")
        return context

    def form_valid(self, form):
        context = self.get_context_data(form=form)
        to_formset = context["to_formset"]
        cc_formset = context["cc_formset"]

        if to_formset.is_valid() and cc_formset.is_valid():
            form.instance.author = self.request.user
            obj = form.save()

            to_formset.instance = obj
            to_formset.delivery = Message.Delivery.TO
            to_formset.save()

            cc_formset.instance = obj
            cc_formset.delivery = Message.Delivery.CC
            cc_formset.save()

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
        if self.request.POST:
            context["to_formset"] = MessageDistributionFormSet(self.request.POST, prefix="to_field", instance=self.object)
            context["cc_formset"] = MessageDistributionFormSet(self.request.POST, prefix="cc_field", instance=self.object)
        else:
            context["to_formset"] = MessageDistributionFormSet(prefix="to_field", instance=self.object)
            context["cc_formset"] = MessageDistributionFormSet(prefix="cc_field", instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data(form=form)
        to_formset = context["to_formset"]
        cc_formset = context["cc_formset"]

        if to_formset.is_valid() and cc_formset.is_valid():
            form.instance.author = self.request.user
            obj = form.save()

            to_formset.instance = obj
            to_formset.delivery = Message.Delivery.TO
            to_formset.save()

            cc_formset.instance = obj
            cc_formset.delivery = Message.Delivery.CC
            cc_formset.save()

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

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.author != self.request.user and self.request.user not in obj.recipients:
            raise Http404(
                _("No %(verbose_name)s found matching the query") % {"verbose_name": queryset.model._meta.verbose_name}
            )
        obj.mark_read(self.request.user)
        return obj


class MessageInboxView(LoginRequiredMixin, ListView):

    model = Message
    template_name = "mail/message_list.html"

    def get_queryset(self):
        return super().get_queryset().in_inbox(recipient=self.request.user)


class MessageDraftsView(LoginRequiredMixin, ListView):

    model = Message
    template_name = "mail/message_list.html"

    def get_queryset(self):
        return super().get_queryset().drafts(author=self.request.user)


class MessageArchiveView(LoginRequiredMixin, ListView):

    model = Message
    template_name = "mail/message_list.html"

    def get_queryset(self):
        return super().get_queryset().archived(recipient=self.request.user)


class MessageTrashView(LoginRequiredMixin, ListView):

    model = Message
    template_name = "mail/message_list.html"

    def get_queryset(self):
        return super().get_queryset().deleted(recipient=self.request.user)
