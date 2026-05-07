"""
================================================================================
FICHIER TEST TEMPORAIRE: Aperçu du Design PDF Mouvements
================================================================================
Permet de tester et ajuster le design PDF avant implémentation finale.
"""

from EtatsPDF_Mouvements import EtatPDFMouvements
from datetime import datetime, timedelta
import os

# Données de test simulées
class TestData:
    """Classe pour créer des données de test"""
    
    @staticmethod
    def get_test_bon_entree():
        """Données de test pour Bon d'Entrée"""
        columns = ("Code", "Désignation", "Unité", "Cmde", "Livré")
        data = [
            ("ART001", "Stylo Bleu Bic", "Unité", "100", "100"),
            ("ART002", "Cahier A4 80g", "Paquet/10", "50", "50"),
            ("ART003", "Crayon HB", "Boîte/12", "30", "25"),
            ("ART004", "Enveloppe Blanche", "Rame/500", "20", "15"),
            ("ART005", "Correcteur Whiteex", "Unité", "15", "15"),
        ]
        return (columns, data)
    
    @staticmethod
    def get_test_bon_sortie():
        """Données de test pour Bon de Sortie"""
        columns = ("Code", "Désignation", "Unité", "Quantité")
        data = [
            ("ART001", "Stylo Bleu Bic", "Unité", "25"),
            ("ART002", "Cahier A4 80g", "Paquet/10", "12"),
            ("ART003", "Crayon HB", "Boîte/12", "8"),
            ("ART004", "Enveloppe Blanche", "Rame/500", "5"),
        ]
        return (columns, data)
    
    @staticmethod
    def get_test_bon_transfert():
        """Données de test pour Bon de Transfert"""
        columns = ("Code", "Désignation", "Unité", "Quantité")
        data = [
            ("ART001", "Stylo Bleu Bic", "Unité", "50"),
            ("ART002", "Cahier A4 80g", "Paquet/10", "20"),
            ("ART003", "Crayon HB", "Boîte/12", "15"),
        ]
        return (columns, data)
    
    @staticmethod
    def get_test_consommation():
        """Données de test pour Consommation Interne"""
        columns = ("Code", "Désignation", "Unité", "Quantité")
        data = [
            ("ART001", "Stylo Bleu Bic", "Unité", "5"),
            ("ART002", "Cahier A4 80g", "Paquet/10", "2"),
            ("ART003", "Crayon HB", "Boîte/12", "1"),
            ("ART006", "Papier A3 90g", "Rame/500", "3"),
        ]
        return (columns, data)
    
    @staticmethod
    def get_test_changement():
        """Données de test pour Changement d'Article"""
        columns = ("Code", "Désignation", "Unité", "Quantité", "Type")
        data = [
            ("ART001", "Stylo Bleu Bic", "Unité", "30", "SORTIE"),
            ("ART007", "Stylo Rouge Bic", "Unité", "30", "ENTREE"),
            ("ART002", "Cahier A4 80g", "Paquet/10", "15", "SORTIE"),
            ("ART008", "Cahier B5 80g", "Paquet/10", "15", "ENTREE"),
        ]
        return (columns, data)


def generate_test_pdfs():
    """Génère des PDFs de test pour aperçu du design"""
    
    print("\n" + "="*80)
    print("GÉNÉRATION DES PDFs DE TEST - APERÇU DU DESIGN")
    print("="*80 + "\n")
    
    # Créer une instance (sans connexion BD pour le test)
    etat_gen = EtatPDFMouvements()
    
    # Dossier de sortie
    output_dir = "temp_pdf_preview"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"📁 Dossier créé: {output_dir}\n")
    
    # Date de test
    test_date = datetime.now().strftime("%d/%m/%Y")
    
    # 1. BON D'ENTRÉE
    print("1️⃣  Génération BON D'ENTRÉE...")
    try:
        columns, data = TestData.get_test_bon_entree()
        table_data = (columns, data)
        output_path = os.path.join(output_dir, "TEST_BonEntree.pdf")
        
        etat_gen._build_pdf_a5(
            output_path=output_path,
            titre_entete="BON D'ENTRÉE",
            reference="COM-2026-001",
            date_operation=test_date,
            magasin="Magasin Principal",
            operateur="Jean Dupont",
            table_data=table_data,
            description="Fournitures de Bureau - Fournisseur: FRANCE BUREAUTIQUE SARL",
            responsable_1="Réceptionnaire",
            responsable_2="Chef Magasin"
        )
        print("   ✅ BON D'ENTRÉE créé\n")
    except Exception as e:
        print(f"   ❌ Erreur: {e}\n")
    
    # 2. BON DE SORTIE
    print("2️⃣  Génération BON DE SORTIE...")
    try:
        columns, data = TestData.get_test_bon_sortie()
        table_data = (columns, data)
        output_path = os.path.join(output_dir, "TEST_BonSortie.pdf")
        
        etat_gen._build_pdf_a5(
            output_path=output_path,
            titre_entete="BON DE SORTIE",
            reference="SORT-2026-0005",
            date_operation=test_date,
            magasin="Magasin Principal",
            operateur="Marie Martin",
            table_data=table_data,
            description="Distribution fournitures - Bureau Administratif",
            responsable_1="Magasinier",
            responsable_2="Responsable Magasin"
        )
        print("   ✅ BON DE SORTIE créé\n")
    except Exception as e:
        print(f"   ❌ Erreur: {e}\n")
    
    # 3. BON DE TRANSFERT
    print("3️⃣  Génération BON DE TRANSFERT...")
    try:
        columns, data = TestData.get_test_bon_transfert()
        table_data = (columns, data)
        output_path = os.path.join(output_dir, "TEST_BonTransfert.pdf")
        
        etat_gen._build_pdf_a5(
            output_path=output_path,
            titre_entete="BON DE TRANSFERT",
            reference="TRANS-2026-0012",
            date_operation=test_date,
            magasin="Magasin Principal → Magasin Annexe",
            operateur="Pierre Lefevre",
            table_data=table_data,
            description="Transfert vers Magasin Annexe",
            responsable_1="Magasinier Source",
            responsable_2="Magasinier Destination"
        )
        print("   ✅ BON DE TRANSFERT créé\n")
    except Exception as e:
        print(f"   ❌ Erreur: {e}\n")
    
    # 4. CONSOMMATION INTERNE
    print("4️⃣  Génération CONSOMMATION INTERNE...")
    try:
        columns, data = TestData.get_test_consommation()
        table_data = (columns, data)
        output_path = os.path.join(output_dir, "TEST_Consommation.pdf")
        
        etat_gen._build_pdf_a5(
            output_path=output_path,
            titre_entete="CONSOMMATION INTERNE",
            reference="CONSO-2026-0003",
            date_operation=test_date,
            magasin="Magasin Principal",
            operateur="Sophie Bernard",
            table_data=table_data,
            description="Consommation pour usage interne - Entretien des locaux",
            responsable_1="Responsable Magasin",
            responsable_2="Gestionnaire Stock"
        )
        print("   ✅ CONSOMMATION INTERNE créée\n")
    except Exception as e:
        print(f"   ❌ Erreur: {e}\n")
    
    # 5. CHANGEMENT D'ARTICLE
    print("5️⃣  Génération CHANGEMENT D'ARTICLE...")
    try:
        columns, data = TestData.get_test_changement()
        table_data = (columns, data)
        output_path = os.path.join(output_dir, "TEST_Changement.pdf")
        
        etat_gen._build_pdf_a5(
            output_path=output_path,
            titre_entete="CHANGEMENT D'ARTICLE",
            reference="CHG-2026-0008",
            date_operation=test_date,
            magasin="Magasin Principal",
            operateur="Marc Rousseau",
            table_data=table_data,
            description="Changement couleurs de stylos et types de cahiers",
            responsable_1="Magasinier",
            responsable_2="Responsable Magasin"
        )
        print("   ✅ CHANGEMENT D'ARTICLE créé\n")
    except Exception as e:
        print(f"   ❌ Erreur: {e}\n")
    
    print("="*80)
    print(f"✅ GÉNÉRATION TERMINÉE")
    print(f"📁 Tous les PDFs sont dans: {output_dir}/")
    print("="*80 + "\n")
    
    print("💡 POINTS D'AJUSTEMENT POSSIBLES:")
    print("   • Largeur des colonnes du tableau")
    print("   • Taille des polices (headers, données, signatures)")
    print("   • Espacement et marges")
    print("   • Format des couleurs")
    print("   • Disposition des sections (en-tête, corps, signatures)")
    print("   • Hauteur des lignes du tableau\n")


if __name__ == "__main__":
    generate_test_pdfs()
    print("💻 Votre interface est maintenant prête pour ajuster le design!")
    print("   Modifiez les paramètres dans EtatsPDF_Mouvements._build_pdf_a5() selon les besoins.\n")
