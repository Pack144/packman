from django.db import models
from django.utils.translation import ugettext_lazy as _


class Category(models.Model):
    name = models.CharField(max_length=32)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')


class Document(models.Model):
    name = models.CharField(max_length=128)
    description = models.TextField(help_text=_('Brief description of what the document is.'), blank=True, null=True)
    file = models.FileField(upload_to='documents')
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    date_added = models.DateField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['category', 'name', ]
        verbose_name = _('Document')
        verbose_name_plural = _('Documents')
