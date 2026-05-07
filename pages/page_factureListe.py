# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           iJeery — pages/page_facture_liste.py                              ║
║           Liste des Factures / Crédits Clients                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  REFONTE UI — Mars 2026                                                      ║
║  OPTIMISATION PERFORMANCE — Avril 2026                                       ║
║    • Sous-requêtes corrélées → JOIN agrégés (x3 → x0 sous-requêtes)        ║
║    • Pool de connexions psycopg2 (config.json lu une seule fois)            ║
║    • Chargement/filtrage asynchrone (thread séparé, UI non bloquée)         ║
║    • Suppression Treeview par détach groupé                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import customtkinter as ctk
import psycopg2
import psycopg2.pool
from tkinter import messagebox, ttk
import json
import pandas as pd
import os
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from tkcalendar import DateEntry
from resource_utils import get_config_path, safe_file_read

from app_theme import Colors, Fonts

try:
    from pages.page_pmtFacture import PagePmtFacture
except ImportError:
    class PagePmtFacture:
        def __init__(self, master, paiement_data: Dict[str, str]):
            messagebox.showerror(
                "Erreur",
                "Le fichier 'page_pmtFacture.py' est manquant ou contient une erreur. "
                "Impossible d'ouvrir la fenêtre de paiement.",
            )


# ══════════════════════════════════════════════════════════════════════════════

class PageFactureListe(ctk.CTkFrame):
    """
    Page liste des factures / crédits clients.

    Layout (grid responsive) :
    ┌─────────────────────────────────────────────────────────┐
    │ Row 0 — [Date Début] [Date Fin] [🔍 Recherche…] [Filtrer]│ BG_CARD
    │         [Réinitialiser]                                  │
    │ Row 1 — Treeview (expansible, style Mouvements)          │ BG_CARD
    │ Row 2 — Total Facture | Total Payé | Solde | Nb lignes   │ BG_CARD
    └─────────────────────────────────────────────────────────┘

    Double-clic sur une ligne → PagePmtFacture (logique inchangée).
    """

    # ── Pool de connexions partagé entre toutes les instances ─────────────────
    _pool: Optional[psycopg2.pool.SimpleConnectionPool] = None
    _db_config: Optional[Dict] = None   # config lue une seule fois

    def __init__(self, master, username=None, iduser=None):
        super().__init__(master, fg_color=Colors.BG_PAGE)
        self.grid(row=0, column=0, sticky="nsew")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Utilisateur connecté ─────────────────────────────────────────────
        # Remonte jusqu'à 4 niveaux de la hiérarchie master pour trouver
        # current_iduser / current_username définis sur App après le login.
        def _find_attr(*attr_names):
            src = master
            for _ in range(4):
                if src is None:
                    break
                for a in attr_names:
                    v = getattr(src, a, None)
                    if v:
                        return v
                src = getattr(src, "master", None) or getattr(src, "_master", None)
            return None

        self.current_username = (
            username
            or _find_attr('current_username', 'username')
        )
        self.current_iduser = (
            iduser
            or _find_attr('current_iduser', 'id_user_connecte', 'iduser')
        )
        print(f"[PageFactureListe] current_iduser={self.current_iduser!r}  current_username={self.current_username!r}")

        # ── État ──────────────────────────────────────────────────────────────
        self.data_df            = pd.DataFrame()
        self.base_df            = pd.DataFrame()
        self._open_payment_lock = False
        self.filtre_actif       = False
        self.date_debut_filtre  = None
        self.date_fin_filtre    = None
        self._loading           = False   # verrou pour éviter les requêtes simultanées

        # ── Construction ──────────────────────────────────────────────────────
        self._init_pool()
        self._build_filter_band()   # Row 0
        self._build_treeview()      # Row 1
        self._build_totals_band()   # Row 2

        self.load_all_credit()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 0 — POOL DE CONNEXIONS
    # ══════════════════════════════════════════════════════════════════════════

    def _init_pool(self):
        """Lit config.json une seule fois et initialise le pool."""
        if PageFactureListe._pool is not None:
            return
        try:
            with open(get_config_path('config.json')) as f:
                config = json.load(f)
                PageFactureListe._db_config = config['database']
            PageFactureListe._pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1, maxconn=5,
                host=self._db_config['host'],
                user=self._db_config['user'],
                password=self._db_config['password'],
                database=self._db_config['database'],
                port=self._db_config['port'],
            )
        except FileNotFoundError:
            messagebox.showerror("Erreur de configuration", "Fichier 'config.json' non trouvé.")
        except psycopg2.Error as e:
            messagebox.showerror("Erreur de Base de Données", f"Impossible de se connecter : {e}")

    def connect_db(self):
        """Récupère une connexion depuis le pool (compatibilité ascendante)."""
        if PageFactureListe._pool:
            try:
                return PageFactureListe._pool.getconn()
            except psycopg2.pool.PoolError:
                # Pool épuisé → connexion directe de secours
                try:
                    return psycopg2.connect(**self._db_config)
                except Exception as e:
                    messagebox.showerror("Erreur DB", str(e))
        return None

    def _release(self, conn):
        """Restitue la connexion au pool."""
        if conn and PageFactureListe._pool:
            try:
                PageFactureListe._pool.putconn(conn)
            except Exception:
                conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1 — CONSTRUCTION UI
    # ══════════════════════════════════════════════════════════════════════════

    def _build_filter_band(self):
        """Row 0 — Filtres de dates sur fond BG_CARD."""
        card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        card.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 2))
        card.grid_columnconfigure(4, weight=1)

        _lbl = dict(font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY)
        _de  = dict(
            width=12, background=Colors.MIDNIGHT,
            foreground='white', borderwidth=1,
            date_pattern='dd/mm/yyyy', locale='fr_FR',
            font=('Roboto', 10),
        )

        ctk.CTkLabel(card, text="Date Début", **_lbl).grid(
            row=0, column=0, padx=(12, 4), pady=8, sticky="w")
        self.date_debut = DateEntry(card, **_de)
        self.date_debut.set_date(datetime.now())
        self.date_debut.grid(row=0, column=1, padx=(0, 10), pady=8, sticky="w")

        ctk.CTkLabel(card, text="Date Fin", **_lbl).grid(
            row=0, column=2, padx=(0, 4), pady=8, sticky="w")
        self.date_fin = DateEntry(card, **_de)
        self.date_fin.set_date(datetime.now())
        self.date_fin.grid(row=0, column=3, padx=(0, 10), pady=8, sticky="w")

        self.search_entry = ctk.CTkEntry(
            card,
            placeholder_text="🔍 Rechercher n'importe quel élément du tableau…",
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            height=30, corner_radius=6, font=Fonts.input(11),
        )
        self.search_entry.grid(row=0, column=4, padx=(0, 10), pady=8, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.search_credit)

        self.btn_filtrer_date = ctk.CTkButton(
            card, text="🔎 Filtrer", height=30,
            font=Fonts.bold(11),
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            corner_radius=6, command=self.filter_by_date,
        )
        self.btn_filtrer_date.grid(row=0, column=5, padx=(0, 6), pady=8)

        self.btn_reset_date = ctk.CTkButton(
            card, text="↺ Réinitialiser", height=30,
            font=Fonts.bold(11),
            fg_color=Colors.TEXT_SECONDARY, hover_color=Colors.MIDNIGHT,
            corner_radius=6, command=self.reset_date_filter,
        )
        self.btn_reset_date.grid(row=0, column=6, padx=(0, 12), pady=8)

    def _build_treeview(self):
        """Row 1 — Treeview thème iJeery."""
        container = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        container.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "FactListe.Treeview",
            background=Colors.BG_CARD,
            foreground=Colors.TEXT_PRIMARY,
            fieldbackground=Colors.BG_CARD,
            rowheight=22, borderwidth=0,
            font=('Roboto', 10),
        )
        style.configure(
            "FactListe.Treeview.Heading",
            background=Colors.BG_HEADER,
            foreground=Colors.TEXT_ON_DARK,
            font=('Roboto', 10, 'bold'),
            relief="flat", padding=(6, 4),
        )
        style.map(
            "FactListe.Treeview",
            background=[("selected", Colors.PRIMARY)],
            foreground=[("selected", Colors.TEXT_ON_DARK)],
        )

        columns = ("N° Facture", "Date", "Description", "Montant Total",
                   "Client", "User", "Qté Lignes")
        self.tree = ttk.Treeview(
            container, columns=columns,
            show="headings", style="FactListe.Treeview",
        )

        self.tree.tag_configure('impaye',         background='#FFBE76', foreground=Colors.TEXT_PRIMARY)
        self.tree.tag_configure('row_white',      background=Colors.BG_CARD,  foreground=Colors.TEXT_PRIMARY)
        self.tree.tag_configure('row_light_gray', background='#F0F4F8',        foreground=Colors.TEXT_PRIMARY)

        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Return>",   self.on_double_click)

        col_cfg = {
            "N° Facture":   (130, "w"),
            "Date":         (155, "center"),
            "Description":  (190, "w"),
            "Montant Total":(120, "e"),
            "Client":       (160, "w"),
            "User":         (110, "w"),
            "Qté Lignes":   ( 70, "e"),
        }
        for col, (w, anchor) in col_cfg.items():
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, minwidth=50, anchor=anchor, stretch=True)

        vsb = ctk.CTkScrollbar(container, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

    def _build_totals_band(self):
        """Row 2 — Barre de totaux sur fond BG_CARD."""
        band = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        band.grid(row=2, column=0, sticky="ew", padx=0, pady=(2, 0))
        for col in range(4):
            band.grid_columnconfigure(col, weight=1)

        _kw = dict(font=Fonts.bold(12), anchor="w")

        self.total_cmd_label = ctk.CTkLabel(
            band, text="Total Facture : 0,00",
            text_color=Colors.TEXT_PRIMARY, **_kw)
        self.total_cmd_label.grid(row=0, column=0, padx=14, pady=8, sticky="w")

        self.total_paye_label = ctk.CTkLabel(
            band, text="Total Payé : 0,00",
            text_color=Colors.SUCCESS_DARK, **_kw)
        self.total_paye_label.grid(row=0, column=1, padx=4, pady=8, sticky="w")

        self.total_solde_label = ctk.CTkLabel(
            band, text="Total Solde : 0,00",
            text_color=Colors.WARNING, **_kw)
        self.total_solde_label.grid(row=0, column=2, padx=4, pady=8, sticky="w")

        self.count_label = ctk.CTkLabel(
            band, text="Factures : 0",
            text_color=Colors.TEXT_SECONDARY,
            font=Fonts.label(11), anchor="e")
        self.count_label.grid(row=0, column=3, padx=(4, 14), pady=8, sticky="e")

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — HELPERS UI
    # ══════════════════════════════════════════════════════════════════════════

    def _update_totals(self, total_factures, total_paye, total_solde, count):
        self.total_cmd_label.configure(
            text=f"Total Facture : {self.format_currency(total_factures)} Ar")
        self.total_paye_label.configure(
            text=f"Total Payé : {self.format_currency(total_paye)} Ar")
        self.total_solde_label.configure(
            text=f"Total Solde : {self.format_currency(total_solde)} Ar")
        self.count_label.configure(text=f"Factures : {count}")

    def _set_buttons_state(self, state: str):
        """Active ou désactive les boutons pendant un chargement."""
        self.btn_filtrer_date.configure(state=state)
        self.btn_reset_date.configure(state=state)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3 — LOGIQUE MÉTIER
    # ══════════════════════════════════════════════════════════════════════════

    def format_currency(self, value):
        try:
            from format_utils import format_nombre
            return format_nombre(value)
        except Exception:
            return "0,00"

    def on_double_click(self, event):
        """Gère le double-clic pour ouvrir PagePmtFacture."""
        if self._open_payment_lock:
            return
        self._open_payment_lock = True
        self.after(500, lambda: setattr(self, "_open_payment_lock", False))

        if PagePmtFacture is None:
            messagebox.showerror("Erreur", "La page de paiement PagePmtFacture n'a pas pu être chargée.")
            return

        selected_item = self.tree.focus()
        if not selected_item:
            return

        item_index = self.tree.index(selected_item)

        if item_index >= len(self.data_df) or self.data_df.empty:
            messagebox.showerror("Erreur", "Ligne de données non trouvée dans le DataFrame.")
            return

        row_data = self.data_df.iloc[item_index]
        solde    = row_data['Solde']
        statut   = row_data.get('Statut', 'EN_ATTENTE')

        if statut != 'EN_ATTENTE':
            messagebox.showinfo("Information", f"Cette facture n'est pas en attente (statut: {statut}).")
            return

        if solde <= 0.01:
            messagebox.showinfo("Information", "Cette Facture est déjà entièrement payée (Solde nul).")
            return

        paiement_data = {
            "refvente":      row_data["N° Facture"],
            "date":          row_data["Date"],
            "description":   row_data["Description"],
            "client":        row_data["Client"],
            "montant_total": f"{solde:.2f}".replace('.', ','),
            "idcli":         row_data["ID Client"],
        }

        # Récupérer l'iduser de la ligne (vendeur) OU celui de la session
        iduser_row = row_data.get("ID User") if "ID User" in row_data.index else None
        iduser_to_pass = self.current_iduser
        username_to_pass = self.current_username

        print(f"\n💰 CAISSE - Facture {paiement_data['refvente']}")
        print(f"  Montant Total Initial (tb_vente.totmtvente): {row_data['Montant Total']:.0f} Ar")
        print(f"  Montant Payé: {row_data['Total Payé']:.0f} Ar")
        print(f"  Solde (à payer): {solde:.0f} Ar")
        print(f"  → Valeur affichée en caisse: {paiement_data['montant_total']} Ar\n")

        if paiement_data['idcli'] is None:
            messagebox.showerror("Erreur", "ID du Client manquant. Impossible d'ouvrir la page de paiement.")
            return

        self.tree.item(selected_item, tags=())

        selected_refvente = str(paiement_data.get("refvente", "")).strip()
        pay_win = PagePmtFacture(self, paiement_data, iduser=iduser_to_pass, username=username_to_pass)

        def _after_payment_closed(event=None):
            if event is not None and event.widget is not pay_win:
                return
            should_restore_focus = bool(selected_refvente)
            try:
                self.reset_date_filter()
            except Exception:
                should_restore_focus = False

            if not should_restore_focus:
                return

            def _restore_focus():
                try:
                    for iid in self.tree.get_children():
                        vals = self.tree.item(iid, "values")
                        if vals and str(vals[0]).strip() == selected_refvente:
                            self.tree.selection_set(iid)
                            self.tree.focus(iid)
                            self.tree.see(iid)
                            break
                except Exception:
                    pass

            self.after(120, _restore_focus)

        try:
            pay_win.bind("<Destroy>", _after_payment_closed, add="+")
        except Exception:
            self.master.after(200, self.reload_data)

    def reload_data(self):
        """Recharge les données en respectant le filtre actif."""
        if self.filtre_actif and self.date_debut_filtre and self.date_fin_filtre:
            self.filter_by_date()
        else:
            self.load_all_credit()

    # ── Requête SQL optimisée (DRY) ───────────────────────────────────────────
    # AVANT : 3 sous-requêtes corrélées exécutées pour chaque ligne retournée.
    # APRÈS : 3 LEFT JOIN agrégés pré-calculés → 1 seule passe sur la BDD.
    _SQL_BASE = """
        SELECT
            v.refvente,
            v.dateregistre,
            v.description,
            COALESCE(v.totmtvente, 0)               AS montant_total,
            v.statut,
            COALESCE(pmt_agg.total_paye, 0)         AS total_paye,
            c.nomcli                                AS client_name,
            c.idclient,
            CONCAT(u.prenomuser, ' ', u.nomuser)    AS utilisateur,
            COALESCE(vd_agg.nb_lignes, 0)           AS nb_lignes,
            mag_agg.premier_magasin,
            v.iduser
        FROM tb_vente v
        LEFT JOIN tb_users  u ON v.iduser   = u.iduser
        LEFT JOIN tb_client c ON v.idclient = c.idclient
        -- Remplacement sous-requête corrélée SUM(tb_pmtfacture) → LEFT JOIN agrégé
        LEFT JOIN (
            SELECT refvente, SUM(mtpaye) AS total_paye
            FROM tb_pmtfacture
            GROUP BY refvente
        ) pmt_agg ON pmt_agg.refvente = v.refvente
        -- Remplacement sous-requête corrélée COUNT(tb_ventedetail) → LEFT JOIN agrégé
        LEFT JOIN (
            SELECT idvente, COUNT(*) AS nb_lignes
            FROM tb_ventedetail
            GROUP BY idvente
        ) vd_agg ON vd_agg.idvente = v.id
        -- Remplacement sous-requête corrélée premier magasin → LEFT JOIN DISTINCT ON
        LEFT JOIN (
            SELECT DISTINCT ON (vd.idvente) vd.idvente, m.designationmag AS premier_magasin
            FROM tb_ventedetail vd
            INNER JOIN tb_magasin m ON vd.idmag = m.idmag
            ORDER BY vd.idvente, vd.id
        ) mag_agg ON mag_agg.idvente = v.id
        WHERE v.deleted = 0
    """

    # ── Exécution SQL asynchrone ──────────────────────────────────────────────

    def _run_query_async(self, query: str, params=None, prefixe_mag: str = ""):
        """
        Lance la requête SQL dans un thread séparé.
        Met à jour l'UI via `self.after()` une fois les données reçues.
        """
        if self._loading:
            return
        self._loading = True
        self._set_buttons_state("disabled")
        self.count_label.configure(text="⏳ Chargement…")

        def _worker():
            conn = self.connect_db()
            rows = []
            error = None
            if conn:
                try:
                    cur = conn.cursor()
                    if params:
                        cur.execute(query, params)
                    else:
                        cur.execute(query)
                    rows = cur.fetchall()
                    cur.close()
                except Exception as e:
                    error = str(e)
                finally:
                    self._release(conn)
            # Retour sur le thread principal via after()
            self.after(0, lambda: self._on_query_done(rows, error, prefixe_mag))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_query_done(self, rows, error, prefixe_mag):
        """Rappel sur le thread UI après la requête asynchrone."""
        self._loading = False
        self._set_buttons_state("normal")
        if error:
            messagebox.showerror("Erreur", f"Erreur lors du chargement: {error}")
            self.count_label.configure(text="Factures : 0")
            return
        self._remplir_tableau(rows, prefixe_mag=prefixe_mag)

    # ── Filtre par date ───────────────────────────────────────────────────────

    def filter_by_date(self):
        """Filtre les factures par intervalle de dates."""
        date_debut = self.date_debut.get_date()
        date_fin   = self.date_fin.get_date()

        if date_debut > date_fin:
            messagebox.showerror("Erreur", "La date de début doit être antérieure ou égale à la date de fin.")
            return

        self.filtre_actif      = True
        self.date_debut_filtre = date_debut
        self.date_fin_filtre   = date_fin

        query = self._SQL_BASE + """
            AND v.dateregistre::DATE BETWEEN %s AND %s
            AND v.statut IN ('EN_ATTENTE', 'VALIDEE')
            ORDER BY v.dateregistre DESC, v.refvente DESC
        """
        self._run_query_async(query, params=(date_debut, date_fin), prefixe_mag="")

    def reset_date_filter(self):
        """Réinitialise le filtre de dates à aujourd'hui et recharge."""
        self.filtre_actif      = False
        self.date_debut_filtre = None
        self.date_fin_filtre   = None
        self.date_debut.set_date(datetime.now())
        self.date_fin.set_date(datetime.now())
        self.load_all_credit()

    def load_all_credit(self):
        """Charge tous les crédits clients du jour."""
        query = self._SQL_BASE + """
            AND v.dateregistre::DATE = CURRENT_DATE
            AND v.statut IN ('EN_ATTENTE', 'VALIDEE')
            ORDER BY v.dateregistre DESC, v.refvente DESC
        """
        self._run_query_async(query, params=None, prefixe_mag="Magasin ")

    # ── Recherche ─────────────────────────────────────────────────────────────

    def search_credit(self, event=None):
        """Recherche dynamique sur toutes les colonnes visibles du tableau."""
        if self.base_df is None or self.base_df.empty:
            self._render_table_from_df(pd.DataFrame(columns=[
                "N° Facture", "Date", "Description", "Montant Total", "Statut",
                "Total Payé", "Solde", "Client", "ID Client", "User", "Qté Lignes"
            ]))
            return

        filtre = (self.search_entry.get() or "").strip().lower()
        if not filtre:
            self._render_table_from_df(self.base_df.copy())
            return

        search_cols = ["N° Facture", "Date", "Description", "Client", "User", "Qté Lignes"]
        mask = self.base_df[search_cols].astype(str).apply(
            lambda col: col.str.lower().str.contains(filtre, na=False)
        ).any(axis=1)
        self._render_table_from_df(self.base_df[mask].copy())

    # ── Remplissage du tableau ────────────────────────────────────────────────

    def _remplir_tableau(self, resultats, date_format="%d/%m/%Y %H:%M:%S",
                         prefixe_mag="Magasin "):
        """Insère les résultats SQL dans le Treeview et reconstruit data_df."""
        data_list = []

        for row in resultats:
            refvente        = row[0]
            date            = row[1].strftime(date_format) if row[1] else ""
            description     = row[2] or ""
            montant_total   = float(row[3] or 0)
            statut          = row[4] or 'EN_ATTENTE'
            paye            = float(row[5] or 0)
            client          = row[6] or ""
            idclient        = row[7]
            user            = row[8] or ""
            nb_lignes       = row[9] or 0
            premier_magasin = row[10] or ""
            iduser_vente    = row[11] if len(row) > 11 else None

            if premier_magasin:
                description_avec_depot = f"{prefixe_mag}{premier_magasin}"
                if (description and description.strip()
                        and premier_magasin not in description):
                    description_clean = description.strip().strip('-').strip()
                    if description_clean:
                        description_avec_depot = f"{description_avec_depot} - {description_clean}"
                description = description_avec_depot

            solde = montant_total - paye
            data_list.append({
                "N° Facture":    refvente,
                "Date":          date,
                "Description":   description,
                "Montant Total": montant_total,
                "Statut":        statut,
                "Total Payé":    paye,
                "Solde":         solde,
                "Client":        client,
                "ID Client":     idclient,
                "User":          user,
                "ID User":       iduser_vente,
                "Qté Lignes":    nb_lignes,
            })

        self.base_df = pd.DataFrame(data_list)
        self.search_credit()

    def _render_table_from_df(self, df: pd.DataFrame):
        """Affiche le DataFrame dans le Treeview de façon optimisée."""
        # Suppression groupée : détacher tous les enfants en un seul appel
        children = self.tree.get_children()
        if children:
            self.tree.delete(*children)

        total_factures = 0.0
        total_paye_sum = 0.0
        total_solde_sum = 0.0

        for idx, (_, row) in enumerate(df.iterrows(), start=1):
            montant_total = float(row["Montant Total"] or 0)
            paye          = float(row["Total Payé"]    or 0)
            solde         = float(row["Solde"]         or 0)

            total_factures  += montant_total
            total_paye_sum  += paye
            total_solde_sum += solde

            tags = ['row_white' if idx % 2 == 1 else 'row_light_gray']
            if solde > 0.01:
                tags.append('impaye')

            self.tree.insert('', 'end', values=(
                row["N° Facture"], row["Date"], row["Description"],
                self.format_currency(montant_total),
                row["Client"], row["User"], row["Qté Lignes"],
            ), tags=tuple(tags))

        self.data_df = df.reset_index(drop=True)
        self._update_totals(total_factures, total_paye_sum, total_solde_sum, len(self.data_df))

    # ── Export Excel ──────────────────────────────────────────────────────────

    def export_to_excel(self):
        """Exporte les données courantes vers un fichier Excel sur le bureau."""
        if self.data_df.empty:
            messagebox.showwarning("Attention", "Aucune donnée à exporter.")
            return
        try:
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename     = f"Factures_Client_{timestamp}.xlsx"
            filepath     = os.path.join(desktop_path, filename)

            export_df = self.data_df[[
                "N° Facture", "Date", "Description", "Montant Total",
                "Total Payé", "Solde", "Client", "User", "Qté Lignes",
            ]].copy()
            export_df.to_excel(filepath, index=False, sheet_name="Factures")
            messagebox.showinfo("Succès", f"Export réussi vers :\n{filepath}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'export: {str(e)}")


# ══════════════════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE AUTONOME (test)
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = ctk.CTk()
    app.title("iJeery — Factures Clients (test)")
    app.geometry("1200x680")
    app.grid_columnconfigure(0, weight=1)
    app.grid_rowconfigure(0, weight=1)
    PageFactureListe(app)
    app.mainloop()
