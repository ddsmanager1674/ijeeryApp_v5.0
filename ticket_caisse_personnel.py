# -*- coding: utf-8 -*-
"""
Tickets de caisse 80 mm — Avance 15e et Avance spéciale personnel.
En-tête société (tb_infosociete), même gabarit que les autres tickets iJeery.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from impression_pdf_utils import build_impression_output_path
from settings_utils import is_setting_enabled, load_settings, open_file_if_enabled

SETTING_AVANCE_15E = "Avance15e_ImpressionTicket80"
SETTING_AVANCE_SPECIAL = "AvanceSpecial_ImpressionTicket80"

TITRE_AVANCE_15E = "AVANCE 15e (QUINZAINE)"
TITRE_AVANCE_SPECIAL = "AVANCE SPÉCIALE PERSONNEL"


def formater_montant_ar(montant: Any) -> str:
    try:
        n = float(montant)
        return (
            f"{n:,.0f}".replace(",", " ").replace(".", ",") + " Ar"
        )
    except (TypeError, ValueError):
        return "0 Ar"


def fetch_infos_societe(cursor) -> Dict[str, str]:
    """Infos entreprise depuis tb_infosociete."""
    default = {
        "nom": "IJEERY",
        "adresse": "",
        "ville": "",
        "contact": "",
    }
    if cursor is None:
        return default
    try:
        cursor.execute(
            """
            SELECT nomsociete, adressesociete, villesociete, contactsociete
            FROM tb_infosociete
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if not row:
            return default
        return {
            "nom": (row[0] or default["nom"]).strip(),
            "adresse": (row[1] or "").strip(),
            "ville": (row[2] or "").strip(),
            "contact": (row[3] or "").strip(),
        }
    except Exception:
        return default


def resolve_operateur_label(cursor, iduser: Optional[int]) -> str:
    if not iduser:
        return "—"
    try:
        cursor.execute(
            """
            SELECT username, nomuser, prenomuser
            FROM tb_users
            WHERE iduser = %s
            LIMIT 1
            """,
            (int(iduser),),
        )
        row = cursor.fetchone()
        if not row:
            return str(iduser)
        username, nom, prenom = row
        if username:
            return str(username).strip()
        label = f"{nom or ''} {prenom or ''}".strip()
        return label or str(iduser)
    except Exception:
        return str(iduser)


def _draw_wrapped(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    max_width: float,
    font: str = "Helvetica",
    size: int = 8,
    line_h: float = 4 * mm,
) -> float:
    """Dessine un paragraphe ; retourne le y final."""
    words = str(text or "").split()
    if not words:
        return y
    line = ""
    for word in words:
        test = f"{line} {word}".strip() if line else word
        if c.stringWidth(test, font, size) <= max_width:
            line = test
        else:
            c.setFont(font, size)
            c.drawString(x, y, line)
            y -= line_h
            line = word
    if line:
        c.setFont(font, size)
        c.drawString(x, y, line)
        y -= line_h
    return y


def generer_ticket_avance_80mm(
    output_path: str,
    *,
    societe: Dict[str, str],
    titre_document: str,
    reference: str,
    date_pmt: datetime,
    personnel_label: str,
    montant: float,
    observation: str = "",
    operateur: str = "—",
    lignes_supplementaires: Optional[List[Tuple[str, str]]] = None,
) -> str:
    """
    Génère un PDF ticket 80 mm (en-tête société + corps standard).
    Retourne le chemin du fichier créé.
    """
    ticket_width = 80 * mm
    ticket_height = 240 * mm
    c = canvas.Canvas(output_path, pagesize=(ticket_width, ticket_height))
    y = ticket_height - 10 * mm
    x_center = ticket_width / 2
    margin = 5 * mm

    nom_soc = (societe.get("nom") or "IJEERY").upper()
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(x_center, y, nom_soc)
    y -= 5 * mm

    c.setFont("Helvetica", 8)
    if societe.get("adresse"):
        c.drawCentredString(x_center, y, societe["adresse"])
        y -= 4 * mm
    if societe.get("ville"):
        c.drawCentredString(x_center, y, societe["ville"])
        y -= 4 * mm
    if societe.get("contact"):
        c.drawCentredString(x_center, y, f"Tél: {societe['contact']}")
        y -= 6 * mm

    c.line(margin, y, ticket_width - margin, y)
    y -= 7 * mm

    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(x_center, y, titre_document)
    y -= 8 * mm
    c.line(margin, y, ticket_width - margin, y)
    y -= 7 * mm

    c.setFont("Helvetica", 9)
    if hasattr(date_pmt, "strftime"):
        date_txt = date_pmt.strftime("%d/%m/%Y %H:%M")
    else:
        date_txt = str(date_pmt)
    c.drawString(margin, y, f"Date: {date_txt}")
    y -= 5 * mm
    c.drawString(margin, y, f"Réf: {reference}")
    y -= 5 * mm
    c.drawString(margin, y, f"Personnel: {personnel_label}")
    y -= 5 * mm
    c.drawString(margin, y, f"Opérateur: {operateur}")
    y -= 7 * mm

    for label, valeur in lignes_supplementaires or []:
        c.drawString(margin, y, f"{label}: {valeur}")
        y -= 5 * mm

    c.line(margin, y, ticket_width - margin, y)
    y -= 7 * mm

    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin, y, "Montant versé :")
    c.drawRightString(ticket_width - margin, y, formater_montant_ar(montant))
    y -= 10 * mm

    if observation and str(observation).strip():
        c.line(margin, y, ticket_width - margin, y)
        y -= 7 * mm
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margin, y, "Observation :")
        y -= 4 * mm
        y = _draw_wrapped(
            c, observation, margin, y,
            ticket_width - 2 * margin,
        )
        y -= 3 * mm

    c.line(margin, y, ticket_width - margin, y)
    y -= 7 * mm
    c.setFont("Helvetica", 8)
    c.drawCentredString(x_center, y, "Merci de votre confiance")
    y -= 4 * mm
    c.drawCentredString(x_center, y, "Document non contractuel")
    y -= 4 * mm
    c.drawCentredString(
        x_center, y,
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    )

    c.save()
    return output_path


def try_imprimer_ticket_avance(
    cursor,
    kind: str,
    *,
    reference: str,
    date_pmt: datetime,
    nom_personnel: str,
    prenom_personnel: Optional[str],
    montant: float,
    observation: str = "",
    iduser: Optional[int] = None,
    nb_remboursement: Optional[int] = None,
) -> bool:
    """
    Génère et ouvre le ticket si le paramètre settings est activé.
    kind: '15e' | 'special'
    """
    settings = load_settings()
    if kind == "special":
        setting_key = SETTING_AVANCE_SPECIAL
        titre = TITRE_AVANCE_SPECIAL
        prefix = "AVS"
    else:
        setting_key = SETTING_AVANCE_15E
        titre = TITRE_AVANCE_15E
        prefix = "AVQ"

    if not is_setting_enabled(setting_key, default=0, settings=settings):
        return False

    societe = fetch_infos_societe(cursor)
    operateur = resolve_operateur_label(cursor, iduser)
    prenom = (prenom_personnel or "").strip()
    nom = (nom_personnel or "").strip()
    personnel_label = f"{nom} {prenom}".strip() or "—"

    lignes_sup: List[Tuple[str, str]] = []
    if kind == "special" and nb_remboursement:
        try:
            nb = int(nb_remboursement)
            lignes_sup.append(("Nb remboursements", str(nb)))
            if nb > 0:
                pm = float(montant) / nb
                lignes_sup.append(("Paiement / mois", formater_montant_ar(pm)))
        except (TypeError, ValueError, ZeroDivisionError):
            pass

    safe_ref = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(reference))
    filename = f"Ticket_{prefix}_{safe_ref}.pdf"
    path, _is_temp = build_impression_output_path(
        filename,
        settings=settings,
        temp_prefix="ijeery_avance_",
    )

    generer_ticket_avance_80mm(
        path,
        societe=societe,
        titre_document=titre,
        reference=reference,
        date_pmt=date_pmt,
        personnel_label=personnel_label,
        montant=float(montant),
        observation=observation or "",
        operateur=operateur,
        lignes_supplementaires=lignes_sup,
    )

    opened = open_file_if_enabled(
        path,
        operation="open",
        settings=settings,
        setting_key=setting_key,
        setting_default=0,
    )
    return opened or True
