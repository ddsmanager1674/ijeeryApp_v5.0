import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import psycopg2
from datetime import datetime
import json
import os
import sys
from resource_utils import get_config_path, safe_file_read


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
        super().__init__(parent)
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

       # Interface Elements
        ctk.CTkLabel(self, text="Désignation Fonction:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.entry_designation = ctk.CTkEntry(self)
        self.entry_designation.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.entry_designation.configure(justify="left")


        ctk.CTkLabel(self, text="ID Autorisation:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.entry_idautorisation = ctk.CTkEntry(self) # Removed fixed width here
        self.entry_idautorisation.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        # Buttons
        self.save_button = ctk.CTkButton(self, text="Enregistrer", fg_color="#2ecc71", 
        hover_color="#27ae60",command=self.enregistrer)
        self.save_button.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        self.modify_button = ctk.CTkButton(self, text="Modifier", fg_color="#3498db",
        hover_color="#2980b9",command=self.modifier)
        self.modify_button.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        self.delete_button = ctk.CTkButton(self, text="Supprimer", fg_color="#e74c3c",
        hover_color="#c0392b",command=self.supprimer)
        self.delete_button.grid(row=2, column=2, padx=10, pady=10, sticky="ew")

        self.clear_button = ctk.CTkButton(self, text="Vider", command=self.vider)
        self.clear_button.grid(row=2, column=3, padx=10, pady=10, sticky="ew")

        # Treeview
        columns = ("id", "designationfonction", "date", "idautorisation")
        self.tree = ctk.CTkScrollableFrame(self)
        self.tree.grid(row=3, column=0, columnspan=4, padx=10, pady=10, sticky="nsew")

        self.treeview = tk.ttk.Treeview(self.tree, columns=columns, show='headings')
        self.treeview.pack(expand=True, fill="both")
        self._configure_table_alternating_colors(self.treeview)

        for col in columns:
            self.treeview.heading(col, text=col.capitalize())
            self.treeview.column(col, width=150, anchor="w")

        self.treeview.bind("<<TreeviewSelect>>", self.remplir_champs)

        # Initial load
        self.charger_fonctions()

    def _configure_table_alternating_colors(self, tree):
        """Configure des couleurs alternées: blanc + vert clair basé sur #036C6B."""
        tree.tag_configure("row_even", background="#FFFFFF")
        tree.tag_configure("row_odd", background="#D9EEED")

    def _refresh_table_alternating_colors(self, tree):
        """Réapplique les couleurs alternées sur les lignes du tableau."""
        for idx, item in enumerate(tree.get_children()):
            tree.item(item, tags=("row_even" if idx % 2 == 0 else "row_odd",))

    def charger_fonctions(self):
        if not self.conn:
            return
        for i in self.treeview.get_children():
            self.treeview.delete(i)
        self._refresh_table_alternating_colors(self.treeview)
        self.cursor.execute("SELECT * FROM tb_fonction")
        for row in self.cursor.fetchall():
            self.treeview.insert('', 'end', values=row)
        self._refresh_table_alternating_colors(self.treeview)

    def enregistrer(self):
        if not self.conn:
            messagebox.showerror("Erreur", "Connexion à la base de données non établie.")
            return
        try:
            designation = self.entry_designation.get()
            idauto = self.entry_idautorisation.get()
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
            idauto = self.entry_idautorisation.get()
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
            self.entry_idautorisation.delete(0, tk.END)
            self.entry_idautorisation.insert(0, values[2])

    def vider(self):
        self.entry_designation.delete(0, tk.END)
        self.entry_idautorisation.delete(0, tk.END)

if __name__ == "__main__":
    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("Gestion des Fonctions (CustomTkinter)")
    app.geometry("800x600")

    fonction_page = PageFonction(app)
    fonction_page.pack(fill="both", expand=True, padx=10, pady=10)

    app.mainloop()
