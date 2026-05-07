import customtkinter as ctk
import tkinter.messagebox as messagebox
from datetime import datetime
import psycopg2
from tkcalendar import DateEntry
import tkinter.ttk as ttk
import pandas as pd # For Excel export
from reportlab.lib.pagesizes import letter, landscape # For PDF export
from reportlab.pdfgen import canvas # For PDF export
import os # For file path operations
import subprocess # For opening the exported file
import json
import sys
from resource_utils import get_config_path, safe_file_read


# Ensure the parent directory is in the Python path for absolute imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    
class DatabaseManager:
    def __init__(self):
        self.db_params = self._load_db_config()
        self.conn = None
        self.cursor = None

    def _load_db_config(self):
        """Loads database configuration from 'config.json'."""
        try:
            config_path = get_config_path('config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('database')
        except FileNotFoundError:
            print("Error: 'config.json' not found.")
            return None
        except KeyError:
            print("Error: 'database' key is missing in 'config.json'.")
            return None
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in 'config.json': {e}")
            return None
        except UnicodeDecodeError as e:
            print(f"Error: Encoding problem in 'config.json': {e}")
            return None

    def connect(self):
        """Establishes a new database connection."""
        if self.db_params is None:
            print("Cannot connect: Database configuration is missing.")
            return False

        try:
            self.conn = psycopg2.connect(
                host=self.db_params['host'],
                user=self.db_params['user'],
                password=self.db_params['password'],
                database=self.db_params['database'],
                port=self.db_params['port'],
                client_encoding='UTF8'
            )
            self.cursor = self.conn.cursor()
            print("Connection to the database successful!")
            return True
        except psycopg2.OperationalError as e:
            print(f"Error connecting to the database: {e}")
            self.conn = None
            self.cursor = None
            return False
        except Exception as e:
            print(f"Unexpected error connecting to database: {e}")
            self.conn = None
            self.cursor = None
            return False

    def get_connection(self):
        """Returns the database connection if connected, otherwise attempts to connect."""
        if self.conn is None or self.conn.closed:
            if self.connect():
                return self.conn
            else:
                return None
        return self.conn

    def close(self):
        """Closes the database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

# Instantiate DatabaseManager
db_manager = DatabaseManager()

# Global database connection (as per your original setup)
# Instantiate DatabaseManager and establish a connection
db_manager = DatabaseManager()
conn = db_manager.get_connection()

if conn is None:
    messagebox.showerror("Erreur de connexion", "Impossible de se connecter à la base de données.")
    
cursor = conn.cursor()
    

# Global sort_order for column sorting
sort_order = {}



def sort_column(tv, col, col_index):
    """Sorts the Treeview column data."""
    global sort_order
    data = [(tv.set(k, col), k) for k in tv.get_children('')]
    try:
        if col in ["Taux horaire", "Total Heure", "Montant", "Avance 15e", "Déduction", "Net à payer"]:
            # Handle French number format for sorting
            data.sort(key=lambda t: float(str(t[0]).replace('.', '').replace(',', '.')),
                      reverse=sort_order.get(col, False))
        else:
            data.sort(key=lambda t: str(t[0]).lower(),
                      reverse=sort_order.get(col, False))
    except Exception:
        data.sort(reverse=sort_order.get(col, False))

    for index, (val, k) in enumerate(data):
        tv.move(k, '', index)

    sort_order[col] = not sort_order.get(col, False)

#---

## PageEtatSalaireHoraire Class

#```python
class PageEtatSalaireHoraire(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.conn = conn
        self.cursor = cursor

        # Data storage for export (unformatted values)
        self.current_export_data = []

        # Configure grid
        self.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6, 7), weight=1)
        self.grid_rowconfigure(2, weight=1)

        # --- Date Entry, Validate, Export Buttons ---
        ctk.CTkLabel(self, text="Date début (AAAA-MM-JJ)").grid(row=0, column=0, padx=10, pady=(10,0), sticky="w")
        self.entry_start = DateEntry(self, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.entry_start.grid(row=1, column=0, padx=10, pady=(0,10), sticky="ew")

        ctk.CTkLabel(self, text="Date fin (AAAA-MM-JJ)").grid(row=0, column=1, padx=10, pady=(10,0), sticky="w")
        self.entry_end = DateEntry(self, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.entry_end.grid(row=1, column=1, padx=10, pady=(0,10), sticky="ew")

        self.validate_btn = ctk.CTkButton(self, text="Valider", fg_color="#2ecc71", 
        hover_color="#27ae60",command=self.load_data)
        self.validate_btn.grid(row=1, column=2, padx=10, pady=(0,10), sticky="ew")

        self.btn_export_excel = ctk.CTkButton(self, text="Exporter Excel", command=self.export_excel)
        self.btn_export_excel.grid(row=1, column=6, padx=10, pady=(0,10), sticky="ew")

        self.btn_export_pdf = ctk.CTkButton(self, text="Exporter PDF", command=self.export_pdf)
        self.btn_export_pdf.grid(row=1, column=7, padx=10, pady=(0,10), sticky="ew")

        # --- Search Entry ---
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(self, textvariable=self.search_var, placeholder_text="Rechercher par nom/prénom")
        self.search_entry.grid(row=1, column=3, columnspan=3, padx=10, pady=(0,10), sticky="ew")
        self.search_entry.bind('<Return>', lambda e: self.load_data())

        # --- Treeview for displaying data ---
        self.columns = ("Nom", "Prénom", "Taux horaire", "Total Heure", "Montant", "Avance 15e", "Déduction", "Net à payer")

        # Configure ttk.Style for Treeview
        self.style = ttk.Style()
        self.style.theme_use("default")

        # Dynamically get CustomTkinter colors
        try:
            ctk_fg_color = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"])
            ctk_text_color = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkLabel"]["text_color"])
            ctk_button_fg_color = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["fg_color"])
            ctk_button_text_color = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["text_color"])
            ctk_button_hover_color = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["hover_color"])
            ctk_border_color = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["border_color"])
        except AttributeError:
            # Fallback colors if ThemeManager attributes are not directly accessible
            ctk_fg_color = "#2b2b2b"
            ctk_text_color = "#ffffff"
            ctk_button_fg_color = "#1f6aa5"
            ctk_button_text_color = "#ffffff"
            ctk_button_hover_color = "#144870"
            ctk_border_color = "#2b2b2b"

        self.style.configure("Treeview",
                             background="#FFFFFF",
                             foreground="#000000",
                             rowheight=22,
                             fieldbackground="#FFFFFF",
                             borderwidth=0,
                             font=('Segoe UI', 8))
        self.style.map("Treeview",
                       background=[('selected', ctk_button_fg_color)],
                       foreground=[('selected', ctk_button_text_color)])

        self.style.configure("Treeview.Heading",
                             background="#E8E8E8",
                             foreground=ctk_button_text_color,
                             font=('Helvetica', 10, 'bold'),
                             relief="flat")
        self.style.map("Treeview.Heading",
                       background=[('active', ctk_button_hover_color)])

        self.tree = ttk.Treeview(self, columns=self.columns, show="headings")
        self.tree.grid(row=2, column=0, columnspan=8, padx=10, pady=10, sticky="nsew")
        self._configure_table_alternating_colors(self.tree)

        for col in self.columns:
            self.tree.heading(col, text=col, command=lambda c=col, i=self.columns.index(col): sort_column(self.tree, c, i))
            self.tree.column(col, anchor="center", width=100)

        self.tree.column("Nom", anchor="w", width=120)
        self.tree.column("Prénom", anchor="w", width=120)
        self.tree.column("Taux horaire", width=100)
        self.tree.column("Total Heure", width=100)
        self.tree.column("Montant", width=100)
        self.tree.column("Avance 15e", width=100)
        self.tree.column("Déduction", width=100)
        self.tree.column("Net à payer", width=100)

        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.vsb.grid(row=2, column=8, sticky="ns", padx=(0,10), pady=10)
        self.tree.configure(yscrollcommand=self.vsb.set)

        # --- Count Label ---
        self.label_count = ctk.CTkLabel(self, text="Professeurs affichés : 0")
        self.label_count.grid(row=3, column=0, columnspan=8, padx=10, pady=10, sticky="w")

    def _configure_table_alternating_colors(self, tree):
        tree.tag_configure("row_even", background="#FFFFFF")
        tree.tag_configure("row_odd", background="#D9EEED")

    def _refresh_table_alternating_colors(self, tree):
        for idx, item in enumerate(tree.get_children()):
            existing_tags = tuple(t for t in tree.item(item, "tags") if t not in ("row_even", "row_odd"))
            alt_tag = "row_even" if idx % 2 == 0 else "row_odd"
            tree.item(item, tags=(alt_tag,) + existing_tags)

    def load_data(self):
        """Loads and displays data in the Treeview based on filters."""
        for row in self.tree.get_children():
            self.tree.delete(row)
        self._refresh_table_alternating_colors(self.tree)

        self.current_export_data = [] # Clear data for export

        total_heures = 0.0
        total_montants = 0.0
        count_professeurs = 0

        search_term = self.search_var.get().strip()
        start_date_str = self.entry_start.get_date().strftime("%Y-%m-%d")
        end_date_str = self.entry_end.get_date().strftime("%Y-%m-%d")

        try:
            datetime.strptime(start_date_str, "%Y-%m-%d")
            datetime.strptime(end_date_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Erreur", "Les dates doivent être valides (AAAA-MM-JJ)")
            return

        
        query = '''
            SELECT p.id, p.nom, p.prenom,
                   (
                       SELECT tauxhoraire FROM tb_tauxhoraire t
                       WHERE t.idpers = p.id
                       ORDER BY dateregistre DESC
                       LIMIT 1
                   ) AS tauxhoraire,
                   COALESCE(SUM(pr.nbheure), 0) AS totalheure,
                   COALESCE(SUM(pr.nbheure), 0) * (
                       SELECT tauxhoraire FROM tb_tauxhoraire t
                       WHERE t.idpers = p.id
                       ORDER BY dateregistre DESC
                       LIMIT 1
                   ) AS montant
            FROM tb_personnel p
            LEFT JOIN tb_presencepers pr ON pr.idpers = p.id
                 AND pr.date BETWEEN %s AND %s
            WHERE (
                SELECT tauxhoraire FROM tb_tauxhoraire t
                WHERE t.idpers = p.id
                ORDER BY dateregistre DESC
                LIMIT 1
            ) IS NOT NULL
            AND CONCAT(p.nom, ' ', p.prenom) ILIKE %s
            GROUP BY p.id, p.nom, p.prenom
            ORDER BY p.nom, p.prenom
        '''

        try:
            self.cursor.execute(query, (start_date_str, end_date_str, f"%{search_term}%"))
            rows = self.cursor.fetchall()
        except Exception as e:
            messagebox.showerror("Erreur SQL", f"Erreur lors de l'exécution de la requête principale: {e}")
            return

        for row in rows:
            idpers, nom, prenom, taux, heures, montant = row
            if heures == 0:
                continue

            try:
                self.cursor.execute("SELECT COALESCE(SUM(mtpaye), 0) FROM tb_avancepers WHERE idpers = %s AND datepmt BETWEEN %s AND %s",
                                   (idpers, start_date_str, end_date_str))
                avance15 = self.cursor.fetchone()[0]
            except Exception as e:
                messagebox.showerror("Erreur Avance 15e", f"Erreur lors de la récupération de l'avance 15e pour {nom} {prenom}: {e}")
                avance15 = 0

            try:
                self.cursor.execute("""
                    SELECT COALESCE(SUM(mtpaye / NULLIF(nbremboursement, 0)), 0)
                    FROM tb_avancespecpers
                    WHERE idpers = %s AND datepmt BETWEEN %s AND %s
                """, (idpers, start_date_str, end_date_str))
                deduction = self.cursor.fetchone()[0]
            except Exception as e:
                messagebox.showerror("Erreur Déduction Spéciale", f"Erreur lors de la récupération de la déduction spéciale pour {nom} {prenom}: {e}")
                deduction = 0

            net = (montant if montant is not None else 0) - (avance15 if avance15 is not None else 0) - (deduction if deduction is not None else 0)

            # Store raw data for export
            self.current_export_data.append(
                (nom, prenom, taux, heures, montant, avance15, deduction, net)
            )

            # Format numbers for display (French format)
            taux_fmt = f"{taux:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".") if taux is not None else "0"
            heures_fmt = f"{heures:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".") if heures is not None else "0"
            montant_fmt = f"{montant:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".") if montant is not None else "0"
            avance_fmt = f"{avance15:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".") if avance15 is not None else "0"
            deduction_fmt = f"{deduction:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".") if deduction is not None else "0"
            net_fmt = f"{net:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".") if net is not None else "0"

            self.tree.insert('', 'end', values=(nom, prenom, taux_fmt, heures_fmt, montant_fmt, avance_fmt, deduction_fmt, net_fmt))

            total_heures += float(heures) if heures is not None else 0
            total_montants += float(net) if net is not None else 0
            count_professeurs += 1

        total_heure_fmt = f"{total_heures:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
        total_montant_fmt = f"{total_montants:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
        self.tree.insert('', 'end', values=('', 'TOTAL', '', total_heure_fmt, '', '', '', total_montant_fmt), tags=('total',))
        self.tree.tag_configure('total', background='#e0f7fa', font=('Arial', 10, 'bold'))
        self._refresh_table_alternating_colors(self.tree)

        self.label_count.configure(text=f"Professeurs affichés : {count_professeurs}")

    def get_company_info(self):
        """Récupère les informations de la société depuis la base de données."""
        try:
            self.cursor.execute("SELECT nomsociete, adressesociete, contactsociete FROM tb_infosociete LIMIT 1")
            info = self.cursor.fetchone()
            if info:
                return {"nom": info[0], "adresse": info[1], "contact": info[2]}
            return {"nom": "Ma Société", "adresse": "", "contact": ""}
        except Exception:
            return {"nom": "Ma Société", "adresse": "", "contact": ""}

    def export_excel(self):
        if not self.current_export_data:
            messagebox.showinfo("Info", "Aucune donnée à exporter.")
            return

        company = self.get_company_info()
        start_date = self.entry_start.get_date().strftime("%d/%m/%Y")
        end_date = self.entry_end.get_date().strftime("%d/%m/%Y")
        
        # Préparation du DataFrame
        df = pd.DataFrame(self.current_export_data, columns=self.columns)
        file_path = os.path.join(os.path.expanduser("~"), "Desktop", "etat_salaire_horaire.xlsx")
        
        try:
            writer = pd.ExcelWriter(file_path, engine='xlsxwriter')
            # On écrit les données à partir de la ligne 6 pour laisser de la place à l'en-tête
            df.to_excel(writer, index=False, sheet_name='Salaire', startrow=5)
            
            workbook = writer.book
            worksheet = writer.sheets['Salaire']
            
            # Formats
            header_format = workbook.add_format({'bold': True, 'font_size': 14})
            info_format = workbook.add_format({'font_size': 10})

            # Insertion des informations de la société
            worksheet.write('A1', company['nom'], header_format)
            worksheet.write('A2', f"Adresse: {company['adresse']}", info_format)
            worksheet.write('A3', f"Contact: {company['contact']}", info_format)
            worksheet.write('A4', f"Salaire pour la période: du {start_date} au {end_date}", workbook.add_format({'bold': True}))

            writer.close()
            messagebox.showinfo("Exportation Excel", f"Données exportées vers:\n{file_path}")
            os.startfile(file_path) if os.name == 'nt' else subprocess.Popen(['open', file_path])
        except Exception as e:
            messagebox.showerror("Erreur Excel", f"Erreur: {e}")

    def export_pdf(self):
        if not self.current_export_data:
            messagebox.showinfo("Info", "Aucune donnée à exporter. Veuillez d'abord afficher les données.")
            return

        company = self.get_company_info()
        start_date = self.entry_start.get_date().strftime("%d/%m/%Y")
        end_date = self.entry_end.get_date().strftime("%d/%m/%Y")
        file_path = os.path.join(os.path.expanduser("~"), "Desktop", "etat_salaire_horaire.pdf")

        try:
            pdf = canvas.Canvas(file_path, pagesize=landscape(letter))
        
            def add_header(pdf_canvas, page_num):
                # 1. Infos Société (Haut Gauche)
                pdf_canvas.setFont("Helvetica-Bold", 12)
                pdf_canvas.drawString(40, 575, company['nom'].upper())
                pdf_canvas.setFont("Helvetica", 9)
                pdf_canvas.drawString(40, 560, f"Adresse : {company['adresse']}")
                pdf_canvas.drawString(40, 545, f"Contact : {company['contact']}")
            
                # 2. Titre Central
                pdf_canvas.setFont("Helvetica-Bold", 16)
                pdf_canvas.drawCentredString(411, 520, "ETAT DE SALAIRE HORAIRE")
                pdf_canvas.setFont("Helvetica-BoldOblique", 11)
                pdf_canvas.drawCentredString(411, 505, f"Période du : {start_date} au {end_date}")
            
                # 3. Métadonnées (Haut Droite)
                current_date = datetime.now().strftime("%d/%m/%Y %H:%M")
                pdf_canvas.setFont("Helvetica", 9)
                pdf_canvas.drawString(650, 575, f"Imprimé le : {current_date}")
                pdf_canvas.drawString(700, 20, f"Page {page_num}")

            page_number = 1
            add_header(pdf, page_number)

            # Positions des colonnes
            x_positions = [40, 140, 240, 340, 440, 530, 620, 710]
            y = 470 # Position de départ sous l'en-tête
            line_height = 20

            # Dessiner les en-têtes du tableau
            pdf.setFont("Helvetica-Bold", 10)
            pdf.line(40, y + 15, 780, y + 15) # Ligne au dessus
            for i, header in enumerate(self.columns):
                pdf.drawString(x_positions[i], y, header)
            pdf.line(40, y - 5, 780, y - 5) # Ligne en dessous
            y -= line_height

            pdf.setFont("Helvetica", 9)
        
            total_heures_sum = 0.0
            total_net_sum = 0.0

            for row_data in self.current_export_data:
                # Gestion du saut de page
                if y < 60:
                    pdf.showPage()
                    page_number += 1
                    add_header(pdf, page_number)
                    y = 470
                    # Répéter les en-têtes sur la nouvelle page
                    pdf.setFont("Helvetica-Bold", 10)
                    for i, header in enumerate(self.columns):
                        pdf.drawString(x_positions[i], y, header)
                    y -= line_height
                    pdf.setFont("Helvetica", 9)

                # Dessiner les données
                for i, value in enumerate(row_data):
                    if isinstance(value, (float, int)):
                        display_val = f"{value:,.0f}".replace(",", " ").replace(".", ",")
                    else:
                        display_val = str(value)
                    pdf.drawString(x_positions[i], y, display_val)

                total_heures_sum += row_data[3] if row_data[3] else 0
                total_net_sum += row_data[7] if row_data[7] else 0
                y -= line_height

            # Ligne de total final
            pdf.line(40, y + 10, 780, y + 10)
            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(x_positions[0], y-5, "TOTAL GÉNÉRAL :")
            pdf.drawString(x_positions[3], y-5, f"{total_heures_sum:,.0f}".replace(",", " "))
            pdf.drawString(x_positions[7], y-5, f"{total_net_sum:,.0f}".replace(",", " "))

            pdf.save()
            messagebox.showinfo("Succès", f"PDF généré : {file_path}")
            os.startfile(file_path) if os.name == 'nt' else subprocess.Popen(['open', file_path])

        except Exception as e:
            messagebox.showerror("Erreur PDF", f"Détails : {e}")

# --- Main Application setup (remains similar) ---
if __name__ == "__main__":
    app = ctk.CTk()
    app.title("État de salaire par heure")
    app.geometry("1200x700")
    app.grid_rowconfigure(0, weight=1)
    app.grid_columnconfigure(0, weight=1)

    page_etat_salaire_horaire = PageEtatSalaireHoraire(app)
    page_etat_salaire_horaire.grid(row=0, column=0, sticky="nsew")

    app.mainloop()

    # Close DB connection
    if cursor:
        cursor.close()
    if conn:
        conn.close()
