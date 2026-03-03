import customtkinter as ctk
from tkinter import messagebox
import psycopg2
import json
from datetime import datetime
from typing import Dict, Any, Optional
import traceback
import tempfile
import os
import subprocess
from resource_utils import get_config_path, safe_file_read


# Importation pour la génération PDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A6 # Format ticket
from reportlab.lib.units import mm

class PagePmtFrs(ctk.CTkToplevel):
    def __init__(self, master, paiement_data: Dict[str, str], id_user_connecte: int = 1):
        super().__init__(master)
        self.id_user = id_user_connecte
        
        self.master = master
        self.data = paiement_data
        self.current_user = id_user_connecte # Récupéré depuis la page_login
        
        self.id_cmd = self.data.get('id_cmd')
        self.factfrs = self.data.get('factfrs', 'N/A')
        self.refcom = self.data.get('refcom', 'N/A')
        self.montant_total_str = self.data.get('montant_total', '0,00')
        self.fournisseur = self.data.get('fournisseur', 'Fournisseur Inconnu')

        try:
            montant_nettoyé = str(self.montant_total_str).replace(' ', '').replace(',', '.')
            self.montant_total_float = float(montant_nettoyé)
        except ValueError:
            self.montant_total_float = 0.0

        # CONFIGURATION DE LA FENÊTRE
        self.title(f"Paiement Facture N° {self.factfrs}")
        self.geometry("600x500")
        self.resizable(False, False)
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self._construire_interface()
        
        self.transient(master)
        self.grab_set()
        
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.winfo_screenheight() // 2) - (500 // 2)
        self.geometry(f"+{x}+{y}")
        
        self.after(100, self._donner_focus)

    def _donner_focus(self):
        self.lift()
        self.focus_force()
        if hasattr(self, 'entry_montant'):
            self.entry_montant.focus_set()

    def on_closing(self):
        self.grab_release()
        self.destroy()

    def connect_db(self):
        try:
            with open(get_config_path('config.json')) as f:
                config = json.load(f)
                db_config = config['database']
            conn = psycopg2.connect(**db_config)
            return conn
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur de connexion : {e}")
            return None

    def charger_modes_paiement(self):
        conn = self.connect_db()
        if not conn:
            return []
        try:
            with conn: # Gère automatiquement le commit ou le rollback
                with conn.cursor() as cursor: # Fermeture automatique du curseur
                    cursor.execute("SELECT idmode, modedepaiement FROM tb_modepaiement ORDER BY idmode")
                    rows = cursor.fetchall()
                    self.liste_modes = {row[1]: row[0] for row in rows}
                    return list(self.liste_modes.keys())
        except Exception as e:
            traceback.print_exc()
            return []
        finally:
            if conn:
                conn.close()

    def _get_info_societe(self):
        """Récupère les informations de l'entreprise"""
        conn = self.connect_db()
        info = {"nom": "", "adresse": "", "ville": "", "contact": ""}
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT nomsociete, adressesociete, villesociete, contactsociete FROM tb_infosociete LIMIT 1")
                row = cursor.fetchone()
                if row:
                    info = {"nom": row[0], "adresse": row[1], "ville": row[2], "contact": row[3]}
            except:
                pass
            finally:
                conn.close()
        return info

    def valider_paiement(self):
        montant_saisi_str = self.entry_montant.get().replace(' ', '').replace(',', '.')
        nom_mode_pmt = self.option_mode_pmt.get()

        try:
            montant_saisi = float(montant_saisi_str)
        except ValueError:
            messagebox.showerror("Erreur Saisie", "Veuillez entrer un montant valide.")
            return

        if montant_saisi <= 0:
            messagebox.showwarning("Attention", "Le montant doit être supérieur à zéro.")
            return

        idmodepmt = getattr(self, 'liste_modes', {}).get(nom_mode_pmt)
        
        conn = self.connect_db()
        if not conn:
            return

        try:
            with conn: # Gestion automatique du commit
                with conn.cursor() as cursor:
                    # 1. Récupération du prochain ID pour la référence
                    cursor.execute("SELECT COALESCE(MAX(id),0)+1 FROM tb_pmtcom")
                    next_id = cursor.fetchone()[0]
                    refpmt = f"{datetime.now().year}-PMTF-{next_id:06d}"
                    
                    date_now = datetime.now()
                    observation = f"PMTF-{self.factfrs}-{self.fournisseur}-{date_now.strftime('%Y-%m-%d')}"

                    # 2. Requête incluant explicitement iduser
                    query = """
                        INSERT INTO tb_pmtcom (
                            refcom, factfrs, mtpaye, datepmt, 
                            idmode, idfrs, observation, refpmt, iduser
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    
                    # On utilise self.id_user récupéré à l'initialisation
                    params = (
                        self.refcom, 
                        self.factfrs, 
                        montant_saisi, 
                        date_now, 
                        idmodepmt, 
                        1, # ID fournisseur (à adapter si besoin)
                        observation, 
                        refpmt,
                        self.id_user # <-- Correction : La colonne iduser est ici
                    )

                    cursor.execute(query, params)

            messagebox.showinfo("Succès", f"Paiement enregistré pour l'utilisateur {self.id_user}")
            
                        
         # 2. Génération et ouverture du PDF
            self._generer_pdf_paiement(montant_saisi, nom_mode_pmt, refpmt)
            
            messagebox.showinfo("Succès", "Paiement enregistré et ticket généré.")
            self.on_closing()

        except psycopg2.Error as e:
            messagebox.showerror("Erreur DB", f"Erreur : {e}")
            traceback.print_exc()
        finally:
            if conn:
                conn.close()

    def _generer_pdf_paiement(self, montant, mode_nom, refpmt):
        """Génère un ticket PDF et l'ouvre automatiquement"""
        try:
            # Infos société
            info = self._get_info_societe()
            
            # Création fichier temporaire
            temp_dir = tempfile.gettempdir()
            pdf_path = os.path.join(temp_dir, f"Ticket_{refpmt}.pdf")
            
            # Création du PDF (Format A6 pour un ticket)
            c = canvas.Canvas(pdf_path, pagesize=A6)
            width, height = A6
            
            # --- ENTETE ---
            c.setFont("Helvetica-Bold", 12)
            c.drawCentredString(width/2, height - 20*mm, info['nom'].upper())
            c.setFont("Helvetica", 9)
            c.drawCentredString(width/2, height - 25*mm, info['adresse'])
            c.drawCentredString(width/2, height - 29*mm, f"{info['ville']} - {info['contact']}")
            
            c.line(10*mm, height - 33*mm, width - 10*mm, height - 33*mm)
            
            # --- CORPS ---
            c.setFont("Helvetica-Bold", 10)
            c.drawCentredString(width/2, height - 40*mm, "RECU DE PAIEMENT")
            
            c.setFont("Helvetica", 10)
            y = height - 50*mm
            c.drawString(15*mm, y, f"Réf Pmt: {refpmt}")
            y -= 6*mm
            c.drawString(15*mm, y, f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            y -= 6*mm
            c.drawString(15*mm, y, f"Facture: {self.factfrs}")
            y -= 6*mm
            c.drawString(15*mm, y, f"Fournisseur: {self.fournisseur}")
            
            y -= 10*mm
            c.setFont("Helvetica-Bold", 11)
            c.drawString(15*mm, y, f"MONTANT PAYE: {montant:,.2f} Ar")
            y -= 6*mm
            c.setFont("Helvetica", 10)
            c.drawString(15*mm, y, f"Mode: {mode_nom}")
            
            # --- PIED DE PAGE ---
            c.line(10*mm, 30*mm, width - 10*mm, 30*mm)
            c.setFont("Helvetica-Oblique", 9)
            c.drawString(15*mm, 20*mm, f"Etabli par: {self.current_user}")
            c.drawCentredString(width/2, 10*mm, "Merci de votre confiance !")
            
            c.save()
            
            # Ouverture automatique
            if os.name == 'nt': # Windows
                os.startfile(pdf_path)
            else: # Linux/Mac
                subprocess.run(['xdg-open', pdf_path])
                
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Erreur PDF", f"Impossible de générer le PDF : {e}")

    def _construire_interface(self):
        """Construction de l'interface (Identique à votre code original)"""
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        title_label = ctk.CTkLabel(
            main_frame, 
            text="💳 PAIEMENT FOURNISSEUR",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=("#1f538d", "#3d8bfd")
        )
        title_label.pack(pady=(0, 20))

        info_frame = ctk.CTkFrame(main_frame, fg_color=("gray90", "gray20"))
        info_frame.pack(fill="x", pady=10, padx=10)
        
        # Labels Infos
        ctk.CTkLabel(info_frame, text="Facture N°:", font=ctk.CTkFont(family="Segoe UI", weight="bold")).grid(row=0, column=0, padx=15, pady=5, sticky="w")
        ctk.CTkLabel(info_frame, text=self.refcom).grid(row=0, column=1, padx=15, pady=5, sticky="w")
        
        ctk.CTkLabel(info_frame, text="Fournisseur:", font=ctk.CTkFont(family="Segoe UI", weight="bold")).grid(row=1, column=0, padx=15, pady=5, sticky="w")
        ctk.CTkLabel(info_frame, text=self.fournisseur).grid(row=1, column=1, padx=15, pady=5, sticky="w")

        ctk.CTkLabel(info_frame, text="Montant Total:", font=ctk.CTkFont(family="Segoe UI", weight="bold")).grid(row=2, column=0, padx=15, pady=5, sticky="w")
        ctk.CTkLabel(info_frame, text=f"{self.montant_total_str} Ar", text_color="green", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")).grid(row=2, column=1, padx=15, pady=5, sticky="w")

        # Saisie
        saisie_frame = ctk.CTkFrame(main_frame)
        saisie_frame.pack(fill="x", pady=20, padx=10)

        ctk.CTkLabel(saisie_frame, text="Montant Reçu :").grid(row=0, column=0, padx=10, pady=10)
        self.entry_montant = ctk.CTkEntry(saisie_frame, width=200)
        self.entry_montant.grid(row=0, column=1, padx=10, pady=10)
        self.entry_montant.insert(0, self.montant_total_str)
        
        self.option_mode_pmt = ctk.CTkOptionMenu(saisie_frame, values=self.charger_modes_paiement(), width=200)
        self.option_mode_pmt.grid(row=1, column=1, padx=10, pady=10)

        # Boutons
        btns_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btns_frame.pack(fill="x", pady=10)

        ctk.CTkButton(btns_frame, text="Valider & Imprimer PDF", fg_color="#2e7d32", command=self.valider_paiement).pack(side="left", padx=20, expand=True)
        ctk.CTkButton(btns_frame, text="Annuler", fg_color="#d32f2f", command=self.on_closing).pack(side="left", padx=20, expand=True)