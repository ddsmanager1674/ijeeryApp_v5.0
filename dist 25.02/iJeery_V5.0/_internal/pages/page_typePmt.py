import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime
import json
import os
from resource_utils import get_config_path, safe_file_read


class PageTypePmt(ctk.CTkFrame):
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
                CREATE TABLE IF NOT EXISTS tb_modepaiement (
	                idmode SERIAL PRIMARY KEY,
	                modedepaiement VARCHAR (50)
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
        
        ctk.CTkLabel(row1, text="Mode de paiement:").pack(side="left", padx=5)
        self.modedepaiement_entry = ctk.CTkEntry(row1, width=150)
        self.modedepaiement_entry.pack(side="left", padx=5)
       
                
        # Frame pour les boutons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", pady=10)
        
        self.add_button = ctk.CTkButton(button_frame, text="Ajouter", 
                                      command=self.add_mode,
                                      fg_color="#2ecc71", hover_color="#27ae60")
        self.add_button.pack(side="left", padx=5)
        
        self.modify_button = ctk.CTkButton(button_frame, text="Modifier", 
                                         command=self.modify_mode,
                                         fg_color="#3498db", hover_color="#2980b9")
        self.modify_button.pack(side="left", padx=5)
        
        self.delete_button = ctk.CTkButton(button_frame, text="Supprimer", 
                                         command=self.delete_mode,
                                         fg_color="#e74c3c", hover_color="#c0392b")
        self.delete_button.pack(side="left", padx=5)
        
        # Treeview - CORRECTION: columns doit être un tuple, pas une chaîne
        columns = ("Mode de paiement",)
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        
        # Configuration des colonnes
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=200)
        
        self.tree.pack(fill="both", expand=True, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Variable pour stocker l'ID du mode sélectionné
        self.selected_mode_id = None
        
        # Charger les modes
        self.load_mode()

    
    def load_mode(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        if not self.conn:
            return

        try:
            # CORRECTION: requête corrigée - idmod -> idmode
            self.cursor.execute("""
                SELECT m.idmode, m.modedepaiement
                FROM tb_modepaiement m
                ORDER BY m.modedepaiement DESC
            """)
            modes = self.cursor.fetchall()
            
            # CORRECTION: n'afficher qu'une seule valeur (mode[1])
            for mode in modes:
                self.tree.insert("", "end", iid=mode[0], values=(mode[1],))
            
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des modes : {err}")

    
    def add_mode(self):
        if not self.conn:
            messagebox.showerror("Erreur", "Connexion à la base de données perdue.")
            return
                    
        try:
            modedepaiement = self.modedepaiement_entry.get()
            
            if not modedepaiement:
                messagebox.showwarning("Attention", "Le champ mode de paiement est obligatoire.")
                return
                
            self.cursor.execute("""
                INSERT INTO tb_modepaiement (modedepaiement)
                VALUES (%s)
                RETURNING idmode
            """, (modedepaiement,))
            
            self.conn.commit()
            self.load_mode()
            self.clear_fields()
            messagebox.showinfo("Succès", "Mode de paiement ajouté avec succès!")
            
        except psycopg2.Error as err:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de l'ajout : {err}")

    def modify_mode(self):
        if not self.conn:
            messagebox.showerror("Erreur", "Connexion à la base de données perdue.")
            return

        if not self.selected_mode_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner un mode de paiement à modifier.")
            return
            
        try:
            modedepaiement = self.modedepaiement_entry.get()
            
            if not modedepaiement:
                messagebox.showwarning("Attention", "Le champ mode de paiement est obligatoire.")
                return
                
            self.cursor.execute("""
                UPDATE tb_modepaiement 
                SET modedepaiement = %s
                WHERE idmode = %s
            """, (modedepaiement, self.selected_mode_id))
            
            self.conn.commit()
            self.load_mode()
            self.clear_fields()
            messagebox.showinfo("Succès", "Mode de paiement modifié avec succès!")
            
        except psycopg2.Error as err:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de la modification : {err}")

    def delete_mode(self):
        if not self.conn:
            messagebox.showerror("Erreur", "Connexion à la base de données perdue.")
            return

        if not self.selected_mode_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner un mode de paiement à supprimer.")
            return
            
        if not messagebox.askyesno("Confirmation", "Voulez-vous vraiment supprimer ce mode de paiement ?"):
            return
            
        try:
            self.cursor.execute("DELETE FROM tb_modepaiement WHERE idmode = %s", (self.selected_mode_id,))
            self.conn.commit()
            self.load_mode()
            self.clear_fields()
            messagebox.showinfo("Succès", "Mode de paiement supprimé avec succès!")
            
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
        mode_id = selected_iid
        
        if not mode_id:
            self.clear_fields()
            return
            
        try:
            self.cursor.execute("""
                SELECT m.idmode, m.modedepaiement
                FROM tb_modepaiement m 
                WHERE m.idmode = %s
            """, (mode_id,))
            
            mode = self.cursor.fetchone()
            if mode:
                self.selected_mode_id = mode[0] 
                
                self.modedepaiement_entry.delete(0, "end")
                self.modedepaiement_entry.insert(0, mode[1])
            else:
                 self.clear_fields()
                
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors de la sélection : {err}")

    def clear_fields(self):
        self.modedepaiement_entry.delete(0, "end")
        self.selected_mode_id = None

    def __del__(self):
        if hasattr(self, 'conn') and self.conn:
            self.cursor.close()
            self.conn.close()

# Pour tester la page individuellement
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    
    app = ctk.CTk()
    app.title("Gestion des modes de paiement")
    app.geometry("500x300")

    page = PageTypePmt(app)
    page.pack(fill="both", expand=True)
    
    app.mainloop()