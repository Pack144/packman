from pathlib import Path

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core import mail
from django.core.validators import URLValidator
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

    is_all = models.BooleanField(
        _("all members"),
        default=False,
        help_text=_(
            "Messages sent to this distribution list should be delivered to "
            "all active members of the Pack."
        ),
    )
    dens = models.ManyToManyField(
        Den,
        related_name="distribution_list",
        related_query_name="distribution_list",
        blank=True
    )
    committees = models.ManyToManyField(
        Committee,
        related_name="distribution_list",
        related_query_name="distribution_list",
        blank=True
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("Distribution List")
        verbose_name_plural = _("Distribution Lists")

    def __str__(self):
        return self.name

    def get_default_email(self):
        return self.addresses.get(is_default=True)

    def get_members(self):
        if self.is_all:
            return User.objects.active()

        return (
            User.objects.active()
            .filter(
                Q(committee_membership__year=PackYear.objects.current(), committee__in=self.committees.all())
                | Q(family__in=Family.objects.in_den(self.dens.all()))
            )
            .distinct()
        )


class EmailAddress(TimeStampedModel):
    """
    A simple model to track an email address.
    """

    distribution_list = models.ForeignKey(DistributionList, on_delete=models.CASCADE, related_name="addresses")
    address = models.EmailField(
        _("email address"),
        unique=True,
        error_messages={"unique": _("A distribution list with this email address already exists.")},
    )
    is_default = models.BooleanField(
        _("default"),
        default=False,
        help_text=_("Indicates whether this address should be used as the default from address."),
    )

    class Meta:
        ordering = ("-is_default", "address")
        verbose_name = _("Email Address")
        verbose_name_plural = _("Email Addresses")

    def __str__(self):
        return self.address

    def save(self, **kwargs):
        # Check to ensure whether one and only one address is default for the distribution list.
        if self.is_default:
            EmailAddress.objects.filter(distribution_list=self.distribution_list, is_default=True).update(
                is_default=False
            )
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
        # BCC = "bcc", _("Bcc")

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_messages",
        related_query_name="sent_message",
        blank=True
    )
    recipients = models.ManyToManyField(User, related_name="messages", through="MessageRecipient", blank=True)
    distribution_lists = models.ManyToManyField(
        DistributionList,
        related_name="messages",
        through="MessageDistribution",
        blank=True
    )
    subject = models.CharField(_("subject"), max_length=150)
    body = models.TextField(_("body"))
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="messages", blank=True, null=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="replies",
        blank=True,
        null=True,
        verbose_name=_("replying to")
    )
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

    def get_absolute_url(self):
        return reverse("mail:detail", kwargs={"pk": self.pk})

    def send(self):
        # ensure all mailboxes are expanded
        self.expand_distribution_lists()
        if not self.recipients.exists():
            raise AttributeError(_("Cannot send an Email with no recipients."))

        site = Site.objects.get_current()

        # open a connection to the mail server
        with mail.get_connection() as connection:

            for recipient in self.recipients.all():
                print("Sending message to %s" % recipient)

                # Personalize the email for each recipient.
                context = {"site": site, "message": self, "recipient": recipient}
                plaintext = render_to_string("mail/message_body.txt", context)
                richtext = render_to_string("mail/message_body.html", context)

                # compose the email
                msg = ListEmail(
                    self.subject,
                    plaintext,
                    to=["%s <%s>" % (recipient.__str__(), recipient.email)],
                    connection=connection,
                    alternatives=[(richtext, "text/html")],
                )

                # add any attachments
                for attachment in self.attachments.all():
                    msg.attach_file(attachment.filename.path)

                sent = msg.send()
                print("%s" % "  success" if sent else "  failed")

        # Mark the message as sent
        self.date_sent = timezone.now()
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
                            MessageRecipient.objects.create(
                                message=self, recipient=member, delivery=delivery, from_distro=True
                            ).distros.add(distribution_list)
                    except IntegrityError:
                        # The member is already a recipient of the message,
                        # check that we have the delivery level correct.
                        recipient = MessageRecipient.objects.get(message=self, recipient=member)
                        recipient.distros.add(distribution_list)
                        if recipient.delivery < delivery:
                            recipient.delivery = delivery
                            recipient.save()

    def mark_read(self, recipient):
        MessageRecipient.objects.get(message=self, recipient=recipient).mark_read()

    def mark_unread(self, recipient):
        MessageRecipient.objects.get(message=self, recipient=recipient).mark_unread()

    def mark_archived(self, recipient):
        MessageRecipient.objects.get(message=self, recipient=recipient).mark_archived()

    def mark_unarchived(self, recipient):
        MessageRecipient.objects.get(message=self, recipient=recipient).mark_unarchived()

    def mark_deleted(self, recipient):
        MessageRecipient.objects.get(message=self, recipient=recipient).mark_deleted()

    def mark_undeleted(self, recipient):
        MessageRecipient.objects.get(message=self, recipient=recipient).mark_undeleted()


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

    from_distro = models.BooleanField(
        _("distribution list"),
        default=False,
        help_text=_(
            "Specify whether this recipient was included in the message "
            "directly or as part of a larger distribution list."
        ),
    )
    distros = models.ManyToManyField(DistributionList)
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
        if not self.date_read:
            self.date_read = timezone.now()
            self.save()

    def mark_unread(self):
        self.date_read = None
        self.save()

    def mark_archived(self):
        if not self.date_archived:
            self.date_archived = timezone.now()
            self.date_deleted = None
            self.save()

    def mark_unarchived(self):
        self.date_archived = None
        self.date_deleted = None
        self.save()

    def mark_deleted(self):
        if not self.date_deleted:
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
    distribution_list = models.ForeignKey(
        DistributionList,
        on_delete=models.CASCADE,
        related_query_name="message_distribution_list"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("message", "distribution_list"), name=_("unique_message_per_distribution_list")
            )
        ]
        verbose_name = _("Message Distribution List")
        verbose_name_plural = _("Message Distribution Lists")

    def __str__(self):
        return self.distribution_list.__str__()


class ListSettings(TimeStampedModel):
    """
    A simple model to track settings for email lists
    """

    list_id = models.CharField(
        _("list ID"),
        max_length=100,
        validators=[URLValidator],
        help_text=_(
            "A List-Id will be included in the header of any email sent from "
            "this application. The List-Id should be unique to the list and "
            "clearly identify your organization (e.g. lists.example.com)."
        ),
    )
    name = models.CharField(
        _("name"),
        max_length=100,
        blank=True,
        help_text=_(
            "An optional descriptive name for emails generated by this "
            "application."
        ),
    )
    from_name = models.CharField(
        _("from name"),
        max_length=40,
        blank=True,
        help_text=_(
            "The name that will be displayed in the From line of emails sent "
            "from this list. If left blank, will default to the from email."
        ),
    )
    from_email = models.EmailField(
        _("from email"),
        blank=True,
        help_text=_(
            "The email address that emails sent from this list will "
            "originate from. If left blank, will default to the site's "
            "DEFAULT_FROM_EMAIL as specified in site settings."
        ),
    )
    subject_prefix = models.CharField(
        _("subject line prefix"),
        max_length=20,
        blank=True,
        help_text=_(
            "If provided, the subject prefix will precede every sent email's "
            "subject in the email subject field."
        ),
    )

    class Meta:
        verbose_name = _("Settings")
        verbose_name_plural = _("Settings")

    def __str__(self):
        return self.list_id

    def save(self, *args, **kwargs):
        if self.__class__.objects.count():
            self.pk = self.__class__.objects.first().pk
        super().save(*args, **kwargs)


class ListEmail(EmailMultiAlternatives):
    def __init__(
        self,
        subject="",
        body="",
        from_email=None,
        to=None,
        bcc=None,
        connection=None,
        attachments=None,
        headers=None,
        alternatives=None,
        cc=None,
        reply_to=None,
    ):

        super().__init__(
            subject,
            body,
            from_email,
            to,
            bcc,
            connection,
            attachments,
            headers,
            alternatives,
            cc,
            reply_to,
        )

        try:
            self.settings = ListSettings.objects.get(pk=1)
        except ListSettings.DoesNotExist:
            # No settings have been stored, there's nothing more we can do here.
            self.settings = ListSettings()

        self.subject = (
            "%s %s" % (self.settings.subject_prefix, self.subject)
            if self.settings.subject_prefix != ""
            else self.subject
        )

        if from_email:
            self.from_email = from_email
        elif self.settings.from_name and self.settings.from_email:
            self.from_email = "%s <%s>" % (self.settings.from_name, self.settings.from_email)
        elif self.settings.from_email:
            self.from_email = "<%s>" % self.settings.from_email
        else:
            self.from_email = settings.DEFAULT_FROM_EMAIL

    def message(self):
        msg = super().message()

        # Get the list settings from the database
        if not self.settings:
            # No settings have been stored, there's nothing more we can do here.
            return msg

        site = Site.objects.get_current()

        # Email header names are case-insensitive (RFC 2045), so we have to
        # accommodate that when doing comparisons.
        header_names = [key.lower() for key in self.extra_headers]

        if "list-id" not in header_names and self.settings.list_id != "":
            if self.settings.name:
                msg["List-Id"] = "<%s> %s" % (self.settings.list_id, self.settings.name)
            else:
                msg["List-Id"] = "<%s>" % self.settings.list_id

        if "list-unsubscribe" not in header_names:
            msg["List-Unsubscribe"] = "<https://%s%s>" % (site.domain, reverse("membership:my-family"))

        return msg