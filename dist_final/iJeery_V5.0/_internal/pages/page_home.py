# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    iJeery — page_home.py  (Dashboard v2)                   ║
║   Tableau de bord professionnel — données caisse + KPIs métier             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import customtkinter as ctk
import psycopg2
from tkinter import messagebox
from datetime import date, datetime
import json
import os
import sys

from resource_utils import get_config_path

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir  = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from app_theme import Colors, Fonts, styled, Theme
    _T = True
except ImportError:
    _T = False

# ─────────────────────────────────────────────────────────────────────────────
# PALETTE LOCALE (fallback si app_theme absent)
# ─────────────────────────────────────────────────────────────────────────────
class _C:
    BG_PAGE        = "#ECF0F1"
    BG_CARD        = "#FFFFFF"
    BG_HEADER      = "#2C3E50"
    BG_INPUT       = "#F4F6F8"
    PRIMARY        = "#3498DB"
    PRIMARY_HOVER  = "#2980B9"
    SUCCESS        = "#2ECC71"
    SUCCESS_DARK   = "#27AE60"
    SUCCESS_LIGHT  = "#D5F5E3"
    DANGER         = "#E74C3C"
    DANGER_DARK    = "#C0392B"
    DANGER_LIGHT   = "#FADBD8"
    WARNING        = "#F39C12"
    WARNING_LIGHT  = "#FEF9E7"
    INFO           = "#1ABC9C"
    INFO_DARK      = "#16A085"
    INFO_LIGHT     = "#D1F2EB"
    PREMIUM        = "#9B59B6"
    PREMIUM_DARK   = "#8E44AD"
    PREMIUM_LIGHT  = "#F5EEF8"
    TEXT_PRIMARY   = "#2C3E50"
    TEXT_SECONDARY = "#5D6D7E"
    TEXT_MUTED     = "#95A5A6"
    BORDER         = "#D5D8DC"
    DIVIDER        = "#E8EAED"

C = Colors if _T else _C


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE MANAGER
# ─────────────────────────────────────────────────────────────────────────────
class DatabaseManager:
    def __init__(self):
        self.db_params = self._load_db_config()

    def _load_db_config(self):
        try:
            config_path = get_config_path('config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)['database']
        except Exception as e:
            print(f"Erreur config: {e}")
            return None

    def get_connection(self):
        if not self.db_params:
            return None
        try:
            conn = psycopg2.connect(
                host=self.db_params['host'],
                user=self.db_params['user'],
                password=self.db_params['password'],
                database=self.db_params['database'],
                port=self.db_params['port'],
                client_encoding='UTF8'
            )
            return conn
        except psycopg2.OperationalError as e:
            print(f"Erreur connexion: {e}")
            return None


def _get_conn():
    return DatabaseManager().get_connection()


def _fmt(v):
    """Formate un montant numérique → '1 250 000 Ar'."""
    try:
        return f"{float(v):,.0f} Ar".replace(",", " ")
    except Exception:
        return "0 Ar"


# ─────────────────────────────────────────────────────────────────────────────
# REQUÊTES — DONNÉES KPI
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_one(query, params=None, default=0):
    conn = _get_conn()
    if not conn:
        return default
    try:
        cur = conn.cursor()
        cur.execute(query, params or [])
        row = cur.fetchone()
        return row[0] if row and row[0] is not None else default
    except Exception as e:
        print(f"Erreur SQL: {e}")
        return default
    finally:
        conn.close()


def _fetch_all(query, params=None):
    conn = _get_conn()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute(query, params or [])
        return cur.fetchall()
    except Exception as e:
        print(f"Erreur SQL: {e}")
        return []
    finally:
        conn.close()


def get_solde_caisse():
    today = date.today().strftime('%Y-%m-%d')
    v = _fetch_one("""
        SELECT COALESCE(SUM(CASE WHEN t1.idtypeoperation=1 THEN t1.mtpaye ELSE -t1.mtpaye END), 0)
        FROM (
            SELECT idmode, mtpaye, idtypeoperation FROM tb_pmtfacture WHERE datepmt::date=%s AND id_banque IS NULL
            UNION ALL
            SELECT idmode, mtpaye, idtypeoperation FROM tb_pmtcom WHERE datepmt::date=%s AND id_banque IS NULL
            UNION ALL
            SELECT idmode, mtpaye, idtypeoperation FROM tb_encaissement WHERE datepmt::date=%s AND id_banque IS NULL
            UNION ALL
            SELECT idmode, mtpaye, idtypeoperation FROM tb_decaissement WHERE datepmt::date=%s AND id_banque IS NULL
            UNION ALL
            SELECT idmode, mtpaye, idtypeoperation FROM tb_avancepers WHERE datepmt::date=%s AND id_banque IS NULL
            UNION ALL
            SELECT idmode, mtpaye, idtypeoperation FROM tb_avancespecpers WHERE datepmt::date=%s AND id_banque IS NULL
            UNION ALL
            SELECT idmode, mtpaye, idtypeoperation FROM tb_pmtsalaire WHERE datepmt::date=%s AND id_banque IS NULL
            UNION ALL
            SELECT idmode, mtpaye, idtypeoperation FROM tb_pmtavoir WHERE datepmt::date=%s AND id_banque IS NULL
            UNION ALL
            SELECT idmode, mtpaye, idtypeoperation FROM tb_pmtcredit WHERE datepmt::date=%s AND id_banque IS NULL
        ) t1
        LEFT JOIN tb_modepaiement t2 ON t1.idmode = t2.idmode
        WHERE COALESCE(t2.modedepaiement, 'Inconnu') IN ('Espèces', 'Espece')
    """, [today] * 9)
    return _fmt(v)


def get_total_client_jour():
    today = date.today()
    v = _fetch_one("""
        SELECT COALESCE(SUM(CASE WHEN idtypeoperation=1 THEN mtpaye ELSE -mtpaye END),0)
        FROM (
            SELECT idtypeoperation,mtpaye FROM tb_pmtfacture
            WHERE datepmt::date=%s AND id_banque IS NULL
            UNION ALL
            SELECT idtypeoperation,mtpaye FROM tb_pmtcredit
            WHERE datepmt::date=%s AND id_banque IS NULL
        ) t
    """, [today, today])
    return _fmt(v)


def get_nb_factures_vente_jour():
    """Nombre de factures de vente validées du jour."""
    v = _fetch_one(
        "SELECT COUNT(*) FROM tb_vente WHERE DATE(dateregistre)=CURRENT_DATE AND statut='VALIDEE'")
    return f"{int(v)} facture{'s' if int(v) > 1 else ''}"


def get_encaissement_jour():
    v = _fetch_one("""
        SELECT COALESCE(SUM(mtpaye),0) FROM tb_encaissement
        WHERE DATE(datepmt)=CURRENT_DATE AND idtypeoperation=1
    """)
    return _fmt(v)


def get_decaissement_jour():
    v = _fetch_one("""
        SELECT COALESCE(SUM(mtpaye),0) FROM tb_decaissement
        WHERE DATE(datepmt)=CURRENT_DATE AND idtypeoperation=2
    """)
    return _fmt(v)


def get_credit_total():
    v = _fetch_one("""
        SELECT COALESCE(SUM(tv.totmtvente), 0) AS credit_donne_jour
        FROM tb_vente tv
        JOIN tb_modepaiement mp ON tv.idmode = mp.idmode
        WHERE mp.modedepaiement IN ('Crédit', 'Credit')
          AND DATE(tv.dateregistre) = CURRENT_DATE
          AND tv.statut = 'VALIDEE'
    """)
    return _fmt(v)


def get_credit_general():
    v = _fetch_one("""
        SELECT
            COALESCE(vc.total_credit_ventes, 0)
            + COALESCE(ac.total_autres_creances, 0)
            - COALESCE(pc.total_paye_credit, 0) AS credit_restant_global
        FROM
            (
                SELECT COALESCE(SUM(tv.totmtvente), 0) AS total_credit_ventes
                FROM tb_vente tv
                JOIN tb_modepaiement mp ON tv.idmode = mp.idmode
                WHERE mp.modedepaiement IN ('Crédit', 'Credit')
                  AND tv.statut = 'VALIDEE'
            ) vc
            CROSS JOIN
            (
                SELECT COALESCE(SUM(montant), 0) AS total_autres_creances
                FROM tb_autrecreance
            ) ac
            CROSS JOIN
            (
                SELECT COALESCE(SUM(mtpaye), 0) AS total_paye_credit
                FROM tb_pmtcredit
            ) pc
    """)
    return _fmt(v)


def get_dette_fournisseur():
    v = _fetch_one("""
        SELECT
            COALESCE(dl.total_dette_livraisons, 0)
            + COALESCE(ad.total_autres_dettes, 0)
            - COALESCE(pc.total_paye_frs, 0) AS dette_fournisseur_restante
        FROM
            (
                SELECT COALESCE(SUM(cd.qtlivre * cd.punitcmd), 0) AS total_dette_livraisons
                FROM (
                    SELECT idcom
                    FROM tb_livraisonfrs
                    WHERE a_payer = 1
                ) l
                JOIN tb_commandedetail cd ON cd.idcom = l.idcom
            ) dl
            CROSS JOIN
            (
                SELECT COALESCE(SUM(montant), 0) AS total_autres_dettes
                FROM tb_autredette
            ) ad
            CROSS JOIN
            (
                SELECT COALESCE(SUM(mtpaye), 0) AS total_paye_frs
                FROM tb_pmtcom
            ) pc
    """)
    return _fmt(v)


def get_appro_jour():
    v = _fetch_one(
        "SELECT COUNT(DISTINCT reflivfrs) FROM tb_livraisonfrs WHERE DATE(dateregistre)=CURRENT_DATE")
    return f"{int(v)} BR"


def get_absences_jour():
    today = date.today().strftime('%Y-%m-%d')
    v = _fetch_one("SELECT COUNT(*) FROM tb_absence WHERE date=%s", [today])
    return int(v)


# ── Données Caisse : ventilation par type & mode (période = aujourd'hui) ─────

def get_ventilation_types_jour():
    """
    Retourne un dict {type_doc: montant_net} pour la journée du jour.
    Utilisé pour les mini-barres de progression de la caisse.
    """
    today = date.today().strftime('%Y-%m-%d')
    result = {}
    queries = [
        ("Client",        "SELECT COALESCE(SUM(CASE WHEN idtypeoperation=1 THEN mtpaye ELSE -mtpaye END),0) FROM tb_pmtfacture  WHERE datepmt::date=%s AND id_banque IS NULL"),
        ("Crédit client", "SELECT COALESCE(SUM(tv.totmtvente), 0) FROM tb_vente tv JOIN tb_modepaiement mp ON tv.idmode = mp.idmode WHERE mp.modedepaiement IN ('Crédit', 'Credit') AND DATE(tv.dateregistre) = %s AND tv.statut = 'VALIDEE'"),
        ("Avoir",         "SELECT COALESCE(SUM(CASE WHEN idtypeoperation=1 THEN mtpaye ELSE -mtpaye END),0) FROM tb_pmtavoir    WHERE datepmt::date=%s AND id_banque IS NULL"),
        ("Fournisseur",   "SELECT COALESCE(SUM(cd.qtlivre * cd.punitcmd), 0) AS total_dette_livraisons FROM (SELECT idcom FROM tb_livraisonfrs WHERE a_payer = 1 AND DATE(dateregistre) = %s) l JOIN tb_commandedetail cd ON cd.idcom = l.idcom"),
        ("Encaissement",  "SELECT COALESCE(SUM(CASE WHEN idtypeoperation=1 THEN mtpaye ELSE -mtpaye END),0) FROM tb_encaissement WHERE datepmt::date=%s AND id_banque IS NULL"),
        ("Dépenses",      "SELECT COALESCE(SUM(CASE WHEN idtypeoperation=1 THEN mtpaye ELSE -mtpaye END),0) FROM tb_decaissement WHERE datepmt::date=%s AND id_banque IS NULL"),
    ]
    for label, q in queries:
        result[label] = float(_fetch_one(q, [today]))
    return result





# ─────────────────────────────────────────────────────────────────────────────
# WIDGETS PERSONNALISÉS
# ─────────────────────────────────────────────────────────────────────────────

def _f(size=10, weight="normal"):
    return ctk.CTkFont(
        family="Roboto" if _T else "Segoe UI",
        size=size, weight=weight)


class KpiCard(ctk.CTkFrame):
    """
    Carte KPI professionnelle :
      ┌──────────────────────────────────────────┐
      │ [icône]  TITRE                           │
      │          Valeur principale (grande)      │
      │          Sous-label optionnel            │
      │  ████░░░░  barre de tendance (optionnel) │
      └──────────────────────────────────────────┘
    """

    def __init__(self, master, title, value, icon="📊",
                 accent="#3498DB", sublabel="", trend=None, **kwargs):
        super().__init__(master,
                         fg_color=C.BG_CARD,
                         corner_radius=10,
                         border_width=1,
                         border_color=C.BORDER,
                         **kwargs)

        accent   = str(accent)
        title    = str(title)
        value    = str(value)
        sublabel = str(sublabel)

        def _light(hex_c, f=0.88):
            hc = hex_c.lstrip("#")
            if len(hc) != 6:
                return "#EEF3F9"
            r, g, b = int(hc[:2],16), int(hc[2:4],16), int(hc[4:],16)
            return f"#{int(r+(255-r)*f):02X}{int(g+(255-g)*f):02X}{int(b+(255-b)*f):02X}"

        # Bande colorée en haut
        bar = ctk.CTkFrame(self, height=4, fg_color=accent, corner_radius=0)
        bar.pack(fill="x", side="top")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=(10, 12))

        # Ligne icône + titre
        top_row = ctk.CTkFrame(body, fg_color="transparent")
        top_row.pack(fill="x")

        icon_bg = ctk.CTkFrame(top_row, width=36, height=36,
                               fg_color=_light(accent), corner_radius=8)
        icon_bg.pack(side="left", padx=(0, 10))
        icon_bg.pack_propagate(False)
        ctk.CTkLabel(icon_bg, text=icon, font=_f(16)).pack(
            expand=True, anchor="center")

        ctk.CTkLabel(top_row, text=title.upper(),
                     font=_f(9, "bold"),
                     text_color=C.TEXT_MUTED,
                     anchor="w").pack(side="left", fill="x", expand=True)

        # Valeur
        ctk.CTkLabel(body, text=value,
                     font=_f(20, "bold"),
                     text_color=accent,
                     anchor="w").pack(fill="x", pady=(8, 0))

        # Sous-label
        if sublabel:
            ctk.CTkLabel(body, text=sublabel,
                         font=_f(9),
                         text_color=C.TEXT_MUTED,
                         anchor="w").pack(fill="x")

        # Barre de tendance (0–100)
        if trend is not None:
            pct = max(0, min(100, float(trend)))
            bar_bg = ctk.CTkFrame(body, height=4, fg_color=C.DIVIDER,
                                  corner_radius=2)
            bar_bg.pack(fill="x", pady=(8, 0))
            if pct > 0:
                bar_fill = ctk.CTkFrame(bar_bg, height=4,
                                        fg_color=accent, corner_radius=2)
                bar_fill.place(relx=0, rely=0, relwidth=pct/100, relheight=1)


class SectionHeader(ctk.CTkFrame):
    """Séparateur de section avec titre et ligne."""

    def __init__(self, master, title, icon="", **kwargs):
        super().__init__(master, fg_color="transparent", height=32, **kwargs)
        self.pack_propagate(False)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=4)
        ctk.CTkLabel(row,
                     text=f"{icon}  {title}" if icon else title,
                     font=_f(12, "bold"),
                     text_color=C.TEXT_PRIMARY,
                     anchor="w").pack(side="left")
        ctk.CTkFrame(row, height=1, fg_color=C.DIVIDER).pack(
            side="left", fill="x", expand=True, padx=(10, 0), pady=10)


class MiniBar(ctk.CTkFrame):
    """Ligne de ventilation : libellé + barre de progression + montant."""

    def __init__(self, master, label, value, max_val, color, **kwargs):
        super().__init__(master, fg_color="transparent", height=28, **kwargs)
        self.pack_propagate(False)

        pct  = (abs(value) / abs(max_val) * 100) if max_val else 0
        pct  = max(0, min(100, pct))
        sign = "+" if value >= 0 else "-"
        sign_color = C.SUCCESS_DARK if value >= 0 else C.DANGER

        ctk.CTkLabel(self, text=label,
                     font=_f(9), text_color=C.TEXT_SECONDARY,
                     width=100, anchor="w").pack(side="left", padx=(0, 6))

        bg = ctk.CTkFrame(self, height=6, fg_color=C.DIVIDER, corner_radius=3)
        bg.pack(side="left", fill="x", expand=True, pady=11)
        if pct > 0:
            fill = ctk.CTkFrame(bg, height=6, fg_color=color, corner_radius=3)
            fill.place(relx=0, rely=0, relwidth=pct/100, relheight=1)

        ctk.CTkLabel(self,
                     text=f"{sign}{_fmt(abs(value))}",
                     font=_f(9, "bold"),
                     text_color=sign_color,
                     width=110, anchor="e").pack(side="left", padx=(6, 0))


# ─────────────────────────────────────────────────────────────────────────────
# PAGE HOME — CLASSE
# ─────────────────────────────────────────────────────────────────────────────

class PageHome(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master, fg_color=C.BG_PAGE)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_body()

    # ── En-tête fixe (style PageMagasin) ─────────────────────────────────────
    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=C.BG_HEADER, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")

        ctk.CTkLabel(
            hdr, text="Tableau de Bord",
            font=_f(18, "bold"), text_color="#FFFFFF"
        ).pack(side="left", padx=16, pady=10)

        now_str = datetime.now().strftime("%d/%m/%Y  %H:%M")
        ctk.CTkLabel(
            hdr, text=now_str,
            font=_f(10), text_color="#BDC3C7"
        ).pack(side="right", padx=16)

    # ── Corps scrollable ──────────────────────────────────────────────────────
    def _build_body(self):
        outer = ctk.CTkScrollableFrame(
            self, fg_color=C.BG_PAGE,
            scrollbar_button_color=C.BORDER,
            scrollbar_button_hover_color=C.PRIMARY)
        outer.grid(row=1, column=0, sticky="nsew")
        outer.grid_columnconfigure(0, weight=1)

        # ── Chargement des données ────────────────────────────────────────────
        try:
            solde_especes     = get_solde_caisse()
            total_client      = get_total_client_jour()
            nb_factures       = get_nb_factures_vente_jour()
            encaissement_jour = get_encaissement_jour()
            decaissement_jour = get_decaissement_jour()
            credit_total      = get_credit_general()
            dette_fournisseur = get_dette_fournisseur()
            appro             = get_appro_jour()
            absences          = get_absences_jour()
            ventilation       = get_ventilation_types_jour()
        except Exception as e:
            print(f"Erreur chargement dashboard: {e}")
            solde_especes = total_client = "0 Ar"
            nb_factures = "0 facture"
            encaissement_jour = decaissement_jour = "0 Ar"
            credit_total = dette_fournisseur = "0 Ar"
            appro = "0 BR"; absences = 0; ventilation = {}

        # ═════════════════════════════════════════════════════════════════════
        # SECTION 1 — CAISSE EN TEMPS RÉEL
        # ═════════════════════════════════════════════════════════════════════
        SectionHeader(outer, "Caisse en temps réel", "🏦").pack(
            fill="x", padx=14, pady=(10, 2))

        caisse_row = ctk.CTkFrame(outer, fg_color="transparent")
        caisse_row.pack(fill="x", padx=14, pady=(8, 14))
        caisse_row.grid_columnconfigure(0, weight=2)
        caisse_row.grid_columnconfigure(1, weight=3)

        # Grande carte Solde en Espèces
        solde_card = ctk.CTkFrame(caisse_row, fg_color="#E2E8EC",
                                   corner_radius=10)
        solde_card.grid(row=0, column=0, sticky="nsew", padx=(0, 7))

        ctk.CTkLabel(solde_card, text="💰  SOLDE EN ESPÈCES",
                     font=_f(13, "bold"), text_color="#34495E").pack(
            pady=(14, 2), padx=14, anchor="w")
        ctk.CTkLabel(solde_card, text=solde_especes,
                     font=_f(25, "bold"), text_color="#34495E").pack(
            pady=(0, 6), padx=14, anchor="w")

        enc_dec = ctk.CTkFrame(solde_card, fg_color="transparent")
        enc_dec.pack(fill="x", padx=14, pady=(8, 22))

        def _mini_stat(parent, icon, label, val, color):
            f = ctk.CTkFrame(parent, fg_color="#D8DDE2", corner_radius=7)
            f.pack(side="left", fill="x", expand=True, padx=(0, 5))
            ctk.CTkLabel(f, text=f"{icon} {label}", font=_f(11),
                         text_color="#34495E").pack(pady=(5, 0))
            ctk.CTkLabel(f, text=val, font=_f(21, "bold"),
                         text_color=color).pack(pady=(0, 5))

        _mini_stat(enc_dec, "⬆", "Enc. du jour", encaissement_jour, "#2ECC71")
        _mini_stat(enc_dec, "⬇", "Déc. du jour", decaissement_jour, "#E74C3C")

        # Panneau ventilation types
        vent_card = ctk.CTkFrame(caisse_row, fg_color=C.BG_CARD,
                                  corner_radius=10, border_width=1,
                                  border_color=C.BORDER)
        vent_card.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(vent_card, text="Ventilation par type — Aujourd'hui",
                     font=_f(9, "bold"), text_color=C.TEXT_SECONDARY,
                     anchor="w").pack(padx=14, pady=(10, 4), fill="x")

        ctk.CTkFrame(vent_card, height=1, fg_color=C.DIVIDER).pack(
            fill="x", padx=10)

        vent_body = ctk.CTkFrame(vent_card, fg_color="transparent")
        vent_body.pack(fill="both", expand=True, padx=10, pady=6)

        colors_map = {
            "Client":        "#7CB342",
            "Crédit client": "#039BE5",
            "Avoir":         "#F9A825",
            "Fournisseur":   "#1E88E5",
            "Encaissement":  "#43A047",
            "Dépenses":      "#E53935",
        }
        max_v = max((abs(v) for v in ventilation.values()), default=1) or 1
        for label, val in ventilation.items():
            MiniBar(vent_body, label, val, max_v,
                    colors_map.get(label, C.PRIMARY)).pack(
                fill="x", pady=1)

        # ═════════════════════════════════════════════════════════════════════
        # SECTION 2 — KPIs JOURNALIERS (3 colonnes)
        # ═════════════════════════════════════════════════════════════════════
        SectionHeader(outer, "Activité du jour", "📋").pack(
            fill="x", padx=14, pady=(6, 2))

        kpi_frame = ctk.CTkFrame(outer, fg_color="transparent")
        kpi_frame.pack(fill="x", padx=14, pady=(0, 6))
        for c in range(3):
            kpi_frame.grid_columnconfigure(c, weight=1, uniform="kpi")

        kpi_jour = [
            ("Recettes Client",    total_client,  "🧾", C.INFO_DARK,  "Paiements factures & crédits"),
            ("Factures du Jour",   nb_factures,   "🛒", C.PRIMARY,    "Ventes validées aujourd'hui"),
            ("Approvisionnements", appro,         "📦", "#C2410C",    "Bons de Réception enregistrés"),
        ]
        for col, (title, val, icon, acc, sub) in enumerate(kpi_jour):
            KpiCard(kpi_frame, title, val, icon=icon, accent=acc,
                    sublabel=sub).grid(
                row=0, column=col, sticky="nsew", padx=5, pady=3)

        # ═════════════════════════════════════════════════════════════════════
        # SECTION 3 — SOLDES & ENGAGEMENTS
        # ═════════════════════════════════════════════════════════════════════
        SectionHeader(outer, "Soldes & Engagements", "📌").pack(
            fill="x", padx=14, pady=(6, 2))

        sol_frame = ctk.CTkFrame(outer, fg_color="transparent")
        sol_frame.pack(fill="x", padx=14, pady=(0, 6))
        for c in range(3):
            sol_frame.grid_columnconfigure(c, weight=1, uniform="sol")

        soldes = [
            ("Crédit Clients",       credit_total,     "💳", C.PREMIUM,     "Solde total à recouvrer",  60),
            ("Dettes Fournisseurs",  dette_fournisseur,"📌", C.DANGER,      "Livraisons non réglées",   75),
            ("Solde en Espèces",     solde_especes,    "🏛", C.SUCCESS_DARK,"Cumul toutes opérations",  None),
        ]
        for col, (title, val, icon, acc, sub, trend) in enumerate(soldes):
            KpiCard(sol_frame, title, val, icon=icon, accent=acc,
                    sublabel=sub, trend=trend).grid(
                row=0, column=col, sticky="nsew", padx=5, pady=3)

        # Espacement de fin
        ctk.CTkFrame(outer, height=10, fg_color="transparent").pack()


# ─────────────────────────────────────────────────────────────────────────────
# Fonctions de compatibilité (signature attendue par page_menu)
# ─────────────────────────────────────────────────────────────────────────────

def page_home(master, **kwargs):
    frame = PageHome(master)
    frame.pack(fill="both", expand=True)
    return frame


def page_home_alt(master, db_conn=None, session_data=None):
    return page_home(master)


# ─────────────────────────────────────────────────────────────────────────────
# Test standalone
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    root.title("iJeery — Dashboard")
    root.geometry("1280x780")
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    PageHome(root).grid(row=0, column=0, sticky="nsew")
    root.mainloop()
