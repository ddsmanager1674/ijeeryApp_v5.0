# -*- coding: utf-8 -*-
"""Exécution d'un fichier .sql multi-instructions (psycopg2)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable


def _strip_comments(sql: str) -> str:
    """Retire les commentaires -- (hors chaînes, approximation suffisante pour nos dumps)."""
    lines = []
    for line in sql.splitlines():
        if line.strip().startswith("--"):
            continue
        lines.append(line)
    return "\n".join(lines)


def iter_sql_statements(sql: str) -> Iterable[str]:
    """
    Découpe un script SQL en instructions (point-virgule hors quotes simples).
    Adapté aux dumps pg_dump / scripts iJeery.
    """
    sql = _strip_comments(sql)
    buf: list[str] = []
    in_quote = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        if ch == "'" and not in_quote:
            in_quote = True
            buf.append(ch)
        elif ch == "'" and in_quote:
            if i + 1 < len(sql) and sql[i + 1] == "'":
                buf.append("''")
                i += 1
            else:
                in_quote = False
                buf.append(ch)
        elif ch == ";" and not in_quote:
            stmt = "".join(buf).strip()
            if stmt:
                yield stmt
            buf = []
        else:
            buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        yield tail


def execute_sql_file(conn, path: Path) -> int:
    """Exécute toutes les instructions d'un fichier ; retourne le nombre exécuté."""
    text = path.read_text(encoding="utf-8")
    cur = conn.cursor()
    n = 0
    for stmt in iter_sql_statements(text):
        cur.execute(stmt)
        n += 1
    cur.close()
    conn.commit()
    return n
