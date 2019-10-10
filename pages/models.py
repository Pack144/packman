from django.db import models
from django.utils import timezone


class StaticPage(models.Model):
    PAGE_CHOICES = (
        ('HOME', 'Home Page'),
        ('ABOUT', 'About Us Page'),
        ('HISTORY', 'History Page'),
    )
    body = models.TextField(blank=True, null=True)
    page = models.CharField(max_length=8, choices=PAGE_CHOICES)
    created_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    published_on = models.DateTimeField(default=timezone.now, blank=True, null=True)

    def __str__(self):
        return '{} ({})'.format(self.get_page_display(), self.published_on)

    class Meta:
        get_latest_by = 'published_on'
