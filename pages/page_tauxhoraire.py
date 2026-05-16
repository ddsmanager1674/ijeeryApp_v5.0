import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime
import unicodedata
import os
import json
import sys
from resource_utils import get_config_path, safe_file_read

from app_theme import Colors, Fonts, styled, Layout
from log_utils import AppLogger


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

    def connect(self):
        """Establishes a new database connection."""
        if self.db_params is None:
            print("Cannot connect: Database configuration is missing.")
            return False

        try:
            from pages.db_helper import connect_page_db
            self.conn = connect_page_db()
            self.cursor = self.conn.cursor()
            print("Connection to the database successful!")
            return True
        except psycopg2.OperationalError as e:
            print(f"Error connecting to the database: {e}")
            self.conn = None
            self.cursor = None
            return False
        except Exception as e:
            print(f"Unexpected error connecting to database: {e}")
            self.conn = None
            self.cursor = None
            return False

    def get_connection(self):
        """Returns the database connection if connected, otherwise attempts to connect."""
        if self.conn is None or self.conn.closed:
            if self.connect():
                return self.conn
            else:
                return None
        return self.conn
    
    def get_cursor(self):
        """Returns the database cursor if connected, otherwise attempts to connect."""
        if self.cursor is None or self.cursor.closed:
            if self.get_connection():
                self.cursor = self.conn.cursor()
            else:
                return None
        return self.cursor

    def close(self):
        """Closes the database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

# Instantiate DatabaseManager
db_manager = DatabaseManager()

class PageTauxHoraire(ctk.CTkFrame):
    # Ajoutez un paramètre 'app_root' pour la fenêtre principale
    def __init__(self, master, app_root):
        # [UI] Thème iJeery (Taux Horaire)
        super().__init__(master, fg_color=Colors.BG_PAGE)
        self.pack(fill="both", expand=True)

        self.app_root = app_root
        self.conn = None
        self.cursor = None
        self.session_data = getattr(master, "session_data", None) or {}
        self._logger = AppLogger(conn=self.conn, session_data=self.session_data)
        self.entry_widgets = {}  # legacy (plus utilisé)
        self.selected_personnel_id: int | None = None
        self.selected_personnel_name = ctk.StringVar(value="")
        self.current_rate_var = ctk.StringVar(value="")
        self.new_rate_var = ctk.StringVar(value="")

        self._setup_treeview_style()
        self._connect_db()
        self._create_widgets()
        # Utilisez self.app_root.after au lieu de self.master.after
        self.app_root.after(150, self._filter_personnel)

        # Assurez-vous que la connexion à la base de données est fermée lorsque la fenêtre principale est fermée
        # Appelez .protocol() sur l'objet app_root, qui est la vraie fenêtre principale
        self.app_root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _connect_db(self):
        """Establishes a connection to the PostgreSQL database."""
        try:
        
            self.db_manager = db_manager
            self.conn = self.db_manager.get_connection()
        
            if self.conn is None:
                messagebox.showerror("Erreur de connexion", "Impossible de se connecter à la base de données.")
                self.is_connected = False
                return
            else:
                self.cursor = self.conn.cursor()
                self.is_connected = True

            # Create the tb_tauxhoraire table if it doesn't exist
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tb_tauxhoraire (
                    id SERIAL PRIMARY KEY,
                    tauxhoraire DOUBLE PRECISION,
                    idpers INT,
                    dateregistre TIMESTAMP
                )
                """
            )
            self.conn.commit()
        except psycopg2.Error as err:
            messagebox.showerror("Erreur de connexion", f"Erreur : {err}")
            self.conn = None # Set to None to indicate failed connection

    def _setup_treeview_style(self):
        # [UI] Style P.Treeview cohérent avec le reste du module Personnel
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure(
            "P.Treeview",
            background=Colors.BG_CARD,
            foreground=Colors.TEXT_PRIMARY,
            fieldbackground=Colors.BG_CARD,
            rowheight=26,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        s.configure(
            "P.Treeview.Heading",
            background=Colors.MIDNIGHT,
            foreground=Colors.TEXT_ON_DARK,
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padding=(6, 5),
        )
        s.map("P.Treeview", background=[("selected", Colors.PRIMARY_LIGHT)])
        s.map("P.Treeview.Heading", background=[("active", Colors.MIDNIGHT_LIGHT)])

    def _configure_table_alternating_colors(self, tree):
        tree.tag_configure("row_even", background=Colors.BG_CARD)
        tree.tag_configure("row_odd", background=Colors.BG_ROW_ALT)

    def _refresh_table_alternating_colors(self, tree):
        for idx, item in enumerate(tree.get_children()):
            tree.item(item, tags=("row_even" if idx % 2 == 0 else "row_odd",))

    def _create_widgets(self):
        """[UI] Interface structurée : sélection personnel → saisie taux → enregistrement."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        header = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT, corner_radius=0, height=46)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        left = styled.frame(header)
        left.pack(side="left", padx=14)
        ctk.CTkLabel(left, text="💲", font=Fonts.heading(16), text_color=Colors.TEXT_ON_DARK).pack(side="left", padx=(0, 8))
        inner = styled.frame(left)
        inner.pack(side="left")
        ctk.CTkLabel(inner, text="Taux Horaire", font=Fonts.bold(13), text_color=Colors.TEXT_ON_DARK).pack(anchor="w")
        ctk.CTkLabel(inner, text="Enregistrement du taux horaire par personnel", font=Fonts.small(9), text_color=Colors.TEXT_ON_DARK_DIM).pack(anchor="w")

        # Toolbar recherche
        toolbar = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        toolbar.grid(row=1, column=0, padx=10, pady=(10, 6), sticky="ew")
        toolbar.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(toolbar, text="Recherche", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(row=0, column=0, padx=(12, 8), pady=10, sticky="w")
        self.search_entry = ctk.CTkEntry(
            toolbar, height=32, fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            corner_radius=8, font=Fonts.body(11), placeholder_text="Nom ou prénom…"
        )
        self.search_entry.grid(row=0, column=1, padx=(0, 12), pady=10, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self._filter_personnel)
        styled.button_secondary(toolbar, text="Actualiser", icon="↻", width=120, height=32, command=self._filter_personnel).grid(
            row=0, column=2, padx=(0, 12), pady=10, sticky="e"
        )

        # Contenu: liste personnel (gauche) + fiche taux (droite)
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 6))
        content.grid_columnconfigure(0, weight=3)
        content.grid_columnconfigure(1, weight=2)
        content.grid_rowconfigure(0, weight=1)

        list_card = ctk.CTkFrame(content, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        list_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        list_card.grid_columnconfigure(0, weight=1)
        list_card.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(list_card, columns=("nom", "prenom", "tauxhoraire"), show="headings", style="P.Treeview", selectmode="browse")
        self._configure_table_alternating_colors(self.tree)
        self.tree.heading("nom", text="Nom")
        self.tree.heading("prenom", text="Prénom")
        self.tree.heading("tauxhoraire", text="Taux actuel")
        self.tree.column("nom", width=180, anchor="w")
        self.tree.column("prenom", width=180, anchor="w")
        self.tree.column("tauxhoraire", width=140, anchor="e")
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        vsb = ttk.Scrollbar(list_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns", pady=6)
        self.tree.bind("<<TreeviewSelect>>", self._on_select_personnel)

        self.label_count = ctk.CTkLabel(list_card, text="Personnel affichés : 0", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY)
        self.label_count.grid(row=1, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 10))

        form_card = ctk.CTkFrame(content, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        form_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        form_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(form_card, text="Fiche taux horaire", font=Fonts.bold(12), text_color=Colors.TEXT_PRIMARY).grid(
            row=0, column=0, padx=12, pady=(12, 6), sticky="w"
        )
        ctk.CTkLabel(form_card, text="Personnel sélectionné", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(
            row=1, column=0, padx=12, pady=(6, 2), sticky="w"
        )
        self.personnel_entry = ctk.CTkEntry(
            form_card, textvariable=self.selected_personnel_name, height=32, fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            corner_radius=8, font=Fonts.body(11), state="readonly"
        )
        self.personnel_entry.grid(row=2, column=0, padx=12, pady=(0, 10), sticky="ew")

        ctk.CTkLabel(form_card, text="Taux actuel", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(
            row=3, column=0, padx=12, pady=(0, 2), sticky="w"
        )
        self.current_rate_entry = ctk.CTkEntry(
            form_card, textvariable=self.current_rate_var, height=32, fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            corner_radius=8, font=Fonts.body(11), state="readonly"
        )
        self.current_rate_entry.grid(row=4, column=0, padx=12, pady=(0, 10), sticky="ew")

        ctk.CTkLabel(form_card, text="Historique (derniers enregistrements)", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(
            row=5, column=0, padx=12, pady=(0, 2), sticky="w"
        )
        hist_card = ctk.CTkFrame(form_card, fg_color=Colors.BG_CARD, corner_radius=10, border_width=1, border_color=Colors.BORDER)
        hist_card.grid(row=6, column=0, padx=12, pady=(0, 10), sticky="nsew")
        hist_card.grid_columnconfigure(0, weight=1)
        hist_card.grid_rowconfigure(0, weight=1)
        self.history_tree = ttk.Treeview(hist_card, columns=("date", "taux"), show="headings", style="P.Treeview", height=5, selectmode="browse")
        self.history_tree.heading("date", text="Date")
        self.history_tree.heading("taux", text="Taux")
        self.history_tree.column("date", width=160, anchor="w")
        self.history_tree.column("taux", width=120, anchor="e")
        self.history_tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        hvsb = ttk.Scrollbar(hist_card, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=hvsb.set)
        hvsb.grid(row=0, column=1, sticky="ns", pady=6)
        self._configure_table_alternating_colors(self.history_tree)

        ctk.CTkLabel(form_card, text="Nouveau taux (Ariary)", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(
            row=7, column=0, padx=12, pady=(0, 2), sticky="w"
        )
        self.new_rate_entry = ctk.CTkEntry(
            form_card, textvariable=self.new_rate_var, height=36, fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            corner_radius=8, font=Fonts.body(12), placeholder_text="Ex: 15000"
        )
        self.new_rate_entry.grid(row=8, column=0, padx=12, pady=(0, 12), sticky="ew")

        actions = ctk.CTkFrame(form_card, fg_color="transparent")
        actions.grid(row=9, column=0, padx=12, pady=(0, 12), sticky="ew")
        styled.button_success(actions, text="Enregistrer", icon="💾", width=160, height=34, command=self._enregistrer_taux).pack(side="left")
        styled.button_secondary(actions, text="Vider", icon="↺", width=120, height=34, command=self._clear_form).pack(side="left", padx=(10, 0))

    def _charger_personnel(self):
        """Fetches all professor data from the database."""
        if not self.cursor:
            return []
        try:
            self.cursor.execute("SELECT id, nom, prenom FROM tb_personnel ORDER BY nom, prenom")
            return self.cursor.fetchall()
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            messagebox.showerror("Erreur SQL", str(e))
            return []
    
    def _normalize_string(self, s):
        """Removes diacritics (accents) from a string and converts to lowercase."""
        if not isinstance(s, str):
            return ""
        return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()

    def _filter_personnel(self, event=None):
        """Filters the Treeview based on the search input (liste à gauche)."""
        # Normalize the search term for comparison
        search_term = self._normalize_string(self.search_entry.get())

        # Clear existing items and entry widgets
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._refresh_table_alternating_colors(self.tree)
        
        # Reload and filter professors
        all_personnel = self._charger_personnel()
        inserted = 0
        for prof in all_personnel:
            idpers, nom, prenom = prof
            # Normalize professor's name and prenom for comparison
            normalized_nom = self._normalize_string(nom)
            normalized_prenom = self._normalize_string(prenom)

            # Fetch current hourly rate if it exists
            current_taux = ""
            if self.cursor:
                try:
                    self.cursor.execute("SELECT tauxhoraire FROM tb_tauxhoraire WHERE idpers = %s ORDER BY dateregistre DESC LIMIT 1", (idpers,))
                    result = self.cursor.fetchone()
                    if result:
                        current_taux = str(result[0])
                except Exception as e:
                    print(f"Erreur lors de la récupération du taux horaire pour {nom} {prenom}: {e}") # For debugging

            # Check if the normalized search term is in the normalized name or prenom
            if search_term in normalized_nom or search_term in normalized_prenom:
                nom_disp = (nom or "").strip() if nom is not None else ""
                prenom_disp = (prenom or "").strip() if prenom is not None else ""
                nom_disp = nom_disp if nom_disp else "-"
                prenom_disp = prenom_disp if prenom_disp else "-"
                self.tree.insert("", "end", iid=idpers, values=(nom_disp, prenom_disp, current_taux))
                inserted += 1
        self._refresh_table_alternating_colors(self.tree)
        if hasattr(self, "label_count"):
            self.label_count.configure(text=f"Personnel affichés : {inserted}")

    def _clear_form(self):
        self.selected_personnel_id = None
        self.selected_personnel_name.set("")
        self.current_rate_var.set("")
        self.new_rate_var.set("")
        if hasattr(self, "history_tree"):
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)

    def _on_select_personnel(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        try:
            pid = int(sel[0])
        except Exception:
            return
        values = self.tree.item(sel[0], "values")
        nom = values[0] if len(values) > 0 else "-"
        prenom = values[1] if len(values) > 1 else "-"
        taux = values[2] if len(values) > 2 else ""
        self.selected_personnel_id = pid
        nom_disp = (str(nom).strip() if nom is not None else "") or "-"
        prenom_disp = (str(prenom).strip() if prenom is not None else "") or "-"
        self.selected_personnel_name.set(f"{nom_disp} {prenom_disp}".strip())
        self.current_rate_var.set(str(taux) if taux is not None else "")
        self.new_rate_var.set("")
        self._load_history(pid)
        try:
            self.new_rate_entry.focus_set()
        except Exception:
            pass

    def _load_history(self, idpers: int, limit: int = 8):
        # [LOGIQUE] Lecture historique depuis tb_tauxhoraire
        if not getattr(self, "cursor", None) or not hasattr(self, "history_tree"):
            return
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        try:
            self.cursor.execute(
                "SELECT dateregistre, tauxhoraire FROM tb_tauxhoraire WHERE idpers=%s ORDER BY dateregistre DESC LIMIT %s",
                (int(idpers), int(limit)),
            )
            rows = self.cursor.fetchall()
            for d, t in rows:
                d_str = d.strftime("%Y-%m-%d %H:%M") if hasattr(d, "strftime") else str(d)
                try:
                    t_val = float(t) if t is not None else 0.0
                    t_str = f"{t_val:,.2f}".replace(",", " ").replace(".", ",")
                except Exception:
                    t_str = str(t)
                self.history_tree.insert("", "end", values=(d_str, t_str))
            self._refresh_table_alternating_colors(self.history_tree)
        except Exception:
            return

    def _enregistrer_taux(self):
        """Saves the entered hourly rate to the database (1 personnel)."""
        if not self.conn or not self.cursor:
            messagebox.showerror("Erreur", "Connexion à la base de données non établie.")
            return

        if not self.selected_personnel_id:
            messagebox.showerror("Erreur", "Veuillez sélectionner un personnel dans la liste.")
            return
        taux_in = (self.new_rate_var.get() or "").strip().replace(" ", "").replace(",", ".")
        if not taux_in:
            messagebox.showerror("Erreur", "Veuillez saisir le nouveau taux.")
            return
        try:
            taux_float = float(taux_in)
            if taux_float <= 0:
                messagebox.showerror("Erreur", "Le taux doit être supérieur à zéro.")
                return
        except ValueError:
            messagebox.showerror("Erreur", "Veuillez entrer un nombre valide pour le taux.")
            return

        now = datetime.now()
        try:
            self.cursor.execute(
                """
                INSERT INTO tb_tauxhoraire (tauxhoraire, idpers, dateregistre)
                VALUES (%s, %s, %s)
                """,
                (taux_float, int(self.selected_personnel_id), now),
            )
            self.conn.commit()
            try:
                self._logger.log(
                    action="Création taux horaire",
                    element=f"idpers={self.selected_personnel_id}",
                    details=f"Taux horaire enregistré (taux={taux_float}, date={now})",
                    value=str(taux_float),
                )
            except Exception:
                pass
            messagebox.showinfo("Succès", "Taux horaire enregistré avec succès.")
            pid = self.selected_personnel_id
            self._filter_personnel()
            if pid:
                # reselect and refresh history
                try:
                    self.tree.selection_set(str(pid))
                    self.tree.see(str(pid))
                except Exception:
                    pass
                self._load_history(pid)
            self._clear_form()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Erreur SQL", f"Erreur lors de l'enregistrement : {e}")


    def _on_closing(self):
        """Handles actions when the main application window is closed."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        # N'appelez pas self.master.destroy() ou self.app_root.destroy() ici
        # si PageTauxHoraire est une sous-fenêtre d'une application plus grande.
        # La fenêtre principale (root) doit gérer sa propre destruction.
        # Cette fonction doit seulement nettoyer les ressources spécifiques à cette page.
        self.app_root.destroy() # Si cette page est le contenu principal, ceci fermera la fenêtre principale


if __name__ == "__main__":
    # --- Main Application Window Setup ---
    ctk.set_appearance_mode("Light")  # Modes: "System" (default), "Dark", "Light"
    ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"

    root = ctk.CTk() # Ceci est la vraie fenêtre principale
    root.title("Mise à jour des taux horaires par professeur")
    root.geometry("700x400")
    
    # Create an instance of the PageTauxHoraire class
    # Passez 'root' comme master ET comme app_root si cette page est le contenu principal
    app = PageTauxHoraire(master=root, app_root=root)

    root.mainloop()
