#!/usr/bin/env python
"""
Sync each Cub's Scouting America membership ID and expiration date from the
Pack144_Cub_Membership.csv council export (data baked in below).

This is one of two independent ways to apply the same update -- run this
script, or run update_cub_membership.sql directly against the database
(e.g. via sqlite3/psql). They don't depend on each other; pick whichever
your admin tooling supports.

The CSV has no field in common with an existing Cub record (no BSA/member
UUID, no slug), so each row is matched to an existing packman.membership.Scout
record by First + Last name (case-insensitive). Rows where a name doesn't
match exactly one Cub are skipped and reported. Rows where both MembershipID
and ExpirationDate were blank in the source CSV (nothing to sync) are not
included in CUB_MEMBERSHIP_DATA at all.

Only `scouting_membership_id` and `scouting_membership_expires_on` are
touched. Den assignment is intentionally out of scope -- it lives in a
separate dens.Membership join table keyed by Pack Year.

Usage:
    uv run python util/update_cub_membership.py [--dry-run]
"""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# One entry per Cub with a MembershipID and/or ExpirationDate on file, taken
# directly from Pack144_Cub_Membership.csv. Rows where both were blank are
# omitted -- there's nothing to sync for them.
CUB_MEMBERSHIP_DATA = [
    {"first_name": "Wyatt", "last_name": "Adams", "membership_id": "141639279", "expires_on": "2027-07-31"},
    {"first_name": "Cory", "last_name": "Aderhold", "membership_id": "140959468", "expires_on": "2027-06-30"},
    {"first_name": "Milo", "last_name": "Almquist", "membership_id": "140520740", "expires_on": "2026-08-31"},
    {"first_name": "Nico", "last_name": "Altamirano", "membership_id": "140520762", "expires_on": "2026-08-31"},
    {"first_name": "William", "last_name": "Appleyard", "membership_id": "142472254", "expires_on": "2027-09-30"},
    {"first_name": "Logan", "last_name": "Bernal", "membership_id": "141035242", "expires_on": "2026-09-30"},
    {"first_name": "Palmer", "last_name": "Bottorff", "membership_id": "140704156", "expires_on": "2027-09-30"},
    {"first_name": "Teddy", "last_name": "Busch", "membership_id": "14870652", "expires_on": "2026-12-31"},
    {"first_name": "Alexander", "last_name": "Cabral", "membership_id": "141675905", "expires_on": "2027-08-31"},
    {"first_name": "Carter", "last_name": "Campbell", "membership_id": "140520516", "expires_on": "2026-08-31"},
    {"first_name": "Jackson", "last_name": "Carter", "membership_id": "142434582", "expires_on": "2027-09-30"},
    {"first_name": "Parker", "last_name": "Champion", "membership_id": "140521039", "expires_on": "2027-08-31"},
    {"first_name": "Avery", "last_name": "Choate", "membership_id": "140959548", "expires_on": "2027-06-30"},
    {"first_name": "Peter", "last_name": "Clausen", "membership_id": "141639268", "expires_on": "2027-07-31"},
    {"first_name": "Will", "last_name": "Clausen", "membership_id": "14870885", "expires_on": "2026-12-31"},
    {"first_name": "Sloane", "last_name": "Collins", "membership_id": "142416412", "expires_on": "2027-08-31"},
    {"first_name": "Mason", "last_name": "Cousins", "membership_id": "142443900", "expires_on": "2027-09-30"},
    {"first_name": "Wren", "last_name": "Dangler", "membership_id": "140520842", "expires_on": "2027-08-31"},
    {"first_name": "Hugo", "last_name": "Deas", "membership_id": "141628561", "expires_on": "2027-05-31"},
    {"first_name": "Sammy", "last_name": "Dershowitz", "membership_id": "141050410", "expires_on": "2026-09-30"},
    {"first_name": "Velvel", "last_name": "Dershowitz", "membership_id": "14870670", "expires_on": "2026-12-31"},
    {"first_name": "Logan", "last_name": "Dubose", "membership_id": "140964281", "expires_on": "2027-06-30"},
    {"first_name": "Nat", "last_name": "Edson", "membership_id": "142418575", "expires_on": "2027-08-31"},
    {"first_name": "Oliver", "last_name": "Feiling", "membership_id": "141776023", "expires_on": "2027-09-30"},
    {"first_name": "Gage", "last_name": "Fenton-Close", "membership_id": "142405702", "expires_on": "2027-08-31"},
    {"first_name": "Calder", "last_name": "Fenton-Close", "membership_id": "142405720", "expires_on": "2027-08-31"},
    {"first_name": "Charlie", "last_name": "Fenwood Hughes", "membership_id": "142435926", "expires_on": "2027-09-30"},
    {"first_name": "Meir", "last_name": "Friedman", "membership_id": "142439446", "expires_on": "2027-09-30"},
    {"first_name": "Ryan", "last_name": "Gozzano", "membership_id": "14870544", "expires_on": "2026-12-31"},
    {"first_name": "Emily", "last_name": "Green", "membership_id": "140376354", "expires_on": "2026-08-31"},
    {"first_name": "David", "last_name": "Hasten", "membership_id": "141629748", "expires_on": "2027-05-31"},
    {"first_name": "William", "last_name": "Hegg", "membership_id": "141318922", "expires_on": "2027-09-30"},
    {"first_name": "Julia", "last_name": "Hirai-Hadley", "membership_id": "14870664", "expires_on": "2026-12-31"},
    {"first_name": "Adit", "last_name": "Holenarsipur", "membership_id": "142450651", "expires_on": "2027-09-30"},
    {"first_name": "Fran", "last_name": "Holman", "membership_id": "141107833", "expires_on": "2027-09-30"},
    {"first_name": "Leo", "last_name": "Hritz", "membership_id": "141634252", "expires_on": "2027-05-31"},
    {"first_name": "Nolan", "last_name": "Kelch", "membership_id": "141012044", "expires_on": "2027-09-30"},
    {"first_name": "Jude", "last_name": "Kelch", "membership_id": "140521002", "expires_on": "2027-08-31"},
    {"first_name": "Joe", "last_name": "Klatte", "membership_id": "140520690", "expires_on": "2027-08-31"},
    {"first_name": "Norbert", "last_name": "Kocar", "membership_id": "142434379", "expires_on": "2027-09-30"},
    {"first_name": "Oliver", "last_name": "Kocar", "membership_id": "142434386", "expires_on": "2027-09-30"},
    {"first_name": "James", "last_name": "LaComb", "membership_id": "142434500", "expires_on": "2027-09-30"},
    {"first_name": "Leo", "last_name": "Markoff", "membership_id": "14870861", "expires_on": "2026-12-31"},
    {"first_name": "Celi", "last_name": "Maximo", "membership_id": "141793246", "expires_on": "2026-09-30"},
    {"first_name": "Bo", "last_name": "Maximo", "membership_id": "141793292", "expires_on": "2026-09-30"},
    {"first_name": "Caelan", "last_name": "McCracken", "membership_id": "142446154", "expires_on": "2027-09-30"},
    {"first_name": "Anders", "last_name": "McCracken", "membership_id": "141832364", "expires_on": "2027-09-30"},
    {"first_name": "Xavier", "last_name": "McVicar", "membership_id": "142383272", "expires_on": "2027-08-31"},
    {"first_name": "Quincy", "last_name": "McVicar", "membership_id": "140520966", "expires_on": "2027-08-31"},
    {"first_name": "Sam", "last_name": "Meguerditchian", "membership_id": "141623384", "expires_on": "2027-05-31"},
    {"first_name": "Jacob", "last_name": "Mondau", "membership_id": "142402735", "expires_on": "2027-08-31"},
    {"first_name": "Callum", "last_name": "Morse", "membership_id": "140521059", "expires_on": "2027-08-31"},
    {"first_name": "William", "last_name": "Mosca", "membership_id": "141644185", "expires_on": "2027-07-31"},
    {"first_name": "Orion", "last_name": "Muller", "membership_id": "141629266", "expires_on": "2027-05-31"},
    {"first_name": "Dashiell", "last_name": "Nicodemus", "membership_id": "140718816", "expires_on": "2026-11-30"},
    {"first_name": "Garrison", "last_name": "Nielsen", "membership_id": "140520641", "expires_on": "2027-08-31"},
    {"first_name": "Fraser", "last_name": "Niffin", "membership_id": "141764175", "expires_on": "2027-09-30"},
    {"first_name": "Alex", "last_name": "Ostradicky", "membership_id": "140520458", "expires_on": "2027-08-31"},
    {"first_name": "Milo", "last_name": "Pahnke", "membership_id": "140520957", "expires_on": "2027-08-31"},
    {"first_name": "Vaso", "last_name": "Patterson", "membership_id": "14870877", "expires_on": "2026-12-31"},
    {"first_name": "Callan", "last_name": "Rooney", "membership_id": "141635391", "expires_on": "2027-05-31"},
    {"first_name": "Alexander", "last_name": "Royalty", "membership_id": "140967909", "expires_on": "2027-06-30"},
    {"first_name": "Linus", "last_name": "Russell", "membership_id": "142412560", "expires_on": "2027-08-31"},
    {"first_name": "Benjamin", "last_name": "Shendure", "membership_id": "140520916", "expires_on": "2027-08-31"},
    {"first_name": "Zuber", "last_name": "Stemen", "membership_id": "140960698", "expires_on": "2027-06-30"},
    {"first_name": "Akash", "last_name": "Sundar", "membership_id": "142418028", "expires_on": "2027-08-31"},
    {"first_name": "Bodhi", "last_name": "Thompson", "membership_id": "141637695", "expires_on": "2027-06-30"},
    {"first_name": "Johannes", "last_name": "Thoreen", "membership_id": "141636711", "expires_on": "2027-05-31"},
    {"first_name": "Olin", "last_name": "Tradal", "membership_id": "141311240", "expires_on": "2027-10-31"},
    {"first_name": "Clara", "last_name": "Walsworth", "membership_id": "141637015", "expires_on": "2027-09-30"},
    {"first_name": "Miles", "last_name": "Walsworth", "membership_id": "141031354", "expires_on": "2027-09-30"},
    {"first_name": "Walter", "last_name": "Weckner", "membership_id": "140959383", "expires_on": "2027-06-30"},
    {"first_name": "Samuel", "last_name": "Wise", "membership_id": "141584633", "expires_on": "2027-07-31"},
    {"first_name": "Ethan", "last_name": "Wu", "membership_id": "141641731", "expires_on": "2026-07-31"},
    {"first_name": "Jude", "last_name": "Yukevich", "membership_id": "140704138", "expires_on": "2026-11-30"},
]


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing anything to the database.",
    )
    return parser.parse_args()


def setup_django():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "packman.settings.local")
    sys.path.insert(0, str(ROOT))
    import django

    django.setup()


def main():
    args = parse_args()
    setup_django()

    import datetime

    from django.db import transaction

    from packman.membership.models import Scout

    updated_count = 0
    skipped_no_match = []
    skipped_ambiguous = []

    with transaction.atomic():
        for entry in CUB_MEMBERSHIP_DATA:
            full_name = f"{entry['first_name']} {entry['last_name']}"
            matches = Scout.objects.filter(
                first_name__iexact=entry["first_name"],
                last_name__iexact=entry["last_name"],
            )
            count = matches.count()
            if count == 0:
                skipped_no_match.append(full_name)
                continue
            elif count > 1:
                skipped_ambiguous.append(full_name)
                continue

            scout = matches.get()
            scout.scouting_membership_id = entry["membership_id"]
            scout.scouting_membership_expires_on = datetime.date.fromisoformat(entry["expires_on"])
            scout.save()
            updated_count += 1

        if args.dry_run:
            transaction.set_rollback(True)

    label = "Would update" if args.dry_run else "Updated"
    print(f"{label} {updated_count} of {len(CUB_MEMBERSHIP_DATA)} Cub record(s).")
    if skipped_no_match:
        print(f"Skipped {len(skipped_no_match)} row(s) with no matching Cub: {', '.join(skipped_no_match)}")
    if skipped_ambiguous:
        print(f"Skipped {len(skipped_ambiguous)} row(s) matching more than one Cub: {', '.join(skipped_ambiguous)}")
    if args.dry_run:
        print("Dry run: no changes were committed to the database.")


if __name__ == "__main__":
    main()
