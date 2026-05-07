import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
import json
from datetime import datetime
from tkcalendar import DateEntry
from PIL import Image, ImageTk
from resource_utils import get_config_path

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
        # Par défaut, l'unité est cochée et affichée au lancement
        if self.update_vars["Unite"].get() == "On":
            self.show_view("PageUnite")
        else:
            self.show_view(None)

    def create_sidebar(self):
        # Sidebar élargie pour afficher photo + infos
        self.sidebar_frame = ctk.CTkFrame(self, width=340, corner_radius=0, fg_color="#3b8ed4")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(8, weight=1)

        ctk.CTkLabel(
            self.sidebar_frame, 
            text="Article Détaillé", 
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), 
            text_color="white"
        ).grid(row=0, column=0, padx=20, pady=(20, 10))

        # ── Bloc photo + infos ───────────────────────────────────────────────
        self._sidebar_photo_ref = None
        self._lbl_article_info = {}

        info_card = ctk.CTkFrame(self.sidebar_frame, fg_color="#2f7fbe", corner_radius=10)
        info_card.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))
        info_card.grid_columnconfigure(0, weight=1)

        photo_box = ctk.CTkFrame(info_card, fg_color="#e9f2fb", corner_radius=10, height=170)
        photo_box.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 8))
        photo_box.grid_propagate(False)
        self._sidebar_photo_box = photo_box

        self._sidebar_photo_label = tk.Label(photo_box, text="Chargement…", bg="#e9f2fb", fg="#1f3a57")
        self._sidebar_photo_label.place(relx=0.5, rely=0.5, anchor="center")

        details_frame = ctk.CTkFrame(info_card, fg_color="transparent")
        details_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        details_frame.grid_columnconfigure(1, weight=1)

        def _add_row(r, title):
            ctk.CTkLabel(
                details_frame, text=f"{title} :",
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color="#eaf4ff"
            ).grid(row=r, column=0, sticky="w", padx=(0, 6), pady=2)
            lbl = ctk.CTkLabel(
                details_frame, text="—",
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color="white",
                wraplength=220, justify="left"
            )
            lbl.grid(row=r, column=1, sticky="w", pady=2)
            return lbl

        self._lbl_article_info["id"] = _add_row(0, "ID")
        self._lbl_article_info["code"] = _add_row(1, "Code")
        self._lbl_article_info["designation"] = _add_row(2, "Désignation")
        self._lbl_article_info["categorie"] = _add_row(3, "Catégorie")

        # Charger les infos article dès l'init si on a un id
        self.after(100, self._refresh_sidebar_article_details)

        self.update_vars = {
            "Unite": tk.StringVar(value="On"),
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
        
        # Checkbox Unité (toujours cochée et inactive)
        self.checkbox_unite = ctk.CTkCheckBox(
            self.sidebar_frame, 
            text="Mise à jour Unité", 
            command=lambda: self.on_checkbox_click("Unite", "PageUnite"),
            variable=self.update_vars["Unite"], 
            onvalue="On", 
            offvalue="Off",
            state="disabled",
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
        # Demandé: cacher totalement les cases à cocher
        self.checkbox_unite.grid_remove()
        self.checkbox_fournisseur.grid_remove()

    def _get_photos_folder(self):
        """
        Même logique que la liste article:
        - si serveur distant → \\IP\\photos
        - sinon → <cwd>/photos (fallback)
        - possibilité de surcharger via config.json (photos_path / photo_path / photos.path)
        """
        try:
            with open(get_config_path('config.json')) as f:
                config = json.load(f)
            configured_path = (
                config.get("photos_path")
                or config.get("photo_path")
                or config.get("photos", {}).get("path")
            )
            if configured_path:
                return configured_path

            server_cfg = config.get("server", {})
            server_ip = (
                server_cfg.get("ip")
                or config.get("server_ip")
                or config.get("ip_server")
                or config.get("database", {}).get("host")
                or "localhost"
            )
        except Exception:
            server_ip = "localhost"

        if str(server_ip).lower() in ("localhost", "127.0.0.1"):
            return os.path.join(os.getcwd(), "photos")
        return rf"\\{server_ip}\photos"

    def _normalize_article_id(self, article_id):
        if article_id is None:
            return ""
        s = str(article_id).strip()
        if not s:
            return ""
        if s.endswith(".0"):
            s = s[:-2]
        return s

    def _find_photo_path(self, idarticle):
        article_id = self._normalize_article_id(idarticle)
        if not article_id:
            return None
        photo_dir = self._get_photos_folder()
        for ext in (".jpg", ".jpeg", ".png", ".gif", ".bmp"):
            candidate = os.path.join(photo_dir, f"{article_id}{ext}")
            if os.path.exists(candidate):
                return candidate
        return None

    def _refresh_sidebar_article_details(self):
        """Met à jour photo + infos dans la sidebar gauche."""
        if not self.initial_idarticle:
            return
        article_id = self._normalize_article_id(self.initial_idarticle)
        if not article_id:
            return

        # 1) Infos texte (DB)
        code = designation = categorie = "—"
        try:
            conn = None
            if self.db_conn:
                conn = self.db_conn
            else:
                with open(get_config_path('config.json')) as f:
                    config = json.load(f)
                    db_config = config['database']
                conn = psycopg2.connect(
                    host=db_config['host'],
                    user=db_config['user'],
                    password=db_config['password'],
                    database=db_config['database'],
                    port=db_config['port']
                )
            cur = conn.cursor()
            cur.execute("""
                SELECT a.idarticle, a.designation, COALESCE(c.designationcat,'')
                FROM tb_article a
                LEFT JOIN tb_categoriearticle c ON a.idca = c.idca
                WHERE a.idarticle = %s
                LIMIT 1
            """, (article_id,))
            row = cur.fetchone()
            if row:
                designation = row[1] or "—"
                categorie = row[2] or "—"
            # code article (prendre le 1er code unité)
            cur.execute("""
                SELECT codearticle
                FROM tb_unite
                WHERE idarticle = %s
                ORDER BY codearticle
                LIMIT 1
            """, (article_id,))
            r2 = cur.fetchone()
            if r2 and r2[0]:
                code = r2[0]
            try:
                cur.close()
            except Exception:
                pass
            if conn is not None and conn is not self.db_conn:
                conn.close()
        except Exception:
            pass

        self._lbl_article_info["id"].configure(text=article_id)
        self._lbl_article_info["code"].configure(text=code)
        self._lbl_article_info["designation"].configure(text=designation)
        self._lbl_article_info["categorie"].configure(text=categorie)

        # 2) Photo (dossier photos)
        photo_path = self._find_photo_path(article_id)

        if not photo_path:
            try:
                self._sidebar_photo_label.configure(image="")
            except Exception:
                pass
            self._sidebar_photo_label.configure(text="Aucune photo")
            return

        try:
            img = Image.open(photo_path).convert("RGB")
            img.thumbnail((260, 160), Image.Resampling.LANCZOS)
            self._sidebar_photo_ref = ImageTk.PhotoImage(img)
            self._sidebar_photo_label.configure(image=self._sidebar_photo_ref, text="")
        except Exception:
            try:
                self._sidebar_photo_label.configure(image="")
            except Exception:
                pass
            self._sidebar_photo_label.configure(text="Photo indisponible")

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