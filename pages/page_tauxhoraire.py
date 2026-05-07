import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime
import unicodedata
import os
import json
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
    
    def get_cursor(self):
        """Returns the database cursor if connected, otherwise attempts to connect."""
        if self.cursor is None or self.cursor.closed:
            if self.get_connection():
                self.cursor = self.conn.cursor()
            else:
                return None
        return self.cursor

    def close(self):
        """Closes the database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

# Instantiate DatabaseManager
db_manager = DatabaseManager()

class PageTauxHoraire(ctk.CTkFrame):
    # Ajoutez un paramètre 'app_root' pour la fenêtre principale
    def __init__(self, master, app_root):
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True) # Ce pack peut rester ici si cette page est le contenu principal du master

        self.app_root = app_root # Stockez une référence à la fenêtre racine de l'application
        self.conn = None
        self.cursor = None
        self.entry_widgets = {} # Stores references to the tk.Entry widgets for hourly rates

        self._connect_db()
        self._create_widgets()
        # Utilisez self.app_root.after au lieu de self.master.after
        self.app_root.after(150, self._filter_personnel)

        # Assurez-vous que la connexion à la base de données est fermée lorsque la fenêtre principale est fermée
        # Appelez .protocol() sur l'objet app_root, qui est la vraie fenêtre principale
        self.app_root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _connect_db(self):
        """Establishes a connection to the PostgreSQL database."""
        try:
        
            self.db_manager = db_manager
            self.conn = self.db_manager.get_connection()
        
            if self.conn is None:
                messagebox.showerror("Erreur de connexion", "Impossible de se connecter à la base de données.")
                self.is_connected = False
                return
            else:
                self.cursor = self.conn.cursor()
                self.is_connected = True

            # Create the tb_tauxhoraire table if it doesn't exist
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tb_tauxhoraire (
                    id SERIAL PRIMARY KEY,
                    tauxhoraire DOUBLE PRECISION,
                    idpers INT,
                    dateregistre TIMESTAMP
                )
                """
            )
            self.conn.commit()
        except psycopg2.Error as err:
            messagebox.showerror("Erreur de connexion", f"Erreur : {err}")
            self.conn = None # Set to None to indicate failed connection

    def _configure_table_alternating_colors(self, tree):
        tree.tag_configure("row_even", background="#FFFFFF")
        tree.tag_configure("row_odd", background="#D9EEED")

    def _refresh_table_alternating_colors(self, tree):
        for idx, item in enumerate(tree.get_children()):
            tree.item(item, tags=("row_even" if idx % 2 == 0 else "row_odd",))

    def _create_widgets(self):
        """Creates and arranges the UI widgets, including the search bar."""
        # --- Search Bar ---
        self.search_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.search_frame.pack(pady=10, padx=10, fill="x")

        self.search_label = ctk.CTkLabel(self.search_frame, text="Rechercher par nom/prénom :")
        self.search_label.pack(side="left", padx=(0, 10))

        self.search_entry = ctk.CTkEntry(self.search_frame, placeholder_text="Saisir le nom ou le prénom...")
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<KeyRelease>", self._filter_personnel) # Bind search logic

        # --- Treeview ---
        self.tree_frame = tk.Frame(self)
        self.tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.tree = ttk.Treeview(self.tree_frame, columns=("nom", "prenom", "tauxhoraire"), show="headings")
        self._configure_table_alternating_colors(self.tree)
        self.tree.heading("nom", text="Nom")
        self.tree.heading("prenom", text="Prénom")
        self.tree.heading("tauxhoraire", text="Taux Horaire (Ariary)")

        self.tree.column("nom", width=200)
        self.tree.column("prenom", width=200)
        self.tree.column("tauxhoraire", width=150)
        self.tree.pack(side="left", fill="both", expand=True)

        # Scrollbar
        self.scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")

        # --- Enregistrer button ---
        self.btn_enregistrer = ctk.CTkButton(self, text="Enregistrer", command=self._enregistrer_taux)
        self.btn_enregistrer.pack(pady=10)

    def _charger_personnel(self):
        """Fetches all professor data from the database."""
        if not self.cursor:
            return []
        try:
            self.cursor.execute("SELECT id, nom, prenom FROM tb_personnel ORDER BY nom, prenom")
            return self.cursor.fetchall()
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            messagebox.showerror("Erreur SQL", str(e))
            return []
    
    def _normalize_string(self, s):
        """Removes diacritics (accents) from a string and converts to lowercase."""
        if not isinstance(s, str):
            return ""
        return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()

    def _filter_personnel(self, event=None):
        """Filters the Treeview based on the search input and re-adds entry fields."""
        # Normalize the search term for comparison
        search_term = self._normalize_string(self.search_entry.get())

        # Clear existing items and entry widgets
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._refresh_table_alternating_colors(self.tree)
        
        # Destroy and clear entry widgets for visible rows
        for entry_widget in self.entry_widgets.values():
            if entry_widget.winfo_exists():
                entry_widget.destroy()
        self.entry_widgets.clear()

        # Reload and filter professors
        all_personnel = self._charger_personnel()
        for prof in all_personnel:
            idpers, nom, prenom = prof
            # Normalize professor's name and prenom for comparison
            normalized_nom = self._normalize_string(nom)
            normalized_prenom = self._normalize_string(prenom)

            # Fetch current hourly rate if it exists
            current_taux = ""
            if self.cursor:
                try:
                    self.cursor.execute("SELECT tauxhoraire FROM tb_tauxhoraire WHERE idpers = %s ORDER BY dateregistre DESC LIMIT 1", (idpers,))
                    result = self.cursor.fetchone()
                    if result:
                        current_taux = str(result[0])
                except Exception as e:
                    print(f"Erreur lors de la récupération du taux horaire pour {nom} {prenom}: {e}") # For debugging

            # Check if the normalized search term is in the normalized name or prenom
            if search_term in normalized_nom or search_term in normalized_prenom:
                self.tree.insert("", "end", iid=idpers, values=(nom, prenom, current_taux))
        self._refresh_table_alternating_colors(self.tree)
        
        # Re-add entry widgets for the filtered, visible rows
        self._add_entry_fields()

    def _add_entry_fields(self):
        """Adds Tkinter Entry widgets into the 'tauxhoraire' column of the Treeview."""
        for item in self.tree.get_children():
            bbox = self.tree.bbox(item, column=2)
            if bbox and len(bbox) == 4:
                x, y, width, height = bbox
                
                # Check if an entry widget already exists for this item and destroy it if it does
                if item in self.entry_widgets and self.entry_widgets[item].winfo_exists():
                    self.entry_widgets[item].destroy()

                taux_entry = tk.Entry(self.tree)
                
                # Insert current value from treeview into the entry field
                current_value = self.tree.item(item, 'values')[2]
                if current_value:
                    taux_entry.insert(0, current_value)

                taux_entry.place(x=x, y=y, width=width, height=height)
                self.entry_widgets[item] = taux_entry

    def _enregistrer_taux(self):
        """Saves the entered hourly rates to the database."""
        if not self.conn or not self.cursor:
            messagebox.showerror("Erreur", "Connexion à la base de données non établie.")
            return

        now = datetime.now()
        success_count = 0
        error_occurred = False

        # Iterate over all professors currently displayed in the treeview
        for idpers_str in self.tree.get_children():
            # Get the associated entry widget for this professor, if it exists
            entry = self.entry_widgets.get(idpers_str)
            if not entry: # Skip if no entry widget is found (e.g., if it was removed/destroyed)
                continue

            taux = entry.get().strip()
            
            # Get the current value from the treeview item to compare
            current_tree_value = self.tree.item(idpers_str, 'values')[2]

            if taux and (taux != current_tree_value): # Process if there's input and it's different
                try:
                    idpers = int(idpers_str)
                    taux_float = float(taux)

                    # Always insert a new record to keep a history of changes
                    self.cursor.execute(
                        """
                        INSERT INTO tb_tauxhoraire (tauxhoraire, idpers, dateregistre)
                        VALUES (%s, %s, %s)
                        """,
                        (taux_float, idpers, now)
                    )
                    success_count += 1
                except ValueError:
                    messagebox.showerror("Erreur de saisie", f"Veuillez entrer un nombre valide pour le taux horaire du personnel ID {idpers_str}.")
                    self.conn.rollback()
                    error_occurred = True
                    break # Stop processing on first error
                except Exception as e:
                    self.conn.rollback()
                    messagebox.showerror("Erreur SQL", f"Erreur pour ID {idpers_str} : {e}")
                    error_occurred = True
                    break # Stop processing on first error
            elif not taux and current_tree_value: # If field is cleared but there was a value
                # You might want to handle deletion or setting to NULL here if a cleared field means something
                pass # For now, we'll just ignore cleared fields if they had a value

        if not error_occurred:
            self.conn.commit()
            if success_count > 0:
                messagebox.showinfo("Succès", f"{success_count} taux horaires enregistrés ou mis à jour avec succès.")
            else:
                messagebox.showinfo("Information", "Aucun changement détecté ou enregistré.")
            self._filter_personnel() # Refresh the view after saving
        else:
            messagebox.showerror("Erreur", "Une erreur est survenue lors de l'enregistrement. Les modifications ont été annulées.")


    def _on_closing(self):
        """Handles actions when the main application window is closed."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        # N'appelez pas self.master.destroy() ou self.app_root.destroy() ici
        # si PageTauxHoraire est une sous-fenêtre d'une application plus grande.
        # La fenêtre principale (root) doit gérer sa propre destruction.
        # Cette fonction doit seulement nettoyer les ressources spécifiques à cette page.
        self.app_root.destroy() # Si cette page est le contenu principal, ceci fermera la fenêtre principale


if __name__ == "__main__":
    # --- Main Application Window Setup ---
    ctk.set_appearance_mode("Light")  # Modes: "System" (default), "Dark", "Light"
    ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"

    root = ctk.CTk() # Ceci est la vraie fenêtre principale
    root.title("Mise à jour des taux horaires par professeur")
    root.geometry("700x400")
    
    # Create an instance of the PageTauxHoraire class
    # Passez 'root' comme master ET comme app_root si cette page est le contenu principal
    app = PageTauxHoraire(master=root, app_root=root)

    root.mainloop()
