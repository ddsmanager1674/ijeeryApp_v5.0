import customtkinter as ctk
from tkinter import messagebox
from tkcalendar import Calendar
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

class PageAbsenceMJ(ctk.CTkToplevel):
    def __init__(self, master=None, conn=None, cursor=None):
        """
        Initialise la fenêtre de mise à jour des absences.
        
        Args:
            master: La fenêtre parent
            conn: Connexion à la base de données (optionnel, sinon créée automatiquement)
            cursor: Curseur de la base de données (optionnel, sinon créé automatiquement)
        """
        super().__init__(master)
        self.title("Enregistrement des Absences")
        self.geometry("1000x700")      

        # Utiliser la connexion fournie ou en créer une nouvelle via connect_db
        if conn and cursor:
            self.conn = conn
            self.cursor = cursor
            self.own_connection = False  # Indique que la connexion est externe
        else:
            self.conn = self.connect_db()
            if self.conn:
                self.cursor = self.conn.cursor()
                self.own_connection = True
            else:
                self.cursor = None
                self.own_connection = True
                # Le message d'erreur est déjà géré dans connect_db

        # Stocker le mapping fonction_designation -> fonction_id
        self.fonction_map = {}
        if self.conn:
            self.load_fonction()

        # Cadre supérieur pour les filtres et la recherche
        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.pack(pady=20, padx=20, fill="x")

        # Champ de date
        self.date_label = ctk.CTkLabel(self.top_frame, text="Date:")
        self.date_label.pack(side="left", padx=5)

        self.selected_date_var = ctk.StringVar(value=datetime.now().strftime('%d/%m/%Y'))
        self.date_entry = ctk.CTkEntry(self.top_frame, textvariable=self.selected_date_var, state="readonly", width=120)
        self.date_entry.pack(side="left", padx=5)

        self.calendar_button = ctk.CTkButton(self.top_frame, text="Choisir Date", command=self.open_calendar_dialog)
        self.calendar_button.pack(side="left", padx=5)

        # Combobox pour la fonction
        self.serie_label = ctk.CTkLabel(self.top_frame, text="Fonction:")
        self.serie_label.pack(side="left", padx=15)
        self.serie_combobox = ctk.CTkComboBox(self.top_frame,
                                              values=list(self.fonction_map.keys()),
                                              command=self.on_fonction_selected)
        self.serie_combobox.set("Toutes les fonctions")
        self.serie_combobox.pack(side="left", padx=5)

        # Zone de recherche
        self.search_label = ctk.CTkLabel(self.top_frame, text="Recherche (N° / Nom):")
        self.search_label.pack(side="left", padx=15)
        self.search_entry = ctk.CTkEntry(self.top_frame, placeholder_text="Rechercher Personnel...")
        self.search_entry.pack(side="left", padx=5, expand=True, fill="x")
        self.search_entry.bind("<Return>", self.perform_search)

        # Cadre pour le tableau des personnels
        self.table_frame = ctk.CTkFrame(self)
        self.table_frame.pack(pady=20, padx=20, fill="both", expand=True)

        self.personnel_table_container = ctk.CTkScrollableFrame(self.table_frame)
        self.personnel_table_container.pack(fill="both", expand=True)

        self.table_headers = ["N°", "Nom et Prénom", "Heure d'absence"]
        self.personnel_rows_data = []

        self.create_table_headers()
        if self.conn:
            self.load_personnel()

        # Bouton Enregistrer
        self.save_button = ctk.CTkButton(self, text="Enregistrer les absences", command=self.save_absences)
        self.save_button.pack(pady=20)

        # Protocole de fermeture
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def connect_db(self):
        """Établit la connexion à la base de données à partir du fichier config.json"""
        try:
            # Recherche du fichier config.json dans le répertoire parent ou courant
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
                port=db_config['port']  
            )
            return conn
        except Exception as err:
            messagebox.showerror("Erreur de connexion", f"Détails : {err}")
            return None

    def load_fonction(self):
        """Charge les désignations et IDs des fonctions depuis tb_fonction."""
        if not self.conn:
            return
        try:
            self.cursor.execute("SELECT idfonction, designationfonction FROM tb_fonction ORDER BY designationfonction")
            self.fonction_map = {"Toutes les fonctions": None}
            for row in self.cursor.fetchall():
                self.fonction_map[row[1]] = row[0]
        except Exception as e:
            messagebox.showerror("Erreur SQL", f"Erreur lors de la récupération des fonctions: {e}")

    def on_fonction_selected(self, selected_personnel_designation):
        """Appelée quand une fonction est sélectionnée dans le combobox."""
        self.search_entry.delete(0, ctk.END)
        self.load_personnel()
    
    def open_calendar_dialog(self):
        """Ouvre une nouvelle fenêtre Toplevel avec le calendrier."""
        def set_date():
            selected_date = cal.get_date()
            self.selected_date_var.set(selected_date)
            top.destroy()

        top = ctk.CTkToplevel(self)
        top.title("Sélectionner une date")
        top.transient(self)
        top.grab_set()

        current_date_str = self.selected_date_var.get()
        try:
            current_date_obj = datetime.strptime(current_date_str, '%d/%m/%Y').date()
        except ValueError:
            current_date_obj = datetime.now().date()

        cal = Calendar(top, selectmode='day',
                       date_pattern='dd/mm/yyyy',
                       headersbackground='#007bff',
                       normalbackground='white',
                       weekendbackground='lightgray',
                       othermonthbackground='lightgray',
                       selectbackground='#0056b3',
                       selectforeground='white',
                       font=("Arial", 12),
                       year=current_date_obj.year,
                       month=current_date_obj.month,
                       day=current_date_obj.day)
        cal.pack(pady=20, padx=20)

        select_button = ctk.CTkButton(top, text="Valider", command=set_date)
        select_button.pack(pady=10)

        top.wait_window()

    def create_table_headers(self):
        """Crée les en-têtes du tableau."""
        for i, header_text in enumerate(self.table_headers):
            header_label = ctk.CTkLabel(self.personnel_table_container, text=header_text, font=("Arial", 12, "bold"))
            header_label.grid(row=0, column=i, padx=10, pady=5, sticky="w")
            self.personnel_table_container.grid_columnconfigure(i, weight=1)

    def clear_personnel_table(self):
        """Nettoie tous les widgets des lignes de personnels du tableau."""
        for row_data in self.personnel_rows_data:
            for widget in row_data['widgets']:
                widget.destroy()
        self.personnel_rows_data = []

    def load_personnel(self, search_query=""):
        """Charge et affiche les personnels dans le tableau."""
        if not self.conn:
            return
            
        self.clear_personnel_table()

        selected_serie_designation = self.serie_combobox.get()
        selected_personnel_id = self.fonction_map.get(selected_serie_designation)

        base_query = """
            SELECT
                E.id,
                E.nom,
                E.prenom,
                E.datenaissance,
                E.idfonction
            FROM
                tb_personnel E
            WHERE 1=1
        """
        params = []

        if selected_personnel_id is not None:
            base_query += " AND E.idfonction = %s"
            params.append(selected_personnel_id)

        if search_query:
            base_query += " AND (E.id::text ILIKE %s OR E.nom ILIKE %s OR E.prenom ILIKE %s)"
            params.extend([f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"])

        final_query = f"""
            WITH RankedPersonnels AS (
                {base_query}
            )
            SELECT
                ROW_NUMBER() OVER (PARTITION BY RS.idfonction ORDER BY RS.datenaissance ASC) as row_num,
                RS.id,
                RS.nom,
                RS.prenom
            FROM
                RankedPersonnels RS
            ORDER BY
                RS.idfonction, row_num;
        """

        try:
            self.cursor.execute(final_query, tuple(params))
            personnels = self.cursor.fetchall()

            for i, personnel in enumerate(personnels):
                row_num, personnel_id, nom, prenom = personnel
                current_row_idx = i + 1

                widgets_in_row = []

                num_label = ctk.CTkLabel(self.personnel_table_container, text=str(row_num))
                num_label.grid(row=current_row_idx, column=0, padx=10, pady=2, sticky="w")
                widgets_in_row.append(num_label)

                name_label = ctk.CTkLabel(self.personnel_table_container, text=f"{nom} {prenom}")
                name_label.grid(row=current_row_idx, column=1, padx=10, pady=2, sticky="w")
                widgets_in_row.append(name_label)

                absence_entry = ctk.CTkEntry(self.personnel_table_container, width=100)
                absence_entry.grid(row=current_row_idx, column=2, padx=10, pady=2, sticky="w")
                widgets_in_row.append(absence_entry)

                self.personnel_rows_data.append({'widgets': widgets_in_row, 'personnel_id': personnel_id})

        except Exception as e:
            messagebox.showerror("Erreur SQL", f"Erreur lors du chargement des personnels: {e}")

    def perform_search(self, event=None):
        """Exécute la recherche quand la touche 'Entrée' est pressée."""
        search_term = self.search_entry.get().strip()
        self.load_personnel(search_term)

    def save_absences(self):
        """Enregistre les absences dans la table tb_absence."""
        if not self.conn:
            return
            
        selected_date = self.selected_date_var.get()
        try:
            date_obj = datetime.strptime(selected_date, '%d/%m/%Y').date()
        except ValueError:
            messagebox.showerror("Erreur de date", "Format de date invalide. Veuillez sélectionner une date valide.")
            return

        absences_to_insert = []
        for row_data in self.personnel_rows_data:
            absence_entry = row_data['widgets'][2]
            personnel_id = row_data['personnel_id']

            try:
                val = absence_entry.get().replace(',', '.') # Gère les virgules
                nbre_heure_abs = float(val)
                if nbre_heure_abs > 0:
                    absences_to_insert.append((personnel_id, date_obj, "Absence", nbre_heure_abs))
            except ValueError:
                continue

        if not absences_to_insert:
            messagebox.showinfo("Information", "Aucune absence à enregistrer.")
            return

        try:
            self.cursor.executemany("""
                INSERT INTO tb_absence (idpers, date, observation, nbreheureabs)
                VALUES (%s, %s, %s, %s)
            """, absences_to_insert)
            self.conn.commit()
            messagebox.showinfo("Succès", f"{len(absences_to_insert)} absence(s) enregistrée(s) avec succès.")
            self.load_personnel()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Erreur d'enregistrement", f"Erreur lors de l'enregistrement des absences: {e}")

    def on_closing(self):
        """Ferme la connexion à la base de données avant de fermer la fenêtre."""
        # Ne fermer la connexion que si nous l'avons créée nous-mêmes
        if self.own_connection:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
        self.destroy()


if __name__ == "__main__":
    app = ctk.CTk()
    app.withdraw()

    page = PageAbsenceMJ(app)
    app.mainloop()