import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import json
from datetime import datetime, timedelta
import threading
from tkinter import ttk
from resource_utils import get_config_path, safe_file_read



# Importations des classes externes
from pages.page_peremption import PageGestionPeremption
from pages.page_inventaire import PageInventaire

class PageStock(ctk.CTkFrame):
    def __init__(self, master, db_conn=None, session_data=None, iduser=None):
        super().__init__(master)
        self.clignotement_actif = False
        self.couleur_alerte = "#d32f2f"
        
        # Gestion robuste de l'ID utilisateur pour la traçabilité
        if iduser is not None:
            self.iduser = iduser
        elif session_data and 'user_id' in session_data:
            self.iduser = session_data['user_id']
        else:
            self.iduser = 1  
            
        self.magasins = []
        self.colonnes_dynamiques = []
        self.all_data = []  # Pour stocker toutes les données pour le filtrage
        
        self.setup_ui()
        self.charger_magasins()
        self.charger_stocks()
    
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
        except Exception as err:
            messagebox.showerror("Erreur de connexion", f"Erreur : {err}")
            return None

    def formater_nombre(self, nombre):
        """Formate les nombres pour l'affichage (ex: 1.250,00)"""
        try:
            return f"{float(nombre):,.2f}".replace(',', ' ').replace('.', ',').replace(' ', '.')
        except:
            return "0,00"

    def setup_ui(self):
        # Titre
        titre = ctk.CTkLabel(self, text="📦 Gestion des Stocks", font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"))
        titre.pack(pady=10)
        
        # Frame de recherche
        frame_recherche = ctk.CTkFrame(self)
        frame_recherche.pack(fill="x", padx=20, pady=10)
        
        # Champ de recherche avec binding KeyRelease
        self.entry_recherche = ctk.CTkEntry(frame_recherche, placeholder_text="Code, désignation...", width=300)
        self.entry_recherche.pack(side="left", padx=5)
        self.entry_recherche.bind('<KeyRelease>', lambda event: self.filtrer_stocks())
        
        # Bouton Réinitialiser
        ctk.CTkButton(frame_recherche, text="🔄 Réinitialiser", command=self.reinitialiser_filtre, fg_color="#2e7d32").pack(side="left", padx=10)
        
        # Boutons à droite
        self.btn_peremption = ctk.CTkButton(frame_recherche, text="🛡️ Articles Périmés", command=self.ouvrir_fenetre_peremption, fg_color="#d32f2f")
        self.btn_peremption.pack(side="right", padx=10)

        self.btn_export = ctk.CTkButton(frame_recherche, text="📊 Export Excel", command=self.exporter_stocks, fg_color="#0288d1")
        self.btn_export.pack(side="right", padx=10)
        
        # Zone du Treeview
        self.tree_frame_inner = ctk.CTkFrame(self)
        self.tree_frame_inner.pack(fill="both", expand=True, padx=20, pady=10)
        self.tree = None 

        # Barre d'état
        frame_info = ctk.CTkFrame(self)
        frame_info.pack(fill="x", padx=20, pady=10)
        
        self.label_total_articles = ctk.CTkLabel(frame_info, text="Total articles: 0", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        self.label_total_articles.pack(side="left", padx=20)
        
        self.label_derniere_maj = ctk.CTkLabel(frame_info, text="Dernière mise à jour: --", font=ctk.CTkFont(family="Segoe UI", size=12))
        self.label_derniere_maj.pack(side="right", padx=20)

    def creer_treeview(self):
        """Initialise le tableau avec colonnes larges et barres de défilement"""
        if self.tree:
            self.tree.destroy()
        
        # Ne pas afficher la colonne Prix dans le tableau de stock
        colonnes_fixes = ("Code", "Désignation", "Unité")
        colonnes_magasins = [mag[1] for mag in self.magasins]
        self.colonnes_dynamiques = colonnes_fixes + tuple(colonnes_magasins) + ("Total",)
        
        # 1. Création du Treeview avec selectmode et gestion du scroll horizontal
        self.tree = ttk.Treeview(
            self.tree_frame_inner, 
            columns=self.colonnes_dynamiques, 
            show="headings",
            selectmode="browse"
        )
        self.tree.tag_configure("even", background="#FFFFFF", foreground="#000000")
        self.tree.tag_configure("odd", background="#E6EFF8", foreground="#000000")
        # Alerte Total=0: texte rouge clair, en conservant le fond alterné
        self.tree.tag_configure("stock_zero_even", background="#FFFFFF", foreground="#f55f5f")
        self.tree.tag_configure("stock_zero_odd", background="#E6EFF8", foreground="#f55f5f")
        
        # ✅ LIAISON DU DOUBLE-CLIC
        self.tree.bind("<Double-1>", self.ouvrir_inventaire_double_clic)
        
        # 2. Configuration des barres de défilement
        vsb = ctk.CTkScrollbar(self.tree_frame_inner, orientation="vertical", command=self.tree.yview)
        hsb = ctk.CTkScrollbar(self.tree_frame_inner, orientation="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # 3. Placement avec grid pour que les barres s'alignent correctement
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # Configurer le poids des lignes/colonnes pour l'extension
        self.tree_frame_inner.grid_rowconfigure(0, weight=1)
        self.tree_frame_inner.grid_columnconfigure(0, weight=1)
        
        # 4. Définition des colonnes (Désignation à gauche et plus large)
        for col in self.colonnes_dynamiques:
            self.tree.heading(col, text=col)
            if col == "Désignation":
                self.tree.column(col, width=350, anchor='w', minwidth=200) # Alignement Gauche
            elif col == "Code":
                self.tree.column(col, width=150, anchor='center')
            else:
                self.tree.column(col, width=110, anchor='center')

    def charger_stocks_avec_progression(self):
        """Charge les stocks avec une fenêtre de progression"""
    
        # Crée la fenêtre de progression
        progress_window = ctk.CTkToplevel(self.root)
        progress_window.title("Chargement en cours...")
        progress_window.geometry("400x150")
        progress_window.transient(self.root)
        progress_window.grab_set()
    
        # Centre la fenêtre
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (progress_window.winfo_screenheight() // 2) - (150 // 2)
        progress_window.geometry(f"400x150+{x}+{y}")
    
        # Label et barre de progression
        label = ctk.CTkLabel(progress_window, text="Chargement des stocks...", font=("Arial", 12))
        label.pack(pady=20)
    
        progress_bar = ttk.Progressbar(progress_window, mode='indeterminate', length=300)
        progress_bar.pack(pady=10)
        progress_bar.start(10)
    
        label_status = ctk.CTkLabel(progress_window, text="Veuillez patienter...", font=("Arial", 9))
        label_status.pack(pady=10)
    
        def charger_en_arriere_plan():
            try:
                self.charger_stocks()
                progress_window.after(0, progress_window.destroy)
            except Exception as e:
                progress_window.after(0, progress_window.destroy)
                messagebox.showerror("Erreur", f"Erreur lors du chargement: {str(e)}")
    
        # Lance le chargement dans un thread séparé
        thread = threading.Thread(target=charger_en_arriere_plan, daemon=True)
        thread.start()

    def charger_stocks(self):
        """Charge les stocks détaillés par magasin - VERSION ULTRA OPTIMISÉE"""
        self.creer_treeview()
        conn = self.connect_db()
        if not conn: 
            return
    
        try:
            cursor = conn.cursor()
            
            print("Chargement des stocks en cours...")
        
            # ✅ REQUÊTE CONSOLIDÉE (V2) : Calcul du stock avec 10 SOURCES de données
            # Les articles liés (même idarticle, unités différentes) sont reliés via qtunite de tb_unite.
            #
            # SOURCES INCLUSES :
            #   ✅ Réceptions (tb_livraisonfrs)
            #   ✅ Ventes validées (tb_ventedetail)
            #   ✅ Sorties BS (tb_sortiedetail)
            #   ✅ Transferts (tb_transfertdetail) - IN et OUT
            #   ✅ Inventaires (tb_inventaire)
            #   ✅ Avoirs (tb_avoirdetail) - Retours de marchandise
            #   ✅ Consommation Interne (tb_consommationinterne_details) - NOUVEAU
            #   ✅ Échanges Entrée (tb_detailchange_entree) - NOUVEAU
            #   ✅ Échanges Sortie (tb_detailchange_sortie) - NOUVEAU
            #
            # LOGIQUE :
            #   1) mouvements_bruts   → chaque mouvement converti en "unité de base"
            #   2) solde_base_par_mag → somme tous les mouvements par (idarticle, idmag) 
            #   3) Requête finale     → divise par qtunite pour obtenir stock affiché
            # ✅ Requête consolidée avec les 9 sources de mouvements + coefficient hiérarchique
            query_optimisee = """
            WITH mouvements_bruts AS (
                -- Réceptions (tb_livraisonfrs)
                SELECT
                    lf.idarticle,
                    lf.idmag,
                    COALESCE(u.qtunite, 1) as qtunite_source,
                    lf.qtlivrefrs as quantite,
                    'reception' as type_mouvement
                FROM tb_livraisonfrs lf
                INNER JOIN tb_unite u ON lf.idarticle = u.idarticle AND lf.idunite = u.idunite
                WHERE lf.deleted = 0

                UNION ALL

                -- Ventes (tb_ventedetail)
                SELECT
                    vd.idarticle,
                    v.idmag,
                    COALESCE(u.qtunite, 1) as qtunite_source,
                    vd.qtvente as quantite,
                    'vente' as type_mouvement
                FROM tb_ventedetail vd
                INNER JOIN tb_vente v ON vd.idvente = v.id AND v.deleted = 0 AND v.statut = 'VALIDEE'
                INNER JOIN tb_unite u ON vd.idarticle = u.idarticle AND vd.idunite = u.idunite
                WHERE vd.deleted = 0

                UNION ALL

                -- Transferts entrants
                SELECT
                    t.idarticle,
                    t.idmagentree as idmag,
                    COALESCE(u.qtunite, 1) as qtunite_source,
                    t.qttransfert as quantite,
                    'transfert_in' as type_mouvement
                FROM tb_transfertdetail t
                INNER JOIN tb_unite u ON t.idarticle = u.idarticle AND t.idunite = u.idunite
                WHERE t.deleted = 0

                UNION ALL

                -- Transferts sortants
                SELECT
                    t.idarticle,
                    t.idmagsortie as idmag,
                    COALESCE(u.qtunite, 1) as qtunite_source,
                    t.qttransfert as quantite,
                    'transfert_out' as type_mouvement
                FROM tb_transfertdetail t
                INNER JOIN tb_unite u ON t.idarticle = u.idarticle AND t.idunite = u.idunite
                WHERE t.deleted = 0

                UNION ALL

                -- Sorties (tb_sortiedetail)
                SELECT
                    sd.idarticle,
                    sd.idmag,
                    COALESCE(u.qtunite, 1) as qtunite_source,
                    sd.qtsortie as quantite,
                    'sortie' as type_mouvement
                FROM tb_sortiedetail sd
                INNER JOIN tb_unite u ON sd.idarticle = u.idarticle AND sd.idunite = u.idunite

                UNION ALL

                -- Inventaires (une seule fois par article = unité de base)
                SELECT
                    u.idarticle,
                    i.idmag,
                    COALESCE(u.qtunite, 1) as qtunite_source,
                    i.qtinventaire as quantite,
                    'inventaire' as type_mouvement
                FROM tb_inventaire i
                INNER JOIN tb_unite u ON i.codearticle = u.codearticle
                WHERE u.idunite IN (
                    SELECT DISTINCT ON (idarticle) idunite
                    FROM tb_unite
                    WHERE deleted = 0
                    ORDER BY idarticle, qtunite ASC
                )

                UNION ALL

                -- Avoirs (augmentent le stock = retour marchandises)
                SELECT
                    ad.idarticle,
                    ad.idmag,
                    COALESCE(u.qtunite, 1) as qtunite_source,
                    ad.qtavoir as quantite,
                    'avoir' as type_mouvement
                FROM tb_avoir a
                INNER JOIN tb_avoirdetail ad ON a.id = ad.idavoir
                INNER JOIN tb_unite u ON ad.idarticle = u.idarticle AND ad.idunite = u.idunite
                WHERE a.deleted = 0 AND ad.deleted = 0

                UNION ALL

                -- Consommation interne (diminue le stock)
                SELECT
                    cd.idarticle,
                    cd.idmag,
                    COALESCE(u.qtunite, 1) as qtunite_source,
                    cd.qtconsomme as quantite,
                    'consommation_interne' as type_mouvement
                FROM tb_consommationinterne_details cd
                INNER JOIN tb_unite u ON cd.idarticle = u.idarticle AND cd.idunite = u.idunite

                UNION ALL

                -- Échanges entrée (augmentent le stock)
                SELECT
                    dce.idarticle,
                    dce.idmagasin,
                    COALESCE(u.qtunite, 1) as qtunite_source,
                    dce.quantite_entree as quantite,
                    'echange_entree' as type_mouvement
                FROM tb_detailchange_entree dce
                INNER JOIN tb_unite u ON dce.idarticle = u.idarticle AND dce.idunite = u.idunite

                UNION ALL

                -- Échanges sortie (diminuent le stock)
                SELECT
                    dcs.idarticle,
                    dcs.idmagasin,
                    COALESCE(u.qtunite, 1) as qtunite_source,
                    dcs.quantite_sortie as quantite,
                    'echange_sortie' as type_mouvement
                FROM tb_detailchange_sortie dcs
                INNER JOIN tb_unite u ON dcs.idarticle = u.idarticle AND dcs.idunite = u.idunite
            ),

            solde_base_par_mag AS (
                SELECT
                    idarticle,
                    idmag,
                    SUM(
                        CASE type_mouvement
                            WHEN 'reception'             THEN  quantite * qtunite_source
                            WHEN 'transfert_in'          THEN  quantite * qtunite_source
                            WHEN 'inventaire'            THEN  quantite * qtunite_source
                            WHEN 'avoir'                 THEN  quantite * qtunite_source
                            WHEN 'echange_entree'        THEN  quantite * qtunite_source
                            WHEN 'vente'                 THEN -quantite * qtunite_source
                            WHEN 'sortie'                THEN -quantite * qtunite_source
                            WHEN 'transfert_out'         THEN -quantite * qtunite_source
                            WHEN 'consommation_interne'  THEN -quantite * qtunite_source
                            WHEN 'echange_sortie'        THEN -quantite * qtunite_source
                            ELSE 0
                        END
                    ) as solde_base
                FROM mouvements_bruts
                GROUP BY idarticle, idmag
            ),

            unite_hierarchie AS (
                SELECT idarticle, idunite, niveau, qtunite, designationunite
                FROM tb_unite
                WHERE deleted = 0
            ),

            unite_coeff AS (
                SELECT
                    idarticle,
                    idunite,
                    niveau,
                    qtunite,
                    designationunite,
                    exp(sum(ln(NULLIF(CASE WHEN qtunite > 0 THEN qtunite ELSE 1 END, 0)))
                        OVER (PARTITION BY idarticle ORDER BY niveau ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                    ) as coeff_hierarchique
                FROM unite_hierarchie
            )

            SELECT
                u.codearticle,
                a.designation,
                u.designationunite,
                COALESCE(
                    (SELECT cd.punitcmd
                     FROM tb_commandedetail cd
                     INNER JOIN tb_commande c ON cd.idcom = c.idcom
                     WHERE cd.idarticle = u.idarticle
                       AND cd.idunite = u.idunite
                       AND c.deleted = 0
                     ORDER BY c.datecom DESC
                     LIMIT 1), 0
                ) as prixachat,
                u.idarticle,
                u.idunite,
                m.idmag,
                COALESCE(sb.solde_base, 0) / NULLIF(COALESCE(uc.coeff_hierarchique, 1), 0) as stock
            FROM tb_unite u
            INNER JOIN tb_article a ON u.idarticle = a.idarticle
            CROSS JOIN tb_magasin m
            LEFT JOIN solde_base_par_mag sb
                ON sb.idarticle = u.idarticle
                AND sb.idmag = m.idmag
            LEFT JOIN unite_coeff uc
                ON uc.idarticle = u.idarticle
                AND uc.idunite = u.idunite
            WHERE a.deleted = 0
              AND m.deleted = 0
            ORDER BY a.designation ASC, u.codearticle ASC
            """
            
            cursor.execute(query_optimisee)
            resultats = cursor.fetchall()
            
            print(f"Données récupérées: {len(resultats)} lignes")
        
            # Regrouper par article
            articles_dict = {}
            for code, desig, unite, prix, idarticle, idunite, idmag, stock in resultats:
                if code not in articles_dict:
                    articles_dict[code] = {
                        'designation': desig,
                        'unite': unite,
                        'prix': prix,
                        'stocks': {},
                        'total': 0
                    }
                
                # Ajouter le stock pour ce magasin
                if idmag:
                    nom_mag = next((m[1] for m in self.magasins if m[0] == idmag), f"Mag{idmag}")
                    stock_val = max(0, stock or 0)
                    articles_dict[code]['stocks'][nom_mag] = stock_val
                    articles_dict[code]['total'] += stock_val
            
            print(f"Articles traités: {len(articles_dict)}")
            
            # Stocker toutes les données pour le filtrage
            self.all_data = []
            
            # Insérer dans le Treeview ET stocker dans all_data
            compteur = 0
            for idx, (code, data) in enumerate(articles_dict.items()):
                # Ne pas inclure le prix dans les valeurs affichées
                valeurs = [
                    code,
                    data['designation'],
                    data['unite']
                ]
            
                # Ajouter les stocks par magasin
                for _, nom_mag in self.magasins:
                    valeurs.append(self.formater_nombre(data['stocks'].get(nom_mag, 0)))
            
                # Ajouter le total
                valeurs.append(self.formater_nombre(data['total']))
                
                # Stocker les données
                self.all_data.append((valeurs, data['total']))  # Stocker les valeurs et le total pour le tag
            
                # TAG POUR ALERTE STOCK BAS
                zebra_tag = "even" if idx % 2 == 0 else "odd"
                if abs(float(data['total'])) < 1e-9:
                    zero_tag = "stock_zero_even" if zebra_tag == "even" else "stock_zero_odd"
                    self.tree.insert("", "end", values=valeurs, tags=(zero_tag,))
                else:
                    self.tree.insert("", "end", values=valeurs, tags=(zebra_tag,))
                
                compteur += 1
                if compteur % 100 == 0:
                    print(f"Insertion: {compteur} articles...")
        
            # Style déjà défini via stock_zero_even/stock_zero_odd
        
            # Mise à jour des infos
            self.label_total_articles.configure(text=f"Total articles: {len(articles_dict)}")
            self.label_derniere_maj.configure(text=f"Dernière mise à jour: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            
            print(f"Chargement terminé: {len(articles_dict)} articles affichés")
        
            # Vérifier les péremptions
            self.mettre_a_jour_badge_peremption()
        
        except Exception as e:
            print(f"ERREUR DÉTAILLÉE: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Erreur de chargement", f"Détails : {str(e)}")
        finally:
            cursor.close()
            conn.close()

    def calculer_stock_article(self, idarticle, idunite_cible, idmag=None):
        """
        ✅ CALCUL CONSOLIDÉ (V2) : 
        Relie tous les mouvements de toutes les unités (PIECE, CARTON, etc.) 
        d'un même idarticle via le coefficient 'qtunite' de tb_unite.
        
        Prend en compte 10 SOURCES de données :
        - Réceptions (tb_livraisonfrs) → +stock
        - Ventes (tb_ventedetail) → -stock
        - Sorties BS (tb_sortiedetail) → -stock
        - Transferts IN et OUT (tb_transfertdetail) → +/- stock
        - Inventaires (tb_inventaire) → +stock
        - Avoirs (tb_avoir/tb_avoirdetail.qtavoir) → +stock (retour marchandise)
        - Consommation Interne (tb_consommationinterne_details) → -stock
        - Échanges Entrée (tb_detailchange_entree) → +stock
        - Échanges Sortie (tb_detailchange_sortie) → -stock
        """
        conn = self.connect_db()
        if not conn: return 0
    
        try:
            cursor = conn.cursor()
            
            # 1. Récupérer TOUTES les unités liées à cet idarticle
            cursor.execute("""
                SELECT idunite, codearticle, COALESCE(qtunite, 1) 
                FROM tb_unite 
                WHERE idarticle = %s
            """, (idarticle,))
            unites_liees = cursor.fetchall()
            
            # 2. Identifier le qtunite de l'unité qu'on veut afficher
            qtunite_affichage = 1
            for idu, code, qt_u in unites_liees:
                if idu == idunite_cible:
                    qtunite_affichage = qt_u if qt_u > 0 else 1
                    break

            total_stock_global_base = 0 # Le "réservoir" total en unité de base (qtunite=1)

            # 3. Sommer les mouvements de chaque variante
            for idu_boucle, code_boucle, qtunite_boucle in unites_liees:
                # Réceptions
                q_rec = "SELECT COALESCE(SUM(qtlivrefrs), 0) FROM tb_livraisonfrs WHERE idarticle = %s AND idunite = %s AND deleted = 0"
                p_rec = [idarticle, idu_boucle]
                if idmag: q_rec += " AND idmag = %s"; p_rec.append(idmag)
                cursor.execute(q_rec, p_rec)
                receptions = cursor.fetchone()[0] or 0
        
                # Ventes
                q_ven = "SELECT COALESCE(SUM(qtvente), 0) FROM tb_ventedetail WHERE idarticle = %s AND idunite = %s AND deleted = 0"
                p_ven = [idarticle, idu_boucle]
                if idmag: q_ven += " AND idmag = %s"; p_ven.append(idmag)
                cursor.execute(q_ven, p_ven)
                ventes = cursor.fetchone()[0] or 0
        
                 # Sorties
                q_sort = "SELECT COALESCE(SUM(qtsortie), 0) FROM tb_sortiedetail WHERE idarticle = %s AND idunite = %s"
                p_sort = [idarticle, idu_boucle]
                if idmag: q_sort += " AND idmag = %s"; p_sort.append(idmag)
                
                # DEBUG - À SUPPRIMER APRÈS
                print(f"DEBUG SORTIES - Query: {q_sort}")
                print(f"DEBUG SORTIES - Params: {p_sort}")
                
                cursor.execute(q_sort, p_sort)
                sorties = cursor.fetchone()[0] or 0
                
                # DEBUG - À SUPPRIMER APRÈS
                print(f"DEBUG SORTIES - Résultat: {sorties}")
        
                # Transferts (In et Out)
                cursor.execute("SELECT COALESCE(SUM(qttransfert), 0) FROM tb_transfertdetail WHERE idarticle = %s AND idunite = %s AND deleted = 0" + (" AND idmagentree = %s" if idmag else ""), ([idarticle, idu_boucle, idmag] if idmag else [idarticle, idu_boucle]))
                t_in = cursor.fetchone()[0] or 0
                
                cursor.execute("SELECT COALESCE(SUM(qttransfert), 0) FROM tb_transfertdetail WHERE idarticle = %s AND idunite = %s AND deleted = 0" + (" AND idmagsortie = %s" if idmag else ""), ([idarticle, idu_boucle, idmag] if idmag else [idarticle, idu_boucle]))
                t_out = cursor.fetchone()[0] or 0
        
                # Inventaires (via codearticle)
                q_inv = "SELECT COALESCE(SUM(qtinventaire), 0) FROM tb_inventaire WHERE codearticle = %s"
                p_inv = [code_boucle]
                if idmag: q_inv += " AND idmag = %s"; p_inv.append(idmag)
                cursor.execute(q_inv, p_inv)
                inv = cursor.fetchone()[0] or 0

                # Avoirs (AUGMENTENT le stock - annulation de vente)
                q_avoir = """
                    SELECT COALESCE(SUM(ad.qtavoir), 0) 
                    FROM tb_avoirdetail ad
                    INNER JOIN tb_avoir a ON ad.idavoir = a.id
                    WHERE ad.idarticle = %s AND ad.idunite = %s 
                    AND a.deleted = 0 AND ad.deleted = 0
                """
                p_avoir = [idarticle, idu_boucle]
                if idmag: q_avoir += " AND ad.idmag = %s"; p_avoir.append(idmag)
                cursor.execute(q_avoir, p_avoir)
                avoirs = cursor.fetchone()[0] or 0

                # Consommation Interne (DIMINUE le stock)
                q_conso = "SELECT COALESCE(SUM(qtconsomme), 0) FROM tb_consommationinterne_details WHERE idarticle = %s AND idunite = %s"
                p_conso = [idarticle, idu_boucle]
                if idmag: q_conso += " AND idmag = %s"; p_conso.append(idmag)
                cursor.execute(q_conso, p_conso)
                consommations = cursor.fetchone()[0] or 0

                # Échanges Entrée (AUGMENTE le stock)
                q_echange_in = "SELECT COALESCE(SUM(quantite_entree), 0) FROM tb_detailchange_entree WHERE idarticle = %s AND idunite = %s"
                p_echange_in = [idarticle, idu_boucle]
                if idmag: q_echange_in += " AND idmagasin = %s"; p_echange_in.append(idmag)
                cursor.execute(q_echange_in, p_echange_in)
                echange_entrees = cursor.fetchone()[0] or 0

                # Échanges Sortie (DIMINUE le stock)
                q_echange_out = "SELECT COALESCE(SUM(quantite_sortie), 0) FROM tb_detailchange_sortie WHERE idarticle = %s AND idunite = %s"
                p_echange_out = [idarticle, idu_boucle]
                if idmag: q_echange_out += " AND idmagasin = %s"; p_echange_out.append(idmag)
                cursor.execute(q_echange_out, p_echange_out)
                echange_sorties = cursor.fetchone()[0] or 0

                # ✅ Normalisation finale avec les 10 sources de données
                # ENTRÉES (+): Réceptions, Transferts IN, Inventaires, Avoirs, Échanges Entrée
                # SORTIES (-): Ventes, Sorties BS, Transferts OUT, Consomm. Interne, Échanges Sortie
                solde_unite = (receptions + t_in + inv + avoirs + echange_entrees - ventes - sorties - t_out - consommations - echange_sorties)
                total_stock_global_base += (solde_unite * qtunite_boucle)

            # 4. Conversion finale pour l'affichage
            stock_final = total_stock_global_base / qtunite_affichage
            return max(0, stock_final)
        
        except Exception as e:
            print(f"Erreur calcul stock consolidé : {e}")
            return 0
        finally:
            cursor.close()
            conn.close()

    def charger_magasins(self):
        """Charge la liste des magasins depuis la base de données"""
        conn = self.connect_db()
        if not conn:
            return
    
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT idmag, designationmag 
                FROM tb_magasin 
                WHERE deleted = 0
                ORDER BY designationmag
            """)
            self.magasins = cursor.fetchall()
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger les magasins : {str(e)}")
        finally:
            cursor.close()
            conn.close()

    def ouvrir_inventaire_double_clic(self, event):
        """Ouvre la fenêtre d'inventaire lors d'un double-clic sur une ligne"""
        selection = self.tree.selection()
        if not selection:
            return
    
        item = self.tree.item(selection[0])
        code_article = item['values'][0]
        
        # Assurer que le code a le bon format avec zéros de gauche (10 chiffres)
        code_article = str(code_article).zfill(10)
    
        # Récupérer idarticle et idunite depuis la base
        conn = self.connect_db()
        if not conn:
            return
    
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.idarticle, u.idunite, a.designation
                FROM tb_unite u
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                WHERE u.codearticle = %s
                LIMIT 1
            """, (str(code_article),))
        
            result = cursor.fetchone()
            if not result:
                messagebox.showwarning("Erreur", f"Article {code_article} introuvable")
                return
        
            idarticle, idunite, designation = result
        
            # Créer le dictionnaire article_data attendu par PageInventaire
            article_data = {
                'code': code_article,
                'designation': designation
            }
        
            # PageInventaire hérite de CTkToplevel, donc pas besoin de créer une fenêtre séparée
            page_inv = PageInventaire(
                self, 
                article_data, 
                self.iduser
            )
        
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'ouverture : {str(e)}")
        finally:
            cursor.close()
            conn.close()

    def clignoter_bouton(self):
        """Fait clignoter le bouton de péremption"""
        if not self.clignotement_actif:
            self.clignotement_actif = True
        
        def toggle_color():
            if self.clignotement_actif:
                couleur_actuelle = self.btn_peremption.cget("fg_color")
                nouvelle_couleur = "#ffffff" if couleur_actuelle == self.couleur_alerte else self.couleur_alerte
                self.btn_peremption.configure(fg_color=nouvelle_couleur)
                self.after(500, toggle_color)
        
        toggle_color()

    def filtrer_stocks(self):
        """Filtre les données selon le critère de recherche (comme page_ArticleListe)"""
        # Effacer le Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Récupérer la valeur de recherche
        search_term = self.entry_recherche.get().lower().strip()
        
        # Si vide, afficher tout
        if not search_term:
            self.recharger_treeview()
            return
        
        # Filtrer
        filtered_data = []
        for valeurs, total in self.all_data:
            # Concaténation des colonnes à rechercher (Code, Désignation, Unité)
            # Les indices correspondent : [0]Code, [1]Désignation, [2]Unité
            searchable_text = f"{valeurs[0]} {valeurs[1]} {valeurs[2]}".lower()
            
            if search_term in searchable_text:
                filtered_data.append((valeurs, total))
        
        # Insérer les résultats filtrés
        if filtered_data:
            for idx, (valeurs, total) in enumerate(filtered_data):
                # TAG POUR ALERTE STOCK BAS
                zebra_tag = "even" if idx % 2 == 0 else "odd"
                if abs(float(total)) < 1e-9:
                    zero_tag = "stock_zero_even" if zebra_tag == "even" else "stock_zero_odd"
                    self.tree.insert("", "end", values=valeurs, tags=(zero_tag,))
                else:
                    self.tree.insert("", "end", values=valeurs, tags=(zebra_tag,))
            self.label_total_articles.configure(text=f"Total articles: {len(filtered_data)}")
        else:
            # Créer une ligne vide avec le message
            empty_values = ["", "Aucun résultat trouvé", ""] + [""] * (len(self.colonnes_dynamiques) - 3)
            self.tree.insert('', 'end', values=empty_values)
            self.label_total_articles.configure(text="Total articles: 0")
    
    def reinitialiser_filtre(self):
        """Réinitialise le filtre et recharge toutes les données"""
        self.entry_recherche.delete(0, 'end')
        self.recharger_treeview()
    
    def recharger_treeview(self):
        """Recharge le Treeview avec toutes les données stockées"""
        # Effacer le Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Réinsérer toutes les données
        if self.all_data:
            for idx, (valeurs, total) in enumerate(self.all_data):
                # TAG POUR ALERTE STOCK BAS
                zebra_tag = "even" if idx % 2 == 0 else "odd"
                if abs(float(total)) < 1e-9:
                    zero_tag = "stock_zero_even" if zebra_tag == "even" else "stock_zero_odd"
                    self.tree.insert("", "end", values=valeurs, tags=(zero_tag,))
                else:
                    self.tree.insert("", "end", values=valeurs, tags=(zebra_tag,))
            self.label_total_articles.configure(text=f"Total articles: {len(self.all_data)}")
        else:
            empty_values = ["", "Aucun article trouvé", ""] + [""] * (len(self.colonnes_dynamiques) - 3)
            self.tree.insert('', 'end', values=empty_values)
            self.label_total_articles.configure(text="Total articles: 0")
    
    def exporter_stocks(self):
        """Exporte les stocks vers un fichier CSV"""
        try:
            from tkinter import filedialog
            import csv
            
            # Demander où enregistrer
            fichier = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile=f"stocks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            
            if not fichier:
                return
            
            # Écrire le CSV
            with open(fichier, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')
                
                # En-têtes
                writer.writerow(self.colonnes_dynamiques)
                
                # Données
                for item in self.tree.get_children():
                    values = self.tree.item(item)['values']
                    writer.writerow(values)
            
            messagebox.showinfo("Succès", f"Stocks exportés vers:\n{fichier}")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'export: {str(e)}")
    
    def mettre_a_jour_tb_stock(self):
        """
        Synchronise les calculs dynamiques avec la table physique tb_stock 
        en utilisant codearticle comme identifiant.
    
        CORRECTION : Utilise la même méthode de calcul que l'affichage dans page_stock
        qui inclut les sorties et les avoirs.
        """
        conn = self.connect_db()
        if not conn:
            return

        try:
            cursor = conn.cursor()
        
            print("Début de la synchronisation tb_stock...")
    
            # 1. Récupérer tous les articles avec leur code et leur unité
            # IMPORTANT : On récupère TOUTES les unités de chaque article
            cursor.execute("""
                SELECT a.idarticle, u.idunite, u.codearticle, u.designationunite, a.designation
                FROM tb_article a
                INNER JOIN tb_unite u ON a.idarticle = u.idarticle
                WHERE a.deleted = 0
                ORDER BY a.designation ASC, u.codearticle ASC
            """)
            articles = cursor.fetchall()
        
            print(f"Articles trouvés : {len(articles)}")
    
            compteur_maj = 0
            compteur_ins = 0
            compteur_total = 0
    
            # 2. Pour chaque article et chaque magasin, calculer et synchroniser
            for idarticle, idunite, code_art, unite_desig, art_desig in articles:
                for idmag, nom_mag in self.magasins:
                    compteur_total += 1
                
                    # Calcul basé sur TOUS les mouvements (réceptions, ventes, sorties, transferts, inventaires, avoirs)
                    # Cette fonction inclut déjà les sorties et les avoirs
                    stock_calcule = self.calculer_stock_article(idarticle, idunite, idmag)
                
                    # Debug pour quelques articles
                    if compteur_total <= 5 or code_art == '0070026701':
                        print(f"  Article: {art_desig} ({unite_desig})")
                        print(f"    Code: {code_art}, Magasin: {nom_mag}")
                        print(f"    Stock calculé: {stock_calcule}")
            
                    # Vérifier si l'enregistrement existe pour ce codearticle dans ce magasin
                    cursor.execute("""
                        SELECT qtstock FROM tb_stock 
                        WHERE codearticle = %s AND idmag = %s
                    """, (str(code_art), idmag))
            
                    resultat = cursor.fetchone()
            
                    if resultat:
                        # UPDATE : Mise à jour du stock physique
                        ancien_stock = resultat[0]
                    
                        # Ne mettre à jour que si le stock a changé
                        if abs(float(ancien_stock or 0) - float(stock_calcule)) > 0.001:
                            cursor.execute("""
                                UPDATE tb_stock 
                                SET qtstock = %s
                                WHERE codearticle = %s AND idmag = %s
                            """, (stock_calcule, str(code_art), idmag))
                            compteur_maj += 1
                        
                            if code_art == '0070026701':
                                print(f"    ✓ Mise à jour : {ancien_stock} → {stock_calcule}")
                    else:
                        # INSERT : Création de la ligne si elle n'existe pas
                        cursor.execute("""
                            INSERT INTO tb_stock (codearticle, idmag, qtstock, qtalert, deleted)
                            VALUES (%s, %s, %s, 0, 0)
                        """, (str(code_art), idmag, stock_calcule))
                        compteur_ins += 1
                    
                        if code_art == '0070026701':
                            print(f"    ✓ Création : stock = {stock_calcule}")
                
                    # Commit tous les 100 enregistrements pour éviter de bloquer la DB
                    if (compteur_maj + compteur_ins) % 100 == 0:
                        conn.commit()
                        print(f"  Progression : {compteur_maj} maj, {compteur_ins} créations sur {compteur_total} traitements")
    
            # Commit final
            conn.commit()
        
            message = f"✅ Synchronisation terminée :\n"
            message += f"  • {compteur_maj} mises à jour\n"
            message += f"  • {compteur_ins} créations\n"
            message += f"  • {compteur_total} lignes traitées"
        
            print(message)
            messagebox.showinfo("Synchronisation réussie", message)
    
        except Exception as e:
            conn.rollback()
            error_msg = f"Erreur lors de la synchronisation :\n{str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            messagebox.showerror("Erreur de synchronisation", error_msg)
        finally:
            cursor.close()
            conn.close()

    def ouvrir_fenetre_peremption(self):
        """Ouvre une fenêtre Toplevel affichant les articles périmés"""
        # Création de la fenêtre surgissante
        self.fenetre_peremp = ctk.CTkToplevel(self)
        self.fenetre_peremp.title("Suivi des Péremptions")
        self.fenetre_peremp.geometry("1100x700")
        
        # S'assurer que la fenêtre est au-dessus
        self.fenetre_peremp.attributes('-topmost', True)
        self.fenetre_peremp.focus_set()
        
        # Instance de la page de péremption
        # On passe self.iduser pour maintenir la session
        self.page_peremp = PageGestionPeremption(self.fenetre_peremp, iduser=self.iduser)
        self.page_peremp.pack(fill="both", expand=True, padx=10, pady=10)

    def mettre_a_jour_badge_peremption(self):
        """Analyse les dates et ajuste la couleur et le texte du bouton"""
        conn = self.connect_db()
        if not conn: return

        try:
            cursor = conn.cursor()
            query = "SELECT l.idarticle, l.idunite, l.dateperemption FROM tb_livraisonfrs l WHERE l.dateperemption IS NOT NULL"
            cursor.execute(query)
            lignes = cursor.fetchall()
        
            aujourdhui = datetime.now().date()
            un_mois = aujourdhui + timedelta(days=30)
        
            nb_perimes = 0
            nb_urgents = 0

            for id_art, id_uni, d_peremp in lignes:
                stock = self.calculer_stock_article(id_art, id_uni)
                if stock > 0:
                    if d_peremp <= aujourdhui:
                        nb_perimes += 1
                    elif d_peremp <= un_mois:
                        nb_urgents += 1

            total_alertes = nb_perimes + nb_urgents
        
            if nb_perimes > 0:
                # État Critique : Rouge clignotant
                self.btn_peremption.configure(text=f"🚨 PÉRIMÉS ({nb_perimes})")
                self.couleur_alerte = "#d32f2f"
                if not self.clignotement_actif:
                    self.clignoter_bouton()
            elif nb_urgents > 0:
                # État Alerte : Orange fixe
                self.clignotement_actif = False
                self.btn_peremption.configure(text=f"⚠️ Alerte ({nb_urgents})", fg_color="#fb8c00", hover_color="#ef6c00")
            else:
                # État Normal : Gris ou Bleu standard
                self.clignotement_actif = False
                self.btn_peremption.configure(text="🛡️ Articles Périmés", fg_color="#2c3e50")

        except Exception as e:
            print(f"Erreur badge: {e}")
        finally:
            cursor.close()
            conn.close()

        
if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("850x700")
    
    iduser = 1
    
    page = PageStock(app, iduser=iduser)
    page.pack(fill="both", expand=True)
    
    app.mainloop()
