import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import json
from datetime import datetime
from reportlab.lib.pagesizes import A5, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from tkinter import simpledialog
import os
from tkcalendar import DateEntry # Ajoutez cette ligne avec les autres imports
from resource_utils import get_config_path, safe_file_read


class PageBonReception(ctk.CTkFrame):
    def __init__(self, parent, iduser):
        super().__init__(parent)
        self.iduser = iduser # L'ID utilisateur est correctement stocké ici
        self.items_livraison = []
        self.idcom_selectionne = None
        self.info_commande = None
    
        # *** NOUVEAU : Variables pour l'impression ***
        self.infos_societe = {}
        self.derniere_reflivfrs_enregistree = None
    
        self.setup_ui()
        self.generer_reference()
        self.charger_magasins()
        self.charger_infos_societe()
    
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
        """Formate un nombre avec séparateur de milliers (1.000,00)"""
        try:
            nombre = float(nombre)
            partie_entiere = int(nombre)
            partie_decimale = abs(nombre - partie_entiere)
            
            str_entiere = f"{partie_entiere:,}".replace(',', '.')
            str_decimale = f"{partie_decimale:.2f}".split('.')[1]
            
            return f"{str_entiere},{str_decimale}"
        except:
            return "0,00"
    
    def parser_nombre(self, texte):
        """Convertit un nombre formaté (1.000,00) en float"""
        try:
            texte_clean = texte.replace('.', '').replace(',', '.')
            return float(texte_clean)
        except:
            return 0.0
    
    def nombre_en_lettres(self, nombre):
        """Convertit un nombre entier en une chaîne de caractères en français (version simplifiée)"""
        # Pour une implémentation complète et robuste, utilisez une librairie comme num2words.
        # Cette version est un placeholder.
        try:
            from num2words import num2words
            # Supposer qu'on veut le montant en toutes lettres
            entier = int(nombre)
            decimal = int(round((nombre - entier) * 100))
            
            texte = num2words(entier, lang='fr')
            if decimal > 0:
                 texte += f" et {decimal:02d}/100"
            return texte.upper() + " ARIARY"
        except ImportError:
            # Si num2words n'est pas installé, retourne juste le nombre en chaîne
            # NOTE : Pour l'utilisateur, il faut installer 'num2words' si cette
            # fonction est utilisée pour un usage professionnel. (pip install num2words)
            return f"MONTANT À CONVERTIR: {self.formater_nombre(nombre)} ARIARY"
        except Exception:
            return ""
        
    def setup_ui(self):
        # Titre
        self.titre = ctk.CTkLabel(self, text="Bon de Réception Fournisseur", 
                            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"))
        self.titre.pack(pady=10)
        
        # Frame en haut pour référence, fournisseur et date
        frame_haut = ctk.CTkFrame(self)
        frame_haut.pack(fill="x", padx=20, pady=10)
        
        # Référence
        ctk.CTkLabel(frame_haut, text="Référence BR:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.entry_ref = ctk.CTkEntry(frame_haut, width=200, state="readonly")
        self.entry_ref.grid(row=0, column=1, padx=10, pady=10)
        
        # Bouton Charger Commande
        btn_charger = ctk.CTkButton(frame_haut, text="📂 Charger Commande", 
                                    command=self.ouvrir_recherche_commande, width=150,
                                    fg_color="#1976d2", hover_color="#1565c0")
        btn_charger.grid(row=0, column=2, padx=10, pady=10)
        
        # Fournisseur
        ctk.CTkLabel(frame_haut, text="Fournisseur:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.entry_fournisseur = ctk.CTkEntry(frame_haut, width=300, state="readonly")
        self.entry_fournisseur.grid(row=1, column=1, columnspan=2, padx=10, pady=10, sticky="w")
        
               
        
        # Magasin
        ctk.CTkLabel(frame_haut, text="Magasin:").grid(row=3, column=0, padx=10, pady=10, sticky="w")
        self.combo_magasin = ctk.CTkComboBox(frame_haut, width=300, state="readonly")
        self.combo_magasin.grid(row=3, column=1, columnspan=2, padx=10, pady=10, sticky="w")
        
        # N° Facture Fournisseur
        ctk.CTkLabel(frame_haut, text="N° Facture:").grid(row=3, column=3, padx=10, pady=10, sticky="w")
        
        # --- CORRECTION 1: CRÉATION DU WIDGET MANQUANT ---
        self.entry_factfrs = ctk.CTkEntry(frame_haut, width=200, placeholder_text="Saisir N° Facture Frs")
        # --------------------------------------------------
        self.entry_factfrs.grid(row=3, column=4, columnspan=2, padx=10, pady=10, sticky="w")
        
        # Frame pour le Treeview
        frame_tree = ctk.CTkFrame(self)
        frame_tree.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Label titre du tableau
        label_titre_tableau = ctk.CTkLabel(frame_tree, text="Articles Livrés", 
                                          font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"))
        label_titre_tableau.pack(pady=(5, 5))
        
        # Treeview
        colonnes = ("Article", "Unité", "Date péremption", "Fournisseur", "Qté Livrée", "Prix Unit.", "Montant")
        self.tree = ttk.Treeview(frame_tree, columns=colonnes, show="headings", height=12)
        
        for col in colonnes:
            self.tree.heading(col, text=col)
            if col == "Article":
                self.tree.column(col, width=300)
            elif col == "Unité":
                self.tree.column(col, width=120)
            elif col == "Date péremption":
                self.tree.column(col, width=120)
            elif col == "Fournisseur":
                self.tree.column(col, width=180)
            else:
                self.tree.column(col, width=150)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(frame_tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True, padx=(0, 5))
        scrollbar.pack(side="right", fill="y")
        
        # Frame boutons bas
        frame_boutons = ctk.CTkFrame(self)
        frame_boutons.pack(fill="x", padx=20, pady=10)
        
        # Bouton Nouveau
        btn_nouveau = ctk.CTkButton(frame_boutons, text="🔄 Nouveau", 
                                    command=self.nouveau_bon_reception,
                                    fg_color="#0288d1", hover_color="#01579b")
        btn_nouveau.pack(side="left", padx=10)
        
        # Bouton Imprimer
        btn_imprimer = ctk.CTkButton(frame_boutons, text="🖨️ Imprimer", 
                                     command=self.imprimer_bon_reception,
                                     fg_color="#ff6f00", hover_color="#e65100")
        btn_imprimer.pack(side="right", padx=10)
        
        # Bouton Enregistrer
        btn_enregistrer = ctk.CTkButton(frame_boutons, text="💾 Enregistrer", 
                                        command=self.enregistrer_livraison,
                                        fg_color="#2e7d32", hover_color="#1b5e20")
        btn_enregistrer.pack(side="right", padx=10)
        
        # Label total
        self.label_total = ctk.CTkLabel(frame_boutons, text="Total: 0,00", 
                                       font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"))
        self.label_total.pack(side="right", padx=20)
    
    def toggle_date_peremption(self):
        """Active ou désactive le widget calendrier selon la case à cocher"""
        # Fonction désactivée - widgets non créés
        pass
    
    def charger_magasins(self):
        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT idmag, designationmag FROM tb_magasin WHERE deleted = 0 ORDER BY designationmag")
            rows = cursor.fetchall()
            self.magasins = {r[1]: r[0] for r in rows}
            self.combo_magasin.configure(values=list(self.magasins.keys()))
            if self.magasins:
                idmag_defaut = None
                cursor.execute("SELECT idmag FROM tb_users WHERE iduser = %s LIMIT 1", (self.iduser,))
                row_user = cursor.fetchone()
                if row_user:
                    idmag_defaut = row_user[0]

                nom_magasin_defaut = next((nom for nom, id_ in self.magasins.items() if id_ == idmag_defaut), None)
                if nom_magasin_defaut:
                    self.combo_magasin.set(nom_magasin_defaut)
                else:
                    self.combo_magasin.set(list(self.magasins.keys())[0])
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur chargement magasins: {e}")
        finally:
            cursor.close()
            conn.close()

    def generer_reference(self):
        """Génère la référence automatique au format 2025-BR-00001"""
        conn = self.connect_db()
        if not conn:
            return
            
        try:
            cursor = conn.cursor()
            annee_courante = datetime.now().year
            
            query = """
                SELECT reflivfrs FROM tb_livraisonfrs 
                WHERE reflivfrs LIKE %s 
                ORDER BY reflivfrs DESC LIMIT 1
            """
            cursor.execute(query, (f"{annee_courante}-BR-%",))
            resultat = cursor.fetchone()
            
            if resultat:
                dernier_num = int(resultat[0].split('-')[-1])
                nouveau_num = dernier_num + 1
            else:
                nouveau_num = 1
            
            reference = f"{annee_courante}-BR-{nouveau_num:05d}"
            self.entry_ref.configure(state="normal")
            self.entry_ref.delete(0, "end")
            self.entry_ref.insert(0, reference)
            self.entry_ref.configure(state="readonly")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la génération de la référence: {str(e)}")
        finally:
            cursor.close()
            conn.close()
    
    def ouvrir_recherche_commande(self):
        """Ouvre une fenêtre pour rechercher et charger une commande avec articles livrés"""
        fenetre = ctk.CTkToplevel(self)
        fenetre.title("Sélectionner une commande")
        fenetre.geometry("900x500")
        fenetre.grab_set()
        
        main_frame = ctk.CTkFrame(fenetre)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        titre = ctk.CTkLabel(main_frame, text="Sélectionner une commande avec articles livrés", 
                            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"))
        titre.pack(pady=(0, 10))
        
        search_frame = ctk.CTkFrame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(search_frame, text="🔍 Rechercher:").pack(side="left", padx=5)
        entry_search = ctk.CTkEntry(search_frame, placeholder_text="Référence ou fournisseur...", width=300)
        entry_search.pack(side="left", padx=5, fill="x", expand=True)
        
        tree_frame = ctk.CTkFrame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        colonnes = ("ID", "Référence BC", "Date", "Fournisseur", "Articles Livrés")
        tree = ttk.Treeview(tree_frame, columns=colonnes, show='headings', height=12)
        
        tree.heading("ID", text="ID")
        tree.heading("Référence BC", text="Référence BC")
        tree.heading("Date", text="Date")
        tree.heading("Fournisseur", text="Fournisseur")
        tree.heading("Articles Livrés", text="Articles Livrés")
        
        tree.column("ID", width=0, stretch=False)
        tree.column("Référence BC", width=120, anchor='w')
        tree.column("Date", width=100, anchor='w')
        tree.column("Fournisseur", width=250, anchor='w')
        tree.column("Articles Livrés", width=100, anchor='center')
        
        scrollbar = ctk.CTkScrollbar(tree_frame, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        label_count = ctk.CTkLabel(main_frame, text="Nombre de commandes : 0")
        label_count.pack(pady=5)
        
        def charger_commandes(filtre=""):
            for item in tree.get_children():
                tree.delete(item)
            
            conn = self.connect_db()
            if not conn:
                return
            
            try:
                cursor = conn.cursor()
                # Récupérer les commandes avec au moins un article livré (qtlivre > 0)
                query = """
                    SELECT DISTINCT c.idcom, c.refcom, c.datemodif,
                           COALESCE(
                               NULLIF(
                                   (
                                       SELECT string_agg(DISTINCT COALESCE(f2.nomfrs, ''), ', ' ORDER BY COALESCE(f2.nomfrs, ''))
                                       FROM tb_commandedetail d2
                                       LEFT JOIN tb_fournisseur f2 ON d2.idfrs = f2.idfrs
                                       WHERE d2.idcom = c.idcom
                                   ),
                                   ''
                               ),
                               'Fournisseur non précisé'
                           ) AS fournisseurs_liste,
                           (SELECT COUNT(*) 
                            FROM tb_commandedetail d 
                            WHERE d.idcom = c.idcom AND d.qtlivre > 0) as nb_articles_livres
                    FROM tb_commande c
                    WHERE c.deleted = 0
                    AND EXISTS (
                        SELECT 1 FROM tb_commandedetail d 
                        WHERE d.idcom = c.idcom AND d.qtlivre > 0
                    )
                """
                params = []
                if filtre:
                    query += """ AND (
                        LOWER(c.refcom) LIKE LOWER(%s) OR 
                        LOWER(
                            COALESCE(
                                (
                                    SELECT string_agg(DISTINCT COALESCE(f2.nomfrs, ''), ', ' ORDER BY COALESCE(f2.nomfrs, ''))
                                    FROM tb_commandedetail d2
                                    LEFT JOIN tb_fournisseur f2 ON d2.idfrs = f2.idfrs
                                    WHERE d2.idcom = c.idcom
                                ),
                                ''
                            )
                        ) LIKE LOWER(%s)
                    )"""
                    params = [f"%{filtre}%", f"%{filtre}%"]
                
                query += " ORDER BY c.datemodif DESC, c.refcom DESC"
                cursor.execute(query, params)
                resultats = cursor.fetchall()
                
                for row in resultats:
                    date_str = row[2].strftime("%d/%m/%Y %H:%M") if row[2] else ""
                    tree.insert('', 'end', 
                              values=(row[0], row[1], date_str, row[3] or "", f"✅ {row[4]}"))
                
                label_count.configure(text=f"Nombre de commandes : {len(resultats)}")
                
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors du chargement: {str(e)}")
            finally:
                cursor.close()
                conn.close()
        
        def rechercher(*args):
            charger_commandes(entry_search.get())
        
        entry_search.bind('<KeyRelease>', rechercher)
        
        def valider_selection():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Attention", "Veuillez sélectionner une commande")
                return
            
            values = tree.item(selection[0])['values']
            idcom = values[0]
            fenetre.destroy()
            self.charger_commande(idcom)
        
        tree.bind('<Double-Button-1>', lambda e: valider_selection())
        
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x")
        
        btn_annuler = ctk.CTkButton(btn_frame, text="❌ Annuler", 
                                     command=fenetre.destroy,
                                     fg_color="#d32f2f", hover_color="#b71c1c")
        btn_annuler.pack(side="left", padx=5, pady=5)
        
        btn_valider = ctk.CTkButton(btn_frame, text="✅ Charger", 
                                     command=valider_selection,
                                     fg_color="#2e7d32", hover_color="#1b5e20")
        btn_valider.pack(side="right", padx=5, pady=5)
        
        charger_commandes()
    
    def charger_commande(self, idcom):
        """Charge les articles livrés d'une commande"""
        conn = self.connect_db()
        if not conn:
            return
            
        try:
            cursor = conn.cursor()
            
            # Récupérer les infos de la commande
            query_commande = """
                SELECT c.idcom, c.refcom, c.datemodif, c.idfrs, f.nomfrs
                FROM tb_commande c
                LEFT JOIN tb_fournisseur f ON c.idfrs = f.idfrs
                WHERE c.idcom = %s AND c.deleted = 0
            """
            cursor.execute(query_commande, (idcom,))
            commande = cursor.fetchone()
            
            if not commande:
                messagebox.showerror("Erreur", "Commande non trouvée")
                return
            
            # Récupérer les articles avec qtlivre > 0
            query_details = """
                SELECT d.id,
                       d.idarticle,
                       a.designation,
                       u.designationunite,
                       d.idunite,
                       d.qtlivre,
                       d.punitcmd,
                       d.dateperemption,
                       COALESCE(f_d.nomfrs, f_c.nomfrs, '') AS nomfrs
                FROM tb_commandedetail d
                INNER JOIN tb_commande c ON d.idcom = c.idcom
                INNER JOIN tb_article a ON d.idarticle = a.idarticle
                INNER JOIN tb_unite u ON d.idunite = u.idunite
                LEFT JOIN tb_fournisseur f_d ON d.idfrs = f_d.idfrs
                LEFT JOIN tb_fournisseur f_c ON c.idfrs = f_c.idfrs
                WHERE d.idcom = %s AND d.qtlivre > 0
            """
            cursor.execute(query_details, (idcom,))
            details = cursor.fetchall()
            
            if not details:
                messagebox.showwarning("Attention", "Aucun article livré dans cette commande")
                return
            
            # Réinitialiser
            self.reinitialiser_formulaire(generer_ref=False)
            
            # Stocker les infos
            self.idcom_selectionne = idcom
            self.info_commande = commande
            
            # Remplir les champs
            self.entry_fournisseur.configure(state="normal")
            self.entry_fournisseur.delete(0, "end")
            self.entry_fournisseur.insert(0, commande[4] or "")
            self.entry_fournisseur.configure(state="readonly")
            
            # Remplir le treeview
            for detail in details:
                # unpack includes new dateperemption field (index 7)
                (idcomdetail, idarticle, designation, unite,
                 idunite, qtlivre, punitcmd, dateper, nomfrs_ligne) = detail
                punitcmd = punitcmd if punitcmd else 0
                montant = (qtlivre or 0) * punitcmd
                date_display = dateper.strftime('%d/%m/%Y') if dateper else '-'

                self.tree.insert("", "end", values=(
                    designation,
                    unite,
                    date_display,
                    nomfrs_ligne or "",
                    self.formater_nombre(qtlivre if qtlivre else 0),
                    self.formater_nombre(punitcmd),
                    self.formater_nombre(montant)
                ))

                self.items_livraison.append({
                    'idcomdetail': idcomdetail,
                    'idarticle': idarticle,
                    'idunite': idunite,
                    'fournisseur': nomfrs_ligne or "",
                    'qtlivre': qtlivre or 0,
                    'punitcmd': punitcmd,
                    'dateperemption': dateper
                })
            
            self.calculer_total()
            messagebox.showinfo("Succès", f"Commande {commande[1]} chargée avec {len(details)} article(s) livré(s)")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement: {str(e)}")
        finally:
            cursor.close()
            conn.close()
    
    def calculer_total(self):
        """Calcule et affiche le total"""
        total = sum(item['qtlivre'] * item['punitcmd'] for item in self.items_livraison)
        self.label_total.configure(text=f"Total: {self.formater_nombre(total)}")
    
    def enregistrer_livraison(self):
        """Enregistre le bon de réception avec gestion de la date de péremption optionnelle"""
        if not self.idcom_selectionne:
            messagebox.showwarning("Attention", "Veuillez charger une commande")
            return

        conn = self.connect_db()
        if not conn: return

        try:
            cursor = conn.cursor()
            numero_facture = self.entry_factfrs.get().strip()

            date_peremption = None  # Widget non créé

            if not numero_facture:
                messagebox.showwarning("Attention", "Veuillez saisir le N° Facture Fournisseur.")
                return

            dateregistre = datetime.now()
            idmag = self.magasins.get(self.combo_magasin.get())

            query_insert = """
                INSERT INTO tb_livraisonfrs 
                (reflivfrs, idcom, idarticle, idunite, qtlivrefrs, dateregistre, 
                typemouvement, idmag, factfrs, iduser, dateperemption)
                VALUES (%s, %s, %s, %s, %s, %s, 1, %s, %s, %s, %s)
            """

            # Garder trace des items insérés pour les lots (idlivfrs généré)
            items_avec_peremption = []

            for item in self.items_livraison:
                cursor.execute(query_insert, (
                    self.entry_ref.get(),
                    self.idcom_selectionne,
                    item['idarticle'],
                    item['idunite'],
                    item['qtlivre'],
                    dateregistre,
                    idmag,
                    numero_facture,
                    self.iduser,
                    item.get('dateperemption')
                ))

                # ── Si l'item possède une date de péremption, on mémorise pour insertion lot
                item_date_per = item.get('dateperemption') or date_peremption
                if item_date_per:
                    items_avec_peremption.append({
                        'idarticle': item['idarticle'],
                        'idunite':   item['idunite'],
                        'qtlivre':   item['qtlivre'],
                        'dateperemption': item_date_per,
                    })

            date_peremption = None

            # ── Insertion dans tb_lot_peremption pour chaque item avec péremption ──
            # Fait AVANT le commit pour rester dans la même transaction.
            # Si l'insertion de lot échoue, toute la livraison est annulée.
            if items_avec_peremption:
                for item_per in items_avec_peremption:
                    # Priorité = MAX existant pour cet article/unité/magasin + 1
                    cursor.execute(
                        """
                        SELECT COALESCE(MAX(priorite), 0)
                        FROM tb_lot_peremption
                        WHERE id_article = %s
                        AND id_unite   = %s
                        AND idmag      = %s
                        AND deleted    = 0
                        """,
                        (item_per['idarticle'], item_per['idunite'], idmag)
                    )
                    max_prio = cursor.fetchone()[0]

                    cursor.execute(
                        """
                        INSERT INTO tb_lot_peremption
                            (id_article, id_unite, idmag, quantite,
                            date_peremption, priorite, date_entree,
                            type_source, note)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 'LIVRAISON', %s)
                        """,
                        (
                            item_per['idarticle'],
                            item_per['idunite'],
                            idmag,
                            item_per['qtlivre'],
                            item_per['dateperemption'],
                            max_prio + 1,
                            dateregistre.date(),
                            f"BL {self.entry_ref.get()} — fact. {numero_facture}",
                        )
                    )

            conn.commit()
            self.derniere_reflivfrs_enregistree = self.entry_ref.get()

            messagebox.showinfo("Succès",
                f"Enregistrement effectué avec succès.\n"
                f"Référence: {self.derniere_reflivfrs_enregistree}"
                + (f"\n{len(items_avec_peremption)} lot(s) de péremption créé(s)."
                if items_avec_peremption else ""))

            # ── Génération PDF (logique inchangée) ───────────────────────────
            try:
                data = self.get_data_bon_reception()
                if data:
                    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    etats_dir   = os.path.join(project_dir, "Etats Impression")
                    if not os.path.exists(etats_dir):
                        os.makedirs(etats_dir)

                    filename = os.path.join(etats_dir,
                        f"BR_{self.entry_ref.get().replace('-', '_')}_A5.pdf")

                    cols = ("Code", "Désignation", "Unité", "Qté", "Fournisseur")
                    rows = []
                    for detail in data.get('details', []):
                        qte = detail.get('qtlivre', 0) or 0
                        rows.append((
                            detail.get('code', ''),
                            detail.get('designation', ''),
                            detail.get('unite', ''),
                            qte,
                            detail.get('fournisseur', '')
                        ))
                    table_data = (cols, rows)

                    operateur = (data.get('utilisateur', {}).get('prenomuser', '') + ' ' +
                                data.get('utilisateur', {}).get('nomuser', ''))
                    if not operateur.strip():
                        operateur = str(self.iduser)

                    try:
                        from EtatsPDF_Mouvements import EtatPDFMouvements
                        etat = EtatPDFMouvements()
                        try: etat.connect_db()
                        except Exception: pass

                        success = etat._build_pdf_a5(
                            output_path=filename,
                            titre_entete="BON DE RÉCEPTION",
                            reference=self.entry_ref.get(),
                            date_operation=data['reception'].get('dateregistre',
                                            datetime.now().strftime('%d/%m/%Y')),
                            magasin=data['reception'].get('magasin', ''),
                            operateur=operateur,
                            table_data=table_data,
                            description=numero_facture,
                            responsable_1="Le Responsable",
                            responsable_2=data['reception'].get('fournisseur', 'Fournisseur')
                        )

                        try: etat.close_db()
                        except Exception: pass

                        if success:
                            try: self.open_file(filename)
                            except Exception: pass

                    except Exception as e:
                        print(f"Erreur génération PDF automatique Bon de Réception: {e}")

            except Exception as e:
                print(f"Erreur préparation données pour PDF automatique: {e}")

            self.reinitialiser_formulaire()

        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement: {str(e)}")
        finally:
            cursor.close()
            conn.close()
    
    def nouveau_bon_reception(self):
        """Réinitialise le formulaire"""
        if self.items_livraison:
            reponse = messagebox.askyesno("Confirmation", 
                "Voulez-vous vraiment créer un nouveau bon de réception?\nLes données non enregistrées seront perdues.")
            if not reponse:
                return
        
        self.reinitialiser_formulaire()
    
    def reinitialiser_formulaire(self, generer_ref=True):
        """Réinitialise le formulaire"""
        if generer_ref:
            self.generer_reference()
        self.charger_magasins()
    
        self.items_livraison.clear()
        self.idcom_selectionne = None
        self.info_commande = None
        self.derniere_reflivfrs_enregistree = None  # *** NOUVEAU ***
    
        for item in self.tree.get_children():
            self.tree.delete(item)
    
        self.entry_fournisseur.configure(state="normal")
        self.entry_fournisseur.delete(0, "end")
        self.entry_fournisseur.configure(state="readonly")
        
        # Réinitialisation du champ N° Facture
        self.entry_factfrs.delete(0, "end")
        
        # self.entry_peremption.set_date(datetime.now())  # Widget non créé
    
        self.calculer_total()
    
    def charger_infos_societe(self):
        """Charge les informations de la société depuis tb_infosociete."""
        conn = self.connect_db()
        if not conn: return
    
        try:
            cursor = conn.cursor()
            sql = """
                SELECT 
                    nomsociete, adressesociete, contactsociete, villesociete, 
                    nifsociete, statsociete, cifsociete
                FROM tb_infosociete 
                LIMIT 1
            """
            cursor.execute(sql)
            result = cursor.fetchone()
        
            if result:
                self.infos_societe = {
                    'nomsociete': result[0] or 'SOCIÉTÉ',
                    'adressesociete': result[1] or 'N/A',
                    'contactsociete': result[2] or 'N/A',
                    'villesociete': result[3] or 'N/A',
                    'nifsociete': result[4] or 'N/A',
                    'statsociete': result[5] or 'N/A',
                    'cifsociete': result[6] or 'N/A'
                }
            else:
                self.infos_societe = {
                    'nomsociete': 'SOCIÉTÉ',
                    'adressesociete': 'N/A',
                    'contactsociete': 'N/A',
                    'villesociete': 'N/A',
                    'nifsociete': 'N/A',
                    'statsociete': 'N/A',
                    'cifsociete': 'N/A'
                }
        
        except Exception as e:
            print(f"Erreur chargement infos société: {str(e)}")
            self.infos_societe = {
                'nomsociete': 'SOCIÉTÉ',
                'adressesociete': 'N/A',
                'contactsociete': 'N/A',
                'villesociete': 'N/A',
                'nifsociete': 'N/A',
                'statsociete': 'N/A',
                'cifsociete': 'N/A'
            }
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()
    
    def get_data_bon_reception(self):
        """Récupère toutes les données nécessaires pour imprimer un bon de réception."""
        # Ajouter le N° Facture à l'objet data
        data = {
            'societe': self.infos_societe,
            'reception': {
                'reflivfrs': self.entry_ref.get(),
            'dateregistre': datetime.now().strftime("%d/%m/%Y %H:%M"),
                'fournisseur': self.entry_fournisseur.get(),
                'magasin': self.combo_magasin.get(),
                'factfrs': self.entry_factfrs.get() # Ajout du N° Facture
            },
            'utilisateur': {},
            'details': []
        }
    
        conn = self.connect_db()
        if not conn: return None
    
        try:
            cursor = conn.cursor()
        
            # Infos utilisateur (Utilise self.iduser)
            cursor.execute("SELECT nomuser, prenomuser FROM tb_users WHERE iduser = %s", (self.iduser,))
            user_info = cursor.fetchone()
            if user_info:
                data['utilisateur'] = {
                    'nomuser': user_info[0],
                    'prenomuser': user_info[1]
                }
        
            # Détails des articles
            for item in self.items_livraison:
                cursor.execute("SELECT designation FROM tb_article WHERE idarticle = %s", (item['idarticle'],))
                designation = cursor.fetchone()
            
                cursor.execute("SELECT codearticle, designationunite FROM tb_unite WHERE idunite = %s", (item['idunite'],))
                unite_info = cursor.fetchone()
            
                if designation and unite_info:
                    data['details'].append({
                        'code': unite_info[0],
                        'designation': designation[0],
                        'unite': unite_info[1],
                        'fournisseur': item.get('fournisseur', ''),
                        'qtlivre': item['qtlivre'],
                        'punitcmd': item['punitcmd']
                    })
        
            return data
        
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la récupération des données: {str(e)}")
            return None
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()

    def generer_pdf_a5(self):
        """Génère un Bon de Réception au format PDF A5 (Portrait)."""
    
        data = self.get_data_bon_reception()
        if not data:
            return
    
        filename = f"BR_{self.entry_ref.get().replace('-', '_')}_A5.pdf"
    
        try:
            # Modification : Passage en Portrait (A5 par défaut est portrait)
            doc = SimpleDocTemplate(filename, pagesize=A5,
                                leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
            styles = getSampleStyleSheet()
            elements = []

            societe = data['societe']
        
            # --- 1. EN-TÊTE : Informations société ---
            style_header = styles['Normal']
            style_header.fontSize = 8 # Réduit pour le mode portrait
            style_header.alignment = 1  # Center
        
            adresse = societe.get('adressesociete', 'N/A')
            ville = societe.get('villesociete', 'N/A')
            contact = societe.get('contactsociete', 'N/A')
            infos_legales = f"NIF: {societe.get('nifsociete', 'N/A')} | STAT: {societe.get('statsociete', 'N/A')}\nCIF: {societe.get('cifsociete', 'N/A')}"
        
            elements.append(Paragraph(f"<b>{societe.get('nomsociete', 'NOM SOCIÉTÉ')}</b>", styles['Heading4']))
            elements.append(Paragraph(f"{adresse}, {ville} - Tél: {contact}", style_header))
            elements.append(Paragraph(infos_legales, style_header))
            elements.append(Spacer(1, 10))
        
            # --- 2. TITRE ---
            style_titre = styles['Heading3']
            style_titre.alignment = 1
            p_titre = Paragraph(f"<u>BON DE RÉCEPTION N°{data['reception']['reflivfrs']}</u>", style_titre)
            elements.append(p_titre)
            elements.append(Spacer(1, 10))

            # --- 3. Informations générales (Tableau 2 colonnes pour gagner de la place) ---
            data_header = [
                [Paragraph(f"<b>Date:</b> {data['reception']['dateregistre']}", style_header), 
                 Paragraph(f"<b>Fournisseur:</b> {data['reception']['fournisseur']}", style_header)],
                [Paragraph(f"<b>Magasin:</b> {data['reception']['magasin']}", style_header), 
                 Paragraph(f"<b>Facture N°:</b> {data['reception']['factfrs']}", style_header)],
                [Paragraph(f"<b>Établi par:</b> {data['utilisateur'].get('prenomuser', '')} {data['utilisateur'].get('nomuser', '')}", style_header), ""]
            ]
        
            table_header = Table(data_header, colWidths=[185, 185])
            table_header.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.2, colors.lightgrey)
            ]))
            elements.append(table_header)
            elements.append(Spacer(1, 10))
        
            # --- 4. Tableau des Détails (Colonnes ajustées pour Portrait) ---
            # Répartition des 370 points de largeur disponible environ
            table_data = [
                ['Code', 'Désignation', 'Unité', 'Qté', 'P.U', 'Montant', 'Fournisseur']
            ]
        
            total_general = 0
            for detail in data['details']:
                montant = detail['qtlivre'] * detail['punitcmd']
                total_general += montant
            
                table_data.append([
                    detail['code'],
                    Paragraph(detail['designation'], styles['Normal']), # Paragraph pour retour à la ligne si long
                    detail['unite'],
                    self.formater_nombre(detail['qtlivre']),
                    self.formater_nombre(detail['punitcmd']),
                    self.formater_nombre(montant),
                    Paragraph(detail.get('fournisseur', ''), styles['Normal'])
                ])
        
            table_data.append(['', '', '', '', '', 'TOTAL:', self.formater_nombre(total_general)])

            # Ajustement des largeurs avec colonne Fournisseur
            table_details = Table(table_data, colWidths=[35, 95, 35, 35, 45, 45, 80])
            table_details.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (3, 1), (5, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -2), 0.5, colors.black),
                ('FONTSIZE', (0, 0), (-1, -1), 7), # Taille de police réduite pour le tableau
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                # Style pour la ligne de total
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, -1), (-1, -1), 8),
            ]))
            elements.append(table_details)
            elements.append(Spacer(1, 15))
        
            # --- 5. Montant en lettres ---
            montant_lettres = self.nombre_en_lettres(total_general)
            style_lettres = styles['Normal']
            style_lettres.fontSize = 8
        
            elements.append(Paragraph(f"<b>Arrêté le présent bon à la somme de :</b> {montant_lettres}", style_lettres))
            elements.append(Spacer(1, 20))

            # --- 6. SIGNATURES ---
            data_sig = [['', 'Le Responsable'], ['', '_________________']]
            table_sig = Table(data_sig, colWidths=[200, 170])
            table_sig.setStyle(TableStyle([
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (1, 0), (1, -1), 9),
            ]))
            elements.append(table_sig)

            doc.build(elements)
        
            messagebox.showinfo("Impression A5", f"Le Bon de Réception (Portrait) a été généré :\n{filename}")
            self.open_file(filename)
        
        except Exception as e:
            messagebox.showerror("Erreur Génération", f"Erreur lors de la génération du PDF : {str(e)}")

    def generer_ticket_80mm(self):
        """Génère un Bon de Réception au format Ticket de Caisse 80mm (fichier texte brut)."""
    
        data = self.get_data_bon_reception()
        if not data:
            return
    
        filename = f"BR_{self.entry_ref.get().replace('-', '_')}_80mm.txt"
    
        try:
            societe = data['societe']
            reception = data['reception']
            utilisateur = data['utilisateur']
            details = data['details']
        
            MAX_WIDTH = 40
        
            def center(text):
                return text.center(MAX_WIDTH)
        
            def line():
                return "-" * MAX_WIDTH

            def format_detail_line(designation, qte, unite, prix, montant):
                qte_str = self.formater_nombre(qte)
                prix_str = self.formater_nombre(prix)
                montant_str = self.formater_nombre(montant)
            
                # Ligne 1: Désignation
                designation_str = designation[:MAX_WIDTH]
            
                # Ligne 2: Qté x Prix = Montant
                detail_str = f"{qte_str} {unite} x {prix_str}"
            
                return f"{designation_str}\n{detail_str}\n  = {montant_str}"

            content = []
        
            # --- EN-TÊTE ---
            content.append(center("Informations Société"))
            content.append(f"{societe.get('nomsociete', 'N/A')}")
            content.append(f"{societe.get('adressesociete', 'N/A')}")
            content.append(f"{societe.get('villesociete', 'N/A')}")
            content.append(f"{societe.get('contactsociete', 'N/A')}")
            content.append(line())
            content.append(center(f"NIF: {societe.get('nifsociete', 'N/A')}"))
            content.append(center(f"STAT: {societe.get('statsociete', 'N/A')}"))
        
            # --- INFOS BR ---
            content.append(f"N° BR: {reception['reflivfrs']}")
            content.append(f"Date: {reception['dateregistre']}")
            content.append(f"Fournisseur: {reception['fournisseur']}")
            content.append(f"Magasin: {reception['magasin']}")
            content.append(f"N° Facture: {reception['factfrs']}") # Affichage du N° Facture
            content.append(f"Opérateur: {utilisateur.get('prenomuser', '')} {utilisateur.get('nomuser', '')}")
            content.append(line())
        
            # --- DÉTAILS ---
            content.append("ARTICLES REÇUS")
            content.append(line())
        
            total_general = 0
            for idx, detail in enumerate(details, 1):
                montant = detail['qtlivre'] * detail['punitcmd']
                total_general += montant
            
                content.append(format_detail_line(
                    f"{idx}. {detail['designation']}", 
                    detail['qtlivre'], 
                    detail['unite'],
                    detail['punitcmd'],
                    montant
                ))
                content.append("")
        
            content.append(line())
        
            # --- TOTAL ---
            content.append(center(f"TOTAL: {self.formater_nombre(total_general)} Ar"))
            content.append(line())
        
            # --- MONTANT EN LETTRES ---
            montant_lettres = self.nombre_en_lettres(total_general)
            content.append(center("Montant en lettres:"))
            # Découper le texte si trop long
            words = montant_lettres.split()
            current_line = ""
            for word in words:
                if len(current_line + " " + word) <= MAX_WIDTH:
                    current_line += (" " if current_line else "") + word
                else:
                    content.append(center(current_line))
                    current_line = word
            if current_line:
                content.append(center(current_line))
        
            content.append(line())
        
            # --- PIED DE PAGE ---
            
            content.append("\n" * 3)
            content.append(center("Signature"))
            content.append("\n" * 3)
            content.append(center("Merci de votre collaboration"))
        
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
        
            messagebox.showinfo("Impression 80mm", 
                          f"Le Bon de Réception a été généré en fichier texte (80mm) :\n{filename}\n"
                          "(À imprimer via un pilote d'imprimante thermique)")
            self.open_file(filename)
        
        except Exception as e:
            messagebox.showerror("Erreur Génération", f"Erreur lors de la génération du ticket : {str(e)}")
    
    def open_file(self, filename):
        """Ouvre le fichier généré avec l'application par défaut du système"""
        try:
            if os.name == 'nt':  # Windows
                os.startfile(filename)
            elif os.name == 'posix':  # macOS et Linux
                import subprocess
                import sys
                if sys.platform == 'darwin':  # macOS
                    subprocess.call(['open', filename])
                else:  # Linux
                    subprocess.call(['xdg-open', filename])
        except Exception as e:
            # Si l'ouverture automatique échoue, ce n'est pas grave
            pass

    
    def imprimer_bon_reception(self):
        """Ouvre une boîte de dialogue pour choisir le format d'impression."""
        if not self.derniere_reflivfrs_enregistree:
            messagebox.showwarning("Attention", 
                             "Veuillez d'abord enregistrer le bon de réception avant de l'imprimer.")
            return

        dialogue = simpledialog.askstring("Format d'Impression", 
                                      "Quel format d'impression souhaitez-vous ?\nEntrez 'A5' ou '80mm'.",
                                      parent=self)
                                      
        if dialogue and dialogue.lower() == 'a5':
            self.generer_pdf_a5()
        elif dialogue and dialogue.lower() == '80mm':
            self.generer_ticket_80mm()
        elif dialogue:
            messagebox.showwarning("Format Inconnu", "Format non reconnu. Veuillez choisir 'A5' ou '80mm'.")
    
    

if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("1000x700")
    
    iduser = 1
    
    page = PageBonReception(app, iduser)
    page.pack(fill="both", expand=True)
    
    app.mainloop()
