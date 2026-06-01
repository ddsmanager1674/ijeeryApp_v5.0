# -*- coding: utf-8 -*-
"""Bon de Livraison — backlog, panier multi-factures (un client), création BL."""

from __future__ import annotations

import threading
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Any, Dict, List, Optional

from app_theme import Colors, Fonts, Layout, styled

try:
    from pages.livraison_common import (
        LivraisonDB,
        fmt_datetime_livraison,
        formater_nombre,
        generer_pdf_bl,
        get_transporteur_defaut_id,
        get_transporteur_pour_bl_auto,
        ligne_panier_key,
        sql_pending_articles,
        sql_pending_factures,
        transporteur_nom_par_id,
    )
    from pages.window_parametres_livraison import ParametresLivraisonWindow
except ImportError:
    from livraison_common import (
        LivraisonDB,
        fmt_datetime_livraison,
        formater_nombre,
        generer_pdf_bl,
        get_transporteur_defaut_id,
        get_transporteur_pour_bl_auto,
        ligne_panier_key,
        sql_pending_articles,
        sql_pending_factures,
        transporteur_nom_par_id,
    )
    from window_parametres_livraison import ParametresLivraisonWindow


class PageBonDeLivraison(ctk.CTkFrame):
    """Panier en mémoire uniquement — réinitialisé à chaque ouverture du menu."""

    def __init__(self, master, id_user_connecte: Optional[int] = None, **kwargs):
        super().__init__(master, fg_color=Colors.BG_PAGE, corner_radius=0)
        self.user_id = id_user_connecte
        if self.user_id is None:
            messagebox.showerror("Erreur", "Utilisateur non connecté.")
            styled.label_muted(
                self, text="Reconnectez-vous pour accéder aux bons de livraison.", size=12,
            ).pack(padx=20, pady=20)
            return

        self._vue = "facture"  # article | facture (défaut : vue facture)
        self._panier: Dict[tuple, Dict[str, Any]] = {}
        self._backlog_art: List[tuple] = []
        self._backlog_fact: List[tuple] = {}
        self._iid_to_row: Dict[str, tuple] = {}
        self._transporteurs: List[tuple] = []
        self._bl_preview = ctk.StringVar(value="—")
        self._panier_visible = False
        self._mode_creation_bl = False
        self._search_after_id: Optional[str] = None
        self._search_job: Optional[int] = 0
        self._search_term = ""
        self._magasins: List[tuple] = []
        self._filtre_idmag: Optional[int] = None
        self._magasin_init_done = False

        LivraisonDB.init_pool()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_ui()
        self.bind("<Destroy>", self._on_destroy)
        self.after(150, self._charger_tout)

    def _on_destroy(self, _event=None):
        self._panier.clear()

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self):
        header = styled.frame(self, color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        header.grid_columnconfigure(0, weight=1)

        tb = styled.frame(header, color="transparent")
        tb.grid(row=0, column=0, sticky="w")
        styled.label_heading(tb, text="Bon de Livraison", size=18).pack(anchor="w")

        family = Fonts._family if getattr(Fonts, "_loaded", False) else "Segoe UI"
        try:
            from pages.menu_auth_utils import (
                CLE_PARAM_LIVRAISON,
                est_lien_param_autorise,
                resolve_session_data,
            )
        except ImportError:
            from menu_auth_utils import (
                CLE_PARAM_LIVRAISON,
                est_lien_param_autorise,
                resolve_session_data,
            )

        self.lbl_parametres = ctk.CTkLabel(
            tb,
            text="⚙  Paramètres",
            font=ctk.CTkFont(family=family, size=11, underline=True),
            text_color=Colors.PRIMARY,
            cursor="hand2",
        )
        if est_lien_param_autorise(resolve_session_data(self), CLE_PARAM_LIVRAISON):
            self.lbl_parametres.pack(anchor="w", pady=(2, 0))
        self.lbl_parametres.bind("<Button-1>", lambda _e: self._ouvrir_parametres())

        styled.label_muted(
            tb,
            text="Créez un BL, puis ajoutez des lignes au panier → enregistrement (trace seule, sans impact stock)",
            size=11,
        ).pack(anchor="w", pady=(2, 0))

        actions = styled.frame(header, color="transparent")
        actions.grid(row=0, column=1, sticky="e")

        btn_row_hdr = styled.frame(actions, color="transparent")
        btn_row_hdr.pack(anchor="e", pady=(0, 6))
        styled.button_premium(
            btn_row_hdr, text="Créer un BL", width=130, height=Layout.BTN_H,
            command=self._creer_bl,
        ).pack(side="right", padx=(8, 0))
        styled.button_secondary(
            btn_row_hdr, text="Actualiser", width=110, height=Layout.BTN_H,
            command=self._charger_tout,
        ).pack(side="right")

        styled.label_muted(actions, text="Prochain BL", size=10).pack(anchor="e")
        styled.label(actions, textvariable=self._bl_preview, size=13, weight="bold").pack(anchor="e")

        body = styled.frame(self, color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        # PanedWindow : ratio 4/7 (tableau) · 3/7 (panier) forcé au redimensionnement
        self._paned_body = ttk.Panedwindow(body, orient="horizontal")
        self._paned_body.grid(row=0, column=0, sticky="nsew")

        pane_main = styled.frame(self._paned_body, color="transparent")
        pane_cart = styled.frame(self._paned_body, color="transparent")
        self._paned_body.add(pane_main, weight=4)
        self._paned_body.add(pane_cart, weight=3)

        self._build_backlog(pane_main)
        self._build_panier(pane_cart)

        self._paned_body.bind("<Configure>", self._on_paned_configure)
        self.after(150, self._masquer_panier)

    def _on_paned_configure(self, event):
        if event.widget is not self._paned_body:
            return
        if self._panier_visible:
            self._afficher_panier_ratio()
        else:
            self._masquer_panier()

    def _masquer_panier(self):
        """Panier replié (largeur 0 visuelle — tableau en pleine largeur)."""
        self._panier_visible = False
        try:
            w = self._paned_body.winfo_width()
            if w > 20:
                self._paned_body.sashpos(0, w - 3)
        except tk.TclError:
            pass

    def _afficher_panier_ratio(self):
        """Affiche le panier à 3/7 de la largeur (tableau 4/7)."""
        self._panier_visible = True
        try:
            w = self._paned_body.winfo_width()
            if w > 100:
                self._paned_body.sashpos(0, max(220, int(w * 4 / 7)))
        except tk.TclError:
            pass

    def _ouvrir_parametres(self):
        if self.user_id is None:
            messagebox.showerror("Erreur", "Utilisateur non connecté.")
            return
        try:
            from pages.menu_auth_utils import (
                CLE_PARAM_LIVRAISON,
                est_lien_param_autorise,
                resolve_session_data,
            )
        except ImportError:
            from menu_auth_utils import (
                CLE_PARAM_LIVRAISON,
                est_lien_param_autorise,
                resolve_session_data,
            )
        if not est_lien_param_autorise(resolve_session_data(self), CLE_PARAM_LIVRAISON):
            messagebox.showwarning(
                "Accès refusé",
                "Votre fonction utilisateur n'est pas autorisée à ouvrir "
                "les paramètres du bon de livraison.",
            )
            return
        ParametresLivraisonWindow(
            self,
            id_user=self.user_id,
            on_saved=lambda: self._charger_tout(conserver_recherche=True),
        )

    def _appliquer_transporteur_defaut(self):
        """Pré-sélectionne le transporteur défini dans les paramètres."""
        tid = get_transporteur_defaut_id()
        nom = transporteur_nom_par_id(self._transporteurs, tid)
        vals = list(self.combo_trans.cget("values") or [])
        if nom in vals:
            self.combo_trans.set(nom)
        elif nom != "— Aucun —":
            self.combo_trans.set("— Aucun —")
        else:
            self.combo_trans.set("— Aucun —")

    def _set_mode_creation_bl(self, actif: bool) -> None:
        """Affiche les actions d'ajout au panier uniquement en mode création BL."""
        self._mode_creation_bl = actif
        if actif:
            self._footer_ajout.grid()
        else:
            self._footer_ajout.grid_remove()

    def _on_backlog_double_click(self, _event=None):
        if not self._mode_creation_bl:
            return
        self._ajouter_selection()

    def _creer_bl(self):
        """Nouveau BL : panier vide, panneau panier ouvert, prochain numéro BL."""
        self._panier.clear()
        self._rafraichir_panier_ui()
        self.ent_desc.delete(0, "end")
        self.combo_trans.set("— Aucun —")
        self._appliquer_transporteur_defaut()
        self._afficher_panier_ratio()
        self._set_mode_creation_bl(True)

        def worker():
            conn = LivraisonDB.get_conn()
            if not conn:
                return
            try:
                cur = conn.cursor()
                bl_ref = LivraisonDB.generate_bl_ref(cur)
                self.after(0, lambda: self._bl_preview.set(bl_ref))
            finally:
                LivraisonDB.release_conn(conn)

        threading.Thread(target=worker, daemon=True).start()

    def _refresh_bl_preview_async(self):
        def worker():
            conn = LivraisonDB.get_conn()
            if not conn:
                return
            try:
                cur = conn.cursor()
                bl_ref = LivraisonDB.generate_bl_ref(cur)
                self.after(0, lambda: self._bl_preview.set(bl_ref))
            finally:
                LivraisonDB.release_conn(conn)

        threading.Thread(target=worker, daemon=True).start()

    def _build_backlog(self, parent):
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        left = styled.card(parent)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        bar = styled.frame(left, color="transparent")
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(12, 6))
        bar.grid_columnconfigure(2, weight=1)

        self.seg_vue = ctk.CTkSegmentedButton(
            bar,
            values=["Vue article", "Vue facture"],
            command=self._changer_vue,
            font=ctk.CTkFont(size=11),
            height=32,
        )
        self.seg_vue.grid(row=0, column=0, sticky="w")
        self.seg_vue.set("Vue facture")

        mag_filtre = styled.frame(bar, color="transparent")
        mag_filtre.grid(row=0, column=1, sticky="w", padx=(10, 8))
        styled.label_muted(mag_filtre, text="Magasin", size=10).pack(anchor="w")
        self.combo_magasin = styled.combobox(
            mag_filtre,
            values=["Tous"],
            width=160,
            height=Layout.INPUT_H,
            command=self._on_magasin_change,
        )
        self.combo_magasin.pack(anchor="w")
        self.combo_magasin.set("Tous")

        self.ent_filtre = styled.entry(
            bar, placeholder="Rechercher (code, article, client, facture, magasin)…", height=Layout.INPUT_H,
        )
        self.ent_filtre.grid(row=0, column=2, sticky="ew", padx=(0, 0))
        self.ent_filtre.bind("<KeyRelease>", self._on_search_key)

        cols_init = (
            "date", "facture", "client", "magasin", "lignes", "reste_tot",
        )
        style_back = self._register_tree_style("BonLivBack")
        self.tree_back = ttk.Treeview(
            left,
            columns=cols_init,
            show="headings",
            selectmode="extended",
            height=16,
            style=style_back,
        )
        self.tree_back.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 4))
        sy = ttk.Scrollbar(left, orient="vertical", command=self.tree_back.yview)
        self.tree_back.configure(yscrollcommand=sy.set)
        sy.grid(row=1, column=1, sticky="ns", pady=(0, 4))
        self.tree_back.bind("<Double-1>", self._on_backlog_double_click)

        footer_back = styled.frame(left, color="transparent")
        footer_back.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 10))
        footer_back.grid_columnconfigure(0, weight=1)

        self.lbl_search_stat = styled.label_muted(footer_back, text="", size=10)
        self.lbl_search_stat.grid(row=0, column=0, sticky="w")

        self._footer_ajout = styled.frame(footer_back, color="transparent")
        self._footer_ajout.grid(row=0, column=1, sticky="e")

        styled.button_primary(
            self._footer_ajout, text="→ Ajouter au panier", width=160, height=Layout.BTN_H,
            command=self._ajouter_selection,
        ).pack(side="right", padx=(6, 0))
        styled.button_secondary(
            self._footer_ajout, text="Double-clic = ajout rapide", width=0, height=Layout.BTN_H,
            state="disabled",
        ).pack(side="right")
        self._footer_ajout.grid_remove()

    def _build_panier(self, parent):
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        right = styled.card(parent)
        right.grid(row=0, column=0, sticky="nsew", padx=(4, 0))
        right.grid_rowconfigure(2, weight=1)
        right.grid_columnconfigure(0, weight=1)

        styled.label(right, text="Panier de livraison", size=14, weight="bold").grid(
            row=0, column=0, sticky="w", padx=14, pady=(14, 4),
        )
        self.lbl_client_panier = styled.badge(right, text="Client : —", variant="neutral")
        self.lbl_client_panier.grid(row=0, column=0, sticky="e", padx=14, pady=(14, 4))

        meta = styled.frame(right, color="transparent")
        meta.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))
        meta.grid_columnconfigure(1, weight=1)

        styled.label_muted(meta, text="Transporteur", size=10).grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.combo_trans = styled.combobox(
            meta, values=["— Aucun —"], height=Layout.INPUT_H,
        )
        self.combo_trans.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        self.combo_trans.set("— Aucun —")

        styled.label_muted(meta, text="Description (voiture, tournée…)", size=10).grid(
            row=0, column=1, sticky="w", pady=(0, 2),
        )
        self.ent_desc = styled.entry(meta, placeholder="Optionnel", height=Layout.INPUT_H)
        self.ent_desc.grid(row=1, column=1, sticky="ew")

        cols = ("date", "facture", "article", "unite", "mag", "reste", "qt_liv")
        style_cart = self._register_tree_style("BonLivCart")
        self.tree_cart = ttk.Treeview(
            right, columns=cols, show="headings", height=12, style=style_cart,
        )
        for c, t, w, stretch in [
            ("date", "Date et Heure", 118, False),
            ("facture", "Facture", 72, False),
            ("article", "Article", 100, True),
            ("unite", "Unité", 52, False),
            ("mag", "Mag.", 52, False),
            ("reste", "Reste", 48, False),
            ("qt_liv", "À livrer", 52, False),
        ]:
            self.tree_cart.heading(c, text=t)
            self.tree_cart.column(
                c, width=w, minwidth=40,
                stretch=stretch,
                anchor="center" if c in ("reste", "qt_liv") else "w",
            )
        self.tree_cart.grid(row=2, column=0, sticky="nsew", padx=10, pady=4)
        self.tree_cart.bind("<Double-1>", self._editer_qte_panier)

        foot = styled.frame(right, color="transparent")
        foot.grid(row=3, column=0, sticky="ew", padx=12, pady=(4, 14))

        styled.button_secondary(
            foot, text="Retirer ligne", width=110, height=Layout.BTN_H,
            command=self._retirer_ligne_panier,
        ).pack(side="left", padx=(0, 6))
        styled.button_danger(
            foot, text="Vider panier", width=120, height=Layout.BTN_H,
            command=self._vider_panier,
        ).pack(side="left")
        styled.button_success(
            foot, text="Enregistrer BL & PDF", width=180, height=Layout.BTN_H,
            command=self._enregistrer_bl,
        ).pack(side="right")

    @staticmethod
    def _register_tree_style(prefix: str) -> str:
        """Enregistre un style Treeview ttk valide (suffixe .Treeview obligatoire)."""
        style = ttk.Style()
        family = Fonts._family if getattr(Fonts, "_loaded", False) else "Segoe UI"
        name = f"{prefix}.Treeview"
        style.configure(
            name,
            background=Colors.BG_CARD,
            foreground=Colors.TEXT_PRIMARY,
            fieldbackground=Colors.BG_CARD,
            rowheight=Layout.ROW_H,
            font=(family, 9),
        )
        style.configure(
            f"{name}.Heading",
            background=Colors.CLOUDS,
            foreground=Colors.TEXT_PRIMARY,
            font=(family, 9, "bold"),
        )
        style.map(
            name,
            background=[("selected", Colors.PRIMARY)],
            foreground=[("selected", Colors.TEXT_ON_DARK)],
        )
        return name

    # ── Données ──────────────────────────────────────────────────────────────

    def _charger_tout(self, conserver_recherche: bool = True):
        if not conserver_recherche:
            self.ent_filtre.delete(0, "end")
            self._search_term = ""
        self._lancer_recherche_db(self.ent_filtre.get().strip(), aussi_transporteurs=True)

    def _on_search_key(self, _event=None):
        if self._search_after_id:
            try:
                self.after_cancel(self._search_after_id)
            except ValueError:
                pass
        self._search_after_id = self.after(280, self._recherche_debounced)

    def _recherche_debounced(self):
        self._search_after_id = None
        terme = self.ent_filtre.get().strip()
        if terme == self._search_term:
            return
        self._lancer_recherche_db(terme, aussi_transporteurs=False)

    def _on_magasin_change(self, _value: str = ""):
        sel = self.combo_magasin.get()
        if sel == "Tous":
            self._filtre_idmag = None
        else:
            self._filtre_idmag = next(
                (mid for mid, nom in self._magasins if nom == sel),
                None,
            )
        self._magasin_init_done = True
        self._search_term = ""  # force rechargement même si le texte de recherche est inchangé
        self._lancer_recherche_db(self.ent_filtre.get().strip(), aussi_transporteurs=False)

    def _idmag_pour_requete(self, idmag_user: Optional[int]) -> Optional[int]:
        """Magasin actif : sélection utilisateur, ou magasin tb_users.idmag au premier chargement."""
        if self._magasin_init_done:
            return self._filtre_idmag
        return idmag_user

    def _lancer_recherche_db(self, terme: str, aussi_transporteurs: bool = False):
        job = self._search_job + 1
        self._search_job = job
        self.lbl_search_stat.configure(text="Recherche…")

        def worker():
            conn = LivraisonDB.get_conn()
            if not conn:
                self.after(0, lambda: self.lbl_search_stat.configure(text=""))
                return
            try:
                cur = conn.cursor()
                if aussi_transporteurs and self.user_id:
                    try:
                        LivraisonDB.run_livraison_auto_clients(
                            cur,
                            int(self.user_id),
                            idtransporteur_defaut=get_transporteur_pour_bl_auto(),
                        )
                        conn.commit()
                    except Exception:
                        conn.rollback()

                magasins: Optional[List[tuple]] = None
                idmag_user: Optional[int] = None
                if self.user_id:
                    cur.execute(
                        """
                        SELECT idmag FROM tb_users
                        WHERE iduser = %s AND COALESCE(deleted, 0) = 0
                        LIMIT 1
                        """,
                        (int(self.user_id),),
                    )
                    row_u = cur.fetchone()
                    if row_u and row_u[0] is not None:
                        idmag_user = int(row_u[0])
                if aussi_transporteurs:
                    cur.execute(
                        """
                        SELECT idmag, designationmag
                        FROM tb_magasin
                        WHERE COALESCE(deleted, 0) = 0
                        ORDER BY designationmag
                        """,
                    )
                    magasins = cur.fetchall()

                idmag_filtre = self._idmag_pour_requete(idmag_user)
                sql_a, params_a = sql_pending_articles(terme, idmag_filtre)
                cur.execute(sql_a, params_a)
                art = cur.fetchall()
                sql_f, params_f = sql_pending_factures(terme, idmag_filtre)
                cur.execute(sql_f, params_f)
                fac = cur.fetchall()
                transporteurs = None
                bl_ref = None
                if aussi_transporteurs:
                    transporteurs = LivraisonDB.fetch_transporteurs(cur)
                    bl_ref = LivraisonDB.generate_bl_ref(cur)

                def apply():
                    if not self.winfo_exists() or job != self._search_job:
                        return
                    if magasins is not None:
                        self._magasins = magasins
                        noms = ["Tous"] + [m[1] for m in magasins]
                        self.combo_magasin.configure(values=noms)
                        if not self._magasin_init_done:
                            self._magasin_init_done = True
                            if idmag_user is not None:
                                nom_def = next(
                                    (n for i, n in magasins if i == idmag_user),
                                    None,
                                )
                                if nom_def:
                                    self.combo_magasin.set(nom_def)
                                    self._filtre_idmag = idmag_user
                                else:
                                    self.combo_magasin.set("Tous")
                                    self._filtre_idmag = None
                            else:
                                self.combo_magasin.set("Tous")
                                self._filtre_idmag = None
                    self._search_term = terme
                    self._backlog_art = art
                    self._backlog_fact = fac
                    if transporteurs is not None:
                        self._transporteurs = transporteurs
                        noms = ["— Aucun —"] + [t[1] for t in self._transporteurs]
                        self.combo_trans.configure(values=noms)
                        if not self._mode_creation_bl:
                            self.combo_trans.set("— Aucun —")
                        else:
                            self._appliquer_transporteur_defaut()
                    if bl_ref:
                        self._bl_preview.set(bl_ref)
                    n = len(art) if self._vue == "article" else len(fac)
                    hint = f"{n} ligne(s)"
                    mag_sel = self.combo_magasin.get()
                    if mag_sel and mag_sel != "Tous":
                        hint += f" — {mag_sel}"
                    if terme:
                        hint += f" — « {terme} »"
                    self.lbl_search_stat.configure(text=hint)
                    self._peupler_backlog()

                self.after(0, apply)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Erreur", f"Recherche : {e}"))
                self.after(0, lambda: self.lbl_search_stat.configure(text=""))
            finally:
                LivraisonDB.release_conn(conn)

        threading.Thread(target=worker, daemon=True).start()

    def _changer_vue(self, value: str):
        self._vue = "facture" if "facture" in value.lower() else "article"
        n = len(self._backlog_fact) if self._vue == "facture" else len(self._backlog_art)
        terme = self._search_term
        hint = f"{n} ligne(s)"
        mag_sel = self.combo_magasin.get()
        if mag_sel and mag_sel != "Tous":
            hint += f" — {mag_sel}"
        if terme:
            hint += f" — « {terme} »"
        self.lbl_search_stat.configure(text=hint)
        self._peupler_backlog()

    def _peupler_backlog(self):
        for i in self.tree_back.get_children():
            self.tree_back.delete(i)
        self._iid_to_row.clear()

        if self._vue == "article":
            cols = (
                "date", "code", "designation", "unite", "magasin", "client",
                "facture", "reste",
            )
            self.tree_back.configure(columns=cols)
            for c, t, w in [
                ("date", "Date et Heure", 130),
                ("code", "Code", 85),
                ("designation", "Désignation", 160),
                ("unite", "Unité", 70),
                ("magasin", "Magasin", 90),
                ("client", "Client", 120),
                ("facture", "Facture", 100),
                ("reste", "Reste", 65),
            ]:
                self.tree_back.heading(c, text=t)
                anc = "center" if c == "reste" else "w"
                self.tree_back.column(c, width=w, anchor=anc)
            for row in self._backlog_art:
                dt_s = fmt_datetime_livraison(row[12])
                iid = self.tree_back.insert("", "end", values=(
                    dt_s,
                    row[0], row[1], row[2], row[3], row[4], row[5],
                    formater_nombre(row[11]),
                ))
                self._iid_to_row[iid] = row
        else:
            cols = ("date", "facture", "client", "magasin", "lignes", "reste_tot")
            self.tree_back.configure(columns=cols)
            for c, t, w in [
                ("date", "Date et Heure", 130),
                ("facture", "Facture", 120),
                ("client", "Client", 160),
                ("magasin", "Magasin", 120),
                ("lignes", "Lignes", 60),
                ("reste_tot", "Reste total", 90),
            ]:
                self.tree_back.heading(c, text=t)
                anc = "center" if c not in ("client", "facture", "magasin") else "w"
                self.tree_back.column(c, width=w, anchor=anc)
            for row in self._backlog_fact:
                ref, nom, _idc, dt, magasins, nb, reste = row
                dt_s = fmt_datetime_livraison(dt)
                iid = self.tree_back.insert("", "end", values=(
                    dt_s, ref, nom, magasins or "—", nb, formater_nombre(reste),
                ))
                self._iid_to_row[iid] = row

    # ── Panier ───────────────────────────────────────────────────────────────

    def _ligne_dict_from_art_row(self, row) -> Dict[str, Any]:
        return {
            "code": row[0],
            "designation": row[1],
            "unite": row[2],
            "magasin": row[3],
            "nomcli": row[4],
            "refvente": row[5],
            "idarticle": row[6],
            "idunite": row[7],
            "idmag": row[8],
            "idclient": row[9],
            "qtvente": float(row[10]),
            "reste": float(row[11]),
            "qtlivrer": float(row[11]),
            "dateregistre": row[12],
        }

    def _ajouter_au_panier(self, items: List[Dict[str, Any]]) -> None:
        if not items:
            return
        id_clients = {int(it["idclient"]) for it in items}
        if len(id_clients) > 1:
            messagebox.showwarning(
                "Client unique",
                "Un bon de livraison ne peut concerner qu'un seul client.\n"
                "Videz le panier ou ne sélectionnez qu'un même client.",
            )
            return
        new_client = next(iter(id_clients))
        if self._panier:
            panier_client = next(iter(self._panier.values()))["idclient"]
            if int(panier_client) != new_client:
                messagebox.showwarning(
                    "Client unique",
                    "Le panier contient déjà des articles d'un autre client.",
                )
                return

        added = 0
        for it in items:
            key = ligne_panier_key(it["refvente"], it["idarticle"], it["idunite"], it["idmag"])
            if key in self._panier:
                continue
            self._panier[key] = it
            added += 1
        if added:
            self._rafraichir_panier_ui()
        else:
            messagebox.showinfo("Panier", "Ligne(s) déjà présente(s) dans le panier.")

    def _ajouter_selection(self):
        if not self._mode_creation_bl:
            messagebox.showinfo(
                "Créer un BL",
                "Cliquez sur « Créer un BL » pour commencer un bon de livraison "
                "et ajouter des lignes au panier.",
            )
            return
        sel = self.tree_back.selection()
        if not sel:
            messagebox.showinfo("Sélection", "Sélectionnez au moins une ligne (Ctrl+clic pour multi).")
            return

        to_add: List[Dict[str, Any]] = []
        if self._vue == "article":
            for iid in sel:
                row = self._iid_to_row.get(iid)
                if row:
                    to_add.append(self._ligne_dict_from_art_row(row))
        else:
            refs = set()
            for iid in sel:
                row = self._iid_to_row.get(iid)
                if row:
                    refs.add(row[0])
            for row in self._backlog_art:
                if row[5] in refs:
                    to_add.append(self._ligne_dict_from_art_row(row))
        self._ajouter_au_panier(to_add)

    def _rafraichir_panier_ui(self):
        for i in self.tree_cart.get_children():
            self.tree_cart.delete(i)
        if not self._panier:
            self.lbl_client_panier.configure(text="Client : —")
            return
        first = next(iter(self._panier.values()))
        self.lbl_client_panier.configure(text=f"Client : {first.get('nomcli', '—')}")
        for it in self._panier.values():
            self.tree_cart.insert("", "end", values=(
                fmt_datetime_livraison(it.get("dateregistre")),
                it["refvente"],
                f"{it['code']} — {it['designation'][:30]}",
                it["unite"],
                it["magasin"],
                formater_nombre(it["reste"]),
                formater_nombre(it["qtlivrer"]),
            ))

    def _editer_qte_panier(self, _event=None):
        sel = self.tree_cart.selection()
        if not sel:
            return
        idx = self.tree_cart.index(sel[0])
        keys = list(self._panier.keys())
        if idx >= len(keys):
            return
        it = self._panier[keys[idx]]

        dlg = ctk.CTkToplevel(self)
        dlg.title("Quantité à livrer")
        dlg.geometry("380x200")
        dlg.configure(fg_color=Colors.BG_PAGE)
        dlg.attributes("-topmost", True)
        dlg.transient(self.winfo_toplevel())

        styled.label_heading(dlg, text=it["designation"], size=14).pack(anchor="w", padx=16, pady=(16, 4))
        styled.label_muted(
            dlg, text=f"Reste : {formater_nombre(it['reste'])}  |  Facture {it['refvente']}", size=11,
        ).pack(anchor="w", padx=16)

        fr = styled.card(dlg)
        fr.pack(fill="x", padx=16, pady=10)
        ent = styled.entry(fr, width=120, height=Layout.INPUT_H)
        ent.insert(0, str(it["qtlivrer"]))
        ent.pack(padx=14, pady=12)
        ent.focus()

        def ok():
            try:
                v = float(ent.get().replace(",", "."))
                if v < 0:
                    raise ValueError
                if v > it["reste"] + 0.0001:
                    messagebox.showwarning(
                        "Quantité",
                        f"Maximum : {formater_nombre(it['reste'])}",
                    )
                    return
                it["qtlivrer"] = v
                self._rafraichir_panier_ui()
                dlg.destroy()
            except ValueError:
                messagebox.showerror("Erreur", "Quantité invalide.")

        bf = styled.frame(dlg, color="transparent")
        bf.pack(fill="x", padx=16, pady=(0, 14))
        styled.button_success(bf, text="OK", command=ok, width=90).pack(side="right")
        styled.button_secondary(bf, text="Annuler", command=dlg.destroy, width=90).pack(side="right", padx=8)
        ent.bind("<Return>", lambda e: ok())

    def _retirer_ligne_panier(self):
        sel = self.tree_cart.selection()
        if not sel:
            messagebox.showinfo("Panier", "Sélectionnez une ligne à retirer.")
            return
        idx = self.tree_cart.index(sel[0])
        keys = list(self._panier.keys())
        if idx < len(keys):
            del self._panier[keys[idx]]
            self._rafraichir_panier_ui()

    def _vider_panier(self):
        if self._panier and messagebox.askyesno("Vider", "Vider tout le panier ?"):
            self._panier.clear()
            self._rafraichir_panier_ui()

    def _enregistrer_bl(self):
        if self.user_id is None:
            messagebox.showerror("Erreur", "Utilisateur non connecté.")
            return
        if not self._panier:
            messagebox.showwarning("Panier vide", "Ajoutez des lignes au panier.")
            return

        lignes = [ln for ln in self._panier.values() if float(ln.get("qtlivrer", 0)) > 0]
        if not lignes:
            messagebox.showwarning("Quantités", "Aucune quantité à livrer (> 0).")
            return

        if not messagebox.askyesno(
            "Confirmer",
            f"Enregistrer le BL avec {len(lignes)} ligne(s) ?",
        ):
            return

        idtransporteur = None
        transp_nom = ""
        sel_t = self.combo_trans.get()
        if sel_t and sel_t != "— Aucun —":
            for tid, nom in self._transporteurs:
                if nom == sel_t:
                    idtransporteur = tid
                    transp_nom = nom
                    break

        description = self.ent_desc.get().strip()
        nom_client = lignes[0].get("nomcli", "")

        conn = LivraisonDB.get_conn()
        if not conn:
            return
        try:
            cur = conn.cursor()
            refliv = LivraisonDB.generate_bl_ref(cur)
            LivraisonDB.insert_bl(
                cur, refliv, lignes, self.user_id, idtransporteur, description,
            )
            conn.commit()
            path = generer_pdf_bl(
                refliv, nom_client, lignes, self.user_id, transp_nom, description,
            )

            messagebox.showinfo(
                "Succès",
                f"Bon de livraison {refliv} enregistré.\nPDF : {path}",
            )
            self._panier.clear()
            self._rafraichir_panier_ui()
            self.ent_desc.delete(0, "end")
            self.combo_trans.set("— Aucun —")
            self._masquer_panier()
            self._set_mode_creation_bl(False)
            self._charger_tout(conserver_recherche=True)
            self._refresh_bl_preview_async()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur", f"Enregistrement : {e}")
            import traceback
            traceback.print_exc()
        finally:
            LivraisonDB.release_conn(conn)
