"""One-off schema inspection for sarah_gros (config.json)."""
import json
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parent.parent
with open(ROOT / "config.json", encoding="utf-8") as f:
    d = json.load(f)["database"]

conn = psycopg2.connect(
    host=d["host"],
    port=d["port"],
    dbname=d["database"],
    user=d["user"],
    password=d["password"],
)
cur = conn.cursor()
cur.execute("SELECT current_database(), version()::text")
print("connected:", cur.fetchone())

tables = (
    "tb_magasin",
    "tb_livraisoncli_attente",
    "tb_categoriepersonnel",
    "tb_postepersonnel",
    "tb_personnel",
    "tb_transporteur",
    "tb_commande",
)
cur.execute(
    """
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    AND table_name = ANY(%s)
    ORDER BY table_name
    """,
    (list(tables),),
)
print("present tables:", [r[0] for r in cur.fetchall()])


def col_list(name: str):
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (name,),
    )
    return [r[0] for r in cur.fetchall()]


for t in tables:
    cur.execute(
        """
        SELECT 1 FROM information_schema.tables
        WHERE table_schema='public' AND table_name=%s
        """,
        (t,),
    )
    if not cur.fetchone():
        print(f"{t}: MISSING")
        continue
    print(f"{t}: {col_list(t)}")

cur.close()
conn.close()
