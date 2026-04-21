import json
import os
from typing import Any, Optional

import psycopg2

from resource_utils import get_config_path


def _build_description(
    action: str,
    element: str,
    details: str,
    value: str,
    username: str,
    computer_name: str,
) -> str:
    element_txt = element or "élément"
    details_txt = details or "aucun détail"
    value_txt = value or "aucune valeur"
    user_txt = username or "Inconnu"
    pc_txt = computer_name or os.environ.get("COMPUTERNAME", "") or "PC-Inconnu"
    return (
        f"{action} de '{element_txt}' "
        f"(détails: {details_txt}, valeur: {value_txt}) "
        f"par '{user_txt}' sur '{pc_txt}'."
    )


class AppLogger:
    """Logger applicatif centralisé vers tb_log_evenements."""

    def __init__(self, conn: Optional[Any] = None, session_data: Optional[dict] = None, fallback_user_id: Optional[int] = None):
        self.conn = conn
        self.session_data = session_data or {}
        self.fallback_user_id = fallback_user_id

    def _connect(self):
        with open(get_config_path("config.json"), "r", encoding="utf-8") as f:
            config = json.load(f)
        db = config["database"]
        return psycopg2.connect(
            host=db["host"],
            user=db["user"],
            password=db["password"],
            database=db["database"],
            port=db["port"],
        )

    def _resolve_user_id(self) -> Optional[int]:
        candidates = [
            self.session_data.get("user_id"),
            self.session_data.get("iduser"),
            self.fallback_user_id,
        ]
        for value in candidates:
            if value is not None:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    continue
        return None

    def _resolve_username(self, conn) -> str:
        username = self.session_data.get("username") or self.session_data.get("user_name")
        if username:
            return str(username)

        user_id = self._resolve_user_id()
        if user_id is None:
            return "Inconnu"

        try:
            with conn.cursor() as cur:
                cur.execute("SELECT username FROM tb_users WHERE iduser=%s", (user_id,))
                row = cur.fetchone()
            return row[0] if row and row[0] else f"user#{user_id}"
        except Exception:
            return f"user#{user_id}"

    def _resolve_computer_name(self) -> str:
        return (
            self.session_data.get("computer_name")
            or os.environ.get("COMPUTERNAME")
            or os.environ.get("HOSTNAME")
            or "PC-Inconnu"
        )

    def log(
        self,
        action: str,
        element: str,
        details: str = "aucun détail",
        value: str = "aucune valeur",
        username: Optional[str] = None,
    ):
        own_conn = False
        conn = self.conn
        try:
            if conn is None or getattr(conn, "closed", 1):
                conn = self._connect()
                own_conn = True

            who = username or self._resolve_username(conn)
            pc_name = self._resolve_computer_name()
            description = _build_description(action, element, details, value, who, pc_name)

            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO tb_log_evenements (description, "user")
                    VALUES (%s, %s)
                    """,
                    (description, who),
                )
            conn.commit()
        except Exception:
            # On ne bloque jamais le flux métier pour un log.
            pass
        finally:
            if own_conn and conn:
                try:
                    conn.close()
                except Exception:
                    pass
