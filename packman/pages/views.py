import logging

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DeleteView, DetailView, FormView, UpdateView

from packman.calendars.models import Event
from packman.membership.forms import AddressFormSet, PhoneNumberFormSet, SignupForm
from packman.membership.models import Family

from .forms import ContactForm, ContentBlockFormSet, PageForm
from .models import Page

logger = logging.getLogger(__name__)


def get_link_list(request):
    """Retrieves a list of pages available for the current user to link to."""
    pages = Page.objects.get_visible_content(user=request.user)
    link_list = [{"title": page.title, "value": page.get_absolute_url()} for page in pages]
    return JsonResponse(link_list, safe=False)


class PageDetailView(DetailView):
    model = Page
    context_object_name = "page"

    def get_object(self, **kwargs):
        obj = super().get_object(**kwargs)
        if obj.content_blocks.count():
            return obj
        else:
            raise PermissionDenied

    def get_queryset(self):
        return super().get_queryset().get_visible_content(self.request.user)


class PageCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Page
    form_class = PageForm
    permission_required = "pages.add_page"
    success_message = _("The page: '%(title)s' has been successfully created.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["contentblock_formset"] = ContentBlockFormSet(self.request.POST)
        else:
            context["contentblock_formset"] = ContentBlockFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data(form=form)
        contentblock_formset = context["contentblock_formset"]
        if contentblock_formset.is_valid():
            self.object = form.save()
            contentblock_formset.instance = self.object
            contentblock_formset.save()
        else:
            return super().form_invalid(form)
        return super().form_valid(form)


class PageDeleteView(PermissionRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Page
    permission_required = "pages.delete_page"
    success_url = reverse_lazy("pages:home")

    def form_valid(self, form):
        success_message = _("The page: '%(page)s' has been successfully deleted.") % {"page": self.object}
        messages.success(self.request, success_message, "danger")
        return super().form_valid(form)


class PageUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Page
    form_class = PageForm
    permission_required = "pages.change_page"
    success_message = _("The page: '%(title)s' has been successfully updated.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["contentblock_formset"] = ContentBlockFormSet(self.request.POST, instance=self.object)
        else:
            context["contentblock_formset"] = ContentBlockFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data(form=form)
        contentblock_formset = context["contentblock_formset"]
        if contentblock_formset.is_valid():
            contentblock_formset.instance = self.object
            contentblock_formset.save()
        else:
            return super().form_invalid(form)
        return super().form_valid(form)


class AboutPageView(PageDetailView):
    template_name = "pages/about_page.html"

    def get_object(self):
        obj, created = self.get_queryset().get_or_create(page=Page.ABOUT)
        if created:
            logger.info = _("About page was requested but none was found in the database.")
            obj.title = _("About Us")
            obj.save()
        return obj


class HomePageView(PageDetailView):
    template_name = "pages/home_page.html"

    def get_object(self):
        obj, created = self.get_queryset().get_or_create(page=Page.HOME)
        if created:
            logger.info = _("Home page was requested but none was found in the database.")

        if self.request.user.is_authenticated and (
            not self.request.user.family or not self.request.user.family.children.exists()
        ):
            messages.add_message(
                self.request,
                messages.INFO,
                _(
                    "<strong>It's awfully lonely in here.</strong> You should visit your "
                    "<a class='alert-link' href='%(my-family)s'>My Family</a> page to "
                    "<a class='alert-link' href='%(add-cub)s'>nominate your Cub</a> for "
                    "membership and add more family members."
                )
                % {
                    "my-family": reverse("membership:my-family"),
                    "add-cub": reverse("membership:scout_create"),
                },
            )

        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["events"] = (
            Event.objects.filter(start__lte=timezone.now() + timezone.timedelta(weeks=1))
            .filter(start__gte=timezone.now() - timezone.timedelta(hours=8))
            .order_by("start")
        )
        return context


class HistoryPageView(PageDetailView):
    template_name = "pages/history_page.html"

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
        "Thank you for reaching out. Your message has been sent and we will be reviewing it momentarily. If you "
        "have requested a response, we will get back to you at %(from_email)s."
    )
    success_url = reverse_lazy("pages:home")
    template_name = "pages/contact_page.html"

    def get_initial(self):
        initial = super().get_initial()
        if self.request.user.is_authenticated:
            initial["from_name"] = str(self.request.user)
            initial["from_email"] = self.request.user.email
        return initial

    def form_valid(self, form):
        form.send_mail()
        return super().form_valid(form)


class SignUpPageView(CreateView):
    form_class = SignupForm
    success_url = reverse_lazy("login")
    template_name = "pages/signup_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["address_formset"] = AddressFormSet(self.request.POST)
            context["phonenumber_formset"] = PhoneNumberFormSet(self.request.POST)
        else:
            context["address_formset"] = AddressFormSet()
            context["phonenumber_formset"] = PhoneNumberFormSet()
        try:
            context["page"] = Page.objects.get_visible_content(user=self.request.user).get(page=Page.SIGNUP)
        except Page.DoesNotExist:
            context["page"] = None
        return context

    def form_valid(self, form):
        context = self.get_context_data(form=form)
        address_formset = context["address_formset"]
        phonenumber_formset = context["phonenumber_formset"]
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
