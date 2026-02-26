import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
import customtkinter as ctk
from datetime import date
from datetime import datetime
import pandas as pd
from tkinter import filedialog
import subprocess
import os # Import the os module
import json


from pages.page_listeParSerie import PageListeParSerie
from pages.page_affectation import PageAffectation # Import PageAffectation

class DatabaseManager:
    def __init__(self):
        self.db_params = self._load_db_config()

    def _load_db_config(self):
        """Loads database configuration from 'config.json'."""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
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
    
    def get_connection(self):
        """Establishes a new database connection."""
        if self.db_params is None:
            print("Cannot connect: Database configuration is missing.")
            return None
        
        try:
            conn = psycopg2.connect(
                host=self.db_params['host'],
                user=self.db_params['user'],
                password=self.db_params['password'],
                database=self.db_params['database'],
                port=self.db_params['port']
            )
            print("Connection to the database successful!")
            return conn
        except psycopg2.OperationalError as e:
            print(f"Error connecting to the database: {e}")
            return None

class PageClasse(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.db_manager = DatabaseManager()
        self.conn = None
        self.cursor = None

        if self.connect_db():
            self._create_interface()
            self.create_widgets()
            self.create_widgets1()
            self.create_widgets_salle()
            self.afficher_series()
            self.load_last_anneescolaire()
            self.afficher_classes()
            self.afficher_vue_salles()
            self.get_professeurs()
            self.mettre_a_jour_niveaux_disponibles()
            self.get_classes()
            self.get_classe_utilises()
            self.populate_professeur_combobox()
            self.populate_serie_combobox()
            self.populate_classe_combobox()
            self.pack(expand=True, fill="both")

            # Lier le double-clic sur le tree_salle
            self.tree_salle.bind("<Double-1>", self.on_salle_double_click)


    def connect_db(self):
        try:
            self.conn = self.db_manager.get_connection()
            if self.conn:
                self.cursor = self.conn.cursor()
                return True
            else:
                messagebox.showerror("Erreur de connexion", "Impossible de se connecter à la base de données. Veuillez vérifier la configuration.")
                return False
        except psycopg2.Error as e:
            messagebox.showerror("Erreur de connexion", f"Impossible de se connecter à la base de données : {e}")
            return False



    def _create_interface(self):
        # Configuration des lignes et colonnes
        self.configure(fg_color="transparent")
        self.grid_rowconfigure(0, weight=0) # Titre
        self.grid_rowconfigure(1, weight=1) # frame_haut
        self.grid_rowconfigure(2, weight=1) # frame_bas
        self.grid_columnconfigure(0, weight=1)

        # -------- Frame haut (Classes et Séries) -------- #

        self.frame_haut = ctk.CTkFrame(self)
        self.frame_haut.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.frame_haut.grid_columnconfigure(0, weight=1)
        self.frame_haut.grid_columnconfigure(1, weight=1)
        self.frame_haut.grid_rowconfigure(0, weight=1)

        # Frame haut gauche (Classes)

        self.frame_haut_gauche = ctk.CTkFrame(self.frame_haut)
        self.frame_haut_gauche.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.frame_haut_gauche.grid_rowconfigure(4, weight=1)
        self.create_widgets() # Widgets pour classes

        # Frame haut droite (Séries)

        self.frame_haut_droite = ctk.CTkFrame(self.frame_haut)
        self.frame_haut_droite.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.frame_haut_droite.grid_rowconfigure(4, weight=1)
        self.create_widgets1() # Widgets pour séries
        self.relocate_widgets1()


        # -------- Frame bas (Salles) -------- #

        self.frame_bas = ctk.CTkFrame(self)
        self.frame_bas.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        self.frame_bas.grid_columnconfigure(0, weight=1)
        self.frame_bas.grid_rowconfigure(4, weight=1)

    def create_widgets(self):

        # Champ désignation

        self.label_designation = ctk.CTkLabel(self.frame_haut_gauche, text="Désignation de la classe:")
        self.entry_designation_classe = tk.Entry(self.frame_haut_gauche, width=15)

        # Champ niveau

        self.label_niveau = ctk.CTkLabel(self.frame_haut_gauche, text="Niveau:")
        self.combo_niveau = ttk.Combobox(self.frame_haut_gauche, width= 5, state="readonly")

        # Boutons d'action pour la classe

        self.btn_frame_classe = ctk.CTkFrame(self.frame_haut_gauche)
        self.btn_ajouter = ctk.CTkButton(self.btn_frame_classe, text="Ajouter Classe", command=self.ajouter_classe, fg_color="#2ecc71", hover_color="#27ae60", text_color="white")
        self.btn_modifier = ctk.CTkButton(self.btn_frame_classe, text="Modifier Classe", command=self.modifier_classe, fg_color="#3498db", hover_color="#2980b9", text_color="white")
        self.btn_supprimer = ctk.CTkButton(self.btn_frame_classe, text="Supprimer Classe", command=self.supprimer_classe, fg_color="#e74c3c", hover_color="#c0392b", text_color="white")


        # Table Treeview pour afficher les classes

        self.tree_classe = ttk.Treeview(self.frame_haut_gauche, columns=("ID", "Désignation", "Niveau"), show="headings")
        self.tree_classe.heading("ID", text="ID")
        self.tree_classe.heading("Désignation", text="Désignation")
        self.tree_classe.heading("Niveau", text="Niveau")

        self.relocate_widgets()


    def relocate_widgets(self):

        # Retirer les widgets de frame_haut_droite
        self.label_designation.grid_forget()
        self.entry_designation_classe.grid_forget()
        self.label_niveau.grid_forget()
        self.combo_niveau.grid_forget()
        self.btn_frame_classe.pack_forget()
        self.tree_classe.grid_forget()

        # Placer les widgets dans frame_haut_gauche
        self.label_designation.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.entry_designation_classe.grid(row=0, column=1, padx=5, pady=5)
        self.label_niveau.grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.combo_niveau.grid(row=1, column=1, padx=5, pady=5)
        self.btn_frame_classe.grid(row=2, column=0, columnspan=2, pady=10)
        self.btn_ajouter.pack(side=tk.LEFT, padx=5)
        self.btn_modifier.pack(side=tk.LEFT, padx=5)
        self.btn_supprimer.pack(side=tk.LEFT, padx=5)
        self.tree_classe.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)


        # Configurer la grille de frame_haut_gauche pour l'étirement
        self.frame_haut_gauche.grid_columnconfigure(1, weight=1)
        self.frame_haut_gauche.grid_rowconfigure(3, weight=1)

    def load_last_anneescolaire(self):

        # Placeholder pour charger la dernière année scolaire (si nécessaire pour cette page)

        pass


    def get_niveaux_utilises(self):
        self.cursor.execute("SELECT niveau FROM tb_classe")
        return {row[0] for row in self.cursor.fetchall()}

    def ajouter_classe(self):
        designation = self.entry_designation_classe.get()
        niveau = self.combo_niveau.get()

        if designation.strip() == "" or niveau == "":
            messagebox.showwarning("Champ vide", "Veuillez remplir tous les champs.")
            return

        try:
            self.cursor.execute("INSERT INTO tb_classe (designation, niveau) VALUES (%s, %s)", (designation, niveau))
            self.conn.commit()
            self.entry_designation_classe.delete(0, tk.END)
            self.combo_niveau.set("")
            self.afficher_classes()
            self.mettre_a_jour_niveaux_disponibles()
        except psycopg2.IntegrityError:
            messagebox.showerror("Erreur", "Ce niveau est déjà utilisé.")
        except psycopg2.Error as err:
            messagebox.showerror("Erreur d'insertion", f"Erreur : {err}")

    def modifier_classe(self):
        selected_item = self.tree_classe.selection()
        if not selected_item:
            messagebox.showwarning("Aucune sélection", "Veuillez sélectionner une classe à modifier.")
            return

        classe_id = self.tree_classe.item(selected_item)['values'][0]
        new_designation = self.entry_designation_classe.get()
        new_niveau = self.combo_niveau.get()

        if new_designation.strip() == "" or new_niveau == "":
            messagebox.showwarning("Champ vide", "Veuillez remplir tous les champs.")
            return

        try:

            self.cursor.execute("UPDATE tb_classe SET designation = %s, niveau = %s WHERE id = %s", (new_designation, new_niveau, classe_id))
            self.conn.commit()
            self.entry_designation_classe.delete(0, tk.END)
            self.combo_niveau.set("")
            self.afficher_classes()
            self.mettre_a_jour_niveaux_disponibles()
        except psycopg2.IntegrityError:
            messagebox.showerror("Erreur", "Ce niveau est déjà utilisé.")
        except psycopg2.Error as err:
            messagebox.showerror("Erreur de mise à jour", f"Erreur : {err}")

    def supprimer_classe(self):
        selected_item = self.tree_classe.selection()
        if not selected_item:
            messagebox.showwarning("Aucune sélection", "Veuillez sélectionner une classe à supprimer.")
            return
        classe_id = self.tree_classe.item(selected_item)['values'][0]
        try:
            self.cursor.execute("DELETE FROM tb_classe WHERE id = %s", (classe_id,))
            self.conn.commit()
            self.afficher_classes()
            self.mettre_a_jour_niveaux_disponibles()
        except psycopg2.Error as err:
            messagebox.showerror("Erreur de suppression", f"Erreur : {err}")

    def afficher_classes(self):
        for row in self.tree_classe.get_children():
            self.tree_classe.delete(row)
        self.cursor.execute("SELECT * FROM tb_classe")
        for classe in self.cursor.fetchall():
            self.tree_classe.insert("", tk.END, values=classe)

    def mettre_a_jour_niveaux_disponibles(self):
        niveaux_utilises = self.get_niveaux_utilises()
        niveaux_disponibles = [str(i) for i in range(1, 26) if i not in niveaux_utilises]
        self.combo_niveau['values'] = niveaux_disponibles


    def get_classe_utilises(self):
        self.cursor.execute("SELECT id, designation FROM tb_classe")
        return self.cursor.fetchall()


    def ajouter_serie(self):
        designation = self.entry_designation_serie.get()
        classe = self.combo_classe.get()

        if not designation.strip() or not classe:
            messagebox.showwarning("Champ vide", "Veuillez remplir tous les champs.")
            return

        try:
            # Récupérer l'ID de la classe à partir de la désignation sélectionnée
            self.cursor.execute("SELECT id FROM tb_classe WHERE designation = %s", (classe,))
            resultat_classe = self.cursor.fetchone()
            if resultat_classe:
                idclasse = resultat_classe[0]
                self.cursor.execute("INSERT INTO tb_serie (designation, idclasse) VALUES (%s, %s)", (designation, idclasse))
                self.conn.commit()
                self.entry_designation_serie.delete(0, tk.END)
                self.combo_classe.set("")
                self.afficher_series()

            else:

                messagebox.showerror("Erreur", "La classe sélectionnée n'existe pas.")
        except psycopg2.IntegrityError:
            messagebox.showerror("Erreur", "Cette série existe déjà pour cette classe.")
        except psycopg2.Error as err:
            messagebox.showerror("Erreur d'insertion", f"Erreur : {err}")

    def afficher_series(self):
        for row in self.tree_serie.get_children():
            self.tree_serie.delete(row)

        query = """
        SELECT s.id, s.designation, c.designation
        FROM tb_serie s
        JOIN tb_classe c ON s.idclasse = c.id
        ORDER BY s.id
        """
        self.cursor.execute(query)
        for row in self.cursor.fetchall():
            self.tree_serie.insert("", "end", values=row)

    def modifier_serie(self):
        selected_item = self.tree_serie.selection()
        if not selected_item:
            messagebox.showwarning("Aucune sélection", "Veuillez sélectionner une série à modifier.")
            return


        serie_id = self.tree_serie.item(selected_item)['values'][0]
        new_designation = self.entry_designation_serie.get()
        new_classe = self.combo_classe.get()

        if new_designation.strip() == "" or new_classe == "":
            messagebox.showwarning("Champ vide", "Veuillez remplir tous les champs.")
            return

        try:

            # Récupérer l'ID de la classe à partir de la désignation sélectionnée
            self.cursor.execute("SELECT id FROM tb_classe WHERE designation = %s", (new_classe,))
            resultat_classe = self.cursor.fetchone()
            if resultat_classe:
                idclasse = resultat_classe[0]
                self.cursor.execute("UPDATE tb_serie SET designation = %s, idclasse = %s WHERE id = %s",
                        (new_designation, idclasse, serie_id))
                self.conn.commit()
                self.entry_designation_serie.delete(0, tk.END)
                self.combo_classe.set("")
                self.afficher_series()
            else:

                messagebox.showerror("Erreur", "La classe sélectionnée n'existe pas.")
        except psycopg2.IntegrityError:
            messagebox.showerror("Erreur", "Cette série existe déjà pour cette classe.")
        except psycopg2.Error as err:
            messagebox.showerror("Erreur de mise à jour", f"Erreur : {err}")

    def supprimer_serie(self):
        selected_item = self.tree_serie.selection()
        if not selected_item:
            messagebox.showwarning("Aucune sélection", "Veuillez sélectionner une série à supprimer.")
            return

        serie_id = self.tree_serie.item(selected_item)['values'][0]
        try:
            self.cursor.execute("DELETE FROM tb_serie WHERE id = %s", (serie_id,))
            self.conn.commit()
            self.afficher_series()
        except psycopg2.Error as err:
            messagebox.showerror("Erreur de suppression", f"Erreur : {err}")

    def populate_classe_combobox(self):
        classe_data = self.get_classe_utilises()
        display_names = []
        self.classe_dict = {}

        for id, designation in classe_data:
            display_names.append(designation)
            self.classe_dict[designation] = id

        self.combo_classe['values'] = display_names
        if display_names:
            self.combo_classe.set(display_names[0])
        else:
            self.combo_classe.set("")

    def create_widgets1(self):
        # Champ désignation série

        self.label_designation_serie = ctk.CTkLabel(self.frame_haut_droite, text="Désignation de la série:")
        self.entry_designation_serie = tk.Entry(self.frame_haut_droite, width=15)

        # ComboBox classe

        self.label_classe = ctk.CTkLabel(self.frame_haut_droite, text="Classe:")
        self.combo_classe = ttk.Combobox(self.frame_haut_droite, width=15, state="readonly")


        # Boutons d'action pour la serie

        self.btn_frame_serie = ctk.CTkFrame(self.frame_haut_droite)
        self.btn_ajouter_serie = ctk.CTkButton(self.btn_frame_serie, text="Ajouter Série", command=self.ajouter_serie, fg_color="#2ecc71", hover_color="#27ae60", text_color="white") # Added command
        self.btn_modifier_serie = ctk.CTkButton(self.btn_frame_serie, text="Modifier Série", command=self.modifier_serie, fg_color="#3498db", hover_color="#2980b9", text_color="white") # Added command
        self.btn_supprimer_serie = ctk.CTkButton(self.btn_frame_serie, text="Supprimer Série", command=self.supprimer_serie, fg_color="#e74c3c", hover_color="#c0392b", text_color="white") # Added command


        # Table Treeview pour afficher les séries
        self.tree_serie = ttk.Treeview(self.frame_haut_droite, columns=("ID", "Série", "Classe"), show="headings")
        self.tree_serie.heading("ID", text="ID")
        self.tree_serie.heading("Série", text="Série")
        self.tree_serie.heading("Classe", text="Classe")

        self.relocate_widgets1()


    def relocate_widgets1(self):
        # Placer les widgets dans frame_haut_droite
        self.label_designation_serie.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.entry_designation_serie.grid(row=0, column=1, padx=5, pady=5)
        self.label_classe.grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.combo_classe.grid(row=1, column=1, padx=5, pady=5)
        self.btn_frame_serie.grid(row=2, column=0, columnspan=2, pady=10)
        self.btn_ajouter_serie.pack(side=tk.LEFT, padx=5)
        self.btn_modifier_serie.pack(side=tk.LEFT, padx=5)
        self.btn_supprimer_serie.pack(side=tk.LEFT, padx=5)
        self.tree_serie.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)


        # Configurer la grille de frame_haut_droite pour l'étirement
        self.frame_haut_droite.grid_columnconfigure(1, weight=1)
        self.frame_haut_droite.grid_rowconfigure(3, weight=1)

    def get_classes(self):
        self.cursor.execute("SELECT id, designation FROM tb_classe")
        return {row[0] for row in self.cursor.fetchall()}


    def get_series(self):
        self.cursor.execute("SELECT id, designation FROM tb_serie")
        return self.cursor.fetchall()


    def get_professeurs(self):
        self.cursor.execute("SELECT id, nom, prenom FROM tb_professeur")
        return self.cursor.fetchall()

    def afficher_vue_salles(self):
        try:
            # Assurez-vous que l'ID de la salle est la première colonne
            self.cursor.execute("""
                SELECT
                    tb_salle.id,
                    tb_salle.designation AS salle,
                    tb_serie.designation AS serie,
                    tb_professeur.nom AS nomProfesseur,
                    tb_professeur.prenom AS prenomProfesseur,
                    tb_salle.nombreEtudiant AS nombreEtudiant,
                    tb_salle.idProfResponsable -- Récupérer l'ID du professeur responsable
                FROM
                    tb_salle
                INNER JOIN
                    tb_serie ON tb_salle.idSerie = tb_serie.id
                INNER JOIN
                    tb_professeur ON tb_salle.idProfResponsable = tb_professeur.id;
            """)

            rows = self.cursor.fetchall()
            for row in self.tree_salle.get_children():
                self.tree_salle.delete(row)
            for row in rows:
                self.tree_salle.insert("", tk.END, values=row)
        except psycopg2.Error as err:
            messagebox.showerror("Erreur SQL", f"Erreur : {err}")

    def vider_champs_salle(self):
        self.entry_designation_salle.delete(0, tk.END)
        self.combo_serie.set("")
        self.combo_responsable.set("")
        self.entry_nombre_places.delete(0, tk.END)

    def ajouter_salle(self):
        designation = self.entry_designation_salle.get()
        selected_serie = self.combo_serie.get()
        selected_prof = self.combo_responsable.get()
        nombre_places = self.entry_nombre_places.get()

        if not designation or not selected_serie or not selected_prof or not nombre_places:
            messagebox.showwarning("Champ vide", "Veuillez remplir tous les champs.")
            return

        serie_id = self.serie_dict.get(selected_serie)
        prof_id = self.prof_dict.get(selected_prof)

        try:
            self.cursor.execute("""
                INSERT INTO tb_salle (designation, idSerie, idProfResponsable, nombreEtudiant)
                VALUES (%s, %s, %s, %s)
            """, (designation, serie_id, prof_id, nombre_places))
            self.conn.commit()
            self.vider_champs_salle()
            self.afficher_vue_salles()
        except psycopg2.Error as err:
            messagebox.showerror("Erreur d'insertion", f"Erreur : {err}")


    def modifier_salle(self):
        selected_item = self.tree_salle.selection()
        if not selected_item:
            messagebox.showwarning("Aucun élément sélectionné", "Veuillez sélectionner une salle à modifier.")
            return

        salle_id = self.tree_salle.item(selected_item)['values'][0]
        designation = self.entry_designation_salle.get()
        selected_serie = self.combo_serie.get()
        selected_prof = self.combo_responsable.get()
        nombre_places = self.entry_nombre_places.get()

        if not designation or not selected_serie or not selected_prof or not nombre_places:
            messagebox.showwarning("Champ vide", "Veuillez remplir tous les champs.")
            return

        serie_id = self.serie_dict.get(selected_serie)
        prof_id = self.prof_dict.get(selected_prof)

        try:
            self.cursor.execute("""
                UPDATE tb_salle
                SET designation=%s, idSerie=%s, idProfResponsable=%s, nombreEtudiant=%s
                WHERE id=%s
            """, (designation, serie_id, prof_id, nombre_places, salle_id))
            self.conn.commit()
            self.vider_champs_salle()
            self.afficher_vue_salles()
        except psycopg2.Error as err:
            messagebox.showerror("Erreur de modification", f"Erreur : {err}")


    def supprimer_salle(self):
        selected_item = self.tree_salle.selection()
        if not selected_item:
            messagebox.showwarning("Aucun élément sélectionné", "Veuillez sélectionner une salle à supprimer.")
            return


        salle_id = self.tree_salle.item(selected_item)['values'][0]
        if messagebox.askyesno("Confirmation", "Voulez-vous vraiment supprimer cette salle ?"):
            try:
                self.cursor.execute("DELETE FROM tb_salle WHERE id=%s", (salle_id,))
                self.conn.commit()
                self.afficher_vue_salles()
            except psycopg2.Error as err:
                messagebox.showerror("Erreur de suppression", f"Erreur : {err}")


    def populate_professeur_combobox(self):
        professors_data = self.get_professeurs()
        display_names = []
        self.prof_dict = {}

        for prof_id, nom, prenom in professors_data:
            display_name = f"{prenom} {nom}"
            display_names.append(display_name)
            self.prof_dict[display_name] = prof_id


        self.combo_responsable['values'] = display_names
        if display_names:
            self.combo_responsable.set(display_names[0])
        else:
            self.combo_responsable.set("")


    def populate_serie_combobox(self):
        serie_data = self.get_series()
        display_names = []
        self.serie_dict = {}

        for id, designation in serie_data:
            display_names.append(designation)
            self.serie_dict[designation] = id
        self.combo_serie['values'] = display_names
        if display_names:
            self.combo_serie.set(display_names[0])
        else:
            self.combo_serie.set("")

    def create_widgets_salle(self):
        # Champ désignation salle
        self.label_designation_salle = ctk.CTkLabel(self.frame_bas, text="Désignation de la salle:")
        self.entry_designation_salle = tk.Entry(self.frame_bas, width=10)

        # ComboBox série
        self.label_serie = ctk.CTkLabel(self.frame_bas, text="Série:")
        self.combo_serie = ttk.Combobox(self.frame_bas, width=15, state="readonly")

        # ComboBox Responsable

        self.label_responsable = ctk.CTkLabel(self.frame_bas, text="Responsable:")
        self.combo_responsable = ttk.Combobox(self.frame_bas, width=60, state="readonly")

        # Champ Nombre de places

        self.label_nombre_places = ctk.CTkLabel(self.frame_bas, text="Nombre de places:")
        self.entry_nombre_places = tk.Entry(self.frame_bas, width=5)

        # Boutons d'action pour la salle

        self.btn_frame_salle = ctk.CTkFrame(self.frame_bas)
        self.btn_ajouter_salle = ctk.CTkButton(self.btn_frame_salle, text="Ajouter Salle", command=self.ajouter_salle, fg_color="#2ecc71", hover_color="#27ae60", text_color="white")
        self.btn_modifier_salle = ctk.CTkButton(self.btn_frame_salle, text="Modifier Salle", command=self.modifier_salle, fg_color="#3498db", hover_color="#2980b9", text_color="white")
        self.btn_supprimer_salle = ctk.CTkButton(self.btn_frame_salle, text="Supprimer Salle", command=self.supprimer_salle, fg_color="#e74c3c", hover_color="#c0392b", text_color="white")
        self.btn_open_liste_etudiant = ctk.CTkButton(self.btn_frame_salle, text="Liste Étudiants", command=self.open_liste_etudiants_window, fg_color="#8e44ad", hover_color="#9b59b6", text_color="white")


        # Table Treeview pour afficher les salles

        self.tree_salle = ttk.Treeview(self.frame_bas, columns=("ID", "Salle", "Série", "Nom du Professeur", "Prénom du Professeur", "Nombre d'étudiants", "ID Prof. Resp."), show="headings")
        self.tree_salle.heading("ID", text="ID") # Add ID column to Treeview
        self.tree_salle.heading("Salle", text="Salle")
        self.tree_salle.heading("Série", text="Série")
        self.tree_salle.heading("Nom du Professeur", text="Nom du Professeur")
        self.tree_salle.heading("Prénom du Professeur", text="Prénom du Professeur")
        self.tree_salle.heading("Nombre d'étudiants", text="Nombre d'étudiants")
        self.tree_salle.heading("ID Prof. Resp.", text="ID Prof. Resp.") # Hidden column for the professor ID


        self.relocate_widgets_salle()


    def relocate_widgets_salle(self):
        # Placer les widgets dans frame_bas
        self.label_designation_salle.grid(row=0, column=0, sticky="w", padx=3, pady=3)
        self.entry_designation_salle.grid(row=0, column=1, sticky="w", padx=3, pady=3)
        self.label_serie.grid(row=1, column=0, sticky="w", padx=3, pady=3)
        self.combo_serie.grid(row=1, column=1, sticky="w", padx=3, pady=3)
        self.label_responsable.grid(row=2, column=0, sticky="w", padx=3, pady=3)
        self.combo_responsable.grid(row=2, column=1, sticky="w", padx=3, pady=3)
        self.label_nombre_places.grid(row=3, column=0, sticky="w", padx=3, pady=3)
        self.entry_nombre_places.grid(row=3, column=1, sticky="w", padx=3, pady=3)
        self.btn_frame_salle.grid(row=5, column=0, columnspan=2, pady=10)
        self.btn_ajouter_salle.pack(side=tk.LEFT, padx=5)
        self.btn_modifier_salle.pack(side=tk.LEFT, padx=5)
        self.btn_supprimer_salle.pack(side=tk.LEFT, padx=5)
        self.btn_open_liste_etudiant.pack(side=tk.LEFT, padx=5)
        self.tree_salle.grid(row=6, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)


        # Configurer la grille de frame_bas pour l'étirement
        self.frame_bas.grid_columnconfigure(1, weight=1)
        self.frame_bas.grid_rowconfigure(4, weight=1)

    def open_liste_etudiants_window(self):
        # Check if an instance of PageListeParSerie already exists to prevent multiple windows
        # and if the window is still alive
        if not hasattr(self, '_page_liste_par_serie_window') or not self._page_liste_par_serie_window.winfo_exists():
            # Create the PageListeParSerie directly as it is a CTkToplevel
            self._page_liste_par_serie_window = PageListeParSerie(self.master) # Use self.master as the parent
            self._page_liste_par_serie_window.title("Liste des Étudiants par Série") # Set title on the window itself
            # No .pack() needed here, as CTkToplevel windows are managed by the OS
            self._page_liste_par_serie_window.transient(self.master.winfo_toplevel()) # Make it transient to the main app window
            self._page_liste_par_serie_window.grab_set()            # Make it modal
            self._page_liste_par_serie_window.focus_set()           # Give focus to the new window
        else:
            self._page_liste_par_serie_window.focus_set() # Bring existing window to front and focus

    def open_affectation_window(self, salle_id=None):
        professeur_id = None
        if salle_id:
            try:
                self.cursor.execute("SELECT idProfResponsable FROM tb_salle WHERE id = %s", (salle_id,))
                result = self.cursor.fetchone()
                if result:
                    professeur_id = result[0]
                else:
                    messagebox.showwarning("Avertissement", f"Aucun professeur responsable trouvé pour la salle ID: {salle_id}.")
                    return
            except psycopg2.Error as err:
                messagebox.showerror("Erreur SQL", f"Erreur lors de la récupération de l'ID du professeur : {err}")
                return

        if not professeur_id:
            messagebox.showwarning("Information", "Veuillez sélectionner une salle avec un professeur responsable pour l'affectation.")
            return

        # Check if an instance of PageAffectation already exists to prevent multiple windows
        if not hasattr(self, '_page_affectation_window') or not self._page_affectation_window.winfo_exists():
            # Create a new top-level window
            new_window = ctk.CTkToplevel(self.master)
            new_window.title(f"Affectation des Matières (Prof ID: {professeur_id})") # Title for clarity
            self._page_affectation_window = PageAffectation(new_window, professeur_id=professeur_id) # Pass professor_id
            self._page_affectation_window.frame.pack(expand=True, fill="both") # PageAffectation has a 'frame' attribute
            new_window.transient(self.master)
            new_window.grab_set()
            new_window.focus_set()
        else:
            # If window already exists, update its professor_id and refresh its content
            self._page_affectation_window.professeur_id = professeur_id
            self._page_affectation_window.load_professor_info() # Reload professor info
            self._page_affectation_window.master.focus_set()


    def on_salle_double_click(self, event):
        """
        Gère l'événement de double-clic sur le Treeview des salles.
        Ouvre la fenêtre d'affectation pour le professeur responsable de la salle sélectionnée.
        """
        selected_item = self.tree_salle.selection()
        if selected_item:
            values = self.tree_salle.item(selected_item, 'values')
            # L'ID de la salle est la première colonne (index 0)
            salle_id = values[0]
            self.open_affectation_window(salle_id)


if __name__ == '__main__':
    root = ctk.CTk()
    root.title("Gestion des Classes")
    page =PageClasse(root)
    root.mainloop()