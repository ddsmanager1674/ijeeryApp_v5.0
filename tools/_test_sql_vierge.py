#!/usr/bin/env python3
"""Teste schema + seed sur une base temporaire ijeery_vierge_test."""
import json
from pathlib import Path

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from sql_execute import execute_sql_file

ROOT = Path(__file__).resolve().parents[1]
cfg = json.load(open(ROOT / "config.json", encoding="utf-8"))["database"]
TEST_DB = "ijeery_vierge_test"

def main():
    admin = {k: v for k, v in cfg.items() if k != "database"}
    admin["database"] = "postgres"
    conn = psycopg2.connect(**admin)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute(f"SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB,))
    if cur.fetchone():
        cur.execute(f"DROP DATABASE {TEST_DB}")
    cur.execute(f"CREATE DATABASE {TEST_DB}")
    cur.close()
    conn.close()

    conn = psycopg2.connect(**{**cfg, "database": TEST_DB})
    print("Applying schema...")
    n1 = execute_sql_file(conn, ROOT / "sql" / "ijeery_schema_vide.sql")
    print(f"  {n1} statements")
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
    )
    print(f"  tables public: {cur.fetchone()[0]}")
    cur.close()
    print("Applying seed...")
    n2 = execute_sql_file(conn, ROOT / "sql" / "ijeery_seed_minimal.sql")
    print(f"  {n2} statements")

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM tb_users WHERE username='admin' AND active=1 AND deleted=0")
    assert cur.fetchone()[0] == 1
    cur.execute("SELECT COUNT(*) FROM tb_menu")
    n_menu = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM tb_autorisation WHERE idfonction=1")
    n_auth = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM tb_vente")
    n_vente = cur.fetchone()[0]
    print(f"OK menus={n_menu} autorisations_admin={n_auth} ventes={n_vente}")
    conn.close()
    print("Test passed.")

if __name__ == "__main__":
    main()
