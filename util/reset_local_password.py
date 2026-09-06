#!/usr/bin/env python3
"""
reset_local_password.py — Reset a local user's password.

Called by util/sync_local_data.sh after syncing a beta/production database
backup, so there's a known login for local development — e.g. for Copilot
to use. Reads SYNC_RESET_PW_EMAIL/SYNC_RESET_PW/DATABASE_URL
from .env; does nothing if the email/password aren't set.

Usage:
    uv run python util/reset_local_password.py [-h]
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def error(msg):
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] in ("-h", "--help"):
            print(__doc__)
            return
        error(f"Unknown option: {sys.argv[1]}")

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "packman.settings.local")

    sys.path.insert(0, str(ROOT))
    import django

    django.setup()

    # django.setup() triggers settings import, which loads .env into
    # os.environ — so these are only available after this point.
    email = os.environ.get("SYNC_RESET_PW_EMAIL")
    password = os.environ.get("SYNC_RESET_PW")
    if not email or not password:
        print("⚠️  No SYNC_RESET_PW_EMAIL/SYNC_RESET_PW configured in .env — skipping")
        return

    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        error(f"No user found with email {email!r}")

    user.set_password(password)
    user.save(update_fields=["password"])
    print(f"✅ Password reset for {email}")


if __name__ == "__main__":
    main()
