import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import json
from datetime import datetime
from html import escape
from html import escape # Décommenter si vous utilisez l'impression HTML
from datetime import datetime # Décommenter si vous utilisez les dates DB
import tempfile # NOUVEAU : Nécessaire pour l'aperçu avant impression
import webbrowser # NOUVEAU : Nécessaire pour l'aperçu avant impression
import os # NOUVEAU : Nécessaire pour l'aperçu avant impression
from reportlab.lib.pagesizes import A5, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from resource_utils import get_config_path, safe_file_read



from pages.page_livrFrs import PageBonReception  # Ajoutez cette ligne
         

# Configuration de l'apparence
ctk.set_appearance_mode("light") 
ctk.set_default_color_theme("blue")

# Définition des couleurs utilisées
NAV_BAR_COLOR = "#007ACC"
ACTIVE_BUTTON_COLOR = "white"
INACTIVE_BUTTON_COLOR = NAV_BAR_COLOR
ACTIVE_TEXT_COLOR = "black"
INACTIVE_TEXT_COLOR = "white"


# --- 1. Votre classe PageCommandeFrs (PageCmdFrs) avec correction ---

class PageCmdFrs(ctk.CTkFrame):
    """
    CLASSE INTÉGRÉE. Correction de l'argument __init__ de 'parent' à 'master'.
    """
    # CORRECTION ICI: Changement de 'parent' à 'master'
    def __init__(self, master, iduser): 
        super().__init__(master, fg_color="white") 
        self.iduser = iduser
        self.article_selectionne = None
        self.items_commande = []
        self.idcom_charge = None
        self.mode_modification = False
        self.index_ligne_selectionnee = None
        self.fournisseurs = {"HTA": 1, "Autre": 2} # STUB: Fournisseurs en dur
        
        self.setup_ui()
        self.generer_reference()
        self.charger_fournisseurs() 

    # --- STUBS ET FONCTIONS UTILITAIRES ---
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
            # Formater avec 2 décimales
            partie_entiere = int(nombre)
            partie_decimale = abs(nombre - partie_entiere)
            
            # Formater la partie entière avec des points comme séparateurs de milliers
            str_entiere = f"{partie_entiere:,}".replace(',', '.')
            
            # Formater la partie décimale
            str_decimale = f"{partie_decimale:.2f}".split('.')[1]
            
            return f"{str_entiere},{str_decimale}"
        except:
            return "0,00"
    
    def parser_nombre(self, texte):
        """Convertit un nombre formaté (1.000,00) en float"""
        try:
            # Enlever les points (séparateurs de milliers) et remplacer la virgule par un point
            texte_clean = texte.replace('.', '').replace(',', '.')
            return float(texte_clean)
        except:
            return 0.0
            
    def generer_reference(self):
        """Génère la référence automatique au format 2025-BC-00001"""
        conn = self.connect_db()
        if not conn:
            return
            
        try:
            cursor = conn.cursor()
            annee_courante = datetime.now().year
            
            query = """
                SELECT refcom FROM tb_commande 
                WHERE refcom LIKE %s 
                ORDER BY refcom DESC LIMIT 1
            """
            cursor.execute(query, (f"{annee_courante}-BC-%",))
            resultat = cursor.fetchone()
            
            if resultat:
                # Extraire le numéro après "BC-"
                dernier_num = int(resultat[0].split('-')[-1])
                nouveau_num = dernier_num + 1
            else:
                nouveau_num = 1
            
            reference = f"{annee_courante}-BC-{nouveau_num:05d}"
            self.entry_ref.configure(state="normal")
            self.entry_ref.delete(0, "end")
            self.entry_ref.insert(0, reference)
            self.entry_ref.configure(state="readonly")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la génération de la référence: {str(e)}")
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()
    
    def charger_fournisseurs(self):
        """Charge la liste des fournisseurs"""
        conn = self.connect_db()
        if not conn:
            return
            
        try:
            cursor = conn.cursor()
            query = "SELECT idfrs, nomfrs FROM tb_fournisseur WHERE deleted = 0 ORDER BY nomfrs"
            cursor.execute(query)
            
            self.fournisseurs = {row[1]: row[0] for row in cursor.fetchall()}
            self.combo_fournisseur.configure(values=list(self.fournisseurs.keys()))
            
            if self.fournisseurs:
                self.combo_fournisseur.set(list(self.fournisseurs.keys())[0])
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des fournisseurs: {str(e)}")
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()
            
    def ouvrir_recherche_article(self):
        """Ouvre une fenêtre pour rechercher et sélectionner un article"""
        if self.index_ligne_selectionnee is not None:
            messagebox.showwarning("Attention", "Veuillez d'abord valider ou annuler la modification de ligne en cours")
            return
            
        fenetre_recherche = ctk.CTkToplevel(self)
        fenetre_recherche.title("Rechercher un article")
        fenetre_recherche.geometry("1000x600")
        fenetre_recherche.grab_set()
        
        main_frame = ctk.CTkFrame(fenetre_recherche)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        titre = ctk.CTkLabel(main_frame, text="Sélectionner un article", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"))
        titre.pack(pady=(0, 10))
        
        search_frame = ctk.CTkFrame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(search_frame, text="🔍 Rechercher:").pack(side="left", padx=5)
        entry_search = ctk.CTkEntry(search_frame, placeholder_text="Code ou désignation...", width=300)
        entry_search.pack(side="left", padx=5, fill="x", expand=True)
        
        tree_frame = ctk.CTkFrame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # COLONNES MODIFIÉES : Ajout de ID_Unite (caché) pour corriger le problème d'idunite
        colonnes = ("ID_Article", "ID_Unite", "Code", "Désignation", "Unité") 
        tree = ttk.Treeview(tree_frame, columns=colonnes, show='headings', height=15)
        
        tree.heading("ID_Article", text="ID_Article") 
        tree.heading("ID_Unite", text="ID_Unite")     
        tree.heading("Code", text="Code")
        tree.heading("Désignation", text="Désignation")
        tree.heading("Unité", text="Unité")
        
        tree.column("ID_Article", width=0, stretch=False) # Caché
        tree.column("ID_Unite", width=0, stretch=False)     # Caché (NOUVEAU)
        tree.column("Code", width=150, anchor='w')
        tree.column("Désignation", width=500, anchor='w')
        tree.column("Unité", width=100, anchor='w')
        
        scrollbar = ctk.CTkScrollbar(tree_frame, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        tree.tag_configure("even", background="#FFFFFF", foreground="#000000")
        tree.tag_configure("odd", background="#E6EFF8", foreground="#000000")
        
        label_count = ctk.CTkLabel(main_frame, text="Nombre d'articles : 0")
        label_count.pack(pady=5)
        
        def charger_articles(filtre=""):
            for item in tree.get_children():
                tree.delete(item)
            conn = self.connect_db()
            if not conn: return
            try:
                cursor = conn.cursor()
                # La requête retourne l'article et son unité de base/de commande
                query = """
                    SELECT T2."idarticle", T1."codearticle", T2."designation", T1."designationunite", T1."idunite"
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
                    if len(row) >= 5:
                        # row: [idarticle, codearticle, designation, designationunite, idunite]
                        # Insertion de 5 valeurs: ID_Article, ID_Unite, Code, Désignation, Unité
                        tag = "even" if idx % 2 == 0 else "odd"
                        tree.insert('', 'end', values=(row[0], row[4], row[1], row[2], row[3]), tags=(tag,)) # Remplir la colonne ID_Unite avec row[4]
                
                label_count.configure(text=f"Nombre d'articles : {len(resultats)}")
                
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors du chargement des articles: {str(e)}")
            finally:
                if 'cursor' in locals() and cursor: cursor.close()
                if conn: conn.close()
        
        def rechercher(*args):
            charger_articles(entry_search.get())
            
        entry_search.bind('<KeyRelease>', rechercher)
        
        def valider_selection():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Attention", "Veuillez sélectionner un article")
                return
            
            values = tree.item(selection[0])['values']
            
            # Récupération des données selon l'ordre des colonnes Treeview (y compris les cachées)
            idarticle = values[0]
            idunite = values[1] # ID DE L'UNITÉ (CORRIGÉ)
            codeart = values[2]
            designation = values[3]
            unite = values[4]
            
            self.article_selectionne = {
                'idarticle': idarticle,
                'idunite': idunite, # L'IDUNITE CORRECT EST MAINTENANT CAPTURÉ
                'designation': designation,
                'unite': unite
            }
            
            # Mettre à jour les champs
            self.entry_article.configure(state="normal")
            self.entry_article.delete(0, "end")
            self.entry_article.insert(0, designation)
            self.entry_article.configure(state="readonly")
            
            self.entry_unite.configure(state="normal")
            self.entry_unite.delete(0, "end")
            self.entry_unite.insert(0, unite)
            self.entry_unite.configure(state="readonly")
            
            self.entry_qtcmd.delete(0, "end")
            self.entry_punitcmd.delete(0, "end")
            
            # Réinitialiser/Afficher le total de la ligne pour les nouveaux champs vides
            self.calculer_total_ligne_preview()
            
            fenetre_recherche.destroy()
        
        tree.bind('<Double-Button-1>', lambda e: valider_selection())
        
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x")
        
        btn_annuler = ctk.CTkButton(btn_frame, text="❌ Annuler", command=fenetre_recherche.destroy, fg_color="#d32f2f", hover_color="#b71c1c")
        btn_annuler.pack(side="left", padx=5, pady=5)
        
        btn_valider = ctk.CTkButton(btn_frame, text="✅ Valider", command=valider_selection, fg_color="#2e7d32", hover_color="#1b5e20")
        btn_valider.pack(side="right", padx=5, pady=5)
        
        charger_articles()
        
    def nombre_en_lettres(self, nombre):
        """Convertit un nombre en lettres (pour le montant)"""
        unites = ["", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf"]
        dizaines = ["", "dix", "vingt", "trente", "quarante", "cinquante", "soixante", "soixante-dix", "quatre-vingt", "quatre-vingt-dix"]
        
        def convert_moins_100(n):
            if n < 10:
                return unites[n]
            elif n < 20:
                specials = ["dix", "onze", "douze", "treize", "quatorze", "quinze", "seize", "dix-sept", "dix-huit", "dix-neuf"]
                return specials[n - 10]
            elif n < 70:
                unite = n % 10
                dizaine = n // 10
                if unite == 0:
                    return dizaines[dizaine]
                elif unite == 1 and dizaine != 8:
                    return dizaines[dizaine] + "-et-un"
                else:
                    return dizaines[dizaine] + "-" + unites[unite]
            elif n < 80:
                return "soixante-" + convert_moins_100(n - 60)
            elif n < 100:
                if n == 80:
                    return "quatre-vingts"
                return "quatre-vingt-" + convert_moins_100(n - 80)
            return ""
        
        def convert_moins_1000(n):
            if n < 100:
                return convert_moins_100(n)
            centaine = n // 100
            reste = n % 100
            if centaine == 1:
                result = "cent"
            else:
                result = unites[centaine] + " cent"
            if reste == 0:
                if centaine > 1:
                    result += "s"
            else:
                result += " " + convert_moins_100(reste)
            return result
        
        try:
            nombre = float(nombre)
            partie_entiere = int(nombre)
            partie_decimale = int(round((nombre - partie_entiere) * 100))
            
            if partie_entiere == 0:
                result = "zéro"
            else:
                result = ""
                
                # Millions
                if partie_entiere >= 1000000:
                    millions = partie_entiere // 1000000
                    if millions == 1:
                        result += "un million "
                    else:
                        result += convert_moins_1000(millions) + " millions "
                    partie_entiere %= 1000000
                
                # Milliers
                if partie_entiere >= 1000:
                    milliers = partie_entiere // 1000
                    if milliers == 1:
                        result += "mille "
                    else:
                        result += convert_moins_1000(milliers) + " mille "
                    partie_entiere %= 1000
                
                # Centaines
                if partie_entiere > 0:
                    result += convert_moins_1000(partie_entiere)
            
            result = result.strip()
            
            # Ajouter la devise
            result += " Ariary"
            
            # Ajouter les centimes si nécessaire
            if partie_decimale > 0:
                result += " et " + convert_moins_100(partie_decimale) + " centimes"
            
            return result.capitalize()
        except:
            return "Zéro Ariary"


    # --- SETUP UI ---
    def setup_ui(self):
        # Titre
        self.titre = ctk.CTkLabel(self, text="Nouvelle Commande Fournisseur", 
                            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"))
        self.titre.pack(pady=10)
        
        # Frame en haut pour référence, fournisseur ET TOTAL GLOBAL
        frame_haut = ctk.CTkFrame(self)
        frame_haut.pack(fill="x", padx=20, pady=10)
        
        # Référence
        ctk.CTkLabel(frame_haut, text="Référence:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.entry_ref = ctk.CTkEntry(frame_haut, width=200, state="readonly")
        self.entry_ref.grid(row=0, column=1, padx=10, pady=10)
        
        # Fournisseur
        ctk.CTkLabel(frame_haut, text="Fournisseur:").grid(row=0, column=2, padx=10, pady=10, sticky="w")
        self.combo_fournisseur = ctk.CTkComboBox(frame_haut, width=300, state="readonly")
        self.combo_fournisseur.grid(row=0, column=3, padx=10, pady=10)
        
        # Bouton Charger Commande (pour la modification)
        btn_charger = ctk.CTkButton(frame_haut, text="📂 Charger Commande", 
                                    command=self.ouvrir_recherche_commande, width=150,
                                    fg_color="#1976d2", hover_color="#1565c0")
        btn_charger.grid(row=0, column=4, padx=10, pady=10)
        
        # LABEL TOTAL GLOBAL DE COMMANDE (NOUVEAU)
        self.label_total_global = ctk.CTkLabel(frame_haut, text="Total Commande: 0,00", 
                                       font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                                       text_color="#2e7d32")
        self.label_total_global.grid(row=0, column=5, padx=20, pady=10, sticky="e")
        
        # Configurer la colonne 5 pour prendre l'espace restant
        frame_haut.grid_columnconfigure(5, weight=1)
        
        # Frame milieu pour saisie des articles
        frame_milieu = ctk.CTkFrame(self)
        frame_milieu.pack(fill="x", padx=20, pady=10)
        
        # Nom d'article avec bouton recherche
        ctk.CTkLabel(frame_milieu, text="Nom d'article:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.entry_article = ctk.CTkEntry(frame_milieu, width=300, state="readonly")
        self.entry_article.grid(row=0, column=1, padx=10, pady=10)
        
        btn_recherche = ctk.CTkButton(frame_milieu, text="🔍 Rechercher", 
                                      command=self.ouvrir_recherche_article, width=120)
        btn_recherche.grid(row=0, column=2, padx=10, pady=10)
        
        # Unité
        ctk.CTkLabel(frame_milieu, text="Unité:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.entry_unite = ctk.CTkEntry(frame_milieu, width=150, state="readonly")
        self.entry_unite.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        
        # Quantité Cmd
        ctk.CTkLabel(frame_milieu, text="Quantité Cmd:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.entry_qtcmd = ctk.CTkEntry(frame_milieu, width=150)
        self.entry_qtcmd.grid(row=2, column=1, padx=10, pady=10, sticky="w")
        self.entry_qtcmd.bind('<KeyRelease>', lambda event: self.calculer_total_ligne_preview()) # Bind pour le calcul
        
        # Prix Unitaire
        ctk.CTkLabel(frame_milieu, text="Prix Unitaire:").grid(row=2, column=2, padx=10, pady=10, sticky="w")
        self.entry_punitcmd = ctk.CTkEntry(frame_milieu, width=150)
        self.entry_punitcmd.grid(row=2, column=3, padx=10, pady=10, sticky="w")
        self.entry_punitcmd.bind('<KeyRelease>', lambda event: self.calculer_total_ligne_preview()) # Bind pour le calcul
        
        # Label Total Ligne (NOUVEAU)
        self.label_total_ligne = ctk.CTkLabel(frame_milieu, text="Total Ligne: 0,00",
                                              font=ctk.CTkFont(family="Segoe UI", weight="bold"))
        self.label_total_ligne.grid(row=2, column=4, padx=20, pady=10, sticky="w")
        
        # Quantité Livrée
        ctk.CTkLabel(frame_milieu, text="Quantité Livrée:").grid(row=3, column=0, padx=10, pady=10, sticky="w")
        self.entry_qtlivre = ctk.CTkEntry(frame_milieu, width=150)
        self.entry_qtlivre.insert(0, "0")
        self.entry_qtlivre.grid(row=3, column=1, padx=10, pady=10, sticky="w")
        
        # Frame pour les boutons Ajouter et Modifier Ligne
        frame_btn_article = ctk.CTkFrame(frame_milieu, fg_color="transparent")
        frame_btn_article.grid(row=3, column=2, columnspan=3, padx=10, pady=10, sticky="w")
        
        # Bouton Ajouter
        self.btn_ajouter = ctk.CTkButton(frame_btn_article, text="➕ Ajouter", 
                                    command=self.ajouter_article, width=120)
        self.btn_ajouter.pack(side="left", padx=5)
        
        # Bouton Modifier Ligne
        self.btn_modifier_ligne = ctk.CTkButton(frame_btn_article, text="✏️ Modifier Ligne", 
                                    command=self.modifier_ligne_article, width=130,
                                    fg_color="#f9a825", hover_color="#f57f17",
                                    state="disabled")
        self.btn_modifier_ligne.pack(side="left", padx=5)
        
        # Bouton Annuler Sélection
        self.btn_annuler_selection = ctk.CTkButton(frame_btn_article, text="✖ Annuler", 
                                    command=self.annuler_selection_ligne, width=100,
                                    fg_color="#757575", hover_color="#616161",
                                    state="disabled")
        self.btn_annuler_selection.pack(side="left", padx=5)
        
        # Frame pour le Treeview
        frame_tree = ctk.CTkFrame(self)
        frame_tree.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Treeview
        colonnes = ("Article", "Unité", "Qté Cmd", "Prix Unit.", "Qté Livrée", "Total")
        self.tree = ttk.Treeview(frame_tree, columns=colonnes, show="headings", height=10)
        
        for col in colonnes:
            self.tree.heading(col, text=col)
            if col == "Article":
                self.tree.column(col, width=250)
            elif col in ["Unité"]:
                self.tree.column(col, width=100)
            else:
                self.tree.column(col, width=120)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(frame_tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.tag_configure("even", background="#FFFFFF", foreground="#000000")
        self.tree.tag_configure("odd", background="#E6EFF8", foreground="#000000")
        
        # Bind pour sélection dans le Treeview
        self.tree.bind('<<TreeviewSelect>>', self.on_selection_ligne)
        self.tree.bind('<Double-Button-1>', self.on_double_click_ligne)
        
        # Frame boutons bas
        frame_boutons = ctk.CTkFrame(self)
        frame_boutons.pack(fill="x", padx=20, pady=10)
        
        btn_supprimer = ctk.CTkButton(frame_boutons, text="🗑️ Supprimer Ligne", 
                                      command=self.supprimer_article, 
                                      fg_color="#d32f2f", hover_color="#b71c1c")
        btn_supprimer.pack(side="left", padx=10)
        
        # Bouton Nouvelle Commande
        btn_nouveau = ctk.CTkButton(frame_boutons, text="🔄 Nouvelle Commande", 
                                    command=self.nouvelle_commande,
                                    fg_color="#0288d1", hover_color="#01579b")
        btn_nouveau.pack(side="left", padx=10)
        
        btn_imprimer = ctk.CTkButton(frame_boutons, text="🖨️ Imprimer", 
                                     command=self.imprimer_bon_commande,
                                     fg_color="#ff6f00", hover_color="#e65100")
        btn_imprimer.pack(side="right", padx=10)
        
        btn_enregistrer = ctk.CTkButton(frame_boutons, text="💾 Enregistrer", 
                                        command=self.enregistrer_commande,
                                        fg_color="#2e7d32", hover_color="#1b5e20")
        btn_enregistrer.pack(side="right", padx=10)
        
        # Label total (pour la zone basse, inchangé pour la cohérence, mais le total principal est en haut)
        self.label_total = ctk.CTkLabel(frame_boutons, text="Total: 0,00", 
                                       font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"))
        self.label_total.pack(side="right", padx=20)

    # --- Méthodes de gestion (inchangées) ---
    def on_selection_ligne(self, event):
        selection = self.tree.selection()
        if selection:
            self.btn_modifier_ligne.configure(state="normal")
            self.btn_annuler_selection.configure(state="normal")
            
    def update_date_modification(self):
        """
        Met à jour la colonne datemodif de la commande principale
        (stockée dans self.idcom_charge) avec la date et l'heure actuelles.
        """
        # Assurez-vous que l'ID de la commande est chargé
        if not self.idcom_charge:
            return 
        
        # Récupérer la date et l'heure actuelles
        current_datetime = datetime.now()
        
        conn = self.connect_db() 
        if conn is None:
            return
        
        try:
            cursor = conn.cursor()
            
            # REQUÊTE SQL CORRIGÉE : Utilisation de datemodif
            sql_update = """
                UPDATE tb_commande 
                SET datemodif = %s 
                WHERE idcom = %s;
            """
            
            # Exécution de la requête
            cursor.execute(sql_update, (current_datetime, self.idcom_charge))
            conn.commit()
            
        except psycopg2.Error as e:
            messagebox.showerror("Erreur BDD", f"Échec de la mise à jour de la date de modification: {e}")
            conn.rollback()
            
        finally:
            if conn:
                conn.close()
            
    def on_double_click_ligne(self, event):
        """Double-clic sur une ligne pour la charger dans les champs"""
        selection = self.tree.selection()
        if not selection:
            return
        
        self.charger_ligne_pour_modification(selection[0])
        
    def charger_ligne_pour_modification(self, item_id):
        """Charge les données d'une ligne dans les champs pour modification"""
        index = self.tree.index(item_id)
        self.index_ligne_selectionnee = index
        
        item_data = self.items_commande[index]
        values = self.tree.item(item_id)['values']
        
        # Remplir les champs
        self.entry_article.configure(state="normal")
        self.entry_article.delete(0, "end")
        self.entry_article.insert(0, values[0])  # Article (désignation)
        self.entry_article.configure(state="readonly")
        
        self.entry_unite.configure(state="normal")
        self.entry_unite.delete(0, "end")
        self.entry_unite.insert(0, values[1])  # Unité
        self.entry_unite.configure(state="readonly")
        
        self.entry_qtcmd.delete(0, "end")
        self.entry_qtcmd.insert(0, self.formater_nombre(item_data['qtcmd']))
        
        self.entry_punitcmd.delete(0, "end")
        self.entry_punitcmd.insert(0, self.formater_nombre(item_data['punitcmd']))
        
        self.entry_qtlivre.delete(0, "end")
        self.entry_qtlivre.insert(0, self.formater_nombre(item_data['qtlivre']))
        
        # Stocker l'article sélectionné pour la modification
        self.article_selectionne = {
            'idarticle': item_data['idarticle'],
            'idunite': item_data['idunite'],
            'designation': values[0],
            'unite': values[1]
        }
        
        # Changer l'état des boutons
        self.btn_ajouter.configure(state="disabled")
        self.btn_modifier_ligne.configure(state="normal", text="✅ Valider Modif.")
        self.btn_annuler_selection.configure(state="normal")
        
        # Mettre à jour le preview du total ligne
        self.calculer_total_ligne_preview()
        
        # Mettre en surbrillance visuelle
        self.titre.configure(text=f"⚠️ Modification de la ligne {index + 1}")
            
    def calculer_total_ligne_preview(self):
        try:
            qtcmd = self.parser_nombre(self.entry_qtcmd.get())
            punitcmd = self.parser_nombre(self.entry_punitcmd.get())
            total_ligne = qtcmd * punitcmd
            self.label_total_ligne.configure(text=f"Total Ligne: {self.formater_nombre(total_ligne)}")
        except:
            self.label_total_ligne.configure(text="Total Ligne: 0,00")
            
            
    def modifier_ligne_article(self):
        """Modifie la ligne sélectionnée avec les nouvelles valeurs"""
        selection = self.tree.selection()
        
        # Si pas en mode modification de ligne, charger d'abord
        if self.index_ligne_selectionnee is None:
            if selection:
                self.charger_ligne_pour_modification(selection[0])
            else:
                messagebox.showwarning("Attention", "Veuillez sélectionner une ligne à modifier")
            return
        
        # Valider les modifications
        try:
            qtcmd = self.parser_nombre(self.entry_qtcmd.get())
            punitcmd = self.parser_nombre(self.entry_punitcmd.get())
            qtlivre = self.parser_nombre(self.entry_qtlivre.get())
            
            if qtcmd <= 0:
                messagebox.showwarning("Attention", "La quantité commandée doit être supérieure à 0")
                return
            
            total = qtcmd * punitcmd
            index = self.index_ligne_selectionnee
            
            # Mettre à jour les données
            self.items_commande[index]['qtcmd'] = qtcmd
            self.items_commande[index]['punitcmd'] = punitcmd
            self.items_commande[index]['qtlivre'] = qtlivre
            self.items_commande[index]['total'] = total # Ajout de la mise à jour du total
            
            # Mettre à jour le Treeview
            item_id = self.tree.get_children()[index]
            self.tree.item(item_id, values=(
                self.article_selectionne['designation'],
                self.article_selectionne['unite'],
                self.formater_nombre(qtcmd),
                self.formater_nombre(punitcmd),
                self.formater_nombre(qtlivre),
                self.formater_nombre(total)
            ))

            # ✅ APPEL DE LA FONCTION DE MISE À JOUR DE LA DATE
            if self.idcom_charge:
                self.update_date_modification()
                # Optionnel: Mettre à jour le total dans la DB immédiatement. 
                # Généralement fait dans enregistrer_commande.
                # self.mettre_a_jour_total_commande_db(sum(item['total'] for item in self.items_commande))

            # Réinitialiser l'état
            self.annuler_selection_ligne()
            self.calculer_total()
            
            messagebox.showinfo("Succès", "Ligne modifiée avec succès!")
            
        except ValueError:
            messagebox.showerror("Erreur", "Veuillez entrer des valeurs numériques valides")
        
    def annuler_selection_ligne(self):
        self.index_ligne_selectionnee = None
        self.article_selectionne = None
        
        self.entry_article.configure(state="normal")
        self.entry_article.delete(0, "end")
        self.entry_article.insert(0, "Sélectionnez un article")
        self.entry_article.configure(state="readonly")
        
        self.entry_unite.configure(state="normal")
        self.entry_unite.delete(0, "end")
        self.entry_unite.configure(state="readonly")
        
        self.entry_qtcmd.delete(0, "end")
        self.entry_punitcmd.delete(0, "end")
        self.entry_qtlivre.delete(0, "end")
        self.entry_qtcmd.insert(0, "10") 
        self.entry_punitcmd.insert(0, "5.000,00")
        self.entry_qtlivre.insert(0, "0")
        
        self.label_total_ligne.configure(text="Total Ligne: 50.000,00") 
        self.btn_ajouter.configure(state="normal")
        self.btn_modifier_ligne.configure(state="disabled", text="✏️ Modifier Ligne")
        self.btn_annuler_selection.configure(state="disabled")
        self.tree.selection_remove(self.tree.selection())
        self.titre.configure(text="Nouvelle Commande Fournisseur")

    def ajouter_article(self):
        """Ajoute un article au treeview"""
        if not self.article_selectionne:
            messagebox.showwarning("Attention", "Veuillez sélectionner un article")
            return
        
        try:
            qtcmd = self.parser_nombre(self.entry_qtcmd.get())
            punitcmd = self.parser_nombre(self.entry_punitcmd.get())
            qtlivre = self.parser_nombre(self.entry_qtlivre.get())
            
            if qtcmd <= 0:
                messagebox.showwarning("Attention", "La quantité commandée doit être supérieure à 0")
                return
                
            total = qtcmd * punitcmd
            
            tag = "even" if len(self.tree.get_children()) % 2 == 0 else "odd"
            self.tree.insert("", "end", values=(
                self.article_selectionne['designation'],
                self.article_selectionne['unite'],
                self.formater_nombre(qtcmd),
                self.formater_nombre(punitcmd),
                self.formater_nombre(qtlivre),
                self.formater_nombre(total)
            ), tags=(tag,))
            
            self.items_commande.append({
                'idcomdetail': None,
                'idarticle': self.article_selectionne['idarticle'],
                'designation': self.article_selectionne['designation'],
                'idunite': self.article_selectionne['idunite'], # idunite est maintenant correctement stocké ici
                'qtcmd': qtcmd,
                'punitcmd': punitcmd,
                'qtlivre': qtlivre,
                'total': total # Ajout du total pour la modification
            })
            
            self.article_selectionne = None
            self.entry_article.configure(state="normal")
            self.entry_article.delete(0, "end")
            self.entry_article.configure(state="readonly")
            
            self.entry_unite.configure(state="normal")
            self.entry_unite.delete(0, "end")
            self.entry_unite.configure(state="readonly")
            
            self.entry_qtcmd.delete(0, "end")
            self.entry_punitcmd.delete(0, "end")
            self.entry_qtlivre.delete(0, "end")
            self.entry_qtlivre.insert(0, "0")
            
            self.calculer_total()
            self.calculer_total_ligne_preview() # Réinitialiser le label de ligne
            
        except ValueError:
            messagebox.showerror("Erreur", "Veuillez entrer des valeurs numériques valides")

    def supprimer_article(self):
        """Supprime l'article sélectionné du treeview"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner un article à supprimer")
            return
            
        if self.index_ligne_selectionnee is not None:
            self.annuler_selection_ligne()
            
        index = self.tree.index(selection[0])
        self.tree.delete(selection[0])
        self.items_commande.pop(index)
        self.calculer_total()
        
    def calculer_total(self):
        """Calcule et affiche le total de la commande (pour les deux labels)"""
        total = sum(item['qtcmd'] * item['punitcmd'] for item in self.items_commande)
        
        # Mise à jour du label en bas
        self.label_total.configure(text=f"Total: {self.formater_nombre(total)}")
        
        # Mise à jour du label total global en haut (NOUVEAU)
        self.label_total_global.configure(text=f"Total Commande: {self.formater_nombre(total)}")
        
    def ouvrir_recherche_commande(self):
        """Ouvre une fenêtre pour rechercher et charger une commande existante"""
        fenetre = ctk.CTkToplevel(self)
        fenetre.title("Rechercher une commande à modifier")
        fenetre.geometry("900x500")
        fenetre.grab_set()
        
        main_frame = ctk.CTkFrame(fenetre)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        titre = ctk.CTkLabel(main_frame, text="Sélectionner une commande", 
                            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"))
        titre.pack(pady=(0, 10))
        
        search_frame = ctk.CTkFrame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(search_frame, text="🔍 Rechercher:").pack(side="left", padx=5)
        entry_search = ctk.CTkEntry(search_frame, placeholder_text="Référence ou fournisseur...", width=300)
        entry_search.pack(side="left", padx=5, fill="x", expand=True)
        
        tree_frame = ctk.CTkFrame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        colonnes = ("ID", "Référence", "Date", "Fournisseur", "Description", "Statut")
        tree = ttk.Treeview(tree_frame, columns=colonnes, show='headings', height=12)
        
        tree.heading("ID", text="ID")
        tree.heading("Référence", text="Référence")
        tree.heading("Date", text="Date")
        tree.heading("Fournisseur", text="Fournisseur")
        tree.heading("Description", text="Description")
        tree.heading("Statut", text="Statut")
        
        tree.column("ID", width=0, stretch=False)
        tree.column("Référence", width=120, anchor='w')
        tree.column("Date", width=100, anchor='w')
        tree.column("Fournisseur", width=200, anchor='w')
        tree.column("Description", width=250, anchor='w')
        tree.column("Statut", width=100, anchor='center')
        
        # Style pour les tags
        style = ttk.Style()
        style.configure("Treeview", rowheight=22, background="#FFFFFF", foreground="#000000", fieldbackground="#FFFFFF", borderwidth=0, font=('Segoe UI', 8))
        style.configure("Treeview.Heading", background="#E8E8E8", foreground="#000000", font=('Segoe UI', 8, 'bold'))
        tree.tag_configure("even", background="#FFFFFF", foreground="#000000")
        tree.tag_configure("odd", background="#E6EFF8", foreground="#000000")
        tree.tag_configure('incomplet', foreground='#B00020')
        tree.tag_configure('complet', foreground='#1B5E20')
        
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
                query = """
                    SELECT c.idcom, c.refcom, c.datecom, f.nomfrs, c.descriptioncom,
                           (SELECT COUNT(*) 
                            FROM tb_commandedetail d 
                            WHERE d.idcom = c.idcom) as total_lignes,
                           (SELECT COUNT(*) 
                            FROM tb_commandedetail d 
                            WHERE d.idcom = c.idcom AND d.qtcmd = d.qtlivre) as lignes_completes
                    FROM tb_commande c
                    LEFT JOIN tb_fournisseur f ON c.idfrs = f.idfrs
                    WHERE c.deleted = 0
                """
                params = []
                if filtre:
                    query += """ AND (
                        LOWER(c.refcom) LIKE LOWER(%s) OR 
                        LOWER(f.nomfrs) LIKE LOWER(%s)
                    )"""
                    params = [f"%{filtre}%", f"%{filtre}%"]
                
                query += " ORDER BY c.datecom DESC, c.refcom DESC"
                cursor.execute(query, params)
                resultats = cursor.fetchall()
                
                for idx, row in enumerate(resultats):
                    date_str = row[2].strftime("%d/%m/%Y") if row[2] else ""
                    total_lignes = row[5] if row[5] else 0
                    lignes_completes = row[6] if row[6] else 0
                    
                    # Déterminer le statut et le tag
                    if total_lignes > 0 and lignes_completes == total_lignes:
                        statut = "✅ Livrés"
                        status_tag = 'complet'
                    else:
                        statut = "⚠️ En attente"
                        status_tag = 'incomplet'
                    zebra_tag = "even" if idx % 2 == 0 else "odd"
                    
                    tree.insert('', 'end', 
                              values=(row[0], row[1], date_str, row[3] or "", row[4] or "", statut),
                              tags=(zebra_tag, status_tag))
                
                label_count.configure(text=f"Nombre de commandes : {len(resultats)}")
                
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors du chargement: {str(e)}")
            finally:
                if 'cursor' in locals() and cursor: cursor.close()
                if conn: conn.close()
        
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
        btn_annuler = ctk.CTkButton(btn_frame, text="❌ Annuler", command=fenetre.destroy, fg_color="#d32f2f", hover_color="#b71c1c")
        btn_annuler.pack(side="left", padx=5, pady=5)
        btn_valider = ctk.CTkButton(btn_frame, text="✅ Charger", command=valider_selection, fg_color="#2e7d32", hover_color="#1b5e20")
        btn_valider.pack(side="right", padx=5, pady=5)
        charger_commandes()
        
    def charger_commande(self, idcom):
        """Charge une commande existante pour modification"""
        conn = self.connect_db()
        if not conn: return
        try:
            cursor = conn.cursor()
            query_commande = """
                SELECT c.idcom, c.refcom, c.datecom, c.idfrs, f.nomfrs, c.descriptioncom
                FROM tb_commande c
                LEFT JOIN tb_fournisseur f ON c.idfrs = f.idfrs
                WHERE c.idcom = %s AND c.deleted = 0
            """
            cursor.execute(query_commande, (idcom,))
            commande = cursor.fetchone()
            if not commande:
                messagebox.showerror("Erreur", "Commande non trouvée")
                return

            query_details = """
                SELECT d.id, d.idarticle, a.designation, u.designationunite, d.idunite, d.qtcmd, d.qtlivre, d.punitcmd
                FROM tb_commandedetail d
                INNER JOIN tb_article a ON d.idarticle = a.idarticle
                INNER JOIN tb_unite u ON d.idunite = u.idunite
                WHERE d.idcom = %s
            """
            cursor.execute(query_details, (idcom,))
            details = cursor.fetchall()
            
            self.reinitialiser_formulaire(generer_ref=False)
            self.mode_modification = True
            self.idcom_charge = idcom
            self.titre.configure(text=f"Modification Commande: {commande[1]}")
            
            self.entry_ref.configure(state="normal")
            self.entry_ref.delete(0, "end")
            self.entry_ref.insert(0, commande[1])
            self.entry_ref.configure(state="readonly")
            
            if commande[4]:
                self.combo_fournisseur.set(commande[4])
                
            for idx, detail in enumerate(details):
                idcomdetail, idarticle, designation, unite, idunite, qtcmd, qtlivre, punitcmd = detail
                punitcmd = punitcmd if punitcmd else 0
                total = qtcmd * punitcmd
                
                # Ajout des données à la liste interne
                self.items_commande.append({
                    'idcomdetail': idcomdetail,
                    'idarticle': idarticle,
                    'idunite': idunite,
                    'qtcmd': qtcmd,
                    'qtlivre': qtlivre,
                    'punitcmd': punitcmd,
                    'total': total
                })
                
                # Ajout au Treeview
                tag = "even" if idx % 2 == 0 else "odd"
                self.tree.insert("", "end", values=(
                    designation, 
                    unite, 
                    self.formater_nombre(qtcmd), 
                    self.formater_nombre(punitcmd), 
                    self.formater_nombre(qtlivre), 
                    self.formater_nombre(total)
                ), tags=(tag,))
                
            self.calculer_total()
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement de la commande: {str(e)}")
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()
        
    def enregistrer_commande(self):
        """Enregistre la commande (INSERT ou UPDATE selon le mode)"""
        if self.index_ligne_selectionnee is not None:
            messagebox.showwarning("Attention", "Veuillez d'abord valider ou annuler la modification de ligne en cours")
            return
            
        if not self.items_commande:
            messagebox.showwarning("Attention", "La commande ne contient aucune ligne.")
            return

        frs_nom = self.combo_fournisseur.get()
        idfrs = self.fournisseurs.get(frs_nom)
        
        if not idfrs:
            messagebox.showwarning("Attention", "Veuillez sélectionner un fournisseur.")
            return
            
        total_commande = sum(item['qtcmd'] * item['punitcmd'] for item in self.items_commande)
        
        conn = self.connect_db()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            description = "" # Description non gérée dans cette version
            
            if self.mode_modification and self.idcom_charge:
                # Mode Modification (UPDATE)
                
                # 1. Mise à jour de la commande principale (AJOUT DE totalcom)
                # VEUILLEZ VOUS ASSURER QUE LA COLONNE totalcom EXISTE DANS tb_commande
                query_commande = """
                    UPDATE tb_commande 
                    SET refcom = %s, idfrs = %s, descriptioncom = %s, totcmd = %s
                    WHERE idcom = %s
                """
                cursor.execute(query_commande, (
                    self.entry_ref.get(), 
                    idfrs, 
                    description, 
                    total_commande, # Nouveau champ totalcom
                    self.idcom_charge
                ))
                
                ids_existants = [item['idcomdetail'] for item in self.items_commande if item['idcomdetail']]
                
                # 2. Suppression des lignes non conservées
                query_select_ids = "SELECT id FROM tb_commandedetail WHERE idcom = %s"
                cursor.execute(query_select_ids, (self.idcom_charge,))
                all_ids_in_db = [row[0] for row in cursor.fetchall()]
                
                ids_a_supprimer = [id_db for id_db in all_ids_in_db if id_db not in ids_existants]
                
                if ids_a_supprimer:
                    # Correction: utiliser le format correct pour IN (tuple)
                    query_delete = "DELETE FROM tb_commandedetail WHERE id IN %s"
                    cursor.execute(query_delete, (tuple(ids_a_supprimer),))

                # 3. Insertion/Mise à jour des lignes
                query_update = """
                    UPDATE tb_commandedetail 
                    SET idarticle = %s, idunite = %s, qtcmd = %s, qtlivre = %s, punitcmd = %s, total = %s
                    WHERE id = %s
                """
                query_insert = """
                    INSERT INTO tb_commandedetail (idcom, idarticle, idunite, qtcmd, qtlivre, punitcmd, total)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                
                for item in self.items_commande:
                    total_ligne = item['qtcmd'] * item['punitcmd']
                    if item['idcomdetail']:
                        # UPDATE
                        cursor.execute(query_update, (
                            item['idarticle'], 
                            item['idunite'], 
                            item['qtcmd'], 
                            item['qtlivre'], 
                            item['punitcmd'], 
                            total_ligne,
                            item['idcomdetail']
                        ))
                    else:
                        # INSERT (nouvelle ligne)
                        cursor.execute(query_insert, (
                            self.idcom_charge, 
                            item['idarticle'], 
                            item['idunite'], 
                            item['qtcmd'], 
                            item['qtlivre'], 
                            item['punitcmd'],
                            total_ligne
                        ))
                        
                conn.commit()
                messagebox.showinfo("Succès", f"Commande {self.entry_ref.get()} modifiée avec succès!")
                
            else:
                # Mode Création (INSERT)
                
                # 1. Insertion de la commande principale (AJOUT DE totalcom)
                # VEUILLEZ VOUS ASSURER QUE LA COLONNE totalcom EXISTE DANS tb_commande
                query_commande = """
                    INSERT INTO tb_commande (refcom, datecom, iduser, idfrs, descriptioncom, totcmd, deleted)
                    VALUES (%s, %s, %s, %s, %s, %s, 0)
                    RETURNING idcom
                """
                cursor.execute(query_commande, (
                    self.entry_ref.get(), 
                    datetime.now().strftime('%Y-%m-%d'), # Utiliser un format DB-friendly
                    self.iduser, 
                    idfrs, 
                    description,
                    total_commande # Nouveau champ totalcom
                ))
                idcom = cursor.fetchone()[0]
                
                # 2. Insertion des détails
                query_detail = """
                    INSERT INTO tb_commandedetail (idcom, idarticle, idunite, qtcmd, qtlivre, punitcmd, total)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                for item in self.items_commande:
                    total_ligne = item['qtcmd'] * item['punitcmd']
                    cursor.execute(query_detail, (
                        idcom, 
                        item['idarticle'], 
                        item['idunite'], 
                        item['qtcmd'], 
                        item['qtlivre'], 
                        item['punitcmd'],
                        total_ligne 
                    ))
                    
                conn.commit()
                messagebox.showinfo("Succès", "Commande enregistrée avec succès!")
                
            self.mode_modification = False
            self.idcom_charge = None
            self.titre.configure(text="Nouvelle Commande Fournisseur")
            self.reinitialiser_formulaire()
            
        except Exception as e:
            conn.rollback()
            # Affichage de l'erreur originale pour débogage
            messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement: {str(e)}")
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()
    
    def reinitialiser_formulaire(self, generer_ref=True):
        """Réinitialise le formulaire après enregistrement"""
        if generer_ref:
            self.generer_reference()
        self.items_commande.clear()
        self.index_ligne_selectionnee = None
        self.article_selectionne = None
        
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        self.entry_article.configure(state="normal")
        self.entry_article.delete(0, "end")
        self.entry_article.configure(state="readonly")
        
        self.entry_unite.configure(state="normal")
        self.entry_unite.delete(0, "end")
        self.entry_unite.configure(state="readonly")
        
        self.entry_qtcmd.delete(0, "end")
        self.entry_punitcmd.delete(0, "end")
        self.entry_qtlivre.delete(0, "end")
        self.entry_qtlivre.insert(0, "0")
        
        self.btn_ajouter.configure(state="normal")
        self.btn_modifier_ligne.configure(state="disabled", text="✏️ Modifier Ligne")
        self.btn_annuler_selection.configure(state="disabled")
        
        # Réinitialiser le label total ligne
        self.label_total_ligne.configure(text="Total Ligne: 0,00")
        
        self.calculer_total()
    
    def nouvelle_commande(self):
        """Réinitialise le formulaire et le mode de commande"""
        self.reinitialiser_formulaire()
        self.mode_modification = False
        self.idcom_charge = None
        self.titre.configure(text="Nouvelle Commande Fournisseur")
        
    def imprimer_bon_commande(self):
        """Génère un Bon de Commande PDF en utilisant le modèle central `EtatPDFMouvements`."""
        if not self.idcom_charge and not self.items_commande:
            messagebox.showwarning("Attention", "Veuillez charger ou créer une commande pour imprimer.")
            return

        # Si non enregistré, proposer d'enregistrer
        if not self.idcom_charge:
            reponse = messagebox.askyesno("Confirmation d'enregistrement", "Voulez-vous enregistrer cette commande avant d'imprimer ?")
            if reponse:
                self.enregistrer_commande()
                if not self.idcom_charge:
                    return
            else:
                messagebox.showwarning("Annulation", "Impression annulée. Enregistrez pour obtenir un bon officiel.")
                return

        # Préparer le dossier et le nom de fichier
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        etats_dir = os.path.join(project_dir, "Etats Impression")
        if not os.path.exists(etats_dir):
            os.makedirs(etats_dir)

        filename = os.path.join(etats_dir, f"Bon_Commande_{self.entry_ref.get().replace('-', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")

        # Construire table_data (Code, Désignation, Unité, Qté, P.U., Total)
        columns = ("Code", "Désignation", "Unité", "Qté", "P.U.", "Total")
        rows = []
        for item in self.items_commande:
            code = item.get('designation', '')[:20]
            designation = item.get('designation', '')
            unite = ''
            # essayer de récupérer l'unité depuis DB si possible
            try:
                conn = self.connect_db()
                if conn:
                    cur = conn.cursor()
                    cur.execute("SELECT designationunite FROM tb_unite WHERE idunite = %s LIMIT 1", (item.get('idunite'),))
                    r = cur.fetchone()
                    if r:
                        unite = r[0]
                    cur.close()
            except Exception:
                unite = ''
            finally:
                try:
                    if conn:
                        conn.close()
                except Exception:
                    pass

            qte = item.get('qtcmd', 0) or 0
            pu = item.get('punitcmd', 0) or 0
            total = item.get('total', qte * pu)
            rows.append((code, designation, unite, qte, pu, total))

        table_data = (columns, rows)

        # Opérateur: essayer de récupérer le nom d'utilisateur si possible
        operateur = str(self.iduser)
        try:
            conn = self.connect_db()
            if conn:
                cur = conn.cursor()
                cur.execute("SELECT username FROM tb_users WHERE iduser = %s LIMIT 1", (self.iduser,))
                r = cur.fetchone()
                if r and r[0]:
                    operateur = r[0]
                cur.close()
        except Exception:
            pass
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                pass

        # Appeler le builder centralisé pour produire le PDF (récupérera les infos société depuis la BDD)
        try:
            from EtatsPDF_Mouvements import EtatPDFMouvements

            etat = EtatPDFMouvements()
            try:
                etat.connect_db()
            except Exception:
                pass

            success = etat._build_pdf_a5(
                output_path=filename,
                titre_entete="BON DE COMMANDE",
                reference=self.entry_ref.get(),
                date_operation=datetime.now().strftime('%d/%m/%Y'),
                magasin="-",
                operateur=operateur,
                table_data=table_data,
                description="Bon de commande",
                responsable_1="Le Responsable",
                responsable_2="Le Fournisseur",
            )

            try:
                etat.close_db()
            except Exception:
                pass

            if success and sys.platform == 'win32':
                try:
                    os.startfile(filename)
                except Exception:
                    pass

            if success:
                messagebox.showinfo("Impression", f"Le bon de commande a été généré:\n{filename}")
            else:
                messagebox.showerror("Erreur", "Échec génération PDF Bon de commande.")

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur génération PDF Bon de commande: {e}")

    def afficher_apercu_impression(self, html_content):
        """Affiche l'aperçu avant impression"""
        import tempfile
        import webbrowser
        import os
    
        # Créer un fichier temporaire
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.html', encoding='utf-8') as f:
            f.write(html_content)
            temp_path = f.name
    
        # Ouvrir dans le navigateur par défaut
        webbrowser.open('file://' + os.path.abspath(temp_path))
    
        messagebox.showinfo("Impression", 
                      "Le bon de commande a été ouvert dans votre navigateur.\n\n"
                      "Utilisez Ctrl+P ou Cmd+P pour l'imprimer.")


# --- 2. Classes de sous-fenêtres (Placeholders) ---

class PageLivrFrs(ctk.CTkFrame):
    """Fenêtre pour le Bon de Réception."""
    def __init__(self, master=None):
        super().__init__(master, fg_color="white")
        label = ctk.CTkLabel(self, text="BON DE RÉCEPTION", font=ctk.CTkFont(family="Segoe UI", size=30, weight="bold"), text_color="black")
        label.pack(pady=50, padx=50)
        
        

class PageTransfert(ctk.CTkFrame):
    """Fenêtre pour le Bon de Transfert."""
    def __init__(self, master=None):
        super().__init__(master, fg_color="white")
        label = ctk.CTkLabel(self, text="BON DE TRANSFERT", font=ctk.CTkFont(family="Segoe UI", size=30, weight="bold"), text_color="black")
        label.pack(pady=50, padx=50)

class PageSortie(ctk.CTkFrame):
    """Fenêtre pour le Bon de Sortie."""
    def __init__(self, master=None):
        super().__init__(master, fg_color="white")
        label = ctk.CTkLabel(self, text="BON DE SORTIE", font=ctk.CTkFont(family="Segoe UI", size=30, weight="bold"), text_color="black")
        label.pack(pady=50, padx=50)


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

        messagebox.showinfo("Enregistrement", 
                          f"Sortie: {len(self.articles_sortie)} articles\nEntrée: {len(self.articles_entree)} articles\n\n"
                          "Enregistrement à développer")

    def imprimer_changement(self):
        """Imprime le changement"""
        if not self.articles_sortie and not self.articles_entree:
            messagebox.showwarning("Attention", "Aucun article à imprimer")
            return

        messagebox.showinfo("Impression", "Impression à développer")


# --- 3. Classe Principale (Conteneur) ---

class PageMouvementStock(ctk.CTkFrame):
    def __init__(self, master=None, iduser=1): 
        super().__init__(master)
        self.iduser = iduser 
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)  # Navigation fixe
        self.grid_columnconfigure(1, weight=1)  # Content expansion
        
        self.current_page = None 
        self.nav_buttons = {}    
        
        # --- NAVIGATION FRAME ---
        self.navigation_frame = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=NAV_BAR_COLOR)
        self.navigation_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.navigation_frame.grid_propagate(False)  # Force la largeur 200px
        
        # --- TITLE SECTION ---
        title_label = ctk.CTkLabel(
            self.navigation_frame, 
            text="Mise-à-jour", 
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), 
            text_color="white"
        )
        title_label.pack(side="top", padx=20, pady=15, fill="x")
        
        # --- BUTTONS FRAME (scrollable si nécessaire) ---
        buttons_frame = ctk.CTkFrame(self.navigation_frame, fg_color=NAV_BAR_COLOR)
        buttons_frame.pack(side="top", fill="both", expand=False, padx=0, pady=0)
        
        # --- PAGES DEFINITION ---
        self.pages = {
            "Mise à jour BC": PageCmdFrs,      
            "Mise à jour BR": PageLivrFrs,
            "Mise à jour Transfer": PageTransfert,
            "Mise à jour Sortie": PageSortie,
            "Changement d'articles": PageChangementArticle,
        }
        
        self.page_frames = {}
        
        # --- CREATE BUTTONS ---
        for i, (name, PageClass) in enumerate(self.pages.items()):
            # Container pour chaque bouton
            btn_container = ctk.CTkFrame(buttons_frame, fg_color=INACTIVE_BUTTON_COLOR, height=50)
            btn_container.pack(side="top", fill="x", padx=0, pady=0)
            btn_container.pack_propagate(False)
            
            # Checkbox
            checkbox = ctk.CTkCheckBox(
                btn_container, 
                text="", 
                width=20, 
                height=20, 
                border_width=2, 
                fg_color=NAV_BAR_COLOR, 
                hover_color=NAV_BAR_COLOR, 
                border_color="white", 
                checkmark_color="white",
                state="disabled" 
            )
            checkbox.pack(side="left", padx=12, pady=10)
            
            # Button
            button_command = lambda p=name, pc=PageClass: self.show_page(p)
            
            button = ctk.CTkButton(
                btn_container, 
                text=name, 
                command=button_command, 
                fg_color="transparent", 
                hover_color="#006BB3", 
                text_color=INACTIVE_TEXT_COLOR,
                anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=12)
            )
            button.pack(side="left", fill="both", expand=True, padx=(0, 12), pady=5)
            
            self.nav_buttons[name] = {
                "container": btn_container,
                "button": button,
                "checkbox": checkbox
            }
        
        # --- SPACER (expansion) ---
        spacer = ctk.CTkFrame(self.navigation_frame, fg_color=NAV_BAR_COLOR)
        spacer.pack(side="top", fill="both", expand=True)
        
        # --- BOTTOM LABEL ---
        bottom_container = ctk.CTkFrame(self.navigation_frame, fg_color=NAV_BAR_COLOR, height=50)
        bottom_container.pack(side="bottom", fill="x", padx=0, pady=0)
        bottom_container.pack_propagate(False)
        
        stop_checkbox = ctk.CTkCheckBox(
            bottom_container, 
            text="", 
            width=20, 
            height=20, 
            border_width=2, 
            fg_color=NAV_BAR_COLOR, 
            border_color="white", 
            checkmark_color="white"
        )
        stop_checkbox.pack(side="left", padx=12, pady=10)
        
        stop_label = ctk.CTkLabel(
            bottom_container, 
            text="Mise-à-jour Arrêt", 
            font=ctk.CTkFont(family="Segoe UI", size=12), 
            text_color="white"
        )
        stop_label.pack(side="left", padx=(0, 12), pady=5, fill="x", expand=True)

        # --- CONTENT FRAME ---
        self.content_frame = ctk.CTkFrame(self, fg_color="white")
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        # --- INITIALIZE ALL PAGES ---
        for name, PageClass in self.pages.items():
            if name in ["Mise à jour BC", "Changement d'articles"]:
                frame = PageClass(master=self.content_frame, iduser=self.iduser)
            else:
                frame = PageClass(master=self.content_frame)
                
            self.page_frames[name] = frame
            frame.grid(row=0, column=0, sticky="nsew") 

        self.show_page("Mise à jour BC")
        
    def show_page(self, page_name):
        """Affiche la page demandée et met à jour l'apparence des boutons."""
        if self.current_page == page_name:
            return

        if self.current_page and self.current_page in self.page_frames:
            self.page_frames[self.current_page].grid_remove()
            self._update_button_visuals(self.current_page, is_active=False)

        if page_name in self.page_frames:
            self.page_frames[page_name].grid()
            self.current_page = page_name
            self._update_button_visuals(page_name, is_active=True)
    
    
    def _update_button_visuals(self, name, is_active):
        """Mettre à jour l'apparence du bouton de navigation."""
        if name in self.nav_buttons:
            widgets = self.nav_buttons[name]
            
            if is_active:
                widgets["container"].configure(fg_color=ACTIVE_BUTTON_COLOR)
                widgets["button"].configure(
                    fg_color=ACTIVE_BUTTON_COLOR, 
                    hover_color="#E0E0E0", 
                    text_color=ACTIVE_TEXT_COLOR
                )
                widgets["checkbox"].select()
                widgets["checkbox"].configure(fg_color="white", checkmark_color=NAV_BAR_COLOR)
            else:
                widgets["container"].configure(fg_color=NAV_BAR_COLOR)
                widgets["button"].configure(
                    fg_color="transparent", 
                    hover_color="#006BB3", 
                    text_color=INACTIVE_TEXT_COLOR
                )
                widgets["checkbox"].deselect()
                widgets["checkbox"].configure(fg_color=NAV_BAR_COLOR, checkmark_color="white")

    def on_double_click(self, event):
        """Gérer le double-clic sur une ligne du tableau"""
        selection = self.tree.selection()
        if not selection:
            return
    
        # Récupérer les valeurs de la ligne sélectionnée
        values = self.tree.item(selection[0])['values']
    
        if not values:
            return
    
        reference = values[1]  # RÉFÉRENCE
        type_doc = values[2]   # TYPE
    
        # Ouvrir la fenêtre appropriée selon le type de document
        if type_doc == "Bon de Réception":
            self.open_bon_reception(reference)
        elif type_doc == "Facture":
            messagebox.showinfo("Info", f"Ouverture de la facture {reference}")
        # self.open_facture(reference)
        elif type_doc == "Bon de sortie":
            messagebox.showinfo("Info", f"Ouverture du bon de sortie {reference}")
            # self.open_bon_sortie(reference)
        elif type_doc == "Avoir":
            messagebox.showinfo("Info", f"Ouverture de l'avoir {reference}")
        # self.open_avoir(reference)
        elif type_doc in ["Bon de transfert (Sortie)", "Bon de transfert (Entrée)"]:
            messagebox.showinfo("Info", f"Ouverture du bon de transfert {reference}")
            # self.open_bon_transfert(reference)

    def open_bon_reception(self, reference):
        """Ouvrir la fenêtre du bon de réception"""
        # Créer une fenêtre toplevel
        bon_window = ctk.CTkToplevel(self)
        bon_window.title(f"Bon de Réception - {reference}")
        bon_window.geometry("1400x800")
        bon_window.transient(self)
    
        # Charger la page PageLivrFrs dans cette fenêtre
        page_livrFrs = PageLivrFrs(bon_window)
    
        # Optionnel : charger automatiquement le bon avec cette référence
        # Si PageLivrFrs a une méthode pour charger un bon spécifique
        # page_livr.load_bon_by_reference(reference)  
        

# --- Point d'entrée de l'application ---
if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Gestion de Mouvements de Stock")
    app.geometry("1000x800")  # Augmenté de 700 à 800 pour plus d'espace vertical 
    
    app.grid_rowconfigure(0, weight=1)
    app.grid_columnconfigure(0, weight=1)
    
    USER_ID = 1 
    
    main_window = PageMouvementStock(master=app, iduser=USER_ID)
    main_window.grid(row=0, column=0, sticky="nsew")
    
    app.mainloop()
