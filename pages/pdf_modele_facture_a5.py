# -*- coding: utf-8 -*-
"""
Modèle PDF A5 paysage — aligné sur la facture « ventes par dépôt » (page_venteParMsin).
Utilisé par les impressions AVOIR et duplicata facture pour un rendu identique.
"""
from __future__ import annotations

import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple

from reportlab.lib.pagesizes import A5
from reportlab.lib import colors as rl_colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (
    Paragraph,
    Table as RLTable,
    TableStyle as RLTableStyle,
)


def formater_nombre_pdf_defaut(n: Any) -> str:
    """Format entier PDF (même règle que PageVenteParMsin.formater_nombre_pdf)."""
    try:
        return "{:,.0f}".format(float(n)).replace(",", ".")
    except Exception:
        return "0"


def detail_vers_ligne_facture(d: Any) -> Optional[Dict[str, Any]]:
    """
    Normalise une ligne de détail (dict vente ou tuple avoir) vers :
    qte, unite, designation, prixunit, remise (unitaire), montant_ttc
    """
    if isinstance(d, dict):
        qte = float(d.get("qte", d.get("qtvente", 0)) or 0)
        pu = float(d.get("prixunit", 0) or 0)
        rem = float(d.get("remise", 0) or 0)
        mt = d.get("montant_ttc", d.get("montant"))
        if mt is None:
            mt = max(0.0, qte * pu - qte * rem)
        else:
            mt = float(mt or 0)
        return {
            "qte": qte,
            "unite": str(d.get("unite", "") or ""),
            "designation": str(d.get("designation", "") or ""),
            "prixunit": pu,
            "remise": rem,
            "montant_ttc": mt,
        }

    if isinstance(d, (list, tuple)) and len(d) >= 8:
        _code, designation, unite, qtavoir, prixunit_net, montant_total, _mag, pu_ttc_brut = d[:8]
        pu_brut = float(pu_ttc_brut or 0)
        pu_net = float(prixunit_net or 0)
        rem = max(0.0, pu_brut - pu_net)
        return {
            "qte": float(qtavoir or 0),
            "unite": str(unite or ""),
            "designation": str(designation or ""),
            "prixunit": pu_brut,
            "remise": rem,
            "montant_ttc": float(montant_total or 0),
        }

    if isinstance(d, (list, tuple)) and len(d) >= 7:
        _code, designation, unite, qtavoir, prixunit_net, montant_total, _mag = d[:7]
        pu = float(prixunit_net or 0)
        return {
            "qte": float(qtavoir or 0),
            "unite": str(unite or ""),
            "designation": str(designation or ""),
            "prixunit": pu,
            "remise": 0.0,
            "montant_ttc": float(montant_total or 0),
        }

    return None


def generer_pdf_a5_modele_ventedepot(
    filename: str,
    *,
    societe: Dict[str, Any],
    utilisateur: Dict[str, Any],
    client: Dict[str, Any],
    magasin_nom: str,
    html_right_header: str,
    details: List[Any],
    nombre_en_lettres_fr: Callable[[float], str],
    formater_nombre_pdf: Optional[Callable[[Any], str]] = None,
    overlay_apres_entete: Optional[Callable[[Any, float, float], None]] = None,
    paragraphes_footer_supplement: Tuple[str, ...] = (),
) -> None:
    """
    Génère un PDF A5 paysage (même mise en page que ventes par dépôt).

    :param html_right_header: contenu HTML ReportLab pour la cellule droite de l'en-tête.
    :param details: dicts (vente) ou tuples (avoir) — normalisés via detail_vers_ligne_facture.
    :param overlay_apres_entete: optionnel, ex. libellé DUPLICATA (canvas, width, height).
    :param paragraphes_footer_supplement: HTML additionnels (italique) sous la mention standard.
    """
    fmt_pdf = formater_nombre_pdf or formater_nombre_pdf_defaut

    MAX_P1 = 25
    MAX_PN = 30
    MARGIN = 10 * mm

    c = rl_canvas.Canvas(filename, pagesize=A5)
    width, height = A5
    soc = societe

    nomsoc = soc.get("nomsociete", "N/A")
    adr = soc.get("adressesociete") or "N/A"
    ville = soc.get("villesociete") or ""
    tel = soc.get("contactsociete") or "N/A"
    nif = soc.get("nifsociete") or "N/A"
    stat = soc.get("statsociete") or "N/A"

    styles = getSampleStyleSheet()
    sp = ParagraphStyle("sp", fontSize=9, leading=11, parent=styles["Normal"])

    def draw_verset():
        verse = (
            "Ankino amin'ny Jehovah ny asanao dia ho lavorary izay kasainao. Ohabolana 16:3"
        )
        c.setLineWidth(1)
        c.rect(MARGIN, height - 13 * mm, width - 2 * MARGIN, 8 * mm)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(width / 2, height - 10.5 * mm, verse)

    def draw_header(cont: bool = False):
        g = Paragraph(
            f"<b><font size='11'>{nomsoc}</font></b><br/>{adr}<br/>"
            f"{'' + ville + '<br/>' if ville else ''}TEL: {tel}<br/>NIF: {nif}<br/>STAT: {stat}",
            sp,
        )
        suite = " <i>(suite)</i>" if cont else ""
        d_ = Paragraph(html_right_header.replace("{SUITE}", suite), sp)
        ht = RLTable([[g, d_]], colWidths=[64 * mm, 64 * mm])
        ht.setStyle(
            RLTableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 1, rl_colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        ht.wrapOn(c, width, height)
        ht.drawOn(c, MARGIN, height - 42 * mm)
        if overlay_apres_entete:
            overlay_apres_entete(c, width, height)

    def draw_footer(total_m: float, table_bottom: float):
        usable = width - 2 * MARGIN
        lettres = nombre_en_lettres_fr(int(total_m)).upper()

        band_h = 14 * mm
        band_y = table_bottom - band_h
        c.setLineWidth(1.2)
        c.rect(MARGIN, band_y, usable, band_h)

        mid_y = band_y + band_h / 2
        c.setLineWidth(0.5)
        c.line(MARGIN, mid_y, MARGIN + usable, mid_y)

        sep_x = MARGIN + usable * 0.60
        c.line(sep_x, band_y, sep_x, band_y + band_h)

        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(sep_x - 3, band_y + band_h / 2 + 1.5 * mm, "TOTAL ARIARY:")
        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(
            MARGIN + usable - 3,
            band_y + band_h / 2 + 1.5 * mm,
            fmt_pdf(total_m),
        )

        c.setFont("Helvetica-BoldOblique", 9)
        c.drawRightString(sep_x - 3, band_y + band_h / 2 - 5.5 * mm, "TOTAL en FMG:")
        c.setFont("Helvetica-Bold", 9)
        c.drawRightString(
            MARGIN + usable - 3,
            band_y + band_h / 2 - 5.5 * mm,
            fmt_pdf(total_m * 5),
        )

        pb = ParagraphStyle(
            "pb",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            alignment=1,
        )
        pi = ParagraphStyle(
            "pi",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=10,
            alignment=1,
        )
        pl = Paragraph(f"ARRETE A LA SOMME DE {lettres} ARIARY TTC", pb)
        pm = Paragraph(
            "Nous déclinons la responsabilité des marchandises non livrées au-delà de 5 jours",
            pi,
        )
        _, hl = pl.wrap(usable, 20 * mm)
        _, hm = pm.wrap(usable, 15 * mm)
        yl = band_y - 2 * mm - hl
        ym = yl - 1.5 * mm - hm
        pl.drawOn(c, MARGIN, yl)
        pm.drawOn(c, MARGIN, ym)
        y_below = ym - 1.5 * mm
        for html_extra in paragraphes_footer_supplement:
            if not (html_extra or "").strip():
                continue
            pe = Paragraph(html_extra, pi)
            _, he = pe.wrap(usable, 20 * mm)
            y_below -= he
            pe.drawOn(c, MARGIN, y_below)
            y_below -= 1.5 * mm

        c.setFont("Helvetica-Bold", 10)
        c.drawString(MARGIN, 15 * mm, "Le Client")
        c.drawCentredString(width / 2, 15 * mm, "Le Caissier")
        c.drawString(width - 35 * mm, 15 * mm, "Le Magasinier")

    def draw_table(t_top: float, t_bot: float, rows: List[List[Any]], show_tot: bool, total_m: float = 0):
        from reportlab.lib.styles import ParagraphStyle as _PS
        from reportlab.platypus import Paragraph as _Para

        fh = t_top - t_bot
        cws = [12 * mm, 15 * mm, 50 * mm, 17 * mm, 17 * mm, 17 * mm]
        rhe = 5.5 * mm
        max_r = int(fh / rhe)
        slots = max_r - 1

        ps_desig = _PS("desig", fontName="Helvetica", fontSize=8, leading=9, wordWrap="LTR")

        def make_row(r):
            row = list(r)
            if row[2] and isinstance(row[2], str):
                row[2] = _Para(row[2], ps_desig)
            return row

        body = [make_row(r) for r in rows]
        for _ in range(max(0, slots - len(body))):
            body.append([""] * 6)

        hdr = [["QTE", "UNITE", "DESIGNATION", "PU TTC", "P.REMISE", "MONTANT"]]
        td = hdr + body

        row_heights = [rhe] + [None] * len(body)

        cmds = [
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("LINEBELOW", (0, 0), (-1, 0), 1, rl_colors.black),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (2, 0), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (3, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("GRID", (0, 0), (-1, -1), 0.3, rl_colors.Color(0.75, 0.75, 0.75)),
            ("LINEBELOW", (0, 0), (-1, 0), 1, rl_colors.black),
        ]
        t = RLTable(td, colWidths=cws, rowHeights=row_heights)
        t.setStyle(RLTableStyle(cmds))
        _tw, th = t.wrapOn(c, width - 2 * MARGIN, fh)
        t.drawOn(c, MARGIN, t_top - th)
        c.setLineWidth(1)
        c.rect(MARGIN, t_top - th, width - 2 * MARGIN, th)
        xp = MARGIN
        for w_ in cws[:-1]:
            xp += w_
            c.line(xp, t_top, xp, t_top - th)
        return t_top - th

    # ── Lignes tableau ──────────────────────────────────────────────────────
    total_m = 0.0
    all_rows: List[List[str]] = []
    for raw in details:
        rowd = detail_vers_ligne_facture(raw)
        if not rowd:
            continue
        mt = float(rowd["montant_ttc"])
        total_m += mt
        pu = float(rowd["prixunit"])
        remise = float(rowd["remise"])
        if remise > 0:
            prix_remise_str = fmt_pdf(max(0.0, pu - remise))
        else:
            prix_remise_str = ""
        all_rows.append(
            [
                str(int(rowd["qte"])),
                rowd["unite"],
                rowd["designation"],
                fmt_pdf(pu),
                prix_remise_str,
                fmt_pdf(mt),
            ]
        )

    pages: List[Tuple[str, List[List[str]]]] = []
    if len(all_rows) <= MAX_P1:
        pages.append(("first", all_rows))
    else:
        pages.append(("first", all_rows[:MAX_P1]))
        reste = all_rows[MAX_P1:]
        while reste:
            pages.append(("cont", reste[:MAX_PN]))
            reste = reste[MAX_PN:]

    for idx, (ptype, rows) in enumerate(pages):
        last = idx == len(pages) - 1
        draw_verset()
        draw_header(ptype == "cont")
        t_top = height - 45 * mm
        t_bot = 69 * mm if last else 15 * mm
        tb = draw_table(t_top, t_bot, rows, last, total_m)
        if last:
            draw_footer(total_m, tb)
        if len(pages) > 1:
            c.setFont("Helvetica", 7)
            c.drawCentredString(width / 2, 8 * mm, f"Page {idx + 1} / {len(pages)}")
        if not last:
            c.showPage()

    try:
        c.save()
    except Exception as e:
        print(f"❌ Erreur PDF A5 (modèle vente dépôt) : {e}")
        traceback.print_exc()


def html_entete_droite_facture(
    refvente: str,
    dateregistre: str,
    magasin: str,
    nom_client: str,
    user_name: str,
) -> str:
    """Bloc HTML droit type facture (identique à l'esprit vente par dépôt)."""
    return (
        f"<b>Facture N°: {refvente}{{SUITE}}</b><br/>"
        f"{dateregistre}<br/><b>MAGASIN {magasin}</b><br/><br/>"
        f"<i>Client: {nom_client}</i><br/><font size='7'>Op: {user_name}</font>"
    )


def html_entete_droite_avoir(
    refavoir: str,
    refvente_associe: str,
    date_texte: str,
    magasin: str,
    nom_client: str,
    user_name: str,
) -> str:
    """Bloc HTML droit pour un avoir."""
    return (
        f"<b>AVOIR N°: {refavoir}{{SUITE}}</b><br/>"
        f"<b>Du Ref: {refvente_associe}</b><br/>"
        f"{date_texte}<br/><b>MAGASIN {magasin}</b><br/><br/>"
        f"<i>Client: {nom_client}</i><br/><font size='7'>Op: {user_name}</font>"
    )
