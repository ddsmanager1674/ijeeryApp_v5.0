# -*- coding: utf-8 -*-
"""Fenêtre Configuration — Liste mouvements (settings.json, par utilisateur)."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

import customtkinter as ctk
from tkinter import messagebox

from app_theme import Colors, Fonts, Layout, styled

try:
    from pages.liste_mouvements_config import (
        get_menu_defaut_liste_mouvements,
        get_sidebar_hamburger_defaut_liste,
        set_menu_defaut_liste_mouvements,
        set_sidebar_hamburger_defaut_liste,
    )
except ImportError:
    from liste_mouvements_config import (
        get_menu_defaut_liste_mouvements,
        get_sidebar_hamburger_defaut_liste,
        set_menu_defaut_liste_mouvements,
        set_sidebar_hamburger_defaut_liste,
    )


class ConfigurationListeMouvementsWindow(ctk.CTkToplevel):
    """Configuration personnelle — Liste mouvements."""

    def __init__(
        self,
        master,
        id_user: Optional[int] = None,
        menus_visibles: Optional[List[Tuple[str, str]]] = None,
        menu_actif: Optional[str] = None,
        on_saved: Optional[Callable[[], None]] = None,
    ):
        super().__init__(master)
        self._id_user = id_user
        self._menus_visibles = list(menus_visibles or [])
        self._menu_actif = menu_actif
        self._on_saved = on_saved
        self._cle_par_label: Dict[str, str] = {lbl: cle for cle, lbl in self._menus_visibles}

        self.title("Configuration — Liste mouvements")
        self.configure(fg_color=Colors.BG_PAGE)
        w, h = 540, 480
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
            text="🔧  Configuration — Liste mouvements",
            font=Fonts.title(15),
            text_color=Colors.TEXT_ON_DARK,
        ).pack(side="left", padx=16)

        body = ctk.CTkScrollableFrame(self, fg_color=Colors.BG_PAGE, corner_radius=0)
        body.pack(fill="both", expand=True, padx=14, pady=12)

        card_menu = styled.card(body)
        card_menu.pack(fill="x", pady=(0, 12))
        inner_m = styled.frame(card_menu, color="transparent")
        inner_m.pack(fill="x", padx=14, pady=14)
        inner_m.grid_columnconfigure(0, weight=1)

        styled.label(inner_m, text="Choix de menu par défaut", size=14, weight="bold").grid(
            row=0, column=0, sticky="w",
        )
        styled.label_muted(
            inner_m,
            text=(
                "Type de mouvement affiché à l'ouverture de « Liste mouvements ». "
                "Seuls les menus visibles dans la barre latérale sont proposés."
            ),
            size=10,
        ).grid(row=1, column=0, sticky="w", pady=(4, 8))

        labels = [lbl for _cle, lbl in self._menus_visibles]
        if not labels:
            styled.label_muted(inner_m, text="Aucun menu disponible.", size=11).grid(
                row=2, column=0, sticky="w",
            )
            self.combo_menu = None
        else:
            self.combo_menu = styled.combobox(
                inner_m, values=labels, height=Layout.INPUT_H,
            )
            self.combo_menu.grid(row=2, column=0, sticky="ew")

        card_side = styled.card(body)
        card_side.pack(fill="x", pady=(0, 12))
        inner_s = styled.frame(card_side, color="transparent")
        inner_s.pack(fill="x", padx=14, pady=14)
        inner_s.grid_columnconfigure(0, weight=1)

        styled.label(inner_s, text="Barre latérale", size=14, weight="bold").grid(
            row=0, column=0, sticky="w",
        )
        styled.label_muted(
            inner_s,
            text="Mode hamburger : barre repliée (icônes seules). Décoché : libellés visibles.",
            size=10,
        ).grid(row=1, column=0, sticky="w", pady=(4, 8))

        self.chk_hamburger = ctk.CTkCheckBox(
            inner_s,
            text="Activer le mode hamburger par défaut",
            font=ctk.CTkFont(size=12),
            checkbox_width=20,
            checkbox_height=20,
        )
        self.chk_hamburger.grid(row=2, column=0, sticky="w")

        styled.label_muted(
            body,
            text="Enregistré dans settings.json (section ListeMouvements, par utilisateur).",
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
            pref = get_menu_defaut_liste_mouvements(self._id_user)
            label_pref = next(
                (lbl for cle, lbl in self._menus_visibles if cle == pref),
                None,
            )
            if label_pref:
                self.combo_menu.set(label_pref)
            elif self._menu_actif:
                label_actif = next(
                    (lbl for cle, lbl in self._menus_visibles if cle == self._menu_actif),
                    None,
                )
                if label_actif:
                    self.combo_menu.set(label_actif)
                else:
                    self.combo_menu.set(self._menus_visibles[0][1])
            else:
                self.combo_menu.set(self._menus_visibles[0][1])
        if get_sidebar_hamburger_defaut_liste(self._id_user, default=True):
            self.chk_hamburger.select()
        else:
            self.chk_hamburger.deselect()

    def _enregistrer(self):
        if self.combo_menu and self._menus_visibles:
            sel = (self.combo_menu.get() or "").strip()
            cle = self._cle_par_label.get(sel)
            if not cle:
                messagebox.showwarning(
                    "Configuration",
                    "Sélectionnez un type de mouvement.",
                    parent=self,
                )
                return
            if not set_menu_defaut_liste_mouvements(self._id_user, cle):
                messagebox.showerror(
                    "Erreur",
                    "Impossible d'enregistrer le menu dans settings.json.",
                    parent=self,
                )
                return
        if not set_sidebar_hamburger_defaut_liste(
            self._id_user, bool(self.chk_hamburger.get()),
        ):
            messagebox.showerror(
                "Erreur",
                "Impossible d'enregistrer la barre latérale dans settings.json.",
                parent=self,
            )
            return
        messagebox.showinfo("Configuration", "Configuration enregistrée.", parent=self)
        if self._on_saved:
            self._on_saved()
        self.destroy()
