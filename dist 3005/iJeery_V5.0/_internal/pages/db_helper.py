# -*- coding: utf-8 -*-
"""Helper connexion DB pour les pages."""

from typing import Any, Optional

from db import ensure_connection, get_connection


def connect_page_db(db_conn: Optional[Any] = None):
    """Retourne une connexion active (réutilise db_conn si encore valide)."""
    return ensure_connection(db_conn)
