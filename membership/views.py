from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import CreateView, DetailView, UpdateView, ListView

from .forms import ParentForm, ScoutForm, AddressFormSet, PhoneNumberFormSet
from .mixins import ActiveMemberTestMixin, ActiveMemberOrContributorTestMixin
from .models import Member, Parent, Scout

user = get_user_model()


class MemberListView(ActiveMemberOrContributorTestMixin, ListView):
    model = Member
    paginate_by = 25
    template_name = 'membership/member_list.html'

    def get_queryset(self):
        return Member.objects.filter(Q(parent__family__children__status__exact='A') | Q(scout__status__exact='A'))


class ParentListView(ActiveMemberOrContributorTestMixin, ListView):
    model = Parent
    paginate_by = 25
    template_name = 'membership/parent_list.html'

    def get_queryset(self):
        return Parent.objects.filter(family__children__status__exact='A')


class ScoutListView(ActiveMemberOrContributorTestMixin, ListView):
    model = Scout
    paginate_by = 25
    template_name = 'membership/scout_list.html'

    def get_queryset(self):
        return Scout.objects.filter(status__exact='A').distinct()


class MemberSearchResultsView(ActiveMemberOrContributorTestMixin, ListView):
    model = Member
    context_object_name = 'member_list'
    template_name = 'membership/member_search_results.html'

    def get_queryset(self):
        query = self.request.GET.get('q')
        return Member.objects.filter(
            Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(middle_name__icontains=query) | Q(nickname__icontains=query)
        )


class ParentCreateView(LoginRequiredMixin, CreateView):
    model = Parent
    form_class = ParentForm

    def get_initial(self, *args, **kwargs):
        initial = super(ParentCreateView, self).get_initial(**kwargs)
        initial['last_name'] = self.request.user.profile.last_name
        initial['family'] = [self.request.user.profile.family.id]
        return initial

    def form_valid(self, form):
        form.instance.family = self.request.user.profile.family
        return super().form_valid(form)


class ParentDetailView(ActiveMemberTestMixin, DetailView):
    model = Parent


class ParentUpdateView(ActiveMemberTestMixin, UpdateView):
    model = Parent
    form_class = ParentForm
    template_name_suffix = '_update_form'


class ScoutCreateView(LoginRequiredMixin, CreateView):
    model = Scout
    form_class = ScoutForm

    def get_initial(self, *args, **kwargs):
        initial = super(ScoutCreateView, self).get_initial(**kwargs)
        initial['last_name'] = self.request.user.profile.last_name
        return initial

    def form_valid(self, form):
        form.instance.status = 'W'
        form.instance.family = self.request.user.profile.family
        return super().form_valid(form)


class ScoutDetailView(ActiveMemberTestMixin, DetailView):
    model = Scout


class ScoutUpdateView(ActiveMemberTestMixin, UpdateView):
    model = Scout
    form_class = ScoutForm
    template_name_suffix = '_update_form'


class FamilyUpdateView(LoginRequiredMixin, UpdateView):
    model = Parent
    form_class = ParentForm
    template_name = 'membership/family_form.html'

    def get_object(self):
        return Parent.objects.get(id=self.request.user.profile.id)

    def get_context_data(self, **kwargs):
        context = super(FamilyUpdateView, self).get_context_data(**kwargs)
        if self.request.POST:
            context['address_formset'] = AddressFormSet(self.request.POST, instance=self.object)
            context['address_formset'].full_clean()
            context['phonenumber_formset'] = PhoneNumberFormSet(self.request.POST, instance=self.object)
            context['phonenumber_formset'].full_clean()
        else:
            context['address_formset'] = AddressFormSet(instance=self.object)
            context['phonenumber_formset'] = PhoneNumberFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data(form=form)
        formset = context['address_formset']
        if formset.is_valid():
            response = super().form_valid(form)
            formset.instance = self.object
            formset.save()
            return response
        else:
            return super().form_invalid(form)
