from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.views.generic import CreateView, DetailView, UpdateView, ListView

from .models import Member, Parent, Scout


class ActiveMemberTestMixin(UserPassesTestMixin):
    """ Parents with active cubs should be allowed to view this page """
    def test_func(self):
        if self.request.user.is_authenticated:
            return self.request.user.profile.active_scouts().count()


class ContributorTestMixin(UserPassesTestMixin):
    """ Contributors should be allowed to view this page """
    def test_func(self):
        if self.request.user.is_authenticated:
            return self.request.user.profile.role == 'C'


class CurrentFamilyTestMixin(UserPassesTestMixin):
    # TODO: This isn't working…yet. This test is performed prior to loading the object for the
    #  page, so it always evaluates to false.
    """ Parents viewing their own family details should be allowed """
    def test_func(self):
        model = self.get_object()
        print(model)
        if self.request.user.is_authenticated:
            if self.request.user.profile == model:
                """ User is looking at their own page """
                return True
            elif self.request.user.profile.children.objects.filter(parents__contain='self.request.user.profile.id'):
                """ User is looking at their child's page """


class MemberListView(ActiveMemberTestMixin, ContributorTestMixin, ListView):
    model = Member
    paginate_by = 25
    template_name = 'membership/member_list.html'

    def get_queryset(self):
        return Member.objects.filter(Q(parent__children__status__contains='A') | Q(scout__status__exact='A'))


class ParentListView(MemberListView):
    model = Parent
    template_name = 'membership/parent_list.html'

    def get_queryset(self):
        return Parent.objects.filter(children__status__contains='A')


class ScoutListView(MemberListView):
    model = Scout
    template_name = 'membership/scout_list.html'

    def get_queryset(self):
        return Scout.objects.filter(status__exact='A')


class ParentCreateView(ActiveMemberTestMixin, CreateView):
    model = Parent
    fields = '__all__'


class ParentDetailView(ActiveMemberTestMixin, CurrentFamilyTestMixin, DetailView):
    model = Parent


class ParentUpdateView(ActiveMemberTestMixin, CurrentFamilyTestMixin, UpdateView):
    model = Parent
    fields = '__all__'
    template_name_suffix = '_update_form'


class ScoutCreateView(LoginRequiredMixin, CreateView):
    model = Scout
    fields = '__all__'


class ScoutDetailView(ActiveMemberTestMixin, CurrentFamilyTestMixin, DetailView):
    model = Scout


class ScoutUpdateView(ActiveMemberTestMixin, CurrentFamilyTestMixin, UpdateView):
    model = Scout
    fields = '__all__'
    template_name_suffix = '_update_form'
