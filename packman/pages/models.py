import logging

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from tinymce.models import HTMLField

from packman.core.models import TimeStampedUUIDModel

from .managers import ContentBlockManager, PageManager

logger = logging.getLogger(__name__)


class Page(TimeStampedUUIDModel):
    """
    Base model used to define a web page. Used by Dynamic and Static pages.
    """

    title = models.CharField(
        _("title"),
        max_length=64,
        help_text=_(
            "The title of this webpage. Will be shown as the top level header "
            "and, if added to the site navigation bar, as the link name."
        ),
    )

    slug = models.SlugField(
        _("slug"),
        unique=True,
        blank=True,
        null=True,
        help_text=_(
            "A slug is the part of a URL which identifies a particular page "
            "on a website in an easy to read form. In other words, it’s the "
            "part of the URL that explains the page’s content. For this "
            "article, for example, the URL is https://example.com/slug, and "
            "the slug simply is ‘slug’."
        ),
    )

    class NavPlacement(models.IntegerChoices):
        PACK_INFO = 1, _("Pack Info dropdown")
        PINNED = 2, _("Pinned top-level link")
        ABOUT = 3, _("About dropdown")
        HOME = 4, _("The home page")
        SIGNUP = 5, _("The join us / sign-up page")
        NCC = 6, _("NCC dropdown")

    # Placements a page picks to appear somewhere in the nav dropdowns/links.
    # HOME, SIGNUP, and NCC are not part of this: HOME/SIGNUP each mark a
    # single fixed page (the home page, the sign-up page); NCC marks any
    # number of pages to show inside the NCC dropdown. All three are looked
    # up individually rather than shown as regular nav links.
    NAV_GROUP_PLACEMENTS = (NavPlacement.PACK_INFO, NavPlacement.PINNED, NavPlacement.ABOUT)

    nav_placement = models.PositiveSmallIntegerField(
        _("navigation placement"),
        choices=NavPlacement.choices,
        blank=True,
        null=True,
        default=None,
        help_text=_(
            "Where this page should appear in the site's navigation bar, if "
            "at all. Leave blank to keep this page out of the navigation bar "
            "entirely. 'The home page' and 'The join us / sign-up page' are "
            "special: only one page may hold each, and it will be used in "
            "place of the site's default one."
        ),
    )
    order = models.PositiveIntegerField(
        _("order"),
        default=0,
        db_index=True,
        help_text=_(
            "Controls the order pages are listed, both in the admin and "
            "within whichever navigation group they are placed in."
        ),
    )

    objects = PageManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["nav_placement"],
                # NavPlacement.HOME: nested classes can't see Page's namespace here.
                condition=models.Q(nav_placement=4),
                name="unique_home_page",
            ),
            models.UniqueConstraint(
                fields=["nav_placement"],
                # NavPlacement.SIGNUP: nested classes can't see Page's namespace here.
                condition=models.Q(nav_placement=5),
                name="unique_signup_page",
            ),
        ]
        indexes = [models.Index(fields=["title"])]
        ordering = ("order", "title")
        verbose_name = _("Page")
        verbose_name_plural = _("Pages")

    def __str__(self):
        return self.title

    @property
    def is_standard(self):
        """Whether this page fills one of the site's fixed roles (home / sign-up)."""
        return self.nav_placement in (self.NavPlacement.HOME, self.NavPlacement.SIGNUP)

    def get_absolute_url(self):
        if self.nav_placement == self.NavPlacement.HOME:
            return reverse("pages:home")
        elif self.nav_placement == self.NavPlacement.SIGNUP:
            return reverse("pages:signup")
        else:
            return reverse("pages:detail", kwargs={"slug": self.slug})

    def clean(self):
        super().clean()
        if self.is_standard:
            already_taken = Page.objects.exclude(pk=self.pk).filter(nav_placement=self.nav_placement).exists()
            if already_taken:
                raise ValidationError(
                    _("Another page is already set as %(placement)s. Change that page first.")
                    % {"placement": self.get_nav_placement_display()}
                )
        if not self.slug:
            self.slug = slugify(self.title)
            logger.warning(
                _("%(page)s does not include a slug. Setting slug to %(slug)s") % {"page": self, "slug": self.slug}
            )


class ContentBlock(TimeStampedUUIDModel):
    """
    Pages can contain any number of content blocks. Each block has its own
    visibility, allowing for different content to be displayed based on whether
    a user is logged in and has permission.
    """

    class Visibility(models.TextChoices):
        PRIVATE = "S", _("Members Only")
        PUBLIC = "P", _("Everyone")
        ANONYMOUS = "A", _("Anonymous / Guests")

    heading = models.CharField(
        _("section heading"),
        max_length=256,
        blank=True,
    )
    bookmark = models.SlugField(
        _("bookmark"),
        blank=True,
        null=True,
        help_text=_("Bookmarks can used to allow readers to jump to specific parts of a webpage."),
    )
    visibility = models.CharField(
        _("permissions"),
        max_length=1,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
        help_text=(
            "'Members Only' content will only be viewable to active members "
            "or contributors. Content marked as 'Everyone' will be viewable "
            "by anyone on the website, including applicants, alumni, and "
            "anonymous visitors. Anonymous content will be displayed only if "
            "no user is logged-in."
        ),
    )
    body = HTMLField(_("section body"))
    page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name="content_blocks",
    )

    published_on = models.DateTimeField(
        default=timezone.now,
        blank=True,
        null=True,
    )
    order = models.PositiveIntegerField(_("order"), default=0, db_index=True)

    objects = ContentBlockManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("page", "bookmark"), name="unique_bookmark_for_page"),
        ]
        indexes = [models.Index(fields=["heading", "published_on"])]
        ordering = ("order", "page")
        verbose_name = _("Content Block")
        verbose_name_plural = _("Content Blocks")

    def __str__(self):
        if self.heading:
            return self.heading
        else:
            return f"{strip_tags(self.body)[:25]}..."
