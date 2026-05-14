"""Apply small schema deltas to DB from config.json (idempotent)."""
import json
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parent.parent

SQL_MAGASIN = """
ALTER TABLE public.tb_magasin
    ADD COLUMN IF NOT EXISTS livraison_auto_client smallint NOT NULL DEFAULT 0;
COMMENT ON COLUMN public.tb_magasin.livraison_auto_client IS
    '1 = BL auto (tb_livraisoncli) à la validation facture pour ce magasin ; 0 = manuel.';
"""


def main() -> None:
    with open(ROOT / "config.json", encoding="utf-8") as f:
        d = json.load(f)["database"]
    conn = psycopg2.connect(
        host=d["host"],
        port=d["port"],
        dbname=d["database"],
        user=d["user"],
        password=d["password"],
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(SQL_MAGASIN)
    print("tb_magasin.livraison_auto_client:", cur.statusmessage)
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
