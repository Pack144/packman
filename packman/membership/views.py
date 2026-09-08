from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from packman.address_book.models import Address, PhoneNumber

from .forms import AddressFormSet, AdultCreation, AdultForm, PhoneNumberFormSet, ScoutForm
from .models import Adult, Family, Member, Scout


class MemberList(LoginRequiredMixin, ListView):
    model = Member
    paginate_by = 25
    context_object_name = "members"
    template_name = "membership/member_list.html"

    def get_queryset(self):
        if self.request.user.active() or self.request.user.role == Adult.CONTRIBUTOR:
            # If you have active cubs or are a contributor, you can see all
            # active members
            return Member.objects.filter(
                Q(adult__family__children__status__exact=Scout.ACTIVE)
                | Q(adult__role__exact=Adult.CONTRIBUTOR)
                | Q(scout__status__exact=Scout.ACTIVE)
            ).distinct()
        elif not self.request.user.family:
            # The user doesn't belong to a family, so we'll just show them
            # their own information
            return Member.objects.filter(adult__uuid__exact=self.request.user.uuid).distinct()
        else:
            # If you are not active, you can only see your own family
            return Member.objects.filter(
                Q(adult__family__exact=self.request.user.family) | Q(scout__family__exact=self.request.user.family)
            )


class MemberSearchResultsList(LoginRequiredMixin, ListView):
    model = Member
    context_object_name = "members"
    template_name = "membership/member_search_results.html"

    def get_queryset(self):
        query = self.request.GET.get("q")
        if self.request.GET.get("alum") == "included":
            results = (
                Member.objects.filter(
                    Q(adult__family__children__status__gte=Scout.ACTIVE) | Q(scout__status__gte=Scout.ACTIVE)
                )
                .filter(
                    Q(first_name__icontains=query)
                    | Q(last_name__icontains=query)
                    | Q(middle_name__icontains=query)
                    | Q(nickname__icontains=query)
                )
                .distinct()
            )
        else:
            results = (
                Member.objects.filter(
                    Q(adult__family__children__status__exact=Scout.ACTIVE)
                    | Q(adult__role__exact=Adult.CONTRIBUTOR)
                    | Q(scout__status__exact=Scout.ACTIVE)
                )
                .filter(
                    Q(first_name__icontains=query)
                    | Q(last_name__icontains=query)
                    | Q(middle_name__icontains=query)
                    | Q(nickname__icontains=query)
                )
                .distinct()
            )

        if self.request.user.active() or self.request.user.role == Adult.CONTRIBUTOR:
            # If you have active cubs or are a contributor, you can get all of
            # the search results
            return results
        elif not self.request.user.family:
            # The user doesn't belong to a family, so we'll just show them
            # their own information
            return Member.objects.filter(adult__uuid__exact=self.request.user.uuid)
        else:
            # If you are not active, you only get members of your own family
            return results.filter(
                Q(adult__family__exact=self.request.user.family) | Q(scout__family__exact=self.request.user.family)
            )


class AdultList(LoginRequiredMixin, ListView):
    model = Adult
    paginate_by = 25
    context_object_name = "members"
    template_name = "membership/adult_list.html"

    def get_queryset(self):
        if self.request.user.active() or self.request.user.role == Adult.CONTRIBUTOR:
            # If you have active cubs or are a contributor, you can get all
            # active members
            return Adult.objects.filter(
                Q(family__children__status=Scout.ACTIVE) | Q(role__exact=Adult.CONTRIBUTOR)
            ).distinct()
        elif not self.request.user.family:
            # The user doesn't belong to a family, so we'll just show them
            # their own information
            return Adult.objects.filter(uuid__exact=self.request.user.uuid)
        else:
            # If you are not active, you only get members of your own family
            return Adult.objects.filter(family__exact=self.request.user.family)


class AdultCreate(LoginRequiredMixin, CreateView):
    model = Adult
    context_object_name = "member"
    form_class = AdultCreation
    template_name = "membership/adult_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["address_formset"] = AddressFormSet(self.request.POST)
            context["phonenumber_formset"] = PhoneNumberFormSet(self.request.POST)
        else:
            context["address_formset"] = AddressFormSet()
            context["phonenumber_formset"] = PhoneNumberFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data(form=form)
        address_formset = context["address_formset"]
        phonenumber_formset = context["phonenumber_formset"]
        request_user = Adult.objects.get(uuid=self.request.user.uuid)
        if address_formset.is_valid() and phonenumber_formset.is_valid():
            self.object = form.save()
            address_formset.instance = self.object
            address_formset.save()
            phonenumber_formset.instance = self.object
            phonenumber_formset.save()
        else:
            return super().form_invalid(form)
        if not request_user.family:
            request_user.family = Family.objects.create()
            request_user.save()
        form.instance.family = request_user.family
        form.instance.password1 = Adult.objects.make_random_password()
        return super().form_valid(form)


class AdultDetail(LoginRequiredMixin, DetailView):
    model = Adult
    context_object_name = "member"
    template_name = "membership/adult_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["email"] = self.object.email if self.object.is_published else None
        context["addresses"] = self.object.addresses.filter(published__exact=True)
        context["phone_numbers"] = self.object.phone_numbers.filter(published__exact=True)
        context["has_publishable_contact_info"] = bool(
            context["email"] or context["addresses"] or context["phone_numbers"]
        )
        return context


def _vcard_escape(value):
    """Escape a value for use in a vCard field per RFC 2426."""
    return str(value).replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


class AdultVCard(LoginRequiredMixin, View):
    """
    Generate a downloadable vCard (.vcf) for an Adult member, respecting the
    same email/address/phone `published` flags used on the member's profile
    page. Any logged-in member may request the vCard for any adult.
    """

    # Map our internal type codes to the vCard TYPE values, with sensible
    # defaults for records that don't specify a type.
    PHONE_TYPE_MAP = {
        PhoneNumber.HOME: "HOME",
        PhoneNumber.MOBILE: "CELL",
        PhoneNumber.WORK: "WORK",
        PhoneNumber.OTHER: "OTHER",
    }
    ADDRESS_TYPE_MAP = {
        Address.HOME: "HOME",
        Address.WORK: "WORK",
        Address.OTHER: "OTHER",
    }

    def get(self, request, *args, **kwargs):
        adult = get_object_or_404(Adult, slug=kwargs["slug"])

        email = adult.email if adult.is_published else None
        addresses = adult.addresses.filter(published__exact=True)
        phone_numbers = adult.phone_numbers.filter(published__exact=True)

        lines = ["BEGIN:VCARD", "VERSION:3.0"]
        lines.append(
            "N:{last};{first};{middle};;{suffix}".format(
                last=_vcard_escape(adult.last_name),
                first=_vcard_escape(adult.first_name),
                middle=_vcard_escape(adult.middle_name),
                suffix=_vcard_escape(adult.suffix),
            )
        )
        lines.append(f"FN:{_vcard_escape(adult.get_full_name())}")
        if adult.nickname:
            lines.append(f"NICKNAME:{_vcard_escape(adult.nickname)}")
        if email:
            lines.append(f"EMAIL;TYPE=HOME:{_vcard_escape(email)}")
        for phone in phone_numbers:
            vcard_type = self.PHONE_TYPE_MAP.get(phone.type, "CELL")
            lines.append(f"TEL;TYPE={vcard_type}:{_vcard_escape(phone.number.as_e164)}")
        for address in addresses:
            vcard_type = self.ADDRESS_TYPE_MAP.get(address.type, "HOME")
            street = address.street
            if address.street2:
                street = f"{street} {address.street2}"
            lines.append(
                "ADR;TYPE={type}:;;{street};{city};{state};{zip_code};".format(
                    type=vcard_type,
                    street=_vcard_escape(street),
                    city=_vcard_escape(address.city),
                    state=_vcard_escape(address.state),
                    zip_code=_vcard_escape(address.zip_code),
                )
            )
        lines.append(f"item1.URL:{request.build_absolute_uri(adult.get_absolute_url())}")
        lines.append(f"item1.X-ABLabel:{_vcard_escape(settings.PACK_SHORTNAME)}")
        lines.append("END:VCARD")

        content = "\r\n".join(lines) + "\r\n"
        response = HttpResponse(content, content_type="text/vcard")
        response["Content-Disposition"] = f'attachment; filename="{adult.slug}.vcf"'
        return response


class AdultUpdate(LoginRequiredMixin, UpdateView):
    model = Adult
    form_class = AdultForm
    context_object_name = "member"
    template_name = "membership/adult_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["address_formset"] = AddressFormSet(self.request.POST, instance=self.object)
            context["phonenumber_formset"] = PhoneNumberFormSet(self.request.POST, instance=self.object)
        else:
            context["address_formset"] = AddressFormSet(instance=self.object)
            context["phonenumber_formset"] = PhoneNumberFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data(form=form)
        address_formset = context["address_formset"]
        phonenumber_formset = context["phonenumber_formset"]
        if not address_formset.is_valid() or not phonenumber_formset.is_valid():
            return super().form_invalid(form)

        response = super().form_valid(form)
        address_formset.instance = self.object
        address_formset.save()
        phonenumber_formset.instance = self.object
        phonenumber_formset.save()
        return response


class ScoutList(LoginRequiredMixin, ListView):
    model = Scout
    paginate_by = 25
    context_object_name = "members"
    template_name = "membership/scout_list.html"

    def get_queryset(self):
        if self.request.user.active() or self.request.user.role == Adult.CONTRIBUTOR:
            # If you have active cubs or are a contributor, you can get all
            # active cubs
            return Scout.objects.filter(status__exact=Scout.ACTIVE)
        elif not self.request.user.family:
            # The user doesn't belong to a family, so we'll just show them
            # nothing
            return Scout.objects.none()
        else:
            # If you are not active, you only get members of your own family
            return Scout.objects.filter(family__exact=self.request.user.family)


class ScoutCreate(LoginRequiredMixin, CreateView):
    model = Scout
    form_class = ScoutForm
    context_object_name = "member"
    template_name = "membership/scout_form.html"

    def get_initial(self, *args, **kwargs):
        initial = super().get_initial(**kwargs)
        initial["last_name"] = self.request.user.last_name
        return initial

    def form_valid(self, form):
        form.instance.status = Scout.APPLIED
        request_user = Adult.objects.get(uuid=self.request.user.uuid)
        if not request_user.family:
            request_user.family = Family.objects.create()
            request_user.save()
        form.instance.family = request_user.family
        form.notify_membership(submitter=request_user)
        form.send_confirmation_email(submitter=request_user)
        return super().form_valid(form)


class ScoutDetail(LoginRequiredMixin, DetailView):
    model = Scout
    context_object_name = "member"
    template_name = "membership/scout_detail.html"


class ScoutUpdate(LoginRequiredMixin, UpdateView):
    model = Scout
    form_class = ScoutForm
    context_object_name = "member"
    template_name = "membership/scout_form.html"


class MyFamilyDetail(AdultDetail):
    """
    An extension of the AdultDetail page that displays the currently
    logged in user's details.
    """

    def get_object(self, queryset=None):
        return self.request.user
