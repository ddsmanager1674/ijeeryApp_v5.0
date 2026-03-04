import customtkinter as ctk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import psycopg2
import json
from datetime import datetime
import sys
import os
import threading
from resource_utils import get_config_path, get_session_path, safe_file_read

# Ajouter le répertoire parent au chemin pour importer stock_manager
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from stock_manager import StockManager


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
        
        # Variables pour le chargement des stocks en arrière-plan
        self.stock_thread = None
        self.thread_stop_event = threading.Event()
        self.rows_pending = []  # Liste des lignes en attente de calcul de stock
        self.tree_items = []    # Liste des item_ids du treeview (synchronisée avec rows_pending)

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
    
    def get_stock_reel(self, idarticle, idunite, idmagasin, datetime_cible, stock_manager=None, close_conn=True):
        """
        Récupère le stock réel à une date/heure précise en utilisant StockManager.
        Retourne la valeur formatée ou '-' si impossible.
        
        Args:
            idarticle, idunite, idmagasin, datetime_cible: paramètres du stock
            stock_manager: StockManager instance optionnel (si None, en crée un nouveau)
            close_conn: si True, ferme la connexion après (ignoré si stock_manager est passé)
        """
        try:
            # Si idmagasin est -1, on ne peut pas calculer (tous les magasins)
            if idmagasin == -1 or idmagasin is None:
                return '-'
            
            # Créer ou utiliser le StockManager fourni
            created_sm = False
            if stock_manager is None:
                with open(get_config_path('config.json')) as f:
                    config = json.load(f)
                    db_config = config['database']
                
                stock_manager = StockManager(
                    host=db_config['host'],
                    port=db_config['port'],
                    dbname=db_config['database'],
                    user=db_config['user'],
                    password=db_config['password']
                )
                created_sm = True
            
            # Appeler la fonction pour obtenir le stock à la date précise
            resultat = stock_manager.get_stock_a_date_precise(
                idarticle=idarticle,
                idunite=idunite,
                idmagasin=idmagasin,
                datetime_cible=datetime_cible
            )
            
            # Fermer la connexion seulement si on l'a créée
            if created_sm and close_conn:
                stock_manager.fermer_connexion()
            
            if resultat and 'stock_dans_unite' in resultat:
                stock_value = float(resultat['stock_dans_unite'])
                return self.formater_nombre(stock_value)
            else:
                return '-'
        
        except Exception as e:
            print(f"ERREUR lors du calcul du stock: {str(e)}")
            import traceback
            traceback.print_exc()
            return '-'
    
    def _charger_stocks_background(self):
        """
        Calcule les stocks en arrière-plan dans un thread séparé.
        Met à jour progressivement les lignes du treeview.
        Réutilise une seule connexion pour tous les calculs.
        """
        try:
            # Créer une connexion unique que on réutilisera pour tous les calculs
            with open(get_config_path('config.json')) as f:
                config = json.load(f)
                db_config = config['database']
            
            stock_manager = StockManager(
                host=db_config['host'],
                port=db_config['port'],
                dbname=db_config['database'],
                user=db_config['user'],
                password=db_config['password']
            )
            
            # Boucler sur les lignes en attente
            for pending_info in self.rows_pending:
                # Vérifier si on doit arrêter le thread
                if self.thread_stop_event.is_set():
                    break
                
                idx = pending_info['index']
                
                # Vérifier que l'index est valide
                if idx < len(self.tree_items):
                    item_id = self.tree_items[idx]
                    
                    # Calculer le stock réel (réutilisant la même connexion)
                    stock_value = self.get_stock_reel(
                        idarticle=pending_info['idarticle'],
                        idunite=pending_info['idunite'],
                        idmagasin=pending_info['idmagasin'],
                        datetime_cible=pending_info['datetime_cible'],
                        stock_manager=stock_manager,
                        close_conn=False  # Ne pas fermer, on la réutilise
                    )
                    
                    # Obtenir les valeurs actuelles
                    current_values = list(self.tree.item(item_id, 'values'))
            
                    
                    if len(current_values) > 8:
                        current_values[8] = stock_value
                        
                        # Mettre à jour via after() pour être thread-safe
                        self.after(0, lambda cvals=current_values, iid=item_id: self.tree.item(iid, values=cvals))
            
            # Fermer la connexion une seule fois à la fin
            stock_manager.fermer_connexion()
        
        except Exception as e:
            print(f"ERREUR lors du calcul des stocks en arrière-plan: {str(e)}")
            import traceback
            traceback.print_exc()
    
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
    
    def _update_label_total(self):
        """Met à jour le label_total avec format dynamique selon filtres et mouvements affichés"""
        try:
            # Récupérer les filtres
            date_debut = self.date_debut.get_date().strftime('%d/%m/%Y')
            date_fin = self.date_fin.get_date().strftime('%d/%m/%Y')
            type_mouvement = self.combo_type.get()
            nom_magasin = self.combo_magasin.get()
            
            # Calculer les totaux d'entrée et sortie à partir des items affichés dans le treeview
            total_entree = 0.0
            total_sortie = 0.0
            
            for item_id in self.tree.get_children():
                values = self.tree.item(item_id, 'values')
                
                # Colonnes: 6=Entrée, 7=Sortie
                if len(values) > 7:
                    entree_str = str(values[6]).strip()
                    sortie_str = str(values[7]).strip()
                    
                    # Convertir les nombres formatés (avec espaces et virgules) en float
                    if entree_str and entree_str != '-':
                        try:
                            # Enlever les espaces, remplacer virgule par point
                            entree_num = float(entree_str.replace(' ', '').replace(',', '.'))
                            total_entree += entree_num
                        except ValueError:
                            pass
                    
                    if sortie_str and sortie_str != '-':
                        try:
                            # Enlever les espaces, remplacer virgule par point
                            sortie_num = float(sortie_str.replace(' ', '').replace(',', '.'))
                            total_sortie += sortie_num
                        except ValueError:
                            pass
            
            # Formater les totaux
            total_entree_fmt = self.formater_nombre(total_entree)
            total_sortie_fmt = self.formater_nombre(total_sortie)
            
            # Construire le texte du label
            label_text = (
                f"Du {date_debut} au {date_fin} | "
                f"Mouvement : {type_mouvement} ; Magasin {nom_magasin} | "
                f"Entrée : {total_entree_fmt}; Sortie : {total_sortie_fmt}"
            )
            
            self.label_total.configure(text=label_text)
        
        except Exception as e:
            print(f"ERREUR lors de la mise à jour du label_total: {str(e)}")
            self.label_total.configure(text="Erreur lors du calcul des totaux")
    
    def _adjust_column_widths(self):
        """Ajuste automatiquement la largeur des colonnes selon leur contenu"""
        import tkinter.font as tkFont
        
        # Créer une police pour mesurer la largeur du texte
        font = tkFont.Font(font=('Segoe UI', 8))
        
        # Colonnes à ajuster (exclure les colonnes cachées)
        visible_columns = [
            col for col in self.tree['columns'] 
            if col not in ["#", "idArticle", "idUnite", "idMagasin"]
        ]
        
        for col in visible_columns:
            # Obtenir le texte du heading
            heading_text = self.tree.heading(col)['text']
            max_width = font.measure(heading_text) + 15
            
            # Itérer sur les premiers items visibles (optimisation performance)
            all_items = self.tree.get_children()
            sample_items = all_items[:50]  # Examiner seulement les 50 premiers
            
            for item_id in sample_items:
                item_values = self.tree.item(item_id, 'values')
                col_index = list(self.tree['columns']).index(col)
                
                if col_index < len(item_values):
                    cell_text = str(item_values[col_index])
                    cell_width = font.measure(cell_text) + 15
                    max_width = max(max_width, cell_width)
            
            # Limiter la largeur entre un minimum et un maximum raisonnable
            min_width = 60
            max_width_limit = 400
            final_width = max(min_width, min(max_width, max_width_limit))
            
            # Appliquer la largeur calculée
            self.tree.column(col, width=int(final_width))
    
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
                WHERE u.idunite = %s AND v.deleted = 0 AND vd.deleted = 0
                AND v.statut = 'VALIDEE' AND DATE(v.dateregistre) < %s
                
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
        columns = ("#", "Date", "Référence", "Type", "Désignation", "Unité", "Entrée", "Sortie", "Stock", "Magasin", "Description", "idArticle", "idUnite", "idMagasin")
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
            "#": 0,
            "Date": 160,
            "Référence": 120,
            "Type": 120,
            "Désignation": 220,
            "Unité": 100,
            "Entrée": 100,
            "Sortie": 100,
            "Stock": 120,
            "Magasin": 70,
            "Description": 250,
            "idArticle": 0,  # Hidden
            "idUnite": 0,    # Hidden
            "idMagasin": 0   # Hidden
        }
        
        for col in columns:
            # Masquer les colonnes (largeur 0)
            if col in ["#", "idArticle", "idUnite", "idMagasin"]:
                self.tree.heading(col, text=col)
                self.tree.column(col, width=0, stretch="no")
            else:
                self.tree.heading(col, text=col)
                width = column_widths.get(col, 100)
                self.tree.column(col, width=width, anchor="w")  # Aligner à gauche
        
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
                    u.codearticle,
                    a.idarticle,
                    u.idunite as idunite_dup,
                    COALESCE(lf.idmag, -1),
                    COALESCE('[FRS: ' || frs.nomfrs || ' , ref. Commande: ' || c.refcom || '] ' || COALESCE(lf.reflivfrs, ''), '')
                FROM tb_livraisonfrs lf
                INNER JOIN tb_unite u ON lf.idunite = u.idunite
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN tb_magasin m ON lf.idmag = m.idmag
                LEFT JOIN tb_users usr ON lf.iduser = usr.iduser
                LEFT JOIN tb_commande c ON lf.idcom = c.idcom
                LEFT JOIN tb_commandedetail cd ON c.idcom = cd.idcom AND cd.idarticle = a.idarticle
                LEFT JOIN tb_fournisseur frs ON cd.idfrs = frs.idfrs
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
                    u.codearticle,
                    a.idarticle,
                    u.idunite as idunite_dup,
                    COALESCE(sd.idmag, -1),
                    COALESCE(sd.motif, '')
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
                    u.codearticle,
                    a.idarticle,
                    u.idunite as idunite_dup,
                    COALESCE(vd.idmag, -1),
                    '[CL: ' || COALESCE(cl.nomcli, 'N/A') || '] vente ' || COALESCE(mp.modedepaiement, 'N/A') || ' validée!'
                FROM tb_vente v
                INNER JOIN tb_ventedetail vd ON v.id = vd.idvente
                INNER JOIN tb_unite u ON vd.idunite = u.idunite
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN tb_magasin m ON vd.idmag = m.idmag
                LEFT JOIN tb_users usr ON v.iduser = usr.iduser
                LEFT JOIN tb_client cl ON v.idclient = cl.idclient
                LEFT JOIN tb_modepaiement mp ON v.idmode = mp.idmode
                WHERE DATE(v.dateregistre) BETWEEN %s AND %s
                AND v.deleted = 0 AND vd.deleted = 0
                AND v.statut = 'VALIDEE'
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
                    u.codearticle,
                    a.idarticle,
                    u.idunite as idunite_dup,
                    COALESCE(td.idmagsortie, -1),
                    COALESCE(td.description, '')
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
                    u.codearticle,
                    a.idarticle,
                    u.idunite as idunite_dup,
                    COALESCE(td.idmagentree, -1),
                    COALESCE(td.description, '')
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
                    u.codearticle,
                    a.idarticle,
                    u.idunite as idunite_dup,
                    COALESCE(i.idmag, -1),
                    COALESCE(i.observation, '')
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
                    u.codearticle,
                    a.idarticle,
                    u.idunite as idunite_dup,
                    COALESCE(ad.idmag, -1),
                    COALESCE(av.observation, '')
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
                    u.codearticle,
                    a.idarticle,
                    u.idunite as idunite_dup,
                    COALESCE(cid.idmag, -1),
                    COALESCE(cid.observation, '')
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
                    u.codearticle,
                    a.idarticle,
                    u.idunite as idunite_dup,
                    COALESCE(dcs.idmagasin, -1),
                    COALESCE(chg.note, '')
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
                    u.codearticle,
                    a.idarticle,
                    u.idunite as idunite_dup,
                    COALESCE(dce.idmagasin, -1),
                    COALESCE(chg.note, '')
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
            self.rows_pending = []  # Réinitialiser la liste des lignes en attente
            
            for idx, mouv in enumerate(mouvements, 1):
                date_format = mouv[0].strftime('%d/%m/%Y %H:%M:%S') if mouv[0] else ""
                reference = mouv[1] or ""
                article_designation = mouv[2] or ""
                type_doc_display = mouv[3] or ""
                entree = float(mouv[4]) if mouv[4] else 0
                sortie = float(mouv[5]) if mouv[5] else 0
                magasin_display = mouv[6] or ""
                username = mouv[7] or ""
                idunite = mouv[8]
                idarticle = mouv[10]  # Index 10: a.idarticle
                idmag = mouv[12]      # Index 12: idmag
                description = mouv[13] if mouv[13] else "-"  # Index 13: description

                # Récupérer la désignation de l'unité
                cursor.execute("SELECT designationunite FROM tb_unite WHERE idunite = %s", (idunite,))
                result = cursor.fetchone()
                unite_display = result[0] if result else ""

                # Préparation de la valeur temporaire pour Stock (affichera "En cours..." le temps du calcul)
                stock_value = "En cours..."
                
                # Stocker les infos nécessaires pour le calcul du stock en arrière-plan
                datetime_cible = mouv[0].strftime('%Y-%m-%d %H:%M:%S') if mouv[0] else ""
                self.rows_pending.append({
                    'index': idx - 1,  # Index dans la liste
                    'idarticle': idarticle,
                    'idunite': idunite,
                    'idmagasin': int(idmag) if idmag != -1 else -1,
                    'datetime_cible': datetime_cible,
                    'unite_display': unite_display  # Ajouter la désignation de l'unité
                })

                
                row_values = (
                    str(idx),  # Index number
                    date_format,
                    reference,
                    type_doc_display,
                    article_designation,
                    unite_display,
                    '-' if entree == 0 else self.formater_nombre(entree),
                    '-' if sortie == 0 else self.formater_nombre(sortie),
                    stock_value,  # Valeur temporaire
                    magasin_display,
                    description,  # Description
                    str(idarticle),  # Hidden: idArticle
                    str(idunite),    # Hidden: idUnite
                    str(idmag)       # Hidden: idMagasin
                )

                rows_to_display.append(row_values)

            # Insérer toutes les lignes dans le treeview et stocker les item_ids
            self.tree_items = []
            for idx, row in enumerate(rows_to_display):
                tag = "even" if idx % 2 == 0 else "odd"
                item_id = self.tree.insert("", "end", values=row, tags=(tag,))
                self.tree_items.append(item_id)

            # Sauvegarder la liste complète pour le filtrage côté client
            self.full_display_rows = rows_to_display
            self._original_rows_pending = list(self.rows_pending)  # Sauvegarder les rows_pending originaux
            
            cursor.close()
            
            # Mettre à jour le label avec infos dynamiques
            self._update_label_total()
            
            # Ajuster la largeur des colonnes selon le contenu
            self._adjust_column_widths()
            
            # Lancer le calcul des stocks en arrière-plan dans un thread
            self._relancer_calcul_stocks_filtres()
            
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des mouvements: {err}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur inattendue: {str(e)}")
        finally:
            conn.close()

    def _relancer_calcul_stocks_filtres(self):
        """
        Arrête le thread de calcul précédent et relance un nouveau avec les rows_pending actuels.
        Cette méthode est appelée après load_mouvements() ou après un filtrage.
        """
        if self.rows_pending:
            # Arrêter le thread précédent si en cours
            if self.stock_thread and self.stock_thread.is_alive():
                self.thread_stop_event.set()
                self.stock_thread.join(timeout=1)
            
            # Créer un nouvel événement d'arrêt
            self.thread_stop_event.clear()
            
            # Démarrer le nouveau thread
            self.stock_thread = threading.Thread(
                target=self._charger_stocks_background,
                daemon=True
            )
            self.stock_thread.start()
    
    def filter_tree_by_text(self, event=None):
        """Filtre le treeview côté client selon le texte saisi (toutes colonnes)."""
        search = self.entry_recherche_article.get().strip().lower()
        rows = getattr(self, 'full_display_rows', [])
        original_pending = getattr(self, '_original_rows_pending', [])

        # Vider le treeview
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not search:
            # Réafficher tous les mouvements
            self.tree_items = []
            for idx, row in enumerate(rows):
                tag = "even" if idx % 2 == 0 else "odd"
                item_id = self.tree.insert("", "end", values=row, tags=(tag,))
                self.tree_items.append(item_id)
            
            # Restaurer les rows_pending originaux
            self.rows_pending = list(original_pending)
            
            # Mettre à jour le label avec infos dynamiques
            self._update_label_total()
            
            # Relancer le calcul des stocks pour TOUS les mouvements
            self._relancer_calcul_stocks_filtres()
            return

        # Filtrer les lignes par texte
        filtered = []
        filtered_indices = []
        
        for row_idx, row in enumerate(rows):
            # Vérifier si le texte est présent dans une des colonnes
            match = False
            for cell in row:
                if search in str(cell).lower():
                    match = True
                    break
            if match:
                filtered.append(row)
                filtered_indices.append(row_idx)

        # Réinsérer les lignes filtrées dans le treeview
        self.tree_items = []
        for idx, row in enumerate(filtered):
            tag = "even" if idx % 2 == 0 else "odd"
            item_id = self.tree.insert("", "end", values=row, tags=(tag,))
            self.tree_items.append(item_id)

        # Mettre à jour le label avec infos dynamiques
        self._update_label_total()
        
        # Créer une nouvelle liste rows_pending SEULEMENT pour les lignes filtrées
        filtered_pending = [original_pending[idx] for idx in filtered_indices if idx < len(original_pending)]
        
        # Mettre à jour les indices dans rows_pending pour correspondre aux nouveaux item_ids
        self.rows_pending = []
        for new_idx, orig_idx in enumerate(filtered_indices):
            if orig_idx < len(original_pending):
                # Copier l'entrée et mettre à jour l'index
                pending_info = original_pending[orig_idx].copy()
                pending_info['index'] = new_idx
                self.rows_pending.append(pending_info)
        
        # Ajuster la largeur des colonnes selon le contenu filtré
        self._adjust_column_widths()
        
        # Relancer le calcul des stocks SEULEMENT pour les lignes filtrées
        self._relancer_calcul_stocks_filtres()
        
        # Mettre à jour le label avec infos dynamiques (appelé à nouveau après le filtrage)
        self._update_label_total()


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
