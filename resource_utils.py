# -*- coding: utf-8 -*-
"""
Utilitaire global pour gérer les chemins de ressources dans PyInstaller.
- Assets read-only : get_resource_path / get_bundle_path (_MEIPASS)
- Données utilisateur (JSON) : get_app_data_path (dossier exe / projet, jamais _internal seul)
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from typing import Any, Dict, Optional

try:
    import export_utils  # noqa: F401
except Exception:
    pass

_APP_DATA_FILES = frozenset({
    "config.json",
    "settings.json",
    "session.json",
    "remember.json",
    "config.ini",
})


def application_writable_root() -> str:
    """Dossier où l'application peut écrire (exe en prod, racine projet en dev)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def get_bundle_path(relative_path: str) -> str:
    """Chemin read-only embarqué (PyInstaller _MEIPASS ou racine dev)."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def get_resource_path(relative_path: str) -> str:
    """
    Ressources statiques (images, fonts, pages packagées).
    Pour config/settings/session, préférer get_app_data_path.
    """
    if relative_path.replace("\\", "/").split("/")[-1] in _APP_DATA_FILES:
        return get_app_data_path(os.path.basename(relative_path))
    return get_bundle_path(relative_path)


def get_app_data_path(filename: str) -> str:
    """Chemin absolu d'un fichier de données modifiable à côté de l'exe."""
    return os.path.join(application_writable_root(), filename)


def ensure_app_data_file(
    filename: str,
    default_content: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Garantit l'existence du fichier dans le dossier writable.
    Si absent : copie depuis le bundle ou écrit default_content (sans écraser l'existant).
    """
    dest = get_app_data_path(filename)
    if os.path.isfile(dest):
        return dest

    bundle = get_bundle_path(filename)
    if os.path.isfile(bundle):
        try:
            shutil.copy2(bundle, dest)
            return dest
        except OSError:
            pass

    if default_content is not None:
        try:
            os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
            with open(dest, "w", encoding="utf-8") as f:
                json.dump(default_content, f, indent=2, ensure_ascii=False)
        except OSError:
            pass
    return dest


def init_app_data_files() -> None:
    """Copie initiale des JSON templates au premier lancement (sans écraser)."""
    for name in _APP_DATA_FILES:
        ensure_app_data_file(name)


def get_config_path(filename: str = "config.json") -> str:
    """config.json modifiable (writable)."""
    return get_app_data_path(filename)


def get_session_path(filename: str = "session.json") -> str:
    """session.json modifiable (writable)."""
    return get_app_data_path(filename)


def get_settings_path(filename: str = "settings.json") -> str:
    return get_app_data_path(filename)


def safe_file_read(file_path: str):
    """Lit un fichier en essayant plusieurs encodages."""
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()
            try:
                from app_runtime_log import log_info
                log_info("Fichier %s lu (encodage %s)", os.path.basename(file_path), encoding)
            except Exception:
                print(f"✓ Fichier {os.path.basename(file_path)} lu avec l'encodage: {encoding}")
            return content, encoding
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            raise FileNotFoundError(f"Fichier non trouvé: {file_path}") from None
    raise ValueError(f"Impossible de lire le fichier {file_path} avec les encodages disponibles")


def is_running_as_exe() -> bool:
    return hasattr(sys, "_MEIPASS")


def log_debug_info() -> None:
    print("\n" + "=" * 60)
    print("DEBUG INFO - Contexte d'exécution")
    print("=" * 60)
    print(f"✓ Running as EXE: {is_running_as_exe()}")
    print(f"✓ Writable root: {application_writable_root()}")
    print(f"✓ Bundle path: {get_bundle_path('')}")
    print(f"✓ Config path: {get_config_path()}")
    print(f"✓ Settings path: {get_settings_path()}")
    print(f"✓ Session path: {get_session_path()}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    log_debug_info()
