from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import CreateView, DetailView, UpdateView, ListView

from .models import Member, Parent, Scout


class ActiveMemberTestMixin(UserPassesTestMixin):
    def test_func(self):
        if self.request.user.is_authenticated:
            return self.request.user.profile.status == 'A'


class MemberListView(ActiveMemberTestMixin, ListView):
    model = Member
    paginate_by = 25

    def get_queryset(self):
        return Member.objects.filter(status__exact='A')


class ParentListView(ActiveMemberTestMixin, ListView):
    model = Parent
    paginate_by = 25

    def get_queryset(self):
        return Parent.objects.filter(status__exact='A')


class ParentCreateView(ActiveMemberTestMixin, CreateView):
    model = Parent
    fields = '__all__'


class ParentDetailView(ActiveMemberTestMixin, DetailView):
    model = Parent


class ParentUpdateView(ActiveMemberTestMixin, UpdateView):
    model = Parent
    fields = '__all__'


class ScoutListView(ActiveMemberTestMixin, ListView):
    model = Scout
    paginate_by = 25

    def get_queryset(self):
        return Scout.objects.filter(status__exact='A')


class ScoutCreateView(LoginRequiredMixin, CreateView):
    model = Scout
    fields = '__all__'


class ScoutDetailView(ActiveMemberTestMixin, DetailView):
    model = Scout


class ScoutUpdateView(ActiveMemberTestMixin, UpdateView):
    model = Scout
    fields = '__all__'
