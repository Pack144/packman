import logging

from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from tinymce.models import HTMLField

from packman.core.models import TimeStampedModel, TimeStampedUUIDModel

from .managers import ContentBlockManager, PageManager

logger = logging.getLogger(__name__)


class Image(TimeStampedModel):
    """
    Basic image model used to store image files that can be attached to a webpage
    """

    image = models.ImageField(_("image"), upload_to="pages")

    class Meta:
        verbose_name = _("image")
        verbose_name_plural = _("images")

    def __str__(self):
        return self.filename()

    def filename(self):
        return self.image.name.split("/")[1]


class Page(TimeStampedUUIDModel):
    """
    Base model used to define a web page. Used by Dynamic and Static pages.
    """

    HOME = "HOME"
    ABOUT = "ABOUT"
    HISTORY = "HISTORY"
    SIGNUP = "SIGNUP"
    PAGE_CHOICES = (
        (HOME, _("Home")),
        (ABOUT, _("About Us")),
        (HISTORY, _("History")),
        (SIGNUP, _("Join Us")),
    )
    title = models.CharField(
        _("title"),
        max_length=64,
        help_text=_(
            "The title of this webpage. Will be shown as the top level header and, if added to the site navigation bar, as the link name."
        ),
    )

    page = models.CharField(
        max_length=8,
        choices=PAGE_CHOICES,
        unique=True,
        blank=True,
        null=True,
        help_text=_("If this is going to be one of the standard pages, specify which one here."),
    )
    slug = models.SlugField(
        _("slug"),
        unique=True,
        blank=True,
        null=True,
        help_text=_(
            "A slug is the part of a URL which identifies a particular page on a website in an easy to read form. In other words, it’s the part of the URL that explains the page’s content. For this article, for example, the URL is https://example.com/slug, and the slug simply is ‘slug’."
        ),
    )
    include_in_nav = models.BooleanField(
        _("Include in navigation"),
        default=False,
        help_text=_(
            "Checking this option will add this page to the site's navigation bar. "
            "Not used for standard pages (e.g. Home, About, Sign-up, etc.) since they will always be included."
        ),
    )

    objects = PageManager()

    class Meta:
        indexes = [models.Index(fields=["title"])]
        verbose_name = _("Page")
        verbose_name_plural = _("Pages")

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        if self.page == self.HOME:
            return reverse("pages:home")
        elif self.page == self.ABOUT:
            return reverse("pages:about")
        elif self.page == self.HISTORY:
            return reverse("pages:history")
        elif self.page == self.SIGNUP:
            return reverse("pages:signup")
        else:
            return reverse("pages:detail", kwargs={"slug": self.slug})

    def clean(self):
        super().clean()
        if self.page and self.include_in_nav:
            self.include_in_nav = False
            logger.warning(_("Default pages will always appear in navbar. Setting is redundant"))
        if not self.page and not self.slug:
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

    PRIVATE = "S"
    PUBLIC = "P"
    ANONYMOUS = "A"
    VISIBILITY_CHOICES = [
        (PRIVATE, _("Members Only")),
        (PUBLIC, _("Everyone")),
        (ANONYMOUS, _("Anonymous / Guests")),
    ]

    heading = models.CharField(
        _("section heading"),
        max_length=256,
        blank=True,
        default="",
    )
    visibility = models.CharField(
        _("permissions"),
        max_length=1,
        choices=VISIBILITY_CHOICES,
        default=PRIVATE,
        help_text=(
            "'Members Only' content will only be viewable to active members or "
            "contributors. Content marked as 'Everyone' will be viewable by anyone on the "
            "website, including applicants, alumni, and anonymous visitors. "
            "Anonymous content will be displayed only if no user is logged-in."
        ),
    )
    body = HTMLField(_("section body"))
    images = models.ManyToManyField(Image, related_name="contentblocks", blank=True)
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

    objects = ContentBlockManager()

    class Meta:
        indexes = [models.Index(fields=["heading", "published_on"])]
        ordering = ["-published_on"]
        verbose_name = _("Content Block")
        verbose_name_plural = _("Content Blocks")

    def __str__(self):
        if self.heading:
            return self.heading
        else:
            return f"{strip_tags(self.body)[:25]}..."
