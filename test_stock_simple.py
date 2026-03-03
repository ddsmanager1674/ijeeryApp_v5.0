import configparser
import sys
from typing import Dict, Any

from stock_manager import StockManager


# --- Variables configurables pour exécution directe ---
# Définissez ici les valeurs souhaitées puis lancez le script.
# Si vous laissez une des valeurs à None, le script utilisera les
# arguments de la ligne de commande.
# Exemple :
#   IDARTICLE = 5
#   IDUNITE   = 12
#   IDMAGASIN = 0   # 0 = tous magasins
IDARTICLE = 2986
IDUNITE = 4572
IDMAGASIN = 1

def _load_db_config() -> Dict[str, Any]:
    cfg = configparser.ConfigParser()
    cfg.read('config.ini')
    db = cfg['database'] if 'database' in cfg else {}
    return {
           'host': db.get('host', 'localhost'),
           'port': int(db.get('port', 5432)),
           'dbname': db.get('dbname', ''),
           'user': db.get('user', 'postgres'),
           'password': db.get('password', ''),
    }


def stock_unit_magasin(idarticle: int, idunite: int, idmagasin: int) -> Dict[str, Any]:
    """Stock de l'article dans l'unité demandée pour un magasin précis."""
    cfg = _load_db_config()
    sm = StockManager(host=cfg['host'], port=cfg['port'], dbname=cfg['dbname'], user=cfg['user'], password=cfg['password'])
    try:
        return sm.get_stock_article_par_unite(idarticle=idarticle, idunite=idunite, idmagasin=idmagasin)
    finally:
        sm.fermer_connexion()


def stock_unit_tous_magasins(idarticle: int, idunite: int) -> Dict[str, Any]:
    """Stock de l'article dans l'unité demandée, tous magasins confondus."""
    cfg = _load_db_config()
    sm = StockManager(host=cfg['host'], port=cfg['port'], dbname=cfg['dbname'], user=cfg['user'], password=cfg['password'])
    try:
        return sm.get_stock_article_par_unite(idarticle=idarticle, idunite=idunite, idmagasin=0)
    finally:
        sm.fermer_connexion()


if __name__ == '__main__':
    # Si les variables sont définies dans le fichier, on les utilise
    if IDARTICLE is not None and IDUNITE is not None and IDMAGASIN is not None:
        idarticle = int(IDARTICLE)
        idunite = int(IDUNITE)
        idmagasin = int(IDMAGASIN)
    else:
        if len(sys.argv) < 4:
            print('Usage: python test_stock_simple.py <idarticle> <idunite> <idmagasin>')
            print('Use <idmagasin>=0 to get stock for all magasins')
            sys.exit(1)

        idarticle = int(sys.argv[1])
        idunite = int(sys.argv[2])
        idmagasin = int(sys.argv[3])

    print('\n--- Résultat: stock pour magasin demandé ---')
    r1 = stock_unit_magasin(idarticle, idunite, idmagasin)
    print(r1)

    print('\n--- Résultat: stock pour tous magasins (agrégé) ---')
    r2 = stock_unit_tous_magasins(idarticle, idunite)
    print(r2)
