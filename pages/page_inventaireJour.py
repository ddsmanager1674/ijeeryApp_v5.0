# -*- coding: utf-8 -*-
"""
PageInventaireJour — UI moderne & compacte
• DatePicker popup calendrier natif
• Badges colorés statut dans le Treeview
• Fenêtre de recherche/sélection article
• Footer stats aligné
Thème : iJeery (app_theme.py)
"""

import json
import calendar
from datetime import datetime, date

import psycopg2
import pandas as pd
import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog

from resource_utils import get_config_path, get_session_path, safe_file_read
from app_theme import Colors, Fonts, styled, Layout, Theme


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
STATUTS = ["Vérifié", "Non vérifié", "Annulé"]

# Palette badges statut
STATUT_STYLE = {
    "Vérifié":     (Colors.SUCCESS_TEXT,  Colors.SUCCESS_LIGHT,  "✅"),
    "Non vérifié": (Colors.WARNING_TEXT,  Colors.WARNING_LIGHT,  "🟠"),
    "Annulé":      (Colors.DANGER_TEXT,   Colors.DANGER_LIGHT,   "🔴"),
}


# ─────────────────────────────────────────────────────────────────────────────
# Treeview style
# ─────────────────────────────────────────────────────────────────────────────

def _setup_style():
    s = ttk.Style()
    s.theme_use("clam")
    s.configure("Inv.Treeview",
                background=Colors.BG_CARD,
                foreground=Colors.TEXT_PRIMARY,
                fieldbackground=Colors.BG_CARD,
                rowheight=28, font=("Segoe UI", 10), borderwidth=0)
    s.configure("Inv.Treeview.Heading",
                background=Colors.MIDNIGHT,
                foreground=Colors.TEXT_ON_DARK,
                font=("Segoe UI", 10, "bold"),
                relief="flat", padding=(6, 5))
    s.map("Inv.Treeview",
          background=[("selected", Colors.PRIMARY_LIGHT)],
          foreground=[("selected", Colors.TEXT_PRIMARY)])
    s.map("Inv.Treeview.Heading",
          background=[("active", Colors.MIDNIGHT_LIGHT)])


# ─────────────────────────────────────────────────────────────────────────────
# DatePicker — popup calendrier compact
# ─────────────────────────────────────────────────────────────────────────────

class DatePickerPopup(ctk.CTkToplevel):
    """
    Mini-calendrier popup.
    Paramètres :
        anchor_widget  – widget d'ancrage pour positionner le popup
        on_select      – callback(date_str: str) appelé au clic sur un jour
        initial_date   – date pré-sélectionnée (str "YYYY-MM-DD" ou None)
    """

    DAYS   = ["Lu", "Ma", "Me", "Je", "Ve", "Sa", "Di"]
    MON_FR = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
              "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

    def __init__(self, master, anchor_widget, on_select, initial_date=None):
        super().__init__(master)
        self._on_select = on_select

        # Date courante affichée
        try:
            init = datetime.strptime(initial_date, "%Y-%m-%d").date() if initial_date else date.today()
        except Exception:
            init = date.today()
        self._year  = init.year
        self._month = init.month
        self._selected: date | None = init if initial_date else None

        self.overrideredirect(True)          # sans barre de titre
        self.configure(fg_color=Colors.BG_CARD)
        self.attributes("-topmost", True)
        self.lift()
        self.after(150, lambda: self.attributes("-topmost", False))

        self._build()

        # Positionner sous le widget d'ancrage
        self.update_idletasks()
        ax = anchor_widget.winfo_rootx()
        ay = anchor_widget.winfo_rooty() + anchor_widget.winfo_height() + 2
        self.geometry(f"+{ax}+{ay}")

        # Fermer si clic en dehors
        self.bind("<FocusOut>", self._on_focus_out)
        self.focus_set()

    # ── Construit le calendrier ──────────────────────────────────────────────

    def _build(self):
        for w in self.winfo_children():
            w.destroy()

        outer = ctk.CTkFrame(self, fg_color=Colors.BG_CARD,
                              border_width=1, border_color=Colors.BORDER,
                              corner_radius=8)
        outer.pack(padx=0, pady=0)

        # Barre navigation mois/année
        nav = ctk.CTkFrame(outer, fg_color=Colors.MIDNIGHT,
                            corner_radius=0, height=34)
        nav.pack(fill="x")
        nav.pack_propagate(False)

        ctk.CTkButton(nav, text="◀", width=28, height=28,
                      fg_color="transparent", hover_color=Colors.MIDNIGHT_LIGHT,
                      text_color=Colors.TEXT_ON_DARK, font=Fonts.bold(11),
                      corner_radius=4, command=self._prev_month
                      ).pack(side="left", padx=4, pady=3)

        ctk.CTkLabel(nav,
                     text=f"{self.MON_FR[self._month - 1]}  {self._year}",
                     font=Fonts.bold(11), text_color=Colors.TEXT_ON_DARK
                     ).pack(side="left", expand=True)

        ctk.CTkButton(nav, text="▶", width=28, height=28,
                      fg_color="transparent", hover_color=Colors.MIDNIGHT_LIGHT,
                      text_color=Colors.TEXT_ON_DARK, font=Fonts.bold(11),
                      corner_radius=4, command=self._next_month
                      ).pack(side="right", padx=4, pady=3)

        # Grille jours
        grid = ctk.CTkFrame(outer, fg_color=Colors.BG_CARD)
        grid.pack(padx=6, pady=4)

        # En-têtes
        for c, day in enumerate(self.DAYS):
            color = Colors.DANGER if c >= 5 else Colors.TEXT_SECONDARY
            ctk.CTkLabel(grid, text=day, font=Fonts.bold(9),
                         text_color=color, width=30, anchor="center"
                         ).grid(row=0, column=c, padx=1, pady=(2, 1))

        # Jours du mois
        cal = calendar.monthcalendar(self._year, self._month)
        for r, week in enumerate(cal):
            for c, day in enumerate(week):
                if day == 0:
                    ctk.CTkLabel(grid, text="", width=30, height=26
                                 ).grid(row=r + 1, column=c, padx=1, pady=1)
                    continue

                d    = date(self._year, self._month, day)
                is_selected = (self._selected == d)
                is_today    = (d == date.today())
                is_weekend  = (c >= 5)

                if is_selected:
                    fg  = Colors.PRIMARY
                    txt = Colors.TEXT_ON_DARK
                elif is_today:
                    fg  = Colors.PRIMARY_LIGHT
                    txt = Colors.PRIMARY
                else:
                    fg  = Colors.BG_CARD
                    txt = Colors.DANGER if is_weekend else Colors.TEXT_PRIMARY

                btn = ctk.CTkButton(
                    grid, text=str(day),
                    width=30, height=26,
                    fg_color=fg, hover_color=Colors.PRIMARY_LIGHT,
                    text_color=txt, font=Fonts.body(10),
                    corner_radius=4,
                    command=lambda d=d: self._pick(d)
                )
                btn.grid(row=r + 1, column=c, padx=1, pady=1)

        # Bouton "Aujourd'hui"
        foot = ctk.CTkFrame(outer, fg_color=Colors.BG_CARD)
        foot.pack(fill="x", padx=6, pady=(0, 6))
        ctk.CTkButton(foot, text="Aujourd'hui", height=24,
                      fg_color=Colors.CLOUDS, hover_color=Colors.SILVER,
                      text_color=Colors.TEXT_PRIMARY,
                      font=Fonts.body(10), corner_radius=4,
                      border_width=1, border_color=Colors.BORDER,
                      command=lambda: self._pick(date.today())
                      ).pack(fill="x")

    def _prev_month(self):
        if self._month == 1:
            self._month, self._year = 12, self._year - 1
        else:
            self._month -= 1
        self._build()

    def _next_month(self):
        if self._month == 12:
            self._month, self._year = 1, self._year + 1
        else:
            self._month += 1
        self._build()

    def _pick(self, d: date):
        self._selected = d
        self._on_select(d.strftime("%Y-%m-%d"))
        self.destroy()

    def _on_focus_out(self, event=None):
        try: self.destroy()
        except Exception: pass


# ─────────────────────────────────────────────────────────────────────────────
# Widget DateEntry (Entry + bouton 📅 → DatePickerPopup)
# ─────────────────────────────────────────────────────────────────────────────

class DateEntry(ctk.CTkFrame):
    """
    Champ de date avec icône calendrier.
    Utilisation :
        de = DateEntry(parent)
        de.get()   → "YYYY-MM-DD" ou ""
        de.set("2026-03-10")
    """

    def __init__(self, parent, width=115, placeholder="YYYY-MM-DD", **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._popup = None

        self._entry = ctk.CTkEntry(
            self, width=width - 30, height=28,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            font=Fonts.body(11), corner_radius=6,
            placeholder_text=placeholder,
        )
        self._entry.pack(side="left")

        ctk.CTkButton(
            self, text="📅", width=26, height=28,
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            text_color=Colors.TEXT_ON_DARK, font=Fonts.body(11),
            corner_radius=6,
            command=self._open_picker,
        ).pack(side="left", padx=(2, 0))

    def _open_picker(self):
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
        self._popup = DatePickerPopup(
            self.winfo_toplevel(),
            anchor_widget=self,
            on_select=self._on_date_selected,
            initial_date=self._entry.get().strip() or None,
        )

    def _on_date_selected(self, date_str: str):
        self._entry.delete(0, "end")
        self._entry.insert(0, date_str)

    def get(self) -> str:
        return self._entry.get().strip()

    def set(self, value: str):
        self._entry.delete(0, "end")
        if value:
            self._entry.insert(0, value)

    def clear(self):
        self._entry.delete(0, "end")


# ─────────────────────────────────────────────────────────────────────────────
# Fenêtre de recherche/sélection article
# ─────────────────────────────────────────────────────────────────────────────

class ArticleSearchWindow(ctk.CTkToplevel):
    """
    Mini-fenêtre de recherche et sélection d'article.
    on_select(article_label: str, article_id: int)
    """

    def __init__(self, master, article_map: dict, on_select):
        super().__init__(master)
        self._article_map = article_map   # {designation: idarticle}
        self._on_select   = on_select

        self.title("Rechercher un article")
        self.geometry("400x420")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_PAGE)
        self.grab_set()
        self.focus_set()
        self._center()
        self._build()
        self._populate("")

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth()  // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        # En-tête
        hdr = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT,
                            corner_radius=0, height=40)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="  🔍  Sélectionner un article",
                     font=Fonts.bold(12), text_color=Colors.TEXT_ON_DARK,
                     anchor="w").pack(side="left", fill="y", padx=12)

        # Recherche
        search_row = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        search_row.pack(fill="x", padx=0, pady=(0, 1))

        self._search_var = ctk.StringVar()
        self._search_entry = ctk.CTkEntry(
            search_row, textvariable=self._search_var,
            height=32, fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER, font=Fonts.body(11),
            corner_radius=0, placeholder_text="Tapez pour filtrer…"
        )
        self._search_entry.pack(fill="x", padx=8, pady=6)
        self._search_entry.bind("<KeyRelease>",
                                lambda e: self._populate(self._search_var.get()))

        # Liste résultats
        list_frame = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=8)
        list_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)

        # Style liste
        ls = ttk.Style()
        ls.configure("Art.Treeview",
                     background=Colors.BG_CARD,
                     foreground=Colors.TEXT_PRIMARY,
                     fieldbackground=Colors.BG_CARD,
                     rowheight=26, font=("Segoe UI", 10), borderwidth=0)
        ls.configure("Art.Treeview.Heading",
                     background=Colors.MIDNIGHT,
                     foreground=Colors.TEXT_ON_DARK,
                     font=("Segoe UI", 10, "bold"), relief="flat")
        ls.map("Art.Treeview",
               background=[("selected", Colors.PRIMARY_LIGHT)],
               foreground=[("selected", Colors.TEXT_PRIMARY)])

        self._list = ttk.Treeview(list_frame, columns=("art",),
                                   show="headings", style="Art.Treeview",
                                   selectmode="browse")
        self._list.heading("art", text="Désignation article")
        self._list.column("art", anchor="w", minwidth=100)

        vsb = ttk.Scrollbar(list_frame, orient="vertical",
                              command=self._list.yview)
        self._list.configure(yscrollcommand=vsb.set)
        self._list.grid(row=0, column=0, sticky="nsew", padx=(4, 0), pady=4)
        vsb.grid(row=0, column=1, sticky="ns", pady=4)

        # Double-clic ou bouton sélectionner
        self._list.bind("<Double-1>", lambda e: self._confirm())

        # Footer boutons
        foot = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        foot.pack(fill="x")

        ctk.CTkButton(foot, text="✕  Annuler", width=96, height=28,
                      fg_color=Colors.CLOUDS, hover_color=Colors.SILVER,
                      text_color=Colors.TEXT_PRIMARY,
                      font=Fonts.bold(11), corner_radius=6,
                      border_width=1, border_color=Colors.BORDER,
                      command=self.destroy
                      ).pack(side="right", padx=(6, 10), pady=6)

        ctk.CTkButton(foot, text="✔  Sélectionner", width=120, height=28,
                      fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
                      font=Fonts.bold(11), corner_radius=6,
                      command=self._confirm
                      ).pack(side="right", padx=(0, 6), pady=6)

        self._search_entry.focus_set()

    def _populate(self, query: str):
        self._list.delete(*self._list.get_children())
        q = query.strip().lower()
        for label in sorted(self._article_map.keys()):
            if q in label.lower():
                self._list.insert("", "end", iid=label, values=(label,))

    def _confirm(self):
        sel = self._list.selection()
        if not sel:
            messagebox.showwarning("Sélection", "Choisissez un article.", parent=self)
            return
        label = sel[0]
        self._on_select(label, self._article_map[label])
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────
# MODAL Inventaire
# ─────────────────────────────────────────────────────────────────────────────

class ModalInventaire(ctk.CTkToplevel):
    def __init__(self, master, on_save, db_get_cursor, db_commit,
                 article_map, magasin_map, current_user_id,
                 mode="ajout", row_values=None, default_magasin_label=None):
        super().__init__(master)
        self._on_save        = on_save
        self._get_cursor     = db_get_cursor
        self._commit         = db_commit
        self.article_map     = article_map
        self.magasin_map     = magasin_map
        self.current_user_id = current_user_id
        self.mode            = mode
        self.row_values      = row_values
        self.unite_map       = {}
        self._selected_article_id: int | None = None
        self._default_magasin_label = default_magasin_label

        self.inv_id = row_values[0] if row_values else None

        titre = "Nouvel inventaire" if mode == "ajout" else "Modifier l'inventaire"
        self.title(titre)
        self.geometry("480x420")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_PAGE)
        self.grab_set()
        self.focus_set()
        self.attributes("-topmost", True)
        self._center()
        self._build_ui()

        if mode == "modification" and row_values:
            self._prefill()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth()  // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # En-tête compact
        hdr = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT,
                            corner_radius=0, height=42)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        icon  = "➕" if self.mode == "ajout" else "✏️"
        titre = "Nouvel inventaire" if self.mode == "ajout" else "Modifier l'inventaire"
        ctk.CTkLabel(hdr, text=f"  {icon}  {titre}",
                     font=Fonts.bold(13), text_color=Colors.TEXT_ON_DARK,
                     anchor="w").pack(side="left", padx=16, fill="y")

        body = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        body.pack(fill="both", expand=True, padx=16, pady=10)
        body.grid_columnconfigure(1, weight=1)

        def lbl(row, text, required=False):
            color = Colors.DANGER if required else Colors.TEXT_SECONDARY
            ctk.CTkLabel(body,
                         text=f"{text} *" if required else text,
                         font=Fonts.label(10), text_color=color, anchor="w"
                         ).grid(row=row, column=0, padx=(0, 8), pady=3, sticky="w")

        def mk_combo(values):
            return ctk.CTkComboBox(body, values=values, state="readonly",
                                   height=28, fg_color=Colors.BG_INPUT,
                                   border_color=Colors.BORDER,
                                   button_color=Colors.PRIMARY,
                                   dropdown_fg_color=Colors.BG_CARD,
                                   font=Fonts.body(11))

        # ── Ligne 0 : Article * (entry + bouton recherche) ────────────────
        lbl(0, "Article", required=True)
        art_row = ctk.CTkFrame(body, fg_color="transparent")
        art_row.grid(row=0, column=1, pady=3, sticky="ew")
        art_row.grid_columnconfigure(0, weight=1)

        self.entry_article = ctk.CTkEntry(
            art_row, height=28, state="readonly",
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            font=Fonts.body(11), corner_radius=6,
            placeholder_text="Cliquer 🔍 pour chercher…"
        )
        self.entry_article.grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(
            art_row, text="🔍", width=30, height=28,
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            text_color=Colors.TEXT_ON_DARK,
            font=Fonts.body(11), corner_radius=6,
            command=self._open_article_search,
        ).grid(row=0, column=1, padx=(4, 0))

        # ── Ligne 1 : Unité * ─────────────────────────────────────────────
        lbl(1, "Unité", required=True)
        self.combo_unite = mk_combo([])
        self.combo_unite.grid(row=1, column=1, pady=3, sticky="ew")

        # ── Ligne 2 : Magasin * ───────────────────────────────────────────
        lbl(2, "Magasin", required=True)
        self.combo_magasin = mk_combo(list(self.magasin_map.keys()))
        self.combo_magasin.grid(row=2, column=1, pady=3, sticky="ew")
        if self.mode == "ajout" and self._default_magasin_label in self.magasin_map:
            self.combo_magasin.set(self._default_magasin_label)

        # ── Ligne 3 : Qté * ───────────────────────────────────────────────
        lbl(3, "Qté corrigée", required=True)
        self.entry_qte = ctk.CTkEntry(
            body, height=28, fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER, font=Fonts.body(11),
            corner_radius=6, placeholder_text="0.00"
        )
        self.entry_qte.grid(row=3, column=1, pady=3, sticky="ew")

        # ── Ligne 4 : Observation ─────────────────────────────────────────
        lbl(4, "Observation")
        self.textbox_obs = ctk.CTkTextbox(
            body, height=65, fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER, border_width=1,
            font=Fonts.body(11), corner_radius=6
        )
        self.textbox_obs.grid(row=4, column=1, pady=3, sticky="ew")

        # Note obligatoires
        ctk.CTkLabel(body, text="* Champs obligatoires",
                     font=Fonts.small(9), text_color=Colors.TEXT_MUTED
                     ).grid(row=5, column=0, columnspan=2, pady=(4, 0), sticky="w")

        # Séparateur
        ctk.CTkFrame(body, height=1, fg_color=Colors.DIVIDER
                     ).grid(row=6, column=0, columnspan=2, pady=(8, 6), sticky="ew")

        # Boutons
        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.grid(row=7, column=0, columnspan=2, sticky="e")

        ctk.CTkButton(btn_row, text="✕  Annuler", width=96, height=28,
                      fg_color=Colors.CLOUDS, hover_color=Colors.SILVER,
                      text_color=Colors.TEXT_PRIMARY,
                      font=Fonts.bold(11), corner_radius=6,
                      border_width=1, border_color=Colors.BORDER,
                      command=self.destroy
                      ).pack(side="left", padx=(0, 6))

        if self.mode == "modification":
            ctk.CTkButton(btn_row, text="🚫  Annuler inv.", width=120, height=28,
                          fg_color=Colors.DANGER, hover_color=Colors.DANGER_DARK,
                          font=Fonts.bold(11), corner_radius=6,
                          command=lambda: self._save(status_override="Annulé")
                          ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(btn_row, text="💾  Enregistrer", width=120, height=28,
                      fg_color=Colors.SUCCESS, hover_color=Colors.SUCCESS_DARK,
                      text_color=Colors.TEXT_ON_DARK,
                      font=Fonts.bold(11), corner_radius=6,
                      command=self._save
                      ).pack(side="left")

    # ── Recherche article ─────────────────────────────────────────────────────

    def _open_article_search(self):
        ArticleSearchWindow(self, self.article_map, self._on_article_selected)

    def _on_article_selected(self, label: str, art_id: int):
        self._selected_article_id = art_id
        self.entry_article.configure(state="normal")
        self.entry_article.delete(0, "end")
        self.entry_article.insert(0, label)
        self.entry_article.configure(state="readonly")
        self._load_unites(art_id)

    def _load_unites(self, art_id: int):
        try:
            cur = self._get_cursor()
            cur.execute(
                "SELECT idunite, designationunite FROM tb_unite "
                "WHERE idarticle=%s AND deleted=0 ORDER BY designationunite",
                (art_id,)
            )
            rows = cur.fetchall()
            self.unite_map = {r[1]: r[0] for r in rows}
            self.combo_unite.configure(values=list(self.unite_map.keys()))
            if rows: self.combo_unite.set(rows[0][1])
            else:    self.combo_unite.set("")
        except Exception as e:
            messagebox.showerror("Erreur", str(e), parent=self)

    def _prefill(self):
        rv = self.row_values
        # rv index: 0=id, 1=magasin, 2=user, 3=datetime,
        #           4=article, 5=unite, 6=magasin_stock,
        #           7=qte, 8=qte_stock, 9=obs, 10=statut, 11=maj, 12=verificateur
        art_label = rv[4] if rv[4] != "-" else ""
        if art_label and art_label in self.article_map:
            art_id = self.article_map[art_label]
            self._selected_article_id = art_id
            self.entry_article.configure(state="normal")
            self.entry_article.delete(0, "end")
            self.entry_article.insert(0, art_label)
            self.entry_article.configure(state="readonly")
            self._load_unites(art_id)

        if rv[5] and rv[5] != "-":
            self.combo_unite.set(rv[5])
        if rv[1] and rv[1] != "-":
            self.combo_magasin.set(rv[1])
        if rv[7] and rv[7] != "-":
            self.entry_qte.delete(0, "end")
            self.entry_qte.insert(0, rv[7])
        if rv[9] and rv[9] != "-":
            self.textbox_obs.insert("1.0", rv[9])

    def _save(self, status_override=None):
        art_label = self.entry_article.get().strip()
        unite     = self.combo_unite.get().strip()
        mag       = self.combo_magasin.get().strip()

        if not art_label or not unite or not mag:
            messagebox.showwarning("Champs manquants",
                                   "Article, Unité et Magasin sont obligatoires.",
                                   parent=self)
            return
        try:
            qte = float(self.entry_qte.get().replace(",", "."))
        except Exception:
            messagebox.showwarning("Quantité invalide",
                                   "Saisissez une valeur numérique.", parent=self)
            return

        obs    = self.textbox_obs.get("1.0", "end").strip()
        now    = datetime.now()
        statut = status_override or "Non vérifié"
        art_id = self._selected_article_id or self.article_map.get(art_label)

        try:
            cur = self._get_cursor()
            if self.mode == "ajout":
                cur.execute(
                    """INSERT INTO tb_inventaire_temporaire
                       (date_creation,date_mise_ajour,idarticle,idunite,idmagasin,
                        qte_corrige,iduser,iduserverificateur,statut,deleted,observation)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,0,%s)""",
                    (now, now, art_id, self.unite_map.get(unite),
                     self.magasin_map.get(mag), qte,
                     self.current_user_id, None, statut, obs)
                )
            else:
                cur.execute(
                    """UPDATE tb_inventaire_temporaire
                       SET date_mise_ajour=%s,idarticle=%s,idunite=%s,idmagasin=%s,
                           qte_corrige=%s,statut=%s,observation=%s
                       WHERE id=%s""",
                    (now, art_id, self.unite_map.get(unite),
                     self.magasin_map.get(mag), qte, statut, obs,
                     self.inv_id)
                )
            self._commit()
            messagebox.showinfo("✅ Succès", "Inventaire enregistré.", parent=self)
            self._on_save()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erreur", str(e), parent=self)


# ─────────────────────────────────────────────────────────────────────────────
# MODAL Vérification
# ─────────────────────────────────────────────────────────────────────────────

class ModalVerification(ctk.CTkToplevel):
    def __init__(self, master, inv_id, row_values, current_user_id, on_refresh):
        super().__init__(master)
        self.inv_id = inv_id
        self.row_values = row_values
        self.current_user_id = current_user_id
        self._on_refresh = on_refresh

        self.title("Vérification inventaire")
        self.geometry("520x360")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_PAGE)
        self.grab_set()
        self.focus_set()
        try:
            self.transient(master)
        except Exception:
            pass
        self.attributes("-topmost", True)
        self.lift(master)
        self.focus_force()
        self._center()
        self._build_ui()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth()  // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        hdr = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT,
                            corner_radius=0, height=42)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="  ✅  Vérification inventaire",
                     font=Fonts.bold(13), text_color=Colors.TEXT_ON_DARK,
                     anchor="w").pack(side="left", padx=16, fill="y")

        body = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        body.pack(fill="both", expand=True, padx=16, pady=10)
        body.grid_columnconfigure(1, weight=1)

        def lbl(row, text):
            ctk.CTkLabel(body, text=text, font=Fonts.label(10),
                         text_color=Colors.TEXT_SECONDARY, anchor="w"
                         ).grid(row=row, column=0, padx=(0, 8), pady=3, sticky="w")

        def val(row, text):
            ctk.CTkLabel(body, text=text, font=Fonts.body(11),
                         text_color=Colors.TEXT_PRIMARY, anchor="w"
                         ).grid(row=row, column=1, pady=3, sticky="w")

        # row_values indexes:
        # 0=id, 1=magasin, 2=user, 3=datetime, 4=article, 5=unite,
        # 6=magasin_stock, 7=qte, 8=qte_stock, 9=obs, 10=statut, 11=maj, 12=verificateur
        lbl(0, "Article");     val(0, self.row_values[4])
        lbl(1, "Unité");       val(1, self.row_values[5])
        lbl(2, "Magasin");     val(2, self.row_values[1])
        lbl(3, "Qté corrigée");val(3, self.row_values[7])
        lbl(4, "Qté en stock");val(4, self.row_values[8])

        lbl(5, "Observation")
        self.obs = ctk.CTkTextbox(
            body, height=70, fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER, border_width=1,
            font=Fonts.body(11), corner_radius=6
        )
        self.obs.grid(row=5, column=1, pady=3, sticky="ew")
        self.obs.insert("1.0", self.row_values[9] if self.row_values[9] != "-" else "")
        self.obs.configure(state="disabled")

        self.var_verif = ctk.BooleanVar(value=(self.row_values[10] == "Vérifié"))
        ctk.CTkCheckBox(
            body, text="Marquer comme vérifié",
            variable=self.var_verif, command=self._toggle_verif,
            fg_color=Colors.SUCCESS, hover_color=Colors.SUCCESS_DARK,
            text_color=Colors.TEXT_PRIMARY, font=Fonts.bold(11)
        ).grid(row=6, column=1, pady=(8, 0), sticky="w")

        ctk.CTkButton(
            body, text="Fermer", width=100, height=28,
            fg_color=Colors.CLOUDS, hover_color=Colors.SILVER,
            text_color=Colors.TEXT_PRIMARY, font=Fonts.bold(11),
            border_width=1, border_color=Colors.BORDER,
            command=self.destroy
        ).grid(row=7, column=1, pady=(10, 0), sticky="e")

    def _toggle_verif(self):
        statut = "Vérifié" if self.var_verif.get() else "Non vérifié"
        id_verif = self.current_user_id if self.var_verif.get() else None
        try:
            cur = db_manager.get_cursor()
            cur.execute(
                "UPDATE tb_inventaire_temporaire "
                "SET statut=%s, iduserverificateur=%s, date_mise_ajour=%s "
                "WHERE id=%s",
                (statut, id_verif, datetime.now(), self.inv_id)
            )
            db_manager.conn.commit()
            if self._on_refresh:
                self._on_refresh()
        except Exception as e:
            messagebox.showerror("Erreur", str(e), parent=self)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE PRINCIPALE
# ─────────────────────────────────────────────────────────────────────────────

class PageInventaireJour(ctk.CTkFrame):
    def __init__(self, parent, db_conn=None, session_data=None, mode="normal", **kwargs):
        super().__init__(parent, fg_color=Colors.BG_PAGE, **kwargs)
        self.db_conn         = db_conn
        self.session_data    = session_data or {}
        self.current_user_id = self._resolve_user_id(self.session_data)
        self.mode            = mode

        if not db_manager.connect():
            ctk.CTkLabel(self, text="❌  Erreur de connexion",
                         text_color=Colors.DANGER, font=Fonts.bold(14)
                         ).pack(pady=40)
            return

        self.user_map    = {}
        self.magasin_map = {}
        self.article_map = {}
        self.current_user_magasin_label = None
        self._footer_labels = {}

        _setup_style()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_filters()
        self._build_table()
        self._build_footer()

        self._load_filter_sources()
        self.load_inventaires()

    def _resolve_user_id(self, session_data):
        if isinstance(session_data, dict):
            sid = session_data.get("user_id") or session_data.get("iduser")
            if sid is not None:
                try: return int(sid)
                except: pass
        try:
            raw, _ = safe_file_read(get_session_path())
            data = json.loads(raw) if raw else {}
            sid  = data.get("user_id") or data.get("iduser")
            return int(sid) if sid else 1
        except Exception:
            return 1

    # ── En-tête ───────────────────────────────────────────────────────────────

    def _build_header(self):
        h = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT,
                          corner_radius=0, height=46)
        h.grid(row=0, column=0, sticky="ew")
        h.grid_propagate(False)
        h.grid_columnconfigure(1, weight=1)

        left = ctk.CTkFrame(h, fg_color="transparent")
        left.grid(row=0, column=0, padx=14, sticky="w")
        ctk.CTkLabel(left, text="📦", font=Fonts.heading(16),
                     text_color=Colors.TEXT_ON_DARK).pack(side="left", padx=(0, 8))
        inner = ctk.CTkFrame(left, fg_color="transparent")
        inner.pack(side="left")
        ctk.CTkLabel(inner, text="Inventaire du Jour",
                     font=Fonts.bold(13), text_color=Colors.TEXT_ON_DARK
                     ).pack(anchor="w")
        ctk.CTkLabel(inner, text="Suivi et correction des stocks",
                     font=Fonts.small(9), text_color=Colors.TEXT_ON_DARK_DIM
                     ).pack(anchor="w")

        ctk.CTkLabel(h, text=f"📅  {date.today().strftime('%d %B %Y')}",
                     font=Fonts.small(10), text_color=Colors.TEXT_ON_DARK_DIM
                     ).grid(row=0, column=2, padx=14)

    # ── Filtres ───────────────────────────────────────────────────────────────

    def _build_filters(self):
        fb = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=8)
        fb.grid(row=1, column=0, padx=8, pady=(6, 3), sticky="ew")

        def lbl(text, r, c, padl=10):
            ctk.CTkLabel(fb, text=text, font=Fonts.label(10),
                         text_color=Colors.TEXT_SECONDARY
                         ).grid(row=r, column=c,
                                padx=(padl, 4), pady=5, sticky="w")

        def mk_combo(values, w=130):
            return ctk.CTkComboBox(fb, values=values, state="readonly",
                                   height=28, width=w,
                                   fg_color=Colors.BG_INPUT,
                                   border_color=Colors.BORDER,
                                   button_color=Colors.PRIMARY,
                                   font=Fonts.body(11))

        # ── Ligne 0 ───────────────────────────────────────────────────────
        lbl("Début :", 0, 0)
        self.date_from = DateEntry(fb, width=140)
        self.date_from.grid(row=0, column=1, padx=(0, 10), pady=5)

        lbl("Fin :", 0, 2, 0)
        self.date_to = DateEntry(fb, width=140)
        self.date_to.grid(row=0, column=3, padx=(0, 10), pady=5)

        lbl("Recherche :", 0, 4, 0)
        self.search_entry = ctk.CTkEntry(
            fb, height=28, width=165,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            font=Fonts.body(11), corner_radius=6,
            placeholder_text="Article, observation…"
        )
        self.search_entry.grid(row=0, column=5, padx=(0, 10), pady=5)
        self.search_entry.bind("<KeyRelease>", lambda e: self.load_inventaires())

        lbl("Utilisateur :", 0, 6, 0)
        self.user_filter = mk_combo(["Tous"])
        self.user_filter.grid(row=0, column=7, padx=(0, 8), pady=5)

        # ── Ligne 1 ───────────────────────────────────────────────────────
        lbl("Magasin :", 1, 0)
        self.magasin_filter = mk_combo(["Tous"])
        self.magasin_filter.grid(row=1, column=1, padx=(0, 10), pady=5)

        lbl("Statut :", 1, 2, 0)
        self.statut_filter = mk_combo(["Tous"] + STATUTS, w=118)
        self.statut_filter.set("Tous")
        self.statut_filter.grid(row=1, column=3, padx=(0, 10), pady=5)

        # Boutons groupés ligne 1 droite
        btn_grp = ctk.CTkFrame(fb, fg_color="transparent")
        btn_grp.grid(row=1, column=6, columnspan=2,
                     padx=(0, 8), pady=5, sticky="e")

        for text, color, hover, cmd in [
            ("🔍 Filtrer",  Colors.PRIMARY,  Colors.PRIMARY_HOVER, self.load_inventaires),
            ("↺ Reset",     Colors.CLOUDS,   Colors.SILVER,        self._reset_filters),
            ("📊 Excel",    Colors.PREMIUM,  Colors.PREMIUM_DARK,  self.export_excel),
        ]:
            btn = ctk.CTkButton(btn_grp, text=text, width=86, height=28,
                                fg_color=color, hover_color=hover,
                                text_color=(Colors.TEXT_PRIMARY
                                            if color == Colors.CLOUDS
                                            else Colors.TEXT_ON_DARK),
                                font=Fonts.bold(11), corner_radius=6,
                                command=cmd)
            if color == Colors.CLOUDS:
                btn.configure(border_width=1, border_color=Colors.BORDER)
            btn.pack(side="left", padx=(0, 5))

    # ── Tableau avec badge statut ─────────────────────────────────────────────

    def _build_table(self):
        card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=8)
        card.grid(row=2, column=0, padx=8, pady=(0, 3), sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(0, weight=1)

        # Colonnes : ID et Magasin cachés, Statut affiché comme badge texte
        cols = ("ID", "Magasin", "Utilisateur", "Date/Heure",
                "Article", "Unité", "Magasin stock",
                "Qté corrigée", "Qté en Stock", "Observation",
                "Statut", "Dernière MàJ", "Vérificateur")

        self.tree = ttk.Treeview(card, columns=cols, show="headings",
                                  style="Inv.Treeview", selectmode="browse")

        verif_qte_stock_w = 90 if self.mode == "verification" else 0
        verif_user_w = 120 if self.mode == "verification" else 0
        for col, w, anc in [
            ("ID",           0,   "center"),
            ("Magasin",      0,   "w"),
            ("Utilisateur",  118, "w"),
            ("Date/Heure",   118, "center"),
            ("Article",        160, "w"),
            ("Unité",          80,  "center"),
            ("Magasin stock",  120, "w"),
            ("Qté corrigée",   80,  "center"),
            ("Qté en Stock",   verif_qte_stock_w,  "center"),
            ("Observation",    150, "w"),
            ("Statut",         100, "center"),
            ("Dernière MàJ",   118, "center"),
            ("Vérificateur",   verif_user_w, "w"),
        ]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor=anc,
                              minwidth=0 if w == 0 else 30,
                              stretch=(w != 0))

        # Tags alternance fond + couleur par statut (foreground pour le badge texte)
        self.tree.tag_configure("even", background=Colors.BG_CARD)
        self.tree.tag_configure("odd",  background=Colors.BG_ROW_ALT)
        self.tree.tag_configure("st_ok",
                                foreground=Colors.SUCCESS_TEXT,
                                background=Colors.SUCCESS_LIGHT)
        self.tree.tag_configure("st_wait",
                                foreground=Colors.WARNING_TEXT,
                                background=Colors.WARNING_LIGHT)
        self.tree.tag_configure("st_cancel",
                                foreground=Colors.DANGER_TEXT,
                                background=Colors.DANGER_LIGHT)

        vsb = ttk.Scrollbar(card, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(card, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(4, 0), pady=4)
        vsb.grid(row=0, column=1, sticky="ns", pady=4)
        hsb.grid(row=1, column=0, sticky="ew", padx=(4, 0))
        self.tree.bind("<Double-1>", self._on_double_click)

    # ── Footer stats bien aligné ──────────────────────────────────────────────

    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=8)
        footer.grid(row=3, column=0, padx=8, pady=(0, 6), sticky="ew")
        # Poids : stats à gauche, bouton à droite
        footer.grid_columnconfigure(1, weight=0)
        footer.grid_columnconfigure(2, weight=1)   # spacer

        # ── Bloc stats groupé ─────────────────────────────────────────────
        stats_frame = ctk.CTkFrame(footer, fg_color="transparent")
        stats_frame.grid(row=0, column=0, padx=(10, 0), pady=6, sticky="w")

        self._footer_labels = {}
        stat_defs = [
            ("total",       "📋 Total",        Colors.TEXT_PRIMARY),
            ("verifie",     "✅ Vérifié",      Colors.SUCCESS_TEXT),
            ("non_verifie", "🟠 Non vérifié",  Colors.WARNING_TEXT),
            ("annule",      "🔴 Annulé",       Colors.DANGER_TEXT),
        ]
        for i, (key, label, color) in enumerate(stat_defs):
            # Chaque stat = une mini-card inline
            cell = ctk.CTkFrame(stats_frame, fg_color=Colors.BG_PAGE,
                                corner_radius=6)
            cell.pack(side="left", padx=(0 if i == 0 else 6, 0))

            ctk.CTkLabel(cell, text=label,
                         font=Fonts.label(10), text_color=color,
                         anchor="w"
                         ).pack(side="left", padx=(8, 3), pady=4)

            val_lbl = ctk.CTkLabel(cell, text="0",
                                   font=Fonts.bold(12), text_color=color)
            val_lbl.pack(side="left", padx=(0, 8), pady=4)
            self._footer_labels[key] = val_lbl

        # ── Bouton Nouveau à droite ───────────────────────────────────────
        if self.mode != "verification":
            ctk.CTkButton(footer, text="➕  Nouvel inventaire",
                          width=150, height=28,
                          fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
                          font=Fonts.bold(11), corner_radius=6,
                          command=self._ouvrir_modal_ajout,
                          ).grid(row=0, column=3, padx=(0, 10), pady=6, sticky="e")

    # ── Sources filtres ───────────────────────────────────────────────────────

    def _load_filter_sources(self):
        try:
            cur = db_manager.get_cursor()
            cur.execute(
                """SELECT iduser,
                          COALESCE(username, nomuser||' '||prenomuser, 'Utilisateur')
                   FROM tb_users WHERE deleted=0 ORDER BY username"""
            )
            self.user_map = {r[1]: r[0] for r in cur.fetchall()}
            self.user_filter.configure(values=["Tous"] + list(self.user_map.keys()))
            self.user_filter.set("Tous")

            cur.execute("SELECT idmag, designationmag FROM tb_magasin "
                        "WHERE deleted=0 ORDER BY designationmag")
            self.magasin_map = {r[1]: r[0] for r in cur.fetchall()}
            self.magasin_filter.configure(
                values=["Tous"] + list(self.magasin_map.keys()))
            self.magasin_filter.set("Tous")

            try:
                cur.execute("SELECT idmag FROM tb_users WHERE iduser=%s",
                            (self.current_user_id,))
                row = cur.fetchone()
                if row and row[0] is not None:
                    id_to_label = {v: k for k, v in self.magasin_map.items()}
                    self.current_user_magasin_label = id_to_label.get(row[0])
            except Exception:
                self.current_user_magasin_label = None
            if self.mode != "verification" and self.current_user_magasin_label in self.magasin_map:
                self.magasin_filter.set(self.current_user_magasin_label)

            cur.execute("SELECT idarticle, designation FROM tb_article "
                        "WHERE deleted=0 ORDER BY designation")
            self.article_map = {r[1]: r[0] for r in cur.fetchall()}
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur filtres : {e}")

    # ── Chargement tableau ────────────────────────────────────────────────────

    def load_inventaires(self):
        self.tree.delete(*self.tree.get_children())
        rows = []
        try:
            cur    = db_manager.get_cursor()
            where  = ["t.deleted=0"]
            params = []

            search = self.search_entry.get().strip().lower()
            if search:
                where.append(
                    "(LOWER(a.designation) LIKE %s OR LOWER(t.observation) LIKE %s "
                    "OR LOWER(COALESCE(u.username,'')) LIKE %s)"
                )
                like = f"%{search}%"
                params.extend([like, like, like])

            df_ = self._parse_date(self.date_from.get())
            dt_ = self._parse_date(self.date_to.get())
            if df_: where.append("t.date_creation::date >= %s"); params.append(df_)
            if dt_: where.append("t.date_creation::date <= %s"); params.append(dt_)

            ul = self.user_filter.get()
            if ul and ul != "Tous":
                where.append("t.iduser=%s"); params.append(self.user_map.get(ul))

            ml = self.magasin_filter.get()
            if ml and ml != "Tous":
                where.append("t.idmagasin=%s"); params.append(self.magasin_map.get(ml))

            st = self.statut_filter.get()
            if st and st != "Tous":
                where.append("t.statut=%s"); params.append(st)

            cur.execute(f"""
                SELECT t.id, m_inv.designationmag,
                       COALESCE(u.username, u.nomuser||' '||u.prenomuser,'Utilisateur'),
                       t.date_creation, a.designation, un.designationunite,
                       COALESCE(m_stock.designationmag, '-') AS magasin_stock,
                       t.qte_corrige, t.observation, t.statut, t.date_mise_ajour,
                       COALESCE(uv.username, uv.nomuser||' '||uv.prenomuser, '-') AS verificateur,
                       t.idarticle, t.idunite, t.idmagasin
                FROM tb_inventaire_temporaire t
                LEFT JOIN tb_users    u        ON t.iduser    = u.iduser
                LEFT JOIN tb_users    uv       ON t.iduserverificateur = uv.iduser
                LEFT JOIN tb_article  a        ON t.idarticle = a.idarticle
                LEFT JOIN tb_unite    un       ON t.idunite   = un.idunite
                LEFT JOIN tb_magasin  m_inv    ON t.idmagasin = m_inv.idmag
                LEFT JOIN tb_magasin  m_stock  ON a.idmag     = m_stock.idmag
                WHERE {" AND ".join(where)}
                ORDER BY t.date_creation DESC
            """, tuple(params))
            rows = cur.fetchall()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

        STATUT_TAG_MAP = {
            "Vérifié":     "st_ok",
            "Non vérifié": "st_wait",
            "Annulé":      "st_cancel",
        }
        for idx, row in enumerate(rows):
            statut  = row[9] or "Non vérifié"
            st_tag  = STATUT_TAG_MAP.get(statut, "st_wait")
            alt_tag = "even" if idx % 2 == 0 else "odd"
            qte_stock = self._calc_stock_article(row[12], row[13], row[14])
            qte_stock_txt = f"{qte_stock:.2f}" if qte_stock is not None else "-"
            # Le tag statut surcharge la couleur de fond + foreground de toute la ligne
            self.tree.insert("", "end", tags=(st_tag,), values=(
                row[0], self._safe(row[1]),
                self._safe(row[2]), self._fmt_dt(row[3]),
                self._safe(row[4]), self._safe(row[5]),
                self._safe(row[6]), self._safe(row[7]),
                qte_stock_txt,
                self._safe(row[8]),
                statut,
                self._fmt_dt(row[10]),
                self._safe(row[11]),
            ))

        self._update_footer(rows)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _ouvrir_modal_ajout(self):
        ModalInventaire(
            self, on_save=self.load_inventaires,
            db_get_cursor=db_manager.get_cursor,
            db_commit=db_manager.conn.commit,
            article_map=self.article_map,
            magasin_map=self.magasin_map,
            current_user_id=self.current_user_id,
            mode="ajout",
            default_magasin_label=self.current_user_magasin_label
        )

    def _on_double_click(self, event):
        item = self.tree.identify("item", event.x, event.y)
        if not item: return
        rv = self.tree.item(item, "values")
        if self.mode == "verification":
            ModalVerification(
                self,
                inv_id=rv[0],
                row_values=rv,
                current_user_id=self.current_user_id,
                on_refresh=self.load_inventaires,
            )
            return
        ModalInventaire(
            self, on_save=self.load_inventaires,
            db_get_cursor=db_manager.get_cursor,
            db_commit=db_manager.conn.commit,
            article_map=self.article_map,
            magasin_map=self.magasin_map,
            current_user_id=self.current_user_id,
            mode="modification", row_values=rv
        )

    def _reset_filters(self):
        self.date_from.clear()
        self.date_to.clear()
        self.search_entry.delete(0, "end")
        self.user_filter.set("Tous")
        self.magasin_filter.set("Tous")
        self.statut_filter.set("Tous")
        self.load_inventaires()

    def export_excel(self):
        data = [self.tree.item(i, "values")[2:]
                for i in self.tree.get_children()]
        if not data:
            messagebox.showinfo("Info", "Aucune donnée."); return
        df = pd.DataFrame(data, columns=[
            "Utilisateur", "Date/Heure", "Article", "Unité", "Magasin stock",
            "Qté corrigée", "Qté en Stock", "Observation",
            "Statut", "Dernière MàJ", "Vérificateur"])
        p = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                          filetypes=[("Excel", "*.xlsx")])
        if p:
            df.to_excel(p, index=False)
            messagebox.showinfo("✅ Succès", "Export réussi.")

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _update_footer(self, rows):
        total       = len(rows)
        verifie     = sum(1 for r in rows if r[9] == "Vérifié")
        annule      = sum(1 for r in rows if r[9] == "Annulé")
        non_verifie = total - verifie - annule
        self._footer_labels["total"].configure(text=str(total))
        self._footer_labels["verifie"].configure(text=str(verifie))
        self._footer_labels["non_verifie"].configure(text=str(non_verifie))
        self._footer_labels["annule"].configure(text=str(annule))

    def _parse_date(self, value: str):
        if not value: return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except Exception:
            return None

    def _calc_stock_article(self, idarticle, idunite_cible, idmag=None):
        if not idarticle or not idunite_cible:
            return None
        _SQL_STOCK = """
        WITH
          params AS (
            SELECT
              %(p_idarticle)s::integer AS p_idarticle,
              %(p_idunite)s::integer   AS p_idunite,
              %(p_idmag)s::integer     AS p_idmag
          ),
          unite_hierarchie AS (
            SELECT
              u.idarticle,
              u.idunite,
              u.niveau,
              CASE WHEN COALESCE(u.qtunite, 1) > 0 THEN u.qtunite ELSE 1 END AS qtunite
            FROM tb_unite u, params p
            WHERE u.idarticle = p.p_idarticle
              AND COALESCE(u.deleted, 0) = 0
          ),
          unite_coeff AS (
            SELECT
              idarticle,
              idunite,
              EXP(
                SUM(LN(qtunite))
                OVER (
                  PARTITION BY idarticle
                  ORDER BY niveau
                  ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                )
              ) AS coeff_vers_base
            FROM unite_hierarchie
          ),
          coeff_cible AS (
            SELECT uc.coeff_vers_base AS coeff
            FROM unite_coeff uc, params p
            WHERE uc.idunite = p.p_idunite
          ),
          code_cible AS (
            SELECT u.codearticle
            FROM tb_unite u, params p
            WHERE u.idarticle = p.p_idarticle
              AND u.idunite   = p.p_idunite
            LIMIT 1
          ),
          rec AS (
            SELECT lf.idunite, lf.idmag, SUM(lf.qtlivrefrs) AS qt
            FROM tb_livraisonfrs lf, params p
            WHERE lf.idarticle = p.p_idarticle
              AND lf.deleted   = 0
              AND (p.p_idmag IS NULL OR lf.idmag = p.p_idmag)
            GROUP BY lf.idunite, lf.idmag
          ),
          ven AS (
            SELECT vd.idunite, v.idmag, SUM(vd.qtvente) AS qt
            FROM tb_ventedetail vd
            INNER JOIN tb_vente v ON v.id      = vd.idvente
                                  AND v.deleted = 0
                                  AND v.statut  = 'VALIDEE',
                 params p
            WHERE vd.idarticle = p.p_idarticle
              AND vd.deleted   = 0
              AND (p.p_idmag IS NULL OR v.idmag = p.p_idmag)
            GROUP BY vd.idunite, v.idmag
          ),
          t_in AS (
            SELECT td.idunite, td.idmagentree AS idmag, SUM(td.qttransfert) AS qt
            FROM tb_transfertdetail td, params p
            WHERE td.idarticle = p.p_idarticle
              AND td.deleted   = 0
              AND (p.p_idmag IS NULL OR td.idmagentree = p.p_idmag)
            GROUP BY td.idunite, td.idmagentree
          ),
          t_out AS (
            SELECT td.idunite, td.idmagsortie AS idmag, SUM(td.qttransfert) AS qt
            FROM tb_transfertdetail td, params p
            WHERE td.idarticle = p.p_idarticle
              AND td.deleted   = 0
              AND (p.p_idmag IS NULL OR td.idmagsortie = p.p_idmag)
            GROUP BY td.idunite, td.idmagsortie
          ),
          sor AS (
            SELECT sd.idunite, sd.idmag, SUM(sd.qtsortie) AS qt
            FROM tb_sortiedetail sd, params p
            WHERE sd.idarticle = p.p_idarticle
              AND (p.p_idmag IS NULL OR sd.idmag = p.p_idmag)
            GROUP BY sd.idunite, sd.idmag
          ),
          inv AS (
            SELECT u.idunite, i.idmag, SUM(i.qtinventaire) AS qt
            FROM tb_inventaire i
            INNER JOIN tb_unite u ON u.codearticle = i.codearticle
            CROSS JOIN params p
            CROSS JOIN code_cible cc
            WHERE i.codearticle = cc.codearticle
              AND u.idarticle   = p.p_idarticle
              AND (p.p_idmag IS NULL OR i.idmag = p.p_idmag)
            GROUP BY u.idunite, i.idmag
          ),
          avo AS (
            SELECT ad.idunite, ad.idmag, SUM(ad.qtavoir) AS qt
            FROM tb_avoirdetail ad
            INNER JOIN tb_avoir a ON a.id = ad.idavoir AND a.deleted = 0,
                 params p
            WHERE ad.idarticle = p.p_idarticle
              AND ad.deleted   = 0
              AND (p.p_idmag IS NULL OR ad.idmag = p.p_idmag)
            GROUP BY ad.idunite, ad.idmag
          ),
          conso AS (
            SELECT cd.idunite, cd.idmag, SUM(cd.qtconsomme) AS qt
            FROM tb_consommationinterne_details cd, params p
            WHERE cd.idarticle = p.p_idarticle
              AND (p.p_idmag IS NULL OR cd.idmag = p.p_idmag)
            GROUP BY cd.idunite, cd.idmag
          ),
          ech_in AS (
            SELECT dce.idunite, dce.idmagasin AS idmag, SUM(dce.quantite_entree) AS qt
            FROM tb_detailchange_entree dce, params p
            WHERE dce.idarticle = p.p_idarticle
              AND (p.p_idmag IS NULL OR dce.idmagasin = p.p_idmag)
            GROUP BY dce.idunite, dce.idmagasin
          ),
          ech_out AS (
            SELECT dcs.idunite, dcs.idmagasin AS idmag, SUM(dcs.quantite_sortie) AS qt
            FROM tb_detailchange_sortie dcs, params p
            WHERE dcs.idarticle = p.p_idarticle
              AND (p.p_idmag IS NULL OR dcs.idmagasin = p.p_idmag)
            GROUP BY dcs.idunite, dcs.idmagasin
          ),
          solde_base AS (
            SELECT
              SUM(
                (  COALESCE(r.qt,  0)
                 + COALESCE(ti.qt, 0)
                 + COALESCE(iv.qt, 0)
                 + COALESCE(av.qt, 0)
                 + COALESCE(ei.qt, 0)
                 - COALESCE(ve.qt, 0)
                 - COALESCE(so.qt, 0)
                 - COALESCE(to_.qt, 0)
                 - COALESCE(co.qt,  0)
                 - COALESCE(eo.qt,  0)
                ) * uc.coeff_vers_base
              ) AS total_base
            FROM unite_coeff uc
            LEFT JOIN rec     r   ON r.idunite   = uc.idunite
            LEFT JOIN ven     ve  ON ve.idunite  = uc.idunite
            LEFT JOIN t_in    ti  ON ti.idunite  = uc.idunite
            LEFT JOIN t_out   to_ ON to_.idunite = uc.idunite
            LEFT JOIN sor     so  ON so.idunite  = uc.idunite
            LEFT JOIN inv     iv  ON iv.idunite  = uc.idunite
            LEFT JOIN avo     av  ON av.idunite  = uc.idunite
            LEFT JOIN conso   co  ON co.idunite  = uc.idunite
            LEFT JOIN ech_in  ei  ON ei.idunite  = uc.idunite
            LEFT JOIN ech_out eo  ON eo.idunite  = uc.idunite
          )
        SELECT
          GREATEST(0,
            COALESCE(sb.total_base, 0) / NULLIF(cc.coeff, 0)
          ) AS stock_reel
        FROM solde_base sb, coeff_cible cc
        """
        try:
            if not db_manager.conn or db_manager.conn.closed:
                if not db_manager.connect():
                    return None
            cursor = db_manager.conn.cursor()
            cursor.execute(
                _SQL_STOCK,
                {"p_idarticle": idarticle, "p_idunite": idunite_cible, "p_idmag": idmag},
            )
            row = cursor.fetchone()
            return row[0] if row and row[0] is not None else 0
        except Exception:
            return None
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def _fmt_dt(self, value):
        if not value: return "-"
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M")
        return str(value)

    def _safe(self, value):
        return str(value) if value and str(value).strip() else "-"


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    Theme.setup()
    root = ctk.CTk()
    Theme.apply(root)
    root.title("Inventaire du Jour — iJeery")
    root.geometry("1280x780")
    PageInventaireJour(root).pack(fill="both", expand=True)
    root.mainloop()
    db_manager.close_connection()
