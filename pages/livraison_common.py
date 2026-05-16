# -*- coding: utf-8 -*-
"""Utilitaires partagés — livraisons client (trace uniquement, sans stock)."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import psycopg2
import psycopg2.pool

# ── Détection avoir (facture non livrable) ───────────────────────────────────

SQL_FILTER_SANS_AVOIR = """
    AND NOT EXISTS (
        SELECT 1 FROM tb_avoir a
        WHERE a.deleted = 0
          AND a.observation ILIKE '%%' || v.refvente || '%%'
    )
    AND NOT EXISTS (
        SELECT 1 FROM tb_pmtavoir p
        WHERE COALESCE(p.deleted, 0) = 0
          AND p.refvente = v.refvente
    )
"""

SQL_LIVRE_SUM = """
    LEFT JOIN (
        SELECT refvente, idarticle, idunite, idmag,
               SUM(qtlivrecli) AS total_livre
        FROM tb_livraisoncli
        GROUP BY refvente, idarticle, idunite, idmag
    ) lv_sum ON lv_sum.refvente  = v.refvente
            AND lv_sum.idarticle = vd.idarticle
            AND lv_sum.idunite   = vd.idunite
            AND lv_sum.idmag     = vd.idmag
"""

SQL_PENDING_ARTICLES = f"""
    SELECT
        u.codearticle,
        a.designation,
        u.designationunite,
        m.designationmag,
        c.nomcli,
        v.refvente,
        vd.idarticle,
        vd.idunite,
        vd.idmag,
        v.idclient,
        vd.qtvente,
        (vd.qtvente - COALESCE(lv_sum.total_livre, 0)) AS reste_a_livrer,
        v.dateregistre
    FROM tb_vente v
    INNER JOIN tb_ventedetail vd ON vd.idvente = v.id
    INNER JOIN tb_article a ON vd.idarticle = a.idarticle AND a.deleted = 0
    INNER JOIN tb_unite u ON vd.idarticle = u.idarticle AND vd.idunite = u.idunite
    INNER JOIN tb_magasin m ON vd.idmag = m.idmag AND COALESCE(m.deleted, 0) = 0
    INNER JOIN tb_client c ON v.idclient = c.idclient
    {SQL_LIVRE_SUM}
    WHERE v.deleted = 0
      AND v.statut = 'VALIDEE'
      AND (vd.qtvente - COALESCE(lv_sum.total_livre, 0)) > 0.0001
      AND COALESCE(m.livraison_auto_client, 0) = 0
      {SQL_FILTER_SANS_AVOIR}
    ORDER BY v.dateregistre DESC, v.refvente, u.codearticle
"""

SQL_PENDING_FACTURES = f"""
    SELECT
        v.refvente,
        c.nomcli,
        v.idclient,
        MIN(v.dateregistre) AS dateregistre,
        COALESCE(
            STRING_AGG(DISTINCT m.designationmag, ', ' ORDER BY m.designationmag),
            ''
        ) AS magasins,
        COUNT(*)::int AS nb_lignes,
        SUM(vd.qtvente - COALESCE(lv_sum.total_livre, 0)) AS reste_total
    FROM tb_vente v
    INNER JOIN tb_ventedetail vd ON vd.idvente = v.id
    INNER JOIN tb_article a ON vd.idarticle = a.idarticle AND a.deleted = 0
    INNER JOIN tb_magasin m ON vd.idmag = m.idmag AND COALESCE(m.deleted, 0) = 0
    INNER JOIN tb_client c ON v.idclient = c.idclient
    {SQL_LIVRE_SUM}
    WHERE v.deleted = 0
      AND v.statut = 'VALIDEE'
      AND (vd.qtvente - COALESCE(lv_sum.total_livre, 0)) > 0.0001
      AND COALESCE(m.livraison_auto_client, 0) = 0
      {SQL_FILTER_SANS_AVOIR}
    GROUP BY v.refvente, c.nomcli, v.idclient
    ORDER BY MIN(v.dateregistre) DESC NULLS LAST, v.refvente DESC
"""


def fmt_datetime_livraison(val) -> str:
    """Affichage date/heure mouvement : dd/MM/yyyy HH:mm."""
    if val is None:
        return "—"
    if hasattr(val, "strftime"):
        return val.strftime("%d/%m/%Y %H:%M")
    return str(val)


def _lire_param_livraison_db() -> Dict[str, Any]:
    """Paramètres globaux livraison (tb_param_livraison_client, ligne id=1)."""
    _default = {"idtransporteur_defaut": None, "transporteur_bl_auto": False}
    conn = LivraisonDB.get_conn()
    if not conn:
        return _default
    try:
        cur = conn.cursor()
        return LivraisonDB.fetch_param_livraison_client(cur)
    except Exception:
        return _default
    finally:
        LivraisonDB.release_conn(conn)


def get_transporteur_defaut_id() -> Optional[int]:
    """Transporteur par défaut BL manuel (base de données)."""
    tid = _lire_param_livraison_db().get("idtransporteur_defaut")
    if tid is None:
        return None
    try:
        return int(tid)
    except (TypeError, ValueError):
        return None


def is_transporteur_bl_auto_enabled() -> bool:
    """Si vrai, les BL-AUTO reprennent le transporteur par défaut."""
    return bool(_lire_param_livraison_db().get("transporteur_bl_auto"))


def get_transporteur_pour_bl_auto() -> Optional[int]:
    """Transporteur des BL-AUTO : défaut seulement si « Transporteur BL-auto » actif en base."""
    if not is_transporteur_bl_auto_enabled():
        return None
    return get_transporteur_defaut_id()


def transporteur_pour_bl_auto_depuis_param(param: Dict[str, Any]) -> Optional[int]:
    """Calcule le transporteur BL-AUTO à partir d'un dict param déjà chargé."""
    if not param.get("transporteur_bl_auto"):
        return None
    tid = param.get("idtransporteur_defaut")
    return int(tid) if tid is not None else None


def transporteur_nom_par_id(
    transporteurs: List[Tuple[int, str]], idtransporteur: Optional[int],
) -> str:
    if not idtransporteur:
        return "— Aucun —"
    for tid, nom in transporteurs:
        if tid == idtransporteur:
            return nom
    return "— Aucun —"


def sql_pending_articles(
    search_term: str = "",
    idmag: Optional[int] = None,
) -> tuple:
    """Retourne (sql, params) avec filtres magasin et ILIKE optionnels."""
    term = (search_term or "").strip()
    params: List[Any] = []
    filt = ""
    if idmag is not None:
        filt += "\n      AND vd.idmag = %s"
        params.append(int(idmag))
    if term:
        pat = f"%{term}%"
        filt += """
      AND (
        u.codearticle ILIKE %s
        OR a.designation ILIKE %s
        OR u.designationunite ILIKE %s
        OR m.designationmag ILIKE %s
        OR c.nomcli ILIKE %s
        OR v.refvente ILIKE %s
      )"""
        params.extend([pat] * 6)
    if not filt:
        return SQL_PENDING_ARTICLES, []
    idx = SQL_PENDING_ARTICLES.rfind("ORDER BY")
    sql = SQL_PENDING_ARTICLES[:idx] + filt + "\n    " + SQL_PENDING_ARTICLES[idx:]
    return sql, params


def sql_pending_factures(
    search_term: str = "",
    idmag: Optional[int] = None,
) -> tuple:
    """Retourne (sql, params) avec filtres magasin et ILIKE optionnels."""
    term = (search_term or "").strip()
    params: List[Any] = []
    filt = ""
    if idmag is not None:
        filt += "\n      AND vd.idmag = %s"
        params.append(int(idmag))
    if term:
        pat = f"%{term}%"
        filt += """
      AND (
        v.refvente ILIKE %s
        OR c.nomcli ILIKE %s
      )"""
        params.extend([pat, pat])
    if not filt:
        return SQL_PENDING_FACTURES, []
    idx = SQL_PENDING_FACTURES.rfind("GROUP BY")
    sql = SQL_PENDING_FACTURES[:idx] + filt + "\n    " + SQL_PENDING_FACTURES[idx:]
    return sql, params


def sql_expr_avoir_apres_livraison(refvente_sql: str = "l.refvente", dt_liv_sql: str = "l.dateregistre") -> str:
    """
    Vrai si un avoir est lié à la facture ET enregistré après la date de livraison de la ligne.
    (Pas les avoirs antérieurs à la livraison.)
    """
    return f"""(
        EXISTS (
            SELECT 1 FROM tb_avoir a
            WHERE COALESCE(a.deleted, 0) = 0
              AND a.observation ILIKE '%%' || {refvente_sql} || '%%'
              AND COALESCE(a.dateavoir, a.dateregistre) > {dt_liv_sql}
        )
        OR EXISTS (
            SELECT 1 FROM tb_pmtavoir p
            WHERE COALESCE(p.deleted, 0) = 0
              AND p.refvente = {refvente_sql}
              AND p.datepmt > {dt_liv_sql}
        )
    )"""


def _sql_fragments_historique() -> Dict[str, str]:
    """Fragments SQL selon colonnes présentes sur tb_livraisoncli."""
    cols = LivraisonDB._extra_cols or set()
    has_trans = "idtransporteur" in cols
    has_desc = "description_livraison" in cols
    return {
        "has_trans": has_trans,
        "has_desc": has_desc,
        "transp_sel": "COALESCE(MAX(tr.nom), '')" if has_trans else "''::text",
        "desc_sel": "COALESCE(MAX(l.description_livraison), '')" if has_desc else "''::text",
        "join_trans": (
            "LEFT JOIN tb_transporteur tr ON tr.idtransporteur = l.idtransporteur"
            if has_trans else ""
        ),
    }


def sql_historique_bl(where_extra: str = "") -> str:
    """
    Un enregistrement par N° BL (reflivcli), toutes lignes tb_livraisoncli agrégées.
    Filtre les BL vides ; client unique par reflivcli (MAX si données hétérogènes).
    """
    f = _sql_fragments_historique()
    transp_hdr = (
        "(SELECT tr.nom FROM tb_livraisoncli l0 "
        "LEFT JOIN tb_transporteur tr ON tr.idtransporteur = l0.idtransporteur "
        "WHERE TRIM(l0.reflivcli) = g.reflivcli AND l0.idtransporteur IS NOT NULL "
        "ORDER BY l0.dateregistre DESC LIMIT 1)"
        if f["has_trans"] else "NULL::text"
    )
    desc_hdr = (
        "(SELECT l0.description_livraison FROM tb_livraisoncli l0 "
        "WHERE TRIM(l0.reflivcli) = g.reflivcli AND l0.description_livraison IS NOT NULL "
        "AND TRIM(l0.description_livraison) <> '' "
        "ORDER BY l0.dateregistre DESC LIMIT 1)"
        if f["has_desc"] else "NULL::text"
    )
    return f"""
    WITH lignes_bl AS (
        SELECT
            TRIM(l.reflivcli) AS reflivcli,
            l.dateregistre,
            l.idclient,
            l.refvente,
            l.qtlivrecli,
            l.iduser,
            CASE WHEN {sql_expr_avoir_apres_livraison()} THEN 1 ELSE 0 END AS avoir_apres_liv
        FROM tb_livraisoncli l
        WHERE l.reflivcli IS NOT NULL
          AND TRIM(l.reflivcli) <> ''
          {where_extra}
    ),
    bl_groupes AS (
        SELECT
            reflivcli,
            MIN(dateregistre) AS dt_bl,
            MAX(dateregistre) AS dt_bl_fin,
            MAX(idclient) AS idclient,
            MAX(iduser) AS iduser,
            COUNT(*)::int AS nb_lignes,
            COALESCE(SUM(qtlivrecli), 0) AS qte_totale,
            (
                SELECT STRING_AGG(f.refvente, ', ' ORDER BY f.refvente)
                FROM (
                    SELECT DISTINCT refvente
                    FROM lignes_bl lb2
                    WHERE lb2.reflivcli = lignes_bl.reflivcli
                      AND lb2.refvente IS NOT NULL
                      AND TRIM(lb2.refvente) <> ''
                ) f
            ) AS factures,
            MAX(avoir_apres_liv) AS has_avoir_apres
        FROM lignes_bl
        GROUP BY reflivcli
    )
    SELECT
        g.reflivcli,
        g.dt_bl,
        g.dt_bl_fin,
        COALESCE(c.nomcli, '') AS nomcli,
        g.idclient,
        g.nb_lignes,
        g.qte_totale,
        COALESCE(g.factures, '') AS factures,
        COALESCE({transp_hdr}, '') AS transporteur,
        COALESCE({desc_hdr}, '') AS description,
        (g.has_avoir_apres = 1) AS has_avoir_apres,
        TRIM(COALESCE(u.nomuser, '') || ' ' || COALESCE(u.prenomuser, '')) AS utilisateur
    FROM bl_groupes g
    LEFT JOIN tb_client c ON c.idclient = g.idclient
    LEFT JOIN tb_users u ON u.iduser = g.iduser
    ORDER BY g.dt_bl DESC, g.reflivcli DESC
    """


def sql_detail_bl() -> str:
    """Toutes les lignes d'un BL avec article, magasin, facture."""
    avoir_expr = sql_expr_avoir_apres_livraison()
    return f"""
    SELECT
        l.idlivcli,
        l.refvente,
        l.dateregistre,
        u.codearticle,
        COALESCE(a.designation, '') AS designation,
        COALESCE(u.designationunite, '') AS designationunite,
        COALESCE(m.designationmag, '') AS designationmag,
        COALESCE(l.qtvente, 0) AS qtvente,
        COALESCE(l.qtlivrecli, 0) AS qtlivrecli,
        TRIM(COALESCE(us.nomuser, '') || ' ' || COALESCE(us.prenomuser, '')) AS utilisateur,
        CASE WHEN {avoir_expr} THEN 1 ELSE 0 END AS avoir_apres_liv
    FROM tb_livraisoncli l
    INNER JOIN tb_article a ON a.idarticle = l.idarticle
    INNER JOIN tb_unite u ON u.idarticle = l.idarticle AND u.idunite = l.idunite
    LEFT JOIN tb_magasin m ON m.idmag = l.idmag
    LEFT JOIN tb_users us ON us.iduser = l.iduser
    WHERE TRIM(l.reflivcli) = TRIM(%s)
    ORDER BY l.dateregistre DESC, l.refvente NULLS LAST, a.designation, l.idlivcli
    """


def fetch_detail_bl_header(cur, refliv: str) -> Dict[str, Any]:
    """En-tête d'un BL (résumé) pour la fenêtre détail."""
    f = _sql_fragments_historique()
    transp_hdr = (
        "(SELECT tr.nom FROM tb_livraisoncli l0 "
        "LEFT JOIN tb_transporteur tr ON tr.idtransporteur = l0.idtransporteur "
        "WHERE TRIM(l0.reflivcli) = TRIM(%s) AND l0.idtransporteur IS NOT NULL "
        "ORDER BY l0.dateregistre DESC LIMIT 1)"
        if f["has_trans"] else "NULL::text"
    )
    desc_hdr = (
        "(SELECT l0.description_livraison FROM tb_livraisoncli l0 "
        "WHERE TRIM(l0.reflivcli) = TRIM(%s) AND l0.description_livraison IS NOT NULL "
        "AND TRIM(l0.description_livraison) <> '' "
        "ORDER BY l0.dateregistre DESC LIMIT 1)"
        if f["has_desc"] else "NULL::text"
    )
    avoir_expr = sql_expr_avoir_apres_livraison()
    avoir_expr_l3 = sql_expr_avoir_apres_livraison("l3.refvente", "l3.dateregistre")
    params: List[Any] = []
    if f["has_trans"]:
        params.append(refliv)
    if f["has_desc"]:
        params.append(refliv)
    params.extend([refliv, refliv, refliv])

    cur.execute(
        f"""
        SELECT
            TRIM(l.reflivcli) AS reflivcli,
            MIN(l.dateregistre) AS dt_bl,
            MAX(l.dateregistre) AS dt_bl_fin,
            MAX(l.idclient) AS idclient,
            COALESCE(MAX(c.nomcli), '') AS nomcli,
            COUNT(*)::int AS nb_lignes,
            COALESCE(SUM(l.qtlivrecli), 0) AS qte_totale,
            COALESCE({transp_hdr}, '') AS transporteur,
            COALESCE({desc_hdr}, '') AS description,
            TRIM(COALESCE(MAX(u.nomuser), '') || ' ' || COALESCE(MAX(u.prenomuser), '')) AS utilisateur,
            (
                SELECT STRING_AGG(f.refvente, ', ' ORDER BY f.refvente)
                FROM (
                    SELECT DISTINCT refvente
                    FROM tb_livraisoncli l2
                    WHERE TRIM(l2.reflivcli) = TRIM(%s)
                      AND l2.refvente IS NOT NULL
                      AND TRIM(l2.refvente) <> ''
                ) f
            ) AS factures,
            (
                SELECT STRING_AGG(DISTINCT l3.refvente, ', ' ORDER BY l3.refvente)
                FROM tb_livraisoncli l3
                WHERE TRIM(l3.reflivcli) = TRIM(%s)
                  AND l3.refvente IS NOT NULL
                  AND TRIM(l3.refvente) <> ''
                  AND {avoir_expr_l3}
            ) AS factures_avoir_apres,
            MAX(
                CASE WHEN {avoir_expr} THEN 1 ELSE 0 END
            ) AS has_avoir_apres
        FROM tb_livraisoncli l
        LEFT JOIN tb_client c ON c.idclient = l.idclient
        LEFT JOIN tb_users u ON u.iduser = l.iduser
        WHERE TRIM(l.reflivcli) = TRIM(%s)
        GROUP BY l.reflivcli
        """,
        tuple(params),
    )
    row = cur.fetchone()
    if not row:
        return {}
    return {
        "refliv": row[0],
        "dt_bl": row[1],
        "dt_bl_fin": row[2],
        "idclient": row[3],
        "nomcli": row[4],
        "nb_lignes": row[5],
        "qte_totale": row[6],
        "transporteur": row[7] or "",
        "description": row[8] or "",
        "utilisateur": row[9] or "",
        "factures": row[10] or "",
        "factures_avoir_apres": row[11] or "",
        "has_avoir_apres": bool(row[12]),
    }


class LivraisonDB:
    _pool: Optional[psycopg2.pool.SimpleConnectionPool] = None
    _extra_cols: Optional[Set[str]] = None

    @classmethod
    def init_pool(cls) -> None:
        if cls._pool is not None:
            return
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(current_dir)
        with open(os.path.join(root_dir, "config.json"), "r", encoding="utf-8") as f:
            db_config = json.load(f)["database"]
        cls._pool = psycopg2.pool.SimpleConnectionPool(1, 5, **db_config)

    @classmethod
    def get_conn(cls):
        cls.init_pool()
        if cls._pool:
            return cls._pool.getconn()
        return None

    @classmethod
    def release_conn(cls, conn) -> None:
        if conn and cls._pool:
            cls._pool.putconn(conn)

    @classmethod
    def table_columns(cls, cur) -> Set[str]:
        if cls._extra_cols is not None:
            return cls._extra_cols
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'tb_livraisoncli'
        """)
        cls._extra_cols = {r[0] for r in cur.fetchall()}
        return cls._extra_cols

    @classmethod
    def generate_bl_ref(cls, cur) -> str:
        year = datetime.now().year
        cur.execute(
            "SELECT COUNT(*) FROM tb_livraisoncli WHERE EXTRACT(YEAR FROM dateregistre) = %s",
            (year,),
        )
        count = cur.fetchone()[0] + 1
        return f"{year}-BL-{count:05d}"

    @classmethod
    def _param_livraison_table_exists(cls, cur) -> bool:
        cur.execute("""
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = 'tb_param_livraison_client'
            LIMIT 1
        """)
        return cur.fetchone() is not None

    @classmethod
    def fetch_param_livraison_client(cls, cur) -> Dict[str, Any]:
        """Ligne unique id=1 : transporteur défaut + flag BL-auto."""
        _default: Dict[str, Any] = {
            "idtransporteur_defaut": None,
            "transporteur_bl_auto": False,
        }
        if not cls._param_livraison_table_exists(cur):
            return _default
        cur.execute("""
            SELECT idtransporteur_defaut, COALESCE(transporteur_bl_auto, 0)
            FROM tb_param_livraison_client
            WHERE id = 1
        """)
        row = cur.fetchone()
        if not row:
            return _default
        return {
            "idtransporteur_defaut": row[0],
            "transporteur_bl_auto": bool(row[1]),
        }

    @classmethod
    def save_param_livraison_client(
        cls,
        cur,
        idtransporteur_defaut: Optional[int],
        transporteur_bl_auto: bool,
    ) -> None:
        if not cls._param_livraison_table_exists(cur):
            raise RuntimeError(
                "Table tb_param_livraison_client absente — "
                "exécutez sql/script_de_mis_a_jour.sql"
            )
        cur.execute(
            """
            INSERT INTO tb_param_livraison_client
                (id, idtransporteur_defaut, transporteur_bl_auto)
            VALUES (1, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                idtransporteur_defaut = EXCLUDED.idtransporteur_defaut,
                transporteur_bl_auto = EXCLUDED.transporteur_bl_auto
            """,
            (idtransporteur_defaut, 1 if transporteur_bl_auto else 0),
        )

    @classmethod
    def fetch_transporteurs(cls, cur) -> List[Tuple[int, str]]:
        cur.execute("""
            SELECT idtransporteur, nom
            FROM tb_transporteur
            WHERE COALESCE(deleted, 0) = 0
            ORDER BY nom
        """)
        return cur.fetchall()

    @classmethod
    def _magasin_auto_column_exists(cls, cur) -> bool:
        cur.execute("""
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'tb_magasin'
              AND column_name = 'livraison_auto_client'
            LIMIT 1
        """)
        return cur.fetchone() is not None

    @classmethod
    def fetch_magasins_livraison_auto(cls, cur) -> List[Tuple[int, str, bool]]:
        """Liste (idmag, designationmag, livraison_auto_active)."""
        if not cls._magasin_auto_column_exists(cur):
            cur.execute("""
                SELECT idmag, designationmag
                FROM tb_magasin
                WHERE COALESCE(deleted, 0) = 0
                ORDER BY designationmag
            """)
            return [(r[0], r[1] or "", False) for r in cur.fetchall()]
        cur.execute("""
            SELECT idmag, designationmag,
                   COALESCE(livraison_auto_client, 0) AS auto_on
            FROM tb_magasin
            WHERE COALESCE(deleted, 0) = 0
            ORDER BY designationmag
        """)
        return [(r[0], r[1] or "", bool(r[2])) for r in cur.fetchall()]

    @classmethod
    def set_magasin_livraison_auto(cls, cur, idmag: int, actif: bool) -> None:
        if not cls._magasin_auto_column_exists(cur):
            raise RuntimeError(
                "Colonne tb_magasin.livraison_auto_client absente — "
                "exécutez sql/script_de_mis_a_jour.sql"
            )
        cur.execute(
            "UPDATE tb_magasin SET livraison_auto_client = %s WHERE idmag = %s",
            (1 if actif else 0, idmag),
        )

    @classmethod
    def generate_bl_ref_auto(cls, cur) -> str:
        year = datetime.now().year
        cur.execute(
            """
            SELECT COUNT(DISTINCT reflivcli) FROM tb_livraisoncli
            WHERE reflivcli ILIKE %s
            """,
            (f"{year}-BL-AUTO-%",),
        )
        count = (cur.fetchone()[0] or 0) + 1
        return f"{year}-BL-AUTO-{count:05d}"

    @classmethod
    def run_livraison_auto_clients(
        cls,
        cur,
        id_user: int,
        idtransporteur_defaut: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Crée un BL-AUTO par facture pour les lignes des magasins en livraison auto.
        Retourne {bl_count, line_count, refs}.
        """
        if not cls._magasin_auto_column_exists(cur):
            return {"bl_count": 0, "line_count": 0, "refs": []}

        sql_lignes = f"""
            SELECT
                v.refvente,
                v.idclient,
                vd.idmag,
                vd.idarticle,
                vd.idunite,
                vd.qtvente,
                COALESCE(lv_sum.total_livre, 0) AS total_livre
            FROM tb_vente v
            INNER JOIN tb_ventedetail vd ON vd.idvente = v.id
            INNER JOIN tb_magasin m ON vd.idmag = m.idmag
                AND COALESCE(m.deleted, 0) = 0
                AND COALESCE(m.livraison_auto_client, 0) = 1
            {SQL_LIVRE_SUM}
            WHERE v.deleted = 0
              AND v.statut = 'VALIDEE'
              AND (vd.qtvente - COALESCE(lv_sum.total_livre, 0)) > 0.0001
              {SQL_FILTER_SANS_AVOIR}
            ORDER BY v.refvente, vd.idmag, vd.idarticle
        """
        cur.execute(sql_lignes)
        rows = cur.fetchall()
        if not rows:
            return {"bl_count": 0, "line_count": 0, "refs": []}

        par_facture: Dict[str, List[tuple]] = defaultdict(list)
        idclient_par_facture: Dict[str, int] = {}
        for row in rows:
            refvente, idclient, idmag, idarticle, idunite, qtvente, total_livre = row
            par_facture[refvente].append(row)
            idclient_par_facture[refvente] = idclient

        cls.table_columns(cur)
        cols = cls._extra_cols or set()
        has_trans = "idtransporteur" in cols
        has_desc = "description_livraison" in cols
        now = datetime.now()
        id_trans = idtransporteur_defaut
        desc_auto = "Livraison automatique (magasin paramétré)"

        base_cols = [
            "reflivcli", "refvente", "idmag", "idarticle", "idunite",
            "qtvente", "qtlivrecli", "dateregistre", "iduser", "idclient",
        ]
        if has_trans:
            base_cols.append("idtransporteur")
        if has_desc:
            base_cols.append("description_livraison")
        placeholders = ", ".join(["%s"] * len(base_cols))
        sql_ins = (
            f"INSERT INTO tb_livraisoncli ({', '.join(base_cols)}) "
            f"VALUES ({placeholders})"
        )

        refs_bl: List[str] = []
        line_count = 0

        for refvente, lignes in par_facture.items():
            refliv = cls.generate_bl_ref_auto(cur)
            refs_bl.append(refliv)
            idclient = idclient_par_facture[refvente]
            for _ref, _idc, idmag, idarticle, idunite, qtvente, total_livre in lignes:
                qte = float(qtvente or 0) - float(total_livre or 0)
                if qte <= 0.0001:
                    continue
                row_vals: List[Any] = [
                    refliv, refvente, idmag, idarticle, idunite,
                    qte, qte, now, id_user, idclient,
                ]
                if has_trans:
                    row_vals.append(id_trans)
                if has_desc:
                    row_vals.append(desc_auto)
                cur.execute(sql_ins, row_vals)
                line_count += 1

        return {
            "bl_count": len(refs_bl),
            "line_count": line_count,
            "refs": refs_bl,
        }

    @classmethod
    def insert_bl(
        cls,
        cur,
        refliv: str,
        lignes: List[Dict[str, Any]],
        id_user: int,
        idtransporteur: Optional[int],
        description: str,
    ) -> None:
        cols = cls.table_columns(cur)
        now = datetime.now()
        has_trans = "idtransporteur" in cols
        has_desc = "description_livraison" in cols

        base_cols = [
            "reflivcli", "refvente", "idmag", "idarticle", "idunite",
            "qtvente", "qtlivrecli", "dateregistre", "iduser", "idclient",
        ]
        if has_trans:
            base_cols.append("idtransporteur")
        if has_desc:
            base_cols.append("description_livraison")

        placeholders = ", ".join(["%s"] * len(base_cols))
        sql = f"INSERT INTO tb_livraisoncli ({', '.join(base_cols)}) VALUES ({placeholders})"

        for ln in lignes:
            if float(ln.get("qtlivrer", 0)) <= 0:
                continue
            row = [
                refliv,
                ln["refvente"],
                ln["idmag"],
                ln["idarticle"],
                ln["idunite"],
                ln["qtvente"],
                float(ln["qtlivrer"]),
                now,
                id_user,
                ln["idclient"],
            ]
            if has_trans:
                row.append(idtransporteur)
            if has_desc:
                row.append(description or None)
            cur.execute(sql, row)


def formater_nombre(nombre) -> str:
    try:
        val = float(nombre)
        if val == int(val):
            return f"{int(val):,}".replace(",", ".")
        return f"{val:,.2f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    except (TypeError, ValueError):
        return "0"


def ligne_panier_key(refvente, idarticle, idunite, idmag) -> Tuple:
    return (refvente, int(idarticle), int(idunite), int(idmag))


def fetch_lignes_bl_pour_pdf(cur, refliv: str) -> List[Dict[str, Any]]:
    """Lignes d'un BL au format attendu par generer_pdf_bl."""
    cur.execute(
        """
        SELECT
            l.refvente,
            u.codearticle,
            COALESCE(a.designation, '') AS designation,
            COALESCE(u.designationunite, '') AS designationunite,
            COALESCE(m.designationmag, '') AS designationmag,
            COALESCE(l.qtlivrecli, 0) AS qtlivrecli
        FROM tb_livraisoncli l
        INNER JOIN tb_article a ON a.idarticle = l.idarticle
        INNER JOIN tb_unite u ON u.idarticle = l.idarticle AND u.idunite = l.idunite
        LEFT JOIN tb_magasin m ON m.idmag = l.idmag
        WHERE TRIM(l.reflivcli) = TRIM(%s)
        ORDER BY l.refvente NULLS LAST, a.designation, l.idlivcli
        """,
        (refliv,),
    )
    out: List[Dict[str, Any]] = []
    for refv, code, des, unite, mag, qtl in cur.fetchall():
        q = float(qtl or 0)
        if q <= 0:
            continue
        out.append({
            "refvente": refv or "",
            "code": code or "",
            "designation": des or "",
            "unite": unite or "",
            "magasin": mag or "",
            "qtlivrer": q,
        })
    return out


def generer_pdf_bl(
    refliv: str,
    nom_client: str,
    lignes: List[Dict[str, Any]],
    id_user: int,
    transporteur: str = "",
    description: str = "",
    *,
    duplicata: bool = False,
    date_operation: Optional[str] = None,
) -> str:
    """
    PDF BL au format A5 paysage (même gabarit que Bon de réception — EtatsPDF_Mouvements).
    """
    from EtatsPDF_Mouvements import EtatPDFMouvements

    pages_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(pages_dir)
    etats_dir = os.path.join(project_dir, "Etats Impression")
    os.makedirs(etats_dir, exist_ok=True)
    prefix = "DUPLICATA_" if duplicata else ""
    path = os.path.join(etats_dir, f"{prefix}BL_{refliv.replace('-', '_')}_A5.pdf")

    nom_user = ""
    conn = LivraisonDB.get_conn()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT nomuser, prenomuser FROM tb_users WHERE iduser = %s",
                (id_user,),
            )
            u = cur.fetchone()
            if u:
                nom_user = f"{u[0] or ''} {u[1] or ''}".strip()
        finally:
            LivraisonDB.release_conn(conn)

    mags = sorted({str(ln.get("magasin") or "").strip() for ln in lignes if ln.get("magasin")})
    if len(mags) > 2:
        magasin_aff = f"{', '.join(mags[:2])} (+{len(mags) - 2})"
    else:
        magasin_aff = ", ".join(mags) if mags else "—"

    factures = sorted({str(ln.get("refvente") or "").strip() for ln in lignes if ln.get("refvente")})
    desc_parts = [f"Client : {nom_client}"]
    if factures:
        desc_parts.append(f"Facture(s) : {', '.join(factures)}")
    if transporteur:
        desc_parts.append(f"Transporteur : {transporteur}")
    if description:
        desc_parts.append(description)
    desc_full = " | ".join(desc_parts)

    cols = ("Code", "Désignation", "Unité", "Qté livrée", "Facture", "Magasin")
    rows_pdf = []
    for ln in lignes:
        q = float(ln.get("qtlivrer", 0))
        if q <= 0:
            continue
        rows_pdf.append((
            ln.get("code", ""),
            ln.get("designation", ""),
            ln.get("unite", ""),
            formater_nombre(q),
            ln.get("refvente", ""),
            ln.get("magasin", ""),
        ))

    etat = EtatPDFMouvements()
    try:
        try:
            etat.connect_db()
        except Exception:
            pass
        dt_op = date_operation or datetime.now().strftime("%d/%m/%Y %H:%M")
        ok = etat._build_pdf_a5(
            output_path=path,
            titre_entete="BON DE LIVRAISON",
            reference=refliv,
            date_operation=dt_op,
            magasin=magasin_aff,
            operateur=nom_user or "—",
            table_data=(cols, rows_pdf),
            description=desc_full,
            responsable_1="Le livreur",
            responsable_2=nom_client or "Le client",
            duplicata=duplicata,
            footer_supplement=(
                "<i>CECI EST UN DUPLICATA DU BON DE LIVRAISON</i>" if duplicata else None
            ),
            setting_key="Livraison_BL_OpenA5",
        )
    finally:
        try:
            etat.close_db()
        except Exception:
            pass

    if not ok:
        raise RuntimeError("Échec de la génération du PDF bon de livraison.")
    return path


def generer_pdf_bl_duplicata(refliv: str, id_user: int = 0) -> str:
    """Réimprime un BL existant avec la mention DUPLICATA (données tb_livraisoncli)."""
    refliv = (refliv or "").strip()
    if not refliv:
        raise ValueError("Référence BL vide.")

    conn = LivraisonDB.get_conn()
    if not conn:
        raise RuntimeError("Connexion base indisponible.")
    try:
        cur = conn.cursor()
        LivraisonDB.table_columns(cur)
        header = fetch_detail_bl_header(cur, refliv)
        lignes = fetch_lignes_bl_pour_pdf(cur, refliv)
        if not lignes:
            raise ValueError(f"Aucune ligne livrée pour le BL {refliv}.")

        cur.execute(
            "SELECT MAX(iduser) FROM tb_livraisoncli WHERE TRIM(reflivcli) = TRIM(%s)",
            (refliv,),
        )
        row_uid = cur.fetchone()
        bl_user = int(row_uid[0]) if row_uid and row_uid[0] else 0
        uid = int(id_user) if id_user else bl_user

        dt_bl = header.get("dt_bl")
        if hasattr(dt_bl, "strftime"):
            date_op = dt_bl.strftime("%d/%m/%Y %H:%M")
        elif dt_bl:
            date_op = str(dt_bl)
        else:
            date_op = None

        return generer_pdf_bl(
            refliv,
            header.get("nomcli") or "",
            lignes,
            uid,
            transporteur=header.get("transporteur") or "",
            description=header.get("description") or "",
            duplicata=True,
            date_operation=date_op,
        )
    finally:
        LivraisonDB.release_conn(conn)
