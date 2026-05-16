#!/usr/bin/env python3
"""Analyse sarah_gros pour tables de référence (seed minimal)."""
import json
import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
cfg = json.load(open(ROOT / "config.json", encoding="utf-8"))["database"]

SEED_TABLES = [
    "tb_fonction",
    "tb_menu",
    "tb_autorisation",
    "tb_users",
    "tb_magasin",
    "tb_typeoperation",
    "tb_modepaiement",
    "tb_typepmt",
    "tb_typeclient",
    "tb_unite",
    "tb_categoriearticle",
    "tb_categoriecompte",
    "tb_categoriepersonnel",
    "tb_postepersonnel",
    "tb_banque",
    "tb_infosociete",
    "tb_configdb",
    "tb_transporteur",
    "tb_codeautorisation",
]

conn = psycopg2.connect(**cfg)
cur = conn.cursor()

cur.execute(
    """
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    ORDER BY table_name
    """
)
all_tables = [r[0] for r in cur.fetchall()]
print("=== TABLES", len(all_tables), "===")

for t in SEED_TABLES:
    if t not in all_tables:
        print(f"MISSING {t}")
        continue
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    n = cur.fetchone()[0]
    cur.execute(
        """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (t,),
    )
    cols = cur.fetchall()
    print(f"\n--- {t} ({n} rows) ---")
    for c in cols[:20]:
        print(" ", c)
    if n and n <= 30:
        col_names = [c[0] for c in cols]
        cur.execute(f"SELECT * FROM {t} ORDER BY 1 LIMIT 30")
        for row in cur.fetchall():
            print("  ROW:", dict(zip(col_names, row)))

conn.close()
