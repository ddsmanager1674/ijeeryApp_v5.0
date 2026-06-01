# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           iJeery V5.0 — page_itineraires.py                                ║
║           Module LOGISTIQUE › Itinéraires / Missions                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Fonctionnalités :                                                           ║
║   • Création et suivi des missions / trajets                                ║
║   • Affectation véhicule + chauffeur par mission                            ║
║   • Statuts : Planifié → En cours → Terminé → Annulé                       ║
║   • Calcul automatique distance parcourue (km retour - km départ)           ║
║   • KPI : missions du mois, en cours, km parcourus, missions terminées      ║
║   • Feuille de route détaillée par mission                                  ║
║   • Connexion PostgreSQL via db_conn                                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional
from datetime import datetime, date

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
_C_PLANIFIE = "#3498DB"
_C_EN_COURS = "#E67E22"
_C_TERMINE  = "#27AE60"
_C_ANNULE   = "#95A5A6"
_C_ROW_ODD  = "#F7F9FC"
_C_ROW_EVEN = "#FFFFFF"

_STATUTS = ["Planifié", "En cours", "Terminé", "Annulé"]
_STATUT_COLORS = {
    "Planifié": _C_PLANIFIE,
    "En cours": _C_EN_COURS,
    "Terminé":  _C_TERMINE,
    "Annulé":   _C_ANNULE,
}


# ─────────────────────────────────────────────────────────────────────────────
# FORMULAIRE MISSION
# ─────────────────────────────────────────────────────────────────────────────

class FormMission(ctk.CTkToplevel):
    """Créer ou modifier une mission / itinéraire."""

    def __init__(self, master, db_conn,
                 mission: Optional[dict] = None,
                 vehicules: Optional[list] = None,
                 on_save: Optional[callable] = None):
        super().__init__(master)
        self.db_conn   = db_conn
        self.mission   = mission
        self.vehicules = vehicules or []
        self.on_save   = on_save
        self._mode     = "Modifier" if mission else "Nouvelle Mission"

        self.title(f"🗺️  {self._mode} — iJeery Logistique")
        self.geometry("530x720")
        self.resizable(False, False)
        self.grab_set()
        self.focus_force()
        self._build()
        if mission:
            self._populate(mission)

    def _build(self):
        ctk.CTkLabel(self, text=f"🗺️  {self._mode}",
                     font=_F(15, "bold"), text_color=_C_PLANIFIE
                     ).pack(pady=(16, 2), padx=22, anchor="w")
        ctk.CTkLabel(self, text="Définissez les paramètres de la mission.",
                     font=_F(10), text_color=Colors.TEXT_MUTED
                     ).pack(padx=22, anchor="w")
        ctk.CTkFrame(self, height=1, fg_color=Colors.DIVIDER
                     ).pack(fill="x", padx=22, pady=(8, 10))

        sc = ctk.CTkScrollableFrame(self, fg_color="transparent")
        sc.pack(fill="both", expand=True, padx=14)

        self._vars = {}

        # ── Véhicule ──────────────────────────────────────────────────────────
        ctk.CTkLabel(sc, text="Véhicule *", font=_F(10, "bold"),
                     text_color=Colors.MIDNIGHT, anchor="w"
                     ).pack(fill="x", padx=6, pady=(7, 1))
        veh_vals = [f"{v['immatriculation']} — {v['marque']} {v.get('modele','')}"
                    for v in self.vehicules] or ["— Aucun véhicule —"]
        self._veh_var = ctk.StringVar(value=veh_vals[0])
        ctk.CTkComboBox(sc, values=veh_vals, variable=self._veh_var,
                        font=_F(11), height=32
                        ).pack(fill="x", padx=6)

        fields = [
            ("Chauffeur *",          "chauffeur",     "entry",   None),
            ("Lieu de départ *",     "depart",        "entry",   None),
            ("Destination *",        "destination",   "entry",   None),
            ("Objet de la mission",  "objet",         "entry",   None),
            ("Date départ (JJ/MM/AAAA HH:MM)", "date_depart",  "entry", None),
            ("Date retour prévue",   "date_retour",   "entry",   None),
            ("Km au départ",         "km_depart",     "entry",   None),
            ("Km au retour",         "km_retour",     "entry",   None),
            ("Statut",               "statut",        "combo",   _STATUTS),
            ("Passagers / Chargement","passagers",    "entry",   None),
            ("Notes / Remarques",    "notes",         "textbox", None),
        ]

        for label, key, wtype, opts in fields:
            ctk.CTkLabel(sc, text=label, font=_F(10, "bold"),
                         text_color=Colors.MIDNIGHT, anchor="w"
                         ).pack(fill="x", padx=6, pady=(7, 1))
            if wtype == "entry":
                var = ctk.StringVar()
                ctk.CTkEntry(sc, textvariable=var, font=_F(11), height=32,
                             placeholder_text=label.replace(" *", "")
                             ).pack(fill="x", padx=6)
                self._vars[key] = var
            elif wtype == "combo":
                var = ctk.StringVar(value=opts[0])
                ctk.CTkComboBox(sc, values=opts, variable=var,
                                font=_F(11), height=32
                                ).pack(fill="x", padx=6)
                self._vars[key] = var
            elif wtype == "textbox":
                tb = ctk.CTkTextbox(sc, font=_F(11), height=60)
                tb.pack(fill="x", padx=6)
                self._vars[key] = tb

        # Distance auto
        for key in ("km_depart", "km_retour"):
            self._vars[key].trace_add("write", lambda *_: self._calc_distance())
        dist_frame = ctk.CTkFrame(sc, fg_color=Colors.BG_CARD, corner_radius=8,
                                   border_width=1, border_color=Colors.DIVIDER)
        dist_frame.pack(fill="x", padx=6, pady=(10, 4))
        ctk.CTkLabel(dist_frame, text="📏  Distance calculée automatiquement",
                     font=_F(10), text_color=Colors.TEXT_MUTED
                     ).pack(padx=12, pady=(8, 2), anchor="w")
        self._lbl_dist = ctk.CTkLabel(dist_frame, text="— km",
                                       font=_F(15, "bold"), text_color=_C_PLANIFIE)
        self._lbl_dist.pack(padx=12, pady=(0, 8), anchor="w")

        # Pré-remplir date départ
        if not self.mission:
            self._vars["date_depart"].set(datetime.now().strftime("%d/%m/%Y %H:%M"))

        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(fill="x", padx=22, pady=(8, 14))
        ctk.CTkButton(bf, text="✅  Enregistrer",
                      fg_color=_C_LOG, hover_color=_C_LOG_H,
                      font=_F(12, "bold"), height=38, corner_radius=8,
                      command=self._save
                      ).pack(side="left", expand=True, padx=(0, 5))
        ctk.CTkButton(bf, text="✕  Annuler",
                      fg_color="#95A5A6", hover_color="#7F8C8D",
                      font=_F(12), height=38, corner_radius=8,
                      command=self.destroy
                      ).pack(side="left", expand=True, padx=(5, 0))

    def _calc_distance(self):
        try:
            kd = float(self._vars["km_depart"].get().replace(",", "."))
            kr = float(self._vars["km_retour"].get().replace(",", "."))
            dist = kr - kd
            if dist >= 0:
                self._lbl_dist.configure(
                    text=f"{dist:,.0f} km".replace(",", " "),
                    text_color=_C_TERMINE)
            else:
                self._lbl_dist.configure(text="⚠️ Km retour < Km départ",
                                          text_color="#E74C3C")
        except Exception:
            self._lbl_dist.configure(text="— km", text_color=Colors.TEXT_MUTED)

    def _populate(self, m: dict):
        # Véhicule
        immat = m.get("immatriculation", "")
        for v in self.vehicules:
            if v.get("immatriculation") == immat:
                self._veh_var.set(
                    f"{v['immatriculation']} — {v['marque']} {v.get('modele','')}")
                break
        for key, var in self._vars.items():
            val = m.get(key, "")
            if isinstance(var, ctk.CTkTextbox):
                var.delete("1.0", "end")
                var.insert("1.0", str(val) if val else "")
            else:
                var.set(str(val) if val else "")

    def _parse_dt(self, s: str) -> Optional[datetime]:
        for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try: return datetime.strptime(s.strip(), fmt)
            except: continue
        return None

    def _get_vehicule_id(self) -> Optional[int]:
        sel  = self._veh_var.get()
        if not sel or "Aucun" in sel: return None
        immat = sel.split("—")[0].strip()
        for v in self.vehicules:
            if v.get("immatriculation") == immat:
                return v.get("id")
        return None

    def _save(self):
        chauffeur   = self._vars["chauffeur"].get().strip()
        depart      = self._vars["depart"].get().strip()
        destination = self._vars["destination"].get().strip()
        if not all([chauffeur, depart, destination]):
            messagebox.showerror("Erreur",
                "Chauffeur, Lieu départ et Destination sont obligatoires.", parent=self)
            return

        def to_float(v):
            try: return float(str(v).replace(",", ".")) if v else None
            except: return None

        objet      = self._vars["objet"].get().strip()
        passagers  = self._vars["passagers"].get().strip()
        statut     = self._vars["statut"].get()
        km_dep     = to_float(self._vars["km_depart"].get())
        km_ret     = to_float(self._vars["km_retour"].get())
        notes_val  = (self._vars["notes"].get("1.0", "end").strip()
                      if isinstance(self._vars["notes"], ctk.CTkTextbox)
                      else self._vars["notes"].get().strip())
        date_dep   = self._parse_dt(self._vars["date_depart"].get())
        date_ret   = self._parse_dt(self._vars["date_retour"].get())
        vehicule_id = self._get_vehicule_id()

        if not self.db_conn:
            messagebox.showwarning("Mode démo", "Mission enregistrée (simulation).",
                                   parent=self)
            if self.on_save: self.on_save()
            self.destroy()
            return

        try:
            cur = self.db_conn.cursor()
            if self.mission:
                cur.execute("""
                    UPDATE logistique_mission
                    SET vehicule_id=%s, chauffeur=%s, depart=%s, destination=%s,
                        objet=%s, date_depart=%s, date_retour=%s,
                        km_depart=%s, km_retour=%s, statut=%s,
                        passagers=%s, notes=%s
                    WHERE id=%s
                """, (vehicule_id, chauffeur, depart, destination, objet or None,
                      date_dep, date_ret, km_dep, km_ret, statut,
                      passagers or None, notes_val or None, self.mission["id"]))
            else:
                cur.execute("""
                    INSERT INTO logistique_mission
                        (vehicule_id, chauffeur, depart, destination, objet,
                         date_depart, date_retour, km_depart, km_retour,
                         statut, passagers, notes, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                """, (vehicule_id, chauffeur, depart, destination, objet or None,
                      date_dep, date_ret, km_dep, km_ret, statut,
                      passagers or None, notes_val or None))
            self.db_conn.commit()
            cur.close()
            messagebox.showinfo("Succès", "Mission enregistrée avec succès.", parent=self)
            if self.on_save: self.on_save()
            self.destroy()
        except Exception as e:
            try: self.db_conn.rollback()
            except: pass
            messagebox.showerror("Erreur DB", str(e), parent=self)


# ─────────────────────────────────────────────────────────────────────────────
# FEUILLE DE ROUTE  (popup lecture seule)
# ─────────────────────────────────────────────────────────────────────────────

class FeuilleDRoute(ctk.CTkToplevel):
    """Affichage formaté de la feuille de route d'une mission."""

    def __init__(self, master, mission: dict):
        super().__init__(master)
        m = mission
        self.title(f"📄  Feuille de Route — Mission #{m.get('id','')}")
        self.geometry("480x580")
        self.resizable(False, False)
        self.grab_set()

        # En-tête
        hdr = ctk.CTkFrame(self, fg_color=_C_HEADER, corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text="📄  FEUILLE DE ROUTE",
                     font=_F(14, "bold"), text_color="#FFFFFF"
                     ).pack(padx=18, pady=12, anchor="w")
        ctk.CTkLabel(hdr,
                     text=f"Mission #{m.get('id','')}  —  "
                          f"{datetime.now().strftime('%d/%m/%Y')}",
                     font=_F(10), text_color="#BDC3C7"
                     ).pack(padx=18, pady=(0, 12), anchor="w")

        sc = ctk.CTkScrollableFrame(self, fg_color=Colors.BG_PAGE)
        sc.pack(fill="both", expand=True, padx=0)

        def row(label, value, color=Colors.MIDNIGHT):
            fr = ctk.CTkFrame(sc, fg_color=Colors.BG_CARD,
                              corner_radius=6, border_width=1,
                              border_color=Colors.DIVIDER)
            fr.pack(fill="x", padx=14, pady=3)
            ctk.CTkLabel(fr, text=label, font=_F(10),
                         text_color=Colors.TEXT_MUTED, anchor="w", width=140
                         ).pack(side="left", padx=12, pady=8)
            ctk.CTkLabel(fr, text=str(value) if value else "—",
                         font=_F(11, "bold"), text_color=color, anchor="w"
                         ).pack(side="left", padx=6, pady=8, fill="x", expand=True)

        def fmt_dt(v):
            if not v: return "—"
            try:
                if isinstance(v, str): return v[:16]
                return v.strftime("%d/%m/%Y %H:%M")
            except: return str(v)

        statut = m.get("statut", "—")
        statut_color = _STATUT_COLORS.get(statut, Colors.MIDNIGHT)

        ctk.CTkLabel(sc, text="🚗  Véhicule & Chauffeur",
                     font=_F(11, "bold"), text_color=_C_LOG
                     ).pack(padx=14, pady=(14, 4), anchor="w")
        row("Immatriculation",  m.get("immatriculation", "—"))
        row("Marque / Modèle",  f"{m.get('marque','—')} {m.get('modele','')}")
        row("Chauffeur",        m.get("chauffeur", "—"))

        ctk.CTkLabel(sc, text="📍  Trajet",
                     font=_F(11, "bold"), text_color=_C_PLANIFIE
                     ).pack(padx=14, pady=(14, 4), anchor="w")
        row("Départ",       m.get("depart", "—"))
        row("Destination",  m.get("destination", "—"))
        row("Objet",        m.get("objet", "—"))
        row("Passagers",    m.get("passagers", "—"))

        ctk.CTkLabel(sc, text="🕐  Dates & Kilomètres",
                     font=_F(11, "bold"), text_color=_C_EN_COURS
                     ).pack(padx=14, pady=(14, 4), anchor="w")
        row("Date départ",  fmt_dt(m.get("date_depart")))
        row("Date retour",  fmt_dt(m.get("date_retour")))
        kd = m.get("km_depart"); kr = m.get("km_retour")
        row("Km départ",    f"{float(kd):,.0f} km".replace(",", " ") if kd else "—")
        row("Km retour",    f"{float(kr):,.0f} km".replace(",", " ") if kr else "—")
        if kd and kr:
            dist = float(kr) - float(kd)
            row("Distance parcourue",
                f"{dist:,.0f} km".replace(",", " "),
                _C_TERMINE if dist >= 0 else "#E74C3C")

        ctk.CTkLabel(sc, text="📋  Statut & Notes",
                     font=_F(11, "bold"), text_color=_C_HEADER
                     ).pack(padx=14, pady=(14, 4), anchor="w")
        row("Statut", statut, statut_color)
        if m.get("notes"):
            fr = ctk.CTkFrame(sc, fg_color=Colors.BG_CARD, corner_radius=6,
                              border_width=1, border_color=Colors.DIVIDER)
            fr.pack(fill="x", padx=14, pady=3)
            ctk.CTkLabel(fr, text="Notes", font=_F(10),
                         text_color=Colors.TEXT_MUTED, anchor="nw", width=140
                         ).pack(side="left", padx=12, pady=8, anchor="n")
            ctk.CTkLabel(fr, text=m.get("notes", ""),
                         font=_F(11), text_color=Colors.MIDNIGHT,
                         anchor="nw", wraplength=260, justify="left"
                         ).pack(side="left", padx=6, pady=8, fill="x", expand=True)

        ctk.CTkButton(self, text="✕  Fermer",
                      fg_color="#95A5A6", hover_color="#7F8C8D",
                      font=_F(12), height=36, corner_radius=8,
                      command=self.destroy
                      ).pack(padx=22, pady=(8, 14), fill="x")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE PRINCIPALE : ITINÉRAIRES
# ─────────────────────────────────────────────────────────────────────────────

class PageItineraires(ctk.CTkFrame):
    """
    Page principale du module Itinéraires / Missions.
    Signature : PageItineraires(master, db_conn, session_data)
    """

    _SQL_CREATE = """
        CREATE TABLE IF NOT EXISTS logistique_mission (
            id              SERIAL PRIMARY KEY,
            vehicule_id     INTEGER REFERENCES logistique_vehicule(id) ON DELETE SET NULL,
            chauffeur       VARCHAR(80) NOT NULL,
            depart          VARCHAR(120) NOT NULL,
            destination     VARCHAR(120) NOT NULL,
            objet           TEXT,
            date_depart     TIMESTAMP,
            date_retour     TIMESTAMP,
            km_depart       NUMERIC(10,1),
            km_retour       NUMERIC(10,1),
            statut          VARCHAR(20) DEFAULT 'Planifié',
            passagers       VARCHAR(120),
            notes           TEXT,
            created_at      TIMESTAMP DEFAULT NOW()
        );
    """

    _COLS = [
        ("ID",           "id",              45,  "center"),
        ("Départ prévu", "date_depart",      100, "center"),
        ("Immatricul.",  "immatriculation",  100, "center"),
        ("Marque",       "marque",            75, "w"),
        ("Chauffeur",    "chauffeur",         110, "w"),
        ("Départ",       "depart",            110, "w"),
        ("Destination",  "destination",       110, "w"),
        ("Objet",        "objet",             120, "w"),
        ("Km départ",    "km_depart",          75, "e"),
        ("Km retour",    "km_retour",          75, "e"),
        ("Distance",     "_distance",          70, "e"),
        ("Statut",       "statut",             90, "center"),
    ]

    def __init__(self, master, db_conn=None, session_data=None, **kw):
        super().__init__(master, fg_color=Colors.BG_PAGE, corner_radius=0, **kw)
        self.db_conn      = db_conn
        self.session_data = session_data or {}
        self._data: list[dict]     = []
        self._filtered: list[dict] = []
        self._vehicules: list[dict] = []
        self._selected_id: Optional[int] = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._ensure_table()
        self._load_vehicules()
        self._build_header()
        self._build_body()
        self._load_data()

    def _ensure_table(self):
        if not self.db_conn: return
        try:
            cur = self.db_conn.cursor()
            cur.execute(self._SQL_CREATE)
            self.db_conn.commit(); cur.close()
        except Exception as e:
            print(f"[Itineraires] _ensure_table: {e}")
            try: self.db_conn.rollback()
            except: pass

    def _load_vehicules(self):
        if not self.db_conn: return
        try:
            cur = self.db_conn.cursor()
            cur.execute("""
                SELECT id, immatriculation, marque, modele
                FROM logistique_vehicule WHERE statut='Actif' ORDER BY immatriculation
            """)
            cols = [d[0] for d in cur.description]
            self._vehicules = [dict(zip(cols, r)) for r in cur.fetchall()]
            cur.close()
        except Exception as e:
            print(f"[Itineraires] _load_vehicules: {e}")

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=_C_HEADER, corner_radius=0, height=56)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(1, weight=1)
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="🗺️  Itinéraires & Missions",
                     font=_F(17, "bold"), text_color="#FFFFFF"
                     ).grid(row=0, column=0, padx=18, pady=14, sticky="w")
        ctk.CTkLabel(hdr, text="LOGISTIQUE  ›  Itinéraires",
                     font=_F(10), text_color="#95A5A6"
                     ).grid(row=0, column=1, padx=0, pady=14, sticky="w")
        ctk.CTkLabel(hdr, text=datetime.now().strftime("%d/%m/%Y"),
                     font=_F(10), text_color="#BDC3C7"
                     ).grid(row=0, column=2, padx=18, pady=14, sticky="e")

    # ── Body ─────────────────────────────────────────────────────────────────

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(2, weight=1)
        body.grid_columnconfigure(0, weight=1)
        self._build_kpi_row(body)
        self._build_toolbar(body)
        self._build_table(body)
        self._build_statusbar(body)

    # ── KPI ───────────────────────────────────────────────────────────────────

    def _build_kpi_row(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 6))
        row.grid_columnconfigure((0, 1, 2, 3), weight=1)
        kpis = [
            ("🗺️  Missions ce mois",  "0",      _C_PLANIFIE),
            ("🔄  En cours",          "0",      _C_EN_COURS),
            ("✅  Terminées",          "0",      _C_TERMINE),
            ("📏  Km parcourus",       "0 km",   _C_LOG),
        ]
        self._kpi_labels = {}
        for col, (title, val, color) in enumerate(kpis):
            card = ctk.CTkFrame(row, fg_color=Colors.BG_CARD, corner_radius=10,
                                border_width=1, border_color=Colors.DIVIDER)
            card.grid(row=0, column=col, padx=5, sticky="ew")
            ctk.CTkLabel(card, text=title, font=_F(10),
                         text_color=Colors.TEXT_MUTED, anchor="w"
                         ).pack(padx=14, pady=(10, 2), anchor="w")
            lbl = ctk.CTkLabel(card, text=val, font=_F(22, "bold"),
                               text_color=color, anchor="w")
            lbl.pack(padx=14, pady=(0, 10), anchor="w")
            self._kpi_labels[col] = lbl

    def _update_kpis(self):
        now = datetime.now()
        mois = [m for m in self._data if self._is_current_month(m.get("date_depart"))]
        en_cours = sum(1 for m in self._data if m.get("statut") == "En cours")
        terminees = sum(1 for m in self._data if m.get("statut") == "Terminé")
        km_total  = 0
        for m in self._data:
            kd = m.get("km_depart"); kr = m.get("km_retour")
            if kd and kr:
                dist = float(kr) - float(kd)
                if dist > 0: km_total += dist
        self._kpi_labels[0].configure(text=str(len(mois)))
        self._kpi_labels[1].configure(text=str(en_cours))
        self._kpi_labels[2].configure(text=str(terminees))
        self._kpi_labels[3].configure(
            text=f"{km_total:,.0f} km".replace(",", " "))

    @staticmethod
    def _is_current_month(val) -> bool:
        if not val: return False
        try:
            now = datetime.now()
            if isinstance(val, str):
                d = datetime.strptime(val[:10], "%Y-%m-%d")
            elif isinstance(val, datetime):
                d = val
            elif isinstance(val, date):
                d = datetime(val.year, val.month, 1)
            else: return False
            return d.month == now.month and d.year == now.year
        except: return False

    # ── Toolbar ───────────────────────────────────────────────────────────────

    def _build_toolbar(self, parent):
        bar = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD, corner_radius=0,
                           height=50, border_width=1, border_color=Colors.DIVIDER)
        bar.grid(row=1, column=0, sticky="ew", padx=14)
        bar.grid_columnconfigure(4, weight=1)
        bar.grid_propagate(False)

        btns = [
            ("➕  Nouvelle Mission", _C_LOG,    _C_LOG_H,  self._open_add),
            ("✏️  Modifier",         "#2980B9", "#1A6B9A",  self._open_edit),
            ("🗑️  Supprimer",        "#E74C3C", "#C0392B",  self._delete),
            ("📄  Feuille Route",    "#8E44AD", "#7D3C98",  self._show_feuille),
        ]
        for col, (txt, fg, hv, cmd) in enumerate(btns):
            ctk.CTkButton(bar, text=txt, fg_color=fg, hover_color=hv,
                          font=_F(11, "bold"), height=34, width=130,
                          corner_radius=7, command=cmd
                          ).grid(row=0, column=col,
                                 padx=(8 if col == 0 else 3, 3), pady=8)

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_filter())
        ctk.CTkEntry(bar, textvariable=self._search_var,
                     placeholder_text="🔍  Rechercher (chauffeur, destination, immatriculation…)",
                     font=_F(11), height=34, corner_radius=7
                     ).grid(row=0, column=4, padx=(10, 6), pady=8, sticky="ew")

        statut_opts = ["Tous"] + _STATUTS
        self._filter_statut = ctk.StringVar(value="Tous")
        ctk.CTkComboBox(bar, values=statut_opts, variable=self._filter_statut,
                        command=lambda _: self._apply_filter(),
                        font=_F(11), height=34, width=120, corner_radius=7
                        ).grid(row=0, column=5, padx=(0, 4), pady=8)

        ctk.CTkButton(bar, text="🔄", fg_color="#95A5A6", hover_color="#7F8C8D",
                      font=_F(13), height=34, width=40, corner_radius=7,
                      command=self._load_data
                      ).grid(row=0, column=6, padx=(0, 8), pady=8)

    # ── Table ─────────────────────────────────────────────────────────────────

    def _build_table(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD, corner_radius=0,
                             border_width=1, border_color=Colors.DIVIDER)
        frame.grid(row=2, column=0, sticky="nsew", padx=14)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Itin.Treeview",
                        background=_C_ROW_EVEN, foreground=Colors.MIDNIGHT,
                        rowheight=28, fieldbackground=_C_ROW_EVEN,
                        font=("Segoe UI", 10), borderwidth=0)
        style.configure("Itin.Treeview.Heading",
                        background=_C_HEADER, foreground="#FFFFFF",
                        font=("Segoe UI", 10, "bold"), relief="flat", padding=5)
        style.map("Itin.Treeview",
                  background=[("selected", _C_PLANIFIE)],
                  foreground=[("selected", "#FFFFFF")])

        cols = tuple(c[0] for c in self._COLS)
        self._tree = ttk.Treeview(frame, columns=cols, show="headings",
                                   style="Itin.Treeview", selectmode="browse")
        for label, _, width, anchor in self._COLS:
            self._tree.heading(label, text=label,
                               command=lambda c=label: self._sort_by(c))
            self._tree.column(label, width=width, anchor=anchor, minwidth=30)

        self._tree.tag_configure("odd",      background=_C_ROW_ODD)
        self._tree.tag_configure("even",     background=_C_ROW_EVEN)
        self._tree.tag_configure("planifie", foreground=_C_PLANIFIE)
        self._tree.tag_configure("encours",  foreground=_C_EN_COURS)
        self._tree.tag_configure("termine",  foreground=_C_TERMINE)
        self._tree.tag_configure("annule",   foreground=_C_ANNULE)

        vsb = ttk.Scrollbar(frame, orient="vertical",   command=self._tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self._tree.bind("<Double-1>", lambda e: self._open_edit())
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

    def _build_statusbar(self, parent):
        bar = ctk.CTkFrame(parent, fg_color=_C_HEADER, corner_radius=0, height=26)
        bar.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 8))
        bar.grid_propagate(False)
        bar.grid_columnconfigure(0, weight=1)
        self._status_lbl = ctk.CTkLabel(bar, text="Chargement…",
                                         font=_F(10), text_color="#BDC3C7", anchor="w")
        self._status_lbl.grid(row=0, column=0, padx=10, sticky="w")

    # ── Données ───────────────────────────────────────────────────────────────

    def _load_data(self):
        self._data.clear()
        if self.db_conn:
            try:
                cur = self.db_conn.cursor()
                cur.execute("""
                    SELECT m.id, m.vehicule_id, m.chauffeur, m.depart,
                           m.destination, m.objet, m.date_depart, m.date_retour,
                           m.km_depart, m.km_retour, m.statut, m.passagers, m.notes,
                           v.immatriculation, v.marque, v.modele
                    FROM logistique_mission m
                    LEFT JOIN logistique_vehicule v ON v.id = m.vehicule_id
                    ORDER BY m.date_depart DESC, m.id DESC
                """)
                cols = [d[0] for d in cur.description]
                for row in cur.fetchall():
                    self._data.append(dict(zip(cols, row)))
                cur.close()
            except Exception as e:
                print(f"[Itineraires] _load_data: {e}")
        else:
            self._data = self._demo_data()

        self._apply_filter()
        self._update_kpis()
        self._status_lbl.configure(
            text=f"✅  {len(self._data)} mission(s) chargée(s)  —  "
                 f"Mise à jour : {datetime.now().strftime('%H:%M:%S')}")

    @staticmethod
    def _demo_data() -> list[dict]:
        return [
            {"id": 1, "chauffeur": "Jean Rakoto", "depart": "Antananarivo",
             "destination": "Toamasina", "objet": "Livraison marchandises",
             "date_depart": "2026-05-06 06:00:00", "date_retour": "2026-05-07 18:00:00",
             "km_depart": 45000, "km_retour": 45370, "statut": "Terminé",
             "immatriculation": "ABC-1234", "marque": "Toyota", "modele": "Hilux",
             "passagers": "2", "notes": ""},
            {"id": 2, "chauffeur": "Marie Ralay", "depart": "Antananarivo",
             "destination": "Antsirabe", "objet": "Collecte fournisseur",
             "date_depart": "2026-05-08 08:00:00", "date_retour": None,
             "km_depart": 28000, "km_retour": None, "statut": "En cours",
             "immatriculation": "GHI-9012", "marque": "Ford", "modele": "Transit",
             "passagers": "1", "notes": "Retour prévu à 17h"},
            {"id": 3, "chauffeur": "Luc Andria", "depart": "Antananarivo",
             "destination": "Mahajanga", "objet": "Transport personnel",
             "date_depart": "2026-05-10 05:00:00", "date_retour": "2026-05-12 20:00:00",
             "km_depart": 15000, "km_retour": None, "statut": "Planifié",
             "immatriculation": "MNO-7890", "marque": "Peugeot", "modele": "Partner",
             "passagers": "4", "notes": ""},
        ]

    def _apply_filter(self, *_):
        q      = self._search_var.get().lower().strip()
        statut = self._filter_statut.get()
        self._filtered = [
            m for m in self._data
            if (statut == "Tous" or m.get("statut") == statut)
            and (not q or any(
                q in str(m.get(col, "")).lower()
                for col in ("chauffeur", "depart", "destination",
                            "immatriculation", "marque", "objet")
            ))
        ]
        self._refresh_tree()

    def _refresh_tree(self):
        self._tree.delete(*self._tree.get_children())
        for i, m in enumerate(self._filtered):
            statut = m.get("statut", "")
            tag_s  = {"Planifié": "planifie", "En cours": "encours",
                      "Terminé": "termine",   "Annulé": "annule"}.get(statut, "")
            tag_r  = "odd" if i % 2 else "even"

            def fmt_dt(v):
                if not v: return "—"
                try:
                    s = str(v)[:16]
                    return datetime.strptime(s, "%Y-%m-%d %H:%M").strftime("%d/%m %H:%M")
                except: return str(v)[:16]

            def fmt_km(v):
                try: return f"{float(v):,.0f}".replace(",", " ") if v else "—"
                except: return "—"

            kd = m.get("km_depart"); kr = m.get("km_retour")
            dist = "—"
            if kd and kr:
                d = float(kr) - float(kd)
                dist = f"{d:,.0f}".replace(",", " ") if d >= 0 else "⚠️"

            values = (
                m.get("id", ""),
                fmt_dt(m.get("date_depart")),
                m.get("immatriculation", "—"),
                m.get("marque", "—"),
                m.get("chauffeur", ""),
                m.get("depart", ""),
                m.get("destination", ""),
                m.get("objet", "")[:30] if m.get("objet") else "—",
                fmt_km(kd),
                fmt_km(kr),
                dist,
                statut,
            )
            self._tree.insert("", "end", iid=str(m.get("id", i)),
                               values=values, tags=(tag_r, tag_s))

        self._status_lbl.configure(
            text=f"✅  {len(self._filtered)} mission(s)  sur  {len(self._data)} au total")

    _sort_reverse: dict = {}

    def _sort_by(self, col_label: str):
        col_key = next((c[1] for c in self._COLS if c[0] == col_label), None)
        if not col_key: return
        rev = self._sort_reverse.get(col_label, False)
        self._filtered.sort(key=lambda m: (m.get(col_key) or ""), reverse=rev)
        self._sort_reverse[col_label] = not rev
        self._refresh_tree()

    def _on_select(self, _=None):
        sel = self._tree.selection()
        self._selected_id = int(sel[0]) if sel else None

    def _get_selected(self) -> Optional[dict]:
        if self._selected_id is None:
            messagebox.showwarning("Aucune sélection",
                "Veuillez sélectionner une mission.", parent=self)
            return None
        return next((m for m in self._data if m.get("id") == self._selected_id), None)

    def _open_add(self):
        FormMission(self, self.db_conn, vehicules=self._vehicules,
                    on_save=self._load_data)

    def _open_edit(self):
        m = self._get_selected()
        if not m: return
        FormMission(self, self.db_conn, mission=m,
                    vehicules=self._vehicules, on_save=self._load_data)

    def _delete(self):
        m = self._get_selected()
        if not m: return
        ref = f"Mission #{m['id']} ({m.get('destination','—')})"
        if not messagebox.askyesno("Confirmation",
            f"Supprimer {ref} ?", parent=self): return
        if not self.db_conn:
            self._data = [d for d in self._data if d.get("id") != m["id"]]
            self._apply_filter(); self._update_kpis(); return
        try:
            cur = self.db_conn.cursor()
            cur.execute("DELETE FROM logistique_mission WHERE id=%s", (m["id"],))
            self.db_conn.commit(); cur.close()
            messagebox.showinfo("Succès", f"{ref} supprimée.", parent=self)
            self._load_data()
        except Exception as e:
            try: self.db_conn.rollback()
            except: pass
            messagebox.showerror("Erreur DB", str(e), parent=self)

    def _show_feuille(self):
        m = self._get_selected()
        if not m: return
        FeuilleDRoute(self, m)


# ─────────────────────────────────────────────────────────────────────────────
# TEST STANDALONE
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    root.title("iJeery V5.0 — Test Itinéraires")
    root.geometry("1280x720")
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    PageItineraires(master=root, db_conn=None).grid(row=0, column=0, sticky="nsew")
    root.mainloop()

