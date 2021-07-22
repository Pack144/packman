from pathlib import Path

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core import mail
from django.db import models, IntegrityError, transaction
from django.db.models import Q
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from packman.core.models import TimeStampedModel, TimeStampedUUIDModel
from packman.dens.models import Den
from packman.committees.models import Committee

from .managers import MessageManager
from packman.calendars.models import PackYear
from packman.membership.models import Family

User = get_user_model()


def get_upload_to(instance, filename):
    return _("mail/%(uuid)s/%(file)s") % {"uuid": instance.message.uuid, "file": filename}


class DistributionList(TimeStampedModel):
    """
    A simple model to track message group addresses and their members.
    """

    name = models.CharField(_("name"), max_length=150, unique=True)

    is_all = models.BooleanField(_("all members"), default=False, help_text=_("Messages sent to this distribution list should be delivered to all active members of the Pack."))
    dens = models.ManyToManyField(Den, related_name="distribution_list", related_query_name="distribution_list", blank=True)
    committees = models.ManyToManyField(Committee, related_name="distribution_list", related_query_name="distribution_list", blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("Distribution List")
        verbose_name_plural = _("Distribution Lists")

    def __str__(self):
        return self.name

    def get_members(self):
        if self.is_all:
            return User.objects.active()

        return User.objects.active().filter(
            Q(committee_membership__year=PackYear.objects.current(), committee__in=self.committees.all()) |
            Q(family__in=Family.objects.in_den(self.dens.all()))
        ).distinct()


class EmailAddress(TimeStampedModel):
    """
    A simple model to track an email address.
    """
    distribution_list = models.ForeignKey(DistributionList, on_delete=models.CASCADE, related_name="addresses")
    address = models.EmailField(_("email address"), unique=True, error_messages={"unique": _("A distribution list with this email address already exists.")})
    is_default = models.BooleanField(_("default"), default=False, help_text=_("Indicates whether this address should be used as the default from address."))

    class Meta:
        ordering = ("-is_default", "address")
        verbose_name = _("Email Address")
        verbose_name_plural = _("Email Addresses")

    def __str__(self):
        return self.address

    def save(self, **kwargs):
        # Check to ensure whether one and only one address is default for the distribution list.
        if self.is_default:
            EmailAddress.objects.filter(distribution_list=self.distribution_list, is_default=True).update(is_default=False)
        elif not EmailAddress.objects.filter(distribution_list=self.distribution_list, is_default=True).exists():
            self.is_default = True
        super().save(**kwargs)


class Thread(TimeStampedUUIDModel):
    """
    A simple model to track a thread of messages.
    """

    class Meta:
        verbose_name = _("Thread")
        verbose_name_plural = _("Threads")

    def __str__(self):
        return str(self.pk)


class Message(TimeStampedUUIDModel):
    """
    A model describing the structure of a message.
    """

    class Delivery(models.TextChoices):
        TO = "to", _("To")
        CC = "cc", _("Cc")
        BCC = "bcc", _("Bcc")

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages", related_query_name="sent_message", blank=True)
    recipients = models.ManyToManyField(User, related_name="messages", through="MessageRecipient", blank=True)
    distribution_lists = models.ManyToManyField(DistributionList, related_name="messages", through="MessageDistribution", blank=True)
    subject = models.CharField(_("subject"), max_length=150)
    body = models.TextField(_("body"))
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="messages", blank=True, null=True)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, related_name="replies", blank=True, null=True, verbose_name=_("replying to"))
    date_sent = models.DateTimeField(_("sent"), blank=True, null=True)

    objects = MessageManager()

    class Meta:
        get_latest_by = "last_updated"
        ordering = ["-last_updated"]
        verbose_name = _("Message")
        verbose_name_plural = _("Messages")

    def __str__(self):
        return self.subject

    def save(self, **kwargs):
        if not self.thread:
            self.thread = self.parent.thread if self.parent else Thread.objects.create()
        super().save(**kwargs)

    def send(self):
        # ensure all mailboxes are expanded
        self.expand_distribution_lists()
        self.date_sent = timezone.now()

        # Format the message:
        site = Site.objects.get_current()
        subject = render_to_string('mail/message_subject.txt', {"site": site, "message": self}).strip()

        distros = self.distribution_lists.filter(addresses__is_default=True).values_list("message_distribution_list__delivery", "addresses__address", "name").order_by()
        recipients = self.recipients.filter(message_recipient__from_distro=False).values_list("message_recipient__delivery", "_short_name", "email").order_by()
        all_recipients = recipients.union(distros)

        to_field = ["%s <%s>" % (n, e) for d, n, e in all_recipients if d == Message.Delivery.TO]
        cc_field = ["%s <%s>" % (n, e) for d, n, e in all_recipients if d == Message.Delivery.CC]
        bcc_field = ["%s <%s>" % (n, e) for d, n, e in all_recipients if d == Message.Delivery.BCC]

        # open a connection to the mailserver
        with mail.get_connection() as connection:

            for recipient in self.recipients.all():

                # Personalize the email for each recipient.
                context = {"site": site, "message": self, "recipient": recipient}
                plaintext = render_to_string("mail/message_body.txt", context)
                richtext = render_to_string("mail/message_body.html", context)

                msg = ListEmail(
                    subject=subject,
                    body=plaintext,
                    to=to_field,
                    cc=cc_field,
                    bcc=bcc_field,
                    rcpt_to=[recipient.email],
                    connection=connection,
                )
                msg.attach_alternative(richtext, "text/html")
                for attachment in self.attachments.all():
                    msg.attach_file(attachment.filename.path)

                print("Sending message to %s" % msg.rcpt_to)
                msg.send()

        # Mark the message as sent
        self.save()

    @admin.display(boolean=True, description=_("sent"))
    def sent(self):
        return bool(self.date_sent)

    def expand_distribution_lists(self):
        # Create unique MessageRecipient instances for each DistributionList in the message.
        for delivery, label in Message.Delivery.choices:
            for distribution_list in self.distribution_lists.filter(message_distribution_list__delivery=delivery):
                for member in distribution_list.get_members():
                    try:
                        with transaction.atomic():
                            MessageRecipient.objects.create(message=self, recipient=member, delivery=delivery, from_distro=True)
                    except IntegrityError:
                        # The member is already a recipient of the message,
                        # check that we have the delivery level correct.
                        recipient = MessageRecipient.objects.get(message=self, recipient=member)
                        if recipient.delivery < delivery:
                            recipient.delivery = delivery
                            recipient.save()


class Attachment(models.Model):
    """
    A simple model to track message attachments.
    """

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="attachments")
    filename = models.FileField(_("file"), upload_to=get_upload_to, help_text=_("attachments should be under 5mb."))

    class Meta:
        verbose_name = _("Attachment")
        verbose_name_plural = _("Attachments")

    def __str__(self):
        return Path(self.filename.name).name


class MessageRecipient(models.Model):
    """
    An intermediate through model to track an individual member's copy of a message.
    """
    delivery = models.CharField("", max_length=3, choices=Message.Delivery.choices, default=Message.Delivery.TO)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_query_name="message_recipient")
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_query_name="message_recipient")

    from_distro = models.BooleanField(_("distribution list"), default=False, help_text=_("Specify whether this recipient was included in the message directly or as part of a larger distribution list."))
    date_received = models.DateTimeField(_("received"), auto_now_add=True)
    date_read = models.DateTimeField(_("read"), blank=True, null=True)
    date_archived = models.DateTimeField(_("archived"), blank=True, null=True)
    date_deleted = models.DateTimeField(_("deleted"), blank=True, null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("message", "recipient"), name="unique_message_per_recipient")]
        verbose_name = _("Message Recipient")
        verbose_name_plural = _("Message Recipients")

    def __str__(self):
        return self.recipient.__str__()

    @admin.display(boolean=True, description=_("read"))
    def is_read(self):
        return bool(self.date_read)

    def mark_read(self):
        self.date_read = timezone.now()
        self.save()

    def mark_unread(self):
        self.date_read = None
        self.save()

    def mark_archived(self):
        self.date_archived = timezone.now()
        self.date_deleted = None
        self.save()

    def mark_unarchived(self):
        self.date_archived = None
        self.date_deleted = None
        self.save()

    def mark_deleted(self):
        self.date_deleted = timezone.now()
        self.date_archived = None
        self.save()

    def mark_undeleted(self):
        self.date_deleted = None
        self.date_archived = None
        self.save()


class MessageDistribution(models.Model):
    """
    An intermediate through model to track delivery of bulk messages.
    """

    delivery = models.CharField("", max_length=3, choices=Message.Delivery.choices, default=Message.Delivery.TO)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_query_name="message_distribution_list")
    distribution_list = models.ForeignKey(DistributionList, on_delete=models.CASCADE, related_query_name="message_distribution_list")

    class Meta:
        constraints = [models.UniqueConstraint(fields=("message", "distribution_list"), name=_("unique_message_per_distribution_list"))]
        verbose_name = _("Message Distribution List")
        verbose_name_plural = _("Message Distribution Lists")

    def __str__(self):
        return self.distribution_list.__str__()


class Settings(TimeStampedModel):
    """
    A simple model to track settings for email lists
    """

    list_name = models.CharField(_("list name"), max_length=100, blank=True)
    list_description = models.CharField(_("list description"), max_length=150, blank=True)
    list_subject = models.CharField(_("subject line prefix"), max_length=20, blank=True)
    list_id = models.CharField(_("list ID"), max_length=100, blank=True)
    list_help = models.CharField(_("help "), max_length=100, blank=True)
    list_from = models.EmailField(_("from"), max_length=100, blank=True)

    class Meta:
        verbose_name = _("Settings")
        verbose_name_plural = _("Settings")

    def __str__(self):
        return self.list_name

    def save(self, *args, **kwargs):
        if self.__class__.objects.count():
            self.pk = self.__class__.objects.first().pk
        super().save(*args, **kwargs)


class ListEmail(EmailMultiAlternatives):

    def __init__(self, subject="", body="", rcpt_to=None, from_email=None, **kwargs):
        super().__init__(subject, body, **kwargs)
        try:
            list_settings = Settings.objects.first()
            list_from_email = list_settings.list_from or None
        except Settings.DoesNotExist:
            # No settings have been stored, there's nothing more we can do here.
            pass

        if rcpt_to:
            if isinstance(rcpt_to, str):
                raise TypeError('"rcpt_to" argument must be a list or tuple')
            self.rcpt_to = list(rcpt_to)
        else:
            self.rcpt_to = []
        self.from_email = from_email or list_from_email or settings.DEFAULT_FROM_EMAIL


    def message(self):
        msg = super().message()

        # Get the list settings from the database
        try:
            settings = Settings.objects.first()
        except Settings.DoesNotExist:
            # No settings have been stored, there's nothing more we can do here.
            return msg
        site = Site.objects.get_current()

        msg['Subject'] = "[%s] %s" % (settings.list_subject, self.subject) if settings.list_subject else self.subject

        # Email header names are case-insensitive (RFC 2045), so we have to
        # accommodate that when doing comparisons.
        header_names = [key.lower() for key in self.extra_headers]
        if 'list-id' not in header_names and settings.list_id != "":
            msg['List-ID'] = settings.list_id
        if 'list-help' not in header_names and settings.list_help != "":
            msg['List-Help'] = settings.list_help
        if 'list-unsubscribe' not in header_names:
            msg['List-Unsubscribe'] = "<https://%s%s>" % (site.domain, reverse("membership:my-family"))

        return msg

    def recipients(self):
        """
        Returns a filtered list of recipients for use in the SMTP envelope.
        """
        return self.rcpt_to
