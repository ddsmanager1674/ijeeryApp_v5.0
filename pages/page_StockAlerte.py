# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              iJeery — page_stock_alerte.py  (refonte thème v2)             ║
╚══════════════════════════════════════════════════════════════════════════════╝
Filtres intuitifs restructurés :
  - Dimension 1 : portée  →  Alerte Générale (défaut)  |  Alerte Magasin
  - Dimension 2 : état    →  Tous | Normal | En alerte | En rupture
  - Filtre magasin (liste dynamique)
  - Recherche texte libre
"""

import customtkinter as ctk
from tkinter import ttk, messagebox, StringVar
import psycopg2
import json
import os
from datetime import datetime
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from log_utils import AppLogger

# ── Thème centralisé ──────────────────────────────────────────────────────────
try:
    from app_theme import Colors, Fonts, styled, Theme, ThemeUtils
    _THEME_OK = True
except ImportError:
    _THEME_OK = False


class _C:
    """Fallback couleurs si app_theme absent."""
    MIDNIGHT       = "#2C3E50"
    BG_PAGE        = "#ECF0F1"
    BG_CARD        = "#FFFFFF"
    BG_HEADER      = "#2C3E50"
    PRIMARY        = "#3498DB"
    PRIMARY_HOVER  = "#2980B9"
    PRIMARY_LIGHT  = "#D6EAF8"
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


C = Colors if _THEME_OK else _C


# ─────────────────────────────────────────────────────────────────────────────
# Requête SQL
# ─────────────────────────────────────────────────────────────────────────────
SQL_STOCK_ALERTE = """
WITH RECURSIVE

    facteur_conversion AS (
        SELECT u.idunite, u.idarticle, u.niveau, u.designationunite,
               1.0::double precision AS facteur_vers_base
        FROM tb_unite u
        WHERE u.niveau = 0 AND u.deleted = 0

        UNION ALL

        SELECT u.idunite, u.idarticle, u.niveau, u.designationunite,
               fc.facteur_vers_base * u.qtunite AS facteur_vers_base
        FROM tb_unite u
        JOIN facteur_conversion fc
          ON fc.idarticle = u.idarticle AND fc.niveau = u.niveau - 1
        WHERE u.deleted = 0
    ),

    unite_max AS (
        SELECT DISTINCT ON (u.idarticle)
            u.idarticle, u.idunite, u.codearticle,
            u.designationunite, fc.facteur_vers_base
        FROM tb_unite u
        JOIN facteur_conversion fc ON fc.idunite = u.idunite
        WHERE u.deleted = 0
        ORDER BY u.idarticle, u.niveau DESC
    ),

    tous_mouvements AS (
        SELECT lf.idunite, lf.idmag, lf.qtlivrefrs  AS quantite, 1 AS signe
        FROM tb_livraisonfrs lf WHERE lf.deleted = 0
        UNION ALL
        SELECT u.idunite, inv.idmag, inv.qtinventaire, 1
        FROM tb_inventaire inv
        JOIN tb_unite u ON u.codearticle = inv.codearticle AND u.niveau=0 AND u.deleted=0
        UNION ALL
        SELECT ad.idunite, ad.idmag, ad.qtavoir, 1
        FROM tb_avoirdetail ad JOIN tb_avoir av ON av.id=ad.idavoir
        WHERE ad.deleted=0 AND av.deleted=0
        UNION ALL
        SELECT dce.idunite, dce.idmagasin, dce.quantite_entree::double precision, 1
        FROM tb_detailchange_entree dce JOIN tb_changement chg ON chg.idchg=dce.idchg
        UNION ALL
        SELECT td.idunite, td.idmagentree, td.qttransfertentree, 1
        FROM tb_transfertdetail td JOIN tb_transfert t ON t.idtransfert=td.idtransfert
        WHERE td.deleted=0 AND t.deleted=0
        UNION ALL
        SELECT vd.idunite, vd.idmag, vd.qtvente, -1
        FROM tb_ventedetail vd JOIN tb_vente v ON v.id=vd.idvente
        WHERE vd.deleted=0 AND v.deleted=0 AND v.statut='VALIDEE'
        UNION ALL
        SELECT sd.idunite, sd.idmag, sd.qtsortie, -1
        FROM tb_sortiedetail sd JOIN tb_sortie s ON s.id=sd.idsortie
        WHERE sd.deleted=0 AND s.deleted=0
        UNION ALL
        SELECT cid.idunite, cid.idmag, cid.qtconsomme::double precision, -1
        FROM tb_consommationinterne_details cid
        JOIN tb_consommationinterne ci ON ci.id=cid.idconsommation
        UNION ALL
        SELECT dcs.idunite, dcs.idmagasin, dcs.quantite_sortie::double precision, -1
        FROM tb_detailchange_sortie dcs JOIN tb_changement chg ON chg.idchg=dcs.idchg
        UNION ALL
        SELECT td.idunite, td.idmagsortie, td.qttransfertsortie, -1
        FROM tb_transfertdetail td JOIN tb_transfert t ON t.idtransfert=td.idtransfert
        WHERE td.deleted=0 AND t.deleted=0
    ),

    stock_base AS (
        SELECT fc.idarticle, tm.idmag,
               SUM(tm.quantite * fc.facteur_vers_base * tm.signe) AS stock_base_mag
        FROM tous_mouvements tm
        JOIN facteur_conversion fc ON fc.idunite=tm.idunite
        GROUP BY fc.idarticle, tm.idmag
    ),

    stock_general AS (
        SELECT idarticle, SUM(stock_base_mag) AS stock_base_gen
        FROM stock_base GROUP BY idarticle
    )

SELECT
    um.codearticle,
    a.designation                                                                    AS designationarticle,
    um.designationunite                                                              AS unite,
    m.designationmag,
    a.alertdepot                                                                     AS alert_mag,
    ROUND((COALESCE(sbm.stock_base_mag,0.0)/um.facteur_vers_base)::numeric,4)       AS stock_mag,
    a.alert                                                                          AS alert_gen,
    ROUND((COALESCE(sg.stock_base_gen, 0.0)/um.facteur_vers_base)::numeric,4)       AS stock_gen,
    a.idarticle, um.idunite, a.idmag
FROM tb_article a
JOIN unite_max   um ON um.idarticle = a.idarticle
JOIN tb_magasin  m  ON m.idmag      = a.idmag AND m.deleted=0
LEFT JOIN stock_base    sbm ON sbm.idarticle=a.idarticle AND sbm.idmag=a.idmag
LEFT JOIN stock_general sg  ON sg.idarticle =a.idarticle
WHERE a.deleted=0
ORDER BY a.designation;
"""


# ─────────────────────────────────────────────────────────────────────────────
# Style Treeview
# ─────────────────────────────────────────────────────────────────────────────
def _apply_treeview_style():
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(
        "Alerte.Treeview",
        background=C.BG_CARD, foreground=C.TEXT_PRIMARY,
        fieldbackground=C.BG_CARD, rowheight=24,
        font=("Roboto", 10) if _THEME_OK else ("Segoe UI", 10),
        borderwidth=0,
    )
    style.configure(
        "Alerte.Treeview.Heading",
        background=C.BG_HEADER, foreground="#FFFFFF",
        font=("Roboto", 10, "bold") if _THEME_OK else ("Segoe UI", 10, "bold"),
        relief="flat", padding=(6, 4),
    )
    style.map("Alerte.Treeview",
              background=[("selected", C.PRIMARY)],
              foreground=[("selected", "#FFFFFF")])
    style.map("Alerte.Treeview.Heading",
              background=[("active", C.MIDNIGHT)])


# ─────────────────────────────────────────────────────────────────────────────
# Composants UI internes
# ─────────────────────────────────────────────────────────────────────────────
class _PillButton(ctk.CTkButton):
    """Bouton pill à deux états actif/inactif."""

    def __init__(self, master, text, on_click, active=False, **kw):
        self._active = active
        self._cb     = on_click
        kw.setdefault("height", 28)
        super().__init__(master, text=text, corner_radius=20,
                         command=self._fired, **kw)
        self._render()

    def _render(self):
        if self._active:
            self.configure(fg_color=C.PRIMARY, hover_color=C.PRIMARY_HOVER,
                           text_color="#FFFFFF", border_width=0)
        else:
            self.configure(fg_color="transparent", hover_color=C.DIVIDER,
                           text_color=C.TEXT_SECONDARY,
                           border_width=1, border_color=C.BORDER)

    def _fired(self):
        self._cb(self)

    def set_active(self, state: bool):
        self._active = state
        self._render()


# ─────────────────────────────────────────────────────────────────────────────
# Page principale
# ─────────────────────────────────────────────────────────────────────────────
class PageStockAlerte(ctk.CTkFrame):
    """
    Page Stock Alerte — thème iJeery.

    Filtres en deux dimensions :
      • Portée  : Alerte Générale (défaut) | Alerte Magasin
      • État    : Tous | Normal | En alerte | En rupture
    + Filtre magasin + recherche texte.
    """

    PORTEE_GEN = "generale"
    PORTEE_MAG = "magasin"

    ETAT_TOUS    = "tous"
    ETAT_NORMAL  = "normal"
    ETAT_ALERTE  = "alerte"
    ETAT_RUPTURE = "rupture"

    def __init__(self, master, db_conn=None, session_data=None, iduser=None):
        super().__init__(master, fg_color=C.BG_PAGE)
        self.item_ids: dict = {}
        self.all_rows: list = []
        self._portee = self.PORTEE_GEN   # ← défaut : Alerte Générale
        self._etat   = self.ETAT_TOUS

        _apply_treeview_style()
        self._build_ui()
        self.charger_donnees()
        resolved_user = None
        if isinstance(session_data, dict):
            resolved_user = session_data.get("user_id") or session_data.get("iduser")
        self._logger = AppLogger(conn=db_conn, session_data=session_data or ({"user_id": resolved_user} if resolved_user else {}))

    # ── Base de données ───────────────────────────────────────────────────────
    def connect_db(self):
        try:
            root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            with open(os.path.join(root, "config.json")) as f:
                cfg = json.load(f)
            return psycopg2.connect(**cfg.get("database", {}))
        except Exception as e:
            messagebox.showerror("Connexion", f"Impossible de se connecter :\n{e}")
            return None

    def charger_donnees(self):
        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute(SQL_STOCK_ALERTE)
            self.all_rows = cur.fetchall()
            self._refresh_magasin_filter()
            self._apply_filters()
            self._lbl_statut.configure(
                text=f"Actualisé : {datetime.now().strftime('%d/%m/%Y  %H:%M:%S')}")
        except Exception as e:
            messagebox.showerror("Erreur SQL", str(e))
        finally:
            conn.close()

    # ── Construction de l'interface ───────────────────────────────────────────
    def _f(self, size=12, weight="normal"):
        """Raccourci font Roboto / Segoe fallback."""
        fam = "Roboto" if _THEME_OK else "Segoe UI"
        return ctk.CTkFont(family=fam, size=size, weight=weight)

    def _build_ui(self):
        # ══════════════════════════════════════════════════════════════════════
        # LIGNE 1 : En-tête  (titre gauche · statut droite)
        # ══════════════════════════════════════════════════════════════════════
        hdr = ctk.CTkFrame(self, fg_color=C.BG_HEADER, corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text="⚠  Stock Alerte",
                     font=self._f(18, "bold"), text_color="#FFFFFF"
                     ).pack(side="left", padx=16, pady=8)
        self._lbl_statut = ctk.CTkLabel(hdr, text="", font=self._f(9),
                                        text_color="#AAAAAA")
        self._lbl_statut.pack(side="right", padx=16)

        # ══════════════════════════════════════════════════════════════════════
        # LIGNE 2 : Badges stats inline  +  Bouton Actualiser
        # ══════════════════════════════════════════════════════════════════════
        row_stats = ctk.CTkFrame(self, fg_color="transparent")
        row_stats.pack(fill="x", padx=12, pady=(8, 0))

        # Badges compacts (hauteur = 34px, même que le bouton)
        badge_defs = [
            ("_sc_total",   "📋", "Affichés",   C.BG_CARD,      C.TEXT_PRIMARY),
            ("_sc_normal",  "✅", "Normal",     C.SUCCESS_LIGHT, C.SUCCESS_TEXT),
            ("_sc_alerte",  "⚠️", "En alerte",  C.WARNING_LIGHT, C.WARNING_TEXT),
            ("_sc_rupture", "🔴", "En rupture", C.DANGER_LIGHT,  C.DANGER_TEXT),
        ]
        for attr, icon, label, bg, fg in badge_defs:
            frm = ctk.CTkFrame(row_stats, fg_color=bg, corner_radius=6,
                               height=34)
            frm.pack(side="left", padx=(0, 6), ipady=0)
            frm.pack_propagate(False)
            inner = ctk.CTkFrame(frm, fg_color="transparent")
            inner.place(relx=0.5, rely=0.5, anchor="center")
            lbl_n = ctk.CTkLabel(inner, text="—",
                                 font=self._f(13, "bold"), text_color=fg)
            lbl_n.pack(side="left", padx=(6, 2))
            ctk.CTkLabel(inner, text=label,
                         font=self._f(10), text_color=fg).pack(side="left",
                                                                padx=(0, 6))
            setattr(self, attr, lbl_n)   # on stocke directement le label

        ctk.CTkButton(
            row_stats, text="↺  Actualiser",
            command=self.charger_donnees,
            fg_color=C.INFO, hover_color=C.INFO_DARK if _THEME_OK else "#16A085",
            text_color="#FFFFFF",
            corner_radius=6, height=34, width=120,
            font=self._f(11, "bold"),
        ).pack(side="right", padx=(0, 0))

        # ══════════════════════════════════════════════════════════════════════
        # LIGNE 3 : Filtres — tout sur UNE seule ligne compacte
        # ══════════════════════════════════════════════════════════════════════
        filter_row = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=8)
        filter_row.pack(fill="x", padx=12, pady=6)

        inner_f = ctk.CTkFrame(filter_row, fg_color="transparent")
        inner_f.pack(fill="x", padx=10, pady=6)

        # — Label PORTÉE —
        ctk.CTkLabel(inner_f, text="Portée :", font=self._f(9, "bold"),
                     text_color=C.TEXT_MUTED).pack(side="left", padx=(0, 4))

        self._pill_gen = _PillButton(
            inner_f, "🌐 Gén.",
            on_click=lambda _: self._set_portee(self.PORTEE_GEN),
            active=True, width=80, height=26, font=self._f(10),
        )
        self._pill_gen.pack(side="left", padx=(0, 3))

        self._pill_mag = _PillButton(
            inner_f, "🏪 Mag.",
            on_click=lambda _: self._set_portee(self.PORTEE_MAG),
            active=False, width=80, height=26, font=self._f(10),
        )
        self._pill_mag.pack(side="left", padx=(0, 10))

        # Séparateur
        ctk.CTkFrame(inner_f, width=1, height=20,
                     fg_color=C.BORDER).pack(side="left", padx=(0, 10))

        # — Label ÉTAT —
        ctk.CTkLabel(inner_f, text="État :", font=self._f(9, "bold"),
                     text_color=C.TEXT_MUTED).pack(side="left", padx=(0, 4))

        self._etat_pills: dict[str, _PillButton] = {}
        etat_cfg = [
            (self.ETAT_TOUS,    "Tous"),
            (self.ETAT_NORMAL,  "✅ Normal"),
            (self.ETAT_ALERTE,  "⚠️ Alerte"),
            (self.ETAT_RUPTURE, "🔴 Rupture"),
        ]
        for key, label in etat_cfg:
            p = _PillButton(
                inner_f, label,
                on_click=lambda _, k=key: self._set_etat(k),
                active=(key == self.ETAT_TOUS),
                width=90, height=26, font=self._f(10),
            )
            p.pack(side="left", padx=(0, 3))
            self._etat_pills[key] = p

        # Séparateur
        ctk.CTkFrame(inner_f, width=1, height=20,
                     fg_color=C.BORDER).pack(side="left", padx=(0, 10))

        # — Recherche —
        ctk.CTkLabel(inner_f, text="🔍", font=ctk.CTkFont(size=12)
                     ).pack(side="left", padx=(0, 3))
        self._var_recherche = StringVar()
        self._var_recherche.trace("w", lambda *_: self._apply_filters())
        ctk.CTkEntry(
            inner_f, textvariable=self._var_recherche,
            placeholder_text="Code / désignation…",
            width=220, height=26,
            fg_color=C.BG_PAGE, border_color=C.BORDER,
            text_color=C.TEXT_PRIMARY, font=self._f(10),
        ).pack(side="left", padx=(0, 10))

        # — Magasin —
        ctk.CTkLabel(inner_f, text="Mag. :", font=self._f(9),
                     text_color=C.TEXT_SECONDARY).pack(side="left", padx=(0, 4))
        self._var_magasin = StringVar(value="Tous")
        self._combo_mag = ttk.Combobox(
            inner_f, textvariable=self._var_magasin,
            values=["Tous"], state="readonly", width=18,
            font=("Roboto", 9) if _THEME_OK else ("Segoe UI", 9),
        )
        self._combo_mag.pack(side="left", ipady=2)
        self._combo_mag.bind("<<ComboboxSelected>>",
                             lambda _: self._apply_filters())

        # ══════════════════════════════════════════════════════════════════════
        # TABLEAU
        # ══════════════════════════════════════════════════════════════════════
        tbl = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=8)
        tbl.pack(fill="both", expand=True, padx=12, pady=(0, 6))

        cols = ("Code", "Désignation", "Unité", "Magasin",
                "Seuil Mag.", "Stock Mag.",
                "Seuil Gén.", "Stock Gén.")

        self.tree = ttk.Treeview(tbl, columns=cols, show="headings",
                                 style="Alerte.Treeview", height=20)

        self.tree.tag_configure('rupture',
                                foreground=C.DANGER_TEXT,
                                background=C.DANGER_LIGHT)
        self.tree.tag_configure('alerte',
                                foreground=C.WARNING_TEXT,
                                background=C.WARNING_LIGHT)
        self.tree.tag_configure('normal',
                                foreground=C.INFO_TEXT,
                                background=C.INFO_LIGHT)

        widths = {"Code": 100, "Désignation": 260, "Unité": 100,
                  "Magasin": 140, "Seuil Mag.": 85, "Stock Mag.": 85,
                  "Seuil Gén.": 85, "Stock Gén.": 85}
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=widths.get(col, 90), anchor="center")

        sy = ctk.CTkScrollbar(tbl, orientation="vertical",
                              command=self.tree.yview)
        sx = ctk.CTkScrollbar(tbl, orientation="horizontal",
                              command=self.tree.xview)
        self.tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.tree.bind("<Double-1>", self._on_double_click)

        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=(6, 0))
        sy.grid(row=0, column=1, sticky="ns", pady=(6, 0))
        sx.grid(row=1, column=0, sticky="ew", padx=(6, 0))
        tbl.grid_rowconfigure(0, weight=1)
        tbl.grid_columnconfigure(0, weight=1)

        # ══════════════════════════════════════════════════════════════════════
        # FOOTER : Légende chips  +  compteur article (inline à droite)
        # ══════════════════════════════════════════════════════════════════════
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=12, pady=(2, 8))

        for bg, fg, label in [
            (C.SUCCESS_LIGHT, C.SUCCESS_TEXT, "● Normal (stock > seuil)"),
            (C.WARNING_LIGHT, C.WARNING_TEXT, "● En alerte (0 < stock ≤ seuil)"),
            (C.DANGER_LIGHT,  C.DANGER_TEXT,  "● En rupture (stock = 0)"),
        ]:
            chip = ctk.CTkFrame(footer, fg_color=bg, corner_radius=5)
            chip.pack(side="left", padx=(0, 8), ipadx=6, ipady=2)
            ctk.CTkLabel(chip, text=label, font=self._f(9),
                         text_color=fg).pack()

        # Hint portée
        self._lbl_portee_hint = ctk.CTkLabel(
            footer, text=self._hint_text(),
            font=self._f(9), text_color=C.TEXT_MUTED, anchor="e")
        self._lbl_portee_hint.pack(side="right", padx=(0, 8))

        # Compteur
        self._lbl_total = ctk.CTkLabel(
            footer, text="0 article(s)",
            font=self._f(10, "bold"), text_color=C.PRIMARY, anchor="e")
        self._lbl_total.pack(side="right", padx=(0, 12))

    # ── Logique filtres ───────────────────────────────────────────────────────
    def _hint_text(self):
        if self._portee == self.PORTEE_GEN:
            return ("🌐  Portée : Alerte Générale  "
                    "— état calculé sur Stock Gén. vs Seuil Gén.")
        return ("🏪  Portée : Alerte Magasin  "
                "— état calculé sur Stock Mag. vs Seuil Mag.")

    def _set_portee(self, portee: str):
        self._portee = portee
        self._pill_gen.set_active(portee == self.PORTEE_GEN)
        self._pill_mag.set_active(portee == self.PORTEE_MAG)
        self._lbl_portee_hint.configure(text=self._hint_text())
        self._apply_filters()

    def _set_etat(self, etat: str):
        self._etat = etat
        for k, p in self._etat_pills.items():
            p.set_active(k == etat)
        self._apply_filters()

    def _row_etat(self, row) -> str:
        try:
            v_sm = float(row[5] or 0)
            v_sg = float(row[7] or 0)
            v_am = float(row[4] or 0)
            v_ag = float(row[6] or 0)
        except (TypeError, ValueError):
            return self.ETAT_NORMAL

        stock = v_sg if self._portee == self.PORTEE_GEN else v_sm
        seuil = v_ag if self._portee == self.PORTEE_GEN else v_am

        if stock == 0:
            return self.ETAT_RUPTURE
        if stock <= seuil:
            return self.ETAT_ALERTE
        return self.ETAT_NORMAL

    def _apply_filters(self):
        search  = self._var_recherche.get().lower().strip()
        mag_sel = self._var_magasin.get()
        result  = []

        for row in self.all_rows:
            if len(row) < 11:
                continue
            if search:
                if search not in " ".join(str(x).lower() for x in row[:4]):
                    continue
            if mag_sel and mag_sel != "Tous":
                if str(row[3]) != mag_sel:
                    continue
            if self._etat != self.ETAT_TOUS:
                if self._row_etat(row) != self._etat:
                    continue
            result.append(row)

        self._populate_table(result)

    def _refresh_magasin_filter(self):
        mags = sorted({str(r[3]) for r in self.all_rows if len(r) > 3})
        self._combo_mag["values"] = ["Tous"] + mags
        self._var_magasin.set("Tous")

    # ── Peuplement tableau ────────────────────────────────────────────────────
    def _populate_table(self, rows):
        self.tree.delete(*self.tree.get_children())
        self.item_ids = {}
        n_n = n_a = n_r = 0

        for row in rows:
            if len(row) < 11:
                continue
            (code, desig, unite, mag,
             am, sm, ag, sg,
             idarticle, idunite, idmag) = row

            try:
                f_sm = float(sm or 0)
                f_sg = float(sg or 0)
                f_am = float(am or 0)
                f_ag = float(ag or 0)
            except (TypeError, ValueError):
                f_sm = f_sg = f_am = f_ag = 0.0

            etat = self._row_etat(row)
            tag  = {'rupture': 'rupture', 'alerte': 'alerte',
                    'normal': 'normal'}[etat]
            if etat == 'normal':   n_n += 1
            elif etat == 'alerte': n_a += 1
            else:                  n_r += 1

            item_id = self.tree.insert(
                '', 'end',
                values=(code, desig, unite, mag,
                        round(f_am, 2), round(f_sm, 2),
                        round(f_ag, 2), round(f_sg, 2)),
                tags=(tag,),
            )
            self.item_ids[item_id] = (idarticle, idunite, idmag)

        total = len(rows)
        self._lbl_total.configure(text=f"{total} article(s)")
        self._sc_total.configure(text=str(total))
        self._sc_normal.configure(text=str(n_n))
        self._sc_alerte.configure(text=str(n_a))
        self._sc_rupture.configure(text=str(n_r))

    # ── Éditeur d'alertes ─────────────────────────────────────────────────────
    def _on_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if item and item in self.item_ids:
            self._open_article_editor(item)

    def _open_article_editor(self, item_id):
        idarticle, idunite, idmag = self.item_ids[item_id]
        v = self.tree.item(item_id, "values")
        codearticle        = v[0]
        designation        = v[1]
        designationunite   = v[2]
        designationmag     = v[3]
        alertdepot_current = v[4]
        alert_current      = v[6]

        win = ctk.CTkToplevel(self)
        win.title("Modifier les alertes")
        win.resizable(False, False)
        win.grab_set()
        win.configure(fg_color=C.BG_PAGE)
        win.update_idletasks()
        W, H = 540, 500
        win.geometry(f"{W}x{H}+"
                     f"{win.winfo_screenwidth()//2 - W//2}+"
                     f"{win.winfo_screenheight()//2 - H//2}")

        # Header
        hdr = ctk.CTkFrame(win, fg_color=C.BG_HEADER, corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text="📦  Modifier les alertes",
                     font=self._f(15, "bold"), text_color="#FFFFFF"
                     ).pack(side="left", padx=20, pady=12)

        body = ctk.CTkFrame(win, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=16)

        # Info article
        ifrm = ctk.CTkFrame(body, fg_color=C.BG_CARD, corner_radius=8)
        ifrm.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(ifrm, text=str(designation),
                     font=self._f(14, "bold"), text_color=C.TEXT_PRIMARY,
                     anchor="w").pack(fill="x", padx=14, pady=(10, 2))
        ctk.CTkLabel(ifrm,
                     text=f"Code : {codearticle}   •   Unité : {designationunite}",
                     font=self._f(10), text_color=C.TEXT_MUTED,
                     anchor="w").pack(fill="x", padx=14, pady=(0, 10))

        # Magasin
        ctk.CTkLabel(body, text="Magasin de rattachement",
                     font=self._f(11, "bold"), text_color=C.TEXT_SECONDARY,
                     anchor="w").pack(fill="x", pady=(0, 4))
        magasins_list    = self._get_magasins()
        var_mag          = StringVar(value=designationmag)
        ttk.Combobox(body, textvariable=var_mag,
                     values=[m[1] for m in magasins_list],
                     state="readonly", width=46,
                     font=("Roboto", 11) if _THEME_OK else ("Segoe UI", 11)
                     ).pack(fill="x", ipady=4, pady=(0, 14))

        # Alertes (2 colonnes)
        ar = ctk.CTkFrame(body, fg_color="transparent")
        ar.pack(fill="x", pady=(0, 16))
        ar.columnconfigure(0, weight=1)
        ar.columnconfigure(1, weight=1)

        var_alert_depot = var_alert_general = None  # initialisées dans la boucle
        _vars = {}
        for col, title, icon, bg, init in [
            (0, "Alerte Magasin",  "🏪", C.WARNING_LIGHT, alertdepot_current),
            (1, "Alerte Générale", "🌐",
             C.PRIMARY_LIGHT if _THEME_OK else "#D6EAF8", alert_current),
        ]:
            frm = ctk.CTkFrame(ar, fg_color=bg, corner_radius=8)
            frm.grid(row=0, column=col, sticky="nsew",
                     padx=(0, 8) if col == 0 else (8, 0))
            ctk.CTkLabel(frm, text=f"{icon}  {title}",
                         font=self._f(12, "bold"),
                         text_color=C.TEXT_PRIMARY, anchor="w"
                         ).pack(anchor="w", padx=12, pady=(10, 2))
            ctk.CTkLabel(frm, text=f"(en {designationunite})",
                         font=self._f(10), text_color=C.TEXT_MUTED,
                         anchor="w").pack(anchor="w", padx=12, pady=(0, 4))
            var = StringVar(value=str(init))
            _vars[col] = var
            ctk.CTkEntry(frm, textvariable=var,
                         font=ctk.CTkFont(size=13),
                         justify="center", height=36
                         ).pack(fill="x", padx=12, pady=(0, 12))

        var_alert_depot   = _vars[0]
        var_alert_general = _vars[1]

        # Boutons
        bf = ctk.CTkFrame(body, fg_color="transparent")
        bf.pack(fill="x", side="bottom", pady=(4, 0))

        def do_save():
            try:
                new_ad = float(var_alert_depot.get())
                new_ag = float(var_alert_general.get())
            except ValueError:
                messagebox.showerror("Erreur",
                                     "Les valeurs d'alerte doivent être des nombres.")
                return
            sel_mag = idmag
            for mid, mname in magasins_list:
                if mname == var_mag.get():
                    sel_mag = mid
                    break
            conn = self.connect_db()
            if not conn:
                return
            try:
                conn.cursor().execute(
                    "UPDATE public.tb_article "
                    "SET alertdepot=%s, alert=%s, idmag=%s WHERE idarticle=%s",
                    (new_ad, new_ag, sel_mag, idarticle))
                conn.commit()
                messagebox.showinfo("Succès", "Alertes mises à jour.")
                try:
                    self._logger.log(
                        action="Modification alerte stock",
                        element=str(designation),
                        details=f"Stock Alerte ({'Générale' if self._portee == self.PORTEE_GEN else 'Magasin'}): article={codearticle}, magasin='{var_mag.get()}', seuil_mag={new_ad}, seuil_gen={new_ag}",
                        value=f"seuil_mag={new_ad}, seuil_gen={new_ag}",
                    )
                except Exception:
                    pass
                win.destroy()
                self.charger_donnees()
            except Exception as e:
                messagebox.showerror("Erreur SQL", str(e))
            finally:
                conn.close()

        ctk.CTkButton(bf, text="Fermer", command=win.destroy,
                      fg_color="transparent", border_width=1,
                      border_color=C.BORDER, text_color=C.TEXT_PRIMARY,
                      width=110, height=36).pack(side="left")
        ctk.CTkButton(bf, text="💾  Enregistrer", command=do_save,
                      fg_color=C.SUCCESS_DARK if _THEME_OK else "#27AE60",
                      hover_color=C.SUCCESS if _THEME_OK else "#2ECC71",
                      text_color="#FFFFFF", width=160, height=36,
                      font=self._f(13, "bold")).pack(side="right")

    def _get_magasins(self):
        conn = self.connect_db()
        if not conn:
            return []
        try:
            cur = conn.cursor()
            cur.execute("SELECT idmag, designationmag FROM public.tb_magasin "
                        "WHERE deleted=0 ORDER BY designationmag")
            return cur.fetchall()
        except Exception:
            return []
        finally:
            conn.close()