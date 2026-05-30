# -*- coding: utf-8 -*-
"""Registre unique des clés settings.json pour l'impression / ouverture PDF."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from impression_pdf_utils import KEY_DOSSIER_REL, KEY_ENREGISTRER
from settings_utils import GLOBAL_PRINT_KEY


@dataclass(frozen=True)
class PdfPrintSetting:
    key: str
    label: str
    default: int
    section: str  # global | export | a5 | ticket80


PDF_PRINT_SETTINGS: Tuple[PdfPrintSetting, ...] = (
    PdfPrintSetting(GLOBAL_PRINT_KEY, "Impression/ouverture automatique globale (Oui/Non)", 1, "global"),
    PdfPrintSetting(KEY_ENREGISTRER, "Enregistrer les PDF / tickets sur le disque", 1, "export"),
    PdfPrintSetting("Vente_ImpressionConfirmation", "Vente - Confirmation", 1, "a5"),
    PdfPrintSetting("Vente_ImpressionA5", "Vente - Facture A5 (PDF)", 1, "a5"),
    PdfPrintSetting("Avoir_ImpressionConfirmation", "Avoir - Confirmation", 1, "a5"),
    PdfPrintSetting("Avoir_ImpressionA5", "Avoir - A5 (PDF)", 1, "a5"),
    PdfPrintSetting("Entree_OpenA5", "Stock - Bon d'entrée A5 (PDF)", 1, "a5"),
    PdfPrintSetting("Sortie_OpenA5", "Stock - Bon de sortie A5 (PDF)", 1, "a5"),
    PdfPrintSetting("Consommation_OpenA5", "Stock - Consommation interne A5 (PDF)", 1, "a5"),
    PdfPrintSetting("Changement_OpenA5", "Stock - Changement articles A5 (PDF)", 1, "a5"),
    PdfPrintSetting("Transfert_OpenA5", "Stock - Bon de transfert A5 (PDF)", 1, "a5"),
    PdfPrintSetting("Mouvements_ImpressionAutoOpen", "Mouvements - Ouverture PDF A5 (générique)", 1, "a5"),
    PdfPrintSetting("Credit_Acceptation_OpenA5", "Crédit - Acceptation A5 (PDF)", 1, "a5"),
    PdfPrintSetting("Credit_Temporaire_OpenA5", "Crédit - État temporaire A5 (PDF)", 0, "a5"),
    PdfPrintSetting("Client_Creance_OpenA5", "Client créance - Ouverture A5 (PDF)", 0, "a5"),
    PdfPrintSetting("Client_PmtCredit_OpenA5", "Client paiement crédit - A5 (PDF)", 0, "a5"),
    PdfPrintSetting("Fournisseur_PmtDette_OpenA5", "Fournisseur paiement dette - A5 (PDF)", 0, "a5"),
    PdfPrintSetting("Fournisseur_Dette_OpenA5", "Fournisseur dette - A5 (PDF)", 0, "a5"),
    PdfPrintSetting("Livraison_BL_OpenA5", "Livraison client - Bon de livraison A5 (PDF)", 1, "a5"),
    PdfPrintSetting("LivraisonFrs_OpenA5", "Livraison fournisseur - BR A5 (PDF)", 1, "a5"),
    PdfPrintSetting("ReceptionDirect_OpenA5", "Réception directe - A5 (PDF)", 1, "a5"),
    PdfPrintSetting("Caisse_Etat_OpenA5", "Caisse - État de caisse A5/PDF", 1, "a5"),
    PdfPrintSetting("Proforma_OpenA5", "Proforma - A5 (PDF)", 1, "a5"),
    PdfPrintSetting("ListeMouvement_PdfOpen", "Liste mouvements - Export PDF", 1, "a5"),
    PdfPrintSetting("FactureListe_VenteDepot_OpenA5", "Facture liste - Modèle vente dépôt A5", 1, "a5"),
    PdfPrintSetting("TransfertCaisse_OpenPdf", "Transfert caisse - PDF", 1, "a5"),
    PdfPrintSetting("TransfertBanque_OpenPdf", "Transfert banque - PDF", 1, "a5"),
    PdfPrintSetting("Encaissement_OpenPdf", "Encaissement - PDF", 1, "a5"),
    PdfPrintSetting("Decaissement_OpenPdf", "Décaissement - PDF", 1, "a5"),
    PdfPrintSetting("Salaire_Etat_OpenA5", "Salaire - États A5 (PDF)", 1, "a5"),
    PdfPrintSetting("PmtFrs_OpenPdf", "Paiement fournisseur - PDF", 1, "a5"),
    PdfPrintSetting("Vente_ImpressionTicket", "Vente - Ticket 80mm", 0, "ticket80"),
    PdfPrintSetting("Avance15e_ImpressionTicket80", "Personnel - Avance 15e - Ticket 80mm", 0, "ticket80"),
    PdfPrintSetting("AvanceSpecial_ImpressionTicket80", "Personnel - Avance spéciale - Ticket 80mm", 0, "ticket80"),
    PdfPrintSetting("Avoir_ImpressionTicket", "Avoir - Ticket 80mm", 0, "ticket80"),
    PdfPrintSetting("ClientAPayer_ImpressionTicket", "Client à payer - Ticket 80mm", 1, "ticket80"),
    PdfPrintSetting("Facture_Paiement_OpenTicket80Pdf", "Facture - Paiement ticket 80mm PDF", 1, "ticket80"),
    PdfPrintSetting("Client_PmtCredit_OpenTicket80", "Client paiement crédit - Ticket 80mm", 0, "ticket80"),
    PdfPrintSetting("Client_PmtCredit_PrintX80", "Client paiement crédit - Impression X80", 0, "ticket80"),
    PdfPrintSetting("Client_Creance_OpenTicketPdf", "Client créance - Ticket 80mm PDF", 0, "ticket80"),
    PdfPrintSetting("Fournisseur_PmtDette_OpenTicket80", "Fournisseur paiement dette - Ticket 80mm", 0, "ticket80"),
    PdfPrintSetting("Fournisseur_Dette_OpenTicketPdf", "Fournisseur dette - Ticket 80mm PDF", 0, "ticket80"),
)


def settings_by_section(section: str) -> List[PdfPrintSetting]:
    return [s for s in PDF_PRINT_SETTINGS if s.section == section]


def merge_defaults_into_settings(settings: dict) -> dict:
    """Ajoute les clés manquantes sans écraser les valeurs existantes."""
    out = dict(settings or {})
    for item in PDF_PRINT_SETTINGS:
        out.setdefault(item.key, item.default)
    out.setdefault(KEY_DOSSIER_REL, ".")
    return out
