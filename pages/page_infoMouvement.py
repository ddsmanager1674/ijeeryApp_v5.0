import customtkinter as ctk
from tkinter import messagebox, ttk
import psycopg2
import json
import os
import sys
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any
from resource_utils import get_config_path, safe_file_read
from app_theme import Colors, Fonts

# Imports pour génération PDF
from reportlab.lib.pagesizes import A5, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageTemplate, Frame
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas


# Importation des pages existantes
from pages.page_CmdFrs import PageCommandeFrs
from pages.page_livrFrs import PageBonReception
from pages.page_transfert import PageTransfert
from pages.page_sortie import PageSortie
from pages.page_SuiviCommande import PageSuiviCommande
from pages.page_transporteur import PageTransporteur
from pages.page_infosCharges import PageInfosCharges

# ============ CLASSE CHANGEMENT D'ARTICLES ============

# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║             iJeery — pages/page_changement_article.py                       ║
║             Gestion des Changements d'Articles (échange sortie / entrée)    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  REFONTE UI — Mars 2026                                                      ║
║  Structure cohérente avec page_venteParMsin / page_avoir / page_transfert : ║
║                                                                              ║
║    Row 0 — Bandeau en-tête (Réf | Date | 📂 Charger)                        ║
║    Row 1 — Panel SORTIE (rouge)                                             ║
║              ├─ Sous-bandeau : Titre 📤 | Magasin Sortie                    ║
║              ├─ Saisie : Article | 🔎 | Qté | Unité | ➕ | ✖                ║
║              ├─ Treeview Sortie (expansible)                                ║
║              └─ Bouton 🗑 Supprimer Ligne                                    ║
║    Row 2 — Panel ENTRÉE (bleu)                                              ║
║              ├─ Sous-bandeau : Titre 📥 | Magasin Entrée                    ║
║              ├─ Saisie : Article | 🔎 | Qté | Unité | ➕ | ✖                ║
║              ├─ Treeview Entrée (expansible)                                ║
║              └─ Bouton 🗑 Supprimer Ligne                                    ║
║    Row 3 — Note (pleine largeur)                                            ║
║    Row 4 — Barre d'actions (🖨 Imprimer | 💾 Enregistrer)                   ║
║                                                                              ║
║  Logique métier : 100% INCHANGÉE                                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""



ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


class PageChangementArticle(ctk.CTkFrame):
    """
    Page de gestion des changements d'articles.

    Architecture UI (cohérente avec les autres pages iJeery) :
    ┌────────────────────────────────────────────────────────────┐
    │ Row 0 — Réf (bold/readonly) | Date | 📂 Charger           │ card BG_CARD
    │ Row 1 — Panel SORTIE (accent DANGER)                       │
    │   📤 ARTICLES À CHANGER | Magasin Sortie                   │ hdr danger
    │   Article | 🔎 | Qté | Unité | ➕ | ✖ Annuler              │ card
    │   Treeview Sortie (expansible)                             │ card
    │   🗑 Supprimer Ligne                                        │
    │ Row 2 — Panel ENTRÉE (accent PRIMARY)                      │
    │   📥 ARTICLES REÇUS | Magasin Entrée                       │ hdr primary
    │   Article | 🔎 | Qté | Unité | ➕ | ✖ Annuler              │ card
    │   Treeview Entrée (expansible)                             │ card
    │   🗑 Supprimer Ligne                                        │
    │ Row 3 — Note pleine largeur                                │ card BG_CARD
    │ Row 4 — (espace) | 🖨 Imprimer | 💾 Enregistrer            │ BG_PAGE
    └────────────────────────────────────────────────────────────┘
    """

    # ── Constantes PDF (A5 Landscape) ────────────────────────────────────────
    PAGE_WIDTH, PAGE_HEIGHT = landscape(A5)
    MARGIN = 5 * mm

    COLOR_HEADER          = colors.HexColor("#034787")
    COLOR_BORDER          = colors.HexColor("#000000")
    COLOR_BG_HEADER       = colors.HexColor("#F5F5F5")
    COLOR_BG_TABLE_HEADER = colors.HexColor("#E8E8E8")
    COLOR_BG_FOOTER       = colors.HexColor("#F0F0F0")

    # ══════════════════════════════════════════════════════════════════════════
    def __init__(self, master, iduser: int, **kwargs):
        super().__init__(master, fg_color=Colors.BG_PAGE, **kwargs)

        self.iduser = iduser
        self.magasins: Dict[str, int] = {}
        self.idchg_charge              = None
        self.mode_modification         = False

        # Listes articles
        self.articles_sortie: list                    = []
        self.article_sortie_selectionne: Optional[dict] = None
        self.articles_entree: list                    = []
        self.article_entree_selectionne: Optional[dict] = None

        # ── Layout principal : 5 rows ─────────────────────────────────────────
        self.grid_columnconfigure(0, weight=1)
        for row, w in enumerate([0, 1, 1, 0, 0]):
            self.grid_rowconfigure(row, weight=w)

        # ── Construction ──────────────────────────────────────────────────────
        self._setup_ui()

        # ── Chargements initiaux ──────────────────────────────────────────────
        self.charger_magasins()
        self.generer_reference()

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
        except Exception as e:
            messagebox.showerror("Erreur de connexion", str(e))
            return None

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — CONSTRUCTION DE L'INTERFACE
    # ══════════════════════════════════════════════════════════════════════════

    def _setup_ui(self):
        """Point d'entrée UI — délègue à 5 sous-méthodes."""
        self._build_header_band()    # Row 0 — Réf / Date / Charger
        self._build_sortie_panel()   # Row 1 — Panel SORTIE
        self._build_entree_panel()   # Row 2 — Panel ENTRÉE
        self._build_note_band()      # Row 3 — Note
        self._build_actions_band()   # Row 4 — Boutons

    # ── Row 0 — Bandeau en-tête ───────────────────────────────────────────────

    def _build_header_band(self):
        """Card blanche (Row 0) : Référence | Date | 📂 Charger."""
        card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        card.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 2))
        for col in range(5):
            card.grid_columnconfigure(col, weight=1)

        lbl_kw   = dict(font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY, anchor="w")
        entry_kw = dict(
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            height=32, corner_radius=6,
        )

        # — Référence —
        ctk.CTkLabel(card, text="Référence", **lbl_kw).grid(
            row=0, column=0, padx=(10, 2), pady=(8, 0), sticky="w")
        self.entry_ref = ctk.CTkEntry(
            card, **entry_kw, font=Fonts.bold(12), state="readonly",
        )
        self.entry_ref.grid(row=1, column=0, padx=(10, 4), pady=(0, 8), sticky="ew")

        # — Date —
        ctk.CTkLabel(card, text="Date", **lbl_kw).grid(
            row=0, column=1, padx=4, pady=(8, 0), sticky="w")
        self.entry_date = ctk.CTkEntry(card, **entry_kw, font=Fonts.input(12))
        self.entry_date.grid(row=1, column=1, padx=4, pady=(0, 8), sticky="ew")
        self.entry_date.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.entry_date.configure(state="readonly")

        # — Espace élastique —
        card.grid_columnconfigure(2, weight=3)

        # — Bouton Charger —
        ctk.CTkLabel(card, text=" ", **lbl_kw).grid(row=0, column=3, padx=4, pady=(8, 0))
        ctk.CTkButton(
            card, text="📂 Charger Changement", height=32,
            font=Fonts.bold(11),
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            corner_radius=6, command=self.ouvrir_recherche_changement,
        ).grid(row=1, column=3, padx=(4, 10), pady=(0, 8), sticky="ew")

    # ── Row 1 — Panel SORTIE ──────────────────────────────────────────────────

    def _build_sortie_panel(self):
        """
        Panel accentué rouge (Row 1) :
          - En-tête : titre 📤 + ComboBox Magasin Sortie
          - Saisie article sortie
          - Treeview sortie (expansible)
          - Bouton 🗑 Supprimer ligne
        """
        panel = ctk.CTkFrame(
            self, fg_color=Colors.BG_CARD, corner_radius=0,
        )
        panel.grid(row=1, column=0, sticky="nsew", padx=0, pady=(0, 2))
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(2, weight=1)   # Treeview expansible

        # ── Sous-bandeau titre + magasin ─────────────────────────────────────
        hdr = ctk.CTkFrame(panel, fg_color=Colors.WARNING, corner_radius=0, height=38)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hdr, text="📤  ARTICLES À CHANGER  —  SORTIE",
            font=Fonts.bold(12), text_color=Colors.TEXT_ON_DARK,
        ).grid(row=0, column=0, padx=10, pady=0, sticky="w")

        mag_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        mag_frame.grid(row=0, column=2, padx=(0, 8), pady=0, sticky="e")
        ctk.CTkLabel(
            mag_frame, text="Magasin :",
            font=Fonts.label(11), text_color=Colors.TEXT_ON_DARK,
        ).pack(side="left", padx=(0, 4))
        self.combo_mag_sortie = ctk.CTkComboBox(
            mag_frame, width=200, height=28,
            font=Fonts.input(11), fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER, button_color=Colors.MIDNIGHT,
            dropdown_fg_color=Colors.BG_CARD,
        )
        self.combo_mag_sortie.pack(side="left")

        # ── Saisie article sortie ─────────────────────────────────────────────
        saisie = ctk.CTkFrame(panel, fg_color=Colors.BG_PAGE, corner_radius=0)
        saisie.grid(row=1, column=0, sticky="ew", padx=0, pady=(0, 1))
        for col in range(6):
            saisie.grid_columnconfigure(col, weight=1)

        lbl_kw   = dict(font=Fonts.label(10), text_color=Colors.TEXT_SECONDARY, anchor="w")
        entry_kw = dict(
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            height=30, corner_radius=6, font=Fonts.input(11),
        )

        # Article
        ctk.CTkLabel(saisie, text="Article", **lbl_kw).grid(
            row=0, column=0, padx=(8, 2), pady=(4, 0), sticky="w")
        self.entry_article_sortie = ctk.CTkEntry(
            saisie, **entry_kw, placeholder_text="Sélectionner…",
        )
        self.entry_article_sortie.grid(row=1, column=0, padx=(8, 3), pady=(0, 6), sticky="ew")

        # Rechercher
        ctk.CTkLabel(saisie, text=" ", **lbl_kw).grid(row=0, column=1, padx=3)
        ctk.CTkButton(
            saisie, text="🔎 Rechercher", height=30,
            font=Fonts.bold(10),
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            corner_radius=6, command=self.ouvrir_recherche_article_sortie,
        ).grid(row=1, column=1, padx=3, pady=(0, 6), sticky="ew")

        # Quantité
        ctk.CTkLabel(saisie, text="Quantité", **lbl_kw).grid(
            row=0, column=2, padx=3, pady=(4, 0), sticky="w")
        self.entry_qty_sortie = ctk.CTkEntry(saisie, **entry_kw, placeholder_text="0")
        self.entry_qty_sortie.grid(row=1, column=2, padx=3, pady=(0, 6), sticky="ew")

        # Unité (readonly)
        ctk.CTkLabel(saisie, text="Unité", **lbl_kw).grid(
            row=0, column=3, padx=3, pady=(4, 0), sticky="w")
        self.entry_unite_sortie = ctk.CTkEntry(saisie, **entry_kw, state="readonly")
        self.entry_unite_sortie.grid(row=1, column=3, padx=3, pady=(0, 6), sticky="ew")

        # Ajouter
        ctk.CTkLabel(saisie, text=" ", **lbl_kw).grid(row=0, column=4, padx=3)
        self.btn_ajouter_sortie = ctk.CTkButton(
            saisie, text="+ Ajouter", height=30,
            font=Fonts.bold(11),
            fg_color=Colors.SUCCESS_DARK, hover_color=Colors.INFO_DARK,
            corner_radius=6, command=self.ajouter_article_sortie,
        )
        self.btn_ajouter_sortie.grid(row=1, column=4, padx=3, pady=(0, 6), sticky="ew")

        # Annuler
        self.btn_annuler_sortie = ctk.CTkButton(
            saisie, text="✖ Annuler", height=30,
            font=Fonts.bold(10),
            fg_color=Colors.TEXT_MUTED, hover_color=Colors.TEXT_SECONDARY,
            corner_radius=6, command=self.annuler_sortie,
        )
        self.btn_annuler_sortie.grid(row=1, column=5, padx=(3, 8), pady=(0, 6), sticky="ew")

        # ── Treeview sortie ───────────────────────────────────────────────────
        tree_container = ctk.CTkFrame(panel, fg_color=Colors.BG_CARD, corner_radius=0)
        tree_container.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)
        tree_container.grid_columnconfigure(0, weight=1)
        tree_container.grid_rowconfigure(0, weight=1)

        self._apply_treeview_style("Sortie")
        colonnes_sortie = ("Code", "Désignation", "Unité", "Magasin", "Quantité")
        self.tree_sortie = ttk.Treeview(
            tree_container, columns=colonnes_sortie,
            show="headings", height=4, style="Sortie.Treeview",
        )
        self._configure_table_alternating_colors(self.tree_sortie)
        for col in colonnes_sortie:
            self.tree_sortie.heading(col, text=col)
            self.tree_sortie.column(
                col,
                width=280 if col == "Désignation" else 110,
                anchor="w" if col in ("Code", "Désignation", "Unité", "Magasin") else "e",
            )

        sb_sortie = ctk.CTkScrollbar(tree_container, command=self.tree_sortie.yview)
        self.tree_sortie.configure(yscrollcommand=sb_sortie.set)
        self.tree_sortie.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=4)
        sb_sortie.grid(row=0, column=1, sticky="ns", padx=(0, 6), pady=4)

        # ── Bouton Supprimer sortie ───────────────────────────────────────────
        ctk.CTkButton(
            panel, text="🗑  Supprimer Ligne sélectionnée", height=32,
            font=Fonts.bold(11),
            fg_color=Colors.DANGER, hover_color=Colors.DANGER_DARK,
            corner_radius=0, command=self.supprimer_article_sortie,
        ).grid(row=3, column=0, sticky="ew", padx=0, pady=(1, 0))

    # ── Row 2 — Panel ENTRÉE ──────────────────────────────────────────────────

    def _build_entree_panel(self):
        """
        Panel accentué bleu (Row 2) :
          - En-tête : titre 📥 + ComboBox Magasin Entrée
          - Saisie article entrée
          - Treeview entrée (expansible)
          - Bouton 🗑 Supprimer ligne
        """
        panel = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        panel.grid(row=2, column=0, sticky="nsew", padx=0, pady=(0, 2))
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(2, weight=1)

        # ── Sous-bandeau titre + magasin ─────────────────────────────────────
        hdr = ctk.CTkFrame(panel, fg_color=Colors.PRIMARY, corner_radius=0, height=38)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hdr, text="📥  ARTICLES REÇUS  —  ENTRÉE",
            font=Fonts.bold(12), text_color=Colors.TEXT_ON_DARK,
        ).grid(row=0, column=0, padx=10, pady=0, sticky="w")

        mag_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        mag_frame.grid(row=0, column=2, padx=(0, 8), pady=0, sticky="e")
        ctk.CTkLabel(
            mag_frame, text="Magasin :",
            font=Fonts.label(11), text_color=Colors.TEXT_ON_DARK,
        ).pack(side="left", padx=(0, 4))
        self.combo_mag_entree = ctk.CTkComboBox(
            mag_frame, width=200, height=28,
            font=Fonts.input(11), fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER, button_color=Colors.MIDNIGHT,
            dropdown_fg_color=Colors.BG_CARD,
        )
        self.combo_mag_entree.pack(side="left")

        # ── Saisie article entrée ─────────────────────────────────────────────
        saisie = ctk.CTkFrame(panel, fg_color=Colors.BG_PAGE, corner_radius=0)
        saisie.grid(row=1, column=0, sticky="ew", padx=0, pady=(0, 1))
        for col in range(6):
            saisie.grid_columnconfigure(col, weight=1)

        lbl_kw   = dict(font=Fonts.label(10), text_color=Colors.TEXT_SECONDARY, anchor="w")
        entry_kw = dict(
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            height=30, corner_radius=6, font=Fonts.input(11),
        )

        ctk.CTkLabel(saisie, text="Article", **lbl_kw).grid(
            row=0, column=0, padx=(8, 2), pady=(4, 0), sticky="w")
        self.entry_article_entree = ctk.CTkEntry(
            saisie, **entry_kw, placeholder_text="Sélectionner…",
        )
        self.entry_article_entree.grid(row=1, column=0, padx=(8, 3), pady=(0, 6), sticky="ew")

        ctk.CTkLabel(saisie, text=" ", **lbl_kw).grid(row=0, column=1, padx=3)
        ctk.CTkButton(
            saisie, text="🔎 Rechercher", height=30,
            font=Fonts.bold(10),
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            corner_radius=6, command=self.ouvrir_recherche_article_entree,
        ).grid(row=1, column=1, padx=3, pady=(0, 6), sticky="ew")

        ctk.CTkLabel(saisie, text="Quantité", **lbl_kw).grid(
            row=0, column=2, padx=3, pady=(4, 0), sticky="w")
        self.entry_qty_entree = ctk.CTkEntry(saisie, **entry_kw, placeholder_text="0")
        self.entry_qty_entree.grid(row=1, column=2, padx=3, pady=(0, 6), sticky="ew")

        ctk.CTkLabel(saisie, text="Unité", **lbl_kw).grid(
            row=0, column=3, padx=3, pady=(4, 0), sticky="w")
        self.entry_unite_entree = ctk.CTkEntry(saisie, **entry_kw, state="readonly")
        self.entry_unite_entree.grid(row=1, column=3, padx=3, pady=(0, 6), sticky="ew")

        ctk.CTkLabel(saisie, text=" ", **lbl_kw).grid(row=0, column=4, padx=3)
        self.btn_ajouter_entree = ctk.CTkButton(
            saisie, text="+ Ajouter", height=30,
            font=Fonts.bold(11),
            fg_color=Colors.SUCCESS_DARK, hover_color=Colors.INFO_DARK,
            corner_radius=6, command=self.ajouter_article_entree,
        )
        self.btn_ajouter_entree.grid(row=1, column=4, padx=3, pady=(0, 6), sticky="ew")

        self.btn_annuler_entree = ctk.CTkButton(
            saisie, text="✖ Annuler", height=30,
            font=Fonts.bold(10),
            fg_color=Colors.TEXT_MUTED, hover_color=Colors.TEXT_SECONDARY,
            corner_radius=6, command=self.annuler_entree,
        )
        self.btn_annuler_entree.grid(row=1, column=5, padx=(3, 8), pady=(0, 6), sticky="ew")

        # ── Treeview entrée ───────────────────────────────────────────────────
        tree_container = ctk.CTkFrame(panel, fg_color=Colors.BG_CARD, corner_radius=0)
        tree_container.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)
        tree_container.grid_columnconfigure(0, weight=1)
        tree_container.grid_rowconfigure(0, weight=1)

        self._apply_treeview_style("Entree")
        colonnes_entree = ("Code", "Désignation", "Unité", "Magasin", "Quantité")
        self.tree_entree = ttk.Treeview(
            tree_container, columns=colonnes_entree,
            show="headings", height=4, style="Entree.Treeview",
        )
        self._configure_table_alternating_colors(self.tree_entree)
        for col in colonnes_entree:
            self.tree_entree.heading(col, text=col)
            self.tree_entree.column(
                col,
                width=280 if col == "Désignation" else 110,
                anchor="w" if col in ("Code", "Désignation", "Unité", "Magasin") else "e",
            )

        sb_entree = ctk.CTkScrollbar(tree_container, command=self.tree_entree.yview)
        self.tree_entree.configure(yscrollcommand=sb_entree.set)
        self.tree_entree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=4)
        sb_entree.grid(row=0, column=1, sticky="ns", padx=(0, 6), pady=4)

        # ── Bouton Supprimer entrée ───────────────────────────────────────────
        ctk.CTkButton(
            panel, text="🗑  Supprimer Ligne sélectionnée", height=32,
            font=Fonts.bold(11),
            fg_color=Colors.DANGER, hover_color=Colors.DANGER_DARK,
            corner_radius=0, command=self.supprimer_article_entree,
        ).grid(row=3, column=0, sticky="ew", padx=0, pady=(1, 0))

    # ── Row 3 — Note ─────────────────────────────────────────────────────────

    def _build_note_band(self):
        """Card blanche (Row 3) : champ Note pleine largeur."""
        card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        card.grid(row=3, column=0, sticky="ew", padx=0, pady=(0, 2))
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card, text="📝 Note du changement",
            font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY,
        ).grid(row=0, column=0, padx=(10, 6), pady=8, sticky="w")

        self.entry_note = ctk.CTkEntry(
            card,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            height=32, corner_radius=6, font=Fonts.input(12),
            placeholder_text="Entrez une note (optionnel)…",
        )
        self.entry_note.grid(row=0, column=1, padx=(0, 10), pady=8, sticky="ew")

    # ── Row 4 — Barre d'actions ───────────────────────────────────────────────

    def _build_actions_band(self):
        """Frame BG_PAGE (Row 4) : 🖨 Imprimer | 💾 Enregistrer (alignés à droite)."""
        bar = ctk.CTkFrame(self, fg_color=Colors.BG_PAGE, corner_radius=0)
        bar.grid(row=4, column=0, sticky="ew", padx=0, pady=(2, 0))
        bar.grid_columnconfigure(0, weight=1)  # espace élastique à gauche

        ctk.CTkButton(
            bar, text="🖨  Imprimer", height=36,
            font=Fonts.bold(12),
            fg_color=Colors.PREMIUM, hover_color=Colors.PREMIUM_DARK,
            corner_radius=8, command=self.imprimer_changement,
        ).grid(row=0, column=1, padx=(0, 6), pady=6)

        ctk.CTkButton(
            bar, text="💾  Enregistrer le Changement", height=36,
            font=Fonts.bold(13),
            fg_color=Colors.SUCCESS_DARK, hover_color=Colors.INFO_DARK,
            corner_radius=8, command=self.enregistrer_changement,
        ).grid(row=0, column=2, padx=(0, 8), pady=6)

    # ── Helpers visuels Treeview ──────────────────────────────────────────────

    def _apply_treeview_style(self, name: str):
        """Crée un style TTK nommé <name>.Treeview avec le thème iJeery."""
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            f"{name}.Treeview",
            rowheight=22, font=('Segoe UI', 9),
            background=Colors.BG_CARD, foreground=Colors.TEXT_PRIMARY,
            fieldbackground=Colors.BG_CARD, borderwidth=0,
        )
        style.configure(
            f"{name}.Treeview.Heading",
            background=Colors.BG_HEADER, foreground=Colors.TEXT_ON_DARK,
            font=('Segoe UI', 9, 'bold'), relief="flat",
        )
        style.map(
            f"{name}.Treeview",
            background=[("selected", Colors.PRIMARY)],
            foreground=[("selected", Colors.TEXT_ON_DARK)],
        )

    def _configure_table_alternating_colors(self, tree):
        """Configure les tags pair/impair pour un tableau."""
        tree.tag_configure("row_even", background=Colors.BG_CARD)
        tree.tag_configure("row_odd",  background=Colors.BG_ROW_ALT)

    def _refresh_table_alternating_colors(self, tree):
        """Réapplique les couleurs alternées sur toutes les lignes."""
        for idx, item in enumerate(tree.get_children()):
            tree.item(item, tags=("row_even" if idx % 2 == 0 else "row_odd",))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3 — FORMATAGE
    # ══════════════════════════════════════════════════════════════════════════

    def formater_nombre(self, nombre) -> str:
        """Formate un nombre avec séparateur de milliers (1.000,00)."""
        try:
            nombre         = float(nombre)
            partie_entiere = int(nombre)
            partie_dec     = abs(nombre - partie_entiere)
            str_ent        = f"{partie_entiere:,}".replace(',', '.')
            str_dec        = f"{partie_dec:.2f}".split('.')[1]
            return f"{str_ent},{str_dec}"
        except Exception:
            return "0,00"

    def parser_nombre(self, texte) -> float:
        """Convertit un nombre formaté (1.000,00) en float."""
        try:
            return float(str(texte).replace('.', '').replace(',', '.'))
        except Exception:
            return 0.0

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 4 — CHARGEMENTS INITIAUX
    # ══════════════════════════════════════════════════════════════════════════

    def generer_reference(self):
        """
        Génère la référence au format AAAA-CHG-NNNNN.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            annee = datetime.now().year
            cursor.execute(
                "SELECT refchg FROM tb_changement "
                "WHERE refchg LIKE %s ORDER BY refchg DESC LIMIT 1",
                (f"{annee}-CHG-%",),
            )
            resultat = cursor.fetchone()

            if resultat:
                try:
                    nouveau_num = int(resultat[0].split('-')[-1]) + 1
                except ValueError:
                    nouveau_num = 1
            else:
                nouveau_num = 1

            reference = f"{annee}-CHG-{nouveau_num:05d}"
            self.entry_ref.configure(state="normal")
            self.entry_ref.delete(0, "end")
            self.entry_ref.insert(0, reference)
            self.entry_ref.configure(state="readonly")

        except Exception as e:
            messagebox.showerror("Erreur", f"Génération référence : {e}")
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()

    def charger_magasins(self):
        """
        Charge les magasins dans les deux ComboBox.
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
            magasins_rows = cursor.fetchall()
            self.magasins = {row[1]: row[0] for row in magasins_rows}
            noms          = list(self.magasins.keys())

            self.combo_mag_sortie.configure(values=noms)
            self.combo_mag_entree.configure(values=noms)

            if noms:
                idmag_defaut = None
                cursor.execute(
                    "SELECT idmag FROM tb_users WHERE iduser=%s LIMIT 1",
                    (self.iduser,),
                )
                row_user = cursor.fetchone()
                if row_user:
                    idmag_defaut = row_user[0]

                nom_defaut = next(
                    (nom for id_, nom in magasins_rows if id_ == idmag_defaut), None
                )
                defaut = nom_defaut if nom_defaut else noms[0]
                self.combo_mag_sortie.set(defaut)
                self.combo_mag_entree.set(defaut)

        except Exception as e:
            messagebox.showerror("Erreur", f"Chargement magasins : {e}")
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 5 — INFOS SOCIÉTÉ (pour PDF)
    # ══════════════════════════════════════════════════════════════════════════

    def _get_societe_info(self) -> Dict[str, str]:
        """
        Récupère les informations de la société depuis tb_infosociete.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        _default = {
            'nomsociete': 'IJEERY', 'adressesociete': 'Adresse Non Configurée',
            'villesociete': '', 'contactsociete': 'Contact: Non Configuré',
            'nifsociete': 'NIF: Non Configuré', 'statsociete': 'STAT: Non Configurée',
            'cifsociete': 'CIF: Non Configuré',
        }
        conn = self.connect_db()
        if not conn:
            return _default
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT nomsociete, villesociete, adressesociete, contactsociete, "
                "nifsociete, statsociete, cifsociete FROM tb_infosociete LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                return {
                    'nomsociete':     row[0] or 'IJEERY',
                    'villesociete':   row[1] or '',
                    'adressesociete': row[2] or 'Adresse Non Configurée',
                    'contactsociete': row[3] or 'Contact: Non Configuré',
                    'nifsociete':     row[4] or 'NIF: Non Configuré',
                    'statsociete':    row[5] or 'STAT: Non Configurée',
                    'cifsociete':     row[6] or 'CIF: Non Configuré',
                }
        except Exception as e:
            print(f"Erreur infos société : {e}")
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()
        return _default

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 6 — CALCUL STOCK
    # ══════════════════════════════════════════════════════════════════════════

    def calculer_stock_article(self, idarticle, idunite, idmag) -> float:
        """
        Calcule le stock consolidé : Réceptions + Transferts IN + Inventaires
        + Avoirs - Ventes - Sorties - Transferts OUT.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        conn = self.connect_db()
        if not conn:
            return 0

        try:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT codearticle FROM tb_unite WHERE idarticle=%s AND idunite=%s",
                (idarticle, idunite),
            )
            result = cursor.fetchone()
            codearticle = result[0] if result else None
            if not codearticle:
                return 0

            def qry(sql, params):
                cursor.execute(sql, params)
                return cursor.fetchone()[0] or 0

            receptions   = qry("SELECT COALESCE(SUM(qtlivrefrs),0) FROM tb_livraisonfrs WHERE idarticle=%s AND idunite=%s AND deleted=0 AND idmag=%s", (idarticle, idunite, idmag))
            ventes        = qry("SELECT COALESCE(SUM(qtvente),0) FROM tb_ventedetail WHERE idarticle=%s AND idunite=%s AND deleted=0 AND idmag=%s", (idarticle, idunite, idmag))
            sorties       = qry("SELECT COALESCE(SUM(qtsortie),0) FROM tb_sortiedetail WHERE idarticle=%s AND idunite=%s AND idmag=%s", (idarticle, idunite, idmag))
            transferts_in = qry("SELECT COALESCE(SUM(qttransfert),0) FROM tb_transfertdetail WHERE idarticle=%s AND idunite=%s AND deleted=0 AND idmagentree=%s", (idarticle, idunite, idmag))
            transferts_out= qry("SELECT COALESCE(SUM(qttransfert),0) FROM tb_transfertdetail WHERE idarticle=%s AND idunite=%s AND deleted=0 AND idmagsortie=%s", (idarticle, idunite, idmag))
            inventaires   = qry("SELECT COALESCE(SUM(qtinventaire),0) FROM tb_inventaire WHERE codearticle=%s AND idmag=%s", (codearticle, idmag))
            avoirs        = qry("SELECT COALESCE(SUM(ad.qtavoir),0) FROM tb_avoirdetail ad INNER JOIN tb_avoir a ON ad.idavoir=a.id WHERE ad.idarticle=%s AND ad.idunite=%s AND ad.idmag=%s AND a.deleted=0 AND ad.deleted=0", (idarticle, idunite, idmag))

            stock = (receptions + transferts_in + inventaires + avoirs) - (ventes + sorties + transferts_out)
            return max(0, stock)

        except Exception as e:
            print(f"Erreur calcul stock : {e}")
            return 0
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 7 — RECHERCHE D'ARTICLE
    # ══════════════════════════════════════════════════════════════════════════

    def ouvrir_recherche_article_sortie(self):
        """Ouvre la fenêtre de recherche pour SORTIE."""
        self.open_recherche_article("sortie")

    def ouvrir_recherche_article_entree(self):
        """Ouvre la fenêtre de recherche pour ENTRÉE."""
        self.open_recherche_article("entree")

    def open_recherche_article(self, type_mouvement: str):
        """
        Fenêtre modale de recherche d'article avec stock CTE consolidé.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        fen = ctk.CTkToplevel(self)
        fen.title("Rechercher un article")
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
            "ArtChg.Treeview",
            rowheight=22, font=('Segoe UI', 8),
            background=Colors.BG_CARD, foreground=Colors.TEXT_PRIMARY,
            fieldbackground=Colors.BG_CARD, borderwidth=0,
        )
        style.configure(
            "ArtChg.Treeview.Heading",
            background=Colors.BG_HEADER, foreground=Colors.TEXT_ON_DARK,
            font=('Segoe UI', 8, 'bold'), relief="flat",
        )

        colonnes = ("ID_Article", "ID_Unite", "Code", "Désignation", "Unité", "Stock", "Prix U.")
        tree = ttk.Treeview(
            tree_frame, columns=colonnes, show='headings',
            height=15, style="ArtChg.Treeview",
        )
        tree.tag_configure("even", background=Colors.BG_CARD)
        tree.tag_configure("odd",  background=Colors.BG_ROW_ALT)

        nom_mag = (
            self.combo_mag_sortie.get() if type_mouvement == "sortie"
            else self.combo_mag_entree.get() or ""
        ).strip()

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

        # ── Requête CTE consolidée (identique aux autres pages) ───────────────
        QUERY = """
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
        ven  AS (SELECT vd.idarticle,vd.idunite,v.idmag,SUM(vd.qtvente) AS q FROM tb_ventedetail vd INNER JOIN tb_vente v ON vd.idvente=v.id AND v.deleted=0 AND v.statut='VALIDEE' WHERE vd.deleted=0 GROUP BY vd.idarticle,vd.idunite,v.idmag),
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
                designationmag  = (
                    self.combo_mag_sortie.get() if type_mouvement == "sortie"
                    else self.combo_mag_entree.get() or ""
                ).strip()
                idmag_actif = self.magasins.get(designationmag)
                tree.heading("Stock", text=f"Magasin {designationmag}" if designationmag else "Magasin")

                if idmag_actif is None:
                    return

                cur.execute(QUERY, (idmag_actif, filtre_like, filtre_like))
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

            idarticle   = values[0]
            idunite     = values[1]
            codeart     = values[2]
            designation = values[3]
            unite       = values[4]
            stock       = self.parser_nombre(str(values[5]))

            if type_mouvement == "sortie":
                self.article_sortie_selectionne = {
                    'idarticle': idarticle, 'idunite': idunite,
                    'designation': designation, 'unite': unite,
                    'code': codeart, 'stock_disponible': stock,
                }
                self.entry_article_sortie.delete(0, "end")
                self.entry_article_sortie.insert(0, designation)
                self.entry_unite_sortie.configure(state="normal")
                self.entry_unite_sortie.delete(0, "end")
                self.entry_unite_sortie.insert(0, unite)
                self.entry_unite_sortie.configure(state="readonly")
            else:
                self.article_entree_selectionne = {
                    'idarticle': idarticle, 'idunite': idunite,
                    'designation': designation, 'unite': unite,
                    'code': codeart, 'stock_disponible': stock,
                }
                self.entry_article_entree.delete(0, "end")
                self.entry_article_entree.insert(0, designation)
                self.entry_unite_entree.configure(state="normal")
                self.entry_unite_entree.delete(0, "end")
                self.entry_unite_entree.insert(0, unite)
                self.entry_unite_entree.configure(state="readonly")

            fen.destroy()

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
    # SECTION 8 — GESTION DES LISTES (SORTIE / ENTRÉE)
    # ══════════════════════════════════════════════════════════════════════════

    def ajouter_article_sortie(self):
        """
        Ajoute un article dans la liste Sortie avec vérification du stock.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        if not self.article_sortie_selectionne:
            messagebox.showwarning("Attention", "Sélectionnez un article.")
            return
        try:
            qty = self.parser_nombre(self.entry_qty_sortie.get())
            if qty <= 0:
                messagebox.showwarning("Attention", "Quantité doit être > 0.")
                return

            stock_dispo = self.article_sortie_selectionne['stock_disponible']
            if qty > stock_dispo:
                messagebox.showerror(
                    "Stock insuffisant",
                    f"Stock disponible : {self.formater_nombre(stock_dispo)}\n"
                    f"Demandé : {self.formater_nombre(qty)}",
                )
                return

            magasin     = self.combo_mag_sortie.get()
            designation = self.article_sortie_selectionne['designation']
            unite       = self.article_sortie_selectionne['unite']
            code        = self.article_sortie_selectionne['code']

            self.tree_sortie.insert("", "end", values=(
                code, designation, unite, magasin, self.formater_nombre(qty),
            ))
            self._refresh_table_alternating_colors(self.tree_sortie)

            self.articles_sortie.append({
                'idarticle': self.article_sortie_selectionne['idarticle'],
                'idunite':   self.article_sortie_selectionne['idunite'],
                'idmagasin': self.magasins[magasin],
                'designation': designation, 'code': code,
                'unite': unite, 'quantite': qty,
            })
            self.annuler_sortie()

        except ValueError:
            messagebox.showerror("Erreur", "Quantité invalide.")

    def ajouter_article_entree(self):
        """
        Ajoute un article dans la liste Entrée.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        if not self.article_entree_selectionne:
            messagebox.showwarning("Attention", "Sélectionnez un article.")
            return
        try:
            qty = self.parser_nombre(self.entry_qty_entree.get())
            if qty <= 0:
                messagebox.showwarning("Attention", "Quantité doit être > 0.")
                return

            magasin     = self.combo_mag_entree.get()
            designation = self.article_entree_selectionne['designation']
            unite       = self.article_entree_selectionne['unite']
            code        = self.article_entree_selectionne['code']

            self.tree_entree.insert("", "end", values=(
                code, designation, unite, magasin, self.formater_nombre(qty),
            ))
            self._refresh_table_alternating_colors(self.tree_entree)

            self.articles_entree.append({
                'idarticle': self.article_entree_selectionne['idarticle'],
                'idunite':   self.article_entree_selectionne['idunite'],
                'idmagasin': self.magasins[magasin],
                'designation': designation, 'code': code,
                'unite': unite, 'quantite': qty,
            })
            self.annuler_entree()
            messagebox.showinfo("Succès", f"Article « {designation} » ajouté à l'entrée.")

        except ValueError:
            messagebox.showerror("Erreur", "Quantité invalide.")

    def annuler_sortie(self):
        """Réinitialise les champs de saisie SORTIE."""
        self.article_sortie_selectionne = None
        self.entry_article_sortie.delete(0, "end")
        self.entry_unite_sortie.configure(state="normal")
        self.entry_unite_sortie.delete(0, "end")
        self.entry_unite_sortie.configure(state="readonly")
        self.entry_qty_sortie.delete(0, "end")

    def annuler_entree(self):
        """Réinitialise les champs de saisie ENTRÉE."""
        self.article_entree_selectionne = None
        self.entry_article_entree.delete(0, "end")
        self.entry_unite_entree.configure(state="normal")
        self.entry_unite_entree.delete(0, "end")
        self.entry_unite_entree.configure(state="readonly")
        self.entry_qty_entree.delete(0, "end")

    def supprimer_article_sortie(self):
        """Supprime la ligne sélectionnée de la sortie."""
        selection = self.tree_sortie.selection()
        if not selection:
            messagebox.showwarning("Attention", "Sélectionnez une ligne.")
            return
        index = self.tree_sortie.index(selection[0])
        self.tree_sortie.delete(selection[0])
        self._refresh_table_alternating_colors(self.tree_sortie)
        self.articles_sortie.pop(index)

    def supprimer_article_entree(self):
        """Supprime la ligne sélectionnée de l'entrée."""
        selection = self.tree_entree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Sélectionnez une ligne.")
            return
        index = self.tree_entree.index(selection[0])
        self.tree_entree.delete(selection[0])
        self._refresh_table_alternating_colors(self.tree_entree)
        self.articles_entree.pop(index)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 9 — CHARGEMENT / RECHERCHE CHANGEMENT
    # ══════════════════════════════════════════════════════════════════════════

    def ouvrir_recherche_changement(self):
        """
        Ouvre le dialogue pour charger un changement existant.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        messagebox.showinfo("À venir", "Fonctionnalité de chargement à développer.")

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 10 — ENREGISTREMENT
    # ══════════════════════════════════════════════════════════════════════════

    def enregistrer_changement(self):
        """
        Enregistre le changement dans tb_changement,
        tb_detailchange_sortie et tb_detailchange_entree.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        if not self.articles_sortie or not self.articles_entree:
            messagebox.showwarning(
                "Attention",
                "Ajoutez au moins un article en sortie ET un article en entrée.",
            )
            return

        conn = self.connect_db()
        if not conn:
            return

        try:
            cursor = conn.cursor()

            refchg = self.entry_ref.get()
            if not refchg:
                messagebox.showerror("Erreur", "Référence vide.")
                return

            note = (self.entry_note.get() or "").strip() or "Aucune description"

            # 1. En-tête changement
            cursor.execute(
                "INSERT INTO tb_changement (refchg, datechg, iduser, note) "
                "VALUES (%s, CURRENT_TIMESTAMP, %s, %s) RETURNING idchg",
                (refchg, self.iduser, note),
            )
            idchg = cursor.fetchone()[0]

            # 2. Articles en sortie
            for article in self.articles_sortie:
                cursor.execute(
                    "INSERT INTO tb_detailchange_sortie "
                    "(idchg, idarticle, idunite, idmagasin, quantite_sortie) "
                    "VALUES (%s,%s,%s,%s,%s)",
                    (idchg, article['idarticle'], article['idunite'],
                     article['idmagasin'], article['quantite']),
                )

            # 3. Articles en entrée
            for article in self.articles_entree:
                cursor.execute(
                    "INSERT INTO tb_detailchange_entree "
                    "(idchg, idarticle, idunite, idmagasin, quantite_entree) "
                    "VALUES (%s,%s,%s,%s,%s)",
                    (idchg, article['idarticle'], article['idunite'],
                     article['idmagasin'], article['quantite']),
                )

            conn.commit()

            messagebox.showinfo(
                "Succès",
                f"Changement enregistré !\n\n"
                f"Référence : {refchg}\n"
                f"Sorties : {len(self.articles_sortie)} article(s)\n"
                f"Entrées : {len(self.articles_entree)} article(s)",
            )

            # Générer le PDF automatiquement
            self.generer_pdf_changement(refchg, idchg)

            # Réinitialiser
            self.articles_sortie = []
            self.articles_entree = []
            self.tree_sortie.delete(*self.tree_sortie.get_children())
            self.tree_entree.delete(*self.tree_entree.get_children())
            self.entry_note.delete(0, "end")
            self.generer_reference()

        except psycopg2.Error as e:
            if conn: conn.rollback()
            messagebox.showerror("Erreur BD", str(e))
        except Exception as e:
            if conn: conn.rollback()
            messagebox.showerror("Erreur", str(e))
            print(f"Erreur enregistrement changement : {e}")
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 11 — IMPRESSION PDF
    # ══════════════════════════════════════════════════════════════════════════

    def imprimer_changement(self):
        """
        Imprime le changement courant sans enregistrement.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        if not self.articles_sortie and not self.articles_entree:
            messagebox.showwarning("Attention", "Aucun article à imprimer.")
            return
        refchg = self.entry_ref.get()
        if refchg:
            self.generer_pdf_changement(refchg, None)
        else:
            messagebox.showwarning("Attention", "Référence requise pour imprimer.")

    def generer_pdf_changement(self, refchg: str, idchg):
        """
        Génère un PDF A5 Landscape pour le changement via _build_pdf_a5.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        try:
            filename = f"Changement_{refchg}.pdf"

            # Récupérer nom utilisateur
            username = "Utilisateur"
            conn     = self.connect_db()
            if conn:
                try:
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT username FROM tb_users WHERE iduser=%s",
                        (self.iduser,),
                    )
                    row = cur.fetchone()
                    if row:
                        username = row[0]
                    cur.close()
                except Exception:
                    pass
                finally:
                    conn.close()

            # Préparer tableau combiné Sortie + Entrée
            colonnes = ("Code", "Désignation", "Unité", "Quantité", "Type")
            data_rows = []
            for art in self.articles_sortie:
                data_rows.append((
                    art.get('code', ''), art.get('designation', ''),
                    art.get('unite', ''), str(art.get('quantite', 0)), 'SORTIE',
                ))
            for art in self.articles_entree:
                data_rows.append((
                    art.get('code', ''), art.get('designation', ''),
                    art.get('unite', ''), str(art.get('quantite', 0)), 'ENTREE',
                ))

            table_data  = (colonnes, data_rows)
            description = (self.entry_note.get() or "").strip() or "Changement d'articles"
            magasin_sortie = (self.combo_mag_sortie.get() or "").strip()

            return self._build_pdf_a5(
                filename,
                "CHANGEMENT D'ARTICLES",
                refchg,
                datetime.now().strftime("%d/%m/%Y"),
                magasin_sortie,
                username,
                table_data,
                description,
                "Magasinier",
                "Responsable Magasin",
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Erreur PDF", str(e))
            return None

    def _build_pdf_a5(self, output_path, titre_entete, reference,
                      date_operation, magasin, operateur,
                      table_data, description,
                      responsable_1="Magasinier",
                      responsable_2="Responsable Magasin"):
        """
        Génère un PDF A5 Landscape avec en-tête société, tableau et signatures.
        Adapté de EtatsPDF_Mouvements.py.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        doc = SimpleDocTemplate(
            output_path,
            pagesize=landscape(A5),
            rightMargin=self.MARGIN, leftMargin=self.MARGIN,
            topMargin=self.MARGIN, bottomMargin=self.MARGIN,
        )
        elements = []
        styles   = getSampleStyleSheet()
        pw       = self.PAGE_WIDTH - 2 * self.MARGIN   # page usable width

        # ── 1. Titre principal ────────────────────────────────────────────────
        main_title = Paragraph(
            "Ankino amin'ny Jehovah ny asanao dia ho lavorary izay kasainao",
            ParagraphStyle('MainTitle', parent=styles['Normal'],
                           fontSize=10, textColor=colors.black,
                           alignment=TA_CENTER, fontName='Helvetica-Bold'),
        )
        title_table = Table([[main_title]], colWidths=[pw])
        title_table.setStyle(TableStyle([
            ('BOX',           (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('BACKGROUND',    (0, 0), (-1, -1), colors.white),
        ]))
        elements.append(title_table)

        # ── 2. En-tête : Société + Opération ─────────────────────────────────
        societe       = self._get_societe_info()
        nomsociete    = societe.get('nomsociete', 'N/A')
        adressesociete= societe.get('adressesociete') or 'Adresse Non Configurée'
        villesociete  = societe.get('villesociete') or ''
        contactsociete= societe.get('contactsociete') or 'Contact: Non Configuré'
        nifsociete    = societe.get('nifsociete') or 'NIF: Non Configuré'
        statsociete   = societe.get('statsociete') or 'STAT: Non Configurée'

        villes_line = f"Ville : {villesociete}<br/>" if villesociete else ""
        header_height = 28 * mm
        company_width = pw * 0.33

        company_details = Paragraph(
            f"<b>{nomsociete}</b><br/>"
            f"Adresse : {adressesociete}<br/>"
            f"{villes_line}"
            f"Contact : {contactsociete}<br/>"
            f"NIF : {nifsociete}<br/>"
            f"STAT : {statsociete}<br/>",
            ParagraphStyle('CompanyDetails', parent=styles['Normal'],
                           fontSize=9, alignment=TA_LEFT, leading=12),
        )
        company_table = Table([[company_details]],
                               colWidths=[company_width - 2*mm],
                               rowHeights=[header_height])
        company_table.setStyle(TableStyle([
            ('BOX',           (0, 0), (-1, -1), 1, self.COLOR_BORDER),
            ('ALIGN',         (0, 0), (0, 0), 'LEFT'),
            ('VALIGN',        (0, 0), (0, 0), 'TOP'),
            ('TOPPADDING',    (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING',   (0, 0), (-1, -1), 6),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
        ]))

        operation_width = pw * 0.67 - 2*mm
        title_w         = operation_width * 0.55
        info_w          = operation_width * 0.45

        op_title = Paragraph(
            titre_entete,
            ParagraphStyle('OpTitle', parent=styles['Normal'],
                           fontSize=14, fontName='Helvetica-Bold',
                           alignment=TA_CENTER, textColor=self.COLOR_HEADER),
        )
        op_info = Paragraph(
            f"<b>Référence :</b> {reference}<br/>"
            f"<b>Date et heure :</b> {date_operation} {datetime.now().strftime('%H:%M')}<br/>"
            f"<b>Magasin :</b> {magasin}<br/>"
            f"<b>Opérateur :</b> {operateur}",
            ParagraphStyle('OpInfo', parent=styles['Normal'],
                           fontSize=9, alignment=TA_LEFT, leading=12),
        )
        op_table = Table([[op_title, op_info]],
                          colWidths=[title_w, info_w], rowHeights=[header_height])
        op_table.setStyle(TableStyle([
            ('BOX',           (0, 0), (-1, -1), 1, self.COLOR_BORDER),
            ('ALIGN',         (0, 0), (0, 0), 'CENTER'),
            ('ALIGN',         (1, 0), (1, 0), 'LEFT'),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',    (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING',   (0, 0), (-1, -1), 6),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
        ]))

        hdr_table = Table([[company_table, op_table]],
                           colWidths=[company_width, operation_width])
        hdr_table.setStyle(TableStyle([
            ('ALIGN',         (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
            ('LINELEFT',      (0, 0), (0, 0),   1, self.COLOR_BORDER),
            ('LINERIGHT',     (0, 0), (0, 0),   1, self.COLOR_BORDER),
            ('LINELEFT',      (1, 0), (1, 0),   1, self.COLOR_BORDER),
            ('LINERIGHT',     (1, 0), (1, 0),   1, self.COLOR_BORDER),
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING',   (0, 0), (-1, -1), -2),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
            ('RIGHTPADDING',  (0, 0), (0, 0),   8),
            ('LEFTPADDING',   (1, 0), (1, 0),   8),
        ]))
        elements.append(hdr_table)
        elements.append(Spacer(1, 4 * mm))

        # ── 3. Tableau articles ───────────────────────────────────────────────
        if table_data:
            columns, data_rows = table_data

            def calc_widths(cols, rows, total_w):
                lengths    = [len(str(c)) for c in cols]
                for row in rows:
                    for i, cell in enumerate(row):
                        lengths[i] = max(lengths[i], len(str(cell or '')))
                total_len  = sum(lengths) or len(cols)
                min_w      = 15 * mm
                avail      = total_w - min_w * len(cols)
                return [min_w + avail * (l / total_len) for l in lengths]

            tbl_w    = pw * 0.95
            col_widths = calc_widths(columns, data_rows, tbl_w)
            cell_style = ParagraphStyle('CellText', parent=styles['Normal'],
                                        fontSize=8, alignment=TA_LEFT, wordWrap='CJK')

            tbl_rows  = [[Paragraph(str(c), cell_style) for c in columns]]
            for row in data_rows:
                tbl_rows.append([Paragraph(str(cell or ''), cell_style) for cell in row])

            art_table = Table(tbl_rows, colWidths=col_widths, repeatRows=1)
            cmds = [
                ('BACKGROUND',   (0, 0), (-1, 0), self.COLOR_BG_TABLE_HEADER),
                ('TEXTCOLOR',    (0, 0), (-1, 0), colors.black),
                ('ALIGN',        (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME',     (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE',     (0, 0), (-1, 0), 8),
                ('TOPPADDING',   (0, 0), (-1, 0), 5),
                ('BOTTOMPADDING',(0, 0), (-1, 0), 5),
                ('VALIGN',       (0, 0), (-1, 0), 'MIDDLE'),
                ('ALIGN',        (0, 1), (1, -1), 'LEFT'),
                ('ALIGN',        (2, 1), (-1, -1),'CENTER'),
                ('VALIGN',       (0, 1), (-1, -1),'TOP'),
                ('TOPPADDING',   (0, 1), (-1, -1), 3),
                ('BOTTOMPADDING',(0, 1), (-1, -1), 3),
                ('LEFTPADDING',  (0, 1), (-1, -1), 3),
                ('RIGHTPADDING', (0, 1), (-1, -1), 3),
                ('BOX',          (0, 0), (-1, -1), 1, self.COLOR_BORDER),
            ]
            for ci in range(1, len(columns)):
                cmds.append(('LINEBEFORE', (ci, 0), (ci, -1), 1, self.COLOR_HEADER))
            art_table.setStyle(TableStyle(cmds))

            elements.append(art_table)
            elements.append(Spacer(1, 3 * mm))

        # ── 4. Description ────────────────────────────────────────────────────
        if description:
            elements.append(Paragraph(
                f"<b>&nbsp;&nbsp;&nbsp;<u>Description :</u></b> {description}<br/><br/>",
                ParagraphStyle('Desc', parent=styles['Normal'],
                               fontSize=9, alignment=TA_LEFT, leading=10),
            ))

        # ── 5. Signatures ─────────────────────────────────────────────────────
        sig_w = pw * 0.33 - 2 * mm
        sig   = Table(
            [[
                Paragraph(responsable_1, ParagraphStyle('S1', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER)),
                '',
                Paragraph(responsable_2, ParagraphStyle('S2', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER)),
            ]],
            colWidths=[sig_w, sig_w, sig_w],
        )
        sig.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('ALIGN',      (0, 0), (0, 1),   'CENTER'),
            ('ALIGN',      (2, 0), (2, 0),   'CENTER'),
            ('VALIGN',     (0, 0), (-1, -1), 'BOTTOM'),
        ]))
        elements.append(sig)

        # ── Build ─────────────────────────────────────────────────────────────
        try:
            doc.build(elements)
            print(f"✅ PDF généré : {output_path}")
            if sys.platform == 'win32':
                os.startfile(output_path)
            return output_path
        except Exception as e:
            print(f"❌ Erreur PDF : {e}")
            messagebox.showerror("Erreur PDF", str(e))
            return None


# ==============================================================================
# POINT D'ENTRÉE AUTONOME (test)
# ==============================================================================

if __name__ == "__main__":
    app = ctk.CTk()
    app.title("iJeery — Changement d'Articles (test)")
    app.geometry("1300x900")

    page = PageChangementArticle(app, iduser=1)
    page.pack(fill="both", expand=True)

    app.mainloop()



class PasswordDialog(ctk.CTkToplevel):
    def __init__(self, title, text):
        super().__init__()
        self.title(title)
        self.geometry("300x150")
        self.result = None
        
        self.label = ctk.CTkLabel(self, text=text)
        self.label.pack(pady=10)
        
        # Le paramètre show="*" cache les caractères
        self.entry = ctk.CTkEntry(self, show="*")
        self.entry.pack(pady=5)
        self.entry.focus_set()
        
        self.btn = ctk.CTkButton(self, text="Valider", command=self.ok)
        self.btn.pack(pady=10)
        
        self.grab_set()  # Rend la fenêtre modale
        self.wait_window()

    def ok(self):
        self.result = self.entry.get()
        self.destroy()


class PageInfoMouvementStock(ctk.CTkFrame):
    """Frame principal avec navigation - Pour intégration dans app_main"""
    def __init__(self, parent, iduser, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.iduser = iduser  # ID de l'utilisateur connecté
        
        # Configuration du thème
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        
        # Connexion à la base de données
        self.db_connection = self.connect_db()
        
        if not self.db_connection:
            messagebox.showwarning("Avertissement", "L'application démarre sans connexion à la base de données.")
        
        # Container principal - Configuration de la grille
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # Création des composants
        self.create_sidebar()
        self.create_content_area()
        
        # Dictionnaire des pages
        self.pages = {}
        self.current_page = None
        
        # Afficher la première page par défaut
        self.show_page("🧾 Bon de commande")
    
    def connect_db(self):
        """Connexion à la base de données PostgreSQL"""
        try:
            # Assurez-vous que 'config.json' existe et est accessible
            with open(get_config_path('config.json')) as f:
                config = json.load(f)
                db_config = config['database']

            conn = psycopg2.connect(
                host=db_config['host'],
                user=db_config['user'],
                password=db_config['password'],
                database=db_config['database'],
                port=db_config['port']  
            )
            return conn
        except FileNotFoundError:
            messagebox.showerror("Erreur de configuration", "Fichier 'config.json' non trouvé.")
            return None
        except KeyError:
            messagebox.showerror("Erreur de configuration", "Clés de base de données manquantes dans 'config.json'.")
            return None
        except psycopg2.Error as err:
            messagebox.showerror("Erreur de connexion", f"Erreur de connexion à PostgreSQL : {err}")
            return None
        except UnicodeDecodeError as err:
            messagebox.showerror("Erreur d'encodage", f"Problème d'encodage du fichier de configuration : {err}")
            return None
        
    def create_sidebar(self):
        """Créer le menu latéral"""
        self.sidebar = ctk.CTkFrame(self, width=150, corner_radius=0, fg_color="#3b82f6")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)
        self.sidebar.grid_propagate(False)  # Empêcher le redimensionnement
        
        # Titre du menu
        title = ctk.CTkLabel(
            self.sidebar,
            text="Mise à jour",
            font=("Arial", 20, "bold"),
            text_color="white"
        )
        title.grid(row=0, column=0, padx=20, pady=30)
        
        # Boutons du menu
        self.menu_buttons = {}
        menus = [
            ("🧾 Bon de commande", "PageCommandeFrs"),
            ("📥 Bon de réception", "PageBonReception"),
            ("🔄 Transferts", "PageTransfert"),
            ("📤 Sortie/Consommation", "PageSortie"),
            ("🔁 Changements", "PageChangementArticle"),
            ("🚚 Transporteurs", "PageTransporteur"),
            ("🧾 Infos Charges", "PageInfosCharges")
        ]
        
        for idx, (menu_name, page_class) in enumerate(menus, start=1):
            btn = ctk.CTkButton(
                self.sidebar,
                text=menu_name,
                font=("Arial", 13),
                fg_color="transparent",
                hover_color="#2563eb",
                anchor="w",
                height=40,
                command=lambda m=menu_name: self.show_page(m)
            )
            btn.grid(row=idx, column=0, padx=10, pady=6, sticky="ew")
            self.menu_buttons[menu_name] = btn
    
    def create_content_area(self):
        """Créer la zone de contenu principal"""
        self.content_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#f8fafc")
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        
        # Message initial
        self.initial_label = ctk.CTkLabel(
            self.content_frame,
            text="⚙️ Prêt à travailler\n\nSélectionnez une option dans le menu",
            font=("Arial", 18),
            text_color="#94a3b8"
        )
        self.initial_label.place(relx=0.5, rely=0.5, anchor="center")
        
    def verifier_code_autorisation(self, code_saisi):
        """Vérifie si le code existe dans la table tb_codeautorisation"""
        if not self.db_connection:
            return False
        try:
            cursor = self.db_connection.cursor()
            query = "SELECT 1 FROM tb_codeautorisation WHERE code = %s"
            cursor.execute(query, (code_saisi,))
            result = cursor.fetchone()
            cursor.close()
            return result is not None
        except Exception as e:
            print(f"Erreur vérification code: {e}")
            return False
    
    def show_page(self, menu_name):
        """Afficher la page correspondant au menu sélectionné"""
        
              
        # Cacher le label initial
        if self.initial_label:
            self.initial_label.place_forget()
            self.initial_label = None
        
        # Mapping menu -> classe de page (IMPORTÉES)
        page_mapping = {
            "🧾 Bon de commande": PageCommandeFrs,
            "📥 Bon de réception": PageBonReception,
            "🔄 Transferts": PageTransfert,
            "📤 Sortie/Consommation": PageSortie,
            "🔁 Changements": PageChangementArticle,
            "🚚 Transporteurs": PageTransporteur,
            "🧾 Infos Charges": PageInfosCharges
        }
        
        # Cacher la page actuelle
        if self.current_page:
            self.current_page.pack_forget()
        
        # Créer ou afficher la page demandée
        if menu_name not in self.pages:
            page_class = page_mapping[menu_name]
            
            # IMPORTANT : Passer le bon paramètre selon la classe
            try:
                if page_class == PageCommandeFrs:
                    self.pages[menu_name] = page_class(self.content_frame, self.iduser)
                elif page_class == PageBonReception:
                    self.pages[menu_name] = page_class(self.content_frame, self.iduser)
                elif page_class == PageTransfert:
                    self.pages[menu_name] = page_class(self.content_frame, self.iduser)
                elif page_class == PageSortie:
                    self.pages[menu_name] = page_class(self.content_frame, self.iduser)
                elif page_class == PageSuiviCommande:
                    self.pages[menu_name] = page_class(self.content_frame) # Pas d'iduser ici
                elif page_class == PageChangementArticle:
                    self.pages[menu_name] = page_class(self.content_frame, self.iduser)
                elif page_class == PageTransporteur:
                    self.pages[menu_name] = page_class(self.content_frame, self.iduser)
                elif page_class == PageInfosCharges:
                    self.pages[menu_name] = page_class(self.content_frame, self.iduser)
                else:
                    self.pages[menu_name] = page_class(self.content_frame, self.iduser)
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors du chargement de la page {menu_name}:\n{str(e)}")
                return
        
        self.current_page = self.pages[menu_name]
        self.current_page.pack(fill="both", expand=True)
        
        # Forcer la mise à jour de l'affichage
        self.content_frame.update_idletasks()
        
        # Mettre à jour l'apparence des boutons
        for btn_name, btn in self.menu_buttons.items():
            if btn_name == menu_name:
                btn.configure(fg_color="#2563eb")
            else:
                btn.configure(fg_color="transparent")


# Test standalone si lancé directement
if __name__ == "__main__":
    # ID utilisateur (à récupérer depuis votre système d'authentification)
    iduser = 1
    
    # Créer une fenêtre de test
    app = ctk.CTk()
    app.title("Test - Mise à jour")
    app.geometry("1400x800")
    
    # Créer et afficher le frame
    page = PageInfoMouvementStock(app, iduser)
    page.pack(fill="both", expand=True)
    
    app.mainloop()
