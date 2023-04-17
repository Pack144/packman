from django.core.exceptions import SuspiciousOperation


class SpamDetected(SuspiciousOperation):
    """The input detected probable unwanted/unsolicited data, a.k.a. SPAM."""

    pass
