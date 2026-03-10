import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime
import winsound # Utilisé pour des sons, peut être retiré si non désiré
import json # Non utilisé dans cette section, peut être retiré si non désiré
import customtkinter as ctk
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

class PageEvenement(ctk.CTkFrame):
    def __init__(self, master, db_conn=None, session_data=None, db_config=None, **kwargs):
        super().__init__(master, **kwargs)

        self.conn = None
        self.cursor = None
        self.connect_to_db()

        self.create_widgets()
        self.load_events()

    def connect_to_db(self):
        """Tente d'établir une connexion à la base de données PostgreSQL."""
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
                CREATE TABLE IF NOT EXISTS tb_evenement (
                    id SERIAL PRIMARY KEY,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Ajout de DEFAULT pour une date automatique
                    evenements VARCHAR(200) NOT NULL
                )
                """
            )
            self.conn.commit()
        except psycopg2.Error as err:
            messagebox.showerror("Erreur de connexion à la base de données", f"Erreur : {err}")
            # Gérer l'échec de la connexion, par exemple désactiver certaines fonctionnalités
            self.conn = None
            self.cursor = None

    def create_widgets(self):
        """Crée les widgets de la page des événements."""

        # --- Champ de saisie pour l'événement ---
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(pady=20, padx=20, fill="x")

        self.event_label = ctk.CTkLabel(input_frame, text="Description de l'événement:", font=("Arial", 16))
        self.event_label.pack(side="left", padx=(0, 10))

        self.event_entry = ctk.CTkEntry(input_frame, width=400, font=("Arial", 14))
        self.event_entry.pack(side="left", fill="x", expand=True)

        # --- Boutons d'action ---
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=10, padx=20)

        self.add_button = ctk.CTkButton(button_frame, text="Ajouter", command=self.add_event, font=("Arial", 14, "bold"), fg_color="#28a745", hover_color="#218838")
        self.add_button.grid(row=0, column=0, padx=10)

        self.modify_button = ctk.CTkButton(button_frame, text="Modifier", command=self.modify_event, font=("Arial", 14, "bold"), fg_color="#007bff", hover_color="#0069d9")
        self.modify_button.grid(row=0, column=1, padx=10)

        self.delete_button = ctk.CTkButton(button_frame, text="Supprimer", command=self.delete_event, font=("Arial", 14, "bold"), fg_color="#dc3545", hover_color="#c82333")
        self.delete_button.grid(row=0, column=2, padx=10)

        # --- Treeview pour afficher les événements ---
        tree_frame = ctk.CTkFrame(self, fg_color="transparent")
        tree_frame.pack(pady=20, padx=20, fill="both", expand=True)

        # Style pour le Treeview (CustomTkinter ne stylise pas directement ttk.Treeview)
        # Vous devrez utiliser un style Tkinter normal pour personnaliser l'apparence
        style = ttk.Style()
        style.theme_use("clam") # 'clam', 'alt', 'default'

        # Configurez les couleurs de la Treeview
        # Ces couleurs peuvent ne pas être parfaites avec votre thème CustomTkinter,
        # vous devrez peut-être les ajuster pour correspondre.
        style.configure("Treeview",
                        background="#FFFFFF",
                        foreground="#000000",
                        rowheight=22,
                        fieldbackground="#FFFFFF",
                        borderwidth=0,
                        font=('Segoe UI', 8))
        style.map('Treeview',
                  background=[('selected', '#347083')])

        style.configure("Treeview.Heading",
                        font=('Segoe UI', 8, 'bold'),
                        background="#E8E8E8",
                        foreground="#000000")

        # Création du Treeview
        self.tree = ttk.Treeview(tree_frame, columns=("ID", "Date", "Description"), show="headings")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Date", text="Date")
        self.tree.heading("Description", text="Description de l'événement")

        # Ajuster les largeurs des colonnes
        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Date", width=150, anchor="center")
        self.tree.column("Description", width=450, anchor="w") # 'w' pour aligner à gauche

        self.tree.pack(side="left", fill="both", expand=True)

        # --- Scrollbar verticale ---
        self.scrollbar = ctk.CTkScrollbar(tree_frame, command=self.tree.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        # Événement de sélection dans le Treeview
        self.tree.bind("<ButtonRelease-1>", self.select_event)

    def load_events(self):
        """Charge tous les événements depuis la base de données et les affiche dans le Treeview."""
        if not self.conn:
            return # Ne rien faire si la connexion échoue

        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            self.cursor.execute("SELECT id, date, evenements FROM tb_evenement ORDER BY date DESC")
            events = self.cursor.fetchall()
            for event in events:
                # Formater la date pour un affichage plus lisible
                formatted_date = event[1].strftime('%Y-%m-%d %H:%M') if event[1] else ''
                self.tree.insert("", "end", values=(event[0], formatted_date, event[2]))
        except psycopg2.Error as e:
            messagebox.showerror("Erreur de chargement", f"Erreur lors du chargement des événements : {e}")

    def add_event(self):
        """Ajoute un nouvel événement à la base de données."""
        if not self.conn:
            return

        event_description = self.event_entry.get().strip()
        if not event_description:
            messagebox.showwarning("Saisie manquante", "Veuillez entrer une description pour l'événement.")
            return

        try:
            # La date est définie automatiquement par DEFAULT CURRENT_TIMESTAMP dans la table
            self.cursor.execute("INSERT INTO tb_evenement (evenements) VALUES (%s)", (event_description,))
            self.conn.commit()
            winsound.Beep(500, 200) # Petit son de succès
            messagebox.showinfo("Succès", "Événement ajouté avec succès !")
            self.event_entry.delete(0, ctk.END) # Efface le champ de saisie
            self.load_events() # Recharge les événements dans le Treeview
        except psycopg2.Error as e:
            messagebox.showerror("Erreur d'ajout", f"Erreur lors de l'ajout de l'événement : {e}")
            self.conn.rollback() # Annule la transaction en cas d'erreur

    def modify_event(self):
        """Modifie un événement sélectionné et actualise la date à l'heure actuelle."""
        if not self.conn:
            return

        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Aucune sélection", "Veuillez sélectionner un événement à modifier.")
            return

        event_id = self.tree.item(selected_item, "values")[0]
        new_description = self.event_entry.get().strip()

        if not new_description:
            messagebox.showwarning("Saisie manquante", "Veuillez entrer la nouvelle description de l'événement.")
            return

        try:
            # Modification ici : on ajoute 'date = CURRENT_TIMESTAMP'
            self.cursor.execute(
                "UPDATE tb_evenement SET evenements = %s, date = CURRENT_TIMESTAMP WHERE id = %s", 
                (new_description, event_id)
            )
            self.conn.commit()
            winsound.Beep(500, 200)
            messagebox.showinfo("Succès", "Événement et date mis à jour avec succès !")
            self.event_entry.delete(0, ctk.END)
            self.load_events()
        except psycopg2.Error as e:
            messagebox.showerror("Erreur de modification", f"Erreur lors de la modification : {e}")
            self.conn.rollback()

    def delete_event(self):
        """Supprime un événement sélectionné de la base de données."""
        if not self.conn:
            return

        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Aucune sélection", "Veuillez sélectionner un événement à supprimer.")
            return

        event_id = self.tree.item(selected_item, "values")[0]
        
        if messagebox.askyesno("Confirmer la suppression", "Êtes-vous sûr de vouloir supprimer cet événement ?"):
            try:
                self.cursor.execute("DELETE FROM tb_evenement WHERE id = %s", (event_id,))
                self.conn.commit()
                winsound.Beep(500, 200)
                messagebox.showinfo("Succès", "Événement supprimé avec succès !")
                self.event_entry.delete(0, ctk.END)
                self.load_events()
            except psycopg2.Error as e:
                messagebox.showerror("Erreur de suppression", f"Erreur lors de la suppression de l'événement : {e}")
                self.conn.rollback()

    def select_event(self, event):
        """Charge la description de l'événement sélectionné dans le champ de saisie."""
        selected_item = self.tree.focus()
        if selected_item:
            values = self.tree.item(selected_item, "values")
            self.event_entry.delete(0, ctk.END)
            self.event_entry.insert(0, values[2]) # La description est à l'index 2

    def __del__(self):
        """Ferme la connexion à la base de données lors de la destruction de l'objet."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

# --- Exemple d'utilisation de la classe PageEvenement ---
if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Gestion des Événements")
    app.geometry("800x600")

    # Définir le thème de CustomTkinter (optionnel, mais recommandé)
    ctk.set_appearance_mode("Light")  # Modes: "System" (par défaut), "Dark", "Light"
    ctk.set_default_color_theme("blue")  # Thèmes: "blue" (par défaut), "dark-blue", "green"

    event_page = PageEvenement(app)
    event_page.pack(fill="both", expand=True, padx=20, pady=20)

    app.mainloop()