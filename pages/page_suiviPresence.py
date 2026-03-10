# -*- coding: utf-8 -*-
"""
PageSuiviPresence — Refonte UI complète
Thème   : iJeery (app_theme.py)
Onglets : style navigateur Chrome (canvas custom)
Statuts : icônes colorées (⬤ vert/orange/rouge/gris)
"""

import json
from datetime import datetime, date

import psycopg2
import pandas as pd
import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog

from resource_utils import get_config_path
from app_theme import Colors, Fonts, Theme, styled, Layout


# ─────────────────────────────────────────────────────────────────────────────
# DB Manager
# ─────────────────────────────────────────────────────────────────────────────

class DatabaseManager:
    def __init__(self):
        self.db_params = self._load_db_config()
        self.conn   = None
        self.cursor = None

    def _load_db_config(self):
        try:
            with open(get_config_path("config.json"), "r", encoding="utf-8") as f:
                return json.load(f)["database"]
        except Exception as e:
            print(f"Erreur config : {e}")
            return None

    def connect(self):
        if not self.db_params:
            return False
        try:
            self.conn   = psycopg2.connect(**self.db_params)
            self.cursor = self.conn.cursor()
            return True
        except Exception as e:
            print(f"Erreur connexion : {e}")
            return False

    def get_cursor(self):
        if self.cursor is None or self.conn.closed:
            self.connect()
        return self.cursor

    def close_connection(self):
        if self.cursor: self.cursor.close()
        if self.conn:   self.conn.close()


db_manager = DatabaseManager()


# ─────────────────────────────────────────────────────────────────────────────
# Constantes de statuts
# ─────────────────────────────────────────────────────────────────────────────

STATE_ORDER = ["en_attente", "present", "retard", "absent"]

# Icône ronde unicode + couleur texte pour Treeview
STATE_ICON = {
    "en_attente": "⬤",
    "present":    "⬤",
    "retard":     "⬤",
    "absent":     "⬤",
}
STATE_DISPLAY = {
    "en_attente": "⬤  En attente",
    "present":    "⬤  Présent",
    "retard":     "⬤  Retard",
    "absent":     "⬤  Absent",
}
# Couleurs tags Treeview par statut
STATE_COLORS = {
    "en_attente": ("#95A5A6", Colors.TEXT_PRIMARY),   # gris / texte normal
    "present":    ("#2ECC71", "#1A5C30"),              # vert
    "retard":     ("#F39C12", "#7D5000"),              # orange
    "absent":     ("#E74C3C", "#7B241C"),              # rouge
}
ICON_ONLY = {
    "en_attente": "⬤",
    "present":    "⬤",
    "retard":     "⬤",
    "absent":     "⬤",
}

LABEL_STATE = {
    "⬤  En attente": "en_attente",
    "⬤  Présent":    "present",
    "⬤  Retard":     "retard",
    "⬤  Absent":     "absent",
}


# ─────────────────────────────────────────────────────────────────────────────
# Onglets style Chrome
# ─────────────────────────────────────────────────────────────────────────────

class ChromeTabs(ctk.CTkFrame):
    """
    Barre d'onglets style navigateur Chrome.
    Chaque onglet est un CTkButton ; l'onglet actif porte un indicateur
    coloré dessiné via un Canvas tkinter (compatible CTk — pas de place(width=…)).
    """

    TAB_W  = 170   # largeur fixe de chaque onglet
    TAB_H  = 42    # hauteur bouton
    IND_H  = 3     # épaisseur de l'indicateur

    def __init__(self, parent, tabs: list, command=None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self._tabs    = tabs
        self._command = command
        self._active  = 0

        # Canvas pour dessiner l'indicateur (hauteur = IND_H, largeur auto)
        total_w = len(tabs) * self.TAB_W
        self._canvas = ctk.CTkCanvas(
            self,
            height=self.IND_H,
            width=total_w,
            bg=Colors.BG_PAGE,
            highlightthickness=0,
        )

        self._build()

    # ── Construction ─────────────────────────────────────────────────────────

    def _build(self):
        # Détruire uniquement les boutons/séparateurs (pas le canvas)
        for w in self.winfo_children():
            if w is not self._canvas:
                w.destroy()

        btn_row = ctk.CTkFrame(self, fg_color="transparent", height=self.TAB_H)
        btn_row.pack(side="top", fill="x")
        btn_row.pack_propagate(False)

        for i, label in enumerate(self._tabs):
            active = (i == self._active)
            icon   = ("📋 " if label == "Suivi du jour" else "📊 ") if len(label) < 20 else ""
            btn = ctk.CTkButton(
                btn_row,
                text=f"{icon}{label}",
                font=Fonts.bold(13)  if active else Fonts.body(13),
                fg_color=Colors.BG_CARD   if active else Colors.BG_PAGE,
                text_color=Colors.PRIMARY if active else Colors.TEXT_SECONDARY,
                hover_color=Colors.BG_CARD,
                corner_radius=0,
                height=self.TAB_H,
                width=self.TAB_W,
                border_width=0,
                command=lambda idx=i: self._select(idx),
            )
            btn.pack(side="left")

            # Séparateur léger entre onglets
            if i < len(self._tabs) - 1:
                ctk.CTkFrame(
                    btn_row, width=1, height=22,
                    fg_color=Colors.BORDER
                ).pack(side="left", pady=10)

        # Indicateur dessiné sur canvas
        self._canvas.pack(side="top", fill="x")
        self._draw_indicator()

    def _draw_indicator(self):
        self._canvas.delete("indicator")
        x0 = self._active * self.TAB_W
        x1 = x0 + self.TAB_W
        self._canvas.create_rectangle(
            x0, 0, x1, self.IND_H,
            fill=Colors.PRIMARY, outline="",
            tags="indicator"
        )

    def _select(self, idx):
        self._active = idx
        self._build()
        if self._command:
            self._command(self._tabs[idx])

    def set(self, tab_name):
        if tab_name in self._tabs:
            self._active = self._tabs.index(tab_name)
            self._build()

    @property
    def active_tab(self):
        return self._tabs[self._active]


# ─────────────────────────────────────────────────────────────────────────────
# Styles Treeview partagés
# ─────────────────────────────────────────────────────────────────────────────

def _apply_treeview_style(name="Presence.Treeview"):
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        name,
        background=Colors.BG_CARD,
        foreground=Colors.TEXT_PRIMARY,
        fieldbackground=Colors.BG_CARD,
        rowheight=38,
        font=("Segoe UI", 11),
        borderwidth=0,
    )
    style.configure(
        f"{name}.Heading",
        background=Colors.MIDNIGHT,
        foreground=Colors.TEXT_ON_DARK,
        font=("Segoe UI", 11, "bold"),
        relief="flat",
        padding=(8, 8),
    )
    style.map(name,
              background=[("selected", Colors.PRIMARY_LIGHT)],
              foreground=[("selected", Colors.TEXT_PRIMARY)])
    style.map(f"{name}.Heading",
              background=[("active", Colors.MIDNIGHT_LIGHT)])


# ─────────────────────────────────────────────────────────────────────────────
# PAGE PRINCIPALE
# ─────────────────────────────────────────────────────────────────────────────

class PageSuiviPresence(ctk.CTkFrame):
    def __init__(self, parent, db_conn=None, session_data=None, **kwargs):
        super().__init__(parent, fg_color=Colors.BG_PAGE, **kwargs)
        self.db_conn      = db_conn
        self.session_data = session_data

        if not db_manager.connect():
            ctk.CTkLabel(
                self, text="❌  Erreur de connexion à la base de données",
                text_color=Colors.DANGER, font=Fonts.bold(16)
            ).pack(pady=60)
            return

        self.update_rows_cache = {}
        _apply_treeview_style()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_chrome_tabs()
        self._build_pages()

        # Afficher le 1er onglet
        self._show_tab("Suivi du jour")
        self.load_update_for_date(self.date_update_var.get())
        self.load_history()

    # ── En-tête ──────────────────────────────────────────────────────────────

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT,
                               corner_radius=0, height=60)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)

        # Icône + titre
        title_box = styled.frame(header)
        title_box.grid(row=0, column=0, padx=20, pady=10, sticky="w")
        ctk.CTkLabel(title_box, text="📋", font=Fonts.title(22),
                     text_color=Colors.TEXT_ON_DARK
                     ).pack(side="left", padx=(0, 10))
        info = styled.frame(title_box)
        info.pack(side="left")
        ctk.CTkLabel(info, text="Suivi de Présence",
                     font=Fonts.heading(16),
                     text_color=Colors.TEXT_ON_DARK
                     ).pack(anchor="w")
        ctk.CTkLabel(info, text="Gestion des présences journalières",
                     font=Fonts.small(10),
                     text_color=Colors.TEXT_ON_DARK_DIM
                     ).pack(anchor="w")

        # Date du jour (badge)
        today_str = date.today().strftime("%d %B %Y")
        ctk.CTkLabel(
            header, text=f"📅  {today_str}",
            font=Fonts.body(12), text_color=Colors.TEXT_ON_DARK_DIM
        ).grid(row=0, column=2, padx=20)

    # ── Onglets Chrome ───────────────────────────────────────────────────────

    def _build_chrome_tabs(self):
        tab_bar = ctk.CTkFrame(self, fg_color=Colors.BG_PAGE,
                                corner_radius=0, height=48)
        tab_bar.grid(row=1, column=0, sticky="ew")
        tab_bar.grid_propagate(False)

        # Ligne de séparation sous les tabs
        ctk.CTkFrame(tab_bar, height=1,
                      fg_color=Colors.BORDER
                      ).pack(side="bottom", fill="x")

        self.chrome_tabs = ChromeTabs(
            tab_bar,
            tabs=["Suivi du jour", "Historique"],
            command=self._show_tab
        )
        self.chrome_tabs.pack(side="left", padx=12, pady=(4, 0))

    # ── Pages conteneurs ─────────────────────────────────────────────────────

    def _build_pages(self):
        container = ctk.CTkFrame(self, fg_color=Colors.BG_PAGE, corner_radius=0)
        container.grid(row=2, column=0, sticky="nsew")
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)
        self._container = container

        # Page "Suivi du jour"
        self._page_update = ctk.CTkFrame(container, fg_color=Colors.BG_PAGE)
        self._page_update.grid_columnconfigure(0, weight=1)
        self._page_update.grid_rowconfigure(2, weight=1)
        self._build_update_page(self._page_update)

        # Page "Historique"
        self._page_history = ctk.CTkFrame(container, fg_color=Colors.BG_PAGE)
        self._page_history.grid_columnconfigure(0, weight=1)
        self._page_history.grid_rowconfigure(1, weight=1)
        self._build_history_page(self._page_history)

    def _show_tab(self, tab_name):
        self.chrome_tabs.set(tab_name)
        if tab_name == "Suivi du jour":
            self._page_history.grid_remove()
            self._page_update.grid(row=0, column=0, sticky="nsew")
        else:
            self._page_update.grid_remove()
            self._page_history.grid(row=0, column=0, sticky="nsew")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — SUIVI DU JOUR
    # ══════════════════════════════════════════════════════════════════════════

    def _build_update_page(self, parent):
        # ── Barre d'outils ────────────────────────────────────────────────
        toolbar = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD,
                                corner_radius=Layout.RADIUS)
        toolbar.grid(row=0, column=0, padx=12, pady=(10, 6), sticky="ew")
        toolbar.grid_columnconfigure(5, weight=1)

        # Date
        ctk.CTkLabel(toolbar, text="📅  Date :", font=Fonts.body(13),
                     text_color=Colors.TEXT_SECONDARY
                     ).grid(row=0, column=0, padx=(16, 6), pady=12, sticky="w")

        self.date_update_var = ctk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        self.date_update_entry = styled.entry(toolbar, height=36, width=148)
        self.date_update_entry.insert(0, self.date_update_var.get())
        self.date_update_entry.grid(row=0, column=1, padx=(0, 8), pady=12, sticky="w")

        styled.button_primary(
            toolbar, text="Charger", icon="🔄",
            command=self.on_update_load, width=110, height=36
        ).grid(row=0, column=2, padx=(0, 20), pady=12, sticky="w")

        # Filtre statut
        ctk.CTkLabel(toolbar, text="Statut :", font=Fonts.body(12),
                     text_color=Colors.TEXT_SECONDARY
                     ).grid(row=0, column=3, padx=(0, 6), pady=12, sticky="w")
        self.combo_filter_statut = ctk.CTkComboBox(
            toolbar,
            values=["Tous", "En attente", "Present", "Retard", "Absent"],
            state="readonly",
            width=140, height=36,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            button_color=Colors.PRIMARY, font=Fonts.body(12),
            command=lambda v: self._apply_update_filter(),
        )
        self.combo_filter_statut.set("Tous")
        self.combo_filter_statut.grid(row=0, column=4, padx=(0, 8), pady=12, sticky="w")

        # Boutons droite
        btn_right = styled.frame(toolbar)
        btn_right.grid(row=0, column=6, padx=16, pady=12, sticky="e")

        styled.button_success(
            btn_right, text="Sauvegarder", icon="💾",
            command=self.save_update, width=140, height=36
        ).pack(side="left", padx=(0, 8))

        styled.button_premium(
            btn_right, text="Exporter Excel", icon="📊",
            command=self.export_update_excel, width=150, height=36
        ).pack(side="left")

        # ── Légende — badges colorés ──────────────────────────────────────
        legend = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD,
                               corner_radius=Layout.RADIUS, height=48)
        legend.grid(row=1, column=0, padx=12, pady=(0, 6), sticky="ew")
        legend.grid_propagate(False)

        ctk.CTkLabel(legend, text="Légende :",
                     font=Fonts.bold(11), text_color=Colors.TEXT_SECONDARY
                     ).pack(side="left", padx=(16, 10))

        badge_defs = [
            ("⬤  En attente", Colors.TEXT_MUTED,  Colors.BG_INPUT),
            ("⬤  Présent",    Colors.SUCCESS_TEXT, Colors.SUCCESS_LIGHT),
            ("⬤  Retard",     Colors.WARNING_TEXT, Colors.WARNING_LIGHT),
            ("⬤  Absent",     Colors.DANGER_TEXT,  Colors.DANGER_LIGHT),
        ]
        for text, fg, bg in badge_defs:
            ctk.CTkLabel(
                legend, text=f"  {text}  ",
                font=Fonts.badge(11),
                text_color=fg, fg_color=bg,
                corner_radius=6,
            ).pack(side="left", padx=4)

        ctk.CTkLabel(legend,
                     text="💡 Double-clic sur Matin / Après-midi pour changer le statut",
                     font=Fonts.small(10), text_color=Colors.TEXT_MUTED
                     ).pack(side="right", padx=16)

        # ── Tableau ───────────────────────────────────────────────────────
        table_card = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD,
                                   corner_radius=Layout.RADIUS)
        table_card.grid(row=2, column=0, padx=12, pady=(0, 6), sticky="nsew")
        table_card.grid_columnconfigure(0, weight=1)
        table_card.grid_rowconfigure(0, weight=1)

        cols = ("ID", "Nom complet", "Sexe", "Fonction",
                "Matin", "Après-midi", "Observation")
        self.update_tree = ttk.Treeview(
            table_card, columns=cols, show="headings",
            style="Presence.Treeview", selectmode="browse"
        )
        col_w = {
            "ID": (45, "center"),
            "Nom complet": (180, "w"),
            "Sexe": (60, "center"),
            "Fonction": (150, "w"),
            "Matin": (120, "center"),
            "Après-midi": (120, "center"),
            "Observation": (200, "w"),
        }
        for col, (w, anchor) in col_w.items():
            self.update_tree.heading(col, text=col)
            self.update_tree.column(col, width=w, anchor=anchor, minwidth=40)

        # Tags de couleur pour statuts dans la colonne Matin / ApresMidi
        for state, (fg_color, txt_color) in STATE_COLORS.items():
            self.update_tree.tag_configure(
                f"matin_{state}",   foreground=fg_color)
            self.update_tree.tag_configure(
                f"aprem_{state}",   foreground=fg_color)

        self.update_tree.tag_configure("even", background=Colors.BG_CARD)
        self.update_tree.tag_configure("odd",  background=Colors.BG_ROW_ALT)

        vsb = ttk.Scrollbar(table_card, orient="vertical",
                             command=self.update_tree.yview)
        hsb = ttk.Scrollbar(table_card, orient="horizontal",
                             command=self.update_tree.xview)
        self.update_tree.configure(yscrollcommand=vsb.set,
                                    xscrollcommand=hsb.set)

        self.update_tree.grid(row=0, column=0, sticky="nsew",
                               padx=(8, 0), pady=8)
        vsb.grid(row=0, column=1, sticky="ns", pady=8)
        hsb.grid(row=1, column=0, sticky="ew", padx=(8, 0))

        self.update_tree.bind("<Double-1>", self.on_update_double_click)
        self._all_update_rows = []   # cache pour filtre côté client

        # ── Résumé ────────────────────────────────────────────────────────
        summary = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD,
                                corner_radius=Layout.RADIUS, height=48)
        summary.grid(row=3, column=0, padx=12, pady=(0, 10), sticky="ew")
        summary.grid_propagate(False)

        self._stat_cards = {}
        stat_defs = [
            ("present",    "✅  Présents",    Colors.SUCCESS,  Colors.SUCCESS_LIGHT),
            ("retard",     "🟠  Retards",     Colors.WARNING,  Colors.WARNING_LIGHT),
            ("absent",     "🔴  Absents",     Colors.DANGER,   Colors.DANGER_LIGHT),
            ("en_attente", "⬜  En attente",  Colors.TEXT_MUTED, Colors.BG_INPUT),
        ]
        for key, label, fg, bg in stat_defs:
            card = ctk.CTkFrame(summary, fg_color=bg,
                                 corner_radius=8, width=150)
            card.pack(side="left", padx=(12, 0), pady=8, fill="y")
            card.pack_propagate(False)
            ctk.CTkLabel(card, text=label, font=Fonts.small(10),
                         text_color=fg, anchor="w"
                         ).pack(side="left", padx=(10, 4))
            lbl = ctk.CTkLabel(card, text="0", font=Fonts.bold(14),
                                text_color=fg)
            lbl.pack(side="left", padx=(0, 10))
            self._stat_cards[key] = lbl

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — HISTORIQUE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_history_page(self, parent):
        # ── Filtres ───────────────────────────────────────────────────────
        filter_card = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD,
                                    corner_radius=Layout.RADIUS)
        filter_card.grid(row=0, column=0, padx=12, pady=(10, 6), sticky="ew")
        filter_card.grid_columnconfigure(5, weight=1)

        ctk.CTkLabel(filter_card, text="📅  Date début :",
                     font=Fonts.body(13), text_color=Colors.TEXT_SECONDARY
                     ).grid(row=0, column=0, padx=(16, 6), pady=12, sticky="w")

        self.history_from_var = ctk.StringVar()
        self.h_from_entry = styled.entry(filter_card, height=36, width=140,
                                          placeholder="YYYY-MM-DD")
        self.h_from_entry.grid(row=0, column=1, padx=(0, 16), pady=12, sticky="w")

        ctk.CTkLabel(filter_card, text="Date fin :",
                     font=Fonts.body(13), text_color=Colors.TEXT_SECONDARY
                     ).grid(row=0, column=2, padx=(0, 6), pady=12, sticky="w")

        self.history_to_var = ctk.StringVar()
        self.h_to_entry = styled.entry(filter_card, height=36, width=140,
                                        placeholder="YYYY-MM-DD")
        self.h_to_entry.grid(row=0, column=3, padx=(0, 16), pady=12, sticky="w")

        styled.button_primary(
            filter_card, text="Filtrer", icon="🔍",
            command=self.load_history, width=110, height=36
        ).grid(row=0, column=4, padx=(0, 8), pady=12, sticky="w")

        styled.button_secondary(
            filter_card, text="Aujourd'hui", icon="📅",
            command=self._history_today, width=120, height=36
        ).grid(row=0, column=5, padx=(0, 8), pady=12, sticky="w")

        styled.button_premium(
            filter_card, text="Exporter Excel", icon="📊",
            command=self.export_history_excel, width=150, height=36
        ).grid(row=0, column=7, padx=(0, 16), pady=12, sticky="e")

        # ── Tableau historique ────────────────────────────────────────────
        table_card = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD,
                                   corner_radius=Layout.RADIUS)
        table_card.grid(row=1, column=0, padx=12, pady=(0, 10), sticky="nsew")
        table_card.grid_columnconfigure(0, weight=1)
        table_card.grid_rowconfigure(0, weight=1)

        cols = ("ID", "Nom complet", "Sexe", "Fonction",
                "✅ Présent", "🟠 Retard", "🔴 Absent", "⬜ En attente")
        self.history_tree = ttk.Treeview(
            table_card, columns=cols, show="headings",
            style="Presence.Treeview", selectmode="browse"
        )
        col_w_h = {
            "ID": (45, "center"),
            "Nom complet": (180, "w"),
            "Sexe": (60, "center"),
            "Fonction": (150, "w"),
            "✅ Présent": (100, "center"),
            "🟠 Retard": (100, "center"),
            "🔴 Absent": (100, "center"),
            "⬜ En attente": (110, "center"),
        }
        for col, (w, anchor) in col_w_h.items():
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=w, anchor=anchor, minwidth=40)

        self.history_tree.tag_configure("even", background=Colors.BG_CARD)
        self.history_tree.tag_configure("odd",  background=Colors.BG_ROW_ALT)

        vsb_h = ttk.Scrollbar(table_card, orient="vertical",
                               command=self.history_tree.yview)
        hsb_h = ttk.Scrollbar(table_card, orient="horizontal",
                               command=self.history_tree.xview)
        self.history_tree.configure(yscrollcommand=vsb_h.set,
                                     xscrollcommand=hsb_h.set)

        self.history_tree.grid(row=0, column=0, sticky="nsew",
                                padx=(8, 0), pady=8)
        vsb_h.grid(row=0, column=1, sticky="ns", pady=8)
        hsb_h.grid(row=1, column=0, sticky="ew", padx=(8, 0))

    # ══════════════════════════════════════════════════════════════════════════
    # LOGIQUE MÉTIER — SUIVI DU JOUR
    # ══════════════════════════════════════════════════════════════════════════

    def on_update_load(self):
        val = self.date_update_entry.get().strip()
        self.date_update_var.set(val)
        self.load_update_for_date(val)

    def _apply_update_filter(self):
        """Filtre la liste affichée selon le statut sélectionné (côté client)."""
        filtre = self.combo_filter_statut.get()
        # Map label combo → clé state
        filtre_map = {
            "En attente": "en_attente",
            "Present":    "present",
            "Retard":     "retard",
            "Absent":     "absent",
        }
        target_state = filtre_map.get(filtre)  # None = "Tous"

        self.update_tree.delete(*self.update_tree.get_children())
        self.update_rows_cache = {}

        count = 0
        for row in self._all_update_rows:
            matin_state = row[4] or "en_attente"
            aprem_state = row[5] or "en_attente"

            if target_state and matin_state != target_state and aprem_state != target_state:
                continue

            tag = "even" if count % 2 == 0 else "odd"
            iid = self.update_tree.insert(
                "", "end", tags=(tag,),
                values=(
                    row[0], row[1].strip(),
                    self._safe(row[2]), self._safe(row[3]),
                    STATE_DISPLAY.get(matin_state, "⬤  En attente"),
                    STATE_DISPLAY.get(aprem_state, "⬤  En attente"),
                    self._safe(row[6]),
                ),
            )
            self.update_rows_cache[iid] = row
            count += 1

        self._update_summary()

    def ensure_presence_day(self, target_date):
        try:
            cursor = db_manager.get_cursor()
            cursor.execute(
                "SELECT id FROM tb_personnel WHERE deleted = 0 ORDER BY nom, prenom"
            )
            personnel_ids = [r[0] for r in cursor.fetchall()]
            cursor.execute(
                "SELECT idpersonnel FROM tb_suivipresence WHERE datepresence = %s",
                (target_date,),
            )
            existing = {r[0] for r in cursor.fetchall()}
            to_insert = [pid for pid in personnel_ids if pid not in existing]
            for pid in to_insert:
                cursor.execute(
                    """INSERT INTO tb_suivipresence
                       (datepresence, idpersonnel, matin, apresmidi, observation, deleted)
                       VALUES (%s, %s, 'en_attente', 'en_attente', '', 0)""",
                    (target_date, pid),
                )
            if to_insert:
                db_manager.conn.commit()
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur création suivi du jour : {e}")

    def load_update_for_date(self, target_date):
        target_date = self._parse_date_or_warn(target_date)
        if not target_date:
            return
        self.ensure_presence_day(target_date)
        self.update_tree.delete(*self.update_tree.get_children())
        self.update_rows_cache = {}

        try:
            cursor = db_manager.get_cursor()
            cursor.execute(
                """
                SELECT p.id,
                       p.nom || ' ' || COALESCE(p.prenom, ''),
                       p.sexe, f.designationfonction,
                       sp.matin, sp.apresmidi, sp.observation
                FROM tb_suivipresence sp
                JOIN tb_personnel p ON sp.idpersonnel = p.id
                LEFT JOIN tb_fonction f ON p.idfonction = f.idfonction
                WHERE sp.datepresence = %s AND sp.deleted = 0
                ORDER BY p.nom, p.prenom
                """,
                (target_date,),
            )
            rows = cursor.fetchall()
            self._all_update_rows = list(rows)
            for idx, row in enumerate(rows):
                matin_state = row[4] or "en_attente"
                aprem_state = row[5] or "en_attente"
                tag = "even" if idx % 2 == 0 else "odd"
                iid = self.update_tree.insert(
                    "", "end", tags=(tag,),
                    values=(
                        row[0],
                        row[1].strip(),
                        self._safe(row[2]),
                        self._safe(row[3]),
                        STATE_DISPLAY.get(matin_state, "⬤  En attente"),
                        STATE_DISPLAY.get(aprem_state, "⬤  En attente"),
                        self._safe(row[6]),
                    ),
                )
                self.update_rows_cache[iid] = row
            self._update_summary()
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur chargement suivi : {e}")

    def on_update_double_click(self, event):
        item   = self.update_tree.identify("item",   event.x, event.y)
        column = self.update_tree.identify_column(event.x)
        if not item or not column:
            return
        col_idx = int(column.replace("#", "")) - 1
        if col_idx in (4, 5):
            self._toggle_state(item, col_idx)
            self._update_summary()
        elif col_idx == 6:
            self._edit_cell(item, col_idx)

    def _toggle_state(self, item, col_idx):
        values        = list(self.update_tree.item(item, "values"))
        current_label = values[col_idx]
        current_state = LABEL_STATE.get(current_label, "en_attente")
        next_idx      = (STATE_ORDER.index(current_state) + 1) % len(STATE_ORDER)
        next_state    = STATE_ORDER[next_idx]
        values[col_idx] = STATE_DISPLAY[next_state]
        self.update_tree.item(item, values=values)

    def _edit_cell(self, item, col_idx):
        bbox = self.update_tree.bbox(item, f"#{col_idx + 1}")
        if not bbox:
            return
        x, y, w, h = bbox
        current = self.update_tree.item(item, "values")[col_idx]
        entry = ctk.CTkEntry(self.update_tree, width=w, height=h,
                              fg_color=Colors.BG_INPUT,
                              font=Fonts.body(12))
        entry.place(x=x, y=y)
        entry.insert(0, "" if current == "-" else current)
        entry.focus_force()

        def save(event=None):
            new_val = entry.get().strip()
            vals = list(self.update_tree.item(item, "values"))
            vals[col_idx] = new_val if new_val else "-"
            self.update_tree.item(item, values=vals)
            entry.destroy()

        entry.bind("<Return>",   save)
        entry.bind("<FocusOut>", save)

    def save_update(self):
        raw = self.date_update_entry.get().strip()
        self.date_update_var.set(raw)
        target_date = self._parse_date_or_warn(raw)
        if not target_date:
            return
        try:
            cursor = db_manager.get_cursor()
            for item in self.update_tree.get_children():
                vals = self.update_tree.item(item, "values")
                idpersonnel = vals[0]
                matin_state = LABEL_STATE.get(vals[4], "en_attente")
                aprem_state = LABEL_STATE.get(vals[5], "en_attente")
                observation = "" if vals[6] == "-" else vals[6]
                cursor.execute(
                    """UPDATE tb_suivipresence
                       SET matin=%s, apresmidi=%s, observation=%s
                       WHERE datepresence=%s AND idpersonnel=%s""",
                    (matin_state, aprem_state, observation, target_date, idpersonnel),
                )
            db_manager.conn.commit()
            messagebox.showinfo("✅  Succès", "Suivi enregistré avec succès.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur sauvegarde : {e}")

    def export_update_excel(self):
        data = [self.update_tree.item(i, "values")
                for i in self.update_tree.get_children()]
        if not data:
            messagebox.showinfo("Info", "Aucune donnée à exporter.")
            return
        df = pd.DataFrame(
            data,
            columns=["ID", "Nom complet", "Sexe", "Fonction",
                     "Matin", "Après-midi", "Observation"],
        )
        path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                             filetypes=[("Excel", "*.xlsx")])
        if path:
            df.to_excel(path, index=False)
            messagebox.showinfo("✅  Succès", "Exportation Excel réussie.")

    def _update_summary(self):
        stats = {"present": 0, "retard": 0, "absent": 0, "en_attente": 0}
        for item in self.update_tree.get_children():
            vals = self.update_tree.item(item, "values")
            for col_val in (vals[4], vals[5]):
                state = LABEL_STATE.get(col_val, "en_attente")
                stats[state] = stats.get(state, 0) + 1

        for key, lbl in self._stat_cards.items():
            lbl.configure(text=str(stats.get(key, 0)))

    # ══════════════════════════════════════════════════════════════════════════
    # LOGIQUE MÉTIER — HISTORIQUE
    # ══════════════════════════════════════════════════════════════════════════

    def _history_today(self):
        today = date.today().strftime("%Y-%m-%d")
        self.h_from_entry.delete(0, "end")
        self.h_from_entry.insert(0, today)
        self.h_to_entry.delete(0, "end")
        self.h_to_entry.insert(0, today)
        self.load_history()

    def load_history(self):
        start = self.h_from_entry.get().strip()
        end   = self.h_to_entry.get().strip()

        if not start or not end:
            today      = date.today()
            start_date = today
            end_date   = today
        else:
            start_date = self._parse_date_or_warn(start)
            end_date   = self._parse_date_or_warn(end)
            if not start_date or not end_date or start_date > end_date:
                messagebox.showwarning("Erreur", "Plage de dates invalide.")
                return

        self.history_tree.delete(*self.history_tree.get_children())

        try:
            cursor = db_manager.get_cursor()
            cursor.execute(
                """SELECT p.id, p.nom || ' ' || COALESCE(p.prenom, ''),
                          p.sexe, f.designationfonction
                   FROM tb_personnel p
                   LEFT JOIN tb_fonction f ON p.idfonction = f.idfonction
                   WHERE p.deleted = 0
                   ORDER BY p.nom, p.prenom"""
            )
            personnels = cursor.fetchall()

            cursor.execute(
                """SELECT datepresence, idpersonnel, matin, apresmidi
                   FROM tb_suivipresence
                   WHERE datepresence BETWEEN %s AND %s AND deleted = 0""",
                (start_date, end_date),
            )
            presence_map = {}
            for d, pid, matin, aprem in cursor.fetchall():
                presence_map.setdefault(pid, []).append((matin, aprem))

            for idx, p in enumerate(personnels):
                stats = {"present": 0, "retard": 0, "absent": 0, "en_attente": 0}
                for m, a in presence_map.get(p[0], []):
                    for s in (m, a):
                        if s in stats:
                            stats[s] += 1
                tag = "even" if idx % 2 == 0 else "odd"
                self.history_tree.insert(
                    "", "end", tags=(tag,),
                    values=(
                        p[0], p[1].strip(),
                        self._safe(p[2]), self._safe(p[3]),
                        stats["present"], stats["retard"],
                        stats["absent"],  stats["en_attente"],
                    ),
                )
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur chargement historique : {e}")

    def export_history_excel(self):
        data = [self.history_tree.item(i, "values")
                for i in self.history_tree.get_children()]
        if not data:
            messagebox.showinfo("Info", "Aucune donnée à exporter.")
            return
        df = pd.DataFrame(
            data,
            columns=["ID", "Nom complet", "Sexe", "Fonction",
                     "Présent", "Retard", "Absent", "En attente"],
        )
        path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                             filetypes=[("Excel", "*.xlsx")])
        if path:
            df.to_excel(path, index=False)
            messagebox.showinfo("✅  Succès", "Exportation Excel réussie.")

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _parse_date_or_warn(self, value):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except Exception:
            messagebox.showwarning(
                "Date invalide", "Format attendu : YYYY-MM-DD\nEx: 2026-03-10"
            )
            return None

    def _safe(self, value):
        if value is None or str(value).strip() == "":
            return "-"
        return str(value)


# ─────────────────────────────────────────────────────────────────────────────
# Test standalone
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    Theme.setup()
    root = ctk.CTk()
    Theme.apply(root)
    root.title("Suivi de présence — iJeery")
    root.geometry("1300x820")
    app = PageSuiviPresence(root)
    app.pack(fill="both", expand=True)
    root.mainloop()
    db_manager.close_connection()