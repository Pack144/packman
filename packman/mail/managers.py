from django.db import models
from django.db.models import Prefetch


class MessageQuerySet(models.QuerySet):
    def with_receipts(self, recipient):
        message_recipients_filter = self.model.message_recipients.field.model.objects.filter(recipient=recipient)
        return self.prefetch_related(
            Prefetch(
                "message_recipients", queryset=message_recipients_filter.select_related("recipient"), to_attr="receipt"
            ),
            "receipt",
        )

    def in_inbox(self, recipient):
        return self.with_receipts(recipient).filter(
            message_recipient__recipient=recipient,
            message_recipient__date_archived__isnull=True,
            message_recipient__date_deleted__isnull=True,
        )

    def unread(self, recipient):
        return self.with_receipts(recipient).filter(
            message_recipient__recipient=recipient, message_recipient__date_read__isnull=True
        )

    def archived(self, recipient):
        return self.with_receipts(recipient).filter(
            message_recipient__recipient=recipient, message_recipient__date_archived__isnull=False
        )

    def deleted(self, recipient):
        return self.with_receipts(recipient).filter(
            message_recipient__recipient=recipient, message_recipient__date_deleted__isnull=False
        )

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

    def for_recipient(self, recipient):
        return self.get_queryset().with_receipts(recipient)

    def in_mailbox(self, recipient, mailbox):
        if mailbox == "inbox":
            return self.get_queryset().in_inbox(recipient)
        elif mailbox == "drafts":
            return self.get_queryset().drafts(recipient)
        elif mailbox == "sent":
            return self.get_queryset().sent(recipient)
        elif mailbox == "archives":
            return self.get_queryset().archived(recipient)
        elif mailbox == "trash":
            return self.get_queryset().deleted(recipient)


class MessageRecipientQuerySet(models.QuerySet):
    def unread(self):
        return self.filter(date_read__isnull=True)
