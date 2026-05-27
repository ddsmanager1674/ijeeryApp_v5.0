import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import psycopg2
import json
import pandas as pd
from datetime import datetime
from tkcalendar import DateEntry
import os
from resource_utils import get_config_path, get_session_path, safe_file_read
from impression_pdf_utils import build_impression_output_path
from log_utils import AppLogger

# ── Thème iJeery ──────────────────────────────────────────────────────────────
try:
    from app_theme import Colors, Fonts, styled, Theme
    _T = True
except ImportError:
    _T = False


class _C:
    MIDNIGHT       = "#2C3E50"
    BG_PAGE        = "#ECF0F1"
    BG_CARD        = "#FFFFFF"
    BG_HEADER      = "#2C3E50"
    BG_INPUT       = "#F4F6F8"
    PRIMARY        = "#3498DB"
    PRIMARY_HOVER  = "#2980B9"
    SUCCESS        = "#2ECC71"
    SUCCESS_DARK   = "#27AE60"
    DANGER         = "#E74C3C"
    DANGER_DARK    = "#C0392B"
    WARNING        = "#F39C12"
    INFO           = "#1ABC9C"
    INFO_DARK      = "#16A085"
    PREMIUM        = "#9B59B6"
    PREMIUM_DARK   = "#8E44AD"
    TEXT_PRIMARY   = "#2C3E50"
    TEXT_SECONDARY = "#5D6D7E"
    TEXT_MUTED     = "#95A5A6"
    BORDER         = "#D5D8DC"
    DIVIDER        = "#E8EAED"


C = Colors if _T else _C


# ── Styles Treeview ───────────────────────────────────────────────────────────
def _apply_tree_style(name):
    s = ttk.Style()
    try:
        s.theme_use("clam")
    except Exception:
        pass
    s.configure(f"{name}.Treeview",
                 background=C.BG_CARD, foreground=C.TEXT_PRIMARY,
                 fieldbackground=C.BG_CARD, rowheight=24,
                 font=("Roboto" if _T else "Segoe UI", 10),
                 borderwidth=0)
    s.configure(f"{name}.Treeview.Heading",
                 background=C.BG_HEADER, foreground="#FFFFFF",
                 font=("Roboto" if _T else "Segoe UI", 10, "bold"),
                 relief="flat", padding=(6, 4))
    s.map(f"{name}.Treeview",
          background=[("selected", C.PRIMARY)],
          foreground=[("selected", "#FFFFFF")])


def _f(size=11, weight="normal"):
    return ctk.CTkFont(
        family="Roboto" if _T else "Segoe UI",
        size=size, weight=weight)


def _load_societe_info(cursor):
    """Charge tb_infosociete pour l'impression PDF."""
    cursor.execute(
        "SELECT nomsociete, adressesociete, contactsociete, villesociete, "
        "nifsociete, statsociete, cifsociete, ambleme FROM tb_infosociete LIMIT 1"
    )
    row = cursor.fetchone()
    if not row:
        return {
            "nomsociete": "SOCIÉTÉ", "adressesociete": "N/A",
            "contactsociete": "N/A", "villesociete": "N/A",
            "nifsociete": "N/A", "statsociete": "N/A",
            "cifsociete": "N/A", "ambleme": "",
        }
    return {
        "nomsociete": row[0] or "SOCIÉTÉ",
        "adressesociete": row[1] or "N/A",
        "contactsociete": row[2] or "N/A",
        "villesociete": row[3] or "N/A",
        "nifsociete": row[4] or "N/A",
        "statsociete": row[5] or "N/A",
        "cifsociete": row[6] or "N/A",
        "ambleme": row[7] or "",
    }


def _get_data_avoir_print(cursor, idavoir, societe_info):
    """Données complètes d'un avoir pour impression (même structure que page_avoir)."""
    cursor.execute(
        """
        SELECT a.refavoir, a.dateregistre, a.dateavoir, a.observation, a.mtavoir,
               u.nomuser, u.prenomuser,
               c.nomcli, c.adressecli, c.contactcli
        FROM tb_avoir a
        INNER JOIN tb_users u ON a.iduser = u.iduser
        LEFT JOIN tb_client c ON a.idclient = c.idclient
        WHERE a.id = %s AND a.deleted = 0
        """,
        (idavoir,),
    )
    avoir_result = cursor.fetchone()
    if not avoir_result:
        return None

    dateavoir_str = (
        avoir_result[2].strftime("%d/%m/%Y")
        if avoir_result[2] else datetime.now().strftime("%d/%m/%Y")
    )
    data = {
        "societe": societe_info,
        "avoir": {
            "refavoir": avoir_result[0],
            "dateregistre": avoir_result[1].strftime("%d/%m/%Y"),
            "dateavoir": dateavoir_str,
            "observation": avoir_result[3] or "",
            "mtavoir": avoir_result[4] or 0.0,
            "refvente_associe": "",
            "magasin_vente": "",
        },
        "utilisateur": {
            "nomuser": avoir_result[5],
            "prenomuser": avoir_result[6],
        },
        "client": {
            "nomcli": avoir_result[7] or "Client Inconnu",
            "adressecli": avoir_result[8] or "N/A",
            "contactcli": avoir_result[9] or "N/A",
        },
        "details": [],
    }

    refvente_associe = None
    for sql in (
        "SELECT refvente FROM tb_pmtavoir WHERE refavoir=%s AND deleted=0 "
        "ORDER BY id DESC LIMIT 1",
        "SELECT refvente FROM tb_pmtfacture WHERE refavoir=%s "
        "ORDER BY id DESC LIMIT 1",
    ):
        try:
            cursor.execute(sql, (data["avoir"]["refavoir"],))
            row = cursor.fetchone()
            if row and row[0]:
                refvente_associe = row[0]
                data["avoir"]["refvente_associe"] = refvente_associe
                break
        except Exception:
            pass

    cursor.execute(
        """
        SELECT u.codearticle, a.designation, u.designationunite,
               ad.qtavoir, ad.prixunit,
               ad.qtavoir * ad.prixunit AS montant_total,
               m.designationmag,
               COALESCE((
                   SELECT vd.prixunit FROM tb_vente v
                   INNER JOIN tb_ventedetail vd ON vd.idvente = v.id
                   WHERE v.refvente = %s
                     AND vd.idarticle = ad.idarticle
                     AND vd.idunite = ad.idunite
                     AND vd.idmag = ad.idmag
                   ORDER BY ABS((vd.prixunit - COALESCE(vd.remise, 0)) - ad.prixunit),
                            vd.id DESC
                   LIMIT 1
               ), ad.prixunit) AS pu_ttc_brut
        FROM tb_avoirdetail ad
        INNER JOIN tb_article a ON ad.idarticle = a.idarticle
        INNER JOIN tb_unite u ON ad.idunite = u.idunite
        INNER JOIN tb_magasin m ON ad.idmag = m.idmag
        WHERE ad.idavoir = %s AND ad.deleted = 0
        ORDER BY a.designation
        """,
        (refvente_associe, idavoir),
    )
    data["details"] = cursor.fetchall()
    magasins = [r[6] for r in data["details"] if len(r) > 6 and r[6]]
    if magasins:
        data["avoir"]["magasin_vente"] = magasins[0]
    return data


def _generate_pdf_a5_avoir_duplicata(data, filename, duplicata=True):
    """PDF A5 avoir — même modèle que page_avoir, mention DUPLICATA optionnelle."""
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.units import mm

    from pages.pdf_modele_facture_a5 import (
        generer_pdf_a5_modele_ventedepot,
        html_entete_droite_avoir,
        formater_nombre_pdf_defaut,
    )
    from pages.page_venteParMsin import nombre_en_lettres_fr

    avoir = data.get("avoir") or {}
    util = data.get("utilisateur") or {}
    user_name = f"{util.get('prenomuser') or ''} {util.get('nomuser') or ''}".strip()
    mag = str(avoir.get("magasin_vente") or "")
    da = avoir.get("dateavoir")
    if isinstance(da, datetime):
        date_effet = da.strftime("%d/%m/%Y %H:%M")
    else:
        date_effet = str(da or "")
    date_txt = f"{avoir.get('dateregistre', '') or ''} · Effet: {date_effet}".strip()

    html_r = html_entete_droite_avoir(
        str(avoir.get("refavoir", "N/A")),
        str(avoir.get("refvente_associe") or "N/A"),
        date_txt,
        mag,
        (data.get("client") or {}).get("nomcli", "Client"),
        user_name,
    )

    overlay = None
    footer_extra = ()
    if duplicata:
        def overlay_duplicata(c, width, height):
            c.saveState()
            c.setFont("Helvetica-Bold", 12)
            c.setFillColor(rl_colors.HexColor("#D32F2F"))
            c.drawCentredString(width / 2, height - 43.5 * mm, "DUPLICATA")
            c.restoreState()

        overlay = overlay_duplicata
        footer_extra = ("<i>CECI EST UN DUPLICATA DE L'AVOIR</i>",)

    dname = os.path.dirname(os.path.abspath(filename))
    if dname:
        os.makedirs(dname, exist_ok=True)

    generer_pdf_a5_modele_ventedepot(
        filename,
        societe=data.get("societe") or {},
        utilisateur=util,
        client=data.get("client") or {},
        magasin_nom=mag,
        html_right_header=html_r,
        details=data.get("details") or [],
        nombre_en_lettres_fr=nombre_en_lettres_fr,
        formater_nombre_pdf=formater_nombre_pdf_defaut,
        overlay_apres_entete=overlay,
        paragraphes_footer_supplement=footer_extra,
    )


# ====================================================================
# Logique métier partagée — détail facture / avoir
# ====================================================================

_BADGE_STATUT = {
    "VALIDEE":    (C.SUCCESS_DARK, "#FFFFFF"),
    "EN_ATTENTE": (C.WARNING,      "#FFFFFF"),
    "ANNULE":     (C.DANGER,       "#FFFFFF"),
    "AVOIR":      (C.PREMIUM_DARK, "#FFFFFF"),
}


class _FactureDetailCore:
    """Méthodes communes popup et panneau embarqué."""

    def _init_detail_state(self, idvente, refvente, statut, parent_page, mode_avoir):
        self.idvente       = idvente
        self.refvente      = refvente
        self.statut        = statut
        self.parent_page   = parent_page
        self.mode_avoir    = mode_avoir
        self.montant_total = 0
        self.mode_paiement = "N/A"

    def _init_detail_logger(self, session_data=None):
        try:
            if session_data is None and self.parent_page and hasattr(self.parent_page, "session_data"):
                session_data = self.parent_page.session_data
            self._logger = AppLogger(session_data=session_data or {})
        except Exception:
            self._logger = None

    def _setup_detail_tree(self, parent, style_name):
        tbl = ctk.CTkFrame(parent, fg_color=C.BG_CARD, corner_radius=8)
        tbl.grid_rowconfigure(0, weight=1)
        tbl.grid_columnconfigure(0, weight=1)

        def _hide_p_remise():
            try:
                self.tree.column("p_remise", width=0, minwidth=0, stretch=False)
            except Exception:
                pass

        def _show_p_remise():
            try:
                self.tree.column("p_remise", width=100, minwidth=70, anchor="e", stretch=False)
            except Exception:
                pass

        self._hide_p_remise_column = _hide_p_remise
        self._show_p_remise_column = _show_p_remise

        cols = ("code", "designation", "qte", "prix", "p_remise", "total")
        self.tree = ttk.Treeview(tbl, columns=cols, show="headings",
                                 style=f"{style_name}.Treeview")
        self.tree.tag_configure("even", background=C.BG_CARD)
        self.tree.tag_configure("odd",  background="#F0F4F8")

        self.tree.heading("code",        text="Code")
        self.tree.heading("designation", text="Désignation")
        self.tree.heading("qte",         text="Qté")
        self.tree.heading("prix",        text="Prix Unit.")
        self.tree.heading("p_remise",    text="P.Remise")
        self.tree.heading("total",       text="Total")

        self.tree.column("code",        width=80,  minwidth=60, anchor="center")
        self.tree.column("designation", width=300, anchor="w")
        self.tree.column("qte",         width=70,  anchor="center")
        self.tree.column("prix",        width=100, anchor="e")
        self.tree.column("p_remise",    width=0, minwidth=0, stretch=False, anchor="e")
        self.tree.column("total",       width=120, anchor="e")

        sy = ctk.CTkScrollbar(tbl, orientation="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sy.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        sy.grid(row=0, column=1, sticky="ns", pady=6)
        return tbl

    def _populate_action_buttons(self, container):
        for w in container.winfo_children():
            w.destroy()

        if self.statut == "VALIDEE" or self.mode_avoir:
            lbl_dup = (
                "🖨️  Duplicata Avoir" if self.mode_avoir
                else "🖨️  Duplicata"
            )
            ctk.CTkButton(
                container, text=lbl_dup,
                command=self.reimprimer_duplicata,
                fg_color=C.PRIMARY, hover_color=C.PRIMARY_HOVER,
                text_color="#FFFFFF", height=28,
                width=150 if self.mode_avoir else 130,
                font=_f(9, "bold"),
            ).pack(side="left", padx=(0, 6))

        if self.statut == "EN_ATTENTE" and not self.mode_avoir:
            ctk.CTkButton(
                container, text="❌  Annuler",
                command=self.annuler_facture,
                fg_color=C.DANGER, hover_color=C.DANGER_DARK,
                text_color="#FFFFFF", height=28, width=110,
                font=_f(9, "bold"),
            ).pack(side="left", padx=(0, 6))

        if self.statut == "ANNULE":
            ctk.CTkLabel(
                container, text="⚠️  Facture Annulée",
                text_color=C.DANGER, font=_f(10, "bold"),
            ).pack(side="left")

    def _close_if_popup(self):
        if isinstance(self, ctk.CTkToplevel):
            self.destroy()

    def formater_montant(self, valeur):
        """Transforme un nombre en format 1.000,00 Ar"""
        try:
            n = f"{float(valeur):,.0f}"
            return n.replace(",", "X").replace(".", ",").replace("X", ".")
        except:
            return "0,00"

    def charger_details(self, idvente):
        try:
            with open(get_config_path('config.json')) as f:
                config = json.load(f)
            from pages.db_helper import connect_page_db
            conn = connect_page_db()
            cursor = conn.cursor()

            if self.mode_avoir:
                cursor.execute(
                    "SELECT a.mtavoir FROM tb_avoir a WHERE a.id = %s AND a.deleted = 0",
                    (idvente,),
                )
            else:
                cursor.execute(
                    "SELECT v.totmtvente FROM tb_vente v WHERE v.id = %s",
                    (idvente,),
                )
            result = cursor.fetchone()
            if result:
                self.montant_total = float(result[0]) if result[0] else 0
                self.lbl_montant.configure(
                    text=f"{self.formater_montant(self.montant_total)} Ar")

            if self.mode_avoir:
                sql = """
                    SELECT u.codearticle, a.designation, ad.qtavoir, ad.prixunit,
                           0 AS remise,
                           (ad.qtavoir * COALESCE(ad.prixunit, 0)) AS total
                    FROM tb_avoirdetail ad
                    INNER JOIN tb_unite u ON ad.idunite = u.idunite
                    INNER JOIN tb_article a ON ad.idarticle = a.idarticle
                    WHERE ad.idavoir = %s AND ad.deleted = 0
                """
            else:
                sql = """
                    SELECT u.codearticle, a.designation, vd.qtvente, vd.prixunit,
                           COALESCE(vd.remise, 0) AS remise,
                           (vd.qtvente * (COALESCE(vd.prixunit, 0) - COALESCE(vd.remise, 0))) AS total
                    FROM tb_ventedetail vd
                    INNER JOIN tb_unite u ON vd.idunite = u.idunite
                    INNER JOIN tb_article a ON vd.idarticle = a.idarticle
                    WHERE vd.idvente = %s
                """
            cursor.execute(sql, (idvente,))
            for item in self.tree.get_children():
                self.tree.delete(item)
            rows = cursor.fetchall()
            any_remise = False
            for idx, r in enumerate(rows):
                code, des, qte, pu, remise, total = r
                pu_f = float(pu or 0)
                rem_f = float(remise or 0)
                if rem_f > 0:
                    any_remise = True
                p_cell = (
                    self.formater_montant(max(0.0, pu_f - rem_f)) if rem_f > 0 else ""
                )
                tag = "even" if idx % 2 == 0 else "odd"
                self.tree.insert("", "end", values=(
                    code, des,
                    self.formater_montant(float(qte or 0)),
                    self.formater_montant(pu_f),
                    p_cell,
                    self.formater_montant(float(total or 0)),
                ), tags=(tag,))
            if any_remise:
                self._show_p_remise_column()
            else:
                self._hide_p_remise_column()
            conn.close()
        except Exception as e:
            messagebox.showerror("Erreur SQL",
                                 f"Erreur lors du chargement des détails : {e}")

    def reimprimer_duplicata(self):
        """Génère un duplicata de la facture ou de l'avoir"""
        if self.mode_avoir:
            self._reimprimer_duplicata_avoir()
            return
        try:
            with open(get_config_path('config.json')) as f:
                config = json.load(f)
            from pages.db_helper import connect_page_db
            conn = connect_page_db()
            cursor = conn.cursor()

            sql = """
                SELECT v.refvente, v.dateregistre, v.description,
                       u.nomuser, u.prenomuser,
                       c.nomcli, c.adressecli, c.contactcli, v.totmtvente
                FROM tb_vente v
                INNER JOIN tb_users u ON v.iduser = u.iduser
                LEFT JOIN tb_client c ON v.idclient = c.idclient
                WHERE v.id = %s
            """
            cursor.execute(sql, (self.idvente,))
            result = cursor.fetchone()
            if not result:
                messagebox.showerror("Erreur",
                                     "Impossible de récupérer les données de la facture")
                return

            (refvente, dateregistre, description, nomuser, prenomuser,
             nomcli, adressecli, contactcli, totmtvente) = result

            sql_details = """
                SELECT u.codearticle, a.designation, u.designationunite,
                       vd.qtvente, vd.prixunit, vd.remise, m.designationmag
                FROM tb_ventedetail vd
                INNER JOIN tb_article a ON vd.idarticle = a.idarticle
                INNER JOIN tb_unite u ON vd.idunite = u.idunite
                INNER JOIN tb_magasin m ON vd.idmag = m.idmag
                WHERE vd.idvente = %s ORDER BY a.designation
            """
            cursor.execute(sql_details, (self.idvente,))
            details_rows = cursor.fetchall()

            cursor.execute(
                "SELECT nomsociete, adressesociete, contactsociete, nifsociete, statsociete, ambleme FROM tb_infosociete LIMIT 1"
            )
            societe_result = cursor.fetchone()
            conn.close()

            societe_info = {
                'nomsociete':     societe_result[0] if societe_result else 'N/A',
                'adressesociete': societe_result[1] if societe_result else 'N/A',
                'contactsociete': societe_result[2] if societe_result else 'N/A',
                'nifsociete':     societe_result[3] if societe_result else 'N/A',
                'statsociete':    societe_result[4] if societe_result else 'N/A',
                'ambleme':        societe_result[5] if societe_result else '',
            }

            data = {
                'societe': societe_info,
                'vente': {
                    'refvente': refvente,
                    'dateregistre': dateregistre.strftime("%d/%m/%Y %H:%M"),
                    'description': description,
                },
                'utilisateur': {'nomuser': nomuser, 'prenomuser': prenomuser},
                'client': {
                    'nomcli':     nomcli or "Client Divers",
                    'adressecli': adressecli or "N/A",
                    'contactcli': contactcli or "N/A",
                },
                'details': [
                    {
                        'code_article': r[0], 'designation': r[1], 'unite': r[2],
                        'qte': float(r[3] or 0), 'prixunit': float(r[4] or 0),
                        'remise': float(r[5] or 0), 'magasin': r[6],
                        'montant_ttc': max(
                            0.0,
                            float(r[3] or 0) * float(r[4] or 0)
                            - float(r[3] or 0) * float(r[5] or 0),
                        ),
                    }
                    for r in details_rows
                ]
            }

            safe_ref = refvente.replace("/", "-").replace("\\", "-")
            basename = f"DUPLICATA_Facture_{safe_ref}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            filename, is_temp = build_impression_output_path(
                basename, temp_prefix="ijeery_duplicata_"
            )

            self.generate_pdf_a5_duplicata(data, filename)
            extra = "\n\n(Fichier temporaire — non enregistré dans le dossier configuré.)" if is_temp else ""
            messagebox.showinfo(
                parent=self,
                title="Succès",
                message=f"Duplicata généré avec succès !\n{filename}{extra}",
            )

            if os.path.exists(filename):
                os.startfile(filename)

            try:
                if self._logger:
                    self._logger.log(
                        action="Impression duplicata facture",
                        element=refvente,
                        details=f"Duplicata généré, fichier={os.path.basename(filename)}",
                        value=filename,
                    )
            except Exception:
                pass
            
            self._close_if_popup()

        except Exception as e:
            messagebox.showerror("Erreur",
                                 f"Erreur lors de la génération du duplicata : {str(e)}")
            import traceback
            traceback.print_exc()

    def _reimprimer_duplicata_avoir(self):
        """Duplicata PDF A5 — même modèle que l'impression avoir (page_avoir)."""
        try:
            with open(get_config_path('config.json')) as f:
                config = json.load(f)
            from pages.db_helper import connect_page_db
            conn = connect_page_db()
            cursor = conn.cursor()

            societe_info = _load_societe_info(cursor)
            data = _get_data_avoir_print(cursor, self.idvente, societe_info)
            conn.close()

            if not data:
                messagebox.showerror(
                    "Erreur",
                    "Impossible de récupérer les données de l'avoir",
                    parent=self,
                )
                return

            refavoir = data["avoir"]["refavoir"]
            safe_ref = str(refavoir).replace("/", "-").replace("\\", "-")
            basename = (
                f"DUPLICATA_Avoir_{safe_ref}_"
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )
            filename, is_temp = build_impression_output_path(
                basename, temp_prefix="ijeery_duplicata_avoir_"
            )

            _generate_pdf_a5_avoir_duplicata(data, filename, duplicata=True)
            extra = (
                "\n\n(Fichier temporaire — non enregistré dans le dossier configuré.)"
                if is_temp else ""
            )
            messagebox.showinfo(
                parent=self,
                title="Succès",
                message=f"Duplicata avoir généré avec succès !\n{filename}{extra}",
            )

            if os.path.exists(filename):
                os.startfile(filename)

            try:
                if self._logger:
                    self._logger.log(
                        action="Impression duplicata avoir",
                        element=refavoir,
                        details=(
                            f"Duplicata généré, fichier={os.path.basename(filename)}"
                        ),
                        value=filename,
                    )
            except Exception:
                pass

            self._close_if_popup()

        except Exception as e:
            messagebox.showerror(
                "Erreur",
                f"Erreur lors de la génération du duplicata avoir : {str(e)}",
                parent=self,
            )
            import traceback
            traceback.print_exc()

    def annuler_facture(self):
        """Annule la facture (change le statut à 'ANNULE')"""
        if messagebox.askyesno(
                parent=self, title="Confirmation",
                message=f"Voulez-vous annuler la facture {self.refvente} ?"):
            try:
                from pages.db_helper import connect_page_db
                conn = connect_page_db()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE tb_vente SET statut = %s WHERE refvente = %s",
                    ("ANNULE", self.refvente))
                conn.commit()
                messagebox.showinfo(
                    parent=self, title="Succès", message=f"La facture {self.refvente} a été annulée.")

                try:
                    if self._logger:
                        self._logger.log(
                            action="Annulation de facture",
                            element=self.refvente,
                            details="Facture annulée (statut -> ANNULE)",
                            value="ANNULE",
                        )
                except Exception:
                    pass
                self.statut = "ANNULE"
                if hasattr(self, "actions_frame"):
                    self._populate_action_buttons(self.actions_frame)
                if hasattr(self, "lbl_badge") and self.lbl_badge.winfo_exists():
                    bg_s, fg_s = _BADGE_STATUT.get("ANNULE", (C.TEXT_MUTED, "#FFFFFF"))
                    self.lbl_badge.configure(text="  ANNULE  ", fg_color=bg_s, text_color=fg_s)
                if self.parent_page:
                    self.parent_page.charger_donnees()
                self._close_if_popup()
            except Exception as e:
                messagebox.showerror("Erreur",
                                     f"Erreur lors de l'annulation : {str(e)}")
                import traceback
                traceback.print_exc()
            finally:
                if 'conn' in locals():
                    conn.close()

    def generate_pdf_a5_duplicata(self, data, filename):
        """
        Duplicata A5 : même modèle visuel que la facture « ventes par dépôt »,
        avec mention DUPLICATA et pied de page complémentaire.
        """
        from reportlab.lib import colors as rl_colors
        from reportlab.lib.units import mm

        from pages.pdf_modele_facture_a5 import (
            generer_pdf_a5_modele_ventedepot,
            html_entete_droite_facture,
            formater_nombre_pdf_defaut,
        )
        from pages.page_venteParMsin import nombre_en_lettres_fr

        dname = os.path.dirname(os.path.abspath(filename))
        if dname:
            os.makedirs(dname, exist_ok=True)

        vente = data["vente"]
        util = data.get("utilisateur") or {}
        user_name = f"{util.get('prenomuser') or ''} {util.get('nomuser') or ''}".strip()
        mag_label = (
            (data.get("details") or [{}])[0].get("magasin", "N/A")
            if data.get("details")
            else "N/A"
        )

        html_r = html_entete_droite_facture(
            str(vente.get("refvente", "")),
            str(vente.get("dateregistre", "")),
            str(mag_label),
            (data.get("client") or {}).get("nomcli", "Client"),
            user_name,
        )

        def overlay_duplicata(c, width, height):
            c.saveState()
            c.setFont("Helvetica-Bold", 12)
            c.setFillColor(rl_colors.HexColor("#D32F2F"))
            c.drawCentredString(width / 2, height - 43.5 * mm, "DUPLICATA")
            c.restoreState()

        generer_pdf_a5_modele_ventedepot(
            filename,
            societe=data.get("societe") or {},
            utilisateur=util,
            client=data.get("client") or {},
            magasin_nom=str(mag_label),
            html_right_header=html_r,
            details=data.get("details") or [],
            nombre_en_lettres_fr=nombre_en_lettres_fr,
            formater_nombre_pdf=formater_nombre_pdf_defaut,
            overlay_apres_entete=overlay_duplicata,
            paragraphes_footer_supplement=("<i>CECI EST UN DUPLICATA DE LA FACTURE</i>",),
        )

    # --------------------------------------------------------------------
    # Fin génération duplicata A5
    # --------------------------------------------------------------------


# ====================================================================
# PageDetailFacture — popup (double-clic)
# ====================================================================

class PageDetailFacture(_FactureDetailCore, ctk.CTkToplevel):
    """Fenêtre affichant les articles d'une facture spécifique"""

    def __init__(self, master, idvente, refvente,
                 statut="EN_ATTENTE", parent_page=None, mode_avoir=False):
        super().__init__(master)
        self.mode_avoir = mode_avoir
        titre_doc = "Avoir" if mode_avoir else "Facture"
        self.title(f"Détails {titre_doc} : {refvente}")
        self.geometry("860x560")
        if _T:
            Theme.apply_toplevel(self)
        self.attributes('-topmost', True)

        self._init_detail_state(idvente, refvente, statut, parent_page, mode_avoir)
        _apply_tree_style("Detail")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        hdr = ctk.CTkFrame(self, fg_color=C.BG_HEADER, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            hdr, text=f"Détails {titre_doc} — {refvente}",
            font=_f(16, "bold"), text_color="#FFFFFF"
        ).pack(side="left", padx=16, pady=10)

        bg_s, fg_s = _BADGE_STATUT.get(statut, (C.TEXT_MUTED, "#FFFFFF"))
        self.lbl_badge = ctk.CTkLabel(
            hdr, text=f"  {statut}  ",
            font=_f(9, "bold"), text_color=fg_s,
            fg_color=bg_s, corner_radius=4
        )
        self.lbl_badge.pack(side="right", padx=16, pady=10)

        tbl = self._setup_detail_tree(self, "Detail")
        tbl.grid(row=1, column=0, sticky="nsew", padx=12, pady=6)

        footer = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=8)
        footer.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))

        left = ctk.CTkFrame(footer, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=16, pady=12)
        ctk.CTkLabel(
            left, text="Montant Total",
            font=_f(9), text_color=C.TEXT_MUTED
        ).pack(anchor="w")
        self.lbl_montant = ctk.CTkLabel(
            left, text="0,00 Ar",
            font=_f(16, "bold"), text_color=C.SUCCESS_DARK)
        self.lbl_montant.pack(anchor="w")

        self.actions_frame = ctk.CTkFrame(footer, fg_color="transparent")
        self.actions_frame.pack(side="right", padx=16, pady=12)
        self._populate_action_buttons(self.actions_frame)

        self.charger_details(idvente)
        session_data = {}
        if parent_page and hasattr(parent_page, "session_data"):
            session_data = parent_page.session_data
        self._init_detail_logger(session_data)


# ====================================================================
# PanelDetailFacture — panneau bas (simple clic)
# ====================================================================

class PanelDetailFacture(_FactureDetailCore, ctk.CTkFrame):
    """Panneau embarqué affichant le détail d'une facture sélectionnée."""

    def __init__(self, master, parent_page=None, session_data=None):
        super().__init__(master, fg_color=C.BG_CARD, corner_radius=8)
        self.parent_page = parent_page
        self._visible = False
        _apply_tree_style("DetailPanel")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        hdr = ctk.CTkFrame(self, fg_color=C.BG_HEADER, corner_radius=6)
        hdr.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        hdr.grid_columnconfigure(0, weight=1)

        self.lbl_titre = ctk.CTkLabel(
            hdr, text="Détail facture",
            font=_f(12, "bold"), text_color="#FFFFFF",
        )
        self.lbl_titre.grid(row=0, column=0, sticky="w", padx=12, pady=8)

        right_hdr = ctk.CTkFrame(hdr, fg_color="transparent")
        right_hdr.grid(row=0, column=1, sticky="e", padx=(0, 4), pady=4)

        self.lbl_badge = ctk.CTkLabel(
            right_hdr, text="  —  ",
            font=_f(9, "bold"), text_color="#FFFFFF",
            fg_color=C.TEXT_MUTED, corner_radius=4,
        )
        self.lbl_badge.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            right_hdr, text="✕", width=28, height=28,
            command=self.masquer,
            fg_color=C.DANGER, hover_color=C.DANGER_DARK,
            text_color="#FFFFFF", font=_f(12, "bold"),
        ).pack(side="left")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 4))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        tbl = self._setup_detail_tree(body, "DetailPanel")
        tbl.grid(row=0, column=0, sticky="nsew")

        footer = ctk.CTkFrame(self, fg_color=C.BG_INPUT, corner_radius=6)
        footer.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))

        left = ctk.CTkFrame(footer, fg_color="transparent")
        left.pack(side="left", padx=12, pady=8)
        ctk.CTkLabel(
            left, text="Montant Total",
            font=_f(8), text_color=C.TEXT_MUTED,
        ).pack(anchor="w")
        self.lbl_montant = ctk.CTkLabel(
            left, text="0,00 Ar",
            font=_f(13, "bold"), text_color=C.SUCCESS_DARK,
        )
        self.lbl_montant.pack(anchor="w")

        self.actions_frame = ctk.CTkFrame(footer, fg_color="transparent")
        self.actions_frame.pack(side="right", padx=12, pady=8)

        self._init_detail_state("", "", "EN_ATTENTE", parent_page, False)
        self._init_detail_logger(session_data)

    def masquer(self):
        self._visible = False
        self.grid_remove()
        if self.parent_page:
            self.parent_page._detail_row_weight(show=False)

    def afficher(self, idvente, refvente, statut, mode_avoir=False):
        self._visible = True
        self._init_detail_state(idvente, refvente, statut, self.parent_page, mode_avoir)

        titre_doc = "Avoir" if mode_avoir else "Facture"
        self.lbl_titre.configure(text=f"Détail {titre_doc} — {refvente}")

        bg_s, fg_s = _BADGE_STATUT.get(statut, (C.TEXT_MUTED, "#FFFFFF"))
        self.lbl_badge.configure(text=f"  {statut}  ", fg_color=bg_s, text_color=fg_s)

        self._populate_action_buttons(self.actions_frame)
        self.charger_details(idvente)

        self.grid()
        if self.parent_page:
            self.parent_page._detail_row_weight(show=True)


class PageListeFacture(ctk.CTkFrame):

    def __init__(self, parent, session_data=None):
        super().__init__(parent, fg_color=C.BG_PAGE)
        self.session_data             = session_data or {}
        self.id_user_connecte         = self.get_connected_user_id(parent, session_data)
        self.magasin_map              = {}
        self.user_default_magasin_nom = None

        _apply_tree_style("Facture")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(3, weight=0, minsize=0)
        self._detail_selection = None

        self.setup_ui()
        self.charger_donnees()
        self._logger = AppLogger(session_data=self.session_data, fallback_user_id=self.id_user_connecte)

    # ====================================================================
    # setup_ui — REFONTE DESIGN UNIQUEMENT
    # ====================================================================

    def setup_ui(self):
        # ── En-tête ───────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=C.BG_HEADER, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            hdr, text="Liste des Factures",
            font=_f(18, "bold"), text_color="#FFFFFF"
        ).pack(side="left", padx=16, pady=10)

        # ── Barre filtres ─────────────────────────────────────────────────
        panel = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=8)
        panel.grid(row=1, column=0, sticky="ew", padx=12, pady=6)

        inner = ctk.CTkFrame(panel, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=8)

        # Recherche
        ctk.CTkLabel(inner, text="🔍", font=_f(13),
                     text_color=C.TEXT_MUTED).pack(side="left", padx=(0, 4))
        self.entry_search = ctk.CTkEntry(
            inner, width=220, height=30,
            placeholder_text="Facture, Client…",
            fg_color=C.BG_INPUT, border_color=C.BORDER,
            text_color=C.TEXT_PRIMARY, font=_f(10))
        self.entry_search.pack(side="left", padx=(0, 8))
        self.entry_search.bind("<KeyRelease>", lambda e: self.charger_donnees())

        # Dates
        ctk.CTkLabel(inner, text="Du :", font=_f(10),
                     text_color=C.TEXT_SECONDARY).pack(side="left", padx=(0, 2))
        self.date_debut = DateEntry(inner, width=10, background=C.BG_HEADER,
                                    foreground='white', borderwidth=1,
                                    date_pattern='dd/mm/yyyy', font=("Segoe UI", 9))
        self.date_debut.pack(side="left", padx=(0, 6))

        ctk.CTkLabel(inner, text="Au :", font=_f(10),
                     text_color=C.TEXT_SECONDARY).pack(side="left", padx=(0, 2))
        self.date_fin = DateEntry(inner, width=10, background=C.BG_HEADER,
                                  foreground='white', borderwidth=1,
                                  date_pattern='dd/mm/yyyy', font=("Segoe UI", 9))
        self.date_fin.pack(side="left", padx=(0, 8))

        # Statut
        ctk.CTkLabel(inner, text="Statut :", font=_f(10),
                     text_color=C.TEXT_SECONDARY).pack(side="left", padx=(0, 2))
        self.combo_statut = ctk.CTkComboBox(
            inner, values=["Tout", "VALIDEE", "EN_ATTENTE", "ANNULE", "AVOIR"],
            state="readonly", width=120, height=30,
            fg_color=C.BG_INPUT, border_color=C.BORDER,
            button_color=C.PRIMARY, font=_f(10))
        self.combo_statut.set("VALIDEE")
        self.combo_statut.pack(side="left", padx=(0, 8))
        self.combo_statut.bind("<<ComboboxSelected>>", lambda e: self.charger_donnees())

        # Magasin
        ctk.CTkLabel(inner, text="Magasin :", font=_f(10),
                     text_color=C.TEXT_SECONDARY).pack(side="left", padx=(0, 2))
        self.combo_magasin = ctk.CTkComboBox(
            inner, values=["Tout"], state="readonly",
            width=160, height=30,
            fg_color=C.BG_INPUT, border_color=C.BORDER,
            button_color=C.PRIMARY, font=_f(10))
        self.combo_magasin.set("Tout")
        self.combo_magasin.pack(side="left", padx=(0, 8))
        self.combo_magasin.bind("<<ComboboxSelected>>", lambda e: self.charger_donnees())
        self.charger_magasins_filtre()

        # Boutons droite
        self.btn_export = ctk.CTkButton(
            inner, text="📊  Excel",
            command=self.exporter_excel,
            fg_color=C.SUCCESS_DARK, hover_color=C.SUCCESS,
            text_color="#FFFFFF", height=30, width=100, font=_f(10, "bold"))
        self.btn_export.pack(side="right", padx=(6, 0))

        ctk.CTkButton(
            inner, text="🔍  Filtrer",
            command=self.charger_donnees,
            fg_color=C.PRIMARY, hover_color=C.PRIMARY_HOVER,
            text_color="#FFFFFF", height=30, width=90, font=_f(10, "bold")
        ).pack(side="right", padx=(0, 6))

        # ── Treeview ──────────────────────────────────────────────────────
        tbl = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=8)
        tbl.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 4))
        tbl.grid_rowconfigure(0, weight=1)
        tbl.grid_columnconfigure(0, weight=1)

        columns = ("date", "n_facture", "magasin", "client",
                   "montant", "statut", "user")
        self.tree = ttk.Treeview(tbl, columns=columns, show="headings",
                                 style="Facture.Treeview")
        self.tree.tag_configure("even", background=C.BG_CARD)
        self.tree.tag_configure("odd",  background="#F0F4F8")

        col_cfg = {
            "date":      ("Date",       150, "center"),
            "n_facture": ("N° Facture", 120, "center"),
            "magasin":   ("Magasin",    150, "w"),
            "client":    ("Client",     160, "w"),
            "montant":   ("Montant",    110, "e"),
            "statut":    ("Statut",     100, "center"),
            "user":      ("Vendeur",    110, "center"),
        }
        for col, (head, w, anc) in col_cfg.items():
            self.tree.heading(col, text=head)
            self.tree.column(col, width=w, anchor=anc)

        sy = ctk.CTkScrollbar(tbl, orientation="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sy.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        sy.grid(row=0, column=1, sticky="ns", pady=6)
        self.tree.bind("<ButtonRelease-1>", self.on_row_click)
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<KeyRelease-Up>", self.on_tree_key_nav)
        self.tree.bind("<KeyRelease-Down>", self.on_tree_key_nav)

        # ── Panneau détail (caché par défaut) ─────────────────────────────
        self.panel_detail = PanelDetailFacture(
            self, parent_page=self, session_data=self.session_data,
        )
        self.panel_detail.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 4))
        self.panel_detail.grid_remove()

        # ── Footer ────────────────────────────────────────────────────────
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=4, column=0, sticky="ew", padx=12, pady=(2, 8))

        self.lbl_count = ctk.CTkLabel(
            footer, text="Factures : 0",
            font=_f(10, "bold"), text_color=C.TEXT_SECONDARY)
        self.lbl_count.pack(side="left")

        self.lbl_total_mt = ctk.CTkLabel(
            footer, text="Total : 0 Ar",
            font=_f(12, "bold"), text_color=C.SUCCESS_DARK)
        self.lbl_total_mt.pack(side="right")

    # ====================================================================
    # LOGIQUE MÉTIER — inchangée
    # ====================================================================

    def get_connected_user_id(self, parent, session_data):
        parent_id = getattr(parent, "id_user_connecte", None)
        if parent_id is None:
            parent_id = getattr(parent, "iduser", None)
        if parent_id is not None:
            try:
                return int(parent_id)
            except (TypeError, ValueError):
                pass
        if isinstance(session_data, int):
            return session_data
        if isinstance(session_data, dict):
            sid = session_data.get("user_id") or session_data.get("iduser")
            if sid is not None:
                try:
                    return int(sid)
                except (TypeError, ValueError):
                    pass
        try:
            session_path = get_session_path()
            with open(session_path, "r", encoding="utf-8") as f:
                sess = json.load(f)
            sid = sess.get("user_id")
            if sid is not None:
                return int(sid)
        except Exception:
            pass
        return None

    def connect_db(self):
        try:
            with open(get_config_path('config.json')) as f:
                config = json.load(f)
            from pages.db_helper import connect_page_db
            return connect_page_db()
        except Exception:
            return None

    def formater_montant(self, valeur):
        """Transforme un nombre en format 1.000,00 ou 1.000 selon décimal"""
        try:
            v = float(valeur)
            if v % 1 == 0:
                # Entier, pas de décimale
                n = f"{int(v):,}"
                return n.replace(",", "X").replace(".", ",").replace("X", ".")
            else:
                # Décimal, deux chiffres après la virgule
                n = f"{v:,.2f}"
                n = n.replace(",", "X").replace(".", ",").replace("X", ".")
                return n
        except:
            return "0,00"

    def charger_magasins_filtre(self):
        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT idmag, designationmag FROM tb_magasin WHERE deleted = 0 ORDER BY designationmag")
            magasins = cursor.fetchall()
            self.magasin_map = {nom: idmag for idmag, nom in magasins}
            valeurs = ["Tout"] + [nom for _, nom in magasins]
            self.combo_magasin.configure(values=valeurs)
            default_nom = None
            if self.id_user_connecte:
                cursor.execute(
                    "SELECT u.idmag FROM tb_users u WHERE u.iduser = %s AND u.deleted = 0",
                    (self.id_user_connecte,))
                row = cursor.fetchone()
                if row and row[0]:
                    idmag_user  = row[0]
                    default_nom = next((nom for idmag, nom in magasins
                                        if idmag == idmag_user), None)
            self.user_default_magasin_nom = default_nom
            self.combo_magasin.set(
                default_nom if default_nom in self.magasin_map else "Tout")
        finally:
            conn.close()

    def _detail_row_weight(self, show=True):
        if show:
            self.grid_rowconfigure(2, weight=2)
            self.grid_rowconfigure(3, weight=1, minsize=220)
        else:
            self.grid_rowconfigure(2, weight=1)
            self.grid_rowconfigure(3, weight=0, minsize=0)
            self._detail_selection = None

    def charger_donnees(self):
        selection_avant = self._detail_selection
        for item in self.tree.get_children():
            self.tree.delete(item)

        val     = self.entry_search.get().strip()
        val_num = None
        if val:
            try:
                val_num = float(
                    val.replace(" ", "").replace(".", "").replace(",", "."))
            except Exception:
                val_num = None

        d1               = self.date_debut.get_date()
        d2               = self.date_fin.get_date()
        statut_filtre    = self.combo_statut.get()
        magasin_filtre_nom = self.combo_magasin.get() \
            if hasattr(self, "combo_magasin") else "Tout"
        magasin_filtre_id = self.magasin_map.get(magasin_filtre_nom)

        conn = self.connect_db()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            filtre_avoir = statut_filtre == "AVOIR"

            if filtre_avoir:
                sql = """
                    SELECT a.dateregistre, a.refavoir,
                           COALESCE((
                               SELECT m.designationmag
                               FROM tb_avoirdetail ad
                               INNER JOIN tb_magasin m ON ad.idmag = m.idmag
                               WHERE ad.idavoir = a.id AND ad.deleted = 0
                               ORDER BY ad.id
                               LIMIT 1
                           ), ''),
                           COALESCE(c.nomcli, 'Client Divers'),
                           a.mtavoir, 'AVOIR', u.username, a.id
                    FROM tb_avoir a
                    LEFT JOIN tb_client c ON a.idclient = c.idclient
                    LEFT JOIN tb_users u ON a.iduser = u.iduser
                    WHERE a.deleted = 0
                    AND (
                        a.refavoir ILIKE %s
                        OR c.nomcli ILIKE %s
                        OR CAST(COALESCE(a.mtavoir, 0) AS TEXT) ILIKE %s
                        OR CAST(COALESCE(a.mtavoir, 0) AS TEXT) ILIKE %s
                        OR (%s IS NOT NULL AND COALESCE(a.mtavoir, 0) = %s)
                    )
                    AND a.dateregistre::date BETWEEN %s AND %s
                """
            else:
                sql = """
                    SELECT v.dateregistre, v.refvente,
                           COALESCE(m.designationmag, ''),
                           COALESCE(c.nomcli, 'Client Divers'),
                           v.totmtvente, v.statut, u.username, v.id
                    FROM tb_vente v
                    LEFT JOIN tb_client c  ON v.idclient = c.idclient
                    LEFT JOIN tb_users u   ON v.iduser   = u.iduser
                    LEFT JOIN tb_magasin m ON v.idmag    = m.idmag
                    WHERE (
                        v.refvente ILIKE %s
                        OR c.nomcli ILIKE %s
                        OR CAST(COALESCE(v.totmtvente, 0) AS TEXT) ILIKE %s
                        OR CAST(COALESCE(v.totmtvente, 0) AS TEXT) ILIKE %s
                        OR (%s IS NOT NULL AND COALESCE(v.totmtvente, 0) = %s)
                    )
                    AND v.dateregistre::date BETWEEN %s AND %s
                """
            params = [
                f"%{val}%", f"%{val}%",
                f"%{val}%", f"%{val.replace(',', '.')}%",
                val_num, val_num,
                d1, d2,
            ]
            if not filtre_avoir and statut_filtre != "Tout":
                sql += " AND v.statut = %s"
                params.append(statut_filtre)
            if magasin_filtre_nom != "Tout" and magasin_filtre_id:
                if filtre_avoir:
                    sql += """
                        AND EXISTS (
                            SELECT 1 FROM tb_avoirdetail ad
                            WHERE ad.idavoir = a.id
                              AND ad.idmag = %s
                              AND ad.deleted = 0
                        )
                    """
                else:
                    sql += " AND v.idmag = %s"
                params.append(magasin_filtre_id)
            if filtre_avoir:
                sql += " ORDER BY a.dateregistre DESC, a.id DESC"
            else:
                sql += " ORDER BY v.dateregistre DESC, v.id DESC"

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            total = 0
            for idx, r in enumerate(rows):
                mt_format = self.formater_montant(r[4])
                tag       = "even" if idx % 2 == 0 else "odd"
                self.tree.insert("", "end", iid=str(r[7]), values=(
                    r[0].strftime("%d/%m/%Y %H:%M:%S"),
                    r[1], r[2], r[3], mt_format, r[5], r[6]
                ), tags=(tag,))
                total += float(r[4] or 0)

            libelle = "Avoirs" if filtre_avoir else "Factures"
            self.lbl_count.configure(text=f"{libelle} : {len(rows)}")
            self.lbl_total_mt.configure(
                text=f"Total : {self.formater_montant(total)} Ar")

            if selection_avant and self.tree.exists(selection_avant):
                self._afficher_detail_ligne(selection_avant)
            elif self.panel_detail._visible:
                self.panel_detail.masquer()
        finally:
            conn.close()

    def _afficher_detail_ligne(self, iid):
        if not iid or not self.tree.exists(iid):
            return
        values = self.tree.item(iid)['values']
        if not values:
            return
        ref_facture = values[1]
        statut = values[5]
        mode_avoir = statut == "AVOIR" or self.combo_statut.get() == "AVOIR"
        self._detail_selection = iid
        self.tree.selection_set(iid)
        self.tree.focus(iid)
        self.tree.see(iid)
        self.panel_detail.afficher(
            iid, ref_facture, statut, mode_avoir=mode_avoir,
        )

    def on_row_click(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        self._afficher_detail_ligne(iid)

    def on_tree_key_nav(self, event):
        if event.keysym not in ("Up", "Down"):
            return
        if not self.panel_detail._visible:
            return
        self.after_idle(self._sync_detail_keyboard)

    def _sync_detail_keyboard(self):
        if not self.panel_detail._visible:
            return
        iid = self.tree.focus()
        if not iid:
            sel = self.tree.selection()
            iid = sel[0] if sel else None
        if iid:
            self._afficher_detail_ligne(iid)

    def on_double_click(self, event):
        selected_item = self.tree.focus()
        if not selected_item:
            return
        values      = self.tree.item(selected_item)['values']
        ref_facture = values[1]
        statut      = values[5]
        mode_avoir  = statut == "AVOIR" or self.combo_statut.get() == "AVOIR"
        PageDetailFacture(
            self, selected_item, ref_facture, statut,
            parent_page=self, mode_avoir=mode_avoir,
        )

    def exporter_excel(self):
        lignes = [self.tree.item(item)['values']
                  for item in self.tree.get_children()]
        if not lignes:
            messagebox.showwarning("Vide", "Rien à exporter")
            return
        df = pd.DataFrame(
            lignes,
            columns=["Date", "N° Facture", "Magasin", "Client",
                     "Montant", "Statut", "Vendeur"])
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=f"Rapport_Ventes_{datetime.now().strftime('%Y%m%d')}")
        if file_path:
            df.to_excel(file_path, index=False)
            messagebox.showinfo(
                "Export réussi",
                f"Le fichier a été enregistré sous :\n{file_path}")
            try:
                self._logger.log(
                    action="Export Excel",
                    element="Liste Facture",
                    details=f"export factures, lignes={len(lignes)}, fichier={os.path.basename(file_path)}",
                    value=file_path,
                )
            except Exception:
                pass