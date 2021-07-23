from django.db import models


class MessageQuerySet(models.QuerySet):
    def in_inbox(self, recipient):
        return self.filter(
            recipients=recipient, recipients__date_archived__isnull=True, recipients__date_deleted__isnull=True
        )

    def unread(self, recipient):
        return self.filter(recipients=recipient, recipients__date_read__isnull=True)

    def archived(self, recipient):
        return self.filter(recipients=recipient, recipients__date_archived__isnull=False)

    def deleted(self, recipient):
        return self.filter(recipients=recipient, recipients__date_deleted__isnull=False)

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
