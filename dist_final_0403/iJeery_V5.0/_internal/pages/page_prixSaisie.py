import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime
import json
from resource_utils import get_config_path, safe_file_read


class PagePrixSaisie(ctk.CTkFrame):
    def __init__(self, parent, iduser, codearticle = None):
        super().__init__(parent)
        self.iduser = iduser
        # CORRECTION: Convertir codearticle en string s'il n'est pas None
        self.codearticle = str(codearticle) if codearticle is not None else None
        self.selected_id = None
        
        # CORRECTION: Initialiser les dictionnaires dès le début
        self.articles_dict = {}
        self.unites_dict = {}
        
        self.configure(fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Titre
        titre = ctk.CTkLabel(
            self, 
            text="Gestion des Prix", 
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold")
        )
        titre.grid(row=0, column=0, pady=20, padx=20, sticky="w")
        
        # Frame principal
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        
        # Frame de saisie
        form_frame = ctk.CTkFrame(main_frame)
        form_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        form_frame.grid_columnconfigure(1, weight=1)
        
        # Code Article
        ctk.CTkLabel(form_frame, text="Code Article:", font=ctk.CTkFont(family="Segoe UI", size=13)).grid(
            row=0, column=0, sticky="w", padx=10, pady=10
        )
        self.combo_code = ctk.CTkComboBox(
            form_frame, 
            width=300,
            command=self.on_code_selected,
            state="readonly"
        )
        self.combo_code.grid(row=0, column=1, sticky="ew", padx=10, pady=10)
        
        # Nom d'Article
        ctk.CTkLabel(form_frame, text="Nom d'Article:", font=ctk.CTkFont(family="Segoe UI", size=13)).grid(
            row=1, column=0, sticky="w", padx=10, pady=10
        )
        self.entry_nom = ctk.CTkEntry(form_frame, width=300, state="readonly")
        self.entry_nom.grid(row=1, column=1, sticky="ew", padx=10, pady=10)
        
        # Unité
        ctk.CTkLabel(form_frame, text="Unité:", font=ctk.CTkFont(family="Segoe UI", size=13)).grid(
            row=2, column=0, sticky="w", padx=10, pady=10
        )
        self.combo_unite = ctk.CTkComboBox(
            form_frame, 
            width=300,
            state="readonly"
        )
        self.combo_unite.grid(row=2, column=1, sticky="ew", padx=10, pady=10)
        
        # Prix
        ctk.CTkLabel(form_frame, text="Prix:", font=ctk.CTkFont(family="Segoe UI", size=13)).grid(
            row=3, column=0, sticky="w", padx=10, pady=10
        )
        self.entry_prix = ctk.CTkEntry(form_frame, width=300, placeholder_text="0.00")
        self.entry_prix.grid(row=3, column=1, sticky="ew", padx=10, pady=10)
        
        # Frame des boutons
        button_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        self.btn_enregistrer = ctk.CTkButton(
            button_frame,
            text="Enregistrer",
            command=self.enregistrer,
            width=120,
            fg_color="#28a745",
            hover_color="#218838"
        )
        self.btn_enregistrer.pack(side="left", padx=5)
        
        self.btn_modifier = ctk.CTkButton(
            button_frame,
            text="Modifier",
            command=self.modifier,
            width=120,
            fg_color="#ffc107",
            hover_color="#e0a800"
        )
        self.btn_modifier.pack(side="left", padx=5)
        
        self.btn_supprimer = ctk.CTkButton(
            button_frame,
            text="Supprimer",
            command=self.supprimer,
            width=120,
            fg_color="#dc3545",
            hover_color="#c82333"
        )
        self.btn_supprimer.pack(side="left", padx=5)
        
        self.btn_nouveau = ctk.CTkButton(
            button_frame,
            text="Nouveau",
            command=self.nouveau,
            width=120,
            fg_color="#17a2b8",
            hover_color="#138496"
        )
        self.btn_nouveau.pack(side="left", padx=5)
        
        # Frame pour le tableau
        table_frame = ctk.CTkFrame(main_frame)
        table_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)
        
        # Label pour l'historique
        ctk.CTkLabel(
            table_frame, 
            text="Historique des Prix", 
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))
        
        # Treeview
        tree_container = ctk.CTkFrame(table_frame)
        tree_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        tree_container.grid_columnconfigure(0, weight=1)
        tree_container.grid_rowconfigure(0, weight=1)
        
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background="#2b2b2b",
            foreground="white",
            fieldbackground="#2b2b2b",
            borderwidth=0,
            font=('Segoe UI', 10)
        )
        style.configure("Treeview.Heading", background="#E8E8E8", foreground="#000000", font=('Segoe UI', 8, 'bold'))
        style.map('Treeview', background=[('selected', '#1f538d')])
        
        self.tree = ttk.Treeview(
            tree_container,
            columns=("ID", "Date", "Prix"),
            show="headings",
            height=10
        )
        
        self.tree.heading("ID", text="ID")
        self.tree.heading("Date", text="Date")
        self.tree.heading("Prix", text="Prix")
        
        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Date", width=200, anchor="center")
        self.tree.column("Prix", width=150, anchor="center")
        
        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        
        # Charger les données initiales
        self.charger_articles()
        self.charger_unites()
        
        if self.codearticle and self.codearticle in self.articles_dict:
            self.combo_code.set(self.codearticle)
            self.on_code_selected(self.codearticle)
        
    def connect_db(self):
        """Connexion à la base de données PostgreSQL"""
        try:
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
    
    def charger_articles(self):
        """Charger les articles depuis la base de données"""
        try:
            conn = self.connect_db()
            if not conn:
                self.articles_dict = {}  # Initialiser même en cas d'erreur
                return
            cur = conn.cursor()
        
            # Si un code article est spécifié, filtrer uniquement cet article
            if self.codearticle:
                # CORRECTION: Forcer le retour en TEXT pour préserver les zéros initiaux
                cur.execute("""
                    SELECT a.idarticle, u.codearticle::TEXT, a.designation, u.designationunite, u.idunite
                    FROM tb_unite u
                    INNER JOIN tb_article a ON u.idarticle = a.idarticle
                    WHERE u.codearticle::TEXT = %s
                    ORDER BY u.codearticle
                """, (self.codearticle,))
            else:
                cur.execute("""
                    SELECT a.idarticle, u.codearticle::TEXT, a.designation, u.designationunite, u.idunite
                    FROM tb_unite u
                    INNER JOIN tb_article a ON u.idarticle = a.idarticle
                    WHERE a.deleted = 0
                    ORDER BY u.codearticle
                """)
        
            articles = cur.fetchall()
        
            if not articles and self.codearticle:
                self.articles_dict = {}  # Initialiser même si vide
                messagebox.showerror("Erreur", 
                    f"L'article avec le code '{self.codearticle}' n'existe pas dans la base de données.\n\n"
                    f"Veuillez vérifier que ce code existe dans la table tb_unite.")
                cur.close()
                conn.close()
                return
        
            # CORRECTION: Gérer les valeurs None dans les tuples
            # Stocker: code -> (idarticle, designation, unite, idunite)
            self.articles_dict = {
                str(a[1]): (
                    a[0], 
                    str(a[2] or ""), 
                    str(a[3] or ""), 
                    a[4]
                ) 
                for a in articles if a[1] is not None
            }
            codes = list(self.articles_dict.keys())
        
            self.combo_code.configure(values=codes if codes else ["Aucun article"])
            if codes:
                self.combo_code.set(codes[0])
                self.on_code_selected(codes[0])
        
            cur.close()
            conn.close()
        except Exception as e:
            self.articles_dict = {}  # Initialiser même en cas d'exception
            messagebox.showerror("Erreur", f"Erreur lors du chargement des articles: {str(e)}")
    
    def charger_unites(self):
        """Charger les unités depuis la base de données"""
        try:
            conn = self.connect_db()
            if not conn:
                return
            cur = conn.cursor()
            cur.execute("""
                SELECT idunite, designationunite 
                FROM tb_unite 
                WHERE deleted = 0 
                ORDER BY designationunite
            """)
            unites = cur.fetchall()
            
            # CORRECTION: Gérer les valeurs None
            self.unites_dict = {str(u[1] or ""): u[0] for u in unites if u[1] is not None}
            designations = list(self.unites_dict.keys())
            
            self.combo_unite.configure(values=designations if designations else ["Aucune unité"])
            if designations:
                self.combo_unite.set(designations[0])
            
            cur.close()
            conn.close()
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des unités: {str(e)}")
    
    def on_code_selected(self, choice):
        """Quand un code article est sélectionné"""
        if choice in self.articles_dict:
            idarticle, designation, unite, idunite = self.articles_dict[choice]
            
            # Afficher le nom d'article
            self.entry_nom.configure(state="normal")
            self.entry_nom.delete(0, "end")
            self.entry_nom.insert(0, designation if designation else "")
            self.entry_nom.configure(state="readonly")
            
            # Afficher l'unité
            if unite:
                self.combo_unite.set(unite)
            elif self.combo_unite.cget("values"):
                self.combo_unite.set(self.combo_unite.cget("values")[0])
            
            # Charger l'historique
            self.charger_historique(idarticle)
    
    def charger_historique(self, idarticle):
        """Charger l'historique des prix pour un article"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            conn = self.connect_db()
            if not conn:
                return
            cur = conn.cursor()
            
            # CORRECTION: Récupérer l'historique des prix avec l'idunite correspondant
            cur.execute("""
                SELECT p.id, p.dateregistre, p.prix 
                FROM tb_prix p
                INNER JOIN tb_unite u ON p.idunite = u.idunite
                WHERE u.idarticle = %s AND p.deleted = 0 
                ORDER BY p.dateregistre DESC
            """, (idarticle,))
            
            for row in cur.fetchall():
                date_str = row[1].strftime("%d/%m/%Y %H:%M:%S") if row[1] else ""
                prix_str = f"{row[2]:.2f}" if row[2] else "0.00"
                self.tree.insert("", "end", values=(row[0], date_str, prix_str))
            
            cur.close()
            conn.close()
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement de l'historique: {str(e)}")
    
    def on_tree_select(self, event):
        """Quand une ligne est sélectionnée dans le tableau"""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            values = item['values']
            self.selected_id = values[0]
            prix = values[2].replace(',', '.')
            self.entry_prix.delete(0, "end")
            self.entry_prix.insert(0, prix)
    
    def valider_formulaire(self):
        """Valider les données du formulaire"""
        code = self.combo_code.get()
        if not code or code == "Aucun article":
            messagebox.showwarning("Attention", "Veuillez sélectionner un article")
            return False
        
        unite = self.combo_unite.get()
        if not unite or unite == "Aucune unité":
            messagebox.showwarning("Attention", "Veuillez sélectionner une unité")
            return False
        
        prix_str = self.entry_prix.get().strip()
        if not prix_str:
            messagebox.showwarning("Attention", "Veuillez saisir un prix")
            return False
        
        try:
            prix = float(prix_str.replace(',', '.'))
            if prix < 0:
                messagebox.showwarning("Attention", "Le prix ne peut pas être négatif")
                return False
        except ValueError:
            messagebox.showwarning("Attention", "Le prix doit être un nombre valide")
            return False
        
        return True
    
    def enregistrer(self):
        """Enregistrer un nouveau prix"""
        if not self.valider_formulaire():
            return
    
        try:
            # 1. Établir la connexion d'abord
            conn = self.connect_db()
            if not conn:
                return
            cur = conn.cursor()

            # 2. Récupérer les données du formulaire
            code = self.combo_code.get()
            idarticle = self.articles_dict[code][0]
            idunite = self.articles_dict[code][3]
            prix = float(self.entry_prix.get().replace(',', '.'))

            # --- AJOUT DE LA SYNCHRONISATION AUTOMATIQUE ---
            # Utilisation de 'cur' (le curseur que nous venons de créer) au lieu de 'self.cursor'
            cur.execute("""
                SELECT setval(pg_get_serial_sequence('tb_prix', 'id'), 
                         COALESCE((SELECT MAX(id) FROM tb_prix), 0) + 1, 
                         false);
            """)
            # Pas besoin de self.conn.commit(), on utilisera conn.commit() à la fin
        
            # 3. Insertion du nouveau prix
            cur.execute("""
                INSERT INTO tb_prix (idarticle, idunite, prix, dateregistre, iduser, deleted)
                VALUES (%s, %s, %s, %s, %s, 0)
            """, (idarticle, idunite, prix, datetime.now(), self.iduser))
        
            # 4. Valider toutes les transactions d'un coup
            conn.commit()
        
            # 5. Nettoyage
            cur.close()
            conn.close()
        
            messagebox.showinfo("Succès", "Prix enregistré avec succès")
            self.charger_historique(idarticle)
            self.nouveau()
        
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement: {str(e)}")
    
    def modifier(self):
        """Modifier un prix existant"""
        if not self.selected_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner un prix à modifier")
            return
        
        if not self.valider_formulaire():
            return
        
        try:
            code = self.combo_code.get()
            idarticle = self.articles_dict[code][0]
            idunite = self.articles_dict[code][3]  # CORRECTION: Récupérer idunite depuis articles_dict
            prix = float(self.entry_prix.get().replace(',', '.'))
            
            conn = self.connect_db()
            if not conn:
                return
            cur = conn.cursor()
            cur.execute("""
                UPDATE tb_prix 
                SET prix = %s, idunite = %s, dateregistre = %s
                WHERE id = %s
            """, (prix, idunite, datetime.now(), self.selected_id))
            
            conn.commit()
            cur.close()
            conn.close()
            
            messagebox.showinfo("Succès", "Prix modifié avec succès")
            self.charger_historique(idarticle)
            self.nouveau()
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la modification: {str(e)}")
    
    def supprimer(self):
        """Supprimer un prix (soft delete)"""
        if not self.selected_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner un prix à supprimer")
            return
        
        reponse = messagebox.askyesno(
            "Confirmation", 
            "Êtes-vous sûr de vouloir supprimer ce prix ?"
        )
        
        if not reponse:
            return
        
        try:
            code = self.combo_code.get()
            idarticle = self.articles_dict[code][0]
            
            conn = self.connect_db()
            if not conn:
                return
            cur = conn.cursor()
            cur.execute("UPDATE tb_prix SET deleted = 1 WHERE id = %s", (self.selected_id,))
            
            conn.commit()
            cur.close()
            conn.close()
            
            messagebox.showinfo("Succès", "Prix supprimé avec succès")
            self.charger_historique(idarticle)
            self.nouveau()
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la suppression: {str(e)}")
    
    def nouveau(self):
        """Réinitialiser le formulaire"""
        self.selected_id = None
        self.entry_prix.delete(0, "end")
        if self.combo_code.cget("values"):
            self.combo_code.set(self.combo_code.cget("values")[0])
            self.on_code_selected(self.combo_code.get())


# Exemple d'utilisation
if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    root = ctk.CTk()
    root.title("Gestion des Prix")
    root.geometry("700x650")
    
    # ID de l'utilisateur connecté (à récupérer depuis votre système d'authentification)
    iduser = 1
    
    app = PagePrixSaisie(root, iduser)
    app.pack(fill="both", expand=True)
    
    root.mainloop()