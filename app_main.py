# -*- coding: utf-8 -*-
import customtkinter as ctk
from PIL import Image
import os
import json
import sys
import time
import subprocess
import tkinter as tk
from datetime import datetime
from typing import Optional
import psycopg2
from psycopg2 import OperationalError
import importlib.util

# Ensure the parent directory is in the Python path for absolute imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


# Import all your page modules
from pages.page_activitePrix import PageActivitePrix
from pages.page_absence import PageAbsence
from pages.page_article import PageArticle
from pages.page_ArticleListe import page_listeArticle
from pages.page_articleFrs import PageArticleFrs
from pages.page_articleMouvement import PageArticleMouvement
from pages.page_autorisation import PageAutorisation
from pages.page_avance15e import PageAVQ
from pages.page_avanceSpecial_ import FenetreAvanceSpec
from pages.page_avoir import PageAvoir
from pages.page_banque import PageBanque
from pages.page_banqueAjout import PageBanqueNv
from pages.page_BaseListe import PageBaseListe
from pages.page_caisse import PageCaisse
from pages.page_categorieArticle import PageCategorieArticle
from pages.page_categorieCompte import PageCategorieCompte
from pages.page_client import PageClient
from pages.page_clientCrédit import PageClientCrédit
from pages.page_CmdFrs import PageCommandeFrs
from pages.page_CodeAutorisation import PageCodeAutorisation
from pages.page_decaissement import PageDecaissement
from pages.page_encaissement import PageEncaissement
from pages.page_evenement import PageEvenement
from pages.page_decaissementBq import PageDecaissementBq
from pages.page_encaissementBq import PageEncaissementBq
from pages.page_Facturation import PageFacturation
from pages.page_factureListe import PageFactureListe
from pages.page_fonction import PageFonction
from pages.page_fournisseur import PageFournisseur
from pages.page_FrsDette import PageFrsDette
from pages.page_home import page_home
from pages.page_chat import PageChat
from pages.page_infoArticle import PageInfoArticle
from pages.page_inventaire import PageInventaire
from pages.page_infoMouvement import PageInfoMouvementStock
from pages.page_livrFrs import PageBonReception
from pages.page_LivraisonClient import PageLivraisonClient
from pages.page_ListeFacture import PageListeFacture
from pages.page_magasin import PageMagasin
from pages.page_mainPers import PageMainPersonnel
from pages.page_personnelAjout import PagePeronnelAjout
from pages.page_personnel import PagePersonnel
from pages.page_peremption import PageGestionPeremption
from pages.page_menu import PageMenu
from pages.page_mouvementStock import PageMouvementStock
from pages.page_pmtCredit import PagePmtCredit
from pages.page_pmtFacture import PagePmtFacture
from pages.page_pmtFrs import PagePmtFrs
from pages.page_pmtSalaire import PageValidationSalaire
from pages.page_presence import PagePresence
from pages.page_prixListe import PagePrixListe
from pages.page_prixSaisie import PagePrixSaisie
from pages.page_proforma import PageCommandeCli
from pages.page_reinit import DBInitializerApp
from pages.page_salaireBase_ import PageSalaireBase
from pages.page_salaireEtatBase_ import PageSalaireEtatSB
from pages.page_salaireEtatHoraire_ import PageEtatSalaireHoraire
from pages.page_sauvegarde import PageSauvegarde
from pages.page_sortie import PageSortie
from pages.page_stock import PageStock
from pages.page_StockLivraison import PageStockLivraison
from pages.page_StockAlerte import PageStockAlerte
from pages.page_SuiviCommande import PageSuiviCommande
from pages.page_transfert import PageTransfert
from pages.page_transfertBanque import PageTransfertBanque
from pages.page_transfertCaisse import PageTransfertCaisse
from pages.page_tauxhoraire import PageTauxHoraire
from pages.page_typePmt import PageTypePmt
from pages.page_unite import PageUnite
from pages.page_unite import PageUniteToplevel
from pages.page_users import PageUsers
from pages.page_venteParMsin import PageVenteParMsin
from pages.page_vente import PageVente
from pages.page_listeMouvement import PageListeMouvement
# from pages.page_absenceMiseAjour import PageAbsenceMJ

from tkinter import messagebox # Import messagebox for logout confirmation

def charger_page_dynamique(nom_module, nom_classe, parent_frame, iduser):
    """Charge une classe depuis un fichier .py externe"""
    try:
        # Déterminer le chemin du dossier 'pages'
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        chemin_fichier = os.path.join(base_path, "pages", f"{nom_module}.py")

        if not os.path.exists(chemin_fichier):
            messagebox.showerror("Erreur", f"Fichier introuvable : {chemin_fichier}")
            return None

        # Importation dynamique
        spec = importlib.util.spec_from_file_location(nom_module, chemin_fichier)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Récupérer la classe et l'instancier
        classe_page = getattr(module, nom_classe)
        return classe_page(parent_frame, iduser)
    except Exception as e:
        messagebox.showerror("Erreur de Module", f"Impossible de charger {nom_module} : {e}")
        return None


ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class DatabaseManager:
    def __init__(self):
        self.db_params = self._load_db_config()
        self.conn = None

    def _load_db_config(self):
        try:
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))

            config_path = os.path.join(base_path, "config.json")

            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            return config["database"]

        except FileNotFoundError:
            print(f"Erreur : config.json introuvable ({config_path})")
            return None
        except KeyError:
            print("Erreur : clé 'database' absente dans config.json")
            return None
        except json.JSONDecodeError as e:
            print(f"Erreur JSON : {e}")
            return None
    
    def get_connection(self):
        """Establishes a new database connection."""
        if self.db_params is None:
            print("❌ Cannot connect: Database configuration is missing.")
            return None
    
        try:
            print(f"🔄 Tentative de connexion à:")
            print(f"   Host: {self.db_params['host']}")
            print(f"   Port: {self.db_params['port']}")
            print(f"   User: {self.db_params['user']}")
            print(f"   Database: {self.db_params['database']}")
        
            self.conn = psycopg2.connect(
                host=self.db_params['host'],
                user=self.db_params['user'],
                password=self.db_params['password'],
                database=self.db_params['database'],
                port=self.db_params['port'],
                connect_timeout=10  # Timeout de 10 secondes
            )
            print("✅ Connection to the database successful!")
            return self.conn
        
        except psycopg2.OperationalError as e:
            print(f"❌ ERREUR OPÉRATIONNELLE PostgreSQL:")
            print(f"   {str(e)}")
        
            # Messages d'erreur spécifiques
            if "timeout" in str(e).lower():
                print("   → Le serveur ne répond pas (pare-feu ou serveur arrêté)")
            elif "password authentication failed" in str(e).lower():
                print("   → Mot de passe incorrect")
            elif "no route to host" in str(e).lower():
                print("   → Impossible d'atteindre le serveur (réseau)")
            elif "connection refused" in str(e).lower():
                print("   → PostgreSQL n'écoute pas sur ce port")
            
            return None
        
        except Exception as e:
            print(f"❌ AUTRE ERREUR: {type(e).__name__}")
            print(f"   {str(e)}")
            return None


class App(ctk.CTk):
    def __init__(self, session_data):
        super().__init__()
        self.title("iJerry - Tableau de Bord")
        self.geometry("1200x760")
        self.minsize(900, 560)

        # Responsive state
        self._base_window_width = 1200
        self._base_window_height = 760
        self._ui_scale = 1.0
        self._sidebar_expanded_width = 220
        self._sidebar_collapsed_width = 44
        self._main_button_height = 60
        self._submenu_button_height = 40
        self._main_font_size = 14
        self._submenu_font_size = 12
        self._toggle_font_size = 16
        self._menu_pad_x = 10
        self._menu_pad_y = 5
        self._submenu_pad_x = 5
        self._submenu_pad_y = 2
        self._menu_corner_radius = 10
        self._sidebar_logo_path = None
        self._sidebar_logo_size = None
        self._last_resize_update = 0.0
        self.sidebar_title_label = None
        
        self.sidebar_expand = True
        self.session_data = session_data
        self.authorized_menus = {menu[0]: menu[1] for menu in session_data['menus']}
        self.id_user_connecte = session_data.get('user_id')  # NOUVEAU
        
        # Initialiser la connexion DB en premier
        self.db_manager = DatabaseManager()
        self.db_conn = self.db_manager.get_connection()

        # Récupérer le nom de la société juste après la connexion réussie
        self.fetch_societe_info()
        
        if self.db_conn is None:
            from tkinter import messagebox
            messagebox.showerror("Erreur", "Impossible de se connecter à la base de données")
            self.destroy()
            return
        
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color="#25a9e1")
        self.sidebar_frame.grid(row=0, column=0, sticky="ns")
        self.sidebar_frame.grid_propagate(False)

        # Charger et afficher le logo
        logo_path = resource_path("image/logo 3.png")
        if os.path.exists(logo_path):
            self._sidebar_logo_path = logo_path
            logo_image = ctk.CTkImage(
                light_image=Image.open(logo_path),
                dark_image=Image.open(logo_path),
                size=(150, 50)
            )
            title_label = ctk.CTkLabel(
                self.sidebar_frame,
                image=logo_image,
                text=""
            )
            title_label.image = logo_image  # Garder une référence
            title_label.pack(pady=(0, 20))
        else:
            # Fallback au texte si l'image n'existe pas
            title_label = ctk.CTkLabel(
                self.sidebar_frame,
                text="iJeery_V5.0",
                text_color="white",
                font=ctk.CTkFont(family="Britannic Bold", size=25, weight="bold")
            )
            title_label.pack(pady=(0, 20))
        self.sidebar_title_label = title_label

        self.toggle_button = ctk.CTkButton(
            self.sidebar_frame, text="≡", corner_radius=10, fg_color="#034787",
            text_color="white", font=("Arial", 16),
            command=self.toggle_sidebar, hover_color="#10ff7c"
        )
        self.toggle_button.pack(pady=10, padx=10, fill="x")

        # Create scrollable frame for menu
        self.scrollable_frame = ctk.CTkScrollableFrame(self.sidebar_frame, fg_color="transparent")
        self.scrollable_frame.pack(fill="both", expand=True)
        
        self.nav_area_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
        self.nav_area_frame.pack(fill="both", expand=True)

        # Initialize submenu frames
        self.admin_submenu_frame = ctk.CTkFrame(self.nav_area_frame, fg_color="#25a9e1")
        self.personnel_submenu_frame = ctk.CTkFrame(self.nav_area_frame, fg_color="#25a9e1")
        self.tresorerie_submenu_frame = ctk.CTkFrame(self.nav_area_frame, fg_color="#25a9e1")
        self.database_submenu_frame = ctk.CTkFrame(self.nav_area_frame, fg_color="#25a9e1")
        self.examen_blanc_submenu_frame = ctk.CTkFrame(self.nav_area_frame, fg_color="#25a9e1")

        self.create_menu_buttons()

        self.logout_button = ctk.CTkButton(
            self.sidebar_frame, text="🚪 Déconnexion", corner_radius=10,
            fg_color="#034787", text_color="white", hover_color="#c0392b",
            font=("Arial", 14), command=self.logout
        )
        self.logout_button.pack(pady=10, padx=10, fill="x", side="bottom")

        self.content_frame = ctk.CTkFrame(self, fg_color="#ecf0f1", corner_radius=15)
        self.content_frame.grid(row=0, column=1, sticky="nsew")


        # Mapping of page names from DB to actual page classes/functions
        self.page_mapping = {
            "PageArticle": PageArticle,
            "PageAbsence" : PageAbsence,
            "PageArticleFrs": PageArticleFrs,
            "page_listeArticle": page_listeArticle,
            "PageArticleMouvement": PageArticleMouvement,
            "PageAutorisation" : PageAutorisation,
            "PageAvoir": PageAvoir,
            "PageAVQ" : PageAVQ,
            "FenetreAvanceSpec" : FenetreAvanceSpec,
            "PageBanque" : PageBanque,
            "PageBanqueNv" : PageBanqueNv,
            "PageBaseListe" : PageBaseListe,
            "PageCaisse": PageCaisse,
            "PageCategorieArticle": PageCategorieArticle,
            "PageCategorieCompte" : PageCategorieCompte,
            "PageClient": PageClient,
            "PageClientCrédit": PageClientCrédit,
            "PageCommandeFrs": PageCommandeFrs,
            "PageCodeAutorisation" : PageCodeAutorisation,
            "PageDecaissement": PageDecaissement,
            "PageDecaissementBq": PageDecaissementBq,
            "PageEncaissement": PageEncaissement,
            "PageEncaissementBq": PageEncaissementBq,
            "PageEvenement" : PageEvenement,
            "PageFacturation" : PageFacturation,
            "PageFactureListe": PageFactureListe,
            "PageFonction": PageFonction,
            "PageFournisseur": PageFournisseur,
            "PageFrsDette": PageFrsDette,
            "page_home": page_home,
            "PageChat": PageChat,
            "PageInfoArticle": PageInfoArticle,
            "PageInfoMouvementStock" : PageInfoMouvementStock,
            "PageBonReception" : PageBonReception,
            "PageLivraisonClient" : PageLivraisonClient,
            "PageListeFacture" : PageListeFacture,
            "PageListeMouvement" : PageListeMouvement,
            "PageMainPersonnel" : PageMainPersonnel,
            "PageMagasin" : PageMagasin,
            "PageMenu": PageMenu,
            "PageMouvementStock": PageMouvementStock,
            "PagePrixListe" : PagePrixListe,
            "PagePresence" : PagePresence,
            "PageSalaireBase" : PageSalaireBase,
            "PageSalaireEtatSB" : PageSalaireEtatSB,
            "PageEtatSalaireHoraire" : PageEtatSalaireHoraire,
            "PageSauvegarde": PageSauvegarde,
            "PageSortie": PageSortie,
            "PageStock": PageStock,
            "PageStockAlerte": PageStockAlerte,
            "PageStockLivraison" : PageStockLivraison,
            "PageSuiviCommande" : PageSuiviCommande,
            "PageTransfert": PageTransfert,
            "PageTransfertBanque" : PageTransfertBanque,
            "PageTransfertCaisse" : PageTransfertCaisse,
            "PageTypePmt" : PageTypePmt,
            "PageUnite" : PageUnite,
            "PageTransfertBanque" : PageTransfertBanque,
            "PageTransfertCaisse" : PageTransfertCaisse,
            "PageUsers": PageUsers,
            "PageVente" : PageVente,
            "PageVenteParMsin" : PageVenteParMsin,
            "PageValidationSalaire" : PageValidationSalaire,
            #"ConfigWindow" : ConfigWindow,
            "PageTauxHoraire" : PageTauxHoraire,
            "DBInitializerApp" : DBInitializerApp
            # "page_personnel" : page_personnel # This was a duplicate import
        }

        
        self.current_submenu_open = None

        # Set close callback
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Display home page or not authorized message
        if "TABLEAU DE BORD" in self.authorized_menus:
            self.show_page(page_home)
        else:
            self.show_page_not_authorized("Vous n'êtes pas autorisé à voir le tableau de bord.")

        if "CHAT INTERNE" in self.authorized_menus:
            self.show_page(PageChat)
        else:
            self.show_page_not_authorized("Vous n'êtes pas autorisé à voir le chat interne.")

        # Update title bar
        self.update_title_bar()
        self.after(1000, self.update_title_bar_time_only)
        self.bind("<Configure>", self._on_window_resize)
        self.after(120, self._apply_responsive_layout)

    def open_db_config_window(self):
        """Ouvre la fenetre de configuration de la base de données"""
        try:
            # Fermer la fenêtre existante si elle est ouverte
            if hasattr(self, '_config_window') and self._config_window is not None and self._config_window.winfo_exists():
                self._config_window.destroy()
                self._config_window = None
        
            # Créer une nouvelle fenêtre de configuration
            self._config_window = DatabaseManager(master=self, app_root=self)
        
            # Rendre la fenêtre modale
            self._config_window.grab_set()
            self._config_window.focus_force()
            self._config_window.transient(self)
        
            # Attendre la fermeture de la fenêtre
            self.wait_window(self._config_window)
            self._config_window = None
        
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'ouvrir la fenetre de configuration : {e}")

    def connect_to_database(self):
        """Establishes or re-establishes the database connection."""
        # Fermer l'ancienne connexion si elle existe
        if hasattr(self, 'db_conn') and self.db_conn:
            try:
                self.db_conn.close()
                print("Ancienne connexion à la base de donnees fermee.")
            except Exception as e:
                print(f"Erreur lors de la fermeture de l'ancienne connexion: {e}")
    
        # Créer une nouvelle connexion en utilisant directement la fonction create_db_connection
        new_conn = DatabaseManager()
        if new_conn:
            print(f"Connecte a la base de donnees.")
            return new_conn
        else:
            print("Echec de la connexion a la base de donnees.")
            return None

        # --- New method to be called by ConfigWindow when config changes ---
    def reload_db_connection(self):
        """Reloads the database connection and updates the title bar after config change."""
        print("Rechargement de la connexion a la base de donnees...")
        new_conn = self.connect_to_database()  # Try to connect with new parameters
        if new_conn:
            self.db_conn = new_conn  # Assign the new connection
            self.update_title_bar()  # Update title bar with new DB name/info
            messagebox.showinfo("Connexion mise a jour", "La connexion a la base de donnees a été mise a jour avec succes.")
            # Optional: Refresh the current page if it relies heavily on DB data
            # self.show_page(self.current_page_func) # You might need to store the current page
        else:
            messagebox.showerror("Erreur", "La connexion à la base de donnees n'a pas pu etre etablie avec les nouveaux parametres.")
    
    def ouvrir_page_vente(self):
        """Ouvre la page de vente en passant l'ID utilisateur"""
        # Vider le frame principal
        for widget in self.main_frame.winfo_children():
            widget.destroy()
    
        # Créer la page de vente avec l'ID utilisateur
        page_vente = PageVenteParMsin(self.main_frame, id_user_connecte=self.id_user_connecte)
        page_vente.pack(fill="both", expand=True)

        # --- New method for graceful closing ---
    def on_closing(self):
        """Handles the window closing event to ensure DB connection is closed."""
        if hasattr(self, 'db_conn') and self.db_conn:
            try:
                self.db_conn.close()
                print("Connexion à la base de données fermée proprement.")
            except Exception as e:
                print(f"Erreur lors de la fermeture de la connexion : {e}")
        self.destroy()

    def logout(self):
        from tkinter import messagebox
        if messagebox.askyesno("Déconnexion", "Êtes-vous sûr de vouloir vous déconnecter ?"):
            try:
                # Supprimer le fichier de session
                if os.path.exists("session.json"):
                    os.remove("session.json")
                    print("Fichier session.json supprimé.")
                
                # Fermer la connexion à la base de données
                if hasattr(self, 'db_conn') and self.db_conn:
                    try:
                        self.db_conn.close()
                        print("Connexion à la base de données fermée.")
                    except Exception as e:
                        print(f"Erreur lors de la fermeture de la connexion : {e}")
                
                # Détruire la fenêtre actuelle AVANT de relancer
                self.withdraw()  # Cacher la fenêtre immédiatement
                
                # Relancer l'application
                import subprocess
                import time
                
                # Déterminer le chemin de l'exécutable
                if getattr(sys, 'frozen', False):
                    # Application compilée avec PyInstaller
                    executable_path = sys.executable
                    print(f"Mode compilé détecté. Exécutable: {executable_path}")
                    
                    # Lancer le nouvel process AVANT de fermer celui-ci
                    subprocess.Popen([executable_path], 
                                   cwd=os.path.dirname(executable_path),
                                   creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0)
                    
                    # Petit délai pour laisser le nouveau process démarrer
                    time.sleep(0.5)
                else:
                    # Mode développement
                    base_path = os.path.dirname(os.path.abspath(__file__))
                    app_script_path = os.path.join(base_path, "app_main.py")
                    
                    if os.path.exists(app_script_path):
                        subprocess.Popen([sys.executable, app_script_path])
                        print(f"Relancement de l'application via {app_script_path}")
                    else:
                        print(f"ATTENTION: {app_script_path} n'existe pas")
                        messagebox.showwarning("Attention", "Le fichier app_main.py est introuvable")
                
                # Fermer proprement l'application actuelle
                try:
                    self.quit()
                    self.destroy()
                except:
                    pass
                
                # Terminer le processus
                sys.exit(0)
                
            except Exception as e:
                print(f"Erreur lors de la déconnexion : {e}")
                import traceback
                traceback.print_exc()
                messagebox.showerror("Erreur", f"Une erreur est survenue lors de la déconnexion : {e}")
                try:
                    self.destroy()
                except:
                    pass
                sys.exit(1)
    
    
    def fetch_societe_info(self):
        """Récupère le nom de la société depuis la base de données."""
        if self.db_conn:
            try:
                cursor = self.db_conn.cursor()
                cursor.execute("SELECT nomsociete FROM tb_infosociete LIMIT 1")
                result = cursor.fetchone()
                if result:
                    self.nom_societe = result[0]
                cursor.close()
            except Exception as e:
                print(f"Erreur lors de la récupération du nom de la société : {e}")
   

    # --- New method to update the entire title bar (school year and time) ---
    def update_title_bar(self):
        """
        Met a jour le titre de la fenetre avec l'annee scolaire et la date/heure actuelles.
        Appelee au demarrage pour initialiser le titre.
        """
        print("DEBUG update_title_bar: Début de la fonction")
    
        
        now = datetime.now()
        current_date_time = now.strftime("%d/%m/%Y %H:%M:%S")

        title_string = f"   {current_date_time} - ijeery - Copyright 2025 by Iski Solution - +261 34 46 687 61 "
        print(f"DEBUG update_title_bar: Titre final = {title_string}")
    
        self.title(title_string)
        print("DEBUG update_title_bar: Titre appliqué")
        
    def update_title_bar_time_only(self):
        """
        Met a jour uniquement la partie de l'heure dans la barre de titre.
        Réutilise l'annee scolaire deja recuperee et stockee.
        """
           
        now = datetime.now()
        current_date_time = now.strftime("%d/%m/%Y %H:%M:%S")

        title_string = f"  {current_date_time}  - {self.nom_societe} - iJeery_V5.0 - Copyright 2025 by Iski Solution - Tél: +261 34 46 687 61"
        self.title(title_string)
    
        # Planifie la prochaine mise à jour dans 1 seconde
        self.after(1000, self.update_title_bar_time_only)

    def open_vente_window(self):
        """
        Ouvre une nouvelle fenêtre avec gestion par tabs (à la place de multiples fenêtres indépendantes).
        ✅ Utilise VenteTabManager pour gérer les tabs
        ✅ Max 10 tabs, +/X buttons pour ajouter/fermer des tabs
        """
        # Récupérer ou créer le manager de tabs unique
        if not hasattr(self, '_vente_tab_manager') or self._vente_tab_manager is None or not self._vente_tab_manager.winfo_exists():
            self._vente_tab_manager = VenteTabManager(
                master=self,
                id_user_connecte=self.id_user_connecte,
                app_reference=self
            )
            self._vente_tab_manager.lift()
            self._vente_tab_manager.focus_force()
        else:
            # Le manager existe déjà, ajouter un nouveau tab
            self._vente_tab_manager.add_new_tab()
            self._vente_tab_manager.lift()
            self._vente_tab_manager.focus_force()

    def create_menu_buttons(self):
        """Dynamically creates main menu buttons based on user authorization."""
        # Clear existing buttons before creating new ones (important for toggle_sidebar)
        # We only destroy buttons, not the submenu frames themselves
        for widget in self.nav_area_frame.winfo_children():
            if isinstance(widget, ctk.CTkButton):
                widget.destroy()
            # Also ensure submenu frames are forgotten if they were packed
            elif isinstance(widget, ctk.CTkFrame) and widget in [self.admin_submenu_frame, self.personnel_submenu_frame,
                                                                  self.tresorerie_submenu_frame, self.database_submenu_frame,
                                                                  self.examen_blanc_submenu_frame]:
                widget.pack_forget()


        # Always add Dashboard if authorized
        if "TABLEAU DE BORD" in self.authorized_menus:
            self.btn_dashboard = ctk.CTkButton(self.nav_area_frame, text="📊 TABLEAU DE BORD", corner_radius=10, height=60,
                                                fg_color="#268908", text_color="white", hover_color="#4CE01F",
                                                font=("Arial", 14), command=lambda: self.show_page(page_home))
            self.btn_dashboard.pack(pady=5, padx=10, fill="x")

        if "CHAT INTERNE" in self.authorized_menus:
            self.btn_dashboard = ctk.CTkButton(self.nav_area_frame, text="💬 CHAT INTERNE", corner_radius=10, height=60,
                                                fg_color="#A19407", text_color="white", hover_color="#cad256",
                                                font=("Arial", 14), command=lambda: self.show_page(PageChat))
            self.btn_dashboard.pack(pady=5, padx=10, fill="x")

        # Comemerciale (Parent Menu)
        admin_submenus_exist = any(menu.startswith("Article Liste") or
                                   menu.startswith("Client") or
                                   menu.startswith("Fournisseur") or
                                   menu.startswith("Magasin") or
                                   menu.startswith("Ventes") or
                                   menu.startswith("Ventes par Dépôt") or
                                   menu.startswith("Liste Facture") or
                                   menu.startswith("Facturation") or
                                   menu.startswith("Stock") or
                                   menu.startswith("Stock Livraison") or
                                   menu.startswith("Mouvement d'article") or
                                   menu.startswith("Suivi Commande") or
                                   menu.startswith("Prx d'article") or
                                   menu.startswith("Livraison Client") or
                                   menu.startswith("Mouvement Stock") or
                                   menu.startswith("Liste mouvements") # Menu pour consulter les listes de mouvements d'articles
                                   for menu in self.authorized_menus)

        if admin_submenus_exist:
            self.btn_administration = ctk.CTkButton(self.nav_area_frame, text="🛒 COMMERCIALE", corner_radius=10, height=60,
                                                     fg_color="#034787", text_color="white", hover_color="#0565c9",
                                                     font=("Arial", 14), command=self.show_commerciale_submenu)
            self.btn_administration.pack(pady=5, padx=10, fill="x")

        # Personnel (Parent Menu)
        personnel_submenus_exist = any(menu.startswith("Liste Personnel") or
                                       menu.startswith("Avance 15e") or
                                       menu.startswith("Avance Spéciale") or
                                       menu.startswith("Fonction") or
                                       menu.startswith("Présence") or
                                       menu.startswith("Nouveau SB") or
                                       menu.startswith("Salaire Base") or
                                       menu.startswith("Salaire Horaire") or
                                       menu.startswith("Absence") or
                                       menu.startswith("Présence") or
                                       menu.startswith("Paramètres Personnel") or
                                       menu.startswith("page_salaireBase_") or
                                       menu.startswith("page_personnel") or
                                       menu.startswith("PageTauxHoraire") or
                                       menu.startswith("PageValidationSalaire")
                                       for menu in self.authorized_menus)

        if personnel_submenus_exist:
            self.btn_personnel = ctk.CTkButton(self.nav_area_frame, text="👥 PERSONNEL", corner_radius=10, height=60,
                                                fg_color="#036C6B", text_color="white", hover_color="#2ec8cd",
                                                font=("Arial", 14), command=self.show_personnel_submenu)
            self.btn_personnel.pack(pady=5, padx=10, fill="x")

        # Trésorerie (Parent Menu)
        tresorerie_submenus_exist = any(menu.startswith("Caisse") or
                                        menu.startswith("Banque") or
                                        menu.startswith("Ajout Banque") or
                                        menu.startswith("Transfert Banque") or
                                        menu.startswith("Transfert Caisse") or
                                        menu.startswith("Etat de Dépenses") or
                                        menu.startswith("Decaissement") or # Added Decaissement
                                        menu.startswith("DecaissementBq") or
                                        menu.startswith("Encaissement") or # Added Encaissement
                                        menu.startswith("EncaissementBq") or
                                        menu.startswith("Client à Payer") or
                                        menu.startswith("Fournisseur à Payer") or
                                        menu.startswith("Catégorie") # Added Catégorie
                                        for menu in self.authorized_menus)

        if tresorerie_submenus_exist:
            self.btn_tresorerie = ctk.CTkButton(self.nav_area_frame, text="💰 TRESORERIE", corner_radius=10, height=60,
                                                 fg_color="#87035D", text_color="white", hover_color="#c936c2",
                                                 font=("Arial", 14), command=self.show_tresorerie_submenu)
            self.btn_tresorerie.pack(pady=5, padx=10, fill="x")

        # Base de données (Parent Menu)
        database_submenus_exist = any(menu.startswith("Autorisation") or
                                       menu.startswith("Sauvegarde") or
                                       menu.startswith("Utilisateurs") or
                                       menu.startswith("Evenements") or
                                       menu.startswith("PageParamReseau") or
                                       menu.startswith("Créer Base de donnees")or
                                       menu.startswith("Export Table")or
                                       menu.startswith("PageBaseListe") or
                                       menu.startswith("Autorisation Admin") or
                                       menu.startswith("Menu") or
                                       menu.startswith("Init DB")
                                       for menu in self.authorized_menus)

        if database_submenus_exist:
            self.btn_database = ctk.CTkButton(self.nav_area_frame, text="🗄️BASE DE DONNEES", corner_radius=10, height=60,
                                               fg_color="#874903", text_color="white", hover_color="#d7956e",
                                               font=("Arial", 14), command=self.show_database_submenu)
            self.btn_database.pack(pady=5, padx=10, fill="x")           

        # Examen Blanc (Parent Menu)
        examen_blanc_submenus_exist = any(menu.startswith("Matière EB") or
                                          menu.startswith("Etudiant EB") or
                                          menu.startswith("Notes EB") or
                                          menu.startswith("Délibération EB") or
                                          menu.startswith("Résultat EB")
                                          for menu in self.authorized_menus)

        if examen_blanc_submenus_exist:
            self.btn_examen_blanc = ctk.CTkButton(self.nav_area_frame, text="📚 EXAMEN BLANC", corner_radius=10, height=60,
                                                   fg_color="#034787", text_color="white", hover_color="#0565c9",
                                                   font=("Arial", 14), command=self.show_examen_blanc_submenu)
            self.btn_examen_blanc.pack(pady=5, padx=10, fill="x")
        self._apply_menu_responsive_styles()

    @staticmethod
    def _clamp(value, min_value, max_value):
        return max(min_value, min(max_value, int(value)))

    def _iter_submenu_frames(self):
        return [
            self.admin_submenu_frame,
            self.personnel_submenu_frame,
            self.tresorerie_submenu_frame,
            self.database_submenu_frame,
            self.examen_blanc_submenu_frame
        ]

    def _on_window_resize(self, event):
        if event.widget is not self:
            return

        now = time.time()
        if now - self._last_resize_update < 0.08:
            return

        self._last_resize_update = now
        self._apply_responsive_layout(event.width, event.height)

    def _update_responsive_metrics(self, width, height):
        width = max(1, width)
        height = max(1, height)
        scale_w = width / self._base_window_width
        scale_h = height / self._base_window_height
        self._ui_scale = max(0.80, min(1.45, min(scale_w, scale_h)))

        self._sidebar_expanded_width = self._clamp(width * 0.22, 170, 340)
        # Collapsed width must be 20% of expanded width
        self._sidebar_collapsed_width = self._clamp(self._sidebar_expanded_width * 0.20, 34, 80)
        self._main_button_height = self._clamp(60 * self._ui_scale, 44, 80)
        self._submenu_button_height = self._clamp(40 * self._ui_scale, 32, 56)
        self._main_font_size = self._clamp(14 * self._ui_scale, 11, 18)
        self._submenu_font_size = self._clamp(12 * self._ui_scale, 10, 15)
        self._toggle_font_size = self._clamp(16 * self._ui_scale, 12, 20)
        self._menu_pad_x = self._clamp(10 * self._ui_scale, 6, 16)
        self._menu_pad_y = self._clamp(5 * self._ui_scale, 3, 10)
        self._submenu_pad_x = self._clamp(5 * self._ui_scale, 3, 10)
        self._submenu_pad_y = self._clamp(2 * self._ui_scale, 1, 5)
        self._menu_corner_radius = self._clamp(10 * self._ui_scale, 8, 16)

    def _update_sidebar_logo(self):
        if not self.sidebar_title_label:
            return

        sidebar_width = self._sidebar_expanded_width if self.sidebar_expand else self._sidebar_collapsed_width

        if self._sidebar_logo_path:
            # Logo scales with both global UI scale and current sidebar width.
            width_factor = max(0.50, min(1.0, sidebar_width / float(self._sidebar_expanded_width or 1)))
            logo_size = (
                self._clamp(150 * self._ui_scale * width_factor, 85, 230),
                self._clamp(50 * self._ui_scale * width_factor, 28, 80)
            )
            if logo_size != self._sidebar_logo_size:
                try:
                    logo_image = ctk.CTkImage(
                        light_image=Image.open(self._sidebar_logo_path),
                        dark_image=Image.open(self._sidebar_logo_path),
                        size=logo_size
                    )
                    self.sidebar_title_label.configure(image=logo_image)
                    self.sidebar_title_label.image = logo_image
                    self._sidebar_logo_size = logo_size
                except Exception as e:
                    print(f"Erreur mise à jour logo responsive: {e}")
        else:
            title_font_size = self._clamp(25 * self._ui_scale, 18, 34)
            self.sidebar_title_label.configure(
                font=ctk.CTkFont(family="Britannic Bold", size=title_font_size, weight="bold")
            )

        if self.sidebar_title_label.winfo_manager() == "pack":
            self.sidebar_title_label.pack_configure(pady=(0, self._clamp(20 * self._ui_scale, 12, 28)))

    def _apply_menu_responsive_styles(self):
        main_font = ("Arial", self._main_font_size)
        submenu_font = ("Arial", self._submenu_font_size)
        submenu_frames = self._iter_submenu_frames()

        for widget in self.nav_area_frame.winfo_children():
            if isinstance(widget, ctk.CTkButton):
                widget.configure(
                    height=self._main_button_height,
                    font=main_font,
                    corner_radius=self._menu_corner_radius
                )
                if widget.winfo_manager() == "pack":
                    widget.pack_configure(padx=self._menu_pad_x, pady=self._menu_pad_y, fill="x")
            elif isinstance(widget, ctk.CTkFrame) and widget in submenu_frames:
                if widget.winfo_manager() == "pack":
                    widget.pack_configure(
                        padx=self._menu_pad_x,
                        pady=(0, self._menu_pad_y),
                        fill="x"
                    )
                for sub_widget in widget.winfo_children():
                    if isinstance(sub_widget, ctk.CTkButton):
                        sub_widget.configure(
                            height=self._submenu_button_height,
                            font=submenu_font,
                            corner_radius=max(8, self._menu_corner_radius - 2)
                        )
                        if sub_widget.winfo_manager() == "pack":
                            sub_widget.pack_configure(
                                padx=self._submenu_pad_x,
                                pady=self._submenu_pad_y,
                                fill="x"
                            )

    def _apply_responsive_layout(self, width=None, height=None):
        if width is None:
            width = self.winfo_width()
        if height is None:
            height = self.winfo_height()

        self._update_responsive_metrics(width, height)

        sidebar_width = self._sidebar_expanded_width if self.sidebar_expand else self._sidebar_collapsed_width
        self.sidebar_frame.configure(width=sidebar_width)
        self.content_frame.configure(corner_radius=self._clamp(15 * self._ui_scale, 8, 24))

        self.toggle_button.configure(
            font=("Arial", self._toggle_font_size),
            height=self._clamp(self._main_button_height * 0.85, 36, 68),
            corner_radius=self._menu_corner_radius
        )
        if self.toggle_button.winfo_manager() == "pack":
            self.toggle_button.pack_configure(
                padx=self._menu_pad_x,
                pady=self._clamp(10 * self._ui_scale, 6, 16),
                fill="x"
            )

        self.logout_button.configure(
            height=self._main_button_height,
            font=("Arial", self._main_font_size),
            corner_radius=self._menu_corner_radius
        )
        if self.logout_button.winfo_manager() == "pack":
            self.logout_button.pack_configure(
                padx=self._menu_pad_x,
                pady=self._clamp(10 * self._ui_scale, 6, 16),
                fill="x",
                side="bottom"
            )

        self._update_sidebar_logo()
        self._apply_menu_responsive_styles()

    def toggle_sidebar(self):
        if self.sidebar_expand:
            self.sidebar_frame.configure(width=self._sidebar_collapsed_width)
            self.toggle_button.configure(text="→")
            self.scrollable_frame.pack_forget()
            self.logout_button.pack_forget()
            self.sidebar_expand = False
            # Close any open submenus when collapsing
            self._close_all_submenus()
        else:
            self.sidebar_frame.configure(width=self._sidebar_expanded_width)
            self.toggle_button.configure(text="≡")           

            # Re-pack the scrollable frame
            self.scrollable_frame.pack(fill="both", expand=True)
            # Re-pack all main menu buttons (and potentially re-open submenu)
            self.create_menu_buttons() # This will re-create all main buttons in order

            # Re-open any currently open submenu if it was open before collapsing
            if self.current_submenu_open == "COMMERCIALE":
                self._repack_commerciale_submenu()
            elif self.current_submenu_open == "PERSONNEL":
                self._repack_personnel_submenu()
            elif self.current_submenu_open == "TRESORERIE":
                self._repack_tresorerie_submenu()
            elif self.current_submenu_open == "DATABASE":
                self._repack_database_submenu()
            elif self.current_submenu_open == "EXAMEN_BLANC":
                self._repack_examen_blanc_submenu()       

            self.logout_button.pack(
                pady=self._clamp(10 * self._ui_scale, 6, 16),
                padx=self._menu_pad_x,
                fill="x",
                side="bottom"
            )
            self.sidebar_expand = True
        self._apply_responsive_layout()

    def clear_dashboard(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def show_page(self, page_func):
        # Special handling for DBInitializerApp and other top-level windows
        if page_func in [DBInitializerApp, DatabaseManager]:
            self.open_top_level_window(page_func)
            return

        self.clear_dashboard()

        try:
            page_instance = None

            # ========================================
            # ✅ CAS SPÉCIAL POUR PageVente
            # ========================================
            if page_func == PageVente:
                if self.id_user_connecte is None:
                    messagebox.showerror(
                        "Erreur Session",
                        "Aucun utilisateur connecté détecté.\nImpossible d'ouvrir la page de vente."
                    )
                    return
    
                page_instance = page_func(
                    master=self.content_frame, 
                    id_user_connecte=self.id_user_connecte
                )
                print(f"✅ PageVente créée avec id_user_connecte={self.id_user_connecte}")

            elif page_func == PageVenteParMsin:
                if self.id_user_connecte is None:
                    messagebox.showerror(
                        "Erreur Session",
                        "Aucun utilisateur connecté détecté.\nImpossible d'ouvrir la page de vente."
                    )
                    return
    
                page_instance = page_func(
                    master=self.content_frame,
                    id_user_connecte=self.id_user_connecte
                )
                print(f"✅ PageVenteParMsin créée avec id_user_connecte={self.id_user_connecte}")
            
            elif page_func == PageLivraisonClient:
                if self.id_user_connecte is None:
                    messagebox.showerror(
                        "Erreur Session",
                        "Aucun utilisateur connecté détecté.\nImpossible d'ouvrir la page de vente."
                    )
                    return
    
                page_instance = page_func(
                    master=self.content_frame,
                    id_user_connecte=self.id_user_connecte
                )
                print(f"✅ PageLivraisonClient créée avec id_user_connecte={self.id_user_connecte}")
                
            elif page_func == PageTransfertBanque:
                if self.id_user_connecte is None:
                    messagebox.showerror(
                        "Erreur Session",
                        "Aucun utilisateur connecté détecté.\nImpossible d'ouvrir la page de vente."
                    )
                    return
    
                page_instance = page_func(
                    master=self.content_frame,
                    id_user_connecte=self.id_user_connecte
                )
                print(f"✅ PageTransferbBanque créée avec id_user_connecte={self.id_user_connecte}")
                
            elif page_func == PageTransfertCaisse:
                if self.id_user_connecte is None:
                    messagebox.showerror(
                        "Erreur Session",
                        "Aucun utilisateur connecté détecté.\nImpossible d'ouvrir la page de vente."
                    )
                    return
    
                page_instance = page_func(
                    master=self.content_frame,
                    id_user_connecte=self.id_user_connecte
                )
                print(f"✅ PageTransfertCaisse créée avec id_user_connecte={self.id_user_connecte}")
                
            elif page_func == PageAVQ:
                if self.id_user_connecte is None:
                    messagebox.showerror(
                        "Erreur Session",
                        "Aucun utilisateur connecté détecté.\nImpossible d'ouvrir la page de vente."
                    )
                    return
    
                page_instance = page_func(
                    master=self.content_frame,
                    iduser=self.id_user_connecte
                )
                print(f"✅ PageAVQ créée avec id_user_connecte={self.id_user_connecte}")
                
            elif page_func == FenetreAvanceSpec:
                if self.id_user_connecte is None:
                    messagebox.showerror(
                        "Erreur Session",
                        "Aucun utilisateur connecté détecté.\nImpossible d'ouvrir la page de vente."
                    )
                    return
    
                page_instance = page_func(
                    master=self.content_frame,
                    iduser=self.id_user_connecte
                )
                print(f"✅ FenetreAvanceSpec créée avec id_user_connecte={self.id_user_connecte}")    

            # ========================================
            # ✅ CAS SPÉCIAL POUR PageChat
            # ========================================
            elif page_func == PageChat:
                if self.id_user_connecte is None:
                    messagebox.showerror(
                        "Erreur Session",
                        "Aucun utilisateur connecté détecté.\nImpossible d'ouvrir le chat."
                    )
                    return
            
                # Créer les données de session pour le chat
                chat_session_data = {
                    "iduser": self.id_user_connecte,
                    "username": self.session_data.get('username', 'Utilisateur')
                }
            
                page_instance = page_func(
                    master=self.content_frame,
                    session_data=chat_session_data
                )
                print(f"✅ PageChat créée avec iduser={self.id_user_connecte}")

            # ========================================
            # ✅ CAS SPÉCIAL POUR PageInfoMouvementStock
            # ========================================
            elif page_func == PageInfoMouvementStock:
                if self.id_user_connecte is None:
                    messagebox.showerror(
                        "Erreur Session",
                        "Aucun utilisateur connecté détecté.\nImpossible d'ouvrir la page."
                    )
                    return
    
                page_instance = page_func(
                    self.content_frame, 
                    iduser=self.id_user_connecte
                )
                print(f"✅ PageInfoMouvementStock créée avec iduser={self.id_user_connecte}")

            # ========================================
            # Cas spéciaux existants
            # ========================================
            elif page_func in [PageTauxHoraire, PageSalaireBase]:
                page_instance = page_func(master=self.content_frame, app_root=self)
            
            elif page_func == PageFacturation:
                if self.id_user_connecte is None:
                    messagebox.showerror("Erreur Session", "Utilisateur non connecté.")
                    return
                page_instance = page_func(
                    master=self.content_frame, 
                    id_user_connecte=self.id_user_connecte
                )
                print(f"✅ PageFacturation créée avec id_user_connecte={self.id_user_connecte}")

            # ========================================
            # Autres pages (essais multiples)
            # ========================================
            else:
                try:
                    # Essai 1: Avec master, db_conn, session_data
                    page_instance = page_func(self.content_frame, db_conn=self.db_conn, session_data=self.session_data)
                except TypeError:
                    try:
                        # Essai 2: Avec master, db_conn (sans session_data)
                        page_instance = page_func(self.content_frame, db_conn=self.db_conn)
                    except TypeError:
                        # Essai 3: Avec master seulement
                        page_instance = page_func(self.content_frame)

            if page_instance:
                if isinstance(page_instance, ctk.CTkToplevel):
                    page_instance.lift()
                    page_instance.focus_force()
                    self.grab_set()
                    self.wait_window(page_instance)
                    self.grab_release()
                else:
                    page_instance.pack(expand=True, fill="both")
            else:
                raise Exception("Impossible de créer l'instance de la page avec les arguments disponibles.")

        except Exception as e:
            messagebox.showerror("Erreur de page", f"Impossible d'afficher la page. Erreur: {e}")
            self.show_page_not_authorized(f"Erreur d'affichage: {e}")
            import traceback
            traceback.print_exc()
    
    def open_top_level_window(self, page_func):
        # Ferme la fenêtre existante si elle est déjà ouverte
        if hasattr(self, '_toplevel_window') and self._toplevel_window is not None and self._toplevel_window.winfo_exists():
            self._toplevel_window.destroy()
            self._toplevel_window = None

        # Instancie la fenêtre Toplevel
        # Si page_activitePrix a besoin de paramètres spécifiques, ajoutez-les ici
        if page_func == PageActivitePrix: # Si vous avez un cas spécifique pour elle
            self._toplevel_window = page_func(master=self, db_conn=self.db_conn, session_data=self.session_data, db_config=self.db_config)
            # ^ Supprimez 'app_root=self' ici
        else:
            self._toplevel_window = page_func(master=self, app_root=self) # Gardez-le pour les autres si nécessaire

        # Rend la fenêtre modale et lui donne le focus
        self._toplevel_window.grab_set()
        self._toplevel_window.focus_force()
        self._toplevel_window.transient(self) # Fait en sorte que la Toplevel soit toujours au-dessus de la fenêtre parente
        self.wait_window(self._toplevel_window) # Attend la fermeture de la fenêtre Toplevel
        self._toplevel_window.grab_release()
        self._toplevel_window = None # Réinitialise la référence après fermeture



    def show_page_not_authorized(self, message="Acces non autorise."):
        self.clear_dashboard()
        unauthorized_label = ctk.CTkLabel(self.content_frame, text=message, font=("Arial", 20, "bold"), text_color="red")
        unauthorized_label.pack(expand=True, pady=50)

    def logout(self):
        # Demander confirmation avant de déconnecter
        from tkinter import messagebox
        if messagebox.askyesno("Déconnexion", "Voulez-vous vraiment vous déconnecter ?"):
            # 1. Fermer la fenêtre actuelle du tableau de bord
            self.destroy()

            # 2. Supprimer le fichier de session pour forcer un nouveau login
            session_file_path = "session.json"
            if os.path.exists(session_file_path):
                try:
                    os.remove(session_file_path)
                except Exception as e:
                    print(f"Erreur lors de la suppression de la session : {e}")

            # 3. Lancer la fenêtre de connexion
            from page_login import LoginWindow
            login_app = LoginWindow()
            login_app.start()




    def _close_all_submenus(self):
        """Helper to close all submenus and reset layout of main buttons."""
        if self.current_submenu_open == "COMMERCIALE":
            self.admin_submenu_frame.pack_forget()
        elif self.current_submenu_open == "PERSONNEL":
            self.personnel_submenu_frame.pack_forget()
        elif self.current_submenu_open == "TRESORERIE":
            self.tresorerie_submenu_frame.pack_forget()
        elif self.current_submenu_open == "DATABASE":
            self.database_submenu_frame.pack_forget()
        elif self.current_submenu_open == "EXAMEN_BLANC":
            self.examen_blanc_submenu_frame.pack_forget()       

        # Reset the main menu button order by re-creating them
        self.create_menu_buttons()
        self.current_submenu_open = None

    # Helper method to repack main buttons correctly after a submenu
    def _repack_main_buttons_after_submenu(self, submenu_parent_btn, submenu_frame):
        """
        Ensures main buttons are correctly packed after a submenu is inserted.
        This is crucial for maintaining the correct order in the sidebar.
        """
        # Get all children in the nav_area_frame
        all_widgets = self.nav_area_frame.winfo_children()
        
        # Find the index of the submenu_parent_btn
        try:
            parent_btn_index = all_widgets.index(submenu_parent_btn)
        except ValueError:
            # If the parent button isn't found, something is wrong, just return
            return

        # Temporarily forget all widgets after the parent button
        for i in range(parent_btn_index + 1, len(all_widgets)):
            all_widgets[i].pack_forget()

        # Pack the submenu frame right after its parent button
        submenu_frame.pack(
            pady=(0, self._menu_pad_y),
            padx=self._menu_pad_x,
            fill="x",
            after=submenu_parent_btn
        )

        # Repack the forgotten widgets in their original order, after the submenu frame
        for i in range(parent_btn_index + 1, len(all_widgets)):
            # Skip the submenu frame itself if it's in the list
            if all_widgets[i] is not submenu_frame:
                all_widgets[i].pack(
                    pady=self._menu_pad_y,
                    padx=self._menu_pad_x,
                    fill="x"
                )

    def show_commerciale_submenu(self):
        if self.current_submenu_open == "COMMERCIALE":  # ✅ CORRECTION ICI
            self._close_all_submenus()
            return
        self._close_all_submenus()

        # Ensure the administration button is packed in its correct place
        if hasattr(self, 'btn_administration'):
            pass

        self._repack_main_buttons_after_submenu(self.btn_administration, self.admin_submenu_frame)

        for widget in self.admin_submenu_frame.winfo_children():
            widget.destroy()

        # Dynamically add COMMERCIALE sub-menu buttons based on authorized menus
        if "Article Liste" in self.authorized_menus:
            btn_articleListe = ctk.CTkButton(self.admin_submenu_frame, text="📦 Article Liste", corner_radius=10, height=40,
                                      fg_color="#034787", text_color="white", hover_color="#0565c9",
                                      font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["page_listeArticle"]))
            btn_articleListe.pack(pady=2, padx=5, fill="x")

        if "Client" in self.authorized_menus:
            btn_client = ctk.CTkButton(self.admin_submenu_frame, text="👤 Client", corner_radius=10, height=40,
                                      fg_color="#034787", text_color="white", hover_color="#0565c9",
                                      font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageClient"]))
            btn_client.pack(pady=2, padx=5, fill="x")

        if "Fournisseur" in self.authorized_menus:
            btn_fournisseur = ctk.CTkButton(self.admin_submenu_frame, text="🏭 Fournisseur", corner_radius=10, height=40,
                                          fg_color="#034787", text_color="white", hover_color="#0565c9",
                                          font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageFournisseur"]))
            btn_fournisseur.pack(pady=2, padx=5, fill="x")

        if "Magasin" in self.authorized_menus:
            btn_magasin = ctk.CTkButton(self.admin_submenu_frame, text="🏬 Magasin", corner_radius=10, height=40,
                                          fg_color="#034787", text_color="white", hover_color="#0565c9",
                                          font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageMagasin"]))
            btn_magasin.pack(pady=2, padx=5, fill="x")

        if "Ventes" in self.authorized_menus:
            btn_vente = ctk.CTkButton(self.admin_submenu_frame, text="📊 Ventes", corner_radius=10, height=40,
                                          fg_color="#034787", text_color="white", hover_color="#0565c9",
                                          font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageVente"]))
            btn_vente.pack(pady=2, padx=5, fill="x")

        if "Ventes par Dépôt" in self.authorized_menus:
            btn_vpd = ctk.CTkButton(
                self.admin_submenu_frame, 
                text="💰 Ventes par Dépôt", 
                corner_radius=10, 
                height=40,
                fg_color="#034787", 
                text_color="white", 
                hover_color="#0565c9",
                font=("Arial", 12), 
                command=self.open_vente_window  # <-- NOUVELLE MÉTHODE
            )
            btn_vpd.pack(pady=2, padx=5, fill="x")

        #if "Ventes par Dépôt" in self.authorized_menus:
            # btn_vpd = ctk.CTkButton(self.admin_submenu_frame, text="Ventes par Dépôt", corner_radius=10, height=40,
                                          # fg_color="#034787", text_color="white", hover_color="#0565c9",
                                          # font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["open_vente_window"]))
            # btn_vpd.pack(pady=2, padx=5, fill="x")
            
        if "Facturation" in self.authorized_menus:
            btn_facturation = ctk.CTkButton(self.admin_submenu_frame, text="📄 Facturation", corner_radius=10, height=40,
                                          fg_color="#034787", text_color="white", hover_color="#0565c9",
                                          font=("Arial", 12), command=self.open_vente_window)
            btn_facturation.pack(pady=2, padx=5, fill="x")

        if "Liste Facture" in self.authorized_menus:
            btn_listfact = ctk.CTkButton(self.admin_submenu_frame, text="📋 Liste Facture", corner_radius=10, height=40,
                                          fg_color="#034787", text_color="white", hover_color="#0565c9",
                                          font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageListeFacture"]))
            btn_listfact.pack(pady=2, padx=5, fill="x")

        if "Stock Article" in self.authorized_menus:
            btn_stock = ctk.CTkButton(self.admin_submenu_frame, text="📦 Stock Article", corner_radius=10, height=40,
                                      fg_color="#034787", text_color="white", hover_color="#0565c9",
                                      font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageStock"]))
            btn_stock.pack(pady=2, padx=5, fill="x")
            
        if "Stock Alerte" in self.authorized_menus:
            btn_alerte = ctk.CTkButton(self.admin_submenu_frame, text="⚠️ Stock Alerte", corner_radius=10, height=40,
                                      fg_color="#034787", text_color="white", hover_color="#0565c9",
                                      font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageStockAlerte"]))
            btn_alerte.pack(pady=2, padx=5, fill="x")
            
        if "Stock Livraison" in self.authorized_menus:
            btn_sl = ctk.CTkButton(self.admin_submenu_frame, text="🚚 Stock Livraion", corner_radius=10, height=40,
                                      fg_color="#034787", text_color="white", hover_color="#0565c9",
                                      font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageStockLivraison"]))
            btn_sl.pack(pady=2, padx=5, fill="x")

        if "Mouvement d'article" in self.authorized_menus:
            btn_ma = ctk.CTkButton(self.admin_submenu_frame, text="🔄 Mouvement d'article", corner_radius=10, height=40,
                                      fg_color="#034787", text_color="white", hover_color="#0565c9",
                                      font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageArticleMouvement"]))
            btn_ma.pack(pady=2, padx=5, fill="x")        

        if "Mouvement Stock" in self.authorized_menus:
            btn_movmtstock = ctk.CTkButton(self.admin_submenu_frame, text="📊 Mouvement Stock", corner_radius=10, height=40,
                                      fg_color="#034787", text_color="white", hover_color="#0565c9",
                                      font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageInfoMouvementStock"]))
            btn_movmtstock.pack(pady=2, padx=5, fill="x")

        # --- NOUVEAU MENU: Liste Mouvements ---
        # Menu permettant de consulter les listes des différents mouvements d'articles
        if "Liste mouvements" in self.authorized_menus:
            btn_liste_mvmt = ctk.CTkButton(self.admin_submenu_frame, text="📊 Liste Mouvements", corner_radius=10, height=40,
                                      fg_color="#034787", text_color="white", hover_color="#0565c9",
                                      font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageListeMouvement"]))
            btn_liste_mvmt.pack(pady=2, padx=5, fill="x")

        if "Suivi Commande" in self.authorized_menus:
            btn_sc = ctk.CTkButton(self.admin_submenu_frame, text="📍 Suivi Commande", corner_radius=10, height=40,
                                          fg_color="#034787", text_color="white", hover_color="#0565c9",
                                          font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageSuiviCommande"]))
            btn_sc.pack(pady=2, padx=5, fill="x")

        if "Prix d'article" in self.authorized_menus:
            btn_pda = ctk.CTkButton(self.admin_submenu_frame, text="💲 Prix d'article", corner_radius=10, height=40,
                                          fg_color="#034787", text_color="white", hover_color="#0565c9",
                                          font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PagePrixListe"]))
            btn_pda.pack(pady=2, padx=5, fill="x")
            
        if "Livraison Client" in self.authorized_menus:
            btn_lc = ctk.CTkButton(self.admin_submenu_frame, text="🚚 Livraison client", corner_radius=10, height=40,
                                          fg_color="#034787", text_color="white", hover_color="#0565c9",
                                          font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageLivraisonClient"]))
            btn_lc.pack(pady=2, padx=5, fill="x")

        if "Matières" in self.authorized_menus:
            btn_matiere = ctk.CTkButton(self.admin_submenu_frame, text="📚 Matières", corner_radius=10, height=40,
                                      fg_color="#034787", text_color="white", hover_color="#0565c9",
                                      font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageMatiere"]))
            btn_matiere.pack(pady=2, padx=5, fill="x")

        if "Notes" in self.authorized_menus:
            btn_notes = ctk.CTkButton(self.admin_submenu_frame, text="📝 Notes", corner_radius=10, height=40,
                                      fg_color="#0565c9", text_color="white", hover_color="#034787",
                                      font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["NoteManagementPage"]))
            btn_notes.pack(pady=2, padx=5, fill="x")

        if "Activités" in self.authorized_menus:
            btn_activite = ctk.CTkButton(self.admin_submenu_frame, text="🎯 Activités", corner_radius=10, height=40,
                                      fg_color="#0565c9", text_color="white", hover_color="#034787",
                                      font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageActivitePrix"]))
            btn_activite.pack(pady=2, padx=5, fill="x")

        if "Evènements" in self.authorized_menus:
            btn_evenement = ctk.CTkButton(self.admin_submenu_frame, text="📅 Evènements", corner_radius=10, height=40,
                                          fg_color="#0565c9", text_color="white", hover_color="#034787",
                                          font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageEvenement"]))
            btn_evenement.pack(pady=2, padx=5, fill="x")
   
        self.current_submenu_open = "COMMERCIALE"  # ✅ CORRECTION ICI
        self._apply_menu_responsive_styles()

    def _repack_commerciale_submenu(self):
        if hasattr(self, 'btn_administration') and self.btn_administration.winfo_ismapped():
            self._repack_main_buttons_after_submenu(self.btn_administration, self.admin_submenu_frame)
            self.show_commerciale_submenu()


    def show_personnel_submenu(self):
        if self.current_submenu_open == "PERSONNEL":
            self._close_all_submenus()
            return        
        self._close_all_submenus()
        
        # Ensure the personnel button is packed in its correct place
        if hasattr(self, 'btn_personnel'):
            pass # No direct pack_forget/pack here, rely on the helper

        self._repack_main_buttons_after_submenu(self.btn_personnel, self.personnel_submenu_frame)

        for widget in self.personnel_submenu_frame.winfo_children():
            widget.destroy()

        if "Liste Personnel" in self.authorized_menus:
            btn_personnel_main = ctk.CTkButton(self.personnel_submenu_frame, text="👥 Liste Personnel", corner_radius=10, height=40,
                                                 fg_color="#036C6B", text_color="white", hover_color="#2ec8cd",
                                                 font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageMainPersonnel"]))
            btn_personnel_main.pack(pady=2, padx=5, fill="x")

        if "Absence" in self.authorized_menus:
            btn_absence = ctk.CTkButton(self.personnel_submenu_frame, text="❌ Absence", corner_radius=10, height=40,
                                                 fg_color="#036C6B", text_color="white", hover_color="#2ec8cd",
                                                 font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageAbsence"]))
            btn_absence.pack(pady=2, padx=5, fill="x")
            
        if "Présence" in self.authorized_menus:
            btn_presence = ctk.CTkButton(self.personnel_submenu_frame, text="✅ Présence", corner_radius=10, height=40,
                                                 fg_color="#036C6B", text_color="white", hover_color="#2ec8cd",
                                                 font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PagePresence"]))
            btn_presence.pack(pady=2, padx=5, fill="x")

        if "Avance 15e" in self.authorized_menus:
            btn_avance15e = ctk.CTkButton(self.personnel_submenu_frame, text="💸 Avance 15e", corner_radius=10, height=40,
                                           fg_color="#036C6B", text_color="white", hover_color="#2ec8cd",
                                           font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageAVQ"]))
            btn_avance15e.pack(pady=2, padx=5, fill="x")

        if "Avance Spéciale" in self.authorized_menus:
            btn_avance_speciale = ctk.CTkButton(self.personnel_submenu_frame, text="💰 Avance Spéciale", corner_radius=10, height=40,
                                                 fg_color="#036C6B", text_color="white", hover_color="#2ec8cd",
                                                 font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["FenetreAvanceSpec"]))
            btn_avance_speciale.pack(pady=2, padx=5, fill="x")

        if "Fonction" in self.authorized_menus:
            btn_fonction = ctk.CTkButton(self.personnel_submenu_frame, text="👔 Fonction", corner_radius=10, height=40,
                                           fg_color="#036C6B", text_color="white", hover_color="#2ec8cd",
                                           font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageFonction"]))
            btn_fonction.pack(pady=2, padx=5, fill="x")

        if "Présence" in self.authorized_menus:
            btn_presence = ctk.CTkButton(self.personnel_submenu_frame, text="Présence", corner_radius=10, height=40,
                                           fg_color="#036C6B", text_color="white", hover_color="#2ec8cd",
                                           font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PagePresence"]))
            btn_presence.pack(pady=2, padx=5, fill="x")

        
        if "Salaire Horaire" in self.authorized_menus:
            btn_salaire_horaire = ctk.CTkButton(self.personnel_submenu_frame, text="⏰ Salaire Horaire", corner_radius=10, height=40,
                                                 fg_color="#036C6B", text_color="white", hover_color="#2ec8cd",
                                                 font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageEtatSalaireHoraire"]))
            btn_salaire_horaire.pack(pady=2, padx=5, fill="x")

        if "Paramètres Personnel" in self.authorized_menus: # This seems to map to page_settings
            btn_settings_personnel = ctk.CTkButton(self.personnel_submenu_frame, text="⚙️ Paramètres Personnel", corner_radius=10, height=40,
                                                    fg_color="#036C6B", text_color="white", hover_color="#2ec8cd",
                                                    font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["page_settings"]))
            btn_settings_personnel.pack(pady=2, padx=5, fill="x")
        
        # This button maps to page_salaireBase_, not page_settings, so it should be distinct
        if "Nouveau SB" in self.authorized_menus: 
            btn_salaire_base_ = ctk.CTkButton(self.personnel_submenu_frame, text="📋 Nouveau SB", corner_radius=10, height=40,
                                                   fg_color="#036C6B", text_color="white", hover_color="#2ec8cd",
                                                   font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageSalaireBase"]))
            btn_salaire_base_.pack(pady=2, padx=5, fill="x")
        
        if "Etat de Salaire" in self.authorized_menus: 
            btn_es_ = ctk.CTkButton(self.personnel_submenu_frame, text="📊 Etat de Salaire", corner_radius=10, height=40,
                                                   fg_color="#036C6B", text_color="white", hover_color="#2ec8cd",
                                                   font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageSalaireEtatSB"]))
            btn_es_.pack(pady=2, padx=5, fill="x")
            
        if "Etat de Salaire Horaire" in self.authorized_menus: 
            btn_esh_ = ctk.CTkButton(self.personnel_submenu_frame, text="📊 Etat de Salaire Horaire", corner_radius=10, height=40,
                                                   fg_color="#036C6B", text_color="white", hover_color="#2ec8cd",
                                                   font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageEtatSalaireHoraire"]))
            btn_esh_.pack(pady=2, padx=5, fill="x")

        if "Taux Horaire" in self.authorized_menus: 
            btn_salaire_base_ = ctk.CTkButton(self.personnel_submenu_frame, text="💲 Taux Horaire", corner_radius=10, height=40,
                                                   fg_color="#036C6B", text_color="white", hover_color="#2ec8cd",
                                                   font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageTauxHoraire"]))
            btn_salaire_base_.pack(pady=2, padx=5, fill="x")

        if "Paiement Salaire" in self.authorized_menus: 
            btn_salaire_base_ = ctk.CTkButton(self.personnel_submenu_frame, text="💳 Paiement Salaire", corner_radius=10, height=40,
                                                   fg_color="#036C6B", text_color="white", hover_color="#2ec8cd",
                                                   font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageValidationSalaire"]))
            btn_salaire_base_.pack(pady=2, padx=5, fill="x")

        self.current_submenu_open = "PERSONNEL"
        self._apply_menu_responsive_styles()
        # The repacking is handled by _repack_main_buttons_after_submenu, no need for the line below
        # self._repack_main_buttons_after_submenu(self.btn_personnel, self.personnel_submenu_frame)

    def show_tresorerie_submenu(self):
        if self.current_submenu_open == "TRESORERIE":
            self._close_all_submenus()
            return
        self._close_all_submenus()

        if hasattr(self, 'btn_tresorerie'):
            pass

        self._repack_main_buttons_after_submenu(self.btn_tresorerie, self.tresorerie_submenu_frame)

        for widget in self.tresorerie_submenu_frame.winfo_children():
            widget.destroy()

        if "Caisse" in self.authorized_menus:
            btn_caisse = ctk.CTkButton(self.tresorerie_submenu_frame, text="🏧 Caisse", corner_radius=10, height=40,
                                       fg_color="#87035D", text_color="white", hover_color="#c936c2",
                                       font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageCaisse"]))
            btn_caisse.pack(pady=2, padx=5, fill="x")

        if "Facture Liste" in self.authorized_menus:
            btn_facap = ctk.CTkButton(self.tresorerie_submenu_frame, text="💳 Client à Payer", corner_radius=10, height=40,
                                            fg_color="#87035D", text_color="white", hover_color="#c936c2",
                                            font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageFactureListe"]))
            btn_facap.pack(pady=2, padx=5, fill="x")
            
        if "Fournisseur Dettes" in self.authorized_menus:
            btn_fd = ctk.CTkButton(self.tresorerie_submenu_frame, text="💰 Fournisseur à Payer", corner_radius=10, height=40,
                                            fg_color="#87035D", text_color="white", hover_color="#c936c2",
                                            font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageFrsDette"]))
            btn_fd.pack(pady=2, padx=5, fill="x")

        if "Banque" in self.authorized_menus:
            btn_banque = ctk.CTkButton(self.tresorerie_submenu_frame, text="🏦 Banque", corner_radius=10, height=40,
                                       fg_color="#87035D", text_color="white", hover_color="#c936c2",
                                       font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageBanque"]))
            btn_banque.pack(pady=2, padx=5, fill="x")

        if "Ajout Banque" in self.authorized_menus:
            btn_ajoutbanque = ctk.CTkButton(self.tresorerie_submenu_frame, text="➕ Ajout Banque", corner_radius=10, height=40,
                                       fg_color="#87035D", text_color="white", hover_color="#c936c2",
                                       font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageBanqueNv"]))
            btn_ajoutbanque.pack(pady=2, padx=5, fill="x")

        if "Transfert Banque" in self.authorized_menus:
            btn_transfertbanque = ctk.CTkButton(self.tresorerie_submenu_frame, text="🔄 Transfert Banque", corner_radius=10, height=40,
                                       fg_color="#87035D", text_color="white", hover_color="#c936c2",
                                       font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageTransfertBanque"]))
            btn_transfertbanque.pack(pady=2, padx=5, fill="x")

        if "Transfert Caisse" in self.authorized_menus:
            btn_transfertcaisse = ctk.CTkButton(self.tresorerie_submenu_frame, text="🔄 Transfert Caisse", corner_radius=10, height=40,
                                       fg_color="#87035D", text_color="white", hover_color="#c936c2",
                                       font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageTransfertCaisse"]))
            btn_transfertcaisse.pack(pady=2, padx=5, fill="x")

        if "Decaissement" in self.authorized_menus:
            btn_decaissement = ctk.CTkButton(self.tresorerie_submenu_frame, text="💸 Décaissement", corner_radius=10, height=40,
                                            fg_color="#87035D", text_color="white", hover_color="#c936c2",
                                            font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageDecaissement"]))
            btn_decaissement.pack(pady=2, padx=5, fill="x")

        if "DecaissementBq" in self.authorized_menus:
            btn_decaissement = ctk.CTkButton(self.tresorerie_submenu_frame, text="DécaissementBq", corner_radius=10, height=40,
                                            fg_color="#87035D", text_color="white", hover_color="#c936c2",
                                            font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageDecaissementBq"]))
            btn_decaissement.pack(pady=2, padx=5, fill="x")

        if "Encaissement" in self.authorized_menus:
            btn_encaissement = ctk.CTkButton(self.tresorerie_submenu_frame, text="📥 Encaissement", corner_radius=10, height=40,
                                            fg_color="#87035D", text_color="white", hover_color="#c936c2",
                                            font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageEncaissement"]))
            btn_encaissement.pack(pady=2, padx=5, fill="x")

        if "EncaissementBq" in self.authorized_menus:
            btn_encaissement = ctk.CTkButton(self.tresorerie_submenu_frame, text="EncaissementBq", corner_radius=10, height=40,
                                            fg_color="#87035D", text_color="white", hover_color="#c936c2",
                                            font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageEncaissementBq"]))
            btn_encaissement.pack(pady=2, padx=5, fill="x")

        if "Etat de Dépenses" in self.authorized_menus:
            btn_depense = ctk.CTkButton(self.tresorerie_submenu_frame, text="📊 Etat de dépenses", corner_radius=10, height=40,
                                            fg_color="#87035D", text_color="white", hover_color="#c936c2",
                                            font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageDepParCat"]))
            btn_depense.pack(pady=2, padx=5, fill="x")

        if "Catégorie" in self.authorized_menus:
            btn_categorie = ctk.CTkButton(self.tresorerie_submenu_frame, text="🏷️ Catégorie", corner_radius=10, height=40,
                                            fg_color="#87035D", text_color="white", hover_color="#c936c2",
                                            font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageCategorie"]))
            btn_categorie.pack(pady=2, padx=5, fill="x")
        
        

        self.current_submenu_open = "TRESORERIE"
        self._apply_menu_responsive_styles()
        # self._repack_main_buttons_after_submenu(self.btn_tresorerie, self.tresorerie_submenu_frame)

    def show_database_submenu(self):
        if self.current_submenu_open == "DATABASE":
            self._close_all_submenus()
            return
        self._close_all_submenus()

        if hasattr(self, 'btn_database'):
            pass

        self._repack_main_buttons_after_submenu(self.btn_database, self.database_submenu_frame)

        for widget in self.database_submenu_frame.winfo_children():
            widget.destroy()

        if "Autorisation" in self.authorized_menus:
            btn_autorisation = ctk.CTkButton(self.database_submenu_frame, text="🔐 Autorisation", corner_radius=10, height=40,
                                             fg_color="#874903", text_color="white", hover_color="#d7956e",
                                             font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageAutorisation"]))
            btn_autorisation.pack(pady=2, padx=5, fill="x")

        if "Evenements" in self.authorized_menus:
            btn_events = ctk.CTkButton(self.database_submenu_frame, text="📅 Evenements", corner_radius=10, height=40,
                                             fg_color="#874903", text_color="white", hover_color="#d7956e",
                                             font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageEvenement"]))
            btn_events.pack(pady=2, padx=5, fill="x")    

        if "Sauvegarde" in self.authorized_menus:
            btn_sauvegarde = ctk.CTkButton(self.database_submenu_frame, text="💾 Sauvegarde", corner_radius=10, height=40,
                                           fg_color="#874903", text_color="white", hover_color="#d7956e",
                                           font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageSauvegarde"]))
            btn_sauvegarde.pack(pady=2, padx=5, fill="x")

        if "Utilisateurs" in self.authorized_menus:
            btn_users = ctk.CTkButton(self.database_submenu_frame, text="👨‍💻 Utilisateurs", corner_radius=10, height=40,
                                      fg_color="#874903", text_color="white", hover_color="#d7956e",
                                      font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageUsers"]))                                      
            btn_users.pack(pady=2, padx=5, fill="x")

        # Example of adding the "Paramètres de la BD" button
        if "Paramètres BD" in self.authorized_menus: # Make sure this menu item exists in your DB for permissions
            btn_db_settings = ctk.CTkButton(self.database_submenu_frame, text="⚙️ Paramètres BD", corner_radius=10, height=40,
                                            fg_color="#874903", text_color="white", hover_color="#d7956e",
                                            font=("Arial", 12), command=self.open_db_config_window)
            btn_db_settings.pack(pady=2, padx=5, fill="x")

        
        if "Paramètre Reseau" in self.authorized_menus:
            btn_users = ctk.CTkButton(self.database_submenu_frame, text="🌐 Paramètre Reseau", corner_radius=10, height=40,
                                      fg_color="#874903", text_color="white", hover_color="#d7956e",
                                      font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageParamReseau"]))                                      
            btn_users.pack(pady=2, padx=5, fill="x")

        if "Init DB" in self.authorized_menus:
            btn_users = ctk.CTkButton(self.database_submenu_frame, text="🔧 Init DB", corner_radius=10, height=40,
                                      fg_color="#874903", text_color="white", hover_color="#d7956e",
                                      font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["DBInitializerApp"]))                                      
            btn_users.pack(pady=2, padx=5, fill="x")
        
        if "Menu" in self.authorized_menus:
            btn_menu = ctk.CTkButton(self.database_submenu_frame, text="📋 Menu", corner_radius=10, height=40,
                                      fg_color="#874903", text_color="white", hover_color="#d7956e",
                                      font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageMenu"]))                                      
            btn_menu.pack(pady=2, padx=5, fill="x")
       
        if "Base Liste" in self.authorized_menus:
            btn_bl = ctk.CTkButton(self.database_submenu_frame, text="📚 Base Liste", corner_radius=10, height=40,
                                      fg_color="#874903", text_color="white", hover_color="#d7956e",
                                      font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageBaseListe"]))                                      
            btn_bl.pack(pady=2, padx=5, fill="x")
            
        if "Autorisation Admin" in self.authorized_menus:
            btn_aa = ctk.CTkButton(self.database_submenu_frame, text="🔐 Autorisation Admin", corner_radius=10, height=40,
                                      fg_color="#874903", text_color="white", hover_color="#d7956e",
                                      font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageCodeAutorisation"]))                                      
            btn_aa.pack(pady=2, padx=5, fill="x")

        self.current_submenu_open = "DATABASE"
        self._apply_menu_responsive_styles()
        # self._repack_main_buttons_after_submenu(self.btn_database, self.database_submenu_frame)

    def show_examen_blanc_submenu(self):
        if self.current_submenu_open == "EXAMEN_BLANC":
            self._close_all_submenus()
            return
        self._close_all_submenus()

        if hasattr(self, 'btn_examen_blanc'):
            pass

        self._repack_main_buttons_after_submenu(self.btn_examen_blanc, self.examen_blanc_submenu_frame)

        for widget in self.examen_blanc_submenu_frame.winfo_children():
            widget.destroy()

        if "Matiere EB" in self.authorized_menus:
            btn_matiere_eb = ctk.CTkButton(self.examen_blanc_submenu_frame, text="Matiere EB", corner_radius=10, height=40,
                                           fg_color="#0565c9", text_color="white", hover_color="#034787",
                                           font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageMatiereEb"]))
            btn_matiere_eb.pack(pady=2, padx=5, fill="x")

        if "Etudiant EB" in self.authorized_menus:
            btn_etudiant_eb = ctk.CTkButton(self.examen_blanc_submenu_frame, text="Etudiant EB", corner_radius=10, height=40,
                                            fg_color="#0565c9", text_color="white", hover_color="#034787",
                                            font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageEtudiantExameBlanc"]))
            btn_etudiant_eb.pack(pady=2, padx=5, fill="x")

        if "Notes EB" in self.authorized_menus:
            btn_notes_eb = ctk.CTkButton(self.examen_blanc_submenu_frame, text="Notes EB", corner_radius=10, height=40,
                                         fg_color="#0565c9", text_color="white", hover_color="#034787",
                                         font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageNoteExamBlanc"]))
            btn_notes_eb.pack(pady=2, padx=5, fill="x")

        if "Déliberation EB" in self.authorized_menus:
            btn_deliberation_eb = ctk.CTkButton(self.examen_blanc_submenu_frame, text="Déliberation EB", corner_radius=10, height=40,
                                                fg_color="#0565c9", text_color="white", hover_color="#034787",
                                                font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageDeliberation"]))
            btn_deliberation_eb.pack(pady=2, padx=5, fill="x")
        
        if "Résultat EB" in self.authorized_menus:
            btn_resultat_eb = ctk.CTkButton(self.examen_blanc_submenu_frame, text="Résultat EB", corner_radius=10, height=40,
                                            fg_color="#0565c9", text_color="white", hover_color="#034787",
                                            font=("Arial", 12), command=lambda: self.show_page(self.page_mapping["PageResultatEB"]))
            btn_resultat_eb.pack(pady=2, padx=5, fill="x")


        self.current_submenu_open = "EXAMEN_BLANC"
        self._apply_menu_responsive_styles()
        # self._repack_main_buttons_after_submenu(self.btn_examen_blanc, self.examen_blanc_submenu_frame)


    # Repack methods for when sidebar is expanded
    # These methods are called by toggle_sidebar to re-display the correct submenu
    def _repack_commerciale_submenu(self):
        if hasattr(self, 'btn_administration') and self.btn_administration.winfo_ismapped():
            self._repack_main_buttons_after_submenu(self.btn_administration, self.admin_submenu_frame)
            # Re-create the submenu buttons as they were destroyed when sidebar collapsed
            self.show_commerciale_submenu() # This will recreate buttons and set current_submenu_open

    def _repack_personnel_submenu(self):
        if hasattr(self, 'btn_personnel') and self.btn_personnel.winfo_ismapped():
            self._repack_main_buttons_after_submenu(self.btn_personnel, self.personnel_submenu_frame)
            self.show_personnel_submenu()

    def _repack_tresorerie_submenu(self):
        if hasattr(self, 'btn_tresorerie') and self.btn_tresorerie.winfo_ismapped():
            self._repack_main_buttons_after_submenu(self.btn_tresorerie, self.tresorerie_submenu_frame)
            self.show_tresorerie_submenu()

    def _repack_database_submenu(self):
        if hasattr(self, 'btn_database') and self.btn_database.winfo_ismapped():
            self._repack_main_buttons_after_submenu(self.btn_database, self.database_submenu_frame)
            self.show_database_submenu()

    def _repack_examen_blanc_submenu(self):
        if hasattr(self, 'btn_examen_blanc') and self.btn_examen_blanc.winfo_ismapped():
            self._repack_main_buttons_after_submenu(self.btn_examen_blanc, self.examen_blanc_submenu_frame)
            self.show_examen_blanc_submenu()

   
# ==============================================================================
# VenteTabManager: Gère les tabs pour les multiples fenêtres de vente
# ==============================================================================
class VenteTabManager(ctk.CTkToplevel):
    """
    Fenêtre indépendante qui gère plusieurs tabs CTkTabview contenant chacun une PageVenteParMsin.
    - Max 10 tabs
    - +/X buttons pour ajouter/fermer des tabs
    """
    def __init__(self, master=None, id_user_connecte: Optional[int] = None, app_reference=None) -> None:
        super().__init__(master)
        
        self.title("Gestion des Ventes - Fenêtres Tabées")
        self.geometry("1350x850")
        self.id_user_connecte = id_user_connecte
        self.app_reference = app_reference
        self.tab_count = 0
        self.max_tabs = 10
        self.tab_list = []  # Liste des (tab_widget, page_vente_frame)
        
        # Après 100ms, amener la fenêtre au premier plan
        self.after(100, self.lift)
        
        # --- Header avec boutons manageurs des tabs ---
        # Place native CTkTabview header at the top; action buttons placed absolute top-right
        # Création des boutons d'action (placés en absolu plus bas)
        self.btn_close_tab = ctk.CTkButton(
            self,
            text="✕",
            width=32,
            height=28,
            font=("Arial", 12, "bold"),
            fg_color="#d32f2f",
            hover_color="#b71c1c",
            text_color="white",
            command=self.close_current_tab
        )

        self.btn_add_tab = ctk.CTkButton(
            self,
            text="+",
            width=32,
            height=28,
            font=("Arial", 12, "bold"),
            fg_color="green",
            hover_color="darkgreen",
            command=self.add_new_tab
        )

        # Position absolue en haut à droite — placement effectué après création du TabView
        # (pour éviter d'être recouvert par le widget TabView)
        
        # --- Tab View ---
        # Placer le TabView en ligne 0 pour que ses onglets natifs apparaissent en haut
        self.tabview = ctk.CTkTabview(self, width=1300, height=750)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=0, pady=(6,0))
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Après création du TabView, placer/monter les boutons d'action et aligner les onglets natifs
        try:
            self.btn_add_tab.place(relx=1.0, x=-6, y=6, anchor='ne')
            self.btn_close_tab.place(relx=1.0, x=-44, y=6, anchor='ne')
            # S'assurer qu'ils sont au-dessus
            self.btn_add_tab.lift()
            self.btn_close_tab.lift()
        except Exception:
            self.btn_add_tab.pack(side='top', anchor='ne', padx=2, pady=2)
            self.btn_close_tab.pack(side='top', anchor='ne', padx=2, pady=2)

        # Aligner la barre d'onglets native à gauche
        self.after(50, self._align_native_tabs_left)

        # Ajouter le premier tab
        self.add_new_tab()
        
    def add_new_tab(self):
        """Ajoute un nouveau tab avec une nouvelle instance de PageVenteParMsin."""
        if self.tab_count >= self.max_tabs:
            from tkinter import messagebox
            messagebox.showwarning(
                "Limite atteinte",
                f"Nombre maximum de {self.max_tabs} tabs atteint. Fermez un tab pour en ouvrir un nouveau."
            )
            return
        
        self.tab_count += 1
        tab_name = f"Vente({self.tab_count})"
        
        # Créer le tab dans le tabview
        new_tab = self.tabview.add(tab_name)
        
        # === DIRECTEMENT PageVenteParMsin (pas de wrapper ni header) ===
        from pages.page_venteParMsin import PageVenteParMsin
        
        page_vente_frame = PageVenteParMsin(
            master=new_tab,
            id_user_connecte=self.id_user_connecte
        )
        page_vente_frame.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Stocker la référence au tab et au frame
        tab_info = {
            'tab_name': tab_name,
            'tab_widget': new_tab,
            'page_frame': page_vente_frame
        }
        self.tab_list.append(tab_info)

        # (Utilisation des onglets natifs du CTkTabview — pas de boutons personnalisés à gauche)
        
        # Cacher le bouton + si on a atteint la limite
        if self.tab_count >= self.max_tabs:
            self.btn_add_tab.configure(state="disabled")
        
        # Sélectionner le nouveau tab (onglet natif)
        self.tabview.set(tab_name)
        # Mettre à jour le label du header (noop)
        self._update_header_label()

    # (removed custom left-tab helpers; using native CTkTabview tabs)
    
    def _update_header_label(self):
        """No-op: on n'affiche plus de texte dans l'en-tête (les onglets natifs du TabView sont visibles)."""
        return
    
    def close_current_tab(self):
        """Ferme le tab actuellement sélectionné ou ferme la fenêtre si c'est le dernier."""
        if len(self.tab_list) <= 1:
            # Fermer directement la fenêtre au lieu de montrer un message
            print("✅ Fermeture de la fenêtre Vente (dernier tab)")
            self.destroy()
            return
        
        # Récupérer le tab actuel
        current_tab_name = self.tabview.get()
        self.close_tab(current_tab_name)
    
    def close_tab(self, tab_name):
        """Ferme un tab spécifique par son nom."""
        if len(self.tab_list) <= 1:
            # Si on tente de fermer le dernier tab, fermer directement la fenêtre.
            try:
                self.destroy()
            except Exception:
                pass
            return
        
        # Chercher le tab à fermer
        tabs_to_remove = [t for t in self.tab_list if t['tab_name'] == tab_name]
        if tabs_to_remove:
            tab_info = tabs_to_remove[0]
            try:
                self.tabview.delete(tab_name)
                # (pas de bouton d'accès rapide personnalisé à détruire)

                self.tab_list.remove(tab_info)
                self.tab_count -= 1

                # Si des tabs restent, sélectionner le dernier et mettre à jour la surbrillance
                if self.tab_list:
                    new_active = self.tab_list[-1]['tab_name']
                    try:
                        self.tabview.set(new_active)
                    except Exception:
                        pass
                
                # Réactiver le bouton + si on n'a pas atteint la limite
                if self.tab_count < self.max_tabs:
                    self.btn_add_tab.configure(state="normal")
                
                print(f"✅ Tab '{tab_name}' fermé avec succès")
            except Exception as e:
                print(f"❌ Erreur lors de la fermeture du tab: {e}")

    def _align_native_tabs_left(self):
        """Tente d'aligner la barre d'onglets native du `CTkTabview` à gauche.

        Selon la version interne de customtkinter, le header peut être contenu
        dans différents widgets internes. On parcourt les enfants pour trouver
        celui contenant des boutons d'onglets puis on réajuste son placement.
        """
        try:
            # Recherche d'un widget interne ressemblant à la barre d'onglets
            for child in list(self.tabview.winfo_children()):
                try:
                    inner = child.winfo_children()
                    # heuristique : contient plusieurs boutons/labels => header
                    btn_like = [c for c in inner if 'Button' in str(type(c)) or 'CTkButton' in str(type(c)) or 'Segmented' in str(type(c))]
                    if len(btn_like) >= 1:
                        try:
                            # tenter de repositionner vers la gauche
                            child.pack_configure(anchor='w')
                            child.pack_configure(side='top', fill='x')
                        except Exception:
                            try:
                                child.grid_configure(sticky='w')
                            except Exception:
                                pass
                except Exception:
                    pass
        except Exception:
            pass

   
# Main execution block
if __name__ == "__main__":
    # Ensure there's a login_window.py with a LoginWindow class and a start method
    # This setup implies LoginWindow manages its own CTk() root.
    # It passes session_data to App upon successful login.

    # This part should be in your login_window.py or a separate entry point
    # to handle the login flow.
    # For now, let's simulate a successful login with dummy data
    # so you can run and test the App class directly.
    # In a real app, this `session_data` would come from `login_window.py`
    # after successful authentication.

    # Dummy session_data for testing purposes if you run app_main.py directly
    # REMOVE THIS FOR PRODUCTION - it's just to make App runnable for testing
    dummy_session_data = {
        'username': 'test_user',
        'role': 'administrateur',
        'menus': [
            ('TABLEAU DE BORD', True),
            ('Enseignant', True),
            ('Absence', True),
            ('Annee Scolaire', True),
            ('Bulletin', True),
            ('Classe', True),
            ('Droit', True),
            ('Ecolage', True),
            ('Inscription', True),
            ('Matieres', True),
            ('Notes', True),
            ('Evenements', True),
            ('Liste Personnel', True),
            ('Avance 15e', True),
            ('Avance Speciale', True),
            ('Fonction', True),
            ('Presence', True),
            ('Salaire Base', True),
            ('Salaire Horaire', True),
            ('Parametres Personnel', True),
            ('Salaire de Base', True),
            ('Caisse', True),
            ('Banque', True),
            ('Ajout Banque', True),
            ('Decaissement', True),
            ('DecaissementBq', True),
            ('Encaissement', True),
            ('EncaissementBq', True),
            ('Categorie', True),
            ('Autorisation', True),
            ('Sauvegarde', True),
            ('Utilisateurs', True),
            ('Creer Base de données', True),
            ('Export Table', True),
            ('Matiere EB', True),
            ('Etudiant EB', True),
            ('Notes EB', True),
            ('Deliberation EB', True),
            ('Resultat EB', True),
            ('Transfert Banque', True),
            ('Transfert Caisse', True),
            ("Parametres BD", True),
            ("Init DB", True),
            ("Activites", True),
            ("Etat de Depenses", True),
            ("PagePeriode", True),
            ("PageListeParSerie", True),
            ("Facture Liste", True),
            ("Paiement Fournisseur", True),
            ("Paiement Client", True),
            ("Noveau SB", True)
            # Add all menus here that your dummy user should see
        ],
        'user_id': 1
    }
    
    # Try to load session data from file
    session_file_path = "session.json"
    if os.path.exists(session_file_path):
        try:
            with open(session_file_path, 'r') as f:
                session_data = json.load(f)
            print("Session data loaded from file.")
        except json.JSONDecodeError as e:
            print(f"Error decoding session.json: {e}. Using dummy data.")
            session_data = dummy_session_data
    else:
        print("No session.json found. Using dummy data for testing.")
        session_data = dummy_session_data # Fallback to dummy if no session file

if __name__ == "__main__":
    # Vérifier s'il y a une session valide
    session_file_path = "session.json"
    if os.path.exists(session_file_path):
        try:
            with open(session_file_path, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            print("Session data loaded from file.")
            
            # Lancer l'application principale
            app = App(session_data)
            app.mainloop()
            
        except json.JSONDecodeError as e:
            print(f"Error decoding session.json: {e}. Launching login window.")
            try:
                os.remove(session_file_path)
            except:
                pass
            from page_login import LoginWindow
            login_app = LoginWindow()
            login_app.start()
    else:
        print("No session.json found. Launching login window.")
        from page_login import LoginWindow
        login_app = LoginWindow()
        login_app.start()
