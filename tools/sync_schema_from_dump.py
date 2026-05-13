#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Génère et/ou applique un patch idempotent à partir d'un dump SQL (pg_dump).

Objectif:
- Créer les tables/séquences manquantes
- Ajouter les colonnes manquantes
- Appliquer les DEFAULT nextval(...) présents dans le dump

Usage:
  python tools/sync_schema_from_dump.py --dump "Structure database.sql" --out "sql/patch_from_structure_dump.sql" --apply
  python tools/sync_schema_from_dump.py --dump "Structure database.sql" --out "sql/patch_from_structure_dump.sql"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import psycopg2


ROOT = Path(__file__).resolve().parent.parent


@dataclass
class TableDef:
    name: str
    create_sql: str
    columns: list[tuple[str, str]]  # (colname, definition fragment)


def _read_db_cfg() -> dict:
    cfg_path = ROOT / "config.json"
    if not cfg_path.is_file():
        raise FileNotFoundError("config.json introuvable")
    with cfg_path.open(encoding="utf-8") as f:
        return json.load(f)["database"]


def _connect():
    db = _read_db_cfg()
    conn = psycopg2.connect(
        host=db["host"],
        user=db["user"],
        password=db["password"],
        database=db["database"],
        port=db["port"],
        connect_timeout=15,
    )
    conn.autocommit = True
    return conn


_RE_CREATE_TABLE = re.compile(
    r"CREATE TABLE public\.(?P<name>[a-zA-Z0-9_]+)\s*\(\n(?P<body>.*?)\n\);\n",
    re.DOTALL,
)
_RE_CREATE_SEQ = re.compile(
    r"CREATE SEQUENCE public\.(?P<name>[a-zA-Z0-9_]+)\n(?P<body>.*?);\n",
    re.DOTALL,
)
_RE_ALTER_COL_DEFAULT = re.compile(
    r"ALTER TABLE ONLY public\.(?P<table>[a-zA-Z0-9_]+)\s+ALTER COLUMN\s+(?P<col>[a-zA-Z0-9_]+)\s+SET DEFAULT\s+(?P<default>.+?);\n"
)


def _split_columns(body: str) -> list[tuple[str, str]]:
    """
    Parse très simple: colonnes = lignes indentées "name type ...".
    Ignore les contraintes en ligne de type "CONSTRAINT ..." (elles sont gérées ailleurs).
    """
    cols: list[tuple[str, str]] = []
    for raw_ln in body.splitlines():
        ln = raw_ln.strip()
        if not ln or ln.startswith("--"):
            continue
        if ln.upper().startswith("CONSTRAINT "):
            continue
        # retire la virgule finale
        if ln.endswith(","):
            ln = ln[:-1]
        # premier token = nom de colonne (peut être "user")
        m = re.match(r'("?[a-zA-Z_][a-zA-Z0-9_]*"?)\s+(.+)$', ln)
        if not m:
            continue
        col = m.group(1)
        rest = m.group(2).strip()
        cols.append((col, rest))
    return cols


def parse_dump(dump_text: str) -> tuple[list[TableDef], dict[str, str], list[tuple[str, str, str]]]:
    tables: list[TableDef] = []
    for m in _RE_CREATE_TABLE.finditer(dump_text):
        name = m.group("name")
        body = m.group("body")
        cols = _split_columns(body)
        create_sql = f"CREATE TABLE public.{name} (\n{body}\n);"
        tables.append(TableDef(name=name, create_sql=create_sql, columns=cols))

    sequences: dict[str, str] = {}
    for m in _RE_CREATE_SEQ.finditer(dump_text):
        name = m.group("name")
        body = m.group("body").rstrip()
        sequences[name] = f"CREATE SEQUENCE public.{name}\n{body};"

    defaults: list[tuple[str, str, str]] = []
    for m in _RE_ALTER_COL_DEFAULT.finditer(dump_text):
        defaults.append((m.group("table"), m.group("col"), m.group("default").strip()))

    return tables, sequences, defaults


def build_patch_sql(tables: list[TableDef], sequences: dict[str, str], defaults: list[tuple[str, str, str]]) -> str:
    out: list[str] = []
    out.append("-- Auto-généré depuis `Structure database.sql` (pg_dump)")
    out.append("-- Idempotent: crée tables/séquences/colonnes si absentes, applique defaults de séquence.")
    out.append("SET statement_timeout = 0;")
    out.append("SET lock_timeout = 0;")
    out.append("SET idle_in_transaction_session_timeout = 0;")
    out.append("")

    # 1) Séquences (avant defaults)
    for seq_name, seq_sql in sorted(sequences.items()):
        out.append(f"-- Sequence: {seq_name}")
        out.append(
            "DO $$\n"
            "BEGIN\n"
            f"  IF to_regclass('public.{seq_name}') IS NULL THEN\n"
            f"    EXECUTE {psycopg2.extensions.adapt(seq_sql).getquoted().decode('utf-8')};\n"
            "  END IF;\n"
            "END $$;"
        )
        out.append("")

    # 2) Tables + colonnes manquantes
    for t in sorted(tables, key=lambda x: x.name):
        out.append(f"-- Table: {t.name}")
        # CREATE TABLE IF NOT EXISTS est ok; on garde le SQL du dump.
        create_if_not_exists = t.create_sql.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ", 1)
        out.append(create_if_not_exists + ";")
        out.append("")
        # ADD COLUMN IF NOT EXISTS pour chaque colonne
        for col, rest in t.columns:
            out.append(
                f"ALTER TABLE IF EXISTS public.{t.name} "
                f"ADD COLUMN IF NOT EXISTS {col} {rest};"
            )
        out.append("")

    # 3) Defaults (souvent nextval('...'))
    out.append("-- Defaults (nextval...)")
    for table, col, default in defaults:
        out.append(
            f"ALTER TABLE IF EXISTS public.{table} "
            f"ALTER COLUMN {col} SET DEFAULT {default};"
        )
    out.append("")

    return "\n".join(out).rstrip() + "\n"


def apply_patch(conn, sql_text: str) -> None:
    cur = conn.cursor()
    # Découpage simple par ';' (le patch généré n'utilise pas de blocs dollar-quoted imbriqués,
    # sauf DO $$ ... $$; qui contient des ';' -> on ne split PAS: on exécute d'un bloc.
    cur.execute(sql_text)
    cur.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", required=True, help="Chemin dump SQL (ex: Structure database.sql)")
    ap.add_argument("--out", required=True, help="Chemin patch SQL de sortie")
    ap.add_argument("--apply", action="store_true", help="Appliquer le patch sur la base")
    args = ap.parse_args()

    os.chdir(ROOT)
    dump_path = Path(args.dump)
    if not dump_path.is_file():
        dump_path = ROOT / args.dump
    if not dump_path.is_file():
        print(f"Dump introuvable: {args.dump}", file=sys.stderr)
        return 1

    dump_text = dump_path.read_text(encoding="utf-8", errors="replace")
    tables, sequences, defaults = parse_dump(dump_text)
    patch_sql = build_patch_sql(tables, sequences, defaults)

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(patch_sql, encoding="utf-8")
    print(f"[OK] Patch généré: {out_path} | tables={len(tables)} sequences={len(sequences)} defaults={len(defaults)}")

    if args.apply:
        conn = _connect()
        try:
            apply_patch(conn, patch_sql)
        finally:
            conn.close()
        print("[OK] Patch appliqué sur la base.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

