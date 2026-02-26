import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, ttk
import psycopg2
import json
import os
from resource_utils import get_config_path, safe_file_read


# Héritage de ctk.CTk pour en faire la fenêtre principale unique
class PageCategorieCompte(ctk.CTkToplevel):  # Changer CTk en CTkToplevel
    def __init__(self, parent):
        super().__init__(parent)
        
        self.parent = parent
        
        self.title("Gestion des Catégories")
        self.geometry("500x550")
        
        # Rendre la fenêtre modale (optionnel)
        self.grab_set()
        
        # 1. Connexion et Initialisation
        self.conn = self.connect_db()
        if self.conn:
            self.cursor = self.conn.cursor()
            self.initialiser_table()
        else:
            # Si la connexion échoue, on affiche une erreur et on quitte
            self.destroy()
            return

        # 2. Configuration de l'Interface (UI)
        self.setup_ui()
        
        # 3. Chargement initial des données
        self.charger_categoriecompte()

    def connect_db(self):
        try:
            if not os.path.exists(get_config_path('config.json')):
                 messagebox.showerror("Erreur", "Fichier config.json manquant.")
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
            messagebox.showerror("Erreur de connexion", f"Détails : {err}")
            return None

    def initialiser_table(self):
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS tb_categoriecompte (
                    idcc SERIAL PRIMARY KEY,
                    categoriecompte VARCHAR(75)
                )
            """)
            self.conn.commit()
        except psycopg2.Error as err:
            messagebox.showerror("Erreur SQL", f"Erreur table : {err}")

    def setup_ui(self):
        # Configuration de la grille principale
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(5, weight=1)

        # Formulaire
        ctk.CTkLabel(self, text="Désignation Catégorie:").grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        self.entry_catCompte = ctk.CTkEntry(self, placeholder_text="Ex: Client, Fournisseur...")
        self.entry_catCompte.grid(row=0, column=1, padx=20, pady=20, sticky="ew")

        # Zone des Boutons
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        self.btn_frame.grid_columnconfigure((0, 1), weight=1)

        self.save_button = ctk.CTkButton(self.btn_frame, text="Enregistrer", fg_color="#2ecc71", 
                                        hover_color="#27ae60", command=self.enregistrer)
        self.save_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.modify_button = ctk.CTkButton(self.btn_frame, text="Modifier", fg_color="#3498db",
                                          hover_color="#2980b9", command=self.modifier)
        self.modify_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.delete_button = ctk.CTkButton(self.btn_frame, text="Supprimer", fg_color="#e74c3c",
                                          hover_color="#c0392b", command=self.supprimer)
        self.delete_button.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        self.clear_button = ctk.CTkButton(self.btn_frame, text="Vider", command=self.vider)
        self.clear_button.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Tableau (Treeview)
        self.tree_frame = ctk.CTkFrame(self)
        self.tree_frame.grid(row=5, column=0, columnspan=2, padx=20, pady=20, sticky="nsew")

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#FFFFFF", foreground="#000000", rowheight=25, fieldbackground="#FFFFFF", borderwidth=0, font=('Segoe UI', 8))
        style.configure("Treeview.Heading", background="#E8E8E8", foreground="#000000", font=('Segoe UI', 8, 'bold'))
        style.map('Treeview', background=[('selected', '#347083')])

        columns = ("idcc", "categoriecompte")
        self.treeview = ttk.Treeview(self.tree_frame, columns=columns, show='headings')
        
        self.treeview.heading("idcc", text="ID")
        self.treeview.column("idcc", width=50, anchor="center")
        self.treeview.heading("categoriecompte", text="Désignation de la Catégorie", anchor="w")
        self.treeview.column("categoriecompte", width=300, anchor="w")
        
        self.treeview.pack(expand=True, fill="both", padx=5, pady=5)
        self.treeview.bind("<<TreeviewSelect>>", self.remplir_champs)

    def charger_categoriecompte(self):
        if not self.conn: return
        for i in self.treeview.get_children():
            self.treeview.delete(i)
        try:
            self.cursor.execute("SELECT idcc, categoriecompte FROM tb_categoriecompte ORDER BY idcc")
            for row in self.cursor.fetchall():
                self.treeview.insert('', 'end', values=row)
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur de chargement : {e}")
    def enregistrer(self):
        cat = self.entry_catCompte.get().strip()
        if not cat:
            messagebox.showwarning("Attention", "Veuillez saisir une désignation.")            
            return

        try:
            # AJOUT DE LA SYNCHRONISATION AVANT L'INSERTION (utiliser self.cursor au lieu de cursor)
            self.cursor.execute("""
            SELECT setval(pg_get_serial_sequence('tb_categoriecompte', 'idcc'), 
                    COALESCE((SELECT MAX(idcc) FROM tb_categoriecompte), 0) + 1, 
                    false);
            """)
        
            # Insertion directe (pas besoin de _generer_code_article_et_niveau qui n'existe pas)
            self.cursor.execute("INSERT INTO tb_categoriecompte (categoriecompte) VALUES (%s)", (cat,))
            self.conn.commit()
            self.charger_categoriecompte()
            self.vider()
            messagebox.showinfo("Succès", "Catégorie enregistrée avec succès.")
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement : {e}")

    def modifier(self):
        selected = self.treeview.selection()
        if not selected: return
        cat = self.entry_catCompte.get().strip()
        idcc = self.treeview.item(selected[0])['values'][0]
        try:
            self.cursor.execute("UPDATE tb_categoriecompte SET categoriecompte=%s WHERE idcc=%s", (cat, idcc))
            self.conn.commit()
            self.charger_categoriecompte()
            self.vider()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def supprimer(self):
        selected = self.treeview.selection()
        if not selected: return
        if messagebox.askyesno("Confirmation", "Supprimer cet élément ?"):
            idcc = self.treeview.item(selected[0])['values'][0]
            try:
                self.cursor.execute("DELETE FROM tb_categoriecompte WHERE idcc=%s", (idcc,))
                self.conn.commit()
                self.charger_categoriecompte()
                self.vider()
            except Exception as e:
                messagebox.showerror("Erreur", str(e))

    def remplir_champs(self, event):
        selected = self.treeview.selection()
        if selected:
            values = self.treeview.item(selected[0])['values']
            self.entry_catCompte.delete(0, tk.END)
            self.entry_catCompte.insert(0, values[1])

    def vider(self):
        self.entry_catCompte.delete(0, tk.END)
        if self.treeview.selection():
            self.treeview.selection_remove(self.treeview.selection())

if __name__ == "__main__":
    app = PageCategorieCompte()
    app.mainloop()