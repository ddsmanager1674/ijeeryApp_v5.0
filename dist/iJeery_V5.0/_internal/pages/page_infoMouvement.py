import customtkinter as ctk
from tkinter import messagebox, ttk
import psycopg2
import json
import os
import sys
import subprocess
from datetime import datetime
from resource_utils import get_config_path, safe_file_read

# Imports pour génération PDF
from reportlab.lib.pagesizes import A5, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageTemplate, Frame
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas


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
    
    # Format A5 Landscape pour PDF
    PAGE_WIDTH, PAGE_HEIGHT = landscape(A5)
    MARGIN = 5 * mm
    
    # Couleurs pour PDF
    COLOR_HEADER = colors.HexColor("#034787")  # Bleu
    COLOR_BORDER = colors.HexColor("#000000")  # Noir
    COLOR_BG_HEADER = colors.HexColor("#F5F5F5")  # Gris très clair
    COLOR_BG_TABLE_HEADER = colors.HexColor("#E8E8E8")  # Gris clair
    COLOR_BG_FOOTER = colors.HexColor("#F0F0F0")  # Gris
    
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

    def _configure_table_alternating_colors(self, tree):
        """Configure les tags pair/impair pour un tableau."""
        tree.tag_configure("row_even", background="#FFFFFF")
        tree.tag_configure("row_odd", background="#F3F7FF")

    def _refresh_table_alternating_colors(self, tree):
        """Réapplique les couleurs alternées sur toutes les lignes."""
        for idx, item in enumerate(tree.get_children()):
            tree.item(item, tags=("row_even" if idx % 2 == 0 else "row_odd",))

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

    def _get_societe_info(self):
        """Récupère les informations de la société depuis tb_infosociete."""
        conn = self.connect_db()
        if not conn:
            return {
                'nomsociete': 'IJEERY',
                'adressesociete': 'Adresse Non Configurée',
                'villesociete': '',
                'contactsociete': 'Contact: Non Configuré',
                'nifsociete': 'NIF: Non Configuré',
                'statsociete': 'STAT: Non Configurée',
                'cifsociete': 'CIF: Non Configuré'
            }
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    nomsociete, villesociete, adressesociete, contactsociete,
                    nifsociete, statsociete, cifsociete
                FROM tb_infosociete LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                return {
                    'nomsociete': row[0] or 'IJEERY',
                    'villesociete': row[1] or '',
                    'adressesociete': row[2] or 'Adresse Non Configurée',
                    'contactsociete': row[3] or 'Contact: Non Configuré',
                    'nifsociete': row[4] or 'NIF: Non Configuré',
                    'statsociete': row[5] or 'STAT: Non Configurée',
                    'cifsociete': row[6] or 'CIF: Non Configuré'
                }
        except Exception as e:
            print(f"Erreur lors de la récupération des infos société: {e}")
        
        return {
            'nomsociete': 'IJEERY',
            'adressesociete': 'Adresse Non Configurée',
            'villesociete': '',
            'contactsociete': 'Contact: Non Configuré',
            'nifsociete': 'NIF: Non Configuré',
            'statsociete': 'STAT: Non Configurée',
            'cifsociete': 'CIF: Non Configuré'
        }

    def charger_magasins(self):
        """Charge la liste des magasins"""
        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            query = "SELECT idmag, designationmag FROM tb_magasin WHERE deleted = 0 ORDER BY designationmag"
            cursor.execute(query)
            magasins_rows = cursor.fetchall()
            self.magasins = {row[1]: row[0] for row in magasins_rows}
            
            noms_magasins = list(self.magasins.keys())
            self.combo_mag_sortie.configure(values=noms_magasins)
            self.combo_mag_entree.configure(values=noms_magasins)
            
            if noms_magasins:
                idmag_defaut = None
                cursor.execute("SELECT idmag FROM tb_users WHERE iduser = %s LIMIT 1", (self.iduser,))
                row_user = cursor.fetchone()
                if row_user:
                    idmag_defaut = row_user[0]

                nom_magasin_defaut = next((nom for id_, nom in magasins_rows if id_ == idmag_defaut), None)
                if nom_magasin_defaut:
                    self.combo_mag_sortie.set(nom_magasin_defaut)
                    self.combo_mag_entree.set(nom_magasin_defaut)
                else:
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
        self.tree_sortie = ttk.Treeview(frame_tree_sortie, columns=colonnes_sortie, show="headings", height=4)
        self._configure_table_alternating_colors(self.tree_sortie)

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
        self.tree_entree = ttk.Treeview(frame_tree_entree, columns=colonnes_entree, show="headings", height=4)
        self._configure_table_alternating_colors(self.tree_entree)

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

        # ============ CHAMP NOTE ============
        frame_note = ctk.CTkFrame(self, fg_color="transparent")
        frame_note.pack(fill="x", padx=20, pady=(0, 10))
        
        ctk.CTkLabel(frame_note, text="📝 Note du changement:").pack(side="left", padx=5)
        self.entry_note = ctk.CTkEntry(frame_note, placeholder_text="Entrez une note (optionnel)...")
        self.entry_note.pack(side="left", fill="x", expand=True, padx=5)

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
        self.open_recherche_article("sortie")

    def ouvrir_recherche_article_entree(self):
        """Ouvre la fenêtre de recherche d'article pour ENTRÉE"""
        self.open_recherche_article("entree")

    def calculer_stock_article(self, idarticle, idunite, idmag):
        """
        Calcule le stock consolidé en prenant en compte tous les mouvements.
        Formule: (Réceptions + Transferts IN + Inventaires + Avoirs - Ventes - Sorties - Transferts OUT)
        """
        conn = self.connect_db()
        if not conn: 
            return 0
    
        try:
            cursor = conn.cursor()
            
            # D'abord récupérer le codearticle pour tb_inventaire
            cursor.execute("""
                SELECT codearticle FROM tb_unite WHERE idarticle = %s AND idunite = %s
            """, (idarticle, idunite))
            result = cursor.fetchone()
            codearticle = result[0] if result else None
            
            if not codearticle:
                return 0
            
            # Réceptions (tb_livraisonfrs)
            cursor.execute("""
                SELECT COALESCE(SUM(qtlivrefrs), 0) 
                FROM tb_livraisonfrs 
                WHERE idarticle = %s AND idunite = %s AND deleted = 0 AND idmag = %s
            """, (idarticle, idunite, idmag))
            receptions = cursor.fetchone()[0] or 0
        
            # Ventes (tb_ventedetail)
            cursor.execute("""
                SELECT COALESCE(SUM(qtvente), 0) 
                FROM tb_ventedetail 
                WHERE idarticle = %s AND idunite = %s AND deleted = 0 AND idmag = %s
            """, (idarticle, idunite, idmag))
            ventes = cursor.fetchone()[0] or 0
        
            # Sorties (tb_sortiedetail)
            cursor.execute("""
                SELECT COALESCE(SUM(qtsortie), 0) 
                FROM tb_sortiedetail 
                WHERE idarticle = %s AND idunite = %s AND idmag = %s
            """, (idarticle, idunite, idmag))
            sorties = cursor.fetchone()[0] or 0
        
            # Transferts Entrée (tb_transfertdetail)
            cursor.execute("""
                SELECT COALESCE(SUM(qttransfert), 0) 
                FROM tb_transfertdetail 
                WHERE idarticle = %s AND idunite = %s AND deleted = 0 AND idmagentree = %s
            """, (idarticle, idunite, idmag))
            transferts_in = cursor.fetchone()[0] or 0
            
            # Transferts Sortie (tb_transfertdetail)
            cursor.execute("""
                SELECT COALESCE(SUM(qttransfert), 0) 
                FROM tb_transfertdetail 
                WHERE idarticle = %s AND idunite = %s AND deleted = 0 AND idmagsortie = %s
            """, (idarticle, idunite, idmag))
            transferts_out = cursor.fetchone()[0] or 0
        
            # Inventaires (tb_inventaire utilise codearticle)
            cursor.execute("""
                SELECT COALESCE(SUM(qtinventaire), 0) 
                FROM tb_inventaire 
                WHERE codearticle = %s AND idmag = %s
            """, (codearticle, idmag))
            inventaires = cursor.fetchone()[0] or 0

            # Avoirs (augmentent le stock - annulation de vente)
            cursor.execute("""
                SELECT COALESCE(SUM(ad.qtavoir), 0) 
                FROM tb_avoirdetail ad
                INNER JOIN tb_avoir a ON ad.idavoir = a.id
                WHERE ad.idarticle = %s AND ad.idunite = %s AND ad.idmag = %s
                AND a.deleted = 0 AND ad.deleted = 0
            """, (idarticle, idunite, idmag))
            avoirs = cursor.fetchone()[0] or 0

            # Calcul final : Stock = Entrées - Sorties
            stock_total = (receptions + transferts_in + inventaires + avoirs) - (ventes + sorties + transferts_out)
            
            return max(0, stock_total)
        
        except Exception as e:
            print(f"Erreur calcul stock: {e}")
            return 0
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def open_recherche_article(self, type_mouvement):
        """Ouvre une fenêtre de recherche d'article avec stock filtré par magasin actif."""
        fenetre = ctk.CTkToplevel(self)
        fenetre.title("Rechercher un article")
        fenetre.geometry("1000x600")
        fenetre.grab_set()

        main_frame = ctk.CTkFrame(fenetre)
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
        nom_magasin_courant = (self.combo_mag_sortie.get() if type_mouvement == "sortie" else self.combo_mag_entree.get() or "").strip()
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

        def charger_articles(filtre=""):
            for item in tree.get_children():
                tree.delete(item)

            conn = self.connect_db()
            if not conn:
                return
            try:
                cur = conn.cursor()
                filtre_like = f"%{filtre}%"

                query = """
                WITH mouvements_bruts AS (
                    SELECT lf.idarticle, lf.idmag, COALESCE(u.qtunite, 1) as qtunite_source, lf.qtlivrefrs as quantite, 'reception' as type_mouvement
                    FROM tb_livraisonfrs lf
                    INNER JOIN tb_unite u ON lf.idarticle = u.idarticle AND lf.idunite = u.idunite
                    WHERE lf.deleted = 0
                    UNION ALL
                    SELECT vd.idarticle, v.idmag, COALESCE(u.qtunite, 1) as qtunite_source, vd.qtvente as quantite, 'vente' as type_mouvement
                    FROM tb_ventedetail vd
                    INNER JOIN tb_vente v ON vd.idvente = v.id AND v.deleted = 0 AND v.statut = 'VALIDEE'
                    INNER JOIN tb_unite u ON vd.idarticle = u.idarticle AND vd.idunite = u.idunite
                    WHERE vd.deleted = 0
                    UNION ALL
                    SELECT t.idarticle, t.idmagentree as idmag, COALESCE(u.qtunite, 1) as qtunite_source, t.qttransfert as quantite, 'transfert_in' as type_mouvement
                    FROM tb_transfertdetail t
                    INNER JOIN tb_unite u ON t.idarticle = u.idarticle AND t.idunite = u.idunite
                    WHERE t.deleted = 0
                    UNION ALL
                    SELECT t.idarticle, t.idmagsortie as idmag, COALESCE(u.qtunite, 1) as qtunite_source, t.qttransfert as quantite, 'transfert_out' as type_mouvement
                    FROM tb_transfertdetail t
                    INNER JOIN tb_unite u ON t.idarticle = u.idarticle AND t.idunite = u.idunite
                    WHERE t.deleted = 0
                    UNION ALL
                    SELECT sd.idarticle, sd.idmag, COALESCE(u.qtunite, 1) as qtunite_source, sd.qtsortie as quantite, 'sortie' as type_mouvement
                    FROM tb_sortiedetail sd
                    INNER JOIN tb_unite u ON sd.idarticle = u.idarticle AND sd.idunite = u.idunite
                    UNION ALL
                    SELECT u.idarticle, i.idmag, COALESCE(u.qtunite, 1) as qtunite_source, i.qtinventaire as quantite, 'inventaire' as type_mouvement
                    FROM tb_inventaire i
                    INNER JOIN tb_unite u ON i.codearticle = u.codearticle
                    WHERE u.idunite IN (
                        SELECT DISTINCT ON (idarticle) idunite
                        FROM tb_unite
                        WHERE deleted = 0
                        ORDER BY idarticle, qtunite ASC
                    )
                    UNION ALL
                    SELECT ad.idarticle, ad.idmag, COALESCE(u.qtunite, 1) as qtunite_source, ad.qtavoir as quantite, 'avoir' as type_mouvement
                    FROM tb_avoir a
                    INNER JOIN tb_avoirdetail ad ON a.id = ad.idavoir
                    INNER JOIN tb_unite u ON ad.idarticle = u.idarticle AND ad.idunite = u.idunite
                    WHERE a.deleted = 0 AND ad.deleted = 0
                    UNION ALL
                    SELECT cd.idarticle, cd.idmag, COALESCE(u.qtunite, 1) as qtunite_source, cd.qtconsomme as quantite, 'consommation_interne' as type_mouvement
                    FROM tb_consommationinterne_details cd
                    INNER JOIN tb_unite u ON cd.idarticle = u.idarticle AND cd.idunite = u.idunite
                    UNION ALL
                    SELECT dce.idarticle, dce.idmagasin, COALESCE(u.qtunite, 1) as qtunite_source, dce.quantite_entree as quantite, 'echange_entree' as type_mouvement
                    FROM tb_detailchange_entree dce
                    INNER JOIN tb_unite u ON dce.idarticle = u.idarticle AND dce.idunite = u.idunite
                    UNION ALL
                    SELECT dcs.idarticle, dcs.idmagasin, COALESCE(u.qtunite, 1) as qtunite_source, dcs.quantite_sortie as quantite, 'echange_sortie' as type_mouvement
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
                    GREATEST(COALESCE(sb.solde_base, 0) / NULLIF(COALESCE(uc.coeff_hierarchique, 1), 0), 0) as stock_total,
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

                designationmag = (self.combo_mag_sortie.get() if type_mouvement == "sortie" else self.combo_mag_entree.get() or "").strip()
                idmag_actif = self.magasins.get(designationmag)
                tree.heading("Stock", text=f"Magasin {designationmag}" if designationmag else "Magasin")
                if idmag_actif is None:
                    return

                cur.execute(query, (idmag_actif, filtre_like, filtre_like))
                articles = cur.fetchall()

                for idx, row in enumerate(articles):
                    zebra_tag = "even" if idx % 2 == 0 else "odd"
                    tree.insert('', 'end', values=(
                        row[0],
                        row[1],
                        row[2] or "",
                        row[3] or "",
                        row[4] or "",
                        self.formater_nombre(row[5]),
                        self.formater_nombre(row[6])
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

            idarticle = values[0]
            idunite = values[1]
            codeart = values[2]
            designation = values[3]
            unite = values[4]
            stock = self.parser_nombre(str(values[5]))

            if type_mouvement == "sortie":
                self.article_sortie_selectionne = {
                    'idarticle': idarticle,
                    'idunite': idunite,
                    'designation': designation,
                    'unite': unite,
                    'code': codeart,
                    'stock_disponible': stock
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
                    'code': codeart,
                    'stock_disponible': stock
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

            # Vérifier le stock disponible
            stock_dispo = self.article_sortie_selectionne['stock_disponible']
            if qty > stock_dispo:
                messagebox.showerror("Stock insuffisant", 
                    f"Stock disponible: {self.formater_nombre(stock_dispo)}\n"
                    f"Vous avez demandé: {self.formater_nombre(qty)}")
                return

            magasin = self.combo_mag_sortie.get()
            designation = self.article_sortie_selectionne['designation']
            unite = self.article_sortie_selectionne['unite']
            code = self.article_sortie_selectionne['code']

            self.tree_sortie.insert("", "end", values=(
                code, designation, unite, magasin, self.formater_nombre(qty)
            ))
            self._refresh_table_alternating_colors(self.tree_sortie)

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
            messagebox.showinfo("Succès", f"Article '{designation}' ajouté à la sortie")
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
            self._refresh_table_alternating_colors(self.tree_entree)

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
            messagebox.showinfo("Succès", f"Article '{designation}' ajouté à l'entrée")
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
        self._refresh_table_alternating_colors(self.tree_sortie)
        self.articles_sortie.pop(index)

    def supprimer_article_entree(self):
        """Supprime la ligne sélectionnée de l'entrée"""
        selection = self.tree_entree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Sélectionnez une ligne")
            return

        index = self.tree_entree.index(selection[0])
        self.tree_entree.delete(selection[0])
        self._refresh_table_alternating_colors(self.tree_entree)
        self.articles_entree.pop(index)

    def ouvrir_recherche_changement(self):
        """Ouvre le dialogue pour charger un changement existant"""
        messagebox.showinfo("À venir", "Fonctionnalité de chargement à développer")

    def enregistrer_changement(self):
        """Enregistre le changement en base de données"""
        if not self.articles_sortie or not self.articles_entree:
            messagebox.showwarning("Attention", "Ajoutez au moins un article en sortie et entrée")
            return

        conn = self.connect_db()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            
            # 1. Récupérer la référence depuis entry_ref
            refchg = self.entry_ref.get()
            if not refchg:
                messagebox.showerror("Erreur", "Référence vide")
                return
            
            # 2. Insérer dans tb_changement
            note = self.entry_note.get().strip() if self.entry_note.get() else ""
            
            # ✅ Si description vide, ajouter texte par défaut
            if not note:
                note = "Aucune description"
            
            cursor.execute("""
                INSERT INTO tb_changement (refchg, datechg, iduser, note)
                VALUES (%s, CURRENT_TIMESTAMP, %s, %s)
                RETURNING idchg
            """, (refchg, self.iduser, note))
            
            idchg = cursor.fetchone()[0]
            
            # 3. Insérer les articles en sortie
            for article in self.articles_sortie:
                cursor.execute("""
                    INSERT INTO tb_detailchange_sortie 
                    (idchg, idarticle, idunite, idmagasin, quantite_sortie)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    idchg,
                    article['idarticle'],
                    article['idunite'],
                    article['idmagasin'],
                    article['quantite']
                ))
            
            # 4. Insérer les articles en entrée
            for article in self.articles_entree:
                cursor.execute("""
                    INSERT INTO tb_detailchange_entree 
                    (idchg, idarticle, idunite, idmagasin, quantite_entree)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    idchg,
                    article['idarticle'],
                    article['idunite'],
                    article['idmagasin'],
                    article['quantite']
                ))
            
            conn.commit()
            
            messagebox.showinfo("Succès", 
                              f"Changement enregistré avec succès!\n\n"
                              f"Référence: {refchg}\n"
                              f"Sorties: {len(self.articles_sortie)} articles\n"
                              f"Entrées: {len(self.articles_entree)} articles")
            
            # Générer et imprimer le PDF automatiquement
            self.generer_pdf_changement(refchg, idchg)
            
            # Réinitialiser après enregistrement
            self.articles_sortie = []
            self.articles_entree = []
            self.tree_sortie.delete(*self.tree_sortie.get_children())
            self.tree_entree.delete(*self.tree_entree.get_children())
            self.entry_note.delete(0, "end")  # Vider le champ note
            
            # Générer nouvelle référence
            self.generer_reference()
            
        except psycopg2.Error as e:
            conn.rollback()
            messagebox.showerror("Erreur Base de Données", f"Erreur: {str(e)}")
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur", f"Erreur: {str(e)}")
            print(f"Erreur enregistrement: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()


    def _build_pdf_a5(self, output_path, titre_entete, reference, date_operation, 
                      magasin, operateur, table_data, description, 
                      responsable_1="Magasinier", responsable_2="Responsable Magasin"):
        """
        Construit et génère un PDF au format A5 Landscape selon le modèle redesigné.
        Adapté du modèle EtatsPDF_Mouvements.py
        """
        doc = SimpleDocTemplate(
            output_path,
            pagesize=landscape(A5),
            rightMargin=self.MARGIN,
            leftMargin=self.MARGIN,
            topMargin=self.MARGIN,
            bottomMargin=self.MARGIN
        )
        
        elements = []
        styles = getSampleStyleSheet()
        page_width_usable = self.PAGE_WIDTH - 2*self.MARGIN
        
        # ========== 1. TITRE PRINCIPAL ==========
        main_title = Paragraph(
            "Ankino amin'ny Jehovah ny asanao dia ho lavorary izay kasainao",
            ParagraphStyle(
                'MainTitle',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.black,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold',
                spaceAfter=3
            )
        )
        
        title_table = Table([[main_title]], colWidths=[page_width_usable])
        title_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ]))
        elements.append(title_table)
        
        # ========== 2. EN-TÊTE: SOCIÉTÉ + OPÉRATION ==========
        societe = self._get_societe_info()
        
        nomsociete = societe.get('nomsociete', 'N/A')
        adressesociete = societe.get('adressesociete') or 'Adresse Non Configurée'
        villesociete = societe.get('villesociete') or ''
        contactsociete = societe.get('contactsociete') or 'Contact: Non Configuré'
        nifsociete = societe.get('nifsociete') or 'NIF: Non Configuré'
        statsociete = societe.get('statsociete') or 'STAT: Non Configurée'
        
        villes_line = f"Ville : {villesociete}<br/>" if villesociete else ""
        
        company_width = page_width_usable * 0.33
        header_height = 28 * mm
       
        company_details = Paragraph(
            f"<b>{nomsociete}</b><br/>"
            f"Adresse : {adressesociete}<br/>"
            f"{villes_line}"
            f"Contact : {contactsociete}<br/>"
            f"NIF : {nifsociete}<br/>"
            f"STAT : {statsociete}<br/>",
            ParagraphStyle(
                'CompanyDetails',
                parent=styles['Normal'],
                fontSize=9,
                alignment=TA_LEFT,
                leading=12
            )
        )
        
        company_data = [[company_details]]
        company_table = Table(company_data, colWidths=[company_width - 2*mm], rowHeights=[header_height])
        company_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, self.COLOR_BORDER),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('VALIGN', (0, 0), (0, 0), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        operation_width = page_width_usable * 0.67 - 2*mm
        title_width = operation_width * 0.55
        info_width = operation_width * 0.45
        
        operation_title = Paragraph(
            titre_entete,
            ParagraphStyle(
                'OpTitle',
                parent=styles['Normal'],
                fontSize=14,
                fontName='Helvetica-Bold',
                alignment=TA_CENTER,
                textColor=self.COLOR_HEADER
            )
        )
        
        operation_info = Paragraph(
            f"<b>Référence :</b> {reference}<br/>"
            f"<b>Date et heure:</b> {date_operation} {datetime.now().strftime('%H:%M')}<br/>"
            f"<b>Magasin :</b> {magasin}<br/>"
            f"<b>Opérateur :</b> {operateur}",
            ParagraphStyle(
                'OpInfo',
                parent=styles['Normal'],
                fontSize=9,
                alignment=TA_LEFT,
                leading=12
            )
        )
        
        operation_data = [[operation_title, operation_info]]
        operation_table = Table(operation_data, colWidths=[title_width, info_width], rowHeights=[header_height])
        operation_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, self.COLOR_BORDER),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('ALIGN', (1, 0), (1, 0), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        header_data = [[company_table, operation_table]]
        header_table = Table(header_data, colWidths=[company_width, operation_width])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LINELEFT', (0, 0), (0, 0), 1, self.COLOR_BORDER),
            ('LINERIGHT', (0, 0), (0, 0), 1, self.COLOR_BORDER),
            ('LINELEFT', (1, 0), (1, 0), 1, self.COLOR_BORDER),
            ('LINERIGHT', (1, 0), (1, 0), 1, self.COLOR_BORDER),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), -2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (0, 0), 8),
            ('LEFTPADDING', (1, 0), (1, 0), 8),
        ]))
        
        elements.append(header_table)
        elements.append(Spacer(1, 4*mm))
        
        # ========== 3. TABLEAU ARTICLES ==========
        if table_data:
            columns, data_rows = table_data
            
            def calculate_column_widths(columns, data_rows, total_width):
                num_cols = len(columns)
                col_lengths = [len(str(col)) for col in columns]
                
                for row_data in data_rows:
                    for i, cell in enumerate(row_data):
                        col_lengths[i] = max(col_lengths[i], len(str(cell or '')))
                
                total_length = sum(col_lengths) if sum(col_lengths) > 0 else num_cols
                col_ratios = [length / total_length for length in col_lengths]
                
                min_col_width = 15 * mm
                available_width = total_width - (min_col_width * num_cols)
                
                col_widths = []
                for ratio in col_ratios:
                    width = min_col_width + (available_width * ratio)
                    col_widths.append(width)
                
                return col_widths
            
            table_width = page_width_usable * 0.95
            col_widths = calculate_column_widths(columns, data_rows, table_width)
            
            cell_style = ParagraphStyle(
                'CellText',
                parent=styles['Normal'],
                fontSize=8,
                alignment=TA_LEFT,
                wordWrap='CJK'
            )
            
            table_rows = []
            header_row = [Paragraph(str(col), cell_style) for col in columns]
            table_rows.append(header_row)
            
            for row_data in data_rows:
                cell_row = [Paragraph(str(cell or ''), cell_style) for cell in row_data]
                table_rows.append(cell_row)
            
            articles_table = Table(table_rows, colWidths=col_widths, repeatRows=1)
            
            table_style_commands = [
                ('BACKGROUND', (0, 0), (-1, 0), self.COLOR_BG_TABLE_HEADER),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 5),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                ('ALIGN', (0, 1), (1, -1), 'LEFT'),
                ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 1), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 1), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
                ('LEFTPADDING', (0, 1), (-1, -1), 3),
                ('RIGHTPADDING', (0, 1), (-1, -1), 3),
                ('BOX', (0, 0), (-1, -1), 1, self.COLOR_BORDER),
            ]
            
            for col_idx in range(1, len(columns)):
                table_style_commands.append(
                    ('LINEBEFORE', (col_idx, 0), (col_idx, -1), 1, self.COLOR_HEADER)
                )
            
            articles_table.setStyle(TableStyle(table_style_commands))
            
            elements.append(articles_table)
            elements.append(Spacer(1, 3*mm))
        
        # ========== 4. DESCRIPTION ==========
        if description:
            desc_line = Paragraph(
                f"<b>&nbsp;&nbsp;&nbsp;<u>Description: </u></b> {description}<br/><br/>",
                ParagraphStyle(
                    'Description',
                    parent=styles['Normal'],
                    fontSize=9,
                    alignment=TA_LEFT,
                    leading=10
                )
            )
            elements.append(desc_line)
        
        # ========== 5. SIGNATURES ==========
        sig_left_1 = Paragraph(responsable_1, ParagraphStyle(
            'SigLabel1',
            parent=styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER
        ))
        
        sig_right = Paragraph(responsable_2, ParagraphStyle(
            'SigLabelRight',
            parent=styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER
        ))
        
        sig_container = Table(
            [
                [sig_left_1, '', sig_right]
            ],
            colWidths=[
                page_width_usable * 0.33 - 2*mm,
                page_width_usable * 0.33 - 2*mm,
                page_width_usable * 0.33 - 2*mm
            ]
        )
        sig_container.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('ALIGN', (0, 0), (0, 1), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ]))
        
        elements.append(sig_container)
        
        # Générer le PDF
        try:
            doc.build(elements)
            print(f"✅ PDF généré avec succès: {output_path}")
            
            # Ouvrir le fichier
            if sys.platform == 'win32':
                os.startfile(output_path)
            
            return output_path
            
        except Exception as e:
            print(f"❌ Erreur sauvegarde PDF : {e}")
            messagebox.showerror("Erreur", f"Erreur lors de la génération du PDF: {str(e)}")
            return None

    def generer_pdf_changement(self, refchg, idchg):
        """Génère un PDF Changement au format A5 Landscape en utilisant le modèle _build_pdf_a5"""
        try:
            filename = f"Changement_{refchg}.pdf"
            
            # Récupérer info utilisateur
            conn = self.connect_db()
            username = "Utilisateur"
            
            if conn:
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT username FROM tb_users WHERE iduser = %s", (self.iduser,))
                    user_res = cur.fetchone()
                    username = user_res[0] if user_res else "Utilisateur"
                    cur.close()
                except:
                    pass
                finally:
                    conn.close()
            
            # Préparer les données pour le tableau
            # Combiner sorties et entrées
            colonnes = ("Code", "Désignation", "Unité", "Quantité", "Type")
            data_rows = []
            
            # Ajouter articles en sortie
            for art in self.articles_sortie:
                data_rows.append((
                    art.get('code', ''),
                    art.get('designation', ''),
                    art.get('unite', ''),
                    str(art.get('quantite', 0)),
                    'SORTIE'
                ))
            
            # Ajouter articles en entrée
            for art in self.articles_entree:
                data_rows.append((
                    art.get('code', ''),
                    art.get('designation', ''),
                    art.get('unite', ''),
                    str(art.get('quantite', 0)),
                    'ENTREE'
                ))
            
            table_data = (colonnes, data_rows)
            
            # Description
            description = self.entry_note.get().strip() or "Changement d'articles"
            
            # Générer le PDF
            magasin_sortie = (self.combo_mag_sortie.get() or "").strip()
            return self._build_pdf_a5(
                filename,
                "CHANGEMENT D'ARTICLES",
                refchg,
                datetime.now().strftime("%d/%m/%Y"),
                magasin_sortie,
                username,
                table_data,
                description,
                "Magasinier",
                "Responsable Magasin"
            )
            
        except Exception as e:
            print(f"❌ Erreur PDF: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Erreur", f"Erreur génération PDF: {str(e)}")
            return None


    def imprimer_changement(self):
        """Imprime le changement"""
        if not self.articles_sortie and not self.articles_entree:
            messagebox.showwarning("Attention", "Aucun article à imprimer")
            return

        # Récupérer la référence
        refchg = self.entry_ref.get()
        if refchg:
            self.generer_pdf_changement(refchg, None)
        else:
            messagebox.showwarning("Attention", "Référence requise pour imprimer")



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
        self.show_page("🧾 Bon de commande")
    
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
        self.sidebar.grid_rowconfigure(6, weight=1)
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
            ("🧾 Bon de commande", "PageCommandeFrs"),
            ("📥 Bon de réception", "PageBonReception"),
            ("🔄 Transferts", "PageTransfert"),
            ("📤 Sortie/Consommation", "PageSortie"),
            ("🔁 Changements", "PageChangementArticle")
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
        
        if menu_name == "📤 Sortie/Consommation":
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
            "🧾 Bon de commande": PageCommandeFrs,
            "📥 Bon de réception": PageBonReception,
            "🔄 Transferts": PageTransfert,
            "📤 Sortie/Consommation": PageSortie,
            "🔁 Changements": PageChangementArticle
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
