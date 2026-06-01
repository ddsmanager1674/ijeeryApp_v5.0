# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           iJeery V5.0 — page_rapportLogistique.py                          ║
║           Module LOGISTIQUE › Rapport & Tableau de Bord                     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Fonctionnalités :                                                           ║
║   • Tableau de bord consolidé de tout le module logistique                  ║
║   • KPI globaux : véhicules, carburant, pièces, missions, maintenance       ║
║   • Synthèse carburant par véhicule (consommation + coût)                   ║
║   • Synthèse maintenance par véhicule (fiches + coût total)                 ║
║   • Historique missions par statut et par mois                              ║
║   • Alertes stock pièces détachées                                          ║
║   • Filtrage par période (ce mois / 3 mois / 6 mois / année)               ║
║   • Connexion PostgreSQL via db_conn                                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

import customtkinter as ctk

try:
    from app_theme import Colors, Fonts
except ImportError:
    class Colors:
        BG_PAGE    = "#ECF0F1"; BG_CARD  = "#FFFFFF"; MIDNIGHT = "#2C3E50"
        TEXT_MUTED = "#95A5A6"; DIVIDER  = "#E8EAED"
    class Fonts: pass

def _F(size=11, weight="normal"):
    return ctk.CTkFont(family="Segoe UI", size=size, weight=weight)

# ── Couleurs ──────────────────────────────────────────────────────────────────
_C_LOG      = "#1A6B3C"
_C_LOG_H    = "#27AE60"
_C_HEADER   = "#2C3E50"
_C_BLUE     = "#3498DB"
_C_ORANGE   = "#E67E22"
_C_RED      = "#E74C3C"
_C_PURPLE   = "#8E44AD"
_C_ROW_ODD  = "#F7F9FC"
_C_ROW_EVEN = "#FFFFFF"

_PERIODES = ["Ce mois", "3 derniers mois", "6 derniers mois", "Cette année", "Tout"]


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _date_debut(periode: str) -> Optional[date]:
    today = date.today()
    if periode == "Ce mois":
        return today.replace(day=1)
    elif periode == "3 derniers mois":
        return (today - relativedelta(months=3)).replace(day=1)
    elif periode == "6 derniers mois":
        return (today - relativedelta(months=6)).replace(day=1)
    elif periode == "Cette année":
        return today.replace(month=1, day=1)
    return None  # Tout


def _kpi_card(parent, title: str, value: str, color: str,
              subtitle: str = "", col: int = 0) -> ctk.CTkLabel:
    """Crée une carte KPI et retourne le label de la valeur."""
    card = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD, corner_radius=12,
                        border_width=1, border_color=Colors.DIVIDER)
    card.grid(row=0, column=col, padx=5, sticky="ew")
    ctk.CTkLabel(card, text=title, font=_F(10),
                 text_color=Colors.TEXT_MUTED, anchor="w"
                 ).pack(padx=14, pady=(10, 1), anchor="w")
    lbl = ctk.CTkLabel(card, text=value, font=_F(22, "bold"),
                       text_color=color, anchor="w")
    lbl.pack(padx=14, pady=(0, 1), anchor="w")
    if subtitle:
        ctk.CTkLabel(card, text=subtitle, font=_F(9),
                     text_color=Colors.TEXT_MUTED, anchor="w"
                     ).pack(padx=14, pady=(0, 8), anchor="w")
    else:
        ctk.CTkFrame(card, height=8, fg_color="transparent").pack()
    return lbl


def _section_title(parent, text: str, color: str = _C_LOG):
    fr = ctk.CTkFrame(parent, fg_color="transparent")
    fr.pack(fill="x", padx=14, pady=(16, 4))
    ctk.CTkFrame(fr, width=4, height=18, fg_color=color, corner_radius=2
                 ).pack(side="left", padx=(0, 8))
    ctk.CTkLabel(fr, text=text, font=_F(12, "bold"),
                 text_color=color
                 ).pack(side="left")


def _mini_table(parent, columns: list, rows: list,
                col_widths: Optional[list] = None,
                style_name: str = "Rpt") -> ttk.Treeview:
    frame = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD,
                         corner_radius=8, border_width=1,
                         border_color=Colors.DIVIDER)
    frame.pack(fill="x", padx=14, pady=(0, 6))
    frame.grid_columnconfigure(0, weight=1)

    style = ttk.Style()
    style.configure(f"{style_name}.Treeview",
                    rowheight=25, font=("Segoe UI", 9),
                    background=_C_ROW_EVEN, borderwidth=0,
                    fieldbackground=_C_ROW_EVEN)
    style.configure(f"{style_name}.Treeview.Heading",
                    background=_C_HEADER, foreground="#FFFFFF",
                    font=("Segoe UI", 9, "bold"), relief="flat")
    style.map(f"{style_name}.Treeview",
              background=[("selected", _C_BLUE)],
              foreground=[("selected", "#FFFFFF")])

    tree = ttk.Treeview(frame, columns=columns, show="headings",
                         style=f"{style_name}.Treeview",
                         height=min(len(rows) + 1, 8))
    for i, col in enumerate(columns):
        tree.heading(col, text=col)
        w = (col_widths[i] if col_widths and i < len(col_widths) else 100)
        tree.column(col, width=w, anchor="center" if i > 0 else "w",
                    minwidth=40)

    for i, row in enumerate(rows):
        tag = "odd" if i % 2 else "even"
        tree.insert("", "end", values=row, tags=(tag,))
    tree.tag_configure("odd",  background=_C_ROW_ODD)
    tree.tag_configure("even", background=_C_ROW_EVEN)

    tree.pack(fill="x", padx=0)
    return tree


# ─────────────────────────────────────────────────────────────────────────────
# PAGE PRINCIPALE : RAPPORT LOGISTIQUE
# ─────────────────────────────────────────────────────────────────────────────

class PageRapportLogistique(ctk.CTkFrame):
    """
    Tableau de bord consolidé du module Logistique.
    Signature : PageRapportLogistique(master, db_conn, session_data)
    """

    def __init__(self, master, db_conn=None, session_data=None, **kw):
        super().__init__(master, fg_color=Colors.BG_PAGE, corner_radius=0, **kw)
        self.db_conn      = db_conn
        self.session_data = session_data or {}
        self._periode     = "Ce mois"

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_body()
        self._load_all()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=_C_HEADER, corner_radius=0, height=56)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(1, weight=1)
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="📊  Rapport Logistique",
                     font=_F(17, "bold"), text_color="#FFFFFF"
                     ).grid(row=0, column=0, padx=18, pady=14, sticky="w")
        ctk.CTkLabel(hdr, text="LOGISTIQUE  ›  Tableau de Bord",
                     font=_F(10), text_color="#95A5A6"
                     ).grid(row=0, column=1, padx=0, pady=14, sticky="w")

        # Filtre période
        pf = ctk.CTkFrame(hdr, fg_color="transparent")
        pf.grid(row=0, column=2, padx=10, pady=10, sticky="e")
        ctk.CTkLabel(pf, text="Période :", font=_F(10),
                     text_color="#BDC3C7"
                     ).pack(side="left", padx=(0, 6))
        self._periode_var = ctk.StringVar(value="Ce mois")
        ctk.CTkComboBox(pf, values=_PERIODES,
                        variable=self._periode_var,
                        command=self._on_periode_change,
                        font=_F(10), height=28, width=150, corner_radius=6,
                        ).pack(side="left")

        ctk.CTkButton(pf, text="🔄", fg_color="#455A64", hover_color="#546E7A",
                      font=_F(11), height=28, width=36, corner_radius=6,
                      command=self._load_all
                      ).pack(side="left", padx=(6, 0))

        ctk.CTkLabel(hdr, text=datetime.now().strftime("%d/%m/%Y %H:%M"),
                     font=_F(10), text_color="#BDC3C7"
                     ).grid(row=0, column=3, padx=18, pady=14, sticky="e")

    def _on_periode_change(self, _=None):
        self._periode = self._periode_var.get()
        self._load_all()

    # ── Body ─────────────────────────────────────────────────────────────────

    def _build_body(self):
        # Zone scrollable principale
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self._scroll.grid_columnconfigure(0, weight=1)

    # ── Chargement global ─────────────────────────────────────────────────────

    def _load_all(self):
        # Vider le scroll
        for widget in self._scroll.winfo_children():
            widget.destroy()

        d_debut = _date_debut(self._periode)

        if self.db_conn:
            self._build_from_db(d_debut)
        else:
            self._build_demo()

    # ── Données depuis DB ─────────────────────────────────────────────────────

    def _build_from_db(self, d_debut: Optional[date]):
        parent = self._scroll

        def safe(sql, params=()):
            try:
                cur = self.db_conn.cursor()
                cur.execute(sql, params)
                rows = cur.fetchall()
                cur.close()
                return rows
            except Exception as e:
                print(f"[RapportLogistique] {e}")
                return []

        date_cond = "AND date_trunc('day', created_at::date) >= %s" if d_debut else ""
        p = (d_debut,) if d_debut else ()

        # ── KPI GLOBAUX ───────────────────────────────────────────────────────
        _section_title(parent, "📌  Indicateurs Clés du Parc", _C_HEADER)
        kpi_row = ctk.CTkFrame(parent, fg_color="transparent")
        kpi_row.pack(fill="x", padx=14, pady=(0, 6))
        kpi_row.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        # Véhicules
        veh = safe("SELECT COUNT(*), SUM(CASE WHEN statut='Actif' THEN 1 ELSE 0 END) FROM logistique_vehicule")
        total_veh = veh[0][0] if veh else 0
        actifs_veh = veh[0][1] if veh else 0
        _kpi_card(kpi_row, "🚗  Véhicules",
                  str(total_veh), _C_BLUE,
                  f"{actifs_veh} actifs", col=0)

        # Carburant
        carb_sql = """
            SELECT COALESCE(SUM(litres),0), COALESCE(SUM(montant_total),0)
            FROM logistique_carburant
        """ + ("WHERE date_plein >= %s" if d_debut else "")
        carb = safe(carb_sql, p)
        litres_tot = float(carb[0][0]) if carb else 0
        cout_carb  = float(carb[0][1]) if carb else 0
        _kpi_card(kpi_row, "⛽  Carburant",
                  f"{litres_tot:,.0f} L".replace(",", " "),
                  _C_ORANGE,
                  f"Coût : {cout_carb:,.0f} Ar".replace(",", " "), col=1)

        # Pièces en alerte
        alerte = safe("""
            SELECT COUNT(*) FROM logistique_piece
            WHERE quantite <= seuil_alerte
        """)
        _kpi_card(kpi_row, "⚠️  Pièces en alerte",
                  str(alerte[0][0] if alerte else 0),
                  _C_RED, "stock ≤ seuil mini", col=2)

        # Missions
        miss_sql = """
            SELECT COUNT(*),
                   SUM(CASE WHEN statut='En cours' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN statut='Terminé' THEN 1 ELSE 0 END)
            FROM logistique_mission
        """ + ("WHERE date_depart::date >= %s" if d_debut else "")
        miss = safe(miss_sql, p)
        _kpi_card(kpi_row, "🗺️  Missions",
                  str(miss[0][0] if miss else 0),
                  _C_PURPLE,
                  f"{miss[0][1] or 0} en cours / {miss[0][2] or 0} terminées",
                  col=3)

        # Maintenance
        maint_sql = """
            SELECT COUNT(*),
                   COALESCE(SUM(COALESCE(cout, cout_estime)), 0)
            FROM logistique_maintenance
        """ + ("WHERE date_entree >= %s" if d_debut else "")
        maint = safe(maint_sql, p)
        _kpi_card(kpi_row, "🔧  Maintenances",
                  str(maint[0][0] if maint else 0),
                  _C_LOG,
                  f"Coût : {float(maint[0][1] if maint else 0):,.0f} Ar".replace(",", " "),
                  col=4)

        # ── CARBURANT PAR VÉHICULE ────────────────────────────────────────────
        _section_title(parent, "⛽  Consommation Carburant par Véhicule", _C_ORANGE)
        carb_veh_sql = """
            SELECT v.immatriculation, v.marque,
                   COUNT(c.id) AS nb_pleins,
                   COALESCE(SUM(c.litres), 0) AS total_litres,
                   COALESCE(SUM(c.montant_total), 0) AS total_cout,
                   COALESCE(AVG(c.prix_litre), 0) AS prix_moy
            FROM logistique_vehicule v
            LEFT JOIN logistique_carburant c ON c.vehicule_id = v.id
                {where}
            GROUP BY v.id, v.immatriculation, v.marque
            HAVING COUNT(c.id) > 0
            ORDER BY total_litres DESC
        """.format(where="AND c.date_plein >= %s" if d_debut else "")
        carb_veh = safe(carb_veh_sql, p)
        rows_cv = [
            (r[0], r[1], r[2],
             f"{float(r[3]):,.1f}".replace(",", " "),
             f"{float(r[4]):,.0f}".replace(",", " "),
             f"{float(r[5]):,.0f}".replace(",", " "))
            for r in carb_veh
        ]
        if rows_cv:
            _mini_table(parent,
                        ["Immatricul.", "Marque", "Nb Pleins",
                         "Total Litres", "Total Coût (Ar)", "Prix Moy/L (Ar)"],
                        rows_cv,
                        [100, 90, 80, 100, 130, 130],
                        style_name="CarbVeh")
        else:
            ctk.CTkLabel(parent, text="Aucune donnée carburant pour cette période.",
                         font=_F(10), text_color=Colors.TEXT_MUTED
                         ).pack(padx=18, pady=4, anchor="w")

        # ── MAINTENANCE PAR VÉHICULE ──────────────────────────────────────────
        _section_title(parent, "🔧  Historique Maintenance par Véhicule", _C_ORANGE)
        maint_veh_sql = """
            SELECT v.immatriculation, v.marque,
                   COUNT(m.id) AS nb_fiches,
                   SUM(CASE WHEN m.statut='En cours'   THEN 1 ELSE 0 END) AS en_cours,
                   SUM(CASE WHEN m.statut='Terminé'    THEN 1 ELSE 0 END) AS terminees,
                   COALESCE(SUM(COALESCE(m.cout, m.cout_estime)), 0) AS total_cout
            FROM logistique_vehicule v
            LEFT JOIN logistique_maintenance m ON m.vehicule_id = v.id
                {where}
            GROUP BY v.id, v.immatriculation, v.marque
            HAVING COUNT(m.id) > 0
            ORDER BY total_cout DESC
        """.format(where="AND m.date_entree >= %s" if d_debut else "")
        maint_veh = safe(maint_veh_sql, p)
        rows_mv = [
            (r[0], r[1], r[2], r[3], r[4],
             f"{float(r[5]):,.0f}".replace(",", " "))
            for r in maint_veh
        ]
        if rows_mv:
            _mini_table(parent,
                        ["Immatricul.", "Marque", "Nb Fiches",
                         "En cours", "Terminées", "Total Coût (Ar)"],
                        rows_mv,
                        [100, 90, 80, 80, 90, 130],
                        style_name="MaintVeh")
        else:
            ctk.CTkLabel(parent, text="Aucune fiche de maintenance pour cette période.",
                         font=_F(10), text_color=Colors.TEXT_MUTED
                         ).pack(padx=18, pady=4, anchor="w")

        # ── MISSIONS PAR STATUT ───────────────────────────────────────────────
        _section_title(parent, "🗺️  Missions — Synthèse par Statut", _C_PURPLE)
        miss_stat_sql = """
            SELECT statut,
                   COUNT(*) AS nb,
                   COALESCE(SUM(km_retour - km_depart)
                       FILTER (WHERE km_retour IS NOT NULL AND km_depart IS NOT NULL), 0) AS km_tot
            FROM logistique_mission
            {where}
            GROUP BY statut ORDER BY nb DESC
        """.format(where="WHERE date_depart::date >= %s" if d_debut else "")
        miss_stat = safe(miss_stat_sql, p)
        rows_ms = [
            (r[0], r[1],
             f"{float(r[2]):,.0f} km".replace(",", " ") if r[2] else "—")
            for r in miss_stat
        ]
        if rows_ms:
            _mini_table(parent,
                        ["Statut", "Nb Missions", "Km Parcourus"],
                        rows_ms, [150, 120, 150],
                        style_name="MissStat")
        else:
            ctk.CTkLabel(parent, text="Aucune mission pour cette période.",
                         font=_F(10), text_color=Colors.TEXT_MUTED
                         ).pack(padx=18, pady=4, anchor="w")

        # ── TOP DESTINATIONS ──────────────────────────────────────────────────
        _section_title(parent, "📍  Top Destinations des Missions", _C_PURPLE)
        dest_sql = """
            SELECT destination, COUNT(*) AS nb,
                   COALESCE(SUM(km_retour - km_depart)
                       FILTER (WHERE km_retour IS NOT NULL), 0) AS km_tot
            FROM logistique_mission
            {where}
            GROUP BY destination ORDER BY nb DESC LIMIT 8
        """.format(where="WHERE date_depart::date >= %s" if d_debut else "")
        dest = safe(dest_sql, p)
        rows_d = [
            (r[0], r[1],
             f"{float(r[2]):,.0f}".replace(",", " ") if r[2] else "—")
            for r in dest
        ]
        if rows_d:
            _mini_table(parent,
                        ["Destination", "Nb Missions", "Km Total"],
                        rows_d, [200, 100, 120],
                        style_name="TopDest")

        # ── PIÈCES EN ALERTE STOCK ────────────────────────────────────────────
        _section_title(parent, "⚠️  Pièces Détachées — Alertes Stock", _C_RED)
        alerte_pieces = safe("""
            SELECT reference, designation, categorie,
                   quantite, seuil_alerte,
                   CASE WHEN quantite = 0 THEN '⛔ Rupture'
                        ELSE '⚠️ Alerte' END AS etat
            FROM logistique_piece
            WHERE quantite <= seuil_alerte
            ORDER BY quantite ASC LIMIT 15
        """)
        rows_ap = [
            (r[0], r[1], r[2], r[3], r[4], r[5])
            for r in alerte_pieces
        ]
        if rows_ap:
            _mini_table(parent,
                        ["Référence", "Désignation", "Catégorie",
                         "Stock", "Seuil Mini", "État"],
                        rows_ap,
                        [90, 160, 90, 60, 80, 90],
                        style_name="AlertePiece")
        else:
            ctk.CTkLabel(parent,
                         text="✅  Aucune pièce en rupture ou en alerte de stock.",
                         font=_F(10), text_color=_C_LOG
                         ).pack(padx=18, pady=6, anchor="w")

        # ── BONS DE SORTIE PAR TYPE ───────────────────────────────────────────
        _section_title(parent, "📋  Bons de Sortie — Synthèse par Type", _C_BLUE)
        bons_sql = """
            SELECT type_bon, statut, COUNT(*) AS nb
            FROM logistique_bon_sortie
            {where}
            GROUP BY type_bon, statut
            ORDER BY type_bon, nb DESC
        """.format(where="WHERE date_bon >= %s" if d_debut else "")
        bons = safe(bons_sql, p)
        rows_b = [(r[0], r[1], r[2]) for r in bons]
        if rows_b:
            _mini_table(parent,
                        ["Type Bon", "Statut", "Nb Bons"],
                        rows_b, [160, 120, 80],
                        style_name="BonsStat")
        else:
            ctk.CTkLabel(parent, text="Aucun bon de sortie pour cette période.",
                         font=_F(10), text_color=Colors.TEXT_MUTED
                         ).pack(padx=18, pady=4, anchor="w")

        # ── PROCHAINES MAINTENANCES ───────────────────────────────────────────
        _section_title(parent, "🔔  Prochaines Maintenances Planifiées", _C_LOG)
        proch = safe("""
            SELECT v.immatriculation, v.marque, m.type_travaux,
                   m.prochain_km, v.kilometrage,
                   CASE WHEN v.kilometrage IS NOT NULL AND m.prochain_km IS NOT NULL
                        THEN m.prochain_km - v.kilometrage
                        ELSE NULL END AS km_restant
            FROM logistique_maintenance m
            JOIN logistique_vehicule v ON v.id = m.vehicule_id
            WHERE m.prochain_km IS NOT NULL AND m.statut = 'Terminé'
            ORDER BY km_restant ASC NULLS LAST
            LIMIT 8
        """)
        rows_p = []
        for r in proch:
            km_rest = r[5]
            if km_rest is not None:
                if float(km_rest) <= 500:
                    etat = "🔴 Urgent"
                elif float(km_rest) <= 2000:
                    etat = "🟡 Proche"
                else:
                    etat = "🟢 OK"
                km_rest_str = f"{float(km_rest):,.0f}".replace(",", " ")
            else:
                etat = "—"; km_rest_str = "—"
            rows_p.append((
                r[0], r[1], r[2],
                f"{float(r[3]):,.0f}".replace(",", " ") if r[3] else "—",
                f"{float(r[4]):,.0f}".replace(",", " ") if r[4] else "—",
                km_rest_str, etat
            ))
        if rows_p:
            _mini_table(parent,
                        ["Immatricul.", "Marque", "Type Travaux",
                         "Prochain km", "Km actuel", "Km restant", "État"],
                        rows_p,
                        [95, 80, 130, 90, 90, 90, 80],
                        style_name="ProchMaint")
        else:
            ctk.CTkLabel(parent,
                         text="Aucune échéance de maintenance renseignée.",
                         font=_F(10), text_color=Colors.TEXT_MUTED
                         ).pack(padx=18, pady=4, anchor="w")

        # Pied de page
        ctk.CTkLabel(parent,
                     text=f"Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}  "
                          f"—  iJeery Logistique V5.0",
                     font=_F(9), text_color=Colors.TEXT_MUTED
                     ).pack(padx=14, pady=(16, 10), anchor="e")

    # ── Mode démo (sans DB) ───────────────────────────────────────────────────

    def _build_demo(self):
        parent = self._scroll

        _section_title(parent, "📌  Indicateurs Clés (Mode Démo)", _C_HEADER)
        kpi_row = ctk.CTkFrame(parent, fg_color="transparent")
        kpi_row.pack(fill="x", padx=14, pady=(0, 6))
        kpi_row.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        _kpi_card(kpi_row, "🚗  Véhicules",   "28",      _C_BLUE,   "24 actifs", col=0)
        _kpi_card(kpi_row, "⛽  Carburant",   "3 840 L", _C_ORANGE, "Coût : 19 968 000 Ar", col=1)
        _kpi_card(kpi_row, "⚠️  Alertes pièces", "4",   _C_RED,    "stock ≤ seuil mini", col=2)
        _kpi_card(kpi_row, "🗺️  Missions",    "9",       _C_PURPLE, "3 en cours / 6 terminées", col=3)
        _kpi_card(kpi_row, "🔧  Maintenances","5",        _C_LOG,   "Coût : 850 000 Ar", col=4)

        _section_title(parent, "⛽  Consommation Carburant par Véhicule (Démo)", _C_ORANGE)
        _mini_table(parent,
            ["Immatricul.", "Marque", "Nb Pleins", "Total Litres", "Total Coût (Ar)", "Prix Moy/L (Ar)"],
            [
                ("ABC-1234", "Toyota",     "3", "180", "936 000", "5 200"),
                ("GHI-9012", "Ford",       "2", "110", "572 000", "5 200"),
                ("DEF-5678", "Mitsubishi", "2",  "90", "468 000", "5 200"),
                ("MNO-7890", "Peugeot",    "1",  "45", "234 000", "5 200"),
            ],
            [100, 90, 80, 100, 130, 130], "CarbVehD")

        _section_title(parent, "🔧  Maintenance par Véhicule (Démo)", _C_ORANGE)
        _mini_table(parent,
            ["Immatricul.", "Marque", "Nb Fiches", "En cours", "Terminées", "Total Coût (Ar)"],
            [
                ("DEF-5678", "Mitsubishi", "2", "1", "1", "625 000"),
                ("ABC-1234", "Toyota",     "1", "0", "1", "175 000"),
                ("GHI-9012", "Ford",       "1", "0", "0",  "85 000"),
            ],
            [100, 90, 80, 80, 90, 130], "MaintVehD")

        _section_title(parent, "🗺️  Missions par Statut (Démo)", _C_PURPLE)
        _mini_table(parent,
            ["Statut", "Nb Missions", "Km Parcourus"],
            [("Planifié", "3", "—"), ("En cours", "3", "—"), ("Terminé", "3", "1 110 km")],
            [150, 120, 150], "MissStatD")

        _section_title(parent, "⚠️  Pièces en Alerte Stock (Démo)", _C_RED)
        _mini_table(parent,
            ["Référence", "Désignation", "Catégorie", "Stock", "Seuil Mini", "État"],
            [
                ("PLQ-002", "Plaquettes de frein avant",  "Freinage",   "2", "4", "⚠️ Alerte"),
                ("BAT-003", "Batterie 12V 70Ah",          "Électrique", "1", "2", "⚠️ Alerte"),
                ("CNR-005", "Courroie de distribution",   "Moteur",     "0", "1", "⛔ Rupture"),
            ],
            [90, 180, 90, 60, 80, 90], "AlertePieceD")

        ctk.CTkLabel(parent,
                     text=f"Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}  "
                          f"—  iJeery Logistique V5.0  (Mode Démo — sans connexion DB)",
                     font=_F(9), text_color=Colors.TEXT_MUTED
                     ).pack(padx=14, pady=(16, 10), anchor="e")


# ─────────────────────────────────────────────────────────────────────────────
# TEST STANDALONE
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    root.title("iJeery V5.0 — Test Rapport Logistique")
    root.geometry("1280x800")
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    PageRapportLogistique(master=root, db_conn=None).grid(row=0, column=0, sticky="nsew")
    root.mainloop()
