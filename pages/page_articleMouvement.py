# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          iJeery — page_ArticleMouvement.py  (refonte v3)                   ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  • Requête SQL UNIFIÉE — un seul aller-retour DB pour tous les mouvements   ║
║  • Stock calculé en SQL par blocs de 50 lignes AVANT insertion treeview     ║
║  • Insertion par after() → UI reste réactive pendant le chargement          ║
║  • Zéro thread, zéro placeholder                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import customtkinter as ctk
from tkinter import ttk, messagebox, StringVar
from tkcalendar import DateEntry
import psycopg2
import json
from datetime import datetime, date
import sys
import os

from resource_utils import get_config_path, get_session_path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Thème iJeery ──────────────────────────────────────────────────────────────
try:
    from app_theme import Colors, Fonts, styled, Theme
    _T = True
except ImportError:
    _T = False


class _C:
    """Fallback couleurs si app_theme absent."""
    MIDNIGHT       = "#2C3E50"
    BG_PAGE        = "#ECF0F1"
    BG_CARD        = "#FFFFFF"
    BG_HEADER      = "#2C3E50"
    BG_INPUT       = "#F4F6F8"
    PRIMARY        = "#3498DB"
    PRIMARY_HOVER  = "#2980B9"
    SUCCESS        = "#2ECC71"
    SUCCESS_DARK   = "#27AE60"
    SUCCESS_LIGHT  = "#D5F5E3"
    SUCCESS_TEXT   = "#1E8449"
    DANGER         = "#E74C3C"
    DANGER_DARK    = "#C0392B"
    DANGER_LIGHT   = "#FADBD8"
    DANGER_TEXT    = "#922B21"
    WARNING        = "#F39C12"
    WARNING_LIGHT  = "#FEF9E7"
    WARNING_TEXT   = "#9A6A00"
    INFO           = "#1ABC9C"
    INFO_DARK      = "#16A085"
    TEXT_PRIMARY   = "#2C3E50"
    TEXT_SECONDARY = "#5D6D7E"
    TEXT_MUTED     = "#95A5A6"
    BORDER         = "#D5D8DC"
    DIVIDER        = "#E8EAED"
    SILVER         = "#BDC3C7"
    CLOUDS         = "#ECF0F1"


C = Colors if _T else _C

# Taille d'un bloc : lignes insérées par tick UI
_BATCH_SIZE = 50


# ─────────────────────────────────────────────────────────────────────────────
# Fenêtre recherche article
# ─────────────────────────────────────────────────────────────────────────────
class FenetreRechercheArticle(ctk.CTkToplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        
        self.callback = callback
        self.title("Recherche d'Article")
        self.geometry("820x520")
        self.transient(parent)
        self.grab_set()
        if _T:
            Theme.apply_toplevel(self)
        self._setup_ui()
        self._charger()

    def _connect(self):
        try:
            with open(get_config_path('config.json')) as f:
                cfg = json.load(f)['database']
            return psycopg2.connect(**cfg)
        except Exception as e:
            messagebox.showerror("Connexion", str(e))
            return None

    def _setup_ui(self):
        hdr = ctk.CTkFrame(self, fg_color=C.BG_HEADER, corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text="Recherche d'Article",
                     font=ctk.CTkFont(family="Roboto" if _T else "Segoe UI",
                                      size=15, weight="bold"),
                     text_color="#FFFFFF").pack(side="left", padx=16, pady=10)

        bar = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=0)
        bar.pack(fill="x")
        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=8)
        self._var_s = StringVar()
        self._var_s.trace("w", lambda *_: self._filter())
        ctk.CTkEntry(inner, textvariable=self._var_s,
                     placeholder_text="Nom ou code article…",
                     width=360, height=32,
                     fg_color=C.BG_INPUT, border_color=C.BORDER,
                     font=ctk.CTkFont(size=11)
                     ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(inner, text="Reinitialiser", command=self._charger,
                      fg_color=C.PRIMARY, hover_color=C.PRIMARY_HOVER,
                      text_color="#FFFFFF", height=32, width=130,
                      font=ctk.CTkFont(size=11)).pack(side="left")

        tbl = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=0)
        tbl.pack(fill="both", expand=True)
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Search.Treeview",
                        background=C.BG_CARD, foreground=C.TEXT_PRIMARY,
                        fieldbackground=C.BG_CARD, rowheight=24,
                        font=("Segoe UI", 10), borderwidth=0)
        style.configure("Search.Treeview.Heading",
                        background=C.BG_HEADER, foreground="#FFFFFF",
                        font=("Segoe UI", 10, "bold"), relief="flat")
        style.map("Search.Treeview",
                  background=[("selected", C.PRIMARY)],
                  foreground=[("selected", "#FFFFFF")])
        sy = ttk.Scrollbar(tbl, orient="vertical")
        sy.pack(side="right", fill="y")
        self._tree = ttk.Treeview(tbl,
                                  columns=("ID", "Designation", "Categorie"),
                                  show="headings", style="Search.Treeview",
                                  yscrollcommand=sy.set, height=18)
        sy.config(command=self._tree.yview)
        for col, w in [("ID", 90), ("Designation", 420), ("Categorie", 200)]:
            self._tree.heading(col, text=col)
            self._tree.column(col, width=w,
                              anchor="center" if col == "ID" else "w")
        self._tree.pack(fill="both", expand=True, padx=8, pady=6)
        self._tree.bind("<Double-Button-1>", lambda _: self._valider())
        self._tree.tag_configure("even", background=C.BG_CARD)
        self._tree.tag_configure("odd",  background="#F0F4F8")

        btn = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=0)
        btn.pack(fill="x")
        ctk.CTkButton(btn, text="Selectionner", command=self._valider,
                      fg_color=C.SUCCESS_DARK, hover_color=C.SUCCESS,
                      text_color="#FFFFFF", height=34, width=160,
                      font=ctk.CTkFont(size=12, weight="bold")
                      ).pack(side="left", padx=12, pady=8)
        ctk.CTkButton(btn, text="Annuler", command=self.destroy,
                      fg_color=C.DANGER, hover_color=C.DANGER_DARK,
                      text_color="#FFFFFF", height=34, width=120,
                      font=ctk.CTkFont(size=12)).pack(side="right", padx=12, pady=8)

    def _charger(self, recherche=""):
        for item in self._tree.get_children():
            self._tree.delete(item)
        conn = self._connect()
        if not conn:
            return
        try:
            cur = conn.cursor()
            if recherche:
                cur.execute("""
                    SELECT a.idarticle, a.designation,
                           COALESCE(c.designationcat,'Sans categorie')
                    FROM tb_article a
                    LEFT JOIN tb_categoriearticle c ON c.idca = a.idca
                    WHERE a.deleted = 0
                      AND (LOWER(a.designation) LIKE %s
                           OR CAST(a.idarticle AS TEXT) LIKE %s)
                    ORDER BY a.designation
                """, (f"%{recherche}%", f"%{recherche}%"))
            else:
                cur.execute("""
                    SELECT a.idarticle, a.designation,
                           COALESCE(c.designationcat,'Sans categorie')
                    FROM tb_article a
                    LEFT JOIN tb_categoriearticle c ON c.idca = a.idca
                    WHERE a.deleted = 0
                    ORDER BY a.designation
                """)
            for i, row in enumerate(cur.fetchall()):
                self._tree.insert("", "end", values=row,
                                  tags=("even" if i % 2 == 0 else "odd",))
        finally:
            conn.close()

    def _filter(self):
        self._charger(self._var_s.get().strip().lower())

    def _valider(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("Attention", "Selectionnez un article.")
            return
        v = self._tree.item(sel[0])['values']
        self.callback({'idarticle': v[0], 'designation': v[1],
                       'categorie': v[2]})
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────
# Page principale
# ─────────────────────────────────────────────────────────────────────────────
class PageArticleMouvement(ctk.CTkFrame):
    """
    Page Mouvements d'Articles.

    Chargement sans thread :
    1. Tous les mouvements recuperes en une passe SQL.
    2. Pour chaque bloc de _BATCH_SIZE lignes :
         a. Calcul des stocks via une seule requete SQL batch.
         b. Insertion dans le treeview avec les vrais stocks.
         c. Reschedule via after(5) → UI reste reactive.
    """

    def __init__(self, parent, initial_idarticle=None, db_conn=None,
                 session_data=None, iduser=None):
        super().__init__(parent, fg_color=C.BG_PAGE)

        # Fallback session depuis fichier si non fourni
        if session_data is None:
            try:
                with open(get_session_path(), encoding="utf-8") as f:
                    session_data = json.load(f)
            except Exception:
                session_data = {"menus": []}

        self._session_data = session_data

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.initial_idarticle     = initial_idarticle
        self.id_user_connecte      = self._get_uid(parent, iduser, session_data)
        self.selected_idarticle    = None
        self.selected_article_name = None
        self.magasin_name_to_id    = {}

        # Etat chargement par blocs
        self._pending_rows: list = []
        self._full_rows:    list = []
        self._after_id            = None
        self._db_conn             = None  # connexion maintenue pendant les batchs

        self._apply_tree_style()
        self._build_ui()
        self._load_magasins()
        self.load_mouvements()

    # ── helpers ──────────────────────────────────────────────────────────────
    def _get_uid(self, parent, iduser, session_data):
        for src in (iduser,
                    getattr(parent, "id_user_connecte", None),
                    getattr(parent, "iduser", None)):
            if src is not None:
                try:
                    return int(src)
                except (TypeError, ValueError):
                    pass
        try:
            with open(get_session_path(), encoding="utf-8") as f:
                return int(json.load(f).get("user_id", 0))
        except Exception:
            return None

    def _connect(self):
        try:
            with open(get_config_path('config.json')) as f:
                cfg = json.load(f)['database']
            return psycopg2.connect(**cfg)
        except Exception as e:
            messagebox.showerror("Connexion", str(e))
            return None

    def _f(self, size=11, weight="normal"):
        return ctk.CTkFont(family="Roboto" if _T else "Segoe UI",
                           size=size, weight=weight)

    def formater_nombre(self, nombre):
        try:
            nombre = float(nombre)
            partie_entiere = int(nombre)
            partie_decimale = abs(nombre - partie_entiere)
            str_entiere = f"{partie_entiere:,}".replace(',', ' ')
            str_decimale = f"{partie_decimale:.2f}".split('.')[1]
            return f"{str_entiere},{str_decimale}"
        except Exception:
            return "0,00"

    def _close_db_conn(self):
        if self._db_conn:
            try:
                self._db_conn.close()
            except Exception:
                pass
            self._db_conn = None

    # ── Style treeview ────────────────────────────────────────────────────────
    def _apply_tree_style(self):
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure("Mouv.Treeview",
                    background=C.BG_CARD, foreground=C.TEXT_PRIMARY,
                    fieldbackground=C.BG_CARD, rowheight=22,
                    font=("Roboto" if _T else "Segoe UI", 10),
                    borderwidth=0)
        s.configure("Mouv.Treeview.Heading",
                    background=C.BG_HEADER, foreground="#FFFFFF",
                    font=("Roboto" if _T else "Segoe UI", 10, "bold"),
                    relief="flat", padding=(6, 4))
        s.map("Mouv.Treeview",
              background=[("selected", C.PRIMARY)],
              foreground=[("selected", "#FFFFFF")])

    # ── Construction UI ───────────────────────────────────────────────────────
    def _build_ui(self):
        # En-tete
        hdr = ctk.CTkFrame(self, fg_color=C.BG_HEADER, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(hdr, text="Mouvements d'Articles",
                     font=self._f(18, "bold"), text_color="#FFFFFF"
                     ).pack(side="left", padx=16, pady=8)
        self._lbl_statut = ctk.CTkLabel(hdr, text="",
                                        font=self._f(9), text_color="#AAAAAA")
        self._lbl_statut.pack(side="right", padx=16)

        # Filtres
        panel = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=8)
        panel.grid(row=1, column=0, sticky="ew", padx=12, pady=6)
        inner = ctk.CTkFrame(panel, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=6)

        self._var_recherche = StringVar()
        self._var_recherche.trace("w", lambda *_: self._filter_client())
        self._entry_art = ctk.CTkEntry(
            inner, textvariable=self._var_recherche,
            placeholder_text="Rechercher article (Entree = DB)…",
            width=240, height=28,
            fg_color=C.BG_INPUT, border_color=C.BORDER,
            text_color=C.TEXT_PRIMARY, font=self._f(10))
        self._entry_art.pack(side="left", padx=(0, 4))
        self._entry_art.bind("<Return>", lambda _: self._search_db())

        ctk.CTkButton(inner, text="Parcourir",
                      command=self._ouvrir_recherche,
                      fg_color=C.PRIMARY, hover_color=C.PRIMARY_HOVER,
                      text_color="#FFFFFF", width=80, height=28,
                      font=self._f(10)).pack(side="left", padx=(0, 10))

        ctk.CTkFrame(inner, width=1, height=20,
                     fg_color=C.BORDER).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(inner, text="Type :", font=self._f(9),
                     text_color=C.TEXT_MUTED).pack(side="left", padx=(0, 3))
        self._combo_type = ttk.Combobox(
            inner,
            values=["Tous", "Entree", "Sortie", "Vente", "Transfert",
                    "Inventaire", "Avoir", "Consommation interne",
                    "Changement"],
            state="readonly", width=20,
            font=("Segoe UI", 9))
        self._combo_type.set("Tous")
        self._combo_type.pack(side="left", padx=(0, 10), ipady=2)

        ctk.CTkLabel(inner, text="Mag. :", font=self._f(9),
                     text_color=C.TEXT_MUTED).pack(side="left", padx=(0, 3))
        self._combo_mag = ttk.Combobox(
            inner, values=["Tous les magasins"],
            state="readonly", width=20, font=("Segoe UI", 9))
        self._combo_mag.set("Tous les magasins")
        self._combo_mag.pack(side="left", padx=(0, 10), ipady=2)

        ctk.CTkFrame(inner, width=1, height=20,
                     fg_color=C.BORDER).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(inner, text="Du :", font=self._f(9),
                     text_color=C.TEXT_MUTED).pack(side="left", padx=(0, 3))
        self._date_debut = DateEntry(inner, width=11,
                                     background=C.MIDNIGHT, foreground="white",
                                     borderwidth=1, date_pattern='dd/mm/yyyy',
                                     font=("Segoe UI", 9))
        self._date_debut.pack(side="left", padx=(0, 6), ipady=2)

        ctk.CTkLabel(inner, text="au :", font=self._f(9),
                     text_color=C.TEXT_MUTED).pack(side="left", padx=(0, 3))
        self._date_fin = DateEntry(inner, width=11,
                                   background=C.MIDNIGHT, foreground="white",
                                   borderwidth=1, date_pattern='dd/mm/yyyy',
                                   font=("Segoe UI", 9))
        self._date_fin.pack(side="left", padx=(0, 10), ipady=2)

        ctk.CTkButton(inner, text="Appliquer",
                      command=self.load_mouvements,
                      fg_color=C.SUCCESS_DARK, hover_color=C.SUCCESS,
                      text_color="#FFFFFF", height=28, width=100,
                      font=self._f(10, "bold")
                      ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(inner, text="Reset", command=self._reset,
                      fg_color="transparent", hover_color=C.DIVIDER,
                      text_color=C.TEXT_SECONDARY,
                      border_width=1, border_color=C.BORDER,
                      height=28, width=60, font=self._f(10)
                      ).pack(side="left")

        # Tableau
        tbl = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=8)
        tbl.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 4))
        tbl.grid_rowconfigure(0, weight=1)
        tbl.grid_columnconfigure(0, weight=1)

        cols = ("Date", "Reference", "Designation", "Type",
                "Unite", "Entree", "Sortie", "Stock",
                "Magasin", "Description", "Utilisateur",
                "idArticle", "idUnite", "idMagasin")

        self.tree = ttk.Treeview(tbl, columns=cols, show="headings",
                                 style="Mouv.Treeview", height=22)
        self.tree.tag_configure("even", background=C.BG_CARD)
        self.tree.tag_configure("odd",  background="#F0F4F8")

        stock_visible = "Stock Article" in {m[0] for m in self._session_data.get("menus", [])}

        widths = {"Date": 140, "Reference": 110, "Designation": 220,
          "Type": 130, "Entree": 90, "Sortie": 90,
          "Stock": 110 if stock_visible else 0,
          "Magasin": 110, "Description": 240, "Utilisateur": 100,
          "idArticle": 0, "idUnite": 0, "idMagasin": 0}

        for col in cols:
            self.tree.heading(col, text=col)
            w = widths.get(col, 100)
            self.tree.column(col, width=w, stretch=(w > 0),
                             anchor="center" if col in
                             ("Entree", "Sortie", "Stock", "Unite") else "w")
            if w == 0:
                self.tree.column(col, width=0, stretch=False, minwidth=0)

        sy = ctk.CTkScrollbar(tbl, orientation="vertical",
                              command=self.tree.yview)
        sx = ctk.CTkScrollbar(tbl, orientation="horizontal",
                              command=self.tree.xview)
        self.tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=(6, 0))
        sy.grid(row=0, column=1, sticky="ns", pady=(6, 0))
        sx.grid(row=1, column=0, sticky="ew", padx=(6, 0))

        # Footer
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=12, pady=(2, 8))
        self._lbl_entrees = ctk.CTkLabel(
            footer, text="Entrees : -",
            font=self._f(10, "bold"), text_color=C.SUCCESS_TEXT)
        self._lbl_entrees.pack(side="left", padx=(0, 16))
        self._lbl_sorties = ctk.CTkLabel(
            footer, text="Sorties : -",
            font=self._f(10, "bold"), text_color=C.DANGER_TEXT)
        self._lbl_sorties.pack(side="left", padx=(0, 16))
        self._lbl_total = ctk.CTkLabel(
            footer, text="0 mouvement(s)",
            font=self._f(10, "bold"), text_color=C.PRIMARY)
        self._lbl_total.pack(side="right")
        self._lbl_progress = ctk.CTkLabel(
            footer, text="",
            font=self._f(9), text_color=C.TEXT_MUTED)
        self._lbl_progress.pack(side="right", padx=(0, 12))

    # ── Chargement magasins ───────────────────────────────────────────────────
    def _load_magasins(self):
        conn = self._connect()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute("SELECT idmag, designationmag FROM tb_magasin "
                        "WHERE deleted=0 ORDER BY designationmag")
            rows = cur.fetchall()
            self.magasin_name_to_id = {r[1]: r[0] for r in rows}
            self._combo_mag["values"] = (
                ["Tous les magasins"] + [r[1] for r in rows])
            if self.id_user_connecte:
                cur.execute("SELECT idmag FROM tb_users "
                            "WHERE iduser=%s AND deleted=0",
                            (self.id_user_connecte,))
                row = cur.fetchone()
                if row and row[0]:
                    nm = next((r[1] for r in rows if r[0] == row[0]), None)
                    if nm:
                        self._combo_mag.set(nm)
        finally:
            conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    # CALCUL STOCK BATCH
    # ══════════════════════════════════════════════════════════════════════════
    def _calcul_stock_batch_sql(self, conn, batch):
        """
        Calcule en UNE requete SQL le stock a l'instant T pour un batch
        de lignes.

        batch : liste de dicts {idarticle, idunite, idmag, datetime_cible}
        Retourne : dict (idarticle, idunite, idmag, datetime_cible str) -> float

        Corrections vs version precedente :
        - Transferts  : qttransfertentree / qttransfertsortie
        - Ventes      : filtre magasin sur vd.idmag (detail), pas v.idmag
        - Inventaires : cumulatifs, via codearticle + niveau 0
        - Coefficients: exp(sum(ln(qtunite))) identique a page_stock.py
        - Magasins -1 : exclus
        """
        valid = [r for r in batch
                 if str(r["idmag"]) not in ("-1", "", "None", "none")]
        if not valid:
            return {}

        value_rows, params = [], []
        for r in valid:
            value_rows.append("(%s::int, %s::int, %s::int, %s::timestamp)")
            params.extend([int(r["idarticle"]), int(r["idunite"]),
                           int(r["idmag"]),     r["datetime_cible"]])

        values_sql = ",\n               ".join(value_rows)

        sql = f"""
        WITH

        unite_coeff AS (
            SELECT
                u.idarticle,
                u.idunite,
                u.niveau,
                u.codearticle,
                exp(
                    sum(
                        ln(NULLIF(
                            CASE WHEN COALESCE(u.qtunite,1) > 0
                                 THEN COALESCE(u.qtunite,1)
                                 ELSE 1
                            END, 0))
                    ) OVER (
                        PARTITION BY u.idarticle
                        ORDER BY u.niveau
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    )
                ) AS coeff_vers_base
            FROM tb_unite u
            WHERE u.deleted = 0
        ),

        demandes(idarticle, idunite_cible, idmag, datetime_cible) AS (
            VALUES {values_sql}
        ),

        mouvements AS (

            SELECT d.idarticle, d.idunite_cible, d.idmag, d.datetime_cible,
                    lf.qtlivrefrs * uc.coeff_vers_base AS qt
            FROM demandes d
            JOIN unite_coeff uc ON uc.idarticle = d.idarticle
            JOIN tb_livraisonfrs lf
              ON lf.idunite = uc.idunite
             AND lf.idmag   = d.idmag
             AND lf.deleted = 0
             AND date_trunc('second', lf.dateregistre)
              <= date_trunc('second', d.datetime_cible)

            UNION ALL

            SELECT d.idarticle, d.idunite_cible, d.idmag, d.datetime_cible,
                    ad.qtavoir * uc.coeff_vers_base
            FROM demandes d
            JOIN unite_coeff uc ON uc.idarticle = d.idarticle
            JOIN tb_avoirdetail ad
              ON ad.idunite = uc.idunite
             AND ad.idmag   = d.idmag
             AND ad.deleted = 0
            JOIN tb_avoir av
              ON av.id      = ad.idavoir
             AND av.deleted = 0
             AND date_trunc('second', av.dateavoir)
              <= date_trunc('second', d.datetime_cible)

            UNION ALL

            SELECT d.idarticle, d.idunite_cible, d.idmag, d.datetime_cible,
                    inv.qtinventaire * uc_base.coeff_vers_base
            FROM demandes d
            JOIN unite_coeff uc_base
              ON uc_base.idarticle = d.idarticle
             AND uc_base.niveau    = 0
            JOIN tb_inventaire inv
              ON inv.codearticle = uc_base.codearticle
             AND inv.idmag       = d.idmag
             AND date_trunc('second', inv.date)
              <= date_trunc('second', d.datetime_cible)

            UNION ALL

            SELECT d.idarticle, d.idunite_cible, d.idmag, d.datetime_cible,
                    td.qttransfertentree * uc.coeff_vers_base
            FROM demandes d
            JOIN unite_coeff uc ON uc.idarticle = d.idarticle
            JOIN tb_transfertdetail td
              ON td.idunite     = uc.idunite
             AND td.idmagentree = d.idmag
             AND td.deleted     = 0
            JOIN tb_transfert t
              ON t.idtransfert = td.idtransfert
             AND t.deleted     = 0
             AND date_trunc('second', t.dateregistre)
              <= date_trunc('second', d.datetime_cible)

            UNION ALL

            SELECT d.idarticle, d.idunite_cible, d.idmag, d.datetime_cible,
                    dce.quantite_entree * uc.coeff_vers_base
            FROM demandes d
            JOIN unite_coeff uc ON uc.idarticle = d.idarticle
            JOIN tb_detailchange_entree dce
              ON dce.idarticle = d.idarticle
             AND dce.idunite   = uc.idunite
             AND dce.idmagasin = d.idmag
            JOIN tb_changement chg
              ON chg.idchg = dce.idchg
             AND date_trunc('second', chg.datechg)
              <= date_trunc('second', d.datetime_cible)

            UNION ALL

            SELECT d.idarticle, d.idunite_cible, d.idmag, d.datetime_cible,
                    -vd.qtvente * uc.coeff_vers_base
            FROM demandes d
            JOIN unite_coeff uc ON uc.idarticle = d.idarticle
            JOIN tb_ventedetail vd
              ON vd.idarticle = d.idarticle
             AND vd.idunite   = uc.idunite
             AND vd.idmag     = d.idmag
             AND vd.deleted   = 0
            JOIN tb_vente v
              ON v.id      = vd.idvente
             AND v.deleted = 0
             AND v.statut  = 'VALIDEE'
             AND date_trunc('second', v.dateregistre)
              <= date_trunc('second', d.datetime_cible)

            UNION ALL

            SELECT d.idarticle, d.idunite_cible, d.idmag, d.datetime_cible,
                    -sd.qtsortie * uc.coeff_vers_base
            FROM demandes d
            JOIN unite_coeff uc ON uc.idarticle = d.idarticle
            JOIN tb_sortiedetail sd
              ON sd.idarticle = d.idarticle
             AND sd.idunite   = uc.idunite
             AND sd.idmag     = d.idmag
             AND sd.deleted   = 0
            JOIN tb_sortie s
              ON s.id      = sd.idsortie
             AND s.deleted = 0
             AND date_trunc('second', s.dateregistre)
              <= date_trunc('second', d.datetime_cible)

            UNION ALL

            SELECT d.idarticle, d.idunite_cible, d.idmag, d.datetime_cible,
                    -cid.qtconsomme * uc.coeff_vers_base
            FROM demandes d
            JOIN unite_coeff uc ON uc.idarticle = d.idarticle
            JOIN tb_consommationinterne_details cid
              ON cid.idarticle = d.idarticle
             AND cid.idunite   = uc.idunite
             AND cid.idmag     = d.idmag
            JOIN tb_consommationinterne ci
              ON ci.id = cid.idconsommation
             AND date_trunc('second', ci.dateregistre)
              <= date_trunc('second', d.datetime_cible)

            UNION ALL

            SELECT d.idarticle, d.idunite_cible, d.idmag, d.datetime_cible,
                    -td.qttransfertsortie * uc.coeff_vers_base
            FROM demandes d
            JOIN unite_coeff uc ON uc.idarticle = d.idarticle
            JOIN tb_transfertdetail td
              ON td.idunite    = uc.idunite
             AND td.idmagsortie = d.idmag
             AND td.deleted    = 0
            JOIN tb_transfert t
              ON t.idtransfert = td.idtransfert
             AND t.deleted     = 0
             AND date_trunc('second', t.dateregistre)
              <= date_trunc('second', d.datetime_cible)

            UNION ALL

            SELECT d.idarticle, d.idunite_cible, d.idmag, d.datetime_cible,
                    -dcs.quantite_sortie * uc.coeff_vers_base
            FROM demandes d
            JOIN unite_coeff uc ON uc.idarticle = d.idarticle
            JOIN tb_detailchange_sortie dcs
              ON dcs.idarticle = d.idarticle
             AND dcs.idunite   = uc.idunite
             AND dcs.idmagasin = d.idmag
            JOIN tb_changement chg
              ON chg.idchg = dcs.idchg
             AND date_trunc('second', chg.datechg)
              <= date_trunc('second', d.datetime_cible)
        ),

        stock_base AS (
            SELECT idarticle, idunite_cible, idmag, datetime_cible,
                   COALESCE(SUM(qt), 0.0) AS total_base
            FROM mouvements
            GROUP BY idarticle, idunite_cible, idmag, datetime_cible
        )

        SELECT
            sb.idarticle,
            sb.idunite_cible,
            sb.idmag,
            to_char(sb.datetime_cible, 'YYYY-MM-DD HH24:MI:SS') AS datetime_str,
            CASE
                WHEN COALESCE(uc.coeff_vers_base, 1) > 0
                THEN FLOOR(sb.total_base / uc.coeff_vers_base)
                ELSE 0
            END AS stock_dans_unite
        FROM stock_base sb
        JOIN unite_coeff uc
          ON uc.idarticle = sb.idarticle
         AND uc.idunite   = sb.idunite_cible
        """

        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.close()
        except Exception as e:
            print(f"[StockBatch] Erreur SQL: {e}")
            import traceback; traceback.print_exc()
            return {}

        result = {}
        for row in rows:
            # row[3] est retourné comme string grâce au to_char() dans le SELECT
            key = (int(row[0]), int(row[1]), int(row[2]), str(row[3]))
            result[key] = float(row[4])
        return result

    # ── Requete mouvements ────────────────────────────────────────────────────
    def build_mouvements_query(self, date_debut, date_fin, type_doc, idmag):
        queries, params = [], []

        if type_doc in ["Tous", "Entree"]:
            q = """
                SELECT lf.dateregistre, lf.reflivfrs, a.designation, 'Entree',
                    COALESCE(lf.qtlivrefrs,0), 0,
                    COALESCE(m.designationmag,'N/A'), COALESCE(usr.username,'N/A'),
                    u.idunite, u.codearticle, a.idarticle,
                    u.idunite, COALESCE(lf.idmag,-1),
                    COALESCE('[FRS: '||frs.nomfrs||
                             ' , ref. Commande: '||c.refcom||'] '
                             ||COALESCE(lf.reflivfrs,''), '')
                FROM tb_livraisonfrs lf
                INNER JOIN tb_unite u ON lf.idunite = u.idunite
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN tb_magasin m ON lf.idmag = m.idmag
                LEFT JOIN tb_users usr ON lf.iduser = usr.iduser
                LEFT JOIN tb_commande c ON lf.idcom = c.idcom
                LEFT JOIN tb_commandedetail cd
                    ON c.idcom = cd.idcom AND cd.idarticle = a.idarticle
                LEFT JOIN tb_fournisseur frs ON cd.idfrs = frs.idfrs
                WHERE DATE(lf.dateregistre) BETWEEN %s AND %s
                  AND lf.deleted = 0
            """
            p = [date_debut, date_fin]
            if self.selected_idarticle:
                q += " AND a.idarticle = %s"
                p.append(int(self.selected_idarticle))
            if idmag:
                q += " AND lf.idmag = %s"; p.append(idmag)
            queries.append(q); params.append(p)

        if type_doc in ["Tous", "Sortie"]:
            q = """
                SELECT s.dateregistre, s.refsortie, a.designation, 'Sortie',
                    0, COALESCE(sd.qtsortie,0),
                    COALESCE(m.designationmag,'N/A'), COALESCE(usr.username,'N/A'),
                    u.idunite, u.codearticle, a.idarticle,
                    u.idunite, COALESCE(sd.idmag,-1), COALESCE(sd.motif,'')
                FROM tb_sortie s
                INNER JOIN tb_sortiedetail sd ON s.id = sd.idsortie
                INNER JOIN tb_unite u ON sd.idunite = u.idunite
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN tb_magasin m ON sd.idmag = m.idmag
                LEFT JOIN tb_users usr ON s.iduser = usr.iduser
                WHERE DATE(s.dateregistre) BETWEEN %s AND %s
                  AND s.deleted = 0 AND sd.deleted = 0
            """
            p = [date_debut, date_fin]
            if self.selected_idarticle:
                q += " AND a.idarticle = %s"
                p.append(int(self.selected_idarticle))
            if idmag:
                q += " AND sd.idmag = %s"; p.append(idmag)
            queries.append(q); params.append(p)

        if type_doc in ["Tous", "Vente"]:
            q = """
                SELECT v.dateregistre, v.refvente, a.designation, 'Vente',
                    0, COALESCE(vd.qtvente,0),
                    COALESCE(m.designationmag,'N/A'), COALESCE(usr.username,'N/A'),
                    u.idunite, u.codearticle, a.idarticle,
                    u.idunite, COALESCE(vd.idmag,-1),
                    '[CL: '||COALESCE(cl.nomcli,'N/A')||'] vente '
                    ||COALESCE(mp.modedepaiement,'N/A')||' validee!'
                FROM tb_vente v
                INNER JOIN tb_ventedetail vd ON v.id = vd.idvente
                INNER JOIN tb_unite u ON vd.idunite = u.idunite
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN tb_magasin m ON vd.idmag = m.idmag
                LEFT JOIN tb_users usr ON v.iduser = usr.iduser
                LEFT JOIN tb_client cl ON v.idclient = cl.idclient
                LEFT JOIN tb_modepaiement mp ON v.idmode = mp.idmode
                WHERE DATE(v.dateregistre) BETWEEN %s AND %s
                  AND v.deleted = 0 AND vd.deleted = 0 AND v.statut = 'VALIDEE'
            """
            p = [date_debut, date_fin]
            if self.selected_idarticle:
                q += " AND a.idarticle = %s"
                p.append(int(self.selected_idarticle))
            if idmag:
                q += " AND vd.idmag = %s"; p.append(idmag)
            queries.append(q); params.append(p)

        if type_doc in ["Tous", "Transfert"]:
            q = """
                SELECT t.dateregistre, t.reftransfert, a.designation,
                    'Transfert (Sortie)', 0, COALESCE(td.qttransfert,0),
                    COALESCE(m.designationmag,'N/A'), COALESCE(usr.username,'N/A'),
                    u.idunite, u.codearticle, a.idarticle,
                    u.idunite, COALESCE(td.idmagsortie,-1),
                    COALESCE(td.description,'')
                FROM tb_transfert t
                INNER JOIN tb_transfertdetail td ON t.idtransfert = td.idtransfert
                INNER JOIN tb_unite u ON td.idunite = u.idunite
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN tb_magasin m ON td.idmagsortie = m.idmag
                LEFT JOIN tb_users usr ON t.iduser = usr.iduser
                WHERE DATE(t.dateregistre) BETWEEN %s AND %s
                  AND t.deleted = 0 AND td.deleted = 0
            """
            p = [date_debut, date_fin]
            if self.selected_idarticle:
                q += " AND a.idarticle = %s"
                p.append(int(self.selected_idarticle))
            if idmag:
                q += " AND td.idmagsortie = %s"; p.append(idmag)
            queries.append(q); params.append(p.copy())

            q = """
                SELECT t.dateregistre, t.reftransfert, a.designation,
                    'Transfert (Entree)', COALESCE(td.qttransfert,0), 0,
                    COALESCE(m.designationmag,'N/A'), COALESCE(usr.username,'N/A'),
                    u.idunite, u.codearticle, a.idarticle,
                    u.idunite, COALESCE(td.idmagentree,-1),
                    COALESCE(td.description,'')
                FROM tb_transfert t
                INNER JOIN tb_transfertdetail td ON t.idtransfert = td.idtransfert
                INNER JOIN tb_unite u ON td.idunite = u.idunite
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN tb_magasin m ON td.idmagentree = m.idmag
                LEFT JOIN tb_users usr ON t.iduser = usr.iduser
                WHERE DATE(t.dateregistre) BETWEEN %s AND %s
                  AND t.deleted = 0 AND td.deleted = 0
            """
            p = [date_debut, date_fin]
            if self.selected_idarticle:
                q += " AND a.idarticle = %s"
                p.append(int(self.selected_idarticle))
            if idmag:
                q += " AND td.idmagentree = %s"; p.append(idmag)
            queries.append(q); params.append(p)

        if type_doc in ["Tous", "Inventaire"]:
            q = """
                SELECT i.date, CONCAT('INV-', i.id), a.designation,
                    CONCAT('Inventaire', CASE WHEN i.observation IS NOT NULL
                        AND i.observation != ''
                        THEN CONCAT(' (', i.observation, ')') ELSE '' END),
                    i.qtinventaire, 0,
                    COALESCE(m.designationmag,'N/A'), COALESCE(usr.username,'N/A'),
                    u.idunite, u.codearticle, a.idarticle,
                    u.idunite, COALESCE(i.idmag,-1), COALESCE(i.observation,'')
                FROM tb_inventaire i
                INNER JOIN tb_unite u ON i.codearticle = u.codearticle
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN tb_magasin m ON i.idmag = m.idmag
                LEFT JOIN tb_users usr ON i.iduser = usr.iduser
                WHERE DATE(i.date) BETWEEN %s AND %s
            """
            p = [date_debut, date_fin]
            if self.selected_idarticle:
                q += " AND a.idarticle = %s"
                p.append(int(self.selected_idarticle))
            if idmag:
                q += " AND i.idmag = %s"; p.append(idmag)
            queries.append(q); params.append(p)

        if type_doc in ["Tous", "Avoir"]:
            q = """
                SELECT av.dateavoir, av.refavoir, a.designation, 'Avoir',
                    ad.qtavoir, 0,
                    COALESCE(m.designationmag,'N/A'), COALESCE(usr.username,'N/A'),
                    u.idunite, u.codearticle, a.idarticle,
                    u.idunite, COALESCE(ad.idmag,-1),
                    COALESCE(av.observation,'')
                FROM tb_avoir av
                INNER JOIN tb_avoirdetail ad ON av.id = ad.idavoir
                INNER JOIN tb_unite u ON ad.idunite = u.idunite
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN tb_magasin m ON ad.idmag = m.idmag
                LEFT JOIN tb_users usr ON av.iduser = usr.iduser
                WHERE DATE(av.dateavoir) BETWEEN %s AND %s AND av.deleted = 0
            """
            p = [date_debut, date_fin]
            if self.selected_idarticle:
                q += " AND a.idarticle = %s"
                p.append(int(self.selected_idarticle))
            if idmag:
                q += " AND ad.idmag = %s"; p.append(idmag)
            queries.append(q); params.append(p)

        if type_doc in ["Tous", "Consommation interne"]:
            q = """
                SELECT ci.dateregistre, ci.refconsommation, a.designation,
                    'Consommation interne', 0, cid.qtconsomme,
                    COALESCE(m.designationmag,'N/A'), COALESCE(usr.username,'N/A'),
                    u.idunite, u.codearticle, a.idarticle,
                    u.idunite, COALESCE(cid.idmag,-1),
                    COALESCE(cid.observation,'')
                FROM tb_consommationinterne ci
                INNER JOIN tb_consommationinterne_details cid
                    ON ci.id = cid.idconsommation
                INNER JOIN tb_unite u ON cid.idunite = u.idunite
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN tb_magasin m ON cid.idmag = m.idmag
                LEFT JOIN tb_users usr ON ci.iduser = usr.iduser
                WHERE DATE(ci.dateregistre) BETWEEN %s AND %s
            """
            p = [date_debut, date_fin]
            if self.selected_idarticle:
                q += " AND a.idarticle = %s"
                p.append(int(self.selected_idarticle))
            if idmag:
                q += " AND cid.idmag = %s"; p.append(idmag)
            queries.append(q); params.append(p)

        if type_doc in ["Tous", "Changement"]:
            q = """
                SELECT chg.datechg, chg.refchg, a.designation,
                    'Changement (Sortie)', 0, dcs.quantite_sortie,
                    COALESCE(m.designationmag,'N/A'), COALESCE(usr.username,'N/A'),
                    u.idunite, u.codearticle, a.idarticle,
                    u.idunite, COALESCE(dcs.idmagasin,-1),
                    COALESCE(chg.note,'')
                FROM tb_changement chg
                INNER JOIN tb_detailchange_sortie dcs ON chg.idchg = dcs.idchg
                INNER JOIN tb_unite u ON dcs.idunite = u.idunite
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN tb_magasin m ON dcs.idmagasin = m.idmag
                LEFT JOIN tb_users usr ON chg.iduser = usr.iduser
                WHERE DATE(chg.datechg) BETWEEN %s AND %s
            """
            p = [date_debut, date_fin]
            if self.selected_idarticle:
                q += " AND a.idarticle = %s"
                p.append(int(self.selected_idarticle))
            if idmag:
                q += " AND dcs.idmagasin = %s"; p.append(idmag)
            queries.append(q); params.append(p.copy())

            q = """
                SELECT chg.datechg, chg.refchg, a.designation,
                    'Changement (Entree)', dce.quantite_entree, 0,
                    COALESCE(m.designationmag,'N/A'), COALESCE(usr.username,'N/A'),
                    u.idunite, u.codearticle, a.idarticle,
                    u.idunite, COALESCE(dce.idmagasin,-1),
                    COALESCE(chg.note,'')
                FROM tb_changement chg
                INNER JOIN tb_detailchange_entree dce ON chg.idchg = dce.idchg
                INNER JOIN tb_unite u ON dce.idunite = u.idunite
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN tb_magasin m ON dce.idmagasin = m.idmag
                LEFT JOIN tb_users usr ON chg.iduser = usr.iduser
                WHERE DATE(chg.datechg) BETWEEN %s AND %s
            """
            p = [date_debut, date_fin]
            if self.selected_idarticle:
                q += " AND a.idarticle = %s"
                p.append(int(self.selected_idarticle))
            if idmag:
                q += " AND dce.idmagasin = %s"; p.append(idmag)
            queries.append(q); params.append(p)

        return queries, params

    # ── Chargement principal ──────────────────────────────────────────────────
    def load_mouvements(self):
        # Annuler insertion en cours
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None

        # Fermer connexion batch precedente
        self._close_db_conn()

        self.tree.delete(*self.tree.get_children())
        self._lbl_total.configure(text="Chargement...")
        self._lbl_progress.configure(text="")
        self._lbl_statut.configure(text="")
        self._full_rows    = []
        self._pending_rows = []

        conn = self._connect()
        if not conn:
            self._lbl_total.configure(text="Erreur de connexion")
            return

        try:
            date_debut = self._date_debut.get_date()
            date_fin   = self._date_fin.get_date()
            type_doc   = self._combo_type.get()
            mag_sel    = self._combo_mag.get()
            idmag      = self.magasin_name_to_id.get(mag_sel) \
                         if mag_sel != "Tous les magasins" else None

            cur = conn.cursor()
            cur.execute("SELECT idunite, designationunite FROM tb_unite "
                        "WHERE deleted=0")
            unite_map = {r[0]: r[1] for r in cur.fetchall()}

            mouvements = []
            queries, params_list = self.build_mouvements_query(
                date_debut, date_fin, type_doc, idmag)

            for query, p in zip(queries, params_list):
                try:
                    cur.execute(query, p)
                    mouvements.extend(cur.fetchall())
                except Exception as e:
                    print(f"ERREUR requete mouvement: {e}")
                    import traceback; traceback.print_exc()

            cur.close()

        except Exception as e:
            messagebox.showerror("Erreur DB", str(e))
            conn.close()
            return

        if not mouvements:
            conn.close()
            self._lbl_total.configure(text="Aucun mouvement trouve")
            self._lbl_statut.configure(
                text=f"Actualise : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            return

        # Tris stables
        try:
            mouvements.sort(key=lambda x: x[9] or "")
        except Exception:
            pass
        try:
            mouvements.sort(key=lambda x: (x[2].lower() if x[2] else ""))
        except Exception:
            pass
        try:
            mouvements.sort(
                key=lambda x: x[0] if x[0] else datetime.min, reverse=True)
        except Exception:
            pass

        te = ts = 0.0
        for mouv in mouvements:
            date_format      = (mouv[0].strftime('%d/%m/%Y %H:%M:%S')
                                if mouv[0] else "")
            reference        = mouv[1] or ""
            article_design   = mouv[2] or ""
            type_doc_display = mouv[3] or ""
            entree           = float(mouv[4]) if mouv[4] else 0.0
            sortie           = float(mouv[5]) if mouv[5] else 0.0
            magasin          = mouv[6] or ""
            username         = mouv[7] or ""
            idunite          = mouv[8]
            idarticle        = mouv[10]
            idmag_r          = mouv[12]
            description      = mouv[13] or "-"
            datetime_cible   = (mouv[0].strftime('%Y-%m-%d %H:%M:%S')
                                if mouv[0] else "")

            unite_display = unite_map.get(idunite, "")
            is_inventaire = "inventaire" in type_doc_display.lower()
            if is_inventaire:
                e_fmt = "-"
                s_fmt = "-"
            else:
                e_fmt = '-' if entree == 0 else self.formater_nombre(entree)
                s_fmt = '-' if sortie == 0 else self.formater_nombre(sortie)
                if entree:
                    te += entree
                if sortie:
                    ts += sortie

            self._full_rows.append({
                "idarticle":      idarticle,
                "idunite":        idunite,
                "idmag":          idmag_r,
                "datetime_cible": datetime_cible,
                "display": [
                    date_format, reference, article_design, type_doc_display,
                    unite_display, e_fmt, s_fmt, "-",
                    magasin, description, username,
                    str(idarticle), str(idunite), str(idmag_r),
                ],
            })

        self._lbl_entrees.configure(
            text=f"Entrees : {self.formater_nombre(te)}")
        self._lbl_sorties.configure(
            text=f"Sorties : {self.formater_nombre(ts)}")
        self._lbl_total.configure(
            text=f"{len(self._full_rows)} mouvement(s)")
        self._lbl_statut.configure(
            text=f"Actualise : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

        # Stocker la connexion pour l'utiliser dans _insert_batch
        self._db_conn      = conn
        self._pending_rows = list(self._full_rows)
        self._insert_batch()

    # ── Insertion par blocs avec stock calcule AVANT insertion ────────────────
    def _insert_batch(self):
        """
        Prend _BATCH_SIZE lignes, calcule leurs stocks en SQL,
        insere dans le treeview avec les vrais stocks,
        reschedule via after(5) pour ne pas bloquer l'UI.
        Le stock calcule est sauvegarde dans row["display"][7] de _full_rows
        pour que le filtre client le reutilise sans re-requete.
        """
        if not self._pending_rows:
            self._lbl_progress.configure(text="")
            self._close_db_conn()
            return

        batch = self._pending_rows[:_BATCH_SIZE]
        self._pending_rows = self._pending_rows[_BATCH_SIZE:]

        # Calcul des stocks pour ce batch
        stock_map = {}
        if self._db_conn:
            try:
                stock_map = self._calcul_stock_batch_sql(self._db_conn, batch)
            except Exception as e:
                print(f"[InsertBatch] Erreur calcul stock: {e}")

        offset = len(self.tree.get_children())
        for i, row in enumerate(batch):
            idmg = row["idmag"]
            key  = None
            if str(idmg) not in ("-1", "", "None", "none"):
                key = (int(row["idarticle"]), int(row["idunite"]),
                       int(idmg),             str(row["datetime_cible"]))

            stock_str = (self.formater_nombre(stock_map[key])
                         if key and key in stock_map else "-")

            # Mettre a jour display[7] directement dans la liste row
            # (row["display"] est une liste mutable, et row est un dict dans _full_rows)
            row["display"][7] = stock_str

            display = row["display"]
            parity = "even" if (offset + i) % 2 == 0 else "odd"
            self.tree.insert("", "end", values=display, tags=(parity,))

        n_done = len(self.tree.get_children())
        n_tot  = len(self._full_rows)
        if self._pending_rows:
            self._lbl_progress.configure(text=f"{n_done}/{n_tot}")
            self._after_id = self.after(5, self._insert_batch)
        else:
            self._lbl_progress.configure(text="")

    # ── Filtre client-side ────────────────────────────────────────────────────
    def _filter_client(self):
        """
        Filtre instantane sur _full_rows deja en memoire.
        Les stocks sont deja calcules et stockes dans row["display"][7],
        donc on insere directement sans re-requete DB.
        """
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None

        # Ne pas fermer _db_conn si un chargement est en cours
        search = self._var_recherche.get().strip().lower()
        self.tree.delete(*self.tree.get_children())

        if not search:
            filtered = list(self._full_rows)
        else:
            filtered = [
                r for r in self._full_rows
                if any(search in str(cell).lower() for cell in r["display"])
            ]

        self._lbl_total.configure(text=f"{len(filtered)} mouvement(s)")

        # Insertion directe par blocs sans recalcul stock
        self._pending_rows = filtered
        self._insert_batch_display_only()

    def _insert_batch_display_only(self):
        """
        Insere les lignes en treeview sans recalcul stock (stocks deja dans display[7]).
        """
        if not self._pending_rows:
            self._lbl_progress.configure(text="")
            return

        batch = self._pending_rows[:_BATCH_SIZE]
        self._pending_rows = self._pending_rows[_BATCH_SIZE:]

        offset = len(self.tree.get_children())
        for i, row in enumerate(batch):
            parity = "even" if (offset + i) % 2 == 0 else "odd"
            self.tree.insert("", "end", values=row["display"], tags=(parity,))

        if self._pending_rows:
            self._lbl_progress.configure(
                text=f"{len(self.tree.get_children())}/{len(self._full_rows)}")
            self._after_id = self.after(5, self._insert_batch_display_only)
        else:
            self._lbl_progress.configure(text="")

    def filter_tree_by_text(self, event=None):
        self._filter_client()

    def _search_db(self):
        q = self._var_recherche.get().strip()
        if not q:
            self._reset_article()
            return
        conn = self._connect()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT idarticle, designation FROM tb_article
                WHERE deleted=0
                  AND (LOWER(designation) LIKE %s
                       OR CAST(idarticle AS TEXT) LIKE %s)
                ORDER BY designation LIMIT 1
            """, (f"%{q.lower()}%", f"%{q.lower()}%"))
            r = cur.fetchone()
            if r:
                self.selected_idarticle    = r[0]
                self.selected_article_name = r[1]
                self._var_recherche.set(r[1])
                self.load_mouvements()
        finally:
            conn.close()

    def filtrer_article_dynamique(self):
        self._search_db()

    def _ouvrir_recherche(self):
        FenetreRechercheArticle(self, self._on_article_selected)

    def ouvrir_recherche_article(self):
        self._ouvrir_recherche()

    def _on_article_selected(self, article):
        self.selected_idarticle    = article['idarticle']
        self.selected_article_name = article['designation']
        self._var_recherche.set(article['designation'])
        self.load_mouvements()

    def on_article_selected(self, article):
        self._on_article_selected(article)

    def _reset_article(self):
        self.selected_idarticle    = None
        self.selected_article_name = None

    def reset_article_selection(self):
        self._reset_article()
        self._var_recherche.set("")
        self.load_mouvements()

    def _reset(self):
        self._reset_article()
        self._var_recherche.set("")
        self._combo_type.set("Tous")
        self._combo_mag.set("Tous les magasins")
        self.load_mouvements()


# ── Test standalone ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    root.title("Mouvements d'Articles")
    root.geometry("1440x820")
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    PageArticleMouvement(root).grid(row=0, column=0, sticky="nsew")
    root.mainloop()
