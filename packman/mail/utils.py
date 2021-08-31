from .models import Message


def get_mailbox_counts(user, viewing_mailbox=None):
    """
    Given a user, return the message counts for all standard folders
    """
    counts = {
        "inbox": {
            "total": Message.objects.in_inbox(recipient=user).count(),
            "unread": Message.objects.in_inbox(recipient=user).unread(user).count(),
        },
        "drafts": {
            "total": Message.objects.drafts(author=user).count(),
        },
        "sent": {
            "total": Message.objects.sent(author=user).count(),
        },
        "archives": {
            "total": Message.objects.archived(recipient=user).count(),
            "unread": Message.objects.archived(recipient=user).unread(user).count(),
        },
        "trash": {
            "total": Message.objects.deleted(recipient=user).count(),
            "unread": Message.objects.deleted(recipient=user).unread(user).count(),
        },
    }

    if viewing_mailbox:
        counts["current"] = counts[viewing_mailbox]

    return counts
