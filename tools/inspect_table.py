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
            cur.execute(
                """
                SELECT table_name, column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name IN ('tb_autorisation','tb_menu','tb_fonction')
                ORDER BY table_name, ordinal_position
                """
            )
            for r in cur.fetchall():
                print(r)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

