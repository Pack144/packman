from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.forms import inlineformset_factory
from django.views.generic import CreateView, DetailView, UpdateView, ListView

from .forms import ParentForm, ScoutForm
from .mixins import ActiveMemberTestMixin, ActiveMemberOrContributorTestMixin
from .models import Member, Parent, Scout


class MemberListView(ActiveMemberOrContributorTestMixin, ListView):
    model = Member
    paginate_by = 25
    template_name = 'membership/member_list.html'

    def get_queryset(self):
        return Member.objects.filter(Q(parent__children__status__contains='A') | Q(scout__status__exact='A')).distinct()


class ParentListView(ActiveMemberOrContributorTestMixin, ListView):
    model = Parent
    paginate_by = 25
    template_name = 'membership/parent_list.html'

    def get_queryset(self):
        return Parent.objects.filter(children__status__contains='A').distinct()


class ScoutListView(ActiveMemberOrContributorTestMixin, ListView):
    model = Scout
    paginate_by = 25
    template_name = 'membership/scout_list.html'

    def get_queryset(self):
        return Scout.objects.filter(status__exact='A').distinct()


class ParentCreateView(ActiveMemberTestMixin, CreateView):
    model = Parent
    fields = '__all__'


class ParentDetailView(ActiveMemberTestMixin, DetailView):
    model = Parent


class ParentUpdateView(ActiveMemberTestMixin, UpdateView):
    model = Parent
    form_class = ParentForm
    template_name_suffix = '_update_form'


class ScoutCreateView(LoginRequiredMixin, CreateView):
    model = Scout
    fields = '__all__'


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
