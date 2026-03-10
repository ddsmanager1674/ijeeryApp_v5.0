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


from .page_clientCrédit import PageClientCrédit


try:
    from app_theme import Colors, Fonts, styled, Theme
    _T = True
except ImportError:
    _T = False

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

    # En-têtes de colonnes
    style.configure(
        "Treeview.Heading",
        background="#2C3E50",        # Midnight Blue
        foreground="#FFFFFF",
        font=(_FONT_FAMILY, _FONT_SIZE_SM, "bold"),
        relief="flat",
        padding=(8, 6),
    )
    style.map(
        "Treeview.Heading",
        background=[("active", "#34495E")],  # hover légèrement plus clair
        relief=[("active", "flat")],
    )

    # Lignes du tableau
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


class PageClient(ctk.CTkFrame):
    def __init__(self, master, db_conn=None, session_data=None, id_user_connecte=None):
        super().__init__(master)
        
        self.type_mapping = {}
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
        
        self.sort_column = "Crédit en cours"
        self.sort_ascending = False
        
        _apply_treeview_theme()   # ← appliqué une seule fois à l'init
        self.setup_ui()
        self.load_types()
        self.load_client()
        
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
                CREATE TABLE IF NOT EXISTS tb_client (
                    idClient SERIAL PRIMARY KEY,
	                nomCli VARCHAR (100),
	                contactCli VARCHAR (50),
	                adresseCli VARCHAR (150),
	                nifCli VARCHAR (20),
	                statCli VARCHAR (20),
	                cifCli VARCHAR (20),
	                credit DOUBLE PRECISION,
	                idtypeclient INT DEFAULT 1,
	                dateregistre TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	                blocked INT DEFAULT 0,
	                deleted INT DEFAULT 0
                )
            """)
            self.conn.commit()
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors de la création de la table : {err}")

    def load_types(self):
        try:
            self.cursor.execute("SELECT idtypeclient, designationtypeclient FROM tb_typeclient WHERE idtypeclient = 2")
            types = self.cursor.fetchall()
            
            self.type_mapping = {t[1]: t[0] for t in types}
            self.type_combo.configure(values=list(self.type_mapping.keys()))
            
            if self.type_mapping:
                self.type_combo.set(list(self.type_mapping.keys())[0])
            else:
                self.type_combo.set("")
                self.type_combo.configure(values=[])
                
        except psycopg2.Error as err:
            print(f"Erreur chargement types : {err}")

    def setup_ui(self):
        self.pack(expand=True, fill="both", padx=20, pady=20)
        
        input_frame = ctk.CTkFrame(self)
        input_frame.pack(fill="x", pady=10)
        
        # Première ligne
        row1 = ctk.CTkFrame(input_frame)
        row1.pack(fill="x", pady=5)
        
        ctk.CTkLabel(row1, text="Nom du Client:", font=_F(_FONT_SIZE_SM)).pack(side="left", padx=5)
        self.nomCli_entry = ctk.CTkEntry(row1, width=150, font=_F(_FONT_SIZE_MD))
        self.nomCli_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(row1, text="Contact:", font=_F(_FONT_SIZE_SM)).pack(side="left", padx=5)
        self.contactCli_entry = ctk.CTkEntry(row1, width=150, font=_F(_FONT_SIZE_MD))
        self.contactCli_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(row1, text="Adresse:", font=_F(_FONT_SIZE_SM)).pack(side="left", padx=5)
        self.adresseCli_entry = ctk.CTkEntry(row1, width=150, font=_F(_FONT_SIZE_MD))
        self.adresseCli_entry.pack(side="left", padx=5)
        
        # Deuxième ligne
        row2 = ctk.CTkFrame(input_frame)
        row2.pack(fill="x", pady=5)
        
        ctk.CTkLabel(row2, text="NIF:", font=_F(_FONT_SIZE_SM)).pack(side="left", padx=5)
        self.nifCli_entry = ctk.CTkEntry(row2, width=120, font=_F(_FONT_SIZE_MD))
        self.nifCli_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(row2, text="Plafond de Crédit:", font=_F(_FONT_SIZE_SM)).pack(side="left", padx=5)
        self.credit_entry = ctk.CTkEntry(row2, width=120, font=_F(_FONT_SIZE_MD))
        self.credit_entry.pack(side="left", padx=5)

        ctk.CTkLabel(row2, text="Type Client:", font=_F(_FONT_SIZE_SM)).pack(side="left", padx=5)
        self.type_combo = ctk.CTkComboBox(row2, width=150, values=[], font=_F(_FONT_SIZE_MD))
        self.type_combo.pack(side="left", padx=5)
        
        # Frame pour les boutons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", pady=10)
        
        self.add_button = ctk.CTkButton(button_frame, text="Ajouter", command=self.add_client,
                                        fg_color="#2ecc71", font=_F(_FONT_SIZE_MD, "bold"))
        self.add_button.pack(side="left", padx=5)
        
        self.modify_button = ctk.CTkButton(button_frame, text="Modifier", command=self.modify_client,
                                           fg_color="#3498db", font=_F(_FONT_SIZE_MD, "bold"))
        self.modify_button.pack(side="left", padx=5)
        
        self.delete_button = ctk.CTkButton(button_frame, text="Supprimer", command=self.delete_client,
                                           fg_color="#e74c3c", font=_F(_FONT_SIZE_MD, "bold"))
        self.delete_button.pack(side="left", padx=5)

        self.credit_page_button = ctk.CTkButton(button_frame, text="Crédit", 
                                       command=self.open_credit_window,
                                       fg_color="#f39c12", hover_color="#e67e22",
                                       font=_F(_FONT_SIZE_MD, "bold"))
        # self.credit_page_button.pack(side="left", padx=5)
        
        # --- Frame de Recherche ---
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", pady=10, padx=0)
        
        ctk.CTkLabel(search_frame, text="Rechercher Client :",
                     font=_F(_FONT_SIZE_MD, "bold")).pack(side="left", padx=5)
        self.search_entry = ctk.CTkEntry(search_frame, width=300,
                                         placeholder_text="Nom, contact, adresse, NIF ou crédit...",
                                         font=_F(_FONT_SIZE_MD))
        self.search_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        self.all_clients_data = []
        self.search_entry.bind("<KeyRelease>", self.filter_clients)
        
        # Treeview — tags couleur lignes alternées
        columns = ("Nom du Client", "Contact", "Adresse", "NIF", "Crédit en cours", "Dernier Crédit", "Type")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        self.tree.tag_configure("even", background="#FFFFFF", foreground="#2C3E50")
        self.tree.tag_configure("odd",  background="#EBF5FB", foreground="#2C3E50")
        
        col_widths = {"Nom du Client": 120, "Contact": 110, "Adresse": 140,
                      "NIF": 90, "Crédit en cours": 130, "Dernier Crédit": 190, "Type": 110}
        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_by_column(c))
            self.tree.column(col, width=col_widths.get(col, 110))
        self.tree.column("Crédit en cours", anchor="e")
        
        self.tree.pack(fill="both", expand=True, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", self.on_client_double_click)
        
        self.selected_cli_id = None

    def load_client(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        if not self.conn: return

        try:
            self.cursor.execute("""
                SELECT c.idclient, c.nomcli, c.contactcli, c.adressecli, c.nifcli, c.credit, t.designationtypeclient
                FROM tb_client c
                LEFT JOIN tb_typeclient t ON c.idtypeclient = t.idtypeclient
                WHERE c.idtypeclient != 1
            """)
            clients = self.cursor.fetchall()
            
            clients_avec_credits = []
            for cli in clients:
                try:
                    _, _, _, credit_restant, _ = self._compute_credit_status_fifo(cli[0])
                except Exception:
                    credit_restant = 0
                dernier_credit = self._get_dernier_credit_label(cli[0])
                clients_avec_credits.append((cli, credit_restant, dernier_credit))
            
            clients_avec_credits.sort(key=lambda x: x[1], reverse=True)
            self.all_clients_data = clients_avec_credits
            self.display_clients(clients_avec_credits)
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors du chargement : {err}")

    def display_clients(self, clients_avec_credits):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for idx, (cli, credit_restant, dernier_credit) in enumerate(clients_avec_credits):
            tag = "even" if idx % 2 == 0 else "odd"
            credit_str = self._formater_nombre(credit_restant)
            self.tree.insert("", "end", iid=cli[0], values=(
                cli[1], cli[2], cli[3], cli[4], credit_str, dernier_credit, cli[6]
            ), tags=(tag,))

    def sort_by_column(self, column):
        if self.sort_column == column:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = column
            self.sort_ascending = True
        
        if not self.all_clients_data:
            return
        
        col_index = {
            "Nom du Client": 1, "Contact": 2, "Adresse": 3, "NIF": 4,
            "Crédit en cours": "credit", "Dernier Crédit": "dernier_credit"
        }
        
        if column == "Crédit en cours":
            sorted_data = sorted(self.all_clients_data, key=lambda x: x[1], reverse=not self.sort_ascending)
        elif column == "Dernier Crédit":
            sorted_data = sorted(
                self.all_clients_data,
                key=lambda x: self._extract_days_from_label(x[2]),
                reverse=not self.sort_ascending
            )
        else:
            idx = col_index.get(column, 1)
            sorted_data = sorted(self.all_clients_data, 
                               key=lambda x: str(x[0][idx] or "").lower(),
                               reverse=not self.sort_ascending)
        
        self.display_clients(sorted_data)

    def add_client(self):
        if not self.conn: return
        try:
            nomcli = self.nomCli_entry.get()
            id_type = self.type_mapping.get(self.type_combo.get())
            
            if not nomcli or not id_type:
                messagebox.showwarning("Attention", "Le nom et le type sont obligatoires.")
                return

            self.cursor.execute("""
                INSERT INTO tb_client (nomcli, contactcli, adressecli, nifcli, credit, idtypeclient)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (nomcli, self.contactCli_entry.get(), self.adresseCli_entry.get(), 
                  self.nifCli_entry.get(), self.credit_entry.get() or 0, id_type))
            
            self.conn.commit()
            self.load_client()
            self.clear_fields()
            messagebox.showinfo("Succès", "Client ajouté !")
        except psycopg2.Error as err:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur : {err}")

    def modify_client(self):
        if not self.selected_cli_id: return
        try:
            id_type = self.type_mapping.get(self.type_combo.get())
            self.cursor.execute("""
                UPDATE tb_client 
                SET nomcli=%s, contactcli=%s, adressecli=%s, nifcli=%s, credit=%s, idtypeclient=%s
                WHERE idclient=%s
            """, (self.nomCli_entry.get(), self.contactCli_entry.get(), self.adresseCli_entry.get(),
                  self.nifCli_entry.get(), self.credit_entry.get(), id_type, self.selected_cli_id))
            self.conn.commit()
            self.load_client()
            messagebox.showinfo("Succès", "Client modifié !")
        except psycopg2.Error as err:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur : {err}")

    def delete_client(self):
        if not self.selected_cli_id: return
        if messagebox.askyesno("Confirmation", "Supprimer ce client ?"):
            try:
                self.cursor.execute("DELETE FROM tb_client WHERE idclient = %s", (self.selected_cli_id,))
                self.conn.commit()
                self.load_client()
                self.clear_fields()
            except psycopg2.Error as err:
                messagebox.showerror("Erreur", f"Erreur : {err}")

    def on_select(self, event):
        selected = self.tree.selection()
        if not selected: return
        
        self.selected_cli_id = selected[0]
        try:
            self.cursor.execute("""
                SELECT c.nomcli, c.contactcli, c.adressecli, c.nifcli, c.credit, t.designationtypeclient
                FROM tb_client c
                LEFT JOIN tb_typeclient t ON c.idtypeclient = t.idtypeclient
                WHERE c.idclient = %s
            """, (self.selected_cli_id,))
            res = self.cursor.fetchone()
            if res:
                self.nomCli_entry.delete(0, "end")
                self.nomCli_entry.insert(0, res[0])
                self.contactCli_entry.delete(0, "end")
                self.contactCli_entry.insert(0, res[1])
                self.adresseCli_entry.delete(0, "end")
                self.adresseCli_entry.insert(0, res[2])
                self.nifCli_entry.delete(0, "end")
                self.nifCli_entry.insert(0, res[3])
                self.credit_entry.delete(0, "end")
                self.credit_entry.insert(0, res[4])
                self.type_combo.set(res[5])
        except psycopg2.Error as err:
            print(err)

    def clear_fields(self):
        for entry in [self.nomCli_entry, self.contactCli_entry, self.adresseCli_entry,
                      self.nifCli_entry, self.credit_entry]:
            entry.delete(0, "end")
        self.selected_cli_id = None

    def filter_clients(self, event=None):
        search_query = self.search_entry.get().lower().strip()

        filtered_data = []
        for cli, credit_restant, dernier_credit in self.all_clients_data:
            searchable_parts = [
                str(cli[0] or ""), str(cli[1] or ""), str(cli[2] or ""),
                str(cli[3] or ""), str(cli[4] or ""), str(cli[6] or ""),
                str(credit_restant or 0),
                self._formater_nombre(credit_restant),
                str(dernier_credit or ""),
            ]
            searchable_text = " ".join(searchable_parts).lower()

            if not search_query or search_query in searchable_text:
                filtered_data.append((cli, credit_restant, dernier_credit))

        self.display_clients(filtered_data)

    def open_credit_window(self):
        credit_window = ctk.CTkToplevel(self)
        credit_window.title("Détails des Crédits Clients")
        credit_window.geometry("900x600")
        credit_window.attributes("-topmost", True)
        credit_window.grid_columnconfigure(0, weight=1)
        credit_window.grid_rowconfigure(0, weight=1)
        credit_page = PageClientCrédit(credit_window)
        credit_page.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def on_client_double_click(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        idclient = selected[0]
        self.open_client_credit_details(idclient)

    def open_client_credit_details(self, idclient):
        try:
            self.cursor.execute(
                """SELECT c.idclient, c.nomcli, c.contactcli, c.adressecli, c.nifcli, c.credit, t.designationtypeclient
                FROM tb_client c
                LEFT JOIN tb_typeclient t ON c.idtypeclient = t.idtypeclient
                WHERE c.idclient = %s""", (idclient,))
            client_info = self.cursor.fetchone()
        except psycopg2.Error as err:
            try:
                if self.conn:
                    self.conn.rollback()
            except Exception:
                pass
            messagebox.showerror("Erreur", f"Impossible de récupérer les infos du client: {err}")
            return
        
        if not client_info:
            messagebox.showwarning("Attention", "Client non trouvé.")
            return
        
        detail_window = ctk.CTkToplevel(self)
        detail_window.title(f"Détails de Crédit - {client_info[1]}")

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
        sidebar_frame = ctk.CTkFrame(detail_window, fg_color="#f0f0f0")
        sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        sidebar_frame.grid_rowconfigure(2, weight=1)
        
        ctk.CTkLabel(sidebar_frame, text="Informations Client", 
                    font=_F(_FONT_SIZE_LG, "bold"),
                    text_color="#2c3e50").pack(anchor="w", padx=10, pady=(10, 5))
        
        info_data = [
            ("Nom:", client_info[1]),
            ("Contact:", client_info[2] or "N/A"),
            ("Adresse:", client_info[3] or "N/A"),
            ("NIF:", client_info[4] or "N/A"),
            ("Plafond Crédit:", f"{client_info[5] or 0} Ar"),
            ("Type:", client_info[6] or "N/A")
        ]
        
        for label, value in info_data:
            info_row = ctk.CTkFrame(sidebar_frame, fg_color="transparent")
            info_row.pack(anchor="w", padx=10, pady=2, fill="x")
            ctk.CTkLabel(info_row, text=label, font=_F(_FONT_SIZE_SM, "bold"),
                        text_color="#34495e", width=80).pack(side="left", anchor="nw")
            ctk.CTkLabel(info_row, text=value, font=_F(_FONT_SIZE_SM),
                        text_color="#2c3e50").pack(side="left", anchor="nw", padx=(5, 0), fill="x", expand=True)
        
        ctk.CTkLabel(sidebar_frame, text="", fg_color="#bdc3c7", height=1).pack(fill="x", pady=10, padx=10)
        
        ctk.CTkLabel(sidebar_frame, text="Situation Crédit", 
                    font=_F(_FONT_SIZE_LG, "bold"),
                    text_color="#2c3e50").pack(anchor="w", padx=10, pady=(5, 10))
        
        credit_info_frame = ctk.CTkFrame(sidebar_frame, fg_color="transparent")
        credit_info_frame.pack(anchor="w", padx=10, pady=2, fill="x")
        
        ctk.CTkLabel(credit_info_frame, text="Total Restant:", font=_F(_FONT_SIZE_SM, "bold"),
                    text_color="#34495e").pack(side="left", anchor="nw")
        label_montant_restant = ctk.CTkLabel(credit_info_frame, text="0,00 Ar", 
                                            font=_F(_FONT_SIZE_LG, "bold"),
                                            text_color="#e74c3c")
        label_montant_restant.pack(side="left", anchor="nw", padx=(5, 0))
        
        btn_paiement_global = ctk.CTkButton(sidebar_frame, text="💳 Effectuer Paiement", 
                                          fg_color="#3498db", hover_color="#2980b9", 
                                          height=40, font=_F(_FONT_SIZE_MD, "bold"),
                                          command=lambda: None)
        btn_paiement_global.pack(padx=10, pady=10, fill="x")
        
        btn_ajouter_creance = ctk.CTkButton(sidebar_frame, text="➕ Ajouter Créance", 
                                          fg_color="#27ae60", hover_color="#229954", 
                                          height=40, font=_F(_FONT_SIZE_MD, "bold"),
                                          command=lambda: self._open_add_creance_window(idclient, detail_window))
        btn_ajouter_creance.pack(padx=10, pady=10, fill="x")
        
        # ── ZONE DROITE ───────────────────────────────────────────────────────
        right_frame = ctk.CTkFrame(detail_window)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(0, weight=1)
        right_frame.grid_rowconfigure(1, weight=1)
        
        # ── Tableau crédits ───────────────────────────────────────────────────
        table_frame = ctk.CTkFrame(right_frame)
        table_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=(0, 5))
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_columnconfigure(1, weight=0)
        table_frame.grid_rowconfigure(0, weight=0)
        table_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(table_frame, text="Récapitulatif des Crédits", 
                    font=_F(_FONT_SIZE_LG, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))
        
        colonnes_credits = ("ID", "Type", "Date", "RefVente", "Montant", "Montant Payé", "Solde Restant", "Statut")
        tree_credits = ttk.Treeview(table_frame, columns=colonnes_credits, show='headings', height=10)
        tree_credits.tag_configure("complet", background="#D5F5E3", foreground="#1E8449")
        tree_credits.tag_configure("partiel", background="#FEF9E7", foreground="#9A6A00")
        tree_credits.tag_configure("impaye",  background="#FADBD8", foreground="#922B21")
        
        for col in colonnes_credits:
            tree_credits.heading(col, text=col)
            if col == "ID":
                tree_credits.column(col, width=0, stretch=False)
            elif col in ("Montant", "Montant Payé", "Solde Restant"):
                tree_credits.column(col, width=100, anchor='e')
            else:
                tree_credits.column(col, width=110, anchor='w')
        
        scrollbar = ttk.Scrollbar(table_frame, command=tree_credits.yview)
        tree_credits.configure(yscrollcommand=scrollbar.set)
        tree_credits.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=5)
        scrollbar.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=5)
        
        try:
            self._render_credit_table(tree_credits, idclient, label_montant_restant)

            def on_paiement_global_click():
                self._open_global_payment_window(idclient, detail_window, tree_credits, label_montant_restant)

            btn_paiement_global.configure(command=on_paiement_global_click)
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur chargement crédits: {err}")
        
        def on_credit_double_click(event):
            selected = tree_credits.selection()
            if not selected:
                return
            item_iid = selected[0]
            values = tree_credits.item(item_iid, "values")
            if not values:
                return
            credit_id = values[0]
            type_credit = values[1]
            if type_credit == "Crédit Vente":
                self._open_vente_detail_window(credit_id, detail_window)
            else:
                self._open_creance_detail_window(credit_id, detail_window)

        tree_credits.bind("<Double-1>", on_credit_double_click)

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
        
        colonnes_paiements = ("ID", "Date Paiement", "Montant Payé", "Observation", "Utilisateur")
        tree_paiements = ttk.Treeview(payment_frame, columns=colonnes_paiements, show='headings', height=8)
        tree_paiements.tag_configure("even", background="#FFFFFF", foreground="#2C3E50")
        tree_paiements.tag_configure("odd",  background="#EBF5FB", foreground="#2C3E50")
        
        for col in colonnes_paiements:
            tree_paiements.heading(col, text=col)
            if col == "ID":
                tree_paiements.column(col, width=0, stretch=False)
            elif col == "Montant Payé":
                tree_paiements.column(col, width=120, anchor='e')
            elif col == "Date Paiement":
                tree_paiements.column(col, width=130, anchor='center')
            else:
                tree_paiements.column(col, width=150, anchor='w')
        
        scrollbar_pmt = ttk.Scrollbar(payment_frame, command=tree_paiements.yview)
        tree_paiements.configure(yscrollcommand=scrollbar_pmt.set)
        tree_paiements.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=5)
        scrollbar_pmt.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=5)
        
        try:
            self.cursor.execute("""
                SELECT p.id, p.datepmt, p.mtpaye, p.observation, 
                       COALESCE(CONCAT(u.prenomuser, ' ', u.nomuser), 'N/A') as utilisateur
                FROM tb_pmtcredit p
                LEFT JOIN tb_users u ON p.iduser = u.iduser
                WHERE p.idclient = %s
                ORDER BY p.datepmt DESC
            """, (idclient,))
            paiements = self.cursor.fetchall()
            
            for idx, pmt in enumerate(paiements):
                pmt_id, date_pmt, montant_pmt, observation, utilisateur = pmt
                tag = "even" if idx % 2 == 0 else "odd"
                tree_paiements.insert('', 'end', iid=f"pmt_{pmt_id}", values=(
                    pmt_id,
                    date_pmt.strftime("%d/%m/%Y %H:%M") if date_pmt else "N/A",
                    f"{montant_pmt or 0:,.2f}",
                    observation or "",
                    utilisateur or "N/A"
                ), tags=(tag,))
            
            if not paiements:
                empty_label = ctk.CTkLabel(payment_frame, text="Aucun paiement enregistré", 
                                          text_color="gray", font=_F(_FONT_SIZE_MD))
                empty_label.grid(row=1, column=0, pady=20)
        
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur chargement paiements: {err}")

    def _open_vente_detail_window(self, pmtfacture_id, parent_window):
        try:
            self.cursor.execute("""
                SELECT refvente FROM tb_pmtfacture WHERE id = %s
            """, (pmtfacture_id,))
            row = self.cursor.fetchone()
            if not row or not row[0]:
                messagebox.showinfo("Information", "Aucune référence de vente associée à ce crédit.")
                return
            refvente = row[0]

            self.cursor.execute("""
                SELECT v.refvente, v.dateregistre, v.totmtvente,
                       COALESCE(u.username, 'N/A') as operateur,
                       COALESCE(m.designationmag, 'N/A') as magasin
                FROM tb_vente v
                LEFT JOIN tb_users u ON v.iduser = u.iduser
                LEFT JOIN tb_magasin m ON v.idmag = m.idmag
                WHERE v.refvente = %s AND v.deleted = 0
            """, (refvente,))
            vente = self.cursor.fetchone()
            if not vente:
                messagebox.showinfo("Information", f"Vente introuvable pour la référence : {refvente}")
                return

            ref, date_vente, total, operateur, magasin = vente

            self.cursor.execute("""
                SELECT 
                    u.codearticle,
                    a.designation,
                    COALESCE(u.designationunite, '-') as unite,
                    vd.prixunit,
                    COALESCE(vd.remise, 0) as remise,
                    vd.qtvente,
                    (vd.prixunit * vd.qtvente * (1 - COALESCE(vd.remise, 0) / 100)) as montant
                FROM tb_ventedetail vd
                LEFT JOIN tb_article a ON vd.idarticle = a.idarticle
                LEFT JOIN tb_unite u ON vd.idunite = u.idunite
                WHERE vd.idvente = (SELECT id FROM tb_vente WHERE refvente = %s AND deleted = 0 LIMIT 1)
                  AND vd.deleted = 0
            """, (refvente,))
            details = self.cursor.fetchall()

        except psycopg2.Error as err:
            try:
                self.conn.rollback()
            except Exception:
                pass
            messagebox.showerror("Erreur", f"Erreur chargement détails vente : {err}")
            return

        win = ctk.CTkToplevel(parent_window)
        win.title(f"Détails Vente — {refvente}")
        parent_window.update_idletasks()
        pw = max(parent_window.winfo_width(), 1)
        ph = max(parent_window.winfo_height(), 1)
        px = parent_window.winfo_x()
        py = parent_window.winfo_y()
        ww, wh = max(700, int(pw * 0.6)), max(500, int(ph * 0.75))
        win.geometry(f"{ww}x{wh}+{px + (pw - ww)//2}+{py + (ph - wh)//2}")
        win.minsize(700, 500)
        win.grab_set()
        win.grid_columnconfigure(0, weight=1)
        win.grid_rowconfigure(1, weight=1)

        info_frame = ctk.CTkFrame(win, fg_color="#f0f4f8")
        info_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))

        ctk.CTkLabel(info_frame, text="Informations de la Vente",
                     font=_F(_FONT_SIZE_LG, "bold"), text_color="#2c3e50"
                     ).grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(8, 4))

        infos = [
            ("Référence :", ref),
            ("Date Vente :", date_vente.strftime("%d/%m/%Y %H:%M") if date_vente else "N/A"),
            ("Magasin :", magasin),
            ("Opérateur :", operateur),
            ("Montant Total :", f"{total or 0:,.2f} Ar"),
        ]
        for col_idx, (label, value) in enumerate(infos):
            ctk.CTkLabel(info_frame, text=label,
                         font=_F(_FONT_SIZE_SM, "bold"), text_color="#34495e"
                         ).grid(row=1, column=col_idx * 2, sticky="w", padx=(10, 2), pady=(0, 8))
            ctk.CTkLabel(info_frame, text=value,
                         font=_F(_FONT_SIZE_SM), text_color="#2c3e50"
                         ).grid(row=1, column=col_idx * 2 + 1, sticky="w", padx=(0, 16), pady=(0, 8))

        detail_frame = ctk.CTkFrame(win)
        detail_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(4, 4))
        detail_frame.grid_columnconfigure(0, weight=1)
        detail_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(detail_frame, text="Détail des Articles",
                     font=_F(_FONT_SIZE_LG, "bold")
                     ).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 4))

        cols = ("Code Article", "Désignation", "Unité", "Qté", "P.U", "Remise (%)", "Montant")
        tree_detail = ttk.Treeview(detail_frame, columns=cols, show="headings", height=12)
        tree_detail.tag_configure("even", background="#FFFFFF", foreground="#2C3E50")
        tree_detail.tag_configure("odd",  background="#EBF5FB", foreground="#2C3E50")

        col_widths = {"Code Article": 90, "Désignation": 180, "Unité": 60,
                      "Qté": 55, "P.U": 90, "Remise (%)": 80, "Montant": 100}
        col_anchor = {"P.U": "e", "Qté": "e", "Remise (%)": "e", "Montant": "e"}
        for col in cols:
            tree_detail.heading(col, text=col)
            tree_detail.column(col, width=col_widths.get(col, 90),
                               anchor=col_anchor.get(col, "w"))

        sb = ttk.Scrollbar(detail_frame, command=tree_detail.yview)
        tree_detail.configure(yscrollcommand=sb.set)
        tree_detail.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=5)
        sb.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=5)

        for idx, d in enumerate(details):
            code, designation, unite, pu, remise, qte, montant_ligne = d
            tag = "even" if idx % 2 == 0 else "odd"
            tree_detail.insert("", "end", tags=(tag,), values=(
                code or "-", designation or "-", unite or "-",
                f"{qte or 0:,.2f}", f"{pu or 0:,.2f}",
                f"{remise or 0:,.1f}", f"{montant_ligne or 0:,.2f}",
            ))

        total_frame = ctk.CTkFrame(win, fg_color="#eaf0fb")
        total_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(2, 12))
        ctk.CTkLabel(total_frame, text=f"Montant Total :  {total or 0:,.2f} Ar",
                     font=_F(_FONT_SIZE_LG, "bold"), text_color="#1a5276"
                     ).pack(side="right", padx=20, pady=8)

        ctk.CTkButton(win, text="Fermer", command=win.destroy,
                      fg_color="#7f8c8d", width=100,
                      font=_F(_FONT_SIZE_MD)).grid(row=3, column=0, pady=(0, 10))

    def _open_creance_detail_window(self, creance_id, parent_window):
        try:
            self.cursor.execute("""
                SELECT ac.id, ac.numfact, ac.dateregistre, ac.montant,
                       c.nomcli, c.contactcli
                FROM tb_autrecreance ac
                LEFT JOIN tb_client c ON ac.idclient = c.idclient
                WHERE ac.id = %s
            """, (creance_id,))
            row = self.cursor.fetchone()
            if not row:
                messagebox.showinfo("Information", "Créance introuvable.")
                return
            ac_id, numfact, date_reg, montant, nomcli, contactcli = row
        except psycopg2.Error as err:
            try:
                self.conn.rollback()
            except Exception:
                pass
            messagebox.showerror("Erreur", f"Erreur chargement créance : {err}")
            return

        win = ctk.CTkToplevel(parent_window)
        win.title(f"Détails Créance — {numfact or ac_id}")
        parent_window.update_idletasks()
        pw = max(parent_window.winfo_width(), 1)
        ph = max(parent_window.winfo_height(), 1)
        px = parent_window.winfo_x()
        py = parent_window.winfo_y()
        ww, wh = 440, 280
        win.geometry(f"{ww}x{wh}+{px + (pw - ww)//2}+{py + (ph - wh)//2}")
        win.resizable(False, False)
        win.grab_set()

        frame = ctk.CTkFrame(win, fg_color="#f0f4f8")
        frame.pack(fill="both", expand=True, padx=14, pady=14)

        ctk.CTkLabel(frame, text="Informations de la Créance",
                     font=_F(_FONT_SIZE_LG, "bold"), text_color="#2c3e50"
                     ).pack(anchor="w", padx=10, pady=(10, 8))

        infos = [
            ("Référence :", numfact or "N/A"),
            ("Date Enregistrement :", date_reg.strftime("%d/%m/%Y %H:%M") if date_reg else "N/A"),
            ("Client :", nomcli or "N/A"),
            ("Contact :", contactcli or "N/A"),
            ("Montant :", f"{montant or 0:,.2f} Ar"),
        ]
        for label, value in infos:
            row_f = ctk.CTkFrame(frame, fg_color="transparent")
            row_f.pack(anchor="w", padx=10, pady=3, fill="x")
            ctk.CTkLabel(row_f, text=label,
                         font=_F(_FONT_SIZE_MD, "bold"), text_color="#34495e",
                         width=180).pack(side="left")
            ctk.CTkLabel(row_f, text=value,
                         font=_F(_FONT_SIZE_MD), text_color="#2c3e50").pack(side="left")

        ctk.CTkButton(win, text="Fermer", command=win.destroy,
                      fg_color="#7f8c8d", width=100,
                      font=_F(_FONT_SIZE_MD)).pack(pady=(8, 10))

    def _open_payment_window(self, credit_id, idclient, type_credit, montant_total, montant_paye, solde_restant, tree_credits, parent_window):
        payment_window = ctk.CTkToplevel(parent_window)
        payment_window.title("Enregistrer un Paiement")
        payment_window.geometry("450x350")
        payment_window.grab_set()
        
        info_text = f"""Crédit ID: {credit_id}
Type: {type_credit}

Montant Total: {montant_total:,.2f} Ar
Montant Déjà Payé: {montant_paye:,.2f} Ar
Solde Restant: {solde_restant:,.2f} Ar"""
        
        ctk.CTkLabel(payment_window, text=info_text, justify="left", 
                    font=_F(_FONT_SIZE_MD)).pack(padx=10, pady=10)
        
        ctk.CTkLabel(payment_window, text=f"Montant à Payer (max: {solde_restant:,.2f} Ar):",
                    font=_F(_FONT_SIZE_MD, "bold")).pack(padx=10, pady=5)
        entry_montant = ctk.CTkEntry(payment_window, width=350, font=_F(_FONT_SIZE_MD))
        entry_montant.pack(padx=10, pady=5)
        
        ctk.CTkLabel(payment_window, text="Observation (optionnel):",
                    font=_F(_FONT_SIZE_MD, "bold")).pack(padx=10, pady=(10, 5))
        entry_obs = ctk.CTkEntry(payment_window, width=350, font=_F(_FONT_SIZE_MD))
        entry_obs.pack(padx=10, pady=5)

        try:
            self.cursor.execute("SELECT idmode, modedepaiement FROM tb_modepaiement ORDER BY modedepaiement")
            modes = self.cursor.fetchall()
        except Exception:
            modes = []

        mode_names = [m[1] for m in modes] if modes else []
        mode_map = {m[1]: m[0] for m in modes} if modes else {}

        ctk.CTkLabel(payment_window, text="Mode de Paiement:",
                     font=_F(_FONT_SIZE_MD, "bold")).pack(padx=10, pady=(10, 5))
        mode_combo = ctk.CTkComboBox(payment_window, values=mode_names, width=350,
                                     font=_F(_FONT_SIZE_MD))
        if mode_names:
            mode_combo.set(mode_names[0])
        mode_combo.pack(padx=10, pady=5)
        
        def enregistrer_paiement():
            try:
                montant_paiement = float(entry_montant.get().replace(',', '.'))
                observation = entry_obs.get().strip()
                
                if montant_paiement <= 0:
                    messagebox.showwarning("Attention", "Le montant doit être supérieur à 0.")
                    return
                
                if montant_paiement > solde_restant:
                    messagebox.showwarning("Attention", f"Le montant dépasse le solde restant ({solde_restant:,.2f} Ar).")
                    return
                
                selected_mode = mode_combo.get() if mode_names else None
                idmode_sel = mode_map.get(selected_mode) if selected_mode else None

                date_pmt = datetime.now()
                self.cursor.execute("""
                    INSERT INTO tb_pmtcredit 
                    (datepmt, mtpaye, observation, idtypeoperation, idclient, idmode, idpaiment, iduser)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (date_pmt, montant_paiement, observation, 1, idclient, idmode_sel, None, 1))
                self.conn.commit()
                
                messagebox.showinfo("Succès", f"Paiement de {montant_paiement:,.2f} Ar enregistré avec succès!")
                
                ticket_filename = os.path.join(os.path.dirname(__file__), '../temp_pdf_preview', f'ticket_payment_{idclient}_{date_pmt.strftime("%Y%m%d%H%M%S")}.txt')
                os.makedirs(os.path.dirname(ticket_filename), exist_ok=True)
                self._generate_ticket_80mm_payment(idclient, montant_paiement, idmode_sel, date_pmt, ticket_filename)
                
                result = messagebox.askyesno("Imprimer", "Voulez-vous imprimer le reçu paiement sur X80?")
                if result:
                    self._print_ticket_80mm(ticket_filename)
                
                for item in tree_credits.get_children():
                    tree_credits.delete(item)
                
                try:
                    self.cursor.execute("""
                        SELECT id, 'Crédit Vente' as type, refvente, datepmt, mtpaye, dateecheance
                        FROM tb_pmtfacture
                        WHERE idclient = %s AND idmode = 4 AND deleted = 0
                        ORDER BY datepmt DESC
                    """, (idclient,))
                    credits_vente = self.cursor.fetchall()
                    
                    self.cursor.execute("""
                        SELECT id, 'Créance' as type, numfact, dateregistre, montant, dateecheance
                        FROM tb_autrecreance
                        WHERE idclient = %s
                        ORDER BY dateregistre DESC
                    """, (idclient,))
                    autrecreances = self.cursor.fetchall()
                    
                    tous_credits = credits_vente + autrecreances
                    tous_credits.sort(key=lambda x: x[3], reverse=True)
                    
                    for idx, credit in enumerate(tous_credits):
                        credit_id_temp, type_credit_temp, ref, date_credit, montant_initial, date_echeance = credit
                        
                        self.cursor.execute("""
                            SELECT COALESCE(SUM(mtpaye), 0)
                            FROM tb_pmtcredit
                            WHERE idclient = %s AND (refvente = %s OR id = %s)
                        """, (idclient, ref, credit_id_temp))
                        result_paiement = self.cursor.fetchone()
                        montant_paye_temp = result_paiement[0] if result_paiement else 0
                        
                        solde_restant_temp = montant_initial - montant_paye_temp
                        
                        if solde_restant_temp <= 0:
                            statut = "✓ Payé Complètement"
                            tag = "complet"
                        elif montant_paye_temp > 0:
                            statut = "⚠️ Partiellement Payé"
                            tag = "partiel"
                        else:
                            statut = "✗ Impayé"
                            tag = "impaye"
                        
                        tree_credits.insert('', 'end', iid=f"{type_credit_temp}_{credit_id_temp}", values=(
                            credit_id_temp, type_credit_temp,
                            date_credit.strftime("%d/%m/%Y %H:%M") if date_credit else "N/A",
                            ref,
                            f"{montant_initial or 0:,.2f}",
                            f"{montant_paye_temp:,.2f}",
                            f"{solde_restant_temp:,.2f}",
                            statut
                        ), tags=(tag,))
                
                except psycopg2.Error as err:
                    messagebox.showerror("Erreur", f"Erreur rafraîchissement: {err}")
                
                payment_window.destroy()
            
            except ValueError:
                messagebox.showerror("Erreur", "Veuillez entrer un montant valide.")
            except psycopg2.Error as err:
                self.conn.rollback()
                messagebox.showerror("Erreur", f"Erreur enregistrement paiement: {err}")
        
        btn_frame = ctk.CTkFrame(payment_window)
        btn_frame.pack(padx=10, pady=10)
        
        ctk.CTkButton(btn_frame, text="Enregistrer", command=enregistrer_paiement,
                     fg_color="#2ecc71", font=_F(_FONT_SIZE_MD, "bold")).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Annuler", command=payment_window.destroy,
                     fg_color="#e74c3c", font=_F(_FONT_SIZE_MD, "bold")).pack(side="left", padx=5)

    def _open_global_payment_window(self, idclient, parent_window, tree_credits, label_montant_restant):
        payment_window = ctk.CTkToplevel(parent_window)
        payment_window.title("Paiement Global des Crédits")
        parent_window.update_idletasks()
        parent_w = max(parent_window.winfo_width(), 1)
        parent_h = max(parent_window.winfo_height(), 1)
        parent_x = parent_window.winfo_x()
        parent_y = parent_window.winfo_y()

        win_w = max(620, int(parent_w * 0.5))
        win_h = max(460, int(parent_h * 0.6))
        pos_x = parent_x + (parent_w - win_w) // 2
        pos_y = parent_y + (parent_h - win_h) // 2
        payment_window.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
        payment_window.minsize(620, 460)
        payment_window.grab_set()
        payment_window.grid_columnconfigure(0, weight=1)
        payment_window.grid_rowconfigure(0, weight=1)

        main_frame = ctk.CTkFrame(payment_window)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=0)
        main_frame.grid_rowconfigure(1, weight=0)
        main_frame.grid_rowconfigure(2, weight=0)
        main_frame.grid_rowconfigure(3, weight=0)
        main_frame.grid_rowconfigure(4, weight=0)
        main_frame.grid_rowconfigure(5, weight=1)
        main_frame.grid_rowconfigure(6, weight=0)

        _, credit_total_initial, credit_total_paye, credit_total_restant, _ = self._compute_credit_status_fifo(idclient)
        
        info_text = f"""Récapitulatif du Crédit Client (ID: {idclient})

Montant Total des Crédits: {credit_total_initial:,.2f} Ar
Montant Total Déjà Payé: {credit_total_paye:,.2f} Ar
Solde Total Restant: {credit_total_restant:,.2f} Ar"""
        
        ctk.CTkLabel(
            main_frame, text=info_text, justify="left", anchor="w",
            font=_F(_FONT_SIZE_MD, "bold")
        ).grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 10))
        
        ctk.CTkLabel(
            main_frame,
            text=f"Montant Global à Payer (max: {credit_total_restant:,.2f} Ar):",
            font=_F(_FONT_SIZE_MD, "bold")
        ).grid(row=1, column=0, sticky="w", padx=8, pady=(0, 4))
        entry_montant = ctk.CTkEntry(main_frame, font=_F(_FONT_SIZE_MD))
        entry_montant.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        
        ctk.CTkLabel(
            main_frame, text="Observation (optionnel):",
            font=_F(_FONT_SIZE_MD, "bold")
        ).grid(row=3, column=0, sticky="w", padx=8, pady=(2, 4))
        entry_obs = ctk.CTkEntry(main_frame, font=_F(_FONT_SIZE_MD))
        entry_obs.grid(row=4, column=0, sticky="ew", padx=8, pady=(0, 8))
        
        ctk.CTkLabel(
            main_frame,
            text="Le paiement sera distribué automatiquement par ancienneté (factures les plus anciennes d'abord).",
            text_color="#95a5a6", justify="left", anchor="w", wraplength=560,
            font=_F(_FONT_SIZE_SM, "normal")
        ).grid(row=5, column=0, sticky="ew", padx=8, pady=(0, 8))

        try:
            self.cursor.execute("SELECT idmode, modedepaiement FROM tb_modepaiement ORDER BY modedepaiement")
            modes = self.cursor.fetchall()
        except Exception:
            modes = []

        mode_names = [m[1] for m in modes] if modes else []
        mode_map = {m[1]: m[0] for m in modes} if modes else {}

        ctk.CTkLabel(main_frame, text="Mode de Paiement:",
                     font=_F(_FONT_SIZE_MD, "bold")).grid(
            row=6, column=0, sticky="w", padx=8, pady=(0, 4)
        )
        mode_combo_global = ctk.CTkComboBox(main_frame, values=mode_names,
                                            font=_F(_FONT_SIZE_MD))
        if mode_names:
            default_mode = "Espèces" if "Espèces" in mode_names else mode_names[0]
            mode_combo_global.set(default_mode)
        mode_combo_global.grid(row=7, column=0, sticky="ew", padx=8, pady=(0, 10))
        
        def enregistrer_paiement_global():
            try:
                montant_global = float(entry_montant.get().replace(',', '.'))
                observation = entry_obs.get().strip()
                
                if montant_global <= 0:
                    messagebox.showwarning("Attention", "Le montant doit être supérieur à 0.")
                    return
                
                if montant_global > credit_total_restant:
                    messagebox.showwarning("Attention", f"Le montant dépasse le solde total ({credit_total_restant:,.2f} Ar).")
                    return
                
                selected_mode_global = mode_combo_global.get() if mode_names else None
                idmode_sel_global = mode_map.get(selected_mode_global) if selected_mode_global else None
                observation = f"Paiement crédit client : {self._get_client_name(idclient)}" + (f" (Desc: {observation})" if observation else "")
                
                date_pmt = datetime.now()
                ref_ticket = f"PMTC-{idclient}-{date_pmt.strftime('%Y%m%d%H%M%S')}"
                self.cursor.execute("""
                    INSERT INTO tb_pmtcredit 
                    (datepmt, mtpaye, observation, idtypeoperation, idclient, refvente, idmode, idpaiment, refpmt, id_banque, iduser)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (date_pmt, montant_global, observation, 1, idclient, None, idmode_sel_global, None, ref_ticket, None, 1))
                
                self.conn.commit()
                
                messagebox.showinfo("Succès", f"Paiement global de {montant_global:,.2f} Ar enregistré avec succès!")

                societe_data = self._get_societe_info()
                societe_tuple = (
                    societe_data.get('name', ''), societe_data.get('addr', ''),
                    societe_data.get('ville', ''), societe_data.get('tel', ''),
                )
                username = self._get_username_by_id(1)
                client_nom = self._get_client_name(idclient)
                articles = [("", "Paiement global crédit client", "", 1, float(montant_global), float(montant_global))]

                result = messagebox.askyesno("Imprimer", "Voulez-vous ouvrir le facture PDF de paiement ?")
                self._generer_ticket_pdf_paiement_credit(
                    societe=societe_tuple, username=username, articles=articles,
                    montant=float(montant_global), mode_nom=selected_mode_global or "Credit",
                    refpmt=ref_ticket, idclient=idclient, client_nom=client_nom,
                    observation=observation, date_paiement=date_pmt, open_after=result
                )
                
                self._render_credit_table(tree_credits, idclient, label_montant_restant)
                payment_window.destroy()
            
            except ValueError:
                messagebox.showerror("Erreur", "Veuillez entrer un montant valide.")
            except psycopg2.Error as err:
                self.conn.rollback()
                messagebox.showerror("Erreur", f"Erreur enregistrement paiement: {err}")
        
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.grid(row=8, column=0, sticky="e", padx=8, pady=(6, 4))
        
        ctk.CTkButton(
            btn_frame, text="Effectuer le Paiement",
            command=enregistrer_paiement_global,
            fg_color="#2ecc71", width=170,
            font=_F(_FONT_SIZE_MD, "bold")
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            btn_frame, text="Annuler",
            command=payment_window.destroy,
            fg_color="#e74c3c", width=130,
            font=_F(_FONT_SIZE_MD, "bold")
        ).pack(side="left", padx=5)

    def _formater_nombre(self, nombre):
        if isinstance(nombre, (int, float)):
            return f"{nombre:,.2f}".replace(",", " ").replace(".", ",")
        return str(nombre)

    def _extract_days_from_label(self, label):
        if not label or "(" not in label:
            return float("inf")
        try:
            inside = label.split("(", 1)[1].split(")", 1)[0]
            days_str = "".join(ch for ch in inside if ch.isdigit())
            return int(days_str) if days_str else float("inf")
        except Exception:
            return float("inf")

    def _get_dernier_credit_label(self, idclient):
        try:
            self.cursor.execute("""
                SELECT id, 'Crédit Vente' as type, refvente, datepmt, mtpaye, dateecheance
                FROM tb_pmtfacture
                WHERE idclient = %s AND idmode = 4 AND deleted = 0
                ORDER BY datepmt DESC LIMIT 1
            """, (idclient,))
            row = self.cursor.fetchone()
            if not row or not row[3]:
                return "-"

            date_pmt = row[3]
            date_ref = date_pmt.date() if hasattr(date_pmt, "date") else date_pmt
            jours = (datetime.now().date() - date_ref).days
            jours = max(jours, 0)
            return "-" if jours is None else "Aujourd'hui" if jours == 0 else f"il y a {jours} jours"
        except Exception:
            return "-"

    def _fetch_client_credits(self, idclient):
        self.cursor.execute("""
            SELECT id, 'Crédit Vente' as type, refvente, datepmt, mtpaye, dateecheance
            FROM tb_pmtfacture
            WHERE idclient = %s AND idmode = 4 AND deleted = 0
        """, (idclient,))
        credits_vente = self.cursor.fetchall()

        self.cursor.execute("""
            SELECT id, 'Créance' as type, numfact, dateregistre, montant, dateecheance
            FROM tb_autrecreance
            WHERE idclient = %s
        """, (idclient,))
        autrecreances = self.cursor.fetchall()

        tous_credits = credits_vente + autrecreances
        tous_credits.sort(key=lambda x: x[3], reverse=True)
        return tous_credits

    def _compute_credit_status_fifo(self, idclient):
        tous_credits_desc = self._fetch_client_credits(idclient)

        self.cursor.execute("""
            SELECT COALESCE(SUM(mtpaye), 0)
            FROM tb_pmtcredit
            WHERE idclient = %s
        """, (idclient,))
        total_paye_global = float(self.cursor.fetchone()[0] or 0)

        total_initial = sum(float(c[4] or 0) for c in tous_credits_desc)
        paid_remaining = total_paye_global

        credits_asc = sorted(tous_credits_desc, key=lambda x: x[3] or datetime.min)
        status_map = {}

        for credit in credits_asc:
            credit_id, type_credit, ref, date_credit, montant_initial, _ = credit
            montant_initial = float(montant_initial or 0)
            key = f"{type_credit}_{credit_id}"

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
        return tous_credits_desc, total_initial, total_paye_global, total_restant, status_map

    def _render_credit_table(self, tree_credits, idclient, label_montant_restant=None):
        for item in tree_credits.get_children():
            tree_credits.delete(item)

        tous_credits_desc, total_initial, total_paye_global, total_restant, status_map = self._compute_credit_status_fifo(idclient)

        for credit in tous_credits_desc:
            credit_id, type_credit, ref, date_credit, montant_initial, _ = credit
            key = f"{type_credit}_{credit_id}"
            montant_paye_ligne, solde_restant, statut, tag = status_map.get(key, (0.0, float(montant_initial or 0), "✗ Impayé", "impaye"))

            tree_credits.insert('', 'end', iid=key, values=(
                credit_id, type_credit,
                date_credit.strftime("%d/%m/%Y %H:%M") if date_credit else "N/A",
                ref,
                f"{float(montant_initial or 0):,.2f}",
                f"{montant_paye_ligne:,.2f}",
                f"{solde_restant:,.2f}",
                statut
            ), tags=(tag,))

        if label_montant_restant is not None:
            label_montant_restant.configure(text=f"{total_restant:,.2f} Ar")

        return total_initial, total_paye_global, total_restant

    def _get_societe_info(self):
        defaults = {'name':'IJEERY','addr':'','ville':'','tel':'','nif':'','stat':'','cif':''}
        if not self.conn:
            return defaults
        try:
            self.cursor.execute("""
                SELECT nomsociete, adressesociete, villesociete, contactsociete, nifsociete, statsociete, cifsociete
                FROM tb_infosociete LIMIT 1
            """)
            societe = self.cursor.fetchone()
            if not societe:
                return defaults
            return {
                'name': societe[0] or defaults['name'], 'addr': societe[1] or defaults['addr'],
                'ville': societe[2] or defaults['ville'], 'tel': societe[3] or defaults['tel'],
                'nif': societe[4] or defaults['nif'], 'stat': societe[5] or defaults['stat'],
                'cif': societe[6] or defaults['cif']
            }
        except psycopg2.Error:
            try:
                if self.conn:
                    self.conn.rollback()
            except Exception:
                pass
            return defaults

    def _generate_ticket_80mm_creance(self, idclient, num_fact, montant, filename):
        MAX_WIDTH = 40
        soc = self._get_societe_info()
        societe_name = soc.get('name')
        societe_addr = soc.get('addr')
        societe_ville = soc.get('ville')
        societe_tel = soc.get('tel')
        societe_nif = soc.get('nif')
        societe_stat = soc.get('stat')
        societe_cif = soc.get('cif')

        try:
            self.cursor.execute("SELECT nomcli, prenomcli FROM tb_client WHERE idclient = %s", (idclient,))
            client = self.cursor.fetchone()
            client_name = f"{client[0]} {client[1]}" if client else "CLIENT"
        except psycopg2.Error:
            try:
                if self.conn:
                    self.conn.rollback()
            except Exception:
                pass
            client_name = "CLIENT"

        def center(text): return text.center(MAX_WIDTH)
        def line(): return "-" * MAX_WIDTH
        def wrap_text(text, max_width=MAX_WIDTH):
            lines = []
            for line_text in str(text).split("\n"):
                if len(line_text) <= max_width:
                    lines.append(line_text)
                else:
                    import textwrap
                    wrapped = textwrap.wrap(line_text, max_width)
                    lines.extend(wrapped)
            return lines

        content = [line(), center(societe_name.upper())]
        if societe_addr: content.extend(wrap_text(center(societe_addr)))
        if societe_ville: content.append(center(societe_ville))
        if societe_nif: content.append(center(f"NIF: {societe_nif}"))
        if societe_stat: content.append(center(f"STAT: {societe_stat}"))
        if societe_cif: content.append(center(f"CIF: {societe_cif}"))
        if societe_tel: content.append(center(f"Tél: {societe_tel}"))
        content += [line(), center("ENREGISTREMENT CRÉANCE"), line(),
                    f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                    f"Créance N°: {num_fact}", f"Client: {client_name}", line(),
                    center("MONTANT"), center(f"{self._formater_nombre(montant)} Ar"), line(),
                    center("Créance Enregistrée"), center(datetime.now().strftime("%d/%m/%Y")), "\n"]
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur génération ticket créance: {e}")

    def _get_username_by_id(self, iduser=1):
        if iduser is None:
            iduser = self._get_connected_user_id()
        if not self.conn:
            return "Utilisateur"
        try:
            self.cursor.execute("SELECT username FROM tb_users WHERE iduser = %s", (iduser,))
            row = self.cursor.fetchone()
            return row[0] if row and row[0] else "Utilisateur"
        except Exception:
            try:
                self.conn.rollback()
            except Exception:
                pass
            return "Utilisateur"

    def _get_connected_user_id(self):
        if self.id_user_connecte is not None:
            return self.id_user_connecte
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

    def _get_client_name(self, idclient):
        if not self.conn:
            return "CLIENT"
        try:
            self.cursor.execute("SELECT nomcli FROM tb_client WHERE idclient = %s", (idclient,))
            row = self.cursor.fetchone()
            return row[0] if row and row[0] else "CLIENT"
        except Exception:
            try:
                self.conn.rollback()
            except Exception:
                pass
            return "CLIENT"

    def _generer_ticket_pdf_creance(self, societe, username, articles, montant, mode_nom, refpmt, client_nom, montant_total, open_after=False):
        try:
            fd, path = tempfile.mkstemp(prefix='ticket_creance_', suffix='.pdf')
            os.close(fd)

            total_height = (160 + (len(articles) * 10)) * mm
            c = canvas.Canvas(path, pagesize=(80 * mm, total_height))
            y = total_height - 10 * mm

            if societe:
                c.setFont("Helvetica-Bold", 11)
                c.drawCentredString(40 * mm, y, str(societe[0]).upper())
                y -= 5 * mm
                c.setFont("Helvetica", 8)
                c.drawCentredString(40 * mm, y, f"{societe[1] or ''}")
                y -= 4 * mm
                c.drawCentredString(40 * mm, y, f"{societe[2] or ''}")
                y -= 4 * mm
                c.drawCentredString(40 * mm, y, f"Tel: {societe[3] or ''}")
                y -= 2 * mm
            else:
                c.setFont("Helvetica-Bold", 10)
                c.drawCentredString(40 * mm, y, "MA SOCIETE")
                y -= 4 * mm

            y -= 4 * mm
            c.line(5 * mm, y, 75 * mm, y)
            y -= 6 * mm
            c.setFont("Helvetica-Bold", 9)
            c.drawCentredString(40 * mm, y, f"VALIDATION CREANCE")
            y -= 6 * mm
            c.setFont("Helvetica", 8)
            c.drawString(5 * mm, y, f"Ref: {refpmt}")
            y -= 4 * mm
            c.drawString(5 * mm, y, f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            y -= 4 * mm
            c.drawString(5 * mm, y, f"Client: {client_nom}")
            y -= 10 * mm
            c.setFont("Helvetica-Bold", 7)
            c.drawString(5 * mm, y, "Code")
            c.drawString(20 * mm, y, "Designation")
            c.drawRightString(48 * mm, y, "Qte")
            c.drawRightString(62 * mm, y, "P.U")
            c.drawRightString(77 * mm, y, "Total")
            y -= 2 * mm
            c.line(5 * mm, y, 75 * mm, y)
            y -= 4 * mm
            c.setFont("Helvetica", 6.5)
            for art in articles:
                code = str(art[0])[:8] if art[0] else ""
                designation = f"{art[1]} ({art[2]})" if art[2] else str(art[1])
                designation = designation[:20]
                c.drawString(5 * mm, y, code)
                c.drawString(20 * mm, y, designation)
                c.drawRightString(48 * mm, y, str(art[3]))
                c.drawRightString(62 * mm, y, f"{art[4]:,.0f}".replace(',', ' '))
                c.drawRightString(77 * mm, y, f"{art[5]:,.0f}".replace(',', ' '))
                y -= 8 * mm
            c.setFont("Helvetica-Bold", 10)
            c.drawString(5 * mm, y, "MONTANT CREANCE :")
            c.drawRightString(75 * mm, y, f"{montant:,.2f} Ar".replace(',', ' ').replace('.', ','))
            y -= 8 * mm
            if num2words:
                c.setFont("Helvetica-Oblique", 6)
                try:
                    lettres = num2words(int(montant), lang='fr').upper()
                    if len(lettres) > 45:
                        c.drawString(5 * mm, y, f"Arrete a: {lettres[:45]}")
                        y -= 3 * mm
                        c.drawString(5 * mm, y, f"{lettres[45:]} ARIARY")
                    else:
                        c.drawString(5 * mm, y, f"Arrete a: {lettres} ARIARY")
                except Exception:
                    pass
            y -= 10 * mm
            c.line(5 * mm, y + 2 * mm, 75 * mm, y + 2 * mm)
            c.setFont("Helvetica", 7)
            c.drawString(5 * mm, y, f"Mode de paiement: {mode_nom}")
            y -= 5 * mm
            c.setFont("Helvetica-Bold", 8)
            c.drawString(5 * mm, y, f"Recu par: {username}")
            c.showPage()
            c.save()
            if open_after:
                if os.name == 'nt':
                    os.startfile(path)
                else:
                    subprocess.Popen(['xdg-open', path])
            return path
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur génération PDF créance: {e}")
            return None

    def _generer_ticket_pdf_paiement_credit(self, societe, username, articles, montant, mode_nom, refpmt, idclient, client_nom, observation, date_paiement, open_after=False):
        try:
            client_adresse = "-"
            client_contact = "-"
            try:
                self.cursor.execute(
                    "SELECT adressecli, contactcli FROM tb_client WHERE idclient = %s", (idclient,))
                row = self.cursor.fetchone()
                if row:
                    client_adresse = row[0] or "-"
                    client_contact = row[1] or "-"
            except Exception:
                try:
                    self.conn.rollback()
                except Exception:
                    pass

            temp_dir = tempfile.gettempdir()
            path = os.path.join(temp_dir, f"Paiement_Credit_{refpmt}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")

            page_width, _ = landscape(A5)
            margin = 5 * mm
            usable_width = page_width - 2 * margin

            doc = SimpleDocTemplate(path, pagesize=landscape(A5),
                                    rightMargin=margin, leftMargin=margin,
                                    topMargin=margin, bottomMargin=margin)

            elements = []
            styles = getSampleStyleSheet()
            color_header = colors.HexColor("#034787")

            verse_title = Paragraph(
                "Ankino amin'ny Jehovah ny asanao dia ho lavorary izay kasainao. Ohabolana 16:3",
                ParagraphStyle("MainTitleCredit", parent=styles["Normal"], fontSize=10,
                               textColor=colors.black, alignment=TA_CENTER,
                               fontName="Helvetica-Bold", spaceAfter=3))
            verse_table = Table([[verse_title]], colWidths=[usable_width])
            verse_table.setStyle(TableStyle([
                ("BOX",(0,0),(-1,-1),1,colors.black),
                ("ALIGN",(0,0),(-1,-1),"CENTER"),
                ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                ("TOPPADDING",(0,0),(-1,-1),0),
                ("BOTTOMPADDING",(0,0),(-1,-1),3),
            ]))
            elements.append(verse_table)

            company_width = usable_width * 0.33
            right_width = usable_width * 0.67 - 2 * mm
            title_width = right_width * 0.55
            info_width = right_width * 0.45
            header_height = 28 * mm

            nom_soc = societe[0] if societe else "IJEERY"
            adr_soc = societe[1] if societe and len(societe) > 1 else ""
            ville_soc = societe[2] if societe and len(societe) > 2 else ""
            contact_soc = societe[3] if societe and len(societe) > 3 else ""

            company_details = Paragraph(
                f"<b>{nom_soc}</b><br/>Adresse : {adr_soc}<br/>Ville : {ville_soc}<br/>Contact : {contact_soc}<br/>",
                ParagraphStyle("CompanyCredit", parent=styles["Normal"], fontSize=9, alignment=TA_LEFT, leading=12))
            company_table = Table([[company_details]], colWidths=[company_width - 2 * mm], rowHeights=[header_height])
            company_table.setStyle(TableStyle([
                ("BOX",(0,0),(-1,-1),1,colors.black), ("VALIGN",(0,0),(-1,-1),"TOP"),
                ("TOPPADDING",(0,0),(-1,-1),6), ("BOTTOMPADDING",(0,0),(-1,-1),6),
                ("LEFTPADDING",(0,0),(-1,-1),6), ("RIGHTPADDING",(0,0),(-1,-1),6),
            ]))

            operation_title = Paragraph(
                "PAIEMENT DE CREDIT",
                ParagraphStyle("OpCreditTitle", parent=styles["Normal"], fontSize=14,
                               fontName="Helvetica-Bold", alignment=TA_CENTER, textColor=color_header))
            operation_info = Paragraph(
                f"<b>Reference :</b> {refpmt}<br/>"
                f"<b>Date et heure :</b> {date_paiement.strftime('%d/%m/%Y %H:%M')}<br/>"
                f"<b>Mode de paiement :</b> {mode_nom}<br/>"
                f"<b>Operateur :</b> {username}",
                ParagraphStyle("OpCreditInfo", parent=styles["Normal"], fontSize=9, alignment=TA_LEFT, leading=12))
            operation_table = Table([[operation_title, operation_info]],
                                    colWidths=[title_width, info_width], rowHeights=[header_height])
            operation_table.setStyle(TableStyle([
                ("BOX",(0,0),(-1,-1),1,colors.black), ("ALIGN",(0,0),(0,0),"CENTER"),
                ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                ("TOPPADDING",(0,0),(-1,-1),6), ("BOTTOMPADDING",(0,0),(-1,-1),6),
                ("LEFTPADDING",(0,0),(-1,-1),6), ("RIGHTPADDING",(0,0),(-1,-1),6),
            ]))

            header_table = Table([[company_table, operation_table]], colWidths=[company_width, right_width])
            header_table.setStyle(TableStyle([
                ("VALIGN",(0,0),(-1,-1),"TOP"),
                ("TOPPADDING",(0,0),(-1,-1),4), ("BOTTOMPADDING",(0,0),(-1,-1),4),
                ("RIGHTPADDING",(0,0),(0,0),8), ("LEFTPADDING",(1,0),(1,0),8),
            ]))
            elements.append(header_table)
            elements.append(Spacer(1, 3 * mm))

            elements.append(Paragraph(
                "<b><u>Infos Paiement Credit</u></b><br/>",
                ParagraphStyle("InfoCreditLine", parent=styles["Normal"], fontSize=9, alignment=TA_CENTER, leading=11)))
            elements.append(Spacer(1, 2 * mm))

            columns_pdf = ["Reference", "Nom Client", "Montant"]
            row_data = [[refpmt, client_nom, self._formater_nombre(montant) + " Ar"]]

            try:
                _, _, _, total_restant, _ = self._compute_credit_status_fifo(idclient)
            except Exception:
                total_restant = 0

            footer_row = ["Reste de Crédit", "", self._formater_nombre(total_restant) + " Ar"]
            table_width = usable_width * 0.95
            col_widths_pdf = [table_width * 0.25, table_width * 0.43, table_width * 0.32]
            table_data = [columns_pdf] + row_data + [footer_row]

            credit_table = Table(table_data, colWidths=col_widths_pdf, repeatRows=1)
            style_list = [
                ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#E8E8E8")),
                ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                ("FONTSIZE",(0,0),(-1,0),12),
                ("ALIGN",(0,0),(-1,0),"CENTER"),
                ("ALIGN",(0,1),(1,-2),"LEFT"),
                ("ALIGN",(2,1),(2,-2),"CENTER"),
                ("FONTSIZE",(0,1),(-1,-1),8),
                ("BOX",(0,0),(-1,-1),1,colors.black),
                ("LINEBEFORE",(1,0),(1,-1),1,color_header),
                ("LINEBEFORE",(2,0),(2,-1),1,color_header),
                ("TOPPADDING",(0,0),(-1,-1),4),
                ("BOTTOMPADDING",(0,0),(-1,-1),4),
            ]
            last_row = len(table_data) - 1
            style_list.extend([
                ("SPAN",(0,last_row),(1,last_row)),
                ("ALIGN",(0,last_row),(1,last_row),"RIGHT"),
                ("ALIGN",(2,last_row),(2,last_row),"CENTER"),
                ("FONTNAME",(0,last_row),(2,last_row),"Helvetica-Bold"),
                ("FONTSIZE",(0,last_row),(2,last_row),10),
                ("BACKGROUND",(0,last_row),(2,last_row),colors.HexColor("#F5F5F5")),
                ("LINEABOVE",(0,last_row),(2,last_row),1,color_header),
            ])
            credit_table.setStyle(TableStyle(style_list))
            elements.append(credit_table)
            elements.append(Spacer(1, 3 * mm))

            coord_client = Paragraph(
                f"<br/>&nbsp;&nbsp;&nbsp;<b><u>Description :</u></b> {observation}",
                ParagraphStyle("CoordClient", parent=styles["Normal"], fontSize=9, alignment=TA_LEFT, leading=11))
            elements.append(coord_client)
            elements.append(Spacer(1, 1.5 * mm))

            coord_client2 = Paragraph(
                f"<br/>&nbsp;&nbsp;&nbsp;<b><u>Coordonnees client :</u></b> {client_adresse} ; Tel : {client_contact}",
                ParagraphStyle("CoordClient2", parent=styles["Normal"], fontSize=9, alignment=TA_LEFT, leading=11))
            elements.append(coord_client2)
            elements.append(Spacer(1, 1.5 * mm))

            sig_left = Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;<u>Le Responsable</u>",
                                 ParagraphStyle("SigRespo", parent=styles["Normal"], fontSize=9, alignment=TA_LEFT))
            sig_right = Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;<u>Le Client</u>",
                                  ParagraphStyle("SigClient", parent=styles["Normal"], fontSize=9, alignment=TA_LEFT))
            sig_table = Table([[sig_left, "", sig_right]],
                              colWidths=[usable_width * 0.35, usable_width * 0.30, usable_width * 0.35])
            sig_table.setStyle(TableStyle([
                ("TOPPADDING",(0,0),(-1,-1),10),
                ("ALIGN",(0,0),(0,0),"LEFT"),
                ("ALIGN",(2,0),(2,0),"RIGHT"),
            ]))
            elements.append(sig_table)

            doc.build(elements)
            if open_after:
                if os.name == 'nt':
                    os.startfile(path)
                else:
                    subprocess.Popen(['xdg-open', path])
            return path
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur génération PDF paiement crédit: {e}")
            return None

    def _generate_ticket_80mm_payment(self, idclient, montant, idmode, date_pmt, filename):
        MAX_WIDTH = 40
        soc = self._get_societe_info()
        societe_name = soc.get('name')
        societe_addr = soc.get('addr')
        societe_ville = soc.get('ville')
        societe_tel = soc.get('tel')
        societe_nif = soc.get('nif')
        societe_stat = soc.get('stat')
        societe_cif = soc.get('cif')

        try:
            self.cursor.execute("SELECT nomcli, prenomcli FROM tb_client WHERE idclient = %s", (idclient,))
            client = self.cursor.fetchone()
            client_name = f"{client[0]} {client[1]}" if client else "CLIENT"
        except psycopg2.Error:
            try:
                if self.conn:
                    self.conn.rollback()
            except Exception:
                pass
            client_name = "CLIENT"

        try:
            self.cursor.execute("SELECT modedepaiement FROM tb_modepaiement WHERE idmode = %s", (idmode,))
            mode = self.cursor.fetchone()
            mode_name = mode[0] if mode else "ESPÈCES"
        except psycopg2.Error:
            try:
                if self.conn:
                    self.conn.rollback()
            except Exception:
                pass
            mode_name = "ESPÈCES"

        def center(text): return text.center(MAX_WIDTH)
        def line(): return "-" * MAX_WIDTH
        def wrap_text(text, max_width=MAX_WIDTH):
            lines = []
            for line_text in str(text).split("\n"):
                if len(line_text) <= max_width:
                    lines.append(line_text)
                else:
                    wrapped = textwrap.wrap(line_text, max_width)
                    lines.extend(wrapped)
            return lines

        content = [line(), center(societe_name.upper())]
        if societe_addr: content.extend(wrap_text(center(societe_addr)))
        if societe_ville: content.append(center(societe_ville))
        if societe_nif: content.append(center(f"NIF: {societe_nif}"))
        if societe_stat: content.append(center(f"STAT: {societe_stat}"))
        if societe_cif: content.append(center(f"CIF: {societe_cif}"))
        if societe_tel: content.append(center(f"Tél: {societe_tel}"))
        content += [line(), center("REÇU PAIEMENT CRÉDIT CLIENT"), line(),
                    f"Date: {date_pmt.strftime('%d/%m/%Y %H:%M')}",
                    f"Client: {client_name}", f"Mode: {mode_name}", line(),
                    center("MONTANT PAYÉ"), center(f"{self._formater_nombre(montant)} Ar"), line(),
                    center("Paiement Reçu"), center(datetime.now().strftime("%d/%m/%Y %H:%M")), "\n"]
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur génération ticket paiement: {e}")

    def _print_ticket_80mm(self, filename):
        try:
            if os.path.exists(filename):
                if os.name == 'nt':
                    subprocess.Popen(['notepad.exe', '/p', filename])
                else:
                    subprocess.Popen(['lpr', filename])
        except Exception as e:
            messagebox.showwarning("Impression", f"Ne peut pas imprimer automatiquement. Fichier: {filename}")

    def _open_add_creance_window(self, idclient, parent_window):
        creance_window = ctk.CTkToplevel(parent_window)
        creance_window.title("Ajouter une Créance")
        parent_window.update_idletasks()
        parent_w = max(parent_window.winfo_width(), 1)
        parent_h = max(parent_window.winfo_height(), 1)
        parent_x = parent_window.winfo_x()
        parent_y = parent_window.winfo_y()

        win_w = max(560, int(parent_w * 0.45))
        win_h = max(360, int(parent_h * 0.5))
        pos_x = parent_x + (parent_w - win_w) // 2
        pos_y = parent_y + (parent_h - win_h) // 2
        creance_window.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
        creance_window.minsize(560, 360)
        creance_window.grab_set()
        creance_window.grid_columnconfigure(0, weight=1)
        creance_window.grid_rowconfigure(0, weight=1)

        main_frame = ctk.CTkFrame(creance_window)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        main_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            main_frame, text="Enregistrer une Créance Manuelle",
            font=_F(_FONT_SIZE_LG, "bold")
        ).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 10))
        
        ctk.CTkLabel(main_frame, text="Référence :",
                     font=_F(_FONT_SIZE_MD, "bold")).grid(
            row=1, column=0, sticky="w", padx=8, pady=(2, 4))
        entry_numfact = ctk.CTkEntry(main_frame,
                                     placeholder_text="Entrez une référence (ex: FACT-001)",
                                     font=_F(_FONT_SIZE_MD))
        entry_numfact.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        
        ctk.CTkLabel(main_frame, text="Montant (Ar) :",
                     font=_F(_FONT_SIZE_MD, "bold")).grid(
            row=3, column=0, sticky="w", padx=8, pady=(2, 4))
        entry_montant = ctk.CTkEntry(main_frame, placeholder_text="Ex: 50000",
                                     font=_F(_FONT_SIZE_MD))
        entry_montant.grid(row=4, column=0, sticky="ew", padx=8, pady=(0, 8))
        
        def enregistrer_creance():
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
                        pg_get_serial_sequence('tb_autrecreance', 'id'),
                        COALESCE((SELECT MAX(id) FROM tb_autrecreance), 0) + 1, false
                    )
                """)
                self.cursor.execute("""
                    INSERT INTO tb_autrecreance (idclient, dateregistre, numfact, montant)
                    VALUES (%s, %s, %s, %s)
                """, (idclient, datetime.now(), num_fact, montant))
                self.conn.commit()
                
                messagebox.showinfo("Succès", f"Créance de {montant:,.2f} Ar enregistrée avec succès!")
                
                username = self._get_username_by_id(1)
                societe_data = self._get_societe_info()
                societe_tuple = (
                    societe_data.get('name', ''), societe_data.get('addr', ''),
                    societe_data.get('ville', ''), societe_data.get('tel', ''),
                )
                articles = [("", "Creance manuelle", "", 1, float(montant), float(montant))]
                result = messagebox.askyesno("Imprimer", "Voulez-vous ouvrir le ticket PDF de créance ?")
                self._generer_ticket_pdf_creance(
                    societe=societe_tuple, username=username, articles=articles,
                    montant=float(montant), mode_nom="Credit", refpmt=num_fact,
                    client_nom=self._get_client_name(idclient), montant_total=float(montant),
                    open_after=result
                )
                
                creance_window.destroy()
                parent_window.destroy()
                self.open_client_credit_details(idclient)
            
            except ValueError:
                messagebox.showerror("Erreur", "Veuillez entrer un montant valide (nombre).")
            except psycopg2.Error as err:
                self.conn.rollback()
                messagebox.showerror("Erreur", f"Erreur enregistrement créance: {err}")
        
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.grid(row=5, column=0, sticky="e", padx=8, pady=(10, 6))
        
        ctk.CTkButton(btn_frame, text="Enregistrer", command=enregistrer_creance,
                     fg_color="#27ae60", font=_F(_FONT_SIZE_MD, "bold")).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Annuler", command=creance_window.destroy,
                     fg_color="#e74c3c", font=_F(_FONT_SIZE_MD, "bold")).pack(side="left", padx=5)


if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("1000x600")
    PageClient(app).pack(fill="both", expand=True)
    app.mainloop()
