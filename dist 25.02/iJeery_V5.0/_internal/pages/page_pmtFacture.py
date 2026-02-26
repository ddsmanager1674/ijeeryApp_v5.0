import customtkinter as ctk
from tkinter import messagebox, simpledialog
import psycopg2
import json
from datetime import datetime
import traceback
import tempfile
import os
import subprocess
from tkcalendar import DateEntry # Nécessite pip install tkcalendar
from resource_utils import get_config_path, safe_file_read


# --- BIBLIOTHÈQUES POUR LE PDF ---
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import mm
from reportlab.lib.units import mm
try:
    from num2words import num2words
except ImportError:
    num2words = None

class PagePmtFacture(ctk.CTkToplevel):
    def __init__(self, master, paiement_data, iduser=None):
        super().__init__(master)
        self.data = paiement_data
        self.id_facture = self.data.get('id_facture')
        self.refvente = self.data.get('refvente', 'N/A')
        self.montant_total_str = self.data.get('montant_total', '0,00')
        self.client = self.data.get('client', 'Client Inconnu')
        self.iduser = iduser if iduser is not None else 1

        try:
            montant_nettoyé = str(self.montant_total_str).replace(' ', '').replace(',', '.')
            self.montant_total_float = float(montant_nettoyé)
        except ValueError:
            self.montant_total_float = 0.0

        self.title(f"Paiement Facture N° {self.refvente}")
        self.geometry("600x550")
        self.grab_set()
        self.focus_set()
        # Flag pour éviter double-clics rapides
        self._processing_payment = False
        # Flag pour garantir un seul popup succès et une seule finalisation.
        self._payment_finalized = False
        self._success_popup_shown = False

        self._construire_interface()

    def _construire_interface(self):
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(main_frame, text="GESTION DU PAIEMENT", font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold")).pack(pady=(0, 20))
        
        info_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        info_frame.pack(fill="x", pady=10, padx=10)
        ctk.CTkLabel(info_frame, text=f"Facture N°: {self.refvente}", font=ctk.CTkFont(family="Segoe UI", weight="bold")).pack(anchor="w")
        ctk.CTkLabel(info_frame, text=f"Client: {self.client}").pack(anchor="w")
        ctk.CTkLabel(info_frame, text=f"Montant Total: {self.montant_total_str} Ar", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")).pack(anchor="w", pady=10)

        saisie_frame = ctk.CTkFrame(main_frame)
        saisie_frame.pack(fill="x", pady=10, padx=10)
        ctk.CTkLabel(saisie_frame, text="Montant Reçu :").grid(row=0, column=0, padx=10, pady=10)
        self.entry_montant = ctk.CTkEntry(saisie_frame, width=200)
        self.entry_montant.grid(row=0, column=1, padx=10, pady=10)
        self.entry_montant.insert(0, self.montant_total_str)
        
        # Ligne 2 : Mode de paiement
        ctk.CTkLabel(saisie_frame, text="Mode de paiement :").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        modes = self.charger_modes_paiement()
        self.option_mode_pmt = ctk.CTkOptionMenu(
            saisie_frame, 
            values=modes, 
            width=150,
            command=self._verifier_mode_credit # Appelé à chaque changement
        )
        self.option_mode_pmt.grid(row=1, column=1, padx=10, pady=10, sticky="w")

        # Ligne 2 (Droite) : Échéance
        ctk.CTkLabel(saisie_frame, text="Échéance :").grid(row=1, column=2, padx=10, pady=10, sticky="w")
        
        # Utilisation de DateEntry (TK) encapsulé pour le style
        self.cal_echeance = DateEntry(
            saisie_frame, 
            width=15, 
            background='darkblue', 
            foreground='white', 
            borderwidth=2, 
            locale='fr_FR',
            date_pattern='dd/mm/yyyy'
        )
        self.cal_echeance.grid(row=1, column=3, padx=10, pady=10, sticky="w")
        
        # Désactiver par défaut au démarrage
        self._verifier_mode_credit(self.option_mode_pmt.get())

        btns_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btns_frame.pack(fill="x", pady=20)
        # Bouton validateur stocké pour pouvoir le désactiver rapidement
        self.btn_valider = ctk.CTkButton(btns_frame, text="Valider & Imprimer PDF", fg_color="#2e7d32", command=self._on_valider_click)
        self.btn_valider.pack(side="left", padx=10, expand=True)
        ctk.CTkButton(btns_frame, text="Annuler", fg_color="#d32f2f", command=self.destroy).pack(side="left", padx=10, expand=True)

    def connect_db(self):
        try:
            with open(get_config_path('config.json')) as f:
                config = json.load(f)
            return psycopg2.connect(**config['database'])
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur de connexion : {e}")
            return None

    def charger_settings(self):
        """Charge les paramètres depuis settings.json"""
        try:
            with open('settings.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Impossible de charger settings.json : {e}")
            return {}

    def charger_modes_paiement(self):
        conn = self.connect_db()
        if not conn: return ["Espèces"]
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT idmode, modedepaiement FROM tb_modepaiement")
            rows = cursor.fetchall()
            self.liste_modes = {row[1]: row[0] for row in rows}
            return list(self.liste_modes.keys())
        except: return ["Espèces"]
        finally: conn.close()

    def calculer_stock_article_reel(self, idarticle, idunite_cible, idmag):
        """
        ✅ CALCUL CONSOLIDÉ DU STOCK RÉEL :
        Relie tous les mouvements de toutes les unités (PIECE, CARTON, etc.)
        d'un même idarticle via le coefficient 'qtunite' de tb_unite.
        
        Prend en compte :
        - Réceptions (tb_livraisonfrs) → +stock
        - Ventes (tb_ventedetail) → -stock
        - Sorties (tb_sortiedetail) → -stock
        - Transferts IN et OUT (tb_transfertdetail) → +/- stock
        - Inventaires (tb_inventaire) → +stock
        - Avoirs (tb_avoir/tb_avoirdetail.qtavoir) → +stock (annulation de vente)
        """
        conn = self.connect_db()
        if not conn: return 0.0
        
        try:
            cursor = conn.cursor()
            
            print(f"\n{'='*80}")
            print(f"🔬 DEBUG CALCUL STOCK ARTICLE #{idarticle} - MAGASIN {idmag}")
            print(f"{'='*80}")
            
            # 1. Récupérer TOUTES les unités liées à cet idarticle
            cursor.execute("""
                SELECT idunite, codearticle, COALESCE(qtunite, 1) 
                FROM tb_unite 
                WHERE idarticle = %s
            """, (idarticle,))
            unites_liees = cursor.fetchall()
            
            print(f"\n📌 Unités trouvées pour idarticle={idarticle}:")
            for idu, code, qt_u in unites_liees:
                print(f"   - idunite={idu}, codearticle='{code}', qtunite={qt_u}")
            
            # 2. Identifier le qtunite de l'unité qu'on veut afficher
            qtunite_affichage = 1
            codearticle_affichage = ""
            for idu, code, qt_u in unites_liees:
                if idu == idunite_cible:
                    qtunite_affichage = qt_u if qt_u > 0 else 1
                    codearticle_affichage = code
                    break
            
            print(f"\n🎯 Unité d'affichage:")
            print(f"   idunite_cible={idunite_cible}, qtunite_affichage={qtunite_affichage}, code='{codearticle_affichage}'")

            total_stock_global_base = 0

            # 3. Sommer les mouvements de chaque variante
            for det_idx, (idu_boucle, code_boucle, qtunite_boucle) in enumerate(unites_liees, 1):
                print(f"\n{'─'*80}")
                print(f"📦 Unité #{det_idx}: idunite={idu_boucle}, code='{code_boucle}', qtunite={qtunite_boucle}")
                print(f"{'─'*80}")
                
                # Réceptions
                cursor.execute(
                    "SELECT COALESCE(SUM(qtlivrefrs), 0) FROM tb_livraisonfrs WHERE idarticle = %s AND idunite = %s AND deleted = 0 AND idmag = %s",
                    (idarticle, idu_boucle, idmag)
                )
                receptions = cursor.fetchone()[0] or 0
                print(f"  📥 Réceptions (tb_livraisonfrs): {receptions}")
        
                # Ventes (UNIQUEMENT VALIDÉES - cohérent avec page_stock.py)
                cursor.execute(
                    """SELECT COALESCE(SUM(vd.qtvente), 0) 
                       FROM tb_ventedetail vd 
                       INNER JOIN tb_vente v ON vd.idvente = v.id 
                       WHERE vd.idarticle = %s AND vd.idunite = %s AND vd.deleted = 0 
                       AND v.deleted = 0 AND v.statut = 'VALIDEE' AND v.idmag = %s""",
                    (idarticle, idu_boucle, idmag)
                )
                ventes = cursor.fetchone()[0] or 0
                print(f"  📤 Ventes (tb_ventedetail - VALIDÉE uniquement): {ventes}")
        
                # Sorties
                cursor.execute(
                    "SELECT COALESCE(SUM(qtsortie), 0) FROM tb_sortiedetail WHERE idarticle = %s AND idunite = %s AND idmag = %s",
                    (idarticle, idu_boucle, idmag)
                )
                sorties = cursor.fetchone()[0] or 0
                print(f"  📤 Sorties (tb_sortiedetail): {sorties}")
        
                # Transferts IN
                cursor.execute(
                    "SELECT COALESCE(SUM(qttransfert), 0) FROM tb_transfertdetail WHERE idarticle = %s AND idunite = %s AND deleted = 0 AND idmagentree = %s",
                    (idarticle, idu_boucle, idmag)
                )
                t_in = cursor.fetchone()[0] or 0
                print(f"  ➡️ Transferts IN (idmagentree): {t_in}")
                
                # Transferts OUT
                cursor.execute(
                    "SELECT COALESCE(SUM(qttransfert), 0) FROM tb_transfertdetail WHERE idarticle = %s AND idunite = %s AND deleted = 0 AND idmagsortie = %s",
                    (idarticle, idu_boucle, idmag)
                )
                t_out = cursor.fetchone()[0] or 0
                print(f"  ⬅️ Transferts OUT (idmagsortie): {t_out}")
        
                # Inventaires
                cursor.execute(
                    "SELECT COALESCE(SUM(qtinventaire), 0) FROM tb_inventaire WHERE codearticle = %s AND idmag = %s",
                    (code_boucle, idmag)
                )
                inv = cursor.fetchone()[0] or 0
                print(f"  📋 Inventaires (tb_inventaire): {inv}")

                # Avoirs (annulation de vente = +stock)
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(ad.qtavoir), 0) 
                    FROM tb_avoirdetail ad
                    INNER JOIN tb_avoir a ON ad.idavoir = a.id
                    WHERE ad.idarticle = %s AND ad.idunite = %s 
                    AND a.deleted = 0 AND ad.deleted = 0 AND ad.idmag = %s
                    """,
                    (idarticle, idu_boucle, idmag)
                )
                avoirs = cursor.fetchone()[0] or 0
                print(f"  🔄 Avoirs/Retours (tb_avoirdetail): {avoirs}")

                # Calcul du solde pour cette unité
                solde_unite = (receptions + t_in + inv + avoirs) - (ventes + sorties + t_out)
                print(f"\n  🧮 Formule: ({receptions} + {t_in} + {inv} + {avoirs}) - ({ventes} + {sorties} + {t_out})")
                print(f"  = ({receptions + t_in + inv + avoirs}) - ({ventes + sorties + t_out})")
                print(f"  = {solde_unite}")
                
                contribution = solde_unite * qtunite_boucle
                print(f"  × Poids (qtunite={qtunite_boucle}) = {contribution}")
                
                total_stock_global_base += contribution

            # 4. Conversion finale pour l'affichage
            print(f"\n{'='*80}")
            print(f"🔢 RÉSUMÉ CALCUL FINAL")
            print(f"{'='*80}")
            print(f"  Total stock global (base): {total_stock_global_base}")
            print(f"  qtunite_affichage: {qtunite_affichage}")
            print(f"  Calcul: {total_stock_global_base} / {qtunite_affichage}")
            
            stock_final = total_stock_global_base / qtunite_affichage
            stock_affiche = max(0.0, stock_final)
            
            print(f"\n✅ STOCK FINAL AFFICHÉ: {stock_affiche}")
            print(f"{'='*80}\n")
            
            return stock_affiche
        
        except Exception as e:
            print(f"❌ Erreur calcul stock consolidé : {e}")
            import traceback
            traceback.print_exc()
            return 0.0
        finally:
            cursor.close()
            conn.close()
        
    def _verifier_mode_credit(self, choix):
        """Active ou désactive le calendrier selon le mode choisi"""
        if choix.lower() == "crédit":
            self.cal_echeance.configure(state="normal")
        else:
            self.cal_echeance.configure(state="disabled")

    def verifier_code_autorisation(self, code_saisi: str) -> bool:
        """
        Vérifie si le code d'autorisation saisi est valide.
        Retourne True si valide, False sinon.
        """
        conn = self.connect_db()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            # Vérifier si le code existe et n'est pas supprimé
            # Note: deleted = 0 signifie non supprimé (au lieu de deleted = FALSE)
            query = """
                SELECT COUNT(*) 
                FROM tb_codeautorisation 
                WHERE code = %s AND deleted = 0
            """
            cursor.execute(query, (code_saisi,))
            result = cursor.fetchone()
            
            return result[0] > 0 if result else False
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la vérification du code : {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    def demander_autorisation(self) -> bool:
        """
        Affiche une boîte de dialogue pour demander le code d'autorisation.
        Retourne True si le code est valide, False sinon.
        """
        # Créer une fenêtre personnalisée pour la saisie du code
        dialog = ctk.CTkToplevel(self)
        dialog.title("Autorisation Requise")
        dialog.geometry("400x200")
        dialog.transient(self)
        dialog.grab_set()
        
        # Variable pour stocker le résultat
        autorisation_valide = [False]  # Liste pour pouvoir modifier dans la fonction interne
        
        # Frame principal
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Message
        ctk.CTkLabel(
            main_frame, 
            text="⚠️ AUTORISATION REQUISE ⚠️", 
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#d32f2f"
        ).pack(pady=(0, 10))
        
        ctk.CTkLabel(
            main_frame, 
            text="Le paiement à crédit nécessite un code d'autorisation.",
            wraplength=350
        ).pack(pady=(0, 20))
        
        # Champ de saisie du code
        ctk.CTkLabel(main_frame, text="Code d'autorisation :").pack(anchor="w", padx=20)
        entry_code = ctk.CTkEntry(main_frame, width=300, show="*")
        entry_code.pack(pady=5, padx=20)
        entry_code.focus_set()
        
        def valider_code():
            code_saisi = entry_code.get().strip()
            
            if not code_saisi:
                messagebox.showwarning("Attention", "Veuillez saisir un code d'autorisation.", parent=dialog)
                return
            
            # Vérifier le code dans la base de données
            if self.verifier_code_autorisation(code_saisi):
                autorisation_valide[0] = True
                dialog.destroy()
            else:
                messagebox.showerror(
                    "Code Invalide", 
                    "Le code d'autorisation est incorrect ou inactif.\nVeuillez réessayer.",
                    parent=dialog
                )
                entry_code.delete(0, "end")
                entry_code.focus_set()
        
        def annuler():
            autorisation_valide[0] = False
            dialog.destroy()
        
        # Boutons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        ctk.CTkButton(
            btn_frame, 
            text="Valider", 
            fg_color="#2e7d32",
            hover_color="#1b5e20",
            command=valider_code,
            width=120
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            btn_frame, 
            text="Annuler", 
            fg_color="#d32f2f",
            hover_color="#b71c1c",
            command=annuler,
            width=120
        ).pack(side="left", padx=10)
        
        # Bind Enter key pour valider
        entry_code.bind('<Return>', lambda e: valider_code())
        
        # Attendre que la fenêtre soit fermée
        dialog.wait_window()
        
        return autorisation_valide[0]

    def _on_valider_click(self):
        """Wrapper pour empêcher les double-clicks rapides sur le bouton Valider."""
        # Si déjà en cours, ignorer
        if getattr(self, '_processing_payment', False) or getattr(self, '_payment_finalized', False):
            return

        # Désactiver le bouton et marquer comme en cours
        try:
            self._processing_payment = True
            try:
                self.btn_valider.configure(state="disabled")
            except Exception:
                pass

            # Appeler la logique principale
            self.valider_paiement()

        finally:
            # Si la fenêtre existe toujours (la validation a pu échouer), réactiver
            try:
                if self.winfo_exists() and not self._payment_finalized:
                    self._processing_payment = False
                    try:
                        self.btn_valider.configure(state="normal")
                    except Exception:
                        pass
            except Exception:
                # Si winfo_exists lève une exception, ignorer
                pass

    def valider_paiement(self):
        if self._payment_finalized:
            return

        montant_saisi_str = self.entry_montant.get().replace(' ', '').replace(',', '.')
        nom_mode_pmt = self.option_mode_pmt.get()
        
        # ✅ VÉRIFICATION DU MODE CRÉDIT - DEMANDE D'AUTORISATION
        if nom_mode_pmt.lower() == "crédit":
            # Demander le code d'autorisation
            if not self.demander_autorisation():
                messagebox.showwarning(
                    "Paiement Annulé", 
                    "Le paiement à crédit a été annulé car l'autorisation n'a pas été validée."
                )
                return  # Arrêter le processus de validation
        
        # Récupération de la date d'échéance si mode Crédit
        date_echeance = None
        if nom_mode_pmt.lower() == "crédit":
            date_echeance = self.cal_echeance.get_date() # Objet datetime.date

        conn = self.connect_db()
        if not conn: return
        
        try:
            montant_saisi = float(montant_saisi_str)
        except: 
            messagebox.showerror("Erreur", "Montant invalide")
            return

        conn = self.connect_db()
        if not conn: return

        try:
            cursor = conn.cursor()

            # ============================================================
            # ÉTAPE 1 : RÉCUPÉRER LA FACTURE DE VENTE
            # ============================================================
            print(f"\n{'='*70}")
            print(f"🔍 ÉTAPE 1 : RÉCUPÉRATION FACTURE DE VENTE")
            print(f"{'='*70}")
            print(f"📌 Facture: {self.refvente}")
            print(f"💰 Client: {self.client}")
            print(f"💵 Montant à encaisser: {montant_saisi} Ar")
            print(f"🏪 Mode de paiement: {nom_mode_pmt}")

            # 1. Infos Société
            cursor.execute("SELECT nomsociete, adressesociete, contactsociete, villesociete FROM tb_infosociete LIMIT 1")
            info_soc = cursor.fetchone()
            
            # 2. Récupérer l'idclient depuis tb_vente
            cursor.execute("SELECT idclient, idmag FROM tb_vente WHERE refvente = %s", (self.refvente,))
            res_vente = cursor.fetchone()
            idclient = res_vente[0] if res_vente else None
            idmag_facture = res_vente[1] if res_vente else None
            print(f"✓ ID Client: {idclient}")
            print(f"✓ Magasin: {idmag_facture}")
            
            # 3. Infos Client
            cursor.execute("SELECT nomcli FROM tb_client WHERE nomcli = %s", (self.client,))
            res_client = cursor.fetchone()
            client = res_client[0] if res_client else "Inconnu"
            
            # 4. Nom de l'utilisateur
            cursor.execute("SELECT username FROM tb_users WHERE iduser = %s", (self.iduser,))
            res_user = cursor.fetchone()
            username = res_user[0] if res_user else "Inconnu"

            # ============================================================
            # ÉTAPE 2 : RÉCUPÉRER LES DÉTAILS DE VENTE (ARTICLES)
            # ============================================================
            print(f"\n{'='*70}")
            print(f"📦 ÉTAPE 2 : RÉCUPÉRATION DES ARTICLES VENDUS")
            print(f"{'='*70}")

            # 5. Requête avec JOINS et CALCUL du montant (qtvente * prixunit)
            # On récupère aussi idarticle, idunite et idmag pour mise à jour stock
            query_articles = """
                SELECT 
                    vd.idarticle,
                    vd.idunite,
                    v.idmag,
                    COALESCE(u.codearticle, '') as codearticle,
                    a.designation, 
                    u.designationunite, 
                    vd.qtvente, 
                    vd.prixunit, 
                    (vd.qtvente * vd.prixunit) as montant_calcule
                FROM tb_ventedetail vd
                JOIN tb_vente v ON v.id = vd.idvente
                JOIN tb_article a ON a.idarticle = vd.idarticle
                LEFT JOIN tb_unite u ON u.idunite = vd.idunite
                WHERE v.refvente = %s
            """
            cursor.execute(query_articles, (self.refvente,))
            articles = cursor.fetchall()
            
            print(f"✓ Nombre d'articles trouvés: {len(articles)}")
            for idx, art in enumerate(articles, 1):
                idarticle, idunite, idmag, codearticle, designation, unite, qtvente, prixunit, montant = art
                print(f"\n  Article #{idx}:")
                print(f"    - ID Article: {idarticle}")
                print(f"    - Code Article: '{codearticle}'")
                print(f"    - Désignation: {designation}")
                print(f"    - Unité: {unite}")
                print(f"    - Quantité vendue: {qtvente}")
                print(f"    - Prix unitaire: {prixunit}")
                print(f"    - Magasin: {idmag}")

            # 6. Enregistrement du paiement avec dateecheance ET idclient
            cursor.execute("SELECT COALESCE(MAX(id),0)+1 FROM tb_pmtfacture")
            next_id = cursor.fetchone()[0]
            refpmt = f"{datetime.now().year}-PMTC-{next_id:06d}"
            
            # Récupération de l'ID du mode de paiement sélectionné
            id_mode_selectionne = self.liste_modes.get(nom_mode_pmt, 1)

            query_pmt = """
                INSERT INTO tb_pmtfacture (
                    refvente, mtpaye, datepmt, idmode, iduser, observation, refpmt, dateecheance, idclient
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params_pmt = (
                self.refvente, 
                montant_saisi, 
                datetime.now(), 
                id_mode_selectionne, 
                self.iduser, 
                f"PMT {self.refvente} - {self.client}", 
                refpmt,
                date_echeance,
                idclient
            )
            cursor.execute(query_pmt, params_pmt)

            # ============================================================
            # ÉTAPE 3 : MISE À JOUR FACTURE ET GESTION DU STOCK
            # ============================================================
            print(f"\n{'='*70}")
            print(f"💳 ÉTAPE 3 : ENREGISTREMENT PAIEMENT ET MISE À JOUR STOCK")
            print(f"{'='*70}")
            print(f"Paiement référencé: {refpmt}")

            # --- MISE A JOUR ATOMIQUE : payment + statut + stock + log ---
            try:
                # 1) Mettre à jour tb_pmtfacture (déjà inséré), puis tb_vente.statut = 'VALIDEE'
                query_update_vente = """
                    UPDATE tb_vente 
                    SET idmode = %s, statut = 'VALIDEE'
                    WHERE refvente = %s
                """
                cursor.execute(query_update_vente, (id_mode_selectionne, self.refvente))
                print(f"✓ Facture marquée comme VALIDÉE")

                # ============================================================
                # ÉTAPE 4 : MISE À JOUR STOCK POUR CHAQUE ARTICLE
                # ============================================================
                print(f"\n{'='*70}")
                print(f"📦 ÉTAPE 4 : MISE À JOUR DU STOCK")
                print(f"{'='*70}")

                # 2) Mettre à jour le stock et journaliser
                for det_idx, det in enumerate(articles, 1):
                    idarticle = det[0]
                    idunite = det[1]
                    idmag = det[2]
                    codearticle = det[3] or ''
                    designation = det[4]
                    qtvente = float(det[6] or 0)

                    print(f"\n  🔄 Article #{det_idx}: {designation}")
                    print(f"     ID: {idarticle}, Code: '{codearticle}', Magasin: {idmag}, Qté vendue: {qtvente}")

                    # 🎯 UTILISER LE CALCUL CONSOLIDÉ DU STOCK RÉEL
                    stock_reel = self.calculer_stock_article_reel(idarticle, idunite, idmag)
                    ancien_stock = stock_reel
                    print(f"     ✓ Stock RÉEL (consolidé): {ancien_stock}")
                    
                    nouveau_stock = ancien_stock - qtvente
                    print(f"     📊 Calcul: {ancien_stock} - {qtvente} = {nouveau_stock}")

                    # ⚠️ TODO: Vérification disponibilité (empêche validation si stock insuffisant) - À DÉVELOPPER
                    # if ancien_stock < qtvente:
                    #     print(f"     ❌ ERREUR: Stock insuffisant!")
                    #     conn.rollback()
                    #     messagebox.showerror("Stock insuffisant", f"Stock insuffisant pour l'article {codearticle or idarticle} (mag {idmag}). Ancien: {ancien_stock}, demandé: {qtvente}")
                    #     return

                    # Mise à jour du stock dans tb_stock (synchronisation du cache)
                    if codearticle:
                        cursor.execute("UPDATE tb_stock SET qtstock = %s WHERE codearticle = %s AND idmag = %s", (nouveau_stock, codearticle, idmag))
                        cursor.execute("SELECT COUNT(*) FROM tb_stock WHERE codearticle = %s AND idmag = %s", (codearticle, idmag))
                        if cursor.fetchone()[0] == 0:
                            cursor.execute("INSERT INTO tb_stock (codearticle, idmag, qtstock, qtalert, deleted) VALUES (%s, %s, %s, 0, 0)", (codearticle, idmag, nouveau_stock))
                        print(f"     ✓ SYNC tb_stock avec codearticle='{codearticle}': qtstock={nouveau_stock}")
                    else:
                        cursor.execute("UPDATE tb_stock SET qtstock = %s WHERE idarticle = %s AND idmag = %s", (nouveau_stock, idarticle, idmag))
                        cursor.execute("SELECT COUNT(*) FROM tb_stock WHERE idarticle = %s AND idmag = %s", (idarticle, idmag))
                        if cursor.fetchone()[0] == 0:
                            cursor.execute("INSERT INTO tb_stock (idarticle, idmag, qtstock, qtalert, deleted) VALUES (%s, %s, %s, 0, 0)", (idarticle, idmag, nouveau_stock))
                        print(f"     ✓ SYNC tb_stock avec idarticle={idarticle}: qtstock={nouveau_stock}")

                    # Insérer le log de stock
                    try:
                        cursor.execute("SELECT setval(pg_get_serial_sequence('tb_log_stock', 'id'), COALESCE((SELECT MAX(id) FROM tb_log_stock), 0) + 1, false);")
                    except Exception:
                        pass

                    cursor.execute(
                        """
                        INSERT INTO tb_log_stock (codearticle, idmag, ancien_stock, nouveau_stock, iduser, type_action, date_action) 
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        """,
                        (codearticle if codearticle else None, idmag, ancien_stock, nouveau_stock, self.iduser, f"VENTE {self.refvente}")
                    )
                    print(f"     📋 Log enregistré: ancien={ancien_stock}, nouveau={nouveau_stock}")

                # Commit global (paiement + update vente + stock + log)
                conn.commit()
                print(f"\n{'='*70}")
                print(f"✅ VALIDATION RÉUSSIE - Tous les changements sont validés")
                print(f"{'='*70}\n")

            except Exception as e:
                conn.rollback()
                print(f"\n❌ ERREUR lors de la mise à jour du stock: {e}\n")
                messagebox.showerror("Erreur Stock", f"Erreur lors de la mise à jour du stock : {e}")
                return

            # 7. Préparer et générer le PDF (articles normalisés)
            articles_pdf = []
            for det in articles:
                try:
                    code = det[3]
                    designation = det[4]
                    unite = det[5]
                    qte = det[6]
                    prix_unit = det[7]
                    montant = det[8]
                    articles_pdf.append((code, designation, unite, qte, prix_unit, montant))
                except Exception:
                    continue

            # Charger le paramètre d'impression depuis settings.json
            settings = self.charger_settings()
            imprimer_ticket = settings.get('ClientAPayer_ImpressionTicket', 1)
            
            print(f"📋 ClientAPayer_ImpressionTicket = {imprimer_ticket}")
            
            self._generer_ticket_pdf(info_soc, username, articles_pdf, montant_saisi, nom_mode_pmt, refpmt, date_echeance, imprimer_ticket)
            
            # Message de confirmation
            msg_impression = " (impression lancée)" if imprimer_ticket == 1 else " (sans impression)"
            self._payment_finalized = True
            self._show_success_once(f"Paiement enregistré avec succès!{msg_impression}\nRéférence: {refpmt}")
            try:
                self.destroy()
            except Exception:
                pass

        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur SQL", f"Détails : {e}")
            traceback.print_exc()
        finally:
            conn.close()

    def _show_success_once(self, message: str):
        """Affiche une seule fois le popup succès pour éviter les doublons."""
        if self._success_popup_shown:
            return
        self._success_popup_shown = True
        messagebox.showinfo("Succès", message)

    def _couper_texte(self, texte, largeur_max_chars):
        """Coupe le texte en lignes pour respecter la largeur maximale"""
        if not texte:
            return [""]
        
        texte = str(texte)
        mots = texte.split()
        lignes = []
        ligne_courante = ""
        
        for mot in mots:
            test_ligne = f"{ligne_courante} {mot}".strip()
            if len(test_ligne) <= largeur_max_chars:
                ligne_courante = test_ligne
            else:
                if ligne_courante:
                    lignes.append(ligne_courante)
                    ligne_courante = mot
                else:
                    # Si un seul mot dépasse, on le coupe quand même
                    lignes.append(mot[:largeur_max_chars])
                    ligne_courante = ""
        
        if ligne_courante:
            lignes.append(ligne_courante)
        
        return lignes if lignes else [""]

    def _generer_ticket_pdf(self, info_soc, username, articles, montant_paye, mode_paiement, refpmt, date_echeance=None, imprimer_ticket=1):
        """Génère un ticket de paiement PDF au format 80mm"""
        try:
            # Création fichier temporaire
            temp_dir = tempfile.gettempdir()
            filename = os.path.join(temp_dir, f"Paiement_{self.refvente}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
            
            # Dimensions ticket (80mm de large)
            largeur = 80 * mm
            hauteur = 297 * mm  # Hauteur variable
            
            c = canvas.Canvas(filename, pagesize=(largeur, hauteur))
            
            # Position Y de départ
            y = hauteur - 10*mm
            
            # --- EN-TÊTE SOCIÉTÉ (centré) ---
            c.setFont("Helvetica-Bold", 10)
            nom_societe = info_soc[0] if info_soc else "NOM SOCIÉTÉ"
            c.drawCentredString(largeur/2, y, nom_societe)
            y -= 4*mm
            
            c.setFont("Helvetica", 8)
            adresse = info_soc[1] if info_soc and len(info_soc) > 1 else ""
            if adresse:
                c.drawCentredString(largeur/2, y, adresse)
                y -= 3.5*mm
            
            contact = info_soc[2] if info_soc and len(info_soc) > 2 else ""
            if contact:
                c.drawCentredString(largeur/2, y, f"Tél: {contact}")
                y -= 3.5*mm
            
            ville = info_soc[3] if info_soc and len(info_soc) > 3 else ""
            if ville:
                c.drawCentredString(largeur/2, y, ville)
                y -= 5*mm
            
            # Ligne de séparation
            c.line(5*mm, y, largeur - 5*mm, y)
            y -= 5*mm
            
            # --- TITRE ---
            c.setFont("Helvetica-Bold", 11)
            c.drawCentredString(largeur/2, y, "REÇU DE PAIEMENT")
            y -= 5*mm
            
            # --- INFORMATIONS PAIEMENT ---
            c.setFont("Helvetica", 8)
            c.drawString(5*mm, y, f"Réf. Paiement: {refpmt}")
            y -= 4*mm
            c.drawString(5*mm, y, f"Facture N°: {self.refvente}")
            y -= 4*mm
            c.drawString(5*mm, y, f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            y -= 4*mm
            c.drawString(5*mm, y, f"Client: {self.client}")
            y -= 4*mm
            c.drawString(5*mm, y, f"Utilisateur: {username}")
            y -= 5*mm
            
            # Ligne de séparation
            c.line(5*mm, y, largeur - 5*mm, y)
            y -= 5*mm
            
            # --- DÉTAILS ARTICLES (avec gestion du texte long) ---
            c.setFont("Helvetica-Bold", 8)
            c.drawString(5*mm, y, "DÉTAILS")
            y -= 4*mm
            
            c.setFont("Helvetica", 7)
            total_calcule = 0
            
            for article in articles:
                code, designation, unite, qte, prix_unit, montant = article
                total_calcule += float(montant)
                
                # Couper la désignation si trop longue (max 30 caractères par ligne)
                lignes_designation = self._couper_texte(designation, 30)
                
                # Première ligne : désignation
                for i, ligne in enumerate(lignes_designation):
                    c.drawString(5*mm, y, ligne)
                    y -= 3.5*mm
                
                # Détails quantité et prix
                detail_qte = f"{qte} {unite or 'unité'} × {prix_unit:.2f} Ar"
                c.drawString(7*mm, y, detail_qte)
                y -= 3.5*mm
                
                # Montant (aligné à droite)
                montant_str = f"{montant:,.2f} Ar".replace(',', ' ')
                c.drawRightString(largeur - 5*mm, y, montant_str)
                y -= 5*mm
                
                # Vérifier si on a assez de place, sinon nouvelle page
                if y < 50*mm:
                    c.showPage()
                    y = hauteur - 10*mm
                    c.setFont("Helvetica", 7)
            
            # Ligne de séparation
            c.line(5*mm, y, largeur - 5*mm, y)
            y -= 5*mm
            
            # --- MONTANT TOTAL ---
            c.setFont("Helvetica-Bold", 10)
            c.drawString(5*mm, y, "MONTANT TOTAL:")
            montant_total_str = f"{total_calcule:,.2f} Ar".replace(',', ' ')
            c.drawRightString(largeur - 5*mm, y, montant_total_str)
            y -= 6*mm
            
            # --- MONTANT PAYÉ ---
            c.setFont("Helvetica-Bold", 10)
            c.drawString(5*mm, y, "MONTANT PAYÉ:")
            montant_paye_str = f"{montant_paye:,.2f} Ar".replace(',', ' ')
            c.drawRightString(largeur - 5*mm, y, montant_paye_str)
            y -= 6*mm
            
            # --- MODE DE PAIEMENT ---
            c.setFont("Helvetica", 9)
            c.drawString(5*mm, y, f"Mode de paiement: {mode_paiement}")
            y -= 5*mm
            
            # --- DATE D'ÉCHÉANCE (si mode crédit) ---
            if mode_paiement.lower() == "crédit" and date_echeance:
                c.setFont("Helvetica-Bold", 9)
                c.drawString(5*mm, y, f"Échéance: {date_echeance.strftime('%d/%m/%Y')}")
                y -= 6*mm
            
            # Ligne de séparation
            c.line(5*mm, y, largeur - 5*mm, y)
            y -= 5*mm
            
            # --- MONTANT EN LETTRES (optionnel si num2words disponible) ---
            if num2words:
                try:
                    montant_lettres = num2words(montant_paye, lang='fr') + " Ariary"
                    c.setFont("Helvetica-Oblique", 7)
                    c.drawString(5*mm, y, "Arrêté le présent reçu à la somme de:")
                    y -= 3.5*mm
                    
                    # Couper le montant en lettres si trop long
                    lignes_montant = self._couper_texte(montant_lettres, 35)
                    for ligne in lignes_montant:
                        c.drawString(5*mm, y, ligne)
                        y -= 3.5*mm
                    
                    y -= 2*mm
                except:
                    pass
            
            # --- PIED DE PAGE ---
            y -= 5*mm
            c.setFont("Helvetica", 7)
            c.drawCentredString(largeur/2, y, "Merci de votre confiance !")
            y -= 4*mm
            c.drawCentredString(largeur/2, y, f"Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
            
            # Sauvegarder et ouvrir
            c.save()
            
            # Ouvrir le PDF seulement si l'impression est activée
            if imprimer_ticket == 1:
                try:
                    if os.name == 'nt':  # Windows
                        os.startfile(filename)
                    elif os.name == 'posix':  # Linux/Mac
                        subprocess.call(['xdg-open', filename])
                    print(f"✅ Ticket de caisse ouvert : {filename}")
                except Exception as e:
                    print(f"⚠️ Erreur lors de l'ouverture du PDF : {e}")
            else:
                print(f"📄 Ticket de caisse généré (impression désactivée) : {filename}")
            
        except Exception as e:
            messagebox.showerror("Erreur PDF", f"Erreur lors de la génération du PDF : {e}")
            traceback.print_exc()
