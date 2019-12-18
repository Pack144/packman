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
        if self.request.user.active or self.request.user.role == models.AdultMember.CONTRIBUTOR:
            # If you have active cubs or are a contributor, you can get all active members
            return models.Member.objects.filter(
                Q(adultmember__family__children__status__exact=models.ChildMember.ACTIVE) | \
                Q(childmember__status__exact=models.ChildMember.ACTIVE))
        else:
            # If you are not active, you can only get members of your own family
            return models.Member.objects.filter(Q(adultmember__isnull=False), Q(adultmember__family__exact=self.request.user.family) | \
                                                Q(childmember__isnull=False), Q(childmember__family__exact=self.request.user.family))


class MemberSearchResultsList(LoginRequiredMixin, ListView):
    model = models.Member
    context_object_name = 'member_list'
    template_name = 'membership/member_search_results.html'

    def get_queryset(self):
        query = self.request.GET.get('q')
        results = models.Member.objects.filter(Q(first_name__icontains=query) | \
                                               Q(last_name__icontains=query) | \
                                               Q(middle_name__icontains=query) | \
                                               Q(nickname__icontains=query))

        if self.request.user.active or self.request.user.role == models.AdultMember.CONTRIBUTOR:
            # If you have active cubs or are a contributor, you can get all of the search results
            return results
        else:
            # If you are not active, you can only get members of your own family
            return results.filter(Q(adultmember__isnull=False), Q(adultmember__family__exact=self.request.user.family) | \
                                  Q(childmember__isnull=False), Q(childmember__family__exact=self.request.user.family))


class FamilyUpdate(LoginRequiredMixin, UpdateView):
    model = models.AdultMember
    form_class = forms.AdultMemberForm
    context_object_name = 'member'
    template_name = 'membership/family_form.html'

    def get_object(self):
        # Return the currently signed on member's page
        return models.AdultMember.objects.get(id=self.request.user.id)

    # def get_context_data(self, **kwargs):
    #     context = super(FamilyUpdate, self).get_context_data(**kwargs)
    #     if self.request.POST:
    #         context['address_formset'] = forms.AddressFormSet(self.request.POST, instance=self.object)
    #         context['address_formset'].full_clean()
    #         context['phonenumber_formset'] = forms.PhoneNumberFormSet(self.request.POST, instance=self.object)
    #         context['phonenumber_formset'].full_clean()
    #     else:
    #         context['address_formset'] = forms.AdultMemberChange(instance=self.object)
    #         context['phonenumber_formset'] = forms.PhoneNumberFormSet(instance=self.object)
    #     return context

    # def form_valid(self, form):
    #     context = self.get_context_data(form=form)
    #     formset = context['address_formset']
    #     if formset.is_valid():
    #         response = super().form_valid(form)
    #         formset.instance = self.object
    #         formset.save()
    #         return response
    #     else:
    #         return super().form_invalid(form)


class AdultMemberList(LoginRequiredMixin, ListView):
    model = models.AdultMember
    paginate_by = 25
    context_object_name = 'member_list'
    template_name = 'membership/adultmember_list.html'

    def get_queryset(self):
        if self.request.user.active or self.request.user.role == models.AdultMember.CONTRIBUTOR:
            # If you have active cubs or are a contributor, you can get all active members
            return models.AdultMember.objects.filter(family__children__status=models.ChildMember.ACTIVE)
        else:
            # If you are not active, you can only get members of your own family
            return models.AdultMember.objects.filter(family__exact=self.request.user.family)


class AdultMemberCreate(LoginRequiredMixin, CreateView):
    model = models.AdultMember
    form_class = forms.AdultMemberCreation
    context_object_name = 'member'
    template_name = 'membership/adultmember_form.html'

    def get_initial(self, *args, **kwargs):
        initial = super(AdultMemberCreate, self).get_initial(**kwargs)
        initial['last_name'] = self.request.user.last_name
        return initial

    def form_valid(self, form):
        form.instance.family = self.request.user.family
        return super().form_valid(form)


class AdultMemberDetail(LoginRequiredMixin, DetailView):
    model = models.AdultMember
    context_object_name = 'member'
    template_name = 'membership/adultmember_detail.html'


class AdultMemberUpdate(LoginRequiredMixin, UpdateView):
    model = models.AdultMember
    form_class = forms.AdultMemberForm
    context_object_name = 'member'
    template_name = 'membership/adultmember_update_form.html'


class ChildMemberList(LoginRequiredMixin, ListView):
    model = models.ChildMember
    paginate_by = 25
    context_object_name = 'member_list'
    template_name = 'membership/childmember_list.html'

    def get_queryset(self):
        if self.request.user.active or self.request.user.role == models.AdultMember.CONTRIBUTOR:
            # If you have active cubs or are a contributor, you can get all active cubs
            return models.ChildMember.objects.filter(status__exact=models.ChildMember.ACTIVE)
        else:
            # If you are not active, you can only get members of your own family
            return models.ChildMember.objects.filter(family__exact=self.request.user.family)


class ChildMemberCreate(LoginRequiredMixin, CreateView):
    model = models.ChildMember
    form_class = forms.ChildMemberForm
    context_object_name = 'member'
    template_name = 'membership/childmember_form.html'

    def get_initial(self, *args, **kwargs):
        initial = super(ChildMemberCreate, self).get_initial(**kwargs)
        initial['last_name'] = self.request.user.last_name
        return initial

    def form_valid(self, form):
        form.instance.status = models.ChildMember.APPLIED
        form.instance.family = self.request.user.family
        return super().form_valid(form)


class ChildMemberDetail(LoginRequiredMixin, DetailView):
    model = models.ChildMember
    context_object_name = 'member'
    template_name = 'membership/childmember_detail.html'


class ChildMemberUpdate(LoginRequiredMixin, UpdateView):
    model = models.ChildMember
    form_class = forms.ChildMemberForm
    context_object_name = 'member'
    template_name = 'membership/childmember_update_form.html'
