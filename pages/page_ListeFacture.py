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


# ====================================================================
# PageDetailFacture
# ====================================================================

class PageDetailFacture(ctk.CTkToplevel):
    """Fenêtre affichant les articles d'une facture spécifique"""

    def __init__(self, master, idvente, refvente,
                 statut="EN_ATTENTE", parent_page=None):
        super().__init__(master)
        self.title(f"Détails Facture : {refvente}")
        self.geometry("860x560")
        if _T:
            Theme.apply_toplevel(self)
        self.attributes('-topmost', True)

        self.idvente      = idvente
        self.refvente     = refvente
        self.statut       = statut
        self.parent_page  = parent_page
        self.montant_total= 0
        self.mode_paiement= "N/A"

        _apply_tree_style("Detail")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── En-tête ───────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=C.BG_HEADER, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            hdr, text=f"Détails Facture — {refvente}",
            font=_f(16, "bold"), text_color="#FFFFFF"
        ).pack(side="left", padx=16, pady=10)

        # Badge statut
        badge_colors = {
            "VALIDEE":    (C.SUCCESS_DARK, "#FFFFFF"),
            "EN_ATTENTE": (C.WARNING,      "#FFFFFF"),
            "ANNULE":     (C.DANGER,       "#FFFFFF"),
        }
        bg_s, fg_s = badge_colors.get(statut, (C.TEXT_MUTED, "#FFFFFF"))
        ctk.CTkLabel(
            hdr, text=f"  {statut}  ",
            font=_f(9, "bold"), text_color=fg_s,
            fg_color=bg_s, corner_radius=4
        ).pack(side="right", padx=16, pady=10)

        # ── Treeview ──────────────────────────────────────────────────────────
        tbl = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=8)
        tbl.grid(row=1, column=0, sticky="nsew", padx=12, pady=6)
        tbl.grid_rowconfigure(0, weight=1)
        tbl.grid_columnconfigure(0, weight=1)

        cols = ("code", "designation", "qte", "prix", "total")
        self.tree = ttk.Treeview(tbl, columns=cols, show="headings",
                                 style="Detail.Treeview")
        self.tree.tag_configure("even", background=C.BG_CARD)
        self.tree.tag_configure("odd",  background="#F0F4F8")

        self.tree.heading("code",        text="Code")
        self.tree.heading("designation", text="Désignation")
        self.tree.heading("qte",         text="Qté")
        self.tree.heading("prix",        text="Prix Unit.")
        self.tree.heading("total",       text="Total")

        self.tree.column("code",        width=80,  minwidth=60, anchor="center")
        self.tree.column("designation", width=350, anchor="w")
        self.tree.column("qte",         width=70,  anchor="center")
        self.tree.column("prix",        width=110, anchor="e")
        self.tree.column("total",       width=130, anchor="e")

        sy = ctk.CTkScrollbar(tbl, orientation="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sy.set)

        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        sy.grid(row=0, column=1, sticky="ns", pady=6)

        # ── Footer ────────────────────────────────────────────────────────────
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

        right = ctk.CTkFrame(footer, fg_color="transparent")
        right.pack(side="right", padx=16, pady=12)

        if self.statut == "VALIDEE":
            ctk.CTkButton(
                right, text="🖨️  Réimprimer (Duplicata)",
                command=self.reimprimer_duplicata,
                fg_color=C.PRIMARY, hover_color=C.PRIMARY_HOVER,
                text_color="#FFFFFF", height=32, width=210,
                font=_f(10, "bold")
            ).pack(pady=(0, 4))

        if self.statut == "EN_ATTENTE":
            ctk.CTkButton(
                right, text="❌  Annuler Facture",
                command=self.annuler_facture,
                fg_color=C.DANGER, hover_color=C.DANGER_DARK,
                text_color="#FFFFFF", height=32, width=180,
                font=_f(10, "bold")
            ).pack(pady=(0, 4))

        if self.statut == "ANNULE":
            ctk.CTkLabel(
                right, text="⚠️  Facture Annulée",
                text_color=C.DANGER, font=_f(11, "bold")
            ).pack(pady=4)

        self.charger_details(idvente)
        try:
            session_data = {}
            if parent_page and hasattr(parent_page, "session_data") and isinstance(parent_page.session_data, dict):
                session_data = parent_page.session_data
            self._logger = AppLogger(session_data=session_data)
        except Exception:
            self._logger = None

    # ====================================================================
    # LOGIQUE MÉTIER — inchangée
    # ====================================================================

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
            conn = psycopg2.connect(**config['database'])
            cursor = conn.cursor()

            sql_vente = "SELECT v.totmtvente FROM tb_vente v WHERE v.id = %s"
            cursor.execute(sql_vente, (idvente,))
            result = cursor.fetchone()
            if result:
                self.montant_total = float(result[0]) if result[0] else 0
                self.lbl_montant.configure(
                    text=f"{self.formater_montant(self.montant_total)} Ar")

            sql = """
                SELECT u.codearticle, a.designation, vd.qtvente, vd.prixunit,
                       (vd.qtvente * (vd.prixunit - vd.remise)) as total
                FROM tb_ventedetail vd
                INNER JOIN tb_unite u ON vd.idunite = u.idunite
                INNER JOIN tb_article a ON vd.idarticle = a.idarticle
                WHERE vd.idvente = %s
            """
            cursor.execute(sql, (idvente,))
            for idx, r in enumerate(cursor.fetchall()):
                tag = "even" if idx % 2 == 0 else "odd"
                self.tree.insert("", "end", values=(
                    r[0], r[1], self.formater_montant(float(r[2])),
                    f"{self.formater_montant(float(r[3]))}",
                    f"{self.formater_montant(float(r[4]))}"
                ), tags=(tag,))
            conn.close()
        except Exception as e:
            messagebox.showerror("Erreur SQL",
                                 f"Erreur lors du chargement des détails : {e}")

    def reimprimer_duplicata(self):
        """Génère un duplicata de la facture"""
        try:
            from pages.page_vente import PageVente
            with open(get_config_path('config.json')) as f:
                config = json.load(f)
            conn = psycopg2.connect(**config['database'])
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
                "SELECT nomsociete, adressesociete, contactsociete, nifsociete, statsociete FROM tb_infosociete LIMIT 1")
            societe_result = cursor.fetchone()
            conn.close()

            societe_info = {
                'nomsociete':     societe_result[0] if societe_result else 'N/A',
                'adressesociete': societe_result[1] if societe_result else 'N/A',
                'contactsociete': societe_result[2] if societe_result else 'N/A',
                'nifsociete':     societe_result[3] if societe_result else 'N/A',
                'statsociete':    societe_result[4] if societe_result else 'N/A',
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

            page_vente = PageVente.__new__(PageVente)
            page_vente.infos_societe = societe_info

            safe_ref = refvente.replace("/", "-").replace("\\", "-")
            basename = f"DUPLICATA_Facture_{safe_ref}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            filename, is_temp = build_impression_output_path(
                basename, temp_prefix="ijeery_duplicata_"
            )

            self.generate_pdf_a5_duplicata(data, filename, page_vente)
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
            
            self.destroy()

        except Exception as e:
            messagebox.showerror("Erreur",
                                 f"Erreur lors de la génération du duplicata : {str(e)}")
            import traceback
            traceback.print_exc()

    def annuler_facture(self):
        """Annule la facture (change le statut à 'ANNULE')"""
        if messagebox.askyesno(
                parent=self, title="Confirmation",
                message=f"Voulez-vous annuler la facture {self.refvente} ?"):
            try:
                with open(get_config_path('config.json')) as f:
                    config = json.load(f)
                conn = psycopg2.connect(**config['database'])
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
                if hasattr(self, 'btn_annuler'):
                    self.btn_annuler.pack_forget()
                if self.parent_page:
                    self.parent_page.charger_donnees()
                self.destroy()
            except Exception as e:
                messagebox.showerror("Erreur",
                                     f"Erreur lors de l'annulation : {str(e)}")
                import traceback
                traceback.print_exc()
            finally:
                if 'conn' in locals():
                    conn.close()

    def generate_pdf_a5_duplicata(self, data, filename, page_vente):
        """
        Génère un PDF duplicata avec le label 'DUPLICATA'.
        - Multi-pages si articles > 25
        - TOTAL Ar toujours en bas du tableau
        - Somme en lettres avec retour à la ligne auto + marges gauche/droite
        """
        from reportlab.lib.pagesizes import A5
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.platypus import Table, TableStyle, Paragraph
        from xml.sax.saxutils import escape
        from pages.page_vente import nombre_en_lettres_fr

        MAX_ARTICLES_PAGE1     = 25
        MAX_ARTICLES_SUIVANTES = 30
        MARGIN                 = 10 * mm

        dname = os.path.dirname(os.path.abspath(filename))
        if dname:
            os.makedirs(dname, exist_ok=True)

        c = canvas.Canvas(filename, pagesize=A5)
        width, height = A5

        societe     = data['societe']
        utilisateur = data['utilisateur']
        client      = data['client']
        vente       = data['vente']

        nomsociete     = societe.get('nomsociete', 'N/A')
        adressesociete = societe.get('adressesociete') or societe.get('adresse', 'N/A')
        contactsociete = societe.get('contactsociete') or societe.get('tel', 'N/A')
        nifsociete     = societe.get('nifsociete') or societe.get('nif', 'N/A')
        statsociete    = societe.get('statsociete') or societe.get('stat', 'N/A')

        if isinstance(utilisateur, dict):
            pren      = utilisateur.get('prenomuser') or ''
            nomu      = utilisateur.get('nomuser') or ''
            user_name = f"{pren} {nomu}".strip()
        else:
            user_name = str(utilisateur) if utilisateur is not None else ''

        def fmt(valeur):
            if hasattr(page_vente, 'formater_nombre'):
                return page_vente.formater_nombre(valeur)
            try:
                return f"{float(valeur):,.0f}".replace(",", " ")
            except Exception:
                return str(valeur)

        def draw_verset():
            verset = "Ankino amin'ny Jehovah ny asanao dia ho lavorary izay kasainao. Ohabolana 16:3"
            c.setLineWidth(1)
            c.rect(MARGIN, height - 15*mm, width - 2*MARGIN, 8*mm)
            c.setFont("Helvetica-Bold", 9)
            c.drawCentredString(width / 2, height - 12.5*mm, verset)

        def draw_header(is_continuation=False):
            styles  = getSampleStyleSheet()
            style_p = ParagraphStyle('style_p', fontSize=9, leading=11,
                                     parent=styles['Normal'])
            gauche_text = (
                f"<b>{nomsociete}</b><br/>"
                f"{adressesociete}<br/>"
                f"TEL: {contactsociete}<br/>"
                f"NIF: {nifsociete} | STAT: {statsociete}"
            )
            suite_label = " <i>(suite)</i>" if is_continuation else ""
            droite_text = (
                f"<b>Facture N°: {vente['refvente']}{suite_label}</b><br/>"
                f"{vente['dateregistre']}<br/>"
                f"<b>Magasin: {data['details'][0]['magasin'] if data['details'] else 'N/A'}</b><br/>"
                f"<b>Client: {client['nomcli']}</b><br/>"
                f"<font size='8'>Op: {user_name}</font>"
            )
            gauche = Paragraph(gauche_text, style_p)
            droite = Paragraph(droite_text, style_p)
            ht = Table([[gauche, droite]], colWidths=[64*mm, 64*mm])
            ht.setStyle(TableStyle([
                ('GRID',          (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING',   (0, 0), (-1, -1), 8),
                ('TOPPADDING',    (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            ht.wrapOn(c, width, height)
            ht.drawOn(c, MARGIN, height - 48*mm)

        def draw_duplicata_label():
            c.setFont("Helvetica-Bold", 14)
            c.setFillColor(colors.HexColor("#D32F2F"))
            c.drawCentredString(width / 2, height - 51*mm, "DUPLICATA")
            c.setFillColor(colors.HexColor("#000000"))

        def draw_footer(total_montant, table_bottom):
            usable_width    = width - 2 * MARGIN
            montant_lettres = nombre_en_lettres_fr(int(total_montant)).upper()
            full_text       = f"ARRETE A LA SOMME DE {montant_lettres}"
            styles  = getSampleStyleSheet()
            style_b = ParagraphStyle('footer_bold', parent=styles['Normal'],
                                     fontName='Helvetica-Bold', fontSize=9,
                                     leading=12, alignment=1)
            style_i = ParagraphStyle('footer_italic', parent=styles['Normal'],
                                     fontName='Helvetica-Oblique', fontSize=8,
                                     leading=10, alignment=1)
            p_lettre   = Paragraph(full_text, style_b)
            p_mention1 = Paragraph(
                "Nous déclinons la responsabilité des marchandises "
                "non livrées au-delà de 5 jours", style_i)
            p_mention2 = Paragraph("CECI EST UN DUPLICATA DE LA FACTURE", style_i)
            _, h_l  = p_lettre.wrap(usable_width, 40*mm)
            _, h_m1 = p_mention1.wrap(usable_width, 20*mm)
            _, h_m2 = p_mention2.wrap(usable_width, 20*mm)
            gap        = 3 * mm
            y_lettre   = table_bottom - gap - h_l
            y_mention1 = y_lettre   - 2*mm - h_m1
            y_mention2 = y_mention1 - 1*mm - h_m2
            p_lettre.drawOn(c,   MARGIN, y_lettre)
            p_mention1.drawOn(c, MARGIN, y_mention1)
            p_mention2.drawOn(c, MARGIN, y_mention2)
            sig_y = 15*mm
            c.setFont("Helvetica-Bold", 10)
            c.drawString(MARGIN, sig_y, "Le Client")
            c.drawCentredString(width / 2, sig_y, "Le Caissier")
            c.drawString(width - 35*mm, sig_y, "Le Magasinier")

        def draw_article_table(table_top, table_bottom, rows,
                               show_totals, total_montant=0):
            frame_height = table_top - table_bottom
            col_widths   = [11*mm, 12*mm, 56*mm, 18*mm, 15*mm, 16*mm]
            avail_w      = sum(col_widths)
            styles       = getSampleStyleSheet()
            style_des_cell = ParagraphStyle(
                'dup_des', parent=styles['Normal'],
                fontName='Helvetica', fontSize=8, leading=9, wordWrap='LTR',
            )
            row_height_est   = 5.5 * mm
            max_rows_visible = int(frame_height / row_height_est)
            reserved_bottom  = 1 if show_totals else 0
            content_slots    = max_rows_visible - 1 - reserved_bottom
            body = []
            for r in rows:
                raw_des = str(r[2] or '').replace('\r\n', '\n').replace('\r', '\n')
                des_p = Paragraph(
                    '<br/>'.join(escape(p) for p in raw_des.split('\n')),
                    style_des_cell,
                )
                body.append([r[0], r[1], des_p, r[3], r[4], r[5]])
            max_fill = max(0, min(content_slots - len(body), 15))
            for _ in range(max_fill):
                body.append(['', '', '', '', '', ''])
            if show_totals:
                total_row  = ['', '', 'TOTAL Ar :', '', '', fmt(total_montant)]
                table_data = [['QTE', 'UNITE', 'DESIGNATION', 'PU', 'REMISE', 'MONTANT']] \
                             + body + [total_row]
            else:
                table_data = [['QTE', 'UNITE', 'DESIGNATION', 'PU', 'REMISE', 'MONTANT']] \
                             + body
            style_cmds = [
                ('BACKGROUND',    (0, 0),  (-1, 0),  colors.lightgrey),
                ('FONTNAME',      (0, 0),  (-1, 0),  'Helvetica-Bold'),
                ('FONTSIZE',      (0, 0),  (-1, 0),  10),
                ('LINEBELOW',     (0, 0),  (-1, 0),  1, colors.black),
                ('FONTSIZE',      (0, 1),  (-1, -1),  8),
                ('ALIGN',         (3, 0),  (-1, -1), 'RIGHT'),
                ('ALIGN',         (0, 0),  (2, 0),   'LEFT'),
                ('VALIGN',        (0, 0),  (-1, 0),  'MIDDLE'),
                ('LEFTPADDING',   (0, 0),  (-1, -1),  2),
                ('RIGHTPADDING',  (3, 0),  (-1, -1),  2),
                ('TOPPADDING',    (0, 0),  (-1, -1),  0),
                ('BOTTOMPADDING', (0, 0),  (-1, -1),  0),
            ]
            if show_totals:
                style_cmds += [
                    ('VALIGN', (0, 1), (-1, -2), 'TOP'),
                    ('VALIGN', (0, -1), (-1, -1), 'MIDDLE'),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.93, 0.93, 0.93)),
                    ('FONTNAME',   (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('FONTSIZE',   (0, -1), (-1, -1),  9),
                    ('LINEABOVE',  (0, -1), (-1, -1),  1, colors.black),
                    ('ALIGN',      (2, -1), (2, -1),  'RIGHT'),
                ]
            else:
                style_cmds += [('VALIGN', (0, 1), (-1, -1), 'TOP')]
            t = Table(table_data, colWidths=col_widths)
            t.setStyle(TableStyle(style_cmds))
            t.wrapOn(c, avail_w, frame_height * 100)
            c.setLineWidth(1)
            c.rect(MARGIN, table_bottom, width - 2*MARGIN, frame_height)
            x_pos = MARGIN
            for w in col_widths[:-1]:
                x_pos += w
                c.line(x_pos, table_top, x_pos, table_bottom)
            c.saveState()
            _clip = c.beginPath()
            _clip.rect(MARGIN, table_bottom, width - 2*MARGIN, frame_height)
            c.clipPath(_clip, stroke=0, fill=0)
            t.drawOn(c, MARGIN, table_bottom)
            c.restoreState()
            return table_bottom

        total_montant = 0
        all_rows = []
        for detail in data['details']:
            qte = float(detail.get('qte', 0) or 0)
            pu = float(detail.get('prixunit', 0) or 0)
            rem = float(detail.get('remise', 0) or 0)
            montant = detail.get('montant_ttc', detail.get('montant'))
            if montant is None:
                montant = max(0.0, qte * pu - qte * rem)
            else:
                montant = float(montant)
            total_montant += montant
            all_rows.append([
                str(int(detail.get('qte', 0))),
                str(detail.get('unite', '')),
                str(detail.get('designation', '')),
                fmt(pu),
                fmt(rem),
                fmt(montant),
            ])

        pages = []
        if len(all_rows) <= MAX_ARTICLES_PAGE1:
            pages.append(('first', all_rows))
        else:
            pages.append(('first', all_rows[:MAX_ARTICLES_PAGE1]))
            reste = all_rows[MAX_ARTICLES_PAGE1:]
            while reste:
                pages.append(('continuation', reste[:MAX_ARTICLES_SUIVANTES]))
                reste = reste[MAX_ARTICLES_SUIVANTES:]

        for page_idx, (page_type, rows) in enumerate(pages):
            is_last = (page_idx == len(pages) - 1)
            draw_verset()
            draw_header(is_continuation=(page_type == 'continuation'))
            draw_duplicata_label()
            table_top    = height - 55*mm
            table_bottom = 65*mm if is_last else 15*mm
            tb = draw_article_table(table_top, table_bottom, rows,
                                    show_totals=is_last,
                                    total_montant=total_montant)
            if is_last:
                draw_footer(total_montant, table_bottom=tb)
            if len(pages) > 1:
                c.setFont("Helvetica", 7)
                c.drawCentredString(width / 2, 8*mm,
                                    f"Page {page_idx + 1} / {len(pages)}")
            if not is_last:
                c.showPage()

        try:
            c.save()
        except Exception as e:
            print(f"❌ Erreur PDF Duplicata : {e}")
            import traceback
            traceback.print_exc()


# ====================================================================
# PageListeFacture
# ====================================================================

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
            inner, values=["Tout", "VALIDEE", "EN_ATTENTE", "ANNULE"],
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
        self.tree.bind("<Double-1>", self.on_double_click)

        # ── Footer ────────────────────────────────────────────────────────
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=12, pady=(2, 8))

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
            return psycopg2.connect(**config['database'])
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

    def charger_donnees(self):
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
            if statut_filtre != "Tout":
                sql += " AND v.statut = %s"
                params.append(statut_filtre)
            if magasin_filtre_nom != "Tout" and magasin_filtre_id:
                sql += " AND v.idmag = %s"
                params.append(magasin_filtre_id)
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
                total += float(r[4])

            self.lbl_count.configure(text=f"Factures : {len(rows)}")
            self.lbl_total_mt.configure(
                text=f"Total : {self.formater_montant(total)} Ar")
        finally:
            conn.close()

    def on_double_click(self, event):
        selected_item = self.tree.focus()
        if not selected_item:
            return
        values      = self.tree.item(selected_item)['values']
        ref_facture = values[1]
        statut      = values[5]
        PageDetailFacture(self, selected_item, ref_facture, statut, parent_page=self)

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