import customtkinter as ctk
from tkinter import messagebox
import psycopg2
import json
from datetime import datetime
import traceback
import tempfile
import os
import subprocess
from tkcalendar import DateEntry
from resource_utils import get_config_path, safe_file_read


# --- BIBLIOTHÈQUES POUR LE PDF ---
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import mm
from reportlab.lib.units import mm
try:
    from num2words import num2words
except ImportError:
    num2words = None

class PagePmtCredit(ctk.CTkToplevel):
    def __init__(self, master, paiement_data, iduser=None):
        super().__init__(master)
        
        # --- 1. CONFIGURATION DE L'AFFICHAGE (Devant et au Centre) ---
        self.attributes("-topmost", True)
        self.grab_set()
        self.focus_force()
        
        self.data = paiement_data
        self.refvente = self.data.get('refvente', 'N/A')
        
        # Conversion sécurisée du montant
        try:
            val = self.data.get('montant_total', 0.0)
            self.montant_total_float = float(val)
        except (ValueError, TypeError):
            self.montant_total_float = 0.0

        self.client_nom = self.data.get('client', 'Client Inconnu')
        self.id_client_db = self.data.get('id_client_reel')
        self.iduser = iduser if iduser is not None else 1

        self.title(f"Paiement Crédit - Facture N° {self.refvente}")
        self.geometry("500x400")
        
        # Centrer la fenêtre après un court délai
        self.after(10, self._centrer_fenetre)
        
        self._construire_interface()

    def _centrer_fenetre(self):
        """Calcule et applique la position centrale sur l'écran"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def connect_db(self):
        """Connexion standard via config.json"""
        try:
            with open(get_config_path('config.json')) as f:
                config = json.load(f)
            return psycopg2.connect(**config['database'])
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur de connexion : {e}")
            return None

    def charger_modes_paiement(self):
        """Charge les modes de paiement en EXCLUANT le mode Crédit (idmode != 4)"""
        conn = self.connect_db()
        if not conn: return ["Espèces"]
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT idmode, modedepaiement FROM tb_modepaiement WHERE idmode != 4")
            rows = cursor.fetchall()
            self.liste_modes = {row[1]: row[0] for row in rows}
            return list(self.liste_modes.keys())
        except: 
            return ["Espèces"]
        finally: 
            conn.close()

    def _construire_interface(self):
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(main_frame, text="ENREGISTRER LE PAIEMENT", 
                    font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold")).pack(pady=(0, 20))
        
        # Résumé des informations
        info_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        info_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(info_frame, text=f"Client : {self.client_nom}", font=("Arial", 12)).pack(anchor="w")
        ctk.CTkLabel(info_frame, text=f"Réf Facture : {self.refvente}", font=("Arial", 12)).pack(anchor="w")
        ctk.CTkLabel(info_frame, text=f"Reste à payer : {self.montant_total_float:,.2f} Ar", 
                    font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color="#d32f2f").pack(anchor="w", pady=5)

        # Zone de saisie
        saisie_frame = ctk.CTkFrame(main_frame)
        saisie_frame.pack(fill="x", pady=15, padx=5)
        
        ctk.CTkLabel(saisie_frame, text="Montant versé :").grid(row=0, column=0, padx=10, pady=15, sticky="w")
        self.entry_montant = ctk.CTkEntry(saisie_frame, width=200)
        self.entry_montant.grid(row=0, column=1, padx=10, pady=15)
        self.entry_montant.insert(0, str(self.montant_total_float))
        
        ctk.CTkLabel(saisie_frame, text="Mode de paiement :").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        modes = self.charger_modes_paiement()
        self.option_mode_pmt = ctk.CTkOptionMenu(saisie_frame, values=modes, width=200)
        self.option_mode_pmt.grid(row=1, column=1, padx=10, pady=10)

        # Boutons d'action
        btn_container = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_container.pack(fill="x", side="bottom", pady=10)
        
        ctk.CTkButton(btn_container, text="Confirmer", fg_color="#2e7d32", hover_color="#1b5e20",
                      command=self.valider_paiement).pack(side="left", padx=5, expand=True)
        ctk.CTkButton(btn_container, text="Annuler", fg_color="#757575", 
                      command=self.fermer_fenetre).pack(side="left", padx=5, expand=True)

    def fermer_fenetre(self):
        """Fermeture propre de la fenêtre"""
        try:
            self.grab_release()
            self.destroy()
        except:
            pass

    def valider_paiement(self):
        """Enregistre le paiement en base de données puis génère le PDF"""
        conn = None
        try:
            # 1. Récupération et nettoyage du montant saisi
            montant_str = self.entry_montant.get().replace(' ', '').replace(',', '.')
            montant_verse = float(montant_str)
            
            if montant_verse <= 0:
                messagebox.showwarning("Attention", "Le montant doit être supérieur à 0.")
                return
            
            if montant_verse > self.montant_total_float + 0.01:
                messagebox.showwarning("Attention", "Le montant versé dépasse le solde de la facture.")
                return

            # 2. Connexion
            conn = self.connect_db()
            if not conn:
                return

            cursor = conn.cursor()
            
            # Récupérer l'ID du mode de paiement sélectionné
            nom_mode = self.option_mode_pmt.get()
            id_mode = self.liste_modes.get(nom_mode)

            # Générer une référence de paiement
            cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM tb_pmtcredit")
            next_id = cursor.fetchone()[0]
            ref_pmt = f"{datetime.now().year}-PMT-CREDIT-{next_id:06d}"

            # 3. Requête d'insertion
            query = """
                INSERT INTO tb_pmtcredit (
                    refvente, 
                    mtpaye, 
                    datepmt, 
                    idmode, 
                    iduser, 
                    observation, 
                    refpmt,
                    idclient
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                self.refvente,
                montant_verse,
                datetime.now(),
                id_mode,
                self.iduser,
                f"Paiement crédit client : {self.client_nom}",
                ref_pmt,
                self.id_client_db
            )

            cursor.execute(query, values)
            conn.commit()
            
            # 4. Récupérer les infos pour le PDF AVANT de fermer la connexion
            username = self._get_username(cursor)
            societe = self._get_societe_info(cursor)
            articles = self._get_articles_vente(cursor)
            
            cursor.close()
            conn.close()
            conn = None
            
            # 5. Fermer la fenêtre IMMÉDIATEMENT après l'enregistrement
            self.withdraw()  # Cache la fenêtre
            self.grab_release()
            
            # 6. Afficher le message de succès
            self.after(50, lambda: messagebox.showinfo(
                "Succès", 
                f"Paiement enregistré avec succès !\nRéférence : {ref_pmt}",
                parent=self.master
            ))
            
            # 7. Générer le PDF après un court délai
            self.after(100, lambda: self._generer_ticket_pdf(
                societe, username, articles, montant_verse, nom_mode, ref_pmt
            ))
            
            # 8. Rafraîchir le parent
            if self.master and self.master.winfo_exists():
                try:
                    if hasattr(self.master, "load_data"):
                        self.after(200, self.master.load_data)
                except Exception as e:
                    print(f"Erreur rafraîchissement : {e}")
            
            # 9. Détruire complètement la fenêtre
            self.after(300, self.destroy)

        except ValueError:
            messagebox.showerror("Erreur", "Veuillez saisir un montant numérique valide.")
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Erreur détaillée : {traceback.format_exc()}")
            messagebox.showerror("Erreur", f"Erreur inattendue : {e}")
        finally:
            if conn:
                conn.close()

    def _get_username(self, cursor):
        """Récupère le nom d'utilisateur depuis tb_users"""
        try:
            # On cherche d'abord 'username', sinon on se rabat sur 'nom'
            cursor.execute("SELECT username FROM tb_users WHERE iduser = %s", (self.iduser,))
            result = cursor.fetchone()
            if result:
                return result[0]
            
            cursor.execute("SELECT nom FROM tb_users WHERE iduser = %s", (self.iduser,))
            result = cursor.fetchone()
            return result[0] if result else "Inconnu"
        except Exception as e:
            print(f"Erreur récupération username: {e}")
            return "Utilisateur"

    def _get_societe_info(self, cursor):
        """Récupère les infos précises de la société"""
        try:
            cursor.execute("""
                SELECT nomsociete, adressesociete, villesociete, contactsociete 
                FROM tb_infosociete 
                LIMIT 1
            """)
            return cursor.fetchone()
        except Exception as e:
            print(f"Erreur récupération société: {e}")
            return None

    def _get_articles_vente(self, cursor):
        """Récupère les articles de la vente"""
        try:
            query = """
                SELECT 
                    p.codeproduit,
                    p.desig,
                    p.unite,
                    dv.qtevente,
                    dv.puvente,
                    (dv.qtevente * dv.puvente) as montant
                FROM tb_detailvente dv
                JOIN tb_produit p ON dv.idproduit = p.idproduit
                WHERE dv.refvente = %s
                ORDER BY dv.id
            """
            cursor.execute(query, (self.refvente,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Erreur récupération articles: {e}")
            return []

    def _generer_ticket_pdf(self, societe, username, articles, montant, mode_nom, refpmt):
        """Génère le ticket PDF avec les informations société et utilisateur corrigées"""
        try:
            fd, path = tempfile.mkstemp(prefix='ticket_pmt_', suffix='.pdf')
            os.close(fd)

            total_height = (160 + (len(articles) * 10)) * mm
            c = canvas.Canvas(path, pagesize=(80*mm, total_height))
            y = total_height - 10*mm

            # ============================================
            # EN-TÊTE SOCIÉTÉ (Mise à jour selon tb_infosociete)
            # ============================================
            if societe:
                # societe[0]: nomsociete, [1]: adressesociete, [2]: villesociete, [3]: contactsociete
                c.setFont("Helvetica-Bold", 11)
                c.drawCentredString(40*mm, y, str(societe[0]).upper())
                y -= 5*mm
                
                c.setFont("Helvetica", 8)
                c.drawCentredString(40*mm, y, f"{societe[1]}") # adressesociete
                y -= 4*mm
                c.drawCentredString(40*mm, y, f"{societe[2]}") # villesociete
                y -= 4*mm
                c.drawCentredString(40*mm, y, f"Tél: {societe[3]}") # contactsociete
                y -= 2*mm
            else:
                c.setFont("Helvetica-Bold", 10)
                c.drawCentredString(40*mm, y, "MA SOCIÉTÉ")
                y -= 4*mm
            
            # Ligne de séparation
            y -= 4*mm
            c.line(5*mm, y, 75*mm, y)
            y -= 6*mm
            
            # ============================================
            # INFORMATIONS TICKET
            # ============================================
            c.setFont("Helvetica-Bold", 9)
            c.drawCentredString(40*mm, y, f"REÇU DE PAIEMENT N° {refpmt}")
            y -= 6*mm
            
            c.setFont("Helvetica", 8)
            c.drawString(5*mm, y, f"Facture: {self.refvente}")
            c.drawRightString(75*mm, y, datetime.now().strftime("%d/%m/%Y %H:%M"))
            y -= 4*mm
            
            c.drawString(5*mm, y, f"Client: {self.client_nom}")

            # ============================================
            # TABLEAU ARTICLES
            # ============================================
            y -= 10*mm
            c.setFont("Helvetica-Bold", 7)
            c.drawString(5*mm, y, "Code")
            c.drawString(20*mm, y, "Désignation")
            c.drawRightString(48*mm, y, "Qté")
            c.drawRightString(62*mm, y, "P.U")
            c.drawRightString(77*mm, y, "Total")
            y -= 2*mm
            c.line(5*mm, y, 75*mm, y)
            y -= 4*mm

            c.setFont("Helvetica", 6.5)
            for art in articles:
                code = str(art[0])[:8] if art[0] else ""
                designation = f"{art[1]} ({art[2]})" if art[2] else str(art[1])
                designation = designation[:20]  # Limite à 20 caractères
                
                c.drawString(5*mm, y, code)
                c.drawString(20*mm, y, designation)
                c.drawRightString(48*mm, y, str(art[3]))
                c.drawRightString(62*mm, y, f"{art[4]:,.0f}".replace(',', ' '))
                c.drawRightString(77*mm, y, f"{art[5]:,.0f}".replace(',', ' '))
                y -= 4*mm

            # ============================================
            # TOTAUX
            # ============================================
            y -= 6*mm
            c.line(40*mm, y+5*mm, 75*mm, y+5*mm)
            
            # NET À PAYER (montant total de la facture)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(5*mm, y, "NET À PAYER :")
            c.drawRightString(75*mm, y, f"{self.montant_total_float:,.2f} Ar".replace(',', ' ').replace('.', ','))
            
            # MONTANT PAYÉ (ce qui vient d'être versé)
            y -= 5*mm
            c.setFont("Helvetica-Bold", 10)
            c.drawString(5*mm, y, "MONTANT PAYÉ :")
            c.drawRightString(75*mm, y, f"{montant:,.2f} Ar".replace(',', ' ').replace('.', ','))
            
            # RESTE À PAYER
            y -= 5*mm
            reste = self.montant_total_float - montant
            c.setFont("Helvetica-Bold", 9)
            c.drawString(5*mm, y, "RESTE À PAYER :")
            c.drawRightString(75*mm, y, f"{reste:,.2f} Ar".replace(',', ' ').replace('.', ','))
            
            # ============================================
            # MONTANT EN LETTRES
            # ============================================
            y -= 8*mm
            if num2words:
                c.setFont("Helvetica-Oblique", 6)
                try:
                    lettres = num2words(int(montant), lang='fr').upper()
                    if len(lettres) > 45:
                        c.drawString(5*mm, y, f"Arrêté à: {lettres[:45]}")
                        y -= 3*mm
                        c.drawString(5*mm, y, f"{lettres[45:]} ARIARY")
                    else:
                        c.drawString(5*mm, y, f"Arrêté à: {lettres} ARIARY")
                except:
                    pass

            # ============================================
            # PIED DE PAGE
            # ============================================
            y -= 10*mm
            c.line(5*mm, y+2*mm, 75*mm, y+2*mm)
            
            c.setFont("Helvetica", 7)
            c.drawString(5*mm, y, f"Mode de paiement: {mode_nom}")
            y -= 5*mm
            
            c.setFont("Helvetica-Bold", 8)
            # Affichage de l'utilisateur récupéré (username)
            c.drawString(5*mm, y, f"Reçu par: {username}")
            
            c.showPage()
            c.save()
            
            # Ouverture du fichier
            if os.name == 'nt':
                os.startfile(path)
            else:
                subprocess.Popen(['xdg-open', path])

        except Exception as e:
            print(f"Erreur PDF : {e}")
            messagebox.showwarning("Erreur", f"Erreur PDF : {e}")