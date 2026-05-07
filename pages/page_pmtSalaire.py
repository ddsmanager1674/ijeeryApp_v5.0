import customtkinter as ctk
import tkinter.messagebox as messagebox
from datetime import datetime
import psycopg2
import pandas as pd
from reportlab.lib.pagesizes import A5, landscape, letter
from reportlab.pdfgen import canvas
import os
import subprocess
from decimal import Decimal, InvalidOperation 
import json
import sys
from resource_utils import get_config_path, safe_file_read


# Configuration du chemin pour les imports
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
        try:
            config_path = get_config_path('config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config['database']
        except Exception as e:
            print(f"Erreur config: {e}")
            return None

    def connect(self):
        if self.db_params is None: return False
        try:
            self.conn = psycopg2.connect(**self.db_params)
            self.cursor = self.conn.cursor()
            return True
        except Exception as e:
            print(f"Erreur connexion: {e}")
            return False

    def get_connection(self):
        if self.conn is None or self.conn.closed:
            if self.connect(): return self.conn
        return self.conn

db_manager = DatabaseManager()
conn = db_manager.get_connection()

class PageValidationSalaire(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.conn = conn
        self.cursor = conn.cursor() if conn else None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1) 

        # --- Interface ---
        self.label_mois = ctk.CTkLabel(self, text="Choisir le mois :")
        self.label_mois.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.mois_combobox = ctk.CTkComboBox(self, values=[
            "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
            "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
        self.mois_combobox.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.mois_combobox.set(datetime.now().strftime("%B")) 

        self.btn_afficher = ctk.CTkButton(self, text="Afficher", fg_color="#2ecc71", command=self.afficher_donnees_combinees)
        self.btn_afficher.grid(row=0, column=2, padx=10, sticky="ew")

        self.btn_excel = ctk.CTkButton(self, text="Etat Excel", command=self.exporter_excel)
        self.btn_excel.grid(row=0, column=3, padx=10, sticky="ew")

        self.btn_pdf_global = ctk.CTkButton(self, text="Etat PDF", command=self.exporter_pdf_global)
        self.btn_pdf_global.grid(row=0, column=4, padx=10, sticky="ew")

        self.btn_pdf_individual_merged = ctk.CTkButton(self, text="Fiches de Paie", command=self.exporter_pdf_fiches_groupees)
        self.btn_pdf_individual_merged.grid(row=0, column=5, padx=10, sticky="ew")

        self.headers = ["Nom", "Prénom", "SB", "Taux Hor.", "Tot. Heure", "Mt. Heure", "Salaire Brut", "Avance 15e", "Avance Spéc.", "Net à Payer"]
        self.current_export_data = [] 
        self.info_ecole = self.recuperer_info_societe()

        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.grid(row=1, column=0, columnspan=6, padx=10, pady=10, sticky="nsew") 
        self.label_count = ctk.CTkLabel(self, text="Enregistrements: 0")
        self.label_count.grid(row=2, column=0, columnspan=6, sticky="w", padx=10)

    def _to_decimal(self, value):
        try: return Decimal(str(value)) if value else Decimal(0)
        except: return Decimal(0)

    def recuperer_info_societe(self):
        """Récupère les informations de l'entreprise"""
        query = "SELECT nomsociete, adressesociete, villesociete, contactsociete FROM tb_infosociete LIMIT 1;"
        try:
            self.cursor.execute(query)
            res = self.cursor.fetchone()
            if res:
                return {"nom": res[0], "adresse": res[1], "ville": res[2], "contact": res[3]}
            return {}
        except Exception as e:
            print(f"Erreur SQL Infos: {e}")
            return {}

    def recuperer_donnees_salaire_base(self, mois):
        year = datetime.now().year
        start_date = f"{year}-{mois:02d}-01"
        query = """
        SELECT p.id, p.nom, p.prenom, COALESCE(sb.montant, 0),
               COALESCE((SELECT SUM(mtpaye) FROM tb_avancepers WHERE idpers = p.id AND EXTRACT(MONTH FROM datepmt) = %s), 0),
               COALESCE((SELECT SUM(mtpaye/nbremboursement) FROM tb_avancespecpers WHERE idpers = p.id AND %s BETWEEN datepmt AND datepmt + (nbremboursement * INTERVAL '1 month')), 0)
        FROM tb_personnel p
        LEFT JOIN tb_salairebasepers sb ON p.id = sb.idpers;
        """
        self.cursor.execute(query, (mois, start_date))
        return {r[0]: {"nom": r[1], "prenom": r[2], "sb": self._to_decimal(r[3]), "av15": self._to_decimal(r[4]), "avs": self._to_decimal(r[5])} for r in self.cursor.fetchall()}

    def recuperer_donnees_salaire_horaire(self, mois):
        query = """
        SELECT p.id, COALESCE(t.tauxhoraire, 0), COALESCE(SUM(pr.nbheure), 0)
        FROM tb_personnel p
        LEFT JOIN tb_tauxhoraire t ON t.idpers = p.id
        LEFT JOIN tb_presencepers pr ON pr.idpers = p.id AND EXTRACT(MONTH FROM pr.date) = %s
        GROUP BY p.id, t.tauxhoraire;
        """
        self.cursor.execute(query, (mois,))
        return {r[0]: {"taux": self._to_decimal(r[1]), "heures": self._to_decimal(r[2])} for r in self.cursor.fetchall()}

    def afficher_donnees_combinees(self):
        mois_str = self.mois_combobox.get()
        mois_idx = self.mois_combobox.cget("values").index(mois_str) + 1
        
        for w in self.scroll_frame.winfo_children(): w.destroy()
        
        data_sb = self.recuperer_donnees_salaire_base(mois_idx)
        data_h = self.recuperer_donnees_salaire_horaire(mois_idx)
        self.current_export_data = []

        for idp in data_sb:
            sb = data_sb[idp]['sb']
            tx = data_h.get(idp, {}).get('taux', 0)
            hrs = data_h.get(idp, {}).get('heures', 0)
            mth = tx * hrs
            brut = sb + mth
            net = brut - data_sb[idp]['av15'] - data_sb[idp]['avs']

            if brut > 0:
                self.current_export_data.append((
                    data_sb[idp]['nom'], data_sb[idp]['prenom'], float(sb), float(tx), 
                    float(hrs), float(mth), float(brut), float(data_sb[idp]['av15']), 
                    float(data_sb[idp]['avs']), float(net)
                ))
                
                f = ctk.CTkFrame(self.scroll_frame)
                f.pack(fill="x", pady=2)
                ctk.CTkLabel(f, text=f"{data_sb[idp]['nom']} {data_sb[idp]['prenom']} | Net: {net:,.0f} Ar").pack(side="left", padx=10)

        self.label_count.configure(text=f"Nombre d'enregistrements: {len(self.current_export_data)}")

    def exporter_pdf_global(self):
        """Génère l'état global avec les infos société"""
        if not self.current_export_data: return
        
        mois = self.mois_combobox.get()
        info = self.info_ecole
        path = os.path.join(os.path.expanduser("~"), "Desktop", f"Etat_Salaires_{mois}.pdf")
        
        c = canvas.Canvas(path, pagesize=landscape(letter))
        
        # En-tête
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(400, 560, info.get("nom", "SOCIETE").upper())
        c.setFont("Helvetica", 10)
        c.drawCentredString(400, 545, f"{info.get('adresse', '')} - {info.get('ville', '')} | Tel: {info.get('contact', '')}")
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(400, 520, f"ETAT DE SALAIRE - MOIS DE : {mois.upper()}")
        
        # Table Headers
        x_pts = [30, 110, 200, 260, 320, 380, 450, 530, 610, 700]
        y = 490
        c.setFont("Helvetica-Bold", 9)
        for i, h in enumerate(self.headers): c.drawString(x_pts[i], y, h)
        
        # Data
        c.setFont("Helvetica", 8)
        y -= 20
        for row in self.current_export_data:
            for i, val in enumerate(row):
                c.drawString(x_pts[i], y, f"{val}" if i < 2 else f"{val:,.0f}")
            y -= 15
            if y < 50: c.showPage(); y = 550

        c.save()
        subprocess.Popen([path], shell=True)

    def exporter_pdf_fiches_groupees(self):
        """Génère les fiches individuelles avec la mention du mois"""
        if not self.current_export_data: return
        
        mois = self.mois_combobox.get()
        info = self.info_ecole
        path = os.path.join(os.path.expanduser("~"), "Desktop", f"Fiches_Paie_{mois}.pdf")
        c = canvas.Canvas(path, pagesize=A5)

        for row in self.current_export_data:
            # En-tête société
            c.setFont("Helvetica-Bold", 12)
            c.drawCentredString(A5[0]/2, A5[1]-30, info.get("nom", "ENTREPRISE"))
            c.setFont("Helvetica", 8)
            c.drawCentredString(A5[0]/2, A5[1]-45, f"{info.get('adresse', '')} - Contact: {info.get('contact', '')}")
            
            # Titre Fiche
            c.setFont("Helvetica-Bold", 11)
            c.drawCentredString(A5[0]/2, A5[1]-70, "FICHE DE SALAIRE")
            c.drawCentredString(A5[0]/2, A5[1]-85, f"Salaire mois de : {mois.upper()}")
            
            # Infos Personnel
            c.setFont("Helvetica", 10)
            c.drawString(40, A5[1]-120, f"Nom & Prénom : {row[0]} {row[1]}")
            c.drawString(40, A5[1]-135, f"Date : {datetime.now().strftime('%d/%m/%Y')}")
            
            # Détails
            y = A5[1]-170
            details = [
                ("Salaire de Base", row[2]), ("Montant Heures", row[5]),
                ("SALAIRE BRUT", row[6]), ("Avance 15e", row[7]),
                ("Deduction Av. Spéc.", row[8]), ("NET A PAYER", row[9])
            ]
            
            for label, val in details:
                if "SALAIRE" in label or "NET" in label: c.setFont("Helvetica-Bold", 10)
                else: c.setFont("Helvetica", 10)
                c.drawString(40, y, label)
                c.drawRightString(A5[0]-40, y, f"{val:,.0f} Ar")
                y -= 20
            
            # Signatures
            c.setFont("Helvetica-Oblique", 9)
            c.drawString(40, y-40, "Signature Employeur")
            c.drawString(A5[0]-140, y-40, "Signature Employé")
            
            c.showPage()

        c.save()
        subprocess.Popen([path], shell=True)

    def exporter_excel(self):
        if not self.current_export_data: return
        df = pd.DataFrame(self.current_export_data, columns=self.headers)
        path = os.path.join(os.path.expanduser("~"), "Desktop", "Salaires.xlsx")
        df.to_excel(path, index=False)
        subprocess.Popen([path], shell=True)

if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("1000x600")
    app.title("Gestion Salaires")
    PageValidationSalaire(app).pack(fill="both", expand=True)
    app.mainloop()