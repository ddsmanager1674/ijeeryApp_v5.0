import customtkinter as ctk
from tkinter import messagebox, ttk, simpledialog
import psycopg2
import json
from datetime import datetime
import calendar 
from typing import Optional, Dict, Any, List
import traceback 
import os
import sys # Ajouté pour open_file sur Linux/macOS
import textwrap # Ajouté pour le formatage du ticket de caisse
import winsound
from resource_utils import get_config_path, safe_file_read


# --- NOUVELLES IMPORTATIONS POUR L'IMPRESSION ---
from reportlab.lib.pagesizes import A5, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from pages.page_avoir import PageAvoir
from pages.page_proforma import PageCommandeCli

class PasswordDialog(ctk.CTkToplevel):
    def __init__(self, title, text):
        super().__init__()
        self.title(title)
        self.geometry("300x150")
        self.result = None
        
        self.label = ctk.CTkLabel(self, text=text)
        self.label.pack(pady=10)
        
        self.entry = ctk.CTkEntry(self, show="*") # Masque la saisie
        self.entry.pack(pady=5)
        self.entry.focus_set()
        
        self.btn = ctk.CTkButton(self, text="Valider", command=self.ok)
        self.btn.pack(pady=10)
        
        self.grab_set()
        self.wait_window()

    def ok(self):
        self.result = self.entry.get()
        self.destroy()

# -----------------------------------------------

# ==============================================================================
# FONCTION UTILITAIRE : CONVERSION NOMBRE EN LETTRES (FRANÇAIS)
# ==============================================================================

def nombre_en_lettres_fr(montant: float) -> str:
    """
    Convertit un montant numérique en sa représentation en lettres en français.
    Gère les Millions et les Milliers correctement.
    """
    from math import floor
    
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
    
    #unite_monetaire = "Ariary" # Assurez-vous que cette unité est correcte (était "Francs" dans le code précédent)
    #result_str += " " + unite_monetaire
    
    # Centimes
    if centimes > 0:
        centime_lettres = convertir_bloc(centimes)
        centime_monetaire = "centimes"
        centime_lettres = centime_lettres.replace("-", " ")
        result_str += " et " + centime_lettres + " " + centime_monetaire

    return result_str.capitalize().replace(" et-", " et ")
    
# ==============================================================================

# ==============================================================================
# CLASSE UTILITAIRE : DIALOGUE DE CHOIX D'IMPRESSION (CTKTOPLEVEL)
# ==============================================================================
class SimpleDialogWithChoice(ctk.CTkToplevel):
    """Dialogue modal personnalisé pour choisir le format d'impression."""
    def __init__(self, master, title, message):
        super().__init__(master)
        self.title(title)
        self.transient(master)
        self.grab_set()
        
        self.result = None
        self.choice = ctk.StringVar(self, value="A5 PDF (Paysage)")
        
        # UI
        ctk.CTkLabel(self, text=message, wraplength=350, justify="left").pack(pady=10, padx=20)
        
        frame_radio = ctk.CTkFrame(self)
        frame_radio.pack(pady=5, padx=20, fill="x")
        
        self.radio_pdf = ctk.CTkRadioButton(frame_radio, text="A5 PDF (Paysage)", variable=self.choice, value="A5 PDF (Paysage)")
        self.radio_pdf.pack(pady=5, padx=10, anchor="w")
        
        self.radio_ticket = ctk.CTkRadioButton(frame_radio, text="Ticket de Caisse 80mm", variable=self.choice, value="Ticket 80mm")
        self.radio_ticket.pack(pady=5, padx=10, anchor="w")
        
        # Boutons
        frame_buttons = ctk.CTkFrame(self)
        frame_buttons.pack(pady=10, padx=20)
        
        ctk.CTkButton(frame_buttons, text="Annuler", command=self.cancel, fg_color="#d32f2f", hover_color="#b71c1c").pack(side="left", padx=5)
        ctk.CTkButton(frame_buttons, text="Imprimer", command=self.ok, fg_color="#00695c", hover_color="#004d40").pack(side="right", padx=5)
        
        self.wait_window(self)

    def ok(self):
        self.result = self.choice.get()
        self.grab_release()
        self.destroy()

    def cancel(self):
        self.result = None
        self.grab_release()
        self.destroy()
# ==============================================================================


# --- Configuration de CustomTkinter ---
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class PageVenteParMsin(ctk.CTkFrame): # MODIFICATION : Hérite de CTkFrame pour support des tabs
    """
    Frame de gestion des ventes de stock - peut être utilisé comme frame dans l'app principale
    ou dans les tabs du gestionnaire de ventes.
    """
    def __init__(self, master=None, id_user_connecte: Optional[int] = None) -> None:
        super().__init__(master) # Initialisation du Frame
        
        if id_user_connecte is None:
            messagebox.showerror("Erreur", "Aucun utilisateur connecté. Veuillez vous reconnecter.")
            self.id_user_connecte = None
        else:
            self.id_user_connecte = id_user_connecte
            print(f"✅ Utilisateur connecté - ID: {self.id_user_connecte}") 
        self.conn: Optional[psycopg2.connection] = None
        self.article_selectionne = None
        self.stock_temporaire_selection = None
        self.detail_vente = []
        self.index_ligne_selectionnee = None
        self.magasin_map = {}
        self.magasin_ids = []
        self.client_map = {}
        self.client_ids = []
        self.infos_societe: Dict[str, Any] = {}
        self.derniere_idvente_enregistree: Optional[int] = None
    
        self.mode_modification = False
        self.idvente_charge = None
        self.details_proforma_a_ajouter: Optional[List[Dict]] = None # NOUVEAU: Stocke temporairement les lignes du proforma
        self.details_proforma_a_ajouter_idprof: Optional[int] = None # NOUVEAU: ID du proforma chargé
        
        # Charger les paramètres d'impression
        self.settings = self.load_settings()
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # En-tête - pas de resize
        self.grid_rowconfigure(1, weight=0)  # Panneau saisie articles - taille fixe
        self.grid_rowconfigure(2, weight=0)  # Boutons action - taille fixe
        self.grid_rowconfigure(3, weight=1)  # Tableau articles - grandit avec la fenêtre
        self.grid_rowconfigure(4, weight=0)  # Totaux - pas de resize
        self.grid_rowconfigure(5, weight=0)  # Barre d'actions
        
        self.setup_ui()
        self.bind("<Configure>", self._on_resize_vente_layout)
        self.generer_reference()
        self.charger_magasins()
        self.charger_client()
        self.charger_infos_societe()
        self.conn = self.connect_db() 

    def connect_db(self):
        """Connexion à la base de données PostgreSQL (Méthode fournie par l'utilisateur)"""
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
        except psycopg2.Error as e:
            messagebox.showerror("Erreur de Base de Données", f"Impossible de se connecter à la base de données : {e}")
            return None
    
    def load_settings(self) -> Dict[str, Any]:
        """Charge les paramètres d'impression depuis settings.json"""
        try:
            with open('settings.json', 'r', encoding='utf-8') as f:
                settings = json.load(f)
                print(f"✅ Paramètres d'impression chargés depuis settings.json")
                return settings
        except FileNotFoundError:
            print("⚠️ Fichier settings.json non trouvé, utilisation des paramètres par défaut")
            return {
                'Vente_ImpressionConfirmation': 1,
                'Vente_ImpressionA5': 1,
                'Vente_ImpressionTicket': 0,
                'Avoir_ImpressionConfirmation': 1,
                'Avoir_ImpressionA5': 1,
                'Avoir_ImpressionTicket': 0
            }
        except json.JSONDecodeError:
            print("⚠️ Erreur dans le format de settings.json, utilisation des paramètres par défaut")
            return {
                'Vente_ImpressionConfirmation': 1,
                'Vente_ImpressionA5': 1,
                'Vente_ImpressionTicket': 0,
                'Avoir_ImpressionConfirmation': 1,
                'Avoir_ImpressionA5': 1,
                'Avoir_ImpressionTicket': 0
            }
    
    # --- FONCTIONS DE FORMATAGE ET DE CALCUL DE STOCK ---
    def formater_nombre(self, nombre):
        """Formate un nombre avec séparateur de milliers (1.000.000,00)"""
        try:
            nombre = float(nombre) 
            # Utilise un formatage pour avoir des séparateurs de milliers
            formatted = "{:,.2f}".format(nombre).replace(',', '_TEMP_').replace('.', ',').replace('_TEMP_', '.')
            return formatted
        except:
            return "0,00"
    
    def formater_nombre_pdf(self, nombre):
        """Formate un nombre avec séparateur de milliers SANS décimales pour PDF (1.000.000)"""
        try:
            nombre = float(nombre)
            # Arrondit à l'entier le plus proche et formate avec séparateur de milliers
            formatted = "{:,.0f}".format(nombre).replace(',', '.')
            return formatted
        except:
            return "0"
    
    def parser_nombre(self, texte):
        """Convertit un nombre formaté (1.000.000,00) en float"""
        try:
            # Remplace le point de séparation des milliers et la virgule décimale par un point
            texte_clean = texte.replace('.', '').replace(',', '.')
            return float(texte_clean)
        except:
            return 0.0

    def get_article_price(self, idarticle, idunite):
        """Récupère le dernier prix unitaire pour l'article et l'unité donnés."""
        conn = self.conn   # <<< UTILISATION DE LA CONNEXION PRINCIPALE
        if not conn:
            return 0.0

        try:
            cursor = conn.cursor()

            # 1. Dernier prix dans tb_prix
            sql_prix = """
                SELECT COALESCE(prix) as prix FROM tb_prix 
                WHERE idarticle = %s AND idunite = %s 
                ORDER BY id DESC 
                LIMIT 1
            """
            cursor.execute(sql_prix, (idarticle, idunite))
            result = cursor.fetchone()

            if result and result[0] is not None and result[0] > 0:
                return float(result[0])

            # 2. Sinon, prixventeunite dans tb_unite
            sql_unite = """
                SELECT prix 
                FROM tb_prix 
                WHERE idarticle = %s AND idunite = %s 
                LIMIT 1
            """
            cursor.execute(sql_unite, (idarticle, idunite))
            result_unite = cursor.fetchone()

            if result_unite and result_unite[0] is not None:
                return float(result_unite[0])

            return 0.0

        except Exception as e:
            print("ERREUR get_article_price :", e)
            return 0.0

        finally:
            if 'cursor' in locals():
                cursor.close()

    def get_unite_niveau_max(self, idarticle):
        """
        Récupère l'unité de niveau maximum pour un article donné.
        Retourne: (idunite, niveau, designationunite) ou None
        """
        conn = self.connect_db()
        if not conn:
            return None
    
        try:
            cursor = conn.cursor()
        
            # Récupérer l'unité avec le niveau maximum
            sql = """
            SELECT idunite, niveau, designationunite 
            FROM tb_unite 
            WHERE idarticle = %s 
            ORDER BY niveau DESC 
            LIMIT 1
        """
            cursor.execute(sql, (idarticle,))
            result = cursor.fetchone()
        
            return result if result else None
        
        except Exception as e:
            print(f"Erreur get_unite_niveau_max: {e}")
            return None
        finally:
            cursor.close()
            conn.close()


    def verifier_unite_depot_b(self, idarticle, idunite):
        """
        Vérifie si l'unité sélectionnée est autorisée pour le dépôt B.
        Pour le dépôt B, seule l'unité de niveau maximum est autorisée.
    
        Retourne: (autorise: bool, message: str)
        """
            # Récupérer le magasin sélectionné
        magasin_selectionne_nom = self.combo_magasin.get()
    
        # Si ce n'est pas le dépôt B, autoriser toutes les unités
        if "B" not in magasin_selectionne_nom.upper():
            return (True, "")
    
        conn = self.connect_db()
        if not conn:
            return (False, "Erreur de connexion à la base de données")
    
        try:
            cursor = conn.cursor()
        
            # Récupérer le niveau de l'unité sélectionnée
            cursor.execute("""
                SELECT niveau, designationunite 
                FROM tb_unite 
                WHERE idarticle = %s AND idunite = %s
            """, (idarticle, idunite))
        
            unite_selectionnee = cursor.fetchone()
        
            if not unite_selectionnee:
                return (False, "Unité introuvable")
        
            niveau_selectionne, designation_selectionnee = unite_selectionnee
        
            # Récupérer le niveau maximum pour cet article
            cursor.execute("""
                SELECT MAX(niveau), designationunite 
                FROM tb_unite 
                WHERE idarticle = %s 
                GROUP BY designationunite
                ORDER BY MAX(niveau) DESC
                LIMIT 1
            """, (idarticle,))
        
            niveau_max_result = cursor.fetchone()
        
            if not niveau_max_result:
                return (False, "Impossible de déterminer le niveau maximum")
        
            niveau_max, designation_max = niveau_max_result
        
            # Vérifier si l'unité sélectionnée est bien celle de niveau maximum
            if niveau_selectionne < niveau_max:
                return (False, 
                    f"⚠️ DÉPÔT B : Seule l'unité de niveau {niveau_max} ({designation_max}) est autorisée.\n"
                    f"Vous avez sélectionné : {designation_selectionnee} (niveau {niveau_selectionne}).\n\n"
                    f"Veuillez choisir l'unité {designation_max} pour facturer depuis le Dépôt B.")
        
            return (True, "")
        
        except Exception as e:
            print(f"Erreur verifier_unite_depot_b: {e}")
            return (False, f"Erreur lors de la vérification: {str(e)}")
        finally:
            cursor.close()
            conn.close()
    
    def calculer_stock_article(self, idarticle, idunite_cible, idmag=None):
        """
        ✅ CALCUL CONSOLIDÉ (identique à page_stock.py) :
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
                q_ven = "SELECT COALESCE(SUM(qtvente), 0) FROM tb_ventedetail vd INNER JOIN tb_vente v ON vd.idvente = v.id WHERE vd.idarticle = %s AND vd.idunite = %s AND v.deleted = 0 AND v.statut = 'VALIDEE'"
                p_ven = [idarticle, idu_boucle]
                if idmag:
                    q_ven += " AND v.idmag = %s"
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

                # Conversion en unité de base puis accumulation dans le réservoir
                solde_unite = (receptions + t_in + inv - ventes - t_out)
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
    
    def charger_stocks(self):
        """Charge les stocks détaillés par magasin - VERSION ULTRA OPTIMISÉE"""
        self.creer_treeview()
        conn = self.connect_db()
        if not conn: 
            return
    
        try:
            cursor = conn.cursor()
            
            print("Chargement des stocks en cours...")
        
            # ✅ REQUÊTE CORRIGÉE : même logique réservoir que page_stock.py.
            # Les articles liés (même idarticle, unités différentes) sont reliés
            # via qtunite de tb_unite.
            query_optimisee = """
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
                INNER JOIN tb_vente v ON vd.idvente = v.id AND v.deleted = 0
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
                    -- Sélectionner UNIQUEMENT l'unité de base (plus petit qtunite)
                    -- pour chaque idarticle afin d'éviter le double-comptage
                    SELECT DISTINCT ON (idarticle) idunite
                    FROM tb_unite
                    WHERE deleted = 0
                    ORDER BY idarticle, qtunite ASC
                )
            ),

            solde_base_par_mag AS (
                SELECT
                    idarticle,
                    idmag,
                    SUM(
                        CASE type_mouvement
                            WHEN 'reception'     THEN  quantite * qtunite_source
                            WHEN 'transfert_in'  THEN  quantite * qtunite_source
                            WHEN 'inventaire'    THEN  quantite * qtunite_source
                            WHEN 'vente'         THEN -quantite * qtunite_source
                            WHEN 'transfert_out' THEN -quantite * qtunite_source
                            ELSE 0
                        END
                    ) as solde_base
                FROM mouvements_bruts
                GROUP BY idarticle, idmag
            )

            SELECT
                u.codearticle,
                a.designation,
                u.designationunite,
                COALESCE(
                    (SELECT cd.punitcmd
                     FROM tb_commandedetail cd
                     INNER JOIN tb_commande c ON cd.idcom = c.idcom
                     WHERE cd.idarticle = u.idarticle
                       AND cd.idunite = u.idunite
                       AND c.deleted = 0
                     ORDER BY c.datecom DESC
                     LIMIT 1), 0
                ) as prixachat,
                u.idarticle,
                u.idunite,
                m.idmag,
                COALESCE(sb.solde_base, 0) / NULLIF(COALESCE(u.qtunite, 1), 0) as stock
            FROM tb_unite u
            INNER JOIN tb_article a ON u.idarticle = a.idarticle
            CROSS JOIN tb_magasin m
            LEFT JOIN solde_base_par_mag sb
                ON sb.idarticle = u.idarticle
                AND sb.idmag = m.idmag
            WHERE a.deleted = 0
              AND m.deleted = 0
            ORDER BY a.designation ASC, u.codearticle ASC, m.idmag
            """
            
            cursor.execute(query_optimisee)
            resultats = cursor.fetchall()
            
            print(f"Données récupérées: {len(resultats)} lignes")
        
            # Regrouper par article
            articles_dict = {}
            for code, desig, unite, prix, idarticle, idunite, idmag, stock in resultats:
                if code not in articles_dict:
                    articles_dict[code] = {
                        'designation': desig,
                        'unite': unite,
                        'prix': prix,
                        'stocks': {},
                        'total': 0
                    }
                
                # Ajouter le stock pour ce magasin
                if idmag:
                    nom_mag = next((m[1] for m in self.magasins if m[0] == idmag), f"Mag{idmag}")
                    stock_val = max(0, stock or 0)
                    articles_dict[code]['stocks'][nom_mag] = stock_val
                    articles_dict[code]['total'] += stock_val
            
            print(f"Articles traités: {len(articles_dict)}")
            
            # Insérer dans le Treeview
            compteur = 0
            for idx, (code, data) in enumerate(articles_dict.items()):
                valeurs = [
                    code, 
                    data['designation'], 
                    data['unite'], 
                    self.formater_nombre(data['prix'])
                ]
            
                # Ajouter les stocks par magasin
                for _, nom_mag in self.magasins:
                    valeurs.append(self.formater_nombre(data['stocks'].get(nom_mag, 0)))
            
                # Ajouter le total
                valeurs.append(self.formater_nombre(data['total']))
                zebra_tag = "even" if idx % 2 == 0 else "odd"
            
                # TAG POUR ALERTE STOCK BAS
                if data['total'] <= 0:
                    self.tree.insert("", "end", values=valeurs, tags=(zebra_tag, "stock_bas"))
                else:
                    self.tree.insert("", "end", values=valeurs, tags=(zebra_tag,))
                
                compteur += 1
                if compteur % 100 == 0:
                    print(f"Insertion: {compteur} articles...")
        
            # Style pour les stocks bas
            self.tree.tag_configure("even", background="#FFFFFF", foreground="#000000")
            self.tree.tag_configure("odd", background="#E6EFF8", foreground="#000000")
            self.tree.tag_configure("stock_bas", background="#ffebee", foreground="#c62828")
        
            # Mise à jour des infos
            self.label_total_articles.configure(text=f"Total articles: {len(articles_dict)}")
            self.label_derniere_maj.configure(text=f"Dernière mise à jour: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            
            print(f"Chargement terminé: {len(articles_dict)} articles affichés")
        
            # Vérifier les péremptions
            self.mettre_a_jour_badge_peremption()
        
        except Exception as e:
            print(f"ERREUR DÉTAILLÉE: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Erreur de chargement", f"Détails : {str(e)}")
        finally:
            cursor.close()
            conn.close()
    # --------------------------------------------------------------------------

    def setup_ui(self):
        """Configure l'interface utilisateur de la page de vente."""
    
        # --- Frame principale d'en-tête (Lot 1) ---
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        header_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6, 7, 8, 9), weight=1)
    
        # Référence
        ctk.CTkLabel(header_frame, text="N° Facture:").grid(row=0, column=0, padx=2, pady=2, sticky="w")
        self.entry_ref_vente = ctk.CTkEntry(header_frame, width=150, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        self.entry_ref_vente.grid(row=0, column=1, padx=2, pady=2, sticky="w")
        self.entry_ref_vente.configure(state="readonly")
    
        # Date
        ctk.CTkLabel(header_frame, text="Date Sortie:").grid(row=0, column=2, padx=2, pady=2, sticky="w")
        self.entry_date_vente = ctk.CTkEntry(header_frame, width=150)
        self.entry_date_vente.grid(row=0, column=3, padx=2, pady=2, sticky="w")
        self.entry_date_vente.insert(0, datetime.now().strftime("%d/%m/%Y"))
    
        # Magasin
        ctk.CTkLabel(header_frame, text="Magasin de:").grid(row=0, column=4, padx=2, pady=2, sticky="w")
        self.combo_magasin = ctk.CTkComboBox(header_frame, width=150, values=["Chargement..."])
        self.combo_magasin.grid(row=0, column=5, padx=2, pady=2, sticky="w")
    
         # Client
        # Champ Entry pour client
        self.entry_client = ctk.CTkEntry(header_frame, width=150, placeholder_text="Client...")
        self.entry_client.grid(row=0, column=7, padx=2, pady=2, sticky="w")

        # Bouton loupe
        self.btn_search_client = ctk.CTkButton(
        header_frame,
        text="🔎",
        width=40,
        command=self.open_recherche_client
        )
        self.btn_search_client.grid(row=0, column=8, padx=1, pady=2, sticky="w")


        # NOUVEAU: Bouton Charger Proforma
        self.btn_charger_proforma = ctk.CTkButton(header_frame, text="📜 Proforma", 
                                    command=self.open_recherche_proforma, width=130,
                                    fg_color="#388e3c", hover_color="#2e7d32")
        self.btn_charger_proforma.grid(row=1, column=6, padx=2, pady=2, sticky="ew") # Col 6
        self.btn_charger_proforma.grid_remove()  # Cacher le bouton Proforma
        
        # Bouton Charger facture (Position ajustée)
        # btn_charger_bs = ctk.CTkButton(header_frame, text="📂 Charger Facture", 
                                    # command=self.ouvrir_recherche_sortie, width=130,
                                    #fg_color="#1976d2", hover_color="#1565c0")
        # btn_charger_bs.grid(row=1, column=7, padx=2, pady=2, sticky="ew") # Col 7 (Position d'origine)
    
        # Désignation (Colspan ajusté)
        self.lbl_designation = ctk.CTkLabel(header_frame, text="Désignation:")
        self.lbl_designation.grid(row=1, column=0, padx=2, pady=2, sticky="w")
        self.lbl_designation.grid_remove()  # Cacher le label Désignation en haut
        self.entry_designation = ctk.CTkEntry(header_frame, width=750)
        self.entry_designation.grid(row=1, column=1, columnspan=5, padx=2, pady=2, sticky="ew") # Colspan 5 (1 à 5)
        self.entry_designation.grid_remove()  # Cacher l'entry Désignation en haut

        # --- Frame d'ajout de Détail (Lot 2) ---
        detail_frame = ctk.CTkFrame(self)
        detail_frame.grid(row=1, column=0, padx=0, pady=(0, 5), sticky="ew")
        detail_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6, 7), weight=1)
        
        # Article
        ctk.CTkLabel(detail_frame, text="Article:").grid(row=0, column=0, padx=2, pady=2, sticky="w")
        self.entry_article = ctk.CTkEntry(detail_frame, width=300)
        self.entry_article.grid(row=1, column=0, padx=2, pady=2, sticky="ew")
        self.entry_article.configure(state="readonly")
        
        self.btn_recherche_article = ctk.CTkButton(detail_frame, text="🔎 Rechercher", command=self.open_recherche_article)
        self.btn_recherche_article.grid(row=1, column=1, padx=2, pady=2, sticky="w")
        
        # Quantité
        ctk.CTkLabel(detail_frame, text="Quantité Vente:").grid(row=0, column=2, padx=2, pady=2, sticky="w")
        self.entry_qtvente = ctk.CTkEntry(detail_frame, width=100)
        self.entry_qtvente.grid(row=1, column=2, padx=2, pady=2, sticky="ew")
        # ✅ Raccourci clavier : Entrée pour ajouter l'article
        self.entry_qtvente.bind("<Return>", lambda e: self.valider_detail())
        
        # Unité
        ctk.CTkLabel(detail_frame, text="Unité:").grid(row=0, column=3, padx=2, pady=2, sticky="w")
        self.entry_unite = ctk.CTkEntry(detail_frame, width=100)
        self.entry_unite.grid(row=1, column=3, padx=2, pady=2, sticky="ew")
        self.entry_unite.configure(state="readonly")

        # Remise (Nouveau champ - montant en Ariary au lieu de pourcentage)
        ctk.CTkLabel(detail_frame, text="Remise (Ar):").grid(row=0, column=4, padx=2, pady=2, sticky="w")
        self.entry_remise = ctk.CTkEntry(detail_frame, width=80)
        self.entry_remise.grid(row=1, column=4, padx=2, pady=2, sticky="ew")
        self.entry_remise.insert(0, "0") # Valeur par défaut
        self.entry_remise.configure(state="disabled") # Désactivé par défaut
        
        # Prix Unitaire (Décalé à la colonne 5)
        ctk.CTkLabel(detail_frame, text="Prix Unitaire:").grid(row=0, column=5, padx=2, pady=2, sticky="w")
        self.entry_prixunit = ctk.CTkEntry(detail_frame, width=100)
        self.entry_prixunit.configure(state="readonly")
        self.entry_prixunit.grid(row=1, column=5, padx=2, pady=2, sticky="ew")

        
        
        
        # NOUVEAU: Bouton pour l'ajout en masse des détails du Proforma (Invisible initialement)
        self.btn_ajouter_proforma_bulk = ctk.CTkButton(detail_frame, text="✅ Ajouter Lignes Proforma", command=self.ajouter_details_proforma_en_masse, 
                                            fg_color="#00695c", hover_color="#004d40")

        self.btn_annuler_mod = ctk.CTkButton(detail_frame, text="✖️ Annuler Modif.", command=self.reset_detail_form, 
                                            fg_color="#d32f2f", hover_color="#b71c1c", state="disabled")
        self.btn_annuler_mod.grid(row=1, column=7, padx=2, pady=2, sticky="w")
        self.btn_annuler_mod.grid_remove()  # Cacher le bouton Annuler modification
        
        # Dans create_widgets (vers la ligne 180-200)
        self.notif_stock_depot = ctk.CTkLabel(
        header_frame, 
        text="🔔", 
        font=("Arial", 24), 
        text_color="gray", 
        cursor="hand2"
        )
        # On ne fait PAS de .pack() ou .grid() ici pour qu'elle soit cachée au départ
        self.notif_stock_depot.bind("<Button-1>", lambda e: self.afficher_details_alerte_stock())
        
    

        # --- Ajout du bouton pour ouvrir la nouvelle page ---
        self.btn_suivi_depot = ctk.CTkButton(header_frame, text="🏪 Suivi Dépôt", 
                                     command=self.ouvrir_suivi_depot,
                                     fg_color="#607D8B", hover_color="#455A64")
        self.btn_suivi_depot.grid(row=0, column=9, padx=2, pady=2) # Ajustez la colonne selon votre grille
        self.btn_suivi_depot.grid_remove()  # Cacher le bouton

        # Lancer la vérification en arrière-plan
        self.verifier_alerte_stock_silencieuse()

        # Bouton d'action principal sur la ligne des infos article
        self.btn_ajouter = ctk.CTkButton(detail_frame, text="➕ Ajouter", command=self.valider_detail, 
                                        fg_color="#2e7d32", hover_color="#1b5e20", width=150)
        self.btn_ajouter.grid(row=1, column=7, padx=2, pady=2, sticky="w")
        

        # --- Treeview pour les Détails (Lot 3) ---
        tree_frame = ctk.CTkFrame(self)
        tree_frame.grid(row=3, column=0, padx=0, pady=(0, 5), sticky="nsew")
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        
        style = ttk.Style()
        style.theme_use("clam") 
        style.configure("Treeview", rowheight=22, font=('Segoe UI', 8), background="#FFFFFF", foreground="#000000", fieldbackground="#FFFFFF", borderwidth=0)
        style.configure("Treeview.Heading", background="#E8E8E8", foreground="#000000", font=('Segoe UI', 8, 'bold'))
        style.configure("Treeview.Heading", font=('Segoe UI', 8, 'bold'))

        # Colonnes AJOUTÉES: "Montant"
        colonnes = ("ID_Article", "ID_Unite", "ID_Magasin", "Code Article", "Désignation", "Magasin", "Unité", "Remise (Ar)", "Prix Unitaire", "Quantité Vente", "Montant")
        self.tree_details = ttk.Treeview(tree_frame, columns=colonnes, show='headings')
        self.tree_details.tag_configure("even", background="#FFFFFF", foreground="#000000")
        self.tree_details.tag_configure("odd", background="#E6EFF8", foreground="#000000")
        
        for col in colonnes:
            self.tree_details.heading(col, text=col.replace('_', ' ').title())
            if "ID" in col:
                 self.tree_details.column(col, width=0, stretch=False) 
            elif "Quantité" in col or "Prix" in col:
                 self.tree_details.column(col, width=100, anchor='e')
            elif "Montant" in col: 
                 self.tree_details.column(col, width=100, anchor='e')
            elif "Désignation" in col:
                 self.tree_details.column(col, width=150, anchor='w')
            else:
                 self.tree_details.column(col, width=100, anchor='w')
        
        # Scrollbar
        scrollbar = ctk.CTkScrollbar(tree_frame, command=self.tree_details.yview)
        scrollbar_x = ctk.CTkScrollbar(tree_frame, orientation="horizontal", command=self.tree_details.xview)
        self.tree_details.configure(yscrollcommand=scrollbar.set)
        self.tree_details.configure(xscrollcommand=scrollbar_x.set)
        
        self.tree_details.grid(row=0, column=0, sticky="nsew", padx=(2, 2), pady=1)
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 2), pady=1)
        scrollbar_x.grid(row=1, column=0, sticky="ew", padx=(2, 2), pady=(0, 1))
        
        # Bindings
        self.tree_details.bind('<Double-1>', self.modifier_detail)

        # --------------------------------------------------------------------------
        # --- NOUVEAU: Frame des Totaux (Lot 4) ---
        # --------------------------------------------------------------------------
        totals_frame = ctk.CTkFrame(self)
        totals_frame.grid(row=4, column=0, padx=2, pady=(0, 2), sticky="ew")
        totals_frame.grid_columnconfigure(0, weight=1) # Pour le total en lettres
        totals_frame.grid_columnconfigure(1, weight=0) # Pour le total général (à droite)

        # Total en Lettres (Côté gauche)
        ctk.CTkLabel(totals_frame, text="Total en Lettres:", font=ctk.CTkFont(family="Segoe UI", weight="bold")).grid(row=0, column=0, padx=2, pady=2, sticky="nw")
        self.label_total_lettres = ctk.CTkLabel(totals_frame, text="Zéro Ariary", wraplength=700, justify="left", 
                                                font=ctk.CTkFont(family="Segoe UI", slant="italic"))
        self.label_total_lettres.grid(row=1, column=0, padx=2, pady=2, sticky="ew")
        
        # Total Général (Côté droit)
        right_total_frame = ctk.CTkFrame(totals_frame, fg_color="transparent")
        right_total_frame.grid(row=0, column=1, rowspan=1, padx=2, pady=2, sticky="ne")
        
        ctk.CTkLabel(right_total_frame, text="TOTAL GÉNÉRAL en Ar: ", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), fg_color="transparent").pack(side="left", padx=2, pady=2)
        self.label_total_general = ctk.CTkLabel(right_total_frame, text=self.formater_nombre(0.0), 
                                               font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color="#d32f2f")
        self.label_total_general.pack(side="right", padx=2, pady=2)
        
        # Montant en FMG (sous le TOTAL GÉNÉRAL)
        fmg_frame = ctk.CTkFrame(totals_frame, fg_color="transparent")
        fmg_frame.grid(row=1, column=1, padx=5, pady=(0, 5), sticky="ne")
        
        ctk.CTkLabel(fmg_frame, text="Montant en FMG:", font=ctk.CTkFont(family="Segoe UI", size=12), fg_color="transparent").pack(side="left", padx=5)
        self.label_montant_fmg = ctk.CTkLabel(fmg_frame, text=self.formater_nombre(0.0), 
                                             font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#1976d2")
        self.label_montant_fmg.pack(side="right", padx=5)
        # --------------------------------------------------------------------------

        # --- Frame de Boutons (Lot 5 - Anciennement Lot 4) ---
        btn_action_frame = ctk.CTkFrame(self)
        btn_action_frame.grid(row=5, column=0, padx=10, pady=10, sticky="ew")
        btn_action_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=0)
        btn_action_frame.grid_columnconfigure(5, weight=1)
        
        self.btn_nouveau_bs = ctk.CTkButton(btn_action_frame, text="📄 Nouvelle Facture", 
                       command=self.nouveau_facture, 
                       fg_color="#0288d1", hover_color="#01579b")
        self.btn_nouveau_bs.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.btn_creer_avoir = ctk.CTkButton(
            btn_action_frame, 
            text="🧾 Créer Avoir", 
            command=self.tentative_ouverture_avoir, 
            fg_color="#e11d48"
        )
        self.btn_creer_avoir.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        self.btn_supprimer_ligne = ctk.CTkButton(btn_action_frame, text="🗑️ Supprimer Ligne", command=self.supprimer_detail, 
                                                 fg_color="#d32f2f", hover_color="#b71c1c")
        self.btn_supprimer_ligne.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        # Ajouter l'appel à la vérification des droits à la fin de setup_ui
        self.entry_remise.bind("<Button-1>", lambda e: self.verifier_droits_admin() if str(self.entry_remise.cget("state")) == "disabled" else None)
        
        self.btn_creer_proforma = ctk.CTkButton(btn_action_frame, text="📄 Créer Proforma", 
                               command=self._ouvrir_page_proforma, 
                               fg_color="#29CC00", hover_color="#00CC7A")
        self.btn_creer_proforma.grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.btn_creer_proforma.grid_remove()  # Cacher le bouton "Créer Proforma"

        # self.btn_imprimer = ctk.CTkButton(btn_action_frame, text="🖨️ Imprimer Facture", command=self.open_impression_dialogue, 
                                          # fg_color="#00695c", hover_color="#004d40", state="disabled")
        # self.btn_imprimer.grid(row=0, column=3, padx=5, pady=5, sticky="ew") 
        
        self.btn_enregistrer = ctk.CTkButton(btn_action_frame, text="💾 Enregistrer la Facture", command=self._on_enregistrer_click, 
                             font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"))
        self.btn_enregistrer.grid(row=0, column=5, padx=5, pady=5, sticky="e")

        # Initialisation des totaux
        self.calculer_totaux()

    def _on_resize_vente_layout(self, event=None):
        """Ajuste quelques éléments UI lors du redimensionnement."""
        try:
            if hasattr(self, "label_total_lettres"):
                # Garde le texte lisible sans sortir du cadre.
                new_wrap = max(300, self.winfo_width() - 420)
                self.label_total_lettres.configure(wraplength=new_wrap)

            if hasattr(self, "tree_details") and self.tree_details.winfo_exists():
                total_width = self.tree_details.winfo_width()
                # Ajuste dynamiquement le nombre de lignes visibles pour laisser
                # toujours de la place aux totaux/boutons en bas.
                available_h = max(180, self.winfo_height() - 380)
                row_height = 24
                visible_rows = max(6, min(22, int(available_h / row_height)))
                self.tree_details.configure(height=visible_rows)

                if total_width > 600:
                    self.tree_details.column("Désignation", width=max(180, int(total_width * 0.22)))
                    self.tree_details.column("Magasin", width=max(120, int(total_width * 0.14)))
                    self.tree_details.column("Code Article", width=max(110, int(total_width * 0.11)))
                    self.tree_details.column("Unité", width=max(90, int(total_width * 0.09)))
                    self.tree_details.column("Prix Unitaire", width=max(110, int(total_width * 0.11)))
                    self.tree_details.column("Quantité Vente", width=max(110, int(total_width * 0.11)))
                    self.tree_details.column("Remise (Ar)", width=max(100, int(total_width * 0.10)))
                    self.tree_details.column("Montant", width=max(120, int(total_width * 0.12)))
        except Exception:
            pass
        
    def verifier_droits_admin(self):
        """Demande un code d'autorisation pour activer la Remise et l'Avoir."""
        # On commence par tout désactiver par sécurité
        self.btn_creer_avoir.configure(state="disabled")
        self.entry_remise.configure(state="disabled")

        # Ouvrir la boîte de dialogue pour demander le code
        dialog = PasswordDialog("Autorisation requise", "Veuillez saisir le code d'autorisation :")
        code_saisi = dialog.result

        if not code_saisi:
            return

        conn = self.connect_db()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            # Vérification du code dans la colonne "code" de tb_codeautorisation
            cursor.execute("SELECT id FROM tb_codeautorisation WHERE code = %s", (code_saisi,))
            auth_data = cursor.fetchone()

            if auth_data:
                # Si le code est correct, on active les fonctionnalités
                self.btn_creer_avoir.configure(state="normal")
                self.entry_remise.configure(state="normal")
                messagebox.showinfo("Succès", "Accès accordé aux remises et avoirs.")
            else:
                messagebox.showerror("Erreur", "Code d'autorisation incorrect.")
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur de vérification : {str(e)}")
        finally:
            conn.close()
            
    def verifier_alerte_stock_silencieuse(self):
        """Vérifie le stock et affiche/cache la cloche de notification"""
        conn = self.connect_db()
        if conn:
            try:
                cursor = conn.cursor()
                # On cherche s'il existe au moins un article dont le stock <= alertdepot
                query = "SELECT COUNT(*) FROM tb_article WHERE deleted = 0 AND alertdepot >= 0" 
                cursor.execute(query)
                count = cursor.fetchone()[0]
        
                if count > 0:
                    # 1. On affiche la cloche si elle était cachée
                    self.notif_stock_depot.pack(side="right", padx=20)
                    self.notif_stock_depot.configure(text_color="red")
                
                    # 2. Optionnel : Son d'alerte
                    try:
                        import winsound
                        winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS)
                    except: pass
                else:
                    # On cache la cloche s'il n'y a plus d'alerte
                    self.notif_stock_depot.pack_forget()
            
            except Exception as e:
                print(f"Erreur vérification stock: {e}")
            finally: 
                conn.close()

        # Vérifier toutes les 5 minutes (300 000 ms)
        self.after(300000, self.verifier_alerte_stock_silencieuse)
    
    def sort_tree(self, tree, col):
        """
        Trie les éléments du treeview selon la colonne `col`.
        - Pour 'Montant Total' : tri numérique
        - Pour 'Date' : tri par date au format JJ/MM/AAAA
        Cette fonction bascule l'ordre à chaque appel.
        """
        # Récupérer les enfants
        children = tree.get_children('')
        # Construire liste (valeur, item)
        vals = []
        for k in children:
            v = tree.set(k, col)
            vals.append((v, k))
        reverse = getattr(tree, "_sort_reverse_" + col, False)
        # Détection type
        try:
            if col == "Montant Total":
                def keyfn(x):
                    txt = x[0] or "0"
                    txt = txt.replace(" ", "").replace(".", "").replace(",", ".")
                    return float(txt) if txt not in ("", None) else 0.0
            elif col == "Date":
                from datetime import datetime as _dt
                def keyfn(x):
                    txt = x[0] or ""
                    try:
                        return _dt.strptime(txt, "%d/%m/%Y")
                    except:
                        return _dt.min
            else:
                def keyfn(x):
                    return x[0] or ""
            vals.sort(key=keyfn, reverse=reverse)
        except Exception:
            # fallback to string sort
            vals.sort(reverse=reverse)
        # reposition
        for index, (_, item) in enumerate(vals):
            tree.move(item, '', index)
        # toggle reverse flag
        setattr(tree, "_sort_reverse_" + col, not reverse)

    def open_recherche_client(self):
        fen = ctk.CTkToplevel(self)
        fen.title("Rechercher un client")
        fen.geometry("500x500")
        fen.grab_set()

        frame = ctk.CTkFrame(fen)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(frame, text="Rechercher un client :", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")).pack(pady=10)

        # Entrée de recherche + filtre type
        top_filter_frame = ctk.CTkFrame(frame, fg_color="transparent")
        top_filter_frame.pack(fill="x", padx=10, pady=10)
        top_filter_frame.grid_columnconfigure(0, weight=1)

        entry_search = ctk.CTkEntry(top_filter_frame, placeholder_text="Nom client...")
        entry_search.grid(row=0, column=0, padx=(0, 8), pady=0, sticky="ew")

        type_filter_combo = ctk.CTkComboBox(
            top_filter_frame,
            values=["Client à crédit", "Client au comptant", "Tous les types"],
            width=180,
            state="readonly"
        )
        type_filter_combo.set("Client à crédit")
        type_filter_combo.grid(row=0, column=1, padx=0, pady=0, sticky="e")

        # 1. Définition du Style d'abord
        style = ttk.Style()
        style.configure("ClientTreeview.Treeview", rowheight=22, font=('Segoe UI', 8))
        style.configure("ClientTreeview.Treeview.Heading", font=('Segoe UI', 8, 'bold'))

        # 2. Création de l'objet Treeview (INDISPENSABLE avant la configuration)
        colonnes = ("ID", "Nom Client", "Contact", "Adresse")
        tree = ttk.Treeview(frame, columns=colonnes, show="headings", height=15, style="ClientTreeview.Treeview")
        tree.tag_configure("even", background="#FFFFFF", foreground="#000000")
        tree.tag_configure("odd", background="#E6EFF8", foreground="#000000")

        # 3. Configuration des colonnes et en-têtes
        tree.heading("ID", text="ID")
        tree.heading("Nom Client", text="Nom Client")
        tree.heading("Contact", text="Contact")
        tree.heading("Adresse", text="Adresse")
        tree.column("ID", width=50, anchor="center") # Évitez width=0 si vous voulez debugger au début
        tree.column("Nom Client", width=220, anchor="w")
        tree.column("Contact", width=150, anchor="w")
        tree.column("Adresse", width=280, anchor="w")
        tree.pack(fill="both", expand=True, pady=10)

        def charger_clients(_event=None):
            filtre = entry_search.get().strip()
            for item in tree.get_children():
                tree.delete(item)

            conn = self.connect_db()
            if not conn: return
            try:
                cursor = conn.cursor()
                filtre_like = f"%{filtre}%"
                selected_type = type_filter_combo.get()
                type_condition = ""
                if selected_type == "Client à crédit":
                    type_condition = " AND COALESCE(idtypeclient, 1) = 2 "
                elif selected_type == "Client au comptant":
                    type_condition = " AND COALESCE(idtypeclient, 1) = 1 "

                cursor.execute("""
                    SELECT
                        idclient,
                        nomcli,
                        CASE
                            WHEN COALESCE(idtypeclient, 1) = 1 AND (contactcli IS NULL OR TRIM(contactcli) = '')
                                THEN 'Aucun contact enregistré'
                            ELSE COALESCE(NULLIF(TRIM(contactcli), ''), 'Aucun contact enregistré')
                        END AS contact_affiche,
                        CASE
                            WHEN COALESCE(idtypeclient, 1) = 1 AND (adressecli IS NULL OR TRIM(adressecli) = '')
                                THEN 'Aucun adrresse enregistré'
                            ELSE COALESCE(NULLIF(TRIM(adressecli), ''), 'Aucun adrresse enregistré')
                        END AS adresse_affiche
                    FROM tb_client
                    WHERE deleted = 0 AND nomcli ILIKE %s
                """ + type_condition + """
                    ORDER BY nomcli
                """, (filtre_like,))
                clients = cursor.fetchall()
                for idx, (id_client, nom_client, contact, adresse) in enumerate(clients):
                    zebra_tag = "even" if idx % 2 == 0 else "odd"
                    tree.insert("", "end", values=(id_client, nom_client, contact, adresse), tags=(zebra_tag,))
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors du chargement des clients: {str(e)}")
            finally:
                conn.close()

        entry_search.bind('<KeyRelease>', charger_clients)
        type_filter_combo.configure(command=lambda _v: charger_clients())

        def valider_selection():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Attention", "Veuillez sélectionner un client")
                return

            values = tree.item(selection[0])['values']
            id_client = values[0]
            nom_client = values[1]
            
            # Mise à jour de l'Entry Client
            self.entry_client.delete(0, "end")
            self.entry_client.insert(0, nom_client)

            # Mise à jour de la map (si le client était nouveau, il a déjà été ajouté dans enregistrer_facture)
            self.client_map[nom_client] = id_client

            fen.destroy()

        tree.bind('<Double-Button-1>', lambda e: valider_selection())

        # Boutons
        btn_frame = ctk.CTkFrame(frame)
        btn_frame.pack(fill="x", pady=5)
        btn_annuler = ctk.CTkButton(btn_frame, text="❌ Annuler", command=fen.destroy, fg_color="#d32f2f", hover_color="#b71c1c")
        btn_annuler.pack(side="left", padx=5, pady=5)
        btn_valider = ctk.CTkButton(btn_frame, text="✅ Valider", command=valider_selection, fg_color="#2e7d32", hover_color="#1b5e20")
        btn_valider.pack(side="right", padx=5, pady=5)

        charger_clients()

    def generer_reference(self):
        """Génère la référence de la facture (ex: 2023-FA-00001)."""
        if self.mode_modification and self.idvente_charge:
            return # Ne pas régénérer la référence en mode modification
            
        conn = self.connect_db()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            annee = datetime.now().year
            
            # Trouver la dernière référence de l'année
            cursor.execute("""
                SELECT refvente FROM tb_vente 
                WHERE refvente ILIKE %s 
                ORDER BY id DESC 
                LIMIT 1
            """, (f"%{annee}-FA-%",))
            
            derniere_ref = cursor.fetchone()
            nouveau_numero = 1
            
            if derniere_ref:
                parts = derniere_ref[0].split('-')
                if len(parts) == 3 and parts[1] == 'FA':
                    try:
                        partie_num = parts[-1]
                        nouveau_numero = int(partie_num) + 1
                    except ValueError:
                        nouveau_numero = 1
            
            nouvelle_ref = f"{annee}-FA-{nouveau_numero:05d}"
            
            self.entry_ref_vente.configure(state="normal")
            self.entry_ref_vente.delete(0, "end")
            self.entry_ref_vente.insert(0, nouvelle_ref)
            self.entry_ref_vente.configure(state="readonly")

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la génération de la référence: {str(e)}")
        finally:
            conn.close()

    def charger_magasins(self):
        """Charge les magasins pour le combobox."""
        conn = self.connect_db()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT idmag, designationmag FROM tb_magasin WHERE deleted = 0 ORDER BY designationmag")
            magasins = cursor.fetchall()
            self.magasin_map = {nom: id_ for id_, nom in magasins}
            self.magasin_ids = [id_ for id_, nom in magasins]
            noms_magasins = list(self.magasin_map.keys())
        
            # 🔥 INITIALISER LE COMBOBOX DE LIGNE
            self.combo_magasin.configure(values=noms_magasins)
            if noms_magasins:
                idmag_defaut_user = None
                if self.id_user_connecte is not None:
                    cursor.execute(
                        "SELECT idmag FROM tb_users WHERE iduser = %s AND deleted = 0",
                        (self.id_user_connecte,)
                    )
                    user_row = cursor.fetchone()
                    if user_row:
                        idmag_defaut_user = user_row[0]

                nom_magasin_defaut = next(
                    (nom for nom, id_ in self.magasin_map.items() if id_ == idmag_defaut_user),
                    None
                )
                self.combo_magasin.set(nom_magasin_defaut if nom_magasin_defaut else noms_magasins[0])
            else:
                self.combo_magasin.set("Aucun magasin trouvé")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des magasins: {str(e)}")
        finally:
            conn.close()

    def charger_client(self):
        """Charge uniquement la map des clients pour la recherche"""
        conn = self.connect_db()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT idclient, nomcli FROM tb_client WHERE deleted = 0 ORDER BY nomcli")
            clients = cursor.fetchall()
            self.client_map = {nom: id_ for id_, nom in clients}
            self.client_ids = [id_ for id_, nom in clients]
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des clients: {str(e)}")
        finally:
            conn.close()

    def charger_infos_societe(self):
        """Charge les informations de la société pour l'impression."""
        conn = self.connect_db()
        if not conn: 
            self.infos_societe = {}  # ✅ Initialiser avec un dict vide
            return
    
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT nomsociete, adressesociete, villesociete, contactsociete, nifsociete, statsociete, cifsociete, ambleme, autre FROM tb_infosociete LIMIT 1")
            info = cursor.fetchone()
            if info:
                self.infos_societe = {
                'nomsociete': info[0],
                'adressesociete': info[1],
                'villesociete': info[2],
                'contactsociete': info[3],
                'nifsociete': info[4],
                'statsociete': info[5],
                'cifsociete': info[6],
                'ambleme': info[7],
                'autre': info[8]
            }
            else:
                # ✅ Si aucune info trouvée, initialiser avec des valeurs par défaut
                self.infos_societe = {
                'nomsociete': 'NOM SOCIÉTÉ',
                'adressesociete': 'N/A',
                'villesociete': 'N/A',
                'contactsociete': 'N/A',
                'nifsociete': 'N/A',
                'statsociete': 'N/A',
                'cifsociete': 'N/A',
                'ambleme': '',
                'autre': ''
            }
        except Exception as e:
            messagebox.showwarning("Avertissement", f"Impossible de charger les infos société pour l'impression: {str(e)}")
            # ✅ En cas d'erreur, initialiser avec des valeurs par défaut
            self.infos_societe = {
            'nomsociete': 'NOM SOCIÉTÉ',
            'adressesociete': 'N/A',
            'villesociete': 'N/A',
            'contactsociete': 'N/A',
            'nifsociete': 'N/A',
            'statsociete': 'N/A',
            'cifsociete': 'N/A',
            'ambleme': '',
            'autre': ''
            }
        finally:
            cursor.close()
            conn.close()

    def open_recherche_article(self):
        """Ouvre une fenêtre pour rechercher et sélectionner un article."""
        if self.index_ligne_selectionnee is not None:
            messagebox.showwarning("Attention", "Veuillez d'abord valider ou annuler la modification de la ligne en cours")
            return

        fenetre_recherche = ctk.CTkToplevel(self)
        fenetre_recherche.title("Rechercher un article pour la sortie")
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
        fenetre_recherche.after(100, entry_search.focus_set)  # Focus automatique sur la barre de recherche (après affichage)

        # Treeview
        tree_frame = ctk.CTkFrame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))

        colonnes = ("ID_Article", "ID_Unite", "Code", "Désignation", "Unité", "Prix Unitaire", "Stock")
        tree = ttk.Treeview(tree_frame, columns=colonnes, show='headings', height=15)
        tree.tag_configure("even", background="#FFFFFF", foreground="#000000")
        tree.tag_configure("odd", background="#E6EFF8", foreground="#000000")
    
        style = ttk.Style()
        style.configure("Treeview", rowheight=22, font=('Segoe UI', 8)) 
        style.configure("Treeview.Heading", font=('Segoe UI', 8, 'bold'))

        tree.heading("ID_Article", text="ID_Article")
        tree.heading("ID_Unite", text="ID_Unite")
        tree.heading("Code", text="Code")
        tree.heading("Désignation", text="Désignation")
        tree.heading("Prix Unitaire", text="Prix Unitaire")
        tree.heading("Unité", text="Unité")
        tree.heading("Stock", text="Stock Magasin")
    
        tree.column("ID_Article", width=0, stretch=False)
        tree.column("ID_Unite", width=0, stretch=False)
        tree.column("Code", width=150, anchor='w')
        tree.column("Désignation", width=350, anchor='w')
        tree.column("Prix Unitaire", width=100, anchor='e')
        tree.column("Unité", width=100, anchor='w')
        tree.column("Stock", width=120, anchor='e')

        scrollbar = ctk.CTkScrollbar(tree_frame, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
        # Fonction de chargement
        def charger_articles(filtre=""):
            for item in tree.get_children():
                tree.delete(item)

            conn = self.connect_db()
            if not conn: return
            try:
                cursor = conn.cursor()
                filtre_like = f"%{filtre}%"
                magasin_selectionne_nom = self.combo_magasin.get()
                idmag_selectionne = self.magasin_map.get(magasin_selectionne_nom)
                heading_stock = f"Magasin '{magasin_selectionne_nom}'" if magasin_selectionne_nom else "Stock Magasin"
                tree.heading("Stock", text=heading_stock)

                if not idmag_selectionne:
                    return
            
                # Requête consolidée (inclut consommations et échanges, coefficient hiérarchique)
                query = """
                WITH mouvements_bruts AS (
                    -- Réceptions
                    SELECT lf.idarticle, lf.idmag, COALESCE(u.qtunite, 1) AS qtunite_source, lf.qtlivrefrs AS quantite, 'reception' AS type_mouvement
                    FROM tb_livraisonfrs lf
                    INNER JOIN tb_unite u ON lf.idarticle = u.idarticle AND lf.idunite = u.idunite
                    WHERE lf.deleted = 0

                    UNION ALL

                    -- Ventes validées
                    SELECT vd.idarticle, v.idmag, COALESCE(u.qtunite, 1) AS qtunite_source, vd.qtvente AS quantite, 'vente' AS type_mouvement
                    FROM tb_ventedetail vd
                    INNER JOIN tb_vente v ON vd.idvente = v.id AND v.deleted = 0 AND v.statut = 'VALIDEE'
                    INNER JOIN tb_unite u ON vd.idarticle = u.idarticle AND vd.idunite = u.idunite
                    WHERE vd.deleted = 0

                    UNION ALL

                    -- Transferts entrants
                    SELECT t.idarticle, t.idmagentree AS idmag, COALESCE(u.qtunite, 1) AS qtunite_source, t.qttransfert AS quantite, 'transfert_in' AS type_mouvement
                    FROM tb_transfertdetail t
                    INNER JOIN tb_unite u ON t.idarticle = u.idarticle AND t.idunite = u.idunite
                    WHERE t.deleted = 0

                    UNION ALL

                    -- Transferts sortants
                    SELECT t.idarticle, t.idmagsortie AS idmag, COALESCE(u.qtunite, 1) AS qtunite_source, t.qttransfert AS quantite, 'transfert_out' AS type_mouvement
                    FROM tb_transfertdetail t
                    INNER JOIN tb_unite u ON t.idarticle = u.idarticle AND t.idunite = u.idunite
                    WHERE t.deleted = 0

                    UNION ALL

                    -- Sorties (BS)
                    SELECT sd.idarticle, sd.idmag, COALESCE(u.qtunite, 1) AS qtunite_source, sd.qtsortie AS quantite, 'sortie' AS type_mouvement
                    FROM tb_sortiedetail sd
                    INNER JOIN tb_unite u ON sd.idarticle = u.idarticle AND sd.idunite = u.idunite
                    WHERE sd.deleted = 0

                    UNION ALL

                    -- Inventaires (une seule fois par article via unité de base)
                    SELECT u.idarticle, i.idmag, COALESCE(u.qtunite, 1) AS qtunite_source, i.qtinventaire AS quantite, 'inventaire' AS type_mouvement
                    FROM tb_inventaire i
                    INNER JOIN tb_unite u ON i.codearticle = u.codearticle
                    WHERE u.idunite IN (
                        SELECT DISTINCT ON (idarticle) idunite FROM tb_unite WHERE deleted = 0 ORDER BY idarticle, qtunite ASC
                    )

                    UNION ALL

                    -- Avoirs
                    SELECT ad.idarticle, ad.idmag, COALESCE(u.qtunite, 1) AS qtunite_source, ad.qtavoir AS quantite, 'avoir' AS type_mouvement
                    FROM tb_avoir a
                    INNER JOIN tb_avoirdetail ad ON a.id = ad.idavoir
                    INNER JOIN tb_unite u ON ad.idarticle = u.idarticle AND ad.idunite = u.idunite
                    WHERE a.deleted = 0 AND ad.deleted = 0

                    UNION ALL

                    -- Consommation interne
                    SELECT cd.idarticle, cd.idmag, COALESCE(u.qtunite, 1) AS qtunite_source, cd.qtconsomme AS quantite, 'consommation_interne' AS type_mouvement
                    FROM tb_consommationinterne_details cd
                    INNER JOIN tb_unite u ON cd.idarticle = u.idarticle AND cd.idunite = u.idunite

                    UNION ALL

                    -- Échanges entrée
                    SELECT dce.idarticle, dce.idmagasin AS idmag, COALESCE(u.qtunite, 1) AS qtunite_source, dce.quantite_entree AS quantite, 'echange_entree' AS type_mouvement
                    FROM tb_detailchange_entree dce
                    INNER JOIN tb_unite u ON dce.idarticle = u.idarticle AND dce.idunite = u.idunite

                    UNION ALL

                    -- Échanges sortie
                    SELECT dcs.idarticle, dcs.idmagasin AS idmag, COALESCE(u.qtunite, 1) AS qtunite_source, dcs.quantite_sortie AS quantite, 'echange_sortie' AS type_mouvement
                    FROM tb_detailchange_sortie dcs
                    INNER JOIN tb_unite u ON dcs.idarticle = u.idarticle AND dcs.idunite = u.idunite
                ),

                -- On agrège par idarticle pour le magasin sélectionné uniquement
                solde_base AS (
                    SELECT idarticle,
                        SUM(
                            CASE
                                WHEN type_mouvement IN ('reception','transfert_in','inventaire','avoir','echange_entree') THEN quantite * qtunite_source
                                WHEN type_mouvement IN ('vente','sortie','transfert_out','consommation_interne','echange_sortie') THEN - quantite * qtunite_source
                                ELSE 0
                            END
                        ) AS solde_global
                    FROM mouvements_bruts
                    WHERE idmag = %s
                    GROUP BY idarticle
                ),

                -- CTE pour la hiérarchie des unités et calcul du coefficient cumulatif
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
                        ) AS coeff_hierarchique
                    FROM unite_hierarchie
                ),

                -- ✅ Récupérer SEULEMENT le dernier prix pour chaque (idarticle, idunite)
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
                    COALESCE(p.prix, 0) AS prix,
                    ROUND(COALESCE(sb.solde_global, 0) / NULLIF(COALESCE(uc.coeff_hierarchique, 1), 0)) AS stock_total
                FROM tb_article a
                INNER JOIN tb_unite u ON a.idarticle = u.idarticle
                LEFT JOIN unite_coeff uc ON uc.idarticle = u.idarticle AND uc.idunite = u.idunite
                LEFT JOIN solde_base sb ON sb.idarticle = u.idarticle
                LEFT JOIN dernier_prix p ON a.idarticle = p.idarticle AND u.idunite = p.idunite AND p.rn = 1
                WHERE a.deleted = 0 AND (u.codearticle ILIKE %s OR a.designation ILIKE %s)
                ORDER BY a.designation ASC, u.codearticle ASC
                """

                
                cursor.execute(query, (idmag_selectionne, filtre_like, filtre_like))
                articles = cursor.fetchall()

                # On insère directement les données reçues
                for idx, row in enumerate(articles):
                    zebra_tag = "even" if idx % 2 == 0 else "odd"
                    tree.insert('', 'end', values=(
                        row[0], # idarticle
                        row[1], # idunite
                        row[2] or "", # code
                        row[3] or "", # désignation
                        row[4] or "", # unité
                        self.formater_nombre(row[5]), # prix (déjà calculé en SQL)
                        self.formater_nombre(row[6])  # stock (déjà lu dans tb_stock)
                    ), tags=(zebra_tag,))

            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur chargement: {str(e)}")
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
            stock_texte = values[6]
            stock_reel = self.parser_nombre(stock_texte)
            print(f"[DEBUG] Stock récupéré (sélection article): {stock_reel} | brut='{stock_texte}'")

            if stock_reel <= 0:
                if not messagebox.askyesno(
                    "Avertissement",
                    f"Quantité en stock insuffisante ({stock_texte} {values[4]}).\n"
                    "Voulez-vous continuer quand même ?",
                    icon="warning"
                ):
                    return
        
            article_data = {
                'idarticle': values[0],
                'nom_article': values[3],
                'idunite': values[1],
                'nom_unite': values[4],
                'code_article': values[2]
            }
            # Utilise le prix unitaire affiché dans la liste
            last_price = self.parser_nombre(values[5])
            article_data['prixunit'] = last_price
            article_data['stock_temporaire'] = stock_reel
            self.stock_temporaire_selection = stock_reel
        
            fenetre_recherche.destroy()
            self.on_article_selected(article_data)

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
        
             
        

    # --- GESTION DU DÉTAIL DE SORTIE (MÉTHODES CORRIGÉES) ---

    def on_article_selected(self, article_data):
        """Met à jour les champs après sélection d'un article."""
        self.article_selectionne = article_data
        self.stock_temporaire_selection = article_data.get("stock_temporaire", self.stock_temporaire_selection)

        # Affichage Article
        designation_complete = f"[{article_data.get('code_article', 'N/A')}] {article_data['nom_article']}"
        self.entry_article.configure(state="normal")
        self.entry_article.delete(0, "end")
        self.entry_article.insert(0, designation_complete)
        self.entry_article.configure(state="readonly")

        # Affichage unité
        self.entry_unite.configure(state="normal")
        self.entry_unite.delete(0, "end")
        self.entry_unite.insert(0, article_data['nom_unite'])
        self.entry_unite.configure(state="readonly")
    
        # --- Récupération prix unitaire automatique ---
        prix = article_data.get("prixunit", 0.0)
        prix_format = self.formater_nombre(prix)
        self.entry_prixunit.configure(state="normal")
        self.entry_prixunit.delete(0, "end")
        self.entry_prixunit.insert(0, prix_format)
        self.entry_prixunit.configure(state="readonly")
    
        # Reset quantité et focus - laisser le champ vide pour saisie manuelle
        self.entry_qtvente.delete(0, "end")
        self.entry_qtvente.focus_set()

        # ✅ NOUVEAU : Appeler le callback pour afficher le stock par dépôt
        if hasattr(self, 'on_article_selected_callback') and self.on_article_selected_callback:
            try:
                self.on_article_selected_callback(
                    article_data['idarticle'],
                    article_data['idunite'],
                    article_data.get('code_article', ''),
                    article_data['nom_article'],
                    article_data['nom_unite'],
                    check_only=False
                )
            except Exception as e:
                print(f"Erreur callback stock: {e}")

    def format_detail_for_treeview(self, detail):
        """Formate le dictionnaire de détail en tuple pour l'affichage dans le Treeview."""
        # Remise stockée est la remise unitaire en Ariary.
        remise_unitaire = float(detail.get('remise', 0))
        qtvente = float(detail.get('qtvente', detail.get('qte', 0)))
        prixunit = float(detail.get('prixunit', 0))

        montant_ht = qtvente * prixunit
        montant_remise_total = remise_unitaire * qtvente
        montant_net = montant_ht - montant_remise_total
        if montant_net < 0:
            montant_net = 0

        # Afficher la remise au Treeview comme remise unitaire, mais conserver
        # les montants calculés (total remise et montant net) dans le dict
        return (
            detail.get('idarticle', ''),
            detail.get('idunite', ''),
            detail.get('idmag', ''),
            detail.get('code_article', 'N/A'),
            detail.get('nom_article', ''),
            detail.get('designationmag', ''),
            detail.get('nom_unite', ''),
            self.formater_nombre(remise_unitaire),
            self.formater_nombre(prixunit),
            self.formater_nombre(qtvente),
            self.formater_nombre(montant_net)
        )
    def charger_details_treeview(self):
        """Charge ou recharge les détails de vente dans le Treeview."""
        for item in self.tree_details.get_children():
            self.tree_details.delete(item)

        for idx, detail in enumerate(self.detail_vente):
            zebra_tag = "even" if idx % 2 == 0 else "odd"
            self.tree_details.insert('', 'end', values=self.format_detail_for_treeview(detail), tags=(zebra_tag,))
            
        self.calculer_totaux() # Recalculer le total après chargement

    def calculer_totaux(self):
        """Calcule et affiche le total général et le total en lettres."""
        total_general = 0.0
        for d in self.detail_vente:
            montant_ttc = float(d.get('montant_ttc', d.get('montant', 0)))
            # montant_ttc here is the net amount after absolute remise
            total_general += montant_ttc

        # Affichage du total général
        total_format = self.formater_nombre(total_general)
        self.label_total_general.configure(text=total_format)

        # Calcul et affichage du montant en FMG (TOTAL GÉNÉRAL x 5)
        montant_fmg = total_general * 5
        montant_fmg_format = self.formater_nombre(montant_fmg)
        self.label_montant_fmg.configure(text=montant_fmg_format)

        # Affichage du total en lettres
        total_lettres = nombre_en_lettres_fr(total_general)
        self.label_total_lettres.configure(text=total_lettres)

    def valider_detail(self):
        """Ajoute un article à la liste des détails de vente."""
        if not self.article_selectionne:
            messagebox.showwarning("Attention", "Veuillez d'abord sélectionner un article.")
            return

        magasin_selectionne_nom = self.combo_magasin.get()
        idmag = self.magasin_map.get(magasin_selectionne_nom)

        if not idmag:
            messagebox.showerror("Erreur", "Veuillez sélectionner un Magasin valide.")
            return
    
        # ✅ NOUVEAU : Vérification spécifique pour le Dépôt B
        autorise, message_erreur = self.verifier_unite_depot_b(
            self.article_selectionne['idarticle'], 
            self.article_selectionne['idunite']
        )
    
        if not autorise:
            messagebox.showerror("❌ Unité Non Autorisée - Dépôt B", message_erreur)
            return
    
        try:
            qtvente = self.parser_nombre(self.entry_qtvente.get())
            prixunit = self.parser_nombre(self.entry_prixunit.get())
            remise = self.parser_nombre(self.entry_remise.get() or "0")
        except ValueError:
            messagebox.showerror("Erreur", "Veuillez entrer une quantité, un prix unitaire et une remise valides.")
            return

        if qtvente <= 0:
            messagebox.showwarning("Avertissement", "La quantité vendue doit être supérieure à 0.", icon="warning")
            return

        if prixunit <= 0:
            messagebox.showwarning("Attention", "Le prix unitaire doit être positif.")
            return
    
        if remise < 0:
            messagebox.showwarning("Attention", "La remise ne peut pas être négative.")
            return

        # Vérification AVANT ajout au tableau par rapport au stock temporairement stocké lors de la sélection.
        if self.index_ligne_selectionnee is None and self.stock_temporaire_selection is not None:
            if qtvente > self.stock_temporaire_selection:
                if not messagebox.askyesno(
                    "Avertissement",
                    f"Quantité saisie ({self.formater_nombre(qtvente)} {self.article_selectionne['nom_unite']}) "
                    f"dépasse le stock disponible ({self.formater_nombre(self.stock_temporaire_selection)} {self.article_selectionne['nom_unite']}).\n"
                    "Voulez-vous continuer quand même ?",
                    icon="warning"
                ):
                    return

        # Vérification du stock
        #if self.index_ligne_selectionnee is None: 
        #    stock_disponible = self.calculer_stock_article(
        #        self.article_selectionne['idarticle'], 
        #        self.article_selectionne['idunite'], 
        #        None
        #    )
               
        #    if qtvente > stock_disponible:
        #        if not messagebox.askyesno("Stock Insuffisant", 
        #                      f"Stock disponible ({self.formater_nombre(stock_disponible)} {self.article_selectionne['nom_unite']}) est inférieur à la quantité demandée. Continuer?"):
        #            return

        # Ajout de la remise dans le dictionnaire
        nouveau_detail = {
            'idarticle': self.article_selectionne['idarticle'],
            'nom_article': self.article_selectionne['nom_article'],
            'idunite': self.article_selectionne['idunite'],
            'nom_unite': self.article_selectionne['nom_unite'],
            'code_article': self.article_selectionne['code_article'],
            'qtvente': qtvente,
            'prixunit': prixunit,
            'remise': remise,
            'designationmag': magasin_selectionne_nom,
            'idmag': idmag 
        }

        # Calculer montants (remise unitaire appliquée à la quantité)
        montant_ht = qtvente * prixunit
        montant_remise = remise * qtvente
        montant_ttc = montant_ht - montant_remise
        if montant_ttc < 0:
            montant_ttc = 0

        nouveau_detail['montant_ht'] = montant_ht
        nouveau_detail['montant_remise'] = montant_remise
        nouveau_detail['montant_ttc'] = montant_ttc

        if self.index_ligne_selectionnee is not None:
            self.detail_vente[self.index_ligne_selectionnee] = nouveau_detail
            self.index_ligne_selectionnee = None
        else:
            self.detail_vente.append(nouveau_detail)

        self.reset_detail_form()
        self.charger_details_treeview()

        

    def modifier_detail(self, event):
        """Charge les données d'un détail sélectionné pour modification."""
        selected_item = self.tree_details.focus()
        if not selected_item:
            return

        try:
            self.index_ligne_selectionnee = self.tree_details.index(selected_item)
            detail = self.detail_vente[self.index_ligne_selectionnee]
        except IndexError:
            messagebox.showerror("Erreur", "Erreur lors de la récupération de la ligne.")
            self.reset_detail_form()
            return

        self.article_selectionne = {
            'idarticle': detail['idarticle'],
            'nom_article': detail['nom_article'],
            'idunite': detail['idunite'],
            'nom_unite': detail['nom_unite'],
            'code_article': detail.get('code_article', 'N/A')
        }

        designation_complete = f"[{detail.get('code_article', 'N/A')}] {detail['nom_article']}"
        self.entry_article.configure(state="normal")
        self.entry_article.delete(0, "end")
        self.entry_article.insert(0, designation_complete)
        self.entry_article.configure(state="readonly")

        self.entry_unite.configure(state="normal")
        self.entry_unite.delete(0, "end")
        self.entry_unite.insert(0, detail['nom_unite'])
        self.entry_unite.configure(state="readonly")

        self.entry_remise.delete(0, "end")
        self.entry_remise.insert(0, str(detail.get('remise', 0)))

        self.entry_qtvente.delete(0, "end")
        self.entry_qtvente.insert(0, self.formater_nombre(detail['qtvente']))

        self.entry_prixunit.configure(state="normal")
        self.entry_prixunit.delete(0, "end")
        self.entry_prixunit.insert(0, self.formater_nombre(detail['prixunit']))
        self.entry_prixunit.configure(state="readonly")
        
        # Mettre à jour le combo magasin (optionnel, on suppose qu'on ne change pas le magasin en cours de modif de ligne)
        self.combo_magasin.set(detail['designationmag'])

        # Mise à jour des boutons
        self.btn_ajouter.configure(text="✔️ Valider Modif.", fg_color="#0288d1", hover_color="#01579b")
        self.btn_annuler_mod.configure(state="normal")
        self.btn_recherche_article.configure(state="disabled")

    def reset_detail_form(self):
        """Réinitialise les champs de saisie de détail."""
        self.article_selectionne = None
        self.stock_temporaire_selection = None
        self.index_ligne_selectionnee = None
        
        self.entry_article.configure(state="normal")
        self.entry_article.delete(0, "end")
        self.entry_article.configure(state="readonly")
        
        self.entry_qtvente.delete(0, "end")
        self.entry_prixunit.configure(state="normal")
        self.entry_prixunit.delete(0, "end")
        self.entry_prixunit.configure(state="readonly")
        
        self.entry_unite.configure(state="normal")
        self.entry_unite.delete(0, "end")
        self.entry_unite.configure(state="readonly")
        
        self.btn_ajouter.configure(text="➕ Ajouter", fg_color="#2e7d32", hover_color="#1b5e20")
        self.btn_annuler_mod.configure(state="disabled")
        self.btn_recherche_article.configure(state="normal")

        # Assurer que l'entrée manuelle est active si l'état Proforma est vide
        if not self.details_proforma_a_ajouter:
            self.activer_entree_manuelle()


    def supprimer_detail(self):
        """Supprime la ligne de détail sélectionnée."""
        selected_item = self.tree_details.focus()
        if not selected_item:
            messagebox.showwarning("Attention", "Veuillez sélectionner une ligne à supprimer.")
            return

        if messagebox.askyesno("Confirmation", "Êtes-vous sûr de vouloir supprimer cette ligne de détail?"):
            index = self.tree_details.index(selected_item)
            try:
                self.detail_vente.pop(index)
                self.reset_detail_form()
                self.charger_details_treeview()
            except IndexError:
                messagebox.showerror("Erreur", "Erreur lors de la suppression de la ligne.")

    def ouvrir_recherche_sortie(self):
        """Ouvre une fenêtre pour rechercher une vente existante à charger."""
        if self.mode_modification:
            messagebox.showwarning("Attention", "Veuillez d'abord terminer la modification de la facture actuelle.")
            return

        fenetre = ctk.CTkToplevel(self)
        fenetre.title("Charger une Facture pour Modification")
        fenetre.geometry("1000x500")
        fenetre.grab_set()

        main_frame = ctk.CTkFrame(fenetre)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Zone de recherche
        search_frame = ctk.CTkFrame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(search_frame, text="🔍 Rechercher N° Facture ou Client:").pack(side="left", padx=5)
        entry_search = ctk.CTkEntry(search_frame, placeholder_text="Référence ou Nom client...", width=300)
        entry_search.pack(side="left", padx=5, fill="x", expand=True)
        
        # Treeview
        tree_frame = ctk.CTkFrame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        colonnes = ("ID", "Ref Vente", "Date", "Description", "Montant Total", "Utilisateur", "Nb Lignes")
        tree = ttk.Treeview(tree_frame, columns=colonnes, show='headings', height=15)
        
        style = ttk.Style()
        style.configure("Treeview", rowheight=22, font=('Segoe UI', 8)) 
        style.configure("Treeview.Heading", font=('Segoe UI', 8, 'bold'))

        tree.heading("ID", text="ID")
        tree.heading("Ref Vente", text="N° Facture")
        tree.heading("Date", text="Date", command=lambda: self.sort_tree(tree, "Date"))
        tree.heading("Description", text="Description")
        tree.heading("Montant Total", text="Montant Total", command=lambda: self.sort_tree(tree, "Montant Total"))
        tree.heading("Utilisateur", text="Utilisateur")
        tree.heading("Nb Lignes", text="Qté Lignes")
        
        tree.column("ID", width=0, stretch=False)
        tree.column("Ref Vente", width=120, anchor='w')
        tree.column("Date", width=100, anchor='center')
        tree.column("Description", width=250, anchor='w')
        tree.column("Montant Total", width=120, anchor='e')
        tree.column("Utilisateur", width=150, anchor='w')
        tree.column("Nb Lignes", width=80, anchor='center')

        scrollbar = ctk.CTkScrollbar(tree_frame, command=tree.yview)
        tree.tag_configure("impaye", foreground="red")
        tree.tag_configure("paye", foreground="black")
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        var_filtre_impaye = ctk.BooleanVar(value=False)
        chk_impaye = ctk.CTkCheckBox(search_frame, text="Afficher seulement impayées", variable=var_filtre_impaye)
        chk_impaye.pack(side='right', padx=5)

        def _on_filtre_change(*args):
            charger_vente(entry_search.get())
        
        try:
            var_filtre_impaye.trace_add('write', _on_filtre_change)
        except Exception:
            try:
                var_filtre_impaye.trace('w', _on_filtre_change)
            except Exception:
                pass

        def charger_vente(self):
            """Charge les statistiques de vente instantanément en une seule requête"""
            self.creer_treeview() # Réinitialise le tableau avec vos nouveaux réglages
        
            conn = self.connect_db()
            if not conn: return

            try:
                cursor = conn.cursor()
                # Requête optimisée : Jointure et Somme groupée par article
                # On récupère la désignation, l'unité et la somme des ventes
                query = """
                    SELECT 
                        u.codearticle, 
                        a.designation, 
                        u.designationunite,
                        COALESCE(SUM(vd.qtvente), 0) as total_vendu,
                        COALESCE(p.prix, 0) as dernier_prix
                    FROM tb_article a
                    INNER JOIN tb_unite u ON a.idarticle = u.idarticle
                    LEFT JOIN tb_ventedetail vd ON (u.idarticle = vd.idarticle AND u.idunite = vd.idunite)
                    LEFT JOIN tb_prix p ON (u.idunite = p.idunite)
                    WHERE a.deleted = 0
                    GROUP BY u.codearticle, a.designation, u.designationunite, p.prix, p.dateregistre
                    ORDER BY a.designation ASC, p.dateregistre DESC
                """
                cursor.execute(query)
                resultats = cursor.fetchall()

                # Utilisation d'un dictionnaire pour gérer le DISTINCT ON manuellement 
                # si votre version de SQL est complexe, ou simplement itérer :
                vus = set()
                for res in resultats:
                    code = res[0]
                    if code in vus: continue # Évite les doublons de prix
                    vus.add(code)

                    vals = [
                        res[0], # Code
                        res[1], # Désignation
                        res[2], # Unité
                        self.formater_nombre(res[4]), # Prix
                        self.formater_nombre(res[3])  # Quantité Vendue
                    ]
                    self.tree.insert("", "end", values=vals)

                self.label_total_articles.configure(text=f"Articles vendus: {len(vus)}")
                self.label_derniere_maj.configure(text=f"MàJ: {datetime.now().strftime('%H:%M:%S')}")

            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur de chargement ventes : {e}")
            finally:
                conn.close()

            tree.tag_configure("impaye", foreground="red")
            tree.tag_configure("paye", foreground="black")

        def rechercher(*args):
            charger_vente(entry_search.get())

        entry_search.bind('<KeyRelease>', rechercher)

        def valider_selection():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Attention", "Veuillez sélectionner un bon de sortie")
                return

            values = tree.item(selection[0])['values']
            idvente = values[0]
            fenetre.destroy()
            self.charger_vente_modification(idvente)

        tree.bind('<Double-Button-1>', lambda e: valider_selection())

        # Boutons
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x")
        btn_annuler = ctk.CTkButton(btn_frame, text="❌ Annuler", command=fenetre.destroy, fg_color="#d32f2f", hover_color="#b71c1c")
        btn_annuler.pack(side="left", padx=5, pady=5)
        btn_valider = ctk.CTkButton(btn_frame, text="✅ Charger", command=valider_selection, fg_color="#2e7d32", hover_color="#1b5e20")
        btn_valider.pack(side="right", padx=5, pady=5)
        
        charger_vente()


    def charger_vente_modification(self, idvente: int):
        """Charge une vente existante pour modification/consultation."""
        self.nouveau_facture() # Reset complet de l'interface
    
        conn = self.connect_db()
        if not conn: return

        try:
            cursor = conn.cursor()

            # 1. Charger l'en-tête
            sql_vente = """
                SELECT v.id, v.refvente, v.dateregistre, v.description, c.nomcli, v.idclient
                FROM tb_vente v 
                LEFT JOIN tb_client c ON v.idclient = c.idclient 
                WHERE v.id = %s
            """
            cursor.execute(sql_vente, (idvente,))
            vente_row = cursor.fetchone()

            if not vente_row:
                messagebox.showerror("Erreur", "Facture introuvable.")
                return

            # ✅ Décomposer correctement les colonnes
            id_vente_db, refvente, dateregistre, description, nomcli, idclient = vente_row

            # 2. Charger les détails
            sql_details = """
                SELECT 
                    vd.idmag, m.designationmag, vd.idarticle, u.codearticle, a.designation,
                    vd.idunite, u.designationunite, vd.qtvente, vd.prixunit, COALESCE(vd.remise, 0) as remise
                FROM tb_ventedetail vd 
                INNER JOIN tb_article a ON vd.idarticle = a.idarticle 
                INNER JOIN tb_unite u ON vd.idunite = u.idunite
                INNER JOIN tb_magasin m ON vd.idmag = m.idmag
                WHERE vd.idvente = %s
            """
            cursor.execute(sql_details, (idvente,))
            details = cursor.fetchall()
        
            # 3. Mettre à jour l'interface
            self.idvente_charge = idvente
            self.mode_modification = True
        
            self.entry_ref_vente.configure(state="normal")
            self.entry_ref_vente.delete(0, "end")
            self.entry_ref_vente.insert(0, refvente)
            self.entry_ref_vente.configure(state="readonly")
        
            self.entry_date_vente.delete(0, "end")
            self.entry_date_vente.insert(0, dateregistre.strftime("%d/%m/%Y"))
        
            self.entry_designation.delete(0, "end")
            self.entry_designation.insert(0, description or "")
        
            self.entry_client.delete(0, "end")
            self.entry_client.insert(0, nomcli or "Client Divers")
            if nomcli:
                self.client_map[nomcli] = idclient

            self.detail_vente = []
            for row in details:
                idmag_d, designationmag, idarticle, codearticle, designation_art, idunite, designationunite, qtvente, prixunit, remise = row
                self.detail_vente.append({
                    'idmag': idmag_d,
                    'designationmag': designationmag,
                    'idarticle': idarticle,
                    'code_article': codearticle,
                    'nom_article': designation_art,
                    'idunite': idunite,
                    'nom_unite': designationunite,
                    'qtvente': float(qtvente),      # ✅ Conversion en float
                    'prixunit': float(prixunit),    # ✅ Conversion en float
                    'remise': float(remise)         # ✅ Conversion en float
                })

            self.charger_details_treeview()

            # Mettre à jour les boutons
            self.btn_enregistrer.configure(text="🔄 Modifier la Facture", fg_color="#ff9800", hover_color="#f57c00", state="normal")
            self.btn_imprimer.configure(state="normal")
            self.btn_charger_proforma.configure(state="disabled")

            messagebox.showinfo("Chargement Réussi", f"La Facture N° {refvente} a été chargée pour modification.")

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement de la facture: {str(e)}")
            import traceback
            traceback.print_exc()
            self.nouveau_facture()
        finally:
            if 'cursor' in locals() and cursor: 
                cursor.close()
            if conn: 
                conn.close()

    def nouveau_facture(self):
        """Réinitialise le formulaire pour une nouvelle facture/bon de sortie."""
        self.generer_reference()
        self.entry_date_vente.delete(0, "end")
        self.entry_date_vente.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.entry_designation.delete(0, "end")
        self.entry_client.delete(0, "end")
        self.detail_vente = []
        self.charger_details_treeview() # Recharge le treeview vide
        self.idvente_charge = None
        self.mode_modification = False
        self.btn_enregistrer.configure(state="normal", text="💾 Enregistrer la Facture", fg_color="#2196f3", hover_color="#1976d2")
        self.btn_imprimer.configure(state="disabled")
        self.btn_charger_proforma.configure(state="normal") # Réactiver le bouton Proforma
        
        # Assurer que l'état Proforma est réinitialisé
        self.reset_proforma_state()


    def enregistrer_facture(self):
        """Sauvegarde les factures (une par magasin) dans la base de données."""
    
        # Protection contre le double-clic
        if hasattr(self, '_enregistrement_en_cours') and self._enregistrement_en_cours:
            print("⚠️ Enregistrement déjà en cours, ignoré")
            return
    
        self._enregistrement_en_cours = True
        self.btn_enregistrer.configure(state="disabled")
    
        try:
            if not self.detail_vente:
                messagebox.showwarning("Attention", "Veuillez ajouter des articles avant d'enregistrer.")
                return
        
            if self.id_user_connecte is None:
                messagebox.showerror("Erreur Critique", 
                                   "Aucun utilisateur connecté. Impossible d'enregistrer la facture.\n"
                                   "Veuillez vous reconnecter.")
                return
        
            # --- RÉCUPÉRATION DES INFOS ---
            date_vente_str = self.entry_date_vente.get()
            description = self.entry_designation.get().strip()
            client_nom = self.entry_client.get().strip()
        
            if client_nom == "":
                messagebox.showerror("Erreur", "Veuillez entrer ou choisir un client.")
                return

            conn = self.connect_db()
            if not conn: return
            cursor = conn.cursor()

            # --- ✅ NOUVEAU : VÉRIFICATION OBLIGATOIRE DU CRÉDIT CLIENT ---
            try:
                # Récupérer le crédit du client
                cursor.execute("SELECT credit FROM tb_client WHERE nomcli = %s AND deleted = 0", (client_nom,))
                result = cursor.fetchone()
                
                if result:
                    limite_credit = result[0]
                    
                    # Calculer le total global de la vente actuelle (tous magasins confondus)
                    total_general_vente = 0.0
                    for d in self.detail_vente:
                        qtvente = float(d['qtvente'])
                        prixunit = float(d['prixunit'])
                        remise = float(d.get('remise', 0))
                        montant_ligne = qtvente * prixunit - (remise * qtvente)
                        if montant_ligne < 0:
                            montant_ligne = 0
                        total_general_vente += montant_ligne
                    
                    # 🚫 BLOCAGE SI DÉPASSEMENT DU CRÉDIT
                    if limite_credit is not None and total_general_vente > limite_credit:
                        messagebox.showerror(
                            "❌ Crédit Dépassé", 
                            f"ENREGISTREMENT BLOQUÉ !\n\n"
                            f"Client : {client_nom}\n"
                            f"Montant total vente : {self.formater_nombre(total_general_vente)} Ar\n"
                            f"Crédit autorisé : {self.formater_nombre(limite_credit)} Ar\n"
                            f"Dépassement : {self.formater_nombre(total_general_vente - limite_credit)} Ar\n\n"
                            f"Veuillez réduire le montant ou augmenter le crédit du client."
                        )
                        return  # ⛔ ARRÊT DE L'ENREGISTREMENT
                else:
                    # Si le client n'existe pas encore (nouveau client), on continue car crédit = 0 par défaut
                    pass
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la vérification du crédit : {e}")
                return

            # --- SUITE DU CODE ORIGINAL (INSERTION) ---
            # 1. Gestion du Client
            idclient = self.client_map.get(client_nom)
            if not idclient: 
                try:
                    cursor.execute("""
                        INSERT INTO tb_client (nomcli, deleted) 
                        VALUES (%s, 0) RETURNING idclient
                    """, (client_nom,))
                    idclient = cursor.fetchone()[0]
                    conn.commit() # Commit pour créer le client
                    self.client_map[client_nom] = idclient
                except Exception as e:
                    conn.rollback()
                    messagebox.showerror("Erreur", f"Impossible d'ajouter le client : {e}")
                    return

            try:
                cursor = conn.cursor()
                try:
                    # Capturer la date saisie et ajouter l'heure précise actuelle
                    date_vente = datetime.strptime(date_vente_str, "%d/%m/%Y").replace(hour=datetime.now().hour, minute=datetime.now().minute, second=datetime.now().second)
                except ValueError:
                    messagebox.showerror("Erreur de Date", "Format de date invalide (attendu: JJ/MM/AAAA).")
                    return
            
                # 🔥 NOUVEAU: Grouper les détails par magasin
                details_par_magasin = {}
                for detail in self.detail_vente:
                    idmag = detail['idmag']
                    if idmag not in details_par_magasin:
                        details_par_magasin[idmag] = []
                    details_par_magasin[idmag].append(detail)
            
                # Réinitialiser le dictionnaire des IDs de vente
                self.idventes_par_magasin = {}
                factures_creees = []
            
                # 🔥 NOUVEAU: Créer une facture par magasin
                for idmag, details_mag in details_par_magasin.items():
                    # ✅ Calculer le total pour ce magasin avec conversion en float
                    total_magasin = 0
                    for d in details_mag:
                        qtvente = float(d['qtvente'])
                        prixunit = float(d['prixunit'])
                        remise = float(d.get('remise', 0))
                        montant_ligne = qtvente * prixunit - (remise * qtvente)
                        if montant_ligne < 0:
                            montant_ligne = 0
                        total_magasin += montant_ligne
                    
                    # 🔍 DEBUG: Afficher les détails du calcul pour chaque ligne
                    print(f"\n🧮 Calcul Total Magasin: {details_mag[0]['designationmag']}")
                    for d in details_mag:
                        qtvente = float(d['qtvente'])
                        prixunit = float(d['prixunit'])
                        remise = float(d.get('remise', 0))
                        montant_ht = qtvente * prixunit
                        montant_remise_ligne = remise * qtvente
                        montant_net = montant_ht - montant_remise_ligne
                        print(f"  Article: {d.get('nom_article', 'N/A')}")
                        print(f"    Qt={qtvente}, PU={prixunit:.0f}, Remise/U={remise:.0f}")
                        print(f"    Montant HT={montant_ht:.0f}, Total Remise={montant_remise_ligne:.0f}, Net={montant_net:.0f}")
                    print(f"📊 TOTAL FINAL À INSÉRER en tb_vente.totmtvente: {total_magasin:.0f} Ar\n")
        
                    # Récupérer le nom du magasin
                    nom_magasin = details_mag[0]['designationmag']
                
                    # Générer une référence unique pour ce magasin
                    annee = datetime.now().year
                    cursor.execute("""
                        SELECT refvente FROM tb_vente 
                        WHERE refvente ILIKE %s 
                        ORDER BY id DESC 
                        LIMIT 1
                    """, (f"%{annee}-FA-%",))
                
                    derniere_ref = cursor.fetchone()
                    nouveau_numero = 1
                
                    if derniere_ref:
                        parts = derniere_ref[0].split('-')
                        if len(parts) == 3 and parts[1] == 'FA':
                            try:
                                partie_num = parts[-1]
                                nouveau_numero = int(partie_num) + 1
                            except ValueError:
                                nouveau_numero = 1
                
                    ref_facture_mag = f"{annee}-FA-{nouveau_numero:05d}"
                
                    # Créer la facture pour ce magasin
                    sql_vente = """
                        INSERT INTO tb_vente (refvente, dateregistre, description, iduser, idclient, totmtvente, idmag, statut, deleted) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0) 
                        RETURNING id
                    """
                    desc_with_mag = f"{description} - {nom_magasin}"
                    params = (ref_facture_mag, date_vente, desc_with_mag, self.id_user_connecte, idclient, total_magasin, idmag, 'EN_ATTENTE')
                
                    print(f"➕ INSERT Facture pour magasin {nom_magasin}: {ref_facture_mag}")
                    cursor.execute(sql_vente, params)
                    idvente = cursor.fetchone()[0]
                
                    # Stocker l'ID de vente pour ce magasin
                    self.idventes_par_magasin[idmag] = idvente
                
                    # Insérer les détails pour cette facture
                    sql_vente_detail = """
                        INSERT INTO tb_ventedetail (idvente, idarticle, idunite, qtvente, prixunit, remise, idmag)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """
                    details_a_inserer = []
                    for detail in details_mag:
                        details_a_inserer.append((
                            idvente,
                            detail['idarticle'],
                            detail['idunite'],
                            detail['qtvente'],
                            detail['prixunit'],
                            detail.get('remise', 0),  # ✅ Ajout remise
                            detail['idmag']
                        ))

                    cursor.executemany(sql_vente_detail, details_a_inserer)
                
                    factures_creees.append({
                        'ref': ref_facture_mag,
                        'magasin': nom_magasin,
                        'total': total_magasin,
                        'idvente': idvente
                    })
                
                    print(f"✅ Facture {ref_facture_mag} créée pour {nom_magasin} - Total: {self.formater_nombre(total_magasin)} Ar")

                # Commit de toutes les factures
                conn.commit()
            
                # Message de succès avec le détail de toutes les factures
                message_factures = "\n".join([
                    f"• {f['ref']} ({f['magasin']}): {self.formater_nombre(f['total'])} Ar" 
                    for f in factures_creees
                ])
            
                total_general = sum(f['total'] for f in factures_creees)
            
                # ✅ UTILISER LES PARAMÈTRES D'IMPRESSION
                show_confirmation = self.settings.get('Vente_ImpressionConfirmation', 1)
                impression_a5 = self.settings.get('Vente_ImpressionA5', 1)
                impression_ticket = self.settings.get('Vente_ImpressionTicket', 0)
                
                if show_confirmation:
                    # Afficher la messagebox de confirmation
                    messagebox.showinfo("Succès", 
                        f"{len(factures_creees)} facture(s) créée(s) avec succès:\n\n{message_factures}\n\nTotal général: {self.formater_nombre(total_general)} Ar")
                else:
                    # Pas de confirmation, impression directe silencieuse
                    print(f"✅ {len(factures_creees)} facture(s) créée(s) avec succès (impression directe)")
            
                # --- DÉCLENCHEMENT DE L'IMPRESSION AUTOMATIQUE ---
                # Pour chaque facture créée, ouvre directement le dialogue de choix
                # de format (A5 PDF Paysage ou Ticket 80mm) via imprimer_facture_unique()
                try:
                    for facture in factures_creees:
                        if impression_a5 or impression_ticket:
                            self.imprimer_facture_avec_settings(facture['idvente'], impression_a5, impression_ticket)
                except Exception as e:
                    messagebox.showerror("Erreur Impression", f"La vente est enregistrée mais l'impression a échoué : {e}")

                # Après enregistrement: réinitialiser le formulaire pour une nouvelle facture
                try:
                    self.nouveau_facture()
                except Exception:
                    # Fallback: réactiver le bouton d'enregistrement si nouveau_facture échoue
                    try:
                        self.btn_enregistrer.configure(state="normal", text="💾 Enregistrer la Facture", fg_color="#2196f3", hover_color="#1976d2")
                    except Exception:
                        pass

            except psycopg2.errors.UniqueViolation as e:
                conn.rollback()
                messagebox.showerror(
                    "Erreur de doublon", 
                    f"Une des factures existe déjà dans la base de données.\n\nDétails: {e}"
                )
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Erreur", f"Une erreur s'est produite: {e}")
                import traceback
                traceback.print_exc()
            finally:
                if 'cursor' in locals() and cursor: cursor.close()
                if conn: conn.close()
    
        finally:
            self._enregistrement_en_cours = False
            try:
                self.btn_enregistrer.configure(state="normal")
            except Exception:
                pass

    def _on_enregistrer_click(self):
        """Garde-fou UI avant enregistrement, puis délègue à enregistrer_facture()."""
        if getattr(self, '_enregistrement_en_cours', False):
            return

        # Vérification client AVANT toute étape d'enregistrement / reset formulaire.
        client_nom = self.entry_client.get().strip()
        if client_nom == "":
            messagebox.showwarning("Attention", "Veuillez entrer ou choisir un client.")
            return

        try:
            self.btn_enregistrer.configure(state='disabled')
        except Exception:
            pass

        try:
            # Exécute le flux d'enregistrement métier existant.
            self.enregistrer_facture()
        finally:
            # Réactive le bouton si présent (enregistrer_facture gère déjà son état interne).
            try:
                self.btn_enregistrer.configure(state='normal')
            except Exception:
                pass

    def open_impression_dialogue(self):
        """Ouvre un dialogue pour choisir quelle facture imprimer."""
        if not self.idventes_par_magasin:
            messagebox.showwarning("Attention", "Veuillez d'abord enregistrer les factures.")
            return
    
        # Créer une fenêtre de sélection
        fen = ctk.CTkToplevel(self)
        fen.title("Sélectionner la facture à imprimer")
        fen.geometry("600x400")
        fen.grab_set()
    
        frame = ctk.CTkFrame(fen)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
    
        ctk.CTkLabel(frame, text="Sélectionnez la facture à imprimer:", 
                 font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")).pack(pady=10)
    
        # Liste des factures
        listbox_frame = ctk.CTkFrame(frame)
        listbox_frame.pack(fill="both", expand=True, pady=10)
    
        colonnes = ("ID Vente", "Magasin", "N° Facture", "Montant")
        tree = ttk.Treeview(listbox_frame, columns=colonnes, show='headings', height=10)
    
        tree.heading("ID Vente", text="ID")
        tree.heading("Magasin", text="Magasin")
        tree.heading("N° Facture", text="N° Facture")
        tree.heading("Montant", text="Montant")
    
        tree.column("ID Vente", width=0, stretch=False)
        tree.column("Magasin", width=200)
        tree.column("N° Facture", width=150)
        tree.column("Montant", width=150, anchor='e')
    
        tree.pack(fill="both", expand=True)
    
        # Charger les factures
        conn = self.connect_db()
        if conn:
            try:
                cursor = conn.cursor()
                for idmag, idvente in self.idventes_par_magasin.items():
                    cursor.execute("""
                        SELECT v.refvente, v.totmtvente, m.designationmag
                        FROM tb_vente v
                        INNER JOIN tb_magasin m ON v.idmag = m.idmag
                        WHERE v.id = %s
                    """, (idvente,))
                    result = cursor.fetchone()
                    if result:
                        ref, total, mag = result
                        tree.insert('', 'end', values=(idvente, mag, ref, self.formater_nombre(total)))
            finally:
                cursor.close()
                conn.close()

        def imprimer_selectionnee():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Attention", "Veuillez sélectionner une facture")
                return
        
            values = tree.item(selection[0])['values']
            idvente = values[0]
        
            fen.destroy()
            self.imprimer_facture_unique(idvente)
    
        def imprimer_toutes():
            fen.destroy()
            for idvente in self.idventes_par_magasin.values():
                self.imprimer_facture_unique(idvente)
            messagebox.showinfo("Impression", f"{len(self.idventes_par_magasin)} facture(s) générée(s).")
    
        # Boutons
        btn_frame = ctk.CTkFrame(frame)
        btn_frame.pack(fill="x", pady=10)
    
        ctk.CTkButton(btn_frame, text="❌ Annuler", command=fen.destroy, 
                  fg_color="#d32f2f", hover_color="#b71c1c").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="🖨️ Imprimer Toutes", command=imprimer_toutes,
                  fg_color="#1976d2", hover_color="#1565c0").pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="✅ Imprimer Sélection", command=imprimer_selectionnee,
                  fg_color="#2e7d32", hover_color="#1b5e20").pack(side="right", padx=5)

    def imprimer_facture_avec_settings(self, idvente: int, imprimer_a5: int, imprimer_ticket: int):
        """
        Imprime une facture directement en fonction des paramètres sans dialogue.
        imprimer_a5: 1 = imprimer A5, 0 = ne pas imprimer
        imprimer_ticket: 1 = imprimer ticket, 0 = ne pas imprimer
        """
        data = self.get_data_facture(idvente)
        
        if not data or not data.get('vente'):
            print(f"❌ Impossible de récupérer les données pour l'ID : {idvente}")
            return
        
        try:
            # Imprimer A5 si configuré
            if imprimer_a5 == 1:
                filename_a5 = f"Facture_{data['vente']['refvente']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                self.generate_pdf_a5(data, filename_a5)
                self.open_file(filename_a5)
                print(f"✅ Impression A5 lancée : {filename_a5}")
            
            # Imprimer Ticket si configuré
            if imprimer_ticket == 1:
                filename_ticket = f"Ticket_{data['vente']['refvente']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                self.generate_ticket_80mm(data, filename_ticket)
                self.open_file(filename_ticket)
                print(f"✅ Impression Ticket lancée : {filename_ticket}")
        
        except Exception as e:
            print(f"❌ Erreur lors de l'impression : {e}")
            messagebox.showerror("Erreur Impression", f"Erreur lors de l'impression de la facture : {e}")

    def imprimer_facture_unique(self, idvente: int):
        """Imprime une facture spécifique."""
        data = self.get_data_facture(idvente)
    
        if not data or not data.get('vente'):
            messagebox.showerror("Erreur", f"Impossible de récupérer les données de la facture (ID: {idvente}).")
            return
    
        try:
            choice_dialog = SimpleDialogWithChoice(
                self, 
                title="Choix du format d'impression", 
                message="Veuillez sélectionner le format de la facture à imprimer:"
            )
            result = choice_dialog.result
        except Exception as e:
            messagebox.showerror("Erreur de Dialogue", f"Impossible d'ouvrir la fenêtre de choix : {e}")
            return
    
        if result == "A5 PDF (Paysage)":
            filename = f"Facture_{data['vente']['refvente']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            self.generate_pdf_a5(data, filename)
            self.open_file(filename)
        elif result == "Ticket 80mm":
            filename = f"Ticket_{data['vente']['refvente']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            self.generate_ticket_80mm(data, filename)
            self.open_file(filename)


    def open_file(self, filename):
        """Ouvre le fichier généré avec le programme par défaut."""
        try:
            if sys.platform == 'win32':
                os.startfile(filename)
            elif sys.platform == 'darwin':
                os.system(f'open "{filename}"')
            else:
                os.system(f'xdg-open "{filename}"')
        except Exception as e:
            pass # Ignorer les erreurs d'ouverture de fichier

    def get_data_facture(self, idvente: int) -> Optional[Dict[str, Any]]:
        """Récupère toutes les données nécessaires pour l'impression d'une facture."""
        print(f"\n{'='*60}")
        print(f"🔍 GET_DATA_FACTURE - ID Vente: {idvente}")
        print(f"{'='*60}")

        conn = self.connect_db()
        if not conn:
            print("❌ ERREUR: Connexion DB impossible")
            return None

        data = {
            'societe': self.infos_societe,
            'vente': None,
            'utilisateur': None,
            'details': []
        }

        try:
            cursor = conn.cursor()

            # DEBUG: Vérifier que l'ID existe dans la table
            cursor.execute("SELECT COUNT(*) FROM tb_vente WHERE id = %s", (idvente,))
            count = cursor.fetchone()[0]
            print(f"📊 Nombre de ventes trouvées avec id={idvente}: {count}")

            # 1. Infos Vente & Client
            sql_vente = """
                SELECT 
                    v.refvente, v.dateregistre, v.description, 
                    u.nomuser, u.prenomuser, 
                    c.nomcli, c.adressecli, c.contactcli
                FROM tb_vente v 
                INNER JOIN tb_users u ON v.iduser = u.iduser 
                LEFT JOIN tb_client c ON v.idclient = c.idclient 
                WHERE v.id = %s
            """
            print(f"🔍 Exécution requête vente avec id={idvente}")
            cursor.execute(sql_vente, (idvente,))
            result = cursor.fetchone()
    
            if not result:
                print(f"❌ ERREUR: Aucune vente trouvée pour id={idvente}")
                return None
    
            print(f"✅ Vente trouvée: {result[0]}")
    
            (refvente, dateregistre, description, nomuser, prenomuser, nomcli, adressecli, contactcli) = result

            data['vente'] = {
                'refvente': refvente,
                'dateregistre': dateregistre.strftime("%d/%m/%Y %H:%M"),
                'description': description,
            }
            # Normaliser les valeurs utilisateur pour éviter d'afficher 'None' dans les PDF
            data['utilisateur'] = {
                'nomuser': nomuser or '',
                'prenomuser': prenomuser or '',
            }
            data['client'] = {
                'nomcli': nomcli or "Client Divers",
                'adressecli': adressecli or "N/A",
                'contactcli': contactcli or "N/A",
            }
    
            # 2. Détails de vente AVEC REMISE ✅
            sql_details = """
                SELECT 
                    u.codearticle, a.designation, u.designationunite, 
                    vd.qtvente, vd.prixunit, COALESCE(vd.remise, 0) as remise, m.designationmag
                FROM tb_ventedetail vd 
                INNER JOIN tb_article a ON vd.idarticle = a.idarticle 
                INNER JOIN tb_unite u ON vd.idunite = u.idunite
                INNER JOIN tb_magasin m ON vd.idmag = m.idmag
                WHERE vd.idvente = %s
                ORDER BY a.designation
            """
            print(f"🔍 Exécution requête détails pour idvente={idvente}")
            cursor.execute(sql_details, (idvente,))
            details_rows = cursor.fetchall()
    
            print(f"📦 Nombre de détails trouvés: {len(details_rows)}")
    
            # ✅ Calcul avec remise (remise = nouveau prix unitaire si > 0)
            data['details'] = []
            premier_magasin = None  # Pour stocker le premier magasin trouvé
            
            for row in details_rows:
                code_article = row[0]
                designation = row[1]
                unite = row[2]
                qte = float(row[3])
                prixunit = float(row[4])
                remise = float(row[5])
                magasin = row[6]
                
                # Capturer le premier magasin pour l'ajouter à la description
                if premier_magasin is None:
                    premier_magasin = magasin
                # Interpréter la remise comme remise unitaire (Ar) appliquée à la quantité
                montant_ht = qte * prixunit
                montant_remise = remise * qte
                montant_ttc = montant_ht - montant_remise
                if montant_ttc < 0:
                    montant_ttc = 0
            
                data['details'].append({
                    'code_article': code_article,
                    'designation': designation,
                    'unite': unite,
                    'qte': qte,
                    'prixunit': prixunit,
                    'remise': remise,
                    'magasin': magasin,
                    'montant_ht': montant_ht,
                    'montant_remise': montant_remise,
                    'montant_ttc': montant_ttc
                })
            
            # Ajouter le magasin à la description de la vente
            if premier_magasin:
                description_avec_depot = f"Magasin {premier_magasin}"
                # Ajouter la description seulement si elle existe, n'est pas vide, 
                # et ne contient pas déjà le nom du dépôt
                if description and description.strip() and premier_magasin not in description:
                    # Nettoyer la description des tirets vides
                    description_clean = description.strip().strip('-').strip()
                    if description_clean:
                        description_avec_depot = f"{description_avec_depot} - {description_clean}"
                data['vente']['description'] = description_avec_depot
            # Ajouter le magasin séparément pour l'impression
            data['magasin'] = premier_magasin or ''
    
            print(f"✅ Données complètes récupérées avec succès")
            print(f"{'='*60}\n")

            return data

        except Exception as e:
            print(f"❌ ERREUR CRITIQUE dans get_data_facture: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Erreur", f"Erreur lors de la récupération des données de facture : {e}")
            return None
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if conn:
                conn.close()

    # ==============================================================================
    # MÉTHODES D'IMPRESSION PDF A5
    # ==============================================================================

    def generate_pdf_a5(self, data: Dict[str, Any], filename: str):
        """
        Génère le PDF de la facture au format A5 avec le modèle canvas amélioré.
        Utilise les données existantes du dictionnaire data.
        """
        from reportlab.lib.pagesizes import A5
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.platypus import Table, TableStyle, Paragraph

        # ✅ CRÉATION DU PDF AVEC CANVAS
        c = canvas.Canvas(filename, pagesize=A5)
        width, height = A5

        # ✅ 1. CADRE DU VERSET (Haut de page avec bordure)
        verset = "Ankino amin'ny Jehovah ny asanao dia ho lavorary izay kasainao. Ohabolana 16:3"
        c.setLineWidth(1)
        c.rect(10*mm, height - 13*mm, width - 20*mm, 8*mm)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(width/2, height - 10.5*mm, verset)

        # ✅ 2. EN-TÊTE DEUX COLONNES
        styles = getSampleStyleSheet()
        style_p = ParagraphStyle('style_p', fontSize=9, leading=11, parent=styles['Normal'])

        societe = data['societe']
        utilisateur = data['utilisateur']
        client = data['client']
        vente = data['vente']
        magasin = data.get('magasin', '')

        # Adapter les clés de données si nécessaire
        nomsociete = societe.get('nomsociete', 'N/A')
        adressesociete = societe.get('adressesociete') or societe.get('adresse', 'N/A')
        villesociete = societe.get('villesociete') or ''
        contactsociete = societe.get('contactsociete') or societe.get('tel', 'N/A')
        nifsociete = societe.get('nifsociete') or societe.get('nif', 'N/A')
        statsociete = societe.get('statsociete') or societe.get('stat', 'N/A')

        # Insérer la ville juste en dessous de l'adresse si disponible
        villes_line = f"{villesociete}<br/>" if villesociete else ""

        gauche_text = f"<b><font size='11'>{nomsociete}</font></b><br/>{adressesociete}<br/>{villes_line}TEL: {contactsociete}<br/>NIF: {nifsociete} <br/>STAT: {statsociete}"

        # Gérer si utilisateur est un dict ou une string et éviter d'afficher 'None'
        if isinstance(utilisateur, dict):
            pren = utilisateur.get('prenomuser') or ''
            nomu = utilisateur.get('nomuser') or ''
            user_name = f"{pren} {nomu}".strip()
        else:
            user_name = str(utilisateur) if utilisateur is not None else ''

        # Affichage: titre magasin en gras à la place du label client, puis
        # le nom du client en italique juste en dessous (vide si absent)
        magasin_display = magasin or ''
        client_display = client.get('nomcli') or ''
        droite_text = (
            f"<b>Facture N°: {vente['refvente']}</b><br/>"
            f"{vente['dateregistre']}<br/>"
            f"<b>MAGASIN {magasin_display}</b><br/><br/>"
            f"<i>Client: {client_display}</i><br/>"
            f"<font size='7'>Op: {user_name}</font>"
        )

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
        header_table.drawOn(c, 10*mm, height - 42*mm)

        # ✅ 3. TABLEAU DES ARTICLES
        table_top = height - 45*mm
        table_bottom = 55*mm
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
                self.formater_nombre_pdf(detail.get('prixunit', 0)),
                self.formater_nombre_pdf(montant)
            ])

        # Ajouter des lignes vides
        montant_fmg = int(total_montant * 5)
        empty_rows_needed = max_rows - 1 - num_articles - 2
        for i in range(max(0, empty_rows_needed)):
            table_data.append(['', '', '', '', ''])

        # Totaux
        table_data.append(['', '', 'TOTAL Ar:', self.formater_nombre_pdf(total_montant), ''])
        table_data.append(['', '', 'Fmg:', self.formater_nombre_pdf(montant_fmg), ''])

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
            ('BACKGROUND', (0, -2), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -3), 8),
            ('FONTSIZE', (0, -2), (-1, -1), 9),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('LINEABOVE', (0, -2), (-1, -2), 1, colors.black),
            ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 0), (2, 0), 'LEFT'),
            ('ALIGN', (2, -2), (2, -1), 'RIGHT'),
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

        # ✅ 4. TEXTE EN LETTRES
        montant_lettres = nombre_en_lettres_fr(int(total_montant)).upper()
        text_y = table_bottom - 18*mm
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(width/2, text_y, f"ARRETE A LA SOMME DE {montant_lettres} ARIARY TTC")

        # ✅ 5. MENTION LÉGALE
        c.setFont("Helvetica-Oblique", 8)
        c.drawCentredString(width/2, text_y - 5*mm, "Nous déclinons la responsabilité des marchandises non livrées au-delà de 5 jours")

        # ✅ 6. SIGNATURES
        sig_y = 15*mm
        c.setFont("Helvetica-Bold", 10)
        c.drawString(15*mm, sig_y, "Le Client")
        c.drawCentredString(width/2, sig_y, "Le Caissier")
        c.drawString(width - 35*mm, sig_y, "Le Magasinier")

        # ✅ SAUVEGARDER
        try:
            c.save()
            print(f"✅ PDF généré avec succès : {filename}")
        except Exception as e:
            print(f"❌ Erreur PDF : {e}")
            import traceback
            traceback.print_exc()
        
    # ==============================================================================
    # MÉTHODES D'IMPRESSION TICKET 80MM (Texte Brut)
    # ==============================================================================

    def generate_ticket_80mm(self, data: Dict[str, Any], filename: str):
        """Génère un PDF pour un ticket de caisse 80mm (format étroit)."""
        from reportlab.lib.units import mm
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        
        # Dimensions du ticket 80mm de large, hauteur variable
        ticket_width = 80 * mm
        ticket_height = 297 * mm  # A4 hauteur, sera ajusté automatiquement
        
        # Marges
        margin_left = 3 * mm
        margin_right = 3 * mm
        margin_top = 5 * mm
        
        doc = SimpleDocTemplate(
            filename,
            pagesize=(ticket_width, ticket_height),
            leftMargin=margin_left,
            rightMargin=margin_right,
            topMargin=margin_top,
            bottomMargin=5 * mm
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Données
        societe = data['societe']
        vente = data['vente']
        client = data['client']
        details = data['details']
        
        # Style centré
        style_center = styles['Normal'].clone('CenterStyle')
        style_center.alignment = TA_CENTER
        style_center.fontSize = 10
        style_center.leading = 12
        
        # Style centré gras
        style_center_bold = styles['Normal'].clone('CenterBoldStyle')
        style_center_bold.alignment = TA_CENTER
        style_center_bold.fontSize = 11
        style_center_bold.fontName = 'Helvetica-Bold'
        style_center_bold.leading = 13
        
        # Style normal
        style_normal = styles['Normal'].clone('NormalStyle')
        style_normal.fontSize = 9
        style_normal.leading = 11
        
        # Style petit
        style_small = styles['Normal'].clone('SmallStyle')
        style_small.fontSize = 8
        style_small.leading = 10
        
        # --- EN-TÊTE SOCIÉTÉ ---
        elements.append(Paragraph(f"<b>{societe.get('nomsociete', 'NOM SOCIÉTÉ')}</b>", style_center_bold))
        elements.append(Paragraph(societe.get('adressesociete', 'N/A'), style_center))
        # Ajouter la ville de la société si disponible
        elements.append(Paragraph(societe.get('villesociete', ''), style_center))
        elements.append(Paragraph(f"Tél: {societe.get('contactsociete', 'N/A')}", style_center))
        elements.append(Spacer(1, 3 * mm))
        
        # Ligne de séparation
        line_width = ticket_width - margin_left - margin_right
        elements.append(Table([["=" * 48]], colWidths=[line_width]))
        elements.append(Spacer(1, 2 * mm))
        
        # --- INFOS FACTURE ---
        elements.append(Paragraph(f"<b>FACTURE N° {vente['refvente']}</b>", style_center_bold))
        elements.append(Paragraph(f"Date: {vente['dateregistre']}", style_normal))
        elements.append(Paragraph(f"Client: {client['nomcli']}", style_normal))
        if vente.get('description'):
            elements.append(Paragraph(f"Désign: {vente['description']}", style_small))
        elements.append(Spacer(1, 2 * mm))
        elements.append(Table([["=" * 48]], colWidths=[line_width]))
        elements.append(Spacer(1, 2 * mm))
        
        # --- DÉTAILS DES ARTICLES ---
        total_ht = 0.0
        total_remise = 0.0
        total_ttc = 0.0
        
        for detail in details:
            # Désignation
            designation = detail.get('designation', 'Article')
            elements.append(Paragraph(f"<b>{designation}</b>", style_normal))
            
            # Ligne avec Quantité x Prix unitaire = Montant
            qte_str = str(int(detail.get('qte', 0)))
            unite = detail.get('unite', '')
            prixunit_str = self.formater_nombre_pdf(detail.get('prixunit', 0))
            montant_ligne = detail.get('montant_ttc', 0)
            montant_str = self.formater_nombre_pdf(montant_ligne)
            
            # Créer une table pour aligner le montant à droite
            ligne_detail = Table(
                [[f"{qte_str} {unite} x {prixunit_str}", f"= {montant_str}"]],
                colWidths=[50 * mm, 20 * mm]
            )
            ligne_detail.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            elements.append(ligne_detail)
            elements.append(Spacer(1, 2 * mm))
            
            # Accumulation des totaux
            total_ht += detail.get('montant_ht', 0)
            total_remise += detail.get('montant_remise', 0)
            total_ttc += detail.get('montant_ttc', 0)
        
        # --- TOTAUX ---
        elements.append(Table([["=" * 48]], colWidths=[line_width]))
        elements.append(Spacer(1, 2 * mm))
        
        # Tableau des totaux
        totals_data = [
            ['TOTAL HT:', self.formater_nombre_pdf(total_ht)]
        ]
        
        if total_remise > 0:
            totals_data.append(['TOTAL REMISE:', f"-{self.formater_nombre_pdf(total_remise)}"])
        
        totals_table = Table(totals_data, colWidths=[35 * mm, 35 * mm])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        elements.append(totals_table)
        
        elements.append(Spacer(1, 2 * mm))
        elements.append(Table([["=" * 48]], colWidths=[line_width]))
        elements.append(Spacer(1, 2 * mm))
        
        # --- MONTANT À PAYER ---
        elements.append(Paragraph("<b>*** MONTANT À PAYER ***</b>", style_center_bold))
        
        style_montant = styles['Normal'].clone('MontantStyle')
        style_montant.alignment = TA_CENTER
        style_montant.fontSize = 14
        style_montant.fontName = 'Helvetica-Bold'
        style_montant.leading = 16
        
        elements.append(Paragraph(f"<b>{self.formater_nombre_pdf(total_ttc)} Ar</b>", style_montant))
        elements.append(Spacer(1, 2 * mm))
        
        # --- MONTANT EN FMG ---
        montant_fmg = total_ttc * 5
        style_fmg = styles['Normal'].clone('FMGStyle')
        style_fmg.alignment = TA_CENTER
        style_fmg.fontSize = 11
        style_fmg.fontName = 'Helvetica-Bold'
        style_fmg.leading = 13
        
        elements.append(Paragraph(f"<b>Montant en FMG: {self.formater_nombre_pdf(montant_fmg)} FMG</b>", style_fmg))
        elements.append(Spacer(1, 2 * mm))
        elements.append(Table([["=" * 48]], colWidths=[line_width]))
        elements.append(Spacer(1, 3 * mm))
        
        # --- TOTAL EN LETTRES ---
        total_lettres = nombre_en_lettres_fr(total_ttc)
        elements.append(Paragraph("<b>TOTAL EN LETTRES</b>", style_center_bold))
        elements.append(Paragraph(total_lettres, style_small))
        elements.append(Spacer(1, 2 * mm))
        elements.append(Table([["=" * 48]], colWidths=[line_width]))
        elements.append(Spacer(1, 5 * mm))
        
        # --- PIED DE PAGE ---
        elements.append(Paragraph("Merci de votre achat !", style_center))
        elements.append(Paragraph(datetime.now().strftime("%d/%m/%Y %H:%M:%S"), style_center))
        elements.append(Spacer(1, 10 * mm))
        
        # Génération du PDF
        try:
            doc.build(elements)
            print(f"✅ Ticket PDF généré avec succès : {filename}")
        except Exception as e:
            print(f"❌ Erreur lors de la génération du ticket PDF : {e}")
            messagebox.showerror("Erreur", f"Erreur lors de la génération du ticket : {e}")

    # ==============================================================================
    # GESTION DES PROFORMAS (NOUVEAU)
    # ==============================================================================

    def open_recherche_proforma(self):
        """Ouvre une fenêtre de dialogue pour rechercher et sélectionner un proforma 'A Facturer'."""
        if self.mode_modification:
            messagebox.showwarning("Attention", "Veuillez d'abord terminer la modification de la facture actuelle.")
            return

        fenetre = ctk.CTkToplevel(self)
        fenetre.title("Charger un Proforma à Facturer")
        fenetre.geometry("900x500")
        fenetre.grab_set()

        main_frame = ctk.CTkFrame(fenetre)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Zone de recherche
        search_frame = ctk.CTkFrame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(search_frame, text="🔍 Rechercher N° Proforma ou Client:").pack(side="left", padx=5)
        entry_search = ctk.CTkEntry(search_frame, placeholder_text="Référence ou Nom client...", width=300)
        entry_search.pack(side="left", padx=5, fill="x", expand=True)
        
        # Treeview
        tree_frame = ctk.CTkFrame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        colonnes = ("ID", "Ref Proforma", "Date", "Client", "Montant Total", "Nb Lignes")
        tree = ttk.Treeview(tree_frame, columns=colonnes, show='headings', height=15)
        
        style = ttk.Style()
        style.configure("Treeview", rowheight=22, font=('Segoe UI', 8)) 
        style.configure("Treeview.Heading", font=('Segoe UI', 8, 'bold'))

        tree.heading("ID", text="ID")
        tree.heading("Ref Proforma", text="N° Proforma")
        tree.heading("Date", text="Date")
        tree.heading("Client", text="Client")
        tree.heading("Montant Total", text="Montant Total")
        tree.heading("Nb Lignes", text="Qté Lignes")
        
        tree.column("ID", width=0, stretch=False)
        tree.column("Ref Proforma", width=120, anchor='w')
        tree.column("Date", width=100, anchor='center')
        tree.column("Client", width=250, anchor='w')
        tree.column("Montant Total", width=120, anchor='e')
        tree.column("Nb Lignes", width=80, anchor='center')

        scrollbar = ctk.CTkScrollbar(tree_frame, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        def charger_proforma(filtre=""):
            conn = self.connect_db()
            if not conn: return
            try:
                cursor = conn.cursor()
                
                # Récupère tous les proformas avec statut 'A Facturer'
                sql = """
                    SELECT p.idprof, p.refprof, p.dateprof, c.nomcli, 
                           SUM(pd.qtlivprof * pd.prixunit) as total_montant, 
                           COUNT(pd.idprof) as nb_lignes
                    FROM tb_proforma p 
                    INNER JOIN tb_client c ON p.idclient = c.idclient 
                    LEFT JOIN tb_proformadetail pd ON p.idprof = pd.idprof 
                    WHERE p.deleted = 0 
                    AND p.statut = '✅ A Facturer'
                    AND (p.refprof ILIKE %s OR c.nomcli ILIKE %s)
                    GROUP BY p.idprof, p.refprof, p.dateprof, c.nomcli 
                    ORDER BY p.dateprof DESC
                """
                filtre_like = f"%{filtre}%"
                cursor.execute(sql, (filtre_like, filtre_like))
                proformas = cursor.fetchall()

                # Clear existing items
                for item in tree.get_children():
                    tree.delete(item)
                    
                for prof in proformas:
                    idprof, refprof, dateregistre, nomcli, total_montant, nb_lignes = prof
                    
                    date_str = dateregistre.strftime("%d/%m/%Y")
                    montant_str = self.formater_nombre(total_montant)

                    tree.insert('', 'end', values=(
                        idprof, 
                        refprof, 
                        date_str, 
                        nomcli, 
                        montant_str, 
                        nb_lignes
                    ))

            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors du chargement des proformas: {str(e)}")
            finally:
                if 'cursor' in locals() and cursor: cursor.close()
                if conn: conn.close()

        def rechercher(*args):
            charger_proforma(entry_search.get())

        entry_search.bind('<KeyRelease>', rechercher)
        
        def valider_selection():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Attention", "Veuillez sélectionner un proforma")
                return

            values = tree.item(selection[0])['values']
            idprof = values[0]
            fenetre.destroy()
            self.charger_proforma_pour_vente(idprof)

        tree.bind('<Double-Button-1>', lambda e: valider_selection())

        # Boutons
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x")
        btn_annuler = ctk.CTkButton(btn_frame, text="❌ Annuler", command=fenetre.destroy, fg_color="#d32f2f", hover_color="#b71c1c")
        btn_annuler.pack(side="left", padx=5, pady=5)
        btn_valider = ctk.CTkButton(btn_frame, text="✅ Charger", command=valider_selection, fg_color="#2e7d32", hover_color="#1b5e20")
        btn_valider.pack(side="right", padx=5, pady=5)
        
        charger_proforma()

    def charger_proforma_pour_vente(self, idprof: int):
        """
        Charge les détails d'un proforma pour la création d'une vente.
        Les détails sont stockés temporairement, en attente de la sélection du magasin.
        """
        # Réinitialisation complète, y compris la référence de vente
        self.nouveau_facture() 
        self.reset_proforma_state() 
        
        conn = self.connect_db()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            
            # 1. Récupérer l'entête du Proforma
            sql_prof = """
                SELECT 
                    p.refprof, p.observation, c.nomcli, c.idclient
                FROM 
                    tb_proforma p
                INNER JOIN 
                    tb_client c ON p.idclient = c.idclient
                WHERE 
                    p.idprof = %s AND p.deleted = 0
            """
            cursor.execute(sql_prof, (idprof,))
            proforma = cursor.fetchone()
            
            if not proforma:
                messagebox.showerror("Erreur", "Proforma introuvable.")
                return

            refprof, description_prof, nomcli, idclient = proforma
            
            # 2. Récupérer les détails du Proforma
            sql_details = """
                SELECT 
                    pd.idarticle, ua.codearticle, a.designation as nom_article,
                    pd.idunite, ua.designationunite as nom_unite, pd.qtlivprof as qtvente, pd.prixunit
                FROM 
                    tb_proformadetail pd
                INNER JOIN 
                    tb_article a ON pd.idarticle = a.idarticle
                INNER JOIN 
                    tb_unite ua ON pd.idunite = ua.idunite
                WHERE 
                    pd.idprof = %s
            """
            cursor.execute(sql_details, (idprof,))
            proforma_details = cursor.fetchall()

            # 3. Stocker les détails temporairement
            self.details_proforma_a_ajouter = []
            cols = ['idarticle', 'code_article', 'nom_article', 'idunite', 'nom_unite', 'qtvente', 'prixunit']
            
            for row in proforma_details:
                detail = dict(zip(cols, row))
                detail['idmag'] = None # Sera défini par l'utilisateur
                detail['designationmag'] = None # Sera défini par l'utilisateur
                self.details_proforma_a_ajouter.append(detail)


            # 4. Mettre à jour les champs d'en-tête (Client, Désignation)
            self.entry_client.delete(0, "end")
            self.entry_client.insert(0, nomcli)
            
            self.entry_designation.delete(0, "end")
            self.entry_designation.insert(0, f"Suivant Proforma n° {refprof}")

            self.client_map[nomcli] = idclient
            self.details_proforma_a_ajouter_idprof = idprof # Conserver l'ID du Proforma

            # 5. Mettre à jour l'interface
            self.detail_vente = [] # S'assurer que le tableau de vente est vide
            self.charger_details_treeview() # Recharge le treeview vide
            self.desactiver_entree_manuelle()
            self.afficher_bouton_ajouter_proforma()
            
            messagebox.showinfo("Proforma Chargé", 
                                f"Proforma N° {refprof} chargé.\n\nÉTAPE SUIVANTE: Veuillez sélectionner le 'Magasin de' (Dépôt) puis cliquez sur le bouton 'Ajouter Lignes Proforma' pour vérifier le stock et ajouter les lignes de vente.")

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement du proforma: {str(e)}")
            self.reset_proforma_state()
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()

    def ajouter_details_proforma_en_masse(self):
        """
        Ajoute tous les détails du proforma dans le tableau de vente,
        en vérifiant le stock pour le magasin sélectionné.
        """
        if not self.details_proforma_a_ajouter:
            messagebox.showwarning("Attention", "Aucun détail de proforma à ajouter.")
            return

        magasin_selectionne_nom = self.combo_magasin.get()
        idmag = self.magasin_map.get(magasin_selectionne_nom)
    
        if not idmag or magasin_selectionne_nom not in self.magasin_map:
            messagebox.showerror("Erreur", "Veuillez sélectionner un Magasin de sortie valide.")
            return
        
        details_ajoutes = 0
        details_non_ajoutes = []
        details_unite_bloquee = []  # ✅ NOUVEAU : Liste des unités bloquées
    
        nouveaux_details_vente = []
    
        for detail_prof in self.details_proforma_a_ajouter:
        
            idarticle = detail_prof['idarticle']
            idunite = detail_prof['idunite']
            qtvente_demandee = detail_prof['qtvente']
            nom_article = detail_prof['nom_article']
            nom_unite = detail_prof['nom_unite']
            code_article = detail_prof['code_article']

            # ✅ NOUVEAU : Vérification unité Dépôt B
            autorise, message_erreur = self.verifier_unite_depot_b(idarticle, idunite)
        
            if not autorise:
                details_unite_bloquee.append(f"{code_article} ({nom_article}): {message_erreur}")
                continue

            # 1. Vérification du Stock
            stock_disponible = self.calculer_stock_article(idarticle, idunite, idmag)
        
            if stock_disponible < qtvente_demandee:
                details_non_ajoutes.append(f"{code_article} ({nom_article}): Qté demandée {self.formater_nombre(qtvente_demandee)} {nom_unite}, Stock {self.formater_nombre(stock_disponible)} {nom_unite}.")
                continue
        
            # 2. Ajout à la liste des nouveaux détails
            nouveau_detail = {
                'idarticle': idarticle,
                'nom_article': nom_article,
                'idunite': idunite,
                'nom_unite': nom_unite,
                'code_article': code_article,
                'qtvente': qtvente_demandee, 
                'prixunit': detail_prof['prixunit'], 
                'designationmag': magasin_selectionne_nom,
                'idmag': idmag 
            }
            nouveaux_details_vente.append(nouveau_detail)
            details_ajoutes += 1

        if nouveaux_details_vente:
            self.detail_vente.extend(nouveaux_details_vente)
            self.charger_details_treeview()
        
            # Mettre à jour le statut du proforma
            if self.details_proforma_a_ajouter_idprof:
                self.marquer_proforma_comme_facture(self.details_proforma_a_ajouter_idprof)

        # Nettoyage et message final
        self.reset_proforma_state() 
    
        # ✅ NOUVEAU : Messages d'erreur combinés
        messages_erreur = []
    
        if details_unite_bloquee:
            msg_unite = "\n".join(details_unite_bloquee)
            messages_erreur.append(f"⚠️ UNITÉS BLOQUÉES (Dépôt B):\n{msg_unite}")
    
        if details_non_ajoutes:
            msg_stock = "\n".join(details_non_ajoutes)
            messages_erreur.append(f"📦 STOCK INSUFFISANT:\n{msg_stock}")
    
        if messages_erreur:
            message_final = f"{details_ajoutes} ligne(s) ajoutée(s).\n\n" + "\n\n".join(messages_erreur)
            messagebox.showwarning("Attention", message_final)
        else:
            messagebox.showinfo("Ajout Réussi", 
                            f"Toutes les {details_ajoutes} lignes du proforma ont été ajoutées avec succès à la facture.")


    def marquer_proforma_comme_facture(self, idprof: int):
        """Met à jour le statut du proforma dans la base de données après facturation."""
        conn = self.connect_db()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            sql = """
                UPDATE tb_proforma 
                SET statut = %s, datefacturation = %s 
                WHERE idprof = %s
            """
            cursor.execute(sql, ('Facturé', datetime.now().date(), idprof))
            conn.commit()
            print(f"Proforma ID {idprof} marqué comme 'Facturé'.")
        except Exception as e:
            conn.rollback()
            print(f"Erreur lors de la mise à jour du statut du proforma: {str(e)}")
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()

    def desactiver_entree_manuelle(self):
        """Désactive les champs d'entrée manuelle de détail de vente."""
        self.entry_article.configure(state="readonly") 
        self.entry_qtvente.configure(state="readonly") 
        self.entry_unite.configure(state="readonly") 
        self.entry_prixunit.configure(state="readonly") 
        self.btn_recherche_article.configure(state="disabled")
        self.btn_ajouter.grid_forget()

    def activer_entree_manuelle(self):
        """Réactive les champs d'entrée manuelle de détail de vente."""
        self.entry_article.configure(state="readonly")
        self.entry_qtvente.configure(state="normal")
        self.entry_unite.configure(state="readonly")
        self.entry_prixunit.configure(state="readonly")
        self.btn_recherche_article.configure(state="normal")
        # Réaffiche le bouton d'ajout manuel
        self.btn_ajouter.grid(row=1, column=7, padx=2, pady=2, sticky="w")
    
    def afficher_bouton_ajouter_proforma(self):
        """Affiche le bouton pour ajouter les détails du proforma en masse et le bouton d'annulation Proforma."""
        # Masque les boutons de détail standard
        self.btn_ajouter.grid_forget()
        self.btn_annuler_mod.grid_forget()
        
        # Affiche le bouton d'ajout en masse
        self.btn_ajouter_proforma_bulk.grid(row=1, column=5, padx=5, pady=5, sticky="w")
        
        # Ajout d'un bouton pour annuler le chargement du proforma temporaire
        self.btn_annuler_proforma = ctk.CTkButton(self.btn_ajouter_proforma_bulk.master, 
                                                  text="✖️ Annuler Proforma", 
                                                  command=self.reset_proforma_state, 
                                                  fg_color="#d32f2f", hover_color="#b71c1c")
        self.btn_annuler_proforma.grid(row=1, column=6, padx=5, pady=5, sticky="w")
        
        # Désactiver les autres boutons principaux en cas de chargement Proforma
        self.btn_enregistrer.configure(state="disabled")
        self.btn_charger_proforma.configure(state="disabled")
        self.btn_search_client.configure(state="disabled")
        self.entry_client.configure(state="readonly")


    def masquer_bouton_ajouter_proforma(self):
        """Masque le bouton d'ajout en masse du proforma et restaure les boutons standards."""
        self.btn_ajouter_proforma_bulk.grid_forget()
        if hasattr(self, 'btn_annuler_proforma'):
             self.btn_annuler_proforma.grid_forget()
             del self.btn_annuler_proforma # Nettoyage
        # Bouton Annuler Modif volontairement caché

    def reset_proforma_state(self):
        """Réinitialise l'état après le chargement d'un proforma (sans le valider ou après validation)."""
        self.details_proforma_a_ajouter = None
        self.details_proforma_a_ajouter_idprof = None
        
        self.masquer_bouton_ajouter_proforma()
        self.activer_entree_manuelle()
        
        # Réactiver les contrôles principaux (seulement si nous ne sommes pas en mode modification de vente)
        if not self.mode_modification:
            self.btn_enregistrer.configure(state="normal")
            self.btn_charger_proforma.configure(state="normal")
            self.btn_search_client.configure(state="normal")
            self.entry_client.configure(state="normal")
        
        # Nettoyage des champs si la liste de détails est vide (sinon les détails de la vente sont conservés)
        if not self.detail_vente and not self.mode_modification:
            self.entry_client.delete(0, "end")
            self.entry_client.insert(0, "") 
            self.entry_designation.delete(0, "end")
            self.entry_designation.insert(0, "") 
            self.generer_reference() # Régénère une référence de facture si nouvelle vente
        
        self.reset_detail_form() # Assure le reset des champs de détail

    def verifier_code_autorisation(self, code_saisi):
        """Vérifie le code en gérant l'absence de connexion initiale"""
    
        # Si db_connection n'existe pas, on tente de la créer localement
        if not hasattr(self, 'db_connection') or self.db_connection is None:
            try:
                with open(get_config_path('config.json')) as f:
                    config = json.load(f)
                    db_config = config['database']
                self.db_connection = psycopg2.connect(**db_config)
            except Exception as e:
                print(f"Erreur de connexion base de données : {e}")
                return False

        try:
            code_propre = str(code_saisi).strip()
            cursor = self.db_connection.cursor()
            # Utilisation de TRIM pour ignorer les espaces en base de données
            query = "SELECT 1 FROM tb_codeautorisation WHERE TRIM(code) = %s"
            cursor.execute(query, (code_propre,))
            result = cursor.fetchone()
            cursor.close()
            return result is not None
        except Exception as e:
            print(f"Erreur lors de la requête : {e}")
            return False

    def tentative_ouverture_avoir(self):
        """Lance le dialogue de vérification"""
        dialog = PasswordDialog("Autorisation Requise", "Entrez le code pour créer un avoir :")
        if dialog.result:
            if self.verifier_code_autorisation(dialog.result):
                self.ouvrir_la_page_avoir_réellement() # Votre ancienne fonction d'ouverture
            else:
                messagebox.showerror("Accès Refusé", "Code d'autorisation incorrect.")

    def ouvrir_la_page_avoir_réellement(self):
        """Ouvre la fenêtre PageAvoir dans un Toplevel."""
        # Si la fenêtre existe déjà, la mettre au premier plan
        if hasattr(self, 'fenetre_avoir') and self.fenetre_avoir.winfo_exists():
            self.fenetre_avoir.focus()
            return

        self.fenetre_avoir = ctk.CTkToplevel(self)
        self.fenetre_avoir.title("Création / Modification d'Avoir")
        self.fenetre_avoir.geometry("1200x600")
        
        # S'assurer que la fenêtre est modale (optionnel, mais recommandé)
        self.fenetre_avoir.grab_set()

        # Initialise PageAvoir dans la nouvelle fenêtre
        # NOTE : On passe 'self.id_user_connecte' pour que la PageAvoir sache qui est l'utilisateur
        page_avoir = PageAvoir(self.fenetre_avoir, id_user_connecte=self.id_user_connecte)
        page_avoir.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Ajout de la gestion de la fermeture de la fenêtre
        self.fenetre_avoir.protocol("WM_DELETE_WINDOW", self._fermer_fenetre_avoir)

    def _fermer_fenetre_avoir(self):
        """Détruit la fenêtre Avoir et supprime la référence."""
        self.fenetre_avoir.grab_release() # Libère le grab avant de détruire
        self.fenetre_avoir.destroy()
        # On supprime la référence pour que le prochain appel crée une nouvelle fenêtre
        if hasattr(self, 'fenetre_avoir'):
            del self.fenetre_avoir
        
        
            
    def _ouvrir_page_proforma(self):
        """Ouvre la fenêtre PageCommandeCli (Proforma) dans un Toplevel."""
        # Si la fenêtre existe déjà, la mettre au premier plan
        if hasattr(self, 'fenetre_proforma') and self.fenetre_proforma.winfo_exists():
            self.fenetre_proforma.focus()
            return

        self.fenetre_proforma = ctk.CTkToplevel(self)
        self.fenetre_proforma.title("Création / Modification de Proforma")
        self.fenetre_proforma.geometry("1200x600")
        
        # S'assurer que la fenêtre est modale
        self.fenetre_proforma.grab_set()

        # CORRECTION ICI : Changer 'id_user_connecte=' par 'iduser='
        page_proforma = PageCommandeCli(self.fenetre_proforma, iduser=self.id_user_connecte)
        
        page_proforma.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Ajout de la gestion de la fermeture de la fenêtre
        self.fenetre_proforma.protocol("WM_DELETE_WINDOW", self._fermer_fenetre_proforma)

    def _fermer_fenetre_proforma(self):
        """Détruit la fenêtre Proforma et supprime la référence."""
        self.fenetre_proforma.grab_release() # Libère le grab avant de détruire
        self.fenetre_proforma.destroy()
        # On supprime la référence pour que le prochain appel crée une nouvelle fenêtre
        if hasattr(self, 'fenetre_proforma'):
            del self.fenetre_proforma
            
    def ouvrir_suivi_depot(self):
        """Ouvre la fenêtre de suivi de stock par dépôt avec gestion d'import flexible."""
        try:
            # Tentative d'importation flexible
            try:
                from pages.page_SuiviStockDepot import PageSuiviStockDepot
            except ImportError:
                from page_SuiviStockDepot import PageSuiviStockDepot
        
            # Vérifier si la fenêtre est déjà ouverte
            if hasattr(self, 'fenetre_suivi') and self.fenetre_suivi.winfo_exists():
                self.fenetre_suivi.lift()
                self.fenetre_suivi.focus_force()
                return

            # Création de la fenêtre (CTkToplevel avec un 'k' minuscule)
            self.fenetre_suivi = ctk.CTkToplevel(self) 
            self.fenetre_suivi.title("Suivi Stock par Dépôt")
            self.fenetre_suivi.geometry("1100x650")
        
            # S'assurer qu'elle passe devant
            self.fenetre_suivi.after(200, lambda: self.fenetre_suivi.focus_force())
        
            # Charger le contenu
            self.page_depot = PageSuiviStockDepot(self.fenetre_suivi, iduser=self.id_user_connecte)
            self.page_depot.pack(fill="both", expand=True, padx=10, pady=10)
        
        except Exception as e:
            messagebox.showerror("Erreur d'ouverture", f"Impossible d'ouvrir la page : {e}")

    def verifier_alerte_stock_silencieuse(self):
        """Vérifie si un article est en alerte dépôt pour faire clignoter la cloche."""
        conn = self.connect_db()
        if conn:
            try:
                cursor = conn.cursor()
                # On cherche s'il existe au moins un article dont le stock <= alertdepot
                query = "SELECT COUNT(*) FROM tb_article WHERE deleted = 0 AND alertdepot >= 0" 
                # Note: Idéalement, utilisez votre fonction calculer_stock_article ici
                cursor.execute(query)
                count = cursor.fetchone()[0]
            
                # Si alerte trouvée
                if count > 0:
                    self.notif_stock_depot.configure(text_color="red")
                    winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS) # Son clochette Windows
                else:
                    self.notif_stock_depot.configure(text_color="gray")
                
            except: pass
            finally: conn.close()
    
        # Vérifier toutes les 5 minutes
        self.after(300000, self.verifier_alerte_stock_silencieuse)        

# --- Partie pour exécuter la fenêtre de test ---
if __name__ == "__main__":
    
    # Simulation de l'utilisateur connecté
    USER_ID = 1 
    
    try:
        app = ctk.CTk()
        app.title("Gestion de Vente")
        app.geometry("1200x600") 
        
        page_vente = PageVenteParMsin(app, id_user_connecte=USER_ID)
        page_vente.pack(fill="both", expand=True, padx=10, pady=10)
        
        app.mainloop()
        
    except Exception as e:
        print(f"Erreur critique lors de l'exécution: {e}")
        traceback.print_exc()
