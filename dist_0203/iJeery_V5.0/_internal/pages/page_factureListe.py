import customtkinter as ctk
import psycopg2
from tkinter import messagebox, ttk
import json
import pandas as pd
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from tkcalendar import DateEntry
from resource_utils import get_config_path, safe_file_read


# IMPORTER LA CLASSE DE PAIEMENT
try:
    from pages.page_pmtFacture import PagePmtFacture
except ImportError:
    class PagePmtFacture:
        def __init__(self, master, paiement_data: Dict[str, str]):
            messagebox.showerror("Erreur", "Le fichier 'page_pmtFacture.py' est manquant ou contient une erreur. Impossible d'ouvrir la fenêtre de paiement.")

class PageFactureListe(ctk.CTkFrame):
    """
    Fenêtre CTK affichant les crédit clients.
    Permet la recherche, l'affichage tabulaire avec totaux,
    la coloration des dettes, l'exportation Excel et le paiement (double-clic).
    """
    def __init__(self, master):
        super().__init__(master)
        self.grid(row=0, column=0, sticky="nsew")
        
        # Configuration de la grille principale de la frame
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.data_df = pd.DataFrame() 
        
        # Variables pour mémoriser le filtre actif
        self.filtre_actif = False
        self.date_debut_filtre = None
        self.date_fin_filtre = None
        
        # --- 1. Filtre par Date ---
        self.date_frame = ctk.CTkFrame(self)
        self.date_frame.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="ew")
        self.date_frame.grid_columnconfigure(2, weight=1)
        
        # Label Date Début
        self.label_date_debut = ctk.CTkLabel(self.date_frame, text="Date Début:", font=ctk.CTkFont(family="Segoe UI", weight="bold"))
        self.label_date_debut.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        # DateEntry Date Début
        self.date_debut = DateEntry(
            self.date_frame,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='dd/mm/yyyy',
            locale='fr_FR'
        )
        self.date_debut.set_date(datetime.now())
        self.date_debut.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        # Label Date Fin
        self.label_date_fin = ctk.CTkLabel(self.date_frame, text="Date Fin:", font=ctk.CTkFont(family="Segoe UI", weight="bold"))
        self.label_date_fin.grid(row=0, column=2, padx=10, pady=10, sticky="w")
        
        # DateEntry Date Fin
        self.date_fin = DateEntry(
            self.date_frame,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='dd/mm/yyyy',
            locale='fr_FR'
        )
        self.date_fin.set_date(datetime.now())
        self.date_fin.grid(row=0, column=3, padx=10, pady=10, sticky="w")
        
        # Bouton Filtrer par Date
        self.btn_filtrer_date = ctk.CTkButton(
            self.date_frame,
            text="Filtrer",
            command=self.filter_by_date,
            fg_color="#1f538d",
            hover_color="#14375e"
        )
        self.btn_filtrer_date.grid(row=0, column=4, padx=10, pady=10)
        
        # Bouton Réinitialiser
        self.btn_reset_date = ctk.CTkButton(
            self.date_frame,
            text="Réinitialiser",
            command=self.reset_date_filter,
            fg_color="#666666",
            hover_color="#444444"
        )
        self.btn_reset_date.grid(row=0, column=5, padx=10, pady=10)
        
        # --- 2. Interface de Recherche et Export ---
        self.search_frame = ctk.CTkFrame(self)
        self.search_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        self.search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            self.search_frame, 
            placeholder_text="Rechercher par Nom du Client...",
            width=400
        )
        self.search_entry.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.search_entry.bind("<Return>", self.search_credit)
        
        self.search_button = ctk.CTkButton(
            self.search_frame, 
            text="Rechercher", 
            command=lambda: self.search_credit(None)
        )
        self.search_button.grid(row=0, column=1, padx=(0, 10), pady=10)

        self.export_button = ctk.CTkButton(
            self.search_frame, 
            text="Export vers Excel", 
            command=self.export_to_excel,
            fg_color="green",
            hover_color="#006400"
        )
        self.export_button.grid(row=0, column=2, padx=(0, 10), pady=10)

        # --- 2. Tableau d'Affichage (ttk.Treeview) ---
        self.tree_frame = ctk.CTkFrame(self)
        self.tree_frame.grid(row=1, column=0, padx=20, pady=5, sticky="nsew")
        self.tree_frame.grid_columnconfigure(0, weight=1)
        self.tree_frame.grid_rowconfigure(0, weight=1)
        
        # Configuration du style pour le Treeview
        style = ttk.Style()
        style.theme_use("default") 

        current_mode = ctk.get_appearance_mode().lower()
        
        if current_mode == "dark":
            bg_color = "#2A2D2E"
            fg_color = "white"
            header_bg = "#383838"
            selected_bg = "#4A4D4E"
        else:
            bg_color = "#EBEBEB"
            fg_color = "black"
            header_bg = "#CFCFCF"
            selected_bg = "#A9A9A9"

        style.configure("Treeview", 
                        background="#FFFFFF",
                        foreground="#000000",
                        rowheight=22,
                        fieldbackground="#FFFFFF",
                        borderwidth=0,
                        font=('Segoe UI', 8))
                        
        style.configure("Treeview.Heading",
                        background="#E8E8E8",
                        foreground=fg_color,
                        font=('Arial', 10, 'bold'))
        
        style.map('Treeview', 
                  background=[('selected', selected_bg)],
                  foreground=[('selected', fg_color)])

        columns = ("N° Facture", "Date", "Description", "Montant Total", "Client", "User", "Qté Lignes")
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings") 

        # Définir le tag pour la coloration orange des dettes
        self.tree.tag_configure('impaye', background='#FFBE76', foreground='black')
        
        # Tags pour les couleurs alternées des lignes
        self.tree.tag_configure('row_white', background='#FFFFFF', foreground='black')
        self.tree.tag_configure('row_light_gray', background='#F2D9EA', foreground='black') 
        
        # --- LIAISON DU DOUBLE-CLIC POUR LE PAIEMENT ---
        self.tree.bind("<Double-1>", self.on_double_click)
        
        # Définition des entêtes
        self.tree.heading("N° Facture", text="N° Facture")
        self.tree.heading("Date", text="Date")
        self.tree.heading("Description", text="Description")
        self.tree.heading("Montant Total", text="Montant Total")
        self.tree.heading("Client", text="Client")
        self.tree.heading("User", text="User")
        self.tree.heading("Qté Lignes", text="Qté Lignes")

        # Configuration des largeurs 
        self.tree.column("N° Facture", width=120, anchor=ctk.W)
        self.tree.column("Date", width=150, anchor=ctk.CENTER)
        self.tree.column("Description", width=150, anchor=ctk.CENTER)
        self.tree.column("Montant Total", width=100, anchor=ctk.CENTER)
        self.tree.column("Client", width=150, anchor=ctk.E)
        self.tree.column("User", width=100, anchor=ctk.E)
        self.tree.column("Qté Lignes", width=50, anchor=ctk.E)

        # Scrollbar verticale
        vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")

        # --- 4. Section des Totaux ---
        self.total_frame = ctk.CTkFrame(self)
        self.total_frame.grid(row=3, column=0, padx=20, pady=(5, 20), sticky="ew") 
        self.total_frame.grid_columnconfigure(0, weight=1)
        self.total_frame.grid_columnconfigure(1, weight=1)
        self.total_frame.grid_columnconfigure(2, weight=1)
        
        # Labels pour les totaux
        self.total_cmd_label = ctk.CTkLabel(self.total_frame, text="Total Facture: 0,00", font=ctk.CTkFont(family="Segoe UI", weight="bold"))
        self.total_cmd_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.total_paye_label = ctk.CTkLabel(self.total_frame, text="Total Payé: 0,00", font=ctk.CTkFont(family="Segoe UI", weight="bold"))
        self.total_paye_label.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        self.total_solde_label = ctk.CTkLabel(self.total_frame, text="Total Solde: 0,00", font=ctk.CTkFont(family="Segoe UI", weight="bold"), text_color="orange")
        self.total_solde_label.grid(row=0, column=2, padx=10, pady=10, sticky="w")
        
        # Label pour le nombre de factures
        self.count_label = ctk.CTkLabel(self.total_frame, text="Nombre de factures: 0", font=ctk.CTkFont(family="Segoe UI", weight="bold"))
        self.count_label.grid(row=0, column=3, padx=10, pady=10, sticky="e")
        
        self.load_all_credit()

    # --- Méthode de formatage ---
    def format_currency(self, value):
        """
        Formate un float en chaîne de caractères avec séparateur de milliers 
        (espace) et virgule décimale (style français).
        Ex: 1234567.89 -> 1 234 567,89
        """
        try:
            sign = "-" if value < 0 else ""
            absolute_value = abs(value)
            
            integer_part, decimal_part = f"{round(absolute_value, 2):.2f}".split('.')
            
            formatted_integer = ""
            for i, digit in enumerate(reversed(integer_part)):
                if i > 0 and i % 3 == 0:
                    formatted_integer = ' ' + formatted_integer
                formatted_integer = digit + formatted_integer
                
            return f"{sign}{formatted_integer},{decimal_part}"
            
        except Exception:
            return "0,00"

    # --- Méthode de Paiement (Double-Clic) ---
    def on_double_click(self, event):
        """
        Gère l'événement de double-clic pour ouvrir la fenêtre de paiement.
        """
        if PagePmtFacture is None:
            messagebox.showerror("Erreur", "La page de paiement PagePmtFacture n'a pas pu être chargée.")
            return

        selected_item = self.tree.focus()
        if not selected_item:
            return

        item_index = self.tree.index(selected_item)
        
        if item_index >= len(self.data_df) or self.data_df.empty:
            messagebox.showerror("Erreur", "Ligne de données non trouvée dans le DataFrame.")
            return

        row_data = self.data_df.iloc[item_index]
        
        solde = row_data['Solde'] 
        statut = row_data.get('Statut', 'EN_ATTENTE')

        # N'autoriser le paiement que si la facture est en attente
        if statut != 'EN_ATTENTE':
            messagebox.showinfo("Information", f"Cette facture n'est pas en attente (statut: {statut}).")
            return

        if solde <= 0.01:
            messagebox.showinfo("Information", "Cette Facture est déjà entièrement payée (Solde nul).")
            return

        paiement_data = {
            "refvente": row_data["N° Facture"],          
            "date": row_data["Date"],
            "description": row_data["Description"], 
            "client": row_data["Client"],     
            "montant_total": f"{solde:.2f}".replace('.', ','),
            "idcli": row_data["ID Client"]
        }
        
        # 🔍 DEBUG: Afficher les montants
        print(f"\n💰 CAISSE - Facture {paiement_data['refvente']}")
        print(f"  Montant Total Initial (tb_vente.totmtvente): {row_data['Montant Total']:.0f} Ar")
        print(f"  Montant Payé: {row_data['Total Payé']:.0f} Ar")
        print(f"  Solde (à payer): {solde:.0f} Ar")
        print(f"  → Valeur affichée en caisse: {paiement_data['montant_total']} Ar\n")
        
        if paiement_data['idcli'] is None:
             messagebox.showerror("Erreur", "ID du Client manquant. Impossible d'ouvrir la page de paiement.")
             return

        # Décolorer immédiatement la ligne pour éviter les doubles clics accidentels
        self.tree.item(selected_item, tags=())
        
        PagePmtFacture(self.master, paiement_data)
        
        # Recharger les données en respectant le filtre actif
        self.master.after(200, self.reload_data)
    
    def reload_data(self):
        """Recharge les données en respectant le filtre actif"""
        if self.filtre_actif and self.date_debut_filtre and self.date_fin_filtre:
            # Réappliquer le filtre de dates
            self.filter_by_date()
        else:
            # Charger les données du jour
            self.load_all_credit()

    # --- Connexion DB ---
    def connect_db(self):
        try:
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
        except FileNotFoundError:
            messagebox.showerror("Erreur de configuration", "Fichier 'config.json' non trouvé.")
            return None
        except psycopg2.Error as e:
            messagebox.showerror("Erreur de Base de Données", f"Impossible de se connecter : {e}")
            return None
    
    # --- Filtre par Date ---
    def filter_by_date(self):
        """Filtre les factures par intervalle de dates"""
        date_debut = self.date_debut.get_date()
        date_fin = self.date_fin.get_date()
        
        # Vérification que date début <= date fin
        if date_debut > date_fin:
            messagebox.showerror("Erreur", "La date de début doit être antérieure ou égale à la date de fin.")
            return
        
        # Mémoriser le filtre actif
        self.filtre_actif = True
        self.date_debut_filtre = date_debut
        self.date_fin_filtre = date_fin
        
        for item in self.tree.get_children():
            self.tree.delete(item)

        conn = self.connect_db()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            query = """
                SELECT 
                    v.refvente,
                    v.dateregistre,
                    v.description,
                    COALESCE(v.totmtvente, 0) AS montant_total,
                    v.statut,
                    COALESCE((
                        SELECT SUM(p.mtpaye) 
                        FROM tb_pmtfacture p 
                        WHERE p.refvente = v.refvente
                    ), 0) AS total_paye,
                    c.nomcli AS client_name,
                    c.idclient,
                    CONCAT(u.prenomuser, ' ', u.nomuser) AS utilisateur,
                    (SELECT COUNT(*) FROM tb_ventedetail vd WHERE vd.idvente = v.id) AS nb_lignes,
                    (SELECT m.designationmag FROM tb_ventedetail vd 
                     INNER JOIN tb_magasin m ON vd.idmag = m.idmag 
                     WHERE vd.idvente = v.id LIMIT 1) AS premier_magasin
                FROM tb_vente v
                LEFT JOIN tb_users u ON v.iduser = u.iduser
                LEFT JOIN tb_client c ON v.idclient = c.idclient
                WHERE v.deleted = 0
                AND v.dateregistre::DATE BETWEEN %s AND %s
                AND v.statut IN ('EN_ATTENTE', 'VALIDEE')
                ORDER BY v.dateregistre DESC, v.refvente DESC
            """
            
            cursor.execute(query, (date_debut, date_fin))
            resultats = cursor.fetchall()
            
            data_list = []
            total_factures = 0
            total_paye = 0
            total_solde = 0
            count = 0
            
            for row in resultats:
                refvente = row[0]
                date = row[1].strftime("%d/%m/%Y %H:%M:%S") if row[1] else ""
                description = row[2] or ""
                montant_total = float(row[3] or 0)
                statut = row[4] or 'EN_ATTENTE'
                paye = float(row[5] or 0)
                client = row[6] or ""
                idclient = row[7]
                user = row[8] or ""
                nb_lignes = row[9] or 0
                premier_magasin = row[10] or ""
                
                # Construire la description avec le dépôt
                if premier_magasin:
                    description_avec_depot = f"{premier_magasin}"
                    if description and description.strip() and premier_magasin not in description:
                        description_clean = description.strip().strip('-').strip()
                        if description_clean:
                            description_avec_depot = f"{description_avec_depot} - {description_clean}"
                    description = description_avec_depot
                
                solde = montant_total - paye
                
                total_factures += montant_total
                total_paye += paye
                total_solde += solde
                count += 1
                
                # Déterminer les tags : couleur alternée + impayé si applicable
                tags = [('row_white' if count % 2 == 1 else 'row_light_gray')]
                if solde > 0.01:
                    tags.append('impaye')
                
                self.tree.insert('', 'end', values=(
                    refvente,
                    date,
                    description,
                    self.format_currency(montant_total),
                    client,
                    user,
                    nb_lignes
                ), tags=tuple(tags))
                
                data_list.append({
                    "N° Facture": refvente,
                    "Date": date,
                    "Description": description,
                    "Montant Total": montant_total,
                    "Total Payé": paye,
                    "Solde": solde,
                    "Client": client,
                    "ID Client": idclient,
                    "User": user,
                    "Qté Lignes": nb_lignes,
                    "Statut": statut
                })
            
            self.data_df = pd.DataFrame(data_list)
            
            self.total_cmd_label.configure(text=f"Total Facture: Ar {self.format_currency(total_factures)}")
            self.total_paye_label.configure(text=f"Total Payé: {self.format_currency(total_paye)}")
            self.total_solde_label.configure(text=f"Total Solde: Ar {self.format_currency(total_solde)}")
            self.count_label.configure(text=f"Nombre de factures: {count}")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du filtrage: {str(e)}")
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def reset_date_filter(self):
        """Réinitialise le filtre de dates à aujourd'hui et recharge les données du jour"""
        self.filtre_actif = False
        self.date_debut_filtre = None
        self.date_fin_filtre = None
        
        self.date_debut.set_date(datetime.now())
        self.date_fin.set_date(datetime.now())
        self.load_all_credit()
            
    # --- Chargement des données ---
    def load_all_credit(self):
        """Charge tous les crédits clients du jour avec filtres par statut"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        conn = self.connect_db()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            query = """
                SELECT 
                    v.refvente,
                    v.dateregistre,
                    v.description,
                    COALESCE(v.totmtvente, 0) AS montant_total,
                    v.statut,
                    COALESCE((
                        SELECT SUM(p.mtpaye) 
                        FROM tb_pmtfacture p 
                        WHERE p.refvente = v.refvente
                    ), 0) AS total_paye,
                    c.nomcli AS client_name,
                    c.idclient,
                    CONCAT(u.prenomuser, ' ', u.nomuser) AS utilisateur,
                    (SELECT COUNT(*) FROM tb_ventedetail vd WHERE vd.idvente = v.id) AS nb_lignes,
                    (SELECT m.designationmag FROM tb_ventedetail vd 
                     INNER JOIN tb_magasin m ON vd.idmag = m.idmag 
                     WHERE vd.idvente = v.id LIMIT 1) AS premier_magasin
                FROM tb_vente v
                LEFT JOIN tb_users u ON v.iduser = u.iduser
                LEFT JOIN tb_client c ON v.idclient = c.idclient
                WHERE v.deleted = 0
                AND v.dateregistre::DATE = CURRENT_DATE
                AND v.statut IN ('EN_ATTENTE', 'VALIDEE')
                ORDER BY v.dateregistre DESC, v.refvente DESC
            """
            
            cursor.execute(query)
            resultats = cursor.fetchall()
            
            data_list = []
            total_factures = 0
            total_paye = 0
            total_solde = 0
            count = 0
            
            for row in resultats:
                refvente = row[0]
                date = row[1].strftime("%d/%m/%Y %H:%M:%S") if row[1] else ""
                description = row[2] or ""
                montant_total = float(row[3] or 0)
                statut = row[4] or 'EN_ATTENTE'
                paye = float(row[5] or 0)
                client = row[6] or ""
                idclient = row[7]
                user = row[8] or ""
                nb_lignes = row[9] or 0
                premier_magasin = row[10] or ""
                
                # Construire la description avec le dépôt
                if premier_magasin:
                    description_avec_depot = f"Magasin {premier_magasin}"
                    if description and description.strip() and premier_magasin not in description:
                        description_clean = description.strip().strip('-').strip()
                        if description_clean:
                            description_avec_depot = f"{description_avec_depot} - {description_clean}"
                    description = description_avec_depot
                
                solde = montant_total - paye
                
                total_factures += montant_total
                total_paye += paye
                total_solde += solde
                count += 1
                
                # Déterminer les tags : couleur alternée + impayé si applicable
                tags = [('row_white' if count % 2 == 1 else 'row_light_gray')]
                if solde > 0.01:
                    tags.append('impaye')
                
                self.tree.insert('', 'end', values=(
                    refvente,
                    date,
                    description,
                    self.format_currency(montant_total),
                    client,
                    user,
                    nb_lignes
                ), tags=tuple(tags))
                
                data_list.append({
                    "N° Facture": refvente,
                    "Date": date,
                    "Description": description,
                    "Montant Total": montant_total,
                    "Statut": statut,
                    "Total Payé": paye,
                    "Solde": solde,
                    "Client": client,
                    "ID Client": idclient,
                    "User": user,
                    "Qté Lignes": nb_lignes
                })
            
            self.data_df = pd.DataFrame(data_list)
            
            self.total_cmd_label.configure(text=f"Total Facture: {self.format_currency(total_factures)}")
            self.total_paye_label.configure(text=f"Total Payé: {self.format_currency(total_paye)}")
            self.total_solde_label.configure(text=f"Total Solde: {self.format_currency(total_solde)}")
            self.count_label.configure(text=f"Nombre de factures: {count}")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement: {str(e)}")
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if conn:
                conn.close()

    # --- Recherche ---
    def search_credit(self, event=None):
        """Recherche des factures par nom de client"""
        filtre = self.search_entry.get().strip()
        
        for item in self.tree.get_children():
            self.tree.delete(item)

        conn = self.connect_db()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            query = """
                SELECT 
                    v.refvente,
                    v.dateregistre,
                    v.description,
                    COALESCE(v.totmtvente, 0) AS montant_total,
                    v.statut,
                    COALESCE((
                        SELECT SUM(p.mtpaye) 
                        FROM tb_pmtfacture p 
                        WHERE p.refvente = v.refvente
                    ), 0) AS total_paye,
                    c.nomcli AS client_name,
                    c.idclient,
                    CONCAT(u.prenomuser, ' ', u.nomuser) AS utilisateur,
                    (SELECT COUNT(*) FROM tb_ventedetail vd WHERE vd.idvente = v.id) AS nb_lignes
                FROM tb_vente v
                LEFT JOIN tb_users u ON v.iduser = u.iduser
                LEFT JOIN tb_client c ON v.idclient = c.idclient
                WHERE v.deleted = 0
                AND v.statut IN ('EN_ATTENTE', 'VALIDEE')
            """
            
            params = []
            if filtre:
                query += """
                    AND (LOWER(v.refvente) LIKE LOWER(%s) 
                        OR LOWER(v.description) LIKE LOWER(%s) 
                        OR LOWER(c.nomcli) LIKE LOWER(%s))
                """
                params = [f"%{filtre}%", f"%{filtre}%", f"%{filtre}%"]
            
            query += " ORDER BY v.dateregistre DESC, v.refvente DESC"
            
            cursor.execute(query, params)
            resultats = cursor.fetchall()
            
            data_list = []
            total_factures = 0
            total_paye = 0
            total_solde = 0
            count = 0
            
            for row in resultats:
                refvente = row[0]
                date = row[1].strftime("%d/%m/%Y") if row[1] else ""
                description = row[2] or ""
                montant_total = float(row[3] or 0)
                statut = row[4] or 'EN_ATTENTE'
                paye = float(row[5] or 0)
                client = row[6] or ""
                idclient = row[7]
                user = row[8] or ""
                nb_lignes = row[9] or 0
                
                solde = montant_total - paye
                
                total_factures += montant_total
                total_paye += paye
                total_solde += solde
                count += 1
                
                # Déterminer les tags : couleur alternée + impayé si applicable
                tags = [('row_white' if count % 2 == 1 else 'row_light_gray')]
                if solde > 0.01:
                    tags.append('impaye')
                
                self.tree.insert('', 'end', values=(
                    refvente,
                    date,
                    description,
                    self.format_currency(montant_total),
                    client,
                    user,
                    nb_lignes
                ), tags=tuple(tags))
                
                data_list.append({
                    "N° Facture": refvente,
                    "Date": date,
                    "Description": description,
                    "Montant Total": montant_total,
                    "Statut": statut,
                    "Total Payé": paye,
                    "Solde": solde,
                    "Client": client,
                    "ID Client": idclient,
                    "User": user,
                    "Qté Lignes": nb_lignes
                })
            
            self.data_df = pd.DataFrame(data_list)
            
            self.total_cmd_label.configure(text=f"Total Facture: {self.format_currency(total_factures)}")
            self.total_paye_label.configure(text=f"Total Payé: {self.format_currency(total_paye)}")
            self.total_solde_label.configure(text=f"Total Solde: {self.format_currency(total_solde)}")
            self.count_label.configure(text=f"Nombre de factures: {count}")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la recherche: {str(e)}")
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if conn:
                conn.close()

    # --- Export Excel ---
    def export_to_excel(self):
        """Exporte les données vers Excel"""
        if self.data_df.empty:
            messagebox.showwarning("Attention", "Aucune donnée à exporter.")
            return
        
        try:
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"Factures_Client_{timestamp}.xlsx"
            filepath = os.path.join(desktop_path, filename)
            
            export_df = self.data_df[[
                "N° Facture", "Date", "Description", "Montant Total", 
                "Total Payé", "Solde", "Client", "User", "Qté Lignes"
            ]].copy()
            
            export_df.to_excel(filepath, index=False, sheet_name="Factures")
            
            messagebox.showinfo("Succès", f"Export réussi vers:\n{filepath}")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'export: {str(e)}")


if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Factures Clients")
    app.geometry("1200x600")
    
    app.grid_columnconfigure(0, weight=1)
    app.grid_rowconfigure(0, weight=1)
    
    page = PageFactureListe(app)
    
    app.mainloop()
