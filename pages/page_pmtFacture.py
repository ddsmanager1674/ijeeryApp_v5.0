# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              iJeery — pages/page_pmtfacture.py                              ║
║              Paiement de Facture Client                                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  REFONTE UI — Mars 2026                                                      ║
║  ─ Seules _construire_interface() et demander_autorisation() sont modifiées  ║
║  ─ Polices : Roboto 12px via Fonts.*                                         ║
║  ─ Couleurs : Colors.*                                                       ║
║  ─ Layout grid responsive (CTkToplevel 620 × 540)                           ║
║  ─ TOUTE LA LOGIQUE MÉTIER EST STRICTEMENT INCHANGÉE                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import customtkinter as ctk
from tkinter import messagebox, simpledialog, ttk
import psycopg2
import json
from datetime import date, datetime, timedelta
import traceback
import tempfile
import os
import subprocess
from tkcalendar import DateEntry
from resource_utils import get_config_path, safe_file_read
from settings_utils import is_global_print_enabled, open_file_if_enabled

from app_theme import Colors, Fonts
from log_utils import AppLogger

# ── ReportLab ────────────────────────────────────────────────────────────────
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5, landscape
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT

try:
    from num2words import num2words
except ImportError:
    num2words = None


# ── Helper UI (module-level, ne dépend d'aucune instance) ────────────────────

def _mk_info_bloc(parent, col: int, label: str, value: str,
                  val_color: str = "#2C3E50", val_size: int = 12):
    """Bloc label + valeur empilés, utilisé dans la card infos horizontale."""
    ctk.CTkLabel(
        parent, text=label,
        font=("Roboto", 10), text_color="#5D6D7E", anchor="center",
    ).grid(row=0, column=col, padx=14, pady=(10, 1), sticky="ew")
    ctk.CTkLabel(
        parent, text=value,
        font=("Roboto", val_size, "bold"), text_color=val_color, anchor="center",
    ).grid(row=1, column=col, padx=14, pady=(1, 10), sticky="ew")


# ══════════════════════════════════════════════════════════════════════════════

class PagePmtFacture(ctk.CTkToplevel):
    """
    Fenêtre de paiement de facture client.

    Layout de _construire_interface() :
    ┌────────────────────────────────────────────────────────────┐
    │ Titre "GESTION DU PAIEMENT"                               │  hdr MIDNIGHT
    │ ┌── Card Infos Facture ──────────────────────────────────┐ │
    │ │ Facture N° | Client | Montant Total                    │ │  BG_CARD
    │ └────────────────────────────────────────────────────────┘ │
    │ ┌── Card Saisie ─────────────────────────────────────────┐ │
    │ │ Montant Reçu      [________________]                   │ │
    │ │ Mode de paiement  [OptionMenu]  Échéance [DateEntry]   │ │  BG_CARD
    │ │ Description       [___________________________________] │ │
    │ └────────────────────────────────────────────────────────┘ │
    │ ┌── Barre actions ───────────────────────────────────────┐ │
    │ │              [✅ Valider & Imprimer]  [❌ Annuler]      │ │  BG_PAGE
    │ └────────────────────────────────────────────────────────┘ │
    └────────────────────────────────────────────────────────────┘
    """

    def __init__(self, master, paiement_data, iduser=None):
        super().__init__(master)

        # ── Données ───────────────────────────────────────────────────────────
        self.data               = paiement_data
        self.id_facture         = self.data.get('id_facture')
        self.refvente           = self.data.get('refvente', 'N/A')
        self.montant_total_str  = self.data.get('montant_total', '0,00')
        self.client             = self.data.get('client', 'Client Inconnu')
        self.iduser             = iduser if iduser is not None else 1
        self.session_data       = getattr(master, "session_data", None) or {"user_id": self.iduser}
        self._logger            = AppLogger(session_data=self.session_data, fallback_user_id=self.iduser)

        try:
            montant_nettoyé         = str(self.montant_total_str).replace(' ', '').replace(',', '.')
            self.montant_total_float = float(montant_nettoyé)
        except ValueError:
            self.montant_total_float = 0.0

        # ── Config fenetre ────────────────────────────────────────────────────
        self.title(f"Paiement — {self.refvente}")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_PAGE)

        # ── Centrage immediat SANS update_idletasks (evite le freeze) ─────────
        w, h = 600, 470
        sw   = self.winfo_screenwidth()
        sh   = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        # ── Masquer pendant la construction, puis reveler d'un coup ───────────
        self.withdraw()

        # ── Flags anti double-clic ─────────────────────────────────────────
        self._processing_payment  = False
        self._payment_finalized   = False
        self._success_popup_shown = False

        # ── Pre-charger les modes de paiement avant de construire l'UI ────────
        # => 1 seule connexion DB au lieu de 1 connexion bloquante mid-UI
        self._modes_cache = self._charger_modes_cache()

        # ── Construire l'UI (utilise _modes_cache, zero requete DB pendant UI) -
        self._construire_interface()

        # ── Reveler la fenetre complete d'un seul coup + grab ─────────────────
        self.deiconify()
        self.grab_set()
        self.focus_set()
        self.bind("<Return>", self._on_valider_enter)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION UI — seule partie modifiée
    # ══════════════════════════════════════════════════════════════════════════

    def _construire_interface(self):
        """
        Interface paiement — layout léger 3 rows :
          Row 0 — Bandeau titre MIDNIGHT (compact h=46)
          Row 1 — Corps : card infos horizontale + card saisie (weight=1)
          Row 2 — Barre actions centrée
        """
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Row 0 — Bandeau titre ─────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT, corner_radius=0, height=46)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr,
            text="💳  PAIEMENT FACTURE",
            font=Fonts.title(15),
            text_color=Colors.TEXT_ON_DARK,
            anchor="w",
        ).grid(row=0, column=0, padx=16, sticky="w")

        ctk.CTkLabel(
            hdr,
            text=self.refvente,
            font=Fonts.bold(13),
            text_color=Colors.TEXT_ON_DARK_DIM,
            anchor="e",
        ).grid(row=0, column=1, padx=16, sticky="e")

        # ── Row 1 — Corps ─────────────────────────────────────────────────────
        body = ctk.CTkFrame(self, fg_color=Colors.BG_PAGE, corner_radius=0)
        body.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)

        # ·· Card Infos — bandeau horizontal compact ···························
        card_info = ctk.CTkFrame(body, fg_color=Colors.BG_CARD, corner_radius=8)
        card_info.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 6))
        # 3 blocs info côte à côte, élastiques
        for c in range(3):
            card_info.grid_columnconfigure(c, weight=1)

        _mk_info_bloc(card_info, col=0,
                      label="Facture N°", value=self.refvente,
                      val_color=Colors.TEXT_PRIMARY)
        _mk_info_bloc(card_info, col=1,
                      label="Client", value=self.client,
                      val_color=Colors.TEXT_PRIMARY)
        _mk_info_bloc(card_info, col=2,
                      label="Solde à payer",
                      value=f"{self.montant_total_str} Ar",
                      val_color=Colors.SUCCESS_DARK, val_size=14)

        # ·· Card Saisie ·······················································
        card_saisie = ctk.CTkFrame(body, fg_color=Colors.BG_CARD, corner_radius=8)
        card_saisie.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 6))
        card_saisie.grid_columnconfigure(1, weight=1)
        card_saisie.grid_columnconfigure(3, weight=1)

        _lbl = dict(font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY, anchor="w")
        _ent = dict(
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            height=32, corner_radius=6, font=Fonts.input(12),
        )

        # Ligne 0 — Montant reçu
        ctk.CTkLabel(card_saisie, text="Montant Reçu (Ar)", **_lbl).grid(
            row=0, column=0, padx=(14, 6), pady=(14, 2), sticky="w")
        self.entry_montant = ctk.CTkEntry(card_saisie, **_ent)
        self.entry_montant.grid(
            row=0, column=1, columnspan=3, padx=(0, 14), pady=(14, 2), sticky="ew")
        self.entry_montant.insert(0, self.montant_total_str)

        # Ligne 1 — Mode + Échéance
        ctk.CTkLabel(card_saisie, text="Mode de paiement", **_lbl).grid(
            row=1, column=0, padx=(14, 6), pady=(8, 2), sticky="w")

        modes = getattr(self, '_modes_cache', None) or self.charger_modes_paiement()
        self.option_mode_pmt = ctk.CTkOptionMenu(
            card_saisie,
            values=modes,
            width=150, height=32,
            font=Fonts.input(12),
            fg_color=Colors.BG_INPUT,
            button_color=Colors.MIDNIGHT,
            button_hover_color=Colors.MIDNIGHT_LIGHT,
            dropdown_fg_color=Colors.BG_CARD,
            text_color=Colors.TEXT_PRIMARY,
            command=self._verifier_mode_credit,
        )
        self.option_mode_pmt.grid(row=1, column=1, padx=(0, 8), pady=(8, 2), sticky="w")

        ctk.CTkLabel(card_saisie, text="Échéance", **_lbl).grid(
            row=1, column=2, padx=(4, 6), pady=(8, 2), sticky="w")

        self.cal_echeance = DateEntry(
            card_saisie,
            width=12,
            background=Colors.MIDNIGHT,
            foreground='white',
            borderwidth=1,
            locale='fr_FR',
            date_pattern='dd/mm/yyyy',
            font=('Roboto', 10),
        )
        self.cal_echeance.grid(row=1, column=3, padx=(0, 14), pady=(8, 2), sticky="w")
        self.cal_echeance.set_date(date.today() + timedelta(days=30))

        # Ligne 2 — Description
        ctk.CTkLabel(card_saisie, text="Observation", **_lbl).grid(
            row=2, column=0, padx=(14, 6), pady=(8, 14), sticky="w")
        self.entry_description_credit = ctk.CTkEntry(
            card_saisie, **_ent,
            placeholder_text="Détails du paiement…",
        )
        self.entry_description_credit.grid(
            row=2, column=1, columnspan=3, padx=(0, 14), pady=(8, 4), sticky="ew")

        # Lien transparent : aperçu de la vente en cours
        ctk.CTkButton(
            card_saisie,
            text="👁  Voir détails de vente",
            font=ctk.CTkFont(family="Roboto", size=11, weight="bold", underline=True),
            fg_color="transparent",
            hover_color=Colors.BG_INPUT,
            text_color=Colors.PRIMARY,
            corner_radius=6,
            height=26,
            command=self._ouvrir_apercu_vente,
        ).grid(row=3, column=1, columnspan=3, padx=(0, 14), pady=(0, 12), sticky="w")

        # ── BoolVar (requis par la logique métier) ────────────────────────────
        self.var_use_description = ctk.BooleanVar(value=True)

        # État initial calendrier
        self._verifier_mode_credit(self.option_mode_pmt.get())

        # ── Row 2 — Barre actions centrée ─────────────────────────────────────
        bar = ctk.CTkFrame(self, fg_color=Colors.BG_PAGE, corner_radius=0)
        bar.grid(row=2, column=0, sticky="ew", padx=0, pady=(2, 12))
        bar.grid_columnconfigure(0, weight=1)
        bar.grid_columnconfigure(3, weight=1)

        self.btn_valider = ctk.CTkButton(
            bar,
            text="✅  Valider & Imprimer",
            font=Fonts.bold(12),
            fg_color=Colors.SUCCESS_DARK, hover_color=Colors.INFO_DARK,
            text_color=Colors.TEXT_ON_DARK,
            height=38, corner_radius=8, width=180,
            command=self._on_valider_click,
        )
        self.btn_valider.grid(row=0, column=1, padx=(0, 8))

        ctk.CTkButton(
            bar,
            text="✖  Annuler",
            font=Fonts.bold(12),
            fg_color=Colors.DANGER, hover_color=Colors.DANGER_DARK,
            text_color=Colors.TEXT_ON_DARK,
            height=38, corner_radius=8, width=120,
            command=self.destroy,
        ).grid(row=0, column=2, padx=(0, 0))

    def _charger_apercu_vente_data(self):
        """Récupère les infos vente + détails pour l'aperçu (lecture seule)."""
        conn = self.connect_db()
        if not conn:
            return None, []
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT
                    v.refvente,
                    COALESCE(c.nomcli, 'Client Inconnu') AS nomclient,
                    COALESCE(v.totmtvente, 0) AS totmtvente,
                    v.dateregistre,
                    COALESCE(m.designationmag, 'N/A') AS nommagasin
                FROM tb_vente v
                LEFT JOIN tb_client c ON c.idclient = v.idclient
                LEFT JOIN tb_magasin m ON m.idmag = v.idmag
                WHERE v.refvente = %s
                LIMIT 1
            """, (self.refvente,))
            vente_info = cur.fetchone()

            cur.execute("""
                SELECT
                    vd.qtvente,
                    COALESCE(a.designation, 'Article') AS designation_article,
                    COALESCE(u.designationunite, 'Unité') AS designation_unite,
                    COALESCE(vd.prixunit, 0) AS prixunit,
                    COALESCE(vd.remise, 0) AS remise,
                    (COALESCE(vd.qtvente, 0) * (COALESCE(vd.prixunit, 0) - COALESCE(vd.remise, 0))) AS montant
                FROM tb_ventedetail vd
                INNER JOIN tb_vente v ON v.id = vd.idvente
                LEFT JOIN tb_article a ON a.idarticle = vd.idarticle
                LEFT JOIN tb_unite u ON u.idunite = vd.idunite
                WHERE v.refvente = %s
                  AND COALESCE(vd.deleted, 0) = 0
                ORDER BY a.designation ASC, vd.id ASC
            """, (self.refvente,))
            details = cur.fetchall()
            return vente_info, details
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger les détails de vente : {e}")
            return None, []
        finally:
            try:
                cur.close()
            except Exception:
                pass
            conn.close()

    def _ouvrir_apercu_vente(self):
        """Fenêtre d'aperçu: infos facture + tableau détails (lecture seule)."""
        vente_info, details = self._charger_apercu_vente_data()
        if not vente_info:
            messagebox.showwarning("Attention", "Aucune information de vente trouvée.")
            return

        win = ctk.CTkToplevel(self)
        win.title(f"Aperçu Vente — {self.refvente}")
        win.resizable(False, False)
        win.configure(fg_color=Colors.BG_PAGE)
        w, h = 900, 520
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        win.transient(self)
        win.grab_set()

        # Header
        hdr = ctk.CTkFrame(win, fg_color=Colors.MIDNIGHT, corner_radius=0, height=42)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(
            hdr, text="👁  Aperçu de la vente",
            font=Fonts.bold(14), text_color=Colors.TEXT_ON_DARK
        ).pack(side="left", padx=12, pady=8)

        # Infos vente
        info = ctk.CTkFrame(win, fg_color=Colors.BG_CARD, corner_radius=8)
        info.pack(fill="x", padx=12, pady=(10, 6))
        for c in range(5):
            info.grid_columnconfigure(c, weight=1)

        ref, nomclient, total, datereg, nommag = vente_info
        date_txt = datereg.strftime("%d/%m/%Y %H:%M:%S") if datereg else ""
        total_txt = self._formater_montant(float(total or 0))

        _mk_info_bloc(info, 0, "Ref Vente", str(ref or ""))
        _mk_info_bloc(info, 1, "Client", str(nomclient or ""))
        _mk_info_bloc(info, 2, "Total", f"{total_txt} Ar", val_color=Colors.SUCCESS_DARK)
        _mk_info_bloc(info, 3, "Date", date_txt)
        _mk_info_bloc(info, 4, "Magasin", str(nommag or ""))

        # Tableau détails
        tbl_wrap = ctk.CTkFrame(win, fg_color=Colors.BG_CARD, corner_radius=8)
        tbl_wrap.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "Apercu.Treeview",
            background=Colors.BG_CARD,
            foreground=Colors.TEXT_PRIMARY,
            fieldbackground=Colors.BG_CARD,
            rowheight=23,
            font=("Roboto", 10),
            borderwidth=0
        )
        style.configure(
            "Apercu.Treeview.Heading",
            background=Colors.BG_HEADER,
            foreground="#FFFFFF",
            font=("Roboto", 10, "bold"),
            relief="flat"
        )

        cols = ("Qté", "Article", "Unité", "PU", "Remise", "Montant")
        tree = ttk.Treeview(tbl_wrap, columns=cols, show="headings", style="Apercu.Treeview", height=12)
        tree.tag_configure("even", background=Colors.BG_CARD)
        tree.tag_configure("odd", background="#F0F4F8")

        cfg = {
            "Qté": (70, "e"),
            "Article": (280, "w"),
            "Unité": (110, "w"),
            "PU": (110, "e"),
            "Remise": (100, "e"),
            "Montant": (120, "e"),
        }
        for col in cols:
            wcol, anc = cfg[col]
            tree.heading(col, text=col)
            tree.column(col, width=wcol, anchor=anc)

        sy = ctk.CTkScrollbar(tbl_wrap, orientation="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sy.set)
        tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        sy.pack(side="right", fill="y", padx=(0, 8), pady=8)

        for i, r in enumerate(details):
            qte, art, unite, pu, remise, montant = r
            tree.insert(
                "", "end",
                values=(
                    str(qte or ""),
                    str(art or ""),
                    str(unite or ""),
                    self._formater_montant(float(pu or 0)),
                    self._formater_montant(float(remise or 0)),
                    self._formater_montant(float(montant or 0)),
                ),
                tags=("even" if i % 2 == 0 else "odd",)
            )

        # Footer action
        foot = ctk.CTkFrame(win, fg_color=Colors.BG_PAGE, corner_radius=0)
        foot.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkButton(
            foot, text="Fermer",
            font=Fonts.bold(11),
            fg_color=Colors.DANGER, hover_color=Colors.DANGER_DARK,
            text_color=Colors.TEXT_ON_DARK,
            width=120, height=34, corner_radius=8,
            command=win.destroy
        ).pack(side="right")

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION UI — Dialogue Autorisation (refonte uniquement)
    # ══════════════════════════════════════════════════════════════════════════

    def demander_autorisation(self) -> bool:
        """
        Affiche une fenêtre modale pour saisir le code d'autorisation crédit.
        Retourne True si le code est valide, False sinon.
        *** LOGIQUE DE VÉRIFICATION INCHANGÉE ***
        """
        dialog = ctk.CTkToplevel(self)
        dialog.title("Autorisation Requise")
        dialog.resizable(False, False)
        dialog.configure(fg_color=Colors.BG_PAGE)
        dialog.transient(self)
        dialog.grab_set()

        # ── Centrage direct (sans update_idletasks) ────────────────────────────
        dw, dh = 420, 240
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
        dialog.geometry(f"{dw}x{dh}+{(sw-dw)//2}+{(sh-dh)//2}")

        autorisation_valide = [False]

        # ── Bandeau alerte ────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(dialog, fg_color=Colors.DANGER, corner_radius=0, height=46)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(
            hdr,
            text="⚠️  AUTORISATION REQUISE",
            font=Fonts.bold(14),
            text_color=Colors.TEXT_ON_DARK,
        ).pack(expand=True)

        # ── Corps ─────────────────────────────────────────────────────────────
        body = ctk.CTkFrame(dialog, fg_color=Colors.BG_CARD, corner_radius=0)
        body.pack(fill="both", expand=True, padx=12, pady=(10, 0))
        body.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            body,
            text="Le paiement à crédit nécessite un code d'autorisation.",
            font=Fonts.body(11),
            text_color=Colors.TEXT_SECONDARY,
            wraplength=360,
            justify="center",
        ).grid(row=0, column=0, padx=14, pady=(12, 8))

        ctk.CTkLabel(
            body,
            text="Code d'autorisation",
            font=Fonts.label(11),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
        ).grid(row=1, column=0, padx=14, pady=(0, 2), sticky="w")

        entry_code = ctk.CTkEntry(
            body,
            show="*",
            font=Fonts.input(13),
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            height=36, corner_radius=6,
        )
        entry_code.grid(row=2, column=0, padx=14, pady=(0, 12), sticky="ew")
        entry_code.focus_set()

        # ── Boutons ───────────────────────────────────────────────────────────
        btn_bar = ctk.CTkFrame(dialog, fg_color=Colors.BG_PAGE, corner_radius=0)
        btn_bar.pack(fill="x", padx=12, pady=(0, 12))

        def valider_code():
            code_saisi = entry_code.get().strip()
            if not code_saisi:
                messagebox.showwarning(
                    "Attention", "Veuillez saisir un code d'autorisation.",
                    parent=dialog,
                )
                return
            # *** vérification inchangée ***
            if self.verifier_code_autorisation(code_saisi):
                autorisation_valide[0] = True
                dialog.destroy()
            else:
                messagebox.showerror(
                    "Code Invalide",
                    "Le code d'autorisation est incorrect ou inactif.\nVeuillez réessayer.",
                    parent=dialog,
                )
                entry_code.delete(0, "end")
                entry_code.focus_set()

        def annuler():
            autorisation_valide[0] = False
            dialog.destroy()

        ctk.CTkButton(
            btn_bar,
            text="✅  Valider",
            font=Fonts.bold(12),
            fg_color=Colors.SUCCESS_DARK, hover_color=Colors.INFO_DARK,
            height=36, corner_radius=6, width=140,
            command=valider_code,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_bar,
            text="❌  Annuler",
            font=Fonts.bold(12),
            fg_color=Colors.DANGER, hover_color=Colors.DANGER_DARK,
            height=36, corner_radius=6, width=140,
            command=annuler,
        ).pack(side="left")

        entry_code.bind('<Return>', lambda e: valider_code())
        dialog.wait_window()
        return autorisation_valide[0]

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION BASE DE DONNÉES — STRICTEMENT INCHANGÉE
    # ══════════════════════════════════════════════════════════════════════════

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
            with open(get_config_path('settings.json'), 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Impossible de charger settings.json : {e}")
            return {}

    def _charger_modes_cache(self) -> list:
        """
        Charge les modes de paiement UNE SEULE FOIS avant la construction UI.
        Résultat mis en cache dans self._modes_cache.
        self.liste_modes est aussi rempli ici pour la logique métier.
        """
        conn = self.connect_db()
        if not conn:
            self.liste_modes = {"Especes": 1}
            return ["Especes"]
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT idmode, modedepaiement FROM tb_modepaiement")
            rows = cursor.fetchall()
            self.liste_modes = {row[1]: row[0] for row in rows}
            return list(self.liste_modes.keys()) or ["Especes"]
        except Exception:
            self.liste_modes = {"Especes": 1}
            return ["Especes"]
        finally:
            conn.close()

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

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION CALCUL STOCK — STRICTEMENT INCHANGÉE
    # ══════════════════════════════════════════════════════════════════════════

    def calculer_stock_article_reel(self, idarticle, idunite_cible, idmag, cursor=None):
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
        conn = None
        local_cursor = cursor
        if local_cursor is None:
            conn = self.connect_db()
            if not conn:
                return 0.0
            local_cursor = conn.cursor()

        try:
            query = """
            WITH unite_hierarchie AS (
                SELECT idarticle, idunite, niveau, qtunite, designationunite
                FROM tb_unite
                WHERE idarticle = %s AND COALESCE(deleted, 0) = 0
            ),
            unite_coeff AS (
                SELECT
                    idarticle,
                    idunite,
                    niveau,
                    qtunite,
                    designationunite,
                    exp(sum(ln(NULLIF(CASE WHEN qtunite > 0 THEN qtunite ELSE 1 END, 0)))
                        OVER (PARTITION BY idarticle ORDER BY niveau ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                    ) as coeff_hierarchique
                FROM unite_hierarchie
            ),
            base_unite_par_article AS (
                SELECT DISTINCT ON (idarticle) idarticle, idunite
                FROM tb_unite
                WHERE idarticle = %s AND COALESCE(deleted, 0) = 0
                ORDER BY idarticle, qtunite ASC, idunite ASC
            ),
            rec AS (
                SELECT lf.idarticle, lf.idunite, lf.idmag, SUM(lf.qtlivrefrs) AS quantite
                FROM tb_livraisonfrs lf
                WHERE lf.idarticle = %s AND lf.idmag = %s AND lf.deleted = 0
                GROUP BY lf.idarticle, lf.idunite, lf.idmag
            ),
            ven AS (
                SELECT vd.idarticle, vd.idunite, v.idmag, SUM(vd.qtvente) AS quantite
                FROM tb_ventedetail vd
                INNER JOIN tb_vente v ON vd.idvente = v.id AND v.deleted = 0 AND v.statut = 'VALIDEE'
                WHERE vd.idarticle = %s AND v.idmag = %s AND vd.deleted = 0
                GROUP BY vd.idarticle, vd.idunite, v.idmag
            ),
            sor AS (
                SELECT sd.idarticle, sd.idunite, sd.idmag, SUM(sd.qtsortie) AS quantite
                FROM tb_sortiedetail sd
                WHERE sd.idarticle = %s AND sd.idmag = %s
                GROUP BY sd.idarticle, sd.idunite, sd.idmag
            ),
            tin AS (
                SELECT t.idarticle, t.idunite, t.idmagentree AS idmag, SUM(t.qttransfert) AS quantite
                FROM tb_transfertdetail t
                WHERE t.idarticle = %s AND t.deleted = 0 AND t.idmagentree = %s
                GROUP BY t.idarticle, t.idunite, t.idmagentree
            ),
            tout AS (
                SELECT t.idarticle, t.idunite, t.idmagsortie AS idmag, SUM(t.qttransfert) AS quantite
                FROM tb_transfertdetail t
                WHERE t.idarticle = %s AND t.deleted = 0 AND t.idmagsortie = %s
                GROUP BY t.idarticle, t.idunite, t.idmagsortie
            ),
            inv AS (
                SELECT bu.idarticle, bu.idunite, i.idmag, SUM(i.qtinventaire) AS quantite
                FROM tb_inventaire i
                INNER JOIN tb_unite u ON i.codearticle = u.codearticle
                INNER JOIN base_unite_par_article bu ON bu.idarticle = u.idarticle AND bu.idunite = u.idunite
                WHERE u.idarticle = %s AND i.idmag = %s
                GROUP BY bu.idarticle, bu.idunite, i.idmag
            ),
            avo AS (
                SELECT ad.idarticle, ad.idunite, ad.idmag, SUM(ad.qtavoir) AS quantite
                FROM tb_avoir a
                INNER JOIN tb_avoirdetail ad ON a.id = ad.idavoir
                WHERE ad.idarticle = %s AND ad.idmag = %s AND a.deleted = 0 AND ad.deleted = 0
                GROUP BY ad.idarticle, ad.idunite, ad.idmag
            ),
            conso AS (
                SELECT ci.idarticle, ci.idunite, ci.idmag, SUM(ci.qtconsomme) AS quantite
                FROM tb_consommationinterne_details ci
                WHERE ci.idarticle = %s AND ci.idmag = %s
                GROUP BY ci.idarticle, ci.idunite, ci.idmag
            ),
            ech_in AS (
                SELECT dce.idarticle, dce.idunite, dce.idmagasin AS idmag, SUM(dce.quantite_entree) AS quantite
                FROM tb_detailchange_entree dce
                WHERE dce.idarticle = %s AND dce.idmagasin = %s
                GROUP BY dce.idarticle, dce.idunite, dce.idmagasin
            ),
            ech_out AS (
                SELECT dcs.idarticle, dcs.idunite, dcs.idmagasin AS idmag, SUM(dcs.quantite_sortie) AS quantite
                FROM tb_detailchange_sortie dcs
                WHERE dcs.idarticle = %s AND dcs.idmagasin = %s
                GROUP BY dcs.idarticle, dcs.idunite, dcs.idmagasin
            ),
            mouvements_agreges AS (
                SELECT idarticle, idunite, idmag, quantite, 'reception' AS type_mouvement FROM rec
                UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'vente' AS type_mouvement FROM ven
                UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'sortie' AS type_mouvement FROM sor
                UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'transfert_in' AS type_mouvement FROM tin
                UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'transfert_out' AS type_mouvement FROM tout
                UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'inventaire' AS type_mouvement FROM inv
                UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'avoir' AS type_mouvement FROM avo
                UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'consommation_interne' AS type_mouvement FROM conso
                UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'echange_entree' AS type_mouvement FROM ech_in
                UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'echange_sortie' AS type_mouvement FROM ech_out
            ),
            solde_base_par_mag AS (
                SELECT
                    ma.idarticle,
                    ma.idmag,
                    SUM(
                        CASE ma.type_mouvement
                            WHEN 'reception'            THEN  ma.quantite * COALESCE(uc.coeff_hierarchique, 1)
                            WHEN 'transfert_in'         THEN  ma.quantite * COALESCE(uc.coeff_hierarchique, 1)
                            WHEN 'inventaire'           THEN  ma.quantite * COALESCE(uc.coeff_hierarchique, 1)
                            WHEN 'avoir'                THEN  ma.quantite * COALESCE(uc.coeff_hierarchique, 1)
                            WHEN 'echange_entree'       THEN  ma.quantite * COALESCE(uc.coeff_hierarchique, 1)
                            WHEN 'vente'                THEN -ma.quantite * COALESCE(uc.coeff_hierarchique, 1)
                            WHEN 'sortie'               THEN -ma.quantite * COALESCE(uc.coeff_hierarchique, 1)
                            WHEN 'transfert_out'        THEN -ma.quantite * COALESCE(uc.coeff_hierarchique, 1)
                            WHEN 'consommation_interne' THEN -ma.quantite * COALESCE(uc.coeff_hierarchique, 1)
                            WHEN 'echange_sortie'       THEN -ma.quantite * COALESCE(uc.coeff_hierarchique, 1)
                            ELSE 0
                        END
                    ) as solde
                FROM mouvements_agreges ma
                LEFT JOIN unite_coeff uc ON uc.idarticle = ma.idarticle AND uc.idunite = ma.idunite
                GROUP BY ma.idarticle, ma.idmag
            )
            SELECT
                GREATEST(
                    COALESCE(sb.solde, 0) / NULLIF(COALESCE(uc.coeff_hierarchique, 1), 0),
                    0
                ) as stock_reel
            FROM tb_article a
            INNER JOIN tb_unite u ON a.idarticle = u.idarticle
            LEFT JOIN unite_coeff uc ON uc.idarticle = u.idarticle AND uc.idunite = u.idunite
            LEFT JOIN solde_base_par_mag sb ON sb.idarticle = u.idarticle AND sb.idmag = %s
            WHERE a.deleted = 0
              AND u.idarticle = %s
              AND u.idunite = %s
            LIMIT 1
            """

            params = [
                idarticle,
                idarticle,
                idarticle, idmag,      # rec
                idarticle, idmag,      # ven
                idarticle, idmag,      # sor
                idarticle, idmag,      # tin
                idarticle, idmag,      # tout
                idarticle, idmag,      # inv
                idarticle, idmag,      # avo
                idarticle, idmag,      # conso
                idarticle, idmag,      # ech_in
                idarticle, idmag,      # ech_out
                idmag,                 # solde magasin
                idarticle,             # article cible
                idunite_cible,         # unité cible
            ]
            local_cursor.execute(query, params)
            row = local_cursor.fetchone()
            return float(row[0] or 0.0)

        except Exception as e:
            print(f"❌ Erreur calcul stock consolidé : {e}")
            return 0.0
        finally:
            if conn is not None:
                try:
                    local_cursor.close()
                except Exception:
                    pass
                conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION LOGIQUE MÉTIER — STRICTEMENT INCHANGÉE
    # ══════════════════════════════════════════════════════════════════════════

    def _verifier_mode_credit(self, choix):
        """Active ou désactive le calendrier selon le mode choisi."""
        if choix.lower() == "crédit":
            self.cal_echeance.configure(state="normal")
        else:
            self.cal_echeance.configure(state="disabled")

    def verifier_code_autorisation(self, code_saisi: str) -> bool:
        """
        Vérifie si le code d'autorisation saisi est valide.
        *** LOGIQUE MÉTIER — NE PAS MODIFIER ***
        """
        conn = self.connect_db()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
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

    def _on_valider_click(self):
        """Wrapper pour empêcher les double-clicks rapides sur le bouton Valider."""
        if getattr(self, '_processing_payment', False) or getattr(self, '_payment_finalized', False):
            messagebox.showwarning("Attention", "Le paiement est déjà en cours de traitement...")
            return
        try:
            self._processing_payment = True
            try:
                self.btn_valider.configure(state="disabled")
            except Exception:
                pass
            self.valider_paiement()
        finally:
            try:
                if self.winfo_exists() and not getattr(self, '_payment_finalized', False):
                    self._processing_payment = False
                    try:
                        self.btn_valider.configure(state="normal")
                    except Exception:
                        pass
            except Exception:
                pass

    def _on_valider_enter(self, event=None):
        """Raccourci clavier Entrée -> même action que le bouton Valider."""
        self._on_valider_click()
        return "break"

    def valider_paiement(self):
        if self._payment_finalized:
            return

        montant_saisi_str = self.entry_montant.get().replace(' ', '').replace(',', '.')
        nom_mode_pmt = self.option_mode_pmt.get()
        
        # ✅ VÉRIFICATION DU MODE CRÉDIT - DEMANDE D'AUTORISATION
        if nom_mode_pmt.lower() == "crédit":
            if not self.demander_autorisation():
                messagebox.showwarning(
                    "Paiement Annulé", 
                    "Le paiement à crédit a été annulé car l'autorisation n'a pas été validée."
                )
                return
        
        date_echeance = None
        description_credit = ""
        description = ""
        if self.var_use_description.get():
            description = (self.entry_description_credit.get() or "").strip()

        if nom_mode_pmt.lower() == "crédit":
            date_echeance = self.cal_echeance.get_date()
            description_credit = f"Acceptation du crédit pour la facture {self.refvente} [CL: {self.client}] - Échéance: {date_echeance.strftime('%d/%m/%Y')}"

        if nom_mode_pmt.lower() == "crédit":
            observation_pmt = description_credit
            if description != "":
                observation_pmt = f"{description_credit} (Obs: {description})"
        else:
            observation_pmt = f"PMT {self.refvente} - {self.client}"
            if description != "":
                observation_pmt = f"PMT {self.refvente} - {self.client} (Obs: {description})"

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

            print(f"\n{'='*70}")
            print(f"🔍 ÉTAPE 1 : RÉCUPÉRATION FACTURE DE VENTE")
            print(f"{'='*70}")
            print(f"📌 Facture: {self.refvente}")
            print(f"💰 Client: {self.client}")
            print(f"💵 Montant à encaisser: {montant_saisi} Ar")
            print(f"🏪 Mode de paiement: {nom_mode_pmt}")

            cursor.execute("SELECT nomsociete, adressesociete, contactsociete, villesociete FROM tb_infosociete LIMIT 1")
            info_soc = cursor.fetchone()
            
            cursor.execute("SELECT idclient, idmag, statut FROM tb_vente WHERE refvente = %s", (self.refvente,))
            res_vente = cursor.fetchone()
            idclient = res_vente[0] if res_vente else None
            idmag_facture = res_vente[1] if res_vente else None
            statut_vente = res_vente[2] if res_vente else None
            print(f"✓ ID Client: {idclient}")
            print(f"✓ Magasin: {idmag_facture}")
            print(f"✓ Statut facture: {statut_vente}")

            cursor.execute("SELECT statut FROM tb_vente WHERE refvente = %s", (self.refvente,))
            statut_row = cursor.fetchone()
            statut_vente_actuel = statut_row[0] if statut_row else None

            if statut_vente_actuel is not None and statut_vente_actuel != 'EN_ATTENTE':
                messagebox.showwarning(
                    "Paiement annulé",
                    f"Ce facture n'est plus en attente, il est déja {statut_vente_actuel}"
                )
                return
            
            cursor.execute(
                "SELECT nomcli, COALESCE(adressecli, ''), COALESCE(contactcli, '') "
                "FROM tb_client WHERE nomcli = %s",
                (self.client,)
            )
            res_client = cursor.fetchone()
            client = res_client[0] if res_client else "Inconnu"
            client_adresse = res_client[1] if res_client else ""
            client_contact = res_client[2] if res_client else ""
            
            cursor.execute("SELECT username FROM tb_users WHERE iduser = %s", (self.iduser,))
            res_user = cursor.fetchone()
            username = res_user[0] if res_user else "Inconnu"

            magasin_nom = f"Magasin {idmag_facture}" if idmag_facture else "N/A"
            if idmag_facture:
                cursor.execute("SELECT designationmag FROM tb_magasin WHERE idmag = %s", (idmag_facture,))
                res_mag = cursor.fetchone()
                if res_mag and res_mag[0]:
                    magasin_nom = res_mag[0]

            print(f"\n{'='*70}")
            print(f"📦 ÉTAPE 2 : RÉCUPÉRATION DES ARTICLES VENDUS")
            print(f"{'='*70}")

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

            print(f"\n{'='*70}")
            print("🔎 ÉTAPE 3 : CONTRÔLE DISPONIBILITÉ STOCK")
            print(f"{'='*70}")
            stocks_initiaux = {}
            stocks_reserves = {}
            for det_idx, det in enumerate(articles, 1):
                idarticle = det[0]
                idunite = det[1]
                idmag = det[2]
                codearticle = det[3] or ''
                designation = det[4]
                qtvente = float(det[6] or 0)
                cle_stock = (idarticle, idunite, idmag)

                if cle_stock not in stocks_initiaux:
                    stock_calcule = self.calculer_stock_article_reel(idarticle, idunite, idmag, cursor=cursor)
                    stocks_initiaux[cle_stock] = stock_calcule
                    stocks_reserves[cle_stock] = stock_calcule

                stock_reel = round(stocks_reserves[cle_stock], 2)

                print(
                    f"  Article #{det_idx} - {designation}: "
                    f"demandé={qtvente}, stock_reel={stock_reel}"
                )

                if qtvente > stock_reel:
                    messagebox.showwarning(
                        "Stock insuffisant",
                        (
                            f"Stock insuffisant pour l'article {designation} "
                            f"({codearticle or idarticle}).\n"
                            f"Demandé: {qtvente}\nDisponible: {stock_reel}"
                        )
                    )
                    return
                stocks_reserves[cle_stock] = stock_reel - qtvente

            today = datetime.now().date()
            cursor.execute("""
                SELECT COUNT(*) FROM tb_pmtfacture 
                WHERE refvente = %s 
                AND mtpaye = %s 
                AND DATE(datepmt) = %s
            """, (self.refvente, montant_saisi, today))
            doublon_count = cursor.fetchone()[0]
            
            if doublon_count > 0:
                messagebox.showwarning(
                    "Paiement Dupliqué",
                    f"⚠️ Un paiement identique existe déjà pour cette facture aujourd'hui:\n"
                    f"Facture: {self.refvente}\n"
                    f"Montant: {montant_saisi} Ar\n"
                    f"Date: {today}\n\n"
                    f"Opération annulée pour éviter un doublon."
                )
                self._payment_finalized = True
                return
            
            cursor.execute("SELECT COALESCE(MAX(id),0)+1 FROM tb_pmtfacture")
            next_id = cursor.fetchone()[0]
            refpmt = f"{datetime.now().year}-PMTC-{next_id:06d}"
            
            id_mode_selectionne = self.liste_modes.get(nom_mode_pmt, 1)

            query_pmt = """
                INSERT INTO tb_pmtfacture (
                    refvente, mtpaye, datepmt, idmode, iduser, observation, refpmt, dateecheance, idclient
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params_pmt = (
                self.refvente, montant_saisi, datetime.now(), 
                id_mode_selectionne, self.iduser, observation_pmt,
                refpmt, date_echeance, idclient,
            )
            cursor.execute(query_pmt, params_pmt)

            print(f"\n{'='*70}")
            print(f"💳 ÉTAPE 3 : ENREGISTREMENT PAIEMENT ET MISE À JOUR STOCK")
            print(f"{'='*70}")
            print(f"Paiement référencé: {refpmt}")

            try:
                query_update_vente = """
                    UPDATE tb_vente 
                    SET idmode = %s, statut = 'VALIDEE'
                    WHERE refvente = %s
                """
                cursor.execute(query_update_vente, (id_mode_selectionne, self.refvente))
                print(f"✓ Facture marquée comme VALIDÉE")

                print(f"\n{'='*70}")
                print(f"📦 ÉTAPE 4 : MISE À JOUR DU STOCK")
                print(f"{'='*70}")

                for det_idx, det in enumerate(articles, 1):
                    idarticle = det[0]
                    idunite = det[1]
                    idmag = det[2]
                    codearticle = det[3] or ''
                    designation = det[4]
                    qtvente = float(det[6] or 0)
                    cle_stock = (idarticle, idunite, idmag)

                    print(f"\n  🔄 Article #{det_idx}: {designation}")
                    print(f"     ID: {idarticle}, Code: '{codearticle}', Magasin: {idmag}, Qté vendue: {qtvente}")

                    ancien_stock = float(stocks_initiaux.get(cle_stock, 0.0))
                    print(f"     ✓ Stock RÉEL (consolidé): {ancien_stock}")
                    nouveau_stock = ancien_stock - qtvente
                    print(f"     📊 Calcul: {ancien_stock} - {qtvente} = {nouveau_stock}")

                    stocks_initiaux[cle_stock] = nouveau_stock

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

                conn.commit()
                print(f"\n{'='*70}")
                print(f"✅ VALIDATION RÉUSSIE - Tous les changements sont validés")
                print(f"{'='*70}\n")
                try:
                    self._logger.log(
                        action="Paiement facture client",
                        element=str(self.refvente),
                        details=(
                            f"Paiement ref: {refpmt} pour facture {self.refvente}, "
                            f"client: {self.client}, mode: {nom_mode_pmt}, "
                            f"montant: {montant_saisi:.0f} Ar"
                        ),
                        value=f"{montant_saisi:.0f} Ar",
                    )
                except Exception:
                    pass

            except Exception as e:
                conn.rollback()
                print(f"\n❌ ERREUR lors de la mise à jour du stock: {e}\n")
                messagebox.showerror("Erreur Stock", f"Erreur lors de la mise à jour du stock : {e}")
                return

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

            settings = self.charger_settings()
            imprimer_ticket = settings.get('ClientAPayer_ImpressionTicket', 1)
            if not is_global_print_enabled(settings=settings, default=1):
                imprimer_ticket = 0
            
            print(f"📋 ClientAPayer_ImpressionTicket = {imprimer_ticket}")
            
            self._generer_ticket_pdf(
                info_soc, username, articles_pdf, montant_saisi, nom_mode_pmt,
                refpmt, date_echeance, imprimer_ticket, description
            )
            if nom_mode_pmt.lower() == "crédit":
                self._generer_etat_credit_pdf(
                    info_soc=info_soc,
                    username=username,
                    refpmt=refpmt,
                    magasin=magasin_nom,
                    ref_facture=self.refvente,
                    client_nom=client,
                    montant_paye=montant_saisi,
                    date_echeance=date_echeance,
                    client_adresse=client_adresse,
                    client_contact=client_contact,
                    description_credit=description_credit,
                    imprimer_ticket=imprimer_ticket
                )
            
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

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION PDF — STRICTEMENT INCHANGÉE
    # ══════════════════════════════════════════════════════════════════════════

    def _couper_texte(self, texte, largeur_max_chars):
        """Coupe le texte en lignes pour respecter la largeur maximale."""
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
                    lignes.append(mot[:largeur_max_chars])
                    ligne_courante = ""
        if ligne_courante:
            lignes.append(ligne_courante)
        return lignes if lignes else [""]

    def _formater_montant(self, montant):
        try:
            return f"{float(montant):,.2f} Ar".replace(',', ' ')
        except Exception:
            return f"{montant} Ar"

    def _generer_etat_credit_pdf(
        self, info_soc, username, refpmt, magasin, ref_facture, client_nom, montant_paye,
        date_echeance, client_adresse, client_contact, description_credit, imprimer_ticket=1
    ):
        """Génère l'état d'acceptation de crédit (A5 paysage)."""
        try:
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(
                temp_dir,
                f"Acceptation_Credit_{ref_facture}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )
            page_width, _ = landscape(A5)
            margin = 5 * mm
            page_width_usable = page_width - 2 * margin

            doc = SimpleDocTemplate(
                output_path,
                pagesize=landscape(A5),
                rightMargin=margin, leftMargin=margin,
                topMargin=margin, bottomMargin=margin,
            )
            elements = []
            styles   = getSampleStyleSheet()
            color_header = colors.HexColor("#034787")

            verse_title = Paragraph(
                "Ankino amin'ny Jehovah ny asanao dia ho lavorary izay kasainao. Ohabolana 16:3",
                ParagraphStyle("MainTitleCredit", parent=styles["Normal"],
                               fontSize=10, textColor=colors.black,
                               alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=3),
            )
            verse_table = Table([[verse_title]], colWidths=[page_width_usable])
            verse_table.setStyle(TableStyle([
                ("BOX",           (0, 0), (-1, -1), 1, colors.black),
                ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING",    (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            elements.append(verse_table)

            company_width = page_width_usable * 0.33
            right_width   = page_width_usable * 0.67 - 2 * mm
            title_width   = right_width * 0.55
            info_width    = right_width * 0.45
            header_height = 28 * mm

            nom_soc     = info_soc[0] if info_soc else "IJEERY"
            adr_soc     = info_soc[1] if info_soc and len(info_soc) > 1 else ""
            contact_soc = info_soc[2] if info_soc and len(info_soc) > 2 else ""
            ville_soc   = info_soc[3] if info_soc and len(info_soc) > 3 else ""
            echeance_str = date_echeance.strftime('%d/%m/%Y') if date_echeance else "N/A"

            company_details = Paragraph(
                f"<b>{nom_soc}</b><br/>"
                f"Adresse : {adr_soc}<br/>"
                f"Ville : {ville_soc}<br/>"
                f"Contact : {contact_soc}<br/>",
                ParagraphStyle("CompanyCredit", parent=styles["Normal"], fontSize=9, alignment=TA_LEFT, leading=12),
            )
            company_table = Table([[company_details]], colWidths=[company_width - 2 * mm], rowHeights=[header_height])
            company_table.setStyle(TableStyle([
                ("BOX",           (0, 0), (-1, -1), 1, colors.black),
                ("VALIGN",        (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING",    (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING",   (0, 0), (-1, -1), 6),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
            ]))

            operation_title = Paragraph(
                "ACCEPTATION DE CREDIT",
                ParagraphStyle("OpCreditTitle", parent=styles["Normal"],
                               fontSize=14, fontName="Helvetica-Bold",
                               alignment=TA_CENTER, textColor=color_header),
            )
            operation_info = Paragraph(
                f"<b>Reference :</b> {refpmt}<br/>"
                f"<b>Date et heure :</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}<br/>"
                f"<b>Magasin :</b> {magasin}<br/>"
                f"<b>Operateur :</b> {username}",
                ParagraphStyle("OpCreditInfo", parent=styles["Normal"], fontSize=9, alignment=TA_LEFT, leading=12),
            )
            operation_table = Table([[operation_title, operation_info]], colWidths=[title_width, info_width], rowHeights=[header_height])
            operation_table.setStyle(TableStyle([
                ("BOX",           (0, 0), (-1, -1), 1, colors.black),
                ("ALIGN",         (0, 0), (0, 0), "CENTER"),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING",    (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING",   (0, 0), (-1, -1), 6),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
            ]))

            header_table = Table([[company_table, operation_table]], colWidths=[company_width, right_width])
            header_table.setStyle(TableStyle([
                ("VALIGN",        (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING",    (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING",  (0, 0), (0, 0),   8),
                ("LEFTPADDING",   (1, 0), (1, 0),   8),
            ]))
            elements.append(header_table)
            elements.append(Spacer(1, 3 * mm))

            infos_credit = Paragraph(
                f"<b><u>Infos Credit</u></b><br/>",
                ParagraphStyle("InfoCreditLine", parent=styles["Normal"], fontSize=9, alignment=TA_CENTER, leading=11),
            )
            elements.append(infos_credit)
            elements.append(Spacer(1, 2 * mm))

            columns  = ["Ref. Facture", "Nom Client", "Montant", "Date echeance"]
            row_data = [[ref_facture, client_nom, self._formater_montant(montant_paye), echeance_str]]
            table_width = page_width_usable * 0.95
            col_widths  = [table_width * 0.22, table_width * 0.34, table_width * 0.20, table_width * 0.24]
            table_data  = [columns] + row_data

            credit_table = Table(table_data, colWidths=col_widths, repeatRows=1)
            credit_table.setStyle(TableStyle([
                ("BACKGROUND",   (0, 0), (-1, 0), colors.HexColor("#E8E8E8")),
                ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",     (0, 0), (-1, 0), 11),
                ("ALIGN",        (0, 0), (-1, 0), "CENTER"),
                ("ALIGN",        (0, 1), (1, -1), "LEFT"),
                ("ALIGN",        (2, 1), (3, -1), "CENTER"),
                ("FONTSIZE",     (0, 1), (-1, -1), 8),
                ("BOX",          (0, 0), (-1, -1), 1, colors.black),
                ("LINEBEFORE",   (1, 0), (1, -1), 1, color_header),
                ("LINEBEFORE",   (2, 0), (2, -1), 1, color_header),
                ("LINEBEFORE",   (3, 0), (3, -1), 1, color_header),
                ("TOPPADDING",   (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
            ]))
            elements.append(credit_table)
            elements.append(Spacer(1, 3 * mm))

            coord_client = Paragraph(
                f"<br/>&nbsp;&nbsp;&nbsp;<b><u>Coordonnees client :</u></b> {client_adresse or '-'} ; Tel : {client_contact or '-'}",
                ParagraphStyle("CoordClient", parent=styles["Normal"], fontSize=9, alignment=TA_LEFT, leading=11),
            )
            elements.append(coord_client)
            elements.append(Spacer(1, 1.5 * mm))

            desc_credit = Paragraph(
                f"<b><u>&nbsp;&nbsp;&nbsp;Description</u>:</b> {description_credit or '-'}",
                ParagraphStyle("DescCredit", parent=styles["Normal"], fontSize=9, alignment=TA_LEFT, leading=11),
            )
            elements.append(desc_credit)
            elements.append(Spacer(1, 4 * mm))

            sig_left  = Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;<u>Le Responsable</u>", ParagraphStyle("SigRespo",   parent=styles["Normal"], fontSize=9, alignment=TA_LEFT))
            sig_right = Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;<u>Le Client</u>",      ParagraphStyle("SigClient",  parent=styles["Normal"], fontSize=9, alignment=TA_LEFT))
            sig_table = Table([[sig_left, "", sig_right]], colWidths=[page_width_usable * 0.35, page_width_usable * 0.30, page_width_usable * 0.35])
            sig_table.setStyle(TableStyle([
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("ALIGN",      (0, 0), (0, 0),   "LEFT"),
                ("ALIGN",      (2, 0), (2, 0),   "RIGHT"),
            ]))
            elements.append(sig_table)

            doc.build(elements)

            if imprimer_ticket == 1:
                try:
                    open_file_if_enabled(output_path, operation="open")
                    print(f"✅ État crédit ouvert : {output_path}")
                except Exception as e:
                    print(f"⚠️ Erreur ouverture état crédit : {e}")
            else:
                print(f"📄 État crédit généré (impression désactivée) : {output_path}")

        except Exception as e:
            print(f"❌ Erreur génération état crédit PDF : {e}")
            traceback.print_exc()

    def _generer_ticket_pdf(self, info_soc, username, articles, montant_paye,
                             mode_paiement, refpmt, date_echeance=None,
                             imprimer_ticket=1, description=""):
        """Génère un ticket de paiement PDF au format 80mm."""
        try:
            temp_dir = tempfile.gettempdir()
            filename = os.path.join(
                temp_dir,
                f"Paiement_{self.refvente}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )
            largeur = 80 * mm
            hauteur = 297 * mm
            c = canvas.Canvas(filename, pagesize=(largeur, hauteur))
            y = hauteur - 10 * mm

            c.setFont("Helvetica-Bold", 10)
            nom_societe = info_soc[0] if info_soc else "NOM SOCIÉTÉ"
            c.drawCentredString(largeur / 2, y, nom_societe)
            y -= 4 * mm

            c.setFont("Helvetica", 8)
            adresse = info_soc[1] if info_soc and len(info_soc) > 1 else ""
            if adresse:
                c.drawCentredString(largeur / 2, y, adresse)
                y -= 3.5 * mm

            contact = info_soc[2] if info_soc and len(info_soc) > 2 else ""
            if contact:
                c.drawCentredString(largeur / 2, y, f"Tél: {contact}")
                y -= 3.5 * mm

            ville = info_soc[3] if info_soc and len(info_soc) > 3 else ""
            if ville:
                c.drawCentredString(largeur / 2, y, ville)
                y -= 5 * mm

            c.line(5 * mm, y, largeur - 5 * mm, y)
            y -= 5 * mm

            c.setFont("Helvetica-Bold", 11)
            c.drawCentredString(largeur / 2, y, "REÇU DE PAIEMENT")
            y -= 5 * mm

            c.setFont("Helvetica", 8)
            c.drawString(5 * mm, y, f"Réf. Paiement: {refpmt}")
            y -= 4 * mm
            c.drawString(5 * mm, y, f"Facture N°: {self.refvente}")
            y -= 4 * mm
            c.drawString(5 * mm, y, f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            y -= 4 * mm
            c.drawString(5 * mm, y, f"Client: {self.client}")
            y -= 4 * mm
            c.drawString(5 * mm, y, f"Utilisateur: {username}")
            y -= 5 * mm

            c.line(5 * mm, y, largeur - 5 * mm, y)
            y -= 5 * mm

            c.setFont("Helvetica-Bold", 8)
            c.drawString(5 * mm, y, "DÉTAILS")
            y -= 4 * mm

            c.setFont("Helvetica", 7)
            total_calcule = 0

            for article in articles:
                code, designation, unite, qte, prix_unit, montant = article
                total_calcule += float(montant)
                lignes_designation = self._couper_texte(designation, 30)
                for ligne in lignes_designation:
                    c.drawString(5 * mm, y, ligne)
                    y -= 3.5 * mm
                detail_qte = f"{qte} {unite or 'unité'} × {prix_unit:.2f} Ar"
                c.drawString(7 * mm, y, detail_qte)
                y -= 3.5 * mm
                montant_str = f"{montant:,.2f} Ar".replace(',', ' ')
                c.drawRightString(largeur - 5 * mm, y, montant_str)
                y -= 5 * mm
                if y < 50 * mm:
                    c.showPage()
                    y = hauteur - 10 * mm
                    c.setFont("Helvetica", 7)

            c.line(5 * mm, y, largeur - 5 * mm, y)
            y -= 5 * mm

            c.setFont("Helvetica-Bold", 10)
            c.drawString(5 * mm, y, "MONTANT PAYÉ:")
            montant_paye_str = f"{montant_paye:,.2f} Ar".replace(',', ' ')
            c.drawRightString(largeur - 5 * mm, y, montant_paye_str)
            y -= 6 * mm

            c.setFont("Helvetica", 9)
            c.drawString(5 * mm, y, f"Mode de paiement: {mode_paiement}")
            y -= 5 * mm

            description = (description or "").strip()
            if description:
                c.setFont("Helvetica", 8)
                c.drawString(5 * mm, y, "Observation:")
                y -= 3.5 * mm
                for ligne in self._couper_texte(description, 35):
                    c.drawString(7 * mm, y, ligne)
                    y -= 3.5 * mm
                y -= 1.5 * mm

            if mode_paiement.lower() == "crédit" and date_echeance:
                c.setFont("Helvetica-Bold", 9)
                c.drawString(5 * mm, y, f"Échéance: {date_echeance.strftime('%d/%m/%Y')}")
                y -= 6 * mm

            c.line(5 * mm, y, largeur - 5 * mm, y)
            y -= 5 * mm

            if num2words:
                try:
                    montant_lettres = num2words(montant_paye, lang='fr') + " Ariary"
                    c.setFont("Helvetica-Oblique", 7)
                    c.drawString(5 * mm, y, "Arrêté le présent reçu à la somme de:")
                    y -= 3.5 * mm
                    for ligne in self._couper_texte(montant_lettres, 35):
                        c.drawString(5 * mm, y, ligne)
                        y -= 3.5 * mm
                    y -= 2 * mm
                except Exception:
                    pass

            y -= 5 * mm
            c.setFont("Helvetica", 7)
            c.drawCentredString(largeur / 2, y, "Merci de votre confiance !")
            y -= 4 * mm
            c.drawCentredString(largeur / 2, y, f"Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}")

            c.save()

            if imprimer_ticket == 1:
                try:
                    open_file_if_enabled(filename, operation="open")
                    print(f"✅ Ticket de caisse ouvert : {filename}")
                except Exception as e:
                    print(f"⚠️ Erreur lors de l'ouverture du PDF : {e}")
            else:
                print(f"📄 Ticket de caisse généré (impression désactivée) : {filename}")

        except Exception as e:
            messagebox.showerror("Erreur PDF", f"Erreur lors de la génération du PDF : {e}")
            traceback.print_exc()
