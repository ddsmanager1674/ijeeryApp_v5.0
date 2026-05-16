import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os
import datetime
import psycopg2
import threading
import json
import sys
import socket
from resource_utils import get_config_path
from app_theme import Colors, Fonts, styled
from log_utils import AppLogger

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
        try:
            config_path = get_config_path("config.json")
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("database")
        except Exception as e:
            print(f"Error loading config: {e}")
            return None

    def connect(self):
        if self.db_params is None:
            return False
        try:
            from pages.db_helper import connect_page_db
            self.conn = connect_page_db()
            self.cursor = self.conn.cursor()
            return True
        except Exception as e:
            print(f"Error connecting: {e}")
            return False

    def get_connection(self):
        if self.conn is None or self.conn.closed:
            if self.connect():
                return self.conn
            return None
        return self.conn

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()


db_manager = DatabaseManager()


def _appareil_label() -> str:
    """Nom du PC suivi de '/' et de l'adresse IP si disponible."""
    host = (socket.gethostname() or "PC").strip()
    ip = ""
    try:
        ip = socket.gethostbyname(host)
    except Exception:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
        except Exception:
            ip = ""
    if ip:
        return f"{host}/{ip}"
    return host


class PageSauvegarde(ctk.CTkFrame):
    def __init__(self, master, db_conn=None, session_data=None, **kwargs):
        super().__init__(master, fg_color=Colors.BG_PAGE)

        self.db_conn = db_conn
        self.session_data = session_data or getattr(master, "session_data", None) or {}

        config = db_manager.db_params
        if config:
            self.DB_NAME = config.get("database", "dbijeery")
            self.DB_USER = config.get("user", "postgres")
            self.DB_PASSWORD = config.get("password", "root")
            self.DB_HOST = config.get("host", "localhost")
            self.DB_PORT = str(config.get("port", "5432"))
        else:
            self.DB_NAME = "dbijeery"
            self.DB_USER = "postgres"
            self.DB_PASSWORD = "root"
            self.DB_HOST = "localhost"
            self.DB_PORT = "5432"

        self.pg_dump_path = r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe"
        self.pg_restore_path = r"C:\Program Files\PostgreSQL\16\bin\pg_restore.exe"

        self._username = self.session_data.get("username") or "Système"
        self._logger = AppLogger(conn=self.db_conn, session_data=self.session_data)

        self._apply_table_style()
        self._build_ui()
        self.after(50, self._init_history)

    def _get_conn(self):
        if self.db_conn is not None:
            try:
                if not self.db_conn.closed:
                    return self.db_conn
            except Exception:
                pass
        return db_manager.get_connection()

    def _init_history(self):
        self._ensure_save_history_table()
        self.refresh_history()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT, corner_radius=0, height=46)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        inner = styled.frame(header)
        inner.pack(side="left", padx=14, pady=6)
        ctk.CTkLabel(
            inner, text="💾", font=Fonts.heading(16), text_color=Colors.TEXT_ON_DARK
        ).pack(side="left", padx=(0, 10))
        titles = styled.frame(inner)
        titles.pack(side="left")
        ctk.CTkLabel(
            titles, text="Sauvegarde", font=Fonts.bold(13), text_color=Colors.TEXT_ON_DARK
        ).pack(anchor="w")
        ctk.CTkLabel(
            titles,
            text="Sauvegarde, restauration et historique",
            font=Fonts.small(9),
            text_color=Colors.TEXT_ON_DARK_DIM,
        ).pack(anchor="w")

        ops_card = styled.card(self)
        ops_card.grid(row=1, column=0, sticky="ew", padx=10, pady=(10, 6))
        ops_card.grid_columnconfigure(0, weight=1)

        styled.label_heading(ops_card, text="Sauvegarde / Restauration", size=13).grid(
            row=0, column=0, sticky="w", padx=14, pady=(12, 8)
        )

        restore_row = styled.frame(ops_card)
        restore_row.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))
        restore_row.grid_columnconfigure(0, weight=1)

        styled.label_muted(restore_row, text="Fichier à restaurer", size=12).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )
        self.entry_chemin = styled.entry(
            restore_row, placeholder="Chemin du fichier .backup", height=36
        )
        self.entry_chemin.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        styled.button_secondary(
            restore_row, text="Parcourir", width=130, height=36, command=self.parcourir_fichier
        ).grid(row=1, column=1, sticky="e")

        progress_wrap = styled.frame(ops_card)
        progress_wrap.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 8))
        progress_wrap.grid_columnconfigure(0, weight=1)
        self.progress_bar = ctk.CTkProgressBar(
            progress_wrap,
            height=10,
            fg_color=Colors.BG_INPUT,
            progress_color=Colors.PRIMARY,
            corner_radius=6,
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        self.progress_bar.set(0)
        self.lbl_progression = styled.label_muted(progress_wrap, text="")
        self.lbl_progression.grid(row=1, column=0, sticky="w")

        btn_row = styled.frame(ops_card)
        btn_row.grid(row=3, column=0, sticky="ew", padx=14, pady=(4, 16))
        btn_row.grid_columnconfigure(0, weight=1)
        btn_row.grid_columnconfigure(1, weight=1)

        btn_kw = dict(
            width=320,
            height=52,
            font=Fonts.bold(13),
            corner_radius=10,
        )
        ctk.CTkButton(
            btn_row,
            text="💾  Sauvegarder la base",
            fg_color=Colors.SUCCESS,
            hover_color=Colors.SUCCESS_DARK,
            text_color=Colors.TEXT_ON_DARK,
            command=self.sauvegarder_bdd,
            **btn_kw,
        ).grid(row=0, column=0, padx=(0, 12), sticky="e")
        ctk.CTkButton(
            btn_row,
            text="↺  Restaurer la base",
            fg_color=Colors.WARNING,
            hover_color="#D68910",
            text_color=Colors.TEXT_ON_DARK,
            command=self.restaurer_bdd,
            **btn_kw,
        ).grid(row=0, column=1, padx=(12, 0), sticky="w")

        history_card = styled.card(self)
        history_card.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        history_card.grid_columnconfigure(0, weight=1)
        history_card.grid_rowconfigure(1, weight=1)

        styled.label_heading(history_card, text="Historique des sauvegardes", size=12).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 4)
        )

        table_wrap = ctk.CTkFrame(history_card, fg_color=Colors.BG_CARD, corner_radius=8)
        table_wrap.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 4))
        table_wrap.grid_columnconfigure(0, weight=1)
        table_wrap.grid_rowconfigure(0, weight=1)

        columns = ("datetime", "libelle", "appareil", "description", "taille_mo", "utilisateur")
        self.tree = ttk.Treeview(
            table_wrap, columns=columns, show="headings", style="SaveHistory.Treeview", height=12
        )
        headings = {
            "datetime": "Date",
            "libelle": "Libellé",
            "appareil": "Appareil",
            "description": "Chemin",
            "taille_mo": "Mo",
            "utilisateur": "Utilisateur",
        }
        widths = {
            "datetime": 120,
            "libelle": 160,
            "appareil": 130,
            "description": 280,
            "taille_mo": 55,
            "utilisateur": 100,
        }
        for col in columns:
            self.tree.heading(col, text=headings[col])
            anchor = "e" if col == "taille_mo" else ("center" if col == "datetime" else "w")
            self.tree.column(col, width=widths[col], anchor=anchor, stretch=(col == "description"))
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        self.tree.tag_configure("row_even", background=Colors.BG_CARD)
        self.tree.tag_configure("row_odd", background=Colors.BG_ROW_ALT)

        y_scroll = ctk.CTkScrollbar(table_wrap, command=self.tree.yview, width=14)
        y_scroll.grid(row=0, column=1, sticky="ns", padx=(0, 6), pady=6)
        self.tree.configure(yscrollcommand=y_scroll.set)

        footer = styled.frame(history_card)
        footer.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))
        self.result_count_label = ctk.CTkLabel(
            footer,
            text="0 élément(s)",
            font=Fonts.small(10),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
        )
        self.result_count_label.pack(side="left")

    def _apply_table_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "SaveHistory.Treeview",
            rowheight=22,
            font=("Segoe UI", 8),
            background=Colors.BG_CARD,
            foreground=Colors.TEXT_PRIMARY,
            fieldbackground=Colors.BG_CARD,
            borderwidth=0,
        )
        style.configure(
            "SaveHistory.Treeview.Heading",
            background=Colors.BG_HEADER,
            foreground=Colors.TEXT_ON_DARK,
            font=("Segoe UI", 8, "bold"),
            relief="flat",
        )
        style.map(
            "SaveHistory.Treeview",
            background=[("selected", Colors.PRIMARY)],
            foreground=[("selected", Colors.TEXT_ON_DARK)],
        )

    def _ensure_save_history_table(self):
        conn = self._get_conn()
        if not conn:
            return
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS public.tb_save_history (
                        id SERIAL PRIMARY KEY,
                        datetime TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        libelle VARCHAR(255) NOT NULL,
                        appareil VARCHAR(200),
                        description TEXT,
                        taille_mo NUMERIC(14, 2),
                        utilisateur VARCHAR(150)
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_tb_save_history_datetime
                    ON public.tb_save_history (datetime DESC)
                    """
                )
            conn.commit()
        except Exception as err:
            try:
                conn.rollback()
            except Exception:
                pass
            print(f"tb_save_history: {err}")

    def _insert_save_history(self, file_path: str, libelle: str):
        conn = self._get_conn()
        if not conn:
            return
        try:
            size_mo = round(os.path.getsize(file_path) / (1024 * 1024), 2)
        except OSError:
            size_mo = None
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO tb_save_history
                        (datetime, libelle, appareil, description, taille_mo, utilisateur)
                    VALUES (CURRENT_TIMESTAMP, %s, %s, %s, %s, %s)
                    """,
                    (
                        libelle,
                        _appareil_label(),
                        file_path,
                        size_mo,
                        self._username,
                    ),
                )
            conn.commit()
            self.refresh_history()
        except Exception as err:
            try:
                conn.rollback()
            except Exception:
                pass
            print(f"Historique sauvegarde non enregistré : {err}")

    def refresh_history(self):
        if not hasattr(self, "tree"):
            return
        for item in self.tree.get_children():
            self.tree.delete(item)

        conn = self._get_conn()
        if not conn:
            self.result_count_label.configure(text="0 élément(s)")
            return

        query = """
            SELECT datetime, libelle, appareil, description, taille_mo, utilisateur
            FROM tb_save_history
            ORDER BY datetime DESC NULLS LAST
        """
        try:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
        except psycopg2.Error as err:
            print(f"Historique sauvegarde : {err}")
            self.result_count_label.configure(text="0 élément(s)")
            return

        for idx, row in enumerate(rows):
            dt, lib, app, desc, taille, user = row
            dt_str = dt.strftime("%d/%m/%Y %H:%M") if dt else ""
            taille_str = f"{float(taille):,.2f}".replace(",", " ") if taille is not None else ""
            tag = "row_even" if idx % 2 == 0 else "row_odd"
            self.tree.insert(
                "",
                "end",
                values=(dt_str, lib or "", app or "", desc or "", taille_str, user or ""),
                tags=(tag,),
            )

        count = len(rows)
        label = "élément" if count == 1 else "éléments"
        self.result_count_label.configure(text=f"{count} {label}")

    def get_nomesociete(self):
        conn = db_manager.get_connection()
        if not conn:
            return "SOCIETE"
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT nomsociete FROM tb_infosociete LIMIT 1;")
                result = cursor.fetchone()
                if result and result[0]:
                    return str(result[0]).replace(" ", "_")
                return "SOCIETE"
        except Exception as e:
            print(f"Erreur lors de la récupération du nom société : {e}")
            return "SOCIETE"

    def sauvegarder_bdd(self):
        nomsociete = self.get_nomesociete()
        now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"SAUVE-{nomsociete}-{now}.backup"

        file_path = filedialog.asksaveasfilename(
            defaultextension=".backup",
            filetypes=[("Fichiers de sauvegarde", "*.backup")],
            initialfile=default_filename,
        )
        if not file_path:
            return

        libelle = os.path.basename(file_path)
        try:
            os.environ["PGPASSWORD"] = self.DB_PASSWORD
            subprocess.run(
                [
                    self.pg_dump_path,
                    "-U",
                    self.DB_USER,
                    "-h",
                    self.DB_HOST,
                    "-p",
                    self.DB_PORT,
                    "-F",
                    "c",
                    "-f",
                    file_path,
                    self.DB_NAME,
                ],
                check=True,
            )
            messagebox.showinfo("Succès", f"Sauvegarde effectuée avec succès :\n{libelle}")
            self._insert_save_history(file_path, libelle)
            try:
                self._logger.log(
                    action="Sauvegarde base de données",
                    element=self.DB_NAME,
                    details=f"Sauvegarde créée: {libelle}",
                    value=file_path,
                )
            except Exception:
                pass
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde :\n{e}")
            try:
                self._logger.log(
                    action="Sauvegarde base de données",
                    element=self.DB_NAME,
                    details=f"Échec sauvegarde: {libelle}",
                    value=str(e),
                )
            except Exception:
                pass
        except FileNotFoundError:
            messagebox.showerror("Erreur", f"pg_dump introuvable à :\n{self.pg_dump_path}")
        finally:
            if "PGPASSWORD" in os.environ:
                del os.environ["PGPASSWORD"]

    def _invalidate_app_db_connection(self):
        app = self.winfo_toplevel()
        if not hasattr(app, "db_manager"):
            return
        old = getattr(app, "db_conn", None)
        if old:
            try:
                old.close()
            except Exception:
                pass
        ensure = getattr(app.db_manager, "ensure_connection", None)
        if callable(ensure):
            app.db_conn = ensure(None)
        else:
            app.db_conn = app.db_manager.get_connection()

    def terminate_all_db_connections(self, dbname_to_terminate):
        conn_sys = None
        try:
            from db import get_postgres_admin_connection
            conn_sys = get_postgres_admin_connection()
            if not conn_sys:
                return False
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

        confirm = messagebox.askyesno(
            "Confirmation", "Cette opération va écraser la base actuelle.\nContinuer ?"
        )
        if not confirm:
            return

        def restauration_thread():
            self.lbl_progression.configure(text="Préparation de la base...")
            self.update_idletasks()

            if not self.terminate_all_db_connections(self.DB_NAME):
                return

            conn_sys = None
            try:
                from db import get_postgres_admin_connection
                conn_sys = get_postgres_admin_connection()
                if not conn_sys:
                    return
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
                os.environ["PGPASSWORD"] = self.DB_PASSWORD
                self.progress_bar.set(0.2)
                self.lbl_progression.configure(text="Restauration en cours...")

                cmd = [
                    self.pg_restore_path,
                    "-U",
                    self.DB_USER,
                    "-h",
                    self.DB_HOST,
                    "-p",
                    self.DB_PORT,
                    "-d",
                    self.DB_NAME,
                    file_path,
                ]
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                _stdout, stderr = process.communicate()

                if process.returncode == 0:
                    self.progress_bar.set(1.0)
                    self.lbl_progression.configure(text="Terminé.")
                    self._invalidate_app_db_connection()
                    messagebox.showinfo("Succès", "Restauration terminée avec succès.")
                    try:
                        self._logger.log(
                            action="Restauration base de données",
                            element=self.DB_NAME,
                            details=f"Restauration OK depuis {os.path.basename(file_path)}",
                            value=file_path,
                        )
                    except Exception:
                        pass
                else:
                    messagebox.showerror("Erreur", f"Détails :\n{stderr}")
                    try:
                        self._logger.log(
                            action="Restauration base de données",
                            element=self.DB_NAME,
                            details=f"Échec restauration depuis {os.path.basename(file_path)}",
                            value=stderr,
                        )
                    except Exception:
                        pass
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
                try:
                    self._logger.log(
                        action="Restauration base de données",
                        element=self.DB_NAME,
                        details=f"Exception restauration depuis {os.path.basename(file_path)}",
                        value=str(e),
                    )
                except Exception:
                    pass
            finally:
                if "PGPASSWORD" in os.environ:
                    del os.environ["PGPASSWORD"]

        threading.Thread(target=restauration_thread, daemon=True).start()

    def parcourir_fichier(self):
        chemin = filedialog.askopenfilename(
            title="Sélectionner un fichier de sauvegarde",
            filetypes=[("Fichiers backup", "*.backup")],
        )
        if chemin:
            self.entry_chemin.delete(0, ctk.END)
            self.entry_chemin.insert(0, chemin)


if __name__ == "__main__":
    from app_theme import Theme, init_theme

    init_theme()
    app = ctk.CTk()
    app.title("Sauvegarde / Restauration")
    app.geometry("1100x720")
    Theme.apply(app)
    PageSauvegarde(app).pack(fill="both", expand=True)
    app.mainloop()
