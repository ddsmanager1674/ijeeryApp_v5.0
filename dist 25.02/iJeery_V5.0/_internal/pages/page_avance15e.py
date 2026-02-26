import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime, date
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os
import json
import sys
from resource_utils import get_config_path, safe_file_read


# Ensure the parent directory is in the Python path for absolute imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

def generer_reference():
    now = datetime.now()
    return now.strftime("AVQ-%Y%m%d%H%M%S%f")[:-3]

def generate_observation(nom_prof, prenom_prof):
    today = date.today().strftime("%d%m%Y")
    return f"AVQ - {nom_prof.upper()} {prenom_prof.capitalize()} - {today}"

class PageAVQ(ctk.CTkFrame):
    def __init__(self, master=None, iduser=None):
        super().__init__(master)
        self.master = master
        self.id_prof_selectionne = None
        self.iduser = iduser

        # Afficher l'iduser pour le débogage
        if self.iduser:
            print(f"FenetreAvance initialisée avec iduser: {self.iduser}")
        else:
            print("ATTENTION: FenetreAvanceSpec initialisée sans iduser!")
        
        # Connexion à la base de données
        self.conn = self.connect_db()
        self.cursor = None
        
        if self.conn:
            self.cursor = self.conn.cursor()
            self.initialize_database()
        
        self.create_widgets()
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

    def _configure_table_alternating_colors(self, tree):
        tree.tag_configure("row_even", background="#FFFFFF")
        tree.tag_configure("row_odd", background="#D9EEED")

    def _refresh_table_alternating_colors(self, tree):
        for idx, item in enumerate(tree.get_children()):
            tree.item(item, tags=("row_even" if idx % 2 == 0 else "row_odd",))

    def initialize_database(self):
        """Initialise la connexion à la base de données et crée la table si nécessaire."""
        if not self.cursor:
            return False
        
        try:
            # Création de la table si elle n'existe pas
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS tb_avanceprof (
                    id SERIAL PRIMARY KEY,
                    refpmt VARCHAR(50),
                    idpers INT REFERENCES tb_personnel(id),
                    mtpaye DOUBLE PRECISION,
                    observation VARCHAR(120),
                    datepmt TIMESTAMP,
                    etat INT,
                    idtypeoperation INT,
                    iduser INT
                )
            """)
            self.conn.commit()
            return True
            
        except psycopg2.Error as err:
            messagebox.showerror("Erreur de connexion", f"Erreur : {err}")
            return False

    def charger_personnel_pour_avance(self, filtre=""):
        """Charge la liste du personnel pour les avances"""
        try:
            if self.cursor:
                self.cursor.execute("SELECT id, nom, prenom FROM tb_personnel ORDER BY nom")
                personnel = self.cursor.fetchall()
                liste_personnel = []
                for id_prof, nom, prenom in personnel:
                    if filtre.lower() in nom.lower() or filtre.lower() in prenom.lower():
                        liste_personnel.append(f"{nom} {prenom} (ID: {id_prof})")
                return liste_personnel
        except Exception as e:
            print(f"Erreur lors du chargement des professeurs : {e}")
        return []

    def create_widgets(self):
        # Zone de saisie
        saisie_frame = ctk.CTkFrame(self, fg_color="transparent")
        saisie_frame.pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(saisie_frame, text="Rechercher Professeur:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # Use ttk.Combobox for direct value passing in command and better integration
        self.liste_personnel_combo = ttk.Combobox(saisie_frame, values=self.charger_personnel_pour_avance(), width=40)
        self.liste_personnel_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.liste_personnel_combo.bind("<<ComboboxSelected>>", self.selectionner_personnel_event)

        ctk.CTkLabel(saisie_frame, text="Montant Payé:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.montant_entry = ctk.CTkEntry(saisie_frame, width=150)
        self.montant_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        ctk.CTkButton(saisie_frame, text="Enregistrer", fg_color="#2ecc71", 
        hover_color="#27ae60", command=self.enregistrer_avance).grid(row=2, column=0, columnspan=2, pady=10)

        # Configuration du grid pour permettre l'expansion
        saisie_frame.grid_columnconfigure(1, weight=1)

        # Treeview for displaying advances
        tree_frame = ctk.CTkFrame(self, fg_color="transparent")
        tree_frame.pack(pady=10, padx=10, fill="both", expand=True)

        # Use ttk.Treeview as CTkTreeview doesn't exist
        self.treeview = ttk.Treeview(tree_frame, columns=("Date", "Référence", "Observation", "Montant", "ID", "Personnel"), show="headings")
        self.treeview.heading("Date", text="Date", anchor="w")
        self.treeview.heading("Référence", text="Référence", anchor="w")
        self.treeview.heading("Observation", text="Observation", anchor="w")
        self.treeview.heading("Montant", text="Montant", anchor="e")
        self.treeview.heading("ID", text="ID", anchor="w")
        self.treeview.heading("Personnel", text="Personnel", anchor="w")

        self.treeview.column("Date", width=150)
        self.treeview.column("Référence", width=120)
        self.treeview.column("Observation", width=200)
        self.treeview.column("Montant", width=80, anchor="e")
        self.treeview.column("ID", width=0, stretch=tk.NO) # Hide ID column
        self.treeview.column("Personnel", width=150)
        self._configure_table_alternating_colors(self.treeview)

        self.treeview.pack(fill="both", expand=True)

        # Frame pour les boutons
        buttons_frame = ctk.CTkFrame(tree_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", pady=(5, 0))

        # Buttons for Modify and Cancel
        ctk.CTkButton(buttons_frame, text="Modifier", command=self.modifier_avance).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(buttons_frame, text="Annuler", fg_color="#e74c3c",
        hover_color="#c0392b", command=self.annuler_avance).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(buttons_frame, text="Exporter Excel", command=self.exporter_excel).pack(side="right", padx=5, pady=5)
        ctk.CTkButton(buttons_frame, text="Exporter PDF", command=self.exporter_pdf).pack(side="right", padx=5, pady=5)

    def selectionner_personnel_event(self, event):
        # This method is called by the ttk.Combobox event binding
        selection = self.liste_personnel_combo.get()
        self.selectionner_personnel(selection)

    def selectionner_personnel(self, selection):
        self.id_prof_selectionne = None
        if selection:
            try:
                self.id_prof_selectionne = int(selection.split('(ID: ')[1][:-1])
            except (IndexError, ValueError):
                messagebox.showerror("Erreur", "Format de personnel invalide.")

    def enregistrer_avance(self):
        if self.id_prof_selectionne is None:
            messagebox.showerror("Erreur", "Veuillez sélectionner un personnel.")
            return

        montant_str = self.montant_entry.get().replace(" ", "").replace(",", ".")
        try:
            montant_paye = float(montant_str)
            if montant_paye <= 0:
                messagebox.showerror("Erreur", "Le montant de l'avance doit être supérieur à zéro.")
                return
        except ValueError:
            messagebox.showerror("Erreur", "Montant invalide.")
            return

        # Vérifier que iduser est défini
        if not self.iduser:
            messagebox.showerror("Erreur", "L'utilisateur n'est pas connecté. Veuillez vous reconnecter.")
            print("ERREUR: iduser est None lors de l'enregistrement!")
            return

        try:
            if not self.conn or not self.cursor:
                messagebox.showerror("Erreur de connexion", "Impossible de se connecter à la base de données.")
                return

            self.cursor.execute("SELECT nom, prenom FROM tb_personnel WHERE id = %s", (self.id_prof_selectionne,))
            personnel = self.cursor.fetchone()
            if not personnel:
                messagebox.showerror("Erreur", "Personnel non trouvé.")
                return

            observation = generate_observation(personnel[0], personnel[1])
            reference = generer_reference()
            date_paiement = datetime.now()
            type_operation = "2"

            self.cursor.execute("""
                INSERT INTO tb_avancepers (refpmt, idpers, mtpaye, observation, datepmt, idtypeoperation, iduser)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (reference, self.id_prof_selectionne, montant_paye, observation, date_paiement, type_operation, self.iduser))
            self.conn.commit()
            messagebox.showinfo("Succès", "Avance enregistrée avec succès !")
            self.rafraichir_treeview()
            self.montant_entry.delete(0, ctk.END)
            self.liste_personnel_combo.set("")
            self.id_prof_selectionne = None
        except psycopg2.Error as e:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement : {e}")

    def modifier_avance(self):
        selection = self.treeview.selection()
        if not selection:
            messagebox.showerror("Erreur", "Veuillez sélectionner une avance à modifier.")
            return

        avance_id = self.treeview.item(selection[0])['values'][4]

        try:
            if not self.conn or not self.cursor:
                messagebox.showerror("Erreur de connexion", "Impossible de se connecter à la base de données.")
                return

            self.cursor.execute("SELECT idpers, mtpaye, observation FROM tb_avancepers WHERE id = %s", (avance_id,))
            avance_actuelle = self.cursor.fetchone()
            if not avance_actuelle:
                messagebox.showerror("Erreur", "Impossible de récupérer les détails de l'avance.")
                return

            fenetre_modification = ctk.CTkToplevel(self)
            fenetre_modification.title("Modifier l'avance")
            fenetre_modification.geometry("400x200")

            self.cursor.execute("SELECT nom, prenom FROM tb_personnel WHERE id = %s", (avance_actuelle[0],))
            personnel = self.cursor.fetchone()
            nom_professeur = f"{personnel[0]} {personnel[1]}" if personnel else "Inconnu"

            ctk.CTkLabel(fenetre_modification, text="Personnel:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            ctk.CTkLabel(fenetre_modification, text=nom_professeur).grid(row=0, column=1, padx=5, pady=5, sticky="w")

            ctk.CTkLabel(fenetre_modification, text="Nouveau Montant:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
            nouveau_montant_entry = ctk.CTkEntry(fenetre_modification)
            nouveau_montant_entry.insert(0, str(avance_actuelle[1]))
            nouveau_montant_entry.grid(row=1, column=1, padx=5, pady=5)

            ctk.CTkLabel(fenetre_modification, text="Nouvelle Observation:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
            nouvelle_observation_entry = ctk.CTkEntry(fenetre_modification)
            nouvelle_observation_entry.insert(0, avance_actuelle[2])
            nouvelle_observation_entry.grid(row=2, column=1, padx=5, pady=5)

            def valider_modification():
                nouveau_montant_str = nouveau_montant_entry.get().replace(" ", "").replace(",", ".")
                try:
                    nouveau_montant = float(nouveau_montant_str)
                    if nouveau_montant <= 0:
                        messagebox.showerror("Erreur", "Le montant doit être supérieur à zéro.")
                        return
                except ValueError:
                    messagebox.showerror("Erreur", "Montant invalide.")
                    return

                nouvelle_observation = nouvelle_observation_entry.get()

                try:
                    self.cursor.execute("""
                        UPDATE tb_avancepers
                        SET mtpaye = %s, observation = %s
                        WHERE id = %s
                    """, (nouveau_montant, nouvelle_observation, avance_id))
                    self.conn.commit()
                    messagebox.showinfo("Succès", "Avance modifiée avec succès !")
                    self.rafraichir_treeview()
                    fenetre_modification.destroy()
                except psycopg2.Error as e:
                    self.conn.rollback()
                    messagebox.showerror("Erreur", f"Erreur lors de la modification : {e}")

            ctk.CTkButton(fenetre_modification, text="Enregistrer les modifications", 
                         command=valider_modification).grid(row=3, column=0, columnspan=2, pady=10)
                         
        except psycopg2.Error as e:
            messagebox.showerror("Erreur", f"Erreur lors de la récupération des données : {e}")

    def annuler_avance(self):
        selection = self.treeview.selection()
        if not selection:
            messagebox.showerror("Erreur", "Veuillez sélectionner une avance à annuler.")
            return

        avance_id = self.treeview.item(selection[0])['values'][4]

        if messagebox.askyesno("Confirmation", "Êtes-vous sûr de vouloir annuler cette avance ?"):
            try:
                if not self.conn or not self.cursor:
                    messagebox.showerror("Erreur de connexion", "Impossible de se connecter à la base de données.")
                    return
                self.cursor.execute("DELETE FROM tb_avancepers WHERE id = %s", (avance_id,))
                self.conn.commit()
                messagebox.showinfo("Succès", "Avance annulée avec succès !")
                self.rafraichir_treeview()
            except psycopg2.Error as e:
                self.conn.rollback()
                messagebox.showerror("Erreur", f"Erreur lors de l'annulation : {e}")

    def rafraichir_treeview(self):
        for item in self.treeview.get_children():
            self.treeview.delete(item)
        self._refresh_table_alternating_colors(self.treeview)
        self.charger_avances()

    def charger_avances(self):
        try:
            if not self.cursor:
                return

            self.cursor.execute("""
                SELECT a.datepmt, a.refpmt, a.observation, a.mtpaye, a.id, p.nom, p.prenom
                FROM tb_avancepers a
                JOIN tb_personnel p ON a.idpers = p.id
                WHERE a.mtpaye > 0
                ORDER BY a.datepmt DESC
            """)
            avances = self.cursor.fetchall()
            for date_pmt, reference, observation, montant, id_avance, nom_prof, prenom_prof in avances:
                self.treeview.insert("", "end", values=(
                    date_pmt.strftime("%Y-%m-%d %H:%M:%S"), 
                    reference, 
                    observation, 
                    f"{montant:.2f}", 
                    id_avance, 
                    f"{nom_prof} {prenom_prof}"
                ))
            self._refresh_table_alternating_colors(self.treeview)
        except psycopg2.Error as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des avances : {e}")

    def exporter_excel(self):
        try:
            if not self.cursor:
                return
            self.cursor.execute("""
                SELECT p.nom, p.prenom, a.refpmt, a.mtpaye, a.datepmt, a.observation
                FROM tb_avancepers a
                JOIN tb_personnel p ON p.id = a.idpers
                WHERE a.mtpaye > 0
                ORDER BY a.datepmt ASC
            """)
            results = self.cursor.fetchall()
            if not results:
                messagebox.showinfo("Info", "Aucune donnée à exporter.")
                return
                
            df = pd.DataFrame(results, columns=["Nom", "Prénom", "Référence", "Montant", "Date", "Observation"])
            df.to_excel("avances_personnel.xlsx", index=False)
            messagebox.showinfo("Exportation", "Exportation Excel réussie !")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'exportation Excel : {e}")

    def exporter_pdf(self):
        try:
            if not self.cursor:
                return
            self.cursor.execute("""
                SELECT p.nom, p.prenom, a.refpmt, a.mtpaye, a.datepmt, a.observation
                FROM tb_avancepers a
                JOIN tb_personnel p ON p.id = a.idpers
                WHERE a.mtpaye > 0
                ORDER BY a.datepmt ASC
            """)
            data = self.cursor.fetchall()

            if not data:
                messagebox.showinfo("Info", "Aucune avance à exporter.")
                return

            pdf = canvas.Canvas("avances_personnel.pdf", pagesize=letter)
            pdf.setFont("Helvetica", 10)
            pdf.drawString(50, 750, "Liste des Avances des Personnel")
            y = 730
            for nom, prenom, reference, montant, date_pmt, observation in data:
                line = f"{date_pmt.strftime('%Y-%m-%d %H:%M:%S')} | Réf: {reference} | Prof: {nom} {prenom} | Montant: {montant:.2f} | Obs: {observation}"
                pdf.drawString(50, y, line)
                y -= 15
                if y < 50:
                    pdf.showPage()
                    pdf.setFont("Helvetica", 10)
                    y = 750
            pdf.save()
            messagebox.showinfo("Exportation", "Exportation PDF réussie !")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'exportation PDF : {e}")

    def __del__(self):
        """Destructeur pour fermer proprement les connexions"""
        if hasattr(self, 'cursor') and self.cursor:
            self.cursor.close()
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

def main():
    ctk.set_appearance_mode("Light")  # Modes: "System" (default), "Dark", "Light"
    ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"

    app = ctk.CTk()
    app.title("Gestion des Avances 15e Personnel")
    app.geometry("800x600")

    # Pour tester: utiliser un iduser fictif
    page_avq = PageAVQ(master=app, iduser=1)
    page_avq.pack(fill="both", expand=True)

    page_avq = PageAVQ(master=app)
    page_avq.pack(fill="both", expand=True)

    app.mainloop()

if __name__ == "__main__":
    main()
