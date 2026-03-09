# page_configDb.py - Version corrigée pour chercher config.json à la racine
import customtkinter as ctk
from tkinter import messagebox
import psycopg2
import threading
import sys
import os
import json

# Ajout du chemin vers le dossier parent pour les imports si nécessaire
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_config_path():
    """Détermine le chemin du config.json compatible avec l'EXE compilé."""
    if getattr(sys, 'frozen', False):
        # Si c'est un EXE, le dossier racine est celui où se trouve l'EXE
        dossier_racine = os.path.dirname(sys.executable)
    else:
        # Si c'est en mode développement (VS Code)
        dossier_actuel = os.path.dirname(os.path.abspath(__file__))
        dossier_racine = os.path.dirname(dossier_actuel)
    
    return os.path.join(dossier_racine, 'config.json')

def load_json_config():
    """Charge les paramètres de connexion directement depuis config.json."""
    config_path = get_config_path()
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            return config['database']
    except FileNotFoundError:
        messagebox.showerror("Erreur Fatale", f"Fichier 'config.json' non trouvé.\nCherché dans : {config_path}")
        return None
    except (KeyError, json.JSONDecodeError) as e:
        messagebox.showerror("Erreur de format", f"Erreur dans le fichier config.json : {e}")
        return None

class DatabaseConfig:
    """Singleton pour gérer la connexion de manière centralisée via config.json"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DatabaseConfig, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._config = load_json_config()
            self._connection = None
            self._initialized = True
            
            if self._config:
                self.verifier_table_config()

    def verifier_table_config(self):
        """Initialise la table tb_configdb si nécessaire."""
        try:
            temp_conn = psycopg2.connect(**self._config)
            cursor = temp_conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tb_configdb (
                    id SERIAL PRIMARY KEY,
                    dbname VARCHAR(50),
                    username VARCHAR(50),
                    password VARCHAR(100),
                    host VARCHAR(100),
                    port INTEGER
                )
            """)
            
            cursor.execute("SELECT COUNT(*) FROM tb_configdb")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO tb_configdb (dbname, username, password, host, port)
                    VALUES (%s, %s, %s, %s, %s)
                """, (self._config['database'], self._config['user'], 
                     self._config['password'], self._config['host'], self._config['port']))
            
            temp_conn.commit()
            cursor.close()
            temp_conn.close()
        except Exception as e:
            print(f"Erreur d'initialisation SQL : {e}")

    def get_connection(self):
        """Retourne une connexion basée sur la configuration centralisée."""
        try:
            if not self._config: 
                self._config = load_json_config()
            
            if self._connection is None or self._connection.closed:
                self._connection = psycopg2.connect(**self._config)
            return self._connection
        except psycopg2.Error as e:
            messagebox.showerror("Erreur", f"Connexion DB impossible : {e}")
            return None

    def update_config(self, dbname, username, password, host, port):
        """Met à jour le fichier config.json à la racine et la table SQL."""
        new_params = {
            'host': host,
            'user': username,
            'password': password,
            'database': dbname,
            'port': int(port)
        }
        try:
            # Écriture dans config.json à la racine
            config_path = get_config_path()
            with open(config_path, 'w') as f:
                json.dump({'database': new_params}, f, indent=4)
            
            self._config = new_params
            
            # Mise à jour synchronisée de la table tb_configdb
            temp_conn = psycopg2.connect(**self._config)
            cursor = temp_conn.cursor()
            cursor.execute("""
                UPDATE tb_configdb 
                SET dbname=%s, username=%s, password=%s, host=%s, port=%s 
                WHERE id = (SELECT id FROM tb_configdb LIMIT 1)
            """, (dbname, username, password, host, port))
            temp_conn.commit()
            temp_conn.close()
            return True
        except Exception as e:
            messagebox.showerror("Erreur de sauvegarde", f"Erreur : {e}")
            return False

    def get_config(self):
        return self._config if self._config else load_json_config()

# Instance globale pour tout le projet
db_config = DatabaseConfig()

class PageConfigDB(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.frame = ctk.CTkFrame(self, fg_color="transparent")
        self.frame.pack(expand=True, fill="both", padx=20, pady=20)

        ctk.CTkLabel(self.frame, text="Configuration Base de Données", font=("Arial", 22, "bold")).grid(row=0, column=0, columnspan=2, pady=20)

        # Création des champs
        self.entry_host = self.creer_champ("Hôte (IP) :", 1)
        self.entry_port = self.creer_champ("Port :", 2)
        self.entry_database = self.creer_champ("Nom de la Base :", 3)
        self.entry_username = self.creer_champ("Utilisateur :", 4)
        self.entry_password = self.creer_champ("Mot de passe :", 5, show="*")

        btn_frame = ctk.CTkFrame(self.frame)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=20)

        ctk.CTkButton(btn_frame, text="Tester Connexion", fg_color="#f39c12", command=self.test_connection).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Enregistrer Tout", fg_color="#2ecc71", command=self.save_config).pack(side="left", padx=5)

        self.load_fields()

    def creer_champ(self, label_text, row, show=None):
        ctk.CTkLabel(self.frame, text=label_text).grid(row=row, column=0, padx=10, pady=5, sticky="w")
        entry = ctk.CTkEntry(self.frame, width=250, show=show)
        entry.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
        return entry

    def load_fields(self):
        config = db_config.get_config()
        if config:
            self.entry_host.insert(0, config.get('host', ''))
            self.entry_port.insert(0, str(config.get('port', '')))
            self.entry_database.insert(0, config.get('database', ''))
            self.entry_username.insert(0, config.get('user', ''))
            self.entry_password.insert(0, config.get('password', ''))

    def test_connection(self):
        try:
            conn = psycopg2.connect(
                host=self.entry_host.get(),
                port=int(self.entry_port.get()),
                database=self.entry_database.get(),
                user=self.entry_username.get(),
                password=self.entry_password.get()
            )
            conn.close()
            messagebox.showinfo("Succès", "La connexion fonctionne !")
        except Exception as e:
            messagebox.showerror("Échec", f"Impossible de se connecter : {e}")

    def save_config(self):
        if db_config.update_config(
            self.entry_database.get(),
            self.entry_username.get(),
            self.entry_password.get(),
            self.entry_host.get(),
            self.entry_port.get()
        ):
            messagebox.showinfo("Succès", "Paramètres sauvegardés à la racine et en DB !")

if __name__ == '__main__':
    root = ctk.CTk()
    root.geometry("500x450")
    PageConfigDB(root).pack(expand=True, fill="both")
    root.mainloop()