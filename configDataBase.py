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
from resource_utils import get_config_path

try:
    from app_theme import Colors, Fonts, Theme, init_theme
except ImportError:
    class Colors:
        BG_PAGE = "#ECF0F1"
        BG_CARD = "#FFFFFF"
        BG_INPUT = "#F4F6F8"
        BG_HEADER = "#2C3E50"
        PRIMARY = "#3498DB"
        PRIMARY_HOVER = "#2980B9"
        SUCCESS = "#2ECC71"
        SUCCESS_DARK = "#27AE60"
        WARNING = "#F39C12"
        TEXT_PRIMARY = "#2C3E50"
        TEXT_SECONDARY = "#5D6D7E"
        TEXT_MUTED = "#95A5A6"
        TEXT_ON_DARK = "#FFFFFF"
        BORDER = "#D5D8DC"
        DIVIDER = "#E8EAED"
        CLOUDS = "#ECF0F1"
        SILVER = "#BDC3C7"

    class Fonts:
        @staticmethod
        def get(size=13, weight="normal"):
            return ctk.CTkFont(family="Segoe UI", size=size, weight=weight)
        @classmethod
        def body(cls, size=13): return cls.get(size)
        @classmethod
        def label(cls, size=12): return cls.get(size)
        @classmethod
        def small(cls, size=11): return cls.get(size)
        @classmethod
        def heading(cls, size=15): return cls.get(size, "bold")
        @classmethod
        def title(cls, size=18): return cls.get(size, "bold")
        @classmethod
        def button(cls, size=13): return cls.get(size, "bold")
        @classmethod
        def input(cls, size=13): return cls.get(size)

    class Theme:
        @staticmethod
        def setup():
            ctk.set_appearance_mode("light")
            ctk.set_default_color_theme("blue")
        @staticmethod
        def apply(window):
            window.configure(fg_color=Colors.BG_PAGE)
        @staticmethod
        def apply_toplevel(window):
            window.configure(fg_color=Colors.BG_PAGE)

    init_theme = Theme.setup


def _entry(parent, placeholder="", show=None):
    entry_kwargs = dict(
        height=36,
        fg_color=Colors.BG_INPUT,
        border_color=Colors.BORDER,
        border_width=1,
        corner_radius=8,
        text_color=Colors.TEXT_PRIMARY,
        placeholder_text=placeholder,
        placeholder_text_color=Colors.TEXT_MUTED,
        font=Fonts.input(12),
    )
    if show:
        entry_kwargs["show"] = show
    return ctk.CTkEntry(parent, **entry_kwargs)


def _button(parent, text, command, kind="primary", state="normal"):
    if kind == "success":
        fg, hover = Colors.SUCCESS, Colors.SUCCESS_DARK
    elif kind == "secondary":
        fg, hover = Colors.CLOUDS, Colors.SILVER
    else:
        fg, hover = Colors.PRIMARY, Colors.PRIMARY_HOVER
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        state=state,
        height=36,
        fg_color=fg,
        hover_color=hover,
        text_color=Colors.TEXT_PRIMARY if kind == "secondary" else Colors.TEXT_ON_DARK,
        border_width=1 if kind == "secondary" else 0,
        border_color=Colors.BORDER,
        corner_radius=8,
        font=Fonts.button(12),
    )


class ConfigDataBase(ctk.CTk):
    def __init__(self):
        try:
            init_theme()
        except Exception:
            Theme.setup()
        super().__init__()
        self.title("Configuration de la base de données")
        self.geometry("640x600")
        self.resizable(False, False)
        Theme.apply(self)

        self.config_file_path = get_config_path('config.json')
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
                self.dev_link_label.grid(row=4, column=1, sticky="w", padx=(10, 24), pady=(0, 8))
            else:
                self.dev_link_label.grid_configure(row=4, column=1, sticky="w", padx=(10, 24), pady=(0, 8))
        else:
            self.dev_link_label.grid_remove()

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
        self.dev_link_label.configure(text_color=Colors.PRIMARY_HOVER)

    def _on_dev_link_leave(self, event=None):
        self.dev_link_label.configure(text_color=Colors.PRIMARY)

    def _on_dev_link_click(self, event=None):
        self.open_restore_window()

    def _on_database_selected(self, value):
        self.update_restore_link_state()

    def open_restore_window(self):
        restore_win = ctk.CTkToplevel(self)
        restore_win.title("Restauration de la base")
        restore_win.geometry("640x300")
        restore_win.resizable(False, False)
        restore_win.transient(self)
        restore_win.grab_set()
        Theme.apply_toplevel(restore_win)

        header = ctk.CTkFrame(restore_win, fg_color=Colors.BG_HEADER, corner_radius=0, height=54)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header,
            text="Restauration de la base",
            font=Fonts.heading(16),
            text_color=Colors.TEXT_ON_DARK,
            anchor="w",
        ).pack(side="left", padx=18)

        body = ctk.CTkFrame(restore_win, fg_color=Colors.BG_PAGE, corner_radius=0)
        body.pack(fill="both", expand=True, padx=18, pady=16)

        ctk.CTkLabel(
            body,
            text="Fichier de sauvegarde PostgreSQL",
            font=Fonts.label(12),
            text_color=Colors.TEXT_SECONDARY,
        ).pack(anchor="w", pady=(0, 6))

        file_row = ctk.CTkFrame(body, fg_color="transparent")
        file_row.pack(fill="x")

        file_entry = _entry(file_row, placeholder="Sélectionner un fichier .backup, .dump ou .sql")
        file_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        browse_btn = _button(
            file_row,
            text="Parcourir",
            command=lambda: self._browse_restore_file(file_entry),
            kind="secondary",
        )
        browse_btn.configure(width=118)
        browse_btn.pack(side="right")

        status_label = ctk.CTkLabel(
            body,
            text="Prêt",
            font=Fonts.small(11),
            text_color=Colors.TEXT_MUTED,
        )
        status_label.pack(anchor="w", pady=(16, 6))

        progress_bar = ctk.CTkProgressBar(
            body,
            mode="determinate",
            height=8,
            fg_color=Colors.BG_INPUT,
            progress_color=Colors.PRIMARY,
            corner_radius=4,
        )
        progress_bar.pack(fill="x")
        progress_bar.set(0)

        launch_btn = _button(
            body,
            text="Lancer la restauration",
            command=lambda: self._start_restore_process(
                restore_win, file_entry, status_label, progress_bar, launch_btn, browse_btn
            ),
            kind="primary",
        )
        launch_btn.pack(pady=(18, 0))

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
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color=Colors.BG_HEADER, corner_radius=0, height=78)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Configuration base de données",
            font=Fonts.title(19),
            text_color=Colors.TEXT_ON_DARK,
            anchor="w",
        ).grid(row=0, column=0, sticky="sw", padx=24, pady=(16, 0))
        ctk.CTkLabel(
            header,
            text="Paramètres de connexion PostgreSQL",
            font=Fonts.small(11),
            text_color=Colors.TEXT_ON_DARK,
            anchor="w",
        ).grid(row=1, column=0, sticky="nw", padx=24, pady=(1, 0))

        frame = ctk.CTkFrame(
            self,
            fg_color=Colors.BG_CARD,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER,
        )
        frame.grid(row=1, column=0, sticky="nsew", padx=24, pady=20)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)

        # Host
        ctk.CTkLabel(frame, text="Host", font=Fonts.label(12), text_color=Colors.TEXT_SECONDARY).grid(
            row=0, column=0, sticky="w", padx=(24, 10), pady=(22, 6)
        )
        self.host_entry = _entry(frame)
        self.host_entry.insert(0, self.config_data['database']['host'])
        self.host_entry.grid(row=1, column=0, sticky="ew", padx=(24, 10), pady=(0, 12))

        # Utilisateur
        ctk.CTkLabel(frame, text="Utilisateur", font=Fonts.label(12), text_color=Colors.TEXT_SECONDARY).grid(
            row=0, column=1, sticky="w", padx=(10, 24), pady=(22, 6)
        )
        self.user_entry = _entry(frame)
        self.user_entry.insert(0, self.config_data['database']['user'])
        self.user_entry.grid(row=1, column=1, sticky="ew", padx=(10, 24), pady=(0, 12))

        # Mot de passe
        ctk.CTkLabel(frame, text="Mot de passe", font=Fonts.label(12), text_color=Colors.TEXT_SECONDARY).grid(
            row=2, column=0, sticky="w", padx=(24, 10), pady=(4, 6)
        )
        self.password_entry = _entry(frame, show="*")
        self.password_entry.insert(0, self.config_data['database']['password'])
        self.password_entry.grid(row=3, column=0, sticky="ew", padx=(24, 10), pady=(0, 12))

        # Base de données (Transformé en ComboBox)
        ctk.CTkLabel(frame, text="Base de données", font=Fonts.label(12), text_color=Colors.TEXT_SECONDARY).grid(
            row=2, column=1, sticky="w", padx=(10, 24), pady=(4, 6)
        )
        self.database_combo = ctk.CTkComboBox(
            frame,
            values=["Chargement..."],
            command=self._on_database_selected,
            height=36,
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            border_width=1,
            button_color=Colors.PRIMARY,
            button_hover_color=Colors.PRIMARY_HOVER,
            dropdown_fg_color=Colors.BG_CARD,
            dropdown_hover_color=Colors.BG_INPUT,
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.input(12),
            dropdown_font=Fonts.body(12),
            corner_radius=8,
        )
        self.database_combo.set(self.config_data['database']['database'])
        self.database_combo.grid(row=3, column=1, sticky="ew", padx=(10, 24), pady=(0, 2))
        self.dev_link_label = ctk.CTkLabel(
            frame,
            text="Restaurer la base",
            text_color=Colors.PRIMARY,
            font=ctk.CTkFont(family="Roboto", size=11, underline=True),
            cursor="hand2"
        )
        self.dev_link_label.grid(row=4, column=1, sticky="w", padx=(10, 24), pady=(0, 8))
        self.dev_link_label.bind("<Enter>", self._on_dev_link_enter)
        self.dev_link_label.bind("<Leave>", self._on_dev_link_leave)
        self.dev_link_label.bind("<Button-1>", self._on_dev_link_click)

        # Port
        ctk.CTkLabel(frame, text="Port", font=Fonts.label(12), text_color=Colors.TEXT_SECONDARY).grid(
            row=5, column=0, sticky="w", padx=(24, 10), pady=(4, 6)
        )
        self.port_entry = _entry(frame)
        self.port_entry.insert(0, str(self.config_data['database']['port']))
        self.port_entry.grid(row=6, column=0, sticky="ew", padx=(24, 10), pady=(0, 18))

        divider = ctk.CTkFrame(frame, height=1, fg_color=Colors.DIVIDER, corner_radius=0)
        divider.grid(row=7, column=0, columnspan=2, sticky="ew", padx=24, pady=(2, 16))

        button_frame = ctk.CTkFrame(frame, fg_color="transparent")
        button_frame.grid(row=8, column=0, columnspan=2, sticky="ew", padx=24)
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        self.edit_button = _button(button_frame, text="Modifier", command=self.enable_editing, kind="secondary")
        self.edit_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.save_button = _button(
            button_frame,
            text="Sauvegarder",
            command=self.save_config,
            kind="success",
            state="disabled",
        )
        self.save_button.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        self.status_label = ctk.CTkLabel(
            frame,
            text="",
            font=Fonts.small(11),
            text_color=Colors.TEXT_MUTED,
            anchor="center",
        )
        self.status_label.grid(row=9, column=0, columnspan=2, sticky="ew", padx=24, pady=(14, 0))

if __name__ == "__main__":
    app = ConfigDataBase()
    app.mainloop()
