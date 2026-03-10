# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   iJeery — pages/page_sortie.py                             ║
║                   Gestion des Sorties de stock & Consommation Interne       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  REFONTE UI — Mars 2026                                                      ║
║  Structure identique à page_venteParMsin / page_avoir / page_transfert :    ║
║    Row 0 — Bandeau type de sortie (BS / CI)                                 ║
║    Row 1 — Bandeau en-tête (Réf | Date | Magasin | Charger)                 ║
║    Row 2 — Bandeau Motif (pleine largeur)                                   ║
║    Row 3 — Bandeau saisie article (Article | 🔍 | Qté | Unité | PU | ➕)   ║
║    Row 4 — Tableau Treeview (weight=1 → expansible)                         ║
║    Row 5 — Barre d'actions (Nouveau | 🖨 Imprimer | 🗑 Suppr | 💾)          ║
║                                                                              ║
║  Logique métier : 100% INCHANGÉE                                             ║
║  Seul setup_ui() → _setup_ui() est refait avec le thème iJeery              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import customtkinter as ctk
from tkinter import messagebox, ttk, simpledialog
import psycopg2
import json
from datetime import datetime
import calendar
from typing import Optional, Dict, Any, List
import traceback
import os
import sys
import subprocess

from resource_utils import get_config_path, get_session_path, safe_file_read
from app_theme import Colors, Fonts

# ReportLab
from reportlab.lib.pagesizes import A5, landscape
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


class PageSortie(ctk.CTkFrame):
    """
    Page de gestion des sorties de stock et consommations internes.

    Architecture UI (cohérente avec page_venteParMsin) :
    ┌────────────────────────────────────────────────────────────┐
    │ Row 0 — Type : Sortie BS  |  Consommation Interne CI       │ card BG_CARD
    │ Row 1 — Réf | Date | Magasin | 📂 Charger                 │ card BG_CARD
    │ Row 2 — Motif (pleine largeur)                             │ card BG_CARD
    │ Row 3 — Article | 🔍 | Qté | Unité | PU (CI) | ➕ | ✖     │ card BG_CARD
    │ Row 4 — Tableau Treeview (expansible)                      │ frame MIDNIGHT hdr
    │ Row 5 — Nouveau | 🖨 Imprimer | (espace) | 🗑 | 💾         │ frame BG_PAGE
    └────────────────────────────────────────────────────────────┘
    """

    def __init__(self, master, id_user_connecte: int, **kwargs):
        super().__init__(master, fg_color=Colors.BG_PAGE, **kwargs)

        self.id_user_connecte = id_user_connecte
        self.conn: Optional[psycopg2.extensions.connection] = None
        self.article_selectionne      = None
        self.detail_sortie: list      = []
        self.index_ligne_selectionnee = None
        self.magasins_map: dict       = {}
        self.magasins_ids: list       = []
        self.infos_societe: Dict[str, Any] = {}
        self.derniere_idsortie_enregistree: Optional[int] = None

        # Type de sortie : "BS" ou "CI"
        self.type_sortie          = "BS"
        self.show_price_columns   = False

        # Mode modification / consultation
        self.mode_modification = False
        self.idsortie_charge   = None

        # Référence du Treeview (recréé dynamiquement selon le type)
        self.tree_details        = None
        self.scrollbar_details   = None

        # ── Layout principal : 6 rows ─────────────────────────────────────────
        self.grid_columnconfigure(0, weight=1)
        for row, w in enumerate([0, 0, 0, 0, 1, 0]):
            self.grid_rowconfigure(row, weight=w)

        # ── Construction de l'interface ───────────────────────────────────────
        self._setup_ui()

        # ── Chargements initiaux ──────────────────────────────────────────────
        self.generer_reference()
        self.charger_magasins()
        self.charger_infos_societe()
        self.conn = self.connect_db()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1 — CONNEXION BASE DE DONNÉES
    # ══════════════════════════════════════════════════════════════════════════

    def connect_db(self):
        """Ouvre une connexion fraîche à PostgreSQL depuis config.json."""
        try:
            with open(get_config_path('config.json')) as f:
                config    = json.load(f)
                db_config = config['database']
            return psycopg2.connect(
                host=db_config['host'], user=db_config['user'],
                password=db_config['password'], database=db_config['database'],
                port=db_config['port'],
            )
        except FileNotFoundError:
            messagebox.showerror("Erreur", "config.json non trouvé.")
            return None
        except psycopg2.Error as e:
            messagebox.showerror("Erreur BD", str(e))
            return None

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — CONSTRUCTION DE L'INTERFACE
    # ══════════════════════════════════════════════════════════════════════════

    def _setup_ui(self):
        """Point d'entrée UI — délègue à 6 sous-méthodes."""
        self._build_type_band()        # Row 0 — Sélecteur BS / CI
        self._build_header_band()      # Row 1 — Réf / Date / Magasin
        self._build_motif_band()       # Row 2 — Motif
        self._build_article_band()     # Row 3 — Saisie article
        self._build_tree_zone()        # Row 4 — Treeview
        self._build_actions_band()     # Row 5 — Boutons

    # ── Row 0 — Sélecteur de type ─────────────────────────────────────────────

    def _build_type_band(self):
        """
        Card blanche (Row 0) : choix du type de sortie BS / CI.
        Deux boutons radio visuels pour un retour immédiat.
        """
        card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        card.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 2))

        ctk.CTkLabel(
            card, text="Type de sortie :",
            font=Fonts.bold(12), text_color=Colors.TEXT_SECONDARY,
        ).pack(side="left", padx=(12, 8), pady=8)

        self.combo_type_sortie = ctk.CTkOptionMenu(
            card,
            values=["Sortie d'articles (BS)", "Consommation interne (CI)"],
            command=self._on_type_sortie_changed,
            width=240, height=32,
            font=Fonts.bold(11),
            fg_color=Colors.MIDNIGHT, button_color=Colors.MIDNIGHT_LIGHT,
            dropdown_fg_color=Colors.BG_CARD,
        )
        self.combo_type_sortie.set("Sortie d'articles (BS)")
        self.combo_type_sortie.pack(side="left", padx=4, pady=8)

        # Label informatif (contexte dynamique)
        self.label_type_info = ctk.CTkLabel(
            card, text="  Bon de Sortie — déduction du stock sans valorisation",
            font=Fonts.label(10), text_color=Colors.TEXT_MUTED,
        )
        self.label_type_info.pack(side="left", padx=8, pady=8)

    # ── Row 1 — Bandeau en-tête ───────────────────────────────────────────────

    def _build_header_band(self):
        """
        Card blanche (Row 1) : Référence (readonly) | Date | Magasin | 📂 Charger.
        """
        card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        card.grid(row=1, column=0, sticky="ew", padx=0, pady=(0, 2))
        for col in range(5):
            card.grid_columnconfigure(col, weight=1)

        lbl_kw   = dict(font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY, anchor="w")
        entry_kw = dict(
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            height=32, corner_radius=6, font=Fonts.input(12),
        )
        entry_kw_no_font = {k: v for k, v in entry_kw.items() if k != 'font'}

        # — Référence —
        ctk.CTkLabel(card, text="Référence", **lbl_kw).grid(
            row=0, column=0, padx=(10, 2), pady=(8, 0), sticky="w")
        self.entry_ref_sortie = ctk.CTkEntry(
            card, **entry_kw_no_font, font=Fonts.bold(12), state="readonly",
        )
        self.entry_ref_sortie.grid(row=1, column=0, padx=(10, 4), pady=(0, 8), sticky="ew")

        # — Date —
        ctk.CTkLabel(card, text="Date Sortie", **lbl_kw).grid(
            row=0, column=1, padx=4, pady=(8, 0), sticky="w")
        self.entry_date_sortie = ctk.CTkEntry(card, **entry_kw)
        self.entry_date_sortie.grid(row=1, column=1, padx=4, pady=(0, 8), sticky="ew")
        self.entry_date_sortie.insert(0, datetime.now().strftime("%d/%m/%Y"))

        # — Magasin —
        ctk.CTkLabel(card, text="Magasin de", **lbl_kw).grid(
            row=0, column=2, padx=4, pady=(8, 0), sticky="w")
        self.combo_magasin = ctk.CTkComboBox(
            card, values=["Chargement…"], height=32,
            font=Fonts.input(12), fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER, button_color=Colors.PRIMARY,
            dropdown_fg_color=Colors.BG_CARD,
        )
        self.combo_magasin.grid(row=1, column=2, padx=4, pady=(0, 8), sticky="ew")

        # — colonne vide (espace) —
        card.grid_columnconfigure(3, weight=2)

        # — Bouton Charger Opération —
        ctk.CTkLabel(card, text=" ", **lbl_kw).grid(
            row=0, column=4, padx=(4, 10), pady=(8, 0))
        self.btn_charger_bs = ctk.CTkButton(
            card, text="📂 Charger Opération", height=32,
            font=Fonts.bold(11),
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            corner_radius=6, command=self.ouvrir_recherche_sortie,
        )
        self.btn_charger_bs.grid(row=1, column=4, padx=(4, 10), pady=(0, 8), sticky="ew")

    # ── Row 2 — Bandeau motif ─────────────────────────────────────────────────

    def _build_motif_band(self):
        """
        Card blanche (Row 2) : champ Motif sur toute la largeur.
        """
        card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        card.grid(row=2, column=0, sticky="ew", padx=0, pady=(0, 2))
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card, text="Motif",
            font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY,
        ).grid(row=0, column=0, padx=(10, 6), pady=8, sticky="w")

        self.entry_motif = ctk.CTkEntry(
            card,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            height=32, corner_radius=6, font=Fonts.input(12),
            placeholder_text="Motif / description de la sortie…",
        )
        self.entry_motif.grid(row=0, column=1, padx=(0, 10), pady=8, sticky="ew")

    # ── Row 3 — Bandeau saisie article ───────────────────────────────────────

    def _build_article_band(self):
        """
        Card blanche (Row 3) : Article | 🔍 | Qté | Unité | PU (CI only) | ➕ | ✖ Annuler.
        """
        card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        card.grid(row=3, column=0, sticky="ew", padx=0, pady=(0, 2))
        for col in range(7):
            card.grid_columnconfigure(col, weight=1)

        lbl_kw   = dict(font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY, anchor="w")
        entry_kw = dict(
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            height=32, corner_radius=6, font=Fonts.input(12),
        )

        # — Article (readonly) —
        ctk.CTkLabel(card, text="Article", **lbl_kw).grid(
            row=0, column=0, padx=(10, 2), pady=(8, 0), sticky="w")
        self.entry_article = ctk.CTkEntry(
            card, **entry_kw, placeholder_text="Sélectionner un article…",
            state="readonly",
        )
        self.entry_article.grid(row=1, column=0, padx=(10, 4), pady=(0, 8), sticky="ew")

        # — Bouton Rechercher —
        ctk.CTkLabel(card, text=" ", **lbl_kw).grid(
            row=0, column=1, padx=4, pady=(8, 0))
        self.btn_recherche_article = ctk.CTkButton(
            card, text="🔎 Rechercher", height=32,
            font=Fonts.bold(11),
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            corner_radius=6, command=self.open_recherche_article,
        )
        self.btn_recherche_article.grid(row=1, column=1, padx=4, pady=(0, 8), sticky="ew")

        # — Quantité —
        ctk.CTkLabel(card, text="Quantité", **lbl_kw).grid(
            row=0, column=2, padx=4, pady=(8, 0), sticky="w")
        self.entry_qtsortie = ctk.CTkEntry(card, **entry_kw, width=100)
        self.entry_qtsortie.grid(row=1, column=2, padx=4, pady=(0, 8), sticky="ew")

        # — Unité (readonly) —
        ctk.CTkLabel(card, text="Unité", **lbl_kw).grid(
            row=0, column=3, padx=4, pady=(8, 0), sticky="w")
        self.entry_unite = ctk.CTkEntry(card, **entry_kw, width=100, state="readonly")
        self.entry_unite.grid(row=1, column=3, padx=4, pady=(0, 8), sticky="ew")

        # — Prix Unitaire (CI seulement, masqué par défaut) —
        self.label_prix_unit = ctk.CTkLabel(card, text="Prix U.", **lbl_kw)
        self.label_prix_unit.grid(row=0, column=4, padx=4, pady=(8, 0), sticky="w")
        self.entry_prix_unit = ctk.CTkEntry(card, **entry_kw, width=100, state="readonly")
        self.entry_prix_unit.grid(row=1, column=4, padx=4, pady=(0, 8), sticky="ew")
        # Masqué par défaut (BS)
        self.label_prix_unit.grid_remove()
        self.entry_prix_unit.grid_remove()

        # — Bouton Ajouter (vert) —
        ctk.CTkLabel(card, text=" ", **lbl_kw).grid(
            row=0, column=5, padx=4, pady=(8, 0))
        self.btn_ajouter = ctk.CTkButton(
            card, text="+ Ajouter", height=32,
            font=Fonts.bold(12),
            fg_color=Colors.SUCCESS_DARK, hover_color=Colors.INFO_DARK,
            corner_radius=6, command=self.valider_detail,
        )
        self.btn_ajouter.grid(row=1, column=5, padx=4, pady=(0, 8), sticky="ew")

        # — Bouton Annuler Modif (rouge, masqué par défaut) —
        self.btn_annuler_mod = ctk.CTkButton(
            card, text="✖ Annuler Modif", height=32,
            font=Fonts.bold(11),
            fg_color=Colors.DANGER, hover_color=Colors.DANGER_DARK,
            corner_radius=6, command=self.reset_detail_form, state="disabled",
        )
        self.btn_annuler_mod.grid(row=1, column=6, padx=(4, 10), pady=(0, 8), sticky="ew")

    # ── Row 4 — Tableau Treeview ──────────────────────────────────────────────

    def _build_tree_zone(self):
        """
        Zone expansible (Row 4) : conteneur du Treeview.
        Le Treeview lui-même est (re)créé par _create_treeview() car ses colonnes
        varient selon le type BS / CI.
        """
        self.tree_container = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        self.tree_container.grid(row=4, column=0, sticky="nsew", padx=0, pady=(0, 2))
        self.tree_container.grid_columnconfigure(0, weight=1)
        self.tree_container.grid_rowconfigure(1, weight=1)

        # Barre d'outils du tableau (toggle prix pour CI)
        toolbar = ctk.CTkFrame(self.tree_container, fg_color="transparent")
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=6, pady=(4, 0))
        toolbar.grid_columnconfigure(0, weight=1)

        self.btn_toggle_prix = ctk.CTkButton(
            toolbar, text="👁 Afficher Prix / Montant",
            height=28, width=200,
            font=Fonts.bold(10),
            fg_color=Colors.WARNING, hover_color="#D68910",
            corner_radius=6, command=self._toggle_price_columns,
        )
        self.btn_toggle_prix.grid(row=0, column=1, sticky="e")
        self.btn_toggle_prix.grid_remove()  # masqué tant que type=BS

        # Création initiale du Treeview
        self._create_treeview()

    def _create_treeview(self):
        """
        Crée ou recrée le Treeview selon le type de sortie.
        Appelé à l'initialisation et à chaque changement BS ↔ CI.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        # Détruire l'ancien Treeview s'il existe
        if self.tree_details is not None:
            self.tree_details.destroy()
        if self.scrollbar_details is not None:
            self.scrollbar_details.destroy()

        # Colonnes selon le type
        if self.type_sortie == "CI":
            colonnes = (
                "ID_Article", "ID_Unite", "ID_Magasin",
                "Code Article", "Désignation", "Magasin",
                "Unité", "Quantité", "Montant", "Motif",
            )
        else:
            colonnes = (
                "ID_Article", "ID_Unite", "ID_Magasin",
                "Code Article", "Désignation", "Magasin",
                "Unité", "Quantité", "Motif",
            )

        # Style TTK (défini une seule fois)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Sortie.Treeview",
            rowheight=22, font=('Segoe UI', 9),
            background=Colors.BG_CARD, foreground=Colors.TEXT_PRIMARY,
            fieldbackground=Colors.BG_CARD, borderwidth=0,
        )
        style.configure(
            "Sortie.Treeview.Heading",
            background=Colors.BG_HEADER, foreground=Colors.TEXT_ON_DARK,
            font=('Segoe UI', 9, 'bold'), relief="flat",
        )
        style.map(
            "Sortie.Treeview",
            background=[("selected", Colors.PRIMARY)],
            foreground=[("selected", Colors.TEXT_ON_DARK)],
        )

        self.tree_details = ttk.Treeview(
            self.tree_container, columns=colonnes, show='headings',
            style="Sortie.Treeview",
        )
        self.tree_details.tag_configure("even", background=Colors.BG_CARD)
        self.tree_details.tag_configure("odd",  background=Colors.BG_ROW_ALT)

        for col in colonnes:
            self.tree_details.heading(col, text=col.replace('_', ' '))
            if "ID" in col:
                self.tree_details.column(col, width=0, stretch=False)
            elif col == "Quantité":
                self.tree_details.column(col, width=130, anchor='e')
            elif col == "Montant":
                self.tree_details.column(col, width=130, anchor='e')
            elif col == "Désignation":
                self.tree_details.column(col, width=300, anchor='w')
            elif col == "Motif":
                self.tree_details.column(col, width=220, anchor='w')
            else:
                self.tree_details.column(col, width=120, anchor='w')

        self.scrollbar_details = ctk.CTkScrollbar(
            self.tree_container, command=self.tree_details.yview,
        )
        self.tree_details.configure(yscrollcommand=self.scrollbar_details.set)

        self.tree_details.grid(row=1, column=0, sticky="nsew", padx=(6, 0), pady=(0, 6))
        self.scrollbar_details.grid(row=1, column=1, sticky="ns", padx=(0, 6), pady=(0, 6))

        self.tree_details.bind('<Double-1>', self.modifier_detail)

        self.charger_details_treeview()

        # Bouton toggle visible uniquement en mode CI
        if self.type_sortie == "CI":
            self.btn_toggle_prix.grid()
        else:
            self.btn_toggle_prix.grid_remove()

    # ── Row 5 — Barre d'actions ───────────────────────────────────────────────

    def _build_actions_band(self):
        """
        Frame BG_PAGE (Row 5) : Nouveau | 🖨 Imprimer | (espace) | 🗑 Supprimer | 💾 Enregistrer.
        """
        bar = ctk.CTkFrame(self, fg_color=Colors.BG_PAGE, corner_radius=0)
        bar.grid(row=5, column=0, sticky="ew", padx=0, pady=(2, 0))
        bar.grid_columnconfigure(3, weight=1)  # espace élastique

        # — Nouveau BS —
        btn_nouveau = ctk.CTkButton(
            bar, text="📄 Nouveau BS", height=34,
            font=Fonts.bold(11),
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            corner_radius=6, command=self.nouveau_bon_sortie,
        )
        btn_nouveau.grid(row=0, column=0, padx=(8, 4), pady=6)

        # — Imprimer (masqué jusqu'à enregistrement) —
        self.btn_imprimer = ctk.CTkButton(
            bar, text="🖨 Imprimer état", height=34,
            font=Fonts.bold(11),
            fg_color=Colors.PREMIUM, hover_color=Colors.PREMIUM_DARK,
            corner_radius=6, command=self.open_impression_dialogue, state="disabled",
        )
        self.btn_imprimer.grid(row=0, column=1, padx=4, pady=6)
        self.btn_imprimer.grid_remove()  # visible après enregistrement

        # — Supprimer Ligne —
        self.btn_supprimer_ligne = ctk.CTkButton(
            bar, text="🗑 Supprimer Ligne", height=34,
            font=Fonts.bold(11),
            fg_color=Colors.DANGER, hover_color=Colors.DANGER_DARK,
            corner_radius=6, command=self.supprimer_detail,
        )
        self.btn_supprimer_ligne.grid(row=0, column=2, padx=4, pady=6)

        # espace élastique — colonne 3

        # — Enregistrer (droite) —
        self.btn_enregistrer = ctk.CTkButton(
            bar, text="💾 Enregistrer la Sortie", height=34,
            font=Fonts.bold(13),
            fg_color=Colors.SUCCESS_DARK, hover_color=Colors.INFO_DARK,
            corner_radius=8, command=self.enregistrer_sortie,
        )
        self.btn_enregistrer.grid(row=0, column=4, padx=(4, 8), pady=6, sticky="e")

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3 — GESTION DU TYPE DE SORTIE (BS / CI)
    # ══════════════════════════════════════════════════════════════════════════

    def _on_type_sortie_changed(self, new_type_str):
        """
        Gère le changement de type BS ↔ CI.
        Régénère la référence, recrée le Treeview, réinitialise le formulaire.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        self.type_sortie = "BS" if "BS" in new_type_str else "CI"

        # Mettre à jour le label d'info
        if self.type_sortie == "CI":
            self.label_type_info.configure(
                text="  Consommation Interne — sortie valorisée (PU × Qté)"
            )
            self.label_prix_unit.grid()
            self.entry_prix_unit.grid()
        else:
            self.label_type_info.configure(
                text="  Bon de Sortie — déduction du stock sans valorisation"
            )
            self.label_prix_unit.grid_remove()
            self.entry_prix_unit.grid_remove()

        self.generer_reference()
        self.reset_form()
        self._create_treeview()

    def _toggle_price_columns(self):
        """
        Bascule l'affichage des colonnes prix / montant (CI seulement).
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        self.show_price_columns = not self.show_price_columns
        self.charger_details_treeview()
        if self.show_price_columns:
            self.btn_toggle_prix.configure(
                text="👁 Masquer Prix / Montant",
                fg_color="#E65100",
            )
        else:
            self.btn_toggle_prix.configure(
                text="👁 Afficher Prix / Montant",
                fg_color=Colors.WARNING,
            )

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 4 — FORMATAGE ET CALCUL DE STOCK
    # ══════════════════════════════════════════════════════════════════════════

    def formater_nombre(self, nombre) -> str:
        """Formate un nombre avec séparateur de milliers (1.000.000,00)."""
        try:
            return (
                "{:,.2f}".format(float(nombre))
                .replace(',', '_T_').replace('.', ',').replace('_T_', '.')
            )
        except Exception:
            return "0,00"

    def parser_nombre(self, texte) -> float:
        """Convertit un nombre formaté (1.000,00) en float."""
        try:
            return float(str(texte).replace('.', '').replace(',', '.'))
        except Exception:
            return 0.0

    def calculer_stock_article(self, idarticle, idunite_cible, idmag=None) -> float:
        """
        Calcul consolidé du stock via réservoir commun (qtunite).
        Identique à page_venteParMsin, page_stock, page_transfert.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        conn = self.connect_db()
        if not conn:
            return 0

        try:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT idunite, codearticle, COALESCE(qtunite,1) FROM tb_unite WHERE idarticle=%s",
                (idarticle,),
            )
            unites_liees = cursor.fetchall()

            qtunite_affichage = 1
            for idu, code, qt_u in unites_liees:
                if idu == idunite_cible:
                    qtunite_affichage = qt_u if qt_u > 0 else 1
                    break

            total_stock_global_base = 0.0

            for idu_boucle, code_boucle, qtunite_boucle in unites_liees:

                def qry(sql, params):
                    cursor.execute(sql, params)
                    return cursor.fetchone()[0] or 0

                # Réceptions
                q = "SELECT COALESCE(SUM(qtlivrefrs),0) FROM tb_livraisonfrs WHERE idarticle=%s AND idunite=%s AND deleted=0"
                p = [idarticle, idu_boucle]
                if idmag: q += " AND idmag=%s"; p.append(idmag)
                receptions = qry(q, p)

                # Ventes
                q = "SELECT COALESCE(SUM(qtvente),0) FROM tb_ventedetail WHERE idarticle=%s AND idunite=%s AND deleted=0"
                p = [idarticle, idu_boucle]
                if idmag: q += " AND idmag=%s"; p.append(idmag)
                ventes = qry(q, p)

                # Sorties
                q = "SELECT COALESCE(SUM(qtsortie),0) FROM tb_sortiedetail WHERE idarticle=%s AND idunite=%s"
                p = [idarticle, idu_boucle]
                if idmag: q += " AND idmag=%s"; p.append(idmag)
                sorties = qry(q, p)

                # Transferts entrants
                q = "SELECT COALESCE(SUM(qttransfert),0) FROM tb_transfertdetail WHERE idarticle=%s AND idunite=%s AND deleted=0"
                p = [idarticle, idu_boucle]
                if idmag: q += " AND idmagentree=%s"; p.append(idmag)
                t_in = qry(q, p)

                # Transferts sortants
                q = "SELECT COALESCE(SUM(qttransfert),0) FROM tb_transfertdetail WHERE idarticle=%s AND idunite=%s AND deleted=0"
                p = [idarticle, idu_boucle]
                if idmag: q += " AND idmagsortie=%s"; p.append(idmag)
                t_out = qry(q, p)

                # Inventaires
                q = "SELECT COALESCE(SUM(qtinventaire),0) FROM tb_inventaire WHERE codearticle=%s"
                p = [code_boucle]
                if idmag: q += " AND idmag=%s"; p.append(idmag)
                inv = qry(q, p)

                # Avoirs
                q = """SELECT COALESCE(SUM(ad.qtavoir),0)
                       FROM tb_avoirdetail ad INNER JOIN tb_avoir a ON ad.idavoir=a.id
                       WHERE ad.idarticle=%s AND ad.idunite=%s AND a.deleted=0 AND ad.deleted=0"""
                p = [idarticle, idu_boucle]
                if idmag: q += " AND ad.idmag=%s"; p.append(idmag)
                avoirs = qry(q, p)

                solde = receptions + t_in + inv + avoirs - ventes - sorties - t_out
                total_stock_global_base += solde * qtunite_boucle

            return max(0, total_stock_global_base / qtunite_affichage)

        except Exception as e:
            print(f"Erreur calcul stock : {e}")
            traceback.print_exc()
            return 0
        finally:
            cursor.close()
            conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 5 — CHARGEMENTS INITIAUX
    # ══════════════════════════════════════════════════════════════════════════

    def generer_reference(self):
        """
        Génère la référence de la prochaine sortie selon le type (BS ou CI).
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        conn = self.connect_db()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            annee       = datetime.now().year
            type_prefix = self.type_sortie

            if self.type_sortie == "CI":
                sql = """
                    SELECT refconsommation FROM tb_consommationinterne
                    WHERE EXTRACT(YEAR FROM dateregistre)=%s AND refconsommation LIKE %s
                    ORDER BY id DESC LIMIT 1
                """
            else:
                sql = """
                    SELECT refsortie FROM tb_sortie
                    WHERE EXTRACT(YEAR FROM dateregistre)=%s AND refsortie LIKE %s
                    ORDER BY id DESC LIMIT 1
                """

            cursor.execute(sql, (annee, f"{annee}-{type_prefix}-%"))
            derniere_ref  = cursor.fetchone()
            nouveau_numero = 1

            if derniere_ref:
                partie_num = derniere_ref[0].split('-')[-1]
                try:
                    nouveau_numero = int(partie_num) + 1
                except ValueError:
                    nouveau_numero = 1

            nouvelle_ref = f"{annee}-{type_prefix}-{nouveau_numero:05d}"

            self.entry_ref_sortie.configure(state="normal")
            self.entry_ref_sortie.delete(0, "end")
            self.entry_ref_sortie.insert(0, nouvelle_ref)
            self.entry_ref_sortie.configure(state="readonly")

        except Exception as e:
            messagebox.showerror("Erreur", f"Génération référence : {e}")
        finally:
            conn.close()

    def charger_magasins(self):
        """
        Charge les magasins dans le ComboBox.
        Sélectionne par défaut le magasin de l'utilisateur connecté.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        conn = self.connect_db()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT idmag, designationmag FROM tb_magasin "
                "WHERE deleted=0 ORDER BY designationmag"
            )
            magasins = cursor.fetchall()

            self.magasins_map = {nom: id_ for id_, nom in magasins}
            self.magasins_ids = [id_ for id_, nom in magasins]
            noms              = list(self.magasins_map.keys())

            self.combo_magasin.configure(values=noms)
            if noms:
                idmag_defaut = None
                cursor.execute(
                    "SELECT idmag FROM tb_users WHERE iduser=%s LIMIT 1",
                    (self.id_user_connecte,),
                )
                row_user = cursor.fetchone()
                if row_user:
                    idmag_defaut = row_user[0]

                nom_defaut = next(
                    (nom for id_, nom in magasins if id_ == idmag_defaut), None
                )
                self.combo_magasin.set(nom_defaut if nom_defaut else noms[0])
            else:
                self.combo_magasin.set("Aucun magasin trouvé")

        except Exception as e:
            messagebox.showerror("Erreur", f"Chargement magasins : {e}")
        finally:
            conn.close()

    def charger_infos_societe(self):
        """
        Charge les informations de la société depuis tb_infosociete.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        _default = {
            'nomsociete': 'SOCIÉTÉ', 'adressesociete': 'N/A',
            'contactsociete': 'N/A', 'villesociete': 'N/A',
            'nifsociete': 'N/A', 'statsociete': 'N/A', 'cifsociete': 'N/A',
        }
        conn = self.connect_db()
        if not conn:
            self.infos_societe = _default
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT nomsociete, adressesociete, contactsociete, villesociete,
                       nifsociete, statsociete, cifsociete
                FROM tb_infosociete LIMIT 1
                """
            )
            result = cursor.fetchone()
            self.infos_societe = {
                'nomsociete':     result[0] or 'SOCIÉTÉ',
                'adressesociete': result[1] or 'N/A',
                'contactsociete': result[2] or 'N/A',
                'villesociete':   result[3] or 'N/A',
                'nifsociete':     result[4] or 'N/A',
                'statsociete':    result[5] or 'N/A',
                'cifsociete':     result[6] or 'N/A',
            } if result else _default

        except Exception as e:
            print(f"Erreur infos société : {e}")
            self.infos_societe = _default
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 6 — RECHERCHE D'ARTICLE
    # ══════════════════════════════════════════════════════════════════════════

    def open_recherche_article(self):
        """
        Ouvre la fenêtre de recherche d'article avec la requête consolidée
        (réservoir commun via qtunite) — identique à page_venteParMsin.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        fen = ctk.CTkToplevel(self)
        fen.title("Rechercher un article pour la sortie")
        fen.geometry("1000x600")
        fen.grab_set()

        main_frame = ctk.CTkFrame(fen)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            main_frame, text="Sélectionner un article",
            font=Fonts.heading(16),
        ).pack(pady=(0, 10))

        # Barre de recherche
        search_frame = ctk.CTkFrame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(search_frame, text="🔍 Rechercher :").pack(side="left", padx=5)
        entry_search = ctk.CTkEntry(
            search_frame, placeholder_text="Code ou désignation…", width=300,
        )
        entry_search.pack(side="left", padx=5, fill="x", expand=True)

        # Treeview
        tree_frame = ctk.CTkFrame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))

        style = ttk.Style()
        style.configure(
            "ArtSearch.Treeview",
            rowheight=22, font=('Segoe UI', 8),
            background=Colors.BG_CARD, foreground=Colors.TEXT_PRIMARY,
            fieldbackground=Colors.BG_CARD, borderwidth=0,
        )
        style.configure(
            "ArtSearch.Treeview.Heading",
            background=Colors.BG_HEADER, foreground=Colors.TEXT_ON_DARK,
            font=('Segoe UI', 8, 'bold'), relief="flat",
        )

        colonnes = ("ID_Article", "ID_Unite", "Code", "Désignation", "Unité", "Stock", "Prix U.")
        tree = ttk.Treeview(
            tree_frame, columns=colonnes, show='headings',
            height=15, style="ArtSearch.Treeview",
        )
        tree.tag_configure("even", background=Colors.BG_CARD)
        tree.tag_configure("odd",  background=Colors.BG_ROW_ALT)

        nom_mag = (self.combo_magasin.get() or "").strip()
        col_cfg = {
            "ID_Article":  (0,   False, "center"),
            "ID_Unite":    (0,   False, "center"),
            "Code":        (120, True,  "w"),
            "Désignation": (300, True,  "w"),
            "Unité":       (80,  True,  "w"),
            "Stock":       (100, True,  "e"),
            "Prix U.":     (100, True,  "e"),
        }
        for col, (w, stretch, anchor) in col_cfg.items():
            lbl = (f"Magasin {nom_mag}" if col == "Stock" and nom_mag else col)
            tree.heading(col, text=lbl)
            tree.column(col, width=w, stretch=stretch, anchor=anchor)
        tree["displaycolumns"] = ("Code", "Désignation", "Unité", "Stock")

        scrollbar = ctk.CTkScrollbar(tree_frame, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ── Requête consolidée ────────────────────────────────────────────────
        QUERY_STOCK = """
        WITH unite_hierarchie AS (
            SELECT idarticle, idunite, niveau, qtunite, designationunite
            FROM tb_unite WHERE deleted=0
        ),
        unite_coeff AS (
            SELECT idarticle, idunite, niveau, qtunite, designationunite,
                exp(sum(ln(NULLIF(CASE WHEN qtunite>0 THEN qtunite ELSE 1 END,0)))
                    OVER (PARTITION BY idarticle ORDER BY niveau
                          ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                ) AS coeff_hierarchique
            FROM unite_hierarchie
        ),
        base_unite_par_article AS (
            SELECT DISTINCT ON (idarticle) idarticle, idunite
            FROM tb_unite WHERE deleted=0
            ORDER BY idarticle, qtunite ASC, idunite ASC
        ),
        rec  AS (SELECT lf.idarticle,lf.idunite,lf.idmag,SUM(lf.qtlivrefrs) AS q FROM tb_livraisonfrs lf WHERE lf.deleted=0 GROUP BY lf.idarticle,lf.idunite,lf.idmag),
        ven  AS (SELECT vd.idarticle,vd.idunite,v.idmag,SUM(vd.qtvente)     AS q FROM tb_ventedetail vd INNER JOIN tb_vente v ON vd.idvente=v.id AND v.deleted=0 AND v.statut='VALIDEE' WHERE vd.deleted=0 GROUP BY vd.idarticle,vd.idunite,v.idmag),
        tin  AS (SELECT t.idarticle,t.idunite,t.idmagentree AS idmag,SUM(t.qttransfert) AS q FROM tb_transfertdetail t WHERE t.deleted=0 GROUP BY t.idarticle,t.idunite,t.idmagentree),
        tout AS (SELECT t.idarticle,t.idunite,t.idmagsortie AS idmag,SUM(t.qttransfert) AS q FROM tb_transfertdetail t WHERE t.deleted=0 GROUP BY t.idarticle,t.idunite,t.idmagsortie),
        sor  AS (SELECT sd.idarticle,sd.idunite,sd.idmag,SUM(sd.qtsortie) AS q FROM tb_sortiedetail sd GROUP BY sd.idarticle,sd.idunite,sd.idmag),
        inv  AS (SELECT bu.idarticle,bu.idunite,i.idmag,SUM(i.qtinventaire) AS q FROM tb_inventaire i INNER JOIN tb_unite u ON i.codearticle=u.codearticle INNER JOIN base_unite_par_article bu ON bu.idarticle=u.idarticle AND bu.idunite=u.idunite GROUP BY bu.idarticle,bu.idunite,i.idmag),
        avo  AS (SELECT ad.idarticle,ad.idunite,ad.idmag,SUM(ad.qtavoir) AS q FROM tb_avoir a INNER JOIN tb_avoirdetail ad ON a.id=ad.idavoir WHERE a.deleted=0 AND ad.deleted=0 GROUP BY ad.idarticle,ad.idunite,ad.idmag),
        conso AS (SELECT cd.idarticle,cd.idunite,cd.idmag,SUM(cd.qtconsomme) AS q FROM tb_consommationinterne_details cd GROUP BY cd.idarticle,cd.idunite,cd.idmag),
        ech_in  AS (SELECT dce.idarticle,dce.idunite,dce.idmagasin AS idmag,SUM(dce.quantite_entree) AS q FROM tb_detailchange_entree dce GROUP BY dce.idarticle,dce.idunite,dce.idmagasin),
        ech_out AS (SELECT dcs.idarticle,dcs.idunite,dcs.idmagasin AS idmag,SUM(dcs.quantite_sortie) AS q FROM tb_detailchange_sortie dcs GROUP BY dcs.idarticle,dcs.idunite,dcs.idmagasin),
        mv AS (
            SELECT idarticle,idunite,idmag,q,'rec'   AS t FROM rec
            UNION ALL SELECT idarticle,idunite,idmag,q,'ven'   FROM ven
            UNION ALL SELECT idarticle,idunite,idmag,q,'tin'   FROM tin
            UNION ALL SELECT idarticle,idunite,idmag,q,'tout'  FROM tout
            UNION ALL SELECT idarticle,idunite,idmag,q,'sor'   FROM sor
            UNION ALL SELECT idarticle,idunite,idmag,q,'inv'   FROM inv
            UNION ALL SELECT idarticle,idunite,idmag,q,'avo'   FROM avo
            UNION ALL SELECT idarticle,idunite,idmag,q,'conso' FROM conso
            UNION ALL SELECT idarticle,idunite,idmag,q,'ei'    FROM ech_in
            UNION ALL SELECT idarticle,idunite,idmag,q,'eo'    FROM ech_out
        ),
        solde AS (
            SELECT mv.idarticle, mv.idmag,
                SUM(CASE mv.t
                    WHEN 'rec'   THEN  mv.q * COALESCE(uc.coeff_hierarchique,1)
                    WHEN 'tin'   THEN  mv.q * COALESCE(uc.coeff_hierarchique,1)
                    WHEN 'inv'   THEN  mv.q * COALESCE(uc.coeff_hierarchique,1)
                    WHEN 'avo'   THEN  mv.q * COALESCE(uc.coeff_hierarchique,1)
                    WHEN 'ei'    THEN  mv.q * COALESCE(uc.coeff_hierarchique,1)
                    WHEN 'ven'   THEN -mv.q * COALESCE(uc.coeff_hierarchique,1)
                    WHEN 'sor'   THEN -mv.q * COALESCE(uc.coeff_hierarchique,1)
                    WHEN 'tout'  THEN -mv.q * COALESCE(uc.coeff_hierarchique,1)
                    WHEN 'conso' THEN -mv.q * COALESCE(uc.coeff_hierarchique,1)
                    WHEN 'eo'    THEN -mv.q * COALESCE(uc.coeff_hierarchique,1)
                    ELSE 0
                END) AS solde_base
            FROM mv LEFT JOIN unite_coeff uc ON uc.idarticle=mv.idarticle AND uc.idunite=mv.idunite
            GROUP BY mv.idarticle, mv.idmag
        ),
        dernier_prix AS (
            SELECT idarticle, idunite, prix,
                   ROW_NUMBER() OVER (PARTITION BY idarticle, idunite ORDER BY id DESC) AS rn
            FROM tb_prix
        )
        SELECT u.idarticle, u.idunite, u.codearticle, a.designation,
               uc.designationunite,
               GREATEST(COALESCE(s.solde_base,0) / NULLIF(COALESCE(uc.coeff_hierarchique,1),0), 0) AS stock_total,
               COALESCE(p.prix,0) AS prix_unitaire
        FROM tb_article a
        INNER JOIN tb_unite u          ON a.idarticle=u.idarticle
        LEFT JOIN  unite_coeff uc      ON uc.idarticle=u.idarticle AND uc.idunite=u.idunite
        LEFT JOIN  solde s             ON s.idarticle=u.idarticle AND s.idmag=%s
        LEFT JOIN  dernier_prix p      ON a.idarticle=p.idarticle AND u.idunite=p.idunite AND p.rn=1
        WHERE a.deleted=0
          AND (u.codearticle ILIKE %s OR a.designation ILIKE %s)
        ORDER BY a.designation ASC, u.codearticle ASC, u.idunite ASC
        """

        def charger_articles(filtre=""):
            for item in tree.get_children():
                tree.delete(item)

            conn = self.connect_db()
            if not conn:
                return
            try:
                cur             = conn.cursor()
                filtre_like     = f"%{filtre}%"
                designationmag  = (self.combo_magasin.get() or "").strip()
                idmag_actif     = self.magasins_map.get(designationmag)
                tree.heading("Stock", text=f"Magasin {designationmag}" if designationmag else "Magasin")

                if idmag_actif is None:
                    return

                cur.execute(QUERY_STOCK, (idmag_actif, filtre_like, filtre_like))
                for idx, row in enumerate(cur.fetchall()):
                    tree.insert('', 'end', values=(
                        row[0], row[1],
                        row[2] or "", row[3] or "", row[4] or "",
                        self.formater_nombre(row[5]),
                        self.formater_nombre(row[6]),
                    ), tags=("even" if idx % 2 == 0 else "odd",))

            except Exception as e:
                messagebox.showerror("Erreur", f"Chargement articles : {e}")
            finally:
                if 'cur' in locals() and cur: cur.close()
                if conn: conn.close()

        def valider_selection():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Attention", "Sélectionnez un article.")
                return
            values = tree.item(sel[0]).get('values', [])
            if len(values) < 7:
                messagebox.showerror("Erreur", "Données incomplètes.")
                return

            article = {
                'idarticle':       values[0],
                'idunite':         values[1],
                'code_article':    values[2],
                'nom_article':     values[3],
                'nom_unite':       values[4],
                'stock_disponible': self.parser_nombre(str(values[5])),
                'prix_unitaire':   self.parser_nombre(str(values[6])),
            }
            fen.destroy()
            self.on_article_selected(article)

        entry_search.bind('<KeyRelease>', lambda e: charger_articles(entry_search.get()))
        tree.bind('<Double-Button-1>', lambda e: valider_selection())

        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x")
        ctk.CTkButton(
            btn_frame, text="❌ Annuler", command=fen.destroy,
            fg_color=Colors.DANGER, hover_color=Colors.DANGER_DARK,
        ).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(
            btn_frame, text="✅ Valider", command=valider_selection,
            fg_color=Colors.SUCCESS_DARK, hover_color=Colors.INFO_DARK,
        ).pack(side="right", padx=5, pady=5)

        charger_articles()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 7 — GESTION DU DÉTAIL DE SORTIE
    # ══════════════════════════════════════════════════════════════════════════

    def on_article_selected(self, article_data):
        """Met à jour les champs de saisie après sélection d'un article."""
        self.article_selectionne = article_data

        designation = f"[{article_data.get('code_article','N/A')}] {article_data['nom_article']}"
        self.entry_article.configure(state="normal")
        self.entry_article.delete(0, "end")
        self.entry_article.insert(0, designation)
        self.entry_article.configure(state="readonly")

        self.entry_unite.configure(state="normal")
        self.entry_unite.delete(0, "end")
        self.entry_unite.insert(0, article_data['nom_unite'])
        self.entry_unite.configure(state="readonly")

        self.entry_prix_unit.configure(state="normal")
        self.entry_prix_unit.delete(0, "end")
        self.entry_prix_unit.insert(0, self.formater_nombre(article_data.get('prix_unitaire', 0)))
        self.entry_prix_unit.configure(state="readonly")

        self.entry_qtsortie.delete(0, "end")
        self.entry_qtsortie.focus_set()

    def valider_detail(self):
        """
        Ajoute ou modifie un article dans la liste temporaire.
        Vérifie le stock disponible avant tout ajout.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        if not self.article_selectionne:
            messagebox.showwarning("Attention", "Sélectionnez d'abord un article.")
            return

        try:
            qtsortie = self.parser_nombre(self.entry_qtsortie.get().strip())
            if qtsortie <= 0:
                raise ValueError
        except Exception:
            messagebox.showerror("Erreur", "La quantité doit être un nombre positif.")
            return

        designationmag = self.combo_magasin.get()
        idmag          = self.magasins_map.get(designationmag)
        if not idmag:
            messagebox.showerror("Erreur", "Sélectionnez un magasin valide.")
            return

        stock_disponible = self.article_selectionne.get('stock_disponible', 0)

        if stock_disponible <= 0:
            messagebox.showerror(
                "Stock Insuffisant",
                f"Stock actuel : {self.formater_nombre(stock_disponible)} "
                f"{self.article_selectionne['nom_unite']}.\nEnregistrement bloqué.",
            )
            return

        if qtsortie > stock_disponible:
            messagebox.showerror(
                "Stock Insuffisant",
                f"Qté demandée ({self.formater_nombre(qtsortie)}) > "
                f"stock disponible ({self.formater_nombre(stock_disponible)}).",
            )
            return

        prix_unitaire = (
            self.article_selectionne.get('prix_unitaire', 0)
            if self.type_sortie == "CI" else 0
        )
        motif_ligne = self.entry_motif.get().strip() or "Aucune description"

        nouveau_detail = {
            'idmag':           idmag,
            'designationmag':  designationmag,
            'idarticle':       self.article_selectionne['idarticle'],
            'code_article':    self.article_selectionne.get('code_article', 'N/A'),
            'nom_article':     self.article_selectionne['nom_article'],
            'idunite':         self.article_selectionne['idunite'],
            'nom_unite':       self.article_selectionne['nom_unite'],
            'qtsortie':        qtsortie,
            'motif':           motif_ligne,
            'prix_unitaire':   prix_unitaire,
            'montant_total':   qtsortie * prix_unitaire,
        }

        if self.index_ligne_selectionnee is not None:
            self.detail_sortie[self.index_ligne_selectionnee] = nouveau_detail
            messagebox.showinfo("Succès", "Ligne modifiée.")
        else:
            # Vérifier doublon → proposition de fusion
            for i, detail in enumerate(self.detail_sortie):
                if (detail['idarticle'] == nouveau_detail['idarticle']
                        and detail['idunite'] == nouveau_detail['idunite']
                        and detail['idmag'] == nouveau_detail['idmag']):

                    nouvelle_qte = detail['qtsortie'] + nouveau_detail['qtsortie']
                    if nouvelle_qte > stock_disponible:
                        messagebox.showerror("Erreur", "Fusion dépasserait le stock.")
                        return

                    if messagebox.askyesno(
                        "Doublon détecté",
                        f"Article « {detail['nom_article']} » déjà présent. Fusionner ?",
                    ):
                        self.detail_sortie[i]['qtsortie']      = nouvelle_qte
                        self.detail_sortie[i]['montant_total']  = nouvelle_qte * detail['prix_unitaire']
                        m_exist = (self.detail_sortie[i].get('motif') or "").strip()
                        if motif_ligne and motif_ligne != "Aucune description" and motif_ligne not in m_exist:
                            self.detail_sortie[i]['motif'] = f"{m_exist}, {motif_ligne}".strip(", ")
                        messagebox.showinfo("Succès", "Quantité fusionnée.")
                        self.charger_details_treeview()
                        self.reset_detail_form()
                    return

            self.detail_sortie.append(nouveau_detail)

        self.charger_details_treeview()
        self.reset_detail_form()

    def charger_details_treeview(self):
        """
        Recharge le Treeview depuis self.detail_sortie.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        if self.tree_details is None:
            return
        for item in self.tree_details.get_children():
            self.tree_details.delete(item)

        for idx, detail in enumerate(self.detail_sortie):
            values = [
                detail['idarticle'], detail['idunite'], detail['idmag'],
                detail.get('code_article', 'N/A'),
                detail['nom_article'],
                detail['designationmag'],
                detail['nom_unite'],
                self.formater_nombre(detail['qtsortie']),
            ]
            if self.type_sortie == "CI":
                values.append(self.formater_nombre(detail.get('montant_total', 0)))
            values.append(detail.get('motif', ''))

            self.tree_details.insert(
                '', 'end', values=values,
                tags=("even" if idx % 2 == 0 else "odd",),
            )

    def modifier_detail(self, event):
        """
        Double-clic sur une ligne → charge les données dans le formulaire.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        selected_item = self.tree_details.focus()
        if not selected_item:
            return

        try:
            self.index_ligne_selectionnee = self.tree_details.index(selected_item)
            detail = self.detail_sortie[self.index_ligne_selectionnee]
        except IndexError:
            messagebox.showerror("Erreur", "Impossible de récupérer la ligne.")
            self.reset_detail_form()
            return

        self.article_selectionne = {
            'idarticle':   detail['idarticle'],
            'nom_article': detail['nom_article'],
            'idunite':     detail['idunite'],
            'nom_unite':   detail['nom_unite'],
            'code_article': detail.get('code_article', 'N/A'),
        }

        designation = f"[{detail.get('code_article','N/A')}] {detail['nom_article']}"
        self.entry_article.configure(state="normal")
        self.entry_article.delete(0, "end")
        self.entry_article.insert(0, designation)
        self.entry_article.configure(state="readonly")

        self.entry_unite.configure(state="normal")
        self.entry_unite.delete(0, "end")
        self.entry_unite.insert(0, detail['nom_unite'])
        self.entry_unite.configure(state="readonly")

        self.entry_qtsortie.delete(0, "end")
        self.entry_qtsortie.insert(0, self.formater_nombre(detail['qtsortie']))
        self.entry_motif.delete(0, "end")
        self.entry_motif.insert(0, detail.get('motif', ''))

        # Signal visuel : bouton Ajouter → "Valider Modif" orange
        self.btn_ajouter.configure(
            text="✔ Valider Modif",
            fg_color=Colors.WARNING, hover_color="#E65100",
        )
        self.btn_annuler_mod.configure(state="normal")

    def supprimer_detail(self):
        """Supprime la ligne sélectionnée du Treeview et de la liste."""
        selected_item = self.tree_details.focus()
        if not selected_item:
            messagebox.showwarning("Attention", "Sélectionnez une ligne à supprimer.")
            return

        if messagebox.askyesno("Confirmation", "Supprimer cette ligne ?"):
            try:
                index = self.tree_details.index(selected_item)
                self.detail_sortie.pop(index)
                self.tree_details.delete(selected_item)
                self.reset_detail_form()
                messagebox.showinfo("Succès", "Ligne supprimée.")
            except Exception as e:
                messagebox.showerror("Erreur", f"Suppression impossible : {e}")

    def reset_detail_form(self):
        """Réinitialise les champs de saisie article et les boutons."""
        self.article_selectionne      = None
        self.index_ligne_selectionnee = None

        for entry, state in [
            (self.entry_article, "readonly"),
            (self.entry_unite,   "readonly"),
        ]:
            entry.configure(state="normal")
            entry.delete(0, "end")
            entry.configure(state=state)

        self.entry_qtsortie.delete(0, "end")
        self.entry_motif.delete(0, "end")

        self.btn_ajouter.configure(
            text="+ Ajouter",
            fg_color=Colors.SUCCESS_DARK, hover_color=Colors.INFO_DARK,
        )
        self.btn_annuler_mod.configure(state="disabled")

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 8 — RECHERCHE ET CHARGEMENT D'UN BON DE SORTIE
    # ══════════════════════════════════════════════════════════════════════════

    def ouvrir_recherche_sortie(self):
        """
        Fenêtre modale pour rechercher et charger un bon de sortie existant.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        fen = ctk.CTkToplevel(self)
        fen.title("Rechercher un bon de sortie")
        fen.geometry("1000x500")
        fen.grab_set()

        main_frame = ctk.CTkFrame(fen)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            main_frame, text="Sélectionner un bon de sortie",
            font=Fonts.heading(16),
        ).pack(pady=(0, 10))

        search_frame = ctk.CTkFrame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(search_frame, text="🔍 Rechercher :").pack(side="left", padx=5)
        entry_search = ctk.CTkEntry(
            search_frame, placeholder_text="Référence ou motif…", width=300,
        )
        entry_search.pack(side="left", padx=5, fill="x", expand=True)

        tree_frame = ctk.CTkFrame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))

        colonnes = ("ID", "Référence", "Date", "Motif", "Utilisateur", "Nb Lignes")
        tree = ttk.Treeview(tree_frame, columns=colonnes, show='headings', height=12)
        tree.tag_configure("even", background=Colors.BG_CARD)
        tree.tag_configure("odd",  background=Colors.BG_ROW_ALT)

        col_w = {
            "ID": (0, False), "Référence": (150, True), "Date": (100, True),
            "Motif": (300, True), "Utilisateur": (150, True), "Nb Lignes": (80, True),
        }
        for col, (w, stretch) in col_w.items():
            tree.heading(col, text=col)
            tree.column(col, width=w, stretch=stretch)

        scrollbar = ctk.CTkScrollbar(tree_frame, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        label_count = ctk.CTkLabel(main_frame, text="")
        label_count.pack(pady=5)

        def charger_sorties(filtre=""):
            for item in tree.get_children():
                tree.delete(item)
            conn = self.connect_db()
            if not conn:
                return
            try:
                cursor = conn.cursor()
                query = """
                    SELECT s.id, s.refsortie, s.dateregistre,
                       COALESCE(NULLIF((
                           SELECT string_agg(NULLIF(TRIM(sd2.motif),''),', ' ORDER BY sd2.id)
                           FROM tb_sortiedetail sd2 WHERE sd2.idsortie=s.id
                       ),''),'Motif non précisé') AS motif_lignes,
                       CONCAT(u.prenomuser,' ',u.nomuser) AS utilisateur,
                       (SELECT COUNT(*) FROM tb_sortiedetail sd WHERE sd.idsortie=s.id) AS nb_lignes
                    FROM tb_sortie s
                    LEFT JOIN tb_users u ON s.iduser=u.iduser
                    WHERE s.deleted=0
                """
                params = []
                if filtre:
                    query += """
                        AND (LOWER(s.refsortie) LIKE LOWER(%s)
                          OR LOWER(COALESCE((
                              SELECT string_agg(NULLIF(TRIM(sd2.motif),''),', ' ORDER BY sd2.id)
                              FROM tb_sortiedetail sd2 WHERE sd2.idsortie=s.id
                          ),'')) LIKE LOWER(%s))"""
                    params = [f"%{filtre}%", f"%{filtre}%"]
                query += " ORDER BY s.dateregistre DESC, s.refsortie DESC"

                cursor.execute(query, params)
                resultats = cursor.fetchall()
                for idx, row in enumerate(resultats):
                    date_str = row[2].strftime("%d/%m/%Y") if row[2] else ""
                    tree.insert('', 'end',
                                values=(row[0], row[1], date_str, row[3] or "", row[4] or "", row[5] or 0),
                                tags=("even" if idx % 2 == 0 else "odd",))
                label_count.configure(text=f"{len(resultats)} bon(s) de sortie")

            except Exception as e:
                messagebox.showerror("Erreur", f"Chargement : {e}")
            finally:
                if 'cursor' in locals() and cursor: cursor.close()
                if conn: conn.close()

        def valider_selection():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Attention", "Sélectionnez un bon de sortie.")
                return
            idsortie = tree.item(sel[0])['values'][0]
            fen.destroy()
            self.charger_sortie(idsortie)

        entry_search.bind('<KeyRelease>', lambda e: charger_sorties(entry_search.get()))
        tree.bind('<Double-Button-1>', lambda e: valider_selection())

        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x")
        ctk.CTkButton(
            btn_frame, text="❌ Annuler", command=fen.destroy,
            fg_color=Colors.DANGER, hover_color=Colors.DANGER_DARK,
        ).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(
            btn_frame, text="✅ Charger", command=valider_selection,
            fg_color=Colors.SUCCESS_DARK, hover_color=Colors.INFO_DARK,
        ).pack(side="right", padx=5, pady=5)

        charger_sorties()

    def charger_sortie(self, idsortie):
        """
        Charge un bon de sortie en mode consultation / impression.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        conn = self.connect_db()
        if not conn:
            return

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT s.id, s.refsortie, s.dateregistre, s.description,
                       CONCAT(u.prenomuser,' ',u.nomuser) AS utilisateur
                FROM tb_sortie s
                LEFT JOIN tb_users u ON s.iduser=u.iduser
                WHERE s.id=%s AND s.deleted=0
                """,
                (idsortie,),
            )
            sortie = cursor.fetchone()
            if not sortie:
                messagebox.showerror("Erreur", "Bon de sortie non trouvé.")
                return

            cursor.execute(
                """
                SELECT sd.idmag, m.designationmag, sd.idarticle, u.codearticle,
                       a.designation, sd.idunite, u.designationunite, sd.qtsortie, sd.motif
                FROM tb_sortiedetail sd
                INNER JOIN tb_article a ON sd.idarticle=a.idarticle
                INNER JOIN tb_unite   u ON sd.idunite=u.idunite
                INNER JOIN tb_magasin m ON sd.idmag=m.idmag
                WHERE sd.idsortie=%s
                """,
                (idsortie,),
            )
            details = cursor.fetchall()

            self.reset_form(reset_imprimer=False)

            self.mode_modification = True
            self.idsortie_charge   = idsortie
            self.derniere_idsortie_enregistree = idsortie

            self.entry_ref_sortie.configure(state="normal")
            self.entry_ref_sortie.delete(0, "end")
            self.entry_ref_sortie.insert(0, sortie[1])
            self.entry_ref_sortie.configure(state="readonly")

            self.entry_date_sortie.delete(0, "end")
            self.entry_date_sortie.insert(0, sortie[2].strftime("%d/%m/%Y"))

            self.detail_sortie = []
            for d in details:
                idmag, designationmag, idarticle, codearticle, designation, \
                    idunite, designationunite, qtsortie, motif = d
                self.detail_sortie.append({
                    'idmag': idmag, 'designationmag': designationmag,
                    'idarticle': idarticle, 'code_article': codearticle,
                    'nom_article': designation, 'idunite': idunite,
                    'nom_unite': designationunite,
                    'qtsortie': qtsortie, 'motif': motif or "",
                })

            self.charger_details_treeview()

            self.btn_imprimer.configure(state="normal")
            self.btn_imprimer.grid()
            self.btn_enregistrer.configure(state="disabled", text="📄 Mode Consultation")

            messagebox.showinfo(
                "Chargement réussi",
                f"Bon de sortie {sortie[1]} chargé.\n"
                "Vous pouvez maintenant l'imprimer.\n\n"
                "Note : L'enregistrement est désactivé en mode consultation.",
            )

        except Exception as e:
            messagebox.showerror("Erreur", f"Chargement bon de sortie : {e}")
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 9 — ENREGISTREMENT
    # ══════════════════════════════════════════════════════════════════════════

    def enregistrer_sortie(self):
        """
        Enregistre la sortie (BS) ou la consommation interne (CI).
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        if not self.detail_sortie:
            messagebox.showwarning("Attention", "La liste est vide.")
            return

        ref_sortie       = self.entry_ref_sortie.get()
        date_sortie_str  = self.entry_date_sortie.get()
        designationmag   = self.combo_magasin.get()

        if not ref_sortie or not date_sortie_str or not designationmag:
            messagebox.showwarning("Attention", "Remplissez tous les champs obligatoires.")
            return

        try:
            date_sortie = datetime.strptime(date_sortie_str, "%d/%m/%Y").date()
        except ValueError:
            messagebox.showerror("Erreur de Date", "Format attendu : JJ/MM/AAAA")
            return

        montant_total_ci  = sum(d.get('montant_total', 0) for d in self.detail_sortie)
        type_label        = "Sortie d'articles (BS)" if self.type_sortie == "BS" else "Consommation interne (CI)"

        if self.type_sortie == "BS":
            msg_conf = (
                f"CONFIRMEZ LA SORTIE D'ARTICLES\n\n"
                f"Type : {type_label}\nRéférence : {ref_sortie}\n"
                f"Articles : {len(self.detail_sortie)}\n\n"
                "Enregistrer cette sortie ?"
            )
        else:
            msg_conf = (
                f"CONFIRMEZ LA CONSOMMATION INTERNE\n\n"
                f"Type : {type_label}\nRéférence : {ref_sortie}\n"
                f"Articles : {len(self.detail_sortie)}\n"
                f"Valeur totale : {self.formater_nombre(montant_total_ci)} Ar\n\n"
                "Enregistrer ?"
            )

        if not messagebox.askyesno("Confirmation", msg_conf):
            return

        conn = self.connect_db()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            if self.type_sortie == "BS":
                self._enregistrer_sortie_bs(cursor, conn, ref_sortie, date_sortie, designationmag)
            else:
                self._enregistrer_consommation_ci(cursor, conn, ref_sortie, date_sortie, designationmag, montant_total_ci)
        except psycopg2.Error as e:
            if conn: conn.rollback()
            messagebox.showerror("Erreur BD", str(e))
        except Exception as e:
            if conn: conn.rollback()
            messagebox.showerror("Erreur", str(e))
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()

    def _enregistrer_sortie_bs(self, cursor, conn, ref_sortie, date_sortie, designationmag):
        """
        Enregistre un Bon de Sortie dans tb_sortie + tb_sortiedetail.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        cursor.execute(
            "SELECT idmag FROM tb_magasin WHERE designationmag=%s LIMIT 1",
            (designationmag,),
        )
        result = cursor.fetchone()
        if not result:
            messagebox.showerror("Erreur", f"Magasin « {designationmag} » introuvable.")
            return
        idmag = result[0]

        try:
            session_path = get_session_path()
            with open(session_path, 'r', encoding='utf-8') as f:
                session = json.load(f)
            iduser = session.get('user_id')
            if not iduser:
                messagebox.showerror("Erreur", "Utilisateur non identifié.")
                return
        except Exception as e:
            messagebox.showerror("Erreur Session", str(e))
            return

        cursor.execute(
            "INSERT INTO tb_sortie (refsortie, iduser, description, deleted) "
            "VALUES (%s,%s,%s,0) RETURNING id",
            (ref_sortie, iduser, None),
        )
        idsortie = cursor.fetchone()[0]

        for d in self.detail_sortie:
            cursor.execute(
                "INSERT INTO tb_sortiedetail (idsortie, idmag, idarticle, idunite, qtsortie, motif) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (idsortie, d['idmag'], d['idarticle'], d['idunite'],
                 d['qtsortie'], d.get('motif')),
            )

        conn.commit()
        messagebox.showinfo("Succès", f"Sortie N°{ref_sortie} enregistrée.")
        self.derniere_idsortie_enregistree = idsortie
        self.generer_pdf_sortie_paysage(ref_sortie, idsortie)
        self.reset_form()

    def _enregistrer_consommation_ci(self, cursor, conn, ref_sortie, date_sortie,
                                     designationmag, montant_total):
        """
        Enregistre une Consommation Interne dans tb_consommationinterne + tb_consommationinterne_details.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        try:
            session_path = get_session_path()
            with open(session_path, 'r', encoding='utf-8') as f:
                session = json.load(f)
            iduser = session.get('user_id')
            if not iduser:
                messagebox.showerror("Erreur", "Utilisateur non identifié.")
                return
        except Exception as e:
            messagebox.showerror("Erreur Session", str(e))
            return

        cursor.execute(
            "INSERT INTO tb_consommationinterne "
            "(refconsommation, iduser, observation, valeur_totale) "
            "VALUES (%s,%s,%s,%s) RETURNING id",
            (ref_sortie, iduser, None, montant_total),
        )
        idconsommation = cursor.fetchone()[0]

        for d in self.detail_sortie:
            cursor.execute(
                "INSERT INTO tb_consommationinterne_details "
                "(idconsommation, idarticle, idunite, idmag, qtconsomme, prixunit, observation) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (idconsommation, d['idarticle'], d['idunite'], d['idmag'],
                 d['qtsortie'], d.get('prix_unitaire', 0), d.get('motif')),
            )

        conn.commit()
        messagebox.showinfo("Succès", f"Consommation N°{ref_sortie} enregistrée.")
        self.generer_pdf_consommation_interne_paysage(ref_sortie, idconsommation)
        self.reset_form()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 10 — RÉINITIALISATION DU FORMULAIRE
    # ══════════════════════════════════════════════════════════════════════════

    def reset_form(self, reset_imprimer: bool = True):
        """Réinitialise complètement le formulaire."""
        self.detail_sortie            = []
        self.article_selectionne      = None
        self.index_ligne_selectionnee = None
        self.mode_modification        = False
        self.idsortie_charge          = None

        self.entry_date_sortie.delete(0, "end")
        self.entry_date_sortie.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.entry_motif.delete(0, "end")

        self.charger_magasins()
        self.generer_reference()
        self.reset_detail_form()

        if self.tree_details:
            for item in self.tree_details.get_children():
                self.tree_details.delete(item)

        self.btn_enregistrer.configure(state="normal", text="💾 Enregistrer la Sortie")

        if reset_imprimer:
            self.btn_imprimer.configure(state="disabled")
            self.btn_imprimer.grid_remove()
            self.derniere_idsortie_enregistree = None

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 11 — IMPRESSION PDF
    # ══════════════════════════════════════════════════════════════════════════

    def nouveau_bon_sortie(self):
        """Réinitialise pour un nouveau bon de sortie."""
        if messagebox.askyesno(
            "Nouveau Bon de Sortie",
            "Créer un nouveau bon de sortie ?\nToutes les données non enregistrées seront perdues.",
        ):
            self.reset_form(reset_imprimer=True)
            messagebox.showinfo("Nouveau BS", "Formulaire réinitialisé.")

    def open_impression_dialogue(self):
        """Dialogue de choix du format d'impression."""
        if self.derniere_idsortie_enregistree is None:
            messagebox.showwarning("Attention", "ID de sortie introuvable.")
            return

        dialogue = simpledialog.askstring(
            "Format d'Impression",
            "Format d'impression ?\nEntrez « A5 » ou « 80mm ».",
            parent=self,
        )
        if not dialogue:
            return
        if dialogue.lower() == 'a5':
            self.imprimer_bon_sortie(self.derniere_idsortie_enregistree, format='A5')
        elif dialogue.lower() == '80mm':
            self.imprimer_bon_sortie(self.derniere_idsortie_enregistree, format='80mm')
        else:
            messagebox.showwarning("Format inconnu", "Choisissez « A5 » ou « 80mm ».")

    def open_file(self, filename):
        """Ouvre un fichier avec l'application par défaut du système."""
        try:
            if os.name == 'nt':
                os.startfile(filename)
            elif sys.platform == 'darwin':
                subprocess.call(['open', filename])
            else:
                subprocess.call(['xdg-open', filename])
        except Exception:
            pass

    def generer_pdf_sortie_paysage(self, ref_sortie: str, idsortie: int):
        """
        Génère un PDF A5 pour le BON DE SORTIE via EtatPDFMouvements.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        try:
            filename = f"BonSortie_{ref_sortie.replace('-','_')}.pdf"

            username = "Utilisateur"
            conn = self.connect_db()
            if conn:
                try:
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT username FROM tb_users WHERE iduser=%s",
                        (self.id_user_connecte,),
                    )
                    row = cur.fetchone()
                    if row:
                        username = row[0]
                    cur.close()
                except Exception:
                    pass
                finally:
                    conn.close()

            columns = ("Code", "Désignation", "Unité", "Quantité", "Magasin", "Motif")
            rows = [
                (str(d.get('code_article', '')), str(d.get('nom_article', '')),
                 str(d.get('nom_unite', '')), d.get('qtsortie', 0) or 0,
                 str(d.get('designationmag', '')), str(d.get('motif', '')))
                for d in self.detail_sortie
            ]
            table_data = (columns, rows)

            try:
                from EtatsPDF_Mouvements import EtatPDFMouvements
                etat = EtatPDFMouvements()
                try: etat.connect_db()
                except Exception: pass

                result = etat._build_pdf_a5(
                    output_path=filename,
                    titre_entete="BON DE SORTIE",
                    reference=ref_sortie,
                    date_operation=datetime.now().strftime('%d/%m/%Y'),
                    magasin=self.combo_magasin.get() if hasattr(self, 'combo_magasin') else '',
                    operateur=username,
                    table_data=table_data,
                    description="",
                    responsable_1="Le Magasinier",
                    responsable_2="Le Contrôleur",
                )
                try: etat.close_db()
                except Exception: pass

                if result and sys.platform == 'win32':
                    try: os.startfile(filename)
                    except Exception: pass

                return result

            except Exception as e:
                print(f"Erreur _build_pdf_a5 (BS): {e}")
                traceback.print_exc()
                messagebox.showerror("Erreur PDF", str(e))
                return None

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur PDF Sortie : {e}")
            return None

    def generer_pdf_consommation_interne_paysage(self, ref_sortie: str, idsortie: int):
        """
        Génère un PDF A5 pour la CONSOMMATION INTERNE via EtatPDFMouvements.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        try:
            filename = f"ConsommationInterne_{ref_sortie.replace('-','_')}.pdf"

            username = "Utilisateur"
            conn = self.connect_db()
            if conn:
                try:
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT username FROM tb_users WHERE iduser=%s",
                        (self.id_user_connecte,),
                    )
                    row = cur.fetchone()
                    if row:
                        username = row[0]
                    cur.close()
                except Exception:
                    pass
                finally:
                    conn.close()

            columns = ("Code", "Désignation", "Unité", "Magasin", "Quantité", "P.U.", "Montant", "Observation")
            rows = []
            for d in self.detail_sortie:
                qte     = d.get('qtsortie', 0) or 0
                pu      = d.get('prix_unitaire', 0) or 0
                montant = d.get('montant_total', qte * pu)
                rows.append((
                    str(d.get('code_article', '')), str(d.get('nom_article', '')),
                    str(d.get('nom_unite', '')), str(d.get('designationmag', '')),
                    qte, pu, montant, str(d.get('motif', '')),
                ))
            table_data = (columns, rows)

            try:
                from EtatsPDF_Mouvements import EtatPDFMouvements
                etat = EtatPDFMouvements()
                try: etat.connect_db()
                except Exception: pass

                result = etat._build_pdf_a5(
                    output_path=filename,
                    titre_entete="CONSOMMATION INTERNE",
                    reference=ref_sortie,
                    date_operation=datetime.now().strftime('%d/%m/%Y'),
                    magasin=self.combo_magasin.get() if hasattr(self, 'combo_magasin') else '',
                    operateur=username,
                    table_data=table_data,
                    description="",
                    responsable_1="Le Magasinier",
                    responsable_2="Le Contrôleur",
                )
                try: etat.close_db()
                except Exception: pass

                if result and sys.platform == 'win32':
                    try: os.startfile(filename)
                    except Exception: pass

                return result

            except Exception as e:
                print(f"Erreur _build_pdf_a5 (CI): {e}")
                traceback.print_exc()
                messagebox.showerror("Erreur PDF", str(e))
                return None

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur PDF CI : {e}")
            return None

    def _generer_pdf_consommation_ci(self, ref_sortie, date_sortie, designationmag,
                                     motif_sortie, montant_total):
        """Génère un PDF de consommation interne (méthode legacy conservée)."""
        try:
            etat_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "Etats Impression",
            )
            os.makedirs(etat_dir, exist_ok=True)

            pdf_filename = (
                f"{ref_sortie.replace('-','_')}_Consommation_"
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )
            pdf_path = os.path.join(etat_dir, pdf_filename)
            doc = SimpleDocTemplate(
                pdf_path, pagesize=landscape(A5),
                rightMargin=10, leftMargin=10, topMargin=10, bottomMargin=10,
            )
            story  = []
            styles = getSampleStyleSheet()

            from reportlab.lib.enums import TA_CENTER
            title_style = styles['Heading1']
            title_style.fontSize  = 14
            title_style.alignment = TA_CENTER
            story.append(Paragraph("CONSOMMATION INTERNE", title_style))

            info_data = [
                ["Référence:", ref_sortie],
                ["Date:", date_sortie.strftime("%d/%m/%Y")],
                ["Magasin:", designationmag],
                ["Motif:", motif_sortie],
                ["Valeur Totale:", f"{self.formater_nombre(montant_total)} Ar"],
            ]
            info_table = Table(info_data, colWidths=[80, 200])
            info_table.setStyle(TableStyle([
                ('BACKGROUND',   (0, 0), (0, -1), colors.lightgrey),
                ('FONTNAME',     (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE',     (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING',(0, 0), (-1, -1), 5),
                ('GRID',         (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(info_table)
            story.append(Spacer(1, 10))

            art_data = [["Code", "Désignation", "Unité", "Quantité", "P.U.", "Montant"]]
            for d in self.detail_sortie:
                art_data.append([
                    d.get('code_article', ''), d.get('nom_article', ''),
                    d.get('nom_unite', ''),
                    self.formater_nombre(d.get('qtsortie', 0)),
                    self.formater_nombre(d.get('prix_unitaire', 0)),
                    self.formater_nombre(d.get('montant_total', 0)),
                ])

            art_table = Table(art_data, colWidths=[50, 110, 40, 50, 50, 65])
            art_table.setStyle(TableStyle([
                ('BACKGROUND',   (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR',    (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME',     (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE',     (0, 0), (-1, -1), 8),
                ('GRID',         (0, 0), (-1, -1), 0.5, colors.black),
                ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            story.append(art_table)

            doc.build(story)
            messagebox.showinfo("PDF Généré", f"Sauvegardé : {pdf_filename}")

        except Exception as e:
            messagebox.showerror("Erreur PDF", str(e))

    def get_data_bon_sortie(self, idsortie: int) -> Optional[Dict[str, Any]]:
        """
        Récupère les données d'un bon de sortie pour l'impression.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        conn = self.connect_db()
        if not conn:
            return None

        data = {
            'societe': self.infos_societe,
            'sortie': None, 'utilisateur': None, 'details': [],
        }

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT s.refsortie, s.dateregistre, s.description,
                       u.nomuser, u.prenomuser
                FROM tb_sortie s
                INNER JOIN tb_users u ON s.iduser=u.iduser
                WHERE s.id=%s
                """,
                (idsortie,),
            )
            row = cursor.fetchone()
            if not row:
                messagebox.showerror("Erreur", "Bon de Sortie introuvable.")
                return None

            data['sortie'] = {
                'refsortie':     row[0],
                'dateregistre':  row[1].strftime("%d/%m/%Y"),
                'description':   row[2],
            }
            data['utilisateur'] = {'nomuser': row[3], 'prenomuser': row[4]}

            cursor.execute(
                """
                SELECT u.codearticle, a.designation, u.designationunite,
                       sd.qtsortie, m.designationmag, sd.motif
                FROM tb_sortiedetail sd
                INNER JOIN tb_article a ON sd.idarticle=a.idarticle
                INNER JOIN tb_unite   u ON sd.idunite=u.idunite
                INNER JOIN tb_magasin m ON sd.idmag=m.idmag
                WHERE sd.idsortie=%s ORDER BY a.designation
                """,
                (idsortie,),
            )
            data['details'] = cursor.fetchall()
            return data

        except Exception as e:
            messagebox.showerror("Erreur", str(e))
            return None
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()

    def imprimer_bon_sortie(self, idsortie: int, format: str):
        """
        Lance l'impression d'un bon de sortie au format A5 ou 80mm.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        data = self.get_data_bon_sortie(idsortie)
        if not data:
            return

        try:
            ref_sortie  = data['sortie']['refsortie']
            project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            etats_dir   = os.path.join(project_dir, "Etats Impression")
            os.makedirs(etats_dir, exist_ok=True)

            if format.lower() == 'a5':
                filename = f"BS_{ref_sortie.replace('-','_')}_A5.pdf"
                self.generer_pdf_a5(data, filename)
                pdf_path = os.path.join(etats_dir, filename)
                messagebox.showinfo("Impression A5", f"PDF généré : {pdf_path}")
                self.open_file(pdf_path)
            elif format.lower() == '80mm':
                filename = f"BS_{ref_sortie.replace('-','_')}_80mm.txt"
                txt_path = os.path.join(etats_dir, filename)
                self.generate_ticket_80mm(data, txt_path)
                messagebox.showinfo("Impression 80mm", f"Ticket généré : {txt_path}")
                self.open_file(txt_path)

        except Exception as e:
            messagebox.showerror("Erreur Génération", str(e))

    def generer_pdf_a5(self, data, filename):
        """
        Génère un PDF A5 Portrait pour le bon de sortie.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        try:
            doc = SimpleDocTemplate(
                filename, pagesize=A5,
                leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20,
            )
            styles   = getSampleStyleSheet()
            elements = []

            societe       = data['societe']
            utilisateur   = data['utilisateur']
            sortie_info   = data['sortie']

            style_hdr = styles['Normal']
            style_hdr.fontSize  = 8
            style_hdr.alignment = 1

            elements.append(Paragraph(f"<b>{societe.get('nomsociete','SOCIÉTÉ')}</b>", styles['Heading4']))
            elements.append(Paragraph(societe.get('adressesociete','N/A'), style_hdr))
            elements.append(Paragraph(f"Tél : {societe.get('contactsociete','N/A')}", style_hdr))
            elements.append(Spacer(1, 15))

            style_titre            = styles['Heading3']
            style_titre.alignment  = 1
            elements.append(Paragraph(f"<u>BON DE SORTIE N°{sortie_info['refsortie']}</u>", style_titre))
            elements.append(Paragraph(f"Date : {sortie_info['dateregistre']}", style_hdr))
            elements.append(Spacer(1, 8))

            style_user           = styles['Normal']
            style_user.fontSize  = 9
            style_user.alignment = 1
            nom = f"{utilisateur.get('prenomuser','')} {utilisateur.get('nomuser','')}".strip()
            elements.append(Paragraph(f"<i>Établi par : {nom}</i>", style_user))
            elements.append(Spacer(1, 10))

            table_data = [['Code', 'Désignation', 'Unité', 'Qté', 'Magasin', 'Motif']]
            for item in data['details']:
                table_data.append([
                    item[0],
                    Paragraph(item[1], styles['Normal']),
                    item[2],
                    self.formater_nombre(item[3]),
                    item[4],
                    item[5] or "",
                ])

            table = Table(table_data, colWidths=[45, 110, 40, 40, 70, 75])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR',  (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN',      (3, 1), (3, -1),  'RIGHT'),
                ('FONTSIZE',   (0, 0), (-1, -1),  7),
                ('GRID',       (0, 0), (-1, -1),  0.5, colors.black),
                ('VALIGN',     (0, 0), (-1, -1),  'MIDDLE'),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 20))

            sig_table = Table([['Le Magasinier', 'Le Réceptionnaire']], colWidths=[190, 190])
            sig_table.setStyle(TableStyle([
                ('ALIGN',    (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1),  9),
            ]))
            elements.append(sig_table)

            doc.build(elements)

            try:
                if sys.platform == 'win32':
                    os.startfile(filename, "print")
                else:
                    subprocess.Popen(['lp', filename])
            except Exception:
                pass

            messagebox.showinfo("Succès", f"PDF généré : {filename}")
            self.open_file(filename)

        except Exception as e:
            messagebox.showerror("Erreur PDF", str(e))

    def generate_ticket_80mm(self, data: Dict[str, Any], filename: str):
        """
        Génère un ticket de caisse 80mm (fichier texte brut).
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        societe     = data['societe']
        sortie      = data['sortie']
        utilisateur = data['utilisateur']
        details     = data['details']

        MAX_WIDTH = 40

        def center(text): return text.center(MAX_WIDTH)
        def line():       return "-" * MAX_WIDTH

        def format_detail_line(designation, qte, unite):
            qte_str = self.formater_nombre(qte)
            space   = MAX_WIDTH - len(qte_str) - len(unite) - 3
            desig   = designation[:space].ljust(space)
            return f"{desig} {qte_str} {unite}"

        content = [
            center("Informations Société"),
            f" {societe.get('nomsociete','N/A')}",
            societe.get('adressesociete','N/A'),
            societe.get('villesociete','N/A'),
            societe.get('contactsociete','N/A'),
            line(),
            center(f"NIF: {societe.get('nifsociete','N/A')}"),
            center(f"STAT: {societe.get('statsociete','N/A')}"),
            center(f"CIF: {societe.get('cifsociete','N/A')}"),
            f"Réf BS: {sortie['refsortie']}",
            f"Date: {sortie['dateregistre']}",
            f"Motif: {sortie['description']}",
            f"Utilisateur: {utilisateur['prenomuser']} {utilisateur['nomuser']}",
            line(),
            "DESIGNATION QTE UNITE",
            line(),
        ]

        for code, designation, unite, qte, magasin, motif in details:
            content.append(format_detail_line(designation, qte, unite))

        content += [
            line(),
            "\n\n\n",
            center("Signature"),
            "\n\n\n",
            center("Merci de votre collaboration"),
        ]

        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))


# ==============================================================================
# POINT D'ENTRÉE AUTONOME (test unitaire)
# ==============================================================================

if __name__ == "__main__":
    USER_ID_TEST = 1
    app = ctk.CTk()
    app.title("iJeery — Gestion des Sorties (test)")
    app.geometry("1300x800")

    page_sortie = PageSortie(app, USER_ID_TEST)
    page_sortie.pack(fill="both", expand=True)

    app.mainloop()