import customtkinter as ctk
from tkinter import filedialog, messagebox
import subprocess
import os
import datetime
import psycopg2
import threading
import json
import sys
from resource_utils import get_config_path, safe_file_read


# Ensure the parent directory is in the Python path for absolute imports
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
        """Loads database configuration from 'config.json'."""
        try:
            config_path = get_config_path('config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('database')
        except Exception as e:
            print(f"Error loading config: {e}")
            return None

    def connect(self):
        """Establishes a new database connection."""
        if self.db_params is None:
            return False
        try:
            self.conn = psycopg2.connect(
                host=self.db_params['host'],
                user=self.db_params['user'],
                password=self.db_params['password'],
                database=self.db_params['database'],
                port=self.db_params['port'],
                client_encoding='UTF8'
            )
            self.cursor = self.conn.cursor()
            return True
        except Exception as e:
            print(f"Error connecting: {e}")
            return False

    def get_connection(self):
        """Returns the database connection if connected, otherwise attempts to connect."""
        if self.conn is None or self.conn.closed:
            if self.connect():
                return self.conn
            else:
                return None
        return self.conn

    def close(self):
        """Closes the database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

# Instantiate DatabaseManager
db_manager = DatabaseManager()

class PageSauvegarde(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        
        # Récupération des paramètres de connexion depuis le db_manager (config.json)
        config = db_manager.db_params
        if config:
            self.DB_NAME = config.get('database', "dbijeery")
            self.DB_USER = config.get('user', "postgres")
            self.DB_PASSWORD = config.get('password', "root")
            self.DB_HOST = config.get('host', "localhost")
            self.DB_PORT = str(config.get('port', "5432"))
        else:
            # Fallback par défaut si config.json est introuvable
            self.DB_NAME = "dbijeery"
            self.DB_USER = "postgres"
            self.DB_PASSWORD = "root"
            self.DB_HOST = "localhost"
            self.DB_PORT = "5432"

        # Chemins complets vers pg_dump et pg_restore
        self.pg_dump_path = r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe"
        self.pg_restore_path = r"C:\Program Files\PostgreSQL\16\bin\pg_restore.exe"

        self.setup_ui()

    def setup_ui(self):
        # Frame principal avec padding
        self.pack(expand=True, fill="both", padx=20, pady=20)

        # Titre
        title_label = ctk.CTkLabel(self, text="Gestion de la Base de Données", 
                                 font=("Arial", 20, "bold"))
        title_label.pack(pady=(0, 20))

        # Frame pour le fichier
        file_frame = ctk.CTkFrame(self)
        file_frame.pack(fill="x", padx=10, pady=10)

        lbl_fichier = ctk.CTkLabel(file_frame, text="Fichier à restaurer :")
        lbl_fichier.pack(anchor="w", pady=(0, 5))

        entry_frame = ctk.CTkFrame(file_frame)
        entry_frame.pack(fill="x")

        self.entry_chemin = ctk.CTkEntry(entry_frame, width=350)
        self.entry_chemin.pack(side="left", padx=(0, 10))

        btn_parcourir = ctk.CTkButton(entry_frame, text="Parcourir", width=100,
                                    command=self.parcourir_fichier)
        btn_parcourir.pack(side="right")

        # Barre de progression et label
        progress_frame = ctk.CTkFrame(self)
        progress_frame.pack(fill="x", padx=10, pady=20)

        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(fill="x", pady=(0, 5))
        self.progress_bar.set(0)

        self.lbl_progression = ctk.CTkLabel(progress_frame, text="")
        self.lbl_progression.pack()

        # Boutons d'action
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=10, pady=10)

        btn_restaurer = ctk.CTkButton(button_frame, text="Restaurer la base",
                                    fg_color="#207561", hover_color="#165e4d",
                                    width=200, height=40,
                                    command=self.restaurer_bdd)
        btn_restaurer.pack(pady=10)

        btn_sauvegarder = ctk.CTkButton(button_frame, text="Sauvegarder la base",
                                      fg_color="#207561", hover_color="#165e4d",
                                      width=200, height=40,
                                      command=self.sauvegarder_bdd)
        btn_sauvegarder.pack(pady=10)

    def get_nomesociete(self):
        """Récupère le nom de la société depuis la table tb_infosociete."""
        conn = db_manager.get_connection()
        if not conn:
            return "SOCIETE"
        
        try:
            # Utilisation d'un curseur avec 'with' pour une fermeture automatique
            with conn.cursor() as cursor:
                cursor.execute("SELECT nomsociete FROM tb_infosociete LIMIT 1;")
                result = cursor.fetchone()
                if result and result[0]:
                    # Remplacer les espaces par des underscores pour le nom de fichier
                    return str(result[0]).replace(" ", "_")
                return "SOCIETE"
        except Exception as e:
            print(f"Erreur lors de la récupération du nom société : {e}")
            return "SOCIETE"

    def sauvegarder_bdd(self):
        # Récupération dynamique du nom
        nomsociete = self.get_nomesociete()
        now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        default_filename = f"SAUVE-{nomsociete}-{now}.backup"

        file_path = filedialog.asksaveasfilename(
            defaultextension=".backup",
            filetypes=[("Fichiers de sauvegarde", "*.backup")],
            initialfile=default_filename
        )
        if not file_path:
            return

        try:
            os.environ['PGPASSWORD'] = self.DB_PASSWORD
            subprocess.run([
                self.pg_dump_path,
                "-U", self.DB_USER,
                "-h", self.DB_HOST,
                "-p", self.DB_PORT,
                "-F", "c",
                "-f", file_path,
                self.DB_NAME
            ], check=True)
            messagebox.showinfo("Succès", f"Sauvegarde effectuée avec succès :\n{os.path.basename(file_path)}")
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde :\n{e}")
        except FileNotFoundError:
            messagebox.showerror("Erreur", f"pg_dump introuvable à :\n{self.pg_dump_path}")
        finally:
            if 'PGPASSWORD' in os.environ:
                del os.environ['PGPASSWORD']

    def terminate_all_db_connections(self, dbname_to_terminate):
        conn_sys = None
        try:
            conn_sys = psycopg2.connect(
                dbname="postgres",
                user=self.DB_USER,
                password=self.DB_PASSWORD,
                host=self.DB_HOST,
                port=self.DB_PORT
            )
            conn_sys.autocommit = True
            cursor_sys = conn_sys.cursor()

            query = f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{dbname_to_terminate}'
              AND pg_stat_activity.pid <> pg_backend_pid();
            """
            cursor_sys.execute(query)
            return True
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de fermer les connexions : {e}")
            return False
        finally:
            if conn_sys:
                conn_sys.close()

    def restaurer_bdd(self):
        file_path = self.entry_chemin.get()
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("Erreur", "Veuillez sélectionner un fichier de sauvegarde valide.")
            return

        confirm = messagebox.askyesno("Confirmation", "Cette opération va écraser la base actuelle.\nContinuer ?")
        if not confirm:
            return

        def restauration_thread():
            self.lbl_progression.configure(text="Préparation de la base...")
            self.update_idletasks()

            if not self.terminate_all_db_connections(self.DB_NAME):
                return

            conn_sys = None
            try:
                conn_sys = psycopg2.connect(
                    dbname="postgres",
                    user=self.DB_USER,
                    password=self.DB_PASSWORD,
                    host=self.DB_HOST,
                    port=self.DB_PORT
                )
                conn_sys.autocommit = True
                cursor_sys = conn_sys.cursor()
                
                cursor_sys.execute(f"DROP DATABASE IF EXISTS {self.DB_NAME};")
                cursor_sys.execute(f"CREATE DATABASE {self.DB_NAME} OWNER {self.DB_USER};")

            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur système : {e}")
                return
            finally:
                if conn_sys:
                    conn_sys.close()

            try:
                os.environ['PGPASSWORD'] = self.DB_PASSWORD
                self.progress_bar.set(0.2)
                self.lbl_progression.configure(text="Restauration en cours...")
                
                cmd = [
                    self.pg_restore_path,
                    "-U", self.DB_USER,
                    "-h", self.DB_HOST,
                    "-p", self.DB_PORT,
                    "-d", self.DB_NAME,
                    file_path
                ]

                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate()

                if process.returncode == 0:
                    self.progress_bar.set(1.0)
                    self.lbl_progression.configure(text="Terminé.")
                    messagebox.showinfo("Succès", "Restauration terminée avec succès.")
                else:
                    messagebox.showerror("Erreur", f"Détails :\n{stderr}")
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
            finally:
                if 'PGPASSWORD' in os.environ:
                    del os.environ['PGPASSWORD']

        threading.Thread(target=restauration_thread).start()

    def parcourir_fichier(self):
        chemin = filedialog.askopenfilename(
            title="Sélectionner un fichier de sauvegarde",
            filetypes=[("Fichiers backup", "*.backup")]
        )
        if chemin:
            self.entry_chemin.delete(0, ctk.END)
            self.entry_chemin.insert(0, chemin)

if __name__ == '__main__':
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    app = ctk.CTk()
    app.title("Sauvegarde / Restauration")
    app.geometry("500x450")
    page = PageSauvegarde(app)
    app.mainloop()