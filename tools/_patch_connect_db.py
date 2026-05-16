"""Patch connect_db and common psycopg2.connect patterns to use pages.db_helper."""
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..", "pages")
SKIP_DIRS = {"vente", "avoir", "__pycache__"}
SKIP_FILES = {"db_helper.py", "ui_dialogs.py"}

NEW_RETURN = (
    "            from pages.db_helper import connect_page_db\n"
    "            return connect_page_db()"
)

NEW_ASSIGN_CONN = (
    "            from pages.db_helper import connect_page_db\n"
    "            conn = connect_page_db()"
)

NEW_SELF_CONN = (
    "            from pages.db_helper import connect_page_db\n"
    "            self.conn = connect_page_db()"
)

# Patterns inside connect_db / similar (return conn)
RETURN_PATTERNS = [
    # return psycopg2.connect(**db_config) or **config['database'] or **cfg
    re.compile(
        r"return psycopg2\.connect\(\*\*(?:db_config|cfg|config\['database'\])\)",
        re.M,
    ),
    re.compile(
        r"            return psycopg2\.connect\(\*\*db_config\)",
        re.M,
    ),
    re.compile(
        r"            return psycopg2\.connect\(\*\*config\['database'\]\)",
        re.M,
    ),
    re.compile(
        r"        return psycopg2\.connect\(\*\*config\['database'\]\)",
        re.M,
    ),
    re.compile(
        r"            return psycopg2\.connect\(\*\*cfg\)",
        re.M,
    ),
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
    re.compile(
        r"            with open\(get_config_path\('config\.json'\)\) as f:\n"
        r"                cfg = json\.load\(f\)\['database'\]\n"
        r"            return psycopg2\.connect\(\n"
        r"                host=cfg\['host'\], user=cfg\['user'\],\n"
        r"                password=cfg\['password'\], database=cfg\['database'\], port=cfg\['port'\]\)",
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
        r"            return psycopg2\.connect\(\*\*db_config\)",
        re.M,
    ),
    # StockLivraison root config path
    re.compile(
        r"            current_dir = os\.path\.dirname\(os\.path\.abspath\(__file__\)\)\n"
        r"            root_dir = os\.path\.dirname\(current_dir\)\n"
        r"            config_path = os\.path\.join\(root_dir, 'config\.json'\)\n"
        r" \n"
        r"            with open\(config_path, 'r'\) as f:\n"
        r"                config = json\.load\(f\)\n"
        r"                db_config = config\['database'\]\n"
        r"            return psycopg2\.connect\(\*\*db_config\)",
        re.M,
    ),
    re.compile(
        r"            with open\(config_path, 'r'(?:, encoding='utf-8')?\) as f:\n"
        r"                config = json\.load\(f\)\n"
        r"                db_config = config\['database'\]\n"
        r"            return psycopg2\.connect\(\*\*db_config\)",
        re.M,
    ),
    # multiline conn return
    re.compile(
        r"            conn = psycopg2\.connect\(\n"
        r"                host=db_config\['host'\], user=db_config\['user'\],\n"
        r"                password=db_config\['password'\],\n?"
        r"                database=db_config\['database'\],\n?"
        r"                port=db_config\['port'\],\n?"
        r"                client_encoding='UTF8'\n?"
        r"            \)\n"
        r"            return conn",
        re.M,
    ),
    re.compile(
        r"            conn = psycopg2\.connect\(\n"
        r"                host=db_config\['host'\], user=db_config\['user'\],\n"
        r"                password=db_config\['password'\],\n?"
        r"                database=db_config\['database'\], port=db_config\['port'\],\n?"
        r"                client_encoding='UTF8'\)\n"
        r"            return conn",
        re.M,
    ),
    re.compile(
        r"            conn = psycopg2\.connect\(\n"
        r"                host=db_config\['host'\],\n?"
        r"                user=db_config\['user'\],\n?"
        r"                password=db_config\['password'\],\n?"
        r"                database=db_config\['database'\],\n?"
        r"                port=db_config\['port'\]\n?"
        r"                \)\n"
        r"            return conn",
        re.M,
    ),
]

SELF_CONN_PATTERNS = [
    re.compile(r"self\.conn\s*=\s*psycopg2\.connect\(\*\*self\.db_params\)", re.M),
    re.compile(r"self\.conn\s*=\s*psycopg2\.connect\(\*\*db_params\)", re.M),
    re.compile(
        r"self\.conn = psycopg2\.connect\(\n"
        r"                host=db_params\['host'\], user=db_params\['user'\],\n"
        r"                password=db_params\['password'\], database=db_params\['database'\],\n"
        r"                port=db_params\['port'\]\n?"
        r"            \)",
        re.M,
    ),
]

CONN_ASSIGN_PATTERNS = [
    re.compile(r"conn = psycopg2\.connect\(\*\*config\['database'\]\)", re.M),
    re.compile(r"conn = psycopg2\.connect\(\*\*db_config\)", re.M),
    re.compile(r"conn = psycopg2\.connect\(\*\*self\.db_params\)", re.M),
]


def patch_file(path: str) -> int:
    with open(path, encoding="utf-8", errors="ignore") as f:
        text = f.read()

  # Skip vente pool internals - only file in vente/
    if "vente" in path.replace("\\", "/") and "SimpleConnectionPool" in text:
        return 0

    original = text
    n = 0

    for pat in RETURN_PATTERNS:
        text, c = pat.subn(NEW_RETURN, text)
        n += c

    for pat in SELF_CONN_PATTERNS:
        text, c = pat.subn(NEW_SELF_CONN, text)
        n += c

    for pat in CONN_ASSIGN_PATTERNS:
        text, c = pat.subn(NEW_ASSIGN_CONN, text)
        n += c

    # Generic return psycopg2.connect(**something) not yet caught
    text2, c = re.subn(
        r"(\n            )return psycopg2\.connect\(\*\*[^)]+\)",
        r"\1from pages.db_helper import connect_page_db\n\1return connect_page_db()",
        text,
    )
    if c:
        text = text2
        n += c

    if text != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return n


def main():
    total = 0
    for dirpath, dirnames, files in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in files:
            if not fn.endswith(".py") or fn in SKIP_FILES:
                continue
            path = os.path.join(dirpath, fn)
            if "psycopg2.connect" not in open(path, encoding="utf-8", errors="ignore").read():
                continue
            c = patch_file(path)
            if c:
                print(f"patched {path}: {c}")
                total += c
    print(f"total replacements: {total}")


if __name__ == "__main__":
    main()
