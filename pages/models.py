from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


from ckeditor.fields import RichTextField


class Category(models.Model):
    name = models.CharField(max_length=32)

    class Meta:
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')

    def __str__(self):
        return self.name


class Page(models.Model):
    title = models.CharField(max_length=128)
    body = RichTextField(blank=True)

    created_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    published_on = models.DateTimeField(default=timezone.now, blank=True, null=True)

    class Meta:
        get_latest_by = 'published_on'
        verbose_name = _('Page')
        verbose_name_plural = _('Pages')

    def __str__(self):
        return self.title


class DynamicPage(Page):
    categories = models.ManyToManyField(Category, related_name='dynamic_page', blank=True)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name = _('Dynamic Page')
        verbose_name_plural = _('Dynamic Pages')

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('dynamic_page', kwargs={'slug': self.slug})


class StaticPage(Page):
    PAGE_CHOICES = (
        ('HOME', 'Home Page'),
        ('ABOUT', 'About Us Page'),
        ('HISTORY', 'History Page'),
    )
    page = models.CharField(max_length=8, choices=PAGE_CHOICES)

    class Meta:
        verbose_name = _('Static Page')
        verbose_name_plural = _('Static Pages')

    def __str__(self):
        return self.get_page_display()


class Attachment(models.Model):
    file = models.FileField(upload_to='pages')
    page = models.ForeignKey(Page, on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('Attachment')
        verbose_name_plural = _('Attachments')

    def __str__(self):
        return self.file.name
