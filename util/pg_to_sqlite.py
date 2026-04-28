#!/usr/bin/env python3
"""
pg_to_sqlite.py — Convert a PostgreSQL pg_dump (.sql or .sql.gz) to a SQLite database.

Does NOT require a running PostgreSQL server — parses the dump file directly.

Usage:
    python util/pg_to_sqlite.py <dump_file> [OPTIONS]

Arguments:
    dump_file           Path to .sql or .sql.gz pg_dump file

Options:
    --output FILE       SQLite output path (default: <dump_file_stem>.sqlite3)
    --django            Also run Django migrations after loading
                        (sets DATABASE_URL to the new SQLite DB)
    -v, --verbose       Show every statement executed
    -h, --help          Show this help

Examples:
    python util/pg_to_sqlite.py django-202603182000.sql.gz
    python util/pg_to_sqlite.py django-202603182000.sql.gz --output db.sqlite3
    python util/pg_to_sqlite.py django-202603182000.sql.gz --output db.sqlite3 --django
"""

import argparse
import gzip
import os
import re
import shutil
import sqlite3
import subprocess  # nosec B404
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

# ── SQLite reserved words that are legal PostgreSQL column names ──────────────
# These must be double-quoted when used as identifiers in SQLite.
SQLITE_RESERVED = {
    "abort",
    "action",
    "add",
    "after",
    "all",
    "alter",
    "always",
    "analyze",
    "and",
    "as",
    "asc",
    "attach",
    "autoincrement",
    "before",
    "begin",
    "between",
    "by",
    "cascade",
    "case",
    "cast",
    "check",
    "collate",
    "column",
    "commit",
    "conflict",
    "constraint",
    "create",
    "cross",
    "current",
    "current_date",
    "current_time",
    "current_timestamp",
    "database",
    "default",
    "deferrable",
    "deferred",
    "delete",
    "detach",
    "distinct",
    "do",
    "drop",
    "each",
    "else",
    "end",
    "escape",
    "except",
    "exclude",
    "exclusive",
    "exists",
    "explain",
    "fail",
    "filter",
    "first",
    "following",
    "for",
    "foreign",
    "from",
    "full",
    "generated",
    "glob",
    "group",
    "groups",
    "having",
    "if",
    "ignore",
    "immediate",
    "in",
    "index",
    "indexed",
    "initially",
    "inner",
    "insert",
    "instead",
    "intersect",
    "into",
    "is",
    "isnull",
    "join",
    "key",
    "last",
    "left",
    "like",
    "limit",
    "match",
    "materialized",
    "natural",
    "no",
    "not",
    "nothing",
    "notnull",
    "null",
    "nulls",
    "of",
    "offset",
    "on",
    "or",
    "order",
    "others",
    "outer",
    "over",
    "partition",
    "plan",
    "pragma",
    "preceding",
    "primary",
    "query",
    "raise",
    "range",
    "recursive",
    "references",
    "regexp",
    "reindex",
    "release",
    "rename",
    "replace",
    "restrict",
    "returning",
    "right",
    "rollback",
    "row",
    "rows",
    "savepoint",
    "select",
    "set",
    "table",
    "temp",
    "temporary",
    "then",
    "ties",
    "to",
    "transaction",
    "trigger",
    "unbounded",
    "union",
    "unique",
    "update",
    "using",
    "vacuum",
    "values",
    "view",
    "virtual",
    "when",
    "where",
    "window",
    "with",
    "without",
    # Common column names that collide
    "position",
    "name",
    "type",
    "status",
    "level",
    "role",
    "year",
}

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
RESET = "\033[0m"
BOLD = "\033[1m"


def info(msg):
    print(f"  {msg}")


def success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")


def warn(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")


def error(msg):
    print(f"{RED}❌ {msg}{RESET}", file=sys.stderr)
    sys.exit(1)


def header(msg):
    print(f"\n{BOLD}{CYAN}{'─'*56}\n  {msg}\n{'─'*56}{RESET}")


def step(msg):
    print(f"\n{BOLD}▶ {msg}{RESET}")


# ── PostgreSQL → SQLite type map ──────────────────────────────────────────────
# Maps PostgreSQL type strings (lower-cased, regex patterns) to SQLite affinity.
PG_TO_SQLITE_TYPES = [
    # Integers / serials
    (r"\bsmallint\b", "INTEGER"),
    (r"\bbigint\b", "INTEGER"),
    (r"\binteger\b", "INTEGER"),
    (r"\bint\b", "INTEGER"),
    (r"\bsmallserial\b", "INTEGER"),
    (r"\bserial\b", "INTEGER"),
    (r"\bbigserial\b", "INTEGER"),
    # Booleans → stored as 0/1 in SQLite
    (r"\bboolean\b", "INTEGER"),
    # Floats / numerics
    (r"\bdouble precision\b", "REAL"),
    (r"\breal\b", "REAL"),
    (r"\bnumeric(\s*\([^)]*\))?", "REAL"),
    (r"\bdecimal(\s*\([^)]*\))?", "REAL"),
    (r"\bfloat(\s*\([^)]*\))?", "REAL"),
    # Strings
    (r"\bcharacter varying(\s*\([^)]*\))?", "TEXT"),
    (r"\bvarchar(\s*\([^)]*\))?", "TEXT"),
    (r"\bcharacter(\s*\([^)]*\))?", "TEXT"),
    (r"\bchar(\s*\([^)]*\))?", "TEXT"),
    (r"\btext\b", "TEXT"),
    (r"\bcitext\b", "TEXT"),
    # UUIDs
    (r"\buuid\b", "TEXT"),
    # Dates / times → store as ISO text
    (r"\btimestamp with time zone\b", "TEXT"),
    (r"\btimestamp without time zone\b", "TEXT"),
    (r"\btimestamptz\b", "TEXT"),
    (r"\btimestamp\b", "TEXT"),
    (r"\bdate\b", "TEXT"),
    (r"\btime with time zone\b", "TEXT"),
    (r"\btime without time zone\b", "TEXT"),
    (r"\btime\b", "TEXT"),
    (r"\binterval\b", "TEXT"),
    # Binary
    (r"\bbytea\b", "BLOB"),
    # JSON
    (r"\bjsonb?\b", "TEXT"),
    # Catch-all
    (r"\barray\b", "TEXT"),
]


def convert_type(pg_type: str) -> str:
    t = pg_type.strip().lower()
    for pattern, sqlite_type in PG_TO_SQLITE_TYPES:
        if re.search(pattern, t):
            return sqlite_type
    return "TEXT"  # safe default


# ── Line-level transformations ────────────────────────────────────────────────


def transform_create_table(sql: str, pk_col: str = None) -> str:
    """
    Convert a full CREATE TABLE statement from PostgreSQL to SQLite-compatible SQL.
    Handles:
      - Type conversions
      - DEFAULT nextval(...) → removed
      - Inline CHECK constraints → kept as-is (SQLite supports them)
      - CONSTRAINT ... UNIQUE/PRIMARY KEY → kept
      - FOREIGN KEY inline → kept
      - Drops: CONSTRAINT ... EXCLUDE, DEFERRABLE, INITIALLY DEFERRED, WITH (...), TABLESPACE
    """
    # Remove PostgreSQL storage options at end of statement
    sql = re.sub(r"\bWITH\s*\([^)]*\)", "", sql)
    sql = re.sub(r"\bTABLESPACE\s+\w+", "", sql)
    sql = re.sub(r"\bDEFERRABLE\b", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bINITIALLY\s+\w+\b", "", sql, flags=re.IGNORECASE)

    # Remove EXCLUDE constraints (no SQLite equivalent)
    sql = re.sub(r",?\s*CONSTRAINT\s+\w+\s+EXCLUDE\b[^,)]*", "", sql, flags=re.IGNORECASE)

    # Detect serial/sequence columns BEFORE stripping nextval defaults.
    # These will become INTEGER PRIMARY KEY in SQLite (auto-increment rowid alias).
    # Falls back to pk_col if the dump sets the default via ALTER TABLE instead of inline.
    serial_cols = set(re.findall(r"^\s+(\w+)\s+\S.*?DEFAULT\s+nextval\s*\(", sql, flags=re.MULTILINE | re.IGNORECASE))
    if not serial_cols and pk_col:
        serial_cols = {pk_col}

    # Remove DEFAULT nextval(...) — SQLite uses INTEGER PRIMARY KEY instead
    sql = re.sub(r"DEFAULT\s+nextval\s*\([^)]*\)\s*(::\s*\w+)?", "", sql, flags=re.IGNORECASE)

    # Remove PostgreSQL casts in DEFAULT values e.g. DEFAULT ''::text → DEFAULT ''
    sql = re.sub(r"::\s*[\w\s]+(\[\])?", "", sql)

    # Convert column types: match "col_name TYPE" patterns inside the column list
    def replace_col_type(m):
        prefix = m.group(1)  # column name + whitespace
        pg_type = m.group(2)  # the type string
        suffix = m.group(3)  # rest of the line
        return f"{prefix}{convert_type(pg_type)}{suffix}"

    # Match column definitions: word boundary, identifier, whitespace, then a type phrase
    type_pattern = (
        r"(\b(\w+)\s+)"  # column name
        r"("  # start type group
        r"character varying(?:\s*\(\d+\))?"
        r"|timestamp\s+with\s+time\s+zone"
        r"|timestamp\s+without\s+time\s+zone"
        r"|time\s+with\s+time\s+zone"
        r"|time\s+without\s+time\s+zone"
        r"|double\s+precision"
        r"|(?:small|big)?(?:int(?:eger)?|serial)"
        r"|varchar(?:\s*\(\d+\))?"
        r"|char(?:acter)?(?:\s*\(\d+\))?"
        r"|numeric(?:\s*\(\d+(?:,\s*\d+)?\))?"
        r"|decimal(?:\s*\(\d+(?:,\s*\d+)?\))?"
        r"|float(?:\s*\(\d+\))?"
        r"|boolean|text|citext|uuid|bytea|jsonb?|date|interval|real|array"
        r")"  # end type group
        r"(\b)"  # word boundary or end
    )
    sql = re.sub(
        type_pattern,
        lambda m: f"{m.group(1)}{convert_type(m.group(3))}{m.group(4)}",
        sql,
        flags=re.IGNORECASE,
    )

    # Promote serial columns to INTEGER PRIMARY KEY (gives SQLite auto-increment
    # via the rowid alias — no explicit AUTOINCREMENT needed).
    if serial_cols:
        serial_lower = {s.lower() for s in serial_cols}

        def make_primary_key(m):
            indent, col, rest = m.group(1), m.group(2), m.group(3)
            if col.lower() in serial_lower:
                # rest starts with \s+INTEGER (captured by the regex) — strip it
                # since we're replacing the whole type with INTEGER PRIMARY KEY.
                rest = re.sub(r"^\s+\w+", "", rest)
                rest = re.sub(r"\s+NOT\s+NULL\b", "", rest, flags=re.IGNORECASE)
                return f'{indent}"{col}" INTEGER PRIMARY KEY{rest}'
            return m.group(0)

        sql = re.sub(r"^([ \t]+)(\w+)(\s+INTEGER\b[^,\n]*)", make_primary_key, sql, flags=re.MULTILINE | re.IGNORECASE)

    # Quote any unquoted column names that are SQLite reserved words.
    # Match: start-of-line whitespace + bare word + space (column definition context).
    def quote_reserved_col(m):
        word = m.group(1)
        rest = m.group(2)
        if word.lower() in SQLITE_RESERVED:
            return f'    "{word}"{rest}'
        return f"    {word}{rest}"

    sql = re.sub(
        r"^    (\w+)(\s+(?:INTEGER|TEXT|REAL|BLOB|NUMERIC)\b)",
        quote_reserved_col,
        sql,
        flags=re.MULTILINE | re.IGNORECASE,
    )

    return sql


# Django's SQLite backend stores UUIDs as 32-char hex WITHOUT hyphens.
# pg_dump emits them WITH hyphens (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx).
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def pg_value_to_sqlite(value: str) -> str:
    """Convert a single tab-separated COPY value to a SQLite-ready Python object."""
    if value == r"\N":
        return None
    if value == r"\\.":
        return None
    # Unescape PostgreSQL backslash sequences
    value = value.replace(r"\\", "\\")
    value = value.replace(r"\n", "\n")
    value = value.replace(r"\r", "\r")
    value = value.replace(r"\t", "\t")
    # Normalise UUIDs: Django's SQLite backend expects 32-char hex without hyphens
    if _UUID_RE.match(value):
        value = value.replace("-", "")
    return value


# ── SQL dump parser / converter ───────────────────────────────────────────────


class PgDumpConverter:
    """
    Streaming parser for a pg_dump plain-SQL file.
    Yields (kind, payload) tuples:
      ('create_table', sql_string)
      ('insert', (table, columns, [values_list, ...]))
      ('index', sql_string)
      ('constraint', sql_string)
      ('skip', None)
    """

    SKIP_PREFIXES = (
        "--",  # comments
        "SET ",  # pg config
        "SELECT pg_",  # sequence resets
        "CREATE SEQUENCE",
        "ALTER SEQUENCE",
        "REVOKE ",
        "GRANT ",
        "CREATE EXTENSION",
        "COMMENT ON",
        "CREATE SCHEMA",
        "ALTER SCHEMA",
        "CREATE TYPE",  # enum types — handle separately if needed
        "ALTER TYPE",
        "CREATE AGGREGATE",
        "CREATE FUNCTION",
        "CREATE OPERATOR",
        "CREATE TRIGGER",
        "CREATE VIEW",
        "ALTER TABLE ONLY",  # constraints / ownership (handled below)
        "ALTER TABLE",
        "ALTER DATABASE",
        "BEGIN;",
        "COMMIT;",
        r"\connect",
        "pg_restore:",
    )

    def __init__(self, lines, verbose=False, pks=None):
        self.lines = iter(lines)
        self.verbose = verbose
        self._peeked = None
        self.pks = pks or {}

    def _next_line(self):
        if self._peeked is not None:
            line = self._peeked
            self._peeked = None
            return line
        return next(self.lines, None)

    def parse(self):
        buffer = []
        in_statement = False
        copy_table = None
        copy_cols = []
        copy_rows = []

        for raw in self.lines:
            line = raw.rstrip("\n")

            # ── Inside a COPY data block ───────────────────────────────────
            if copy_table is not None:
                if line == "\\.":
                    yield ("insert", (copy_table, copy_cols, copy_rows))
                    copy_table = None
                    copy_cols = []
                    copy_rows = []
                else:
                    values = [pg_value_to_sqlite(v) for v in line.split("\t")]
                    copy_rows.append(values)
                continue

            # ── Skip blank lines and comments ──────────────────────────────
            stripped = line.strip()
            if not stripped:
                continue

            # ── COPY statement ─────────────────────────────────────────────
            copy_match = re.match(r"COPY\s+(?:\w+\.)?(\w+)\s*\(([^)]+)\)\s+FROM\s+stdin", stripped, re.IGNORECASE)
            if copy_match:
                copy_table = copy_match.group(1)
                copy_cols = [c.strip().strip('"') for c in copy_match.group(2).split(",")]
                copy_rows = []
                continue

            # ── Detect start of CREATE TABLE ───────────────────────────────
            if re.match(r"CREATE TABLE\b", stripped, re.IGNORECASE):
                buffer = [line]
                in_statement = True
                continue

            # ── Collect CREATE TABLE body ──────────────────────────────────
            if in_statement:
                buffer.append(line)
                if stripped.endswith(";"):
                    full = "\n".join(buffer)
                    # Remove schema qualifiers: public.tablename → tablename
                    full = re.sub(r"\bpublic\.(\w+)", r"\1", full)
                    tbl_match = re.match(r"CREATE TABLE\s+(?:\w+\.)?(\w+)\b", full, re.IGNORECASE)
                    tbl_name = tbl_match.group(1) if tbl_match else None
                    pk_col = self.pks.get(tbl_name) if tbl_name else None
                    yield ("create_table", transform_create_table(full, pk_col=pk_col))
                    buffer = []
                    in_statement = False
                continue

            # ── CREATE INDEX ───────────────────────────────────────────────
            if re.match(r"CREATE\s+(UNIQUE\s+)?INDEX\b", stripped, re.IGNORECASE):
                idx = re.sub(r"\bpublic\.(\w+)", r"\1", stripped)
                # Strip CONCURRENTLY (not supported in SQLite)
                idx = re.sub(r"\bCONCURRENTLY\b\s*", "", idx, flags=re.IGNORECASE)
                # Strip USING <method> (btree, hash, gist, gin, brin, spgist)
                idx = re.sub(r"\bUSING\s+\w+\s*", "", idx, flags=re.IGNORECASE)
                # Strip PostgreSQL operator classes inside index column list
                # e.g. (email varchar_pattern_ops) → (email)
                idx = re.sub(
                    r"\b(varchar|text|bpchar|integer|float|date|timestamptz?)_pattern_ops\b",
                    "",
                    idx,
                    flags=re.IGNORECASE,
                )
                idx = re.sub(r"\b\w+_ops\b", "", idx)  # catch any remaining _ops
                # Strip NULLS FIRST/LAST
                idx = re.sub(r"\bNULLS\s+(FIRST|LAST)\b", "", idx, flags=re.IGNORECASE)
                # Clean up any double spaces left behind
                idx = re.sub(r"  +", " ", idx).strip()

                # Quote reserved words appearing as column names in index column list
                def quote_idx_col(m):
                    col = m.group(1)
                    if col.lower() in SQLITE_RESERVED:
                        return f'"{col}"'
                    return col

                idx = re.sub(r"\b([a-zA-Z_]\w*)\b(?=\s*[,)])", quote_idx_col, idx)
                yield ("index", idx)
                continue

            # ── ADD CONSTRAINT (FK / UNIQUE / PK from ALTER TABLE) ─────────
            if re.match(r"ALTER TABLE\b.*ADD CONSTRAINT\b", stripped, re.IGNORECASE):
                yield ("constraint", stripped)  # logged but not applied
                continue

            # ── Everything else: skip ──────────────────────────────────────
            # (SET, SELECT pg_catalog, sequences, grants, etc.)


# ── SQLite writer ─────────────────────────────────────────────────────────────


class SQLiteWriter:
    def __init__(self, db_path: Path, verbose: bool = False):
        self.db_path = db_path
        self.verbose = verbose
        self.conn = sqlite3.connect(str(db_path))
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=OFF")  # disable during load
        self.conn.execute("PRAGMA synchronous=OFF")  # faster bulk insert
        self.tables_created = 0
        self.rows_inserted = 0
        self.errors = []

    def execute(self, sql: str):
        if self.verbose:
            preview = sql[:120].replace("\n", " ")
            info(f"SQL: {preview}{'…' if len(sql) > 120 else ''}")
        try:
            self.conn.execute(sql)
        except sqlite3.OperationalError as e:
            msg = f"SQLite error: {e}\n  Statement: {sql[:200]}"
            self.errors.append(msg)
            warn(msg)

    def create_table(self, sql: str):
        # Strip any remaining PostgreSQL-isms that slipped through
        sql = re.sub(r"\bpublic\.(\w+)", r"\1", sql)
        # SQLite doesn't support some constraint syntax
        # Remove NOT VALID
        sql = re.sub(r"\bNOT VALID\b", "", sql, flags=re.IGNORECASE)
        self.execute(sql)
        self.tables_created += 1

    def insert_rows(self, table: str, columns: list, rows: list):
        if not rows:
            return
        placeholders = ", ".join(["?"] * len(columns))
        cols = ", ".join(f'"{c}"' for c in columns)
        sql = f'INSERT OR IGNORE INTO "{table}" ({cols}) VALUES ({placeholders})'

        try:
            self.conn.executemany(sql, rows)
            self.rows_inserted += len(rows)
        except sqlite3.OperationalError as e:
            # Table might not exist (view, temp table, etc.) — skip gracefully
            warn(f"Insert into '{table}' failed: {e} — skipping {len(rows)} rows")

    def commit(self):
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.commit()
        self.conn.close()

    def report(self):
        success(f"Tables created : {self.tables_created}")
        success(f"Rows inserted  : {self.rows_inserted:,}")
        if self.errors:
            warn(f"Errors         : {len(self.errors)} (see above)")


# ── Open dump file ────────────────────────────────────────────────────────────


def open_dump(path: Path):
    """Return an iterator of decoded text lines from a .sql or .sql.gz file."""
    if path.suffix == ".gz":
        f = gzip.open(path, "rt", encoding="utf-8", errors="replace")
    else:
        f = open(path, "r", encoding="utf-8", errors="replace")
    return f


def prescan_pks(path: Path) -> dict:
    """
    Quick first-pass scan to collect single-column primary keys from
    ALTER TABLE ... ADD CONSTRAINT ... PRIMARY KEY (...) statements.
    Handles both single-line and two-line forms (pg_dump splits them).
    Returns {table_name: pk_col_name}.  Multi-column PKs are ignored
    (they can't be INTEGER PRIMARY KEY in SQLite).
    """
    pks = {}
    alter_re = re.compile(r"ALTER TABLE\s+(?:ONLY\s+)?(?:\w+\.)?(\w+)\s*$", re.IGNORECASE)
    pk_re = re.compile(r"ADD CONSTRAINT\s+\w+\s+PRIMARY KEY\s*\(([^)]+)\)", re.IGNORECASE)
    last_table = None
    with open_dump(path) as fh:
        for line in fh:
            # Single-line form: ALTER TABLE ... ADD CONSTRAINT ... PRIMARY KEY (...)
            combined_m = re.search(
                r"ALTER TABLE\s+(?:ONLY\s+)?(?:\w+\.)?(\w+)\s+ADD CONSTRAINT\s+\w+\s+PRIMARY KEY\s*\(([^)]+)\)",
                line,
                re.IGNORECASE,
            )
            if combined_m:
                table = combined_m.group(1)
                cols = [c.strip().strip('"') for c in combined_m.group(2).split(",")]
                if len(cols) == 1:
                    pks[table] = cols[0]
                last_table = None
                continue

            # Two-line form: track ALTER TABLE line, then match ADD CONSTRAINT on next
            alter_m = alter_re.search(line)
            if alter_m:
                last_table = alter_m.group(1)
                continue

            if last_table:
                pk_m = pk_re.search(line)
                if pk_m:
                    cols = [c.strip().strip('"') for c in pk_m.group(1).split(",")]
                    if len(cols) == 1:
                        pks[last_table] = cols[0]
                last_table = None

    return pks


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Convert a pg_dump SQL file to SQLite.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("dump_file", help="Path to .sql or .sql.gz pg_dump file")
    parser.add_argument("--output", help="SQLite output path (default: <stem>.sqlite3)")
    parser.add_argument(
        "--django", action="store_true", help="Run Django migrations after load (merges schema + data)"
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    dump_path = Path(args.dump_file).expanduser().resolve()
    if not dump_path.exists():
        error(f"Dump file not found: {dump_path}")

    stem = dump_path.name.replace(".sql.gz", "").replace(".sql", "")
    if args.output:
        sqlite_path = Path(args.output).expanduser().resolve()
    else:
        sqlite_path = dump_path.parent / f"{stem}.sqlite3"

    header("PostgreSQL dump → SQLite")
    info(f"Input  : {dump_path}  ({dump_path.stat().st_size / 1024 / 1024:.1f} MB)")
    info(f"Output : {sqlite_path}")

    # Remove old DB and any WAL/shm files so we start fresh
    for suffix in ("", "-shm", "-wal"):
        p = sqlite_path.parent / (sqlite_path.name + suffix)
        if p.exists():
            warn(f"Removing existing {p.name}")
            p.unlink()

    writer = SQLiteWriter(sqlite_path, verbose=args.verbose)

    step("Pre-scanning dump for primary keys…")
    pks = prescan_pks(dump_path)
    info(f"Found {len(pks)} single-column primary key(s)")

    step("Parsing and converting dump…")
    counts = {"create_table": 0, "insert": 0, "index": 0, "constraint": 0}

    with open_dump(dump_path) as fh:
        converter = PgDumpConverter(fh, verbose=args.verbose, pks=pks)
        for kind, payload in converter.parse():
            counts[kind] = counts.get(kind, 0) + 1
            if kind == "create_table":
                writer.create_table(payload)
            elif kind == "insert":
                table, cols, rows = payload
                writer.insert_rows(table, cols, rows)
            elif kind == "index":
                writer.execute(payload)
            # 'constraint' (FK / UNIQUE from ALTER TABLE) — logged, not applied
            # SQLite enforces them via CREATE TABLE definitions instead

    writer.commit()

    step("Results")
    info(f"Statements processed: {sum(counts.values()):,}")
    info(f"  CREATE TABLE : {counts.get('create_table', 0)}")
    info(f"  COPY→INSERT  : {counts.get('insert', 0)}")
    info(f"  CREATE INDEX : {counts.get('index', 0)}")
    writer.report()

    # ── Optional: run Django migrations ───────────────────────────────────
    if args.django:
        step("Running Django migrations (--django flag)")
        info("This fills in any tables Django manages that weren't in the dump.")
        db_url = f"sqlite:///{sqlite_path}"
        env = {
            **os.environ,
            "DATABASE_URL": db_url,
            "DJANGO_SETTINGS_MODULE": "packman.settings.local",
        }
        if shutil.which("pipenv") and (ROOT / "Pipfile").exists():
            python_cmd = ["pipenv", "run", "python"]
        elif (ROOT / ".venv" / "bin" / "python").exists():
            python_cmd = [str(ROOT / ".venv" / "bin" / "python")]
        else:
            python_cmd = ["python"]

        result = subprocess.run(  # nosec B603
            [*python_cmd, "manage.py", "migrate", "--run-syncdb"],
            env=env,
            cwd=ROOT,
        )
        if result.returncode == 0:
            success("Django migrations complete")
        else:
            warn("Django migrations finished with errors — check output above")

    header("Done")
    success(f"SQLite database saved to: {sqlite_path}")
    info(f"To use with Django, set DATABASE_URL=sqlite:///{sqlite_path}")
    info("Or copy to db.sqlite3 in the project root.")


if __name__ == "__main__":
    main()
