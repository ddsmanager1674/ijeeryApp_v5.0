# -*- coding: utf-8 -*-
"""Fenêtre Configuration — Prix Article (settings.json, par utilisateur)."""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk
from tkinter import messagebox

from app_theme import Colors, Fonts, Layout, styled

try:
    from pages.prix_article_config import (
        get_afficher_variation_prix_defaut,
        set_afficher_variation_prix_defaut,
    )
except ImportError:
    from prix_article_config import (
        get_afficher_variation_prix_defaut,
        set_afficher_variation_prix_defaut,
    )


class ConfigurationPrixArticleWindow(ctk.CTkToplevel):
    """Configuration personnelle — affichage variation des prix."""

    def __init__(
        self,
        master,
        id_user: Optional[int] = None,
        on_saved: Optional[Callable[[], None]] = None,
    ):
        super().__init__(master)
        self._id_user = id_user
        self._on_saved = on_saved

        self.title("Configuration — Prix Article")
        self.configure(fg_color=Colors.BG_PAGE)
        w, h = 520, 320
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        self.transient(master.winfo_toplevel())
        self.grab_set()

        self._build_ui()
        self._charger_valeurs()

    def _build_ui(self):
        hdr = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT, corner_radius=0, height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(
            hdr,
            text="🔧  Configuration — Prix Article",
            font=Fonts.title(15),
            text_color=Colors.TEXT_ON_DARK,
        ).pack(side="left", padx=16)

        body = ctk.CTkScrollableFrame(self, fg_color=Colors.BG_PAGE, corner_radius=0)
        body.pack(fill="both", expand=True, padx=14, pady=12)

        card = styled.card(body)
        card.pack(fill="x", pady=(0, 12))
        inner = styled.frame(card, color="transparent")
        inner.pack(fill="x", padx=14, pady=14)
        inner.grid_columnconfigure(0, weight=1)

        styled.label(inner, text="Variation des prix", size=14, weight="bold").grid(
            row=0, column=0, sticky="w",
        )
        styled.label_muted(
            inner,
            text=(
                "À l'ouverture de « Prix Article », coche automatiquement "
                "« Afficher la variation du prix » (colonnes min–max et moyenne)."
            ),
            size=10,
        ).grid(row=1, column=0, sticky="w", pady=(4, 8))

        self.chk_variation = ctk.CTkCheckBox(
            inner,
            text="Afficher la variation du prix par défaut",
            font=ctk.CTkFont(size=12),
            checkbox_width=20,
            checkbox_height=20,
        )
        self.chk_variation.grid(row=2, column=0, sticky="w")

        styled.label_muted(
            body,
            text="Enregistré dans settings.json (section PrixArticle, par utilisateur).",
            size=10,
        ).pack(anchor="w", padx=4)

        foot = styled.frame(self, color="transparent")
        foot.pack(fill="x", padx=14, pady=(0, 14))

        styled.button_success(
            foot, text="Enregistrer", width=120, height=Layout.BTN_H,
            command=self._enregistrer,
        ).pack(side="right", padx=(8, 0))
        styled.button_secondary(
            foot, text="Annuler", width=100, height=Layout.BTN_H,
            command=self.destroy,
        ).pack(side="right")

    def _charger_valeurs(self):
        if get_afficher_variation_prix_defaut(self._id_user, default=False):
            self.chk_variation.select()
        else:
            self.chk_variation.deselect()

    def _enregistrer(self):
        if not set_afficher_variation_prix_defaut(
            self._id_user,
            bool(self.chk_variation.get()),
        ):
            messagebox.showerror(
                "Erreur",
                "Impossible d'enregistrer dans settings.json.",
                parent=self,
            )
            return
        messagebox.showinfo(
            "Configuration", "Configuration enregistrée.", parent=self,
        )
        if self._on_saved:
            self._on_saved()
        self.destroy()
