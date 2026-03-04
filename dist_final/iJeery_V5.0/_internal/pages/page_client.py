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

class PageClient(ctk.CTkFrame):
    def __init__(self, master, db_conn=None, session_data=None, id_user_connecte=None):
        super().__init__(master)
        
        self.type_mapping = {}  # Dictionnaire pour stocker {Désignation: ID}
        self.session_data = session_data or {}
        self.id_user_connecte = id_user_connecte
        if self.id_user_connecte is None:
            self.id_user_connecte = (
                self.session_data.get("user_id")
                or self.session_data.get("iduser")
                or getattr(master, "id_user_connecte", None)
            )
        
        # Connexion à la base de données
        self.conn = self.connect_db()
        if self.conn:
            self.cursor = self.conn.cursor()
            self.create_table()
        
        self.setup_ui()
        self.load_types() # Charger les types dans la combobox
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
        """Récupère uniquement le type de client avec l'ID 2 pour la ComboBox."""
        try:
            # Ajout de la condition WHERE idtypeclient = 2
            self.cursor.execute("SELECT idtypeclient, designationtypeclient FROM tb_typeclient WHERE idtypeclient = 2")
            types = self.cursor.fetchall()
            
            self.type_mapping = {t[1]: t[0] for t in types}
            self.type_combo.configure(values=list(self.type_mapping.keys()))
            
            if self.type_mapping:
                self.type_combo.set(list(self.type_mapping.keys())[0])
            else:
                # Optionnel : vider la combobox si l'ID 2 n'existe pas en base
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
        
        ctk.CTkLabel(row1, text="Nom du Client:").pack(side="left", padx=5)
        self.nomCli_entry = ctk.CTkEntry(row1, width=150)
        self.nomCli_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(row1, text="Contact:").pack(side="left", padx=5)
        self.contactCli_entry = ctk.CTkEntry(row1, width=150)
        self.contactCli_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(row1, text="Adresse:").pack(side="left", padx=5)
        self.adresseCli_entry = ctk.CTkEntry(row1, width=150)
        self.adresseCli_entry.pack(side="left", padx=5)
        
        # Deuxième ligne
        row2 = ctk.CTkFrame(input_frame)
        row2.pack(fill="x", pady=5)
        
        ctk.CTkLabel(row2, text="NIF:").pack(side="left", padx=5)
        self.nifCli_entry = ctk.CTkEntry(row2, width=120)
        self.nifCli_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(row2, text="Plafond de Crédit:").pack(side="left", padx=5)
        self.credit_entry = ctk.CTkEntry(row2, width=120)
        self.credit_entry.pack(side="left", padx=5)

        # NOUVEAU: ComboBox pour Type de Client
        ctk.CTkLabel(row2, text="Type Client:").pack(side="left", padx=5)
        self.type_combo = ctk.CTkComboBox(row2, width=150, values=[])
        self.type_combo.pack(side="left", padx=5)
        
        # Frame pour les boutons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", pady=10)
        
        self.add_button = ctk.CTkButton(button_frame, text="Ajouter", command=self.add_client, fg_color="#2ecc71")
        self.add_button.pack(side="left", padx=5)
        
        self.modify_button = ctk.CTkButton(button_frame, text="Modifier", command=self.modify_client, fg_color="#3498db")
        self.modify_button.pack(side="left", padx=5)
        
        self.delete_button = ctk.CTkButton(button_frame, text="Supprimer", command=self.delete_client, fg_color="#e74c3c")
        self.delete_button.pack(side="left", padx=5)

        # NOUVEAU : Bouton Crédit
        self.credit_page_button = ctk.CTkButton(button_frame, text="Crédit", 
                                       command=self.open_credit_window,
                                       fg_color="#f39c12", hover_color="#e67e22")
        # Masquer le bouton "Crédit" sur cette page
        # self.credit_page_button.pack(side="left", padx=5)
        
        # --- Frame de Recherche ---
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", pady=10, padx=0)
        
        ctk.CTkLabel(search_frame, text="Rechercher Client :", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        self.search_entry = ctk.CTkEntry(search_frame, width=300, placeholder_text="Nom, contact, adresse, NIF ou crédit...")
        self.search_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        # Stocker les données complètes pour la recherche
        self.all_clients_data = []
        
        # Bind pour mise à jour en temps réel
        self.search_entry.bind("<KeyRelease>", self.filter_clients)
        
        # Treeview
        columns = ("Nom du Client", "Contact", "Adresse", "NIF", "Crédit en cours", "Type")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        self.tree.tag_configure("even", background="#FFFFFF", foreground="#000000")
        self.tree.tag_configure("odd", background="#E6EFF8", foreground="#000000")
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)
        
        self.tree.pack(fill="both", expand=True, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", self.on_client_double_click)
        
        self.selected_cli_id = None

    def load_client(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        if not self.conn: return

        try:
            # On masque idtypeclient = 1 avec la clause WHERE
            self.cursor.execute("""
                SELECT c.idclient, c.nomcli, c.contactcli, c.adressecli, c.nifcli, c.credit, t.designationtypeclient
                FROM tb_client c
                LEFT JOIN tb_typeclient t ON c.idtypeclient = t.idtypeclient
                WHERE c.idtypeclient != 1
                ORDER BY c.nomcli ASC
            """)
            clients = self.cursor.fetchall()
            self.all_clients_data = clients  # Stocker les données complètes
            
            for idx, cli in enumerate(clients):
                tag = "even" if idx % 2 == 0 else "odd"
                # calcul crédit restant
                try:
                    _, _, _, credit_restant, _ = self._compute_credit_status_fifo(cli[0])
                except Exception:
                    credit_restant = 0
                credit_str = f" {self._formater_nombre(credit_restant)} Ar"
                self.tree.insert("", "end", iid=cli[0], values=(
                    cli[1], cli[2], cli[3], cli[4], credit_str, cli[6]
                ), tags=(tag,))
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors du chargement : {err}")

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
        for entry in [self.nomCli_entry, self.contactCli_entry, self.adresseCli_entry, self.nifCli_entry, self.credit_entry]:
            entry.delete(0, "end")
        self.selected_cli_id = None

    def filter_clients(self, event=None):
        """Filtre les clients en temps réel basé sur la requête de recherche."""
        search_query = self.search_entry.get().lower().strip()
        
        # Vider le treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Si la requête est vide, afficher tous les clients
        if not search_query:
            for idx, cli in enumerate(self.all_clients_data):
                tag = "even" if idx % 2 == 0 else "odd"
                try:
                    _, _, _, credit_restant, _ = self._compute_credit_status_fifo(cli[0])
                except Exception:
                    credit_restant = 0
                credit_str = self._formater_nombre(credit_restant)
                self.tree.insert("", "end", iid=cli[0], values=(
                    cli[1], cli[2], cli[3], cli[4], credit_str, cli[6]
                ), tags=(tag,))
            return
        
        # Filtrer les clients
        idx = 0
        for cli in self.all_clients_data:
            # cli = (idclient, nomcli, contactcli, adressecli, nifcli, credit, typeclient)
            # Chercher dans tous les champs
            nom = str(cli[1]).lower() if cli[1] else ""
            contact = str(cli[2]).lower() if cli[2] else ""
            adresse = str(cli[3]).lower() if cli[3] else ""
            nif = str(cli[4]).lower() if cli[4] else ""
            # calculer crédit restant pour recherche
            try:
                _, _, _, credit_restant, _ = self._compute_credit_status_fifo(cli[0])
            except Exception:
                credit_restant = 0
            credit = str(credit_restant).lower() if credit_restant else ""
            typeclient = str(cli[6]).lower() if cli[6] else ""
            
            # Vérifier si la requête correspond à un champ
            if (search_query in nom or 
                search_query in contact or 
                search_query in adresse or 
                search_query in nif or 
                search_query in credit or
                search_query in typeclient):
                tag = "even" if idx % 2 == 0 else "odd"
                try:
                    _, _, _, credit_restant, _ = self._compute_credit_status_fifo(cli[0])
                except Exception:
                    credit_restant = 0
                credit_str = self._formater_nombre(credit_restant)
                self.tree.insert("", "end", iid=cli[0], values=(cli[1], cli[2], cli[3], cli[4], credit_str, cli[6]), tags=(tag,))
                idx += 1

    def open_credit_window(self):
        """Ouvre la fenêtre des crédits clients dans un nouveau pop-up."""
        credit_window = ctk.CTkToplevel(self)
        credit_window.title("Détails des Crédits Clients")
        credit_window.geometry("900x600")
    
        # Force la fenêtre à être au-dessus
        credit_window.attributes("-topmost", True)
    
        # Rendre la fenêtre redimensionnable
        credit_window.grid_columnconfigure(0, weight=1)
        credit_window.grid_rowconfigure(0, weight=1)
    
        # Initialisation de la page de crédit à l'intérieur du pop-up
        credit_page = PageClientCrédit(credit_window)
        credit_page.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def on_client_double_click(self, event):
        """Appelé au double-clic sur une ligne client."""
        selected = self.tree.selection()
        if not selected:
            return
        
        idclient = selected[0]
        self.open_client_credit_details(idclient)

    def open_client_credit_details(self, idclient):
        """Ouvre une fenêtre avec les détails de crédit personnalisés pour un client."""
        # Récupérer les infos du client
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
        
        # Créer la fenêtre de détails avec une taille responsive
        detail_window = ctk.CTkToplevel(self)
        detail_window.title(f"Détails de Crédit - {client_info[1]}")

        # 50% de la largeur de la fenêtre principale, centrée par rapport à celle-ci
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

        # Désactiver always-on-top: la fenêtre peut passer derrière, perdre le focus, et se minimiser normalement
        detail_window.attributes("-topmost", False)
        
        # Configuration du layout principal (2 colonnes)
        detail_window.grid_columnconfigure(0, weight=0, minsize=350)  # Sidebar gauche (25%)
        detail_window.grid_columnconfigure(1, weight=1)  # Contenu droit (75%)
        detail_window.grid_rowconfigure(0, weight=1)
        
        # ============================================
        # SIDEBAR GAUCHE (25% - Infos Client + Crédit)
        # ============================================
        sidebar_frame = ctk.CTkFrame(detail_window, fg_color="#f0f0f0")
        sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        sidebar_frame.grid_rowconfigure(2, weight=1)  # Pour avoir du space vide
        
        # --- Titre Informations ---
        ctk.CTkLabel(sidebar_frame, text="Informations Client", 
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                    text_color="#2c3e50").pack(anchor="w", padx=10, pady=(10, 5))
        
        # --- Infos Client ---
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
            
            ctk.CTkLabel(info_row, text=label, font=ctk.CTkFont(weight="bold", size=10),
                        text_color="#34495e", width=80).pack(side="left", anchor="nw")
            ctk.CTkLabel(info_row, text=value, font=ctk.CTkFont(size=10),
                        text_color="#2c3e50").pack(side="left", anchor="nw", padx=(5, 0), fill="x", expand=True)
        
        # --- Séparateur ---
        ctk.CTkLabel(sidebar_frame, text="", fg_color="#bdc3c7", height=1).pack(fill="x", pady=10, padx=10)
        
        # --- Titre Crédit ---
        ctk.CTkLabel(sidebar_frame, text="Situation Crédit", 
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                    text_color="#2c3e50").pack(anchor="w", padx=10, pady=(5, 10))
        
        # --- Label Crédit Total ---
        credit_info_frame = ctk.CTkFrame(sidebar_frame, fg_color="transparent")
        credit_info_frame.pack(anchor="w", padx=10, pady=2, fill="x")
        
        ctk.CTkLabel(credit_info_frame, text="Total Restant:", font=ctk.CTkFont(weight="bold", size=10),
                    text_color="#34495e").pack(side="left", anchor="nw")
        label_montant_restant = ctk.CTkLabel(credit_info_frame, text="0,00 Ar", 
                                            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                                            text_color="#e74c3c")
        label_montant_restant.pack(side="left", anchor="nw", padx=(5, 0))
        
        # --- Bouton Paiement Global ---
        btn_paiement_global = ctk.CTkButton(sidebar_frame, text="💳 Effectuer Paiement", 
                                          fg_color="#3498db", hover_color="#2980b9", 
                                          height=40, font=ctk.CTkFont(size=11, weight="bold"),
                                          command=lambda: None)
        btn_paiement_global.pack(padx=10, pady=10, fill="x")
        
        # --- Bouton Ajouter Créance ---
        btn_ajouter_creance = ctk.CTkButton(sidebar_frame, text="➕ Ajouter Créance", 
                                          fg_color="#27ae60", hover_color="#229954", 
                                          height=40, font=ctk.CTkFont(size=11, weight="bold"),
                                          command=lambda: self._open_add_creance_window(idclient, detail_window))
        btn_ajouter_creance.pack(padx=10, pady=10, fill="x")
        
        # ============================================
        # CONTENU DROIT (75% - Crédits + Paiements)
        # ============================================
        right_frame = ctk.CTkFrame(detail_window)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(0, weight=1)
        right_frame.grid_rowconfigure(1, weight=1)
        
        # --- TABLEAU DES CRÉDITS (Haut) ---
        table_frame = ctk.CTkFrame(right_frame)
        table_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=(0, 5))
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_columnconfigure(1, weight=0)
        table_frame.grid_rowconfigure(0, weight=0)
        table_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(table_frame, text="Récapitulatif des Crédits", 
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))
        
        # Créer le treeview des crédits
        colonnes_credits = ("ID", "Type", "Date", "Montant", "Montant Payé", "Solde Restant", "Statut")
        tree_credits = ttk.Treeview(table_frame, columns=colonnes_credits, show='headings', height=10)
        tree_credits.tag_configure("complet", background="#C8E6C9", foreground="#000000")
        tree_credits.tag_configure("partiel", background="#FFF9C4", foreground="#000000")
        tree_credits.tag_configure("impaye", background="#FFCDD2", foreground="#000000")
        
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
        
        # Charger les crédits du client depuis les deux sources
        try:
            self._render_credit_table(tree_credits, idclient, label_montant_restant)

            # Paiement global uniquement
            def on_paiement_global_click():
                self._open_global_payment_window(idclient, detail_window, tree_credits, label_montant_restant)

            btn_paiement_global.configure(command=on_paiement_global_click)
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur chargement crédits: {err}")
        
        # Fonction pour gérer le double-clic sur les crédits
        def on_credit_double_click(event):
            selected = tree_credits.selection()
            if not selected:
                return
            
            item_id = selected[0]
            try:
                self._open_global_payment_window(idclient, detail_window, tree_credits, label_montant_restant)
            except (ValueError, psycopg2.Error) as err:
                messagebox.showerror("Erreur", f"Erreur ouverture paiement global: {err}")
        
        tree_credits.bind("<Double-1>", on_credit_double_click)

        # --- TABLEAU D'HISTORIQUE DES PAIEMENTS (Bas) ---
        payment_frame = ctk.CTkFrame(right_frame)
        payment_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=(5, 0))
        payment_frame.grid_columnconfigure(0, weight=1)
        payment_frame.grid_columnconfigure(1, weight=0)
        payment_frame.grid_rowconfigure(0, weight=0)
        payment_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(payment_frame, text="Historique des Paiements", 
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))
        
        # Créer le treeview des paiements
        colonnes_paiements = ("ID", "Date Paiement", "Montant Payé", "Observation", "Utilisateur")
        tree_paiements = ttk.Treeview(payment_frame, columns=colonnes_paiements, show='headings', height=8)
        tree_paiements.tag_configure("even", background="#FFFFFF", foreground="#000000")
        tree_paiements.tag_configure("odd", background="#E6EFF8", foreground="#000000")
        
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
        
        # Charger l'historique des paiements
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
            
            # Afficher un message si aucun paiement
            if not paiements:
                empty_label = ctk.CTkLabel(payment_frame, text="Aucun paiement enregistré", 
                                          text_color="gray", font=ctk.CTkFont(size=11))
                empty_label.grid(row=1, column=0, pady=20)
        
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur chargement paiements: {err}")

    def _open_payment_window(self, credit_id, idclient, type_credit, montant_total, montant_paye, solde_restant, tree_credits, parent_window):
        """Ouvre une fenêtre pour enregistrer un paiement partiel."""
        payment_window = ctk.CTkToplevel(parent_window)
        payment_window.title("Enregistrer un Paiement")
        payment_window.geometry("450x350")
        payment_window.grab_set()
        
        # Info du crédit
        info_text = f"""Crédit ID: {credit_id}
Type: {type_credit}

Montant Total: {montant_total:,.2f} Ar
Montant Déjà Payé: {montant_paye:,.2f} Ar
Solde Restant: {solde_restant:,.2f} Ar"""
        
        ctk.CTkLabel(payment_window, text=info_text, justify="left", 
                    font=ctk.CTkFont(family="Segoe UI", size=11)).pack(padx=10, pady=10)
        
        # Entrée du montant à payer
        ctk.CTkLabel(payment_window, text=f"Montant à Payer (max: {solde_restant:,.2f} Ar):",
                    font=ctk.CTkFont(weight="bold")).pack(padx=10, pady=5)
        entry_montant = ctk.CTkEntry(payment_window, width=350)
        entry_montant.pack(padx=10, pady=5)
        
        # Observation
        ctk.CTkLabel(payment_window, text="Observation (optionnel):",
                    font=ctk.CTkFont(weight="bold")).pack(padx=10, pady=(10, 5))
        entry_obs = ctk.CTkEntry(payment_window, width=350)
        entry_obs.pack(padx=10, pady=5)

        # Mode de paiement (récupérer depuis la table tb_modepaiement)
        try:
            self.cursor.execute("SELECT idmode, modedepaiement FROM tb_modepaiement ORDER BY modedepaiement")
            modes = self.cursor.fetchall()
        except Exception:
            modes = []

        mode_names = [m[1] for m in modes] if modes else []
        mode_map = {m[1]: m[0] for m in modes} if modes else {}

        ctk.CTkLabel(payment_window, text="Mode de Paiement:", font=ctk.CTkFont(weight="bold")).pack(padx=10, pady=(10, 5))
        mode_combo = ctk.CTkComboBox(payment_window, values=mode_names, width=350)
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
                
                # Déterminer l'idmode sélectionné (peut être None)
                selected_mode = mode_combo.get() if mode_names else None
                idmode_sel = mode_map.get(selected_mode) if selected_mode else None

                # Enregistrer le paiement dans tb_pmtcredit en respectant le schéma
                date_pmt = datetime.now()
                self.cursor.execute("""
                    INSERT INTO tb_pmtcredit 
                    (datepmt, mtpaye, observation, idtypeoperation, idclient, idmode, idpaiment, iduser)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (date_pmt, montant_paiement, observation, 1, idclient, idmode_sel, None, 1))  # idtypeoperation=1, idpaiment=NULL, iduser=1
                self.conn.commit()
                
                messagebox.showinfo("Succès", f"Paiement de {montant_paiement:,.2f} Ar enregistré avec succès!")
                
                # Générer et imprimer le ticket 80mm
                ticket_filename = os.path.join(os.path.dirname(__file__), '../temp_pdf_preview', f'ticket_payment_{idclient}_{date_pmt.strftime("%Y%m%d%H%M%S")}.txt')
                os.makedirs(os.path.dirname(ticket_filename), exist_ok=True)
                self._generate_ticket_80mm_payment(idclient, montant_paiement, idmode_sel, date_pmt, ticket_filename)
                
                # Demander si l'utilisateur veut imprimer
                result = messagebox.askyesno("Imprimer", "Voulez-vous imprimer le reçu paiement sur X80?")
                if result:
                    self._print_ticket_80mm(ticket_filename)
                
                # Rafraîchir le tableau des crédits
                for item in tree_credits.get_children():
                    tree_credits.delete(item)
                
                # Recharger tous les crédits
                try:
                    # 1. Crédits de vente
                    self.cursor.execute("""
                        SELECT id, 'Crédit Vente' as type, refvente, datepmt, mtpaye, dateecheance
                        FROM tb_pmtfacture
                        WHERE idclient = %s AND idmode = 4 AND deleted = 0
                        ORDER BY datepmt DESC
                    """, (idclient,))
                    credits_vente = self.cursor.fetchall()
                    
                    # 2. Autres créances
                    self.cursor.execute("""
                        SELECT id, 'Créance' as type, numfact, dateregistre, montant, dateecheance
                        FROM tb_autrecreance
                        WHERE idclient = %s
                        ORDER BY dateregistre DESC
                    """, (idclient,))
                    autrecreances = self.cursor.fetchall()
                    
                    tous_credits = credits_vente + autrecreances
                    # Trier les crédits par date DESC (plus récent en premier)
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
                            credit_id_temp,
                            type_credit_temp,
                            date_credit.strftime("%d/%m/%Y %H:%M") if date_credit else "N/A",
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
                     fg_color="#2ecc71").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Annuler", command=payment_window.destroy, 
                     fg_color="#e74c3c").pack(side="left", padx=5)

    def _open_global_payment_window(self, idclient, parent_window, tree_credits, label_montant_restant):
        """Ouvre une fenêtre pour effectuer un paiement global sur tous les crédits."""
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
        
        # Info du crédit global
        info_text = f"""Récapitulatif du Crédit Client (ID: {idclient})

Montant Total des Crédits: {credit_total_initial:,.2f} Ar
Montant Total Déjà Payé: {credit_total_paye:,.2f} Ar
Solde Total Restant: {credit_total_restant:,.2f} Ar"""
        
        ctk.CTkLabel(
            main_frame,
            text=info_text,
            justify="left",
            anchor="w",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        ).grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 10))
        
        # Entrée du montant global à payer
        ctk.CTkLabel(
            main_frame,
            text=f"Montant Global à Payer (max: {credit_total_restant:,.2f} Ar):",
            font=ctk.CTkFont(weight="bold")
        ).grid(row=1, column=0, sticky="w", padx=8, pady=(0, 4))
        entry_montant = ctk.CTkEntry(main_frame)
        entry_montant.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        
        # Observation
        ctk.CTkLabel(
            main_frame,
            text="Observation (optionnel):",
            font=ctk.CTkFont(weight="bold")
        ).grid(row=3, column=0, sticky="w", padx=8, pady=(2, 4))
        entry_obs = ctk.CTkEntry(main_frame)
        entry_obs.grid(row=4, column=0, sticky="ew", padx=8, pady=(0, 8))
        
        # Info sur la distribution automatique
        info_dist = ctk.CTkLabel(
            main_frame,
            text="Le paiement sera distribué automatiquement par ancienneté (factures les plus anciennes d'abord).",
            text_color="#95a5a6",
            justify="left",
            anchor="w",
            wraplength=560,
            font=ctk.CTkFont(family="Segoe UI", size=10, slant="italic")
        )
        info_dist.grid(row=5, column=0, sticky="ew", padx=8, pady=(0, 8))

        # Mode de paiement (récupérer depuis la table tb_modepaiement)
        try:
            self.cursor.execute("SELECT idmode, modedepaiement FROM tb_modepaiement ORDER BY modedepaiement")
            modes = self.cursor.fetchall()
        except Exception:
            modes = []

        mode_names = [m[1] for m in modes] if modes else []
        mode_map = {m[1]: m[0] for m in modes} if modes else {}

        ctk.CTkLabel(main_frame, text="Mode de Paiement:", font=ctk.CTkFont(weight="bold")).grid(
            row=6, column=0, sticky="w", padx=8, pady=(0, 4)
        )
        mode_combo_global = ctk.CTkComboBox(main_frame, values=mode_names)
        if mode_names:
            # choisir "Espèces" par défaut si présent, sinon prendre le premier élément
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
                
                # idmode sélectionné pour cet ensemble de paiements
                selected_mode_global = mode_combo_global.get() if mode_names else None
                idmode_sel_global = mode_map.get(selected_mode_global) if selected_mode_global else None
                observation = f"Paiement crédit client : {self._get_client_name(idclient)}" + (f" (Desc: {observation})" if observation else "")
                
                date_pmt = datetime.now()
                ref_ticket = f"PMTC-{idclient}-{date_pmt.strftime('%Y%m%d%H%M%S')}"
                self.cursor.execute("""
                    INSERT INTO tb_pmtcredit 
                    (datepmt, mtpaye, observation, idtypeoperation, idclient, refvente, idmode, idpaiment, refpmt, id_banque, iduser)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    date_pmt, montant_global, observation, 1, idclient, None, idmode_sel_global, None, ref_ticket,None, 1
                ))
                
                self.conn.commit()
                
                # Message de confirmation
                messagebox.showinfo("Succès", f"Paiement global de {montant_global:,.2f} Ar enregistré avec succès!")

                # Générer un ticket PDF avec le modèle créance (plus lisible et cohérent)
                societe_data = self._get_societe_info()
                societe_tuple = (
                    societe_data.get('name', ''),
                    societe_data.get('addr', ''),
                    societe_data.get('ville', ''),
                    societe_data.get('tel', ''),
                )
                username = self._get_username_by_id(1)
                client_nom = self._get_client_name(idclient)
               
                # Ligne synthétique pour le tableau du ticket
                articles = [("", "Paiement global crédit client", "", 1, float(montant_global), float(montant_global))]

                # Demander si l'utilisateur veut ouvrir le PDF
                result = messagebox.askyesno("Imprimer", "Voulez-vous ouvrir le facture PDF de paiement ?")
                self._generer_ticket_pdf_paiement_credit(
                    societe=societe_tuple,
                    username=username,
                    articles=articles,
                    montant=float(montant_global),
                    mode_nom=selected_mode_global or "Credit",
                    refpmt=ref_ticket,
                    idclient=idclient,
                    client_nom=client_nom,
                    observation=observation,
                    date_paiement=date_pmt,
                    open_after=result
                )
                
                # Rafraîchir le tableau des crédits
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
            btn_frame,
            text="Effectuer le Paiement",
            command=enregistrer_paiement_global,
            fg_color="#2ecc71",
            width=170
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            btn_frame,
            text="Annuler",
            command=payment_window.destroy,
            fg_color="#e74c3c",
            width=130
        ).pack(side="left", padx=5)

    def _formater_nombre(self, nombre):
        """Formate un nombre avec séparateurs de milliers."""
        if isinstance(nombre, (int, float)):
            return f"{nombre:,.2f}".replace(",", " ").replace(".", ",")
        return str(nombre)

    def _fetch_client_credits(self, idclient):
        """Retourne la liste unifiée des crédits d'un client (vente + créance)."""
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
        tous_credits.sort(key=lambda x: x[3], reverse=True)  # affichage DESC
        return tous_credits

    def _compute_credit_status_fifo(self, idclient):
        """
        Calcule les statuts avec paiement global FIFO:
        répartition du total payé du plus ancien vers le plus récent.
        """
        tous_credits_desc = self._fetch_client_credits(idclient)

        self.cursor.execute("""
            SELECT COALESCE(SUM(mtpaye), 0)
            FROM tb_pmtcredit
            WHERE idclient = %s
        """, (idclient,))
        total_paye_global = float(self.cursor.fetchone()[0] or 0)

        total_initial = sum(float(c[4] or 0) for c in tous_credits_desc)
        paid_remaining = total_paye_global

        # Travail FIFO en ASC (plus ancien -> plus récent)
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
        """Rafraîchit le tableau récapitulatif avec la logique FIFO globale."""
        for item in tree_credits.get_children():
            tree_credits.delete(item)

        tous_credits_desc, total_initial, total_paye_global, total_restant, status_map = self._compute_credit_status_fifo(idclient)

        for credit in tous_credits_desc:
            credit_id, type_credit, ref, date_credit, montant_initial, _ = credit
            key = f"{type_credit}_{credit_id}"
            montant_paye_ligne, solde_restant, statut, tag = status_map.get(key, (0.0, float(montant_initial or 0), "✗ Impayé", "impaye"))

            tree_credits.insert('', 'end', iid=key, values=(
                credit_id,
                type_credit,
                date_credit.strftime("%d/%m/%Y %H:%M") if date_credit else "N/A",
                f"{float(montant_initial or 0):,.2f}",
                f"{montant_paye_ligne:,.2f}",
                f"{solde_restant:,.2f}",
                statut
            ), tags=(tag,))

        if label_montant_restant is not None:
            label_montant_restant.configure(text=f"{total_restant:,.2f} Ar")

        return total_initial, total_paye_global, total_restant

    def _get_societe_info(self):
        """Récupère les informations de la société depuis la table tb_infosociete.
        Retourne un dict avec des clés 'name','addr','ville','tel','nif','stat','cif'.
        En cas d'erreur ou si la table est vide, retourne des valeurs par défaut.
        """
        defaults = {
            'name': 'IJEERY',
            'addr': '',
            'ville': '',
            'tel': '',
            'nif': '',
            'stat': '',
            'cif': ''
        }
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
                'name': societe[0] or defaults['name'],
                'addr': societe[1] or defaults['addr'],
                'ville': societe[2] or defaults['ville'],
                'tel': societe[3] or defaults['tel'],
                'nif': societe[4] or defaults['nif'],
                'stat': societe[5] or defaults['stat'],
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
        """Génère un ticket 80mm pour une créance créée."""
        MAX_WIDTH = 40
        
        # Récupérer les infos societé via helper
        soc = self._get_societe_info()
        societe_name = soc.get('name')
        societe_addr = soc.get('addr')
        societe_ville = soc.get('ville')
        societe_tel = soc.get('tel')
        societe_nif = soc.get('nif')
        societe_stat = soc.get('stat')
        societe_cif = soc.get('cif')

        # Récupérer infos client (séparément pour gérer les erreurs proprement)
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

        def center(text):
            return text.center(MAX_WIDTH)

        def line():
            return "-" * MAX_WIDTH
        
        def wrap_text(text, max_width=MAX_WIDTH):
            """Divise le texte sur plusieurs lignes si trop long"""
            lines = []
            for line_text in str(text).split("\n"):
                if len(line_text) <= max_width:
                    lines.append(line_text)
                else:
                    import textwrap
                    wrapped = textwrap.wrap(line_text, max_width)
                    lines.extend(wrapped)
            return lines

        content = []
        
        # --- EN-TÊTE SOCIÉTÉ (complète) ---
        content.append(line())
        content.append(center(societe_name.upper()))
        
        if societe_addr:
            content.extend(wrap_text(center(societe_addr)))
        if societe_ville:
            content.append(center(societe_ville))
        
        # Infos légales: NIF, STAT, CIF
        if societe_nif:
            content.append(center(f"NIF: {societe_nif}"))
        if societe_stat:
            content.append(center(f"STAT: {societe_stat}"))
        if societe_cif:
            content.append(center(f"CIF: {societe_cif}"))
        
        if societe_tel:
            content.append(center(f"Tél: {societe_tel}"))
        
        content.append(line())
        
        # --- TYPE DE DOCUMENT ---
        content.append(center("ENREGISTREMENT CRÉANCE"))
        content.append(line())
        
        # --- INFOS CRÉANCE ---
        content.append(f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        content.append(f"Créance N°: {num_fact}")
        content.append(f"Client: {client_name}")
        content.append(line())
        
        # --- MONTANT ---
        content.append(center("MONTANT"))
        montant_str = self._formater_nombre(montant)
        content.append(center(f"{montant_str} Ar"))
        content.append(line())
        
        # --- PIED DE PAGE ---
        content.append(center("Créance Enregistrée"))
        content.append(center(datetime.now().strftime("%d/%m/%Y")))
        content.append("\n")
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur génération ticket créance: {e}")

    def _get_username_by_id(self, iduser=1):
        """Récupère username depuis tb_users."""
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
        """Retourne l'ID de l'utilisateur connecté avec fallback sécurisé."""
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
        """Récupère le nom client par idclient."""
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
        """Génère un ticket PDF (modèle page_pmtcredit) pour validation d'ajout de créance."""
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

            c.setFont("Helvetica", 8)
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
        """Génère un document A5 paysage pour validation de paiement de crédit client."""
        try:
            client_adresse = "-"
            client_contact = "-"
            try:
                self.cursor.execute(
                    "SELECT adressecli, contactcli FROM tb_client WHERE idclient = %s",
                    (idclient,)
                )
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
            path = os.path.join(
                temp_dir,
                f"Paiement_Credit_{refpmt}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )

            page_width, _ = landscape(A5)
            margin = 5 * mm
            usable_width = page_width - 2 * margin

            doc = SimpleDocTemplate(
                path,
                pagesize=landscape(A5),
                rightMargin=margin,
                leftMargin=margin,
                topMargin=margin,
                bottomMargin=margin,
            )

            elements = []
            styles = getSampleStyleSheet()
            color_header = colors.HexColor("#034787")

            verse_title = Paragraph(
                "Ankino amin'ny Jehovah ny asanao dia ho lavorary izay kasainao. Ohabolana 16:3",
                ParagraphStyle(
                    "MainTitleCredit",
                    parent=styles["Normal"],
                    fontSize=10,
                    textColor=colors.black,
                    alignment=TA_CENTER,
                    fontName="Helvetica-Bold",
                    spaceAfter=3,
                ),
            )
            verse_table = Table([[verse_title]], colWidths=[usable_width])
            verse_table.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 1, colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
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
                f"<b>{nom_soc}</b><br/>"
                f"Adresse : {adr_soc}<br/>"
                f"Ville : {ville_soc}<br/>"
                f"Contact : {contact_soc}<br/>",
                ParagraphStyle("CompanyCredit", parent=styles["Normal"], fontSize=9, alignment=TA_LEFT, leading=12),
            )
            company_table = Table([[company_details]], colWidths=[company_width - 2 * mm], rowHeights=[header_height])
            company_table.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 1, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))

            operation_title = Paragraph(
                "PAIEMENT DE CREDIT",
                ParagraphStyle(
                    "OpCreditTitle",
                    parent=styles["Normal"],
                    fontSize=14,
                    fontName="Helvetica-Bold",
                    alignment=TA_CENTER,
                    textColor=color_header,
                ),
            )
            operation_info = Paragraph(
                f"<b>Reference :</b> {refpmt}<br/>"
                f"<b>Date et heure :</b> {date_paiement.strftime('%d/%m/%Y %H:%M')}<br/>"
                f"<b>Mode de paiement :</b> {mode_nom}<br/>"
                f"<b>Operateur :</b> {username}",
                ParagraphStyle("OpCreditInfo", parent=styles["Normal"], fontSize=9, alignment=TA_LEFT, leading=12),
            )
            operation_table = Table([[operation_title, operation_info]], colWidths=[title_width, info_width], rowHeights=[header_height])
            operation_table.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 1, colors.black),
                ("ALIGN", (0, 0), (0, 0), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))

            header_table = Table([[company_table, operation_table]], colWidths=[company_width, right_width])
            header_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (0, 0), 8),
                ("LEFTPADDING", (1, 0), (1, 0), 8),
            ]))
            elements.append(header_table)
            elements.append(Spacer(1, 3 * mm))

            infos_credit = Paragraph(
                "<b><u>Infos Paiement Credit</u></b><br/>",
                ParagraphStyle("InfoCreditLine", parent=styles["Normal"], fontSize=9, alignment=TA_CENTER, leading=11),
            )
            elements.append(infos_credit)
            elements.append(Spacer(1, 2 * mm))

            columns = ["Reference", "Nom Client", "Montant"]
            row_data = [[refpmt, client_nom, self._formater_nombre(montant) + " Ar"]]

            # Calculer le crédit restant du client après déduction du montant payé
            try:
                _, _, _, total_restant, _ = self._compute_credit_status_fifo(idclient)
            except Exception:
                total_restant = 0

            # Ligne footer qui fusionne les deux premières colonnes et affiche le reste
            footer_row = ["Reste de Crédit", "", self._formater_nombre(total_restant) + " Ar"]

            table_width = usable_width * 0.95
            col_widths = [table_width * 0.25, table_width * 0.43, table_width * 0.32]
            table_data = [columns] + row_data + [footer_row]

            credit_table = Table(table_data, colWidths=col_widths, repeatRows=1)
            style_list = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E8E8")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("ALIGN", (0, 1), (1, -2), "LEFT"),
                ("ALIGN", (2, 1), (2, -2), "CENTER"),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("BOX", (0, 0), (-1, -1), 1, colors.black),
                ("LINEBEFORE", (1, 0), (1, -1), 1, color_header),
                ("LINEBEFORE", (2, 0), (2, -1), 1, color_header),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]

            # Styles pour la ligne footer (dernière ligne)
            last_row = len(table_data) - 1
            style_list.extend([
                ("SPAN", (0, last_row), (1, last_row)),
                ("ALIGN", (0, last_row), (1, last_row), "RIGHT"),
                ("ALIGN", (2, last_row), (2, last_row), "CENTER"),
                ("FONTNAME", (0, last_row), (2, last_row), "Helvetica-Bold"),
                ("FONTSIZE", (0, last_row), (2, last_row), 10),
                ("BACKGROUND", (0, last_row), (2, last_row), colors.HexColor("#F5F5F5")),
                # Ligne supérieure (top border) pour séparer le footer de la ligne précédente
                ("LINEABOVE", (0, last_row), (2, last_row), 1, color_header),
            ])

            credit_table.setStyle(TableStyle(style_list))
            elements.append(credit_table)
            elements.append(Spacer(1, 3 * mm))

            coord_client = Paragraph(
                f"<br/>&nbsp;&nbsp;&nbsp;<b><u>Description :</u></b> {observation}",
                ParagraphStyle("CoordClient", parent=styles["Normal"], fontSize=9, alignment=TA_LEFT, leading=11),
            )
            elements.append(coord_client)
            elements.append(Spacer(1, 1.5 * mm))

            coord_client = Paragraph(
                f"<br/>&nbsp;&nbsp;&nbsp;<b><u>Coordonnees client :</u></b> {client_adresse} ; Tel : {client_contact}",
                ParagraphStyle("CoordClient", parent=styles["Normal"], fontSize=9, alignment=TA_LEFT, leading=11),
            )
            elements.append(coord_client)
            elements.append(Spacer(1, 1.5 * mm))

           

            sig_left = Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;<u>Le Responsable</u>", ParagraphStyle("SigRespo", parent=styles["Normal"], fontSize=9, alignment=TA_LEFT))
            sig_right = Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;<u>Le Client</u>", ParagraphStyle("SigClient", parent=styles["Normal"], fontSize=9, alignment=TA_LEFT))
            sig_table = Table([[sig_left, "", sig_right]], colWidths=[usable_width * 0.35, usable_width * 0.30, usable_width * 0.35])
            sig_table.setStyle(TableStyle([
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
                ("ALIGN", (2, 0), (2, 0), "RIGHT"),
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
        """Génère un ticket 80mm pour un paiement de crédit."""
        MAX_WIDTH = 40
        
        # Récupérer les infos societe via helper
        soc = self._get_societe_info()
        societe_name = soc.get('name')
        societe_addr = soc.get('addr')
        societe_ville = soc.get('ville')
        societe_tel = soc.get('tel')
        societe_nif = soc.get('nif')
        societe_stat = soc.get('stat')
        societe_cif = soc.get('cif')

        # Récupérer infos client et mode de paiement séparément
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
            # Note: column name may be 'modedepaiement' in some schemas
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

        def center(text):
            return text.center(MAX_WIDTH)

        def line():
            return "-" * MAX_WIDTH
        
        def wrap_text(text, max_width=MAX_WIDTH):
            """Divise le texte sur plusieurs lignes si trop long"""
            lines = []
            for line_text in str(text).split("\n"):
                if len(line_text) <= max_width:
                    lines.append(line_text)
                else:
                    wrapped = textwrap.wrap(line_text, max_width)
                    lines.extend(wrapped)
            return lines

        content = []
        
        # --- EN-TÊTE SOCIÉTÉ (complète) ---
        content.append(line())
        content.append(center(societe_name.upper()))
        
        if societe_addr:
            content.extend(wrap_text(center(societe_addr)))
        if societe_ville:
            content.append(center(societe_ville))
        
        # Infos légales: NIF, STAT, CIF
        if societe_nif:
            content.append(center(f"NIF: {societe_nif}"))
        if societe_stat:
            content.append(center(f"STAT: {societe_stat}"))
        if societe_cif:
            content.append(center(f"CIF: {societe_cif}"))
        
        if societe_tel:
            content.append(center(f"Tél: {societe_tel}"))
        
        content.append(line())
        
        # --- TYPE DE DOCUMENT ---
        content.append(center("REÇU PAIEMENT CRÉDIT CLIENT"))
        content.append(line())
        
        # --- INFOS PAIEMENT ---
        content.append(f"Date: {date_pmt.strftime('%d/%m/%Y %H:%M')}")
        content.append(f"Client: {client_name}")
        content.append(f"Mode: {mode_name}")
        content.append(line())
        
        # --- MONTANT ---
        content.append(center("MONTANT PAYÉ"))
        montant_str = self._formater_nombre(montant)
        content.append(center(f"{montant_str} Ar"))
        content.append(line())
        
        # --- PIED DE PAGE ---
        content.append(center("Paiement Reçu"))
        content.append(center(datetime.now().strftime("%d/%m/%Y %H:%M")))
        content.append("\n")
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur génération ticket paiement: {e}")

    def _print_ticket_80mm(self, filename):
        """Imprime un fichier ticket 80mm sur l'imprimante par défaut."""
        try:
            if os.path.exists(filename):
                # Windows: utilise notepad pour imprimer
                if os.name == 'nt':
                    subprocess.Popen(['notepad.exe', '/p', filename])
                else:
                    # Linux/macOS
                    subprocess.Popen(['lpr', filename])
        except Exception as e:
            messagebox.showwarning("Impression", f"Ne peut pas imprimer automatiquement. Fichier: {filename}")

    def _open_add_creance_window(self, idclient, parent_window):
        """Ouvre une fenêtre pour ajouter une créance manuelle."""
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
        
        # Titre
        ctk.CTkLabel(
            main_frame,
            text="Enregistrer une Créance Manuelle",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 10))
        
        # Numéro de facture
        ctk.CTkLabel(main_frame, text="Référence :", font=ctk.CTkFont(weight="bold")).grid(
            row=1, column=0, sticky="w", padx=8, pady=(2, 4)
        )
        entry_numfact = ctk.CTkEntry(main_frame, placeholder_text="Entrez une référence (ex: FACT-001)")
        entry_numfact.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        
        # Montant
        ctk.CTkLabel(main_frame, text="Montant (Ar) :", font=ctk.CTkFont(weight="bold")).grid(
            row=3, column=0, sticky="w", padx=8, pady=(2, 4)
        )
        entry_montant = ctk.CTkEntry(main_frame, placeholder_text="Ex: 50000")
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
                
                # Resynchroniser la sequence (corrige duplicate key sur id)
                self.cursor.execute("""
                    SELECT setval(
                        pg_get_serial_sequence('tb_autrecreance', 'id'),
                        COALESCE((SELECT MAX(id) FROM tb_autrecreance), 0) + 1,
                        false
                    )
                """)

                # Insérer la créance dans tb_autrecreance
                self.cursor.execute("""
                    INSERT INTO tb_autrecreance (idclient, dateregistre, numfact, montant)
                    VALUES (%s, %s, %s, %s)
                """, (idclient, datetime.now(), num_fact, montant))
                self.conn.commit()
                
                messagebox.showinfo("Succès", f"Créance de {montant:,.2f} Ar enregistrée avec succès!")
                
                # Générer le ticket PDF créance avec le modèle de page_pmtcredit
                username = self._get_username_by_id(1)
                societe_data = self._get_societe_info()
                societe_tuple = (
                    societe_data.get('name', ''),
                    societe_data.get('addr', ''),
                    societe_data.get('ville', ''),
                    societe_data.get('tel', ''),
                )
                articles = [("", "Creance manuelle", "", 1, float(montant), float(montant))]
                result = messagebox.askyesno("Imprimer", "Voulez-vous ouvrir le ticket PDF de créance ?")
                self._generer_ticket_pdf_creance(
                    societe=societe_tuple,
                    username=username,
                    articles=articles,
                    montant=float(montant),
                    mode_nom="Credit",
                    refpmt=num_fact,
                    client_nom=self._get_client_name(idclient),
                    montant_total=float(montant),
                    open_after=result
                )
                
                creance_window.destroy()
                
                # Rafraîchir la fenêtre de détails
                parent_window.destroy()
                self.open_client_credit_details(idclient)
            
            except ValueError:
                messagebox.showerror("Erreur", "Veuillez entrer un montant valide (nombre).")
            except psycopg2.Error as err:
                self.conn.rollback()
                messagebox.showerror("Erreur", f"Erreur enregistrement créance: {err}")
        
        # Boutons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.grid(row=5, column=0, sticky="e", padx=8, pady=(10, 6))
        
        ctk.CTkButton(btn_frame, text="Enregistrer", command=enregistrer_creance, 
                     fg_color="#27ae60").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Annuler", command=creance_window.destroy, 
                     fg_color="#e74c3c").pack(side="left", padx=5)

if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("1000x600")
    PageClient(app).pack(fill="both", expand=True)
    app.mainloop()
