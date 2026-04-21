# -*- coding: utf-8 -*-
import customtkinter as ctk
from tkinter import messagebox
import psycopg2
import json
from datetime import datetime
from resource_utils import get_config_path, safe_file_read
import traceback
from app_theme import Theme, Colors, Fonts, Layout, styled
from log_utils import AppLogger


class PageInventaire(ctk.CTkToplevel):
    def __init__(self, master, article_data, iduser):
        super().__init__(master)
        self.title(f"Inventaire - {article_data['designation']}")
        self.geometry("860x640")
        self.iduser = iduser
        self.article_data = article_data
        self.magasins_dict = {}
        self.unites_dict = {}
        self.session_data = getattr(master, "session_data", None) or {"user_id": self.iduser}
        self._logger = AppLogger(session_data=self.session_data, fallback_user_id=self.iduser)

        self.attributes('-topmost', True)
        Theme.apply_toplevel(self)
        self.setup_ui()
        self.charger_magasins()
        self.charger_unites()
        self.refresh_stocks_overview()

    # ─────────────────────────────────────────────────────────────────────────
    # DB
    # ─────────────────────────────────────────────────────────────────────────

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

    # ─────────────────────────────────────────────────────────────────────────
    # UI
    # ─────────────────────────────────────────────────────────────────────────

    def setup_ui(self):
        header = styled.frame(self)
        header.pack(fill="x", padx=20, pady=(18, 10))
        styled.label_title(header, text="Ajustement d'inventaire").pack(anchor="w")
        styled.label_muted(
            header,
            text="Contrôlez le stock par magasin, puis validez l'inventaire par unité."
        ).pack(anchor="w", pady=(2, 0))

        body = styled.frame(self)
        body.pack(fill="both", expand=True, padx=20, pady=(0, 18))

        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)

        # ── Colonne gauche : infos article + stocks ──────────────────────────
        left = styled.frame(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        info_card = styled.card(left)
        info_card.pack(fill="x", pady=(0, 12))
        info_card.pack_propagate(False)
        styled.label_heading(info_card, text="Article").pack(anchor="w", padx=16, pady=(12, 6))
        styled.label(info_card, text=self.article_data["designation"], size=15, weight="bold").pack(
            anchor="w", padx=16
        )
        styled.label_muted(
            info_card, text=f"Code : {self.article_data['code']}"
        ).pack(anchor="w", padx=16, pady=(2, 10))

        unit_row = styled.frame(info_card)
        unit_row.pack(fill="x", padx=16, pady=(0, 12))
        styled.label_muted(unit_row, text="Unité d'inventaire", anchor="w").pack(side="left")
        self.combo_unite = styled.combobox(unit_row, values=[], command=self.on_unite_change, width=220)
        self.combo_unite.pack(side="right")

        stock_card = styled.card(left)
        stock_card.pack(fill="both", expand=True)
        styled.label_heading(stock_card, text="Stocks par magasin").pack(anchor="w", padx=16, pady=(12, 6))
        self.label_stock_total = styled.label(
            stock_card, text="Stock total: --", size=14, weight="bold", color=Colors.PRIMARY
        )
        self.label_stock_total.pack(anchor="w", padx=16, pady=(0, 8))

        self.stock_list = styled.scrollable_frame(stock_card)
        self.stock_list.pack(fill="both", expand=True, padx=8, pady=(0, 12))

        # ── Colonne droite : inventaire ──────────────────────────────────────
        right = styled.frame(body)
        right.grid(row=0, column=1, sticky="nsew")

        inv_card = styled.card(right)
        inv_card.pack(fill="x")
        styled.label_heading(inv_card, text="Inventaire ciblé").pack(anchor="w", padx=16, pady=(12, 6))

        styled.label_muted(inv_card, text="Magasin", anchor="w").pack(fill="x", padx=16, pady=(4, 2))
        self.combo_magasin = styled.combobox(inv_card, values=[], command=self.afficher_stock_actuel, width=250)
        self.combo_magasin.pack(fill="x", padx=16, pady=(0, 8))

        self.label_stock_actuel = styled.label(
            inv_card, text="Stock actuel: --", size=13, weight="bold", color=Colors.INFO
        )
        self.label_stock_actuel.pack(anchor="w", padx=16, pady=(0, 8))

        styled.label_muted(inv_card, text="Quantité réelle comptée", anchor="w").pack(
            fill="x", padx=16, pady=(6, 2)
        )
        self.entry_qt = styled.entry(inv_card, placeholder="ex: 120")
        self.entry_qt.pack(fill="x", padx=16, pady=(0, 8))

        styled.label_muted(inv_card, text="Observation (traçabilité)", anchor="w").pack(
            fill="x", padx=16, pady=(6, 2)
        )
        self.entry_obs = styled.entry(inv_card, placeholder="ex: comptage inventaire mensuel")
        self.entry_obs.pack(fill="x", padx=16, pady=(0, 12))

        actions = styled.frame(inv_card)
        actions.pack(fill="x", padx=16, pady=(0, 14))
        styled.button_success(
            actions, text="Valider l'inventaire", icon="✔", width=180, height=Layout.BTN_H,
            command=self.valider
        ).pack(side="left")
        styled.button_secondary(
            actions, text="Rafraîchir stocks", icon="↻", width=160, height=Layout.BTN_H,
            command=self.refresh_stocks_overview
        ).pack(side="right")

    # ─────────────────────────────────────────────────────────────────────────
    # Chargement des données
    # ─────────────────────────────────────────────────────────────────────────

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
                        magasin_defaut_nom = next(
                            (nom for nom, idmag in self.magasins_dict.items() if idmag == idmag_user),
                            None
                        )
                except Exception:
                    magasin_defaut_nom = None

            if rows:
                nom_selectionne = magasin_defaut_nom if magasin_defaut_nom in self.magasins_dict else rows[0][1]
                self.combo_magasin.set(nom_selectionne)
                self.afficher_stock_actuel(nom_selectionne)
            conn.close()

    def charger_unites(self):
        conn = self.connect_db()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT idunite, designationunite
                FROM tb_unite
                WHERE codearticle = %s AND COALESCE(deleted, 0) = 0
                ORDER BY COALESCE(niveau, 0) ASC, idunite ASC
            """, (self.article_data["code"],))
            rows = cursor.fetchall()
            self.unites_dict = {r[1] or f"Unité {r[0]}": r[0] for r in rows}
            self.combo_unite.configure(values=list(self.unites_dict.keys()))
            if rows:
                default_id = self.article_data.get("idunite")
                default_name = None
                if default_id:
                    default_name = next(
                        (name for name, uid in self.unites_dict.items() if uid == default_id),
                        None
                    )
                first_name = default_name or rows[0][1] or f"Unité {rows[0][0]}"
                self.combo_unite.set(first_name)
            conn.close()

    def get_selected_unite_id(self):
        label = self.combo_unite.get().strip()
        return self.unites_dict.get(label)

    def on_unite_change(self, _=None):
        self.afficher_stock_actuel()
        self.refresh_stocks_overview()

    def formater_nombre(self, nombre):
        try:
            return f"{float(nombre):,.2f}".replace(',', ' ').replace('.', ',').replace(' ', '.')
        except Exception:
            return "0,00"

    # ─────────────────────────────────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════════
    #  CALCUL DU STOCK RÉEL — requête SQL consolidée (idarticle, idunite, idmag)
    # ══════════════════════════════════════════════════════════════════════════
    # ─────────────────────────────────────────────────────────────────────────

    _SQL_STOCK = """
    WITH
      -- ════════════════════════════════════════════════════════════════
      -- PARAMÈTRES  (transmis via %(p_idarticle)s / %(p_idunite)s / %(p_idmag)s)
      -- ════════════════════════════════════════════════════════════════
      params AS (
        SELECT
          %(p_idarticle)s::integer AS p_idarticle,
          %(p_idunite)s::integer   AS p_idunite,
          %(p_idmag)s::integer     AS p_idmag   -- NULL => tous magasins
      ),

      -- ════════════════════════════════════════════════════════════════
      -- HIÉRARCHIE DES UNITÉS DE L'ARTICLE CIBLÉ
      -- ════════════════════════════════════════════════════════════════
      unite_hierarchie AS (
        SELECT
          u.idarticle,
          u.idunite,
          u.niveau,
          CASE WHEN COALESCE(u.qtunite, 1) > 0 THEN u.qtunite ELSE 1 END AS qtunite
        FROM tb_unite u, params p
        WHERE u.idarticle = p.p_idarticle
          AND COALESCE(u.deleted, 0) = 0
      ),

      -- Coefficient cumulé de chaque unité vers l'unité de base (la plus petite)
      unite_coeff AS (
        SELECT
          idarticle,
          idunite,
          EXP(
            SUM(LN(qtunite))
            OVER (
              PARTITION BY idarticle
              ORDER BY niveau
              ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            )
          ) AS coeff_vers_base
        FROM unite_hierarchie
      ),

      -- Coefficient de l'unité cible (p_idunite)
      coeff_cible AS (
        SELECT uc.coeff_vers_base AS coeff
        FROM unite_coeff uc, params p
        WHERE uc.idunite = p.p_idunite
      ),

      -- Code article pour tb_inventaire (lié via codearticle)
      code_cible AS (
        SELECT u.codearticle
        FROM tb_unite u, params p
        WHERE u.idarticle = p.p_idarticle
          AND u.idunite   = p.p_idunite
        LIMIT 1
      ),

      -- ════════════════════════════════════════════════════════════════
      -- MOUVEMENTS AGRÉGÉS PAR (idunite, idmag) — filtrés sur p_idmag
      -- Quand p_idmag IS NULL → tous les magasins (somme globale)
      -- ════════════════════════════════════════════════════════════════

      rec AS (
        SELECT lf.idunite, lf.idmag, SUM(lf.qtlivrefrs) AS qt
        FROM tb_livraisonfrs lf, params p
        WHERE lf.idarticle = p.p_idarticle
          AND lf.deleted   = 0
          AND (p.p_idmag IS NULL OR lf.idmag = p.p_idmag)
        GROUP BY lf.idunite, lf.idmag
      ),

      ven AS (
        SELECT vd.idunite, v.idmag, SUM(vd.qtvente) AS qt
        FROM tb_ventedetail vd
        INNER JOIN tb_vente v ON v.id      = vd.idvente
                              AND v.deleted = 0
                              AND v.statut  = 'VALIDEE',
             params p
        WHERE vd.idarticle = p.p_idarticle
          AND vd.deleted   = 0
          AND (p.p_idmag IS NULL OR v.idmag = p.p_idmag)
        GROUP BY vd.idunite, v.idmag
      ),

      t_in AS (
        SELECT td.idunite, td.idmagentree AS idmag, SUM(td.qttransfert) AS qt
        FROM tb_transfertdetail td, params p
        WHERE td.idarticle = p.p_idarticle
          AND td.deleted   = 0
          AND (p.p_idmag IS NULL OR td.idmagentree = p.p_idmag)
        GROUP BY td.idunite, td.idmagentree
      ),

      t_out AS (
        SELECT td.idunite, td.idmagsortie AS idmag, SUM(td.qttransfert) AS qt
        FROM tb_transfertdetail td, params p
        WHERE td.idarticle = p.p_idarticle
          AND td.deleted   = 0
          AND (p.p_idmag IS NULL OR td.idmagsortie = p.p_idmag)
        GROUP BY td.idunite, td.idmagsortie
      ),

      sor AS (
        SELECT sd.idunite, sd.idmag, SUM(sd.qtsortie) AS qt
        FROM tb_sortiedetail sd, params p
        WHERE sd.idarticle = p.p_idarticle
          AND (p.p_idmag IS NULL OR sd.idmag = p.p_idmag)
        GROUP BY sd.idunite, sd.idmag
      ),

      inv AS (
        SELECT u.idunite, i.idmag, SUM(i.qtinventaire) AS qt
        FROM tb_inventaire i
        INNER JOIN tb_unite u ON u.codearticle = i.codearticle
        CROSS JOIN params p
        CROSS JOIN code_cible cc
        WHERE i.codearticle = cc.codearticle
          AND u.idarticle   = p.p_idarticle
          AND (p.p_idmag IS NULL OR i.idmag = p.p_idmag)
        GROUP BY u.idunite, i.idmag
      ),

      avo AS (
        SELECT ad.idunite, ad.idmag, SUM(ad.qtavoir) AS qt
        FROM tb_avoirdetail ad
        INNER JOIN tb_avoir a ON a.id = ad.idavoir AND a.deleted = 0,
             params p
        WHERE ad.idarticle = p.p_idarticle
          AND ad.deleted   = 0
          AND (p.p_idmag IS NULL OR ad.idmag = p.p_idmag)
        GROUP BY ad.idunite, ad.idmag
      ),

      conso AS (
        SELECT cd.idunite, cd.idmag, SUM(cd.qtconsomme) AS qt
        FROM tb_consommationinterne_details cd, params p
        WHERE cd.idarticle = p.p_idarticle
          AND (p.p_idmag IS NULL OR cd.idmag = p.p_idmag)
        GROUP BY cd.idunite, cd.idmag
      ),

      ech_in AS (
        SELECT dce.idunite, dce.idmagasin AS idmag, SUM(dce.quantite_entree) AS qt
        FROM tb_detailchange_entree dce, params p
        WHERE dce.idarticle = p.p_idarticle
          AND (p.p_idmag IS NULL OR dce.idmagasin = p.p_idmag)
        GROUP BY dce.idunite, dce.idmagasin
      ),

      ech_out AS (
        SELECT dcs.idunite, dcs.idmagasin AS idmag, SUM(dcs.quantite_sortie) AS qt
        FROM tb_detailchange_sortie dcs, params p
        WHERE dcs.idarticle = p.p_idarticle
          AND (p.p_idmag IS NULL OR dcs.idmagasin = p.p_idmag)
        GROUP BY dcs.idunite, dcs.idmagasin
      ),

      -- ════════════════════════════════════════════════════════════════
      -- SOLDE EN UNITÉ DE BASE — on somme TOUS les mouvements de toutes
      -- les unités sources, convertis vers la base via coeff_vers_base
      -- ════════════════════════════════════════════════════════════════
      solde_base AS (
        SELECT
          SUM(
            (  COALESCE(r.qt,  0)
             + COALESCE(ti.qt, 0)
             + COALESCE(iv.qt, 0)
             + COALESCE(av.qt, 0)
             + COALESCE(ei.qt, 0)
             - COALESCE(ve.qt, 0)
             - COALESCE(so.qt, 0)
             - COALESCE(to_.qt, 0)
             - COALESCE(co.qt,  0)
             - COALESCE(eo.qt,  0)
            ) * uc.coeff_vers_base
          ) AS total_base
        FROM unite_coeff uc
        LEFT JOIN rec     r   ON r.idunite   = uc.idunite
        LEFT JOIN ven     ve  ON ve.idunite  = uc.idunite
        LEFT JOIN t_in    ti  ON ti.idunite  = uc.idunite
        LEFT JOIN t_out   to_ ON to_.idunite = uc.idunite
        LEFT JOIN sor     so  ON so.idunite  = uc.idunite
        LEFT JOIN inv     iv  ON iv.idunite  = uc.idunite
        LEFT JOIN avo     av  ON av.idunite  = uc.idunite
        LEFT JOIN conso   co  ON co.idunite  = uc.idunite
        LEFT JOIN ech_in  ei  ON ei.idunite  = uc.idunite
        LEFT JOIN ech_out eo  ON eo.idunite  = uc.idunite
      )

    -- ════════════════════════════════════════════════════════════════
    -- RÉSULTAT : stock réel dans l'unité cible (p_idunite)
    -- ════════════════════════════════════════════════════════════════
    SELECT
      GREATEST(0,
        COALESCE(sb.total_base, 0) / NULLIF(cc.coeff, 0)
      ) AS stock_reel
    FROM solde_base sb, coeff_cible cc
    """

    def calculer_stock_article(self, idarticle, idunite_cible, idmag=None):
        """
        Calcule le stock réel d'un article via la requête SQL consolidée.

        Paramètres
        ----------
        idarticle     : int  — identifiant de l'article
        idunite_cible : int  — identifiant de l'unité d'affichage souhaitée
        idmag         : int | None — magasin ciblé ; None = tous magasins confondus

        Retourne
        --------
        float — stock réel >= 0 dans l'unité cible
        """
        conn = self.connect_db()
        if not conn:
            return 0.0
        try:
            cursor = conn.cursor()
            cursor.execute(
                self._SQL_STOCK,
                {
                    'p_idarticle': idarticle,
                    'p_idunite':   idunite_cible,
                    'p_idmag':     idmag,          # NULL accepté → tous magasins
                }
            )
            row = cursor.fetchone()
            return float(row[0]) if row and row[0] is not None else 0.0
        except Exception as e:
            print(f"[PageInventaire] Erreur calcul stock (idarticle={idarticle}, "
                  f"idunite={idunite_cible}, idmag={idmag}) : {e}")
            return 0.0
        finally:
            cursor.close()
            conn.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Affichage des stocks
    # ─────────────────────────────────────────────────────────────────────────

    def _get_idarticle(self, cursor=None):
        """Retourne l'idarticle depuis article_data ou via requête DB."""
        idarticle = self.article_data.get("idarticle")
        if idarticle:
            return idarticle
        # Fallback : chercher via le code article
        conn_local = None
        try:
            if cursor is None:
                conn_local = self.connect_db()
                if not conn_local:
                    return None
                cur = conn_local.cursor()
            else:
                cur = cursor

            cur.execute(
                "SELECT idarticle FROM tb_unite WHERE codearticle = %s LIMIT 1",
                (self.article_data["code"],)
            )
            res = cur.fetchone()
            return res[0] if res else None
        finally:
            if conn_local:
                conn_local.close()

    def afficher_stock_actuel(self, magasin_nom=None):
        """Affiche le stock actuel du magasin sélectionné (colonne droite)."""
        if magasin_nom is None:
            magasin_nom = self.combo_magasin.get()

        idmag    = self.magasins_dict.get(magasin_nom)
        idunite  = self.get_selected_unite_id()
        idarticle = self._get_idarticle()

        if not idarticle or not idunite:
            self.label_stock_actuel.configure(text="Stock actuel : 0,00")
            return

        # Libellé de l'unité
        unite_label = self.combo_unite.get().strip()

        # ── Calcul via la requête consolidée ──────────────────────────────────
        stock = self.calculer_stock_article(idarticle, idunite, idmag)

        self.label_stock_actuel.configure(
            text=f"Stock Actuelle : {self.formater_nombre(stock)} {unite_label}".strip()
        )

    def refresh_stocks_overview(self):
        """Recharge la liste des stocks par magasin (colonne gauche)."""
        for child in self.stock_list.winfo_children():
            child.destroy()

        if not self.magasins_dict:
            return

        idunite   = self.get_selected_unite_id()
        idarticle = self._get_idarticle()

        if not idarticle or not idunite:
            self.label_stock_total.configure(text="Stock total : 0,00")
            return

        # ── Stock TOTAL (tous magasins, idmag=None) ────────────────────────────
        stock_total = self.calculer_stock_article(idarticle, idunite, None)
        self.label_stock_total.configure(
            text=f"Stock total : {self.formater_nombre(stock_total)}"
        )

        # ── Stock par magasin ──────────────────────────────────────────────────
        for nom_mag, idmag in self.magasins_dict.items():
            stock_mag = self.calculer_stock_article(idarticle, idunite, idmag)

            row = styled.frame(self.stock_list)
            row.pack(fill="x", padx=8, pady=4)

            styled.label(row, text=nom_mag, size=12).pack(side="left")

            if stock_mag > 0:
                variant = "info"
            elif stock_mag == 0:
                variant = "warning"
            else:
                variant = "danger"

            styled.badge(
                row,
                text=self.formater_nombre(stock_mag),
                variant=variant
            ).pack(side="right")

    # ─────────────────────────────────────────────────────────────────────────
    # Validation de l'inventaire (logique inchangée)
    # ─────────────────────────────────────────────────────────────────────────

    def _log_step(self, step, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[INVENTAIRE][{timestamp}][STEP {step}] {message}")

    def valider(self):
        self._log_step("01", "Début valider()")

        # ── Collecte des saisies ──────────────────────────────────────────────
        mag_nom        = self.combo_magasin.get()
        idmag          = self.magasins_dict.get(mag_nom)
        obs            = self.entry_obs.get()
        code_article   = self.article_data['code']
        designation    = self.article_data['designation']
        idunite_saisie = self.get_selected_unite_id()
        unite_label    = self.combo_unite.get().strip()

        rapport = []   # ← toutes les lignes du rapport affiché à la fin
        sep     = "─" * 52

        rapport.append("╔══════════════════════════════════════════════════╗")
        rapport.append("║       PIPELINE DE VALIDATION D'INVENTAIRE        ║")
        rapport.append("╚══════════════════════════════════════════════════╝")
        rapport.append("")
        rapport.append("▶ ÉTAPE 1 — SAISIE UTILISATEUR")
        rapport.append(sep)
        rapport.append(f"  Article     : {designation}")
        rapport.append(f"  Code        : {code_article}")
        rapport.append(f"  Magasin     : {mag_nom}  (idmag={idmag})")
        rapport.append(f"  Unité       : {unite_label}  (idunite={idunite_saisie})")
        rapport.append(f"  Observation : {obs}")
        rapport.append("")

        if not obs:
            messagebox.showwarning("Attention", "L'observation est obligatoire.")
            return

        conn = self.connect_db()
        if not conn:
            return

        try:
            nouveau = float(self.entry_qt.get().replace(',', '.'))
            cursor  = conn.cursor()
            rapport.append(f"  Quantité saisie : {nouveau} {unite_label}")
            rapport.append("")

            # ── ÉTAPE 2 : Résolution idarticle ────────────────────────────────
            rapport.append("▶ ÉTAPE 2 — RÉSOLUTION DE L'ARTICLE (DB)")
            rapport.append(sep)
            cursor.execute("""
                SELECT u.idarticle, u.idunite
                FROM tb_unite u
                INNER JOIN tb_article a ON a.idarticle = u.idarticle
                WHERE u.codearticle = %s AND a.deleted = 0 AND COALESCE(u.deleted, 0) = 0
                LIMIT 1
            """, (code_article,))
            res_article = cursor.fetchone()
            if not res_article:
                messagebox.showwarning("Attention", f"Code article introuvable : {code_article}")
                conn.close()
                return
            idarticle_saisi, idunite_saisie_db = res_article
            if idunite_saisie is None:
                idunite_saisie = idunite_saisie_db
            rapport.append(f"  SQL : SELECT idarticle, idunite FROM tb_unite")
            rapport.append(f"        WHERE codearticle = '{code_article}'")
            rapport.append(f"  → idarticle = {idarticle_saisi}")
            rapport.append(f"  → idunite   = {idunite_saisie}")
            rapport.append("")

            # ── ÉTAPE 3 : Hiérarchie des unités + coefficients ────────────────
            rapport.append("▶ ÉTAPE 3 — HIÉRARCHIE DES UNITÉS & COEFFICIENTS")
            rapport.append(sep)
            cursor.execute("""
                SELECT idunite, codearticle, COALESCE(qtunite, 1), COALESCE(niveau, 0),
                       COALESCE(designationunite, '')
                FROM tb_unite
                WHERE idarticle = %s AND COALESCE(deleted, 0) = 0
                ORDER BY COALESCE(niveau, 0) ASC, idunite ASC
            """, (idarticle_saisi,))
            unites_liees_full = cursor.fetchall()
            # On garde aussi la version sans designation pour la suite
            unites_liees = [(r[0], r[1], r[2], r[3]) for r in unites_liees_full]

            if not unites_liees:
                messagebox.showwarning("Attention", f"Aucune unité trouvée pour '{designation}'.")
                conn.close()
                return

            # Construction des coefficients cumulés
            coeffs_cumules = {}
            coeff_courant  = 1.0
            rapport.append(f"  {'Niveau':<8} {'Unité':<18} {'qtunite':<10} {'Coeff cumulé':<14}")
            rapport.append(f"  {'------':<8} {'-----':<18} {'-------':<10} {'------------':<14}")
            for idu, code_u, qt_u, niv, desig_u in unites_liees_full:
                qt_safe = qt_u if qt_u and qt_u > 0 else 1
                coeff_courant *= qt_safe
                coeffs_cumules[idu] = coeff_courant
                marker = " ◄ unité saisie" if idu == idunite_saisie else ""
                rapport.append(f"  {niv:<8} {desig_u or code_u:<18} {qt_safe:<10.4g} {coeff_courant:<14.4g}{marker}")

            coeff_unite_saisie = coeffs_cumules.get(idunite_saisie, 1.0)
            qte_unite_base     = nouveau * coeff_unite_saisie

            rapport.append("")
            rapport.append(f"  Conversion vers unité de BASE :")
            rapport.append(f"  {nouveau} × {coeff_unite_saisie} = {qte_unite_base} (unité base)")
            rapport.append("")

            # ── ÉTAPE 4 : Boucle par unité ────────────────────────────────────
            rapport.append("▶ ÉTAPE 4 — TRAITEMENT PAR UNITÉ (boucle DB)")
            rapport.append(sep)

            unites_mises_a_jour = []
            derniers_ids        = []

            for idx, (idu_lie, code_lie, qt_u_lie, niv_lie, desig_lie) in enumerate(unites_liees_full, 1):
                coeff_unite_liee = coeffs_cumules.get(idu_lie, 1.0)
                stock_cible      = qte_unite_base / coeff_unite_liee if coeff_unite_liee else 0.0
                stock_courant    = self.calculer_stock_article(idarticle_saisi, idu_lie, idmag)
                delta_inventaire = stock_cible - stock_courant

                rapport.append(f"  [{idx}] Unité : {desig_lie or code_lie}  (code={code_lie}, niveau={niv_lie})")
                rapport.append(f"      Coeff cumulé      = {coeff_unite_liee:.4g}")
                rapport.append(f"      Stock cible       = {qte_unite_base:.4g} ÷ {coeff_unite_liee:.4g} = {stock_cible:.4f}")
                rapport.append(f"      Stock actuel (DB) = {stock_courant:.4f}")
                rapport.append(f"      Delta             = {delta_inventaire:+.4f}")
                rapport.append("")

                # tb_stock
                cursor.execute(
                    "SELECT COALESCE(qtstock, 0) FROM tb_stock WHERE codearticle = %s AND idmag = %s",
                    (code_lie, idmag))
                res_old = cursor.fetchone()
                ancien_tb_stock = res_old[0] if res_old else None

                cursor.execute(
                    "UPDATE tb_stock SET qtstock = %s WHERE codearticle = %s AND idmag = %s",
                    (stock_cible, code_lie, idmag))

                if cursor.rowcount == 0:
                    cursor.execute(
                        "INSERT INTO tb_stock (codearticle, idmag, qtstock, qtalert, deleted) VALUES (%s,%s,%s,0,0)",
                        (code_lie, idmag, stock_cible))
                    action_tb_stock = f"INSERT qtstock={stock_cible:.4f}"
                else:
                    action_tb_stock = f"UPDATE qtstock: {ancien_tb_stock} → {stock_cible:.4f}"

                rapport.append(f"      ✏ tb_stock      : {action_tb_stock}")

                try:
                    cursor.execute("""
                        SELECT setval(pg_get_serial_sequence('tb_inventaire', 'id'),
                          COALESCE((SELECT MAX(id) FROM tb_inventaire), 0) + 1, false)
                    """)
                    obs_trim = obs[:50] if len(obs) > 50 else obs
                    cursor.execute("""
                        INSERT INTO tb_inventaire (codearticle, idmag, qtinventaire, iduser, observation, date)
                        VALUES (%s, %s, %s, %s, %s, NOW()) RETURNING id
                    """, (code_lie, idmag, delta_inventaire, self.iduser, obs_trim))

                    resultat = cursor.fetchone()
                    inv_id   = resultat[0] if resultat else "?"
                    derniers_ids.append(f"{code_lie}: ID {inv_id}")
                    rapport.append(f"      ✏ tb_inventaire : INSERT qtinventaire={delta_inventaire:+.4f}  → id={inv_id}")

                    cursor.execute("""
                        SELECT setval(pg_get_serial_sequence('tb_log_stock', 'id'),
                          COALESCE((SELECT MAX(id) FROM tb_log_stock), 0) + 1, false)
                    """)
                    type_action = f"INV AUTO ({designation}): {obs}"[:50]
                    cursor.execute("""
                        INSERT INTO tb_log_stock (codearticle, idmag, ancien_stock, nouveau_stock, iduser, type_action, date_action)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """, (code_lie, idmag, stock_courant, stock_cible, self.iduser, type_action))
                    rapport.append(f"      ✏ tb_log_stock  : INSERT ancien={stock_courant:.4f}  nouveau={stock_cible:.4f}")
                    rapport.append("")

                    unites_mises_a_jour.append(
                        f"{code_lie} : ancien={stock_courant:.2f}, cible={stock_cible:.2f}, delta={delta_inventaire:.2f}"
                    )

                except psycopg2.Error as e:
                    conn.rollback()
                    messagebox.showerror("Erreur SQL", f"Erreur lors de l'insertion : {e}")
                    return

            # ── COMMIT ────────────────────────────────────────────────────────
            conn.commit()
            self._log_step("20", "COMMIT effectué")
            try:
                details_parts = [
                    f"Article={designation} (code={code_article})",
                    f"Magasin={mag_nom} (idmag={idmag})",
                    f"Unité saisie={unite_label} (idunite={idunite_saisie})",
                    f"Qt saisie={nouveau}",
                    f"Obs={obs}",
                ]
                # On évite de dépasser : prendre seulement quelques lignes
                if unites_mises_a_jour:
                    details_parts.append("Maj unités: " + " | ".join(unites_mises_a_jour[:3]))
                    if len(unites_mises_a_jour) > 3:
                        details_parts.append(f"...(+{len(unites_mises_a_jour) - 3} autres)")

                self._logger.log(
                    action="Ajustement inventaire",
                    element=f"{designation} ({code_article})",
                    details="; ".join(details_parts),
                    value=f"idmag={idmag}, iduser={self.iduser}",
                )
            except Exception:
                pass

            rapport.append("▶ ÉTAPE 5 — COMMIT TRANSACTION")
            rapport.append(sep)
            rapport.append("  ✅ conn.commit() — toutes les écritures sont validées.")
            rapport.append("")
            rapport.append("▶ RÉCAPITULATIF FINAL")
            rapport.append(sep)
            rapport.append(f"  Article  : {designation}  (code={code_article})")
            rapport.append(f"  Magasin  : {mag_nom}")
            rapport.append(f"  Saisie   : {nouveau} {unite_label}")
            rapport.append(f"  Base     : {qte_unite_base} (unité de base)")
            rapport.append("")
            for ligne in unites_mises_a_jour:
                rapport.append(f"  • {ligne}")
            rapport.append("")
            rapport.append(f"  IDs tb_inventaire créés :")
            for id_ligne in derniers_ids:
                rapport.append(f"    → {id_ligne}")

            # ── Affichage messagebox ──────────────────────────────────────────
            # messagebox.showinfo(
            #     "✅ Pipeline de validation — Détail complet",
            #     "\n".join(rapport)
            # )

            if hasattr(self.master, 'charger_stocks'):
                self.master.charger_stocks()

            self.destroy()

        except ValueError:
            messagebox.showerror("Erreur", "Quantité saisie invalide.")
        except Exception as e:
            self._log_step("E2", traceback.format_exc())
            conn.rollback()
            messagebox.showerror("Erreur SQL", f"Détails : {str(e)}")
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass