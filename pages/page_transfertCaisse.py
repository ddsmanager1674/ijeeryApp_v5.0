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
from app_theme import Colors, styled, Layout
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
            from pages.db_helper import connect_page_db
            self.conn = connect_page_db()
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
        self.configure(fg_color=Colors.BG_PAGE)
        self.current_user_id = id_user_connecte
        self.session_data = getattr(master, "session_data", None) or {"user_id": self.current_user_id}
        self._logger = AppLogger(session_data=self.session_data, fallback_user_id=self.current_user_id)
       
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
        self.selected_banque_id = None
        self._responsive_mode = None  # "wide" | "narrow"
        self.create_widgets()
        # Load data after widget creation with error handling
        self.after(100, self.load_initial_data)  # Delay loading to ensure widgets are ready

    def create_widgets(self):
        self.pack(fill="both", expand=True, padx=Layout.CARD_PADX, pady=Layout.CARD_PADY_TOP)

        self.container = styled.frame(self, color="transparent")
        self.container.pack(fill="both", expand=True)

        # --- Titre ---
        self.title_card = styled.card(self.container)
        self.title_card.pack(fill="x", pady=(0, Layout.SECTION_GAP))
        title_row = styled.frame(self.title_card, color="transparent")
        title_row.pack(fill="x", padx=Layout.CARD_PADX, pady=Layout.CARD_PADY_TOP)
        styled.label_title(title_row, text="Transfert Banque vers Caisse").pack(anchor="w")
        styled.label_muted(title_row, text="Transférer un montant depuis une banque vers la caisse.").pack(anchor="w", pady=(4, 0))

        # --- Résumé (solde banque sélectionnée) ---
        self.summary_card = styled.card(self.container)
        self.summary_card.pack(fill="x", pady=(0, Layout.SECTION_GAP))
        summary_row = styled.frame(self.summary_card, color="transparent")
        summary_row.pack(fill="x", padx=Layout.CARD_PADX, pady=Layout.CARD_PADY_TOP)
        self.label_banque_solde = styled.badge(summary_row, text="Solde de la banque sélectionnée : Chargement...", variant="info")
        self.label_banque_solde.pack(anchor="w")

        # --- Formulaire ---
        self.form_card = styled.card(self.container)
        self.form_card.pack(fill="both", expand=True)
        self.form = styled.frame(self.form_card, color="transparent")
        self.form.pack(fill="x", padx=Layout.CARD_PADX, pady=Layout.CARD_PADY_TOP)
        self.form.grid_columnconfigure(0, weight=1)
        self.form.grid_columnconfigure(1, weight=1)

        # Banque
        self.bank_block = styled.frame(self.form, color="transparent")
        self.bank_block.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        styled.label_muted(self.bank_block, text="Banque", anchor="w").pack(anchor="w", pady=(0, 4))
        self.banque_options = []
        self.combo_banque = styled.combobox(
            self.bank_block,
            values=self.banque_options,
            command=self.on_banque_selected,
            state="readonly",
            width=420,
        )
        self.combo_banque.pack(fill="x")

        # Montant
        self.amount_block = styled.frame(self.form, color="transparent")
        self.amount_block.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=(0, 12))
        styled.label_muted(self.amount_block, text="Montant du transfert", anchor="w").pack(anchor="w", pady=(0, 4))
        self.entry_montant = styled.entry(self.amount_block, placeholder="Entrez le montant")
        self.entry_montant.pack(fill="x")

        # Action
        self.action_block = styled.frame(self.form, color="transparent")
        self.action_block.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(0, 12))
        styled.label_muted(self.action_block, text="Action", anchor="w").pack(anchor="w", pady=(0, 4))
        self.button_transfert = styled.button_success(self.action_block, text="Effectuer le transfert", width=240, command=self.perform_transfert)
        self.button_transfert.pack(anchor="e", fill="x")

        # Statut
        self.status_card = styled.frame(self.container, color="transparent")
        self.status_card.pack(fill="x", pady=(Layout.SECTION_GAP, 0))
        self.label_status = styled.label(self.status_card, text="", size=12, color=Colors.SUCCESS_TEXT)
        self.label_status.pack(anchor="w")

        self.bind("<Configure>", lambda e: self._update_responsive_layout(e.width))
        self._update_responsive_layout(self.winfo_width() or 700)

    def _update_responsive_layout(self, width: int):
        mode = "narrow" if width < 620 else "wide"
        if mode == self._responsive_mode:
            return
        self._responsive_mode = mode

        if mode == "narrow":
            self.amount_block.grid(row=1, column=0, columnspan=2, sticky="ew", padx=0, pady=(0, 12))
            self.action_block.grid(row=2, column=0, columnspan=2, sticky="ew", padx=0, pady=(0, 0))
        else:
            self.amount_block.grid(row=1, column=0, columnspan=1, sticky="ew", padx=(0, 10), pady=(0, 12))
            self.action_block.grid(row=1, column=1, columnspan=1, sticky="ew", padx=(10, 0), pady=(0, 12))

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
                self.combo_banque.configure(values=self.banque_options)
                self.combo_banque.set(self.banque_options[0])
                self.on_banque_selected(self.banque_options[0])
            else:
                self.combo_banque.configure(values=["Aucune banque trouvée"])
                self.combo_banque.set("Aucune banque trouvée")
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
        selected_banque_name = self.combo_banque.get()

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

        selected_banque_name = self.combo_banque.get()
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
            try:
                self._logger.log(
                    action="Transfert Banque vers Caisse",
                    element=str(reference_caisse),
                    details=f"Transfert banque '{selected_banque_name}' -> caisse, montant={mtpaye:.0f} Ar (ref={reference_caisse})",
                    value=f"{mtpaye:.0f} Ar",
                )
            except Exception:
                pass
            
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