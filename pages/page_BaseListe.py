import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk
import psycopg2
import json
import os
import sys
from resource_utils import get_config_path, safe_file_read


# Configuration du chemin pour les imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


class PageBaseListe(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        
        # Configuration de la grille
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_columnconfigure(2, weight=1)
        self.grid_columnconfigure(3, weight=1)
        self.grid_rowconfigure(3, weight=1)

       # Connexion à la base de données
        self.conn = self.connect_db()
        self.cursor = None
        
        if self.conn:
            self.cursor = self.conn.cursor()
            self.initialize_database()

        if self.conn is None:
            messagebox.showerror("Erreur", "Impossible de se connecter à la base de données.")
            return
        
        # CORRECTION PRINCIPALE : Appeler setup_ui() dans __init__
        self.setup_ui()
        
    def connect_db(self):
        """Établit la connexion à la base de données à partir du fichier config.json"""
        try:
            config_path = get_config_path('config.json')
            if not os.path.exists(config_path):
                config_path = 'config.json'
                
            if not os.path.exists(config_path):
                messagebox.showerror("Erreur", "Fichier config.json manquant.")
                return None
                 
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                db_config = config['database']

            conn = psycopg2.connect(
                host=db_config['host'],
                user=db_config['user'],
                password=db_config['password'],
                database=db_config['database'],
                port=db_config['port'],
                client_encoding='UTF8'
            )
            print("Connection to the database successful!")
            return conn
        except Exception as err:
            messagebox.showerror("Erreur de connexion", f"Détails : {err}")
            return None
    
    def initialize_database(self):
        """Initialise la connexion à la base de données et crée la table si nécessaire."""
        if not self.cursor:
            return False

        self.cursor = self.conn.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tb_baseliste (
                id SERIAL PRIMARY KEY,
                nombase VARCHAR(75),
                designationbase VARCHAR (75),
                deleted INT DEFAULT 0
            )
        """)
        self.conn.commit()

    def setup_ui(self):
        self.pack(expand=True, fill="both", padx=20, pady=20)

        # --- Éléments d'interface ---
        ctk.CTkLabel(self, text="Nom de la Base :").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.entry_nombase = ctk.CTkEntry(self)
        self.entry_nombase.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self, text="Désignation/Adresse :").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.entry_designationbase = ctk.CTkEntry(self)
        self.entry_designationbase.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        # Boutons
        self.save_button = ctk.CTkButton(self, text="Enregistrer", fg_color="#2ecc71", hover_color="#27ae60", command=self.enregistrer)
        self.save_button.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        self.modify_button = ctk.CTkButton(self, text="Modifier", fg_color="#3498db", hover_color="#2980b9", command=self.modifier)
        self.modify_button.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        self.delete_button = ctk.CTkButton(self, text="Supprimer", fg_color="#e74c3c", hover_color="#c0392b", command=self.supprimer)
        self.delete_button.grid(row=2, column=2, padx=10, pady=10, sticky="ew")

        self.clear_button = ctk.CTkButton(self, text="Vider", command=self.vider)
        self.clear_button.grid(row=2, column=3, padx=10, pady=10, sticky="ew")

        # --- Treeview ---
        # Note : On affiche ID, Nom et Désignation (Colonnes 0, 1, 2 de la table)
        columns = ("id", "nombase", "designation")
        self.tree_container = ctk.CTkFrame(self)
        self.tree_container.grid(row=3, column=0, columnspan=4, padx=10, pady=10, sticky="nsew")

        self.treeview = ttk.Treeview(self.tree_container, columns=columns, show='headings')
        self.treeview.tag_configure("row_even", background="#FFFFFF")
        self.treeview.tag_configure("row_odd", background="#F1E4D8")
        self.treeview.pack(expand=True, fill="both")

        self.treeview.heading("id", text="ID")
        self.treeview.heading("nombase", text="Base de donnée")
        self.treeview.heading("designation", text="Désignation / Adresse")

        self.treeview.column("id", width=50, anchor="center")
        self.treeview.column("nombase", width=200, anchor="w")
        self.treeview.column("designation", width=300, anchor="w")

        self.treeview.bind("<<TreeviewSelect>>", self.remplir_champs)

        self.charger_base()

    def _refresh_table_alternating_colors(self):
        for idx, item in enumerate(self.treeview.get_children()):
            self.treeview.item(item, tags=("row_even" if idx % 2 == 0 else "row_odd",))

    def charger_base(self):
        if not self.conn: return
        for i in self.treeview.get_children():
            self.treeview.delete(i)
        self._refresh_table_alternating_colors()
        
        # On ne sélectionne que les colonnes nécessaires pour l'affichage
        self.cursor.execute("SELECT id, nombase, designationbase FROM tb_baseliste WHERE deleted = 0 ORDER BY id DESC")
        for row in self.cursor.fetchall():
            self.treeview.insert('', 'end', values=row)
        self._refresh_table_alternating_colors()

    def enregistrer(self):
        if not self.conn: return
        try:
            nombase = self.entry_nombase.get()
            designation = self.entry_designationbase.get()
            if not nombase:
                messagebox.showwarning("Attention", "Le nom de la base est requis.")
                return

            self.cursor.execute("INSERT INTO tb_baseliste (nombase, designationbase) VALUES (%s, %s)", (nombase, designation))
            self.conn.commit()
            self.charger_base()
            self.vider()
            messagebox.showinfo("Succès", "Base enregistrée.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement : {e}")

    def modifier(self):
        selected = self.treeview.selection()
        if not selected:
            messagebox.showwarning("Attention", "Sélectionnez une ligne.")
            return
        try:
            id_ = self.treeview.item(selected[0])['values'][0]
            nombase = self.entry_nombase.get()
            designation = self.entry_designationbase.get()
            
            # Correction SQL : Pas de virgule avant WHERE
            self.cursor.execute("UPDATE tb_baseliste SET nombase=%s, designationbase=%s WHERE id=%s",
                               (nombase, designation, id_))
            self.conn.commit()
            self.charger_base()
            self.vider()
            messagebox.showinfo("Succès", "Base modifiée.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur modification : {e}")

    def supprimer(self):
        selected = self.treeview.selection()
        if not selected:
            messagebox.showwarning("Attention", "Sélectionnez une ligne.")
            return
        if messagebox.askyesno("Confirmation", "Voulez-vous vraiment supprimer cet élément ?"):
            try:
                id_ = self.treeview.item(selected[0])['values'][0]
                self.cursor.execute("DELETE FROM tb_baseliste WHERE id=%s", (id_,))
                self.conn.commit()
                self.charger_base()
                self.vider()
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur suppression : {e}")

    def remplir_champs(self, event):
        selected = self.treeview.selection()
        if selected:
            values = self.treeview.item(selected[0])['values']
            self.vider()
            self.entry_nombase.insert(0, values[1])
            self.entry_designationbase.insert(0, values[2])

    def vider(self):
        self.entry_nombase.delete(0, tk.END)
        self.entry_designationbase.delete(0, tk.END)

if __name__ == "__main__":
    ctk.set_appearance_mode("Light")
    app = ctk.CTk()
    app.title("Gestion des Bases")
    app.geometry("700x500")
    page = PageBaseListe(app)
    page.pack(fill="both", expand=True, padx=10, pady=10)
    app.mainloop()
