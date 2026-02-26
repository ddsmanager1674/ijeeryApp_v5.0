import customtkinter as ctk
import tkinter as tk  # Import tkinter for ttk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime, date
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import json
import sys
import os
from resource_utils import get_config_path, safe_file_read


# Ensure the parent directory is in the Python path for absolute imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

    
def charger_personnels(cursor):
        """Charge la liste des personnels depuis la base de données."""
        cursor.execute("SELECT id, nom, prenom FROM tb_personnel ORDER BY nom")
        return [{"id": row[0], "nom": row[1], "prenom": row[2], "nom_complet": f"{row[1]} {row[2]}"} for row in cursor.fetchall()]

# ---
class FenetreAvanceSpec(ctk.CTkFrame):

    def __init__(self, master, iduser=None):
        super().__init__(master)
        self.master = master
        # Stocker l'iduser passé en paramètre
        self.iduser = iduser
        
        # Afficher l'iduser pour le débogage
        if self.iduser:
            print(f"FenetreAvanceSpec initialisée avec iduser: {self.iduser}")
        else:
            print("ATTENTION: FenetreAvanceSpec initialisée sans iduser!")

        # Connexion à la base de données
        self.conn = self.connect_db()
        self.cursor = None
        
        if self.conn:
            self.cursor = self.conn.cursor()
            self.initialize_database()

        self.personnel = charger_personnels(self.cursor)
        self.prof_ids = {prof["nom_complet"]: prof["id"] for prof in self.personnel}

        # Widgets d'interface
        self.creer_widgets()

        # Chargement initial des données
        self.charger_avances()

    def connect_db(self):
        """Établit la connexion à la base de données à partir du fichier config.json"""
        try:
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
                port=db_config['port'],
                client_encoding='UTF8'
            )
            print("Connection to the database successful!")
            return conn
        except Exception as err:
            messagebox.showerror("Erreur de connexion", f"Détails : {err}")
            return None

    def initialize_database(self):
        """Initialise la connexion à la base de données et crée la table si nécessaire."""
        if not self.cursor:
            return False
        
        try:        
            self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tb_avancespecpers (
                id SERIAL PRIMARY KEY,
                refpmt VARCHAR(50) UNIQUE,
                observation VARCHAR(120),
                idpers INT REFERENCES tb_personnel(id),
                mtpaye DOUBLE PRECISION NOT NULL CHECK (mtpaye > 0),
                nbremboursement INTEGER NOT NULL CHECK (nbremboursement > 0),
                datepmt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                idtypeoperation INT DEFAULT '2',
                iduser INT
            )
            """)
            self.conn.commit()
            return True
            
        except psycopg2.Error as err:
            messagebox.showerror("Erreur de connexion", f"Erreur : {err}")
            return False

    def _configure_table_alternating_colors(self, tree):
        tree.tag_configure("row_even", background="#FFFFFF")
        tree.tag_configure("row_odd", background="#D9EEED")

    def _refresh_table_alternating_colors(self, tree):
        for idx, item in enumerate(tree.get_children()):
            tree.item(item, tags=("row_even" if idx % 2 == 0 else "row_odd",))
     
    
    def autocompletion_personnel(self, event):
        typed = self.personnel_var.get().lower()
        if typed == "":
            data = self.nom_complets
        else:
            data = [nom for nom in self.nom_complets if typed in nom.lower()]

        # update values
        self.combobox_personnel['values'] = data
        self.combobox_personnel.event_generate('<Down>')  # show dropdown list

    def generate_observation(self, nom, prenom):
        today = date.today().strftime("%d/%m/%Y")
        return f"AVS - {nom.upper()} {prenom.capitalize()} - {today}"

    def creer_widgets(self):
        # Section Champs de Saisie en Haut
        input_frame = ctk.CTkFrame(self)
        input_frame.pack(pady=10, padx=10, fill="x")

        # Combobox pour les personnel
        ctk.CTkLabel(input_frame, text="Personnel :").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.personnel_var = tk.StringVar()
        self.nom_complets = [p["nom_complet"] for p in self.personnel]
        
        # Use ttk.Combobox
        self.combobox_personnel = ttk.Combobox(input_frame, textvariable=self.personnel_var, values=self.nom_complets, state="normal")
        self.combobox_personnel.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        self.combobox_personnel.bind("<KeyRelease>", self.autocompletion_personnel)

        # Champ de saisie mtpaye
        ctk.CTkLabel(input_frame, text="Montant à Payer :").grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.mtpaye_var = tk.StringVar()
        ctk.CTkEntry(input_frame, textvariable=self.mtpaye_var).grid(row=0, column=3, padx=5, pady=2, sticky="ew")

        # Champ de saisie nombre de remboursement
        ctk.CTkLabel(input_frame, text="Nb Remboursement :").grid(row=0, column=4, padx=5, pady=2, sticky="w")
        self.nbremboursement_var = tk.StringVar()
        ctk.CTkEntry(input_frame, textvariable=self.nbremboursement_var).grid(row=0, column=5, padx=5, pady=2, sticky="ew")

        # Frame for Treeview to better manage its packing
        tree_container_frame = ctk.CTkFrame(self, fg_color="transparent")
        tree_container_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Treeview des avances spéciales (still ttk.Treeview)
        self.tree = ttk.Treeview(tree_container_frame, columns=("Date", "Référence", "Observation", "Montant", "Nb Remboursement", "Paiement par Mois"), show="headings")
        self._configure_table_alternating_colors(self.tree)
        for col in ("Date", "Référence", "Observation", "Montant", "Nb Remboursement", "Paiement par Mois"):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)

        # Configuration des scrolls (still ttk.Scrollbar)
        vsb = ttk.Scrollbar(tree_container_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side='right', fill='y')
        hsb.pack(side='bottom', fill='x')

        # Section des boutons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=10)

        ctk.CTkButton(btn_frame, text="Enregistrer", fg_color="#2ecc71", 
        hover_color="#27ae60", command=self.enregistrer_avance).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Modifier", command=self.modifier_avance).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Annuler", fg_color="#e74c3c",
        hover_color="#c0392b", command=self.annuler_saisie).pack(side="left", padx=5)
        
        # Add Export Buttons
        ctk.CTkButton(btn_frame, text="Exporter Excel", command=self.exporter_excel).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Exporter PDF", command=self.exporter_pdf).pack(side="left", padx=5)

        # Configuration du poids des colonnes pour l'étirement
        input_frame.columnconfigure(1, weight=1)
        input_frame.columnconfigure(3, weight=1)
        input_frame.columnconfigure(5, weight=1)

    def charger_avances(self):
        # Clear existing content
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._refresh_table_alternating_colors(self.tree)

        self.cursor.execute("""
            SELECT tap.datepmt, tap.refpmt, tap.observation, tap.mtpaye, tap.nbremboursement, p.nom, p.prenom
            FROM tb_avancespecpers tap
            JOIN tb_personnel p ON tap.idpers = p.id
            ORDER BY tap.datepmt DESC
        """)
        resultats = self.cursor.fetchall()

        for ligne in resultats:
            datepmt = ligne[0] if ligne[0] else datetime.now()
            reference = ligne[1]
            observation = ligne[2]
            montant = ligne[3]
            nb_remboursement = ligne[4]
            nom_prof = ligne[5]
            prenom_prof = ligne[6]
            
            paiement_par_mois = montant / nb_remboursement if nb_remboursement else 0
            
            # Format the observation to include professor name if it's generic
            if "AVS -" in observation and not f"{nom_prof.upper()} {prenom_prof.capitalize()}" in observation:
                observation = self.generate_observation(nom_prof, prenom_prof)

            self.tree.insert("", "end", values=(
                datepmt.strftime("%Y-%m-%d %H:%M:%S"),
                reference,
                observation,
                f"{montant:,.2f}".replace(',', ' ').replace('.', ','),
                nb_remboursement,
                f"{paiement_par_mois:,.2f}".replace(',', ' ').replace('.', ',')
            ))
        self._refresh_table_alternating_colors(self.tree)

    def enregistrer_avance(self):
        personnel_selectionne = self.personnel_var.get()
        montant = self.mtpaye_var.get().strip()
        nb_remboursement = self.nbremboursement_var.get().strip()

        if not personnel_selectionne:
            messagebox.showerror("Erreur", "Veuillez sélectionner un personnel.")
            return
        if not montant:
            messagebox.showerror("Erreur", "Veuillez saisir le montant à payer.")
            return
        if not nb_remboursement:
            messagebox.showerror("Erreur", "Veuillez saisir le nombre de remboursements.")
            return

        # Vérifier que iduser est défini
        if not self.iduser:
            messagebox.showerror("Erreur", "L'utilisateur n'est pas connecté. Veuillez vous reconnecter.")
            print("ERREUR: iduser est None lors de l'enregistrement!")
            return

        try:
            montant_val = float(montant.replace(',', '.'))
            nb_remboursement_val = int(nb_remboursement)
            
            if montant_val <= 0 or nb_remboursement_val <= 0:
                messagebox.showerror("Erreur", "Le montant et le nombre de remboursements doivent être supérieurs à zéro.")
                return

            personnel_id = self.prof_ids.get(personnel_selectionne)
            if not personnel_id:
                messagebox.showerror("Erreur", "ID du personnel non trouvé. Veuillez sélectionner un personnel valide de la liste.")
                return

            reference = self.generer_reference()
            # Retrieve professor name and first name for observation
            pers_info = next((p for p in self.personnel if p["id"] == personnel_id), None)
            observation = self.generate_observation(pers_info["nom"], pers_info["prenom"])
            date_actuelle = datetime.now()

            print(f"Enregistrement avec iduser: {self.iduser}")  # Debug

            self.cursor.execute("""
                INSERT INTO tb_avancespecpers (refpmt, observation, idpers, mtpaye, nbremboursement, datepmt, idtypeoperation, iduser)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (reference, observation, personnel_id, montant_val, nb_remboursement_val, date_actuelle, 2, self.iduser))

            self.conn.commit()

            messagebox.showinfo("Succès", "Avance enregistrée.")
            self.charger_avances()
            self.annuler_saisie()

        except ValueError:
            messagebox.showerror("Erreur", "Veuillez saisir des valeurs numériques valides pour le montant et le nombre de remboursements.")
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement : {e}")

    def modifier_avance(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showerror("Erreur", "Veuillez sélectionner une avance à modifier.")
            return

        # Get the reference from the selected item
        current_values = self.tree.item(selected_item)['values']
        reference_to_modify = current_values[1]  # Reference is at index 1

        # Fetch the full data for the selected advance from the DB
        self.cursor.execute("""
            SELECT id, observation, idpers, mtpaye, nbremboursement
            FROM tb_avancespecpers
            WHERE refpmt = %s
        """, (reference_to_modify,))
        advance_data = self.cursor.fetchone()

        if not advance_data:
            messagebox.showerror("Erreur", "Détails de l'avance non trouvés.")
            return

        avance_id, current_observation, current_idprof, current_mtpaye, current_nbremboursement = advance_data

        # Create a Toplevel window for editing
        edit_window = ctk.CTkToplevel(self.master)
        edit_window.title("Modifier Avance Spéciale")
        edit_window.geometry("450x250")

        # Get professor's full name
        prof_info = next((p for p in self.personnel if p["id"] == current_idprof), None)
        prof_full_name = prof_info["nom_complet"] if prof_info else "Inconnu"

        ctk.CTkLabel(edit_window, text=f"Personnel: {prof_full_name}").grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(edit_window, text="Nouveau Montant:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        new_mtpaye_var = ctk.CTkEntry(edit_window)
        new_mtpaye_var.insert(0, str(current_mtpaye))
        new_mtpaye_var.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(edit_window, text="Nouveau Nb Remboursement:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        new_nbremboursement_var = ctk.CTkEntry(edit_window)
        new_nbremboursement_var.insert(0, str(current_nbremboursement))
        new_nbremboursement_var.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(edit_window, text="Nouvelle Observation:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        new_observation_var = ctk.CTkEntry(edit_window)
        new_observation_var.insert(0, current_observation)
        new_observation_var.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

        def save_changes():
            try:
                new_montant = float(new_mtpaye_var.get().replace(',', '.'))
                new_nbrem = int(new_nbremboursement_var.get())
                new_obs = new_observation_var.get()

                if new_montant <= 0 or new_nbrem <= 0:
                    messagebox.showerror("Erreur", "Le montant et le nombre de remboursements doivent être supérieurs à zéro.")
                    return

                self.cursor.execute("""
                    UPDATE tb_avancespecpers
                    SET mtpaye = %s, nbremboursement = %s, observation = %s
                    WHERE id = %s
                """, (new_montant, new_nbrem, new_obs, avance_id))
                self.conn.commit()
                messagebox.showinfo("Succès", "Avance modifiée avec succès.")
                edit_window.destroy()
                self.charger_avances()  # Refresh the treeview
            except ValueError:
                messagebox.showerror("Erreur", "Veuillez saisir des valeurs numériques valides.")
            except Exception as e:
                self.conn.rollback()
                messagebox.showerror("Erreur", f"Erreur lors de la modification : {e}")

        ctk.CTkButton(edit_window, text="Enregistrer les modifications", command=save_changes).grid(row=4, column=0, columnspan=2, pady=15)
        edit_window.grab_set()  # Make the Toplevel modal

    def annuler_saisie(self):
        self.personnel_var.set("")
        self.mtpaye_var.set("")
        self.nbremboursement_var.set("")

    def generer_reference(self):
        return datetime.now().strftime("AVS-%Y%m%d-%H%M%S-%f")[:22]
    
    def exporter_excel(self):
        try:
            self.cursor.execute("""
                SELECT p.nom, p.prenom, tap.refpmt, tap.mtpaye, tap.nbremboursement, tap.datepmt, tap.observation
                FROM tb_avancespecpers tap
                JOIN tb_personnel p ON p.id = tap.idpers
                ORDER BY tap.datepmt ASC
            """)
            results = self.cursor.fetchall()
            df = pd.DataFrame(results, columns=["Nom Personnel", "Prénom Personnel", "Référence", "Montant Payé", "Nb Remboursement", "Date Paiement", "Observation"])
            
            # Calculate "Paiement par Mois"
            df["Paiement par Mois"] = df["Montant Payé"] / df["Nb Remboursement"]

            df.to_excel("avances_speciales_personnel.xlsx", index=False)
            messagebox.showinfo("Exportation", "Exportation Excel réussie !")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'exportation Excel : {e}")

    def exporter_pdf(self):
        try:
            self.cursor.execute("""
                SELECT p.nom, p.prenom, tap.refpmt, tap.mtpaye, tap.nbremboursement, tap.datepmt, tap.observation
                FROM tb_avancespecpers tap
                JOIN tb_personnel p ON p.id = tap.idpers
                ORDER BY tap.datepmt ASC
            """)
            data = self.cursor.fetchall()

            if not data:
                messagebox.showinfo("Info", "Aucune avance spéciale à exporter.")
                return

            pdf = canvas.Canvas("avances_speciales_personnel.pdf", pagesize=letter)
            pdf.setFont("Helvetica", 10)
            
            y_position = 750
            page_width, page_height = letter

            pdf.drawString(50, y_position, "Liste des Avances Spéciales des Personnel")
            y_position -= 20

            # Headers
            headers = ["Date", "Réf.", "Personnel", "Montant", "Nb Remb.", "Pmt/Mois", "Observation"]
            col_widths = [80, 70, 100, 60, 60, 60, 120]

            # Draw headers
            x_start = 50
            for i, header in enumerate(headers):
                pdf.drawString(x_start + sum(col_widths[:i]), y_position, header)
            y_position -= 15

            # Draw a line under headers
            pdf.line(50, y_position, page_width - 50, y_position)
            y_position -= 15

            for nom_prof, prenom_prof, reference, montant, nb_remboursement, date_pmt, observation in data:
                if y_position < 50:  # Check if new page is needed
                    pdf.showPage()
                    pdf.setFont("Helvetica", 10)
                    y_position = 750
                    pdf.drawString(50, y_position, "Liste des Avances Spéciales des personnels (suite)")
                    y_position -= 20
                    for i, header in enumerate(headers):
                        pdf.drawString(x_start + sum(col_widths[:i]), y_position, header)
                    y_position -= 15
                    pdf.line(50, y_position, page_width - 50, y_position)
                    y_position -= 15

                # Calculate "Paiement par Mois"
                paiement_par_mois = montant / nb_remboursement if nb_remboursement else 0

                # Format data for PDF
                display_date = date_pmt.strftime("%Y-%m-%d")
                display_prof = f"{nom_prof} {prenom_prof}"
                display_montant = f"{montant:,.2f}".replace(',', ' ').replace('.', ',')
                display_nbremb = str(nb_remboursement)
                display_pmt_mois = f"{paiement_par_mois:,.2f}".replace(',', ' ').replace('.', ',')
                display_obs = observation

                row_data = [
                    display_date,
                    reference,
                    display_prof,
                    display_montant,
                    display_nbremb,
                    display_pmt_mois,
                    display_obs
                ]

                # Draw row data
                for i, item in enumerate(row_data):
                    pdf.drawString(x_start + sum(col_widths[:i]), y_position, str(item))
                y_position -= 15

            pdf.save()
            messagebox.showinfo("Exportation", "Exportation PDF réussie !")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'exportation PDF : {e}")

    def __del__(self):
        """Ferme proprement la connexion à la base de données lors de la destruction de l'objet."""
        if hasattr(self, 'cursor') and self.cursor:
            self.cursor.close()
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()


# ---
if __name__ == "__main__":
    ctk.set_appearance_mode("Light")  # Modes: "System" (default), "Dark", "Light"
    ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"

    app = ctk.CTk()
    app.title("Avance Spéciale des Personnels")
    app.geometry("1000x700")

    # Pour tester: utiliser un iduser fictif
    fenetre_avance_spec = FenetreAvanceSpec(master=app, iduser=1)
    fenetre_avance_spec.pack(fill="both", expand=True)

    app.mainloop()
