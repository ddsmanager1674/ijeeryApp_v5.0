# -*- coding: utf-8 -*-
"""Préférences personnelles Prix Article — stockées dans settings.json."""

from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from settings_utils import load_settings, save_settings
except ImportError:
    from settings_utils import load_settings, save_settings

GROUPE_PRIX_ARTICLE = "PrixArticle"
COMMENTAIRE_GROUPE = (
    "Préférences personnelles du menu Prix Article "
    "(par id utilisateur tb_users.iduser)."
)
CLE_AFFICHER_VARIATION = "AfficherVariationPrixParUtilisateur"


def _cle_utilisateur(iduser: Optional[int]) -> str:
    try:
        return str(int(iduser)) if iduser is not None else "0"
    except (TypeError, ValueError):
        return "0"


def _groupe_prix_article(settings: Dict[str, Any]) -> Dict[str, Any]:
    grp = settings.get(GROUPE_PRIX_ARTICLE)
    if not isinstance(grp, dict):
        grp = {
            "_comment": COMMENTAIRE_GROUPE,
            CLE_AFFICHER_VARIATION: {},
        }
        settings[GROUPE_PRIX_ARTICLE] = grp
    if "_comment" not in grp:
        grp["_comment"] = COMMENTAIRE_GROUPE
    if CLE_AFFICHER_VARIATION not in grp or not isinstance(
        grp[CLE_AFFICHER_VARIATION], dict
    ):
        grp[CLE_AFFICHER_VARIATION] = {}
    return grp


def _to_bool_pref(value: Any, default: bool = False) -> bool:
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


def get_afficher_variation_prix_defaut(
    iduser: Optional[int],
    default: bool = False,
) -> bool:
    settings = load_settings()
    grp = settings.get(GROUPE_PRIX_ARTICLE)
    if not isinstance(grp, dict):
        return default
    par_user = grp.get(CLE_AFFICHER_VARIATION)
    if not isinstance(par_user, dict):
        return default
    return _to_bool_pref(par_user.get(_cle_utilisateur(iduser)), default=default)


def set_afficher_variation_prix_defaut(
    iduser: Optional[int],
    afficher: bool,
) -> bool:
    settings = load_settings()
    grp = _groupe_prix_article(settings)
    grp[CLE_AFFICHER_VARIATION][_cle_utilisateur(iduser)] = bool(afficher)
    return save_settings(settings)
