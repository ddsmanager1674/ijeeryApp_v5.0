#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from pathlib import Path

import psycopg2


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    db = json.loads((root / "config.json").read_text(encoding="utf-8"))["database"]
    conn = psycopg2.connect(
        host=db["host"],
        user=db["user"],
        password=db["password"],
        database=db["database"],
        port=db["port"],
        connect_timeout=10,
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, designationmenu FROM tb_menu")
            menus = cur.fetchall()
            print(f"tb_menu rows: {len(menus)}")

            cur.execute("SELECT idfonction, designationfonction FROM tb_fonction ORDER BY designationfonction")
            fonctions = cur.fetchall()
            print(f"tb_fonction rows: {len(fonctions)}")

            cur.execute("SELECT idfonction, idmenu FROM tb_autorisation")
            auth = cur.fetchall()
            print(f"tb_autorisation rows: {len(auth)}")
    finally:
        conn.close()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

