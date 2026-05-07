import customtkinter as ctk
import psycopg2
import tkinter.messagebox
import tkinter.ttk as ttk
import os
import json
import sys
from datetime import datetime
from tkinter import filedialog
from resource_utils import get_config_path, safe_file_read


# Ensure the parent directory is in the Python path for absolute imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    

from pages.page_pmtActivite import page_pmtActivite
    
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


# Import openpyxl for Excel export
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment
except ImportError:
    tkinter.messagebox.showerror("Erreur d'Importation", "La bibliothèque 'openpyxl' est nécessaire pour l'export Excel. Veuillez l'installer avec 'pip install openpyxl'.")
    sys.exit(1) # Exit if openpyxl is not found

# MODIFICATION PRINCIPALE : Hériter de CTkFrame au lieu de CTkToplevel
class PageActivitePrix(ctk.CTkFrame):
    def __init__(self, master=None, app_root=None, db_conn=None, session_data=None, db_config=None, **kwargs):
        super().__init__(master, **kwargs)

        self.app_root = app_root or master
        self.db_conn = db_manager
        self.session_data = session_data
        self.db_config = db_config

        # Plus besoin de geometry() car c'est un frame
        # self.title() et autres méthodes de fenêtre ne sont plus disponibles

        self.db_params = self.db_conn.db_params

        self.activites_data = {}
        self.series_data = {}
        self.latest_annee_scolaire_id = None
        self.latest_annee_scolaire_designation = None
        self.mois_scolaire_data = []

        self.fetch_initial_data()
        self.create_widgets()

        self.load_prices_into_treeview()
        self.load_etudiants_data()

        if hasattr(self, 'lower_treeview'):
            self.lower_treeview.bind("<Double-1>", self.on_lower_treeview_double_click)

    def fetch_initial_data(self):
        """Récupère les données d'activités, de séries et l'ID de la dernière année scolaire."""
        conn = None
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor()

            cur.execute("SELECT id, designationactivite FROM tb_activite ORDER BY designationactivite")
            for activite_id, designation in cur.fetchall():
                self.activites_data[designation] = activite_id
            
            if not self.activites_data:
                tkinter.messagebox.showwarning("Données manquantes", "Aucune activité trouvée. Veuillez en ajouter.")
                return

            cur.execute("SELECT id, designation FROM tb_serie ORDER BY designation")
            for serie_id, designation in cur.fetchall():
                self.series_data[designation] = serie_id
            
            if not self.series_data:
                tkinter.messagebox.showwarning("Données manquantes", "Aucune série trouvée. Veuillez en ajouter.")
                return

            cur.execute("SELECT id, designation FROM tb_anneescolaire ORDER BY designation DESC LIMIT 1")
            result = cur.fetchone()
            if result:
                self.latest_annee_scolaire_id = result[0]
                self.latest_annee_scolaire_designation = result[1]
            else:
                tkinter.messagebox.showwarning("Données manquantes", "Aucune année scolaire trouvée.")
                return
            
            self.fetch_mois_scolaire(cur)

        except psycopg2.Error as e:
            tkinter.messagebox.showerror("Erreur de Base de Données", f"Impossible de charger les données initiales : {e}")
        finally:
            if conn:
                conn.close()

    def fetch_mois_scolaire(self, cur):
        """Récupère les désignations des mois scolaires."""
        cur.execute("SELECT designation FROM tb_moisscolaire ORDER BY id")
        self.mois_scolaire_data = [row[0] for row in cur.fetchall()]

    def create_widgets(self):
        # Titre principal de la page
        title_label = ctk.CTkLabel(self, text="Activités et Prix", font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"))
        title_label.pack(pady=10)

        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        
        main_frame.grid_rowconfigure(0, weight=2) 
        main_frame.grid_rowconfigure(1, weight=1) 

        input_frame = ctk.CTkFrame(main_frame)
        input_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(input_frame, text="Champ de saisie", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")).pack(pady=(5, 10))

        ctk.CTkLabel(input_frame, text="Activité :").pack(pady=(2,0))
        activite_options = sorted(list(self.activites_data.keys()))
        activite_combobox_frame = ctk.CTkFrame(input_frame)
        activite_combobox_frame.pack(pady=(0, 5))
        self.activite_combobox = ctk.CTkComboBox(activite_combobox_frame,
                                                values=activite_options,
                                                command=self.load_prices_into_treeview,
                                                width=200)
        self.activite_combobox.pack(side="left")
        add_activite_button = ctk.CTkButton(activite_combobox_frame, text="+", width=30, fg_color="blue", text_color="white", command=self.open_add_activite_window)
        add_activite_button.pack(side="left", padx=(5,0))

        ctk.CTkLabel(input_frame, text="Série :").pack(pady=(2,0))
        serie_options = sorted(list(self.series_data.keys()))
        self.serie_combobox = ctk.CTkComboBox(input_frame,
                                             values=serie_options,
                                             width=200)
        self.serie_combobox.pack(pady=(0, 5))

        ctk.CTkLabel(input_frame, text="Montant :").pack(pady=(2,0))
        self.montant_entry = ctk.CTkEntry(input_frame, placeholder_text="0.00", width=200)
        self.montant_entry.pack(pady=(0, 5))

        self.save_button = ctk.CTkButton(
            input_frame,
            text="Enregistrer",
            command=self.save_activite_prix,
            fg_color="green",  
            text_color="white"
        )
        self.save_button.pack(pady=(5, 5)) 

        treeview_frame = ctk.CTkFrame(main_frame)
        treeview_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew") 
        treeview_frame.grid_rowconfigure(0, weight=0)
        treeview_frame.grid_rowconfigure(1, weight=1)
        treeview_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(treeview_frame, text="Prix par Série", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")).grid(row=0, column=0, pady=(10, 20), sticky="n")

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#FFFFFF", foreground="#000000", fieldbackground="#FFFFFF", borderwidth=0, rowheight=22, font=('Segoe UI', 8))
        style.configure("Treeview.Heading", background="#E8E8E8", foreground="#000000", font=('Segoe UI', 8, 'bold'))
        
        # Couleurs simplifiées pour éviter les erreurs
        bg_color = "#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#ffffff"
        fg_color = "#ffffff" if ctk.get_appearance_mode() == "Dark" else "#000000"
        select_color = "#1f538d" if ctk.get_appearance_mode() == "Dark" else "#0078d4"
        
        style.configure("Treeview",
                        background=bg_color,
                        foreground=fg_color,
                        fieldbackground=bg_color,
                        lightcolor=bg_color,
                        darkcolor=bg_color,
                        rowheight=25
                        )
        style.map('Treeview', background=[('selected', select_color)])
        
        style.configure("Treeview.Heading",
                        font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                        background=select_color,
                        foreground="white"
                        )
        style.map('Treeview.Heading', background=[('active', select_color)])

        self.treeview = ttk.Treeview(treeview_frame, columns=("Serie", "Montant"), show="headings")
        self.treeview.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        self.treeview.heading("Serie", text="SERIE", anchor="center")
        self.treeview.heading("Montant", text="MONTANT", anchor="center")

        self.treeview.column("Serie", width=150, anchor="w")
        self.treeview.column("Montant", width=100, anchor="e")

        scrollbar = ctk.CTkScrollbar(treeview_frame, command=self.treeview.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", padx=(0,10), pady=10)
        self.treeview.configure(yscrollcommand=scrollbar.set)

        self.treeview.bind("<Double-1>", self.on_treeview_double_click)

        # --- DÉBUT DU DEUXIÈME TREEVIEW ---
        lower_treeview_frame = ctk.CTkFrame(main_frame)
        lower_treeview_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew") 
        
        # Configure rows for lower_treeview_frame
        lower_treeview_frame.grid_rowconfigure(0, weight=0) # For the title
        lower_treeview_frame.grid_rowconfigure(1, weight=1) # For the Treeview itself (allow it to expand)
        lower_treeview_frame.grid_rowconfigure(2, weight=0) # NEW: For the horizontal scrollbar (minimal height)
        lower_treeview_frame.grid_columnconfigure(0, weight=1) # For Treeview and horizontal scrollbar

        # Frame for title and export button
        title_export_frame = ctk.CTkFrame(lower_treeview_frame, fg_color="transparent")
        title_export_frame.grid(row=0, column=0, sticky="ew", pady=(10, 5))
        title_export_frame.grid_columnconfigure(0, weight=1) # For title
        title_export_frame.grid_columnconfigure(1, weight=0) # For button

        ctk.CTkLabel(title_export_frame, text="Liste des Étudiants", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")).grid(row=0, column=0, sticky="w", padx=10)
        
        # New Export Excel Button
        self.export_excel_button = ctk.CTkButton(
            title_export_frame,
            text="Exporter Excel",
            command=self.export_to_excel,
            fg_color="darkgreen",
            text_color="white",
            width=120
        )
        self.export_excel_button.grid(row=0, column=1, sticky="e", padx=10)

        lower_treeview_columns = ["No", "Matricule", "Nom et prénom"] + self.mois_scolaire_data
        # MODIFICATION ICI : Ajouter xscrollcommand pour le treeview
        self.lower_treeview = ttk.Treeview(lower_treeview_frame, columns=lower_treeview_columns, show="headings")
        self.lower_treeview.grid(row=1, column=0, sticky="nsew", padx=10, pady=10) # Treeview placed in row 1, column 0

        self.lower_treeview.heading("No", text="N°", anchor="center")
        self.lower_treeview.heading("Matricule", text="Matricule", anchor="center")
        self.lower_treeview.heading("Nom et prénom", text="Nom et prénom", anchor="w")
        for mois in self.mois_scolaire_data:
            self.lower_treeview.heading(mois, text=mois, anchor="center")
            self.lower_treeview.column(mois, width=80, anchor="center") 

        self.lower_treeview.column("No", width=50, anchor="center")
        self.lower_treeview.column("Matricule", width=100, anchor="w")
        self.lower_treeview.column("Nom et prénom", width=200, anchor="w")

        # Barre de défilement verticale pour le deuxième Treeview (inchangée)
        lower_scrollbar = ctk.CTkScrollbar(lower_treeview_frame, command=self.lower_treeview.yview)
        lower_scrollbar.grid(row=1, column=1, sticky="ns", padx=(0,10), pady=10) # Placed in row 1, column 1 (next to treeview)
        # MODIFICATION ICI : Assurez-vous que le treeview utilise les deux scrollbars
        self.lower_treeview.configure(yscrollcommand=lower_scrollbar.set)

        # NOUVEAU : Barre de défilement horizontale pour le deuxième Treeview
        lower_h_scrollbar = ctk.CTkScrollbar(lower_treeview_frame, orientation="horizontal", command=self.lower_treeview.xview)
        lower_h_scrollbar.grid(row=2, column=0, sticky="ew", padx=10, pady=(0,10)) # Placed in row 2, column 0 (below treeview)
        # MODIFICATION ICI : Configurez le treeview pour utiliser le scrollbar horizontal
        self.lower_treeview.configure(xscrollcommand=lower_h_scrollbar.set)
        # --- FIN DU DEUXIÈME TREEVIEW ---

    def on_treeview_double_click(self, event):
        """Gère l'événement de double-clic sur le premier treeview."""
        selected_item = self.treeview.selection()
        if selected_item:
            item_id = selected_item[0]
            item_values = self.treeview.item(item_id, 'values')
            if not item_values:
                return
            selected_serie_designation = item_values[0]

            serie_id = self.series_data.get(selected_serie_designation)
            if serie_id is not None:
                self.load_etudiants_data(serie_id=serie_id)
            else:
                tkinter.messagebox.showwarning("Série Inconnue", "La série sélectionnée n'a pas pu être trouvée dans les données.")

    def format_currency_ar(self, amount):
        """
        Formate un montant numérique au format "10.000,00 Ar".
        """
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            return "N/A Ar"

        amount_str = f"{amount:.2f}"

        parts = amount_str.split('.')
        integer_part = parts[0]
        decimal_part = parts[1]

        formatted_integer = ""
        for i, digit in enumerate(reversed(integer_part)):
            if i > 0 and i % 3 == 0:
                formatted_integer = "." + formatted_integer
            formatted_integer = digit + formatted_integer
        
        return f"{formatted_integer},{decimal_part} Ar"

    def load_prices_into_treeview(self, event=None):
        """Charge les prix des activités de la base de données dans le Treeview."""
        for item in self.treeview.get_children():
            self.treeview.delete(item)

        selected_activite_designation = self.activite_combobox.get()
        
        if selected_activite_designation not in self.activites_data or self.latest_annee_scolaire_id is None:
            return

        id_activite = self.activites_data[selected_activite_designation]
        id_annee_scolaire = self.latest_annee_scolaire_id

        conn = None
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor()

            sql = """
            SELECT ts.designation, tap.montant
            FROM tb_activiteprix tap
            JOIN tb_serie ts ON tap.idserie = ts.id
            WHERE tap.idactivite = %s AND tap.idanneescolaire = %s
            ORDER BY ts.designation
            """
            cur.execute(sql, (id_activite, id_annee_scolaire))
            
            rows = cur.fetchall()
            for row in rows:
                serie_designation = row[0]
                montant_formatte = self.format_currency_ar(row[1])
                self.treeview.insert("", "end", values=(serie_designation, montant_formatte))

        except psycopg2.Error as e:
            tkinter.messagebox.showerror("Erreur de Chargement", f"Impossible de charger les prix : {e}")
        finally:
            if conn:
                conn.close()

    def load_etudiants_data(self, serie_id=None):
        """
        Charge les données des étudiants dans le deuxième Treeview.
        Optionnellement, filtre les étudiants par la série donnée (via tb_etudiant.idserie).
        """
        for item in self.lower_treeview.get_children():
            self.lower_treeview.delete(item)

        conn = None
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor()

            # Étape 1 : Trouver le dernier idanneescolaire
            cur.execute("SELECT MAX(idanneescolaire) FROM tb_etudiant")
            latest_annee_scolaire_id = cur.fetchone()[0]

            if latest_annee_scolaire_id is None:
                return # Sortir si aucune année scolaire n'est trouvée

            # Étape 2 : Charger les étudiants pour le dernier idanneescolaire
            sql_etudiants = """
                SELECT id, matricule, nom, prenom, dateinscription, idanneescolaire
                FROM tb_etudiant
                WHERE idanneescolaire = %s
            """
            params_etudiants = [latest_annee_scolaire_id]

            if serie_id is not None:
                sql_etudiants += " AND idserie = %s"
                params_etudiants.append(serie_id)

            sql_etudiants += " ORDER BY dateinscription ASC"

            cur.execute(sql_etudiants, tuple(params_etudiants))
            etudiants = cur.fetchall()

            # Le reste de votre code pour charger les paiements et afficher dans le Treeview
            paiements_mensuels = {}
        
            # Récupérer les paiements pour l'activité sélectionnée et l'année scolaire actuelle
            selected_activite_designation = self.activite_combobox.get()
            id_activite = self.activites_data.get(selected_activite_designation)

            if id_activite:
                cur.execute("""
                    SELECT matricule, designationmois
                    FROM tb_pmtactivite
                    WHERE designationannee = %s AND idactivite = %s
                """, (self.latest_annee_scolaire_designation, id_activite))
            
                for matricule_paiement, designationmois_paiement in cur.fetchall():
                    paiements_mensuels[(matricule_paiement, designationmois_paiement)] = "P"

            for i, etudiant in enumerate(etudiants):
                etudiant_id, matricule, nom, prenom, dateinscription, idanneescolaire = etudiant
            
                numero = len(etudiants) - i 
                full_name = f"{nom} {prenom}"

                row_values = [numero, matricule, full_name]
            
                for mois_designation in self.mois_scolaire_data: 
                    status = paiements_mensuels.get((matricule, mois_designation), "") 
                    row_values.append(status)
            
                self.lower_treeview.insert("", "end", values=row_values)

        except psycopg2.Error as e:
            tkinter.messagebox.showerror("Erreur de Chargement", f"Impossible de charger les données des étudiants : {e}")
        finally:
            if conn:
                conn.close()

    def save_activite_prix(self):
        selected_activite_designation = self.activite_combobox.get()
        selected_serie_designation = self.serie_combobox.get()
        montant_str = self.montant_entry.get().strip()

        if not selected_activite_designation or selected_activite_designation == "Aucune activité disponible":
            tkinter.messagebox.showwarning("Sélection invalide", "Veuillez sélectionner une activité.")
            return
        if not selected_serie_designation or selected_serie_designation == "Aucune série disponible":
            tkinter.messagebox.showwarning("Sélection invalide", "Veuillez sélectionner une série.")
            return
        
        if selected_activite_designation not in self.activites_data:
            tkinter.messagebox.showwarning("Erreur", "Activité sélectionnée introuvable dans les données chargées.")
            return
        if selected_serie_designation not in self.series_data:
            tkinter.messagebox.showwarning("Erreur", "Série sélectionnée introuvable dans les données chargées.")
            return

        try:
            montant = float(montant_str)
            if montant < 0:
                raise ValueError("Le montant ne peut pas être négatif.")
        except ValueError:
            tkinter.messagebox.showwarning("Montant invalide", "Veuillez saisir un montant numérique valide.")
            return

        if self.latest_annee_scolaire_id is None:
            tkinter.messagebox.showerror("Erreur", "Impossible de déterminer l'année scolaire. Veuillez vérifier la base de données.")
            return

        id_activite = self.activites_data[selected_activite_designation]
        id_serie = self.series_data[selected_serie_designation]
        id_annee_scolaire = self.latest_annee_scolaire_id

        conn = None
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor()

            cur.execute("""
                SELECT id FROM tb_activiteprix
                WHERE idactivite = %s AND idserie = %s AND idanneescolaire = %s
            """, (id_activite, id_serie, id_annee_scolaire))
            
            existing_id = cur.fetchone()

            if existing_id:
                sql = """
                UPDATE tb_activiteprix
                SET montant = %s
                WHERE id = %s
                """
                cur.execute(sql, (montant, existing_id[0]))
                message = "Prix d'activité mis à jour avec succès !"
            else:
                sql = """
                INSERT INTO tb_activiteprix (montant, idserie, idanneescolaire, idactivite)
                VALUES (%s, %s, %s, %s)
                """
                cur.execute(sql, (montant, id_serie, id_annee_scolaire, id_activite))
                message = "Prix d'activité enregistré avec succès !"
            
            conn.commit()

            tkinter.messagebox.showinfo("Succès", message)
            self.montant_entry.delete(0, ctk.END)
            self.load_prices_into_treeview()

        except psycopg2.Error as e:
            tkinter.messagebox.showerror("Erreur de Base de Données", f"Une erreur est survenue lors de l'opération : {e}")
        finally:
            if conn:
                conn.close()

    def on_lower_treeview_double_click(self, event):
        """Ouvre la fenêtre de paiement d'activité pour l'étudiant sélectionné."""
        selected_item = self.lower_treeview.selection()
        if not selected_item:
            return
        item_id = selected_item[0]
        values = self.lower_treeview.item(item_id, 'values')
        if not values or len(values) < 3:
            return
        matricule = values[1]
        nom_prenom = values[2]
        nom, prenom = nom_prenom.split(' ', 1) if ' ' in nom_prenom else (nom_prenom, "")
        montant_droit = None
        try:
            selected_activite = self.activite_combobox.get()
            selected_serie = self.serie_combobox.get()
            id_activite = self.activites_data.get(selected_activite)
            id_serie = self.series_data.get(selected_serie)
            id_annee = self.latest_annee_scolaire_id
            if id_activite and id_serie and id_annee:
                conn = psycopg2.connect(**self.db_params)
                cur = conn.cursor()
                cur.execute("""
                    SELECT montant FROM tb_activiteprix
                    WHERE idactivite = %s AND idserie = %s AND idanneescolaire = %s
                """, (id_activite, id_serie, id_annee))
                result = cur.fetchone()
                if result:
                    montant_droit = result[0]
                cur.close()
                conn.close()
        except Exception as e:
            montant_droit = None
        
        # Création et affichage de la fenêtre de paiement (reste une Toplevel car c'est une fenêtre modale)
        try:
            # Utiliser self.winfo_toplevel() pour obtenir la fenêtre principale
            main_window = self.winfo_toplevel()
            
            paiement_window = page_pmtActivite(
                master=main_window,  # Fenêtre principale comme parent
                matricule=matricule,
                nom=nom,
                prenom=prenom,
                montant_droit=montant_droit,
                idactivite=self.activites_data.get(self.activite_combobox.get()),
                designation_annee=self.latest_annee_scolaire_designation
            )
            
            # Vérifier si la fenêtre existe encore avant de faire grab_set
            if paiement_window and paiement_window.winfo_exists():
                paiement_window.grab_set()
                
                # Le rafraîchissement est géré dans la fenêtre de paiement elle-même ou en la détruisant
                def refresh_on_close():
                    if paiement_window and paiement_window.winfo_exists():
                        paiement_window.destroy()
                    self.load_etudiants_data()
                    
                paiement_window.protocol("WM_DELETE_WINDOW", refresh_on_close)
        except Exception as e:
            tkinter.messagebox.showerror("Erreur", f"Impossible d'ouvrir la fenêtre de paiement : {e}")

    def export_to_excel(self):
        """Exports the data from the lower_treeview to an Excel file."""
        if not self.lower_treeview.get_children():
            tkinter.messagebox.showwarning("Export vide", "Il n'y a pas de données à exporter dans le tableau.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Fichiers Excel", "*.xlsx"), ("Tous les fichiers", "*.*")],
            title="Enregistrer la liste des étudiants"
        )

        if not file_path:
            return # User cancelled the dialog

        try:
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Liste Etudiants Paiements"

            # Write headers
            columns = [self.lower_treeview.heading(col, "text") for col in self.lower_treeview["columns"]]
            sheet.append(columns)

            # Style headers
            header_font = Font(bold=True)
            for col_idx, cell in enumerate(sheet[1]):
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
                # Adjust column width based on content
                max_length = 0
                for row_idx, item_id in enumerate(self.lower_treeview.get_children()):
                    value = str(self.lower_treeview.item(item_id, 'values')[col_idx])
                    if len(value) > max_length:
                        max_length = len(value)
                adjusted_width = (max_length + 2) if max_length > len(columns[col_idx]) else (len(columns[col_idx]) + 2)
                sheet.column_dimensions[chr(65 + col_idx)].width = adjusted_width

            # Write data rows
            for item_id in self.lower_treeview.get_children():
                values = self.lower_treeview.item(item_id, 'values')
                sheet.append(values)
            
            workbook.save(file_path)
            tkinter.messagebox.showinfo("Export Réussi", f"Les données ont été exportées avec succès vers :\n{file_path}")

        except Exception as e:
            tkinter.messagebox.showerror("Erreur d'Export", f"Une erreur est survenue lors de l'exportation vers Excel : {e}")

    def open_add_activite_window(self):
        try:
            from pages.page_activite import PageActivite
            # Utiliser self.winfo_toplevel() pour obtenir la fenêtre principale
            main_window = self.winfo_toplevel()
            
            def on_close():
                self.reload_activites()
                if add_window and add_window.winfo_exists():
                    add_window.destroy()
                    
            add_window = PageActivite(main_window)
            if add_window and add_window.winfo_exists():
                add_window.protocol("WM_DELETE_WINDOW", on_close)
                add_window.grab_set()
        except Exception as e:
            tkinter.messagebox.showerror("Erreur", f"Impossible d'ouvrir la fenêtre d'activité : {e}")

    def reload_activites(self):
        """Recharge la liste des activités dans la combobox après ajout."""
        conn = None
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor()
            cur.execute("SELECT id, designationactivite FROM tb_activite ORDER BY designationactivite")
            self.activites_data = {designation: activite_id for activite_id, designation in cur.fetchall()}
            activite_options = sorted(list(self.activites_data.keys()))
            self.activite_combobox.configure(values=activite_options)
        except psycopg2.Error as e:
            tkinter.messagebox.showerror("Erreur de Base de Données", f"Impossible de recharger les activités : {e}")
        finally:
            if conn:
                conn.close()

# Fonction utilitaire pour intégrer la page dans app_main
def show_page_activite_prix(parent_frame, app_root=None):
    """
    Fonction pour afficher la page d'activités et prix dans un frame parent.
    À appeler depuis app_main.py
    """
    # Nettoyer le frame parent
    for widget in parent_frame.winfo_children():
        widget.destroy()
    
    # Créer et afficher la page
    page = PageActivitePrix(parent_frame, app_root=app_root)
    page.pack(fill="both", expand=True)
    
    return page

# Exemple d'utilisation dans app_main (à ajouter dans app_main.py)
"""
Dans app_main.py, vous devriez avoir quelque chose comme :

def show_activite_prix_page(self):
    from pages.page_activitePrix import show_page_activite_prix
    self.current_page = show_page_activite_prix(self.main_content_frame, self)

Ou si vous utilisez un système de navigation par boutons :

self.activite_prix_button = ctk.CTkButton(
    self.sidebar_frame,
    text="Activités et Prix",
    command=self.show_activite_prix_page
)
"""

if __name__ == "__main__":
    # Test standalone (pour le développement)
    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")

    try:
        # Créer une fenêtre de test
        test_root = ctk.CTk()
        test_root.title("Test - Activités et Prix")
        test_root.geometry("1200x800")

        # Créer la page dans la fenêtre de test
        page = PageActivitePrix(test_root)
        page.pack(fill="both", expand=True, padx=10, pady=10)

        # Lancer la boucle principale
        test_root.mainloop()
        
    except Exception as e:
        print(f"Erreur lors du lancement du test : {e}")