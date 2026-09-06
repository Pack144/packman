#!/usr/bin/env python3
"""
reset_local_password.py — Reset a local user's password.

Useful after syncing a beta/production database backup (see
util/sync_local_data.sh) so there's a known login for local development —
e.g. for Copilot to use.

Usage:
    uv run python util/reset_local_password.py --email EMAIL --password PASSWORD

Options:
    --email EMAIL         Email of the user to update (required)
    --password PASSWORD   New password to set (required)
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
    parser.add_argument("--email", required=True, help="Email of the user to update")
    parser.add_argument("--password", required=True, help="New password to set")
    parser.add_argument("--database-url", help="Override DATABASE_URL for this run")
    args = parser.parse_args()

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "packman.settings.local")
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    sys.path.insert(0, str(ROOT))
    import django

    django.setup()

    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        user = User.objects.get(email__iexact=args.email)
    except User.DoesNotExist:
        error(f"No user found with email {args.email!r}")

    user.set_password(args.password)
    user.save(update_fields=["password"])
    print(f"✅ Password reset for {args.email}")


if __name__ == "__main__":
    main()
