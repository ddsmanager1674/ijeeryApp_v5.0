import customtkinter as ctk
import tkinter as tk  # Import tkinter for ttk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime, date
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import json
import sys
import os
from resource_utils import get_config_path, safe_file_read
from date_picker_utils import (
    format_date_iso,
    get_date_from_widget,
    set_date_on_widget,
)
from treeview_sort_utils import TreeColumn, TreeSortController, new_sort_state
from log_utils import resolve_connected_user_id

# Thème UI iJeery
from app_theme import Colors, Fonts, Theme, styled, Layout

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from ticket_caisse_personnel import try_imprimer_ticket_avance
except ImportError:
    def try_imprimer_ticket_avance(*_a, **_kw):
        return False

    
def charger_personnels(cursor):
        """Charge la liste des personnels depuis la base de données."""
        cursor.execute("SELECT id, nom, prenom FROM tb_personnel ORDER BY nom")
        # [UI] Affichage propre: prenom None → "-"
        out = []
        for _id, nom, prenom in cursor.fetchall():
            prenom_disp = (prenom or "").strip() if prenom is not None else ""
            prenom_disp = prenom_disp if prenom_disp else "-"
            nom_disp = (nom or "").strip() if nom is not None else ""
            nom_disp = nom_disp if nom_disp else "-"
            out.append({"id": _id, "nom": nom, "prenom": prenom, "nom_complet": f"{nom_disp} {prenom_disp}"})
        return out

# ---
class FenetreAvanceSpec(ctk.CTkFrame):

    def __init__(self, master, iduser=None):
        # [UI] Harmonisation Avance Spéciale avec app_theme (header/cards/boutons/table)
        # [LOGIQUE] Aucune modification des règles métier/SQL ; uniquement UI et styles
        super().__init__(master, fg_color=Colors.BG_PAGE)
        self.master = master
        # Stocker l'iduser passé en paramètre
        self.iduser = iduser if iduser is not None else resolve_connected_user_id(master=master)
        
        # Afficher l'iduser pour le débogage
        if self.iduser:
            print(f"FenetreAvanceSpec initialisée avec iduser: {self.iduser}")
        else:
            print("ATTENTION: FenetreAvanceSpec initialisée sans iduser!")

        # Connexion à la base de données
        self.conn = self.connect_db()
        self.cursor = None
        
        if self.conn:
            self.cursor = self.conn.cursor()
            self.initialize_database()

        self.personnel = charger_personnels(self.cursor)
        self.prof_ids = {prof["nom_complet"]: prof["id"] for prof in self.personnel}
        self.id_prof_selectionne = None
        self.selected_personnel_var = ctk.StringVar(value="")
        self._avances_raw = []
        self._sort_state = new_sort_state()
        self._table_sort = None

        # Widgets d'interface
        self.creer_widgets()

        # Chargement initial des données
        self.charger_avances()

    def connect_db(self):


        try:


            from pages.db_helper import connect_page_db


            shared = (


                getattr(self, '_db_conn_shared', None)


                or getattr(self, '_db_conn_initial', None)


            )


            return connect_page_db(shared)

        except Exception as err:
            messagebox.showerror("Erreur de connexion", f"Détails : {err}")
            return None

    def initialize_database(self):
        """Initialise la connexion à la base de données et crée la table si nécessaire."""
        if not self.cursor:
            return False
        
        try:        
            self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tb_avancespecpers (
                id SERIAL PRIMARY KEY,
                refpmt VARCHAR(50) UNIQUE,
                observation VARCHAR(120),
                idpers INT REFERENCES tb_personnel(id),
                mtpaye DOUBLE PRECISION NOT NULL CHECK (mtpaye > 0),
                nbremboursement INTEGER NOT NULL CHECK (nbremboursement > 0),
                datepmt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                idtypeoperation INT DEFAULT '2',
                iduser INT
            )
            """)
            self.conn.commit()
            return True
            
        except psycopg2.Error as err:
            messagebox.showerror("Erreur de connexion", f"Erreur : {err}")
            return False

    def _configure_table_alternating_colors(self, tree):
        # [UI] Palette alignée au thème iJeery
        tree.tag_configure("row_even", background=Colors.BG_CARD)
        tree.tag_configure("row_odd", background=Colors.BG_ROW_ALT)

    def _refresh_table_alternating_colors(self, tree):
        for idx, item in enumerate(tree.get_children()):
            tree.item(item, tags=("row_even" if idx % 2 == 0 else "row_odd",))
     
    
    def autocompletion_personnel(self, event):
        # [UI] Ancien mode combobox (désactivé) — personnel se fait via bouton Rechercher
        return

    # ──────────────────────────────────────────────────────────────────────
    # [UI] Sélecteur personnel (bouton Rechercher + champ readonly)
    # ──────────────────────────────────────────────────────────────────────

    def open_personnel_picker(self):
        top = ctk.CTkToplevel(self)
        top.title("Rechercher un personnel")
        top.geometry("520x420")
        top.transient(self.winfo_toplevel())
        top.grab_set()

        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(top, fg_color=Colors.MIDNIGHT, corner_radius=0, height=46)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        left = styled.frame(header)
        left.pack(side="left", padx=14)
        ctk.CTkLabel(left, text="👤", font=Fonts.heading(16), text_color=Colors.TEXT_ON_DARK).pack(side="left", padx=(0, 8))
        inner = styled.frame(left)
        inner.pack(side="left")
        ctk.CTkLabel(inner, text="Personnel", font=Fonts.bold(13), text_color=Colors.TEXT_ON_DARK).pack(anchor="w")
        ctk.CTkLabel(inner, text="Rechercher et sélectionner", font=Fonts.small(9), text_color=Colors.TEXT_ON_DARK_DIM).pack(anchor="w")

        tools = ctk.CTkFrame(top, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        tools.grid(row=1, column=0, sticky="ew", padx=10, pady=(10, 6))
        tools.grid_columnconfigure(0, weight=1)

        q_var = ctk.StringVar(value="")
        q_entry = ctk.CTkEntry(
            tools, textvariable=q_var, height=32, fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            corner_radius=8, font=Fonts.body(11), placeholder_text="Nom ou prénom…",
        )
        q_entry.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        table_card = ctk.CTkFrame(top, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        table_card.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        table_card.grid_columnconfigure(0, weight=1)
        table_card.grid_rowconfigure(0, weight=1)

        tv = ttk.Treeview(table_card, columns=("id", "nom", "prenom"), show="headings", height=10, style="P.Treeview")
        tv.heading("id", text="ID")
        tv.heading("nom", text="Nom")
        tv.heading("prenom", text="Prénom")
        tv.column("id", width=70, anchor="center")
        tv.column("nom", width=200, anchor="w")
        tv.column("prenom", width=200, anchor="w")
        tv.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        vsb = ttk.Scrollbar(table_card, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns", pady=6)

        def _fill(query: str = ""):
            for item in tv.get_children():
                tv.delete(item)
            try:
                if not self.cursor:
                    return
                like = f"%{query.strip()}%"
                self.cursor.execute(
                    "SELECT id, nom, prenom FROM tb_personnel WHERE (nom ILIKE %s OR prenom ILIKE %s) ORDER BY nom, prenom",
                    (like, like),
                )
                for _id, nom, prenom in self.cursor.fetchall():
                    nom_disp = (nom or "").strip() if nom is not None else ""
                    prenom_disp = (prenom or "").strip() if prenom is not None else ""
                    nom_disp = nom_disp if nom_disp else "-"
                    prenom_disp = prenom_disp if prenom_disp else "-"
                    tv.insert("", "end", values=(_id, nom_disp, prenom_disp))
            except Exception:
                return

        def _select():
            sel = tv.selection()
            if not sel:
                return
            _id, nom, prenom = tv.item(sel[0], "values")
            try:
                self.id_prof_selectionne = int(_id)
            except Exception:
                self.id_prof_selectionne = None
            self.selected_personnel_var.set(self._fmt_personnel(nom, prenom))
            top.destroy()

        tv.bind("<Double-1>", lambda e: _select())
        q_entry.bind("<Return>", lambda e: _fill(q_var.get()))

        footer = ctk.CTkFrame(top, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        styled.button_secondary(footer, text="Annuler", icon="✖", width=120, height=32, command=top.destroy).pack(side="right")
        styled.button_success(footer, text="Sélectionner", icon="✅", width=140, height=32, command=_select).pack(side="right", padx=(0, 8))

        _fill("")
        q_entry.focus_set()

    # ──────────────────────────────────────────────────────────────────────
    # [UI] Filtres + tri liste avances (client-side)
    # ──────────────────────────────────────────────────────────────────────

    def _get_date_filter_value(self, w):
        d = get_date_from_widget(w)
        return format_date_iso(d) if d else ""

    def reset_filters(self):
        try:
            self.filter_search_var.set("")
        except Exception:
            pass
        try:
            set_date_on_widget(self.filter_date_start, date.today())
            set_date_on_widget(self.filter_date_end, date.today())
        except Exception:
            pass
        try:
            self.sort_key.set("Date (desc)")
        except Exception:
            pass
        self.apply_filters()

    def sort_treeview(self, key):
        if self._table_sort:
            self._table_sort.click(key)

    def apply_filters(self, force_sort_key=None, force_desc=None):
        q = (self.filter_search_var.get() if hasattr(self, "filter_search_var") else "").strip().lower()
        d1 = self._get_date_filter_value(getattr(self, "filter_date_start", None))
        d2 = self._get_date_filter_value(getattr(self, "filter_date_end", None))

        def _parse_ymd(s):
            try:
                return datetime.strptime(s, "%Y-%m-%d").date()
            except Exception:
                return None

        d1v = _parse_ymd(d1) if d1 else None
        d2v = _parse_ymd(d2) if d2 else None

        rows = []
        for r in (self._avances_raw or []):
            if q:
                hay = f"{r.get('ref','')} {r.get('obs','')} {r.get('personnel','')}".lower()
                if q not in hay:
                    continue
            if d1v or d2v:
                dd = (r.get("date_dt") or datetime.min).date()
                if d1v and dd < d1v:
                    continue
                if d2v and dd > d2v:
                    continue
            rows.append(r)

        sort_mode = (self.sort_key.get() if hasattr(self, "sort_key") else "Date (desc)")
        if force_sort_key:
            map_key = {
                "date": ("date_dt", False),
                "montant": ("montant", False),
                "personnel": ("personnel", False),
                "ref": ("ref", False),
                "obs": ("obs", False),
            }
            col, _ = map_key.get(force_sort_key, ("date_dt", True))
            desc = bool(force_desc)
            rows.sort(key=lambda x: x.get(col) or "", reverse=desc)
        else:
            if sort_mode == "Date (asc)":
                rows.sort(key=lambda x: x.get("date_dt") or datetime.min, reverse=False)
            elif sort_mode == "Personnel (A→Z)":
                rows.sort(key=lambda x: (x.get("personnel") or "").lower(), reverse=False)
            elif sort_mode == "Personnel (Z→A)":
                rows.sort(key=lambda x: (x.get("personnel") or "").lower(), reverse=True)
            elif sort_mode == "Montant (asc)":
                rows.sort(key=lambda x: x.get("montant") or 0, reverse=False)
            elif sort_mode == "Montant (desc)":
                rows.sort(key=lambda x: x.get("montant") or 0, reverse=True)
            else:
                rows.sort(key=lambda x: x.get("date_dt") or datetime.min, reverse=True)

        if self._table_sort:
            self._table_sort.refresh_headings()
        for item in self.tree.get_children():
            self.tree.delete(item)
        for r in rows:
            self.tree.insert(
                "",
                "end",
                values=(
                    r["date_str"],
                    r["ref"],
                    r["obs"],
                    r["montant_str"],
                    r["nb_remb"],
                    r["pmt_mois_str"],
                ),
            )
        self._refresh_table_alternating_colors(self.tree)

    def generate_observation(self, nom, prenom):
        today = date.today().strftime("%d/%m/%Y")
        # [LOGIQUE] Robuste aux valeurs NULL (évite prenom=None → capitalize() crash)
        nom_s = (nom or "").strip()
        prenom_s = (prenom or "").strip()
        nom_fmt = nom_s.upper() if nom_s else "INCONNU"
        prenom_fmt = prenom_s.capitalize() if prenom_s else ""
        sep = " " if prenom_fmt else ""
        return f"AVS - {nom_fmt}{sep}{prenom_fmt} - {today}"

    def _fmt_personnel(self, nom, prenom):
        nom_s = (nom or "").strip() if nom is not None else ""
        prenom_s = (prenom or "").strip() if prenom is not None else ""
        nom_s = nom_s if nom_s else "-"
        prenom_s = prenom_s if prenom_s else "-"
        return f"{nom_s} {prenom_s}".strip()

    def _setup_treeview_style(self):
        # [UI] Style tableau cohérent avec le thème iJeery
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure(
            "P.Treeview",
            background=Colors.BG_CARD,
            foreground=Colors.TEXT_PRIMARY,
            fieldbackground=Colors.BG_CARD,
            rowheight=26,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        s.configure(
            "P.Treeview.Heading",
            background=Colors.MIDNIGHT,
            foreground=Colors.TEXT_ON_DARK,
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padding=(6, 5),
        )
        s.map("P.Treeview", background=[("selected", Colors.PRIMARY_LIGHT)])
        s.map("P.Treeview.Heading", background=[("active", Colors.MIDNIGHT_LIGHT)])

    def creer_widgets(self):
        # [UI] Header + cards (même logique que les pages modernisées)
        self._setup_treeview_style()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        header = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT, corner_radius=0, height=46)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)

        left = styled.frame(header)
        left.grid(row=0, column=0, padx=14, sticky="w")
        ctk.CTkLabel(left, text="💰", font=Fonts.heading(16), text_color=Colors.TEXT_ON_DARK).pack(side="left", padx=(0, 8))
        inner = styled.frame(left)
        inner.pack(side="left")
        ctk.CTkLabel(inner, text="Avance Spéciale", font=Fonts.bold(13), text_color=Colors.TEXT_ON_DARK).pack(anchor="w")
        ctk.CTkLabel(inner, text="Saisie, remboursement et export", font=Fonts.small(9), text_color=Colors.TEXT_ON_DARK_DIM).pack(anchor="w")

        # Section Champs de Saisie (card)
        input_frame = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        input_frame.grid(row=1, column=0, padx=10, pady=(10, 6), sticky="ew")
        # [UI] Formulaire inline : Rechercher personnel + Montant + Nb remboursements + Enregistrer
        input_frame.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(input_frame, text="Personnel", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(
            row=0, column=0, padx=(12, 6), pady=10, sticky="w"
        )
        styled.button_primary(
            input_frame, text="Rechercher", icon="🔎", width=120, height=32, command=self.open_personnel_picker
        ).grid(row=0, column=1, padx=(0, 8), pady=10, sticky="w")

        self.selected_personnel_entry = ctk.CTkEntry(
            input_frame,
            textvariable=self.selected_personnel_var,
            height=32,
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            corner_radius=8,
            font=Fonts.body(11),
            state="readonly",
            placeholder_text="Aucun personnel sélectionné",
        )
        self.selected_personnel_entry.grid(row=0, column=2, padx=(0, 12), pady=10, sticky="ew")

        ctk.CTkLabel(input_frame, text="Montant", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(
            row=0, column=3, padx=(0, 6), pady=10, sticky="w"
        )
        self.mtpaye_var = tk.StringVar()
        self.mtpaye_entry = ctk.CTkEntry(
            input_frame, textvariable=self.mtpaye_var, height=32, fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            corner_radius=8, font=Fonts.body(11), placeholder_text="0,00",
        )
        self.mtpaye_entry.grid(row=0, column=4, padx=(0, 12), pady=10, sticky="w")

        ctk.CTkLabel(input_frame, text="Nb remb.", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(
            row=0, column=5, padx=(0, 6), pady=10, sticky="w"
        )
        self.nbremboursement_var = tk.StringVar()
        self.nbremb_entry = ctk.CTkEntry(
            input_frame, textvariable=self.nbremboursement_var, height=32, fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            corner_radius=8, font=Fonts.body(11), placeholder_text="1",
            width=90,
        )
        self.nbremb_entry.grid(row=0, column=6, padx=(0, 12), pady=10, sticky="w")

        styled.button_success(
            input_frame, text="Enregistrer", icon="💾", width=150, height=32, command=self.enregistrer_avance
        ).grid(row=0, column=7, padx=(0, 12), pady=10, sticky="e")

        # Card filtres/tri (liste avances spéciales)
        filtres_frame = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        filtres_frame.grid(row=2, column=0, padx=10, pady=(0, 6), sticky="ew")
        filtres_frame.grid_columnconfigure(5, weight=1)

        ctk.CTkLabel(filtres_frame, text="Du", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(row=0, column=0, padx=(12, 6), pady=10, sticky="w")
        self.filter_date_start = styled.date_entry(filtres_frame, width=11, initial=date.today())
        self.filter_date_end = styled.date_entry(filtres_frame, width=11, initial=date.today())
        self.filter_date_start.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="w")

        ctk.CTkLabel(filtres_frame, text="Au", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(row=0, column=2, padx=(0, 6), pady=10, sticky="w")
        self.filter_date_end.grid(row=0, column=3, padx=(0, 10), pady=10, sticky="w")

        ctk.CTkLabel(filtres_frame, text="Recherche", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(row=0, column=4, padx=(0, 6), pady=10, sticky="w")
        self.filter_search_var = ctk.StringVar(value="")
        self.filter_search_entry = ctk.CTkEntry(
            filtres_frame, textvariable=self.filter_search_var, height=32, fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER, corner_radius=8, font=Fonts.body(11), placeholder_text="Nom, prénom, ref…",
        )
        self.filter_search_entry.grid(row=0, column=5, padx=(0, 10), pady=10, sticky="ew")
        self.filter_search_entry.bind("<Return>", lambda e: self.apply_filters())

        ctk.CTkLabel(filtres_frame, text="Tri", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(row=0, column=6, padx=(0, 6), pady=10, sticky="w")
        self.sort_key = ctk.StringVar(value="Date (desc)")
        self.sort_combo = styled.combobox(
            filtres_frame,
            values=["Date (desc)", "Date (asc)", "Personnel (A→Z)", "Personnel (Z→A)", "Montant (desc)", "Montant (asc)"],
            command=lambda *_: self.apply_filters(),
            height=32,
            width=160,
            variable=self.sort_key,
        )
        self.sort_combo.grid(row=0, column=7, padx=(0, 10), pady=10, sticky="w")

        styled.button_secondary(filtres_frame, text="Réinitialiser", icon="↩", width=120, height=32, command=self.reset_filters).grid(
            row=0, column=8, padx=(0, 12), pady=10, sticky="e"
        )

        # Card tableau
        tree_container_frame = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        tree_container_frame.grid(row=3, column=0, padx=10, pady=(0, 6), sticky="nsew")
        tree_container_frame.grid_columnconfigure(0, weight=1)
        tree_container_frame.grid_rowconfigure(0, weight=1)

        # Treeview des avances spéciales (still ttk.Treeview)
        self.tree = ttk.Treeview(
            tree_container_frame,
            columns=("Date", "Référence", "Observation", "Montant", "Nb Remboursement", "Paiement par Mois"),
            show="headings",
            style="P.Treeview",
        )
        self._configure_table_alternating_colors(self.tree)
        self._table_sort = TreeSortController(
            self.tree,
            [
                TreeColumn("Date", sort_key="date", sort_type="date", width=120),
                TreeColumn("Référence", sort_key="ref", width=120),
                TreeColumn("Observation", sort_key="obs", width=120),
                TreeColumn("Montant", sort_key="montant", sort_type="float", width=120),
                TreeColumn("Nb Remboursement", sortable=False, width=120),
                TreeColumn("Paiement par Mois", sortable=False, width=120),
            ],
            sort_state=self._sort_state,
        )
        self._table_sort.on_sort = lambda sk, desc: self.apply_filters(force_sort_key=sk, force_desc=desc)
        self._table_sort.wire_headings()

        # Configuration des scrolls (still ttk.Scrollbar)
        vsb = ttk.Scrollbar(tree_container_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        vsb.grid(row=0, column=1, sticky="ns", pady=6)
        hsb.grid(row=1, column=0, sticky="ew", padx=(6, 0))

        # Section des boutons
        btn_frame = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        btn_frame.grid(row=4, column=0, padx=10, pady=(0, 10), sticky="ew")

        # bouton Enregistrer déplacé dans le formulaire inline
        styled.button_primary(btn_frame, text="Modifier", icon="✏️", width=120, height=32, command=self.modifier_avance).pack(side="left", padx=0, pady=10)
        styled.button_danger(btn_frame, text="Annuler", icon="✖", width=120, height=32, command=self.annuler_saisie).pack(side="left", padx=10, pady=10)
        styled.button_premium(btn_frame, text="Exporter Excel", icon="📊", width=160, height=32, command=self.exporter_excel).pack(side="right", padx=10, pady=10)
        styled.button_premium(btn_frame, text="Exporter PDF", icon="📄", width=150, height=32, command=self.exporter_pdf).pack(side="right", padx=0, pady=10)

        # (UI) poids déjà configurés via grid_columnconfigure ci-dessus

    def charger_avances(self):
        self.cursor.execute("""
            SELECT tap.datepmt, tap.refpmt, tap.observation, tap.mtpaye, tap.nbremboursement, p.nom, p.prenom
            FROM tb_avancespecpers tap
            JOIN tb_personnel p ON tap.idpers = p.id
            ORDER BY tap.datepmt DESC
        """)
        resultats = self.cursor.fetchall()
        self._avances_raw = []
        for ligne in resultats:
            datepmt = ligne[0] if ligne[0] else datetime.now()
            reference = ligne[1] or ""
            observation = ligne[2] or ""
            montant = ligne[3]
            nb_remboursement = ligne[4] or 0
            nom_prof = ligne[5]
            prenom_prof = ligne[6]

            try:
                mt = float(montant) if montant is not None else 0.0
            except Exception:
                mt = 0.0

            try:
                nb = int(nb_remboursement) if nb_remboursement is not None else 0
            except Exception:
                nb = 0

            paiement_par_mois = (mt / nb) if nb else 0.0

            # [LOGIQUE] Observation: éviter les erreurs si prénom NULL
            if "AVS -" in observation:
                expected_name = self._fmt_personnel(nom_prof, prenom_prof)
                if expected_name and expected_name.upper() not in observation.upper():
                    observation = self.generate_observation(nom_prof, prenom_prof)

            self._avances_raw.append({
                "date_dt": datepmt,
                "date_str": datepmt.strftime("%Y-%m-%d %H:%M:%S"),
                "ref": reference,
                "obs": observation,
                "montant": mt,
                "montant_str": f"{mt:,.2f}".replace(",", " ").replace(".", ","),
                "nb_remb": nb,
                "pmt_mois": paiement_par_mois,
                "pmt_mois_str": f"{paiement_par_mois:,.2f}".replace(",", " ").replace(".", ","),
                "personnel": self._fmt_personnel(nom_prof, prenom_prof),
            })
        self.apply_filters()

    def enregistrer_avance(self):
        montant = self.mtpaye_var.get().strip()
        nb_remboursement = self.nbremboursement_var.get().strip()

        if not self.id_prof_selectionne:
            messagebox.showerror("Erreur", "Veuillez sélectionner un personnel.")
            return
        if not montant:
            messagebox.showerror("Erreur", "Veuillez saisir le montant à payer.")
            return
        if not nb_remboursement:
            messagebox.showerror("Erreur", "Veuillez saisir le nombre de remboursements.")
            return

        # Vérifier que iduser est défini
        if not self.iduser:
            messagebox.showerror("Erreur", "L'utilisateur n'est pas connecté. Veuillez vous reconnecter.")
            print("ERREUR: iduser est None lors de l'enregistrement!")
            return

        try:
            montant_val = float(montant.replace(',', '.'))
            nb_remboursement_val = int(nb_remboursement)
            
            if montant_val <= 0 or nb_remboursement_val <= 0:
                messagebox.showerror("Erreur", "Le montant et le nombre de remboursements doivent être supérieurs à zéro.")
                return

            personnel_id = self.id_prof_selectionne

            reference = self.generer_reference()
            # Retrieve professor name and first name for observation
            pers_info = next((p for p in self.personnel if p["id"] == personnel_id), None)
            nom = pers_info["nom"] if pers_info else None
            prenom = pers_info["prenom"] if pers_info else None
            observation = self.generate_observation(nom, prenom)
            date_actuelle = datetime.now()

            print(f"Enregistrement avec iduser: {self.iduser}")  # Debug

            self.cursor.execute("""
                INSERT INTO tb_avancespecpers (refpmt, observation, idpers, mtpaye, nbremboursement, datepmt, idtypeoperation, iduser)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (reference, observation, personnel_id, montant_val, nb_remboursement_val, date_actuelle, 2, self.iduser))

            self.conn.commit()

            try:
                try_imprimer_ticket_avance(
                    self.cursor,
                    "special",
                    reference=reference,
                    date_pmt=date_actuelle,
                    nom_personnel=nom,
                    prenom_personnel=prenom,
                    montant=montant_val,
                    observation=observation,
                    iduser=self.iduser,
                    nb_remboursement=nb_remboursement_val,
                )
            except Exception as exc:
                print(f"Ticket avance spéciale : {exc}")

            messagebox.showinfo("Succès", "Avance enregistrée.")
            self.charger_avances()
            self.annuler_saisie()

        except ValueError:
            messagebox.showerror("Erreur", "Veuillez saisir des valeurs numériques valides pour le montant et le nombre de remboursements.")
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement : {e}")

    def modifier_avance(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showerror("Erreur", "Veuillez sélectionner une avance à modifier.")
            return

        # Get the reference from the selected item
        current_values = self.tree.item(selected_item)['values']
        reference_to_modify = current_values[1]  # Reference is at index 1

        # Fetch the full data for the selected advance from the DB
        self.cursor.execute("""
            SELECT id, observation, idpers, mtpaye, nbremboursement
            FROM tb_avancespecpers
            WHERE refpmt = %s
        """, (reference_to_modify,))
        advance_data = self.cursor.fetchone()

        if not advance_data:
            messagebox.showerror("Erreur", "Détails de l'avance non trouvés.")
            return

        avance_id, current_observation, current_idprof, current_mtpaye, current_nbremboursement = advance_data

        # Create a Toplevel window for editing
        edit_window = ctk.CTkToplevel(self.master)
        edit_window.title("Modifier Avance Spéciale")
        edit_window.geometry("450x250")

        # Get professor's full name
        prof_info = next((p for p in self.personnel if p["id"] == current_idprof), None)
        prof_full_name = prof_info["nom_complet"] if prof_info else "Inconnu"

        ctk.CTkLabel(edit_window, text=f"Personnel: {prof_full_name}").grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(edit_window, text="Nouveau Montant:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        new_mtpaye_var = ctk.CTkEntry(edit_window)
        new_mtpaye_var.insert(0, str(current_mtpaye))
        new_mtpaye_var.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(edit_window, text="Nouveau Nb Remboursement:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        new_nbremboursement_var = ctk.CTkEntry(edit_window)
        new_nbremboursement_var.insert(0, str(current_nbremboursement))
        new_nbremboursement_var.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(edit_window, text="Nouvelle Observation:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        new_observation_var = ctk.CTkEntry(edit_window)
        new_observation_var.insert(0, current_observation)
        new_observation_var.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

        def save_changes():
            try:
                new_montant = float(new_mtpaye_var.get().replace(',', '.'))
                new_nbrem = int(new_nbremboursement_var.get())
                new_obs = new_observation_var.get()

                if new_montant <= 0 or new_nbrem <= 0:
                    messagebox.showerror("Erreur", "Le montant et le nombre de remboursements doivent être supérieurs à zéro.")
                    return

                self.cursor.execute("""
                    UPDATE tb_avancespecpers
                    SET mtpaye = %s, nbremboursement = %s, observation = %s
                    WHERE id = %s
                """, (new_montant, new_nbrem, new_obs, avance_id))
                self.conn.commit()
                messagebox.showinfo("Succès", "Avance modifiée avec succès.")
                edit_window.destroy()
                self.charger_avances()  # Refresh the treeview
            except ValueError:
                messagebox.showerror("Erreur", "Veuillez saisir des valeurs numériques valides.")
            except Exception as e:
                self.conn.rollback()
                messagebox.showerror("Erreur", f"Erreur lors de la modification : {e}")

        ctk.CTkButton(edit_window, text="Enregistrer les modifications", command=save_changes).grid(row=4, column=0, columnspan=2, pady=15)
        edit_window.grab_set()  # Make the Toplevel modal

    def annuler_saisie(self):
        self.id_prof_selectionne = None
        self.selected_personnel_var.set("")
        self.mtpaye_var.set("")
        self.nbremboursement_var.set("")

    def generer_reference(self):
        return datetime.now().strftime("AVS-%Y%m%d-%H%M%S-%f")[:22]
    
    def exporter_excel(self):
        try:
            self.cursor.execute("""
                SELECT p.nom, p.prenom, tap.refpmt, tap.mtpaye, tap.nbremboursement, tap.datepmt, tap.observation
                FROM tb_avancespecpers tap
                JOIN tb_personnel p ON p.id = tap.idpers
                ORDER BY tap.datepmt ASC
            """)
            results = self.cursor.fetchall()
            df = pd.DataFrame(results, columns=["Nom Personnel", "Prénom Personnel", "Référence", "Montant Payé", "Nb Remboursement", "Date Paiement", "Observation"])
            
            # Calculate "Paiement par Mois"
            df["Paiement par Mois"] = df["Montant Payé"] / df["Nb Remboursement"]

            df.to_excel("avances_speciales_personnel.xlsx", index=False)
            messagebox.showinfo("Exportation", "Exportation Excel réussie !")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'exportation Excel : {e}")

    def exporter_pdf(self):
        try:
            self.cursor.execute("""
                SELECT p.nom, p.prenom, tap.refpmt, tap.mtpaye, tap.nbremboursement, tap.datepmt, tap.observation
                FROM tb_avancespecpers tap
                JOIN tb_personnel p ON p.id = tap.idpers
                ORDER BY tap.datepmt ASC
            """)
            data = self.cursor.fetchall()

            if not data:
                messagebox.showinfo("Info", "Aucune avance spéciale à exporter.")
                return

            pdf = canvas.Canvas("avances_speciales_personnel.pdf", pagesize=letter)
            pdf.setFont("Helvetica", 10)
            
            y_position = 750
            page_width, page_height = letter

            pdf.drawString(50, y_position, "Liste des Avances Spéciales des Personnel")
            y_position -= 20

            # Headers
            headers = ["Date", "Réf.", "Personnel", "Montant", "Nb Remb.", "Pmt/Mois", "Observation"]
            col_widths = [80, 70, 100, 60, 60, 60, 120]

            # Draw headers
            x_start = 50
            for i, header in enumerate(headers):
                pdf.drawString(x_start + sum(col_widths[:i]), y_position, header)
            y_position -= 15

            # Draw a line under headers
            pdf.line(50, y_position, page_width - 50, y_position)
            y_position -= 15

            for nom_prof, prenom_prof, reference, montant, nb_remboursement, date_pmt, observation in data:
                if y_position < 50:  # Check if new page is needed
                    pdf.showPage()
                    pdf.setFont("Helvetica", 10)
                    y_position = 750
                    pdf.drawString(50, y_position, "Liste des Avances Spéciales des personnels (suite)")
                    y_position -= 20
                    for i, header in enumerate(headers):
                        pdf.drawString(x_start + sum(col_widths[:i]), y_position, header)
                    y_position -= 15
                    pdf.line(50, y_position, page_width - 50, y_position)
                    y_position -= 15

                # Calculate "Paiement par Mois"
                paiement_par_mois = montant / nb_remboursement if nb_remboursement else 0

                # Format data for PDF
                display_date = date_pmt.strftime("%Y-%m-%d")
                display_prof = f"{nom_prof} {prenom_prof}"
                display_montant = f"{montant:,.2f}".replace(',', ' ').replace('.', ',')
                display_nbremb = str(nb_remboursement)
                display_pmt_mois = f"{paiement_par_mois:,.2f}".replace(',', ' ').replace('.', ',')
                display_obs = observation

                row_data = [
                    display_date,
                    reference,
                    display_prof,
                    display_montant,
                    display_nbremb,
                    display_pmt_mois,
                    display_obs
                ]

                # Draw row data
                for i, item in enumerate(row_data):
                    pdf.drawString(x_start + sum(col_widths[:i]), y_position, str(item))
                y_position -= 15

            pdf.save()
            messagebox.showinfo("Exportation", "Exportation PDF réussie !")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'exportation PDF : {e}")

    def __del__(self):
        """Ferme proprement la connexion à la base de données lors de la destruction de l'objet."""
        if hasattr(self, 'cursor') and self.cursor:
            self.cursor.close()
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()


# ---
if __name__ == "__main__":
    ctk.set_appearance_mode("Light")  # Modes: "System" (default), "Dark", "Light"
    ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"

    app = ctk.CTk()
    app.title("Avance Spéciale des Personnels")
    app.geometry("1000x700")

    # Pour tester: utiliser un iduser fictif
    fenetre_avance_spec = FenetreAvanceSpec(master=app, iduser=1)
    fenetre_avance_spec.pack(fill="both", expand=True)

    app.mainloop()
