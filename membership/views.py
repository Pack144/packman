from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms import (
    AddressFormSet, AdultCreation, AdultForm, PhoneNumberFormSet, ScoutForm
)
from .models import Adult, Family, Member, Scout


class MemberList(LoginRequiredMixin, ListView):
    model = Member
    paginate_by = 25
    context_object_name = 'member_list'
    template_name = 'membership/member_list.html'

    def get_queryset(self):
        if self.request.user.active() or self.request.user.role == Adult.CONTRIBUTOR:
            # If you have active cubs or are a contributor, you can see all
            # active members
            return Member.objects.filter(
                Q(adult__family__children__status__exact=Scout.ACTIVE) |
                Q(adult__role__exact=Adult.CONTRIBUTOR) |
                Q(scout__status__exact=Scout.ACTIVE)
            ).distinct()
        elif not self.request.user.family:
            # The user doesn't belong to a family, so we'll just show them
            # their own information
            return Member.objects.filter(
                adult__uuid__exact=self.request.user.uuid
            ).distinct()
        else:
            # If you are not active, you can only see your own family
            return Member.objects.filter(
                Q(adult__family__exact=self.request.user.family) |
                Q(scout__family__exact=self.request.user.family)
            )


class MemberSearchResultsList(LoginRequiredMixin, ListView):
    model = Member
    context_object_name = 'member_list'
    template_name = 'membership/member_search_results.html'

    def get_queryset(self):
        query = self.request.GET.get('q')
        if self.request.GET.get('alum') == 'on':
            results = Member.objects.filter(
                Q(adult__family__children__status__gte=Scout.ACTIVE) |
                Q(scout__status__gte=Scout.ACTIVE)
            ).filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(middle_name__icontains=query) |
                Q(nickname__icontains=query)
            ).distinct()
        else:
            results = Member.objects.filter(
                Q(adult__family__children__status__exact=Scout.ACTIVE) |
                Q(adult__role__exact=Adult.CONTRIBUTOR) |
                Q(scout__status__exact=Scout.ACTIVE)
            ).filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(middle_name__icontains=query) |
                Q(nickname__icontains=query)
            ).distinct()

        if self.request.user.active() or self.request.user.role == Adult.CONTRIBUTOR:
            # If you have active cubs or are a contributor, you can get all of
            # the search results
            return results
        elif not self.request.user.family:
            # The user doesn't belong to a family, so we'll just show them
            # their own information
            return Member.objects.filter(
                adult__uuid__exact=self.request.user.uuid
            )
        else:
            # If you are not active, you only get members of your own family
            return results.filter(
                Q(adult__family__exact=self.request.user.family) |
                Q(scout__family__exact=self.request.user.family)
            )


class AdultList(LoginRequiredMixin, ListView):
    model = Adult
    paginate_by = 25
    context_object_name = 'member_list'
    template_name = 'membership/adult_list.html'

    def get_queryset(self):
        if self.request.user.active() or self.request.user.role == Adult.CONTRIBUTOR:
            # If you have active cubs or are a contributor, you can get all
            # active members
            return Adult.objects.filter(
                Q(family__children__status=Scout.ACTIVE) |
                Q(role__exact=Adult.CONTRIBUTOR)
            ).distinct()
        elif not self.request.user.family:
            # The user doesn't belong to a family, so we'll just show them
            # their own information
            return Adult.objects.filter(
                uuid__exact=self.request.user.uuid
            )
        else:
            # If you are not active, you only get members of your own family
            return Adult.objects.filter(
                family__exact=self.request.user.family
            )


class AdultCreate(LoginRequiredMixin, CreateView):
    model = Adult
    context_object_name = 'member'
    form_class = AdultCreation
    template_name = 'membership/adult_form.html'

    def get_context_data(self, **kwargs):
        context = super(AdultCreate, self).get_context_data(**kwargs)
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
        return context

    def form_valid(self, form):
        context = self.get_context_data(form=form)
        address_formset = context['address_formset']
        phonenumber_formset = context['phonenumber_formset']
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
    context_object_name = 'member'
    template_name = 'membership/adult_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['email'] = self.object.email if self.object.is_published else None
        context['addresses'] = self.object.addresses.filter(published__exact=True)
        context['phone_numbers'] = self.object.phone_numbers.filter(published__exact=True)
        return context


class AdultUpdate(LoginRequiredMixin, UpdateView):
    model = Adult
    form_class = AdultForm
    context_object_name = 'member'
    template_name = 'membership/adult_form.html'

    def get_context_data(self, **kwargs):
        context = super(AdultUpdate, self).get_context_data(**kwargs)
        if self.request.POST:
            context['address_formset'] = AddressFormSet(
                self.request.POST,
                instance=self.object
            )
            context['phonenumber_formset'] = PhoneNumberFormSet(
                self.request.POST,
                instance=self.object
            )
        else:
            context['address_formset'] = AddressFormSet(
                instance=self.object
            )
            context['phonenumber_formset'] = PhoneNumberFormSet(
                instance=self.object
            )
        return context

    def form_valid(self, form):
        context = self.get_context_data(form=form)
        address_formset = context['address_formset']
        phonenumber_formset = context['phonenumber_formset']
        if address_formset.is_valid() and phonenumber_formset.is_valid():
            response = super().form_valid(form)
            address_formset.instance = self.object
            address_formset.save()
            phonenumber_formset.instance = self.object
            phonenumber_formset.save()
            return response
        else:
            return super().form_invalid(form)


class ScoutList(LoginRequiredMixin, ListView):
    model = Scout
    paginate_by = 25
    context_object_name = 'member_list'
    template_name = 'membership/scout_list.html'

    def get_queryset(self):
        if self.request.user.active() or self.request.user.role == Adult.CONTRIBUTOR:
            # If you have active cubs or are a contributor, you can get all
            # active cubs
            return Scout.objects.filter(
                status__exact=Scout.ACTIVE
            )
        elif not self.request.user.family:
            # The user doesn't belong to a family, so we'll just show them
            # nothing
            return Scout.objects.none()
        else:
            # If you are not active, you only get members of your own family
            return Scout.objects.filter(
                family__exact=self.request.user.family
            )


class ScoutCreate(LoginRequiredMixin, CreateView):
    model = Scout
    form_class = ScoutForm
    context_object_name = 'member'
    template_name = 'membership/scout_form.html'

    def get_initial(self, *args, **kwargs):
        initial = super(ScoutCreate, self).get_initial(**kwargs)
        initial['last_name'] = self.request.user.last_name
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
    context_object_name = 'member'
    template_name = 'membership/scout_detail.html'


class ScoutUpdate(LoginRequiredMixin, UpdateView):
    model = Scout
    form_class = ScoutForm
    context_object_name = 'member'
    template_name = 'membership/scout_form.html'
