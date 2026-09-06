#!/usr/bin/env python3
"""
reset_local_password.py — Reset a local user's password.

Useful after syncing a beta/production database backup (see
util/sync_local_data.sh) so there's a known login for local development —
e.g. for Copilot to use.

Defaults to the SYNC_RESET_PASSWORD_EMAIL/SYNC_RESET_PASSWORD values in
.env; if neither --email/--password nor those are set, does nothing.

Usage:
    uv run python util/reset_local_password.py [OPTIONS]

Options:
    --email EMAIL         Email of the user to update. Falls back to
                          SYNC_RESET_PASSWORD_EMAIL in .env.
    --password PASSWORD   New password to set. Falls back to
                          SYNC_RESET_PASSWORD in .env.
    --database-url URL    Override DATABASE_URL for this run
    -h, --help             Show this help message
"""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def error(msg):
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Reset a local user's password.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--email", help="Email of the user to update (defaults to SYNC_RESET_PASSWORD_EMAIL in .env)"
    )
    parser.add_argument(
        "--password", help="New password to set (defaults to SYNC_RESET_PASSWORD in .env)"
    )
    parser.add_argument("--database-url", help="Override DATABASE_URL for this run")
    args = parser.parse_args()

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "packman.settings.local")
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    sys.path.insert(0, str(ROOT))
    import django

    django.setup()

    # django.setup() triggers settings import, which loads .env into
    # os.environ — so these are only available after this point.
    email = args.email or os.environ.get("SYNC_RESET_PASSWORD_EMAIL")
    password = args.password or os.environ.get("SYNC_RESET_PASSWORD")
    if not email or not password:
        print("⚠️  No email/password configured — skipping (see --email/--password or SYNC_RESET_PASSWORD_EMAIL/SYNC_RESET_PASSWORD in .env)")
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
