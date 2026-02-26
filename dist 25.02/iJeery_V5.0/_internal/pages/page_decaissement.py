# page_decaissement.py
import customtkinter as ctk
from tkinter import messagebox
import psycopg2
from datetime import datetime
import json
import os
import sys
from reportlab.lib.pagesizes import portrait
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from resource_utils import get_config_path, safe_file_read


# Ensure the parent directory is in the Python path for absolute imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Now, the absolute import will work
from pages.page_categorieCompte import PageCategorieCompte


class PageDecaissement(ctk.CTkToplevel):
    def __init__(self, master, username="Système"):
        super().__init__(master)
        self.title("Nouveau Décaissement")
        self.geometry("600x450")
        self.transient(master)
        self.grab_set()

        self.master_app = master
        self.current_user = username
        self.categories = {} 

        # Connexion à la base de données
        self.conn = self.connect_db()
        if self.conn:
            self.cursor = self.conn.cursor()
            self.create_widgets()
            self.charger_categories()
        else:
            messagebox.showerror("Erreur", "Connexion échouée")
            self.destroy()

    def connect_db(self):
        """Établit la connexion à la base de données à partir du fichier config.json"""
        try:
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
                port=db_config['port'],
                client_encoding='UTF8'
            )
            print("Connection to the database successful!")
            return conn
        except Exception as err:
            messagebox.showerror("Erreur de connexion", f"Détails : {err}")
            return None

    def create_widgets(self):
        """Crée et positionne les widgets de l'interface utilisateur."""
        self.grid_columnconfigure((0, 1, 2), weight=1)
        for i in range(5):
            self.grid_rowconfigure(i, weight=1)

        ctk.CTkLabel(self, text="Catégorie:").grid(row=0, column=0, padx=10, pady=10, sticky='e')
        self.combo_categorie = ctk.CTkComboBox(self, width=250, values=[], state="readonly")
        self.combo_categorie.grid(row=0, column=1, padx=10, pady=10, sticky='ew')

        self.bouton_ajouter_categorie = ctk.CTkButton(self, text="+", width=40, command=self.ouvrir_fenetre_categorie)
        self.bouton_ajouter_categorie.grid(row=0, column=2, padx=5, pady=10, sticky='w')

        ctk.CTkLabel(self, text="Montant:").grid(row=1, column=0, padx=10, pady=10, sticky='e')
        self.entry_montant = ctk.CTkEntry(self, width=250)
        self.entry_montant.grid(row=1, column=1, columnspan=2, padx=10, pady=10, sticky='ew')

        ctk.CTkLabel(self, text="Description:").grid(row=2, column=0, padx=10, pady=10, sticky='e')
        self.entry_description = ctk.CTkEntry(self, width=250)
        self.entry_description.grid(row=2, column=1, columnspan=2, padx=10, pady=10, sticky='ew')

        self.bouton_enregistrer = ctk.CTkButton(self, text="Enregistrer", fg_color="green", hover_color="#006400", command=self.enregistrer)
        self.bouton_enregistrer.grid(row=4, column=1, pady=20, padx=(10, 5), sticky='e')

        self.bouton_annuler = ctk.CTkButton(self, text="Annuler", fg_color="red", hover_color="#8B0000", command=self.annuler)
        self.bouton_annuler.grid(row=4, column=2, pady=20, padx=(5, 10), sticky='w')
        
        self.lbl_user = ctk.CTkLabel(self, text=f"Opérateur : {self.current_user}", font=("Arial", 10))
        self.lbl_user.grid(row=5, column=0, columnspan=3, pady=5)

    def ouvrir_fenetre_categorie(self):
        """Ouvre la fenêtre de catégorie et gère le retour en toute sécurité."""
        try:
            category_window = PageCategorieCompte(self)
            self.wait_window(category_window)
            
            if self.winfo_exists():
                self.charger_categories()
        except Exception as e:
            print(f"Erreur lors de la mise à jour : {e}")

    def generer_reference(self):
        """Génère une référence unique pour le décaissement."""
        now = datetime.now()
        return "DEC-" + now.strftime("%Y%m%d%H%M%S")

    def charger_categories(self):
        """Charge les catégories depuis la base de données et met à jour le combobox."""
        if not self.conn or not self.cursor:
            messagebox.showwarning("Avertissement", "Connexion à la base de données non disponible pour charger les catégories.")
            return

        try:
            self.cursor.execute("SELECT idcc, categoriecompte FROM tb_categoriecompte ORDER BY categoriecompte")
            self.categories = {}
            category_names = []
            for row in self.cursor.fetchall():
                self.categories[row[1]] = row[0]
                category_names.append(row[1])
            
            self.combo_categorie.configure(values=category_names)
            if category_names:
                self.combo_categorie.set(category_names[0])
            else:
                self.combo_categorie.set("")
            
            print(f"DEBUG: {len(category_names)} catégories chargées")
            
        except psycopg2.Error as e:
            messagebox.showerror("Erreur SQL", f"Erreur lors du chargement des catégories : {e}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur inattendue lors du chargement des catégories : {e}")

    def get_type_operation(self):
        """
        Récupère l'ID numérique (idtypeoperation) du type d'opération 'DEC'
        depuis la base de données.
        """
        if not self.conn or not self.cursor:
            return None 
        try:
            self.cursor.execute("SELECT idtypeoperation FROM tb_typeoperation WHERE LOWER(typeoperation) = 'dec'")
            result = self.cursor.fetchone()
            return result[0] if result else None
            
        except psycopg2.Error as e:
            messagebox.showwarning("Avertissement", f"Impossible de récupérer l'ID du type d'opération : {e}.")
            return None

    def get_infos_societe(self):
        """Récupère les informations de la société depuis tb_infosociete"""
        if not self.conn or not self.cursor:
            return None
        try:
            self.cursor.execute("""
                SELECT nomsociete, adressesociete, contactsociete, villesociete 
                FROM tb_infosociete 
                LIMIT 1
            """)
            result = self.cursor.fetchone()
            if result:
                return {
                    'nom': result[0] or "Nom Société",
                    'adresse': result[1] or "Adresse",
                    'contact': result[2] or "Contact",
                    'ville': result[3] or "Ville"
                }
            return None
        except Exception as e:
            print(f"Erreur lors de la récupération des infos société: {e}")
            return None

    def generer_ticket_pdf(self, reference, categorie, montant, description, operateur):
        """Génère un ticket de caisse au format PDF 80mm"""
        try:
            # Récupérer les infos de la société
            infos_societe = self.get_infos_societe()
            if not infos_societe:
                infos_societe = {
                    'nom': "Nom Société",
                    'adresse': "Adresse",
                    'contact': "Contact",
                    'ville': "Ville"
                }
            
            # Dimensions pour ticket 80mm
            largeur_ticket = 80 * mm
            hauteur_ticket = 200 * mm  # Hauteur dynamique
            
            # Créer le répertoire tickets s'il n'existe pas
            tickets_dir = os.path.join(os.path.expanduser("~"), "tickets_caisse")
            if not os.path.exists(tickets_dir):
                os.makedirs(tickets_dir)
            
            # Créer le fichier PDF
            fichier_pdf = os.path.join(tickets_dir, f"ticket_{reference}.pdf")
            c = canvas.Canvas(fichier_pdf, pagesize=(largeur_ticket, hauteur_ticket))
            
            # Position Y de départ (du haut vers le bas)
            y = hauteur_ticket - 10 * mm
            x_centre = largeur_ticket / 2
            marge_gauche = 5 * mm
            
            # --- EN-TÊTE SOCIÉTÉ ---
            c.setFont("Helvetica-Bold", 12)
            c.drawCentredString(x_centre, y, infos_societe['nom'])
            y -= 5 * mm
            
            c.setFont("Helvetica", 8)
            c.drawCentredString(x_centre, y, infos_societe['adresse'])
            y -= 4 * mm
            
            c.drawCentredString(x_centre, y, infos_societe['ville'])
            y -= 4 * mm
            
            c.drawCentredString(x_centre, y, f"Tél: {infos_societe['contact']}")
            y -= 7 * mm
            
            # Ligne de séparation
            c.line(marge_gauche, y, largeur_ticket - marge_gauche, y)
            y -= 7 * mm
            
            # --- TITRE ---
            c.setFont("Helvetica-Bold", 11)
            c.drawCentredString(x_centre, y, "TICKET DE DÉCAISSEMENT")
            y -= 7 * mm
            
            # Ligne de séparation
            c.line(marge_gauche, y, largeur_ticket - marge_gauche, y)
            y -= 7 * mm
            
            # --- DÉTAILS DE LA TRANSACTION ---
            c.setFont("Helvetica", 9)
            
            # Date et heure
            date_actuelle = datetime.now()
            c.drawString(marge_gauche, y, f"Date: {date_actuelle.strftime('%d/%m/%Y %H:%M')}")
            y -= 5 * mm
            
            # Référence
            c.drawString(marge_gauche, y, f"Réf: {reference}")
            y -= 5 * mm
            
            # Opérateur
            c.drawString(marge_gauche, y, f"Opérateur: {operateur}")
            y -= 7 * mm
            
            # Ligne de séparation
            c.line(marge_gauche, y, largeur_ticket - marge_gauche, y)
            y -= 7 * mm
            
            # Catégorie
            c.setFont("Helvetica-Bold", 9)
            c.drawString(marge_gauche, y, "Catégorie:")
            y -= 4 * mm
            c.setFont("Helvetica", 9)
            c.drawString(marge_gauche + 3 * mm, y, categorie)
            y -= 7 * mm
            
            # Description
            c.setFont("Helvetica-Bold", 9)
            c.drawString(marge_gauche, y, "Description:")
            y -= 4 * mm
            c.setFont("Helvetica", 8)
            
            # Découper la description si elle est trop longue
            max_largeur = largeur_ticket - 2 * marge_gauche - 3 * mm
            mots = description.split()
            ligne_actuelle = ""
            
            for mot in mots:
                test_ligne = ligne_actuelle + " " + mot if ligne_actuelle else mot
                largeur_texte = c.stringWidth(test_ligne, "Helvetica", 8)
                
                if largeur_texte <= max_largeur:
                    ligne_actuelle = test_ligne
                else:
                    c.drawString(marge_gauche + 3 * mm, y, ligne_actuelle)
                    y -= 4 * mm
                    ligne_actuelle = mot
            
            if ligne_actuelle:
                c.drawString(marge_gauche + 3 * mm, y, ligne_actuelle)
                y -= 7 * mm
            
            # Ligne de séparation
            c.line(marge_gauche, y, largeur_ticket - marge_gauche, y)
            y -= 7 * mm
            
            # --- MONTANT ---
            c.setFont("Helvetica-Bold", 14)
            c.drawString(marge_gauche, y, "MONTANT:")
            montant_str = f"{montant:,.2f} Ar"
            c.drawRightString(largeur_ticket - marge_gauche, y, montant_str)
            y -= 10 * mm
            
            # Ligne de séparation
            c.line(marge_gauche, y, largeur_ticket - marge_gauche, y)
            y -= 10 * mm
            
            # --- PIED DE PAGE ---
            c.setFont("Helvetica", 7)
            c.drawCentredString(x_centre, y, "Merci de votre confiance")
            y -= 4 * mm
            c.drawCentredString(x_centre, y, "Document non contractuel")
            
            # Sauvegarder le PDF
            c.save()
            
            return fichier_pdf
            
        except Exception as e:
            messagebox.showerror("Erreur PDF", f"Erreur lors de la génération du ticket: {e}")
            print(f"DEBUG: Erreur complète: {e}")
            return None

    def enregistrer(self):
        """Enregistre le décaissement avec l'utilisateur connecté."""
        if not self.conn or not self.cursor:
            return

        try:
            if not self.winfo_exists(): 
                return

            reference = self.generer_reference()
            categorie_nom = self.combo_categorie.get()
            idcc = self.categories.get(categorie_nom)
        
            mtpaye_str = self.entry_montant.get()
            observation = self.entry_description.get()
        
            if not idcc or not mtpaye_str or not observation:
                messagebox.showwarning("Attention", "Tous les champs doivent être remplis")
                return

            mtpaye = float(mtpaye_str)
            typeoperation_id = self.get_type_operation()
            datepmt = datetime.now()
        
            print(f"DEBUG: current_user = '{self.current_user}'")
        
            # Récupérer l'ID numérique de l'utilisateur
            self.cursor.execute("SELECT iduser, username FROM tb_users")
            all_users = self.cursor.fetchall()
            print(f"DEBUG: Utilisateurs dans la base: {all_users}")
        
            self.cursor.execute(
                "SELECT iduser FROM tb_users WHERE LOWER(TRIM(username)) = LOWER(TRIM(%s))", 
                (self.current_user,)
            )
            result = self.cursor.fetchone()
        
            if result:
                iduser = result[0]
                print(f"DEBUG: iduser trouvé = {iduser}")
            else:
                print(f"ATTENTION: Utilisateur '{self.current_user}' introuvable")
                self.cursor.execute("SELECT iduser FROM tb_users WHERE iduser = 1")
                default_user = self.cursor.fetchone()
            
                if default_user:
                    iduser = 1
                    print(f"DEBUG: Utilisation de l'utilisateur par défaut (ID=1)")
                else:
                    messagebox.showerror("Erreur", f"Aucun utilisateur trouvé dans la base de données")
                    return
            
            # INSERTION AVEC L'ID UTILISATEUR
            query = """
            INSERT INTO tb_decaissement (refpmt, idcc, mtpaye, observation, idtypeoperation, datepmt, iduser)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            print(f"DEBUG: Insertion avec iduser = {iduser}")
            self.cursor.execute(query, (reference, idcc, mtpaye, observation, typeoperation_id, datepmt, iduser))
        
            self.conn.commit()
            
            # --- GÉNÉRATION DU TICKET PDF ---
            fichier_pdf = self.generer_ticket_pdf(
                reference=reference,
                categorie=categorie_nom,
                montant=mtpaye,
                description=observation,
                operateur=self.current_user
            )
            
            if fichier_pdf:
                messagebox.showinfo("Succès", 
                    f"Décaissement enregistré avec succès!\n\n"
                    f"Référence: {reference}\n"
                    f"Ticket généré: {os.path.basename(fichier_pdf)}\n"
                    f"Emplacement: {os.path.dirname(fichier_pdf)}")
                
                # Ouvrir automatiquement le PDF
                try:
                    if sys.platform == "win32":
                        os.startfile(fichier_pdf)
                    elif sys.platform == "darwin":
                        os.system(f"open '{fichier_pdf}'")
                    else:
                        os.system(f"xdg-open '{fichier_pdf}'")
                except Exception as e:
                    print(f"Impossible d'ouvrir le PDF automatiquement: {e}")
                    # Ouvrir le dossier contenant le fichier
                    try:
                        if sys.platform == "win32":
                            os.startfile(os.path.dirname(fichier_pdf))
                        elif sys.platform == "darwin":
                            os.system(f"open '{os.path.dirname(fichier_pdf)}'")
                        else:
                            os.system(f"xdg-open '{os.path.dirname(fichier_pdf)}'")
                    except:
                        pass
            else:
                messagebox.showinfo("Succès", 
                    f"Décaissement enregistré avec succès!\n"
                    f"Référence: {reference}\n"
                    f"(Erreur lors de la génération du ticket)")
            
            # Réinitialiser les champs
            self.entry_montant.delete(0, 'end')
            self.entry_description.delete(0, 'end')
            if self.combo_categorie.cget("values"):
                self.combo_categorie.set(self.combo_categorie.cget("values")[0])
        
        except ValueError:
            messagebox.showerror("Erreur", "Le montant doit être un nombre valide")
            self.conn.rollback()
        except Exception as e:
            messagebox.showerror("Erreur SQL", str(e))
            print(f"DEBUG: Exception complète: {e}")
            self.conn.rollback()

    def annuler(self):
        """Ferme la fenêtre."""
        self.destroy()

    def __del__(self):
        """Assure que la connexion à la base de données est fermée lorsque l'objet est détruit."""
        if hasattr(self, 'conn') and self.conn:
            try:
                self.cursor.close()
            except:
                pass
            try:
                self.conn.close()
            except:
                pass
            print("Database connection closed.")


if __name__ == "__main__":
    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")

    root_for_test = ctk.CTk()
    root_for_test.withdraw()
    
    def open_decaissement_page_test():
        decaissement_page = PageDecaissement(root_for_test)
        root_for_test.wait_window(decaissement_page)

    open_decaissement_page_test()
    root_for_test.destroy()