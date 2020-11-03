from django.db import models
from django.utils.translation import gettext_lazy as _

from tinymce.models import HTMLField


# class Message(models.Model):
# #    to_field = models.ManyToManyField('dens.Den')
#     from_field = models.CharField(max_length=128)
#     subject = models.CharField(max_length=64, blank=True)
#     body = HTMLField(blank=True)
#
#     def __str__(self):
#         return self.subject
#
#     def get_to_addresses(self):
#         pass
#
#     @property
#     def plain_text_body(self):
#         pass


# class GroupMailbox(models.Model):
#     """ A model to store messages for groups of members """
#     name = models.CharField(max_length=64)
#     email = models.EmailField()
#
#     class Meta:
#         ordering = ('name', )
#         verbose_name = _("Group Mailbox")
#         verbose_name_plural = _("Group Mailboxes")
#
#     def __str__(self):
#         return self.name
