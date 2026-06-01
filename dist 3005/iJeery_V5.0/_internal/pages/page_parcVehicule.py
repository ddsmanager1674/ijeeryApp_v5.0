# -*- coding: utf-8 -*-
"""
iJeery V5.0 — page_parcVehicule.py
Module LOGISTIQUE › Parc Véhicule
"""

from __future__ import annotations

from tkinter import ttk, messagebox
from typing import Optional
from datetime import datetime, date

import customtkinter as ctk

try:
    from app_theme import Colors, Fonts
except ImportError:
    class Colors:
        BG_PAGE = "#ECF0F1"
        BG_CARD = "#FFFFFF"
        MIDNIGHT = "#2C3E50"
        TEXT_MUTED = "#95A5A6"
        DIVIDER = "#E8EAED"
    class Fonts:
        pass


def _F(size=11, weight="normal"):
    return ctk.CTkFont(family="Segoe UI", size=size, weight=weight)


_C_LOG = "#1A6B3C"
_C_LOG_H = "#27AE60"
_C_HEADER = "#2C3E50"
_C_ACTIF = "#27AE60"
_C_INACTIF = "#95A5A6"
_C_MAINT = "#E67E22"
_C_ROW_ODD = "#F7F9FC"
_C_ROW_EVEN = "#FFFFFF"

_TYPES = ["Voiture", "Camionnette", "Camion", "Moto", "Bus", "Autre"]
_CARBURANTS = ["Diesel", "Essence", "GPL", "Électrique", "Hybride"]
_STATUTS = ["Actif", "En maintenance", "Hors service", "Vendu"]


class FormVehicule(ctk.CTkToplevel):
    """Ajout ou modification d'un véhicule."""

    def __init__(self, master, db_conn, vehicule: Optional[dict] = None,
                 on_save: Optional[callable] = None):
        super().__init__(master)
        self.db_conn = db_conn
        self.vehicule = vehicule
        self.on_save = on_save
        self._mode = "Modifier" if vehicule else "Ajouter"

        self.title(f"{self._mode} un Véhicule — iJeery Logistique")
        self.geometry("520x720")
        self.resizable(False, False)
        self.grab_set()
        self.focus_force()
        self._build()
        if vehicule:
            self._populate(vehicule)

    def _build(self):
        ctk.CTkLabel(self, text=f"🚗  {self._mode} un Véhicule",
                     font=_F(15, "bold"), text_color=_C_LOG
                     ).pack(pady=(16, 2), padx=22, anchor="w")
        ctk.CTkLabel(self, text="Renseignez les informations du véhicule.",
                     font=_F(10), text_color=Colors.TEXT_MUTED
                     ).pack(padx=22, anchor="w")
        ctk.CTkFrame(self, height=1, fg_color=Colors.DIVIDER
                     ).pack(fill="x", padx=22, pady=(8, 12))

        sc = ctk.CTkScrollableFrame(self, fg_color="transparent")
        sc.pack(fill="both", expand=True, padx=14)

        self._vars = {}
        fields = [
            ("Immatriculation *", "immatriculation", "entry", None),
            ("Marque *", "marque", "entry", None),
            ("Modèle", "modele", "entry", None),
            ("Type véhicule", "type_vehicule", "combo", _TYPES),
            ("Année", "annee", "entry", None),
            ("Couleur", "couleur", "entry", None),
            ("N° Châssis", "num_chassis", "entry", None),
            ("N° Moteur", "num_moteur", "entry", None),
            ("Kilométrage", "kilometrage", "entry", None),
            ("Carburant", "carburant", "combo", _CARBURANTS),
            ("Date mise en service", "date_mise_service", "entry", None),
            ("Statut", "statut", "combo", _STATUTS),
            ("Chauffeur habituel", "chauffeur", "entry", None),
            ("Notes", "notes", "textbox", None),
        ]

        for label_txt, key, wtype, opts in fields:
            ctk.CTkLabel(sc, text=label_txt, font=_F(10, "bold"),
                         text_color=Colors.MIDNIGHT, anchor="w"
                         ).pack(fill="x", padx=6, pady=(7, 1))
            if wtype == "entry":
                var = ctk.StringVar()
                ctk.CTkEntry(sc, textvariable=var, font=_F(11), height=32,
                             placeholder_text=label_txt.replace(" *", "")
                             ).pack(fill="x", padx=6)
                self._vars[key] = var
            elif wtype == "combo":
                var = ctk.StringVar(value=opts[0])
                ctk.CTkComboBox(sc, values=opts, variable=var,
                                font=_F(11), height=32).pack(fill="x", padx=6)
                self._vars[key] = var
            elif wtype == "textbox":
                tb = ctk.CTkTextbox(sc, font=_F(11), height=60)
                tb.pack(fill="x", padx=6)
                self._vars[key] = tb

        if "statut" in self._vars and not self.vehicule:
            self._vars["statut"].set("Actif")
        if "carburant" in self._vars and not self.vehicule:
            self._vars["carburant"].set("Diesel")

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

    def _populate(self, v: dict):
        for key, var in self._vars.items():
            val = v.get(key, "")
            if key == "date_mise_service" and val:
                if hasattr(val, "strftime"):
                    val = val.strftime("%d/%m/%Y")
            if isinstance(var, ctk.CTkTextbox):
                var.delete("1.0", "end")
                var.insert("1.0", str(val) if val else "")
            else:
                var.set(str(val) if val is not None else "")

    def _get_values(self) -> dict:
        data = {}
        for key, var in self._vars.items():
            if isinstance(var, ctk.CTkTextbox):
                data[key] = var.get("1.0", "end").strip()
            else:
                data[key] = var.get().strip()
        return data

    def _save(self):
        data = self._get_values()
        if not data.get("immatriculation"):
            messagebox.showerror("Erreur", "L'immatriculation est obligatoire.", parent=self)
            return
        if not data.get("marque"):
            messagebox.showerror("Erreur", "La marque est obligatoire.", parent=self)
            return

        def to_int(v):
            try:
                return int(v) if v else None
            except ValueError:
                return None

        def to_float(v):
            try:
                return float(str(v).replace(",", ".")) if v else None
            except ValueError:
                return None

        def parse_date(s):
            if not s:
                return None
            for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                try:
                    return datetime.strptime(s, fmt).date()
                except ValueError:
                    continue
            return None

        if not self.db_conn:
            messagebox.showwarning("Mode démo",
                                   "Base non connectée — enregistrement simulé.", parent=self)
            if self.on_save:
                self.on_save(data)
            self.destroy()
            return

        try:
            cur = self.db_conn.cursor()
            params = (
                data["immatriculation"], data["marque"], data["modele"],
                data["type_vehicule"], to_int(data["annee"]), data["couleur"],
                data["num_chassis"], data["num_moteur"],
                to_float(data["kilometrage"]) or 0,
                data["carburant"], parse_date(data["date_mise_service"]),
                data["statut"], data["chauffeur"], data["notes"],
            )
            if self.vehicule:
                cur.execute("""
                    UPDATE logistique_vehicule
                    SET immatriculation=%s, marque=%s, modele=%s, type_vehicule=%s,
                        annee=%s, couleur=%s, num_chassis=%s, num_moteur=%s,
                        kilometrage=%s, carburant=%s, date_mise_service=%s,
                        statut=%s, chauffeur=%s, notes=%s, updated_at=NOW()
                    WHERE id=%s
                """, params + (self.vehicule["id"],))
            else:
                cur.execute("""
                    INSERT INTO logistique_vehicule
                        (immatriculation, marque, modele, type_vehicule, annee, couleur,
                         num_chassis, num_moteur, kilometrage, carburant, date_mise_service,
                         statut, chauffeur, notes, created_at, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW())
                """, params)
            self.db_conn.commit()
            cur.close()
            messagebox.showinfo("Succès", "Véhicule enregistré.", parent=self)
            if self.on_save:
                self.on_save(data)
            self.destroy()
        except Exception as e:
            try:
                self.db_conn.rollback()
            except Exception:
                pass
            messagebox.showerror("Erreur DB", str(e), parent=self)


class PageParcVehicule(ctk.CTkFrame):
    """Page principale du parc véhicule."""

    _SQL_CREATE = """
        CREATE TABLE IF NOT EXISTS logistique_vehicule (
            id                SERIAL PRIMARY KEY,
            immatriculation   VARCHAR(30) UNIQUE NOT NULL,
            marque            VARCHAR(60) NOT NULL,
            modele            VARCHAR(60),
            type_vehicule     VARCHAR(40) DEFAULT 'Voiture',
            annee             INTEGER,
            couleur           VARCHAR(30),
            num_chassis       VARCHAR(60),
            num_moteur        VARCHAR(60),
            kilometrage       NUMERIC(10,1) DEFAULT 0,
            carburant         VARCHAR(20) DEFAULT 'Diesel',
            date_mise_service DATE,
            statut            VARCHAR(30) DEFAULT 'Actif',
            chauffeur         VARCHAR(80),
            notes             TEXT,
            created_at        TIMESTAMP DEFAULT NOW(),
            updated_at        TIMESTAMP DEFAULT NOW()
        );
    """

    _COLS = [
        ("ID", "id", 45, "center"),
        ("Immatricul.", "immatriculation", 110, "center"),
        ("Marque", "marque", 90, "w"),
        ("Modèle", "modele", 90, "w"),
        ("Type", "type_vehicule", 90, "center"),
        ("Année", "annee", 55, "center"),
        ("Km", "kilometrage", 80, "e"),
        ("Carburant", "carburant", 80, "center"),
        ("Chauffeur", "chauffeur", 110, "w"),
        ("Statut", "statut", 100, "center"),
    ]

    def __init__(self, master, db_conn=None, session_data=None, **kw):
        super().__init__(master, fg_color=Colors.BG_PAGE, corner_radius=0, **kw)
        self.db_conn = db_conn
        self.session_data = session_data or {}
        self._data: list[dict] = []
        self._filtered: list[dict] = []
        self._selected_id: Optional[int] = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._ensure_table()
        self._build_header()
        self._build_body()
        self._load_data()

    def _ensure_table(self):
        if not self.db_conn:
            return
        try:
            cur = self.db_conn.cursor()
            cur.execute(self._SQL_CREATE)
            self.db_conn.commit()
            cur.close()
        except Exception as e:
            print(f"[ParcVehicule] _ensure_table: {e}")
            try:
                self.db_conn.rollback()
            except Exception:
                pass

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=_C_HEADER, corner_radius=0, height=56)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(1, weight=1)
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="🚗  Parc Véhicule",
                     font=_F(17, "bold"), text_color="#FFFFFF"
                     ).grid(row=0, column=0, padx=18, pady=14, sticky="w")
        ctk.CTkLabel(hdr, text="LOGISTIQUE  ›  Parc Véhicule",
                     font=_F(10), text_color="#95A5A6"
                     ).grid(row=0, column=1, padx=0, pady=14, sticky="w")
        ctk.CTkLabel(hdr, text=datetime.now().strftime("%d/%m/%Y"),
                     font=_F(10), text_color="#BDC3C7"
                     ).grid(row=0, column=2, padx=18, pady=14, sticky="e")

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(2, weight=1)
        body.grid_columnconfigure(0, weight=1)
        self._build_kpi_row(body)
        self._build_toolbar(body)
        self._build_table(body)
        self._build_statusbar(body)

    def _build_kpi_row(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 6))
        row.grid_columnconfigure((0, 1, 2, 3), weight=1)

        kpis = [
            ("🚗  Total Véhicules", "0", "#3498DB"),
            ("✅  Actifs", "0", _C_ACTIF),
            ("🔧  En maintenance", "0", _C_MAINT),
            ("📏  Km moyen", "0", _C_LOG),
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
        total = len(self._data)
        actifs = sum(1 for v in self._data if v.get("statut") == "Actif")
        maint = sum(1 for v in self._data if v.get("statut") == "En maintenance")
        kms = [float(v.get("kilometrage") or 0) for v in self._data if v.get("kilometrage")]
        km_moy = f"{sum(kms) / len(kms):,.0f}".replace(",", " ") if kms else "0"
        for i, val in enumerate([str(total), str(actifs), str(maint), km_moy]):
            self._kpi_labels[i].configure(text=val)

    def _build_toolbar(self, parent):
        bar = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD, corner_radius=0,
                           height=50, border_width=1, border_color=Colors.DIVIDER)
        bar.grid(row=1, column=0, sticky="ew", padx=14)
        bar.grid_columnconfigure(4, weight=1)
        bar.grid_propagate(False)

        btns = [
            ("➕  Ajouter", _C_LOG, _C_LOG_H, self._open_add),
            ("✏️  Modifier", "#2980B9", "#1A6B9A", self._open_edit),
            ("🗑️  Supprimer", "#E74C3C", "#C0392B", self._delete),
        ]
        for col, (txt, fg, hv, cmd) in enumerate(btns):
            ctk.CTkButton(bar, text=txt, fg_color=fg, hover_color=hv,
                          font=_F(11, "bold"), height=34, width=110,
                          corner_radius=7, command=cmd
                          ).grid(row=0, column=col,
                                 padx=(8 if col == 0 else 3, 3), pady=8)

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_filter())
        ctk.CTkEntry(bar, textvariable=self._search_var,
                     placeholder_text="🔍  Rechercher (immat., marque, chauffeur…)",
                     font=_F(11), height=34, corner_radius=7
                     ).grid(row=0, column=3, padx=(10, 6), pady=8, sticky="ew")

        statut_opts = ["Tous"] + _STATUTS
        self._filter_statut = ctk.StringVar(value="Tous")
        ctk.CTkComboBox(bar, values=statut_opts, variable=self._filter_statut,
                        command=lambda _: self._apply_filter(),
                        font=_F(11), height=34, width=130, corner_radius=7
                        ).grid(row=0, column=4, padx=(0, 4), pady=8)

        ctk.CTkButton(bar, text="🔄", fg_color="#95A5A6", hover_color="#7F8C8D",
                      font=_F(13), height=34, width=40, corner_radius=7,
                      command=self._load_data
                      ).grid(row=0, column=5, padx=(0, 8), pady=8)

    def _build_table(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD, corner_radius=0,
                             border_width=1, border_color=Colors.DIVIDER)
        frame.grid(row=2, column=0, sticky="nsew", padx=14)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Veh.Treeview",
                        background=_C_ROW_EVEN, foreground=Colors.MIDNIGHT,
                        rowheight=28, fieldbackground=_C_ROW_EVEN,
                        font=("Segoe UI", 10), borderwidth=0)
        style.configure("Veh.Treeview.Heading",
                        background=_C_HEADER, foreground="#FFFFFF",
                        font=("Segoe UI", 10, "bold"), relief="flat", padding=5)
        style.map("Veh.Treeview",
                  background=[("selected", _C_LOG)],
                  foreground=[("selected", "#FFFFFF")])

        cols = tuple(c[0] for c in self._COLS)
        self._tree = ttk.Treeview(frame, columns=cols, show="headings",
                                  style="Veh.Treeview", selectmode="browse")
        for label, _, width, anchor in self._COLS:
            self._tree.heading(label, text=label)
            self._tree.column(label, width=width, anchor=anchor, minwidth=30)

        self._tree.tag_configure("odd", background=_C_ROW_ODD)
        self._tree.tag_configure("even", background=_C_ROW_EVEN)
        self._tree.tag_configure("actif", foreground=_C_ACTIF)
        self._tree.tag_configure("inactif", foreground=_C_INACTIF)
        self._tree.tag_configure("maint", foreground=_C_MAINT)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
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

    def _load_data(self):
        self._data.clear()
        if self.db_conn:
            try:
                cur = self.db_conn.cursor()
                cur.execute("""
                    SELECT id, immatriculation, marque, modele, type_vehicule,
                           annee, kilometrage, carburant, chauffeur, statut
                    FROM logistique_vehicule ORDER BY immatriculation ASC
                """)
                cols = [d[0] for d in cur.description]
                for row in cur.fetchall():
                    self._data.append(dict(zip(cols, row)))
                cur.close()
            except Exception as e:
                print(f"[ParcVehicule] _load_data: {e}")
        else:
            self._data = self._demo_data()

        self._apply_filter()
        self._update_kpis()
        self._status_lbl.configure(
            text=f"✅  {len(self._data)} véhicule(s)  —  "
                 f"Mise à jour : {datetime.now().strftime('%H:%M:%S')}")

    @staticmethod
    def _demo_data() -> list[dict]:
        return [
            {"id": 1, "immatriculation": "1234 TAA", "marque": "Toyota", "modele": "Hilux",
             "type_vehicule": "Camionnette", "annee": 2020, "kilometrage": 45200,
             "carburant": "Diesel", "chauffeur": "Rakoto J.", "statut": "Actif"},
            {"id": 2, "immatriculation": "5678 TBB", "marque": "Mitsubishi", "modele": "L200",
             "type_vehicule": "Camionnette", "annee": 2019, "kilometrage": 67800,
             "carburant": "Diesel", "chauffeur": "Andry M.", "statut": "En maintenance"},
            {"id": 3, "immatriculation": "9012 TCC", "marque": "Peugeot", "modele": "Partner",
             "type_vehicule": "Voiture", "annee": 2021, "kilometrage": 23100,
             "carburant": "Diesel", "chauffeur": "", "statut": "Actif"},
        ]

    def _apply_filter(self, *_):
        q = self._search_var.get().lower().strip()
        statut = self._filter_statut.get()
        self._filtered = [
            v for v in self._data
            if (statut == "Tous" or v.get("statut") == statut)
            and (not q or any(
                q in str(v.get(col, "")).lower()
                for col in ("immatriculation", "marque", "modele", "chauffeur", "type_vehicule")
            ))
        ]
        self._refresh_tree()

    def _refresh_tree(self):
        self._tree.delete(*self._tree.get_children())
        for i, v in enumerate(self._filtered):
            statut = v.get("statut", "")
            if statut == "Actif":
                tag_stat = "actif"
            elif statut == "En maintenance":
                tag_stat = "maint"
            else:
                tag_stat = "inactif"

            km = v.get("kilometrage")
            km_str = f"{float(km):,.0f}".replace(",", " ") if km is not None else "—"

            values = (
                v.get("id", ""),
                v.get("immatriculation", ""),
                v.get("marque", ""),
                v.get("modele", ""),
                v.get("type_vehicule", ""),
                v.get("annee", ""),
                km_str,
                v.get("carburant", ""),
                v.get("chauffeur", ""),
                statut,
            )
            row_tag = "odd" if i % 2 else "even"
            self._tree.insert("", "end", iid=str(v.get("id", i)),
                              values=values, tags=(row_tag, tag_stat))

        self._status_lbl.configure(
            text=f"✅  {len(self._filtered)} véhicule(s) affiché(s)  sur  {len(self._data)} au total")

    def _on_select(self, _=None):
        sel = self._tree.selection()
        self._selected_id = int(sel[0]) if sel else None

    def _get_selected(self) -> Optional[dict]:
        if self._selected_id is None:
            messagebox.showwarning("Aucune sélection",
                                   "Veuillez sélectionner un véhicule.", parent=self)
            return None
        return next((v for v in self._data if v.get("id") == self._selected_id), None)

    def _open_add(self):
        FormVehicule(self, self.db_conn, on_save=lambda _: self._load_data())

    def _open_edit(self):
        v = self._get_selected()
        if not v:
            return
        full = self._fetch_full(v["id"]) or v
        FormVehicule(self, self.db_conn, vehicule=full, on_save=lambda _: self._load_data())

    def _fetch_full(self, vid: int) -> Optional[dict]:
        if not self.db_conn:
            return None
        try:
            cur = self.db_conn.cursor()
            cur.execute("SELECT * FROM logistique_vehicule WHERE id=%s", (vid,))
            row = cur.fetchone()
            cols = [d[0] for d in cur.description]
            cur.close()
            return dict(zip(cols, row)) if row else None
        except Exception:
            return None

    def _delete(self):
        v = self._get_selected()
        if not v:
            return
        immat = v.get("immatriculation", "ce véhicule")
        if not messagebox.askyesno("Confirmation",
                                   f"Supprimer le véhicule {immat} ?",
                                   parent=self):
            return

        if not self.db_conn:
            self._data = [d for d in self._data if d.get("id") != v["id"]]
            self._apply_filter()
            self._update_kpis()
            return

        try:
            cur = self.db_conn.cursor()
            cur.execute("DELETE FROM logistique_vehicule WHERE id=%s", (v["id"],))
            self.db_conn.commit()
            cur.close()
            messagebox.showinfo("Succès", f"Véhicule {immat} supprimé.", parent=self)
            self._load_data()
        except Exception as e:
            try:
                self.db_conn.rollback()
            except Exception:
                pass
            messagebox.showerror("Erreur DB", str(e), parent=self)


if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    root.title("iJeery V5.0 — Test Parc Véhicule")
    root.geometry("1200x700")
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    PageParcVehicule(master=root, db_conn=None).grid(row=0, column=0, sticky="nsew")
    root.mainloop()
