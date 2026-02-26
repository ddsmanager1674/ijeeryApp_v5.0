import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import date
import psycopg2
from datetime import date, datetime
import os
from pathlib import Path
from num2words import num2words
from fpdf import FPDF 
import json

class DatabaseManager:
    def __init__(self):
        self.db_params = self._load_db_config()
        self.conn = None

    def _load_db_config(self):
        """Loads database configuration from 'config.json'."""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
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
    
    def get_connection(self):
        """Establishes a new database connection."""
        if self.db_params is None:
            print("Cannot connect: Database configuration is missing.")
            return None
        
        try:
            self.conn = psycopg2.connect(
                host=self.db_params['host'],
                user=self.db_params['user'],
                password=self.db_params['password'],
                database=self.db_params['database'],
                port=self.db_params['port']
            )
            print("Connection to the database successful!")
            return self.conn
        except psycopg2.OperationalError as e:
            print(f"Error connecting to the database: {e}")
            self.conn = None
            return None

def page_pmtActivite(master, matricule="", nom="", prenom="", montant_droit=None, treeview_banque=None, treeview_caisse=None, idactivite=None, designation_annee=None, db_conn=None):
    
    def get_activity_designation(id):
        if db_conn:
            try:
                if id is None:
                    print("Debug: idactivite est None, ne peut pas récupérer la désignation.")
                    return "ACTIVITE"
                
                print(f"Debug: Récupération de la désignation pour idactivite = {id}")
                cur = db_conn.cursor()
                cur.execute("SELECT designationactivite FROM tb_activite WHERE id = %s", (id,))
                result = cur.fetchone()
                cur.close()
                if result:
                    return result[0]
                return "ACTIVITE"
            except psycopg2.Error as e:
                print(f"Erreur lors de la récupération de la désignation de l'activité: {e}")
                return "ACTIVITE"
        return "ACTIVITE"

    def get_school_info():
        """Récupère les informations de l'école depuis tb_infoecole"""
        if db_conn:
            try:
                cur = db_conn.cursor()
                cur.execute("SELECT nomecole, contactecole, region, commune FROM tb_infoecole LIMIT 1")
                result = cur.fetchone()
                cur.close()
                if result:
                    return {
                        'nomecole': result[0],
                        'contactecole': result[1],
                        'region': result[2],
                        'commune': result[3]
                    }
                return None
            except psycopg2.Error as e:
                print(f"Erreur lors de la récupération des infos école: {e}")
                return None
        return None    
    
    def number_to_words(number):
        """Convertit un nombre en lettres en français"""
        try:
            return num2words(int(number), lang='fr')
        except:
            return ""

    def save_pdf_receipt(payment_data):
        """Enregistre le ticket de caisse au format PDF et l'ouvre"""
        try:
            school_info = get_school_info()
            if not school_info:
                messagebox.showerror("Erreur", "Impossible de récupérer les informations de l'école")
                return

            # Création du dossier "Tickets" sur le bureau s'il n'existe pas
            desktop = Path(os.path.join(os.environ["USERPROFILE"], "Desktop"))
            tickets_dir = desktop / "Tickets"
            tickets_dir.mkdir(parents=True, exist_ok=True)

            # Création du PDF
            pdf = FPDF('P', 'mm', (80, 200))
            pdf.add_page()
            pdf.set_font('Arial', '', 10)
            
            # En-tête
            pdf.cell(w=0, h=5, txt=school_info['nomecole'], ln=1, align='C')
            pdf.cell(w=0, h=5, txt=school_info['contactecole'], ln=1, align='C')
            pdf.cell(w=0, h=5, txt=f"{school_info['region']} - {school_info['commune']}", ln=1, align='C')
            pdf.ln(5)

            # Informations du paiement
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(w=0, h=5, txt="Reçu de paiement", ln=1, align='C')
            pdf.ln(5)
            
            pdf.set_font('Arial', '', 9)
            pdf.cell(w=0, h=5, txt=f"Année Scolaire: {payment_data['designationannee']}", ln=1)
            pdf.cell(w=0, h=5, txt=f"Date: {payment_data['datepmt']}", ln=1)
            pdf.cell(w=0, h=5, txt=f"Référence: {payment_data['reference']}", ln=1)
            pdf.multi_cell(w=0, h=5, txt=f"Observation: {payment_data['observation']}")
            pdf.ln(5)

            pdf.set_font('Arial', 'B', 12)
            pdf.cell(w=0, h=5, txt=f"Montant: {payment_data['mtpaye']:,.0f} Ar", ln=1, align='C')
            pdf.ln(5)

            pdf.set_font('Arial', '', 9)
            amount_in_words = number_to_words(payment_data['mtpaye'])
            pdf.multi_cell(w=0, h=5, txt=f"Montant en lettres:\n{amount_in_words} Ariary")
            pdf.ln(10)

            # Signature
            pdf.cell(w=30, h=5, txt="Le Client", align='L')
            pdf.cell(w=30, h=5, txt="L'Administration", align='R')

            # Nom du fichier
            file_name = f"TICKET - {payment_data['reference']}.pdf"
            file_path = tickets_dir / file_name

            # Sauvegarde du PDF
            pdf.output(file_path)
            
            messagebox.showinfo("Succès", f"Ticket de caisse enregistré avec succès :\n{file_path}")
            
            # Ouvrir le fichier pour l'utilisateur
            os.startfile(file_path)

        except Exception as e:
            messagebox.showerror("Erreur de sauvegarde", f"Erreur lors de la création du PDF : {str(e)}")


    def load_months():
        if db_conn:
            cur = db_conn.cursor()
            cur.execute("SELECT designation FROM tb_moisscolaire")
            months = [row[0] for row in cur.fetchall()]
            mois_cb['values'] = months
            cur.close()
    
    def load_banks():
        if db_conn:
            cur = db_conn.cursor()
            cur.execute("SELECT nombanque FROM tb_banque") 
            banks = [row[0] for row in cur.fetchall()]
            banks.insert(0, "Caisse") 
            bank_cb['values'] = banks
            cur.close()

    def get_bank_id(bank_name):
        if bank_name == "Caisse":
            return None 
        if db_conn:
            cur = db_conn.cursor()
            cur.execute("SELECT id_banque FROM tb_banque WHERE nombanque = %s", (bank_name,)) 
            bank_id = cur.fetchone()
            cur.close()
            return bank_id[0] if bank_id else None
        return None

    def generate_reference():
        now = datetime.now()
        return f"ACT-{now.strftime('%Y%m%d%H%M%S')}"

    def get_activity_designation(id):
        if db_conn:
            try:
                if id is None:
                    return "ACTIVITE"
                cur = db_conn.cursor()
                cur.execute("SELECT designationactivite FROM tb_activite WHERE id = %s", (id,))
                result = cur.fetchone()
                cur.close()
                if result:
                    return result[0]
                return "ACTIVITE"
            except psycopg2.Error as e:
                print(f"Erreur lors de la récupération de la désignation de l'activité: {e}")
                return "ACTIVITE"
        return "ACTIVITE"
    
    def generate_observation(nom, prenom, idactivite):
        today = date.today().strftime("%d%m%Y")
        designation = get_activity_designation(idactivite)
        return f"{designation} - {nom.upper()} {prenom.capitalize()} - {today}"


    def add_payment():
        if db_conn:
            try:
                cur = db_conn.cursor()
                selected_bank_name = bank_cb.get()
                id_banque = get_bank_id(selected_bank_name) 

                matricule_val = matricule_var.get()
                date_val = date_var.get()
                mt_paye_val = mt_paye_var.get()
                mois_val = mois_cb.get()
                annee_val = annee_var.get()
                reference_val = reference_var.get()
                observation_val = observation_var.get()
                
                try:
                    mt_paye_val_num = float(mt_paye_val) 
                except ValueError:
                    messagebox.showerror("Erreur de saisie", "Le montant payé doit être un nombre valide.")
                    return

                type_operation_val = "recette" 

                cur.execute("""
                    INSERT INTO tb_pmtactivite (matricule, datepmt, mtpaye, designationmois, designationannee, typeoperation, id_banque, reference, observation, idactivite)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (matricule_val, date_val, mt_paye_val_num, mois_val, annee_val,
                      type_operation_val, id_banque, reference_val, observation_val, idactivite))
                
                db_conn.commit()
                messagebox.showinfo("Succès", "Paiement ajouté avec succès.")

                payment_data = {
                    'designationannee': annee_val,
                    'datepmt': date_val,
                    'observation': observation_val,
                    'reference': reference_val,
                    'mtpaye': mt_paye_val_num
                }
                
                save_pdf_receipt(payment_data)
                
                clear_fields() 
            except ValueError as ve:
                messagebox.showerror("Erreur de saisie", str(ve))
            except psycopg2.Error as e:
                print(f"PostgreSQL Error Details: {e.pgcode} - {e.pgerror}")
                messagebox.showerror("Erreur", f"Erreur lors de l'ajout : {e}")
            finally:
                if 'cur' in locals() and cur:
                    cur.close()

    def clear_fields():
        matricule_var.set(matricule)
        nom_var.set(nom)
        prenom_var.set(prenom)
        date_var.set(str(date.today()))
        mt_paye_var.set(str(montant_droit) if montant_droit is not None else "") 
        mois_courant = date.today().strftime("%B")
        mois_courant_fr = mois_fr.get(mois_courant, mois_courant)
        mois_cb.set(mois_courant_fr) 
        bank_cb.set("Caisse")
        
        reference_var.set(generate_reference())
        observation_var.set(generate_observation(nom_var.get(), prenom_var.get(), idactivite))

    frame = ctk.CTkFrame(master, fg_color="transparent")
    frame.pack(fill="both", expand=True) 

    matricule_var = ctk.StringVar(value=matricule)
    nom_var = ctk.StringVar(value=nom)
    prenom_var = ctk.StringVar(value=prenom)
    date_var = ctk.StringVar(value=str(date.today()))
    mt_paye_var = ctk.StringVar(value=str(montant_droit) if montant_droit is not None else "")
    annee_var = ctk.StringVar(value=designation_annee if designation_annee else "") 
    bank_var = ctk.StringVar() 
    reference_var = ctk.StringVar()
    observation_var = ctk.StringVar()

    mois_fr = {
        "January": "Janvier", "February": "Février", "March": "Mars", "April": "Avril",
        "May": "Mai", "June": "Juin", "July": "Juillet", "August": "Août",
        "September": "Septembre", "October": "Octobre", "November": "Novembre", "December": "Décembre"
    }
    mois_courant = date.today().strftime("%B")
    mois_courant_fr = mois_fr.get(mois_courant, mois_courant)

    
    frame.grid_columnconfigure(1, weight=1) 
    
    ctk.CTkLabel(frame, text="Matricule :").grid(row=0, column=0, sticky="w", padx=10, pady=5)
    ctk.CTkEntry(frame, textvariable=matricule_var, state="readonly").grid(row=0, column=1, sticky="ew", padx=10, pady=5)

    ctk.CTkLabel(frame, text="Nom :").grid(row=1, column=0, sticky="w", padx=10, pady=5)
    ctk.CTkEntry(frame, textvariable=nom_var, state="readonly").grid(row=1, column=1, sticky="ew", padx=10, pady=5)

    ctk.CTkLabel(frame, text="Prénom :").grid(row=2, column=0, sticky="w", padx=10, pady=5)
    ctk.CTkEntry(frame, textvariable=prenom_var, state="readonly").grid(row=2, column=1, sticky="ew", padx=10, pady=5)

    ctk.CTkLabel(frame, text="Date Paiement :").grid(row=3, column=0, sticky="w", padx=10, pady=5)
    ctk.CTkEntry(frame, textvariable=date_var, state="readonly").grid(row=3, column=1, sticky="ew", padx=10, pady=5)

    ctk.CTkLabel(frame, text="Montant Payé :").grid(row=4, column=0, sticky="w", padx=10, pady=5)
    ctk.CTkEntry(frame, textvariable=mt_paye_var).grid(row=4, column=1, sticky="ew", padx=10, pady=5)

    ctk.CTkLabel(frame, text="Mois Scolaire :").grid(row=5, column=0, sticky="w", padx=10, pady=5)
    mois_cb = ttk.Combobox(frame)
    mois_cb.grid(row=5, column=1, sticky="ew", padx=10, pady=5)
    mois_cb.set(mois_courant_fr) 

    ctk.CTkLabel(frame, text="Année Scolaire :").grid(row=6, column=0, sticky="w", padx=10, pady=5)
    ctk.CTkEntry(frame, textvariable=annee_var, state="readonly").grid(row=6, column=1, sticky="ew", padx=10, pady=5)

    ctk.CTkLabel(frame, text="Banque/Caisse :").grid(row=7, column=0, sticky="w", padx=10, pady=5)
    bank_cb = ttk.Combobox(frame, textvariable=bank_var)
    bank_cb.grid(row=7, column=1, sticky="ew", padx=10, pady=5)
    bank_cb.set("Caisse") 

    ctk.CTkLabel(frame, text="Référence :").grid(row=8, column=0, sticky="w", padx=10, pady=5)
    ctk.CTkEntry(frame, textvariable=reference_var, state="readonly").grid(row=8, column=1, sticky="ew", padx=10, pady=5)

    ctk.CTkLabel(frame, text="Observation :").grid(row=9, column=0, sticky="w", padx=10, pady=5)
    observation_entry = ctk.CTkEntry(frame, textvariable=observation_var, state="readonly")
    observation_entry.grid(row=9, column=1, sticky="ew", padx=10, pady=5)


    btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
    btn_frame.grid(row=10, column=0, columnspan=2, pady=10)

    ctk.CTkButton(btn_frame, text="Ajouter", command=add_payment).pack(side="left", padx=5)
    ctk.CTkButton(btn_frame, text="Modifier").pack(side="left", padx=5)
    ctk.CTkButton(btn_frame, text="Supprimer").pack(side="left", padx=5)

    load_months() 
    load_banks() 
    clear_fields() 

    return frame

if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("400x600") 
    app.title("Saisie d'Activité (Test)")

    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")
    
    db_manager = DatabaseManager()
    db_conn = db_manager.get_connection()
    if db_conn:
        ecolage_page = page_pmtActivite(app, matricule="STU001", nom="RAKOTO", prenom="Jean", montant_droit=75000.00,
                                     treeview_banque=None, treeview_caisse=None, db_conn=db_conn)
        ecolage_page.pack(fill="both", expand=True)
        app.mainloop()
        db_conn.close()
    else:
        messagebox.showerror("Erreur de connexion", "Impossible de se connecter à la base de données. L'application va se fermer.")
        app.destroy()