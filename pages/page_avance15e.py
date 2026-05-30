import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime, date
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os
import json
import sys
from resource_utils import get_config_path, safe_file_read
try:
    from tkcalendar import DateEntry
except Exception:  # tkcalendar non installé → fallback sur Entry texte
    DateEntry = None
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

def generer_reference():
    now = datetime.now()
    return now.strftime("AVQ-%Y%m%d%H%M%S%f")[:-3]

def generate_observation(nom_prof, prenom_prof):
    today = date.today().strftime("%d%m%Y")
    # [LOGIQUE] Robuste aux valeurs NULL en base / sélection incomplète
    nom = (nom_prof or "").strip()
    prenom = (prenom_prof or "").strip()
    nom_fmt = nom.upper() if nom else "INCONNU"
    prenom_fmt = prenom.capitalize() if prenom else ""
    sep = " " if prenom_fmt else ""
    return f"AVQ - {nom_fmt}{sep}{prenom_fmt} - {today}"

class PageAVQ(ctk.CTkFrame):
    def __init__(self, master=None, iduser=None):
        # [UI] Harmonisation de l’interface Avance 15e avec app_theme (header/cards/boutons/table)
        # [LOGIQUE] Aucune modification des règles métier/SQL ; uniquement UI et styles
        super().__init__(master, fg_color=Colors.BG_PAGE)
        self.master = master
        self.id_prof_selectionne = None
        self.selected_personnel_var = ctk.StringVar(value="")
        self.iduser = iduser if iduser is not None else resolve_connected_user_id(master=master)
        self._avances_raw = []
        self._sort_state = new_sort_state()
        self._table_sort = None

        # Afficher l'iduser pour le débogage
        if self.iduser:
            print(f"FenetreAvance initialisée avec iduser: {self.iduser}")
        else:
            print("ATTENTION: FenetreAvanceSpec initialisée sans iduser!")
        
        # Connexion à la base de données
        self.conn = self.connect_db()
        self.cursor = None
        
        if self.conn:
            self.cursor = self.conn.cursor()
            self.initialize_database()
        
        self.create_widgets()
        self.charger_avances()

    def _setup_treeview_style(self):
        # [UI] Style Treeview cohérent avec les pages modernes du projet
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

    def _configure_table_alternating_colors(self, tree):
        # [UI] Palette alignée au thème iJeery
        tree.tag_configure("row_even", background=Colors.BG_CARD)
        tree.tag_configure("row_odd", background=Colors.BG_ROW_ALT)

    def _refresh_table_alternating_colors(self, tree):
        for idx, item in enumerate(tree.get_children()):
            tree.item(item, tags=("row_even" if idx % 2 == 0 else "row_odd",))

    def initialize_database(self):
        """Initialise la connexion à la base de données et crée la table si nécessaire."""
        if not self.cursor:
            return False
        
        try:
            # Création de la table si elle n'existe pas
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS tb_avanceprof (
                    id SERIAL PRIMARY KEY,
                    refpmt VARCHAR(50),
                    idpers INT REFERENCES tb_personnel(id),
                    mtpaye DOUBLE PRECISION,
                    observation VARCHAR(120),
                    datepmt TIMESTAMP,
                    etat INT,
                    idtypeoperation INT,
                    iduser INT
                )
            """)
            self.conn.commit()
            return True
            
        except psycopg2.Error as err:
            messagebox.showerror("Erreur de connexion", f"Erreur : {err}")
            return False

    def charger_personnel_pour_avance(self, filtre=""):
        """Charge la liste du personnel pour les avances"""
        try:
            if self.cursor:
                self.cursor.execute("SELECT id, nom, prenom FROM tb_personnel ORDER BY nom")
                personnel = self.cursor.fetchall()
                liste_personnel = []
                for id_prof, nom, prenom in personnel:
                    if filtre.lower() in nom.lower() or filtre.lower() in prenom.lower():
                        liste_personnel.append(f"{nom} {prenom} (ID: {id_prof})")
                return liste_personnel
        except Exception as e:
            print(f"Erreur lors du chargement des professeurs : {e}")
        return []

    def create_widgets(self):
        # [UI] Header + cards pour une lecture plus claire (même logique que Suivi de présence)
        self._setup_treeview_style()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        header = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT, corner_radius=0, height=46)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)

        left = styled.frame(header)
        left.grid(row=0, column=0, padx=14, sticky="w")
        ctk.CTkLabel(left, text="💸", font=Fonts.heading(16), text_color=Colors.TEXT_ON_DARK).pack(side="left", padx=(0, 8))
        inner = styled.frame(left)
        inner.pack(side="left")
        ctk.CTkLabel(inner, text="Avance 15e", font=Fonts.bold(13), text_color=Colors.TEXT_ON_DARK).pack(anchor="w")
        ctk.CTkLabel(inner, text="Saisie et gestion des avances quinzaine", font=Fonts.small(9), text_color=Colors.TEXT_ON_DARK_DIM).pack(anchor="w")

        # Card saisie
        saisie_frame = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        saisie_frame.grid(row=1, column=0, padx=10, pady=(10, 6), sticky="ew")
        # [UI] Bloc inline : recherche personnel + montant + enregistrer sur une seule ligne
        saisie_frame.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(saisie_frame, text="Personnel", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(
            row=0, column=0, padx=(12, 6), pady=10, sticky="w"
        )
        styled.button_primary(
            saisie_frame, text="Rechercher", icon="🔎", width=120, height=32, command=self.open_personnel_picker
        ).grid(row=0, column=1, padx=(0, 8), pady=10, sticky="w")

        self.selected_personnel_entry = ctk.CTkEntry(
            saisie_frame,
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

        ctk.CTkLabel(saisie_frame, text="Montant", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(
            row=0, column=3, padx=(0, 6), pady=10, sticky="w"
        )
        self.montant_entry = ctk.CTkEntry(
            saisie_frame, width=150, height=32, fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            corner_radius=8, font=Fonts.body(11), placeholder_text="0,00",
        )
        self.montant_entry.grid(row=0, column=4, padx=(0, 10), pady=10, sticky="w")

        styled.button_success(saisie_frame, text="Enregistrer", icon="💾", width=150, height=32, command=self.enregistrer_avance).grid(
            row=0, column=5, padx=(0, 12), pady=10, sticky="e"
        )

        # Card filtres/tri (liste avances)
        filtres_frame = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        filtres_frame.grid(row=2, column=0, padx=10, pady=(0, 6), sticky="ew")
        for c in range(0, 9):
            filtres_frame.grid_columnconfigure(c, weight=0)
        filtres_frame.grid_columnconfigure(5, weight=1)

        ctk.CTkLabel(filtres_frame, text="Du", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(row=0, column=0, padx=(12, 6), pady=10, sticky="w")
        if DateEntry:
            de_kw = dict(width=12, background=Colors.PRIMARY_HOVER, foreground=Colors.TEXT_ON_DARK, borderwidth=2, date_pattern="yyyy-mm-dd")
            self.filter_date_start = DateEntry(filtres_frame, **de_kw)
            self.filter_date_end = DateEntry(filtres_frame, **de_kw)
        else:
            self.filter_date_start = ctk.CTkEntry(filtres_frame, width=120, height=32, fg_color=Colors.BG_INPUT, border_color=Colors.BORDER, corner_radius=8, font=Fonts.body(11), placeholder_text="YYYY-MM-DD")
            self.filter_date_end = ctk.CTkEntry(filtres_frame, width=120, height=32, fg_color=Colors.BG_INPUT, border_color=Colors.BORDER, corner_radius=8, font=Fonts.body(11), placeholder_text="YYYY-MM-DD")
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

        # Treeview for displaying advances
        tree_frame = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        tree_frame.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="nsew")
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        # Use ttk.Treeview as CTkTreeview doesn't exist
        self.treeview = ttk.Treeview(tree_frame, columns=("Date", "Référence", "Observation", "Montant", "ID", "Personnel"), show="headings", style="P.Treeview")
        self._table_sort = TreeSortController(
            self.treeview,
            [
                TreeColumn("Date", sort_key="date", sort_type="date", width=150),
                TreeColumn("Référence", sort_key="ref", width=120),
                TreeColumn("Observation", sort_key="obs", width=200),
                TreeColumn("Montant", sort_key="montant", sort_type="float", width=80, anchor="e"),
                TreeColumn("ID", sortable=False, width=0, stretch=False),
                TreeColumn("Personnel", sort_key="personnel", width=150),
            ],
            sort_state=self._sort_state,
        )
        self._table_sort.on_sort = lambda sk, desc: self.apply_filters(force_sort_key=sk, force_desc=desc)
        self._table_sort.wire_headings()
        self._configure_table_alternating_colors(self.treeview)

        self.treeview.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.treeview.yview)
        self.treeview.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns", pady=6)

        # Frame pour les boutons
        buttons_frame = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        buttons_frame.grid(row=4, column=0, padx=10, pady=(0, 10), sticky="ew")

        # Buttons for Modify and Cancel
        styled.button_primary(buttons_frame, text="Modifier", icon="✏️", width=120, height=32, command=self.modifier_avance).pack(side="left", padx=10, pady=10)
        styled.button_danger(buttons_frame, text="Annuler", icon="✖", width=120, height=32, command=self.annuler_avance).pack(side="left", padx=0, pady=10)
        styled.button_premium(buttons_frame, text="Exporter PDF", icon="📄", width=140, height=32, command=self.exporter_pdf).pack(side="right", padx=10, pady=10)
        styled.button_premium(buttons_frame, text="Exporter Excel", icon="📊", width=150, height=32, command=self.exporter_excel).pack(side="right", padx=0, pady=10)

    def selectionner_personnel_event(self, event):
        # This method is called by the ttk.Combobox event binding
        selection = getattr(self, "liste_personnel_combo", None)
        if selection:
            self.selectionner_personnel(selection.get())

    def selectionner_personnel(self, selection):
        self.id_prof_selectionne = None
        if selection:
            try:
                self.id_prof_selectionne = int(selection.split('(ID: ')[1][:-1])
            except (IndexError, ValueError):
                messagebox.showerror("Erreur", "Format de personnel invalide.")

    def _fmt_personnel(self, nom, prenom):
        # [UI] Affichage propre: prenom None → "-"
        nom_s = (nom or "").strip()
        prenom_s = (prenom or "").strip() if prenom is not None else ""
        prenom_s = prenom_s if prenom_s else "-"
        nom_s = nom_s if nom_s else "-"
        return f"{nom_s} {prenom_s}".strip()

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
                rows = self.cursor.fetchall()
                for _id, nom, prenom in rows:
                    nom_disp = (nom or "").strip() if nom is not None else ""
                    prenom_disp = (prenom or "").strip() if prenom is not None else ""
                    nom_disp = nom_disp if nom_disp else "-"
                    prenom_disp = prenom_disp if prenom_disp else "-"
                    tv.insert("", "end", values=(_id, nom_disp, prenom_disp))
            except Exception:
                # pas bloquant: on laisse vide
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
        footer.grid_columnconfigure(0, weight=1)
        styled.button_secondary(footer, text="Annuler", icon="✖", width=120, height=32, command=top.destroy).pack(side="right")
        styled.button_success(footer, text="Sélectionner", icon="✅", width=140, height=32, command=_select).pack(side="right", padx=(0, 8))

        _fill("")
        q_entry.focus_set()

    # ──────────────────────────────────────────────────────────────────────
    # [UI] Filtres + tri liste avances (client-side)
    # ──────────────────────────────────────────────────────────────────────

    def _get_date_filter_value(self, w):
        if DateEntry and hasattr(w, "get_date"):
            return w.get_date().strftime("%Y-%m-%d")
        if hasattr(w, "get"):
            return (w.get() or "").strip()
        return ""

    def reset_filters(self):
        try:
            self.filter_search_var.set("")
        except Exception:
            pass
        if DateEntry:
            try:
                self.filter_date_start.set_date(date.today())
                self.filter_date_end.set_date(date.today())
            except Exception:
                pass
        else:
            try:
                self.filter_date_start.delete(0, ctk.END)
                self.filter_date_end.delete(0, ctk.END)
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
        # build filtered list from self._avances_raw
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
            # r: dict(date_dt, date_str, ref, obs, montant, id, personnel)
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

        # sort selection
        sort_mode = (self.sort_key.get() if hasattr(self, "sort_key") else "Date (desc)")
        if force_sort_key:
            # mapping from header click
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
            else:  # Date (desc)
                rows.sort(key=lambda x: x.get("date_dt") or datetime.min, reverse=True)

        # render
        for item in self.treeview.get_children():
            self.treeview.delete(item)
        if self._table_sort:
            self._table_sort.refresh_headings()
        for r in rows:
            self.treeview.insert(
                "",
                "end",
                values=(
                    r["date_str"],
                    r["ref"],
                    r["obs"],
                    r["montant_str"],
                    r["id"],
                    r["personnel"],
                ),
            )
        self._refresh_table_alternating_colors(self.treeview)

    def enregistrer_avance(self):
        if self.id_prof_selectionne is None:
            messagebox.showerror("Erreur", "Veuillez sélectionner un personnel.")
            return

        montant_str = self.montant_entry.get().replace(" ", "").replace(",", ".")
        try:
            montant_paye = float(montant_str)
            if montant_paye <= 0:
                messagebox.showerror("Erreur", "Le montant de l'avance doit être supérieur à zéro.")
                return
        except ValueError:
            messagebox.showerror("Erreur", "Montant invalide.")
            return

        # Vérifier que iduser est défini
        if not self.iduser:
            messagebox.showerror("Erreur", "L'utilisateur n'est pas connecté. Veuillez vous reconnecter.")
            print("ERREUR: iduser est None lors de l'enregistrement!")
            return

        try:
            if not self.conn or not self.cursor:
                messagebox.showerror("Erreur de connexion", "Impossible de se connecter à la base de données.")
                return

            self.cursor.execute("SELECT nom, prenom FROM tb_personnel WHERE id = %s", (self.id_prof_selectionne,))
            personnel = self.cursor.fetchone()
            if not personnel:
                messagebox.showerror("Erreur", "Personnel non trouvé.")
                return

            observation = generate_observation(personnel[0], personnel[1])
            reference = generer_reference()
            date_paiement = datetime.now()
            type_operation = "2"

            self.cursor.execute("""
                INSERT INTO tb_avancepers (refpmt, idpers, mtpaye, observation, datepmt, idtypeoperation, iduser)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (reference, self.id_prof_selectionne, montant_paye, observation, date_paiement, type_operation, self.iduser))
            self.conn.commit()
            try:
                try_imprimer_ticket_avance(
                    self.cursor,
                    "15e",
                    reference=reference,
                    date_pmt=date_paiement,
                    nom_personnel=personnel[0],
                    prenom_personnel=personnel[1],
                    montant=montant_paye,
                    observation=observation,
                    iduser=self.iduser,
                )
            except Exception as exc:
                print(f"Ticket avance 15e : {exc}")
            messagebox.showinfo("Succès", "Avance enregistrée avec succès !")
            self.rafraichir_treeview()
            self.montant_entry.delete(0, ctk.END)
            self.selected_personnel_var.set("")
            self.id_prof_selectionne = None
        except psycopg2.Error as e:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement : {e}")

    def modifier_avance(self):
        selection = self.treeview.selection()
        if not selection:
            messagebox.showerror("Erreur", "Veuillez sélectionner une avance à modifier.")
            return

        avance_id = self.treeview.item(selection[0])['values'][4]

        try:
            if not self.conn or not self.cursor:
                messagebox.showerror("Erreur de connexion", "Impossible de se connecter à la base de données.")
                return

            self.cursor.execute("SELECT idpers, mtpaye, observation FROM tb_avancepers WHERE id = %s", (avance_id,))
            avance_actuelle = self.cursor.fetchone()
            if not avance_actuelle:
                messagebox.showerror("Erreur", "Impossible de récupérer les détails de l'avance.")
                return

            fenetre_modification = ctk.CTkToplevel(self)
            fenetre_modification.title("Modifier l'avance")
            fenetre_modification.geometry("400x200")

            self.cursor.execute("SELECT nom, prenom FROM tb_personnel WHERE id = %s", (avance_actuelle[0],))
            personnel = self.cursor.fetchone()
            nom_professeur = f"{personnel[0]} {personnel[1]}" if personnel else "Inconnu"

            ctk.CTkLabel(fenetre_modification, text="Personnel:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            ctk.CTkLabel(fenetre_modification, text=nom_professeur).grid(row=0, column=1, padx=5, pady=5, sticky="w")

            ctk.CTkLabel(fenetre_modification, text="Nouveau Montant:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
            nouveau_montant_entry = ctk.CTkEntry(fenetre_modification)
            nouveau_montant_entry.insert(0, str(avance_actuelle[1]))
            nouveau_montant_entry.grid(row=1, column=1, padx=5, pady=5)

            ctk.CTkLabel(fenetre_modification, text="Nouvelle Observation:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
            nouvelle_observation_entry = ctk.CTkEntry(fenetre_modification)
            nouvelle_observation_entry.insert(0, avance_actuelle[2])
            nouvelle_observation_entry.grid(row=2, column=1, padx=5, pady=5)

            def valider_modification():
                nouveau_montant_str = nouveau_montant_entry.get().replace(" ", "").replace(",", ".")
                try:
                    nouveau_montant = float(nouveau_montant_str)
                    if nouveau_montant <= 0:
                        messagebox.showerror("Erreur", "Le montant doit être supérieur à zéro.")
                        return
                except ValueError:
                    messagebox.showerror("Erreur", "Montant invalide.")
                    return

                nouvelle_observation = nouvelle_observation_entry.get()

                try:
                    self.cursor.execute("""
                        UPDATE tb_avancepers
                        SET mtpaye = %s, observation = %s
                        WHERE id = %s
                    """, (nouveau_montant, nouvelle_observation, avance_id))
                    self.conn.commit()
                    messagebox.showinfo("Succès", "Avance modifiée avec succès !")
                    self.rafraichir_treeview()
                    fenetre_modification.destroy()
                except psycopg2.Error as e:
                    self.conn.rollback()
                    messagebox.showerror("Erreur", f"Erreur lors de la modification : {e}")

            ctk.CTkButton(fenetre_modification, text="Enregistrer les modifications", 
                         command=valider_modification).grid(row=3, column=0, columnspan=2, pady=10)
                         
        except psycopg2.Error as e:
            messagebox.showerror("Erreur", f"Erreur lors de la récupération des données : {e}")

    def annuler_avance(self):
        selection = self.treeview.selection()
        if not selection:
            messagebox.showerror("Erreur", "Veuillez sélectionner une avance à annuler.")
            return

        avance_id = self.treeview.item(selection[0])['values'][4]

        if messagebox.askyesno("Confirmation", "Êtes-vous sûr de vouloir annuler cette avance ?"):
            try:
                if not self.conn or not self.cursor:
                    messagebox.showerror("Erreur de connexion", "Impossible de se connecter à la base de données.")
                    return
                self.cursor.execute("DELETE FROM tb_avancepers WHERE id = %s", (avance_id,))
                self.conn.commit()
                messagebox.showinfo("Succès", "Avance annulée avec succès !")
                self.rafraichir_treeview()
            except psycopg2.Error as e:
                self.conn.rollback()
                messagebox.showerror("Erreur", f"Erreur lors de l'annulation : {e}")

    def rafraichir_treeview(self):
        for item in self.treeview.get_children():
            self.treeview.delete(item)
        self._refresh_table_alternating_colors(self.treeview)
        self.charger_avances()

    def charger_avances(self):
        try:
            if not self.cursor:
                return

            self.cursor.execute("""
                SELECT a.datepmt, a.refpmt, a.observation, a.mtpaye, a.id, p.nom, p.prenom
                FROM tb_avancepers a
                JOIN tb_personnel p ON a.idpers = p.id
                WHERE a.mtpaye > 0
                ORDER BY a.datepmt DESC
            """)
            avances = self.cursor.fetchall()
            self._avances_raw = []
            for date_pmt, reference, observation, montant, id_avance, nom_prof, prenom_prof in avances:
                personnel = self._fmt_personnel(nom_prof, prenom_prof)
                date_str = date_pmt.strftime("%Y-%m-%d %H:%M:%S")
                try:
                    mt = float(montant) if montant is not None else 0.0
                except Exception:
                    mt = 0.0
                self._avances_raw.append({
                    "date_dt": date_pmt,
                    "date_str": date_str,
                    "ref": reference or "",
                    "obs": observation or "",
                    "montant": mt,
                    "montant_str": f"{mt:.2f}",
                    "id": id_avance,
                    "personnel": personnel,
                })
            self.apply_filters()
        except psycopg2.Error as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des avances : {e}")

    def exporter_excel(self):
        try:
            if not self.cursor:
                return
            self.cursor.execute("""
                SELECT p.nom, p.prenom, a.refpmt, a.mtpaye, a.datepmt, a.observation
                FROM tb_avancepers a
                JOIN tb_personnel p ON p.id = a.idpers
                WHERE a.mtpaye > 0
                ORDER BY a.datepmt ASC
            """)
            results = self.cursor.fetchall()
            if not results:
                messagebox.showinfo("Info", "Aucune donnée à exporter.")
                return
                
            df = pd.DataFrame(results, columns=["Nom", "Prénom", "Référence", "Montant", "Date", "Observation"])
            df.to_excel("avances_personnel.xlsx", index=False)
            messagebox.showinfo("Exportation", "Exportation Excel réussie !")
            try:
                from log_utils import AppLogger, resolve_connected_user_id
                AppLogger(session_data=getattr(self, "session_data", {}) or {}).log(
                    action="Export Excel",
                    element="Avance 15e",
                    details=f"export avances personnel, lignes={len(df)}, fichier=avances_personnel.xlsx",
                    value="avances_personnel.xlsx",
                )
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'exportation Excel : {e}")

    def exporter_pdf(self):
        try:
            if not self.cursor:
                return
            self.cursor.execute("""
                SELECT p.nom, p.prenom, a.refpmt, a.mtpaye, a.datepmt, a.observation
                FROM tb_avancepers a
                JOIN tb_personnel p ON p.id = a.idpers
                WHERE a.mtpaye > 0
                ORDER BY a.datepmt ASC
            """)
            data = self.cursor.fetchall()

            if not data:
                messagebox.showinfo("Info", "Aucune avance à exporter.")
                return

            pdf = canvas.Canvas("avances_personnel.pdf", pagesize=letter)
            pdf.setFont("Helvetica", 10)
            pdf.drawString(50, 750, "Liste des Avances des Personnel")
            y = 730
            for nom, prenom, reference, montant, date_pmt, observation in data:
                line = f"{date_pmt.strftime('%Y-%m-%d %H:%M:%S')} | Réf: {reference} | Prof: {nom} {prenom} | Montant: {montant:.2f} | Obs: {observation}"
                pdf.drawString(50, y, line)
                y -= 15
                if y < 50:
                    pdf.showPage()
                    pdf.setFont("Helvetica", 10)
                    y = 750
            pdf.save()
            messagebox.showinfo("Exportation", "Exportation PDF réussie !")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'exportation PDF : {e}")

    def __del__(self):
        """Destructeur pour fermer proprement les connexions"""
        if hasattr(self, 'cursor') and self.cursor:
            self.cursor.close()
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

def main():
    ctk.set_appearance_mode("Light")  # Modes: "System" (default), "Dark", "Light"
    ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"

    app = ctk.CTk()
    app.title("Gestion des Avances 15e Personnel")
    app.geometry("800x600")

    # Pour tester: utiliser un iduser fictif
    page_avq = PageAVQ(master=app, iduser=1)
    page_avq.pack(fill="both", expand=True)

    page_avq = PageAVQ(master=app)
    page_avq.pack(fill="both", expand=True)

    app.mainloop()

if __name__ == "__main__":
    main()
