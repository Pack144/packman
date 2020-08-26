from django.db import models


class ContentQuerySet(models.QuerySet):
    def anonymous(self):
        return self.filter(
            visibility__exact=self.model.ANONYMOUS,
        )

    def authenticated(self):
        return self.filter(
            visibility__exact=self.model.PUBLIC,
        )

    def public(self):
        return self.filter(
            visibility__lte=self.model.PUBLIC,
        )

    def private(self):
        return self.filter(
            visibility__gte=self.model.PUBLIC,
        )


class ContentManager(models.Manager):
    def get_queryset(self):
        return ContentQuerySet(self.model, using=self._db)

    def visible(self, user):
        if user.is_anonymous:
            return self.get_queryset().public()
        elif user.active():
            return self.get_queryset().private()
        else:
            return self.get_queryset().authenticated()
