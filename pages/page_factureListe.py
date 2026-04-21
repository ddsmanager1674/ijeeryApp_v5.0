# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           iJeery — pages/page_facture_liste.py                              ║
║           Liste des Factures / Crédits Clients                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  REFONTE UI — Mars 2026                                                      ║
║  Layout grid responsive — 3 rows :                                          ║
║    Row 0 — Bandeau filtres + recherche (BG_CARD, hauteur fixe)              ║
║    Row 1 — Treeview (weight=1, expansible)                                  ║
║    Row 2 — Barre totaux               (BG_CARD, hauteur fixe)               ║
║                                                                              ║
║  Polices  : Roboto 12px via Fonts.*                                         ║
║  Couleurs : Colors.*                                                        ║
║  TOUTE LA LOGIQUE MÉTIER EST STRICTEMENT INCHANGÉE                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import customtkinter as ctk
import psycopg2
from tkinter import messagebox, ttk
import json
import pandas as pd
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from tkcalendar import DateEntry
from resource_utils import get_config_path, safe_file_read

from app_theme import Colors, Fonts
from log_utils import AppLogger

# ── Import page paiement ──────────────────────────────────────────────────────
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

    def __init__(self, master):
        super().__init__(master, fg_color=Colors.BG_PAGE)
        self.grid(row=0, column=0, sticky="nsew")

        # ── Grid principale ───────────────────────────────────────────────────
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)   # seul le tableau s'étire

        # ── État ──────────────────────────────────────────────────────────────
        self.data_df            = pd.DataFrame()
        self.base_df            = pd.DataFrame()
        self._open_payment_lock = False
        self.filtre_actif       = False
        self.date_debut_filtre  = None
        self.date_fin_filtre    = None

        # ── Construction ──────────────────────────────────────────────────────
        self._build_filter_band()   # Row 0
        self._build_treeview()      # Row 1
        self._build_totals_band()   # Row 2

        self.session_data = getattr(master, "session_data", None) or {}
        self._logger = AppLogger(session_data=self.session_data)

        self.load_all_credit()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1 — CONSTRUCTION UI
    # ══════════════════════════════════════════════════════════════════════════

    def _build_filter_band(self):
        """Row 0 — Filtres de dates sur fond BG_CARD."""
        card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        card.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 2))
        # colonne élastique recherche
        card.grid_columnconfigure(4, weight=1)

        _lbl = dict(font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY)
        _ent = dict(
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            height=30, corner_radius=6, font=Fonts.input(11),
        )
        _de = dict(
            width=12, background=Colors.MIDNIGHT,
            foreground='white', borderwidth=1,
            date_pattern='dd/mm/yyyy', locale='fr_FR',
            font=('Roboto', 10),
        )

        # — Date Début —
        ctk.CTkLabel(card, text="Date Début", **_lbl).grid(
            row=0, column=0, padx=(12, 4), pady=8, sticky="w")
        self.date_debut = DateEntry(card, **_de)
        self.date_debut.set_date(datetime.now())
        self.date_debut.grid(row=0, column=1, padx=(0, 10), pady=8, sticky="w")

        # — Date Fin —
        ctk.CTkLabel(card, text="Date Fin", **_lbl).grid(
            row=0, column=2, padx=(0, 4), pady=8, sticky="w")
        self.date_fin = DateEntry(card, **_de)
        self.date_fin.set_date(datetime.now())
        self.date_fin.grid(row=0, column=3, padx=(0, 10), pady=8, sticky="w")

        # — Recherche dynamique (inline) —
        self.search_entry = ctk.CTkEntry(
            card,
            placeholder_text="🔍 Rechercher n'importe quel élément du tableau…",
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            height=30, corner_radius=6, font=Fonts.input(11),
        )
        self.search_entry.grid(row=0, column=4, padx=(0, 10), pady=8, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.search_credit)

        # — Boutons —
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
        """Row 2 — Treeview thème iJeery aligné sur page_articleMouvement."""
        container = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        container.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

        # ── Style TTK unique à cette page ────────────────────────────────────
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "FactListe.Treeview",
            background=Colors.BG_CARD,
            foreground=Colors.TEXT_PRIMARY,
            fieldbackground=Colors.BG_CARD,
            rowheight=22,
            borderwidth=0,
            font=('Roboto', 10),
        )
        style.configure(
            "FactListe.Treeview.Heading",
            background=Colors.BG_HEADER,
            foreground=Colors.TEXT_ON_DARK,
            font=('Roboto', 10, 'bold'),
            relief="flat",
            padding=(6, 4),
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

        # ── Tags de coloration ────────────────────────────────────────────────
        self.tree.tag_configure('impaye',         background='#FFBE76', foreground=Colors.TEXT_PRIMARY)
        self.tree.tag_configure('row_white',      background=Colors.BG_CARD,     foreground=Colors.TEXT_PRIMARY)
        self.tree.tag_configure('row_light_gray', background='#F0F4F8',          foreground=Colors.TEXT_PRIMARY)

        # ── Double-clic paiement ──────────────────────────────────────────────
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Return>", self.on_double_click)

        # ── En-têtes & colonnes ───────────────────────────────────────────────
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

        # ── Scrollbar ────────────────────────────────────────────────────────
        vsb = ctk.CTkScrollbar(container, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

    def _build_totals_band(self):
        """Row 3 — Barre de totaux sur fond BG_CARD."""
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
    # SECTION 2 — MISE À JOUR DES TOTAUX (helper)
    # ══════════════════════════════════════════════════════════════════════════

    def _update_totals(self, total_factures, total_paye, total_solde, count):
        """Met à jour les labels totaux — appelé par les 3 méthodes de chargement."""
        self.total_cmd_label.configure(
            text=f"Total Facture : {self.format_currency(total_factures)} Ar")
        self.total_paye_label.configure(
            text=f"Total Payé : {self.format_currency(total_paye)} Ar")
        self.total_solde_label.configure(
            text=f"Total Solde : {self.format_currency(total_solde)} Ar")
        self.count_label.configure(
            text=f"Factures : {count}")

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3 — LOGIQUE MÉTIER (STRICTEMENT INCHANGÉE)
    # ══════════════════════════════════════════════════════════════════════════

    def format_currency(self, value):
        """
        Formate un float en chaîne avec séparateur de milliers '.' et virgule décimale ','.
        Ex: 1234567.89 → 1.234.567,89
        Si le nombre est entier, affiche sans décimale.
        """
        try:
            from format_utils import format_nombre
            return format_nombre(value)
        except Exception:
            return "0,00"

    def on_double_click(self, event):
        """
        Gère le double-clic pour ouvrir PagePmtFacture.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
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
            "refvente":     row_data["N° Facture"],
            "date":         row_data["Date"],
            "description":  row_data["Description"],
            "client":       row_data["Client"],
            "montant_total": f"{solde:.2f}".replace('.', ','),
            "idcli":        row_data["ID Client"],
        }

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
        try:
            self._logger.log(
                action="Paiement facture (ouverture)",
                element=selected_refvente,
                details=f"Ouverture paiement facture ref: {selected_refvente}, client: {paiement_data.get('client')}, solde: {paiement_data.get('montant_total')} Ar",
                value=paiement_data.get("montant_total"),
            )
        except Exception:
            pass
        pay_win = PagePmtFacture(self.master, paiement_data)

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

    def connect_db(self):
        """Ouvre une connexion PostgreSQL depuis config.json."""
        try:
            with open(get_config_path('config.json')) as f:
                config    = json.load(f)
                db_config = config['database']
            return psycopg2.connect(
                host=db_config['host'], user=db_config['user'],
                password=db_config['password'], database=db_config['database'],
                port=db_config['port'],
            )
        except FileNotFoundError:
            messagebox.showerror("Erreur de configuration", "Fichier 'config.json' non trouvé.")
            return None
        except psycopg2.Error as e:
            messagebox.showerror("Erreur de Base de Données", f"Impossible de se connecter : {e}")
            return None

    # ── Requête SQL partagée (DRY) ────────────────────────────────────────────
    _SQL_BASE = """
        SELECT
            v.refvente,
            v.dateregistre,
            v.description,
            COALESCE(v.totmtvente, 0)        AS montant_total,
            v.statut,
            COALESCE((
                SELECT SUM(p.mtpaye)
                FROM tb_pmtfacture p
                WHERE p.refvente = v.refvente
            ), 0)                            AS total_paye,
            c.nomcli                         AS client_name,
            c.idclient,
            CONCAT(u.prenomuser,' ',u.nomuser) AS utilisateur,
            (SELECT COUNT(*) FROM tb_ventedetail vd WHERE vd.idvente = v.id) AS nb_lignes,
            (SELECT m.designationmag FROM tb_ventedetail vd
             INNER JOIN tb_magasin m ON vd.idmag = m.idmag
             WHERE vd.idvente = v.id LIMIT 1) AS premier_magasin
        FROM tb_vente v
        LEFT JOIN tb_users  u ON v.iduser   = u.iduser
        LEFT JOIN tb_client c ON v.idclient = c.idclient
        WHERE v.deleted = 0
    """

    def _remplir_tableau(self, resultats, date_format="%d/%m/%Y %H:%M:%S",
                         prefixe_mag="Magasin "):
        """
        Insère les résultats SQL dans le Treeview et reconstruit data_df.
        Logique de coloration et de construction description : inchangée.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
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
                "N° Facture":  refvente,
                "Date":        date,
                "Description": description,
                "Montant Total": montant_total,
                "Statut":      statut,
                "Total Payé":  paye,
                "Solde":       solde,
                "Client":      client,
                "ID Client":   idclient,
                "User":        user,
                "Qté Lignes":  nb_lignes,
            })
        self.base_df = pd.DataFrame(data_list)
        self.search_credit()

    def _render_table_from_df(self, df: pd.DataFrame):
        for item in self.tree.get_children():
            self.tree.delete(item)

        total_factures = 0.0
        total_paye_sum = 0.0
        total_solde_sum = 0.0

        for idx, (_, row) in enumerate(df.iterrows(), start=1):
            montant_total = float(row["Montant Total"] or 0)
            paye = float(row["Total Payé"] or 0)
            solde = float(row["Solde"] or 0)

            total_factures += montant_total
            total_paye_sum += paye
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

    # ── Filtre par date ───────────────────────────────────────────────────────

    def filter_by_date(self):
        """
        Filtre les factures par intervalle de dates.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        date_debut = self.date_debut.get_date()
        date_fin   = self.date_fin.get_date()

        if date_debut > date_fin:
            messagebox.showerror("Erreur", "La date de début doit être antérieure ou égale à la date de fin.")
            return

        self.filtre_actif      = True
        self.date_debut_filtre = date_debut
        self.date_fin_filtre   = date_fin

        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            query  = self._SQL_BASE + """
                AND v.dateregistre::DATE BETWEEN %s AND %s
                AND v.statut IN ('EN_ATTENTE', 'VALIDEE')
                ORDER BY v.dateregistre DESC, v.refvente DESC
            """
            cursor.execute(query, (date_debut, date_fin))
            self._remplir_tableau(cursor.fetchall(), prefixe_mag="")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du filtrage: {str(e)}")
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()

    def reset_date_filter(self):
        """
        Réinitialise le filtre de dates à aujourd'hui et recharge.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        self.filtre_actif      = False
        self.date_debut_filtre = None
        self.date_fin_filtre   = None
        self.date_debut.set_date(datetime.now())
        self.date_fin.set_date(datetime.now())
        self.load_all_credit()

    # ── Chargement du jour ────────────────────────────────────────────────────

    def load_all_credit(self):
        """
        Charge tous les crédits clients du jour.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            query  = self._SQL_BASE + """
                AND v.dateregistre::DATE = CURRENT_DATE
                AND v.statut IN ('EN_ATTENTE', 'VALIDEE')
                ORDER BY v.dateregistre DESC, v.refvente DESC
            """
            cursor.execute(query)
            self._remplir_tableau(cursor.fetchall(), prefixe_mag="Magasin ")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement: {str(e)}")
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()

    # ── Recherche ─────────────────────────────────────────────────────────────

    def search_credit(self, event=None):
        """
        Recherche dynamique sur toutes les colonnes visibles du tableau.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
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

    # ── Export Excel ──────────────────────────────────────────────────────────

    def export_to_excel(self):
        """
        Exporte les données courantes vers un fichier Excel sur le bureau.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
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
            try:
                from log_utils import AppLogger
                AppLogger(session_data=getattr(self, "session_data", {}) or {}).log(
                    action="Export Excel",
                    element="Client à Payer",
                    details=f"export factures clients, lignes={len(export_df)}, fichier={os.path.basename(filepath)}",
                    value=filepath,
                )
            except Exception:
                pass
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
