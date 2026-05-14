import json
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parent.parent
d = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))["database"]
conn = psycopg2.connect(
    host=d["host"],
    port=d["port"],
    dbname=d["database"],
    user=d["user"],
    password=d["password"],
    connect_timeout=10,
)
conn.autocommit = True
c = conn.cursor()
c.execute("SET lock_timeout = '8s'")
c.execute(
    "ALTER TABLE public.tb_magasin "
    "ADD COLUMN IF NOT EXISTS livraison_auto_client smallint NOT NULL DEFAULT 0"
)
print(c.statusmessage)
conn.close()
