import customtkinter as ctk
import psycopg2
import json
from tkinter import messagebox, filedialog, ttk
import winsound
import pandas as pd
from datetime import datetime
import threading
from resource_utils import get_config_path, safe_file_read


class PageSuiviCommande(ctk.CTkFrame):
    def __init__(self, master, iduser=None):
        super().__init__(master)
        self.iduser = iduser
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # --- En-tête ---
        self.header_frame = ctk.CTkFrame(self, height=60)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        self.lbl_titre = ctk.CTkLabel(self.header_frame, text="📦 SUIVI DES STOCKS & RÉAPPROVISIONNEMENT", font=("Arial", 18, "bold"))
        self.lbl_titre.pack(side="left", padx=20)
        
        self.icon_notif = ctk.CTkLabel(self.header_frame, text="🔔", font=("Arial", 28))
        self.icon_notif.pack(side="right", padx=20)

        # --- Barre de recherche ---
        self.search_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.search_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        self.entry_recherche = ctk.CTkEntry(
            self.search_frame, 
            placeholder_text="🔍 Rechercher par code, désignation, unité ou fournisseur...", 
            width=400,
            height=35
        )
        self.entry_recherche.pack(side="left", padx=5)
        self.entry_recherche.bind('<KeyRelease>', lambda event: self.filtrer_stocks())
        
        self.btn_reinitialiser = ctk.CTkButton(
            self.search_frame, 
            text="🔄 Réinitialiser", 
            command=self.reinitialiser_filtre,
            fg_color="#2e7d32",
            hover_color="#1b5e20",
            width=120
        )
        self.btn_reinitialiser.pack(side="left", padx=5)
        
        self.lbl_compteur = ctk.CTkLabel(
            self.search_frame, 
            text="Articles affichés: 0", 
            font=("Arial", 11, "bold")
        )
        self.lbl_compteur.pack(side="right", padx=20)

        # --- Zone du Tableau (Treeview) ---
        self.setup_treeview()
        
        # --- Barre de boutons en bas ---
        self.bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)

        self.btn_export = ctk.CTkButton(self.bottom_frame, text="📊 Export Excel", 
                                        fg_color="#1D6F42", hover_color="#145A32",
                                        command=self.exporter_excel)
        self.btn_export.pack(side="left", padx=10)

        self.lbl_status = ctk.CTkLabel(self.bottom_frame, text="Dernière mise à jour : --:--", font=("Arial", 10))
        self.lbl_status.pack(side="right", padx=10)

        self.donnees_actuelles = []
        self.donnees_completes = []  # Pour stocker toutes les données avant filtrage
        self.boucle_verification()

    def setup_treeview(self):
        """Configuration du Treeview avec colonnes séparées"""
        self.tree_frame = ctk.CTkFrame(self)
        self.tree_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        
        # Définition des colonnes
        columns = ("code", "designation", "unite", "stock", "alert", "fournisseur")
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings", selectmode="browse")
        
        # Définition des entêtes
        self.tree.heading("code", text="Code Article")
        self.tree.heading("designation", text="Désignation")
        self.tree.heading("unite", text="Unité")
        self.tree.heading("stock", text="Stock Actuel")
        self.tree.heading("alert", text="Seuil Alerte")
        self.tree.heading("fournisseur", text="Dernier Fournisseur")

        # Configuration des largeurs
        self.tree.column("code", width=120, anchor="center")
        self.tree.column("designation", width=250, anchor="w")
        self.tree.column("unite", width=100, anchor="center")
        self.tree.column("stock", width=100, anchor="center")
        self.tree.column("alert", width=100, anchor="center")
        self.tree.column("fournisseur", width=200, anchor="w")

        # Scrollbars
        ysb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=ysb.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        ysb.pack(side="right", fill="y")

        # Style pour les alertes (rouge)
        self.tree.tag_configure("LOW_STOCK", foreground="red", font=('Arial', 10, 'bold'))
        self.tree.tag_configure("even", background="#FFFFFF", foreground="#000000")
        self.tree.tag_configure("odd", background="#E6EFF8", foreground="#000000")
        self.tree.tag_configure("LOW_STOCK_EVEN", background="#FFFFFF", foreground="red", font=('Arial', 10, 'bold'))
        self.tree.tag_configure("LOW_STOCK_ODD", background="#E6EFF8", foreground="red", font=('Arial', 10, 'bold'))

    def connect_db(self):
        try:
            with open(get_config_path('config.json')) as f:
                config = json.load(f)
                db_config = config['database']
            return psycopg2.connect(
                host=db_config['host'], user=db_config['user'],
                password=db_config['password'], database=db_config['database'],
                port=db_config['port']
            )
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur de connexion : {e}")
            return None

    def calculer_stock_article(self, idarticle, idunite_cible, idmag=None):
        """
        Calcule le stock consolidé pour un article (MÊME LOGIQUE que page_stock.py).
        Cette fonction calcule le stock réel basé sur tous les mouvements :
        réceptions, ventes, sorties, transferts, inventaires, avoirs.
        """
        conn = self.connect_db()
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
            
            # 2. Identifier le qtunite de l'unité qu'on veut afficher
            qtunite_affichage = 1
            for idu, code, qt_u in unites_liees:
                if idu == idunite_cible:
                    qtunite_affichage = qt_u if qt_u > 0 else 1
                    break

            total_stock_global_base = 0  # Le "réservoir" total en unité de base (qtunite=1)

            # 3. Sommer les mouvements de chaque variante
            for idu_boucle, code_boucle, qtunite_boucle in unites_liees:
                # Réceptions
                q_rec = "SELECT COALESCE(SUM(qtlivrefrs), 0) FROM tb_livraisonfrs WHERE idarticle = %s AND idunite = %s AND deleted = 0"
                p_rec = [idarticle, idu_boucle]
                if idmag: 
                    q_rec += " AND idmag = %s"
                    p_rec.append(idmag)
                cursor.execute(q_rec, p_rec)
                receptions = cursor.fetchone()[0] or 0
        
                # Ventes
                q_ven = "SELECT COALESCE(SUM(qtvente), 0) FROM tb_ventedetail WHERE idarticle = %s AND idunite = %s AND deleted = 0"
                p_ven = [idarticle, idu_boucle]
                if idmag: 
                    q_ven += " AND idmag = %s"
                    p_ven.append(idmag)
                cursor.execute(q_ven, p_ven)
                ventes = cursor.fetchone()[0] or 0
        
                # Sorties
                q_sort = "SELECT COALESCE(SUM(qtsortie), 0) FROM tb_sortiedetail WHERE idarticle = %s AND idunite = %s"
                p_sort = [idarticle, idu_boucle]
                if idmag: 
                    q_sort += " AND idmag = %s"
                    p_sort.append(idmag)
                cursor.execute(q_sort, p_sort)
                sorties = cursor.fetchone()[0] or 0
        
                # Transferts (In)
                q_tin = "SELECT COALESCE(SUM(qttransfert), 0) FROM tb_transfertdetail WHERE idarticle = %s AND idunite = %s AND deleted = 0"
                p_tin = [idarticle, idu_boucle]
                if idmag:
                    q_tin += " AND idmagentree = %s"
                    p_tin.append(idmag)
                cursor.execute(q_tin, p_tin)
                t_in = cursor.fetchone()[0] or 0
                
                # Transferts (Out)
                q_tout = "SELECT COALESCE(SUM(qttransfert), 0) FROM tb_transfertdetail WHERE idarticle = %s AND idunite = %s AND deleted = 0"
                p_tout = [idarticle, idu_boucle]
                if idmag:
                    q_tout += " AND idmagsortie = %s"
                    p_tout.append(idmag)
                cursor.execute(q_tout, p_tout)
                t_out = cursor.fetchone()[0] or 0
        
                # Inventaires (via codearticle)
                q_inv = "SELECT COALESCE(SUM(qtinventaire), 0) FROM tb_inventaire WHERE codearticle = %s"
                p_inv = [code_boucle]
                if idmag: 
                    q_inv += " AND idmag = %s"
                    p_inv.append(idmag)
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
                if idmag: 
                    q_avoir += " AND ad.idmag = %s"
                    p_avoir.append(idmag)
                cursor.execute(q_avoir, p_avoir)
                avoirs = cursor.fetchone()[0] or 0

                # Normalisation : (Solde unité) * (Son poids)
                solde_unite = (receptions + t_in + inv + avoirs - ventes - sorties - t_out)
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

    def verifier_stocks_optimise(self):
        """Version ULTRA-OPTIMISÉE avec calcul SQL unique (comme page_stock.py)"""
        # Créer une fenêtre de progression
        progress_window = ctk.CTkToplevel(self)
        progress_window.title("Chargement en cours...")
        progress_window.geometry("450x120")
        progress_window.attributes('-topmost', True)
        
        # Centrer la fenêtre
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth() // 2) - (225)
        y = (progress_window.winfo_screenheight() // 2) - (60)
        progress_window.geometry(f"450x120+{x}+{y}")
        
        label = ctk.CTkLabel(progress_window, text="Calcul des stocks...", font=("Arial", 12, "bold"))
        label.pack(pady=20)
        
        progress_bar = ctk.CTkProgressBar(progress_window, width=350, mode='indeterminate')
        progress_bar.pack(pady=10)
        progress_bar.start()
        
        # Lancer le chargement dans un thread
        import threading
        
        def charger_optimise():
            conn = self.connect_db()
            if not conn:
                progress_window.after(0, progress_window.destroy)
                return

            try:
                cursor = conn.cursor()
                
                # REQUÊTE SQL OPTIMISÉE : Calcul global en une seule passe
                query = """
                WITH unite_hierarchie AS (
                    SELECT idarticle, idunite, niveau, qtunite
                    FROM tb_unite
                    WHERE deleted = 0
                ),
                unite_coeff AS (
                    SELECT
                        idarticle,
                        idunite,
                        exp(sum(ln(NULLIF(CASE WHEN qtunite > 0 THEN qtunite ELSE 1 END, 0)))
                            OVER (PARTITION BY idarticle ORDER BY niveau ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                        ) as coeff_hierarchique
                    FROM unite_hierarchie
                ),
                base_unite_par_article AS (
                    SELECT DISTINCT ON (idarticle) idarticle, idunite
                    FROM tb_unite
                    WHERE deleted = 0
                    ORDER BY idarticle, qtunite ASC, idunite ASC
                ),
                rec AS (
                    SELECT idarticle, idunite, SUM(qtlivrefrs) AS quantite
                    FROM tb_livraisonfrs
                    WHERE deleted = 0
                    GROUP BY idarticle, idunite
                ),
                ven AS (
                    SELECT vd.idarticle, vd.idunite, SUM(vd.qtvente) AS quantite
                    FROM tb_ventedetail vd
                    INNER JOIN tb_vente v ON vd.idvente = v.id AND v.deleted = 0
                    WHERE vd.deleted = 0
                    GROUP BY vd.idarticle, vd.idunite
                ),
                tin AS (
                    SELECT idarticle, idunite, SUM(qttransfert) AS quantite
                    FROM tb_transfertdetail
                    WHERE deleted = 0
                    GROUP BY idarticle, idunite
                ),
                tout AS (
                    SELECT idarticle, idunite, SUM(qttransfert) AS quantite
                    FROM tb_transfertdetail
                    WHERE deleted = 0
                    GROUP BY idarticle, idunite
                ),
                sor AS (
                    SELECT idarticle, idunite, SUM(qtsortie) AS quantite
                    FROM tb_sortiedetail
                    GROUP BY idarticle, idunite
                ),
                inv AS (
                    SELECT bu.idarticle, bu.idunite, SUM(i.qtinventaire) AS quantite
                    FROM tb_inventaire i
                    INNER JOIN tb_unite u ON i.codearticle = u.codearticle
                    INNER JOIN base_unite_par_article bu ON bu.idarticle = u.idarticle AND bu.idunite = u.idunite
                    GROUP BY bu.idarticle, bu.idunite
                ),
                avo AS (
                    SELECT ad.idarticle, ad.idunite, SUM(ad.qtavoir) AS quantite
                    FROM tb_avoir a
                    INNER JOIN tb_avoirdetail ad ON a.id = ad.idavoir
                    WHERE a.deleted = 0 AND ad.deleted = 0
                    GROUP BY ad.idarticle, ad.idunite
                ),
                mouvements_agreges AS (
                    SELECT idarticle, idunite, quantite, 'reception' AS type_mouvement FROM rec
                    UNION ALL SELECT idarticle, idunite, quantite, 'vente' AS type_mouvement FROM ven
                    UNION ALL SELECT idarticle, idunite, quantite, 'transfert_in' AS type_mouvement FROM tin
                    UNION ALL SELECT idarticle, idunite, quantite, 'transfert_out' AS type_mouvement FROM tout
                    UNION ALL SELECT idarticle, idunite, quantite, 'sortie' AS type_mouvement FROM sor
                    UNION ALL SELECT idarticle, idunite, quantite, 'inventaire' AS type_mouvement FROM inv
                    UNION ALL SELECT idarticle, idunite, quantite, 'avoir' AS type_mouvement FROM avo
                ),
                solde_base_par_article AS (
                    SELECT
                        ma.idarticle,
                        SUM(
                            CASE ma.type_mouvement
                                WHEN 'reception'     THEN  ma.quantite * COALESCE(uc.coeff_hierarchique, 1)
                                WHEN 'transfert_in'  THEN  ma.quantite * COALESCE(uc.coeff_hierarchique, 1)
                                WHEN 'inventaire'    THEN  ma.quantite * COALESCE(uc.coeff_hierarchique, 1)
                                WHEN 'avoir'         THEN  ma.quantite * COALESCE(uc.coeff_hierarchique, 1)
                                WHEN 'vente'         THEN -ma.quantite * COALESCE(uc.coeff_hierarchique, 1)
                                WHEN 'sortie'        THEN -ma.quantite * COALESCE(uc.coeff_hierarchique, 1)
                                WHEN 'transfert_out' THEN -ma.quantite * COALESCE(uc.coeff_hierarchique, 1)
                                ELSE 0
                            END
                        ) as solde_base
                    FROM mouvements_agreges ma
                    LEFT JOIN unite_coeff uc ON uc.idarticle = ma.idarticle AND uc.idunite = ma.idunite
                    GROUP BY ma.idarticle
                ),
                
                LastSupplier AS (
                    SELECT DISTINCT ON (u.idarticle)
                        u.idarticle,
                        f.nomfrs
                    FROM tb_unite u
                    JOIN tb_commandedetail dc ON u.idunite = dc.idunite
                    JOIN tb_commande c ON dc.idcom = c.idcom
                    JOIN tb_fournisseur f ON c.idfrs = f.idfrs
                    ORDER BY u.idarticle, c.datecom DESC
                )
                
                SELECT DISTINCT ON (a.idarticle)
                    u.codearticle,
                    a.designation,
                    u.designationunite,
                    COALESCE(sb.solde_base, 0) / NULLIF(COALESCE(uc.coeff_hierarchique, 1), 0) as stock,
                    a.alert,
                    COALESCE(ls.nomfrs, 'Aucun fournisseur') as dernier_frs
                FROM tb_article a
                INNER JOIN tb_unite u ON a.idarticle = u.idarticle
                LEFT JOIN unite_coeff uc ON uc.idarticle = u.idarticle AND uc.idunite = u.idunite
                LEFT JOIN solde_base_par_article sb ON sb.idarticle = u.idarticle
                LEFT JOIN LastSupplier ls ON a.idarticle = ls.idarticle
                WHERE a.deleted = 0
                ORDER BY a.idarticle, u.codearticle DESC;
                """
                
                cursor.execute(query)
                articles = cursor.fetchall()
                
                # Nettoyer le Treeview
                self.after(0, lambda: [self.tree.delete(item) for item in self.tree.get_children()])

                alerte_active = False
                donnees_pour_export = []
                
                for idx, art in enumerate(articles):
                    code, nom, unite, stock, alert, frs = art
                    
                    stock = max(0, float(stock or 0))
                    stock_formate = "{:.2f}".format(stock)
                    is_low = stock <= alert
                    
                    if is_low:
                        tags = ("LOW_STOCK_EVEN",) if idx % 2 == 0 else ("LOW_STOCK_ODD",)
                    else:
                        tags = ("even",) if idx % 2 == 0 else ("odd",)
                    
                    # Insérer dans le Treeview
                    self.after(0, lambda c=code, n=nom, u=unite, s=stock_formate, a=alert, f=frs, t=tags:
                        self.tree.insert("", "end", values=(c, n, u, s, a, f), tags=t)
                    )
                    
                    donnees_pour_export.append((code, nom, unite, stock, alert, frs))
                    
                    if is_low:
                        alerte_active = True
                
                self.donnees_actuelles = donnees_pour_export
                self.donnees_completes = donnees_pour_export  # Pour le filtrage
                
                # Mettre à jour le compteur
                self.after(0, lambda t=len(donnees_pour_export): 
                    self.lbl_compteur.configure(text=f"Articles affichés: {t}")
                )
                
                # Notification
                if alerte_active:
                    self.after(0, self.notifier)
                else:
                    self.after(0, lambda: self.icon_notif.configure(text_color="white"))

                # Fermer la fenêtre
                progress_window.after(0, progress_window.destroy)
                
            except Exception as e:
                print(f"Erreur SQL: {e}")
                import traceback
                traceback.print_exc()
                progress_window.after(0, progress_window.destroy)
                self.after(0, lambda: messagebox.showerror("Erreur", f"Erreur lors du chargement : {str(e)}"))
            finally:
                conn.close()
        
        thread = threading.Thread(target=charger_optimise, daemon=True)
        thread.start()

    def verifier_stocks(self):
        """Utilise la version optimisée par défaut"""
        self.verifier_stocks_optimise()

    def exporter_excel(self):
        if not self.donnees_actuelles:
            messagebox.showwarning("Export", "Aucune donnée à exporter.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=f"Alerte_Stock_{datetime.now().strftime('%Y%m%d_%H%M')}"
        )

        if filepath:
            try:
                df = pd.DataFrame(self.donnees_actuelles, columns=[
                    "Code Article", "Désignation", "Unité", "Stock Actuel", "Seuil Alerte", "Dernier Fournisseur"
                ])
                # On exporte tout le tableau, mais on peut filtrer si besoin
                df.to_excel(filepath, index=False)
                messagebox.showinfo("Succès", "Fichier Excel généré.")
            except Exception as e:
                messagebox.showerror("Erreur", f"Export impossible : {e}")

    def boucle_verification(self):
        self.verifier_stocks()
        now = datetime.now().strftime("%H:%M:%S")
        self.lbl_status.configure(text=f"Mise à jour : {now}")
        self.after(60000, self.boucle_verification)

    def notifier(self):
        winsound.Beep(1000, 400)
        current = self.icon_notif.cget("text_color")
        self.icon_notif.configure(text_color="red" if current != "red" else "gray")
    
    def filtrer_stocks(self):
        """Filtre les articles selon le critère de recherche"""
        search_term = self.entry_recherche.get().lower().strip()
        
        # Effacer le Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Si vide, afficher tout
        if not search_term:
            self.recharger_treeview()
            return
        
        # Filtrer les données
        alerte_active = False
        compteur = 0
        
        for idx, data in enumerate(self.donnees_completes):
            code, nom, unite, stock, alert, frs = data
            
            # Recherche dans tous les champs
            if (search_term in str(code).lower() or 
                search_term in nom.lower() or 
                search_term in unite.lower() or 
                search_term in frs.lower()):
                
                stock_formate = "{:.2f}".format(float(stock))
                is_low = stock <= alert
                
                if is_low:
                    tags = ("LOW_STOCK_EVEN",) if idx % 2 == 0 else ("LOW_STOCK_ODD",)
                else:
                    tags = ("even",) if idx % 2 == 0 else ("odd",)
                self.tree.insert("", "end", values=(code, nom, unite, stock_formate, alert, frs), tags=tags)
                
                compteur += 1
                if is_low:
                    alerte_active = True
        
        # Mettre à jour le compteur
        self.lbl_compteur.configure(text=f"Articles affichés: {compteur}")
        
        # Notification si alertes
        if alerte_active:
            self.icon_notif.configure(text_color="red")
        else:
            self.icon_notif.configure(text_color="white")
    
    def reinitialiser_filtre(self):
        """Réinitialise le filtre et affiche tous les articles"""
        self.entry_recherche.delete(0, 'end')
        self.recharger_treeview()
    
    def recharger_treeview(self):
        """Recharge toutes les données dans le Treeview"""
        # Effacer le Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        alerte_active = False
        
        for idx, data in enumerate(self.donnees_completes):
            code, nom, unite, stock, alert, frs = data
            
            stock_formate = "{:.2f}".format(float(stock))
            is_low = stock <= alert
            
            if is_low:
                tags = ("LOW_STOCK_EVEN",) if idx % 2 == 0 else ("LOW_STOCK_ODD",)
            else:
                tags = ("even",) if idx % 2 == 0 else ("odd",)
            self.tree.insert("", "end", values=(code, nom, unite, stock_formate, alert, frs), tags=tags)
            
            if is_low:
                alerte_active = True
        
        # Mettre à jour le compteur
        self.lbl_compteur.configure(text=f"Articles affichés: {len(self.donnees_completes)}")
        
        # Notification
        if alerte_active:
            self.icon_notif.configure(text_color="red")
        else:
            self.icon_notif.configure(text_color="white")
