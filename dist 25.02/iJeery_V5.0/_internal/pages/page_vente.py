import customtkinter as ctk
from tkinter import messagebox, ttk, simpledialog
import psycopg2
import json
from datetime import datetime
import calendar 
from typing import Optional, Dict, Any, List
import traceback 
import os
import sys # Ajouté pour open_file sur Linux/macOS
import textwrap # Ajouté pour le formatage du ticket de caisse
from resource_utils import get_config_path, safe_file_read


# --- NOUVELLES IMPORTATIONS POUR L'IMPRESSION ---
from reportlab.lib.pagesizes import A5, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from pages.page_avoir import PageAvoir
from pages.page_proforma import PageCommandeCli
# -----------------------------------------------

# ==============================================================================
# FONCTION UTILITAIRE : CONVERSION NOMBRE EN LETTRES (FRANÇAIS)
# ==============================================================================

def nombre_en_lettres_fr(montant: float) -> str:
    """
    Convertit un montant numérique en sa représentation en lettres en français.
    Gère les Millions et les Milliers correctement.
    """
    from math import floor
    
    if montant is None: return ""
    
    try:
        montant = round(float(montant), 2)
    except ValueError:
        return ""

    unites = ["", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf"]
    dix_a_dixneuf = ["dix", "onze", "douze", "treize", "quatorze", "quinze", "seize"]
    dizaines = ["", "dix", "vingt", "trente", "quarante", "cinquante", "soixante", "soixante", "quatre-vingt", "quatre-vingt"]
    
    def convertir_nombre_simple(n):
        if n == 0: return ""
        texte = []
        
        # Unités (0-9)
        if n < 10:
            texte.append(unites[n])
        # 10-16
        elif n < 17:
            texte.append(dix_a_dixneuf[n - 10])
        # 17-19
        elif n < 20:
            texte.append("dix-" + unites[n - 10])
        # 20-99 (simplifié)
        elif n < 100:
            d = n // 10
            u = n % 10
            
            partie_dizaine = dizaines[d]
            if (d == 2 or d > 6) and u == 1: # 21, 71, 91 (simplifié)
                 partie_dizaine += " et"
            
            texte.append(partie_dizaine)
            if u > 0:
                if d == 7 or d == 9: # 70-79, 90-99
                    texte.append("-" + convertir_nombre_simple(n - (d * 10)))
                else:
                    texte.append("-" + unites[u])
        
        return "".join(texte).replace("--", "-") # Corrige double trait d'union

    def convertir_bloc(n):
        if n == 0: return ""
        if n < 100: return convertir_nombre_simple(n)
        
        texte = []
        c = n // 100
        r = n % 100
        
        if c == 1: texte.append("cent")
        else: 
            texte.append(convertir_nombre_simple(c) + "-cent")
            if r == 0: texte[-1] += "s" # Quatre-cents
        
        if r > 0:
            texte.append("-" + convertir_bloc(r))

        return "".join(texte).replace("un-cent", "cent") # Corrige 'un-cent' -> 'cent'
    
    entier = floor(montant)
    centimes = int(round((montant - entier) * 100))
    
    # ====================================================================
    # Gestion des blocs Millions, Milliers, Unités
    # ====================================================================
    million = entier // 1_000_000
    mille_reste = (entier % 1_000_000) // 1_000 
    reste_unites = entier % 1_000 
    
    resultat = []
    
    # 1. MILLIONS
    if million > 0:
        lettres_million = convertir_bloc(million)
        bloc_million = "million"
        if million > 1: bloc_million += "s"
        resultat.append(f"{lettres_million} {bloc_million}")
    
    # 2. MILLIERS (0 à 999)
    if mille_reste > 0:
        lettres_mille = convertir_bloc(mille_reste)
        resultat.append(f"{lettres_mille} mille")
    
    # 3. UNITÉS (0 à 999)
    if reste_unites > 0:
        resultat.append(convertir_bloc(reste_unites))
    
    # 4. CAS SPECIAL: ZÉRO
    if entier == 0 and centimes == 0 and not resultat:
        resultat.append("zéro")

    
    # Monnaie
    result_str = " ".join(resultat).strip().replace("  ", " ").replace("-", " ") 
    if not result_str: result_str = "zéro"
    
    unite_monetaire = "Ariary" # Assurez-vous que cette unité est correcte (était "Francs" dans le code précédent)
    result_str += " " + unite_monetaire
    
    # Centimes
    if centimes > 0:
        centime_lettres = convertir_bloc(centimes)
        centime_monetaire = "centimes"
        centime_lettres = centime_lettres.replace("-", " ")
        result_str += " et " + centime_lettres + " " + centime_monetaire

    return result_str.capitalize().replace(" et-", " et ")
    
# ==============================================================================

# ==============================================================================
# CLASSE UTILITAIRE : DIALOGUE DE CHOIX D'IMPRESSION (CTKTOPLEVEL)
# ==============================================================================
class SimpleDialogWithChoice(ctk.CTkToplevel):
    """Dialogue modal personnalisé pour choisir le format d'impression."""
    def __init__(self, master, title, message):
        super().__init__(master)
        self.title(title)
        self.transient(master)
        self.grab_set()
        
        self.result = None
        self.choice = ctk.StringVar(self, value="A5 PDF (Paysage)")
        
        # UI
        ctk.CTkLabel(self, text=message, wraplength=350, justify="left").pack(pady=10, padx=20)
        
        frame_radio = ctk.CTkFrame(self)
        frame_radio.pack(pady=5, padx=20, fill="x")
        
        self.radio_pdf = ctk.CTkRadioButton(frame_radio, text="A5 PDF (Paysage)", variable=self.choice, value="A5 PDF (Paysage)")
        self.radio_pdf.pack(pady=5, padx=10, anchor="w")
        
        self.radio_ticket = ctk.CTkRadioButton(frame_radio, text="Ticket de Caisse 80mm", variable=self.choice, value="Ticket 80mm")
        self.radio_ticket.pack(pady=5, padx=10, anchor="w")
        
        # Boutons
        frame_buttons = ctk.CTkFrame(self)
        frame_buttons.pack(pady=10, padx=20)
        
        ctk.CTkButton(frame_buttons, text="Annuler", command=self.cancel, fg_color="#d32f2f", hover_color="#b71c1c").pack(side="left", padx=5)
        ctk.CTkButton(frame_buttons, text="Imprimer", command=self.ok, fg_color="#00695c", hover_color="#004d40").pack(side="right", padx=5)
        
        self.wait_window(self)

    def ok(self):
        self.result = self.choice.get()
        self.grab_release()
        self.destroy()

    def cancel(self):
        self.result = None
        self.grab_release()
        self.destroy()
# ==============================================================================


# --- Configuration de CustomTkinter ---
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class PageVente(ctk.CTkFrame):
    """
    Fenêtre de gestion des ventes de stock.
    """
    def __init__(self, master, id_user_connecte=None, **kwargs):
        super().__init__(master, **kwargs)
        self.id_user_connecte = id_user_connecte
        self.magasins = [] # Liste pour stocker (id, nom)
        self.charger_magasins() # Appelez votre méthode existante ou celle ci-dessous
        
        # --- AJOUTEZ CES DEUX LIGNES ICI ---
        self.magasins = []
        self.charger_magasins()
        if id_user_connecte is None:
            messagebox.showerror("Erreur", "Aucun utilisateur connecté. Veuillez vous reconnecter.")
            self.id_user_connecte = None
        else:
            self.id_user_connecte = id_user_connecte
            print(f"✅ Utilisateur connecté - ID: {self.id_user_connecte}")
        self.id_user_connecte = id_user_connecte 
        self.conn: Optional[psycopg2.connection] = None
        self.article_selectionne = None
        self.detail_vente = []
        self.index_ligne_selectionnee = None
        self.magasin_map = {}
        self.magasin_ids = []
        self.client_map = {}
        self.client_ids = []
        self.infos_societe: Dict[str, Any] = {}
        self.derniere_idvente_enregistree: Optional[int] = None
    
        self.mode_modification = False
        self.idvente_charge = None
        self.details_proforma_a_ajouter: Optional[List[Dict]] = None # NOUVEAU: Stocke temporairement les lignes du proforma
        self.details_proforma_a_ajouter_idprof: Optional[int] = None # NOUVEAU: ID du proforma chargé
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=0)
        
        self.setup_ui()
        self.generer_reference()
        self.charger_magasins()
        self.charger_client()
        self.charger_infos_societe()
        self.conn = self.connect_db() 

    def connect_db(self):
        """Connexion à la base de données PostgreSQL (Méthode fournie par l'utilisateur)"""
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
            messagebox.showerror("Erreur de Base de Données", f"Impossible de se connecter à la base de données : {e}")
            return None
    
    # --- FONCTIONS DE FORMATAGE ET DE CALCUL DE STOCK ---
    def formater_nombre(self, nombre):
        """Formate un nombre avec séparateur de milliers (1.000.000,00)"""
        try:
            nombre = float(nombre) 
            # Utilise un formatage pour avoir des séparateurs de milliers
            formatted = "{:,.2f}".format(nombre).replace(',', '_TEMP_').replace('.', ',').replace('_TEMP_', '.')
            return formatted
        except:
            return "0,00"
    
    def parser_nombre(self, texte):
        """Convertit un nombre formaté (1.000.000,00) en float"""
        try:
            # Remplace le point de séparation des milliers et la virgule décimale par un point
            texte_clean = texte.replace('.', '').replace(',', '.')
            return float(texte_clean)
        except:
            return 0.0

    def get_article_price(self, idarticle, idunite):
        """Récupère le dernier prix unitaire pour l'article et l'unité donnés."""
        conn = self.conn   # <<< UTILISATION DE LA CONNEXION PRINCIPALE
        if not conn:
            return 0.0

        try:
            cursor = conn.cursor()

            # 1. Dernier prix dans tb_prix
            sql_prix = """
                SELECT COALESCE(prix) as prix FROM tb_prix 
                WHERE idarticle = %s AND idunite = %s 
                ORDER BY id DESC 
                LIMIT 1
            """
            cursor.execute(sql_prix, (idarticle, idunite))
            result = cursor.fetchone()

            if result and result[0] is not None and result[0] > 0:
                return float(result[0])

            # 2. Sinon, prixventeunite dans tb_unite
            sql_unite = """
                SELECT prix 
                FROM tb_unite 
                WHERE idarticle = %s AND idunite = %s 
                LIMIT 1
            """
            cursor.execute(sql_unite, (idarticle, idunite))
            result_unite = cursor.fetchone()

            if result_unite and result_unite[0] is not None:
                return float(result_unite[0])

            return 0.0

        except Exception as e:
            print("ERREUR get_article_price :", e)
            return 0.0

        finally:
            if 'cursor' in locals():
                cursor.close()

    
    def calculer_stock_article(self, id_art, id_uni, id_mag):
        """Calcule le stock actuel pour un article, une unité et un magasin précis."""
        conn = self.connect_db()
        stock_total = 0
        if conn:
            try:
                cursor = conn.cursor()
                query = """
                SELECT 
                    (SELECT COALESCE(SUM(quantite), 0) FROM tb_entree_stock 
                     WHERE idarticle = %s AND idunite = %s AND idmagasin = %s) -
                                        (SELECT COALESCE(SUM(quantite), 0) FROM tb_ligne_vente lv
                                         JOIN tb_vente v ON lv.idvente = v.idvente
                                         WHERE lv.idarticle = %s AND lv.idunite = %s AND v.idmagasin = %s
                                             AND v.statut = 'VALIDEE')
            """
                cursor.execute(query, (id_art, id_uni, id_mag, id_art, id_uni, id_mag))
                res = cursor.fetchone()
                stock_total = res[0] if res else 0
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"Erreur calcul stock: {e}")
        return stock_total
    
    def charger_stocks(self):
        """Charge tous les stocks dans le Treeview"""
        # Créer/recréer le Treeview
        self.creer_treeview()
        
        # Vider le Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        conn = self.connect_db()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            
            # Récupérer tous les articles avec leurs unités
            query = """
                SELECT DISTINCT 
                    a.idarticle, 
                    u.codearticle, 
                    a.designation, 
                    u.designationunite,
                    u.idunite,
                    COALESCE(p.prix, 0) as prix
                FROM tb_article a
                INNER JOIN tb_unite u ON a.idarticle = u.idarticle
                LEFT JOIN tb_prix p ON a.idarticle = p.idarticle AND u.idunite = p.idunite
                WHERE a.deleted = 0
                ORDER BY u.codearticle, a.designation
            """
            cursor.execute(query)
            articles = cursor.fetchall()
            
            # Pour chaque article, calculer le stock par magasin
            for article in articles:
                idarticle, code, designation, unite, idunite, prix = article
                
                # Calculer le stock pour chaque magasin
                stocks_magasins = []
                total_stock = 0
                
                for idmag, nom_mag in self.magasins:
                    stock = self.calculer_stock_article(idarticle, idunite, idmag)
                    stocks_magasins.append(stock)
                    total_stock += stock
                
                # Construire les valeurs pour le Treeview
                values = [
                    code or "",
                    designation or "",
                    unite or "",
                    self.formater_nombre(prix)
                ]
                
                # Ajouter les stocks par magasin
                for stock in stocks_magasins:
                    values.append(self.formater_nombre(stock))
                
                # Ajouter le total
                values.append(self.formater_nombre(total_stock))
                
                # Déterminer le tag (stock bas ou ok)
                # TODO: Comparer avec qtalert de tb_stock si nécessaire
                tag = 'stock_ok' if total_stock > 0 else 'stock_bas'
                
                # Insérer dans le Treeview
                self.tree.insert("", "end", values=values, tags=(tag,))
            
            # Mettre à jour les labels
            self.label_total_articles.configure(text=f"Total articles: {len(articles)}")
            self.label_derniere_maj.configure(
                text=f"Dernière mise à jour: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            )
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des stocks: {str(e)}")
        finally:
            cursor.close()
            conn.close()
    # --------------------------------------------------------------------------

    def setup_ui(self):
        """Configure l'interface utilisateur de la page de vente."""
    
        # --- Frame principale d'en-tête (Lot 1) ---
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        header_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6, 7), weight=1)
    
        # Référence
        ctk.CTkLabel(header_frame, text="N° Facture:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.entry_ref_vente = ctk.CTkEntry(header_frame, width=150)
        self.entry_ref_vente.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.entry_ref_vente.configure(state="readonly")
    
        # Date
        ctk.CTkLabel(header_frame, text="Date Sortie:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.entry_date_vente = ctk.CTkEntry(header_frame, width=150)
        self.entry_date_vente.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.entry_date_vente.insert(0, datetime.now().strftime("%d/%m/%Y"))
    
        # Magasin
        ctk.CTkLabel(header_frame, text="Magasin de:").grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.combo_magasin = ctk.CTkComboBox(header_frame, width=200, values=["Chargement..."])
        self.combo_magasin.grid(row=0, column=5, padx=5, pady=5, sticky="w")
    
         # Client
        # Champ Entry pour client
        self.entry_client = ctk.CTkEntry(header_frame, width=200, placeholder_text="Client...")
        self.entry_client.grid(row=0, column=7, padx=5, pady=5, sticky="w")

        # Bouton loupe
        self.btn_search_client = ctk.CTkButton(
        header_frame,
        text="🔎",
        width=40,
        command=self.open_recherche_client
        )
        self.btn_search_client.grid(row=0, column=8, padx=2, pady=5, sticky="w")


        # NOUVEAU: Bouton Charger Proforma
        self.btn_charger_proforma = ctk.CTkButton(header_frame, text="📜 Proforma", 
                                    command=self.open_recherche_proforma, width=130,
                                    fg_color="#388e3c", hover_color="#2e7d32")
        self.btn_charger_proforma.grid(row=1, column=6, padx=5, pady=5, sticky="ew") # Col 6
        
        # Bouton Charger facture (Position ajustée)
        btn_charger_bs = ctk.CTkButton(header_frame, text="📂 Charger Facture", 
                                    command=self.ouvrir_recherche_sortie, width=130,
                                    fg_color="#1976d2", hover_color="#1565c0")
        btn_charger_bs.grid(row=1, column=7, padx=5, pady=5, sticky="ew") # Col 7 (Position d'origine)
    
        # Désignation (Colspan ajusté)
        ctk.CTkLabel(header_frame, text="Désignation:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.entry_designation = ctk.CTkEntry(header_frame, width=750)
        self.entry_designation.grid(row=1, column=1, columnspan=5, padx=5, pady=5, sticky="ew") # Colspan 5 (1 à 5)

        # --- Frame d'ajout de Détail (Lot 2) ---
        detail_frame = ctk.CTkFrame(self)
        detail_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        detail_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6), weight=1)
        
        # Article
        ctk.CTkLabel(detail_frame, text="Article:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.entry_article = ctk.CTkEntry(detail_frame, width=300)
        self.entry_article.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.entry_article.configure(state="readonly")
        
        self.btn_recherche_article = ctk.CTkButton(detail_frame, text="🔎 Rechercher", command=self.open_recherche_article)
        self.btn_recherche_article.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        # Quantité
        ctk.CTkLabel(detail_frame, text="Quantité Vente:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.entry_qtvente = ctk.CTkEntry(detail_frame, width=100)
        self.entry_qtvente.grid(row=1, column=2, padx=5, pady=5, sticky="ew")
        # ✅ Raccourci clavier : Entrée pour ajouter l'article
        self.entry_qtvente.bind("<Return>", lambda e: self.valider_detail())
        
        # Unité
        ctk.CTkLabel(detail_frame, text="Unité:").grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.entry_unite = ctk.CTkEntry(detail_frame, width=100)
        self.entry_unite.grid(row=1, column=3, padx=5, pady=5, sticky="ew")
        self.entry_unite.configure(state="readonly")
        
        # Prix Unitaire
        ctk.CTkLabel(detail_frame, text="Prix Unitaire:").grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.entry_prixunit = ctk.CTkEntry(detail_frame, width=100)
        self.entry_prixunit.configure(state="readonly")
        self.entry_prixunit.grid(row=1, column=4, padx=5, pady=5, sticky="ew")

        
        # Boutons d'action
        self.btn_ajouter = ctk.CTkButton(detail_frame, text="➕ Ajouter", command=self.valider_detail, 
                                        fg_color="#2e7d32", hover_color="#1b5e20")
        self.btn_ajouter.grid(row=1, column=5, padx=5, pady=5, sticky="w")
        
        # NOUVEAU: Bouton pour l'ajout en masse des détails du Proforma (Invisible initialement)
        self.btn_ajouter_proforma_bulk = ctk.CTkButton(detail_frame, text="✅ Ajouter Lignes Proforma", command=self.ajouter_details_proforma_en_masse, 
                                            fg_color="#00695c", hover_color="#004d40")

        self.btn_annuler_mod = ctk.CTkButton(detail_frame, text="✖️ Annuler Modif.", command=self.reset_detail_form, 
                                            fg_color="#d32f2f", hover_color="#b71c1c", state="disabled")
        self.btn_annuler_mod.grid(row=1, column=6, padx=5, pady=5, sticky="w")


        # --- Treeview pour les Détails (Lot 3) ---
        tree_frame = ctk.CTkFrame(self)
        tree_frame.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="nsew")
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        
        style = ttk.Style()
        style.theme_use("clam") 
        style.configure("Treeview", rowheight=22, font=('Segoe UI', 8), background="#FFFFFF", foreground="#000000", fieldbackground="#FFFFFF", borderwidth=0)
        style.configure("Treeview.Heading", background="#E8E8E8", foreground="#000000", font=('Segoe UI', 8, 'bold'))
        style.configure("Treeview.Heading", font=('Segoe UI', 8, 'bold'), background="#E8E8E8", foreground="#000000")

        # Colonnes AJOUTÉES: "Montant"
        colonnes = ("ID_Article", "ID_Unite", "ID_Magasin", "Code Article", "Désignation", "Magasin", "Unité", "Prix Unitaire", "Quantité Vente", "Montant")
        self.tree_details = ttk.Treeview(tree_frame, columns=colonnes, show='headings')
        
        for col in colonnes:
            self.tree_details.heading(col, text=col.replace('_', ' ').title())
            if "ID" in col:
                 self.tree_details.column(col, width=0, stretch=False) 
            elif "Quantité" in col or "Prix" in col:
                 self.tree_details.column(col, width=100, anchor='e')
            elif "Montant" in col: 
                 self.tree_details.column(col, width=120, anchor='e')
            elif "Désignation" in col:
                 self.tree_details.column(col, width=350, anchor='w')
            else:
                 self.tree_details.column(col, width=150, anchor='w')
        
        # Scrollbar
        scrollbar = ctk.CTkScrollbar(tree_frame, command=self.tree_details.yview)
        self.tree_details.configure(yscrollcommand=scrollbar.set)
        
        self.tree_details.grid(row=0, column=0, sticky="nsew", padx=(5, 0), pady=5)
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 5), pady=5)
        
        # Bindings
        self.tree_details.bind('<Double-1>', self.modifier_detail)

        # --------------------------------------------------------------------------
        # --- NOUVEAU: Frame des Totaux (Lot 4) ---
        # --------------------------------------------------------------------------
        totals_frame = ctk.CTkFrame(self)
        totals_frame.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")
        totals_frame.grid_columnconfigure(0, weight=1) # Pour le total en lettres
        totals_frame.grid_columnconfigure(1, weight=0) # Pour le total général (à droite)

        # Total en Lettres (Côté gauche)
        ctk.CTkLabel(totals_frame, text="Total en Lettres:", font=ctk.CTkFont(family="Segoe UI", weight="bold")).grid(row=0, column=0, padx=5, pady=5, sticky="nw")
        self.label_total_lettres = ctk.CTkLabel(totals_frame, text="Zéro Ariary", wraplength=700, justify="left", 
                                                font=ctk.CTkFont(family="Segoe UI", slant="italic"))
        self.label_total_lettres.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        
        # Total Général (Côté droit)
        right_total_frame = ctk.CTkFrame(totals_frame, fg_color="transparent")
        right_total_frame.grid(row=0, column=1, rowspan=2, padx=5, pady=5, sticky="ne")
        
        ctk.CTkLabel(right_total_frame, text="TOTAL GÉNÉRAL:", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), fg_color="transparent").pack(side="left", padx=5, pady=5)
        self.label_total_general = ctk.CTkLabel(right_total_frame, text=self.formater_nombre(0.0), 
                                               font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color="#d32f2f")
        self.label_total_general.pack(side="right", padx=5, pady=5)
        # --------------------------------------------------------------------------

        # --- Frame de Boutons (Lot 5 - Anciennement Lot 4) ---
        btn_action_frame = ctk.CTkFrame(self)
        btn_action_frame.grid(row=4, column=0, padx=10, pady=10, sticky="ew")
        btn_action_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.btn_supprimer_ligne = ctk.CTkButton(btn_action_frame, text="🗑️ Supprimer Ligne", command=self.supprimer_detail, 
                                                 fg_color="#d32f2f", hover_color="#b71c1c")
        self.btn_supprimer_ligne.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        btn_nouveau_bs = ctk.CTkButton(btn_action_frame, text="📄 Nouvelle Facture", 
                               command=self.nouveau_facture, 
                               fg_color="#0288d1", hover_color="#01579b")
        btn_nouveau_bs.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.btn_creer_avoir = ctk.CTkButton(
            btn_action_frame, 
            text="📄 Créer Avoir", 
            command=self._ouvrir_page_avoir, 
            fg_color="orange", 
            hover_color="#CC8400"
        )
        self.btn_creer_avoir.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Ajouter l'appel à la vérification des droits à la fin de setup_ui
        self.verifier_droits_admin()
        
        btn_creer_proforma = ctk.CTkButton(btn_action_frame, text="📄 Créer Proforma", 
                               command=self._ouvrir_page_proforma, 
                               fg_color="#29CC00", hover_color="#00CC7A")
        btn_creer_proforma.grid(row=0, column=2, padx=5, pady=5, sticky="w")    

        self.btn_imprimer = ctk.CTkButton(btn_action_frame, text="🖨️ Imprimer Facture", command=self.open_impression_dialogue, 
                                          fg_color="#00695c", hover_color="#004d40", state="disabled")
        self.btn_imprimer.grid(row=0, column=3, padx=5, pady=5, sticky="ew") 
        
        self.btn_enregistrer = ctk.CTkButton(btn_action_frame, text="💾 Enregistrer la Facture", command=self.enregistrer_facture, 
                                             font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"))
        self.btn_enregistrer.grid(row=0, column=4, padx=5, pady=5, sticky="e")

        # Initialisation des totaux
        self.calculer_totaux()
        
    def verifier_droits_admin(self):
        """Vérifie si l'utilisateur est admin pour activer le bouton Avoir."""
        if not self.id_user_connecte:
            self.btn_creer_avoir.configure(state="disabled")
            return

        conn = self.connect_db()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            # On vérifie l'idfonction (1) ou le nomuser (admin)
            cursor.execute("""
                SELECT idfonction, nomuser 
                FROM tb_users 
                WHERE iduser = %s
            """, (self.id_user_connecte,))
        
            user_data = cursor.fetchone()
        
            if user_data:
                id_fonction = user_data[0]
                nom_utilisateur = user_data[1]
            
                # Condition : idfonction == 1 OU nomuser == 'admin'
                if id_fonction == 1 or nom_utilisateur.lower() == "admin":
                    self.btn_creer_avoir.configure(state="normal")
                else:
                    self.btn_creer_avoir.configure(state="disabled")
            else:
                self.btn_creer_avoir.configure(state="disabled")

        except Exception as e:
            print(f"Erreur lors de la vérification des droits : {e}")
            self.btn_creer_avoir.configure(state="disabled")
        finally:
            conn.close()
    
    def sort_tree(self, tree, col):
        """
        Trie les éléments du treeview selon la colonne `col`.
        - Pour 'Montant Total' : tri numérique
        - Pour 'Date' : tri par date au format JJ/MM/AAAA
        Cette fonction bascule l'ordre à chaque appel.
        """
        # Récupérer les enfants
        children = tree.get_children('')
        # Construire liste (valeur, item)
        vals = []
        for k in children:
            v = tree.set(k, col)
            vals.append((v, k))
        reverse = getattr(tree, "_sort_reverse_" + col, False)
        # Détection type
        try:
            if col == "Montant Total":
                def keyfn(x):
                    txt = x[0] or "0"
                    txt = txt.replace(" ", "").replace(".", "").replace(",", ".")
                    return float(txt) if txt not in ("", None) else 0.0
            elif col == "Date":
                from datetime import datetime as _dt
                def keyfn(x):
                    txt = x[0] or ""
                    try:
                        return _dt.strptime(txt, "%d/%m/%Y")
                    except:
                        return _dt.min
            else:
                def keyfn(x):
                    return x[0] or ""
            vals.sort(key=keyfn, reverse=reverse)
        except Exception:
            # fallback to string sort
            vals.sort(reverse=reverse)
        # reposition
        for index, (_, item) in enumerate(vals):
            tree.move(item, '', index)
        # toggle reverse flag
        setattr(tree, "_sort_reverse_" + col, not reverse)

    def open_recherche_client(self):
        fen = ctk.CTkToplevel(self)
        fen.title("Rechercher un client")
        fen.geometry("500x400")
        fen.grab_set()

        frame = ctk.CTkFrame(fen)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(frame, text="Rechercher un client :", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")).pack(pady=5)
        entry_search = ctk.CTkEntry(frame, placeholder_text="Nom client...")
        entry_search.pack(fill="x", padx=5, pady=5)

        # Treeview
        colonnes = ("ID", "Nom Client")
        tree = ttk.Treeview(frame, columns=colonnes, show="headings", height=10)
        
        tree.heading("ID", text="ID")
        tree.heading("Nom Client", text="Nom Client")
        tree.column("ID", width=0, stretch=False)
        tree.column("Nom Client", width=300, anchor="w")
        tree.pack(fill="both", expand=True, pady=5)

        # Fonction chargement
        def charger_clients(filtre=""):
            for item in tree.get_children():
                tree.delete(item)

            conn = self.connect_db()
            if not conn: return
            try:
                cursor = conn.cursor()
                filtre_like = f"%{filtre}%"
                cursor.execute("""
                    SELECT idclient, nomcli FROM tb_client 
                    WHERE deleted = 0 AND nomcli ILIKE %s
                    ORDER BY nomcli
                """, (filtre_like,))
                clients = cursor.fetchall()
                for id_client, nom_client in clients:
                    tree.insert("", "end", values=(id_client, nom_client))
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors du chargement des clients: {str(e)}")
            finally:
                conn.close()

        def rechercher(*args):
            charger_clients(entry_search.get())

        entry_search.bind('<KeyRelease>', rechercher)

        def valider_selection():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Attention", "Veuillez sélectionner un client")
                return

            values = tree.item(selection[0])['values']
            id_client = values[0]
            nom_client = values[1]
            
            # Mise à jour de l'Entry Client
            self.entry_client.delete(0, "end")
            self.entry_client.insert(0, nom_client)

            # Mise à jour de la map (si le client était nouveau, il a déjà été ajouté dans enregistrer_facture)
            self.client_map[nom_client] = id_client

            fen.destroy()

        tree.bind('<Double-Button-1>', lambda e: valider_selection())

        # Boutons
        btn_frame = ctk.CTkFrame(frame)
        btn_frame.pack(fill="x", pady=5)
        btn_annuler = ctk.CTkButton(btn_frame, text="❌ Annuler", command=fen.destroy, fg_color="#d32f2f", hover_color="#b71c1c")
        btn_annuler.pack(side="left", padx=5, pady=5)
        btn_valider = ctk.CTkButton(btn_frame, text="✅ Valider", command=valider_selection, fg_color="#2e7d32", hover_color="#1b5e20")
        btn_valider.pack(side="right", padx=5, pady=5)

        charger_clients()

    def generer_reference(self):
        """Génère la référence de la facture (ex: 2023-FA-00001)."""
        if self.mode_modification and self.idvente_charge:
            return # Ne pas régénérer la référence en mode modification
            
        conn = self.connect_db()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            annee = datetime.now().year
            
            # Trouver la dernière référence de l'année
            cursor.execute("""
                SELECT refvente FROM tb_vente 
                WHERE refvente ILIKE %s 
                ORDER BY id DESC 
                LIMIT 1
            """, (f"%{annee}-FA-%",))
            
            derniere_ref = cursor.fetchone()
            nouveau_numero = 1
            
            if derniere_ref:
                parts = derniere_ref[0].split('-')
                if len(parts) == 3 and parts[1] == 'FA':
                    try:
                        partie_num = parts[-1]
                        nouveau_numero = int(partie_num) + 1
                    except ValueError:
                        nouveau_numero = 1
            
            nouvelle_ref = f"{annee}-FA-{nouveau_numero:05d}"
            
            self.entry_ref_vente.configure(state="normal")
            self.entry_ref_vente.delete(0, "end")
            self.entry_ref_vente.insert(0, nouvelle_ref)
            self.entry_ref_vente.configure(state="readonly")

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la génération de la référence: {str(e)}")
        finally:
            conn.close()

    def charger_magasins(self):
        """Récupère la liste des magasins depuis la base de données."""
        conn = self.connect_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT idmagasin, nom_magasin FROM tb_magasin ORDER BY idmagasin")
                self.magasins = cursor.fetchall()
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"Erreur lors du chargement des magasins: {e}")

    def charger_client(self):
        """Charge uniquement la map des clients pour la recherche"""
        conn = self.connect_db()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT idclient, nomcli FROM tb_client WHERE deleted = 0 ORDER BY nomcli")
            clients = cursor.fetchall()
            self.client_map = {nom: id_ for id_, nom in clients}
            self.client_ids = [id_ for id_, nom in clients]
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des clients: {str(e)}")
        finally:
            conn.close()

    def charger_infos_societe(self):
        """Charge les informations de la société pour l'impression."""
        conn = self.connect_db()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT nomsociete, adressesociete, villesociete, contactsociete, nifsociete, statsociete, cifsociete FROM tb_infosociete LIMIT 1")
            info = cursor.fetchone()
            if info:
                self.infos_societe = {
                    'nomsociete': info[0],
                    'adressesociete': info[1],
                    'villesociete': info[2],
                    'contactsociete': info[3],
                    'nifsociete': info[4],
                    'statsociete': info[5],
                    'cifsociete': info[6]
                }
        except Exception as e:
            messagebox.showwarning("Avertissement", f"Impossible de charger les infos société pour l'impression: {str(e)}")
        finally:
            conn.close()

    def open_recherche_article(self):
        """Ouvre la fenêtre de recherche avec les stocks par magasin en colonnes."""
        self.fenetre_recherche = ctk.CTkToplevel(self)
        self.fenetre_recherche.title("Rechercher un Article - Disponibilité par Magasin")
        self.fenetre_recherche.geometry("1100x600")
        self.fenetre_recherche.grab_set()

        # Zone de saisie
        frame_top = ctk.CTkFrame(self.fenetre_recherche)
        frame_top.pack(fill="x", padx=10, pady=10)
    
        self.entry_search_art = ctk.CTkEntry(frame_top, placeholder_text="Code ou désignation...", width=400)
        self.entry_search_art.pack(side="left", padx=10)
        self.entry_search_art.bind("<KeyRelease>", lambda e: self.actualiser_recherche_article())

        # Préparation des colonnes (Exactement comme dans page_stock.py)
        # On garde les IDs cachés au début pour la sélection
        colonnes_fixes = ("ID_Art", "ID_Uni", "Code", "Désignation", "Unité", "Prix")
        colonnes_magasins = [mag[1] for mag in self.magasins] # Noms des magasins
        self.cols_recherche = colonnes_fixes + tuple(colonnes_magasins) + ("Total",)

        frame_tree = ctk.CTkFrame(self.fenetre_recherche)
        frame_tree.pack(fill="both", expand=True, padx=10, pady=10)

        self.tree_art = ttk.Treeview(frame_tree, columns=self.cols_recherche, show='headings')
    
        for col in self.cols_recherche:
            self.tree_art.heading(col, text=col)
            if "ID_" in col:
                self.tree_art.column(col, width=0, stretch=False) # Cacher les IDs
            else:
                self.tree_art.column(col, width=110, anchor="center")

        self.tree_art.pack(side="left", fill="both", expand=True)
        scroll = ctk.CTkScrollbar(frame_tree, command=self.tree_art.yview)
        self.tree_art.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")

        self.tree_art.bind("<Double-1>", self.on_article_selected)
        self.actualiser_recherche_article()
        
    def actualiser_recherche_article(self):
        """Remplit le tableau avec les calculs de stock par magasin."""
        for item in self.tree_art.get_children():
            self.tree_art.delete(item)

        search_query = self.entry_search_art.get().lower()
        conn = self.connect_db()
        if not conn: return

        try:
            cursor = conn.cursor()
            # Requête SQL (Identique à la logique de page_stock.py)
            query = """
            SELECT DISTINCT ON (u.codearticle)
                a.idarticle, u.idunite, u.codearticle, a.designation, 
                u.designationunite, COALESCE(p.prix, 0)
            FROM tb_article a
            INNER JOIN tb_unite u ON a.idarticle = u.idarticle
            LEFT JOIN tb_prix p ON (a.idarticle = p.idarticle AND u.idunite = p.idunite)
            WHERE a.deleted = 0 AND (LOWER(u.codearticle) LIKE %s OR LOWER(a.designation) LIKE %s)
            ORDER BY u.codearticle, p.dateregistre DESC
        """
            cursor.execute(query, (f"%{search_query}%", f"%{search_query}%"))
            articles = cursor.fetchall()

            for art in articles:
                id_art, id_uni, code, desig, unite, prix = art
                stocks_mag = []
                total_stock = 0

                # Boucle sur les magasins pour remplir les colonnes dynamiques
                for mag in self.magasins:
                    id_mag = mag[0]
                    # Utilisation de votre fonction existante de calcul de stock
                    s = self.calculer_stock_article(id_art, id_uni, id_mag)
                    stocks_mag.append(self.formater_nombre(s))
                    total_stock += s

                # Construction de la ligne : Fixes + Stocks Magasins + Total
                vals = [id_art, id_uni, code, desig, unite, self.formater_nombre(prix)] + \
                   stocks_mag + [self.formater_nombre(total_stock)]
            
                self.tree_art.insert("", "end", values=vals)

        except Exception as e:
            print(f"Erreur recherche article: {e}")
        finally:
            conn.close()
        
        
        
        

    # --- GESTION DU DÉTAIL DE SORTIE (MÉTHODES CORRIGÉES) ---

    def on_article_selected(self, event):
        """Récupère les données depuis le nouveau format de colonnes."""
        selection = self.tree_art.selection()
        if not selection: return

        item = self.tree_art.item(selection[0])
        vals = item['values']

        # Index 0: ID_Art, 1: ID_Uni, 2: Code, 3: Désignation, 4: Unité, 5: Prix
        self.article_selectionne = {
            'idarticle': vals[0],
            'idunite': vals[1],
            'code': vals[2],
            'designation': vals[3],
            'unite': vals[4],
            'prix': self.parser_nombre(str(vals[5]))
        }

        # Mise à jour des champs de l'interface de vente
        for entry, val in [(self.entry_article, f"{vals[2]} - {vals[3]}"), 
                       (self.entry_unite, vals[4]), 
                       (self.entry_prixunit, vals[5])]:
            entry.configure(state="normal")
            entry.delete(0, "end")
            entry.insert(0, val)
            entry.configure(state="readonly")

        self.fenetre_recherche.destroy()

    def format_detail_for_treeview(self, detail):
        """Formate le dictionnaire de détail en tuple pour l'affichage dans le Treeview."""
        # Calcul du montant total
        montant_total = detail['qtvente'] * detail['prixunit'] 
        
        # Colonnes: ("ID_Article", "ID_Unite", "ID_Magasin", "Code Article", "Désignation", "Magasin", "Unité", "Prix Unitaire", "Quantité Vente", "Montant")
        return (
            detail['idarticle'],
            detail['idunite'],
            detail['idmag'],
            detail.get('code_article', 'N/A'),
            detail['nom_article'],
            detail['designationmag'],
            detail['nom_unite'],
            self.formater_nombre(detail['prixunit']),
            self.formater_nombre(detail['qtvente']),
            self.formater_nombre(montant_total) # AJOUT DU MONTANT FORMATÉ
        )

    def charger_details_treeview(self):
        """Charge ou recharge les détails de vente dans le Treeview."""
        for item in self.tree_details.get_children():
            self.tree_details.delete(item)

        for detail in self.detail_vente:
            self.tree_details.insert('', 'end', values=self.format_detail_for_treeview(detail))
            
        self.calculer_totaux() # Recalculer le total après chargement

    def calculer_totaux(self):
        """Calcule et affiche le total général et le total en lettres."""
        total_general = sum(d['qtvente'] * d['prixunit'] for d in self.detail_vente)
        
        # Affichage du total général
        total_format = self.formater_nombre(total_general)
        self.label_total_general.configure(text=total_format)
        
        # Affichage du total en lettres
        total_lettres = nombre_en_lettres_fr(total_general)
        self.label_total_lettres.configure(text=total_lettres)

    def valider_detail(self):
        """Ajoute un article à la liste des détails de vente (ou le modifie)."""
        if not self.article_selectionne:
            messagebox.showwarning("Attention", "Veuillez d'abord sélectionner un article.")
            return

        magasin_selectionne_nom = self.combo_magasin.get()
        idmag = self.magasin_map.get(magasin_selectionne_nom)
        
        if not idmag:
            messagebox.showerror("Erreur", "Veuillez sélectionner un Magasin de sortie valide.")
            return
            
        try:
            qtvente = self.parser_nombre(self.entry_qtvente.get())
            prixunit = self.parser_nombre(self.entry_prixunit.get())
        except ValueError:
            messagebox.showerror("Erreur", "Veuillez entrer une quantité et un prix unitaires valides.")
            return

        if qtvente <= 0 or prixunit <= 0:
            messagebox.showwarning("Attention", "La quantité vendue et le prix unitaire doivent être positifs.")
            return

        # 1. Vérification du Stock (uniquement si ce n'est pas une modification et non le mode proforma)
        # En mode modification, la vérification du stock est ignorée car la sortie a déjà eu lieu.
        # Le mode Proforma est géré par la méthode `ajouter_details_proforma_en_masse`
        if self.index_ligne_selectionnee is None: 
            stock_disponible = self.calculer_stock_article(self.article_selectionne['idarticle'], 
                                                          self.article_selectionne['idunite'], 
                                                          idmag)
            
            if qtvente > stock_disponible:
                if not messagebox.askyesno("Stock Insuffisant", 
                                          f"Stock disponible ({self.formater_nombre(stock_disponible)} {self.article_selectionne['nom_unite']}) est inférieur à la quantité demandée. Continuer l'ajout?"):
                    return


        nouveau_detail = {
            'idarticle': self.article_selectionne['idarticle'],
            'nom_article': self.article_selectionne['nom_article'],
            'idunite': self.article_selectionne['idunite'],
            'nom_unite': self.article_selectionne['nom_unite'],
            'code_article': self.article_selectionne['code_article'],
            'qtvente': qtvente, 
            'prixunit': prixunit, 
            'designationmag': magasin_selectionne_nom,
            'idmag': idmag 
        }

        if self.index_ligne_selectionnee is not None:
            # Mode Modification
            self.detail_vente[self.index_ligne_selectionnee] = nouveau_detail
            self.index_ligne_selectionnee = None
        else:
            # Mode Ajout
            self.detail_vente.append(nouveau_detail)

        self.reset_detail_form()
        self.charger_details_treeview()

    def modifier_detail(self, event):
        """Charge les données d'un détail sélectionné pour modification."""
        selected_item = self.tree_details.focus()
        if not selected_item:
            return

        try:
            self.index_ligne_selectionnee = self.tree_details.index(selected_item)
            detail = self.detail_vente[self.index_ligne_selectionnee]
        except IndexError:
            messagebox.showerror("Erreur", "Erreur lors de la récupération de la ligne.")
            self.reset_detail_form()
            return

        self.article_selectionne = {
            'idarticle': detail['idarticle'],
            'nom_article': detail['nom_article'],
            'idunite': detail['idunite'],
            'nom_unite': detail['nom_unite'],
            'code_article': detail.get('code_article', 'N/A')
        }

        designation_complete = f"[{detail.get('code_article', 'N/A')}] {detail['nom_article']}"
        self.entry_article.configure(state="normal")
        self.entry_article.delete(0, "end")
        self.entry_article.insert(0, designation_complete)
        self.entry_article.configure(state="readonly")

        self.entry_unite.configure(state="normal")
        self.entry_unite.delete(0, "end")
        self.entry_unite.insert(0, detail['nom_unite'])
        self.entry_unite.configure(state="readonly")

        self.entry_qtvente.delete(0, "end")
        self.entry_qtvente.insert(0, self.formater_nombre(detail['qtvente']))

        self.entry_prixunit.configure(state="normal")
        self.entry_prixunit.delete(0, "end")
        self.entry_prixunit.insert(0, self.formater_nombre(detail['prixunit']))
        self.entry_prixunit.configure(state="readonly")
        
        # Mettre à jour le combo magasin (optionnel, on suppose qu'on ne change pas le magasin en cours de modif de ligne)
        self.combo_magasin.set(detail['designationmag'])

        # Mise à jour des boutons
        self.btn_ajouter.configure(text="✔️ Valider Modif.", fg_color="#0288d1", hover_color="#01579b")
        self.btn_annuler_mod.configure(state="normal")
        self.btn_recherche_article.configure(state="disabled")

    def reset_detail_form(self):
        """Réinitialise les champs de saisie de détail."""
        self.article_selectionne = None
        self.index_ligne_selectionnee = None
        
        self.entry_article.configure(state="normal")
        self.entry_article.delete(0, "end")
        self.entry_article.configure(state="readonly")
        
        self.entry_qtvente.delete(0, "end")
        self.entry_prixunit.configure(state="normal")
        self.entry_prixunit.delete(0, "end")
        self.entry_prixunit.configure(state="readonly")
        
        self.entry_unite.configure(state="normal")
        self.entry_unite.delete(0, "end")
        self.entry_unite.configure(state="readonly")
        
        self.btn_ajouter.configure(text="➕ Ajouter", fg_color="#2e7d32", hover_color="#1b5e20")
        self.btn_annuler_mod.configure(state="disabled")
        self.btn_recherche_article.configure(state="normal")

        # Assurer que l'entrée manuelle est active si l'état Proforma est vide
        if not self.details_proforma_a_ajouter:
            self.activer_entree_manuelle()


    def supprimer_detail(self):
        """Supprime la ligne de détail sélectionnée."""
        selected_item = self.tree_details.focus()
        if not selected_item:
            messagebox.showwarning("Attention", "Veuillez sélectionner une ligne à supprimer.")
            return

        if messagebox.askyesno("Confirmation", "Êtes-vous sûr de vouloir supprimer cette ligne de détail?"):
            index = self.tree_details.index(selected_item)
            try:
                self.detail_vente.pop(index)
                self.reset_detail_form()
                self.charger_details_treeview()
            except IndexError:
                messagebox.showerror("Erreur", "Erreur lors de la suppression de la ligne.")

    def ouvrir_recherche_sortie(self):
        """Ouvre une fenêtre pour rechercher une vente existante à charger."""
        if self.mode_modification:
            messagebox.showwarning("Attention", "Veuillez d'abord terminer la modification de la facture actuelle.")
            return

        fenetre = ctk.CTkToplevel(self)
        fenetre.title("Charger une Facture pour Modification")
        fenetre.geometry("1000x500")
        fenetre.grab_set()

        main_frame = ctk.CTkFrame(fenetre)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Zone de recherche
        search_frame = ctk.CTkFrame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(search_frame, text="🔍 Rechercher N° Facture ou Client:").pack(side="left", padx=5)
        entry_search = ctk.CTkEntry(search_frame, placeholder_text="Référence ou Nom client...", width=300)
        entry_search.pack(side="left", padx=5, fill="x", expand=True)
        
        # Treeview
        tree_frame = ctk.CTkFrame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        style = ttk.Style()
        style.configure("Treeview", rowheight=22, font=('Segoe UI', 8), background="#FFFFFF", foreground="#000000", fieldbackground="#FFFFFF", borderwidth=0)
        style.configure("Treeview.Heading", font=('Segoe UI', 8, 'bold'), background="#E8E8E8", foreground="#000000")

        tree.heading("ID", text="ID")
        tree.heading("Ref Vente", text="N° Facture")
        tree.heading("Date", text="Date", command=lambda: self.sort_tree(tree, "Date"))
        tree.heading("Description", text="Description")
        tree.heading("Montant Total", text="Montant Total", command=lambda: self.sort_tree(tree, "Montant Total"))
        tree.heading("Utilisateur", text="Utilisateur")
        tree.heading("Nb Lignes", text="Qté Lignes")
        
        tree.column("ID", width=0, stretch=False)
        tree.column("Ref Vente", width=120, anchor='w')
        tree.column("Date", width=100, anchor='center')
        tree.column("Description", width=250, anchor='w')
        tree.column("Montant Total", width=120, anchor='e')
        tree.column("Utilisateur", width=150, anchor='w')
        tree.column("Nb Lignes", width=80, anchor='center')

        scrollbar = ctk.CTkScrollbar(tree_frame, command=tree.yview)
        tree.tag_configure("impaye", foreground="red")
        tree.tag_configure("paye", foreground="black")
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        var_filtre_impaye = ctk.BooleanVar(value=False)
        chk_impaye = ctk.CTkCheckBox(search_frame, text="Afficher seulement impayées", variable=var_filtre_impaye)
        chk_impaye.pack(side='right', padx=5)

        def _on_filtre_change(*args):
            charger_vente(entry_search.get())
        
        try:
            var_filtre_impaye.trace_add('write', _on_filtre_change)
        except Exception:
            try:
                var_filtre_impaye.trace('w', _on_filtre_change)
            except Exception:
                pass

        def charger_vente(filtre=""):
            conn = self.connect_db()
            if not conn: return
            try:
                cursor = conn.cursor()
                
                filtre_impaye = var_filtre_impaye.get()
                
                # Début de la requête SQL
                sql = """
                    SELECT 
                        v.id, v.refvente, v.dateregistre, v.description, c.nomcli, 
                        (u.nomuser || ' ' || u.prenomuser) as utilisateur,
                        COALESCE(v.totmtvente, 0) as total_montant,
                        COUNT(vd.id) as nb_lignes
                    FROM 
                        tb_vente v
                    LEFT JOIN 
                        tb_client c ON v.idclient = c.idclient
                    INNER JOIN 
                        tb_users u ON v.iduser = u.iduser
                    LEFT JOIN
                        tb_ventedetail vd ON v.id = vd.idvente
                    WHERE 
                        v.deleted = 0 
                        AND (v.refvente ILIKE %s OR c.nomcli ILIKE %s)
                """
                
                # Ajout du filtre impayé
                # Note: La logique de paiement n'est pas détaillée ici, mais on assume un champ 'paye' ou une table 'paiement'
                # Pour cet exemple, je vais simplifier en supposant qu'une facture n'est jamais impayée dans tb_vente (pas de gestion de caisse)
                # Si vous avez une table de paiement, vous devriez ajuster cette clause WHERE
                # Pour l'instant, le filtre impayé est désactivé / à implémenter si la table 'paiement' est disponible.

                sql += """
                    GROUP BY
                        v.id, v.refvente, v.dateregistre, v.description, c.nomcli, utilisateur
                    ORDER BY 
                        v.dateregistre DESC
                """
                
                filtre_like = f"%{filtre}%"
                cursor.execute(sql, (filtre_like, filtre_like))
                ventes = cursor.fetchall()

                # Clear existing items
                for item in tree.get_children():
                    tree.delete(item)
                    
                for vente in ventes:
                    idvente, refvente, dateregistre, description, nomcli, utilisateur, total_montant, nb_lignes = vente
                    
                    date_str = dateregistre.strftime("%d/%m/%Y")
                    montant_str = self.formater_nombre(total_montant)
                    
                    tag = "paye" # À ajuster avec la vraie logique de paiement

                    tree.insert('', 'end', values=(
                        idvente, 
                        refvente, 
                        date_str, 
                        f"{description} ({nomcli or 'Client Divers'})", 
                        montant_str, 
                        utilisateur, 
                        nb_lignes
                    ), tags=(tag,))

            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors du chargement: {str(e)}")
            finally:
                if 'cursor' in locals() and cursor: cursor.close()
                if conn: conn.close()

            tree.tag_configure("impaye", foreground="red")
            tree.tag_configure("paye", foreground="black")

        def rechercher(*args):
            charger_vente(entry_search.get())

        entry_search.bind('<KeyRelease>', rechercher)

        def valider_selection():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Attention", "Veuillez sélectionner un bon de sortie")
                return

            values = tree.item(selection[0])['values']
            idvente = values[0]
            fenetre.destroy()
            self.charger_vente_modification(idvente)

        tree.bind('<Double-Button-1>', lambda e: valider_selection())

        # Boutons
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x")
        btn_annuler = ctk.CTkButton(btn_frame, text="❌ Annuler", command=fenetre.destroy, fg_color="#d32f2f", hover_color="#b71c1c")
        btn_annuler.pack(side="left", padx=5, pady=5)
        btn_valider = ctk.CTkButton(btn_frame, text="✅ Charger", command=valider_selection, fg_color="#2e7d32", hover_color="#1b5e20")
        btn_valider.pack(side="right", padx=5, pady=5)
        
        charger_vente()


    def charger_vente_modification(self, idvente: int):
        """Charge une vente existante pour modification/consultation."""
        self.nouveau_facture() # Reset complet de l'interface
        
        conn = self.connect_db()
        if not conn: return

        try:
            cursor = conn.cursor()

            # 1. Charger l'entête
            sql_vente = """
                SELECT v.id, v.refvente, v.dateregistre, v.description, c.nomcli, v.idclient
                FROM tb_vente v 
                LEFT JOIN tb_client c ON v.idclient = c.idclient 
                WHERE v.id = %s
            """
            cursor.execute(sql_vente, (idvente,))
            vente = cursor.fetchone()

            if not vente:
                messagebox.showerror("Erreur", "Facture introuvable.")
                return

            idvente, refvente, dateregistre, description, nomcli, idclient = vente

            # 2. Charger les détails
            sql_details = """
                SELECT 
                    vd.idmag, m.designationmag, vd.idarticle, u.codearticle, a.designation,
                    vd.idunite, u.designationunite, vd.qtvente, vd.prixunit
                FROM tb_ventedetail vd 
                INNER JOIN tb_article a ON vd.idarticle = a.idarticle 
                INNER JOIN tb_unite u ON vd.idunite = u.idunite
                INNER JOIN tb_magasin m ON vd.idmag = m.idmag
                WHERE vd.idvente = %s
            """
            cursor.execute(sql_details, (idvente,))
            details = cursor.fetchall()
            
            # 3. Mettre à jour l'interface
            self.idvente_charge = idvente
            self.mode_modification = True
            
            self.entry_ref_vente.configure(state="normal")
            self.entry_ref_vente.delete(0, "end")
            self.entry_ref_vente.insert(0, refvente)
            self.entry_ref_vente.configure(state="readonly")
            
            self.entry_date_vente.delete(0, "end")
            self.entry_date_vente.insert(0, dateregistre.strftime("%d/%m/%Y"))
            
            self.entry_designation.delete(0, "end")
            self.entry_designation.insert(0, description)
            
            self.entry_client.delete(0, "end")
            self.entry_client.insert(0, nomcli or "Client Divers")
            self.client_map[nomcli or "Client Divers"] = idclient

            self.detail_vente = []
            for row in details:
                idmag_d, designationmag, idarticle, codearticle, designation, idunite, designationunite, qtvente, prixunit = row
                self.detail_vente.append({
                    'idmag': idmag_d,
                    'designationmag': designationmag,
                    'idarticle': idarticle,
                    'code_article': codearticle,
                    'nom_article': designation,
                    'idunite': idunite,
                    'nom_unite': designationunite,
                    'qtvente': qtvente,
                    'prixunit': prixunit
                })

            self.charger_details_treeview()

            # Mettre à jour les boutons
            self.btn_enregistrer.configure(text="📝 Modifier la Facture", fg_color="#ff9800", hover_color="#f57c00", state="normal")
            self.btn_imprimer.configure(state="normal")
            self.btn_charger_proforma.configure(state="disabled") # Désactiver chargement proforma en modif

            messagebox.showinfo("Chargement Réussi", f"La Facture N° {refvente} a été chargée pour modification.")

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement de la facture: {str(e)}")
            self.nouveau_facture()
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()

    def nouveau_facture(self):
        """Réinitialise le formulaire pour une nouvelle facture/bon de sortie."""
        self.generer_reference()
        self.entry_date_vente.delete(0, "end")
        self.entry_date_vente.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.entry_designation.delete(0, "end")
        self.entry_client.delete(0, "end")
        self.detail_vente = []
        self.charger_details_treeview() # Recharge le treeview vide
        self.idvente_charge = None
        self.mode_modification = False
        self.btn_enregistrer.configure(state="normal", text="💾 Enregistrer la Facture", fg_color="#2196f3", hover_color="#1976d2")
        self.btn_imprimer.configure(state="disabled")
        self.btn_charger_proforma.configure(state="normal") # Réactiver le bouton Proforma
        
        # Assurer que l'état Proforma est réinitialisé
        self.reset_proforma_state()


    def enregistrer_facture(self):
        """Sauvegarde ou modifie la facture dans la base de données."""
    
        # ✅ PROTECTION CONTRE LE DOUBLE-CLIC
        if hasattr(self, '_enregistrement_en_cours') and self._enregistrement_en_cours:
            print("⚠️ Enregistrement déjà en cours, ignoré")
            return
    
        self._enregistrement_en_cours = True
        self.btn_enregistrer.configure(state="disabled")
    
        try:
            if not self.detail_vente:
                messagebox.showwarning("Attention", "Veuillez ajouter des articles avant d'enregistrer.")
                return
        
            # VÉRIFICATION CRITIQUE: id_user_connecte ne doit pas être None
            if self.id_user_connecte is None:
                messagebox.showerror("Erreur Critique", 
                               "Aucun utilisateur connecté. Impossible d'enregistrer la facture.\n"
                               "Veuillez vous reconnecter.")
                return
        
            ref_vente = self.entry_ref_vente.get()
            date_vente_str = self.entry_date_vente.get()
            description = self.entry_designation.get().strip()
            client_nom = self.entry_client.get().strip()
        
            if client_nom == "":
                messagebox.showerror("Erreur", "Veuillez entrer ou choisir un client.")
                return

            # Connexion DB
            conn = self.connect_db()
            if not conn: return

            # 1. Gestion du Client
            idclient = self.client_map.get(client_nom)
            if not idclient: 
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO tb_client (nomcli, deleted) 
                        VALUES (%s, 0) RETURNING idclient
                    """, (client_nom,))
                    idclient = cursor.fetchone()[0]
                    conn.commit()
                    self.client_map[client_nom] = idclient
                except Exception as e:
                    conn.rollback()
                    messagebox.showerror("Erreur", f"Impossible d'ajouter le client : {e}")
                    return
        
            if not idclient:
                messagebox.showerror("Erreur", "Client non sélectionné ou invalide.")
                return

            try:
                cursor = conn.cursor()
                try:
                    # Capturer la date saisie et ajouter l'heure précise actuelle
                    date_vente = datetime.strptime(date_vente_str, "%d/%m/%Y").replace(hour=datetime.now().hour, minute=datetime.now().minute, second=datetime.now().second)
                except ValueError:
                    messagebox.showerror("Erreur de Date", "Format de date invalide (attendu: JJ/MM/AAAA).")
                    return
            
                # CALCUL DU TOTAL GÉNÉRAL
                total_general = sum(d['qtvente'] * d['prixunit'] for d in self.detail_vente)
            
                # DEBUG
                print(f"📝 Enregistrement facture:")
                print(f"   - Référence: {ref_vente}")
                print(f"   - iduser: {self.id_user_connecte}")
                print(f"   - idclient: {idclient}")
                print(f"   - Total: {total_general}")
            
                # --- 2. Enregistrement/Modification de l'entête ---
                if self.mode_modification and self.idvente_charge:
                    # Mode Modification
                    idvente = self.idvente_charge
                    sql_vente = """
                        UPDATE tb_vente 
                        SET dateregistre = %s, 
                            description = %s, 
                            idclient = %s, 
                            iduser = %s,
                            totmtvente = %s,
                            dateupdate = NOW() 
                        WHERE id = %s
                    """
                    params = (date_vente, description, idclient, self.id_user_connecte, total_general, idvente)
                    print(f"🔄 UPDATE avec params: {params}")
                    cursor.execute(sql_vente, params)

                    # Suppression des anciens détails pour réinsertion
                    cursor.execute("DELETE FROM tb_ventedetail WHERE idvente = %s", (idvente,))
                
                else:
                    # Mode Ajout
                    sql_vente = """
                        INSERT INTO tb_vente (refvente, dateregistre, description, iduser, idclient, totmtvente, statut, deleted) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 0) 
                        RETURNING id
                    """
                    params = (ref_vente, date_vente, description, self.id_user_connecte, idclient, total_general, 'EN_ATTENTE')
                    print(f"➕ INSERT avec params: {params}")
                    cursor.execute(sql_vente, params)
                    idvente = cursor.fetchone()[0]
                    self.derniere_idvente_enregistree = idvente
                    self.idvente_charge = idvente
                    self.mode_modification = True
                
                    print(f"✅ Facture créée avec ID: {idvente}")

                # --- 3. Enregistrement des détails ---
                sql_vente_detail = """
                    INSERT INTO tb_ventedetail (idvente, idmag, idarticle, idunite, qtvente, prixunit) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                details_a_inserer = []
                for detail in self.detail_vente:
                    details_a_inserer.append((
                        idvente,
                        detail['idmag'],
                        detail['idarticle'],
                        detail['idunite'],
                        detail['qtvente'],
                        detail['prixunit']
                    ))

                cursor.executemany(sql_vente_detail, details_a_inserer)

                # 4. Commit et mise à jour de l'interface
                conn.commit()
            
                message = f"Facture N° {ref_vente} enregistrée avec succès.\nMontant total: {self.formater_nombre(total_general)} Ariary"
                if self.mode_modification:
                    message = f"Facture N° {ref_vente} modifiée avec succès.\nMontant total: {self.formater_nombre(total_general)} Ariary"
            
                messagebox.showinfo("Succès", message)
            
                # Mettre à jour les boutons après enregistrement
                self.btn_enregistrer.configure(
                    text="🔄 Modifier la Facture", 
                    fg_color="#ff9800", 
                    hover_color="#f57c00",
                    state="normal"
                )
                self.btn_imprimer.configure(state="normal")
                self.btn_charger_proforma.configure(state="disabled")

            except psycopg2.errors.UniqueViolation as e:
                # ✅ GESTION SPÉCIFIQUE DE L'ERREUR DE DOUBLON
                conn.rollback()
                messagebox.showerror(
                    "Erreur de doublon", 
                    f"La facture N° {ref_vente} existe déjà dans la base de données.\n\n"
                    f"Impossible de créer un doublon.\n\n"
                    f"Détails: {e}"
                )
                print(f"❌ ERREUR DOUBLON: {e}")
            except psycopg2.Error as e:
                conn.rollback()
                messagebox.showerror("Erreur SQL", f"Erreur lors de l'enregistrement/modification de la facture: {e}")
                print(f"❌ ERREUR SQL: {e}")
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Erreur", f"Une erreur inattendue s'est produite: {e}")
                print(f"❌ ERREUR: {e}")
                import traceback
                traceback.print_exc()
            finally:
                if 'cursor' in locals() and cursor: cursor.close()
                if conn: conn.close()
    
        finally:
            # ✅ TOUJOURS RÉACTIVER LE BOUTON ET RESET LE FLAG
            self._enregistrement_en_cours = False
            self.btn_enregistrer.configure(state="normal")

    def open_impression_dialogue(self):
        """Ouvre un dialogue pour choisir le format d'impression et lance l'impression."""
        # Vérification de l'ID de la vente
        if not self.idvente_charge and not self.derniere_idvente_enregistree:
            messagebox.showwarning("Attention", "Veuillez d'abord enregistrer ou charger une facture pour imprimer.")
            return

        idvente = self.idvente_charge or self.derniere_idvente_enregistree
    
        # DEBUG: Afficher l'ID de la vente
        print(f"🔍 DEBUG - ID Vente à imprimer: {idvente}")
    
        # Récupération des données
        data = self.get_data_facture(idvente)
    
        # DEBUG: Vérifier les données récupérées
        if data:
            print(f"✅ Données récupérées avec succès")
            print(f"   - Vente: {data.get('vente')}")
            print(f"   - Nombre de détails: {len(data.get('details', []))}")
        else:
            print(f"❌ Aucune donnée récupérée pour idvente={idvente}")
    
        if not data or not data.get('vente'):
            messagebox.showerror("Erreur", f"Impossible de récupérer les données de la facture (ID: {idvente}).\n\nVérifiez que la facture a bien été enregistrée.")
            return
        
        try:
            choice_dialog = SimpleDialogWithChoice(
                self, 
                title="Choix du format d'impression", 
                message="Veuillez sélectionner le format de la facture à imprimer:"
            )
            result = choice_dialog.result
        except Exception as e:
            messagebox.showerror("Erreur de Dialogue", f"Impossible d'ouvrir la fenêtre de choix d'impression : {e}")
            return
        
        if result == "A5 PDF (Paysage)":
            filename = f"Facture_{data['vente']['refvente']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            self.generate_pdf_a5(data, filename)
            self.open_file(filename)
            messagebox.showinfo("Impression PDF", f"Le fichier PDF '{filename}' a été généré avec succès.")
        elif result == "Ticket 80mm":
            filename = f"Ticket_{data['vente']['refvente']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            self.generate_ticket_80mm(data, filename)
            self.open_file(filename)
            messagebox.showinfo("Impression Ticket", f"Le fichier Ticket '{filename}' (texte brut) a été généré avec succès.")
        else:
            messagebox.showinfo("Annulation", "Impression annulée.")


    def open_file(self, filename):
        """Ouvre le fichier généré avec le programme par défaut."""
        try:
            if sys.platform == 'win32':
                os.startfile(filename)
            elif sys.platform == 'darwin':
                os.system(f'open "{filename}"')
            else:
                os.system(f'xdg-open "{filename}"')
        except Exception as e:
            pass # Ignorer les erreurs d'ouverture de fichier

    def get_data_facture(self, idvente: int) -> Optional[Dict[str, Any]]:
        """Récupère toutes les données nécessaires pour l'impression d'une facture."""
        print(f"\n{'='*60}")
        print(f"🔍 GET_DATA_FACTURE - ID Vente: {idvente}")
        print(f"{'='*60}")
    
        conn = self.connect_db()
        if not conn:
            print("❌ ERREUR: Connexion DB impossible")
            return None

        data = {
            'societe': self.infos_societe,
            'vente': None,
            'utilisateur': None,
            'details': []
        }
    
        try:
            cursor = conn.cursor()

            # DEBUG: Vérifier que l'ID existe dans la table
            cursor.execute("SELECT COUNT(*) FROM tb_vente WHERE id = %s", (idvente,))
            count = cursor.fetchone()[0]
            print(f"📊 Nombre de ventes trouvées avec id={idvente}: {count}")

            # 1. Infos Vente & Client
            sql_vente = """
                SELECT 
                    v.refvente, v.dateregistre, v.description, 
                    u.nomuser, u.prenomuser, 
                    c.nomcli, c.adressecli, c.contactcli
                FROM tb_vente v 
                INNER JOIN tb_users u ON v.iduser = u.iduser 
                LEFT JOIN tb_client c ON v.idclient = c.idclient 
                WHERE v.id = %s
            """
            print(f"📝 Exécution requête vente avec id={idvente}")
            cursor.execute(sql_vente, (idvente,))
            result = cursor.fetchone()
        
            if not result:
                print(f"❌ ERREUR: Aucune vente trouvée pour id={idvente}")
                return None
        
            print(f"✅ Vente trouvée: {result[0]}")
        
            (refvente, dateregistre, description, nomuser, prenomuser, nomcli, adressecli, contactcli) = result

            data['vente'] = {
                'refvente': refvente,
                'dateregistre': dateregistre.strftime("%d/%m/%Y %H:%M"),
                'description': description,
            }
            data['utilisateur'] = {
                'nomuser': nomuser,
                'prenomuser': prenomuser,
            }
            data['client'] = {
                'nomcli': nomcli or "Client Divers",
                'adressecli': adressecli or "N/A",
                'contactcli': contactcli or "N/A",
            }
        
            # 2. Détails de vente
            sql_details = """
                SELECT 
                    u.codearticle, a.designation, u.designationunite, 
                    vd.qtvente, vd.prixunit, m.designationmag
                FROM tb_ventedetail vd 
                INNER JOIN tb_article a ON vd.idarticle = a.idarticle 
                INNER JOIN tb_unite u ON vd.idunite = u.idunite
                INNER JOIN tb_magasin m ON vd.idmag = m.idmag
                WHERE vd.idvente = %s
                ORDER BY a.designation
            """
            print(f"📝 Exécution requête détails pour idvente={idvente}")
            cursor.execute(sql_details, (idvente,))
            details_rows = cursor.fetchall()
        
            print(f"📦 Nombre de détails trouvés: {len(details_rows)}")
        
            data['details'] = [
                {
                    'code_article': row[0],
                    'designation': row[1],
                    'unite': row[2],
                    'qte': row[3],
                    'prixunit': row[4],
                    'magasin': row[5],
                    'montant': row[3] * row[4]
                }
                for row in details_rows
            ]
        
            print(f"✅ Données complètes récupérées avec succès")
            print(f"{'='*60}\n")

            return data

        except Exception as e:
            print(f"❌ ERREUR CRITIQUE dans get_data_facture: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Erreur", f"Erreur lors de la récupération des données de facture : {e}")
            return None
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if conn:
                conn.close()

    # ==============================================================================
    # MÉTHODES D'IMPRESSION PDF A5
    # ==============================================================================

    def generate_pdf_a5(self, data: Dict[str, Any], filename: str):
        """
        Génère le PDF de la facture au format A5 avec le modèle canvas amélioré.
        Utilise les données existantes du dictionnaire data.
        """
        from reportlab.lib.pagesizes import A5
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.platypus import Table, TableStyle, Paragraph

        # ✅ CRÉATION DU PDF AVEC CANVAS
        c = canvas.Canvas(filename, pagesize=A5)
        width, height = A5

        # ✅ 1. CADRE DU VERSET (Haut de page avec bordure)
        verset = "Ankino amin'ny Jehovah ny asanao dia ho lavorary izay kasainao. Ohabolana 16:3"
        c.setLineWidth(1)
        c.rect(10*mm, height - 15*mm, width - 20*mm, 8*mm)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(width/2, height - 12.5*mm, verset)

        # ✅ 2. EN-TÊTE DEUX COLONNES
        styles = getSampleStyleSheet()
        style_p = ParagraphStyle('style_p', fontSize=9, leading=11, parent=styles['Normal'])

        societe = data['societe']
        utilisateur = data['utilisateur']
        client = data['client']
        vente = data['vente']

        # Adapter les clés de données si nécessaire
        nomsociete = societe.get('nomsociete', 'N/A')
        adressesociete = societe.get('adressesociete') or societe.get('adresse', 'N/A')
        contactsociete = societe.get('contactsociete') or societe.get('tel', 'N/A')
        nifsociete = societe.get('nifsociete') or societe.get('nif', 'N/A')
        statsociete = societe.get('statsociete') or societe.get('stat', 'N/A')

        gauche_text = f"<b>{nomsociete}</b><br/>{adressesociete}<br/>TEL: {contactsociete}<br/>NIF: {nifsociete} | STAT: {statsociete}"

        # Gérer si utilisateur est un dict ou une string
        if isinstance(utilisateur, dict):
            user_name = f"{utilisateur.get('prenomuser', '')} {utilisateur.get('nomuser', '')}"
        else:
            user_name = str(utilisateur)

        droite_text = f"<b>Facture N°: {vente['refvente']}</b><br/>{vente['dateregistre']}<br/><b>CLIENT: {client['nomcli']}</b><br/><font size='8'>Op: {user_name}</font>"

        gauche = Paragraph(gauche_text, style_p)
        droite = Paragraph(droite_text, style_p)

        header_table = Table([[gauche, droite]], colWidths=[64*mm, 64*mm])
        header_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))

        header_table.wrapOn(c, width, height)
        header_table.drawOn(c, 10*mm, height - 42*mm)

        # ✅ 3. TABLEAU DES ARTICLES
        table_top = height - 52*mm
        table_bottom = 65*mm
        frame_height = table_top - table_bottom

        row_height = 5.5*mm
        max_rows = int(frame_height / row_height)

        # Préparer les données du tableau
        table_data = [['QTE', 'UNITE', 'DESIGNATION', 'PU TTC', 'MONTANT']]

        total_montant = 0
        num_articles = 0
        for detail in data['details']:
            montant = detail.get('montant_ttc', detail.get('montant', 0))
            total_montant += montant
            num_articles += 1
            table_data.append([
                str(int(detail.get('qte', 0))),
                str(detail.get('unite', '')),
                str(detail.get('designation', '')),
                self.formater_nombre(detail.get('prixunit', 0)),
                self.formater_nombre(montant)
            ])

        # Ajouter des lignes vides
        montant_fmg = int(total_montant * 5)
        empty_rows_needed = max_rows - 1 - num_articles - 2
        for i in range(max(0, empty_rows_needed)):
            table_data.append(['', '', '', '', ''])

        # Totaux
        table_data.append(['', '', 'TOTAL Ar:', self.formater_nombre(total_montant), ''])
        table_data.append(['', '', 'Fmg:', self.formater_nombre(montant_fmg), ''])

        col_widths = [12*mm, 15*mm, 62*mm, 19.5*mm, 19.5*mm]

        # Dessiner le cadre et lignes
        c.setLineWidth(1)
        c.rect(10*mm, table_bottom, width - 20*mm, frame_height)

        x_pos = 10*mm
        for w in col_widths[:-1]:
            x_pos += w
            c.line(x_pos, table_top, x_pos, table_bottom)

        # Créer le tableau avec hauteurs proportionnelles
        actual_row_height = frame_height / len(table_data)
        row_heights = [actual_row_height] * len(table_data)

        articles_table = Table(table_data, colWidths=col_widths, rowHeights=row_heights)
        articles_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('BACKGROUND', (0, -2), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -3), 8),
            ('FONTSIZE', (0, -2), (-1, -1), 9),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('LINEABOVE', (0, -2), (-1, -2), 1, colors.black),
            ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 0), (2, 0), 'LEFT'),
            ('ALIGN', (2, -2), (2, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 1),
            ('RIGHTPADDING', (3, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))

        articles_table.wrapOn(c, width, height)
        assert actual_row_height, 'actual_row_height must not be None'
        actual_total_height = len(table_data) * actual_row_height
        articles_table.drawOn(c, 10*mm, table_top - actual_total_height)

        # ✅ 4. TEXTE EN LETTRES
        montant_lettres = nombre_en_lettres_fr(int(total_montant)).upper()
        text_y = table_bottom - 18*mm
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(width/2, text_y, f"ARRETE A LA SOMME DE {montant_lettres} ARIARY")

        # ✅ 5. MENTION LÉGALE
        c.setFont("Helvetica-Oblique", 8)
        c.drawCentredString(width/2, text_y - 5*mm, "Nous déclinons la responsabilité des marchandises non livrées au-delà de 5 jours")

        # ✅ 6. SIGNATURES
        sig_y = 15*mm
        c.setFont("Helvetica-Bold", 10)
        c.drawString(15*mm, sig_y, "Le Client")
        c.drawCentredString(width/2, sig_y, "Le Caissier")
        c.drawString(width - 35*mm, sig_y, "Le Magasinier")

        # ✅ SAUVEGARDER
        try:
            c.save()
            print(f"✅ PDF généré avec succès : {filename}")
        except Exception as e:
            print(f"❌ Erreur PDF : {e}")
            import traceback
            traceback.print_exc()
        
    # ==============================================================================
    # MÉTHODES D'IMPRESSION TICKET 80MM (Texte Brut)
    # ==============================================================================

    def generate_ticket_80mm(self, data: Dict[str, Any], filename: str):
        """Génère un fichier texte brut pour un ticket de caisse 80mm."""
        MAX_WIDTH = 40 # Largeur typique pour 80mm (environ 40-42 caractères)
        societe = data['societe']
        vente = data['vente']
        client = data['client']
        details = data['details']

        def center(text):
            return text.center(MAX_WIDTH)

        def line():
            return "-" * MAX_WIDTH

        def format_detail_line(designation, unite, qte, prixunit, montant_total):
            """Formate une ligne de détail pour le ticket."""
            lines = []
            designation_lines = textwrap.wrap(designation, MAX_WIDTH)
            lines.extend(designation_lines)
            
            qte_str = str(int(qte))
            prixunit_str = self.formater_nombre(prixunit)
            
            qte_pu_line = f"{qte_str} {unite} @ {prixunit_str}"
            montant_total_str = self.formater_nombre(montant_total)

            # Tente de mettre la quantité/prix et le montant sur la même ligne
            if len(qte_pu_line) + len(montant_total_str) + 1 <= MAX_WIDTH:
                 lines.append(qte_pu_line.ljust(MAX_WIDTH - len(montant_total_str)) + montant_total_str.rjust(len(montant_total_str)))
            else:
                 lines.append(qte_pu_line)
                 lines.append(montant_total_str.rjust(MAX_WIDTH)) # Montant sur la ligne suivante

            return lines

        content = []

        # --- EN-TÊTE SOCIÉTÉ ---
        content.append(center(societe.get('nomsociete', 'NOM SOCIÉTÉ')))
        content.append(center(societe.get('adressesociete', 'N/A')))
        content.append(center(f"Tél: {societe.get('contactsociete', 'N/A')}"))
        content.append(line())

        # --- INFOS FACTURE ---
        content.append(center(f"FACTURE N° {vente['refvente']}"))
        content.append(f"Date: {vente['dateregistre']}")
        content.append(f"Client: {client['nomcli']}")
        if vente['description']:
             content.append(f"Désign: {vente['description']}")
        content.append(line())

        # --- DÉTAILS ---
        total_general = 0.0
        for detail in details:
            montant = detail['montant']
            total_general += montant
            content.extend(format_detail_line(
                detail['designation'], 
                detail['unite'], 
                detail['qte'], 
                detail['prixunit'], 
                montant
            ))
            content.append("-" * MAX_WIDTH) # Ligne de séparation courte entre articles

        # --- TOTAL ---
        content.append(line())
        total_label = "TOTAL À PAYER:"
        total_montant_str = self.formater_nombre(total_general)
        
        # Alignement Total
        total_line = total_label.ljust(MAX_WIDTH - len(total_montant_str)) + total_montant_str
        content.append(total_line)
        content.append(line())

        # TOTAL EN LETTRES
        total_lettres = nombre_en_lettres_fr(total_general)
        content.append(center("TOTAL EN LETTRES"))
        lines_en_lettres = textwrap.wrap(total_lettres, MAX_WIDTH, subsequent_indent='  ')
        content.extend(lines_en_lettres)
        content.append(line())

        # --- PIED DE PAGE ---
        content.append(center(vente['description']))
        content.append("\n")
        content.append(center("Merci de votre achat !"))
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))

    # ==============================================================================
    # GESTION DES PROFORMAS (NOUVEAU)
    # ==============================================================================

    def open_recherche_proforma(self):
        """Ouvre une fenêtre de dialogue pour rechercher et sélectionner un proforma 'A Facturer'."""
        if self.mode_modification:
            messagebox.showwarning("Attention", "Veuillez d'abord terminer la modification de la facture actuelle.")
            return

        fenetre = ctk.CTkToplevel(self)
        fenetre.title("Charger un Proforma à Facturer")
        fenetre.geometry("900x500")
        fenetre.grab_set()

        main_frame = ctk.CTkFrame(fenetre)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Zone de recherche
        search_frame = ctk.CTkFrame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(search_frame, text="🔍 Rechercher N° Proforma ou Client:").pack(side="left", padx=5)
        entry_search = ctk.CTkEntry(search_frame, placeholder_text="Référence ou Nom client...", width=300)
        entry_search.pack(side="left", padx=5, fill="x", expand=True)
        
        # Treeview
        tree_frame = ctk.CTkFrame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        style = ttk.Style()
        style.configure("Treeview", rowheight=22, font=('Segoe UI', 8), background="#FFFFFF", foreground="#000000", fieldbackground="#FFFFFF", borderwidth=0)
        style.configure("Treeview.Heading", font=('Segoe UI', 8, 'bold'), background="#E8E8E8", foreground="#000000")

        tree.heading("ID", text="ID")
        tree.heading("Ref Proforma", text="N° Proforma")
        tree.heading("Date", text="Date")
        tree.heading("Client", text="Client")
        tree.heading("Montant Total", text="Montant Total")
        tree.heading("Nb Lignes", text="Qté Lignes")
        
        tree.column("ID", width=0, stretch=False)
        tree.column("Ref Proforma", width=120, anchor='w')
        tree.column("Date", width=100, anchor='center')
        tree.column("Client", width=250, anchor='w')
        tree.column("Montant Total", width=120, anchor='e')
        tree.column("Nb Lignes", width=80, anchor='center')

        scrollbar = ctk.CTkScrollbar(tree_frame, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        def charger_proforma(filtre=""):
            conn = self.connect_db()
            if not conn: return
            try:
                cursor = conn.cursor()
                
                # Récupère tous les proformas avec statut 'A Facturer'
                sql = """
                    SELECT p.idprof, p.refprof, p.dateprof, c.nomcli, 
                           SUM(pd.qtlivprof * pd.prixunit) as total_montant, 
                           COUNT(pd.idprof) as nb_lignes
                    FROM tb_proforma p 
                    INNER JOIN tb_client c ON p.idclient = c.idclient 
                    LEFT JOIN tb_proformadetail pd ON p.idprof = pd.idprof 
                    WHERE p.deleted = 0 
                    AND p.statut = '✅ A Facturer'
                    AND (p.refprof ILIKE %s OR c.nomcli ILIKE %s)
                    GROUP BY p.idprof, p.refprof, p.dateprof, c.nomcli 
                    ORDER BY p.dateprof DESC
                """
                filtre_like = f"%{filtre}%"
                cursor.execute(sql, (filtre_like, filtre_like))
                proformas = cursor.fetchall()

                # Clear existing items
                for item in tree.get_children():
                    tree.delete(item)
                    
                for prof in proformas:
                    idprof, refprof, dateregistre, nomcli, total_montant, nb_lignes = prof
                    
                    date_str = dateregistre.strftime("%d/%m/%Y")
                    montant_str = self.formater_nombre(total_montant)

                    tree.insert('', 'end', values=(
                        idprof, 
                        refprof, 
                        date_str, 
                        nomcli, 
                        montant_str, 
                        nb_lignes
                    ))

            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors du chargement des proformas: {str(e)}")
            finally:
                if 'cursor' in locals() and cursor: cursor.close()
                if conn: conn.close()

        def rechercher(*args):
            charger_proforma(entry_search.get())

        entry_search.bind('<KeyRelease>', rechercher)
        
        def valider_selection():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Attention", "Veuillez sélectionner un proforma")
                return

            values = tree.item(selection[0])['values']
            idprof = values[0]
            fenetre.destroy()
            self.charger_proforma_pour_vente(idprof)

        tree.bind('<Double-Button-1>', lambda e: valider_selection())

        # Boutons
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x")
        btn_annuler = ctk.CTkButton(btn_frame, text="❌ Annuler", command=fenetre.destroy, fg_color="#d32f2f", hover_color="#b71c1c")
        btn_annuler.pack(side="left", padx=5, pady=5)
        btn_valider = ctk.CTkButton(btn_frame, text="✅ Charger", command=valider_selection, fg_color="#2e7d32", hover_color="#1b5e20")
        btn_valider.pack(side="right", padx=5, pady=5)
        
        charger_proforma()

    def charger_proforma_pour_vente(self, idprof: int):
        """
        Charge les détails d'un proforma pour la création d'une vente.
        Les détails sont stockés temporairement, en attente de la sélection du magasin.
        """
        # Réinitialisation complète, y compris la référence de vente
        self.nouveau_facture() 
        self.reset_proforma_state() 
        
        conn = self.connect_db()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            
            # 1. Récupérer l'entête du Proforma
            sql_prof = """
                SELECT 
                    p.refprof, p.observation, c.nomcli, c.idclient
                FROM 
                    tb_proforma p
                INNER JOIN 
                    tb_client c ON p.idclient = c.idclient
                WHERE 
                    p.idprof = %s AND p.deleted = 0
            """
            cursor.execute(sql_prof, (idprof,))
            proforma = cursor.fetchone()
            
            if not proforma:
                messagebox.showerror("Erreur", "Proforma introuvable.")
                return

            refprof, description_prof, nomcli, idclient = proforma
            
            # 2. Récupérer les détails du Proforma
            sql_details = """
                SELECT 
                    pd.idarticle, ua.codearticle, a.designation as nom_article,
                    pd.idunite, ua.designationunite as nom_unite, pd.qtlivprof as qtvente, pd.prixunit
                FROM 
                    tb_proformadetail pd
                INNER JOIN 
                    tb_article a ON pd.idarticle = a.idarticle
                INNER JOIN 
                    tb_unite ua ON pd.idunite = ua.idunite
                WHERE 
                    pd.idprof = %s
            """
            cursor.execute(sql_details, (idprof,))
            proforma_details = cursor.fetchall()

            # 3. Stocker les détails temporairement
            self.details_proforma_a_ajouter = []
            cols = ['idarticle', 'code_article', 'nom_article', 'idunite', 'nom_unite', 'qtvente', 'prixunit']
            
            for row in proforma_details:
                detail = dict(zip(cols, row))
                detail['idmag'] = None # Sera défini par l'utilisateur
                detail['designationmag'] = None # Sera défini par l'utilisateur
                self.details_proforma_a_ajouter.append(detail)


            # 4. Mettre à jour les champs d'en-tête (Client, Désignation)
            self.entry_client.delete(0, "end")
            self.entry_client.insert(0, nomcli)
            
            self.entry_designation.delete(0, "end")
            self.entry_designation.insert(0, f"Suivant Proforma n° {refprof}")

            self.client_map[nomcli] = idclient
            self.details_proforma_a_ajouter_idprof = idprof # Conserver l'ID du Proforma

            # 5. Mettre à jour l'interface
            self.detail_vente = [] # S'assurer que le tableau de vente est vide
            self.charger_details_treeview() # Recharge le treeview vide
            self.desactiver_entree_manuelle()
            self.afficher_bouton_ajouter_proforma()
            
            messagebox.showinfo("Proforma Chargé", 
                                f"Proforma N° {refprof} chargé.\n\nÉTAPE SUIVANTE: Veuillez sélectionner le 'Magasin de' (Dépôt) puis cliquez sur le bouton 'Ajouter Lignes Proforma' pour vérifier le stock et ajouter les lignes de vente.")

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement du proforma: {str(e)}")
            self.reset_proforma_state()
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()

    def ajouter_details_proforma_en_masse(self):
        """
        Ajoute tous les détails du proforma dans le tableau de vente,
        en vérifiant le stock pour le magasin sélectionné.
        """
        if not self.details_proforma_a_ajouter:
            messagebox.showwarning("Attention", "Aucun détail de proforma à ajouter.")
            return

        magasin_selectionne_nom = self.combo_magasin.get()
        idmag = self.magasin_map.get(magasin_selectionne_nom)
        
        if not idmag or magasin_selectionne_nom not in self.magasin_map:
            messagebox.showerror("Erreur", "Veuillez sélectionner un Magasin de sortie valide.")
            return
            
        details_ajoutes = 0
        details_non_ajoutes = []
        
        nouveaux_details_vente = []
        
        for detail_prof in self.details_proforma_a_ajouter:
            
            idarticle = detail_prof['idarticle']
            idunite = detail_prof['idunite']
            qtvente_demandee = detail_prof['qtvente']
            nom_article = detail_prof['nom_article']
            nom_unite = detail_prof['nom_unite']
            code_article = detail_prof['code_article']

            # 1. Vérification du Stock
            stock_disponible = self.calculer_stock_article(idarticle, idunite, idmag)
            
            if stock_disponible < qtvente_demandee:
                details_non_ajoutes.append(f"{code_article} ({nom_article}): Qté demandée {self.formater_nombre(qtvente_demandee)} {nom_unite}, Stock {self.formater_nombre(stock_disponible)} {nom_unite}.")
                continue
            
            # 2. Ajout à la liste des nouveaux détails
            nouveau_detail = {
                'idarticle': idarticle,
                'nom_article': nom_article,
                'idunite': idunite,
                'nom_unite': nom_unite,
                'code_article': code_article,
                'qtvente': qtvente_demandee, 
                'prixunit': detail_prof['prixunit'], 
                'designationmag': magasin_selectionne_nom,
                'idmag': idmag 
            }
            nouveaux_details_vente.append(nouveau_detail)
            details_ajoutes += 1

        if nouveaux_details_vente:
            self.detail_vente.extend(nouveaux_details_vente)
            self.charger_details_treeview() # Recharger le treeview
            
            # Mettre à jour le statut du proforma
            if self.details_proforma_a_ajouter_idprof:
                 self.marquer_proforma_comme_facture(self.details_proforma_a_ajouter_idprof)

        # Nettoyage et message final
        self.reset_proforma_state() 
        
        if details_non_ajoutes:
            details_str = "\n".join(details_non_ajoutes)
            messagebox.showwarning("Stock Insuffisant", 
                                   f"{details_ajoutes} ligne(s) ajoutée(s). Les articles suivants n'ont pas pu être ajoutés faute de stock disponible dans le magasin '{magasin_selectionne_nom}':\n\n{details_str}")
        else:
            messagebox.showinfo("Ajout Réussi", 
                                f"Toutes les {details_ajoutes} lignes du proforma ont été ajoutées avec succès à la facture.")

    def marquer_proforma_comme_facture(self, idprof: int):
        """Met à jour le statut du proforma dans la base de données après facturation."""
        conn = self.connect_db()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            sql = """
                UPDATE tb_proforma 
                SET statut = %s, datefacturation = %s 
                WHERE idprof = %s
            """
            cursor.execute(sql, ('Facturé', datetime.now().date(), idprof))
            conn.commit()
            print(f"Proforma ID {idprof} marqué comme 'Facturé'.")
        except Exception as e:
            conn.rollback()
            print(f"Erreur lors de la mise à jour du statut du proforma: {str(e)}")
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()

    def desactiver_entree_manuelle(self):
        """Désactive les champs d'entrée manuelle de détail de vente."""
        self.entry_article.configure(state="readonly") 
        self.entry_qtvente.configure(state="readonly") 
        self.entry_unite.configure(state="readonly") 
        self.entry_prixunit.configure(state="readonly") 
        self.btn_recherche_article.configure(state="disabled")
        self.btn_ajouter.grid_forget()

    def activer_entree_manuelle(self):
        """Réactive les champs d'entrée manuelle de détail de vente."""
        self.entry_article.configure(state="readonly")
        self.entry_qtvente.configure(state="normal")
        self.entry_unite.configure(state="readonly")
        self.entry_prixunit.configure(state="readonly")
        self.btn_recherche_article.configure(state="normal")
        # Réaffiche le bouton d'ajout manuel
        self.btn_ajouter.grid(row=1, column=5, padx=5, pady=5, sticky="w")
    
    def afficher_bouton_ajouter_proforma(self):
        """Affiche le bouton pour ajouter les détails du proforma en masse et le bouton d'annulation Proforma."""
        # Masque les boutons de détail standard
        self.btn_ajouter.grid_forget()
        self.btn_annuler_mod.grid_forget()
        
        # Affiche le bouton d'ajout en masse
        self.btn_ajouter_proforma_bulk.grid(row=1, column=5, padx=5, pady=5, sticky="w")
        
        # Ajout d'un bouton pour annuler le chargement du proforma temporaire
        self.btn_annuler_proforma = ctk.CTkButton(self.btn_ajouter_proforma_bulk.master, 
                                                  text="✖️ Annuler Proforma", 
                                                  command=self.reset_proforma_state, 
                                                  fg_color="#d32f2f", hover_color="#b71c1c")
        self.btn_annuler_proforma.grid(row=1, column=6, padx=5, pady=5, sticky="w")
        
        # Désactiver les autres boutons principaux en cas de chargement Proforma
        self.btn_enregistrer.configure(state="disabled")
        self.btn_charger_proforma.configure(state="disabled")
        self.btn_search_client.configure(state="disabled")
        self.entry_client.configure(state="readonly")


    def masquer_bouton_ajouter_proforma(self):
        """Masque le bouton d'ajout en masse du proforma et restaure les boutons standards."""
        self.btn_ajouter_proforma_bulk.grid_forget()
        if hasattr(self, 'btn_annuler_proforma'):
             self.btn_annuler_proforma.grid_forget()
             del self.btn_annuler_proforma # Nettoyage
        # Restaure le bouton Annuler Modif. original
        self.btn_annuler_mod.grid(row=1, column=6, padx=5, pady=5, sticky="w") 

    def reset_proforma_state(self):
        """Réinitialise l'état après le chargement d'un proforma (sans le valider ou après validation)."""
        self.details_proforma_a_ajouter = None
        self.details_proforma_a_ajouter_idprof = None
        
        self.masquer_bouton_ajouter_proforma()
        self.activer_entree_manuelle()
        
        # Réactiver les contrôles principaux (seulement si nous ne sommes pas en mode modification de vente)
        if not self.mode_modification:
            self.btn_enregistrer.configure(state="normal")
            self.btn_charger_proforma.configure(state="normal")
            self.btn_search_client.configure(state="normal")
            self.entry_client.configure(state="normal")
        
        # Nettoyage des champs si la liste de détails est vide (sinon les détails de la vente sont conservés)
        if not self.detail_vente and not self.mode_modification:
            self.entry_client.delete(0, "end")
            self.entry_client.insert(0, "") 
            self.entry_designation.delete(0, "end")
            self.entry_designation.insert(0, "") 
            self.generer_reference() # Régénère une référence de facture si nouvelle vente
        
        self.reset_detail_form() # Assure le reset des champs de détail

    def _ouvrir_page_avoir(self):
        """Ouvre la fenêtre PageAvoir dans un Toplevel."""
        # Si la fenêtre existe déjà, la mettre au premier plan
        if hasattr(self, 'fenetre_avoir') and self.fenetre_avoir.winfo_exists():
            self.fenetre_avoir.focus()
            return

        self.fenetre_avoir = ctk.CTkToplevel(self)
        self.fenetre_avoir.title("Création / Modification d'Avoir")
        self.fenetre_avoir.geometry("1200x600")
        
        # S'assurer que la fenêtre est modale (optionnel, mais recommandé)
        self.fenetre_avoir.grab_set()

        # Initialise PageAvoir dans la nouvelle fenêtre
        # NOTE : On passe 'self.id_user_connecte' pour que la PageAvoir sache qui est l'utilisateur
        page_avoir = PageAvoir(self.fenetre_avoir, id_user_connecte=self.id_user_connecte)
        page_avoir.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Ajout de la gestion de la fermeture de la fenêtre
        self.fenetre_avoir.protocol("WM_DELETE_WINDOW", self._fermer_fenetre_avoir)

    def _fermer_fenetre_avoir(self):
        """Détruit la fenêtre Avoir et supprime la référence."""
        self.fenetre_avoir.grab_release() # Libère le grab avant de détruire
        self.fenetre_avoir.destroy()
        # On supprime la référence pour que le prochain appel crée une nouvelle fenêtre
        if hasattr(self, 'fenetre_avoir'):
            del self.fenetre_avoir
            
    def _ouvrir_page_proforma(self):
        """Ouvre la fenêtre PageCommandeCli (Proforma) dans un Toplevel."""
        # Si la fenêtre existe déjà, la mettre au premier plan
        if hasattr(self, 'fenetre_proforma') and self.fenetre_proforma.winfo_exists():
            self.fenetre_proforma.focus()
            return

        self.fenetre_proforma = ctk.CTkToplevel(self)
        self.fenetre_proforma.title("Création / Modification de Proforma")
        self.fenetre_proforma.geometry("1200x600")
        
        # S'assurer que la fenêtre est modale
        self.fenetre_proforma.grab_set()

        # CORRECTION ICI : Changer 'id_user_connecte=' par 'iduser='
        page_proforma = PageCommandeCli(self.fenetre_proforma, iduser=self.id_user_connecte)
        
        page_proforma.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Ajout de la gestion de la fermeture de la fenêtre
        self.fenetre_proforma.protocol("WM_DELETE_WINDOW", self._fermer_fenetre_proforma)

    def _fermer_fenetre_proforma(self):
        """Détruit la fenêtre Proforma et supprime la référence."""
        self.fenetre_proforma.grab_release() # Libère le grab avant de détruire
        self.fenetre_proforma.destroy()
        # On supprime la référence pour que le prochain appel crée une nouvelle fenêtre
        if hasattr(self, 'fenetre_proforma'):
            del self.fenetre_proforma        

# --- Partie pour exécuter la fenêtre de test ---
if __name__ == "__main__":
    
    # Simulation de l'utilisateur connecté
    USER_ID = 1 
    
    try:
        app = ctk.CTk()
        app.title("Gestion de Vente")
        app.geometry("1200x600") 
        
        page_vente = PageVente(app, id_user_connecte=USER_ID)
        page_vente.pack(fill="both", expand=True, padx=10, pady=10)
        
        app.mainloop()
        
    except Exception as e:
        print(f"Erreur critique lors de l'exécution: {e}")
        traceback.print_exc()