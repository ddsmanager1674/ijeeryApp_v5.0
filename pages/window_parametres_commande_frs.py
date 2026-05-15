# -*- coding: utf-8 -*-
"""Fenêtre Paramètres — Bon de commande fournisseur."""

from __future__ import annotations

import threading
from typing import Callable, List, Optional, Tuple

import customtkinter as ctk
from tkinter import messagebox

from app_theme import Colors, Fonts, Layout, styled

try:
    from pages.commande_frs_common import (
        CommandeFrsDB,
        fournisseur_nom_par_id,
    )
except ImportError:
    from commande_frs_common import (
        CommandeFrsDB,
        fournisseur_nom_par_id,
    )


class ParametresCommandeFrsWindow(ctk.CTkToplevel):
    """Paramètres du bon de commande (fournisseur par défaut, etc.)."""

    def __init__(
        self,
        master,
        id_user: Optional[int] = None,
        on_saved: Optional[Callable[[], None]] = None,
    ):
        super().__init__(master)
        self._id_user = id_user
        self._on_saved = on_saved
        self._fournisseurs: List[Tuple[int, str]] = []

        self.title("Paramètres — Bon de commande")
        self.configure(fg_color=Colors.BG_PAGE)
        w, h = 520, 320
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        self.transient(master.winfo_toplevel())
        self.grab_set()

        self._build_ui()
        self._charger_donnees()

    def _build_ui(self):
        hdr = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT, corner_radius=0, height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(
            hdr,
            text="⚙  Paramètres — Bon de commande",
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

        styled.label(inner, text="Fournisseur par défaut", size=14, weight="bold").grid(
            row=0, column=0, sticky="w",
        )
        styled.label_muted(
            inner,
            text=(
                "Fournisseur pré-affiché dans le champ fournisseur à l'ouverture "
                "d'un nouveau bon de commande (enregistré en base)."
            ),
            size=10,
        ).grid(row=1, column=0, sticky="w", pady=(4, 8))

        self.combo_frs_defaut = styled.combobox(
            inner, values=["— Aucun —"], height=Layout.INPUT_H,
        )
        self.combo_frs_defaut.grid(row=2, column=0, sticky="ew")

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

    def _charger_donnees(self):
        def worker():
            conn = CommandeFrsDB.get_conn()
            if not conn:
                return
            try:
                cur = conn.cursor()
                fournisseurs = CommandeFrsDB.fetch_fournisseurs(cur)
                param = CommandeFrsDB.fetch_param_commande_frs(cur)
                id_def = param.get("idfrs_defaut")
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Erreur", str(e), parent=self))
                return
            finally:
                CommandeFrsDB.release_conn(conn)

            def apply():
                if not self.winfo_exists():
                    return
                self._fournisseurs = fournisseurs
                noms = ["— Aucun —"] + [n for _i, n in fournisseurs]
                self.combo_frs_defaut.configure(values=noms)
                self.combo_frs_defaut.set(
                    fournisseur_nom_par_id(fournisseurs, id_def),
                )

            self.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    def _enregistrer(self):
        def worker():
            conn = CommandeFrsDB.get_conn()
            if not conn:
                return
            try:
                cur = conn.cursor()
                sel = self.combo_frs_defaut.get()
                id_frs = None
                if sel and sel != "— Aucun —":
                    for fid, nom in self._fournisseurs:
                        if nom == sel:
                            id_frs = fid
                            break
                CommandeFrsDB.save_param_commande_frs(cur, id_frs)
                conn.commit()
            except Exception as e:
                conn.rollback()
                err = str(e)
                self.after(
                    0,
                    lambda: messagebox.showerror("Erreur", err, parent=self),
                )
                return
            finally:
                CommandeFrsDB.release_conn(conn)

            def done():
                if not self.winfo_exists():
                    return
                messagebox.showinfo(
                    "Paramètres",
                    "Paramètres enregistrés.",
                    parent=self,
                )
                if self._on_saved:
                    self._on_saved()
                self.destroy()

            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()
