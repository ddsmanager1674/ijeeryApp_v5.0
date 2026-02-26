import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import json
from datetime import datetime
from html import escape
from math import floor
from resource_utils import get_config_path, safe_file_read


# --- IMPORTS REPORTLAB POUR PDF ---
from reportlab.lib.pagesizes import A5
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph

# ==============================================================================
# FONCTION UTILITAIRE : CONVERSION NOMBRE EN LETTRES (FRANÇAIS)
# ==============================================================================

def nombre_en_lettres_fr(montant: float) -> str:
    """
    Convertit un montant numérique en sa représentation en lettres en français.
    Gère les Millions et les Milliers correctement.
    """
    
    if montant is None: return ""
    
    try:
        montant = round(float(montant), 2)
    except ValueError:
        return ""

    unites = ["", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf"]
    dix_a_dixneuf = ["dix", "onze", "douze", "treize", "quatorze", "quinze", "seize"]
    dizaines = ["", "dix", "vingt", "trente", "quarante", "cinquante", "soixante", "soixante", "quatre-vingt", "quatre-vingt"]
    
    def convertir_nombre_simple(n):
        if n == 0: return ""
        texte = []
        
        # Unités (0-9)
        if n < 10:
            texte.append(unites[n])
        # 10-16
        elif n < 17:
            texte.append(dix_a_dixneuf[n - 10])
        # 17-19
        elif n < 20:
            texte.append("dix-" + unites[n - 10])
        # 20-99 (simplifié)
        elif n < 100:
            d = n // 10
            u = n % 10
            
            partie_dizaine = dizaines[d]
            if (d == 2 or d > 6) and u == 1: # 21, 71, 91 (simplifié)
                 partie_dizaine += " et"
            
            texte.append(partie_dizaine)
            if u > 0:
                if d == 7 or d == 9: # 70-79, 90-99
                    texte.append("-" + convertir_nombre_simple(n - (d * 10)))
                else:
                    texte.append("-" + unites[u])
        
        return "".join(texte).replace("--", "-") # Corrige double trait d'union

    def convertir_bloc(n):
        if n == 0: return ""
        if n < 100: return convertir_nombre_simple(n)
        
        texte = []
        c = n // 100
        r = n % 100
        
        if c == 1: texte.append("cent")
        else: 
            texte.append(convertir_nombre_simple(c) + "-cent")
            if r == 0: texte[-1] += "s" # Quatre-cents
        
        if r > 0:
            texte.append("-" + convertir_bloc(r))

        return "".join(texte).replace("un-cent", "cent") # Corrige 'un-cent' -> 'cent'
    
    entier = floor(montant)
    centimes = int(round((montant - entier) * 100))
    
    # ====================================================================
    # Gestion des blocs Millions, Milliers, Unités
    # ====================================================================
    million = entier // 1_000_000
    mille_reste = (entier % 1_000_000) // 1_000 
    reste_unites = entier % 1_000 
    
    resultat = []
    
    # 1. MILLIONS
    if million > 0:
        lettres_million = convertir_bloc(million)
        bloc_million = "million"
        if million > 1: bloc_million += "s"
        resultat.append(f"{lettres_million} {bloc_million}")
    
    # 2. MILLIERS (0 à 999)
    if mille_reste > 0:
        lettres_mille = convertir_bloc(mille_reste)
        resultat.append(f"{lettres_mille} mille")
    
    # 3. UNITÉS (0 à 999)
    if reste_unites > 0:
        resultat.append(convertir_bloc(reste_unites))
    
    # 4. CAS SPECIAL: ZÉRO
    if entier == 0 and centimes == 0 and not resultat:
        resultat.append("zéro")

    
    # Monnaie
    result_str = " ".join(resultat).strip().replace("  ", " ").replace("-", " ") 
    if not result_str: result_str = "zéro"
    
    unite_monetaire = "Ariary"
    result_str += " " + unite_monetaire
    
    # Centimes
    if centimes > 0:
        centime_lettres = convertir_bloc(centimes)
        centime_monetaire = "centimes"
        centime_lettres = centime_lettres.replace("-", " ")
        result_str += " et " + centime_lettres + " " + centime_monetaire

    return result_str.capitalize().replace(" et-", " et ")

class PageCommandeCli(ctk.CTkFrame):
    def __init__(self, parent, iduser):
        super().__init__(parent)
        self.iduser = iduser
        self.article_selectionne = None
        self.items_commande = []
        
        # Variable pour stocker l'ID de la commande en mode modification
        self.idprof_charge = None
        self.mode_modification = False
        
        # Index de la ligne sélectionnée pour modification
        self.index_ligne_selectionnee = None
        
        self.setup_ui()
        self.generer_reference()
        self.charger_Clients()
    
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
        
    def setup_ui(self):
        # Titre
        self.titre = ctk.CTkLabel(self, text="Nouvelle Commande Clients", 
                            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"))
        self.titre.pack(pady=10)
        
        # Frame en haut pour référence et Client
        frame_haut = ctk.CTkFrame(self)
        frame_haut.pack(fill="x", padx=20, pady=10)
        
        # Référence
        ctk.CTkLabel(frame_haut, text="Référence:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.entry_ref = ctk.CTkEntry(frame_haut, width=200, state="readonly")
        self.entry_ref.grid(row=0, column=1, padx=10, pady=10)
        
        # Client
        ctk.CTkLabel(frame_haut, text="Client:").grid(row=0, column=2, padx=10, pady=10, sticky="w")
        self.entry_client = ctk.CTkEntry(frame_haut, width=300, placeholder_text="Entrez le nom du client...")
        self.entry_client.grid(row=0, column=3, padx=10, pady=10)
        
        # Bouton pour rechercher un client existant
        self.btn_rechercher_client = ctk.CTkButton(frame_haut, text="🔍 Rechercher", width=120, 
                                                    command=self.ouvrir_recherche_client)
        self.btn_rechercher_client.grid(row=0, column=4, padx=(5, 0), pady=10)
        
        # Variables pour stocker les infos du client sélectionné
        self.client_selectionne_id = None
        
        # Bouton Charger Proforma (pour la modification)
        btn_charger = ctk.CTkButton(frame_haut, text="📂 Charger Proforma", 
                                    command=self.ouvrir_recherche_commande, width=150,
                                    fg_color="#1976d2", hover_color="#1565c0")
        btn_charger.grid(row=0, column=5, padx=10, pady=10)
        
        # Bouton Actualiser les prix
        self.btn_actualiser_prix = ctk.CTkButton(frame_haut, text="💰 Actualiser Prix", 
                                    command=self.actualiser_tous_les_prix, width=150,
                                    fg_color="#f57c00", hover_color="#e65100")
        self.btn_actualiser_prix.grid(row=0, column=6, padx=10, pady=10)
        self.btn_actualiser_prix.grid_remove()  # Caché par défaut
        
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
        
        # Quantité proforma
        ctk.CTkLabel(frame_milieu, text="Quantité proforma:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.entry_qtprof = ctk.CTkEntry(frame_milieu, width=150)
        self.entry_qtprof.grid(row=2, column=1, padx=10, pady=10, sticky="w")
        
        # Prix Unitaire
        ctk.CTkLabel(frame_milieu, text="Prix Unitaire:").grid(row=2, column=2, padx=10, pady=10, sticky="w")
        self.entry_prixunit = ctk.CTkEntry(frame_milieu, width=150)
        self.entry_prixunit.grid(row=2, column=3, padx=10, pady=10, sticky="w")
        
        # Quantité Livrée
        ctk.CTkLabel(frame_milieu, text="Quantité Livrée:").grid(row=3, column=0, padx=10, pady=10, sticky="w")
        self.entry_qtlivprof = ctk.CTkEntry(frame_milieu, width=150)
        self.entry_qtlivprof.insert(0, "0")
        self.entry_qtlivprof.grid(row=3, column=1, padx=10, pady=10, sticky="w")
        
        # Frame pour les boutons Ajouter et Modifier Ligne
        frame_btn_article = ctk.CTkFrame(frame_milieu, fg_color="transparent")
        frame_btn_article.grid(row=3, column=2, columnspan=2, padx=10, pady=10, sticky="w")
        
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
        colonnes = ("Article", "Unité", "Qté Prof", "Prix Unit.", "Qté Livrée", "Total")
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
                                     command=self.imprimer_proforma,
                                     fg_color="#ff6f00", hover_color="#e65100")
        btn_imprimer.pack(side="right", padx=10)
        
        btn_enregistrer = ctk.CTkButton(frame_boutons, text="💾 Enregistrer", 
                                        command=self.enregistrer_proforma,
                                        fg_color="#2e7d32", hover_color="#1b5e20")
        btn_enregistrer.pack(side="right", padx=10)
        
        # Label total
        self.label_total = ctk.CTkLabel(frame_boutons, text="Total: 0,00", 
                                       font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"))
        self.label_total.pack(side="right", padx=20)
    
    # ==================== NOUVELLES FONCTIONS: Sélection et modification de ligne ====================
    
    def on_selection_ligne(self, event):
        """Appelé quand une ligne est sélectionnée dans le Treeview"""
        selection = self.tree.selection()
        if selection:
            # Activer les boutons
            self.btn_modifier_ligne.configure(state="normal")
            self.btn_annuler_selection.configure(state="normal")
    
    # Suppression de la fonction update_date_modification (obsolète après la modification de enregistrer_proforma)
    
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
        
        # ATTENTION : Utilisation des clés internes ('qtprof', 'prixunit', 'qtlivprof')
        # qui doivent être les mêmes que celles utilisées dans charger_commande
        self.entry_qtprof.delete(0, "end")
        self.entry_qtprof.insert(0, self.formater_nombre(item_data['qtprof']))
        
        self.entry_prixunit.delete(0, "end")
        self.entry_prixunit.insert(0, self.formater_nombre(item_data['prixunit']))
        
        self.entry_qtlivprof.delete(0, "end")
        self.entry_qtlivprof.insert(0, self.formater_nombre(item_data['qtlivprof']))
        
        # Stocker l'article sélectionné pour la modification
        self.article_selectionne = {
            'idarticle': item_data['idarticle'],
            'idunite': item_data['idunite'],
            'nomart': values[0],
            'unite': values[1]
        }
        
        # Changer l'état des boutons
        self.btn_ajouter.configure(state="disabled")
        self.btn_modifier_ligne.configure(state="normal", text="✅ Valider Modif.")
        self.btn_annuler_selection.configure(state="normal")
        
        # Mettre en surbrillance visuelle
        self.titre.configure(text=f"⚠️ Modification de la ligne {index + 1}")
    
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
            qtprof = self.parser_nombre(self.entry_qtprof.get())
            prixunit = self.parser_nombre(self.entry_prixunit.get())
            qtlivprof = self.parser_nombre(self.entry_qtlivprof.get())
            
            if qtprof <= 0:
                messagebox.showwarning("Attention", "La quantité commandée doit être supérieure à 0")
                return
            
            total = qtprof * prixunit
            index = self.index_ligne_selectionnee
            
            # Mettre à jour les données DANS self.items_commande
            self.items_commande[index]['qtprof'] = qtprof
            self.items_commande[index]['prixunit'] = prixunit
            self.items_commande[index]['qtlivprof'] = qtlivprof
            self.items_commande[index]['total'] = total # Ajout de la mise à jour du total
            # ✅ S'assurer que designation et designationunite sont présents
            self.items_commande[index]['designation'] = self.article_selectionne['nomart']
            self.items_commande[index]['designationunite'] = self.article_selectionne['unite']
            
            # Mettre à jour le Treeview
            item_id = self.tree.get_children()[index]
            self.tree.item(item_id, values=(
                self.article_selectionne['nomart'],
                self.article_selectionne['unite'],
                self.formater_nombre(qtprof),
                self.formater_nombre(prixunit),
                self.formater_nombre(qtlivprof),
                self.formater_nombre(total)
            ))

            # L'appel à update_date_modification est supprimé car la date et le statut
            # seront mis à jour dans enregistrer_proforma lors de la sauvegarde complète.

            # Réinitialiser l'état
            self.annuler_selection_ligne()
            self.calculer_total()
            
            messagebox.showinfo("Succès", "Ligne modifiée avec succès! (N'oubliez pas d'enregistrer la commande)")
            
        except ValueError:
            messagebox.showerror("Erreur", "Veuillez entrer des valeurs numériques valides")
    
    def annuler_selection_ligne(self):
        """Annule la sélection et réinitialise les champs"""
        self.index_ligne_selectionnee = None
        self.article_selectionne = None
        
        # Réinitialiser les champs
        self.entry_article.configure(state="normal")
        self.entry_article.delete(0, "end")
        self.entry_article.configure(state="readonly")
        
        self.entry_unite.configure(state="normal")
        self.entry_unite.delete(0, "end")
        self.entry_unite.configure(state="readonly")
        
        self.entry_qtprof.delete(0, "end")
        self.entry_prixunit.delete(0, "end")
        self.entry_qtlivprof.delete(0, "end")
        self.entry_qtlivprof.insert(0, "0")
        
        # Réinitialiser les boutons
        self.btn_ajouter.configure(state="normal")
        self.btn_modifier_ligne.configure(state="disabled", text="✏️ Modifier Ligne")
        self.btn_annuler_selection.configure(state="disabled")
        
        # Désélectionner dans le Treeview
        self.tree.selection_remove(self.tree.selection())
        
        # Réinitialiser le titre
        if self.mode_modification and self.idprof_charge:
            self.titre.configure(text=f"Modification Commande: {self.entry_ref.get()}")
        else:
            # CORRECTION DU TITRE : Utilisation du nom de la classe
            self.titre.configure(text="Nouvelle Commande Clients")
    
    # ==================== FIN NOUVELLES FONCTIONS ====================
    
    def generer_reference(self):
        """Génère la référence automatique au format 2025-BC-00001"""
        conn = self.connect_db()
        if not conn:
            return
            
        try:
            cursor = conn.cursor()
            annee_courante = datetime.now().year
            
            query = """
                SELECT refprof FROM tb_proforma 
                WHERE refprof LIKE %s 
                ORDER BY refprof DESC LIMIT 1
            """
            cursor.execute(query, (f"{annee_courante}-PRO-%",))
            resultat = cursor.fetchone()
            
            if resultat:
                # Extraire le numéro après "PRO-"
                dernier_num = int(resultat[0].split('-')[-1])
                nouveau_num = dernier_num + 1
            else:
                nouveau_num = 1
            
            reference = f"{annee_courante}-PRO-{nouveau_num:05d}"
            self.entry_ref.configure(state="normal")
            self.entry_ref.delete(0, "end")
            self.entry_ref.insert(0, reference)
            self.entry_ref.configure(state="readonly")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la génération de la référence: {str(e)}")
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()
    
    def charger_Clients(self):
        """Charge la liste des clients"""
        conn = self.connect_db()
        if not conn:
            return
            
        try:
            cursor = conn.cursor()
            query = "SELECT idclient, nomcli FROM tb_client WHERE deleted = 0 ORDER BY nomcli"
            cursor.execute(query)
            
            self.clients = {row[1]: row[0] for row in cursor.fetchall()}
            
            if self.clients:
                self.entry_client.delete(0, "end"); self.entry_client.insert(0, list(self.clients.keys())[0])
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des clients: {str(e)}")
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()

    
    def recuperer_dernier_prix(self, idarticle):
        """
        Récupère le dernier prix d'un article depuis la table tb_prix
        en fonction de l'idarticle
        Retourne le prix (float) ou None si aucun prix n'est trouvé
        """
        conn = self.connect_db()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            # Requête pour récupérer le dernier prix de l'article
            # Tri par date décroissante (ou par ID si pas de date) pour avoir le plus récent
            query = """
                SELECT prix
                FROM tb_prix 
                WHERE idarticle = %s 
                ORDER BY id DESC 
                LIMIT 1
            """
            cursor.execute(query, (idarticle,))
            resultat = cursor.fetchone()
            
            if resultat and resultat[0] is not None:
                return float(resultat[0])
            else:
                return None
                
        except Exception as e:
            print(f"Erreur lors de la récupération du prix: {e}")
            return None
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def actualiser_tous_les_prix(self):
        """
        Actualise tous les prix des articles de la proforma en cours
        avec les derniers prix de la table tb_prix
        """
        if not self.items_commande:
            messagebox.showwarning("Attention", "Aucun article dans la proforma.")
            return
        
        # Demander confirmation
        reponse = messagebox.askyesno(
            "Actualiser les prix",
            f"Cette action va remplacer tous les prix actuels par les derniers prix de la table tb_prix.\n\n"
            f"Nombre d'articles à actualiser: {len(self.items_commande)}\n\n"
            "Voulez-vous continuer?"
        )
        
        if not reponse:
            return
        
        nb_prix_actualises = 0
        nb_prix_non_trouves = 0
        details_actualisation = []
        
        # Parcourir tous les articles
        for i, item in enumerate(self.items_commande):
            idarticle = item['idarticle']
            ancien_prix = item['prixunit']
            
            # Récupérer le dernier prix
            nouveau_prix = self.recuperer_dernier_prix(idarticle)
            
            if nouveau_prix is not None and nouveau_prix != ancien_prix:
                # Mettre à jour le prix dans la liste
                self.items_commande[i]['prixunit'] = nouveau_prix
                nb_prix_actualises += 1
                
                details_actualisation.append(
                    f"• {item['designation']}: {self.formater_nombre(ancien_prix)} → {self.formater_nombre(nouveau_prix)} Ar"
                )
            elif nouveau_prix is None:
                nb_prix_non_trouves += 1
                details_actualisation.append(
                    f"⚠ {item['designation']}: Aucun prix trouvé dans tb_prix"
                )
        
        # Rafraîchir l'affichage du Treeview
        self.tree.delete(*self.tree.get_children())
        for item in self.items_commande:
            total_ligne = item['qtprof'] * item['prixunit']
            self.tree.insert("", "end", values=(
                item.get('designation', 'N/A'),
                item.get('designationunite', 'N/A'),
                self.formater_nombre(item['qtprof']),
                self.formater_nombre(item['prixunit']),
                self.formater_nombre(item.get('qtlivprof', 0)),
                self.formater_nombre(total_ligne)
            ))
        
        # Afficher le résultat
        message = f"Actualisation terminée:\n\n"
        message += f"✅ Prix actualisés: {nb_prix_actualises}\n"
        message += f"⚠️ Prix non trouvés: {nb_prix_non_trouves}\n\n"
        
        if details_actualisation:
            message += "Détails:\n" + "\n".join(details_actualisation[:10])  # Limiter à 10 lignes
            if len(details_actualisation) > 10:
                message += f"\n... et {len(details_actualisation) - 10} autre(s)"
        
        messagebox.showinfo("Actualisation des prix", message)
    
    def ouvrir_recherche_client(self):
        """Ouvre une fenêtre de dialogue pour rechercher et sélectionner un client"""
        if not self.clients:
            messagebox.showwarning("Attention", "Aucun client disponible. Veuillez créer des clients d'abord.")
            return
        
        # Créer une fenêtre de dialogue
        dialog = ctk.CTkToplevel(self)
        dialog.title("Rechercher un client")
        dialog.geometry("600x400")
        dialog.transient(self)
        dialog.grab_set()
        
        # Frame de recherche
        frame_recherche = ctk.CTkFrame(dialog)
        frame_recherche.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(frame_recherche, text="Rechercher:").pack(side="left", padx=5)
        entry_recherche = ctk.CTkEntry(frame_recherche, width=300)
        entry_recherche.pack(side="left", padx=5)
        
        # Frame pour la liste
        frame_liste = ctk.CTkFrame(dialog)
        frame_liste.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Créer le Treeview
        columns = ("ID", "Nom")
        tree = ttk.Treeview(frame_liste, columns=columns, show="headings", height=10)
        tree.heading("ID", text="ID")
        tree.heading("Nom", text="Nom du Client")
        tree.column("ID", width=80)
        tree.column("Nom", width=400)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(frame_liste, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Fonction pour remplir la liste
        def remplir_liste(filtre=""):
            tree.delete(*tree.get_children())
            for nom, idclient in self.clients.items():
                if filtre.lower() in nom.lower():
                    tree.insert("", "end", values=(idclient, nom))
        
        # Fonction de recherche
        def rechercher(*args):
            remplir_liste(entry_recherche.get())
        
        entry_recherche.bind("<KeyRelease>", rechercher)
        
        # Fonction de sélection
        def selectionner_client():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Attention", "Veuillez sélectionner un client.")
                return
            
            item = tree.item(selection[0])
            idclient = item['values'][0]
            nom_client = item['values'][1]
            
            # Mettre à jour le champ client
            self.entry_client.delete(0, "end")
            self.entry_client.insert(0, nom_client)
            self.client_selectionne_id = idclient
            
            dialog.destroy()
        
        # Double-clic pour sélectionner
        tree.bind("<Double-Button-1>", lambda e: selectionner_client())
        
        # Frame des boutons
        frame_boutons = ctk.CTkFrame(dialog)
        frame_boutons.pack(fill="x", padx=20, pady=10)
        
        btn_selectionner = ctk.CTkButton(frame_boutons, text="Sélectionner", command=selectionner_client)
        btn_selectionner.pack(side="left", padx=5)
        
        btn_annuler = ctk.CTkButton(frame_boutons, text="Annuler", command=dialog.destroy)
        btn_annuler.pack(side="left", padx=5)
        
        # Remplir la liste initialement
        remplir_liste()
        
        # Focus sur le champ de recherche
        entry_recherche.focus()

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
        entry_search = ctk.CTkEntry(search_frame, placeholder_text="Référence ou client...", width=300)
        entry_search.pack(side="left", padx=5, fill="x", expand=True)
        
        tree_frame = ctk.CTkFrame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        colonnes = ("ID", "Référence", "Date", "Client", "Description", "Statut")
        tree = ttk.Treeview(tree_frame, columns=colonnes, show='headings', height=12)
        
        tree.heading("ID", text="ID")
        tree.heading("Référence", text="Référence")
        tree.heading("Date", text="Date")
        tree.heading("Client", text="Client")
        tree.heading("Description", text="Description")
        tree.heading("Statut", text="Statut")
        
        tree.column("ID", width=0, stretch=False)
        tree.column("Référence", width=120, anchor='w')
        tree.column("Date", width=100, anchor='w')
        tree.column("Client", width=200, anchor='w')
        tree.column("Description", width=250, anchor='w')
        tree.column("Statut", width=100, anchor='center')
        
        # Style pour les tags
        style = ttk.Style()
        style.configure("Treeview", rowheight=22, background="#FFFFFF", foreground="#000000", fieldbackground="#FFFFFF", borderwidth=0, font=('Segoe UI', 8))
        style.configure("Treeview.Heading", background="#E8E8E8", foreground="#000000", font=('Segoe UI', 8, 'bold'))
        tree.tag_configure('incomplet', background='#ffcccc')  # Rouge clair pour incomplet
        tree.tag_configure('complet', background='#ccffcc')    # Vert clair pour complet
        
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
                # --- MODIFICATION DE LA REQUÊTE : Sélection du statut stocké dans tb_proforma ---
                query = """
                    SELECT p.idprof, p.refprof, p.dateprof, c.nomcli, p.observation, p.statut
                    FROM tb_proforma p
                    LEFT JOIN tb_client c ON p.idclient = c.idclient
                    WHERE p.deleted = 0
                """
                # -----------------------------------------------------------------------
                params = []
                if filtre:
                    query += """ AND (
                        LOWER(p.refprof) LIKE LOWER(%s) OR 
                        LOWER(c.nomcli) LIKE LOWER(%s)
                    )"""
                    params = [f"%{filtre}%", f"%{filtre}%"]
                
                query += " ORDER BY p.dateprof DESC, p.refprof DESC"
                cursor.execute(query, params)
                resultats = cursor.fetchall()
                
                for row in resultats:
                    # row[5] est maintenant le statut stocké (p.statut)
                    idprof, refprof, dateprof, nomcli, observation, statut_db = row
                    
                    date_str = dateprof.strftime("%d/%m/%Y") if dateprof else ""
                    
                    # Déterminer le statut et le tag à partir de la valeur stockée
                    if statut_db == "✅ A facturer":
                        statut = statut_db
                        tag = 'complet'
                    else:
                        statut = statut_db if statut_db else "⚠️ En attente" # Utilise "⚠️ En attente" si null (ancienne entrée)
                        tag = 'incomplet'
                        
                    tree.insert('', 'end', 
                              values=(idprof, refprof, date_str, nomcli or "", observation or "", statut),
                              tags=(tag,))
                
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
        
        btn_valider = ctk.CTkButton(main_frame, text="Charger la commande", 
                                    command=valider_selection, 
                                    fg_color="#2e7d32", hover_color="#1b5e20")
        btn_valider.pack(pady=10)
        
        charger_commandes()
    
    def charger_commande(self, idprof):
        """Charge les détails d'une commande existante pour modification"""
        conn = self.connect_db()
        if not conn:
            return
            
        try:
            cursor = conn.cursor()
            
            # Récupérer les données de la commande principale
            query_commande = """
                SELECT p.idprof, p.refprof, p.dateprof, p.idclient, c.nomcli, p.observation
                FROM tb_proforma p
                LEFT JOIN tb_client c ON p.idclient = c.idclient
                WHERE p.idprof = %s AND p.deleted = 0
            """
            cursor.execute(query_commande, (idprof,))
            commande = cursor.fetchone()
            
            if not commande:
                messagebox.showerror("Erreur", "Commande non trouvée")
                return
            
            # Récupérer les détails de la commande
            query_details = """
                SELECT pd.id, pd.idarticle, a.designation, u.designationunite, pd.idunite, pd.qtprof, pd.qtlivprof, pd.prixunit
                FROM tb_proformadetail pd
                INNER JOIN tb_article a ON pd.idarticle = a.idarticle
                INNER JOIN tb_unite u ON pd.idunite = u.idunite
                WHERE pd.idprof = %s
            """
            cursor.execute(query_details, (idprof,))
            details = cursor.fetchall()
            
            # 1. Réinitialiser et préparer l'interface
            self.reinitialiser_formulaire(generer_ref=False)
            self.mode_modification = True
            self.idprof_charge = idprof
            self.titre.configure(text=f"Modification Commande: {commande[1]}")
            
            # Afficher le bouton d'actualisation des prix en mode modification
            self.btn_actualiser_prix.grid()
            
            # 2. Remplir les champs principaux
            self.entry_ref.configure(state="normal")
            self.entry_ref.delete(0, "end")
            self.entry_ref.insert(0, commande[1])
            self.entry_ref.configure(state="readonly")
            
            if commande[4]:
                self.entry_client.delete(0, "end"); self.entry_client.insert(0, commande[4])
            
            # 3. Remplir le Treeview et la liste interne
            for detail in details:
                # detail: (idprofdetail, idarticle, designation, unite_designation, idunite, qtprof, qtlivprof, prixunit)
                idprofdetail, idarticle, designation, unite_designation, idunite, qtprof, qtlivprof, prixunit = detail
                
                prixunit = prixunit if prixunit is not None else 0 # Assurer une valeur numérique
                qtprof = qtprof if qtprof is not None else 0
                qtlivprof = qtlivprof if qtlivprof is not None else 0
                total = qtprof * prixunit
                
                # Ajout des données à la liste interne
                self.items_commande.append({
                    'idprofdetail': idprofdetail,
                    'idarticle': idarticle,
                    'idunite': idunite,
                    'designation': designation,  # ✅ AJOUT
                    'designationunite': unite_designation,  # ✅ AJOUT 
                    'qtprof': qtprof,
                    'qtlivprof': qtlivprof,
                    'prixunit': prixunit,
                    'total': total # Calculé à partir des données DB
                })
                
                # Ajout au Treeview
                self.tree.insert("", "end", values=(
                    designation, 
                    unite_designation, 
                    self.formater_nombre(qtprof), 
                    self.formater_nombre(prixunit),
                    self.formater_nombre(qtlivprof), 
                    self.formater_nombre(total)
                ))
            
            self.calculer_total()
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement de la commande: {str(e)}")
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()

    def ouvrir_recherche_article(self):
        """Ouvre une fenêtre pour rechercher et sélectionner un article"""
        if self.index_ligne_selectionnee is not None:
            messagebox.showwarning("Attention", "Veuillez d'abord valider ou annuler la modification de ligne en cours")
            return

        fenetre_recherche = ctk.CTkToplevel(self)
        fenetre_recherche.title("Rechercher Article")
        fenetre_recherche.geometry("900x500")
        fenetre_recherche.grab_set()
        
        main_frame = ctk.CTkFrame(fenetre_recherche)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        titre = ctk.CTkLabel(main_frame, text="Sélectionner un Article", 
                            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"))
        titre.pack(pady=(0, 10))
        
        search_frame = ctk.CTkFrame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(search_frame, text="🔍 Rechercher:").pack(side="left", padx=5)
        entry_search = ctk.CTkEntry(search_frame, placeholder_text="Code ou désignation...", width=300)
        entry_search.pack(side="left", padx=5, fill="x", expand=True)
        
        tree_frame = ctk.CTkFrame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        colonnes = ("ID_Article", "ID_Unite", "Code", "Désignation", "Unité")
        tree = ttk.Treeview(tree_frame, columns=colonnes, show='headings', height=12)
        
        tree.heading("ID_Article", text="ID")
        tree.heading("ID_Unite", text="ID_U")
        tree.heading("Code", text="Code")
        tree.heading("Désignation", text="Désignation")
        tree.heading("Unité", text="Unité")
        
        tree.column("ID_Article", width=0, stretch=False) # Caché
        tree.column("ID_Unite", width=0, stretch=False)   # Caché
        tree.column("Code", width=150, anchor='w')
        tree.column("Désignation", width=500, anchor='w')
        tree.column("Unité", width=100, anchor='w')
        
        scrollbar = ctk.CTkScrollbar(tree_frame, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        label_count = ctk.CTkLabel(main_frame, text="Nombre d'articles : 0")
        label_count.pack(pady=5)
        
        def charger_articles(filtre=""):
            for item in tree.get_children():
                tree.delete(item)
            
            conn = self.connect_db()
            if not conn:
                return
            
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
                
                query += " ORDER BY T2.\"designation\" ASC, T1.\"codearticle\" ASC"
                cursor.execute(query, params)
                resultats = cursor.fetchall()
                
                for row in resultats:
                    if len(row) >= 5:
                        # row: [idarticle, codearticle, designation, designationunite, idunite]
                        # Insertion de 5 valeurs: ID_Article, ID_Unite, Code, Désignation, Unité
                        tree.insert('', 'end', values=(row[0], row[4], row[1], row[2], row[3])) 
                
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
            
            idarticle = values[0]
            idunite = values[1]
            nomart = values[3]
            unite = values[4]
            
            self.article_selectionne = {
                'idarticle': idarticle,
                'idunite': idunite,
                'nomart': nomart,
                'unite': unite
            }
            
            # Remplir les champs de la page principale
            self.entry_article.configure(state="normal")
            self.entry_article.delete(0, "end")
            self.entry_article.insert(0, nomart)
            self.entry_article.configure(state="readonly")
            
            self.entry_unite.configure(state="normal")
            self.entry_unite.delete(0, "end")
            self.entry_unite.insert(0, unite)
            self.entry_unite.configure(state="readonly")
            
            self.entry_qtprof.delete(0, "end")
            self.entry_qtlivprof.delete(0, "end")
            self.entry_qtlivprof.insert(0, "0")
            
            # Récupérer le dernier prix de l'article depuis tb_prix
            self.entry_prixunit.delete(0, "end")
            dernier_prix = self.recuperer_dernier_prix(idarticle)
            if dernier_prix is not None:
                self.entry_prixunit.insert(0, self.formater_nombre(dernier_prix))
            else:
                self.entry_prixunit.insert(0, "0,00")
            
            fenetre_recherche.destroy()

        tree.bind('<Double-Button-1>', lambda e: valider_selection())
        
        btn_valider = ctk.CTkButton(main_frame, text="Sélectionner", 
                                    command=valider_selection, 
                                    fg_color="#2e7d32", hover_color="#1b5e20")
        btn_valider.pack(pady=10)
        
        charger_articles()

    def ajouter_article(self):
        """Ajoute l'article sélectionné à la liste et au treeview"""
        if not self.article_selectionne:
            messagebox.showwarning("Attention", "Veuillez sélectionner un article")
            return
        
        try:
            qtprof = self.parser_nombre(self.entry_qtprof.get())
            prixunit = self.parser_nombre(self.entry_prixunit.get())
            qtlivprof = self.parser_nombre(self.entry_qtlivprof.get())
            
            if qtprof <= 0:
                messagebox.showwarning("Attention", "La quantité commandée doit être supérieure à 0")
                return

            total = qtprof * prixunit
            
            # Vérifier si l'article est déjà dans la liste (pour éviter les doublons accidentels)
            for item in self.items_commande:
                if item['idarticle'] == self.article_selectionne['idarticle']:
                    messagebox.showwarning("Attention", "Cet article est déjà dans la liste. Veuillez le modifier.")
                    return

            self.tree.insert("", "end", values=(
                self.article_selectionne['nomart'],
                self.article_selectionne['unite'],
                self.formater_nombre(qtprof),
                self.formater_nombre(prixunit),
                self.formater_nombre(qtlivprof),
                self.formater_nombre(total)
            ))
            
            self.items_commande.append({
                # Correction: Utilisation de 'idprofdetail' pour la clé de détail (alignement avec la base de données/mise à jour)
                'idprofdetail': None, 
                'idarticle': self.article_selectionne['idarticle'],
                'idunite': self.article_selectionne['idunite'], # idunite est maintenant correctement stocké ici
                'designation': self.article_selectionne['nomart'],  # ✅ AJOUT
                'designationunite': self.article_selectionne['unite'],  # ✅ AJOUT
                'qtprof': qtprof,
                'prixunit': prixunit,
                'qtlivprof': qtlivprof,
                'total': total
            })
            
            self.article_selectionne = None
            
            # Réinitialiser les champs de saisie
            self.entry_article.configure(state="normal")
            self.entry_article.delete(0, "end")
            self.entry_article.configure(state="readonly")
            
            self.entry_unite.configure(state="normal")
            self.entry_unite.delete(0, "end")
            self.entry_unite.configure(state="readonly")
            
            self.entry_qtprof.delete(0, "end")
            self.entry_prixunit.delete(0, "end")
            self.entry_qtlivprof.delete(0, "end")
            self.entry_qtlivprof.insert(0, "0")
            
            self.calculer_total()
            
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
        """Calcule et affiche le total de la commande"""
        # Utilisation de 'qtprof' et 'prixunit' pour la cohérence
        total = sum(item.get('qtprof', 0) * item.get('prixunit', 0) for item in self.items_commande)
        self.label_total.configure(text=f"Total: {self.formater_nombre(total)}")

    # --- NOUVELLE FONCTION POUR CALCULER LE STATUT ---
    def calculer_statut_proforma(self):
        """Détermine le statut de la proforma (texte) basé sur self.items_commande"""
        total_lignes = len(self.items_commande)
        
        if total_lignes == 0:
            return "⚠️ En attente" 

        # Compter les lignes où la quantité proforma est égale à la quantité livrée ET > 0
        lignes_completes = sum(1 for item in self.items_commande 
                               if item.get('qtprof', 0) > 0 and 
                               item.get('qtprof', 0) == item.get('qtlivprof', 0))
        
        # Si toutes les lignes sont complètes (nombre de lignes = lignes complètes)
        if lignes_completes == total_lignes:
            return "✅ A Facturer"
        else:
            # Si au moins une ligne existe mais toutes ne sont pas complètes
            return "⚠️ En attente"
    # ------------------------------------------------

    def enregistrer_proforma(self):
        """Enregistre la commande (INSERT ou UPDATE selon le mode)"""
        if self.index_ligne_selectionnee is not None:
            messagebox.showwarning("Attention", "Veuillez d'abord valider ou annuler la modification de ligne en cours")
            return

        if not self.items_commande:
            messagebox.showwarning("Attention", "La commande ne contient aucune ligne.")
            return

        frs_nom = self.entry_client.get()
        idclient = self.clients.get(frs_nom)
        if not idclient:
            messagebox.showwarning("Attention", "Veuillez sélectionner un client valide.")
            return
        
        # --- AJOUT DU CALCUL DU MONTANT TOTAL ---
        montant_total = sum(item.get('qtprof', 0) * item.get('prixunit', 0) for item in self.items_commande)
        # ----------------------------------------
        
        # --- AJOUT: Calcul du statut ---
        nouveau_statut = self.calculer_statut_proforma()
        # -------------------------------
        
        conn = self.connect_db()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            # Utiliser une observation simple (à adapter si vous avez un champ observation dans l'UI)
            description = "Proforma pour " + frs_nom 
            
            if self.mode_modification and self.idprof_charge:
                # Mode Modification (UPDATE)
                
                # --- MODIFICATION: Ajout du statut et de la date de modification à l'UPDATE de la commande principale ---
                query_commande_update = """
                    UPDATE tb_proforma 
                    SET idclient = %s, observation = %s, datemodif = %s, statut = %s, mtprof = %s
                    WHERE idprof = %s
                """
                cursor.execute(query_commande_update, (
                    idclient, 
                    description, 
                    datetime.now(), # datemodif
                    nouveau_statut, # statut
                    montant_total,  # <-- NOUVEAU: mtprof
                    self.idprof_charge
                ))
                # -----------------------------------------------------------------------------------------------------

                # Requêtes pour les détails
                query_update = """ 
                    UPDATE tb_proformadetail 
                    SET idarticle = %s, idunite = %s, qtprof = %s, qtlivprof = %s, prixunit = %s, total = %s 
                    WHERE id = %s 
                """
                query_insert = """ 
                    INSERT INTO tb_proformadetail (idprof, idarticle, idunite, qtprof, qtlivprof, prixunit, total) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s) 
                """

                for item in self.items_commande:
                    total_ligne = item['qtprof'] * item['prixunit']
                    if item.get('idprofdetail'): # Utilisation de .get() pour plus de sécurité
                        # UPDATE
                        cursor.execute(query_update, (
                            item['idarticle'], item['idunite'], item['qtprof'], 
                            item['qtlivprof'], item['prixunit'], total_ligne, 
                            item['idprofdetail']
                        ))
                    else:
                        # INSERT (nouvelle ligne)
                        cursor.execute(query_insert, (
                            self.idprof_charge, item['idarticle'], item['idunite'], 
                            item['qtprof'], item['qtlivprof'], item['prixunit'], total_ligne
                        ))
                
                conn.commit()
                messagebox.showinfo("Succès", f"Proforma {self.entry_ref.get()} modifiée avec succès! Statut: {nouveau_statut}")
                
            else:
                # Mode Création (INSERT)
                
                # --- MODIFICATION: Ajout du statut dans l'INSERT de la commande principale ---
                query_commande = """
                    INSERT INTO tb_proforma (refprof, dateprof, iduser, idclient, observation, deleted, statut, mtprof) 
                    VALUES (%s, %s, %s, %s, %s, 0, %s, %s) 
                    RETURNING idprof
                """
                cursor.execute(query_commande, (
                    self.entry_ref.get(), 
                    datetime.now().strftime('%Y-%m-%d'), 
                    self.iduser, 
                    idclient, 
                    description,
                    nouveau_statut, # statut
                    montant_total   # <-- NOUVEAU: mtprof
                ))
                # -------------------------------------------------------------------------
                
                idprof = cursor.fetchone()[0]
                query_detail = """ 
                    INSERT INTO tb_proformadetail (idprof, idarticle, idunite, qtprof, qtlivprof, prixunit, total) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s) 
                """
                for item in self.items_commande:
                    total_ligne = item['qtprof'] * item['prixunit']
                    cursor.execute(query_detail, (
                        idprof, item['idarticle'], item['idunite'], 
                        item['qtprof'], item['qtlivprof'], item['prixunit'], total_ligne
                    ))
                
                conn.commit()
                messagebox.showinfo("Succès", f"Proforma enregistrée avec succès! Statut: {nouveau_statut}")
                self.mode_modification = False
                self.idprof_charge = None
                self.titre.configure(text="Nouvelle Commande Clients")
                self.reinitialiser_formulaire()

        except Exception as e:
            conn.rollback() 
            messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement: {str(e)}")
            
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()

    def nouvelle_commande(self):
        """Réinitialise le formulaire pour une nouvelle commande"""
        if self.mode_modification:
            if not messagebox.askyesno("Confirmation", "Voulez-vous vraiment commencer une nouvelle commande? Les modifications non enregistrées seront perdues."):
                return

        self.reinitialiser_formulaire(generer_ref=True)
        self.mode_modification = False
        self.idprof_charge = None
        self.titre.configure(text="Nouvelle Commande Clients")
        
    def reinitialiser_formulaire(self, generer_ref=True):
        """Réinitialise tous les champs et la liste des articles"""
        if generer_ref:
            self.generer_reference()
        
        if self.clients:
            self.entry_client.delete(0, "end"); self.entry_client.insert(0, list(self.clients.keys())[0])
        
        self.entry_qtprof.delete(0, "end")
        self.entry_prixunit.delete(0, "end")
        self.entry_qtlivprof.delete(0, "end")
        self.entry_qtlivprof.insert(0, "0")
        
        self.entry_article.configure(state="normal")
        self.entry_article.delete(0, "end")
        self.entry_article.configure(state="readonly")
        
        self.entry_unite.configure(state="normal")
        self.entry_unite.delete(0, "end")
        self.entry_unite.configure(state="readonly")
        
        self.article_selectionne = None
        self.items_commande = []
        self.index_ligne_selectionnee = None
        
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        self.calculer_total()
        
        self.btn_ajouter.configure(state="normal")
        self.btn_modifier_ligne.configure(state="disabled", text="✏️ Modifier Ligne")
        self.btn_annuler_selection.configure(state="disabled")

    def generate_pdf_a5_proforma(self, data: dict, filename: str):
        """
        Génère le PDF de la proforma au format A5 avec le modèle ReportLab.
        Marque clairement le document comme PROFORMA.
        """
        c = canvas.Canvas(filename, pagesize=A5)
        width, height = A5

        # ✅ 1. EN-TÊTE AVEC VERSET
        verset = "Ankino amin'ny Jehovah ny asanao dia ho lavorary izay kasainao. Ohabolana 16:3"
        c.setLineWidth(1)
        c.rect(10*mm, height - 15*mm, width - 20*mm, 8*mm)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(width/2, height - 12.5*mm, verset)

        # ✅ 2. EN-TÊTE DEUX COLONNES
        styles = getSampleStyleSheet()
        style_p = ParagraphStyle('style_p', fontSize=9, leading=11, parent=styles['Normal'])

        societe = data['societe']
        utilisateur = data['utilisateur']
        client = data['client']
        proforma = data['proforma']

        # Adapter les clés de données si nécessaire
        nomsociete = societe.get('nomsociete', 'N/A')
        adressesociete = societe.get('adressesociete') or societe.get('adresse', 'N/A')
        contactsociete = societe.get('contactsociete') or societe.get('tel', 'N/A')
        nifsociete = societe.get('nifsociete') or societe.get('nif', 'N/A')
        statsociete = societe.get('statsociete') or societe.get('stat', 'N/A')

        gauche_text = f"<b>{nomsociete}</b><br/>{adressesociete}<br/>TEL: {contactsociete}<br/>NIF: {nifsociete} | STAT: {statsociete}"

        # Gérer si utilisateur est un dict ou une string
        if isinstance(utilisateur, dict):
            user_name = f"{utilisateur.get('prenomuser', '')} {utilisateur.get('nomuser', '')}"
        else:
            user_name = str(utilisateur)

        droite_text = f"<b>Proforma N°: {proforma['refprof']}</b><br/>{proforma['dateprof']}<br/><b>CLIENT: {client['nomcli']}</b><br/><font size='8'>Op: {user_name}</font>"

        gauche = Paragraph(gauche_text, style_p)
        droite = Paragraph(droite_text, style_p)

        header_table = Table([[gauche, droite]], colWidths=[64*mm, 64*mm])
        header_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))

        header_table.wrapOn(c, width, height)
        header_table.drawOn(c, 10*mm, height - 48*mm)

        # ✅ 3. MARQUEUR PROFORMA (APRÈS L'EN-TÊTE, PETIT, EN ROUGE, MINIMAL SPACE)
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(colors.HexColor("#FF6B6B"))
        c.drawCentredString(width/2, height - 51*mm, "PROFORMA")
        c.setFillColor(colors.HexColor("#000000"))

        # ✅ 4. TABLEAU DES ARTICLES
        table_top = height - 55*mm
        table_bottom = 65*mm
        frame_height = table_top - table_bottom

        row_height = 5.5*mm
        max_rows = int(frame_height / row_height)

        # Préparer les données du tableau
        table_data = [['QTE', 'UNITE', 'DESIGNATION', 'PU TTC', 'MONTANT']]

        total_montant = 0
        num_articles = 0
        for detail in data['details']:
            montant = detail.get('montant_ttc', detail.get('montant', 0))
            total_montant += montant
            num_articles += 1
            table_data.append([
                str(int(detail.get('qte', 0))),
                str(detail.get('unite', '')),
                str(detail.get('designation', '')),
                self.formater_nombre(detail.get('prixunit', 0)),
                self.formater_nombre(montant)
            ])

        # Ajouter des lignes vides
        empty_rows_needed = max_rows - 1 - num_articles - 2
        for i in range(max(0, empty_rows_needed)):
            table_data.append(['', '', '', '', ''])

        # Totaux
        table_data.append(['', '', 'TOTAL Ar:', self.formater_nombre(total_montant), ''])

        col_widths = [12*mm, 15*mm, 62*mm, 19.5*mm, 19.5*mm]

        # Dessiner le cadre et lignes
        c.setLineWidth(1)
        c.rect(10*mm, table_bottom, width - 20*mm, frame_height)

        x_pos = 10*mm
        for w in col_widths[:-1]:
            x_pos += w
            c.line(x_pos, table_top, x_pos, table_bottom)

        # Créer le tableau avec hauteurs proportionnelles
        actual_row_height = frame_height / len(table_data)
        row_heights = [actual_row_height] * len(table_data)

        articles_table = Table(table_data, colWidths=col_widths, rowHeights=row_heights)
        articles_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -2), 8),
            ('FONTSIZE', (0, -1), (-1, -1), 9),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
            ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 0), (2, 0), 'LEFT'),
            ('ALIGN', (2, -1), (2, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 1),
            ('RIGHTPADDING', (3, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))

        articles_table.wrapOn(c, width, height)
        assert actual_row_height, 'actual_row_height must not be None'
        actual_total_height = len(table_data) * actual_row_height
        articles_table.drawOn(c, 10*mm, table_top - actual_total_height)

        # ✅ 5. TEXTE EN LETTRES
        montant_lettres = nombre_en_lettres_fr(int(total_montant)).upper()
        text_y = table_bottom - 18*mm
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(width/2, text_y, f"ARRETE A LA SOMME DE {montant_lettres}")

        # ✅ 6. MENTION "BON DE COMMANDE"
        c.setFont("Helvetica-Oblique", 8)
        c.drawCentredString(width/2, text_y - 5*mm, "Bon de Commande - Ceci n'est pas une facture")

        # ✅ 7. SIGNATURES
        sig_y = 15*mm
        c.setFont("Helvetica-Bold", 10)
        c.drawString(15*mm, sig_y, "Le Client")
        c.drawCentredString(width/2, sig_y, "Responsable")
        c.drawString(width - 35*mm, sig_y, "Gestionnaire")

        # ✅ SAUVEGARDER
        try:
            c.save()
            print(f"✅ PDF Proforma généré avec succès : {filename}")
        except Exception as e:
            print(f"❌ Erreur PDF Proforma : {e}")
            import traceback
            traceback.print_exc()

    def imprimer_proforma(self):
        """Génère et imprime la proforma au format PDF A5"""
        if not self.idprof_charge:
            if not messagebox.askyesno("Attention", "La commande n'est pas encore enregistrée. Voulez-vous l'enregistrer maintenant pour obtenir un bon officiel ?"):
                return # Ne pas continuer si l'enregistrement est refusé
            
            # Tenter l'enregistrement
            self.enregistrer_proforma()
            # Si l'enregistrement a réussi, self.idprof_charge sera défini
            if not self.idprof_charge:
                # Cela signifie que enregistrer_proforma a échoué (un message d'erreur a déjà été affiché)
                return

        # Récupération des infos société et client
        conn = self.connect_db()
        if not conn:
            messagebox.showerror("Erreur", "Impossible de se connecter à la base de données.")
            return

        try:
            cursor = conn.cursor()
            
            # Récupération des infos de la société
            cursor.execute("SELECT nomsociete, adressesociete, contactsociete, nifsociete, statsociete FROM tb_infosociete LIMIT 1")
            row_societe = cursor.fetchone()
            societe_info = {
                'nomsociete': row_societe[0] if row_societe else 'N/A',
                'adressesociete': row_societe[1] if row_societe else 'N/A',
                'contactsociete': row_societe[2] if row_societe else 'N/A',
                'nifsociete': row_societe[3] if row_societe else 'N/A',
                'statsociete': row_societe[4] if row_societe else 'N/A',
            }

            # Récupération des infos client
            idclient = self.client_selectionne_id if self.client_selectionne_id else self.clients.get(self.entry_client.get())
            client_info = {'nomcli': 'N/A'}
            if idclient:
                cursor.execute("SELECT nomcli FROM tb_client WHERE idclient = %s", (idclient,))
                row_client = cursor.fetchone()
                if row_client:
                    client_info = {'nomcli': row_client[0]}

            # Récupération des infos proforma
            cursor.execute("SELECT refprof, dateprof FROM tb_proforma WHERE idprof = %s", (self.idprof_charge,))
            row_proforma = cursor.fetchone()
            proforma_info = {
                'refprof': row_proforma[0] if row_proforma else self.entry_ref.get(),
                'dateprof': row_proforma[1].strftime('%d/%m/%Y') if row_proforma and row_proforma[1] else datetime.now().strftime('%d/%m/%Y'),
            }

            # Récupération des détails de la proforma
            cursor.execute("""
                SELECT pd.qtprof, u.designationunite, a.designation, pd.prixunit, (pd.qtprof * pd.prixunit) as montant
                FROM tb_proformadetail pd
                JOIN tb_unite u ON pd.idunite = u.idunite
                JOIN tb_article a ON pd.idarticle = a.idarticle
                WHERE pd.idprof = %s
                ORDER BY pd.id
            """, (self.idprof_charge,))
            
            details = []
            for row in cursor.fetchall():
                details.append({
                    'qte': row[0],
                    'unite': row[1],
                    'designation': row[2],
                    'prixunit': row[3],
                    'montant_ttc': row[4],
                })

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur de récupération des données pour l'impression: {str(e)}")
            return
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()

        # Préparer les données pour le PDF
        data = {
            'societe': societe_info,
            'utilisateur': 'Opérateur',
            'client': client_info,
            'proforma': proforma_info,
            'details': details,
        }

        # Générer le PDF
        import tempfile
        import os
        import webbrowser
        
        # Créer un fichier temporaire
        pdf_filename = os.path.expanduser(f"~\\Desktop\\Proforma_{proforma_info['refprof'].replace('/', '-')}.pdf")
        
        # Créer le répertoire s'il n'existe pas
        os.makedirs(os.path.dirname(pdf_filename), exist_ok=True)
        
        try:
            self.generate_pdf_a5_proforma(data, pdf_filename)
            messagebox.showinfo("Succès", f"Proforma PDF généré avec succès !\n{pdf_filename}")
            
            # Ouvrir le fichier PDF
            if os.path.exists(pdf_filename):
                os.startfile(pdf_filename)  # Windows
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la génération du PDF : {str(e)}")


if __name__ == "__main__":
    # Assurez-vous d'avoir un fichier config.json et une base de données PostgreSQL configurée
    app = ctk.CTk()
    app.geometry("1200x800")
    
    iduser = 1 # ID utilisateur de test (à adapter à votre application principale)
    
    page = PageCommandeCli(app, iduser=iduser)
    page.pack(fill="both", expand=True, padx=10, pady=10)
    
    app.mainloop()