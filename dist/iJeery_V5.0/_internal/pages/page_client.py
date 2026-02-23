import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime
import json
import os
from resource_utils import get_config_path, safe_file_read


from .page_clientCrédit import PageClientCrédit

class PageClient(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        
        self.type_mapping = {}  # Dictionnaire pour stocker {Désignation: ID}
        
        # Connexion à la base de données
        self.conn = self.connect_db()
        if self.conn:
            self.cursor = self.conn.cursor()
            self.create_table()
        
        self.setup_ui()
        self.load_types() # Charger les types dans la combobox
        self.load_client()
        
    def connect_db(self):
        try:
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
        
    def create_table(self):
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS tb_client (
                    idClient SERIAL PRIMARY KEY,
	                nomCli VARCHAR (100),
	                contactCli VARCHAR (50),
	                adresseCli VARCHAR (150),
	                nifCli VARCHAR (20),
	                statCli VARCHAR (20),
	                cifCli VARCHAR (20),
	                credit DOUBLE PRECISION,
	                idtypeclient INT DEFAULT 1,
	                dateregistre TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	                blocked INT DEFAULT 0,
	                deleted INT DEFAULT 0
                )
            """)
            self.conn.commit()
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors de la création de la table : {err}")

    def load_types(self):
        """Récupère uniquement le type de client avec l'ID 2 pour la ComboBox."""
        try:
            # Ajout de la condition WHERE idtypeclient = 2
            self.cursor.execute("SELECT idtypeclient, designationtypeclient FROM tb_typeclient WHERE idtypeclient = 2")
            types = self.cursor.fetchall()
            
            self.type_mapping = {t[1]: t[0] for t in types}
            self.type_combo.configure(values=list(self.type_mapping.keys()))
            
            if self.type_mapping:
                self.type_combo.set(list(self.type_mapping.keys())[0])
            else:
                # Optionnel : vider la combobox si l'ID 2 n'existe pas en base
                self.type_combo.set("")
                self.type_combo.configure(values=[])
                
        except psycopg2.Error as err:
            print(f"Erreur chargement types : {err}")

    def setup_ui(self):
        self.pack(expand=True, fill="both", padx=20, pady=20)
        
        input_frame = ctk.CTkFrame(self)
        input_frame.pack(fill="x", pady=10)
        
        # Première ligne
        row1 = ctk.CTkFrame(input_frame)
        row1.pack(fill="x", pady=5)
        
        ctk.CTkLabel(row1, text="Nom du Client:").pack(side="left", padx=5)
        self.nomCli_entry = ctk.CTkEntry(row1, width=150)
        self.nomCli_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(row1, text="Contact:").pack(side="left", padx=5)
        self.contactCli_entry = ctk.CTkEntry(row1, width=150)
        self.contactCli_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(row1, text="Adresse:").pack(side="left", padx=5)
        self.adresseCli_entry = ctk.CTkEntry(row1, width=150)
        self.adresseCli_entry.pack(side="left", padx=5)
        
        # Deuxième ligne
        row2 = ctk.CTkFrame(input_frame)
        row2.pack(fill="x", pady=5)
        
        ctk.CTkLabel(row2, text="NIF:").pack(side="left", padx=5)
        self.nifCli_entry = ctk.CTkEntry(row2, width=120)
        self.nifCli_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(row2, text="Crédit:").pack(side="left", padx=5)
        self.credit_entry = ctk.CTkEntry(row2, width=120)
        self.credit_entry.pack(side="left", padx=5)

        # NOUVEAU: ComboBox pour Type de Client
        ctk.CTkLabel(row2, text="Type Client:").pack(side="left", padx=5)
        self.type_combo = ctk.CTkComboBox(row2, width=150, values=[])
        self.type_combo.pack(side="left", padx=5)
        
        # Frame pour les boutons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", pady=10)
        
        self.add_button = ctk.CTkButton(button_frame, text="Ajouter", command=self.add_client, fg_color="#2ecc71")
        self.add_button.pack(side="left", padx=5)
        
        self.modify_button = ctk.CTkButton(button_frame, text="Modifier", command=self.modify_client, fg_color="#3498db")
        self.modify_button.pack(side="left", padx=5)
        
        self.delete_button = ctk.CTkButton(button_frame, text="Supprimer", command=self.delete_client, fg_color="#e74c3c")
        self.delete_button.pack(side="left", padx=5)

        # NOUVEAU : Bouton Crédit
        self.credit_page_button = ctk.CTkButton(button_frame, text="Crédit", 
                                       command=self.open_credit_window,
                                       fg_color="#f39c12", hover_color="#e67e22")
        self.credit_page_button.pack(side="left", padx=5)
        
        # Treeview
        columns = ("Nom du Client", "Contact", "Adresse", "NIF", "Crédit", "Type")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        self.tree.tag_configure("even", background="#FFFFFF", foreground="#000000")
        self.tree.tag_configure("odd", background="#E6EFF8", foreground="#000000")
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)
        
        self.tree.pack(fill="both", expand=True, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        
        self.selected_cli_id = None

    def load_client(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        if not self.conn: return

        try:
            # On masque idtypeclient = 1 avec la clause WHERE
            self.cursor.execute("""
                SELECT c.idclient, c.nomcli, c.contactcli, c.adressecli, c.nifcli, c.credit, t.designationtypeclient
                FROM tb_client c
                LEFT JOIN tb_typeclient t ON c.idtypeclient = t.idtypeclient
                WHERE c.idtypeclient != 1
                ORDER BY c.nomcli ASC
            """)
            clients = self.cursor.fetchall()
            for idx, cli in enumerate(clients):
                tag = "even" if idx % 2 == 0 else "odd"
                self.tree.insert("", "end", iid=cli[0], values=(cli[1], cli[2], cli[3], cli[4], cli[5], cli[6]), tags=(tag,))
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors du chargement : {err}")

    def add_client(self):
        if not self.conn: return
        try:
            nomcli = self.nomCli_entry.get()
            id_type = self.type_mapping.get(self.type_combo.get())
            
            if not nomcli or not id_type:
                messagebox.showwarning("Attention", "Le nom et le type sont obligatoires.")
                return

            self.cursor.execute("""
                INSERT INTO tb_client (nomcli, contactcli, adressecli, nifcli, credit, idtypeclient)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (nomcli, self.contactCli_entry.get(), self.adresseCli_entry.get(), 
                  self.nifCli_entry.get(), self.credit_entry.get() or 0, id_type))
            
            self.conn.commit()
            self.load_client()
            self.clear_fields()
            messagebox.showinfo("Succès", "Client ajouté !")
        except psycopg2.Error as err:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur : {err}")

    def modify_client(self):
        if not self.selected_cli_id: return
        try:
            id_type = self.type_mapping.get(self.type_combo.get())
            self.cursor.execute("""
                UPDATE tb_client 
                SET nomcli=%s, contactcli=%s, adressecli=%s, nifcli=%s, credit=%s, idtypeclient=%s
                WHERE idclient=%s
            """, (self.nomCli_entry.get(), self.contactCli_entry.get(), self.adresseCli_entry.get(),
                  self.nifCli_entry.get(), self.credit_entry.get(), id_type, self.selected_cli_id))
            self.conn.commit()
            self.load_client()
            messagebox.showinfo("Succès", "Client modifié !")
        except psycopg2.Error as err:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur : {err}")

    def delete_client(self):
        if not self.selected_cli_id: return
        if messagebox.askyesno("Confirmation", "Supprimer ce client ?"):
            try:
                self.cursor.execute("DELETE FROM tb_client WHERE idclient = %s", (self.selected_cli_id,))
                self.conn.commit()
                self.load_client()
                self.clear_fields()
            except psycopg2.Error as err:
                messagebox.showerror("Erreur", f"Erreur : {err}")

    def on_select(self, event):
        selected = self.tree.selection()
        if not selected: return
        
        self.selected_cli_id = selected[0]
        try:
            self.cursor.execute("""
                SELECT c.nomcli, c.contactcli, c.adressecli, c.nifcli, c.credit, t.designationtypeclient
                FROM tb_client c
                LEFT JOIN tb_typeclient t ON c.idtypeclient = t.idtypeclient
                WHERE c.idclient = %s
            """, (self.selected_cli_id,))
            res = self.cursor.fetchone()
            if res:
                self.nomCli_entry.delete(0, "end")
                self.nomCli_entry.insert(0, res[0])
                self.contactCli_entry.delete(0, "end")
                self.contactCli_entry.insert(0, res[1])
                self.adresseCli_entry.delete(0, "end")
                self.adresseCli_entry.insert(0, res[2])
                self.nifCli_entry.delete(0, "end")
                self.nifCli_entry.insert(0, res[3])
                self.credit_entry.delete(0, "end")
                self.credit_entry.insert(0, res[4])
                self.type_combo.set(res[5])
        except psycopg2.Error as err:
            print(err)

    def clear_fields(self):
        for entry in [self.nomCli_entry, self.contactCli_entry, self.adresseCli_entry, self.nifCli_entry, self.credit_entry]:
            entry.delete(0, "end")
        self.selected_cli_id = None

    def open_credit_window(self):
        """Ouvre la fenêtre des crédits clients dans un nouveau pop-up."""
        credit_window = ctk.CTkToplevel(self)
        credit_window.title("Détails des Crédits Clients")
        credit_window.geometry("900x600")
    
        # Force la fenêtre à être au-dessus
        credit_window.attributes("-topmost", True)
    
        # Rendre la fenêtre redimensionnable
        credit_window.grid_columnconfigure(0, weight=1)
        credit_window.grid_rowconfigure(0, weight=1)
    
        # Initialisation de la page de crédit à l'intérieur du pop-up
        credit_page = PageClientCrédit(credit_window)
        credit_page.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("1000x600")
    PageClient(app).pack(fill="both", expand=True)
    app.mainloop()
