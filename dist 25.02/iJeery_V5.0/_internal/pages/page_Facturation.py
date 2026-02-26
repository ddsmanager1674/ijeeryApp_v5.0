import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import json
from resource_utils import get_config_path, safe_file_read


from pages.page_venteParMsin import PageVenteParMsin


class PageFacturation(ctk.CTkFrame):

    def __init__(self, master, id_user_connecte=None, **kwargs):
        super().__init__(master, **kwargs)

        self.id_user_connecte = id_user_connecte
        self.magasins = []
        self.tree_stock = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.setup_ui()
        self.charger_magasins()
        self.initialiser_stock_vide()

    # ------------------------------------------------------------------
    # DATABASE
    # ------------------------------------------------------------------
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

    def formater_nombre(self, v):
        try:
            return f"{float(v):,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")
        except Exception:
            return "0,00"

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def setup_ui(self):

        # =======================
        # ZONE 1 : STOCK
        # =======================
        frame_stock = ctk.CTkFrame(self, height=110)
        frame_stock.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        frame_stock.grid_propagate(False)

        ctk.CTkLabel(
            frame_stock,
            text="📦 Stock par dépôt",
            font=ctk.CTkFont(family="Segoe UI", weight="bold")
        ).pack()

        btn_tous = ctk.CTkButton(
            frame_stock,
            text="Afficher tous les stocks",
            width=180,
            command=self.charger_tous_stocks
        )
        btn_tous.pack(pady=(2, 4))

        self.frame_stock_inner = ctk.CTkFrame(frame_stock)
        self.frame_stock_inner.pack(fill="both", expand=True)

        # =======================
        # ZONE 2 : FACTURATION
        # =======================
        frame_vente = ctk.CTkFrame(self)
        frame_vente.grid(row=1, column=0, sticky="nsew", padx=10)

        ctk.CTkLabel(
            frame_vente,
            text="🧾 Facturation",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
        ).pack()

        self.page_vente = PageVenteParMsin(
            frame_vente,
            id_user_connecte=self.id_user_connecte
        )
        self.page_vente.pack(fill="both", expand=True)

        # 🔗 Liaison callback
        self.page_vente.on_article_selected_callback = self.afficher_stock_article_selectionne

    # ------------------------------------------------------------------
    # MAGASINS
    # ------------------------------------------------------------------
    def charger_magasins(self):
        conn = self.connect_db()
        if not conn:
            return

        cur = conn.cursor()
        cur.execute("""
            SELECT idmag, designationmag
            FROM tb_magasin
            WHERE deleted = 0
            ORDER BY designationmag
        """)
        self.magasins = cur.fetchall()

        noms = [m[1] for m in self.magasins]
        self.page_vente.combo_magasin.configure(values=noms)
        if noms:
            self.page_vente.combo_magasin.set(noms[0])

        conn.close()

    # ------------------------------------------------------------------
    # STOCK GLOBAL
    # ------------------------------------------------------------------
    def creer_treeview_stock(self):

        if self.tree_stock:
            self.tree_stock.destroy()

        cols = ("idarticle", "idunite", "code", "designation", "unite") + \
               tuple(m[1] for m in self.magasins) + ("Total",)

        self.tree_stock = ttk.Treeview(
            self.frame_stock_inner,
            columns=cols,
            show="headings",
            height=1
        )

        for c in cols:
            self.tree_stock.heading(c, text=c)
            if c.startswith("id"):
                self.tree_stock.column(c, width=0, stretch=False)
            elif c == "designation":
                self.tree_stock.column(c, width=260)
            else:
                self.tree_stock.column(c, width=90, anchor="center")

        self.tree_stock.pack(fill="both", expand=True)

    def initialiser_stock_vide(self):
        """Crée le Treeview vide au démarrage"""
        self.creer_treeview_stock()

    def charger_tous_stocks(self):
        """Charge tous les articles avec leur stock"""
        self.creer_treeview_stock()
        
        conn = self.connect_db()
        if not conn:
            return

        cur = conn.cursor()
        
        # Récupérer tous les articles avec CAST pour préserver les zéros
        cur.execute("""
            SELECT DISTINCT a.idarticle, u.idunite, 
                   CAST(a.codearticle AS TEXT) as codearticle,
                   a.designationarticle, u.designationunite
            FROM tb_article a
            CROSS JOIN tb_unite u
            WHERE a.deleted = 0
            ORDER BY a.designationarticle
        """)
        
        articles = cur.fetchall()
        conn.close()

        # Afficher chaque article avec son stock dans tous les magasins
        for article in articles:
            idarticle, idunite, code, designation, unite = article
            
            # Formater le code avec les zéros initiaux si nécessaire
            code_formate = str(code).zfill(10) if code else ""
            
            stocks = []
            total = 0
            
            for mag in self.magasins:
                qte = self.calculer_stock_article(idarticle, idunite, mag[0])
                stocks.append(self.formater_nombre(qte))
                total += qte
            
            # N'afficher que les articles avec du stock
            if total > 0:
                self.tree_stock.insert("", "end", values=[
                    idarticle, idunite, code_formate, designation, unite,
                    *stocks,
                    self.formater_nombre(total)
                ])

    # ------------------------------------------------------------------
    # 🔥 STOCK ARTICLE SÉLECTIONNÉ
    # ------------------------------------------------------------------
    def afficher_stock_article_selectionne(
        self, idarticle, idunite, code, designation, unite, check_only=False
    ):
        print(f"🔥 Callback appelé avec: {idarticle}, {code}, {designation}")
        
        if self.tree_stock is None:
            self.creer_treeview_stock()

        # Formater le code avec les zéros initiaux
        code_formate = str(code).zfill(10) if code else ""

        total = 0
        for mag in self.magasins:
            total += self.calculer_stock_article(idarticle, idunite, mag[0])

        if check_only:
            print(f"Check only: retour total = {total}")
            return total

        # Vider le Treeview
        for item in self.tree_stock.get_children():
            self.tree_stock.delete(item)

        # Calculer les stocks par magasin
        stocks = []
        for mag in self.magasins:
            qte = self.calculer_stock_article(idarticle, idunite, mag[0])
            stocks.append(self.formater_nombre(qte))
            print(f"Magasin {mag[1]}: {qte}")

        # Insérer la ligne avec l'article sélectionné
        self.tree_stock.insert("", "end", values=[
            idarticle, idunite, code_formate, designation, unite,
            *stocks,
            self.formater_nombre(total)
        ])
        
        print(f"Total affiché: {total}")

    # ------------------------------------------------------------------
    # CALCUL STOCK
    # ------------------------------------------------------------------
    def calculer_stock_article(self, idarticle, idunite, idmag=None):
        """
        Calcule le stock d'un article pour un magasin donné
        Prend en compte les conversions d'unités hiérarchiques ET les ajustements d'inventaire
        """
        conn = self.connect_db()
        if not conn:
            return 0

        try:
            cursor = conn.cursor()
    
            # Récupérer toutes les unités de cet article avec leur qtunite
            cursor.execute("""
            SELECT idunite, COALESCE(qtunite, 1) as qtunite
            FROM tb_unite 
            WHERE idarticle = %s
            ORDER BY idunite ASC 
        """, (idarticle,))
            unites_article = cursor.fetchall()
    
            if not unites_article:
                return 0
    
            # L'unité de base est la première dans la liste triée
            idunite_base = unites_article[0][0]
    
            # Créer un dictionnaire : {idunite: facteur_vers_base}
            facteurs_conversion = {}
    
            # L'unité de base a un facteur de 1
            facteurs_conversion[idunite_base] = 1.0
    
            # Pour les autres unités, calculer le facteur cumulatif
            facteur_cumul = 1.0
            for i, (id_unite, qt_unite) in enumerate(unites_article):
                if i == 0:
                    facteurs_conversion[id_unite] = 1.0
                else:
                    facteur_cumul *= qt_unite
                    facteurs_conversion[id_unite] = facteur_cumul
    
            # Construire la clause WHERE pour le magasin
            clause_mag = "AND idmag = %s" if idmag else ""
            params_mag = [idmag] if idmag else []
    
            # Calculer le stock total dans l'unité de base
            stock_en_unite_base = 0
    
            # Pour chaque unité de l'article, calculer le stock et le convertir vers l'unité de base
            for idunite_source, qtunite_source in unites_article:
                # 1. Livraisons fournisseurs (ENTRÉE)
                query_livraison = f"""
                SELECT COALESCE(SUM(qtlivrefrs), 0) 
                FROM tb_livraisonfrs 
                WHERE idarticle = %s AND idunite = %s {clause_mag}
            """
                cursor.execute(query_livraison, [idarticle, idunite_source] + params_mag)
                total_livraison = cursor.fetchone()[0] or 0
        
                # 2. Ventes (SORTIE)
                query_vente = f"""
                SELECT COALESCE(SUM(qtvente), 0) 
                FROM tb_ventedetail 
                WHERE idarticle = %s AND idunite = %s {clause_mag}
            """
                cursor.execute(query_vente, [idarticle, idunite_source] + params_mag)
                total_vente = cursor.fetchone()[0] or 0
        
                # 3. Sorties (SORTIE)
                query_sortie = f"""
                SELECT COALESCE(SUM(qtsortie), 0) 
                FROM tb_sortiedetail 
                WHERE idarticle = %s AND idunite = %s {clause_mag}
            """
                cursor.execute(query_sortie, [idarticle, idunite_source] + params_mag)
                total_sortie = cursor.fetchone()[0] or 0
        
                # 4. Transferts sortants (SORTIE)
                query_transfert_sortie = """
                SELECT COALESCE(SUM(td.qttransfertsortie), 0)
                FROM tb_transfertdetail td
                INNER JOIN tb_transfert t ON td.idtransfert = t.idtransfert
                WHERE td.idarticle = %s AND td.idunite = %s
            """
                params_transfert_sortie = [idarticle, idunite_source]
                if idmag:
                    query_transfert_sortie += " AND t.idmagsortie = %s"
                    params_transfert_sortie.append(idmag)
        
                cursor.execute(query_transfert_sortie, params_transfert_sortie)
                total_transfert_sortie = cursor.fetchone()[0] or 0
        
                # 5. Transferts entrants (ENTRÉE)
                query_transfert_entree = """
                SELECT COALESCE(SUM(td.qttransfertentree), 0)
                FROM tb_transfertdetail td
                INNER JOIN tb_transfert t ON td.idtransfert = t.idtransfert
                WHERE td.idarticle = %s AND td.idunite = %s
            """
                params_transfert_entree = [idarticle, idunite_source]
                if idmag:
                    query_transfert_entree += " AND t.idmagentree = %s"
                    params_transfert_entree.append(idmag)
        
                cursor.execute(query_transfert_entree, params_transfert_entree)
                total_transfert_entree = cursor.fetchone()[0] or 0
            
                # 6. AVOIR (ENTRÉE)
                query_avoir = f"""
                SELECT COALESCE(SUM(qtavoir), 0) 
                FROM tb_avoirdetail 
                WHERE idarticle = %s AND idunite = %s {clause_mag}
            """
                cursor.execute(query_avoir, [idarticle, idunite_source] + params_mag)
                total_avoir = cursor.fetchone()[0] or 0
        
                # Calcul du stock pour cette unité source
                stock_unite_source = (total_livraison + total_avoir + total_transfert_entree - 
                             total_vente - total_sortie - total_transfert_sortie)
        
                # Convertir vers l'unité de base
                facteur_vers_base = facteurs_conversion.get(idunite_source, 1.0)
                stock_en_unite_base += stock_unite_source * facteur_vers_base
    
            # ✅ CORRECTION MAJEURE : Récupérer le codearticle pour chercher les inventaires
            cursor.execute("""
            SELECT codearticle FROM tb_unite WHERE idarticle = %s AND idunite = %s
        """, (idarticle, idunite))
            res_code = cursor.fetchone()
        
            if res_code and idmag:
                code_article = res_code[0]
            
                # 7. AJUSTEMENTS D'INVENTAIRE
                # Récupérer le dernier inventaire validé pour cet article et ce magasin
                cursor.execute("""
                SELECT qtinventaire, date 
                FROM tb_inventaire 
                WHERE codearticle = %s AND idmag = %s
                ORDER BY date DESC
                LIMIT 1
            """, (code_article, idmag))
            
                dernier_inventaire = cursor.fetchone()
            
                if dernier_inventaire:
                    qt_inventaire = dernier_inventaire[0]
                    date_inventaire = dernier_inventaire[1]
                
                    # Convertir l'unité de base vers l'unité cible
                    facteur_cible = facteurs_conversion.get(idunite, 1.0)
                    if facteur_cible == 0:
                        return 0
                    
                    stock_calcule_avant_inv = stock_en_unite_base / facteur_cible
                
                    # Calculer les mouvements APRÈS l'inventaire
                    mouvements_apres = 0
                
                    for idunite_source, qtunite_source in unites_article:
                        # Livraisons après inventaire
                        cursor.execute(f"""
                        SELECT COALESCE(SUM(qtlivrefrs), 0) 
                        FROM tb_livraisonfrs 
                        WHERE idarticle = %s AND idunite = %s AND idmag = %s
                        AND dateregistre > %s
                    """, (idarticle, idunite_source, idmag, date_inventaire))
                        liv_apres = cursor.fetchone()[0] or 0
                    
                        # Ventes après inventaire
                        cursor.execute(f"""
                        SELECT COALESCE(SUM(vd.qtvente), 0) 
                        FROM tb_ventedetail vd
                        INNER JOIN tb_vente v ON vd.idvente = v.id
                        WHERE vd.idarticle = %s AND vd.idunite = %s AND vd.idmag = %s
                        AND v.dateregistre > %s
                    """, (idarticle, idunite_source, idmag, date_inventaire))
                        vte_apres = cursor.fetchone()[0] or 0
                    
                        # Sorties après inventaire
                        cursor.execute(f"""
                        SELECT COALESCE(SUM(sd.qtsortie), 0) 
                        FROM tb_sortiedetail sd
                        INNER JOIN tb_sortie s ON sd.idsortie = s.id
                        WHERE sd.idarticle = %s AND sd.idunite = %s AND sd.idmag = %s
                        AND s.dateregistre > %s
                    """, (idarticle, idunite_source, idmag, date_inventaire))
                        sort_apres = cursor.fetchone()[0] or 0
                    
                        # Avoir après inventaire
                        cursor.execute(f"""
                        SELECT COALESCE(SUM(ad.qtavoir), 0) 
                        FROM tb_avoirdetail ad
                        INNER JOIN tb_avoir a ON ad.idavoir = a.id
                        WHERE ad.idarticle = %s AND ad.idunite = %s AND ad.idmag = %s
                        AND a.dateregistre > %s
                    """, (idarticle, idunite_source, idmag, date_inventaire))
                        avoir_apres = cursor.fetchone()[0] or 0
                    
                        # Transferts sortants après inventaire
                        cursor.execute("""
                        SELECT COALESCE(SUM(td.qttransfertsortie), 0)
                        FROM tb_transfertdetail td
                        INNER JOIN tb_transfert t ON td.idtransfert = t.idtransfert
                        WHERE td.idarticle = %s AND td.idunite = %s
                        AND t.idmagsortie = %s AND t.dateregistre > %s
                    """, (idarticle, idunite_source, idmag, date_inventaire))
                        transf_sort_apres = cursor.fetchone()[0] or 0
                    
                        # Transferts entrants après inventaire
                        cursor.execute("""
                        SELECT COALESCE(SUM(td.qttransfertentree), 0)
                        FROM tb_transfertdetail td
                        INNER JOIN tb_transfert t ON td.idtransfert = t.idtransfert
                        WHERE td.idarticle = %s AND td.idunite = %s
                        AND t.idmagentree = %s AND t.dateregistre > %s
                    """, (idarticle, idunite_source, idmag, date_inventaire))
                        transf_entr_apres = cursor.fetchone()[0] or 0
                    
                        # Calculer mouvement dans cette unité et convertir
                        mouv_unite = (liv_apres + avoir_apres + transf_entr_apres - 
                                 vte_apres - sort_apres - transf_sort_apres)
                    
                        facteur_vers_base = facteurs_conversion.get(idunite_source, 1.0)
                        mouvements_apres += mouv_unite * facteur_vers_base
                
                    # Stock final = Inventaire + Mouvements après inventaire (converti)
                    mouvements_apres_converti = mouvements_apres / facteur_cible
                    stock_final = qt_inventaire + mouvements_apres_converti
                
                    return stock_final
    
            # Convertir de l'unité de base vers l'unité cible demandée
            facteur_cible = facteurs_conversion.get(idunite, 1.0)
    
            if facteur_cible == 0:
                return 0
    
            stock_final = stock_en_unite_base / facteur_cible
            return stock_final
    
        except Exception as e:
            print(f"Erreur calcul stock: {str(e)}")
            import traceback
            traceback.print_exc()
            return 0
        finally:
            cursor.close()
            conn.close()

# ----------------------------------------------------------------------
# TEST
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("1400x800")
    app.title("Facturation")

    page = PageFacturation(app, id_user_connecte=1)
    page.pack(fill="both", expand=True)

    app.mainloop()