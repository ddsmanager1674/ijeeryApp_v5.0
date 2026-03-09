import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime
import json
import os
from resource_utils import get_config_path, safe_file_read


class PageUsers(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        
        # Connexion à la base de données
        self.conn = self.connect_db()
        if self.conn:
            self.cursor = self.conn.cursor()
            self.create_table()
        
        # Initialisation des dictionnaires pour la traduction des IDs
        self.fonctions_dict = {}
        self.magasins_dict = {}
        
        self.setup_ui()
        
    def connect_db(self):
        try:
            # Assurez-vous que 'config.json' existe et est accessible
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
        except FileNotFoundError:
            messagebox.showerror("Erreur de configuration", "Fichier 'config.json' non trouvé.")
            return None
        except KeyError:
            messagebox.showerror("Erreur de configuration", "Clés de base de données manquantes dans 'config.json'.")
            return None
        except psycopg2.Error as err:
            messagebox.showerror("Erreur de connexion", f"Erreur de connexion à PostgreSQL : {err}")
            return None
        except UnicodeDecodeError as err:
            messagebox.showerror("Erreur d'encodage", f"Problème d'encodage du fichier de configuration : {err}")
            return None
        
    def create_table(self):
        try:
            # Création de la table des utilisateurs (selon votre structure initiale)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS tb_users (
                    idUser SERIAL PRIMARY KEY,
	                nomUser VARCHAR (50),
	                prenomUser VARCHAR (50),
	                adresseUser VARCHAR (100),
	                contactUser VARCHAR (50),
	                username VARCHAR (50),
	                password VARCHAR (50),
	                idFonction INT,
	                idMag INT,
	                active INT,
	                dateregistre TIMESTAMP,
	                deleted INT DEFAULT 0
                )
            """)
            
            # NOTE : Les tables tb_fonction et tb_magasin doivent exister.
            # J'ajoute une table exemple pour tb_magasin au cas où elle n'existerait pas.
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS tb_magasin (
                    idmag SERIAL PRIMARY KEY,
                    designationmag VARCHAR(50)
                )
            """)
            # J'ajoute une table exemple pour tb_fonction au cas où elle n'existerait pas.
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS tb_fonction (
                    idfonction SERIAL PRIMARY KEY,
                    designationfonction VARCHAR(50)
                )
            """)
            
            self.conn.commit()
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors de la création de la table : {err}")

    def setup_ui(self):
        self.pack(expand=True, fill="both", padx=20, pady=20)
        
        # --- Frame pour les champs de saisie ---
        input_frame = ctk.CTkFrame(self)
        input_frame.pack(fill="x", pady=10)
        
        # Première ligne : Infos Personnelles
        row1 = ctk.CTkFrame(input_frame)
        row1.pack(fill="x", pady=5)
        
        ctk.CTkLabel(row1, text="Nom:").pack(side="left", padx=5)
        self.nomuser_entry = ctk.CTkEntry(row1, width=150)
        self.nomuser_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(row1, text="Prénom:").pack(side="left", padx=5)
        self.prenomuser_entry = ctk.CTkEntry(row1, width=150)
        self.prenomuser_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(row1, text="Adresse:").pack(side="left", padx=5)
        self.adresseuser_entry = ctk.CTkEntry(row1, width=150)
        self.adresseuser_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(row1, text="Contact:").pack(side="left", padx=5)
        self.contactuser_entry = ctk.CTkEntry(row1, width=150)
        self.contactuser_entry.pack(side="left", padx=5)
       
        
        # Deuxième ligne : Infos de Connexion/Rôle
        row2 = ctk.CTkFrame(input_frame)
        row2.pack(fill="x", pady=5)
        
        ctk.CTkLabel(row2, text="Username:").pack(side="left", padx=5)
        self.username_entry = ctk.CTkEntry(row2, width=150)
        self.username_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(row2, text="Password:").pack(side="left", padx=5)
        self.password_entry = ctk.CTkEntry(row2, width=150, show="*")
        self.password_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(row2, text="Fonction:").pack(side="left", padx=5)
        self.fonction_combobox = ctk.CTkComboBox(row2, width=150)
        self.fonction_combobox.pack(side="left", padx=5)
        self.load_fonctions()
        
        # NOUVEAU : ComboBox Magasin
        ctk.CTkLabel(row2, text="Magasin par défaut: ").pack(side="left", padx=5)
        self.magasin_combobox = ctk.CTkComboBox(row2, width=150)
        self.magasin_combobox.pack(side="left", padx=5)
        self.load_magasins()
        
        self.active_var = ctk.BooleanVar(value=True)
        self.active_checkbox = ctk.CTkCheckBox(row2, text="Actif", variable=self.active_var)
        self.active_checkbox.pack(side="left", padx=20)
        
        # --- Frame pour les boutons ---
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", pady=10)
        
        self.add_button = ctk.CTkButton(button_frame, text="Ajouter Utilisateur", 
                                      command=self.add_user,
                                      fg_color="#2ecc71", hover_color="#27ae60")
        self.add_button.pack(side="left", padx=5)
        
        self.modify_button = ctk.CTkButton(button_frame, text="Modifier", 
                                         command=self.modify_user,
                                         fg_color="#3498db", hover_color="#2980b9")
        self.modify_button.pack(side="left", padx=5)
        
        self.delete_button = ctk.CTkButton(button_frame, text="Supprimer", 
                                         command=self.delete_user,
                                         fg_color="#e74c3c", hover_color="#c0392b")
        self.delete_button.pack(side="left", padx=5)
        
        # --- Treeview ---
        # NOUVEAU : Ajout de la colonne Magasin
        columns = ("ID", "Nom", "Prénom", "Username", "Fonction", "Magasin", "Actif", "Date")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        self.tree.tag_configure("row_even", background="#FFFFFF")
        self.tree.tag_configure("row_odd", background="#F1E4D8")
        
        # Configuration des colonnes
        for col in columns:
            self.tree.heading(col, text=col)
            width = 100
            if col in ["ID", "Actif"]:
                width = 50
            elif col == "Date":
                width = 120
            self.tree.column(col, width=width)
        
        self.tree.pack(fill="both", expand=True, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Variable pour stocker l'ID de l'utilisateur sélectionné
        self.selected_user_id = None
        
        # Charger les utilisateurs
        self.load_users()

    def _refresh_table_alternating_colors(self):
        for idx, item in enumerate(self.tree.get_children()):
            self.tree.item(item, tags=("row_even" if idx % 2 == 0 else "row_odd",))

    def load_fonctions(self):
        """Charge les fonctions depuis tb_fonction et les stocke dans un dictionnaire."""
        try:
            if not self.conn: return
            self.cursor.execute("SELECT idfonction, designationfonction FROM tb_fonction ORDER BY designationfonction")
            fonctions = self.cursor.fetchall()
            self.fonctions_dict = {f[1]: f[0] for f in fonctions}
            self.fonction_combobox.configure(values=list(self.fonctions_dict.keys()))
            if fonctions:
                self.fonction_combobox.set(fonctions[0][1])
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des fonctions : {err}")
            
    def load_magasins(self):
        """Charge les magasins depuis tb_magasin."""
        try:
            if not self.conn: return
            self.cursor.execute("SELECT idmag, designationmag FROM tb_magasin ORDER BY designationmag")
            magasins = self.cursor.fetchall()
            
            self.magasins_dict = {m[1]: m[0] for m in magasins}
            self.magasin_combobox.configure(values=list(self.magasins_dict.keys()))
            if magasins:
                self.magasin_combobox.set(magasins[0][1])
            
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des magasins : {err}")

   
    def load_users(self):
        """Charge la liste des utilisateurs pour le Treeview."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._refresh_table_alternating_colors()
        
        if not self.conn: return
            
        try:
            # Récupérer iduser, nom, prenom, username, fonction, actif, date, et designationmag
            self.cursor.execute("""
                SELECT u.iduser, u.nomuser, u.prenomuser, u.username, f.designationfonction, 
                       u.active, u.dateregistre, m.designationmag
                FROM tb_users u
                JOIN tb_fonction f ON u.idfonction = f.idfonction
                LEFT JOIN tb_magasin m ON u.idmag = m.idmag  
                WHERE u.deleted = 0
                ORDER BY u.iduser DESC
            """)
            
            for row in self.cursor.fetchall():
                active_text = "Oui" if row[5] == 1 else "Non"
                date_str = row[6].strftime("%Y-%m-%d %H:%M") if row[6] else "Non défini"
                magasin_text = row[7] if row[7] else ""
                
                self.tree.insert("", "end", values=(row[0], row[1], row[2], row[3], 
                                                  row[4], magasin_text, active_text, date_str))
            self._refresh_table_alternating_colors()
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des utilisateurs : {err}")

    
    def add_user(self):
        """Ajoute un nouvel utilisateur à la table tb_users."""
        if not self.conn: return
                    
        try:
            # Récupérer toutes les entrées
            nomuser = self.nomuser_entry.get().strip()
            prenomuser = self.prenomuser_entry.get().strip()
            adresseuser = self.adresseuser_entry.get().strip()
            contactuser = self.contactuser_entry.get().strip()
            username = self.username_entry.get().strip()
            password = self.password_entry.get().strip()
            fonction_designation = self.fonction_combobox.get()
            magasin_designation = self.magasin_combobox.get()
            active = 1 if self.active_var.get() else 0
            
            if not all([nomuser, prenomuser, username, password, fonction_designation, magasin_designation]):
                messagebox.showwarning("Attention", "Les champs Nom, Prénom, Username, Password, Fonction et Magasin sont obligatoires.")
                return
            
            # Récupérer les IDs
            idfonction = self.fonctions_dict.get(fonction_designation)
            idmag = self.magasins_dict.get(magasin_designation)
            
            if idfonction is None or magasin_designation not in self.magasins_dict:
                 messagebox.showwarning("Attention", "Veuillez sélectionner une Fonction et un Magasin valides.")
                 return

            self.cursor.execute("""
                INSERT INTO tb_users (nomuser, prenomuser, adresseuser, contactuser, username, password, idFonction, idMag, active, dateregistre, deleted)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, 0)
            """, (nomuser, prenomuser, adresseuser, contactuser, username, password, 
                  idfonction, idmag, active))
            
            self.conn.commit()
            self.load_users()
            self.clear_fields()
            messagebox.showinfo("Succès", "Utilisateur ajouté avec succès!")
            
        except psycopg2.Error as err:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de l'ajout : {err}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur inattendue : {e}")


    def modify_user(self):
        """Modifie les informations de l'utilisateur sélectionné."""
        if not self.selected_user_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner un utilisateur à modifier.")
            return
        if not self.conn: return
            
        try:
            # Récupérer toutes les entrées
            nomuser = self.nomuser_entry.get().strip()
            prenomuser = self.prenomuser_entry.get().strip()
            adresseuser = self.adresseuser_entry.get().strip()
            contactuser = self.contactuser_entry.get().strip()
            username = self.username_entry.get().strip()
            password = self.password_entry.get().strip()
            fonction_designation = self.fonction_combobox.get()
            magasin_designation = self.magasin_combobox.get()
            active = 1 if self.active_var.get() else 0
            
            if not all([nomuser, prenomuser, username, password, fonction_designation, magasin_designation]):
                messagebox.showwarning("Attention", "Tous les champs obligatoires doivent être remplis.")
                return
            
            # Récupérer les IDs
            idfonction = self.fonctions_dict.get(fonction_designation)
            idmag = self.magasins_dict.get(magasin_designation)
            
            if idfonction is None or magasin_designation not in self.magasins_dict:
                 messagebox.showwarning("Attention", "Veuillez sélectionner une Fonction et un Magasin valides.")
                 return
                
            self.cursor.execute("""
                UPDATE tb_users 
                SET nomuser = %s, prenomuser = %s, adresseuser = %s, contactuser = %s, 
                    username = %s, password = %s, idfonction = %s, idmag = %s, active = %s
                WHERE iduser = %s
            """, (nomuser, prenomuser, adresseuser, contactuser, username, password, 
                  idfonction, idmag, active, self.selected_user_id))
            
            self.conn.commit()
            self.load_users()
            self.clear_fields()
            messagebox.showinfo("Succès", "Utilisateur modifié avec succès!")
            
        except psycopg2.Error as err:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de la modification : {err}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur inattendue : {e}")


    def delete_user(self):
        """Marque l'utilisateur sélectionné comme supprimé (suppression logique)."""
        if not self.selected_user_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner un utilisateur à supprimer.")
            return
        if not self.conn: return
            
        if not messagebox.askyesno("Confirmation", f"Voulez-vous vraiment supprimer l'utilisateur ID {self.selected_user_id} ? (Suppression logique)"):
            return
            
        try:
            # Suppression logique (setting deleted=1)
            self.cursor.execute("UPDATE tb_users SET deleted = 1 WHERE iduser = %s", (self.selected_user_id,))
            self.conn.commit()
            self.load_users()
            self.clear_fields()
            messagebox.showinfo("Succès", "Utilisateur supprimé (logiquement) avec succès!")
            
        except psycopg2.Error as err:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de la suppression : {err}")

    def on_select(self, event):
        """Gère la sélection d'une ligne dans le Treeview et remplit les champs."""
        if not self.conn: return
        selected = self.tree.selection()
        if not selected:
            self.clear_fields() # Optionnel: effacer les champs si la sélection est perdue
            return
            
        item = self.tree.item(selected[0])
        user_id = item['values'][0]
        
        try:
            # Récupérer toutes les informations de l'utilisateur, y compris l'adresse et le contact.
            self.cursor.execute("""
                SELECT u.iduser, u.nomuser, u.prenomuser, u.adresseuser, u.contactuser, 
                       u.username, u.password, f.designationfonction, u.active, m.designationmag
                FROM tb_users u
                JOIN tb_fonction f ON u.idfonction = f.idfonction
                LEFT JOIN tb_magasin m ON u.idmag = m.idmag
                WHERE u.iduser = %s
            """, (user_id,))
            
            user = self.cursor.fetchone()
            if user:
                # user[0]: iduser, user[1]: nomuser, user[2]: prenomuser, user[3]: adresseuser, user[4]: contactuser
                # user[5]: username, user[6]: password, user[7]: designationfonction, user[8]: active, user[9]: designationmag
                
                self.selected_user_id = user[0]
                
                # Remplissage des champs de saisie
                self.nomuser_entry.delete(0, "end")
                self.nomuser_entry.insert(0, user[1] if user[1] else "")
                
                self.prenomuser_entry.delete(0, "end")
                self.prenomuser_entry.insert(0, user[2] if user[2] else "")
                
                self.adresseuser_entry.delete(0, "end")
                self.adresseuser_entry.insert(0, user[3] if user[3] else "")
                
                self.contactuser_entry.delete(0, "end")
                self.contactuser_entry.insert(0, user[4] if user[4] else "")
                
                self.username_entry.delete(0, "end")
                self.username_entry.insert(0, user[5])
                
                self.password_entry.delete(0, "end")
                self.password_entry.insert(0, user[6])
                
                # ComboBox Fonction
                self.fonction_combobox.set(user[7])
                
                # ComboBox Magasin
                magasin_designation = user[9]
                if magasin_designation in self.magasins_dict:
                    self.magasin_combobox.set(magasin_designation)
                elif self.magasins_dict:
                    self.magasin_combobox.set(next(iter(self.magasins_dict)))
                
                self.active_var.set(user[8] == 1)
                
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors de la sélection : {err}")

    def clear_fields(self):
        """Réinitialise tous les champs de saisie et la sélection."""
        # Réinitialisation des champs de texte
        self.nomuser_entry.delete(0, "end")
        self.prenomuser_entry.delete(0, "end")
        self.adresseuser_entry.delete(0, "end")
        self.contactuser_entry.delete(0, "end")
        self.username_entry.delete(0, "end")
        self.password_entry.delete(0, "end")
        
        # Réinitialisation des ComboBox (si des valeurs existent)
        if len(self.fonction_combobox.cget("values")) > 0:
            self.fonction_combobox.set(self.fonction_combobox.cget("values")[0])
            
        if self.magasins_dict:
            self.magasin_combobox.set(next(iter(self.magasins_dict)))
        
        # Réinitialisation de la checkbox
        self.active_var.set(True)
        
        # Réinitialisation de la sélection
        self.selected_user_id = None
        for item in self.tree.selection():
            self.tree.selection_remove(item)

    def __del__(self):
        """Ferme la connexion à la base de données lors de la destruction de l'objet."""
        if hasattr(self, 'conn') and self.conn:
            try:
                self.cursor.close()
                self.conn.close()
            except Exception:
                pass

# Pour tester la page individuellement
if __name__ == "__main__":
    # NOTE: Assurez-vous que votre fichier config.json est correctement configuré 
    # et que les tables tb_fonction et tb_magasin existent (même vides) dans votre base.
    # Pour le test, vous devriez insérer au moins une fonction et un magasin 
    # pour que les ComboBox ne soient pas vides.
    
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    
    app = ctk.CTk()
    app.title("Mise à jour utilisateurs")
    app.geometry("1200x600")

    page = PageUsers(app)
    page.pack(fill="both", expand=True)
    
    app.mainloop()
