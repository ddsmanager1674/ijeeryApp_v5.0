import customtkinter as ctk
import tkinter.messagebox as messagebox
from datetime import datetime, date, time, timedelta
import psycopg2
from tkcalendar import DateEntry
import tkinter.ttk as ttk
import pandas as pd # For Excel export
from reportlab.lib.pagesizes import letter, landscape # For PDF export
from reportlab.pdfgen import canvas # For PDF export
import os # For file path operations
import subprocess # For opening the exported file
import json
import sys
from resource_utils import get_config_path, safe_file_read

from app_theme import Colors, Fonts, styled, Layout
from log_utils import AppLogger


# Ensure the parent directory is in the Python path for absolute imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    
class DatabaseManager:
    def __init__(self):
        self.db_params = self._load_db_config()
        self.conn = None
        self.cursor = None

    def _load_db_config(self):
        """Loads database configuration from 'config.json'."""
        try:
            config_path = get_config_path('config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('database')
        except FileNotFoundError:
            print("Error: 'config.json' not found.")
            return None
        except KeyError:
            print("Error: 'database' key is missing in 'config.json'.")
            return None
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in 'config.json': {e}")
            return None
        except UnicodeDecodeError as e:
            print(f"Error: Encoding problem in 'config.json': {e}")
            return None

    def connect(self):
        """Establishes a new database connection."""
        if self.db_params is None:
            print("Cannot connect: Database configuration is missing.")
            return False

        try:
            self.conn = psycopg2.connect(
                host=self.db_params['host'],
                user=self.db_params['user'],
                password=self.db_params['password'],
                database=self.db_params['database'],
                port=self.db_params['port'],
                client_encoding='UTF8'
            )
            self.cursor = self.conn.cursor()
            print("Connection to the database successful!")
            return True
        except psycopg2.OperationalError as e:
            print(f"Error connecting to the database: {e}")
            self.conn = None
            self.cursor = None
            return False
        except Exception as e:
            print(f"Unexpected error connecting to database: {e}")
            self.conn = None
            self.cursor = None
            return False

    def get_connection(self):
        """Returns the database connection if connected, otherwise attempts to connect."""
        if self.conn is None or self.conn.closed:
            if self.connect():
                return self.conn
            else:
                return None
        return self.conn

    def close(self):
        """Closes the database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

# Instantiate DatabaseManager
db_manager = DatabaseManager()

# Global database connection (as per your original setup)
# Instantiate DatabaseManager and establish a connection
db_manager = DatabaseManager()
conn = db_manager.get_connection()

if conn is None:
    messagebox.showerror("Erreur de connexion", "Impossible de se connecter à la base de données.")
    
cursor = conn.cursor()
    

# Global sort_order for column sorting
sort_order = {}



def sort_column(tv, col, col_index):
    """Sorts the Treeview column data."""
    global sort_order
    data = [(tv.set(k, col), k) for k in tv.get_children('')]
    try:
        if col in ["Taux horaire", "Total Heure", "Montant", "Avance 15e", "Déduction", "Net à payer"]:
            # Handle French number format for sorting
            data.sort(key=lambda t: float(str(t[0]).replace('.', '').replace(',', '.')),
                      reverse=sort_order.get(col, False))
        else:
            data.sort(key=lambda t: str(t[0]).lower(),
                      reverse=sort_order.get(col, False))
    except Exception:
        data.sort(reverse=sort_order.get(col, False))

    for index, (val, k) in enumerate(data):
        tv.move(k, '', index)

    sort_order[col] = not sort_order.get(col, False)

#---

## PageEtatSalaireHoraire Class

#```python
class PageEtatSalaireHoraire(ctk.CTkFrame):
    def __init__(self, parent):
        # [UI] Salaire Horaire — thème iJeery (remplace ThemeManager / couleurs ad hoc)
        super().__init__(parent, fg_color=Colors.BG_PAGE)
        self.conn = conn
        self.cursor = cursor
        self.session_data = getattr(parent, "session_data", None) or {}
        self._logger = AppLogger(conn=self.conn, session_data=self.session_data)

        self.current_export_data = []
        self.selected_personnel_id = None
        self.selected_personnel_var = ctk.StringVar(value="")

        self._setup_treeview_style()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT, corner_radius=0, height=46)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        left = styled.frame(header)
        left.pack(side="left", padx=14)
        ctk.CTkLabel(left, text="📊", font=Fonts.heading(16), text_color=Colors.TEXT_ON_DARK).pack(side="left", padx=(0, 8))
        inner = styled.frame(left)
        inner.pack(side="left")
        ctk.CTkLabel(inner, text="Salaire Horaire", font=Fonts.bold(13), text_color=Colors.TEXT_ON_DARK).pack(anchor="w")
        ctk.CTkLabel(inner, text="État par période et export", font=Fonts.small(9), text_color=Colors.TEXT_ON_DARK_DIM).pack(anchor="w")

        toolbar = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        toolbar.grid(row=1, column=0, sticky="ew", padx=10, pady=(10, 6))
        for c in (1, 4, 7):
            toolbar.grid_columnconfigure(c, weight=1)

        ctk.CTkLabel(toolbar, text="Date début", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(row=0, column=0, padx=(12, 6), pady=(10, 2), sticky="w")
        ctk.CTkLabel(toolbar, text="Date fin", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(row=0, column=1, padx=(8, 6), pady=(10, 2), sticky="w")
        ctk.CTkLabel(toolbar, text="Période", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(row=0, column=2, padx=(8, 6), pady=(10, 2), sticky="w")
        ctk.CTkLabel(toolbar, text="Recherche", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(row=0, column=4, columnspan=2, padx=(8, 6), pady=(10, 2), sticky="w")

        de_kw = dict(width=12, background=Colors.PRIMARY_HOVER, foreground=Colors.TEXT_ON_DARK, borderwidth=2, date_pattern="dd/mm/yyyy")
        self.entry_start = DateEntry(toolbar, **de_kw)
        self.entry_start.grid(row=1, column=0, padx=(12, 8), pady=(0, 10), sticky="w")
        self.entry_end = DateEntry(toolbar, **de_kw)
        self.entry_end.grid(row=1, column=1, padx=(0, 8), pady=(0, 10), sticky="w")

        # [UI] Presets période : Jour / Semaine / Mois
        presets = ctk.CTkFrame(toolbar, fg_color="transparent")
        presets.grid(row=1, column=2, padx=6, pady=(0, 10), sticky="w")
        styled.button_secondary(presets, text="Jour", icon="📅", width=86, height=32, command=lambda: self.set_period_preset("day")).pack(side="left")
        styled.button_secondary(presets, text="Semaine", icon="🗓", width=96, height=32, command=lambda: self.set_period_preset("week")).pack(side="left", padx=(6, 0))
        styled.button_secondary(presets, text="Mois", icon="📆", width=86, height=32, command=lambda: self.set_period_preset("month")).pack(side="left", padx=(6, 0))

        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            toolbar, textvariable=self.search_var, height=32, fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            corner_radius=8, font=Fonts.body(11), placeholder_text="Nom / prénom…",
        )
        self.search_entry.grid(row=1, column=4, columnspan=2, padx=(0, 8), pady=(0, 10), sticky="ew")
        self.search_entry.bind("<Return>", lambda e: self.load_data())

        styled.button_success(toolbar, text="Valider", icon="🔍", width=110, height=32, command=self.load_data).grid(row=1, column=6, padx=4, pady=(0, 10), sticky="e")
        styled.button_premium(toolbar, text="Excel", icon="📊", width=100, height=32, command=self.export_excel).grid(row=1, column=7, padx=4, pady=(0, 10), sticky="e")
        styled.button_premium(toolbar, text="PDF", icon="📄", width=100, height=32, command=self.export_pdf).grid(row=1, column=8, padx=(4, 12), pady=(0, 10), sticky="e")

        self.columns = ("Nom", "Prénom", "Taux horaire", "Total Heure", "Montant", "Avance 15e", "Déduction", "Net à payer")

        # Contenu: état (gauche) + saisie heures (droite)
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 6))
        content.grid_columnconfigure(0, weight=3)
        content.grid_columnconfigure(1, weight=2)
        content.grid_rowconfigure(0, weight=1)

        table_card = ctk.CTkFrame(content, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        table_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        table_card.grid_rowconfigure(0, weight=1)
        table_card.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(table_card, columns=self.columns, show="headings", style="P.Treeview", selectmode="browse")
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        self._configure_table_alternating_colors(self.tree)

        for col in self.columns:
            self.tree.heading(col, text=col, command=lambda c=col, i=self.columns.index(col): sort_column(self.tree, c, i))
            self.tree.column(col, anchor="center", width=100)

        self.tree.column("Nom", anchor="w", width=120)
        self.tree.column("Prénom", anchor="w", width=120)
        self.tree.column("Taux horaire", width=100)
        self.tree.column("Total Heure", width=100)
        self.tree.column("Montant", width=100)
        self.tree.column("Avance 15e", width=100)
        self.tree.column("Déduction", width=100)
        self.tree.column("Net à payer", width=100)

        self.vsb = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        self.vsb.grid(row=0, column=1, sticky="ns", pady=6)
        self.tree.configure(yscrollcommand=self.vsb.set)

        right = ctk.CTkFrame(content, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        right.grid_columnconfigure(0, weight=1)
        # [UI] Responsive: l'historique prend l'espace, pas le formulaire
        right.grid_rowconfigure(9, weight=1)

        ctk.CTkLabel(right, text="Saisie heures", font=Fonts.bold(12), text_color=Colors.TEXT_PRIMARY).grid(
            row=0, column=0, padx=12, pady=(12, 6), sticky="w"
        )

        ctk.CTkLabel(right, text="Personnel", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(
            row=1, column=0, padx=12, pady=(6, 2), sticky="w"
        )
        pick = ctk.CTkFrame(right, fg_color="transparent")
        pick.grid(row=2, column=0, padx=12, pady=(0, 10), sticky="ew")
        pick.grid_columnconfigure(1, weight=1)
        styled.button_primary(pick, text="Rechercher", icon="🔎", width=120, height=32, command=self.open_personnel_picker).grid(
            row=0, column=0, padx=(0, 8), pady=0, sticky="w"
        )
        self.selected_personnel_entry = ctk.CTkEntry(
            pick, textvariable=self.selected_personnel_var, height=32, fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            corner_radius=8, font=Fonts.body(11), state="readonly", placeholder_text="Aucun personnel sélectionné",
        )
        self.selected_personnel_entry.grid(row=0, column=1, sticky="ew")

        ctk.CTkLabel(right, text="Date", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(
            row=3, column=0, padx=12, pady=(0, 2), sticky="w"
        )
        self.hours_date = DateEntry(right, **de_kw)
        self.hours_date.set_date(date.today())
        self.hours_date.grid(row=4, column=0, padx=12, pady=(0, 10), sticky="w")

        ctk.CTkLabel(right, text="Nombre d'heures", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(
            row=5, column=0, padx=12, pady=(0, 2), sticky="w"
        )
        self.hours_var = ctk.StringVar(value="")
        self.hours_entry = ctk.CTkEntry(
            right, textvariable=self.hours_var, height=36, fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            corner_radius=8, font=Fonts.body(12), placeholder_text="Ex: 2.5",
        )
        self.hours_entry.grid(row=6, column=0, padx=12, pady=(0, 10), sticky="ew")

        actions = ctk.CTkFrame(right, fg_color="transparent")
        actions.grid(row=7, column=0, padx=12, pady=(0, 12), sticky="ew")
        styled.button_success(actions, text="Ajouter", icon="➕", width=130, height=34, command=self.add_hours).pack(side="left")
        styled.button_secondary(actions, text="Vider", icon="↺", width=120, height=34, command=self.clear_hours_form).pack(side="left", padx=(10, 0))

        ctk.CTkLabel(right, text="Historique heures", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(
            row=8, column=0, padx=12, pady=(0, 2), sticky="w"
        )
        hist_card = ctk.CTkFrame(right, fg_color=Colors.BG_CARD, corner_radius=10, border_width=1, border_color=Colors.BORDER)
        hist_card.grid(row=9, column=0, padx=12, pady=(0, 12), sticky="nsew")
        hist_card.grid_columnconfigure(0, weight=1)
        hist_card.grid_rowconfigure(0, weight=1)
        self.hist_tree = ttk.Treeview(hist_card, columns=("date", "heures"), show="headings", style="P.Treeview", height=6)
        self.hist_tree.heading("date", text="Date")
        self.hist_tree.heading("heures", text="Heures")
        self.hist_tree.column("date", width=150, anchor="w")
        self.hist_tree.column("heures", width=90, anchor="e")
        self.hist_tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        hsvb = ttk.Scrollbar(hist_card, orient="vertical", command=self.hist_tree.yview)
        self.hist_tree.configure(yscrollcommand=hsvb.set)
        hsvb.grid(row=0, column=1, sticky="ns", pady=6)
        self._configure_table_alternating_colors(self.hist_tree)

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        footer.grid_columnconfigure(0, weight=1)
        self.label_count = ctk.CTkLabel(footer, text="Professeurs affichés : 0", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY)
        self.label_count.pack(side="left", padx=(4, 0))

    def _setup_treeview_style(self):
        # [UI] Style P.Treeview (supprime l’appel inexistant à _apply_appearance_mode)
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

    def _configure_table_alternating_colors(self, tree):
        tree.tag_configure("row_even", background=Colors.BG_CARD)
        tree.tag_configure("row_odd", background=Colors.BG_ROW_ALT)

    def _refresh_table_alternating_colors(self, tree):
        for idx, item in enumerate(tree.get_children()):
            existing_tags = tuple(t for t in tree.item(item, "tags") if t not in ("row_even", "row_odd"))
            alt_tag = "row_even" if idx % 2 == 0 else "row_odd"
            tree.item(item, tags=(alt_tag,) + existing_tags)

    # ──────────────────────────────────────────────────────────────────────
    # [UI] Périodes rapides
    # ──────────────────────────────────────────────────────────────────────

    def set_period_preset(self, preset: str):
        today = date.today()
        if preset == "day":
            start = end = today
        elif preset == "week":
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
        elif preset == "month":
            start = today.replace(day=1)
            # dernier jour du mois
            next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
            end = next_month - timedelta(days=1)
        else:
            return
        try:
            self.entry_start.set_date(start)
            self.entry_end.set_date(end)
        except Exception:
            pass
        self.load_data()

    # ──────────────────────────────────────────────────────────────────────
    # [UI] Sélecteur personnel
    # ──────────────────────────────────────────────────────────────────────

    def _fmt_personnel(self, nom, prenom):
        nom_s = (nom or "").strip() if nom is not None else ""
        prenom_s = (prenom or "").strip() if prenom is not None else ""
        nom_s = nom_s if nom_s else "-"
        prenom_s = prenom_s if prenom_s else "-"
        return f"{nom_s} {prenom_s}".strip()

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
                self.selected_personnel_id = int(_id)
            except Exception:
                self.selected_personnel_id = None
            self.selected_personnel_var.set(self._fmt_personnel(nom, prenom))
            self.clear_hours_form(keep_personnel=True)
            self.load_hours_history()
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
    # [LOGIQUE] Saisie heures + historique
    # ──────────────────────────────────────────────────────────────────────

    def clear_hours_form(self, keep_personnel: bool = False):
        if not keep_personnel:
            self.selected_personnel_id = None
            self.selected_personnel_var.set("")
        try:
            self.hours_date.set_date(date.today())
        except Exception:
            pass
        self.hours_var.set("")
        if hasattr(self, "hist_tree"):
            for item in self.hist_tree.get_children():
                self.hist_tree.delete(item)

    def add_hours(self):
        if not self.conn or not self.cursor:
            messagebox.showerror("Erreur", "Connexion à la base de données non établie.")
            return
        if not self.selected_personnel_id:
            messagebox.showerror("Erreur", "Veuillez sélectionner un personnel.")
            return
        heures_in = (self.hours_var.get() or "").strip().replace(" ", "").replace(",", ".")
        if not heures_in:
            messagebox.showerror("Erreur", "Veuillez saisir le nombre d'heures.")
            return
        try:
            nb = float(heures_in)
            if nb <= 0:
                messagebox.showerror("Erreur", "Le nombre d'heures doit être supérieur à zéro.")
                return
        except ValueError:
            messagebox.showerror("Erreur", "Veuillez saisir un nombre valide (ex: 2.5).")
            return
        d = self.hours_date.get_date()
        dt = datetime.combine(d, time(12, 0, 0))
        try:
            self.cursor.execute(
                "INSERT INTO tb_presencepers (idpers, nbheure, date) VALUES (%s, %s, %s)",
                (int(self.selected_personnel_id), nb, dt),
            )
            self.conn.commit()
            try:
                self._logger.log(
                    action="Création présence (heures)",
                    element=f"idpers={self.selected_personnel_id}",
                    details=f"Heures enregistrées (nbheure={nb}, date={dt.date()})",
                    value=str(nb),
                )
            except Exception:
                pass
            messagebox.showinfo("Succès", "Heures enregistrées.")
            self.hours_var.set("")
            self.load_hours_history()
            self.load_data()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Erreur SQL", f"Erreur lors de l'enregistrement : {e}")

    def load_hours_history(self, limit: int = 20):
        if not self.cursor or not self.selected_personnel_id:
            return
        for item in self.hist_tree.get_children():
            self.hist_tree.delete(item)
        try:
            self.cursor.execute(
                "SELECT date, nbheure FROM tb_presencepers WHERE idpers=%s ORDER BY date DESC LIMIT %s",
                (int(self.selected_personnel_id), int(limit)),
            )
            rows = self.cursor.fetchall()
            for d, h in rows:
                d_str = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)
                try:
                    h_val = float(h) if h is not None else 0.0
                    h_str = f"{h_val:,.2f}".replace(",", " ").replace(".", ",")
                except Exception:
                    h_str = str(h)
                self.hist_tree.insert("", "end", values=(d_str, h_str))
            self._refresh_table_alternating_colors(self.hist_tree)
        except Exception:
            return

    def load_data(self):
        """Loads and displays data in the Treeview based on filters."""
        for row in self.tree.get_children():
            self.tree.delete(row)
        self._refresh_table_alternating_colors(self.tree)

        self.current_export_data = [] # Clear data for export

        total_heures = 0.0
        total_montants = 0.0
        count_professeurs = 0

        search_term = self.search_var.get().strip()
        start_d = self.entry_start.get_date()
        end_d = self.entry_end.get_date()
        start_dt = datetime.combine(start_d, time(0, 0, 0))
        end_dt = datetime.combine(end_d, time(23, 59, 59))

        
        query = '''
            SELECT p.id, p.nom, p.prenom,
                   (
                       SELECT tauxhoraire FROM tb_tauxhoraire t
                       WHERE t.idpers = p.id
                       ORDER BY dateregistre DESC
                       LIMIT 1
                   ) AS tauxhoraire,
                   COALESCE(SUM(pr.nbheure), 0) AS totalheure,
                   COALESCE(SUM(pr.nbheure), 0) * (
                       SELECT tauxhoraire FROM tb_tauxhoraire t
                       WHERE t.idpers = p.id
                       ORDER BY dateregistre DESC
                       LIMIT 1
                   ) AS montant
            FROM tb_personnel p
            LEFT JOIN tb_presencepers pr ON pr.idpers = p.id
                 AND pr.date BETWEEN %s AND %s
            WHERE (
                SELECT tauxhoraire FROM tb_tauxhoraire t
                WHERE t.idpers = p.id
                ORDER BY dateregistre DESC
                LIMIT 1
            ) IS NOT NULL
            AND CONCAT(p.nom, ' ', p.prenom) ILIKE %s
            GROUP BY p.id, p.nom, p.prenom
            ORDER BY p.nom, p.prenom
        '''

        try:
            self.cursor.execute(query, (start_dt, end_dt, f"%{search_term}%"))
            rows = self.cursor.fetchall()
        except Exception as e:
            messagebox.showerror("Erreur SQL", f"Erreur lors de l'exécution de la requête principale: {e}")
            return

        for row in rows:
            idpers, nom, prenom, taux, heures, montant = row
            if heures == 0:
                continue

            try:
                self.cursor.execute("SELECT COALESCE(SUM(mtpaye), 0) FROM tb_avancepers WHERE idpers = %s AND datepmt BETWEEN %s AND %s",
                                   (idpers, start_dt, end_dt))
                avance15 = self.cursor.fetchone()[0]
            except Exception as e:
                messagebox.showerror("Erreur Avance 15e", f"Erreur lors de la récupération de l'avance 15e pour {nom} {prenom}: {e}")
                avance15 = 0

            try:
                self.cursor.execute("""
                    SELECT COALESCE(SUM(mtpaye / NULLIF(nbremboursement, 0)), 0)
                    FROM tb_avancespecpers
                    WHERE idpers = %s AND datepmt BETWEEN %s AND %s
                """, (idpers, start_dt, end_dt))
                deduction = self.cursor.fetchone()[0]
            except Exception as e:
                messagebox.showerror("Erreur Déduction Spéciale", f"Erreur lors de la récupération de la déduction spéciale pour {nom} {prenom}: {e}")
                deduction = 0

            net = (montant if montant is not None else 0) - (avance15 if avance15 is not None else 0) - (deduction if deduction is not None else 0)

            # Store raw data for export
            self.current_export_data.append(
                (nom, prenom, taux, heures, montant, avance15, deduction, net)
            )

            # Format numbers for display (French format)
            taux_fmt = f"{taux:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".") if taux is not None else "0"
            heures_fmt = f"{heures:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".") if heures is not None else "0"
            montant_fmt = f"{montant:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".") if montant is not None else "0"
            avance_fmt = f"{avance15:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".") if avance15 is not None else "0"
            deduction_fmt = f"{deduction:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".") if deduction is not None else "0"
            net_fmt = f"{net:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".") if net is not None else "0"

            self.tree.insert('', 'end', values=(nom, prenom, taux_fmt, heures_fmt, montant_fmt, avance_fmt, deduction_fmt, net_fmt))

            total_heures += float(heures) if heures is not None else 0
            total_montants += float(net) if net is not None else 0
            count_professeurs += 1

        total_heure_fmt = f"{total_heures:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
        total_montant_fmt = f"{total_montants:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
        self.tree.insert('', 'end', values=('', 'TOTAL', '', total_heure_fmt, '', '', '', total_montant_fmt), tags=('total',))
        # [UI] Ligne total : fond du thème (INFO_LIGHT)
        self.tree.tag_configure("total", background=Colors.PRIMARY_LIGHT, font=("Segoe UI", 10, "bold"))
        self._refresh_table_alternating_colors(self.tree)

        self.label_count.configure(text=f"Professeurs affichés : {count_professeurs}")

    def get_company_info(self):
        """Récupère les informations de la société depuis la base de données."""
        try:
            self.cursor.execute("SELECT nomsociete, adressesociete, contactsociete FROM tb_infosociete LIMIT 1")
            info = self.cursor.fetchone()
            if info:
                return {"nom": info[0], "adresse": info[1], "contact": info[2]}
            return {"nom": "Ma Société", "adresse": "", "contact": ""}
        except Exception:
            return {"nom": "Ma Société", "adresse": "", "contact": ""}

    def export_excel(self):
        if not self.current_export_data:
            messagebox.showinfo("Info", "Aucune donnée à exporter.")
            return

        company = self.get_company_info()
        start_date = self.entry_start.get_date().strftime("%d/%m/%Y")
        end_date = self.entry_end.get_date().strftime("%d/%m/%Y")
        
        # Préparation du DataFrame
        df = pd.DataFrame(self.current_export_data, columns=self.columns)
        file_path = os.path.join(os.path.expanduser("~"), "Desktop", "etat_salaire_horaire.xlsx")
        
        try:
            writer = pd.ExcelWriter(file_path, engine='xlsxwriter')
            # On écrit les données à partir de la ligne 6 pour laisser de la place à l'en-tête
            df.to_excel(writer, index=False, sheet_name='Salaire', startrow=5)
            
            workbook = writer.book
            worksheet = writer.sheets['Salaire']
            
            # Formats
            header_format = workbook.add_format({'bold': True, 'font_size': 14})
            info_format = workbook.add_format({'font_size': 10})

            # Insertion des informations de la société
            worksheet.write('A1', company['nom'], header_format)
            worksheet.write('A2', f"Adresse: {company['adresse']}", info_format)
            worksheet.write('A3', f"Contact: {company['contact']}", info_format)
            worksheet.write('A4', f"Salaire pour la période: du {start_date} au {end_date}", workbook.add_format({'bold': True}))

            writer.close()
            messagebox.showinfo("Exportation Excel", f"Données exportées vers:\n{file_path}")
            os.startfile(file_path) if os.name == 'nt' else subprocess.Popen(['open', file_path])
        except Exception as e:
            messagebox.showerror("Erreur Excel", f"Erreur: {e}")

    def export_pdf(self):
        if not self.current_export_data:
            messagebox.showinfo("Info", "Aucune donnée à exporter. Veuillez d'abord afficher les données.")
            return

        company = self.get_company_info()
        start_date = self.entry_start.get_date().strftime("%d/%m/%Y")
        end_date = self.entry_end.get_date().strftime("%d/%m/%Y")
        file_path = os.path.join(os.path.expanduser("~"), "Desktop", "etat_salaire_horaire.pdf")

        try:
            pdf = canvas.Canvas(file_path, pagesize=landscape(letter))
        
            def add_header(pdf_canvas, page_num):
                # 1. Infos Société (Haut Gauche)
                pdf_canvas.setFont("Helvetica-Bold", 12)
                pdf_canvas.drawString(40, 575, company['nom'].upper())
                pdf_canvas.setFont("Helvetica", 9)
                pdf_canvas.drawString(40, 560, f"Adresse : {company['adresse']}")
                pdf_canvas.drawString(40, 545, f"Contact : {company['contact']}")
            
                # 2. Titre Central
                pdf_canvas.setFont("Helvetica-Bold", 16)
                pdf_canvas.drawCentredString(411, 520, "ETAT DE SALAIRE HORAIRE")
                pdf_canvas.setFont("Helvetica-BoldOblique", 11)
                pdf_canvas.drawCentredString(411, 505, f"Période du : {start_date} au {end_date}")
            
                # 3. Métadonnées (Haut Droite)
                current_date = datetime.now().strftime("%d/%m/%Y %H:%M")
                pdf_canvas.setFont("Helvetica", 9)
                pdf_canvas.drawString(650, 575, f"Imprimé le : {current_date}")
                pdf_canvas.drawString(700, 20, f"Page {page_num}")

            page_number = 1
            add_header(pdf, page_number)

            # Positions des colonnes
            x_positions = [40, 140, 240, 340, 440, 530, 620, 710]
            y = 470 # Position de départ sous l'en-tête
            line_height = 20

            # Dessiner les en-têtes du tableau
            pdf.setFont("Helvetica-Bold", 10)
            pdf.line(40, y + 15, 780, y + 15) # Ligne au dessus
            for i, header in enumerate(self.columns):
                pdf.drawString(x_positions[i], y, header)
            pdf.line(40, y - 5, 780, y - 5) # Ligne en dessous
            y -= line_height

            pdf.setFont("Helvetica", 9)
        
            total_heures_sum = 0.0
            total_net_sum = 0.0

            for row_data in self.current_export_data:
                # Gestion du saut de page
                if y < 60:
                    pdf.showPage()
                    page_number += 1
                    add_header(pdf, page_number)
                    y = 470
                    # Répéter les en-têtes sur la nouvelle page
                    pdf.setFont("Helvetica-Bold", 10)
                    for i, header in enumerate(self.columns):
                        pdf.drawString(x_positions[i], y, header)
                    y -= line_height
                    pdf.setFont("Helvetica", 9)

                # Dessiner les données
                for i, value in enumerate(row_data):
                    if isinstance(value, (float, int)):
                        display_val = f"{value:,.0f}".replace(",", " ").replace(".", ",")
                    else:
                        display_val = str(value)
                    pdf.drawString(x_positions[i], y, display_val)

                total_heures_sum += row_data[3] if row_data[3] else 0
                total_net_sum += row_data[7] if row_data[7] else 0
                y -= line_height

            # Ligne de total final
            pdf.line(40, y + 10, 780, y + 10)
            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(x_positions[0], y-5, "TOTAL GÉNÉRAL :")
            pdf.drawString(x_positions[3], y-5, f"{total_heures_sum:,.0f}".replace(",", " "))
            pdf.drawString(x_positions[7], y-5, f"{total_net_sum:,.0f}".replace(",", " "))

            pdf.save()
            messagebox.showinfo("Succès", f"PDF généré : {file_path}")
            os.startfile(file_path) if os.name == 'nt' else subprocess.Popen(['open', file_path])

        except Exception as e:
            messagebox.showerror("Erreur PDF", f"Détails : {e}")

# --- Main Application setup (remains similar) ---
if __name__ == "__main__":
    app = ctk.CTk()
    app.title("État de salaire par heure")
    app.geometry("1200x700")
    app.grid_rowconfigure(0, weight=1)
    app.grid_columnconfigure(0, weight=1)

    page_etat_salaire_horaire = PageEtatSalaireHoraire(app)
    page_etat_salaire_horaire.grid(row=0, column=0, sticky="nsew")

    app.mainloop()

    # Close DB connection
    if cursor:
        cursor.close()
    if conn:
        conn.close()
