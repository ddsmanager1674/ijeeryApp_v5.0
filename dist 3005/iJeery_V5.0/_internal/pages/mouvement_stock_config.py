# -*- coding: utf-8 -*-
"""Préférences personnelles Mouvement de stock — stockées dans settings.json."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from settings_utils import load_settings, save_settings
except ImportError:
    from settings_utils import load_settings, save_settings

# ── Clés settings.json (groupe MouvementStock) ───────────────────────────────
GROUPE_MOUVEMENT_STOCK = "MouvementStock"
COMMENTAIRE_GROUPE = (
    "Préférences personnelles du menu Mouvement de stock "
    "(par id utilisateur tb_users.iduser)."
)
CLE_MENU_DEFAUT = "MenuDefautParUtilisateur"
# 1 = barre latérale repliée (icônes seules, mode hamburger)
CLE_SIDEBAR_HAMBURGER = "SidebarHamburgerParUtilisateur"


def _cle_utilisateur(iduser: Optional[int]) -> str:
    try:
        return str(int(iduser)) if iduser is not None else "0"
    except (TypeError, ValueError):
        return "0"


def _groupe_mouvement_stock(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Retourne le dict MouvementStock, le crée si absent."""
    grp = settings.get(GROUPE_MOUVEMENT_STOCK)
    if not isinstance(grp, dict):
        grp = {
            "_comment": COMMENTAIRE_GROUPE,
            CLE_MENU_DEFAUT: {},
            CLE_SIDEBAR_HAMBURGER: {},
        }
        settings[GROUPE_MOUVEMENT_STOCK] = grp
    if "_comment" not in grp:
        grp["_comment"] = COMMENTAIRE_GROUPE
    if CLE_MENU_DEFAUT not in grp or not isinstance(grp[CLE_MENU_DEFAUT], dict):
        grp[CLE_MENU_DEFAUT] = {}
    if CLE_SIDEBAR_HAMBURGER not in grp or not isinstance(grp[CLE_SIDEBAR_HAMBURGER], dict):
        grp[CLE_SIDEBAR_HAMBURGER] = {}
    return grp


def _to_bool_pref(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return int(value) != 0
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"1", "true", "vrai", "oui", "yes"}:
            return True
        if v in {"0", "false", "faux", "non", "no"}:
            return False
    return default


def get_menu_defaut_mouvement_stock(iduser: Optional[int]) -> Optional[str]:
    """Menu Mouvement de stock à ouvrir par défaut pour cet utilisateur."""
    settings = load_settings()
    grp = settings.get(GROUPE_MOUVEMENT_STOCK)
    if not isinstance(grp, dict):
        return None
    par_user = grp.get(CLE_MENU_DEFAUT)
    if not isinstance(par_user, dict):
        return None
    val = par_user.get(_cle_utilisateur(iduser))
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def set_menu_defaut_mouvement_stock(
    iduser: Optional[int],
    libelle_menu: str,
) -> bool:
    """Enregistre le menu par défaut (libellé exact du sous-menu)."""
    settings = load_settings()
    grp = _groupe_mouvement_stock(settings)
    grp[CLE_MENU_DEFAUT][_cle_utilisateur(iduser)] = libelle_menu.strip()
    return save_settings(settings)


def get_sidebar_hamburger_defaut(
    iduser: Optional[int],
    default: bool = True,
) -> bool:
    """True = sidebar repliée (mode icônes / hamburger actif par défaut)."""
    settings = load_settings()
    grp = settings.get(GROUPE_MOUVEMENT_STOCK)
    if not isinstance(grp, dict):
        return default
    par_user = grp.get(CLE_SIDEBAR_HAMBURGER)
    if not isinstance(par_user, dict):
        return default
    return _to_bool_pref(par_user.get(_cle_utilisateur(iduser)), default=default)


def set_sidebar_hamburger_defaut(
    iduser: Optional[int],
    hamburger_actif: bool,
) -> bool:
    """Enregistre l'état par défaut de la barre latérale (repliée si True)."""
    settings = load_settings()
    grp = _groupe_mouvement_stock(settings)
    grp[CLE_SIDEBAR_HAMBURGER][_cle_utilisateur(iduser)] = bool(hamburger_actif)
    return save_settings(settings)


def resoudre_menu_defaut(
    iduser: Optional[int],
    menus_visibles: List[str],
    fallback: Optional[str] = None,
) -> str:
    """
    Retourne le libellé du menu à ouvrir : préférence utilisateur si visible,
    sinon premier menu visible, sinon fallback.
    """
    if not menus_visibles:
        return fallback or ""
    pref = get_menu_defaut_mouvement_stock(iduser)
    if pref and pref in menus_visibles:
        return pref
    if fallback and fallback in menus_visibles:
        return fallback
    return menus_visibles[0]
