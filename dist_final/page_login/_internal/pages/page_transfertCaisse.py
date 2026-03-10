# Fichier: page_transfertCaisse.py
import customtkinter as ctk
from datetime import datetime
import psycopg2
from tkinter import messagebox
import os
import json
import sys
from reportlab.lib.pagesizes import mm
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm as MM
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
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


class PageTransfertCaisse(ctk.CTkFrame):
    def __init__(self, master, db_config=None, id_user_connecte=None):
        print(f"PageTransfertCaisse.__init__ called with master={master}, db_config={db_config}")
        super().__init__(master)
        self.current_user_id = id_user_connecte
       
        self.db_manager = db_manager
        self.conn = self.db_manager.get_connection()
        
        if self.conn is None:
            messagebox.showerror("Erreur de connexion", "Impossible de se connecter à la base de données.")
            self.is_connected = False
            return
        else:
            self.cursor = self.conn.cursor()
            self.is_connected = True
        
        self.banque_data = {}   # Initialize banque data
        self.current_banque_solde = 0 # Initialize balance for the selected bank
        self.create_widgets()
        # Load data after widget creation with error handling
        self.after(100, self.load_initial_data)  # Delay loading to ensure widgets are ready

    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)

        self.label_title = ctk.CTkLabel(self, text="Transfert Banque vers Caisse", font=("Arial", 20, "bold"))
        self.label_title.grid(row=0, column=0, columnspan=2, pady=20)

        self.label_banque = ctk.CTkLabel(self, text="Sélectionner la Banque :")
        self.label_banque.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.banque_options = []
        self.selected_banque_name = ctk.StringVar(value="")
        self.selected_banque_id = None
        self.optionmenu_banque = ctk.CTkOptionMenu(self, variable=self.selected_banque_name,
                                                     values=self.banque_options,
                                                     command=self.on_banque_selected)
        self.optionmenu_banque.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        # Add a label for current bank balance, similar to cash balance in the other window
        self.label_banque_solde = ctk.CTkLabel(self, text="Solde de la banque sélectionnée : Chargement...", font=("Arial", 14, "bold"))
        self.label_banque_solde.grid(row=2, column=0, columnspan=2, pady=10)

        self.label_montant = ctk.CTkLabel(self, text="Montant du transfert :")
        self.label_montant.grid(row=3, column=0, padx=10, pady=10, sticky="w")
        self.entry_montant = ctk.CTkEntry(self, placeholder_text="Entrez le montant")
        self.entry_montant.grid(row=3, column=1, padx=10, pady=10, sticky="ew")

        self.button_transfert = ctk.CTkButton(self, text="Effectuer le Transfert", command=self.perform_transfert, fg_color="#28a745", hover_color="#218838")
        self.button_transfert.grid(row=4, column=0, columnspan=2, pady=20)

        self.label_status = ctk.CTkLabel(self, text="", text_color="green")
        self.label_status.grid(row=5, column=0, columnspan=2, pady=10)

    def load_initial_data(self):
        """Charge les données initiales après la création des widgets"""
        if not self.is_connected:
            return
            
        try:
            self.load_banques()
            if self.selected_banque_id:
                self.load_banque_balance(self.selected_banque_id)
            else:
                self.label_banque_solde.configure(text="Solde de la banque sélectionnée : N/A")
        except Exception as e:
            self.show_status(f"Erreur lors du chargement initial: {e}", "red")

    def format_montant(self, valeur):
        """Format amount with proper French formatting"""
        return f"{valeur:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def load_banques(self):
        if not self.is_connected:
            return
            
        try:
            self.cursor.execute("SELECT id_banque, nombanque FROM tb_banque ORDER BY nombanque;")
            banques = self.cursor.fetchall()

            self.banque_data = {name: id for id, name in banques}
            self.banque_options = list(self.banque_data.keys())
            if self.banque_options:
                self.optionmenu_banque.configure(values=self.banque_options)
                self.selected_banque_name.set(self.banque_options[0])
                self.on_banque_selected(self.banque_options[0])
            else:
                self.optionmenu_banque.configure(values=["Aucune banque trouvée"])
                self.selected_banque_name.set("Aucune banque trouvée")
                self.selected_banque_id = None

        except psycopg2.Error as e:
            self.show_status(f"Erreur lors du chargement des banques: {e}", "red")
            messagebox.showerror("Erreur de base de données", f"Impossible de charger les banques: {e}")

    def load_banque_balance(self, id_banque):
        """Load the balance for the selected bank"""
        if not self.is_connected:
            return
    
        try:
            # Query to calculate the balance for a specific bank
            self.cursor.execute("""
                SELECT COALESCE(SUM(CASE WHEN idtypeoperation = 1 THEN mtpaye ELSE 0 END), 0) - 
                COALESCE(SUM(CASE WHEN idtypeoperation = 2 THEN mtpaye ELSE 0 END), 0) 
                FROM (
                    SELECT idtypeoperation, mtpaye FROM tb_pmtfacture WHERE id_banque = %s
                    UNION ALL 
                    SELECT idtypeoperation, mtpaye FROM tb_pmtcom WHERE id_banque = %s
                    UNION ALL 
                    SELECT idtypeoperation, mtpaye FROM tb_encaissementbq WHERE id_banque = %s
                    UNION ALL 
                    SELECT idtypeoperation, mtpaye FROM tb_decaissementbq WHERE id_banque = %s
                    UNION ALL 
                    SELECT idtypeoperation, mtpaye FROM tb_avancepers WHERE id_banque = %s
                    UNION ALL 
                    SELECT idtypeoperation, mtpaye FROM tb_avancespecpers WHERE id_banque = %s
                    UNION ALL 
                    SELECT idtypeoperation, mtpaye FROM tb_pmtsalaire WHERE id_banque = %s
                    UNION ALL 
                    SELECT idtypeoperation, mtpaye FROM tb_transfertbanque WHERE id_banque = %s
                ) AS toutes_operations_banque
            """, (id_banque, id_banque, id_banque, id_banque, id_banque, id_banque, id_banque, id_banque))
    
            result = self.cursor.fetchone()
            solde = result[0] if result and result[0] is not None else 0
            self.label_banque_solde.configure(text=f"Solde de la banque sélectionnée : {self.format_montant(solde)} Ar")
            self.current_banque_solde = solde
    
        except psycopg2.Error as e:
            messagebox.showerror("Erreur de base de données", f"Erreur lors du chargement du solde de la banque: {e}")
            self.label_banque_solde.configure(text="Solde de la banque sélectionnée : Erreur")
            self.current_banque_solde = 0

    def on_banque_selected(self, new_banque_name):
        if hasattr(self, 'banque_data') and self.banque_data:
            self.selected_banque_id = self.banque_data.get(new_banque_name)
            if self.selected_banque_id:
                self.load_banque_balance(self.selected_banque_id)
            else:
                self.label_banque_solde.configure(text="Solde de la banque sélectionnée : N/A")
                self.current_banque_solde = 0
        else:
            self.selected_banque_id = None
            self.label_banque_solde.configure(text="Solde de la banque sélectionnée : N/A")
            self.current_banque_solde = 0

    def validate_input(self):
        montant_str = self.entry_montant.get().strip()
        selected_banque_name = self.selected_banque_name.get()

        if not montant_str:
            self.show_status("Veuillez entrer un montant.", "red")
            return None
        try:
            mtpaye = float(montant_str.replace(',', '.')) # Handle French decimal separator
            if mtpaye <= 0:
                self.show_status("Le montant doit être positif.", "red")
                return None
        except ValueError:
            self.show_status("Montant invalide. Veuillez entrer un nombre.", "red")
            return None
        
        if not self.selected_banque_id or selected_banque_name == "Aucune banque trouvée":
            self.show_status("Veuillez sélectionner une banque valide.", "red")
            return None

        if mtpaye > self.current_banque_solde:
            self.show_status("Le montant à transférer dépasse le solde de la banque sélectionnée.", "red")
            return None

        return mtpaye

    def generer_ticket_caisse_pdf(self, reference_caisse, mtpaye, date_du_jour):
        """Génère un ticket de caisse PDF 80mm avec les informations du transfert et de la société"""
        try:
            # Récupérer les informations de la société
            self.cursor.execute("""
                SELECT nomsociete, adressesociete, villesociete, contactsociete 
                FROM tb_infosociete 
                LIMIT 1
            """)
            info_societe = self.cursor.fetchone()
            
            if not info_societe:
                messagebox.showwarning("Attention", "Aucune information de société trouvée.")
                return None
            
            nomsociete, adressesociete, villesociete, contactsociete = info_societe
            
            # Créer le dossier tickets s'il n'existe pas
            tickets_dir = os.path.join(parent_dir, "tickets_caisse")
            os.makedirs(tickets_dir, exist_ok=True)
            
            # Nom du fichier PDF
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ticket_transfert_{timestamp}.pdf"
            filepath = os.path.join(tickets_dir, filename)
            
            # Dimensions du ticket 80mm (largeur) - hauteur variable
            width = 80 * MM
            height = 200 * MM  # Hauteur initiale, sera ajustée si nécessaire
            
            # Créer le PDF
            c = canvas.Canvas(filepath, pagesize=(width, height))
            
            # Position de départ
            y_position = height - 10 * MM
            x_center = width / 2
            
            # En-tête - Nom de la société (en gras)
            c.setFont("Helvetica-Bold", 12)
            c.drawCentredString(x_center, y_position, nomsociete or "")
            y_position -= 5 * MM
            
            # Adresse et ville
            c.setFont("Helvetica", 9)
            if adressesociete:
                c.drawCentredString(x_center, y_position, adressesociete)
                y_position -= 4 * MM
            if villesociete:
                c.drawCentredString(x_center, y_position, villesociete)
                y_position -= 4 * MM
            
            # Contact
            if contactsociete:
                c.drawCentredString(x_center, y_position, f"Tel: {contactsociete}")
                y_position -= 6 * MM
            
            # Ligne de séparation
            c.line(5 * MM, y_position, width - 5 * MM, y_position)
            y_position -= 6 * MM
            
            # Titre du ticket
            c.setFont("Helvetica-Bold", 11)
            c.drawCentredString(x_center, y_position, "TICKET DE CAISSE")
            y_position -= 5 * MM
            
            c.setFont("Helvetica-Bold", 10)
            c.drawCentredString(x_center, y_position, "Transfert Banque vers Caisse")
            y_position -= 6 * MM
            
            # Ligne de séparation
            c.line(5 * MM, y_position, width - 5 * MM, y_position)
            y_position -= 6 * MM
            
            # Date
            c.setFont("Helvetica", 9)
            date_formatee = datetime.strptime(date_du_jour, "%Y-%m-%d").strftime("%d/%m/%Y")
            heure_actuelle = datetime.now().strftime("%H:%M:%S")
            c.drawString(5 * MM, y_position, f"Date: {date_formatee}")
            y_position -= 4 * MM
            c.drawString(5 * MM, y_position, f"Heure: {heure_actuelle}")
            y_position -= 5 * MM
            
            # Référence
            c.setFont("Helvetica-Bold", 8)
            c.drawString(5 * MM, y_position, f"Reference: {reference_caisse}")
            y_position -= 6 * MM
            
            # Ligne de séparation
            c.line(5 * MM, y_position, width - 5 * MM, y_position)
            y_position -= 6 * MM
            
            # Montant (en gros et centré)
            c.setFont("Helvetica-Bold", 14)
            c.drawCentredString(x_center, y_position, "MONTANT")
            y_position -= 6 * MM
            
            c.setFont("Helvetica-Bold", 16)
            montant_formate = self.format_montant(mtpaye)
            c.drawCentredString(x_center, y_position, f"{montant_formate} Ar")
            y_position -= 8 * MM
            
            # Ligne de séparation
            c.line(5 * MM, y_position, width - 5 * MM, y_position)
            y_position -= 6 * MM
            
            # Pied de page
            c.setFont("Helvetica-Oblique", 8)
            c.drawCentredString(x_center, y_position, "Merci pour votre confiance")
            y_position -= 4 * MM
            c.drawCentredString(x_center, y_position, "Conservez ce ticket")
            
            # Sauvegarder le PDF
            c.save()
            
            return filepath
            
        except psycopg2.Error as e:
            messagebox.showerror("Erreur de base de données", f"Erreur lors de la génération du ticket: {e}")
            return None
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la génération du ticket PDF: {e}")
            return None

    def perform_transfert(self):
        if not self.is_connected:
            self.show_status("Pas de connexion à la base de données.", "red")
            return
            
        mtpaye = self.validate_input()
        if mtpaye is None:
            return

        selected_banque_name = self.selected_banque_name.get()
        date_du_jour = datetime.now().strftime("%Y-%m-%d")
        reference_prefix = datetime.now().strftime("%Y%m%d%H%M%S")

        reference_caisse = f"TRA-DE-BQ-VERS-CAISSE-{reference_prefix}"
        observation_caisse = f"TRANSFERT CAISSE DE {selected_banque_name}"
        typeoperation_caisse = "1"
        id_banque_caisse = None 

        reference_banque = f"TRA-BQ-VERS-CAISSE-{reference_prefix}"
        observation_banque = f"TRANSFERT BANQUE VERS CAISSE"
        typeoperation_banque = "2"
        id_banque_banque = self.selected_banque_id 

        try:
            self.cursor.execute(
                "INSERT INTO tb_transfertcaisse (datepmt, refpmt, mtpaye, idtypeoperation, id_banque, observation, idmode, iduser) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);",
                (date_du_jour, reference_caisse, mtpaye, typeoperation_caisse, id_banque_caisse, observation_caisse, "1", self.current_user_id)
            )

            self.cursor.execute(
                "INSERT INTO tb_transfertbanque (datepmt, refpmt, mtpaye, idtypeoperation, id_banque, observation, idmode, iduser) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);",
                (date_du_jour, reference_banque, mtpaye, typeoperation_banque, id_banque_banque, observation_banque, "1", self.current_user_id)
            )

            self.conn.commit()
            
            # Générer le ticket de caisse PDF
            pdf_path = self.generer_ticket_caisse_pdf(reference_caisse, mtpaye, date_du_jour)
            
            if pdf_path:
                self.show_status(f"Transfert effectué avec succès ! Ticket généré: {os.path.basename(pdf_path)}", "green")
                # Ouvrir le PDF automatiquement (optionnel)
                try:
                    if sys.platform == "win32":
                        os.startfile(pdf_path)
                    elif sys.platform == "darwin":
                        os.system(f"open '{pdf_path}'")
                    else:
                        os.system(f"xdg-open '{pdf_path}'")
                except Exception as e:
                    print(f"Impossible d'ouvrir le PDF: {e}")
            else:
                self.show_status("Transfert effectué mais erreur lors de la génération du ticket.", "orange")
            
            self.entry_montant.delete(0, ctk.END)
            self.load_banque_balance(self.selected_banque_id) # Refresh bank balance

            if hasattr(self.master, 'event_generate'):
                self.master.after_idle(self.master.event_generate, "<<TransfertComplete>>")

        except psycopg2.Error as e:
            if self.conn:
                self.conn.rollback()
            error_msg = f"Erreur lors du transfert: {e}"
            self.show_status(error_msg, "red")
            messagebox.showerror("Erreur de base de données", error_msg)

    def show_status(self, message, color):
        self.label_status.configure(text=message, text_color=color)
        self.after(5000, lambda: self.label_status.configure(text=""))

    def refresh_data(self, event=None):
        """Refresh all data (useful for external calls)"""
        self.load_banques()
        if self.selected_banque_id:
            self.load_banque_balance(self.selected_banque_id)

# Exemple d'utilisation (pour tester cette classe seule)
if __name__ == "__main__":
    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")
    app = ctk.CTk()
    app.geometry("600x450")
    app.title("Transfert Banque vers Caisse")
    
    # db_config n'est plus nécessaire ici car il est géré par DatabaseManager
    transfer_page = PageTransfertCaisse(app)
    transfer_page.pack(fill="both", expand=True)
    app.mainloop()