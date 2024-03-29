from django.contrib.auth.models import UserManager
from django.db import models
from django.db.models import Case, Count, Q, Value, When
from django.db.models.functions import Coalesce, Concat

from packman.calendars.models import PackYear
from packman.dens.models import Rank


class FamilyQuerySet(models.QuerySet):
    def active(self):
        return self.filter(
            children__den_memberships__year_assigned=PackYear.objects.current(),
            children__status=self.model.children.rel.related_model.ACTIVE,
        )

    def in_den(self, den_list):
        return self.active().filter(
            children__den_memberships__year_assigned=PackYear.objects.current(),
            children__den_memberships__den__number__in=den_list,
        )

    def count_active_scouts(self):
        return self.annotate(
            active_cub_count=Count(Q(children__in=self.model.children.rel.related_model.objects.active()))
        )


class FamilyManager(models.Manager):
    def get_queryset(self):
        qs = FamilyQuerySet(self.model, using=self._db)
        return qs.prefetch_related("adults", "children")

    def active(self):
        return self.get_queryset().active()

    def in_den(self, den_list):
        return self.get_queryset().in_den(den_list=den_list)

    def count_active_scouts(self):
        return self.get_queryset().count_active_scouts()


class MemberQuerySet(models.QuerySet):
    def active(self):
        return self.filter(family__in=self.model.family.field.related_model.objects.active())

    def in_den(self, den_list):
        return self.active().filter(family__in=self.model.family.field.related_model.objects.in_den(den_list))

    def in_committee(self, committee_list):
        return self.active().filter(committees__in=committee_list, committees__year=PackYear.objects.current())


class MemberManager(UserManager):
    def get_queryset(self):
        return MemberQuerySet(model=self.model, using=self._db).annotate(
            _short_name=Coalesce(
                Case(
                    When(nickname__exact="", then=None),
                    default="nickname",
                    outputfield=models.CharField(),
                ),
                "first_name",
            ),
            _full_name=Concat("_short_name", Value(" "), "last_name"),
        )

    def get_by_natural_key(self, username):
        case_insensitive_username_field = f"{self.model.USERNAME_FIELD}__iexact"
        return self.get(**{case_insensitive_username_field: username})

    def active(self):
        return self.get_queryset().active()

    def in_den(self, den_list):
        return self.get_queryset().in_den(den_list)

    def in_committee(self, committee_list):
        return self.get_queryset().in_committee(committee_list)

    def _create_user(self, email, password, **extra_fields):
        """
        Custom user model manager where email is the unique identifiers for
        authentication instead of usernames. All other code is shamelessly
        ripped off directly from Django's own UserManager
        https://github.com/django/django/blob/master/django/contrib/auth/models.py
        """
        if not email:
            raise ValueError("Users must have an email address")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault("_is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault("_is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("_is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class ScoutQuerySet(models.QuerySet):
    def active(self):
        return self.filter(
            den_memberships__year_assigned=PackYear.objects.current(),
            status=self.model.ACTIVE,
        )

    def lions(self):
        return self.active().filter(den_memberships__den__rank__rank=Rank.RankChoices.LION)

    def tigers(self):
        return self.active().filter(den_memberships__den__rank__rank=Rank.RankChoices.TIGER)

    def wolves(self):
        return self.active().filter(den_memberships__den__rank__rank=Rank.RankChoices.WOLF)

    def bears(self):
        return self.active().filter(den_memberships__den__rank__rank=Rank.RankChoices.BEAR)

    def jr_webes(self):
        return self.active().filter(den_memberships__den__rank__rank=Rank.RankChoices.JR_WEBE)

    def sr_webes(self):
        return self.active().filter(den_memberships__den__rank__rank=Rank.RankChoices.SR_WEBE)

    def arrows_of_light(self):
        return self.active().filter(den_memberships__den__rank__rank=Rank.RankChoices.ARROW)

    def animal_ranks(self):
        return self.active().filter(den_memberships__den__rank__rank__lte=Rank.RankChoices.BEAR)

    def webelo_ranks(self):
        return self.active().filter(den_memberships__den__rank__rank__gte=Rank.RankChoices.JR_WEBE)


class ScoutManager(models.Manager):
    def get_queryset(self):
        return ScoutQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def lions(self):
        return self.get_queryset().lions()

    def tigers(self):
        return self.get_queryset().tigers()

    def wolves(self):
        return self.get_queryset().wolves()

    def bears(self):
        return self.get_queryset().bears()

    def jr_webes(self):
        return self.get_queryset().jr_webes()

    def sr_webes(self):
        return self.get_queryset().sr_webes()

    def arrows_of_lights(self):
        return self.get_queryset().arrows_of_light()

    def animal_ranks(self):
        return self.get_queryset().animal_ranks()

    def webelo_ranks(self):
        return self.get_queryset().webelo_ranks()
