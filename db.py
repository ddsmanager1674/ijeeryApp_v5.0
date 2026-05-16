# -*- coding: utf-8 -*-
"""
Point d'accès unique à PostgreSQL pour iJeery.
Usage :
    from db import get_connection, ensure_connection, connection, transaction
    with connection() as conn:
        ...
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

import psycopg2

from resource_utils import get_config_path

_BASE = os.path.dirname(os.path.abspath(__file__))

_default_manager: Optional["DatabaseManager"] = None


def load_db_config() -> Optional[Dict[str, Any]]:
    """Charge la section database depuis config.json."""
    paths = [
        get_config_path("config.json"),
        os.path.join(_BASE, "config.json"),
        "config.json",
    ]
    seen = set()
    for p in paths:
        if not p or p in seen:
            continue
        seen.add(p)
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)["database"]
            except Exception as e:
                print(f"[DB] config.json invalide ({p}): {e}")
    print("[DB] config.json introuvable.")
    return None


class DatabaseManager:
    """Connexion PostgreSQL centralisée avec retry simple."""

    def __init__(self):
        self.db_params = load_db_config()

    def get_connection(self):
        if not self.db_params:
            return None
        try:
            conn = psycopg2.connect(
                host=self.db_params["host"],
                user=self.db_params["user"],
                password=self.db_params["password"],
                database=self.db_params["database"],
                port=self.db_params["port"],
                connect_timeout=10,
            )
            print("[DB] Connexion établie.")
            return conn
        except psycopg2.OperationalError as e:
            print(f"[DB] {e}")
            return None

    def ensure_connection(self, conn=None):
        """Retourne une connexion active ; reconnecte si fermée ou invalide."""
        if conn is not None and not getattr(conn, "closed", True):
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                return conn
            except psycopg2.Error:
                try:
                    conn.close()
                except Exception:
                    pass
        return self.get_connection()


def _manager() -> DatabaseManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = DatabaseManager()
    return _default_manager


def get_connection():
    """Ouvre une nouvelle connexion (ou None si config absente)."""
    return _manager().get_connection()


def ensure_connection(conn=None):
    """Ping/reconnect sur conn existante ou nouvelle connexion."""
    return _manager().ensure_connection(conn)


@contextmanager
def connection() -> Generator[Any, None, None]:
    """Context manager : ouvre et ferme une connexion."""
    conn = get_connection()
    try:
        yield conn
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


@contextmanager
def transaction(conn=None) -> Generator[Any, None, None]:
    """Context manager : commit si OK, rollback si exception."""
    own = conn is None
    if own:
        conn = get_connection()
    if conn is None:
        yield None
        return
    try:
        yield conn
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        if own and conn is not None:
            try:
                conn.close()
            except Exception:
                pass
