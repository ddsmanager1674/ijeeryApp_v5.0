# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           iJeery — pages/page_ReceptionDirecte.py                           ║
║           Réception Directe Fournisseur (sans Bon de Commande)              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Enregistre directement dans tb_livraisonfrs :                              ║
║    INSERT INTO tb_livraisonfrs                                               ║
║      (reflivfrs, idcom, idarticle, idunite, qtlivrefrs, dateregistre,       ║
║       typemouvement, idmag, factfrs, iduser, dateperemption, a_payer)       ║
║    VALUES (%s,%s,%s,%s,%s,%s,1,%s,%s,%s,%s,%s)                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import json
import os
import tempfile
import subprocess
import sys
from datetime import datetime, date
from tkcalendar import DateEntry
from resource_utils import get_config_path
from app_theme import Colors, Fonts, styled, Theme

from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.lib import colors as rl_colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers TTK — appliqués une seule fois
# ─────────────────────────────────────────────────────────────────────────────
def _apply_treeview_style():
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "RD.Treeview",
        background=Colors.BG_CARD,
        foreground=Colors.TEXT_PRIMARY,
        fieldbackground=Colors.BG_CARD,
        rowheight=28,
        font=("Segoe UI", 9),
        borderwidth=0,
    )
    style.configure(
        "RD.Treeview.Heading",
        background=Colors.MIDNIGHT,
        foreground=Colors.TEXT_ON_DARK,
        font=("Segoe UI", 9, "bold"),
        relief="flat",
        borderwidth=0,
    )
    style.map("RD.Treeview",
              background=[("selected", Colors.PRIMARY_LIGHT)],
              foreground=[("selected", Colors.TEXT_PRIMARY)])
    style.map("RD.Treeview.Heading",
              background=[("active", Colors.MIDNIGHT_LIGHT)])


# ─────────────────────────────────────────────────────────────────────────────
# Page principale
# ─────────────────────────────────────────────────────────────────────────────
class PageReceptionDirecte(ctk.CTkFrame):
    """
    Bon de Réception Direct — sans passer par un Bon de Commande.
    Insère dans tb_livraisonfrs avec idcom = NULL et typemouvement = 1.

    Layout :
    ┌────────────────────────────────────────────────────────┐
    │ En-tête (titre + bouton Nouveau)                       │
    ├────────────────────────────────────────────────────────┤
    │ Section 1 — Infos BR (N°BR readonly | Fournisseur 🔍) │
    │             Magasin (combobox) | Fact. Frs | Date      │
    ├────────────────────────────────────────────────────────┤
    │ Section 2 — Saisie article (🔍 article | Unité)        │
    │             Qté Livrée | Prix Unit. | Montant | ➕     │
    │             Péremption (opt.) | A payer (checkbox)     │
    ├────────────────────────────────────────────────────────┤
    │ Section 3 — Tableau articles + boutons Modifier/Suppr. │
    │             Total | Enregistrer                        │
    └────────────────────────────────────────────────────────┘
    """

    def __init__(self, parent, iduser: int):
        super().__init__(parent, fg_color=Colors.BG_PAGE)
        _apply_treeview_style()

        self.iduser = iduser
        self.fournisseur_id   = None
        self.fournisseur_nom  = ""
        self.article_selectionne = None   # dict: idarticle, idunite, nomart, unite
        self.items_reception  = []        # liste des lignes en cours
        self.index_modif      = None      # index de la ligne en cours de modification
        self.magasins         = {}        # {designation: idmag}

        self.setup_ui()
        self._generer_reference()
        self._charger_magasins()

    # =========================================================================
    # BASE DE DONNÉES
    # =========================================================================
    def connect_db(self):
        try:
            with open(get_config_path('config.json')) as f:
                config = json.load(f)
                db = config['database']
            return psycopg2.connect(
                host=db['host'], user=db['user'],
                password=db['password'], database=db['database'],
                port=db['port']
            )
        except FileNotFoundError:
            messagebox.showerror("Erreur", "Fichier 'config.json' non trouvé.")
        except psycopg2.Error as e:
            messagebox.showerror("Connexion DB", str(e))
        return None

    # =========================================================================
    # UTILITAIRES NUMÉRIQUES
    # =========================================================================
    def _fmt(self, v):
        """Float → chaîne lisible  1.234,56"""
        try:
            v = float(v)
            entier = int(v)
            dec    = abs(v - entier)
            return f"{entier:,}".replace(',', '.') + f",{int(dec*100):02d}"
        except Exception:
            return "0,00"

    def _parse(self, txt):
        try:
            return float(str(txt).replace('.', '').replace(',', '.'))
        except Exception:
            return 0.0

    def _format_date_db(self, s):
        """JJ/MM/AAAA → AAAA-MM-JJ"""
        if not s:
            return None
        try:
            p = s.split('/')
            return f"{p[2]}-{p[1]}-{p[0]}" if len(p) == 3 else s
        except Exception:
            return None

    # =========================================================================
    # COULEURS ALTERNÉES TREEVIEW
    # =========================================================================
    def _configure_alt_colors(self, tree):
        tree.tag_configure("row_even", background=Colors.BG_CARD)
        tree.tag_configure("row_odd",  background=Colors.BG_ROW_ALT)

    def _refresh_alt_colors(self, tree):
        for idx, item in enumerate(tree.get_children()):
            tags = tuple(t for t in tree.item(item, "tags") if t not in ("row_even", "row_odd"))
            tree.item(item, tags=tags + ("row_even" if idx % 2 == 0 else "row_odd",))

    # =========================================================================
    # CONSTRUCTION UI
    # =========================================================================
    def setup_ui(self):
        # ── En-tête ──────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT, corner_radius=0, height=42)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        self.lbl_titre = ctk.CTkLabel(
            hdr, text="📦  Nouvelle Réception Directe",
            font=Fonts.bold(14), text_color=Colors.TEXT_ON_DARK
        )
        self.lbl_titre.pack(side="left", padx=14)

        styled.button_secondary(
            hdr, text="🔄 Nouveau", command=self._nouveau,
            width=100, height=28
        ).pack(side="right", padx=8, pady=7)

        # ── Corps ─────────────────────────────────────────────────────────────
        body = ctk.CTkFrame(self, fg_color=Colors.BG_PAGE)
        body.pack(fill="both", expand=True, padx=8, pady=6)

        self._build_section_infos(body)
        self._build_section_article(body)
        self._build_section_tableau(body)

    # ─────────────────────────────────────────────────────────────────────────
    # Section 1 — Infos générales
    # ─────────────────────────────────────────────────────────────────────────
    def _build_section_infos(self, parent):
        card = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD,
                            corner_radius=8, border_width=1, border_color=Colors.BORDER)
        card.pack(fill="x", pady=(0, 4))

        # ── Ligne 1 : N°BR | Fournisseur ─────────────────────────────────────
        row1 = ctk.CTkFrame(card, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=(8, 4))
        row1.columnconfigure(3, weight=1)

        ctk.CTkLabel(row1, text="📋 BR N°", font=Fonts.bold(11),
                     text_color=Colors.MIDNIGHT, width=70, anchor="w"
                     ).grid(row=0, column=0, sticky="w", padx=(0, 6))

        self.entry_ref = ctk.CTkEntry(
            row1, width=170, height=28,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            font=Fonts.body(11), state="readonly"
        )
        self.entry_ref.grid(row=0, column=1, sticky="w", padx=(0, 20))

        ctk.CTkLabel(row1, text="Fournisseur :", font=Fonts.label(10),
                     text_color=Colors.TEXT_SECONDARY, anchor="w"
                     ).grid(row=0, column=2, sticky="w", padx=(0, 4))

        frs_f = ctk.CTkFrame(row1, fg_color="transparent")
        frs_f.grid(row=0, column=3, sticky="ew")

        self.entry_fournisseur = ctk.CTkEntry(
            frs_f, height=28,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            font=Fonts.body(11), state="readonly",
            placeholder_text="Sélectionner un fournisseur…"
        )
        self.entry_fournisseur.pack(side="left", fill="x", expand=True, padx=(0, 4))

        ctk.CTkButton(
            frs_f, text="🔍", width=28, height=28,
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            text_color="white", font=Fonts.body(11), corner_radius=6,
            command=self._ouvrir_recherche_fournisseur
        ).pack(side="left")

        # ── Ligne 2 : Magasin | Fact. Fournisseur | Date ─────────────────────
        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=(0, 8))
        row2.columnconfigure(5, weight=1)

        # Magasin
        ctk.CTkLabel(row2, text="Magasin :", font=Fonts.label(10),
                     text_color=Colors.TEXT_SECONDARY, anchor="w"
                     ).grid(row=0, column=0, sticky="w", padx=(0, 4))

        self.combo_magasin = ctk.CTkComboBox(
            row2, width=180, height=28,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            font=Fonts.body(11), values=[],
            state="readonly"
        )
        self.combo_magasin.grid(row=0, column=1, sticky="w", padx=(0, 20))

        # Facture fournisseur
        ctk.CTkLabel(row2, text="N° Facture frs :", font=Fonts.label(10),
                     text_color=Colors.TEXT_SECONDARY, anchor="w"
                     ).grid(row=0, column=2, sticky="w", padx=(0, 4))

        self.entry_factfrs = ctk.CTkEntry(
            row2, width=150, height=28,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            font=Fonts.body(11),
            placeholder_text="Réf. facture frs…"
        )
        self.entry_factfrs.grid(row=0, column=3, sticky="w", padx=(0, 20))

        # Date
        ctk.CTkLabel(row2, text="Date :", font=Fonts.label(10),
                     text_color=Colors.TEXT_SECONDARY, anchor="w"
                     ).grid(row=0, column=4, sticky="w", padx=(0, 4))

        self.date_reception = DateEntry(
            row2, width=11,
            background=Colors.MIDNIGHT, foreground="white",
            borderwidth=1, date_pattern="dd/mm/yyyy",
            locale='fr_FR', font=("Segoe UI", 9)
        )
        self.date_reception.set_date(date.today())
        self.date_reception.grid(row=0, column=5, sticky="w")

    # ─────────────────────────────────────────────────────────────────────────
    # Section 2 — Saisie article
    # ─────────────────────────────────────────────────────────────────────────
    def _build_section_article(self, parent):
        card = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD,
                            corner_radius=8, border_width=1, border_color=Colors.BORDER)
        card.pack(fill="x", pady=(0, 4))

        # ── Ligne 1 : Article + bouton recherche ──────────────────────────────
        r1 = ctk.CTkFrame(card, fg_color="transparent")
        r1.pack(fill="x", padx=10, pady=(8, 4))
        r1.columnconfigure(2, weight=1)

        ctk.CTkLabel(r1, text="📦 Article", font=Fonts.bold(11),
                     text_color=Colors.MIDNIGHT, width=78, anchor="w"
                     ).grid(row=0, column=0, sticky="w", padx=(0, 6))

        self.entry_article = ctk.CTkEntry(
            r1, height=28,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            font=Fonts.body(11), state="readonly",
            placeholder_text="Cliquez sur 🔍 pour sélectionner un article…"
        )
        self.entry_article.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(0, 4))

        ctk.CTkButton(
            r1, text="🔍 Rechercher", width=110, height=28,
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            text_color="white", font=Fonts.body(10), corner_radius=6,
            command=self._ouvrir_recherche_article
        ).grid(row=0, column=3, sticky="w")

        # ── Ligne 2 : champs de saisie inline ────────────────────────────────
        r2 = ctk.CTkFrame(card, fg_color="transparent")
        r2.pack(fill="x", padx=10, pady=(0, 8))

        def _field(par, label, width=90, readonly=False):
            wrap = ctk.CTkFrame(par, fg_color="transparent")
            wrap.pack(side="left", padx=(0, 6))
            ctk.CTkLabel(wrap, text=label, font=Fonts.small(9),
                         text_color=Colors.TEXT_MUTED).pack(anchor="w")
            e = ctk.CTkEntry(
                wrap, width=width, height=26,
                fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
                font=Fonts.body(10),
                state="readonly" if readonly else "normal"
            )
            e.pack()
            return e

        self.entry_unite     = _field(r2, "Unité",        85, readonly=True)
        self.entry_qtlivree  = _field(r2, "Qté livrée",   95)
        self.entry_prix_unit = _field(r2, "Prix unitaire", 105)

        # Montant (calculé)
        montant_wrap = ctk.CTkFrame(r2, fg_color="transparent")
        montant_wrap.pack(side="left", padx=(0, 6))
        ctk.CTkLabel(montant_wrap, text="Montant", font=Fonts.small(9),
                     text_color=Colors.TEXT_MUTED).pack(anchor="w")
        self.lbl_montant_ligne = ctk.CTkLabel(
            montant_wrap, text="0,00",
            font=Fonts.bold(10), text_color=Colors.SUCCESS_TEXT,
            fg_color=Colors.SUCCESS_LIGHT, corner_radius=5, padx=7, pady=4,
            width=100
        )
        self.lbl_montant_ligne.pack(anchor="w")

        # Séparateur vertical
        ctk.CTkFrame(r2, width=1, height=44, fg_color=Colors.BORDER
                     ).pack(side="left", padx=8)

        # Péremption (optionnelle)
        per_wrap = ctk.CTkFrame(r2, fg_color="transparent")
        per_wrap.pack(side="left", padx=(0, 6))

        per_lbl_row = ctk.CTkFrame(per_wrap, fg_color="transparent")
        per_lbl_row.pack(anchor="w")

        self.var_peremption = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            per_lbl_row, text="", variable=self.var_peremption,
            command=self._toggle_peremption,
            checkbox_width=15, checkbox_height=15,
            checkmark_color=Colors.TEXT_ON_DARK,
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            width=18
        ).pack(side="left", padx=(0, 2))
        ctk.CTkLabel(per_lbl_row, text="Péremption (opt.)",
                     font=Fonts.small(9), text_color=Colors.TEXT_MUTED
                     ).pack(side="left")

        self.cal_peremption = DateEntry(
            per_wrap, width=9,
            background=Colors.MIDNIGHT, foreground="white",
            borderwidth=1, date_pattern="dd/mm/yyyy",
            locale='fr_FR', font=("Segoe UI", 9), state="disabled"
        )
        self._toggle_peremption()  # état initial

        # À payer (checkbox)
        apayer_wrap = ctk.CTkFrame(r2, fg_color="transparent")
        apayer_wrap.pack(side="left", padx=(0, 6))
        ctk.CTkLabel(apayer_wrap, text=" ", font=Fonts.small(9)).pack(anchor="w")  # alignement
        self.var_a_payer = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            apayer_wrap, text="À payer", variable=self.var_a_payer,
            checkbox_width=15, checkbox_height=15,
            checkmark_color=Colors.TEXT_ON_DARK,
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
        ).pack(anchor="w")

        # ── Boutons ──────────────────────────────────────────────────────────
        btn_wrap = ctk.CTkFrame(r2, fg_color="transparent")
        btn_wrap.pack(side="right")
        ctk.CTkLabel(btn_wrap, text=" ", font=Fonts.small(9)).pack(anchor="w")  # alignement
        btn_inner = ctk.CTkFrame(btn_wrap, fg_color="transparent")
        btn_inner.pack()

        self.btn_ajouter = ctk.CTkButton(
            btn_inner, text="➕ Ajouter", width=100, height=26,
            fg_color=Colors.SUCCESS, hover_color=Colors.SUCCESS_DARK,
            text_color=Colors.TEXT_ON_DARK, font=Fonts.button(10),
            corner_radius=5, command=self._ajouter_article
        )
        self.btn_ajouter.pack(side="left", padx=(0, 4))

        self.btn_valider_modif = ctk.CTkButton(
            btn_inner, text="✅ Valider modif.", width=120, height=26,
            fg_color=Colors.WARNING, hover_color="#D68910",
            text_color=Colors.TEXT_ON_DARK, font=Fonts.button(10),
            corner_radius=5, state="disabled",
            command=self._valider_modification
        )
        self.btn_valider_modif.pack(side="left", padx=(0, 4))

        self.btn_annuler_modif = ctk.CTkButton(
            btn_inner, text="✖", width=28, height=26,
            fg_color=Colors.CLOUDS, hover_color=Colors.SILVER,
            text_color=Colors.TEXT_PRIMARY, font=Fonts.button(10),
            border_width=1, border_color=Colors.BORDER, corner_radius=5,
            state="disabled", command=self._annuler_modif
        )
        self.btn_annuler_modif.pack(side="left")

        # Liaisons calcul automatique
        self.entry_qtlivree.bind('<KeyRelease>',  lambda e: self._recalc_montant())
        self.entry_prix_unit.bind('<KeyRelease>', lambda e: self._recalc_montant())

    # ─────────────────────────────────────────────────────────────────────────
    # Section 3 — Tableau + actions
    # ─────────────────────────────────────────────────────────────────────────
    def _build_section_tableau(self, parent):
        card = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD,
                            corner_radius=8, border_width=1, border_color=Colors.BORDER)
        card.pack(fill="both", expand=True, pady=(0, 0))

        # En-tête tableau
        thead = ctk.CTkFrame(card, fg_color="transparent")
        thead.pack(fill="x", padx=10, pady=(6, 4))

        ctk.CTkLabel(thead, text="📄 Lignes de réception",
                     font=Fonts.bold(11), text_color=Colors.MIDNIGHT
                     ).pack(side="left")

        self.lbl_total_global = ctk.CTkLabel(
            thead, text="Total : 0,00",
            font=Fonts.bold(12), text_color=Colors.SUCCESS_TEXT,
            fg_color=Colors.SUCCESS_LIGHT, corner_radius=6, padx=10, pady=3
        )
        self.lbl_total_global.pack(side="right")

        # Treeview
        tree_frame = ctk.CTkFrame(card, fg_color=Colors.BORDER, corner_radius=6)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 4))

        colonnes = ("Article", "Unité", "Qté Livrée", "Prix Unit.", "Montant", "Péremption", "À payer")
        self.tree = ttk.Treeview(
            tree_frame, columns=colonnes,
            show="headings", height=7,
            style="RD.Treeview"
        )
        self._configure_alt_colors(self.tree)

        col_widths = {
            "Article": 250, "Unité": 80, "Qté Livrée": 90,
            "Prix Unit.": 100, "Montant": 110, "Péremption": 90, "À payer": 70
        }
        col_anchors = {
            "Article": "w", "Unité": "center", "Qté Livrée": "e",
            "Prix Unit.": "e", "Montant": "e", "Péremption": "center", "À payer": "center"
        }
        for col in colonnes:
            self.tree.column(col, width=col_widths[col],
                             anchor=col_anchors[col], minwidth=50)

        from treeview_sort_utils import attach_tree_sort
        attach_tree_sort(self.tree, list(colonnes), configure_columns=False)
        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.tree.bind('<<TreeviewSelect>>', self._on_select)
        self.tree.bind('<Double-Button-1>', self._on_double_click)

        # Barre basse
        bot = ctk.CTkFrame(card, fg_color="transparent")
        bot.pack(fill="x", padx=10, pady=(0, 8))

        styled.button_warning(
            bot, text="✏️ Modifier", icon="",
            width=120, height=28,
            command=self._modifier_ligne_selectionnee
        ).pack(side="left", padx=(0, 6))

        styled.button_danger(
            bot, text="🗑️ Supprimer", icon="",
            width=120, height=28,
            command=self._supprimer_ligne
        ).pack(side="left")

        ctk.CTkButton(
            bot,
            text="🖨️ Imprimer PDF",
            font=Fonts.button(11),
            fg_color=Colors.INFO,
            hover_color=Colors.INFO_DARK,
            text_color=Colors.TEXT_ON_DARK,
            height=28, width=140, corner_radius=6,
            command=self._imprimer_pdf,
        ).pack(side="left", padx=(12, 0))

        styled.button_success(
            bot, text="💾 Enregistrer", icon="",
            command=self._enregistrer, width=150, height=28
        ).pack(side="right")

        self.lbl_total_bas = ctk.CTkLabel(
            bot, text="Total : 0,00",
            font=Fonts.bold(11), text_color=Colors.TEXT_MUTED
        )
        self.lbl_total_bas.pack(side="right", padx=12)

    # =========================================================================
    # CHARGEMENTS DB
    # =========================================================================
    def _generer_reference(self):
        """Génère le prochain N° BR basé sur tb_livraisonfrs."""
        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            annee = datetime.now().year
            cur.execute(
                "SELECT reflivfrs FROM tb_livraisonfrs WHERE reflivfrs LIKE %s "
                "ORDER BY reflivfrs DESC LIMIT 1",
                (f"{annee}-BR-%",)
            )
            row = cur.fetchone()
            num = (int(row[0].split('-')[-1]) + 1) if row else 1
            ref = f"{annee}-BR-{num:05d}"
            self.entry_ref.configure(state="normal")
            self.entry_ref.delete(0, "end")
            self.entry_ref.insert(0, ref)
            self.entry_ref.configure(state="readonly")
        except Exception as e:
            messagebox.showerror("Erreur", f"Génération référence : {e}")
        finally:
            if 'cur' in locals():
                cur.close()
            conn.close()

    def _charger_magasins(self):
        """Charge la liste des magasins dans le combobox."""
        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT idmag, designationmag FROM tb_magasin "
                "WHERE COALESCE(deleted, 0) = 0 ORDER BY designationmag"
            )
            rows = cur.fetchall()
            self.magasins = {r[1]: r[0] for r in rows}
            noms = list(self.magasins.keys())
            self.combo_magasin.configure(values=noms)
            if noms:
                self.combo_magasin.set(noms[0])
        except Exception as e:
            messagebox.showerror("Erreur", f"Magasins : {e}")
        finally:
            if 'cur' in locals():
                cur.close()
            conn.close()

    # =========================================================================
    # RECHERCHE FOURNISSEUR
    # =========================================================================
    def _ouvrir_recherche_fournisseur(self):
        fen = ctk.CTkToplevel(self)
        fen.title("Rechercher un fournisseur")
        fen.geometry("800x420")
        fen.grab_set()
        Theme.apply_toplevel(fen)

        main = ctk.CTkFrame(fen, fg_color=Colors.BG_PAGE)
        main.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(main, text="Sélectionner un fournisseur",
                     font=Fonts.heading(14), text_color=Colors.MIDNIGHT
                     ).pack(pady=(0, 10))

        sf = ctk.CTkFrame(main, fg_color="transparent")
        sf.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(sf, text="🔍").pack(side="left", padx=6)
        entry_s = ctk.CTkEntry(
            sf, placeholder_text="Nom ou contact…", height=34,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            font=Fonts.body(11)
        )
        entry_s.pack(side="left", fill="x", expand=True, padx=4)

        tf = ctk.CTkFrame(main, fg_color=Colors.BORDER, corner_radius=8)
        tf.pack(fill="both", expand=True, pady=(0, 8))
        cols = ("ID", "Nom", "Contact", "Adresse")
        tree = ttk.Treeview(tf, columns=cols, show="headings",
                             height=10, style="RD.Treeview")
        self._configure_alt_colors(tree)
        tree.column("ID", width=0, stretch=False)
        tree.column("Nom", width=180)
        tree.column("Contact", width=150)
        tree.column("Adresse", width=300)
        for c in cols:
            tree.heading(c, text=c)
        sb = ttk.Scrollbar(tf, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        lbl_c = ctk.CTkLabel(main, text="", font=Fonts.small(10),
                              text_color=Colors.TEXT_MUTED)
        lbl_c.pack(pady=(0, 4))

        def charger(filtre=""):
            for i in tree.get_children():
                tree.delete(i)
            conn = self.connect_db()
            if not conn:
                return
            try:
                cur = conn.cursor()
                q = ("SELECT idfrs, nomfrs, contactfrs, adressefrs "
                     "FROM tb_fournisseur WHERE deleted=0")
                p = []
                if filtre:
                    q += (" AND (LOWER(nomfrs) LIKE LOWER(%s) "
                          "OR LOWER(contactfrs) LIKE LOWER(%s))")
                    p = [f"%{filtre}%", f"%{filtre}%"]
                q += " ORDER BY nomfrs"
                cur.execute(q, p)
                rows = cur.fetchall()
                for r in rows:
                    tree.insert("", "end",
                                values=(r[0], r[1] or '', r[2] or '', r[3] or ''))
                self._refresh_alt_colors(tree)
                lbl_c.configure(text=f"{len(rows)} fournisseur(s)")
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
            finally:
                conn.close()

        entry_s.bind('<KeyRelease>', lambda e: charger(entry_s.get()))

        def valider():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Attention", "Sélectionnez un fournisseur.")
                return
            v = tree.item(sel[0])['values']
            self.fournisseur_id  = v[0]
            self.fournisseur_nom = v[1]
            self.entry_fournisseur.configure(state="normal")
            self.entry_fournisseur.delete(0, "end")
            self.entry_fournisseur.insert(0, v[1])
            self.entry_fournisseur.configure(state="readonly")
            fen.destroy()

        tree.bind('<Double-Button-1>', lambda e: valider())
        bf = ctk.CTkFrame(main, fg_color="transparent")
        bf.pack(fill="x")
        styled.button_danger(bf, text="Annuler", icon="❌",
                             width=110, height=36,
                             command=fen.destroy).pack(side="left", padx=4)
        styled.button_success(bf, text="Valider", icon="✅",
                              width=110, height=36,
                              command=valider).pack(side="right", padx=4)
        charger()

    # =========================================================================
    # RECHERCHE ARTICLE
    # =========================================================================
    def _ouvrir_recherche_article(self):
        if self.index_modif is not None:
            messagebox.showwarning("Attention",
                                   "Validez ou annulez la modification en cours.")
            return

        fen = ctk.CTkToplevel(self)
        fen.title("Rechercher un article")
        fen.geometry("1000x560")
        fen.grab_set()
        Theme.apply_toplevel(fen)

        main = ctk.CTkFrame(fen, fg_color=Colors.BG_PAGE)
        main.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(main, text="Sélectionner un article",
                     font=Fonts.heading(14), text_color=Colors.MIDNIGHT
                     ).pack(pady=(0, 10))

        sf = ctk.CTkFrame(main, fg_color="transparent")
        sf.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(sf, text="🔍").pack(side="left", padx=6)
        entry_s = ctk.CTkEntry(
            sf, placeholder_text="Code ou désignation…", height=34,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            font=Fonts.body(11)
        )
        entry_s.pack(side="left", fill="x", expand=True, padx=4)
        entry_s.focus_set()

        tf = ctk.CTkFrame(main, fg_color=Colors.BORDER, corner_radius=8)
        tf.pack(fill="both", expand=True, pady=(0, 8))
        cols = ("ID_Art", "ID_Unite", "Code", "Désignation", "Unité")
        tree = ttk.Treeview(tf, columns=cols, show="headings",
                             height=14, style="RD.Treeview")
        self._configure_alt_colors(tree)
        tree.column("ID_Art",   width=0,   stretch=False)
        tree.column("ID_Unite", width=0,   stretch=False)
        tree.column("Code",        width=140)
        tree.column("Désignation", width=480)
        tree.column("Unité",       width=110)
        for c in cols:
            tree.heading(c, text=c)
        sb = ttk.Scrollbar(tf, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        lbl_c = ctk.CTkLabel(main, text="", font=Fonts.small(10),
                              text_color=Colors.TEXT_MUTED)
        lbl_c.pack(pady=(0, 4))

        def charger(filtre=""):
            for i in tree.get_children():
                tree.delete(i)
            conn = self.connect_db()
            if not conn:
                return
            try:
                cur = conn.cursor()
                q = """
                    SELECT T2.idarticle, T1.idunite, T1.codearticle,
                           T2.designation, T1.designationunite
                    FROM tb_unite T1
                    INNER JOIN tb_article T2 ON T1.idarticle = T2.idarticle
                    WHERE T2.deleted = 0
                """
                p = []
                if filtre:
                    q += (" AND (LOWER(T1.codearticle) LIKE LOWER(%s) "
                          "OR LOWER(T2.designation) LIKE LOWER(%s))")
                    p = [f"%{filtre}%", f"%{filtre}%"]
                q += " ORDER BY T1.codearticle"
                cur.execute(q, p)
                rows = cur.fetchall()
                for r in rows:
                    tree.insert("", "end",
                                values=(r[0], r[1], r[2], r[3], r[4]))
                self._refresh_alt_colors(tree)
                lbl_c.configure(text=f"{len(rows)} article(s)")
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
            finally:
                conn.close()

        entry_s.bind('<KeyRelease>', lambda e: charger(entry_s.get()))

        def valider():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Attention", "Sélectionnez un article.")
                return
            v = tree.item(sel[0])['values']
            self.article_selectionne = {
                'idarticle': v[0], 'idunite': v[1],
                'nomart': v[3], 'unite': v[4]
            }
            self.entry_article.configure(state="normal")
            self.entry_article.delete(0, "end")
            self.entry_article.insert(0, v[3])
            self.entry_article.configure(state="readonly")
            self.entry_unite.configure(state="normal")
            self.entry_unite.delete(0, "end")
            self.entry_unite.insert(0, v[4])
            self.entry_unite.configure(state="readonly")
            self.entry_qtlivree.delete(0, "end")
            self.entry_prix_unit.delete(0, "end")
            self._recalc_montant()
            fen.destroy()

        tree.bind('<Double-Button-1>', lambda e: valider())
        bf = ctk.CTkFrame(main, fg_color="transparent")
        bf.pack(fill="x")
        styled.button_danger(bf, text="Annuler", icon="❌",
                             width=110, height=36,
                             command=fen.destroy).pack(side="left", padx=4)
        styled.button_success(bf, text="Valider", icon="✅",
                              width=110, height=36,
                              command=valider).pack(side="right", padx=4)
        charger()

    # =========================================================================
    # CALCUL MONTANT LIGNE
    # =========================================================================
    def _recalc_montant(self):
        try:
            qt  = self._parse(self.entry_qtlivree.get())
            pu  = self._parse(self.entry_prix_unit.get())
            self.lbl_montant_ligne.configure(text=self._fmt(qt * pu))
        except Exception:
            self.lbl_montant_ligne.configure(text="0,00")

    # =========================================================================
    # PÉREMPTION TOGGLE
    # =========================================================================
    def _toggle_peremption(self):
        if self.var_peremption.get():
            self.cal_peremption.configure(state="normal")
            if not self.cal_peremption.winfo_manager():
                self.cal_peremption.pack(anchor="w")
        else:
            self.cal_peremption.configure(state="disabled")
            if self.cal_peremption.winfo_manager():
                self.cal_peremption.pack_forget()

    # =========================================================================
    # AJOUTER LIGNE
    # =========================================================================
    def _ajouter_article(self):
        if not self.article_selectionne:
            messagebox.showwarning("Attention", "Sélectionnez d'abord un article.")
            return
        if not self.fournisseur_id:
            messagebox.showwarning("Attention", "Sélectionnez d'abord un fournisseur.")
            return
        mag = self.combo_magasin.get()
        if not mag or mag not in self.magasins:
            messagebox.showwarning("Attention", "Sélectionnez un magasin.")
            return

        try:
            qt = self._parse(self.entry_qtlivree.get())
            pu = self._parse(self.entry_prix_unit.get())
        except Exception:
            messagebox.showerror("Erreur", "Quantité ou prix invalide.")
            return

        if qt <= 0:
            messagebox.showwarning("Attention", "La quantité livrée doit être > 0.")
            return

        montant    = qt * pu
        date_per   = (self.cal_peremption.get_date().strftime('%d/%m/%Y')
                      if self.var_peremption.get() else "")
        a_payer    = 1 if self.var_a_payer.get() else 0

        self.tree.insert("", "end", values=(
            self.article_selectionne['nomart'],
            self.article_selectionne['unite'],
            self._fmt(qt),
            self._fmt(pu),
            self._fmt(montant),
            date_per,
            "Oui" if a_payer else "Non"
        ))
        self._refresh_alt_colors(self.tree)

        self.items_reception.append({
            'idarticle':     self.article_selectionne['idarticle'],
            'idunite':       self.article_selectionne['idunite'],
            'nomart':        self.article_selectionne['nomart'],
            'unite':         self.article_selectionne['unite'],
            'qtlivrefrs':    qt,
            'prixunit':      pu,
            'montant':       montant,
            'dateperemption': date_per or None,
            'a_payer':        a_payer,
        })

        self._vider_champs_article()
        self._calc_total()

    # =========================================================================
    # SÉLECTION / MODIFICATION / SUPPRESSION
    # =========================================================================
    def _on_select(self, event=None):
        pass  # sélection simple — pas d'action automatique

    def _on_double_click(self, event=None):
        sel = self.tree.selection()
        if sel:
            self._charger_ligne_modif(self.tree.index(sel[0]))

    def _modifier_ligne_selectionnee(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Attention", "Sélectionnez une ligne à modifier.")
            return
        self._charger_ligne_modif(self.tree.index(sel[0]))

    def _charger_ligne_modif(self, idx: int):
        if idx >= len(self.items_reception):
            return
        self.index_modif = idx
        item = self.items_reception[idx]

        # Remplir champs
        self.article_selectionne = {
            'idarticle': item['idarticle'],
            'idunite':   item['idunite'],
            'nomart':    item['nomart'],
            'unite':     item['unite'],
        }
        self.entry_article.configure(state="normal")
        self.entry_article.delete(0, "end")
        self.entry_article.insert(0, item['nomart'])
        self.entry_article.configure(state="readonly")

        self.entry_unite.configure(state="normal")
        self.entry_unite.delete(0, "end")
        self.entry_unite.insert(0, item['unite'])
        self.entry_unite.configure(state="readonly")

        self.entry_qtlivree.delete(0, "end")
        self.entry_qtlivree.insert(0, self._fmt(item['qtlivrefrs']))
        self.entry_prix_unit.delete(0, "end")
        self.entry_prix_unit.insert(0, self._fmt(item['prixunit']))
        self._recalc_montant()

        # Péremption
        dp = item.get('dateperemption')
        if dp:
            self.var_peremption.set(True)
            self._toggle_peremption()
            try:
                p = dp.split('/')
                self.cal_peremption.set_date(
                    datetime(int(p[2]), int(p[1]), int(p[0])))
            except Exception:
                pass
        else:
            self.var_peremption.set(False)
            self._toggle_peremption()

        self.var_a_payer.set(bool(item.get('a_payer', 1)))

        # Basculer boutons
        self.btn_ajouter.configure(state="disabled")
        self.btn_valider_modif.configure(state="normal")
        self.btn_annuler_modif.configure(state="normal")
        self.lbl_titre.configure(text=f"⚠️  Modification ligne {idx + 1}")

    def _valider_modification(self):
        if self.index_modif is None:
            return
        try:
            qt = self._parse(self.entry_qtlivree.get())
            pu = self._parse(self.entry_prix_unit.get())
        except Exception:
            messagebox.showerror("Erreur", "Quantité ou prix invalide.")
            return
        if qt <= 0:
            messagebox.showwarning("Attention", "La quantité livrée doit être > 0.")
            return

        montant  = qt * pu
        date_per = (self.cal_peremption.get_date().strftime('%d/%m/%Y')
                    if self.var_peremption.get() else "")
        a_payer  = 1 if self.var_a_payer.get() else 0
        idx      = self.index_modif

        self.items_reception[idx].update({
            'qtlivrefrs':     qt,
            'prixunit':       pu,
            'montant':        montant,
            'dateperemption': date_per or None,
            'a_payer':        a_payer,
        })

        item_id = self.tree.get_children()[idx]
        self.tree.item(item_id, values=(
            self.items_reception[idx]['nomart'],
            self.items_reception[idx]['unite'],
            self._fmt(qt),
            self._fmt(pu),
            self._fmt(montant),
            date_per,
            "Oui" if a_payer else "Non"
        ))
        self._refresh_alt_colors(self.tree)
        self._annuler_modif()
        self._calc_total()
        messagebox.showinfo("Succès", "Ligne modifiée avec succès !")

    def _annuler_modif(self):
        self.index_modif = None
        self._vider_champs_article()
        self.btn_ajouter.configure(state="normal")
        self.btn_valider_modif.configure(state="disabled")
        self.btn_annuler_modif.configure(state="disabled")
        self.tree.selection_remove(self.tree.selection())
        self.lbl_titre.configure(text="📦  Nouvelle Réception Directe")

    def _supprimer_ligne(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Attention", "Sélectionnez une ligne à supprimer.")
            return
        if self.index_modif is not None:
            self._annuler_modif()
        idx = self.tree.index(sel[0])
        self.tree.delete(sel[0])
        self._refresh_alt_colors(self.tree)
        self.items_reception.pop(idx)
        self._calc_total()

    # =========================================================================
    # TOTAL
    # =========================================================================
    def _calc_total(self):
        total = sum(i['montant'] for i in self.items_reception)
        txt = f"Total : {self._fmt(total)}"
        self.lbl_total_global.configure(text=txt)
        self.lbl_total_bas.configure(text=txt)

    # =========================================================================
    # VIDER CHAMPS ARTICLE
    # =========================================================================
    def _vider_champs_article(self):
        self.article_selectionne = None
        for e in (self.entry_article, self.entry_unite):
            e.configure(state="normal")
            e.delete(0, "end")
            e.configure(state="readonly")
        self.entry_qtlivree.delete(0, "end")
        self.entry_prix_unit.delete(0, "end")
        self.lbl_montant_ligne.configure(text="0,00")
        self.var_peremption.set(False)
        self._toggle_peremption()

    # =========================================================================
    # ENREGISTREMENT
    # =========================================================================
    def _enregistrer(self):
        # ── Validations ──────────────────────────────────────────────────────
        if self.index_modif is not None:
            messagebox.showwarning("Attention",
                                   "Validez ou annulez la modification en cours.")
            return
        if not self.items_reception:
            messagebox.showwarning("Attention",
                                   "Ajoutez au moins une ligne avant d'enregistrer.")
            return
        if not self.fournisseur_id:
            messagebox.showwarning("Attention", "Sélectionnez un fournisseur.")
            return
        mag_nom = self.combo_magasin.get()
        if not mag_nom or mag_nom not in self.magasins:
            messagebox.showwarning("Attention", "Sélectionnez un magasin.")
            return

        refbr   = self.entry_ref.get().strip()
        factfrs = self.entry_factfrs.get().strip() or None
        idmag   = self.magasins[mag_nom]
        date_rec = self.date_reception.get_date()

        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()

            for item in self.items_reception:
                dp = self._format_date_db(item.get('dateperemption'))
                cur.execute("""
                    INSERT INTO tb_livraisonfrs
                        (reflivfrs, idcom, idarticle, idunite, qtlivrefrs,
                         dateregistre, typemouvement, idmag, factfrs,
                         iduser, dateperemption, a_payer)
                    VALUES (%s, %s, %s, %s, %s, %s, 1, %s, %s, %s, %s, %s)
                """, (
                    refbr,
                    None,                       # idcom = NULL (réception directe)
                    item['idarticle'],
                    item['idunite'],
                    item['qtlivrefrs'],
                    date_rec,
                    idmag,
                    factfrs,
                    self.iduser,
                    dp,
                    item['a_payer'],
                ))

            conn.commit()
            messagebox.showinfo(
                "Succès",
                f"Bon de Réception {refbr} enregistré avec succès !\n"
                f"{len(self.items_reception)} ligne(s) insérée(s)."
            )
            # ── Proposition d'impression ──────────────────────────────────────
            self._imprimer_pdf(refbr=refbr)
            self._nouveau()

        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur", f"Enregistrement : {e}")
        finally:
            if 'cur' in locals():
                cur.close()
            conn.close()

    # =========================================================================
    # IMPRESSION PDF A5
    # =========================================================================
    def _imprimer_pdf(self, refbr=None):
        """Génère et ouvre un Bon de Réception au format A5."""
        if not self.items_reception:
            messagebox.showwarning("Attention",
                                   "Aucune ligne à imprimer.")
            return

        if refbr is None:
            refbr = self.entry_ref.get().strip()

        # ── Récupération infos société + utilisateur ──────────────────────────
        info_soc  = {}
        nom_user  = ""
        conn = self.connect_db()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("""
                    SELECT nomsociete, adressesociete, contactsociete,
                           villesociete, nifsociete, statsociete, cifsociete
                    FROM tb_infosociete LIMIT 1
                """)
                row = cur.fetchone()
                if row:
                    info_soc = {
                        'nom':    row[0] or '',
                        'adresse': row[1] or '',
                        'tel':    row[2] or '',
                        'ville':  row[3] or '',
                        'nif':    row[4] or '',
                        'stat':   row[5] or '',
                        'cif':    row[6] or '',
                    }
                cur.execute(
                    "SELECT nomuser, prenomuser FROM tb_users WHERE iduser = %s",
                    (self.iduser,)
                )
                u = cur.fetchone()
                if u:
                    nom_user = f"{u[1]} {u[0]}".strip()
            except Exception:
                pass
            finally:
                try:
                    cur.close()
                except Exception:
                    pass
                conn.close()

        # ── Préparation fichier ───────────────────────────────────────────────
        filename = os.path.join(
            tempfile.gettempdir(),
            f"BR_{refbr.replace('-', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )

        # ── Styles ───────────────────────────────────────────────────────────
        styles = getSampleStyleSheet()
        s_center = ParagraphStyle('center', parent=styles['Normal'],
                                  alignment=TA_CENTER, fontSize=8, leading=10)
        s_normal = ParagraphStyle('normal', parent=styles['Normal'],
                                  fontSize=8, leading=10)
        s_bold   = ParagraphStyle('bold',   parent=styles['Normal'],
                                  fontSize=8, leading=10, fontName='Helvetica-Bold')
        s_title  = ParagraphStyle('title',  parent=styles['Normal'],
                                  alignment=TA_CENTER, fontSize=13, leading=16,
                                  fontName='Helvetica-Bold')
        s_small  = ParagraphStyle('small',  parent=styles['Normal'],
                                  alignment=TA_CENTER, fontSize=7, leading=9,
                                  textColor=rl_colors.HexColor('#555555'))
        s_right  = ParagraphStyle('right',  parent=styles['Normal'],
                                  alignment=TA_RIGHT, fontSize=8, leading=10)

        # ── Couleur entête tableau ────────────────────────────────────────────
        HDR_COLOR = rl_colors.HexColor('#2C3E50')
        ALT_COLOR = rl_colors.HexColor('#F3F7FF')
        BORDER    = rl_colors.HexColor('#BDC3C7')

        doc = SimpleDocTemplate(
            filename,
            pagesize=A5,
            leftMargin=12 * mm, rightMargin=12 * mm,
            topMargin=10 * mm, bottomMargin=10 * mm,
        )
        W = A5[0] - 24 * mm   # largeur utile

        elems = []

        # ── En-tête société ───────────────────────────────────────────────────
        nom_soc = info_soc.get('nom', 'NOM SOCIÉTÉ').upper()
        elems.append(Paragraph(f"<b>{nom_soc}</b>", s_center))
        elems.append(Paragraph(
            f"{info_soc.get('adresse', '')} — {info_soc.get('ville', '')}",
            s_center))
        elems.append(Paragraph(
            f"Tél : {info_soc.get('tel', '')}",
            s_center))
        elems.append(Paragraph(
            f"NIF : {info_soc.get('nif', '')}  |  "
            f"STAT : {info_soc.get('stat', '')}  |  "
            f"CIF : {info_soc.get('cif', '')}",
            s_small))

        elems.append(Spacer(1, 4 * mm))

        # Ligne de séparation
        elems.append(Table(
            [['']],
            colWidths=[W],
            style=TableStyle([
                ('LINEBELOW', (0, 0), (-1, -1), 1, HDR_COLOR),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ])
        ))
        elems.append(Spacer(1, 3 * mm))

        # ── Titre ─────────────────────────────────────────────────────────────
        elems.append(Paragraph("BON DE RÉCEPTION DIRECT", s_title))
        elems.append(Spacer(1, 4 * mm))

        # ── Infos BR (2 colonnes) ─────────────────────────────────────────────
        date_str = self.date_reception.get_date().strftime('%d/%m/%Y')
        factfrs  = self.entry_factfrs.get().strip() or '—'
        mag_nom  = self.combo_magasin.get() or '—'
        frs_nom  = self.entry_fournisseur.get() or '—'

        info_data = [
            [Paragraph(f"<b>N° BR :</b> {refbr}", s_normal),
             Paragraph(f"<b>Date :</b> {date_str}", s_normal)],
            [Paragraph(f"<b>Fournisseur :</b> {frs_nom}", s_normal),
             Paragraph(f"<b>Magasin :</b> {mag_nom}", s_normal)],
            [Paragraph(f"<b>N° Facture frs :</b> {factfrs}", s_normal),
             Paragraph(f"<b>Établi par :</b> {nom_user}", s_normal)],
        ]
        tbl_info = Table(info_data, colWidths=[W * 0.55, W * 0.45])
        tbl_info.setStyle(TableStyle([
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING',    (0, 0), (-1, -1), 2),
            ('GRID',          (0, 0), (-1, -1), 0.3, BORDER),
            ('BACKGROUND',    (0, 0), (-1, -1), rl_colors.HexColor('#F9FAFB')),
        ]))
        elems.append(tbl_info)
        elems.append(Spacer(1, 4 * mm))

        # ── Tableau articles ──────────────────────────────────────────────────
        col_labels = ['#', 'Article', 'Unité', 'Qté', 'Prix Unit.', 'Montant']
        col_w = [
            8  * mm,   # #
            W - 8*mm - 18*mm - 16*mm - 22*mm - 22*mm,  # Article (dynamique)
            18 * mm,   # Unité
            16 * mm,   # Qté
            22 * mm,   # Prix unit
            22 * mm,   # Montant
        ]

        tbl_data = [[Paragraph(f"<b>{h}</b>", s_center) for h in col_labels]]
        total_general = 0.0

        for idx, item in enumerate(self.items_reception):
            montant = item['montant']
            total_general += montant
            bg = ALT_COLOR if idx % 2 == 1 else rl_colors.white
            row = [
                Paragraph(str(idx + 1), s_center),
                Paragraph(str(item['nomart']), s_normal),
                Paragraph(str(item['unite']), s_center),
                Paragraph(self._fmt(item['qtlivrefrs']), s_right),
                Paragraph(self._fmt(item['prixunit']), s_right),
                Paragraph(self._fmt(montant), s_right),
            ]
            tbl_data.append(row)

        # Ligne total
        tbl_data.append([
            Paragraph('', s_normal),
            Paragraph('', s_normal),
            Paragraph('', s_normal),
            Paragraph('', s_normal),
            Paragraph('<b>TOTAL</b>', s_right),
            Paragraph(f'<b>{self._fmt(total_general)}</b>', s_right),
        ])

        tbl_articles = Table(tbl_data, colWidths=col_w, repeatRows=1)

        # Style dynamique avec couleurs alternées par ligne
        ts = [
            # En-tête
            ('BACKGROUND',    (0, 0), (-1, 0),  HDR_COLOR),
            ('TEXTCOLOR',     (0, 0), (-1, 0),  rl_colors.white),
            ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
            ('FONTSIZE',      (0, 0), (-1, 0),  8),
            ('ROWBACKGROUND', (0, 1), (-1, -2),
             [rl_colors.white, ALT_COLOR]),
            # Ligne total
            ('BACKGROUND',    (0, -1), (-1, -1), rl_colors.HexColor('#ECF0F1')),
            ('FONTNAME',      (4, -1), (-1, -1), 'Helvetica-Bold'),
            # Bordures
            ('GRID',          (0, 0), (-1, -2),  0.4, BORDER),
            ('LINEABOVE',     (0, -1), (-1, -1),  1,   HDR_COLOR),
            # Padding
            ('TOPPADDING',    (0, 0), (-1, -1),  2),
            ('BOTTOMPADDING', (0, 0), (-1, -1),  2),
            ('LEFTPADDING',   (0, 0), (-1, -1),  3),
            ('RIGHTPADDING',  (0, 0), (-1, -1),  3),
            ('VALIGN',        (0, 0), (-1, -1),  'MIDDLE'),
        ]
        tbl_articles.setStyle(TableStyle(ts))
        elems.append(tbl_articles)
        elems.append(Spacer(1, 5 * mm))

        # ── Montant en lettres ────────────────────────────────────────────────
        try:
            from num2words import num2words
            lettres = num2words(int(total_general), lang='fr').capitalize() + " Ariary"
            if int((total_general - int(total_general)) * 100) > 0:
                lettres += f" et {int((total_general - int(total_general)) * 100):02d} centimes"
        except Exception:
            lettres = f"Montant : {self._fmt(total_general)} Ariary"

        elems.append(Paragraph(
            f"<i>Arrêté le présent bon à la somme de : <b>{lettres}</b></i>",
            s_normal
        ))
        elems.append(Spacer(1, 8 * mm))

        # ── Signatures ───────────────────────────────────────────────────────
        sig_data = [[
            Paragraph('<b>Le Responsable</b>', s_center),
            Paragraph('<b>Le Fournisseur</b>', s_center),
        ], [
            Paragraph('<br/><br/>___________________', s_center),
            Paragraph('<br/><br/>___________________', s_center),
        ]]
        tbl_sig = Table(sig_data, colWidths=[W / 2, W / 2])
        tbl_sig.setStyle(TableStyle([
            ('ALIGN',   (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN',  (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE',(0, 0), (-1, -1), 9),
        ]))
        elems.append(tbl_sig)

        # ── Build et ouverture ────────────────────────────────────────────────
        try:
            doc.build(elems)
            self._ouvrir_fichier(filename)
        except Exception as e:
            messagebox.showerror("Erreur PDF",
                                 f"Impossible de générer le PDF :\n{e}")

    def _ouvrir_fichier(self, path: str):
        """Ouvre un fichier avec l'application par défaut du système."""
        try:
            if os.name == 'nt':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.call(['open', path])
            else:
                subprocess.call(['xdg-open', path])
        except Exception as e:
            messagebox.showwarning("Ouverture", f"PDF généré mais impossible de l'ouvrir :\n{e}")

    # =========================================================================
    # RÉINITIALISATION
    # =========================================================================
    def _nouveau(self):
        self.items_reception.clear()
        self.index_modif         = None
        self.article_selectionne = None
        self.fournisseur_id      = None
        self.fournisseur_nom     = ""

        # Vider tableau
        for i in self.tree.get_children():
            self.tree.delete(i)

        # Vider fournisseur
        self.entry_fournisseur.configure(state="normal")
        self.entry_fournisseur.delete(0, "end")
        self.entry_fournisseur.configure(state="readonly")

        # Vider fact frs
        self.entry_factfrs.delete(0, "end")

        # Vider champs article
        self._vider_champs_article()

        # Réinitialiser date
        self.date_reception.set_date(date.today())

        # Réinitialiser boutons
        self.btn_ajouter.configure(state="normal")
        self.btn_valider_modif.configure(state="disabled")
        self.btn_annuler_modif.configure(state="disabled")

        self._calc_total()
        self.lbl_titre.configure(text="📦  Nouvelle Réception Directe")

        # Nouveau N° BR
        self._generer_reference()


# ─────────────────────────────────────────────────────────────────────────────
# Test autonome
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from app_theme import init_theme
    init_theme()
    app = ctk.CTk()
    app.geometry("1280x820")
    app.title("Réception Directe — iJeery")
    Theme.apply(app)
    page = PageReceptionDirecte(app, iduser=1)
    page.pack(fill="both", expand=True)
    app.mainloop()