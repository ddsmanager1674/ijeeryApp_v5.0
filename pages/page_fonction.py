import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import psycopg2
from datetime import datetime
import json
import os
import sys
from resource_utils import get_config_path, safe_file_read

# Thème UI iJeery
from app_theme import Colors, Fonts, Theme, styled, Layout


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
            # Assurez-vous que le chemin vers config.json est correct
            config_path = get_config_path('config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config['database']
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
                port=self.db_params['port']
            )
            self.cursor = self.conn.cursor()
            print("Connection to the database successful!")
            return True
        except psycopg2.OperationalError as e:
            print(f"Error connecting to the database: {e}")
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

class PageFonction(ctk.CTkFrame):
    def __init__(self, parent):
        # [UI] Harmonisation de la page Fonction avec app_theme (header/cards/boutons/table)
        # [LOGIQUE] Aucune modification des opérations SQL métier ; uniquement UI et lisibilité
        super().__init__(parent, fg_color=Colors.BG_PAGE)
        self.grid_columnconfigure(0, weight=1) # Column for labels
        self.grid_columnconfigure(1, weight=3) # Give more weight to the column for entries
        self.grid_columnconfigure(2, weight=1)
        self.grid_columnconfigure(3, weight=1)
        self.grid_rowconfigure(3, weight=1) # Make row 3 (where treeview is) expandable

        # Instantiate DatabaseManager and establish a connection
        db_manager = DatabaseManager()
        self.conn = db_manager.get_connection()

        if self.conn is None:
            messagebox.showerror("Erreur de connexion", "Impossible de se connecter à la base de données.")
            return

        try:
            self.cursor = self.conn.cursor()
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tb_fonction (
                    id SERIAL PRIMARY KEY,
                    designationfonction VARCHAR(100),
                    idautorisation INT,
                    dateregistre TIMESTAMP
                )
                """
            )
            self.conn.commit()
        except psycopg2.Error as err:
            messagebox.showerror("Erreur de connexion", f"Erreur : {err}")
            self.conn = None
            self.cursor = None

        self._setup_treeview_style()

        # Header
        header = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT, corner_radius=0, height=46)
        header.grid(row=0, column=0, columnspan=4, sticky="ew")
        header.grid_propagate(False)

        left = styled.frame(header)
        left.pack(side="left", padx=14)
        ctk.CTkLabel(left, text="👔", font=Fonts.heading(16), text_color=Colors.TEXT_ON_DARK).pack(side="left", padx=(0, 8))
        inner = styled.frame(left)
        inner.pack(side="left")
        ctk.CTkLabel(inner, text="Fonction", font=Fonts.bold(13), text_color=Colors.TEXT_ON_DARK).pack(anchor="w")
        ctk.CTkLabel(inner, text="Gestion des fonctions et autorisations", font=Fonts.small(9), text_color=Colors.TEXT_ON_DARK_DIM).pack(anchor="w")

        # Card formulaire
        form = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        form.grid(row=1, column=0, columnspan=4, padx=10, pady=(10, 6), sticky="ew")
        form.grid_columnconfigure(1, weight=1)
        # [UI] Formulaire inline : uniquement désignation (idautorisation fixé par défaut)

        ctk.CTkLabel(form, text="Désignation :", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(row=0, column=0, padx=(12, 6), pady=10, sticky="w")
        self.entry_designation = ctk.CTkEntry(form, height=32, fg_color=Colors.BG_INPUT, border_color=Colors.BORDER, corner_radius=8, font=Fonts.body(11))
        self.entry_designation.grid(row=0, column=1, padx=(0, 12), pady=10, sticky="ew")

        # Card actions
        actions = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        actions.grid(row=2, column=0, columnspan=4, padx=10, pady=(0, 6), sticky="ew")

        styled.button_success(actions, text="Enregistrer", icon="💾", width=150, height=32, command=self.enregistrer).pack(side="left", padx=10, pady=10)
        styled.button_primary(actions, text="Modifier", icon="✏️", width=130, height=32, command=self.modifier).pack(side="left", padx=0, pady=10)
        styled.button_danger(actions, text="Supprimer", icon="🗑", width=135, height=32, command=self.supprimer).pack(side="left", padx=10, pady=10)
        styled.button_secondary(actions, text="Vider", icon="↺", width=110, height=32, command=self.vider).pack(side="right", padx=10, pady=10)

        # Card tableau
        table_card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        table_card.grid(row=3, column=0, columnspan=4, padx=10, pady=(0, 10), sticky="nsew")
        table_card.grid_columnconfigure(0, weight=1)
        table_card.grid_rowconfigure(0, weight=1)

        # [UI] Tableau : afficher uniquement la désignation (id conservé caché pour CRUD)
        columns = ("id", "designationfonction")
        self.treeview = tk.ttk.Treeview(table_card, columns=columns, show='headings', style="P.Treeview", selectmode="browse")
        self.treeview.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        vsb = tk.ttk.Scrollbar(table_card, orient="vertical", command=self.treeview.yview)
        self.treeview.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns", pady=6)

        self._configure_table_alternating_colors(self.treeview)
        self.treeview.heading("designationfonction", text="Désignation")
        self.treeview.column("designationfonction", width=320, anchor="w")
        self.treeview.heading("id", text="ID")
        self.treeview.column("id", width=0, stretch=tk.NO)
        self.treeview.bind("<<TreeviewSelect>>", self.remplir_champs)

        # Footer count
        self.label_count = ctk.CTkLabel(self, text="Nombre de fonctions enregistrées = 0", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY)
        self.label_count.grid(row=4, column=0, columnspan=4, sticky="w", padx=14, pady=(0, 10))

        # Initial load
        self.charger_fonctions()

    def _configure_table_alternating_colors(self, tree):
        """Couleurs alternées (thème iJeery)."""
        # [UI] Palette alignée au thème iJeery
        tree.tag_configure("row_even", background=Colors.BG_CARD)
        tree.tag_configure("row_odd", background=Colors.BG_ROW_ALT)

    def _refresh_table_alternating_colors(self, tree):
        """Réapplique les couleurs alternées sur les lignes du tableau."""
        for idx, item in enumerate(tree.get_children()):
            tree.item(item, tags=("row_even" if idx % 2 == 0 else "row_odd",))

    def _setup_treeview_style(self):
        # [UI] Style Treeview cohérent (heading Midnight + sélection Primary)
        s = tk.ttk.Style()
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

    def charger_fonctions(self):
        if not self.conn:
            return
        for i in self.treeview.get_children():
            self.treeview.delete(i)
        self._refresh_table_alternating_colors(self.treeview)
        # [LOGIQUE] Schéma réel : idfonction + colonne deleted
        self.cursor.execute(
            "SELECT idfonction, designationfonction "
            "FROM tb_fonction "
            "WHERE COALESCE(deleted, 0)=0 "
            "ORDER BY designationfonction"
        )
        rows = self.cursor.fetchall()
        for row in rows:
            self.treeview.insert('', 'end', values=row)
        self._refresh_table_alternating_colors(self.treeview)
        if hasattr(self, "label_count"):
            self.label_count.configure(text=f"Nombre de fonctions enregistrées = {len(rows)}")

    def enregistrer(self):
        if not self.conn:
            messagebox.showerror("Erreur", "Connexion à la base de données non établie.")
            return
        try:
            designation = self.entry_designation.get()
            # [LOGIQUE] idautorisation fixé par défaut
            idauto = 1
            date = datetime.now()
            self.cursor.execute("INSERT INTO tb_fonction (designationfonction, idautorisation, dateregistre) VALUES (%s, %s, %s)", (designation, idauto, date))
            self.conn.commit()
            self.charger_fonctions()
            self.vider()
            messagebox.showinfo("Succès", "Fonction enregistrée.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement : {e}")

    def modifier(self):
        if not self.conn:
            messagebox.showerror("Erreur", "Connexion à la base de données non établie.")
            return
        selected = self.treeview.selection()
        if not selected:
            messagebox.showwarning("Attention", "Sélectionnez une ligne à modifier.")
            return
        try:
            id_ = self.treeview.item(selected[0])['values'][0]
            designation = self.entry_designation.get()
            # [LOGIQUE] idautorisation fixé par défaut
            idauto = 1
            date = datetime.now()
            self.cursor.execute("UPDATE tb_fonction SET designationfonction=%s, idautorisation=%s, dateregistre=%s WHERE idfonction=%s",
                               (designation, idauto, date, id_))
            self.conn.commit()
            self.charger_fonctions()
            self.vider()
            messagebox.showinfo("Succès", "Fonction modifiée.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la modification : {e}")


    def supprimer(self):
        if not self.conn:
            messagebox.showerror("Erreur", "Connexion à la base de données non établie.")
            return
        selected = self.treeview.selection()
        if not selected:
            messagebox.showwarning("Attention", "Sélectionnez une ligne à supprimer.")
            return
        try:
            id_ = self.treeview.item(selected[0])['values'][0]
            # [LOGIQUE] Soft delete si la colonne existe (évite suppression physique)
            try:
                self.cursor.execute("UPDATE tb_fonction SET deleted=1 WHERE idfonction=%s", (id_,))
            except Exception:
                self.cursor.execute("DELETE FROM tb_fonction WHERE idfonction=%s", (id_,))
            self.conn.commit()
            self.charger_fonctions()
            self.vider()
            messagebox.showinfo("Succès", "Fonction supprimée.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la suppression : {e}")

    def remplir_champs(self, event):
        selected = self.treeview.selection()
        if selected:
            values = self.treeview.item(selected[0])['values']
            self.entry_designation.delete(0, tk.END)
            self.entry_designation.insert(0, values[1])

    def vider(self):
        self.entry_designation.delete(0, tk.END)

if __name__ == "__main__":
    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("Gestion des Fonctions (CustomTkinter)")
    app.geometry("800x600")

    fonction_page = PageFonction(app)
    fonction_page.pack(fill="both", expand=True, padx=10, pady=10)

    app.mainloop()
