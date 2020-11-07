import logging

from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.generic import (
    CreateView, DetailView, FormView, TemplateView, UpdateView,
)

from membership.forms import AddressFormSet, PhoneNumberFormSet, SignupForm
from membership.models import Family
from pack_calendar.models import Event
from .forms import ContactForm
from .models import Page


logger = logging.getLogger(__name__)


class PageDetailView(DetailView):
    model = Page
    context_object_name = 'page'

    def get_object(self, **kwargs):
        obj = super().get_object(**kwargs)
        if obj.content_blocks.count():
            return obj
        else:
            raise PermissionDenied

    def get_queryset(self):
        qs = super().get_queryset().get_visible_content(self.request.user)
        return qs


class PageUpdateView(UpdateView):
    model = Page
    context_object_name = 'page_content'
    fields = '__all__'


class AboutPageView(PageDetailView):
    template_name = 'pages/about_page.html'

    def get_object(self):
        obj, created = self.get_queryset().get_or_create(page=Page.ABOUT)
        if created:
            logger.info = _("About page was requested but none was found in the database.")
            obj.title = _("About Us")
            obj.save()
        return obj


class HomePageView(PageDetailView):
    template_name = 'pages/home_page.html'

    def get_object(self):
        obj, created = self.get_queryset().get_or_create(page=Page.HOME)
        if created:
            logger.info = _("Home page was requested but none was found in the database.")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['events'] = Event.objects.filter(
            start__lte=timezone.now() + timezone.timedelta(weeks=1)
        ).filter(
            start__gte=timezone.now() - timezone.timedelta(hours=8)
        ).order_by('start')
        return context


class HistoryPageView(PageDetailView):
    template_name = 'pages/history_page.html'

    def get_object(self):
        obj, created = self.get_queryset().get_or_create(page=Page.HISTORY)
        if created:
            logger.info = _("History page was requested but none was found in the database.")
            obj.title = _("Our History")
            obj.save()
        return obj


class ContactPageView(SuccessMessageMixin, FormView):
    form_class = ContactForm
    success_message = _(
        'Thank you for reaching out. Your message has been sent and we will be reviewing it momentarily. If you '
        'have requested a response, we will get back to you at %(from_email)s.'
    )
    success_url = reverse_lazy('pages:home')
    template_name = 'pages/contact_page.html'

    def form_valid(self, form):
        form.send_mail()
        return super().form_valid(form)


class SignUpPageView(CreateView):
    form_class = SignupForm
    success_url = reverse_lazy('login')
    template_name = 'pages/signup_page.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['address_formset'] = AddressFormSet(
                self.request.POST
            )
            context['phonenumber_formset'] = PhoneNumberFormSet(
                self.request.POST
            )
        else:
            context['address_formset'] = AddressFormSet()
            context['phonenumber_formset'] = PhoneNumberFormSet()
        try:
            context['page'] = Page.objects.get_visible_content(user=self.request.user).get(
                page=Page.SIGNUP
            )
        except Page.DoesNotExist:
            context['page'] = None
        return context

    def form_valid(self, form):
        context = self.get_context_data(form=form)
        address_formset = context['address_formset']
        phonenumber_formset = context['phonenumber_formset']
        if address_formset.is_valid() and phonenumber_formset.is_valid():
            self.object = form.save()
            form.instance.family = Family.objects.create()
            address_formset.instance = self.object
            address_formset.save()
            phonenumber_formset.instance = self.object
            phonenumber_formset.save()
        else:
            return super().form_invalid(form)
        return super().form_valid(form)
