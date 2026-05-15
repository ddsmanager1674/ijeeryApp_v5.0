# -*- coding: utf-8 -*-
"""Historiques livraison — consultation des BL enregistrés."""

import threading
import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import List, Optional

from app_theme import Colors, Fonts, Layout, styled

try:
    from pages.livraison_common import (
        LivraisonDB,
        fetch_detail_bl_header,
        formater_nombre,
        generer_pdf_bl_duplicata,
        sql_detail_bl,
        sql_historique_bl,
    )
except ImportError:
    from livraison_common import (
        LivraisonDB,
        fetch_detail_bl_header,
        formater_nombre,
        generer_pdf_bl_duplicata,
        sql_detail_bl,
        sql_historique_bl,
    )


def _fmt_dt(val) -> str:
    if val is None:
        return "—"
    if hasattr(val, "strftime"):
        return val.strftime("%d/%m/%Y %H:%M")
    return str(val)


class PageHistoriqueLivraison(ctk.CTkFrame):
    def __init__(self, master, db_conn=None, session_data=None, iduser=None):
        super().__init__(master, fg_color=Colors.BG_PAGE, corner_radius=0)
        self._rows_cache = {}
        self.iduser = iduser or 0
        if session_data and not self.iduser:
            self.iduser = (
                session_data.get("iduser")
                or session_data.get("id_user")
                or session_data.get("user_id")
                or 0
            )
        self._magasins: List[tuple] = []
        self._filtre_idmag: Optional[int] = None
        self._magasin_init_done = False
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        LivraisonDB.init_pool()
        self._setup_ui()
        self.after(200, self.charger_donnees)

    def _setup_ui(self):
        header = styled.frame(self, color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        header.grid_columnconfigure(0, weight=1)

        title_box = styled.frame(header, color="transparent")
        title_box.grid(row=0, column=0, sticky="w")
        styled.label_heading(title_box, text="Historiques livraison", size=18).pack(anchor="w")
        styled.label_muted(
            title_box,
            text="BL enregistrés — tag « Avoir après liv. » si un avoir est passé après la livraison",
            size=11,
        ).pack(anchor="w", pady=(2, 0))

        styled.button_secondary(
            header, text="Actualiser", width=120, height=Layout.BTN_H,
            command=self.charger_donnees,
        ).grid(row=0, column=1, padx=(8, 0))

        filt = styled.card(self)
        filt.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
        filt.grid_columnconfigure(1, weight=1)

        today = datetime.now().strftime("%Y-%m-%d")

        styled.label_muted(filt, text="Magasin", size=11).grid(
            row=0, column=0, sticky="w", padx=(14, 6), pady=(12, 2),
        )
        self.combo_magasin = styled.combobox(
            filt,
            values=["Tous"],
            width=160,
            height=Layout.INPUT_H,
            command=self._on_magasin_change,
        )
        self.combo_magasin.grid(row=1, column=0, sticky="w", padx=(14, 8), pady=(0, 12))
        self.combo_magasin.set("Tous")

        styled.label_muted(filt, text="Recherche (BL, client, facture, transporteur)", size=11).grid(
            row=0, column=1, sticky="w", padx=(0, 6), pady=(12, 2),
        )
        self.ent_search = styled.entry(filt, placeholder="Texte libre…", height=Layout.INPUT_H)
        self.ent_search.grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=(0, 12))
        self.ent_search.bind("<KeyRelease>", lambda e: self._appliquer_filtre_local())

        styled.label_muted(filt, text="Du", size=11).grid(row=0, column=2, padx=6, pady=(12, 2))
        self.ent_du = styled.entry(filt, placeholder="AAAA-MM-JJ", width=110, height=Layout.INPUT_H)
        self.ent_du.grid(row=1, column=2, padx=6, pady=(0, 12))
        self.ent_du.insert(0, today)

        styled.label_muted(filt, text="Au", size=11).grid(row=0, column=3, padx=6, pady=(12, 2))
        self.ent_au = styled.entry(filt, placeholder="AAAA-MM-JJ", width=110, height=Layout.INPUT_H)
        self.ent_au.grid(row=1, column=3, padx=6, pady=(0, 12))
        self.ent_au.insert(0, today)

        styled.button_primary(
            filt, text="Appliquer", width=110, height=Layout.INPUT_H,
            command=self.charger_donnees,
        ).grid(row=1, column=4, padx=8, pady=(0, 12))

        table_card = styled.card(self)
        table_card.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 10))
        table_card.grid_rowconfigure(0, weight=1)
        table_card.grid_columnconfigure(0, weight=1)

        cols = ("date", "bl", "client", "factures", "lignes", "qte", "transporteur", "utilisateur", "tag")
        tree_style = self._register_tree_style()
        self.tree = ttk.Treeview(
            table_card, columns=cols, show="headings", height=18, style=tree_style,
        )
        heads = [
            ("date", "Date et Heure", 130),
            ("bl", "N° BL", 120),
            ("client", "Client", 150),
            ("factures", "Facture(s)", 160),
            ("lignes", "Lignes", 55),
            ("qte", "Qté livrée", 80),
            ("transporteur", "Transporteur", 110),
            ("utilisateur", "Par", 100),
            ("tag", "Tag", 110),
        ]
        for c, t, w in heads:
            self.tree.heading(c, text=t)
            anc = "center" if c in ("lignes", "qte", "tag") else "w"
            self.tree.column(c, width=w, anchor=anc)

        sy = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sy.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)
        sy.grid(row=0, column=1, sticky="ns", pady=10)
        self.tree.bind("<Double-1>", self._ouvrir_detail)
        self.tree.bind("<Double-Button-1>", self._ouvrir_detail)
        self.tree.bind("<Return>", self._ouvrir_detail)
        self.tree.tag_configure("avoir", foreground=Colors.DANGER_TEXT)

        info = styled.frame(self, color="transparent")
        info.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 16))
        self.lbl_count = styled.badge(info, text="0 BL", variant="neutral")
        self.lbl_count.pack(side="left")
        styled.label_muted(
            info, text="Double-clic sur un BL pour voir toutes les lignes et factures associées", size=11,
        ).pack(side="right")

    @staticmethod
    def _register_tree_style() -> str:
        style = ttk.Style()
        family = Fonts._family if getattr(Fonts, "_loaded", False) else "Segoe UI"
        name = "HistLiv.Treeview"
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
        self.charger_donnees()

    def _idmag_pour_requete(self, idmag_user: Optional[int]) -> Optional[int]:
        if self._magasin_init_done:
            return self._filtre_idmag
        return idmag_user

    def charger_donnees(self):
        where_parts = []
        params = []
        du = self.ent_du.get().strip()
        au = self.ent_au.get().strip()
        if du:
            try:
                datetime.strptime(du, "%Y-%m-%d")
                where_parts.append("AND CAST(l.dateregistre AS DATE) >= %s")
                params.append(du)
            except ValueError:
                messagebox.showwarning("Date", "Date « Du » invalide (AAAA-MM-JJ).")
                return
        if au:
            try:
                datetime.strptime(au, "%Y-%m-%d")
                where_parts.append("AND CAST(l.dateregistre AS DATE) <= %s")
                params.append(au)
            except ValueError:
                messagebox.showwarning("Date", "Date « Au » invalide (AAAA-MM-JJ).")
                return

        self.lbl_count.configure(text="Chargement…")

        def worker():
            conn = LivraisonDB.get_conn()
            if not conn:
                self.after(0, lambda: self.lbl_count.configure(text="Erreur connexion"))
                return
            try:
                cur = conn.cursor()
                LivraisonDB.table_columns(cur)

                magasins: Optional[List[tuple]] = None
                idmag_user: Optional[int] = None
                cur.execute(
                    """
                    SELECT idmag, designationmag
                    FROM tb_magasin
                    WHERE COALESCE(deleted, 0) = 0
                    ORDER BY designationmag
                    """,
                )
                magasins = cur.fetchall()
                if self.iduser:
                    cur.execute(
                        """
                        SELECT idmag FROM tb_users
                        WHERE iduser = %s AND COALESCE(deleted, 0) = 0
                        LIMIT 1
                        """,
                        (int(self.iduser),),
                    )
                    row_u = cur.fetchone()
                    if row_u and row_u[0] is not None:
                        idmag_user = int(row_u[0])

                idmag_actif = self._idmag_pour_requete(idmag_user)
                where_mag = list(where_parts)
                params_mag = list(params)
                if idmag_actif is not None:
                    where_mag.append("AND l.idmag = %s")
                    params_mag.append(idmag_actif)
                where_sql_mag = " ".join(where_mag)

                sql = sql_historique_bl(where_sql_mag)
                cur.execute(sql, params_mag)
                rows = cur.fetchall()
            except Exception as e:
                err = str(e)
                self.after(0, lambda: messagebox.showerror("Erreur", f"Chargement historique :\n{err}"))
                self.after(0, lambda: self.lbl_count.configure(text="0 BL"))
                return
            finally:
                LivraisonDB.release_conn(conn)

            def apply():
                if not self.winfo_exists():
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
                for i in self.tree.get_children():
                    self.tree.delete(i)
                self._rows_cache.clear()
                for row in rows:
                    (
                        refliv, dt_bl, _dt_fin, nomcli, _idc,
                        nb, qte_tot, factures, transp, descr, has_avoir_apres, utilisateur,
                    ) = row
                    dt_s = _fmt_dt(dt_bl)
                    tag = "Avoir après liv." if has_avoir_apres else "—"
                    tags = ("avoir",) if has_avoir_apres else ()
                    iid = self.tree.insert("", "end", values=(
                        dt_s,
                        refliv,
                        nomcli or "",
                        factures or "",
                        nb,
                        formater_nombre(qte_tot),
                        transp or "—",
                        utilisateur or "—",
                        tag,
                    ), tags=tags)
                    self._rows_cache[iid] = {
                        "refliv": refliv,
                        "descr": descr or "",
                        "client": nomcli or "",
                    }
                hint = f"{len(rows)} BL"
                mag_sel = self.combo_magasin.get()
                if mag_sel and mag_sel != "Tous":
                    hint += f" — {mag_sel}"
                if du or au:
                    hint += f" ({du or '…'} → {au or '…'})"
                self.lbl_count.configure(text=hint)
                self._appliquer_filtre_local()

            self.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    def _appliquer_filtre_local(self):
        terme = self.ent_search.get().lower().strip()
        visible = 0
        for iid in self.tree.get_children():
            if not terme:
                self.tree.reattach(iid, "", "end")
                visible += 1
                continue
            vals = " ".join(str(v).lower() for v in self.tree.item(iid, "values"))
            if terme in vals:
                self.tree.reattach(iid, "", "end")
                visible += 1
            else:
                self.tree.detach(iid)
        total = len(self.tree.get_children())
        if terme:
            self.lbl_count.configure(text=f"{visible} / {total} BL")

    def _set_busy_cursor(self, busy: bool) -> None:
        cur = "watch" if busy else ""
        try:
            self.tree.configure(cursor=cur)
        except Exception:
            pass
        top = self.winfo_toplevel()
        try:
            top.configure(cursor=cur)
        except Exception:
            pass

    def _ouvrir_detail(self, event=None):
        iid = None
        if event is not None:
            iid = self.tree.identify_row(event.y)
            if iid:
                self.tree.selection_set(iid)
                self.tree.focus(iid)
        sel = self.tree.selection()
        if not sel:
            return
        iid = iid or sel[0]
        meta = self._rows_cache.get(iid, {})
        vals = self.tree.item(iid, "values")
        refliv = (meta.get("refliv") or (vals[1] if len(vals) > 1 else vals[0]) or "").strip()
        if not refliv:
            return

        self._set_busy_cursor(True)
        self.update_idletasks()

        def worker():
            conn = LivraisonDB.get_conn()
            if not conn:
                self.after(0, lambda: self._set_busy_cursor(False))
                return
            header = {}
            lignes = []
            try:
                cur = conn.cursor()
                LivraisonDB.table_columns(cur)
                header = fetch_detail_bl_header(cur, refliv)
                cur.execute(sql_detail_bl(), (refliv,))
                lignes = cur.fetchall()
            except Exception as e:
                err = str(e)
                self.after(0, lambda: messagebox.showerror("Erreur", f"Détail BL :\n{err}"))
                self.after(0, lambda: self._set_busy_cursor(False))
                return
            finally:
                LivraisonDB.release_conn(conn)

            self.after(0, lambda: self._afficher_detail(refliv, header, lignes))

        threading.Thread(target=worker, daemon=True).start()

    def _afficher_detail(self, refliv: str, header: dict, lignes: list):
        self._set_busy_cursor(False)
        if not header and not lignes:
            messagebox.showinfo("Détail", f"Aucune ligne trouvée pour le BL {refliv}.")
            return

        if not header:
            sel = self.tree.selection()
            nom_cache = self._rows_cache.get(sel[0], {}).get("client", "") if sel else ""
            header = {"refliv": refliv, "nomcli": nom_cache, "factures": "", "nb_lignes": len(lignes)}

        dlg = ctk.CTkToplevel(self)
        dlg.title(f"Détail BL — {refliv}")
        dlg.geometry("900x560")
        dlg.configure(fg_color=Colors.BG_PAGE)
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        top_bar = styled.frame(dlg, color="transparent")
        top_bar.pack(fill="x", padx=16, pady=(16, 0))
        top_bar.grid_columnconfigure(0, weight=1)

        styled.label_heading(
            top_bar, text=f"BL {header.get('refliv', refliv)}", size=16,
        ).grid(row=0, column=0, sticky="w")
        styled.button_primary(
            top_bar,
            text="Imprimer un duplicata",
            width=170,
            command=lambda: self._imprimer_duplicata_bl(refliv, dlg),
        ).grid(row=0, column=1, sticky="e", padx=(8, 0))

        hdr = styled.card(dlg)
        hdr.pack(fill="x", padx=16, pady=(8, 8))

        dt_debut = _fmt_dt(header.get("dt_bl"))
        dt_fin = _fmt_dt(header.get("dt_bl_fin"))
        periode = dt_debut if dt_debut == dt_fin or dt_fin == "—" else f"{dt_debut} → {dt_fin}"

        infos = [
            f"Client : {header.get('nomcli', '—')}",
            f"Date : {periode}",
            f"Facture(s) : {header.get('factures', '—')}",
            f"Lignes : {header.get('nb_lignes', len(lignes))}  |  Qté totale livrée : {formater_nombre(header.get('qte_totale', 0))}",
            f"Enregistré par : {header.get('utilisateur', '—')}",
            f"Transporteur : {header.get('transporteur') or '—'}",
        ]
        for i, line in enumerate(infos):
            styled.label(hdr, text=line, size=11).pack(
                anchor="w", padx=14, pady=(12, 0) if i == 0 else 0,
            )
        if header.get("description"):
            styled.label_muted(hdr, text=f"Note : {header['description']}", size=11).pack(
                anchor="w", padx=14, pady=(0, 12),
            )
        if header.get("has_avoir_apres"):
            fac_av = header.get("factures_avoir_apres") or "—"
            styled.badge(
                hdr,
                text=f"Avoir enregistré après livraison — facture(s) : {fac_av}",
                variant="danger",
            ).pack(anchor="w", padx=14, pady=(0, 12))

        box = styled.card(dlg)
        box.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        cols = ("date", "facture", "code", "designation", "unite", "mag", "qt_v", "qt_l", "tag_avoir")
        tr_style = self._register_tree_style()
        tr = ttk.Treeview(box, columns=cols, show="headings", style=tr_style)
        for c, t, w in [
            ("date", "Date et Heure", 130),
            ("facture", "Facture", 100),
            ("code", "Code", 85),
            ("designation", "Désignation", 200),
            ("unite", "Unité", 75),
            ("mag", "Magasin", 95),
            ("qt_v", "Qté fact.", 75),
            ("qt_l", "Qté livrée", 75),
            ("tag_avoir", "Tag", 95),
        ]:
            tr.heading(c, text=t)
            tr.column(c, width=w, anchor="center" if c.startswith("qt") or c == "tag_avoir" else "w")

        for r in lignes:
            (
                _id, refv, dt_ligne, code, des, unite, mag, qtv, qtl, _usr, avoir_apres_liv,
            ) = r
            tags = ("avoir",) if bool(avoir_apres_liv) else ()
            tag_ligne = "Avoir après liv." if bool(avoir_apres_liv) else "—"
            tr.insert("", "end", values=(
                _fmt_dt(dt_ligne),
                refv or "—",
                code or "",
                des or "",
                unite or "",
                mag or "",
                formater_nombre(qtv),
                formater_nombre(qtl),
                tag_ligne,
            ), tags=tags)
        tr.tag_configure("avoir", foreground=Colors.DANGER_TEXT)

        sy = ttk.Scrollbar(box, orient="vertical", command=tr.yview)
        tr.configure(yscrollcommand=sy.set)
        tr.pack(fill="both", expand=True, side="left", padx=(10, 0), pady=10)
        sy.pack(side="right", fill="y", pady=10)

        foot = styled.frame(dlg, color="transparent")
        foot.pack(fill="x", padx=16, pady=(0, 14))
        styled.label_muted(
            foot, text=f"{len(lignes)} ligne(s) dans tb_livraisoncli pour ce BL", size=10,
        ).pack(anchor="w")

    def _imprimer_duplicata_bl(self, refliv: str, dlg=None):
        if not messagebox.askyesno(
            "Duplicata",
            f"Générer un duplicata du bon de livraison {refliv} ?",
            parent=dlg or self,
        ):
            return

        self._set_busy_cursor(True)
        self.update_idletasks()
        uid = self.iduser

        def worker():
            try:
                path = generer_pdf_bl_duplicata(refliv, id_user=uid)
                self.after(0, lambda: messagebox.showinfo(
                    "Duplicata",
                    f"PDF duplicata généré :\n{path}",
                    parent=dlg or self,
                ))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: messagebox.showerror(
                    "Erreur",
                    f"Impression duplicata :\n{err}",
                    parent=dlg or self,
                ))
            finally:
                self.after(0, lambda: self._set_busy_cursor(False))

        threading.Thread(target=worker, daemon=True).start()
