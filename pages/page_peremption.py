# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              iJeery — page_gestionPeremption.py  (refonte v2)              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  • Thème iJeery (app_theme) — même patron que page_ArticleMouvement         ║
║  • Fenêtres modales thémées (ajout lot + gestion lot existant)              ║
║  • Logique métier SQL inchangée                                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import customtkinter as ctk
from tkinter import ttk, messagebox, StringVar, BooleanVar
import psycopg2, psycopg2.extras, json
from datetime import datetime, timedelta
from resource_utils import get_config_path
from log_utils import AppLogger

# ── Thème iJeery ──────────────────────────────────────────────────────────────
try:
    from app_theme import Colors, Fonts, styled, Theme
    _T = True
except ImportError:
    _T = False


class _C:
    MIDNIGHT        = "#2C3E50"
    BG_PAGE         = "#ECF0F1"
    BG_CARD         = "#FFFFFF"
    BG_HEADER       = "#2C3E50"
    BG_INPUT        = "#F4F6F8"
    PRIMARY         = "#3498DB"
    PRIMARY_HOVER   = "#2980B9"
    SUCCESS         = "#2ECC71"
    SUCCESS_DARK    = "#27AE60"
    SUCCESS_LIGHT   = "#D5F5E3"
    SUCCESS_TEXT    = "#1E8449"
    DANGER          = "#E74C3C"
    DANGER_DARK     = "#C0392B"
    DANGER_LIGHT    = "#FADBD8"
    DANGER_TEXT     = "#922B21"
    WARNING         = "#F39C12"
    WARNING_LIGHT   = "#FEF9E7"
    WARNING_TEXT    = "#9A6A00"
    INFO            = "#1ABC9C"
    INFO_DARK       = "#16A085"
    INFO_LIGHT      = "#D1F2EB"
    INFO_TEXT       = "#0E6655"
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
#  Requêtes SQL (inchangées)
# ─────────────────────────────────────────────────────────────────────────────
SQL_TOUS = """
WITH RECURSIVE
    facteur_conversion AS (
        SELECT u.idunite, u.idarticle, u.niveau, u.designationunite,
               1.0::double precision AS facteur_vers_base
        FROM tb_unite u WHERE u.niveau = 0 AND u.deleted = 0
        UNION ALL
        SELECT u.idunite, u.idarticle, u.niveau, u.designationunite,
               fc.facteur_vers_base * u.qtunite
        FROM tb_unite u
        JOIN facteur_conversion fc ON fc.idarticle = u.idarticle
                                  AND fc.niveau = u.niveau - 1
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
        SELECT lf.idunite, lf.idmag, lf.qtlivrefrs AS quantite, 1 AS signe
          FROM tb_livraisonfrs lf WHERE lf.deleted = 0
        UNION ALL
        SELECT u.idunite, inv.idmag, inv.qtinventaire, 1
          FROM tb_inventaire inv
          JOIN tb_unite u ON u.codearticle = inv.codearticle
                         AND u.niveau = 0 AND u.deleted = 0
        UNION ALL
        SELECT ad.idunite, ad.idmag, ad.qtavoir, 1
          FROM tb_avoirdetail ad JOIN tb_avoir av ON av.id = ad.idavoir
         WHERE ad.deleted = 0 AND av.deleted = 0
        UNION ALL
        SELECT dce.idunite, dce.idmagasin, dce.quantite_entree::double precision, 1
          FROM tb_detailchange_entree dce
          JOIN tb_changement chg ON chg.idchg = dce.idchg
        UNION ALL
        SELECT td.idunite, td.idmagentree, td.qttransfertentree, 1
          FROM tb_transfertdetail td
          JOIN tb_transfert t ON t.idtransfert = td.idtransfert
         WHERE td.deleted = 0 AND t.deleted = 0
        UNION ALL
        SELECT vd.idunite, vd.idmag, vd.qtvente, -1
          FROM tb_ventedetail vd JOIN tb_vente v ON v.id = vd.idvente
         WHERE vd.deleted = 0 AND v.deleted = 0 AND v.statut = 'VALIDEE'
        UNION ALL
        SELECT sd.idunite, sd.idmag, sd.qtsortie, -1
          FROM tb_sortiedetail sd JOIN tb_sortie s ON s.id = sd.idsortie
         WHERE sd.deleted = 0 AND s.deleted = 0
        UNION ALL
        SELECT cid.idunite, cid.idmag, cid.qtconsomme::double precision, -1
          FROM tb_consommationinterne_details cid
          JOIN tb_consommationinterne ci ON ci.id = cid.idconsommation
        UNION ALL
        SELECT dcs.idunite, dcs.idmagasin, dcs.quantite_sortie::double precision, -1
          FROM tb_detailchange_sortie dcs
          JOIN tb_changement chg ON chg.idchg = dcs.idchg
        UNION ALL
        SELECT td.idunite, td.idmagsortie, td.qttransfertsortie, -1
          FROM tb_transfertdetail td
          JOIN tb_transfert t ON t.idtransfert = td.idtransfert
         WHERE td.deleted = 0 AND t.deleted = 0
    ),
    stock_par_mag AS (
        SELECT fc.idarticle, tm.idmag,
               COALESCE(SUM(tm.quantite * fc.facteur_vers_base * tm.signe), 0.0)
                   AS stock_base_mag
        FROM tous_mouvements tm
        JOIN facteur_conversion fc ON fc.idunite = tm.idunite
        GROUP BY fc.idarticle, tm.idmag
    ),
    lots_ranked AS (
        SELECT lp.id, lp.id_article, lp.id_unite, lp.idmag,
               lp.quantite, lp.date_peremption, lp.priorite,
               lp.date_entree, lp.note,
               SUM(lp.quantite) OVER (
                   PARTITION BY lp.id_article, lp.id_unite, lp.idmag
                   ORDER BY lp.priorite DESC, lp.date_entree DESC
                   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
               ) AS cumul_depuis_recents
        FROM tb_lot_peremption lp WHERE lp.deleted = 0
    )
SELECT
    um.codearticle,
    a.designation                                                                    AS designationarticle,
    um.designationunite                                                              AS unite,
    um.facteur_vers_base,
    m.designationmag                                                                 AS designationmag,
    lr.idmag,
    ROUND((COALESCE(sm.stock_base_mag,0.0)/um.facteur_vers_base)::numeric, 4)        AS stock_global,
    lr.id                                                                            AS id_lot,
    lr.id_article,
    lr.id_unite,
    lr.date_peremption,
    lr.date_entree,
    lr.priorite,
    lr.note,
    ROUND((lr.quantite)::numeric, 4)                                                 AS qt_lot_unite,
    ROUND(
        (GREATEST(0.0, LEAST(
            lr.quantite,
            COALESCE(sm.stock_base_mag,0.0) - (lr.cumul_depuis_recents - lr.quantite)
        )))::numeric
    , 4)                                                                             AS qt_restante_unite,
    a.idarticle,
    TRUE                                                                             AS has_lot
FROM lots_ranked lr
JOIN tb_article  a  ON a.idarticle  = lr.id_article AND a.deleted = 0
JOIN unite_max   um ON um.idarticle = lr.id_article
LEFT JOIN tb_magasin m  ON m.idmag  = lr.idmag
LEFT JOIN stock_par_mag sm ON sm.idarticle = lr.id_article AND sm.idmag = lr.idmag

UNION ALL

SELECT
    um.codearticle,
    a.designation                                                                    AS designationarticle,
    um.designationunite                                                              AS unite,
    um.facteur_vers_base,
    m.designationmag                                                                 AS designationmag,
    sm.idmag,
    ROUND((sm.stock_base_mag / um.facteur_vers_base)::numeric, 4)                   AS stock_global,
    NULL   AS id_lot,
    a.idarticle AS id_article,
    um.idunite  AS id_unite,
    NULL   AS date_peremption,
    NULL   AS date_entree,
    NULL   AS priorite,
    NULL   AS note,
    NULL   AS qt_lot_unite,
    NULL   AS qt_restante_unite,
    a.idarticle,
    FALSE  AS has_lot
FROM tb_article a
JOIN unite_max   um ON um.idarticle = a.idarticle
JOIN stock_par_mag sm ON sm.idarticle = a.idarticle AND sm.stock_base_mag > 0
JOIN tb_magasin  m  ON m.idmag = sm.idmag AND m.deleted = 0
WHERE a.deleted = 0
  AND NOT EXISTS (
      SELECT 1 FROM tb_lot_peremption lp
      WHERE lp.id_article = a.idarticle
        AND lp.idmag = sm.idmag
        AND lp.deleted = 0
  )
ORDER BY codearticle, designationmag,
         priorite ASC NULLS LAST, date_entree ASC NULLS LAST;
"""

SQL_MAGASINS = ("SELECT idmag, designationmag FROM tb_magasin "
                "WHERE deleted=0 ORDER BY designationmag;")


# ─────────────────────────────────────────────────────────────────────────────
#  Page principale
# ─────────────────────────────────────────────────────────────────────────────
class PageGestionPeremption(ctk.CTkFrame):

    # Couleurs sémantiques des tags (visibles dans le treeview)
    _TAG_COLORS = {
        "perime":   C.DANGER,
        "urgent":   C.WARNING,
        "proche":   C.SUCCESS_DARK,
        "normal":   C.TEXT_PRIMARY,
        "epuise":   C.TEXT_MUTED,
        "sans_lot": C.TEXT_SECONDARY,
    }

    def __init__(self, parent, iduser=1):
        super().__init__(parent, fg_color=C.BG_PAGE)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.iduser       = iduser
        self._logger      = AppLogger(session_data={"user_id": self.iduser} if self.iduser else {})
        self.all_rows     = []
        self.item_meta    = {}
        self.magasins     = []
        self.search_timer = None
        self._sort_state  = {}

        self._apply_tree_style()
        self._build_ui()
        self._load_magasins()
        self.charger_donnees()

    # ── helpers ──────────────────────────────────────────────────────────────
    def connect_db(self):
        try:
            with open(get_config_path('config.json')) as f:
                cfg = json.load(f)['database']
            return psycopg2.connect(
                host=cfg['host'], user=cfg['user'],
                password=cfg['password'],
                database=cfg['database'], port=cfg['port'])
        except Exception as e:
            messagebox.showerror("Connexion", f"Erreur : {e}")
            return None

    def _exec(self, sql, params=()):
        conn = self.connect_db()
        if not conn:
            return []
        try:
            with conn.cursor(
                    cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            messagebox.showerror("SQL", str(e))
            return []
        finally:
            conn.close()

    def _exec_write(self, sql, params=()):
        conn = self.connect_db()
        if not conn:
            return False
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            messagebox.showerror("SQL", str(e))
            return False
        finally:
            conn.close()

    def _load_magasins(self):
        rows = self._exec(SQL_MAGASINS)
        self.magasins = [(r['idmag'], r['designationmag']) for r in rows]
        noms = ["Tous les magasins"] + [m[1] for m in self.magasins]
        try:
            self.combo_mag['values'] = noms
        except Exception:
            pass

    # ── Style treeview ────────────────────────────────────────────────────────
    def _apply_tree_style(self):
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure("Per.Treeview",
                    background=C.BG_CARD, foreground=C.TEXT_PRIMARY,
                    fieldbackground=C.BG_CARD, rowheight=24,
                    font=("Roboto" if _T else "Segoe UI", 9),
                    borderwidth=0)
        s.configure("Per.Treeview.Heading",
                    background=C.BG_HEADER, foreground="#FFFFFF",
                    font=("Roboto" if _T else "Segoe UI", 9, "bold"),
                    relief="flat", padding=(4, 4))
        s.map("Per.Treeview",
              background=[("selected", C.PRIMARY)],
              foreground=[("selected", "#FFFFFF")])

    # ── Construction UI ───────────────────────────────────────────────────────
    def _build_ui(self):
        # ── En-tête ──────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=C.BG_HEADER, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(hdr, text="Suivi des Péremptions",
                     font=_f(18, "bold"),
                     text_color="#FFFFFF"
                     ).pack(side="left", padx=16, pady=8)
        self._lbl_statut = ctk.CTkLabel(hdr, text="",
                                        font=_f(9), text_color=C.TEXT_ON_DARK_DIM)
        self._lbl_statut.pack(side="right", padx=16)

        # ── Barre de filtres ─────────────────────────────────────────────────
        panel = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=8)
        panel.grid(row=1, column=0, sticky="ew", padx=12, pady=6)
        inner = ctk.CTkFrame(panel, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=8)

        # Recherche
        ctk.CTkLabel(inner, text="🔍", font=_f(13),
                     width=22).pack(side="left", padx=(0, 3))
        self.entry_recherche = ctk.CTkEntry(
            inner,
            placeholder_text="Code ou désignation…",
            width=220, height=28,
            fg_color=C.BG_INPUT, border_color=C.BORDER,
            border_width=1, text_color=C.TEXT_PRIMARY,
            font=_f(10), corner_radius=6)
        self.entry_recherche.pack(side="left", padx=(0, 8))
        self.entry_recherche.bind("<KeyRelease>", self.on_search_change)

        # Séparateur
        ctk.CTkFrame(inner, width=1, height=20,
                     fg_color=C.BORDER).pack(side="left", padx=(0, 8))

        # Filtre état
        ctk.CTkLabel(inner, text="État :",
                     font=_f(10), text_color=C.TEXT_MUTED
                     ).pack(side="left", padx=(0, 4))
        self.var_filter = StringVar(value="Tous")
        self.combo_etat = ttk.Combobox(
            inner,
            values=["Tous", "Perime", "< 1 mois", "< 2 mois",
                    "> 2 mois", "Epuise", "Sans peremption"],
            textvariable=self.var_filter,
            state="readonly", width=14,
            font=("Segoe UI", 9))
        self.combo_etat.pack(side="left", padx=(0, 8), ipady=2)
        self.combo_etat.bind("<<ComboboxSelected>>", self.on_filter_change)

        # Filtre magasin
        ctk.CTkLabel(inner, text="Magasin :",
                     font=_f(10), text_color=C.TEXT_MUTED
                     ).pack(side="left", padx=(0, 4))
        self.var_magasin = StringVar(value="Tous les magasins")
        self.combo_mag = ttk.Combobox(
            inner,
            values=["Tous les magasins"],
            textvariable=self.var_magasin,
            state="readonly", width=18,
            font=("Segoe UI", 9))
        self.combo_mag.pack(side="left", padx=(0, 8), ipady=2)
        self.combo_mag.bind("<<ComboboxSelected>>", self.on_filter_change)

        # Séparateur
        ctk.CTkFrame(inner, width=1, height=20,
                     fg_color=C.BORDER).pack(side="left", padx=(0, 8))

        # Checkbox
        self.var_with_per = BooleanVar(value=True)
        ctk.CTkCheckBox(
            inner,
            text="Avec péremption uniquement",
            variable=self.var_with_per,
            command=self.on_filter_change,
            font=_f(10), text_color=C.TEXT_PRIMARY,
            checkbox_width=16, checkbox_height=16,
            corner_radius=3,
            fg_color=C.PRIMARY, hover_color=C.PRIMARY_HOVER
        ).pack(side="left", padx=(0, 8))

        # Séparateur
        ctk.CTkFrame(inner, width=1, height=20,
                     fg_color=C.BORDER).pack(side="left", padx=(0, 8))

        # Bouton Actualiser
        ctk.CTkButton(
            inner, text="↺  Actualiser",
            command=self.charger_donnees,
            height=28, width=110,
            fg_color=C.SUCCESS_DARK, hover_color=C.SUCCESS,
            text_color="#FFFFFF", font=_f(10, "bold"),
            corner_radius=6
        ).pack(side="left")

        # ── Tableau ──────────────────────────────────────────────────────────
        tbl = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=8)
        tbl.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 4))
        tbl.grid_rowconfigure(0, weight=1)
        tbl.grid_columnconfigure(0, weight=1)

        cols = ("Code", "Designation", "Unite", "Magasin",
                "Stock global", "Priorite", "Date entree",
                "Date peremption", "Jours rest.",
                "Qt lot", "Qt restante", "Note")

        self.tree = ttk.Treeview(tbl, columns=cols, show="headings",
                                 style="Per.Treeview", height=18)

        # Tags couleurs
        self.tree.tag_configure(
            "perime",   foreground=C.DANGER,
            font=("Roboto" if _T else "Segoe UI", 9, "bold"))
        self.tree.tag_configure(
            "urgent",   foreground=C.WARNING,
            font=("Roboto" if _T else "Segoe UI", 9, "bold"))
        self.tree.tag_configure(
            "proche",   foreground=C.SUCCESS_DARK,
            font=("Roboto" if _T else "Segoe UI", 9))
        self.tree.tag_configure(
            "normal",   foreground=C.TEXT_PRIMARY,
            font=("Roboto" if _T else "Segoe UI", 9))
        self.tree.tag_configure(
            "epuise",   foreground=C.TEXT_MUTED,
            font=("Roboto" if _T else "Segoe UI", 9, "italic"))
        self.tree.tag_configure(
            "sans_lot", foreground=C.TEXT_SECONDARY,
            font=("Roboto" if _T else "Segoe UI", 9, "italic"))

        col_cfg = {
            "Code":          (100, "center"),
            "Designation":   (210, "w"),
            "Unite":         (80,  "center"),
            "Magasin":       (120, "w"),
            "Stock global":  (95,  "center"),
            "Priorite":      (60,  "center"),
            "Date entree":   (95,  "center"),
            "Date peremption": (155, "w"),
            "Jours rest.":   (85,  "center"),
            "Qt lot":        (85,  "center"),
            "Qt restante":   (100, "center"),
            "Note":          (150, "w"),
        }
        for col in cols:
            w, anchor = col_cfg[col]
            self.tree.heading(col, text=col,
                              command=lambda c=col: self._sort_by(c))
            self.tree.column(col, width=w, anchor=anchor)

        sy = ctk.CTkScrollbar(tbl, orientation="vertical",
                              command=self.tree.yview)
        sx = ctk.CTkScrollbar(tbl, orientation="horizontal",
                              command=self.tree.xview)
        self.tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.tree.grid(row=0, column=0, sticky="nsew",
                       padx=(6, 0), pady=(6, 0))
        sy.grid(row=0, column=1, sticky="ns", pady=(6, 0))
        sx.grid(row=1, column=0, sticky="ew", padx=(6, 0))

        self.tree.bind("<Double-Button-1>", self.on_double_click)

        # ── Footer ───────────────────────────────────────────────────────────
        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.grid(row=3, column=0, sticky="ew", padx=12, pady=(2, 8))

        self.lbl_total = ctk.CTkLabel(
            foot, text="",
            font=_f(10, "bold"), text_color=C.PRIMARY)
        self.lbl_total.pack(side="left", padx=(0, 16))

        # Légende
        legend = ctk.CTkFrame(foot, fg_color="transparent")
        legend.pack(side="left")
        for txt, col in [
            ("Sans pér.",  C.TEXT_SECONDARY),
            ("Épuisé",     C.TEXT_MUTED),
            ("> 2 mois",   C.TEXT_PRIMARY),
            ("< 2 mois",   C.SUCCESS_DARK),
            ("< 1 mois",   C.WARNING),
            ("Périmé",     C.DANGER),
        ]:
            ctk.CTkLabel(
                legend, text=f"● {txt}",
                text_color=col,
                font=_f(9, "bold")
            ).pack(side="right", padx=6)

        self.lbl_statut_foot = ctk.CTkLabel(
            foot, text="",
            font=_f(9), text_color=C.TEXT_MUTED)
        self.lbl_statut_foot.pack(side="right")

    # ─────────────────────────────────────────────────────────────────────────
    #  Chargement & Populate — logique métier inchangée
    # ─────────────────────────────────────────────────────────────────────────
    def charger_donnees(self):
        self._lbl_statut.configure(text="Chargement…")
        self.lbl_total.configure(text="…")
        self.update()
        rows  = self._exec(SQL_TOUS)
        terme = self.entry_recherche.get().strip().lower()
        if terme:
            rows = [r for r in rows
                    if terme in str(r['codearticle']).lower()
                    or terme in str(r['designationarticle']).lower()]
        self.all_rows = rows
        self._populate(rows)
        self._lbl_statut.configure(
            text=f"MAJ : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    @staticmethod
    def _tag(row):
        if not row.get('has_lot'):
            return 'sans_lot'
        today    = datetime.today().date()
        date_per = row['date_peremption']
        qt_rest  = float(row['qt_restante_unite'] or 0)
        if qt_rest <= 0:
            return 'epuise'
        if isinstance(date_per, datetime):
            date_per = date_per.date()
        if not date_per:
            return 'normal'
        if date_per <= today:
            return 'perime'
        if date_per <= today + timedelta(days=30):
            return 'urgent'
        if date_per <= today + timedelta(days=60):
            return 'proche'
        return 'normal'

    def _populate(self, rows):
        self.tree.delete(*self.tree.get_children())
        self.item_meta = {}
        today    = datetime.today().date()

        filt     = self.var_filter.get()
        filt_map = {
            'Perime':          'perime',
            '< 1 mois':        'urgent',
            '< 2 mois':        'proche',
            '> 2 mois':        'normal',
            'Epuise':          'epuise',
            'Sans peremption': 'sans_lot',
        }
        required       = filt_map.get(filt)
        mag_sel        = self.var_magasin.get()
        with_per_only  = self.var_with_per.get()

        for r in rows:
            tag = self._tag(r)

            if mag_sel and mag_sel != "Tous les magasins":
                if str(r.get('designationmag', '')) != mag_sel:
                    continue

            if with_per_only and tag == 'sans_lot':
                continue

            if required and tag != required:
                continue

            has_lot     = bool(r.get('has_lot'))
            date_per    = r['date_peremption']
            if isinstance(date_per, datetime):
                date_per = date_per.date()
            de          = r['date_entree']
            date_entree_s = (de.strftime('%d/%m/%Y')
                             if hasattr(de, 'strftime') else
                             str(de) if de else '')

            if date_per:
                j       = (date_per - today).days
                jours_s    = f"PERIME {j}j" if j < 0 else f"{j} j"
                date_per_s = date_per.strftime('%d/%m/%Y')
            else:
                jours_s    = ''
                date_per_s = '— Aucune péremption —' if not has_lot else ''

            qt_rest  = float(r['qt_restante_unite'] or 0) if has_lot else None
            qt_lot   = float(r['qt_lot_unite']      or 0) if has_lot else None
            stock_gl = float(r['stock_global']       or 0)
            prio_s   = str(r['priorite']) if r['priorite'] is not None else ''
            mag_s    = r.get('designationmag') or '—'

            values = (
                r['codearticle'],
                r['designationarticle'],
                r['unite'],
                mag_s,
                f"{stock_gl:,.2f}".replace(',', ' '),
                prio_s,
                date_entree_s,
                date_per_s,
                jours_s,
                f"{qt_lot:,.2f}".replace(',', ' ')  if qt_lot  is not None else '',
                f"{qt_rest:,.2f}".replace(',', ' ') if qt_rest is not None else '',
                r['note'] or '',
            )
            iid = self.tree.insert('', 'end', values=values, tags=(tag,))
            self.item_meta[iid] = dict(r)

        nb_lots = sum(1 for r in self.item_meta.values() if r.get('has_lot'))
        nb_sans = sum(1 for r in self.item_meta.values() if not r.get('has_lot'))
        self.lbl_total.configure(
            text=(f"{len(self.item_meta)} ligne(s)   |   "
                  f"Avec lots : {nb_lots}   |   "
                  f"Sans péremption : {nb_sans}"))

    # ── Filtres ───────────────────────────────────────────────────────────────
    def on_search_change(self, *_):
        if self.search_timer:
            self.after_cancel(self.search_timer)
        self.search_timer = self.after(400, self.charger_donnees)

    def on_filter_change(self, *_):
        self._populate(self.all_rows)

    def _sort_by(self, col):
        reverse = self._sort_state.get(col, False)
        self._sort_state[col] = not reverse
        key_map = {
            "Code":             "codearticle",
            "Designation":      "designationarticle",
            "Unite":            "unite",
            "Magasin":          "designationmag",
            "Stock global":     "stock_global",
            "Priorite":         "priorite",
            "Date entree":      "date_entree",
            "Date peremption":  "date_peremption",
            "Qt lot":           "qt_lot_unite",
            "Qt restante":      "qt_restante_unite",
        }
        k = key_map.get(col)
        if k:
            try:
                self._populate(sorted(
                    self.all_rows,
                    key=lambda r: (r[k] is None, r[k]),
                    reverse=reverse))
            except Exception:
                pass

    # ── Double-clic ───────────────────────────────────────────────────────────
    def on_double_click(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid or iid not in self.item_meta:
            return
        row = self.item_meta[iid]
        if row.get('has_lot'):
            self.ouvrir_gestion_lot(row)
        else:
            self.ouvrir_ajout_peremption(row)

    # ─────────────────────────────────────────────────────────────────────────
    #  Helpers fenêtres modales
    # ─────────────────────────────────────────────────────────────────────────
    def _make_toplevel(self, title, w, h):
        win = ctk.CTkToplevel(self)
        win.title(title)
        win.resizable(False, False)
        win.grab_set()
        if _T:
            Theme.apply_toplevel(win)
        win.update_idletasks()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        return win

    @staticmethod
    def _sep(parent):
        ctk.CTkFrame(parent, height=1, fg_color=C.DIVIDER).pack(
            fill="x", padx=0, pady=(0, 12))

    # ── Carte info (petite) ───────────────────────────────────────────────────
    @staticmethod
    def _info_card(parent, col, label, value, color=None):
        f = ctk.CTkFrame(parent, fg_color=C.BG_PAGE,
                         corner_radius=8,
                         border_width=1, border_color=C.BORDER)
        f.grid(row=0, column=col, sticky="nsew",
               padx=(0 if col == 0 else 5, 0), pady=0)
        ctk.CTkLabel(f, text=label,
                     font=_f(9), text_color=C.TEXT_MUTED,
                     anchor="w").pack(anchor="w", padx=10, pady=(8, 1))
        kw = {"font": _f(12, "bold"), "anchor": "w"}
        if color:
            kw["text_color"] = color
        ctk.CTkLabel(f, text=str(value), **kw).pack(
            anchor="w", padx=10, pady=(0, 8))

    # ─────────────────────────────────────────────────────────────────────────
    #  Fenêtre : ajout péremption (article sans lot)
    # ─────────────────────────────────────────────────────────────────────────
    def ouvrir_ajout_peremption(self, row):
        win  = self._make_toplevel(
            f"Ajouter une péremption — {row['codearticle']}", 520, 490)

        # ── En-tête ──────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(win, fg_color=C.BG_HEADER, corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text="📦  Nouveau lot de péremption",
                     font=_f(14, "bold"), text_color="#FFFFFF"
                     ).pack(side="left", padx=16, pady=10)

        root = ctk.CTkFrame(win, fg_color="transparent")
        root.pack(fill="both", expand=True, padx=20, pady=14)

        # Article info
        ctk.CTkLabel(root, text=str(row['designationarticle']),
                     font=_f(13, "bold"), text_color=C.TEXT_PRIMARY,
                     anchor="w").pack(fill="x")
        ctk.CTkLabel(root,
                     text=(f"Code : {row['codearticle']}   •   "
                           f"Unité : {row['unite']}"),
                     font=_f(10), text_color=C.TEXT_MUTED,
                     anchor="w").pack(fill="x", pady=(1, 10))
        self._sep(root)

        # Cards info
        stock_gl = float(row['stock_global'] or 0)
        mag_nom  = row.get('designationmag') or '—'
        cards    = ctk.CTkFrame(root, fg_color="transparent")
        cards.pack(fill="x", pady=(0, 12))
        cards.columnconfigure((0, 1, 2), weight=1)
        self._info_card(cards, 0, "Magasin",             mag_nom)
        self._info_card(cards, 1, "Stock (ce magasin)",
                        f"{stock_gl:,.2f} {row['unite']}")
        self._info_card(cards, 2, "Lots existants",      "Aucun",
                        color=C.TEXT_MUTED)

        self._sep(root)

        ctk.CTkLabel(root,
                     text="Vous pouvez enregistrer tout le stock ou une partie.",
                     font=_f(10), text_color=C.TEXT_MUTED,
                     anchor="w").pack(fill="x", pady=(0, 10))

        # Formulaire
        form = ctk.CTkFrame(root, fg_color=C.BG_CARD,
                            corner_radius=8,
                            border_width=1, border_color=C.BORDER)
        form.pack(fill="x", pady=(0, 12))
        form.columnconfigure((0, 1), weight=1)

        for ci, lbl in enumerate([
            f"Quantité du lot  (max {stock_gl:,.2f})",
            "Date de péremption  (JJ/MM/AAAA)"
        ]):
            ctk.CTkLabel(form, text=lbl,
                         font=_f(10, "bold"), text_color=C.TEXT_PRIMARY,
                         anchor="w").grid(
                row=0, column=ci, padx=12,
                pady=(12, 2), sticky="w")

        var_qt   = StringVar(value=f"{stock_gl:.4f}" if stock_gl > 0 else '')
        var_date = StringVar()
        var_note = StringVar()

        entry_qt = ctk.CTkEntry(
            form, textvariable=var_qt, height=32,
            fg_color=C.BG_INPUT, border_color=C.BORDER,
            border_width=1, font=_f(11), corner_radius=6,
            justify="center")
        entry_qt.grid(row=1, column=0, padx=12, pady=(0, 10), sticky="ew")

        entry_date = styled.date_entry(form, width=11)
        entry_date.grid(row=1, column=1, padx=12, pady=(0, 10), sticky="ew")

        ctk.CTkLabel(form, text="Note (optionnel)",
                     font=_f(10, "bold"), text_color=C.TEXT_PRIMARY,
                     anchor="w").grid(
            row=2, column=0, columnspan=2,
            padx=12, pady=(0, 2), sticky="w")
        ctk.CTkEntry(
            form, textvariable=var_note, height=30,
            fg_color=C.BG_INPUT, border_color=C.BORDER,
            border_width=1, font=_f(10), corner_radius=6
        ).grid(row=3, column=0, columnspan=2,
               padx=12, pady=(0, 12), sticky="ew")

        # Boutons
        btn_bar = ctk.CTkFrame(root, fg_color="transparent")
        btn_bar.pack(fill="x", side="bottom", pady=(4, 0))

        def do_ajouter():
            try:
                qt = float(var_qt.get().replace(',', '.'))
            except ValueError:
                messagebox.showerror("Erreur", "La quantité doit être un nombre.")
                return
            if qt <= 0:
                messagebox.showerror("Erreur", "La quantité doit être > 0.")
                return
            from date_picker_utils import get_date_from_widget
            dp = get_date_from_widget(entry_date)
            if not dp:
                messagebox.showerror("Erreur",
                                     "Date invalide — format jj/mm/aaaa.")
                return
            if dp < datetime.today().date():
                if not messagebox.askyesno(
                        "Attention",
                        "La date saisie est dans le passé. Continuer ?"):
                    return
            conn = self.connect_db()
            if not conn:
                return
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT COALESCE(MAX(priorite),0) "
                    "FROM tb_lot_peremption "
                    "WHERE id_article=%s AND id_unite=%s "
                    "AND idmag=%s AND deleted=0",
                    (row['id_article'], row['id_unite'], row['idmag']))
                max_prio = cur.fetchone()[0]
                facteur  = float(row.get('facteur_vers_base') or 1)
                cur.execute(
                    """INSERT INTO tb_lot_peremption
                       (id_article, id_unite, idmag, quantite,
                        date_peremption, priorite, date_entree,
                        type_source, note)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,'MANUEL',%s)""",
                    (row['id_article'], row['id_unite'], row['idmag'],
                     qt * facteur, dp, max_prio + 1,
                     datetime.today().date(),
                     var_note.get() or None))
                conn.commit()
                try:
                    self._logger.log(
                        action="Création lot péremption",
                        element=str(row.get("designationarticle") or row.get("codearticle") or "Article"),
                        details=(
                            f"Création lot péremption magasin='{mag_nom}', "
                            f"qt={qt:,.2f} {row.get('unite','')}, "
                            f"date_peremption={dp.strftime('%d/%m/%Y')}"
                        ),
                        value=f"qt={qt}",
                    )
                except Exception:
                    pass
                messagebox.showinfo(
                    "Succès",
                    f"Lot créé avec succès.\n"
                    f"Magasin : {mag_nom}\n"
                    f"Quantité : {qt:,.2f} {row['unite']}\n"
                    f"Date : {dp.strftime('%d/%m/%Y')}")
                win.destroy()
                self.charger_donnees()
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Erreur SQL", str(e))
            finally:
                conn.close()

        ctk.CTkButton(
            btn_bar, text="Fermer", command=win.destroy,
            height=34, width=100,
            fg_color=C.CLOUDS, hover_color=C.SILVER,
            text_color=C.TEXT_PRIMARY,
            border_width=1, border_color=C.BORDER,
            font=_f(10), corner_radius=6
        ).pack(side="left")
        ctk.CTkButton(
            btn_bar, text="✔  Créer le lot",
            command=do_ajouter,
            height=34, width=160,
            fg_color=C.SUCCESS_DARK, hover_color=C.SUCCESS,
            text_color="#FFFFFF", font=_f(11, "bold"),
            corner_radius=6
        ).pack(side="right")

    # ─────────────────────────────────────────────────────────────────────────
    #  Fenêtre : gestion lot existant
    # ─────────────────────────────────────────────────────────────────────────
    def ouvrir_gestion_lot(self, row):
        win = self._make_toplevel(
            f"Lot #{row['id_lot']}  —  {row['designationarticle']}", 620, 600)

        today    = datetime.today().date()
        date_per = row['date_peremption']
        if isinstance(date_per, datetime):
            date_per = date_per.date()
        jours    = (date_per - today).days if date_per else None
        j_txt    = (f"PÉRIMÉ depuis {abs(jours)}j"
                    if jours is not None and jours < 0
                    else f"{jours} j restants"
                    if jours is not None else '?')
        j_col    = (C.DANGER   if jours is not None and jours <= 0
                    else C.WARNING if jours is not None and jours <= 30
                    else C.SUCCESS_DARK)
        qt_rest  = float(row['qt_restante_unite'] or 0)
        qt_lot   = float(row['qt_lot_unite']      or 0)
        stock_gl = float(row['stock_global']       or 0)
        mag_nom  = row.get('designationmag') or '—'

        # ── En-tête ──────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(win, fg_color=C.BG_HEADER, corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text=f"Lot #{row['id_lot']}",
                     font=_f(14, "bold"), text_color="#FFFFFF"
                     ).pack(side="left", padx=16, pady=10)
        ctk.CTkLabel(hdr,
                     text=f"{row['designationarticle']}  "
                          f"({row['codearticle']})",
                     font=_f(11), text_color=C.TEXT_ON_DARK_DIM
                     ).pack(side="left")

        root = ctk.CTkFrame(win, fg_color="transparent")
        root.pack(fill="both", expand=True, padx=20, pady=14)

        # ── Ligne 1 : 4 cards ────────────────────────────────────────────────
        c1 = ctk.CTkFrame(root, fg_color="transparent")
        c1.pack(fill="x", pady=(0, 6))
        c1.columnconfigure((0, 1, 2, 3), weight=1)
        self._info_card(c1, 0, "Magasin",        mag_nom)
        self._info_card(c1, 1, "Priorité FIFO",  f"#{row['priorite']}")
        self._info_card(c1, 2, "Date péremption",
                        date_per.strftime('%d/%m/%Y') if date_per else '?',
                        color=j_col)
        self._info_card(c1, 3, "Jours restants", j_txt, color=j_col)

        # ── Ligne 2 : 3 cards ────────────────────────────────────────────────
        c2 = ctk.CTkFrame(root, fg_color="transparent")
        c2.pack(fill="x", pady=(0, 10))
        c2.columnconfigure((0, 1, 2), weight=1)
        self._info_card(c2, 0, "Stock magasin",
                        f"{stock_gl:,.2f} {row['unite']}")
        self._info_card(c2, 1, "Qté initiale du lot",
                        f"{qt_lot:,.2f} {row['unite']}")
        self._info_card(c2, 2, "Qté restante (FIFO)",
                        f"{qt_rest:,.2f} {row['unite']}",
                        color=C.DANGER if qt_rest <= 0 else C.SUCCESS_DARK)

        self._sep(root)

        # ── Note ─────────────────────────────────────────────────────────────
        ctk.CTkLabel(root, text="Note / Observation",
                     font=_f(11, "bold"), text_color=C.TEXT_PRIMARY,
                     anchor="w").pack(fill="x")
        var_note = StringVar(value=row.get('note') or '')
        ctk.CTkEntry(
            root, textvariable=var_note, height=32,
            fg_color=C.BG_INPUT, border_color=C.BORDER,
            border_width=1, font=_f(10), corner_radius=6
        ).pack(fill="x", pady=(4, 10))

        self._sep(root)

        # ── Section split ─────────────────────────────────────────────────────
        sp_card = ctk.CTkFrame(root, fg_color=C.BG_CARD,
                               corner_radius=8,
                               border_width=1, border_color=C.BORDER)
        sp_card.pack(fill="x", pady=(0, 12))
        sp_card.columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(sp_card, text="✂  Diviser ce lot en deux",
                     font=_f(11, "bold"), text_color=C.PREMIUM
                     ).grid(row=0, column=0, columnspan=4,
                            padx=12, pady=(10, 4), sticky="w")

        for i, lbl in enumerate([
            "Qté lot A",
            "Date A  (JJ/MM/AAAA)",
            "Qté lot B",
            "Date B  (JJ/MM/AAAA)",
        ]):
            ctk.CTkLabel(sp_card, text=lbl,
                         font=_f(9), text_color=C.TEXT_MUTED
                         ).grid(row=1, column=i,
                                padx=(12 if i == 0 else 6, 0),
                                pady=(0, 2), sticky="w")

        var_qa = StringVar()
        var_da = StringVar(
            value=date_per.strftime('%d/%m/%Y') if date_per else '')
        var_qb = StringVar()
        var_db = StringVar()

        for i, var in enumerate([var_qa, var_da, var_qb, var_db]):
            ctk.CTkEntry(
                sp_card, textvariable=var, height=30,
                fg_color=C.BG_INPUT, border_color=C.BORDER,
                border_width=1, font=_f(10), corner_radius=6,
                justify="center"
            ).grid(row=2, column=i,
                   padx=(12 if i == 0 else 6,
                          12 if i == 3 else 0),
                   pady=(0, 10), sticky="ew")

        # ── Boutons ───────────────────────────────────────────────────────────
        btn_bar = ctk.CTkFrame(root, fg_color="transparent")
        btn_bar.pack(fill="x", side="bottom", pady=(4, 0))

        def do_note():
            if self._exec_write(
                "UPDATE tb_lot_peremption SET note=%s WHERE id=%s",
                    (var_note.get(), row['id_lot'])):
                messagebox.showinfo("Succès", "Note enregistrée.")
                try:
                    self._logger.log(
                        action="Modification péremption",
                        element=f"lot#{row.get('id_lot')}",
                        details=f"Mise à jour note lot péremption (magasin='{mag_nom}')",
                        value=var_note.get() or "",
                    )
                except Exception:
                    pass

        def do_supprimer():
            if not messagebox.askyesno(
                    "Confirmer",
                    f"Supprimer le lot #{row['id_lot']} "
                    f"du magasin '{mag_nom}' ?"):
                return
            if self._exec_write(
                "UPDATE tb_lot_peremption SET deleted=1 WHERE id=%s",
                    (row['id_lot'],)):
                messagebox.showinfo("Succès", "Lot supprimé.")
                try:
                    self._logger.log(
                        action="Suppression lot péremption",
                        element=f"lot#{row.get('id_lot')}",
                        details=f"Suppression lot péremption magasin='{mag_nom}'",
                        value=f"id_lot={row.get('id_lot')}",
                    )
                except Exception:
                    pass
                win.destroy()
                self.charger_donnees()

        def do_split():
            try:
                qa = float(var_qa.get().replace(',', '.'))
                qb = float(var_qb.get().replace(',', '.'))
            except ValueError:
                messagebox.showerror("Erreur", "Quantités invalides.")
                return
            try:
                da  = datetime.strptime(
                    var_da.get().strip(), '%d/%m/%Y').date()
                db_ = datetime.strptime(
                    var_db.get().strip(), '%d/%m/%Y').date()
            except ValueError:
                messagebox.showerror("Erreur",
                                     "Dates invalides (JJ/MM/AAAA).")
                return
            if round(qa + qb, 6) != round(qt_lot, 6):
                if not messagebox.askyesno(
                        "Attention",
                        f"Somme ({qa + qb:.4f}) ≠ "
                        f"Qté initiale ({qt_lot:.4f}).\nContinuer ?"):
                    return
            conn = self.connect_db()
            if not conn:
                return
            try:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE tb_lot_peremption "
                    "SET deleted=1 WHERE id=%s",
                    (row['id_lot'],))
                cur.execute(
                    "SELECT COALESCE(MAX(priorite),0) "
                    "FROM tb_lot_peremption "
                    "WHERE id_article=%s AND id_unite=%s "
                    "AND idmag=%s AND deleted=0",
                    (row['id_article'], row['id_unite'], row['idmag']))
                max_prio = cur.fetchone()[0]
                facteur  = float(row.get('facteur_vers_base') or 1)
                for qt_u, dp, prio, label in [
                    (qa,  da,  row['priorite'], 'A'),
                    (qb,  db_, max_prio + 1,    'B'),
                ]:
                    cur.execute(
                        """INSERT INTO tb_lot_peremption
                           (id_article, id_unite, idmag, quantite,
                            date_peremption, priorite, date_entree,
                            type_source, id_split, note)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,
                                   'SPLIT',%s,%s)""",
                        (row['id_article'], row['id_unite'], row['idmag'],
                         qt_u * facteur, dp, prio,
                         datetime.today().date(),
                         row['id_lot'],
                         f"Split lot #{row['id_lot']} part {label}"))
                conn.commit()
                messagebox.showinfo("Succès", "Lot divisé avec succès.")
                try:
                    self._logger.log(
                        action="Modification péremption",
                        element=f"lot#{row.get('id_lot')}",
                        details=(
                            f"Split lot péremption magasin='{mag_nom}', "
                            f"A: qt={qa} date={da.strftime('%d/%m/%Y')}, "
                            f"B: qt={qb} date={db_.strftime('%d/%m/%Y')}"
                        ),
                        value=f"qa={qa}, qb={qb}",
                    )
                except Exception:
                    pass
                win.destroy()
                self.charger_donnees()
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Erreur SQL", str(e))
            finally:
                conn.close()

        ctk.CTkButton(
            btn_bar, text="🗑  Supprimer",
            command=do_supprimer,
            height=34, width=130,
            fg_color=C.DANGER, hover_color=C.DANGER_DARK,
            text_color="#FFFFFF", font=_f(10, "bold"),
            corner_radius=6
        ).pack(side="left")

        ctk.CTkButton(
            btn_bar, text="💾  Sauver note",
            command=do_note,
            height=34, width=120,
            fg_color=C.PRIMARY, hover_color=C.PRIMARY_HOVER,
            text_color="#FFFFFF", font=_f(10, "bold"),
            corner_radius=6
        ).pack(side="left", padx=(6, 0))

        ctk.CTkButton(
            btn_bar, text="✂  Diviser",
            command=do_split,
            height=34, width=110,
            fg_color=C.PREMIUM, hover_color=C.PREMIUM_DARK,
            text_color="#FFFFFF", font=_f(10, "bold"),
            corner_radius=6
        ).pack(side="left", padx=(6, 0))

        ctk.CTkButton(
            btn_bar, text="Fermer",
            command=win.destroy,
            height=34, width=100,
            fg_color=C.CLOUDS, hover_color=C.SILVER,
            text_color=C.TEXT_PRIMARY,
            border_width=1, border_color=C.BORDER,
            font=_f(10), corner_radius=6
        ).pack(side="right")


# ── Test standalone ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        from app_theme import init_theme, Theme
        init_theme()
    except ImportError:
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.geometry("1420x800")
    app.title("Gestion des Péremptions — iJeery")
    app.grid_rowconfigure(0, weight=1)
    app.grid_columnconfigure(0, weight=1)

    try:
        Theme.apply(app)
    except Exception:
        pass

    PageGestionPeremption(app).grid(row=0, column=0, sticky="nsew")
    app.mainloop()