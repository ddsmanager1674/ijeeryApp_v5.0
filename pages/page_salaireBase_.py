import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime
import unicodedata # Import to handle accented characters
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


# Set CustomTkinter appearance and theme
# "System" matches the OS theme (Light/Dark), "Dark" is always dark, "Light" is always light
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"

class PageSalaireBase(ctk.CTkFrame):
    def __init__(self, master, app_root):
        super().__init__(master)
        self.app_root = app_root if app_root else master
    """
    A CustomTkinter page for managing professors' base salaries.
    Allows searching, displaying, and updating base salaries in a PostgreSQL database.
    """
    def __init__(self, master, app_root):
        """
        Initializes the PageSalaireBase frame.

        Args:
            master: The parent widget (e.g., ctk.CTk).
            app_root: The main application window, used for protocol handling (e.g., window closing).
        """
        # Call the constructor of the parent class (ctk.CTkFrame)
        super().__init__(master, fg_color="transparent")
        # Pack this main frame to fill the entire master window
        self.pack(fill="both", expand=True)

        self.app_root = app_root # Store reference to the main application window

        # Database connection variables
        self.conn = None
        self.cursor = None
        
        # Dictionary to store references to dynamically created CTkEntry widgets for salary input
        self.entry_widgets = {} 

        # Initialize the user interface components
        self._init_ui()
        # Connect to the database and load initial data
        self._init_db_and_data()
        # Set up the window closing protocol
        self._setup_protocol()

    def _init_ui(self):
        """
        Initializes and lays out all the UI components for the page.
        """
        # --- Search Zone ---
        self.search_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.search_frame.pack(pady=10, padx=10, fill="x")

        self.search_label = ctk.CTkLabel(self.search_frame, text="Rechercher par nom/prénom :")
        self.search_label.pack(side="left", padx=(0, 10))

        self.search_entry = ctk.CTkEntry(self.search_frame, placeholder_text="Saisir le nom ou le prénom...")
        self.search_entry.pack(side="left", fill="x", expand=True)
        # Bind the search entry's KeyRelease event to the filter method
        self.search_entry.bind("<KeyRelease>", self._filter_personnels)

        # --- Treeview for displaying professor data ---
        # Note: CustomTkinter does not have a direct CTkTreeview.
        # We use ttk.Treeview which is part of standard Tkinter's themed widgets.
        # Styling might not perfectly match CTk themes but it will function.
        self.tree_frame = ctk.CTkFrame(self, fg_color="transparent") # Use CTkFrame for the container
        self.tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Configure ttk.Treeview styles for better integration with dark mode
       # Configure ttk.Treeview styles for better integration with dark mode
        # This is a basic attempt; more comprehensive styling might require a custom theme
        style = ttk.Style()
        # Set background for headings
        style.configure("Treeview.Heading", background="#E8E8E8",
                        foreground="#000000",
                        font=('Segoe UI', 8, 'bold'))
        # Set background and foreground for rows
        style.configure("Treeview", background="#FFFFFF",
                        foreground="#000000",
                        fieldbackground="#FFFFFF",
                        borderwidth=0,
                        rowheight=22,
                        font=('Segoe UI', 8))

        # Create the Treeview widget
        self.tree = ttk.Treeview(self.tree_frame, columns=("nom", "prenom", "montant"), show="headings")
        self._configure_table_alternating_colors(self.tree)
        self.tree.heading("nom", text="Nom")
        self.tree.heading("prenom", text="Prénom")
        self.tree.heading("montant", text="Salaire de base (Ariary)")

        self.tree.column("nom", width=200, anchor="w")
        self.tree.column("prenom", width=200, anchor="w")
        self.tree.column("montant", width=150, anchor="e") # Right-align numbers
        self.tree.pack(side="left", fill="both", expand=True)

        # CustomTkinter Scrollbar for the Treeview
        self.scrollbar = ctk.CTkScrollbar(self.tree_frame, orientation="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")

        # --- Save Button ---
        self.btn_enregistrer = ctk.CTkButton(self, text="Enregistrer", command=self._enregistrer_sb)
        self.btn_enregistrer.pack(pady=10)

    def _configure_table_alternating_colors(self, tree):
        tree.tag_configure("row_even", background="#FFFFFF")
        tree.tag_configure("row_odd", background="#D9EEED")

    def _refresh_table_alternating_colors(self, tree):
        for idx, item in enumerate(tree.get_children()):
            tree.item(item, tags=("row_even" if idx % 2 == 0 else "row_odd",))

    def _init_db_and_data(self):
        """
        Attempts to connect to the database and initializes the data display.
        """
        print("Attempting to connect to the database and load initial data...")
        if not self._connect_db():
            # If connection fails, disable save button to prevent further errors
            self.btn_enregistrer.configure(state="disabled")
            messagebox.showerror("Erreur de connexion", "Impossible de se connecter à la base de données. Veuillez vérifier vos paramètres.")
            print("Database connection failed. Save button disabled.")
            return

        # Use self.after to ensure the UI is fully rendered before populating
        # This prevents issues with widget placement and sizing.
        print("Database connected. Calling _filter_professors to populate treeview.")
        self.after(150, self._filter_personnels)

    def _setup_protocol(self):
        """
        Sets up the window closing protocol to ensure database connection is closed.
        """
        self.app_root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _connect_db(self):
        """
        Establishes a connection to the PostgreSQL database.
        Initializes self.conn and self.cursor upon successful connection.
        Returns True if connection is successful, False otherwise.
        """
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

            # Create the tb_salairebasepers table if it does not exist
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tb_salairebasepers (
                    id SERIAL PRIMARY KEY,
                    idpers INT,
                    montant DOUBLE PRECISION,
                    date TIMESTAMP
                )
                """
            )
            self.conn.commit()
            print("Table 'tb_salairebasepers' checked/created.")
            return True # Indicate successful connection
        except psycopg2.Error as err:
            messagebox.showerror("Erreur de connexion", f"Erreur : {err}")
            self.conn = None # Set to None to indicate failed connection
            self.cursor = None
            print(f"Failed to connect to database: {err}")
            return False # Indicate failed connection

    def _normalize_string(self, s):
        """
        Removes diacritics (accents) from a string and converts to lowercase.
        Used for case-insensitive and accent-insensitive searching.
        """
        if not isinstance(s, str):
            return ""
        # Normalize to NFD (Canonical Decomposition) and remove combining characters (Mn)
        return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()

    def _charger_personnel(self):
        """
        Fetches all professor data (id, nom, prenom) from the tb_personnel table.
        Returns a list of tuples, sorted by nom and prenom.
        """
        if not self.cursor:
            print("Cursor is not available, cannot charge personnel.")
            return []
        try:
            self.cursor.execute("SELECT id, nom, prenom FROM tb_personnel ORDER BY nom, prenom")
            personnels = self.cursor.fetchall()
            print(f"Loaded {len(personnels)} professors from tb_personnel.")
            return personnels
        except Exception as e:
            if self.conn:
                self.conn.rollback() # Rollback in case of an error during fetch
            messagebox.showerror("Erreur SQL", f"Erreur lors du chargement des personnels: {e}")
            print(f"Error loading personnel: {e}")
            return []

    def _filter_personnels(self, event=None):
        """
        Filters the Treeview based on the search input.
        Clears existing entries, reloads personnels, and adds input fields for visible rows.
        """
        search_term = self._normalize_string(self.search_entry.get())
        print(f"Filtering personnels with search term: '{search_term}'")

        # Clear existing items in the treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
        print("Treeview cleared.")
        self._refresh_table_alternating_colors(self.tree)
        
        # Destroy and clear CTkEntry widgets for visible rows
        # This is important to prevent orphaned widgets when the Treeview is refreshed
        for entry_widget in self.entry_widgets.values():
            if entry_widget.winfo_exists(): # Check if the widget still exists before destroying
                entry_widget.destroy()
        self.entry_widgets.clear()
        print("Existing salary entry widgets destroyed and cleared.")

        # Reload and filter professors
        all_personnel = self._charger_personnel()
        inserted_count = 0
        for prof in all_personnel:
            idprof, nom, prenom = prof
            # Normalize professor's name and prenom for comparison with search term
            normalized_nom = self._normalize_string(nom)
            normalized_prenom = self._normalize_string(prenom)

            # Fetch current base salary if it exists
            current_montant = ""
            if self.cursor:
                try:
                    # Get the most recent base salary for the professor
                    self.cursor.execute("SELECT montant FROM tb_salairebasepers WHERE idpers = %s ORDER BY date DESC LIMIT 1", (idprof,))
                    result = self.cursor.fetchone()
                    if result:
                        current_montant = str(result[0]) # Convert float to string for display
                except Exception as e:
                    print(f"Erreur lors de la récupération du salaire de base pour {nom} {prenom}: {e}") # For debugging purposes

            # Check if the normalized search term is present in the normalized name or prenom
            if search_term in normalized_nom or search_term in normalized_prenom:
                # Insert the professor into the treeview with their current salary
                self.tree.insert("", "end", iid=idprof, values=(nom, prenom, current_montant))
                inserted_count += 1
        self._refresh_table_alternating_colors(self.tree)
        
        print(f"Inserted {inserted_count} professors into the treeview.")
        # Re-add CTkEntry widgets for the filtered, visible rows
        self._ajouter_champs_saisie()
        print("Salary entry fields added/updated.")


    def _ajouter_champs_saisie(self):
        """
        Adds CustomTkinter Entry widgets into the 'montant' column of the Treeview.
        These entries allow users to input or modify base salaries.
        """
        # Iterate over all items currently visible in the Treeview
        for item in self.tree.get_children():
            # Get the bounding box of the 'montant' column for the current item
            bbox = self.tree.bbox(item, column=2)
            if bbox and len(bbox) == 4: # Ensure bbox is valid (x, y, width, height)
                x, y, width, height = bbox
                
                # If an entry widget already exists for this item and is still valid, destroy it
                # This handles refreshing the entries when the treeview content changes
                if item in self.entry_widgets and self.entry_widgets[item].winfo_exists():
                    self.entry_widgets[item].destroy()

                # Create a new CTkEntry widget, parented to the treeview
                # Set fg_color to match treeview background and text_color for readability
                taux_entry = ctk.CTkEntry(self.tree, 
                                          width=width,  # Pass width to constructor
                                          height=height, # Pass height to constructor
                                          fg_color=ctk.ThemeManager.theme["CTkFrame"]["fg_color"],
                                          text_color=ctk.ThemeManager.theme["CTkLabel"]["text_color"],
                                          corner_radius=5) # Add rounded corners

                # Insert the current value from the treeview into the entry field
                current_value = self.tree.item(item, 'values')[2]
                if current_value:
                    taux_entry.insert(0, current_value)

                # Place the entry widget precisely over the Treeview cell
                # REMOVED width=width, height=height from place() method
                taux_entry.place(x=x, y=y) 
                # Store the reference to the entry widget using the item ID as key
                self.entry_widgets[item] = taux_entry

    def _enregistrer_sb(self):
        """
        Saves the entered base salaries to the database.
        Each modification creates a new record in tb_salairebasepers to maintain history.
        """
        if not self.conn or not self.cursor:
            messagebox.showerror("Erreur", "Connexion à la base de données non établie.")
            return

        now = datetime.now() # Get current timestamp for the record
        success_count = 0
        error_occurred = False

        # Iterate over all professor IDs currently displayed in the treeview
        for idpers_str in self.tree.get_children():
            # Get the associated CTkEntry widget for this professor
            entry = self.entry_widgets.get(idpers_str)
            if not entry: # Skip if no entry widget is found for this item
                continue

            montant_input = entry.get().strip() # Get the text from the entry field
            
            # Get the current value displayed in the treeview for comparison
            # This helps avoid saving identical data unnecessarily
            current_tree_value = self.tree.item(idpers_str, 'values')[2]

            # Only process if a value is entered AND it's different from the currently displayed value
            if montant_input and (montant_input != current_tree_value): 
                try:
                    idpers = int(idpers_str) # Convert item ID (which is prof ID) to integer
                    montant_float = float(montant_input) # Convert salary input to float

                    # Always insert a new record to keep a historical log of salary changes
                    self.cursor.execute(
                        """
                        INSERT INTO tb_salairebasepers (montant, idpers, date)
                        VALUES (%s, %s, %s)
                        """,
                        (montant_float, idpers, now)
                    )
                    success_count += 1 # Increment success counter
                except ValueError:
                    # Handle cases where the input is not a valid number
                    messagebox.showerror("Erreur de saisie", f"Veuillez entrer un nombre valide pour le salaire du personnel ID {idpers_str} ('{montant_input}' n'est pas un nombre valide).")
                    self.conn.rollback() # Rollback all changes if any error occurs
                    error_occurred = True
                    break # Stop processing on the first error
                except Exception as e:
                    # Handle other potential database errors
                    self.conn.rollback() # Rollback all changes
                    messagebox.showerror("Erreur SQL", f"Erreur lors de l'enregistrement du salaire pour ID {idpers_str} : {e}")
                    error_occurred = True
                    break # Stop processing on the first error
            # If montant_input is empty, or if it's the same as the current_tree_value, we do nothing.
            # If explicit handling for clearing a salary (e.g., setting to NULL) is needed,
            # that logic would be added here.

        if not error_occurred:
            self.conn.commit() # Commit all changes if no errors occurred
            if success_count > 0:
                messagebox.showinfo("Succès", f"{success_count} salaires de base enregistrés avec succès.")
            else:
                messagebox.showinfo("Information", "Aucun nouveau salaire de base à enregistrer ou aucun changement détecté.")
            self._filter_personnels() # Refresh the view after saving to show updated data
        else:
            # An error message was already shown in the loop, this is a final summary
            messagebox.showerror("Erreur", "Une ou plusieurs erreurs sont survenues lors de l'enregistrement. Les modifications ont été annulées.")

    def _on_closing(self):
        """
        Handles actions when the application window is closed.
        Ensures the database connection and cursor are properly closed.
        """
        if self.cursor:
            self.cursor.close()
            print("Database cursor closed.")
        if self.conn:
            self.conn.close()
            print("Database connection closed.")
        self.app_root.destroy() # Close the main application window

# --- Main execution block ---
if __name__ == "__main__":
    root = ctk.CTk()
    root.title("Mise à jour salaire de base")
    root.geometry("900x700")

    # Create an instance of the PageSalaireBase class
    # The 'root' is passed as both master (parent widget) and app_root (main window for protocol)
    app = PageSalaireBase(master=root, app_root=root)
    app.pack(fill="both", expand=True)

    
    # Start the CustomTkinter event loop
    root.mainloop()
