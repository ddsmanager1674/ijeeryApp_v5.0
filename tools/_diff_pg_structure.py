"""Parse pg_dump CREATE TABLE blocks and diff current vs target schema."""
from __future__ import annotations

import re
import sys
from pathlib import Path


def extract_tables(sql: str) -> dict[str, list[str]]:
    """table_name -> list of raw column definition lines (trimmed, no trailing comma)."""
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
    """Collapse whitespace for comparison."""
    return re.sub(r"\s+", " ", s.strip())


def col_name(line: str) -> str:
    """First token is column name (may be quoted)."""
    line = line.strip()
    if line.startswith('"'):
        end = line.find('"', 1)
        return line[: end + 1] if end > 0 else line.split()[0]
    return line.split()[0]


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    current_path = root / "temp" / "strcuture-sg.sql"
    target_path = root / "Structure database.sql"
    cur = extract_tables(current_path.read_text(encoding="utf-8", errors="replace"))
    tgt = extract_tables(target_path.read_text(encoding="utf-8", errors="replace"))

    only_target = sorted(set(tgt) - set(cur))
    only_current = sorted(set(cur) - set(tgt))

    lines: list[str] = []
    lines.append("-- Migration: aligner la base actuelle (temp/strcuture-sg.sql)")
    lines.append("-- sur le schéma cible (Structure database.sql)")
    lines.append("-- Généré automatiquement; vérifier avant exécution.")
    lines.append("")
    lines.append("BEGIN;")
    lines.append("")

    if only_target:
        lines.append("-- Tables présentes dans Structure database.sql mais absentes de la base actuelle:")
        for t in only_target:
            lines.append(f"--   {t}")
        lines.append("")

    if only_current:
        lines.append("-- Tables dans la base actuelle mais absentes du fichier cible (non modifiées ici):")
        for t in only_current:
            lines.append(f"--   {t}")
        lines.append("")

    for table in sorted(set(cur) & set(tgt)):
        cur_cols = {normalize_col(c): c for c in cur[table]}
        tgt_cols = {normalize_col(c): c for c in tgt[table]}
        cur_by_name = {col_name(c): c for c in cur[table]}
        tgt_by_name = {col_name(c): c for c in tgt[table]}

        # Column order in target
        tgt_order = [col_name(c) for c in tgt[table]]

        for cn in tgt_order:
            if cn not in cur_by_name:
                defn = tgt_by_name[cn]
                lines.append(f"ALTER TABLE public.{table} ADD COLUMN IF NOT EXISTS {defn};")

        for cn in cur_by_name:
            if cn not in tgt_by_name:
                lines.append(
                    f"-- Colonne en trop dans la base actuelle (à supprimer manuellement si souhaité): "
                    f"public.{table}.{cn}"
                )

        for cn in tgt_order:
            if cn not in cur_by_name or cn not in tgt_by_name:
                continue
            c_raw = cur_by_name[cn]
            t_raw = tgt_by_name[cn]
            if normalize_col(c_raw) != normalize_col(t_raw):
                lines.append(
                    f"-- DIFF public.{table} {cn}:"
                )
                lines.append(f"--   actuel:  {c_raw}")
                lines.append(f"--   cible:   {t_raw}")
                lines.append(
                    "--   => ALTER TYPE / DEFAULT / NOT NULL à ajuster manuellement si nécessaire."
                )

    lines.append("")
    lines.append("COMMIT;")
    out = root / "sql" / "patch_structure_sg_to_reference.sql"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}")
    print(f"Tables current: {len(cur)}, target: {len(tgt)}")
    print(f"Only in target: {only_target}")
    print(f"Only in current: {only_current}")


if __name__ == "__main__":
    main()
