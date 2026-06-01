# -*- coding: utf-8 -*-
"""Paramètres globaux Stock Article — settings.json."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

try:
    from settings_utils import load_settings, save_settings
except ImportError:
    from settings_utils import load_settings, save_settings

GROUPE_STOCK_ARTICLE = "StockArticle"
COMMENTAIRE_GROUPE = (
    "Paramètres globaux du menu Stock Article. "
    "Liste vide = toutes les fonctions autorisées au double-clic inventaire."
)
CLE_FONCTIONS_AUTORISEES_INVENTAIRE = "FonctionsAutoriseesInventaire"


def _groupe_stock_article(settings: Dict[str, Any]) -> Dict[str, Any]:
    grp = settings.get(GROUPE_STOCK_ARTICLE)
    if not isinstance(grp, dict):
        grp = {
            "_comment": COMMENTAIRE_GROUPE,
            CLE_FONCTIONS_AUTORISEES_INVENTAIRE: [],
        }
        settings[GROUPE_STOCK_ARTICLE] = grp
    if "_comment" not in grp:
        grp["_comment"] = COMMENTAIRE_GROUPE
    if CLE_FONCTIONS_AUTORISEES_INVENTAIRE not in grp:
        grp[CLE_FONCTIONS_AUTORISEES_INVENTAIRE] = []
    return grp


def _parse_id_list(value: Any) -> List[int]:
    if not isinstance(value, list):
        return []
    out: List[int] = []
    for item in value:
        try:
            out.append(int(item))
        except (TypeError, ValueError):
            continue
    return out


def get_fonctions_autorisees_inventaire() -> Optional[Set[int]]:
    """
    Ensemble des idfonction autorisées au double-clic inventaire.
    None si liste vide ou absente => aucune restriction (tout le monde).
    """
    settings = load_settings()
    grp = settings.get(GROUPE_STOCK_ARTICLE)
    if not isinstance(grp, dict):
        return None
    ids = _parse_id_list(grp.get(CLE_FONCTIONS_AUTORISEES_INVENTAIRE))
    if not ids:
        return None
    return set(ids)


def set_fonctions_autorisees_inventaire(idfonctions: List[int]) -> bool:
    """Enregistre les fonctions cochées. Liste vide = tout le monde autorisé."""
    settings = load_settings()
    grp = _groupe_stock_article(settings)
    grp[CLE_FONCTIONS_AUTORISEES_INVENTAIRE] = sorted({int(i) for i in idfonctions})
    return save_settings(settings)


def est_fonction_autorisee_inventaire(idfonction: Optional[int]) -> bool:
    """True si la fonction peut ouvrir l'inventaire au double-clic sur le stock."""
    allowed = get_fonctions_autorisees_inventaire()
    if allowed is None:
        return True
    if idfonction is None:
        return False
    try:
        return int(idfonction) in allowed
    except (TypeError, ValueError):
        return False
