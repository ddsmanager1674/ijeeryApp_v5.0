# -*- coding: utf-8 -*-
from stock_manager import StockManager

# Vos paramètres de connexion à la base de données (à adapter)
HOST = 'localhost'
PORT = 5432
DBNAME = 'sarah_gros'
USER = 'postgres'
PASSWORD = 'root'

# Variables fournies (exemples)
idArticle = 1
idUnite   = 1
idMagasin = 1   # mettre 0 pour tous les magasins

# 1. Créer une instance du gestionnaire de stock
sm = StockManager(host=HOST, port=PORT, dbname=DBNAME,
                  user=USER, password=PASSWORD)

try:
    # 2. Appeler la méthode pour obtenir le stock dans l'unité demandée
    resultat = sm.get_stock_article_par_unite(
        idarticle=idArticle,
        idunite=idUnite,
        idmagasin=idMagasin,   # 0 = tous les magasins
        date_fin=None           # None = aujourd'hui (stock actuel)
    )

    # 3. Afficher le résultat (ou l'utiliser selon vos besoins)
    print("=== Résultat du stock ===")
    print(f"Article : {resultat['designation']} (id {resultat['idarticle']})")
    print(f"Unité demandée : {resultat['designationunite']} (facteur {resultat['facteur_conversion']})")
    print(f"Magasin : {resultat['idmagasin']}")
    print(f"Stock en unité de base : {resultat['stock_en_base']} {resultat['unite_base']}")
    print(f"Stock dans l'unité '{resultat['designationunite']}' : {resultat['stock_dans_unite']} "
          f"(reste {resultat['reste_en_base']} {resultat['unite_base']})")
    print(f"Date de calcul : {resultat['date_calcul']}")

except Exception as e:
    print(f"Une erreur est survenue : {e}")

finally:
    # 4. Toujours fermer la connexion
    sm.fermer_connexion()