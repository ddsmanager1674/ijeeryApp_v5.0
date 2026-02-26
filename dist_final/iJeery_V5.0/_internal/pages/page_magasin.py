import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime
import json
import os
from resource_utils import get_config_path, safe_file_read


class PageMagasin(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        
        # Connexion à la base de données
        self.conn = self.connect_db()
        if self.conn:
            self.cursor = self.conn.cursor()
            self.create_table()
        
        self.setup_ui()
        
    def connect_db(self):
        try:
            # Vérifiez que config.json existe et est accessible
            if not os.path.exists(get_config_path('config.json')):
                 messagebox.showerror("Erreur de configuration", "Le fichier config.json est manquant.")
                 return None
                 
            with open(get_config_path('config.json')) as f:
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
        except psycopg2.Error as err:
            messagebox.showerror("Erreur de connexion", f"Erreur : {err}")
            return None
        except UnicodeDecodeError as err:
            messagebox.showerror("Erreur d'encodage", f"Problème d'encodage : {err}")
            return None
        except KeyError as err:
            messagebox.showerror("Erreur de configuration", f"Clé manquante dans config.json : {err}")
            return None
        
    def create_table(self):
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS tb_magasin (
                    idMag SERIAL PRIMARY KEY,
	                designationMag VARCHAR (50),
	                adresseMag VARCHAR (50),
	                livraison INT,
	                deleted INT
                )
            """)
            self.conn.commit()
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors de la création de la table : {err}")

    def setup_ui(self):
        self.pack(expand=True, fill="both", padx=20, pady=20)
        
       
        # Frame pour les champs de saisie
        input_frame = ctk.CTkFrame(self)
        input_frame.pack(fill="x", pady=10)
        
        # Première ligne
        row1 = ctk.CTkFrame(input_frame)
        row1.pack(fill="x", pady=5)
        
        ctk.CTkLabel(row1, text="Nom du Dépôt:").pack(side="left", padx=5)
        self.designationmag_entry = ctk.CTkEntry(row1, width=150)
        self.designationmag_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(row1, text="Adresse:").pack(side="left", padx=5)
        self.adressemag_entry = ctk.CTkEntry(row1, width=150)
        self.adressemag_entry.pack(side="left", padx=5)
       
                
        # Frame pour les boutons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", pady=10)
        
        self.add_button = ctk.CTkButton(button_frame, text="Ajouter", 
                                      command=self.add_magasin,
                                      fg_color="#2ecc71", hover_color="#27ae60")
        self.add_button.pack(side="left", padx=5)
        
        self.modify_button = ctk.CTkButton(button_frame, text="Modifier", 
                                         command=self.modify_magasin,
                                         fg_color="#3498db", hover_color="#2980b9")
        self.modify_button.pack(side="left", padx=5)
        
        self.delete_button = ctk.CTkButton(button_frame, text="Supprimer", 
                                         command=self.delete_magasin,
                                         fg_color="#e74c3c", hover_color="#c0392b")
        self.delete_button.pack(side="left", padx=5)
        
        # Treeview
        columns = ("Nom du dépôt", "Adresse")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        self.tree.tag_configure("even", background="#FFFFFF", foreground="#000000")
        self.tree.tag_configure("odd", background="#E6EFF8", foreground="#000000")
        
        # Configuration des colonnes
        for col in columns:
            self.tree.heading(col, text=col)
            # Ajustement des largeurs de colonne pour les colonnes affichées
            width = 200 if col == "Nom du dépôt" else 200
            self.tree.column(col, width=width)
        
        self.tree.pack(fill="both", expand=True, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Variable pour stocker l'ID du dépôt sélectionné
        self.selected_mag_id = None
        
        # Charger les dépôts
        self.load_magasin()

    
   # CORRECTION ICI : Ajout du fetchall et de l'insertion dans le treeview
    def load_magasin(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        if not self.conn:
            return

        try:
            self.cursor.execute("""
                SELECT m.idmag, m.designationmag, m.adressemag
                FROM tb_magasin m
                ORDER BY m.designationmag DESC
            """)
            magasins = self.cursor.fetchall()
            
            # Insérer les données dans le Treeview
            for idx, mag in enumerate(magasins):
                # mag[0] = idMag (utilisé comme iid), mag[1] = designationMag, mag[2] = adresseMag
                # Les valeurs affichées sont (Nom du dépôt, Adresse)
                tag = "even" if idx % 2 == 0 else "odd"
                self.tree.insert("", "end", iid=mag[0], values=(mag[1], mag[2]), tags=(tag,))
            
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des dépôts : {err}")

    
    def add_magasin(self):
        if not self.conn:
            messagebox.showerror("Erreur", "Connexion à la base de données perdue.")
            return
                    
        try:
                        
            designationmag = self.designationmag_entry.get()
            adressemag = self.adressemag_entry.get()
            
            if not all([designationmag, adressemag]):
                messagebox.showwarning("Attention", "Tous les champs sont obligatoires.")
                return
                
            self.cursor.execute("""
                INSERT INTO tb_magasin (designationmag, adressemag)
                VALUES (%s, %s)
                RETURNING idmag
            """, (designationmag, adressemag))
            
            self.conn.commit()
            self.load_magasin()
            self.clear_fields()
            messagebox.showinfo("Succès", "Dépôt ajouté avec succès!")
            
        except psycopg2.Error as err:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de l'ajout : {err}")

    def modify_magasin(self):
        if not self.conn:
            messagebox.showerror("Erreur", "Connexion à la base de données perdue.")
            return

        if not self.selected_mag_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner un dépôt à modifier.")
            return
            
        try:
            designationmag = self.designationmag_entry.get()
            adressemag = self.adressemag_entry.get()
            
            if not all([designationmag, adressemag]):
                messagebox.showwarning("Attention", "Tous les champs sont obligatoires.")
                return
                
            self.cursor.execute("""
                UPDATE tb_magasin 
                SET designationmag = %s, adressemag = %s
                WHERE idmag = %s
            """, (designationmag, adressemag, self.selected_mag_id))
            
            self.conn.commit()
            self.load_magasin()
            self.clear_fields()
            messagebox.showinfo("Succès", "Dépôt modifié avec succès!")
            
        except psycopg2.Error as err:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de la modification : {err}")

    def delete_magasin(self):
        if not self.conn:
            messagebox.showerror("Erreur", "Connexion à la base de données perdue.")
            return

        if not self.selected_mag_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner un dépôt à supprimer.")
            return
            
        if not messagebox.askyesno("Confirmation", "Voulez-vous vraiment supprimer ce dépôt ?"):
            return
            
        try:
            # Note: Si 'deleted' est utilisé, il faudrait faire un UPDATE:
            # self.cursor.execute("UPDATE tb_magasin SET deleted = 1 WHERE idmag = %s", (self.selected_mag_id,))
            # Ici, on utilise DELETE comme dans votre code initial.
            self.cursor.execute("DELETE FROM tb_magasin WHERE idmag = %s", (self.selected_mag_id,))
            self.conn.commit()
            self.load_magasin()
            self.clear_fields()
            messagebox.showinfo("Succès", "Dépôt supprimé avec succès!")
            
        except psycopg2.Error as err:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de la suppression : {err}")

    # CORRECTION ICI : Récupération de l'iid et utilisation des bons index
    def on_select(self, event):
        if not self.conn:
            return

        selected = self.tree.selection()
        if not selected:
            self.clear_fields()
            return
            
        # 1. Récupérer l'ID interne (iid) de l'élément sélectionné
        # L'élément sélectionné est le premier dans la liste 'selected'
        selected_iid = selected[0] 
        
        # 2. L'identifiant interne (iid) est l'ID du magasin stocké dans la BDD.
        # Dans ce cas, selected_iid contient déjà l'ID du magasin (mag_id)
        # car c'est ce que nous avons passé comme 'iid' lors de l'insertion (mag[0]).
        mag_id = selected_iid
        
        # S'assurer que l'ID est valide (non vide)
        if not mag_id:
            self.clear_fields()
            return
            
        try:
            # Récupération des informations du dépôt sélectionné
            self.cursor.execute("""
                SELECT m.idmag, m.designationmag, m.adressemag
                FROM tb_magasin m 
                WHERE m.idmag = %s
            """, (mag_id,))
            
            magasin = self.cursor.fetchone()
            if magasin:
                # La requête retourne 3 colonnes : [0]idmag, [1]designationmag, [2]adressemag
                self.selected_mag_id = magasin[0] 
                
                self.designationmag_entry.delete(0, "end")
                self.designationmag_entry.insert(0, magasin[1]) # Index 1 pour designationmag
                
                self.adressemag_entry.delete(0, "end")
                self.adressemag_entry.insert(0, magasin[2]) # Index 2 pour adressemag
            else:
                 self.clear_fields()
                
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors de la sélection : {err}")

    def clear_fields(self):
        self.designationmag_entry.delete(0, "end")
        self.adressemag_entry.delete(0, "end")
        self.selected_mag_id = None

    def __del__(self):
        if hasattr(self, 'conn') and self.conn:
            self.cursor.close()
            self.conn.close()

# Pour tester la page individuellement
if __name__ == "__main__":
    # Assurez-vous d'avoir un fichier 'config.json' dans le même répertoire
    # avec la structure suivante pour le test:
    # {
    #   "database": {
    #     "host": "votre_host",
    #     "user": "votre_user",
    #     "password": "votre_password",
    #     "database": "votre_db_name",
    #     "port": "votre_port" 
    #   }
    # }
    
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    
    app = ctk.CTk()
    app.title("Ajouter des nouveaux dépôts")
    app.geometry("500x400")

    page = PageMagasin(app)
    page.pack(fill="both", expand=True)
    
    app.mainloop()
