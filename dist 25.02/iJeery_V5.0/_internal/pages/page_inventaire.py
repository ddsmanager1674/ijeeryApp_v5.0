import customtkinter as ctk
from tkinter import messagebox
import psycopg2
import json
from datetime import datetime
from resource_utils import get_config_path, safe_file_read


class PageInventaire(ctk.CTkToplevel):
    def __init__(self, master, article_data, iduser):
        super().__init__(master)
        self.title(f"Inventaire - {article_data['designation']}")
        self.geometry("450x500")
        self.iduser = iduser
        self.article_data = article_data # Contient 'code' (codearticle) et 'designation'
        self.magasins_dict = {}

        self.attributes('-topmost', True)
        self.setup_ui()
        self.charger_magasins()

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
            messagebox.showerror("Erreur", f"Connexion impossible : {e}")
            return None

    def setup_ui(self):
        ctk.CTkLabel(self, text="📦 Ajustement d'Inventaire", font=("Arial", 18, "bold")).pack(pady=15)
        ctk.CTkLabel(self, text=f"Article: {self.article_data['designation']}\nCode: {self.article_data['code']}", 
                    font=("Arial", 12)).pack(pady=5)

        self.frame = ctk.CTkFrame(self)
        self.frame.pack(pady=10, padx=20, fill="both", expand=True)

        ctk.CTkLabel(self.frame, text="Magasin:").pack(pady=(10,0))
        self.combo_magasin = ctk.CTkComboBox(self.frame, width=250, command=self.afficher_stock_actuel)
        self.combo_magasin.pack(pady=5)

        self.label_stock_actuel = ctk.CTkLabel(self.frame, text="Stock actuel: --", 
                                                font=("Arial", 12, "bold"), 
                                                text_color="#1976d2")
        self.label_stock_actuel.pack(pady=(5,0))

        ctk.CTkLabel(self.frame, text="Quantité réelle comptée:").pack(pady=(10,0))
        self.entry_qt = ctk.CTkEntry(self.frame, width=250)
        self.entry_qt.pack(pady=5)

        ctk.CTkLabel(self.frame, text="Observation (Traçabilité):").pack(pady=(10,0))
        self.entry_obs = ctk.CTkEntry(self.frame, width=250)
        self.entry_obs.pack(pady=5)

        ctk.CTkButton(self.frame, text="Valider l'Inventaire", fg_color="#2e7d32", 
                      command=self.valider).pack(pady=20)

    def charger_magasins(self):
        conn = self.connect_db()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT idmag, designationmag FROM tb_magasin WHERE deleted = 0")
            rows = cursor.fetchall()
            self.magasins_dict = {r[1]: r[0] for r in rows}
            self.combo_magasin.configure(values=list(self.magasins_dict.keys()))

            magasin_defaut_nom = None
            if self.iduser is not None:
                try:
                    cursor.execute(
                        "SELECT idmag FROM tb_users WHERE iduser = %s AND deleted = 0",
                        (self.iduser,)
                    )
                    user_row = cursor.fetchone()
                    if user_row and user_row[0]:
                        idmag_user = user_row[0]
                        magasin_defaut_nom = next((nom for nom, idmag in self.magasins_dict.items() if idmag == idmag_user), None)
                except Exception:
                    magasin_defaut_nom = None

            if rows:
                nom_selectionne = magasin_defaut_nom if magasin_defaut_nom in self.magasins_dict else rows[0][1]
                self.combo_magasin.set(nom_selectionne)
                self.afficher_stock_actuel(nom_selectionne)
            conn.close()

    def afficher_stock_actuel(self, magasin_nom=None):
        """Affiche le stock actuel calculé dynamiquement (même logique que page_stock.py)"""
        if magasin_nom is None:
            magasin_nom = self.combo_magasin.get()
        
        idmag = self.magasins_dict.get(magasin_nom)
        code_article = self.article_data['code']
        
        conn = self.connect_db()
        if conn:
            cursor = conn.cursor()
            
            # Récupérer idarticle et idunite pour ce codearticle
            cursor.execute("""
                SELECT idarticle, idunite, COALESCE(qtunite, 1)
                FROM tb_unite 
                WHERE codearticle = %s
            """, (code_article,))
            res = cursor.fetchone()
            
            if not res:
                self.label_stock_actuel.configure(text=f"Stock actuel: 0,00")
                conn.close()
                return
                
            idarticle, idunite, qtunite_affichage = res
            
            # Calculer le stock en utilisant la MÊME logique que page_stock.py
            stock_actuel = self.calculer_stock_article(idarticle, idunite, idmag)
            
            #self.label_stock_actuel.configure(text=f"Stock actuel: {self.formater_nombre(stock_actuel)}")
            self.label_stock_actuel.configure(text=f"")
            conn.close()
    
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
                # Les avoirs s'AJOUTENT car c'est une annulation de vente (retour marchandise)
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

    def formater_nombre(self, nombre):
        try:
            return f"{float(nombre):,.2f}".replace(',', ' ').replace('.', ',').replace(' ', '.')
        except:
            return "0,00"

    def valider(self):
        mag_nom = self.combo_magasin.get()
        idmag = self.magasins_dict.get(mag_nom)
        obs = self.entry_obs.get()
        code_article = self.article_data['code']
        designation = self.article_data['designation']
        
        if not obs:
            messagebox.showwarning("Attention", "L'observation est obligatoire.")
            return

        conn = self.connect_db()
        if not conn: return

        try:
            nouveau = float(self.entry_qt.get().replace(',', '.'))
            cursor = conn.cursor()

            # --- LOGIQUE MULTI-UNITÉS CORRIGÉE ---
            
            # 1. Récupérer la qtunite de l'article saisi
            cursor.execute("""
                SELECT qtunite FROM tb_unite WHERE codearticle = %s
            """, (code_article,))
            res_u = cursor.fetchone()
            qt_unite_saisie = res_u[0] if res_u and res_u[0] > 0 else 1

            # 2. Trouver TOUTES les unités avec la MÊME désignation
            cursor.execute("""
                SELECT u.codearticle, u.qtunite, a.designation
                FROM tb_unite u
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                WHERE a.designation = %s
                AND a.deleted = 0
                ORDER BY u.codearticle
            """, (designation,))
            unites_liees = cursor.fetchall()
            
            if not unites_liees:
                messagebox.showwarning("Attention", 
                    f"Aucune unité trouvée pour '{designation}'.\n"
                    "Vérifiez que tb_unite et tb_article contiennent bien les enregistrements.")
                conn.close()
                return

            # 3. CALCUL CORRIGÉ : Conversion en unité de base puis vers unité cible
            # qtunite = combien d'unités de base contient cette unité
            # Exemple : 30 CARTONS (qtunite=4) 
            #   → En unité de base : 30 * 4 = 120 sachets
            #   → Pour SACHET (qtunite=1) : 120 / 1 = 120
            #   → Pour CARTON (qtunite=4) : 120 / 4 = 30
            
            # Calcul de la quantité en unité de base (plus petite unité)
            qte_unite_base = nouveau * qt_unite_saisie
            
            unites_mises_a_jour = []
            derniers_ids = []  # Pour stocker les IDs générés
            
            for code_lie, qt_u_lie, desig in unites_liees:
                # Pour chaque unité : quantité_base / qtunite_de_cette_unité
                stock_calcule = qte_unite_base / qt_u_lie

                # a) Récupérer l'ancien stock pour le log
                cursor.execute("""
                    SELECT COALESCE(qtstock, 0) FROM tb_stock 
                    WHERE codearticle = %s AND idmag = %s
                """, (code_lie, idmag))
                res_old = cursor.fetchone()
                ancien_stock_unite = res_old[0] if res_old else 0

                # b) Mise à jour de tb_stock
                cursor.execute("""
                    UPDATE tb_stock SET qtstock = %s 
                    WHERE codearticle = %s AND idmag = %s
                """, (stock_calcule, code_lie, idmag))
                
                if cursor.rowcount == 0:
                    # Insertion si n'existe pas
                    cursor.execute("""
                        INSERT INTO tb_stock (codearticle, idmag, qtstock, qtalert, deleted)
                        VALUES (%s, %s, %s, 0, 0)
                    """, (code_lie, idmag, stock_calcule))
                
                try:
                    # AJOUT DE LA SYNCHRONISATION AVANT L'INSERTION
                    cursor.execute("""
                        SELECT setval(pg_get_serial_sequence('tb_inventaire', 'id'), 
                          COALESCE((SELECT MAX(id) FROM tb_inventaire), 0) + 1, 
                          false);
                    """)

                    # c) Enregistrement dans tb_inventaire
                    # On utilise qtinventaire (colonne réelle) et RETURNING id
                    # Troncature sécurisée de l'observation pour éviter les erreurs
                    # (champ observation potentiellement VARCHAR(50) dans la base)
                    obs_trim = obs if len(obs) <= 50 else obs[:50]
                    cursor.execute("""
                    INSERT INTO tb_inventaire (codearticle, idmag, qtinventaire, iduser, observation, date)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    RETURNING id
                    """, (code_lie, idmag, stock_calcule, self.iduser, obs_trim))
                
                    # Récupération sécurisée du nouvel ID généré (43849, 43850, etc.)
                    resultat = cursor.fetchone()
                    if resultat:
                        id_genere = resultat[0]
                        derniers_ids.append(f"{code_lie}: ID {id_genere}")

                    # AJOUT DE LA SYNCHRONISATION AVANT L'INSERTION
                    cursor.execute("""
                        SELECT setval(pg_get_serial_sequence('tb_log_stock', 'id'), 
                          COALESCE((SELECT MAX(id) FROM tb_log_stock), 0) + 1, 
                          false);
                    """)

                    # d) Log pour traçabilité dans tb_log_stock
                    # Préparer une description d'action tronquée pour le log (éviter VARCHAR(50) overflow)
                    type_action_raw = f"INV AUTO ({designation}): {obs}"
                    type_action = type_action_raw if len(type_action_raw) <= 50 else type_action_raw[:50]
                    cursor.execute("""
                    INSERT INTO tb_log_stock (codearticle, idmag, ancien_stock, nouveau_stock, iduser, type_action, date_action) 
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """, (code_lie, idmag, ancien_stock_unite, stock_calcule, self.iduser, type_action))
                
                    unites_mises_a_jour.append(f"{code_lie} → {stock_calcule:.2f}")

                except psycopg2.Error as e:
                    conn.rollback()
                    messagebox.showerror("Erreur SQL", f"Erreur lors de l'insertion : {e}")
                    return
            conn.commit()
            
            # Message de confirmation détaillé avec les IDs
            detail_msg = "\n".join(unites_mises_a_jour)
            ids_msg = "\n".join(derniers_ids)
            messagebox.showinfo("Succès", 
                f"✓ {len(unites_liees)} unité(s) mise(s) à jour :\n\n{detail_msg}\n\n"
                f"IDs d'inventaire créés :\n{ids_msg}")
    
            # Rafraîchir la page stock parente
            if hasattr(self.master, 'charger_stocks'):
                self.master.charger_stocks()
    
            self.destroy()
            
        except ValueError:
            messagebox.showerror("Erreur", "Quantité saisie invalide.")
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur SQL", f"Détails : {str(e)}")
        finally:
            cursor.close()
            conn.close()
