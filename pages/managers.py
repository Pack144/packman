from django.db import models


class ContentBlockQuerySet(models.QuerySet):
    def anonymous(self):
        return self.filter(visibility__exact=self.model.ANONYMOUS)

    def authenticated(self):
        return self.filter(visibility__exact=self.model.PUBLIC)

    def public(self):
        return self.filter(visibility__lte=self.model.PUBLIC)

    def private(self):
        return self.filter(visibility__gte=self.model.PUBLIC)


class ContentBlockManager(models.Manager):
    def get_queryset(self):
        return ContentBlockQuerySet(self.model, using=self._db)

    def get_visible(self, user):
        if user.is_anonymous:
            return self.get_queryset().public()
        elif user.active():
            return self.get_queryset().private()
        else:
            return self.get_queryset().authenticated()


class PageQuerySet(models.QuerySet):
    def get_visible_content(self, user):
        return self.prefetch_related(models.Prefetch(
            "content_blocks",
            queryset=self.model.content_blocks.field.model.objects.get_visible(user=user)
        ))


class PageManager(models.Manager):
    def get_queryset(self):
        return PageQuerySet(self.model, using=self._db)

    def get_visible_content(self, user):
        return self.get_queryset().get_visible_content(user=user)
