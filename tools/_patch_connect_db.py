"""Patch connect_db standard patterns to use pages.db_helper."""
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..", "pages")
SKIP_DIRS = {"vente", "avoir", "__pycache__"}
NEW = (
    "            from pages.db_helper import connect_page_db\n"
    "            return connect_page_db()"
)

PATTERNS = [
    re.compile(
        r"            with open\(get_config_path\('config\.json'\)\) as f:\n"
        r"                config = json\.load\(f\)\n"
        r"                db_config = config\['database'\]\n"
        r"            return psycopg2\.connect\(\n"
        r"                host=db_config\['host'\], user=db_config\['user'\],\n"
        r"                password=db_config\['password'\], database=db_config\['database'\],\n"
        r"                port=db_config\['port'\]\n?"
        r"            \)",
        re.M,
    ),
    re.compile(
        r"            with open\(get_config_path\('config\.json'\)\) as f:\n"
        r"                config = json\.load\(f\)\n"
        r"                db_config = config\['database'\]\n"
        r"            return psycopg2\.connect\(\n"
        r"                host=db_config\['host'\], user=db_config\['user'\],\n"
        r"                password=db_config\['password'\], database=db_config\['database'\],\n"
        r"                port=db_config\['port'\]\)",
        re.M,
    ),
    re.compile(
        r"            conn = psycopg2\.connect\(\n"
        r"                host=db_config\['host'\],\n?"
        r"                user=db_config\['user'\],\n?"
        r"                password=db_config\['password'\],\n?"
        r"                database=db_config\['database'\],\n?"
        r"                port=db_config\['port'\]\n?"
        r"            \)\n"
        r"            return conn",
        re.M,
    ),
    re.compile(
        r"            with open\(get_config_path\('config\.json'\)\) as f:\n"
        r"                config = json\.load\(f\)\n"
        r"                db_config = config\['database'\]\n"
        r"            return psycopg2\.connect\(\n"
        r"                host=db_config\['host'\],\n?"
        r"                user=db_config\['user'\],\n?"
        r"                password=db_config\['password'\],\n?"
        r"                database=db_config\['database'\],\n?"
        r"                port=db_config\['port'\]\n?"
        r"            \)",
        re.M,
    ),
    re.compile(
        r"            with open\(get_config_path\('config\.json'\)\) as f:\n"
        r"                cfg = json\.load\(f\)\['database'\]\n"
        r"            return psycopg2\.connect\(\n"
        r"                host=cfg\['host'\], user=cfg\['user'\],\n"
        r"                password=cfg\['password'\], database=cfg\['database'\],\n"
        r"                port=cfg\['port'\]\n?"
        r"            \)",
        re.M,
    ),
]

count = 0
for dirpath, dirnames, files in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
    for fn in files:
        if not fn.endswith(".py") or fn == "db_helper.py":
            continue
        path = os.path.join(dirpath, fn)
        with open(path, encoding="utf-8", errors="ignore") as f:
            text = f.read()
        if "psycopg2.connect" not in text:
            continue
        changed = False
        for pat in PATTERNS:
            ntext, n = pat.subn(NEW, text)
            if n:
                text = ntext
                count += n
                changed = True
        if changed:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"patched {path}")
print(f"total replacements: {count}")
