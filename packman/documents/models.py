from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from packman.core.models import TimeStampedUUIDModel


def document_upload_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/documents/category_slug/<filename>
    return f"documents/{slugify(instance.category)}/{filename}"


class Category(TimeStampedUUIDModel):
    name = models.CharField(
        max_length=32,
    )

    class Meta:
        ordering = ['name']
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def __str__(self):
        return self.name


class Document(TimeStampedUUIDModel):
    name = models.CharField(
        max_length=128,
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text=_("Brief description of what the document is."),
    )
    file = models.FileField(
        upload_to=document_upload_path,
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='documents',
    )
    committee = models.ForeignKey(
        'committees.Committee',
        on_delete=models.SET_NULL,
        related_name='documents',
        blank=True,
        null=True,
    )
    display_in_repository = models.BooleanField(
        default=True,
        help_text=_("Make this document visible in the Document Repository"),
    )

    class Meta:
        ordering = ['category', 'name', ]
        verbose_name = _("Document")
        verbose_name_plural = _("Documents")

    def __str__(self):
        return self.name

    def get_file_type(self):
        extension = self.file.file.split('.')[-1]
        if extension in ('txt', 'rtf'):
            return _("Text Document")
        elif extension in ('pdf', ):
            return _("PDF")
        elif extension in ('doc', 'docx'):
            return _("Microsoft Word Document")
        elif extension in ('xls', 'xlsx'):
            return _("Microsoft Excel Spreadsheet")
        elif extension in ('ppt', 'pptx', 'pps', 'ppsx'):
            return _("Microsoft Powerpoint Presentation")
        elif extension in ('jpg', 'jpeg', 'gif', 'png', 'tiff', 'bmp'):
            return _("Image")
        elif extension in ('mp4', 'm4v', 'ogv', 'webm', 'mov'):
            return _("Video")
        elif extension in ('wav', 'wave', 'mp3', 'ogg', 'oga', 'ogm', 'spx', 'opus'):
            return _("Audio")
        elif extension in ('zip', ):
            return _("Compressed Archive")
