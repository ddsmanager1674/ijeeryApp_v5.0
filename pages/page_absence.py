import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
from datetime import datetime
import psycopg2
import subprocess
import sys
import os
import json
from resource_utils import get_config_path, safe_file_read
from log_utils import AppLogger


# Importations spécifiques pour le PDF
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# Thème UI iJeery (référence: page_suiviPresence.py)
from app_theme import Colors, Fonts, Theme, styled, Layout

# Assurer que le répertoire parent est dans le chemin Python pour les imports absolus
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from pages.page_absenceMiseAjour import PageAbsenceMJ

class PageAbsence(ctk.CTkFrame):
    """Classe principale qui hérite de CTkFrame pour l'intégration dans app_main"""
    
    def __init__(self, master, db_conn=None, session_data=None):
        # [UI] Harmonisation du fond et des composants avec app_theme (cards, header, boutons, spacing)
        # [LOGIQUE] Aucune modification des requêtes SQL métier ; uniquement mise en forme et style table
        super().__init__(master, fg_color=Colors.BG_PAGE)
        
        # Initialisation de la connexion directement via la nouvelle méthode
        self.conn = self.connect_db()
        
        if self.conn is None:
            self.show_error_message()
            return
            
        self.cursor = self.conn.cursor()
        self.session_data = session_data or getattr(master, "session_data", None) or {}
        self._logger = AppLogger(conn=self.conn, session_data=self.session_data)

        # Charger les informations de la société
        self.info_societe = self.get_info_societe()

        # Initialisation des widgets
        self.create_widgets()

    def _setup_treeview_style(self):
        # [UI] Style Treeview cohérent (en-têtes Midnight + lignes alternées du thème)
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure(
            "P.Treeview",
            background=Colors.BG_CARD,
            foreground=Colors.TEXT_PRIMARY,
            fieldbackground=Colors.BG_CARD,
            rowheight=26,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        s.configure(
            "P.Treeview.Heading",
            background=Colors.MIDNIGHT,
            foreground=Colors.TEXT_ON_DARK,
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padding=(6, 5),
        )
        s.map("P.Treeview", background=[("selected", Colors.PRIMARY_LIGHT)])
        s.map("P.Treeview.Heading", background=[("active", Colors.MIDNIGHT_LIGHT)])

    def connect_db(self):
        """Établit la connexion à la base de données à partir du fichier config.json"""
        try:
            # Recherche du fichier config.json dans le répertoire parent ou courant
            config_path = get_config_path('config.json')
            if not os.path.exists(config_path):
                config_path = 'config.json'
                
            if not os.path.exists(config_path):
                messagebox.showerror("Erreur", "Fichier config.json manquant.")
                return None
                 
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                db_config = config['database']

            conn = psycopg2.connect(
                host=db_config['host'],
                user=db_config['user'],
                password=db_config['password'],
                database=db_config['database'],
                port=db_config['port']  
            )
            return conn
        except Exception as err:
            messagebox.showerror("Erreur de connexion", f"Détails : {err}")
            return None

    def _configure_table_alternating_colors(self, tree):
        # [UI] Palette alignée au thème iJeery (évite couleurs hors thème)
        tree.tag_configure("row_even", background=Colors.BG_CARD)
        tree.tag_configure("row_odd", background=Colors.BG_ROW_ALT)

    def _refresh_table_alternating_colors(self, tree):
        for idx, item in enumerate(tree.get_children()):
            tree.item(item, tags=("row_even" if idx % 2 == 0 else "row_odd",))

    def get_info_societe(self):
        """Récupère les informations de la société depuis la base de données."""
        try:
            self.cursor.execute("""
                SELECT nomsociete, adressesociete, villesociete, contactsociete
                FROM tb_infosociete
                LIMIT 1
            """)
            result = self.cursor.fetchone()
            if result:
                return {
                    'nom': result[0] or '',
                    'adresse': result[1] or '',
                    'ville': result[2] or '',
                    'contact': result[3] or ''
                }
            else:
                return {
                    'nom': 'Société',
                    'adresse': '',
                    'ville': '',
                    'contact': ''
                }
        except Exception as e:
            print(f"Erreur lors de la récupération des infos société: {e}")
            return {
                'nom': 'Société',
                'adresse': '',
                'ville': '',
                'contact': ''
            }

    def show_error_message(self):
        """Affiche un message d'erreur si la connexion échoue"""
        error_label = ctk.CTkLabel(
            self, 
            text="Erreur de connexion à la base de données\nVérifiez votre fichier config.json",
            font=("Arial", 16, "bold"),
            text_color="red"
        )
        error_label.pack(expand=True, pady=50)

    def create_widgets(self):
        # [UI] Header + cards (même logique visuelle que Suivi de présence)
        self._setup_treeview_style()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        header = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT, corner_radius=0, height=46)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)

        left = styled.frame(header)
        left.grid(row=0, column=0, padx=14, sticky="w")
        ctk.CTkLabel(left, text="❌", font=Fonts.heading(16), text_color=Colors.TEXT_ON_DARK).pack(side="left", padx=(0, 8))
        inner = styled.frame(left)
        inner.pack(side="left")
        ctk.CTkLabel(inner, text="Absence", font=Fonts.bold(13), text_color=Colors.TEXT_ON_DARK).pack(anchor="w")
        ctk.CTkLabel(inner, text="Saisie et suivi des absences", font=Fonts.small(9), text_color=Colors.TEXT_ON_DARK_DIM).pack(anchor="w")

        # Card saisie
        form = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        form.grid(row=1, column=0, sticky="ew", padx=10, pady=(10, 6))
        form.grid_columnconfigure(5, weight=1)

        ctk.CTkLabel(form, text="Date :", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(row=0, column=0, padx=(12, 6), pady=10, sticky="w")
        # DateEntry est un widget Tk; on garde la logique, en ajustant les couleurs sur la palette existante.
        self.date_entry = DateEntry(
            form, width=14,
            background=Colors.PRIMARY_HOVER,
            foreground=Colors.TEXT_ON_DARK,
            borderwidth=2,
            date_pattern="yyyy-mm-dd",
        )
        self.date_entry.grid(row=0, column=1, padx=(0, 12), pady=10, sticky="w")

        ctk.CTkLabel(form, text="Observation :", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(row=0, column=2, padx=(0, 6), pady=10, sticky="w")
        self.observation_entry = ctk.CTkEntry(form, height=32, fg_color=Colors.BG_INPUT, border_color=Colors.BORDER, corner_radius=8, font=Fonts.body(11))
        self.observation_entry.grid(row=0, column=3, padx=(0, 12), pady=10, sticky="ew")

        ctk.CTkLabel(form, text="Nb heures :", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(row=0, column=4, padx=(0, 6), pady=10, sticky="w")
        self.nbre_heure_entry = ctk.CTkEntry(form, width=90, height=32, fg_color=Colors.BG_INPUT, border_color=Colors.BORDER, corner_radius=8, font=Fonts.body(11))
        self.nbre_heure_entry.grid(row=0, column=5, padx=(0, 12), pady=10, sticky="w")

        # Card recherche + actions principales
        tools = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        tools.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 6))
        tools.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(tools, text="Recherche :", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(row=0, column=0, padx=(12, 6), pady=10, sticky="w")
        self.search_entry = ctk.CTkEntry(tools, height=32, fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
                                         corner_radius=8, font=Fonts.body(11),
                                         placeholder_text="Matricule, nom ou prénom…")
        self.search_entry.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="ew")
        self.search_entry.bind("<Return>", self.search_personnel)

        styled.button_primary(tools, text="Rechercher", icon="🔍", width=120, height=32, command=self.search_personnel).grid(row=0, column=2, padx=(0, 8), pady=10, sticky="e")
        styled.button_success(tools, text="Valider", icon="✅", width=110, height=32, command=self.valider_absence).grid(row=0, column=3, padx=(0, 12), pady=10, sticky="e")

        # Card tableau
        table_card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        table_card.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 6))
        table_card.grid_columnconfigure(0, weight=1)
        table_card.grid_rowconfigure(0, weight=1)

        cols = ("ID", "Nom", "Prénom", "Matricule", "Fonction")
        self.personnel_tree = ttk.Treeview(table_card, columns=cols, show="headings", style="P.Treeview", selectmode="browse")
        for col, w, anc in [
            ("ID", 60, "center"),
            ("Nom", 180, "w"),
            ("Prénom", 180, "w"),
            ("Matricule", 120, "w"),
            ("Fonction", 160, "w"),
        ]:
            self.personnel_tree.heading(col, text=col)
            self.personnel_tree.column(col, width=w, anchor=anc, minwidth=50)
        self.personnel_tree.tag_configure("row_even", background=Colors.BG_CARD)
        self.personnel_tree.tag_configure("row_odd", background=Colors.BG_ROW_ALT)

        vsb = ttk.Scrollbar(table_card, orient="vertical", command=self.personnel_tree.yview)
        self.personnel_tree.configure(yscrollcommand=vsb.set)
        self.personnel_tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        vsb.grid(row=0, column=1, sticky="ns", pady=6)
        self.personnel_tree.bind("<<TreeviewSelect>>", self.on_personnel_select)

        # Card actions secondaires
        actions = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        actions.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 10))

        styled.button_premium(actions, text="Exporter PDF", icon="📄", width=140, height=32, command=self.generer_pdf).pack(side="left", padx=10, pady=10)
        styled.button_info(actions, text="Mise à jour", icon="🛠", width=150, height=32, command=self.open_update_window).pack(side="left", padx=0, pady=10)
        styled.button_secondary(actions, text="Imprimer", icon="🖨", width=130, height=32, command=self.imprimer).pack(side="right", padx=10, pady=10)

        self.personnel_selectionne_id = None

    def search_personnel(self, event=None):
        search_term = self.search_entry.get().strip()
        if not search_term:
            messagebox.showwarning("Recherche", "Veuillez entrer un terme de recherche.")
            return

        for item in self.personnel_tree.get_children():
            self.personnel_tree.delete(item)
        self._refresh_table_alternating_colors(self.personnel_tree)

        try:
            query = """
                SELECT p.id, p.nom, p.prenom, p.matricule, f.designationfonction
                FROM tb_personnel p
                JOIN tb_fonction f ON p.idfonction = f.idfonction
                WHERE p.matricule ILIKE %s OR p.nom ILIKE %s OR p.prenom ILIKE %s
            """
            self.cursor.execute(query, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
            personnels = self.cursor.fetchall()
            
            if not personnels:
                messagebox.showinfo("Recherche", "Aucun personnel trouvé.")
                return

            for personnel in personnels:
                self.personnel_tree.insert("", "end", values=personnel)
            self._refresh_table_alternating_colors(self.personnel_tree)
        except psycopg2.Error as e:
            messagebox.showerror("Erreur BD", f"Erreur lors de la recherche des personnels : {e}")

    def on_personnel_select(self, event):
        selected_item = self.personnel_tree.focus()
        if selected_item:
            values = self.personnel_tree.item(selected_item, 'values')
            self.personnel_selectionne_id = values[0]

    def valider_absence(self):
        if not self.personnel_selectionne_id:
            messagebox.showwarning("Sélection requise", "Veuillez sélectionner un personnel dans la liste.")
            return

        date_absence = self.date_entry.get_date()
        observation = self.observation_entry.get()
        nbre_heure_str = self.nbre_heure_entry.get()

        if not (date_absence and nbre_heure_str):
            messagebox.showwarning("Champs manquants", "Veuillez remplir tous les champs (Date, Nombre d'heures).")
            return
        
        try:
            nbre_heure = int(nbre_heure_str)

            self.cursor.execute("""
                INSERT INTO tb_absence (
                    idpers, date, observation, nbreheureabs
                ) VALUES (%s, %s, %s, %s)
            """, (self.personnel_selectionne_id, date_absence, observation, nbre_heure))
            
            self.conn.commit()
            try:
                self._logger.log(
                    action="Création absence",
                    element=f"idpers={self.personnel_selectionne_id}",
                    details=f"Absence enregistrée (date={date_absence}, heures={nbre_heure}, observation='{observation}')",
                    value=f"{nbre_heure} h",
                )
            except Exception:
                pass
            messagebox.showinfo("Succès", "Absence enregistrée avec succès.")
            self.clear_input_fields()

        except ValueError:
            messagebox.showerror("Erreur", "Le nombre d'heures doit être un nombre entier.")
        except psycopg2.Error as e:
            self.conn.rollback()
            messagebox.showerror("Erreur BD", f"Erreur lors de l'enregistrement de l'absence : {e}")

    def create_pdf_header(self):
        """Crée l'en-tête du PDF avec les informations de la société."""
        styles = getSampleStyleSheet()
        
        nom_style = ParagraphStyle(
            'NomSociete',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1a5490'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        info_style = ParagraphStyle(
            'InfoSociete',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#333333'),
            spaceAfter=3,
            alignment=TA_CENTER
        )
        
        elements = []
        elements.append(Paragraph(self.info_societe['nom'], nom_style))
        if self.info_societe['adresse']:
            elements.append(Paragraph(self.info_societe['adresse'], info_style))
        if self.info_societe['ville']:
            elements.append(Paragraph(self.info_societe['ville'], info_style))
        if self.info_societe['contact']:
            elements.append(Paragraph(f"Tél: {self.info_societe['contact']}", info_style))
        elements.append(Spacer(1, 0.2*inch))
        
        return elements

    def generer_pdf(self):
        try:
            self.cursor.execute("""
                SELECT
                    p.matricule, p.nom, p.prenom, f.designationfonction AS fonction,
                    a.date, a.observation, a.nbreheureabs
                FROM tb_absence a
                JOIN tb_personnel p ON a.idpers = p.id
                JOIN tb_fonction f ON p.idfonction = f.idfonction
                ORDER BY a.date DESC, p.nom ASC
            """)
            absences = self.cursor.fetchall()

            if not absences:
                messagebox.showinfo("Génération PDF", "Aucune absence à exporter.")
                return

            filepath = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("Fichier PDF", "*.pdf"), ("Tous les fichiers", "*.*")],
                title="Enregistrer le fichier PDF des absences"
            )

            if not filepath:
                return

            doc = SimpleDocTemplate(filepath, pagesize=landscape(letter),
                                  topMargin=0.5*inch, bottomMargin=0.5*inch)
            elements = []
            elements.extend(self.create_pdf_header())

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=14,
                textColor=colors.HexColor('#1a5490'),
                spaceAfter=12,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
            
            title = Paragraph("Liste des Absences de Personnel", title_style)
            elements.append(title)
            elements.append(Spacer(1, 0.2*inch))
            
            data = [["Matricule", "Nom", "Prénom", "Fonction", "Date d'absence", "Observation", "Nb d'heures"]]
            for row in absences:
                row_list = list(row)
                if isinstance(row_list[4], datetime) or hasattr(row_list[4], 'strftime'):
                    row_list[4] = row_list[4].strftime('%d/%m/%Y')
                data.append(row_list)

            table_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5490')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#1a5490')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')])
            ])
            
            table = Table(data)
            table.setStyle(table_style)
            elements.append(table)
            
            doc.build(elements)
            messagebox.showinfo("Succès", "Le PDF a été généré avec succès.")
            self.open_pdf(filepath)

        except psycopg2.Error as e:
            messagebox.showerror("Erreur BD", f"Erreur lors de la génération du PDF : {e}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Une erreur s'est produite : {e}")

    def imprimer(self):
        try:
            import tempfile
            temp_dir = tempfile.gettempdir()
            filepath = os.path.join(temp_dir, f"absences_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
            self.generer_pdf_pour_impression(filepath)
            self.open_pdf(filepath)
        except Exception as e:
            messagebox.showerror("Erreur d'impression", f"Erreur lors de l'impression : {e}")

    def open_pdf(self, filepath):
        """Ouvre le fichier PDF avec le lecteur par défaut du système."""
        try:
            if sys.platform == "win32":
                os.startfile(filepath)
            elif sys.platform == "darwin":
                subprocess.call(["open", filepath])
            else:
                subprocess.call(["xdg-open", filepath])
        except Exception as e:
            messagebox.showwarning("Aperçu PDF", f"Fichier créé : {filepath}\nImpossible de l'ouvrir automatiquement.")

    def generer_pdf_pour_impression(self, filepath):
        try:
            self.cursor.execute("""
                SELECT
                    p.matricule, p.nom, p.prenom, f.designationfonction AS fonction,
                    a.date, a.observation, a.nbreheureabs
                FROM tb_absence a
                JOIN tb_personnel p ON a.idpers = p.id
                JOIN tb_fonction f ON p.idfonction = f.idfonction
                ORDER BY a.date DESC, p.nom ASC
            """)
            absences = self.cursor.fetchall()
            if not absences:
                raise Exception("Aucune absence à imprimer.")

            doc = SimpleDocTemplate(filepath, pagesize=landscape(letter),
                                  topMargin=0.5*inch, bottomMargin=0.5*inch)
            elements = []
            elements.extend(self.create_pdf_header())

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=14, 
                                        textColor=colors.HexColor('#1a5490'), alignment=TA_CENTER)
            
            elements.append(Paragraph("Liste des Absences des Personnels", title_style))
            elements.append(Spacer(1, 0.2*inch))
            
            data = [["Matricule", "Nom", "Prénom", "Fonction", "Date d'absence", "Observation", "Nb d'heures"]]
            for row in absences:
                row_list = list(row)
                if isinstance(row_list[4], datetime) or hasattr(row_list[4], 'strftime'):
                    row_list[4] = row_list[4].strftime('%d/%m/%Y')
                data.append(row_list)

            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5490')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTSIZE', (0, 1), (-1, -1), 9)
            ]))
            elements.append(table)
            doc.build(elements)
        except Exception as e:
            raise e

    def open_update_window(self):
        try:
            self._page_absenceMJ_window = PageAbsenceMJ(self.master, self.conn, self.cursor)
            self._page_absenceMJ_window.grab_set()
            self._page_absenceMJ_window.focus_set()
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'ouvrir la fenêtre de mise à jour : {e}")

    def clear_input_fields(self):
        self.date_entry.set_date(datetime.now().date())
        self.observation_entry.delete(0, ctk.END)
        self.nbre_heure_entry.delete(0, ctk.END)
        self.personnel_tree.delete(*self.personnel_tree.get_children())
        self._refresh_table_alternating_colors(self.personnel_tree)
        self.personnel_selectionne_id = None
        self.search_entry.delete(0, ctk.END)

    @staticmethod
    def launch(master, session_data=None):
        """Méthode statique pour lancer la page (compatibilité avec app_main)"""
        page = PageAbsence(master)
        return page

if __name__ == "__main__":
    root = ctk.CTk()
    root.title("Page Absences Personnel")
    root.geometry("800x600")
    page_instance = PageAbsence(root)
    page_instance.pack(expand=True, fill="both")
    root.mainloop()
