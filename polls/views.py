from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView, RedirectView

from membership.mixins import ActiveMemberOrContributorTest

from .models import Choice, Question, Vote


class IndexView(ActiveMemberOrContributorTest, ListView):
    template_name = 'polls/index.html'
    context_object_name = 'latest_question_list'

    def get_queryset(self):
        return Question.objects.filter(poll_opens__lte=timezone.now()).filter(poll_closes__gt=timezone.now())


class QuestionView(ActiveMemberOrContributorTest, DetailView):
    model = Question
    template_name = 'polls/detail.html'

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        context['question'].votable = self.object.can_vote(self.request.user)
        context['question'].votes_cast = self.object.vote_set.filter(family=self.request.user.family) if not self.object.is_anonymous else None

        if not context['question'].votable:
            context['error_title'] = _("You've voted")
            context['error_level'] = 'info'
            context['error_message'] = _("You have already voted on this question. There is nothing more you need to do.")

        elif self.object.poll_opens > timezone.now():
            context['error_title'] = _("Please Wait")
            context['error_level'] = 'warning'
            context['error_message'] = _(f"This question will be available to answer at {self.object.poll_opens}.")

        elif self.object.poll_closes <= timezone.now():
            context['error_title'] = _("Time's Up")
            context['error_level'] = 'warning'
            context['error_message'] = _(f"The deadline to submit responses was {self.object.poll_opens}.")

        return context

    def get_queryset(self):
        """
        Excludes any questions that aren't published yet.
        """
        return Question.objects.filter(poll_opens__lte=timezone.now()).filter(poll_closes__gt=timezone.now())


class ResultsView(ActiveMemberOrContributorTest, DetailView):
    model = Question
    template_name = 'polls/results.html'


class VoteView(ActiveMemberOrContributorTest, RedirectView):
    def post(self, request, *args, **kwargs):
        question = Question.objects.get(id=kwargs['pk'])
        family = request.user.family
        choice = Choice.objects.get(id=request.POST['choice'])
        Vote.objects.create(question=question, family=family, choice=choice)
        messages.success(request, _("Thank you for your vote"))
        return super(VoteView, self).post(request, *args, **kwargs)

    def get_redirect_url(self, **kwargs):
        return reverse_lazy('polls:detail', args=[kwargs['pk']])
