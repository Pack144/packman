from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ckeditor.fields import RichTextField


class Category(models.Model):
    name = models.CharField(max_length=32)

    class Meta:
        ordering = ['name']
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')

    def __str__(self):
        return self.name


class Page(models.Model):
    title = models.CharField(_('Title'), max_length=128)
    private_content = RichTextField(_('Private content'), blank=True, help_text=(
        "Private content will only be viewable to active members."
    ))
    public_content = RichTextField(_('Publicly available content'), blank=True, help_text=_(
        "Public content is viewable by anyone on the website."
    ))
    # attachments = models.ManyToManyField(_('Attachments'), 'documents.Document', related_name='page', blank=True)

    created_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    published_on = models.DateTimeField(default=timezone.now, blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=['title'])]
        get_latest_by = 'published_on'
        verbose_name = _('Page')
        verbose_name_plural = _('Pages')

    def __str__(self):
        return self.title


class DynamicPage(Page):
    categories = models.ManyToManyField(Category, related_name='dynamic_page', blank=True)
    include_in_nav = models.BooleanField(_('Include in navigation'), default=False, help_text=_(
        "Checking this option will add this page to the site's menu bar."
    ))
    parent_page = models.ForeignKey(Page, on_delete=models.SET_NULL, related_name='child_page', blank=True, null=True, help_text=_(
        "Is this page part of another?"
    ))
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name = _('Dynamic Page')
        verbose_name_plural = _('Dynamic Pages')

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('dynamic_page', kwargs={'slug': self.slug})


class StaticPage(Page):
    HOME = 'HOME'
    ABOUT = 'ABOUT'
    HISTORY = 'HISTORY'
    SIGNUP = 'SIGNUP'
    PAGE_CHOICES = (
        (HOME, _('Home Page')),
        (ABOUT, _('About Us Page')),
        (HISTORY, _('History Page')),
        (SIGNUP, _('Join Us')),
    )
    page = models.CharField(max_length=8, choices=PAGE_CHOICES)

    class Meta:
        verbose_name = _('Static Page')
        verbose_name_plural = _('Static Pages')

    def __str__(self):
        return self.get_page_display()
