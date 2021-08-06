from django.db import models
from django.db.models import Prefetch


class MessageQuerySet(models.QuerySet):
    def for_recipient(self, recipient):
        message_recipients = self.model.message_recipients.field.model.objects.filter(recipient=recipient)
        return self.filter(recipients=recipient).prefetch_related(Prefetch("message_recipients", queryset=message_recipients, to_attr="recipient")).distinct()

    def in_inbox(self, recipient):
        return self.for_recipient(recipient).filter(
            message_recipient__date_archived__isnull=True, message_recipient__date_deleted__isnull=True
        )

    def unread(self, recipient):
        return self.for_recipient(recipient).filter(message_recipient__date_read__isnull=True)

    def archived(self, recipient):
        return self.for_recipient(recipient).filter(message_recipient__date_archived__isnull=False)

    def deleted(self, recipient):
        return self.for_recipient(recipient).filter(message_recipient__date_deleted__isnull=False)

    def drafts(self, author):
        return self.filter(author=author, date_sent__isnull=True)

    def sent(self, author):
        return self.filter(author=author, date_sent__isnull=False)


class MessageManager(models.Manager):
    def get_queryset(self):
        return MessageQuerySet(self.model, using=self._db)

    def in_inbox(self, recipient):
        return self.get_queryset().in_inbox(recipient)

    def unread(self, recipient):
        return self.get_queryset().unread(recipient)

    def archived(self, recipient):
        return self.get_queryset().archived(recipient)

    def deleted(self, recipient):
        return self.get_queryset().deleted(recipient)

    def drafts(self, author):
        return self.get_queryset().drafts(author)

    def sent(self, author):
        return self.get_queryset().sent(author)
