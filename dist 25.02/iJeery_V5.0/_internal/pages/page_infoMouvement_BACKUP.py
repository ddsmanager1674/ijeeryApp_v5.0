import customtkinter as ctk
from tkinter import messagebox, ttk
import psycopg2
import json
from datetime import datetime
from resource_utils import get_config_path, safe_file_read


# Importation des pages existantes
from pages.page_CmdFrs import PageCommandeFrs
from pages.page_livrFrs import PageBonReception
from pages.page_transfert import PageTransfert
from pages.page_sortie import PageSortie
from pages.page_SuiviCommande import PageSuiviCommande


# ============ CLASSE CHANGEMENT D'ARTICLES ============

class PageChangementArticle(ctk.CTkFrame):
    """
    CLASSE POUR GESTION DES CHANGEMENTS D'ARTICLES.
    Permet les sorties et entrées d'articles avec interface verticale.
    """
    def __init__(self, master, iduser):
        super().__init__(master, fg_color="white")
        self.iduser = iduser
        self.magasins = {}
        self.idchg_charge = None
        self.mode_modification = False
        
        # Données pour sorties (articles à changer)
        self.articles_sortie = []
        self.article_sortie_selectionne = None
        
        # Données pour entrées (articles reçus)
        self.articles_entree = []
        self.article_entree_selectionne = None
        
        self.setup_ui()
        self.charger_magasins()
        self.generer_reference()

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
            messagebox.showerror("Erreur de connexion", f"Erreur: {str(e)}")
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

    def generer_reference(self):
        """Génère la référence automatique au format 2025-CHG-00001"""
        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            annee_courante = datetime.now().year
            query = """
                SELECT refchg FROM tb_changement 
                WHERE refchg LIKE %s 
                ORDER BY refchg DESC LIMIT 1
            """
            cursor.execute(query, (f"{annee_courante}-CHG-%",))
            resultat = cursor.fetchone()
            
            if resultat:
                dernier_num = int(resultat[0].split('-')[-1])
                nouveau_num = dernier_num + 1
            else:
                nouveau_num = 1
            
            reference = f"{annee_courante}-CHG-{nouveau_num:05d}"
            self.entry_ref.configure(state="normal")
            self.entry_ref.delete(0, "end")
            self.entry_ref.insert(0, reference)
            self.entry_ref.configure(state="readonly")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la génération: {str(e)}")
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if conn:
                conn.close()

    def charger_magasins(self):
        """Charge la liste des magasins"""
        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            query = "SELECT idmagasin, nommagasin FROM tb_magasin WHERE deleted = 0 ORDER BY nommagasin"
            cursor.execute(query)
            self.magasins = {row[1]: row[0] for row in cursor.fetchall()}
            
            noms_magasins = list(self.magasins.keys())
            self.combo_mag_sortie.configure(values=noms_magasins)
            self.combo_mag_entree.configure(values=noms_magasins)
            
            if noms_magasins:
                self.combo_mag_sortie.set(noms_magasins[0])
                self.combo_mag_entree.set(noms_magasins[0])
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur chargement magasins: {str(e)}")
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if conn:
                conn.close()

    def setup_ui(self):
        """Construit l'interface utilisateur - DISPOSITION VERTICALE"""
        # ============ EN-TÊTE ============
        frame_entete = ctk.CTkFrame(self)
        frame_entete.pack(fill="x", padx=20, pady=10)

        titre = ctk.CTkLabel(frame_entete, text="Changement d'Articles", 
                            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"))
        titre.pack(pady=10, anchor="w")

        # Référence, Date, Charger sur une ligne
        frame_ref_date = ctk.CTkFrame(frame_entete)
        frame_ref_date.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(frame_ref_date, text="Référence:").pack(side="left", padx=10)
        self.entry_ref = ctk.CTkEntry(frame_ref_date, width=150, state="readonly")
        self.entry_ref.pack(side="left", padx=5)

        ctk.CTkLabel(frame_ref_date, text="Date:").pack(side="left", padx=10)
        self.entry_date = ctk.CTkEntry(frame_ref_date, width=120, state="readonly")
        self.entry_date.configure(state="normal")
        self.entry_date.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.entry_date.configure(state="readonly")
        self.entry_date.pack(side="left", padx=5)

        btn_charger = ctk.CTkButton(frame_ref_date, text="📂 Charger", 
                                    command=self.ouvrir_recherche_changement, width=140,
                                    fg_color="#1976d2", hover_color="#1565c0")
        btn_charger.pack(side="left", padx=10)

        # ============ CORPS PRINCIPAL (VERTICAL) ============
        frame_contenu = ctk.CTkFrame(self, fg_color="transparent")
        frame_contenu.pack(fill="both", expand=True, padx=20, pady=10)

        # ========== PANEL HAUT : SORTIES ==========
        frame_sortie = ctk.CTkFrame(frame_contenu, fg_color="#FFF5F5", border_width=2, border_color="#D32F2F")
        frame_sortie.pack(fill="both", expand=True, padx=0, pady=(0, 10))

        # En-tête Sortie (Titre + Magasin)
        frame_header_sortie = ctk.CTkFrame(frame_sortie, fg_color="transparent")
        frame_header_sortie.pack(fill="x", padx=10, pady=10)
        
        titre_sortie = ctk.CTkLabel(frame_header_sortie, text="📤 ARTICLES À CHANGER (Sortie)", 
                                    font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                                    text_color="#D32F2F")
        titre_sortie.pack(side="left", anchor="w")
        
        # Magasin Sortie (à droite)
        frame_mag_sortie = ctk.CTkFrame(frame_header_sortie, fg_color="transparent")
        frame_mag_sortie.pack(side="right", fill="x", expand=False)
        ctk.CTkLabel(frame_mag_sortie, text="Magasin:").pack(side="left", padx=5)
        self.combo_mag_sortie = ctk.CTkComboBox(frame_mag_sortie, width=200, state="readonly")
        self.combo_mag_sortie.pack(side="left", padx=5)

        # Ligne de saisie complète (Article, Charger, Quantité, Unité, Boutons)
        frame_input_sortie = ctk.CTkFrame(frame_sortie, fg_color="transparent")
        frame_input_sortie.pack(fill="x", padx=10, pady=5)

        self.entry_article_sortie = ctk.CTkEntry(frame_input_sortie, placeholder_text="Rechercher article...", width=200)
        self.entry_article_sortie.pack(side="left", padx=3)

        btn_recherche_sortie = ctk.CTkButton(frame_input_sortie, text="🔍 Charger", 
                                            command=self.ouvrir_recherche_article_sortie, width=100,
                                            fg_color="#1976d2", hover_color="#1565c0")
        btn_recherche_sortie.pack(side="left", padx=3)

        self.entry_qty_sortie = ctk.CTkEntry(frame_input_sortie, placeholder_text="Qty", width=60)
        self.entry_qty_sortie.pack(side="left", padx=3)

        self.entry_unite_sortie = ctk.CTkEntry(frame_input_sortie, placeholder_text="Unité", width=60, state="readonly")
        self.entry_unite_sortie.pack(side="left", padx=3)

        self.btn_ajouter_sortie = ctk.CTkButton(frame_input_sortie, text="➕ Ajouter", 
                                               command=self.ajouter_article_sortie, width=90,
                                               fg_color="#2e7d32", hover_color="#1b5e20")
        self.btn_ajouter_sortie.pack(side="left", padx=3)

        self.btn_annuler_sortie = ctk.CTkButton(frame_input_sortie, text="❌ Annuler", 
                                               command=self.annuler_sortie, width=80,
                                               fg_color="#757575", hover_color="#616161")
        self.btn_annuler_sortie.pack(side="left", padx=3)

        # Tableau Sortie
        frame_tree_sortie = ctk.CTkFrame(frame_sortie)
        frame_tree_sortie.pack(fill="both", expand=True, padx=10, pady=10)
        frame_tree_sortie.grid_rowconfigure(0, weight=1)
        frame_tree_sortie.grid_columnconfigure(0, weight=1)

        colonnes_sortie = ("Code", "Désignation", "Unité", "Magasin", "Quantité")
        self.tree_sortie = ttk.Treeview(frame_tree_sortie, columns=colonnes_sortie, show="headings", height=2)
        
        for col in colonnes_sortie:
            self.tree_sortie.heading(col, text=col)
            if col == "Désignation":
                self.tree_sortie.column(col, width=200)
            else:
                self.tree_sortie.column(col, width=100)

        scrollbar_sortie = ttk.Scrollbar(frame_tree_sortie, orient="vertical", command=self.tree_sortie.yview)
        self.tree_sortie.configure(yscrollcommand=scrollbar_sortie.set)

        self.tree_sortie.pack(side="left", fill="both", expand=True)
        scrollbar_sortie.pack(side="right", fill="y")

        # Bouton Supprimer Sortie
        btn_supprimer_sortie = ctk.CTkButton(frame_sortie, text="🗑️ Supprimer Ligne", 
                                            command=self.supprimer_article_sortie,
                                            fg_color="#d32f2f", hover_color="#b71c1c", width=150)
        btn_supprimer_sortie.pack(padx=10, pady=5, fill="x")

        # ========== PANEL BAS : ENTRÉES ==========
        frame_entree = ctk.CTkFrame(frame_contenu, fg_color="#F5F5FF", border_width=2, border_color="#1976D2")
        frame_entree.pack(fill="both", expand=True, padx=0, pady=0)

        # En-tête Entrée (Titre + Magasin)
        frame_header_entree = ctk.CTkFrame(frame_entree, fg_color="transparent")
        frame_header_entree.pack(fill="x", padx=10, pady=10)
        
        titre_entree = ctk.CTkLabel(frame_header_entree, text="📥 ARTICLES REÇUS (Entrée)", 
                                   font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                                   text_color="#1976D2")
        titre_entree.pack(side="left", anchor="w")
        
        # Magasin Entrée (à droite)
        frame_mag_entree = ctk.CTkFrame(frame_header_entree, fg_color="transparent")
        frame_mag_entree.pack(side="right", fill="x", expand=False)
        ctk.CTkLabel(frame_mag_entree, text="Magasin:").pack(side="left", padx=5)
        self.combo_mag_entree = ctk.CTkComboBox(frame_mag_entree, width=200, state="readonly")
        self.combo_mag_entree.pack(side="left", padx=5)

        # Ligne de saisie (Article, Charger, Quantité, Unité, Ajouter, Annuler)
        frame_input_entree = ctk.CTkFrame(frame_entree, fg_color="transparent")
        frame_input_entree.pack(fill="x", padx=10, pady=5)

        self.entry_article_entree = ctk.CTkEntry(frame_input_entree, placeholder_text="Rechercher article...", width=200)
        self.entry_article_entree.pack(side="left", padx=3)

        btn_recherche_entree = ctk.CTkButton(frame_input_entree, text="🔍 Charger", 
                                            command=self.ouvrir_recherche_article_entree, width=100,
                                            fg_color="#1976d2", hover_color="#1565c0")
        btn_recherche_entree.pack(side="left", padx=3)

        self.entry_qty_entree = ctk.CTkEntry(frame_input_entree, placeholder_text="Quantité", width=60)
        self.entry_qty_entree.pack(side="left", padx=3)

        self.entry_unite_entree = ctk.CTkEntry(frame_input_entree, placeholder_text="Unité", width=60, state="readonly")
        self.entry_unite_entree.pack(side="left", padx=3)

        self.btn_ajouter_entree = ctk.CTkButton(frame_input_entree, text="➕ Ajouter", 
                                               command=self.ajouter_article_entree, width=90,
                                               fg_color="#2e7d32", hover_color="#1b5e20")
        self.btn_ajouter_entree.pack(side="left", padx=3)

        self.btn_annuler_entree = ctk.CTkButton(frame_input_entree, text="❌ Annuler", 
                                               command=self.annuler_entree, width=80,
                                               fg_color="#757575", hover_color="#616161")
        self.btn_annuler_entree.pack(side="left", padx=3)

        # Tableau Entrée
        frame_tree_entree = ctk.CTkFrame(frame_entree)
        frame_tree_entree.pack(fill="both", expand=True, padx=10, pady=10)
        frame_tree_entree.grid_rowconfigure(0, weight=1)
        frame_tree_entree.grid_columnconfigure(0, weight=1)

        colonnes_entree = ("Code", "Désignation", "Unité", "Magasin", "Quantité")
        self.tree_entree = ttk.Treeview(frame_tree_entree, columns=colonnes_entree, show="headings", height=2)

        for col in colonnes_entree:
            self.tree_entree.heading(col, text=col)
            if col == "Désignation":
                self.tree_entree.column(col, width=200)
            else:
                self.tree_entree.column(col, width=100)

        scrollbar_entree = ttk.Scrollbar(frame_tree_entree, orient="vertical", command=self.tree_entree.yview)
        self.tree_entree.configure(yscrollcommand=scrollbar_entree.set)

        self.tree_entree.pack(side="left", fill="both", expand=True)
        scrollbar_entree.pack(side="right", fill="y")

        # Bouton Supprimer Entrée
        btn_supprimer_entree = ctk.CTkButton(frame_entree, text="🗑️ Supprimer Ligne", 
                                            command=self.supprimer_article_entree,
                                            fg_color="#d32f2f", hover_color="#b71c1c", width=150)
        btn_supprimer_entree.pack(padx=10, pady=5, fill="x")

        # ============ FOOTER (COMMUN) ============
        frame_footer = ctk.CTkFrame(self, fg_color="transparent")
        frame_footer.pack(fill="x", padx=20, pady=10)

        btn_imprimer = ctk.CTkButton(frame_footer, text="🖨️ Imprimer", 
                                     command=self.imprimer_changement,
                                     fg_color="#ff6f00", hover_color="#e65100")
        btn_imprimer.pack(side="right", padx=10)

        btn_enregistrer = ctk.CTkButton(frame_footer, text="💾 Enregistrer", 
                                       command=self.enregistrer_changement,
                                       fg_color="#2e7d32", hover_color="#1b5e20")
        btn_enregistrer.pack(side="right", padx=10)

    def ouvrir_recherche_article_sortie(self):
        """Ouvre la fenêtre de recherche d'article pour SORTIE"""
        self._ouvrir_recherche_article("sortie")

    def ouvrir_recherche_article_entree(self):
        """Ouvre la fenêtre de recherche d'article pour ENTRÉE"""
        self._ouvrir_recherche_article("entree")

    def _ouvrir_recherche_article(self, type_mouvement):
        """Fenêtre générique de recherche d'article"""
        fenetre = ctk.CTkToplevel(self)
        fenetre.title("Rechercher un article")
        fenetre.geometry("900x500")
        fenetre.grab_set()

        main_frame = ctk.CTkFrame(fenetre)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        titre = ctk.CTkLabel(main_frame, text="Sélectionner un article", 
                            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"))
        titre.pack(pady=(0, 10))

        search_frame = ctk.CTkFrame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(search_frame, text="🔍 Rechercher:").pack(side="left", padx=5)
        entry_search = ctk.CTkEntry(search_frame, placeholder_text="Code ou désignation...", width=300)
        entry_search.pack(side="left", padx=5, fill="x", expand=True)

        tree_frame = ctk.CTkFrame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))

        colonnes = ("ID", "ID_Unite", "Code", "Désignation", "Unité")
        tree = ttk.Treeview(tree_frame, columns=colonnes, show='headings', height=15)

        for col in colonnes:
            tree.heading(col, text=col)
        
        tree.column("ID", width=0, stretch=False)
        tree.column("ID_Unite", width=0, stretch=False)
        tree.column("Code", width=150, anchor='w')
        tree.column("Désignation", width=500, anchor='w')
        tree.column("Unité", width=100, anchor='w')

        scrollbar = ctk.CTkScrollbar(tree_frame, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        label_count = ctk.CTkLabel(main_frame, text="Articles: 0")
        label_count.pack(pady=5)

        def charger_articles(filtre=""):
            for item in tree.get_children():
                tree.delete(item)
            conn = self.connect_db()
            if not conn:
                return
            try:
                cursor = conn.cursor()
                query = """
                    SELECT T2."idarticle", T1."idunite", T1."codearticle", T2."designation", T1."designationunite"
                    FROM tb_unite AS T1
                    INNER JOIN tb_article AS T2 ON T1.idarticle = T2.idarticle
                    WHERE T2."deleted" = 0
                """
                params = []
                if filtre:
                    query += """ AND (
                        LOWER(T1."codearticle") LIKE LOWER(%s) OR 
                        LOWER(T2."designation") LIKE LOWER(%s)
                    )"""
                    params = [f"%{filtre}%", f"%{filtre}%"]
                query += " ORDER BY T1.\"codearticle\""
                cursor.execute(query, params)
                resultats = cursor.fetchall()

                for row in resultats:
                    tree.insert('', 'end', values=(row[0], row[1], row[2], row[3], row[4]))

                label_count.configure(text=f"Articles: {len(resultats)}")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur: {str(e)}")
            finally:
                if 'cursor' in locals() and cursor:
                    cursor.close()
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

            values = tree.item(selection[0])['values']
            idarticle = values[0]
            idunite = values[1]
            codeart = values[2]
            designation = values[3]
            unite = values[4]

            if type_mouvement == "sortie":
                self.article_sortie_selectionne = {
                    'idarticle': idarticle,
                    'idunite': idunite,
                    'designation': designation,
                    'unite': unite,
                    'code': codeart
                }
                self.entry_article_sortie.delete(0, "end")
                self.entry_article_sortie.insert(0, designation)
                
                self.entry_unite_sortie.configure(state="normal")
                self.entry_unite_sortie.delete(0, "end")
                self.entry_unite_sortie.insert(0, unite)
                self.entry_unite_sortie.configure(state="readonly")
            else:
                self.article_entree_selectionne = {
                    'idarticle': idarticle,
                    'idunite': idunite,
                    'designation': designation,
                    'unite': unite,
                    'code': codeart
                }
                self.entry_article_entree.delete(0, "end")
                self.entry_article_entree.insert(0, designation)
                
                self.entry_unite_entree.configure(state="normal")
                self.entry_unite_entree.delete(0, "end")
                self.entry_unite_entree.insert(0, unite)
                self.entry_unite_entree.configure(state="readonly")

            fenetre.destroy()

        tree.bind('<Double-Button-1>', lambda e: valider_selection())

        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x")

        btn_annuler = ctk.CTkButton(btn_frame, text="❌ Annuler", command=fenetre.destroy, 
                                    fg_color="#d32f2f", hover_color="#b71c1c")
        btn_annuler.pack(side="left", padx=5, pady=5)

        btn_valider = ctk.CTkButton(btn_frame, text="✅ Valider", command=valider_selection, 
                                    fg_color="#2e7d32", hover_color="#1b5e20")
        btn_valider.pack(side="right", padx=5, pady=5)

        charger_articles()

    def ajouter_article_sortie(self):
        """Ajoute un article à la sortie"""
        if not self.article_sortie_selectionne:
            messagebox.showwarning("Attention", "Veuillez sélectionner un article")
            return

        try:
            qty = self.parser_nombre(self.entry_qty_sortie.get())
            if qty <= 0:
                messagebox.showwarning("Attention", "Quantité doit être > 0")
                return

            magasin = self.combo_mag_sortie.get()
            designation = self.article_sortie_selectionne['designation']
            unite = self.article_sortie_selectionne['unite']
            code = self.article_sortie_selectionne['code']

            self.tree_sortie.insert("", "end", values=(
                code, designation, unite, magasin, self.formater_nombre(qty)
            ))

            self.articles_sortie.append({
                'idarticle': self.article_sortie_selectionne['idarticle'],
                'idunite': self.article_sortie_selectionne['idunite'],
                'idmagasin': self.magasins[magasin],
                'designation': designation,
                'code': code,
                'unite': unite,
                'quantite': qty
            })

            self.annuler_sortie()
        except ValueError:
            messagebox.showerror("Erreur", "Quantité invalide")

    def ajouter_article_entree(self):
        """Ajoute un article à l'entrée"""
        if not self.article_entree_selectionne:
            messagebox.showwarning("Attention", "Veuillez sélectionner un article")
            return

        try:
            qty = self.parser_nombre(self.entry_qty_entree.get())
            if qty <= 0:
                messagebox.showwarning("Attention", "Quantité doit être > 0")
                return

            magasin = self.combo_mag_entree.get()
            designation = self.article_entree_selectionne['designation']
            unite = self.article_entree_selectionne['unite']
            code = self.article_entree_selectionne['code']

            self.tree_entree.insert("", "end", values=(
                code, designation, unite, magasin, self.formater_nombre(qty)
            ))

            self.articles_entree.append({
                'idarticle': self.article_entree_selectionne['idarticle'],
                'idunite': self.article_entree_selectionne['idunite'],
                'idmagasin': self.magasins[magasin],
                'designation': designation,
                'code': code,
                'unite': unite,
                'quantite': qty
            })

            self.annuler_entree()
        except ValueError:
            messagebox.showerror("Erreur", "Quantité invalide")

    def annuler_sortie(self):
        """Réinitialise les champs de sortie"""
        self.article_sortie_selectionne = None
        self.entry_article_sortie.delete(0, "end")
        self.entry_unite_sortie.configure(state="normal")
        self.entry_unite_sortie.delete(0, "end")
        self.entry_unite_sortie.configure(state="readonly")
        self.entry_qty_sortie.delete(0, "end")

    def annuler_entree(self):
        """Réinitialise les champs d'entrée"""
        self.article_entree_selectionne = None
        self.entry_article_entree.delete(0, "end")
        self.entry_unite_entree.configure(state="normal")
        self.entry_unite_entree.delete(0, "end")
        self.entry_unite_entree.configure(state="readonly")
        self.entry_qty_entree.delete(0, "end")

    def supprimer_article_sortie(self):
        """Supprime la ligne sélectionnée de la sortie"""
        selection = self.tree_sortie.selection()
        if not selection:
            messagebox.showwarning("Attention", "Sélectionnez une ligne")
            return

        index = self.tree_sortie.index(selection[0])
        self.tree_sortie.delete(selection[0])
        self.articles_sortie.pop(index)

    def supprimer_article_entree(self):
        """Supprime la ligne sélectionnée de l'entrée"""
        selection = self.tree_entree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Sélectionnez une ligne")
            return

        index = self.tree_entree.index(selection[0])
        self.tree_entree.delete(selection[0])
        self.articles_entree.pop(index)

    def ouvrir_recherche_changement(self):
        """Ouvre le dialogue pour charger un changement existant"""
        messagebox.showinfo("À venir", "Fonctionnalité de chargement à développer")

    def enregistrer_changement(self):
        """Enregistre le changement en base de données"""
        if not self.articles_sortie and not self.articles_entree:
            messagebox.showwarning("Attention", "Ajoutez au moins un article en sortie ou entrée")
            return

        messagebox.showinfo("Enregistrement", 
                          f"Sortie: {len(self.articles_sortie)} articles\nEntrée: {len(self.articles_entree)} articles\n\n"
                          "Enregistrement à développer")

    def imprimer_changement(self):
        """Imprime le changement"""
        if not self.articles_sortie and not self.articles_entree:
            messagebox.showwarning("Attention", "Aucun article à imprimer")
            return

        messagebox.showinfo("Impression", "Impression à développer")


class PasswordDialog(ctk.CTkToplevel):
    def __init__(self, title, text):
        super().__init__()
        self.title(title)
        self.geometry("300x150")
        self.result = None
        
        self.label = ctk.CTkLabel(self, text=text)
        self.label.pack(pady=10)
        
        # Le paramètre show="*" cache les caractères
        self.entry = ctk.CTkEntry(self, show="*")
        self.entry.pack(pady=5)
        self.entry.focus_set()
        
        self.btn = ctk.CTkButton(self, text="Valider", command=self.ok)
        self.btn.pack(pady=10)
        
        self.grab_set()  # Rend la fenêtre modale
        self.wait_window()

    def ok(self):
        self.result = self.entry.get()
        self.destroy()


class PageInfoMouvementStock(ctk.CTkFrame):
    """Frame principal avec navigation - Pour intégration dans app_main"""
    def __init__(self, parent, iduser, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.iduser = iduser  # ID de l'utilisateur connecté
        
        # Configuration du thème
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        
        # Connexion à la base de données
        self.db_connection = self.connect_db()
        
        if not self.db_connection:
            messagebox.showwarning("Avertissement", "L'application démarre sans connexion à la base de données.")
        
        # Container principal - Configuration de la grille
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # Création des composants
        self.create_sidebar()
        self.create_content_area()
        
        # Dictionnaire des pages
        self.pages = {}
        self.current_page = None
        
        # Afficher la première page par défaut
        self.show_page("Mise à jour BC")
    
    def connect_db(self):
        """Connexion à la base de données PostgreSQL"""
        try:
            # Assurez-vous que 'config.json' existe et est accessible
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
        
    def create_sidebar(self):
        """Créer le menu latéral"""
        self.sidebar = ctk.CTkFrame(self, width=150, corner_radius=0, fg_color="#3b82f6")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(5, weight=1)
        self.sidebar.grid_propagate(False)  # Empêcher le redimensionnement
        
        # Titre du menu
        title = ctk.CTkLabel(
            self.sidebar,
            text="Mise à jour",
            font=("Arial", 20, "bold"),
            text_color="white"
        )
        title.grid(row=0, column=0, padx=20, pady=30)
        
        # Boutons du menu
        self.menu_buttons = {}
        menus = [
            ("Mise à jour BC", "PageCommandeFrs"),
            ("Mise à jour BR", "PageBonReception"),
            ("Mise à jour Transfert", "PageTransfert"),
            ("Mise à jour Sortie", "PageSortie"),
            ("Suivi Commande", "PageSuiviCommande"),
            ("Changement d'Articles", "PageChangementArticle")
        ]
        
        for idx, (menu_name, page_class) in enumerate(menus, start=1):
            btn = ctk.CTkButton(
                self.sidebar,
                text=menu_name,
                font=("Arial", 13),
                fg_color="transparent",
                hover_color="#2563eb",
                anchor="w",
                height=40,
                command=lambda m=menu_name: self.show_page(m)
            )
            btn.grid(row=idx, column=0, padx=10, pady=5, sticky="ew")
            self.menu_buttons[menu_name] = btn
    
    def create_content_area(self):
        """Créer la zone de contenu principal"""
        self.content_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#f8fafc")
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        
        # Message initial
        self.initial_label = ctk.CTkLabel(
            self.content_frame,
            text="⚙️ Prêt à travailler\n\nSélectionnez une option dans le menu",
            font=("Arial", 18),
            text_color="#94a3b8"
        )
        self.initial_label.place(relx=0.5, rely=0.5, anchor="center")
        
    def verifier_code_autorisation(self, code_saisi):
        """Vérifie si le code existe dans la table tb_codeautorisation"""
        if not self.db_connection:
            return False
        try:
            cursor = self.db_connection.cursor()
            query = "SELECT 1 FROM tb_codeautorisation WHERE code = %s"
            cursor.execute(query, (code_saisi,))
            result = cursor.fetchone()
            cursor.close()
            return result is not None
        except Exception as e:
            print(f"Erreur vérification code: {e}")
            return False
    
    def show_page(self, menu_name):
        """Afficher la page correspondant au menu sélectionné"""
        
        if menu_name == "Mise à jour Sortie":
            # Utilisation du dialogue personnalisé avec mot de passe caché
            dialog = PasswordDialog("Accès Sécurisé", "Entrez le code d'autorisation :")
            code = dialog.result
        
            if code:
                if not self.verifier_code_autorisation(code):
                    messagebox.showerror("Accès Refusé", "Code d'autorisation invalide.")
                    return
            else:
                return # Annulation ou champ vide
        
        # Cacher le label initial
        if self.initial_label:
            self.initial_label.place_forget()
            self.initial_label = None
        
        # Mapping menu -> classe de page (IMPORTÉES)
        page_mapping = {
            "Mise à jour BC": PageCommandeFrs,
            "Mise à jour BR": PageBonReception,
            "Mise à jour Transfert": PageTransfert,
            "Mise à jour Sortie": PageSortie,
            "Suivi Commande" : PageSuiviCommande,
            "Changement d'Articles": PageChangementArticle
        }
        
        # Cacher la page actuelle
        if self.current_page:
            self.current_page.pack_forget()
        
        # Créer ou afficher la page demandée
        if menu_name not in self.pages:
            page_class = page_mapping[menu_name]
            
            # IMPORTANT : Passer le bon paramètre selon la classe
            try:
                if page_class == PageCommandeFrs:
                    self.pages[menu_name] = page_class(self.content_frame, self.iduser)
                elif page_class == PageBonReception:
                    self.pages[menu_name] = page_class(self.content_frame, self.iduser)
                elif page_class == PageTransfert:
                    self.pages[menu_name] = page_class(self.content_frame, self.iduser)
                elif page_class == PageSortie:
                    self.pages[menu_name] = page_class(self.content_frame, self.iduser)
                elif page_class == PageSuiviCommande:
                    self.pages[menu_name] = page_class(self.content_frame) # Pas d'iduser ici
                elif page_class == PageChangementArticle:
                    self.pages[menu_name] = page_class(self.content_frame, self.iduser)
                else:
                    self.pages[menu_name] = page_class(self.content_frame, self.iduser)
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors du chargement de la page {menu_name}:\n{str(e)}")
                return
        
        self.current_page = self.pages[menu_name]
        self.current_page.pack(fill="both", expand=True)
        
        # Forcer la mise à jour de l'affichage
        self.content_frame.update_idletasks()
        
        # Mettre à jour l'apparence des boutons
        for btn_name, btn in self.menu_buttons.items():
            if btn_name == menu_name:
                btn.configure(fg_color="#2563eb")
            else:
                btn.configure(fg_color="transparent")


# Test standalone si lancé directement
if __name__ == "__main__":
    # ID utilisateur (à récupérer depuis votre système d'authentification)
    iduser = 1
    
    # Créer une fenêtre de test
    app = ctk.CTk()
    app.title("Test - Mise à jour")
    app.geometry("1400x800")
    
    # Créer et afficher le frame
    page = PageInfoMouvementStock(app, iduser)
    page.pack(fill="both", expand=True)
    
    app.mainloop()
