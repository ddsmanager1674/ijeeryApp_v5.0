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
        # [UI] Fond et structure alignés sur app_theme (Nouveau SB)
        super().__init__(master, fg_color=Colors.BG_PAGE)
        self.pack(fill="both", expand=True)

        self.session_data = getattr(master, "session_data", None) or {}
        self._logger = AppLogger(conn=getattr(self, "conn", None), session_data=self.session_data)

        self.app_root = app_root

        # Database connection variables
        self.conn = None
        self.cursor = None
        
        # Dictionary to store references to dynamically created CTkEntry widgets for salary input
        self.entry_widgets = {}  # legacy (plus utilisé)
        self.selected_personnel_id: int | None = None
        self.selected_personnel_name = ctk.StringVar(value="")
        self.current_salary_var = ctk.StringVar(value="")
        self.new_salary_var = ctk.StringVar(value="")

        self._setup_treeview_style()
        # Initialize the user interface components
        self._init_ui()
        # Connect to the database and load initial data
        self._init_db_and_data()
        # Set up the window closing protocol
        self._setup_protocol()

    def _init_ui(self):
        """[UI] Interface structurée : sélection personnel → saisie salaire → enregistrement."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        header = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT, corner_radius=0, height=46)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        left = styled.frame(header)
        left.pack(side="left", padx=14, pady=0)
        ctk.CTkLabel(left, text="📋", font=Fonts.heading(16), text_color=Colors.TEXT_ON_DARK).pack(side="left", padx=(0, 8))
        inner = styled.frame(left)
        inner.pack(side="left")
        ctk.CTkLabel(inner, text="Nouveau SB", font=Fonts.bold(13), text_color=Colors.TEXT_ON_DARK).pack(anchor="w")
        ctk.CTkLabel(inner, text="Enregistrement du salaire de base", font=Fonts.small(9), text_color=Colors.TEXT_ON_DARK_DIM).pack(anchor="w")

        # Toolbar recherche
        toolbar = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        toolbar.grid(row=1, column=0, padx=10, pady=(10, 6), sticky="ew")
        toolbar.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(toolbar, text="Recherche", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(row=0, column=0, padx=(12, 8), pady=10, sticky="w")
        self.search_entry = ctk.CTkEntry(
            toolbar, height=32, fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            corner_radius=8, font=Fonts.body(11), placeholder_text="Nom ou prénom…"
        )
        self.search_entry.grid(row=0, column=1, padx=(0, 12), pady=10, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self._filter_personnels)
        styled.button_secondary(toolbar, text="Actualiser", icon="↻", width=120, height=32, command=self._filter_personnels).grid(
            row=0, column=2, padx=(0, 12), pady=10, sticky="e"
        )

        # Contenu: liste personnel (gauche) + fiche salaire (droite)
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 6))
        content.grid_columnconfigure(0, weight=3)
        content.grid_columnconfigure(1, weight=2)
        content.grid_rowconfigure(0, weight=1)

        list_card = ctk.CTkFrame(content, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        list_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        list_card.grid_columnconfigure(0, weight=1)
        list_card.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(list_card, columns=("nom", "prenom", "montant"), show="headings", style="P.Treeview", selectmode="browse")
        self._configure_table_alternating_colors(self.tree)
        self.tree.heading("nom", text="Nom")
        self.tree.heading("prenom", text="Prénom")
        self.tree.heading("montant", text="Salaire actuel")
        self.tree.column("nom", width=180, anchor="w")
        self.tree.column("prenom", width=180, anchor="w")
        self.tree.column("montant", width=140, anchor="e")
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        vsb = ttk.Scrollbar(list_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns", pady=6)
        self.tree.bind("<<TreeviewSelect>>", self._on_select_personnel)

        self.label_count = ctk.CTkLabel(list_card, text="Personnel affichés : 0", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY)
        self.label_count.grid(row=1, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 10))

        form_card = ctk.CTkFrame(content, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        form_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        form_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(form_card, text="Fiche salaire", font=Fonts.bold(12), text_color=Colors.TEXT_PRIMARY).grid(
            row=0, column=0, padx=12, pady=(12, 6), sticky="w"
        )
        ctk.CTkLabel(form_card, text="Personnel sélectionné", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(
            row=1, column=0, padx=12, pady=(6, 2), sticky="w"
        )
        self.personnel_entry = ctk.CTkEntry(
            form_card, textvariable=self.selected_personnel_name, height=32, fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            corner_radius=8, font=Fonts.body(11), state="readonly"
        )
        self.personnel_entry.grid(row=2, column=0, padx=12, pady=(0, 10), sticky="ew")

        ctk.CTkLabel(form_card, text="Salaire actuel", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(
            row=3, column=0, padx=12, pady=(0, 2), sticky="w"
        )
        self.current_salary_entry = ctk.CTkEntry(
            form_card, textvariable=self.current_salary_var, height=32, fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            corner_radius=8, font=Fonts.body(11), state="readonly"
        )
        self.current_salary_entry.grid(row=4, column=0, padx=12, pady=(0, 10), sticky="ew")

        # Historique (même table tb_salairebasepers)
        ctk.CTkLabel(form_card, text="Historique (derniers enregistrements)", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(
            row=5, column=0, padx=12, pady=(0, 2), sticky="w"
        )
        hist_card = ctk.CTkFrame(form_card, fg_color=Colors.BG_CARD, corner_radius=10, border_width=1, border_color=Colors.BORDER)
        hist_card.grid(row=6, column=0, padx=12, pady=(0, 10), sticky="nsew")
        hist_card.grid_columnconfigure(0, weight=1)
        hist_card.grid_rowconfigure(0, weight=1)

        self.history_tree = ttk.Treeview(hist_card, columns=("date", "montant"), show="headings", style="P.Treeview", height=5, selectmode="browse")
        self.history_tree.heading("date", text="Date")
        self.history_tree.heading("montant", text="Montant")
        self.history_tree.column("date", width=160, anchor="w")
        self.history_tree.column("montant", width=120, anchor="e")
        self.history_tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        hvsb = ttk.Scrollbar(hist_card, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=hvsb.set)
        hvsb.grid(row=0, column=1, sticky="ns", pady=6)
        self._configure_table_alternating_colors(self.history_tree)

        ctk.CTkLabel(form_card, text="Nouveau salaire (Ariary)", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(
            row=7, column=0, padx=12, pady=(0, 2), sticky="w"
        )
        self.new_salary_entry = ctk.CTkEntry(
            form_card, textvariable=self.new_salary_var, height=36, fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            corner_radius=8, font=Fonts.body(12), placeholder_text="Ex: 250000"
        )
        self.new_salary_entry.grid(row=8, column=0, padx=12, pady=(0, 12), sticky="ew")

        actions = ctk.CTkFrame(form_card, fg_color="transparent")
        actions.grid(row=9, column=0, padx=12, pady=(0, 12), sticky="ew")
        styled.button_success(actions, text="Enregistrer", icon="💾", width=160, height=34, command=self._enregistrer_sb).pack(side="left")
        styled.button_secondary(actions, text="Vider", icon="↺", width=120, height=34, command=self._clear_form).pack(side="left", padx=(10, 0))

    def _setup_treeview_style(self):
        # [UI] Style P.Treeview aligné sur Suivi présence / Absence
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
        Affiche nom/prénom + salaire actuel (dernier).
        """
        search_term = self._normalize_string(self.search_entry.get())
        print(f"Filtering personnels with search term: '{search_term}'")

        # Clear existing items in the treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
        print("Treeview cleared.")
        self._refresh_table_alternating_colors(self.tree)
        
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
                prenom_disp = (prenom or "").strip() if prenom is not None else ""
                prenom_disp = prenom_disp if prenom_disp else "-"
                nom_disp = (nom or "").strip() if nom is not None else ""
                nom_disp = nom_disp if nom_disp else "-"
                # Insert the professor into the treeview with their current salary
                self.tree.insert("", "end", iid=idprof, values=(nom_disp, prenom_disp, current_montant))
                inserted_count += 1
        self._refresh_table_alternating_colors(self.tree)
        
        print(f"Inserted {inserted_count} professors into the treeview.")
        if hasattr(self, "label_count"):
            self.label_count.configure(text=f"Personnel affichés : {inserted_count}")


    def _clear_form(self):
        self.selected_personnel_id = None
        self.selected_personnel_name.set("")
        self.current_salary_var.set("")
        self.new_salary_var.set("")
        if hasattr(self, "history_tree"):
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)

    def _on_select_personnel(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        try:
            pid = int(sel[0])
        except Exception:
            return
        values = self.tree.item(sel[0], "values")
        nom = values[0] if len(values) > 0 else ""
        prenom = values[1] if len(values) > 1 else ""
        salaire = values[2] if len(values) > 2 else ""
        self.selected_personnel_id = pid
        nom_disp = (str(nom).strip() if nom is not None else "") or "-"
        prenom_disp = (str(prenom).strip() if prenom is not None else "") or "-"
        self.selected_personnel_name.set(f"{nom_disp} {prenom_disp}".strip())
        self.current_salary_var.set(str(salaire) if salaire is not None else "")
        self.new_salary_var.set("")
        self._load_history(pid)
        try:
            self.new_salary_entry.focus_set()
        except Exception:
            pass

    def _load_history(self, idpers: int, limit: int = 8):
        # [LOGIQUE] Lecture historique depuis tb_salairebasepers
        if not getattr(self, "cursor", None):
            return
        if not hasattr(self, "history_tree"):
            return
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        try:
            self.cursor.execute(
                "SELECT date, montant FROM tb_salairebasepers WHERE idpers=%s ORDER BY date DESC LIMIT %s",
                (int(idpers), int(limit)),
            )
            rows = self.cursor.fetchall()
            for idx, (d, m) in enumerate(rows):
                d_str = d.strftime("%Y-%m-%d %H:%M") if hasattr(d, "strftime") else str(d)
                try:
                    m_val = float(m) if m is not None else 0.0
                    m_str = f"{m_val:,.2f}".replace(",", " ").replace(".", ",")
                except Exception:
                    m_str = str(m)
                self.history_tree.insert("", "end", values=(d_str, m_str))
            self._refresh_table_alternating_colors(self.history_tree)
        except Exception:
            return

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

        # [LOGIQUE] Enregistrement guidé : 1 personnel sélectionné
        if not self.selected_personnel_id:
            messagebox.showerror("Erreur", "Veuillez sélectionner un personnel dans la liste.")
            return
        montant_input = (self.new_salary_var.get() or "").strip().replace(" ", "").replace(",", ".")
        if not montant_input:
            messagebox.showerror("Erreur", "Veuillez saisir le nouveau salaire.")
            return
        try:
            montant_float = float(montant_input)
            if montant_float <= 0:
                messagebox.showerror("Erreur", "Le salaire doit être supérieur à zéro.")
                return
        except ValueError:
            messagebox.showerror("Erreur", "Veuillez entrer un nombre valide pour le salaire.")
            return

        try:
            self.cursor.execute(
                """
                INSERT INTO tb_salairebasepers (montant, idpers, date)
                VALUES (%s, %s, %s)
                """,
                (montant_float, int(self.selected_personnel_id), now),
            )
            success_count = 1
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Erreur SQL", f"Erreur lors de l'enregistrement : {e}")
            error_occurred = True

        if not error_occurred:
            self.conn.commit() # Commit all changes if no errors occurred
            try:
                self._logger.log(
                    action="Création salaire de base",
                    element=f"idpers={self.selected_personnel_id}",
                    details=f"Salaire de base enregistré (montant={montant_float}, date={now})",
                    value=str(montant_float),
                )
            except Exception:
                pass
            if success_count > 0:
                messagebox.showinfo("Succès", f"{success_count} salaires de base enregistrés avec succès.")
            else:
                messagebox.showinfo("Information", "Aucun nouveau salaire de base à enregistrer ou aucun changement détecté.")
            self._filter_personnels() # Refresh the view after saving to show updated data
            # rafraîchir l'historique du personnel courant puis reset formulaire
            pid = self.selected_personnel_id
            if pid:
                self._load_history(pid)
            self._clear_form()
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
