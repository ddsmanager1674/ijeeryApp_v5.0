# -*- coding: utf-8 -*-
"""
Page Commande Fournisseur — iJeery
Refactorisé : thème app_theme, layout responsive, toggle transporteur, impression post-save.
"""

import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import json
from datetime import datetime
from typing import Optional
from html import escape
from tkcalendar import DateEntry
from resource_utils import get_config_path, safe_file_read
from app_theme import Colors, Fonts, styled, Theme


# ─────────────────────────────────────────────────────────────────────────────
# Dialogs
# ─────────────────────────────────────────────────────────────────────────────
class MessageDialog(ctk.CTkToplevel):
    def __init__(self, title: str, message: str, type_: str = "info"):
        super().__init__()
        self.title(title)
        self.geometry("420x190")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_CARD)

        icon = "ℹ️" if type_ == "info" else "⚠️" if type_ == "warning" else "❌"
        icon_color = Colors.PRIMARY if type_ == "info" else Colors.WARNING if type_ == "warning" else Colors.DANGER

        ctk.CTkLabel(
            self, text=icon, font=Fonts.heading(24), text_color=icon_color
        ).pack(pady=(18, 6))
        ctk.CTkLabel(
            self, text=message, font=Fonts.body(12),
            text_color=Colors.TEXT_PRIMARY, wraplength=360, justify="center"
        ).pack(padx=16, pady=(0, 14))

        styled.button_success(
            self, text="OK", command=self.destroy, width=110, height=34
        ).pack(pady=(0, 14))

        self.grab_set()
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.wait_window()


class YesNoDialog(ctk.CTkToplevel):
    def __init__(self, title: str, message: str):
        super().__init__()
        self.title(title)
        self.geometry("430x200")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_CARD)
        self.result = False

        ctk.CTkLabel(
            self, text="❓", font=Fonts.heading(24), text_color=Colors.WARNING
        ).pack(pady=(18, 6))
        ctk.CTkLabel(
            self, text=message, font=Fonts.body(12),
            text_color=Colors.TEXT_PRIMARY, wraplength=370, justify="center"
        ).pack(padx=16, pady=(0, 14))

        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(pady=(0, 14))
        styled.button_danger(bf, text="Non", command=self._no, width=110, height=34).pack(side="left", padx=8)
        styled.button_success(bf, text="Oui", command=self._yes, width=110, height=34).pack(side="left", padx=8)

        self.grab_set()
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.wait_window()

    def _yes(self):
        self.result = True
        self.destroy()

    def _no(self):
        self.result = False
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers TTK style (appliqués une seule fois)
# ─────────────────────────────────────────────────────────────────────────────
def _apply_treeview_style():
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "iJeery.Treeview",
        background=Colors.BG_CARD,
        foreground=Colors.TEXT_PRIMARY,
        fieldbackground=Colors.BG_CARD,
        rowheight=28,
        font=("Segoe UI", 9),
        borderwidth=0,
    )
    style.configure(
        "iJeery.Treeview.Heading",
        background=Colors.MIDNIGHT,
        foreground=Colors.TEXT_ON_DARK,
        font=("Segoe UI", 9, "bold"),
        relief="flat",
        borderwidth=0,
    )
    style.map("iJeery.Treeview",
              background=[("selected", Colors.PRIMARY_LIGHT)],
              foreground=[("selected", Colors.TEXT_PRIMARY)])
    style.map("iJeery.Treeview.Heading",
              background=[("active", Colors.MIDNIGHT_LIGHT)])


# ─────────────────────────────────────────────────────────────────────────────
# Séparateur horizontal léger
# ─────────────────────────────────────────────────────────────────────────────
def _divider(parent):
    return ctk.CTkFrame(parent, height=1, fg_color=Colors.DIVIDER)


class PageCommandeFrs(ctk.CTkFrame):
    def __init__(self, parent, iduser):
        super().__init__(parent, fg_color=Colors.BG_PAGE)
        _apply_treeview_style()   # Appelé ici — fenêtre Tk déjà initialisée
        self.iduser = iduser
        self.article_selectionne = None
        self.items_commande = []

        self.idcom_charge = None
        self.mode_modification = False
        self.index_ligne_selectionnee = None

        # Transporteur
        self.transporteur_id = None
        self.transporteur_nom = None
        self._infos_charge_value = ""

        self.setup_ui()
        self.generer_reference()
        self.charger_fournisseurs()

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
        except FileNotFoundError:
            messagebox.showerror("Erreur", "Fichier 'config.json' non trouvé.")
        except KeyError:
            messagebox.showerror("Erreur", "Clés DB manquantes dans 'config.json'.")
        except psycopg2.Error as e:
            messagebox.showerror("Connexion", f"Erreur PostgreSQL : {e}")
        except UnicodeDecodeError as e:
            messagebox.showerror("Encodage", f"Problème d'encodage : {e}")
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Utilitaires numériques
    # ─────────────────────────────────────────────────────────────────────────
    def formater_nombre(self, nombre):
        try:
            nombre = float(nombre)
            partie_entiere = int(nombre)
            partie_decimale = abs(nombre - partie_entiere)
            str_entiere = f"{partie_entiere:,}".replace(',', '.')
            str_decimale = f"{partie_decimale:.2f}".split('.')[1]
            return f"{str_entiere},{str_decimale}"
        except:
            return "0,00"

    def parser_nombre(self, texte):
        try:
            return float(texte.replace('.', '').replace(',', '.'))
        except:
            return 0.0

    # ─────────────────────────────────────────────────────────────────────────
    # Couleurs alternées Treeview
    # ─────────────────────────────────────────────────────────────────────────
    def _configure_table_alternating_colors(self, tree):
        tree.tag_configure("row_even", background=Colors.BG_CARD)
        tree.tag_configure("row_odd", background=Colors.BG_ROW_ALT)

    def _refresh_table_alternating_colors(self, tree):
        for idx, item in enumerate(tree.get_children()):
            tags = tuple(t for t in tree.item(item, "tags") if t not in ("row_even", "row_odd"))
            alt = "row_even" if idx % 2 == 0 else "row_odd"
            tree.item(item, tags=tags + (alt,))

    # ─────────────────────────────────────────────────────────────────────────
    # Nombre en lettres
    # ─────────────────────────────────────────────────────────────────────────
    def nombre_en_lettres(self, nombre):
        unites = ["", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf"]
        dizaines = ["", "dix", "vingt", "trente", "quarante", "cinquante",
                    "soixante", "soixante-dix", "quatre-vingt", "quatre-vingt-dix"]

        def c100(n):
            if n < 10: return unites[n]
            if n < 20:
                s = ["dix","onze","douze","treize","quatorze","quinze","seize",
                     "dix-sept","dix-huit","dix-neuf"]
                return s[n-10]
            if n < 70:
                u = n % 10; d = n // 10
                if u == 0: return dizaines[d]
                if u == 1 and d != 8: return dizaines[d] + "-et-un"
                return dizaines[d] + "-" + unites[u]
            if n < 80: return "soixante-" + c100(n-60)
            if n == 80: return "quatre-vingts"
            return "quatre-vingt-" + c100(n-80)

        def c1000(n):
            if n < 100: return c100(n)
            cent = n // 100; reste = n % 100
            r = ("cent" if cent == 1 else unites[cent] + " cent")
            if reste == 0:
                if cent > 1: r += "s"
            else: r += " " + c100(reste)
            return r

        try:
            nombre = float(nombre)
            entier = int(nombre)
            dec = int(round((nombre - entier) * 100))
            if entier == 0: res = "zéro"
            else:
                res = ""
                if entier >= 1000000:
                    m = entier // 1000000
                    res += ("un million " if m == 1 else c1000(m) + " millions ")
                    entier %= 1000000
                if entier >= 1000:
                    k = entier // 1000
                    res += ("mille " if k == 1 else c1000(k) + " mille ")
                    entier %= 1000
                if entier > 0: res += c1000(entier)
            res = res.strip() + " Ariary"
            if dec > 0: res += " et " + c100(dec) + " centimes"
            return res.capitalize()
        except:
            return "Zéro Ariary"

    # =========================================================================
    # CONSTRUCTION DE L'UI  — layout compact, sans scrollbar
    # =========================================================================
    def setup_ui(self):
        # ── En-tête ──────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT, corner_radius=0, height=42)
        header.pack(fill="x")
        header.pack_propagate(False)

        styled.button_info(
            header, text="Charger", icon="📂",
            command=self.ouvrir_recherche_commande, width=120, height=28
        ).pack(side="right", padx=8, pady=7)

        styled.button_secondary(
            header, text="Nouveau", icon="🔄",
            command=self.nouvelle_commande, width=100, height=28
        ).pack(side="right", padx=0, pady=7)

        styled.button_info(
            header, text="Stock par frs", icon="📦",
            command=self.ouvrir_stock_par_frs, width=140, height=28
        ).pack(side="right", padx=8, pady=7)

        # ── Corps principal (pas de scrollbar) ───────────────────────────────
        body = ctk.CTkFrame(self, fg_color=Colors.BG_PAGE)
        body.pack(fill="both", expand=True, padx=8, pady=6)

        # Section 1 — Infos générales
        self._build_section_infos(body)

        # Section 2 — Transporteur
        self._build_section_transporteur(body)

        # Section 3 — Saisie article
        self._build_section_article(body)

        # Section 4 — Tableau
        self._build_section_tableau(body)

    # ─────────────────────────────────────────────────────────────────────────
    # Section 1 — Infos générales  (ref + fournisseur inline)
    # ─────────────────────────────────────────────────────────────────────────
    def ouvrir_stock_par_frs(self):
        """
        Ouvre l'écran "Stock par Fournisseur" (PageStockParFrs).
        Conçu pour être accessible depuis le menu "Bon de commande".
        """
        fen = ctk.CTkToplevel(self)
        fen.title("Stock par Fournisseur")
        fen.geometry("1200x720")
        fen.resizable(True, True)
        fen.grab_set()

        try:
            Theme.apply_toplevel(fen)
        except Exception:
            pass

        try:
            from pages.page_stockParFrs import PageStockParFrs
        except ImportError:
            from page_stockParFrs import PageStockParFrs

        page = PageStockParFrs(fen, iduser=self.iduser)
        page.pack(fill="both", expand=True)

    def _build_section_infos(self, parent):
        card = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD,
                            corner_radius=8, border_width=1, border_color=Colors.BORDER)
        card.pack(fill="x", pady=(0, 4))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=6)
        row.columnconfigure(3, weight=1)

        # Titre section inline à gauche
        ctk.CTkLabel(row, text="📋 Commande", font=Fonts.bold(11),
                     text_color=Colors.MIDNIGHT, width=90, anchor="w"
                     ).grid(row=0, column=0, sticky="w", padx=(0, 6))

        # Référence
        self.entry_ref = ctk.CTkEntry(row, width=160, height=28,
                                      fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
                                      font=Fonts.body(11), state="readonly")
        self.entry_ref.grid(row=0, column=1, sticky="w", padx=(0, 20))

        # Fournisseur label
        ctk.CTkLabel(row, text="Fournisseur :", font=Fonts.label(10),
                     text_color=Colors.TEXT_SECONDARY, anchor="w"
                     ).grid(row=0, column=2, sticky="w", padx=(0, 4))

        # Fournisseur entry + bouton
        frs_f = ctk.CTkFrame(row, fg_color="transparent")
        frs_f.grid(row=0, column=3, sticky="ew")

        self.entry_fournisseur = ctk.CTkEntry(frs_f, height=28,
                                              fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
                                              font=Fonts.body(11), state="readonly")
        self.entry_fournisseur.pack(side="left", fill="x", expand=True, padx=(0, 4))

        ctk.CTkButton(frs_f, text="🔍", width=28, height=28,
                      fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
                      text_color="white", font=Fonts.body(11), corner_radius=6,
                      command=self.ouvrir_recherche_fournisseur
                      ).pack(side="left")

        self.fournisseur_id = None
        self.fournisseur_contact = None
        self.fournisseur_adresse = None

    # ─────────────────────────────────────────────────────────────────────────
    # Section 2 — Transporteur (toggle inline)
    # ─────────────────────────────────────────────────────────────────────────
    def _build_section_transporteur(self, parent):
        card = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD,
                            corner_radius=8, border_width=1, border_color=Colors.BORDER)
        card.pack(fill="x", pady=(0, 4))

        # Ligne unique : titre + switch + entry + bouton (tout inline)
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=6)
        row.columnconfigure(3, weight=1)

        ctk.CTkLabel(row, text="🚛 Transporteur", font=Fonts.bold(11),
                     text_color=Colors.MIDNIGHT, width=110, anchor="w"
                     ).grid(row=0, column=0, sticky="w", padx=(0, 6))

        self.var_transporteur = ctk.BooleanVar(value=False)
        self.switch_transporteur = ctk.CTkSwitch(
            row, text="", variable=self.var_transporteur,
            command=self.toggle_transporteur,
            width=40, button_color=Colors.PRIMARY,
            progress_color=Colors.PRIMARY_LIGHT,
            switch_width=40, switch_height=20
        )
        self.switch_transporteur.grid(row=0, column=1, sticky="w", padx=(0, 10))

        # Entry transporteur (masquée ou visible selon switch)
        self.entry_transporteur = ctk.CTkEntry(
            row, height=28, fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER, font=Fonts.body(11),
            state="readonly", placeholder_text="Sélectionner un transporteur..."
        )
        # Bouton recherche transporteur
        self.btn_search_trans = ctk.CTkButton(
            row, text="🔍", width=28, height=28,
            fg_color=Colors.INFO, hover_color=Colors.INFO_DARK,
            text_color="white", font=Fonts.body(11), corner_radius=6,
            command=self.ouvrir_recherche_transporteur
        )

        # Widgets cachés par défaut — affichés par toggle_transporteur
        self._trans_entry_col = 3
        self._trans_btn_col   = 4

    def toggle_transporteur(self):
        if self.var_transporteur.get():
            row = self.entry_transporteur.master
            self.entry_transporteur.grid(row=0, column=self._trans_entry_col, sticky="ew", padx=(0, 4))
            self.btn_search_trans.grid(row=0, column=self._trans_btn_col, sticky="w")
        else:
            self.entry_transporteur.grid_remove()
            self.btn_search_trans.grid_remove()
            self.transporteur_id = None
            self.transporteur_nom = None
            self.entry_transporteur.configure(state="normal")
            self.entry_transporteur.delete(0, "end")
            self.entry_transporteur.configure(state="readonly")

    # ─────────────────────────────────────────────────────────────────────────
    # Section 3 — Saisie article (compact)
    # ─────────────────────────────────────────────────────────────────────────
    def _build_section_article(self, parent):
        card = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD,
                            corner_radius=8, border_width=1, border_color=Colors.BORDER)
        card.pack(fill="x", pady=(0, 4))

        # ── Ligne 1 : titre section | entry article + bouton recherche ───────
        r1 = ctk.CTkFrame(card, fg_color="transparent")
        r1.pack(fill="x", padx=10, pady=(6, 2))
        r1.columnconfigure(2, weight=1)

        ctk.CTkLabel(r1, text="📦 Article", font=Fonts.bold(11),
                     text_color=Colors.MIDNIGHT, width=78, anchor="w"
                     ).grid(row=0, column=0, sticky="w", padx=(0, 6))

        self.entry_article = ctk.CTkEntry(r1, height=28,
                                          fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
                                          font=Fonts.body(11), state="readonly")
        self.entry_article.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(0, 4))

        ctk.CTkButton(r1, text="🔍 Rechercher", width=110, height=28,
                      fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
                      text_color="white", font=Fonts.body(10), corner_radius=6,
                      command=self.ouvrir_recherche_article
                      ).grid(row=0, column=3, sticky="w")

        # ── Ligne 2 : tout inline sur une seule ligne ─────────────────────────
        r2 = ctk.CTkFrame(card, fg_color="transparent")
        r2.pack(fill="x", padx=10, pady=(2, 6))

        def _field(par, label, width=90, readonly=False):
            """Label au-dessus + entry, empilés, packés side=left."""
            wrap = ctk.CTkFrame(par, fg_color="transparent")
            wrap.pack(side="left", padx=(0, 6))
            ctk.CTkLabel(wrap, text=label, font=Fonts.small(9),
                         text_color=Colors.TEXT_MUTED).pack(anchor="w")
            e = ctk.CTkEntry(wrap, width=width, height=26,
                             fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
                             font=Fonts.body(10),
                             state="readonly" if readonly else "normal")
            e.pack()
            return e

        self.entry_qtcmd    = _field(r2, "Qté cmd",       95)
        self.entry_qtlivre  = _field(r2, "Qté livrée",    85)
        self.entry_qtlivre.insert(0, "0")
        self.entry_unite    = _field(r2, "Unité",          85, readonly=True)
        self.entry_punitcmd = _field(r2, "Prix unitaire", 105)

        self._font_label_small = Fonts.small(9)
        self._font_label_small_strike = Fonts.small(9)
        self._font_label_small_strike.configure(overstrike=True)

        self.entry_qtcmd.bind('<KeyRelease>',    lambda e: self.calculer_total_ligne_preview())
        self.entry_punitcmd.bind('<KeyRelease>', lambda e: self.calculer_total_ligne_preview())

        # Frais/Charges (label + checkbox en haut, entry en bas)
        charge_wrap = ctk.CTkFrame(r2, fg_color="transparent")
        charge_wrap.pack(side="left", padx=(0, 6))
        charge_label_row = ctk.CTkFrame(charge_wrap, fg_color="transparent")
        charge_label_row.pack(anchor="w")

        self.var_has_charge = ctk.BooleanVar(value=False)
        self.check_charge = ctk.CTkCheckBox(
            charge_label_row, text="", variable=self.var_has_charge,
            command=self.toggle_frais_charge,
            checkbox_width=16, checkbox_height=16,
            checkmark_color=Colors.TEXT_ON_DARK,
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            width=18
        )
        self.check_charge.pack(side="left", padx=(0, 2))
        self.label_charge = ctk.CTkLabel(
            charge_label_row, text="Frais/Charges",
            font=self._font_label_small_strike, text_color=Colors.TEXT_MUTED
        )
        self.label_charge.pack(side="left", padx=(0, 4))
        self.info_charge = ctk.CTkLabel(
            charge_label_row, text="ℹ", cursor="hand2",
            font=Fonts.bold(10), text_color=Colors.INFO
        )
        self.info_charge.pack(side="left")
        self.info_charge.bind("<Enter>", self._show_charge_tooltip)
        self.info_charge.bind("<Leave>", self._hide_charge_tooltip)
        self.info_charge.bind("<Button-1>", self._show_charge_tooltip)
        self.info_charge.pack_forget()
        self._charge_tooltip = None
        self.entry_charge = ctk.CTkEntry(
            charge_wrap, width=90, height=26,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            font=Fonts.body(10)
        )

        # Péremption optionnelle (label + checkbox en haut, date en bas)
        per_wrap = ctk.CTkFrame(r2, fg_color="transparent")
        per_wrap.pack(side="left", padx=(0, 6))
        per_label_row = ctk.CTkFrame(per_wrap, fg_color="transparent")
        per_label_row.pack(anchor="w")

        self.var_has_peremption = ctk.BooleanVar(value=False)
        self.check_peremption = ctk.CTkCheckBox(
            per_label_row, text="", variable=self.var_has_peremption,
            command=self.toggle_date_peremption,
            checkbox_width=16, checkbox_height=16,
            checkmark_color=Colors.TEXT_ON_DARK,
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            width=18
        )
        self.check_peremption.pack(side="left", padx=(0, 2))
        self.label_peremption = ctk.CTkLabel(
            per_label_row, text="Péremption (opt.)",
            font=self._font_label_small_strike, text_color=Colors.TEXT_MUTED
        )
        self.label_peremption.pack(side="left", padx=(0, 4))
        self.entry_peremption = DateEntry(
            per_wrap, width=9, background=Colors.MIDNIGHT,
            foreground="white", borderwidth=1,
            date_pattern="dd/mm/yyyy", state="disabled",
            font=("Segoe UI", 9)
        )
        self.toggle_frais_charge(False)
        self.toggle_date_peremption(False)

        # Total ligne preview (label badge, toujours visible)
        tot_wrap = ctk.CTkFrame(r2, fg_color="transparent")
        tot_wrap.pack(side="left", padx=(6, 10))
        ctk.CTkLabel(tot_wrap, text="Total ligne", font=Fonts.small(9),
                     text_color=Colors.TEXT_MUTED).pack(anchor="w")
        self.label_total_ligne = ctk.CTkLabel(
            tot_wrap, text="0,00",
            font=Fonts.bold(10), text_color=Colors.SUCCESS_TEXT,
            fg_color=Colors.SUCCESS_LIGHT, corner_radius=5, padx=7, pady=3
        )
        self.label_total_ligne.pack(anchor="w")

        # ── Boutons d'action — inline dans r2, poussés à droite ──────────────
        btn_wrap = ctk.CTkFrame(r2, fg_color="transparent")
        btn_wrap.pack(side="right")

        # Espace vide pour aligner les boutons avec les entries (compense le label au-dessus)
        ctk.CTkLabel(btn_wrap, text=" ", font=Fonts.small(9)).pack(anchor="w")
        btn_inner = ctk.CTkFrame(btn_wrap, fg_color="transparent")
        btn_inner.pack()

        self.btn_ajouter = ctk.CTkButton(
            btn_inner, text="➕ Ajouter", width=90, height=26,
            fg_color=Colors.SUCCESS, hover_color=Colors.SUCCESS_DARK,
            text_color=Colors.TEXT_ON_DARK, font=Fonts.button(10),
            corner_radius=5, command=self.ajouter_article
        )
        self.btn_ajouter.pack(side="left", padx=(0, 4))

        self.btn_modifier_ligne = ctk.CTkButton(
            btn_inner, text="✏️ Modif.", width=85, height=26,
            fg_color=Colors.WARNING, hover_color="#D68910",
            text_color=Colors.TEXT_ON_DARK, font=Fonts.button(10),
            corner_radius=5, state="disabled",
            command=self.modifier_ligne_article
        )
        self.btn_modifier_ligne.pack(side="left", padx=(0, 4))

        self.btn_annuler_selection = ctk.CTkButton(
            btn_inner, text="✖", width=28, height=26,
            fg_color=Colors.CLOUDS, hover_color=Colors.SILVER,
            text_color=Colors.TEXT_PRIMARY, font=Fonts.button(10),
            border_width=1, border_color=Colors.BORDER, corner_radius=5,
            state="disabled", command=self.annuler_selection_ligne
        )
        self.btn_annuler_selection.pack(side="left")

    # ─────────────────────────────────────────────────────────────────────────
    # Section 4 — Tableau (expand)
    # ─────────────────────────────────────────────────────────────────────────
    def _build_section_tableau(self, parent):
        card = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD,
                            corner_radius=8, border_width=1, border_color=Colors.BORDER)
        card.pack(fill="both", expand=True, pady=(0, 0))

        # En-tête tableau
        thead = ctk.CTkFrame(card, fg_color="transparent")
        thead.pack(fill="x", padx=10, pady=(6, 4))

        ctk.CTkLabel(thead, text="📄 Lignes de commande",
                     font=Fonts.bold(11), text_color=Colors.MIDNIGHT
                     ).pack(side="left")

        self.label_total_global = ctk.CTkLabel(
            thead, text="Total : 0,00",
            font=Fonts.bold(12), text_color=Colors.SUCCESS_TEXT,
            fg_color=Colors.SUCCESS_LIGHT, corner_radius=6, padx=10, pady=3
        )
        self.label_total_global.pack(side="right")

        # Treeview
        tree_frame = ctk.CTkFrame(card, fg_color=Colors.BORDER, corner_radius=6)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 4))

        colonnes = ("Article", "Unité", "Qté Cmd", "Prix Unit.", "Qté Livrée", "Péremption", "Fournisseur")
        self.tree = ttk.Treeview(tree_frame, columns=colonnes,
                                  show="headings", height=6,
                                  style="iJeery.Treeview")
        self._configure_table_alternating_colors(self.tree)

        col_widths = {"Article": 220, "Unité": 75, "Qté Cmd": 90,
                      "Prix Unit.": 105, "Qté Livrée": 90, "Péremption": 90, "Fournisseur": 140}
        for col in colonnes:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=col_widths.get(col, 90),
                             anchor="center" if col not in ("Article", "Fournisseur") else "w",
                             minwidth=60)

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.tree.bind('<<TreeviewSelect>>', self.on_selection_ligne)
        self.tree.bind('<Double-Button-1>', self.on_double_click_ligne)

        # Barre basse : supprimer + total + enregistrer
        bot = ctk.CTkFrame(card, fg_color="transparent")
        bot.pack(fill="x", padx=10, pady=(0, 6))

        styled.button_danger(bot, text="Supprimer", icon="🗑️",
                             width=120, height=28,
                             command=self.supprimer_article
                             ).pack(side="left")

        styled.button_success(bot, text="Enregistrer", icon="💾",
                              command=self.enregistrer_commande, width=140, height=28
                              ).pack(side="right")

        self.label_total = ctk.CTkLabel(bot, text="Total : 0,00",
                                        font=Fonts.bold(11), text_color=Colors.TEXT_MUTED)
        self.label_total.pack(side="right", padx=12)

    # =========================================================================
    # LOGIQUE TRANSPORTEUR
    # =========================================================================
    def ouvrir_recherche_transporteur(self):
        fen = ctk.CTkToplevel(self)
        fen.title("Rechercher un transporteur")
        fen.geometry("700x380")
        fen.grab_set()
        Theme.apply_toplevel(fen)

        main = ctk.CTkFrame(fen, fg_color=Colors.BG_PAGE)
        main.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(main, text="Sélectionner un transporteur",
                     font=Fonts.heading(14), text_color=Colors.MIDNIGHT
                     ).pack(pady=(0, 10))

        sf = ctk.CTkFrame(main, fg_color="transparent")
        sf.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(sf, text="🔍", font=Fonts.body(13)).pack(side="left", padx=6)
        entry_s = ctk.CTkEntry(sf, placeholder_text="Nom ou contact...",
                               height=34, fg_color=Colors.BG_INPUT,
                               border_color=Colors.BORDER, font=Fonts.body(11))
        entry_s.pack(side="left", fill="x", expand=True, padx=4)

        tf = ctk.CTkFrame(main, fg_color=Colors.BORDER, corner_radius=8)
        tf.pack(fill="both", expand=True, pady=(0, 8))

        cols = ("ID", "Nom", "Contact", "Adresse")
        tree = ttk.Treeview(tf, columns=cols, show="headings",
                             height=8, style="iJeery.Treeview")
        self._configure_table_alternating_colors(tree)
        tree.heading("ID", text="ID")
        tree.heading("Nom", text="Nom")
        tree.heading("Contact", text="Contact")
        tree.heading("Adresse", text="Adresse")
        tree.column("ID", width=0, stretch=False)
        tree.column("Nom", width=180)
        tree.column("Contact", width=140)
        tree.column("Adresse", width=260)
        sb = ttk.Scrollbar(tf, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        lbl_count = ctk.CTkLabel(main, text="", font=Fonts.small(10),
                                  text_color=Colors.TEXT_MUTED)
        lbl_count.pack(pady=(0, 4))

        def charger(filtre=""):
            for i in tree.get_children(): tree.delete(i)
            conn = self.connect_db()
            if not conn: return
            try:
                cur = conn.cursor()
                q = "SELECT idtransporteur, nom, contact, adresse FROM tb_transporteur WHERE deleted=0"
                p = []
                if filtre:
                    q += " AND (LOWER(nom) LIKE LOWER(%s) OR LOWER(contact) LIKE LOWER(%s))"
                    p = [f"%{filtre}%", f"%{filtre}%"]
                q += " ORDER BY nom"
                cur.execute(q, p)
                rows = cur.fetchall()
                for r in rows:
                    tree.insert("", "end", values=(r[0], r[1] or "", r[2] or "", r[3] or ""))
                self._refresh_table_alternating_colors(tree)
                lbl_count.configure(text=f"{len(rows)} transporteur(s)")
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
            finally:
                conn.close()

        entry_s.bind('<KeyRelease>', lambda e: charger(entry_s.get()))

        def valider():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Attention", "Veuillez sélectionner un transporteur.")
                return
            v = tree.item(sel[0])['values']
            self.transporteur_id = v[0]
            self.transporteur_nom = v[1]
            self.entry_transporteur.configure(state="normal")
            self.entry_transporteur.delete(0, "end")
            self.entry_transporteur.insert(0, v[1])
            self.entry_transporteur.configure(state="readonly")
            fen.destroy()

        tree.bind('<Double-Button-1>', lambda e: valider())

        bf = ctk.CTkFrame(main, fg_color="transparent")
        bf.pack(fill="x")
        styled.button_danger(bf, text="Annuler", icon="❌", width=110, height=36,
                             command=fen.destroy).pack(side="left", padx=4)
        styled.button_success(bf, text="Valider", icon="✅", width=110, height=36,
                              command=valider).pack(side="right", padx=4)
        charger()

    # =========================================================================
    # LOGIQUE MÉTIER (inchangée, sauf adaptations mineures)
    # =========================================================================

    def toggle_date_peremption(self, force_state=None):
        if force_state is not None:
            self.var_has_peremption.set(bool(force_state))
        enabled = self.var_has_peremption.get()
        self.label_peremption.configure(
            font=self._font_label_small if enabled else self._font_label_small_strike
        )
        if enabled:
            if not self.entry_peremption.winfo_manager():
                self.entry_peremption.pack(anchor="w")
            self.entry_peremption.configure(state="normal")
        else:
            self.entry_peremption.configure(state="disabled")
            if self.entry_peremption.winfo_manager():
                self.entry_peremption.pack_forget()

    def toggle_frais_charge(self, force_state=None):
        if force_state is not None:
            self.var_has_charge.set(bool(force_state))
        enabled = self.var_has_charge.get()
        self.label_charge.configure(
            font=self._font_label_small if enabled else self._font_label_small_strike
        )
        if enabled:
            if not self.entry_charge.winfo_manager():
                self.entry_charge.pack(anchor="w")
            self.entry_charge.configure(state="normal")
            if not self.info_charge.winfo_manager():
                self.info_charge.pack(side="left")
        else:
            self.entry_charge.configure(state="disabled")
            if self.entry_charge.winfo_manager():
                self.entry_charge.pack_forget()
            self.entry_charge.delete(0, "end")
            if self.info_charge.winfo_manager():
                self.info_charge.pack_forget()

    def _show_charge_tooltip(self, event=None):
        if self._charge_tooltip and self._charge_tooltip.winfo_exists():
            return
        tip = ctk.CTkToplevel(self)
        tip.overrideredirect(True)
        tip.attributes("-topmost", True)
        tip.configure(fg_color=Colors.BG_CARD)

        texte = self._get_infos_charge_value() or ""
        if not texte:
            texte = " "
        lbl = ctk.CTkLabel(
            tip, text=texte,
            font=Fonts.small(10), text_color=Colors.TEXT_PRIMARY,
            fg_color=Colors.BG_CARD, padx=8, pady=4,
            wraplength=320, justify="left"
        )
        lbl.pack()

        x = (event.x_root + 8) if event else (self.winfo_rootx() + 20)
        y = (event.y_root + 10) if event else (self.winfo_rooty() + 20)
        tip.geometry(f"+{x}+{y}")
        self._charge_tooltip = tip

    def _hide_charge_tooltip(self, event=None):
        if self._charge_tooltip and self._charge_tooltip.winfo_exists():
            self._charge_tooltip.destroy()
        self._charge_tooltip = None

    def _get_infos_charge_value(self):
        conn = self.connect_db()
        if not conn:
            return ""
        try:
            cur = conn.cursor()
            cur.execute("SELECT valeur FROM tb_autre_infos WHERE intitule=%s", ("infos_charge",))
            row = cur.fetchone()
            self._infos_charge_value = row[0] if row and row[0] else ""
        except Exception:
            self._infos_charge_value = ""
        finally:
            cur.close()
            conn.close()
        return self._infos_charge_value

    def on_selection_ligne(self, event):
        if self.tree.selection():
            self.btn_modifier_ligne.configure(state="normal")
            self.btn_annuler_selection.configure(state="normal")

    def on_fournisseur_change(self, selection=None):
        if not selection: return
        try:
            self.fournisseur_id = selection.split(" - ")[0].strip() if " - " in selection else selection.strip()
        except Exception:
            self.fournisseur_id = None

    def update_date_modification(self):
        if not self.idcom_charge: return
        conn = self.connect_db()
        if conn is None: return
        try:
            cur = conn.cursor()
            cur.execute("UPDATE tb_commande SET datemodif=%s WHERE idcom=%s",
                        (datetime.now(), self.idcom_charge))
            conn.commit()
        except psycopg2.Error as e:
            conn.rollback()
        finally:
            conn.close()

    def on_double_click_ligne(self, event):
        sel = self.tree.selection()
        if sel: self.charger_ligne_pour_modification(sel[0])

    def calculer_total_ligne_preview(self):
        try:
            t = self.parser_nombre(self.entry_qtcmd.get()) * self.parser_nombre(self.entry_punitcmd.get())
            self.label_total_ligne.configure(text=self.formater_nombre(t))
        except:
            self.label_total_ligne.configure(text="0,00")

    def charger_ligne_pour_modification(self, item_id):
        index = self.tree.index(item_id)
        self.index_ligne_selectionnee = index
        item_data = self.items_commande[index]
        values = self.tree.item(item_id)['values']

        self.entry_article.configure(state="normal")
        self.entry_article.delete(0, "end")
        self.entry_article.insert(0, values[0])
        self.entry_article.configure(state="readonly")

        self.entry_unite.configure(state="normal")
        self.entry_unite.delete(0, "end")
        self.entry_unite.insert(0, values[1])
        self.entry_unite.configure(state="readonly")

        self.entry_qtcmd.delete(0, "end")
        self.entry_qtcmd.insert(0, self.formater_nombre(item_data['qtcmd']))
        self.entry_punitcmd.delete(0, "end")
        self.entry_punitcmd.insert(0, self.formater_nombre(item_data['punitcmd']))
        self.entry_qtlivre.delete(0, "end")
        self.entry_qtlivre.insert(0, self.formater_nombre(item_data['qtlivre']))

        if item_data.get('dateperemption'):
            self.toggle_date_peremption(True)
            try:
                parts = item_data['dateperemption'].split('/')
                if len(parts) == 3:
                    self.entry_peremption.set_date(
                        datetime(int(parts[2]), int(parts[1]), int(parts[0])))
            except:
                pass
        else:
            self.toggle_date_peremption(False)

        montant_charge = item_data.get('montant_charge', 0) or 0
        if montant_charge > 0:
            self.toggle_frais_charge(True)
            self.entry_charge.delete(0, "end")
            self.entry_charge.insert(0, self.formater_nombre(montant_charge))
        else:
            self.toggle_frais_charge(False)

        self.article_selectionne = {
            'idarticle': item_data['idarticle'],
            'idunite': item_data['idunite'],
            'nomart': values[0],
            'unite': values[1]
        }

        self.btn_ajouter.configure(state="disabled")
        self.btn_modifier_ligne.configure(state="normal", text="✅  Valider Modif.")
        self.btn_annuler_selection.configure(state="normal")
        self.calculer_total_ligne_preview()

    def modifier_ligne_article(self):
        sel = self.tree.selection()
        if self.index_ligne_selectionnee is None:
            if sel: self.charger_ligne_pour_modification(sel[0])
            else: messagebox.showwarning("Attention", "Sélectionnez une ligne à modifier.")
            return
        try:
            qtcmd = self.parser_nombre(self.entry_qtcmd.get())
            punitcmd = self.parser_nombre(self.entry_punitcmd.get())
            qtlivre = self.parser_nombre(self.entry_qtlivre.get())
            if qtcmd <= 0:
                messagebox.showwarning("Attention", "La quantité doit être > 0.")
                return
            date_p = self.entry_peremption.get_date().strftime('%d/%m/%Y') if self.var_has_peremption.get() else ""
            montant_charge = self.parser_nombre(self.entry_charge.get()) if self.var_has_charge.get() else 0
            total = qtcmd * punitcmd
            idx = self.index_ligne_selectionnee
            self.items_commande[idx].update({'qtcmd': qtcmd, 'punitcmd': punitcmd,
                                             'qtlivre': qtlivre, 'total': total,
                                             'dateperemption': date_p or None,
                                             'montant_charge': montant_charge})
            item_id = self.tree.get_children()[idx]
            self.tree.item(item_id, values=(
                self.article_selectionne['nomart'], self.article_selectionne['unite'],
                self.formater_nombre(qtcmd), self.formater_nombre(punitcmd),
                self.formater_nombre(qtlivre), date_p,
                self.items_commande[idx].get('nomfrs', '')
            ))
            if self.idcom_charge: self.update_date_modification()
            self.annuler_selection_ligne()
            self.calculer_total()
            messagebox.showinfo("Succès", "Ligne modifiée avec succès !")
        except ValueError:
            messagebox.showerror("Erreur", "Valeurs numériques invalides.")

    def annuler_selection_ligne(self):
        self.index_ligne_selectionnee = None
        self.article_selectionne = None
        for e in (self.entry_article, self.entry_unite):
            e.configure(state="normal"); e.delete(0, "end"); e.configure(state="readonly")
        self.entry_qtcmd.delete(0, "end")
        self.entry_punitcmd.delete(0, "end")
        self.entry_qtlivre.delete(0, "end")
        self.entry_qtlivre.insert(0, "0")
        self.label_total_ligne.configure(text="0,00")
        self.toggle_frais_charge(False)
        self.toggle_date_peremption(False)
        self.btn_ajouter.configure(state="normal")
        self.btn_modifier_ligne.configure(state="disabled", text="✏️  Modifier Ligne")
        self.btn_annuler_selection.configure(state="disabled")
        self.tree.selection_remove(self.tree.selection())

    # ─────────────────────────────────────────────────────────────────────────
    # Génération référence
    # ─────────────────────────────────────────────────────────────────────────
    def generer_reference(self):
        conn = self.connect_db()
        if not conn: return
        try:
            cur = conn.cursor()
            annee = datetime.now().year
            cur.execute("SELECT refcom FROM tb_commande WHERE refcom LIKE %s ORDER BY refcom DESC LIMIT 1",
                        (f"{annee}-BC-%",))
            r = cur.fetchone()
            num = (int(r[0].split('-')[-1]) + 1) if r else 1
            ref = f"{annee}-BC-{num:05d}"
            self.entry_ref.configure(state="normal")
            self.entry_ref.delete(0, "end")
            self.entry_ref.insert(0, ref)
            self.entry_ref.configure(state="readonly")
        except Exception as e:
            messagebox.showerror("Erreur", f"Référence : {e}")
        finally:
            if 'cur' in locals(): cur.close()
            if conn: conn.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Fournisseurs
    # ─────────────────────────────────────────────────────────────────────────
    def _appliquer_fournisseur_entree(
        self,
        idfrs,
        nomfrs: Optional[str] = None,
    ) -> None:
        """Met à jour le champ fournisseur et les métadonnées associées."""
        if not idfrs:
            return
        info = getattr(self, "fournisseurs", {}).get(idfrs, {})
        nom = (nomfrs or info.get("nom") or "").strip()
        self.fournisseur_id = idfrs
        self.fournisseur_contact = info.get("contact", "") or ""
        self.fournisseur_adresse = info.get("adresse", "") or ""
        self.entry_fournisseur.configure(state="normal")
        self.entry_fournisseur.delete(0, "end")
        self.entry_fournisseur.insert(0, nom)
        self.entry_fournisseur.configure(state="readonly")

    def _fournisseur_premier_ligne_commande(self, commande, details):
        """Premier fournisseur présent dans les lignes de la commande chargée."""
        for d in details:
            idfrs_d, nomfrs_d = d[10], d[11]
            if idfrs_d:
                return int(idfrs_d), (nomfrs_d or "").strip()
        if commande[3]:
            return int(commande[3]), (commande[4] or "").strip()
        return None, None

    def appliquer_fournisseur_defaut_param(self) -> None:
        """Applique le fournisseur par défaut enregistré en base (nouveau BC)."""
        if self.mode_modification and self.idcom_charge:
            return
        try:
            from pages.commande_frs_common import CommandeFrsDB
        except ImportError:
            from commande_frs_common import CommandeFrsDB

        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            param = CommandeFrsDB.fetch_param_commande_frs(cur)
            id_def = param.get("idfrs_defaut")
            if id_def and id_def in getattr(self, "fournisseurs", {}):
                self._appliquer_fournisseur_entree(id_def)
        except Exception:
            pass
        finally:
            if "cur" in locals():
                cur.close()
            if conn:
                conn.close()

    def charger_fournisseurs(self):
        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT idfrs, nomfrs, contactfrs, adressefrs "
                "FROM tb_fournisseur WHERE deleted=0 ORDER BY nomfrs",
            )
            self.fournisseurs = {}
            rows = cur.fetchall()
            for row in rows:
                self.fournisseurs[row[0]] = {
                    "nom": row[1],
                    "contact": row[2] or "",
                    "adresse": row[3] or "",
                }
            self.appliquer_fournisseur_defaut_param()
            if not self.fournisseur_id and rows:
                self._appliquer_fournisseur_entree(rows[0][0], rows[0][1])
        except Exception as e:
            messagebox.showerror("Erreur", f"Fournisseurs : {e}")
        finally:
            if "cur" in locals():
                cur.close()
            if conn:
                conn.close()

    def ouvrir_recherche_fournisseur(self):
        fen = ctk.CTkToplevel(self)
        fen.title("Rechercher un fournisseur")
        fen.geometry("800x420")
        fen.grab_set()
        Theme.apply_toplevel(fen)

        main = ctk.CTkFrame(fen, fg_color=Colors.BG_PAGE)
        main.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(main, text="Sélectionner un fournisseur",
                     font=Fonts.heading(14), text_color=Colors.MIDNIGHT
                     ).pack(pady=(0, 10))

        sf = ctk.CTkFrame(main, fg_color="transparent")
        sf.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(sf, text="🔍").pack(side="left", padx=6)
        entry_s = ctk.CTkEntry(sf, placeholder_text="Nom ou contact...", height=34,
                               fg_color=Colors.BG_INPUT, border_color=Colors.BORDER, font=Fonts.body(11))
        entry_s.pack(side="left", fill="x", expand=True, padx=4)

        tf = ctk.CTkFrame(main, fg_color=Colors.BORDER, corner_radius=8)
        tf.pack(fill="both", expand=True, pady=(0, 8))
        cols = ("ID", "Nom", "Contact", "Adresse")
        tree = ttk.Treeview(tf, columns=cols, show="headings", height=10, style="iJeery.Treeview")
        self._configure_table_alternating_colors(tree)
        tree.column("ID", width=0, stretch=False)
        tree.column("Nom", width=160); tree.column("Contact", width=150); tree.column("Adresse", width=300)
        for c in cols: tree.heading(c, text=c)
        sb = ttk.Scrollbar(tf, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        lbl_c = ctk.CTkLabel(main, text="", font=Fonts.small(10), text_color=Colors.TEXT_MUTED)
        lbl_c.pack(pady=(0, 4))

        def charger(filtre=""):
            for i in tree.get_children(): tree.delete(i)
            conn = self.connect_db()
            if not conn: return
            try:
                cur = conn.cursor()
                q = "SELECT idfrs, nomfrs, contactfrs, adressefrs FROM tb_fournisseur WHERE deleted=0"
                p = []
                if filtre:
                    q += " AND (LOWER(nomfrs) LIKE LOWER(%s) OR LOWER(contactfrs) LIKE LOWER(%s))"
                    p = [f"%{filtre}%", f"%{filtre}%"]
                q += " ORDER BY nomfrs"
                cur.execute(q, p)
                rows = cur.fetchall()
                for r in rows:
                    tree.insert("", "end", values=(r[0], r[1] or '', r[2] or '', r[3] or ''))
                self._refresh_table_alternating_colors(tree)
                lbl_c.configure(text=f"{len(rows)} fournisseur(s)")
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
            finally:
                conn.close()

        entry_s.bind('<KeyRelease>', lambda e: charger(entry_s.get()))

        def valider():
            sel = tree.selection()
            if not sel: messagebox.showwarning("Attention", "Sélectionnez un fournisseur."); return
            v = tree.item(sel[0])['values']
            self._appliquer_fournisseur_entree(v[0], v[1])
            self.fournisseur_contact = v[2] or ""
            self.fournisseur_adresse = v[3] or ""
            fen.destroy()

        tree.bind('<Double-Button-1>', lambda e: valider())
        bf = ctk.CTkFrame(main, fg_color="transparent")
        bf.pack(fill="x")
        styled.button_danger(bf, text="Annuler", icon="❌", width=110, height=36, command=fen.destroy).pack(side="left", padx=4)
        styled.button_success(bf, text="Valider", icon="✅", width=110, height=36, command=valider).pack(side="right", padx=4)
        charger()

    # ─────────────────────────────────────────────────────────────────────────
    # Recherche commande
    # ─────────────────────────────────────────────────────────────────────────
    def ouvrir_recherche_commande(self):
        fen = ctk.CTkToplevel(self)
        fen.title("Charger une commande")
        fen.geometry("900x520")
        fen.grab_set()
        Theme.apply_toplevel(fen)

        main = ctk.CTkFrame(fen, fg_color=Colors.BG_PAGE)
        main.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(main, text="Sélectionner une commande",
                     font=Fonts.heading(14), text_color=Colors.MIDNIGHT).pack(pady=(0, 10))

        sf = ctk.CTkFrame(main, fg_color="transparent")
        sf.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(sf, text="🔍").pack(side="left", padx=6)
        entry_s = ctk.CTkEntry(sf, placeholder_text="Référence ou fournisseur...", height=34,
                               fg_color=Colors.BG_INPUT, border_color=Colors.BORDER, font=Fonts.body(11))
        entry_s.pack(side="left", fill="x", expand=True, padx=4)

        tf = ctk.CTkFrame(main, fg_color=Colors.BORDER, corner_radius=8)
        tf.pack(fill="both", expand=True, pady=(0, 8))
        cols = ("ID", "Référence", "Date", "Fournisseur", "Statut")
        tree = ttk.Treeview(tf, columns=cols, show="headings", height=12, style="iJeery.Treeview")
        self._configure_table_alternating_colors(tree)
        tree.column("ID", width=0, stretch=False)
        tree.column("Référence", width=130); tree.column("Date", width=110)
        tree.column("Fournisseur", width=220); tree.column("Statut", width=110, anchor="center")
        for c in cols: tree.heading(c, text=c)
        tree.tag_configure('incomplet', background='#fff3cd')
        tree.tag_configure('complet', background='#d4edda')
        sb = ttk.Scrollbar(tf, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        lbl_c = ctk.CTkLabel(main, text="", font=Fonts.small(10), text_color=Colors.TEXT_MUTED)
        lbl_c.pack(pady=(0, 4))

        def charger(filtre=""):
            for i in tree.get_children(): tree.delete(i)
            conn = self.connect_db()
            if not conn: return
            try:
                cur = conn.cursor()
                q = """
                    SELECT c.idcom, c.refcom, c.datecom,
                           COALESCE(NULLIF((
                               SELECT string_agg(DISTINCT COALESCE(f2.nomfrs,''),', ' ORDER BY COALESCE(f2.nomfrs,''))
                               FROM tb_commandedetail d2
                               LEFT JOIN tb_fournisseur f2 ON d2.idfrs=f2.idfrs
                               WHERE d2.idcom=c.idcom), ''), 'Non précisé') AS frs,
                           (SELECT COUNT(*) FROM tb_commandedetail d WHERE d.idcom=c.idcom) as tl,
                           (SELECT COUNT(*) FROM tb_commandedetail d WHERE d.idcom=c.idcom AND d.qtcmd=d.qtlivre) as lc
                    FROM tb_commande c WHERE c.deleted=0
                """
                p = []
                if filtre:
                    q += " AND (LOWER(c.refcom) LIKE LOWER(%s))"
                    p = [f"%{filtre}%"]
                q += " ORDER BY c.datecom DESC"
                cur.execute(q, p)
                rows = cur.fetchall()
                for r in rows:
                    ds = r[2].strftime("%d/%m/%Y") if r[2] else ""
                    tl = r[4] or 0; lc = r[5] or 0
                    statut = "✅ Livré" if tl > 0 and lc == tl else "⏳ En attente"
                    tag = "complet" if tl > 0 and lc == tl else "incomplet"
                    tree.insert("", "end", values=(r[0], r[1], ds, r[3] or "", statut), tags=(tag,))
                lbl_c.configure(text=f"{len(rows)} commande(s)")
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
            finally:
                conn.close()

        entry_s.bind('<KeyRelease>', lambda e: charger(entry_s.get()))

        def valider():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Attention", "Sélectionnez une commande.", parent=fen)
                return
            idcom = tree.item(sel[0])["values"][0]
            fen.destroy()
            self.charger_commande(idcom)

        def supprimer_commande():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning(
                    "Attention",
                    "Sélectionnez une commande à supprimer.",
                    parent=fen,
                )
                return
            vals = tree.item(sel[0])["values"]
            idcom = vals[0]
            refcom = vals[1] if len(vals) > 1 else str(idcom)
            if not messagebox.askyesno(
                "Confirmer la suppression",
                f"Supprimer la commande {refcom} ?\n\n"
                "Elle ne sera plus visible dans cette liste ni dans le "
                "chargement de commande du bon de réception.",
                parent=fen,
            ):
                return
            conn = self.connect_db()
            if not conn:
                return
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    UPDATE tb_commande
                    SET deleted = 1, datemodif = %s
                    WHERE idcom = %s AND COALESCE(deleted, 0) = 0
                    """,
                    (datetime.now(), idcom),
                )
                if cur.rowcount == 0:
                    conn.rollback()
                    messagebox.showerror(
                        "Erreur",
                        "Commande introuvable ou déjà supprimée.",
                        parent=fen,
                    )
                    return
                conn.commit()
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Erreur", f"Suppression : {e}", parent=fen)
                return
            finally:
                if "cur" in locals():
                    cur.close()
                conn.close()

            if getattr(self, "idcom_charge", None) == idcom:
                self.nouvelle_commande()
            charger(entry_s.get().strip())
            messagebox.showinfo(
                "Succès",
                f"Commande {refcom} supprimée.",
                parent=fen,
            )

        tree.bind("<Double-Button-1>", lambda e: valider())
        bf = ctk.CTkFrame(main, fg_color="transparent")
        bf.pack(fill="x")
        styled.button_danger(
            bf,
            text="Supprimer cette commande",
            icon="🗑",
            width=200,
            height=36,
            command=supprimer_commande,
        ).pack(side="left", padx=4)
        styled.button_success(
            bf, text="Charger", icon="📂", width=130, height=36, command=valider,
        ).pack(side="right", padx=4)
        charger()

    def charger_commande(self, idcom):
        conn = self.connect_db()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT c.idcom, c.refcom, c.datecom, c.idfrs, f.nomfrs, c.descriptioncom, c.idtransportuer
                FROM tb_commande c
                LEFT JOIN tb_fournisseur f ON c.idfrs=f.idfrs
                WHERE c.idcom=%s AND c.deleted=0
            """, (idcom,))
            commande = cur.fetchone()
            if not commande: messagebox.showerror("Erreur", "Commande non trouvée."); return

            cur.execute("""
                SELECT d.id, d.idarticle, a.designation, u.designationunite, d.idunite,
                       d.qtcmd, d.qtlivre, d.punitcmd, d.total, d.dateperemption, d.idfrs, f.nomfrs,
                       d.montant_charge
                FROM tb_commandedetail d
                INNER JOIN tb_article a ON d.idarticle=a.idarticle
                INNER JOIN tb_unite u ON d.idunite=u.idunite
                LEFT JOIN tb_fournisseur f ON d.idfrs=f.idfrs
                WHERE d.idcom=%s
            """, (idcom,))
            details = cur.fetchall()

            self.reinitialiser_formulaire(generer_ref=False)
            self.mode_modification = True
            self.idcom_charge = idcom

            self.entry_ref.configure(state="normal")
            self.entry_ref.delete(0, "end")
            self.entry_ref.insert(0, commande[1])
            self.entry_ref.configure(state="readonly")

            id_frs, nom_frs = self._fournisseur_premier_ligne_commande(commande, details)
            if id_frs:
                self._appliquer_fournisseur_entree(id_frs, nom_frs)

            # Transporteur
            idtrans = commande[6]
            if idtrans:
                self.var_transporteur.set(True)
                self.toggle_transporteur()
                # Récupérer nom transporteur
                cur.execute("SELECT nom FROM tb_transporteur WHERE idtransporteur=%s", (idtrans,))
                tr = cur.fetchone()
                if tr:
                    self.transporteur_id = idtrans
                    self.transporteur_nom = tr[0]
                    self.entry_transporteur.configure(state="normal")
                    self.entry_transporteur.delete(0, "end")
                    self.entry_transporteur.insert(0, tr[0])
                    self.entry_transporteur.configure(state="readonly")

            for d in details:
                idcd, idar, desig, unite, idunite, qtcmd, qtlivre, punit, total_db, datep, idfrs_d, nomfrs_d, montant_charge = d
                punit = punit or 0
                total = total_db if total_db else (qtcmd * punit)
                dp_str = ""
                if datep:
                    dp_str = datep if isinstance(datep, str) else datep.strftime('%d/%m/%Y')
                self.items_commande.append({
                    'idcomdetail': idcd, 'idarticle': idar, 'idunite': idunite,
                    'idfrs': idfrs_d if idfrs_d else commande[3],
                    'nomfrs': nomfrs_d if nomfrs_d else (commande[4] or ""),
                    'qtcmd': qtcmd, 'qtlivre': qtlivre, 'punitcmd': punit,
                    'total': total, 'dateperemption': dp_str,
                    'montant_charge': montant_charge or 0
                })
                self.tree.insert("", "end", values=(
                    desig, unite,
                    self.formater_nombre(qtcmd), self.formater_nombre(punit),
                    self.formater_nombre(qtlivre), dp_str,
                    nomfrs_d if nomfrs_d else (commande[4] or "")
                ))
            self._refresh_table_alternating_colors(self.tree)
            self.calculer_total()
        except Exception as e:
            messagebox.showerror("Erreur", f"Chargement commande : {e}")
        finally:
            if 'cur' in locals(): cur.close()
            if conn: conn.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Recherche article
    # ─────────────────────────────────────────────────────────────────────────
    def ouvrir_recherche_article(self):
        if self.index_ligne_selectionnee is not None:
            messagebox.showwarning("Attention", "Validez ou annulez la modification en cours.")
            return
        fen = ctk.CTkToplevel(self)
        fen.title("Rechercher un article")
        fen.geometry("1000x580")
        fen.grab_set()
        Theme.apply_toplevel(fen)

        main = ctk.CTkFrame(fen, fg_color=Colors.BG_PAGE)
        main.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(main, text="Sélectionner un article",
                     font=Fonts.heading(14), text_color=Colors.MIDNIGHT).pack(pady=(0, 10))

        sf = ctk.CTkFrame(main, fg_color="transparent")
        sf.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(sf, text="🔍").pack(side="left", padx=6)
        entry_s = ctk.CTkEntry(sf, placeholder_text="Code ou désignation...", height=34,
                               fg_color=Colors.BG_INPUT, border_color=Colors.BORDER, font=Fonts.body(11))
        entry_s.pack(side="left", fill="x", expand=True, padx=4)

        tf = ctk.CTkFrame(main, fg_color=Colors.BORDER, corner_radius=8)
        tf.pack(fill="both", expand=True, pady=(0, 8))
        cols = ("ID_Article", "ID_Unite", "Code", "Désignation", "Unité")
        tree = ttk.Treeview(tf, columns=cols, show="headings", height=14, style="iJeery.Treeview")
        self._configure_table_alternating_colors(tree)
        tree.column("ID_Article", width=0, stretch=False)
        tree.column("ID_Unite", width=0, stretch=False)
        tree.column("Code", width=140); tree.column("Désignation", width=480); tree.column("Unité", width=110)
        for c in cols: tree.heading(c, text=c)
        sb = ttk.Scrollbar(tf, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        lbl_c = ctk.CTkLabel(main, text="", font=Fonts.small(10), text_color=Colors.TEXT_MUTED)
        lbl_c.pack(pady=(0, 4))

        def charger(filtre=""):
            for i in tree.get_children(): tree.delete(i)
            conn = self.connect_db()
            if not conn: return
            try:
                cur = conn.cursor()
                q = """SELECT T2.idarticle, T1.codearticle, T2.designation, T1.designationunite, T1.idunite
                       FROM tb_unite T1 INNER JOIN tb_article T2 ON T1.idarticle=T2.idarticle
                       WHERE T2.deleted=0"""
                p = []
                if filtre:
                    q += " AND (LOWER(T1.codearticle) LIKE LOWER(%s) OR LOWER(T2.designation) LIKE LOWER(%s))"
                    p = [f"%{filtre}%", f"%{filtre}%"]
                q += ' ORDER BY T1.codearticle'
                cur.execute(q, p)
                rows = cur.fetchall()
                for r in rows:
                    tree.insert("", "end", values=(r[0], r[4], r[1], r[2], r[3]))
                self._refresh_table_alternating_colors(tree)
                lbl_c.configure(text=f"{len(rows)} article(s)")
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
            finally:
                conn.close()

        entry_s.bind('<KeyRelease>', lambda e: charger(entry_s.get()))

        def valider():
            sel = tree.selection()
            if not sel: messagebox.showwarning("Attention", "Sélectionnez un article."); return
            v = tree.item(sel[0])['values']
            self.article_selectionne = {'idarticle': v[0], 'idunite': v[1], 'nomart': v[3], 'unite': v[4]}
            self.entry_article.configure(state="normal")
            self.entry_article.delete(0, "end")
            self.entry_article.insert(0, v[3])
            self.entry_article.configure(state="readonly")
            self.entry_unite.configure(state="normal")
            self.entry_unite.delete(0, "end")
            self.entry_unite.insert(0, v[4])
            self.entry_unite.configure(state="readonly")
            self.entry_qtcmd.delete(0, "end")
            self.entry_punitcmd.delete(0, "end")
            self.calculer_total_ligne_preview()
            fen.destroy()

        tree.bind('<Double-Button-1>', lambda e: valider())
        bf = ctk.CTkFrame(main, fg_color="transparent")
        bf.pack(fill="x")
        styled.button_danger(bf, text="Annuler", icon="❌", width=110, height=36, command=fen.destroy).pack(side="left", padx=4)
        styled.button_success(bf, text="Valider", icon="✅", width=110, height=36, command=valider).pack(side="right", padx=4)
        charger()

    # ─────────────────────────────────────────────────────────────────────────
    # Ajouter / Supprimer article
    # ─────────────────────────────────────────────────────────────────────────
    def ajouter_article(self):
        if not self.article_selectionne:
            messagebox.showwarning("Attention", "Sélectionnez un article.")
            return
        if not self.fournisseur_id:
            messagebox.showwarning("Attention", "Sélectionnez un fournisseur.")
            return
        try:
            qtcmd = self.parser_nombre(self.entry_qtcmd.get())
            punitcmd = self.parser_nombre(self.entry_punitcmd.get())
            qtlivre = self.parser_nombre(self.entry_qtlivre.get())
            if qtcmd <= 0:
                messagebox.showwarning("Attention", "La quantité doit être > 0.")
                return
            date_p = self.entry_peremption.get_date().strftime('%d/%m/%Y') if self.var_has_peremption.get() else ""
            montant_charge = self.parser_nombre(self.entry_charge.get()) if self.var_has_charge.get() else 0
            total = qtcmd * punitcmd
            frs_nom = self.entry_fournisseur.get()

            self.tree.insert("", "end", values=(
                self.article_selectionne['nomart'], self.article_selectionne['unite'],
                self.formater_nombre(qtcmd), self.formater_nombre(punitcmd),
                self.formater_nombre(qtlivre), date_p, frs_nom
            ))
            self._refresh_table_alternating_colors(self.tree)

            self.items_commande.append({
                'idcomdetail': None, 'idarticle': self.article_selectionne['idarticle'],
                'idunite': self.article_selectionne['idunite'], 'idfrs': self.fournisseur_id,
                'nomfrs': frs_nom, 'qtcmd': qtcmd, 'punitcmd': punitcmd,
                'qtlivre': qtlivre, 'dateperemption': date_p or None, 'total': total,
                'montant_charge': montant_charge
            })

            for e in (self.entry_article, self.entry_unite):
                e.configure(state="normal"); e.delete(0, "end"); e.configure(state="readonly")
            self.entry_qtcmd.delete(0, "end")
            self.entry_punitcmd.delete(0, "end")
            self.entry_qtlivre.delete(0, "end")
            self.entry_qtlivre.insert(0, "0")
            self.toggle_frais_charge(False)
            self.toggle_date_peremption(False)
            self.article_selectionne = None
            self.label_total_ligne.configure(text="0,00")
            self.calculer_total()
            if self.idcom_charge: self.update_date_modification()
        except ValueError:
            messagebox.showerror("Erreur", "Données numériques invalides.")

    def supprimer_article(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Attention", "Sélectionnez une ligne à supprimer.")
            return
        if self.index_ligne_selectionnee is not None:
            self.annuler_selection_ligne()
        idx = self.tree.index(sel[0])
        self.tree.delete(sel[0])
        self._refresh_table_alternating_colors(self.tree)
        self.items_commande.pop(idx)
        self.calculer_total()

    def calculer_total(self):
        total = sum(i['qtcmd'] * i['punitcmd'] for i in self.items_commande)
        txt = self.formater_nombre(total)
        self.label_total.configure(text=f"Total : {txt}")
        self.label_total_global.configure(text=f"Total : {txt}")

    # ─────────────────────────────────────────────────────────────────────────
    # ENREGISTREMENT — avec proposition d'impression
    # ─────────────────────────────────────────────────────────────────────────
    def enregistrer_commande(self):
        if self.index_ligne_selectionnee is not None:
            messagebox.showwarning("Attention", "Validez ou annulez la modification en cours.")
            return
        if not self.items_commande:
            messagebox.showwarning("Attention", "La commande ne contient aucune ligne.")
            return
        if not self.fournisseur_id:
            messagebox.showwarning("Attention", "Sélectionnez un fournisseur.")
            return

        # Vérification transporteur si switch activé
        if self.var_transporteur.get() and not self.transporteur_id:
            messagebox.showwarning("Attention",
                                   "Le transporteur est activé mais aucun transporteur n'est sélectionné.\n"
                                   "Veuillez en choisir un ou désactiver l'option transporteur.")
            return

        total_commande = sum(i['qtcmd'] * i['punitcmd'] for i in self.items_commande)
        idtrans = self.transporteur_id if self.var_transporteur.get() else None

        conn = self.connect_db()
        if not conn: return
        try:
            cur = conn.cursor()

            if self.mode_modification and self.idcom_charge:
                # UPDATE
                cur.execute("""
                    UPDATE tb_commande SET refcom=%s, idfrs=NULL, descriptioncom=%s,
                    totcmd=%s, idtransportuer=%s WHERE idcom=%s
                """, (self.entry_ref.get(), "", total_commande, idtrans, self.idcom_charge))

                ids_existants = [i['idcomdetail'] for i in self.items_commande if i['idcomdetail']]
                cur.execute("SELECT id FROM tb_commandedetail WHERE idcom=%s", (self.idcom_charge,))
                all_ids = [r[0] for r in cur.fetchall()]
                to_del = [x for x in all_ids if x not in ids_existants]
                if to_del:
                    cur.execute("DELETE FROM tb_commandedetail WHERE id IN %s", (tuple(to_del),))

                for item in self.items_commande:
                    tl = item['qtcmd'] * item['punitcmd']
                    dp = self._format_date_db(item.get('dateperemption'))
                    if item['idcomdetail']:
                        cur.execute("""
                            UPDATE tb_commandedetail SET idarticle=%s, idunite=%s, idfrs=%s,
                            qtcmd=%s, qtlivre=%s, punitcmd=%s, total=%s, dateperemption=%s, montant_charge=%s WHERE id=%s
                        """, (item['idarticle'], item['idunite'], item.get('idfrs'),
                              item['qtcmd'], item['qtlivre'], item['punitcmd'], tl, dp,
                              item.get('montant_charge', 0), item['idcomdetail']))
                    else:
                        cur.execute("""
                            INSERT INTO tb_commandedetail (idcom, idarticle, idunite, idfrs, qtcmd, qtlivre, punitcmd, total, dateperemption, montant_charge)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """, (self.idcom_charge, item['idarticle'], item['idunite'], item.get('idfrs'),
                              item['qtcmd'], item['qtlivre'], item['punitcmd'], tl, dp,
                              item.get('montant_charge', 0)))
                conn.commit()
                ref_sauvee = self.entry_ref.get()
                messagebox.showinfo("Succès", f"Commande {ref_sauvee} modifiée avec succès !")

            else:
                # INSERT
                cur.execute("""
                    INSERT INTO tb_commande (refcom, datecom, iduser, idfrs, descriptioncom, datemodif, totcmd, deleted, idtransportuer)
                    VALUES (%s,%s,%s,NULL,'',%s,%s,0,%s) RETURNING idcom
                """, (self.entry_ref.get(), datetime.now(), self.iduser,
                      datetime.now(), total_commande, idtrans))
                idcom = cur.fetchone()[0]
                self.idcom_charge = idcom

                for item in self.items_commande:
                    tl = item['qtcmd'] * item['punitcmd']
                    dp = self._format_date_db(item.get('dateperemption'))
                    cur.execute("""
                        INSERT INTO tb_commandedetail (idcom, idarticle, idunite, idfrs, qtcmd, qtlivre, punitcmd, total, dateperemption, montant_charge)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (idcom, item['idarticle'], item['idunite'], item.get('idfrs'),
                          item['qtcmd'], item['qtlivre'], item['punitcmd'], tl, dp,
                          item.get('montant_charge', 0)))
                conn.commit()
                messagebox.showinfo("Succès", "Commande enregistrée avec succès !")

            # ── Proposition d'impression ──────────────────────────────────
            imprimer = YesNoDialog(
                "Impression",
                "La commande a été enregistrée.\n\nVoulez-vous imprimer le bon de commande ?"
            ).result
            if imprimer:
                self.imprimer_bon_commande()

            self.mode_modification = False
            self.reinitialiser_formulaire()
            self.appliquer_fournisseur_defaut_param()

        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur", f"Enregistrement : {e}")
        finally:
            if 'cur' in locals(): cur.close()
            if conn: conn.close()

    def _format_date_db(self, date_str):
        """Convertit JJ/MM/AAAA → AAAA-MM-JJ pour la DB."""
        if not date_str: return None
        try:
            if '/' in date_str:
                p = date_str.split('/')
                if len(p) == 3: return f"{p[2]}-{p[1]}-{p[0]}"
            return date_str
        except:
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # Réinitialisation
    # ─────────────────────────────────────────────────────────────────────────
    def reinitialiser_formulaire(self, generer_ref=True):
        if generer_ref: self.generer_reference()
        self.items_commande.clear()
        self.index_ligne_selectionnee = None
        self.article_selectionne = None
        self.idcom_charge = None
        for i in self.tree.get_children(): self.tree.delete(i)
        self._refresh_table_alternating_colors(self.tree)
        for e in (self.entry_article, self.entry_unite):
            e.configure(state="normal"); e.delete(0, "end"); e.configure(state="readonly")
        self.entry_qtcmd.delete(0, "end")
        self.entry_punitcmd.delete(0, "end")
        self.entry_qtlivre.delete(0, "end")
        self.entry_qtlivre.insert(0, "0")
        self.btn_ajouter.configure(state="normal")
        self.btn_modifier_ligne.configure(state="disabled", text="✏️  Modifier Ligne")
        self.btn_annuler_selection.configure(state="disabled")
        self.label_total_ligne.configure(text="0,00")
        self.toggle_frais_charge(False)
        self.toggle_date_peremption(False)
        # Réinitialiser transporteur
        self.var_transporteur.set(False)
        self.toggle_transporteur()
        self.calculer_total()

    def nouvelle_commande(self):
        self.reinitialiser_formulaire()
        self.mode_modification = False
        self.idcom_charge = None
        self.appliquer_fournisseur_defaut_param()

    # ─────────────────────────────────────────────────────────────────────────
    # IMPRESSION
    # ─────────────────────────────────────────────────────────────────────────
    def imprimer_bon_commande(self):
        if not self.idcom_charge and not self.items_commande:
            messagebox.showwarning("Attention", "Aucune commande à imprimer.")
            return

        conn = self.connect_db()
        if not conn: return

        info_societe = None
        fournisseur_info = {
            "nom": self.entry_fournisseur.get(),
            "contact": self.fournisseur_contact or "N/A",
            "adresse": self.fournisseur_adresse or "N/A"
        }
        transporteur_info = {"nom": "", "contact": "", "adresse": ""}

        try:
            cur = conn.cursor()
            cur.execute("SELECT nomsociete, villesociete, adressesociete, contactsociete, nifsociete, statsociete, cifsociete FROM tb_infosociete LIMIT 1")
            row = cur.fetchone()
            if row:
                info_societe = (row[0], row[1], "Siège Social:", row[2], row[3], row[1], row[4], row[5], row[6])

            if self.fournisseur_id:
                cur.execute("SELECT nomfrs, contactfrs, adressefrs FROM tb_fournisseur WHERE idfrs=%s", (self.fournisseur_id,))
                rf = cur.fetchone()
                if rf:
                    fournisseur_info = {"nom": rf[0], "contact": rf[1] or "N/A", "adresse": rf[2] or "N/A"}

            if self.transporteur_id:
                cur.execute("SELECT nom, contact, adresse FROM tb_transporteur WHERE idtransporteur=%s", (self.transporteur_id,))
                rt = cur.fetchone()
                if rt:
                    transporteur_info = {"nom": rt[0] or "", "contact": rt[1] or "", "adresse": rt[2] or ""}
        except Exception as e:
            messagebox.showerror("Erreur", f"Données impression : {e}")
        finally:
            cur.close(); conn.close()

        if not info_societe:
            info_societe = ("Société", "Ville", "Siège Social:", "Adresse", "Tél", "Ville", "NIF", "STAT", "CIF")

        lignes_html = ""
        montant_total = 0
        numero = 1

        for item in self.items_commande:
            total = item['qtcmd'] * item['punitcmd']
            montant_total += total
            conn2 = self.connect_db()
            designation, unite = "Article inconnu", "N/A"
            if conn2:
                try:
                    cur2 = conn2.cursor()
                    cur2.execute("""
                        SELECT a.designation, u.designationunite FROM tb_article a
                        INNER JOIN tb_unite u ON a.idarticle=u.idarticle
                        WHERE a.idarticle=%s AND u.idunite=%s
                    """, (item['idarticle'], item['idunite']))
                    r2 = cur2.fetchone()
                    if r2: designation, unite = r2[0], r2[1]
                    cur2.close()
                except: pass
                finally: conn2.close()

            lignes_html += f"""
            <tr>
                <td class="center">{numero}</td>
                <td>{escape(designation)}</td>
                <td class="center">{escape(unite)}</td>
                <td class="right">{self.formater_nombre(item['qtcmd'])}</td>
                {"<td class=\"right\">" + self.formater_nombre(item['punitcmd']) + "</td>" if total != 0 or True else ""}
                {"<td class=\"right\">" + self.formater_nombre(total) + "</td>" if total != 0 or True else ""}
            </tr>"""
            numero += 1

        afficher_montants = montant_total != 0
        if not afficher_montants:
            # Reconstruire les lignes sans colonnes prix/montant
            lignes_html = ""
            numero = 1
            for item in self.items_commande:
                conn2 = self.connect_db()
                designation, unite = "Article inconnu", "N/A"
                if conn2:
                    try:
                        cur2 = conn2.cursor()
                        cur2.execute("""
                            SELECT a.designation, u.designationunite FROM tb_article a
                            INNER JOIN tb_unite u ON a.idarticle=u.idarticle
                            WHERE a.idarticle=%s AND u.idunite=%s
                        """, (item['idarticle'], item['idunite']))
                        r2 = cur2.fetchone()
                        if r2:
                            designation, unite = r2[0], r2[1]
                        cur2.close()
                    except:
                        pass
                    finally:
                        conn2.close()
                lignes_html += f"""
                <tr>
                    <td class="center">{numero}</td>
                    <td>{escape(designation)}</td>
                    <td class="center">{escape(unite)}</td>
                    <td class="right">{self.formater_nombre(item['qtcmd'])}</td>
                </tr>"""
                numero += 1

        total_lettres = self.nombre_en_lettres(montant_total)

        montant_cols_header_html = ""
        montant_cols_row_html = ""
        total_row_html = ""
        montant_lettres_html = ""
        if afficher_montants:
            montant_cols_header_html = """
    <th style="width:120px" class="right">Prix Unitaire</th>
    <th style="width:120px" class="right">Total</th>"""
            montant_cols_row_html_template = """
                <td class="right">{prix}</td>
                <td class="right">{total}</td>"""
            # Injection des colonnes montant dans les lignes déjà construites
            lignes_html = ""
            numero = 1
            for item in self.items_commande:
                total = item['qtcmd'] * item['punitcmd']
                conn2 = self.connect_db()
                designation, unite = "Article inconnu", "N/A"
                if conn2:
                    try:
                        cur2 = conn2.cursor()
                        cur2.execute("""
                            SELECT a.designation, u.designationunite FROM tb_article a
                            INNER JOIN tb_unite u ON a.idarticle=u.idarticle
                            WHERE a.idarticle=%s AND u.idunite=%s
                        """, (item['idarticle'], item['idunite']))
                        r2 = cur2.fetchone()
                        if r2:
                            designation, unite = r2[0], r2[1]
                        cur2.close()
                    except:
                        pass
                    finally:
                        conn2.close()
                montant_cols_row_html = montant_cols_row_html_template.format(
                    prix=self.formater_nombre(item['punitcmd']),
                    total=self.formater_nombre(total)
                )
                lignes_html += f"""
                <tr>
                    <td class="center">{numero}</td>
                    <td>{escape(designation)}</td>
                    <td class="center">{escape(unite)}</td>
                    <td class="right">{self.formater_nombre(item['qtcmd'])}</td>
                    {montant_cols_row_html}
                </tr>"""
                numero += 1

            total_row_html = f"""
<tr class="total-row">
    <td colspan="5" style="text-align:right">MONTANT TOTAL (Ariary)</td>
    <td class="right">{self.formater_nombre(montant_total)}</td>
</tr>"""
            montant_lettres_html = f"""
<div class="montant-lettres"><strong>En lettres :</strong> {total_lettres}</div>"""

        # Bloc transporteur dans le HTML (si présent)
        transporteur_html = ""
        if self.var_transporteur.get() and transporteur_info['nom']:
            transporteur_html = f"""
            <div class="info-box">
                <h3>Transporteur</h3>
                <p><strong>Nom:</strong> {escape(transporteur_info['nom'])}</p>
                <p><strong>Adresse:</strong> {escape(transporteur_info['adresse'])}</p>
                <p><strong>Contact:</strong> {escape(transporteur_info['contact'])}</p>
            </div>"""

        html_content = f"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<title>Bon de Commande - {self.entry_ref.get()}</title>
<style>
@page {{ size: A4; margin: 10mm; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:Arial,sans-serif; font-size:11pt; line-height:1.4; color:#000; background:white; position:relative; }}
body::before {{ content:'BC'; position:fixed; top:50%; left:50%; transform:translate(-50%,-50%) rotate(-45deg);
    font-size:300px; font-weight:bold; color:rgba(0,0,0,0.04); z-index:-1; }}
.container {{ width:100%; max-width:210mm; margin:0 auto; background:white; }}
.header {{ display:flex; justify-content:space-between; margin-bottom:18px; padding-bottom:12px; border-bottom:3px solid #2C3E50; }}
.logo {{ font-size:26px; font-weight:bold; color:#2C3E50; margin-bottom:4px; }}
.company-info {{ font-size:9pt; line-height:1.4; }}
.title {{ text-align:center; margin:20px 0; }}
.title h1 {{ font-size:22pt; font-weight:bold; color:#2C3E50; text-transform:uppercase; letter-spacing:2px; }}
.info-section {{ display:flex; gap:12px; margin-bottom:18px; flex-wrap:wrap; }}
.info-box {{ flex:1; min-width:180px; border:2px solid #2C3E50; padding:10px; background:#f9f9f9; border-radius:4px; }}
.info-box h3 {{ font-size:11pt; font-weight:bold; margin-bottom:6px; color:#2C3E50; border-bottom:1px solid #2C3E50; padding-bottom:3px; }}
.info-box p {{ font-size:10pt; margin:2px 0; }}
table {{ width:100%; border-collapse:collapse; margin-top:16px; }}
table th, table td {{ border:1px solid #BDC3C7; padding:7px; text-align:left; }}
table th {{ background:#2C3E50; color:#fff; font-size:9.5pt; text-transform:uppercase; }}
.right {{ text-align:right; }} .center {{ text-align:center; }}
.total-row td {{ font-weight:bold; background:#ECF0F1; }}
.montant-lettres {{ margin-top:16px; font-size:10.5pt; font-style:italic; padding:8px; border:1px solid #ECF0F1; border-radius:4px; background:#f9f9f9; }}
.signatures {{ display:flex; justify-content:space-between; margin-top:36px; }}
.signature-box {{ width:44%; text-align:center; }}
.signature-box .sig-title {{ font-weight:bold; font-size:11pt; margin-bottom:50px; text-decoration:underline; }}
</style>
</head>
<body><div class="container">
<div class="header">
<div>
    <div class="logo">{escape(str(info_societe[0] or ''))}</div>
    <div class="company-info">
        <strong>{escape(str(info_societe[2] or ''))}</strong><br>
        {escape(str(info_societe[3] or ''))}<br>
        {escape(str(info_societe[5] or ''))} — Tél: {escape(str(info_societe[4] or ''))}<br>
        <strong>NIF:</strong> {escape(str(info_societe[6] or ''))} | <strong>STAT:</strong> {escape(str(info_societe[7] or ''))} | <strong>CIF:</strong> {escape(str(info_societe[8] or ''))}
    </div>
</div>
<div class="company-info" style="text-align:right">{escape(str(info_societe[1] or ''))}</div>
</div>

<div class="title"><h1>Bon de Commande</h1></div>

<div class="info-section">
<div class="info-box">
    <h3>Fournisseur</h3>
    <p><strong>Nom:</strong> {escape(fournisseur_info['nom'])}</p>
    <p><strong>Adresse:</strong> {escape(fournisseur_info['adresse'])}</p>
    <p><strong>Tél:</strong> {escape(fournisseur_info['contact'])}</p>
</div>
<div class="info-box">
    <h3>Informations Commande</h3>
    <p><strong>Référence:</strong> {escape(self.entry_ref.get())}</p>
    <p><strong>Date:</strong> {datetime.now().strftime('%d/%m/%Y')}</p>
    <p><strong>État:</strong> En attente</p>
</div>
{transporteur_html}
</div>

<table>
<thead><tr>
    <th style="width:44px" class="center">N°</th>
    <th>Désignation</th>
    <th style="width:76px" class="center">Unité</th>
    <th style="width:110px" class="right">Quantité</th>
    {montant_cols_header_html}
</tr></thead>
<tbody>
{lignes_html}
{total_row_html}
</tbody>
</table>

{montant_lettres_html}

<div class="signatures">
<div class="signature-box"><div class="sig-title">Le Responsable</div></div>
<div class="signature-box"><div class="sig-title">Le Fournisseur</div></div>
</div>
</div></body></html>"""

        self._ouvrir_navigateur(html_content)

    def _ouvrir_navigateur(self, html_content):
        import tempfile, webbrowser, os
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.html', encoding='utf-8') as f:
            f.write(html_content)
            path = f.name
        webbrowser.open('file://' + os.path.abspath(path))
        MessageDialog(
            "Impression",
            "Le bon de commande est ouvert dans votre navigateur.\nUtilisez Ctrl+P pour imprimer.",
            "info",
        )


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from app_theme import init_theme
    init_theme()
    app = ctk.CTk()
    app.geometry("1280x820")
    app.title("Commande Fournisseur — iJeery")
    Theme.apply(app)
    page = PageCommandeFrs(app, iduser=1)
    page.pack(fill="both", expand=True)
    app.mainloop()
