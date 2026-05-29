import json
import os
from typing import Any, Optional

from db import get_connection


def resolve_connected_user_id(
    master=None,
    session_data=None,
    id_user_connecte=None,
    *,
    default: int = 1,
) -> int:
    """Retourne l'ID de l'utilisateur connecté (session app, parent, session.json)."""
    if id_user_connecte is not None:
        try:
            return int(id_user_connecte)
        except (TypeError, ValueError):
            pass

    session_data = session_data or {}
    for key in ("user_id", "iduser"):
        val = session_data.get(key)
        if val is not None:
            try:
                return int(val)
            except (TypeError, ValueError):
                continue

    parent = master
    while parent is not None:
        pid = getattr(parent, "id_user_connecte", None)
        if pid is not None:
            try:
                return int(pid)
            except (TypeError, ValueError):
                return pid
        ps = getattr(parent, "session_data", None) or {}
        for key in ("user_id", "iduser"):
            val = ps.get(key)
            if val is not None:
                try:
                    return int(val)
                except (TypeError, ValueError):
                    continue
        parent = getattr(parent, "master", None)

    try:
        from resource_utils import get_config_path

        session_path = get_config_path("session.json")
        if session_path and os.path.exists(session_path):
            with open(session_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key in ("user_id", "iduser", "id"):
                val = data.get(key)
                if val is not None:
                    return int(val)
    except Exception:
        pass

    return default


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
        return get_connection()

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
