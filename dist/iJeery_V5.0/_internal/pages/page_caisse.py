import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry
from tkinter import messagebox
import psycopg2
from datetime import datetime
import json
import os
from resource_utils import get_config_path, safe_file_read


# Imports ReportLab pour le PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Déterminer le répertoire parent
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class PageCaisse(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.configure(fg_color="#f5f5f5")

        self.modes_paiement_dict = {"Tous": None}
        self.donnees_pour_pdf = []
        
        self.total_enc_periode = 0
        self.total_dec_periode = 0
        
        # Dictionnaires pour stocker les montants des cadres
        self.montants_docs = {}
        self.montants_modes = {}
        
        # Dictionnaires pour stocker les widgets des cadres
        self.cadres_docs = {}
        self.cadres_modes = {}
        
        # Variables pour les filtres actifs
        self.filtre_doc_actif = None
        self.filtre_mode_actif = None
        
        # 🔑 CRUCIAL: Mapping entre noms UI (cadres) et noms BD exactes
        # Clé: Nom du cadre UI | Valeur: Nom exact en BD
        self.mode_ui_to_bd = {
            "Espèces": None,      # Sera rempli depuis la BD
            "Crédit": None,
            "Chèque": None,
            "Virement": None,
            "Any maka vola": None,
            "Mvola": None,
            "Airtel Money": None,
            "Orange Money": None
        }
        
        # Mapping inverse pour retrouver l'ID rapidement
        self.mode_bd_to_id = {}

        # Connexion à la base de données
        self.conn = self.connect_db()
        if self.conn:
            self.cursor = self.conn.cursor()
        else:
            messagebox.showerror("Erreur", "Connexion impossible.")
            return

        # ---- CADRES DE CATÉGORIES ----
        self.frame_categories = ctk.CTkFrame(self, fg_color="#f5f5f5")
        self.frame_categories.pack(pady=5, fill="x", padx=10)
        
        # Première ligne: Documents
        self.frame_docs = ctk.CTkFrame(self.frame_categories, fg_color="#f5f5f5")
        self.frame_docs.pack(fill="x", pady=2)
        
        docs_config = [
            ("Client", "#7cb342"),
            ("Avoir", "#ffeb3b"),
            ("Fournisseur", "#64b5f6"),
            ("Personnel", "#9e9e9e"),
            ("Dépenses", "#f44336"),
            ("Encaissement", "#4caf50")
        ]
        
        for doc, color in docs_config:
            self.creer_cadre_doc(self.frame_docs, doc, color)
        
        # Deuxième ligne: Modes de paiement
        self.frame_modes = ctk.CTkFrame(self.frame_categories, fg_color="#f5f5f5")
        self.frame_modes.pack(fill="x", pady=2)
        
        modes_config = [
            ("Espèces", "#ff6f00"),
            ("Crédit", "#42a5f5"),
            ("Chèque", "#0091ea"),
            ("Virement", "#ce93d8"),
            ("Any maka vola", "#f44336"),
            ("Mvola", "#fdd835"),
            ("Airtel Money", "#c0ca33"),
            ("Orange Money", "#00bcd4")
        ]
        
        for mode, color in modes_config:
            self.creer_cadre_mode(self.frame_modes, mode, color)

        # ---- UI TOP (Filtres) ----
        self.frame_top = ctk.CTkFrame(self, fg_color="#f5f5f5")
        self.frame_top.pack(pady=10, fill="x", padx=10)

        self.label_solde_global = ctk.CTkLabel(self.frame_top, text="Solde de caisse : 0 Ar", text_color="#000", font=("Arial", 18, "bold"))
        self.label_solde_global.pack(side="left", padx=20)

        self.frame_filtre = ctk.CTkFrame(self.frame_top, fg_color="#f5f5f5")
        self.frame_filtre.pack(side="left", padx=20)

        self.entry_debut = DateEntry(self.frame_filtre, width=12, background='darkblue', date_pattern='dd/mm/yyyy')
        self.entry_debut.pack(side="left", padx=5)
        self.entry_fin = DateEntry(self.frame_filtre, width=12, background='darkblue', date_pattern='dd/mm/yyyy')
        self.entry_fin.pack(side="left", padx=5)

        ctk.CTkButton(self.frame_filtre, text="Valider", width=80, fg_color="#28a745", command=self.appliquer_filtres).pack(side="left", padx=5)
        ctk.CTkButton(self.frame_filtre, text="Imprimer PDF", width=100, fg_color="#17a2b8", command=self.generer_pdf).pack(side="left", padx=5)

        # ---- TREEVIEW ----
        self.colonnes = ("Date", "Référence", "Description", "Encaissement", "Décaissement", "Mode", "Utilisateur")
        self.frame_tree = ctk.CTkFrame(self)
        self.frame_tree.pack(fill="both", expand=True, padx=10, pady=5)

        self.tree = ttk.Treeview(self.frame_tree, columns=self.colonnes, show="headings")
        for col in self.colonnes:
            self.tree.heading(col, text=col)
            if col == "Date":
                self.tree.column(col, anchor="center", width=150)
            else:
                self.tree.column(col, anchor="center", width=110)
        self.tree.column("Description", width=250, anchor="w")

        self.scrollbar_y = ttk.Scrollbar(self.frame_tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar_y.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.scrollbar_y.grid(row=0, column=1, sticky="ns")
        self.frame_tree.grid_rowconfigure(0, weight=1)
        self.frame_tree.grid_columnconfigure(0, weight=1)

        # Styles pour lignes alternées (meilleure lisibilité)
        try:
            # Tags 'odd' et 'even' utilisés lors de l'insertion des lignes
            self.tree.tag_configure('odd', background='#ffffff')
            self.tree.tag_configure('even', background='#F2D9EA')
        except Exception:
            # Certains environnements peuvent ne pas supporter tag_configure ; ignorer silencieusement
            pass
        # ---- BOTTOM (Totaux et Boutons d'action) ----
        self.frame_bottom_container = ctk.CTkFrame(self, fg_color="#f5f5f5")
        self.frame_bottom_container.pack(pady=10, fill="x", padx=10, side="bottom")

        # Totaux à gauche
        self.frame_totaux = ctk.CTkFrame(self.frame_bottom_container, fg_color="#f5f5f5")
        self.frame_totaux.pack(side="left", fill="y")

        self.label_total_enc = ctk.CTkLabel(self.frame_totaux, text="Total Enc: 0 Ar", font=("Arial", 13, "bold"))
        self.label_total_enc.grid(row=0, column=0, padx=20, sticky='w')
        self.label_total_dec = ctk.CTkLabel(self.frame_totaux, text="Total Déc: 0 Ar", font=("Arial", 13, "bold"))
        self.label_total_dec.grid(row=1, column=0, padx=20, sticky='w')

        # Boutons à droite
        self.frame_actions = ctk.CTkFrame(self.frame_bottom_container, fg_color="#f5f5f5")
        self.frame_actions.pack(side="right", fill="y", padx=20)

        self.btn_encaissement = ctk.CTkButton(
            self.frame_actions, text="+ Encaissement", fg_color="#28a745", 
            hover_color="#218838", width=150, command=self.open_page_encaissement
        )
        self.btn_encaissement.pack(side="left", padx=5)

        self.btn_decaissement = ctk.CTkButton(
            self.frame_actions, text="- Décaissement", fg_color="#dc3545", 
            hover_color="#c82333", width=150, command=self.open_page_decaissement
        )
        self.btn_decaissement.pack(side="left", padx=5)

        self.charger_modes_paiement()
        self.appliquer_filtres()

    def creer_cadre_doc(self, parent, nom, couleur):
        """Crée un cadre cliquable pour un type de document"""
        frame = ctk.CTkFrame(parent, fg_color=couleur, corner_radius=8, width=155, height=50)
        frame.pack(side="left", padx=3, pady=3)
        frame.pack_propagate(False)
        
        label_nom = ctk.CTkLabel(frame, text=nom.upper(), font=("Arial", 9, "bold"), 
                                  text_color="#000" if couleur == "#ffeb3b" else "#fff")
        label_nom.pack(pady=(5, 0))
        
        label_montant = ctk.CTkLabel(frame, text="0", font=("Arial", 10, "bold"),
                                      text_color="#000" if couleur == "#ffeb3b" else "#fff")
        label_montant.pack()
        
        # Rendre le cadre cliquable
        def on_click(event=None):
            self.filtrer_par_doc(nom)
        
        frame.bind("<Button-1>", on_click)
        label_nom.bind("<Button-1>", on_click)
        label_montant.bind("<Button-1>", on_click)
        
        self.cadres_docs[nom] = label_montant
        
    def creer_cadre_mode(self, parent, nom, couleur):
        """Crée un cadre cliquable pour un mode de paiement"""
        frame = ctk.CTkFrame(parent, fg_color=couleur, corner_radius=8, width=130, height=50)
        frame.pack(side="left", padx=3, pady=3)
        frame.pack_propagate(False)
        
        label_nom = ctk.CTkLabel(frame, text=nom.upper(), font=("Arial", 10, "bold"),
                                  text_color="#000" if couleur in ["#ffeb3b", "#fdd835", "#c0ca33"] else "#fff")
        label_nom.pack(pady=(5, 0))
        
        label_montant = ctk.CTkLabel(frame, text="0", font=("Arial", 11, "bold"),
                                      text_color="#000" if couleur in ["#ffeb3b", "#fdd835", "#c0ca33"] else "#fff")
        label_montant.pack()
        
        # Rendre le cadre cliquable
        def on_click(event=None):
            self.filtrer_par_mode(nom)
        
        frame.bind("<Button-1>", on_click)
        label_nom.bind("<Button-1>", on_click)
        label_montant.bind("<Button-1>", on_click)
        
        self.cadres_modes[nom] = label_montant

    def filtrer_par_doc(self, doc):
        """Filtre les données par type de document - cliquer à nouveau pour désactiver le filtre"""
        if self.filtre_doc_actif == doc:
            # Si on clique sur le même filtre, on le désactive
            self.filtre_doc_actif = None
        else:
            self.filtre_doc_actif = doc
        self.appliquer_filtres()
        
    def filtrer_par_mode(self, mode):
        """Filtre les données par mode de paiement - cliquer à nouveau pour désactiver le filtre"""
        if self.filtre_mode_actif == mode:
            # Si on clique sur le même filtre, on le désactive
            self.filtre_mode_actif = None
        else:
            self.filtre_mode_actif = mode
        self.appliquer_filtres()

    def connect_db(self):
        """Établit la connexion à la base de données à partir du fichier config.json"""
        try:
            config_path = get_config_path('config.json')
            if not os.path.exists(config_path):
                config_path = 'config.json'
                
            if not os.path.exists(config_path):
                messagebox.showerror("Erreur", "Fichier config.json manquant.")
                return None
                 
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                db_config = config['database']

            conn = psycopg2.connect(
                host=db_config['host'],
                user=db_config['user'],
                password=db_config['password'],
                database=db_config['database'],
                port=db_config['port'],
                client_encoding='UTF8'
            )
            print("Connection to the database successful!")
            return conn
        except Exception as err:
            messagebox.showerror("Erreur de connexion", f"Détails : {err}")
            return None

    def format_montant(self, v):
        return f"{v:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    
    def format_montant_court(self, v):
        """Formate les montants pour les cadres avec séparateurs de milliers"""
        return self.format_montant(v)

    def charger_modes_paiement(self):
        """Charge les modes de paiement et crée un mapping UI ↔ BD"""
        try:
            self.cursor.execute("SELECT idmode, modedepaiement FROM tb_modepaiement ORDER BY modedepaiement")
            rows = self.cursor.fetchall()
            
            print("\n" + "="*80)
            print("🔄 CHARGEMENT DES MODES DE PAIEMENT")
            print("="*80)
            
            # D'abord, afficher ce qu'on a en base
            print("\n📊 Modes en base de données:")
            for r in rows:
                idmode, modedepaiement = r
                print(f"   ID {idmode}: '{modedepaiement}'")
            
            # Créer le mapping inverse : BD → ID
            for r in rows:
                idmode, modedepaiement = r
                self.mode_bd_to_id[modedepaiement] = idmode
            
            # Définir les mappages UI → BD avec TOUS les alias possibles
            print("\n🔗 Mappage UI → BD:")
            
            alias_mapping = {
                "Espèces": ["Espèces", "Espece"],
                "Crédit": ["Crédit", "Credit"],
                "Chèque": ["Chèque", "Cheque", "Chèque bancaire"],
                "Virement": ["Virement", "Virement bancaire"],
                "Any maka vola": ["Any maka vola", "Any Maka Vola"],
                "Mvola": ["Mvola", "MVOLA"],
                "Airtel Money": ["Airtel Money", "Airtel money"],
                "Orange Money": ["Orange Money", "Orange money"]
            }
            
            # Pour chaque cadre UI, chercher le mode BD correspondant
            for nom_ui, alias_list in alias_mapping.items():
                found = False
                for alias in alias_list:
                    for nom_bd, idmode in self.mode_bd_to_id.items():
                        if nom_bd.lower().strip() == alias.lower().strip():
                            self.mode_ui_to_bd[nom_ui] = nom_bd
                            self.modes_paiement_dict[nom_ui] = idmode
                            print(f"   '{nom_ui}' → '{nom_bd}' (ID: {idmode})")
                            found = True
                            break
                    if found:
                        break
                
                if not found:
                    print(f"   ⚠️  '{nom_ui}' → NON TROUVÉ en BD")
            
            print("\n📋 Dictionnaires finaux:")
            print(f"   mode_ui_to_bd = {self.mode_ui_to_bd}")
            print(f"   modes_paiement_dict = {self.modes_paiement_dict}")
            print("="*80 + "\n")
            
        except Exception as e:
            print(f"❌ Erreur lors du chargement des modes: {e}")
            import traceback
            traceback.print_exc()

    def calculer_montants_categories(self, date_d, date_f):
        """Calcule les soldes (Encaissement - Décaissement) pour chaque catégorie et mode de paiement"""
        d_str, f_str = date_d.strftime('%Y-%m-%d'), date_f.strftime('%Y-%m-%d')
        
        # Réinitialiser les montants
        self.montants_docs = {"Client": 0, "Avoir": 0, "Fournisseur": 0, "Personnel": 0, "Dépenses": 0, "Encaissement": 0}
        self.montants_modes = {}
        
        try:
            # Calculer par type de document (Encaissement - Décaissement)
            
            # Clients (Encaissements) - inclut tb_pmtfacture + tb_pmtcredit
            query_clients = """
                SELECT SUM(CASE WHEN idtypeoperation = 1 THEN mtpaye ELSE -mtpaye END)
                FROM (
                    SELECT idtypeoperation, mtpaye FROM tb_pmtfacture 
                    WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                    UNION ALL
                    SELECT idtypeoperation, mtpaye FROM tb_pmtcredit 
                    WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                ) as clients
            """
            self.cursor.execute(query_clients, [d_str, f_str, d_str, f_str])
            result = self.cursor.fetchone()
            self.montants_docs["Client"] = float(result[0]) if result and result[0] else 0
            
            # Avoir
            query_avoir = """
                SELECT SUM(CASE WHEN idtypeoperation = 1 THEN mtpaye ELSE -mtpaye END)
                FROM tb_pmtavoir 
                WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
            """
            self.cursor.execute(query_avoir, [d_str, f_str])
            result = self.cursor.fetchone()
            self.montants_docs["Avoir"] = float(result[0]) if result and result[0] else 0
            
            # Fournisseurs (Décaissements)
            query_fournisseurs = """
                SELECT SUM(CASE WHEN idtypeoperation = 1 THEN mtpaye ELSE -mtpaye END)
                FROM tb_pmtcom 
                WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
            """
            self.cursor.execute(query_fournisseurs, [d_str, f_str])
            result = self.cursor.fetchone()
            self.montants_docs["Fournisseur"] = float(result[0]) if result and result[0] else 0
            
            # Personnel (avances + salaires)
            query_pers = """
                SELECT SUM(CASE WHEN idtypeoperation = 1 THEN mtpaye ELSE -mtpaye END)
                FROM (
                    SELECT idtypeoperation, mtpaye FROM tb_avancepers WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                    UNION ALL
                    SELECT idtypeoperation, mtpaye FROM tb_avancespecpers WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                    UNION ALL
                    SELECT idtypeoperation, mtpaye FROM tb_pmtsalaire WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                ) as pers
            """
            self.cursor.execute(query_pers, [d_str, f_str, d_str, f_str, d_str, f_str])
            result = self.cursor.fetchone()
            self.montants_docs["Personnel"] = float(result[0]) if result and result[0] else 0
            
            # Dépenses (seulement tb_decaissement - référence DEC...)
            query_depenses = """
                SELECT SUM(CASE WHEN idtypeoperation = 1 THEN mtpaye ELSE -mtpaye END)
                FROM tb_decaissement 
                WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
            """
            self.cursor.execute(query_depenses, [d_str, f_str])
            result = self.cursor.fetchone()
            self.montants_docs["Dépenses"] = float(result[0]) if result and result[0] else 0
            
            # Encaissements (seulement tb_encaissement - référence ENC...)
            query_encaissements = """
                SELECT SUM(CASE WHEN idtypeoperation = 1 THEN mtpaye ELSE -mtpaye END)
                FROM tb_encaissement 
                WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
            """
            self.cursor.execute(query_encaissements, [d_str, f_str])
            result = self.cursor.fetchone()
            self.montants_docs["Encaissement"] = float(result[0]) if result and result[0] else 0
            
            # Calculer par mode de paiement (Encaissement - Décaissement)
            query_modes = """
                SELECT COALESCE(t2.modedepaiement, 'Inconnu'), 
                       SUM(CASE WHEN t1.idtypeoperation = 1 THEN t1.mtpaye ELSE -t1.mtpaye END)
                FROM (
                    SELECT idmode, mtpaye, idtypeoperation FROM tb_pmtfacture WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                    UNION ALL
                    SELECT idmode, mtpaye, idtypeoperation FROM tb_pmtcom WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                    UNION ALL
                    SELECT idmode, mtpaye, idtypeoperation FROM tb_encaissement WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                    UNION ALL
                    SELECT idmode, mtpaye, idtypeoperation FROM tb_decaissement WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                    UNION ALL
                    SELECT idmode, mtpaye, idtypeoperation FROM tb_avancepers WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                    UNION ALL
                    SELECT idmode, mtpaye, idtypeoperation FROM tb_avancespecpers WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                    UNION ALL
                    SELECT idmode, mtpaye, idtypeoperation FROM tb_pmtsalaire WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                    UNION ALL
                    SELECT idmode, mtpaye, idtypeoperation FROM tb_pmtavoir WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                    UNION ALL
                    SELECT idmode, mtpaye, idtypeoperation FROM tb_pmtcredit WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                ) t1
                LEFT JOIN tb_modepaiement t2 ON t1.idmode = t2.idmode
                GROUP BY t2.modedepaiement
            """
            params = [d_str, f_str] * 9
            self.cursor.execute(query_modes, params)
            for row in self.cursor.fetchall():
                mode, solde = row
                self.montants_modes[mode] = float(solde) if solde else 0
            
            # Mettre à jour l'affichage des cadres
            self.mettre_a_jour_cadres()
            
        except Exception as e:
            print(f"Erreur calcul montants: {e}")

    def mettre_a_jour_cadres(self):
        """Met à jour l'affichage des montants dans les cadres"""
        # Mise à jour des cadres documents
        for doc, label in self.cadres_docs.items():
            montant = self.montants_docs.get(doc, 0)
            
            label.configure(text=self.format_montant_court(montant))
        
        # Mise à jour des cadres modes de paiement
        # ⚠️ CRUCIAL: Convertir les noms UI en noms BD pour chercher les montants
        for mode_ui, label in self.cadres_modes.items():
            mode_bd = self.mode_ui_to_bd.get(mode_ui)
            if mode_bd:
                montant = self.montants_modes.get(mode_bd, 0)
            else:
                montant = 0
            label.configure(text=self.format_montant_court(montant))

    def appliquer_filtres(self, _=None):
        # Utiliser les filtres actifs au lieu des ComboBox
        mode_nom_ui = self.filtre_mode_actif  # C'est le nom du cadre UI
        
        # Chercher l'ID du mode en utilisant le mapping
        mode_id = None
        if mode_nom_ui:
            # mode_nom_ui est le nom du cadre (ex: "Espèces")
            # On cherche le mode_bd correspondant dans le mapping
            mode_bd = self.mode_ui_to_bd.get(mode_nom_ui)
            if mode_bd:
                mode_id = self.mode_bd_to_id.get(mode_bd)
        
        type_doc = self.filtre_doc_actif if self.filtre_doc_actif else "Tous"
        
        # 🔍 DEBUG - Afficher les filtres actifs
        print(f"\n{'='*60}")
        print(f"🔍 FILTRES ACTIFS:")
        print(f"   Type document        : {type_doc}")
        print(f"   Mode (UI)            : {mode_nom_ui}")
        print(f"   Mode (BD)            : {self.mode_ui_to_bd.get(mode_nom_ui) if mode_nom_ui else None}")
        print(f"   Mode ID              : {mode_id}")
        print(f"{'='*60}\n")
        
        date_d = self.entry_debut.get_date()
        date_f = self.entry_fin.get_date()
        
        # Calculer les montants des catégories
        self.calculer_montants_categories(date_d, date_f)
        
        # Charger les données filtrées
        self.charger_donnees(date_d, date_f, mode_id, type_doc)

    def charger_donnees(self, date_d, date_f, mode_id=None, type_doc="Tous"):
        if not self.conn: return
        d_str, f_str = date_d.strftime('%Y-%m-%d'), date_f.strftime('%Y-%m-%d')

        for item in self.tree.get_children(): self.tree.delete(item)
        all_ops = []

        # Construire la clause WHERE pour le mode
        sql_mode = ""
        mode_params = []
        if mode_id is not None:
            sql_mode = " AND t1.idmode = %s"
            mode_params = [mode_id]

        try:
            # ==================================================================
            # LOGIQUE CORRECTE :
            # - CLIENTS = tb_pmtfacture + tb_pmtcredit (tous modes de paiement)
            # - AVOIR = tb_pmtavoir
            # - FOURNISSEURS = tb_pmtcom
            # - PERSONNEL = tb_avancepers + tb_avancespecpers + tb_pmtsalaire
            # - DÉPENSES = tb_decaissement
            # - ENCAISSEMENTS = tb_encaissement
            # ==================================================================
            
            # 1. tb_pmtfacture (CLIENTS - tous les paiements de factures clients)
            if type_doc in ["Tous", "Client"]:
                query_pmtfacture = f"""
                    SELECT t1.datepmt, t1.refpmt, t1.observation, t1.mtpaye, t1.idtypeoperation, 
                        COALESCE(t2.modedepaiement, 'Inconnu'), COALESCE(t3.username, 'Système')
                    FROM tb_pmtfacture t1
                    LEFT JOIN tb_modepaiement t2 ON t1.idmode = t2.idmode
                    LEFT JOIN tb_users t3 ON t1.iduser = t3.iduser
                    WHERE t1.datepmt::date BETWEEN %s AND %s AND t1.id_banque IS NULL {sql_mode}
                """
                params = [d_str, f_str] + mode_params
                try:
                    self.cursor.execute(query_pmtfacture, params)
                    all_ops.extend(self.cursor.fetchall())
                    print(f"✅ tb_pmtfacture: {self.cursor.rowcount} lignes")
                except psycopg2.Error as e:
                    print(f"❌ Erreur sur tb_pmtfacture: {e}")
                    self.conn.rollback()

            # 2. tb_pmtcredit (CLIENTS - paiements de crédits clients)
            if type_doc in ["Tous", "Client"]:
                query_pmtcredit = f"""
                    SELECT t1.datepmt, t1.refpmt, t1.observation, t1.mtpaye, t1.idtypeoperation, 
                        COALESCE(t2.modedepaiement, 'Inconnu'), COALESCE(t3.username, 'Système')
                    FROM tb_pmtcredit t1
                    LEFT JOIN tb_modepaiement t2 ON t1.idmode = t2.idmode
                    LEFT JOIN tb_users t3 ON t1.iduser = t3.iduser
                    WHERE t1.datepmt::date BETWEEN %s AND %s AND t1.id_banque IS NULL {sql_mode}
                """
                params = [d_str, f_str] + mode_params
                try:
                    self.cursor.execute(query_pmtcredit, params)
                    all_ops.extend(self.cursor.fetchall())
                    print(f"✅ tb_pmtcredit: {self.cursor.rowcount} lignes")
                except psycopg2.Error as e:
                    print(f"❌ Erreur sur tb_pmtcredit: {e}")
                    self.conn.rollback()

            # 3. tb_pmtavoir (AVOIR)
            if type_doc in ["Tous", "Avoir"]:
                query_avoir = f"""
                    SELECT t1.datepmt, t1.refavoir, t1.observation, t1.mtpaye, t1.idtypeoperation, 
                        COALESCE(t2.modedepaiement, 'Inconnu'), COALESCE(t3.username, 'Système')
                    FROM tb_pmtavoir t1
                    LEFT JOIN tb_modepaiement t2 ON t1.idmode = t2.idmode
                    LEFT JOIN tb_users t3 ON t1.iduser = t3.iduser
                    WHERE t1.datepmt::date BETWEEN %s AND %s AND t1.id_banque IS NULL {sql_mode}
                """
                params = [d_str, f_str] + mode_params
                try:
                    self.cursor.execute(query_avoir, params)
                    all_ops.extend(self.cursor.fetchall())
                    print(f"✅ tb_pmtavoir: {self.cursor.rowcount} lignes")
                except psycopg2.Error as e:
                    print(f"❌ Erreur sur tb_pmtavoir: {e}")
                    self.conn.rollback()

            # 4. tb_pmtcom (FOURNISSEURS)
            if type_doc in ["Tous", "Fournisseur"]:
                query_pmtcom = f"""
                    SELECT t1.datepmt, t1.refpmt, t1.observation, t1.mtpaye, t1.idtypeoperation, 
                        COALESCE(t2.modedepaiement, 'Inconnu'), COALESCE(t3.username, 'Système')
                    FROM tb_pmtcom t1
                    LEFT JOIN tb_modepaiement t2 ON t1.idmode = t2.idmode
                    LEFT JOIN tb_users t3 ON t1.iduser = t3.iduser
                    WHERE t1.datepmt::date BETWEEN %s AND %s AND t1.id_banque IS NULL {sql_mode}
                """
                params = [d_str, f_str] + mode_params
                try:
                    self.cursor.execute(query_pmtcom, params)
                    all_ops.extend(self.cursor.fetchall())
                    print(f"✅ tb_pmtcom: {self.cursor.rowcount} lignes")
                except psycopg2.Error as e:
                    print(f"❌ Erreur sur tb_pmtcom: {e}")
                    self.conn.rollback()

            # 5. tb_encaissement (ENCAISSEMENTS)
            if type_doc in ["Tous", "Encaissement"]:
                query_enc = f"""
                    SELECT t1.datepmt, t1.refpmt, t1.observation, t1.mtpaye, t1.idtypeoperation, 
                        COALESCE(t2.modedepaiement, 'Inconnu'), COALESCE(t3.username, 'Système')
                    FROM tb_encaissement t1
                    LEFT JOIN tb_modepaiement t2 ON t1.idmode = t2.idmode
                    LEFT JOIN tb_users t3 ON t1.iduser = t3.iduser
                    WHERE t1.datepmt::date BETWEEN %s AND %s AND t1.id_banque IS NULL {sql_mode}
                """
                params = [d_str, f_str] + mode_params
                try:
                    self.cursor.execute(query_enc, params)
                    all_ops.extend(self.cursor.fetchall())
                    print(f"✅ tb_encaissement: {self.cursor.rowcount} lignes")
                except psycopg2.Error as e:
                    print(f"❌ Erreur sur tb_encaissement: {e}")
                    self.conn.rollback()

            # 6. tb_decaissement (DÉPENSES)
            if type_doc in ["Tous", "Dépenses"]:
                query_dec = f"""
                    SELECT t1.datepmt, t1.refpmt, t1.observation, t1.mtpaye, t1.idtypeoperation, 
                        COALESCE(t2.modedepaiement, 'Inconnu'), COALESCE(t3.username, 'Système')
                    FROM tb_decaissement t1
                    LEFT JOIN tb_modepaiement t2 ON t1.idmode = t2.idmode
                    LEFT JOIN tb_users t3 ON t1.iduser = t3.iduser
                    WHERE t1.datepmt::date BETWEEN %s AND %s AND t1.id_banque IS NULL {sql_mode}
                """
                params = [d_str, f_str] + mode_params
                try:
                    self.cursor.execute(query_dec, params)
                    all_ops.extend(self.cursor.fetchall())
                    print(f"✅ tb_decaissement: {self.cursor.rowcount} lignes")
                except psycopg2.Error as e:
                    print(f"❌ Erreur sur tb_decaissement: {e}")
                    self.conn.rollback()

            # 7. Tables PERSONNEL (avances et salaires)
            if type_doc in ["Tous", "Personnel"]:
                # tb_avancepers
                query_avpers = f"""
                    SELECT t1.datepmt, t1.refpmt, t1.observation, t1.mtpaye, t1.idtypeoperation, 
                        COALESCE(t2.modedepaiement, 'Inconnu'), COALESCE(t3.username, 'Système')
                    FROM tb_avancepers t1
                    LEFT JOIN tb_modepaiement t2 ON t1.idmode = t2.idmode
                    LEFT JOIN tb_users t3 ON t1.iduser = t3.iduser
                    WHERE t1.datepmt::date BETWEEN %s AND %s AND t1.id_banque IS NULL {sql_mode}
                """
                params = [d_str, f_str] + mode_params
                try:
                    self.cursor.execute(query_avpers, params)
                    all_ops.extend(self.cursor.fetchall())
                    print(f"✅ tb_avancepers: {self.cursor.rowcount} lignes")
                except psycopg2.Error as e:
                    print(f"❌ Erreur sur tb_avancepers: {e}")
                    self.conn.rollback()

                # tb_avancespecpers
                query_avspec = f"""
                    SELECT t1.datepmt, t1.refpmt, t1.observation, t1.mtpaye, t1.idtypeoperation, 
                        COALESCE(t2.modedepaiement, 'Inconnu'), COALESCE(t3.username, 'Système')
                    FROM tb_avancespecpers t1
                    LEFT JOIN tb_modepaiement t2 ON t1.idmode = t2.idmode
                    LEFT JOIN tb_users t3 ON t1.iduser = t3.iduser
                    WHERE t1.datepmt::date BETWEEN %s AND %s AND t1.id_banque IS NULL {sql_mode}
                """
                params = [d_str, f_str] + mode_params
                try:
                    self.cursor.execute(query_avspec, params)
                    all_ops.extend(self.cursor.fetchall())
                    print(f"✅ tb_avancespecpers: {self.cursor.rowcount} lignes")
                except psycopg2.Error as e:
                    print(f"❌ Erreur sur tb_avancespecpers: {e}")
                    self.conn.rollback()

                # tb_pmtsalaire
                query_sal = f"""
                    SELECT t1.datepmt, t1.refpmt, t1.observation, t1.mtpaye, t1.idtypeoperation, 
                        COALESCE(t2.modedepaiement, 'Inconnu'), COALESCE(t3.username, 'Système')
                    FROM tb_pmtsalaire t1
                    LEFT JOIN tb_modepaiement t2 ON t1.idmode = t2.idmode
                    LEFT JOIN tb_users t3 ON t1.iduser = t3.iduser
                    WHERE t1.datepmt::date BETWEEN %s AND %s AND t1.id_banque IS NULL {sql_mode}
                """
                params = [d_str, f_str] + mode_params
                try:
                    self.cursor.execute(query_sal, params)
                    all_ops.extend(self.cursor.fetchall())
                    print(f"✅ tb_pmtsalaire: {self.cursor.rowcount} lignes")
                except psycopg2.Error as e:
                    print(f"❌ Erreur sur tb_pmtsalaire: {e}")
                    self.conn.rollback()

            # 8. Transferts (seulement si "Tous" et mode Espèces ou pas de filtre mode)
            if (not mode_id or mode_id == 1) and type_doc == "Tous": 
                query_transfert = """
                    SELECT t1.datepmt, t1.refpmt, t1.observation, t1.mtpaye, t1.idtypeoperation, 
                        COALESCE(t2.modedepaiement, 'Espèces'), COALESCE(t3.username, 'admin')
                    FROM tb_transfertcaisse t1
                    LEFT JOIN tb_modepaiement t2 ON t1.idmode = t2.idmode
                    LEFT JOIN tb_users t3 ON t1.iduser = t3.iduser
                    WHERE t1.datepmt::date BETWEEN %s AND %s
                """
                try:
                    self.cursor.execute(query_transfert, [d_str, f_str])
                    all_ops.extend(self.cursor.fetchall())
                    print(f"✅ tb_transfertcaisse: {self.cursor.rowcount} lignes")
                except psycopg2.Error as e:
                    print(f"❌ Erreur sur tb_transfertcaisse: {e}")
                    self.conn.rollback()

            # Convertir toutes les dates en datetime pour le tri
            def get_datetime(op):
                dt = op[0]
                if isinstance(dt, datetime):
                    return dt
                else:  # C'est un objet date
                    return datetime.combine(dt, datetime.min.time())
            
            all_ops.sort(key=get_datetime, reverse=True)
            self.donnees_pour_pdf = []
            self.total_enc_periode = 0
            self.total_dec_periode = 0

            for i, r in enumerate(all_ops):
                dt, ref, obs, mt, typ, mod, usr = r
                enc = float(mt) if typ == 1 else 0
                dec = float(mt) if typ == 2 else 0
                self.total_enc_periode += enc
                self.total_dec_periode += dec

                # Gérer datetime et date
                if isinstance(dt, datetime):
                    date_str = dt.strftime("%d/%m/%Y %H:%M:%S")
                else:  # C'est un objet date
                    date_str = dt.strftime("%d/%m/%Y 00:00:00")

                vals = (date_str, str(ref), str(obs), 
                    self.format_montant(enc) if enc else "", 
                    self.format_montant(dec) if dec else "", 
                    mod, usr)

                # Alternance des lignes pour lisibilité
                tag = 'even' if (i % 2) else 'odd'
                try:
                    self.tree.insert("", "end", values=vals, tags=(tag,))
                except TypeError:
                    # Certains environnements/test runners peuvent rejeter tags ; utiliser insertion simple
                    self.tree.insert("", "end", values=vals)

                self.donnees_pour_pdf.append(list(vals))

            self.label_total_enc.configure(text=f"Total Encaissement: {self.format_montant(self.total_enc_periode)} Ar")
            self.label_total_dec.configure(text=f"Total Décaissement: {self.format_montant(self.total_dec_periode)} Ar")
            self.update_solde_global()
    
        except Exception as e:
            print(f"Erreur lors du chargement des données: {e}")

    def update_solde_global(self):
        try:
            query = """
                SELECT SUM(CASE WHEN idtypeoperation = 1 THEN mtpaye ELSE -mtpaye END) 
                FROM (
                    SELECT idtypeoperation, mtpaye FROM tb_pmtfacture WHERE id_banque IS NULL
                    UNION ALL SELECT idtypeoperation, mtpaye FROM tb_pmtcom WHERE id_banque IS NULL
                    UNION ALL SELECT idtypeoperation, mtpaye FROM tb_encaissement WHERE id_banque IS NULL
                    UNION ALL SELECT idtypeoperation, mtpaye FROM tb_decaissement WHERE id_banque IS NULL
                    UNION ALL SELECT idtypeoperation, mtpaye FROM tb_avancepers WHERE id_banque IS NULL
                    UNION ALL SELECT idtypeoperation, mtpaye FROM tb_avancespecpers WHERE id_banque IS NULL
                    UNION ALL SELECT idtypeoperation, mtpaye FROM tb_pmtsalaire WHERE id_banque IS NULL
                    UNION ALL SELECT idtypeoperation, mtpaye FROM tb_transfertcaisse
                    UNION ALL SELECT idtypeoperation, mtpaye FROM tb_pmtavoir WHERE id_banque IS NULL
                    UNION ALL SELECT idtypeoperation, mtpaye FROM tb_pmtcredit WHERE id_banque IS NULL
                ) as total
            """
            self.cursor.execute(query)
            res = self.cursor.fetchone()
            
            solde = float(res[0]) if res and res[0] is not None else 0.0
            
            self.label_solde_global.configure(
                text=f"Solde de caisse : {self.format_montant(solde)} Ar"
            )
        except Exception as e:
            print(f"Erreur calcul solde global: {e}")
            self.label_solde_global.configure(text="Solde de caisse : Erreur Ar")

    def generer_pdf(self):
        if not self.donnees_pour_pdf:
            messagebox.showwarning("Vide", "Aucune donnée à imprimer.")
            return

        # 1. Récupération des infos société
        infos_societe = {"nom": "", "adresse": "", "ville": "", "contact": ""}
        try:
            self.cursor.execute("SELECT nomsociete, adressesociete, villesociete, contactsociete FROM tb_infosociete LIMIT 1")
            res = self.cursor.fetchone()
            if res:
                infos_societe = {
                    "nom": res[0],
                    "adresse": res[1],
                    "ville": res[2],
                    "contact": res[3]
                }
        except Exception as e:
            print(f"Erreur recup infos societe: {e}")

        nom_fichier = f"Etat_Caisse_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        try:
            doc = SimpleDocTemplate(nom_fichier, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
            elements = []
            styles = getSampleStyleSheet()
            
            style_societe_nom = ParagraphStyle('SocieteNom', parent=styles['Normal'], fontSize=14, leading=16, fontName='Helvetica-Bold')
            style_societe_details = ParagraphStyle('SocieteDetails', parent=styles['Normal'], fontSize=10, leading=12)

            if infos_societe["nom"]:
                elements.append(Paragraph(infos_societe["nom"].upper(), style_societe_nom))
                elements.append(Paragraph(f"{infos_societe['adresse']}", style_societe_details))
                elements.append(Paragraph(f"{infos_societe['ville']}", style_societe_details))
                elements.append(Paragraph(f"Contact : {infos_societe['contact']}", style_societe_details))
            
            elements.append(Spacer(1, 20))
            
            filtre_doc = self.filtre_doc_actif if self.filtre_doc_actif else "Tous"
            filtre_mode = self.filtre_mode_actif if self.filtre_mode_actif else "Tous"
            
            elements.append(Paragraph(f"<b>ETAT DE CAISSE - {filtre_mode} ({filtre_doc})</b>", styles['Title']))
            elements.append(Paragraph(f"Période du {self.entry_debut.get()} au {self.entry_fin.get()}", styles['Normal']))
            elements.append(Spacer(1, 15))

            data = [self.colonnes]
            data.extend(self.donnees_pour_pdf)
            solde_periode = self.total_enc_periode - self.total_dec_periode
            data.append(["", "", "TOTAL CUMULÉ", self.format_montant(self.total_enc_periode), self.format_montant(self.total_dec_periode), "", ""])
            data.append(["", "", "SOLDE DE LA PÉRIODE", "", self.format_montant(solde_periode), "", ""])

            t = Table(data, repeatRows=1, colWidths=[100, 80, 200, 90, 90, 70, 70])
            style_list = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (2, 0), (2, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -3), 0.5, colors.black),
                ('BACKGROUND', (0, -2), (-1, -1), colors.lightgrey),
                ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
                ('GRID', (2, -2), (4, -1), 1, colors.black),
                ('ALIGN', (3, -2), (4, -1), 'RIGHT'),
            ]
            t.setStyle(TableStyle(style_list))
            elements.append(t)
            
            elements.append(Spacer(1, 30))
            elements.append(Paragraph(f"Edité le : {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Italic']))
            
            doc.build(elements)
            os.startfile(nom_fichier)
            
        except Exception as e:
            messagebox.showerror("Erreur PDF", f"Détails : {e}")

    def open_page_decaissement(self):
        try:
            from page_decaissement import PageDecaissement
        except ImportError:
            from pages.page_decaissement import PageDecaissement
    
        win = PageDecaissement(self.master, username="VotreUsername")
        self.master.wait_window(win)
        self.appliquer_filtres()

    def open_page_encaissement(self):
        try:
            from page_encaissement import PageEncaissement
        except ImportError:
            from pages.page_encaissement import PageEncaissement
    
        win = PageEncaissement(self.master, username="VotreUsername")
        self.master.wait_window(win)
        self.appliquer_filtres()

if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Gestion Caisse")
    app.geometry("1150x700")
    PageCaisse(app).pack(fill="both", expand=True)
    app.mainloop()
