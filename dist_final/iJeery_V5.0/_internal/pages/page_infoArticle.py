import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
import json
from datetime import datetime
from tkcalendar import DateEntry

# Ajout pour forcer les chemins d'import
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))  # Dossier courant
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pages'))  # Dossier 'pages/'

# ====================================================================
# FONCTION D'IMPORT ADAPTATIVE
# ====================================================================

def adaptive_import(module_names, class_name, fallback_class=None):
    for module_name in module_names:
        try:
            module = __import__(module_name, fromlist=[class_name])
            imported_class = getattr(module, class_name, None)
            if imported_class:
                print(f"✓ {class_name} importée depuis {module_name}")
                return imported_class
        except ImportError as e:
            print(f"⚠ Tentative d'import de {class_name} depuis {module_name} échouée: {e}")
            continue
    
    print(f"❌ Impossible d'importer {class_name}, utilisation de la classe de substitution")
    return fallback_class

# ====================================================================
# IMPORTS ADAPTATIFS DES PAGES
# ====================================================================

# Fallbacks
class PageArticleFrsFallback(ctk.CTkFrame):
    def __init__(self, master, initial_idarticle=None):
        super().__init__(master, fg_color="white")
        ctk.CTkLabel(self, text="Fournisseurs non disponible").pack(pady=80)

class PageUniteFallback(ctk.CTkFrame):
    def __init__(self, master, db_connector=None, initial_idarticle=None):
        super().__init__(master, fg_color="white")
        ctk.CTkLabel(self, text="Unité non disponible").pack(pady=80)

# Imports adaptatifs
PageArticleFrs = adaptive_import(
    ["pages.page_articleFrs", "page_articleFrs", ".pages.page_articleFrs", ".page_articleFrs"],
    "PageArticleFrs",
    PageArticleFrsFallback
)

PageUnite = adaptive_import(
    ["pages.page_unite", "page_unite", ".pages.page_unite", ".page_unite"],
    "PageUnite",
    PageUniteFallback
)

# Vérifier imports
ARTICLE_FRS_AVAILABLE = PageArticleFrs != PageArticleFrsFallback
UNITE_AVAILABLE = PageUnite != PageUniteFallback

print(f"\n{'='*60}")
print("STATUT DES IMPORTS DANS page_infoArticle.py")
print(f"PageArticleFrs disponible : {ARTICLE_FRS_AVAILABLE}")
print(f"PageUnite disponible : {UNITE_AVAILABLE}")
print(f"{'='*60}\n")

# DB Connectors (si besoin)
UniteDBConnector = None  # Exemple, adapte si besoin

class PageInfoArticle(ctk.CTkFrame):
    def __init__(self, master, db_conn=None, session_data=None, initial_idarticle=None):
        super().__init__(master)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.db_conn = db_conn
        self.session_data = session_data
        self.initial_idarticle = str(initial_idarticle) if initial_idarticle is not None else None
        
        # DBConnectors (exemple)
        self.db_connectors = {
            'unite': UniteDBConnector,
            'fournisseur': None,
        }
        
        self.views = {}
        self.current_view_name = None 
        
        self.create_sidebar()
        self.create_main_container()
        
        self._initialize_views()
        self.show_view(None) 

    def create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color="#3b8ed4")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(
            self.sidebar_frame, 
            text="Article Détaillé", 
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), 
            text_color="white"
        ).grid(row=0, column=0, padx=20, pady=(20, 10))

        self.update_vars = {
            "Unite": tk.StringVar(value="Off"),
            "Fournisseur": tk.StringVar(value="Off")
        }
        
        checkbox_config = {
            "fg_color": "#2980b9",
            "hover_color": "#3498db",
            "checkmark_color": "white",
            "text_color": "white",
            "font": ctk.CTkFont(family="Segoe UI", size=13),
            "corner_radius": 5
        }
        
        # Checkbox Unité
        self.checkbox_unite = ctk.CTkCheckBox(
            self.sidebar_frame, 
            text="Mise à jour Unité", 
            command=lambda: self.on_checkbox_click("Unite", "PageUnite"),
            variable=self.update_vars["Unite"], 
            onvalue="On", 
            offvalue="Off",
            **checkbox_config
        )
        self.checkbox_unite.grid(row=1, column=0, padx=15, pady=(15, 5), sticky="w")

        # Checkbox Fournisseur
        self.checkbox_fournisseur = ctk.CTkCheckBox(
            self.sidebar_frame, 
            text="Fournisseurs", 
            command=lambda: self.on_checkbox_click("Fournisseur", "PageArticleFrs"),
            variable=self.update_vars["Fournisseur"], 
            onvalue="On", 
            offvalue="Off",
            **checkbox_config
        )
        self.checkbox_fournisseur.grid(row=2, column=0, padx=15, pady=5, sticky="w")

    def create_main_container(self):
        self.right_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(1, weight=1)

        # En-tête bleu
        self.title_frame = ctk.CTkFrame(self.right_panel, corner_radius=8, fg_color="#3b8ed4", height=60)
        self.title_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 10))
        self.title_frame.grid_propagate(False)
    
        title_text = f"Détail de l'Article" + (f" - ID: {self.initial_idarticle}" if self.initial_idarticle else "")
        ctk.CTkLabel(self.title_frame, text=title_text, font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color="white").pack(expand=True)
    
        # Conteneur des vues
        self.view_container = ctk.CTkFrame(self.right_panel, fg_color="white")
        self.view_container.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.view_container.grid_rowconfigure(0, weight=1)
        self.view_container.grid_columnconfigure(0, weight=1)
    
        # Message d'accueil
        self.welcome_frame = ctk.CTkFrame(self.view_container, fg_color="white")
        self.welcome_frame.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(self.welcome_frame, text="Sélectionnez une vue dans la sidebar", font=("Arial", 16)).grid(row=0, column=0, pady=100)

    def _initialize_views(self):
        print("Initialisation des vues...")
        
        # Page Unité
        try:
            self.views["PageUnite"] = PageUnite(
                self.view_container,
                db_connector=self.db_connectors.get('unite'),
                initial_idarticle=self.initial_idarticle
            )
            print("✓ PageUnite chargée avec succès")
        except Exception as e:
            print(f"❌ Erreur chargement PageUnite : {e}")
            import traceback; traceback.print_exc()
            error = ctk.CTkFrame(self.view_container, fg_color="#ffebee")
            ctk.CTkLabel(error, text=f"Erreur PageUnite\n{str(e)}", text_color="red").pack(pady=40)
            self.views["PageUnite"] = error

        # Page Fournisseurs
        try:
            self.views["PageArticleFrs"] = PageArticleFrs(
                self.view_container,
                initial_idarticle=self.initial_idarticle
            )
            print("✓ PageArticleFrs chargée")
        except Exception as e:
            print(f"❌ Erreur PageArticleFrs : {e}")
            error = ctk.CTkFrame(self.view_container, fg_color="#fff3cd")
            ctk.CTkLabel(error, text=f"Erreur Fournisseurs\n{str(e)}", text_color="#856404").pack(pady=40)
            self.views["PageArticleFrs"] = error
        
        print("Vues disponibles :", list(self.views.keys()))

    def show_view(self, view_name):
        print("\n" + "="*50)
        print(f"show_view appelée pour : {view_name}")
        print("Contenu actuel de self.views :")
        for k, v in self.views.items():
            print(f"  {k:18} → {type(v).__name__ if v is not None else 'None'}")
        print("="*50 + "\n")
        
        if hasattr(self, 'welcome_frame') and self.welcome_frame is not None:
            self.welcome_frame.grid_forget()
        
        for frame in self.views.values():
            if frame is not None:
                frame.grid_forget()
        
        if view_name and view_name in self.views:
            frame_to_show = self.views[view_name]
            if frame_to_show is not None:
                frame_to_show.grid(row=0, column=0, sticky="nsew")
                self.current_view_name = view_name
            else:
                print(f"Impossible d'afficher {view_name} : frame est None")
        else:
            if hasattr(self, 'welcome_frame'):
                self.welcome_frame.grid(row=0, column=0, sticky="nsew")
            self.current_view_name = None

    def on_checkbox_click(self, checkbox_key, view_class_name):
        current_state = self.update_vars[checkbox_key].get()
        
        for key, var in self.update_vars.items():
            if key != checkbox_key:
                var.set("Off")
        
        if current_state == "On":
            print(f"Tentative d'affichage de la vue: {view_class_name}")
            self.show_view(view_class_name)
        else:
            self.show_view(None)

# Test de la page
if __name__ == "__main__":
    ctk.set_appearance_mode("light") 
    ctk.set_default_color_theme("blue")
    
    app = ctk.CTk()
    app.title("Test PageInfoArticle")
    app.geometry("1200x700")
    
    app.grid_columnconfigure(0, weight=1)
    app.grid_rowconfigure(0, weight=1)

    page_frame = PageInfoArticle(master=app, db_conn=None, initial_idarticle="1009")
    page_frame.grid(row=0, column=0, sticky="nsew")

    app.mainloop()