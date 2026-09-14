import logging

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
            "Identifies this page in URLs and templates. Inline CMS entries must start with 'cms-'. "
            "If omitted, the prefix will be added when the page is saved."
        ),
    )

    class NavPlacement(models.IntegerChoices):
        PACK_INFO = 1, _("Pack Info dropdown")
        PINNED = 2, _("Pinned top-level link")
        ABOUT = 3, _("About dropdown")
        NCC = 6, _("NCC dropdown")
        INLINE_CMS = 7, _("Inline (CMS)")

    # Placements that produce ordinary navigation links. NCC is populated
    # separately, while inline CMS entries are embedded in other templates.
    NAV_GROUP_PLACEMENTS = (NavPlacement.PACK_INFO, NavPlacement.PINNED, NavPlacement.ABOUT)

    nav_placement = models.PositiveSmallIntegerField(
        _("navigation placement"),
        choices=NavPlacement.choices,
        blank=True,
        null=True,
        default=None,
        help_text=_(
            "Where this page should be used. Leave blank to keep it out of "
            "the navigation bar. Inline (CMS) entries are inserted into other "
            "pages by slug and cannot be opened as standalone pages."
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
            models.CheckConstraint(
                condition=(
                    # NavPlacement.INLINE_CMS: nested classes cannot see Page's namespace here.
                    ~models.Q(nav_placement=7)
                    | (models.Q(slug__isnull=False) & models.Q(slug__startswith="cms-"))
                ),
                name="inline_cms_slug_prefix",
            ),
        ]
        indexes = [models.Index(fields=["title"])]
        ordering = ("order", "title")
        verbose_name = _("Page")
        verbose_name_plural = _("Pages")

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        if self.nav_placement == self.NavPlacement.INLINE_CMS:
            return reverse("admin:pages_page_change", args=(self.pk,))
        return reverse("pages:detail", kwargs={"slug": self.slug})

    def clean(self):
        super().clean()
        if not self.slug:
            self.slug = slugify(self.title)
            logger.warning(
                _("%(page)s does not include a slug. Setting slug to %(slug)s") % {"page": self, "slug": self.slug}
            )
        if self.nav_placement == self.NavPlacement.INLINE_CMS and not self.slug.startswith("cms-"):
            self.slug = f"cms-{self.slug}"


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
