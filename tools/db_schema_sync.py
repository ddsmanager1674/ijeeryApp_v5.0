"""
iJeery — DB schema sync (non-destructive)

Goal:
- Compare the *expected* schema (from `Structure database.sql` + optional extra SQL via `--extra-sql`)
  with the *actual* schema in PostgreSQL (public schema),
  then apply ONLY additive changes: missing tables, columns, PK/FK constraints, indexes.

Safety:
- No DROP, no type changes, no column removals.
- All DDL is executed in a single transaction by default (rollback on failure).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Iterable, Optional

import psycopg2


_RE_CREATE_TABLE = re.compile(r"^\s*CREATE\s+TABLE\s+public\.(?P<table>[a-zA-Z0-9_]+)\s*\(\s*$")
_RE_ALTER_TABLE_ONLY = re.compile(r"^\s*ALTER\s+TABLE\s+ONLY\s+public\.(?P<table>[a-zA-Z0-9_]+)\s*$")
_RE_ADD_PK = re.compile(
    r"^\s*ADD\s+CONSTRAINT\s+(?P<name>[a-zA-Z0-9_]+)\s+PRIMARY\s+KEY\s*\((?P<cols>[^)]+)\)\s*;\s*$",
    re.IGNORECASE,
)
_RE_ADD_FK = re.compile(
    r"^\s*ADD\s+CONSTRAINT\s+(?P<name>[a-zA-Z0-9_]+)\s+FOREIGN\s+KEY\s*\((?P<cols>[^)]+)\)\s+REFERENCES\s+public\.(?P<ref_table>[a-zA-Z0-9_]+)\s*\((?P<ref_cols>[^)]+)\)\s*;\s*$",
    re.IGNORECASE,
)
_RE_CREATE_INDEX = re.compile(
    r"^\s*CREATE\s+INDEX\s+(?P<name>[a-zA-Z0-9_]+)\s+ON\s+public\.(?P<table>[a-zA-Z0-9_]+)\s+USING\s+(?P<method>[a-zA-Z0-9_]+)\s*\((?P<expr>.+)\)\s*;\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ExpectedIndex:
    name: str
    table: str
    method: str
    expr: str

    def ddl(self) -> str:
        return f'CREATE INDEX IF NOT EXISTS {self.name} ON public.{self.table} USING {self.method} ({self.expr});'


@dataclass(frozen=True)
class ExpectedConstraint:
    name: str
    table: str
    ddl_fragment: str  # e.g. "ADD CONSTRAINT ... PRIMARY KEY (...);" or FK

    def ddl(self) -> str:
        return f"ALTER TABLE ONLY public.{self.table}\n    {self.ddl_fragment}"


@dataclass
class ExpectedTable:
    name: str
    column_lines: list[str]  # raw column lines (without trailing newline)

    def create_ddl(self) -> str:
        cols = []
        for ln in self.column_lines:
            ln = ln.strip()
            if not ln:
                continue
            # keep exactly as in dump, but remove a trailing comma if present
            cols.append(re.sub(r",\s*$", "", ln))
        body = ",\n    ".join(cols)
        return f"CREATE TABLE IF NOT EXISTS public.{self.name} (\n    {body}\n);"


def _read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_db_config(project_root: str) -> dict:
    cfg_path = os.path.join(project_root, "config.json")
    cfg = _read_json(cfg_path)
    return cfg["database"]


def _iter_expected_sql_files(project_root: str, extra_sql_paths: list[str]) -> list[str]:
    files: list[str] = []
    base = os.path.join(project_root, "Structure database.sql")
    if os.path.exists(base):
        files.append(base)
    # project sql patches
    sql_dir = os.path.join(project_root, "sql")
    if os.path.isdir(sql_dir):
        for name in sorted(os.listdir(sql_dir)):
            if name.lower().endswith(".sql"):
                files.append(os.path.join(sql_dir, name))
    # extra user-provided paths
    for p in extra_sql_paths:
        files.append(p if os.path.isabs(p) else os.path.join(project_root, p))
    # keep only existing
    return [p for p in files if os.path.exists(p)]


def _patch_tables_from_sql(sql_text: str) -> set[str]:
    """
    Extract tables created by patch files (usually better-curated than the dump).
    We only use this to avoid creating a table with a less accurate definition.
    """
    tables: set[str] = set()
    for m in re.finditer(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+public\.(?P<table>[a-zA-Z0-9_]+)", sql_text, re.IGNORECASE):
        tables.add(m.group("table"))
    return tables


def parse_expected_from_structure_sql(sql_text: str) -> tuple[dict[str, ExpectedTable], list[ExpectedConstraint], list[ExpectedIndex]]:
    """
    Parse a pg_dump-like schema file.
    Supported:
    - CREATE TABLE public.<name> ( ... );
    - ALTER TABLE ONLY public.<name> ADD CONSTRAINT ... PRIMARY KEY (...);
    - ALTER TABLE ONLY public.<name> ADD CONSTRAINT ... FOREIGN KEY (...) REFERENCES public.<ref>(...);
    - CREATE INDEX <name> ON public.<table> USING <method> (...);
    """
    tables: dict[str, ExpectedTable] = {}
    constraints: list[ExpectedConstraint] = []
    indexes: list[ExpectedIndex] = []

    lines = sql_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]

        m_tbl = _RE_CREATE_TABLE.match(line)
        if m_tbl:
            tname = m_tbl.group("table")
            col_lines: list[str] = []
            i += 1
            while i < len(lines):
                ln = lines[i]
                if re.match(r"^\s*\)\s*;\s*$", ln):
                    break
                # ignore comment/TOC lines inside blocks (rare)
                if ln.strip().startswith("--"):
                    i += 1
                    continue
                col_lines.append(ln)
                i += 1
            tables[tname] = ExpectedTable(name=tname, column_lines=col_lines)
            # jump past closing );
            while i < len(lines) and not re.match(r"^\s*\)\s*;\s*$", lines[i]):
                i += 1
            i += 1
            continue

        m_idx = _RE_CREATE_INDEX.match(line)
        if m_idx:
            indexes.append(
                ExpectedIndex(
                    name=m_idx.group("name"),
                    table=m_idx.group("table"),
                    method=m_idx.group("method"),
                    expr=m_idx.group("expr").strip(),
                )
            )
            i += 1
            continue

        m_alter = _RE_ALTER_TABLE_ONLY.match(line)
        if m_alter:
            tname = m_alter.group("table")
            # next non-empty line might be ADD CONSTRAINT ...
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                ln = lines[j]
                m_pk = _RE_ADD_PK.match(ln)
                if m_pk:
                    constraints.append(
                        ExpectedConstraint(
                            name=m_pk.group("name"),
                            table=tname,
                            ddl_fragment=f"ADD CONSTRAINT {m_pk.group('name')} PRIMARY KEY ({m_pk.group('cols').strip()});",
                        )
                    )
                    i = j + 1
                    continue
                m_fk = _RE_ADD_FK.match(ln)
                if m_fk:
                    constraints.append(
                        ExpectedConstraint(
                            name=m_fk.group("name"),
                            table=tname,
                            ddl_fragment=(
                                f"ADD CONSTRAINT {m_fk.group('name')} FOREIGN KEY ({m_fk.group('cols').strip()}) "
                                f"REFERENCES public.{m_fk.group('ref_table')}({m_fk.group('ref_cols').strip()});"
                            ),
                        )
                    )
                    i = j + 1
                    continue
        i += 1

    return tables, constraints, indexes


def parse_expected_from_patch_sql(sql_text: str) -> tuple[dict[str, ExpectedTable], list[ExpectedConstraint], list[ExpectedIndex]]:
    """
    Lightweight parser for patch files that already use IF NOT EXISTS.
    We only care about CREATE TABLE/INDEX and constraints that are inline in CREATE TABLE.
    For patches we just return empty here and let the patch SQL run as-is.
    """
    return {}, [], []


def _fetch_existing(conn) -> tuple[set[str], dict[str, set[str]], set[str], set[str]]:
    """
    Returns:
    - tables: set of table names in public
    - columns: dict[table] -> set[column]
    - constraints: set of constraint names in public
    - indexes: set of index names in public
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT tablename
            FROM pg_catalog.pg_tables
            WHERE schemaname = 'public'
            """
        )
        tables = {r[0] for r in cur.fetchall()}

        cur.execute(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            """
        )
        cols: dict[str, set[str]] = {}
        for t, c in cur.fetchall():
            cols.setdefault(t, set()).add(c)

        cur.execute(
            """
            SELECT conname
            FROM pg_catalog.pg_constraint c
            JOIN pg_catalog.pg_namespace n ON n.oid = c.connamespace
            WHERE n.nspname = 'public'
            """
        )
        constraints = {r[0] for r in cur.fetchall()}

        cur.execute(
            """
            SELECT indexname
            FROM pg_catalog.pg_indexes
            WHERE schemaname = 'public'
            """
        )
        indexes = {r[0] for r in cur.fetchall()}

    return tables, cols, constraints, indexes


def _extract_column_name(col_def_line: str) -> Optional[str]:
    """
    From a line like:
      'idarticle integer NOT NULL,'
    return 'idarticle'
    """
    s = col_def_line.strip()
    if not s or s.startswith("--"):
        return None
    # quoted names are rare in this dump (except column named "user")
    if s.startswith('"'):
        m = re.match(r'^"([^"]+)"\s+(.+)$', s)
        return m.group(1) if m else None
    m = re.match(r"^([a-zA-Z0-9_]+)\s+(.+)$", s)
    return m.group(1) if m else None


def _col_add_ddl(table: str, col_line: str) -> Optional[str]:
    col_line = col_line.strip()
    if not col_line or col_line.startswith("--"):
        return None
    col_line = re.sub(r",\s*$", "", col_line)
    return f"ALTER TABLE public.{table} ADD COLUMN IF NOT EXISTS {col_line};"


def _run_sql(conn, sql: str, *, dry_run: bool, verbose: bool) -> None:
    sql = sql.strip()
    if not sql:
        return
    if verbose or dry_run:
        print(sql)
    if dry_run:
        return
    with conn.cursor() as cur:
        cur.execute(sql)


def _run_patch_file(conn, path: str, *, dry_run: bool, verbose: bool) -> None:
    with open(path, "r", encoding="utf-8") as f:
        txt = f.read()

    def _strip_full_line_comments(raw: str) -> str:
        out: list[str] = []
        for ln in raw.splitlines():
            if ln.lstrip().startswith("--"):
                continue
            out.append(ln)
        return "\n".join(out)

    def _split_sql_statements(raw: str) -> list[str]:
        """
        Split on ';' while respecting dollar-quoted blocks ($$...$$ or $tag$...$tag$).
        Good enough for our patch files and generated patches.
        """
        text = _strip_full_line_comments(raw)
        statements: list[str] = []
        buf: list[str] = []
        i = 0
        in_quote: str | None = None

        while i < len(text):
            if in_quote is not None:
                if text.startswith(in_quote, i):
                    buf.append(in_quote)
                    i += len(in_quote)
                    in_quote = None
                else:
                    buf.append(text[i])
                    i += 1
                continue

            if text[i] == "$":
                if i + 1 < len(text) and text[i + 1] == "$":
                    in_quote = "$$"
                    buf.append("$$")
                    i += 2
                    continue
                m = re.match(r"\$([a-zA-Z_][a-zA-Z0-9_]*)\$", text[i:])
                if m:
                    in_quote = m.group(0)
                    buf.append(in_quote)
                    i += len(in_quote)
                    continue

            if text[i] == ";":
                stmt = "".join(buf).strip()
                if stmt:
                    statements.append(stmt)
                buf = []
                i += 1
                continue

            buf.append(text[i])
            i += 1

        stmt = "".join(buf).strip()
        if stmt:
            statements.append(stmt)
        return statements

    statements = _split_sql_statements(txt)
    for st in statements:
        _run_sql(conn, st.rstrip() + ";", dry_run=dry_run, verbose=verbose)


def build_plan(
    expected_tables: dict[str, ExpectedTable],
    expected_constraints: list[ExpectedConstraint],
    expected_indexes: list[ExpectedIndex],
    existing_tables: set[str],
    existing_columns: dict[str, set[str]],
    existing_constraints: set[str],
    existing_indexes: set[str],
    *,
    skip_create_tables: set[str] | None = None,
    include_create_tables: bool = True,
    include_columns: bool = True,
    include_constraints: bool = True,
    include_indexes: bool = True,
) -> list[str]:
    plan: list[str] = []
    skip_create_tables = skip_create_tables or set()

    # tables + columns
    for tname, tbl in sorted(expected_tables.items(), key=lambda x: x[0]):
        if tname not in existing_tables:
            if tname in skip_create_tables:
                continue
            if include_create_tables:
                plan.append(tbl.create_ddl())
            continue

        if include_columns:
            present_cols = existing_columns.get(tname, set())
            for col_line in tbl.column_lines:
                col_name = _extract_column_name(col_line)
                if not col_name:
                    continue
                if col_name not in present_cols:
                    ddl = _col_add_ddl(tname, col_line)
                    if ddl:
                        plan.append(ddl)

    # constraints
    if include_constraints:
        for c in expected_constraints:
            if c.name in existing_constraints:
                continue
            # Avoid adding constraints to tables that don't exist yet (and are meant
            # to be created by patches later).
            if c.table not in existing_tables and c.table in skip_create_tables:
                continue
            plan.append(c.ddl())

    # indexes
    if include_indexes:
        for idx in expected_indexes:
            if idx.name in existing_indexes:
                continue
            if idx.table not in existing_tables and idx.table in skip_create_tables:
                continue
            plan.append(idx.ddl())

    return plan


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Sync PostgreSQL schema (additive, non-destructive).")
    ap.add_argument("--project-root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--dry-run", action="store_true", help="Print DDL without executing it.")
    ap.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run).")
    ap.add_argument("--verbose", action="store_true", help="Print statements as they are executed.")
    ap.add_argument(
        "--extra-sql",
        action="append",
        default=[],
        help="Additional SQL file path(s) to run after syncing.",
    )
    args = ap.parse_args(argv)

    project_root = os.path.abspath(args.project_root)
    dry_run = args.dry_run or not args.apply

    db = _load_db_config(project_root)
    print(f"[db-sync] Target: {db['host']}:{db['port']} db={db['database']} user={db['user']}")
    print(f"[db-sync] Mode: {'DRY-RUN' if dry_run else 'APPLY'} (transaction)")

    sql_files = _iter_expected_sql_files(project_root, args.extra_sql)
    if not sql_files:
        print("[db-sync] ❌ No schema files found.")
        return 2

    # Parse expected from Structure database.sql only; patch sql is applied verbatim later.
    expected_tables: dict[str, ExpectedTable] = {}
    expected_constraints: list[ExpectedConstraint] = []
    expected_indexes: list[ExpectedIndex] = []

    structure_path = os.path.join(project_root, "Structure database.sql")
    if os.path.exists(structure_path):
        with open(structure_path, "r", encoding="utf-8") as f:
            txt = f.read()
        t, c, idx = parse_expected_from_structure_sql(txt)
        expected_tables.update(t)
        expected_constraints.extend(c)
        expected_indexes.extend(idx)
        print(f"[db-sync] Parsed expected from dump: {len(t)} tables, {len(c)} constraints, {len(idx)} indexes")

    # Identify which tables are created by curated patch files.
    patch_tables: set[str] = set()
    for p in sql_files:
        if os.path.normcase(p) == os.path.normcase(structure_path):
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                patch_tables |= _patch_tables_from_sql(f.read())
        except Exception:
            pass

    # Connect
    conn = psycopg2.connect(
        host=db["host"],
        user=db["user"],
        password=db["password"],
        database=db["database"],
        port=db["port"],
        connect_timeout=10,
    )
    try:
        conn.autocommit = False
        existing_tables, existing_columns, existing_constraints, existing_indexes = _fetch_existing(conn)
        print(f"[db-sync] Existing: {len(existing_tables)} tables, {sum(len(v) for v in existing_columns.values())} columns")

        # Phase 1: create missing tables from dump (but avoid tables defined by patches).
        plan = build_plan(
            expected_tables,
            expected_constraints,
            expected_indexes,
            existing_tables,
            existing_columns,
            existing_constraints,
            existing_indexes,
            skip_create_tables=patch_tables,
            include_create_tables=True,
            include_columns=False,
            include_constraints=False,
            include_indexes=False,
        )

        print(f"[db-sync] Planned DDL statements: {len(plan)}")

        for st in plan:
            _run_sql(conn, st, dry_run=dry_run, verbose=args.verbose)

        # Run optional extra SQL files (idempotent) after dump-driven creates
        for p in sql_files:
            if os.path.normcase(p) == os.path.normcase(structure_path):
                continue
            print(f"[db-sync] Patch: {os.path.relpath(p, project_root)}")
            _run_patch_file(conn, p, dry_run=dry_run, verbose=args.verbose)

        # Phase 2: re-scan after patches and add missing columns/constraints/indexes.
        # In DRY-RUN, patches are not executed; re-scanning would produce misleading plans.
        if not dry_run:
            existing_tables, existing_columns, existing_constraints, existing_indexes = _fetch_existing(conn)
            plan2 = build_plan(
                expected_tables,
                expected_constraints,
                expected_indexes,
                existing_tables,
                existing_columns,
                existing_constraints,
                existing_indexes,
                skip_create_tables=set(),
                include_create_tables=True,
                include_columns=True,
                include_constraints=True,
                include_indexes=True,
            )
            if plan2:
                print(f"[db-sync] Planned DDL statements (phase2): {len(plan2)}")
            for st in plan2:
                _run_sql(conn, st, dry_run=dry_run, verbose=args.verbose)
        else:
            print("[db-sync] (dry-run) Phase2 skipped because patches are not executed in dry-run.")

        if dry_run:
            conn.rollback()
            print("[db-sync] DRY-RUN complete (rolled back).")
        else:
            conn.commit()
            print("[db-sync] ✅ APPLY complete (committed).")
        return 0
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"[db-sync] ❌ Failed: {e}")
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

