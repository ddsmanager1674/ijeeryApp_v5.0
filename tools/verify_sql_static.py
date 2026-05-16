# -*- coding: utf-8 -*-
"""Compare les tables entre Structure database.sql et script_de_mis_a_jour.sql."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def extract_tables(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    tables = set()
    for m in re.finditer(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:public\.)?([a-zA-Z0-9_]+)",
        text,
        re.IGNORECASE,
    ):
        tables.add(m.group(1).lower())
    return tables


def main() -> int:
    structure = ROOT / "Structure database.sql"
    patch = ROOT / "sql" / "script_de_mis_a_jour.sql"
    if not structure.exists():
        print(f"Missing: {structure}")
        return 1
    if not patch.exists():
        print(f"Missing: {patch}")
        return 1

    s_tables = extract_tables(structure)
    p_tables = extract_tables(patch)

    print(f"Structure database.sql: {len(s_tables)} tables")
    print(f"script_de_mis_a_jour.sql: {len(p_tables)} tables")

    only_patch = sorted(p_tables - s_tables)
    in_both = sorted(p_tables & s_tables)

    if in_both:
        print("\nTables du script déjà présentes dans Structure:")
        for t in in_both:
            print(f"  - {t}")

    if only_patch:
        print("\nTables du script ABSENTES de Structure (patch prod ciblé):")
        for t in only_patch:
            print(f"  - {t}")
    else:
        print("\nToutes les tables du script sont couvertes par Structure.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
