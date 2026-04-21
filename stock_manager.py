"""
=============================================================================
  STOCK MANAGER - Gestionnaire de stocks multi-magasins
  Auteur : Généré automatiquement
  Base de données : PostgreSQL
  Dépendance : psycopg2  (pip install psycopg2-binary)
=============================================================================

LISTE DES MÉTHODES DISPONIBLES :
─────────────────────────────────────────────────────────────────────────────

  CONNEXION & CONFIGURATION
  ─────────────────────────
  StockManager(host, port, dbname, user, password)
      → Instancie le gestionnaire et ouvre la connexion DB.
  fermer_connexion()
      → Ferme proprement la connexion à la base de données.

  INFORMATIONS SUR LES UNITÉS
  ───────────────────────────
  get_unites_article(idarticle)
      → Retourne la liste de toutes les unités d'un article avec
        leur facteur de conversion vers l'unité de base.

  get_facteur_conversion(idunite)
      → Retourne le facteur multiplicateur pour convertir une quantité
        exprimée dans l'unité donnée vers l'unité de base (niveau 0).

  STOCK PAR ARTICLE
  ─────────────────
  get_stock_article_base(idarticle, idmagasin=0, date_fin=None)
      → Stock total d'un article en UNITÉ DE BASE (niveau 0).
        idmagasin=0  → tous les magasins confondus.
        date_fin=None → jusqu'à aujourd'hui.

  get_stock_article_par_unite(idarticle, idunite, idmagasin=0, date_fin=None)
      → Stock d'un article converti dans l'unité choisie (idunite).
        Retourne aussi le reste non-converti (en unité de base).

  get_stock_article_par_magasin(idarticle, date_fin=None)
      → Stock d'un article ventilé magasin par magasin (en unité de base).

  get_stock_tous_articles(idmagasin=0, date_fin=None)
      → Stock de TOUS les articles (en unité de base),
        avec désignation, alerte, et flag "en alerte".

  MOUVEMENTS & HISTORIQUE
  ───────────────────────
  get_mouvements_article(idarticle, idmagasin=0,
                         type_mouvement=None,
                         date_debut=None, date_fin=None)
      → Historique détaillé de tous les mouvements d'un article.
        type_mouvement : 'ENTREE', 'SORTIE', ou None pour tout.
        Retourne chaque ligne avec : date, type, quantité (en unité de base),
        magasin et l'unité d'origine.

  get_mouvements_par_type(idarticle, type_operation,
                          idmagasin=0,
                          date_debut=None, date_fin=None)
      → Filtre les mouvements par type précis :
          'LIVRAISON', 'INVENTAIRE', 'AVOIR',
          'CHANGEMENT_ENTREE', 'TRANSFERT_ENTREE',
          'VENTE', 'SORTIE', 'CONSOMMATION',
          'CHANGEMENT_SORTIE', 'TRANSFERT_SORTIE'

  ALERTES & RAPPORTS
  ──────────────────
  get_articles_en_alerte(idmagasin=0, date_fin=None)
      → Retourne les articles dont le stock (en unité de base) est
        inférieur ou égal au seuil d'alerte défini dans tb_article.

  get_resume_mouvements_periode(idarticle, date_debut, date_fin,
                                idmagasin=0)
      → Résumé entrées / sorties / stock net sur une période donnée.

─────────────────────────────────────────────────────────────────────────────
  EXEMPLE D'UTILISATION :
  ─────────────────────────────────────────────────────────────────────────
  from stock_manager import StockManager

  sm = StockManager(host='localhost', port=5432, dbname='ma_base',
                    user='postgres', password='motdepasse')

  # Stock de l'article id=5 dans tous les magasins, en unité de base
  stock = sm.get_stock_article_base(idarticle=5)

  # Stock de l'article id=5 dans le magasin id=2, converti en idunite=12
  resultat = sm.get_stock_article_par_unite(idarticle=5, idunite=12, idmagasin=2)

  # Historique des ventes de l'article id=5 en janvier 2025
  historique = sm.get_mouvements_par_type(
      idarticle=5,
      type_operation='VENTE',
      date_debut='2025-01-01',
      date_fin='2025-01-31'
  )

  sm.fermer_connexion()
─────────────────────────────────────────────────────────────────────────────
"""

import psycopg2
import psycopg2.extras
from datetime import datetime
from typing import Optional, List, Dict, Any


class StockManager:
    """
    Gestionnaire centralisé des stocks.

    Calcule le stock en temps réel en agrégeant tous les types de mouvements
    présents dans la base de données :
      Entrées  : Livraison fournisseur, Inventaire, Avoir, Changement entrée,
                 Transfert (côté entrée)
      Sorties  : Vente (VALIDEE uniquement), Sortie, Consommation interne,
                 Changement sortie, Transfert (côté sortie)

    Toutes les quantités sont converties en unité de base (niveau 0)
    via le facteur de conversion récursif des unités.
    """

    # ─────────────────────────────────────────────────────────────
    # Types de mouvements reconnus (pour filtrage)
    # ─────────────────────────────────────────────────────────────
    TYPES_ENTREE = {
        'ENTREE',
        'LIVRAISON',
        'INVENTAIRE',
        'AVOIR',
        'CHANGEMENT_ENTREE',
        'TRANSFERT_ENTREE',
    }

    TYPES_SORTIE = {
        'VENTE',
        'SORTIE',
        'CONSOMMATION',
        'CHANGEMENT_SORTIE',
        'TRANSFERT_SORTIE',
    }

    # ─────────────────────────────────────────────────────────────
    # CONSTRUCTEUR
    # ─────────────────────────────────────────────────────────────

    def __init__(
        self,
        host: str = 'localhost',
        port: int = 5432,
        dbname: str = '',
        user: str = 'postgres',
        password: str = '',
    ):
        """
        Initialise le StockManager et ouvre la connexion PostgreSQL.

        Paramètres
        ----------
        host     : adresse du serveur PostgreSQL
        port     : port PostgreSQL (défaut : 5432)
        dbname   : nom de la base de données
        user     : nom d'utilisateur
        password : mot de passe
        """
        try:
            self._connexion = psycopg2.connect(
                host=host,
                port=port,
                dbname=dbname,
                user=user,
                password=password,
            )
            self._connexion.autocommit = True
            print(f"[StockManager] Connexion réussie à '{dbname}' sur {host}:{port}")
        except psycopg2.Error as erreur:
            raise ConnectionError(
                f"[StockManager] Impossible de se connecter à la base : {erreur}"
            )

    # ─────────────────────────────────────────────────────────────
    # CONNEXION
    # ─────────────────────────────────────────────────────────────

    def fermer_connexion(self):
        """Ferme proprement la connexion à la base de données."""
        if self._connexion and not self._connexion.closed:
            self._connexion.close()
            print("[StockManager] Connexion fermée.")

    def _executer_requete(
        self, sql: str, parametres: tuple = ()
    ) -> List[Dict[str, Any]]:
        """
        Méthode interne : exécute une requête SQL et retourne
        les résultats sous forme de liste de dictionnaires.

        Paramètres
        ----------
        sql        : requête SQL avec placeholders %s
        parametres : tuple de valeurs à injecter

        Retourne
        --------
        Liste de dict {nom_colonne: valeur, ...}
        """
        with self._connexion.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as curseur:
            curseur.execute(sql, parametres)
            return [dict(ligne) for ligne in curseur.fetchall()]

    # ─────────────────────────────────────────────────────────────
    # CTE RÉUTILISABLES (blocs SQL communs)
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _cte_facteur_conversion() -> str:
        """
        Retourne le bloc CTE SQL qui calcule récursivement le facteur
        de conversion de chaque unité vers l'unité de base (niveau 0).

        Principe :
          - niveau 0 → facteur = 1.0
          - niveau N → facteur = qtunite(N) × facteur(N-1)

        Exemple :
          pièce (niv 0, qt=1)   → facteur = 1
          paquet (niv 1, qt=5)  → facteur = 5
          carton (niv 2, qt=100)→ facteur = 500
        """
        return """
        facteur_conversion AS (
            -- Cas de base : unités de niveau 0 (unité de base)
            SELECT
                u.idunite,
                u.idarticle,
                u.niveau,
                u.designationunite,
                1.0::double precision AS facteur_vers_base
            FROM tb_unite u
            WHERE u.niveau = 0
              AND u.deleted = 0

            UNION ALL

            -- Cas récursif : chaque niveau multiplie par qtunite du niveau parent
            SELECT
                u.idunite,
                u.idarticle,
                u.niveau,
                u.designationunite,
                fc.facteur_vers_base * u.qtunite AS facteur_vers_base
            FROM tb_unite u
            JOIN facteur_conversion fc
              ON fc.idarticle = u.idarticle
             AND fc.niveau    = u.niveau - 1
            WHERE u.deleted = 0
        )
        """

    @staticmethod
    def _cte_tous_mouvements() -> str:
        """
        Retourne le bloc CTE SQL qui unifie tous les types de mouvements
        en un seul jeu de données avec :
          - idunite        : unité du mouvement (permet la conversion)
          - idmag          : magasin concerné
          - date_mouvement : horodatage du mouvement
          - quantite       : quantité dans l'unité du mouvement
          - type_mouvement : libellé du type (ex: 'VENTE', 'LIVRAISON'…)
          - signe          : +1 pour entrée, -1 pour sortie
        """
        return """
        tous_mouvements AS (

            -- ── ENTRÉES ──────────────────────────────────────────────────

            -- 0. Entrée directe (Bon d'Entrée)
            SELECT
                ed.idunite,
                ed.idmag,
                e.dateregistre              AS date_mouvement,
                ed.qtentree                 AS quantite,
                'ENTREE'                    AS type_mouvement,
                1                           AS signe
            FROM tb_entreedetail ed
            JOIN tb_entree e ON e.id = ed.identree
            WHERE ed.deleted = 0
              AND e.deleted  = 0

            UNION ALL

            -- 1. Livraison fournisseur
            SELECT
                lf.idunite,
                lf.idmag,
                lf.dateregistre             AS date_mouvement,
                lf.qtlivrefrs               AS quantite,
                'LIVRAISON'                 AS type_mouvement,
                1                           AS signe
            FROM tb_livraisonfrs lf
            WHERE lf.deleted = 0

            UNION ALL

            -- 2. Inventaire
            --    IMPORTANT : on prend uniquement les lignes dont l'unité
            --    associée est de niveau 0 (évite la duplication mentionnée).
            SELECT
                u.idunite,
                inv.idmag,
                inv.date                    AS date_mouvement,
                inv.qtinventaire            AS quantite,
                'INVENTAIRE'                AS type_mouvement,
                1                           AS signe
            FROM tb_inventaire inv
            JOIN tb_unite u
              ON u.codearticle = inv.codearticle
             AND u.niveau      = 0
             AND u.deleted     = 0

            UNION ALL

            -- 3. Avoir (retour client → ré-entrée en stock)
            SELECT
                ad.idunite,
                ad.idmag,
                av.dateavoir             AS date_mouvement,
                ad.qtavoir                  AS quantite,
                'AVOIR'                     AS type_mouvement,
                1                           AS signe
            FROM tb_avoirdetail ad
            JOIN tb_avoir av ON av.id = ad.idavoir
            WHERE ad.deleted = 0
              AND av.deleted = 0

            UNION ALL

            -- 4. Changement Entrée
            SELECT
                dce.idunite,
                dce.idmagasin               AS idmag,
                chg.datechg                 AS date_mouvement,
                dce.quantite_entree::double precision AS quantite,
                'CHANGEMENT_ENTREE'         AS type_mouvement,
                1                           AS signe
            FROM tb_detailchange_entree dce
            JOIN tb_changement chg ON chg.idchg = dce.idchg

            UNION ALL

            -- 5. Transfert – côté entrée (magasin destinataire)
            SELECT
                td.idunite,
                td.idmagentree              AS idmag,
                t.dateregistre              AS date_mouvement,
                td.qttransfertentree        AS quantite,
                'TRANSFERT_ENTREE'          AS type_mouvement,
                1                           AS signe
            FROM tb_transfertdetail td
            JOIN tb_transfert t ON t.idtransfert = td.idtransfert
            WHERE td.deleted = 0
              AND t.deleted  = 0

            -- ── SORTIES ───────────────────────────────────────────────────

            UNION ALL

            -- 6. Vente (uniquement si statut = 'VALIDEE')
            SELECT
                vd.idunite,
                vd.idmag,
                v.dateregistre              AS date_mouvement,
                vd.qtvente                  AS quantite,
                'VENTE'                     AS type_mouvement,
                -1                          AS signe
            FROM tb_ventedetail vd
            JOIN tb_vente v ON v.id = vd.idvente
            WHERE vd.deleted  = 0
              AND v.deleted   = 0
              AND v.statut    = 'VALIDEE'

            UNION ALL

            -- 7. Sortie manuelle
            SELECT
                sd.idunite,
                sd.idmag,
                s.dateregistre              AS date_mouvement,
                sd.qtsortie                 AS quantite,
                'SORTIE'                    AS type_mouvement,
                -1                          AS signe
            FROM tb_sortiedetail sd
            JOIN tb_sortie s ON s.id = sd.idsortie
            WHERE sd.deleted = 0
              AND s.deleted  = 0

            UNION ALL

            -- 8. Consommation interne
            SELECT
                cid.idunite,
                cid.idmag,
                ci.dateregistre             AS date_mouvement,
                cid.qtconsomme::double precision AS quantite,
                'CONSOMMATION'              AS type_mouvement,
                -1                          AS signe
            FROM tb_consommationinterne_details cid
            JOIN tb_consommationinterne ci ON ci.id = cid.idconsommation

            UNION ALL

            -- 9. Changement Sortie
            SELECT
                dcs.idunite,
                dcs.idmagasin               AS idmag,
                chg.datechg                 AS date_mouvement,
                dcs.quantite_sortie::double precision AS quantite,
                'CHANGEMENT_SORTIE'         AS type_mouvement,
                -1                          AS signe
            FROM tb_detailchange_sortie dcs
            JOIN tb_changement chg ON chg.idchg = dcs.idchg

            UNION ALL

            -- 10. Transfert – côté sortie (magasin expéditeur)
            SELECT
                td.idunite,
                td.idmagsortie              AS idmag,
                t.dateregistre              AS date_mouvement,
                td.qttransfertsortie        AS quantite,
                'TRANSFERT_SORTIE'          AS type_mouvement,
                -1                          AS signe
            FROM tb_transfertdetail td
            JOIN tb_transfert t ON t.idtransfert = td.idtransfert
            WHERE td.deleted = 0
              AND t.deleted  = 0
        )
        """

    # ─────────────────────────────────────────────────────────────
    # UNITÉS
    # ─────────────────────────────────────────────────────────────

    def get_unites_article(self, idarticle: int) -> List[Dict[str, Any]]:
        """
        Retourne toutes les unités d'un article avec leur facteur
        de conversion vers l'unité de base.

        Paramètres
        ----------
        idarticle : identifiant de l'article

        Retourne
        --------
        Liste de dict :
          idunite, designationunite, niveau, qtunite, facteur_vers_base
        """
        sql = f"""
        WITH RECURSIVE {self._cte_facteur_conversion()}
        SELECT
            fc.idunite,
            fc.designationunite,
            fc.niveau,
            u.qtunite,
            fc.facteur_vers_base
        FROM facteur_conversion fc
        JOIN tb_unite u ON u.idunite = fc.idunite
        WHERE fc.idarticle = %s
        ORDER BY fc.niveau ASC
        """
        return self._executer_requete(sql, (idarticle,))

    def get_facteur_conversion(self, idunite: int) -> float:
        """
        Retourne le facteur de conversion d'une unité vers l'unité de base.

        Exemple : si idunite est un 'carton' valant 500 pièces,
                  le facteur retourné est 500.0.

        Paramètres
        ----------
        idunite : identifiant de l'unité

        Retourne
        --------
        float : facteur de conversion (1.0 si unité de base introuvable)
        """
        sql = f"""
        WITH RECURSIVE {self._cte_facteur_conversion()}
        SELECT facteur_vers_base
        FROM facteur_conversion
        WHERE idunite = %s
        """
        resultats = self._executer_requete(sql, (idunite,))
        if resultats:
            return float(resultats[0]['facteur_vers_base'])
        return 1.0

    # ─────────────────────────────────────────────────────────────
    # STOCK PAR ARTICLE
    # ─────────────────────────────────────────────────────────────

    def get_stock_article_base(
        self,
        idarticle: int,
        idmagasin: int = 0,
        date_fin: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calcule le stock d'un article en unité de base (niveau 0).

        Paramètres
        ----------
        idarticle : identifiant de l'article
        idmagasin : 0 = tous les magasins, sinon filtre sur ce magasin
        date_fin  : date limite 'YYYY-MM-DD' (None = aujourd'hui inclus)

        Retourne
        --------
        dict : {
            idarticle,
            designation,
            idmagasin (ou 'TOUS'),
            stock_en_base,
            unite_base,           -- désignation de l'unité de base
            date_calcul
        }
        """
        # Construction des filtres dynamiques
        filtre_magasin = "" if idmagasin == 0 else "AND tm.idmag = %(idmagasin)s"
        filtre_date    = "" if date_fin is None else "AND tm.date_mouvement <= %(date_fin)s::timestamp"

        sql = f"""
        WITH RECURSIVE
            {self._cte_facteur_conversion()},
            {self._cte_tous_mouvements()}
        SELECT
            a.idarticle,
            a.designation,
            COALESCE(SUM(tm.quantite * fc.facteur_vers_base * tm.signe), 0.0)
                AS stock_en_base,
            u_base.designationunite AS unite_base
        FROM tb_article a
        -- Unité de base de l'article
        JOIN tb_unite u_base
          ON u_base.idarticle = a.idarticle
         AND u_base.niveau    = 0
         AND u_base.deleted   = 0
        -- Jointure avec les mouvements via facteur_conversion
        LEFT JOIN facteur_conversion fc ON fc.idarticle = a.idarticle
        LEFT JOIN tous_mouvements tm
          ON tm.idunite = fc.idunite
          {filtre_magasin}
          {filtre_date}
        WHERE a.idarticle = %(idarticle)s
          AND a.deleted   = 0
        GROUP BY a.idarticle, a.designation, u_base.designationunite
        """

        params = {
            'idarticle' : idarticle,
            'idmagasin' : idmagasin,
            'date_fin'  : date_fin,
        }

        resultats = self._executer_requete(sql, params)
        if not resultats:
            return {
                'idarticle'   : idarticle,
                'designation' : None,
                'idmagasin'   : idmagasin if idmagasin != 0 else 'TOUS',
                'stock_en_base': 0.0,
                'unite_base'  : None,
                'date_calcul' : date_fin or datetime.today().strftime('%Y-%m-%d'),
            }

        resultat = resultats[0]
        resultat['idmagasin']   = idmagasin if idmagasin != 0 else 'TOUS'
        resultat['date_calcul'] = date_fin or datetime.today().strftime('%Y-%m-%d')
        return resultat

    def get_stock_article_par_unite(
        self,
        idarticle: int,
        idunite: int,
        idmagasin: int = 0,
        date_fin: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retourne le stock d'un article converti dans l'unité demandée,
        avec le reste en unité de base.

        Exemple : si stock = 1523 pièces et idunite = 'carton' (facteur 500)
                  → 3 cartons et 23 pièces restantes.

        Paramètres
        ----------
        idarticle : identifiant de l'article
        idunite   : unité dans laquelle exprimer le résultat
        idmagasin : 0 = tous les magasins
        date_fin  : date limite (None = aujourd'hui)

        Retourne
        --------
        dict : {
            idarticle, designation, idunite, designationunite,
            stock_en_base, stock_dans_unite (partie entière),
            reste_en_base (reste après conversion), facteur_conversion,
            idmagasin, date_calcul
        }
        """
        # 1. Récupérer le stock en unité de base
        stock_base = self.get_stock_article_base(idarticle, idmagasin, date_fin)
        quantite_base = stock_base.get('stock_en_base', 0.0)

        # 2. Récupérer le facteur de conversion de l'unité cible
        facteur = self.get_facteur_conversion(idunite)

        # 3. Récupérer la désignation de l'unité cible
        sql_unite = """
        SELECT designationunite, niveau
        FROM tb_unite
        WHERE idunite = %s AND deleted = 0
        """
        info_unite = self._executer_requete(sql_unite, (idunite,))
        designation_unite = info_unite[0]['designationunite'] if info_unite else '?'

        # 4. Convertir
        if facteur > 0:
            stock_dans_unite = int(quantite_base // facteur)
            reste_en_base    = quantite_base % facteur
        else:
            stock_dans_unite = 0
            reste_en_base    = quantite_base

        return {
            'idarticle'        : idarticle,
            'designation'      : stock_base.get('designation'),
            'idunite'          : idunite,
            'designationunite' : designation_unite,
            'facteur_conversion': facteur,
            'stock_en_base'    : quantite_base,
            'stock_dans_unite' : stock_dans_unite,
            'reste_en_base'    : reste_en_base,
            'unite_base'       : stock_base.get('unite_base'),
            'idmagasin'        : idmagasin if idmagasin != 0 else 'TOUS',
            'date_calcul'      : date_fin or datetime.today().strftime('%Y-%m-%d'),
        }

    def get_stock_article_par_magasin(
        self,
        idarticle: int,
        date_fin: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retourne le stock d'un article ventilé par magasin.

        Paramètres
        ----------
        idarticle : identifiant de l'article
        date_fin  : date limite (None = aujourd'hui)

        Retourne
        --------
        Liste de dict : {idarticle, designation, idmag, designationmag,
                         stock_en_base, unite_base, date_calcul}
        """
        filtre_date = (
            "" if date_fin is None
            else "AND tm.date_mouvement <= %(date_fin)s::timestamp"
        )

        sql = f"""
        WITH RECURSIVE
            {self._cte_facteur_conversion()},
            {self._cte_tous_mouvements()}
        SELECT
            a.idarticle,
            a.designation,
            tm.idmag,
            mag.designationmag,
            COALESCE(SUM(tm.quantite * fc.facteur_vers_base * tm.signe), 0.0)
                AS stock_en_base,
            u_base.designationunite AS unite_base
        FROM tb_article a
        JOIN tb_unite u_base
          ON u_base.idarticle = a.idarticle
         AND u_base.niveau    = 0
         AND u_base.deleted   = 0
        JOIN facteur_conversion fc ON fc.idarticle = a.idarticle
        JOIN tous_mouvements tm
          ON tm.idunite = fc.idunite
          {filtre_date}
        JOIN tb_magasin mag ON mag.idmag = tm.idmag AND mag.deleted = 0
        WHERE a.idarticle = %(idarticle)s
          AND a.deleted   = 0
        GROUP BY a.idarticle, a.designation, tm.idmag, mag.designationmag,
                 u_base.designationunite
        ORDER BY tm.idmag
        """

        params = {'idarticle': idarticle, 'date_fin': date_fin}
        resultats = self._executer_requete(sql, params)

        date_calcul = date_fin or datetime.today().strftime('%Y-%m-%d')
        for ligne in resultats:
            ligne['date_calcul'] = date_calcul

        return resultats

    def get_stock_tous_articles(
        self,
        idmagasin: int = 0,
        date_fin: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retourne le stock de tous les articles actifs.

        Paramètres
        ----------
        idmagasin : 0 = tous les magasins, sinon filtre sur ce magasin
        date_fin  : date limite (None = aujourd'hui)

        Retourne
        --------
        Liste de dict : {idarticle, designation, categorie,
                         stock_en_base, unite_base, seuil_alerte,
                         en_alerte (True/False), idmagasin, date_calcul}
        """
        filtre_magasin = "" if idmagasin == 0 else "AND tm.idmag = %(idmagasin)s"
        filtre_date    = (
            "" if date_fin is None
            else "AND tm.date_mouvement <= %(date_fin)s::timestamp"
        )

        sql = f"""
        WITH RECURSIVE
            {self._cte_facteur_conversion()},
            {self._cte_tous_mouvements()}
        SELECT
            a.idarticle,
            a.designation,
            cat.designationcat  AS categorie,
            u_base.designationunite AS unite_base,
            COALESCE(a.alert, 0)  AS seuil_alerte,
            COALESCE(SUM(tm.quantite * fc.facteur_vers_base * tm.signe), 0.0)
                AS stock_en_base
        FROM tb_article a
        LEFT JOIN tb_categoriearticle cat
          ON cat.idca = a.idca AND cat.deleted = 0
        JOIN tb_unite u_base
          ON u_base.idarticle = a.idarticle
         AND u_base.niveau    = 0
         AND u_base.deleted   = 0
        LEFT JOIN facteur_conversion fc ON fc.idarticle = a.idarticle
        LEFT JOIN tous_mouvements tm
          ON tm.idunite = fc.idunite
          {filtre_magasin}
          {filtre_date}
        WHERE a.deleted = 0
        GROUP BY a.idarticle, a.designation, cat.designationcat,
                 u_base.designationunite, a.alert
        ORDER BY a.designation ASC
        """

        params = {'idmagasin': idmagasin, 'date_fin': date_fin}
        resultats = self._executer_requete(sql, params)

        date_calcul = date_fin or datetime.today().strftime('%Y-%m-%d')
        for ligne in resultats:
            ligne['en_alerte']   = (
                float(ligne['stock_en_base']) <= float(ligne['seuil_alerte'])
            )
            ligne['idmagasin']   = idmagasin if idmagasin != 0 else 'TOUS'
            ligne['date_calcul'] = date_calcul

        return resultats

    # ─────────────────────────────────────────────────────────────
    # MOUVEMENTS & HISTORIQUE
    # ─────────────────────────────────────────────────────────────

    def get_mouvements_article(
        self,
        idarticle: int,
        idmagasin: int = 0,
        type_mouvement: Optional[str] = None,
        date_debut: Optional[str] = None,
        date_fin: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retourne l'historique détaillé des mouvements d'un article.

        Paramètres
        ----------
        idarticle     : identifiant de l'article
        idmagasin     : 0 = tous les magasins
        type_mouvement: 'ENTREE', 'SORTIE', ou None pour tout afficher
        date_debut    : filtre début 'YYYY-MM-DD' (optionnel)
        date_fin      : filtre fin   'YYYY-MM-DD' (optionnel)

        Retourne
        --------
        Liste de dict triée par date_mouvement :
          {date_mouvement, type_mouvement, sens, idmag, designationmag,
           idunite, designationunite, quantite_originale,
           facteur_conversion, quantite_en_base}
        """
        # Construire les filtres dynamiques
        filtres = ["fc.idarticle = %(idarticle)s"]

        if idmagasin != 0:
            filtres.append("tm.idmag = %(idmagasin)s")
        if date_debut:
            filtres.append("tm.date_mouvement >= %(date_debut)s::timestamp")
        if date_fin:
            filtres.append("tm.date_mouvement <= %(date_fin)s::timestamp")

        # Filtre sur le sens (ENTREE / SORTIE)
        if type_mouvement:
            sens = type_mouvement.upper()
            if sens == 'ENTREE':
                filtres.append("tm.signe = 1")
            elif sens == 'SORTIE':
                filtres.append("tm.signe = -1")

        clause_where = "WHERE " + " AND ".join(filtres)

        sql = f"""
        WITH RECURSIVE
            {self._cte_facteur_conversion()},
            {self._cte_tous_mouvements()}
        SELECT
            tm.date_mouvement,
            tm.type_mouvement,
            CASE WHEN tm.signe = 1 THEN 'ENTREE' ELSE 'SORTIE' END AS sens,
            tm.idmag,
            mag.designationmag,
            fc.idunite,
            fc.designationunite,
            tm.quantite                               AS quantite_originale,
            fc.facteur_vers_base                      AS facteur_conversion,
            tm.quantite * fc.facteur_vers_base        AS quantite_en_base
        FROM tous_mouvements tm
        JOIN facteur_conversion fc ON fc.idunite = tm.idunite
        LEFT JOIN tb_magasin mag ON mag.idmag = tm.idmag
        {clause_where}
        ORDER BY tm.date_mouvement DESC
        """

        params = {
            'idarticle' : idarticle,
            'idmagasin' : idmagasin,
            'date_debut': date_debut,
            'date_fin'  : date_fin,
        }

        return self._executer_requete(sql, params)

    def get_mouvements_par_type(
        self,
        idarticle: int,
        type_operation: str,
        idmagasin: int = 0,
        date_debut: Optional[str] = None,
        date_fin: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Filtre les mouvements d'un article par type précis.

        Paramètres
        ----------
        idarticle     : identifiant de l'article
        type_operation: type exact parmi :
                        'LIVRAISON', 'INVENTAIRE', 'AVOIR',
                        'CHANGEMENT_ENTREE', 'TRANSFERT_ENTREE',
                        'VENTE', 'SORTIE', 'CONSOMMATION',
                        'CHANGEMENT_SORTIE', 'TRANSFERT_SORTIE'
        idmagasin     : 0 = tous les magasins
        date_debut    : filtre début (optionnel)
        date_fin      : filtre fin   (optionnel)

        Retourne
        --------
        Même structure que get_mouvements_article().
        """
        tous_types = self.TYPES_ENTREE | self.TYPES_SORTIE
        if type_operation.upper() not in tous_types:
            raise ValueError(
                f"Type de mouvement inconnu : '{type_operation}'.\n"
                f"Types valides : {sorted(tous_types)}"
            )

        filtres = [
            "fc.idarticle       = %(idarticle)s",
            "tm.type_mouvement  = %(type_operation)s",
        ]
        if idmagasin != 0:
            filtres.append("tm.idmag = %(idmagasin)s")
        if date_debut:
            filtres.append("tm.date_mouvement >= %(date_debut)s::timestamp")
        if date_fin:
            filtres.append("tm.date_mouvement <= %(date_fin)s::timestamp")

        clause_where = "WHERE " + " AND ".join(filtres)

        sql = f"""
        WITH RECURSIVE
            {self._cte_facteur_conversion()},
            {self._cte_tous_mouvements()}
        SELECT
            tm.date_mouvement,
            tm.type_mouvement,
            CASE WHEN tm.signe = 1 THEN 'ENTREE' ELSE 'SORTIE' END AS sens,
            tm.idmag,
            mag.designationmag,
            fc.idunite,
            fc.designationunite,
            tm.quantite                               AS quantite_originale,
            fc.facteur_vers_base                      AS facteur_conversion,
            tm.quantite * fc.facteur_vers_base        AS quantite_en_base
        FROM tous_mouvements tm
        JOIN facteur_conversion fc ON fc.idunite = tm.idunite
        LEFT JOIN tb_magasin mag ON mag.idmag = tm.idmag
        {clause_where}
        ORDER BY tm.date_mouvement DESC
        """

        params = {
            'idarticle'     : idarticle,
            'type_operation': type_operation.upper(),
            'idmagasin'     : idmagasin,
            'date_debut'    : date_debut,
            'date_fin'      : date_fin,
        }

        return self._executer_requete(sql, params)

    # ─────────────────────────────────────────────────────────────
    # ALERTES & RAPPORTS
    # ─────────────────────────────────────────────────────────────

    def get_articles_en_alerte(
        self,
        idmagasin: int = 0,
        date_fin: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retourne les articles dont le stock est inférieur ou égal
        au seuil d'alerte (champ 'alert' de tb_article).

        Paramètres
        ----------
        idmagasin : 0 = tous les magasins
        date_fin  : date de référence (None = aujourd'hui)

        Retourne
        --------
        Liste de dict triée par écart croissant (les plus critiques en premier) :
          {idarticle, designation, stock_en_base, seuil_alerte,
           ecart_par_rapport_alerte, unite_base, idmagasin, date_calcul}
        """
        tous = self.get_stock_tous_articles(idmagasin=idmagasin, date_fin=date_fin)

        articles_en_alerte = [
            {
                **a,
                'ecart_par_rapport_alerte': float(a['stock_en_base']) - float(a['seuil_alerte'])
            }
            for a in tous
            if a['en_alerte']
        ]

        # Trier : les plus critiques (écart le plus négatif) en premier
        articles_en_alerte.sort(key=lambda x: x['ecart_par_rapport_alerte'])
        return articles_en_alerte

    def get_resume_mouvements_periode(
        self,
        idarticle: int,
        date_debut: str,
        date_fin: str,
        idmagasin: int = 0,
    ) -> Dict[str, Any]:
        """
        Calcule un résumé des entrées, sorties et stock net sur une période.

        Paramètres
        ----------
        idarticle  : identifiant de l'article
        date_debut : début de la période 'YYYY-MM-DD'
        date_fin   : fin   de la période 'YYYY-MM-DD'
        idmagasin  : 0 = tous les magasins

        Retourne
        --------
        dict : {
            idarticle, designation, unite_base,
            stock_debut_periode,     -- stock AVANT date_debut
            total_entrees_periode,   -- somme des entrées sur la période
            total_sorties_periode,   -- somme des sorties sur la période
            stock_fin_periode,       -- stock calculé à date_fin
            detail_par_type          -- dict {type_mouvement: quantite_en_base}
        }
        """
        filtre_magasin = "" if idmagasin == 0 else "AND tm.idmag = %(idmagasin)s"

        # Stock avant la période (jusqu'à la veille de date_debut)
        stock_avant = self.get_stock_article_base(
            idarticle=idarticle,
            idmagasin=idmagasin,
            date_fin=date_debut,  # borne exclus via < dans la requête suivante
        )

        # Mouvements durant la période
        sql = f"""
        WITH RECURSIVE
            {self._cte_facteur_conversion()},
            {self._cte_tous_mouvements()}
        SELECT
            tm.type_mouvement,
            tm.signe,
            COALESCE(SUM(tm.quantite * fc.facteur_vers_base), 0.0) AS total_en_base
        FROM tous_mouvements tm
        JOIN facteur_conversion fc ON fc.idunite = tm.idunite
        WHERE fc.idarticle         = %(idarticle)s
          AND tm.date_mouvement    > %(date_debut)s::timestamp
          AND tm.date_mouvement   <= %(date_fin)s::timestamp
          {filtre_magasin}
        GROUP BY tm.type_mouvement, tm.signe
        ORDER BY tm.type_mouvement
        """

        params = {
            'idarticle' : idarticle,
            'date_debut': date_debut,
            'date_fin'  : date_fin,
            'idmagasin' : idmagasin,
        }

        lignes = self._executer_requete(sql, params)

        total_entrees  = 0.0
        total_sorties  = 0.0
        detail_par_type: Dict[str, float] = {}

        for ligne in lignes:
            montant = float(ligne['total_en_base'])
            detail_par_type[ligne['type_mouvement']] = montant
            if ligne['signe'] == 1:
                total_entrees += montant
            else:
                total_sorties += montant

        stock_debut = float(stock_avant.get('stock_en_base', 0.0))

        return {
            'idarticle'              : idarticle,
            'designation'            : stock_avant.get('designation'),
            'unite_base'             : stock_avant.get('unite_base'),
            'idmagasin'              : idmagasin if idmagasin != 0 else 'TOUS',
            'date_debut'             : date_debut,
            'date_fin'               : date_fin,
            'stock_debut_periode'    : stock_debut,
            'total_entrees_periode'  : total_entrees,
            'total_sorties_periode'  : total_sorties,
            'stock_fin_periode'      : stock_debut + total_entrees - total_sorties,
            'detail_par_type'        : detail_par_type,
        }

    # ─────────────────────────────────────────────────────────────
    # TRACÉ COMPLET — TOUS LES MOUVEMENTS AVEC STOCK APRÈS
    # ─────────────────────────────────────────────────────────────

    def get_trace_mouvements_article(
        self,
        idarticle: int,
        date_debut: Optional[str] = None,
        date_fin: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retourne le tracé chronologique complet de TOUS les mouvements
        d'un article, toutes unités et tous magasins confondus.

        Pour chaque mouvement, le stock cumulé après ce mouvement est
        calculé via une fonction de fenêtre SQL (SUM ... OVER), ce qui
        garantit un calcul précis et non une simple accumulation Python.

        Colonnes retournées
        -------------------
        date_mouvement      : horodatage exact du mouvement
        codearticle         : code de l'unité impliquée (lié à l'article)
        designation_article : nom de l'article
        designation_unite   : nom de l'unité du mouvement
        niveau_unite        : niveau de l'unité (0 = base)
        type_mouvement      : LIVRAISON, VENTE, INVENTAIRE…
        sens                : ENTREE ou SORTIE
        idmag               : identifiant du magasin
        designation_magasin : nom du magasin
        quantite_originale  : quantité dans l'unité d'origine du mouvement
        quantite_en_base    : quantité convertie en unité de base (signée)
        stock_apres_mouvement : stock cumulé en unité de base après ce mouvement

        Paramètres
        ----------
        idarticle  : identifiant de l'article
        date_debut : filtre début 'YYYY-MM-DD' (optionnel)
        date_fin   : filtre fin   'YYYY-MM-DD' (optionnel)
        """
        filtres = ["fc.idarticle = %(idarticle)s"]
        if date_debut:
            filtres.append("tm.date_mouvement >= %(date_debut)s::timestamp")
        if date_fin:
            filtres.append("tm.date_mouvement <= %(date_fin)s::timestamp")

        clause_where = "WHERE " + " AND ".join(filtres)

        sql = f"""
        WITH RECURSIVE
            {self._cte_facteur_conversion()},
            {self._cte_tous_mouvements()},

            -- Tracé détaillé : chaque mouvement avec sa quantité signée en base
            trace_brut AS (
                SELECT
                    tm.date_mouvement,
                    u.codearticle,
                    a.designation                                   AS designation_article,
                    fc.designationunite                             AS designation_unite,
                    fc.niveau                                       AS niveau_unite,
                    tm.type_mouvement,
                    CASE WHEN tm.signe = 1
                         THEN 'ENTREE' ELSE 'SORTIE'
                    END                                             AS sens,
                    tm.idmag,
                    mag.designationmag                              AS designation_magasin,
                    tm.quantite                                     AS quantite_originale,
                    -- Quantité signée convertie en unité de base
                    (tm.quantite * fc.facteur_vers_base * tm.signe) AS quantite_signee_base
                FROM tous_mouvements tm
                JOIN facteur_conversion fc  ON fc.idunite    = tm.idunite
                JOIN tb_unite u             ON u.idunite     = fc.idunite
                JOIN tb_article a           ON a.idarticle   = fc.idarticle
                LEFT JOIN tb_magasin mag    ON mag.idmag      = tm.idmag
                {clause_where}
            )

        -- Résultat final : stock après chaque mouvement via fenêtre SQL
        SELECT
            date_mouvement,
            codearticle,
            designation_article,
            designation_unite,
            niveau_unite,
            type_mouvement,
            sens,
            idmag,
            designation_magasin,
            quantite_originale,
            quantite_signee_base                         AS quantite_en_base,
            -- Stock cumulé après chaque mouvement (ordonné chronologiquement)
            SUM(quantite_signee_base) OVER (
                ORDER BY date_mouvement
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            )                                            AS stock_apres_mouvement
        FROM trace_brut
        ORDER BY date_mouvement ASC
        """

        params = {
            'idarticle' : idarticle,
            'date_debut': date_debut,
            'date_fin'  : date_fin,
        }

        return self._executer_requete(sql, params)

    # ─────────────────────────────────────────────────────────────
    # STOCK PRÉCIS — article + unité + magasin + date & heure
    # ─────────────────────────────────────────────────────────────

    def get_stock_a_date_precise(
        self,
        idarticle : int,
        idunite   : int,
        idmagasin : int,
        datetime_cible: str,
    ) -> Dict[str, Any]:
        """
        Retourne le stock d'un article dans une unité et un magasin
        précis, à un instant exact (date ET heure).

        Le stock est calculé en agrégeant tous les mouvements dont
        la date est STRICTEMENT INFÉRIEURE OU ÉGALE à datetime_cible,
        puis converti de l'unité de base vers l'unité demandée.

        Paramètres
        ----------
        idarticle     : identifiant de l'article
        idunite       : unité dans laquelle exprimer le résultat
        idmagasin     : magasin précis (obligatoire, ≠ 0)
        datetime_cible: instant de référence au format
                        'YYYY-MM-DD HH:MM:SS'  ou  'YYYY-MM-DD HH:MM'

        Retourne
        --------
        dict : {
            idarticle,
            designation_article,
            idunite,
            designation_unite,
            facteur_conversion,
            idmagasin,
            designation_magasin,
            datetime_cible,
            stock_en_base,           -- stock exprimé en unité de base
            stock_dans_unite,        -- partie entière dans l'unité demandée
            reste_en_base,           -- reste non converti (en unité de base)
            unite_base,              -- désignation de l'unité de base
        }
        """
        sql = f"""
        WITH RECURSIVE
            {self._cte_facteur_conversion()},
            {self._cte_tous_mouvements()},

            -- Unité de base de l'article (niveau 0)
            unite_base AS (
                SELECT idunite, designationunite
                FROM   tb_unite
                WHERE  idarticle = %(idarticle)s
                  AND  niveau    = 0
                  AND  deleted   = 0
                LIMIT 1
            ),

            -- Facteur de conversion de l'unité demandée → base
            facteur_cible AS (
                SELECT facteur_vers_base, designationunite
                FROM   facteur_conversion
                WHERE  idunite    = %(idunite)s
                  AND  idarticle  = %(idarticle)s
                LIMIT 1
            )

        SELECT
            a.idarticle,
            a.designation                   AS designation_article,
            %(idunite)s                     AS idunite,
            fc_cible.designationunite       AS designation_unite,
            fc_cible.facteur_vers_base      AS facteur_conversion,
            %(idmagasin)s                   AS idmagasin,
            mag.designationmag              AS designation_magasin,
            %(datetime_cible)s              AS datetime_cible,
            ub.designationunite             AS unite_base,
            -- Stock total en unité de base jusqu'à l'instant demandé
            COALESCE(
                SUM(tm.quantite * fc.facteur_vers_base * tm.signe),
                0.0
            )                               AS stock_en_base
        FROM tb_article a
        -- Unité de base
        JOIN unite_base ub         ON true
        -- Facteur de l'unité cible
        JOIN facteur_cible fc_cible ON true
        -- Magasin
        JOIN tb_magasin mag         ON mag.idmag   = %(idmagasin)s
                                   AND mag.deleted = 0
        -- Tous les mouvements de l'article dans ce magasin jusqu'à datetime_cible
        LEFT JOIN facteur_conversion fc
               ON fc.idarticle = a.idarticle
        LEFT JOIN tous_mouvements tm
               ON tm.idunite        = fc.idunite
              AND tm.idmag          = %(idmagasin)s
              AND date_trunc('second', tm.date_mouvement)
                <=
                date_trunc('second', %(datetime_cible)s::timestamp)
        WHERE a.idarticle = %(idarticle)s
          AND a.deleted   = 0
        GROUP BY
            a.idarticle,
            a.designation,
            fc_cible.designationunite,
            fc_cible.facteur_vers_base,
            mag.designationmag,
            ub.designationunite
        """

        params = {
            'idarticle'     : idarticle,
            'idunite'       : idunite,
            'idmagasin'     : idmagasin,
            'datetime_cible': datetime_cible,
        }

        resultats = self._executer_requete(sql, params)

        if not resultats:
            return {
                'idarticle'           : idarticle,
                'designation_article' : None,
                'idunite'             : idunite,
                'designation_unite'   : None,
                'facteur_conversion'  : 1.0,
                'idmagasin'           : idmagasin,
                'designation_magasin' : None,
                'datetime_cible'      : datetime_cible,
                'stock_en_base'       : 0.0,
                'stock_dans_unite'    : 0,
                'reste_en_base'       : 0.0,
                'unite_base'          : None,
            }

        row     = resultats[0]
        base    = float(row['stock_en_base'])
        facteur = float(row['facteur_conversion']) if row['facteur_conversion'] else 1.0

        stock_dans_unite = int(base // facteur) if facteur > 0 else 0
        reste_en_base    = base % facteur        if facteur > 0 else base

        row['stock_en_base']    = base
        row['stock_dans_unite'] = stock_dans_unite
        row['reste_en_base']    = reste_en_base
        row['facteur_conversion'] = facteur

        return row