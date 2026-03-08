import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import json
from datetime import datetime, timedelta
import threading
from tkinter import ttk
from resource_utils import get_config_path, safe_file_read

# ── Thème iJeery ──────────────────────────────────────────────────────────────
try:
    from app_theme import Colors, Fonts, styled, Theme
    _T = True
except ImportError:
    _T = False


class _C:
    MIDNIGHT       = "#2C3E50"
    BG_PAGE        = "#ECF0F1"
    BG_CARD        = "#FFFFFF"
    BG_HEADER      = "#2C3E50"
    BG_INPUT       = "#F4F6F8"
    PRIMARY        = "#3498DB"
    PRIMARY_HOVER  = "#2980B9"
    SUCCESS        = "#2ECC71"
    SUCCESS_DARK   = "#27AE60"
    DANGER         = "#E74C3C"
    DANGER_DARK    = "#C0392B"
    WARNING        = "#F39C12"
    WARNING_LIGHT  = "#FEF9E7"
    WARNING_TEXT   = "#9A6A00"
    INFO           = "#1ABC9C"
    INFO_DARK      = "#16A085"
    TEXT_PRIMARY   = "#2C3E50"
    TEXT_SECONDARY = "#5D6D7E"
    TEXT_MUTED     = "#95A5A6"
    BORDER         = "#D5D8DC"
    DIVIDER        = "#E8EAED"


C = Colors if _T else _C


# ── Style Treeview ────────────────────────────────────────────────────────────
def _apply_tree_style():
    s = ttk.Style()
    try:
        s.theme_use("clam")
    except Exception:
        pass
    s.configure("Stock.Treeview",
                 background=C.BG_CARD, foreground=C.TEXT_PRIMARY,
                 fieldbackground=C.BG_CARD, rowheight=24,
                 font=("Roboto" if _T else "Segoe UI", 10),
                 borderwidth=0)
    s.configure("Stock.Treeview.Heading",
                 background=C.BG_HEADER, foreground="#FFFFFF",
                 font=("Roboto" if _T else "Segoe UI", 10, "bold"),
                 relief="flat", padding=(6, 4))
    s.map("Stock.Treeview",
          background=[("selected", C.PRIMARY)],
          foreground=[("selected", "#FFFFFF")])


# ── Importations des classes externes ─────────────────────────────────────────
from pages.page_peremption import PageGestionPeremption
from pages.page_inventaire import PageInventaire


# ====================================================================
# PageStock
# ====================================================================

class PageStock(ctk.CTkFrame):

    def __init__(self, master, db_conn=None, session_data=None, iduser=None):
        super().__init__(master, fg_color=C.BG_PAGE)
        self.clignotement_actif = False
        self.couleur_alerte     = C.DANGER

        if iduser is not None:
            self.iduser = iduser
        elif session_data and 'user_id' in session_data:
            self.iduser = session_data['user_id']
        else:
            self.iduser = 1

        self.magasins            = []
        self.colonnes_dynamiques = []
        self.all_data            = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        _apply_tree_style()
        self.setup_ui()
        self.charger_magasins()
        self.charger_stocks()

    # ── helper font ──────────────────────────────────────────────────────────
    def _f(self, size=11, weight="normal"):
        return ctk.CTkFont(
            family="Roboto" if _T else "Segoe UI",
            size=size, weight=weight)

    # ====================================================================
    # setup_ui — REFONTE DESIGN UNIQUEMENT
    # ====================================================================

    def setup_ui(self):
        # ── En-tête ───────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=C.BG_HEADER, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            hdr, text="Gestion des Stocks",
            font=self._f(18, "bold"), text_color="#FFFFFF"
        ).pack(side="left", padx=16, pady=10)

        # ── Barre filtres + actions ────────────────────────────────────────
        panel = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=8)
        panel.grid(row=1, column=0, sticky="ew", padx=12, pady=6)

        inner = ctk.CTkFrame(panel, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=8)

        # Recherche
        ctk.CTkLabel(
            inner, text="🔍", font=self._f(13), text_color=C.TEXT_MUTED
        ).pack(side="left", padx=(0, 4))

        self.entry_recherche = ctk.CTkEntry(
            inner,
            placeholder_text="Code, désignation…",
            width=280, height=30,
            fg_color=C.BG_INPUT, border_color=C.BORDER,
            text_color=C.TEXT_PRIMARY, font=self._f(10))
        self.entry_recherche.pack(side="left", padx=(0, 6))
        self.entry_recherche.bind('<KeyRelease>', lambda e: self.filtrer_stocks())

        ctk.CTkButton(
            inner, text="Réinitialiser",
            command=self.reinitialiser_filtre,
            fg_color="transparent", hover_color=C.DIVIDER,
            text_color=C.TEXT_SECONDARY,
            border_width=1, border_color=C.BORDER,
            height=30, width=110, font=self._f(10)
        ).pack(side="left", padx=(0, 4))

        # Boutons actions (côté droit)
        self.btn_peremption = ctk.CTkButton(
            inner, text="🛡️  Articles Périmés",
            command=self.ouvrir_fenetre_peremption,
            fg_color=C.DANGER, hover_color=C.DANGER_DARK,
            text_color="#FFFFFF",
            height=30, width=160, font=self._f(10, "bold"))
        self.btn_peremption.pack(side="right", padx=(6, 0))

        self.btn_export = ctk.CTkButton(
            inner, text="📊  Export Excel",
            command=self.exporter_stocks,
            fg_color=C.INFO_DARK, hover_color=C.INFO,
            text_color="#FFFFFF",
            height=30, width=140, font=self._f(10, "bold"))
        self.btn_export.pack(side="right", padx=(0, 6))

        # ── Zone Treeview ─────────────────────────────────────────────────
        self.tree_frame_inner = ctk.CTkFrame(
            self, fg_color=C.BG_CARD, corner_radius=8)
        self.tree_frame_inner.grid(
            row=2, column=0, sticky="nsew", padx=12, pady=(0, 4))
        self.tree_frame_inner.grid_rowconfigure(0, weight=1)
        self.tree_frame_inner.grid_columnconfigure(0, weight=1)
        self.tree = None

        # ── Footer ────────────────────────────────────────────────────────
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=12, pady=(2, 8))

        self.label_total_articles = ctk.CTkLabel(
            footer, text="Total articles : 0",
            font=self._f(10, "bold"), text_color=C.PRIMARY)
        self.label_total_articles.pack(side="left")

        self.label_derniere_maj = ctk.CTkLabel(
            footer, text="",
            font=self._f(9), text_color=C.TEXT_MUTED)
        self.label_derniere_maj.pack(side="right")

    # ====================================================================
    # LOGIQUE MÉTIER — inchangée
    # ====================================================================

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
        except Exception as err:
            messagebox.showerror("Erreur de connexion", f"Erreur : {err}")
            return None

    def formater_nombre(self, nombre):
        """Formate les nombres pour l'affichage (ex: 1.250,00)"""
        try:
            return f"{float(nombre):,.2f}".replace(',', ' ').replace('.', ',').replace(' ', '.')
        except:
            return "0,00"

    def creer_treeview(self):
        """Initialise le tableau avec colonnes larges et barres de défilement"""
        if self.tree:
            self.tree.destroy()

        colonnes_fixes    = ("Code", "Désignation", "Unité", "Prix")
        colonnes_magasins = [mag[1] for mag in self.magasins]
        self.colonnes_dynamiques = colonnes_fixes + tuple(colonnes_magasins) + ("Total",)

        self.tree = ttk.Treeview(
            self.tree_frame_inner,
            columns=self.colonnes_dynamiques,
            show="headings",
            style="Stock.Treeview",
            selectmode="browse")

        self.tree.tag_configure("even", background=C.BG_CARD,   foreground=C.TEXT_PRIMARY)
        self.tree.tag_configure("odd",  background="#F0F4F8",   foreground=C.TEXT_PRIMARY)
        self.tree.tag_configure("stock_zero_even", background=C.BG_CARD, foreground="#E74C3C")
        self.tree.tag_configure("stock_zero_odd",  background="#F0F4F8", foreground="#E74C3C")

        self.tree.bind("<Double-1>", self.ouvrir_inventaire_double_clic)

        vsb = ctk.CTkScrollbar(self.tree_frame_inner, orientation="vertical",   command=self.tree.yview)
        hsb = ctk.CTkScrollbar(self.tree_frame_inner, orientation="horizontal",  command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=(6, 0))
        vsb.grid(row=0, column=1, sticky="ns",  pady=(6, 0))
        hsb.grid(row=1, column=0, sticky="ew",  padx=(6, 0))

        for col in self.colonnes_dynamiques:
            self.tree.heading(col, text=col)
            if col == "Désignation":
                self.tree.column(col, width=350, anchor="w",      minwidth=200)
            elif col == "Code":
                self.tree.column(col, width=150, anchor="center")
            elif col == "Prix":
                self.tree.column(col, width=120, anchor="e")
            else:
                self.tree.column(col, width=110, anchor="center")

    def charger_stocks_avec_progression(self):
        """Charge les stocks avec une fenêtre de progression"""
        progress_window = ctk.CTkToplevel(self.root)
        progress_window.title("Chargement en cours...")
        progress_window.geometry("400x150")
        progress_window.transient(self.root)
        progress_window.grab_set()
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth()  // 2) - 200
        y = (progress_window.winfo_screenheight() // 2) - 75
        progress_window.geometry(f"400x150+{x}+{y}")
        label = ctk.CTkLabel(progress_window, text="Chargement des stocks...", font=self._f(12))
        label.pack(pady=20)
        progress_bar = ttk.Progressbar(progress_window, mode='indeterminate', length=300)
        progress_bar.pack(pady=10)
        progress_bar.start(10)
        ctk.CTkLabel(progress_window, text="Veuillez patienter...", font=self._f(9)).pack(pady=10)

        def charger_en_arriere_plan():
            try:
                self.charger_stocks()
                progress_window.after(0, progress_window.destroy)
            except Exception as e:
                progress_window.after(0, progress_window.destroy)
                messagebox.showerror("Erreur", f"Erreur lors du chargement: {str(e)}")

        threading.Thread(target=charger_en_arriere_plan, daemon=True).start()

    def charger_stocks(self):
        """Charge en 2 phases: articles/unites puis stocks calculés."""
        self.creer_treeview()
        self._charger_articles_unites_initiaux()
        threading.Thread(target=self._charger_stocks_calcules_async, daemon=True).start()

    def _charger_articles_unites_initiaux(self):
        """Affiche immédiatement les articles/unités avec stocks à 0."""
        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    u.codearticle,
                    a.designation,
                    u.designationunite,
                    COALESCE(dp.prix, 0) AS prix
                FROM tb_unite u
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN (
                    SELECT idunite, prix
                    FROM (
                        SELECT idunite, prix,
                               ROW_NUMBER() OVER (
                                   PARTITION BY idunite
                                   ORDER BY dateregistre DESC
                               ) AS rn
                        FROM tb_prix
                        WHERE deleted = 0
                    ) x
                    WHERE x.rn = 1
                ) dp ON dp.idunite = u.idunite
                WHERE a.deleted = 0 AND COALESCE(u.deleted, 0) = 0
                ORDER BY a.designation ASC, u.codearticle ASC
            """)
            base_rows = cursor.fetchall()
            self.all_data = []
            for code, designation, unite, prix in base_rows:
                valeurs = [code, designation, unite, self.formater_nombre(prix)]
                for _idmag, _nom_mag in self.magasins:
                    valeurs.append(self.formater_nombre(0))
                valeurs.append(self.formater_nombre(0))
                self.all_data.append((valeurs, 0.0))
            self.recharger_treeview()
            self.label_derniere_maj.configure(
                text="Chargement des stocks en cours…")
        except Exception as e:
            messagebox.showerror("Erreur de chargement", f"Détails : {str(e)}")
        finally:
            cursor.close()
            conn.close()

    def _charger_stocks_calcules_async(self):
        """Calcule les stocks en arrière-plan et applique le résultat sur l'UI."""
        try:
            all_data_calculee = self._calculer_all_data_stocks()
            self.after(0, lambda: self._appliquer_all_data_calculee(all_data_calculee))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Erreur de chargement", f"Détails : {str(e)}"))

    def _calculer_all_data_stocks(self):
        """Exécute la requête consolidée et prépare all_data."""
        conn = self.connect_db()
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            query_optimisee = """
            WITH unite_hierarchie AS (
                SELECT idarticle, idunite, niveau, qtunite, designationunite
                FROM tb_unite WHERE deleted = 0
            ),
            unite_coeff AS (
                SELECT idarticle, idunite, niveau, qtunite, designationunite,
                    exp(sum(ln(NULLIF(CASE WHEN qtunite > 0 THEN qtunite ELSE 1 END, 0)))
                        OVER (PARTITION BY idarticle ORDER BY niveau
                              ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                    ) as coeff_hierarchique
                FROM unite_hierarchie
            ),
            base_unite_par_article AS (
                SELECT DISTINCT ON (idarticle) idarticle, idunite
                FROM tb_unite WHERE deleted = 0
                ORDER BY idarticle, qtunite ASC, idunite ASC
            ),
            rec  AS (SELECT lf.idarticle, lf.idunite, lf.idmag, SUM(lf.qtlivrefrs) AS quantite FROM tb_livraisonfrs lf WHERE lf.deleted=0 GROUP BY lf.idarticle, lf.idunite, lf.idmag),
            ven  AS (SELECT vd.idarticle, vd.idunite, v.idmag,  SUM(vd.qtvente)    AS quantite FROM tb_ventedetail vd INNER JOIN tb_vente v ON vd.idvente=v.id AND v.deleted=0 AND v.statut='VALIDEE' WHERE vd.deleted=0 GROUP BY vd.idarticle, vd.idunite, v.idmag),
            tin  AS (SELECT t.idarticle,  t.idunite,  t.idmagentree  AS idmag, SUM(t.qttransfert) AS quantite FROM tb_transfertdetail t WHERE t.deleted=0 GROUP BY t.idarticle, t.idunite, t.idmagentree),
            tout AS (SELECT t.idarticle,  t.idunite,  t.idmagsortie  AS idmag, SUM(t.qttransfert) AS quantite FROM tb_transfertdetail t WHERE t.deleted=0 GROUP BY t.idarticle, t.idunite, t.idmagsortie),
            sor  AS (SELECT sd.idarticle, sd.idunite, sd.idmag,                SUM(sd.qtsortie)   AS quantite FROM tb_sortiedetail sd GROUP BY sd.idarticle, sd.idunite, sd.idmag),
            inv  AS (SELECT bu.idarticle, bu.idunite, i.idmag,                 SUM(i.qtinventaire) AS quantite FROM tb_inventaire i INNER JOIN tb_unite u ON i.codearticle=u.codearticle INNER JOIN base_unite_par_article bu ON bu.idarticle=u.idarticle AND bu.idunite=u.idunite GROUP BY bu.idarticle, bu.idunite, i.idmag),
            avo  AS (SELECT ad.idarticle, ad.idunite, ad.idmag,                SUM(ad.qtavoir)    AS quantite FROM tb_avoir a INNER JOIN tb_avoirdetail ad ON a.id=ad.idavoir WHERE a.deleted=0 AND ad.deleted=0 GROUP BY ad.idarticle, ad.idunite, ad.idmag),
            conso AS (SELECT cd.idarticle, cd.idunite, cd.idmag,               SUM(cd.qtconsomme) AS quantite FROM tb_consommationinterne_details cd GROUP BY cd.idarticle, cd.idunite, cd.idmag),
            ech_in  AS (SELECT dce.idarticle, dce.idunite, dce.idmagasin AS idmag, SUM(dce.quantite_entree) AS quantite FROM tb_detailchange_entree dce GROUP BY dce.idarticle, dce.idunite, dce.idmagasin),
            ech_out AS (SELECT dcs.idarticle, dcs.idunite, dcs.idmagasin AS idmag, SUM(dcs.quantite_sortie) AS quantite FROM tb_detailchange_sortie dcs GROUP BY dcs.idarticle, dcs.idunite, dcs.idmagasin),
            mouvements_agreges AS (
                SELECT idarticle, idunite, idmag, quantite, 'reception'            AS type_mouvement FROM rec   UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'vente'                AS type_mouvement FROM ven   UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'transfert_in'         AS type_mouvement FROM tin   UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'transfert_out'        AS type_mouvement FROM tout  UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'sortie'               AS type_mouvement FROM sor   UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'inventaire'           AS type_mouvement FROM inv   UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'avoir'                AS type_mouvement FROM avo   UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'consommation_interne' AS type_mouvement FROM conso UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'echange_entree'       AS type_mouvement FROM ech_in  UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'echange_sortie'       AS type_mouvement FROM ech_out
            ),
            mouvements_bruts AS (
                SELECT ma.idarticle, ma.idmag,
                       COALESCE(uc.coeff_hierarchique,1) as coeff_source_vers_base,
                       ma.quantite, ma.type_mouvement
                FROM mouvements_agreges ma
                LEFT JOIN unite_coeff uc ON uc.idarticle=ma.idarticle AND uc.idunite=ma.idunite
            ),
            solde_base_par_mag AS (
                SELECT idarticle, idmag,
                    SUM(CASE type_mouvement
                        WHEN 'reception'            THEN  quantite*coeff_source_vers_base
                        WHEN 'transfert_in'         THEN  quantite*coeff_source_vers_base
                        WHEN 'inventaire'           THEN  quantite*coeff_source_vers_base
                        WHEN 'avoir'                THEN  quantite*coeff_source_vers_base
                        WHEN 'echange_entree'       THEN  quantite*coeff_source_vers_base
                        WHEN 'vente'                THEN -quantite*coeff_source_vers_base
                        WHEN 'sortie'               THEN -quantite*coeff_source_vers_base
                        WHEN 'transfert_out'        THEN -quantite*coeff_source_vers_base
                        WHEN 'consommation_interne' THEN -quantite*coeff_source_vers_base
                        WHEN 'echange_sortie'       THEN -quantite*coeff_source_vers_base
                        ELSE 0 END
                    ) as solde_base
                FROM mouvements_bruts GROUP BY idarticle, idmag
            ),
            dernier_prix AS (
                SELECT idunite, prix
                FROM (
                    SELECT idunite, prix,
                           ROW_NUMBER() OVER (
                               PARTITION BY idunite
                               ORDER BY dateregistre DESC
                           ) AS rn
                    FROM tb_prix
                    WHERE deleted = 0
                ) p
                WHERE p.rn = 1
            )
            SELECT u.codearticle, a.designation, u.designationunite,
                COALESCE(dp.prix, 0) AS prix,
                u.idarticle, u.idunite, m.idmag,
                COALESCE(sb.solde_base,0) / NULLIF(COALESCE(uc.coeff_hierarchique,1),0) as stock
            FROM tb_unite u
            INNER JOIN tb_article a ON u.idarticle=a.idarticle
            CROSS JOIN tb_magasin m
            LEFT JOIN solde_base_par_mag sb ON sb.idarticle=u.idarticle AND sb.idmag=m.idmag
            LEFT JOIN unite_coeff uc ON uc.idarticle=u.idarticle AND uc.idunite=u.idunite
            LEFT JOIN dernier_prix dp ON dp.idunite = u.idunite
            WHERE a.deleted=0 AND m.deleted=0
            ORDER BY a.designation ASC, u.codearticle ASC
            """
            cursor.execute(query_optimisee)
            resultats = cursor.fetchall()
            articles_dict = {}
            for code, desig, unite, prix, idarticle, idunite, idmag, stock in resultats:
                key = (code, idunite)
                if key not in articles_dict:
                    articles_dict[key] = {
                        'code': code,
                        'designation': desig,
                        'unite': unite,
                        'prix': prix,
                        'stocks': {},
                        'total': 0
                    }
                if idmag:
                    nom_mag   = next((m[1] for m in self.magasins if m[0] == idmag), f"Mag{idmag}")
                    stock_val = max(0, stock or 0)
                    articles_dict[key]['stocks'][nom_mag] = stock_val
                    articles_dict[key]['total'] += stock_val
            all_data = []
            for _idx, (_key, data) in enumerate(articles_dict.items()):
                valeurs = [data['code'], data['designation'], data['unite'], self.formater_nombre(data['prix'])]
                for _, nom_mag in self.magasins:
                    valeurs.append(self.formater_nombre(data['stocks'].get(nom_mag, 0)))
                valeurs.append(self.formater_nombre(data['total']))
                all_data.append((valeurs, data['total']))
            return all_data
        except Exception as e:
            print(f"ERREUR DÉTAILLÉE: {e}")
            return []
        finally:
            cursor.close()
            conn.close()

    def _appliquer_all_data_calculee(self, all_data_calculee):
        """Applique les stocks calculés et rafraîchit le Treeview."""
        self.all_data = all_data_calculee
        if self.entry_recherche.get().strip():
            self.filtrer_stocks()
        else:
            self.recharger_treeview()
        self.label_total_articles.configure(text=f"Total articles : {len(self.all_data)}")
        self.label_derniere_maj.configure(
            text=f"Actualisé : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        self.mettre_a_jour_badge_peremption()

    def calculer_stock_article(self, idarticle, idunite_cible, idmag=None):
        conn = self.connect_db()
        if not conn: return 0
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT idunite, codearticle, COALESCE(qtunite, 1), COALESCE(niveau, 0)
                FROM tb_unite WHERE idarticle = %s
                ORDER BY COALESCE(niveau, 0) ASC, idunite ASC
            """, (idarticle,))
            unites_liees = cursor.fetchall()
            coeffs_cumules = {}
            coeff_courant  = 1.0
            for idu, _code, qt_u, _niv in unites_liees:
                qt_safe = qt_u if qt_u and qt_u > 0 else 1
                coeff_courant *= qt_safe
                coeffs_cumules[idu] = coeff_courant
            qtunite_affichage = 1
            for idu, _code, _qt_u, _niv in unites_liees:
                if idu == idunite_cible:
                    qtunite_affichage = coeffs_cumules.get(idu, 1)
                    break
            total_stock_global_base = 0
            for idu_boucle, code_boucle, _qtunite_boucle, _niv in unites_liees:
                coeff_source = coeffs_cumules.get(idu_boucle, 1)
                q_rec = "SELECT COALESCE(SUM(qtlivrefrs), 0) FROM tb_livraisonfrs WHERE idarticle = %s AND idunite = %s AND deleted = 0"
                p_rec = [idarticle, idu_boucle]
                if idmag: q_rec += " AND idmag = %s"; p_rec.append(idmag)
                cursor.execute(q_rec, p_rec); receptions = cursor.fetchone()[0] or 0
                q_ven = "SELECT COALESCE(SUM(qtvente), 0) FROM tb_ventedetail WHERE idarticle = %s AND idunite = %s AND deleted = 0"
                p_ven = [idarticle, idu_boucle]
                if idmag: q_ven += " AND idmag = %s"; p_ven.append(idmag)
                cursor.execute(q_ven, p_ven); ventes = cursor.fetchone()[0] or 0
                q_sort = "SELECT COALESCE(SUM(qtsortie), 0) FROM tb_sortiedetail WHERE idarticle = %s AND idunite = %s"
                p_sort = [idarticle, idu_boucle]
                if idmag: q_sort += " AND idmag = %s"; p_sort.append(idmag)
                cursor.execute(q_sort, p_sort); sorties = cursor.fetchone()[0] or 0
                cursor.execute("SELECT COALESCE(SUM(qttransfert), 0) FROM tb_transfertdetail WHERE idarticle = %s AND idunite = %s AND deleted = 0" + (" AND idmagentree = %s" if idmag else ""), ([idarticle, idu_boucle, idmag] if idmag else [idarticle, idu_boucle]))
                t_in = cursor.fetchone()[0] or 0
                cursor.execute("SELECT COALESCE(SUM(qttransfert), 0) FROM tb_transfertdetail WHERE idarticle = %s AND idunite = %s AND deleted = 0" + (" AND idmagsortie = %s" if idmag else ""), ([idarticle, idu_boucle, idmag] if idmag else [idarticle, idu_boucle]))
                t_out = cursor.fetchone()[0] or 0
                q_inv = "SELECT COALESCE(SUM(qtinventaire), 0) FROM tb_inventaire WHERE codearticle = %s"
                p_inv = [code_boucle]
                if idmag: q_inv += " AND idmag = %s"; p_inv.append(idmag)
                cursor.execute(q_inv, p_inv); inv = cursor.fetchone()[0] or 0
                q_avoir = """
                    SELECT COALESCE(SUM(ad.qtavoir), 0)
                    FROM tb_avoirdetail ad INNER JOIN tb_avoir a ON ad.idavoir = a.id
                    WHERE ad.idarticle = %s AND ad.idunite = %s AND a.deleted = 0 AND ad.deleted = 0
                """
                p_avoir = [idarticle, idu_boucle]
                if idmag: q_avoir += " AND ad.idmag = %s"; p_avoir.append(idmag)
                cursor.execute(q_avoir, p_avoir); avoirs = cursor.fetchone()[0] or 0
                q_conso = "SELECT COALESCE(SUM(qtconsomme), 0) FROM tb_consommationinterne_details WHERE idarticle = %s AND idunite = %s"
                p_conso = [idarticle, idu_boucle]
                if idmag: q_conso += " AND idmag = %s"; p_conso.append(idmag)
                cursor.execute(q_conso, p_conso); consommations = cursor.fetchone()[0] or 0
                q_ech_in = "SELECT COALESCE(SUM(quantite_entree), 0) FROM tb_detailchange_entree WHERE idarticle = %s AND idunite = %s"
                p_ech_in = [idarticle, idu_boucle]
                if idmag: q_ech_in += " AND idmagasin = %s"; p_ech_in.append(idmag)
                cursor.execute(q_ech_in, p_ech_in); echange_entrees = cursor.fetchone()[0] or 0
                q_ech_out = "SELECT COALESCE(SUM(quantite_sortie), 0) FROM tb_detailchange_sortie WHERE idarticle = %s AND idunite = %s"
                p_ech_out = [idarticle, idu_boucle]
                if idmag: q_ech_out += " AND idmagasin = %s"; p_ech_out.append(idmag)
                cursor.execute(q_ech_out, p_ech_out); echange_sorties = cursor.fetchone()[0] or 0
                solde_unite = (receptions + t_in + inv + avoirs + echange_entrees
                               - ventes - sorties - t_out - consommations - echange_sorties)
                total_stock_global_base += (solde_unite * coeff_source)
            return max(0, total_stock_global_base / qtunite_affichage)
        except Exception as e:
            print(f"Erreur calcul stock consolidé : {e}")
            return 0
        finally:
            cursor.close()
            conn.close()

    def charger_magasins(self):
        """Charge la liste des magasins depuis la base de données"""
        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT idmag, designationmag FROM tb_magasin
                WHERE deleted = 0 ORDER BY designationmag
            """)
            self.magasins = cursor.fetchall()
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger les magasins : {str(e)}")
        finally:
            cursor.close()
            conn.close()

    def ouvrir_inventaire_double_clic(self, event):
        """Ouvre la fenêtre d'inventaire lors d'un double-clic sur une ligne"""
        selection = self.tree.selection()
        if not selection:
            return
        item         = self.tree.item(selection[0])
        code_article = str(item['values'][0]).zfill(10)
        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.idarticle, u.idunite, a.designation
                FROM tb_unite u INNER JOIN tb_article a ON u.idarticle = a.idarticle
                WHERE u.codearticle = %s LIMIT 1
            """, (str(code_article),))
            result = cursor.fetchone()
            if not result:
                messagebox.showwarning("Erreur", f"Article {code_article} introuvable")
                return
            idarticle, idunite, designation = result
            article_data = {'code': code_article, 'designation': designation}
            PageInventaire(self, article_data, self.iduser)
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'ouverture : {str(e)}")
        finally:
            cursor.close()
            conn.close()

    def clignoter_bouton(self):
        """Fait clignoter le bouton de péremption"""
        if not self.clignotement_actif:
            self.clignotement_actif = True

        def toggle_color():
            if self.clignotement_actif:
                couleur_actuelle = self.btn_peremption.cget("fg_color")
                nouvelle_couleur = "#ffffff" if couleur_actuelle == self.couleur_alerte else self.couleur_alerte
                self.btn_peremption.configure(fg_color=nouvelle_couleur)
                self.after(500, toggle_color)

        toggle_color()

    def filtrer_stocks(self):
        """Filtre les données selon le critère de recherche"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        search_term = self.entry_recherche.get().lower().strip()
        if not search_term:
            self.recharger_treeview()
            return
        filtered_data = [
            (valeurs, total) for valeurs, total in self.all_data
            if search_term in f"{valeurs[0]} {valeurs[1]} {valeurs[2]} {valeurs[3]}".lower()
        ]
        if filtered_data:
            for idx, (valeurs, total) in enumerate(filtered_data):
                zebra = "even" if idx % 2 == 0 else "odd"
                tag   = (f"stock_zero_{zebra}" if abs(float(total)) < 1e-9 else zebra)
                self.tree.insert("", "end", values=valeurs, tags=(tag,))
            self.label_total_articles.configure(text=f"Total articles : {len(filtered_data)}")
        else:
            empty = ["", "Aucun résultat trouvé", "", ""] + [""] * (len(self.colonnes_dynamiques) - 4)
            self.tree.insert('', 'end', values=empty)
            self.label_total_articles.configure(text="Total articles : 0")

    def reinitialiser_filtre(self):
        """Réinitialise le filtre et recharge toutes les données"""
        self.entry_recherche.delete(0, 'end')
        self.recharger_treeview()

    def recharger_treeview(self):
        """Recharge le Treeview avec toutes les données stockées"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        if self.all_data:
            for idx, (valeurs, total) in enumerate(self.all_data):
                zebra = "even" if idx % 2 == 0 else "odd"
                tag   = (f"stock_zero_{zebra}" if abs(float(total)) < 1e-9 else zebra)
                self.tree.insert("", "end", values=valeurs, tags=(tag,))
            self.label_total_articles.configure(text=f"Total articles : {len(self.all_data)}")
        else:
            empty = ["", "Aucun article trouvé", "", ""] + [""] * (len(self.colonnes_dynamiques) - 4)
            self.tree.insert('', 'end', values=empty)
            self.label_total_articles.configure(text="Total articles : 0")

    def exporter_stocks(self):
        """Exporte les stocks vers un fichier CSV"""
        try:
            from tkinter import filedialog
            import csv
            fichier = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile=f"stocks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            if not fichier:
                return
            with open(fichier, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(self.colonnes_dynamiques)
                for item in self.tree.get_children():
                    writer.writerow(self.tree.item(item)['values'])
            messagebox.showinfo("Succès", f"Stocks exportés vers :\n{fichier}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'export: {str(e)}")

    def mettre_a_jour_tb_stock(self):
        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.idarticle, u.idunite, u.codearticle, u.designationunite, a.designation
                FROM tb_article a INNER JOIN tb_unite u ON a.idarticle = u.idarticle
                WHERE a.deleted = 0 ORDER BY a.designation ASC, u.codearticle ASC
            """)
            articles = cursor.fetchall()
            compteur_maj = compteur_ins = compteur_total = 0
            for idarticle, idunite, code_art, unite_desig, art_desig in articles:
                for idmag, nom_mag in self.magasins:
                    compteur_total += 1
                    stock_calcule  = self.calculer_stock_article(idarticle, idunite, idmag)
                    cursor.execute("SELECT qtstock FROM tb_stock WHERE codearticle = %s AND idmag = %s",
                                   (str(code_art), idmag))
                    resultat = cursor.fetchone()
                    if resultat:
                        if abs(float(resultat[0] or 0) - float(stock_calcule)) > 0.001:
                            cursor.execute("UPDATE tb_stock SET qtstock = %s WHERE codearticle = %s AND idmag = %s",
                                           (stock_calcule, str(code_art), idmag))
                            compteur_maj += 1
                    else:
                        cursor.execute("INSERT INTO tb_stock (codearticle, idmag, qtstock, qtalert, deleted) VALUES (%s, %s, %s, 0, 0)",
                                       (str(code_art), idmag, stock_calcule))
                        compteur_ins += 1
                    if (compteur_maj + compteur_ins) % 100 == 0:
                        conn.commit()
            conn.commit()
            messagebox.showinfo("Synchronisation réussie",
                                f"✅ {compteur_maj} mises à jour, {compteur_ins} créations, {compteur_total} lignes traitées.")
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur de synchronisation", str(e))
            import traceback; traceback.print_exc()
        finally:
            cursor.close()
            conn.close()

    def ouvrir_fenetre_peremption(self):
        """Ouvre une fenêtre Toplevel affichant les articles périmés"""
        self.fenetre_peremp = ctk.CTkToplevel(self)
        self.fenetre_peremp.title("Suivi des Péremptions")
        self.fenetre_peremp.geometry("1100x700")
        if _T:
            Theme.apply_toplevel(self.fenetre_peremp)
        self.fenetre_peremp.attributes('-topmost', True)
        self.fenetre_peremp.focus_set()
        self.page_peremp = PageGestionPeremption(self.fenetre_peremp, iduser=self.iduser)
        self.page_peremp.pack(fill="both", expand=True, padx=10, pady=10)

    def mettre_a_jour_badge_peremption(self):
        """Analyse les dates et ajuste la couleur et le texte du bouton"""
        conn = self.connect_db()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT l.idarticle, l.idunite, l.dateperemption FROM tb_livraisonfrs l WHERE l.dateperemption IS NOT NULL")
            lignes     = cursor.fetchall()
            aujourdhui = datetime.now().date()
            un_mois    = aujourdhui + timedelta(days=30)
            nb_perimes = nb_urgents = 0
            for id_art, id_uni, d_peremp in lignes:
                stock = self.calculer_stock_article(id_art, id_uni)
                if stock > 0:
                    if d_peremp <= aujourdhui: nb_perimes += 1
                    elif d_peremp <= un_mois:  nb_urgents += 1
            if nb_perimes > 0:
                self.btn_peremption.configure(text=f"🚨  PÉRIMÉS ({nb_perimes})")
                self.couleur_alerte = C.DANGER
                if not self.clignotement_actif:
                    self.clignoter_bouton()
            elif nb_urgents > 0:
                self.clignotement_actif = False
                self.btn_peremption.configure(
                    text=f"⚠️  Alerte ({nb_urgents})",
                    fg_color=C.WARNING, hover_color="#E67E22")
            else:
                self.clignotement_actif = False
                self.btn_peremption.configure(
                    text="🛡️  Articles Périmés",
                    fg_color=C.DANGER, hover_color=C.DANGER_DARK)
        except Exception as e:
            print(f"Erreur badge: {e}")
        finally:
            cursor.close()
            conn.close()


# ── Test standalone ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    app = ctk.CTk()
    app.title("iJeery — Gestion des Stocks")
    app.geometry("1100x750")
    if _T:
        Theme.apply(app)
    app.grid_rowconfigure(0, weight=1)
    app.grid_columnconfigure(0, weight=1)
    PageStock(app, iduser=1).grid(row=0, column=0, sticky="nsew")
    app.mainloop()
