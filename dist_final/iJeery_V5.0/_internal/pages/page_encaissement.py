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

from pages.page_categorieCompte import PageCategorieCompte

class DatabaseManager:
    def __init__(self):
        self.db_params = self._load_db_config()

    def _load_db_config(self):
        """Loads database configuration from 'config.json'."""
        try:
            config_path = get_config_path('config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
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
            conn = psycopg2.connect(
                host=self.db_params['host'],
                user=self.db_params['user'],
                password=self.db_params['password'],
                database=self.db_params['database'],
                port=self.db_params['port']
            )
            print("Connection to the database successful!")
            return conn
        except psycopg2.OperationalError as e:
            print(f"Error connecting to the database: {e}")
            return None

class PageEncaissement(ctk.CTkToplevel):
    # Ajout du paramètre username (défaut à "Système" si non fourni)
    def __init__(self, master, username="Système"):
        super().__init__(master)
        self.title("Nouvel Encaissement")
        # taille initiale raisonnable puis centrage
        self.geometry("500x350")
        self.transient(master)
        self.grab_set()
        self.center_window()

        self.master_app = master
        # Charger l'utilisateur courant depuis la session si disponible
        loaded_username, loaded_user_id = self._load_user_session()
        # Priorité : session.json si présente, sinon paramètre username (ou défaut)
        if loaded_username:
            self.current_user = loaded_username
        elif username and username != "Système":
            self.current_user = username
        else:
            self.current_user = username

        # ID numérique de l'utilisateur si disponible (pour insertion directe)
        self.current_user_id = loaded_user_id
        self.categories = {}
        # Protection contre les double-clics
        self._processing = False
        self._finalized = False

        self.db_manager = DatabaseManager()
        self.conn = self.db_manager.get_connection()

        if self.conn:
            self.cursor = self.conn.cursor()
            self.create_widgets()
            # s'assurer que le label affichant l'opérateur est à jour
            try:
                self.lbl_user.configure(text=f"Opérateur : {self.current_user}")
            except Exception:
                pass
            self.charger_categories()
        else:
            messagebox.showerror("Erreur", "Connexion échouée")
            self.destroy()

    def center_window(self):
        """Centre la fenêtre sur l'écran."""
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _load_user_session(self):
        """Charge le nom d'utilisateur et l'ID depuis session.json si disponible.
        Retourne (username, user_id) ou (None, None) si non trouvé.
        """
        try:
            session_path = get_config_path('session.json')
            if session_path and os.path.exists(session_path):
                with open(session_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    username = data.get('username') or data.get('user')
                    # Plusieurs versions peuvent stocker l'id sous différents noms
                    user_id = data.get('user_id') or data.get('id') or data.get('iduser')
                    return username, user_id
        except Exception as e:
            print(f"DEBUG: impossible de charger session.json: {e}")
        return None, None

    def create_widgets(self):
        """Crée et positionne les widgets de l'interface utilisateur avec un design épuré."""
        # cadre principal
        main = ctk.CTkFrame(self, fg_color="#f0f0f0", corner_radius=10)
        main.pack(expand=True, fill="both", padx=20, pady=20)

        header = ctk.CTkLabel(main, text="NOUVEL ENCAISSEMENT", font=ctk.CTkFont(size=18, weight="bold"))
        header.pack(pady=(0,15))

        form = ctk.CTkFrame(main)
        form.pack(fill="x", pady=10)
        form.grid_columnconfigure(1, weight=1)

        # catégorie
        ctk.CTkLabel(form, text="Catégorie:", anchor="w").grid(row=0, column=0, padx=5, pady=8, sticky='w')
        self.combo_categorie = ctk.CTkComboBox(form, width=200, values=[])
        self.combo_categorie.grid(row=0, column=1, padx=5, pady=8, sticky='ew')
        self.bouton_ajouter_categorie = ctk.CTkButton(form, text="+", width=30, command=self.ouvrir_fenetre_categorie)
        self.bouton_ajouter_categorie.grid(row=0, column=2, padx=5, pady=8)

        # montant
        ctk.CTkLabel(form, text="Montant:", anchor="w").grid(row=1, column=0, padx=5, pady=8, sticky='w')
        self.entry_montant = ctk.CTkEntry(form, width=200)
        self.entry_montant.grid(row=1, column=1, columnspan=2, padx=5, pady=8, sticky='ew')
        self.entry_montant.bind("<KeyRelease>", lambda e: self.format_montant())
        self.entry_montant.bind("<FocusOut>", lambda e: self.format_montant())

        # description
        ctk.CTkLabel(form, text="Description:", anchor="w").grid(row=2, column=0, padx=5, pady=8, sticky='w')
        self.entry_description = ctk.CTkEntry(form, width=200)
        self.entry_description.grid(row=2, column=1, columnspan=2, padx=5, pady=8, sticky='ew')

        # boutons
        button_frame = ctk.CTkFrame(main, fg_color="transparent")
        button_frame.pack(pady=15)
        self.bouton_enregistrer = ctk.CTkButton(button_frame, text="Enregistrer", fg_color="#007AFF", hover_color="#005BB5", width=120, command=self._on_enregistrer_click)
        self.bouton_enregistrer.pack(side="left", padx=10)
        self.bouton_annuler = ctk.CTkButton(button_frame, text="Annuler", fg_color="#FF3B30", hover_color="#C1271A", width=120, command=self.annuler)
        self.bouton_annuler.pack(side="left", padx=10)

        self.lbl_user = ctk.CTkLabel(main, text=f"Opérateur : {self.current_user}", font=ctk.CTkFont(size=10))
        self.lbl_user.pack(pady=(10,0))

    def format_montant(self):
        """Formate le montant avec séparateurs de milliers (format français: 1.234.567)."""
        current = self.entry_montant.get()
        if not current:
            return
        
        # Supprimer tous les séparateurs existants
        # Ne garder que les chiffres (pas de décimales autorisées)
        cleaned = current.replace('.', '').replace(',', '').replace(' ', '')
        
        # Vérifier que ce ne sont que des chiffres
        if not cleaned or not cleaned.isdigit():
            self.entry_montant.delete(0, 'end')
            self.entry_montant.insert(0, current)  # Restaurer la saisie inchangée
            return
        
        # Ajouter séparateurs de milliers (.) à la partie entière
        formatted = ''
        for i, digit in enumerate(reversed(cleaned)):
            if i > 0 and i % 3 == 0:
                formatted = '.' + formatted
            formatted = digit + formatted
        
        self.entry_montant.delete(0, 'end')
        self.entry_montant.insert(0, formatted)
        
        # Positionner le curseur à la fin du texte
        self.entry_montant.icursor(len(formatted))

    def ouvrir_fenetre_categorie(self):
        """Ouvre la fenêtre de catégorie et gère le retour en toute sécurité."""
        try:
            category_window = PageCategorieCompte(self.master)
            self.master.wait_window(category_window)
            
            if self.winfo_exists():
                self.charger_categories()
        except Exception as e:
            print(f"Erreur lors de la mise à jour : {e}")

    def _on_enregistrer_click(self):
        """Wrapper pour empêcher les double-clics rapides sur le bouton Enregistrer."""
        # Si déjà en cours ou finalisé, ignorer
        if self._processing or self._finalized:
            messagebox.showwarning("Attention", "L'enregistrement est déjà en cours...")
            return
        
        try:
            self._processing = True
            self.bouton_enregistrer.configure(state="disabled")
            self.bouton_annuler.configure(state="disabled")
            
            # Appeler la logique principale
            self.enregistrer()
        finally:
            # Réactiver les boutons si la fenêtre existe toujours et que ce n'est pas finalisé
            if self.winfo_exists() and not self._finalized:
                self._processing = False
                try:
                    self.bouton_enregistrer.configure(state="normal")
                    self.bouton_annuler.configure(state="normal")
                except:
                    pass

    def generer_reference(self):
        """Génère une référence unique pour l'encaissement."""
        now = datetime.now()
        return "ENC - " + now.strftime("%Y%m%d%H%M%S")

    def charger_categories(self):
        """Charge les catégories depuis la base de données et met à jour le combobox."""
        if not self.conn or not self.cursor:
            messagebox.showwarning("Avertissement", "Connexion à la base de données non disponible pour charger les catégories.")
            return

        try:
            self.cursor.execute("SELECT idcc, categoriecompte FROM tb_categoriecompte")
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
        except psycopg2.Error as e:
            messagebox.showerror("Erreur SQL", f"Erreur lors du chargement des catégories : {e}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur inattendue lors du chargement des catégories : {e}")

    def get_type_operation(self):
        """
        CORRECTION: Récupère l'ID numérique (idtypeoperation) du type d'opération 'ENC'
        depuis la base de données.
        """
        if not self.conn or not self.cursor:
            return None
        try:
            # Sélectionne idtypeoperation (l'ID entier) pour le type 'ENC' (Encaissement)
            self.cursor.execute("SELECT idtypeoperation FROM tb_typeoperation WHERE LOWER(typeoperation) = 'enc' OR idtypeoperation = 1")
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
            c.drawCentredString(x_centre, y, "TICKET D'ENCAISSEMENT")
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

    def _on_enregistrer_click(self):
        """Wrapper pour empêcher les double-clics rapides sur le bouton Enregistrer."""
        # Si déjà en cours ou finalisé, ignorer
        if self._processing or self._finalized:
            messagebox.showwarning("Attention", "L'enregistrement est déjà en cours...")
            return
        
        try:
            self._processing = True
            self.bouton_enregistrer.configure(state="disabled")
            self.bouton_annuler.configure(state="disabled")
            
            # Appeler la logique principale
            self.enregistrer()
        finally:
            # Réactiver les boutons si la fenêtre existe toujours et que ce n'est pas finalisé
            if self.winfo_exists() and not self._finalized:
                self._processing = False
                try:
                    self.bouton_enregistrer.configure(state="normal")
                    self.bouton_annuler.configure(state="normal")
                except:
                    pass

    def enregistrer(self):
        """Enregistre l'encaissement avec l'utilisateur connecté."""
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
                messagebox.showwarning("Attention", "Champs vides")
                return

            # Supprimer les séparateurs de milliers et convertir en float
            # Format: 1.234.567 → supprime "." → 1234567 → 1234567.0
            mtpaye = float(mtpaye_str.replace('.', ''))
            typeoperation_id = self.get_type_operation()
            datepmt = datetime.now()
            
            # DEBUG: Afficher le nom d'utilisateur actuel
            print(f"DEBUG: current_user = '{self.current_user}'")
            
            # Si nous avons déjà l'ID utilisateur depuis la session, l'utiliser
            if getattr(self, 'current_user_id', None):
                iduser = self.current_user_id
                print(f"DEBUG: Utilisation de l'id utilisateur depuis la session: {iduser}")
            else:
                # CORRECTION: Récupérer l'ID numérique de l'utilisateur depuis la base
                try:
                    self.cursor.execute("SELECT iduser, username FROM tb_users")
                    all_users = self.cursor.fetchall()
                    print(f"DEBUG: Utilisateurs dans la base: {all_users}")

                    # Chercher l'utilisateur (insensible à la casse)
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
                        # Essayer de récupérer l'ID 1 (utilisateur par défaut)
                        self.cursor.execute("SELECT iduser FROM tb_users WHERE iduser = 1")
                        default_user = self.cursor.fetchone()

                        if default_user:
                            iduser = 1
                            print(f"DEBUG: Utilisation de l'utilisateur par défaut (ID=1)")
                        else:
                            messagebox.showerror("Erreur", f"Aucun utilisateur trouvé dans la base de données")
                            return
                except Exception as e:
                    print(f"DEBUG: erreur lors de la recherche d'utilisateur: {e}")
                    messagebox.showerror("Erreur", f"Erreur lors de la recherche de l'utilisateur: {e}")
                    return
                
            # INSERTION AVEC L'ID UTILISATEUR ET IDMODE = 1 (Espèces)
            query = """
            INSERT INTO tb_encaissement (refpmt, idcc, mtpaye, observation, idtypeoperation, datepmt, iduser, idmode)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            print(f"DEBUG: Insertion avec iduser = {iduser}, idmode = 1 (Espèces)")
            self.cursor.execute(query, (reference, idcc, mtpaye, observation, typeoperation_id, datepmt, iduser, 1))
        
            self.conn.commit()
            self._finalized = True  # Marquer comme finalisé

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
                    f"Encaissement enregistré avec succès!\n\n"
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
    
    def open_encaissement_page_test():
        encaissement_page = PageEncaissement(root_for_test)
        root_for_test.wait_window(encaissement_page)

    open_encaissement_page_test()
    root_for_test.destroy()