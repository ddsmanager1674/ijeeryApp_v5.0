# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              iJeery — page_vente_par_msin.py  (refactorisé)                ║
║           Page principale de gestion des ventes (Facturation)               ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Refactoring v2.0 :                                                          ║
║    • Thème iJeery (Colors, Fonts, styled) intégré                            ║
║    • Système d'onglets TTK propre (Chrome-like)                              ║
║    • Layout responsive et léger avec grid() optimisé                         ║
║    • Chargement différé : DB sollicitée uniquement quand nécessaire          ║
║    • Toute la logique métier d'origine conservée intacte                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

# ──────────────────────────────────────────────────────────────────────────────
# IMPORTS STANDARDS
# ──────────────────────────────────────────────────────────────────────────────
import os
import sys
import json
import traceback
import textwrap
from datetime import datetime
from typing import Optional, Dict, Any, List

# ──────────────────────────────────────────────────────────────────────────────
# IMPORTS TIERS
# ──────────────────────────────────────────────────────────────────────────────
import customtkinter as ctk
from tkinter import messagebox, ttk
import psycopg2

# PDF via ReportLab
from reportlab.lib.pagesizes import A5
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ──────────────────────────────────────────────────────────────────────────────
# IMPORTS LOCAUX
# ──────────────────────────────────────────────────────────────────────────────
from app_theme import Colors, Fonts, styled, Theme
from resource_utils import get_config_path, safe_file_read
from pages.page_avoir import PageAvoir
from pages.page_proforma import PageCommandeCli


# ==============================================================================
# DIALOGUE MOT DE PASSE — inchangé (logique d'autorisation)
# ==============================================================================
class PasswordDialog(ctk.CTkToplevel):
    """Dialogue modal sécurisé pour saisir un code d'autorisation (remise, avoir…)."""

    def __init__(self, title: str, text: str):
        super().__init__()
        self.title(title)
        self.geometry("320x160")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_CARD)
        self.result = None

        ctk.CTkLabel(self, text=text, font=Fonts.body(12),
                     text_color=Colors.TEXT_PRIMARY).pack(pady=(18, 6), padx=20)

        self.entry = ctk.CTkEntry(self, show="*", font=Fonts.input(13),
                                  fg_color=Colors.BG_INPUT,
                                  border_color=Colors.BORDER, height=36)
        self.entry.pack(pady=(0, 10), padx=20, fill="x")
        self.entry.focus_set()
        # Entrée clavier → valider directement
        self.entry.bind("<Return>", lambda _e: self._ok())

        styled.button_primary(self, text="Valider", command=self._ok,
                              width=120, height=36).pack(pady=(0, 14))
        self.grab_set()
        self.wait_window()

    def _ok(self):
        self.result = self.entry.get()
        self.destroy()


# ==============================================================================
# DIALOGUE DE CHOIX DU FORMAT D'IMPRESSION — inchangé
# ==============================================================================
class SimpleDialogWithChoice(ctk.CTkToplevel):
    """Dialogue pour choisir entre A5 PDF Paysage et Ticket 80 mm."""

    def __init__(self, master, title: str, message: str):
        super().__init__(master)
        self.title(title)
        self.configure(fg_color=Colors.BG_CARD)
        self.transient(master)
        self.grab_set()
        self.result = None
        self.choice = ctk.StringVar(self, value="A5 PDF (Paysage)")

        ctk.CTkLabel(self, text=message, wraplength=350,
                     font=Fonts.body(12), text_color=Colors.TEXT_PRIMARY,
                     justify="left").pack(pady=12, padx=20)

        rf = ctk.CTkFrame(self, fg_color=Colors.BG_INPUT, corner_radius=8)
        rf.pack(pady=4, padx=20, fill="x")

        ctk.CTkRadioButton(rf, text="A5 PDF (Paysage)",
                           variable=self.choice, value="A5 PDF (Paysage)",
                           font=Fonts.body(12),
                           text_color=Colors.TEXT_PRIMARY).pack(pady=6, padx=12, anchor="w")
        ctk.CTkRadioButton(rf, text="Ticket de Caisse 80 mm",
                           variable=self.choice, value="Ticket 80mm",
                           font=Fonts.body(12),
                           text_color=Colors.TEXT_PRIMARY).pack(pady=6, padx=12, anchor="w")

        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(pady=12, padx=20)
        styled.button_danger(bf, text="Annuler", command=self._cancel,
                             width=120).pack(side="left", padx=6)
        styled.button_success(bf, text="Imprimer", command=self._ok,
                              width=120).pack(side="right", padx=6)

        self.wait_window(self)

    def _ok(self):
        self.result = self.choice.get()
        self.grab_release()
        self.destroy()

    def _cancel(self):
        self.result = None
        self.grab_release()
        self.destroy()


# ==============================================================================
# UTILITAIRE : CONVERSION NOMBRE → LETTRES (FRANÇAIS) — inchangé
# ==============================================================================
def nombre_en_lettres_fr(montant: float) -> str:
    """
    Convertit un montant numérique en sa représentation en lettres en français.
    Gère les Millions et les Milliers correctement.
    """
    from math import floor

    if montant is None:
        return ""
    try:
        montant = round(float(montant), 2)
    except ValueError:
        return ""

    unites       = ["", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf"]
    dix_a_16     = ["dix", "onze", "douze", "treize", "quatorze", "quinze", "seize"]
    dizaines     = ["", "dix", "vingt", "trente", "quarante", "cinquante",
                    "soixante", "soixante", "quatre-vingt", "quatre-vingt"]

    def _simple(n):
        if n == 0: return ""
        if n < 10: return unites[n]
        if n < 17: return dix_a_16[n - 10]
        if n < 20: return "dix-" + unites[n - 10]
        d, u = n // 10, n % 10
        p = dizaines[d]
        if d in (2,) and u == 1: p += " et"
        if d in (7, 9): return p + "-" + _simple(n - d * 10) if u else p + "-" + _simple(10)
        if u:
            if d > 6 and u == 1: p += " et"
            return p + "-" + unites[u]
        return p

    def _bloc(n):
        if n == 0: return ""
        if n < 100: return _simple(n)
        c, r = n // 100, n % 100
        s = ("" if c == 1 else _simple(c) + "-") + "cent"
        if r == 0 and c > 1: s += "s"
        return s + ("-" + _bloc(r) if r else "")

    entier   = floor(montant)
    centimes = int(round((montant - entier) * 100))
    million  = entier // 1_000_000
    mille    = (entier % 1_000_000) // 1_000
    unite_r  = entier % 1_000

    parts = []
    if million: parts.append(_bloc(million) + (" millions" if million > 1 else " million"))
    if mille:   parts.append(_bloc(mille) + " mille")
    if unite_r: parts.append(_bloc(unite_r))
    if not parts: parts.append("zéro")

    res = " ".join(parts).strip().replace("  ", " ").replace("-", " ")
    if centimes:
        res += " et " + _bloc(centimes).replace("-", " ") + " centimes"

    return res.capitalize().replace(" et-", " et ")


# ==============================================================================
# PAGE PRINCIPALE DE VENTE
# ==============================================================================
class PageVenteParMsin(ctk.CTkFrame):
    """
    Frame principale de gestion des ventes (facturation par magasin).

    Utilisable :
      • en tant que frame standalone (tests, __main__)
      • intégrée dans un TTKNotebook (onglets de l'application principale)

    Architecture UI (grid rows) :
      Row 0 — Bandeau en-tête (référence, date, magasin, client)
      Row 1 — Bandeau saisie article (article, qté, unité, remise, prix)
      Row 2 — Tableau de détails (poids = 1 → expansible)
      Row 3 — Zone totaux
      Row 4 — Barre d'actions (boutons)
    """

    def __init__(self, master=None, id_user_connecte: Optional[int] = None) -> None:
        super().__init__(master)

        # ── Vérification utilisateur ──────────────────────────────────────────
        if id_user_connecte is None:
            messagebox.showerror("Erreur", "Aucun utilisateur connecté. Veuillez vous reconnecter.")
            self.id_user_connecte = None
        else:
            self.id_user_connecte = id_user_connecte
            print(f"✅ Utilisateur connecté — ID: {self.id_user_connecte}")

        # ── État interne ──────────────────────────────────────────────────────
        self.conn: Optional[psycopg2.connection] = None
        self.article_selectionne: Optional[Dict] = None
        self.stock_temporaire_selection: Optional[float] = None
        self.detail_vente: List[Dict] = []
        self.index_ligne_selectionnee: Optional[int] = None
        self.magasin_map: Dict[str, int] = {}
        self.magasin_ids: List[int] = []
        self.client_map: Dict[str, int] = {}
        self.client_ids: List[int] = []
        self.infos_societe: Dict[str, Any] = {}
        self.derniere_idvente_enregistree: Optional[int] = None
        self.mode_modification: bool = False
        self.idvente_charge: Optional[int] = None
        # Stockage temporaire des lignes d'un proforma avant ajout en masse
        self.details_proforma_a_ajouter: Optional[List[Dict]] = None
        self.details_proforma_a_ajouter_idprof: Optional[int] = None
        # Protection contre le double-clic d'enregistrement
        self._enregistrement_en_cours: bool = False

        # ── Chargement des paramètres d'impression ────────────────────────────
        self.settings = self._load_settings()

        # ── Thème du frame racine ─────────────────────────────────────────────
        self.configure(fg_color=Colors.BG_PAGE)

        # ── Configuration de la grille principale ─────────────────────────────
        self.grid_columnconfigure(0, weight=1)
        # Row 2 (tableau) prend tout l'espace disponible ; les autres rows sont fixes
        self.grid_rowconfigure(0, weight=0)  # en-tête
        self.grid_rowconfigure(1, weight=0)  # saisie article
        self.grid_rowconfigure(2, weight=1)  # tableau détails (expansible)
        self.grid_rowconfigure(3, weight=0)  # totaux
        self.grid_rowconfigure(4, weight=0)  # boutons d'action

        # ── Construction de l'interface ───────────────────────────────────────
        self._setup_ui()

        # ── Connexion DB et chargements initiaux ──────────────────────────────
        self.conn = self._connect_db()
        self.generer_reference()
        self.charger_magasins()
        self.charger_client()
        self.charger_infos_societe()

        # ── Responsivité ──────────────────────────────────────────────────────
        self.bind("<Configure>", self._on_resize)

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 1 — CONNEXION DATABASE
    # ──────────────────────────────────────────────────────────────────────────

    def _connect_db(self) -> Optional[psycopg2.connection]:
        """
        Ouvre une nouvelle connexion PostgreSQL à partir de config.json.
        Retourne None en cas d'erreur (évite les crashs silencieux).
        """
        try:
            with open(get_config_path('config.json')) as f:
                cfg = json.load(f)['database']
            return psycopg2.connect(
                host=cfg['host'], user=cfg['user'],
                password=cfg['password'], database=cfg['database'],
                port=cfg['port']
            )
        except FileNotFoundError:
            messagebox.showerror("Config manquante", "Fichier 'config.json' introuvable.")
        except psycopg2.Error as e:
            messagebox.showerror("Connexion DB", f"Impossible de se connecter : {e}")
        return None

    # Alias public conservé pour compatibilité avec le code existant
    def connect_db(self):
        return self._connect_db()

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 2 — PARAMÈTRES D'IMPRESSION
    # ──────────────────────────────────────────────────────────────────────────

    def _load_settings(self) -> Dict[str, Any]:
        """Charge settings.json ; retourne les valeurs par défaut si absent."""
        defaults = {
            'Vente_ImpressionConfirmation': 1,
            'Vente_ImpressionA5': 1,
            'Vente_ImpressionTicket': 0,
            'Avoir_ImpressionConfirmation': 1,
            'Avoir_ImpressionA5': 1,
            'Avoir_ImpressionTicket': 0,
        }
        try:
            with open('settings.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"⚠ settings.json : {e} — paramètres par défaut appliqués.")
        return defaults

    # Alias public
    def load_settings(self):
        return self._load_settings()

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 3 — FORMATAGE NOMBRES
    # ──────────────────────────────────────────────────────────────────────────

    def formater_nombre(self, n) -> str:
        """1 234 567,89  → format d'affichage IHM (avec décimales)."""
        try:
            return "{:,.2f}".format(float(n)).replace(',', '_T_').replace('.', ',').replace('_T_', '.')
        except Exception:
            return "0,00"

    def formater_nombre_pdf(self, n) -> str:
        """1 234 567  → format entier sans décimales pour les PDF."""
        try:
            return "{:,.0f}".format(float(n)).replace(',', '.')
        except Exception:
            return "0"

    def parser_nombre(self, texte: str) -> float:
        """Inverse de formater_nombre : '1.234,56' → 1234.56."""
        try:
            return float(str(texte).replace('.', '').replace(',', '.'))
        except Exception:
            return 0.0

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 4 — CONSTRUCTION DE L'INTERFACE (setup_ui)
    # ──────────────────────────────────────────────────────────────────────────

    def _setup_ui(self):
        """
        Construit les 5 zones de l'interface.
        Aucune logique métier ici — uniquement la mise en page.
        """
        self._build_header_band()   # Row 0 — en-tête facture
        self._build_article_band()  # Row 1 — saisie article
        self._build_detail_table()  # Row 2 — tableau de lignes
        self._build_totals_band()   # Row 3 — totaux
        self._build_action_bar()    # Row 4 — boutons

        # Calcul initial des totaux à zéro
        self.calculer_totaux()

    # ── 4.0  Bandeau en-tête facture ──────────────────────────────────────────
    def _build_header_band(self):
        """
        Ligne 0 : N° Facture | Date | Magasin | Client + loupe.
        Card blanche avec ombre légère.
        """
        card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD,
                            corner_radius=0, border_width=0)
        card.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 2))
        # 10 colonnes avec poids équilibrés
        for col in range(10):
            card.grid_columnconfigure(col, weight=1)

        lbl_kw = dict(font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY, anchor="w")
        entry_kw = dict(font=Fonts.input(12), fg_color=Colors.BG_INPUT,
                        border_color=Colors.BORDER, height=32, corner_radius=6)

        # Variante de entry_kw sans 'font' pour permettre une surcharge par widget
        entry_kw_no_font = {k: v for k, v in entry_kw.items() if k != 'font'}

        # — N° Facture — (police bold pour la référence)
        ctk.CTkLabel(card, text="N° Facture", **lbl_kw).grid(
            row=0, column=0, padx=(10, 2), pady=(8, 0), sticky="w")
        self.entry_ref_vente = ctk.CTkEntry(card, **entry_kw_no_font, width=155,
                                             font=Fonts.bold(12))
        self.entry_ref_vente.grid(row=1, column=0, padx=(10, 4), pady=(0, 8), sticky="ew")
        self.entry_ref_vente.configure(state="readonly")

        # — Date —
        ctk.CTkLabel(card, text="Date Sortie", **lbl_kw).grid(
            row=0, column=1, padx=4, pady=(8, 0), sticky="w")
        self.entry_date_vente = ctk.CTkEntry(card, **entry_kw, width=130)
        self.entry_date_vente.grid(row=1, column=1, padx=4, pady=(0, 8), sticky="ew")
        self.entry_date_vente.insert(0, datetime.now().strftime("%d/%m/%Y"))

        # — Magasin —
        ctk.CTkLabel(card, text="Magasin de", **lbl_kw).grid(
            row=0, column=2, padx=4, pady=(8, 0), sticky="w")
        self.combo_magasin = ctk.CTkComboBox(
            card, values=["Chargement…"], width=160, height=32,
            font=Fonts.input(12), fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER, button_color=Colors.PRIMARY,
            dropdown_fg_color=Colors.BG_CARD,
        )
        self.combo_magasin.grid(row=1, column=2, padx=4, pady=(0, 8), sticky="ew")

        # — Client (entry + loupe) —
        ctk.CTkLabel(card, text="Client", **lbl_kw).grid(
            row=0, column=3, padx=4, pady=(8, 0), sticky="w")

        client_frame = ctk.CTkFrame(card, fg_color="transparent")
        client_frame.grid(row=1, column=3, columnspan=2, padx=4, pady=(0, 8), sticky="ew")
        client_frame.grid_columnconfigure(0, weight=1)

        self.entry_client = ctk.CTkEntry(client_frame, **entry_kw,
                                          placeholder_text="Nom du client…")
        self.entry_client.grid(row=0, column=0, sticky="ew")

        self.btn_search_client = ctk.CTkButton(
            client_frame, text="🔎", width=36, height=32,
            font=Fonts.body(14),
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            corner_radius=6, command=self.open_recherche_client,
        )
        self.btn_search_client.grid(row=0, column=1, padx=(4, 0))

        # — Désignation (cachée par défaut, utilisée en mode modification) —
        self.lbl_designation = ctk.CTkLabel(card, text="Désignation", **lbl_kw)
        self.entry_designation = ctk.CTkEntry(card, **entry_kw)
        # Ces widgets sont masqués mais accessibles via .grid() en mode modif
        self.lbl_designation.grid_remove()
        self.entry_designation.grid_remove()

        # — Bouton Charger Proforma (masqué par défaut) —
        self.btn_charger_proforma = ctk.CTkButton(
            card, text="📜 Proforma",
            font=Fonts.button(11), height=32, corner_radius=6,
            fg_color=Colors.SUCCESS_DARK, hover_color=Colors.SUCCESS,
            command=self.open_recherche_proforma,
        )
        self.btn_charger_proforma.grid(row=1, column=6, padx=4, pady=(0, 8))
        self.btn_charger_proforma.grid_remove()

    # ── 4.1  Bandeau saisie article ────────────────────────────────────────────
    def _build_article_band(self):
        """
        Ligne 1 : Article (readonly) | Rechercher | Qté | Unité | Remise | Prix | Ajouter.
        """
        band = ctk.CTkFrame(self, fg_color=Colors.BG_CARD,
                            corner_radius=0, border_width=0)
        band.grid(row=1, column=0, sticky="ew", padx=0, pady=(0, 2))
        for col in range(8):
            band.grid_columnconfigure(col, weight=1 if col in (0, 6) else 0)

        lbl_kw   = dict(font=Fonts.label(10), text_color=Colors.TEXT_SECONDARY, anchor="w")
        entry_kw = dict(font=Fonts.input(12), fg_color=Colors.BG_INPUT,
                        border_color=Colors.BORDER, height=30, corner_radius=6)

        # — Article —
        ctk.CTkLabel(band, text="Article", **lbl_kw).grid(
            row=0, column=0, padx=(10, 2), pady=(6, 0), sticky="w")
        self.entry_article = ctk.CTkEntry(band, **entry_kw, width=280,
                                           state="readonly")
        self.entry_article.grid(row=1, column=0, padx=(10, 4), pady=(0, 6), sticky="ew")

        self.btn_recherche_article = ctk.CTkButton(
            band, text="🔎 Rechercher", height=30, width=130, font=Fonts.button(11),
            corner_radius=6, fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            command=self.open_recherche_article,
        )
        self.btn_recherche_article.grid(row=1, column=1, padx=4, pady=(0, 6))

        # — Quantité —
        ctk.CTkLabel(band, text="Quantité", **lbl_kw).grid(
            row=0, column=2, padx=4, pady=(6, 0), sticky="w")
        self.entry_qtvente = ctk.CTkEntry(band, **entry_kw, width=90)
        self.entry_qtvente.grid(row=1, column=2, padx=4, pady=(0, 6))
        # Raccourci : Entrée → valider_detail
        self.entry_qtvente.bind("<Return>", lambda _e: self.valider_detail())

        # — Unité —
        ctk.CTkLabel(band, text="Unité", **lbl_kw).grid(
            row=0, column=3, padx=4, pady=(6, 0), sticky="w")
        self.entry_unite = ctk.CTkEntry(band, **entry_kw, width=90, state="readonly")
        self.entry_unite.grid(row=1, column=3, padx=4, pady=(0, 6))

        # — Remise (Ar) — désactivée par défaut, activable via code autorisation
        ctk.CTkLabel(band, text="Remise (Ar)", **lbl_kw).grid(
            row=0, column=4, padx=4, pady=(6, 0), sticky="w")
        self.entry_remise = ctk.CTkEntry(band, **entry_kw, width=90, state="disabled")
        self.entry_remise.grid(row=1, column=4, padx=4, pady=(0, 6))
        self.entry_remise.insert(0, "0")
        # Clic sur la remise désactivée → demande code autorisation
        self.entry_remise.bind(
            "<Button-1>",
            lambda _e: self.verifier_droits_admin()
            if str(self.entry_remise.cget("state")) == "disabled" else None
        )

        # — Prix Unitaire —
        ctk.CTkLabel(band, text="Prix Unitaire", **lbl_kw).grid(
            row=0, column=5, padx=4, pady=(6, 0), sticky="w")
        self.entry_prixunit = ctk.CTkEntry(band, **entry_kw, width=110, state="readonly")
        self.entry_prixunit.grid(row=1, column=5, padx=4, pady=(0, 6))

        # — Bouton Ajouter —
        self.btn_ajouter = ctk.CTkButton(
            band, text="➕ Ajouter", height=30, width=130, font=Fonts.button(11),
            corner_radius=6, fg_color=Colors.SUCCESS_DARK, hover_color=Colors.SUCCESS,
            command=self.valider_detail,
        )
        self.btn_ajouter.grid(row=1, column=6, padx=(4, 8), pady=(0, 6))

        # — Bouton Annuler Modification (masqué par défaut) —
        self.btn_annuler_mod = ctk.CTkButton(
            band, text="✖ Annuler Modif.", height=30, width=140, font=Fonts.button(11),
            corner_radius=6, fg_color=Colors.DANGER, hover_color=Colors.DANGER_DARK,
            command=self.reset_detail_form, state="disabled",
        )
        self.btn_annuler_mod.grid(row=1, column=7, padx=(0, 8), pady=(0, 6))
        self.btn_annuler_mod.grid_remove()

        # — Bouton ajout en masse lignes proforma (masqué par défaut) —
        self.btn_ajouter_proforma_bulk = ctk.CTkButton(
            band, text="✅ Ajouter Lignes Proforma", height=30, font=Fonts.button(11),
            corner_radius=6, fg_color=Colors.INFO_DARK, hover_color=Colors.INFO,
            command=self.ajouter_details_proforma_en_masse,
        )
        # Sera affiché via afficher_bouton_ajouter_proforma()

    # ── 4.2  Tableau de détails ────────────────────────────────────────────────
    def _build_detail_table(self):
        """
        Zone expansible (weight=1) contenant le TTK Treeview des lignes de vente.
        Style zébré, scrollbar verticale et horizontale.
        """
        tf = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        tf.grid(row=2, column=0, sticky="nsew", padx=0, pady=(0, 2))
        tf.grid_columnconfigure(0, weight=1)
        tf.grid_rowconfigure(0, weight=1)

        # utilitaires pour colonnes dynamiques
        def _hide_remise():
            try:
                self.tree_details.column("Remise (Ar)", width=0, anchor="e", minwidth=0, stretch=False)
            except Exception:
                pass
        def _show_remise():
            try:
                self.tree_details.column("Remise (Ar)", width=110, anchor="e", minwidth=80, stretch=True)
            except Exception:
                pass
        # intégration sur self pour usage ultérieur
        self._hide_remise_column = _hide_remise
        self._show_remise_column = _show_remise

        # ── Style TTK ─────────────────────────────────────────────────────────
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("Vente.Treeview",
                    rowheight=24,
                    font=("Roboto", 10),
                    background=Colors.BG_CARD,
                    foreground=Colors.TEXT_PRIMARY,
                    fieldbackground=Colors.BG_CARD,
                    borderwidth=0,
                    relief="flat")
        s.configure("Vente.Treeview.Heading",
                    background=Colors.BG_HEADER,
                    foreground=Colors.TEXT_ON_DARK,
                    font=("Roboto", 10, "bold"),
                    relief="flat", padding=4)
        s.map("Vente.Treeview",
              background=[("selected", Colors.PRIMARY_LIGHT)],
              foreground=[("selected", Colors.TEXT_PRIMARY)])

        # ── Colonnes ─────────────────────────────────────────────────────────
        cols = ("ID_Article", "ID_Unite", "ID_Magasin",
                "Code Article", "Désignation", "Magasin",
                "Unité", "Remise (Ar)", "Prix Unitaire",
                "Quantité Vente", "Montant")

        self.tree_details = ttk.Treeview(
            tf, columns=cols, show="headings", style="Vente.Treeview"
        )
        # Tags de couleur lignes
        self.tree_details.tag_configure("even", background=Colors.BG_CARD)
        self.tree_details.tag_configure("odd",  background=Colors.BG_ROW_ALT)

        for col in cols:
            self.tree_details.heading(col, text=col.replace("_", " ").title())
            # cacher certaines colonnes par défaut
            if "ID" in col or col in ("Code Article",):
                # colonnes techniques ou peu utiles en mode normal
                self.tree_details.column(col, width=0, stretch=False)
            elif col == "Remise (Ar)":
                # remise masquée par défaut et dévoilée dynamiquement
                self.tree_details.column(col, width=0, anchor="e", minwidth=0, stretch=False)
            elif col in ("Quantité Vente", "Prix Unitaire", "Montant"):
                self.tree_details.column(col, width=110, anchor="e", minwidth=80)
            elif col == "Désignation":
                self.tree_details.column(col, width=200, anchor="w", minwidth=120)
            else:
                self.tree_details.column(col, width=110, anchor="w", minwidth=80)

        # ── Scrollbars ────────────────────────────────────────────────────────
        sb_v = ctk.CTkScrollbar(tf, command=self.tree_details.yview)
        sb_h = ctk.CTkScrollbar(tf, orientation="horizontal",
                                  command=self.tree_details.xview)
        self.tree_details.configure(yscrollcommand=sb_v.set,
                                     xscrollcommand=sb_h.set)

        self.tree_details.grid(row=0, column=0, sticky="nsew", padx=(2, 0), pady=2)
        sb_v.grid(row=0, column=1, sticky="ns", pady=2)
        sb_h.grid(row=1, column=0, sticky="ew", padx=(2, 0))

        # Double-clic → charger la ligne en mode modification
        self.tree_details.bind("<Double-1>", self.modifier_detail)

    # ── 4.3  Zone Totaux ──────────────────────────────────────────────────────
    def _build_totals_band(self):
        """
        Ligne 3 : Total en Lettres (gauche) | Total Général + FMG (droite).
        """
        tband = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        tband.grid(row=3, column=0, sticky="ew", padx=0, pady=(0, 2))
        tband.grid_columnconfigure(0, weight=1)
        tband.grid_columnconfigure(1, weight=0)

        # — Côté gauche : total en lettres —
        ctk.CTkLabel(tband, text="Total en Lettres",
                     font=Fonts.bold(11), text_color=Colors.TEXT_SECONDARY,
                     anchor="w").grid(row=0, column=0, padx=(12, 4), pady=(6, 0), sticky="w")
        self.label_total_lettres = ctk.CTkLabel(
            tband, text="Zéro Ariary", wraplength=700, justify="left",
            font=Fonts.body(11), text_color=Colors.TEXT_MUTED,
        )
        self.label_total_lettres.grid(row=1, column=0, padx=(12, 4), pady=(0, 8), sticky="ew")

        # — Côté droit : montants —
        right = ctk.CTkFrame(tband, fg_color="transparent")
        right.grid(row=0, column=1, rowspan=2, padx=(4, 12), pady=6, sticky="ne")

        ctk.CTkLabel(right, text="TOTAL GÉNÉRAL (Ar) :",
                     font=Fonts.bold(13), text_color=Colors.TEXT_PRIMARY).pack(side="left", padx=4)
        self.label_total_general = ctk.CTkLabel(
            right, text="0,00",
            font=Fonts.bold(15), text_color=Colors.DANGER,
        )
        self.label_total_general.pack(side="left", padx=(0, 16))

        # Montant FMG (× 5)
        fmg_frame = ctk.CTkFrame(tband, fg_color="transparent")
        fmg_frame.grid(row=1, column=1, padx=(4, 12), pady=(0, 8), sticky="ne")
        ctk.CTkLabel(fmg_frame, text="En FMG :",
                     font=Fonts.body(11), text_color=Colors.TEXT_SECONDARY).pack(side="left", padx=4)
        self.label_montant_fmg = ctk.CTkLabel(
            fmg_frame, text="0,00",
            font=Fonts.bold(12), text_color=Colors.PRIMARY,
        )
        self.label_montant_fmg.pack(side="left")

    # ── 4.4  Barre d'actions (boutons bas) ────────────────────────────────────
    def _build_action_bar(self):
        """
        Ligne 4 : Nouvelle Facture | Créer Avoir | Supprimer Ligne | … | 💾 Enregistrer.
        """
        bar = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        bar.grid(row=4, column=0, sticky="ew", padx=0, pady=0)
        bar.grid_columnconfigure(99, weight=1)  # espace entre gauche et droite

        btn_kw = dict(height=36, corner_radius=6, font=Fonts.button(11))

        # — Nouvelle Facture —
        self.btn_nouveau_bs = ctk.CTkButton(
            bar, text="📄 Nouvelle Facture",
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            command=self.nouveau_facture, **btn_kw,
        )
        self.btn_nouveau_bs.grid(row=0, column=0, padx=(10, 4), pady=8)

        # — Créer Avoir (accès protégé par code) —
        self.btn_creer_avoir = ctk.CTkButton(
            bar, text="🧾 Créer Avoir",
            fg_color="#e11d48", hover_color="#be123c",
            command=self.tentative_ouverture_avoir, **btn_kw,
        )
        self.btn_creer_avoir.grid(row=0, column=1, padx=4, pady=8)

        # — Supprimer Ligne —
        self.btn_supprimer_ligne = ctk.CTkButton(
            bar, text="🗑 Supprimer Ligne",
            fg_color=Colors.DANGER, hover_color=Colors.DANGER_DARK,
            command=self.supprimer_detail, **btn_kw,
        )
        self.btn_supprimer_ligne.grid(row=0, column=2, padx=4, pady=8)

        # — Créer Proforma (masqué par défaut) —
        self.btn_creer_proforma = ctk.CTkButton(
            bar, text="📄 Créer Proforma",
            fg_color=Colors.SUCCESS, hover_color=Colors.SUCCESS_DARK,
            command=self._ouvrir_page_proforma, **btn_kw,
        )
        self.btn_creer_proforma.grid(row=0, column=3, padx=4, pady=8)
        self.btn_creer_proforma.grid_remove()

        # — Enregistrer (bouton principal, à droite) —
        self.btn_enregistrer = ctk.CTkButton(
            bar, text="💾 Enregistrer la Facture",
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            font=Fonts.bold(13), height=40, corner_radius=8,
            command=self._on_enregistrer_click,
        )
        self.btn_enregistrer.grid(row=0, column=99, padx=(4, 10), pady=6, sticky="e")

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 5 — RESPONSIVITÉ
    # ──────────────────────────────────────────────────────────────────────────

    def _on_resize(self, event=None):
        """
        Ajuste la wraplength du total en lettres et la hauteur visible
        du tableau en fonction de la taille actuelle du frame.
        """
        try:
            w = self.winfo_width()
            h = self.winfo_height()

            if hasattr(self, "label_total_lettres"):
                self.label_total_lettres.configure(wraplength=max(300, w - 450))

            if hasattr(self, "tree_details") and self.tree_details.winfo_exists():
                available_h = max(180, h - 360)
                rows = max(6, min(25, int(available_h / 25)))
                self.tree_details.configure(height=rows)

                if w > 700:
                    self.tree_details.column("Désignation",     width=max(180, int(w * 0.22)))
                    self.tree_details.column("Magasin",         width=max(110, int(w * 0.13)))
                    self.tree_details.column("Unité",           width=max(80,  int(w * 0.08)))
                    self.tree_details.column("Prix Unitaire",   width=max(100, int(w * 0.10)))
                    self.tree_details.column("Quantité Vente",  width=max(100, int(w * 0.10)))
                    self.tree_details.column("Montant",         width=max(110, int(w * 0.11)))
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 6 — LOGIQUE MÉTIER : ARTICLES & STOCK
    # (inchangée par rapport à la version d'origine)
    # ──────────────────────────────────────────────────────────────────────────

    def get_article_price(self, idarticle: int, idunite: int) -> float:
        """Récupère le dernier prix de vente pour (idarticle, idunite) depuis tb_prix."""
        if not self.conn:
            return 0.0
        try:
            cur = self.conn.cursor()
            cur.execute("""
                SELECT COALESCE(prix) FROM tb_prix
                WHERE idarticle=%s AND idunite=%s ORDER BY id DESC LIMIT 1
            """, (idarticle, idunite))
            r = cur.fetchone()
            if r and r[0] and r[0] > 0:
                return float(r[0])
            return 0.0
        except Exception as e:
            print("Erreur get_article_price:", e)
            return 0.0
        finally:
            if 'cur' in locals(): cur.close()

    def get_unite_niveau_max(self, idarticle: int):
        """Retourne (idunite, niveau, designationunite) de niveau max pour l'article."""
        conn = self._connect_db()
        if not conn: return None
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT idunite, niveau, designationunite
                FROM tb_unite WHERE idarticle=%s ORDER BY niveau DESC LIMIT 1
            """, (idarticle,))
            return cur.fetchone()
        except Exception as e:
            print(f"Erreur get_unite_niveau_max: {e}")
        finally:
            cur.close(); conn.close()

    def verifier_unite_depot_b(self, idarticle: int, idunite: int):
        """
        Pour le dépôt B : seule l'unité de niveau MAX est autorisée.
        Retourne (autorise: bool, message: str).
        """
        mag_nom = self.combo_magasin.get()
        if "B" not in mag_nom.upper():
            return (True, "")
        conn = self._connect_db()
        if not conn: return (False, "Erreur de connexion")
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT niveau, designationunite FROM tb_unite
                WHERE idarticle=%s AND idunite=%s
            """, (idarticle, idunite))
            row = cur.fetchone()
            if not row: return (False, "Unité introuvable")
            niv_sel, des_sel = row
            cur.execute("""
                SELECT MAX(niveau), designationunite FROM tb_unite
                WHERE idarticle=%s GROUP BY designationunite
                ORDER BY MAX(niveau) DESC LIMIT 1
            """, (idarticle,))
            row2 = cur.fetchone()
            if not row2: return (False, "Impossible de déterminer le niveau max")
            niv_max, des_max = row2
            if niv_sel < niv_max:
                return (False,
                    f"⚠ DÉPÔT B : Seule l'unité de niveau {niv_max} ({des_max}) est autorisée.\n"
                    f"Vous avez sélectionné : {des_sel} (niveau {niv_sel}).\n\n"
                    f"Veuillez choisir {des_max}.")
            return (True, "")
        except Exception as e:
            return (False, str(e))
        finally:
            cur.close(); conn.close()

    def calculer_stock_article(self, idarticle: int, idunite_cible: int,
                                idmag: Optional[int] = None) -> float:
        """
        Calcul consolidé du stock (identique à page_stock.py).
        Réservoir commun converti via qtunite, filtrable par magasin.
        """
        conn = self._connect_db()
        if not conn: return 0
        try:
            cur = conn.cursor()
            # Récupération de toutes les unités liées
            cur.execute("""
                SELECT idunite, codearticle, COALESCE(qtunite,1)
                FROM tb_unite WHERE idarticle=%s
            """, (idarticle,))
            unites = cur.fetchall()
            qt_affichage = next((qt for uid, _, qt in unites
                                  if uid == idunite_cible and qt > 0), 1)
            reservoir = 0
            for uid, code, qt_u in unites:
                def _sum(sql, params):
                    cur.execute(sql, params)
                    return cur.fetchone()[0] or 0

                p = [idarticle, uid]
                pm = p + ([idmag] if idmag else [])
                mag_clause = " AND idmag=%s" if idmag else ""

                rec  = _sum(f"SELECT COALESCE(SUM(qtlivrefrs),0) FROM tb_livraisonfrs WHERE idarticle=%s AND idunite=%s AND deleted=0{mag_clause}", pm)
                ven  = _sum(f"SELECT COALESCE(SUM(qtvente),0) FROM tb_ventedetail vd INNER JOIN tb_vente v ON vd.idvente=v.id WHERE vd.idarticle=%s AND vd.idunite=%s AND v.deleted=0 AND v.statut='VALIDEE'{' AND v.idmag=%s' if idmag else ''}", pm)
                tin  = _sum(f"SELECT COALESCE(SUM(qttransfert),0) FROM tb_transfertdetail WHERE idarticle=%s AND idunite=%s AND deleted=0{' AND idmagentree=%s' if idmag else ''}", pm)
                tout = _sum(f"SELECT COALESCE(SUM(qttransfert),0) FROM tb_transfertdetail WHERE idarticle=%s AND idunite=%s AND deleted=0{' AND idmagsortie=%s' if idmag else ''}", pm)

                # Inventaire (via codearticle)
                pi = [code] + ([idmag] if idmag else [])
                inv = _sum(f"SELECT COALESCE(SUM(qtinventaire),0) FROM tb_inventaire WHERE codearticle=%s{' AND idmag=%s' if idmag else ''}", pi)

                reservoir += (rec + tin + inv - ven - tout) * qt_u

            return max(0, reservoir / qt_affichage)
        except Exception as e:
            print(f"Erreur calcul stock: {e}")
            return 0
        finally:
            cur.close(); conn.close()

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 7 — LOGIQUE MÉTIER : CHARGEMENTS INITIAUX
    # ──────────────────────────────────────────────────────────────────────────

    def generer_reference(self):
        """Génère et affiche une nouvelle référence FA-AAAA-NNNNN."""
        if self.mode_modification and self.idvente_charge:
            return  # Ne pas écraser la référence existante en mode modif
        conn = self._connect_db()
        if not conn: return
        try:
            cur = conn.cursor()
            annee = datetime.now().year
            cur.execute("""
                SELECT refvente FROM tb_vente
                WHERE refvente ILIKE %s ORDER BY id DESC LIMIT 1
            """, (f"%{annee}-FA-%",))
            row = cur.fetchone()
            num = 1
            if row:
                parts = row[0].split('-')
                if len(parts) == 3 and parts[1] == 'FA':
                    try: num = int(parts[-1]) + 1
                    except ValueError: pass
            ref = f"{annee}-FA-{num:05d}"
            self.entry_ref_vente.configure(state="normal")
            self.entry_ref_vente.delete(0, "end")
            self.entry_ref_vente.insert(0, ref)
            self.entry_ref_vente.configure(state="readonly")
        except Exception as e:
            messagebox.showerror("Erreur", f"Génération référence : {e}")
        finally:
            cur.close(); conn.close()

    def charger_magasins(self):
        """Charge les magasins dans combo_magasin et sélectionne celui de l'utilisateur."""
        conn = self._connect_db()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("SELECT idmag, designationmag FROM tb_magasin WHERE deleted=0 ORDER BY designationmag")
            mags = cur.fetchall()
            self.magasin_map = {nom: id_ for id_, nom in mags}
            self.magasin_ids = [id_ for id_, _ in mags]
            noms = list(self.magasin_map.keys())
            self.combo_magasin.configure(values=noms)

            if not noms:
                self.combo_magasin.set("Aucun magasin")
                return

            # Sélection du magasin par défaut de l'utilisateur connecté
            idmag_user = None
            if self.id_user_connecte:
                cur.execute("SELECT idmag FROM tb_users WHERE iduser=%s AND deleted=0",
                            (self.id_user_connecte,))
                row = cur.fetchone()
                if row: idmag_user = row[0]

            defaut = next((n for n, i in self.magasin_map.items() if i == idmag_user), noms[0])
            self.combo_magasin.set(defaut)
        except Exception as e:
            messagebox.showerror("Erreur", f"Chargement magasins : {e}")
        finally:
            cur.close(); conn.close()

    def charger_client(self):
        """Pré-charge la map {nomcli: idclient} pour la validation rapide."""
        conn = self._connect_db()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("SELECT idclient, nomcli FROM tb_client WHERE deleted=0 ORDER BY nomcli")
            clients = cur.fetchall()
            self.client_map = {nom: id_ for id_, nom in clients}
            self.client_ids = [id_ for id_, _ in clients]
        except Exception as e:
            messagebox.showerror("Erreur", f"Chargement clients : {e}")
        finally:
            cur.close(); conn.close()

    def charger_infos_societe(self):
        """Charge les informations de la société depuis tb_infosociete (pour les PDF)."""
        _defaults = {
            'nomsociete': 'NOM SOCIÉTÉ', 'adressesociete': 'N/A',
            'villesociete': 'N/A', 'contactsociete': 'N/A',
            'nifsociete': 'N/A', 'statsociete': 'N/A',
            'cifsociete': 'N/A', 'ambleme': '', 'autre': '',
        }
        conn = self._connect_db()
        if not conn:
            self.infos_societe = _defaults
            return
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT nomsociete, adressesociete, villesociete, contactsociete,
                       nifsociete, statsociete, cifsociete, ambleme, autre
                FROM tb_infosociete LIMIT 1
            """)
            row = cur.fetchone()
            if row:
                keys = ['nomsociete','adressesociete','villesociete','contactsociete',
                        'nifsociete','statsociete','cifsociete','ambleme','autre']
                self.infos_societe = dict(zip(keys, row))
            else:
                self.infos_societe = _defaults
        except Exception as e:
            messagebox.showwarning("Avertissement", f"Infos société : {e}")
            self.infos_societe = _defaults
        finally:
            cur.close(); conn.close()

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 8 — LOGIQUE MÉTIER : GESTION DU DÉTAIL DE VENTE
    # ──────────────────────────────────────────────────────────────────────────

    def format_detail_for_treeview(self, detail: Dict) -> tuple:
        """Convertit un dict de détail en tuple pour l'affichage dans le Treeview."""
        remise   = float(detail.get('remise', 0))
        qtvente  = float(detail.get('qtvente', detail.get('qte', 0)))
        prixunit = float(detail.get('prixunit', 0))
        montant_net = max(0, qtvente * prixunit - remise * qtvente)
        return (
            detail.get('idarticle', ''),
            detail.get('idunite', ''),
            detail.get('idmag', ''),
            detail.get('code_article', 'N/A'),
            detail.get('nom_article', ''),
            detail.get('designationmag', ''),
            detail.get('nom_unite', ''),
            self.formater_nombre(remise),
            self.formater_nombre(prixunit),
            self.formater_nombre(qtvente),
            self.formater_nombre(montant_net),
        )

    def charger_details_treeview(self):
        """Efface et recharge toutes les lignes de self.detail_vente dans le Treeview."""
        for item in self.tree_details.get_children():
            self.tree_details.delete(item)
        for idx, detail in enumerate(self.detail_vente):
            tag = "even" if idx % 2 == 0 else "odd"
            self.tree_details.insert('', 'end',
                                      values=self.format_detail_for_treeview(detail),
                                      tags=(tag,))
        self.calculer_totaux()
        # masquer la colonne remise si aucun détail n'en a
        if not any(float(d.get('remise', 0)) > 0 for d in self.detail_vente):
            self._hide_remise_column()

    def calculer_totaux(self):
        """Recalcule et affiche le total général, FMG (×5) et le total en lettres."""
        total = sum(float(d.get('montant_ttc', d.get('montant', 0)))
                    for d in self.detail_vente)
        self.label_total_general.configure(text=self.formater_nombre(total))
        self.label_montant_fmg.configure(text=self.formater_nombre(total * 5))
        self.label_total_lettres.configure(text=nombre_en_lettres_fr(total))

    def valider_detail(self):
        """
        Valide la saisie de l'article en cours et l'ajoute (ou met à jour) dans
        self.detail_vente, avec contrôle de stock et de remise.
        """
        if not self.article_selectionne:
            messagebox.showwarning("Attention", "Veuillez d'abord sélectionner un article.")
            return

        mag_nom = self.combo_magasin.get()
        idmag   = self.magasin_map.get(mag_nom)
        if not idmag:
            messagebox.showerror("Erreur", "Veuillez sélectionner un magasin valide.")
            return

        # Vérification unité Dépôt B
        ok, msg = self.verifier_unite_depot_b(
            self.article_selectionne['idarticle'],
            self.article_selectionne['idunite']
        )
        if not ok:
            messagebox.showerror("Unité Non Autorisée — Dépôt B", msg)
            return

        try:
            qtvente  = self.parser_nombre(self.entry_qtvente.get())
            prixunit = self.parser_nombre(self.entry_prixunit.get())
            remise   = self.parser_nombre(self.entry_remise.get() or "0")
        except ValueError:
            messagebox.showerror("Erreur", "Quantité, prix ou remise invalide.")
            return

        if qtvente <= 0:
            messagebox.showwarning("Avertissement", "La quantité doit être > 0.")
            return
        if prixunit <= 0:
            messagebox.showwarning("Attention", "Le prix unitaire doit être positif.")
            return
        if remise < 0:
            messagebox.showwarning("Attention", "La remise ne peut pas être négative.")
            return

        # Contrôle stock (uniquement pour un nouvel ajout, pas en modification)
        if self.index_ligne_selectionnee is None and self.stock_temporaire_selection is not None:
            if qtvente > self.stock_temporaire_selection:
                messagebox.showwarning(
                    "Stock Insuffisant",
                    f"Quantité saisie ({self.formater_nombre(qtvente)}) dépasse "
                    f"le stock ({self.formater_nombre(self.stock_temporaire_selection)}).",
                )
                return

        # Construction du dict de la ligne de détail
        nouveau = {
            'idarticle':      self.article_selectionne['idarticle'],
            'nom_article':    self.article_selectionne['nom_article'],
            'idunite':        self.article_selectionne['idunite'],
            'nom_unite':      self.article_selectionne['nom_unite'],
            'code_article':   self.article_selectionne['code_article'],
            'qtvente':        qtvente,
            'prixunit':       prixunit,
            'remise':         remise,
            'designationmag': mag_nom,
            'idmag':          idmag,
        }
        # Calcul des montants
        ht      = qtvente * prixunit
        remise_t = remise * qtvente
        ttc     = max(0, ht - remise_t)
        nouveau.update({'montant_ht': ht, 'montant_remise': remise_t, 'montant_ttc': ttc})

        if self.index_ligne_selectionnee is not None:
            self.detail_vente[self.index_ligne_selectionnee] = nouveau
            self.index_ligne_selectionnee = None
        else:
            self.detail_vente.append(nouveau)

        # afficher colonne remise si la ligne possède une remise
        if remise and remise != 0:
            self._show_remise_column()

        self.reset_detail_form()
        self.charger_details_treeview()

    def modifier_detail(self, event):
        """Double-clic : charge la ligne sélectionnée dans les champs de saisie."""
        item = self.tree_details.focus()
        if not item: return
        try:
            self.index_ligne_selectionnee = self.tree_details.index(item)
            detail = self.detail_vente[self.index_ligne_selectionnee]
        except IndexError:
            messagebox.showerror("Erreur", "Erreur de récupération de la ligne.")
            self.reset_detail_form()
            return

        self.article_selectionne = {
            'idarticle':   detail['idarticle'],
            'nom_article': detail['nom_article'],
            'idunite':     detail['idunite'],
            'nom_unite':   detail['nom_unite'],
            'code_article': detail.get('code_article', 'N/A'),
        }
        self.entry_article.configure(state="normal")
        self.entry_article.delete(0, "end")
        self.entry_article.insert(0, f"[{detail.get('code_article','N/A')}] {detail['nom_article']}")
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

        self.combo_magasin.set(detail['designationmag'])

        # Basculer les boutons en mode "modification de ligne"
        self.btn_ajouter.configure(text="✔ Valider Modif.",
                                    fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER)
        self.btn_annuler_mod.configure(state="normal")
        self.btn_annuler_mod.grid()
        self.btn_recherche_article.configure(state="disabled")

    def reset_detail_form(self):
        """Réinitialise tous les champs de saisie article et restaure les boutons."""
        self.article_selectionne      = None
        self.stock_temporaire_selection = None
        self.index_ligne_selectionnee = None

        # Remise
        self.entry_remise.delete(0, "end")
        self.entry_remise.insert(0, "0")

        # Article
        self.entry_article.configure(state="normal")
        self.entry_article.delete(0, "end")
        self.entry_article.configure(state="readonly")

        # Quantité
        self.entry_qtvente.delete(0, "end")

        # Prix
        self.entry_prixunit.configure(state="normal")
        self.entry_prixunit.delete(0, "end")
        self.entry_prixunit.configure(state="readonly")

        # Unité
        self.entry_unite.configure(state="normal")
        self.entry_unite.delete(0, "end")
        self.entry_unite.configure(state="readonly")

        # Restaurer le bouton Ajouter
        self.btn_ajouter.configure(
            text="➕ Ajouter",
            fg_color=Colors.SUCCESS_DARK, hover_color=Colors.SUCCESS,
        )
        self.btn_annuler_mod.configure(state="disabled")
        self.btn_annuler_mod.grid_remove()
        self.btn_recherche_article.configure(state="normal")

        # Réactiver l'entrée manuelle si aucun proforma n'est en attente
        if not self.details_proforma_a_ajouter:
            self.activer_entree_manuelle()

    def supprimer_detail(self):
        """Supprime la ligne sélectionnée dans le Treeview (avec confirmation)."""
        item = self.tree_details.focus()
        if not item:
            messagebox.showwarning("Attention", "Veuillez sélectionner une ligne.")
            return
        if messagebox.askyesno("Confirmation", "Supprimer cette ligne de détail ?"):
            idx = self.tree_details.index(item)
            try:
                self.detail_vente.pop(idx)
                self.reset_detail_form()
                self.charger_details_treeview()
            except IndexError:
                messagebox.showerror("Erreur", "Erreur lors de la suppression.")

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 9 — LOGIQUE MÉTIER : FENÊTRES DE RECHERCHE
    # ──────────────────────────────────────────────────────────────────────────

    def open_recherche_client(self):
        """Ouvre une fenêtre modale de sélection de client avec filtre et type."""
        fen = ctk.CTkToplevel(self)
        fen.title("Rechercher un client")
        fen.geometry("550*550")
        fen.configure(fg_color=Colors.BG_PAGE)
        fen.grab_set()
        fen.lift()
        fen.focus_force()
        fen.attributes('-topmost', True)

        frame = ctk.CTkFrame(fen, fg_color=Colors.BG_CARD, corner_radius=12)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(frame, text="🔍 Sélectionner un client",
                     font=Fonts.heading(14), text_color=Colors.TEXT_PRIMARY).pack(pady=(12, 8))

        # Zone filtre
        tf = ctk.CTkFrame(frame, fg_color="transparent")
        tf.pack(fill="x", padx=12, pady=(0, 8))
        tf.grid_columnconfigure(0, weight=1)

        entry_search = ctk.CTkEntry(tf, placeholder_text="Nom client…",
                                     font=Fonts.input(12), fg_color=Colors.BG_INPUT,
                                     border_color=Colors.BORDER, height=32)
        entry_search.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        type_filter = ctk.CTkComboBox(tf, values=["Client à crédit", "Client au comptant", "Tous"],
                                       width=170, height=32, state="readonly",
                                       font=Fonts.input(11), fg_color=Colors.BG_INPUT,
                                       border_color=Colors.BORDER)
        type_filter.set("Client à crédit")
        type_filter.grid(row=0, column=1)

        # Treeview clients
        cols = ("ID", "Nom Client", "Contact", "Adresse")
        tree = ttk.Treeview(frame, columns=cols, show="headings",
                             height=14, style="Vente.Treeview")
        tree.tag_configure("even", background=Colors.BG_CARD)
        tree.tag_configure("odd",  background=Colors.BG_ROW_ALT)
        tree.heading("ID", text="ID")
        tree.heading("Nom Client", text="Nom Client")
        tree.heading("Contact", text="Contact")
        tree.heading("Adresse", text="Adresse")
        tree.column("ID", width=0, stretch=False)
        tree.column("Nom Client", width=210, anchor="w")
        tree.column("Contact", width=140, anchor="w")
        tree.column("Adresse", width=260, anchor="w")
        tree.pack(fill="both", expand=True, padx=12, pady=8)

        def charger(_e=None):
            filtre = entry_search.get().strip()
            for i in tree.get_children(): tree.delete(i)
            conn = self._connect_db()
            if not conn: return
            try:
                cur = conn.cursor()
                tp  = type_filter.get()
                tc  = (" AND COALESCE(idtypeclient,1)=2" if tp == "Client à crédit"
                       else " AND COALESCE(idtypeclient,1)=1" if tp == "Client au comptant"
                       else "")
                cur.execute(f"""
                    SELECT idclient, nomcli,
                           COALESCE(NULLIF(TRIM(contactcli),''),'Aucun contact') AS ct,
                           COALESCE(NULLIF(TRIM(adressecli),''),'Aucune adresse') AS adr
                    FROM tb_client WHERE deleted=0 AND nomcli ILIKE %s {tc}
                    ORDER BY nomcli
                """, (f"%{filtre}%",))
                for idx, row in enumerate(cur.fetchall()):
                    tree.insert("", "end", values=row,
                                tags=("even" if idx % 2 == 0 else "odd",))
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
            finally:
                cur.close(); conn.close()

        entry_search.bind("<KeyRelease>", charger)
        type_filter.configure(command=lambda _: charger())

        def valider():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Attention", "Sélectionnez un client.")
                return
            vals = tree.item(sel[0])['values']
            self.entry_client.delete(0, "end")
            self.entry_client.insert(0, vals[1])
            self.client_map[vals[1]] = vals[0]
            fen.destroy()

        tree.bind("<Double-Button-1>", lambda _e: valider())

        bf = ctk.CTkFrame(frame, fg_color="transparent")
        bf.pack(fill="x", padx=12, pady=(0, 12))
        styled.button_danger(bf, text="❌ Annuler", command=fen.destroy, width=120).pack(side="left")
        styled.button_success(bf, text="✅ Valider", command=valider, width=120).pack(side="right")

        charger()

    def open_recherche_article(self):
        """
        Ouvre la fenêtre de recherche d'article avec stock en temps réel
        pour le magasin sélectionné. Bloque si stock ≤ 0.
        """
        if self.index_ligne_selectionnee is not None:
            messagebox.showwarning("Attention",
                                   "Validez ou annulez la modification en cours.")
            return

        fen = ctk.CTkToplevel(self)
        fen.title("Rechercher un article")
        fen.geometry("1020x620")
        fen.configure(fg_color=Colors.BG_PAGE)
        fen.grab_set()
        fen.lift()
        fen.focus_force()
        fen.attributes('-topmost', True)

        mf = ctk.CTkFrame(fen, fg_color=Colors.BG_CARD, corner_radius=12)
        mf.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(mf, text="📦 Sélectionner un article",
                     font=Fonts.heading(14), text_color=Colors.TEXT_PRIMARY).pack(pady=(12, 8))

        sf = ctk.CTkFrame(mf, fg_color="transparent")
        sf.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkLabel(sf, text="🔍", font=Fonts.body(14),
                     text_color=Colors.TEXT_MUTED).pack(side="left", padx=(0, 6))
        entry_search = ctk.CTkEntry(sf, placeholder_text="Code ou désignation…",
                                     font=Fonts.input(12), fg_color=Colors.BG_INPUT,
                                     border_color=Colors.BORDER, height=32)
        entry_search.pack(side="left", fill="x", expand=True)
        fen.after(100, entry_search.focus_set)

        tf = ctk.CTkFrame(mf, fg_color="transparent")
        tf.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        cols = ("ID_Article", "ID_Unite", "Code", "Désignation", "Unité", "Prix Unitaire", "Stock")
        tree = ttk.Treeview(tf, columns=cols, show="headings",
                             height=18, style="Vente.Treeview")
        tree.tag_configure("even",      background=Colors.BG_CARD)
        tree.tag_configure("odd",       background=Colors.BG_ROW_ALT)
        tree.tag_configure("stock_nul", foreground=Colors.DANGER)

        tree.heading("ID_Article", text="ID")
        tree.heading("ID_Unite",   text="IDU")
        tree.heading("Code",       text="Code")
        tree.heading("Désignation",text="Désignation")
        tree.heading("Unité",      text="Unité")
        tree.heading("Prix Unitaire", text="Prix Unitaire")
        tree.heading("Stock",      text="Stock Magasin")

        tree.column("ID_Article", width=0, stretch=False)
        tree.column("ID_Unite",   width=0, stretch=False)
        tree.column("Code",       width=150, anchor="w")
        tree.column("Désignation",width=350, anchor="w")
        tree.column("Unité",      width=100, anchor="w")
        tree.column("Prix Unitaire", width=110, anchor="e")
        tree.column("Stock",      width=130, anchor="e")

        sb = ctk.CTkScrollbar(tf, command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        def charger(filtre=""):
            for i in tree.get_children(): tree.delete(i)
            mag_nom = self.combo_magasin.get()
            idmag   = self.magasin_map.get(mag_nom)
            tree.heading("Stock", text=f"Stock '{mag_nom}'" if mag_nom else "Stock Magasin")
            if not idmag: return
            conn = self._connect_db()
            if not conn: return
            try:
                cur = conn.cursor()
                # Requête consolidée avec coefficient hiérarchique
                cur.execute("""
                WITH uc AS (
                    SELECT idarticle, idunite, niveau, designationunite,
                           exp(sum(ln(NULLIF(CASE WHEN qtunite>0 THEN qtunite ELSE 1 END,0)))
                               OVER (PARTITION BY idarticle ORDER BY niveau
                                     ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                           ) AS coeff
                    FROM (SELECT idarticle, idunite,
                                 COALESCE(qtunite,1) AS qtunite,
                                 niveau,
                                 designationunite
                          FROM tb_unite WHERE deleted=0) u_
                ),
                bu AS (
                    SELECT DISTINCT ON (idarticle) idarticle, idunite
                    FROM tb_unite WHERE deleted=0
                    ORDER BY idarticle, qtunite ASC, idunite ASC
                ),
                solde AS (
                    SELECT ma.idarticle,
                        SUM(CASE ma.tm
                            WHEN 'rec'  THEN  ma.q * COALESCE(uc.coeff,1)
                            WHEN 'tin'  THEN  ma.q * COALESCE(uc.coeff,1)
                            WHEN 'inv'  THEN  ma.q * COALESCE(uc.coeff,1)
                            WHEN 'avo'  THEN  ma.q * COALESCE(uc.coeff,1)
                            WHEN 'ein'  THEN  ma.q * COALESCE(uc.coeff,1)
                            ELSE              -ma.q * COALESCE(uc.coeff,1)
                        END) AS solde_base
                    FROM (
                        SELECT idarticle,idunite,%s AS idmag,SUM(qtlivrefrs)  AS q,'rec' AS tm FROM tb_livraisonfrs WHERE deleted=0 AND idmag=%s GROUP BY idarticle,idunite
                        UNION ALL
                        SELECT vd.idarticle,vd.idunite,%s,SUM(vd.qtvente),'ven' FROM tb_ventedetail vd JOIN tb_vente v ON vd.idvente=v.id AND v.deleted=0 AND v.statut='VALIDEE' AND v.idmag=%s WHERE vd.deleted=0 GROUP BY vd.idarticle,vd.idunite
                        UNION ALL
                        SELECT idarticle,idunite,%s,SUM(qttransfert),'tin' FROM tb_transfertdetail WHERE deleted=0 AND idmagentree=%s GROUP BY idarticle,idunite
                        UNION ALL
                        SELECT idarticle,idunite,%s,SUM(qttransfert),'tout' FROM tb_transfertdetail WHERE deleted=0 AND idmagsortie=%s GROUP BY idarticle,idunite
                        UNION ALL
                        SELECT bu.idarticle,bu.idunite,%s,SUM(i.qtinventaire),'inv' FROM tb_inventaire i JOIN tb_unite u ON i.codearticle=u.codearticle JOIN bu ON bu.idarticle=u.idarticle AND bu.idunite=u.idunite WHERE i.idmag=%s GROUP BY bu.idarticle,bu.idunite
                    ) ma
                    LEFT JOIN uc ON uc.idarticle=ma.idarticle AND uc.idunite=ma.idunite
                    GROUP BY ma.idarticle
                ),
                dp AS (
                    SELECT idarticle,idunite,prix,ROW_NUMBER() OVER(PARTITION BY idarticle,idunite ORDER BY id DESC) rn
                    FROM tb_prix
                )
                SELECT a.idarticle, u.idunite, u.codearticle, a.designation,
                       uc.designationunite, COALESCE(p.prix,0),
                       COALESCE(s.solde_base,0)/NULLIF(COALESCE(uc.coeff,1),0) AS stock
                FROM tb_article a
                JOIN tb_unite u ON a.idarticle=u.idarticle
                LEFT JOIN uc ON uc.idarticle=u.idarticle AND uc.idunite=u.idunite
                LEFT JOIN solde s ON s.idarticle=u.idarticle
                LEFT JOIN dp p ON p.idarticle=u.idarticle AND p.idunite=u.idunite AND p.rn=1
                WHERE a.deleted=0 AND (u.codearticle ILIKE %s OR a.designation ILIKE %s)
                ORDER BY a.designation, u.codearticle
                """, [idmag]*10 + [f"%{filtre}%", f"%{filtre}%"])

                for idx, row in enumerate(cur.fetchall()):
                    stk = max(0, row[6])
                    tags = ("even" if idx % 2 == 0 else "odd",)
                    if stk <= 0: tags = tags + ("stock_nul",)
                    tree.insert("", "end", values=(
                        row[0], row[1], row[2] or "",
                        row[3] or "", row[4] or "",
                        self.formater_nombre(row[5]),
                        self.formater_nombre(stk),
                    ), tags=tags)
            except Exception as e:
                messagebox.showerror("Erreur chargement", str(e))
            finally:
                cur.close(); conn.close()

        entry_search.bind("<KeyRelease>", lambda _e: charger(entry_search.get()))

        def valider():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Attention", "Sélectionnez un article.")
                return
            vals = tree.item(sel[0])['values']
            stk  = self.parser_nombre(str(vals[6]))
            if stk <= 0:
                messagebox.showwarning(
                    "Stock insuffisant",
                    f"Stock disponible : {vals[6]} {vals[4]}. Impossible de continuer.",
                )
                return
            self.stock_temporaire_selection = stk
            fen.destroy()
            self.on_article_selected({
                'idarticle':   vals[0],
                'idunite':     vals[1],
                'code_article': vals[2],
                'nom_article': vals[3],
                'nom_unite':   vals[4],
                'prixunit':    self.parser_nombre(str(vals[5])),
                'stock_temporaire': stk,
            })

        tree.bind("<Double-Button-1>", lambda _e: valider())

        bf = ctk.CTkFrame(mf, fg_color="transparent")
        bf.pack(fill="x", padx=12, pady=(0, 12))
        styled.button_danger(bf,  text="❌ Annuler", command=fen.destroy, width=120).pack(side="left")
        styled.button_success(bf, text="✅ Valider", command=valider, width=120).pack(side="right")
        charger()

    def on_article_selected(self, article_data: Dict):
        """Remplit les champs de saisie après sélection d'un article."""
        self.article_selectionne = article_data
        self.stock_temporaire_selection = article_data.get("stock_temporaire",
                                                            self.stock_temporaire_selection)
        label = f"[{article_data.get('code_article','N/A')}] {article_data['nom_article']}"

        for e, val, st in [
            (self.entry_article, label, "readonly"),
            (self.entry_unite,   article_data['nom_unite'], "readonly"),
        ]:
            e.configure(state="normal")
            e.delete(0, "end"); e.insert(0, val)
            e.configure(state=st)

        self.entry_prixunit.configure(state="normal")
        self.entry_prixunit.delete(0, "end")
        self.entry_prixunit.insert(0, self.formater_nombre(article_data.get('prixunit', 0)))
        self.entry_prixunit.configure(state="readonly")

        self.entry_qtvente.delete(0, "end")
        self.entry_qtvente.focus_set()

        # Callback optionnel (ex. affichage stock par dépôt)
        cb = getattr(self, 'on_article_selected_callback', None)
        if cb:
            try:
                cb(article_data['idarticle'], article_data['idunite'],
                   article_data.get('code_article', ''), article_data['nom_article'],
                   article_data['nom_unite'], check_only=False)
            except Exception as e:
                print(f"Erreur callback stock: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 10 — LOGIQUE MÉTIER : ENREGISTREMENT FACTURE
    # ──────────────────────────────────────────────────────────────────────────

    def _on_enregistrer_click(self):
        """Garde-fou UI : vérifie le client, désactive le bouton puis délègue."""
        if getattr(self, '_enregistrement_en_cours', False):
            return
        if not self.entry_client.get().strip():
            messagebox.showwarning("Attention", "Veuillez entrer ou choisir un client.")
            return
        try:
            self.btn_enregistrer.configure(state="disabled")
            self.enregistrer_facture()
        finally:
            try:
                self.btn_enregistrer.configure(state="normal")
            except Exception:
                pass

    def enregistrer_facture(self):
        """
        Sauvegarde une ou plusieurs factures (une par magasin) en base de données.
        Après succès, déclenche l'impression automatique selon les settings.json.
        """
        if self._enregistrement_en_cours:
            print("⚠ Enregistrement déjà en cours, ignoré")
            return
        self._enregistrement_en_cours = True
        self.btn_enregistrer.configure(state="disabled")

        try:
            # ── Validations préliminaires ──────────────────────────────────────
            if not self.detail_vente:
                messagebox.showwarning("Attention", "Ajoutez des articles avant d'enregistrer.")
                return
            if self.id_user_connecte is None:
                messagebox.showerror("Erreur", "Aucun utilisateur connecté.")
                return

            date_str    = self.entry_date_vente.get()
            description = self.entry_designation.get().strip()
            client_nom  = self.entry_client.get().strip()

            if not client_nom:
                messagebox.showerror("Erreur", "Veuillez entrer ou choisir un client.")
                return

            conn = self._connect_db()
            if not conn: return
            cur = conn.cursor()

            # ── Vérification du crédit client ──────────────────────────────────
            try:
                cur.execute("SELECT credit FROM tb_client WHERE nomcli=%s AND deleted=0",
                            (client_nom,))
                row = cur.fetchone()
                if row and row[0] is not None:
                    total_vente = sum(
                        max(0, float(d['qtvente']) * float(d['prixunit'])
                            - float(d.get('remise', 0)) * float(d['qtvente']))
                        for d in self.detail_vente
                    )
                    if total_vente > row[0]:
                        messagebox.showerror(
                            "❌ Crédit Dépassé",
                            f"Client : {client_nom}\n"
                            f"Montant vente : {self.formater_nombre(total_vente)} Ar\n"
                            f"Crédit autorisé : {self.formater_nombre(row[0])} Ar\n"
                            f"Dépassement : {self.formater_nombre(total_vente - row[0])} Ar\n\n"
                            "Réduisez le montant ou augmentez le crédit du client."
                        )
                        return
            except Exception as e:
                messagebox.showerror("Erreur", f"Vérification crédit : {e}")
                return

            # ── Gestion / création du client ───────────────────────────────────
            idclient = self.client_map.get(client_nom)
            if not idclient:
                try:
                    cur.execute("INSERT INTO tb_client (nomcli, deleted) VALUES (%s, 0) RETURNING idclient",
                                (client_nom,))
                    idclient = cur.fetchone()[0]
                    conn.commit()
                    self.client_map[client_nom] = idclient
                except Exception as e:
                    conn.rollback()
                    messagebox.showerror("Erreur", f"Impossible d'ajouter le client : {e}")
                    return

            # ── Parse de la date ───────────────────────────────────────────────
            try:
                now = datetime.now()
                date_vente = datetime.strptime(date_str, "%d/%m/%Y").replace(
                    hour=now.hour, minute=now.minute, second=now.second)
            except ValueError:
                messagebox.showerror("Erreur de Date", "Format attendu : JJ/MM/AAAA")
                return

            # ── Groupement par magasin ─────────────────────────────────────────
            details_par_mag: Dict[int, list] = {}
            for d in self.detail_vente:
                details_par_mag.setdefault(d['idmag'], []).append(d)

            self.idventes_par_magasin = {}
            factures_creees = []

            try:
                for idmag, details_mag in details_par_mag.items():
                    # Calcul du total pour ce magasin
                    total_mag = sum(
                        max(0, float(d['qtvente']) * float(d['prixunit'])
                            - float(d.get('remise', 0)) * float(d['qtvente']))
                        for d in details_mag
                    )
                    nom_mag = details_mag[0]['designationmag']

                    # Référence unique par magasin
                    annee = now.year
                    cur.execute("""
                        SELECT refvente FROM tb_vente
                        WHERE refvente ILIKE %s ORDER BY id DESC LIMIT 1
                    """, (f"%{annee}-FA-%",))
                    r = cur.fetchone()
                    num = 1
                    if r:
                        parts = r[0].split('-')
                        if len(parts) == 3 and parts[1] == 'FA':
                            try: num = int(parts[-1]) + 1
                            except ValueError: pass
                    ref_mag = f"{annee}-FA-{num:05d}"

                    # Insertion en-tête
                    cur.execute("""
                        INSERT INTO tb_vente
                            (refvente, dateregistre, description, iduser, idclient,
                             totmtvente, idmag, statut, deleted)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,0) RETURNING id
                    """, (ref_mag, date_vente,
                          f"{description} - {nom_mag}" if description else nom_mag,
                          self.id_user_connecte, idclient, total_mag, idmag, 'EN_ATTENTE'))
                    idvente = cur.fetchone()[0]
                    self.idventes_par_magasin[idmag] = idvente

                    # Insertion des lignes de détail
                    cur.executemany("""
                        INSERT INTO tb_ventedetail
                            (idvente, idarticle, idunite, qtvente, prixunit, remise, idmag)
                        VALUES (%s,%s,%s,%s,%s,%s,%s)
                    """, [(idvente, d['idarticle'], d['idunite'], d['qtvente'],
                           d['prixunit'], d.get('remise', 0), d['idmag'])
                          for d in details_mag])

                    factures_creees.append({'ref': ref_mag, 'magasin': nom_mag,
                                             'total': total_mag, 'idvente': idvente})
                    print(f"✅ Facture {ref_mag} — {nom_mag} — {self.formater_nombre(total_mag)} Ar")

                conn.commit()

            except psycopg2.errors.UniqueViolation as e:
                conn.rollback()
                messagebox.showerror("Doublon", f"Facture déjà existante.\n{e}")
                return
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Erreur", str(e))
                traceback.print_exc()
                return
            finally:
                cur.close(); conn.close()

            # ── Affichage de la confirmation ───────────────────────────────────
            total_general = sum(f['total'] for f in factures_creees)
            if self.settings.get('Vente_ImpressionConfirmation', 1):
                lines = "\n".join(f"• {f['ref']} ({f['magasin']}): {self.formater_nombre(f['total'])} Ar"
                                  for f in factures_creees)
                messagebox.showinfo("Succès",
                    f"{len(factures_creees)} facture(s) créée(s) :\n\n{lines}"
                    f"\n\nTotal : {self.formater_nombre(total_general)} Ar")

            # ── Impression automatique selon settings ──────────────────────────
            imp_a5     = self.settings.get('Vente_ImpressionA5', 1)
            imp_ticket = self.settings.get('Vente_ImpressionTicket', 0)
            try:
                for fac in factures_creees:
                    if imp_a5 or imp_ticket:
                        self.imprimer_facture_avec_settings(fac['idvente'], imp_a5, imp_ticket)
            except Exception as e:
                messagebox.showerror("Erreur Impression",
                                     f"Facture enregistrée mais impression échouée : {e}")

            # ── Réinitialisation du formulaire ─────────────────────────────────
            try:
                self.nouveau_facture()
            except Exception:
                pass

        finally:
            self._enregistrement_en_cours = False
            try:
                self.btn_enregistrer.configure(state="normal")
            except Exception:
                pass

    def nouveau_facture(self):
        """Réinitialise TOUT le formulaire pour une nouvelle facture vierge."""
        self.generer_reference()
        self.entry_date_vente.delete(0, "end")
        self.entry_date_vente.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.entry_designation.delete(0, "end")
        self.entry_client.delete(0, "end")
        self.detail_vente = []
        self.charger_details_treeview()
        self.idvente_charge   = None
        self.mode_modification = False
        self.entry_remise.configure(state="disabled")
        self.entry_remise.delete(0, "end")
        # masquer colonne remise au démarrage d'une nouvelle facture
        self._hide_remise_column()
        self.btn_enregistrer.configure(
            state="normal", text="💾 Enregistrer la Facture",
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
        )
        self.reset_proforma_state()

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 11 — LOGIQUE MÉTIER : IMPRESSION PDF
    # ──────────────────────────────────────────────────────────────────────────

    def imprimer_facture_avec_settings(self, idvente: int, a5: int, ticket: int):
        """Impression directe (sans dialogue) selon les flags a5/ticket de settings.json."""
        data = self.get_data_facture(idvente)
        if not data or not data.get('vente'):
            print(f"❌ Données introuvables pour l'ID : {idvente}")
            return
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        ref = data['vente']['refvente']
        try:
            if a5:
                fn = f"Facture_{ref}_{ts}.pdf"
                self.generate_pdf_a5(data, fn)
                self.open_file(fn)
            if ticket:
                fn = f"Ticket_{ref}_{ts}.pdf"
                self.generate_ticket_80mm(data, fn)
                self.open_file(fn)
        except Exception as e:
            messagebox.showerror("Erreur Impression", str(e))

    def imprimer_facture_unique(self, idvente: int):
        """Impression avec dialogue de choix du format (A5 ou Ticket 80 mm)."""
        data = self.get_data_facture(idvente)
        if not data or not data.get('vente'):
            messagebox.showerror("Erreur", f"Données introuvables (ID: {idvente}).")
            return
        dlg = SimpleDialogWithChoice(self,
                                      title="Format d'impression",
                                      message="Choisissez le format de la facture :")
        if not dlg.result:
            return
        ts  = datetime.now().strftime('%Y%m%d_%H%M%S')
        ref = data['vente']['refvente']
        if dlg.result == "A5 PDF (Paysage)":
            fn = f"Facture_{ref}_{ts}.pdf"
            self.generate_pdf_a5(data, fn)
        else:
            fn = f"Ticket_{ref}_{ts}.pdf"
            self.generate_ticket_80mm(data, fn)
        self.open_file(fn)

    def open_file(self, filename: str):
        """Ouvre le PDF généré avec le lecteur par défaut du système."""
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
        Récupère toutes les données d'une facture (en-tête + lignes + société)
        pour la génération des PDF.
        """
        conn = self._connect_db()
        if not conn: return None
        data = {'societe': self.infos_societe, 'vente': None, 'utilisateur': None, 'details': []}
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT v.refvente, v.dateregistre, v.description,
                       u.nomuser, u.prenomuser,
                       c.nomcli, c.adressecli, c.contactcli
                FROM tb_vente v
                INNER JOIN tb_users u ON v.iduser=u.iduser
                LEFT JOIN tb_client c ON v.idclient=c.idclient
                WHERE v.id=%s
            """, (idvente,))
            row = cur.fetchone()
            if not row: return None
            ref, date_r, desc, nomuser, prenomuser, nomcli, adr, contact = row
            data['vente']       = {'refvente': ref,
                                    'dateregistre': date_r.strftime("%d/%m/%Y %H:%M"),
                                    'description': desc}
            data['utilisateur'] = {'nomuser': nomuser or '', 'prenomuser': prenomuser or ''}
            data['client']      = {'nomcli': nomcli or 'Client Divers',
                                   'adressecli': adr or 'N/A',
                                   'contactcli': contact or 'N/A'}

            cur.execute("""
                SELECT u.codearticle, a.designation, u.designationunite,
                       vd.qtvente, vd.prixunit, COALESCE(vd.remise,0), m.designationmag
                FROM tb_ventedetail vd
                INNER JOIN tb_article a ON vd.idarticle=a.idarticle
                INNER JOIN tb_unite u ON vd.idunite=u.idunite
                INNER JOIN tb_magasin m ON vd.idmag=m.idmag
                WHERE vd.idvente=%s ORDER BY a.designation
            """, (idvente,))
            premier_mag = None
            for r in cur.fetchall():
                code, desig, unite, qte, pu, remise, mag = r
                if not premier_mag: premier_mag = mag
                ht  = float(qte) * float(pu)
                rmt = float(remise) * float(qte)
                ttc = max(0, ht - rmt)
                data['details'].append({
                    'code_article': code, 'designation': desig,
                    'unite': unite, 'qte': float(qte),
                    'prixunit': float(pu), 'remise': float(remise), 'magasin': mag,
                    'montant_ht': ht, 'montant_remise': rmt, 'montant_ttc': ttc,
                })
            if premier_mag:
                data['vente']['description'] = f"Magasin {premier_mag}"
                if desc and desc.strip() and premier_mag not in desc:
                    data['vente']['description'] += f" — {desc.strip().strip('-').strip()}"
            data['magasin'] = premier_mag or ''
            return data
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
            traceback.print_exc()
            return None
        finally:
            cur.close(); conn.close()

    # ── generate_pdf_a5 : inchangé (logique ReportLab complexe) ───────────────
    def generate_pdf_a5(self, data: dict, filename: str):
        """
        Génère le PDF de la facture au format A5 paysage.
        Supporte plusieurs pages (saut automatique au-delà de 25 lignes).
        Total Ar / FMG en bas du dernier tableau, somme en lettres dans le footer.
        """
        from reportlab.lib.pagesizes import A5
        from reportlab.lib import colors as rl_colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.platypus import Table as RLTable, TableStyle as RLTableStyle, Paragraph

        MAX_P1 = 25; MAX_PN = 30; MARGIN = 10 * mm
        c = rl_canvas.Canvas(filename, pagesize=A5)
        width, height = A5
        soc  = data['societe']
        util = data['utilisateur']
        cli  = data['client']
        vte  = data['vente']
        mag  = data.get('magasin', '')

        nomsoc = soc.get('nomsociete', 'N/A')
        adr    = soc.get('adressesociete') or 'N/A'
        ville  = soc.get('villesociete') or ''
        tel    = soc.get('contactsociete') or 'N/A'
        nif    = soc.get('nifsociete') or 'N/A'
        stat   = soc.get('statsociete') or 'N/A'
        user_n = f"{util.get('prenomuser','')} {util.get('nomuser','')}".strip()
        cli_n  = cli.get('nomcli', '')

        styles = getSampleStyleSheet()
        sp = ParagraphStyle('sp', fontSize=9, leading=11, parent=styles['Normal'])

        def draw_verset():
            verse = "Ankino amin'ny Jehovah ny asanao dia ho lavorary izay kasainao. Ohabolana 16:3"
            c.setLineWidth(1); c.rect(MARGIN, height-13*mm, width-2*MARGIN, 8*mm)
            c.setFont("Helvetica-Bold", 9)
            c.drawCentredString(width/2, height-10.5*mm, verse)

        def draw_header(cont=False):
            g = Paragraph(
                f"<b><font size='11'>{nomsoc}</font></b><br/>{adr}<br/>"
                f"{''+ville+'<br/>' if ville else ''}TEL: {tel}<br/>NIF: {nif}<br/>STAT: {stat}", sp)
            suite = " <i>(suite)</i>" if cont else ""
            d_ = Paragraph(
                f"<b>Facture N°: {vte['refvente']}{suite}</b><br/>"
                f"{vte['dateregistre']}<br/><b>MAGASIN {mag}</b><br/><br/>"
                f"<i>Client: {cli_n}</i><br/><font size='7'>Op: {user_n}</font>", sp)
            ht = RLTable([[g, d_]], colWidths=[64*mm, 64*mm])
            ht.setStyle(RLTableStyle([
                ('GRID', (0,0),(-1,-1), 1, rl_colors.black),
                ('VALIGN',(0,0),(-1,-1),'TOP'),
                ('LEFTPADDING',(0,0),(-1,-1),8),
                ('TOPPADDING',(0,0),(-1,-1),5),
                ('BOTTOMPADDING',(0,0),(-1,-1),5),
            ]))
            ht.wrapOn(c, width, height); ht.drawOn(c, MARGIN, height-42*mm)

        def draw_footer(total_m, table_bottom):
            usable = width - 2*MARGIN
            lettres = nombre_en_lettres_fr(int(total_m)).upper()
            pb = ParagraphStyle('pb', parent=styles['Normal'],
                                fontName='Helvetica-Bold', fontSize=9, leading=12, alignment=1)
            pi = ParagraphStyle('pi', parent=styles['Normal'],
                                fontName='Helvetica-Oblique', fontSize=8, leading=10, alignment=1)
            pl = Paragraph(f"ARRETE A LA SOMME DE {lettres} ARIARY TTC", pb)
            pm = Paragraph("Nous déclinons la responsabilité des marchandises non livrées au-delà de 5 jours", pi)
            _, hl = pl.wrap(usable, 40*mm); _, hm = pm.wrap(usable, 20*mm)
            yl = table_bottom - 3*mm - hl; ym = yl - 2*mm - hm
            pl.drawOn(c, MARGIN, yl); pm.drawOn(c, MARGIN, ym)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(MARGIN, 15*mm, "Le Client")
            c.drawCentredString(width/2, 15*mm, "Le Caissier")
            c.drawString(width-35*mm, 15*mm, "Le Magasinier")

        def draw_table(t_top, t_bot, rows, show_tot, total_m=0):
            fh = t_top - t_bot
            cws = [12*mm, 15*mm, 62*mm, 19.5*mm, 19.5*mm]
            rhe = 5.5*mm; max_r = int(fh/rhe)
            res = 2 if show_tot else 0
            slots = max_r - 1 - res
            body = list(rows)
            for _ in range(max(0, slots-len(body))): body.append(['']*5)
            if show_tot:
                body += [['', '', 'TOTAL Ar :', self.formater_nombre_pdf(total_m), ''],
                         ['', '', 'Fmg :',      self.formater_nombre_pdf(total_m*5), '']]
            td = [['QTE','UNITE','DESIGNATION','PU TTC','MONTANT']] + body
            c.setLineWidth(1); c.rect(MARGIN, t_bot, width-2*MARGIN, fh)
            xp = MARGIN
            for w_ in cws[:-1]:
                xp += w_; c.line(xp, t_top, xp, t_bot)
            arh = fh/len(td)
            cmds = [
                ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,0),10),
                ('LINEBELOW',(0,0),(-1,0),1,rl_colors.black),('FONTSIZE',(0,1),(-1,-1),8),
                ('ALIGN',(3,0),(-1,-1),'RIGHT'),('ALIGN',(0,0),(2,0),'LEFT'),
                ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                ('LEFTPADDING',(0,0),(-1,-1),2),('RIGHTPADDING',(3,0),(-1,-1),2),
                ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
            ]
            if show_tot:
                cmds += [
                    ('FONTNAME',(0,-2),(-1,-1),'Helvetica-Bold'),('FONTSIZE',(0,-2),(-1,-1),9),
                    ('LINEABOVE',(0,-2),(-1,-2),1,rl_colors.black),
                    ('ALIGN',(2,-2),(2,-1),'RIGHT'),
                    ('BACKGROUND',(0,-2),(-1,-1),rl_colors.Color(0.93,0.93,0.93)),
                ]
            t = RLTable(td, colWidths=cws, rowHeights=[arh]*len(td))
            t.setStyle(RLTableStyle(cmds))
            t.wrapOn(c, width, height)
            t.drawOn(c, MARGIN, t_top - len(td)*arh)
            return t_bot

        total_m = 0; all_rows = []
        for d in data['details']:
            mt = d.get('montant_ttc', d.get('montant', 0)); total_m += mt
            all_rows.append([str(int(d.get('qte',0))), str(d.get('unite','')),
                              str(d.get('designation','')),
                              self.formater_nombre_pdf(d.get('prixunit',0)),
                              self.formater_nombre_pdf(mt)])

        pages = []
        if len(all_rows) <= MAX_P1:
            pages.append(('first', all_rows))
        else:
            pages.append(('first', all_rows[:MAX_P1]))
            reste = all_rows[MAX_P1:]
            while reste: pages.append(('cont', reste[:MAX_PN])); reste = reste[MAX_PN:]

        for idx, (ptype, rows) in enumerate(pages):
            last = (idx == len(pages)-1)
            draw_verset(); draw_header(ptype == 'cont')
            t_top = height-45*mm; t_bot = 55*mm if last else 15*mm
            tb = draw_table(t_top, t_bot, rows, last, total_m)
            if last: draw_footer(total_m, tb)
            if len(pages) > 1:
                c.setFont("Helvetica", 7)
                c.drawCentredString(width/2, 8*mm, f"Page {idx+1} / {len(pages)}")
            if not last: c.showPage()
        try:
            c.save()
            print(f"✅ PDF A5 généré : {filename}")
        except Exception as e:
            print(f"❌ Erreur PDF A5 : {e}"); traceback.print_exc()

    def generate_ticket_80mm(self, data: Dict[str, Any], filename: str):
        """Génère un PDF ticket de caisse format 80 mm (texte étroit)."""
        from reportlab.lib.units import mm
        from reportlab.lib.enums import TA_CENTER

        TW = 80*mm
        doc = SimpleDocTemplate(filename, pagesize=(TW, 297*mm),
                                 leftMargin=3*mm, rightMargin=3*mm,
                                 topMargin=5*mm, bottomMargin=5*mm)
        elems = []; styles = getSampleStyleSheet()
        soc = data['societe']; vte = data['vente']
        cli = data['client'];  dets = data['details']
        LW  = TW - 6*mm

        sc = ParagraphStyle('sc', alignment=TA_CENTER, fontSize=10, leading=12,
                             parent=styles['Normal'])
        scb = ParagraphStyle('scb', alignment=TA_CENTER, fontSize=11, leading=13,
                              fontName='Helvetica-Bold', parent=styles['Normal'])
        sn  = ParagraphStyle('sn', fontSize=9, leading=11, parent=styles['Normal'])
        ss  = ParagraphStyle('ss', fontSize=8, leading=10, parent=styles['Normal'])

        elems += [Paragraph(f"<b>{soc.get('nomsociete','SOCIÉTÉ')}</b>", scb),
                  Paragraph(soc.get('adressesociete',''), sc),
                  Paragraph(soc.get('villesociete',''), sc),
                  Paragraph(f"Tél: {soc.get('contactsociete','')}", sc),
                  Spacer(1, 3*mm),
                  Table([["="*48]], colWidths=[LW]),
                  Spacer(1, 2*mm),
                  Paragraph(f"<b>FACTURE N° {vte['refvente']}</b>", scb),
                  Paragraph(f"Date: {vte['dateregistre']}", sn),
                  Paragraph(f"Client: {cli['nomcli']}", sn),
                  Spacer(1, 2*mm),
                  Table([["="*48]], colWidths=[LW]),
                  Spacer(1, 2*mm)]

        total_ht = total_rem = total_ttc = 0.0
        for d in dets:
            elems.append(Paragraph(f"<b>{d.get('designation','')}</b>", sn))
            ld = Table([[f"{int(d.get('qte',0))} {d.get('unite','')} × {self.formater_nombre_pdf(d.get('prixunit',0))}",
                         f"= {self.formater_nombre_pdf(d.get('montant_ttc',0))}"]],
                        colWidths=[50*mm, 20*mm])
            ld.setStyle(TableStyle([
                ('ALIGN',(0,0),(0,0),'LEFT'), ('ALIGN',(1,0),(1,0),'RIGHT'),
                ('FONTSIZE',(0,0),(-1,-1),8),
                ('LEFTPADDING',(0,0),(-1,-1),2), ('RIGHTPADDING',(0,0),(-1,-1),0),
                ('TOPPADDING',(0,0),(-1,-1),0),  ('BOTTOMPADDING',(0,0),(-1,-1),0),
            ]))
            elems += [ld, Spacer(1, 2*mm)]
            total_ht  += d.get('montant_ht', 0)
            total_rem += d.get('montant_remise', 0)
            total_ttc += d.get('montant_ttc', 0)

        # Totaux
        tot_data = [['TOTAL HT:', self.formater_nombre_pdf(total_ht)]]
        if total_rem > 0:
            tot_data.append(['REMISE:', f"-{self.formater_nombre_pdf(total_rem)}"])
        tt = Table(tot_data, colWidths=[35*mm, 35*mm])
        tt.setStyle(TableStyle([
            ('ALIGN',(0,0),(0,-1),'LEFT'), ('ALIGN',(1,0),(1,-1),'RIGHT'),
            ('FONTSIZE',(0,0),(-1,-1),9),
        ]))
        sm = ParagraphStyle('sm', alignment=TA_CENTER, fontSize=14,
                             fontName='Helvetica-Bold', leading=16, parent=styles['Normal'])
        sf = ParagraphStyle('sf', alignment=TA_CENTER, fontSize=11,
                             fontName='Helvetica-Bold', leading=13, parent=styles['Normal'])

        fmg = total_ttc * 5
        elems += [
            Table([["="*48]], colWidths=[LW]), Spacer(1, 2*mm),
            tt, Spacer(1, 2*mm),
            Table([["="*48]], colWidths=[LW]), Spacer(1, 2*mm),
            Paragraph("<b>*** MONTANT À PAYER ***</b>", scb),
            Paragraph(f"<b>{self.formater_nombre_pdf(total_ttc)} Ar</b>", sm),
            Spacer(1, 2*mm),
            Paragraph(f"<b>En FMG: {self.formater_nombre_pdf(fmg)} FMG</b>", sf),
            Spacer(1, 2*mm),
            Table([["="*48]], colWidths=[LW]), Spacer(1, 3*mm),
            Paragraph("<b>TOTAL EN LETTRES</b>", scb),
            Paragraph(nombre_en_lettres_fr(total_ttc), ss),
            Spacer(1, 2*mm),
            Table([["="*48]], colWidths=[LW]), Spacer(1, 5*mm),
            Paragraph("Merci de votre achat !", sc),
            Paragraph(datetime.now().strftime("%d/%m/%Y %H:%M:%S"), sc),
            Spacer(1, 10*mm),
        ]
        try:
            doc.build(elems)
            print(f"✅ Ticket PDF généré : {filename}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur ticket PDF : {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 12 — LOGIQUE MÉTIER : PROFORMAS
    # ──────────────────────────────────────────────────────────────────────────

    def open_recherche_proforma(self):
        """Ouvre la fenêtre de sélection d'un proforma avec statut 'A Facturer'."""
        if self.mode_modification:
            messagebox.showwarning("Attention", "Terminez la modification en cours.")
            return

        fen = ctk.CTkToplevel(self)
        fen.title("Charger un Proforma à Facturer")
        fen.geometry("900x500")
        fen.configure(fg_color=Colors.BG_PAGE)
        fen.grab_set()

        mf = ctk.CTkFrame(fen, fg_color=Colors.BG_CARD, corner_radius=12)
        mf.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(mf, text="📜 Sélectionner un Proforma à Facturer",
                     font=Fonts.heading(14), text_color=Colors.TEXT_PRIMARY).pack(pady=(12, 8))

        sf = ctk.CTkFrame(mf, fg_color="transparent")
        sf.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkLabel(sf, text="🔍", font=Fonts.body(14), text_color=Colors.TEXT_MUTED).pack(side="left")
        entry_search = ctk.CTkEntry(sf, placeholder_text="Référence ou client…",
                                     font=Fonts.input(12), fg_color=Colors.BG_INPUT,
                                     border_color=Colors.BORDER, height=32)
        entry_search.pack(side="left", fill="x", expand=True, padx=6)

        cols = ("ID","Ref Proforma","Date","Client","Montant Total","Nb Lignes")
        tree = ttk.Treeview(mf, columns=cols, show="headings",
                             height=14, style="Vente.Treeview")
        tree.tag_configure("even", background=Colors.BG_CARD)
        tree.tag_configure("odd",  background=Colors.BG_ROW_ALT)
        for col, w in zip(cols, [0, 120, 100, 250, 120, 80]):
            tree.heading(col, text=col); tree.column(col, width=w, anchor="center" if w < 150 else "w")
        tree.column("ID", width=0, stretch=False)
        tree.pack(fill="both", expand=True, padx=12, pady=8)

        def charger(filtre=""):
            for i in tree.get_children(): tree.delete(i)
            conn = self._connect_db()
            if not conn: return
            try:
                cur = conn.cursor()
                cur.execute("""
                    SELECT p.idprof, p.refprof, p.dateprof, c.nomcli,
                           SUM(pd.qtlivprof*pd.prixunit) AS total, COUNT(pd.idprof)
                    FROM tb_proforma p
                    INNER JOIN tb_client c ON p.idclient=c.idclient
                    LEFT JOIN tb_proformadetail pd ON p.idprof=pd.idprof
                    WHERE p.deleted=0 AND p.statut='✅ A Facturer'
                    AND (p.refprof ILIKE %s OR c.nomcli ILIKE %s)
                    GROUP BY p.idprof, p.refprof, p.dateprof, c.nomcli
                    ORDER BY p.dateprof DESC
                """, (f"%{filtre}%", f"%{filtre}%"))
                for idx, row in enumerate(cur.fetchall()):
                    idp, ref, dt, nom, tot, nb = row
                    tree.insert("", "end", values=(
                        idp, ref, dt.strftime("%d/%m/%Y"), nom,
                        self.formater_nombre(tot), nb,
                    ), tags=("even" if idx % 2 == 0 else "odd",))
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
            finally:
                cur.close(); conn.close()

        entry_search.bind("<KeyRelease>", lambda _e: charger(entry_search.get()))

        def valider():
            sel = tree.selection()
            if not sel: messagebox.showwarning("Attention", "Sélectionnez un proforma."); return
            idp = tree.item(sel[0])['values'][0]
            fen.destroy()
            self.charger_proforma_pour_vente(idp)

        tree.bind("<Double-Button-1>", lambda _e: valider())
        bf = ctk.CTkFrame(mf, fg_color="transparent")
        bf.pack(fill="x", padx=12, pady=(0, 12))
        styled.button_danger(bf,  text="❌ Annuler", command=fen.destroy, width=120).pack(side="left")
        styled.button_success(bf, text="✅ Charger", command=valider, width=120).pack(side="right")
        charger()

    def charger_proforma_pour_vente(self, idprof: int):
        """
        Charge les lignes d'un proforma en attente de validation du magasin.
        Les données sont stockées temporairement dans self.details_proforma_a_ajouter.
        """
        self.nouveau_facture(); self.reset_proforma_state()
        conn = self._connect_db()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT p.refprof, p.observation, c.nomcli, c.idclient
                FROM tb_proforma p INNER JOIN tb_client c ON p.idclient=c.idclient
                WHERE p.idprof=%s AND p.deleted=0
            """, (idprof,))
            row = cur.fetchone()
            if not row: messagebox.showerror("Erreur", "Proforma introuvable."); return
            refprof, obs, nomcli, idclient = row

            cur.execute("""
                SELECT pd.idarticle, ua.codearticle, a.designation,
                       pd.idunite, ua.designationunite, pd.qtlivprof, pd.prixunit
                FROM tb_proformadetail pd
                INNER JOIN tb_article a ON pd.idarticle=a.idarticle
                INNER JOIN tb_unite ua ON pd.idunite=ua.idunite
                WHERE pd.idprof=%s
            """, (idprof,))
            cols = ['idarticle','code_article','nom_article','idunite','nom_unite','qtvente','prixunit']
            self.details_proforma_a_ajouter = [dict(zip(cols, r)) for r in cur.fetchall()]

            self.entry_client.delete(0, "end"); self.entry_client.insert(0, nomcli)
            self.entry_designation.delete(0, "end")
            self.entry_designation.insert(0, f"Suivant Proforma n° {refprof}")
            self.client_map[nomcli] = idclient
            self.details_proforma_a_ajouter_idprof = idprof
            self.detail_vente = []; self.charger_details_treeview()
            self.desactiver_entree_manuelle()
            self.afficher_bouton_ajouter_proforma()
            messagebox.showinfo("Proforma Chargé",
                                f"Proforma N° {refprof} chargé.\n\n"
                                "Sélectionnez le Magasin puis cliquez sur "
                                "'Ajouter Lignes Proforma'.")
        except Exception as e:
            messagebox.showerror("Erreur", str(e)); self.reset_proforma_state()
        finally:
            cur.close(); conn.close()

    def ajouter_details_proforma_en_masse(self):
        """
        Ajoute toutes les lignes du proforma dans le tableau de vente après
        vérification du stock disponible et des règles Dépôt B.
        """
        if not self.details_proforma_a_ajouter:
            messagebox.showwarning("Attention", "Aucun détail proforma à ajouter.")
            return

        mag_nom = self.combo_magasin.get()
        idmag   = self.magasin_map.get(mag_nom)
        if not idmag:
            messagebox.showerror("Erreur", "Sélectionnez un magasin valide.")
            return

        ajoutes = []; bloquee = []; stock_insuf = []

        for d in self.details_proforma_a_ajouter:
            ia, iu = d['idarticle'], d['idunite']
            ok, msg = self.verifier_unite_depot_b(ia, iu)
            if not ok:
                bloquee.append(f"{d['code_article']} ({d['nom_article']}): {msg}")
                continue
            stock = self.calculer_stock_article(ia, iu, idmag)
            if stock < d['qtvente']:
                stock_insuf.append(
                    f"{d['code_article']} ({d['nom_article']}): "
                    f"Demandé {self.formater_nombre(d['qtvente'])} / "
                    f"Dispo {self.formater_nombre(stock)}"
                )
                continue
            nd = {**d, 'designationmag': mag_nom, 'idmag': idmag}
            ht = nd['qtvente'] * nd['prixunit']
            nd.update({'remise': 0, 'montant_ht': ht, 'montant_remise': 0, 'montant_ttc': ht})
            ajoutes.append(nd)

        if ajoutes:
            self.detail_vente.extend(ajoutes)
            self.charger_details_treeview()
            if self.details_proforma_a_ajouter_idprof:
                self.marquer_proforma_comme_facture(self.details_proforma_a_ajouter_idprof)

        self.reset_proforma_state()
        errs = []
        if bloquee:    errs.append("⚠ UNITÉS BLOQUÉES (Dépôt B):\n" + "\n".join(bloquee))
        if stock_insuf: errs.append("📦 STOCK INSUFFISANT:\n" + "\n".join(stock_insuf))
        if errs:
            messagebox.showwarning("Attention",
                                   f"{len(ajoutes)} ligne(s) ajoutée(s).\n\n" + "\n\n".join(errs))
        else:
            messagebox.showinfo("Ajout Réussi",
                                f"Toutes les {len(ajoutes)} lignes ont été ajoutées.")

    def marquer_proforma_comme_facture(self, idprof: int):
        """Met le statut du proforma à 'Facturé' après conversion en vente."""
        conn = self._connect_db()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("UPDATE tb_proforma SET statut=%s, datefacturation=%s WHERE idprof=%s",
                        ('Facturé', datetime.now().date(), idprof))
            conn.commit()
            print(f"Proforma {idprof} → 'Facturé'")
        except Exception as e:
            conn.rollback(); print(f"Erreur statut proforma: {e}")
        finally:
            cur.close(); conn.close()

    def desactiver_entree_manuelle(self):
        """Désactive tous les champs de saisie manuelle (mode proforma en cours)."""
        self.entry_article.configure(state="readonly")
        self.entry_qtvente.configure(state="readonly")
        self.entry_unite.configure(state="readonly")
        self.entry_prixunit.configure(state="readonly")
        self.btn_recherche_article.configure(state="disabled")
        self.btn_ajouter.grid_forget()

    def activer_entree_manuelle(self):
        """Réactive tous les champs de saisie manuelle (après proforma ou annulation)."""
        self.entry_article.configure(state="readonly")
        self.entry_qtvente.configure(state="normal")
        self.entry_unite.configure(state="readonly")
        self.entry_prixunit.configure(state="readonly")
        self.btn_recherche_article.configure(state="normal")
        self.btn_ajouter.grid(row=1, column=6, padx=(4, 8), pady=(0, 6))

    def afficher_bouton_ajouter_proforma(self):
        """Affiche les boutons de masse proforma et masque les contrôles standard."""
        self.btn_ajouter.grid_forget()
        self.btn_annuler_mod.grid_forget()
        self.btn_ajouter_proforma_bulk.grid(row=1, column=5, padx=5, pady=(0, 6))

        # Bouton d'annulation du chargement proforma (créé dynamiquement)
        self.btn_annuler_proforma = ctk.CTkButton(
            self.btn_ajouter_proforma_bulk.master,
            text="✖ Annuler Proforma", height=30, font=Fonts.button(11),
            corner_radius=6, fg_color=Colors.DANGER, hover_color=Colors.DANGER_DARK,
            command=self.reset_proforma_state,
        )
        self.btn_annuler_proforma.grid(row=1, column=6, padx=5, pady=(0, 6))

        # Verrouiller les contrôles principaux pendant le chargement proforma
        self.btn_enregistrer.configure(state="disabled")
        self.btn_charger_proforma.configure(state="disabled")
        self.btn_search_client.configure(state="disabled")
        self.entry_client.configure(state="readonly")

    def masquer_bouton_ajouter_proforma(self):
        """Masque les boutons proforma et nettoie les widgets dynamiques."""
        self.btn_ajouter_proforma_bulk.grid_forget()
        if hasattr(self, 'btn_annuler_proforma'):
            self.btn_annuler_proforma.grid_forget()
            del self.btn_annuler_proforma

    def reset_proforma_state(self):
        """Réinitialise l'état complet lié au proforma (annulation ou après ajout)."""
        self.details_proforma_a_ajouter       = None
        self.details_proforma_a_ajouter_idprof = None
        self.masquer_bouton_ajouter_proforma()
        self.activer_entree_manuelle()
        if not self.mode_modification:
            self.btn_enregistrer.configure(state="normal")
            self.btn_charger_proforma.configure(state="normal")
            self.btn_search_client.configure(state="normal")
            self.entry_client.configure(state="normal")
        if not self.detail_vente and not self.mode_modification:
            self.entry_client.delete(0, "end")
            self.entry_designation.delete(0, "end")
            self.generer_reference()
        self.reset_detail_form()

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 13 — LOGIQUE MÉTIER : DROITS & AUTORISATION
    # ──────────────────────────────────────────────────────────────────────────

    def verifier_droits_admin(self):
        """Demande un code d'autorisation pour activer la remise et l'avoir."""
        self.btn_creer_avoir.configure(state="disabled")
        self.entry_remise.configure(state="disabled")
        dlg = PasswordDialog("Autorisation requise", "Code d'autorisation :")
        if not dlg.result:
            return
        conn = self._connect_db()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM tb_codeautorisation WHERE code=%s", (dlg.result,))
            if cur.fetchone():
                self.btn_creer_avoir.configure(state="normal")
                self.entry_remise.configure(state="normal")
                messagebox.showinfo("Succès", "Accès accordé aux remises et avoirs.")
            else:
                messagebox.showerror("Erreur", "Code d'autorisation incorrect.")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
        finally:
            conn.close()

    def verifier_code_autorisation(self, code_saisi: str) -> bool:
        """Vérifie un code d'autorisation en base (utilisé pour l'ouverture Avoir)."""
        conn = self._connect_db()
        if not conn: return False
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM tb_codeautorisation WHERE TRIM(code)=%s",
                        (str(code_saisi).strip(),))
            return cur.fetchone() is not None
        except Exception as e:
            print(f"Erreur vérification code: {e}"); return False
        finally:
            conn.close()

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 14 — LOGIQUE MÉTIER : ALERTES STOCK
    # ──────────────────────────────────────────────────────────────────────────

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 15 — LOGIQUE MÉTIER : FENÊTRES SECONDAIRES
    # ──────────────────────────────────────────────────────────────────────────

    def tentative_ouverture_avoir(self):
        """Ouvre la page Avoir après vérification du code d'autorisation."""
        dlg = PasswordDialog("Autorisation Requise", "Code pour créer un avoir :")
        if dlg.result and self.verifier_code_autorisation(dlg.result):
            self.ouvrir_la_page_avoir_réellement()
        elif dlg.result:
            messagebox.showerror("Accès Refusé", "Code d'autorisation incorrect.")

    def ouvrir_la_page_avoir_réellement(self):
        """Instancie PageAvoir dans un CTkToplevel modal."""
        if hasattr(self, 'fenetre_avoir') and self.fenetre_avoir.winfo_exists():
            self.fenetre_avoir.focus(); return
        self.fenetre_avoir = ctk.CTkToplevel(self)
        self.fenetre_avoir.title("Création / Modification d'Avoir")
        self.fenetre_avoir.geometry("1200x600")
        Theme.apply_toplevel(self.fenetre_avoir)
        self.fenetre_avoir.grab_set()
        PageAvoir(self.fenetre_avoir, id_user_connecte=self.id_user_connecte).pack(
            fill="both", expand=True, padx=10, pady=10)
        self.fenetre_avoir.protocol("WM_DELETE_WINDOW", self._fermer_fenetre_avoir)

    def _fermer_fenetre_avoir(self):
        """Ferme et nettoie la référence vers la fenêtre Avoir."""
        self.fenetre_avoir.grab_release()
        self.fenetre_avoir.destroy()
        if hasattr(self, 'fenetre_avoir'): del self.fenetre_avoir

    def _ouvrir_page_proforma(self):
        """Instancie PageCommandeCli (Proforma) dans un CTkToplevel modal."""
        if hasattr(self, 'fenetre_proforma') and self.fenetre_proforma.winfo_exists():
            self.fenetre_proforma.focus(); return
        self.fenetre_proforma = ctk.CTkToplevel(self)
        self.fenetre_proforma.title("Création / Modification de Proforma")
        self.fenetre_proforma.geometry("1200x600")
        Theme.apply_toplevel(self.fenetre_proforma)
        self.fenetre_proforma.grab_set()
        PageCommandeCli(self.fenetre_proforma, iduser=self.id_user_connecte).pack(
            fill="both", expand=True, padx=10, pady=10)
        self.fenetre_proforma.protocol("WM_DELETE_WINDOW", self._fermer_fenetre_proforma)

    def _fermer_fenetre_proforma(self):
        """Ferme et nettoie la référence vers la fenêtre Proforma."""
        self.fenetre_proforma.grab_release()
        self.fenetre_proforma.destroy()
        if hasattr(self, 'fenetre_proforma'): del self.fenetre_proforma

    def ouvrir_suivi_depot(self):
        """Ouvre la fenêtre de suivi du stock par dépôt (import flexible)."""
        try:
            try:
                from pages.page_SuiviStockDepot import PageSuiviStockDepot
            except ImportError:
                from page_SuiviStockDepot import PageSuiviStockDepot
            if hasattr(self, 'fenetre_suivi') and self.fenetre_suivi.winfo_exists():
                self.fenetre_suivi.lift(); self.fenetre_suivi.focus_force(); return
            self.fenetre_suivi = ctk.CTkToplevel(self)
            self.fenetre_suivi.title("Suivi Stock par Dépôt")
            self.fenetre_suivi.geometry("1100x650")
            Theme.apply_toplevel(self.fenetre_suivi)
            self.fenetre_suivi.after(200, self.fenetre_suivi.focus_force)
            PageSuiviStockDepot(self.fenetre_suivi, iduser=self.id_user_connecte).pack(
                fill="both", expand=True, padx=10, pady=10)
        except Exception as e:
            messagebox.showerror("Erreur d'ouverture", str(e))

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 16 — TRI DU TREEVIEW (utilitaire partagé)
    # ──────────────────────────────────────────────────────────────────────────

    def sort_tree(self, tree, col: str):
        """
        Trie le Treeview par colonne avec alternance asc/desc.
        Tri numérique pour 'Montant Total', tri date pour 'Date', tri alpha sinon.
        """
        children = tree.get_children('')
        vals = [(tree.set(k, col), k) for k in children]
        reverse = getattr(tree, f"_sort_rev_{col}", False)

        try:
            if col == "Montant Total":
                def key(x):
                    t = x[0].replace(" ", "").replace(".", "").replace(",", ".")
                    return float(t) if t else 0.0
            elif col == "Date":
                from datetime import datetime as _dt
                def key(x):
                    try: return _dt.strptime(x[0], "%d/%m/%Y")
                    except: return _dt.min
            else:
                def key(x): return x[0] or ""
            vals.sort(key=key, reverse=reverse)
        except Exception:
            vals.sort(reverse=reverse)

        for i, (_, item) in enumerate(vals):
            tree.move(item, '', i)
        setattr(tree, f"_sort_rev_{col}", not reverse)

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 17 — CHARGEMENT FACTURE POUR MODIFICATION (héritage)
    # ──────────────────────────────────────────────────────────────────────────

    def charger_vente_modification(self, idvente: int):
        """Charge une facture existante dans le formulaire pour modification."""
        self.nouveau_facture()
        conn = self._connect_db()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT v.id, v.refvente, v.dateregistre, v.description, c.nomcli, v.idclient
                FROM tb_vente v LEFT JOIN tb_client c ON v.idclient=c.idclient
                WHERE v.id=%s
            """, (idvente,))
            row = cur.fetchone()
            if not row: messagebox.showerror("Erreur", "Facture introuvable."); return
            _id, ref, date_r, desc, nomcli, idclient = row

            cur.execute("""
                SELECT vd.idmag, m.designationmag, vd.idarticle, u.codearticle,
                       a.designation, vd.idunite, u.designationunite,
                       vd.qtvente, vd.prixunit, COALESCE(vd.remise,0)
                FROM tb_ventedetail vd
                INNER JOIN tb_article a ON vd.idarticle=a.idarticle
                INNER JOIN tb_unite u ON vd.idunite=u.idunite
                INNER JOIN tb_magasin m ON vd.idmag=m.idmag
                WHERE vd.idvente=%s
            """, (idvente,))
            details = cur.fetchall()

            self.idvente_charge    = idvente
            self.mode_modification = True

            self.entry_ref_vente.configure(state="normal")
            self.entry_ref_vente.delete(0, "end"); self.entry_ref_vente.insert(0, ref)
            self.entry_ref_vente.configure(state="readonly")
            self.entry_date_vente.delete(0, "end")
            self.entry_date_vente.insert(0, date_r.strftime("%d/%m/%Y"))
            self.entry_designation.delete(0, "end")
            self.entry_designation.insert(0, desc or "")
            self.entry_client.delete(0, "end")
            self.entry_client.insert(0, nomcli or "Client Divers")
            if nomcli: self.client_map[nomcli] = idclient

            self.detail_vente = []
            for r in details:
                idmag_d, desmag, ia, code, desig_a, iu, desiu, qtv, pu, rem = r
                self.detail_vente.append({
                    'idmag': idmag_d, 'designationmag': desmag,
                    'idarticle': ia, 'code_article': code, 'nom_article': desig_a,
                    'idunite': iu, 'nom_unite': desiu,
                    'qtvente': float(qtv), 'prixunit': float(pu), 'remise': float(rem),
                })
            self.charger_details_treeview()
            self.btn_enregistrer.configure(
                text="🔄 Modifier la Facture",
                fg_color=Colors.WARNING, hover_color=Colors.WARNING_LIGHT_C,
                state="normal",
            )
            messagebox.showinfo("Chargement OK",
                                f"Facture N° {ref} chargée pour modification.")
        except Exception as e:
            messagebox.showerror("Erreur", str(e)); traceback.print_exc(); self.nouveau_facture()
        finally:
            cur.close(); conn.close()


# ==============================================================================
# POINT D'ENTRÉE — TEST STANDALONE
# ==============================================================================
if __name__ == "__main__":
    USER_ID = 1
    try:
        app = ctk.CTk()
        app.title("iJeery — Gestion des Ventes")
        app.geometry("1280x720")
        Theme.apply(app)

        page = PageVenteParMsin(app, id_user_connecte=USER_ID)
        page.pack(fill="both", expand=True)

        app.mainloop()
    except Exception as e:
        print(f"Erreur critique : {e}")
        traceback.print_exc()