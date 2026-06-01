# -*- coding: utf-8 -*-
"""Vérification des autorisations menu (session / tb_autorisation)."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Set

# Clés tb_menu — liens ⚙ Paramètres / 🔧 Configuration in-page
CLE_PARAM_STOCK = "Paramètres Stock Article"
CLE_PARAM_LIVRAISON = "Paramètres Bon de Livraison"
CLE_PARAM_MOUVEMENT = "Paramètres Mouvement Stock"
CLE_PARAM_COMMANDE_FRS = "Paramètres Commande Fournisseur"
CLE_PARAM_LISTE_MVT = "Paramètres Liste mouvements"
CLE_PARAM_PRIX = "Paramètres Prix Article"
CLE_CONF_MOUVEMENT = "Configuration Mouvement Stock"
CLE_CONF_LISTE_MVT = "Configuration Liste mouvements"
CLE_CONF_PRIX = "Configuration Prix Article"

BLOC_PARAMETRES_MODULES = "BLOC: PARAMÈTRES MODULES"

BLOC_LOGISTIQUE = "BLOC: LOGISTIQUE"

CLES_LOGISTIQUE: tuple[str, ...] = (
    "Parc Vehicule",
    "Pieces Detachees",
    "Carburant",
    "Itineraires",
    "Bons Sortie",
    "Maintenance",
    "Rapport Logistique",
)

PAGES_LOGISTIQUE: Dict[str, str] = {
    BLOC_LOGISTIQUE: "",
    "Parc Vehicule": "pages.page_parcVehicule",
    "Pieces Detachees": "pages.page_piecesDetachees",
    "Carburant": "pages.page_carburant",
    "Itineraires": "pages.page_itineraires",
    "Bons Sortie": "pages.page_bonsSortie",
    "Maintenance": "pages.page_maintenance",
    "Rapport Logistique": "pages.page_rapportLogistique",
}

CLES_PARAMETRES_MODULES: tuple[str, ...] = (
    CLE_PARAM_STOCK,
    CLE_PARAM_LIVRAISON,
    CLE_PARAM_MOUVEMENT,
    CLE_PARAM_COMMANDE_FRS,
    CLE_PARAM_LISTE_MVT,
    CLE_PARAM_PRIX,
    CLE_CONF_MOUVEMENT,
    CLE_CONF_LISTE_MVT,
    CLE_CONF_PRIX,
)


def resolve_session_data(widget: Any) -> dict:
    """Remonte la hiérarchie widgets pour trouver session_data."""
    w = widget
    while w is not None:
        for attr in ("session_data", "_session_data"):
            sd = getattr(w, attr, None)
            if isinstance(sd, dict) and sd:
                return sd
        try:
            w = w.master
        except Exception:
            break
    return {}


def menus_autorises(session_data: Optional[dict]) -> Set[str]:
    menus = (session_data or {}).get("menus") or []
    return {str(m[0]) for m in menus if m and m[0]}


def est_lien_param_autorise(session_data: Optional[dict], menu_key: str) -> bool:
    """True si la fonction utilisateur a le menu coché dans Autorisation."""
    return menu_key in menus_autorises(session_data)


def appliquer_visibilite_lien(widget: Any, visible: bool) -> None:
    if visible:
        try:
            if not widget.winfo_ismapped():
                widget.pack(side="left", padx=(0, 14))
        except Exception:
            pass
    else:
        try:
            widget.pack_forget()
        except Exception:
            pass


def appliquer_visibilite_lien_pack(
    widget: Any,
    visible: bool,
    *,
    side: str = "left",
    padx=(0, 14),
    **pack_kw,
) -> None:
    if visible:
        try:
            if not widget.winfo_ismapped():
                widget.pack(side=side, padx=padx, **pack_kw)
        except Exception:
            pass
    else:
        try:
            widget.pack_forget()
        except Exception:
            pass


def noms_menus_param_modules() -> Iterable[str]:
    yield BLOC_PARAMETRES_MODULES
    yield from CLES_PARAMETRES_MODULES


def noms_menus_logistique() -> Iterable[str]:
    yield BLOC_LOGISTIQUE
    yield from CLES_LOGISTIQUE
