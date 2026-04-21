# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           iJeery — pages/page_liste_mouvement.py                            ║
║           Liste des Mouvements d'Articles                                   ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ARCHITECTURE UI                                                            ║
║  ┌──────────────────────────────────────────────────────────────────────┐  ║
║  │ Row 0 — Bandeau titre MIDNIGHT (h=48)                                │  ║
║  ├────────────────┬─────────────────────────────────────────────────────┤  ║
║  │ Col 0          │ Col 1 (weight=1)                                    │  ║
║  │ Nav gauche     │ Row 0 — Barre recherche + Export                    │  ║
║  │ (5 boutons)    │ Row 1 — Treeview (weight=1)                         │  ║
║  │                │ Row 2 — Footer statistiques                         │  ║
║  └────────────────┴─────────────────────────────────────────────────────┘  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import customtkinter as ctk
from tkinter import messagebox, ttk, filedialog
import psycopg2
import json
import pandas as pd
import os
from datetime import datetime
from resource_utils import get_config_path, safe_file_read
from app_theme import Colors, Fonts

try:
    from EtatsPDF_Mouvements import EtatPDFMouvements
except ImportError:
    EtatPDFMouvements = None


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION DES TYPES DE MOUVEMENTS
# ══════════════════════════════════════════════════════════════════════════════

TYPES_MOUVEMENT = {
    "entree":      {"label": "📥  Entrées",              "icon": "📥"},
    "sortie":      {"label": "📤  Sorties",              "icon": "📤"},
    "transfert":   {"label": "🔄  Transferts",           "icon": "🔄"},
    "consommation":{"label": "⚙️   Consommation Interne", "icon": "⚙️"},
    "changement":  {"label": "🔁  Changement d'Article", "icon": "🔁"},
}


# ══════════════════════════════════════════════════════════════════════════════
# PAGE PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════

class PageListeMouvement(ctk.CTkFrame):
    """
    Page de consultation des listes de mouvements d'articles.
    Thème iJeery — cohérent avec page_facture_liste.py, page_sortie.py, etc.
    """

    def __init__(self, master, iduser=None):
        super().__init__(master, fg_color=Colors.BG_PAGE)

        self.iduser                = iduser
        self.type_mouvement_actif  = "entree"
        self.data_df               = pd.DataFrame()
        self._nav_buttons          = {}   # {key: CTkButton}

        # Grille principale : row 0 bandeau titre, row 1 corps
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_title_band()
        self._build_body()

        # Chargement initial
        self._select_type("entree")

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1 — CONSTRUCTION UI
    # ══════════════════════════════════════════════════════════════════════════

    def _build_title_band(self):
        """Bandeau titre MIDNIGHT pleine largeur (row 0)."""
        band = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT, corner_radius=0, height=48)
        band.grid(row=0, column=0, sticky="ew")
        band.grid_propagate(False)
        band.grid_columnconfigure(1, weight=1)

        # Icône + Titre dynamique
        ctk.CTkLabel(
            band,
            text="📋",
            font=Fonts.heading(18),
            text_color=Colors.TEXT_ON_DARK,
        ).grid(row=0, column=0, padx=(16, 6), pady=12)

        self.lbl_titre = ctk.CTkLabel(
            band,
            text="Listes des Mouvements — Entrées",
            font=Fonts.heading(15),
            text_color=Colors.TEXT_ON_DARK,
            anchor="w",
        )
        self.lbl_titre.grid(row=0, column=1, sticky="w")

    def _build_body(self):
        """Corps principal : nav gauche + contenu droit (row 1)."""
        body = ctk.CTkFrame(self, fg_color=Colors.BG_PAGE, corner_radius=0)
        body.grid(row=1, column=0, sticky="nsew", padx=12, pady=12)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        self._build_nav(body)       # Col 0
        self._build_content(body)   # Col 1

    def _build_nav(self, parent):
        """
        Panneau de navigation gauche — 5 boutons types de mouvements.
        Style : fond BG_CARD, bouton actif SUCCESS_DARK, inactif MIDNIGHT.
        """
        nav = ctk.CTkFrame(
            parent,
            fg_color=Colors.BG_CARD,
            corner_radius=10,
            border_width=1,
            border_color=Colors.BORDER,
            width=190,
        )
        nav.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        nav.grid_propagate(False)
        nav.grid_columnconfigure(0, weight=1)

        # Titre de la nav
        ctk.CTkLabel(
            nav,
            text="Types de Mouvements",
            font=Fonts.bold(11),
            text_color=Colors.TEXT_SECONDARY,
            anchor="center",
        ).grid(row=0, column=0, padx=10, pady=(14, 6), sticky="ew")

        # Séparateur
        ctk.CTkFrame(nav, fg_color=Colors.BORDER, height=1, corner_radius=0).grid(
            row=1, column=0, sticky="ew", padx=10, pady=(0, 8))

        # Boutons
        for idx, (key, info) in enumerate(TYPES_MOUVEMENT.items()):
            btn = ctk.CTkButton(
                nav,
                text=info["label"],
                font=Fonts.bold(11),
                fg_color=Colors.MIDNIGHT,
                hover_color=Colors.MIDNIGHT_LIGHT,
                text_color=Colors.TEXT_ON_DARK,
                anchor="w",
                corner_radius=8,
                height=40,
                command=lambda k=key: self._select_type(k),
            )
            btn.grid(row=idx + 2, column=0, padx=10, pady=3, sticky="ew")
            self._nav_buttons[key] = btn

        # Remplissage vertical
        nav.grid_rowconfigure(len(TYPES_MOUVEMENT) + 2, weight=1)

    def _build_content(self, parent):
        """Zone de contenu droite : barre de recherche + treeview + footer."""
        content = ctk.CTkFrame(parent, fg_color=Colors.BG_PAGE, corner_radius=0)
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_rowconfigure(1, weight=1)
        content.grid_columnconfigure(0, weight=1)

        # ── Barre recherche + export ──────────────────────────────────────────
        self._build_search_bar(content)   # row 0

        # ── Treeview ──────────────────────────────────────────────────────────
        self._build_treeview(content)     # row 1

        # ── Footer statistiques ───────────────────────────────────────────────
        self._build_footer(content)       # row 2

    def _build_search_bar(self, parent):
        """Barre horizontale : recherche + boutons Chercher / Réinitialiser / Export."""
        bar = ctk.CTkFrame(
            parent,
            fg_color=Colors.BG_CARD,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER,
            height=52,
        )
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        bar.grid_propagate(False)
        bar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            bar,
            text="🔍",
            font=Fonts.body(13),
            text_color=Colors.TEXT_SECONDARY,
        ).grid(row=0, column=0, padx=(12, 4), pady=10)

        self.search_entry = ctk.CTkEntry(
            bar,
            placeholder_text="Rechercher…",
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            height=30,
            corner_radius=8,
            font=Fonts.input(12),
        )
        self.search_entry.grid(row=0, column=1, padx=(0, 8), pady=10, sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda e: self.search_data())

        # Bouton Chercher
        ctk.CTkButton(
            bar,
            text="Chercher",
            font=Fonts.button(11),
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            height=30, corner_radius=8, width=90,
            command=self.search_data,
        ).grid(row=0, column=2, padx=(0, 6), pady=10)

        # Bouton Réinitialiser
        ctk.CTkButton(
            bar,
            text="↺  Tout",
            font=Fonts.button(11),
            fg_color=Colors.MIDNIGHT_LIGHT,
            hover_color=Colors.MIDNIGHT,
            text_color=Colors.TEXT_ON_DARK,
            height=30, corner_radius=8, width=80,
            command=self.reset_search,
        ).grid(row=0, column=3, padx=(0, 6), pady=10)

        # Bouton Export Excel
        ctk.CTkButton(
            bar,
            text="📊  Excel",
            font=Fonts.button(11),
            fg_color=Colors.SUCCESS_DARK,
            hover_color=Colors.SUCCESS,
            height=30, corner_radius=8, width=90,
            command=self.export_to_excel,
        ).grid(row=0, column=4, padx=(0, 12), pady=10)

    def _build_treeview(self, parent):
        """Treeview avec style thème iJeery (en-têtes MIDNIGHT, lignes alternées)."""
        tree_card = ctk.CTkFrame(
            parent,
            fg_color=Colors.BG_CARD,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER,
        )
        tree_card.grid(row=1, column=0, sticky="nsew")
        tree_card.grid_rowconfigure(0, weight=1)
        tree_card.grid_columnconfigure(0, weight=1)

        # Style Treeview isolé "Mouvement.Treeview"
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Mouvement.Treeview",
            background=Colors.BG_CARD,
            foreground=Colors.TEXT_PRIMARY,
            fieldbackground=Colors.BG_CARD,
            rowheight=24,
            font=("Roboto", 10),
            borderwidth=0,
        )
        style.configure(
            "Mouvement.Treeview.Heading",
            background=Colors.BG_HEADER,
            foreground=Colors.TEXT_ON_DARK,
            font=("Roboto", 10, "bold"),
            relief="flat",
            padding=(6, 6),
        )
        style.map(
            "Mouvement.Treeview",
            background=[("selected", Colors.PRIMARY_LIGHT)],
            foreground=[("selected", Colors.TEXT_PRIMARY)],
        )
        style.map(
            "Mouvement.Treeview.Heading",
            background=[("active", Colors.MIDNIGHT_LIGHT)],
        )

        # Treeview
        cols_default = ("Date", "Référence", "Fournisseur", "Articles",
                        "Montant Total", "Statut", "Description", "Utilisateur")
        self.tree = ttk.Treeview(
            tree_card,
            columns=cols_default,
            show="headings",
            style="Mouvement.Treeview",
        )
        self.tree.tag_configure("row_white", background=Colors.BG_CARD,
                                foreground=Colors.TEXT_PRIMARY)
        self.tree.tag_configure("row_alt",   background=Colors.BG_ROW_ALT,
                                foreground=Colors.TEXT_PRIMARY)

        for col in cols_default:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="center")

        # Scrollbars via CTkScrollbar (thème cohérent)
        sb_y = ctk.CTkScrollbar(tree_card, command=self.tree.yview)
        sb_x = ctk.CTkScrollbar(tree_card, orientation="horizontal",
                                 command=self.tree.xview)
        self.tree.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        sb_y.grid(row=0, column=1, sticky="ns")
        sb_x.grid(row=1, column=0, sticky="ew")

        # Double-clic → détails
        self.tree.bind("<Double-1>", lambda e: self.on_row_double_click())

    def _build_footer(self, parent):
        """Footer statistiques (row 2)."""
        footer = ctk.CTkFrame(
            parent,
            fg_color=Colors.BG_CARD,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER,
            height=38,
        )
        footer.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        footer.grid_propagate(False)
        footer.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            footer,
            text="📊  Statistiques :",
            font=Fonts.bold(11),
            text_color=Colors.TEXT_SECONDARY,
        ).grid(row=0, column=0, padx=(12, 6), pady=8)

        self.stats_label = ctk.CTkLabel(
            footer,
            text="Total : 0 ligne",
            font=Fonts.body(11),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
        )
        self.stats_label.grid(row=0, column=1, sticky="w", pady=8)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — NAVIGATION & CHARGEMENT
    # ══════════════════════════════════════════════════════════════════════════

    def _select_type(self, key: str):
        """
        Active un type de mouvement :
          - Met à jour l'état visuel des boutons nav
          - Met à jour le titre
          - Recharge les données
        """
        self.type_mouvement_actif = key

        # Mettre à jour les boutons
        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.configure(fg_color=Colors.SUCCESS_DARK, hover_color=Colors.SUCCESS)
            else:
                btn.configure(fg_color=Colors.MIDNIGHT, hover_color=Colors.MIDNIGHT_LIGHT)

        # Mettre à jour le titre
        icons = {
            "entree": "Entrées d'Articles",
            "sortie": "Sorties d'Articles",
            "transfert": "Transferts d'Articles",
            "consommation": "Consommation Interne",
            "changement": "Changement d'Articles",
        }
        self.lbl_titre.configure(
            text=f"Listes des Mouvements — {icons.get(key, key)}"
        )

        # Réinitialiser la recherche et recharger
        self.search_entry.delete(0, "end")
        self.load_mouvement_data(key)

    # Alias de compatibilité
    def on_mouvement_button_click(self, type_mouvement):
        self._select_type(type_mouvement)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3 — BASE DE DONNÉES
    # ══════════════════════════════════════════════════════════════════════════

    def connect_db(self):
        """Ouvre une connexion PostgreSQL depuis config.json."""
        try:
            with open(get_config_path('config.json')) as f:
                config = json.load(f)
                db_config = config['database']
            return psycopg2.connect(**db_config)
        except Exception as e:
            messagebox.showerror("Erreur de connexion",
                                 f"Impossible de se connecter à la BDD: {e}")
            return None

    def load_mouvement_data(self, type_mouvement: str):
        """Charge les données du type de mouvement dans le treeview."""
        conn = self.connect_db()
        if not conn:
            return
        try:
            query = self.get_query_for_mouvement(type_mouvement)
            if query:
                self.data_df = pd.read_sql(query, conn)
                self.display_data_in_tree(self.data_df)
                self.update_statistics()
            else:
                self.clear_tree()
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur chargement données: {e}")
        finally:
            conn.close()

    def get_query_for_mouvement(self, type_mouvement: str):
        """Retourne la requête SQL selon le type de mouvement."""
        queries = {
            # ──────────────────────────────────────────────────────────────────
            # ENTRÉES — colonne "Description" = tb_livraisonfrs.factfrs
            # ──────────────────────────────────────────────────────────────────
            "entree": """
                SELECT
                    c.datecom::DATE as "Date",
                    c.refcom as "Référence",
                    COALESCE(
                        STRING_AGG(DISTINCT fcd.nomfrs, ', ')
                            FILTER (WHERE fcd.nomfrs IS NOT NULL AND fcd.nomfrs <> ''),
                        f.nomfrs,
                        'N/A'
                    ) as "Fournisseur",
                    COUNT(DISTINCT cd.idarticle) as "Articles",
                    CASE
                        WHEN COALESCE(SUM(CAST(cd.total AS NUMERIC)), 0) = 0 THEN '-'
                        ELSE CAST(COALESCE(SUM(CAST(cd.total AS NUMERIC)), 0) AS TEXT)
                    END as "Montant Total",
                    CASE
                        WHEN EXISTS (
                            SELECT 1 FROM tb_livraisonfrs lf
                            WHERE lf.idcom = c.idcom AND lf.deleted = 0
                        ) THEN '✅✅ Livrée & Reçue'
                        WHEN (
                            SELECT COUNT(*) FROM tb_commandedetail
                            WHERE idcom = c.idcom AND COALESCE(qtlivre, 0) > 0
                        ) = (
                            SELECT COUNT(*) FROM tb_commandedetail
                            WHERE idcom = c.idcom
                        ) AND (
                            SELECT COUNT(*) FROM tb_commandedetail
                            WHERE idcom = c.idcom
                        ) > 0 THEN '✅ Livré Complet'
                        WHEN EXISTS (
                            SELECT 1 FROM tb_commandedetail
                            WHERE idcom = c.idcom AND COALESCE(qtlivre, 0) > 0
                        ) THEN '⚠️ Livré Partiel'
                        ELSE '⏳ En Attente'
                    END as "Statut",
                    COALESCE(
                        (
                            SELECT lf.factfrs
                            FROM tb_livraisonfrs lf
                            WHERE lf.idcom = c.idcom
                              AND lf.deleted = 0
                              AND lf.factfrs IS NOT NULL
                              AND lf.factfrs <> ''
                            ORDER BY lf.idcom
                            LIMIT 1
                        ),
                        'N/A'
                    ) as "Description",
                    CONCAT(COALESCE(u.prenomuser,''), ' ', COALESCE(u.nomuser,'')) as "Utilisateur"
                FROM tb_commande c
                LEFT JOIN tb_fournisseur f ON c.idfrs = f.idfrs
                LEFT JOIN tb_commandedetail cd ON c.idcom = cd.idcom
                LEFT JOIN tb_fournisseur fcd ON cd.idfrs = fcd.idfrs
                LEFT JOIN tb_users u ON c.iduser = u.iduser
                WHERE c.deleted = 0
                GROUP BY c.idcom, c.datecom, c.refcom, f.nomfrs, u.prenomuser, u.nomuser
                ORDER BY c.datecom DESC
            """,
            "sortie": """
                SELECT
                    s.dateregistre::DATE as "Date",
                    s.refsortie as "Référence",
                    COUNT(DISTINCT sd.idarticle) as "Nombre d'articles",
                    COALESCE(
                        STRING_AGG(DISTINCT sd.motif, ', ')
                            FILTER (WHERE sd.motif IS NOT NULL AND sd.motif <> ''),
                        s.description,
                        'N/A'
                    ) as "Description",
                    CONCAT(COALESCE(u.prenomuser,''), ' ', COALESCE(u.nomuser,'')) as "Utilisateur"
                FROM tb_sortie s
                LEFT JOIN tb_sortiedetail sd ON s.id = sd.idsortie
                LEFT JOIN tb_users u ON s.iduser = u.iduser
                WHERE s.deleted = 0
                GROUP BY s.id, s.dateregistre, s.refsortie, s.description, u.prenomuser, u.nomuser
                ORDER BY s.dateregistre DESC
            """,
            "transfert": """
                SELECT
                    t.dateregistre::DATE as "Date",
                    t.reftransfert as "Référence",
                    COUNT(DISTINCT td.idarticle) as "Nombre d'articles",
                    COALESCE(
                        STRING_AGG(DISTINCT td.description, ', ')
                            FILTER (WHERE td.description IS NOT NULL AND td.description <> ''),
                        t.description,
                        'N/A'
                    ) as "Description",
                    CONCAT(COALESCE(u.prenomuser,''), ' ', COALESCE(u.nomuser,'')) as "Utilisateur"
                FROM tb_transfert t
                LEFT JOIN tb_transfertdetail td ON t.idtransfert = td.idtransfert
                LEFT JOIN tb_users u ON t.iduser = u.iduser
                WHERE t.deleted = 0
                GROUP BY t.idtransfert, t.dateregistre, t.reftransfert, t.description,
                         u.prenomuser, u.nomuser
                ORDER BY t.dateregistre DESC
            """,
            "consommation": """
                SELECT
                    ci.dateregistre::DATE as "Date",
                    ci.refconsommation as "Référence",
                    COUNT(DISTINCT cid.idarticle) as "Nombre d'articles",
                    COALESCE(
                        STRING_AGG(DISTINCT cid.observation, ', ')
                            FILTER (WHERE cid.observation IS NOT NULL AND cid.observation <> ''),
                        ci.observation,
                        'N/A'
                    ) as "Description",
                    COALESCE(SUM(CAST(cid.montant_total AS NUMERIC)), 0) as "Montant Total",
                    CONCAT(COALESCE(u.prenomuser,''), ' ', COALESCE(u.nomuser,'')) as "Utilisateur"
                FROM tb_consommationinterne ci
                LEFT JOIN tb_consommationinterne_details cid ON ci.id = cid.idconsommation
                LEFT JOIN tb_users u ON ci.iduser = u.iduser
                GROUP BY ci.id, ci.dateregistre, ci.refconsommation, ci.observation,
                         u.prenomuser, u.nomuser
                ORDER BY ci.dateregistre DESC
            """,
            "changement": """
                SELECT
                    ch.datechg::DATE as "Date",
                    ch.refchg as "Référence",
                    COALESCE(ch.note, 'N/A') as "Description",
                    CONCAT(COALESCE(u.prenomuser,''), ' ', COALESCE(u.nomuser,'')) as "Utilisateur"
                FROM tb_changement ch
                LEFT JOIN tb_users u ON ch.iduser = u.iduser
                ORDER BY ch.datechg DESC
            """,
        }
        return queries.get(type_mouvement)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 4 — AFFICHAGE TREEVIEW
    # ══════════════════════════════════════════════════════════════════════════

    def display_data_in_tree(self, df: pd.DataFrame):
        """Reconfigure les colonnes et remplit le treeview depuis un DataFrame."""
        self.clear_tree()

        if df is None or df.empty:
            return

        cols = list(df.columns)
        self.tree.configure(columns=cols)

        for col in cols:
            self.tree.heading(col, text=col)
            # Largeur adaptée par type de colonne
            if col in ("Montant Total", "Articles", "Nombre d'articles"):
                self.tree.column(col, width=110, anchor="e",   minwidth=80)
            elif col in ("Date", "Statut"):
                self.tree.column(col, width=105, anchor="center", minwidth=80)
            elif col == "Référence":
                self.tree.column(col, width=130, anchor="center", minwidth=90)
            elif col == "Utilisateur":
                self.tree.column(col, width=140, anchor="w",   minwidth=100)
            elif col == "Description":
                self.tree.column(col, width=180, anchor="w",   minwidth=120)
            else:
                self.tree.column(col, width=150, anchor="w",   minwidth=100)

        for idx, row in df.iterrows():
            tag = "row_white" if idx % 2 == 0 else "row_alt"
            self.tree.insert("", "end", values=tuple(row), tags=(tag,))

    def clear_tree(self):
        """Vide le treeview."""
        for item in self.tree.get_children():
            self.tree.delete(item)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 5 — RECHERCHE & STATISTIQUES
    # ══════════════════════════════════════════════════════════════════════════

    def search_data(self):
        """Filtre le DataFrame sur tous les champs selon le texte de recherche."""
        term = self.search_entry.get().strip().lower()
        if not term:
            self.display_data_in_tree(self.data_df)
            self.update_statistics()
            return

        filtered = self.data_df[
            self.data_df.astype(str)
                        .apply(lambda x: x.str.contains(term, case=False, na=False))
                        .any(axis=1)
        ]
        self.display_data_in_tree(filtered)
        self.update_statistics(filtered)

    def reset_search(self):
        """Réinitialise la recherche."""
        self.search_entry.delete(0, "end")
        self.load_mouvement_data(self.type_mouvement_actif)

    def update_statistics(self, df: pd.DataFrame = None):
        """Met à jour le label de statistiques dans le footer."""
        if df is None:
            df = self.data_df

        if df is None or df.empty:
            self.stats_label.configure(text="Total : 0 ligne")
            return

        n = len(df)

        # Montant total si disponible
        if "Montant Total" in df.columns:
            try:
                total = pd.to_numeric(df["Montant Total"], errors="coerce").sum()
                self.stats_label.configure(
                    text=f"Total : {n} ligne(s)   |   Montant total : {total:,.0f} Ar"
                )
                return
            except Exception:
                pass

        self.stats_label.configure(text=f"Total : {n} ligne(s)")

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 6 — EXPORT EXCEL
    # ══════════════════════════════════════════════════════════════════════════

    def export_to_excel(self):
        """Exporte les données affichées vers un fichier Excel sur le Bureau."""
        if self.data_df is None or self.data_df.empty:
            messagebox.showwarning("Export", "Aucune donnée à exporter.")
            return
        try:
            ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"mouvements_{self.type_mouvement_actif}_{ts}.xlsx"
            desktop  = os.path.join(os.path.expanduser("~"), "Desktop")
            path     = os.path.join(desktop if os.path.isdir(desktop) else ".", filename)

            self.data_df.to_excel(path, index=False, sheet_name="Mouvements")
            messagebox.showinfo("Export Excel", f"Fichier exporté :\n{path}")
            try:
                from log_utils import AppLogger
                AppLogger(session_data=getattr(self, "session_data", {}) or {}).log(
                    action="Export Excel",
                    element="Liste Mouvements",
                    details=f"export mouvements '{self.type_mouvement_actif}', lignes={len(self.data_df)}, fichier={os.path.basename(path)}",
                    value=path,
                )
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Erreur Export", f"Erreur lors de l'export : {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 7 — DOUBLE-CLIC ET FENÊTRE DÉTAILS
    # ══════════════════════════════════════════════════════════════════════════

    def on_row_double_click(self):
        """Ouvre la fenêtre de détails pour la ligne sélectionnée."""
        selection = self.tree.selection()
        if not selection:
            return
        values = self.tree.item(selection[0]).get("values", [])
        ref = self._extract_ref(values)
        if not ref:
            return
        try:
            dispatch = {
                "entree":       self.show_commande_details_by_ref,
                "sortie":       self.show_sortie_details_by_ref,
                "transfert":    self.show_transfert_details_by_ref,
                "consommation": self.show_consommation_details_by_ref,
                "changement":   self.show_changement_details_by_ref,
            }
            dispatch[self.type_mouvement_actif](ref)
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'ouvrir les détails : {e}")

    def _extract_ref(self, values) -> str | None:
        """Extrait la valeur de la colonne 'Référence' depuis les values d'une ligne."""
        try:
            cols = list(self.tree["columns"])
            if "Référence" in cols:
                idx = cols.index("Référence")
                if idx < len(values):
                    return str(values[idx])
        except Exception:
            pass
        return str(values[1]) if len(values) >= 2 else None

    def _open_details_window(self, title: str, columns: tuple,
                             rows: list, reference: str = None,
                             type_mouvement: str = None,
                             show_print_button: bool = True):
        """
        Ouvre une fenêtre modale avec un treeview des détails.
        Boutons : Imprimer PDF (si disponible) + Fermer.
        """
        win = ctk.CTkToplevel(self)
        win.title(title)
        win.geometry("960x520")
        win.grab_set()

        # Bandeau titre
        band = ctk.CTkFrame(win, fg_color=Colors.MIDNIGHT, corner_radius=0, height=44)
        band.pack(fill="x")
        band.pack_propagate(False)
        ctk.CTkLabel(
            band,
            text=f"  🔍  {title}",
            font=Fonts.heading(13),
            text_color=Colors.TEXT_ON_DARK,
            anchor="w",
        ).pack(side="left", padx=12, pady=10)

        # Corps
        body = ctk.CTkFrame(win, fg_color=Colors.BG_PAGE, corner_radius=0)
        body.pack(fill="both", expand=True, padx=10, pady=(10, 0))
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        # Card treeview
        card = ctk.CTkFrame(body, fg_color=Colors.BG_CARD, corner_radius=8,
                            border_width=1, border_color=Colors.BORDER)
        card.grid(row=0, column=0, sticky="nsew")
        card.grid_rowconfigure(0, weight=1)
        card.grid_columnconfigure(0, weight=1)

        tree = ttk.Treeview(card, columns=columns, show="headings",
                            style="Mouvement.Treeview")
        tree.tag_configure("row_white", background=Colors.BG_CARD,
                           foreground=Colors.TEXT_PRIMARY)
        tree.tag_configure("row_alt",   background=Colors.BG_ROW_ALT,
                           foreground=Colors.TEXT_PRIMARY)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=130, anchor="w")

        sb_y = ctk.CTkScrollbar(card, command=tree.yview)
        sb_x = ctk.CTkScrollbar(card, orientation="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)

        tree.grid(row=0, column=0, sticky="nsew")
        sb_y.grid(row=0, column=1, sticky="ns")
        sb_x.grid(row=1, column=0, sticky="ew")

        for idx, r in enumerate(rows):
            tag = "row_white" if idx % 2 == 0 else "row_alt"
            tree.insert("", "end", values=r, tags=(tag,))

        # Barre d'actions
        actions = ctk.CTkFrame(win, fg_color=Colors.BG_CARD, corner_radius=0, height=52)
        actions.pack(fill="x", padx=10, pady=10)
        actions.pack_propagate(False)

        ctk.CTkButton(
            actions,
            text="✖  Fermer",
            font=Fonts.button(11),
            fg_color=Colors.MIDNIGHT_LIGHT,
            hover_color=Colors.MIDNIGHT,
            text_color=Colors.TEXT_ON_DARK,
            height=32, corner_radius=8, width=100,
            command=win.destroy,
        ).pack(side="right", padx=(6, 12), pady=10)

        if reference and type_mouvement and EtatPDFMouvements and show_print_button:
            ctk.CTkButton(
                actions,
                text="🖨  Imprimer PDF",
                font=Fonts.button(11),
                fg_color=Colors.PREMIUM,
                hover_color=Colors.PREMIUM_DARK,
                height=32, corner_radius=8, width=130,
                command=lambda: self._imprimer_pdf(reference, type_mouvement),
            ).pack(side="right", padx=6, pady=10)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 8 — MÉTHODES DÉTAILS PAR TYPE
    # ══════════════════════════════════════════════════════════════════════════

    def show_commande_details_by_ref(self, refcom):
        if not refcom:
            return
        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute("SELECT idcom FROM tb_commande WHERE refcom = %s LIMIT 1", (refcom,))
            row = cur.fetchone()
            if not row:
                messagebox.showinfo("Info", "Commande introuvable.")
                return
            idcom = row[0]
            statut = self._get_entree_status_for_idcom(cur, idcom)
            cur.execute("""
                SELECT
                    COALESCE(fr.nomfrs, f.nomfrs, 'N/A') as "Fournisseur",
                    COALESCE(u.codearticle, '') as "Code Article",
                    a.designation                as "Désignation",
                    u.designationunite           as "Unité",
                    cd.qtcmd                     as "Qté commandée",
                    COALESCE(cd.qtlivre, 0)      as "Qté livrée",
                    CASE
                        WHEN COALESCE(CAST(cd.total AS NUMERIC), 0) = 0 THEN '-'
                        ELSE CAST(cd.total AS TEXT)
                    END as "Montant"
                FROM tb_commandedetail cd
                LEFT JOIN tb_commande c ON cd.idcom = c.idcom
                LEFT JOIN tb_article a ON cd.idarticle = a.idarticle
                LEFT JOIN tb_unite   u ON cd.idunite   = u.idunite
                LEFT JOIN tb_fournisseur fr ON cd.idfrs = fr.idfrs
                LEFT JOIN tb_fournisseur f ON c.idfrs = f.idfrs
                WHERE cd.idcom = %s
                ORDER BY a.designation
            """, (idcom,))
            details = cur.fetchall()
            cols = ("Fournisseur", "Code Article", "Désignation", "Unité",
                    "Qté commandée", "Qté livrée", "Montant")
            self._open_details_window(
                f"Détails Entrée — {refcom}", cols, details, refcom, "entree",
                show_print_button=self._is_print_allowed_for_entree(statut))
        finally:
            conn.close()

    def _get_entree_status_for_idcom(self, cur, idcom: int) -> str:
        """Retourne le statut d'une commande d'entrée, aligné avec la liste principale."""
        cur.execute("""
            SELECT
                CASE
                    WHEN EXISTS (
                        SELECT 1 FROM tb_livraisonfrs lf
                        WHERE lf.idcom = c.idcom AND lf.deleted = 0
                    ) THEN '✅✅ Livrée & Reçue'
                    WHEN (
                        SELECT COUNT(*) FROM tb_commandedetail
                        WHERE idcom = c.idcom AND COALESCE(qtlivre, 0) > 0
                    ) = (
                        SELECT COUNT(*) FROM tb_commandedetail
                        WHERE idcom = c.idcom
                    ) AND (
                        SELECT COUNT(*) FROM tb_commandedetail
                        WHERE idcom = c.idcom
                    ) > 0 THEN '✅ Livré Complet'
                    WHEN EXISTS (
                        SELECT 1 FROM tb_commandedetail
                        WHERE idcom = c.idcom AND COALESCE(qtlivre, 0) > 0
                    ) THEN '⚠️ Livré Partiel'
                    ELSE '⏳ En Attente'
                END as statut
            FROM tb_commande c
            WHERE c.idcom = %s
            LIMIT 1
        """, (idcom,))
        row = cur.fetchone()
        return row[0] if row else ""

    def _is_print_allowed_for_entree(self, statut: str) -> bool:
        """Autorise l'impression uniquement pour 'Livrée & Reçue' ou 'Livré Partiel'."""
        s = (statut or "").strip().lower()
        return ("livrée" in s and "reçue" in s) or ("livre" in s and "recu" in s) or ("livré partiel" in s) or ("livre partiel" in s)

    def show_sortie_details_by_ref(self, refsortie):
        if not refsortie:
            return
        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM tb_sortie WHERE refsortie = %s LIMIT 1",
                        (refsortie,))
            row = cur.fetchone()
            if not row:
                messagebox.showinfo("Info", "Sortie introuvable.")
                return
            idsortie = row[0]
            cur.execute("""
                SELECT
                    COALESCE(u.codearticle, '') as "Code Article",
                    a.designation              as "Désignation",
                    u.designationunite         as "Unité",
                    sd.qtsortie                as "Quantité sortie",
                    COALESCE(sd.motif, 'N/A')  as "Motif"
                FROM tb_sortiedetail sd
                LEFT JOIN tb_article a ON sd.idarticle = a.idarticle
                LEFT JOIN tb_unite   u ON sd.idunite   = u.idunite
                WHERE sd.idsortie = %s
                ORDER BY a.designation
            """, (idsortie,))
            details = cur.fetchall()
            cols = ("Code Article", "Désignation", "Unité", "Quantité sortie", "Motif")
            self._open_details_window(
                f"Détails Sortie — {refsortie}", cols, details, refsortie, "sortie")
        finally:
            conn.close()

    def show_transfert_details_by_ref(self, reftrans):
        if not reftrans:
            return
        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT idtransfert FROM tb_transfert WHERE reftransfert = %s LIMIT 1",
                (reftrans,))
            row = cur.fetchone()
            if not row:
                messagebox.showinfo("Info", "Transfert introuvable.")
                return
            idtr = row[0]
            cur.execute("""
                SELECT
                    a.designation      as "Désignation",
                    u.designationunite as "Unité",
                    td.qttransfert     as "Quantité",
                    COALESCE(td.description, 'N/A') as "Description",
                    td.idmagsortie     as "Magasin Sortie",
                    td.idmagentree     as "Magasin Entrée"
                FROM tb_transfertdetail td
                LEFT JOIN tb_article a ON td.idarticle = a.idarticle
                LEFT JOIN tb_unite   u ON td.idunite   = u.idunite
                WHERE td.idtransfert = %s
                ORDER BY a.designation
            """, (idtr,))
            details = cur.fetchall()
            cols = ("Désignation", "Unité", "Quantité", "Description",
                    "Magasin Sortie", "Magasin Entrée")
            self._open_details_window(
                f"Détails Transfert — {reftrans}", cols, details, reftrans, "transfert")
        finally:
            conn.close()

    def show_consommation_details_by_ref(self, refcons):
        if not refcons:
            return
        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM tb_consommationinterne WHERE refconsommation = %s LIMIT 1",
                (refcons,))
            row = cur.fetchone()
            if not row:
                messagebox.showinfo("Info", "Consommation introuvable.")
                return
            idc = row[0]
            cur.execute("""
                SELECT
                    COALESCE(u.codearticle, '') as "Code Article",
                    a.designation              as "Désignation",
                    u.designationunite         as "Unité",
                    d.qtconsomme               as "Quantité",
                    d.prixunit                 as "Prix Unitaire",
                    d.montant_total            as "Montant",
                    COALESCE(d.observation, 'N/A') as "Observation"
                FROM tb_consommationinterne_details d
                LEFT JOIN tb_article a ON d.idarticle = a.idarticle
                LEFT JOIN tb_unite   u ON d.idunite   = u.idunite
                WHERE d.idconsommation = %s
                ORDER BY a.designation
            """, (idc,))
            details = cur.fetchall()
            cols = ("Code Article", "Désignation", "Unité",
                    "Quantité", "Prix Unitaire", "Montant", "Observation")
            self._open_details_window(
                f"Détails Consommation — {refcons}", cols, details,
                refcons, "consommation")
        finally:
            conn.close()

    def show_changement_details_by_ref(self, refchg):
        if not refchg:
            return
        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT idchg FROM tb_changement WHERE refchg = %s LIMIT 1", (refchg,))
            row = cur.fetchone()
            if not row:
                messagebox.showinfo("Info", "Changement introuvable.")
                return
            idchg = row[0]

            details = []

            # Articles SORTANTS
            cur.execute("""
                SELECT
                    COALESCE(u.codearticle, '-')  as "Code Article",
                    COALESCE(a.designation, '-')  as "Désignation",
                    COALESCE(u.designationunite,'-') as "Unité",
                    ds.quantite_sortie            as "Qté Sortie",
                    '-'                           as "Qté Entrée"
                FROM tb_detailchange_sortie ds
                LEFT JOIN tb_article a ON ds.idarticle = a.idarticle
                LEFT JOIN tb_unite   u ON ds.idunite   = u.idunite
                WHERE ds.idchg = %s
                ORDER BY a.designation
            """, (idchg,))
            details.extend(cur.fetchall())

            # Articles ENTRANTS (non déjà présents en sortie)
            cur.execute("""
                SELECT
                    COALESCE(u.codearticle, '-')  as "Code Article",
                    COALESCE(a.designation, '-')  as "Désignation",
                    COALESCE(u.designationunite,'-') as "Unité",
                    '-'                           as "Qté Sortie",
                    de.quantite_entree            as "Qté Entrée"
                FROM tb_detailchange_entree de
                LEFT JOIN tb_article a ON de.idarticle = a.idarticle
                LEFT JOIN tb_unite   u ON de.idunite   = u.idunite
                WHERE de.idchg = %s
                  AND (de.idarticle, de.idunite) NOT IN (
                      SELECT ds.idarticle, ds.idunite
                      FROM tb_detailchange_sortie ds
                      WHERE ds.idchg = %s
                  )
                ORDER BY a.designation
            """, (idchg, idchg))
            details.extend(cur.fetchall())

            cols = ("Code Article", "Désignation", "Unité", "Qté Sortie", "Qté Entrée")
            self._open_details_window(
                f"Détails Changement — {refchg}", cols, details, refchg, "changement")
        finally:
            conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 9 — IMPRESSION PDF
    # ══════════════════════════════════════════════════════════════════════════

    def _imprimer_pdf(self, reference: str, type_mouvement: str):
        """Génère un PDF via EtatPDFMouvements et propose la sauvegarde."""
        if not EtatPDFMouvements:
            messagebox.showerror("Erreur",
                                 "Module EtatsPDF_Mouvements introuvable.")
            return
        try:
            path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF", "*.pdf"), ("Tous", "*.*")],
                initialfile=f"Bon_{type_mouvement}_{reference}.pdf",
            )
            if not path:
                return
            gen = EtatPDFMouvements()
            ok  = gen.generer_etat(type_mouvement, reference, path)
            gen.close_db()
            if ok:
                messagebox.showinfo("PDF", f"PDF généré :\n{path}")
            else:
                messagebox.showerror("Erreur",
                                     f"Échec génération PDF pour {reference}")
        except Exception as e:
            messagebox.showerror("Erreur PDF", f"Erreur : {e}")