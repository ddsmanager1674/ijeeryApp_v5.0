# -*- coding: utf-8 -*-
"""
PageSuiviPresence — UI compacte & dense
Thème   : iJeery (app_theme.py)
Onglets : style Chrome (Canvas tkinter pour l'indicateur)
Statuts : ⬤ coloré dans Treeview
"""

import json
from datetime import datetime, date

import psycopg2
import pandas as pd
import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog

from resource_utils import get_config_path
from app_theme import Colors, Fonts, Theme, styled, Layout
from date_picker_utils import get_date_from_widget, parse_date, set_date_on_widget
from pages.personnel_structure import UNKNOWN_LABEL, ensure_personnel_structure, has_personnel_structure, personnel_poste_joins


# ─────────────────────────────────────────────────────────────────────────────
# DB Manager
# ─────────────────────────────────────────────────────────────────────────────

class DatabaseManager:
    def __init__(self):
        self.db_params = self._load_db_config()
        self.conn = None
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
            self.conn = psycopg2.connect(**self.db_params)
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
# Constantes statuts
# ─────────────────────────────────────────────────────────────────────────────

STATE_ORDER = ["en_attente", "present", "retard", "absent"]

STATE_DISPLAY = {
    "en_attente": "⬤  En attente",
    "present":    "⬤  Présent",
    "retard":     "⬤  Retard",
    "absent":     "⬤  Absent",
}
LABEL_STATE = {v: k for k, v in STATE_DISPLAY.items()}

STATE_FG = {
    "en_attente": "#95A5A6",
    "present":    "#27AE60",
    "retard":     "#E67E22",
    "absent":     "#E74C3C",
}

FILTER_MAP = {
    "En attente": "en_attente",
    "Present":    "present",
    "Retard":     "retard",
    "Absent":     "absent",
}


# ─────────────────────────────────────────────────────────────────────────────
# Onglets Chrome
# ─────────────────────────────────────────────────────────────────────────────

class ChromeTabs(ctk.CTkFrame):
    TAB_W = 155
    TAB_H = 34
    IND_H = 3

    def __init__(self, parent, tabs: list, command=None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._tabs    = tabs
        self._command = command
        self._active  = 0
        total_w = len(tabs) * self.TAB_W
        self._canvas = ctk.CTkCanvas(
            self, height=self.IND_H, width=total_w,
            bg=Colors.BG_PAGE, highlightthickness=0,
        )
        self._build()

    def _build(self):
        # [UI] Évite les redraws après destruction (Tkinter: invalid command name)
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        for w in self.winfo_children():
            if w is not self._canvas:
                w.destroy()
        row = ctk.CTkFrame(self, fg_color="transparent", height=self.TAB_H)
        row.pack(side="top", fill="x")
        row.pack_propagate(False)
        for i, label in enumerate(self._tabs):
            active = (i == self._active)
            ctk.CTkButton(
                row, text=label,
                font=Fonts.bold(12) if active else Fonts.body(12),
                fg_color=Colors.BG_CARD   if active else Colors.BG_PAGE,
                text_color=Colors.PRIMARY if active else Colors.TEXT_SECONDARY,
                hover_color=Colors.BG_CARD,
                corner_radius=0, height=self.TAB_H, width=self.TAB_W,
                border_width=0,
                command=lambda idx=i: self._select(idx),
            ).pack(side="left")
            if i < len(self._tabs) - 1:
                ctk.CTkFrame(row, width=1, height=18,
                              fg_color=Colors.BORDER).pack(side="left", pady=8)
        self._canvas.pack(side="top", fill="x")
        self._draw_indicator()

    def _draw_indicator(self):
        # [UI] Le canvas peut déjà être détruit si la page est fermée rapidement
        try:
            if not self.winfo_exists() or not self._canvas.winfo_exists():
                return
            self._canvas.delete("ind")
            x0 = self._active * self.TAB_W
            self._canvas.create_rectangle(
                x0, 0, x0 + self.TAB_W, self.IND_H,
                fill=Colors.PRIMARY, outline="", tags="ind"
            )
        except Exception:
            return

    def _select(self, idx):
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        self._active = idx
        self._build()
        if self._command:
            self._command(self._tabs[idx])

    def set(self, name):
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        if name in self._tabs:
            self._active = self._tabs.index(name)
            self._build()


# ─────────────────────────────────────────────────────────────────────────────
# Style Treeview compact
# ─────────────────────────────────────────────────────────────────────────────

def _setup_treeview_style():
    s = ttk.Style()
    s.theme_use("clam")
    s.configure("P.Treeview",
                background=Colors.BG_CARD,
                foreground=Colors.TEXT_PRIMARY,
                fieldbackground=Colors.BG_CARD,
                rowheight=26,
                font=("Segoe UI", 10),
                borderwidth=0)
    s.configure("P.Treeview.Heading",
                background=Colors.MIDNIGHT,
                foreground=Colors.TEXT_ON_DARK,
                font=("Segoe UI", 10, "bold"),
                relief="flat", padding=(6, 5))
    s.map("P.Treeview",
          background=[("selected", Colors.PRIMARY_LIGHT)],
          foreground=[("selected", Colors.TEXT_PRIMARY)])
    s.map("P.Treeview.Heading",
          background=[("active", Colors.MIDNIGHT_LIGHT)])


# ─────────────────────────────────────────────────────────────────────────────
# PAGE PRINCIPALE
# ─────────────────────────────────────────────────────────────────────────────

class PageSuiviPresence(ctk.CTkFrame):
    def __init__(self, parent, db_conn=None, session_data=None, **kwargs):
        super().__init__(parent, fg_color=Colors.BG_PAGE, **kwargs)
        self.db_conn = db_conn
        self.session_data = session_data

        if not db_manager.connect():
            ctk.CTkLabel(self, text="Erreur de connexion",
                         text_color=Colors.DANGER, font=Fonts.bold(14)
                         ).pack(pady=40)
            return
        try:
            self._personnel_structure_ready = ensure_personnel_structure(db_manager.conn)
        except Exception:
            self._personnel_structure_ready = False

        self.update_rows_cache = {}
        self._all_update_rows  = []
        self._stat_labels      = {}
        self._categorie_filter_map = {}
        self._poste_filter_map = {}
        _setup_treeview_style()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_tabs_bar()
        self._build_pages()
        self._load_category_poste_filters()

        self._show_tab("Suivi du jour")
        self.load_update_for_date(self.date_entry.get())
        self.load_history()

    # ── En-tête compact ──────────────────────────────────────────────────────

    def _build_header(self):
        h = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT, corner_radius=0, height=46)
        h.grid(row=0, column=0, sticky="ew")
        h.grid_propagate(False)
        h.grid_columnconfigure(1, weight=1)

        left = styled.frame(h)
        left.grid(row=0, column=0, padx=14, pady=0, sticky="w")
        ctk.CTkLabel(left, text="📋", font=Fonts.heading(16),
                     text_color=Colors.TEXT_ON_DARK).pack(side="left", padx=(0, 8))
        inner = styled.frame(left)
        inner.pack(side="left")
        ctk.CTkLabel(inner, text="Suivi de Présence",
                     font=Fonts.bold(13), text_color=Colors.TEXT_ON_DARK
                     ).pack(anchor="w")
        ctk.CTkLabel(inner, text="Gestion des présences journalières",
                     font=Fonts.small(9), text_color=Colors.TEXT_ON_DARK_DIM
                     ).pack(anchor="w")

        ctk.CTkLabel(h, text=f"📅  {date.today().strftime('%d %B %Y')}",
                     font=Fonts.small(10), text_color=Colors.TEXT_ON_DARK_DIM
                     ).grid(row=0, column=2, padx=14)

    # ── Onglets ───────────────────────────────────────────────────────────────

    def _build_tabs_bar(self):
        bar = ctk.CTkFrame(self, fg_color=Colors.BG_PAGE, corner_radius=0, height=40)
        bar.grid(row=1, column=0, sticky="ew")
        bar.grid_propagate(False)
        ctk.CTkFrame(bar, height=1, fg_color=Colors.BORDER
                     ).pack(side="bottom", fill="x")
        self.chrome_tabs = ChromeTabs(
            bar, tabs=["Suivi du jour", "Historique"],
            command=self._show_tab
        )
        self.chrome_tabs.pack(side="left", padx=10, pady=(3, 0))

    # ── Conteneur pages ───────────────────────────────────────────────────────

    def _build_pages(self):
        cont = ctk.CTkFrame(self, fg_color=Colors.BG_PAGE, corner_radius=0)
        cont.grid(row=2, column=0, sticky="nsew")
        cont.grid_columnconfigure(0, weight=1)
        cont.grid_rowconfigure(0, weight=1)

        self._pg_update = ctk.CTkFrame(cont, fg_color=Colors.BG_PAGE)
        self._pg_update.grid_columnconfigure(0, weight=1)
        self._pg_update.grid_rowconfigure(2, weight=1)
        self._build_update_page(self._pg_update)

        self._pg_history = ctk.CTkFrame(cont, fg_color=Colors.BG_PAGE)
        self._pg_history.grid_columnconfigure(0, weight=1)
        self._pg_history.grid_rowconfigure(1, weight=1)
        self._build_history_page(self._pg_history)

    def _show_tab(self, name):
        self.chrome_tabs.set(name)
        if name == "Suivi du jour":
            self._pg_history.grid_remove()
            self._pg_update.grid(row=0, column=0, sticky="nsew")
        else:
            self._pg_update.grid_remove()
            self._pg_history.grid(row=0, column=0, sticky="nsew")

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE SUIVI DU JOUR
    # ══════════════════════════════════════════════════════════════════════════

    def _build_update_page(self, parent):

        # ── Toolbar 1 ligne compacte ──────────────────────────────────────
        tb = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD, corner_radius=8)
        tb.grid(row=0, column=0, padx=8, pady=(6, 3), sticky="ew")
        tb.grid_columnconfigure(9, weight=1)

        def lbl(text, col, padl=10):
            ctk.CTkLabel(tb, text=text, font=Fonts.label(11),
                         text_color=Colors.TEXT_SECONDARY
                         ).grid(row=0, column=col, padx=(padl, 4), pady=7, sticky="w")

        lbl("Date :", 0)
        self.date_entry = styled.date_entry(tb, width=11, initial=date.today())
        self.date_entry.grid(row=0, column=1, padx=(0, 6), pady=7)

        ctk.CTkButton(tb, text="Charger", width=80, height=28,
                      fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
                      font=Fonts.bold(11), corner_radius=6,
                      command=self.on_update_load,
                      ).grid(row=0, column=2, padx=(0, 12), pady=7)

        lbl("Statut :", 3, 0)
        self.combo_statut = ctk.CTkComboBox(
            tb, values=["Tous", "En attente", "Present", "Retard", "Absent"],
            state="readonly", width=118, height=28,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            button_color=Colors.PRIMARY, font=Fonts.body(11),
            command=lambda v: self._apply_filter(),
        )
        self.combo_statut.set("Tous")
        self.combo_statut.grid(row=0, column=4, padx=(0, 6), pady=7)

        lbl("Catégorie :", 5, 0)
        self.combo_filter_categorie = ctk.CTkComboBox(
            tb, values=["Toutes"], state="readonly", width=125, height=28,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            button_color=Colors.PRIMARY, font=Fonts.body(11),
            command=lambda v: self._on_filter_category_change(v),
        )
        self.combo_filter_categorie.set("Toutes")
        self.combo_filter_categorie.grid(row=0, column=6, padx=(0, 6), pady=7)

        lbl("Poste :", 7, 0)
        self.combo_filter_poste = ctk.CTkComboBox(
            tb, values=["Tous"], state="readonly", width=120, height=28,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            button_color=Colors.PRIMARY, font=Fonts.body(11),
            command=lambda v: self._apply_filter(),
        )
        self.combo_filter_poste.set("Tous")
        self.combo_filter_poste.grid(row=0, column=8, padx=(0, 6), pady=7)

        rg = styled.frame(tb)
        rg.grid(row=0, column=10, padx=10, pady=7, sticky="e")
        ctk.CTkButton(rg, text="💾 Sauvegarder", width=118, height=28,
                      fg_color=Colors.SUCCESS, hover_color=Colors.SUCCESS_DARK,
                      font=Fonts.bold(11), corner_radius=6,
                      command=self.save_update,
                      ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(rg, text="📊 Excel", width=82, height=28,
                      fg_color=Colors.PREMIUM, hover_color=Colors.PREMIUM_DARK,
                      font=Fonts.bold(11), corner_radius=6,
                      command=self.export_update_excel,
                      ).pack(side="left")

        # ── Légende inline simple ─────────────────────────────────────────
        leg = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD, corner_radius=8)
        leg.grid(row=1, column=0, padx=8, pady=(0, 3), sticky="ew")

        ctk.CTkLabel(leg, text="Légende :", font=Fonts.label(10),
                     text_color=Colors.TEXT_SECONDARY
                     ).pack(side="left", padx=(10, 6), pady=4)
        for text, color in [
            ("⬤ En attente", STATE_FG["en_attente"]),
            ("⬤ Présent",    STATE_FG["present"]),
            ("⬤ Retard",     STATE_FG["retard"]),
            ("⬤ Absent",     STATE_FG["absent"]),
        ]:
            ctk.CTkLabel(leg, text=text, font=Fonts.label(10),
                         text_color=color).pack(side="left", padx=7, pady=4)

        ctk.CTkLabel(leg, text="💡 Double-clic Matin/Après-midi pour changer",
                     font=Fonts.small(9), text_color=Colors.TEXT_MUTED
                     ).pack(side="right", padx=10, pady=4)

        # ── Tableau (s'étend) ─────────────────────────────────────────────
        tc = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD, corner_radius=8)
        tc.grid(row=2, column=0, padx=8, pady=(0, 3), sticky="nsew")
        tc.grid_columnconfigure(0, weight=1)
        tc.grid_rowconfigure(0, weight=1)

        cols = ("ID", "Nom complet", "Sexe", "Catégorie", "Poste",
                "Matin", "Après-midi", "Observation")
        self.update_tree = ttk.Treeview(tc, columns=cols, show="headings",
                                         style="P.Treeview", selectmode="browse")
        for col, w, anc in [
            ("ID", 38, "center"), ("Nom complet", 165, "w"),
            ("Sexe", 48, "center"), ("Catégorie", 125, "w"), ("Poste", 135, "w"),
            ("Matin", 108, "center"), ("Après-midi", 108, "center"),
            ("Observation", 180, "w"),
        ]:
            self.update_tree.heading(col, text=col)
            self.update_tree.column(col, width=w, anchor=anc, minwidth=30)

        self.update_tree.tag_configure("even", background=Colors.BG_CARD)
        self.update_tree.tag_configure("odd",  background=Colors.BG_ROW_ALT)

        vsb = ttk.Scrollbar(tc, orient="vertical",   command=self.update_tree.yview)
        hsb = ttk.Scrollbar(tc, orient="horizontal", command=self.update_tree.xview)
        self.update_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.update_tree.grid(row=0, column=0, sticky="nsew", padx=(4, 0), pady=4)
        vsb.grid(row=0, column=1, sticky="ns", pady=4)
        hsb.grid(row=1, column=0, sticky="ew", padx=(4, 0))
        self.update_tree.bind("<Double-1>", self._on_dbl_click)
        self._all_update_rows = []

        # ── Footer stats — labels inline ──────────────────────────────────
        footer = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD, corner_radius=8)
        footer.grid(row=3, column=0, padx=8, pady=(0, 6), sticky="ew")

        self._stat_labels = {}
        for key, label, color in [
            ("present",    "⬤ Présents :",   STATE_FG["present"]),
            ("retard",     "⬤ Retards :",    STATE_FG["retard"]),
            ("absent",     "⬤ Absents :",    STATE_FG["absent"]),
            ("en_attente", "⬤ En attente :", STATE_FG["en_attente"]),
        ]:
            ctk.CTkLabel(footer, text=label, font=Fonts.label(10),
                         text_color=color).pack(side="left", padx=(10, 2), pady=5)
            val = ctk.CTkLabel(footer, text="0", font=Fonts.bold(11),
                               text_color=color)
            val.pack(side="left", padx=(0, 16), pady=5)
            self._stat_labels[key] = val

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE HISTORIQUE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_history_page(self, parent):
        fc = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD, corner_radius=8)
        fc.grid(row=0, column=0, padx=8, pady=(6, 3), sticky="ew")
        fc.grid_columnconfigure(5, weight=1)

        def lbl(text, col, padl=10):
            ctk.CTkLabel(fc, text=text, font=Fonts.label(11),
                         text_color=Colors.TEXT_SECONDARY
                         ).grid(row=0, column=col, padx=(padl, 4), pady=7, sticky="w")

        lbl("Début :", 0)
        self.h_from = styled.date_entry(fc, width=11, initial=date.today())
        self.h_from.grid(row=0, column=1, padx=(0, 8), pady=7)

        lbl("Fin :", 2, 0)
        self.h_to = styled.date_entry(fc, width=11, initial=date.today())
        self.h_to.grid(row=0, column=3, padx=(0, 8), pady=7)

        ctk.CTkButton(fc, text="🔍 Filtrer", width=84, height=28,
                      fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
                      font=Fonts.bold(11), corner_radius=6,
                      command=self.load_history,
                      ).grid(row=0, column=4, padx=(0, 6), pady=7)

        ctk.CTkButton(fc, text="Aujourd'hui", width=90, height=28,
                      fg_color=Colors.CLOUDS, hover_color=Colors.SILVER,
                      text_color=Colors.TEXT_PRIMARY,
                      font=Fonts.bold(11), corner_radius=6,
                      border_width=1, border_color=Colors.BORDER,
                      command=self._history_today,
                      ).grid(row=0, column=5, padx=(0, 6), pady=7, sticky="w")

        ctk.CTkButton(fc, text="📊 Excel", width=84, height=28,
                      fg_color=Colors.PREMIUM, hover_color=Colors.PREMIUM_DARK,
                      font=Fonts.bold(11), corner_radius=6,
                      command=self.export_history_excel,
                      ).grid(row=0, column=7, padx=(0, 10), pady=7, sticky="e")

        tc = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD, corner_radius=8)
        tc.grid(row=1, column=0, padx=8, pady=(0, 6), sticky="nsew")
        tc.grid_columnconfigure(0, weight=1)
        tc.grid_rowconfigure(0, weight=1)

        cols = ("ID", "Nom complet", "Sexe", "Catégorie", "Poste",
                "✅ Présent", "🟠 Retard", "🔴 Absent", "⬜ Attente")
        self.history_tree = ttk.Treeview(tc, columns=cols, show="headings",
                                          style="P.Treeview", selectmode="browse")
        for col, w, anc in [
            ("ID", 38, "center"), ("Nom complet", 165, "w"),
            ("Sexe", 48, "center"), ("Catégorie", 125, "w"), ("Poste", 135, "w"),
            ("✅ Présent", 80, "center"), ("🟠 Retard", 80, "center"),
            ("🔴 Absent", 80, "center"), ("⬜ Attente", 80, "center"),
        ]:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=w, anchor=anc, minwidth=30)

        self.history_tree.tag_configure("even", background=Colors.BG_CARD)
        self.history_tree.tag_configure("odd",  background=Colors.BG_ROW_ALT)

        vsb = ttk.Scrollbar(tc, orient="vertical",   command=self.history_tree.yview)
        hsb = ttk.Scrollbar(tc, orient="horizontal", command=self.history_tree.xview)
        self.history_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.history_tree.grid(row=0, column=0, sticky="nsew", padx=(4, 0), pady=4)
        vsb.grid(row=0, column=1, sticky="ns", pady=4)
        hsb.grid(row=1, column=0, sticky="ew", padx=(4, 0))

    # ══════════════════════════════════════════════════════════════════════════
    # LOGIQUE — SUIVI DU JOUR
    # ══════════════════════════════════════════════════════════════════════════

    def on_update_load(self):
        self.load_update_for_date(self.date_entry.get().strip())

    def _load_category_poste_filters(self):
        if not hasattr(self, "combo_filter_categorie"):
            return
        if not self._personnel_structure_ready:
            self.combo_filter_categorie.configure(values=["Toutes", UNKNOWN_LABEL])
            self.combo_filter_poste.configure(values=["Tous", UNKNOWN_LABEL])
            return
        try:
            cur = db_manager.get_cursor()
            cur.execute(
                "SELECT idcategorie, titre FROM tb_categoriepersonnel "
                "WHERE COALESCE(deleted,0)=0 ORDER BY titre"
            )
            cats = cur.fetchall()
            self._categorie_filter_map = {r[1]: r[0] for r in cats}
            self.combo_filter_categorie.configure(values=["Toutes", UNKNOWN_LABEL] + [r[1] for r in cats])
            self._load_poste_filter_values()
        except Exception:
            pass

    def _load_poste_filter_values(self):
        if not hasattr(self, "combo_filter_poste"):
            return
        if not self._personnel_structure_ready:
            self.combo_filter_poste.configure(values=["Tous", UNKNOWN_LABEL])
            self.combo_filter_poste.set("Tous")
            return
        selected_cat = self.combo_filter_categorie.get()
        try:
            cur = db_manager.get_cursor()
            if selected_cat == "Toutes":
                cur.execute(
                    "SELECT idposte, titre FROM tb_postepersonnel "
                    "WHERE COALESCE(deleted,0)=0 ORDER BY titre"
                )
                rows = cur.fetchall()
                self._poste_filter_map = {r[1]: r[0] for r in rows}
                values = ["Tous", UNKNOWN_LABEL] + [r[1] for r in rows]
            elif selected_cat == UNKNOWN_LABEL:
                self._poste_filter_map = {}
                values = ["Tous", UNKNOWN_LABEL]
            else:
                cur.execute(
                    "SELECT idposte, titre FROM tb_postepersonnel "
                    "WHERE COALESCE(deleted,0)=0 AND idcategorie=%s ORDER BY titre",
                    (self._categorie_filter_map.get(selected_cat),),
                )
                rows = cur.fetchall()
                self._poste_filter_map = {r[1]: r[0] for r in rows}
                values = ["Tous", UNKNOWN_LABEL] + [r[1] for r in rows]
            self.combo_filter_poste.configure(values=values)
            self.combo_filter_poste.set("Tous")
        except Exception:
            pass

    def _on_filter_category_change(self, value):
        self._load_poste_filter_values()
        self._apply_filter()

    def _apply_filter(self):
        target = FILTER_MAP.get(self.combo_statut.get())
        cat_filter = self.combo_filter_categorie.get() if hasattr(self, "combo_filter_categorie") else "Toutes"
        poste_filter = self.combo_filter_poste.get() if hasattr(self, "combo_filter_poste") else "Tous"
        self.update_tree.delete(*self.update_tree.get_children())
        self.update_rows_cache = {}
        count = 0
        for row in self._all_update_rows:
            ms = row[5] or "en_attente"
            ap = row[6] or "en_attente"
            if target and ms != target and ap != target:
                continue
            if cat_filter != "Toutes" and row[3] != cat_filter:
                continue
            if poste_filter != "Tous" and row[4] != poste_filter:
                continue
            tag = "even" if count % 2 == 0 else "odd"
            iid = self.update_tree.insert("", "end", tags=(tag,), values=(
                row[0], row[1].strip(), self._safe(row[2]), self._safe(row[3]), self._safe(row[4]),
                STATE_DISPLAY.get(ms), STATE_DISPLAY.get(ap), self._safe(row[7]),
            ))
            self.update_rows_cache[iid] = row
            count += 1
        self._update_stats()

    def ensure_presence_day(self, d):
        try:
            cur = db_manager.get_cursor()
            cur.execute("SELECT id FROM tb_personnel WHERE deleted=0 ORDER BY nom,prenom")
            pids = [r[0] for r in cur.fetchall()]
            cur.execute("SELECT idpersonnel FROM tb_suivipresence WHERE datepresence=%s", (d,))
            existing = {r[0] for r in cur.fetchall()}
            to_ins = [p for p in pids if p not in existing]
            for pid in to_ins:
                cur.execute(
                    "INSERT INTO tb_suivipresence "
                    "(datepresence,idpersonnel,matin,apresmidi,observation,deleted) "
                    "VALUES (%s,%s,'en_attente','en_attente','',0)",
                    (d, pid)
                )
            if to_ins:
                db_manager.conn.commit()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def load_update_for_date(self, raw):
        d = self._parse(raw)
        if not d: return
        self.ensure_presence_day(d)
        self.update_tree.delete(*self.update_tree.get_children())
        self.update_rows_cache = {}
        try:
            cur = db_manager.get_cursor()
            if self._personnel_structure_ready and has_personnel_structure(db_manager.conn):
                sql = """SELECT p.id, p.nom||' '||COALESCE(p.prenom,''), p.sexe,
                                COALESCE(cp.titre, 'Inconnu') AS categorie,
                                COALESCE(pp.titre, 'Inconnu') AS poste,
                                sp.matin, sp.apresmidi, sp.observation
                         FROM tb_suivipresence sp
                         JOIN tb_personnel p ON sp.idpersonnel=p.id
                         {joins}
                         WHERE sp.datepresence=%s AND sp.deleted=0
                         ORDER BY p.nom,p.prenom""".format(joins=personnel_poste_joins("p"))
                cur.execute(sql, (d,))
            else:
                self._personnel_structure_ready = False
                cur.execute(
                    """SELECT p.id, p.nom||' '||COALESCE(p.prenom,''), p.sexe,
                              %s AS categorie, %s AS poste,
                              sp.matin, sp.apresmidi, sp.observation
                       FROM tb_suivipresence sp
                       JOIN tb_personnel p ON sp.idpersonnel=p.id
                       WHERE sp.datepresence=%s AND sp.deleted=0
                       ORDER BY p.nom,p.prenom""",
                    (UNKNOWN_LABEL, UNKNOWN_LABEL, d),
                )
            rows = cur.fetchall()
            self._all_update_rows = list(rows)
            for idx, row in enumerate(rows):
                ms  = row[5] or "en_attente"
                ap  = row[6] or "en_attente"
                tag = "even" if idx % 2 == 0 else "odd"
                iid = self.update_tree.insert("", "end", tags=(tag,), values=(
                    row[0], row[1].strip(), self._safe(row[2]), self._safe(row[3]), self._safe(row[4]),
                    STATE_DISPLAY.get(ms), STATE_DISPLAY.get(ap), self._safe(row[7]),
                ))
                self.update_rows_cache[iid] = row
            self._update_stats()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def _on_dbl_click(self, event):
        item = self.update_tree.identify("item",   event.x, event.y)
        col  = self.update_tree.identify_column(event.x)
        if not item or not col: return
        ci = int(col.replace("#", "")) - 1
        if ci in (5, 6):
            vals = list(self.update_tree.item(item, "values"))
            cur_s  = LABEL_STATE.get(vals[ci], "en_attente")
            next_s = STATE_ORDER[(STATE_ORDER.index(cur_s) + 1) % 4]
            vals[ci] = STATE_DISPLAY[next_s]
            self.update_tree.item(item, values=vals)
            self._update_stats()
        elif ci == 7:
            self._inline_edit(item, ci)

    def _inline_edit(self, item, ci):
        bbox = self.update_tree.bbox(item, f"#{ci+1}")
        if not bbox: return
        x, y, w, h = bbox
        current = self.update_tree.item(item, "values")[ci]
        e = ctk.CTkEntry(self.update_tree, width=w, height=h,
                          fg_color=Colors.BG_INPUT, font=Fonts.body(10))
        e.place(x=x, y=y)
        e.insert(0, "" if current == "-" else current)
        e.focus_force()
        def save(ev=None):
            v = e.get().strip()
            vals = list(self.update_tree.item(item, "values"))
            vals[ci] = v if v else "-"
            self.update_tree.item(item, values=vals)
            e.destroy()
        e.bind("<Return>", save)
        e.bind("<FocusOut>", save)

    def save_update(self):
        d = get_date_from_widget(self.date_entry)
        if not d: return
        try:
            cur = db_manager.get_cursor()
            for item in self.update_tree.get_children():
                vals = self.update_tree.item(item, "values")
                cur.execute(
                    "UPDATE tb_suivipresence SET matin=%s,apresmidi=%s,observation=%s "
                    "WHERE datepresence=%s AND idpersonnel=%s",
                    (LABEL_STATE.get(vals[5], "en_attente"),
                     LABEL_STATE.get(vals[6], "en_attente"),
                     "" if vals[7] == "-" else vals[7],
                     d, vals[0])
                )
            db_manager.conn.commit()
            messagebox.showinfo("Succès", "Suivi enregistré.")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def export_update_excel(self):
        data = [self.update_tree.item(i, "values")
                for i in self.update_tree.get_children()]
        if not data:
            messagebox.showinfo("Info", "Aucune donnée."); return
        df = pd.DataFrame(data, columns=[
            "ID", "Nom complet", "Sexe", "Catégorie", "Poste",
            "Matin", "Après-midi", "Observation"])
        p = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                          filetypes=[("Excel", "*.xlsx")])
        if p:
            df.to_excel(p, index=False)
            messagebox.showinfo("Succès", "Export réussi.")
            try:
                from log_utils import AppLogger
                AppLogger(session_data=getattr(self, "session_data", {}) or {}).log(
                    action="Export Excel",
                    element="Suivi de présence",
                    details=f"export suivi présence (mise à jour), lignes={len(df)}, fichier={os.path.basename(p)}",
                    value=p,
                )
            except Exception:
                pass

    def _update_stats(self):
        stats = {k: 0 for k in STATE_ORDER}
        for item in self.update_tree.get_children():
            vals = self.update_tree.item(item, "values")
            for v in (vals[5], vals[6]):
                stats[LABEL_STATE.get(v, "en_attente")] += 1
        for key, lbl in self._stat_labels.items():
            lbl.configure(text=str(stats.get(key, 0)))

    # ══════════════════════════════════════════════════════════════════════════
    # LOGIQUE — HISTORIQUE
    # ══════════════════════════════════════════════════════════════════════════

    def _history_today(self):
        t = date.today()
        set_date_on_widget(self.h_from, t)
        set_date_on_widget(self.h_to, t)
        self.load_history()

    def load_history(self):
        sd = get_date_from_widget(self.h_from) or date.today()
        ed = get_date_from_widget(self.h_to) or date.today()
        if sd > ed:
            messagebox.showwarning("Erreur", "La date de début doit être antérieure à la date de fin.")
            return
        self.history_tree.delete(*self.history_tree.get_children())
        try:
            cur = db_manager.get_cursor()
            if self._personnel_structure_ready and has_personnel_structure(db_manager.conn):
                cur.execute(
                    """SELECT p.id, p.nom||' '||COALESCE(p.prenom,''), p.sexe,
                              COALESCE(cp.titre, 'Inconnu') AS categorie,
                              COALESCE(pp.titre, 'Inconnu') AS poste
                       FROM tb_personnel p
                       {joins}
                       WHERE p.deleted=0 ORDER BY p.nom,p.prenom""".format(joins=personnel_poste_joins("p"))
                )
            else:
                self._personnel_structure_ready = False
                cur.execute(
                    """SELECT p.id, p.nom||' '||COALESCE(p.prenom,''), p.sexe,
                              %s AS categorie, %s AS poste
                       FROM tb_personnel p
                       WHERE p.deleted=0 ORDER BY p.nom,p.prenom""",
                    (UNKNOWN_LABEL, UNKNOWN_LABEL),
                )
            personnels = cur.fetchall()
            cur.execute(
                """SELECT datepresence,idpersonnel,matin,apresmidi
                   FROM tb_suivipresence
                   WHERE datepresence BETWEEN %s AND %s AND deleted=0""",
                (sd, ed)
            )
            pmap = {}
            for _, pid, m, a in cur.fetchall():
                pmap.setdefault(pid, []).append((m, a))
            for idx, p in enumerate(personnels):
                st = {k: 0 for k in STATE_ORDER}
                for m, a in pmap.get(p[0], []):
                    for x in (m, a):
                        if x in st: st[x] += 1
                tag = "even" if idx % 2 == 0 else "odd"
                self.history_tree.insert("", "end", tags=(tag,), values=(
                    p[0], p[1].strip(), self._safe(p[2]), self._safe(p[3]), self._safe(p[4]),
                    st["present"], st["retard"], st["absent"], st["en_attente"],
                ))
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def export_history_excel(self):
        data = [self.history_tree.item(i, "values")
                for i in self.history_tree.get_children()]
        if not data:
            messagebox.showinfo("Info", "Aucune donnée."); return
        df = pd.DataFrame(data, columns=[
            "ID", "Nom complet", "Sexe", "Catégorie", "Poste",
            "Présent", "Retard", "Absent", "En attente"])
        p = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                          filetypes=[("Excel", "*.xlsx")])
        if p:
            df.to_excel(p, index=False)
            messagebox.showinfo("Succès", "Export réussi.")

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _parse(self, value):
        d = parse_date(value)
        if value and not d:
            messagebox.showwarning("Date invalide", "Format attendu : jj/mm/aaaa")
        return d

    def _safe(self, value):
        return str(value) if value and str(value).strip() else "-"


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    Theme.setup()
    root = ctk.CTk()
    Theme.apply(root)
    root.title("Suivi de présence — iJeery")
    root.geometry("1200x720")
    PageSuiviPresence(root).pack(fill="both", expand=True)
    root.mainloop()
    db_manager.close_connection()
