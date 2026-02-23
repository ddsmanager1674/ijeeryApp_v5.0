import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import json
from datetime import datetime
from reportlab.lib.pagesizes import A5
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import os
from resource_utils import get_config_path, safe_file_read


class PageTransfert(ctk.CTkFrame):
    def __init__(self, parent, user_id):
        super().__init__(parent)
        self.user_id = user_id
        self.articles_transfert = []
        
        self.setup_ui()
        self.charger_magasins()
        
    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        titre = ctk.CTkLabel(
            self,
            text="TRANSFERT DE STOCK",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
        )
        titre.grid(row=0, column=0, pady=(16, 8))

        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)

        # Bloc entête transfert
        header_frame = ctk.CTkFrame(main_frame)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        for i in range(4):
            header_frame.grid_columnconfigure(i, weight=1)

        ctk.CTkLabel(header_frame, text="Référence:", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", padx=6, pady=(6, 2))
        self.entry_ref = ctk.CTkEntry(header_frame, state="readonly")
        self.entry_ref.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 6))

        ctk.CTkLabel(header_frame, text="Date:", font=("Segoe UI", 11, "bold")).grid(row=0, column=1, sticky="w", padx=6, pady=(6, 2))
        self.entry_date = ctk.CTkEntry(header_frame)
        self.entry_date.grid(row=1, column=1, sticky="ew", padx=6, pady=(0, 6))
        self.entry_date.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        ctk.CTkLabel(header_frame, text="Magasin sortie:", font=("Segoe UI", 11, "bold")).grid(row=0, column=2, sticky="w", padx=6, pady=(6, 2))
        self.combo_mag_sortie = ctk.CTkComboBox(header_frame, values=[""])
        self.combo_mag_sortie.grid(row=1, column=2, sticky="ew", padx=6, pady=(0, 6))

        ctk.CTkLabel(header_frame, text="Magasin entrée:", font=("Segoe UI", 11, "bold")).grid(row=0, column=3, sticky="w", padx=6, pady=(6, 2))
        self.combo_mag_entree = ctk.CTkComboBox(header_frame, values=[""])
        self.combo_mag_entree.grid(row=1, column=3, sticky="ew", padx=6, pady=(0, 6))

        ctk.CTkLabel(header_frame, text="Description:", font=("Segoe UI", 11, "bold")).grid(row=2, column=0, sticky="w", padx=6, pady=(2, 2))
        self.entry_description = ctk.CTkEntry(header_frame)
        self.entry_description.grid(row=3, column=0, columnspan=4, sticky="ew", padx=6, pady=(0, 8))
        self.generer_reference()

        # Bloc ajout article
        article_frame = ctk.CTkFrame(main_frame)
        article_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))
        for i in range(6):
            article_frame.grid_columnconfigure(i, weight=1 if i in (1, 2) else 0)

        ctk.CTkLabel(article_frame, text="Article:", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", padx=6, pady=(6, 2))
        self.entry_code_article = ctk.CTkEntry(article_frame, width=110, state="readonly")
        self.entry_code_article.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 6))

        self.entry_nom_article = ctk.CTkEntry(article_frame, state="readonly")
        self.entry_nom_article.grid(row=1, column=1, sticky="ew", padx=6, pady=(0, 6))

        btn_recherche = ctk.CTkButton(article_frame, text="🔍 Rechercher", width=120, command=self.rechercher_article)
        btn_recherche.grid(row=1, column=2, sticky="ew", padx=6, pady=(0, 6))

        ctk.CTkLabel(article_frame, text="Unité:", font=("Segoe UI", 11, "bold")).grid(row=0, column=3, sticky="w", padx=6, pady=(6, 2))
        self.entry_unite = ctk.CTkEntry(article_frame, width=130, state="readonly")
        self.entry_unite.grid(row=1, column=3, sticky="ew", padx=6, pady=(0, 6))

        ctk.CTkLabel(article_frame, text="Quantité:", font=("Segoe UI", 11, "bold")).grid(row=0, column=4, sticky="w", padx=6, pady=(6, 2))
        self.entry_quantite = ctk.CTkEntry(article_frame, width=120)
        self.entry_quantite.grid(row=1, column=4, sticky="ew", padx=6, pady=(0, 6))

        self.btn_ajouter = ctk.CTkButton(article_frame, text="Ajouter", command=self.ajouter_article, height=32, fg_color="#2e7d32", hover_color="#1b5e20")
        self.btn_ajouter.grid(row=1, column=5, sticky="ew", padx=6, pady=(0, 6))

        # Tableau des lignes
        table_frame = ctk.CTkFrame(main_frame)
        table_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 8))
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.grid(row=0, column=1, sticky="ns")

        columns = ("Code", "Article", "Unité", "Quantité")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", yscrollcommand=scrollbar.set, height=12)
        scrollbar.config(command=self.tree.yview)

        self.tree.heading("Code", text="Code Article")
        self.tree.heading("Article", text="Nom Article")
        self.tree.heading("Unité", text="Unité")
        self.tree.heading("Quantité", text="Quantité")
        self.tree.column("Code", width=130, anchor="w")
        self.tree.column("Article", width=380, anchor="w")
        self.tree.column("Unité", width=130, anchor="w")
        self.tree.column("Quantité", width=120, anchor="e")
        self.tree.grid(row=0, column=0, sticky="nsew")

        self.btn_supprimer = ctk.CTkButton(table_frame, text="Supprimer ligne", command=self.supprimer_ligne, fg_color="#e74c3c", hover_color="#c0392b", height=30)
        self.btn_supprimer.grid(row=1, column=0, sticky="w", padx=4, pady=(6, 2))

        # Barre d'actions globale
        action_frame = ctk.CTkFrame(main_frame)
        action_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        action_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.btn_enregistrer = ctk.CTkButton(
            action_frame,
            text="💾 Enregistrer",
            command=self.enregistrer_transfert,
            height=36,
            fg_color="#2e7d32",
            hover_color="#1b5e20",
        )
        self.btn_enregistrer.grid(row=0, column=0, sticky="ew", padx=4, pady=6)

        self.btn_charger = ctk.CTkButton(
            action_frame,
            text="📂 Charger Transfert",
            command=self.ouvrir_fenetre_chargement,
            height=36,
            fg_color="#f39c12",
            hover_color="#d68910",
        )
        self.btn_charger.grid(row=0, column=1, sticky="ew", padx=4, pady=6)

        self.btn_nouveau = ctk.CTkButton(
            action_frame,
            text="🆕 Nouveau",
            command=self.nouveau_transfert,
            height=36,
        )
        self.btn_nouveau.grid(row=0, column=2, sticky="ew", padx=4, pady=6)
        
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
    
    def get_connection(self):
        return self.connect_db()
    
    def generer_reference(self):
        try:
            conn = self.get_connection()
            if not conn:
                return
            
            cur = conn.cursor()
            
            annee = datetime.now().year
            cur.execute("""
                SELECT reftransfert FROM tb_transfert 
                WHERE reftransfert LIKE %s 
                ORDER BY reftransfert DESC LIMIT 1
            """, (f"{annee}-TRA-%",))
            
            result = cur.fetchone()
            if result:
                # Assurez-vous que la référence est bien au format "YYYY-TRA-NNNNN"
                parts = result[0].split('-')
                if len(parts) == 3 and parts[1] == 'TRA':
                    try:
                        dernier_num = int(parts[2])
                        nouveau_num = dernier_num + 1
                    except ValueError:
                        # Si le numéro n'est pas un entier valide
                        nouveau_num = 1
                else:
                    nouveau_num = 1
            else:
                nouveau_num = 1
                
            reference = f"{annee}-TRA-{nouveau_num:05d}"
            self.entry_ref.configure(state="normal")
            self.entry_ref.delete(0, "end")
            self.entry_ref.insert(0, reference)
            self.entry_ref.configure(state="readonly")
            
            cur.close()
            conn.close()
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur génération référence: {str(e)}")
    
    def charger_magasins(self):
        try:
            conn = self.get_connection()
            if not conn:
                return
            
            cur = conn.cursor()
            
            cur.execute("SELECT idmag, designationmag FROM tb_magasin WHERE deleted = 0")
            magasins = cur.fetchall()
            
            self.magasins_data = {mag[1]: mag[0] for mag in magasins}
            mag_list = list(self.magasins_data.keys())
            
            self.combo_mag_sortie.configure(values=mag_list)
            self.combo_mag_entree.configure(values=mag_list)
            
            if mag_list:
                idmag_defaut = None
                cur.execute("SELECT idmag FROM tb_users WHERE iduser = %s LIMIT 1", (self.user_id,))
                row_user = cur.fetchone()
                if row_user:
                    idmag_defaut = row_user[0]

                nom_magasin_defaut = next((nom for id_, nom in magasins if id_ == idmag_defaut), None)
                if nom_magasin_defaut:
                    self.combo_mag_sortie.set(nom_magasin_defaut)
                    self.combo_mag_entree.set(nom_magasin_defaut)
                else:
                    self.combo_mag_sortie.set(mag_list[0])
                    self.combo_mag_entree.set(mag_list[0])
            
            cur.close()
            conn.close()
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur chargement magasins: {str(e)}")
    
    def rechercher_article(self):
        """Ouvre une fenêtre pour rechercher et sélectionner un article.
           Utilise la même requête consolidée (réservoir commun via qtunite)
           que page_venteParMsin pour calculer le stock correctement."""
        fenetre_recherche = ctk.CTkToplevel(self)
        fenetre_recherche.title("Rechercher un article pour le transfert")
        fenetre_recherche.geometry("1000x600")
        fenetre_recherche.grab_set()

        main_frame = ctk.CTkFrame(fenetre_recherche)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        titre = ctk.CTkLabel(main_frame, text="Sélectionner un article", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"))
        titre.pack(pady=(0, 10))

        # Zone de recherche
        search_frame = ctk.CTkFrame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(search_frame, text="🔍 Rechercher:").pack(side="left", padx=5)
        entry_search = ctk.CTkEntry(search_frame, placeholder_text="Code ou désignation...", width=300)
        entry_search.pack(side="left", padx=5, fill="x", expand=True)

        # Treeview
        tree_frame = ctk.CTkFrame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))

        colonnes = ("ID_Article", "ID_Unite", "Code", "Désignation", "Unité", "Stock", "Prix U.")
        tree = ttk.Treeview(tree_frame, columns=colonnes, show='headings', height=15)
        tree.tag_configure("even", background="#FFFFFF", foreground="#000000")
        tree.tag_configure("odd", background="#E6EFF8", foreground="#000000")

        style = ttk.Style()
        style.configure("Treeview", rowheight=22, font=('Segoe UI', 8), background="#FFFFFF", foreground="#000000", fieldbackground="#FFFFFF", borderwidth=0)
        style.configure("Treeview.Heading", background="#E8E8E8", foreground="#000000", font=('Segoe UI', 8, 'bold'))
        style.configure("Treeview.Heading", font=('Segoe UI', 8, 'bold'), background="#E8E8E8", foreground="#000000")

        tree.heading("ID_Article", text="ID_Article")
        tree.heading("ID_Unite", text="ID_Unite")
        tree.heading("Code", text="Code")
        tree.heading("Désignation", text="Désignation")
        tree.heading("Unité", text="Unité")
        nom_magasin_courant = (self.combo_mag_sortie.get() or "").strip()
        tree.heading("Stock", text=f"Magasin {nom_magasin_courant}" if nom_magasin_courant else "Magasin")
        tree.heading("Prix U.", text="Prix U.")

        tree.column("ID_Article", width=0, stretch=False)
        tree.column("ID_Unite", width=0, stretch=False)
        tree.column("Code", width=120, anchor='w')
        tree.column("Désignation", width=300, anchor='w')
        tree.column("Unité", width=80, anchor='w')
        tree.column("Stock", width=100, anchor='e')
        tree.column("Prix U.", width=100, anchor='e')

        scrollbar = ttk.Scrollbar(tree_frame, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def formater_nombre(nombre):
            try:
                n = float(nombre)
                return "{:,.2f}".format(n).replace(',', '_TEMP_').replace('.', ',').replace('_TEMP_', '.')
            except Exception:
                return "0,00"

        def parser_nombre(texte):
            try:
                return float(str(texte).replace('.', '').replace(',', '.'))
            except Exception:
                return 0.0

        # Fonction de chargement avec la requête consolidée (réservoir commun)
        def charger_articles(filtre=""):
            for item in tree.get_children():
                tree.delete(item)

            conn = self.get_connection()
            if not conn:
                return
            try:
                cur = conn.cursor()
                filtre_like = f"%{filtre}%"

                # Même logique réservoir que page_stock :
                # tous les mouvements sont convertis en "unité de base" via qtunite,
                # puis le solde du magasin actif est divisé par le qtunite de chaque ligne.
                query = """
                WITH mouvements_bruts AS (
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

                    SELECT
                        sd.idarticle,
                        sd.idmag,
                        COALESCE(u.qtunite, 1) as qtunite_source,
                        sd.qtsortie as quantite,
                        'sortie' as type_mouvement
                    FROM tb_sortiedetail sd
                    INNER JOIN tb_unite u ON sd.idarticle = u.idarticle AND sd.idunite = u.idunite

                    UNION ALL

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

                    SELECT
                        ci.idarticle,
                        ci.idmag,
                        COALESCE(u.qtunite, 1) as qtunite_source,
                        ci.qtconsomme as quantite,
                        'consommation_interne' as type_mouvement
                    FROM tb_consommationinterne_details ci
                    INNER JOIN tb_unite u ON ci.idarticle = u.idarticle AND ci.idunite = u.idunite

                    UNION ALL

                    SELECT
                        dce.idarticle,
                        dce.idmagasin,
                        COALESCE(u.qtunite, 1) as qtunite_source,
                        dce.quantite_entree as quantite,
                        'echange_entree' as type_mouvement
                    FROM tb_detailchange_entree dce
                    INNER JOIN tb_unite u ON dce.idarticle = u.idarticle AND dce.idunite = u.idunite

                    UNION ALL

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
                                WHEN 'reception'           THEN  quantite * qtunite_source
                                WHEN 'transfert_in'        THEN  quantite * qtunite_source
                                WHEN 'inventaire'          THEN  quantite * qtunite_source
                                WHEN 'avoir'               THEN  quantite * qtunite_source
                                WHEN 'echange_entree'      THEN  quantite * qtunite_source
                                WHEN 'vente'               THEN -quantite * qtunite_source
                                WHEN 'sortie'              THEN -quantite * qtunite_source
                                WHEN 'transfert_out'       THEN -quantite * qtunite_source
                                WHEN 'consommation_interne' THEN -quantite * qtunite_source
                                WHEN 'echange_sortie'      THEN -quantite * qtunite_source
                                ELSE 0
                            END
                        ) as solde
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
                ),
                dernier_prix AS (
                    SELECT
                        idarticle,
                        idunite,
                        prix,
                        ROW_NUMBER() OVER (PARTITION BY idarticle, idunite ORDER BY id DESC) AS rn
                    FROM tb_prix
                )

                SELECT
                    u.idarticle,
                    u.idunite,
                    u.codearticle,
                    a.designation,
                    uc.designationunite,
                    GREATEST(COALESCE(sb.solde, 0) / NULLIF(COALESCE(uc.coeff_hierarchique, 1), 0), 0) as stock_total,
                    COALESCE(p.prix, 0) as prix_unitaire
                FROM tb_article a
                INNER JOIN tb_unite u ON a.idarticle = u.idarticle
                LEFT JOIN unite_coeff uc ON uc.idarticle = u.idarticle AND uc.idunite = u.idunite
                LEFT JOIN solde_base_par_mag sb ON sb.idarticle = u.idarticle AND sb.idmag = %s
                LEFT JOIN dernier_prix p ON a.idarticle = p.idarticle AND u.idunite = p.idunite AND p.rn = 1
                WHERE a.deleted = 0
                  AND (u.codearticle ILIKE %s OR a.designation ILIKE %s)
                ORDER BY a.designation ASC, u.codearticle ASC, u.idunite ASC
                """
                designationmag = (self.combo_mag_sortie.get() or "").strip()
                idmag_actif = self.magasins_data.get(designationmag)
                tree.heading("Stock", text=f"Magasin {designationmag}" if designationmag else "Magasin")
                if idmag_actif is None:
                    return

                cur.execute(query, (idmag_actif, filtre_like, filtre_like))
                articles = cur.fetchall()

                for idx, row in enumerate(articles):
                    zebra_tag = "even" if idx % 2 == 0 else "odd"
                    tree.insert('', 'end', values=(
                        row[0],          # idarticle
                        row[1],          # idunite
                        row[2] or "",    # codearticle
                        row[3] or "",    # designation
                        row[4] or "",    # designationunite
                        formater_nombre(row[5]),  # stock_total
                        formater_nombre(row[6])   # prix_unitaire
                    ), tags=(zebra_tag,))

            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur chargement articles: {str(e)}")
            finally:
                if 'cur' in locals() and cur:
                    cur.close()
                if conn:
                    conn.close()

        def rechercher(*args):
            charger_articles(entry_search.get())

        entry_search.bind('<KeyRelease>', rechercher)

        def valider_selection():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Attention", "Veuillez sélectionner un article")
                return

            values = tree.item(selection[0]).get('values', [])
            if len(values) < 7:
                messagebox.showerror("Erreur", "Données de l'article incomplètes dans le tableau.")
                return

            # Stocker l'article sélectionné avec les mêmes clés utilisées dans ajouter_article
            self.article_selectionne = {
                'id': values[0],           # idarticle
                'idunite': values[1],      # idunite
                'code': values[2] or "N/A",
                'nom': values[3] or "N/A",
                'unite': values[4] or "N/A",
                'stock_disponible': parser_nombre(values[5]),
                'prix_unitaire': parser_nombre(values[6])
            }

            self.entry_code_article.configure(state="normal")
            self.entry_code_article.delete(0, "end")
            self.entry_code_article.insert(0, self.article_selectionne['code'])
            self.entry_code_article.configure(state="readonly")

            self.entry_nom_article.configure(state="normal")
            self.entry_nom_article.delete(0, "end")
            self.entry_nom_article.insert(0, self.article_selectionne['nom'])
            self.entry_nom_article.configure(state="readonly")

            self.entry_unite.configure(state="normal")
            self.entry_unite.delete(0, "end")
            self.entry_unite.insert(0, self.article_selectionne['unite'])
            self.entry_unite.configure(state="readonly")

            fenetre_recherche.destroy()

        tree.bind('<Double-Button-1>', lambda e: valider_selection())

        # Boutons
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x")
        btn_annuler = ctk.CTkButton(btn_frame, text="❌ Annuler", command=fenetre_recherche.destroy, fg_color="#d32f2f", hover_color="#b71c1c")
        btn_annuler.pack(side="left", padx=5, pady=5)
        btn_valider = ctk.CTkButton(btn_frame, text="✅ Valider", command=valider_selection, fg_color="#2e7d32", hover_color="#1b5e20")
        btn_valider.pack(side="right", padx=5, pady=5)

        # Chargement initial
        charger_articles()
        
    def calculer_stock_article(self, idarticle, idunite_cible, idmag=None):
        """
        ✅ CALCUL CONSOLIDÉ (identique à page_venteParMsin / page_stock.py) :
        Relie tous les mouvements de toutes les unités (PIECE, CARTON, etc.)
        d'un même idarticle via le coefficient 'qtunite' de tb_unite.

        LOGIQUE :
          1) On récupère toutes les unités sœurs (même idarticle).
          2) Pour chaque unité sœur, on somme ses mouvements puis on les convertit
             en "unité de base" en multipliant par son qtunite.
          3) Le solde total (réservoir commun) est divisé par le qtunite de
             l'unité cible pour obtenir le stock affiché.

        Exemple : vente de 20 PIECES → réservoir diminue de 20×1 = 20.
                  CARTON (qtunite=20) → stock = réservoir / 20  →  -1 CARTON.
        """
        conn = self.get_connection()
        if not conn:
            return 0

        try:
            cursor = conn.cursor()

            # 1. Récupérer TOUTES les unités liées à cet idarticle
            cursor.execute("""
                SELECT idunite, codearticle, COALESCE(qtunite, 1)
                FROM tb_unite
                WHERE idarticle = %s
            """, (idarticle,))
            unites_liees = cursor.fetchall()

            # 2. Identifier le qtunite de l'unité cible
            qtunite_affichage = 1
            for idu, code, qt_u in unites_liees:
                if idu == idunite_cible:
                    qtunite_affichage = qt_u if qt_u > 0 else 1
                    break

            total_stock_global_base = 0  # Réservoir commun en unité de base

            # 3. Sommer les mouvements de chaque unité sœur
            for idu_boucle, code_boucle, qtunite_boucle in unites_liees:

                # --- Réceptions ---
                q_rec = "SELECT COALESCE(SUM(qtlivrefrs), 0) FROM tb_livraisonfrs WHERE idarticle = %s AND idunite = %s AND deleted = 0"
                p_rec = [idarticle, idu_boucle]
                if idmag:
                    q_rec += " AND idmag = %s"
                    p_rec.append(idmag)
                cursor.execute(q_rec, p_rec)
                receptions = cursor.fetchone()[0] or 0

                # --- Ventes ---
                q_ven = "SELECT COALESCE(SUM(qtvente), 0) FROM tb_ventedetail WHERE idarticle = %s AND idunite = %s AND deleted = 0"
                p_ven = [idarticle, idu_boucle]
                if idmag:
                    q_ven += " AND idmag = %s"
                    p_ven.append(idmag)
                cursor.execute(q_ven, p_ven)
                ventes = cursor.fetchone()[0] or 0

                # --- Transferts entrants ---
                q_tin = "SELECT COALESCE(SUM(qttransfert), 0) FROM tb_transfertdetail WHERE idarticle = %s AND idunite = %s AND deleted = 0"
                p_tin = [idarticle, idu_boucle]
                if idmag:
                    q_tin += " AND idmagentree = %s"
                    p_tin.append(idmag)
                cursor.execute(q_tin, p_tin)
                t_in = cursor.fetchone()[0] or 0

                # --- Transferts sortants ---
                q_tout = "SELECT COALESCE(SUM(qttransfert), 0) FROM tb_transfertdetail WHERE idarticle = %s AND idunite = %s AND deleted = 0"
                p_tout = [idarticle, idu_boucle]
                if idmag:
                    q_tout += " AND idmagsortie = %s"
                    p_tout.append(idmag)
                cursor.execute(q_tout, p_tout)
                t_out = cursor.fetchone()[0] or 0

                # --- Inventaires (via codearticle) ---
                q_inv = "SELECT COALESCE(SUM(qtinventaire), 0) FROM tb_inventaire WHERE codearticle = %s"
                p_inv = [code_boucle]
                if idmag:
                    q_inv += " AND idmag = %s"
                    p_inv.append(idmag)
                cursor.execute(q_inv, p_inv)
                inv = cursor.fetchone()[0] or 0

                # --- Avoirs (AUGMENTENT le stock - annulation de vente) ---
                q_avoir = """
                    SELECT COALESCE(SUM(ad.qtavoir), 0) 
                    FROM tb_avoirdetail ad
                    INNER JOIN tb_avoir a ON ad.idavoir = a.id
                    WHERE ad.idarticle = %s AND ad.idunite = %s 
                    AND a.deleted = 0 AND ad.deleted = 0
                """
                p_avoir = [idarticle, idu_boucle]
                if idmag:
                    q_avoir += " AND ad.idmag = %s"
                    p_avoir.append(idmag)
                cursor.execute(q_avoir, p_avoir)
                avoirs = cursor.fetchone()[0] or 0

                # --- Consommation interne (RÉDUIT le stock) ---
                q_consomm = "SELECT COALESCE(SUM(qtconsomme), 0) FROM tb_consommationinterne_details WHERE idarticle = %s AND idunite = %s"
                p_consomm = [idarticle, idu_boucle]
                if idmag:
                    q_consomm += " AND idmag = %s"
                    p_consomm.append(idmag)
                cursor.execute(q_consomm, p_consomm)
                consomm = cursor.fetchone()[0] or 0

                # --- Échange entrant (AUGMENTE le stock) ---
                q_echange_in = "SELECT COALESCE(SUM(quantite_entree), 0) FROM tb_detailchange_entree WHERE idarticle = %s AND idunite = %s"
                p_echange_in = [idarticle, idu_boucle]
                if idmag:
                    q_echange_in += " AND idmagasin = %s"
                    p_echange_in.append(idmag)
                cursor.execute(q_echange_in, p_echange_in)
                echange_in = cursor.fetchone()[0] or 0

                # --- Échange sortant (RÉDUIT le stock) ---
                q_echange_out = "SELECT COALESCE(SUM(quantite_sortie), 0) FROM tb_detailchange_sortie WHERE idarticle = %s AND idunite = %s"
                p_echange_out = [idarticle, idu_boucle]
                if idmag:
                    q_echange_out += " AND idmagasin = %s"
                    p_echange_out.append(idmag)
                cursor.execute(q_echange_out, p_echange_out)
                echange_out = cursor.fetchone()[0] or 0

                # Conversion en unité de base puis accumulation dans le réservoir
                # Entrées: receptions, transferts entrants, inventaires, avoirs (retour), échanges entrants
                # Sorties: ventes, sorties, transferts sortants, consommation interne, échanges sortants
                solde_unite = (receptions + t_in + inv + avoirs + echange_in - ventes - t_out - consomm - echange_out)
                total_stock_global_base += (solde_unite * qtunite_boucle)

            # 4. Conversion finale : réservoir / qtunite de l'unité cible
            stock_final = total_stock_global_base / qtunite_affichage
            return max(0, stock_final)

        except Exception as e:
            print(f"Erreur calcul stock consolidé : {e}")
            return 0
        finally:
            cursor.close()
            conn.close()
    
    def ajouter_article(self):
        # 1. Vérifications de base (Article et Unité)
        if not hasattr(self, 'article_selectionne'):
            messagebox.showwarning("Attention", "Veuillez sélectionner un article")
            return
            
        if not self.article_selectionne.get('idunite'):
             messagebox.showwarning("Attention", "Cet article n'a pas d'unité par défaut.")
             return
        
        # 2. Vérification de la saisie quantité
        try:
            quantite_saisie = float(self.entry_quantite.get())
            if quantite_saisie <= 0:
                messagebox.showwarning("Attention", "La quantité doit être supérieure à 0")
                return
        except ValueError:
            messagebox.showwarning("Attention", "Quantité invalide")
            return

        # 3. VERIFICATION DU STOCK (BLOCAGE)
        mag_sortie_nom = self.combo_mag_sortie.get()
        if not mag_sortie_nom:
            messagebox.showwarning("Attention", "Sélectionnez le magasin de sortie")
            return

        id_mag_sortie = self.magasins_data[mag_sortie_nom]
        id_article = self.article_selectionne['id']
        id_unite = self.article_selectionne['idunite']
        
        stock_actuel = self.calculer_stock_article(id_article, id_unite, id_mag_sortie)
        
        if quantite_saisie > stock_actuel:
            messagebox.showerror("Stock Insuffisant", 
                f"Transfert impossible.\n\n"
                f"Article : {self.article_selectionne['nom']}\n"
                f"Stock disponible : {stock_actuel}\n"
                f"Quantité demandée : {quantite_saisie}")
            return # Sortie de la fonction sans ajouter au Treeview

        # 4. Ajout au Treeview et à la liste si stock suffisant
        self.tree.insert("", "end", values=(
            self.article_selectionne['code'],
            self.article_selectionne['nom'],
            self.article_selectionne['unite'],
            quantite_saisie
        ))
        
        self.articles_transfert.append({
            'idarticle': self.article_selectionne['id'],
            'idunite': self.article_selectionne['idunite'],
            'code': self.article_selectionne['code'],
            'nom': self.article_selectionne['nom'],
            'unite': self.article_selectionne['unite'],
            'quantite': quantite_saisie
        })
        
        # Réinitialisation des champs de saisie
        self.reinitialiser_champs_article()
    
    def reinitialiser_champs_article(self):
        """Réinitialise les champs de saisie d'article après un ajout réussi."""
        self.entry_code_article.configure(state="normal")
        self.entry_code_article.delete(0, "end")
        self.entry_code_article.configure(state="readonly")

        self.entry_nom_article.configure(state="normal")
        self.entry_nom_article.delete(0, "end")
        self.entry_nom_article.configure(state="readonly")

        self.entry_unite.configure(state="normal")
        self.entry_unite.delete(0, "end")
        self.entry_unite.configure(state="readonly")

        self.entry_quantite.delete(0, "end")

        if hasattr(self, 'article_selectionne'):
            del self.article_selectionne

    def supprimer_ligne(self):
        selection = self.tree.selection()
        if selection:
            index = self.tree.index(selection[0])
            self.tree.delete(selection[0])
            del self.articles_transfert[index]
    
    def enregistrer_transfert(self):
        if not self.articles_transfert:
            messagebox.showwarning("Attention", "Aucun article dans le transfert")
            return
        
        mag_sortie = self.combo_mag_sortie.get()
        mag_entree = self.combo_mag_entree.get()
        
        if not mag_sortie or not mag_entree:
            messagebox.showwarning("Attention", "Sélectionnez les magasins")
            return
        
        if mag_sortie == mag_entree:
            messagebox.showwarning("Attention", "Les magasins doivent être différents")
            return
        
        try:
            conn = self.get_connection()
            if not conn:
                return
            
            cur = conn.cursor()

            # ---------- MODE MODIFICATION (UPDATE) ----------
            if getattr(self, 'idtransfert_en_cours', None) is not None:
                idtransfert = self.idtransfert_en_cours

                # Mettre à jour l'en-tête du transfert
                cur.execute("""
                    UPDATE tb_transfert
                    SET idmagsortie   = %s,
                        idmagentree   = %s,
                        dateregistre  = %s,
                        description   = %s
                    WHERE idtransfert = %s
                """, (
                    self.magasins_data[mag_sortie],
                    self.magasins_data[mag_entree],
                    self.entry_date.get(),
                    self.entry_description.get(),
                    idtransfert
                ))

                # Supprimer les anciennes lignes de détail (soft-delete)
                cur.execute("""
                    UPDATE tb_transfertdetail SET deleted = 1
                    WHERE idtransfert = %s AND deleted = 0
                """, (idtransfert,))

                # Ré-insérer les détails actuels
                for art in self.articles_transfert:
                    cur.execute("""
                        INSERT INTO tb_transfertdetail 
                        (idarticle, idunite, qttransfert, qttransfertsortie, qttransfertentree,
                         deleted, idtransfert, idmagsortie, idmagentree)
                        VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s)
                    """, (
                        art['idarticle'],
                        art['idunite'],
                        art['quantite'],
                        art['quantite'],
                        art['quantite'],
                        idtransfert,
                        self.magasins_data[mag_sortie],
                        self.magasins_data[mag_entree]
                    ))

                conn.commit()
                cur.close()
                conn.close()

                messagebox.showinfo("Succès", f"Transfert « {self.entry_ref.get()} » mis à jour avec succès.")
                self.imprimer_transfert(idtransfert)
                self.nouveau_transfert()
                return   # fin du chemin UPDATE

            # ---------- MODE CRÉATION (INSERT) ----------
            cur.execute("""
                INSERT INTO tb_transfert 
                (reftransfert, iduser, idmagsortie, idmagentree, dateregistre, description, deleted)
                VALUES (%s, %s, %s, %s, %s, %s, 0)
                RETURNING idtransfert
            """, (
                self.entry_ref.get(),
                self.user_id,
                self.magasins_data[mag_sortie],
                self.magasins_data[mag_entree],
                self.entry_date.get(),
                self.entry_description.get()
            ))
            
            idtransfert = cur.fetchone()[0]
            
            # Insérer détails
            for art in self.articles_transfert:
                cur.execute("""
                    INSERT INTO tb_transfertdetail 
                    (idarticle, idunite, qttransfert, qttransfertsortie, qttransfertentree,
                     deleted, idtransfert, idmagsortie, idmagentree)
                    VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s)
                """, (
                    art['idarticle'],
                    art['idunite'],
                    art['quantite'],
                    art['quantite'],
                    art['quantite'],
                    idtransfert,
                    self.magasins_data[mag_sortie],
                    self.magasins_data[mag_entree]
                ))
            
            conn.commit()
            cur.close()
            conn.close()
            
            messagebox.showinfo("Succès", "Transfert enregistré avec succès")
            self.imprimer_transfert(idtransfert)
            self.nouveau_transfert()
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur enregistrement: {str(e)}")
    
    def imprimer_transfert(self, idtransfert):
        try:
            conn = self.get_connection()
            if not conn:
                return
            
            cur = conn.cursor()

            # Infos transfert
            cur.execute("""
                SELECT 
                    t.idtransfert,
                    t.reftransfert,
                    t.dateregistre,
                    t.description,
                    COALESCE(u.username, 'Utilisateur'),
                    COALESCE(ms.designationmag, ''),
                    COALESCE(me.designationmag, '')
                FROM tb_transfert t
                LEFT JOIN tb_users u ON t.iduser = u.iduser
                LEFT JOIN tb_magasin ms ON t.idmagsortie = ms.idmag
                LEFT JOIN tb_magasin me ON t.idmagentree = me.idmag
                WHERE t.idtransfert = %s
            """, (idtransfert,))
            
            transfert = cur.fetchone()
            
            # Détails transfert
            cur.execute("""
                SELECT u.codearticle, a.designation, u.designationunite, td.qttransfert
                FROM tb_transfertdetail td
                LEFT JOIN tb_article a ON td.idarticle = a.idarticle
                LEFT JOIN tb_unite u ON td.idunite = u.idunite
                WHERE td.idtransfert = %s AND td.deleted = 0
            """, (idtransfert,))
            
            details = cur.fetchall()
            
            cur.close()
            conn.close()

            if not transfert:
                messagebox.showwarning("Attention", "Transfert introuvable.")
                return

            reftransfert = transfert[1]
            date_operation = transfert[2].strftime('%d/%m/%Y') if transfert[2] else datetime.now().strftime('%d/%m/%Y')
            description = transfert[3] or ""
            username = transfert[4] or "Utilisateur"
            mag_sortie = transfert[5] or ""
            mag_entree = transfert[6] or ""

            # Construire table_data attendu par _build_pdf_a5
            columns = ("Code", "Désignation", "Unité", "Quantité", "Mouvement")
            rows = []
            mouvement_label = f"{mag_sortie} -> {mag_entree}".strip(" ->")
            for code, designation, unite, qte in details:
                rows.append((
                    str(code or ""),
                    str(designation or ""),
                    str(unite or ""),
                    qte or 0,
                    mouvement_label
                ))

            table_data = (columns, rows)
            filename = f"Transfert_{reftransfert.replace('-', '_')}.pdf"

            try:
                from EtatsPDF_Mouvements import EtatPDFMouvements

                etat = EtatPDFMouvements()
                try:
                    etat.connect_db()
                except Exception:
                    pass

                result = etat._build_pdf_a5(
                    output_path=filename,
                    titre_entete="BON DE TRANSFERT",
                    reference=reftransfert,
                    date_operation=date_operation,
                    magasin=f"{mag_sortie} -> {mag_entree}",
                    operateur=username,
                    table_data=table_data,
                    description=description,
                    responsable_1="Le Magasinier",
                    responsable_2="Le Contrôleur",
                )

                try:
                    etat.close_db()
                except Exception:
                    pass

                if result:
                    try:
                        os.startfile(filename)
                    except Exception:
                        pass
                return result
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur génération PDF transfert (builder): {str(e)}")
                return None
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur impression: {str(e)}")
            
    def desactiver_edition(self):
        """Désactive l'édition des champs et des boutons d'ajout/suppression quand 
           un ancien transfert est chargé."""
        self.entry_date.configure(state="readonly")
        self.entry_description.configure(state="readonly")
        self.combo_mag_sortie.configure(state="readonly")
        self.combo_mag_entree.configure(state="readonly")
        
        # Désactiver les boutons d'action
        self.btn_ajouter.configure(state="disabled")
        self.btn_supprimer.configure(state="disabled")
        self.btn_enregistrer.configure(state="disabled")
        
    def activer_edition(self):
        """Active l'édition des champs et des boutons d'action pour un nouveau transfert."""
        self.entry_date.configure(state="normal")
        self.entry_description.configure(state="normal")
        self.combo_mag_sortie.configure(state="normal")
        self.combo_mag_entree.configure(state="normal")
        
        # Activer les boutons d'action
        self.btn_ajouter.configure(state="normal") 
        self.btn_supprimer.configure(state="normal") 
        self.btn_enregistrer.configure(state="normal") 

    def ouvrir_fenetre_chargement(self):
        """Ouvre une fenêtre pour rechercher et charger un transfert existant.
           Fournit aussi les boutons Modifier et Supprimer sur le transfert sélectionné."""
        
        load_win = ctk.CTkToplevel(self)
        load_win.title("Charger un Transfert Existant")
        load_win.geometry("900x650")
        load_win.grab_set()

        # ---------- zone recherche ----------
        search_frame = ctk.CTkFrame(load_win)
        search_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(search_frame, text="Référence/Magasin:").pack(side="left", padx=5)
        entry_search = ctk.CTkEntry(search_frame, width=300)
        entry_search.pack(side="left", padx=5)
        
        btn_rechercher = ctk.CTkButton(search_frame, text="Rechercher", 
                                       command=lambda: charger_transferts(entry_search.get()))
        btn_rechercher.pack(side="left", padx=5)

        # ---------- treeview ----------
        tree_frame = ctk.CTkFrame(load_win)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side="right", fill="y")
        
        columns = ("ID", "Référence", "Date", "Mag. Sortie", "Mag. Entrée", "Utilisateur")
        self.tree_transferts = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                    yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.tree_transferts.yview)
        
        self.tree_transferts.heading("Référence", text="Référence")
        self.tree_transferts.heading("Date", text="Date")
        self.tree_transferts.heading("Mag. Sortie", text="De (Magasin)")
        self.tree_transferts.heading("Mag. Entrée", text="À (Magasin)")
        self.tree_transferts.heading("Utilisateur", text="Utilisateur")
        
        self.tree_transferts.column("ID", width=0, stretch=False)
        self.tree_transferts.column("Référence", width=150)
        self.tree_transferts.column("Date", width=150)
        self.tree_transferts.column("Mag. Sortie", width=150)
        self.tree_transferts.column("Mag. Entrée", width=150)
        self.tree_transferts.column("Utilisateur", width=100)
        
        self.tree_transferts["displaycolumns"] = ("Référence", "Date", "Mag. Sortie", "Mag. Entrée", "Utilisateur")
        self.tree_transferts.pack(fill="both", expand=True)

        # ---------- barre de boutons (désactivés jusqu'à une sélection) ----------
        btn_frame = ctk.CTkFrame(load_win)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        btn_charger = ctk.CTkButton(btn_frame, text="📂 Charger",
                                    command=lambda: action_charger(),
                                    state="disabled", width=140, height=35,
                                    fg_color="#2e7d32", hover_color="#1b5e20")
        btn_charger.pack(side="left", padx=5, pady=5)

        btn_modifier = ctk.CTkButton(btn_frame, text="✏️  Modifier",
                                     command=lambda: action_modifier(),
                                     state="disabled", width=140, height=35,
                                     fg_color="#1565c0", hover_color="#0d47a1")
        btn_modifier.pack(side="left", padx=5, pady=5)

        btn_supprimer = ctk.CTkButton(btn_frame, text="🗑️  Supprimer",
                                      command=lambda: action_supprimer(),
                                      state="disabled", width=140, height=35,
                                      fg_color="#c62828", hover_color="#b71c1c")
        btn_supprimer.pack(side="left", padx=5, pady=5)

        # ---------- charger la liste ----------
        def charger_transferts(filtre=""):
            try:
                self.tree_transferts.delete(*self.tree_transferts.get_children())
                # Après rafraîchissement, aucune sélection → désactiver les boutons
                mettre_a_jour_boutons()

                conn = self.get_connection()
                if not conn:
                    return
                cur = conn.cursor()
                
                query = """
                    SELECT t.idtransfert, t.reftransfert, t.dateregistre, 
                           ms.designationmag as mag_sortie, me.designationmag as mag_entree, 
                           u.username
                    FROM tb_transfert t
                    LEFT JOIN tb_magasin ms ON t.idmagsortie = ms.idmag
                    LEFT JOIN tb_magasin me ON t.idmagentree = me.idmag
                    LEFT JOIN tb_users u ON t.iduser = u.iduser
                    WHERE t.deleted = 0
                """
                params = []
                if filtre:
                    query += """ AND (LOWER(t.reftransfert) LIKE LOWER(%s) OR 
                                  LOWER(ms.designationmag) LIKE LOWER(%s) OR 
                                  LOWER(me.designationmag) LIKE LOWER(%s))"""
                    params.extend([f"%{filtre}%", f"%{filtre}%", f"%{filtre}%"])
                
                query += " ORDER BY t.dateregistre DESC"
                
                cur.execute(query, tuple(params))
                
                transferts = cur.fetchall()
                for trf in transferts:
                    self.tree_transferts.insert("", "end", values=trf)
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur chargement transferts: {str(e)}")
            finally:
                if 'cur' in locals() and cur:
                    cur.close()
                if 'conn' in locals() and conn:
                    conn.close()

        # ---------- activer/désactiver les boutons selon la sélection ----------
        def mettre_a_jour_boutons(*args):
            etat = "normal" if self.tree_transferts.selection() else "disabled"
            btn_charger.configure(state=etat)
            btn_modifier.configure(state=etat)
            btn_supprimer.configure(state=etat)

        self.tree_transferts.bind("<<TreeviewSelect>>", mettre_a_jour_boutons)

        # ---------- action : charger (lecture seule, comme avant) ----------
        def action_charger():
            selection = self.tree_transferts.selection()
            if not selection:
                return
            id_transfert = self.tree_transferts.item(selection[0])['values'][0]
            self.charger_transfert_selectionne(id_transfert)
            load_win.destroy()

        # ---------- action : modifier ----------
        def action_modifier():
            selection = self.tree_transferts.selection()
            if not selection:
                return
            id_transfert = self.tree_transferts.item(selection[0])['values'][0]
            ref_transfert = self.tree_transferts.item(selection[0])['values'][1]
            self.modifier_transfert(id_transfert, ref_transfert)
            load_win.destroy()

        # ---------- action : supprimer (soft-delete) ----------
        def action_supprimer():
            selection = self.tree_transferts.selection()
            if not selection:
                return
            item = self.tree_transferts.item(selection[0])
            id_transfert = item['values'][0]
            ref_transfert = item['values'][1]

            if not messagebox.askyesno("Confirmation suppression",
                    f"Êtes-vous sûr de vouloir supprimer le transfert\n"
                    f"« {ref_transfert} » ?\n\n"
                    f"Cette action est irréversible."):
                return

            try:
                conn = self.get_connection()
                if not conn:
                    return
                cur = conn.cursor()

                # Soft-delete détails puis en-tête
                cur.execute("UPDATE tb_transfertdetail SET deleted = 1 WHERE idtransfert = %s AND deleted = 0",
                            (id_transfert,))
                cur.execute("UPDATE tb_transfert SET deleted = 1 WHERE idtransfert = %s",
                            (id_transfert,))
                conn.commit()
                cur.close()
                conn.close()

                messagebox.showinfo("Supprimé", f"Transfert « {ref_transfert} » supprimé avec succès.")
                # Rafraîchir la liste
                charger_transferts(entry_search.get())

            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur suppression: {str(e)}")

        # ---------- liaison clavier / double-clic ----------
        charger_transferts()
        entry_search.bind("<Return>", lambda e: charger_transferts(entry_search.get()))
        self.tree_transferts.bind("<Double-1>", lambda e: action_charger())


    def charger_transfert_selectionne(self, idtransfert):
        """Charge les détails du transfert sélectionné dans l'interface principale."""
        try:
            conn = self.get_connection()
            if not conn:
                return

            cur = conn.cursor()

            # 1. Infos transfert principal
            cur.execute("""
                SELECT t.reftransfert, t.dateregistre, t.description, 
                       ms.designationmag, me.designationmag, t.idmagsortie, t.idmagentree
                FROM tb_transfert t
                LEFT JOIN tb_magasin ms ON t.idmagsortie = ms.idmag
                LEFT JOIN tb_magasin me ON t.idmagentree = me.idmag
                WHERE t.idtransfert = %s
            """, (idtransfert,))
            transfert = cur.fetchone()

            if not transfert:
                messagebox.showwarning("Attention", "Transfert non trouvé.")
                cur.close()
                conn.close()
                return

            # On commence un nouveau transfert pour vider l'interface, sans générer de nouvelle référence
            self.nouveau_transfert(is_loading=True)

            # Remplir les champs principaux (en mode lecture seule pour la référence)
            self.entry_ref.configure(state="normal")
            self.entry_ref.delete(0, "end")
            self.entry_ref.insert(0, transfert[0]) # Référence
            self.entry_ref.configure(state="readonly")
            
            self.entry_date.delete(0, "end")
            self.entry_date.insert(0, str(transfert[1])) # Date
            
            self.entry_description.delete(0, "end")
            self.entry_description.insert(0, transfert[2] or '') # Description

            self.combo_mag_sortie.set(transfert[3]) # Magasin Sortie
            self.combo_mag_entree.set(transfert[4]) # Magasin Entrée
            
            # 2. Détails des articles
            cur.execute("""
                SELECT td.idarticle, td.idunite, u.codearticle, a.designation, u.designationunite, td.qttransfert
                FROM tb_transfertdetail td
                LEFT JOIN tb_article a ON td.idarticle = a.idarticle
                LEFT JOIN tb_unite u ON td.idunite = u.idunite
                WHERE td.idtransfert = %s AND td.deleted = 0
            """, (idtransfert,))
            details = cur.fetchall()

            # Remplir le Treeview et la liste interne
            self.articles_transfert = []
            for det in details:
                # Format: (idart, idunite, code, nom, unite, qte)
                
                # Treeview (pour l'affichage)
                self.tree.insert("", "end", values=(det[2], det[3], det[4], det[5]))
                
                # Liste interne (pour la gestion)
                self.articles_transfert.append({
                    'idarticle': det[0],
                    'idunite': det[1],
                    'code': det[2],
                    'nom': det[3],
                    'unite': det[4],
                    'quantite': det[5]
                })

            messagebox.showinfo("Succès", f"Transfert {transfert[0]} chargé. Mode Lecture Seule.")
            
            # Verrouiller l'enregistrement
            self.desactiver_edition()

            cur.close()
            conn.close()

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement du transfert: {str(e)}")
    
    def modifier_transfert(self, idtransfert, ref_transfert):
        """Charge un transfert existant en MODE ÉDITION.
           Les champs restent modifiables et l'enregistrement fait un UPDATE
           sur le même idtransfert au lieu d'un INSERT."""
        try:
            conn = self.get_connection()
            if not conn:
                return

            cur = conn.cursor()

            # 1. Infos transfert principal
            cur.execute("""
                SELECT t.reftransfert, t.dateregistre, t.description, 
                       ms.designationmag, me.designationmag, t.idmagsortie, t.idmagentree
                FROM tb_transfert t
                LEFT JOIN tb_magasin ms ON t.idmagsortie = ms.idmag
                LEFT JOIN tb_magasin me ON t.idmagentree = me.idmag
                WHERE t.idtransfert = %s
            """, (idtransfert,))
            transfert = cur.fetchone()

            if not transfert:
                messagebox.showwarning("Attention", "Transfert non trouvé.")
                cur.close()
                conn.close()
                return

            # Vider l'interface sans générer de nouvelle référence
            self.nouveau_transfert(is_loading=True)

            # Remplir les champs (référence verrouillée, reste éditable)
            self.entry_ref.configure(state="normal")
            self.entry_ref.delete(0, "end")
            self.entry_ref.insert(0, transfert[0])
            self.entry_ref.configure(state="readonly")

            self.entry_date.delete(0, "end")
            self.entry_date.insert(0, str(transfert[1]))

            self.entry_description.delete(0, "end")
            self.entry_description.insert(0, transfert[2] or '')

            self.combo_mag_sortie.set(transfert[3])
            self.combo_mag_entree.set(transfert[4])

            # 2. Détails des articles
            cur.execute("""
                SELECT td.idarticle, td.idunite, u.codearticle, a.designation, u.designationunite, td.qttransfert
                FROM tb_transfertdetail td
                LEFT JOIN tb_article a ON td.idarticle = a.idarticle
                LEFT JOIN tb_unite u ON td.idunite = u.idunite
                WHERE td.idtransfert = %s AND td.deleted = 0
            """, (idtransfert,))
            details = cur.fetchall()

            self.articles_transfert = []
            for det in details:
                self.tree.insert("", "end", values=(det[2], det[3], det[4], det[5]))
                self.articles_transfert.append({
                    'idarticle': det[0],
                    'idunite': det[1],
                    'code': det[2],
                    'nom': det[3],
                    'unite': det[4],
                    'quantite': det[5]
                })

            cur.close()
            conn.close()

            # 3. Activer l'édition complète ET mémoriser l'id pour le UPDATE
            self.activer_edition()
            self.idtransfert_en_cours = idtransfert   # ← clé pour distinguer UPDATE / INSERT

            messagebox.showinfo("Mode Modification",
                f"Transfert « {ref_transfert} » chargé en mode modification.\n"
                f"Vous pouvez changer les articles, les quantités ou les magasins\n"
                f"puis appuyer sur « Enregistrer ».")

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la modification du transfert: {str(e)}")

    def nouveau_transfert(self, is_loading=False):
        # Réinitialiser tous les champs
        self.entry_date.delete(0, "end")
        self.entry_date.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.entry_description.delete(0, "end")
        self.entry_quantite.delete(0, "end")
        
        self.entry_code_article.configure(state="normal")
        self.entry_code_article.delete(0, "end")
        self.entry_code_article.configure(state="readonly")
        
        self.entry_nom_article.configure(state="normal")
        self.entry_nom_article.delete(0, "end")
        self.entry_nom_article.configure(state="readonly")
        
        self.entry_unite.configure(state="normal")
        self.entry_unite.delete(0, "end")
        self.entry_unite.configure(state="readonly")
        
        # Vider le treeview
        self.tree.delete(*self.tree.get_children())
        self.articles_transfert = []
        
        # Nouvelle référence
        if not is_loading: # On ne génère une nouvelle référence que si on commence vraiment un nouveau transfert
            self.generer_reference()
            self.activer_edition() # Réactiver l'édition
            self.idtransfert_en_cours = None  # Réinitialiser → prochain enregistrement sera un INSERT


# Exemple d'utilisation
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    
    root = ctk.CTk()
    root.title("Transfert de Stock")
    root.geometry("600x800")
    
    # ID utilisateur (à récupérer depuis votre système d'authentification)
    user_id = 1
    
    app = PageTransfert(root, user_id)
    app.pack(fill="both", expand=True)
    
    root.mainloop()
