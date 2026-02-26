import customtkinter as ctk
import tkinter.messagebox as messagebox
from datetime import datetime
import psycopg2
import pandas as pd
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
import os
import subprocess
import tkinter.ttk as ttk  # Import ttk
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
            # Assurez-vous que le chemin vers config.json est correct
            config_path = get_config_path('config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config['database']
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
                port=self.db_params['port']
            )
            self.cursor = self.conn.cursor()
            print("Connection to the database successful!")
            return True
        except psycopg2.OperationalError as e:
            print(f"Error connecting to the database: {e}")
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

# We will instantiate the DatabaseManager globally but manage the connection inside the class.
db_manager = DatabaseManager()


class Salaire(ctk.CTkFrame):  # ou autre base selon votre structure
    def __init__(self, master):
        super().__init__(master)
        # We handle the connection directly inside the class
        self.db_manager = db_manager
        self.conn = self.db_manager.get_connection()
        if self.conn is None:
            messagebox.showerror("Erreur de connexion", "Impossible de se connecter à la base de données.")
            self.is_connected = False
            return
        else:
            self.cursor = self.conn.cursor()
            self.is_connected = True
        self.cursor = self.conn.cursor()
        self._create_interface()

    def _configure_table_alternating_colors(self, tree):
        tree.tag_configure("row_even", background="#FFFFFF")
        tree.tag_configure("row_odd", background="#D9EEED")

    def _refresh_table_alternating_colors(self, tree):
        for idx, item in enumerate(tree.get_children()):
            tree.item(item, tags=("row_even" if idx % 2 == 0 else "row_odd",))



    def _create_interface(self):
        self.frame = ctk.CTkFrame(self.master, fg_color="transparent")
        self.frame.pack(expand=True, fill="both")

        # Configuration des lignes et colonnes de self.frame
        self.frame.grid_rowconfigure(0, weight=0) # Titre
        self.frame.grid_rowconfigure(1, weight=1) # frame_haut (for salaireEtatBase)
        self.frame.grid_rowconfigure(2, weight=1) # frame_bas (for salaireEtatHoraire)
        self.frame.grid_columnconfigure(0, weight=1)

        # Titre
        title_label = ctk.CTkLabel(self.frame, text="Gestion des Salaires", font=("Arial", 18)) # Changed title
        title_label.grid(row=0, column=0, pady=10, sticky="ew")

        # --- Frame haut (salaireEtatBase) --- #
        frame_haut = ctk.CTkFrame(self.frame)
        frame_haut.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        frame_haut.grid_columnconfigure(0, weight=1) # Configure column for the widget inside
        frame_haut.grid_rowconfigure(0, weight=1) # Configure row for the widget inside

        # Placeholder for salaireEtatBase - replace with your actual widget
        self.salaireEtatBase = ctk.CTkFrame(frame_haut, fg_color="blue") # Example placeholder
        self.salaireEtatBase.grid(row=0, column=0, sticky="nsew")
        # If salaireEtatBase is a separate class, you would instantiate it like:
        # self.salaireEtatBase = SalaireEtatBase(frame_haut)
        # self.salaireEtatBase.grid(row=0, column=0, sticky="nsew")

        # --- Frame bas (salaireEtatHoraire) --- #
        self.frame_bas = ctk.CTkFrame(self.frame)
        self.frame_bas.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        self.frame_bas.grid_columnconfigure(0, weight=1) # Configure column for the widget inside
        self.frame_bas.grid_rowconfigure(0, weight=1) # Configure row for the widget inside

        # Placeholder for salaireEtatHoraire - replace with your actual widget
        self.salaireEtatHoraire = ctk.CTkFrame(self.frame_bas, fg_color="green") # Example placeholder
        self.salaireEtatHoraire.grid(row=0, column=0, sticky="nsew")
        # If salaireEtatHoraire is a separate class, you would instantiate it like:
        # self.salaireEtatHoraire = SalaireEtatHoraire(self.frame_bas)
        # self.salaireEtatHoraire.grid(row=0, column=0, sticky="nsew")

# SALAIRE ETAT BASE

    # Configure grid for better responsiveness
        self.frame.grid_rowconfigure(1, weight=1)
        self.frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)


        self.label_mois = ctk.CTkLabel(frame_haut, text="Choisir le mois :")
        self.label_mois.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.mois_combobox = ctk.CTkComboBox(frame_haut, values=[
            "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
            "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
        self.mois_combobox.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.btn_afficher = ctk.CTkButton(frame_haut, text="Afficher", command=self.afficher_donnees)
        self.btn_afficher.grid(row=0, column=2, padx=10, sticky="ew")

        self.btn_excel = ctk.CTkButton(frame_haut, text="Exporter Excel", command=self.exporter_excel)
        self.btn_excel.grid(row=0, column=3, padx=10, sticky="ew")

        self.btn_pdf = ctk.CTkButton(frame_haut, text="Exporter PDF", command=self.exporter_pdf)
        self.btn_pdf.grid(row=0, column=4, padx=10, sticky="ew")

        self.headers = ["Nom", "Prénom", "Salaire Base", "Avance 15e", "Déduction Avance Spéciale", "Net à Payer"]
        self.current_display_data = []

        # --- Modifications pour ttk.Treeview ---
        # Créer un style pour le Treeview afin qu'il s'harmonise mieux avec CustomTkinter
        self.style = ttk.Style()
        self.style.theme_use("default") # Utiliser le thème par défaut pour pouvoir le modifier
        self.style.configure("Treeview",
                             background="#FFFFFF",
                             foreground="#000000",
                             rowheight=22,
                             fieldbackground="#FFFFFF",
                             borderwidth=0,
                             font=('Segoe UI', 8))
        self.style.map("Treeview",
                       background=[('selected', ctk.ThemeManager.theme["CTkButton"]["fg_color"])],
                       foreground=[('selected', ctk.ThemeManager.theme["CTkButton"]["text_color"])])

        self.style.configure("Treeview.Heading",
                             background="#E8E8E8",
                             foreground="#000000",
                             font=('Segoe UI', 8, 'bold'))
        self.style.map("Treeview.Heading",
                       background=[('active', ctk.ThemeManager.theme["CTkButton"]["hover_color"])])

        # Créer le Treeview
        self.treeview = ttk.Treeview(frame_haut, columns=self.headers, show="headings")
        self.treeview.grid(row=1, column=0, columnspan=5, padx=10, pady=10, sticky="nsew")
        self._configure_table_alternating_colors(self.treeview)

        # Configurer les en-têtes des colonnes
        for col in self.headers:
            self.treeview.heading(col, text=col, anchor="center")
            self.treeview.column(col, anchor="center", width=120) # Ajustez la largeur si nécessaire

        # Ajuster les largeurs spécifiques pour Nom et Prénom si vous voulez qu'ils soient plus larges
        self.treeview.column("Nom", anchor="w", width=150)
        self.treeview.column("Prénom", anchor="w", width=150)


        # Ajouter une barre de défilement verticale
        self.scrollbar_y = ttk.Scrollbar(frame_haut, orient="vertical", command=self.treeview.yview)
        self.scrollbar_y.grid(row=1, column=5, sticky="ns")
        self.treeview.configure(yscrollcommand=self.scrollbar_y.set)
        # --- Fin des modifications pour ttk.Treeview ---


        self.label_count = ctk.CTkLabel(self, text="Nombre affichés: 0")
        self.label_count.grid(row=2, column=0, columnspan=5, sticky="w", padx=10)

    # Note: La méthode _create_header_labels n'est plus nécessaire avec ttk.Treeview
    # car Treeview gère ses propres en-têtes. Vous pouvez la supprimer.

    def connect_db(self):
        try:
            # Lecture robuste du fichier config avec chemin absolu
            config_path = get_config_path('config.json')
            config_content, encoding = safe_file_read(config_path)
            config = json.loads(config_content)
            db_config = config['database']

            return psycopg2.connect(
                host=db_config['host'],
                user=db_config['user'],
                password=db_config['password'],
                database=db_config['database'],
                port=db_config['port']
            )
        except psycopg2.Error as e:
            messagebox.showerror("Erreur de connexion", f"Impossible de se connecter à la base de données: {e}")
            exit()
        except FileNotFoundError:
            messagebox.showerror("Erreur", f"Fichier config.json introuvable à: {get_config_path('config.json')}")
            exit()
        except KeyError as e:
            messagebox.showerror("Erreur", f"Clé manquante dans config.json: {e}")
            exit()
        except Exception as e:
            messagebox.showerror("Erreur de configuration", f"Erreur: {e}")
            exit()

    def recuperer_donnees(self, mois):
        query = """
        SELECT
            p.nom,
            p.prenom,
            COALESCE(sb.montant, 0) AS salaire_base,
            COALESCE(avances_quinzaine.somme_avance_quinzaine, 0) AS avance_quinzaine,
            CASE
                WHEN DATE_TRUNC('month', avs.datepmt) <= DATE_TRUNC('month', make_date(EXTRACT(YEAR FROM CURRENT_DATE)::int, %s, 1))
                     AND DATE_TRUNC('month', make_date(EXTRACT(YEAR FROM CURRENT_DATE)::int, %s, 1)) < DATE_TRUNC('month', avs.datepmt + (avs.nbremboursement * INTERVAL '1 month'))
                THEN ROUND(avs.mtpaye::numeric / avs.nbremboursement::numeric, 2)
                ELSE 0
            END AS deduction_avance_speciale,
            COALESCE(sb.montant, 0) - COALESCE(avances_quinzaine.somme_avance_quinzaine, 0) -
            CASE
                WHEN DATE_TRUNC('month', avs.datepmt) <= DATE_TRUNC('month', make_date(EXTRACT(YEAR FROM CURRENT_DATE)::int, %s, 1))
                     AND DATE_TRUNC('month', make_date(EXTRACT(YEAR FROM CURRENT_DATE)::int, %s, 1)) < DATE_TRUNC('month', avs.datepmt + (avs.nbremboursement * INTERVAL '1 month'))
                THEN ROUND(avs.mtpaye::numeric / avs.nbremboursement::numeric, 2)
                ELSE 0
            END AS net_a_payer
        FROM tb_avancespecprof avs
        JOIN tb_professeur p ON p.id = avs.idprof
        LEFT JOIN tb_salairebasepers sb ON p.id = sb.idprof
        LEFT JOIN (
            SELECT idprof, SUM(mtpaye) AS somme_avance_quinzaine
            FROM tb_avanceprof
            WHERE EXTRACT(MONTH FROM datepmt) = %s
            GROUP BY idprof
        ) AS avances_quinzaine ON p.id = avances_quinzaine.idprof
        WHERE avs.mtpaye > 0
        GROUP BY p.nom, p.prenom, sb.montant, avances_quinzaine.somme_avance_quinzaine, avs.mtpaye, avs.nbremboursement, avs.datepmt, p.id
        ORDER BY p.nom;
        """
        try:
            self.cursor.execute(query, (mois, mois, mois, mois, mois))
            return self.cursor.fetchall()
        except Exception as e:
            messagebox.showerror("Erreur SQL", f"Erreur lors de la récupération des données: {e}")
            return []

    def afficher_donnees(self):
        mois_str = self.mois_combobox.get()
        if not mois_str:
            messagebox.showwarning("Attention", "Veuillez sélectionner un mois.")
            return

        mois = self.mois_combobox.cget("values").index(mois_str) + 1

        # Supprimer toutes les lignes existantes dans le Treeview
        for item in self.treeview.get_children():
            self.treeview.delete(item)
        self._refresh_table_alternating_colors(self.treeview)

        donnees = self.recuperer_donnees(mois)
        self.current_display_data = [] # Réinitialiser les données affichées

        # Insérer les nouvelles données dans le Treeview
        for row_data in donnees:
            # Formater les floats pour l'affichage (avec 2 décimales et séparateur de milliers)
            formatted_row = []
            for j, value in enumerate(row_data):
                if isinstance(value, (float, int)):
                    formatted_row.append(f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")) # Format FR (virgule décimale, point milliers)
                else:
                    formatted_row.append(str(value))
            self.treeview.insert("", "end", values=formatted_row)
            self.current_display_data.append(row_data) # Conserver les valeurs numériques pour l'exportation
        self._refresh_table_alternating_colors(self.treeview)

        self.label_count.configure(text=f"Nombre d'enregistrements affichés: {len(donnees)}")

    def exporter_excel(self):
        if not self.current_display_data:
            messagebox.showinfo("Info", "Aucune donnée à exporter. Veuillez d'abord afficher les données.")
            return

        # Utiliser les données brutes (non formatées) pour l'exportation Excel
        df = pd.DataFrame(self.current_display_data, columns=self.headers)
        chemin = os.path.join(os.path.expanduser("~"), "Desktop", "salaire_professeurs.xlsx")
        try:
            df.to_excel(chemin, index=False)
            messagebox.showinfo("Exportation Excel", f"Données exportées avec succès dans {chemin}")
        except Exception as e:
            messagebox.showerror("Erreur Excel", f"Une erreur s'est produite lors de l'exportation Excel : {e}")

    def exporter_pdf(self):
        if not self.current_display_data:
            messagebox.showinfo("Info", "Aucune donnée à exporter. Veuillez d'abord afficher les données.")
            return

        chemin_bureau = os.path.join(os.path.expanduser("~"), "Desktop")
        nom_fichier_pdf = "salaire_professeurs.pdf"
        chemin_fichier_pdf = os.path.join(chemin_bureau, nom_fichier_pdf)

        try:
            pdf = canvas.Canvas(chemin_fichier_pdf, pagesize=landscape(letter))
            pdf.setFont("Helvetica", 9)

            def ajouter_entete(pdf_canvas, titre, page_num):
                pdf_canvas.setFont("Helvetica-Bold", 14)
                pdf_canvas.drawCentredString(421, 570, "FIANATRA")
                pdf_canvas.setFont("Helvetica", 10)
                pdf_canvas.drawCentredString(421, 555, f"{titre}")
                date_aujourd_hui = datetime.now().strftime("%d/%m/%Y %H:%M")
                pdf_canvas.drawString(650, 555, f"Date : {date_aujourd_hui}")
                pdf_canvas.drawString(700, 15, f"Page {page_num}")
                pdf_canvas.setFont("Helvetica", 9)

            page_number = 1
            ajouter_entete(pdf, "Etat de salaire (SB)", page_number)

            headers = ["Nom", "Prénom", "Salaire Base", "Avance 15e", "Déduction Avance Spéciale", "Net à Payer"]
            y = 530

            x_positions = [50, 160, 280, 390, 510, 630] # Ajustez ces positions pour le PDF si nécessaire

            for i, header in enumerate(headers):
                pdf.drawString(x_positions[i], y, header)

            y -= 15
            line_height = 15

            total_salaire_base = 0.0
            total_avance_quinzaine = 0.0
            total_deduction_avance_speciale = 0.0
            total_net_a_payer = 0.0

            for row_data in self.current_display_data: # Utilisez current_display_data qui contient les floats
                if y < 70:
                    pdf.showPage()
                    page_number += 1
                    ajouter_entete(pdf, "Etat de salaire (SB) (Suite)", page_number)
                    for i, header in enumerate(headers):
                        pdf.drawString(x_positions[i], 530, header)
                    y = 515

                for i, value in enumerate(row_data):
                    display_value = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if isinstance(value, (float, int)) else str(value)
                    pdf.drawString(x_positions[i], y, display_value)
                    try:
                        # Les calculs de totaux doivent toujours utiliser les valeurs numériques brutes
                        # C'est pourquoi self.current_display_data est important.
                        numeric_value = float(value) # value est déjà numérique ici
                        if i == 2:
                            total_salaire_base += numeric_value
                        elif i == 3:
                            total_avance_quinzaine += numeric_value
                        elif i == 4:
                            total_deduction_avance_speciale += numeric_value
                        elif i == 5:
                            total_net_a_payer += numeric_value
                    except ValueError:
                        pass # Ignore non-numeric values for totals
                y -= line_height

            y -= 10
            pdf.line(x_positions[0], y, x_positions[-1] + 80, y)
            y -= 15
            pdf.setFont("Helvetica-Bold", 9)
            pdf.drawString(x_positions[0], y, "Totaux:")
            # Formater les totaux avec le format français
            pdf.drawString(x_positions[2], y, f"{total_salaire_base:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            pdf.drawString(x_positions[3], y, f"{total_avance_quinzaine:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            pdf.drawString(x_positions[4], y, f"{total_deduction_avance_speciale:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            pdf.drawString(x_positions[5], y, f"{total_net_a_payer:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            pdf.setFont("Helvetica", 9)

            pdf.save()

            messagebox.showinfo("Exportation PDF", f"Données exportées vers PDF avec succès dans le bureau !\nFichier : {chemin_fichier_pdf}")

            if os.path.exists(chemin_fichier_pdf):
                try:
                    subprocess.Popen([chemin_fichier_pdf], shell=True)
                except Exception as e:
                    messagebox.showerror("Erreur lors de l'ouverture du PDF", f"Impossible d'ouvrir le fichier PDF : {e}")

        except Exception as e:
            messagebox.showerror("Erreur PDF", f"Une erreur s'est produite lors de l'exportation PDF : {e}")
    



root = ctk.CTk()
app = Salaire(root)
app.pack(fill="both", expand=True)
root.mainloop()
