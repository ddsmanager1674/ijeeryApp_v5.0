# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  iJeery — pages/page_transfert.py                           ║
║                  Transfert de stock entre magasins                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  REFONTE UI — Mars 2026                                                      ║
║  Structure identique à page_venteParMsin / page_avoir :                      ║
║    Row 0 — Bandeau en-tête (Réf | Date | Mag Sortie | Mag Entrée)           ║
║    Row 1 — Bandeau Description (pleine largeur)                              ║
║    Row 2 — Bandeau saisie article (Code | Nom | 🔍 | Unité | Qté | ➕)      ║
║    Row 3 — Tableau Treeview (weight=1 → expansible)                         ║
║    Row 4 — Barre d'actions (Nouveau | 📂 Charger | 🗑 Supprimer | 💾)       ║
║                                                                              ║
║  Logique métier : 100% INCHANGÉE                                             ║
║  Seul setup_ui() → _setup_ui() est refait avec le thème iJeery              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import customtkinter as ctk
from tkinter import ttk
import psycopg2
import json
from datetime import datetime
import os

from resource_utils import get_config_path, safe_file_read
from app_theme import Colors, Fonts
from stock_snapshot import StockSnapshot, format_nombre_auto

# ReportLab (impression PDF)
from reportlab.lib.pagesizes import A5
from reportlab.lib import colors as rl_colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT


class MessageDialog(ctk.CTkToplevel):
    """Dialogue personnalisé info/warning/error."""

    def __init__(self, title: str, message: str, type_: str = 'info'):
        super().__init__()
        self.title(title)
        self.geometry("400x180")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_CARD)

        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        ww, wh = 400, 180
        x = (sw // 2) - (ww // 2)
        y = (sh // 2) - (wh // 2)
        self.geometry(f"{ww}x{wh}+{x}+{y}")

        icon_text = "ℹ️" if type_ == 'info' else "⚠️" if type_ == 'warning' else "❌"
        icon_color = Colors.PRIMARY if type_ == 'info' else Colors.WARNING if type_ == 'warning' else Colors.DANGER

        ctk.CTkLabel(self, text=icon_text, font=Fonts.heading(24), text_color=icon_color).pack(pady=(20, 5))
        ctk.CTkLabel(
            self, text=message, font=Fonts.body(12),
            text_color=Colors.TEXT_PRIMARY, wraplength=350, justify="center"
        ).pack(pady=(0, 20), padx=20)
        ctk.CTkButton(
            self, text="OK", command=self.destroy, width=100, height=36,
            fg_color=Colors.SUCCESS_DARK, hover_color=Colors.INFO_DARK
        ).pack(pady=(0, 14))

        self.grab_set()
        self.lift()
        self.focus_force()
        self.attributes('-topmost', True)
        self.wait_window()


class YesNoDialog(ctk.CTkToplevel):
    """Dialogue personnalisé de confirmation Oui/Non."""

    def __init__(self, title: str, message: str):
        super().__init__()
        self.title(title)
        self.geometry("420x190")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_CARD)
        self.result = False

        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        ww, wh = 420, 190
        x = (sw // 2) - (ww // 2)
        y = (sh // 2) - (wh // 2)
        self.geometry(f"{ww}x{wh}+{x}+{y}")

        ctk.CTkLabel(self, text="❓", font=Fonts.heading(24), text_color=Colors.WARNING).pack(pady=(20, 5))
        ctk.CTkLabel(
            self, text=message, font=Fonts.body(12),
            text_color=Colors.TEXT_PRIMARY, wraplength=360, justify="center"
        ).pack(pady=(0, 20), padx=20)

        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(pady=(0, 14))
        ctk.CTkButton(
            bf, text="Non", width=100, height=36, command=self._no,
            fg_color=Colors.DANGER, hover_color=Colors.DANGER_DARK
        ).pack(side="left", padx=10)
        ctk.CTkButton(
            bf, text="Oui", width=100, height=36, command=self._yes,
            fg_color=Colors.SUCCESS_DARK, hover_color=Colors.INFO_DARK
        ).pack(side="right", padx=10)

        self.grab_set()
        self.lift()
        self.focus_force()
        self.attributes('-topmost', True)
        self.wait_window()

    def _yes(self):
        self.result = True
        self.destroy()

    def _no(self):
        self.result = False
        self.destroy()


class PageTransfert(ctk.CTkFrame):
    """
    Page de transfert de stock entre magasins.

    Architecture UI (cohérente avec page_venteParMsin) :
    ┌─────────────────────────────────────────────────────────────┐
    │ Row 0 — Réf | Date | Mag Sortie ➜ | Mag Entrée             │ card BG_CARD
    │ Row 1 — Description (pleine largeur)                        │ card BG_CARD
    │ Row 2 — Article | Nom | 🔍 Rechercher | Unité | Qté | ➕    │ card BG_CARD
    │ Row 3 — Tableau Treeview (expansible)                       │ frame MIDNIGHT hdr
    │ Row 4 — Actions : Nouveau | 📂 Charger | 🗑 Suppr | 💾 Enr │ frame BG_PAGE
    └─────────────────────────────────────────────────────────────┘
    """

    def __init__(self, parent, user_id):
        super().__init__(parent, fg_color=Colors.BG_PAGE)
        self.user_id = user_id
        self.articles_transfert: list = []
        self.magasins_data:      dict = {}

        # Identifiant du transfert en cours d'édition (None = nouveau)
        self.idtransfert_en_cours = None

        # ── Layout principal : 5 rows ─────────────────────────────────────────
        self.grid_columnconfigure(0, weight=1)
        for row, w in enumerate([0, 0, 0, 1, 0]):
            self.grid_rowconfigure(row, weight=w)

        # ── Construction de l'interface ───────────────────────────────────────
        self._setup_ui()

        # ── Chargements initiaux ──────────────────────────────────────────────
        self.charger_magasins()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1 — CONNEXION BASE DE DONNÉES
    # ══════════════════════════════════════════════════════════════════════════

    def connect_db(self):
        """Ouvre une connexion fraîche à PostgreSQL depuis config.json."""
        try:
            with open(get_config_path('config.json')) as f:
                config    = json.load(f)
                db_config = config['database']

            return psycopg2.connect(
                host=db_config['host'],
                user=db_config['user'],
                password=db_config['password'],
                database=db_config['database'],
                port=db_config['port'],
            )
        except FileNotFoundError:
            MessageDialog("Erreur", "config.json non trouvé.", type_='error')
            return None
        except KeyError:
            MessageDialog("Erreur", "Clés de base de données manquantes.", type_='error')
            return None
        except psycopg2.Error as err:
            MessageDialog("Erreur connexion", str(err), type_='error')
            return None
        except UnicodeDecodeError as err:
            MessageDialog("Erreur encodage", str(err), type_='error')
            return None

    def get_connection(self):
        """Alias public pour rétrocompatibilité."""
        return self.connect_db()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — CONSTRUCTION DE L'INTERFACE
    # ══════════════════════════════════════════════════════════════════════════

    def _setup_ui(self):
        """
        Point d'entrée UI — délègue à 5 sous-méthodes.
        Aucune logique métier ici.
        """
        self._build_header_band()       # Row 0 — Réf / Date / Magasins
        self._build_description_band()  # Row 1 — Description
        self._build_article_band()      # Row 2 — Saisie article
        self._build_tree_zone()         # Row 3 — Tableau
        self._build_actions_band()      # Row 4 — Boutons d'action

        # Génération de la première référence
        self.generer_reference()

    # ── Row 0 — Bandeau en-tête ───────────────────────────────────────────────

    def _build_header_band(self):
        """
        Card blanche (Row 0) : Référence (readonly) | Date | Mag Sortie | Mag Entrée.
        """
        card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        card.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 2))
        for col in range(4):
            card.grid_columnconfigure(col, weight=1)

        lbl_kw   = dict(font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY, anchor="w")
        entry_kw = dict(
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            height=32, corner_radius=6, font=Fonts.input(12),
        )
        entry_kw_no_font = {k: v for k, v in entry_kw.items() if k != 'font'}

        # — Référence (bold, readonly) —
        ctk.CTkLabel(card, text="Référence", **lbl_kw).grid(
            row=0, column=0, padx=(10, 2), pady=(8, 0), sticky="w")
        self.entry_ref = ctk.CTkEntry(
            card, **entry_kw_no_font, font=Fonts.bold(12), state="readonly",
        )
        self.entry_ref.grid(row=1, column=0, padx=(10, 4), pady=(0, 8), sticky="ew")

        # — Date —
        ctk.CTkLabel(card, text="Date", **lbl_kw).grid(
            row=0, column=1, padx=4, pady=(8, 0), sticky="w")
        self.entry_date = ctk.CTkEntry(card, **entry_kw)
        self.entry_date.grid(row=1, column=1, padx=4, pady=(0, 8), sticky="ew")
        self.entry_date.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # — Magasin Sortie —
        ctk.CTkLabel(card, text="Magasin Sortie  ➜", **lbl_kw).grid(
            row=0, column=2, padx=4, pady=(8, 0), sticky="w")
        self.combo_mag_sortie = ctk.CTkComboBox(
            card, values=[""], height=32,
            font=Fonts.input(12), fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER, button_color=Colors.DANGER,
            dropdown_fg_color=Colors.BG_CARD,
        )
        self.combo_mag_sortie.grid(row=1, column=2, padx=4, pady=(0, 8), sticky="ew")

        # — Magasin Entrée —
        ctk.CTkLabel(card, text="Magasin Entrée", **lbl_kw).grid(
            row=0, column=3, padx=(4, 10), pady=(8, 0), sticky="w")
        self.combo_mag_entree = ctk.CTkComboBox(
            card, values=[""], height=32,
            font=Fonts.input(12), fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER, button_color=Colors.SUCCESS_DARK,
            dropdown_fg_color=Colors.BG_CARD,
        )
        self.combo_mag_entree.grid(row=1, column=3, padx=(4, 10), pady=(0, 8), sticky="ew")

    # ── Row 1 — Bandeau description ───────────────────────────────────────────

    def _build_description_band(self):
        """
        Card blanche (Row 1) : champ Description (global du transfert) pleine largeur.
        """
        card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        card.grid(row=1, column=0, sticky="ew", padx=0, pady=(0, 2))
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card, text="Description",
            font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY,
        ).grid(row=0, column=0, padx=(10, 6), pady=8, sticky="w")

        self.entry_description = ctk.CTkEntry(
            card,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            height=32, corner_radius=6, font=Fonts.input(12),
            placeholder_text="Description du transfert…",
        )
        self.entry_description.grid(row=0, column=1, padx=(0, 10), pady=8, sticky="ew")

    # ── Row 2 — Bandeau saisie article ───────────────────────────────────────

    def _build_article_band(self):
        """
        Card blanche (Row 2) : Code | Désignation | 🔍 Rechercher | Unité | Qté | ➕ Ajouter.
        """
        card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        card.grid(row=2, column=0, sticky="ew", padx=0, pady=(0, 2))
        # Colonnes : Code(fixe) | Nom(flex) | Rechercher | Unité | Qté | Ajouter
        card.grid_columnconfigure(0, weight=0)
        card.grid_columnconfigure(1, weight=2)
        card.grid_columnconfigure(2, weight=0)
        card.grid_columnconfigure(3, weight=1)
        card.grid_columnconfigure(4, weight=0)
        card.grid_columnconfigure(5, weight=0)

        lbl_kw   = dict(font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY, anchor="w")
        entry_kw = dict(
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            height=32, corner_radius=6, font=Fonts.input(12),
        )

        # — Code Article (readonly) —
        ctk.CTkLabel(card, text="Code Article", **lbl_kw).grid(
            row=0, column=0, padx=(10, 2), pady=(8, 0), sticky="w")
        self.entry_code_article = ctk.CTkEntry(
            card, **entry_kw, width=120, state="readonly",
        )
        self.entry_code_article.grid(row=1, column=0, padx=(10, 4), pady=(0, 8), sticky="ew")

        # — Désignation Article (readonly) —
        ctk.CTkLabel(card, text="Article", **lbl_kw).grid(
            row=0, column=1, padx=4, pady=(8, 0), sticky="w")
        self.entry_nom_article = ctk.CTkEntry(
            card, **entry_kw, placeholder_text="Sélectionner un article…",
            state="readonly",
        )
        self.entry_nom_article.grid(row=1, column=1, padx=4, pady=(0, 8), sticky="ew")

        # — Bouton Rechercher —
        ctk.CTkLabel(card, text=" ", **lbl_kw).grid(
            row=0, column=2, padx=4, pady=(8, 0))
        btn_recherche = ctk.CTkButton(
            card, text="🔍 Rechercher", height=32,
            font=Fonts.bold(11),
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            corner_radius=6, command=self.rechercher_article,
        )
        btn_recherche.grid(row=1, column=2, padx=4, pady=(0, 8))

        # — Unité (readonly) —
        ctk.CTkLabel(card, text="Unité", **lbl_kw).grid(
            row=0, column=3, padx=4, pady=(8, 0), sticky="w")
        self.entry_unite = ctk.CTkEntry(
            card, **entry_kw, width=120, state="readonly",
        )
        self.entry_unite.grid(row=1, column=3, padx=4, pady=(0, 8), sticky="ew")

        # — Quantité —
        ctk.CTkLabel(card, text="Quantité", **lbl_kw).grid(
            row=0, column=4, padx=4, pady=(8, 0), sticky="w")
        self.entry_quantite = ctk.CTkEntry(
            card, **entry_kw, width=110,
        )
        self.entry_quantite.grid(row=1, column=4, padx=4, pady=(0, 8), sticky="ew")

        # — Bouton Ajouter —
        ctk.CTkLabel(card, text=" ", **lbl_kw).grid(
            row=0, column=5, padx=(4, 10), pady=(8, 0))
        self.btn_ajouter = ctk.CTkButton(
            card, text="+ Ajouter", height=32, width=110,
            font=Fonts.bold(12),
            fg_color=Colors.SUCCESS_DARK, hover_color=Colors.INFO_DARK,
            corner_radius=6, command=self.ajouter_article,
        )
        self.btn_ajouter.grid(row=1, column=5, padx=(4, 10), pady=(0, 8))

    # ── Row 3 — Tableau Treeview ──────────────────────────────────────────────

    def _build_tree_zone(self):
        """
        Zone expansible (Row 3) : Treeview TTK avec style iJeery.
        En-tête MIDNIGHT, lignes alternées BG_CARD / BG_ROW_ALT.
        Style défini une seule fois (pas de reconfiguration à chaque chargement).
        """
        frame = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        frame.grid(row=3, column=0, sticky="nsew", padx=0, pady=(0, 2))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        # ── Style TTK ────────────────────────────────────────────────────────
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Transfert.Treeview",
            rowheight=22,
            font=('Segoe UI', 9),
            background=Colors.BG_CARD,
            foreground=Colors.TEXT_PRIMARY,
            fieldbackground=Colors.BG_CARD,
            borderwidth=0,
        )
        style.configure(
            "Transfert.Treeview.Heading",
            background=Colors.BG_HEADER,
            foreground=Colors.TEXT_ON_DARK,
            font=('Segoe UI', 9, 'bold'),
            relief="flat",
        )
        style.map(
            "Transfert.Treeview",
            background=[("selected", Colors.PRIMARY)],
            foreground=[("selected", Colors.TEXT_ON_DARK)],
        )

        # ── Colonnes ─────────────────────────────────────────────────────────
        columns = ("Code", "Article", "Unité", "Quantité", "Description")
        self.tree = ttk.Treeview(
            frame, columns=columns, show="headings",
            style="Transfert.Treeview", height=12,
        )

        self.tree.tag_configure("even", background=Colors.BG_CARD)
        self.tree.tag_configure("odd",  background=Colors.BG_ROW_ALT)

        col_config = {
            "Code":        (130, "w"),
            "Article":     (380, "w"),
            "Unité":       (130, "w"),
            "Quantité":    (120, "e"),
            "Description": (260, "w"),
        }
        for col, (w, anchor) in col_config.items():
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor=anchor)

        # Scrollbar CTk
        scrollbar = ctk.CTkScrollbar(frame, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 6), pady=6)

        # Bouton supprimer ligne (dans la zone tableau, aligné à gauche)
        self.btn_supprimer = ctk.CTkButton(
            frame, text="🗑 Supprimer ligne", height=30, width=160,
            font=Fonts.bold(11),
            fg_color=Colors.DANGER, hover_color=Colors.DANGER_DARK,
            corner_radius=6, command=self.supprimer_ligne,
        )
        self.btn_supprimer.grid(row=1, column=0, padx=6, pady=(0, 6), sticky="w")

    # ── Row 4 — Barre d'actions ───────────────────────────────────────────────

    def _build_actions_band(self):
        """
        Frame BG_PAGE (Row 4) : actions globales alignées gauche / droite.
        """
        bar = ctk.CTkFrame(self, fg_color=Colors.BG_PAGE, corner_radius=0)
        bar.grid(row=4, column=0, sticky="ew", padx=0, pady=(2, 0))
        bar.grid_columnconfigure(2, weight=1)  # espace élastique

        # — Nouveau (bleu) —
        self.btn_nouveau = ctk.CTkButton(
            bar, text="🆕 Nouveau", height=34,
            font=Fonts.bold(11),
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            corner_radius=6, command=self.nouveau_transfert,
        )
        self.btn_nouveau.grid(row=0, column=0, padx=(8, 4), pady=6)

        # — Charger Transfert (orange) —
        self.btn_charger = ctk.CTkButton(
            bar, text="📂 Charger Transfert", height=34,
            font=Fonts.bold(11),
            fg_color=Colors.WARNING, hover_color="#D68910",
            corner_radius=6, command=self.ouvrir_fenetre_chargement,
        )
        self.btn_charger.grid(row=0, column=1, padx=4, pady=6)

        # espace élastique — colonne 2

        # — Enregistrer (vert, droite) —
        self.btn_enregistrer = ctk.CTkButton(
            bar, text="💾 Enregistrer le Transfert", height=34,
            font=Fonts.bold(13),
            fg_color=Colors.SUCCESS_DARK, hover_color=Colors.INFO_DARK,
            corner_radius=8, command=self.enregistrer_transfert,
        )
        self.btn_enregistrer.grid(row=0, column=3, padx=(4, 8), pady=6, sticky="e")

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3 — CHARGEMENTS INITIAUX
    # ══════════════════════════════════════════════════════════════════════════

    def generer_reference(self):
        """
        Génère et affiche la prochaine référence de transfert (AAAA-TRA-NNNNN).
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        try:
            conn = self.get_connection()
            if not conn:
                return

            cur  = conn.cursor()
            annee = datetime.now().year

            cur.execute(
                """
                SELECT reftransfert FROM tb_transfert
                WHERE reftransfert LIKE %s
                ORDER BY reftransfert DESC LIMIT 1
                """,
                (f"{annee}-TRA-%",),
            )
            result = cur.fetchone()

            if result:
                parts = result[0].split('-')
                if len(parts) == 3 and parts[1] == 'TRA':
                    try:
                        nouveau_num = int(parts[2]) + 1
                    except ValueError:
                        nouveau_num = 1
                else:
                    nouveau_num = 1
            else:
                nouveau_num = 1

            reference = f"{annee}-TRA-{nouveau_num:05d}"

            self.entry_ref.configure(state="normal")
            self.entry_ref.delete(0, "end")
            self.entry_ref.insert(0, reference)
            self.entry_ref.configure(state="readonly")

            cur.close()
            conn.close()

        except Exception as e:
            MessageDialog("Erreur", f"Génération référence : {e}", type_='error')

    def charger_magasins(self):
        """
        Charge la liste des magasins dans les deux ComboBox.
        Sélectionne par défaut le magasin de l'utilisateur connecté.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        try:
            conn = self.get_connection()
            if not conn:
                return

            cur = conn.cursor()
            cur.execute(
                "SELECT idmag, designationmag FROM tb_magasin WHERE deleted=0"
            )
            magasins = cur.fetchall()

            self.magasins_data = {mag[1]: mag[0] for mag in magasins}
            mag_list           = list(self.magasins_data.keys())

            self.combo_mag_sortie.configure(values=mag_list)
            self.combo_mag_entree.configure(values=mag_list)

            if mag_list:
                # Magasin par défaut de l'utilisateur
                idmag_defaut = None
                cur.execute(
                    "SELECT idmag FROM tb_users WHERE iduser=%s LIMIT 1",
                    (self.user_id,),
                )
                row_user = cur.fetchone()
                if row_user:
                    idmag_defaut = row_user[0]

                nom_defaut = next(
                    (nom for id_, nom in magasins if id_ == idmag_defaut), None
                )
                if nom_defaut:
                    self.combo_mag_sortie.set(nom_defaut)
                    self.combo_mag_entree.set(nom_defaut)
                else:
                    self.combo_mag_sortie.set(mag_list[0])
                    self.combo_mag_entree.set(mag_list[0])

            cur.close()
            conn.close()

        except Exception as e:
            MessageDialog("Erreur", f"Chargement magasins : {e}", type_='error')

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 4 — RECHERCHE ET SÉLECTION D'ARTICLE
    # ══════════════════════════════════════════════════════════════════════════

    def rechercher_article(self):
        """
        Ouvre la fenêtre de recherche d'article.
        Utilise la requête consolidée (réservoir commun via qtunite) identique
        à page_venteParMsin / page_stock pour le calcul de stock.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        fen = ctk.CTkToplevel(self)
        fen.title("Rechercher un article pour le transfert")
        fen.geometry("1000x600")
        fen.grab_set()

        main_frame = ctk.CTkFrame(fen)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            main_frame, text="Sélectionner un article",
            font=Fonts.heading(16),
        ).pack(pady=(0, 10))

        # Barre de recherche
        search_frame = ctk.CTkFrame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(search_frame, text="🔍 Rechercher :").pack(side="left", padx=5)
        entry_search = ctk.CTkEntry(
            search_frame, placeholder_text="Code ou désignation…", width=300,
        )
        entry_search.pack(side="left", padx=5, fill="x", expand=True)

        # Treeview
        tree_frame = ctk.CTkFrame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))

        # Style TTK pour la fenêtre de recherche
        style = ttk.Style()
        style.configure(
            "Search.Treeview",
            rowheight=22, font=('Segoe UI', 8),
            background=Colors.BG_CARD, foreground=Colors.TEXT_PRIMARY,
            fieldbackground=Colors.BG_CARD, borderwidth=0,
        )
        style.configure(
            "Search.Treeview.Heading",
            background=Colors.BG_HEADER, foreground=Colors.TEXT_ON_DARK,
            font=('Segoe UI', 8, 'bold'), relief="flat",
        )

        colonnes = ("ID_Article", "ID_Unite", "Code", "Désignation", "Unité", "Stock", "Prix U.")
        tree = ttk.Treeview(
            tree_frame, columns=colonnes, show='headings',
            height=15, style="Search.Treeview",
        )
        tree.tag_configure("even", background=Colors.BG_CARD)
        tree.tag_configure("odd",  background=Colors.BG_ROW_ALT)

        nom_magasin_courant = (self.combo_mag_sortie.get() or "").strip()
        col_cfg = {
            "ID_Article": (0, False, "center"),
            "ID_Unite":   (0, False, "center"),
            "Code":       (120, True, "w"),
            "Désignation":(300, True, "w"),
            "Unité":      (80,  True, "w"),
            "Stock":      (100, True, "e"),
            "Prix U.":    (100, True, "e"),
        }
        for col, (w, stretch, anchor) in col_cfg.items():
            lbl = (f"Magasin {nom_magasin_courant}" if col == "Stock" and nom_magasin_courant else col)
            tree.heading(col, text=lbl)
            tree.column(col, width=w, stretch=stretch, anchor=anchor)

        scrollbar = ctk.CTkScrollbar(tree_frame, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ── Helpers ───────────────────────────────────────────────────────────

        def parser_nombre(texte):
            try:
                return float(str(texte).replace('.', '').replace(',', '.'))
            except Exception:
                return 0.0

        # ── Chargement des articles (requête consolidée) ──────────────────────

        def charger_articles(filtre=""):
            for item in tree.get_children():
                tree.delete(item)

            conn = self.get_connection()
            if not conn:
                return

            try:
                cur = conn.cursor()
                filtre_like = f"%{filtre}%"

                designationmag = (self.combo_mag_sortie.get() or "").strip()
                idmag_actif    = self.magasins_data.get(designationmag)
                tree.heading("Stock", text=f"Magasin {designationmag}" if designationmag else "Magasin")

                if idmag_actif is None:
                    return

                snapshot = StockSnapshot.build(int(idmag_actif))

                cur.execute(
                    """
                    SELECT
                        u.idarticle,
                        u.idunite,
                        u.codearticle,
                        a.designation,
                        u.designationunite,
                        COALESCE(p.prix, 0) AS prix_unitaire
                    FROM tb_unite u
                    INNER JOIN tb_article a ON a.idarticle = u.idarticle
                    LEFT JOIN (
                        SELECT idarticle, idunite, prix
                        FROM (
                            SELECT idarticle, idunite, prix,
                                   ROW_NUMBER() OVER (
                                       PARTITION BY idarticle, idunite
                                       ORDER BY id DESC
                                   ) AS rn
                            FROM tb_prix
                            WHERE deleted = 0
                        ) x
                        WHERE x.rn = 1
                    ) p ON p.idarticle = u.idarticle AND p.idunite = u.idunite
                    WHERE a.deleted = 0
                      AND COALESCE(u.deleted, 0) = 0
                      AND (u.codearticle ILIKE %s OR a.designation ILIKE %s)
                    ORDER BY a.designation ASC, u.codearticle ASC, u.idunite ASC
                    """,
                    (filtre_like, filtre_like),
                )

                for idx, row in enumerate(cur.fetchall()):
                    stock_total = snapshot.stock_unite(row[0], row[1])
                    tree.insert(
                        '',
                        'end',
                        values=(
                            row[0], row[1],
                            row[2] or "", row[3] or "", row[4] or "",
                            format_nombre_auto(stock_total),
                            format_nombre_auto(row[5]),
                        ),
                        tags=("even" if idx % 2 == 0 else "odd",),
                    )

            except Exception as e:
                MessageDialog("Erreur", f"Chargement articles : {e}", type_='error')
            finally:
                if 'cur' in locals() and cur:
                    cur.close()
                if conn:
                    conn.close()

        def valider_selection():
            selection = tree.selection()
            if not selection:
                MessageDialog("Attention", "Sélectionnez un article.", type_='warning')
                return

            values = tree.item(selection[0]).get('values', [])
            if len(values) < 7:
                MessageDialog("Erreur", "Données incomplètes.", type_='error')
                return

            self.article_selectionne = {
                'id':                values[0],
                'idunite':           values[1],
                'code':              values[2] or "N/A",
                'nom':               values[3] or "N/A",
                'unite':             values[4] or "N/A",
                'stock_disponible':  parser_nombre(values[5]),
                'prix_unitaire':     parser_nombre(values[6]),
            }

            for entry, key in [
                (self.entry_code_article, 'code'),
                (self.entry_nom_article,  'nom'),
                (self.entry_unite,        'unite'),
            ]:
                entry.configure(state="normal")
                entry.delete(0, "end")
                entry.insert(0, self.article_selectionne[key])
                entry.configure(state="readonly")

            fen.destroy()

        entry_search.bind('<KeyRelease>', lambda e: charger_articles(entry_search.get()))
        tree.bind('<Double-Button-1>', lambda e: valider_selection())

        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x")
        ctk.CTkButton(
            btn_frame, text="❌ Annuler", command=fen.destroy,
            fg_color=Colors.DANGER, hover_color=Colors.DANGER_DARK,
        ).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(
            btn_frame, text="✅ Valider", command=valider_selection,
            fg_color=Colors.SUCCESS_DARK, hover_color=Colors.INFO_DARK,
        ).pack(side="right", padx=5, pady=5)

        charger_articles()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 5 — CALCUL DE STOCK CONSOLIDÉ
    # ══════════════════════════════════════════════════════════════════════════

    def calculer_stock_article(self, idarticle, idunite_cible, idmag=None):
        """
        Calcul consolidé du stock via réservoir commun (qtunite).
        Identique à page_venteParMsin et page_stock.py.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        conn = self.get_connection()
        if not conn:
            return 0

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT idunite, codearticle, COALESCE(qtunite,1)
                FROM tb_unite WHERE idarticle=%s
                """,
                (idarticle,),
            )
            unites_liees = cursor.fetchall()

            qtunite_affichage = 1
            for idu, code, qt_u in unites_liees:
                if idu == idunite_cible:
                    qtunite_affichage = qt_u if qt_u > 0 else 1
                    break

            total_stock_global_base = 0.0

            for idu_boucle, code_boucle, qtunite_boucle in unites_liees:

                def qry(sql, params):
                    cursor.execute(sql, params)
                    return cursor.fetchone()[0] or 0

                # Réceptions
                q = "SELECT COALESCE(SUM(qtlivrefrs),0) FROM tb_livraisonfrs WHERE idarticle=%s AND idunite=%s AND deleted=0"
                p = [idarticle, idu_boucle]
                if idmag: q += " AND idmag=%s"; p.append(idmag)
                receptions = qry(q, p)

                # Ventes
                q = "SELECT COALESCE(SUM(qtvente),0) FROM tb_ventedetail WHERE idarticle=%s AND idunite=%s AND deleted=0"
                p = [idarticle, idu_boucle]
                if idmag: q += " AND idmag=%s"; p.append(idmag)
                ventes = qry(q, p)

                # Transferts entrants
                q = "SELECT COALESCE(SUM(qttransfert),0) FROM tb_transfertdetail WHERE idarticle=%s AND idunite=%s AND deleted=0"
                p = [idarticle, idu_boucle]
                if idmag: q += " AND idmagentree=%s"; p.append(idmag)
                t_in = qry(q, p)

                # Transferts sortants
                q = "SELECT COALESCE(SUM(qttransfert),0) FROM tb_transfertdetail WHERE idarticle=%s AND idunite=%s AND deleted=0"
                p = [idarticle, idu_boucle]
                if idmag: q += " AND idmagsortie=%s"; p.append(idmag)
                t_out = qry(q, p)

                # Inventaires
                q = "SELECT COALESCE(SUM(qtinventaire),0) FROM tb_inventaire WHERE codearticle=%s"
                p = [code_boucle]
                if idmag: q += " AND idmag=%s"; p.append(idmag)
                inv = qry(q, p)

                # Avoirs
                q = """SELECT COALESCE(SUM(ad.qtavoir),0)
                       FROM tb_avoirdetail ad INNER JOIN tb_avoir a ON ad.idavoir=a.id
                       WHERE ad.idarticle=%s AND ad.idunite=%s AND a.deleted=0 AND ad.deleted=0"""
                p = [idarticle, idu_boucle]
                if idmag: q += " AND ad.idmag=%s"; p.append(idmag)
                avoirs = qry(q, p)

                # Consommation interne
                q = "SELECT COALESCE(SUM(qtconsomme),0) FROM tb_consommationinterne_details WHERE idarticle=%s AND idunite=%s"
                p = [idarticle, idu_boucle]
                if idmag: q += " AND idmag=%s"; p.append(idmag)
                consomm = qry(q, p)

                # Échange entrant
                q = "SELECT COALESCE(SUM(quantite_entree),0) FROM tb_detailchange_entree WHERE idarticle=%s AND idunite=%s"
                p = [idarticle, idu_boucle]
                if idmag: q += " AND idmagasin=%s"; p.append(idmag)
                echange_in = qry(q, p)

                # Échange sortant
                q = "SELECT COALESCE(SUM(quantite_sortie),0) FROM tb_detailchange_sortie WHERE idarticle=%s AND idunite=%s"
                p = [idarticle, idu_boucle]
                if idmag: q += " AND idmagasin=%s"; p.append(idmag)
                echange_out = qry(q, p)

                solde = (receptions + t_in + inv + avoirs + echange_in
                         - ventes - t_out - consomm - echange_out)
                total_stock_global_base += solde * qtunite_boucle

            return max(0, total_stock_global_base / qtunite_affichage)

        except Exception as e:
            print(f"Erreur calcul stock : {e}")
            return 0
        finally:
            cursor.close()
            conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 6 — GESTION DES LIGNES DU TRANSFERT
    # ══════════════════════════════════════════════════════════════════════════

    def ajouter_article(self):
        """
        Valide la saisie et ajoute une ligne au transfert.
        Vérifie le stock disponible avant d'autoriser l'ajout.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        if not hasattr(self, 'article_selectionne'):
            MessageDialog("Attention", "Sélectionnez un article.", type_='warning')
            return

        if not self.article_selectionne.get('idunite'):
            MessageDialog("Attention", "L'article n'a pas d'unité.", type_='warning')
            return

        try:
            quantite_saisie = float(self.entry_quantite.get())
            if quantite_saisie <= 0:
                MessageDialog("Attention", "La quantité doit être > 0.", type_='warning')
                return
        except ValueError:
            MessageDialog("Attention", "Quantité invalide.", type_='warning')
            return

        mag_sortie_nom = self.combo_mag_sortie.get()
        if not mag_sortie_nom:
            MessageDialog("Attention", "Sélectionnez le magasin de sortie.", type_='warning')
            return

        stock_actuel = self.article_selectionne['stock_disponible']

        if quantite_saisie > stock_actuel:
            MessageDialog(
                "Stock Insuffisant",
                f"Transfert impossible.\n\n"
                f"Article : {self.article_selectionne['nom']}\n"
                f"Stock disponible : {stock_actuel}\n"
                f"Quantité demandée : {quantite_saisie}",
                type_='error',
            )
            return

        description_ligne = (self.entry_description.get() or "").strip()

        # Insertion dans le Treeview avec alternance de couleur
        idx = len(self.tree.get_children())
        self.tree.insert("", "end", values=(
            self.article_selectionne['code'],
            self.article_selectionne['nom'],
            self.article_selectionne['unite'],
            quantite_saisie,
            description_ligne,
        ), tags=("even" if idx % 2 == 0 else "odd",))

        self.articles_transfert.append({
            'idarticle':   self.article_selectionne['id'],
            'idunite':     self.article_selectionne['idunite'],
            'code':        self.article_selectionne['code'],
            'nom':         self.article_selectionne['nom'],
            'unite':       self.article_selectionne['unite'],
            'quantite':    quantite_saisie,
            'description': description_ligne,
        })

        # Vider la description (par ligne) et réinitialiser les champs article
        #self.entry_description.delete(0, "end")
        self.reinitialiser_champs_article()

    def reinitialiser_champs_article(self):
        """Remet à blanc les champs de saisie article après un ajout."""
        for entry in (self.entry_code_article, self.entry_nom_article, self.entry_unite):
            entry.configure(state="normal")
            entry.delete(0, "end")
            entry.configure(state="readonly")

        self.entry_quantite.delete(0, "end")

        if hasattr(self, 'article_selectionne'):
            del self.article_selectionne

    def supprimer_ligne(self):
        """Supprime la ligne sélectionnée du Treeview et de la liste interne."""
        selection = self.tree.selection()
        if selection:
            index = self.tree.index(selection[0])
            self.tree.delete(selection[0])
            del self.articles_transfert[index]

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 7 — ENREGISTREMENT DU TRANSFERT
    # ══════════════════════════════════════════════════════════════════════════

    def enregistrer_transfert(self):
        """
        Enregistre ou met à jour le transfert dans tb_transfert + tb_transfertdetail.
        Mode INSERT si nouveau, mode UPDATE si idtransfert_en_cours est défini.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        if not self.articles_transfert:
            MessageDialog("Attention", "Aucun article dans le transfert.", type_='warning')
            return

        mag_sortie = self.combo_mag_sortie.get()
        mag_entree = self.combo_mag_entree.get()

        if not mag_sortie or not mag_entree:
            MessageDialog("Attention", "Sélectionnez les deux magasins.", type_='warning')
            return

        if mag_sortie == mag_entree:
            MessageDialog("Attention", "Les magasins doivent être différents.", type_='warning')
            return

        try:
            conn = self.get_connection()
            if not conn:
                return

            cur = conn.cursor()

            # ── MODE MODIFICATION (UPDATE) ────────────────────────────────────
            if getattr(self, 'idtransfert_en_cours', None) is not None:
                idtransfert = self.idtransfert_en_cours

                cur.execute(
                    """
                    UPDATE tb_transfert
                    SET idmagsortie=%s, idmagentree=%s, dateregistre=%s, description=NULL
                    WHERE idtransfert=%s
                    """,
                    (self.magasins_data[mag_sortie], self.magasins_data[mag_entree],
                     self.entry_date.get(), idtransfert),
                )

                cur.execute(
                    "UPDATE tb_transfertdetail SET deleted=1 WHERE idtransfert=%s AND deleted=0",
                    (idtransfert,),
                )

                for art in self.articles_transfert:
                    cur.execute(
                        """
                        INSERT INTO tb_transfertdetail
                        (idarticle, idunite, qttransfert, qttransfertsortie, qttransfertentree,
                         deleted, idtransfert, idmagsortie, idmagentree, description)
                        VALUES (%s,%s,%s,%s,%s,0,%s,%s,%s,%s)
                        """,
                        (art['idarticle'], art['idunite'], art['quantite'],
                         art['quantite'], art['quantite'], idtransfert,
                         self.magasins_data[mag_sortie], self.magasins_data[mag_entree],
                         art.get('description', '')),
                    )

                conn.commit()
                cur.close()
                conn.close()

                MessageDialog("Succès", f"Transfert « {self.entry_ref.get()} » mis à jour.", type_='info')
                self.imprimer_transfert(idtransfert)
                self.nouveau_transfert()
                return

            # ── MODE CRÉATION (INSERT) ────────────────────────────────────────
            cur.execute(
                """
                INSERT INTO tb_transfert
                (reftransfert, iduser, idmagsortie, idmagentree, dateregistre, description, deleted)
                VALUES (%s,%s,%s,%s,%s,%s,0)
                RETURNING idtransfert
                """,
                (self.entry_ref.get(), self.user_id,
                 self.magasins_data[mag_sortie], self.magasins_data[mag_entree],
                 self.entry_date.get(), None),
            )
            idtransfert = cur.fetchone()[0]

            for art in self.articles_transfert:
                cur.execute(
                    """
                    INSERT INTO tb_transfertdetail
                    (idarticle, idunite, qttransfert, qttransfertsortie, qttransfertentree,
                     deleted, idtransfert, idmagsortie, idmagentree, description)
                    VALUES (%s,%s,%s,%s,%s,0,%s,%s,%s,%s)
                    """,
                    (art['idarticle'], art['idunite'], art['quantite'],
                     art['quantite'], art['quantite'], idtransfert,
                     self.magasins_data[mag_sortie], self.magasins_data[mag_entree],
                     art.get('description', '')),
                )

            conn.commit()
            cur.close()
            conn.close()

            MessageDialog("Succès", "Transfert enregistré avec succès.", type_='info')
            self.imprimer_transfert(idtransfert)
            self.nouveau_transfert()

        except Exception as e:
            MessageDialog("Erreur", f"Enregistrement : {e}", type_='error')

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 8 — IMPRESSION PDF
    # ══════════════════════════════════════════════════════════════════════════

    def imprimer_transfert(self, idtransfert):
        """
        Génère et ouvre le PDF du bon de transfert via EtatPDFMouvements.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        try:
            conn = self.get_connection()
            if not conn:
                return

            cur = conn.cursor()

            cur.execute(
                """
                SELECT t.idtransfert, t.reftransfert, t.dateregistre, t.description,
                       COALESCE(u.username,'Utilisateur'),
                       COALESCE(ms.designationmag,''), COALESCE(me.designationmag,'')
                FROM tb_transfert t
                LEFT JOIN tb_users   u  ON t.iduser      = u.iduser
                LEFT JOIN tb_magasin ms ON t.idmagsortie = ms.idmag
                LEFT JOIN tb_magasin me ON t.idmagentree = me.idmag
                WHERE t.idtransfert=%s
                """,
                (idtransfert,),
            )
            transfert = cur.fetchone()

            cur.execute(
                """
                SELECT u.codearticle, a.designation, u.designationunite,
                       td.qttransfert, td.description
                FROM tb_transfertdetail td
                LEFT JOIN tb_article a ON td.idarticle = a.idarticle
                LEFT JOIN tb_unite   u ON td.idunite   = u.idunite
                WHERE td.idtransfert=%s AND td.deleted=0
                """,
                (idtransfert,),
            )
            details = cur.fetchall()
            cur.close()
            conn.close()

            if not transfert:
                MessageDialog("Attention", "Transfert introuvable.", type_='warning')
                return

            reftransfert    = transfert[1]
            date_operation  = (
                transfert[2].strftime('%d/%m/%Y')
                if transfert[2] else datetime.now().strftime('%d/%m/%Y')
            )
            description = transfert[3] or ""
            username    = transfert[4] or "Utilisateur"
            mag_sortie  = transfert[5] or ""
            mag_entree  = transfert[6] or ""

            columns = ("Code", "Désignation", "Unité", "Quantité", "Mouvement", "Description")
            mouvement_label = f"{mag_sortie} -> {mag_entree}".strip(" ->")
            rows = [
                (str(code or ""), str(desig or ""), str(unite or ""),
                 qte or 0, mouvement_label, str(desc or ""))
                for code, desig, unite, qte, desc in details
            ]
            table_data = (columns, rows)
            filename   = f"Transfert_{reftransfert.replace('-','_')}.pdf"

            try:
                from EtatsPDF_Mouvements import EtatPDFMouvements

                etat = EtatPDFMouvements()
                try:
                    etat.connect_db()
                except Exception:
                    pass

                result = etat._build_pdf_a5(
                    output_path=filename,
                    titre_entete="BON DE TRANSFERT",
                    reference=reftransfert,
                    date_operation=date_operation,
                    magasin=f"{mag_sortie} -> {mag_entree}",
                    operateur=username,
                    table_data=table_data,
                    description=description,
                    responsable_1="Le Magasinier",
                    responsable_2="Le Contrôleur",
                )

                try:
                    etat.close_db()
                except Exception:
                    pass

                if result:
                    try:
                        os.startfile(filename)
                    except Exception:
                        pass
                return result

            except Exception as e:
                MessageDialog("Erreur PDF", f"Génération PDF : {e}", type_='error')
                return None

        except Exception as e:
            MessageDialog("Erreur", f"Impression : {e}", type_='error')

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 9 — ACTIVATION / DÉSACTIVATION DE L'ÉDITION
    # ══════════════════════════════════════════════════════════════════════════

    def desactiver_edition(self):
        """Verrouille l'interface en mode lecture seule (transfert chargé)."""
        for w in (self.entry_date, self.entry_description,
                  self.combo_mag_sortie, self.combo_mag_entree):
            w.configure(state="readonly")
        self.btn_ajouter.configure(state="disabled")
        self.btn_supprimer.configure(state="disabled")
        self.btn_enregistrer.configure(state="disabled")

    def activer_edition(self):
        """Déverrouille l'interface pour la saisie (nouveau transfert ou modification)."""
        for w in (self.entry_date, self.entry_description,
                  self.combo_mag_sortie, self.combo_mag_entree):
            w.configure(state="normal")
        self.btn_ajouter.configure(state="normal")
        self.btn_supprimer.configure(state="normal")
        self.btn_enregistrer.configure(state="normal")

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 10 — FENÊTRE DE CHARGEMENT D'UN TRANSFERT EXISTANT
    # ══════════════════════════════════════════════════════════════════════════

    def ouvrir_fenetre_chargement(self):
        """
        Ouvre une fenêtre modale pour rechercher, charger, modifier
        ou supprimer un transfert existant.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        load_win = ctk.CTkToplevel(self)
        load_win.title("Charger un Transfert Existant")
        load_win.geometry("950x680")
        load_win.grab_set()

        # ── Barre de recherche ────────────────────────────────────────────────
        search_frame = ctk.CTkFrame(load_win, fg_color="transparent")
        search_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            search_frame, text="Référence / Magasin :",
            font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY,
        ).pack(side="left", padx=5)

        entry_search = ctk.CTkEntry(
            search_frame, width=300,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            height=32, corner_radius=6,
        )
        entry_search.pack(side="left", padx=5)

        ctk.CTkButton(
            search_frame, text="Rechercher", height=32,
            font=Fonts.bold(11),
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            corner_radius=6,
            command=lambda: charger_transferts(entry_search.get()),
        ).pack(side="left", padx=5)

        # ── Treeview des transferts ───────────────────────────────────────────
        tree_frame = ctk.CTkFrame(load_win, fg_color=Colors.BG_CARD, corner_radius=0)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        style = ttk.Style()
        style.configure(
            "LoadTrf.Treeview",
            rowheight=22, font=('Segoe UI', 9),
            background=Colors.BG_CARD, foreground=Colors.TEXT_PRIMARY,
            fieldbackground=Colors.BG_CARD, borderwidth=0,
        )
        style.configure(
            "LoadTrf.Treeview.Heading",
            background=Colors.BG_HEADER, foreground=Colors.TEXT_ON_DARK,
            font=('Segoe UI', 9, 'bold'), relief="flat",
        )

        columns = ("ID", "Référence", "Date", "Mag. Sortie", "Mag. Entrée",
                   "Utilisateur", "Description")
        self.tree_transferts = ttk.Treeview(
            tree_frame, columns=columns, show="headings",
            style="LoadTrf.Treeview",
        )
        self.tree_transferts["displaycolumns"] = (
            "Référence", "Date", "Mag. Sortie", "Mag. Entrée",
            "Utilisateur", "Description",
        )

        col_w = {
            "ID": (0, False), "Référence": (150, True), "Date": (150, True),
            "Mag. Sortie": (150, True), "Mag. Entrée": (150, True),
            "Utilisateur": (100, True), "Description": (260, True),
        }
        for col, (w, stretch) in col_w.items():
            self.tree_transferts.heading(col, text=col)
            self.tree_transferts.column(col, width=w, stretch=stretch)

        sb = ctk.CTkScrollbar(tree_frame, command=self.tree_transferts.yview)
        self.tree_transferts.configure(yscrollcommand=sb.set)
        self.tree_transferts.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        sb.grid(row=0, column=1, sticky="ns", padx=(0, 6), pady=6)

        # ── Boutons d'action ──────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(load_win, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        btn_charger = ctk.CTkButton(
            btn_frame, text="📂 Charger", width=140, height=34,
            font=Fonts.bold(11),
            fg_color=Colors.SUCCESS_DARK, hover_color=Colors.INFO_DARK,
            corner_radius=6, state="disabled",
            command=lambda: action_charger(),
        )
        btn_charger.pack(side="left", padx=5, pady=5)

        btn_modifier = ctk.CTkButton(
            btn_frame, text="✏ Modifier", width=140, height=34,
            font=Fonts.bold(11),
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            corner_radius=6, state="disabled",
            command=lambda: action_modifier(),
        )
        btn_modifier.pack(side="left", padx=5, pady=5)

        btn_suppr = ctk.CTkButton(
            btn_frame, text="🗑 Supprimer", width=140, height=34,
            font=Fonts.bold(11),
            fg_color=Colors.DANGER, hover_color=Colors.DANGER_DARK,
            corner_radius=6, state="disabled",
            command=lambda: action_supprimer(),
        )
        btn_suppr.pack(side="left", padx=5, pady=5)

        # ── Logique de chargement ─────────────────────────────────────────────

        def charger_transferts(filtre=""):
            self.tree_transferts.delete(*self.tree_transferts.get_children())
            mettre_a_jour_boutons()

            conn = self.get_connection()
            if not conn:
                return
            try:
                cur = conn.cursor()
                query = """
                    SELECT t.idtransfert, t.reftransfert, t.dateregistre,
                           ms.designationmag, me.designationmag, u.username,
                           COALESCE(
                               NULLIF((
                                   SELECT string_agg(NULLIF(TRIM(td.description),''),', ' ORDER BY td.id)
                                   FROM tb_transfertdetail td
                                   WHERE td.idtransfert=t.idtransfert AND td.deleted=0
                               ),''),
                               'Description non précisée'
                           ) AS description_lignes
                    FROM tb_transfert t
                    LEFT JOIN tb_magasin ms ON t.idmagsortie=ms.idmag
                    LEFT JOIN tb_magasin me ON t.idmagentree=me.idmag
                    LEFT JOIN tb_users   u  ON t.iduser=u.iduser
                    WHERE t.deleted=0
                """
                params = []
                if filtre:
                    query += """ AND (LOWER(t.reftransfert) LIKE LOWER(%s)
                                   OR LOWER(ms.designationmag) LIKE LOWER(%s)
                                   OR LOWER(me.designationmag) LIKE LOWER(%s))"""
                    params.extend([f"%{filtre}%"] * 3)
                query += " ORDER BY t.dateregistre DESC"

                cur.execute(query, tuple(params))
                for trf in cur.fetchall():
                    self.tree_transferts.insert("", "end", values=trf)

            except Exception as e:
                MessageDialog("Erreur", f"Chargement transferts : {e}", type_='error')
            finally:
                if 'cur' in locals() and cur: cur.close()
                if conn: conn.close()

        def mettre_a_jour_boutons(*args):
            etat = "normal" if self.tree_transferts.selection() else "disabled"
            btn_charger.configure(state=etat)
            btn_modifier.configure(state=etat)
            btn_suppr.configure(state=etat)

        self.tree_transferts.bind("<<TreeviewSelect>>", mettre_a_jour_boutons)

        def action_charger():
            sel = self.tree_transferts.selection()
            if not sel:
                return
            id_transfert = self.tree_transferts.item(sel[0])['values'][0]
            self.charger_transfert_selectionne(id_transfert)
            load_win.destroy()

        def action_modifier():
            sel = self.tree_transferts.selection()
            if not sel:
                return
            vals = self.tree_transferts.item(sel[0])['values']
            self.modifier_transfert(vals[0], vals[1])
            load_win.destroy()

        def action_supprimer():
            sel = self.tree_transferts.selection()
            if not sel:
                return
            vals          = self.tree_transferts.item(sel[0])['values']
            id_transfert  = vals[0]
            ref_transfert = vals[1]

            confirm = YesNoDialog(
                "Confirmation suppression",
                f"Supprimer le transfert « {ref_transfert} » ?\n"
                "Cette action est irréversible.",
            )
            if not confirm.result:
                return

            try:
                conn = self.get_connection()
                if not conn:
                    return
                cur = conn.cursor()
                cur.execute(
                    "UPDATE tb_transfertdetail SET deleted=1 WHERE idtransfert=%s AND deleted=0",
                    (id_transfert,),
                )
                cur.execute(
                    "UPDATE tb_transfert SET deleted=1 WHERE idtransfert=%s",
                    (id_transfert,),
                )
                conn.commit()
                cur.close()
                conn.close()
                MessageDialog("Supprimé", f"Transfert « {ref_transfert} » supprimé.", type_='info')
                charger_transferts(entry_search.get())
            except Exception as e:
                MessageDialog("Erreur", f"Suppression : {e}", type_='error')

        entry_search.bind("<Return>", lambda e: charger_transferts(entry_search.get()))
        self.tree_transferts.bind("<Double-1>", lambda e: action_charger())

        charger_transferts()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 11 — CHARGEMENT ET MODIFICATION D'UN TRANSFERT
    # ══════════════════════════════════════════════════════════════════════════

    def charger_transfert_selectionne(self, idtransfert):
        """
        Charge un transfert en MODE LECTURE SEULE.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        try:
            conn = self.get_connection()
            if not conn:
                return

            cur = conn.cursor()
            cur.execute(
                """
                SELECT t.reftransfert, t.dateregistre, t.description,
                       ms.designationmag, me.designationmag, t.idmagsortie, t.idmagentree
                FROM tb_transfert t
                LEFT JOIN tb_magasin ms ON t.idmagsortie=ms.idmag
                LEFT JOIN tb_magasin me ON t.idmagentree=me.idmag
                WHERE t.idtransfert=%s
                """,
                (idtransfert,),
            )
            transfert = cur.fetchone()

            if not transfert:
                MessageDialog("Attention", "Transfert non trouvé.", type_='warning')
                cur.close(); conn.close()
                return

            self.nouveau_transfert(is_loading=True)

            self.entry_ref.configure(state="normal")
            self.entry_ref.delete(0, "end")
            self.entry_ref.insert(0, transfert[0])
            self.entry_ref.configure(state="readonly")

            self.entry_date.delete(0, "end")
            self.entry_date.insert(0, str(transfert[1]))
            self.entry_description.delete(0, "end")
            self.entry_description.insert(0, transfert[2] or '')
            self.combo_mag_sortie.set(transfert[3])
            self.combo_mag_entree.set(transfert[4])

            cur.execute(
                """
                SELECT td.idarticle, td.idunite, u.codearticle, a.designation,
                       u.designationunite, td.qttransfert, td.description
                FROM tb_transfertdetail td
                LEFT JOIN tb_article a ON td.idarticle=a.idarticle
                LEFT JOIN tb_unite   u ON td.idunite=u.idunite
                WHERE td.idtransfert=%s AND td.deleted=0
                """,
                (idtransfert,),
            )
            details = cur.fetchall()

            self.articles_transfert = []
            for idx, det in enumerate(details):
                self.tree.insert("", "end", values=(det[2], det[3], det[4], det[5], det[6] or ""),
                                 tags=("even" if idx % 2 == 0 else "odd",))
                self.articles_transfert.append({
                    'idarticle': det[0], 'idunite': det[1],
                    'code': det[2], 'nom': det[3], 'unite': det[4],
                    'quantite': det[5], 'description': det[6] or "",
                })

            MessageDialog("Succès", f"Transfert {transfert[0]} chargé. Mode Lecture Seule.", type_='info')
            self.desactiver_edition()

            cur.close(); conn.close()

        except Exception as e:
            MessageDialog("Erreur", f"Chargement transfert : {e}", type_='error')

    def modifier_transfert(self, idtransfert, ref_transfert):
        """
        Charge un transfert en MODE ÉDITION (enregistrement → UPDATE).
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        try:
            conn = self.get_connection()
            if not conn:
                return

            cur = conn.cursor()
            cur.execute(
                """
                SELECT t.reftransfert, t.dateregistre, t.description,
                       ms.designationmag, me.designationmag, t.idmagsortie, t.idmagentree
                FROM tb_transfert t
                LEFT JOIN tb_magasin ms ON t.idmagsortie=ms.idmag
                LEFT JOIN tb_magasin me ON t.idmagentree=me.idmag
                WHERE t.idtransfert=%s
                """,
                (idtransfert,),
            )
            transfert = cur.fetchone()

            if not transfert:
                MessageDialog("Attention", "Transfert non trouvé.", type_='warning')
                cur.close(); conn.close()
                return

            self.nouveau_transfert(is_loading=True)

            self.entry_ref.configure(state="normal")
            self.entry_ref.delete(0, "end")
            self.entry_ref.insert(0, transfert[0])
            self.entry_ref.configure(state="readonly")

            self.entry_date.delete(0, "end")
            self.entry_date.insert(0, str(transfert[1]))
            self.entry_description.delete(0, "end")
            self.entry_description.insert(0, transfert[2] or '')
            self.combo_mag_sortie.set(transfert[3])
            self.combo_mag_entree.set(transfert[4])

            cur.execute(
                """
                SELECT td.idarticle, td.idunite, u.codearticle, a.designation,
                       u.designationunite, td.qttransfert, td.description
                FROM tb_transfertdetail td
                LEFT JOIN tb_article a ON td.idarticle=a.idarticle
                LEFT JOIN tb_unite   u ON td.idunite=u.idunite
                WHERE td.idtransfert=%s AND td.deleted=0
                """,
                (idtransfert,),
            )
            details = cur.fetchall()

            self.articles_transfert = []
            for idx, det in enumerate(details):
                self.tree.insert("", "end", values=(det[2], det[3], det[4], det[5], det[6] or ""),
                                 tags=("even" if idx % 2 == 0 else "odd",))
                self.articles_transfert.append({
                    'idarticle': det[0], 'idunite': det[1],
                    'code': det[2], 'nom': det[3], 'unite': det[4],
                    'quantite': det[5], 'description': det[6] or "",
                })

            cur.close(); conn.close()

            # Activer l'édition et mémoriser l'id pour le UPDATE
            self.activer_edition()
            self.idtransfert_en_cours = idtransfert

            MessageDialog(
                "Mode Modification",
                f"Transfert « {ref_transfert} » chargé en mode modification.\n"
                "Modifiez les articles / quantités / magasins, puis Enregistrer.",
                type_='info',
            )

        except Exception as e:
            MessageDialog("Erreur", f"Modification transfert : {e}", type_='error')

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 12 — RÉINITIALISATION FORMULAIRE
    # ══════════════════════════════════════════════════════════════════════════

    def nouveau_transfert(self, is_loading: bool = False):
        """
        Remet le formulaire à zéro.
        is_loading=True : ne génère pas de nouvelle référence (chargement en cours).
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        # Vider les champs texte
        self.entry_date.delete(0, "end")
        self.entry_date.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.entry_description.delete(0, "end")
        self.entry_quantite.delete(0, "end")

        # Réinitialiser article
        for entry in (self.entry_code_article, self.entry_nom_article, self.entry_unite):
            entry.configure(state="normal")
            entry.delete(0, "end")
            entry.configure(state="readonly")

        # Vider le Treeview
        self.tree.delete(*self.tree.get_children())
        self.articles_transfert = []

        if not is_loading:
            # Nouveau transfert réel → nouvelle référence + édition active
            self.generer_reference()
            self.activer_edition()
            self.idtransfert_en_cours = None


# ==============================================================================
# POINT D'ENTRÉE AUTONOME (test unitaire)
# ==============================================================================

if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root    = ctk.CTk()
    root.title("iJeery — Transfert de Stock (test)")
    root.geometry("1300x800")

    app = PageTransfert(root, user_id=1)
    app.pack(fill="both", expand=True)

    root.mainloop()

