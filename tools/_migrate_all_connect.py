"""Migrate remaining psycopg2.connect to connect_page_db in pages/."""
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..", "pages")
SKIP = {"vente", "avoir", "__pycache__"}

STANDARD_CONNECT_DB_BODY = """        try:
            from pages.db_helper import connect_page_db
            shared = (
                getattr(self, "_db_conn_shared", None)
                or getattr(self, "_db_conn_initial", None)
                or getattr(self, "db_conn", None)
            )
            return connect_page_db(shared)
"""

# Files: replace entire connect_db try block (from try: to except) - pattern per file
SIMPLE_REPLACEMENTS = [
    # peremption cfg one-liner host
    (
        r"    def connect_db\(self\):\n        try:\n            with open\(get_config_path\('config\.json'\)\) as f:\n                cfg = json\.load\(f\)\['database'\]\n            return psycopg2\.connect\(\n                host=cfg\['host'\], user=cfg\['user'\],\n                password=cfg\['password'\],\n                database=cfg\['database'\], port=cfg\['port'\]\)\n        except Exception as e:\n            messagebox\.showerror\(\"Connexion\", f\"Erreur : \{e\}\"\)\n            return None",
        """    def connect_db(self):
        try:
            from pages.db_helper import connect_page_db
            return connect_page_db()
        except Exception as e:
            messagebox.showerror("Connexion", f"Erreur : {e}")
            return None""",
    ),
]

# Global replacements (any file)
GLOBAL = [
    (
        r"return psycopg2\.connect\(\s*host=cfg\['host'\], user=cfg\['user'\],\s*password=cfg\['password'\],\s*database=cfg\['database'\], port=cfg\['port'\]\s*\)",
        "from pages.db_helper import connect_page_db\n            return connect_page_db()",
    ),
    (
        r"return psycopg2\.connect\(\s*host=db\[\"host\"\],\s*user=db\[\"user\"\],\s*password=db\[\"password\"\],\s*database=db\[\"database\"\],\s*port=db\[\"port\"\],\s*connect_timeout=5,\s*\)",
        "from pages.db_helper import connect_page_db\n        return connect_page_db()",
    ),
    (
        r"self\.conn = psycopg2\.connect\(\s*host=self\.db_params\['host'\],\s*user=self\.db_params\['user'\],\s*password=self\.db_params\['password'\],\s*database=self\.db_params\['database'\],\s*port=self\.db_params\['port'\],\s*client_encoding='UTF8'\s*\)",
        "from pages.db_helper import connect_page_db\n            self.conn = connect_page_db()",
    ),
    (
        r"self\.conn = psycopg2\.connect\(\s*host=db_params\['host'\],\s*user=db_params\['user'\],\s*password=db_params\['password'\],\s*database=db_params\['database'\],\s*port=db_params\['port'\]\s*\)",
        "from pages.db_helper import connect_page_db\n            self.conn = connect_page_db()",
    ),
    (
        r"self\.conn = psycopg2\.connect\(\*\*self\.db_params\)",
        "from pages.db_helper import connect_page_db\n            self.conn = connect_page_db()",
    ),
    (
        r"conn = psycopg2\.connect\(\s*host=db_config\['host'\],\s*user=db_config\['user'\],\s*password=db_config\['password'\],\s*database=db_config\['database'\],\s*port=db_config\['port'\]\s*\)",
        "from pages.db_helper import connect_page_db\n            conn = connect_page_db()",
    ),
    (
        r"return psycopg2\.connect\(\s*host=db_config\['host'\], user=db_config\['user'\],\s*password=db_config\['password'\],\s*database=db_config\['database'\],\s*port=db_config\['port'\]\s*\)",
        "from pages.db_helper import connect_page_db\n            return connect_page_db()",
    ),
]


def patch_connect_db_function(text: str) -> str:
    """Replace connect_db methods that still use psycopg2.connect inside."""

    def replacer(m):
        indent = m.group(1)
        except_block = m.group(2)
        return (
            f"{indent}def connect_db(self):\n"
            f"{indent}    try:\n"
            f"{indent}        from pages.db_helper import connect_page_db\n"
            f"{indent}        shared = (\n"
            f"{indent}            getattr(self, '_db_conn_shared', None)\n"
            f"{indent}            or getattr(self, '_db_conn_initial', None)\n"
            f"{indent}            or getattr(self, 'db_conn', None)\n"
            f"{indent}        )\n"
            f"{indent}        return connect_page_db(shared)\n"
            f"{except_block}"
        )

    pattern = re.compile(
        r"(\s*)def connect_db\(self\):\s*\n"
        r"((?:\s{4,}.*\n)*?)"
        r"(?=\s*def |\s*class |\Z)",
        re.MULTILINE,
    )

    def process_match(m):
        body = m.group(2)
        if "psycopg2.connect" not in body and "connect_page_db" in body:
            return m.group(0)
        if "psycopg2.connect" not in body:
            return m.group(0)
        indent = m.group(1)
        # preserve except clause from original
        except_m = re.search(r"(\s+except[^\n]+:.*?(?=\n\s*def |\n\s*class |\Z))", body, re.DOTALL)
        if except_m:
            except_part = except_m.group(1)
        else:
            except_part = f"{indent}    except Exception as e:\n{indent}        return None\n"
        return (
            f"{indent}def connect_db(self):\n"
            f"{indent}    try:\n"
            f"{indent}        from pages.db_helper import connect_page_db\n"
            f"{indent}        shared = (\n"
            f"{indent}            getattr(self, '_db_conn_shared', None)\n"
            f"{indent}            or getattr(self, '_db_conn_initial', None)\n"
            f"{indent}        )\n"
            f"{indent}        return connect_page_db(shared)\n"
            f"{except_part}"
        )

    # Simpler: only replace if psycopg2.connect in connect_db block
    new_text = text
    for m in list(pattern.finditer(text)):
        block = m.group(0)
        if "psycopg2.connect" in block:
            new_block = process_match(m)
            new_text = new_text.replace(block, new_block, 1)
    return new_text


def main():
    total = 0
    for dirpath, dirnames, files in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        for fn in files:
            if not fn.endswith(".py") or fn == "db_helper.py":
                continue
            path = os.path.join(dirpath, fn)
            with open(path, encoding="utf-8", errors="ignore") as f:
                text = f.read()
            if "psycopg2.connect" not in text:
                continue
            orig = text
            for old, new in GLOBAL:
                text, c = re.subn(old, new, text, flags=re.DOTALL)
                total += c
            for old, new in SIMPLE_REPLACEMENTS:
                text, c = re.subn(old, new, text, flags=re.DOTALL)
                total += c
            text = patch_connect_db_function(text)
            # Last resort: any remaining return psycopg2.connect(**x)
            text, c = re.subn(
                r"return psycopg2\.connect\([^)]+\)",
                "from pages.db_helper import connect_page_db\n            return connect_page_db()",
                text,
            )
            total += c
            if text != orig:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"updated {path}")
    print(f"done, subs: {total}")


if __name__ == "__main__":
    main()
