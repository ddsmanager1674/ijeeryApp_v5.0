import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime
import json
import os
from resource_utils import get_config_path, safe_file_read


from .page_FrsDette import PageFrsDette

class PageFournisseur(ctk.CTkFrame):
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
            # CORRECTION: Changement de tb_magasin à tb_client pour la cohérence
            # Ajout des valeurs par défaut pour les colonnes non entrées par l'utilisateur
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS tb_client (
                    idFrs SERIAL PRIMARY KEY,
	                nomFrs VARCHAR (150),
	                contactFrs VARCHAR (50),
	                adresseFrs VARCHAR (150),
	                nifFrs VARCHAR (20),
	                statFrs VARCHAR (20),
	                cifFrs VARCHAR (20),
	                dateregistre TIMESTAMP,
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
        
        ctk.CTkLabel(row1, text="Nom du Fournisseur:").pack(side="left", padx=5)
        self.nomFrs_entry = ctk.CTkEntry(row1, width=150)
        self.nomFrs_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(row1, text="Contact:").pack(side="left", padx=5)
        self.contactFrs_entry = ctk.CTkEntry(row1, width=150)
        self.contactFrs_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(row1, text="Adresse:").pack(side="left", padx=5)
        self.adresseFrs_entry = ctk.CTkEntry(row1, width=150)
        self.adresseFrs_entry.pack(side="left", padx=5)
        
        # Deuxième ligne
        row2 = ctk.CTkFrame(input_frame)
        row2.pack(fill="x", pady=5)
        
        ctk.CTkLabel(row2, text="NIF:").pack(side="left", padx=5)
        self.nifFrs_entry = ctk.CTkEntry(row2, width=150)
        self.nifFrs_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(row2, text="STAT:").pack(side="left", padx=5)
        self.statFrs_entry = ctk.CTkEntry(row2, width=150)
        self.statFrs_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(row2, text="CIF:").pack(side="left", padx=5)
        self.cifFrs_entry = ctk.CTkEntry(row2, width=150)
        self.cifFrs_entry.pack(side="left", padx=5)
                
        # Frame pour les boutons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", pady=10)
        
        self.add_button = ctk.CTkButton(button_frame, text="Ajouter", 
                                      command=self.add_fournisseur,
                                      fg_color="#2ecc71", hover_color="#27ae60")
        self.add_button.pack(side="left", padx=5)
        
        self.modify_button = ctk.CTkButton(button_frame, text="Modifier", 
                                         command=self.modify_fournisseur,
                                         fg_color="#3498db", hover_color="#2980b9")
        self.modify_button.pack(side="left", padx=5)
        
        self.delete_button = ctk.CTkButton(button_frame, text="Supprimer", 
                                         command=self.delete_fournisseur,
                                         fg_color="#e74c3c", hover_color="#c0392b")
        self.delete_button.pack(side="left", padx=5)
        
        # NOUVEAU : Bouton Crédit
        self.dette_page_button = ctk.CTkButton(button_frame, text="Dettes", 
                                       command=self.open_dettes_window,
                                       fg_color="#f39c12", hover_color="#e67e22")
        self.dette_page_button.pack(side="left", padx=5)
        
        # Treeview
        columns = ("Nom du Fournisseur", "Contact", "Adresse", "NIF", "STAT", "CIF")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        self.tree.tag_configure("even", background="#FFFFFF", foreground="#000000")
        self.tree.tag_configure("odd", background="#E6EFF8", foreground="#000000")
        
        # Configuration des colonnes
        for col in columns:
            self.tree.heading(col, text=col)
            # Ajustement des largeurs de colonne 
            width = 100 
            self.tree.column(col, width=width)
        
        self.tree.pack(fill="both", expand=True, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        
        # Scrollbar Vertical
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Variable pour stocker l'ID du client sélectionné
        self.selected_frs_id = None
        
        # Charger les clients
        self.load_Fournisseur()

    def open_dettes_window(self):
        """Ouvre la fenêtre des dettes fournisseurs dans un nouveau pop-up."""
        credit_window = ctk.CTkToplevel(self)
        credit_window.title("Détails des Dettes Fournisseurs")
        credit_window.geometry("900x600")
    
        # Force la fenêtre à être au-dessus
        credit_window.attributes("-topmost", True)
    
        # Rendre la fenêtre redimensionnable
        credit_window.grid_columnconfigure(0, weight=1)
        credit_window.grid_rowconfigure(0, weight=1)
    
        # Initialisation de la page de crédit à l'intérieur du pop-up
        credit_page = PageFrsDette(credit_window)
        credit_page.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
    def load_Fournisseur(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        if not self.conn:
            return

        try:
            self.cursor.execute("""
                SELECT f.idfrs, f.nomfrs, f.contactfrs, f.adressefrs, f.niffrs, f.statfrs, f.ciffrs
                FROM tb_fournisseur f
                ORDER BY f.nomfrs DESC
            """)
            fournisseurs = self.cursor.fetchall()
            
            # Insérer les données dans le Treeview
            for idx, frs in enumerate(fournisseurs):
                # CORRECTION: Insérer les 7 colonnes affichables pour le Treeview
                # cli[0]=idclient, cli[1]=nomcli, cli[2]=contactcli, cli[3]=adressecli, cli[4]=nifcli, cli[5]=statcli, cli[6]=cifcli, cli[7]=credit
                tag = "even" if idx % 2 == 0 else "odd"
                self.tree.insert("", "end", iid=frs[0], values=(frs[1], frs[2], frs[3], frs[4], frs[5], frs[6]), tags=(tag,))
            
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des fournisseurs : {err}")

    
    def add_fournisseur(self):
        if not self.conn:
            messagebox.showerror("Erreur", "Connexion à la base de données perdue.")
            return
                    
        try:
                        
            nomfrs = self.nomFrs_entry.get()
            contactfrs = self.contactFrs_entry.get()
            adressefrs = self.adresseFrs_entry.get()
            niffrs = self.nifFrs_entry.get()
            statfrs = self.statFrs_entry.get()
            ciffrs = self.cifFrs_entry.get()
            
            if not all([nomfrs, contactfrs, adressefrs, niffrs, statfrs, ciffrs]):
                messagebox.showwarning("Attention", "Tous les champs sont obligatoires.")
                return
                
            # CORRECTION : Spécifier explicitement toutes les colonnes et fournir toutes les valeurs.
            self.cursor.execute("""
                INSERT INTO tb_fournisseur (nomfrs, contactfrs, adressefrs, niffrs, statfrs, ciffrs, dateregistre, deleted)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, 0)
                RETURNING idfrs
            """, (nomfrs, contactfrs, adressefrs, niffrs, statfrs, ciffrs))
            
            self.conn.commit()
            self.load_Fournisseur()
            self.clear_fields()
            messagebox.showinfo("Succès", "Fournisseur ajouté avec succès!")
            
        except psycopg2.Error as err:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de l'ajout : {err}")

    def modify_fournisseur(self):
        if not self.conn:
            messagebox.showerror("Erreur", "Connexion à la base de données perdue.")
            return

        if not self.selected_frs_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner un client à modifier.")
            return
            
        try:
            nomfrs = self.nomFrs_entry.get()
            contactfrs = self.contactFrs_entry.get()
            adressefrs = self.adresseFrs_entry.get()
            niffrs = self.nifFrs_entry.get()
            statfrs = self.statFrs_entry.get()
            ciffrs = self.cifFrs_entry.get()
            
            if not all([nomfrs, contactfrs, adressefrs, niffrs, statfrs, ciffrs]):
                messagebox.showwarning("Attention", "Tous les champs sont obligatoires.")
                return
                
            self.cursor.execute("""
                UPDATE tb_fournisseur 
                SET nomfrs = %s, contactfrs = %s, adressefrs = %s, niffrs = %s, statfrs = %s, ciffrs = %s
                WHERE idfrs = %s
            """, (nomfrs, contactfrs, adressefrs, niffrs, statfrs, ciffrs, self.selected_frs_id))
            
            self.conn.commit()
            self.load_Fournisseur()
            self.clear_fields()
            messagebox.showinfo("Succès", "Fournisseur modifié avec succès!")
            
        except psycopg2.Error as err:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de la modification : {err}")

    def delete_fournisseur(self):
        if not self.conn:
            messagebox.showerror("Erreur", "Connexion à la base de données perdue.")
            return

        if not self.selected_frs_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner un fournisseur à supprimer.")
            return
            
        if not messagebox.askyesno("Confirmation", "Voulez-vous vraiment supprimer ce fournisseur ?"):
            return
            
        try:
            self.cursor.execute("DELETE FROM tb_fournisseur WHERE idfrs = %s", (self.selected_frs_id,))
            self.conn.commit()
            self.load_Fournisseur()
            self.clear_fields()
            messagebox.showinfo("Succès", "Fournisseur supprimé avec succès!")
            
        except psycopg2.Error as err:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de la suppression : {err}")

    def on_select(self, event):
        if not self.conn:
            return

        selected = self.tree.selection()
        if not selected:
            self.clear_fields()
            return
            
        selected_iid = selected[0] 
        frs_id = selected_iid
        
        if not frs_id:
            self.clear_fields()
            return
            
        try:
            # CORRECTION : Correction des alias (un seul alias 'c' est utilisé)
            self.cursor.execute("""
                SELECT f.idfrs, f.nomfrs, f.contactfrs, f.adressefrs, f.niffrs, f.statfrs, f.ciffrs
                FROM tb_fournisseur f
                WHERE f.idfrs = %s
            """, (frs_id,))
            
            client = self.cursor.fetchone()
            if client:
                # Les indices sont : [0]idclient, [1]nomcli, [2]contactcli, [3]adressecli, [4]nifcli, [5]statcli, [6]cifcli, [7]credit
                self.selected_frs_id = client[0] 
                
                self.nomFrs_entry.delete(0, "end")
                self.nomFrs_entry.insert(0, client[1]) 
                
                self.contactFrs_entry.delete(0, "end")
                self.contactFrs_entry.insert(0, client[2]) 
                
                self.adresseFrs_entry.delete(0, "end")
                self.adresseFrs_entry.insert(0, client[3])
                
                self.nifFrs_entry.delete(0, "end")
                self.nifFrs_entry.insert(0, client[4])
                
                self.statFrs_entry.delete(0, "end")
                self.statFrs_entry.insert(0, client[5])
                
                self.cifFrs_entry.delete(0, "end")
                self.cifFrs_entry.insert(0, client[6])
            else:
                 self.clear_fields()
                
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors de la sélection : {err}")

    def clear_fields(self):
        self.nomFrs_entry.delete(0, "end")
        self.contactFrs_entry.delete(0, "end")
        self.adresseFrs_entry.delete(0, "end")
        self.nifFrs_entry.delete(0, "end")
        self.statFrs_entry.delete(0, "end")
        self.cifFrs_entry.delete(0, "end")
        self.selected_frs_id = None

    def __del__(self):
        if hasattr(self, 'conn') and self.conn:
            if hasattr(self, 'cursor') and self.cursor:
                self.cursor.close()
            self.conn.close()

# Pour tester la page individuellement
if __name__ == "__main__":
        
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    
    app = ctk.CTk()
    app.title("Mise à jour Fournisseurs")
    app.geometry("1000x500")

    page = PageFournisseur(app)
    page.pack(fill="both", expand=True)
    
    app.mainloop()
