# -*- coding: utf-8 -*-
"""Fenêtre Paramètres — Bon de livraison."""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional, Tuple

import customtkinter as ctk
from tkinter import messagebox

from app_theme import Colors, Fonts, Layout, styled

try:
    from pages.livraison_common import (
        LivraisonDB,
        transporteur_nom_par_id,
        transporteur_pour_bl_auto_depuis_param,
    )
except ImportError:
    from livraison_common import (
        LivraisonDB,
        transporteur_nom_par_id,
        transporteur_pour_bl_auto_depuis_param,
    )


class ParametresLivraisonWindow(ctk.CTkToplevel):
    """Paramètres livraison auto par magasin + transporteur par défaut."""

    def __init__(
        self,
        master,
        id_user: Optional[int] = None,
        on_saved: Optional[Callable[[], None]] = None,
    ):
        super().__init__(master)
        self._id_user = id_user
        self._on_saved = on_saved
        self._magasin_rows: List[Tuple[int, str, bool]] = []
        self._transporteurs: List[Tuple[int, str]] = []
        self._switches: Dict[int, ctk.CTkSwitch] = {}

        self.title("Paramètres — Bon de livraison")
        self.configure(fg_color=Colors.BG_PAGE)
        w, h = 620, 560
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
            text="⚙  Paramètres — Bon de livraison",
            font=Fonts.title(15),
            text_color=Colors.TEXT_ON_DARK,
        ).pack(side="left", padx=16)

        body = ctk.CTkScrollableFrame(self, fg_color=Colors.BG_PAGE, corner_radius=0)
        body.pack(fill="both", expand=True, padx=14, pady=12)

        # ── Panel Livraison auto ─────────────────────────────────────────────
        card_auto = styled.card(body)
        card_auto.pack(fill="x", pady=(0, 12))
        inner_a = styled.frame(card_auto, color="transparent")
        inner_a.pack(fill="x", padx=14, pady=14)

        styled.label(inner_a, text="Livraison auto", size=14, weight="bold").pack(anchor="w")
        styled.label_muted(
            inner_a,
            text=(
                "Par magasin : si activé, les restes à livrer sont enregistrés automatiquement "
                "dans tb_livraisoncli sous un BL « {année}-BL-AUTO-##### » (un BL par facture, "
                "lignes du magasin concerné, quantité = reste à livrer).\n"
                "Les magasins en mode manuel restent visibles dans la liste d'attente du Bon de livraison."
            ),
            size=10,
        ).pack(anchor="w", pady=(6, 10))

        self._frame_magasins = styled.frame(inner_a, color="transparent")
        self._frame_magasins.pack(fill="x")

        # ── Panel Transporteur ─────────────────────────────────────────────────
        card_trans = styled.card(body)
        card_trans.pack(fill="x", pady=(0, 12))
        inner_t = styled.frame(card_trans, color="transparent")
        inner_t.pack(fill="x", padx=14, pady=14)
        inner_t.grid_columnconfigure(0, weight=1)

        styled.label(inner_t, text="Transporteur par défaut", size=14, weight="bold").grid(
            row=0, column=0, sticky="w",
        )
        styled.label_muted(
            inner_t,
            text="Pré-sélectionné à la création d'un BL manuel (enregistré en base). "
                 "Laissez « Aucun » si inutile.",
            size=10,
        ).grid(row=1, column=0, sticky="w", pady=(4, 8))

        self.combo_trans_defaut = styled.combobox(
            inner_t, values=["— Aucun —"], height=Layout.INPUT_H,
        )
        self.combo_trans_defaut.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        self.chk_transporteur_bl_auto = ctk.CTkCheckBox(
            inner_t,
            text="Transporteur BL-auto",
            font=ctk.CTkFont(size=12),
            checkbox_width=20,
            checkbox_height=20,
        )
        self.chk_transporteur_bl_auto.grid(row=3, column=0, sticky="w")
        styled.label_muted(
            inner_t,
            text="Si coché, le transporteur par défaut est reporté sur les BL automatiques. "
                 "Sinon, les BL-AUTO sont enregistrés sans transporteur.",
            size=10,
        ).grid(row=4, column=0, sticky="w", pady=(4, 0))

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
            conn = LivraisonDB.get_conn()
            if not conn:
                return
            try:
                cur = conn.cursor()
                magasins = LivraisonDB.fetch_magasins_livraison_auto(cur)
                transporteurs = LivraisonDB.fetch_transporteurs(cur)
                param = LivraisonDB.fetch_param_livraison_client(cur)
                tid_def = param.get("idtransporteur_defaut")
                bl_auto_on = bool(param.get("transporteur_bl_auto"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Erreur", str(e), parent=self))
                return
            finally:
                LivraisonDB.release_conn(conn)

            def apply():
                if not self.winfo_exists():
                    return
                self._magasin_rows = magasins
                self._transporteurs = transporteurs
                self._peupler_magasins()
                noms = ["— Aucun —"] + [t[1] for t in transporteurs]
                self.combo_trans_defaut.configure(values=noms)
                self.combo_trans_defaut.set(
                    transporteur_nom_par_id(transporteurs, tid_def),
                )
                if bl_auto_on:
                    self.chk_transporteur_bl_auto.select()
                else:
                    self.chk_transporteur_bl_auto.deselect()

            self.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    def _peupler_magasins(self):
        for w in self._frame_magasins.winfo_children():
            w.destroy()
        self._switches.clear()

        if not self._magasin_rows:
            styled.label_muted(
                self._frame_magasins, text="Aucun magasin actif.", size=11,
            ).pack(anchor="w")
            return

        for idmag, nom, actif in self._magasin_rows:
            row = styled.frame(self._frame_magasins, color="transparent")
            row.pack(fill="x", pady=3)
            styled.label(row, text=nom or f"Magasin #{idmag}", size=12).pack(side="left")
            sw = ctk.CTkSwitch(
                row,
                text="Auto",
                width=46,
                font=ctk.CTkFont(size=11),
                command=lambda m=idmag: None,
            )
            if actif:
                sw.select()
            else:
                sw.deselect()
            sw.pack(side="right")
            self._switches[idmag] = sw

    def _enregistrer(self):
        def worker():
            conn = LivraisonDB.get_conn()
            if not conn:
                return
            auto_result: Dict[str, Any] = {"bl_count": 0, "line_count": 0, "refs": []}
            try:
                cur = conn.cursor()
                for idmag, _nom, _old in self._magasin_rows:
                    sw = self._switches.get(idmag)
                    actif = bool(sw.get()) if sw else False
                    LivraisonDB.set_magasin_livraison_auto(cur, idmag, actif)

                sel = self.combo_trans_defaut.get()
                tid = None
                if sel and sel != "— Aucun —":
                    for t_id, t_nom in self._transporteurs:
                        if t_nom == sel:
                            tid = t_id
                            break
                bl_auto = bool(self.chk_transporteur_bl_auto.get())
                LivraisonDB.save_param_livraison_client(cur, tid, bl_auto)
                param = LivraisonDB.fetch_param_livraison_client(cur)

                if self._id_user:
                    auto_result = LivraisonDB.run_livraison_auto_clients(
                        cur,
                        self._id_user,
                        idtransporteur_defaut=transporteur_pour_bl_auto_depuis_param(
                            param,
                        ),
                    )
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
                LivraisonDB.release_conn(conn)

            def done():
                if not self.winfo_exists():
                    return
                msg = "Paramètres enregistrés."
                if auto_result.get("line_count", 0) > 0:
                    refs = ", ".join(auto_result.get("refs", [])[:5])
                    extra = f"… (+{len(auto_result['refs']) - 5})" if len(auto_result.get("refs", [])) > 5 else ""
                    msg += (
                        f"\n\nLivraison auto : {auto_result['line_count']} ligne(s) "
                        f"dans {auto_result['bl_count']} BL ({refs}{extra})."
                    )
                messagebox.showinfo("Paramètres", msg, parent=self)
                if self._on_saved:
                    self._on_saved()
                self.destroy()

            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()
