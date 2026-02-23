import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import psycopg2
import json
import pandas as pd
from datetime import datetime
from tkcalendar import DateEntry # Importation nécessaire
import os
from resource_utils import get_config_path, get_session_path, safe_file_read


class PageDetailFacture(ctk.CTkToplevel):
    """Fenêtre affichant les articles d'une facture spécifique"""
    def __init__(self, master, idvente, refvente, statut="EN_ATTENTE", parent_page=None):
        super().__init__(master)
        self.title(f"Détails Facture : {refvente}")
        self.geometry("900x600")
        self.attributes('-topmost', True)
        self.idvente = idvente
        self.refvente = refvente
        self.statut = statut
        self.parent_page = parent_page
        self.montant_total = 0
        self.mode_paiement = "N/A"
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        container = ctk.CTkFrame(self)
        container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        cols = ("code", "designation", "qte", "prix", "total")
        self.tree = ttk.Treeview(container, columns=cols, show="headings")
        self.tree.tag_configure("even", background="#FFFFFF", foreground="#000000")
        self.tree.tag_configure("odd", background="#E6EFF8", foreground="#000000")
        
        # --- CONFIGURATION DES COLONNES ---
        self.tree.heading("code", text="Code")
        self.tree.heading("designation", text="Désignation")
        self.tree.heading("qte", text="Qté")
        self.tree.heading("prix", text="Prix Unit.")
        self.tree.heading("total", text="Total")

        # Réduction de 75% de la colonne code (fixée à 45 pixels)
        self.tree.column("code", width=70, minwidth=60, anchor="center") 
        self.tree.column("designation", width=350, anchor="w")
        self.tree.column("qte", width=70, anchor="center")
        self.tree.column("prix", width=100, anchor="e")
        self.tree.column("total", width=120, anchor="e")
        
        self.tree.pack(side="left", fill="both", expand=True)
        
        # Scrollbar pour le confort
        scroll = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        
        # --- FOOTER AVEC MONTANT TOTAL ET MODE PAIEMENT ---
        footer_frame = ctk.CTkFrame(self)
        footer_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        
        # Gauche : Montant total
        left_frame = ctk.CTkFrame(footer_frame)
        left_frame.pack(side="left", fill="x", expand=True)
        
        ctk.CTkLabel(left_frame, text="Montant Total:", font=("Segoe UI", 11)).pack(anchor="w")
        self.lbl_montant = ctk.CTkLabel(left_frame, text="0,00 Ar", font=("Segoe UI", 14, "bold"), text_color="#2ecc71")
        self.lbl_montant.pack(anchor="w")
        
        # Droite : Boutons (conditionnels selon statut)
        right_frame = ctk.CTkFrame(footer_frame)
        right_frame.pack(side="right", fill="both")
        
        # Bouton Réimpression : VISIBLE UNIQUEMENT SI VALIDÉE
        if self.statut == "VALIDEE":
            self.btn_reimprimer = ctk.CTkButton(
                right_frame, 
                text="🖨️  Réimprimer (Duplicata)", 
                fg_color="#3498db",
                hover_color="#2980b9",
                command=self.reimprimer_duplicata,
                width=200
            )
            self.btn_reimprimer.pack(pady=5)
        
        # Bouton Annuler : VISIBLE UNIQUEMENT SI EN ATTENTE
        if self.statut == "EN_ATTENTE":
            self.btn_annuler = ctk.CTkButton(
                right_frame, 
                text="❌ Annuler Facture", 
                fg_color="#e74c3c",
                hover_color="#c0392b",
                command=self.annuler_facture,
                width=200
            )
            self.btn_annuler.pack(pady=5)
        
        # Si ANNULÉ : message informatif
        if self.statut == "ANNULE":
            ctk.CTkLabel(right_frame, text="⚠️ Facture Annulée", text_color="#e74c3c", font=("Segoe UI", 11, "bold")).pack(pady=5)
        
        self.charger_details(idvente)

    def formater_montant(self, valeur):
        """Transforme un nombre en format 1.000,00 Ar"""
        try:
            n = f"{float(valeur):,.2f}"
            return n.replace(",", "X").replace(".", ",").replace("X", ".")
        except:
            return "0,00"

    def charger_details(self, idvente):
        try:
            with open(get_config_path('config.json')) as f:
                config = json.load(f)
            conn = psycopg2.connect(**config['database'])
            cursor = conn.cursor()
            
            # Récupérer les infos de la facture (montant total, mode paiement)
            sql_vente = """
                SELECT v.totmtvente
                FROM tb_vente v
                WHERE v.id = %s
            """
            cursor.execute(sql_vente, (idvente,))
            result = cursor.fetchone()
            if result:
                self.montant_total = float(result[0]) if result[0] else 0
                self.lbl_montant.configure(text=f"{self.formater_montant(self.montant_total)} Ar")
            
            # Requête SQL pour les détails
            sql = """
                SELECT 
                    u.codearticle, 
                    a.designation, 
                    vd.qtvente, 
                    vd.prixunit, 
                    (vd.qtvente * vd.prixunit) as total
                FROM tb_ventedetail vd
                INNER JOIN tb_unite u ON vd.idunite = u.idunite
                INNER JOIN tb_article a ON vd.idarticle = a.idarticle
                WHERE vd.idvente = %s
            """
            cursor.execute(sql, (idvente,))
            
            for idx, r in enumerate(cursor.fetchall()):
                # Formatage avec séparateur de milliers pour les prix
                zebra_tag = "even" if idx % 2 == 0 else "odd"
                self.tree.insert("", "end", values=(
                    r[0], 
                    r[1], 
                    r[2], 
                    f"{float(r[3]):,.0f}", 
                    f"{float(r[4]):,.0f}"
                ), tags=(zebra_tag,))
            
            conn.close()
        except Exception as e:
            messagebox.showerror("Erreur SQL", f"Erreur lors du chargement des détails : {e}")

    def reimprimer_duplicata(self):
        """Génère un duplicata de la facture"""
        try:
            # Importer les fonctions de page_vente pour générer le PDF
            from pages.page_vente import PageVente
            
            with open(get_config_path('config.json')) as f:
                config = json.load(f)
            conn = psycopg2.connect(**config['database'])
            cursor = conn.cursor()
            
            # Récupérer toutes les infos de la facture
            sql = """
                SELECT 
                    v.refvente, v.dateregistre, v.description, 
                    u.nomuser, u.prenomuser, 
                    c.nomcli, c.adressecli, c.contactcli,
                    v.totmtvente
                FROM tb_vente v 
                INNER JOIN tb_users u ON v.iduser = u.iduser 
                LEFT JOIN tb_client c ON v.idclient = c.idclient 
                WHERE v.id = %s
            """
            cursor.execute(sql, (self.idvente,))
            result = cursor.fetchone()
            
            if not result:
                messagebox.showerror("Erreur", "Impossible de récupérer les données de la facture")
                return
            
            (refvente, dateregistre, description, nomuser, prenomuser, nomcli, adressecli, contactcli, totmtvente) = result
            
            # Récupérer les détails
            sql_details = """
                SELECT 
                    u.codearticle, a.designation, u.designationunite, 
                    vd.qtvente, vd.prixunit, m.designationmag
                FROM tb_ventedetail vd 
                INNER JOIN tb_article a ON vd.idarticle = a.idarticle 
                INNER JOIN tb_unite u ON vd.idunite = u.idunite
                INNER JOIN tb_magasin m ON vd.idmag = m.idmag
                WHERE vd.idvente = %s
                ORDER BY a.designation
            """
            cursor.execute(sql_details, (self.idvente,))
            details_rows = cursor.fetchall()
            
            # Récupérer infos société
            sql_societe = """
                SELECT nomsociete, adressesociete, contactsociete, nifsociete, statsociete
                FROM tb_infosociete LIMIT 1
            """
            cursor.execute(sql_societe)
            societe_result = cursor.fetchone()
            
            conn.close()
            
            # Préparer les données
            societe_info = {
                'nomsociete': societe_result[0] if societe_result else 'N/A',
                'adressesociete': societe_result[1] if societe_result else 'N/A',
                'contactsociete': societe_result[2] if societe_result else 'N/A',
                'nifsociete': societe_result[3] if societe_result else 'N/A',
                'statsociete': societe_result[4] if societe_result else 'N/A',
            }
            
            data = {
                'societe': societe_info,
                'vente': {
                    'refvente': refvente,
                    'dateregistre': dateregistre.strftime("%d/%m/%Y %H:%M"),
                    'description': description,
                },
                'utilisateur': {
                    'nomuser': nomuser,
                    'prenomuser': prenomuser,
                },
                'client': {
                    'nomcli': nomcli or "Client Divers",
                    'adressecli': adressecli or "N/A",
                    'contactcli': contactcli or "N/A",
                },
                'details': [
                    {
                        'code_article': r[0],
                        'designation': r[1],
                        'unite': r[2],
                        'qte': r[3],
                        'prixunit': r[4],
                        'magasin': r[5],
                        'montant': r[3] * r[4]
                    }
                    for r in details_rows
                ]
            }
            
            # Créer une instance de PageVente pour accéder à la méthode generate_pdf_a5
            page_vente = PageVente.__new__(PageVente)
            page_vente.infos_societe = societe_info
            
            # Générer le PDF avec "DUPLICATA" dans le titre
            filename = os.path.expanduser(f"~\\Desktop\\DUPLICATA_Facture_{refvente.replace('/', '-')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
            
            # Appeler generate_pdf_a5_duplicata (version modifiée)
            self.generate_pdf_a5_duplicata(data, filename, page_vente)
            
            messagebox.showinfo("Succès", f"Duplicata généré avec succès !\n{filename}")
            
            # Ouvrir le fichier
            if os.path.exists(filename):
                os.startfile(filename)
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la génération du duplicata : {str(e)}")
            import traceback
            traceback.print_exc()

    def annuler_facture(self):
        """Annule la facture (change le statut à 'ANNULE')"""
        if messagebox.askyesno("Confirmation", f"Voulez-vous annuler la facture {self.refvente} ?"):
            try:
                with open(get_config_path('config.json')) as f:
                    config = json.load(f)
                conn = psycopg2.connect(**config['database'])
                cursor = conn.cursor()
                
                # Mettre à jour le statut à 'ANNULE'
                sql = "UPDATE tb_vente SET statut = %s WHERE refvente = %s"
                cursor.execute(sql, ("ANNULE", self.refvente))
                conn.commit()
                
                messagebox.showinfo("Succès", f"La facture {self.refvente} a été annulée.")
                
                # Mettre à jour le statut local et masquer le bouton
                self.statut = "ANNULE"
                if hasattr(self, 'btn_annuler'):
                    self.btn_annuler.pack_forget()
                
                # Recharger les données dans la page parent
                if self.parent_page:
                    self.parent_page.charger_donnees()
                
                # Fermer la fenêtre
                self.destroy()
                
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de l'annulation : {str(e)}")
                import traceback
                traceback.print_exc()
            finally:
                if 'conn' in locals():
                    conn.close()

    def generate_pdf_a5_duplicata(self, data, filename, page_vente):
        """Génère un PDF duplicata avec le label 'DUPLICATA'"""
        from reportlab.lib.pagesizes import A5
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.platypus import Table, TableStyle, Paragraph
        from pages.page_vente import nombre_en_lettres_fr
        
        c = canvas.Canvas(filename, pagesize=A5)
        width, height = A5

        # ✅ 1. CADRE DU VERSET (Haut de page avec bordure)
        verset = "Ankino amin'ny Jehovah ny asanao dia ho lavorary izay kasainao. Ohabolana 16:3"
        c.setLineWidth(1)
        c.rect(10*mm, height - 15*mm, width - 20*mm, 8*mm)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(width/2, height - 12.5*mm, verset)

        # ✅ 2. EN-TÊTE DEUX COLONNES
        styles = getSampleStyleSheet()
        style_p = ParagraphStyle('style_p', fontSize=9, leading=11, parent=styles['Normal'])

        societe = data['societe']
        utilisateur = data['utilisateur']
        client = data['client']
        vente = data['vente']

        nomsociete = societe.get('nomsociete', 'N/A')
        adressesociete = societe.get('adressesociete') or societe.get('adresse', 'N/A')
        contactsociete = societe.get('contactsociete') or societe.get('tel', 'N/A')
        nifsociete = societe.get('nifsociete') or societe.get('nif', 'N/A')
        statsociete = societe.get('statsociete') or societe.get('stat', 'N/A')

        gauche_text = f"<b>{nomsociete}</b><br/>{adressesociete}<br/>TEL: {contactsociete}<br/>NIF: {nifsociete} | STAT: {statsociete}"

        if isinstance(utilisateur, dict):
            user_name = f"{utilisateur.get('prenomuser', '')} {utilisateur.get('nomuser', '')}"
        else:
            user_name = str(utilisateur)

        droite_text = f"<b>Facture N°: {vente['refvente']}</b><br/>{vente['dateregistre']}<br/><b>CLIENT: {client['nomcli']}</b><br/><font size='8'>Op: {user_name}</font>"

        gauche = Paragraph(gauche_text, style_p)
        droite = Paragraph(droite_text, style_p)

        header_table = Table([[gauche, droite]], colWidths=[64*mm, 64*mm])
        header_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))

        header_table.wrapOn(c, width, height)
        header_table.drawOn(c, 10*mm, height - 48*mm)

        # ✅ 3. MARQUEUR DUPLICATA (EN ROUGE - À LA PLACE DE "PROFORMA")
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(colors.HexColor("#D32F2F"))
        c.drawCentredString(width/2, height - 51*mm, "DUPLICATA")
        c.setFillColor(colors.HexColor("#000000"))

        # ✅ 4. TABLEAU DES ARTICLES
        table_top = height - 55*mm
        table_bottom = 65*mm
        frame_height = table_top - table_bottom

        row_height = 5.5*mm
        max_rows = int(frame_height / row_height)

        # Préparer les données du tableau
        table_data = [['QTE', 'UNITE', 'DESIGNATION', 'PU TTC', 'MONTANT']]

        total_montant = 0
        num_articles = 0
        for detail in data['details']:
            montant = detail.get('montant_ttc', detail.get('montant', 0))
            total_montant += montant
            num_articles += 1
            table_data.append([
                str(int(detail.get('qte', 0))),
                str(detail.get('unite', '')),
                str(detail.get('designation', '')),
                page_vente.formater_nombre(detail.get('prixunit', 0)) if hasattr(page_vente, 'formater_nombre') else str(detail.get('prixunit', 0)),
                page_vente.formater_nombre(montant) if hasattr(page_vente, 'formater_nombre') else str(montant)
            ])

        # Ajouter des lignes vides
        empty_rows_needed = max_rows - 1 - num_articles - 2
        for i in range(max(0, empty_rows_needed)):
            table_data.append(['', '', '', '', ''])

        # Totaux
        total_formatted = page_vente.formater_nombre(total_montant) if hasattr(page_vente, 'formater_nombre') else str(total_montant)
        table_data.append(['', '', 'TOTAL Ar:', total_formatted, ''])

        col_widths = [12*mm, 15*mm, 62*mm, 19.5*mm, 19.5*mm]

        # Dessiner le cadre et lignes
        c.setLineWidth(1)
        c.rect(10*mm, table_bottom, width - 20*mm, frame_height)

        x_pos = 10*mm
        for w in col_widths[:-1]:
            x_pos += w
            c.line(x_pos, table_top, x_pos, table_bottom)

        # Créer le tableau avec hauteurs proportionnelles
        actual_row_height = frame_height / len(table_data)
        row_heights = [actual_row_height] * len(table_data)

        articles_table = Table(table_data, colWidths=col_widths, rowHeights=row_heights)
        articles_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -2), 8),
            ('FONTSIZE', (0, -1), (-1, -1), 9),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
            ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 0), (2, 0), 'LEFT'),
            ('ALIGN', (2, -1), (2, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 1),
            ('RIGHTPADDING', (3, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))

        articles_table.wrapOn(c, width, height)
        actual_total_height = len(table_data) * actual_row_height
        articles_table.drawOn(c, 10*mm, table_top - actual_total_height)

        # ✅ 5. TEXTE EN LETTRES
        montant_lettres = nombre_en_lettres_fr(int(total_montant)).upper()
        text_y = table_bottom - 18*mm
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(width/2, text_y, f"ARRETE A LA SOMME DE {montant_lettres}")

        # ✅ 6. MENTION LÉGALE + "DUPLICATA"
        c.setFont("Helvetica-Oblique", 8)
        c.drawCentredString(width/2, text_y - 5*mm, "Nous déclinons la responsabilité des marchandises non livrées au-delà de 5 jours")
        c.drawCentredString(width/2, text_y - 8*mm, "CECI EST UN DUPLICATA DE LA FACTURE")

        # ✅ 7. SIGNATURES
        sig_y = 15*mm
        c.setFont("Helvetica-Bold", 10)
        c.drawString(15*mm, sig_y, "Le Client")
        c.drawCentredString(width/2, sig_y, "Le Caissier")
        c.drawString(width - 35*mm, sig_y, "Le Magasinier")

        # ✅ SAUVEGARDER
        try:
            c.save()
            print(f"✅ PDF Duplicata généré avec succès : {filename}")
        except Exception as e:
            print(f"❌ Erreur PDF Duplicata : {e}")
            import traceback
            traceback.print_exc()



class PageListeFacture(ctk.CTkFrame):
    def __init__(self, parent, session_data=None):
        super().__init__(parent)
        self.session_data = session_data
        self.id_user_connecte = self.get_connected_user_id(parent, session_data)
        self.magasin_map = {}
        self.user_default_magasin_nom = None
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.setup_ui()
        self.charger_donnees()

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
        except Exception as e:
            return None

    def setup_ui(self):
        # --- Barre de recherche ---
        search_frame = ctk.CTkFrame(self)
        search_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        # 1. Recherche textuelle existante
        self.entry_search = ctk.CTkEntry(search_frame, width=250, placeholder_text="Facture, Client...")
        self.entry_search.pack(side="left", padx=5, pady=10)
        self.entry_search.bind("<KeyRelease>", lambda e: self.charger_donnees())

        # 2. Sélecteur Date Début
        ctk.CTkLabel(search_frame, text="Du:").pack(side="left", padx=2)
        self.date_debut = DateEntry(search_frame, width=12, background='darkblue', 
                                   foreground='white', borderwidth=2, date_pattern='dd/mm/yyyy')
        self.date_debut.pack(side="left", padx=5)

        # 3. Sélecteur Date Fin
        ctk.CTkLabel(search_frame, text="Au:").pack(side="left", padx=2)
        self.date_fin = DateEntry(search_frame, width=12, background='darkblue', 
                                 foreground='white', borderwidth=2, date_pattern='dd/mm/yyyy')
        self.date_fin.pack(side="left", padx=5)

        # 4. Filtre Statut (SELECT)
        ctk.CTkLabel(search_frame, text="Statut:").pack(side="left", padx=2)
        self.combo_statut = ctk.CTkComboBox(
            search_frame,
            values=["Tout", "VALIDEE", "EN_ATTENTE", "ANNULE"],
            state="readonly",
            width=120
        )
        self.combo_statut.set("VALIDEE")  # Par défaut
        self.combo_statut.pack(side="left", padx=5)
        self.combo_statut.bind("<<ComboboxSelected>>", lambda e: self.charger_donnees())

        # 5. Filtre Magasin
        ctk.CTkLabel(search_frame, text="Magasin:").pack(side="left", padx=2)
        self.combo_magasin = ctk.CTkComboBox(
            search_frame,
            values=["Tout"],
            state="readonly",
            width=170
        )
        self.combo_magasin.set("Tout")
        self.combo_magasin.pack(side="left", padx=5)
        self.combo_magasin.bind("<<ComboboxSelected>>", lambda e: self.charger_donnees())
        self.charger_magasins_filtre()

        # Boutons
        ctk.CTkButton(search_frame, text="🔍 Filtrer", width=80, 
                      command=self.charger_donnees).pack(side="left", padx=5)
        
        self.btn_export = ctk.CTkButton(search_frame, text="📊 Excel", width=80,
                                        fg_color="#1e7e34", hover_color="#155724", 
                                        command=self.exporter_excel)
        self.btn_export.pack(side="right", padx=10)

        # --- Tableau ---
        table_frame = ctk.CTkFrame(self)
        table_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        columns = ("date", "n_facture", "magasin", "client", "montant", "statut", "user")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.tree.tag_configure("even", background="#FFFFFF", foreground="#000000")
        self.tree.tag_configure("odd", background="#E6EFF8", foreground="#000000")
        
        # Configurer les colonnes avec largeurs appropriées
        col_widths = {"date": 150, "n_facture": 110, "magasin": 140, "client": 150, "montant": 100, "statut": 100, "user": 100}
        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            width = col_widths.get(col, 80)
            anchor = "center" if col in ["date", "montant", "statut", "user"] else "w"
            self.tree.column(col, width=width, anchor=anchor)

        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<Double-1>", self.on_double_click)

        # --- Footer ---
        footer_frame = ctk.CTkFrame(self)
        footer_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        self.lbl_count = ctk.CTkLabel(footer_frame, text="Factures: 0")
        self.lbl_count.pack(side="left", padx=20)
        self.lbl_total_mt = ctk.CTkLabel(footer_frame, text="Total: 0 Ar", font=("Arial", 16, "bold"), text_color="#2ecc71")
        self.lbl_total_mt.pack(side="right", padx=20)

    def formater_montant(self, valeur):
        """Transforme un nombre en format 1.000,00"""
        try:
            # Formatage initial : 1,000.00
            n = f"{float(valeur):,.2f}"
            # Remplacement pour le format FR : 1.000,00
            return n.replace(",", "X").replace(".", ",").replace("X", ".")
        except:
            return "0,00"

    def charger_magasins_filtre(self):
        conn = self.connect_db()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT idmag, designationmag FROM tb_magasin WHERE deleted = 0 ORDER BY designationmag"
            )
            magasins = cursor.fetchall()
            self.magasin_map = {nom: idmag for idmag, nom in magasins}

            valeurs = ["Tout"] + [nom for _, nom in magasins]
            self.combo_magasin.configure(values=valeurs)

            default_nom = None
            if self.id_user_connecte:
                cursor.execute(
                    """
                    SELECT u.idmag
                    FROM tb_users u
                    WHERE u.iduser = %s AND u.deleted = 0
                    """,
                    (self.id_user_connecte,)
                )
                row = cursor.fetchone()
                if row and row[0]:
                    idmag_user = row[0]
                    default_nom = next((nom for idmag, nom in magasins if idmag == idmag_user), None)

            self.user_default_magasin_nom = default_nom
            self.combo_magasin.set(default_nom if default_nom in self.magasin_map else "Tout")
        finally:
            conn.close()

    def charger_donnees(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        
        val = self.entry_search.get().strip()
        val_num = None
        if val:
            try:
                val_num = float(val.replace(" ", "").replace(".", "").replace(",", "."))
            except Exception:
                val_num = None
        d1 = self.date_debut.get_date()
        d2 = self.date_fin.get_date()
        statut_filtre = self.combo_statut.get()
        magasin_filtre_nom = self.combo_magasin.get() if hasattr(self, "combo_magasin") else "Tout"
        magasin_filtre_id = self.magasin_map.get(magasin_filtre_nom)
        
        conn = self.connect_db()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            # SQL incluant le filtre de date et statut
            sql = """
                SELECT v.dateregistre, v.refvente, COALESCE(m.designationmag, ''), COALESCE(c.nomcli, 'Client Divers'), v.totmtvente, v.statut, u.username, v.id
                FROM tb_vente v
                LEFT JOIN tb_client c ON v.idclient = c.idclient
                LEFT JOIN tb_users u ON v.iduser = u.iduser
                LEFT JOIN tb_magasin m ON v.idmag = m.idmag
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
                f"%{val}%",
                f"%{val}%",
                f"%{val}%",
                f"%{val.replace(',', '.')}%",
                val_num,
                val_num,
                d1,
                d2
            ]
            
            # Ajouter filtre statut si différent de "Tout"
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
                mt_format = self.formater_montant(r[4]) # Utilisation de la fonction
                zebra_tag = "even" if idx % 2 == 0 else "odd"
                self.tree.insert("", "end", iid=str(r[7]), values=(
                    r[0].strftime("%d/%m/%Y %H:%M:%S"), 
                    r[1], 
                    r[2], 
                    r[3], 
                    mt_format, 
                    r[5],  # Statut
                    r[6]   # User
                ), tags=(zebra_tag,))
                total += float(r[4])
        
            self.lbl_count.configure(text=f"Total factures : {len(rows)}")
            self.lbl_total_mt.configure(text=f"Montant Total en Ar: {self.formater_montant(total)}")
        finally:
            conn.close()

    def on_double_click(self, event):
        """Action lors du double clic"""
        selected_item = self.tree.focus()
        if not selected_item: return
        
        # Récupérer les infos de la ligne
        values = self.tree.item(selected_item)['values']
        ref_facture = values[1]
        statut = values[5]  # Statut de la facture
        
        # Ouvrir la fenêtre de détails
        PageDetailFacture(self, selected_item, ref_facture, statut, parent_page=self)

    def exporter_excel(self):
        lignes = []
        for item in self.tree.get_children():
            lignes.append(self.tree.item(item)['values'])
        
        if not lignes:
            messagebox.showwarning("Vide", "Rien à exporter")
            return

        df = pd.DataFrame(lignes, columns=["Date", "N° Facture", "Magasin", "Client", "Montant", "Statut", "Vendeur"])
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=f"Rapport_Ventes_{datetime.now().strftime('%Y%m%d')}"
        )
        
        if file_path:
            df.to_excel(file_path, index=False)
            messagebox.showinfo("Export réussi", f"Le fichier a été enregistré sous :\n{file_path}")



