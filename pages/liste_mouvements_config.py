# -*- coding: utf-8 -*-
"""Préférences personnelles Liste mouvements — stockées dans settings.json."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from settings_utils import load_settings, save_settings
except ImportError:
    from settings_utils import load_settings, save_settings

GROUPE_LISTE_MOUVEMENTS = "ListeMouvements"
COMMENTAIRE_GROUPE = (
    "Préférences personnelles du menu Liste mouvements "
    "(par id utilisateur tb_users.iduser). "
    "MenuDefaut : clé interne (entree, sortie, transfert, …)."
)
CLE_MENU_DEFAUT = "MenuDefautParUtilisateur"
CLE_SIDEBAR_HAMBURGER = "SidebarHamburgerParUtilisateur"


def _cle_utilisateur(iduser: Optional[int]) -> str:
    try:
        return str(int(iduser)) if iduser is not None else "0"
    except (TypeError, ValueError):
        return "0"


def _groupe_liste_mouvements(settings: Dict[str, Any]) -> Dict[str, Any]:
    grp = settings.get(GROUPE_LISTE_MOUVEMENTS)
    if not isinstance(grp, dict):
        grp = {
            "_comment": COMMENTAIRE_GROUPE,
            CLE_MENU_DEFAUT: {},
            CLE_SIDEBAR_HAMBURGER: {},
        }
        settings[GROUPE_LISTE_MOUVEMENTS] = grp
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


def get_menu_defaut_liste_mouvements(iduser: Optional[int]) -> Optional[str]:
    settings = load_settings()
    grp = settings.get(GROUPE_LISTE_MOUVEMENTS)
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


def set_menu_defaut_liste_mouvements(iduser: Optional[int], cle_menu: str) -> bool:
    settings = load_settings()
    grp = _groupe_liste_mouvements(settings)
    grp[CLE_MENU_DEFAUT][_cle_utilisateur(iduser)] = cle_menu.strip()
    return save_settings(settings)


def get_sidebar_hamburger_defaut_liste(
    iduser: Optional[int],
    default: bool = True,
) -> bool:
    settings = load_settings()
    grp = settings.get(GROUPE_LISTE_MOUVEMENTS)
    if not isinstance(grp, dict):
        return default
    par_user = grp.get(CLE_SIDEBAR_HAMBURGER)
    if not isinstance(par_user, dict):
        return default
    return _to_bool_pref(par_user.get(_cle_utilisateur(iduser)), default=default)


def set_sidebar_hamburger_defaut_liste(
    iduser: Optional[int],
    hamburger_actif: bool,
) -> bool:
    settings = load_settings()
    grp = _groupe_liste_mouvements(settings)
    grp[CLE_SIDEBAR_HAMBURGER][_cle_utilisateur(iduser)] = bool(hamburger_actif)
    return save_settings(settings)


def resoudre_menu_defaut_liste(
    iduser: Optional[int],
    cles_visibles: List[str],
    fallback: Optional[str] = None,
) -> str:
    if not cles_visibles:
        return fallback or ""
    pref = get_menu_defaut_liste_mouvements(iduser)
    if pref and pref in cles_visibles:
        return pref
    if fallback and fallback in cles_visibles:
        return fallback
    return cles_visibles[0]
