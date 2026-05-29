# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           iJeery V5.0 — page_piecesDetachees.py                            ║
║           Module LOGISTIQUE › Pièces Détachées                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Fonctionnalités :                                                           ║
║   • Catalogue des pièces avec stock en temps réel                           ║
║   • Entrées / Sorties de stock avec historique                              ║
║   • Alertes stock minimum (seuil configurable)                              ║
║   • Association pièce ↔ véhicule / marque                                  ║
║   • KPI : total pièces, valeur stock, alertes, sorties du mois              ║
║   • Connexion PostgreSQL via db_conn                                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional
from datetime import datetime

import customtkinter as ctk

# ── Thème ─────────────────────────────────────────────────────────────────────
try:
    from app_theme import Colors, Fonts
except ImportError:
    class Colors:
        BG_PAGE        = "#ECF0F1"
        BG_CARD        = "#FFFFFF"
        MIDNIGHT       = "#2C3E50"
        TEXT_MUTED     = "#95A5A6"
        DIVIDER        = "#E8EAED"
    class Fonts:
        pass

def _F(size=11, weight="normal"):
    return ctk.CTkFont(family="Segoe UI", size=size, weight=weight)

# ── Couleurs module ───────────────────────────────────────────────────────────
_C_LOG       = "#1A6B3C"
_C_LOG_H     = "#27AE60"
_C_HEADER    = "#2C3E50"
_C_ALERTE    = "#E74C3C"
_C_OK        = "#27AE60"
_C_WARN      = "#E67E22"
_C_ROW_ODD   = "#F7F9FC"
_C_ROW_EVEN  = "#FFFFFF"


# ─────────────────────────────────────────────────────────────────────────────
# FORMULAIRE PIÈCE
# ─────────────────────────────────────────────────────────────────────────────

class FormPiece(ctk.CTkToplevel):
    """Ajout ou modification d'une pièce détachée."""

    CATEGORIES = ["Moteur", "Transmission", "Freinage", "Suspension",
                  "Électrique", "Carrosserie", "Filtres", "Pneus", "Autre"]

    def __init__(self, master, db_conn, piece: Optional[dict] = None,
                 on_save: Optional[callable] = None):
        super().__init__(master)
        self.db_conn  = db_conn
        self.piece    = piece
        self.on_save  = on_save
        self._mode    = "Modifier" if piece else "Ajouter"

        self.title(f"{self._mode} une Pièce — iJeery Logistique")
        self.geometry("500x660")
        self.resizable(False, False)
        self.grab_set()
        self.focus_force()
        self._build()
        if piece:
            self._populate(piece)

    def _build(self):
        ctk.CTkLabel(self, text=f"🔩  {self._mode} une Pièce Détachée",
                     font=_F(15, "bold"), text_color=_C_LOG
                     ).pack(pady=(16, 2), padx=22, anchor="w")
        ctk.CTkLabel(self, text="Renseignez les informations de la pièce.",
                     font=_F(10), text_color=Colors.TEXT_MUTED
                     ).pack(padx=22, anchor="w")
        ctk.CTkFrame(self, height=1, fg_color=Colors.DIVIDER
                     ).pack(fill="x", padx=22, pady=(8, 12))

        sc = ctk.CTkScrollableFrame(self, fg_color="transparent")
        sc.pack(fill="both", expand=True, padx=14)

        self._vars = {}
        fields = [
            ("Référence *",         "reference",      "entry", None),
            ("Désignation *",       "designation",    "entry", None),
            ("Catégorie",           "categorie",      "combo", self.CATEGORIES),
            ("Marque véhicule",     "marque_vehicule","entry", None),
            ("Fournisseur",         "fournisseur",    "entry", None),
            ("Quantité en stock",   "quantite",       "entry", None),
            ("Seuil alerte min.",   "seuil_alerte",   "entry", None),
            ("Prix unitaire (Ar)",  "prix_unitaire",  "entry", None),
            ("Emplacement / Rayon", "emplacement",    "entry", None),
            ("Notes",               "notes",          "textbox", None),
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
                                font=_F(11), height=32
                                ).pack(fill="x", padx=6)
                self._vars[key] = var
            elif wtype == "textbox":
                tb = ctk.CTkTextbox(sc, font=_F(11), height=60)
                tb.pack(fill="x", padx=6)
                self._vars[key] = tb

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

    def _populate(self, p: dict):
        for key, var in self._vars.items():
            val = p.get(key, "")
            if isinstance(var, ctk.CTkTextbox):
                var.delete("1.0", "end")
                var.insert("1.0", str(val) if val else "")
            else:
                var.set(str(val) if val else "")

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
        if not data.get("reference"):
            messagebox.showerror("Erreur", "La référence est obligatoire.", parent=self)
            return
        if not data.get("designation"):
            messagebox.showerror("Erreur", "La désignation est obligatoire.", parent=self)
            return

        def to_int(v, default=0):
            try: return int(v) if v else default
            except: return default

        def to_float(v):
            try: return float(str(v).replace(",", ".")) if v else None
            except: return None

        if not self.db_conn:
            messagebox.showwarning("Mode démo",
                "Base non connectée — enregistrement simulé.", parent=self)
            if self.on_save: self.on_save(data)
            self.destroy()
            return

        try:
            cur = self.db_conn.cursor()
            if self.piece:
                cur.execute("""
                    UPDATE logistique_piece
                    SET reference=%s, designation=%s, categorie=%s,
                        marque_vehicule=%s, fournisseur=%s, quantite=%s,
                        seuil_alerte=%s, prix_unitaire=%s, emplacement=%s,
                        notes=%s, updated_at=NOW()
                    WHERE id=%s
                """, (data["reference"], data["designation"], data["categorie"],
                      data["marque_vehicule"], data["fournisseur"],
                      to_int(data["quantite"]), to_int(data["seuil_alerte"], 2),
                      to_float(data["prix_unitaire"]),
                      data["emplacement"], data["notes"], self.piece["id"]))
            else:
                cur.execute("""
                    INSERT INTO logistique_piece
                        (reference, designation, categorie, marque_vehicule,
                         fournisseur, quantite, seuil_alerte, prix_unitaire,
                         emplacement, notes, created_at, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW())
                """, (data["reference"], data["designation"], data["categorie"],
                      data["marque_vehicule"], data["fournisseur"],
                      to_int(data["quantite"]), to_int(data["seuil_alerte"], 2),
                      to_float(data["prix_unitaire"]),
                      data["emplacement"], data["notes"]))
            self.db_conn.commit()
            cur.close()
            messagebox.showinfo("Succès", "Pièce enregistrée.", parent=self)
            if self.on_save: self.on_save(data)
            self.destroy()
        except Exception as e:
            try: self.db_conn.rollback()
            except: pass
            messagebox.showerror("Erreur DB", str(e), parent=self)


# ─────────────────────────────────────────────────────────────────────────────
# FORMULAIRE MOUVEMENT (Entrée / Sortie de stock)
# ─────────────────────────────────────────────────────────────────────────────

class FormMouvement(ctk.CTkToplevel):
    """Enregistrement d'une entrée ou sortie de stock."""

    def __init__(self, master, db_conn, piece: dict,
                 type_mvt: str = "Entrée", on_save: Optional[callable] = None):
        super().__init__(master)
        self.db_conn  = db_conn
        self.piece    = piece
        self.type_mvt = type_mvt
        self.on_save  = on_save

        emoji = "📥" if type_mvt == "Entrée" else "📤"
        self.title(f"{emoji} {type_mvt} de stock — {piece.get('reference','')}")
        self.geometry("420x420")
        self.resizable(False, False)
        self.grab_set()
        self.focus_force()
        self._build()

    def _build(self):
        color = _C_OK if self.type_mvt == "Entrée" else _C_WARN
        emoji = "📥" if self.type_mvt == "Entrée" else "📤"

        ctk.CTkLabel(self,
                     text=f"{emoji}  {self.type_mvt} de stock",
                     font=_F(15, "bold"), text_color=color
                     ).pack(pady=(16, 2), padx=22, anchor="w")
        ctk.CTkLabel(self,
                     text=f"Pièce : {self.piece.get('designation','')}  "
                          f"[ Réf. {self.piece.get('reference','')} ]",
                     font=_F(10), text_color=Colors.TEXT_MUTED
                     ).pack(padx=22, anchor="w")
        ctk.CTkLabel(self,
                     text=f"Stock actuel : {self.piece.get('quantite', 0)} unité(s)",
                     font=_F(11, "bold"), text_color=Colors.MIDNIGHT
                     ).pack(padx=22, pady=(4, 0), anchor="w")
        ctk.CTkFrame(self, height=1, fg_color=Colors.DIVIDER
                     ).pack(fill="x", padx=22, pady=(10, 14))

        self._vars = {}
        fields = [
            ("Quantité *",        "quantite",    "entry"),
            ("Référence document","ref_doc",      "entry"),
            ("Véhicule concerné", "vehicule",    "entry"),
            ("Motif / Description","motif",       "entry"),
        ]
        for label, key, _ in fields:
            ctk.CTkLabel(self, text=label, font=_F(10, "bold"),
                         text_color=Colors.MIDNIGHT, anchor="w"
                         ).pack(fill="x", padx=22, pady=(6, 1))
            var = ctk.StringVar()
            ctk.CTkEntry(self, textvariable=var, font=_F(11), height=32,
                         placeholder_text=label.replace(" *", "")
                         ).pack(fill="x", padx=22)
            self._vars[key] = var

        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(fill="x", padx=22, pady=(16, 14))
        ctk.CTkButton(bf, text=f"✅  Confirmer {self.type_mvt}",
                      fg_color=color,
                      hover_color=_C_LOG_H if self.type_mvt == "Entrée" else "#C0392B",
                      font=_F(12, "bold"), height=38, corner_radius=8,
                      command=self._save
                      ).pack(side="left", expand=True, padx=(0, 5))
        ctk.CTkButton(bf, text="✕  Annuler",
                      fg_color="#95A5A6", hover_color="#7F8C8D",
                      font=_F(12), height=38, corner_radius=8,
                      command=self.destroy
                      ).pack(side="left", expand=True, padx=(5, 0))

    def _save(self):
        try:
            qte = int(self._vars["quantite"].get().strip())
            if qte <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erreur", "Quantité invalide (entier > 0).", parent=self)
            return

        ref_doc = self._vars["ref_doc"].get().strip()
        vehicule = self._vars["vehicule"].get().strip()
        motif    = self._vars["motif"].get().strip()

        if not self.db_conn:
            messagebox.showwarning("Mode démo",
                f"Simulation : {self.type_mvt} de {qte} unité(s).", parent=self)
            if self.on_save: self.on_save()
            self.destroy()
            return

        try:
            cur = self.db_conn.cursor()
            # Insérer le mouvement
            cur.execute("""
                INSERT INTO logistique_piece_mouvement
                    (piece_id, type_mouvement, quantite, ref_document,
                     vehicule, motif, date_mouvement, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (self.piece["id"], self.type_mvt, qte,
                  ref_doc or None, vehicule or None, motif or None))

            # Mettre à jour le stock
            if self.type_mvt == "Entrée":
                cur.execute("""
                    UPDATE logistique_piece
                    SET quantite = quantite + %s, updated_at = NOW()
                    WHERE id = %s
                """, (qte, self.piece["id"]))
            else:
                # Vérifier stock suffisant
                cur.execute("SELECT quantite FROM logistique_piece WHERE id=%s",
                            (self.piece["id"],))
                stock_actuel = cur.fetchone()[0]
                if stock_actuel < qte:
                    cur.close()
                    self.db_conn.rollback()
                    messagebox.showerror("Stock insuffisant",
                        f"Stock disponible : {stock_actuel} unité(s) seulement.",
                        parent=self)
                    return
                cur.execute("""
                    UPDATE logistique_piece
                    SET quantite = quantite - %s, updated_at = NOW()
                    WHERE id = %s
                """, (qte, self.piece["id"]))

            self.db_conn.commit()
            cur.close()
            messagebox.showinfo("Succès",
                f"{self.type_mvt} de {qte} unité(s) enregistrée.", parent=self)
            if self.on_save: self.on_save()
            self.destroy()
        except Exception as e:
            try: self.db_conn.rollback()
            except: pass
            messagebox.showerror("Erreur DB", str(e), parent=self)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE PRINCIPALE : PIÈCES DÉTACHÉES
# ─────────────────────────────────────────────────────────────────────────────

class PagePiecesDetachees(ctk.CTkFrame):
    """
    Page principale du module Pièces Détachées.
    Signature : PagePiecesDetachees(master, db_conn, session_data)
    """

    _SQL_CREATE_PIECE = """
        CREATE TABLE IF NOT EXISTS logistique_piece (
            id              SERIAL PRIMARY KEY,
            reference       VARCHAR(40) UNIQUE NOT NULL,
            designation     VARCHAR(120) NOT NULL,
            categorie       VARCHAR(40) DEFAULT 'Autre',
            marque_vehicule VARCHAR(60),
            fournisseur     VARCHAR(80),
            quantite        INTEGER DEFAULT 0,
            seuil_alerte    INTEGER DEFAULT 2,
            prix_unitaire   NUMERIC(12,2),
            emplacement     VARCHAR(80),
            notes           TEXT,
            created_at      TIMESTAMP DEFAULT NOW(),
            updated_at      TIMESTAMP DEFAULT NOW()
        );
    """

    _SQL_CREATE_MVT = """
        CREATE TABLE IF NOT EXISTS logistique_piece_mouvement (
            id              SERIAL PRIMARY KEY,
            piece_id        INTEGER REFERENCES logistique_piece(id) ON DELETE CASCADE,
            type_mouvement  VARCHAR(10) NOT NULL,
            quantite        INTEGER NOT NULL,
            ref_document    VARCHAR(60),
            vehicule        VARCHAR(80),
            motif           TEXT,
            date_mouvement  TIMESTAMP DEFAULT NOW(),
            created_at      TIMESTAMP DEFAULT NOW()
        );
    """

    _COLS = [
        ("ID",           "id",              45,  "center"),
        ("Référence",    "reference",        100, "w"),
        ("Désignation",  "designation",      160, "w"),
        ("Catégorie",    "categorie",         90, "center"),
        ("Marque Veh.",  "marque_vehicule",   90, "w"),
        ("Fournisseur",  "fournisseur",       100, "w"),
        ("Stock",        "quantite",          55, "center"),
        ("Seuil Mini",   "seuil_alerte",      70, "center"),
        ("Prix Unit.",   "prix_unitaire",      80, "e"),
        ("Emplacement",  "emplacement",        90, "w"),
        ("État Stock",   "_etat",              90, "center"),
    ]

    def __init__(self, master, db_conn=None, session_data=None, **kw):
        super().__init__(master, fg_color=Colors.BG_PAGE, corner_radius=0, **kw)
        self.db_conn      = db_conn
        self.session_data = session_data or {}
        self._data: list[dict]     = []
        self._filtered: list[dict] = []
        self._selected_id: Optional[int] = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._ensure_tables()
        self._build_header()
        self._build_body()
        self._load_data()

    def _ensure_tables(self):
        if not self.db_conn: return
        try:
            cur = self.db_conn.cursor()
            cur.execute(self._SQL_CREATE_PIECE)
            cur.execute(self._SQL_CREATE_MVT)
            self.db_conn.commit()
            cur.close()
        except Exception as e:
            print(f"[PiecesDetachees] _ensure_tables: {e}")
            try: self.db_conn.rollback()
            except: pass

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=_C_HEADER, corner_radius=0, height=56)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(1, weight=1)
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="🔩  Pièces Détachées",
                     font=_F(17, "bold"), text_color="#FFFFFF"
                     ).grid(row=0, column=0, padx=18, pady=14, sticky="w")
        ctk.CTkLabel(hdr, text="LOGISTIQUE  ›  Pièces Détachées",
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
            ("🔩  Total Références", "0", "#3498DB"),
            ("⚠️  En Alerte Stock",  "0", _C_ALERTE),
            ("💰  Valeur Stock",      "0 Ar", _C_LOG),
            ("📤  Sorties ce mois",  "0", _C_WARN),
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
        total  = len(self._data)
        alerte = sum(1 for p in self._data
                     if (p.get("quantite") or 0) <= (p.get("seuil_alerte") or 0))
        valeur = sum((p.get("quantite") or 0) * float(p.get("prix_unitaire") or 0)
                     for p in self._data)
        # Sorties du mois depuis DB
        sorties = self._fetch_sorties_mois()
        for i, val in enumerate([str(total),
                                  str(alerte),
                                  f"{valeur:,.0f} Ar".replace(",", " "),
                                  str(sorties)]):
            self._kpi_labels[i].configure(text=val)

    def _fetch_sorties_mois(self) -> int:
        if not self.db_conn: return 0
        try:
            cur = self.db_conn.cursor()
            cur.execute("""
                SELECT COALESCE(SUM(quantite), 0)
                FROM logistique_piece_mouvement
                WHERE type_mouvement = 'Sortie'
                  AND date_trunc('month', date_mouvement) = date_trunc('month', NOW())
            """)
            val = cur.fetchone()[0]
            cur.close()
            return int(val)
        except Exception:
            return 0

    # ── Toolbar ───────────────────────────────────────────────────────────────

    def _build_toolbar(self, parent):
        bar = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD, corner_radius=0,
                           height=50, border_width=1, border_color=Colors.DIVIDER)
        bar.grid(row=1, column=0, sticky="ew", padx=14)
        bar.grid_columnconfigure(5, weight=1)
        bar.grid_propagate(False)

        btns = [
            ("➕  Ajouter",    _C_LOG,    _C_LOG_H,  self._open_add),
            ("✏️  Modifier",   "#2980B9", "#1A6B9A",  self._open_edit),
            ("🗑️  Supprimer",  "#E74C3C", "#C0392B",  self._delete),
            ("📥  Entrée",     _C_OK,     "#1E8449",  self._open_entree),
            ("📤  Sortie",     _C_WARN,   "#D35400",  self._open_sortie),
        ]
        for col, (txt, fg, hv, cmd) in enumerate(btns):
            ctk.CTkButton(bar, text=txt, fg_color=fg, hover_color=hv,
                          font=_F(11, "bold"), height=34, width=100,
                          corner_radius=7, command=cmd
                          ).grid(row=0, column=col, padx=(8 if col == 0 else 3, 3),
                                 pady=8)

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_filter())
        ctk.CTkEntry(bar, textvariable=self._search_var,
                     placeholder_text="🔍  Rechercher (référence, désignation, catégorie…)",
                     font=_F(11), height=34, corner_radius=7
                     ).grid(row=0, column=5, padx=(10, 6), pady=8, sticky="ew")

        self._filter_alerte = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(bar, text="⚠️ Alertes seules",
                        variable=self._filter_alerte,
                        command=self._apply_filter,
                        font=_F(10)
                        ).grid(row=0, column=6, padx=6, pady=8)

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
        style.configure("Piece.Treeview",
                        background=_C_ROW_EVEN, foreground=Colors.MIDNIGHT,
                        rowheight=28, fieldbackground=_C_ROW_EVEN,
                        font=("Segoe UI", 10), borderwidth=0)
        style.configure("Piece.Treeview.Heading",
                        background=_C_HEADER, foreground="#FFFFFF",
                        font=("Segoe UI", 10, "bold"), relief="flat", padding=5)
        style.map("Piece.Treeview",
                  background=[("selected", "#2980B9")],
                  foreground=[("selected", "#FFFFFF")])

        cols = tuple(c[0] for c in self._COLS)
        self._tree = ttk.Treeview(frame, columns=cols, show="headings",
                                   style="Piece.Treeview", selectmode="browse")
        for label, _, width, anchor in self._COLS:
            self._tree.heading(label, text=label,
                               command=lambda c=label: self._sort_by(c))
            self._tree.column(label, width=width, anchor=anchor, minwidth=30)

        self._tree.tag_configure("odd",    background=_C_ROW_ODD)
        self._tree.tag_configure("even",   background=_C_ROW_EVEN)
        self._tree.tag_configure("alerte", foreground=_C_ALERTE)
        self._tree.tag_configure("ok",     foreground=_C_OK)
        self._tree.tag_configure("warn",   foreground=_C_WARN)

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
                    SELECT id, reference, designation, categorie, marque_vehicule,
                           fournisseur, quantite, seuil_alerte, prix_unitaire, emplacement
                    FROM logistique_piece ORDER BY designation ASC
                """)
                cols = [d[0] for d in cur.description]
                for row in cur.fetchall():
                    self._data.append(dict(zip(cols, row)))
                cur.close()
            except Exception as e:
                print(f"[PiecesDetachees] _load_data: {e}")
        else:
            self._data = self._demo_data()

        self._apply_filter()
        self._update_kpis()
        self._status_lbl.configure(
            text=f"✅  {len(self._data)} référence(s)  —  "
                 f"Mise à jour : {datetime.now().strftime('%H:%M:%S')}")

    @staticmethod
    def _demo_data() -> list[dict]:
        return [
            {"id": 1, "reference": "FLT-001", "designation": "Filtre à huile Toyota",
             "categorie": "Filtres", "marque_vehicule": "Toyota", "fournisseur": "Pièces Auto MG",
             "quantite": 8, "seuil_alerte": 3, "prix_unitaire": 25000, "emplacement": "R1-A"},
            {"id": 2, "reference": "PLQ-002", "designation": "Plaquettes de frein avant",
             "categorie": "Freinage", "marque_vehicule": "Mitsubishi", "fournisseur": "AutoParts",
             "quantite": 2, "seuil_alerte": 4, "prix_unitaire": 85000, "emplacement": "R2-B"},
            {"id": 3, "reference": "BAT-003", "designation": "Batterie 12V 70Ah",
             "categorie": "Électrique", "marque_vehicule": "Tout", "fournisseur": "Elec Store",
             "quantite": 1, "seuil_alerte": 2, "prix_unitaire": 350000, "emplacement": "R3-A"},
            {"id": 4, "reference": "HUI-004", "designation": "Huile moteur 5W40 (5L)",
             "categorie": "Moteur", "marque_vehicule": "Tout", "fournisseur": "Lubrifiant MG",
             "quantite": 15, "seuil_alerte": 5, "prix_unitaire": 62000, "emplacement": "R1-C"},
            {"id": 5, "reference": "CNR-005", "designation": "Courroie de distribution",
             "categorie": "Moteur", "marque_vehicule": "Ford", "fournisseur": "Ford Parts",
             "quantite": 0, "seuil_alerte": 1, "prix_unitaire": 145000, "emplacement": "R2-A"},
        ]

    def _apply_filter(self, *_):
        q       = self._search_var.get().lower().strip()
        alerte  = self._filter_alerte.get()
        self._filtered = [
            p for p in self._data
            if (not alerte or (p.get("quantite") or 0) <= (p.get("seuil_alerte") or 0))
            and (not q or any(
                q in str(p.get(col, "")).lower()
                for col in ("reference", "designation", "categorie",
                            "marque_vehicule", "fournisseur", "emplacement")
            ))
        ]
        self._refresh_tree()

    def _refresh_tree(self):
        self._tree.delete(*self._tree.get_children())
        for i, p in enumerate(self._filtered):
            qte    = p.get("quantite") or 0
            seuil  = p.get("seuil_alerte") or 0
            if qte == 0:
                etat = "⛔ Rupture"; tag_etat = "alerte"
            elif qte <= seuil:
                etat = "⚠️ Alerte"; tag_etat = "alerte"
            elif qte <= seuil * 2:
                etat = "🔶 Faible";  tag_etat = "warn"
            else:
                etat = "✅ Normal"; tag_etat = "ok"

            prix = p.get("prix_unitaire")
            prix_str = f"{float(prix):,.0f}".replace(",", " ") if prix else "—"

            values = (
                p.get("id", ""),
                p.get("reference", ""),
                p.get("designation", ""),
                p.get("categorie", ""),
                p.get("marque_vehicule", ""),
                p.get("fournisseur", ""),
                qte,
                seuil,
                prix_str,
                p.get("emplacement", ""),
                etat,
            )
            row_tag = "odd" if i % 2 else "even"
            self._tree.insert("", "end", iid=str(p.get("id", i)),
                               values=values, tags=(row_tag, tag_etat))

        self._status_lbl.configure(
            text=f"✅  {len(self._filtered)} pièce(s) affichée(s)  sur  {len(self._data)} au total")

    _sort_reverse: dict = {}

    def _sort_by(self, col_label: str):
        col_key = next((c[1] for c in self._COLS if c[0] == col_label), None)
        if not col_key: return
        rev = self._sort_reverse.get(col_label, False)
        self._filtered.sort(key=lambda p: (p.get(col_key) or ""), reverse=rev)
        self._sort_reverse[col_label] = not rev
        self._refresh_tree()

    def _on_select(self, _=None):
        sel = self._tree.selection()
        self._selected_id = int(sel[0]) if sel else None

    def _get_selected(self) -> Optional[dict]:
        if self._selected_id is None:
            messagebox.showwarning("Aucune sélection",
                "Veuillez sélectionner une pièce.", parent=self)
            return None
        return next((p for p in self._data if p.get("id") == self._selected_id), None)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def _open_add(self):
        FormPiece(self, self.db_conn, on_save=lambda _: self._load_data())

    def _open_edit(self):
        p = self._get_selected()
        if not p: return
        full = self._fetch_full(p["id"]) or p
        FormPiece(self, self.db_conn, piece=full, on_save=lambda _: self._load_data())

    def _fetch_full(self, pid: int) -> Optional[dict]:
        if not self.db_conn: return None
        try:
            cur = self.db_conn.cursor()
            cur.execute("SELECT * FROM logistique_piece WHERE id=%s", (pid,))
            row = cur.fetchone()
            cols = [d[0] for d in cur.description]
            cur.close()
            return dict(zip(cols, row)) if row else None
        except: return None

    def _delete(self):
        p = self._get_selected()
        if not p: return
        ref = p.get("reference", "cette pièce")
        if not messagebox.askyesno("Confirmation",
            f"Supprimer la pièce {ref} ?\n\nL'historique des mouvements sera aussi supprimé.",
            parent=self): return

        if not self.db_conn:
            self._data = [d for d in self._data if d.get("id") != p["id"]]
            self._apply_filter(); self._update_kpis()
            return

        try:
            cur = self.db_conn.cursor()
            cur.execute("DELETE FROM logistique_piece WHERE id=%s", (p["id"],))
            self.db_conn.commit(); cur.close()
            messagebox.showinfo("Succès", f"Pièce {ref} supprimée.", parent=self)
            self._load_data()
        except Exception as e:
            try: self.db_conn.rollback()
            except: pass
            messagebox.showerror("Erreur DB", str(e), parent=self)

    def _open_entree(self):
        p = self._get_selected()
        if not p: return
        FormMouvement(self, self.db_conn, p, "Entrée",
                      on_save=self._load_data)

    def _open_sortie(self):
        p = self._get_selected()
        if not p: return
        FormMouvement(self, self.db_conn, p, "Sortie",
                      on_save=self._load_data)


# ─────────────────────────────────────────────────────────────────────────────
# TEST STANDALONE
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    root.title("iJeery V5.0 — Test Pièces Détachées")
    root.geometry("1200x700")
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    PagePiecesDetachees(master=root, db_conn=None).grid(row=0, column=0, sticky="nsew")
    root.mainloop()


