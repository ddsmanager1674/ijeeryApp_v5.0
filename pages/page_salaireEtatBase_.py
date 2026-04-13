import customtkinter as ctk
import tkinter.messagebox as messagebox
from datetime import datetime
import psycopg2
import pandas as pd
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
import os
import subprocess
import tkinter.ttk as ttk
import json
import sys
from resource_utils import get_config_path, safe_file_read

from app_theme import Colors, Fonts, styled, Layout


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
        except Exception as e:
            print(f"Error loading config: {e}")
            return None

    def connect(self):
        """Establishes a new database connection."""
        if self.db_params is None: return False
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
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def get_connection(self):
        if self.conn is None or self.conn.closed:
            if self.connect(): return self.conn
        return self.conn

db_manager = DatabaseManager()

class PageSalaireEtatSB(ctk.CTkFrame):
    def __init__(self, parent):
        # [UI] État de Salaire (base) — thème iJeery
        super().__init__(parent, fg_color=Colors.BG_PAGE)

        self.conn = db_manager.get_connection()
        if not self.conn:
            messagebox.showerror("Erreur", "Connexion impossible.")
            return

        self.cursor = self.conn.cursor()

        self._setup_treeview_style()
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT, corner_radius=0, height=46)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        left = styled.frame(header)
        left.pack(side="left", padx=14)
        ctk.CTkLabel(left, text="📊", font=Fonts.heading(16), text_color=Colors.TEXT_ON_DARK).pack(side="left", padx=(0, 8))
        inner = styled.frame(left)
        inner.pack(side="left")
        ctk.CTkLabel(inner, text="État de Salaire", font=Fonts.bold(13), text_color=Colors.TEXT_ON_DARK).pack(anchor="w")
        ctk.CTkLabel(inner, text="Salaire base, avances et net", font=Fonts.small(9), text_color=Colors.TEXT_ON_DARK_DIM).pack(anchor="w")

        toolbar = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        toolbar.grid(row=1, column=0, sticky="ew", padx=10, pady=(10, 6))
        for c in range(0, 5):
            toolbar.grid_columnconfigure(c, weight=1)

        self.label_mois = ctk.CTkLabel(toolbar, text="Mois :", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY)
        self.label_mois.grid(row=0, column=0, padx=(12, 6), pady=10, sticky="w")

        mois_vals = [
            "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
            "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
        ]
        self.mois_combobox = styled.combobox(toolbar, values=mois_vals, height=32)
        self.mois_combobox.grid(row=0, column=1, padx=(0, 8), pady=10, sticky="ew")
        # [UI] Mois courant par défaut au chargement
        try:
            self.mois_combobox.set(mois_vals[datetime.now().month - 1])
        except Exception:
            pass

        styled.button_success(toolbar, text="Afficher", icon="🔍", width=120, height=32, command=self.afficher_donnees).grid(row=0, column=2, padx=4, pady=10, sticky="ew")
        styled.button_premium(toolbar, text="Excel", icon="📊", width=120, height=32, command=self.exporter_excel).grid(row=0, column=3, padx=4, pady=10, sticky="ew")
        styled.button_premium(toolbar, text="PDF", icon="📄", width=120, height=32, command=self.exporter_pdf).grid(row=0, column=4, padx=(4, 12), pady=10, sticky="ew")

        self.headers = ["Nom", "Prénom", "Salaire Base", "Avance 15e", "Déduction Avance Spéciale", "Net à Payer"]
        self.current_display_data = []

        table_card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        table_card.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 6))
        table_card.grid_rowconfigure(0, weight=1)
        table_card.grid_columnconfigure(0, weight=1)

        self.treeview = ttk.Treeview(table_card, columns=self.headers, show="headings", style="P.Treeview", selectmode="browse")
        self._configure_table_alternating_colors(self.treeview)
        self.treeview.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        vsb = ttk.Scrollbar(table_card, orient="vertical", command=self.treeview.yview)
        self.treeview.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns", pady=6)
        for col in self.headers:
            self.treeview.heading(col, text=col)
            self.treeview.column(col, anchor="center", width=120)

        self.label_count = ctk.CTkLabel(self, text="Nombre affichés: 0", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY)
        self.label_count.grid(row=4, column=0, sticky="w", padx=14, pady=(0, 10))

    def _setup_treeview_style(self):
        # [UI] Style tableau aligné sur le module Personnel
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

    def _configure_table_alternating_colors(self, tree):
        tree.tag_configure("row_even", background=Colors.BG_CARD)
        tree.tag_configure("row_odd", background=Colors.BG_ROW_ALT)

    def _refresh_table_alternating_colors(self, tree):
        for idx, item in enumerate(tree.get_children()):
            tree.item(item, tags=("row_even" if idx % 2 == 0 else "row_odd",))

    def get_info_societe(self):
        """Récupère les informations de l'entreprise."""
        try:
            self.cursor.execute("SELECT nomsociete, adressesociete, contactsociete FROM tb_infosociete LIMIT 1")
            res = self.cursor.fetchone()
            return res if res else ("SOCIETE", "ADRESSE", "CONTACT")
        except:
            return ("SOCIETE", "ADRESSE", "CONTACT")

    def recuperer_donnees(self, mois):
        query = """
        SELECT p.nom, p.prenom, COALESCE(sb.montant, 0),
               COALESCE(avq.somme, 0),
               COALESCE(CASE WHEN DATE_TRUNC('month', avs.datepmt) <= DATE_TRUNC('month', make_date(EXTRACT(YEAR FROM CURRENT_DATE)::int, %s, 1))
                        AND DATE_TRUNC('month', make_date(EXTRACT(YEAR FROM CURRENT_DATE)::int, %s, 1)) < DATE_TRUNC('month', avs.datepmt + (avs.nbremboursement * INTERVAL '1 month'))
                        THEN ROUND(avs.mtpaye::numeric / avs.nbremboursement::numeric, 2) ELSE 0 END, 0),
               0 -- Net à payer calculé après
        FROM tb_personnel p
        LEFT JOIN tb_salairebasepers sb ON p.id = sb.idpers
        LEFT JOIN tb_avancespecpers avs ON p.id = avs.idpers
        LEFT JOIN (SELECT idpers, SUM(mtpaye) as somme FROM tb_avancepers WHERE EXTRACT(MONTH FROM datepmt) = %s GROUP BY idpers) avq ON p.id = avq.idpers
        ORDER BY p.nom;
        """
        try:
            self.cursor.execute(query, (mois, mois, mois))
            raw_data = self.cursor.fetchall()
            final_data = []
            for r in raw_data:
                net = float(r[2]) - float(r[3]) - float(r[4])
                final_data.append((*r[:5], net))
            return final_data
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
            return []

    def afficher_donnees(self):
        mois_str = self.mois_combobox.get()
        if not mois_str: return
        mois_idx = self.mois_combobox.cget("values").index(mois_str) + 1
        
        for item in self.treeview.get_children(): self.treeview.delete(item)
        self._refresh_table_alternating_colors(self.treeview)
        self.current_display_data = self.recuperer_donnees(mois_idx)
        
        for row in self.current_display_data:
            formatted = [f"{v:,.2f}".replace(",", " ").replace(".", ",") if isinstance(v, (float, int)) else v for v in row]
            self.treeview.insert("", "end", values=formatted)
        self._refresh_table_alternating_colors(self.treeview)
        self.label_count.configure(text=f"Nombre d'enregistrements: {len(self.current_display_data)}")

    def exporter_excel(self):
        if not self.current_display_data: return
        df = pd.DataFrame(self.current_display_data, columns=self.headers)
        path = os.path.join(os.path.expanduser("~"), "Desktop", "salaire_base.xlsx")
        df.to_excel(path, index=False)
        messagebox.showinfo("Export", f"Fichier Excel créé sur le bureau.")

    def exporter_pdf(self):
        if not self.current_display_data: return
        
        nom_soc, adr_soc, tel_soc = self.get_info_societe()
        mois_sel = self.mois_combobox.get()
        path = os.path.join(os.path.expanduser("~"), "Desktop", "etat_salaire.pdf")
        
        c = canvas.Canvas(path, pagesize=landscape(letter))
        width, height = landscape(letter)

        def draw_header(canvas_obj, page_num):
            canvas_obj.setFont("Helvetica-Bold", 12)
            canvas_obj.drawString(50, height - 50, nom_soc.upper())
            canvas_obj.setFont("Helvetica", 10)
            canvas_obj.drawString(50, height - 65, adr_soc)
            canvas_obj.drawString(50, height - 80, f"Contact: {tel_soc}")
            
            canvas_obj.setFont("Helvetica-Bold", 14)
            canvas_obj.drawCentredString(width/2, height - 100, "ETAT DE SALAIRE (BASE)")
            canvas_obj.setFont("Helvetica-Oblique", 11)
            canvas_obj.drawCentredString(width/2, height - 115, f"Etat de salaire pour le mois de : {mois_sel}")
            
            canvas_obj.setFont("Helvetica", 9)
            canvas_obj.drawString(width - 150, height - 50, f"Date: {datetime.now().strftime('%d/%m/%Y')}")
            canvas_obj.drawString(width - 70, 30, f"Page {page_num}")

        page = 1
        draw_header(c, page)
        
        y = height - 150
        x_pos = [50, 150, 280, 400, 520, 650]
        c.setFont("Helvetica-Bold", 9)
        for i, h in enumerate(self.headers): c.drawString(x_pos[i], y, h)
        c.line(50, y-5, width-50, y-5)
        
        y -= 20
        c.setFont("Helvetica", 9)
        totaux = [0.0] * 4 # Pour SB, Avance, Déduction, Net

        for row in self.current_display_data:
            if y < 70:
                c.showPage()
                page += 1
                draw_header(c, page)
                y = height - 150
                c.setFont("Helvetica-Bold", 9)
                for i, h in enumerate(self.headers): c.drawString(x_pos[i], y, h)
                y -= 20
                c.setFont("Helvetica", 9)

            for i, val in enumerate(row):
                text = f"{val:,.2f}".replace(",", " ").replace(".", ",") if isinstance(val, (float, int)) else str(val)
                c.drawString(x_pos[i], y, text)
                if i >= 2: totaux[i-2] += float(val)
            y -= 15

        # Ligne de Totaux
        c.line(50, y+10, width-50, y+10)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(50, y-5, "TOTAL GÉNÉRAL :")
        for i, t in enumerate(totaux):
            c.drawString(x_pos[i+2], y-5, f"{t:,.2f}".replace(",", " ").replace(".", ","))

        c.save()
        messagebox.showinfo("PDF", "Exporté sur le bureau.")
        subprocess.Popen([path], shell=True)

if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("1000x700")
    PageSalaireEtatSB(app).pack(fill="both", expand=True)
    app.mainloop()
