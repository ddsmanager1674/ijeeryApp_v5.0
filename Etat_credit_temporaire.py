from reportlab.lib.pagesizes import landscape, A5
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import os
import subprocess
from datetime import datetime


class EtatCreditTemporaire:
    """Prototype PDF temporaire pour l'interface d'un etat d'acceptation de credit."""

    PAGE_WIDTH, PAGE_HEIGHT = landscape(A5)
    MARGIN = 5 * mm

    COLOR_HEADER = colors.HexColor("#034787")
    COLOR_BORDER = colors.black
    COLOR_BG_TABLE_HEADER = colors.HexColor("#E8E8E8")

    def _open_pdf_in_chrome(self, pdf_path):
        """Ouvre le PDF genere dans Chrome, sinon lecteur par defaut."""
        try:
            abs_path = os.path.abspath(pdf_path)
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                "chrome",
                "google-chrome",
            ]

            for chrome_path in chrome_paths:
                if os.path.exists(chrome_path) or chrome_path in ["chrome", "google-chrome"]:
                    try:
                        subprocess.Popen([chrome_path, f"file:///{abs_path}"])
                        return
                    except Exception:
                        continue

            if os.name == "nt":
                os.startfile(abs_path)
            else:
                subprocess.Popen(["open", abs_path])
        except Exception as e:
            print(f"Impossible d'ouvrir le PDF automatiquement: {e}")

    def generer_pdf_temporaire(self, output_path=None):
        """Genere un etat PDF temporaire pour illustrer l'interface."""
        if not output_path:
            output_path = f"Etat_Credit_Temporaire_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        doc = SimpleDocTemplate(
            output_path,
            pagesize=landscape(A5),
            rightMargin=self.MARGIN,
            leftMargin=self.MARGIN,
            topMargin=self.MARGIN,
            bottomMargin=self.MARGIN,
        )

        elements = []
        styles = getSampleStyleSheet()
        page_width_usable = self.PAGE_WIDTH - 2 * self.MARGIN

        verse_title = Paragraph(
            "Ankino amin'ny Jehovah ny asanao dia ho lavorary izay kasainao. Ohabolana 16:3",
            ParagraphStyle(
                "MainTitle",
                parent=styles["Normal"],
                fontSize=10,
                textColor=colors.black,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
                spaceAfter=3,
            ),
        )
        verse_table = Table([[verse_title]], colWidths=[page_width_usable])
        verse_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ]))
        elements.append(verse_table)

        company_width = page_width_usable * 0.33
        operation_width = page_width_usable * 0.67 - 2 * mm
        header_height = 28 * mm

        company_details = Paragraph(
            "<b>IJEERY</b><br/>"
            "Adresse : Lot II M 85, Tsaravatsy<br/>"
            "Ville : Antananarivo<br/>"
            "Contact : +261 34 00 000 00<br/>"
            "NIF : 000 000 0000<br/>"
            "STAT : 00000 00 00000 00000",
            ParagraphStyle(
                "CompanyDetails",
                parent=styles["Normal"],
                fontSize=9,
                alignment=TA_LEFT,
                leading=12,
            ),
        )
        company_table = Table([[company_details]], colWidths=[company_width - 2 * mm], rowHeights=[header_height])
        company_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, self.COLOR_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))

        title_width = operation_width * 0.55
        info_width = operation_width * 0.45

        operation_title = Paragraph(
            "ACCEPTATION DE CREDIT",
            ParagraphStyle(
                "OpTitle",
                parent=styles["Normal"],
                fontSize=14,
                fontName="Helvetica-Bold",
                alignment=TA_CENTER,
                textColor=self.COLOR_HEADER,
            ),
        )
        operation_info = Paragraph(
            f"<b>Reference :</b> CRD-TEMP-001<br/>"
            f"<b>Date :</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}<br/>"
            f"<b>Magasin :</b> Tsaravatsy<br/>"
            f"<b>Operateur :</b> Utilisateur Test",
            ParagraphStyle(
                "OpInfo",
                parent=styles["Normal"],
                fontSize=9,
                alignment=TA_LEFT,
                leading=12,
            ),
        )

        operation_table = Table([[operation_title, operation_info]], colWidths=[title_width, info_width], rowHeights=[header_height])
        operation_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, self.COLOR_BORDER),
            ("ALIGN", (0, 0), (0, 0), "CENTER"),
            ("ALIGN", (1, 0), (1, 0), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))

        header_table = Table([[company_table, operation_table]], colWidths=[company_width, operation_width])
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINELEFT", (0, 0), (0, 0), 1, self.COLOR_BORDER),
            ("LINERIGHT", (0, 0), (0, 0), 1, self.COLOR_BORDER),
            ("LINELEFT", (1, 0), (1, 0), 1, self.COLOR_BORDER),
            ("LINERIGHT", (1, 0), (1, 0), 1, self.COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), -2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (0, 0), 8),
            ("LEFTPADDING", (1, 0), (1, 0), 8),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 4 * mm))

        infosCredit = Paragraph(
            "&nbsp;&nbsp;&nbsp;<b><u>Infos Credit</u>:</b>",
            ParagraphStyle(
                "InfosClient",
                parent=styles["Normal"],
                fontSize=9,
                alignment=TA_LEFT,
                leading=11,
            ),
        )
        elements.append(infosCredit)

        elements.append(Spacer(1, 4 * mm))

        columns = ["Ref. Facture", "Nom Client", "Montant", "Date echeance"]
        data_rows = [
            ["FAC-2026-001", "Rakoto Jean", "250 000 Ar", "05/03/2026"],
            ["FAC-2026-002", "Rasoanaivo Lala", "180 000 Ar", "10/03/2026"],
            ["FAC-2026-003", "Andry Hery", "320 000 Ar", "15/03/2026"],
        ]

        table_width = page_width_usable * 0.95
        col_widths = [table_width * 0.22, table_width * 0.34, table_width * 0.20, table_width * 0.24]

        cell_style = ParagraphStyle(
            "CellText",
            parent=styles["Normal"],
            fontSize=11,
            alignment=TA_LEFT,
            wordWrap="CJK",
        )

        table_rows = [[Paragraph(col, cell_style) for col in columns]]
        for row in data_rows:
            table_rows.append([Paragraph(str(cell), cell_style) for cell in row])

        credit_table = Table(table_rows, colWidths=col_widths, repeatRows=1)
        credit_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), self.COLOR_BG_TABLE_HEADER),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 5),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
            ("ALIGN", (0, 1), (1, -1), "LEFT"),
            ("ALIGN", (2, 1), (3, -1), "CENTER"),
            ("VALIGN", (0, 1), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 1), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
            ("LEFTPADDING", (0, 1), (-1, -1), 3),
            ("RIGHTPADDING", (0, 1), (-1, -1), 3),
            ("BOX", (0, 0), (-1, -1), 1, self.COLOR_BORDER),
            ("LINEBEFORE", (1, 0), (1, -1), 1, self.COLOR_HEADER),
            ("LINEBEFORE", (2, 0), (2, -1), 1, self.COLOR_HEADER),
            ("LINEBEFORE", (3, 0), (3, -1), 1, self.COLOR_HEADER),
        ]))

        elements.append(credit_table)
        elements.append(Spacer(1, 3 * mm))

        infos_client = Paragraph(
            "<br/>&nbsp;&nbsp;&nbsp;<b><u>Coordonées Client</u>:</b> Lot XX quelquePart | Tel : +261 34 00 000 00<br/><br/>",
            ParagraphStyle(
                "InfosClient",
                parent=styles["Normal"],
                fontSize=9,
                alignment=TA_LEFT,
                leading=11,
            ),
        )
        elements.append(infos_client)


        description = Paragraph(
            "<b>&nbsp;&nbsp;&nbsp;<u>Description:</u></b> "
            "Etat temporaire d'acceptation de credit pour illustration de l'interface PDF."
            "<br/><br/>",
            ParagraphStyle(
                "Description",
                parent=styles["Normal"],
                fontSize=9,
                alignment=TA_LEFT,
                leading=10,
            ),
        )
        elements.append(description)

        sig_left = Paragraph("<u>Le Responsable</u>", ParagraphStyle(
            "SigLeft",
            parent=styles["Normal"],
            fontSize=9,
            alignment=TA_LEFT,
        ))
        sig_right = Paragraph("<u>Le Client</u>", ParagraphStyle(
            "SigRight",
            parent=styles["Normal"],
            fontSize=9,
            alignment=TA_CENTER,
        ))

        sig_table = Table(
            [[sig_left, "", sig_right]],
            colWidths=[
                page_width_usable * 0.35,
                page_width_usable * 0.30,
                page_width_usable * 0.35,
            ],
        )
        sig_table.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("ALIGN", (2, 0), (2, 0), "RIGHT"),
            ("RIGHTPADDING", (2, 0), (2, 0), 0),
        ]))
        elements.append(sig_table)

        try:
            doc.build(elements)
            print(f"PDF temporaire genere: {output_path}")
            self._open_pdf_in_chrome(output_path)
            return True
        except Exception as e:
            print(f"Erreur lors de la generation du PDF: {e}")
            return False


if __name__ == "__main__":
    etat = EtatCreditTemporaire()
    etat.generer_pdf_temporaire()

