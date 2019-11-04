from django.db import models
from django.utils import timezone

from ckeditor_uploader.fields import RichTextUploadingField


class Page(models.Model):
    title = models.CharField(max_length=128)
    body = RichTextUploadingField(blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    published_on = models.DateTimeField(default=timezone.now, blank=True, null=True)

    def __str__(self):
        return self.title

    class Meta:
        get_latest_by = 'published_on'


class StaticPage(Page):
    PAGE_CHOICES = (
        ('HOME', 'Home Page'),
        ('ABOUT', 'About Us Page'),
        ('HISTORY', 'History Page'),
    )
    page = models.CharField(max_length=8, choices=PAGE_CHOICES)

    def __str__(self):
        return self.get_page_display()
