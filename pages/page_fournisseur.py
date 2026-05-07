import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime
import json
import os
import textwrap
import subprocess
import tempfile
from resource_utils import get_config_path, safe_file_read
from settings_utils import load_settings, is_setting_enabled, open_file_if_enabled
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A5, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
try:
    from num2words import num2words
except ImportError:
    num2words = None

try:
    from app_theme import Colors, Fonts, styled, Theme
    _T = True
except ImportError:
    _T = False

from log_utils import AppLogger

# ── Constantes de police (cohérence globale) ─────────────────────────────────
_FONT_FAMILY  = "Roboto" if _T else "Segoe UI"
_FONT_SIZE_SM = 10   # labels secondaires, infos
_FONT_SIZE_MD = 11   # corps standard, entrées
_FONT_SIZE_LG = 13   # titres de section
_FONT_SIZE_XL = 14   # boutons importants

def _F(size=_FONT_SIZE_MD, weight="normal"):
    return ctk.CTkFont(family=_FONT_FAMILY, size=size, weight=weight)

# ── Style TTK centralisé ─────────────────────────────────────────────────────
def _apply_treeview_theme():
    """Configure le style ttk global : en-têtes dark, lignes lisibles, police Segoe UI."""
    style = ttk.Style()
    style.theme_use("default")

    style.configure(
        "Treeview.Heading",
        background="#2C3E50",
        foreground="#FFFFFF",
        font=(_FONT_FAMILY, _FONT_SIZE_SM, "bold"),
        relief="flat",
        padding=(8, 6),
    )
    style.map(
        "Treeview.Heading",
        background=[("active", "#34495E")],
        relief=[("active", "flat")],
    )

    style.configure(
        "Treeview",
        background="#FFFFFF",
        foreground="#2C3E50",
        fieldbackground="#FFFFFF",
        font=(_FONT_FAMILY, _FONT_SIZE_SM),
        rowheight=25,
        borderwidth=0,
    )
    style.map(
        "Treeview",
        background=[("selected", "#D6EAF8")],
        foreground=[("selected", "#1A5276")],
    )


class PageFournisseur(ctk.CTkFrame):
    def __init__(self, master, db_conn=None, session_data=None, id_user_connecte=None):
        super().__init__(master)

        self.session_data = session_data or {}
        self.id_user_connecte = id_user_connecte
        if self.id_user_connecte is None:
            self.id_user_connecte = (
                self.session_data.get("user_id")
                or self.session_data.get("iduser")
                or getattr(master, "id_user_connecte", None)
            )

        self.conn = self.connect_db()
        if self.conn:
            self.cursor = self.conn.cursor()
            self.create_table()

        self._logger = AppLogger(conn=self.conn, session_data=self.session_data, fallback_user_id=self.id_user_connecte)

        self.sort_column = "Dette en cours"
        self.sort_ascending = False

        _apply_treeview_theme()   # ← appliqué une seule fois à l'init
        self.setup_ui()
        self.load_fournisseur()

    # ──────────────────────────────────────────────────────────────────
    # BASE DE DONNÉES
    # ──────────────────────────────────────────────────────────────────

    def connect_db(self):
        try:
            if not os.path.exists(get_config_path('config.json')):
                messagebox.showerror("Erreur de configuration", "Le fichier config.json est manquant.")
                return None
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
            return conn
        except psycopg2.Error as err:
            messagebox.showerror("Erreur de connexion", f"Erreur : {err}")
            return None

    def create_table(self):
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS tb_fournisseur (
                    idfrs SERIAL PRIMARY KEY,
                    nomfrs VARCHAR(150),
                    contactfrs VARCHAR(50),
                    adressefrs VARCHAR(150),
                    nombanque VARCHAR(150),
                    comptebancaire VARCHAR(150),
                    adressebanque VARCHAR(150),
                    niffrs VARCHAR(20),
                    statfrs VARCHAR(20),
                    ciffrs VARCHAR(20),
                    dateregistre TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted INT DEFAULT 0
                )
            """)
            # Assure la présence des colonnes banque si la table existe déjà.
            self.cursor.execute("ALTER TABLE tb_fournisseur ADD COLUMN IF NOT EXISTS nombanque VARCHAR(150)")
            self.cursor.execute("ALTER TABLE tb_fournisseur ADD COLUMN IF NOT EXISTS comptebancaire VARCHAR(150)")
            self.cursor.execute("ALTER TABLE tb_fournisseur ADD COLUMN IF NOT EXISTS adressebanque VARCHAR(150)")
            self.conn.commit()
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors de la création de la table : {err}")

    # ──────────────────────────────────────────────────────────────────
    # UI PRINCIPALE
    # ──────────────────────────────────────────────────────────────────

    def setup_ui(self):
        self.pack(expand=True, fill="both", padx=20, pady=20)

        input_frame = ctk.CTkFrame(self)
        input_frame.pack(fill="x", pady=10)

        row1 = ctk.CTkFrame(input_frame)
        row1.pack(fill="x", pady=5)

        ctk.CTkLabel(row1, text="Nom du Fournisseur:", font=_F(_FONT_SIZE_SM)).pack(side="left", padx=5)
        self.nomFrs_entry = ctk.CTkEntry(row1, width=150, font=_F(_FONT_SIZE_MD))
        self.nomFrs_entry.pack(side="left", padx=5)

        ctk.CTkLabel(row1, text="Contact:", font=_F(_FONT_SIZE_SM)).pack(side="left", padx=5)
        self.contactFrs_entry = ctk.CTkEntry(row1, width=150, font=_F(_FONT_SIZE_MD))
        self.contactFrs_entry.pack(side="left", padx=5)

        ctk.CTkLabel(row1, text="Adresse:", font=_F(_FONT_SIZE_SM)).pack(side="left", padx=5)
        self.adresseFrs_entry = ctk.CTkEntry(row1, width=150, font=_F(_FONT_SIZE_MD))
        self.adresseFrs_entry.pack(side="left", padx=5)

        ctk.CTkLabel(row1, text="Nom Banque:", font=_F(_FONT_SIZE_SM)).pack(side="left", padx=5)
        self.nombanqueFrs_entry = ctk.CTkEntry(row1, width=130, font=_F(_FONT_SIZE_MD))
        self.nombanqueFrs_entry.pack(side="left", padx=5)

        row2 = ctk.CTkFrame(input_frame)
        row2.pack(fill="x", pady=5)

        ctk.CTkLabel(row2, text="Compte Bancaire:", font=_F(_FONT_SIZE_SM)).pack(side="left", padx=5)
        self.comptebancaireFrs_entry = ctk.CTkEntry(row2, width=130, font=_F(_FONT_SIZE_MD))
        self.comptebancaireFrs_entry.pack(side="left", padx=5)

        ctk.CTkLabel(row2, text="Adresse Banque:", font=_F(_FONT_SIZE_SM)).pack(side="left", padx=5)
        self.adressebanqueFrs_entry = ctk.CTkEntry(row2, width=150, font=_F(_FONT_SIZE_MD))
        self.adressebanqueFrs_entry.pack(side="left", padx=5)

        ctk.CTkLabel(row2, text="NIF:", font=_F(_FONT_SIZE_SM)).pack(side="left", padx=5)
        self.nifFrs_entry = ctk.CTkEntry(row2, width=120, font=_F(_FONT_SIZE_MD))
        self.nifFrs_entry.pack(side="left", padx=5)

        ctk.CTkLabel(row2, text="STAT:", font=_F(_FONT_SIZE_SM)).pack(side="left", padx=5)
        self.statFrs_entry = ctk.CTkEntry(row2, width=120, font=_F(_FONT_SIZE_MD))
        self.statFrs_entry.pack(side="left", padx=5)

        ctk.CTkLabel(row2, text="CIF:", font=_F(_FONT_SIZE_SM)).pack(side="left", padx=5)
        self.cifFrs_entry = ctk.CTkEntry(row2, width=120, font=_F(_FONT_SIZE_MD))
        self.cifFrs_entry.pack(side="left", padx=5)

        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", pady=10)

        ctk.CTkButton(button_frame, text="Ajouter", command=self.add_fournisseur,
                      fg_color="#2ecc71", hover_color="#27ae60",
                      font=_F(_FONT_SIZE_MD, "bold")).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Modifier", command=self.modify_fournisseur,
                      fg_color="#3498db", hover_color="#2980b9",
                      font=_F(_FONT_SIZE_MD, "bold")).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Supprimer", command=self.delete_fournisseur,
                      fg_color="#e74c3c", hover_color="#c0392b",
                      font=_F(_FONT_SIZE_MD, "bold")).pack(side="left", padx=5)

        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(search_frame, text="Rechercher Fournisseur :",
                     font=_F(_FONT_SIZE_MD, "bold")).pack(side="left", padx=5)
        self.search_entry = ctk.CTkEntry(search_frame, width=300,
                                         placeholder_text="Nom, contact, adresse, NIF...",
                                         font=_F(_FONT_SIZE_MD))
        self.search_entry.pack(side="left", padx=5, fill="x", expand=True)
        self.all_frs_data = []
        self.search_entry.bind("<KeyRelease>", self.filter_fournisseurs)

        # Treeview — tags couleur lignes alternées
        columns = ("Nom du Fournisseur", "Contact", "Adresse",
                   "Nom Banque", "Compte Bancaire", "Adresse Banque",
                   "NIF", "STAT", "CIF", "Dette en cours")

        tree_container = ctk.CTkFrame(self, fg_color="transparent")
        tree_container.pack(fill="both", expand=True, pady=10)
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(tree_container, columns=columns, show="headings")
        self.tree.tag_configure("even", background="#FFFFFF", foreground="#2C3E50")
        self.tree.tag_configure("odd",  background="#FEF9F0", foreground="#2C3E50")

        col_widths = {"Nom du Fournisseur": 160, "Contact": 110, "Adresse": 130,
                      "Nom Banque": 120, "Compte Bancaire": 120, "Adresse Banque": 130,
                      "NIF": 90, "STAT": 90, "CIF": 90, "Dette en cours": 130}
        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_by_column(c))
            self.tree.column(col, width=col_widths.get(col, 110), minwidth=80)
        self.tree.column("Dette en cours", anchor="e")

        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", self.on_frs_double_click)

        self.selected_frs_id = None

    # ──────────────────────────────────────────────────────────────────
    # CRUD FOURNISSEUR
    # ──────────────────────────────────────────────────────────────────

    def load_fournisseur(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        if not self.conn:
            return
        try:
            self.cursor.execute("""
                SELECT idfrs, nomfrs, contactfrs, adressefrs,
                       nombanque, comptebancaire, adressebanque,
                       niffrs, statfrs, ciffrs
                FROM tb_fournisseur
                WHERE deleted = 0
            """)
            fournisseurs = self.cursor.fetchall()

            fournisseurs_avec_dettes = []
            for frs in fournisseurs:
                try:
                    _, _, _, dette_restante, _ = self._compute_dette_status_fifo(frs[0])
                except Exception:
                    dette_restante = 0
                fournisseurs_avec_dettes.append((frs, dette_restante))

            fournisseurs_avec_dettes.sort(key=lambda x: x[1], reverse=True)
            self.all_frs_data = fournisseurs_avec_dettes
            self.display_fournisseurs(fournisseurs_avec_dettes)
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors du chargement : {err}")

    def display_fournisseurs(self, fournisseurs_avec_dettes):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for idx, (frs, dette_restante) in enumerate(fournisseurs_avec_dettes):
            tag = "even" if idx % 2 == 0 else "odd"
            dette_str = self._formater_nombre(dette_restante)
            self.tree.insert("", "end", iid=frs[0], values=(
                frs[1], frs[2], frs[3],
                frs[4] or "", frs[5] or "", frs[6] or "",
                frs[7], frs[8], frs[9], dette_str
            ), tags=(tag,))

    def sort_by_column(self, column):
        if self.sort_column == column:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = column
            self.sort_ascending = True

        if not self.all_frs_data:
            return

        col_index = {
            "Nom du Fournisseur": 1, "Contact": 2, "Adresse": 3,
            "Nom Banque": 4, "Compte Bancaire": 5, "Adresse Banque": 6,
            "NIF": 7, "STAT": 8, "CIF": 9, "Dette en cours": "dette"
        }

        if column == "Dette en cours":
            sorted_data = sorted(self.all_frs_data, key=lambda x: x[1], reverse=not self.sort_ascending)
        else:
            idx = col_index.get(column, 1)
            sorted_data = sorted(self.all_frs_data,
                                 key=lambda x: str(x[0][idx] or "").lower(),
                                 reverse=not self.sort_ascending)

        self.display_fournisseurs(sorted_data)

    def add_fournisseur(self):
        if not self.conn:
            return
        try:
            nomfrs = self.nomFrs_entry.get().strip()
            if not nomfrs:
                messagebox.showwarning("Attention", "Le nom est obligatoire.")
                return
            self.cursor.execute("""
                INSERT INTO tb_fournisseur
                    (nomfrs, contactfrs, adressefrs,
                     nombanque, comptebancaire, adressebanque,
                     niffrs, statfrs, ciffrs, dateregistre, deleted)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, 0)
            """, (nomfrs, self.contactFrs_entry.get(), self.adresseFrs_entry.get(),
                  self.nombanqueFrs_entry.get(), self.comptebancaireFrs_entry.get(),
                  self.adressebanqueFrs_entry.get(),
                  self.nifFrs_entry.get(), self.statFrs_entry.get(), self.cifFrs_entry.get()))
            self.conn.commit()
            self.load_fournisseur()
            self.clear_fields()
            messagebox.showinfo("Succès", "Fournisseur ajouté !")
            try:
                self._logger.log(
                    action="Création du fournisseur",
                    element=nomfrs,
                    details="Création fournisseur (CRUD Fournisseur)",
                    value="aucune valeur",
                )
            except Exception:
                pass
        except psycopg2.Error as err:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur : {err}")

    def modify_fournisseur(self):
        if not self.selected_frs_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner un fournisseur.")
            return
        try:
            old_name = ""
            try:
                self.cursor.execute("SELECT nomfrs FROM tb_fournisseur WHERE idfrs=%s", (self.selected_frs_id,))
                r = self.cursor.fetchone()
                old_name = r[0] if r and r[0] else ""
            except Exception:
                old_name = ""
            self.cursor.execute("""
                UPDATE tb_fournisseur
                SET nomfrs=%s, contactfrs=%s, adressefrs=%s,
                    nombanque=%s, comptebancaire=%s, adressebanque=%s,
                    niffrs=%s, statfrs=%s, ciffrs=%s
                WHERE idfrs=%s
            """, (self.nomFrs_entry.get(), self.contactFrs_entry.get(), self.adresseFrs_entry.get(),
                  self.nombanqueFrs_entry.get(), self.comptebancaireFrs_entry.get(),
                  self.adressebanqueFrs_entry.get(),
                  self.nifFrs_entry.get(), self.statFrs_entry.get(), self.cifFrs_entry.get(),
                  self.selected_frs_id))
            self.conn.commit()
            self.load_fournisseur()
            messagebox.showinfo("Succès", "Fournisseur modifié !")
            try:
                new_name = self.nomFrs_entry.get().strip()
                self._logger.log(
                    action="Modification du fournisseur",
                    element=old_name or f"idfrs={self.selected_frs_id}",
                    details=f"Fournisseur modifié en '{new_name}'",
                    value=f"idfrs={self.selected_frs_id}",
                )
            except Exception:
                pass
        except psycopg2.Error as err:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur : {err}")

    def delete_fournisseur(self):
        if not self.selected_frs_id:
            return
        if messagebox.askyesno("Confirmation", "Supprimer ce fournisseur ?"):
            try:
                frs_name = ""
                try:
                    self.cursor.execute("SELECT nomfrs FROM tb_fournisseur WHERE idfrs=%s", (self.selected_frs_id,))
                    r = self.cursor.fetchone()
                    frs_name = r[0] if r and r[0] else ""
                except Exception:
                    frs_name = ""
                self.cursor.execute("DELETE FROM tb_fournisseur WHERE idfrs = %s", (self.selected_frs_id,))
                self.conn.commit()
                self.load_fournisseur()
                self.clear_fields()
                try:
                    self._logger.log(
                        action="Suppression du fournisseur",
                        element=frs_name or f"idfrs={self.selected_frs_id}",
                        details="Suppression fournisseur (CRUD Fournisseur)",
                        value=f"idfrs={self.selected_frs_id}",
                    )
                except Exception:
                    pass
            except psycopg2.Error as err:
                messagebox.showerror("Erreur", f"Erreur : {err}")

    def on_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        self.selected_frs_id = selected[0]
        try:
            self.cursor.execute("""
                SELECT idfrs, nomfrs, contactfrs, adressefrs,
                       nombanque, comptebancaire, adressebanque,
                       niffrs, statfrs, ciffrs
                FROM tb_fournisseur WHERE idfrs = %s
            """, (self.selected_frs_id,))
            res = self.cursor.fetchone()
            if res:
                self.nomFrs_entry.delete(0, "end"); self.nomFrs_entry.insert(0, res[1] or "")
                self.contactFrs_entry.delete(0, "end"); self.contactFrs_entry.insert(0, res[2] or "")
                self.adresseFrs_entry.delete(0, "end"); self.adresseFrs_entry.insert(0, res[3] or "")
                self.nombanqueFrs_entry.delete(0, "end"); self.nombanqueFrs_entry.insert(0, res[4] or "")
                self.comptebancaireFrs_entry.delete(0, "end"); self.comptebancaireFrs_entry.insert(0, res[5] or "")
                self.adressebanqueFrs_entry.delete(0, "end"); self.adressebanqueFrs_entry.insert(0, res[6] or "")
                self.nifFrs_entry.delete(0, "end"); self.nifFrs_entry.insert(0, res[7] or "")
                self.statFrs_entry.delete(0, "end"); self.statFrs_entry.insert(0, res[8] or "")
                self.cifFrs_entry.delete(0, "end"); self.cifFrs_entry.insert(0, res[9] or "")
        except psycopg2.Error as err:
            print(err)

    def clear_fields(self):
        for entry in [self.nomFrs_entry, self.contactFrs_entry, self.adresseFrs_entry,
                      self.nombanqueFrs_entry, self.comptebancaireFrs_entry, self.adressebanqueFrs_entry,
                      self.nifFrs_entry, self.statFrs_entry, self.cifFrs_entry]:
            entry.delete(0, "end")
        self.selected_frs_id = None

    def filter_fournisseurs(self, event=None):
        search_query = self.search_entry.get().lower().strip()
        filtered_data = []
        for frs, dette_restante in self.all_frs_data:
            searchable_parts = [
                str(frs[0] or ""), str(frs[1] or ""), str(frs[2] or ""),
                str(frs[3] or ""), str(frs[4] or ""), str(frs[5] or ""),
                str(frs[6] or ""), str(frs[7] or ""), str(frs[8] or ""),
                str(frs[9] or ""), str(dette_restante or 0),
                self._formater_nombre(dette_restante),
            ]
            if not search_query or search_query in " ".join(searchable_parts).lower():
                filtered_data.append((frs, dette_restante))
        self.display_fournisseurs(filtered_data)

    # ──────────────────────────────────────────────────────────────────
    # DOUBLE-CLIC → DÉTAILS DETTE
    # ──────────────────────────────────────────────────────────────────

    def on_frs_double_click(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        self.open_frs_dette_details(selected[0])

    def open_frs_dette_details(self, idfrs):
        try:
            self.cursor.execute("""
                SELECT idfrs, nomfrs, contactfrs, adressefrs,
                       nombanque, comptebancaire, adressebanque,
                       niffrs, statfrs, ciffrs
                FROM tb_fournisseur WHERE idfrs = %s
            """, (idfrs,))
            frs_info = self.cursor.fetchone()
        except psycopg2.Error as err:
            try:
                if self.conn: self.conn.rollback()
            except Exception:
                pass
            messagebox.showerror("Erreur", f"Impossible de récupérer les infos du fournisseur: {err}")
            return

        if not frs_info:
            messagebox.showwarning("Attention", "Fournisseur non trouvé.")
            return

        detail_window = ctk.CTkToplevel(self)
        detail_window.title(f"Dettes Fournisseur - {frs_info[1]}")

        main_window = self.winfo_toplevel()
        main_window.update_idletasks()
        main_w = max(main_window.winfo_width(), 1)
        main_h = max(main_window.winfo_height(), 1)
        main_x = main_window.winfo_x()
        main_y = main_window.winfo_y()

        window_w = max(900, int(main_w * 0.5))
        window_h = max(650, int(main_h * 0.85))
        pos_x = main_x + (main_w - window_w) // 2
        pos_y = main_y + (main_h - window_h) // 2
        detail_window.geometry(f"{window_w}x{window_h}+{pos_x}+{pos_y}")
        detail_window.attributes("-topmost", False)

        detail_window.grid_columnconfigure(0, weight=0, minsize=350)
        detail_window.grid_columnconfigure(1, weight=1)
        detail_window.grid_rowconfigure(0, weight=1)

        # ── SIDEBAR GAUCHE ────────────────────────────────────────────────────
        sidebar_frame = ctk.CTkFrame(detail_window, fg_color="#fff8f0")
        sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        sidebar_frame.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(sidebar_frame, text="Informations Fournisseur",
                     font=_F(_FONT_SIZE_LG, "bold"),
                     text_color="#2c3e50").pack(anchor="w", padx=10, pady=(10, 5))

        info_data = [
            ("Nom:", frs_info[1]),
            ("Contact:", frs_info[2] or "N/A"),
            ("Adresse:", frs_info[3] or "N/A"),
            ("Nom Banque:", frs_info[4] or "N/A"),
            ("Compte Bancaire:", frs_info[5] or "N/A"),
            ("Adresse Banque:", frs_info[6] or "N/A"),
            ("NIF:", frs_info[7] or "N/A"),
            ("STAT:", frs_info[8] or "N/A"),
            ("CIF:", frs_info[9] or "N/A"),
        ]
        for label, value in info_data:
            row_f = ctk.CTkFrame(sidebar_frame, fg_color="transparent")
            row_f.pack(anchor="w", padx=10, pady=2, fill="x")
            ctk.CTkLabel(row_f, text=label, font=_F(_FONT_SIZE_SM, "bold"),
                         text_color="#34495e", width=80).pack(side="left", anchor="nw")
            ctk.CTkLabel(row_f, text=value, font=_F(_FONT_SIZE_SM),
                         text_color="#2c3e50").pack(side="left", anchor="nw", padx=(5, 0))

        ctk.CTkLabel(sidebar_frame, text="", fg_color="#bdc3c7", height=1).pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(sidebar_frame, text="Situation Dettes",
                     font=_F(_FONT_SIZE_LG, "bold"),
                     text_color="#2c3e50").pack(anchor="w", padx=10, pady=(5, 10))

        dette_info_frame = ctk.CTkFrame(sidebar_frame, fg_color="transparent")
        dette_info_frame.pack(anchor="w", padx=10, pady=2, fill="x")
        ctk.CTkLabel(dette_info_frame, text="Total Restant:", font=_F(_FONT_SIZE_SM, "bold"),
                     text_color="#34495e").pack(side="left", anchor="nw")
        label_montant_restant = ctk.CTkLabel(dette_info_frame, text="0,00 Ar",
                                             font=_F(_FONT_SIZE_LG, "bold"),
                                             text_color="#e74c3c")
        label_montant_restant.pack(side="left", anchor="nw", padx=(5, 0))

        btn_paiement_global = ctk.CTkButton(
            sidebar_frame, text="💸 Effectuer Paiement",
            fg_color="#e67e22", hover_color="#d35400",
            height=40, font=_F(_FONT_SIZE_MD, "bold"),
            command=lambda: None
        )
        btn_paiement_global.pack(padx=10, pady=10, fill="x")

        btn_ajouter_dette = ctk.CTkButton(
            sidebar_frame, text="➕ Ajouter Dette",
            fg_color="#8e44ad", hover_color="#7d3c98",
            height=40, font=_F(_FONT_SIZE_MD, "bold"),
            command=lambda: self._open_add_dette_window(idfrs, detail_window)
        )
        btn_ajouter_dette.pack(padx=10, pady=10, fill="x")

        # ── ZONE DROITE ───────────────────────────────────────────────────────
        right_frame = ctk.CTkFrame(detail_window)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(0, weight=1)
        right_frame.grid_rowconfigure(1, weight=1)

        # ── Tableau dettes ────────────────────────────────────────────────────
        table_frame = ctk.CTkFrame(right_frame)
        table_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=(0, 5))
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_columnconfigure(1, weight=0)
        table_frame.grid_rowconfigure(0, weight=0)
        table_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(table_frame, text="Récapitulatif des Dettes",
                     font=_F(_FONT_SIZE_LG, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))

        colonnes_dettes = ("ID", "Type", "Bon de Réception", "N° Facture Frs", "Date",
                           "Montant", "Montant Payé", "Solde Restant", "Statut")
        tree_dettes = ttk.Treeview(table_frame, columns=colonnes_dettes, show='headings', height=10)
        tree_dettes.tag_configure("complet", background="#D5F5E3", foreground="#1E8449")
        tree_dettes.tag_configure("partiel", background="#FEF9E7", foreground="#9A6A00")
        tree_dettes.tag_configure("impaye",  background="#FADBD8", foreground="#922B21")

        for col in colonnes_dettes:
            tree_dettes.heading(col, text=col)
            if col == "ID":
                tree_dettes.column(col, width=0, stretch=False)
            elif col in ("Montant", "Montant Payé", "Solde Restant"):
                tree_dettes.column(col, width=100, anchor='e')
            elif col in ("Bon de Réception", "N° Facture Frs"):
                tree_dettes.column(col, width=130, anchor='w')
            else:
                tree_dettes.column(col, width=110, anchor='w')

        scrollbar = ttk.Scrollbar(table_frame, command=tree_dettes.yview)
        tree_dettes.configure(yscrollcommand=scrollbar.set)
        tree_dettes.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=5)
        scrollbar.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=5)

        try:
            self._render_dette_table(tree_dettes, idfrs, label_montant_restant)

            def on_paiement_global_click():
                self._open_global_payment_window(idfrs, detail_window, tree_dettes, label_montant_restant)

            btn_paiement_global.configure(command=on_paiement_global_click)
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur chargement dettes: {err}")

        def on_dette_double_click(event):
            selected = tree_dettes.selection()
            if not selected:
                return
            item_iid = selected[0]
            values = tree_dettes.item(item_iid, "values")
            if not values:
                return
            dette_id = values[0]
            type_dette = values[1]
            if type_dette == "Livraison Reçue":
                self._open_livraison_detail_window(values[2], idfrs, detail_window)
            else:
                self._open_dette_manuelle_detail_window(dette_id, detail_window)

        tree_dettes.bind("<Double-1>", on_dette_double_click)

        # ── Tableau paiements ─────────────────────────────────────────────────
        payment_frame = ctk.CTkFrame(right_frame)
        payment_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=(5, 0))
        payment_frame.grid_columnconfigure(0, weight=1)
        payment_frame.grid_columnconfigure(1, weight=0)
        payment_frame.grid_rowconfigure(0, weight=0)
        payment_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(payment_frame, text="Historique des Paiements",
                     font=_F(_FONT_SIZE_LG, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))

        colonnes_pmt = ("ID", "Date Paiement", "Montant Payé", "Mode de Paiement", "Observation", "Utilisateur")
        tree_pmt = ttk.Treeview(payment_frame, columns=colonnes_pmt, show='headings', height=8)
        tree_pmt.tag_configure("even", background="#FFFFFF", foreground="#2C3E50")
        tree_pmt.tag_configure("odd",  background="#FEF9F0", foreground="#2C3E50")

        for col in colonnes_pmt:
            tree_pmt.heading(col, text=col)
            if col == "ID":
                tree_pmt.column(col, width=0, stretch=False)
            elif col == "Montant Payé":
                tree_pmt.column(col, width=120, anchor='e')
            elif col == "Date Paiement":
                tree_pmt.column(col, width=130, anchor='center')
            elif col == "Mode de Paiement":
                tree_pmt.column(col, width=120, anchor='w')
            else:
                tree_pmt.column(col, width=150, anchor='w')

        scrollbar_pmt = ttk.Scrollbar(payment_frame, command=tree_pmt.yview)
        tree_pmt.configure(yscrollcommand=scrollbar_pmt.set)
        tree_pmt.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=5)
        scrollbar_pmt.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=5)

        label_no_paiement = None
        def refresh_payment_history():
            nonlocal label_no_paiement
            for item in tree_pmt.get_children():
                tree_pmt.delete(item)
            if label_no_paiement is not None:
                try:
                    label_no_paiement.destroy()
                except Exception:
                    pass
                label_no_paiement = None

            try:
                self.cursor.execute("""
                    SELECT p.id, p.datepmt, p.mtpaye, p.observation,
                           COALESCE(m.modedepaiement, 'N/A') as mode_paiement,
                           COALESCE(CONCAT(u.prenomuser, ' ', u.nomuser), 'N/A') as utilisateur
                    FROM tb_pmtcom p
                    LEFT JOIN tb_users u ON p.iduser = u.iduser
                    LEFT JOIN tb_modepaiement m ON p.idmode = m.idmode
                    WHERE p.idfrs = %s
                    ORDER BY p.datepmt DESC
                """, (idfrs,))
                paiements = self.cursor.fetchall()

                for idx, pmt in enumerate(paiements):
                    pmt_id, date_pmt, montant_pmt, observation, mode_paiement, utilisateur = pmt
                    tag = "even" if idx % 2 == 0 else "odd"
                    tree_pmt.insert('', 'end', iid=f"pmt_{pmt_id}", values=(
                        pmt_id,
                        date_pmt.strftime("%d/%m/%Y %H:%M") if date_pmt else "N/A",
                        self._formater_nombre(montant_pmt or 0),
                        mode_paiement or "N/A",
                        observation or "",
                        utilisateur or "N/A"
                    ), tags=(tag,))

                if not paiements:
                    label_no_paiement = ctk.CTkLabel(payment_frame, text="Aucun paiement enregistré",
                                                         text_color="gray", font=_F(_FONT_SIZE_MD))
                    label_no_paiement.grid(row=1, column=0, pady=20)

            except psycopg2.Error as err:
                messagebox.showerror("Erreur", f"Erreur chargement paiements: {err}")

        refresh_payment_history()

    # ──────────────────────────────────────────────────────────────────
    # LOGIQUE FIFO DES DETTES FOURNISSEUR
    # ──────────────────────────────────────────────────────────────────

    def _fetch_frs_dettes(self, idfrs):
        self.cursor.execute("""
            SELECT
                lf.reflivfrs                                    AS id_ref,
                'Livraison Reçue'                               AS type,
                lf.reflivfrs                                    AS ref,
                MIN(lf.dateregistre)                            AS date_livraison,
                COALESCE(SUM(cd.punitcmd * lf.qtlivrefrs), 0)  AS montant,
                MIN(lf.datepaiement)                            AS dateecheance,
                lf.reflivfrs                                    AS bon_reception,
                MAX(lf.factfrs)                                 AS num_facture
            FROM tb_livraisonfrs lf
            JOIN tb_commandedetail cd
                ON cd.idcom = lf.idcom
               AND cd.idarticle = lf.idarticle
            WHERE cd.idfrs = %s
              AND lf.deleted = 0
              AND lf.a_payer = 1
            GROUP BY lf.reflivfrs
            ORDER BY MIN(lf.dateregistre) DESC
        """, (idfrs,))
        dettes_livraison = self.cursor.fetchall()

        self._ensure_autredette_table()
        self.cursor.execute("""
            SELECT id, 'Dette Manuelle' AS type, numfact, dateregistre, montant, dateecheance,
                   ''  AS bon_reception,
                   numfact AS num_facture
            FROM tb_autredette
            WHERE idfrs = %s
        """, (idfrs,))
        autres_dettes = self.cursor.fetchall()

        toutes_dettes = list(dettes_livraison) + list(autres_dettes)
        toutes_dettes.sort(key=lambda x: x[3] or datetime.min, reverse=True)
        return toutes_dettes

    def _ensure_autredette_table(self):
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS tb_autredette (
                    id SERIAL PRIMARY KEY,
                    idfrs INTEGER,
                    dateregistre TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    numfact VARCHAR(50),
                    montant DOUBLE PRECISION,
                    dateecheance DATE
                )
            """)
            self.conn.commit()
        except psycopg2.Error:
            try:
                self.conn.rollback()
            except Exception:
                pass

    def _compute_dette_status_fifo(self, idfrs):
        toutes_dettes_desc = self._fetch_frs_dettes(idfrs)

        self.cursor.execute("""
            SELECT COALESCE(SUM(mtpaye), 0)
            FROM tb_pmtcom
            WHERE idfrs = %s
        """, (idfrs,))
        total_paye_global = float(self.cursor.fetchone()[0] or 0)

        total_initial = sum(float(d[4] or 0) for d in toutes_dettes_desc)
        paid_remaining = total_paye_global

        dettes_asc = sorted(toutes_dettes_desc, key=lambda x: x[3] or datetime.min)
        status_map = {}

        for dette in dettes_asc:
            dette_id, type_dette, ref, date_dette, montant_initial, _, bon_rec, num_fact = dette
            montant_initial = float(montant_initial or 0)
            key = f"{type_dette}_{dette_id}"

            if paid_remaining >= montant_initial:
                montant_paye_ligne = montant_initial
                statut = "✓ Payé Complètement"
                tag = "complet"
                paid_remaining -= montant_initial
            elif paid_remaining > 0:
                montant_paye_ligne = paid_remaining
                statut = "⚠️ Partiellement Payé"
                tag = "partiel"
                paid_remaining = 0
            else:
                montant_paye_ligne = 0.0
                statut = "✗ Impayé"
                tag = "impaye"

            solde_restant = montant_initial - montant_paye_ligne
            status_map[key] = (montant_paye_ligne, solde_restant, statut, tag)

        total_restant = max(total_initial - total_paye_global, 0)
        return toutes_dettes_desc, total_initial, total_paye_global, total_restant, status_map

    def _render_dette_table(self, tree_dettes, idfrs, label_montant_restant=None):
        for item in tree_dettes.get_children():
            tree_dettes.delete(item)

        toutes_dettes_desc, total_initial, total_paye_global, total_restant, status_map = \
            self._compute_dette_status_fifo(idfrs)

        for dette in toutes_dettes_desc:
            dette_id, type_dette, ref, date_dette, montant_initial, _, bon_rec, num_fact = dette
            key = f"{type_dette}_{dette_id}"
            montant_paye_ligne, solde_restant, statut, tag = status_map.get(
                key, (0.0, float(montant_initial or 0), "✗ Impayé", "impaye"))

            tree_dettes.insert('', 'end', iid=key, values=(
                dette_id, type_dette, bon_rec or "", num_fact or "",
                date_dette.strftime("%d/%m/%Y %H:%M") if date_dette else "N/A",
                f"{self._formater_nombre(float(montant_initial or 0))}",
                f"{self._formater_nombre(montant_paye_ligne)}",
                f"{self._formater_nombre(solde_restant)}",
                statut
            ), tags=(tag,))

        if label_montant_restant is not None:
            label_montant_restant.configure(text=f"{self._formater_nombre(total_restant)} Ar")

        return total_initial, total_paye_global, total_restant

    def _open_livraison_detail_window(self, reflivfrs, idfrs, parent_window):
        try:
            self.cursor.execute("""
                SELECT
                    lf.reflivfrs,
                    MIN(lf.dateregistre)                            AS date_livraison,
                    MAX(lf.factfrs)                                 AS num_facture_frs,
                    MIN(lf.datepaiement)                            AS date_echeance,
                    COALESCE(MAX(CONCAT(u.prenomuser, ' ', u.nomuser)), 'N/A') AS operateur,
                    COALESCE(MAX(m.designationmag), 'N/A')          AS magasin,
                    c.refcom
                FROM tb_livraisonfrs lf
                JOIN tb_commandedetail cd ON cd.idcom = lf.idcom AND cd.idarticle = lf.idarticle
                JOIN tb_commande c ON c.idcom = lf.idcom
                LEFT JOIN tb_users u ON lf.iduser = u.iduser
                LEFT JOIN tb_magasin m ON lf.idmag = m.idmag
                WHERE lf.reflivfrs = %s AND cd.idfrs = %s AND lf.deleted = 0 AND lf.a_payer = 1
                GROUP BY lf.reflivfrs, c.refcom
                LIMIT 1
            """, (reflivfrs, idfrs))
            entete = self.cursor.fetchone()
            if not entete:
                messagebox.showinfo("Information", f"Aucune livraison trouvée pour le bon : {reflivfrs}")
                return
            ref, date_liv, num_fact, date_ech, operateur, magasin, refcom = entete

            self.cursor.execute("""
                SELECT
                    a.designation,
                    COALESCE(u.designationunite, '-')   AS unite,
                    lf.qtlivrefrs                       AS quantite,
                    cd.punitcmd                         AS prix_unit,
                    (cd.punitcmd * lf.qtlivrefrs)       AS montant_ligne
                FROM tb_livraisonfrs lf
                JOIN tb_commandedetail cd ON cd.idcom = lf.idcom AND cd.idarticle = lf.idarticle
                LEFT JOIN tb_article a ON a.idarticle = lf.idarticle
                LEFT JOIN tb_unite u ON u.idunite = lf.idunite
                WHERE lf.reflivfrs = %s AND cd.idfrs = %s AND lf.deleted = 0 AND lf.a_payer = 1
            """, (reflivfrs, idfrs))
            details = self.cursor.fetchall()
            montant_total = sum(float(d[4] or 0) for d in details)

        except psycopg2.Error as err:
            try:
                self.conn.rollback()
            except Exception:
                pass
            messagebox.showerror("Erreur", f"Erreur chargement livraison : {err}")
            return

        win = ctk.CTkToplevel(parent_window)
        win.title(f"Détails Livraison — {reflivfrs}")
        parent_window.update_idletasks()
        pw = max(parent_window.winfo_width(), 1)
        ph = max(parent_window.winfo_height(), 1)
        px = parent_window.winfo_x()
        py = parent_window.winfo_y()
        ww, wh = max(720, int(pw * 0.6)), max(500, int(ph * 0.75))
        win.geometry(f"{ww}x{wh}+{px + (pw - ww)//2}+{py + (ph - wh)//2}")
        win.minsize(720, 500)
        win.grab_set()
        win.grid_columnconfigure(0, weight=1)
        win.grid_rowconfigure(1, weight=1)

        info_frame = ctk.CTkFrame(win, fg_color="#fff8f0")
        info_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))

        ctk.CTkLabel(info_frame, text="Informations du Bon de Réception",
                     font=_F(_FONT_SIZE_LG, "bold"), text_color="#2c3e50"
                     ).grid(row=0, column=0, columnspan=6, sticky="w", padx=10, pady=(8, 4))

        infos = [
            ("Bon de Réception :", ref or "N/A"),
            ("N° Facture Frs :", num_fact or "N/A"),
            ("Bon de Commande :", refcom or "N/A"),
            ("Date Livraison :", date_liv.strftime("%d/%m/%Y %H:%M") if date_liv else "N/A"),
            ("Date Échéance :", date_ech.strftime("%d/%m/%Y") if date_ech else "N/A"),
            ("Magasin :", magasin),
            ("Opérateur :", operateur),
        ]
        row1_infos = infos[:4]
        row2_infos = infos[4:]
        for col_idx, (label, value) in enumerate(row1_infos):
            ctk.CTkLabel(info_frame, text=label,
                         font=_F(_FONT_SIZE_SM, "bold"), text_color="#34495e"
                         ).grid(row=1, column=col_idx * 2, sticky="w", padx=(10, 2), pady=(0, 4))
            ctk.CTkLabel(info_frame, text=value,
                         font=_F(_FONT_SIZE_SM), text_color="#2c3e50"
                         ).grid(row=1, column=col_idx * 2 + 1, sticky="w", padx=(0, 14), pady=(0, 4))
        for col_idx, (label, value) in enumerate(row2_infos):
            ctk.CTkLabel(info_frame, text=label,
                         font=_F(_FONT_SIZE_SM, "bold"), text_color="#34495e"
                         ).grid(row=2, column=col_idx * 2, sticky="w", padx=(10, 2), pady=(0, 8))
            ctk.CTkLabel(info_frame, text=value,
                         font=_F(_FONT_SIZE_SM), text_color="#2c3e50"
                         ).grid(row=2, column=col_idx * 2 + 1, sticky="w", padx=(0, 14), pady=(0, 8))

        detail_frame = ctk.CTkFrame(win)
        detail_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(4, 4))
        detail_frame.grid_columnconfigure(0, weight=1)
        detail_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(detail_frame, text="Articles Livrés",
                     font=_F(_FONT_SIZE_LG, "bold")
                     ).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 4))

        cols = ("Désignation", "Unité", "Quantité", "Prix Unitaire", "Montant")
        tree_detail = ttk.Treeview(detail_frame, columns=cols, show="headings", height=12)
        tree_detail.tag_configure("even", background="#FFFFFF", foreground="#2C3E50")
        tree_detail.tag_configure("odd",  background="#FEF9F0", foreground="#2C3E50")

        col_widths = {"Désignation": 220, "Unité": 70, "Quantité": 80, "Prix Unitaire": 110, "Montant": 110}
        col_anchor = {"Quantité": "e", "Prix Unitaire": "e", "Montant": "e"}
        for col in cols:
            tree_detail.heading(col, text=col)
            tree_detail.column(col, width=col_widths.get(col, 100), anchor=col_anchor.get(col, "w"))

        sb = ttk.Scrollbar(detail_frame, command=tree_detail.yview)
        tree_detail.configure(yscrollcommand=sb.set)
        tree_detail.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=5)
        sb.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=5)

        for idx, d in enumerate(details):
            designation, unite, qte, pu, montant_ligne = d
            tag = "even" if idx % 2 == 0 else "odd"
            tree_detail.insert("", "end", tags=(tag,), values=(
                designation or "-", unite or "-",
                f"{self._formater_nombre(qte or 0)}", f"{self._formater_nombre(pu or 0)}", f"{self._formater_nombre(montant_ligne or 0)}",
            ))

        total_frame = ctk.CTkFrame(win, fg_color="#f3e5f5")
        total_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(2, 4))
        ctk.CTkLabel(total_frame, text=f"Montant Total :  {self._formater_nombre(montant_total)} Ar",
                     font=_F(_FONT_SIZE_LG, "bold"), text_color="#6c3483"
                     ).pack(side="right", padx=20, pady=8)

        ctk.CTkButton(win, text="Fermer", command=win.destroy,
                      fg_color="#7f8c8d", width=100,
                      font=_F(_FONT_SIZE_MD)).grid(row=3, column=0, pady=(0, 10))

    def _open_dette_manuelle_detail_window(self, dette_id, parent_window):
        try:
            self.cursor.execute("""
                SELECT ad.id, ad.numfact, ad.dateregistre, ad.montant, ad.dateecheance,
                       f.nomfrs, f.contactfrs
                FROM tb_autredette ad
                LEFT JOIN tb_fournisseur f ON f.idfrs = ad.idfrs
                WHERE ad.id = %s
            """, (dette_id,))
            row = self.cursor.fetchone()
            if not row:
                messagebox.showinfo("Information", "Dette introuvable.")
                return
            ad_id, numfact, date_reg, montant, date_ech, nomfrs, contactfrs = row
        except psycopg2.Error as err:
            try:
                self.conn.rollback()
            except Exception:
                pass
            messagebox.showerror("Erreur", f"Erreur chargement dette : {err}")
            return

        win = ctk.CTkToplevel(parent_window)
        win.title(f"Détails Dette Manuelle — {numfact or ad_id}")
        parent_window.update_idletasks()
        pw = max(parent_window.winfo_width(), 1)
        ph = max(parent_window.winfo_height(), 1)
        px = parent_window.winfo_x(); py = parent_window.winfo_y()
        ww, wh = 460, 300
        win.geometry(f"{ww}x{wh}+{px + (pw - ww)//2}+{py + (ph - wh)//2}")
        win.resizable(False, False)
        win.grab_set()

        frame = ctk.CTkFrame(win, fg_color="#fff8f0")
        frame.pack(fill="both", expand=True, padx=14, pady=14)

        ctk.CTkLabel(frame, text="Informations de la Dette Manuelle",
                     font=_F(_FONT_SIZE_LG, "bold"), text_color="#2c3e50"
                     ).pack(anchor="w", padx=10, pady=(10, 8))

        infos = [
            ("Référence :", numfact or "N/A"),
            ("Date Enregistrement :", date_reg.strftime("%d/%m/%Y %H:%M") if date_reg else "N/A"),
            ("Date Échéance :", date_ech.strftime("%d/%m/%Y") if date_ech else "N/A"),
            ("Fournisseur :", nomfrs or "N/A"),
            ("Contact :", contactfrs or "N/A"),
            ("Montant :", f"{self._formater_nombre(montant or 0)} Ar"),
        ]
        for label, value in infos:
            row_f = ctk.CTkFrame(frame, fg_color="transparent")
            row_f.pack(anchor="w", padx=10, pady=3, fill="x")
            ctk.CTkLabel(row_f, text=label,
                         font=_F(_FONT_SIZE_MD, "bold"), text_color="#34495e",
                         width=190).pack(side="left")
            ctk.CTkLabel(row_f, text=value,
                         font=_F(_FONT_SIZE_MD), text_color="#2c3e50").pack(side="left")

        ctk.CTkButton(win, text="Fermer", command=win.destroy,
                      fg_color="#7f8c8d", width=100,
                      font=_F(_FONT_SIZE_MD)).pack(pady=(8, 10))

    # ──────────────────────────────────────────────────────────────────
    # FENÊTRE PAIEMENT GLOBAL
    # ──────────────────────────────────────────────────────────────────

    def _open_global_payment_window(self, idfrs, parent_window, tree_dettes, label_montant_restant):
        payment_window = ctk.CTkToplevel(parent_window)
        payment_window.title("Paiement Global des Dettes Fournisseur")
        parent_window.update_idletasks()
        parent_w = max(parent_window.winfo_width(), 1)
        parent_h = max(parent_window.winfo_height(), 1)
        parent_x = parent_window.winfo_x()
        parent_y = parent_window.winfo_y()

        win_w = max(620, int(parent_w * 0.5))
        win_h = max(490, int(parent_h * 0.6))
        pos_x = parent_x + (parent_w - win_w) // 2
        pos_y = parent_y + (parent_h - win_h) // 2
        payment_window.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
        payment_window.minsize(620, 490)
        payment_window.grab_set()
        payment_window.grid_columnconfigure(0, weight=1)
        payment_window.grid_rowconfigure(0, weight=1)

        main_frame = ctk.CTkFrame(payment_window)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        main_frame.grid_columnconfigure(0, weight=1)
        for i in range(9):
            main_frame.grid_rowconfigure(i, weight=0)
        main_frame.grid_rowconfigure(5, weight=1)

        _, dette_total_initial, dette_total_paye, dette_total_restant, _ = \
            self._compute_dette_status_fifo(idfrs)

        # ── Infos bancaires du fournisseur ────────────────────────────────
        try:
            self.cursor.execute("""
                SELECT nomfrs, nombanque, comptebancaire, adressebanque
                FROM tb_fournisseur WHERE idfrs = %s
            """, (idfrs,))
            frs_bank = self.cursor.fetchone()
            frs_nombanque = frs_bank[1] or "N/A" if frs_bank else "N/A"
            frs_comptebancaire = frs_bank[2] or "N/A" if frs_bank else "N/A"
            frs_adressebanque = frs_bank[3] or "N/A" if frs_bank else "N/A"
        except Exception:
            frs_nombanque = frs_comptebancaire = frs_adressebanque = "N/A"

        info_text = (
            f"Récapitulatif des Dettes Fournisseur (ID: {idfrs})\n\n"
            f"Montant Total des Dettes: {self._formater_nombre(dette_total_initial)} Ar\n"
            f"Montant Total Déjà Payé: {self._formater_nombre(dette_total_paye)} Ar\n"
            f"Solde Total Restant: {self._formater_nombre(dette_total_restant)} Ar"
        )

        ctk.CTkLabel(main_frame, text=info_text, justify="left", anchor="w",
                     font=_F(_FONT_SIZE_MD, "bold")).grid(
            row=0, column=0, sticky="ew", padx=8, pady=(8, 6))

        # ── Bloc infos bancaires (badge) ───────────────────────────────────
        bank_frame = ctk.CTkFrame(
            main_frame, fg_color="#eaf4fb",
            corner_radius=8, border_width=1, border_color="#aed6f1"
        )
        bank_frame.grid(row=0, column=0, sticky="se", padx=8, pady=(6, 2))
        ctk.CTkLabel(
            bank_frame,
            text="🏦  Coordonnées Bancaires",
            font=_F(_FONT_SIZE_SM, "bold"), text_color="#1a5276"
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=(6, 2), sticky="w")
        for r_idx, (lbl, val) in enumerate([
            ("Banque :", frs_nombanque),
            ("N° Compte :", frs_comptebancaire),
            ("Adresse Banque :", frs_adressebanque),
        ], start=1):
            ctk.CTkLabel(
                bank_frame, text=lbl,
                font=_F(_FONT_SIZE_SM, "bold"), text_color="#2980b9"
            ).grid(row=r_idx, column=0, padx=(10, 4), pady=2, sticky="w")
            ctk.CTkLabel(
                bank_frame, text=val,
                font=_F(_FONT_SIZE_SM), text_color="#1a5276"
            ).grid(row=r_idx, column=1, padx=(0, 10), pady=2, sticky="w")
        ctk.CTkFrame(bank_frame, height=4, fg_color="transparent").grid(row=4, column=0)

        ctk.CTkLabel(main_frame, text=f"Montant Global à Payer (max: {self._formater_nombre(dette_total_restant)} Ar):",
                     font=_F(_FONT_SIZE_MD, "bold")).grid(row=1, column=0, sticky="w", padx=8, pady=(0, 4))
        entry_montant = ctk.CTkEntry(main_frame, font=_F(_FONT_SIZE_MD))
        entry_montant.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))

        ctk.CTkLabel(main_frame, text="Observation (optionnel):",
                     font=_F(_FONT_SIZE_MD, "bold")).grid(row=3, column=0, sticky="w", padx=8, pady=(2, 4))
        entry_obs = ctk.CTkEntry(main_frame, font=_F(_FONT_SIZE_MD))
        entry_obs.grid(row=4, column=0, sticky="ew", padx=8, pady=(0, 8))

        ctk.CTkLabel(main_frame,
                     text="Le paiement sera distribué automatiquement par ancienneté (commandes les plus anciennes d'abord).",
                     text_color="#95a5a6", justify="left", anchor="w", wraplength=560,
                     font=_F(_FONT_SIZE_SM)).grid(
            row=5, column=0, sticky="ew", padx=8, pady=(0, 8))

        try:
            self.cursor.execute("SELECT idmode, modedepaiement FROM tb_modepaiement ORDER BY modedepaiement")
            modes = self.cursor.fetchall()
        except Exception:
            modes = []

        mode_names = [m[1] for m in modes] if modes else []
        mode_map = {m[1]: m[0] for m in modes} if modes else {}

        ctk.CTkLabel(main_frame, text="Mode de Paiement:",
                     font=_F(_FONT_SIZE_MD, "bold")).grid(row=6, column=0, sticky="w", padx=8, pady=(0, 4))
        mode_combo = ctk.CTkComboBox(main_frame, values=mode_names, font=_F(_FONT_SIZE_MD))
        if mode_names:
            default_mode = "Espèces" if "Espèces" in mode_names else mode_names[0]
            mode_combo.set(default_mode)
        mode_combo.grid(row=7, column=0, sticky="ew", padx=8, pady=(0, 10))

        def enregistrer_paiement_global():
            try:
                montant_global = float(entry_montant.get().replace(',', '.'))
                observation = entry_obs.get().strip()

                if montant_global <= 0:
                    messagebox.showwarning("Attention", "Le montant doit être supérieur à 0.")
                    return
                if montant_global > dette_total_restant:
                    messagebox.showwarning("Attention",
                                           f"Le montant dépasse le solde total ({self._formater_nombre(dette_total_restant)} Ar).")
                    return

                selected_mode = mode_combo.get() if mode_names else None
                idmode_sel = mode_map.get(selected_mode) if selected_mode else None

                frs_nom = self._get_frs_name(idfrs)
                observation_full = f"Paiement dette fournisseur : {frs_nom}" + \
                                   (f" ({observation})" if observation else "")

                date_pmt = datetime.now()
                ref_ticket = f"PMTF-{idfrs}-{date_pmt.strftime('%Y%m%d%H%M%S')}"
                iduser = self._get_connected_user_id()

                self.cursor.execute("""
                    INSERT INTO tb_pmtcom
                    (datepmt, mtpaye, observation, idtypeoperation, idfrs, refcom, idmode, idpaiment, refpmt, id_banque, iduser)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (date_pmt, montant_global, observation_full, 2, idfrs,
                      None, idmode_sel, None, ref_ticket, None, iduser))
                self.conn.commit()

                try:
                    self._logger.log(
                        action="Paiement dette fournisseur",
                        element=frs_nom or f"idfrs={idfrs}",
                        details=f"Paiement global dette fournisseur, ref={ref_ticket}, mode={selected_mode or 'N/A'}",
                        value=f"{montant_global} Ar",
                    )
                except Exception:
                    pass

                messagebox.showinfo("Succès", f"Paiement de {self._formater_nombre(montant_global)} Ar enregistré avec succès!")

                societe_data = self._get_societe_info()
                societe_tuple = (
                    societe_data.get('name', ''), societe_data.get('addr', ''),
                    societe_data.get('ville', ''), societe_data.get('tel', ''),
                )
                username = self._get_username_by_id(iduser)
                articles = [("", "Paiement global dette fournisseur", "", 1,
                              float(montant_global), float(montant_global))]

                settings = load_settings()
                open_a5 = is_setting_enabled("Fournisseur_PmtDette_OpenA5", default=0, settings=settings)
                facture_path = self._generer_ticket_pdf_paiement_dette(
                    societe=societe_tuple, username=username, articles=articles,
                    montant=float(montant_global), mode_nom=selected_mode or "Espèces",
                    refpmt=ref_ticket, idfrs=idfrs, frs_nom=frs_nom,
                    observation=observation_full, date_paiement=date_pmt,
                    open_after=open_a5, output_format="A5",
                    open_setting_key="Fournisseur_PmtDette_OpenA5", open_setting_default=0,
                )
                if facture_path:
                    messagebox.showinfo("Confirmation", "Le PDF de paiement a été généré.")
                    open_ticket = is_setting_enabled("Fournisseur_PmtDette_OpenTicket80", default=0, settings=settings)
                    ticket_path = self._generer_ticket_pdf_paiement_dette(
                        societe=societe_tuple, username=username, articles=articles,
                        montant=float(montant_global), mode_nom=selected_mode or "Espèces",
                        refpmt=ref_ticket, idfrs=idfrs, frs_nom=frs_nom,
                        observation=observation_full, date_paiement=date_pmt,
                        open_after=open_ticket, output_format="ticket80",
                        open_setting_key="Fournisseur_PmtDette_OpenTicket80", open_setting_default=0,
                    )
                    if open_ticket and ticket_path:
                        messagebox.showinfo("Confirmation", "Le ticket 80mm a été généré et ouvert.")

                self._render_dette_table(tree_dettes, idfrs, label_montant_restant)
                self.load_fournisseur()
                payment_window.destroy()

            except ValueError:
                messagebox.showerror("Erreur", "Veuillez entrer un montant valide.")
            except psycopg2.Error as err:
                self.conn.rollback()
                messagebox.showerror("Erreur", f"Erreur enregistrement paiement: {err}")

        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.grid(row=8, column=0, sticky="e", padx=8, pady=(6, 4))

        ctk.CTkButton(btn_frame, text="Effectuer le Paiement",
                      command=enregistrer_paiement_global,
                      fg_color="#e67e22", width=170,
                      font=_F(_FONT_SIZE_MD, "bold")).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Annuler",
                      command=payment_window.destroy,
                      fg_color="#e74c3c", width=130,
                      font=_F(_FONT_SIZE_MD, "bold")).pack(side="left", padx=5)

    # ──────────────────────────────────────────────────────────────────
    # FENÊTRE AJOUTER DETTE MANUELLE
    # ──────────────────────────────────────────────────────────────────

    def _open_add_dette_window(self, idfrs, parent_window):
        dette_window = ctk.CTkToplevel(parent_window)
        dette_window.title("Ajouter une Dette Fournisseur")
        parent_window.update_idletasks()
        parent_w = max(parent_window.winfo_width(), 1)
        parent_h = max(parent_window.winfo_height(), 1)
        parent_x = parent_window.winfo_x()
        parent_y = parent_window.winfo_y()

        win_w = max(560, int(parent_w * 0.45))
        win_h = max(360, int(parent_h * 0.5))
        pos_x = parent_x + (parent_w - win_w) // 2
        pos_y = parent_y + (parent_h - win_h) // 2
        dette_window.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
        dette_window.minsize(560, 360)
        dette_window.grab_set()
        dette_window.grid_columnconfigure(0, weight=1)
        dette_window.grid_rowconfigure(0, weight=1)

        main_frame = ctk.CTkFrame(dette_window)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        main_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(main_frame, text="Enregistrer une Dette Manuelle",
                     font=_F(_FONT_SIZE_LG, "bold")).grid(
            row=0, column=0, sticky="w", padx=8, pady=(8, 10))

        ctk.CTkLabel(main_frame, text="Référence (N° Facture Fournisseur) :",
                     font=_F(_FONT_SIZE_MD, "bold")).grid(row=1, column=0, sticky="w", padx=8, pady=(2, 4))
        entry_numfact = ctk.CTkEntry(main_frame, placeholder_text="Ex: FACT-FRS-001",
                                     font=_F(_FONT_SIZE_MD))
        entry_numfact.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))

        ctk.CTkLabel(main_frame, text="Montant (Ar) :",
                     font=_F(_FONT_SIZE_MD, "bold")).grid(row=3, column=0, sticky="w", padx=8, pady=(2, 4))
        entry_montant = ctk.CTkEntry(main_frame, placeholder_text="Ex: 150000",
                                     font=_F(_FONT_SIZE_MD))
        entry_montant.grid(row=4, column=0, sticky="ew", padx=8, pady=(0, 8))

        def enregistrer_dette():
            try:
                num_fact = entry_numfact.get().strip()
                montant_str = entry_montant.get().strip()

                if not num_fact or not montant_str:
                    messagebox.showwarning("Attention", "Veuillez remplir tous les champs.")
                    return

                montant = float(montant_str.replace(',', '.'))
                if montant <= 0:
                    messagebox.showwarning("Attention", "Le montant doit être supérieur à 0.")
                    return

                self.cursor.execute("""
                    SELECT setval(
                        pg_get_serial_sequence('tb_autredette', 'id'),
                        COALESCE((SELECT MAX(id) FROM tb_autredette), 0) + 1, false)
                """)
                self.cursor.execute("""
                    INSERT INTO tb_autredette (idfrs, dateregistre, numfact, montant)
                    VALUES (%s, %s, %s, %s)
                """, (idfrs, datetime.now(), num_fact, montant))
                self.conn.commit()

                try:
                    frs_nom = self._get_frs_name(idfrs)
                    self._logger.log(
                        action="Création de dette fournisseur",
                        element=frs_nom or f"idfrs={idfrs}",
                        details=f"Dette manuelle ref='{num_fact}'",
                        value=f"{montant} Ar",
                    )
                except Exception:
                    pass

                messagebox.showinfo("Succès", f"Dette de {self._formater_nombre(montant)} Ar enregistrée avec succès!")

                username = self._get_username_by_id(self._get_connected_user_id())
                societe_data = self._get_societe_info()
                societe_tuple = (
                    societe_data.get('name', ''), societe_data.get('addr', ''),
                    societe_data.get('ville', ''), societe_data.get('tel', ''),
                )
                articles = [("", "Dette manuelle fournisseur", "", 1, float(montant), float(montant))]
                observation = f"Dette manuelle fournisseur : {num_fact}"
                settings = load_settings()
                open_ticket = is_setting_enabled("Fournisseur_Dette_OpenTicketPdf", default=0, settings=settings)
                ticket_path = self._generer_ticket_pdf_dette(
                    societe=societe_tuple, username=username, articles=articles,
                    montant=float(montant), mode_nom="Dette", refpmt=num_fact,
                    frs_nom=self._get_frs_name(idfrs), montant_total=float(montant), open_after=open_ticket
                )
                if ticket_path:
                    messagebox.showinfo("Confirmation", "Le ticket PDF de dette a été généré.")
                    open_a5 = is_setting_enabled("Fournisseur_Dette_OpenA5", default=0, settings=settings)
                    facture_a5_path = self._generer_ticket_pdf_paiement_dette(
                        societe=societe_tuple, username=username, articles=articles,
                        montant=float(montant), mode_nom="Dette", refpmt=num_fact,
                        idfrs=idfrs, frs_nom=self._get_frs_name(idfrs),
                        observation=observation, date_paiement=datetime.now(),
                        open_after=open_a5, output_format="A5",
                        operation_title="VALIDATION DETTE FOURNISSEUR", info_title="Infos Dette Fournisseur",
                        open_setting_key="Fournisseur_Dette_OpenA5", open_setting_default=0,
                    )
                    if open_a5 and facture_a5_path:
                        messagebox.showinfo("Confirmation", "La facture PDF A5 de dette a été générée.")

                self.load_fournisseur()
                dette_window.destroy()
                parent_window.destroy()
                self.open_frs_dette_details(idfrs)

            except ValueError:
                messagebox.showerror("Erreur", "Veuillez entrer un montant valide (nombre).")
            except psycopg2.Error as err:
                self.conn.rollback()
                messagebox.showerror("Erreur", f"Erreur enregistrement dette: {err}")

        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.grid(row=5, column=0, sticky="e", padx=8, pady=(10, 6))

        ctk.CTkButton(btn_frame, text="Enregistrer", command=enregistrer_dette,
                      fg_color="#8e44ad", font=_F(_FONT_SIZE_MD, "bold")).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Annuler", command=dette_window.destroy,
                      fg_color="#e74c3c", font=_F(_FONT_SIZE_MD, "bold")).pack(side="left", padx=5)

    # ──────────────────────────────────────────────────────────────────
    # GÉNÉRATION PDF — inchangée
    # ──────────────────────────────────────────────────────────────────

    def _generer_ticket_pdf_paiement_dette(
        self,
        societe,
        username,
        articles,
        montant,
        mode_nom,
        refpmt,
        idfrs,
        frs_nom,
        observation,
        date_paiement,
        open_after=False,
        output_format="A5",
        operation_title="PAIEMENT DETTE FOURNISSEUR",
        info_title="Infos Paiement Dette Fournisseur",
        open_setting_key: str | None = None,
        open_setting_default: int = 0,
    ):
        try:
            frs_adresse = "-"; frs_contact = "-"
            try:
                self.cursor.execute(
                    "SELECT adressefrs, contactfrs FROM tb_fournisseur WHERE idfrs = %s", (idfrs,))
                row = self.cursor.fetchone()
                if row: frs_adresse = row[0] or "-"; frs_contact = row[1] or "-"
            except Exception:
                try: self.conn.rollback()
                except: pass

            temp_dir = tempfile.gettempdir()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nom_soc  = societe[0] if societe else "IJEERY"
            adr_soc  = societe[1] if societe and len(societe) > 1 else ""
            ville_soc= societe[2] if societe and len(societe) > 2 else ""
            contact_soc = societe[3] if societe and len(societe) > 3 else ""

            if str(output_format).lower() == "ticket80":
                path = os.path.join(temp_dir,
                    f"Paiement_Dette_Frs_Ticket80_{refpmt}_{timestamp}.pdf")

                ticket_width = 80 * mm
                ticket_height = 200 * mm
                c = canvas.Canvas(path, pagesize=(ticket_width, ticket_height))
                y = ticket_height - 10 * mm
                x_center = ticket_width / 2
                margin = 5 * mm

                c.setFont("Helvetica-Bold", 12)
                c.drawCentredString(x_center, y, (nom_soc or "IJEERY").upper())
                y -= 5 * mm
                c.setFont("Helvetica", 8)
                if adr_soc:
                    c.drawCentredString(x_center, y, adr_soc)
                    y -= 4 * mm
                if ville_soc:
                    c.drawCentredString(x_center, y, ville_soc)
                    y -= 4 * mm
                if contact_soc:
                    c.drawCentredString(x_center, y, f"Tél: {contact_soc}")
                    y -= 6 * mm

                c.line(margin, y, ticket_width - margin, y)
                y -= 7 * mm
                c.setFont("Helvetica-Bold", 11)
                c.drawCentredString(x_center, y, operation_title)
                y -= 8 * mm
                c.line(margin, y, ticket_width - margin, y)
                y -= 7 * mm

                c.setFont("Helvetica", 9)
                c.drawString(margin, y, f"Date: {date_paiement.strftime('%d/%m/%Y %H:%M')}")
                y -= 5 * mm
                c.drawString(margin, y, f"Réf: {refpmt}")
                y -= 5 * mm
                c.drawString(margin, y, f"Fournisseur: {frs_nom}")
                y -= 5 * mm
                c.drawString(margin, y, f"Mode: {mode_nom}")
                y -= 5 * mm
                c.drawString(margin, y, f"Opérateur: {username}")
                y -= 7 * mm

                c.line(margin, y, ticket_width - margin, y)
                y -= 7 * mm
                c.setFont("Helvetica-Bold", 10)
                c.drawString(margin, y, "Montant payé :")
                c.drawRightString(ticket_width - margin, y, f"{self._formater_nombre(montant)} Ar")
                y -= 10 * mm

                try:
                    _, _, _, total_restant, _ = self._compute_dette_status_fifo(idfrs)
                except Exception:
                    total_restant = 0
                c.setFont("Helvetica", 9)
                c.drawString(margin, y, "Reste de Dette :")
                c.drawRightString(ticket_width - margin, y, f"{self._formater_nombre(total_restant)} Ar")
                y -= 8 * mm
                c.line(margin, y, ticket_width - margin, y)
                y -= 7 * mm

                c.setFont("Helvetica-Bold", 9)
                c.drawString(margin, y, "Observation :")
                y -= 4 * mm
                c.setFont("Helvetica", 8)
                current_line = ""
                max_width = ticket_width - 2 * margin
                for mot in str(observation or "").split():
                    test_line = f"{current_line} {mot}".strip() if current_line else mot
                    if c.stringWidth(test_line, "Helvetica", 8) <= max_width:
                        current_line = test_line
                    else:
                        c.drawString(margin, y, current_line)
                        y -= 4 * mm
                        current_line = mot
                if current_line:
                    c.drawString(margin, y, current_line)
                    y -= 7 * mm

                c.line(margin, y, ticket_width - margin, y)
                y -= 7 * mm
                c.setFont("Helvetica", 8)
                c.drawCentredString(x_center, y, "Merci de votre confiance")
                y -= 4 * mm
                c.drawCentredString(x_center, y, "Document non contractuel")
                c.save()

                if open_after:
                    open_file_if_enabled(
                        path,
                        operation="open",
                        setting_key="Fournisseur_PmtDette_OpenTicket80",
                        setting_default=0,
                    )
                return path

            path = os.path.join(temp_dir,
                f"Paiement_Dette_Frs_{refpmt}_{timestamp}.pdf")

            page_width, _ = landscape(A5)
            margin = 5 * mm
            usable_width = page_width - 2 * margin

            doc = SimpleDocTemplate(path, pagesize=landscape(A5),
                                    rightMargin=margin, leftMargin=margin,
                                    topMargin=margin, bottomMargin=margin)
            elements = []
            styles = getSampleStyleSheet()
            color_header = colors.HexColor("#7d3c98")

            verse_title = Paragraph(
                "Ankino amin'ny Jehovah ny asanao dia ho lavorary izay kasainao. Ohabolana 16:3",
                ParagraphStyle("VerseFrs", parent=styles["Normal"], fontSize=10,
                               textColor=colors.black, alignment=TA_CENTER,
                               fontName="Helvetica-Bold", spaceAfter=3))
            verse_table = Table([[verse_title]], colWidths=[usable_width])
            verse_table.setStyle(TableStyle([
                ("BOX",(0,0),(-1,-1),1,colors.black), ("ALIGN",(0,0),(-1,-1),"CENTER"),
                ("VALIGN",(0,0),(-1,-1),"MIDDLE"), ("TOPPADDING",(0,0),(-1,-1),0),
                ("BOTTOMPADDING",(0,0),(-1,-1),3)]))
            elements.append(verse_table)

            company_width = usable_width * 0.33
            right_width   = usable_width * 0.67 - 2 * mm
            title_width   = right_width * 0.55
            info_width    = right_width * 0.45
            header_height = 28 * mm

            nom_soc  = societe[0] if societe else "IJEERY"
            adr_soc  = societe[1] if societe and len(societe) > 1 else ""
            ville_soc= societe[2] if societe and len(societe) > 2 else ""
            contact_soc = societe[3] if societe and len(societe) > 3 else ""

            company_details = Paragraph(
                f"<b>{nom_soc}</b><br/>Adresse : {adr_soc}<br/>Ville : {ville_soc}<br/>Contact : {contact_soc}<br/>",
                ParagraphStyle("CompanyFrs", parent=styles["Normal"], fontSize=9, alignment=TA_LEFT, leading=12))
            company_table = Table([[company_details]], colWidths=[company_width - 2*mm], rowHeights=[header_height])
            company_table.setStyle(TableStyle([
                ("BOX",(0,0),(-1,-1),1,colors.black), ("VALIGN",(0,0),(-1,-1),"TOP"),
                ("TOPPADDING",(0,0),(-1,-1),6), ("BOTTOMPADDING",(0,0),(-1,-1),6),
                ("LEFTPADDING",(0,0),(-1,-1),6), ("RIGHTPADDING",(0,0),(-1,-1),6)]))

            op_title = Paragraph(operation_title,
                ParagraphStyle("OpFrsTitle", parent=styles["Normal"], fontSize=12,
                               fontName="Helvetica-Bold", alignment=TA_CENTER, textColor=color_header))
            operation_info = Paragraph(
                f"<b>Reference :</b> {refpmt}<br/>"
                f"<b>Date et heure :</b> {date_paiement.strftime('%d/%m/%Y %H:%M')}<br/>"
                f"<b>Mode de paiement :</b> {mode_nom}<br/>"
                f"<b>Operateur :</b> {username}",
                ParagraphStyle("OpFrsInfo", parent=styles["Normal"], fontSize=9, alignment=TA_LEFT, leading=12))
            operation_table = Table([[op_title, operation_info]],
                                     colWidths=[title_width, info_width], rowHeights=[header_height])
            operation_table.setStyle(TableStyle([
                ("BOX",(0,0),(-1,-1),1,colors.black), ("ALIGN",(0,0),(0,0),"CENTER"),
                ("VALIGN",(0,0),(-1,-1),"MIDDLE"), ("TOPPADDING",(0,0),(-1,-1),6),
                ("BOTTOMPADDING",(0,0),(-1,-1),6), ("LEFTPADDING",(0,0),(-1,-1),6),
                ("RIGHTPADDING",(0,0),(-1,-1),6)]))

            header_table = Table([[company_table, operation_table]], colWidths=[company_width, right_width])
            header_table.setStyle(TableStyle([
                ("VALIGN",(0,0),(-1,-1),"TOP"), ("TOPPADDING",(0,0),(-1,-1),4),
                ("BOTTOMPADDING",(0,0),(-1,-1),4), ("RIGHTPADDING",(0,0),(0,0),8),
                ("LEFTPADDING",(1,0),(1,0),8)]))
            elements.append(header_table)
            elements.append(Spacer(1, 3*mm))

            elements.append(Paragraph(f"<b><u>{info_title}</u></b><br/>",
                ParagraphStyle("InfoDetteLine", parent=styles["Normal"], fontSize=9,
                               alignment=TA_CENTER, leading=11)))
            elements.append(Spacer(1, 2*mm))

            try:
                _, _, _, total_restant, _ = self._compute_dette_status_fifo(idfrs)
            except: total_restant = 0

            table_width = usable_width * 0.95
            col_widths_t = [table_width*0.25, table_width*0.43, table_width*0.32]
            table_data = [["Reference","Nom Fournisseur","Montant"],
                          [refpmt, frs_nom, self._formater_nombre(montant) + " Ar"],
                          ["Reste de Dette", "", self._formater_nombre(total_restant) + " Ar"]]
            last_row = len(table_data) - 1
            dette_table = Table(table_data, colWidths=col_widths_t, repeatRows=1)
            dette_table.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#F3E5F5")),
                ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"), ("FONTSIZE",(0,0),(-1,0),12),
                ("ALIGN",(0,0),(-1,0),"CENTER"), ("ALIGN",(0,1),(1,-2),"LEFT"),
                ("ALIGN",(2,1),(2,-2),"CENTER"), ("FONTSIZE",(0,1),(-1,-1),8),
                ("BOX",(0,0),(-1,-1),1,colors.black), ("LINEBEFORE",(1,0),(1,-1),1,color_header),
                ("LINEBEFORE",(2,0),(2,-1),1,color_header), ("TOPPADDING",(0,0),(-1,-1),4),
                ("BOTTOMPADDING",(0,0),(-1,-1),4), ("SPAN",(0,last_row),(1,last_row)),
                ("ALIGN",(0,last_row),(1,last_row),"RIGHT"), ("ALIGN",(2,last_row),(2,last_row),"CENTER"),
                ("FONTNAME",(0,last_row),(2,last_row),"Helvetica-Bold"),
                ("FONTSIZE",(0,last_row),(2,last_row),10),
                ("BACKGROUND",(0,last_row),(2,last_row),colors.HexColor("#F5F5F5")),
                ("LINEABOVE",(0,last_row),(2,last_row),1,color_header)]))
            elements.append(dette_table)
            elements.append(Spacer(1, 3*mm))
            elements.append(Paragraph(f"<br/>&nbsp;&nbsp;&nbsp;<b><u>Description :</u></b> {observation}",
                ParagraphStyle("DescFrs", parent=styles["Normal"], fontSize=9, alignment=TA_LEFT, leading=11)))
            elements.append(Spacer(1, 1.5*mm))
            elements.append(Paragraph(
                f"<br/>&nbsp;&nbsp;&nbsp;<b><u>Coordonnées fournisseur :</u></b> {frs_adresse} ; Tel : {frs_contact}",
                ParagraphStyle("CoordFrs", parent=styles["Normal"], fontSize=9, alignment=TA_LEFT, leading=11)))
            elements.append(Spacer(1, 1.5*mm))

            sig_left  = Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;<u>Le Responsable</u>",
                ParagraphStyle("SigRespoFrs", parent=styles["Normal"], fontSize=9, alignment=TA_LEFT))
            sig_right = Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;<u>Le Fournisseur</u>",
                ParagraphStyle("SigFrs", parent=styles["Normal"], fontSize=9, alignment=TA_LEFT))
            sig_table = Table([[sig_left,"",sig_right]],
                colWidths=[usable_width*0.35, usable_width*0.30, usable_width*0.35])
            sig_table.setStyle(TableStyle([
                ("TOPPADDING",(0,0),(-1,-1),10), ("ALIGN",(0,0),(0,0),"LEFT"),
                ("ALIGN",(2,0),(2,0),"RIGHT")]))
            elements.append(sig_table)
            doc.build(elements)

            if open_after:
                open_file_if_enabled(
                    path,
                    operation="open",
                    setting_key=(open_setting_key or "Fournisseur_PmtDette_OpenA5"),
                    setting_default=open_setting_default,
                )
            return path

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur génération PDF paiement dette: {e}")
            return None

    def _generer_ticket_pdf_dette(self, societe, username, articles, montant,
                                   mode_nom, refpmt, frs_nom, montant_total, open_after=False):
        try:
            fd, path = tempfile.mkstemp(prefix='ticket_dette_frs_', suffix='.pdf')
            os.close(fd)
            total_height = (160 + (len(articles) * 10)) * mm
            c = canvas.Canvas(path, pagesize=(80*mm, total_height))
            y = total_height - 10*mm

            if societe:
                c.setFont("Helvetica-Bold", 11)
                c.drawCentredString(40*mm, y, str(societe[0]).upper()); y -= 5*mm
                c.setFont("Helvetica", 8)
                c.drawCentredString(40*mm, y, f"{societe[1] or ''}"); y -= 4*mm
                c.drawCentredString(40*mm, y, f"{societe[2] or ''}"); y -= 4*mm
                c.drawCentredString(40*mm, y, f"Tel: {societe[3] or ''}"); y -= 2*mm
            else:
                c.setFont("Helvetica-Bold", 10)
                c.drawCentredString(40*mm, y, "MA SOCIETE"); y -= 4*mm

            y -= 4*mm; c.line(5*mm, y, 75*mm, y); y -= 6*mm
            c.setFont("Helvetica-Bold", 9)
            c.drawCentredString(40*mm, y, "ENREGISTREMENT DETTE FRS"); y -= 6*mm
            c.setFont("Helvetica", 8)
            c.drawString(5*mm, y, f"Ref: {refpmt}"); y -= 4*mm
            c.drawString(5*mm, y, f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}"); y -= 4*mm
            c.drawString(5*mm, y, f"Fournisseur: {frs_nom}")

            y -= 10*mm; c.setFont("Helvetica-Bold", 7)
            c.drawString(5*mm, y, "Designation"); c.drawRightString(48*mm, y, "Qte")
            c.drawRightString(62*mm, y, "P.U"); c.drawRightString(77*mm, y, "Total")
            y -= 2*mm; c.line(5*mm, y, 75*mm, y); y -= 4*mm
            c.setFont("Helvetica", 6.5)
            for art in articles:
                designation = f"{art[1]} ({art[2]})" if art[2] else str(art[1])
                c.drawString(5*mm, y, designation[:25])
                c.drawRightString(48*mm, y, str(art[3]))
                c.drawRightString(62*mm, y, f"{art[4]:,.0f}".replace(',', ' '))
                c.drawRightString(77*mm, y, f"{art[5]:,.0f}".replace(',', ' ')); y -= 8*mm

            c.setFont("Helvetica-Bold", 10)
            c.drawString(5*mm, y, "MONTANT DETTE :")
            c.drawRightString(75*mm, y, f"{self._formater_nombre(montant)} Ar")
            y -= 8*mm
            if num2words:
                c.setFont("Helvetica-Oblique", 6)
                try:
                    lettres = num2words(int(montant), lang='fr').upper()
                    if len(lettres) > 45:
                        c.drawString(5*mm, y, f"Arrete a: {lettres[:45]}"); y -= 3*mm
                        c.drawString(5*mm, y, f"{lettres[45:]} ARIARY")
                    else:
                        c.drawString(5*mm, y, f"Arrete a: {lettres} ARIARY")
                except: pass

            y -= 10*mm; c.line(5*mm, y+2*mm, 75*mm, y+2*mm)
            c.setFont("Helvetica", 7); c.drawString(5*mm, y, f"Mode: {mode_nom}"); y -= 5*mm
            c.setFont("Helvetica-Bold", 8); c.drawString(5*mm, y, f"Enregistre par: {username}")
            c.showPage(); c.save()

            if open_after:
                open_file_if_enabled(
                    path,
                    operation="open",
                    setting_key="Fournisseur_Dette_OpenTicketPdf",
                    setting_default=0,
                )
            return path

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur génération PDF dette: {e}")
            return None

    # ──────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────

    def _formater_nombre(self, nombre):
        if isinstance(nombre, (int, float)):
            return f"{nombre:,.0f}".replace(".", ",").replace(",", ".")
        return str(nombre)

    def format_montant(self, entry_widget):
        """Formate le montant avec séparateurs de milliers (format français: 1.234.567)."""
        current = entry_widget.get()
        if not current:
            return

        cleaned = current.replace('.', '').replace(',', '').replace(' ', '')
        if not cleaned or not cleaned.isdigit():
            entry_widget.delete(0, 'end')
            entry_widget.insert(0, current)
            return

        formatted = ''
        for i, digit in enumerate(reversed(cleaned)):
            if i > 0 and i % 3 == 0:
                formatted = '.' + formatted
            formatted = digit + formatted

        entry_widget.delete(0, 'end')
        entry_widget.insert(0, formatted)
        entry_widget.icursor(len(formatted))

    def _get_societe_info(self):
        defaults = {'name': 'IJEERY', 'addr': '', 'ville': '', 'tel': '',
                    'nif': '', 'stat': '', 'cif': ''}
        if not self.conn: return defaults
        try:
            self.cursor.execute("""
                SELECT nomsociete, adressesociete, villesociete, contactsociete,
                       nifsociete, statsociete, cifsociete
                FROM tb_infosociete LIMIT 1
            """)
            societe = self.cursor.fetchone()
            if not societe: return defaults
            return {
                'name': societe[0] or defaults['name'], 'addr': societe[1] or defaults['addr'],
                'ville': societe[2] or defaults['ville'], 'tel': societe[3] or defaults['tel'],
                'nif': societe[4] or defaults['nif'], 'stat': societe[5] or defaults['stat'],
                'cif': societe[6] or defaults['cif']
            }
        except psycopg2.Error:
            try:
                if self.conn: self.conn.rollback()
            except: pass
            return defaults

    def _get_username_by_id(self, iduser=1):
        if iduser is None: iduser = self._get_connected_user_id()
        if not self.conn: return "Utilisateur"
        try:
            self.cursor.execute("SELECT username FROM tb_users WHERE iduser = %s", (iduser,))
            row = self.cursor.fetchone()
            return row[0] if row and row[0] else "Utilisateur"
        except Exception:
            try: self.conn.rollback()
            except: pass
            return "Utilisateur"

    def _get_connected_user_id(self):
        if self.id_user_connecte is not None: return self.id_user_connecte
        session_id = self.session_data.get("user_id") or self.session_data.get("iduser")
        if session_id is not None:
            self.id_user_connecte = session_id
            return self.id_user_connecte
        parent = self.master
        while parent is not None:
            parent_id = getattr(parent, "id_user_connecte", None)
            if parent_id is not None:
                self.id_user_connecte = parent_id
                return self.id_user_connecte
            parent = getattr(parent, "master", None)
        return 1

    def _get_frs_name(self, idfrs):
        if not self.conn: return "FOURNISSEUR"
        try:
            self.cursor.execute("SELECT nomfrs FROM tb_fournisseur WHERE idfrs = %s", (idfrs,))
            row = self.cursor.fetchone()
            return row[0] if row and row[0] else "FOURNISSEUR"
        except Exception:
            try: self.conn.rollback()
            except: pass
            return "FOURNISSEUR"

    def __del__(self):
        if hasattr(self, 'conn') and self.conn:
            if hasattr(self, 'cursor') and self.cursor: self.cursor.close()
            self.conn.close()


# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    app = ctk.CTk()
    app.title("Gestion Fournisseurs")
    app.geometry("1200x650")
    PageFournisseur(app).pack(fill="both", expand=True)
    app.mainloop()