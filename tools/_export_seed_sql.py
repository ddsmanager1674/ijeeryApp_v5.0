#!/usr/bin/env python3
"""Exporte menus + autorisations admin depuis sarah_gros vers SQL."""
import json
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

ROOT = Path(__file__).resolve().parents[1]
cfg = json.load(open(ROOT / "config.json", encoding="utf-8"))["database"]
conn = psycopg2.connect(**cfg)
cur = conn.cursor(cursor_factory=RealDictCursor)

cur.execute("SELECT id, designationmenu, page FROM tb_menu ORDER BY id")
menus = cur.fetchall()
cur.execute(
    "SELECT idfonction, idmenu FROM tb_autorisation WHERE idfonction = 1 ORDER BY idmenu"
)
auths = cur.fetchall()

def esc(s):
    if s is None:
        return "NULL"
    return "'" + str(s).replace("'", "''") + "'"

lines = ["-- Menus exportés depuis sarah_gros", "INSERT INTO tb_menu (id, designationmenu, page) VALUES"]
for i, m in enumerate(menus):
    sep = "," if i < len(menus) - 1 else ";"
    lines.append(f"  ({m['id']}, {esc(m['designationmenu'])}, {esc(m['page'])}){sep}")

lines.append("")
lines.append("INSERT INTO tb_autorisation (idfonction, idmenu) VALUES")
for i, a in enumerate(auths):
    sep = "," if i < len(auths) - 1 else ";"
    lines.append(f"  ({a['idfonction']}, {a['idmenu']}){sep}")

out = ROOT / "sql" / "_menus_admin_export.sql"
out.write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote {out} ({len(menus)} menus, {len(auths)} autorisations)")
conn.close()
