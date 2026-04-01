# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    iJeery — pages/page_avoir.py                             ║
║                    Gestion des Avoirs (Retours clients)                     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  REFONTE UI — Mars 2026                                                      ║
║  Structure identique à page_venteParMsin :                                   ║
║    Row 0 — Bandeau en-tête (N° Avoir | Date | Client + loupe | Charger)     ║
║    Row 1 — Désignation (ligne pleine)                                        ║
║    Row 2 — Bandeau saisie article (Article | Rechercher | Qté | PU | Ajouter)║
║    Row 3 — Tableau détails TTK Treeview (weight=1 → expansible)             ║
║    Row 4 — Zone totaux (Lettres gauche | Total Ar + FMG droite)             ║
║    Row 5 — Barre d'actions                                                  ║
║                                                                              ║
║  Logique métier : 100% INCHANGÉE — seul setup_ui() → _setup_ui() est refait ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import customtkinter as ctk
from tkinter import ttk
import psycopg2
import json
from datetime import datetime
import calendar                         # noqa: F401 — conservé pour compatibilité
from typing import Optional, Dict, Any, List
import traceback
import os
import sys
import textwrap
from decimal import Decimal, InvalidOperation

from resource_utils import get_config_path, safe_file_read
from app_theme import Colors, Fonts, styled

# ── Imports ReportLab (impression PDF) ───────────────────────────────────────
from reportlab.lib.pagesizes import A5, landscape
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as rl_canvas


# ==============================================================================
# UTILITAIRE : CONVERSION NOMBRE → LETTRES (FRANÇAIS)
# ==============================================================================

def nombre_en_lettres_fr(montant: float) -> str:
    """
    Convertit un montant numérique en sa représentation en lettres en français.
    Gère les Millions et les Milliers correctement.
    *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
    """
    from math import floor

    if montant is None:
        return ""

    try:
        montant = round(float(montant), 2)
    except ValueError:
        return ""

    unites        = ["", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf"]
    dix_a_dixneuf = ["dix", "onze", "douze", "treize", "quatorze", "quinze", "seize"]
    dizaines      = ["", "dix", "vingt", "trente", "quarante", "cinquante",
                     "soixante", "soixante", "quatre-vingt", "quatre-vingt"]

    def convertir_nombre_simple(n):
        if n == 0:
            return ""
        texte = []
        if n < 10:
            texte.append(unites[n])
        elif n < 17:
            texte.append(dix_a_dixneuf[n - 10])
        elif n < 20:
            texte.append("dix-" + unites[n - 10])
        elif n < 100:
            d = n // 10
            u = n % 10
            partie_dizaine = dizaines[d]
            if (d == 2 or d > 6) and u == 1:
                partie_dizaine += " et"
            texte.append(partie_dizaine)
            if u > 0:
                if d == 7 or d == 9:
                    texte.append("-" + convertir_nombre_simple(n - (d * 10)))
                else:
                    texte.append("-" + unites[u])
        return "".join(texte).replace("--", "-")

    def convertir_bloc(n):
        if n == 0:
            return ""
        if n < 100:
            return convertir_nombre_simple(n)
        texte = []
        c = n // 100
        r = n % 100
        if c == 1:
            texte.append("cent")
        else:
            texte.append(convertir_nombre_simple(c) + "-cent")
            if r == 0:
                texte[-1] += "s"
        if r > 0:
            texte.append("-" + convertir_bloc(r))
        return "".join(texte).replace("un-cent", "cent")

    entier   = floor(montant)
    centimes = int(round((montant - entier) * 100))

    million       = entier // 1_000_000
    mille_reste   = (entier % 1_000_000) // 1_000
    reste_unites  = entier % 1_000

    resultat = []

    if million > 0:
        lettres_million = convertir_bloc(million)
        bloc_million    = "million" + ("s" if million > 1 else "")
        resultat.append(f"{lettres_million} {bloc_million}")

    if mille_reste > 0:
        resultat.append(f"{convertir_bloc(mille_reste)} mille")

    if reste_unites > 0:
        resultat.append(convertir_bloc(reste_unites))

    if entier == 0 and centimes == 0 and not resultat:
        resultat.append("zéro")

    result_str = " ".join(resultat).strip().replace("  ", " ").replace("-", " ")
    if not result_str:
        result_str = "zéro"

    if centimes > 0:
        centime_lettres  = convertir_bloc(centimes).replace("-", " ")
        result_str += " et " + centime_lettres + " centimes"

    return result_str.capitalize().replace(" et-", " et ")


# ==============================================================================
# DIALOGUE DE CHOIX D'IMPRESSION
# ==============================================================================

class SimpleDialogWithChoice(ctk.CTkToplevel):
    """
    Dialogue modal pour choisir le format d'impression.
    *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
    """

    def __init__(self, master, title, message):
        super().__init__(master)
        self.title(title)
        self.transient(master)
        self.grab_set()

        self.result = None
        self.choice = ctk.StringVar(self, value="A5 PDF (Paysage)")

        ctk.CTkLabel(self, text=message, wraplength=350, justify="left").pack(
            pady=10, padx=20
        )

        frame_radio = ctk.CTkFrame(self)
        frame_radio.pack(pady=5, padx=20, fill="x")

        ctk.CTkRadioButton(
            frame_radio, text="A5 PDF (Paysage)",
            variable=self.choice, value="A5 PDF (Paysage)"
        ).pack(pady=5, padx=10, anchor="w")

        ctk.CTkRadioButton(
            frame_radio, text="Ticket de Caisse 80mm",
            variable=self.choice, value="Ticket 80mm"
        ).pack(pady=5, padx=10, anchor="w")

        frame_buttons = ctk.CTkFrame(self)
        frame_buttons.pack(pady=10, padx=20)

        ctk.CTkButton(
            frame_buttons, text="Annuler", command=self.cancel,
            fg_color=Colors.DANGER, hover_color=Colors.DANGER_DARK,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            frame_buttons, text="Imprimer", command=self.ok,
            fg_color=Colors.SUCCESS_DARK, hover_color=Colors.INFO_DARK,
        ).pack(side="right", padx=5)

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
# PAGE PRINCIPALE : PageAvoir
# ==============================================================================

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


class MessageDialog(ctk.CTkToplevel):
    """Dialogue personnalisé pour remplacer messagebox.showinfo/warning/error avec z-index élevé."""

    def __init__(self, title: str, message: str, type_: str = 'info'):
        super().__init__()
        self.title(title)
        self.geometry("400x180")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_CARD)

        # Centrer la fenêtre
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = 400
        window_height = 180
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Icône selon le type
        icon_text = "ℹ️" if type_ == 'info' else "⚠️" if type_ == 'warning' else "❌"
        icon_color = Colors.PRIMARY if type_ == 'info' else Colors.WARNING if type_ == 'warning' else Colors.DANGER

        ctk.CTkLabel(self, text=icon_text, font=Fonts.heading(24),
                     text_color=icon_color).pack(pady=(20, 5))

        ctk.CTkLabel(self, text=message, font=Fonts.body(12),
                     text_color=Colors.TEXT_PRIMARY, wraplength=350,
                     justify="center").pack(pady=(0, 20), padx=20)

        styled.button_success(self, text="OK", command=self.destroy,
                              width=100, height=36).pack(pady=(0, 14))

        self.grab_set()
        self.lift()
        self.focus_force()
        self.attributes('-topmost', True)
        self.wait_window()


class YesNoDialog(ctk.CTkToplevel):
    """Dialogue personnalisé pour remplacer messagebox.askyesno avec z-index élevé."""

    def __init__(self, title: str, message: str):
        super().__init__()
        self.title(title)
        self.geometry("400x180")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_CARD)
        self.result = False

        # Centrer la fenêtre
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = 400
        window_height = 180
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")

        ctk.CTkLabel(self, text="❓", font=Fonts.heading(24),
                     text_color=Colors.WARNING).pack(pady=(20, 5))

        ctk.CTkLabel(self, text=message, font=Fonts.body(12),
                     text_color=Colors.TEXT_PRIMARY, wraplength=350,
                     justify="center").pack(pady=(0, 20), padx=20)

        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(pady=(0, 14))
        styled.button_danger(bf, text="Non", command=self._no,
                             width=100, height=36).pack(side="left", padx=10)
        styled.button_success(bf, text="Oui", command=self._yes,
                              width=100, height=36).pack(side="right", padx=10)

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


class PageAvoir(ctk.CTkFrame):
    """
    Page de gestion des Avoirs (retours clients).

    Architecture UI (identique à page_venteParMsin) :
    ┌─────────────────────────────────────────────────────────┐
    │ Row 0 — En-tête : N° Avoir | Date | Client 🔎 | 📂      │  Card BG_CARD
    │ Row 1 — Désignation (champ pleine largeur)              │  Card BG_CARD
    │ Row 2 — Saisie article : Article | 🔎 | Qté | PU | ➕   │  Card BG_CARD
    │ Row 3 — Tableau Treeview (expansible)                   │  Frame MIDNIGHT header
    │ Row 4 — Totaux : lettres gauche | Total Ar + FMG droite │  Card BG_CARD
    │ Row 5 — Actions : Nouveau | Suppr | Imprimer | 💾        │  Frame BG_PAGE
    └─────────────────────────────────────────────────────────┘
    """

    def __init__(self, master, id_user_connecte: int,
                 role_user: str = "normal", **kwargs):
        super().__init__(master, fg_color=Colors.BG_PAGE, **kwargs)

        # ── État interne ──────────────────────────────────────────────────────
        self.id_user_connecte  = id_user_connecte
        self.conn: Optional[psycopg2.extensions.connection] = None
        self.article_selectionne         = None
        self.detail_avoir: list          = []
        self.index_ligne_selectionnee    = None
        self.magasin_map: dict           = {}
        self.magasin_ids: list           = []
        self.client_map: dict            = {}
        self.client_ids: list            = []
        self.role_user                   = role_user
        self.infos_societe: Dict[str, Any] = {}
        self.derniere_idvente_enregistree: Optional[int] = None
        self.mode_modification           = False
        self.idvente_charge: Optional[int] = None
        self._is_saving_avoir           = False

        # ── Paramètres d'impression (settings.json) ───────────────────────────
        self.settings = self._load_settings()

        # ── Layout principal : 6 rows ─────────────────────────────────────────
        self.grid_columnconfigure(0, weight=1)
        for row, w in enumerate([0, 0, 0, 1, 0, 0]):
            self.grid_rowconfigure(row, weight=w)

        # ── Construction de l'interface ───────────────────────────────────────
        self._setup_ui()

        # ── Chargements initiaux ───────────────────────────────────────────────
        self.generer_reference()
        self.charger_magasins()
        self.charger_client()
        self.charger_infos_societe()
        self.conn = self.connect_db()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1 — CONNEXION BASE DE DONNÉES
    # ══════════════════════════════════════════════════════════════════════════

    def connect_db(self):
        """
        Ouvre une connexion fraîche à PostgreSQL.
        Toujours appeler connect_db() au lieu de réutiliser self.conn
        pour les opérations ponctuelles (évite les connexions mortes).
        """
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
            MessageDialog("Erreur de configuration",
                          "Fichier 'config.json' non trouvé.", type_='error')
            return None
        except psycopg2.Error as e:
            MessageDialog("Erreur de Base de Données",
                          f"Impossible de se connecter : {e}", type_='error')
            return None

    def _load_settings(self) -> Dict[str, Any]:
        """
        Charge settings.json pour les paramètres d'impression.
        Retourne des valeurs par défaut si le fichier est absent/invalide.
        """
        defaults = {
            'Vente_ImpressionConfirmation': 1,
            'Vente_ImpressionA5':           1,
            'Vente_ImpressionTicket':       0,
            'Avoir_ImpressionConfirmation': 1,
            'Avoir_ImpressionA5':           1,
            'Avoir_ImpressionTicket':       0,
        }
        try:
            with open(get_config_path('settings.json'), 'r', encoding='utf-8') as f:
                settings = json.load(f)
            print("✅ Paramètres d'impression chargés depuis settings.json")
            return settings
        except FileNotFoundError:
            print("⚠️ settings.json non trouvé, valeurs par défaut utilisées")
        except json.JSONDecodeError:
            print("⚠️ settings.json invalide, valeurs par défaut utilisées")
        return defaults

    # Alias public pour rétrocompatibilité
    def load_settings(self) -> Dict[str, Any]:
        return self._load_settings()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — FORMATAGE NOMBRES
    # ══════════════════════════════════════════════════════════════════════════

    def formater_nombre(self, nombre) -> str:
        """Formate un nombre avec séparateur de milliers (1.000.000,00)."""
        try:
            valeur = Decimal(str(nombre))
        except (InvalidOperation, TypeError):
            return "0,00"

        valeur = valeur.quantize(Decimal("0.01"))
        if valeur == valeur.to_integral_value():
            fmt = "{:,.0f}"
        else:
            fmt = "{:,.2f}"

        return (
            fmt.format(valeur)
            .replace(',', '_TEMP_')
            .replace('.', ',')
            .replace('_TEMP_', '.')
        )

    def parser_nombre(self, texte) -> float:
        """Convertit un nombre formaté (1.000.000,00) en float."""
        try:
            return float(str(texte).replace('.', '').replace(',', '.'))
        except Exception:
            return 0.0

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3 — CONSTRUCTION DE L'INTERFACE (_setup_ui + 5 _build_*)
    # ══════════════════════════════════════════════════════════════════════════

    def _setup_ui(self):
        """
        Point d'entrée de la construction UI.
        Délègue à 5 sous-méthodes, une par zone fonctionnelle.
        *** NE CONTIENT QUE DU CODE UI — logique métier dans les autres sections ***
        """
        self._build_header_band()       # Row 0 — N° Avoir, Date, Client
        self._build_designation_band()  # Row 1 — Désignation (pleine largeur)
        self._build_article_band()      # Row 2 — Saisie article
        self._build_tree_zone()         # Row 3 — Tableau détails
        self._build_totals_band()       # Row 4 — Totaux
        self._build_actions_band()      # Row 5 — Boutons d'action

        # Initialiser les totaux à zéro au démarrage
        self.calculer_totaux()

    # ── Row 0 — Bandeau en-tête ───────────────────────────────────────────────

    def _build_header_band(self):
        """
        Card blanche (Row 0) : N° Avoir | Date | Magasin (masqué) | Client 🔎 | 📂 Charger
        Structure identique à la page de vente pour cohérence visuelle.
        """
        card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        card.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 2))
        card.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        # Styles partagés
        lbl_kw   = dict(font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY, anchor="w")
        entry_kw = dict(
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            height=32, corner_radius=6, font=Fonts.input(12),
        )
        entry_kw_no_font = {k: v for k, v in entry_kw.items() if k != 'font'}

        # — N° Avoir — (police bold pour la référence)
        ctk.CTkLabel(card, text="N° Avoir", **lbl_kw).grid(
            row=0, column=0, padx=(10, 2), pady=(8, 0), sticky="w")
        self.entry_ref_avoir = ctk.CTkEntry(
            card, **entry_kw_no_font, width=155, font=Fonts.bold(12),
        )
        self.entry_ref_avoir.grid(row=1, column=0, padx=(10, 4), pady=(0, 8), sticky="ew")
        self.entry_ref_avoir.configure(state="readonly")

        # — Date —
        ctk.CTkLabel(card, text="Date Avoir", **lbl_kw).grid(
            row=0, column=1, padx=4, pady=(8, 0), sticky="w")
        self.entry_date_avoir = ctk.CTkEntry(card, **entry_kw, width=150)
        self.entry_date_avoir.grid(row=1, column=1, padx=4, pady=(0, 8), sticky="ew")
        self.entry_date_avoir.insert(0, datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

        # — Magasin (masqué par défaut, visible en mode modification) —
        self.label_magasin = ctk.CTkLabel(card, text="Magasin de", **lbl_kw)
        self.label_magasin.grid(row=0, column=2, padx=4, pady=(8, 0), sticky="w")
        self.combo_magasin = ctk.CTkComboBox(
            card, values=["Chargement…"], width=160, height=32,
            font=Fonts.input(12), fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER, button_color=Colors.PRIMARY,
            dropdown_fg_color=Colors.BG_CARD,
        )
        self.combo_magasin.grid(row=1, column=2, padx=4, pady=(0, 8), sticky="ew")
        self.label_magasin.grid_remove()  # masqué par défaut
        self.combo_magasin.grid_remove()  # masqué par défaut

        # — Client (entry + loupe) —
        ctk.CTkLabel(card, text="Client", **lbl_kw).grid(
            row=0, column=3, padx=4, pady=(8, 0), sticky="w")

        client_frame = ctk.CTkFrame(card, fg_color="transparent")
        client_frame.grid(row=1, column=3, columnspan=2, padx=4, pady=(0, 8), sticky="ew")
        client_frame.grid_columnconfigure(0, weight=1)

        self.entry_client = ctk.CTkEntry(
            client_frame, **entry_kw, placeholder_text="Nom du client…",
        )
        self.entry_client.grid(row=0, column=0, sticky="ew")

        self.btn_search_client = ctk.CTkButton(
            client_frame, text="🔎", width=36, height=32,
            font=Fonts.body(14),
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            corner_radius=6, command=self.open_recherche_client,
        )
        self.btn_search_client.grid(row=0, column=1, padx=(4, 0))

        # — Bouton Charger Facture —
        ctk.CTkLabel(card, text=" ", **lbl_kw).grid(
            row=0, column=5, padx=(4, 10), pady=(8, 0), sticky="w")
        self.btn_charger_bs = ctk.CTkButton(
            card, text="📂 Charger Facture",
            font=Fonts.bold(11), height=32,
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            corner_radius=6, command=self.ouvrir_recherche_sortie,
        )
        self.btn_charger_bs.grid(row=1, column=5, padx=(4, 10), pady=(0, 8), sticky="ew")

    # ── Row 1 — Bandeau désignation ───────────────────────────────────────────

    def _build_designation_band(self):
        """
        Card blanche (Row 1) : champ Désignation sur toute la largeur.
        Séparé du header pour faciliter le masquage en mode consultation.
        """
        card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        card.grid(row=1, column=0, sticky="ew", padx=0, pady=(0, 2))
        card.grid_columnconfigure(1, weight=1)

        lbl_kw   = dict(font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY)
        entry_kw = dict(
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            height=32, corner_radius=6, font=Fonts.input(12),
        )

        ctk.CTkLabel(card, text="Désignation", **lbl_kw).grid(
            row=0, column=0, padx=(10, 6), pady=8, sticky="w")
        self.entry_designation = ctk.CTkEntry(
            card, **entry_kw, placeholder_text="Motif / description de l'avoir…",
            state="disabled",
        )
        self.entry_designation.grid(row=0, column=1, padx=(0, 10), pady=8, sticky="ew")

    # ── Row 2 — Bandeau saisie article ───────────────────────────────────────

    def _build_article_band(self):
        """
        Card blanche (Row 2) : Article | 🔎 Rechercher | Qté Avoir | PU | ➕ Ajouter.
        Identique à la zone de saisie de la page de vente.
        """
        card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        card.grid(row=2, column=0, sticky="ew", padx=0, pady=(0, 2))
        for col in range(7):
            card.grid_columnconfigure(col, weight=1)

        lbl_kw   = dict(font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY, anchor="w")
        entry_kw = dict(
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            height=32, corner_radius=6, font=Fonts.input(12),
        )

        # — Article (readonly, rempli par la recherche) —
        ctk.CTkLabel(card, text="Article", **lbl_kw).grid(
            row=0, column=0, padx=(10, 2), pady=(8, 0), sticky="w")
        self.entry_article = ctk.CTkEntry(
            card, **entry_kw, placeholder_text="Sélectionner un article…",
        )
        self.entry_article.grid(row=1, column=0, padx=(10, 4), pady=(0, 8), sticky="ew")
        self.entry_article.configure(state="readonly")

        # — Bouton Rechercher article —
        ctk.CTkLabel(card, text=" ", **lbl_kw).grid(
            row=0, column=1, padx=4, pady=(8, 0), sticky="w")
        self.btn_recherche_article = ctk.CTkButton(
            card, text="🔎 Rechercher", height=32,
            font=Fonts.bold(11),
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            corner_radius=6, command=self.open_recherche_article,
        )
        self.btn_recherche_article.grid(row=1, column=1, padx=4, pady=(0, 8), sticky="ew")
        self.btn_recherche_article.configure(state="disabled")  # activé après chargement

        # — Quantité Avoir —
        ctk.CTkLabel(card, text="Quantité", **lbl_kw).grid(
            row=0, column=2, padx=4, pady=(8, 0), sticky="w")
        self.entry_qtavoir = ctk.CTkEntry(card, **entry_kw, width=100)
        self.entry_qtavoir.grid(row=1, column=2, padx=4, pady=(0, 8), sticky="ew")

        # — Unité (readonly) —
        ctk.CTkLabel(card, text="Unité", **lbl_kw).grid(
            row=0, column=3, padx=4, pady=(8, 0), sticky="w")
        self.entry_unite = ctk.CTkEntry(card, **entry_kw, width=100)
        self.entry_unite.grid(row=1, column=3, padx=4, pady=(0, 8), sticky="ew")
        self.entry_unite.configure(state="readonly")

        # — Prix Unitaire (readonly pour non-admin) —
        ctk.CTkLabel(card, text="Prix Unitaire", **lbl_kw).grid(
            row=0, column=4, padx=4, pady=(8, 0), sticky="w")
        self.entry_prixunit = ctk.CTkEntry(card, **entry_kw, width=120)
        self.entry_prixunit.grid(row=1, column=4, padx=4, pady=(0, 8), sticky="ew")
        self.entry_prixunit.configure(state="readonly")

        # — Bouton Ajouter (vert) —
        ctk.CTkLabel(card, text=" ", **lbl_kw).grid(
            row=0, column=5, padx=4, pady=(8, 0), sticky="w")
        self.btn_ajouter = ctk.CTkButton(
            card, text="+ Ajouter", height=32,
            font=Fonts.bold(12),
            fg_color=Colors.SUCCESS_DARK, hover_color=Colors.INFO_DARK,
            corner_radius=6, command=self.valider_detail,
        )
        self.btn_ajouter.grid(row=1, column=5, padx=4, pady=(0, 8), sticky="ew")

        # — Bouton Annuler modification (rouge, masqué par défaut) —
        self.btn_annuler_mod = ctk.CTkButton(
            card, text="✖ Annuler Modif", height=32,
            font=Fonts.bold(11),
            fg_color=Colors.DANGER, hover_color=Colors.DANGER_DARK,
            corner_radius=6, command=self.reset_detail_form, state="disabled",
        )
        self.btn_annuler_mod.grid(row=1, column=6, padx=(4, 10), pady=(0, 8), sticky="ew")
        self.btn_annuler_mod.grid_remove()  # visible seulement en mode modification

        # Masquer la bande de saisie d'article par défaut
        card.grid_remove()

    # ── Row 3 — Tableau Treeview ──────────────────────────────────────────────

    def _build_tree_zone(self):
        """
        Zone expansible (Row 3) : Treeview TTK avec style iJeery.
        En-têtes MIDNIGHT, lignes alternées, scrollbar CTk intégrée.
        Style défini UNE SEULE FOIS pour éviter les recalculs à chaque chargement.
        """
        frame = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        frame.grid(row=3, column=0, sticky="nsew", padx=0, pady=(0, 2))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        # ── Style TTK (défini une seule fois) ────────────────────────────────
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Avoir.Treeview",
            rowheight=22,
            font=('Segoe UI', 9),
            background=Colors.BG_CARD,
            foreground=Colors.TEXT_PRIMARY,
            fieldbackground=Colors.BG_CARD,
            borderwidth=0,
        )
        style.configure(
            "Avoir.Treeview.Heading",
            background=Colors.BG_HEADER,
            foreground=Colors.TEXT_ON_DARK,
            font=('Segoe UI', 9, 'bold'),
            relief="flat",
        )
        style.map(
            "Avoir.Treeview",
            background=[("selected", Colors.PRIMARY)],
            foreground=[("selected", Colors.TEXT_ON_DARK)],
        )

        # ── Colonnes ─────────────────────────────────────────────────────────
        colonnes = (
            "ID_Article", "ID_Unite", "ID_Magasin",
            "Code Article", "Désignation", "Magasin",
            "Unité", "Prix Unitaire", "Quantité Avoir", "Montant",
        )
        self.tree_details = ttk.Treeview(
            frame, columns=colonnes, show='headings',
            style="Avoir.Treeview",
        )

        # Tags lignes alternées
        self.tree_details.tag_configure("even", background=Colors.BG_CARD)
        self.tree_details.tag_configure("odd",  background=Colors.BG_ROW_ALT)

        # En-têtes et largeurs
        for col in colonnes:
            self.tree_details.heading(col, text=col.replace('_', ' '))
            if "ID" in col:
                self.tree_details.column(col, width=0, stretch=False)
            elif col in ("Quantité Avoir", "Prix Unitaire"):
                self.tree_details.column(col, width=110, anchor='e')
            elif col == "Montant":
                self.tree_details.column(col, width=120, anchor='e')
            elif col == "Désignation":
                self.tree_details.column(col, width=320, anchor='w')
            elif col == "Code Article":
                self.tree_details.column(col, width=120, anchor='w')
            else:
                self.tree_details.column(col, width=130, anchor='w')

        # Scrollbar CTk
        scrollbar = ctk.CTkScrollbar(frame, command=self.tree_details.yview)
        self.tree_details.configure(yscrollcommand=scrollbar.set)

        self.tree_details.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 6), pady=6)

        # Double-clic → modification de la ligne
        self.tree_details.bind('<Double-1>', self.modifier_detail)

    # ── Row 4 — Zone totaux ───────────────────────────────────────────────────

    def _build_totals_band(self):
        """
        Card blanche (Row 4) : total en lettres (gauche) | Total Ar + FMG (droite).
        Structure symétrique avec la page de vente.
        """
        card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        card.grid(row=4, column=0, sticky="ew", padx=0, pady=(0, 2))
        card.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(1, weight=0)

        # Côté gauche — Total en lettres
        ctk.CTkLabel(
            card, text="Total en Lettres",
            font=Fonts.bold(11), text_color=Colors.TEXT_SECONDARY,
            anchor="w",
        ).grid(row=0, column=0, padx=(12, 4), pady=(6, 0), sticky="w")

        self.label_total_lettres = ctk.CTkLabel(
            card, text="Zéro",
            font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY,
            wraplength=550, justify="left", anchor="w",
        )
        self.label_total_lettres.grid(
            row=1, column=0, padx=(12, 4), pady=(0, 8), sticky="ew",
        )

        # Côté droit — Montants numériques
        right_frame = ctk.CTkFrame(card, fg_color="transparent")
        right_frame.grid(row=0, column=1, rowspan=2, padx=(4, 16), pady=6, sticky="e")

        # Total Ar
        ctk.CTkLabel(
            right_frame,
            text="TOTAL GÉNÉRAL (Ar) : ",
            font=Fonts.bold(13), text_color=Colors.TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="e")

        self.label_total_general = ctk.CTkLabel(
            right_frame, text="0,00",
            font=Fonts.bold(14), text_color=Colors.DANGER,
        )
        self.label_total_general.grid(row=0, column=1, padx=(4, 0), sticky="e")

        # Total FMG (× 5)
        ctk.CTkLabel(
            right_frame,
            text="En FMG : ",
            font=Fonts.label(11), text_color=Colors.TEXT_MUTED,
        ).grid(row=1, column=0, sticky="e")

        self.label_total_fmg = ctk.CTkLabel(
            right_frame, text="0,00",
            font=Fonts.label(11), text_color=Colors.TEXT_MUTED,
        )
        self.label_total_fmg.grid(row=1, column=1, padx=(4, 0), sticky="e")

    # ── Row 5 — Barre d'actions ───────────────────────────────────────────────

    def _build_actions_band(self):
        """
        Frame BG_PAGE (Row 5) : boutons d'action alignés gauche/droite.
        Couleurs cohérentes avec la charte iJeery.
        """
        bar = ctk.CTkFrame(self, fg_color=Colors.BG_PAGE, corner_radius=0)
        bar.grid(row=5, column=0, sticky="ew", padx=0, pady=(2, 0))
        bar.grid_columnconfigure(3, weight=1)  # espace élastique avant "Enregistrer"

        # — Valider Modif (vert, désactivé par défaut) —
        self.btn_valider_modif = ctk.CTkButton(
            bar, text="✅ Valider Modif", height=34,
            font=Fonts.bold(11),
            fg_color=Colors.SUCCESS_DARK, hover_color=Colors.INFO_DARK,
            corner_radius=6, command=self.enregistrer_avoir, state="disabled",
        )
        self.btn_valider_modif.grid(row=0, column=0, padx=(8, 4), pady=6)

        # — Supprimer Ligne (rouge) —
        self.btn_supprimer_ligne = ctk.CTkButton(
            bar, text="🗑 Supprimer Ligne", height=34,
            font=Fonts.bold(11),
            fg_color=Colors.DANGER, hover_color=Colors.DANGER_DARK,
            corner_radius=6, command=self.supprimer_detail,
            state="disabled",
        )
        self.btn_supprimer_ligne.grid(row=0, column=1, padx=4, pady=6)

        # — Imprimer (masqué jusqu'à enregistrement) —
        self.btn_imprimer = ctk.CTkButton(
            bar, text="🖨 Imprimer", height=34,
            font=Fonts.bold(11),
            fg_color=Colors.PREMIUM, hover_color=Colors.PREMIUM_DARK,
            corner_radius=6, command=self.open_impression_dialogue, state="disabled",
        )
        self.btn_imprimer.grid(row=0, column=2, padx=4, pady=6)
        self.btn_imprimer.grid_remove()  # visible uniquement après enregistrement

        # espace élastique — colonne 3 est weight=1

        # — Enregistrer la Facture (bleu principal, droite) —
        self.btn_enregistrer = ctk.CTkButton(
            bar, text="💾 Enregistrer l'Avoir", height=34,
            font=Fonts.bold(13),
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            corner_radius=8, command=self.enregistrer_avoir,
        )
        self.btn_enregistrer.grid(row=0, column=4, padx=(4, 8), pady=6, sticky="e")

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 4 — CALCUL DES TOTAUX
    # ══════════════════════════════════════════════════════════════════════════

    def calculer_totaux(self):
        """
        Recalcule le total général depuis self.detail_avoir
        et met à jour les labels Total Ar, FMG et Total en Lettres.
        """
        total_general = sum(
            float(d.get('qtvente', 0) or 0) *
            (float(d.get('prixunit', 0) or 0) - float(d.get('remise', 0) or 0))
            for d in self.detail_avoir
        )

        self.label_total_general.configure(text=self.formater_nombre(total_general))
        self.label_total_fmg.configure(
            text=self.formater_nombre(total_general * 5)
        )
        self.label_total_lettres.configure(
            text=nombre_en_lettres_fr(total_general) or "Zéro"
        )

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 5 — LOGIQUE MÉTIER : PRIX & STOCK
    # ══════════════════════════════════════════════════════════════════════════

    def get_article_price(self, idarticle, idunite) -> float:
        """
        Récupère le dernier prix unitaire pour l'article et l'unité donnés.
        Priorité : tb_prix → tb_unite.prixventeunite
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        conn = self.conn
        if not conn:
            return 0.0

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT COALESCE(prix) AS prix FROM tb_prix
                WHERE idarticle = %s AND idunite = %s
                ORDER BY id DESC LIMIT 1
                """,
                (idarticle, idunite),
            )
            result = cursor.fetchone()
            if result and result[0] is not None and result[0] > 0:
                return float(result[0])

            cursor.execute(
                """
                SELECT prix FROM tb_unite
                WHERE idarticle = %s AND idunite = %s LIMIT 1
                """,
                (idarticle, idunite),
            )
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

    def calculer_stock_article(self, idarticle, idunite_cible, idmag=None) -> float:
        """
        Calcule le stock consolidé d'un article dans l'unité cible.
        Prend en compte : livraisons, ventes, avoirs, sorties, transferts.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        conn = self.connect_db()
        if not conn:
            return 0

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT idunite, COALESCE(qtunite, 1) AS qtunite
                FROM tb_unite WHERE idarticle = %s ORDER BY idunite ASC
                """,
                (idarticle,),
            )
            unites_article = cursor.fetchall()

            if not unites_article:
                return 0

            facteurs_conversion: dict = {}
            facteur_cumul = 1.0
            for i, (id_unite, qt_unite) in enumerate(unites_article):
                if i == 0:
                    facteurs_conversion[id_unite] = 1.0
                else:
                    facteur_cumul *= qt_unite
                    facteurs_conversion[id_unite] = facteur_cumul

            facteur_cible = facteurs_conversion.get(idunite_cible, 1.0)
            if facteur_cible == 0:
                return 0

            clause_mag = "AND idmag = %s" if idmag else ""
            params_mag = [idmag] if idmag else []

            stock_en_unite_base = 0.0

            for idunite_source, _ in unites_article:
                def qry(sql, params):
                    cursor.execute(sql, params)
                    return cursor.fetchone()[0] or 0

                total_livraison = qry(
                    f"SELECT COALESCE(SUM(qtlivrefrs),0) FROM tb_livraisonfrs "
                    f"WHERE idarticle=%s AND idunite=%s {clause_mag}",
                    [idarticle, idunite_source] + params_mag,
                )
                total_vente = qry(
                    f"SELECT COALESCE(SUM(qtvente),0) FROM tb_ventedetail "
                    f"WHERE idarticle=%s AND idunite=%s {clause_mag}",
                    [idarticle, idunite_source] + params_mag,
                )
                total_avoir = qry(
                    f"SELECT COALESCE(SUM(qtavoir),0) FROM tb_avoirdetail "
                    f"WHERE idarticle=%s AND idunite=%s {clause_mag}",
                    [idarticle, idunite_source] + params_mag,
                )
                total_sortie = qry(
                    f"SELECT COALESCE(SUM(qtsortie),0) FROM tb_sortiedetail sd "
                    f"INNER JOIN tb_sortie s ON sd.idsortie=s.id "
                    f"WHERE sd.idarticle=%s AND sd.idunite=%s AND s.deleted=0 {clause_mag}",
                    [idarticle, idunite_source] + params_mag,
                )

                p_ts = [idarticle, idunite_source]
                q_ts = ("SELECT COALESCE(SUM(td.qttransfertsortie),0) "
                        "FROM tb_transfertdetail td "
                        "INNER JOIN tb_transfert t ON td.reftransfert=t.reftransfert "
                        "WHERE td.idarticle=%s AND td.idunite=%s AND t.deleted=0")
                if idmag:
                    q_ts += " AND t.idmagsortie=%s"
                    p_ts.append(idmag)
                total_transfert_sortie = qry(q_ts, p_ts)

                p_te = [idarticle, idunite_source]
                q_te = ("SELECT COALESCE(SUM(td.qttransfertentree),0) "
                        "FROM tb_transfertdetail td "
                        "INNER JOIN tb_transfert t ON td.reftransfert=t.reftransfert "
                        "WHERE td.idarticle=%s AND td.idunite=%s AND t.deleted=0")
                if idmag:
                    q_te += " AND t.idmagentree=%s"
                    p_te.append(idmag)
                total_transfert_entree = qry(q_te, p_te)

                stock_source = (
                    total_livraison + total_avoir + total_transfert_entree
                    - total_vente - total_sortie - total_transfert_sortie
                )
                stock_en_unite_base += stock_source * facteurs_conversion.get(idunite_source, 1.0)

            return stock_en_unite_base / facteur_cible

        except Exception:
            return 0
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if conn:
                conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 6 — CHARGEMENTS INITIAUX
    # ══════════════════════════════════════════════════════════════════════════

    def generer_reference(self):
        """Génère et affiche la prochaine référence d'Avoir (AAAA-AV-NNNNN)."""
        conn = self.connect_db()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            annee = datetime.now().year
            cursor.execute(
                """
                SELECT refavoir FROM tb_avoir
                WHERE EXTRACT(YEAR FROM dateregistre) = %s
                ORDER BY id DESC LIMIT 1
                """,
                (annee,),
            )
            derniere_ref  = cursor.fetchone()
            nouveau_numero = 1

            if derniere_ref:
                parts = derniere_ref[0].split('-')
                if len(parts) == 3 and parts[1] == 'AV':
                    try:
                        nouveau_numero = int(parts[-1]) + 1
                    except ValueError:
                        nouveau_numero = 1

            nouvelle_ref = f"{annee}-AV-{nouveau_numero:05d}"

            self.entry_ref_avoir.configure(state="normal")
            self.entry_ref_avoir.delete(0, "end")
            self.entry_ref_avoir.insert(0, nouvelle_ref)
            self.entry_ref_avoir.configure(state="readonly")

        except Exception as e:
            MessageDialog("Erreur", f"Erreur génération référence : {e}", type_='error')
        finally:
            conn.close()

    def charger_magasins(self):
        """Remplit le ComboBox magasin depuis tb_magasin."""
        conn = self.connect_db()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT idmag, designationmag FROM tb_magasin "
                "WHERE deleted=0 ORDER BY designationmag"
            )
            magasins = cursor.fetchall()

            self.magasin_map  = {nom: id_ for id_, nom in magasins}
            self.magasin_ids  = [id_ for id_, nom in magasins]
            noms              = list(self.magasin_map.keys())

            self.combo_magasin.configure(values=noms)
            self.combo_magasin.set(noms[0] if noms else "Aucun magasin")

        except Exception as e:
            MessageDialog("Erreur", f"Chargement magasins : {e}", type_='error')
        finally:
            conn.close()

    def charger_client(self):
        """Charge la map des clients pour la recherche rapide."""
        conn = self.connect_db()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT idclient, nomcli FROM tb_client "
                "WHERE deleted=0 ORDER BY nomcli"
            )
            clients = cursor.fetchall()

            self.client_map = {nom: id_ for id_, nom in clients}
            self.client_ids = [id_ for id_, nom in clients]

        except Exception as e:
            MessageDialog("Erreur", f"Chargement clients : {e}", type_='error')
        finally:
            conn.close()

    def charger_infos_societe(self):
        """Charge les informations de la société depuis tb_infosociete."""
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
                'nomsociete':    result[0] or 'SOCIÉTÉ',
                'adressesociete': result[1] or 'N/A',
                'contactsociete': result[2] or 'N/A',
                'villesociete':   result[3] or 'N/A',
                'nifsociete':     result[4] or 'N/A',
                'statsociete':    result[5] or 'N/A',
                'cifsociete':     result[6] or 'N/A',
            } if result else _default

        except Exception as e:
            print(f"Erreur chargement infos société : {e}")
            self.infos_societe = _default
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if conn:
                conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 7 — FENÊTRES DE RECHERCHE
    # ══════════════════════════════════════════════════════════════════════════

    def open_recherche_client(self):
        """Fenêtre modale de recherche client avec filtre type et loupe."""
        fen = ctk.CTkToplevel(self)
        fen.title("Rechercher un client")
        fen.geometry("820x500")
        fen.grab_set()

        frame = ctk.CTkFrame(fen)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            frame, text="Rechercher un client",
            font=Fonts.heading(14),
        ).pack(pady=5)

        # Filtres
        top_frame = ctk.CTkFrame(frame, fg_color="transparent")
        top_frame.pack(fill="x", padx=5, pady=5)
        top_frame.grid_columnconfigure(0, weight=1)

        entry_search = ctk.CTkEntry(top_frame, placeholder_text="Nom client…")
        entry_search.grid(row=0, column=0, padx=(0, 8), sticky="ew")

        type_filter_combo = ctk.CTkComboBox(
            top_frame,
            values=["Client à crédit", "Client au comptant", "Tous les types"],
            width=190, state="readonly",
        )
        type_filter_combo.set("Client à crédit")
        type_filter_combo.grid(row=0, column=1, sticky="e")

        # Treeview
        colonnes = ("ID", "Nom Client", "Contact", "Adresse")
        tree = ttk.Treeview(frame, columns=colonnes, show="headings", height=10)
        tree.tag_configure("even", background=Colors.BG_CARD)
        tree.tag_configure("odd",  background=Colors.BG_ROW_ALT)

        for col, w in zip(colonnes, [60, 220, 180, 320]):
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor="w" if col != "ID" else "center")

        tree.pack(fill="both", expand=True, pady=5)

        def charger_clients(filtre=""):
            for item in tree.get_children():
                tree.delete(item)
            conn = self.connect_db()
            if not conn:
                return
            try:
                cursor = conn.cursor()
                selected_type = type_filter_combo.get()
                type_condition = ""
                if selected_type == "Client à crédit":
                    type_condition = " AND COALESCE(idtypeclient,1)=2 "
                elif selected_type == "Client au comptant":
                    type_condition = " AND COALESCE(idtypeclient,1)=1 "

                cursor.execute(
                    f"""
                    SELECT idclient, nomcli,
                        COALESCE(NULLIF(TRIM(contactcli),''),'Aucun contact') AS contact,
                        COALESCE(NULLIF(TRIM(adressecli),''),'Aucune adresse') AS adresse
                    FROM tb_client
                    WHERE deleted=0 AND nomcli ILIKE %s
                    {type_condition}
                    ORDER BY nomcli
                    """,
                    (f"%{filtre}%",),
                )
                for idx, (idc, nom, contact, adresse) in enumerate(cursor.fetchall()):
                    tree.insert("", "end", values=(idc, nom, contact, adresse),
                                tags=("even" if idx % 2 == 0 else "odd",))
            finally:
                cursor.close()
                conn.close()

        entry_search.bind("<KeyRelease>", lambda e: charger_clients(entry_search.get()))
        type_filter_combo.configure(command=lambda _v: charger_clients(entry_search.get()))

        def valider_selection():
            sel = tree.selection()
            if not sel:
                return
            nom_client = tree.item(sel[0])["values"][1]
            self.entry_client.delete(0, "end")
            self.entry_client.insert(0, nom_client)
            fen.destroy()

        tree.bind("<Double-1>", lambda e: valider_selection())
        charger_clients()

    def open_recherche_article(self):
        """
        Fenêtre modale de recherche article.
        Calcule le stock réel et charge le prix automatiquement.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        if self.index_ligne_selectionnee is not None:
            MessageDialog(
                "Attention",
                "Veuillez d'abord valider ou annuler la modification en cours.",
                type_='warning'
            )
            return

        fen = ctk.CTkToplevel(self)
        fen.title("Rechercher un article")
        fen.geometry("1000x600")
        fen.grab_set()

        main_frame = ctk.CTkFrame(fen)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            main_frame, text="Sélectionner un article",
            font=Fonts.heading(16),
        ).pack(pady=(0, 10))

        # Recherche
        search_frame = ctk.CTkFrame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(search_frame, text="🔍 Rechercher :").pack(side="left", padx=5)
        entry_search = ctk.CTkEntry(
            search_frame, placeholder_text="Code ou désignation…", width=300,
        )
        entry_search.pack(side="left", padx=5, fill="x", expand=True)

        # Treeview articles
        tree_frame = ctk.CTkFrame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))

        colonnes = ("ID_Article", "ID_Unite", "Code", "Désignation", "Unité", "Prix Unitaire", "Stock")
        tree = ttk.Treeview(tree_frame, columns=colonnes, show='headings', height=15)
        tree.tag_configure("even", background=Colors.BG_CARD)
        tree.tag_configure("odd",  background=Colors.BG_ROW_ALT)

        col_widths = {"ID_Article": 0, "ID_Unite": 0, "Code": 150,
                      "Désignation": 400, "Unité": 100,
                      "Prix Unitaire": 120, "Stock": 150}
        for col, w in col_widths.items():
            tree.heading(col, text=col.replace("_", " "))
            if w == 0:
                tree.column(col, width=0, stretch=False)
            else:
                tree.column(col, width=w, anchor='e' if col in ("Prix Unitaire", "Stock") else 'w')

        scrollbar = ctk.CTkScrollbar(tree_frame, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        label_count = ctk.CTkLabel(main_frame, text="")
        label_count.pack(pady=(0, 5))

        def charger_articles(terme=""):
            for item in tree.get_children():
                tree.delete(item)
            conn = self.connect_db()
            if not conn:
                return
            try:
                cursor = conn.cursor()
                t = f"%{terme.strip()}%"
                cursor.execute(
                    """
                    SELECT a.idarticle, a.designation, u.idunite,
                           u.codearticle, u.designationunite
                    FROM tb_article a
                    INNER JOIN tb_unite u ON a.idarticle = u.idarticle
                    WHERE a.deleted=0
                      AND (u.codearticle ILIKE %s OR a.designation ILIKE %s)
                    ORDER BY a.designation, u.idunite
                    """,
                    (t, t),
                )
                resultats = cursor.fetchall()
                designationmag = self.combo_magasin.get()
                idmag          = self.magasin_map.get(designationmag)

                for idx, row in enumerate(resultats):
                    idarticle, designation, idunite, codearticle, designationunite = row
                    stock = self.calculer_stock_article(idarticle, idunite, idmag)
                    prix  = self.get_article_price(idarticle, idunite)
                    tree.insert('', 'end', values=(
                        idarticle, idunite, codearticle, designation,
                        designationunite,
                        self.formater_nombre(prix),
                        self.formater_nombre(stock),
                    ), tags=("even" if idx % 2 == 0 else "odd",))

                label_count.configure(text=f"{len(resultats)} article(s) trouvé(s)")
            except Exception as e:
                MessageDialog("Erreur", f"Chargement articles : {e}", type_='error')
            finally:
                if 'cursor' in locals() and cursor:
                    cursor.close()
                if conn:
                    conn.close()

        def valider_selection():
            sel = tree.selection()
            if not sel:
                MessageDialog("Attention", "Sélectionnez un article.", type_='warning')
                return
            values    = tree.item(sel[0])['values']
            stock_reel = self.parser_nombre(str(values[6]))

            if stock_reel <= 0:
                if not YesNoDialog(
                    "Stock faible",
                    f"Stock disponible : {values[6]} {values[4]}\n"
                    "Voulez-vous continuer ?"
                ).result:
                    return

            article_data = {
                'idarticle': values[0], 'nom_article': values[3],
                'idunite':   values[1], 'nom_unite':   values[4],
                'code_article': values[2],
                'prixunit': self.get_article_price(values[0], values[1]),
            }
            fen.destroy()
            self.on_article_selected(article_data)

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

    def on_article_selected(self, article_data):
        """Met à jour les champs du formulaire après sélection d'un article."""
        self.article_selectionne = article_data

        designation_complete = f"[{article_data.get('code_article','N/A')}] {article_data['nom_article']}"

        self.entry_article.configure(state="normal")
        self.entry_article.delete(0, "end")
        self.entry_article.insert(0, designation_complete)
        self.entry_article.configure(state="readonly")

        self.entry_unite.configure(state="normal")
        self.entry_unite.delete(0, "end")
        self.entry_unite.insert(0, article_data['nom_unite'])
        self.entry_unite.configure(state="readonly")

        prix = article_data.get("prixunit", 0.0)
        self.entry_prixunit.configure(state="normal")
        self.entry_prixunit.delete(0, "end")
        self.entry_prixunit.insert(0, self.formater_nombre(prix))

        # Seuls les admins peuvent modifier le prix
        if self.role_user != "admin":
            self.entry_prixunit.configure(state="readonly")

        self.entry_qtavoir.delete(0, "end")
        self.entry_qtavoir.focus_set()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 8 — GESTION DU DÉTAIL AVOIR
    # ══════════════════════════════════════════════════════════════════════════

    def valider_detail(self):
        """
        Ajoute ou modifie un article dans self.detail_avoir
        et rafraîchit le Treeview + totaux.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        if not self.article_selectionne:
            MessageDialog("Attention", "Sélectionnez d'abord un article.", type_='warning')
            return

        try:
            qtvente = self.parser_nombre(self.entry_qtavoir.get().strip())
            if qtvente < 0:
                raise ValueError
        except Exception:
            MessageDialog("Erreur", "La quantité doit être positive ou nulle.", type_='error')
            return

        try:
            prixunit = self.parser_nombre(self.entry_prixunit.get().strip())
            if prixunit < 0:
                raise ValueError
        except Exception:
            MessageDialog("Erreur", "Le prix unitaire doit être positif ou nul.", type_='error')
            return

        designationmag = self.combo_magasin.get().strip()
        if not designationmag or designationmag in ("Chargement…", "Aucun magasin"):
            MessageDialog("Erreur", "Sélectionnez un magasin valide.", type_='error')
            return
        idmag = self.magasin_map.get(designationmag)
        if not idmag:
            MessageDialog("Erreur", "Magasin non valide.", type_='error')
            return

        nouveau_detail = {
            'idmag':          idmag,
            'designationmag': designationmag,
            'idarticle':      self.article_selectionne['idarticle'],
            'code_article':   self.article_selectionne.get('code_article', 'N/A'),
            'nom_article':    self.article_selectionne['nom_article'],
            'idunite':        self.article_selectionne['idunite'],
            'nom_unite':      self.article_selectionne['nom_unite'],
            'qtvente':        qtvente,
            'prixunit':       prixunit,
        }

        # En mode modification : vérification qt_origine
        if self.index_ligne_selectionnee is not None:
            detail_original = self.detail_avoir[self.index_ligne_selectionnee]
            if 'qt_origine' in detail_original:
                nouveau_detail['qt_origine'] = detail_original['qt_origine']
                if qtvente > detail_original['qt_origine']:
                    MessageDialog(
                        "Erreur",
                        f"Qt avoir ({self.formater_nombre(qtvente)}) > "
                        f"Qt vendue ({self.formater_nombre(detail_original['qt_origine'])}).",
                        type_='error'
                    )
                    return

            # Mise à jour de la ligne existante
            self.detail_avoir[self.index_ligne_selectionnee] = nouveau_detail
            selected_item = self.tree_details.selection()[0]
            self.tree_details.item(
                selected_item,
                values=self.format_detail_for_treeview(nouveau_detail),
            )
            MessageDialog("Succès", "Ligne modifiée.", type_='info')
        else:
            # Ajout d'une nouvelle ligne
            self.detail_avoir.append(nouveau_detail)
            idx = len(self.tree_details.get_children())
            self.tree_details.insert(
                '', 'end',
                values=self.format_detail_for_treeview(nouveau_detail),
                tags=("even" if idx % 2 == 0 else "odd",),
            )
            MessageDialog("Succès", "Article ajouté.", type_='info')

        self.calculer_totaux()
        self.reset_detail_form()

    def format_detail_for_treeview(self, detail) -> tuple:
        """Formate un dict de détail en tuple pour le Treeview."""
        qtvente   = float(detail.get('qtvente', 0) or 0)
        prixunit  = float(detail.get('prixunit', 0) or 0)
        remise    = float(detail.get('remise', 0) or 0)
        montant   = qtvente * (prixunit - remise)

        return (
            detail['idarticle'],
            detail['idunite'],
            detail['idmag'],
            detail.get('code_article', 'N/A'),
            detail['nom_article'],
            detail['designationmag'],
            detail['nom_unite'],
            self.formater_nombre(prixunit),
            self.formater_nombre(qtvente),
            self.formater_nombre(montant),
        )

    def charger_details_treeview(self):
        """Vide et recharge le Treeview depuis self.detail_avoir."""
        for item in self.tree_details.get_children():
            self.tree_details.delete(item)

        for idx, detail in enumerate(self.detail_avoir):
            self.tree_details.insert(
                '', 'end',
                values=self.format_detail_for_treeview(detail),
                tags=("even" if idx % 2 == 0 else "odd",),
            )

        self.calculer_totaux()

    def modifier_detail(self, event):
        """
        Double-clic sur une ligne → charge les données dans le formulaire
        pour permettre la modification de la quantité.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        if self.mode_modification:
            MessageDialog("Attention", "Mode consultation — modification impossible.", type_='warning')
            return

        selected_item = self.tree_details.focus()
        if not selected_item:
            return

        try:
            self.index_ligne_selectionnee = self.tree_details.index(selected_item)
            detail = self.detail_avoir[self.index_ligne_selectionnee]
        except IndexError:
            MessageDialog("Erreur", "Impossible de récupérer la ligne.", type_='error')
            self.reset_detail_form()
            return

        self.article_selectionne = {
            'idarticle':    detail['idarticle'],
            'nom_article':  detail['nom_article'],
            'idunite':      detail['idunite'],
            'nom_unite':    detail['nom_unite'],
            'code_article': detail.get('code_article', 'N/A'),
            'prixunit':     detail.get('prixunit', 0.0),
        }

        designation_complete = f"[{detail.get('code_article','N/A')}] {detail['nom_article']}"

        self.entry_article.configure(state="normal")
        self.entry_article.delete(0, "end")
        self.entry_article.insert(0, designation_complete)
        self.entry_article.configure(state="readonly")

        self.entry_unite.configure(state="normal")
        self.entry_unite.delete(0, "end")
        self.entry_unite.insert(0, detail['nom_unite'])
        self.entry_unite.configure(state="readonly")

        self.entry_prixunit.configure(state="normal")
        self.entry_prixunit.delete(0, "end")
        self.entry_prixunit.insert(0, self.formater_nombre(detail.get('prixunit', 0.0)))
        if self.role_user != "admin":
            self.entry_prixunit.configure(state="readonly")

        self.entry_qtavoir.delete(0, "end")
        self.entry_qtavoir.insert(0, self.formater_nombre(detail['qtvente']))

        # Signal visuel : bouton ajouter vire en orange "Valider Modif"
        self.btn_ajouter.configure(
            text="✔ Valider Modif",
            fg_color=Colors.WARNING, hover_color="#E65100",
        )
        self.btn_annuler_mod.configure(state="normal")
        self.btn_annuler_mod.grid()

        self.entry_qtavoir.focus_set()

    def supprimer_detail(self):
        """Supprime la ligne sélectionnée dans le Treeview et self.detail_avoir."""
        selected_item = self.tree_details.focus()
        if not selected_item:
            MessageDialog("Attention", "Sélectionnez une ligne.", type_='warning')
            return

        if self.mode_modification:
            MessageDialog("Attention", "Mode consultation — suppression impossible.", type_='warning')
            return

        try:
            index = self.tree_details.index(selected_item)
            del self.detail_avoir[index]
            self.tree_details.delete(selected_item)
            self.calculer_totaux()
            MessageDialog("Succès", "Ligne supprimée.", type_='info')
        except Exception as e:
            MessageDialog("Erreur", f"Suppression impossible : {e}", type_='error')

        self.reset_detail_form()

    def reset_detail_form(self):
        """Réinitialise le formulaire de saisie d'article (champs + état boutons)."""
        self.article_selectionne      = None
        self.index_ligne_selectionnee = None

        for entry, state in [
            (self.entry_article,  "readonly"),
            (self.entry_unite,    "readonly"),
        ]:
            entry.configure(state="normal")
            entry.delete(0, "end")
            entry.configure(state=state)

        self.entry_prixunit.configure(state="normal")
        self.entry_prixunit.delete(0, "end")
        self.entry_qtavoir.delete(0, "end")

        # Remettre le bouton Ajouter à son état normal (vert)
        self.btn_ajouter.configure(
            text="+ Ajouter",
            fg_color=Colors.SUCCESS_DARK, hover_color=Colors.INFO_DARK,
        )
        self.btn_annuler_mod.configure(state="disabled")
        self.btn_annuler_mod.grid_remove()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 9 — RECHERCHE ET CHARGEMENT DE FACTURE
    # ══════════════════════════════════════════════════════════════════════════

    def ouvrir_recherche_sortie(self):
        """
        Fenêtre modale pour rechercher une facture (vente) à transformer en avoir.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        if self.detail_avoir:
            if not YesNoDialog(
                "Attention",
                "Le formulaire contient des lignes non enregistrées.\n"
                "Voulez-vous continuer et les effacer ?"
            ).result:
                return

        fen = ctk.CTkToplevel(self)
        fen.title("Rechercher une Facture (Vente)")
        fen.geometry("1000x600")
        fen.grab_set()
        fen.lift()
        fen.focus_force()
        fen.attributes('-topmost', True)

        main_frame = ctk.CTkFrame(fen)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            main_frame,
            text="Sélectionner une Facture pour Avoir",
            font=Fonts.heading(16),
        ).pack(pady=(0, 10))

        # Filtres
        search_frame = ctk.CTkFrame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(search_frame, text="🔍 Référence ou Client :").pack(side="left", padx=5)
        entry_search = ctk.CTkEntry(
            search_frame, placeholder_text="Référence ou Nom Client…", width=300,
        )
        entry_search.pack(side="left", padx=5, fill="x", expand=True)
        ctk.CTkLabel(search_frame, text="Date (YYYY-MM-DD) :").pack(side="left", padx=(10, 5))
        entry_date = ctk.CTkEntry(search_frame, width=130)
        entry_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        entry_date.pack(side="left", padx=5)

        # Treeview factures
        tree_frame = ctk.CTkFrame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))

        style = ttk.Style()
        style.configure(
            "Search.Treeview",
            font=('Segoe UI', 8), background=Colors.BG_CARD,
            foreground=Colors.TEXT_PRIMARY, fieldbackground=Colors.BG_CARD,
            borderwidth=0, rowheight=22,
        )
        style.configure(
            "Search.Treeview.Heading",
            font=('Segoe UI', 8, 'bold'),
            background=Colors.BG_HEADER, foreground=Colors.TEXT_ON_DARK,
        )

        colonnes = ("ID", "Ref Vente", "Date et heure", "Client", "Montant Total", "Utilisateur")
        tree = ttk.Treeview(
            tree_frame, columns=colonnes, show='headings',
            height=15, selectmode='browse', style="Search.Treeview",
        )
        tree.tag_configure("even", background=Colors.BG_CARD)
        tree.tag_configure("odd",  background=Colors.BG_ROW_ALT)
        # Ligne désactivée si la facture a déjà un avoir associé
        tree.tag_configure(
            "disabled",
            background=Colors.BG_CARD,
            foreground=Colors.TEXT_MUTED,
        )

        col_config = {
            "ID": (0, False), "Ref Vente": (120, True),
            "Date et heure": (170, True), "Client": (150, True),
            "Montant Total": (120, True), "Utilisateur": (100, True),
        }
        for col, (w, visible) in col_config.items():
            tree.heading(col, text=col)
            tree.column(col, width=w, stretch=visible, anchor='center')

        scrollbar = ctk.CTkScrollbar(tree_frame, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def charger_factures(filtre=""):
            for item in tree.get_children():
                tree.delete(item)
            conn = self.connect_db()
            if not conn:
                return
            try:
                cursor = conn.cursor()
                filtre_like = f"%{filtre}%"
                date_str = entry_date.get().strip()
                try:
                    date_filtre = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    return

                cursor.execute(
                    """
                    SELECT v.id, v.refvente, v.dateregistre,
                           c.nomcli, COALESCE(v.totmtvente,0), u.nomuser,
                           EXISTS(
                               SELECT 1 FROM tb_avoir a
                               WHERE a.deleted = 0
                                 AND a.observation ILIKE '%%' || v.refvente || '%%'
                           ) AS has_avoir
                    FROM tb_vente v
                    LEFT JOIN tb_client c ON v.idclient = c.idclient
                    LEFT JOIN tb_users  u ON v.iduser   = u.iduser
                    WHERE v.deleted=0 AND v.statut='VALIDEE'
                      AND DATE(v.dateregistre) = %s
                      AND (v.refvente ILIKE %s OR v.description ILIKE %s OR c.nomcli ILIKE %s)
                    ORDER BY v.dateregistre DESC
                    """,
                    (date_filtre, filtre_like, filtre_like, filtre_like),
                )
                for idx, row in enumerate(cursor.fetchall()):
                    id_vente, ref_vente, date_vente, nom_cli, montant, nom_user, has_avoir = row
                    tags = ("disabled",) if has_avoir else ("even" if idx % 2 == 0 else "odd",)
                    tree.insert('', 'end', values=(
                        id_vente, ref_vente,
                        date_vente.strftime("%d/%m/%Y %H:%M:%S") if date_vente else "N/A",
                        nom_cli or "N/A",
                        self.formater_nombre(montant or 0.0),
                        nom_user or "Inconnu",
                    ), tags=tags)
                    if has_avoir:
                        print(f"[AVOIR] Facture déjà associée à un avoir : {ref_vente}")
            except Exception as e:
                MessageDialog("Erreur SQL", f"Chargement factures : {e}", type_='error')
            finally:
                if 'cursor' in locals():
                    cursor.close()
                if conn:
                    conn.close()

        def valider_selection():
            sel = tree.selection()
            if not sel:
                MessageDialog("Attention", "Sélectionnez une facture.", type_='warning')
                return
            item = sel[0]
            tags = tree.item(item).get('tags', [])
            if 'disabled' in tags:
                ref_vente = tree.item(item)['values'][1]
                print(f"[AVOIR] Sélection interdite : facture déjà avoirée {ref_vente}")
                MessageDialog(
                    "Attention",
                    "Cette facture a déjà un avoir associé et ne peut plus être sélectionnée.",
                    type_='warning'
                )
                return
            idvente = tree.item(item)['values'][0]
            fen.destroy()
            self.charger_vente_modification(idvente)

        entry_search.bind('<KeyRelease>', lambda e: charger_factures(entry_search.get()))
        entry_date.bind('<KeyRelease>',   lambda e: charger_factures(entry_search.get()))
        entry_date.bind('<FocusOut>',     lambda e: charger_factures(entry_search.get()))
        tree.bind('<Double-Button-1>', lambda e: valider_selection())

        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x")
        ctk.CTkButton(
            btn_frame, text="❌ Annuler", command=fen.destroy,
            fg_color=Colors.DANGER, hover_color=Colors.DANGER_DARK,
        ).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(
            btn_frame, text="✅ Charger la Facture", command=valider_selection,
            fg_color=Colors.SUCCESS_DARK, hover_color=Colors.INFO_DARK,
        ).pack(side="right", padx=5, pady=5)

        charger_factures()

    def charger_vente_modification(self, idvente: int):
        """
        Charge une facture pour créer un avoir.
        Active le formulaire avec les données de la vente.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        conn = self.connect_db()
        if not conn:
            return

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT v.id, v.refvente, v.dateregistre, v.description,
                       c.nomcli, v.idclient
                FROM tb_vente v
                LEFT JOIN tb_client c ON v.idclient = c.idclient
                WHERE v.id = %s
                """,
                (idvente,),
            )
            vente = cursor.fetchone()
            if not vente:
                MessageDialog("Erreur", "Facture introuvable.", type_='error')
                return

            cursor.execute(
                """
                SELECT vd.idmag, m.designationmag, vd.idarticle, u.codearticle,
                       a.designation, vd.idunite, u.designationunite, vd.qtvente,
                       vd.prixunit, COALESCE(vd.remise,0) AS remise
                FROM tb_ventedetail vd
                INNER JOIN tb_article a ON vd.idarticle = a.idarticle
                INNER JOIN tb_unite   u ON vd.idunite   = u.idunite
                INNER JOIN tb_magasin m ON vd.idmag     = m.idmag
                WHERE vd.idvente = %s
                """,
                (idvente,),
            )
            details = cursor.fetchall()

            self.reset_form(reset_imprimer=False)

            self.mode_modification  = False
            self.idvente_charge     = idvente
            self.derniere_idvente_enregistree = None

            self.generer_reference()

            self.entry_date_avoir.configure(state="normal")
            self.entry_date_avoir.delete(0, "end")
            self.entry_date_avoir.insert(0, vente[2].strftime("%d/%m/%Y %H:%M:%S"))

            self.entry_client.configure(state="normal")
            self.entry_client.delete(0, "end")
            self.entry_client.insert(0, vente[4] or "Client Inconnu")

            self.entry_designation.configure(state="normal")
            self.entry_designation.delete(0, "end")
            self.entry_designation.insert(0, f"Avoir pour Facture {vente[1]} - {vente[3] or ''}".strip())
            self.entry_designation.configure(state="disabled")

            self.detail_avoir = []
            for d in details:
                idmag, designationmag, idarticle, codearticle, designation, \
                    idunite, designationunite, qtvente, prixunit, remise = d
                self.detail_avoir.append({
                    'idmag':          idmag,
                    'designationmag': designationmag,
                    'idarticle':      idarticle,
                    'code_article':   codearticle,
                    'nom_article':    designation,
                    'idunite':        idunite,
                    'nom_unite':      designationunite,
                    'qtvente':        qtvente,
                    'prixunit':       prixunit,
                    'remise':         float(remise or 0),
                    'qt_origine':     qtvente,
                })

            self.charger_details_treeview()

            # Verrouiller les champs non éditables
            self.entry_client.configure(state="readonly")
            self.combo_magasin.configure(state="disabled")
            self.btn_recherche_article.configure(state="disabled")
            self.btn_ajouter.configure(state="normal")
            self.btn_supprimer_ligne.configure(state="disabled")

            # Activer l'enregistrement
            self.btn_enregistrer.configure(
                state="normal",
                text="💾 Enregistrer l'Avoir",
                command=self.enregistrer_avoir,
            )
            self.btn_imprimer.configure(state="disabled")
            self.btn_valider_modif.configure(state="disabled")

            self.calculer_totaux()

        except Exception as e:
            self.btn_enregistrer.configure(state="disabled")
            MessageDialog("Erreur", f"Chargement : {e}", type_='error')
            traceback.print_exc()
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if conn:
                conn.close()

    def charger_avoir_modification(self, idavoir: int):
        """
        Charge un avoir existant en mode consultation (impression uniquement).
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        conn = self.connect_db()
        if not conn:
            return

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT a.id, a.refavoir, a.dateregistre, a.observation,
                       c.nomcli, a.idclient
                FROM tb_avoir a
                LEFT JOIN tb_client c ON a.idclient = c.idclient
                WHERE a.id = %s
                """,
                (idavoir,),
            )
            avoir = cursor.fetchone()
            if not avoir:
                MessageDialog("Erreur", "Avoir introuvable.", type_='error')
                return

            cursor.execute(
                """
                SELECT ad.idmag, m.designationmag, ad.idarticle, u.codearticle,
                       a.designation, ad.idunite, u.designationunite, ad.qtavoir, ad.prixunit
                FROM tb_avoirdetail ad
                INNER JOIN tb_article a ON ad.idarticle = a.idarticle
                INNER JOIN tb_unite   u ON ad.idunite   = u.idunite
                INNER JOIN tb_magasin m ON ad.idmag     = m.idmag
                WHERE ad.idavoir = %s
                """,
                (idavoir,),
            )
            details = cursor.fetchall()

            self.reset_form(reset_imprimer=False)

            self.mode_modification               = True
            self.idvente_charge                  = idavoir
            self.derniere_idvente_enregistree    = idavoir

            self.entry_ref_avoir.configure(state="normal")
            self.entry_ref_avoir.delete(0, "end")
            self.entry_ref_avoir.insert(0, avoir[1])
            self.entry_ref_avoir.configure(state="readonly")

            self.entry_date_avoir.delete(0, "end")
            self.entry_date_avoir.insert(0, avoir[2].strftime("%d/%m/%Y %H:%M:%S"))

            self.entry_client.delete(0, "end")
            self.entry_client.insert(0, avoir[4] or "Client Inconnu")

            self.entry_designation.delete(0, "end")
            self.entry_designation.insert(0, avoir[3] or "")

            self.detail_avoir = []
            for d in details:
                idmag, designationmag, idarticle, codearticle, designation, \
                    idunite, designationunite, qtavoir, prixunit = d
                self.detail_avoir.append({
                    'idmag': idmag, 'designationmag': designationmag,
                    'idarticle': idarticle, 'code_article': codearticle,
                    'nom_article': designation, 'idunite': idunite,
                    'nom_unite': designationunite,
                    'qtvente': qtavoir,  # alias 'qtvente' pour compatibilité
                    'prixunit': prixunit,
                })

            self.charger_details_treeview()

            # Mode consultation : tout verrouillé
            for w in (self.entry_designation, self.entry_date_avoir, self.entry_client):
                w.configure(state="readonly")
            self.combo_magasin.configure(state="disabled")
            self.btn_imprimer.configure(state="normal")
            self.btn_imprimer.grid()
            self.btn_enregistrer.configure(state="disabled", text="📄 Mode Consultation")
            self.btn_recherche_article.configure(state="disabled")
            self.btn_ajouter.configure(state="disabled")
            self.btn_supprimer_ligne.configure(state="disabled")

            MessageDialog(
                "Chargement réussi",
                f"Avoir {avoir[1]} chargé.\nVous pouvez maintenant l'imprimer.\n\n"
                "Note : L'enregistrement est désactivé en mode consultation.",
                type_='info'
            )

        except Exception as e:
            MessageDialog("Erreur", f"Chargement avoir : {e}", type_='error')
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if conn:
                conn.close()

    def charger_vente_pour_transformation(self, idvente: int):
        """
        Charge une facture pour transformation en avoir (alias alternatif).
        Quantités modifiables, articles/unités/prix verrouillés.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        conn = self.connect_db()
        if not conn:
            return

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT v.id, v.refvente, v.dateregistre, v.description,
                       c.nomcli, v.idclient
                FROM tb_vente v
                LEFT JOIN tb_client c ON v.idclient = c.idclient
                WHERE v.id = %s
                """,
                (idvente,),
            )
            vente = cursor.fetchone()
            if not vente:
                MessageDialog("Erreur", "Facture introuvable.", type_='error')
                return

            cursor.execute(
                """
                SELECT vd.idmag, m.designationmag, vd.idarticle, u.codearticle,
                       a.designation, vd.idunite, u.designationunite, vd.qtvente,
                       vd.prixunit, COALESCE(vd.remise,0) AS remise
                FROM tb_ventedetail vd
                INNER JOIN tb_article a ON vd.idarticle = a.idarticle
                INNER JOIN tb_unite   u ON vd.idunite   = u.idunite
                INNER JOIN tb_magasin m ON vd.idmag     = m.idmag
                WHERE vd.idvente = %s
                """,
                (idvente,),
            )
            details = cursor.fetchall()

            self.reset_form(reset_imprimer=True)
            self.generer_reference()

            self.mode_modification  = False
            self.idvente_charge     = idvente

            self.entry_date_avoir.delete(0, "end")
            self.entry_date_avoir.insert(0, datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
            self.entry_client.delete(0, "end")
            self.entry_client.insert(0, vente[4] or "Client Inconnu")
            self.entry_designation.delete(0, "end")
            self.entry_designation.insert(0, f"Avoir de la facture {vente[1]}")
            self.entry_designation.configure(state="readonly")
            self.entry_date_avoir.configure(state="readonly")

            self.detail_avoir = []
            for d in details:
                idmag, designationmag, idarticle, codearticle, designation, \
                    idunite, designationunite, qtvente, prixunit, remise = d
                self.detail_avoir.append({
                    'idmag': idmag, 'designationmag': designationmag,
                    'idarticle': idarticle, 'code_article': codearticle,
                    'nom_article': designation, 'idunite': idunite,
                    'nom_unite': designationunite,
                    'qtvente': qtvente, 'qt_origine': qtvente,
                    'prixunit': prixunit, 'remise': float(remise or 0),
                })

            self.charger_details_treeview()

            try:
                self.btn_enregistrer.configure(
                    state="normal", text="💾 Enregistrer Avoir",
                    command=self.enregistrer_avoir,
                )
                self.btn_recherche_article.configure(state="disabled")
                self.btn_ajouter.configure(state="normal")
                self.btn_supprimer_ligne.configure(state="disabled")
                self.btn_imprimer.configure(state="disabled")
            except Exception:
                pass

            MessageDialog(
                "Transformation",
                f"Facture {vente[1]} chargée.\n"
                "Seules les quantités sont modifiables.",
                type_='info'
            )

        except Exception as e:
            MessageDialog("Erreur", f"Chargement transformation : {e}", type_='error')
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if conn:
                conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 10 — ENREGISTREMENT DE L'AVOIR
    # ══════════════════════════════════════════════════════════════════════════

    def enregistrer_avoir(self):
        """
        Enregistre l'avoir dans tb_avoir + tb_avoirdetail.
        Insère automatiquement dans tb_pmtavoir.
        Lance l'impression selon les paramètres settings.json.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        if self._is_saving_avoir:
            return

        self._is_saving_avoir = True
        try:
            self.btn_enregistrer.configure(state="disabled", text="⏳ Enregistrement...")
            self.update_idletasks()
        except Exception:
            pass

        conn = None
        success = False
        try:
            if not self.detail_avoir:
                MessageDialog("Attention", "Aucun détail à enregistrer.", type_='warning')
                return

            # Filtrer les lignes avec quantité > 0
            details_a_enregistrer = [d for d in self.detail_avoir if d.get('qtvente', 0) > 0]

            if not details_a_enregistrer:
                MessageDialog("Attention", "Aucun article avec quantité > 0.", type_='warning')
                return

            # Validation quantités
            for d in details_a_enregistrer:
                if d.get('qtvente', 0) < 0:
                    MessageDialog("Erreur", "Les quantités doivent être positives.", type_='error')
                    return
                if 'qt_origine' in d and d.get('qtvente', 0) > d.get('qt_origine', 0):
                    MessageDialog(
                        "Erreur",
                        f"Qt avoir '{d['nom_article']}' ({self.formater_nombre(d['qtvente'])}) "
                        f"> Qt vendue ({self.formater_nombre(d['qt_origine'])})."
                    )
                    return

            conn = self.connect_db()
            if not conn:
                return

            ref_avoir    = self.entry_ref_avoir.get()
            date_str     = self.entry_date_avoir.get()
            description  = self.entry_designation.get().strip() + " (Ref: " + ref_avoir + ")"
            client_nom   = self.entry_client.get().strip()

            idclient = self.client_map.get(client_nom)
            if not idclient:
                try:
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO tb_client (nomcli, deleted) VALUES (%s, 0) RETURNING idclient",
                        (client_nom,),
                    )
                    idclient = cur.fetchone()[0]
                    conn.commit()
                    self.client_map[client_nom] = idclient
                    cur.close()
                except Exception as e:
                    conn.rollback()
                    MessageDialog("Erreur", f"Impossible d'ajouter le client : {e}", type_='error')
                    return

            cur = conn.cursor()

            try:
                datereg = datetime.strptime(date_str, "%d/%m/%Y %H:%M:%S")
            except ValueError:
                MessageDialog("Erreur de Date",
                              "Format attendu : JJ/MM/AAAA HH:MM:SS", type_='error')
                return

            # Calcul montant total avoir
            montant_total_avoir = sum(
                float(d.get('qtvente', 0) or 0) *
                (float(d.get('prixunit', 0) or 0) - float(d.get('remise', 0) or 0))
                for d in details_a_enregistrer
            )

            dateavoir = datetime.now()

            # Insertion en-tête avoir
            cur.execute(
                """
                INSERT INTO tb_avoir
                    (refavoir, dateregistre, dateavoir, observation, iduser, idclient, mtavoir, deleted)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 0)
                RETURNING id
                """,
                (ref_avoir, datereg, dateavoir, description,
                 self.id_user_connecte, idclient, montant_total_avoir),
            )
            id_avoir = cur.fetchone()[0]

            # Insertion détails
            params = []
            for d in details_a_enregistrer:
                prixunit_net = float(d.get('prixunit', 0) or 0) - float(d.get('remise', 0) or 0)
                params.append((
                    id_avoir, d['idmag'], d['idarticle'], d['idunite'],
                    d['qtvente'], max(prixunit_net, 0.0),
                ))
            cur.executemany(
                "INSERT INTO tb_avoirdetail (idavoir, idmag, idarticle, idunite, qtavoir, prixunit) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                params,
            )

            # Récupération refvente associé
            refvente_associe = None
            if self.idvente_charge:
                cur.execute(
                    "SELECT refvente FROM tb_vente WHERE id = %s",
                    (self.idvente_charge,),
                )
                row = cur.fetchone()
                if row:
                    refvente_associe = row[0]

            # Récupération infos paiement depuis tb_pmtfacture
            id_banque = None
            idmode    = None
            if refvente_associe:
                cur.execute(
                    "SELECT id_banque, idmode FROM tb_pmtfacture "
                    "WHERE refvente = %s ORDER BY id DESC LIMIT 1",
                    (refvente_associe,),
                )
                row_pmt = cur.fetchone()
                if row_pmt:
                    id_banque = row_pmt[0]
                    idmode    = row_pmt[1]

            # Insertion dans tb_pmtavoir
            observation_pmt = self.entry_designation.get().strip() + " [CL: " + client_nom + "]"
            cur.execute(
                """
                INSERT INTO tb_pmtavoir
                    (datepmt, mtpaye, observation, idtypeoperation, deleted,
                     refvente, refavoir, id_banque, iduser, idmode)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (dateavoir, montant_total_avoir, observation_pmt,
                 2, 0, refvente_associe, ref_avoir, id_banque,
                 self.id_user_connecte, idmode),
            )

            conn.commit()

            # Confirmation + impression selon settings
            show_confirmation = self.settings.get('Avoir_ImpressionConfirmation', 1)
            if show_confirmation:
                MessageDialog(
                    "Succès",
                    f"Avoir N°{ref_avoir} enregistré.\n"
                    f"Montant : {self.formater_nombre(montant_total_avoir)}\n"
                    "Paiement enregistré dans tb_pmtavoir.",
                    type_='info',
                )
            else:
                print(f"✅ Avoir N°{ref_avoir} enregistré (impression directe)")

            self.derniere_idvente_enregistree = id_avoir
            self.btn_imprimer.configure(state="normal")
            self.btn_imprimer.grid()
            self.btn_enregistrer.configure(state="disabled", text="✔ Avoir Enregistré")
            success = True

            # Impression automatique
            impression_a5     = self.settings.get('Avoir_ImpressionA5', 1)
            impression_ticket = self.settings.get('Avoir_ImpressionTicket', 0)
            if impression_a5 or impression_ticket:
                self.imprimer_avoir_avec_settings(id_avoir, impression_a5, impression_ticket)

        except Exception as e:
            if conn:
                conn.rollback()
            MessageDialog("Erreur BD", f"Enregistrement : {e}", type_='error')
            traceback.print_exc()
        finally:
            if 'cur' in locals():
                cur.close()
            if conn:
                conn.close()
            if not success:
                self._is_saving_avoir = False
                try:
                    self.btn_enregistrer.configure(
                        state="normal",
                        text="💾 Enregistrer l'Avoir",
                        command=self.enregistrer_avoir,
                    )
                except Exception:
                    pass

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 11 — IMPRESSION PDF
    # ══════════════════════════════════════════════════════════════════════════

    def imprimer_avoir_avec_settings(self, idavoir: int,
                                     imprimer_a5: int, imprimer_ticket: int):
        """Lance l'impression selon les flags de settings.json."""
        data = self.get_data_avoir(idavoir)
        if not data:
            print("⚠️ Données avoir introuvables pour l'impression.")
            return

        try:
            if imprimer_a5 == 1:
                fn = (f"Avoir_{data['avoir']['refavoir']}_"
                      f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
                self.generate_pdf_a5_avoir(data, fn)
                self.open_file(fn)
                print(f"✅ Impression A5 : {fn}")
        except Exception as e:
            print(f"❌ Erreur impression : {e}")
            MessageDialog("Erreur d'impression", str(e), type_='error')
            traceback.print_exc()

    def imprimer_avoir_automatique(self, idavoir: int):
        """Impression automatique A5 après enregistrement."""
        data = self.get_data_avoir(idavoir)
        if not data:
            MessageDialog("Attention", "Données de l'avoir introuvables.", type_='warning')
            return
        try:
            fn = (f"Avoir_{data['avoir']['refavoir']}_"
                  f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
            self.generate_pdf_a5_avoir(data, fn)
            self.open_file(fn)
            MessageDialog("Impression", f"Avoir imprimé : {fn}", type_='info')
        except Exception as e:
            MessageDialog("Erreur d'impression", str(e), type_='error')
            traceback.print_exc()

    def get_data_avoir(self, idavoir: int) -> Optional[Dict[str, Any]]:
        """
        Récupère les données complètes d'un avoir pour l'impression.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        conn = self.connect_db()
        if not conn:
            return None

        data = {'societe': self.infos_societe, 'avoir': None,
                'utilisateur': None, 'client': None, 'details': []}

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT a.refavoir, a.dateregistre, a.dateavoir, a.observation, a.mtavoir,
                       u.nomuser, u.prenomuser,
                       c.nomcli, c.adressecli, c.contactcli
                FROM tb_avoir a
                INNER JOIN tb_users u ON a.iduser = u.iduser
                LEFT JOIN  tb_client c ON a.idclient = c.idclient
                WHERE a.id = %s
                """,
                (idavoir,),
            )
            avoir_result = cursor.fetchone()

            if not avoir_result:
                MessageDialog("Erreur", "Avoir introuvable.", type_='error')
                return None

            dateavoir_str = (
                avoir_result[2].strftime("%d/%m/%Y")
                if avoir_result[2] else datetime.now().strftime("%d/%m/%Y")
            )

            data['avoir'] = {
                'refavoir':        avoir_result[0],
                'dateregistre':    avoir_result[1].strftime("%d/%m/%Y"),
                'dateavoir':       dateavoir_str,
                'observation':     avoir_result[3] or '',
                'mtavoir':         avoir_result[4] or 0.0,
                'refvente_associe': '',
                'magasin_vente':   '',
            }
            data['utilisateur'] = {'nomuser': avoir_result[5], 'prenomuser': avoir_result[6]}
            data['client']      = {
                'nomcli':     avoir_result[7] or 'Client Inconnu',
                'adressecli': avoir_result[8] or 'N/A',
                'contactcli': avoir_result[9] or 'N/A',
            }

            # Référence facture associée
            refvente_associe = None
            for sql in (
                "SELECT refvente FROM tb_pmtavoir WHERE refavoir=%s AND deleted=0 ORDER BY id DESC LIMIT 1",
                "SELECT refvente FROM tb_pmtfacture WHERE refavoir=%s ORDER BY id DESC LIMIT 1",
            ):
                try:
                    cursor.execute(sql, (data['avoir']['refavoir'],))
                    row = cursor.fetchone()
                    if row and row[0]:
                        refvente_associe = row[0]
                        data['avoir']['refvente_associe'] = refvente_associe
                        break
                except Exception:
                    pass

            # Détails de l'avoir
            cursor.execute(
                """
                SELECT u.codearticle, a.designation, u.designationunite,
                       ad.qtavoir, ad.prixunit,
                       ad.qtavoir * ad.prixunit AS montant_total,
                       m.designationmag,
                       COALESCE((
                           SELECT vd.prixunit FROM tb_vente v
                           INNER JOIN tb_ventedetail vd ON vd.idvente = v.id
                           WHERE v.refvente = %s
                             AND vd.idarticle = ad.idarticle
                             AND vd.idunite   = ad.idunite
                             AND vd.idmag     = ad.idmag
                           ORDER BY ABS((vd.prixunit - COALESCE(vd.remise,0)) - ad.prixunit), vd.id DESC
                           LIMIT 1
                       ), ad.prixunit) AS pu_ttc_brut
                FROM tb_avoirdetail ad
                INNER JOIN tb_article a ON ad.idarticle = a.idarticle
                INNER JOIN tb_unite   u ON ad.idunite   = u.idunite
                INNER JOIN tb_magasin m ON ad.idmag     = m.idmag
                WHERE ad.idavoir = %s
                ORDER BY a.designation
                """,
                (refvente_associe, idavoir),
            )
            data['details'] = cursor.fetchall()

            # Magasin principal
            try:
                magasins = [r[6] for r in data['details'] if len(r) > 6 and r[6]]
                if magasins:
                    data['avoir']['magasin_vente'] = magasins[0]
            except Exception:
                pass

            return data

        except Exception as e:
            MessageDialog("Erreur", f"Récupération données avoir : {e}", type_='error')
            traceback.print_exc()
            return None
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if conn:
                conn.close()

    def generate_pdf_a5_avoir(self, data: Dict[str, Any], filename: str):
        """
        Génère un PDF A5 pour un AVOIR.
        Multi-pages si articles > 25.
        TOTAL Ar / Fmg en bas du tableau.
        *** LOGIQUE MÉTIER IMPRESSION — NE PAS MODIFIER ***
        """
        from reportlab.lib.pagesizes import A5
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas as rl_cv
        from reportlab.platypus import Table, TableStyle, Paragraph

        MAX_ARTICLES_PAGE1     = 25
        MAX_ARTICLES_SUIVANTES = 30
        MARGIN                 = 10 * mm

        c = rl_cv.Canvas(filename, pagesize=A5)
        width, height = A5

        societe     = data['societe']
        utilisateur = data['utilisateur']
        client      = data['client']
        avoir       = data.get('avoir', {})

        nomsociete     = societe.get('nomsociete', 'N/A')
        adressesociete = societe.get('adressesociete') or 'N/A'
        contactsociete = societe.get('contactsociete') or 'N/A'
        nifsociete     = societe.get('nifsociete') or 'N/A'
        statsociete    = societe.get('statsociete') or 'N/A'

        if isinstance(utilisateur, dict):
            user_name = f"{utilisateur.get('prenomuser','') or ''} {utilisateur.get('nomuser','') or ''}".strip()
        else:
            user_name = str(utilisateur or '')

        refavoir          = avoir.get('refavoir', 'N/A')
        refvente_associe  = avoir.get('refvente_associe') or 'N/A'
        magasin_vente     = avoir.get('magasin_vente') or 'N/A'
        dateavoir         = avoir.get('dateavoir')
        dateavoir_affiche = (
            dateavoir.strftime("%d/%m/%Y %H:%M")
            if isinstance(dateavoir, datetime) else (dateavoir or "")
        )

        def draw_verset():
            verset = "Ankino amin'ny Jehovah ny asanao dia ho lavorary izay kasainao. Ohabolana 16:3"
            c.setLineWidth(1)
            c.rect(MARGIN, height - 15 * mm, width - 2 * MARGIN, 8 * mm)
            c.setFont("Helvetica-Bold", 9)
            c.drawCentredString(width / 2, height - 12.5 * mm, verset)

        def draw_header(is_continuation=False):
            styles  = getSampleStyleSheet()
            style_p = ParagraphStyle('p', fontSize=9, leading=11, parent=styles['Normal'])

            suite_label = " <i>(suite)</i>" if is_continuation else ""
            gauche = Paragraph(
                f"<b>{nomsociete}</b><br/>{adressesociete}<br/>"
                f"TEL: {contactsociete}<br/>NIF: {nifsociete}<br/>STAT: {statsociete}",
                style_p,
            )
            droite = Paragraph(
                f"<b>AVOIR N°: {refavoir}{suite_label}</b><br/>"
                f"<b>Du Ref: {refvente_associe}</b><br/>"
                f"{dateavoir_affiche}<br/>"
                f"<b>Magasin {magasin_vente}</b><br/>"
                f"<b>CLIENT: {client['nomcli']}</b><br/>"
                f"<font size='8'>Op: {user_name}</font>",
                style_p,
            )
            ht = Table([[gauche, droite]], colWidths=[64 * mm, 64 * mm])
            ht.setStyle(TableStyle([
                ('GRID',          (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING',   (0, 0), (-1, -1), 8),
                ('TOPPADDING',    (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            ht.wrapOn(c, width, height)
            ht.drawOn(c, MARGIN, height - 42 * mm)

        def draw_footer(total_montant, table_bottom):
            styles  = getSampleStyleSheet()
            usable_width = width - 2 * MARGIN
            montant_lettres = nombre_en_lettres_fr(int(total_montant)).upper()

            p_lettre = Paragraph(
                f"ARRETE A LA SOMME DE {montant_lettres} ARIARY TTC",
                ParagraphStyle('fb', parent=styles['Normal'],
                               fontName='Helvetica-Bold', fontSize=9,
                               leading=12, alignment=1),
            )
            p_mention = Paragraph(
                "Nous déclinons la responsabilité des marchandises "
                "non livrées au-delà de 5 jours",
                ParagraphStyle('fi', parent=styles['Normal'],
                               fontName='Helvetica-Oblique', fontSize=8,
                               leading=10, alignment=1),
            )
            _, h_l = p_lettre.wrap(usable_width, 40 * mm)
            _, h_m = p_mention.wrap(usable_width, 20 * mm)

            p_lettre.drawOn(c,  MARGIN, table_bottom - 3 * mm - h_l)
            p_mention.drawOn(c, MARGIN, table_bottom - 3 * mm - h_l - 2 * mm - h_m)

            c.setFont("Helvetica-Bold", 10)
            c.drawString(MARGIN, 15 * mm, "Le Client")
            c.drawCentredString(width / 2, 15 * mm, "Le Caissier")
            c.drawString(width - 35 * mm, 15 * mm, "Le Magasinier")

        def draw_article_table(table_top, table_bottom, rows, show_totals, total_montant=0):
            frame_height = table_top - table_bottom
            col_widths   = [12 * mm, 15 * mm, 62 * mm, 19.5 * mm, 19.5 * mm]
            row_height_est = 5.5 * mm
            max_rows = int(frame_height / row_height_est)
            reserved = 2 if show_totals else 0
            content_slots = max_rows - 1 - reserved

            body = list(rows)
            for _ in range(max(0, content_slots - len(body))):
                body.append(['', '', '', '', ''])

            if show_totals:
                montant_fmg = int(total_montant * 5)
                table_data = (
                    [['QTE', 'UNITE', 'DESIGNATION', 'PU TTC', 'MONTANT']]
                    + body
                    + [['', '', 'TOTAL Ar :', self.formater_nombre(total_montant), ''],
                       ['', '', 'Fmg :',      self.formater_nombre(montant_fmg),   '']]
                )
            else:
                table_data = [['QTE', 'UNITE', 'DESIGNATION', 'PU TTC', 'MONTANT']] + body

            c.setLineWidth(1)
            c.rect(MARGIN, table_bottom, width - 2 * MARGIN, frame_height)
            x_pos = MARGIN
            for w in col_widths[:-1]:
                x_pos += w
                c.line(x_pos, table_top, x_pos, table_bottom)

            actual_rh   = frame_height / len(table_data)
            row_heights = [actual_rh] * len(table_data)

            style_cmds = [
                ('BACKGROUND',    (0, 0),  (-1, 0),  colors.lightgrey),
                ('FONTNAME',      (0, 0),  (-1, 0),  'Helvetica-Bold'),
                ('FONTSIZE',      (0, 0),  (-1, 0),  10),
                ('LINEBELOW',     (0, 0),  (-1, 0),  1, colors.black),
                ('FONTSIZE',      (0, 1),  (-1, -1),  8),
                ('ALIGN',         (3, 0),  (-1, -1), 'RIGHT'),
                ('ALIGN',         (0, 0),  (2, 0),   'LEFT'),
                ('VALIGN',        (0, 0),  (-1, -1), 'MIDDLE'),
                ('LEFTPADDING',   (0, 0),  (-1, -1),  2),
                ('RIGHTPADDING',  (3, 0),  (-1, -1),  2),
                ('TOPPADDING',    (0, 0),  (-1, -1),  0),
                ('BOTTOMPADDING', (0, 0),  (-1, -1),  0),
            ]

            if show_totals:
                style_cmds += [
                    ('BACKGROUND', (0, -2), (-1, -1), colors.Color(0.93, 0.93, 0.93)),
                    ('FONTNAME',   (0, -2), (-1, -1), 'Helvetica-Bold'),
                    ('FONTSIZE',   (0, -2), (-1, -1),  9),
                    ('LINEABOVE',  (0, -2), (-1, -2),  1, colors.black),
                    ('ALIGN',      (2, -2), (2, -1),  'RIGHT'),
                ]

            t = Table(table_data, colWidths=col_widths, rowHeights=row_heights)
            t.setStyle(TableStyle(style_cmds))
            t.wrapOn(c, width, height)
            t.drawOn(c, MARGIN, table_top - len(table_data) * actual_rh)
            return table_bottom

        # Préparation des lignes
        total_montant = 0.0
        all_rows      = []
        for detail in data['details']:
            if isinstance(detail, (list, tuple)) and len(detail) >= 8:
                code, designation, unite, qtavoir, prixunit_net, montant_total, magasin, pu_ttc_brut = detail[:8]
                prixunit_affiche = pu_ttc_brut
                montant          = montant_total
            elif isinstance(detail, (list, tuple)) and len(detail) >= 7:
                code, designation, unite, qtavoir, prixunit_net, montant_total, magasin = detail[:7]
                prixunit_affiche = prixunit_net
                montant          = montant_total
            else:
                qtavoir          = detail.get('qtavoir', detail.get('qte', 0))
                designation      = detail.get('designation', '')
                unite            = detail.get('unite', '')
                prixunit_affiche = detail.get('pu_ttc_brut', detail.get('prixunit', 0))
                montant          = detail.get('montant_ttc', detail.get('montant', 0))

            total_montant += montant
            all_rows.append([
                str(int(qtavoir)),
                str(unite),
                str(designation),
                self.formater_nombre(prixunit_affiche),
                self.formater_nombre(montant),
            ])

        # Découpage en pages
        pages = []
        if len(all_rows) <= MAX_ARTICLES_PAGE1:
            pages.append(('first', all_rows))
        else:
            pages.append(('first', all_rows[:MAX_ARTICLES_PAGE1]))
            reste = all_rows[MAX_ARTICLES_PAGE1:]
            while reste:
                pages.append(('continuation', reste[:MAX_ARTICLES_SUIVANTES]))
                reste = reste[MAX_ARTICLES_SUIVANTES:]

        # Rendu page par page
        for page_idx, (page_type, rows) in enumerate(pages):
            is_last = (page_idx == len(pages) - 1)

            draw_verset()
            draw_header(is_continuation=(page_type == 'continuation'))

            table_top    = height - 52 * mm
            table_bottom = 55 * mm if is_last else 15 * mm

            tb = draw_article_table(
                table_top, table_bottom, rows,
                show_totals=is_last, total_montant=total_montant,
            )

            if is_last:
                draw_footer(total_montant, table_bottom=tb)

            if len(pages) > 1:
                c.setFont("Helvetica", 7)
                c.drawCentredString(width / 2, 8 * mm,
                                    f"Page {page_idx + 1} / {len(pages)}")

            if not is_last:
                c.showPage()

        try:
            c.save()
            print(f"✅ PDF généré : {filename}")
        except Exception as e:
            print(f"❌ Erreur PDF : {e}")
            traceback.print_exc()

    def open_impression_dialogue(self):
        """
        Ouvre le dialogue de choix de format d'impression
        (A5 PDF ou Ticket 80mm).
        """
        if not self.derniere_idvente_enregistree:
            MessageDialog("Attention",
                          "Enregistrez ou chargez un avoir d'abord.", type_='warning')
            return

        data = self.get_data_avoir(self.derniere_idvente_enregistree)
        if not data:
            return

        try:
            choice_dialog = SimpleDialogWithChoice(
                self.master,
                title="Format d'impression",
                message="Sélectionnez le format d'impression :",
            )
            result = choice_dialog.result
        except Exception as e:
            MessageDialog("Erreur", f"Dialogue d'impression : {e}", type_='error')
            return

        if result == "A5 PDF (Paysage)":
            fn = (f"Avoir_{data['avoir']['refavoir']}_"
                  f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
            self.generate_pdf_a5_avoir(data, fn)
            self.open_file(fn)
            MessageDialog("Impression", f"PDF généré : {fn}", type_='info')
        elif result == "Ticket 80mm":
            MessageDialog(
                "Information",
                "L'impression ticket pour les avoirs n'est pas encore disponible.",
                type_='info',
            )

    def create_watermark(self, canvas, doc):
        """Ajoute le filigrane 'AVOIR' en arrière-plan."""
        canvas.saveState()
        canvas.setFont('Helvetica-Bold', 100)
        canvas.setFillGray(0.5, 0.3)
        canvas.translate(297, 210)
        canvas.rotate(45)
        canvas.drawCentredString(0, 0, "AVOIR")
        canvas.restoreState()

    def open_file(self, filename):
        """Ouvre un fichier avec l'application par défaut du système."""
        try:
            if sys.platform == 'win32':
                os.startfile(filename)
            elif sys.platform == 'darwin':
                os.system(f'open "{filename}"')
            else:
                os.system(f'xdg-open "{filename}"')
        except Exception:
            pass

    def get_data_facture(self, idvente: int) -> Optional[Dict[str, Any]]:
        """
        Récupère les données d'une facture de vente pour l'impression.
        Conservé pour rétrocompatibilité.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        conn = self.connect_db()
        if not conn:
            return None

        data = {'societe': self.infos_societe, 'vente': None,
                'utilisateur': None, 'details': []}

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT v.refvente, v.dateregistre, v.description,
                       u.nomuser, u.prenomuser,
                       c.nomcli, c.adressecli, c.contactcli
                FROM tb_vente v
                INNER JOIN tb_users  u ON v.iduser   = u.iduser
                LEFT JOIN  tb_client c ON v.idclient = c.idclient
                WHERE v.id = %s
                """,
                (idvente,),
            )
            vente_result = cursor.fetchone()

            if not vente_result:
                MessageDialog("Erreur", "Facture introuvable.", type_='error')
                return None

            data['vente']       = {
                'refvente':    vente_result[0],
                'dateregistre': vente_result[1].strftime("%d/%m/%Y"),
                'description': vente_result[2],
            }
            data['utilisateur'] = {'nomuser': vente_result[3], 'prenomuser': vente_result[4]}
            data['client']      = {
                'nomcli':     vente_result[5] or 'Client Inconnu',
                'adressecli': vente_result[6] or 'N/A',
                'contactcli': vente_result[7] or 'N/A',
            }

            cursor.execute(
                """
                SELECT u.codearticle, a.designation, u.designationunite,
                       vd.qtvente, vd.prixunit,
                       vd.qtvente * vd.prixunit AS montant_total,
                       m.designationmag
                FROM tb_ventedetail vd
                INNER JOIN tb_article a ON vd.idarticle = a.idarticle
                INNER JOIN tb_unite   u ON vd.idunite   = u.idunite
                INNER JOIN tb_magasin m ON vd.idmag     = m.idmag
                WHERE vd.idvente = %s
                ORDER BY a.designation
                """,
                (idvente,),
            )
            data['details'] = cursor.fetchall()
            return data

        except Exception as e:
            MessageDialog("Erreur", f"Données facture : {e}", type_='error')
            return None
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if conn:
                conn.close()

    def generate_ticket_80mm(self, data: Dict[str, Any], filename: str):
        """
        Génère un ticket de caisse 80mm (texte brut).
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        societe = data['societe']
        vente   = data['vente']
        client  = data['client']
        details = data['details']

        MAX_WIDTH = 40

        def center(text): return text.center(MAX_WIDTH)
        def line():       return "-" * MAX_WIDTH

        def format_detail_line(designation, qte, unite, prixunit, montant_total):
            lines = textwrap.wrap(designation, MAX_WIDTH)
            qte_pu_line    = f"{self.formater_nombre(qte)} {unite} @ {self.formater_nombre(prixunit)}"
            montant_str    = self.formater_nombre(montant_total)
            if len(qte_pu_line) + len(montant_str) + 1 <= MAX_WIDTH:
                lines.append(
                    qte_pu_line.ljust(MAX_WIDTH - len(montant_str) - 1) + montant_str.rjust(len(montant_str))
                )
            else:
                lines += [qte_pu_line, montant_str.rjust(MAX_WIDTH)]
            lines.append("")
            return lines

        content  = [
            center(societe.get('nomsociete', 'SOCIÉTÉ')),
            center(societe.get('adressesociete', 'N/A')),
            center(f"Tél: {societe.get('contactsociete','N/A')}"),
            line(),
            f"Facture N°: {vente['refvente']}",
            f"Date: {vente['dateregistre']}",
            f"Client: {client['nomcli']}",
            line(),
        ]

        total_general = 0.0
        for code, designation, unite, qte, prixunit, montant_total, magasin in details:
            content.extend(format_detail_line(designation, qte, unite, prixunit, montant_total))
            total_general += montant_total

        content += [
            line(),
            f"TOTAL À PAYER: {self.formater_nombre(total_general)}".rjust(MAX_WIDTH),
            line(),
            center("TOTAL EN LETTRES"),
            *textwrap.wrap(nombre_en_lettres_fr(total_general), MAX_WIDTH, subsequent_indent='  '),
            line(),
            center(vente['description']),
            "\n",
            center("Merci de votre achat !"),
        ]

        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 12 — TRI TREEVIEW
    # ══════════════════════════════════════════════════════════════════════════

    def sort_tree(self, tree, col):
        """
        Tri des éléments du Treeview par colonne.
        Bascule l'ordre ascendant/descendant à chaque appel.
        """
        children = tree.get_children('')
        vals     = [(tree.set(k, col), k) for k in children]
        reverse  = getattr(tree, f"_sort_reverse_{col}", False)

        try:
            if col == "Montant Total":
                def keyfn(x):
                    txt = (x[0] or "0").replace(" ", "").replace(".", "").replace(",", ".")
                    try:
                        return float(txt)
                    except Exception:
                        return 0.0
            elif col == "Date":
                from datetime import datetime as _dt
                def keyfn(x):
                    try:
                        return _dt.strptime(x[0] or "", "%d/%m/%Y")
                    except Exception:
                        return _dt.min
            else:
                def keyfn(x):
                    return x[0] or ""

            vals.sort(key=keyfn, reverse=reverse)
        except Exception:
            vals.sort(reverse=reverse)

        for index, (_, item) in enumerate(vals):
            tree.move(item, '', index)

        setattr(tree, f"_sort_reverse_{col}", not reverse)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 13 — RÉINITIALISATION FORMULAIRE COMPLET
    # ══════════════════════════════════════════════════════════════════════════

    def reset_form(self, reset_imprimer: bool = True):
        """
        Réinitialise complètement le formulaire de l'avoir :
        vide tous les champs, réactive les boutons, recharge la référence.
        """
        self.detail_avoir             = []
        self.article_selectionne      = None
        self.index_ligne_selectionnee = None
        self.mode_modification        = False
        self.idvente_charge           = None

        # Champs d'en-tête
        self.entry_date_avoir.configure(state="normal")
        self.entry_date_avoir.delete(0, "end")
        self.entry_date_avoir.insert(0, datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

        self.entry_designation.configure(state="normal")
        self.entry_designation.delete(0, "end")
        self.entry_designation.configure(state="disabled")

        self.entry_client.configure(state="normal")
        self.entry_client.delete(0, "end")

        self.combo_magasin.configure(state="normal")

        # Rechargements
        self.charger_magasins()
        self.charger_client()
        self.generer_reference()

        # Réinitialiser saisie article
        self.reset_detail_form()

        # Vider le Treeview
        for item in self.tree_details.get_children():
            self.tree_details.delete(item)

        # Remettre les boutons dans leur état initial
        self.btn_enregistrer.configure(
            state="normal", text="💾 Enregistrer l'Avoir",
            command=self.enregistrer_avoir,
        )
        self.btn_recherche_article.configure(state="disabled")
        self.btn_ajouter.configure(state="normal")
        self.btn_supprimer_ligne.configure(state="disabled")

        if reset_imprimer:
            self.btn_imprimer.configure(state="disabled")
            self.btn_imprimer.grid_remove()
            self.derniere_idvente_enregistree = None

        # Recalcul totaux (tout à zéro)
        self.calculer_totaux()

    def nouveau_facture(self):
        """Alias : réinitialise pour un nouvel avoir."""
        self.reset_form(reset_imprimer=True)
        MessageDialog("Nouveau", "Formulaire d'avoir prêt.", type_='info')


# ==============================================================================
# POINT D'ENTRÉE AUTONOME (test unitaire)
# ==============================================================================

if __name__ == "__main__":
    USER_ID = 1

    try:
        app = ctk.CTk()
        app.title("iJeery — Page Avoir (test)")
        app.geometry("1300x800")

        page_avoir = PageAvoir(app, id_user_connecte=USER_ID)
        page_avoir.pack(fill="both", expand=True, padx=6, pady=6)

        app.mainloop()

    except Exception as e:
        print(f"Erreur critique :\n{traceback.format_exc()}")
