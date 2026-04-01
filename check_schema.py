import json
import psycopg2
from resource_utils import get_config_path

try:
    # Charger la config
    with open(get_config_path('config.json'), 'r') as f:
        config = json.load(f)
    
    db_config = config['database']
    
    conn = psycopg2.connect(
        host=db_config['host'],
        user=db_config['user'],
        password=db_config['password'],
        database=db_config['database'],
        port=db_config['port']
    )
    cur = conn.cursor()

    # Obtenir les colonnes de tb_transfert
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'tb_transfert'
        ORDER BY ordinal_position
    """)

    cols = cur.fetchall()
    print("=== Colonnes de tb_transfert ===")
    for col in cols:
        print(f"  - {col[0]}")

    conn.close()
except Exception as e:
    print(f"Erreur: {e}")
