import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import json
from datetime import datetime

from resource_utils import get_config_path


class PageChangementArticle(ctk.CTkFrame):
    """
    CLASSE POUR GESTION DES CHANGEMENTS D'ARTICLES.
    Permet les sorties et entrées d'articles avec interface à deux colonnes.
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
        except Exception:
            return "0,00"

    def parser_nombre(self, texte):
        """Convertit un nombre formaté (1.000,00) en float"""
        try:
            texte_clean = str(texte).replace('.', '').replace(',', '.')
            return float(texte_clean)
        except Exception:
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
        """Construit l'interface utilisateur"""
        # ============ EN-TÊTE ============
        frame_entete = ctk.CTkFrame(self)
        frame_entete.pack(fill="x", padx=20, pady=10)

        # Titre
        titre = ctk.CTkLabel(frame_entete, text="Changement d'Articles",
                             font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"))
        titre.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="w")

        # Référence
        ctk.CTkLabel(frame_entete, text="Référence:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.entry_ref = ctk.CTkEntry(frame_entete, width=200, state="readonly")
        self.entry_ref.grid(row=1, column=1, padx=10, pady=5)

        # Date
        ctk.CTkLabel(frame_entete, text="Date:").grid(row=1, column=2, padx=10, pady=5, sticky="w")
        self.entry_date = ctk.CTkEntry(frame_entete, width=150, state="readonly")
        self.entry_date.configure(state="normal")
        self.entry_date.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.entry_date.configure(state="readonly")
        self.entry_date.grid(row=1, column=3, padx=10, pady=5)

        # Bouton Charger Changement
        btn_charger = ctk.CTkButton(frame_entete, text="📂 Charger",
                                    command=self.ouvrir_recherche_changement, width=140,
                                    fg_color="#1976d2", hover_color="#1565c0")
        btn_charger.grid(row=1, column=4, padx=10, pady=5)

        # ============ CORPS PRINCIPAL (DEUX COLONNES) ============
        frame_contenu = ctk.CTkFrame(self, fg_color="transparent")
        frame_contenu.pack(fill="both", expand=True, padx=20, pady=10)
        frame_contenu.grid_columnconfigure((0, 1), weight=1)

        # ========== COLONNE GAUCHE : SORTIES ==========
        frame_sortie = ctk.CTkFrame(frame_contenu, fg_color="#FFF5F5", border_width=2, border_color="#D32F2F")
        frame_sortie.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        frame_sortie.grid_rowconfigure(3, weight=1)

        # Titre Sortie
        titre_sortie = ctk.CTkLabel(frame_sortie, text="📤 ARTICLES À CHANGER (Sortie)",
                                    font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                                    text_color="#D32F2F")
        titre_sortie.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="w")

        # Sélecteur Magasin Sortie
        ctk.CTkLabel(frame_sortie, text="Magasin Sortie:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.combo_mag_sortie = ctk.CTkComboBox(frame_sortie, width=250, state="readonly")
        self.combo_mag_sortie.grid(row=1, column=1, columnspan=2, padx=10, pady=5, sticky="w")

        # Recherche Article Sortie
        ctk.CTkLabel(frame_sortie, text="Article:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.entry_article_sortie = ctk.CTkEntry(frame_sortie, width=250, state="readonly")
        self.entry_article_sortie.grid(row=2, column=1, padx=10, pady=5)

        btn_recherche_sortie = ctk.CTkButton(frame_sortie, text="🔍",
                                            command=self.ouvrir_recherche_article_sortie, width=40)
        btn_recherche_sortie.grid(row=2, column=2, padx=5, pady=5)

        # Quantité et Unité Sortie
        ctk.CTkLabel(frame_sortie, text="Quantité:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.entry_qty_sortie = ctk.CTkEntry(frame_sortie, width=100)
        self.entry_qty_sortie.grid(row=3, column=1, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(frame_sortie, text="Unité:").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.entry_unite_sortie = ctk.CTkEntry(frame_sortie, width=250, state="readonly")
        self.entry_unite_sortie.grid(row=4, column=1, columnspan=2, padx=10, pady=5)

        # Boutons Sortie
        frame_btn_sortie = ctk.CTkFrame(frame_sortie, fg_color="transparent")
        frame_btn_sortie.grid(row=5, column=0, columnspan=3, padx=10, pady=10, sticky="w")

        self.btn_ajouter_sortie = ctk.CTkButton(frame_btn_sortie, text="➕ Ajouter",
                                               command=self.ajouter_article_sortie, width=110)
        self.btn_ajouter_sortie.pack(side="left", padx=5)

        self.btn_annuler_sortie = ctk.CTkButton(frame_btn_sortie, text="❌ Annuler",
                                               command=self.annuler_sortie, width=100,
                                               fg_color="#757575", hover_color="#616161")
        self.btn_annuler_sortie.pack(side="left", padx=5)

        # Tableau Sortie
        frame_tree_sortie = ctk.CTkFrame(frame_sortie)
        frame_tree_sortie.grid(row=6, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)
        frame_tree_sortie.grid_rowconfigure(0, weight=1)
        frame_tree_sortie.grid_columnconfigure(0, weight=1)

        colonnes_sortie = ("Code", "Désignation", "Unité", "Magasin", "Quantité")
        self.tree_sortie = ttk.Treeview(frame_tree_sortie, columns=colonnes_sortie, show="headings", height=6)

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
        self.tree_sortie.tag_configure("even", background="#FFFFFF", foreground="#000000")
        self.tree_sortie.tag_configure("odd", background="#E6EFF8", foreground="#000000")

        # Bouton Supprimer Sortie
        btn_supprimer_sortie = ctk.CTkButton(frame_sortie, text="🗑️ Supprimer Ligne",
                                            command=self.supprimer_article_sortie,
                                            fg_color="#d32f2f", hover_color="#b71c1c", width=200)
        btn_supprimer_sortie.grid(row=7, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

        # ========== COLONNE DROITE : ENTRÉES ==========
        frame_entree = ctk.CTkFrame(frame_contenu, fg_color="#F5F5FF", border_width=2, border_color="#1976D2")
        frame_entree.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        frame_entree.grid_rowconfigure(3, weight=1)

        # Titre Entrée
        titre_entree = ctk.CTkLabel(frame_entree, text="📥 ARTICLES REÇUS (Entrée)",
                                   font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                                   text_color="#1976D2")
        titre_entree.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="w")

        # Sélecteur Magasin Entrée
        ctk.CTkLabel(frame_entree, text="Magasin Entrée:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.combo_mag_entree = ctk.CTkComboBox(frame_entree, width=250, state="readonly")
        self.combo_mag_entree.grid(row=1, column=1, columnspan=2, padx=10, pady=5, sticky="w")

        # Recherche Article Entrée
        ctk.CTkLabel(frame_entree, text="Article:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.entry_article_entree = ctk.CTkEntry(frame_entree, width=250, state="readonly")
        self.entry_article_entree.grid(row=2, column=1, padx=10, pady=5)

        btn_recherche_entree = ctk.CTkButton(frame_entree, text="🔍",
                                            command=self.ouvrir_recherche_article_entree, width=40)
        btn_recherche_entree.grid(row=2, column=2, padx=5, pady=5)

        # Quantité et Unité Entrée
        ctk.CTkLabel(frame_entree, text="Quantité:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.entry_qty_entree = ctk.CTkEntry(frame_entree, width=100)
        self.entry_qty_entree.grid(row=3, column=1, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(frame_entree, text="Unité:").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.entry_unite_entree = ctk.CTkEntry(frame_entree, width=250, state="readonly")
        self.entry_unite_entree.grid(row=4, column=1, columnspan=2, padx=10, pady=5)

        # Boutons Entrée
        frame_btn_entree = ctk.CTkFrame(frame_entree, fg_color="transparent")
        frame_btn_entree.grid(row=5, column=0, columnspan=3, padx=10, pady=10, sticky="w")

        self.btn_ajouter_entree = ctk.CTkButton(frame_btn_entree, text="➕ Ajouter",
                                               command=self.ajouter_article_entree, width=110,
                                               fg_color="#2e7d32", hover_color="#1b5e20")
        self.btn_ajouter_entree.pack(side="left", padx=5)

        self.btn_annuler_entree = ctk.CTkButton(frame_btn_entree, text="❌ Annuler",
                                               command=self.annuler_entree, width=100,
                                               fg_color="#757575", hover_color="#616161")
        self.btn_annuler_entree.pack(side="left", padx=5)

        # Tableau Entrée
        frame_tree_entree = ctk.CTkFrame(frame_entree)
        frame_tree_entree.grid(row=6, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)
        frame_tree_entree.grid_rowconfigure(0, weight=1)
        frame_tree_entree.grid_columnconfigure(0, weight=1)

        colonnes_entree = ("Code", "Désignation", "Unité", "Magasin", "Quantité")
        self.tree_entree = ttk.Treeview(frame_tree_entree, columns=colonnes_entree, show="headings", height=6)

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
        self.tree_entree.tag_configure("even", background="#FFFFFF", foreground="#000000")
        self.tree_entree.tag_configure("odd", background="#E6EFF8", foreground="#000000")

        # Bouton Supprimer Entrée
        btn_supprimer_entree = ctk.CTkButton(frame_entree, text="🗑️ Supprimer Ligne",
                                            command=self.supprimer_article_entree,
                                            fg_color="#d32f2f", hover_color="#b71c1c", width=200)
        btn_supprimer_entree.grid(row=7, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

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
        tree.tag_configure("even", background="#FFFFFF", foreground="#000000")
        tree.tag_configure("odd", background="#E6EFF8", foreground="#000000")

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

                for idx, row in enumerate(resultats):
                    tag = "even" if idx % 2 == 0 else "odd"
                    tree.insert('', 'end', values=(row[0], row[1], row[2], row[3], row[4]), tags=(tag,))

                label_count.configure(text=f"Articles: {len(resultats)}")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur: {str(e)}")
            finally:
                if 'cursor' in locals() and cursor:
                    cursor.close()
                if conn:
                    conn.close()

        def rechercher(*_args):
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
                self.entry_article_sortie.configure(state="normal")
                self.entry_article_sortie.delete(0, "end")
                self.entry_article_sortie.insert(0, designation)
                self.entry_article_sortie.configure(state="readonly")

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
                self.entry_article_entree.configure(state="normal")
                self.entry_article_entree.delete(0, "end")
                self.entry_article_entree.insert(0, designation)
                self.entry_article_entree.configure(state="readonly")

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

            tag = "even" if len(self.tree_sortie.get_children()) % 2 == 0 else "odd"
            self.tree_sortie.insert("", "end", values=(
                code, designation, unite, magasin, self.formater_nombre(qty)
            ), tags=(tag,))

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

            tag = "even" if len(self.tree_entree.get_children()) % 2 == 0 else "odd"
            self.tree_entree.insert("", "end", values=(
                code, designation, unite, magasin, self.formater_nombre(qty)
            ), tags=(tag,))

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
        self.entry_article_sortie.configure(state="normal")
        self.entry_article_sortie.delete(0, "end")
        self.entry_article_sortie.configure(state="readonly")
        self.entry_unite_sortie.configure(state="normal")
        self.entry_unite_sortie.delete(0, "end")
        self.entry_unite_sortie.configure(state="readonly")
        self.entry_qty_sortie.delete(0, "end")

    def annuler_entree(self):
        """Réinitialise les champs d'entrée"""
        self.article_entree_selectionne = None
        self.entry_article_entree.configure(state="normal")
        self.entry_article_entree.delete(0, "end")
        self.entry_article_entree.configure(state="readonly")
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

        messagebox.showinfo(
            "Enregistrement",
            f"Sortie: {len(self.articles_sortie)} articles\nEntrée: {len(self.articles_entree)} articles\n\n"
            "Enregistrement à développer"
        )

    def imprimer_changement(self):
        """Imprime le changement"""
        if not self.articles_sortie and not self.articles_entree:
            messagebox.showwarning("Attention", "Aucun article à imprimer")
            return

        messagebox.showinfo("Impression", "Impression à développer")

