# -*- coding: utf-8 -*-
"""Fenêtre Configuration — Mouvement de stock (settings.json, par utilisateur)."""

from __future__ import annotations

from typing import Callable, List, Optional

import customtkinter as ctk
from tkinter import messagebox

from app_theme import Colors, Fonts, Layout, styled

try:
    from pages.mouvement_stock_config import (
        get_menu_defaut_mouvement_stock,
        get_sidebar_hamburger_defaut,
        set_menu_defaut_mouvement_stock,
        set_sidebar_hamburger_defaut,
    )
except ImportError:
    from mouvement_stock_config import (
        get_menu_defaut_mouvement_stock,
        get_sidebar_hamburger_defaut,
        set_menu_defaut_mouvement_stock,
        set_sidebar_hamburger_defaut,
    )


class ConfigurationMouvementStockWindow(ctk.CTkToplevel):
    """Configuration personnelle du module Mouvement de stock."""

    def __init__(
        self,
        master,
        id_user: Optional[int] = None,
        menus_visibles: Optional[List[str]] = None,
        menu_actuel: Optional[str] = None,
        on_saved: Optional[Callable[[], None]] = None,
    ):
        super().__init__(master)
        self._id_user = id_user
        self._menus_visibles = list(menus_visibles or [])
        self._menu_actuel = menu_actuel
        self._on_saved = on_saved

        self.title("Configuration — Mouvement de stock")
        self.configure(fg_color=Colors.BG_PAGE)
        w, h = 540, 430
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
            text="🔧  Configuration — Mouvement de stock",
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

        styled.label(inner, text="Choix de menu par défaut", size=14, weight="bold").grid(
            row=0, column=0, sticky="w",
        )
        styled.label_muted(
            inner,
            text=(
                "Sous-menu ouvert automatiquement à l'entrée dans « Mouvement de stock ». "
                "Seuls les menus actuellement visibles dans la barre latérale sont proposés "
                "(les autorisations utilisateur pourront filtrer cette liste plus tard)."
            ),
            size=10,
        ).grid(row=1, column=0, sticky="w", pady=(4, 8))

        if not self._menus_visibles:
            styled.label_muted(
                inner, text="Aucun menu disponible.", size=11,
            ).grid(row=2, column=0, sticky="w")
            self.combo_menu = None
        else:
            self.combo_menu = styled.combobox(
                inner,
                values=self._menus_visibles,
                height=Layout.INPUT_H,
            )
            self.combo_menu.grid(row=2, column=0, sticky="ew")

        card_side = styled.card(body)
        card_side.pack(fill="x", pady=(0, 12))
        inner_side = styled.frame(card_side, color="transparent")
        inner_side.pack(fill="x", padx=14, pady=14)
        inner_side.grid_columnconfigure(0, weight=1)

        styled.label(inner_side, text="Barre latérale", size=14, weight="bold").grid(
            row=0, column=0, sticky="w",
        )
        styled.label_muted(
            inner_side,
            text="Mode hamburger : barre repliée avec icônes seules. Décoché : libellés visibles.",
            size=10,
        ).grid(row=1, column=0, sticky="w", pady=(4, 8))

        self.chk_hamburger = ctk.CTkCheckBox(
            inner_side,
            text="Activer le mode hamburger par défaut",
            font=ctk.CTkFont(size=12),
            checkbox_width=20,
            checkbox_height=20,
        )
        self.chk_hamburger.grid(row=2, column=0, sticky="w")

        styled.label_muted(
            body,
            text="Enregistré dans settings.json (section MouvementStock, par utilisateur).",
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
        if self.combo_menu and self._menus_visibles:
            pref = get_menu_defaut_mouvement_stock(self._id_user)
            if pref and pref in self._menus_visibles:
                self.combo_menu.set(pref)
            elif self._menu_actuel and self._menu_actuel in self._menus_visibles:
                self.combo_menu.set(self._menu_actuel)
            else:
                self.combo_menu.set(self._menus_visibles[0])
        if get_sidebar_hamburger_defaut(self._id_user, default=True):
            self.chk_hamburger.select()
        else:
            self.chk_hamburger.deselect()

    def _enregistrer(self):
        if self.combo_menu and self._menus_visibles:
            sel = (self.combo_menu.get() or "").strip()
            if sel not in self._menus_visibles:
                messagebox.showwarning(
                    "Configuration",
                    "Sélectionnez un menu dans la liste.",
                    parent=self,
                )
                return
            if not set_menu_defaut_mouvement_stock(self._id_user, sel):
                messagebox.showerror(
                    "Erreur",
                    "Impossible d'enregistrer le menu dans settings.json.",
                    parent=self,
                )
                return
        hamburger = bool(self.chk_hamburger.get())
        if not set_sidebar_hamburger_defaut(self._id_user, hamburger):
            messagebox.showerror(
                "Erreur",
                "Impossible d'enregistrer la barre latérale dans settings.json.",
                parent=self,
            )
            return
        messagebox.showinfo(
            "Configuration",
            "Configuration enregistrée.",
            parent=self,
        )
        if self._on_saved:
            self._on_saved()
        self.destroy()
