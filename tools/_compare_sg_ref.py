"""One-off: diff temp/structure--sg.sql vs Structure database.sql (CREATE TABLE only)."""
from __future__ import annotations

import re
from pathlib import Path


def extract_tables(sql: str) -> dict[str, list[str]]:
    tables: dict[str, list[str]] = {}
    pattern = re.compile(
        r"CREATE TABLE public\.(\w+)\s*\(\s*(.*?)\s*\)\s*;",
        re.DOTALL | re.IGNORECASE,
    )
    for m in pattern.finditer(sql):
        name = m.group(1)
        body = m.group(2)
        cols: list[str] = []
        for line in body.splitlines():
            s = line.strip().rstrip(",")
            if not s or s.upper().startswith("CONSTRAINT "):
                continue
            cols.append(s)
        tables[name] = cols
    return tables


def normalize_col(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())


def col_name(line: str) -> str:
    line = line.strip()
    if line.startswith('"'):
        end = line.find('"', 1)
        return line[: end + 1] if end > 0 else line.split()[0]
    return line.split()[0]


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    cur = extract_tables(
        (root / "temp" / "structure--sg.sql").read_text(encoding="utf-8", errors="replace")
    )
    tgt = extract_tables(
        (root / "Structure database.sql").read_text(encoding="utf-8", errors="replace")
    )

    only_tgt = sorted(set(tgt) - set(cur))
    only_cur = sorted(set(cur) - set(tgt))

    missing_cols: list[tuple[str, str, str]] = []
    extra_cols: list[tuple[str, str, str]] = []
    type_mismatch: list[tuple[str, str, str, str]] = []

    for table in sorted(set(cur) & set(tgt)):
        cur_by_name = {col_name(c): c for c in cur[table]}
        tgt_by_name = {col_name(c): c for c in tgt[table]}
        for cn in sorted(set(cur_by_name) | set(tgt_by_name)):
            if cn not in cur_by_name:
                missing_cols.append((table, cn, tgt_by_name[cn]))
            elif cn not in tgt_by_name:
                extra_cols.append((table, cn, cur_by_name[cn]))
            else:
                if normalize_col(cur_by_name[cn]) != normalize_col(tgt_by_name[cn]):
                    type_mismatch.append((table, cn, cur_by_name[cn], tgt_by_name[cn]))

    print("=== TABLES ONLY IN TARGET (Structure) — absent prod ===")
    for t in only_tgt:
        print(f"  {t}")
    print(f"count: {len(only_tgt)}\n")

    print("=== TABLES ONLY IN PROD (SG) — absent Structure ===")
    for t in only_cur:
        print(f"  {t}")
    print(f"count: {len(only_cur)}\n")

    print("=== MISSING COLUMNS IN PROD (ADD toward Structure) ===")
    for table, cn, defn in missing_cols:
        print(f"  {table}.{cn}")
    print(f"count: {len(missing_cols)}\n")

    print("=== EXTRA COLUMNS IN PROD (DROP or keep out of Structure) ===")
    for table, cn, defn in extra_cols:
        print(f"  {table}.{cn}: {defn[:100]}")
    print(f"count: {len(extra_cols)}\n")

    print("=== COLUMN DEFINITION MISMATCHES ===")
    for table, cn, c_raw, t_raw in type_mismatch:
        print(f"--- {table}.{cn}")
        print(f"  SG:  {c_raw}")
        print(f"  REF: {t_raw}")
    print(f"count: {len(type_mismatch)}")


if __name__ == "__main__":
    main()
