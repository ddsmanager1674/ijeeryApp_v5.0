import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import json
import os
from resource_utils import get_config_path, safe_file_read


class PageCodeAutorisation(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        
        # Variables de contrôle
        self.selected_id = None
        
        # --- Interface Graphique ---
        self.label_titre = ctk.CTkLabel(self, text="Gestion des Codes d'Autorisation", font=("Arial", 20, "bold"))
        self.label_titre.pack(pady=20)

        # Zone de saisie
        self.frame_form = ctk.CTkFrame(self)
        self.frame_form.pack(pady=10, padx=20, fill="x")

        self.lbl_code = ctk.CTkLabel(self.frame_form, text="Code :")
        self.lbl_code.grid(row=0, column=0, padx=10, pady=10)
        
        self.entry_code = ctk.CTkEntry(self.frame_form, width=200)
        self.entry_code.grid(row=0, column=1, padx=10, pady=10)

        # Boutons
        self.frame_buttons = ctk.CTkFrame(self)
        self.frame_buttons.pack(pady=10)

        self.btn_enregistrer = ctk.CTkButton(self.frame_buttons, text="Enregistrer", command=self.enregistrer_code)
        self.btn_enregistrer.grid(row=0, column=0, padx=10)

        self.btn_modifier = ctk.CTkButton(self.frame_buttons, text="Modifier", command=self.modifier_code, fg_color="orange")
        self.btn_modifier.grid(row=0, column=1, padx=10)

        # Treeview (Tableau)
        self.style = ttk.Style()
        self.style.theme_use("default")
        self.style.configure("Treeview", background="#FFFFFF", foreground="#000000", fieldbackground="#FFFFFF", borderwidth=0, rowheight=22, font=('Segoe UI', 8))
        self.style.configure("Treeview.Heading", background="#E8E8E8", foreground="#000000", font=('Segoe UI', 8, 'bold'))
        self.style.map("Treeview", background=[('selected', '#1f538d')])

        self.tree = ttk.Treeview(self, columns=("ID", "Code", "Username"), show='headings')
        self.tree.heading("ID", text="ID")
        self.tree.heading("Code", text="Code")
        self.tree.heading("Username", text="Utilisateur")
        
        self.tree.column("ID", width=50)
        self.tree.column("Code", width=150)
        self.tree.column("Username", width=150)
        
        self.tree.pack(pady=20, padx=20, fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.selectionner_item)

        # Charger les données au démarrage
        self.afficher_donnees()

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
        except Exception as err:
            messagebox.showerror("Erreur", f"Erreur : {err}")
            return None

    def afficher_donnees(self):
        # On vide le treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        conn = self.connect_db()
        if conn:
            try:
                cur = conn.cursor()
                # Jointure pour récupérer le username de tb_users
                query = """
                    SELECT ca.id, ca.code, u.username 
                    FROM tb_codeautorisation ca
                    JOIN tb_users u ON ca.iduser = u.iduser
                    WHERE ca.deleted = 0
                    ORDER BY ca.id DESC
                """
                cur.execute(query)
                for row in cur.fetchall():
                    self.tree.insert("", "end", values=row)
                conn.close()
            except Exception as e:
                print(f"Erreur d'affichage : {e}")

    def enregistrer_code(self):
        code = self.entry_code.get()
        if not code:
            messagebox.showwarning("Champs vide", "Veuillez saisir un code.")
            return

        conn = self.connect_db()
        if conn:
            try:
                cur = conn.cursor()
                # On utilise iduser = 1 par défaut comme demandé
                cur.execute("INSERT INTO tb_codeautorisation (code, iduser) VALUES (%s, %s)", (code, 1))
                conn.commit()
                conn.close()
                messagebox.showinfo("Succès", "Code enregistré avec succès !")
                self.entry_code.delete(0, 'end')
                self.afficher_donnees()
            except Exception as e:
                messagebox.showerror("Erreur", f"Échec de l'enregistrement : {e}")

    def selectionner_item(self, event):
        selected = self.tree.focus()
        if selected:
            values = self.tree.item(selected, 'values')
            self.selected_id = values[0]
            self.entry_code.delete(0, 'end')
            self.entry_code.insert(0, values[1])

    def modifier_code(self):
        if not self.selected_id:
            messagebox.showwarning("Sélection", "Veuillez sélectionner un code dans la liste.")
            return

        code = self.entry_code.get()
        conn = self.connect_db()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("UPDATE tb_codeautorisation SET code = %s WHERE id = %s", (code, self.selected_id))
                conn.commit()
                conn.close()
                messagebox.showinfo("Succès", "Code modifié avec succès !")
                self.selected_id = None
                self.entry_code.delete(0, 'end')
                self.afficher_donnees()
            except Exception as e:
                messagebox.showerror("Erreur", f"Échec de la modification : {e}")

if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Test Page Code Autorisation")
    app.geometry("400x300")
    
    # Instance de votre page
    page = PageCodeAutorisation(app)
    page.pack(fill="both", expand=True)
    
    app.mainloop()