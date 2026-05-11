# -*- coding: utf-8 -*-
"""
Chemins d'export des PDF / tickets générés par l'application.
Paramètres : settings.json → ImpressionPdf_EnregistrerFichiers, ImpressionPdf_DossierRelatif
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
from typing import Any, Optional, Tuple

from settings_utils import load_settings

# 1 = enregistrer sous le dossier relatif à la racine d'écriture de l'app ; 0 = fichier temporaire + ouverture
KEY_ENREGISTRER = "ImpressionPdf_EnregistrerFichiers"
# Sous-dossier relatif à la racine d'écriture (défaut "." = racine projet / dossier exe)
KEY_DOSSIER_REL = "ImpressionPdf_DossierRelatif"


def _to_int(v: Any, default: int = 1) -> int:
    if v is None:
        return default
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, (int, float)):
        return 1 if int(v) != 0 else 0
    if isinstance(v, str):
        t = v.strip().lower()
        if t in {"1", "true", "vrai", "oui", "yes", "y"}:
            return 1
        if t in {"0", "false", "faux", "non", "no", "n"}:
            return 0
    return default


def application_writable_root() -> str:
    """
    Racine où l'on peut écrire les exports : dossier de l'exécutable (PyInstaller),
    sinon répertoire du projet (dossier parent de ce fichier = racine app).
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def normalize_relative_subpath(raw: str) -> str:
    """Nettoie un chemin relatif ; refuse les segments '..' pour éviter l'évasion de dossier."""
    s = (raw or ".").strip().replace("\\", "/")
    if not s or s in {".", "./"}:
        return "."
    parts: list[str] = []
    for p in s.split("/"):
        if not p or p == ".":
            continue
        if p == "..":
            continue
        parts.append(p)
    return os.path.join(*parts) if parts else "."


def _effective_settings(settings: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    merged: dict[str, Any] = dict(default_pdf_export_settings())
    if settings is not None:
        merged.update(settings)
    else:
        ld = load_settings()
        if isinstance(ld, dict):
            merged.update(ld)
    return merged


def pdf_save_to_disk_enabled(settings: Optional[dict[str, Any]] = None) -> bool:
    s = _effective_settings(settings)
    return _to_int(s.get(KEY_ENREGISTRER, 1), 1) == 1


def get_configured_export_directory_abs(settings: Optional[dict[str, Any]] = None) -> str:
    s = _effective_settings(settings)
    rel = normalize_relative_subpath(str(s.get(KEY_DOSSIER_REL, ".") or "."))
    root = application_writable_root()
    if rel == ".":
        return os.path.normpath(root)
    return os.path.normpath(os.path.join(root, rel))


def folder_to_relative_export_path(selected_dir: str) -> Optional[str]:
    """
    Convertit un dossier choisi via l'explorateur en chemin relatif stocké dans settings
    (sous la racine d'écriture de l'application uniquement).
    Retourne None si le dossier n'est pas sous cette racine ou n'existe pas.
    """
    root = os.path.normpath(os.path.abspath(application_writable_root()))
    sel = os.path.normpath(os.path.abspath(selected_dir))
    if not os.path.isdir(sel):
        return None
    try:
        common = os.path.normpath(os.path.commonpath([root, sel]))
    except ValueError:
        return None
    if os.path.normcase(common) != os.path.normcase(root):
        return None
    rel = os.path.relpath(sel, root)
    if rel in (".", ""):
        return "."
    return rel.replace("\\", "/")


def sanitize_export_filename(name: str) -> str:
    base = os.path.basename(str(name).strip()) or "document"
    base = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", base)
    return base


def build_impression_output_path(
    filename: str,
    settings: Optional[dict[str, Any]] = None,
    *,
    temp_prefix: str = "ijeery_",
) -> Tuple[str, bool]:
    """
    Construit le chemin absolu pour un PDF ou ticket exporté.

    Returns:
        (chemin_absolu, est_temporaire)
        est_temporaire True si l'enregistrement configuré est désactivé (fichier dans %TMP%).
    """
    s = _effective_settings(settings)
    safe_name = sanitize_export_filename(filename)
    ext = os.path.splitext(safe_name)[1] or ".pdf"

    if not pdf_save_to_disk_enabled(s):
        fd, path = tempfile.mkstemp(prefix=temp_prefix, suffix=ext)
        os.close(fd)
        return os.path.abspath(path), True

    out_dir = get_configured_export_directory_abs(s)
    os.makedirs(out_dir, exist_ok=True)
    return os.path.abspath(os.path.join(out_dir, safe_name)), False


def default_pdf_export_settings() -> dict[str, Any]:
    """Valeurs par défaut à fusionner si absentes de settings.json."""
    return {
        KEY_ENREGISTRER: 1,
        KEY_DOSSIER_REL: ".",
    }
