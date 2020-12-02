from django.db import models
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from tinymce.models import HTMLField


def two_weeks_hence(when=timezone.now()):
    return when + timezone.timedelta(weeks=2)


class Question(models.Model):
    question_text = models.CharField(
        max_length=200,
    )
    description = HTMLField(
        blank=True,
        null=True,
    )
    poll_opens = models.DateTimeField(
        _("poll opens"),
        default=timezone.now,
        blank=True,
    )
    poll_closes = models.DateTimeField(
        _("poll closes"),
        default=two_weeks_hence,
        blank=True,
    )

    is_anonymous = models.BooleanField(
        _("anonymous"),
        default=False,
    )
    is_editable = models.BooleanField(
        _("editable"),
        default=True,
    )

    class Meta:
        ordering = ('-poll_closes', )

    def __str__(self):
        return self.question_text

    def get_absolute_url(self):
        return reverse_lazy('polls:detail', kwargs={'pk': self.pk})

    def can_vote(self, member):
        if self.poll_opens <= timezone.now() <= self.poll_closes:
            return member.get_active_scouts().count() - self.vote_set.filter(
                family=member.family
            ).count()

    def count_choices(self):
        return self.choice_set.count()

    def count_total_votes(self):
        return sum(choice.count_votes() for choice in self.choice_set.all())

    def was_published_recently(self):
        now = timezone.now()
        return now - timezone.timedelta(days=1) <= self.poll_opens <= now

    was_published_recently.admin_order_field = 'poll_opens'
    was_published_recently.boolean = True
    was_published_recently.short_description = _("Recently published?")


class Choice(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
    )
    choice_text = models.CharField(
        max_length=200,
    )

    def __str__(self):
        return self.choice_text

    def count_votes(self):
        return self.vote_set.count()


class Vote(models.Model):
    family = models.ForeignKey(
        'membership.Family',
        on_delete=models.CASCADE,
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
    )
    choice = models.ForeignKey(
        Choice,
        on_delete=models.CASCADE,
    )

    date_added = models.DateTimeField(
        auto_now_add=True,
    )
    last_updated = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"Vote for {self.choice}"
