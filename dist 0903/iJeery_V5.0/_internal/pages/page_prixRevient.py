# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                 iJeery — page_prixRevient.py  (refonte v2)                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  • Thème iJeery (app_theme) — même patron que page_ArticleMouvement         ║
║  • FournisseurSelectWindow  thémée                                          ║
║  • HistoriquePrixWindow     thémée                                          ║
║  • Logique métier SQL inchangée                                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import json
import threading

# ── Thème iJeery ──────────────────────────────────────────────────────────────
try:
    from app_theme import Colors, Fonts, styled, Theme
    _T = True
except ImportError:
    _T = False


class _C:
    """Fallback couleurs si app_theme absent."""
    MIDNIGHT        = "#2C3E50"
    MIDNIGHT_LIGHT  = "#34495E"
    BG_PAGE         = "#ECF0F1"
    BG_CARD         = "#FFFFFF"
    BG_HEADER       = "#2C3E50"
    BG_INPUT        = "#F4F6F8"
    BG_ROW_ALT      = "#F0F4F8"
    PRIMARY         = "#3498DB"
    PRIMARY_HOVER   = "#2980B9"
    PRIMARY_LIGHT   = "#D6EAF8"
    SUCCESS         = "#2ECC71"
    SUCCESS_DARK    = "#27AE60"
    SUCCESS_LIGHT   = "#D5F5E3"
    SUCCESS_TEXT    = "#1E8449"
    DANGER          = "#E74C3C"
    DANGER_DARK     = "#C0392B"
    DANGER_TEXT     = "#922B21"
    WARNING         = "#F39C12"
    INFO            = "#1ABC9C"
    INFO_DARK       = "#16A085"
    PREMIUM         = "#9B59B6"
    PREMIUM_DARK    = "#8E44AD"
    TEXT_PRIMARY    = "#2C3E50"
    TEXT_SECONDARY  = "#5D6D7E"
    TEXT_MUTED      = "#95A5A6"
    TEXT_ON_DARK    = "#FFFFFF"
    TEXT_ON_DARK_DIM= "#BDC3C7"
    BORDER          = "#D5D8DC"
    BORDER_FOCUS    = "#3498DB"
    DIVIDER         = "#E8EAED"
    SILVER          = "#BDC3C7"
    CLOUDS          = "#ECF0F1"


C = Colors if _T else _C


def _f(size=11, weight="normal"):
    return ctk.CTkFont(
        family="Roboto" if _T else "Segoe UI",
        size=size, weight=weight)


# ─────────────────────────────────────────────────────────────────────────────
#  Fenêtre de sélection de fournisseur
# ─────────────────────────────────────────────────────────────────────────────
class FournisseurSelectWindow(ctk.CTkToplevel):
    """Fenêtre modale thémée pour choisir un fournisseur."""

    def __init__(self, parent, fournisseurs: list, on_select_callback):
        super().__init__(parent)
        self.title("Sélectionner un fournisseur")
        self.geometry("440x500")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        if _T:
            Theme.apply_toplevel(self)

        self.on_select_callback  = on_select_callback
        self._all_fournisseurs   = fournisseurs

        self._apply_style()
        self._build_ui()
        self._populate(fournisseurs)

        self.update_idletasks()
        px = (parent.winfo_rootx()
              + (parent.winfo_width()  - self.winfo_width())  // 2)
        py = (parent.winfo_rooty()
              + (parent.winfo_height() - self.winfo_height()) // 2)
        self.geometry(f"+{px}+{py}")

    def _apply_style(self):
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure("Frs.Treeview",
                    background=C.BG_CARD, foreground=C.TEXT_PRIMARY,
                    fieldbackground=C.BG_CARD, rowheight=24,
                    font=("Roboto" if _T else "Segoe UI", 10),
                    borderwidth=0)
        s.configure("Frs.Treeview.Heading",
                    background=C.BG_HEADER, foreground="#FFFFFF",
                    font=("Roboto" if _T else "Segoe UI", 10, "bold"),
                    relief="flat")
        s.map("Frs.Treeview",
              background=[("selected", C.PRIMARY)],
              foreground=[("selected", "#FFFFFF")])

    def _build_ui(self):
        import tkinter as tk

        # En-tête
        hdr = ctk.CTkFrame(self, fg_color=C.BG_HEADER, corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text="Sélectionner un fournisseur",
                     font=_f(14, "bold"), text_color="#FFFFFF"
                     ).pack(side="left", padx=16, pady=10)

        # Barre de recherche
        bar = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=0)
        bar.pack(fill="x")
        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=8)

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", self._on_search)
        entry = ctk.CTkEntry(
            inner, textvariable=self._search_var,
            placeholder_text="Filtrer…",
            height=28, fg_color=C.BG_INPUT,
            border_color=C.BORDER, border_width=1,
            font=_f(10), corner_radius=6)
        entry.pack(fill="x")
        entry.focus_set()

        # Listbox dans une card
        card = ctk.CTkFrame(self, fg_color=C.BG_CARD,
                            corner_radius=0)
        card.pack(fill="both", expand=True, padx=10, pady=(0, 4))
        card.grid_rowconfigure(0, weight=1)
        card.grid_columnconfigure(0, weight=1)

        vsb = ttk.Scrollbar(card, orient="vertical")
        self._listbox = tk.Listbox(
            card, selectmode="single",
            font=("Roboto" if _T else "Segoe UI", 10),
            relief="flat", activestyle="dotbox",
            bg=C.BG_CARD, fg=C.TEXT_PRIMARY,
            selectbackground=C.PRIMARY,
            selectforeground="#FFFFFF",
            yscrollcommand=vsb.set,
            bd=0, highlightthickness=0)
        vsb.config(command=self._listbox.yview)
        self._listbox.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        vsb.grid(row=0, column=1, sticky="ns", pady=6, padx=(0, 4))

        self._listbox.bind("<Double-Button-1>", lambda _: self._confirm())
        self._listbox.bind("<Return>",          lambda _: self._confirm())

        # Boutons
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.pack(fill="x", padx=10, pady=(0, 12))

        ctk.CTkButton(
            btn_bar, text="✔  Sélectionner", height=32,
            fg_color=C.SUCCESS_DARK, hover_color=C.SUCCESS,
            text_color="#FFFFFF", font=_f(10, "bold"),
            corner_radius=6, command=self._confirm
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_bar, text="✕  Annuler", height=32,
            fg_color=C.CLOUDS, hover_color=C.SILVER,
            text_color=C.TEXT_PRIMARY, font=_f(10),
            border_width=1, border_color=C.BORDER,
            corner_radius=6, command=self.destroy
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_bar, text="↺  Tous", height=32,
            fg_color=C.WARNING, hover_color="#D68910",
            text_color="#FFFFFF", font=_f(10, "bold"),
            corner_radius=6, command=self._select_all
        ).pack(side="right")

    def _populate(self, items):
        self._listbox.delete(0, "end")
        for item in items:
            self._listbox.insert("end", item)

    def _on_search(self, *_):
        term = self._search_var.get().lower()
        self._populate([f for f in self._all_fournisseurs
                        if term in f.lower()])

    def _confirm(self):
        sel = self._listbox.curselection()
        if sel:
            self.on_select_callback(self._listbox.get(sel[0]))
            self.destroy()

    def _select_all(self):
        self.on_select_callback("")
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────
#  Fenêtre historique des prix de revient
# ─────────────────────────────────────────────────────────────────────────────
class HistoriquePrixWindow(ctk.CTkToplevel):

    def __init__(self, parent, connect_db_fn,
                 code_article: str, designation: str,
                 unite: str, idunite: int):
        super().__init__(parent)
        self.title(f"Historique — {designation} ({unite})")
        self.geometry("820x500")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()
        if _T:
            Theme.apply_toplevel(self)

        self._connect_db = connect_db_fn
        self._idunite    = idunite

        self._apply_style()
        self._build_ui(code_article, designation, unite)
        self._load_historique()

        self.update_idletasks()
        px = (parent.winfo_rootx()
              + (parent.winfo_width()  - self.winfo_width())  // 2)
        py = (parent.winfo_rooty()
              + (parent.winfo_height() - self.winfo_height()) // 2)
        self.geometry(f"+{px}+{py}")

    def _apply_style(self):
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure("Hist.Treeview",
                    background=C.BG_CARD, foreground=C.TEXT_PRIMARY,
                    fieldbackground=C.BG_CARD, rowheight=24,
                    font=("Roboto" if _T else "Segoe UI", 10),
                    borderwidth=0)
        s.configure("Hist.Treeview.Heading",
                    background=C.BG_HEADER, foreground="#FFFFFF",
                    font=("Roboto" if _T else "Segoe UI", 10, "bold"),
                    relief="flat", padding=(6, 4))
        s.map("Hist.Treeview",
              background=[("selected", C.PRIMARY)],
              foreground=[("selected", "#FFFFFF")])

    def _build_ui(self, code, designation, unite):
        # En-tête
        hdr = ctk.CTkFrame(self, fg_color=C.BG_HEADER, corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(
            hdr, text=f"📦  {code}  —  {designation}",
            font=_f(13, "bold"), text_color="#FFFFFF"
        ).pack(side="left", padx=16, pady=10)
        ctk.CTkLabel(
            hdr, text=f"Unité : {unite}",
            font=_f(11), text_color=C.TEXT_ON_DARK_DIM
        ).pack(side="right", padx=16)

        # Treeview
        tbl = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=0)
        tbl.pack(fill="both", expand=True, padx=12, pady=(10, 4))
        tbl.grid_rowconfigure(0, weight=1)
        tbl.grid_columnconfigure(0, weight=1)

        vsb = ctk.CTkScrollbar(tbl, orientation="vertical")
        hsb = ctk.CTkScrollbar(tbl, orientation="horizontal")

        self._tree = ttk.Treeview(
            tbl,
            columns=("date", "ref", "fournisseur", "prix"),
            show="headings",
            style="Hist.Treeview",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set)
        vsb.configure(command=self._tree.yview)
        hsb.configure(command=self._tree.xview)

        self._tree.tag_configure("even",  background=C.BG_CARD)
        self._tree.tag_configure("odd",   background="#F0F4F8")
        self._tree.tag_configure("first", background=C.SUCCESS_LIGHT)

        for col, label, w, anchor in [
            ("date",        "Date livraison",          150, "center"),
            ("ref",         "Réf. Facture / Réception", 240, "w"),
            ("fournisseur", "Fournisseur",              210, "w"),
            ("prix",        "Prix unitaire",            140, "e"),
        ]:
            self._tree.heading(col, text=label)
            self._tree.column(col, width=w, anchor=anchor, minwidth=80)

        self._tree.grid(row=0, column=0, sticky="nsew",
                        padx=(6, 0), pady=(6, 0))
        vsb.grid(row=0, column=1, sticky="ns", pady=(6, 0))
        hsb.grid(row=1, column=0, sticky="ew", padx=(6, 0))

        # Footer statut
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=14, pady=(2, 10))
        self._lbl_status = ctk.CTkLabel(
            footer, text="Chargement…",
            font=_f(9), text_color=C.TEXT_MUTED)
        self._lbl_status.pack(side="left")

    def _load_historique(self):
        threading.Thread(target=self._fetch_historique, daemon=True).start()

    def _fetch_historique(self):
        conn = self._connect_db()
        if not conn:
            self.after(0, lambda: self._lbl_status.configure(
                text="Erreur de connexion"))
            return
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT
                    lf.dateregistre,
                    COALESCE(lf.factfrs,   '—') AS ref_facture,
                    COALESCE(lf.reflivfrs, '—') AS ref_reception,
                    COALESCE(f.nomFrs, 'Inconnu') AS fournisseur,
                    cd.punitcmd
                FROM tb_livraisonfrs lf
                INNER JOIN tb_commande       com ON lf.idcom   = com.idcom
                INNER JOIN tb_commandedetail cd  ON cd.idcom   = com.idcom
                                                 AND cd.idunite = lf.idunite
                                                 AND cd.punitcmd IS NOT NULL
                                                 AND cd.punitcmd <> 0
                LEFT  JOIN tb_fournisseur    f   ON cd.idfrs  = f.idfrs
                WHERE lf.idunite  = %s
                  AND lf.deleted  = 0
                  AND com.deleted = 0
                ORDER BY lf.dateregistre DESC
            """, (self._idunite,))
            rows = cur.fetchall()
            cur.close()
            conn.close()
            self.after(0, lambda r=rows: self._populate_tree(r))
        except Exception as e:
            try:
                conn.close()
            except Exception:
                pass
            self.after(0, lambda ex=e: self._lbl_status.configure(
                text=f"Erreur : {ex}"))

    def _populate_tree(self, rows):
        for item in self._tree.get_children():
            self._tree.delete(item)
        for idx, row in enumerate(rows):
            date_str = (row[0].strftime("%d/%m/%Y %H:%M")
                        if row[0] else "—")
            ref = f"{row[1]}  /  {row[2]}"
            try:
                prix_fmt = (f"{float(row[4]):,.2f}"
                            .replace('.', '#').replace(',', '.')
                            .replace('#', ','))
            except Exception:
                prix_fmt = "0,00"
            tag = "first" if idx == 0 else (
                "even" if idx % 2 == 0 else "odd")
            self._tree.insert("", "end",
                              values=(date_str, ref, row[3], prix_fmt),
                              tags=(tag,))
        self._lbl_status.configure(
            text=(f"{len(rows)} entrée(s)  —  "
                  "ligne verte = prix le plus récent"))


# ─────────────────────────────────────────────────────────────────────────────
#  Page principale
# ─────────────────────────────────────────────────────────────────────────────
class PagePrixRevient(ctk.CTkFrame):

    def __init__(self, parent, db_connector=None, iduser=1):
        super().__init__(parent, fg_color=C.BG_PAGE)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.db_connector       = db_connector
        self.iduser             = iduser
        self.is_opening_window  = False
        self._destroyed         = False
        self.code_mapping       = {}
        self.idunite_mapping    = {}
        self._fournisseurs_list = []

        self._apply_tree_style()
        self._build_ui()

        self.after(100, self.load_data_async)
        self.after(100, self._load_fournisseurs_cache)
        self.bind("<Destroy>", self._on_destroy)

    # ── helpers ──────────────────────────────────────────────────────────────
    def _on_destroy(self, event):
        if event.widget == self:
            self._destroyed = True

    def _safe_ui(self, fn):
        try:
            if not self._destroyed and self.winfo_exists():
                self.after(0, fn)
        except Exception:
            pass

    # ── Style treeview ────────────────────────────────────────────────────────
    def _apply_tree_style(self):
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure("Rev.Treeview",
                    background=C.BG_CARD, foreground=C.TEXT_PRIMARY,
                    fieldbackground=C.BG_CARD, rowheight=24,
                    font=("Roboto" if _T else "Segoe UI", 10),
                    borderwidth=0)
        s.configure("Rev.Treeview.Heading",
                    background=C.BG_HEADER, foreground="#FFFFFF",
                    font=("Roboto" if _T else "Segoe UI", 10, "bold"),
                    relief="flat", padding=(6, 4))
        s.map("Rev.Treeview",
              background=[("selected", C.PRIMARY)],
              foreground=[("selected", "#FFFFFF")])

    # ── Construction UI ───────────────────────────────────────────────────────
    def _build_ui(self):
        # ── En-tête ──────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=C.BG_HEADER, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(hdr, text="Prix de Revient",
                     font=_f(18, "bold"),
                     text_color="#FFFFFF"
                     ).pack(side="left", padx=16, pady=8)

        # ── Barre de filtres ─────────────────────────────────────────────────
        panel = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=8)
        panel.grid(row=1, column=0, sticky="ew", padx=12, pady=6)
        inner = ctk.CTkFrame(panel, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=7)

        # Champ recherche principale
        ctk.CTkLabel(inner, text="🔍", font=_f(13),
                     width=24, anchor="center"
                     ).pack(side="left", padx=(0, 4))

        self.entry_search = ctk.CTkEntry(
            inner,
            placeholder_text="Code article, désignation, fournisseur…",
            height=28, fg_color=C.BG_INPUT,
            border_color=C.BORDER, border_width=1,
            text_color=C.TEXT_PRIMARY,
            font=_f(10), corner_radius=6)
        self.entry_search.pack(side="left", padx=(0, 8), fill="x",
                               expand=True)
        self.entry_search.bind("<KeyRelease>", self.search_data)

        # Séparateur
        ctk.CTkFrame(inner, width=1, height=20,
                     fg_color=C.BORDER).pack(side="left", padx=(0, 8))

        # Filtre fournisseur
        ctk.CTkLabel(inner, text="Fournisseur :",
                     font=_f(10), text_color=C.TEXT_MUTED
                     ).pack(side="left", padx=(0, 4))

        self._frs_var = ctk.StringVar(value="")
        self.entry_fournisseur = ctk.CTkEntry(
            inner, textvariable=self._frs_var,
            placeholder_text="Tous",
            height=28, fg_color=C.BG_INPUT,
            border_color=C.BORDER, border_width=1,
            text_color=C.TEXT_PRIMARY,
            font=_f(10), corner_radius=6,
            width=160, state="readonly")
        self.entry_fournisseur.pack(side="left", padx=(0, 2))

        # Bouton loupe fournisseur
        ctk.CTkButton(
            inner, text="🔎",
            width=28, height=28,
            fg_color=C.PRIMARY, hover_color=C.PRIMARY_HOVER,
            font=_f(12), corner_radius=6,
            command=self._open_fournisseur_picker
        ).pack(side="left", padx=(0, 2))

        # Bouton effacer fournisseur
        ctk.CTkButton(
            inner, text="✕",
            width=28, height=28,
            fg_color=C.CLOUDS, hover_color=C.SILVER,
            text_color=C.TEXT_SECONDARY,
            border_width=1, border_color=C.BORDER,
            font=_f(11), corner_radius=6,
            command=self._clear_fournisseur
        ).pack(side="left", padx=(0, 8))

        # Séparateur
        ctk.CTkFrame(inner, width=1, height=20,
                     fg_color=C.BORDER).pack(side="left", padx=(0, 8))

        # Checkbox "avec prix uniquement"
        self._only_with_price = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            inner,
            text="Avec prix uniquement",
            variable=self._only_with_price,
            font=_f(10), text_color=C.TEXT_PRIMARY,
            checkbox_width=16, checkbox_height=16,
            corner_radius=3,
            fg_color=C.PRIMARY, hover_color=C.PRIMARY_HOVER,
            command=self.load_data_async
        ).pack(side="left", padx=(0, 8))

        # Séparateur
        ctk.CTkFrame(inner, width=1, height=20,
                     fg_color=C.BORDER).pack(side="left", padx=(0, 8))

        # Bouton Réinitialiser
        ctk.CTkButton(
            inner, text="↺  Reset",
            height=28, width=90,
            fg_color="transparent", hover_color=C.DIVIDER,
            text_color=C.TEXT_SECONDARY,
            border_width=1, border_color=C.BORDER,
            font=_f(10), corner_radius=6,
            command=self._reset_all
        ).pack(side="left")

        # ── Tableau ──────────────────────────────────────────────────────────
        tbl = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=8)
        tbl.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 4))
        tbl.grid_rowconfigure(0, weight=1)
        tbl.grid_columnconfigure(0, weight=1)

        cols = ("code", "designation", "unite", "fournisseur", "prix")
        self.tree = ttk.Treeview(tbl, columns=cols,
                                 show="headings",
                                 style="Rev.Treeview",
                                 height=20)

        self.tree.tag_configure("even",      background=C.BG_CARD)
        self.tree.tag_configure("odd",       background="#F0F4F8")
        self.tree.tag_configure("even_zero", background=C.BG_CARD,
                                foreground=C.DANGER)
        self.tree.tag_configure("odd_zero",  background="#F0F4F8",
                                foreground=C.DANGER)

        col_cfg = {
            "code":        ("Code Article",        130, "center"),
            "designation": ("Désignation",         310, "w"),
            "unite":       ("Unité",               120, "center"),
            "fournisseur": ("Fournisseur (dernier)", 220, "w"),
            "prix":        ("Prix de revient",      150, "e"),
        }
        for col, (label, w, anchor) in col_cfg.items():
            self.tree.heading(col, text=label)
            self.tree.column(col, width=w, anchor=anchor, minwidth=80)

        sy = ctk.CTkScrollbar(tbl, orientation="vertical",
                              command=self.tree.yview)
        sx = ctk.CTkScrollbar(tbl, orientation="horizontal",
                              command=self.tree.xview)
        self.tree.configure(yscrollcommand=sy.set,
                            xscrollcommand=sx.set)
        self.tree.grid(row=0, column=0, sticky="nsew",
                       padx=(6, 0), pady=(6, 0))
        sy.grid(row=0, column=1, sticky="ns", pady=(6, 0))
        sx.grid(row=1, column=0, sticky="ew", padx=(6, 0))

        self.tree.bind("<Double-Button-1>", self._on_row_double_click)

        # ── Footer ───────────────────────────────────────────────────────────
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=12, pady=(2, 8))

        self.lbl_count = ctk.CTkLabel(
            footer, text="0 article(s)",
            font=_f(10, "bold"), text_color=C.PRIMARY)
        self.lbl_count.pack(side="left")

        self.lbl_status = ctk.CTkLabel(
            footer, text="",
            font=_f(9), text_color=C.TEXT_MUTED)
        self.lbl_status.pack(side="right")

    # ── Actions filtres ───────────────────────────────────────────────────────
    def _open_fournisseur_picker(self):
        FournisseurSelectWindow(self, self._fournisseurs_list,
                                self._on_fournisseur_selected)

    def _on_fournisseur_selected(self, value: str):
        self._frs_var.set(value)
        self.load_data_async()

    def _clear_fournisseur(self):
        self._frs_var.set("")
        self.load_data_async()

    def _reset_all(self):
        self.entry_search.delete(0, "end")
        self._frs_var.set("")
        self._only_with_price.set(False)
        self.load_data_async()

    def search_data(self, event=None):
        self.load_data_async(self.entry_search.get().strip())

    # ── Base de données ───────────────────────────────────────────────────────
    def connect_db(self):
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                cfg = json.load(f).get('database', {})
            return psycopg2.connect(
                host=cfg.get('host'), user=cfg.get('user'),
                password=cfg.get('password'), database=cfg.get('database'),
                port=cfg.get('port'))
        except FileNotFoundError:
            messagebox.showerror("Configuration",
                                 "Fichier 'config.json' introuvable.")
        except psycopg2.Error as err:
            messagebox.showerror("Connexion", str(err))
        except Exception as err:
            messagebox.showerror("Erreur", str(err))
        return None

    def _load_fournisseurs_cache(self):
        threading.Thread(target=self._fetch_fournisseurs,
                         daemon=True).start()

    def _fetch_fournisseurs(self):
        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT nomFrs FROM tb_fournisseur "
                        "WHERE deleted = 0 ORDER BY nomFrs ASC")
            self._fournisseurs_list = [r[0] for r in cur.fetchall()]
            cur.close()
            conn.close()
        except Exception:
            try:
                conn.close()
            except Exception:
                pass

    # ── Chargement données ────────────────────────────────────────────────────
    def load_data_async(self, search_term=""):
        if not isinstance(search_term, str):
            search_term = self.entry_search.get().strip()
        self._safe_ui(lambda: self.lbl_status.configure(text="Chargement…"))
        threading.Thread(target=self._load_data,
                         args=(search_term,), daemon=True).start()

    def _load_data(self, search_term=""):
        conn = self.connect_db()
        if not conn:
            self._safe_ui(lambda: self.lbl_status.configure(
                text="Erreur de connexion"))
            return
        try:
            cur = conn.cursor()
            query = """
                SELECT
                    LPAD(u.codearticle::TEXT, 10, '0') AS code,
                    a.designation,
                    u.designationunite,
                    COALESCE(f.nomFrs, 'Aucun fournisseur') AS fournisseur,
                    COALESCE(last_lf.punitcmd, 0)           AS dernier_prix,
                    u.idunite
                FROM tb_unite u
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN LATERAL (
                    SELECT cd.punitcmd, cd.idfrs
                    FROM tb_livraisonfrs lf
                    INNER JOIN tb_commande       com ON lf.idcom   = com.idcom
                    INNER JOIN tb_commandedetail cd  ON cd.idcom   = com.idcom
                                                     AND cd.idunite = u.idunite
                                                     AND cd.punitcmd IS NOT NULL
                                                     AND cd.punitcmd <> 0
                    WHERE lf.idunite = u.idunite
                      AND lf.deleted  = 0
                      AND com.deleted = 0
                    ORDER BY lf.dateregistre DESC
                    LIMIT 1
                ) last_lf ON TRUE
                LEFT JOIN tb_fournisseur f ON last_lf.idfrs = f.idfrs
                WHERE a.deleted = 0
                  AND u.deleted = 0
            """
            params, where_clauses = [], []

            frs_sel = self._frs_var.get().strip()
            if frs_sel:
                where_clauses.append("f.nomFrs = %s")
                params.append(frs_sel)

            if self._only_with_price.get():
                where_clauses.append(
                    "last_lf.punitcmd IS NOT NULL AND last_lf.punitcmd <> 0")

            if search_term:
                where_clauses.append("""(
                    LPAD(u.codearticle::TEXT, 10, '0') LIKE %s OR
                    LOWER(a.designation)      LIKE LOWER(%s) OR
                    LOWER(u.designationunite) LIKE LOWER(%s) OR
                    LOWER(f.nomFrs)           LIKE LOWER(%s)
                )""")
                p = f"%{search_term}%"
                params.extend([p, p, p, p])

            if where_clauses:
                query += " AND (" + " AND ".join(where_clauses) + ")"
            query += " ORDER BY a.designation ASC, u.codearticle ASC"

            cur.execute(query, params)
            rows = cur.fetchall()
            cur.close()
            conn.close()
            self._safe_ui(lambda r=rows: self._update_treeview(r))

        except psycopg2.Error as err:
            try:
                conn.close()
            except Exception:
                pass
            self._safe_ui(lambda e=err: messagebox.showerror(
                "Erreur SQL", str(e)))
        except Exception as ex:
            try:
                conn.close()
            except Exception:
                pass
            self._safe_ui(lambda e=ex: messagebox.showerror(
                "Erreur", str(e)))

    # ── Mise à jour treeview ──────────────────────────────────────────────────
    def _update_treeview(self, rows):
        if self._destroyed:
            return
        try:
            if not self.winfo_exists() or not self.tree.winfo_exists():
                return
        except Exception:
            return

        self.tree.delete(*self.tree.get_children())
        self.code_mapping    = {}
        self.idunite_mapping = {}

        for idx, row in enumerate(rows):
            if self._destroyed:
                return
            try:
                code        = row[0] or ""
                designation = row[1] or ""
                unite       = row[2] or ""
                fournisseur = row[3] or ""
                prix        = row[4] if row[4] is not None else 0
                idunite     = row[5]

                try:
                    prix_fmt = (f"{float(prix):,.2f}"
                                .replace('.', '#').replace(',', '.')
                                .replace('#', ','))
                    zero = float(prix) == 0
                except Exception:
                    prix_fmt = "0,00"
                    zero = True

                tag = ("even_zero" if zero else "even") if idx % 2 == 0 \
                    else ("odd_zero"  if zero else "odd")

                iid = self.tree.insert(
                    "", "end",
                    values=(code, designation, unite, fournisseur, prix_fmt),
                    tags=(tag,))
                self.code_mapping[iid]    = code
                self.idunite_mapping[iid] = idunite
            except Exception:
                return

        try:
            n = f"{len(rows):,}".replace(",", "\u202f")
            self.lbl_count.configure(text=f"{n} article(s)")
            self.lbl_status.configure(text="")
        except Exception:
            pass

    # ── Double-clic → historique ──────────────────────────────────────────────
    def _on_row_double_click(self, event=None):
        if self.is_opening_window:
            return
        sel = self.tree.selection()
        if not sel:
            return
        iid     = sel[0]
        values  = self.tree.item(iid, "values")
        idunite = self.idunite_mapping.get(iid)
        if not idunite:
            return
        self.is_opening_window = True
        try:
            HistoriquePrixWindow(self, self.connect_db,
                                 values[0], values[1], values[2], idunite)
        finally:
            self.after(400, lambda: setattr(self, 'is_opening_window', False))


# ─────────────────────────────────────────────────────────────────────────────
#  Test standalone
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        from app_theme import init_theme, Theme
        init_theme()
    except ImportError:
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Prix de Revient — iJeery")
    root.geometry("1200x700")
    root.minsize(800, 500)
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)

    try:
        Theme.apply(root)
    except Exception:
        pass

    PagePrixRevient(root).grid(row=0, column=0, sticky="nsew")
    root.mainloop()