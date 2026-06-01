# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           iJeery V5.0 — page_carburant.py                                  ║
║           Module LOGISTIQUE › Carburant                                     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Fonctionnalités :                                                           ║
║   • Enregistrement des pleins par véhicule                                  ║
║   • Calcul automatique consommation (L/100km)                               ║
║   • Suivi coût carburant par véhicule et par période                        ║
║   • KPI : litres du mois, coût total, consommation moy., nbre de pleins     ║
║   • Filtres par véhicule, période, type carburant                           ║
║   • Connexion PostgreSQL via db_conn                                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional
from datetime import datetime, date

import customtkinter as ctk

# ── Thème ─────────────────────────────────────────────────────────────────────
try:
    from app_theme import Colors, Fonts
except ImportError:
    class Colors:
        BG_PAGE  = "#ECF0F1"; BG_CARD = "#FFFFFF"; MIDNIGHT = "#2C3E50"
        TEXT_MUTED = "#95A5A6"; DIVIDER = "#E8EAED"
    class Fonts:
        pass

def _F(size=11, weight="normal"):
    return ctk.CTkFont(family="Segoe UI", size=size, weight=weight)

# ── Couleurs module ───────────────────────────────────────────────────────────
_C_LOG     = "#1A6B3C"
_C_LOG_H   = "#27AE60"
_C_HEADER  = "#2C3E50"
_C_FUEL    = "#E67E22"
_C_FUEL_H  = "#D35400"
_C_ROW_ODD  = "#F7F9FC"
_C_ROW_EVEN = "#FFFFFF"


# ─────────────────────────────────────────────────────────────────────────────
# FORMULAIRE BON DE CARBURANT
# ─────────────────────────────────────────────────────────────────────────────

class FormCarburant(ctk.CTkToplevel):
    """Enregistrement d'un bon / plein de carburant."""

    TYPES_CARBURANT = ["Diesel", "Essence", "Sans Plomb 95", "Sans Plomb 98",
                       "GPL", "Électrique"]

    def __init__(self, master, db_conn,
                 bon: Optional[dict] = None,
                 vehicules: Optional[list] = None,
                 on_save: Optional[callable] = None):
        super().__init__(master)
        self.db_conn   = db_conn
        self.bon       = bon
        self.vehicules = vehicules or []
        self.on_save   = on_save
        self._mode     = "Modifier" if bon else "Nouveau Bon"

        self.title(f"⛽  {self._mode} Carburant — iJeery Logistique")
        self.geometry("480x580")
        self.resizable(False, False)
        self.grab_set()
        self.focus_force()
        self._build()
        if bon:
            self._populate(bon)

    def _build(self):
        ctk.CTkLabel(self, text=f"⛽  {self._mode} de Carburant",
                     font=_F(15, "bold"), text_color=_C_FUEL
                     ).pack(pady=(16, 2), padx=22, anchor="w")
        ctk.CTkLabel(self, text="Enregistrez un plein ou une allocation carburant.",
                     font=_F(10), text_color=Colors.TEXT_MUTED
                     ).pack(padx=22, anchor="w")
        ctk.CTkFrame(self, height=1, fg_color=Colors.DIVIDER
                     ).pack(fill="x", padx=22, pady=(8, 12))

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
            ("Date du plein *",      "date_plein",    "entry", None),
            ("Litres (L) *",         "litres",        "entry", None),
            ("Prix / Litre (Ar)",    "prix_litre",    "entry", None),
            ("Type de carburant",    "type_carburant","combo", self.TYPES_CARBURANT),
            ("Km au compteur",       "km_au_plein",   "entry", None),
            ("Station / Lieu",       "station",       "entry", None),
            ("Bon / Référence",      "ref_bon",       "entry", None),
            ("Notes",                "notes",         "textbox", None),
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
                                font=_F(11), height=32).pack(fill="x", padx=6)
                self._vars[key] = var
            elif wtype == "textbox":
                tb = ctk.CTkTextbox(sc, font=_F(11), height=55)
                tb.pack(fill="x", padx=6)
                self._vars[key] = tb

        # Pré-remplir date
        if "date_plein" in self._vars and not self.bon:
            self._vars["date_plein"].set(date.today().strftime("%d/%m/%Y"))

        # Frame montant auto
        mnt_frame = ctk.CTkFrame(sc, fg_color=Colors.BG_CARD, corner_radius=8,
                                  border_width=1, border_color=Colors.DIVIDER)
        mnt_frame.pack(fill="x", padx=6, pady=(10, 4))
        ctk.CTkLabel(mnt_frame, text="💰  Montant total calculé automatiquement",
                     font=_F(10), text_color=Colors.TEXT_MUTED
                     ).pack(padx=12, pady=(8, 2), anchor="w")
        self._lbl_montant = ctk.CTkLabel(mnt_frame, text="— Ar",
                                          font=_F(15, "bold"), text_color=_C_FUEL)
        self._lbl_montant.pack(padx=12, pady=(0, 8), anchor="w")

        # Calcul automatique
        for key in ("litres", "prix_litre"):
            self._vars[key].trace_add("write", lambda *_: self._calc_montant())

        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(fill="x", padx=22, pady=(8, 14))
        ctk.CTkButton(bf, text="✅  Enregistrer",
                      fg_color=_C_FUEL, hover_color=_C_FUEL_H,
                      font=_F(12, "bold"), height=38, corner_radius=8,
                      command=self._save
                      ).pack(side="left", expand=True, padx=(0, 5))
        ctk.CTkButton(bf, text="✕  Annuler",
                      fg_color="#95A5A6", hover_color="#7F8C8D",
                      font=_F(12), height=38, corner_radius=8,
                      command=self.destroy
                      ).pack(side="left", expand=True, padx=(5, 0))

    def _calc_montant(self):
        try:
            L   = float(self._vars["litres"].get().replace(",", "."))
            pu  = float(self._vars["prix_litre"].get().replace(",", "."))
            mnt = L * pu
            self._lbl_montant.configure(
                text=f"{mnt:,.0f} Ar".replace(",", " "), text_color=_C_FUEL)
        except Exception:
            self._lbl_montant.configure(text="— Ar", text_color=Colors.TEXT_MUTED)

    def _populate(self, b: dict):
        for key, var in self._vars.items():
            val = b.get(key, "")
            if isinstance(var, ctk.CTkTextbox):
                var.delete("1.0", "end")
                var.insert("1.0", str(val) if val else "")
            else:
                var.set(str(val) if val else "")

    def _get_vehicule_id(self) -> Optional[int]:
        sel = self._veh_var.get()
        if not sel or "Aucun" in sel: return None
        immat = sel.split("—")[0].strip()
        for v in self.vehicules:
            if v.get("immatriculation") == immat:
                return v.get("id")
        return None

    def _save(self):
        def to_float(v):
            try: return float(str(v).replace(",", ".")) if v else None
            except: return None
        def parse_date(s):
            for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
                try: return datetime.strptime(s, fmt).date()
                except: continue
            return None

        litres_str = self._vars["litres"].get().strip()
        if not litres_str:
            messagebox.showerror("Erreur", "Les litres sont obligatoires.", parent=self)
            return
        litres = to_float(litres_str)
        if not litres or litres <= 0:
            messagebox.showerror("Erreur", "Quantité en litres invalide.", parent=self)
            return

        date_str = self._vars["date_plein"].get().strip()
        d = parse_date(date_str)
        if not d:
            messagebox.showerror("Erreur",
                "Date invalide. Utilisez le format JJ/MM/AAAA.", parent=self)
            return

        prix_litre      = to_float(self._vars["prix_litre"].get())
        montant_total   = (litres * prix_litre) if (litres and prix_litre) else None
        km_au_plein     = to_float(self._vars["km_au_plein"].get())
        type_carb       = self._vars["type_carburant"].get()
        station         = self._vars["station"].get().strip()
        ref_bon         = self._vars["ref_bon"].get().strip()
        notes           = (self._vars["notes"].get("1.0", "end").strip()
                           if isinstance(self._vars["notes"], ctk.CTkTextbox)
                           else self._vars["notes"].get().strip())
        vehicule_id     = self._get_vehicule_id()

        if not self.db_conn:
            messagebox.showwarning("Mode démo",
                f"Simulation : {litres} L enregistrés.", parent=self)
            if self.on_save: self.on_save()
            self.destroy()
            return

        try:
            cur = self.db_conn.cursor()
            if self.bon:
                cur.execute("""
                    UPDATE logistique_carburant
                    SET vehicule_id=%s, date_plein=%s, litres=%s, prix_litre=%s,
                        montant_total=%s, km_au_plein=%s, type_carburant=%s,
                        station=%s, ref_bon=%s, notes=%s
                    WHERE id=%s
                """, (vehicule_id, d, litres, prix_litre, montant_total,
                      km_au_plein, type_carb, station or None,
                      ref_bon or None, notes or None, self.bon["id"]))
            else:
                cur.execute("""
                    INSERT INTO logistique_carburant
                        (vehicule_id, date_plein, litres, prix_litre, montant_total,
                         km_au_plein, type_carburant, station, ref_bon, notes, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                """, (vehicule_id, d, litres, prix_litre, montant_total,
                      km_au_plein, type_carb, station or None,
                      ref_bon or None, notes or None))
            self.db_conn.commit()
            cur.close()
            messagebox.showinfo("Succès", "Bon carburant enregistré.", parent=self)
            if self.on_save: self.on_save()
            self.destroy()
        except Exception as e:
            try: self.db_conn.rollback()
            except: pass
            messagebox.showerror("Erreur DB", str(e), parent=self)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE PRINCIPALE : CARBURANT
# ─────────────────────────────────────────────────────────────────────────────

class PageCarburant(ctk.CTkFrame):
    """
    Page principale du module Carburant.
    Signature : PageCarburant(master, db_conn, session_data)
    """

    _SQL_CREATE = """
        CREATE TABLE IF NOT EXISTS logistique_carburant (
            id              SERIAL PRIMARY KEY,
            vehicule_id     INTEGER REFERENCES logistique_vehicule(id) ON DELETE SET NULL,
            date_plein      DATE NOT NULL DEFAULT CURRENT_DATE,
            litres          NUMERIC(8,2) NOT NULL,
            prix_litre      NUMERIC(8,2),
            montant_total   NUMERIC(12,2),
            km_au_plein     NUMERIC(10,1),
            type_carburant  VARCHAR(20) DEFAULT 'Diesel',
            station         VARCHAR(80),
            ref_bon         VARCHAR(60),
            notes           TEXT,
            created_at      TIMESTAMP DEFAULT NOW()
        );
    """

    _COLS = [
        ("ID",           "id",              45,  "center"),
        ("Date",         "date_plein",       90,  "center"),
        ("Immatricul.",  "immatriculation",  110, "center"),
        ("Marque",       "marque",            80, "w"),
        ("Litres (L)",   "litres",            80, "e"),
        ("Prix/L (Ar)",  "prix_litre",        85, "e"),
        ("Montant (Ar)", "montant_total",    105, "e"),
        ("Km compteur",  "km_au_plein",       90, "e"),
        ("Carburant",    "type_carburant",    80, "center"),
        ("Station",      "station",          100, "w"),
        ("Bon / Réf.",   "ref_bon",           90, "w"),
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
            self.db_conn.commit()
            cur.close()
        except Exception as e:
            print(f"[Carburant] _ensure_table: {e}")
            try: self.db_conn.rollback()
            except: pass

    def _load_vehicules(self):
        if not self.db_conn: return
        try:
            cur = self.db_conn.cursor()
            cur.execute("""
                SELECT id, immatriculation, marque, modele
                FROM logistique_vehicule
                WHERE statut = 'Actif'
                ORDER BY immatriculation
            """)
            cols = [d[0] for d in cur.description]
            self._vehicules = [dict(zip(cols, r)) for r in cur.fetchall()]
            cur.close()
        except Exception as e:
            print(f"[Carburant] _load_vehicules: {e}")

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=_C_HEADER, corner_radius=0, height=56)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(1, weight=1)
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="⛽  Carburant",
                     font=_F(17, "bold"), text_color="#FFFFFF"
                     ).grid(row=0, column=0, padx=18, pady=14, sticky="w")
        ctk.CTkLabel(hdr, text="LOGISTIQUE  ›  Carburant",
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
            ("⛽  Litres ce mois",   "0 L",    _C_FUEL),
            ("💰  Coût ce mois",     "0 Ar",   "#E74C3C"),
            ("📊  Consomm. moy.",    "— L/100","#3498DB"),
            ("🔢  Nb de pleins",     "0",      _C_LOG),
        ]
        self._kpi_labels = {}
        for col, (title, val, color) in enumerate(kpis):
            card = ctk.CTkFrame(row, fg_color=Colors.BG_CARD, corner_radius=10,
                                border_width=1, border_color=Colors.DIVIDER)
            card.grid(row=0, column=col, padx=5, sticky="ew")
            ctk.CTkLabel(card, text=title, font=_F(10),
                         text_color=Colors.TEXT_MUTED, anchor="w"
                         ).pack(padx=14, pady=(10, 2), anchor="w")
            lbl = ctk.CTkLabel(card, text=val, font=_F(20, "bold"),
                               text_color=color, anchor="w")
            lbl.pack(padx=14, pady=(0, 10), anchor="w")
            self._kpi_labels[col] = lbl

    def _update_kpis(self):
        # Filtrer données du mois courant
        now = datetime.now()
        mois = [d for d in self._data
                if self._is_current_month(d.get("date_plein"))]
        litres = sum(float(d.get("litres") or 0) for d in mois)
        cout   = sum(float(d.get("montant_total") or 0) for d in mois)
        nb     = len(mois)

        # Consommation moyenne (L/100km) si données suffisantes
        consomm_str = "— L/100"
        kms = [d for d in mois if d.get("km_au_plein")]
        if len(kms) >= 2:
            try:
                km_sorted = sorted(kms, key=lambda x: float(x.get("km_au_plein") or 0))
                delta_km  = float(km_sorted[-1]["km_au_plein"]) - float(km_sorted[0]["km_au_plein"])
                total_L   = sum(float(d.get("litres") or 0) for d in km_sorted[1:])
                if delta_km > 0:
                    consomm_str = f"{total_L / delta_km * 100:.1f} L/100"
            except Exception:
                pass

        self._kpi_labels[0].configure(text=f"{litres:,.1f} L".replace(",", " "))
        self._kpi_labels[1].configure(text=f"{cout:,.0f} Ar".replace(",", " "))
        self._kpi_labels[2].configure(text=consomm_str)
        self._kpi_labels[3].configure(text=str(nb))

    @staticmethod
    def _is_current_month(val) -> bool:
        if not val: return False
        try:
            now = datetime.now()
            if isinstance(val, str):
                d = datetime.strptime(val[:10], "%Y-%m-%d")
            elif isinstance(val, (date, datetime)):
                d = val
            else:
                return False
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
            ("➕  Nouveau Bon",  _C_FUEL,   _C_FUEL_H, self._open_add),
            ("✏️  Modifier",     "#2980B9", "#1A6B9A",  self._open_edit),
            ("🗑️  Supprimer",    "#E74C3C", "#C0392B",  self._delete),
        ]
        for col, (txt, fg, hv, cmd) in enumerate(btns):
            ctk.CTkButton(bar, text=txt, fg_color=fg, hover_color=hv,
                          font=_F(11, "bold"), height=34, width=120,
                          corner_radius=7, command=cmd
                          ).grid(row=0, column=col,
                                 padx=(8 if col == 0 else 3, 3), pady=8)

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_filter())
        ctk.CTkEntry(bar, textvariable=self._search_var,
                     placeholder_text="🔍  Rechercher (immatriculation, station, bon…)",
                     font=_F(11), height=34, corner_radius=7
                     ).grid(row=0, column=4, padx=(10, 6), pady=8, sticky="ew")

        # Filtre véhicule
        veh_opts = ["Tous"] + [v["immatriculation"] for v in self._vehicules]
        self._filter_veh = ctk.StringVar(value="Tous")
        ctk.CTkComboBox(bar, values=veh_opts, variable=self._filter_veh,
                        command=lambda _: self._apply_filter(),
                        font=_F(11), height=34, width=130, corner_radius=7
                        ).grid(row=0, column=5, padx=(0, 4), pady=8)

        # Filtre mois
        mois_opts = ["Tous les mois", "Ce mois", "Mois dernier"]
        self._filter_mois = ctk.StringVar(value="Ce mois")
        ctk.CTkComboBox(bar, values=mois_opts, variable=self._filter_mois,
                        command=lambda _: self._apply_filter(),
                        font=_F(11), height=34, width=130, corner_radius=7
                        ).grid(row=0, column=6, padx=(0, 4), pady=8)

        ctk.CTkButton(bar, text="🔄", fg_color="#95A5A6", hover_color="#7F8C8D",
                      font=_F(13), height=34, width=40, corner_radius=7,
                      command=self._load_data
                      ).grid(row=0, column=7, padx=(0, 8), pady=8)

    # ── Table ─────────────────────────────────────────────────────────────────

    def _build_table(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD, corner_radius=0,
                             border_width=1, border_color=Colors.DIVIDER)
        frame.grid(row=2, column=0, sticky="nsew", padx=14)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Carb.Treeview",
                        background=_C_ROW_EVEN, foreground=Colors.MIDNIGHT,
                        rowheight=28, fieldbackground=_C_ROW_EVEN,
                        font=("Segoe UI", 10), borderwidth=0)
        style.configure("Carb.Treeview.Heading",
                        background=_C_HEADER, foreground="#FFFFFF",
                        font=("Segoe UI", 10, "bold"), relief="flat", padding=5)
        style.map("Carb.Treeview",
                  background=[("selected", "#E67E22")],
                  foreground=[("selected", "#FFFFFF")])

        cols = tuple(c[0] for c in self._COLS)
        self._tree = ttk.Treeview(frame, columns=cols, show="headings",
                                   style="Carb.Treeview", selectmode="browse")
        for label, _, width, anchor in self._COLS:
            self._tree.heading(label, text=label,
                               command=lambda c=label: self._sort_by(c))
            self._tree.column(label, width=width, anchor=anchor, minwidth=30)

        self._tree.tag_configure("odd",  background=_C_ROW_ODD)
        self._tree.tag_configure("even", background=_C_ROW_EVEN)

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
        # Total Ar affiché à droite
        self._lbl_total = ctk.CTkLabel(bar, text="",
                                        font=_F(10, "bold"), text_color=_C_FUEL)
        self._lbl_total.grid(row=0, column=1, padx=10, sticky="e")

    # ── Données ───────────────────────────────────────────────────────────────

    def _load_data(self):
        self._data.clear()
        if self.db_conn:
            try:
                cur = self.db_conn.cursor()
                cur.execute("""
                    SELECT c.id, c.vehicule_id, c.date_plein, c.litres, c.prix_litre,
                           c.montant_total, c.km_au_plein, c.type_carburant,
                           c.station, c.ref_bon, c.notes,
                           v.immatriculation, v.marque
                    FROM logistique_carburant c
                    LEFT JOIN logistique_vehicule v ON v.id = c.vehicule_id
                    ORDER BY c.date_plein DESC, c.id DESC
                """)
                cols = [d[0] for d in cur.description]
                for row in cur.fetchall():
                    self._data.append(dict(zip(cols, row)))
                cur.close()
            except Exception as e:
                print(f"[Carburant] _load_data: {e}")
        else:
            self._data = self._demo_data()

        self._apply_filter()
        self._update_kpis()
        self._status_lbl.configure(
            text=f"✅  {len(self._data)} bon(s) chargé(s)  —  "
                 f"Mise à jour : {datetime.now().strftime('%H:%M:%S')}")

    @staticmethod
    def _demo_data() -> list[dict]:
        return [
            {"id": 1, "vehicule_id": 1, "date_plein": "2026-05-02",
             "litres": 60.0, "prix_litre": 5200, "montant_total": 312000,
             "km_au_plein": 45500, "type_carburant": "Diesel",
             "station": "Total Analakely", "ref_bon": "BON-001",
             "immatriculation": "ABC-1234", "marque": "Toyota"},
            {"id": 2, "vehicule_id": 2, "date_plein": "2026-05-03",
             "litres": 45.0, "prix_litre": 5200, "montant_total": 234000,
             "km_au_plein": 72100, "type_carburant": "Diesel",
             "station": "Shell Tana", "ref_bon": "BON-002",
             "immatriculation": "DEF-5678", "marque": "Mitsubishi"},
            {"id": 3, "vehicule_id": 3, "date_plein": "2026-05-05",
             "litres": 55.0, "prix_litre": 5200, "montant_total": 286000,
             "km_au_plein": 28200, "type_carburant": "Diesel",
             "station": "Total Ankorondrano", "ref_bon": "BON-003",
             "immatriculation": "GHI-9012", "marque": "Ford"},
        ]

    def _apply_filter(self, *_):
        q          = self._search_var.get().lower().strip()
        veh_filtre = self._filter_veh.get()
        mois_opt   = self._filter_mois.get()
        now        = datetime.now()

        def match_mois(d_val) -> bool:
            if mois_opt == "Tous les mois": return True
            try:
                if isinstance(d_val, str):
                    d = datetime.strptime(d_val[:10], "%Y-%m-%d")
                elif isinstance(d_val, (date, datetime)):
                    d = d_val if isinstance(d_val, datetime) else datetime(d_val.year, d_val.month, 1)
                else:
                    return True
                if mois_opt == "Ce mois":
                    return d.month == now.month and d.year == now.year
                else:  # Mois dernier
                    m, y = (now.month - 1, now.year) if now.month > 1 else (12, now.year - 1)
                    return d.month == m and d.year == y
            except: return True

        self._filtered = [
            d for d in self._data
            if (veh_filtre == "Tous" or d.get("immatriculation") == veh_filtre)
            and match_mois(d.get("date_plein"))
            and (not q or any(
                q in str(d.get(col, "")).lower()
                for col in ("immatriculation", "marque", "station",
                            "ref_bon", "type_carburant")
            ))
        ]
        self._refresh_tree()

    def _refresh_tree(self):
        self._tree.delete(*self._tree.get_children())
        total_ar = 0
        for i, d in enumerate(self._filtered):
            montant = d.get("montant_total")
            if montant: total_ar += float(montant)

            def fmt_num(v, dec=1):
                try: return f"{float(v):,.{dec}f}".replace(",", " ") if v else "—"
                except: return "—"

            date_str = str(d.get("date_plein", ""))[:10] if d.get("date_plein") else "—"
            try:
                date_str = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
            except: pass

            values = (
                d.get("id", ""),
                date_str,
                d.get("immatriculation", "—"),
                d.get("marque", "—"),
                fmt_num(d.get("litres")),
                fmt_num(d.get("prix_litre"), 0),
                fmt_num(d.get("montant_total"), 0),
                fmt_num(d.get("km_au_plein"), 0),
                d.get("type_carburant", "—"),
                d.get("station", "—"),
                d.get("ref_bon", "—"),
            )
            tag = "odd" if i % 2 else "even"
            self._tree.insert("", "end", iid=str(d.get("id", i)),
                               values=values, tags=(tag,))

        self._status_lbl.configure(
            text=f"✅  {len(self._filtered)} bon(s)  sur  {len(self._data)} au total")
        self._lbl_total.configure(
            text=f"Total affiché : {total_ar:,.0f} Ar".replace(",", " "))

    _sort_reverse: dict = {}

    def _sort_by(self, col_label: str):
        col_key = next((c[1] for c in self._COLS if c[0] == col_label), None)
        if not col_key: return
        rev = self._sort_reverse.get(col_label, False)
        self._filtered.sort(key=lambda d: (d.get(col_key) or ""), reverse=rev)
        self._sort_reverse[col_label] = not rev
        self._refresh_tree()

    def _on_select(self, _=None):
        sel = self._tree.selection()
        self._selected_id = int(sel[0]) if sel else None

    def _get_selected(self) -> Optional[dict]:
        if self._selected_id is None:
            messagebox.showwarning("Aucune sélection",
                "Veuillez sélectionner un bon.", parent=self)
            return None
        return next((d for d in self._data if d.get("id") == self._selected_id), None)

    def _open_add(self):
        FormCarburant(self, self.db_conn, vehicules=self._vehicules,
                      on_save=self._load_data)

    def _open_edit(self):
        d = self._get_selected()
        if not d: return
        FormCarburant(self, self.db_conn, bon=d, vehicules=self._vehicules,
                      on_save=self._load_data)

    def _delete(self):
        d = self._get_selected()
        if not d: return
        ref = d.get("ref_bon") or f"ID#{d['id']}"
        if not messagebox.askyesno("Confirmation",
            f"Supprimer le bon {ref} ?", parent=self): return

        if not self.db_conn:
            self._data = [x for x in self._data if x.get("id") != d["id"]]
            self._apply_filter(); self._update_kpis()
            return

        try:
            cur = self.db_conn.cursor()
            cur.execute("DELETE FROM logistique_carburant WHERE id=%s", (d["id"],))
            self.db_conn.commit(); cur.close()
            messagebox.showinfo("Succès", f"Bon {ref} supprimé.", parent=self)
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
    root.title("iJeery V5.0 — Test Carburant")
    root.geometry("1280x720")
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    PageCarburant(master=root, db_conn=None).grid(row=0, column=0, sticky="nsew")
    root.mainloop()


