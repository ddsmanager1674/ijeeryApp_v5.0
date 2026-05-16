# -*- coding: utf-8 -*-
"""
iJeery — pages/page_entree.py
Bon d'Entrée (BE) : entrée directe en magasin.

Objectif : opération inverse de la sortie (BS) :
- Ajoute au stock (pas de contrôle "stock insuffisant")
- UI et thème identiques à la refonte de page_sortie.py (Mars 2026)
"""

import customtkinter as ctk
from tkinter import messagebox, ttk, simpledialog
import psycopg2
import json
from datetime import datetime
from typing import Optional, Dict, Any
import traceback
import os
import sys
import subprocess

from settings_utils import open_file_if_enabled
from resource_utils import get_config_path, get_session_path
from app_theme import Colors, Fonts, styled
from date_picker_utils import get_date_from_widget, set_date_on_widget
from log_utils import AppLogger

from db import ensure_connection, get_connection
from stock_service import get_snapshot
from stock_snapshot import format_nombre_auto


ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


class PageEntree(ctk.CTkFrame):
    """
    Page de gestion des entrées directes en stock (Bon d'Entrée).

    Layout (proche de PageSortie refondue) :
    Row 0 — Bandeau info (Bon d'Entrée)
    Row 1 — Réf | Date | Magasin | 📂 Charger
    Row 2 — Motif / description
    Row 3 — Saisie article (Article | 🔎 | Qté | Unité | ➕ | ✖)
    Row 4 — Tableau Treeview (expansible)
    Row 5 — Actions (Nouveau | 🖨 | 🗑 | 💾)
    """

    def __init__(self, master, iduser: int, db_conn=None, **kwargs):
        super().__init__(master, fg_color=Colors.BG_PAGE, **kwargs)

        self.id_user_connecte = iduser
        self._db_conn_initial = db_conn
        self.session_data = getattr(master, "session_data", None) or {"user_id": self.id_user_connecte}
        self._logger = AppLogger(session_data=self.session_data, fallback_user_id=self.id_user_connecte)

        self.conn: Optional[psycopg2.extensions.connection] = None
        self.article_selectionne = None
        self.detail_entree: list = []
        self.index_ligne_selectionnee = None
        self.magasins_map: dict = {}
        self.infos_societe: Dict[str, Any] = {}
        self.derniere_identree_enregistree: Optional[int] = None

        self.mode_modification = False
        self.identree_charge = None

        self.tree_details = None
        self.scrollbar_details = None

        self.grid_columnconfigure(0, weight=1)
        for row, w in enumerate([0, 0, 0, 1, 0]):
            self.grid_rowconfigure(row, weight=w)

        self._setup_ui()
        self.generer_reference()
        self.charger_magasins()
        self.charger_infos_societe()
        self.conn = self.connect_db()

    # ══════════════════════════════════════════════════════════════════════════
    # DB
    # ══════════════════════════════════════════════════════════════════════════

    def connect_db(self):
        try:
            conn = self._db_conn_initial or get_connection()
            return ensure_connection(conn)
        except Exception as e:
            messagebox.showerror("Erreur BD", str(e))
            return None

    # ══════════════════════════════════════════════════════════════════════════
    # UI
    # ══════════════════════════════════════════════════════════════════════════

    def _setup_ui(self):
        self._build_header_band()   # Row 0
        self._build_motif_band()    # Row 1
        self._build_article_band()  # Row 2
        self._build_tree_zone()     # Row 3
        self._build_actions_band()  # Row 4

    def _build_header_band(self):
        card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        card.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 2))
        for col in range(5):
            card.grid_columnconfigure(col, weight=1)

        lbl_kw = dict(font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY, anchor="w")
        entry_kw = dict(
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            height=32,
            corner_radius=6,
            font=Fonts.input(12),
        )
        entry_kw_no_font = {k: v for k, v in entry_kw.items() if k != 'font'}

        ctk.CTkLabel(card, text="Référence", **lbl_kw).grid(row=0, column=0, padx=(10, 2), pady=(8, 0), sticky="w")
        self.entry_ref_entree = ctk.CTkEntry(
            card, **entry_kw_no_font, font=Fonts.bold(12), state="readonly",
        )
        self.entry_ref_entree.grid(row=1, column=0, padx=(10, 4), pady=(0, 8), sticky="ew")

        ctk.CTkLabel(card, text="Date Entrée", **lbl_kw).grid(row=0, column=1, padx=4, pady=(8, 0), sticky="w")
        self.entry_date_entree = styled.date_entry(card, width=11)
        self.entry_date_entree.grid(row=1, column=1, padx=4, pady=(0, 8), sticky="ew")

        ctk.CTkLabel(card, text="Magasin", **lbl_kw).grid(row=0, column=2, padx=4, pady=(8, 0), sticky="w")
        self.combo_magasin = ctk.CTkComboBox(
            card,
            values=["Chargement…"],
            height=32,
            font=Fonts.input(12),
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            button_color=Colors.PRIMARY,
            dropdown_fg_color=Colors.BG_CARD,
        )
        self.combo_magasin.grid(row=1, column=2, padx=4, pady=(0, 8), sticky="ew")

        card.grid_columnconfigure(3, weight=2)

        ctk.CTkLabel(card, text=" ", **lbl_kw).grid(row=0, column=4, padx=(4, 10), pady=(8, 0))
        self.btn_charger_be = ctk.CTkButton(
            card,
            text="📂 Charger Opération",
            height=32,
            font=Fonts.bold(11),
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            corner_radius=6,
            command=self.ouvrir_recherche_entree,
        )
        self.btn_charger_be.grid(row=1, column=4, padx=(4, 10), pady=(0, 8), sticky="ew")

    def _build_motif_band(self):
        card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        card.grid(row=1, column=0, sticky="ew", padx=0, pady=(0, 2))
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card, text="Motif",
            font=Fonts.label(11),
            text_color=Colors.TEXT_SECONDARY,
        ).grid(row=0, column=0, padx=(10, 6), pady=8, sticky="w")

        self.entry_motif = ctk.CTkEntry(
            card,
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            height=32,
            corner_radius=6,
            font=Fonts.input(12),
            placeholder_text="Motif / description de l'entrée…",
        )
        self.entry_motif.grid(row=0, column=1, padx=(0, 10), pady=8, sticky="ew")

    def _build_article_band(self):
        card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        card.grid(row=2, column=0, sticky="ew", padx=0, pady=(0, 2))
        for col in range(6):
            card.grid_columnconfigure(col, weight=1)

        lbl_kw = dict(font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY, anchor="w")
        entry_kw = dict(
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            height=32,
            corner_radius=6,
            font=Fonts.input(12),
        )

        ctk.CTkLabel(card, text="Article", **lbl_kw).grid(row=0, column=0, padx=(10, 2), pady=(8, 0), sticky="w")
        self.entry_article = ctk.CTkEntry(
            card, **entry_kw, placeholder_text="Sélectionner un article…", state="readonly",
        )
        self.entry_article.grid(row=1, column=0, padx=(10, 4), pady=(0, 8), sticky="ew")

        ctk.CTkLabel(card, text=" ", **lbl_kw).grid(row=0, column=1, padx=4, pady=(8, 0))
        self.btn_recherche_article = ctk.CTkButton(
            card,
            text="🔎 Rechercher",
            height=32,
            font=Fonts.bold(11),
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            corner_radius=6,
            command=self.open_recherche_article,
        )
        self.btn_recherche_article.grid(row=1, column=1, padx=4, pady=(0, 8), sticky="ew")

        ctk.CTkLabel(card, text="Quantité", **lbl_kw).grid(row=0, column=2, padx=4, pady=(8, 0), sticky="w")
        self.entry_qtentree = ctk.CTkEntry(card, **entry_kw, width=100)
        self.entry_qtentree.grid(row=1, column=2, padx=4, pady=(0, 8), sticky="ew")

        ctk.CTkLabel(card, text="Unité", **lbl_kw).grid(row=0, column=3, padx=4, pady=(8, 0), sticky="w")
        self.entry_unite = ctk.CTkEntry(card, **entry_kw, width=100, state="readonly")
        self.entry_unite.grid(row=1, column=3, padx=4, pady=(0, 8), sticky="ew")

        ctk.CTkLabel(card, text=" ", **lbl_kw).grid(row=0, column=4, padx=4, pady=(8, 0))
        self.btn_ajouter = ctk.CTkButton(
            card,
            text="+ Ajouter",
            height=32,
            font=Fonts.bold(12),
            fg_color=Colors.SUCCESS_DARK,
            hover_color=Colors.INFO_DARK,
            corner_radius=6,
            command=self.valider_detail,
        )
        self.btn_ajouter.grid(row=1, column=4, padx=4, pady=(0, 8), sticky="ew")

        self.btn_annuler_mod = ctk.CTkButton(
            card,
            text="✖ Annuler Modif",
            height=32,
            font=Fonts.bold(11),
            fg_color=Colors.DANGER,
            hover_color=Colors.DANGER_DARK,
            corner_radius=6,
            command=self.reset_detail_form,
            state="disabled",
        )
        self.btn_annuler_mod.grid(row=1, column=5, padx=(4, 10), pady=(0, 8), sticky="ew")

    def _build_tree_zone(self):
        self.tree_container = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        self.tree_container.grid(row=3, column=0, sticky="nsew", padx=0, pady=(0, 2))
        self.tree_container.grid_columnconfigure(0, weight=1)
        self.tree_container.grid_rowconfigure(0, weight=1)

        self._create_treeview()

    def _create_treeview(self):
        if self.tree_details is not None:
            self.tree_details.destroy()
        if self.scrollbar_details is not None:
            self.scrollbar_details.destroy()

        colonnes = (
            "ID_Article", "ID_Unite", "ID_Magasin",
            "Code Article", "Désignation", "Magasin",
            "Unité", "Quantité", "Motif",
        )

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Entree.Treeview",
            rowheight=22,
            font=('Segoe UI', 9),
            background=Colors.BG_CARD,
            foreground=Colors.TEXT_PRIMARY,
            fieldbackground=Colors.BG_CARD,
            borderwidth=0,
        )
        style.configure(
            "Entree.Treeview.Heading",
            background=Colors.BG_HEADER,
            foreground=Colors.TEXT_ON_DARK,
            font=('Segoe UI', 9, 'bold'),
            relief="flat",
        )
        style.map(
            "Entree.Treeview",
            background=[("selected", Colors.PRIMARY)],
            foreground=[("selected", Colors.TEXT_ON_DARK)],
        )

        self.tree_details = ttk.Treeview(
            self.tree_container,
            columns=colonnes,
            show='headings',
            style="Entree.Treeview",
        )
        self.tree_details.tag_configure("even", background=Colors.BG_CARD)
        self.tree_details.tag_configure("odd", background=Colors.BG_ROW_ALT)

        for col in colonnes:
            self.tree_details.heading(col, text=col.replace('_', ' '))
            if "ID" in col:
                self.tree_details.column(col, width=0, stretch=False)
            elif col == "Quantité":
                self.tree_details.column(col, width=130, anchor='e')
            elif col == "Désignation":
                self.tree_details.column(col, width=300, anchor='w')
            elif col == "Motif":
                self.tree_details.column(col, width=220, anchor='w')
            else:
                self.tree_details.column(col, width=120, anchor='w')

        self.scrollbar_details = ctk.CTkScrollbar(
            self.tree_container, command=self.tree_details.yview,
        )
        self.tree_details.configure(yscrollcommand=self.scrollbar_details.set)

        self.tree_details.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        self.scrollbar_details.grid(row=0, column=1, sticky="ns", padx=(0, 6), pady=6)
        self.tree_details.bind('<Double-1>', self.modifier_detail)

        self.charger_details_treeview()

    def _build_actions_band(self):
        bar = ctk.CTkFrame(self, fg_color=Colors.BG_PAGE, corner_radius=0)
        bar.grid(row=4, column=0, sticky="ew", padx=0, pady=(2, 0))
        bar.grid_columnconfigure(3, weight=1)

        btn_nouveau = ctk.CTkButton(
            bar,
            text="📄 Nouveau BE",
            height=34,
            font=Fonts.bold(11),
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            corner_radius=6,
            command=self.nouveau_bon_entree,
        )
        btn_nouveau.grid(row=0, column=0, padx=(8, 4), pady=6)

        self.btn_imprimer = ctk.CTkButton(
            bar,
            text="🖨 Imprimer état",
            height=34,
            font=Fonts.bold(11),
            fg_color=Colors.PREMIUM,
            hover_color=Colors.PREMIUM_DARK,
            corner_radius=6,
            command=self.open_impression_dialogue,
            state="disabled",
        )
        self.btn_imprimer.grid(row=0, column=1, padx=4, pady=6)
        self.btn_imprimer.grid_remove()

        self.btn_supprimer_ligne = ctk.CTkButton(
            bar,
            text="🗑 Supprimer Ligne",
            height=34,
            font=Fonts.bold(11),
            fg_color=Colors.DANGER,
            hover_color=Colors.DANGER_DARK,
            corner_radius=6,
            command=self.supprimer_detail,
        )
        self.btn_supprimer_ligne.grid(row=0, column=2, padx=4, pady=6)

        self.btn_enregistrer = ctk.CTkButton(
            bar,
            text="💾 Enregistrer l'Entrée",
            height=34,
            font=Fonts.bold(13),
            fg_color=Colors.SUCCESS_DARK,
            hover_color=Colors.INFO_DARK,
            corner_radius=8,
            command=self.enregistrer_entree,
        )
        self.btn_enregistrer.grid(row=0, column=4, padx=(4, 8), pady=6, sticky="e")

    # ══════════════════════════════════════════════════════════════════════════
    # Utilitaires nombre
    # ══════════════════════════════════════════════════════════════════════════

    def formater_nombre(self, nombre) -> str:
        try:
            return (
                "{:,.2f}".format(float(nombre))
                .replace(',', '_T_').replace('.', ',').replace('_T_', '.')
            )
        except Exception:
            return "0,00"

    def parser_nombre(self, texte) -> float:
        try:
            return float(str(texte).replace('.', '').replace(',', '.'))
        except Exception:
            return 0.0

    # ══════════════════════════════════════════════════════════════════════════
    # Chargements initiaux
    # ══════════════════════════════════════════════════════════════════════════

    def generer_reference(self):
        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            annee = datetime.now().year
            prefix = "BE"
            cursor.execute(
                """
                SELECT refentree FROM tb_entree
                WHERE EXTRACT(YEAR FROM dateregistre)=%s AND refentree LIKE %s
                ORDER BY id DESC LIMIT 1
                """,
                (annee, f"{annee}-{prefix}-%"),
            )
            derniere_ref = cursor.fetchone()
            nouveau_numero = 1
            if derniere_ref and derniere_ref[0]:
                try:
                    nouveau_numero = int(derniere_ref[0].split('-')[-1]) + 1
                except ValueError:
                    nouveau_numero = 1
            nouvelle_ref = f"{annee}-{prefix}-{nouveau_numero:05d}"
            self.entry_ref_entree.configure(state="normal")
            self.entry_ref_entree.delete(0, "end")
            self.entry_ref_entree.insert(0, nouvelle_ref)
            self.entry_ref_entree.configure(state="readonly")
        except Exception as e:
            messagebox.showerror("Erreur", f"Génération référence : {e}")
        finally:
            conn.close()

    def charger_magasins(self):
        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT idmag, designationmag FROM tb_magasin WHERE deleted=0 ORDER BY designationmag"
            )
            magasins = cursor.fetchall()
            self.magasins_map = {nom: id_ for id_, nom in magasins}
            noms = list(self.magasins_map.keys())
            self.combo_magasin.configure(values=noms)
            if noms:
                idmag_defaut = None
                cursor.execute("SELECT idmag FROM tb_users WHERE iduser=%s LIMIT 1", (self.id_user_connecte,))
                row_user = cursor.fetchone()
                if row_user:
                    idmag_defaut = row_user[0]
                nom_defaut = next((nom for id_, nom in magasins if id_ == idmag_defaut), None)
                self.combo_magasin.set(nom_defaut if nom_defaut else noms[0])
            else:
                self.combo_magasin.set("Aucun magasin trouvé")
        except Exception as e:
            messagebox.showerror("Erreur", f"Chargement magasins : {e}")
        finally:
            conn.close()

    def charger_infos_societe(self):
        _default = {
            'nomsociete': 'SOCIÉTÉ', 'adressesociete': 'N/A',
            'contactsociete': 'N/A', 'villesociete': 'N/A',
            'nifsociete': 'N/A', 'statsociete': 'N/A', 'cifsociete': 'N/A',
        }
        conn = self.connect_db()
        if not conn:
            self.infos_societe = _default
            return
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT nomsociete, adressesociete, contactsociete, villesociete,
                       nifsociete, statsociete, cifsociete
                FROM tb_infosociete LIMIT 1
                """
            )
            result = cursor.fetchone()
            self.infos_societe = {
                'nomsociete': result[0] or 'SOCIÉTÉ',
                'adressesociete': result[1] or 'N/A',
                'contactsociete': result[2] or 'N/A',
                'villesociete': result[3] or 'N/A',
                'nifsociete': result[4] or 'N/A',
                'statsociete': result[5] or 'N/A',
                'cifsociete': result[6] or 'N/A',
            } if result else _default
        except Exception:
            self.infos_societe = _default
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    # Recherche article (inspirée de page_sortie.py)
    # ══════════════════════════════════════════════════════════════════════════

    def open_recherche_article(self):
        fen = ctk.CTkToplevel(self)
        fen.title("Rechercher un article pour l'entrée")
        fen.geometry("1000x600")
        fen.grab_set()

        main_frame = ctk.CTkFrame(fen)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(main_frame, text="Sélectionner un article", font=Fonts.heading(16)).pack(pady=(0, 10))

        search_frame = ctk.CTkFrame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(search_frame, text="🔍 Rechercher :").pack(side="left", padx=5)
        entry_search = ctk.CTkEntry(search_frame, placeholder_text="Code ou désignation…", width=300)
        entry_search.pack(side="left", padx=5, fill="x", expand=True)

        tree_frame = ctk.CTkFrame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))

        style = ttk.Style()
        style.configure(
            "ArtSearchEntree.Treeview",
            rowheight=22,
            font=('Segoe UI', 8),
            background=Colors.BG_CARD,
            foreground=Colors.TEXT_PRIMARY,
            fieldbackground=Colors.BG_CARD,
            borderwidth=0,
        )
        style.configure(
            "ArtSearchEntree.Treeview.Heading",
            background=Colors.BG_HEADER,
            foreground=Colors.TEXT_ON_DARK,
            font=('Segoe UI', 8, 'bold'),
            relief="flat",
        )

        colonnes = ("ID_Article", "ID_Unite", "Code", "Désignation", "Unité", "Stock")
        tree = ttk.Treeview(tree_frame, columns=colonnes, show='headings', height=15, style="ArtSearchEntree.Treeview")
        tree.tag_configure("even", background=Colors.BG_CARD)
        tree.tag_configure("odd", background=Colors.BG_ROW_ALT)

        nom_mag = (self.combo_magasin.get() or "").strip()
        col_cfg = {
            "ID_Article": (0, False, "center"),
            "ID_Unite": (0, False, "center"),
            "Code": (120, True, "w"),
            "Désignation": (330, True, "w"),
            "Unité": (90, True, "w"),
            "Stock": (120, True, "e"),
        }
        for col, (w, stretch, anchor) in col_cfg.items():
            lbl = (f"Magasin {nom_mag}" if col == "Stock" and nom_mag else col)
            tree.heading(col, text=lbl)
            tree.column(col, width=w, stretch=stretch, anchor=anchor)
        tree["displaycolumns"] = ("Code", "Désignation", "Unité", "Stock")

        scrollbar = ctk.CTkScrollbar(tree_frame, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        QUERY_ARTICLES = """
            SELECT
                u.idarticle,
                u.idunite,
                u.codearticle,
                a.designation,
                u.designationunite
            FROM tb_unite u
            INNER JOIN tb_article a ON a.idarticle = u.idarticle
            WHERE a.deleted = 0
              AND COALESCE(u.deleted, 0) = 0
              AND (u.codearticle ILIKE %s OR a.designation ILIKE %s)
            ORDER BY a.designation ASC, u.codearticle ASC, u.idunite ASC
        """

        def charger_articles(filtre=""):
            for item in tree.get_children():
                tree.delete(item)
            conn = self.connect_db()
            if not conn:
                return
            try:
                cur = conn.cursor()
                filtre_like = f"%{filtre}%"
                designationmag = (self.combo_magasin.get() or "").strip()
                idmag_actif = self.magasins_map.get(designationmag)
                tree.heading("Stock", text=f"Magasin {designationmag}" if designationmag else "Magasin")
                if idmag_actif is None:
                    return
                snapshot = get_snapshot(int(idmag_actif), conn=self.conn)
                cur.execute(QUERY_ARTICLES, (filtre_like, filtre_like))
                for idx, row in enumerate(cur.fetchall()):
                    stock_total = snapshot.stock_unite(row[0], row[1])
                    tree.insert(
                        '',
                        'end',
                        values=(row[0], row[1], row[2] or "", row[3] or "", row[4] or "", format_nombre_auto(stock_total)),
                        tags=("even" if idx % 2 == 0 else "odd",),
                    )
            except Exception as e:
                messagebox.showerror("Erreur", f"Chargement articles : {e}")
            finally:
                if 'cur' in locals() and cur:
                    cur.close()
                conn.close()

        def valider_selection():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Attention", "Sélectionnez un article.")
                return
            values = tree.item(sel[0]).get('values', [])
            if len(values) < 6:
                messagebox.showerror("Erreur", "Données incomplètes.")
                return
            article = {
                'idarticle': values[0],
                'idunite': values[1],
                'code_article': values[2],
                'nom_article': values[3],
                'nom_unite': values[4],
                'stock_disponible': self.parser_nombre(str(values[5])),
            }
            fen.destroy()
            self.on_article_selected(article)

        entry_search.bind('<KeyRelease>', lambda e: charger_articles(entry_search.get()))
        tree.bind('<Double-Button-1>', lambda e: valider_selection())

        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x")
        ctk.CTkButton(
            btn_frame,
            text="❌ Annuler",
            command=fen.destroy,
            fg_color=Colors.DANGER,
            hover_color=Colors.DANGER_DARK,
        ).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(
            btn_frame,
            text="✅ Valider",
            command=valider_selection,
            fg_color=Colors.SUCCESS_DARK,
            hover_color=Colors.INFO_DARK,
        ).pack(side="right", padx=5, pady=5)

        charger_articles()

    def on_article_selected(self, article_data):
        self.article_selectionne = article_data
        designation = f"[{article_data.get('code_article','N/A')}] {article_data['nom_article']}"
        self.entry_article.configure(state="normal")
        self.entry_article.delete(0, "end")
        self.entry_article.insert(0, designation)
        self.entry_article.configure(state="readonly")

        self.entry_unite.configure(state="normal")
        self.entry_unite.delete(0, "end")
        self.entry_unite.insert(0, article_data['nom_unite'])
        self.entry_unite.configure(state="readonly")

        self.entry_qtentree.delete(0, "end")
        self.entry_qtentree.focus_set()

    # ══════════════════════════════════════════════════════════════════════════
    # Détail entrée
    # ══════════════════════════════════════════════════════════════════════════

    def valider_detail(self):
        if not self.article_selectionne:
            messagebox.showwarning("Attention", "Sélectionnez d'abord un article.")
            return

        try:
            qtentree = self.parser_nombre(self.entry_qtentree.get().strip())
            if qtentree <= 0:
                raise ValueError
        except Exception:
            messagebox.showerror("Erreur", "La quantité doit être un nombre positif.")
            return

        designationmag = self.combo_magasin.get()
        idmag = self.magasins_map.get(designationmag)
        if not idmag:
            messagebox.showerror("Erreur", "Sélectionnez un magasin valide.")
            return

        motif_ligne = self.entry_motif.get().strip() or "Aucune description"
        nouveau_detail = {
            'idmag': idmag,
            'designationmag': designationmag,
            'idarticle': self.article_selectionne['idarticle'],
            'code_article': self.article_selectionne.get('code_article', 'N/A'),
            'nom_article': self.article_selectionne['nom_article'],
            'idunite': self.article_selectionne['idunite'],
            'nom_unite': self.article_selectionne['nom_unite'],
            'qtentree': qtentree,
            'motif': motif_ligne,
        }

        if self.index_ligne_selectionnee is not None:
            self.detail_entree[self.index_ligne_selectionnee] = nouveau_detail
            messagebox.showinfo("Succès", "Ligne modifiée.")
        else:
            for i, detail in enumerate(self.detail_entree):
                if (detail['idarticle'] == nouveau_detail['idarticle']
                        and detail['idunite'] == nouveau_detail['idunite']
                        and detail['idmag'] == nouveau_detail['idmag']):
                    if messagebox.askyesno(
                        "Doublon détecté",
                        f"Article « {detail['nom_article']} » déjà présent. Fusionner les quantités ?",
                    ):
                        nouvelle_qte = detail['qtentree'] + nouveau_detail['qtentree']
                        self.detail_entree[i]['qtentree'] = nouvelle_qte
                        m_exist = (self.detail_entree[i].get('motif') or "").strip()
                        if motif_ligne and motif_ligne != "Aucune description" and motif_ligne not in m_exist:
                            self.detail_entree[i]['motif'] = f"{m_exist}, {motif_ligne}".strip(", ")
                        messagebox.showinfo("Succès", "Quantité fusionnée.")
                        self.charger_details_treeview()
                        self.reset_detail_form()
                    return
            self.detail_entree.append(nouveau_detail)

        self.charger_details_treeview()
        self.reset_detail_form()

    def charger_details_treeview(self):
        if self.tree_details is None:
            return
        for item in self.tree_details.get_children():
            self.tree_details.delete(item)

        for idx, detail in enumerate(self.detail_entree):
            values = [
                detail['idarticle'],
                detail['idunite'],
                detail['idmag'],
                detail.get('code_article', 'N/A'),
                detail['nom_article'],
                detail['designationmag'],
                detail['nom_unite'],
                self.formater_nombre(detail['qtentree']),
                detail.get('motif', ''),
            ]
            self.tree_details.insert('', 'end', values=values, tags=("even" if idx % 2 == 0 else "odd",))

    def modifier_detail(self, _event):
        selected_item = self.tree_details.focus()
        if not selected_item:
            return
        try:
            self.index_ligne_selectionnee = self.tree_details.index(selected_item)
            detail = self.detail_entree[self.index_ligne_selectionnee]
        except Exception:
            messagebox.showerror("Erreur", "Impossible de récupérer la ligne.")
            self.reset_detail_form()
            return

        self.article_selectionne = {
            'idarticle': detail['idarticle'],
            'nom_article': detail['nom_article'],
            'idunite': detail['idunite'],
            'nom_unite': detail['nom_unite'],
            'code_article': detail.get('code_article', 'N/A'),
        }

        designation = f"[{detail.get('code_article','N/A')}] {detail['nom_article']}"
        self.entry_article.configure(state="normal")
        self.entry_article.delete(0, "end")
        self.entry_article.insert(0, designation)
        self.entry_article.configure(state="readonly")

        self.entry_unite.configure(state="normal")
        self.entry_unite.delete(0, "end")
        self.entry_unite.insert(0, detail['nom_unite'])
        self.entry_unite.configure(state="readonly")

        self.entry_qtentree.delete(0, "end")
        self.entry_qtentree.insert(0, self.formater_nombre(detail['qtentree']))
        self.entry_motif.delete(0, "end")
        self.entry_motif.insert(0, detail.get('motif', ''))

        self.btn_ajouter.configure(text="✔ Valider Modif", fg_color=Colors.WARNING, hover_color="#E65100")
        self.btn_annuler_mod.configure(state="normal")

    def supprimer_detail(self):
        selected_item = self.tree_details.focus()
        if not selected_item:
            messagebox.showwarning("Attention", "Sélectionnez une ligne à supprimer.")
            return
        if messagebox.askyesno("Confirmation", "Supprimer cette ligne ?"):
            try:
                index = self.tree_details.index(selected_item)
                self.detail_entree.pop(index)
                self.tree_details.delete(selected_item)
                self.reset_detail_form()
                messagebox.showinfo("Succès", "Ligne supprimée.")
            except Exception as e:
                messagebox.showerror("Erreur", f"Suppression impossible : {e}")

    def reset_detail_form(self):
        self.article_selectionne = None
        self.index_ligne_selectionnee = None

        for entry, state in [(self.entry_article, "readonly"), (self.entry_unite, "readonly")]:
            entry.configure(state="normal")
            entry.delete(0, "end")
            entry.configure(state=state)

        self.entry_qtentree.delete(0, "end")

        self.btn_ajouter.configure(text="+ Ajouter", fg_color=Colors.SUCCESS_DARK, hover_color=Colors.INFO_DARK)
        self.btn_annuler_mod.configure(state="disabled")

    # ══════════════════════════════════════════════════════════════════════════
    # Recherche / chargement BE
    # ══════════════════════════════════════════════════════════════════════════

    def ouvrir_recherche_entree(self):
        fen = ctk.CTkToplevel(self)
        fen.title("Rechercher un bon d'entrée")
        fen.geometry("1000x500")
        fen.grab_set()

        main_frame = ctk.CTkFrame(fen)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(main_frame, text="Sélectionner un bon d'entrée", font=Fonts.heading(16)).pack(pady=(0, 10))

        search_frame = ctk.CTkFrame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(search_frame, text="🔍 Rechercher :").pack(side="left", padx=5)
        entry_search = ctk.CTkEntry(search_frame, placeholder_text="Référence ou motif…", width=300)
        entry_search.pack(side="left", padx=5, fill="x", expand=True)

        tree_frame = ctk.CTkFrame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))
        colonnes = ("ID", "Référence", "Date", "Motif", "Utilisateur", "Nb Lignes")
        tree = ttk.Treeview(tree_frame, columns=colonnes, show='headings', height=12)
        tree.tag_configure("even", background=Colors.BG_CARD)
        tree.tag_configure("odd", background=Colors.BG_ROW_ALT)

        col_w = {
            "ID": (0, False),
            "Référence": (150, True),
            "Date": (100, True),
            "Motif": (300, True),
            "Utilisateur": (150, True),
            "Nb Lignes": (80, True),
        }
        for col, (w, stretch) in col_w.items():
            tree.column(col, width=w, stretch=stretch)
        from treeview_sort_utils import attach_tree_sort
        attach_tree_sort(tree, list(col_w.keys()), configure_columns=False)

        scrollbar = ctk.CTkScrollbar(tree_frame, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        label_count = ctk.CTkLabel(main_frame, text="")
        label_count.pack(pady=5)

        def charger_entrees(filtre=""):
            for item in tree.get_children():
                tree.delete(item)
            conn = self.connect_db()
            if not conn:
                return
            try:
                cursor = conn.cursor()
                query = """
                    SELECT e.id, e.refentree, e.dateregistre,
                       COALESCE(NULLIF((
                           SELECT string_agg(NULLIF(TRIM(ed2.motif),''),', ' ORDER BY ed2.id)
                           FROM tb_entreedetail ed2 WHERE ed2.identree=e.id
                       ),''),'Motif non précisé') AS motif_lignes,
                       CONCAT(u.prenomuser,' ',u.nomuser) AS utilisateur,
                       (SELECT COUNT(*) FROM tb_entreedetail ed WHERE ed.identree=e.id) AS nb_lignes
                    FROM tb_entree e
                    LEFT JOIN tb_users u ON e.iduser=u.iduser
                    WHERE e.deleted=0
                """
                params = []
                if filtre:
                    query += """
                        AND (LOWER(e.refentree) LIKE LOWER(%s)
                          OR LOWER(COALESCE((
                              SELECT string_agg(NULLIF(TRIM(ed2.motif),''),', ' ORDER BY ed2.id)
                              FROM tb_entreedetail ed2 WHERE ed2.identree=e.id
                          ),'')) LIKE LOWER(%s))"""
                    params = [f"%{filtre}%", f"%{filtre}%"]
                query += " ORDER BY e.dateregistre DESC, e.refentree DESC"

                cursor.execute(query, params)
                resultats = cursor.fetchall()
                for idx, row in enumerate(resultats):
                    date_str = row[2].strftime("%d/%m/%Y") if row[2] else ""
                    tree.insert(
                        '',
                        'end',
                        values=(row[0], row[1], date_str, row[3] or "", row[4] or "", row[5] or 0),
                        tags=("even" if idx % 2 == 0 else "odd",),
                    )
                label_count.configure(text=f"{len(resultats)} bon(s) d'entrée")
            except Exception as e:
                messagebox.showerror("Erreur", f"Chargement : {e}")
            finally:
                if 'cursor' in locals() and cursor:
                    cursor.close()
                conn.close()

        def valider_selection():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Attention", "Sélectionnez un bon d'entrée.")
                return
            identree = tree.item(sel[0])['values'][0]
            fen.destroy()
            self.charger_entree(identree)

        entry_search.bind('<KeyRelease>', lambda e: charger_entrees(entry_search.get()))
        tree.bind('<Double-Button-1>', lambda e: valider_selection())

        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x")
        ctk.CTkButton(
            btn_frame,
            text="❌ Annuler",
            command=fen.destroy,
            fg_color=Colors.DANGER,
            hover_color=Colors.DANGER_DARK,
        ).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(
            btn_frame,
            text="✅ Charger",
            command=valider_selection,
            fg_color=Colors.SUCCESS_DARK,
            hover_color=Colors.INFO_DARK,
        ).pack(side="right", padx=5, pady=5)

        charger_entrees()

    def charger_entree(self, identree: int):
        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT e.id, e.refentree, e.dateregistre, e.description,
                       CONCAT(u.prenomuser,' ',u.nomuser) AS utilisateur
                FROM tb_entree e
                LEFT JOIN tb_users u ON e.iduser=u.iduser
                WHERE e.id=%s AND e.deleted=0
                """,
                (identree,),
            )
            entree = cursor.fetchone()
            if not entree:
                messagebox.showerror("Erreur", "Bon d'entrée non trouvé.")
                return

            cursor.execute(
                """
                SELECT ed.idmag, m.designationmag, ed.idarticle, u.codearticle,
                       a.designation, ed.idunite, u.designationunite, ed.qtentree, ed.motif
                FROM tb_entreedetail ed
                INNER JOIN tb_article a ON ed.idarticle=a.idarticle
                INNER JOIN tb_unite   u ON ed.idunite=u.idunite
                INNER JOIN tb_magasin m ON ed.idmag=m.idmag
                WHERE ed.identree=%s AND ed.deleted=0
                """,
                (identree,),
            )
            details = cursor.fetchall()

            self.reset_form(reset_imprimer=False)
            self.mode_modification = True
            self.identree_charge = identree
            self.derniere_identree_enregistree = identree

            self.entry_ref_entree.configure(state="normal")
            self.entry_ref_entree.delete(0, "end")
            self.entry_ref_entree.insert(0, entree[1])
            self.entry_ref_entree.configure(state="readonly")

            if entree[2]:
                set_date_on_widget(self.entry_date_entree, entree[2])

            self.detail_entree = []
            for d in details:
                idmag, designationmag, idarticle, codearticle, designation, idunite, designationunite, qtentree, motif = d
                self.detail_entree.append({
                    'idmag': idmag,
                    'designationmag': designationmag,
                    'idarticle': idarticle,
                    'code_article': codearticle,
                    'nom_article': designation,
                    'idunite': idunite,
                    'nom_unite': designationunite,
                    'qtentree': qtentree,
                    'motif': motif or "",
                })
            self.charger_details_treeview()

            self.btn_imprimer.configure(state="normal")
            self.btn_imprimer.grid()
            self.btn_enregistrer.configure(state="disabled", text="📄 Mode Consultation")

            messagebox.showinfo(
                "Chargement réussi",
                f"Bon d'entrée {entree[1]} chargé.\nVous pouvez maintenant l'imprimer.\n\n"
                "Note : L'enregistrement est désactivé en mode consultation.",
            )
        except Exception as e:
            messagebox.showerror("Erreur", f"Chargement bon d'entrée : {e}")
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    # Enregistrement
    # ══════════════════════════════════════════════════════════════════════════

    def enregistrer_entree(self):
        if not self.detail_entree:
            messagebox.showwarning("Attention", "La liste est vide.")
            return

        ref_entree = self.entry_ref_entree.get()
        date_entree = get_date_from_widget(self.entry_date_entree)
        designationmag = self.combo_magasin.get()
        if not ref_entree or not date_entree or not designationmag:
            messagebox.showwarning("Attention", "Remplissez tous les champs obligatoires.")
            return

        msg_conf = (
            "CONFIRMEZ L'ENTRÉE D'ARTICLES\n\n"
            f"Référence : {ref_entree}\n"
            f"Articles : {len(self.detail_entree)}\n\n"
            "Enregistrer cette entrée ?"
        )
        if not messagebox.askyesno("Confirmation", msg_conf):
            return

        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()

            try:
                session_path = get_session_path()
                with open(session_path, 'r', encoding='utf-8') as f:
                    session = json.load(f)
                iduser = session.get('user_id') or self.id_user_connecte
            except Exception:
                iduser = self.id_user_connecte

            cursor.execute(
                "INSERT INTO tb_entree (refentree, iduser, description, deleted) "
                "VALUES (%s,%s,%s,0) RETURNING id",
                (ref_entree, iduser, None),
            )
            identree = cursor.fetchone()[0]

            for d in self.detail_entree:
                cursor.execute(
                    "INSERT INTO tb_entreedetail (identree, idmag, idarticle, idunite, qtentree, motif, deleted) "
                    "VALUES (%s,%s,%s,%s,%s,%s,0)",
                    (identree, d['idmag'], d['idarticle'], d['idunite'], d['qtentree'], d.get('motif')),
                )

            conn.commit()

            try:
                self._logger.log(
                    action="Création bon d'entrée",
                    element=str(ref_entree),
                    details=f"Bon d'entrée enregistré (identree={identree}, magasin='{designationmag}', lignes={len(self.detail_entree)})",
                    value=f"identree={identree}",
                )
            except Exception:
                pass

            messagebox.showinfo("Succès", f"Entrée N°{ref_entree} enregistrée.")
            self.derniere_identree_enregistree = identree
            self.generer_pdf_entree_paysage(ref_entree)
            self.reset_form()

        except psycopg2.Error as e:
            conn.rollback()
            messagebox.showerror("Erreur BD", str(e))
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur", str(e))
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            conn.close()

    def reset_form(self, reset_imprimer: bool = True):
        self.detail_entree = []
        self.article_selectionne = None
        self.index_ligne_selectionnee = None
        self.mode_modification = False
        self.identree_charge = None

        set_date_on_widget(self.entry_date_entree, datetime.now().date())
        self.entry_motif.delete(0, "end")

        self.charger_magasins()
        self.generer_reference()
        self.reset_detail_form()

        if self.tree_details:
            for item in self.tree_details.get_children():
                self.tree_details.delete(item)

        self.btn_enregistrer.configure(state="normal", text="💾 Enregistrer l'Entrée")

        if reset_imprimer:
            self.btn_imprimer.configure(state="disabled")
            self.btn_imprimer.grid_remove()
            self.derniere_identree_enregistree = None

    def nouveau_bon_entree(self):
        if messagebox.askyesno(
            "Nouveau Bon d'Entrée",
            "Créer un nouveau bon d'entrée ?\nToutes les données non enregistrées seront perdues.",
        ):
            self.reset_form(reset_imprimer=True)
            messagebox.showinfo("Nouveau BE", "Formulaire réinitialisé.")

    # ══════════════════════════════════════════════════════════════════════════
    # Impression (format identique au moteur PDF mouvements)
    # ══════════════════════════════════════════════════════════════════════════

    def open_file(self, filename):
        try:
            if os.name == 'nt':
                open_file_if_enabled(filename, operation="open", setting_key="Entree_OpenA5", setting_default=1)
            elif sys.platform == 'darwin':
                subprocess.call(['open', filename])
            else:
                subprocess.call(['xdg-open', filename])
        except Exception:
            pass

    def open_impression_dialogue(self):
        if self.derniere_identree_enregistree is None:
            messagebox.showwarning("Attention", "ID d'entrée introuvable.")
            return

        dialogue = simpledialog.askstring(
            "Format d'Impression",
            "Format d'impression ?\nEntrez « A5 » ou « 80mm ».",
            parent=self,
        )
        if not dialogue:
            return
        if dialogue.lower() == 'a5':
            self.imprimer_bon_entree(self.derniere_identree_enregistree, format='A5')
        elif dialogue.lower() == '80mm':
            self.imprimer_bon_entree(self.derniere_identree_enregistree, format='80mm')
        else:
            messagebox.showwarning("Format inconnu", "Choisissez « A5 » ou « 80mm ».")

    def generer_pdf_entree_paysage(self, ref_entree: str, output_path: Optional[str] = None):
        try:
            filename = output_path or f"BonEntree_{ref_entree.replace('-','_')}.pdf"

            username = "Utilisateur"
            conn = self.connect_db()
            if conn:
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT username FROM tb_users WHERE iduser=%s", (self.id_user_connecte,))
                    row = cur.fetchone()
                    if row:
                        username = row[0]
                    cur.close()
                except Exception:
                    pass
                finally:
                    conn.close()

            columns = ("Code", "Désignation", "Unité", "Quantité", "Magasin", "Motif")
            rows = [
                (
                    str(d.get('code_article', '')),
                    str(d.get('nom_article', '')),
                    str(d.get('nom_unite', '')),
                    d.get('qtentree', 0) or 0,
                    str(d.get('designationmag', '')),
                    str(d.get('motif', '')),
                )
                for d in self.detail_entree
            ]
            table_data = (columns, rows)

            from EtatsPDF_Mouvements import EtatPDFMouvements
            etat = EtatPDFMouvements()
            try:
                etat.connect_db()
            except Exception:
                pass

            result = etat._build_pdf_a5(
                output_path=filename,
                titre_entete="BON D'ENTRÉE",
                reference=ref_entree,
                date_operation=datetime.now().strftime('%d/%m/%Y'),
                magasin=self.combo_magasin.get() if hasattr(self, 'combo_magasin') else '',
                operateur=username,
                table_data=table_data,
                description="",
                responsable_1="Le Magasinier",
                responsable_2="Le Contrôleur",
            )
            try:
                etat.close_db()
            except Exception:
                pass

            if result and sys.platform == 'win32':
                try:
                    open_file_if_enabled(filename, operation="open", setting_key="Entree_OpenA5", setting_default=1)
                except Exception:
                    pass
            return result
        except Exception as e:
            print(f"Erreur PDF Entrée : {e}")
            traceback.print_exc()
            messagebox.showerror("Erreur", f"Erreur PDF Entrée : {e}")
            return None

    def get_data_bon_entree(self, identree: int) -> Optional[Dict[str, Any]]:
        conn = self.connect_db()
        if not conn:
            return None

        data = {'societe': self.infos_societe, 'entree': None, 'utilisateur': None, 'details': []}
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT e.refentree, e.dateregistre, e.description,
                       u.nomuser, u.prenomuser
                FROM tb_entree e
                INNER JOIN tb_users u ON e.iduser=u.iduser
                WHERE e.id=%s
                """,
                (identree,),
            )
            row = cursor.fetchone()
            if not row:
                messagebox.showerror("Erreur", "Bon d'Entrée introuvable.")
                return None

            data['entree'] = {
                'refentree': row[0],
                'dateregistre': row[1].strftime("%d/%m/%Y") if row[1] else "",
                'description': row[2],
            }
            data['utilisateur'] = {'nomuser': row[3], 'prenomuser': row[4]}

            cursor.execute(
                """
                SELECT u.codearticle, a.designation, u.designationunite,
                       ed.qtentree, m.designationmag, ed.motif
                FROM tb_entreedetail ed
                INNER JOIN tb_article a ON ed.idarticle=a.idarticle
                INNER JOIN tb_unite   u ON ed.idunite=u.idunite
                INNER JOIN tb_magasin m ON ed.idmag=m.idmag
                WHERE ed.identree=%s AND ed.deleted=0
                ORDER BY a.designation
                """,
                (identree,),
            )
            data['details'] = cursor.fetchall()
            return data
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
            return None
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            conn.close()

    def imprimer_bon_entree(self, identree: int, format: str):
        data = self.get_data_bon_entree(identree)
        if not data:
            return
        try:
            ref_entree = data['entree']['refentree']
            project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            etats_dir = os.path.join(project_dir, "Etats Impression")
            os.makedirs(etats_dir, exist_ok=True)

            if format.lower() == 'a5':
                filename = f"BE_{ref_entree.replace('-','_')}_A5.pdf"
                pdf_path = os.path.join(etats_dir, filename)
                # Utilise la liste actuelle (chargée) pour générer le PDF dans le dossier états
                self.generer_pdf_entree_paysage(ref_entree, output_path=pdf_path)
                messagebox.showinfo("Impression A5", f"PDF généré : {pdf_path}")
                self.open_file(pdf_path)
            elif format.lower() == '80mm':
                filename = f"BE_{ref_entree.replace('-','_')}_80mm.txt"
                txt_path = os.path.join(etats_dir, filename)
                self.generate_ticket_80mm(data, txt_path)
                messagebox.showinfo("Impression 80mm", f"Ticket généré : {txt_path}")
                self.open_file(txt_path)
        except Exception as e:
            messagebox.showerror("Erreur Génération", str(e))

    def generate_ticket_80mm(self, data: Dict[str, Any], filename: str):
        societe = data['societe']
        entree = data['entree']
        utilisateur = data['utilisateur']
        details = data['details']

        MAX_WIDTH = 40

        def center(text): return text.center(MAX_WIDTH)
        def line(): return "-" * MAX_WIDTH

        def format_detail_line(designation, qte, unite):
            qte_str = self.formater_nombre(qte)
            space = MAX_WIDTH - len(qte_str) - len(unite) - 3
            desig = str(designation)[:space].ljust(space)
            return f"{desig} {qte_str} {unite}"

        content = [
            center("Informations Société"),
            f" {societe.get('nomsociete','N/A')}",
            societe.get('adressesociete','N/A'),
            societe.get('villesociete','N/A'),
            societe.get('contactsociete','N/A'),
            line(),
            center(f"NIF: {societe.get('nifsociete','N/A')}"),
            center(f"STAT: {societe.get('statsociete','N/A')}"),
            center(f"CIF: {societe.get('cifsociete','N/A')}"),
            f"Réf BE: {entree['refentree']}",
            f"Date: {entree['dateregistre']}",
            f"Motif: {entree['description']}",
            f"Utilisateur: {utilisateur['prenomuser']} {utilisateur['nomuser']}",
            line(),
            "DESIGNATION QTE UNITE",
            line(),
        ]

        for _code, designation, unite, qte, _magasin, _motif in details:
            content.append(format_detail_line(designation, qte, unite))

        content += [
            line(),
            "\n\n\n",
            center("Signature"),
            "\n\n\n",
            center("Merci de votre collaboration"),
        ]

        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))


if __name__ == "__main__":
    USER_ID_TEST = 1
    app = ctk.CTk()
    app.title("iJeery — Gestion des Entrées (test)")
    app.geometry("1300x800")
    page = PageEntree(app, USER_ID_TEST)
    page.pack(fill="both", expand=True)
    app.mainloop()

