# -*- coding: utf-8 -*-
"""Utilitaires partagés — paramètres Bon de commande fournisseur."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
import psycopg2.pool

from resource_utils import get_config_path


class CommandeFrsDB:
    """Accès base — paramètres commande fournisseur."""

    _pool: Optional[psycopg2.pool.SimpleConnectionPool] = None

    @classmethod
    def init_pool(cls) -> None:
        if cls._pool is not None:
            return
        with open(get_config_path("config.json"), encoding="utf-8") as f:
            db = json.load(f)["database"]
        cls._pool = psycopg2.pool.SimpleConnectionPool(
            1,
            4,
            host=db["host"],
            user=db["user"],
            password=db["password"],
            database=db["database"],
            port=db["port"],
        )

    @classmethod
    def get_conn(cls):
        cls.init_pool()
        if cls._pool is None:
            return None
        return cls._pool.getconn()

    @classmethod
    def release_conn(cls, conn) -> None:
        if cls._pool and conn:
            cls._pool.putconn(conn)

    @classmethod
    def _param_table_exists(cls, cur) -> bool:
        cur.execute(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = 'tb_param_commande_frs'
            LIMIT 1
            """,
        )
        return cur.fetchone() is not None

    @classmethod
    def fetch_param_commande_frs(cls, cur) -> Dict[str, Any]:
        """Ligne unique id=1 : fournisseur par défaut à l'ouverture."""
        _default: Dict[str, Any] = {"idfrs_defaut": None}
        if not cls._param_table_exists(cur):
            return _default
        cur.execute(
            """
            SELECT idfrs_defaut
            FROM tb_param_commande_frs
            WHERE id = 1
            """,
        )
        row = cur.fetchone()
        if not row:
            return _default
        return {"idfrs_defaut": row[0]}

    @classmethod
    def save_param_commande_frs(
        cls,
        cur,
        idfrs_defaut: Optional[int],
    ) -> None:
        if not cls._param_table_exists(cur):
            raise RuntimeError(
                "Table tb_param_commande_frs absente — "
                "exécutez sql/script_de_mis_a_jour.sql",
            )
        cur.execute(
            """
            INSERT INTO tb_param_commande_frs (id, idfrs_defaut)
            VALUES (1, %s)
            ON CONFLICT (id) DO UPDATE SET
                idfrs_defaut = EXCLUDED.idfrs_defaut
            """,
            (idfrs_defaut,),
        )

    @classmethod
    def fetch_fournisseurs(cls, cur) -> List[Tuple[int, str]]:
        cur.execute(
            """
            SELECT idfrs, nomfrs
            FROM tb_fournisseur
            WHERE COALESCE(deleted, 0) = 0
            ORDER BY nomfrs
            """,
        )
        return cur.fetchall()


def fournisseur_nom_par_id(
    fournisseurs: List[Tuple[int, str]],
    idfrs: Optional[int],
) -> str:
    if not idfrs:
        return "— Aucun —"
    for fid, nom in fournisseurs:
        if fid == idfrs:
            return nom or f"Fournisseur #{fid}"
    return "— Aucun —"
