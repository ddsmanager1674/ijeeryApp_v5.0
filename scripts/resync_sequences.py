#!/usr/bin/env python3
"""
Resynchronise automatiquement les séquences PostgreSQL liées aux colonnes `id`.
Usage: python scripts/resync_sequences.py

Le script :
 - lit `config.json` via `resource_utils.get_config_path`
 - se connecte à la base (psycopg2)
 - recherche toutes les tables publiques ayant une colonne `id`
 - pour chaque table, obtient la séquence (pg_get_serial_sequence) et lance :
     SELECT setval(seq, COALESCE((SELECT MAX(id) FROM table), 0) + 1, true);
 - affiche un résumé

ATTENTION: exécuter en environnement sûr (backup recommandé).
"""

import json
import sys
import traceback
from psycopg2 import sql
import psycopg2

try:
    # Import helper from project to locate config
    from resource_utils import get_config_path
except Exception:
    def get_config_path(name):
        return name


def load_db_config():
    path = get_config_path('config.json')
    with open(path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    return cfg['database']


def main():
    try:
        db_cfg = load_db_config()
    except Exception as e:
        print(f"Erreur lecture config: {e}")
        sys.exit(1)

    conn = None
    try:
        conn = psycopg2.connect(**db_cfg)
        cursor = conn.cursor()

        # Récupérer toutes les tables publiques ayant une colonne 'id'
        cursor.execute("""
            SELECT table_name
            FROM information_schema.columns
            WHERE column_name = 'id' AND table_schema = 'public'
        """)
        tables = [r[0] for r in cursor.fetchall()]

        if not tables:
            print("Aucune table trouvée avec une colonne 'id' dans le schéma public.")
            return

        print(f"Tables examinées ({len(tables)}): {tables}")

        updated = []
        skipped = []

        for table in tables:
            # Obtenir le nom de la séquence associée à la colonne id (si existante)
            cursor.execute("SELECT pg_get_serial_sequence(%s, 'id')", (table,))
            seq = cursor.fetchone()[0]
            if not seq:
                skipped.append((table, None))
                continue

            # Calculer MAX(id)
            cursor.execute(sql.SQL("SELECT COALESCE(MAX(id), 0) FROM {};").format(sql.Identifier(table)))
            maxid = cursor.fetchone()[0] or 0
            nextval = maxid + 1

            # Mettre à jour la séquence
            cursor.execute("SELECT setval(%s, %s, true);", (seq, nextval))
            updated.append((table, seq, maxid, nextval))
            print(f"Sequence mise à jour pour table '{table}': seq={seq}, MAX(id)={maxid} -> next={nextval}")

        conn.commit()

        print("\nRésumé :")
        print(f"  mises à jour : {len(updated)}")
        for t, s, m, n in updated:
            print(f"    - {t}: seq={s}, MAX={m}, next={n}")
        print(f"  ignorées (pas de séquence) : {len(skipped)}")

    except Exception as e:
        if conn:
            conn.rollback()
        print("Erreur lors de la synchronisation des séquences:")
        traceback.print_exc()
        sys.exit(2)
    finally:
        if conn:
            cursor.close()
            conn.close()


if __name__ == '__main__':
    main()
