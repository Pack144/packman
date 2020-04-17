from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import CreateView, DetailView, UpdateView, ListView

from . import forms, models


class MemberList(LoginRequiredMixin, ListView):
    model = models.Member
    paginate_by = 25
    context_object_name = 'member_list'
    template_name = 'membership/member_list.html'

    def get_queryset(self):
        if self.request.user.active or self.request.user.role == models.Adult.CONTRIBUTOR:
            # If you have active cubs or are a contributor, you can get all active members
            return models.Member.objects.filter(
                Q(adult__family__children__status__exact=models.Scout.ACTIVE) |
                Q(adult__role__exact=models.Adult.CONTRIBUTOR) |
                Q(scout__status__exact=models.Scout.ACTIVE)).distinct()
        elif not self.request.user.family:
            # The user doesn't belong to a family, so we'll just show them their own information
            return models.Member.objects.filter(adult__id__exact=self.request.user.uuid).distinct()
        else:
            # If you are not active, you can only get members of your own family
            return models.Member.objects.filter(Q(adult__family__exact=self.request.user.family) |
                                                Q(scout__family__exact=self.request.user.family))


class MemberSearchResultsList(LoginRequiredMixin, ListView):
    model = models.Member
    context_object_name = 'member_list'
    template_name = 'membership/member_search_results.html'

    def get_queryset(self):
        query = self.request.GET.get('q')
        results = models.Member.objects.filter(
            Q(adult__family__children__status__exact=models.Scout.ACTIVE) |
            Q(adult__role__exact=models.Adult.CONTRIBUTOR) |
            Q(scout__status__exact=models.Scout.ACTIVE)).filter(Q(first_name__icontains=query) |
                                                                      Q(last_name__icontains=query) |
                                                                      Q(middle_name__icontains=query) |
                                                                      Q(nickname__icontains=query)).distinct()

        if self.request.user.active or self.request.user.role == models.Adult.CONTRIBUTOR:
            # If you have active cubs or are a contributor, you can get all of the search results
            return results
        elif not self.request.user.family:
            # The user doesn't belong to a family, so we'll just show them their own information
            return models.Member.objects.filter(adult__id__exact=self.request.user.uuid)
        else:
            # If you are not active, you can only get members of your own family
            return results.filter(Q(adult__family__exact=self.request.user.family) |
                                  Q(scout__family__exact=self.request.user.family))


class FamilyUpdate(LoginRequiredMixin, DetailView):
    model = models.Adult
    context_object_name = 'member'
    template_name = 'membership/adult_detail.html'

    def get_object(self):
        # Return the currently signed on member's page
        return models.Adult.objects.get(uuid=self.request.user.uuid)


class AdultList(LoginRequiredMixin, ListView):
    model = models.Adult
    paginate_by = 25
    context_object_name = 'member_list'
    template_name = 'membership/adult_list.html'

    def get_queryset(self):
        if self.request.user.active or self.request.user.role == models.Adult.CONTRIBUTOR:
            # If you have active cubs or are a contributor, you can get all active members
            return models.Adult.objects.filter(
                Q(family__children__status=models.Scout.ACTIVE) |
                Q(role__exact=models.Adult.CONTRIBUTOR)).distinct()
        elif not self.request.user.family:
            # The user doesn't belong to a family, so we'll just show them their own information
            return models.Adult.objects.filter(id__exact=self.request.user.uuid)
        else:
            # If you are not active, you can only get members of your own family
            return models.Adult.objects.filter(family__exact=self.request.user.family)


class AdultCreate(LoginRequiredMixin, CreateView):
    model = models.Adult
    context_object_name = 'member'
    form_class = forms.AdultCreation
    template_name = 'membership/adult_form.html'

    def get_context_data(self, **kwargs):
        context = super(AdultCreate, self).get_context_data(**kwargs)
        if self.request.POST:
            context['address_formset'] = forms.AddressFormSet(self.request.POST)
            context['phonenumber_formset'] = forms.PhoneNumberFormSet(self.request.POST)
        else:
            context['address_formset'] = forms.AddressFormSet()
            context['phonenumber_formset'] = forms.PhoneNumberFormSet()
        return context

    def get_initial(self, *args, **kwargs):
        initial = super(AdultCreate, self).get_initial(**kwargs)
        initial['last_name'] = self.request.user.last_name
        return initial

    def form_valid(self, form):
        context = self.get_context_data(form=form)
        address_formset = context['address_formset']
        phonenumber_formset = context['phonenumber_formset']
        request_user = models.Adult.objects.get(uuid=self.request.user.uuid)
        if address_formset.is_valid() and phonenumber_formset.is_valid():
            self.object = form.save()
            address_formset.instance = self.object
            address_formset.save()
            phonenumber_formset.instance = self.object
            phonenumber_formset.save()
        else:
            return super().form_invalid(form)
        if not request_user.family:
            request_user.family = models.Family.objects.create()
            request_user.save()
        form.instance.family = request_user.family
        form.instance.password1 = models.Adult.objects.make_random_password()
        return super().form_valid(form)


class AdultDetail(LoginRequiredMixin, DetailView):
    model = models.Adult
    context_object_name = 'member'
    template_name = 'membership/adult_detail.html'


class AdultUpdate(LoginRequiredMixin, UpdateView):
    model = models.Adult
    form_class = forms.AdultForm
    context_object_name = 'member'
    template_name = 'membership/adult_form.html'

    def get_context_data(self, **kwargs):
        context = super(AdultUpdate, self).get_context_data(**kwargs)
        if self.request.POST:
            context['address_formset'] = forms.AddressFormSet(self.request.POST, instance=self.object)
            context['phonenumber_formset'] = forms.PhoneNumberFormSet(self.request.POST, instance=self.object)
        else:
            context['address_formset'] = forms.AddressFormSet(instance=self.object)
            context['phonenumber_formset'] = forms.PhoneNumberFormSet(instance=self.object)
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
    model = models.Scout
    paginate_by = 25
    context_object_name = 'member_list'
    template_name = 'membership/scout_list.html'

    def get_queryset(self):
        if self.request.user.active or self.request.user.role == models.Adult.CONTRIBUTOR:
            # If you have active cubs or are a contributor, you can get all active cubs
            return models.Scout.objects.filter(status__exact=models.Scout.ACTIVE)
        elif not self.request.user.family:
            # The user doesn't belong to a family, so we'll just show them nothing
            return models.Scout.objects.none()
        else:
            # If you are not active, you can only get members of your own family
            return models.Scout.objects.filter(family__exact=self.request.user.family)


class ScoutCreate(LoginRequiredMixin, CreateView):
    model = models.Scout
    form_class = forms.ScoutForm
    context_object_name = 'member'
    template_name = 'membership/scout_form.html'

    def get_initial(self, *args, **kwargs):
        initial = super(ScoutCreate, self).get_initial(**kwargs)
        initial['last_name'] = self.request.user.last_name
        return initial

    def form_valid(self, form):
        form.instance.status = models.Scout.APPLIED
        request_user = models.Adult.objects.get(uuid=self.request.user.uuid)
        if not request_user.family:
            request_user.family = models.Family.objects.create()
            request_user.save()
        form.instance.family = request_user.family
        return super().form_valid(form)


class ScoutDetail(LoginRequiredMixin, DetailView):
    model = models.Scout
    context_object_name = 'member'
    template_name = 'membership/scout_detail.html'


class ScoutUpdate(LoginRequiredMixin, UpdateView):
    model = models.Scout
    form_class = forms.ScoutForm
    context_object_name = 'member'
    template_name = 'membership/scout_form.html'
