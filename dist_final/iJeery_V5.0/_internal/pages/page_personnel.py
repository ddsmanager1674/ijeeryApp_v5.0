import psycopg2
import pandas as pd
import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import json
import os
import sys
from resource_utils import get_config_path, safe_file_read


# Configuration du chemin pour les imports
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
        try:
            config_path = get_config_path('config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config['database']
        except Exception as e:
            print(f"Erreur de configuration : {e}")
            return None

    def connect(self):
        if self.db_params is None: return False
        try:
            self.conn = psycopg2.connect(**self.db_params)
            self.cursor = self.conn.cursor()
            return True
        except Exception as e:
            print(f"Erreur connexion : {e}")
            return False

    def get_cursor(self):
        if self.cursor is None or self.conn.closed:
            self.connect()
        return self.cursor

    def close_connection(self):
        if self.cursor: self.cursor.close()
        if self.conn: self.conn.close()

db_manager = DatabaseManager()

class PagePersonnel(ctk.CTkFrame):
    import customtkinter as ctk

class PagePersonnel(ctk.CTkFrame):
    # Ajoutez 'callback_ajout' ici 
    def __init__(self, parent, callback_ajout): 
        super().__init__(parent)
        self.parent = parent
        self.callback_ajout = callback_ajout # On stocke la fonction pour revenir

        # Exemple de bouton pour revenir à la page d'ajout
        self.btn_retour = ctk.CTkButton(self, 
                                        text="Ajouter Nouveau Personnel", 
                                        command=self.callback_ajout)
        self.btn_retour.pack(pady=20)
        
        ctk.CTkLabel(self, text="", font=("Arial", 20)).pack()
        
        if db_manager.connect():
            self.create_widgets()
        else:
            error_label = ctk.CTkLabel(self, text="Erreur de connexion à la base de données", 
                                     text_color="red", font=("Arial", 16, "bold"))
            error_label.pack(pady=50)
        
        self.pack(expand=True, fill="both")

    def _configure_table_alternating_colors(self, tree):
        tree.tag_configure("row_even", background="#FFFFFF")
        tree.tag_configure("row_odd", background="#D9EEED")

    def _refresh_table_alternating_colors(self, tree):
        for idx, item in enumerate(tree.get_children()):
            tree.item(item, tags=("row_even" if idx % 2 == 0 else "row_odd",))

    def create_widgets(self):
        # Titre
        ctk.CTkLabel(self, text="LISTE DES PERSONNELS", font=("Arial", 20, "bold")).pack(pady=10)

        # Zone gauche : Fonctions
        self.frame_gauche = ctk.CTkFrame(self, width=250)
        self.frame_gauche.pack(side="left", fill="y", padx=10, pady=10)

        ctk.CTkLabel(self.frame_gauche, text="Rechercher une fonction :").pack(pady=(10,0))
        self.entry_recherche = ctk.CTkEntry(self.frame_gauche)
        self.entry_recherche.pack(padx=10, pady=5)
        
        ctk.CTkButton(self.frame_gauche, text="Rechercher", command=self.rechercher_fonction).pack(pady=5)

        # Liste des fonctions (Treeview)
        self.tree_fonction = ttk.Treeview(self.frame_gauche, columns=("ID", "Fonction"), show="headings")
        self._configure_table_alternating_colors(self.tree_fonction)
        self.tree_fonction.heading("ID", text="ID")
        self.tree_fonction.heading("Fonction", text="Désignation")
        self.tree_fonction.column("ID", width=40)
        self.tree_fonction.column("Fonction", width=150)
        self.tree_fonction.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree_fonction.bind("<<TreeviewSelect>>", self.on_select_fonction)

        # Zone droite : Personnels
        self.frame_droite = ctk.CTkFrame(self)
        self.frame_droite.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # Barre d'outils droite
        self.frame_controles = ctk.CTkFrame(self.frame_droite)
        self.frame_controles.pack(fill="x", pady=5, padx=5)

        ctk.CTkButton(self.frame_controles, text="TOUT AFFICHER", command=self.afficher_personnels_tous).pack(side="left", padx=5)
        ctk.CTkButton(self.frame_controles, text="Exporter Excel", fg_color="green", command=self.export_to_excel).pack(side="right", padx=5)

        # Zone de défilement pour la liste des personnels
        self.tree_personnels = ctk.CTkScrollableFrame(self.frame_droite)
        self.tree_personnels.pack(padx=10, pady=10, fill="both", expand=True)

        self.charger_fonctions_initial()

    def charger_fonctions_initial(self):
        try:
            cursor = db_manager.get_cursor()
            cursor.execute("SELECT idfonction, designationfonction FROM tb_fonction ORDER BY designationfonction")
            for row in cursor.fetchall():
                self.tree_fonction.insert("", "end", values=row)
            self._refresh_table_alternating_colors(self.tree_fonction)
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur de chargement : {e}")

    def rechercher_fonction(self):
        recherche = self.entry_recherche.get().lower()
        for row in self.tree_fonction.get_children():
            self.tree_fonction.delete(row)
        self._refresh_table_alternating_colors(self.tree_fonction)
        try:
            cursor = db_manager.get_cursor()
            cursor.execute("SELECT idfonction, designationfonction FROM tb_fonction WHERE LOWER(designationfonction) LIKE %s", (f"%{recherche}%",))
            for row in cursor.fetchall():
                self.tree_fonction.insert("", "end", values=row)
            self._refresh_table_alternating_colors(self.tree_fonction)
        except Exception as e:
            messagebox.showerror("Erreur", f"Recherche impossible : {e}")

    def on_select_fonction(self, event):
        selected = self.tree_fonction.selection()
        if selected:
            id_fonction = self.tree_fonction.item(selected[0])['values'][0]
            self.afficher_personnels(id_fonction)

    def afficher_personnels(self, id_fonction):
        """Affiche les personnels filtrés par la fonction sélectionnée."""
        for widget in self.tree_personnels.winfo_children():
            widget.destroy()
        
        headers = ["Matricule", "Nom", "Prénom", "Sexe", "Date Naiss.", "CIN", "Fonction", "Actions"]
        for j, header in enumerate(headers):
            ctk.CTkLabel(self.tree_personnels, text=header, font=("Arial", 12, "bold")).grid(row=0, column=j, padx=10, pady=5, sticky="w")
        
        try:
            cursor = db_manager.get_cursor()
            # CORRECTION : Ajout du WHERE pour filtrer par id_fonction
            query = """
                SELECT p.matricule, p.nom, p.prenom, p.sexe, p.datenaissance, p.cin, f.designationfonction
                FROM tb_personnel p
                JOIN tb_fonction f ON p.idfonction = f.idfonction
                WHERE p.idfonction = %s
                ORDER BY p.nom, p.prenom
            """
            cursor.execute(query, (id_fonction,))
            rows = cursor.fetchall()

            for i, row in enumerate(rows):
                self._draw_row(i + 1, row)
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur d'affichage : {e}")

    def afficher_personnels_tous(self):
        """Affiche tous les personnels sans filtre."""
        for widget in self.tree_personnels.winfo_children():
            widget.destroy()
            
        headers = ["Matricule", "Nom", "Prénom", "Sexe", "Date Naiss.", "CIN", "Fonction", "Actions"]
        for j, header in enumerate(headers):
            ctk.CTkLabel(self.tree_personnels, text=header, font=("Arial", 12, "bold")).grid(row=0, column=j, padx=10, pady=5, sticky="w")
            
        try:
            cursor = db_manager.get_cursor()
            query = """
                SELECT p.matricule, p.nom, p.prenom, p.sexe, p.datenaissance, p.cin, f.designationfonction
                FROM tb_personnel p
                JOIN tb_fonction f ON p.idfonction = f.idfonction
                ORDER BY p.nom, p.prenom
            """
            cursor.execute(query)
            rows = cursor.fetchall()

            for i, row in enumerate(rows):
                self._draw_row(i + 1, row)
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur d'affichage total : {e}")

    def _draw_row(self, row_idx, data):
        """Helper pour dessiner une ligne dans le scrollable frame."""
        for col_idx, value in enumerate(data):
            ctk.CTkLabel(self.tree_personnels, text=str(value)).grid(row=row_idx*2, column=col_idx, padx=10, pady=2, sticky="w")
        
        btn_frame = ctk.CTkFrame(self.tree_personnels)
        btn_frame.grid(row=row_idx*2, column=7, padx=10, pady=2)
        
        ctk.CTkButton(btn_frame, text="✏️", width=30, height=25, command=lambda: self.modifier_personnel(data[0])).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="❌", width=30, height=25, fg_color="red", command=lambda: self.supprimer_personnel(data[0])).pack(side="left", padx=2)
        
        sep = ctk.CTkFrame(self.tree_personnels, height=1, fg_color="gray")
        sep.grid(row=row_idx*2 + 1, column=0, columnspan=8, sticky="ew", pady=2)

    def modifier_personnel(self, matricule):
        messagebox.showinfo("Info", f"Modification du matricule : {matricule}")

    def supprimer_personnel(self, matricule):
        if messagebox.askyesno("Confirmation", f"Supprimer le personnel {matricule} ?"):
            try:
                cursor = db_manager.get_cursor()
                cursor.execute("DELETE FROM tb_personnel WHERE matricule = %s", (matricule,))
                db_manager.conn.commit()
                self.afficher_personnels_tous()
            except Exception as e:
                messagebox.showerror("Erreur", str(e))

    def export_to_excel(self):
        try:
            cursor = db_manager.get_cursor()
            cursor.execute("""
                SELECT p.matricule, p.nom, p.prenom, p.sexe, p.datenaissance, p.cin, f.designationfonction
                FROM tb_personnel p
                JOIN tb_fonction f ON p.idfonction = f.idfonction
            """)
            df = pd.DataFrame(cursor.fetchall(), columns=["Matricule", "Nom", "Prénom", "Sexe", "Date Naissance", "CIN", "Fonction"])
            path = filedialog.asksaveasfilename(defaultextension=".xlsx")
            if path:
                df.to_excel(path, index=False)
                messagebox.showinfo("Succès", "Exportation réussie")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

if __name__ == '__main__':
    root = ctk.CTk()
    root.title("Gestion des Personnels")
    root.geometry("1200x700")
    app = PagePersonnel(root)
    root.mainloop()
    db_manager.close_connection()
