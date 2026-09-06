from django import template

from packman.compliance import summaries

register = template.Library()


@register.simple_tag
def membership_standing(member):
    """
    One member's Scouting America registration: standing, ID and expiration.

    The requirements card is included from the membership detail pages, which
    know nothing about compliance and pass only `member`. Reading the rule here
    keeps every caller in step with the family page rather than asking each view
    to put the same thing in its context.

    A missing member reads as nothing rather than raising, so a template that
    includes the card without one renders empty the way it always has. An
    unresolved template variable arrives as string_if_invalid, not None, so
    this tests for truth rather than identity.
    """
    if not member:
        return None
    return summaries.membership_standing(member)
