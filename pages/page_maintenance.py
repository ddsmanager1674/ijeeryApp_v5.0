# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           iJeery V5.0 — page_maintenance.py                                ║
║           Module LOGISTIQUE › Maintenance Véhicules                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Fonctionnalités :                                                           ║
║   • Planning des entretiens préventifs et correctifs                        ║
║   • Suivi : En attente → En cours → Terminé → Annulé                       ║
║   • Types : Vidange, Freins, Pneus, Électrique, Carrosserie, Révision…     ║
║   • Coût de chaque intervention + coût total cumulé                        ║
║   • Historique complet par véhicule                                         ║
║   • KPI : en cours, terminées ce mois, coût du mois, prochaines échéances  ║
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
_C_LOG       = "#1A6B3C"
_C_LOG_H     = "#27AE60"
_C_HEADER    = "#2C3E50"
_C_ATTENTE   = "#3498DB"
_C_EN_COURS  = "#E67E22"
_C_TERMINE   = "#27AE60"
_C_ANNULE    = "#95A5A6"
_C_URGENT    = "#E74C3C"
_C_ROW_ODD   = "#F7F9FC"
_C_ROW_EVEN  = "#FFFFFF"

_STATUTS = ["En attente", "En cours", "Terminé", "Annulé"]
_TYPES_TRAVAUX = [
    "Vidange + Filtres", "Révision générale", "Freinage",
    "Pneus / Jantes",    "Batterie",           "Électrique",
    "Carrosserie",        "Climatisation",      "Transmission",
    "Suspension",         "Courroie distribution","Contrôle technique",
    "Autre"
]
_STATUT_COLORS = {
    "En attente": _C_ATTENTE,
    "En cours":   _C_EN_COURS,
    "Terminé":    _C_TERMINE,
    "Annulé":     _C_ANNULE,
}


# ─────────────────────────────────────────────────────────────────────────────
# FORMULAIRE MAINTENANCE
# ─────────────────────────────────────────────────────────────────────────────

class FormMaintenance(ctk.CTkToplevel):
    """Créer ou modifier une fiche de maintenance."""

    def __init__(self, master, db_conn,
                 fiche: Optional[dict] = None,
                 vehicules: Optional[list] = None,
                 on_save: Optional[callable] = None):
        super().__init__(master)
        self.db_conn   = db_conn
        self.fiche     = fiche
        self.vehicules = vehicules or []
        self.on_save   = on_save
        self._mode     = "Modifier" if fiche else "Nouvelle Fiche"

        self.title(f"🔧  {self._mode} Maintenance — iJeery Logistique")
        self.geometry("510x700")
        self.resizable(False, False)
        self.grab_set()
        self.focus_force()
        self._build()
        if fiche:
            self._populate(fiche)

    def _build(self):
        ctk.CTkLabel(self, text=f"🔧  {self._mode} de Maintenance",
                     font=_F(15, "bold"), text_color=_C_EN_COURS
                     ).pack(pady=(16, 2), padx=22, anchor="w")
        ctk.CTkLabel(self, text="Renseignez les détails de l'intervention.",
                     font=_F(10), text_color=Colors.TEXT_MUTED
                     ).pack(padx=22, anchor="w")
        ctk.CTkFrame(self, height=1, fg_color=Colors.DIVIDER
                     ).pack(fill="x", padx=22, pady=(8, 10))

        sc = ctk.CTkScrollableFrame(self, fg_color="transparent")
        sc.pack(fill="both", expand=True, padx=14)

        self._vars = {}

        # Véhicule
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
            ("Type de travaux *",        "type_travaux",   "combo",  _TYPES_TRAVAUX),
            ("Description",              "description",    "textbox", None),
            ("Garage / Technicien",      "garage",         "entry",   None),
            ("Date entrée (JJ/MM/AAAA)", "date_entree",    "entry",   None),
            ("Date sortie prévue",       "date_sortie",    "entry",   None),
            ("Km au compteur",           "kilometrage",    "entry",   None),
            ("Coût estimé (Ar)",         "cout_estime",    "entry",   None),
            ("Coût réel (Ar)",           "cout",           "entry",   None),
            ("Statut",                   "statut",         "combo",   _STATUTS),
            ("Pièces utilisées",         "pieces_utilisees","entry",  None),
            ("Prochain entretien (km)",  "prochain_km",    "entry",   None),
            ("Notes",                    "notes",          "textbox", None),
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
                tb = ctk.CTkTextbox(sc, font=_F(11), height=55)
                tb.pack(fill="x", padx=6)
                self._vars[key] = tb

        # Pré-remplir date entrée
        if not self.fiche:
            self._vars["date_entree"].set(date.today().strftime("%d/%m/%Y"))

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

    def _populate(self, f: dict):
        immat = f.get("immatriculation", "")
        for v in self.vehicules:
            if v.get("immatriculation") == immat:
                self._veh_var.set(
                    f"{v['immatriculation']} — {v['marque']} {v.get('modele','')}")
                break
        for key, var in self._vars.items():
            val = f.get(key, "")
            if isinstance(var, ctk.CTkTextbox):
                var.delete("1.0", "end")
                var.insert("1.0", str(val) if val else "")
            else:
                var.set(str(val) if val else "")

    def _parse_date(self, s: str) -> Optional[date]:
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try: return datetime.strptime(s.strip(), fmt).date()
            except: continue
        return None

    def _get_vehicule_id(self) -> Optional[int]:
        sel = self._veh_var.get()
        if not sel or "Aucun" in sel: return None
        immat = sel.split("—")[0].strip()
        for v in self.vehicules:
            if v.get("immatriculation") == immat:
                return v.get("id")
        return None

    def _save(self):
        type_t = self._vars["type_travaux"].get().strip()
        if not type_t:
            messagebox.showerror("Erreur", "Le type de travaux est obligatoire.", parent=self)
            return

        def to_float(v):
            try: return float(str(v).replace(",", ".")) if v else None
            except: return None

        def get_text(k):
            var = self._vars[k]
            if isinstance(var, ctk.CTkTextbox):
                return var.get("1.0", "end").strip()
            return var.get().strip()

        date_e = self._parse_date(self._vars["date_entree"].get())
        date_s = self._parse_date(self._vars["date_sortie"].get())
        vehicule_id = self._get_vehicule_id()

        statut          = self._vars["statut"].get()
        garage          = self._vars["garage"].get().strip()
        description     = get_text("description")
        pieces          = self._vars["pieces_utilisees"].get().strip()
        notes           = get_text("notes")
        km              = to_float(self._vars["kilometrage"].get())
        cout_estime     = to_float(self._vars["cout_estime"].get())
        cout            = to_float(self._vars["cout"].get())
        prochain_km     = to_float(self._vars["prochain_km"].get())

        if not self.db_conn:
            messagebox.showwarning("Mode démo", "Fiche enregistrée (simulation).", parent=self)
            if self.on_save: self.on_save()
            self.destroy()
            return

        try:
            cur = self.db_conn.cursor()
            if self.fiche:
                cur.execute("""
                    UPDATE logistique_maintenance
                    SET vehicule_id=%s, type_travaux=%s, description=%s,
                        garage=%s, date_entree=%s, date_sortie=%s,
                        kilometrage=%s, cout_estime=%s, cout=%s,
                        statut=%s, pieces_utilisees=%s, prochain_km=%s, notes=%s
                    WHERE id=%s
                """, (vehicule_id, type_t, description or None,
                      garage or None, date_e, date_s,
                      km, cout_estime, cout, statut,
                      pieces or None, prochain_km, notes or None,
                      self.fiche["id"]))
            else:
                cur.execute("""
                    INSERT INTO logistique_maintenance
                        (vehicule_id, type_travaux, description, garage,
                         date_entree, date_sortie, kilometrage, cout_estime,
                         cout, statut, pieces_utilisees, prochain_km, notes, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                """, (vehicule_id, type_t, description or None,
                      garage or None, date_e, date_s,
                      km, cout_estime, cout, statut,
                      pieces or None, prochain_km, notes or None))
            self.db_conn.commit(); cur.close()
            messagebox.showinfo("Succès", "Fiche de maintenance enregistrée.", parent=self)
            if self.on_save: self.on_save()
            self.destroy()
        except Exception as e:
            try: self.db_conn.rollback()
            except: pass
            messagebox.showerror("Erreur DB", str(e), parent=self)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE PRINCIPALE : MAINTENANCE
# ─────────────────────────────────────────────────────────────────────────────

class PageMaintenance(ctk.CTkFrame):
    """
    Page principale du module Maintenance Véhicules.
    Signature : PageMaintenance(master, db_conn, session_data)
    """

    _SQL_CREATE = """
        CREATE TABLE IF NOT EXISTS logistique_maintenance (
            id                SERIAL PRIMARY KEY,
            vehicule_id       INTEGER REFERENCES logistique_vehicule(id) ON DELETE SET NULL,
            type_travaux      VARCHAR(80) NOT NULL,
            description       TEXT,
            garage            VARCHAR(80),
            date_entree       DATE,
            date_sortie       DATE,
            kilometrage       NUMERIC(10,1),
            cout_estime       NUMERIC(12,2),
            cout              NUMERIC(12,2),
            statut            VARCHAR(20) DEFAULT 'En attente',
            pieces_utilisees  TEXT,
            prochain_km       NUMERIC(10,1),
            notes             TEXT,
            created_at        TIMESTAMP DEFAULT NOW()
        );
    """

    _COLS = [
        ("ID",             "id",               45,  "center"),
        ("Date entrée",    "date_entree",       90,  "center"),
        ("Immatricul.",    "immatriculation",   100, "center"),
        ("Marque",         "marque",             70, "w"),
        ("Type travaux",   "type_travaux",       130, "w"),
        ("Garage",         "garage",             100, "w"),
        ("Km",             "kilometrage",         70, "e"),
        ("Coût estimé",    "cout_estime",         90, "e"),
        ("Coût réel",      "cout",                90, "e"),
        ("Date sortie",    "date_sortie",          90, "center"),
        ("Prochain km",    "prochain_km",          80, "e"),
        ("Statut",         "statut",               90, "center"),
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
            print(f"[Maintenance] _ensure_table: {e}")
            try: self.db_conn.rollback()
            except: pass

    def _load_vehicules(self):
        if not self.db_conn: return
        try:
            cur = self.db_conn.cursor()
            cur.execute("""
                SELECT id, immatriculation, marque, modele
                FROM logistique_vehicule ORDER BY immatriculation
            """)
            cols = [d[0] for d in cur.description]
            self._vehicules = [dict(zip(cols, r)) for r in cur.fetchall()]
            cur.close()
        except Exception as e:
            print(f"[Maintenance] _load_vehicules: {e}")

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=_C_HEADER, corner_radius=0, height=56)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(1, weight=1)
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="🔧  Maintenance Véhicules",
                     font=_F(17, "bold"), text_color="#FFFFFF"
                     ).grid(row=0, column=0, padx=18, pady=14, sticky="w")
        ctk.CTkLabel(hdr, text="LOGISTIQUE  ›  Maintenance",
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
            ("🔧  En cours",          "0",      _C_EN_COURS),
            ("⏳  En attente",         "0",      _C_ATTENTE),
            ("✅  Terminées ce mois",  "0",      _C_TERMINE),
            ("💰  Coût ce mois (Ar)",  "0",      _C_URGENT),
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
        now   = datetime.now()
        en_cours  = sum(1 for f in self._data if f.get("statut") == "En cours")
        attente   = sum(1 for f in self._data if f.get("statut") == "En attente")
        term_mois = sum(1 for f in self._data
                        if f.get("statut") == "Terminé"
                        and self._is_current_month(f.get("date_sortie")))
        cout_mois = sum(float(f.get("cout") or f.get("cout_estime") or 0)
                        for f in self._data
                        if self._is_current_month(
                            f.get("date_sortie") or f.get("date_entree")))
        self._kpi_labels[0].configure(text=str(en_cours))
        self._kpi_labels[1].configure(text=str(attente))
        self._kpi_labels[2].configure(text=str(term_mois))
        self._kpi_labels[3].configure(
            text=f"{cout_mois:,.0f}".replace(",", " "))

    @staticmethod
    def _is_current_month(val) -> bool:
        if not val: return False
        try:
            now = datetime.now()
            if isinstance(val, str): d = datetime.strptime(val[:10], "%Y-%m-%d")
            elif isinstance(val, (date, datetime)):
                d = val if isinstance(val, datetime) else datetime(val.year, val.month, 1)
            else: return False
            return d.month == now.month and d.year == now.year
        except: return False

    # ── Toolbar ───────────────────────────────────────────────────────────────

    def _build_toolbar(self, parent):
        bar = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD, corner_radius=0,
                           height=50, border_width=1, border_color=Colors.DIVIDER)
        bar.grid(row=1, column=0, sticky="ew", padx=14)
        bar.grid_columnconfigure(3, weight=1)
        bar.grid_propagate(False)

        btns = [
            ("➕  Nouvelle Fiche",  _C_LOG,    _C_LOG_H,  self._open_add),
            ("✏️  Modifier",        "#2980B9", "#1A6B9A",  self._open_edit),
            ("🗑️  Supprimer",       "#E74C3C", "#C0392B",  self._delete),
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
                     placeholder_text="🔍  Rechercher (véhicule, type travaux, garage…)",
                     font=_F(11), height=34, corner_radius=7
                     ).grid(row=0, column=3, padx=(10, 6), pady=8, sticky="ew")

        statut_opts = ["Tous"] + _STATUTS
        self._filter_statut = ctk.StringVar(value="Tous")
        ctk.CTkComboBox(bar, values=statut_opts, variable=self._filter_statut,
                        command=lambda _: self._apply_filter(),
                        font=_F(11), height=34, width=120, corner_radius=7
                        ).grid(row=0, column=4, padx=(0, 4), pady=8)

        type_opts = ["Tous types"] + _TYPES_TRAVAUX
        self._filter_type = ctk.StringVar(value="Tous types")
        ctk.CTkComboBox(bar, values=type_opts, variable=self._filter_type,
                        command=lambda _: self._apply_filter(),
                        font=_F(11), height=34, width=150, corner_radius=7
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
        style.configure("Maint.Treeview",
                        background=_C_ROW_EVEN, foreground=Colors.MIDNIGHT,
                        rowheight=28, fieldbackground=_C_ROW_EVEN,
                        font=("Segoe UI", 10), borderwidth=0)
        style.configure("Maint.Treeview.Heading",
                        background=_C_HEADER, foreground="#FFFFFF",
                        font=("Segoe UI", 10, "bold"), relief="flat", padding=5)
        style.map("Maint.Treeview",
                  background=[("selected", _C_EN_COURS)],
                  foreground=[("selected", "#FFFFFF")])

        cols = tuple(c[0] for c in self._COLS)
        self._tree = ttk.Treeview(frame, columns=cols, show="headings",
                                   style="Maint.Treeview", selectmode="browse")
        for label, _, width, anchor in self._COLS:
            self._tree.heading(label, text=label,
                               command=lambda c=label: self._sort_by(c))
            self._tree.column(label, width=width, anchor=anchor, minwidth=30)

        self._tree.tag_configure("odd",     background=_C_ROW_ODD)
        self._tree.tag_configure("even",    background=_C_ROW_EVEN)
        self._tree.tag_configure("attente", foreground=_C_ATTENTE)
        self._tree.tag_configure("encours", foreground=_C_EN_COURS)
        self._tree.tag_configure("termine", foreground=_C_TERMINE)
        self._tree.tag_configure("annule",  foreground=_C_ANNULE)
        self._tree.tag_configure("urgent",  foreground=_C_URGENT,
                                            background="#FFF3F3")

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
        self._lbl_total = ctk.CTkLabel(bar, text="",
                                        font=_F(10, "bold"), text_color=_C_EN_COURS)
        self._lbl_total.grid(row=0, column=1, padx=10, sticky="e")

    # ── Données ───────────────────────────────────────────────────────────────

    def _load_data(self):
        self._data.clear()
        if self.db_conn:
            try:
                cur = self.db_conn.cursor()
                cur.execute("""
                    SELECT m.id, m.vehicule_id, m.type_travaux, m.description,
                           m.garage, m.date_entree, m.date_sortie, m.kilometrage,
                           m.cout_estime, m.cout, m.statut, m.pieces_utilisees,
                           m.prochain_km, m.notes,
                           v.immatriculation, v.marque, v.modele
                    FROM logistique_maintenance m
                    LEFT JOIN logistique_vehicule v ON v.id = m.vehicule_id
                    ORDER BY
                        CASE m.statut
                            WHEN 'En cours'   THEN 1
                            WHEN 'En attente' THEN 2
                            WHEN 'Terminé'    THEN 3
                            ELSE 4
                        END,
                        m.date_entree DESC
                """)
                cols = [d[0] for d in cur.description]
                for row in cur.fetchall():
                    self._data.append(dict(zip(cols, row)))
                cur.close()
            except Exception as e:
                print(f"[Maintenance] _load_data: {e}")
        else:
            self._data = self._demo_data()

        self._apply_filter()
        self._update_kpis()
        self._status_lbl.configure(
            text=f"✅  {len(self._data)} fiche(s) chargée(s)  —  "
                 f"Mise à jour : {datetime.now().strftime('%H:%M:%S')}")

    @staticmethod
    def _demo_data() -> list[dict]:
        return [
            {"id": 1, "type_travaux": "Vidange + Filtres",
             "description": "Vidange moteur + filtre à huile + filtre à air",
             "garage": "Garage Central", "date_entree": "2026-05-06",
             "date_sortie": "2026-05-06", "kilometrage": 45000,
             "cout_estime": 180000, "cout": 175000, "statut": "Terminé",
             "pieces_utilisees": "Huile 5W40, Filtre Purflux",
             "prochain_km": 50000, "notes": "",
             "immatriculation": "ABC-1234", "marque": "Toyota", "modele": "Hilux"},
            {"id": 2, "type_travaux": "Freinage",
             "description": "Remplacement plaquettes avant + disques",
             "garage": "Auto Expert", "date_entree": "2026-05-07",
             "date_sortie": None, "kilometrage": 72000,
             "cout_estime": 450000, "cout": None, "statut": "En cours",
             "pieces_utilisees": "Plaquettes Ferodo, Disques ATE",
             "prochain_km": None, "notes": "Commande pièces en attente",
             "immatriculation": "DEF-5678", "marque": "Mitsubishi", "modele": "L200"},
            {"id": 3, "type_travaux": "Contrôle technique",
             "description": "Visite technique annuelle obligatoire",
             "garage": "CTMM", "date_entree": "2026-05-15",
             "date_sortie": None, "kilometrage": 28000,
             "cout_estime": 85000, "cout": None, "statut": "En attente",
             "pieces_utilisees": "", "prochain_km": None, "notes": "",
             "immatriculation": "GHI-9012", "marque": "Ford", "modele": "Transit"},
        ]

    def _apply_filter(self, *_):
        q      = self._search_var.get().lower().strip()
        statut = self._filter_statut.get()
        type_t = self._filter_type.get()
        self._filtered = [
            f for f in self._data
            if (statut == "Tous" or f.get("statut") == statut)
            and (type_t == "Tous types" or f.get("type_travaux") == type_t)
            and (not q or any(
                q in str(f.get(col, "")).lower()
                for col in ("immatriculation", "marque", "type_travaux",
                            "garage", "description", "pieces_utilisees")
            ))
        ]
        self._refresh_tree()

    def _refresh_tree(self):
        self._tree.delete(*self._tree.get_children())
        total_cout = 0
        for i, f in enumerate(self._filtered):
            statut = f.get("statut", "")
            tag_s  = {"En attente": "attente", "En cours": "encours",
                      "Terminé": "termine",    "Annulé": "annule"}.get(statut, "")
            tag_r  = "odd" if i % 2 else "even"

            # Surbrillance rouge si En cours depuis > 7 jours
            extra_tag = ""
            if statut == "En cours" and f.get("date_entree"):
                try:
                    de = datetime.strptime(str(f["date_entree"])[:10], "%Y-%m-%d")
                    if (datetime.now() - de).days > 7:
                        extra_tag = "urgent"
                except: pass

            def fmt_date(v):
                if not v: return "—"
                try: return datetime.strptime(str(v)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
                except: return str(v)[:10]

            def fmt_ar(v):
                try: return f"{float(v):,.0f}".replace(",", " ") if v else "—"
                except: return "—"

            cout_val = f.get("cout") or f.get("cout_estime")
            if cout_val: total_cout += float(cout_val)

            values = (
                f.get("id", ""),
                fmt_date(f.get("date_entree")),
                f.get("immatriculation", "—"),
                f.get("marque", "—"),
                f.get("type_travaux", ""),
                f.get("garage", "—"),
                fmt_ar(f.get("kilometrage")),
                fmt_ar(f.get("cout_estime")),
                fmt_ar(f.get("cout")),
                fmt_date(f.get("date_sortie")),
                fmt_ar(f.get("prochain_km")),
                statut,
            )
            tags = (extra_tag or tag_r, tag_s)
            self._tree.insert("", "end", iid=str(f.get("id", i)),
                               values=values, tags=tags)

        self._status_lbl.configure(
            text=f"✅  {len(self._filtered)} fiche(s)  sur  {len(self._data)} au total")
        self._lbl_total.configure(
            text=f"Total coût affiché : {total_cout:,.0f} Ar".replace(",", " "))

    _sort_reverse: dict = {}

    def _sort_by(self, col_label: str):
        col_key = next((c[1] for c in self._COLS if c[0] == col_label), None)
        if not col_key: return
        rev = self._sort_reverse.get(col_label, False)
        self._filtered.sort(key=lambda f: (f.get(col_key) or ""), reverse=rev)
        self._sort_reverse[col_label] = not rev
        self._refresh_tree()

    def _on_select(self, _=None):
        sel = self._tree.selection()
        self._selected_id = int(sel[0]) if sel else None

    def _get_selected(self) -> Optional[dict]:
        if self._selected_id is None:
            messagebox.showwarning("Aucune sélection",
                "Veuillez sélectionner une fiche.", parent=self)
            return None
        return next((f for f in self._data if f.get("id") == self._selected_id), None)

    def _open_add(self):
        FormMaintenance(self, self.db_conn, vehicules=self._vehicules,
                        on_save=self._load_data)

    def _open_edit(self):
        f = self._get_selected()
        if not f: return
        FormMaintenance(self, self.db_conn, fiche=f,
                        vehicules=self._vehicules, on_save=self._load_data)

    def _delete(self):
        f = self._get_selected()
        if not f: return
        ref = f"Fiche #{f['id']} ({f.get('type_travaux','—')})"
        if not messagebox.askyesno("Confirmation",
            f"Supprimer {ref} ?", parent=self): return
        if not self.db_conn:
            self._data = [d for d in self._data if d.get("id") != f["id"]]
            self._apply_filter(); self._update_kpis(); return
        try:
            cur = self.db_conn.cursor()
            cur.execute("DELETE FROM logistique_maintenance WHERE id=%s", (f["id"],))
            self.db_conn.commit(); cur.close()
            messagebox.showinfo("Succès", f"{ref} supprimée.", parent=self)
            self._load_data()
        except Exception as e:
            try: self.db_conn.rollback()
            except: pass
            messagebox.showerror("Erreur DB", str(e), parent=self)


# ─────────────────────────────────────────────────────────────────────────────
# TEST STANDALONE
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    root.title("iJeery V5.0 — Test Maintenance")
    root.geometry("1280x720")
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    PageMaintenance(master=root, db_conn=None).grid(row=0, column=0, sticky="nsew")
    root.mainloop()


