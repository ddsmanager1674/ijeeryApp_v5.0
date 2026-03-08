# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              iJeery — app_main.py  (Shell principal v2.0)                  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Refonte :                                                                  ║
║   • Sidebar entièrement repensée (responsive, toggle hamburger propre)     ║
║   • Toggle collapse → seul l'icône hamburger reste visible                 ║
║   • Sous-menus en accordéon fluide, organisation claire                    ║
║   • Grid-based layout — pas de pack_forget/pack en cascade                 ║
║   • Chargement lazy des pages (imports différés)                            ║
║   • Horloge title-bar sans boucle gourmande                                ║
║   • Couleurs des boutons inchangées (conformément à la demande)            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from typing import Optional, Callable

import customtkinter as ctk
from PIL import Image
from tkinter import messagebox
import psycopg2

# ── Chemins ──────────────────────────────────────────────────────────────────
_BASE = os.path.dirname(os.path.abspath(__file__))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

# ── Thème ─────────────────────────────────────────────────────────────────────
try:
    from app_theme import Colors, Fonts, Theme
    _THEME = True
except ImportError:
    _THEME = False
    class Colors:
        BG_PAGE = "#ECF0F1"; BG_CARD = "#FFFFFF"; MIDNIGHT = "#2C3E50"
        MIDNIGHT_LIGHT = "#34495E"; PRIMARY = "#3498DB"; SILVER = "#BDC3C7"
        TEXT_ON_DARK = "#FFFFFF"; TEXT_MUTED = "#95A5A6"; DIVIDER = "#E8EAED"
    class Fonts:
        @staticmethod
        def get(s=12, w="normal"):
            return ctk.CTkFont(family="Segoe UI", size=s, weight=w)
        @classmethod
        def bold(cls, s=12): return cls.get(s, "bold")
        @classmethod
        def body(cls, s=12): return cls.get(s)

try:
    from theme import load_roboto, apply_global_font
    _HAS_THEME = True
except ImportError:
    _HAS_THEME = False
    def load_roboto(): pass
    def apply_global_font(w): pass

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

def resource_path(rel: str) -> str:
    base = getattr(sys, "_MEIPASS", _BASE)
    return os.path.join(base, rel)

# ── Utilitaire de police rapide ───────────────────────────────────────────────
def _F(size=11, weight="normal"):
    fam = "Roboto" if _THEME else "Segoe UI"
    return ctk.CTkFont(family=fam, size=size, weight=weight)


# ─────────────────────────────────────────────────────────────────────────────
# GESTIONNAIRE DE BASE DE DONNÉES
# ─────────────────────────────────────────────────────────────────────────────

class DatabaseManager:
    """Connexion PostgreSQL centralisée avec retry simple."""

    def __init__(self):
        self.db_params = self._load_config()

    def _load_config(self):
        paths = [
            os.path.join(_BASE, "config.json"),
            "config.json",
        ]
        for p in paths:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        return json.load(f)["database"]
                except Exception as e:
                    print(f"[DB] config.json invalide ({p}): {e}")
        print("[DB] ❌ config.json introuvable.")
        return None

    def get_connection(self):
        if not self.db_params:
            return None
        try:
            conn = psycopg2.connect(
                host=self.db_params["host"],
                user=self.db_params["user"],
                password=self.db_params["password"],
                database=self.db_params["database"],
                port=self.db_params["port"],
                connect_timeout=10,
            )
            print("[DB] ✅ Connexion établie.")
            return conn
        except psycopg2.OperationalError as e:
            print(f"[DB] ❌ {e}")
            return None


# ─────────────────────────────────────────────────────────────────────────────
# DÉFINITION DES MENUS (séparation données / UI)
# ─────────────────────────────────────────────────────────────────────────────
# Format : (label_affiché, clé_auth, module_path, class_name, kwargs_spéciaux)
# kwargs_spéciaux peut être None ou un dict indiquant des args non-standard

MENU_STRUCTURE = [
    # ── TABLEAU DE BORD ────────────────────────────────────────────────────
    {
        "id":    "DASHBOARD",
        "label": "📊  TABLEAU DE BORD",
        "auth":  "TABLEAU DE BORD",
        "color": "#268908",
        "hover": "#4CE01F",
        "module": "pages.page_home",
        "class":  "page_home",
        "subs":  [],
    },
    # ── CHAT INTERNE ───────────────────────────────────────────────────────
    {
        "id":    "CHAT",
        "label": "💬  CHAT INTERNE",
        "auth":  "CHAT INTERNE",
        "color": "#A19407",
        "hover": "#cad256",
        "module": "pages.page_chat",
        "class":  "PageChat",
        "kwargs": "chat",
        "subs":  [],
    },
    # ── COMMERCIALE ────────────────────────────────────────────────────────
    {
        "id":    "COMMERCIALE",
        "label": "🛒  COMMERCIALE",
        "color": "#034787",
        "hover": "#0565c9",
        "subs": [
            ("📦  Article Liste",       "Article Liste",         "pages.page_ArticleListe",    "page_listeArticle",    None),
            ("👤  Client",              "Client",                "pages.page_client",           "PageClient",          None),
            ("🏭  Fournisseur",         "Fournisseur",           "pages.page_fournisseur",      "PageFournisseur",     None),
            ("🏬  Magasin",             "Magasin",               "pages.page_magasin",          "PageMagasin",         None),
            ("📊  Ventes",              "Ventes",                "pages.page_vente",            "PageVente",           "vente"),
            ("💰  Ventes par Dépôt",   "Ventes par Dépôt",      None,                          None,                  "vente_tab"),
            ("📄  Facturation",         "Facturation",           None,                          None,                  "vente_tab"),
            ("📋  Liste Facture",       "Liste Facture",         "pages.page_ListeFacture",     "PageListeFacture",    None),
            ("📦  Stock Article",       "Stock Article",         "pages.page_stock",            "PageStock",           None),
            ("⚠️  Stock Alerte",        "Stock Alerte",          "pages.page_StockAlerte",      "PageStockAlerte",     None),
            ("🛡️  Péremption Article",  "Péremption d'article",  "pages.page_peremption",       "PageGestionPeremption", None),
            ("🚚  Stock Livraison",     "Stock Livraison",       "pages.page_StockLivraison",   "PageStockLivraison",  None),
            ("🔄  Mouvement Article",   "Mouvement d'article",   "pages.page_articleMouvement", "PageArticleMouvement", None),
            ("📊  Mouvement Stock",     "Mouvement Stock",       "pages.page_infoMouvement",    "PageInfoMouvementStock", "iduser"),
            ("📋  Liste Mouvements",    "Liste mouvements",      "pages.page_listeMouvement",   "PageListeMouvement",  None),
            ("📍  Suivi Commande",      "Suivi Commande",        "pages.page_SuiviCommande",    "PageSuiviCommande",   None),
            ("💲  Prix Article",        "Prix d'article",        "pages.page_prixListe",        "PagePrixListe",       None),
            ("📊  Prix de Revient",     "Prix de revient",       "pages.page_prixRevient",      "PagePrixRevient",     None),
            ("🚚  Livraison Client",    "Livraison Client",      "pages.page_LivraisonClient",  "PageLivraisonClient", "vente"),
        ],
    },
    # ── PERSONNEL ──────────────────────────────────────────────────────────
    {
        "id":    "PERSONNEL",
        "label": "👥  PERSONNEL",
        "color": "#036C6B",
        "hover": "#2ec8cd",
        "subs": [
            ("👥  Liste Personnel",     "Liste Personnel",       "pages.page_mainPers",         "PageMainPersonnel",   None),
            ("❌  Absence",             "Absence",               "pages.page_absence",          "PageAbsence",         None),
            ("✅  Présence",            "Présence",              "pages.page_presence",         "PagePresence",        None),
            ("💸  Avance 15e",          "Avance 15e",            "pages.page_avance15e",        "PageAVQ",             "iduser"),
            ("💰  Avance Spéciale",     "Avance Spéciale",       "pages.page_avanceSpecial_",   "FenetreAvanceSpec",   "iduser"),
            ("👔  Fonction",            "Fonction",              "pages.page_fonction",         "PageFonction",        None),
            ("📋  Nouveau SB",          "Nouveau SB",            "pages.page_salaireBase_",     "PageSalaireBase",     "app_root"),
            ("📊  État de Salaire",     "Etat de Salaire",       "pages.page_salaireEtatBase_", "PageSalaireEtatSB",   None),
            ("📊  Salaire Horaire",     "Salaire Horaire",       "pages.page_salaireEtatHoraire_", "PageEtatSalaireHoraire", None),
            ("💲  Taux Horaire",        "Taux Horaire",          "pages.page_tauxhoraire",      "PageTauxHoraire",     "app_root"),
            ("💳  Paiement Salaire",    "Paiement Salaire",      "pages.page_pmtSalaire",       "PageValidationSalaire", None),
        ],
    },
    # ── TRÉSORERIE ─────────────────────────────────────────────────────────
    {
        "id":    "TRESORERIE",
        "label": "💰  TRÉSORERIE",
        "color": "#87035D",
        "hover": "#c936c2",
        "subs": [
            ("🏧  Caisse",              "Caisse",                "pages.page_caisse",           "PageCaisse",          None),
            ("💳  Client à Payer",      "Facture Liste",         "pages.page_factureListe",     "PageFactureListe",    None),
            ("💰  Fournisseur à Payer", "Fournisseur Dettes",    "pages.page_FrsDette",         "PageFrsDette",        None),
            ("🏦  Banque",              "Banque",                "pages.page_banque",           "PageBanque",          None),
            ("➕  Ajout Banque",        "Ajout Banque",          "pages.page_banqueAjout",      "PageBanqueNv",        None),
            ("🔄  Transfert Banque",    "Transfert Banque",      "pages.page_transfertBanque",  "PageTransfertBanque", "vente"),
            ("🔄  Transfert Caisse",    "Transfert Caisse",      "pages.page_transfertCaisse",  "PageTransfertCaisse", "vente"),
            ("💸  Décaissement",        "Decaissement",          "pages.page_decaissement",     "PageDecaissement",    None),
            ("🏦  Décaissement Bq",     "DecaissementBq",        "pages.page_decaissementBq",   "PageDecaissementBq",  None),
            ("📥  Encaissement",        "Encaissement",          "pages.page_encaissement",     "PageEncaissement",    None),
            ("📥  Encaissement Bq",     "EncaissementBq",        "pages.page_encaissementBq",   "PageEncaissementBq",  None),
        ],
    },
    # ── BASE DE DONNÉES ────────────────────────────────────────────────────
    {
        "id":    "DATABASE",
        "label": "🗄️  BASE DE DONNÉES",
        "color": "#874903",
        "hover": "#d7956e",
        "subs": [
            ("🔐  Autorisation",        "Autorisation",          "pages.page_autorisation",     "PageAutorisation",    None),
            ("📅  Événements",          "Evenements",            "pages.page_evenement",        "PageEvenement",       None),
            ("💾  Sauvegarde",          "Sauvegarde",            "pages.page_sauvegarde",       "PageSauvegarde",      None),
            ("👨‍💻  Utilisateurs",       "Utilisateurs",          "pages.page_users",            "PageUsers",           None),
            ("📋  Menu",                "Menu",                  "pages.page_menu",             "PageMenu",            None),
            ("📚  Base Liste",          "Base Liste",            "pages.page_BaseListe",        "PageBaseListe",       None),
            ("🔐  Autorisation Admin",  "Autorisation Admin",    "pages.page_CodeAutorisation", "PageCodeAutorisation", None),
            ("🔧  Init DB",             "Init DB",               "pages.page_reinit",           "DBInitializerApp",    "toplevel"),
        ],
    },
    # ── EXAMEN BLANC ───────────────────────────────────────────────────────
    {
        "id":    "EXAMEN_BLANC",
        "label": "📚  EXAMEN BLANC",
        "color": "#034787",
        "hover": "#0565c9",
        "subs": [
            ("📚  Matière EB",          "Matiere EB",            "pages.page_BaseListe",        "PageBaseListe",       None),
            ("👨‍🎓  Étudiant EB",        "Etudiant EB",           "pages.page_BaseListe",        "PageBaseListe",       None),
            ("📝  Notes EB",            "Notes EB",              "pages.page_BaseListe",        "PageBaseListe",       None),
            ("⚖️  Délibération EB",     "Déliberation EB",       "pages.page_BaseListe",        "PageBaseListe",       None),
            ("🏆  Résultat EB",         "Résultat EB",           "pages.page_BaseListe",        "PageBaseListe",       None),
        ],
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# CHARGEMENT DYNAMIQUE DES PAGES
# ─────────────────────────────────────────────────────────────────────────────

def _lazy_load(module_path: str, class_name: str):
    """Importe un module et retourne la classe demandée (import différé)."""
    try:
        mod = importlib.import_module(module_path)
        return getattr(mod, class_name)
    except ImportError as e:
        print(f"[lazy_load] Import échoué {module_path}.{class_name}: {e}")
        return None
    except AttributeError:
        print(f"[lazy_load] Classe {class_name} introuvable dans {module_path}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# COMPOSANT : BOUTON DE SOUS-MENU (accordéon)
# ─────────────────────────────────────────────────────────────────────────────

class SubMenuButton(ctk.CTkButton):
    """Bouton de sous-menu avec indentation visuelle."""

    def __init__(self, parent, text, command, color, hover, **kw):
        super().__init__(
            parent,
            text=text,
            command=command,
            fg_color=color,
            hover_color=hover,
            text_color="#FFFFFF",
            anchor="w",
            corner_radius=6,
            height=34,
            font=_F(11),
            **kw,
        )


# ─────────────────────────────────────────────────────────────────────────────
# COMPOSANT : ENTRÉE DE MENU PRINCIPAL (avec accordéon)
# ─────────────────────────────────────────────────────────────────────────────

class MenuAccordion(ctk.CTkFrame):
    """
    Bouton principal + frame de sous-menus collapsable.
    Indépendant du gestionnaire de sidebar.
    """

    def __init__(self, parent, cfg: dict, app: "App", sidebar_ref: "Sidebar"):
        super().__init__(parent, fg_color="transparent", corner_radius=0)

        self._cfg        = cfg
        self._app        = app
        self._sidebar    = sidebar_ref
        self._expanded   = False
        self._sub_frame  = None

        color = cfg.get("color", "#034787")
        hover = cfg.get("hover", "#0565c9")

        # Bouton principal
        label = cfg.get("label", "")
        has_subs = bool(cfg.get("subs"))
        arrow_text = "  ▾" if has_subs else ""

        self._main_btn = ctk.CTkButton(
            self,
            text=label + arrow_text,
            fg_color=color,
            hover_color=hover,
            text_color="#FFFFFF",
            anchor="w",
            corner_radius=8,
            height=46,
            font=_F(12, "bold"),
            command=self._on_click,
        )
        self._main_btn.pack(fill="x", padx=6, pady=(2, 0))

        # Frame des sous-menus (caché par défaut)
        if has_subs:
            self._sub_frame = ctk.CTkFrame(self, fg_color="transparent")
            self._build_sub_buttons()
            # Caché initialement

    def _build_sub_buttons(self):
        if not self._sub_frame:
            return
        color = self._cfg.get("color", "#034787")
        hover = self._cfg.get("hover", "#0565c9")
        # Légèrement assombri pour différencier
        for item in self._cfg.get("subs", []):
            lbl, auth, mod_path, cls_name, kwargs_key = item
            btn = SubMenuButton(
                self._sub_frame,
                text="  " + lbl,
                command=lambda m=mod_path, c=cls_name, k=kwargs_key, a=auth: (
                    self._app.navigate(m, c, k, a)
                ),
                color=color,
                hover=hover,
            )
            btn.pack(fill="x", padx=(18, 6), pady=1)

    def _on_click(self):
        if self._cfg.get("subs"):
            self._toggle()
        else:
            # Page directe
            mod   = self._cfg.get("module")
            cls   = self._cfg.get("class")
            kw    = self._cfg.get("kwargs")
            auth  = self._cfg.get("auth", "")
            self._app.navigate(mod, cls, kw, auth)

    def _toggle(self):
        if self._expanded:
            self._collapse()
        else:
            # Fermer les autres accordéons
            self._sidebar.collapse_all_except(self)
            self._expand()

    def _expand(self):
        if self._sub_frame:
            self._sub_frame.pack(fill="x", after=self._main_btn, pady=(0, 2))
            self._expanded = True
            # Mettre à jour la flèche
            cur = self._main_btn.cget("text")
            self._main_btn.configure(text=cur.replace("▾", "▴"))

    def _collapse(self):
        if self._sub_frame:
            self._sub_frame.pack_forget()
            self._expanded = False
            cur = self._main_btn.cget("text")
            self._main_btn.configure(text=cur.replace("▴", "▾"))

    def set_sidebar_collapsed(self, collapsed: bool):
        """Cache le texte (mode icône uniquement) quand la sidebar est réduite."""
        # En mode réduit : cacher ce widget entièrement
        if collapsed:
            self.pack_forget()
        else:
            self.pack(fill="x", pady=1)
            if self._expanded and self._sub_frame:
                self._sub_frame.pack(fill="x", after=self._main_btn, pady=(0, 2))

    def is_expanded(self):
        return self._expanded


# ─────────────────────────────────────────────────────────────────────────────
# COMPOSANT : SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

_SIDEBAR_W_OPEN   = 228
_SIDEBAR_W_CLOSED = 46

class Sidebar(ctk.CTkFrame):
    """
    Barre latérale responsive :
    - Ouverte  : logo + menu complet + déconnexion
    - Fermée   : seul le bouton hamburger est visible (largeur 46px)
    Transition instantanée, pas d'animation (léger).
    """

    def __init__(self, parent, app: "App", session_data: dict):
        super().__init__(
            parent,
            fg_color=Colors.PRIMARY,
            corner_radius=0,
            width=_SIDEBAR_W_OPEN,
        )
        self.grid_propagate(False)

        self._app           = app
        self._session       = session_data
        self._authorized    = {m[0]: m[1] for m in session_data.get("menus", [])}
        self._is_open       = True
        self._accordions: list[MenuAccordion] = []

        self.grid_rowconfigure(2, weight=1)   # scroll area
        self.grid_columnconfigure(0, weight=1)

        self._build_toggle_row()
        self._build_logo()
        self._build_scroll_area()
        self._build_menu()
        self._build_logout()

    # ── Construction ─────────────────────────────────────────────────────────

    def _build_toggle_row(self):
        row = ctk.CTkFrame(self, fg_color="transparent", height=46)
        row.grid(row=0, column=0, sticky="ew")
        row.grid_columnconfigure(0, weight=1)
        row.grid_propagate(False)

        self._btn_hamburger = ctk.CTkButton(
            row,
            text="☰",
            width=36, height=36,
            fg_color="#034787",
            hover_color="#0565c9",
            text_color="#FFFFFF",
            font=_F(17, "bold"),
            corner_radius=8,
            command=self.toggle,
        )
        self._btn_hamburger.grid(row=0, column=0, padx=5, pady=5, sticky="w")

    def _build_logo(self):
        self._logo_frame = ctk.CTkFrame(self, fg_color="transparent", height=60)
        self._logo_frame.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 4))
        self._logo_frame.grid_propagate(False)

        logo_path = resource_path(os.path.join("image", "logo 3.png"))
        if os.path.exists(logo_path):
            img = ctk.CTkImage(
                light_image=Image.open(logo_path),
                dark_image=Image.open(logo_path),
                size=(160, 52),
            )
            self._logo_lbl = ctk.CTkLabel(self._logo_frame, image=img, text="")
            self._logo_lbl.image = img
        else:
            self._logo_lbl = ctk.CTkLabel(
                self._logo_frame,
                text="iJeery",
                font=_F(20, "bold"),
                text_color="#FFFFFF",
            )
        self._logo_lbl.pack(expand=True)

    def _build_scroll_area(self):
        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=Colors.MIDNIGHT_LIGHT,
            scrollbar_button_hover_color=Colors.PRIMARY,
        )
        self._scroll.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)

    def _build_menu(self):
        """Construit les accordéons de menu selon les autorisations."""
        for cfg in MENU_STRUCTURE:
            # Vérifier autorisation
            if not self._is_authorized(cfg):
                continue

            acc = MenuAccordion(self._scroll, cfg, self._app, self)
            acc.pack(fill="x", pady=1)
            self._accordions.append(acc)

    def _is_authorized(self, cfg: dict) -> bool:
        """Retourne True si au moins un élément du groupe est autorisé."""
        # Pages directes
        if cfg.get("auth"):
            return cfg["auth"] in self._authorized
        # Groupes avec sous-menus
        for sub in cfg.get("subs", []):
            if sub[1] in self._authorized:
                return True
        return False

    def _build_logout(self):
        self._btn_logout = ctk.CTkButton(
            self,
            text="🚪  Déconnexion",
            fg_color="#C0392B",
            hover_color="#922B21",
            text_color="#FFFFFF",
            height=40,
            font=_F(12, "bold"),
            corner_radius=8,
            command=self._app.logout,
        )
        self._btn_logout.grid(row=3, column=0, sticky="ew", padx=8, pady=8)

    # ── Toggle ────────────────────────────────────────────────────────────────

    def toggle(self):
        if self._is_open:
            self._close()
        else:
            self._open()

    def _close(self):
        self._is_open = False
        self.configure(width=_SIDEBAR_W_CLOSED)

        # Cacher logo, scroll, logout
        self._logo_frame.grid_remove()
        self._scroll.grid_remove()
        self._btn_logout.grid_remove()

        # Changer icône hamburger
        self._btn_hamburger.configure(text="☰")

    def _open(self):
        self._is_open = True
        self.configure(width=_SIDEBAR_W_OPEN)

        self._logo_frame.grid()
        self._scroll.grid()
        self._btn_logout.grid()

        self._btn_hamburger.configure(text="✕")

    def collapse_all_except(self, keep: MenuAccordion):
        """Ferme tous les accordéons sauf celui passé en paramètre."""
        for acc in self._accordions:
            if acc is not keep and acc.is_expanded():
                acc._collapse()

    @property
    def authorized(self):
        return self._authorized


# ─────────────────────────────────────────────────────────────────────────────
# FENÊTRE DE VENTE EN ONGLETS — STYLE CHROME
# Remplace le VenteTabManager existant dans app_main.py
#
# CHANGEMENTS vs version précédente :
#   • Suppression du CTkTabview (badge "Vente(1)" laid au centre)
#   • Suppression des boutons flottants ✕ / + disgracieux
#   • Barre d'onglets ttk.Notebook stylisée : fond MIDNIGHT, onglets arrondis
#     en haut, onglet actif blanc, inactifs gris sombre — exactement comme Chrome
#   • Bouton "＋" intégré dans la barre (discret, à droite des onglets)
#   • Fermeture d'onglet par bouton "×" DANS chaque onglet (label cliquable)
#   • Fenêtre se ferme automatiquement quand le dernier onglet est fermé
# ─────────────────────────────────────────────────────────────────────────────

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional
import customtkinter as ctk


# ─── Couleurs iJeery (synchronisées avec app_theme.Colors) ───────────────────
_MIDNIGHT       = "#2C3E50"   # fond barre onglets
_MIDNIGHT_LIGHT = "#34495E"   # onglet inactif hover
_MIDNIGHT_DARK  = "#1A252F"   # onglet inactif normal
_BG_PAGE        = "#ECF0F1"   # fond onglet actif (même que la page)
_TEXT_ON_DARK   = "#FFFFFF"   # texte onglet inactif
_TEXT_PRIMARY   = "#2C3E50"   # texte onglet actif
_SUCCESS_DARK   = "#27AE60"   # bouton +
_DANGER         = "#E74C3C"   # bouton × de fermeture
_BORDER         = "#D5D8DC"


class VenteTabManager(ctk.CTkToplevel):
    """
    Fenêtre multi-onglets pour PageVenteParMsin.

    Architecture :
    ┌─────────────────────────────────────────────────────────┐
    │  [🧾 Vente 1  ×] [🧾 Vente 2  ×] [＋]   ← barre Midnight  │
    ├─────────────────────────────────────────────────────────┤
    │                                                         │
    │              Contenu PageVenteParMsin                   │
    │                                                         │
    └─────────────────────────────────────────────────────────┘

    Chaque onglet est un frame CTk affiché/caché via grid/grid_remove.
    La "barre" est une Frame Midnight avec des boutons CTk simulant des onglets.
    Pas de CTkTabview → pas de badge central, pas de boutons flottants natifs.
    """

    MAX_TABS = 10

    def __init__(self, master, id_user_connecte: Optional[int] = None):
        super().__init__(master)
        self.title("Gestion des Ventes")
        self.geometry("1350x850")
        self.minsize(900, 600)
        self.configure(fg_color=_BG_PAGE)

        self._id_user    = id_user_connecte
        self._tab_count  = 0          # compteur cumulatif (pour le numéro)
        self._tabs: list[dict] = []   # [{id, btn, frame, label_btn}]
        self._active_id: Optional[int] = None

        # ── Grille principale : barre (fixe) + contenu (expansible) ──────────
        self.grid_rowconfigure(0, weight=0)   # barre onglets
        self.grid_rowconfigure(1, weight=1)   # contenu
        self.grid_columnconfigure(0, weight=1)

        # ── Barre d'onglets (fond Midnight) ───────────────────────────────────
        self._tab_bar = tk.Frame(self, bg=_MIDNIGHT, height=38)
        self._tab_bar.grid(row=0, column=0, sticky="ew")
        self._tab_bar.grid_propagate(False)   # hauteur fixe

        # Conteneur scrollable pour les boutons d'onglets (au cas où beaucoup d'onglets)
        self._tabs_inner = tk.Frame(self._tab_bar, bg=_MIDNIGHT)
        self._tabs_inner.pack(side="left", fill="y")

        # Bouton "＋" discret à droite dans la barre
        self._btn_add = tk.Button(
            self._tab_bar,
            text=" ＋ ",
            bg=_MIDNIGHT,
            fg=_TEXT_ON_DARK,
            activebackground=_MIDNIGHT_LIGHT,
            activeforeground=_TEXT_ON_DARK,
            relief="flat",
            bd=0,
            font=("Segoe UI", 13, "bold"),
            cursor="hand2",
            command=self.add_tab,
        )
        self._btn_add.pack(side="left", padx=(2, 0), pady=6)

        # Séparateur visuel fin en bas de la barre
        tk.Frame(self, bg=_BORDER, height=1).grid(row=0, column=0, sticky="sew")

        # ── Zone de contenu (frames des onglets empilés) ──────────────────────
        self._content_area = ctk.CTkFrame(self, fg_color=_BG_PAGE, corner_radius=0)
        self._content_area.grid(row=1, column=0, sticky="nsew")
        self._content_area.grid_rowconfigure(0, weight=1)
        self._content_area.grid_columnconfigure(0, weight=1)

        # Ouverture du premier onglet au démarrage
        self.add_tab()

    # ──────────────────────────────────────────────────────────────────────────
    # GESTION DES ONGLETS
    # ──────────────────────────────────────────────────────────────────────────

    def add_tab(self):
        """Crée un nouvel onglet avec sa PageVenteParMsin et l'active."""
        if len(self._tabs) >= self.MAX_TABS:
            messagebox.showwarning("Limite atteinte",
                                   f"Maximum {self.MAX_TABS} onglets simultanés.")
            return

        self._tab_count += 1
        tab_id    = self._tab_count
        tab_label = f"  🧾 Vente {tab_id}  "

        # ── Bouton-onglet dans la barre ───────────────────────────────────────
        tab_btn_frame = tk.Frame(self._tabs_inner, bg=_MIDNIGHT_DARK)
        tab_btn_frame.pack(side="left", padx=(4, 0), pady=4)

        lbl_btn = tk.Label(
            tab_btn_frame,
            text=tab_label,
            bg=_MIDNIGHT_DARK,
            fg=_TEXT_ON_DARK,
            font=("Segoe UI", 10),
            cursor="hand2",
            padx=4, pady=3,
        )
        lbl_btn.pack(side="left")

        # Bouton × de fermeture intégré dans l'onglet
        close_btn = tk.Label(
            tab_btn_frame,
            text=" ×",
            bg=_MIDNIGHT_DARK,
            fg="#95A5A6",          # gris discret par défaut
            font=("Segoe UI", 11, "bold"),
            cursor="hand2",
            padx=2,
        )
        close_btn.pack(side="left")

        # ── Frame de contenu (PageVenteParMsin) ───────────────────────────────
        content_frame = ctk.CTkFrame(
            self._content_area, fg_color=_BG_PAGE, corner_radius=0
        )
        content_frame.grid(row=0, column=0, sticky="nsew")
        content_frame.grid_remove()   # caché par défaut jusqu'à activation

        # Chargement différé de PageVenteParMsin (évite import circulaire)
        try:
            from pages.page_venteParMsin import PageVenteParMsin
            page = PageVenteParMsin(content_frame, id_user_connecte=self._id_user)
            page.pack(fill="both", expand=True)
        except Exception as e:
            # Afficher l'erreur dans le cadre sans crasher toute l'appli
            ctk.CTkLabel(
                content_frame,
                text=f"❌ Erreur chargement page vente :\n{e}",
                text_color=_DANGER,
                font=("Segoe UI", 12),
            ).pack(expand=True)

        # ── Enregistrement de l'onglet ────────────────────────────────────────
        tab_info = {
            "id":            tab_id,
            "btn_frame":     tab_btn_frame,
            "lbl_btn":       lbl_btn,
            "close_btn":     close_btn,
            "content_frame": content_frame,
        }
        self._tabs.append(tab_info)

        # ── Bindings ──────────────────────────────────────────────────────────
        # Clic sur le label → activer l'onglet
        lbl_btn.bind("<Button-1>",   lambda _e, tid=tab_id: self._activate_tab(tid))
        # Clic sur × → fermer l'onglet
        close_btn.bind("<Button-1>", lambda _e, tid=tab_id: self.close_tab(tid))
        # Hover sur × : rouge vif pour signaler l'action
        close_btn.bind("<Enter>",    lambda _e, b=close_btn: b.config(fg=_DANGER))
        close_btn.bind("<Leave>",    lambda _e, b=close_btn: b.config(fg="#95A5A6"))
        # Hover sur l'onglet inactif : éclaircissement
        lbl_btn.bind("<Enter>",
            lambda _e, t=tab_info: self._on_tab_hover(t, True))
        lbl_btn.bind("<Leave>",
            lambda _e, t=tab_info: self._on_tab_hover(t, False))

        # Désactiver le bouton + si limite atteinte
        if len(self._tabs) >= self.MAX_TABS:
            self._btn_add.config(state="disabled", fg="#5D6D7E")

        # Activer le nouvel onglet
        self._activate_tab(tab_id)

    def close_tab(self, tab_id: int):
        """Ferme l'onglet correspondant à tab_id."""
        if len(self._tabs) <= 1:
            # Dernier onglet → ferme toute la fenêtre
            self.destroy()
            return

        tab = self._get_tab(tab_id)
        if not tab:
            return

        # Destruction des widgets de la barre et du contenu
        tab["btn_frame"].destroy()
        tab["content_frame"].destroy()
        self._tabs = [t for t in self._tabs if t["id"] != tab_id]

        # Réactiver le bouton + si on était à la limite
        self._btn_add.config(state="normal", fg=_TEXT_ON_DARK)

        # Si l'onglet fermé était l'actif, basculer sur le dernier restant
        if self._active_id == tab_id and self._tabs:
            self._activate_tab(self._tabs[-1]["id"])

    def _activate_tab(self, tab_id: int):
        """Active visuellement l'onglet tab_id et affiche son contenu."""
        self._active_id = tab_id
        for tab in self._tabs:
            is_active = (tab["id"] == tab_id)
            self._apply_tab_style(tab, active=is_active)
            if is_active:
                tab["content_frame"].grid()    # afficher
            else:
                tab["content_frame"].grid_remove()  # cacher

    def _apply_tab_style(self, tab: dict, active: bool):
        """Applique le style visuel Chrome (actif = blanc, inactif = sombre)."""
        if active:
            bg  = _BG_PAGE
            fg  = _TEXT_PRIMARY
            font = ("Segoe UI", 10, "bold")
            close_fg = "#5D6D7E"
        else:
            bg  = _MIDNIGHT_DARK
            fg  = _TEXT_ON_DARK
            font = ("Segoe UI", 10)
            close_fg = "#5D6D7E"

        tab["btn_frame"].config(bg=bg)
        tab["lbl_btn"].config(bg=bg, fg=fg, font=font)
        tab["close_btn"].config(bg=bg, fg=close_fg)

    def _on_tab_hover(self, tab: dict, entering: bool):
        """Effet hover sur les onglets inactifs uniquement."""
        if tab["id"] == self._active_id:
            return   # ne pas altérer le style de l'onglet actif
        bg = _MIDNIGHT_LIGHT if entering else _MIDNIGHT_DARK
        tab["btn_frame"].config(bg=bg)
        tab["lbl_btn"].config(bg=bg)
        tab["close_btn"].config(bg=bg)

    def _get_tab(self, tab_id: int) -> Optional[dict]:
        """Retourne le dict d'onglet pour un tab_id donné."""
        return next((t for t in self._tabs if t["id"] == tab_id), None)

    def close_current_tab(self):
        """Ferme l'onglet actuellement actif (rétrocompatibilité app_main)."""
        if self._active_id is not None:
            self.close_tab(self._active_id)
# ─────────────────────────────────────────────────────────────────────────────
# FENÊTRE PRINCIPALE
# ─────────────────────────────────────────────────────────────────────────────

class App(ctk.CTk):

    def __init__(self, session_data: dict):
        super().__init__()

        load_roboto()
        apply_global_font(self)

        if _THEME:
            Theme.apply(self)
        else:
            self.configure(fg_color=Colors.BG_PAGE)

        self.title("iJeery")
        self.geometry("1280x780")
        self.minsize(960, 600)

        self.session_data     = session_data
        self.id_user_connecte = session_data.get("user_id")
        self._vente_tab_mgr   = None

        # Connexion DB
        self.db_manager = DatabaseManager()
        self.db_conn    = self.db_manager.get_connection()

        if self.db_conn is None:
            messagebox.showerror("Connexion", "Impossible de se connecter à la base de données.")
            self.destroy()
            return

        self.nom_societe = self._fetch_societe_name()

        # ── Layout racine ────────────────────────────────────────────────────
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ── Sidebar ──────────────────────────────────────────────────────────
        self._sidebar = Sidebar(self, self, session_data)
        self._sidebar.grid(row=0, column=0, sticky="ns")

        # ── Zone de contenu ───────────────────────────────────────────────────
        self._content = ctk.CTkFrame(
            self,
            fg_color=Colors.BG_PAGE,
            corner_radius=0,
        )
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

        # ── Événements ────────────────────────────────────────────────────────
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._start_clock()

        # ── Page initiale ─────────────────────────────────────────────────────
        authorized = self._sidebar.authorized
        if "CHAT INTERNE" in authorized:
            self.navigate("pages.page_chat", "PageChat", "chat", "CHAT INTERNE")
        elif "TABLEAU DE BORD" in authorized:
            self.navigate("pages.page_home", "page_home", None, "TABLEAU DE BORD")
        elif authorized:
            first_auth = next(iter(authorized))
            self.navigate(None, None, None, first_auth)

    # ── Horloge titre ─────────────────────────────────────────────────────────

    def _start_clock(self):
        self._update_title()

    def _update_title(self):
        now = datetime.now().strftime("%d/%m/%Y  %H:%M:%S")
        self.title(
            f"  {now}  —  {self.nom_societe}  —  iJeery v5.0  "
            f"—  Copyright 2025 Iski Solution  —  +261 34 46 687 61"
        )
        self.after(1000, self._update_title)

    def _fetch_societe_name(self) -> str:
        try:
            cur = self.db_conn.cursor()
            cur.execute("SELECT nomsociete FROM tb_infosociete LIMIT 1")
            row = cur.fetchone()
            cur.close()
            return row[0] if row else "iJeery"
        except Exception:
            return "iJeery"

    # ── Navigation ────────────────────────────────────────────────────────────

    def _safe_clear_content(self):
        """
        Détruit proprement tous les widgets enfants du content_frame.
        Utilise update_idletasks() pour laisser Tkinter traiter les événements
        pendants AVANT la destruction, ce qui évite le TclError classique :
        "invalid command name .!widget..." quand un after() se déclenche
        après que le widget a été détruit.
        """
        children = self._content.winfo_children()
        if not children:
            return

        # 1. Cacher immédiatement tous les enfants (stoppe les redessins)
        for w in children:
            try:
                w.grid_remove()
                w.pack_forget()
            except Exception:
                pass

        # 2. Laisser Tkinter vider sa file d'événements (after() en attente)
        self._content.update_idletasks()

        # 3. Destruction propre
        for w in children:
            try:
                w.destroy()
            except Exception:
                pass

    def navigate(self, module_path: Optional[str], class_name: Optional[str],
                 kwargs_key: Optional[str], auth_key: str):
        """
        Charge et affiche une page dans la zone de contenu.
        kwargs_key contrôle les arguments spéciaux à passer.
        """
        # ── Vider le contenu en annulant d'abord les callbacks "after" pendants ──
        # Cela évite le TclError quand une page a un after() en cours
        # (ex: page_stock qui rappelle recharger_treeview après destruction)
        self._safe_clear_content()

        # ── Cas spéciaux ──────────────────────────────────────────────────────
        if kwargs_key == "vente_tab":
            self._open_vente_tab()
            return

        if kwargs_key == "toplevel" and module_path and class_name:
            cls = _lazy_load(module_path, class_name)
            if cls:
                win = cls(master=self, app_root=self)
                win.grab_set(); win.focus_force(); win.transient(self)
                self.wait_window(win)
            return

        if not module_path or not class_name:
            self._show_not_authorized("Page non configurée.")
            return

        # ── Chargement de la classe ───────────────────────────────────────────
        cls = _lazy_load(module_path, class_name)
        if cls is None:
            self._show_not_authorized(f"Module introuvable : {module_path}.{class_name}")
            return

        # ── Instanciation avec les bons arguments ────────────────────────────
        try:
            instance = self._instantiate(cls, kwargs_key)
        except Exception as e:
            import traceback; traceback.print_exc()
            self._show_not_authorized(f"Erreur d'affichage :\n{e}")
            return

        if instance is None:
            self._show_not_authorized("Impossible de créer la page.")
            return

        if isinstance(instance, ctk.CTkToplevel):
            instance.lift(); instance.focus_force(); instance.transient(self)
            self.wait_window(instance)
        else:
            instance.grid(row=0, column=0, sticky="nsew")

    def _instantiate(self, cls, kwargs_key: Optional[str]):
        """Instancie une page avec la bonne signature."""
        master = self._content

        if kwargs_key == "vente":
            return cls(master=master, id_user_connecte=self.id_user_connecte)

        if kwargs_key == "iduser":
            # Certaines pages utilisent "parent" (positionnel) d'autres "master=" (kwarg).
            # On essaie les deux pour couvrir PageInfoMouvementStock et PageAVQ/FenetreAvanceSpec.
            for call in [
                lambda: cls(master, iduser=self.id_user_connecte),   # parent positionnel
                lambda: cls(master=master, iduser=self.id_user_connecte),
            ]:
                try:
                    return call()
                except TypeError:
                    continue
            return None

        if kwargs_key == "app_root":
            return cls(master=master, app_root=self)

        if kwargs_key == "chat":
            return cls(
                master=master,
                session_data={
                    "iduser":   self.id_user_connecte,
                    "username": self.session_data.get("username", "Utilisateur"),
                },
            )

        # Essais en cascade : (master, db_conn, session_data) → (master, db_conn) → (master,)
        for args, kw in [
            ((master,), {"db_conn": self.db_conn, "session_data": self.session_data}),
            ((master,), {"db_conn": self.db_conn}),
            ((master,), {}),
        ]:
            try:
                return cls(*args, **kw)
            except TypeError:
                continue

        return None

    def _open_vente_tab(self):
        if self._vente_tab_mgr is None or not self._vente_tab_mgr.winfo_exists():
            self._vente_tab_mgr = VenteTabManager(self, self.id_user_connecte)
        else:
            self._vente_tab_mgr.add_tab()
        self._vente_tab_mgr.lift()
        self._vente_tab_mgr.focus_force()
        self._vente_tab_mgr.attributes('-topmost', True)

    def _show_not_authorized(self, msg: str = "Accès non autorisé."):
        for w in self._content.winfo_children():
            w.destroy()
        lbl = ctk.CTkLabel(
            self._content,
            text=msg,
            font=_F(14),
            text_color=Colors.TEXT_MUTED,
            wraplength=400,
            justify="center",
        )
        lbl.grid(row=0, column=0, sticky="nsew")

    # ── Déconnexion ───────────────────────────────────────────────────────────

    def logout(self):
        if not messagebox.askyesno("Déconnexion", "Voulez-vous vraiment vous déconnecter ?"):
            return
        try:
            if os.path.exists("session.json"):
                os.remove("session.json")
            if self.db_conn:
                try: self.db_conn.close()
                except Exception: pass
            self.withdraw()

            if getattr(sys, "frozen", False):
                subprocess.Popen(
                    [sys.executable],
                    cwd=os.path.dirname(sys.executable),
                    creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
                )
            else:
                script = os.path.join(_BASE, "app_main.py")
                if os.path.exists(script):
                    subprocess.Popen([sys.executable, script])

            time.sleep(0.4)
            try: self.quit(); self.destroy()
            except Exception: pass
            sys.exit(0)

        except Exception as e:
            messagebox.showerror("Erreur", f"Déconnexion échouée : {e}")

    def _on_close(self):
        if self.db_conn:
            try: self.db_conn.close()
            except Exception: pass
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────────────────────────────────────

def _dummy_session() -> dict:
    """Session factice pour les tests directs."""
    menus = [
        "TABLEAU DE BORD", "CHAT INTERNE",
        "Article Liste", "Client", "Fournisseur", "Magasin",
        "Ventes", "Ventes par Dépôt", "Facturation", "Liste Facture",
        "Stock Article", "Stock Alerte", "Péremption d'article", "Stock Livraison",
        "Mouvement d'article", "Mouvement Stock", "Liste mouvements",
        "Suivi Commande", "Prix d'article", "Prix de revient", "Livraison Client",
        "Liste Personnel", "Absence", "Présence", "Avance 15e", "Avance Spéciale",
        "Fonction", "Nouveau SB", "Etat de Salaire", "Salaire Horaire",
        "Taux Horaire", "Paiement Salaire",
        "Caisse", "Facture Liste", "Fournisseur Dettes", "Banque", "Ajout Banque",
        "Transfert Banque", "Transfert Caisse", "Decaissement", "DecaissementBq",
        "Encaissement", "EncaissementBq",
        "Autorisation", "Evenements", "Sauvegarde", "Utilisateurs",
        "Menu", "Base Liste", "Autorisation Admin", "Init DB",
    ]
    return {
        "username": "admin",
        "user_id":  1,
        "menus":    [(m, True) for m in menus],
    }


if __name__ == "__main__":
    session_data = None
    session_file = os.path.join(_BASE, "session.json")

    if os.path.exists(session_file):
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                session_data = json.load(f)
            print("[App] Session chargée depuis session.json")
        except Exception as e:
            print(f"[App] session.json invalide : {e}")

    if session_data:
        app = App(session_data)
        app.mainloop()
    else:
        print("[App] Pas de session — lancement de la fenêtre de login.")
        try:
            from page_login import LoginWindow
            LoginWindow().start()
        except ImportError:
            print("[App] page_login introuvable — utilisation de la session factice.")
            app = App(_dummy_session())
            app.mainloop()
