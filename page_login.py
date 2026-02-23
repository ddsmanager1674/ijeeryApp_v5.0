# -*- coding: utf-8 -*-
import customtkinter as ctk
from tkinter import messagebox
import psycopg2
from PIL import Image
import os
import json
import sys
import time
import threading
import subprocess

# Importation de la classe ConfigDataBase
# Assurez-vous que configDataBase.py est dans le même dossier
from configDataBase import ConfigDataBase 
from resource_utils import get_resource_path, get_config_path, get_session_path, safe_file_read

def resource_path(relative_path):
    """DEPRECATED: Utiliser get_resource_path() depuis resource_utils.py"""
    return get_resource_path(relative_path)

# Configuration globale de customtkinter
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# Ajouter le repertoire parent au chemin Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.configure(fg_color="#E5E5E5") # Gris clair (LightGray)
        
        # Configuration de la fenetre
        self.title("ijeery - Connexion")
        self.geometry("400x500")
        self.resizable(False, False)
        
        # Variables pour stocker les identifiants
        self.username = ctk.StringVar()
        self.password = ctk.StringVar()
        self.remember_me = ctk.BooleanVar()
        
        self.setup_ui()
        
        # Centrer la fenetre
        self.center_window()
        
        # Variable pour contrôler la fermeture
        self.app_launched = False
        
    def center_window(self):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        x = (screen_width - 400) // 2
        y = (screen_height - 500) // 2
        
        self.geometry(f"400x500+{x}+{y}")

    def get_authorized_menus(self, idfonction):
        """Recupere les menus autorises pour une fonction donnee"""
        conn = None
        try:
            conn = self.connect_db()
            if not conn:
                return []
                
            cursor = conn.cursor()
            cursor.execute("""
                SELECT m.designationmenu, m.page
                FROM tb_menu m
                JOIN tb_autorisation a ON m.id = a.idmenu
                WHERE a.idfonction = %s
                ORDER BY m.designationmenu
            """, (idfonction,))
            
            menus = cursor.fetchall()
            return menus
            
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors de la recuperation des menus : {err}")
            return []
        finally:
            if conn:
                conn.close()

    def save_user_session(self, user_data, menus):
        """Sauvegarde les informations de session de l'utilisateur"""
        session_data = {
            "user_id": user_data[0],
            "username": user_data[1],
            "fonction_id": user_data[2],
            "fonction_name": user_data[3],
            "menus": [(menu[0], menu[1]) for menu in menus]
        }
        
        try:
            session_path = get_session_path()
            with open(session_path, "w", encoding='utf-8') as f:
                json.dump(session_data, f, indent=4, ensure_ascii=False)
            print(f"✓ Session sauvegardée avec succès: {session_path}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde de la session : {e}")

    def connect_db(self):
        try:
            # Lecture robuste du fichier config avec chemin absolu
            config_path = get_config_path('config.json')
            config_content, encoding = safe_file_read(config_path)
            config = json.loads(config_content)
            db_config = config['database']

            conn = psycopg2.connect(
                host=db_config['host'],
                user=db_config['user'],
                password=db_config['password'],
                database=db_config['database'],
                port=db_config['port']  
            )
            return conn
        except psycopg2.Error as err:
            messagebox.showerror("Erreur de connexion", f"Erreur : {err}")
            return None
        except FileNotFoundError:
            messagebox.showerror("Erreur", f"Fichier config.json introuvable à: {get_config_path('config.json')}")
            return None
        except KeyError as err:
            messagebox.showerror("Erreur", f"Cle manquante dans config.json : {err}")
            return None
        except Exception as err:
            messagebox.showerror("Erreur", f"Erreur de configuration : {err}")
            return None
            
    def show_error(self, message):
        self.error_label.configure(text=message)
        self.after(3000, lambda: self.error_label.configure(text=""))

    def launch_main_app_safely(self, session_data):
        """Lance l'application principale de manière sécurisée"""
        def run_app():
            try:
                # Attendre un petit délai pour s'assurer que la session est sauvegardée
                time.sleep(0.5)
                
                # Créer un nouveau processus Python pour l'application principale
                script_path = os.path.join(os.path.dirname(__file__), "app_main.py")
                if os.path.exists(script_path):
                    # Lancer app_main.py comme un processus séparé
                    subprocess.Popen([sys.executable, script_path])
                    
                    # Fermer la fenêtre de login après un délai
                    self.after(1000, self.close_login)
                else:
                    # Si app_main.py n'existe pas, essayer l'import direct avec plus de précautions
                    self.after(500, lambda: self.import_and_run_app(session_data))
                    
            except Exception as e:
                self.after(0, lambda: self.handle_app_error(e))
        
        # Lancer dans un thread séparé
        threading.Thread(target=run_app, daemon=True).start()

    def import_and_run_app(self, session_data):
        
        """Import et lancement direct de l'application"""
        try:
            # Import tardif pour éviter les conflits
            import importlib.util
            
            # Vérifier si app_main peut être importé
            spec = importlib.util.find_spec("app_main")
            if spec is None:
                raise ImportError("Module app_main non trouvé")
            
            from app_main import App

            # Détruire la fenêtre de login AVANT de créer une nouvelle instance Tk
            # Evite d'avoir deux instances de Tkinter dans le même processus
            try:
                self.withdraw()
                self.update_idletasks()
            except Exception:
                pass
            try:
                self.destroy()
            except Exception:
                pass

            # Créer l'application principale (nouvelle instance Tk)
            main_app = App(session_data)
            
            # Marquer que l'app est lancée
            self.app_launched = True
            
            # Configurer la fermeture
            original_destroy = main_app.destroy
            def safe_destroy():
                try:
                    original_destroy()
                except:
                    pass
                finally:
                    # Fermer l'application de login
                    try:
                        self.quit()
                    except:
                        pass
                    # Forcer la fermeture si nécessaire
                    os._exit(0)
            
            main_app.destroy = safe_destroy
            main_app.protocol("WM_DELETE_WINDOW", safe_destroy)
            
            # Lancer l'application principale
            main_app.mainloop()
            
        except Exception as e:
            self.handle_app_error(e)

    def handle_app_error(self, error):
        """Gère les erreurs lors du lancement de l'application"""
        self.deiconify()  # Rendre visible la fenêtre de login
        self.app_launched = False
        messagebox.showerror("Erreur", f"Erreur lors de l'ouverture de l'application : {error}")
        print(f"Erreur détaillée : {error}")
        import traceback
        traceback.print_exc()

    def close_login(self):
        """Ferme la fenêtre de login de manière sécurisée"""
        try:
            self.quit()
            self.destroy()
        except:
            pass
        
    def login(self):
        username = self.username.get().strip()
        password = self.password.get().strip()
        
        if not username or not password:
            self.show_error("Veuillez remplir tous les champs")
            return
            
        conn = self.connect_db()
        if not conn:
            return
            
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.iduser, u.username, u.idfonction, f.designationfonction, u.active
                FROM tb_users u
                JOIN tb_fonction f ON u.idfonction = f.idfonction
                WHERE u.username = %s AND u.password = %s
            """, (username, password))
            
            user = cursor.fetchone()
            
            if user and user[4]:  # Verifie si l'utilisateur existe et est actif
                menus = self.get_authorized_menus(user[2])
                
                session_data = {
                    "user_id": user[0],
                    "username": user[1],
                    "fonction_id": user[2],
                    "fonction_name": user[3],
                    "menus": [(menu[0], menu[1]) for menu in menus]
                }
                
                # Sauvegarder la session
                self.save_user_session(user, menus)
                
                # Désactiver le bouton de connexion pour éviter les clics multiples
                self.login_button.configure(state="disabled")
                
                # Lancer l'application principale de manière sécurisée
                self.launch_main_app_safely(session_data)
                
            else:
                self.show_error("Nom d'utilisateur ou mot de passe incorrect")
                
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors de la connexion : {err}")
        finally:
            if conn:
                conn.close()

    # Nouvelle méthode pour ouvrir la fenêtre de configuration
    def open_database_config(self):
        # Ouvre la configuration sans fermer la page login
        config_window = ConfigDataBase()
        config_window.focus_force()
        config_window.mainloop()

    def start(self):
        self.mainloop()

    def setup_ui(self):
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)

         # Logo
        try:
            logo_path = resource_path("image/logo 3.png")
            self.logo_image = ctk.CTkImage(
                light_image=Image.open(logo_path),
                dark_image=Image.open(logo_path),
                size=(120, 50)
            )
            self.logo_label = ctk.CTkLabel(main_frame, image=self.logo_image, text="")
            self.logo_label.pack(pady=(0, 20))
        
        except Exception as e:
            print(f"Erreur chargement logo: {e}")
            self.logo_label = ctk.CTkLabel(
                main_frame, 
                text="iJeery_V5.0", 
                font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold")
            )
            self.logo_label.pack(pady=(0, 20))

        input_frame = ctk.CTkFrame(main_frame)
        input_frame.pack(fill="x", padx=20, pady=10)

        username_label = ctk.CTkLabel(
            input_frame,
            text="Nom d'utilisateur:",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        username_label.pack(anchor="w", pady=(0, 5))

        self.username_entry = ctk.CTkEntry(
            input_frame,
            textvariable=self.username,
            width=300
        )
        self.username_entry.pack(pady=(0, 10))

        password_label = ctk.CTkLabel(
            input_frame,
            text="Mot de passe:",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        password_label.pack(anchor="w", pady=(0, 5))

        self.password_entry = ctk.CTkEntry(
            input_frame,
            textvariable=self.password,
            show="*",
            width=300
        )
        self.password_entry.pack(pady=(0, 10))

        self.remember_checkbox = ctk.CTkCheckBox(
            input_frame,
            text="Se souvenir de moi",
            variable=self.remember_me
        )
        self.remember_checkbox.pack(pady=(0, 10))

        # Stocker la référence du bouton de connexion
        self.login_button = ctk.CTkButton(
            input_frame,
            text="Se connecter",
            command=self.login,
            width=300
        )
        self.login_button.pack(pady=(10, 0))
        
        # Nouveau bouton "DataBaseLogin"
        self.database_login_button = ctk.CTkButton(
            input_frame,
            text="DataBaseLogin",
            command=self.open_database_config,
            fg_color="gray",
            hover_color="orange",  # Change la couleur en orange au survol
            width=300
        )
        self.database_login_button.pack(pady=(10, 0))

        self.error_label = ctk.CTkLabel(
            input_frame,
            text="",
            text_color="red",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.error_label.pack(pady=(10, 0))

        self.bind("<Return>", lambda event: self.login())

if __name__ == "__main__":
    login_window = LoginWindow()
    login_window.start()
