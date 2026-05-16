# -*- coding: utf-8 -*-
"""Corrige les imports connect_page_db mal indentés par le patch automatique."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "pages"

PATTERNS = [
    (re.compile(r"^[ \t]{20,}from pages\.db_helper import connect_page_db", re.M),
     "            from pages.db_helper import connect_page_db"),
]


def fix_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    orig = text
    for rx, repl in PATTERNS:
        text = rx.sub(repl, text)
    if text != orig:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main():
    changed = []
    for py in PAGES.rglob("*.py"):
        if py.name == "db_helper.py":
            continue
        if fix_file(py):
            changed.append(py.relative_to(ROOT))
    print(f"Fixed {len(changed)} files:")
    for p in changed:
        print(f"  {p}")


if __name__ == "__main__":
    main()
