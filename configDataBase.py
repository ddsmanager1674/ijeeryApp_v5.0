import customtkinter as ctk
import json
import os
import glob
import shutil
import threading
import subprocess
import psycopg2 # Assurez-vous d'avoir installé psycopg2 : pip install psycopg2-binary
from psycopg2 import sql
from tkinter import messagebox, filedialog

class ConfigDataBase(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Configuration de la base de données")
        self.geometry("600x550")
        self.resizable(False, False)

        self.config_file_path = "config.json"
        self.config_data = self.load_config()

        self.create_widgets()
        self.set_entries_state("disabled")
        
        # Charger les bases de données après la création des widgets
        self.update_combobox_list()
        self.update_restore_link_state()

    def load_config(self):
        if os.path.exists(self.config_file_path):
            try:
                with open(self.config_file_path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return self.default_config()
        return self.default_config()

    def default_config(self):
        return {
            "database": {
                "host": "",
                "user": "",
                "password": "",
                "database": "",
                "port": 5432
            }
        }

    def fetch_database_names(self):
        """Récupère les noms des bases depuis la table tb_baseliste."""
        db_list = []
        try:
            # On utilise les identifiants actuels pour se connecter et lister les noms
            conn = psycopg2.connect(
                host=self.config_data['database']['host'],
                user=self.config_data['database']['user'],
                password=self.config_data['database']['password'],
                database=self.config_data['database']['database'],
                port=self.config_data['database']['port']
            )
            cursor = conn.cursor()
            # Requête pour récupérer la colonne nombase
            cursor.execute("SELECT nombase FROM tb_baseliste;")
            rows = cursor.fetchall()
            db_list = [row[0] for row in rows]
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Erreur de récupération : {e}")
            # Si erreur, on garde au moins la valeur actuelle du config
            current = self.config_data['database']['database']
            db_list = [current] if current else ["postgres"]
        
        return db_list

    def update_combobox_list(self):
        """Met à jour les valeurs de la ComboBox."""
        names = self.fetch_database_names()
        self.database_combo.configure(values=names)
        if self.config_data['database']['database'] in names:
            self.database_combo.set(self.config_data['database']['database'])

    def check_database_exists(self, db_name):
        """Vérifie si la base existe dans pg_database."""
        if not db_name:
            return False

        base_cfg = self.config_data['database']
        for maintenance_db in ("postgres", "template1"):
            try:
                conn = psycopg2.connect(
                    host=base_cfg.get('host', ''),
                    user=base_cfg.get('user', ''),
                    password=base_cfg.get('password', ''),
                    database=maintenance_db,
                    port=base_cfg.get('port', 5432)
                )
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (db_name,))
                exists = cursor.fetchone() is not None
                cursor.close()
                conn.close()
                return exists
            except Exception:
                continue

        return False

    def update_restore_link_state(self):
        selected_db = self.database_combo.get().strip() if hasattr(self, "database_combo") else ""
        missing = not self.check_database_exists(selected_db)
        if missing:
            self.dev_link_label.configure(text="(⚠) Restaurer la base (il n'existe pas)")
            if not self.dev_link_label.winfo_manager():
                self.dev_link_label.pack(pady=(2, 0))
            else:
                self.dev_link_label.pack_configure(pady=(2, 0))
        else:
            self.dev_link_label.pack_forget()

    def save_config(self):
        if self.save_button.cget("state") == "disabled":
            return

        try:
            new_port = int(self.port_entry.get())
        except ValueError:
            self.status_label.configure(text="Erreur: Le port doit être un nombre entier.", text_color="red")
            return

        self.config_data['database'].update({
            "host": self.host_entry.get(),
            "user": self.user_entry.get(),
            "password": self.password_entry.get(),
            "database": self.database_combo.get(), # Récupère la valeur de la ComboBox
            "port": new_port
        })

        with open(self.config_file_path, 'w') as f:
            json.dump(self.config_data, f, indent=4)

        self.status_label.configure(text="Configuration sauvegardée avec succès!", text_color="green")
        self.set_entries_state("disabled")
        self.save_button.configure(state="disabled")
        self.edit_button.configure(state="normal")
        self.update_restore_link_state()
        #self.after(2000, self.destroy)

    def set_entries_state(self, state):
        self.host_entry.configure(state=state)
        self.user_entry.configure(state=state)
        self.password_entry.configure(state=state)
        self.database_combo.configure(state=state) # État de la ComboBox
        self.port_entry.configure(state=state)
    
    def enable_editing(self):
        self.set_entries_state("normal")
        self.status_label.configure(text="Mode modification activé.", text_color="orange")
        self.edit_button.configure(state="disabled")
        self.save_button.configure(state="normal")

    def _on_dev_link_enter(self, event=None):
        self.dev_link_label.configure(text_color="#87CEEB")  # Bleu ciel

    def _on_dev_link_leave(self, event=None):
        self.dev_link_label.configure(text_color="#000080")  # Bleu marine

    def _on_dev_link_click(self, event=None):
        self.open_restore_window()

    def _on_database_selected(self, value):
        self.update_restore_link_state()

    def open_restore_window(self):
        restore_win = ctk.CTkToplevel(self)
        restore_win.title("Restauration de la base")
        restore_win.geometry("620x280")
        restore_win.resizable(False, False)
        restore_win.transient(self)
        restore_win.grab_set()

        ctk.CTkLabel(restore_win, text="Fichier de sauvegarde PostgreSQL").pack(pady=(14, 6))

        file_row = ctk.CTkFrame(restore_win, fg_color="transparent")
        file_row.pack(fill="x", padx=16)

        file_entry = ctk.CTkEntry(file_row)
        file_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        browse_btn = ctk.CTkButton(
            file_row,
            text="Parcourir",
            width=110,
            command=lambda: self._browse_restore_file(file_entry)
        )
        browse_btn.pack(side="right")

        status_label = ctk.CTkLabel(restore_win, text="Prêt")
        status_label.pack(pady=(14, 4))

        progress_bar = ctk.CTkProgressBar(restore_win, mode="determinate")
        progress_bar.pack(fill="x", padx=16)
        progress_bar.set(0)

        launch_btn = ctk.CTkButton(
            restore_win,
            text="Lancer la restauration",
            command=lambda: self._start_restore_process(
                restore_win, file_entry, status_label, progress_bar, launch_btn, browse_btn
            )
        )
        launch_btn.pack(pady=16)

    def _browse_restore_file(self, entry_widget):
        file_path = filedialog.askopenfilename(
            title="Sélectionner un fichier de sauvegarde",
            filetypes=[
                ("Fichiers backup/sql", "*.backup *.dump *.sql"),
                ("Tous les fichiers", "*.*")
            ]
        )
        if file_path:
            entry_widget.delete(0, ctk.END)
            entry_widget.insert(0, file_path)

    def _find_pg_binary(self, binary_name):
        from_path = f"{binary_name}.exe" if os.name == "nt" else binary_name
        if shutil.which(from_path):
            return from_path

        if os.name == "nt":
            candidates = sorted(
                glob.glob(fr"C:\Program Files\PostgreSQL\*\bin\{binary_name}.exe"),
                reverse=True
            )
            if candidates:
                return candidates[0]
        return None

    def _terminate_db_connections(self, db_name):
        conn = None
        try:
            cfg = self.config_data["database"]
            conn = psycopg2.connect(
                dbname="postgres",
                user=cfg["user"],
                password=cfg["password"],
                host=cfg["host"],
                port=cfg["port"]
            )
            conn.autocommit = True
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = %s AND pid <> pg_backend_pid()
                    """,
                    (db_name,)
                )
            return True, None
        except Exception as e:
            return False, str(e)
        finally:
            if conn:
                conn.close()

    def _start_restore_process(self, win, file_entry, status_label, progress_bar, launch_btn, browse_btn):
        file_path = file_entry.get().strip()
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("Erreur", "Veuillez sélectionner un fichier de sauvegarde valide.", parent=win)
            return

        launch_btn.configure(state="disabled")
        browse_btn.configure(state="disabled")
        status_label.configure(text="Vérification de la base...")
        progress_bar.set(0.1)

        threading.Thread(
            target=self._run_restore_process,
            args=(win, file_path, status_label, progress_bar, launch_btn, browse_btn),
            daemon=True
        ).start()

    def _run_restore_process(self, win, file_path, status_label, progress_bar, launch_btn, browse_btn):
        def ui(update_fn):
            try:
                win.after(0, update_fn)
            except Exception:
                pass

        cfg = self.config_data["database"]
        db_name = cfg["database"]

        try:
            base_exists = self.check_database_exists(db_name)
            ui(lambda: status_label.configure(text="Préparation de la base..."))
            ui(lambda: progress_bar.set(0.25))

            ok, err = self._terminate_db_connections(db_name)
            if not ok:
                raise RuntimeError(f"Impossible de fermer les connexions actives: {err}")

            conn = psycopg2.connect(
                dbname="postgres",
                user=cfg["user"],
                password=cfg["password"],
                host=cfg["host"],
                port=cfg["port"]
            )
            conn.autocommit = True
            try:
                with conn.cursor() as cursor:
                    if base_exists:
                        cursor.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(db_name)))
                    cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
            finally:
                conn.close()

            ui(lambda: status_label.configure(text="Restauration en cours..."))
            ui(lambda: progress_bar.set(0.55))

            os.environ["PGPASSWORD"] = str(cfg["password"])
            file_lower = file_path.lower()
            if file_lower.endswith(".sql"):
                psql_path = self._find_pg_binary("psql")
                if not psql_path:
                    raise FileNotFoundError("psql introuvable. Installez PostgreSQL client ou ajoutez-le au PATH.")
                cmd = [
                    psql_path,
                    "-U", str(cfg["user"]),
                    "-h", str(cfg["host"]),
                    "-p", str(cfg["port"]),
                    "-d", str(db_name),
                    "-f", file_path
                ]
            else:
                pg_restore_path = self._find_pg_binary("pg_restore")
                if not pg_restore_path:
                    raise FileNotFoundError("pg_restore introuvable. Installez PostgreSQL client ou ajoutez-le au PATH.")
                cmd = [
                    pg_restore_path,
                    "-U", str(cfg["user"]),
                    "-h", str(cfg["host"]),
                    "-p", str(cfg["port"]),
                    "-d", str(db_name),
                    "--clean",
                    "--if-exists",
                    file_path
                ]

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            _, stderr = process.communicate()
            if process.returncode != 0:
                raise RuntimeError(stderr.strip() or "Erreur inconnue pendant la restauration.")

            ui(lambda: progress_bar.set(1.0))
            ui(lambda: status_label.configure(text="Terminé"))
            ui(lambda: self.update_restore_link_state())
            ui(lambda: messagebox.showinfo("Succès", "Restauration terminée avec succès.", parent=win))
        except Exception as e:
            ui(lambda: progress_bar.set(0))
            ui(lambda: status_label.configure(text="Échec"))
            ui(lambda: messagebox.showerror("Erreur", f"Erreur de restauration:\n{e}", parent=win))
        finally:
            if "PGPASSWORD" in os.environ:
                del os.environ["PGPASSWORD"]
            ui(lambda: launch_btn.configure(state="normal"))
            ui(lambda: browse_btn.configure(state="normal"))

    def create_widgets(self):
        frame = ctk.CTkFrame(self)
        frame.pack(padx=20, pady=20, fill="both", expand=True)

        # Host
        ctk.CTkLabel(frame, text="Host:").pack(pady=(10, 0))
        self.host_entry = ctk.CTkEntry(frame)
        self.host_entry.insert(0, self.config_data['database']['host'])
        self.host_entry.pack()

        # Utilisateur
        ctk.CTkLabel(frame, text="Utilisateur:").pack(pady=(10, 0))
        self.user_entry = ctk.CTkEntry(frame)
        self.user_entry.insert(0, self.config_data['database']['user'])
        self.user_entry.pack()

        # Mot de passe
        ctk.CTkLabel(frame, text="Mot de passe:").pack(pady=(10, 0))
        self.password_entry = ctk.CTkEntry(frame, show="*")
        self.password_entry.insert(0, self.config_data['database']['password'])
        self.password_entry.pack()

        # Base de données (Transformé en ComboBox)
        ctk.CTkLabel(frame, text="Base de données:").pack(pady=(10, 0))
        self.database_combo = ctk.CTkComboBox(frame, values=["Chargement..."], command=self._on_database_selected)
        self.database_combo.set(self.config_data['database']['database'])
        self.database_combo.pack()
        self.dev_link_label = ctk.CTkLabel(
            frame,
            text="Restaurer la base",
            text_color="#000080",
            font=ctk.CTkFont(underline=True),
            cursor="hand2"
        )
        self.dev_link_label.pack(pady=(2, 0))
        self.dev_link_label.bind("<Enter>", self._on_dev_link_enter)
        self.dev_link_label.bind("<Leave>", self._on_dev_link_leave)
        self.dev_link_label.bind("<Button-1>", self._on_dev_link_click)

        # Port
        ctk.CTkLabel(frame, text="Port:").pack(pady=(10, 0))
        self.port_entry = ctk.CTkEntry(frame)
        self.port_entry.insert(0, str(self.config_data['database']['port']))
        self.port_entry.pack()

        button_frame = ctk.CTkFrame(frame)
        button_frame.pack(pady=20)

        self.edit_button = ctk.CTkButton(button_frame, text="Modifier", command=self.enable_editing)
        self.edit_button.pack(side="left", padx=5)

        self.save_button = ctk.CTkButton(button_frame, text="Sauvegarder", command=self.save_config, state="disabled")
        self.save_button.pack(side="left", padx=5)

        self.status_label = ctk.CTkLabel(frame, text="")
        self.status_label.pack()

if __name__ == "__main__":
    app = ConfigDataBase()
    app.mainloop()
