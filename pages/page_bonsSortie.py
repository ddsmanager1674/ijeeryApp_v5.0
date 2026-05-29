# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           iJeery V5.0 — page_bonsSortie.py                                 ║
║           Module LOGISTIQUE › Bons de Sortie                                ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Fonctionnalités :                                                           ║
║   • Création de bons de sortie véhicule (matériel, carburant, mission)      ║
║   • Numérotation automatique BS-AAAA-NNNN                                   ║
║   • Statuts : Brouillon → Validé → Clôturé → Annulé                        ║
║   • Impression / aperçu du bon de sortie formaté                            ║
║   • Lignes articles (désignation, qté, unité) par bon                       ║
║   • KPI : bons du mois, validés, en brouillon, valeur totale                ║
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
_C_BROUILLON = "#95A5A6"
_C_VALIDE    = "#3498DB"
_C_CLOTURE   = _C_LOG
_C_ANNULE    = "#E74C3C"
_C_ROW_ODD   = "#F7F9FC"
_C_ROW_EVEN  = "#FFFFFF"

_STATUTS     = ["Brouillon", "Validé", "Clôturé", "Annulé"]
_TYPES_BON   = ["Sortie Matériel", "Sortie Carburant", "Sortie Pièces",
                "Mission Véhicule", "Livraison", "Autre"]

_STATUT_COLORS = {
    "Brouillon": _C_BROUILLON,
    "Validé":    _C_VALIDE,
    "Clôturé":   _C_CLOTURE,
    "Annulé":    _C_ANNULE,
}


# ─────────────────────────────────────────────────────────────────────────────
# APERÇU / IMPRESSION BON DE SORTIE
# ─────────────────────────────────────────────────────────────────────────────

class ApercuBon(ctk.CTkToplevel):
    """Affichage formaté du bon de sortie (prêt à imprimer)."""

    def __init__(self, master, bon: dict, lignes: list):
        super().__init__(master)
        self.title(f"📋  Bon de Sortie {bon.get('numero_bon','')}")
        self.geometry("520x680")
        self.resizable(False, False)
        self.grab_set()

        statut = bon.get("statut", "")
        color  = _STATUT_COLORS.get(statut, Colors.MIDNIGHT)

        # ── En-tête ───────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=_C_HEADER, corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text="📋  BON DE SORTIE",
                     font=_F(15, "bold"), text_color="#FFFFFF"
                     ).pack(padx=18, pady=(12, 2), anchor="w")
        ctk.CTkLabel(hdr,
                     text=f"{bon.get('numero_bon','—')}  —  "
                          f"Émis le {self._fmt_date(bon.get('date_bon'))}",
                     font=_F(10), text_color="#BDC3C7"
                     ).pack(padx=18, pady=(0, 12), anchor="w")

        sc = ctk.CTkScrollableFrame(self, fg_color=Colors.BG_PAGE)
        sc.pack(fill="both", expand=True)

        def section(title, fg):
            ctk.CTkLabel(sc, text=title, font=_F(11, "bold"),
                         text_color=fg
                         ).pack(padx=14, pady=(14, 4), anchor="w")

        def row(label, value, bold=False):
            fr = ctk.CTkFrame(sc, fg_color=Colors.BG_CARD, corner_radius=6,
                              border_width=1, border_color=Colors.DIVIDER)
            fr.pack(fill="x", padx=14, pady=2)
            ctk.CTkLabel(fr, text=label, font=_F(10),
                         text_color=Colors.TEXT_MUTED, width=150, anchor="w"
                         ).pack(side="left", padx=12, pady=7)
            ctk.CTkLabel(fr,
                         text=str(value) if value else "—",
                         font=_F(11, "bold" if bold else "normal"),
                         text_color=Colors.MIDNIGHT, anchor="w"
                         ).pack(side="left", padx=6, pady=7, fill="x", expand=True)

        section("🏢  Informations générales", _C_LOG)
        row("N° Bon",          bon.get("numero_bon"), bold=True)
        row("Type",            bon.get("type_bon"))
        row("Date",            self._fmt_date(bon.get("date_bon")))
        row("Statut",          statut)
        row("Demandeur",       bon.get("demandeur"))
        row("Service / Dept.", bon.get("service"))
        row("Responsable",     bon.get("responsable"))

        section("🚗  Véhicule concerné", _C_VALIDE)
        row("Immatriculation", bon.get("immatriculation"))
        row("Marque / Modèle", f"{bon.get('marque','—')} {bon.get('modele','')}")
        row("Chauffeur",       bon.get("chauffeur"))

        section("📦  Articles / Détails sortis", _C_LOG)
        if lignes:
            # Tableau des lignes
            tbl = ctk.CTkFrame(sc, fg_color=Colors.BG_CARD, corner_radius=6,
                               border_width=1, border_color=Colors.DIVIDER)
            tbl.pack(fill="x", padx=14, pady=2)

            # En-tête tableau
            hdr2 = ctk.CTkFrame(tbl, fg_color=_C_HEADER, corner_radius=0)
            hdr2.pack(fill="x")
            for txt, w in [("Désignation", 200), ("Qté", 60), ("Unité", 80), ("Obs.", 100)]:
                ctk.CTkLabel(hdr2, text=txt, font=_F(10, "bold"),
                             text_color="#FFFFFF", width=w, anchor="w"
                             ).pack(side="left", padx=8, pady=5)

            for i, lg in enumerate(lignes):
                bg = _C_ROW_ODD if i % 2 else _C_ROW_EVEN
                lg_fr = ctk.CTkFrame(tbl, fg_color=bg, corner_radius=0)
                lg_fr.pack(fill="x")
                for val, w in [
                    (lg.get("designation", ""), 200),
                    (str(lg.get("quantite", "")), 60),
                    (lg.get("unite", ""), 80),
                    (lg.get("observation", ""), 100),
                ]:
                    ctk.CTkLabel(lg_fr, text=val, font=_F(10),
                                 text_color=Colors.MIDNIGHT, width=w, anchor="w"
                                 ).pack(side="left", padx=8, pady=4)
        else:
            row("Désignation",  bon.get("designation"))
            row("Quantité",     bon.get("quantite"))
            row("Unité",        bon.get("unite"))

        section("📝  Observations", _C_HEADER)
        row("Destination",  bon.get("destination"))
        row("Observations", bon.get("observations"))

        # Signatures
        sig_fr = ctk.CTkFrame(sc, fg_color="transparent")
        sig_fr.pack(fill="x", padx=14, pady=(16, 4))
        sig_fr.grid_columnconfigure((0, 1, 2), weight=1)
        for col, txt in enumerate(["Demandeur", "Responsable", "Magasinier"]):
            f2 = ctk.CTkFrame(sig_fr, fg_color=Colors.BG_CARD, corner_radius=8,
                              border_width=1, border_color=Colors.DIVIDER)
            f2.grid(row=0, column=col, padx=4, sticky="ew")
            ctk.CTkLabel(f2, text=txt, font=_F(10),
                         text_color=Colors.TEXT_MUTED
                         ).pack(padx=10, pady=(8, 0))
            ctk.CTkLabel(f2, text="\n\n", font=_F(10)).pack()
            ctk.CTkLabel(f2, text="Signature : ___________",
                         font=_F(9), text_color=Colors.TEXT_MUTED
                         ).pack(padx=10, pady=(0, 8))

        ctk.CTkButton(self, text="✕  Fermer",
                      fg_color="#95A5A6", hover_color="#7F8C8D",
                      font=_F(12), height=36, corner_radius=8,
                      command=self.destroy
                      ).pack(padx=22, pady=(8, 14), fill="x")

    @staticmethod
    def _fmt_date(v) -> str:
        if not v: return "—"
        try:
            if isinstance(v, str): return datetime.strptime(v[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
            if isinstance(v, (date, datetime)): return v.strftime("%d/%m/%Y")
        except: pass
        return str(v)[:10]


# ─────────────────────────────────────────────────────────────────────────────
# FORMULAIRE BON DE SORTIE
# ─────────────────────────────────────────────────────────────────────────────

class FormBonSortie(ctk.CTkToplevel):
    """Créer ou modifier un bon de sortie avec lignes articles."""

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
        self._lignes: list[dict] = []

        self.title(f"📋  {self._mode} de Sortie — iJeery Logistique")
        self.geometry("600x780")
        self.resizable(True, True)
        self.grab_set()
        self.focus_force()
        self._build()
        if bon:
            self._populate(bon)
            self._load_lignes(bon.get("id"))

    # ── Construction ─────────────────────────────────────────────────────────

    def _build(self):
        # Titre
        ctk.CTkLabel(self, text=f"📋  {self._mode} de Sortie",
                     font=_F(15, "bold"), text_color=_C_LOG
                     ).pack(pady=(14, 2), padx=20, anchor="w")
        ctk.CTkLabel(self, text="Renseignez les informations et les articles sortis.",
                     font=_F(10), text_color=Colors.TEXT_MUTED
                     ).pack(padx=20, anchor="w")
        ctk.CTkFrame(self, height=1, fg_color=Colors.DIVIDER
                     ).pack(fill="x", padx=20, pady=(8, 0))

        # Notebook (onglets)
        self._nb = ttk.Notebook(self)
        self._nb.pack(fill="both", expand=True, padx=0, pady=0)

        self._tab_info   = ctk.CTkFrame(self._nb, fg_color="transparent")
        self._tab_lignes = ctk.CTkFrame(self._nb, fg_color="transparent")
        self._nb.add(self._tab_info,   text="  📝  Informations  ")
        self._nb.add(self._tab_lignes, text="  📦  Articles sortis  ")

        self._build_tab_info()
        self._build_tab_lignes()

        # Boutons bas
        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(fill="x", padx=20, pady=(6, 12))
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

    def _build_tab_info(self):
        sc = ctk.CTkScrollableFrame(self._tab_info, fg_color="transparent")
        sc.pack(fill="both", expand=True, padx=10, pady=8)

        self._vars = {}

        # Numéro bon (auto si nouveau)
        ctk.CTkLabel(sc, text="N° Bon", font=_F(10, "bold"),
                     text_color=Colors.MIDNIGHT, anchor="w"
                     ).pack(fill="x", padx=6, pady=(6, 1))
        self._var_numero = ctk.StringVar(
            value=self._gen_numero() if not self.bon else "")
        ctk.CTkEntry(sc, textvariable=self._var_numero,
                     font=_F(11), height=32
                     ).pack(fill="x", padx=6)

        fields = [
            ("Type de bon *",       "type_bon",     "combo",  _TYPES_BON),
            ("Date (JJ/MM/AAAA) *", "date_bon",     "entry",  None),
            ("Demandeur *",         "demandeur",    "entry",  None),
            ("Service / Département","service",     "entry",  None),
            ("Responsable / Visa",  "responsable",  "entry",  None),
            ("Destination / Objet", "destination",  "entry",  None),
            ("Statut",              "statut",       "combo",  _STATUTS),
            ("Observations",        "observations", "textbox",None),
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

        # Véhicule
        ctk.CTkLabel(sc, text="Véhicule concerné", font=_F(10, "bold"),
                     text_color=Colors.MIDNIGHT, anchor="w"
                     ).pack(fill="x", padx=6, pady=(7, 1))
        veh_vals = ["— Aucun —"] + [
            f"{v['immatriculation']} — {v['marque']} {v.get('modele','')}"
            for v in self.vehicules]
        self._veh_var = ctk.StringVar(value=veh_vals[0])
        ctk.CTkComboBox(sc, values=veh_vals, variable=self._veh_var,
                        font=_F(11), height=32
                        ).pack(fill="x", padx=6)

        ctk.CTkLabel(sc, text="Chauffeur / Bénéficiaire", font=_F(10, "bold"),
                     text_color=Colors.MIDNIGHT, anchor="w"
                     ).pack(fill="x", padx=6, pady=(7, 1))
        self._var_chauffeur = ctk.StringVar()
        ctk.CTkEntry(sc, textvariable=self._var_chauffeur,
                     font=_F(11), height=32
                     ).pack(fill="x", padx=6)

        # Pré-remplir date
        if not self.bon:
            self._vars["date_bon"].set(date.today().strftime("%d/%m/%Y"))

    def _build_tab_lignes(self):
        """Onglet de gestion des lignes articles."""
        parent = self._tab_lignes

        # Barre ajout ligne
        add_bar = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD,
                               corner_radius=0, height=46,
                               border_width=1, border_color=Colors.DIVIDER)
        add_bar.pack(fill="x", padx=10, pady=(8, 0))
        add_bar.pack_propagate(False)

        self._lg_desig = ctk.CTkEntry(add_bar, placeholder_text="Désignation article",
                                       font=_F(10), height=30, width=180)
        self._lg_desig.pack(side="left", padx=(8, 4), pady=8)

        self._lg_qte = ctk.CTkEntry(add_bar, placeholder_text="Qté",
                                     font=_F(10), height=30, width=55)
        self._lg_qte.pack(side="left", padx=4, pady=8)

        self._lg_unite = ctk.CTkEntry(add_bar, placeholder_text="Unité",
                                       font=_F(10), height=30, width=70)
        self._lg_unite.pack(side="left", padx=4, pady=8)

        self._lg_obs = ctk.CTkEntry(add_bar, placeholder_text="Observation",
                                     font=_F(10), height=30, width=120)
        self._lg_obs.pack(side="left", padx=4, pady=8)

        ctk.CTkButton(add_bar, text="➕ Ajouter",
                      fg_color=_C_LOG, hover_color=_C_LOG_H,
                      font=_F(10, "bold"), height=30, width=90, corner_radius=6,
                      command=self._add_ligne
                      ).pack(side="left", padx=4, pady=8)

        ctk.CTkButton(add_bar, text="🗑️ Retirer",
                      fg_color="#E74C3C", hover_color="#C0392B",
                      font=_F(10), height=30, width=80, corner_radius=6,
                      command=self._remove_ligne
                      ).pack(side="left", padx=4, pady=8)

        # Treeview lignes
        frame = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD,
                             corner_radius=0, border_width=1,
                             border_color=Colors.DIVIDER)
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.configure("Lignes.Treeview",
                        rowheight=26, font=("Segoe UI", 10), borderwidth=0)
        style.configure("Lignes.Treeview.Heading",
                        background=_C_LOG, foreground="#FFFFFF",
                        font=("Segoe UI", 10, "bold"), relief="flat")

        self._tree_lg = ttk.Treeview(
            frame,
            columns=("N°", "Désignation", "Qté", "Unité", "Observation"),
            show="headings", style="Lignes.Treeview")
        widths = [35, 230, 60, 80, 140]
        for col, w in zip(("N°", "Désignation", "Qté", "Unité", "Observation"), widths):
            self._tree_lg.heading(col, text=col)
            self._tree_lg.column(col, width=w, anchor="w" if col not in ("N°","Qté") else "center")

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self._tree_lg.yview)
        self._tree_lg.configure(yscrollcommand=vsb.set)
        self._tree_lg.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self._lbl_nb_lignes = ctk.CTkLabel(parent,
            text="0 article(s)", font=_F(10),
            text_color=Colors.TEXT_MUTED)
        self._lbl_nb_lignes.pack(padx=10, anchor="w")

    # ── Gestion lignes ────────────────────────────────────────────────────────

    def _add_ligne(self):
        desig = self._lg_desig.get().strip()
        if not desig:
            messagebox.showwarning("Attention",
                "La désignation de l'article est obligatoire.", parent=self)
            return
        try:
            qte = float(self._lg_qte.get().replace(",", ".") or "1")
        except ValueError:
            qte = 1.0
        lg = {
            "designation": desig,
            "quantite":    qte,
            "unite":       self._lg_unite.get().strip() or "Unité",
            "observation": self._lg_obs.get().strip(),
        }
        self._lignes.append(lg)
        self._refresh_lignes()
        # Vider les champs
        for w in (self._lg_desig, self._lg_qte, self._lg_unite, self._lg_obs):
            w.delete(0, "end")
        self._lg_desig.focus()

    def _remove_ligne(self):
        sel = self._tree_lg.selection()
        if not sel:
            messagebox.showwarning("Attention",
                "Sélectionnez une ligne à retirer.", parent=self)
            return
        idx = int(self._tree_lg.item(sel[0], "values")[0]) - 1
        if 0 <= idx < len(self._lignes):
            self._lignes.pop(idx)
            self._refresh_lignes()

    def _refresh_lignes(self):
        self._tree_lg.delete(*self._tree_lg.get_children())
        for i, lg in enumerate(self._lignes):
            self._tree_lg.insert("", "end",
                values=(i + 1, lg["designation"],
                        lg["quantite"], lg["unite"],
                        lg.get("observation", "")))
        self._lbl_nb_lignes.configure(
            text=f"{len(self._lignes)} article(s)")

    def _load_lignes(self, bon_id: Optional[int]):
        if not self.db_conn or not bon_id: return
        try:
            cur = self.db_conn.cursor()
            cur.execute("""
                SELECT designation, quantite, unite, observation
                FROM logistique_bon_sortie_ligne
                WHERE bon_id=%s ORDER BY id
            """, (bon_id,))
            for row in cur.fetchall():
                self._lignes.append({
                    "designation": row[0], "quantite": row[1],
                    "unite": row[2] or "", "observation": row[3] or ""
                })
            cur.close()
            self._refresh_lignes()
        except Exception as e:
            print(f"[BonSortie] _load_lignes: {e}")

    # ── Pré-remplissage ───────────────────────────────────────────────────────

    def _populate(self, b: dict):
        self._var_numero.set(b.get("numero_bon", ""))
        for key, var in self._vars.items():
            val = b.get(key, "")
            if isinstance(var, ctk.CTkTextbox):
                var.delete("1.0", "end")
                var.insert("1.0", str(val) if val else "")
            else:
                var.set(str(val) if val else "")
        # Formater la date
        if b.get("date_bon"):
            try:
                d = b["date_bon"]
                if isinstance(d, (date, datetime)):
                    self._vars["date_bon"].set(d.strftime("%d/%m/%Y"))
                elif isinstance(d, str):
                    self._vars["date_bon"].set(
                        datetime.strptime(d[:10], "%Y-%m-%d").strftime("%d/%m/%Y"))
            except: pass
        # Véhicule
        immat = b.get("immatriculation", "")
        if immat:
            for v in self.vehicules:
                if v.get("immatriculation") == immat:
                    self._veh_var.set(
                        f"{v['immatriculation']} — {v['marque']} {v.get('modele','')}")
                    break
        self._var_chauffeur.set(b.get("chauffeur", ""))

    @staticmethod
    def _gen_numero() -> str:
        now = datetime.now()
        import random
        return f"BS-{now.year}-{now.month:02d}{now.day:02d}-{random.randint(100,999)}"

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

    # ── Sauvegarde ────────────────────────────────────────────────────────────

    def _save(self):
        numero   = self._var_numero.get().strip()
        type_bon = self._vars["type_bon"].get()
        demandeur= self._vars["demandeur"].get().strip()
        if not all([numero, demandeur]):
            messagebox.showerror("Erreur",
                "N° Bon et Demandeur sont obligatoires.", parent=self)
            return

        d_bon = self._parse_date(self._vars["date_bon"].get())
        if not d_bon:
            messagebox.showerror("Erreur",
                "Date invalide. Format attendu : JJ/MM/AAAA", parent=self)
            return

        def get_text(k):
            var = self._vars[k]
            if isinstance(var, ctk.CTkTextbox):
                return var.get("1.0", "end").strip()
            return var.get().strip()

        service      = self._vars["service"].get().strip()
        responsable  = self._vars["responsable"].get().strip()
        destination  = self._vars["destination"].get().strip()
        statut       = self._vars["statut"].get()
        observations = get_text("observations")
        chauffeur    = self._var_chauffeur.get().strip()
        vehicule_id  = self._get_vehicule_id()

        if not self.db_conn:
            messagebox.showwarning("Mode démo",
                "Bon enregistré (simulation).", parent=self)
            if self.on_save: self.on_save()
            self.destroy()
            return

        try:
            cur = self.db_conn.cursor()
            if self.bon:
                cur.execute("""
                    UPDATE logistique_bon_sortie
                    SET numero_bon=%s, type_bon=%s, date_bon=%s, demandeur=%s,
                        service=%s, responsable=%s, destination=%s, statut=%s,
                        observations=%s, vehicule_id=%s, chauffeur=%s
                    WHERE id=%s
                """, (numero, type_bon, d_bon, demandeur, service or None,
                      responsable or None, destination or None, statut,
                      observations or None, vehicule_id, chauffeur or None,
                      self.bon["id"]))
                bon_id = self.bon["id"]
                # Supprimer anciennes lignes et réinsérer
                cur.execute(
                    "DELETE FROM logistique_bon_sortie_ligne WHERE bon_id=%s",
                    (bon_id,))
            else:
                cur.execute("""
                    INSERT INTO logistique_bon_sortie
                        (numero_bon, type_bon, date_bon, demandeur, service,
                         responsable, destination, statut, observations,
                         vehicule_id, chauffeur, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                    RETURNING id
                """, (numero, type_bon, d_bon, demandeur, service or None,
                      responsable or None, destination or None, statut,
                      observations or None, vehicule_id, chauffeur or None))
                bon_id = cur.fetchone()[0]

            # Insérer les lignes
            for lg in self._lignes:
                cur.execute("""
                    INSERT INTO logistique_bon_sortie_ligne
                        (bon_id, designation, quantite, unite, observation)
                    VALUES (%s,%s,%s,%s,%s)
                """, (bon_id, lg["designation"], lg["quantite"],
                      lg.get("unite", "Unité"), lg.get("observation", "")))

            self.db_conn.commit(); cur.close()
            messagebox.showinfo("Succès", "Bon de sortie enregistré.", parent=self)
            if self.on_save: self.on_save()
            self.destroy()
        except Exception as e:
            try: self.db_conn.rollback()
            except: pass
            messagebox.showerror("Erreur DB", str(e), parent=self)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE PRINCIPALE : BONS DE SORTIE
# ─────────────────────────────────────────────────────────────────────────────

class PageBonsSortie(ctk.CTkFrame):
    """
    Page principale du module Bons de Sortie.
    Signature : PageBonsSortie(master, db_conn, session_data)
    """

    _SQL_BON = """
        CREATE TABLE IF NOT EXISTS logistique_bon_sortie (
            id           SERIAL PRIMARY KEY,
            numero_bon   VARCHAR(40) UNIQUE NOT NULL,
            type_bon     VARCHAR(40) DEFAULT 'Sortie Matériel',
            date_bon     DATE NOT NULL DEFAULT CURRENT_DATE,
            demandeur    VARCHAR(80) NOT NULL,
            service      VARCHAR(80),
            responsable  VARCHAR(80),
            destination  VARCHAR(120),
            statut       VARCHAR(20) DEFAULT 'Brouillon',
            observations TEXT,
            vehicule_id  INTEGER REFERENCES logistique_vehicule(id) ON DELETE SET NULL,
            chauffeur    VARCHAR(80),
            created_at   TIMESTAMP DEFAULT NOW()
        );
    """

    _SQL_LIGNE = """
        CREATE TABLE IF NOT EXISTS logistique_bon_sortie_ligne (
            id           SERIAL PRIMARY KEY,
            bon_id       INTEGER REFERENCES logistique_bon_sortie(id) ON DELETE CASCADE,
            designation  VARCHAR(120) NOT NULL,
            quantite     NUMERIC(10,3) DEFAULT 1,
            unite        VARCHAR(30) DEFAULT 'Unité',
            observation  TEXT
        );
    """

    _COLS = [
        ("ID",         "id",           40,  "center"),
        ("N° Bon",     "numero_bon",  130,  "w"),
        ("Type",       "type_bon",    110,  "w"),
        ("Date",       "date_bon",     85,  "center"),
        ("Demandeur",  "demandeur",   110,  "w"),
        ("Service",    "service",      90,  "w"),
        ("Véhicule",   "immatriculation", 90, "center"),
        ("Chauffeur",  "chauffeur",   100,  "w"),
        ("Articles",   "_nb_lignes",   60,  "center"),
        ("Statut",     "statut",       90,  "center"),
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

        self._ensure_tables()
        self._load_vehicules()
        self._build_header()
        self._build_body()
        self._load_data()

    def _ensure_tables(self):
        if not self.db_conn: return
        try:
            cur = self.db_conn.cursor()
            cur.execute(self._SQL_BON)
            cur.execute(self._SQL_LIGNE)
            self.db_conn.commit(); cur.close()
        except Exception as e:
            print(f"[BonsSortie] _ensure_tables: {e}")
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
            print(f"[BonsSortie] _load_vehicules: {e}")

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=_C_HEADER, corner_radius=0, height=56)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(1, weight=1)
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="📋  Bons de Sortie",
                     font=_F(17, "bold"), text_color="#FFFFFF"
                     ).grid(row=0, column=0, padx=18, pady=14, sticky="w")
        ctk.CTkLabel(hdr, text="LOGISTIQUE  ›  Bons de Sortie",
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
            ("📋  Bons ce mois",    "0",    "#3498DB"),
            ("✅  Validés",          "0",    _C_VALIDE),
            ("📝  Brouillons",      "0",    _C_BROUILLON),
            ("✔️  Clôturés",        "0",    _C_CLOTURE),
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
        mois     = [b for b in self._data if self._is_current_month(b.get("date_bon"))]
        valides  = sum(1 for b in self._data if b.get("statut") == "Validé")
        brouill  = sum(1 for b in self._data if b.get("statut") == "Brouillon")
        clotures = sum(1 for b in self._data if b.get("statut") == "Clôturé")
        self._kpi_labels[0].configure(text=str(len(mois)))
        self._kpi_labels[1].configure(text=str(valides))
        self._kpi_labels[2].configure(text=str(brouill))
        self._kpi_labels[3].configure(text=str(clotures))

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
        bar.grid_columnconfigure(4, weight=1)
        bar.grid_propagate(False)

        btns = [
            ("➕  Nouveau Bon",   _C_LOG,    _C_LOG_H,  self._open_add),
            ("✏️  Modifier",      "#2980B9", "#1A6B9A",  self._open_edit),
            ("🗑️  Supprimer",     "#E74C3C", "#C0392B",  self._delete),
            ("👁️  Aperçu / Impr.","#8E44AD", "#7D3C98",  self._apercu),
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
                     placeholder_text="🔍  Rechercher (N° bon, demandeur, service…)",
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
        style.configure("Bon.Treeview",
                        background=_C_ROW_EVEN, foreground=Colors.MIDNIGHT,
                        rowheight=28, fieldbackground=_C_ROW_EVEN,
                        font=("Segoe UI", 10), borderwidth=0)
        style.configure("Bon.Treeview.Heading",
                        background=_C_HEADER, foreground="#FFFFFF",
                        font=("Segoe UI", 10, "bold"), relief="flat", padding=5)
        style.map("Bon.Treeview",
                  background=[("selected", _C_LOG)],
                  foreground=[("selected", "#FFFFFF")])

        cols = tuple(c[0] for c in self._COLS)
        self._tree = ttk.Treeview(frame, columns=cols, show="headings",
                                   style="Bon.Treeview", selectmode="browse")
        for label, _, width, anchor in self._COLS:
            self._tree.heading(label, text=label,
                               command=lambda c=label: self._sort_by(c))
            self._tree.column(label, width=width, anchor=anchor, minwidth=30)

        self._tree.tag_configure("odd",       background=_C_ROW_ODD)
        self._tree.tag_configure("even",      background=_C_ROW_EVEN)
        self._tree.tag_configure("brouillon", foreground=_C_BROUILLON)
        self._tree.tag_configure("valide",    foreground=_C_VALIDE)
        self._tree.tag_configure("cloture",   foreground=_C_CLOTURE)
        self._tree.tag_configure("annule",    foreground=_C_ANNULE)

        vsb = ttk.Scrollbar(frame, orient="vertical",   command=self._tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self._tree.bind("<Double-1>", lambda e: self._apercu())
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
                    SELECT b.id, b.numero_bon, b.type_bon, b.date_bon,
                           b.demandeur, b.service, b.responsable,
                           b.destination, b.statut, b.observations,
                           b.chauffeur,
                           v.immatriculation, v.marque, v.modele,
                           (SELECT COUNT(*) FROM logistique_bon_sortie_ligne l
                            WHERE l.bon_id = b.id) AS nb_lignes
                    FROM logistique_bon_sortie b
                    LEFT JOIN logistique_vehicule v ON v.id = b.vehicule_id
                    ORDER BY b.date_bon DESC, b.id DESC
                """)
                cols = [d[0] for d in cur.description]
                for row in cur.fetchall():
                    self._data.append(dict(zip(cols, row)))
                cur.close()
            except Exception as e:
                print(f"[BonsSortie] _load_data: {e}")
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
            {"id": 1, "numero_bon": "BS-2026-0508-101", "type_bon": "Sortie Pièces",
             "date_bon": "2026-05-08", "demandeur": "Jean Rakoto",
             "service": "Logistique", "responsable": "Chef Garage",
             "destination": "Garage Central", "statut": "Validé",
             "observations": "Urgent", "chauffeur": "",
             "immatriculation": "DEF-5678", "marque": "Mitsubishi",
             "modele": "L200", "nb_lignes": 3},
            {"id": 2, "numero_bon": "BS-2026-0507-089", "type_bon": "Mission Véhicule",
             "date_bon": "2026-05-07", "demandeur": "Marie Ralay",
             "service": "Direction", "responsable": "DG",
             "destination": "Antananarivo", "statut": "Clôturé",
             "observations": "", "chauffeur": "Luc Andria",
             "immatriculation": "GHI-9012", "marque": "Ford",
             "modele": "Transit", "nb_lignes": 1},
            {"id": 3, "numero_bon": "BS-2026-0508-102", "type_bon": "Sortie Carburant",
             "date_bon": "2026-05-08", "demandeur": "Paul Rabe",
             "service": "Transport", "responsable": "Chef Transport",
             "destination": "Station Total", "statut": "Brouillon",
             "observations": "", "chauffeur": "Paul Rabe",
             "immatriculation": "ABC-1234", "marque": "Toyota",
             "modele": "Hilux", "nb_lignes": 0},
        ]

    def _apply_filter(self, *_):
        q      = self._search_var.get().lower().strip()
        statut = self._filter_statut.get()
        self._filtered = [
            b for b in self._data
            if (statut == "Tous" or b.get("statut") == statut)
            and (not q or any(
                q in str(b.get(col, "")).lower()
                for col in ("numero_bon", "demandeur", "service",
                            "type_bon", "immatriculation", "chauffeur",
                            "destination")
            ))
        ]
        self._refresh_tree()

    def _refresh_tree(self):
        self._tree.delete(*self._tree.get_children())
        for i, b in enumerate(self._filtered):
            statut = b.get("statut", "")
            tag_s  = {"Brouillon": "brouillon", "Validé": "valide",
                      "Clôturé": "cloture",     "Annulé": "annule"}.get(statut, "")
            tag_r  = "odd" if i % 2 else "even"

            def fmt_date(v):
                if not v: return "—"
                try: return datetime.strptime(str(v)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
                except: return str(v)[:10]

            values = (
                b.get("id", ""),
                b.get("numero_bon", ""),
                b.get("type_bon", ""),
                fmt_date(b.get("date_bon")),
                b.get("demandeur", ""),
                b.get("service", "—"),
                b.get("immatriculation", "—"),
                b.get("chauffeur", "—"),
                b.get("nb_lignes", 0),
                statut,
            )
            self._tree.insert("", "end", iid=str(b.get("id", i)),
                               values=values, tags=(tag_r, tag_s))

        self._status_lbl.configure(
            text=f"✅  {len(self._filtered)} bon(s)  sur  {len(self._data)} au total")

    _sort_reverse: dict = {}

    def _sort_by(self, col_label: str):
        col_key = next((c[1] for c in self._COLS if c[0] == col_label), None)
        if not col_key: return
        rev = self._sort_reverse.get(col_label, False)
        self._filtered.sort(key=lambda b: (b.get(col_key) or ""), reverse=rev)
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
        return next((b for b in self._data if b.get("id") == self._selected_id), None)

    def _fetch_lignes(self, bon_id: int) -> list:
        if not self.db_conn: return []
        try:
            cur = self.db_conn.cursor()
            cur.execute("""
                SELECT designation, quantite, unite, observation
                FROM logistique_bon_sortie_ligne
                WHERE bon_id=%s ORDER BY id
            """, (bon_id,))
            rows = [{"designation": r[0], "quantite": r[1],
                     "unite": r[2], "observation": r[3]}
                    for r in cur.fetchall()]
            cur.close()
            return rows
        except: return []

    def _open_add(self):
        FormBonSortie(self, self.db_conn, vehicules=self._vehicules,
                      on_save=self._load_data)

    def _open_edit(self):
        b = self._get_selected()
        if not b: return
        FormBonSortie(self, self.db_conn, bon=b,
                      vehicules=self._vehicules, on_save=self._load_data)

    def _apercu(self):
        b = self._get_selected()
        if not b: return
        lignes = self._fetch_lignes(b["id"])
        ApercuBon(self, b, lignes)

    def _delete(self):
        b = self._get_selected()
        if not b: return
        ref = b.get("numero_bon", f"ID#{b['id']}")
        if not messagebox.askyesno("Confirmation",
            f"Supprimer le bon {ref} ?\nLes lignes articles seront aussi supprimées.",
            parent=self): return
        if not self.db_conn:
            self._data = [d for d in self._data if d.get("id") != b["id"]]
            self._apply_filter(); self._update_kpis(); return
        try:
            cur = self.db_conn.cursor()
            cur.execute("DELETE FROM logistique_bon_sortie WHERE id=%s", (b["id"],))
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
    root.title("iJeery V5.0 — Test Bons de Sortie")
    root.geometry("1280x720")
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    PageBonsSortie(master=root, db_conn=None).grid(row=0, column=0, sticky="nsew")
    root.mainloop()

