import customtkinter as ctk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import psycopg2
import json
from datetime import datetime
from resource_utils import get_config_path, get_session_path, safe_file_read


class FenetreRechercheArticle(ctk.CTkToplevel):
    """Fenêtre de recherche d'articles"""
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.title("🔍 Recherche d'Article")
        self.geometry("800x500")
        self.selected_article = None
        
        # Rendre la fenêtre modale
        self.transient(parent)
        self.grab_set()
        
        self.setup_ui()
        self.charger_articles()
    
    def connect_db(self):
        """Connexion à la base de données PostgreSQL"""
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
        except Exception as e:
            messagebox.showerror("Erreur", f"Connexion impossible : {e}")
            return None
    
    def setup_ui(self):
        """Configuration de l'interface"""
        # Frame de recherche
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(pady=10, padx=10, fill="x")
        
        ctk.CTkLabel(search_frame, text="Rechercher:", font=("Arial", 12)).pack(side="left", padx=5)
        self.entry_recherche = ctk.CTkEntry(search_frame, width=300, placeholder_text="Nom ou code article...")
        self.entry_recherche.pack(side="left", padx=5)
        self.entry_recherche.bind("<KeyRelease>", lambda e: self.filtrer_articles())
        
        ctk.CTkButton(
            search_frame, 
            text="🔄 Réinitialiser",
            command=self.charger_articles,
            width=120
        ).pack(side="left", padx=5)
        
        # Frame du treeview
        tree_frame = ctk.CTkFrame(self)
        tree_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        # Scrollbars
        scrollbar_y = ttk.Scrollbar(tree_frame, orient="vertical")
        scrollbar_y.pack(side="right", fill="y")
        
        # Style
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
                       background="#FFFFFF",
                       foreground="#000000",
                       fieldbackground="#FFFFFF",
                       borderwidth=0,
                       rowheight=22,
                       font=('Segoe UI', 8))
        style.configure("Treeview.Heading",
                       background="#E8E8E8",
                       foreground="#000000",
                       font=('Segoe UI', 8, 'bold'),
                       borderwidth=0)
        style.map('Treeview', background=[('selected', '#0d47a1')])
        
        # Treeview
        columns = ("ID", "Désignation", "Catégorie")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            yscrollcommand=scrollbar_y.set,
            height=15
        )
        
        scrollbar_y.config(command=self.tree.yview)
        
        # Configuration des colonnes
        self.tree.heading("ID", text="ID Article")
        self.tree.heading("Désignation", text="Désignation")
        self.tree.heading("Catégorie", text="Catégorie")
        
        self.tree.column("ID", width=100, anchor="center")
        self.tree.column("Désignation", width=400, anchor="w")
        self.tree.column("Catégorie", width=200, anchor="w")
        
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-Button-1>", lambda e: self.valider())
        self.tree.tag_configure("even", background="#FFFFFF", foreground="#000000")
        self.tree.tag_configure("odd", background="#E6EFF8", foreground="#000000")
        
        # Frame des boutons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=10, padx=10, fill="x")
        
        ctk.CTkButton(
            btn_frame,
            text="✓ Sélectionner",
            command=self.valider,
            fg_color="#2e7d32",
            width=150
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="✕ Annuler",
            command=self.destroy,
            fg_color="#d32f2f",
            width=150
        ).pack(side="right", padx=5)
    
    def charger_articles(self):
        """Charge tous les articles"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        conn = self.connect_db()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT 
                    a.idarticle, 
                    a.designation,
                    COALESCE(c.designationcat, 'Sans catégorie') as categorie
                FROM tb_article a
                LEFT JOIN tb_categoriearticle c ON a.idca = c.idca
                WHERE a.deleted = 0
                ORDER BY a.designation
            """)
            
            for idx, row in enumerate(cursor.fetchall()):
                tag = "even" if idx % 2 == 0 else "odd"
                self.tree.insert("", "end", values=row, tags=(tag,))
            
            cursor.close()
            conn.close()
    
    def filtrer_articles(self):
        """Filtre les articles selon la recherche"""
        recherche = self.entry_recherche.get().strip().lower()
        
        if not recherche:
            self.charger_articles()
            return
        
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        conn = self.connect_db()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT 
                    a.idarticle, 
                    a.designation,
                    COALESCE(c.designationcat, 'Sans catégorie') as categorie
                FROM tb_article a
                LEFT JOIN tb_categoriearticle c ON a.idca = c.idca
                WHERE a.deleted = 0
                AND (
                    LOWER(a.designation) LIKE %s 
                    OR CAST(a.idarticle AS TEXT) LIKE %s
                )
                ORDER BY a.designation
            """, (f"%{recherche}%", f"%{recherche}%"))
            
            for idx, row in enumerate(cursor.fetchall()):
                tag = "even" if idx % 2 == 0 else "odd"
                self.tree.insert("", "end", values=row, tags=(tag,))
            
            cursor.close()
            conn.close()
    
    def valider(self):
        """Valide la sélection"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner un article.")
            return
        
        item = self.tree.item(selection[0])
        values = item['values']
        
        self.selected_article = {
            'idarticle': values[0],
            'designation': values[1],
            'categorie': values[2]
        }
        
        self.callback(self.selected_article)
        self.destroy()


class PageArticleMouvement(ctk.CTkFrame):
    def __init__(self, parent, initial_idarticle=None):
        super().__init__(parent)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # Row 2 est le treeview

        self.initial_idarticle = initial_idarticle
        self.id_user_connecte = self.get_connected_user_id(parent)

        # Variables d'affichage
        self.selected_idarticle = None
        self.selected_article_name = None

        # Création interface
        self.create_widgets()

        # Chargement des données
        self.load_magasins()
        self.load_mouvements()

    def get_connected_user_id(self, parent):
        """Récupère l'ID utilisateur connecté (parent puis session.json)."""
        parent_id = getattr(parent, "id_user_connecte", None)
        if parent_id is None:
            parent_id = getattr(parent, "iduser", None)

        if parent_id is not None:
            try:
                return int(parent_id)
            except (TypeError, ValueError):
                pass

        try:
            session_path = get_session_path()
            with open(session_path, "r", encoding="utf-8") as f:
                session_data = json.load(f)
            session_id = session_data.get("user_id")
            if session_id is not None:
                return int(session_id)
        except Exception:
            pass

        return None
    
    def connect_db(self):
        """Connexion à la base de données PostgreSQL"""
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
        except KeyError:
            messagebox.showerror("Erreur de configuration", "Clés de base de données manquantes dans 'config.json'.")
            return None
        except psycopg2.Error as err:
            messagebox.showerror("Erreur de connexion", f"Erreur de connexion à PostgreSQL : {err}")
            return None
        except UnicodeDecodeError as err:
            messagebox.showerror("Erreur d'encodage", f"Problème d'encodage du fichier de configuration : {err}")
            return None
    
    def formater_nombre(self, nombre):
        """Formate un nombre avec séparateur de milliers (1 000,00)"""
        try:
            nombre = float(nombre)
            partie_entiere = int(nombre)
            partie_decimale = abs(nombre - partie_entiere)
        
            str_entiere = f"{partie_entiere:,}".replace(',', ' ')
            str_decimale = f"{partie_decimale:.2f}".split('.')[1]
        
            return f"{str_entiere},{str_decimale}"
        except:
            return "0,00"
    
    def get_unite_hierarchy(self, conn, idarticle):
        """Récupère la hiérarchie complète des unités pour un article"""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT idunite, niveau, COALESCE(qtunite, 1) as qtunite, designationunite, codearticle
            FROM tb_unite
            WHERE idarticle = %s
            ORDER BY niveau ASC
        """, (idarticle,))
    
        unites = {}
        for row in cursor.fetchall():
            idunite, niveau, qtunite, designation, codearticle = row
            unites[idunite] = {
                'niveau': niveau,
                'qtunite': qtunite,
                'designation': designation,
                'codearticle': codearticle
            }
        cursor.close()
        return unites
    
    def calculer_facteurs_conversion(self, unites_hierarchy):
        """Calcule les facteurs de conversion vers l'unité de base"""
        if not unites_hierarchy:
            return {}
    
        unite_base = min(unites_hierarchy.items(), key=lambda x: x[1]['niveau'])
        idunite_base = unite_base[0]
    
        facteurs = {idunite_base: 1.0}
    
        unites_triees = sorted(unites_hierarchy.items(), key=lambda x: x[1]['niveau'])
    
        facteur_cumul = 1.0
        for i, (idunite, info) in enumerate(unites_triees):
            if i == 0:
                facteurs[idunite] = 1.0
            else:
                facteur_cumul *= info['qtunite']
                facteurs[idunite] = facteur_cumul
    
        return facteurs
    
    def convert_to_unite_cible(self, quantity, from_unite, to_unite, facteurs_conversion):
        """Convertit une quantité de from_unite vers to_unite"""
        if from_unite == to_unite:
            return quantity
    
        if from_unite not in facteurs_conversion or to_unite not in facteurs_conversion:
            return 0
    
        qte_en_base = quantity * facteurs_conversion[from_unite]
        qte_en_cible = qte_en_base / facteurs_conversion[to_unite]
    
        return qte_en_cible
    
    def calculer_stock_initial(self, conn, idarticle, idunite, date_debut, idmag=None):
        """
        Calcule le stock initial AVANT la date de début
        (Somme de tous les mouvements AVANT cette date pour une unité spécifique)
        """
        cursor = conn.cursor()
        
        # Requête unifiée plus simple pour tous les mouvements AVANT la date
        query = """
            SELECT 
                COALESCE(SUM(CASE WHEN type_mouv IN ('entree', 'inventaire', 'avoir', 'transfert_entree') 
                    THEN qt ELSE 0 END), 0) as total_entrees,
                COALESCE(SUM(CASE WHEN type_mouv IN ('sortie', 'vente', 'transfert_sortie') 
                    THEN qt ELSE 0 END), 0) as total_sorties
            FROM (
                -- Entrées Fournisseurs
                SELECT lf.qtlivrefrs as qt, 'entree' as type_mouv, lf.dateregistre as date_mouv
                FROM tb_livraisonfrs lf
                INNER JOIN tb_unite u ON lf.idunite = u.idunite
                WHERE u.idunite = %s AND lf.deleted = 0 AND DATE(lf.dateregistre) < %s
                
                UNION ALL
                -- Sorties
                SELECT sd.qtsortie as qt, 'sortie' as type_mouv, s.dateregistre as date_mouv
                FROM tb_sortie s
                INNER JOIN tb_sortiedetail sd ON s.id = sd.idsortie
                INNER JOIN tb_unite u ON sd.idunite = u.idunite
                WHERE u.idunite = %s AND s.deleted = 0 AND sd.deleted = 0 AND DATE(s.dateregistre) < %s
                
                UNION ALL
                -- Ventes
                SELECT vd.qtvente as qt, 'vente' as type_mouv, v.dateregistre as date_mouv
                FROM tb_vente v
                INNER JOIN tb_ventedetail vd ON v.id = vd.idvente
                INNER JOIN tb_unite u ON vd.idunite = u.idunite
                WHERE u.idunite = %s AND v.deleted = 0 AND vd.deleted = 0 AND DATE(v.dateregistre) < %s
                
                UNION ALL
                -- Transferts Sortie
                SELECT td.qttransfert as qt, 'transfert_sortie' as type_mouv, t.dateregistre as date_mouv
                FROM tb_transfert t
                INNER JOIN tb_transfertdetail td ON t.idtransfert = td.idtransfert
                INNER JOIN tb_unite u ON td.idunite = u.idunite
                WHERE u.idunite = %s AND t.deleted = 0 AND td.deleted = 0 AND DATE(t.dateregistre) < %s
                
                UNION ALL
                -- Transferts Entrée
                SELECT td.qttransfert as qt, 'transfert_entree' as type_mouv, t.dateregistre as date_mouv
                FROM tb_transfert t
                INNER JOIN tb_transfertdetail td ON t.idtransfert = td.idtransfert
                INNER JOIN tb_unite u ON td.idunite = u.idunite
                WHERE u.idunite = %s AND t.deleted = 0 AND td.deleted = 0 AND DATE(t.dateregistre) < %s
                
                UNION ALL
                -- Inventaires
                SELECT i.qtinventaire as qt, 'inventaire' as type_mouv, i.date as date_mouv
                FROM tb_inventaire i
                INNER JOIN tb_unite u ON i.codearticle = u.codearticle
                WHERE u.idunite = %s AND DATE(i.date) < %s
                
                UNION ALL
                -- Avoirs
                SELECT ad.qtavoir as qt, 'avoir' as type_mouv, av.dateavoir as date_mouv
                FROM tb_avoir av
                INNER JOIN tb_avoirdetail ad ON av.id = ad.idavoir
                INNER JOIN tb_unite u ON ad.idunite = u.idunite
                WHERE u.idunite = %s AND av.deleted = 0 AND DATE(av.dateavoir) < %s
            ) as mouvements
        """
        
        # 8 paramètres: idunite et date_debut répétés 8 fois
        params = [idunite, date_debut] * 8
        
        try:
            cursor.execute(query, params)
            result = cursor.fetchone()
            cursor.close()
            
            total_entrees = float(result[0]) if result and result[0] else 0
            total_sorties = float(result[1]) if result and result[1] else 0
            stock_initial = total_entrees - total_sorties
            
            return stock_initial
        except Exception as e:
            print(f"ERREUR lors du calcul du stock initial: {str(e)}")
            cursor.close()
            return 0
    
    def filtrer_article_dynamique(self):
        """Filtre et recherche dynamiquement un article par nom ou code dans le tableau"""
        recherche = self.entry_recherche_article.get().strip().lower()
        
        if not recherche:
            # Si le champ est vide, réinitialiser
            self.reset_article_selection()
            return
        
        conn = self.connect_db()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT idarticle, designation, COALESCE(c.designationcat, 'Sans catégorie')
                FROM tb_article a
                LEFT JOIN tb_categoriearticle c ON a.idca = c.idca
                WHERE a.deleted = 0
                AND (
                    LOWER(a.designation) LIKE %s 
                    OR CAST(a.idarticle AS TEXT) LIKE %s
                )
                ORDER BY a.designation
                LIMIT 1
            """, (f"%{recherche}%", f"%{recherche}%"))
            
            resultat = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if resultat:
                # Sélectionner le premier résultat trouvé
                article = {
                    'idarticle': resultat[0],
                    'designation': resultat[1],
                    'categorie': resultat[2]
                }
                self.selected_idarticle = article['idarticle']
                self.selected_article_name = article['designation']
                # Recharger le tableau avec ce nouvel article sélectionné
                self.load_mouvements()
            else:
                # Aucun résultat
                self.reset_article_selection()
        
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la recherche : {str(e)}")
            if conn:
                conn.close()
    
    def ouvrir_recherche_article(self):
        """Ouvre la fenêtre de recherche d'articles"""
        FenetreRechercheArticle(self, self.on_article_selected)
    
    def on_article_selected(self, article):
        """Callback quand un article est sélectionné"""
        self.selected_idarticle = article['idarticle']
        self.selected_article_name = article['designation']
        
        # Mettre à jour le champ de recherche
        self.entry_recherche_article.delete(0, "end")
        self.entry_recherche_article.insert(0, article['designation'])
        
        # Recharger les mouvements
        self.load_mouvements()
    
    def reset_article_selection(self):
        """Réinitialise la sélection d'article"""
        self.selected_idarticle = None
        self.selected_article_name = None
        self.entry_recherche_article.delete(0, "end")
        
        self.load_mouvements()
    
    def create_widgets(self):
        """Création des widgets de l'interface"""
        # ===== EN-TÊTE AVEC TITRE =====
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        header.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            header, 
            text="📋 Mouvements d'Articles", 
            font=("Arial", 20, "bold")
        ).pack(side="left")
        
        # ===== FRAME DE FILTRES =====
        filter_frame = ctk.CTkFrame(self)
        filter_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        filter_frame.grid_columnconfigure(0, weight=1)  # Column 0 s'étend
        filter_frame.grid_columnconfigure((1, 2), weight=0)  # Columns 1, 2 taille fixe
        
        # --- ROW 1: Recherche article + Type doc + Magasin ---
        # Recherche article (colonne 0)
        ctk.CTkLabel(filter_frame, text="Rechercher article:", font=("Arial", 11, "bold")).grid(
            row=0, column=0, sticky="w", padx=(5, 0), pady=(0, 3)
        )
        
        self.entry_recherche_article = ctk.CTkEntry(
            filter_frame,
            placeholder_text="Nom ou code article...",
            height=35,
            width=250
        )
        self.entry_recherche_article.grid(row=1, column=0, sticky="ew", padx=(5, 10), pady=(0, 10))
        # On text change: filter current table; on Enter: search DB for exact article
        self.entry_recherche_article.bind("<KeyRelease>", lambda e: self.filter_tree_by_text())
        self.entry_recherche_article.bind("<Return>", lambda e: self.filtrer_article_dynamique())
        
        # Type de document (colonne 1)
        ctk.CTkLabel(filter_frame, text="Type:", font=("Arial", 11, "bold")).grid(
            row=0, column=1, sticky="w", padx=5, pady=(0, 3)
        )
        self.combo_type = ctk.CTkComboBox(
            filter_frame,
            values=["Tous", "Entrée", "Sortie", "Vente", "Transfert", "Inventaire", "Avoir", "Consommation interne", "Changement"],
            width=180,
            height=35
        )
        self.combo_type.grid(row=1, column=1, sticky="ew", padx=5, pady=(0, 10))
        self.combo_type.set("Tous")
        
        # Magasin (colonne 2)
        ctk.CTkLabel(filter_frame, text="Magasin:", font=("Arial", 11, "bold")).grid(
            row=0, column=2, sticky="w", padx=5, pady=(0, 3)
        )
        self.combo_magasin = ctk.CTkComboBox(
            filter_frame,
            values=["Tous les magasins"],
            width=200,
            height=35
        )
        self.combo_magasin.grid(row=1, column=2, sticky="ew", padx=5, pady=(0, 10))
        self.combo_magasin.set("Tous les magasins")
        
        # --- ROW 2: Dates + Bouton rechercher ---
        ctk.CTkLabel(filter_frame, text="Date début:", font=("Arial", 11, "bold")).grid(
            row=2, column=0, sticky="w", padx=(5, 0), pady=(0, 3)
        )
        
        self.date_debut = DateEntry(
            filter_frame,
            width=25,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='dd/mm/yyyy'
        )
        self.date_debut.grid(row=3, column=0, sticky="w", padx=(5, 10), pady=(0, 10))
        
        ctk.CTkLabel(filter_frame, text="Date fin:", font=("Arial", 11, "bold")).grid(
            row=2, column=1, sticky="w", padx=5, pady=(0, 3)
        )
        
        self.date_fin = DateEntry(
            filter_frame,
            width=25,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='dd/mm/yyyy'
        )
        self.date_fin.grid(row=3, column=1, sticky="w", padx=5, pady=(0, 10))
        
        # Bouton rechercher (colonne 2, aligné avec les dates)
        ctk.CTkButton(
            filter_frame,
            text="🔍 Appliquer filtres",
            command=self.load_mouvements,
            width=160,
            height=35,
            fg_color="#2e7d32"
        ).grid(row=3, column=2, sticky="ew", padx=5, pady=(0, 10))
        
        # ===== TREEVIEW =====
        tree_frame = ctk.CTkFrame(self)
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Scrollbars
        scrollbar_y = ttk.Scrollbar(tree_frame, orient="vertical")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        
        scrollbar_x = ttk.Scrollbar(tree_frame, orient="horizontal")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        
        # Configuration du style
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                       background="#FFFFFF",
                       foreground="#000000",
                       fieldbackground="#FFFFFF",
                       borderwidth=0,
                       rowheight=22,
                       font=('Segoe UI', 8))
        style.configure("Treeview.Heading",
                       background="#1f538d",
                       foreground="white",
                       borderwidth=1)
        style.map('Treeview',
                 background=[('selected', '#0d47a1')])
        
        # Treeview
        columns = ("Date", "Référence", "Type", "Désignation", "Unité", "Entrée", "Sortie", "Magasin", "Utilisateur")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set,
            height=20
        )
        
        scrollbar_y.config(command=self.tree.yview)
        scrollbar_x.config(command=self.tree.xview)
        
        # Configuration des colonnes
        column_widths = {
            "Date": 160,
            "Référence": 120,
            "Type": 120,
            "Désignation": 220,
            "Unité": 100,
            "Entrée": 100,
            "Sortie": 100,
            "Magasin": 150,
            "Utilisateur": 120
        }
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=column_widths.get(col, 100), anchor="center")
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        
        # Configuration des tags
        self.tree.tag_configure('header', background='#1976d2', foreground='white', font=('Arial', 10, 'bold'))
        self.tree.tag_configure('separator', background='#424242')
        self.tree.tag_configure("even", background="#FFFFFF", foreground="#000000")
        self.tree.tag_configure("odd", background="#E6EFF8", foreground="#000000")
        
        # Label total
        self.label_total = ctk.CTkLabel(
            self,
            text="Nombre total de documents: 0",
            font=("Arial", 12, "bold")
        )
        self.label_total.grid(row=3, column=0, pady=5)
    
    def load_magasins(self):
        """Charge la liste des magasins"""
        conn = self.connect_db()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT idmag, designationmag 
                FROM tb_magasin 
                WHERE deleted = 0
                ORDER BY designationmag
            """)
            magasins = cursor.fetchall()

            # Mapping nom -> id pour conserver la logique métier
            self.magasin_name_to_id = {m[1]: m[0] for m in magasins}
            magasin_list = ["Tous les magasins"] + [m[1] for m in magasins]
            self.combo_magasin.configure(values=magasin_list)
            self.combo_magasin.set("Tous les magasins")

            if self.id_user_connecte is not None:
                cursor.execute(
                    "SELECT idmag FROM tb_users WHERE iduser = %s AND deleted = 0",
                    (self.id_user_connecte,)
                )
                row = cursor.fetchone()
                if row and row[0]:
                    idmag_user = row[0]
                    nom_magasin_user = next((m[1] for m in magasins if m[0] == idmag_user), None)
                    if nom_magasin_user:
                        self.combo_magasin.set(nom_magasin_user)

            cursor.close()
            conn.close()
    
    def build_mouvements_query(self, date_debut, date_fin, type_doc, idmag):
        """
        Construit une requête UNION optimisée pour tous les mouvements
        Retourne: (query_sql, params)
        Structure tuple: (date, reference, designation, type, entree, sortie, magasin, username, idunite, codearticle)
        """
        queries = []
        params = []
        
        # --- ENTRÉES (Livraisons Fournisseurs) ---
        if type_doc in ["Tous", "Entrée"]:
            query_entree = """
                SELECT 
                    lf.dateregistre,
                    lf.reflivfrs,
                    a.designation,
                    'Entrée',
                    COALESCE(lf.qtlivrefrs, 0),
                    0,
                    COALESCE(m.designationmag, 'N/A'),
                    COALESCE(usr.username, 'N/A'),
                    u.idunite,
                    u.codearticle
                FROM tb_livraisonfrs lf
                INNER JOIN tb_unite u ON lf.idunite = u.idunite
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN tb_magasin m ON lf.idmag = m.idmag
                LEFT JOIN tb_users usr ON lf.iduser = usr.iduser
                WHERE DATE(lf.dateregistre) BETWEEN %s AND %s
                AND lf.deleted = 0
            """
            query_params = [date_debut, date_fin]
            
            if self.selected_idarticle:
                query_entree += " AND a.idarticle = %s"
                query_params.append(int(self.selected_idarticle))
            
            if idmag:
                query_entree += " AND lf.idmag = %s"
                query_params.append(idmag)
            
            queries.append(query_entree)
            params.append(query_params)
        
        # --- SORTIES ---
        if type_doc in ["Tous", "Sortie"]:
            query_sortie = """
                SELECT 
                    s.dateregistre,
                    s.refsortie,
                    a.designation,
                    'Sortie',
                    0,
                    COALESCE(sd.qtsortie, 0),
                    COALESCE(m.designationmag, 'N/A'),
                    COALESCE(usr.username, 'N/A'),
                    u.idunite,
                    u.codearticle
                FROM tb_sortie s
                INNER JOIN tb_sortiedetail sd ON s.id = sd.idsortie
                INNER JOIN tb_unite u ON sd.idunite = u.idunite
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN tb_magasin m ON sd.idmag = m.idmag
                LEFT JOIN tb_users usr ON s.iduser = usr.iduser
                WHERE DATE(s.dateregistre) BETWEEN %s AND %s
                AND s.deleted = 0 AND sd.deleted = 0
            """
            query_params = [date_debut, date_fin]
            
            if self.selected_idarticle:
                query_sortie += " AND a.idarticle = %s"
                query_params.append(int(self.selected_idarticle))
            
            if idmag:
                query_sortie += " AND sd.idmag = %s"
                query_params.append(idmag)
            
            queries.append(query_sortie)
            params.append(query_params)
        
        # --- VENTES ---
        if type_doc in ["Tous", "Vente"]:
            query_vente = """
                SELECT 
                    v.dateregistre,
                    v.refvente,
                    a.designation,
                    'Vente',
                    0,
                    COALESCE(vd.qtvente, 0),
                    COALESCE(m.designationmag, 'N/A'),
                    COALESCE(usr.username, 'N/A'),
                    u.idunite,
                    u.codearticle
                FROM tb_vente v
                INNER JOIN tb_ventedetail vd ON v.id = vd.idvente
                INNER JOIN tb_unite u ON vd.idunite = u.idunite
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN tb_magasin m ON vd.idmag = m.idmag
                LEFT JOIN tb_users usr ON v.iduser = usr.iduser
                WHERE DATE(v.dateregistre) BETWEEN %s AND %s
                AND v.deleted = 0 AND vd.deleted = 0
            """
            query_params = [date_debut, date_fin]
            
            if self.selected_idarticle:
                query_vente += " AND a.idarticle = %s"
                query_params.append(int(self.selected_idarticle))
            
            if idmag:
                query_vente += " AND vd.idmag = %s"
                query_params.append(idmag)
            
            queries.append(query_vente)
            params.append(query_params)
        
        # --- TRANSFERTS (Sorties + Entrées) ---
        if type_doc in ["Tous", "Transfert"]:
            # Transferts Sortie
            query_t_sortie = """
                SELECT 
                    t.dateregistre,
                    t.reftransfert,
                    a.designation,
                    'Transfert (Sortie)',
                    0,
                    COALESCE(td.qttransfert, 0),
                    COALESCE(m.designationmag, 'N/A'),
                    COALESCE(usr.username, 'N/A'),
                    u.idunite,
                    u.codearticle
                FROM tb_transfert t
                INNER JOIN tb_transfertdetail td ON t.idtransfert = td.idtransfert
                INNER JOIN tb_unite u ON td.idunite = u.idunite
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN tb_magasin m ON td.idmagsortie = m.idmag
                LEFT JOIN tb_users usr ON t.iduser = usr.iduser
                WHERE DATE(t.dateregistre) BETWEEN %s AND %s
                AND t.deleted = 0 AND td.deleted = 0
            """
            query_params = [date_debut, date_fin]
            
            if self.selected_idarticle:
                query_t_sortie += " AND a.idarticle = %s"
                query_params.append(int(self.selected_idarticle))
            
            if idmag:
                query_t_sortie += " AND td.idmagsortie = %s"
                query_params.append(idmag)
            
            queries.append(query_t_sortie)
            params.append(query_params.copy())
            
            # Transferts Entrée
            query_t_entree = """
                SELECT 
                    t.dateregistre,
                    t.reftransfert,
                    a.designation,
                    'Transfert (Entrée)',
                    COALESCE(td.qttransfert, 0),
                    0,
                    COALESCE(m.designationmag, 'N/A'),
                    COALESCE(usr.username, 'N/A'),
                    u.idunite,
                    u.codearticle
                FROM tb_transfert t
                INNER JOIN tb_transfertdetail td ON t.idtransfert = td.idtransfert
                INNER JOIN tb_unite u ON td.idunite = u.idunite
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN tb_magasin m ON td.idmagentree = m.idmag
                LEFT JOIN tb_users usr ON t.iduser = usr.iduser
                WHERE DATE(t.dateregistre) BETWEEN %s AND %s
                AND t.deleted = 0 AND td.deleted = 0
            """
            query_params = [date_debut, date_fin]
            
            if self.selected_idarticle:
                query_t_entree += " AND a.idarticle = %s"
                query_params.append(int(self.selected_idarticle))
            
            if idmag:
                query_t_entree += " AND td.idmagentree = %s"
                query_params.append(idmag)
            
            queries.append(query_t_entree)
            params.append(query_params)
        
        # --- INVENTAIRES ---
        if type_doc in ["Tous", "Inventaire"]:
            query_inv = """
                SELECT 
                    i.date,
                    CONCAT('INV-', i.id),
                    a.designation,
                    CONCAT('Inventaire', CASE WHEN i.observation IS NOT NULL AND i.observation != '' 
                        THEN CONCAT(' (', i.observation, ')') ELSE '' END),
                    i.qtinventaire,
                    0,
                    COALESCE(m.designationmag, 'N/A'),
                    COALESCE(usr.username, 'N/A'),
                    u.idunite,
                    u.codearticle
                FROM tb_inventaire i
                INNER JOIN tb_unite u ON i.codearticle = u.codearticle
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN tb_magasin m ON i.idmag = m.idmag
                LEFT JOIN tb_users usr ON i.iduser = usr.iduser
                WHERE DATE(i.date) BETWEEN %s AND %s
            """
            query_params = [date_debut, date_fin]
            
            if self.selected_idarticle:
                query_inv += " AND a.idarticle = %s"
                query_params.append(int(self.selected_idarticle))
            
            if idmag:
                query_inv += " AND i.idmag = %s"
                query_params.append(idmag)
            
            queries.append(query_inv)
            params.append(query_params)
        
        # --- AVOIRS ---
        if type_doc in ["Tous", "Avoir"]:
            query_avoir = """
                SELECT 
                    av.dateavoir,
                    av.refavoir,
                    a.designation,
                    'Avoir',
                    ad.qtavoir,
                    0,
                    COALESCE(m.designationmag, 'N/A'),
                    COALESCE(usr.username, 'N/A'),
                    u.idunite,
                    u.codearticle
                FROM tb_avoir av
                INNER JOIN tb_avoirdetail ad ON av.id = ad.idavoir
                INNER JOIN tb_unite u ON ad.idunite = u.idunite
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN tb_magasin m ON ad.idmag = m.idmag
                LEFT JOIN tb_users usr ON av.iduser = usr.iduser
                WHERE DATE(av.dateavoir) BETWEEN %s AND %s
                AND av.deleted = 0
            """
            query_params = [date_debut, date_fin]
            
            if self.selected_idarticle:
                query_avoir += " AND a.idarticle = %s"
                query_params.append(int(self.selected_idarticle))
            
            if idmag:
                query_avoir += " AND ad.idmag = %s"
                query_params.append(idmag)
            
            queries.append(query_avoir)
            params.append(query_params)
        
        # --- CONSOMMATION INTERNE ---
        if type_doc in ["Tous", "Consommation interne"]:
            query_conso = """
                SELECT 
                    ci.dateregistre,
                    ci.refconsommation,
                    a.designation,
                    'Consommation interne',
                    0,
                    cid.qtconsomme,
                    COALESCE(m.designationmag, 'N/A'),
                    COALESCE(usr.username, 'N/A'),
                    u.idunite,
                    u.codearticle
                FROM tb_consommationinterne ci
                INNER JOIN tb_consommationinterne_details cid ON ci.id = cid.idconsommation
                INNER JOIN tb_unite u ON cid.idunite = u.idunite
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN tb_magasin m ON cid.idmag = m.idmag
                LEFT JOIN tb_users usr ON ci.iduser = usr.iduser
                WHERE DATE(ci.dateregistre) BETWEEN %s AND %s
            """
            query_params = [date_debut, date_fin]
            
            if self.selected_idarticle:
                query_conso += " AND a.idarticle = %s"
                query_params.append(int(self.selected_idarticle))
            
            if idmag:
                query_conso += " AND cid.idmag = %s"
                query_params.append(idmag)
            
            queries.append(query_conso)
            params.append(query_params)
        
        # --- CHANGEMENT (Sortie + Entrée) ---
        if type_doc in ["Tous", "Changement"]:
            # Changement Sortie
            query_chg_sortie = """
                SELECT 
                    chg.datechg,
                    chg.refchg,
                    a.designation,
                    'Changement (Sortie)',
                    0,
                    dcs.quantite_sortie,
                    COALESCE(m.designationmag, 'N/A'),
                    COALESCE(usr.username, 'N/A'),
                    u.idunite,
                    u.codearticle
                FROM tb_changement chg
                INNER JOIN tb_detailchange_sortie dcs ON chg.idchg = dcs.idchg
                INNER JOIN tb_unite u ON dcs.idunite = u.idunite
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN tb_magasin m ON dcs.idmagasin = m.idmag
                LEFT JOIN tb_users usr ON chg.iduser = usr.iduser
                WHERE DATE(chg.datechg) BETWEEN %s AND %s
            """
            query_params = [date_debut, date_fin]
            
            if self.selected_idarticle:
                query_chg_sortie += " AND a.idarticle = %s"
                query_params.append(int(self.selected_idarticle))
            
            if idmag:
                query_chg_sortie += " AND dcs.idmagasin = %s"
                query_params.append(idmag)
            
            queries.append(query_chg_sortie)
            params.append(query_params.copy())
            
            # Changement Entrée
            query_chg_entree = """
                SELECT 
                    chg.datechg,
                    chg.refchg,
                    a.designation,
                    'Changement (Entrée)',
                    dce.quantite_entree,
                    0,
                    COALESCE(m.designationmag, 'N/A'),
                    COALESCE(usr.username, 'N/A'),
                    u.idunite,
                    u.codearticle
                FROM tb_changement chg
                INNER JOIN tb_detailchange_entree dce ON chg.idchg = dce.idchg
                INNER JOIN tb_unite u ON dce.idunite = u.idunite
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN tb_magasin m ON dce.idmagasin = m.idmag
                LEFT JOIN tb_users usr ON chg.iduser = usr.iduser
                WHERE DATE(chg.datechg) BETWEEN %s AND %s
            """
            query_params = [date_debut, date_fin]
            
            if self.selected_idarticle:
                query_chg_entree += " AND a.idarticle = %s"
                query_params.append(int(self.selected_idarticle))
            
            if idmag:
                query_chg_entree += " AND dce.idmagasin = %s"
                query_params.append(idmag)
            
            queries.append(query_chg_entree)
            params.append(query_params)
        
        return queries, params
    
    def load_mouvements(self):
        """Charge les mouvements d'articles avec filtres optimisés"""
        conn = self.connect_db()
        if not conn:
            return
        
        try:
            # Effacer le treeview
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Récupérer les filtres
            date_debut = self.date_debut.get_date()
            date_fin = self.date_fin.get_date()
            type_doc = self.combo_type.get()
            
            # Filtre magasin
            magasin_selection = self.combo_magasin.get()
            idmag = None
            if magasin_selection != "Tous les magasins":
                idmag = self.magasin_name_to_id.get(magasin_selection)
            
            cursor = conn.cursor()
            
            # Récupérer la hiérarchie des unités si un article est sélectionné
            unites_hierarchy = {}
            if self.selected_idarticle:
                unites_hierarchy = self.get_unite_hierarchy(conn, int(self.selected_idarticle))
            
            # Construire et exécuter les requêtes
            mouvements = []
            queries, params_list = self.build_mouvements_query(date_debut, date_fin, type_doc, idmag)
            
            for query, params in zip(queries, params_list):
                try:
                    cursor.execute(query, params)
                    mouvements.extend(cursor.fetchall())
                except Exception as e:
                    print(f"ERREUR dans requête: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            if not mouvements:
                self.label_total.configure(text="Aucun mouvement trouvé pour les filtres sélectionnés")
                cursor.close()
                conn.close()
                return
            
            # Trier les mouvements: d'abord par codearticle ASC, puis designation ASC, puis date DESC
            # Utilisation de tris stables successifs
            try:
                mouvements.sort(key=lambda x: x[9] or "")  # codearticle ASC
            except Exception:
                pass

            try:
                mouvements.sort(key=lambda x: (x[2].lower() if x[2] else ""))  # designation ASC
            except Exception:
                pass

            try:
                mouvements.sort(key=lambda x: x[0] if x[0] else datetime.min, reverse=True)  # date DESC
            except Exception:
                pass
            
            # Unified flat display: insert each movement as a single row (no per-unit grouping)
            rows_to_display = []
            for mouv in mouvements:
                date_format = mouv[0].strftime('%d/%m/%Y %H:%M:%S') if mouv[0] else ""
                reference = mouv[1] or ""
                article_designation = mouv[2] or ""
                type_doc_display = mouv[3] or ""
                entree = float(mouv[4]) if mouv[4] else 0
                sortie = float(mouv[5]) if mouv[5] else 0
                magasin_display = mouv[6] or ""
                username = mouv[7] or ""
                idunite = mouv[8]

                # Récupérer la désignation de l'unité
                cursor.execute("SELECT designationunite FROM tb_unite WHERE idunite = %s", (idunite,))
                result = cursor.fetchone()
                unite_display = result[0] if result else ""

                row_values = (
                    date_format,
                    reference,
                    type_doc_display,
                    article_designation,
                    unite_display,
                    '-' if entree == 0 else self.formater_nombre(entree),
                    '-' if sortie == 0 else self.formater_nombre(sortie),
                    magasin_display,
                    username
                )

                rows_to_display.append(row_values)

            # Insérer toutes les lignes dans le treeview
            for idx, row in enumerate(rows_to_display):
                tag = "even" if idx % 2 == 0 else "odd"
                self.tree.insert("", "end", values=row, tags=(tag,))

            # Sauvegarder la liste complète pour le filtrage côté client
            self.full_display_rows = rows_to_display
            self.label_total.configure(text=f"Nombre total de documents: {len(rows_to_display)}")
            
            cursor.close()
            
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des mouvements: {err}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur inattendue: {str(e)}")
        finally:
            conn.close()

    def filter_tree_by_text(self, event=None):
        """Filtre le treeview côté client selon le texte saisi (toutes colonnes)."""
        search = self.entry_recherche_article.get().strip().lower()
        rows = getattr(self, 'full_display_rows', [])

        # Vider le treeview
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not search:
            for idx, row in enumerate(rows):
                tag = "even" if idx % 2 == 0 else "odd"
                self.tree.insert("", "end", values=row, tags=(tag,))
            self.label_total.configure(text=f"Nombre total de documents: {len(rows)}")
            return

        filtered = []
        for row in rows:
            # Vérifier si le texte est présent dans une des colonnes
            match = False
            for cell in row:
                if search in str(cell).lower():
                    match = True
                    break
            if match:
                filtered.append(row)

        for idx, row in enumerate(filtered):
            tag = "even" if idx % 2 == 0 else "odd"
            self.tree.insert("", "end", values=row, tags=(tag,))

        self.label_total.configure(text=f"Nombre total de documents: {len(filtered)} (filtré)")


# Test de la classe (optionnel)
if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    root = ctk.CTk()
    root.title("Mouvements d'Articles")
    root.geometry("1400x700")
    
    # Configuration de la grille du root
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    
    # Création et affichage de la page
    page = PageArticleMouvement(root)
    page.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    
    root.mainloop()
