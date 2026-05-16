# -*- coding: utf-8 -*-
import json
import os
import subprocess
from typing import Any

from resource_utils import ensure_app_data_file, get_settings_path


SETTINGS_FILE = "settings.json"

# Clé globale (0 => ne pas ouvrir/imprimer automatiquement les PDFs)
GLOBAL_PRINT_KEY = "Global_Impression"


def load_settings() -> dict[str, Any]:
    try:
        ensure_app_data_file(SETTINGS_FILE)
        with open(get_settings_path(SETTINGS_FILE), "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_settings(settings: dict[str, Any]) -> bool:
    try:
        path = get_settings_path(SETTINGS_FILE)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings or {}, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def _to_int_bool(value: Any, default: int = 1) -> int:
    if value is None:
        return 1 if default else 0
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        return 1 if int(value) != 0 else 0
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"1", "true", "vrai", "oui", "yes", "y"}:
            return 1
        if v in {"0", "false", "faux", "non", "no", "n"}:
            return 0
    return 1 if default else 0


def is_setting_enabled(key: str, default: int = 1, settings: dict[str, Any] | None = None) -> bool:
    settings = settings if settings is not None else load_settings()
    return _to_int_bool(settings.get(key, default), default=default) == 1


def is_global_print_enabled(settings: dict[str, Any] | None = None, default: int = 1) -> bool:
    settings = settings if settings is not None else load_settings()
    return _to_int_bool(settings.get(GLOBAL_PRINT_KEY, default), default=default) == 1


def open_file_if_enabled(
    path: str,
    operation: str = "open",
    settings: dict[str, Any] | None = None,
    setting_key: str | None = None,
    setting_default: int = 1,
) -> bool:
    """
    operation:
      - "open"  : ouvre le fichier avec l'app par défaut
      - "print" : envoie à l'impression (Windows seulement)
    """
    if not path:
        return False

    if not is_global_print_enabled(settings=settings, default=1):
        return False

    if setting_key:
        try:
            if not is_setting_enabled(setting_key, default=setting_default, settings=(settings or load_settings())):
                return False
        except Exception:
            # En cas d'erreur de lecture settings, on garde le comportement historique (autoriser)
            pass

    try:
        abs_path = os.path.abspath(path)
        if os.name == "nt":
            if operation == "print":
                os.startfile(abs_path, "print")
            else:
                os.startfile(abs_path)
        else:
            # macOS/Linux
            if operation == "print":
                # Pas d'équivalent générique fiable ici; on se limite à l'ouverture.
                subprocess.Popen(["open", abs_path])  # noqa: S603,S607
            else:
                subprocess.Popen(["open", abs_path])  # noqa: S603,S607
        return True
    except Exception:
        return False

