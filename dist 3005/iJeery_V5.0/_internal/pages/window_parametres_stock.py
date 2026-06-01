# -*- coding: utf-8 -*-
"""Fenêtre Paramètres — Gestion des stocks (autorisation inventaire)."""

from __future__ import annotations

import threading
from typing import Callable, Dict, List, Optional, Tuple

import customtkinter as ctk
from tkinter import messagebox

from app_theme import Colors, Fonts, Layout, styled

try:
    from db import ensure_connection, get_connection
except ImportError:
    from db import ensure_connection, get_connection

try:
    from pages.stock_config import (
        get_fonctions_autorisees_inventaire,
        set_fonctions_autorisees_inventaire,
    )
except ImportError:
    from stock_config import (
        get_fonctions_autorisees_inventaire,
        set_fonctions_autorisees_inventaire,
    )


class ParametresStockWindow(ctk.CTkToplevel):
    """Autorisation par fonction : double-clic stock → inventaire article."""

    def __init__(
        self,
        master,
        db_conn=None,
        id_user: Optional[int] = None,
        on_saved: Optional[Callable[[], None]] = None,
    ):
        super().__init__(master)
        self._db_conn = db_conn
        self._id_user = id_user
        self._on_saved = on_saved
        self._fonctions: List[Tuple[int, str]] = []
        self._checks: Dict[int, ctk.CTkCheckBox] = {}

        self.title("Paramètres — Gestion des stocks")
        self.configure(fg_color=Colors.BG_PAGE)
        w, h = 560, 480
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        self.transient(master.winfo_toplevel())
        self.grab_set()

        self._build_ui()
        self._charger_fonctions()

    def _connect_db(self):
        try:
            conn = self._db_conn or get_connection()
            return ensure_connection(conn)
        except Exception as err:
            messagebox.showerror(
                "Erreur de connexion", f"Connexion impossible : {err}", parent=self,
            )
            return None

    def _build_ui(self):
        hdr = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT, corner_radius=0, height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(
            hdr,
            text="⚙  Paramètres — Gestion des stocks",
            font=Fonts.title(15),
            text_color=Colors.TEXT_ON_DARK,
        ).pack(side="left", padx=16)

        body = ctk.CTkScrollableFrame(self, fg_color=Colors.BG_PAGE, corner_radius=0)
        body.pack(fill="both", expand=True, padx=14, pady=12)

        card = styled.card(body)
        card.pack(fill="x", pady=(0, 12))
        inner = styled.frame(card, color="transparent")
        inner.pack(fill="x", padx=14, pady=14)

        styled.label(
            inner, text="Autorisation inventaire (double-clic)", size=14, weight="bold",
        ).pack(anchor="w")

        styled.label_muted(
            inner,
            text=(
                "Cochez les fonctions utilisateur autorisées à double-cliquer une ligne "
                "du stock article pour ouvrir la fenêtre d'inventaire.\n\n"
                "Si aucune case n'est cochée (liste vide enregistrée), toutes les fonctions "
                "restent autorisées."
            ),
            size=10,
        ).pack(anchor="w", pady=(6, 12))

        self._frame_checks = styled.frame(inner, color="transparent")
        self._frame_checks.pack(fill="x")

        self._lbl_chargement = styled.label_muted(
            self._frame_checks, text="Chargement des fonctions…", size=10,
        )
        self._lbl_chargement.pack(anchor="w")

        styled.label_muted(
            body,
            text="Enregistré dans settings.json (section StockArticle).",
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

    def _charger_fonctions(self):
        def worker():
            conn = self._connect_db()
            if not conn:
                return
            rows: List[Tuple[int, str]] = []
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT idfonction, designationfonction
                    FROM tb_fonction
                    WHERE COALESCE(deleted, 0) = 0
                    ORDER BY designationfonction
                    """
                )
                rows = [(int(r[0]), str(r[1] or "")) for r in cur.fetchall()]
                cur.close()
            except Exception as e:
                self.after(
                    0,
                    lambda: messagebox.showerror("Erreur", str(e), parent=self),
                )
                return
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

            allowed = get_fonctions_autorisees_inventaire()

            def apply():
                if not self.winfo_exists():
                    return
                self._fonctions = rows
                self._checks.clear()
                if self._lbl_chargement.winfo_exists():
                    self._lbl_chargement.destroy()

                for fid, label in rows:
                    chk = ctk.CTkCheckBox(
                        self._frame_checks,
                        text=label,
                        font=ctk.CTkFont(size=12),
                        checkbox_width=20,
                        checkbox_height=20,
                    )
                    chk.pack(anchor="w", pady=3)
                    if allowed is None:
                        chk.deselect()
                    elif fid in allowed:
                        chk.select()
                    else:
                        chk.deselect()
                    self._checks[fid] = chk

                if not rows:
                    styled.label_muted(
                        self._frame_checks,
                        text="Aucune fonction trouvée dans tb_fonction.",
                        size=10,
                    ).pack(anchor="w")

            self.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    def _enregistrer(self):
        ids = [fid for fid, chk in self._checks.items() if chk.get()]
        if not set_fonctions_autorisees_inventaire(ids):
            messagebox.showerror(
                "Erreur",
                "Impossible d'enregistrer dans settings.json.",
                parent=self,
            )
            return
        if ids:
            msg = f"{len(ids)} fonction(s) autorisée(s) au double-clic inventaire."
        else:
            msg = (
                "Aucune restriction : toutes les fonctions sont autorisées "
                "au double-clic inventaire."
            )
        messagebox.showinfo("Paramètres", msg, parent=self)
        if self._on_saved:
            self._on_saved()
        self.destroy()
