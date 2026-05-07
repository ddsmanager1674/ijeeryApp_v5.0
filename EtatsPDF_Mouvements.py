"""
================================================================================
MODULE: Génération d'États PDF Centralisés pour Mouvements d'Articles (A5 Landscape)
================================================================================
Module permettant la génération d'états PDF normalisés au format A5 Paysage pour:
- Bon d'Entrée (Commandes)
- Bon de Sortie
- Bon de Transfert
- Consommation Interne
- Changement d'Articles

Structure uniforme basée sur un modèle A5 Landscape avec:
- En-tête société + opération
- Tableau articles centré à 85% de largeur
- Description et signatures
================================================================================
"""

from reportlab.lib.pagesizes import landscape, A5
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, 
    PageBreak, Frame, PageTemplate
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import psycopg2
import json
import os
import subprocess
from datetime import datetime
from resource_utils import get_config_path


class EtatPDFMouvements:
    """
    Classe centralisée pour la génération d'états PDF au format A5 Landscape.
    Modèle uniforme pour tous les types de mouvements.
    """
    
    # Format A5 Landscape
    PAGE_WIDTH, PAGE_HEIGHT = landscape(A5)  # ~210mm x 148mm (landscape)
    MARGIN = 5 * mm  # Marge minimale
    
    # Couleurs
    COLOR_HEADER = colors.HexColor("#034787")  # Bleu
    COLOR_BORDER = colors.HexColor("#000000")  # Noir
    COLOR_BG_HEADER = colors.HexColor("#F5F5F5")  # Gris très clair
    COLOR_BG_TABLE_HEADER = colors.HexColor("#E8E8E8")  # Gris clair
    COLOR_BG_FOOTER = colors.HexColor("#F0F0F0")  # Gris
    
    def __init__(self, config_path='config.json'):
        """
        Initialise la classe avec la configuration de la base de données.
        
        Args:
            config_path: Chemin vers le fichier config.json
        """
        self.config_path = get_config_path(config_path)
        self.db_config = self._load_config()
        self.conn = None
        
    def _load_config(self):
        """Charge la configuration de la base de données."""
        try:
            with open(self.config_path) as f:
                config = json.load(f)
                return config['database']
        except Exception as e:
            print(f"Erreur lors du chargement de la configuration: {e}")
            return None
    
    def connect_db(self):
        """Établit la connexion à la base de données."""
        try:
            self.conn = psycopg2.connect(
                host=self.db_config['host'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                database=self.db_config['database'],
                port=self.db_config['port']
            )
        except Exception as e:
            print(f"Erreur de connexion: {e}")
            self.conn = None
    
    def close_db(self):
        """Ferme la connexion à la base de données."""
        if self.conn:
            self.conn.close()
    
    # ========================================================
    # RÉCUPÉRATION DES INFORMATIONS
    # ========================================================
    
    def _get_societe_info(self):
        """Récupère les informations de la société depuis tb_infosociete."""
        if not self.conn:
            return {
                'nomsociete': 'IJEERY',
                'adressesociete': 'Adresse Non Configurée',
                'villesociete': '',
                'contactsociete': 'Contact: Non Configuré',
                'nifsociete': 'NIF: Non Configuré',
                'statsociete': 'STAT: Non Configurée',
                'cifsociete': 'CIF: Non Configuré'
            }
        
        try:
            cur = self.conn.cursor()
            cur.execute("""
                SELECT 
                    nomsociete, villesociete, adressesociete, contactsociete,
                    nifsociete, statsociete, cifsociete
                FROM tb_infosociete LIMIT 1
            """)
            row = cur.fetchone()
            if row:
                return {
                    'nomsociete': row[0] or 'IJEERY',
                    'villesociete': row[1] or '',
                    'adressesociete': row[2] or 'Adresse Non Configurée',
                    'contactsociete': row[3] or 'Contact: Non Configuré',
                    'nifsociete': row[4] or 'NIF: Non Configuré',
                    'statsociete': row[5] or 'STAT: Non Configurée',
                    'cifsociete': row[6] or 'CIF: Non Configuré'
                }
        except Exception as e:
            print(f"Erreur lors de la récupération des infos société: {e}")
        
        return {
            'nomsociete': 'IJEERY',
            'adressesociete': 'Adresse Non Configurée',
            'villesociete': '',
            'contactsociete': 'Contact: Non Configuré',
            'nifsociete': 'NIF: Non Configuré',
            'statsociete': 'STAT: Non Configurée',
            'cifsociete': 'CIF: Non Configuré'
        }
    
    # ========================================================
    # CONSTRUCTION DU PDF SELON MODÈLE A5 LANDSCAPE
    # ========================================================
    
    def _build_pdf_a5(self, output_path, titre_entete, reference, date_operation, 
                      magasin, operateur, table_data, description, 
                      responsable_1="Responsable 1", responsable_2="Responsable 2"):
        """
        Construit et génère un PDF au format A5 Landscape selon le modèle redesigné.
        
        Args:
            output_path: Chemin de sortie du PDF
            titre_entete: Titre de l'opération (ex: "BON DE SORTIE")
            reference: Numéro de référence
            date_operation: Date de l'opération
            magasin: Nom du magasin
            operateur: Nom de l'opérateur
            table_data: Tuple (colonnes, données) pour le tableau
            description: Description de l'opération
            responsable_1: Fonction du 1er responsable
            responsable_2: Fonction du 2e responsable
        """
        doc = SimpleDocTemplate(
            output_path,
            pagesize=landscape(A5),
            rightMargin=self.MARGIN,
            leftMargin=self.MARGIN,
            topMargin=self.MARGIN,
            bottomMargin=self.MARGIN
        )
        
        elements = []
        styles = getSampleStyleSheet()
        page_width_usable = self.PAGE_WIDTH - 2*self.MARGIN
        
        # ========== 1. TITRE PRINCIPAL AVEC TEXTE SACRÉ ==========
        main_title = Paragraph(
            "Ankino amin'ny Jehovah ny asanao dia ho lavorary izay kasainao. Ohabolana 16:3",
            ParagraphStyle(
                'MainTitle',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.black,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold',
                spaceAfter=3
            )
        )
        
        title_table = Table([[main_title]], colWidths=[page_width_usable])
        title_table.setStyle(TableStyle([
            # Outer simple black border occupying full width
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ]))
        elements.append(title_table)
        #elements.append(Spacer(1, 3*mm))
        
        # ========== 2. SECTION EN-TÊTE: 1/3 SOCIÉTÉ + 2/3 OPÉRATION ==========
        societe = self._get_societe_info()
        
        # Adapter les clés de données si nécessaire (comme dans page_venteParMsin.py)
        nomsociete = societe.get('nomsociete', 'N/A')
        adressesociete = societe.get('adressesociete') or 'Adresse Non Configurée'
        villesociete = societe.get('villesociete') or ''
        contactsociete = societe.get('contactsociete') or 'Contact: Non Configuré'
        nifsociete = societe.get('nifsociete') or 'NIF: Non Configuré'
        statsociete = societe.get('statsociete') or 'STAT: Non Configurée'
        
        # Insérer la ville juste en dessous de l'adresse si disponible
        villes_line = f"Ville : {villesociete}<br/>" if villesociete else ""
        
        # BLOC GAUCHE: Société (1/3 de la largeur)
        company_width = page_width_usable * 0.33

        # Hauteur fixe pour les blocs d'en-tête afin qu'ils aient la même hauteur
        header_height = 28 * mm
       
        company_details = Paragraph(
            f"<b>{nomsociete}</b><br/>"
            f"Adresse : {adressesociete}<br/>"
            f"{villes_line}"
            f"Contact : {contactsociete}<br/>"
            f"NIF : {nifsociete}<br/>"
            f"STAT : {statsociete}<br/>",
            ParagraphStyle(
                'CompanyDetails',
                parent=styles['Normal'],
                fontSize=9,
                alignment=TA_LEFT,
                leading=12
            )
        )
        
        company_data = [[company_details]]
        company_table = Table(company_data, colWidths=[company_width - 2*mm], rowHeights=[header_height])
        company_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, self.COLOR_BORDER),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('VALIGN', (0, 0), (0, 0), 'TOP'),
            ('VALIGN', (0, 1), (0, 1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        # BLOC DROIT: 2/3 lié à l'opération
        # Divisé: 2/3 titre gauche + 1/3 infos droite
        operation_width = page_width_usable * 0.67 - 2*mm
        title_width = operation_width * 0.55
        info_width = operation_width * 0.45
        
        # Titre grand et gras (2/3 du bloc droit)
        operation_title = Paragraph(
            titre_entete,
            ParagraphStyle(
                'OpTitle',
                parent=styles['Normal'],
                fontSize=14,
                fontName='Helvetica-Bold',
                alignment=TA_CENTER,
                textColor=self.COLOR_HEADER
            )
        )
        
        # Infos opération (1/3 du bloc droit)
        operation_info = Paragraph(
            f"<b>Référence :</b> {reference}<br/>"
            f"<b>Date et heure:</b> {date_operation} <br/>" # datetime.now().strftime('%H:%M')}<br/>"
            f"<b>Magasin :</b> {magasin}<br/>"
            f"<b>Opérateur :</b> {operateur}",
            ParagraphStyle(
                'OpInfo',
                parent=styles['Normal'],
                fontSize=9,
                alignment=TA_LEFT,
                leading=12
            )
        )
        
        # Layout du bloc droit
        operation_data = [[operation_title, operation_info]]
        operation_table = Table(operation_data, colWidths=[title_width, info_width], rowHeights=[header_height])
        operation_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, self.COLOR_BORDER),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('ALIGN', (1, 0), (1, 0), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        # Conteneur final : 1/3 + 2/3
        header_data = [[company_table, operation_table]]
        header_table = Table(header_data, colWidths=[company_width, operation_width])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            # Keep outer lines for each cell but prefer BOX on inner tables
            ('LINELEFT', (0, 0), (0, 0), 1, self.COLOR_BORDER),
            ('LINERIGHT', (0, 0), (0, 0), 1, self.COLOR_BORDER),
            # Removed external horizontal lines above/below header cells to keep only inner BOX borders
            ('LINELEFT', (1, 0), (1, 0), 1, self.COLOR_BORDER),
            ('LINERIGHT', (1, 0), (1, 0), 1, self.COLOR_BORDER),
            # Small padding around cells to create a minimal gap between the two blocks
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), -2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            # Extra gap between the two columns
            ('RIGHTPADDING', (0, 0), (0, 0), 8),
            ('LEFTPADDING', (1, 0), (1, 0), 8),
        ]))
        
        elements.append(header_table)
        elements.append(Spacer(1, 4*mm))
        
        # ========== 3. TABLEAU ARTICLES ==========
        if table_data:
            columns, data_rows = table_data
            
            # Fonction pour calculer les largeurs de colonnes en fonction du contenu
            def calculate_column_widths(columns, data_rows, total_width):
                """
                Calcule les largeurs de colonnes proportionnelles au contenu.
                Les colonnes avec du texte long prennent plus d'espace.
                """
                num_cols = len(columns)
                col_lengths = [len(str(col)) for col in columns]
                
                # Calculer la longueur maximale pour chaque colonne (header + data)
                for row_data in data_rows:
                    for i, cell in enumerate(row_data):
                        col_lengths[i] = max(col_lengths[i], len(str(cell or '')))
                
                # Calculer le ratio de chaque colonne
                total_length = sum(col_lengths) if sum(col_lengths) > 0 else num_cols
                col_ratios = [length / total_length for length in col_lengths]
                
                # Appliquer les ratios à la largeur disponible (avec marge minimale)
                min_col_width = 15 * mm  # Largeur minimale par colonne
                available_width = total_width - (min_col_width * num_cols)
                
                col_widths = []
                for ratio in col_ratios:
                    width = min_col_width + (available_width * ratio)
                    col_widths.append(width)
                
                return col_widths
            
            # Préparer les données du tableau avec support du wrapping responsive
            table_width = page_width_usable * 0.95  # 95% de la largeur disponible
            col_widths = calculate_column_widths(columns, data_rows, table_width)
            
            # Convertir les cellules en Paragraph pour permettre le wrapping automatique
            cell_style = ParagraphStyle(
                'CellText',
                parent=styles['Normal'],
                fontSize=8,
                alignment=TA_LEFT,
                wordWrap='CJK'  # Permet le wrapping automatique du texte
            )
            
            # Créer les lignes avec Paragraph (en-tête + données)
            table_rows = []
            header_row = [Paragraph(str(col), cell_style) for col in columns]
            table_rows.append(header_row)
            
            # Ajouter les données (convertir en Paragraph aussi)
            for row_data in data_rows:
                cell_row = [Paragraph(str(cell or ''), cell_style) for cell in row_data]
                table_rows.append(cell_row)
            
            articles_table = Table(table_rows, colWidths=col_widths, repeatRows=1)
            
            # Style du tableau: bordures colonnes + contour + responsive wrapping
            # Créer les commandes de bordure pour chaque colonne
            table_style_commands = [
                # En-tête (fond) et style texte - pas de lignes horizontales internes
                ('BACKGROUND', (0, 0), (-1, 0), self.COLOR_BG_TABLE_HEADER),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 5),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),

                # Données - alignement responsive avec wrapping
                ('ALIGN', (0, 1), (1, -1), 'LEFT'),
                ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 1), (-1, -1), 'TOP'),  # Aligner en haut pour le wrapping
                ('TOPPADDING', (0, 1), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
                ('LEFTPADDING', (0, 1), (-1, -1), 3),
                ('RIGHTPADDING', (0, 1), (-1, -1), 3),

                # Bordure extérieure complète (BOX)
                ('BOX', (0, 0), (-1, -1), 1, self.COLOR_BORDER),
            ]
            
            # Ajouter les bordures verticales internes entre chaque colonne en utilisant LINEBEFORE
            # Commence à la colonne 1 (ligne verticale avant la colonne 1), jusqu'à la dernière colonne
            for col_idx in range(1, len(columns)):
                table_style_commands.append(
                    ('LINEBEFORE', (col_idx, 0), (col_idx, -1), 1, self.COLOR_HEADER)
                )
            
            articles_table.setStyle(TableStyle(table_style_commands))
            
            elements.append(articles_table)
            elements.append(Spacer(1, 3*mm))
        
        # ========== 4. DESCRIPTION ==========
        if description:
            desc_line = Paragraph(
                f"<b>&nbsp;&nbsp;&nbsp;<u>Description: </u></b> {description}<br/><br/>",
                ParagraphStyle(
                    'Description',
                    parent=styles['Normal'],
                    fontSize=9,
                    alignment=TA_LEFT,
                    leading=10
                )
            )
            elements.append(desc_line)
        
        # ========== 5. SIGNATURES EN BAS ==========
        # Deux textes à gauche (stacked) et un à droite
        sig_left_1 = Paragraph(responsable_1, ParagraphStyle(
            'SigLabel1',
            parent=styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER
        ))
        
        sig_right = Paragraph("Contrôleur", ParagraphStyle(
            'SigLabelRight',
            parent=styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER
        ))
        
        # Layout: deux colonnes gauche (stacked) + colonne droite
        sig_container = Table(
            [
                [sig_left_1, '', sig_right]
            ],
            colWidths=[
                page_width_usable * 0.33 - 2*mm,
                page_width_usable * 0.33 - 2*mm,
                page_width_usable * 0.33 - 2*mm
            ]
        )
        sig_container.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('ALIGN', (0, 0), (0, 1), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
            # Removed top horizontal lines above signature blocks (unnecessary)
        ]))
        
        elements.append(sig_container)
        
        # Générer le PDF
        try:
            doc.build(elements)
            print(f"✅ PDF généré avec succès: {output_path}")
            
            # Ouvrir automatiquement dans Google Chrome
            self._open_pdf_in_chrome(output_path)
            
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la génération du PDF: {e}")
            return False
    
    def _open_pdf_in_chrome(self, pdf_path):
        """Ouvre le PDF généré dans Google Chrome."""
        try:
            # Convertir le chemin en chemin absolu
            abs_path = os.path.abspath(pdf_path)
            
            # Essayer de trouver Chrome/Chromium
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files\Chromium\Application\chrome.exe",
                "chrome",  # Sur macOS/Linux
                "google-chrome",  # Sur Linux
            ]
            
            chrome_found = False
            for chrome_path in chrome_paths:
                if os.path.exists(chrome_path) or chrome_path in ['chrome', 'google-chrome']:
                    try:
                        subprocess.Popen([chrome_path, f"file:///{abs_path}"])
                        print(f"✅ PDF ouvert dans Chrome: {abs_path}")
                        chrome_found = True
                        break
                    except Exception:
                        continue
            
            if not chrome_found:
                print(f"⚠️ Chrome non trouvé. Ouverture avec le lecteur par défaut...")
                os.startfile(abs_path) if os.name == 'nt' else subprocess.Popen(['open', abs_path])
        except Exception as e:
            print(f"⚠️ Erreur lors de l'ouverture du PDF: {e}")
    
    # ========================================================
    # MÉTHODES POUR CHAQUE TYPE DE MOUVEMENT
    # ========================================================
    
    def generer_bon_entree(self, refcom, output_path=None):
        """Génère un PDF pour un Bon d'Entrée au format A5 Landscape."""
        if not self.conn:
            self.connect_db()
        
        try:
            cur = self.conn.cursor()
            cur.execute("""
                SELECT c.idcom, c.datecom, c.refcom, f.nomfrs
                FROM tb_commande c
                LEFT JOIN tb_fournisseur f ON c.idfrs = f.idfrs
                WHERE c.refcom = %s AND c.deleted = 0 LIMIT 1
            """, (refcom,))
            
            cmd_info = cur.fetchone()
            if not cmd_info:
                print(f"❌ Commande {refcom} non trouvée")
                return False
            
            idcom, datecom, ref, fournisseur = cmd_info
            
            cur.execute("""
                SELECT 
                    COALESCE(u.codearticle, '-'),
                    a.designation,
                    u.designationunite,
                    cd.qtcmd,
                    COALESCE(cd.qtlivre, 0)
                FROM tb_commandedetail cd
                LEFT JOIN tb_article a ON cd.idarticle = a.idarticle
                LEFT JOIN tb_unite u ON cd.idunite = u.idunite
                WHERE cd.idcom = %s
                ORDER BY a.designation
            """, (idcom,))
            
            details = cur.fetchall()
            
            if not output_path:
                output_path = f"Bon_Entree_{refcom}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            colonnes = ("Code", "Désignation", "Unité", "Cmde", "Livré")
            table_data = (colonnes, list(details))
            
            return self._build_pdf_a5(
                output_path, "BON D'ENTRÉE", ref,
                datecom.strftime("%d/%m/%Y") if datecom else "N/A",
                "Magasin TSARAVATSY", fournisseur or "N/A",
                table_data, f"Fournisseur: {fournisseur or 'N/A'}",
                "Réceptionnaire", "Responsable Magasin"
            )
        except Exception as e:
            print(f"❌ Erreur bon d'entrée: {e}")
            return False
    
    def generer_bon_sortie(self, refsortie, output_path=None):
        """Génère un PDF pour un Bon de Sortie au format A5 Landscape."""
        if not self.conn:
            self.connect_db()
        
        try:
            cur = self.conn.cursor()
            cur.execute("""
                SELECT s.id, s.dateregistre, s.refsortie, s.description,
                       CONCAT(usr.prenomuser, ' ', usr.nomuser) as operateur
                FROM tb_sortie s
                LEFT JOIN tb_users usr ON s.iduser = usr.iduser
                WHERE s.refsortie = %s AND s.deleted = 0 LIMIT 1
            """, (refsortie,))
            
            sortie_info = cur.fetchone()
            if not sortie_info:
                print(f"❌ Sortie {refsortie} non trouvée")
                return False
            
            idsortie, date_sortie, ref, description, operateur = sortie_info
            
            cur.execute("""
                SELECT 
                    COALESCE(u.codearticle, '-'),
                    a.designation,
                    u.designationunite,
                    sd.qtsortie
                FROM tb_sortiedetail sd
                LEFT JOIN tb_article a ON sd.idarticle = a.idarticle
                LEFT JOIN tb_unite u ON sd.idunite = u.idunite
                WHERE sd.idsortie = %s
                ORDER BY a.designation
            """, (idsortie,))
            
            details = cur.fetchall()
            
            if not output_path:
                output_path = f"Bon_Sortie_{refsortie}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            colonnes = ("Code", "Désignation", "Unité", "Quantité")
            table_data = (colonnes, list(details))
            
            return self._build_pdf_a5(
                output_path, "BON DE SORTIE", ref,
                date_sortie.strftime("%d/%m/%Y") if date_sortie else "N/A",
                "Magasin TSARAVATSY", operateur or "N/A",
                table_data, description or "Sortie de stock",
                "Magasinier", "Responsable Magasin"
            )
        except Exception as e:
            print(f"❌ Erreur bon de sortie: {e}")
            return False
    
    def generer_bon_transfert(self, reftransfert, output_path=None):
        """Génère un PDF pour un Bon de Transfert au format A5 Landscape."""
        if not self.conn:
            self.connect_db()
        
        try:
            cur = self.conn.cursor()
            cur.execute("""
                SELECT t.idtransfert, t.dateregistre, t.reftransfert, m1.designationmag, m2.designationmag,
                       CONCAT(usr.prenomuser, ' ', usr.nomuser) as operateur
                FROM tb_transfert t
                LEFT JOIN tb_magasin m1 ON t.idmagsortie = m1.idmag
                LEFT JOIN tb_magasin m2 ON t.idmagentree = m2.idmag
                LEFT JOIN tb_users usr ON t.iduser = usr.iduser
                WHERE t.reftransfert = %s AND t.deleted = 0 LIMIT 1
            """, (reftransfert,))
            
            transfert_info = cur.fetchone()
            if not transfert_info:
                print(f"❌ Transfert {reftransfert} non trouvé")
                return False
            
            idtransfert, date_transfert, ref, mag_source, mag_dest, operateur = transfert_info
            
            cur.execute("""
                SELECT 
                    COALESCE(u.codearticle, '-'),
                    a.designation,
                    u.designationunite,
                    td.qttransfert
                FROM tb_transfertdetail td
                LEFT JOIN tb_article a ON td.idarticle = a.idarticle
                LEFT JOIN tb_unite u ON td.idunite = u.idunite
                WHERE td.idtransfert = %s
                ORDER BY a.designation
            """, (idtransfert,))
            
            details = cur.fetchall()
            
            if not output_path:
                output_path = f"Bon_Transfert_{reftransfert}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            colonnes = ("Code", "Désignation", "Unité", "Quantité")
            table_data = (colonnes, list(details))
            magasins = f"{mag_source or 'N/A'} → {mag_dest or 'N/A'}"
            
            return self._build_pdf_a5(
                output_path, "BON DE TRANSFERT", ref,
                date_transfert.strftime("%d/%m/%Y %H:%M") if date_transfert else "N/A",
                magasins, operateur or "N/A",
                table_data, f"Transfert: {magasins}",
                "Magasinier Source", "Magasinier Destination"
            )
        except Exception as e:
            print(f"❌ Erreur bon de transfert: {e}")
            return False
    
    def generer_bon_consommation(self, refconso, output_path=None):
        """Génère un PDF pour une Consommation Interne au format A5 Landscape."""
        if not self.conn:
            self.connect_db()
        
        try:
            cur = self.conn.cursor()
            cur.execute("""
                SELECT c.id, c.dateregistre, c.refconsommation, c.observation,
                       CONCAT(usr.prenomuser, ' ', usr.nomuser) as operateur
                FROM tb_consommationinterne c
                LEFT JOIN tb_users usr ON c.iduser = usr.iduser
                WHERE c.refconsommation = %s LIMIT 1
            """, (refconso,))
            
            conso_info = cur.fetchone()
            if not conso_info:
                print(f"❌ Consommation {refconso} non trouvée")
                return False
            
            idconso, date_conso, ref, observation, operateur = conso_info
            
            cur.execute("""
                SELECT 
                    COALESCE(u.codearticle, '-'),
                    a.designation,
                    u.designationunite,
                    cd.qtconsomme
                FROM tb_consommationinterne_details cd
                LEFT JOIN tb_article a ON cd.idarticle = a.idarticle
                LEFT JOIN tb_unite u ON cd.idunite = u.idunite
                WHERE cd.idconsommation = %s
                ORDER BY a.designation
            """, (idconso,))
            
            details = cur.fetchall()
            
            if not output_path:
                output_path = f"Bon_Consommation_{refconso}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            colonnes = ("Code", "Désignation", "Unité", "Quantité")
            table_data = (colonnes, list(details))
            
            return self._build_pdf_a5(
                output_path, "CONSOMMATION INTERNE", ref,
                date_conso.strftime("%d/%m/%Y") if date_conso else "N/A",
                "Magasin TSARAVATSY", operateur or "N/A",
                table_data, observation or "Consommation interne",
                "Responsable Magasin", "Gestionnaire Stock"
            )
        except Exception as e:
            print(f"❌ Erreur consommation: {e}")
            return False
    
    def generer_bon_changement(self, refchg, output_path=None):
        """Génère un PDF pour un Changement d'Article au format A5 Landscape."""
        if not self.conn:
            self.connect_db()
        
        try:
            cur = self.conn.cursor()
            cur.execute("""
                SELECT c.idchg, c.datechg, c.refchg, c.note,
                       CONCAT(usr.prenomuser, ' ', usr.nomuser) as operateur
                FROM tb_changement c
                LEFT JOIN tb_users usr ON c.iduser = usr.iduser
                WHERE c.refchg = %s LIMIT 1
            """, (refchg,))
            
            chg_info = cur.fetchone()
            if not chg_info:
                print(f"❌ Changement {refchg} non trouvé")
                return False
            
            idchg, date_chg, ref, observation, operateur = chg_info
            
            cur.execute("""
                SELECT 
                    COALESCE(u.codearticle, '-'),
                    a.designation,
                    u.designationunite,
                    ds.quantite_sortie,
                    'SORTIE'
                FROM tb_detailchange_sortie ds
                LEFT JOIN tb_article a ON ds.idarticle = a.idarticle
                LEFT JOIN tb_unite u ON ds.idunite = u.idunite
                WHERE ds.idchg = %s
                UNION ALL
                SELECT 
                    COALESCE(u.codearticle, '-'),
                    a.designation,
                    u.designationunite,
                    de.quantite_entree,
                    'ENTREE'
                FROM tb_detailchange_entree de
                LEFT JOIN tb_article a ON de.idarticle = a.idarticle
                LEFT JOIN tb_unite u ON de.idunite = u.idunite
                WHERE de.idchg = %s
                ORDER BY 5, 2
            """, (idchg, idchg))
            
            details = cur.fetchall()
            
            if not output_path:
                output_path = f"Bon_Changement_{refchg}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            colonnes = ("Code", "Désignation", "Unité", "Quantité", "Type")
            table_data = (colonnes, list(details))
            
            return self._build_pdf_a5(
                output_path, "CHANGEMENT D'ARTICLE", ref,
                date_chg.strftime("%d/%m/%Y") if date_chg else "N/A",
                "Magasin TSARAVATSY", operateur or "N/A",
                table_data, observation or "Changement effectué",
                "Magasinier", "Responsable Magasin"
            )
        except Exception as e:
            print(f"❌ Erreur changement: {e}")
            return False
    
    def generer_etat(self, type_mouvement, reference, output_path=None):
        """Génère un état PDF selon le type de mouvement."""
        type_mouvement = type_mouvement.lower()
        
        if type_mouvement == 'entree':
            return self.generer_bon_entree(reference, output_path)
        elif type_mouvement == 'sortie':
            return self.generer_bon_sortie(reference, output_path)
        elif type_mouvement == 'transfert':
            return self.generer_bon_transfert(reference, output_path)
        elif type_mouvement == 'consommation':
            return self.generer_bon_consommation(reference, output_path)
        elif type_mouvement == 'changement':
            return self.generer_bon_changement(reference, output_path)
        else:
            print(f"❌ Type inconnu: {type_mouvement}")
            return False


if __name__ == "__main__":
    etat = EtatPDFMouvements()
    etat.close_db()
