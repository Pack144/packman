from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.views.generic import CreateView, DetailView, UpdateView, ListView

from .models import Member, Parent, Scout


class ActiveMemberTestMixin(UserPassesTestMixin):
    """ Parents with active cubs should be allowed to view this page """
    def test_func(self):
        if self.request.user.is_authenticated:
            return self.request.user.profile.is_active


class ContributorTestMixin(UserPassesTestMixin):
    """ Contributors should be allowed to view this page """
    def test_func(self):
        if self.request.user.is_authenticated:
            return self.request.user.profile.role == 'C'


class MemberListView(ActiveMemberTestMixin, ContributorTestMixin, ListView):
    model = Member
    paginate_by = 25
    template_name = 'membership/member_list.html'

    @staticmethod
    def get_queryset(self):
        return Member.objects.filter(Q(parent__children__status__contains='A') | Q(scout__status__exact='A'))


class ParentListView(ActiveMemberTestMixin, ContributorTestMixin, ListView):
    model = Parent
    paginate_by = 25
    template_name = 'membership/parent_list.html'

    @staticmethod
    def get_queryset():
        return Parent.objects.filter(children__status__contains='A')


class ScoutListView(ActiveMemberTestMixin, ContributorTestMixin, ListView):
    model = Scout
    paginate_by = 25
    template_name = 'membership/scout_list.html'

    @staticmethod
    def get_queryset(self):
        return Scout.objects.filter(status__exact='A')


class ParentCreateView(ActiveMemberTestMixin, CreateView):
    model = Parent
    fields = '__all__'


class ParentDetailView(ActiveMemberTestMixin, DetailView):
    model = Parent


class ParentUpdateView(ActiveMemberTestMixin, UpdateView):
    model = Parent
    fields = '__all__'
    template_name_suffix = '_update_form'


class ScoutCreateView(LoginRequiredMixin, CreateView):
    model = Scout
    fields = '__all__'


class ScoutDetailView(ActiveMemberTestMixin, DetailView):
    model = Scout


class ScoutUpdateView(ActiveMemberTestMixin, UpdateView):
    model = Scout
    fields = '__all__'
    template_name_suffix = '_update_form'


class FamilyUpdateView(LoginRequiredMixin, UpdateView):
    model = Parent
    fields = '__all__'

    def get_object(self):
        return Parent.objects.get(id=self.request.user.profile.id)
