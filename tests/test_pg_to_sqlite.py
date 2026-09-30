import sqlite3
import tempfile
from pathlib import Path
from unittest import TestCase

from util.pg_to_sqlite import PgDumpConverter, SQLiteWriter


class PgDumpConstraintTestCase(TestCase):
    def test_parser_preserves_single_line_and_split_key_constraints(self):
        statements = [
            "ALTER TABLE ONLY public.membership_scout",
            "    ADD CONSTRAINT membership_scout_pkey PRIMARY KEY (member_ptr_id);",
            "ALTER TABLE ONLY public.membership_member ADD CONSTRAINT membership_member_slug_key UNIQUE (slug);",
        ]

        events = list(PgDumpConverter(statements).parse())

        self.assertEqual(
            events,
            [
                (
                    "unique_constraint",
                    {
                        "table": "membership_scout",
                        "name": "membership_scout_pkey",
                        "kind": "PRIMARY KEY",
                        "columns": ("member_ptr_id",),
                    },
                ),
                (
                    "unique_constraint",
                    {
                        "table": "membership_member",
                        "name": "membership_member_slug_key",
                        "kind": "UNIQUE",
                        "columns": ("slug",),
                    },
                ),
            ],
        )

    def test_imported_text_primary_key_can_be_referenced_by_foreign_key(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            writer = SQLiteWriter(Path(temporary_directory) / "test.sqlite3")
            try:
                writer.create_table('CREATE TABLE "membership_scout" ("member_ptr_id" TEXT NOT NULL)')
                writer.insert_rows("membership_scout", ["member_ptr_id"], [["scout-1"]])
                writer.add_unique_constraint(
                    {
                        "table": "membership_scout",
                        "name": "membership_scout_pkey",
                        "kind": "PRIMARY KEY",
                        "columns": ("member_ptr_id",),
                    }
                )
                writer.create_table(
                    'CREATE TABLE "campaigns_campaignscout" ('
                    '"scout_id" TEXT NOT NULL, '
                    'FOREIGN KEY ("scout_id") REFERENCES "membership_scout" ("member_ptr_id")'
                    ")"
                )
                writer.insert_rows("campaigns_campaignscout", ["scout_id"], [["scout-1"]])

                self.assertEqual(writer.conn.execute("PRAGMA foreign_key_check").fetchall(), [])
                with self.assertRaises(sqlite3.IntegrityError):
                    writer.conn.execute(
                        'INSERT INTO "membership_scout" ("member_ptr_id") VALUES (?)',
                        ("scout-1",),
                    )
            finally:
                writer.conn.close()

    def test_existing_integer_primary_key_does_not_get_a_redundant_index(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            writer = SQLiteWriter(Path(temporary_directory) / "test.sqlite3")
            try:
                writer.create_table('CREATE TABLE "campaign" ("id" INTEGER PRIMARY KEY)')
                writer.add_unique_constraint(
                    {
                        "table": "campaign",
                        "name": "campaign_pkey",
                        "kind": "PRIMARY KEY",
                        "columns": ("id",),
                    }
                )

                self.assertEqual(writer.conn.execute('PRAGMA index_list("campaign")').fetchall(), [])
            finally:
                writer.conn.close()
