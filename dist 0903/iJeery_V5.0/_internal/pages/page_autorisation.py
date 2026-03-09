import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime
import tkinter as tk
import os
import json
from resource_utils import get_config_path, safe_file_read


class PageAutorisation(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        
        # Connexion à la base de données
        self.conn = self.connect_db()
        self.cursor = None
        
        if self.conn:
            self.cursor = self.conn.cursor()
        
        self.selected_fonction_id = None
        self.setup_ui()
        self.configure_style()
        
    def connect_db(self):
        """Établit la connexion à la base de données à partir du fichier config.json"""
        try:
            # Déterminer le répertoire parent si nécessaire
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = get_config_path('config.json')
            
            if not os.path.exists(config_path):
                config_path = 'config.json'
                
            if not os.path.exists(config_path):
                messagebox.showerror("Erreur", "Fichier config.json manquant.")
                return None
                 
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                db_config = config['database']

            conn = psycopg2.connect(
                host=db_config['host'],
                user=db_config['user'],
                password=db_config['password'],
                database=db_config['database'],
                port=db_config['port']  
            )
            print("Connection to the database successful!")
            return conn
        except Exception as err:
            messagebox.showerror("Erreur de connexion", f"Détails : {err}")
            return None
    
    def configure_style(self):
        # Configuration du style pour les Treeview
        style = ttk.Style()
        style.configure("Treeview",
                       background="#FFFFFF",
                       foreground="#000000",
                       rowheight=22,
                       fieldbackground="#FFFFFF",
                       borderwidth=0,
                       font=('Segoe UI', 8))
        style.configure("Treeview.Heading",
                       background="#E8E8E8",
                       foreground="#000000",
                       font=('Segoe UI', 8, 'bold'))
        style.map("Treeview",
                 background=[('selected', '#2ecc71')],
                 foreground=[('selected', '#ffffff')])
                 
        # Configuration des tags pour les couleurs Oui/Non
        if hasattr(self, 'menu_tree'):
            self.menu_tree.tag_configure('oui', foreground='#27ae60')  # Vert
            self.menu_tree.tag_configure('non', foreground='#c0392b')  # Rouge
            self.menu_tree.tag_configure('row_even', background='#FFFFFF')
            self.menu_tree.tag_configure('row_odd', background='#F1E4D8')
        if hasattr(self, 'fonction_tree'):
            self.fonction_tree.tag_configure('row_even', background='#FFFFFF')
            self.fonction_tree.tag_configure('row_odd', background='#F1E4D8')

    def _refresh_fonction_tree_alternating(self):
        for idx, item in enumerate(self.fonction_tree.get_children()):
            self.fonction_tree.item(item, tags=("row_even" if idx % 2 == 0 else "row_odd",))

    def _refresh_menu_tree_alternating(self):
        for idx, item in enumerate(self.menu_tree.get_children()):
            current = list(self.menu_tree.item(item).get('tags', ()))
            current = [t for t in current if t not in ('row_even', 'row_odd')]
            row_tag = "row_even" if idx % 2 == 0 else "row_odd"
            self.menu_tree.item(item, tags=tuple([row_tag] + current))

    def setup_ui(self):
        self.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Frame principal avec deux colonnes
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Frame gauche pour la liste des fonctions
        left_frame = ctk.CTkFrame(main_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        # Frame de recherche pour les fonctions
        search_frame_fonction = ctk.CTkFrame(left_frame)
        search_frame_fonction.pack(fill="x", pady=5)
        ctk.CTkLabel(search_frame_fonction, text="Rechercher une fonction:").pack(side="left", padx=5)
        self.search_fonction = ctk.CTkEntry(search_frame_fonction)
        self.search_fonction.pack(side="left", fill="x", expand=True, padx=5)
        self.search_fonction.bind("<KeyRelease>", self.filter_fonctions)
        
        # Label pour les fonctions
        ctk.CTkLabel(left_frame, text="Liste des fonctions", 
                    font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")).pack(pady=5)
        
        # Treeview pour les fonctions
        self.fonction_tree = ttk.Treeview(left_frame, columns=("ID", "Fonction"), show="headings")
        self.fonction_tree.heading("ID", text="ID")
        self.fonction_tree.heading("Fonction", text="Fonction")
        self.fonction_tree.column("ID", width=50)
        self.fonction_tree.column("Fonction", width=200)
        self.fonction_tree.pack(fill="both", expand=True, pady=5)
        
        # Scrollbar pour fonction_tree
        scrollbar_fonction = ttk.Scrollbar(left_frame, orient="vertical", command=self.fonction_tree.yview)
        scrollbar_fonction.pack(side="right", fill="y")
        self.fonction_tree.configure(yscrollcommand=scrollbar_fonction.set)
        
        # Frame droite pour les menus et autorisations
        right_frame = ctk.CTkFrame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        
        # Frame de recherche pour les menus
        search_frame_menu = ctk.CTkFrame(right_frame)
        search_frame_menu.pack(fill="x", pady=5)
        ctk.CTkLabel(search_frame_menu, text="Rechercher un menu:").pack(side="left", padx=5)
        self.search_menu = ctk.CTkEntry(search_frame_menu)
        self.search_menu.pack(side="left", fill="x", expand=True, padx=5)
        self.search_menu.bind("<KeyRelease>", self.filter_menus)
        
        # Frame pour les boutons de contrôle
        control_frame = ctk.CTkFrame(right_frame)
        control_frame.pack(fill="x", pady=5)
        
        # Boutons Tout cocher/décocher
        ctk.CTkButton(control_frame, 
                     text="Tout cocher",
                     command=lambda: self.toggle_all_checkboxes(True),
                     fg_color="#3498db",
                     hover_color="#2980b9",
                     width=120).pack(side="left", padx=5)
                     
        ctk.CTkButton(control_frame,
                     text="Tout décocher",
                     command=lambda: self.toggle_all_checkboxes(False),
                     fg_color="#e74c3c",
                     hover_color="#c0392b",
                     width=120).pack(side="left", padx=5)
        
        # Label pour les menus
        ctk.CTkLabel(right_frame, text="Autorisations des menus",
                    font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")).pack(pady=5)
        
        # Frame pour le treeview des menus
        menu_frame = ctk.CTkFrame(right_frame)
        menu_frame.pack(fill="both", expand=True)
        
        # Treeview pour les menus avec checkbox
        self.menu_tree = ttk.Treeview(menu_frame, columns=("ID", "Menu", "Autorisation"), show="headings")
        self.menu_tree.heading("ID", text="ID")
        self.menu_tree.heading("Menu", text="Menu")
        self.menu_tree.heading("Autorisation", text="Autorisation")
        self.menu_tree.column("ID", width=50)
        self.menu_tree.column("Menu", width=200)
        self.menu_tree.column("Autorisation", width=100)
        self.menu_tree.pack(fill="both", expand=True, pady=5)
        
        # Scrollbar pour menu_tree
        scrollbar_menu = ttk.Scrollbar(menu_frame, orient="vertical", command=self.menu_tree.yview)
        scrollbar_menu.pack(side="right", fill="y")
        self.menu_tree.configure(yscrollcommand=scrollbar_menu.set)
        
        # Bouton de sauvegarde avec style amélioré
        save_frame = ctk.CTkFrame(right_frame)
        save_frame.pack(fill="x", pady=10)
        self.save_button = ctk.CTkButton(save_frame,
                                       text="Enregistrer les autorisations",
                                       command=self.save_autorisations,
                                       fg_color="#2ecc71",
                                       hover_color="#27ae60",
                                       height=40,
                                       font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"))
        self.save_button.pack(pady=10, padx=20, fill="x")
        
        # Stockage des données non filtrées
        self.all_fonctions = []
        self.all_menus = []
        
        # Charger les données SEULEMENT si la connexion existe
        if self.conn and self.cursor:
            self.load_fonctions()
            self.fonction_tree.bind("<<TreeviewSelect>>", self.on_fonction_select)
            self.menu_tree.bind("<ButtonRelease-1>", self.on_checkbox_click)

    def filter_fonctions(self, event=None):
        """Filtre la liste des fonctions selon le terme de recherche"""
        if not hasattr(self, 'all_fonctions'):
            return
            
        search_term = self.search_fonction.get().lower()
        self.fonction_tree.delete(*self.fonction_tree.get_children())
        
        for fonction in self.all_fonctions:
            if search_term in fonction[1].lower():
                self.fonction_tree.insert("", "end", values=fonction)
        self._refresh_fonction_tree_alternating()

    def filter_menus(self, event=None):
        """Filtre la liste des menus selon le terme de recherche"""
        if not hasattr(self, 'all_menus'):
            return
            
        search_term = self.search_menu.get().lower()
        self.menu_tree.delete(*self.menu_tree.get_children())
        
        for menu in self.all_menus:
            if search_term in menu[1].lower():
                item = self.menu_tree.insert("", "end", values=menu)
                # Appliquer le tag approprié
                tag = 'oui' if menu[2] == 'Oui' else 'non'
                self.menu_tree.item(item, tags=(tag,))
        self._refresh_menu_tree_alternating()

    def toggle_all_checkboxes(self, state):
        """Coche ou décoche toutes les autorisations"""
        for item in self.menu_tree.get_children():
            values = list(self.menu_tree.item(item)['values'])
            values[2] = "Oui" if state else "Non"
            self.menu_tree.item(item, values=values)
            # Mettre à jour le tag
            tag = 'oui' if state else 'non'
            self.menu_tree.item(item, tags=(tag,))
        self._refresh_menu_tree_alternating()

    def load_fonctions(self):
        """Charge la liste des fonctions depuis la base de données"""
        if not self.cursor:
            messagebox.showerror("Erreur", "Pas de connexion à la base de données.")
            return
            
        try:
            self.cursor.execute("SELECT idfonction, designationfonction FROM tb_fonction ORDER BY designationfonction")
            self.all_fonctions = self.cursor.fetchall()
            
            # Vider le treeview
            for item in self.fonction_tree.get_children():
                self.fonction_tree.delete(item)
                
            # Ajouter les nouvelles données
            for row in self.all_fonctions:
                self.fonction_tree.insert("", "end", values=row)
            self._refresh_fonction_tree_alternating()
                
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des fonctions : {err}")

    def load_menus(self, fonction_id):
        """Charge la liste des menus et leurs autorisations pour une fonction donnée"""
        if not self.cursor:
            messagebox.showerror("Erreur", "Pas de connexion à la base de données.")
            return
            
        try:
            # Effacer les menus existants
            for item in self.menu_tree.get_children():
                self.menu_tree.delete(item)
                
            # Charger tous les menus et vérifier les autorisations
            self.cursor.execute("""
                SELECT m.id, m.designationmenu,
                    CASE WHEN a.id IS NOT NULL THEN 'Oui' ELSE 'Non' END as autorise
                FROM tb_menu m
                LEFT JOIN tb_autorisation a ON m.id = a.idmenu AND a.idfonction = %s
                ORDER BY m.designationmenu
            """, (fonction_id,))
            
            self.all_menus = []
            for row in self.cursor.fetchall():
                self.all_menus.append(row)
                item = self.menu_tree.insert("", "end", values=row)
                # Appliquer le tag approprié
                tag = 'oui' if row[2] == 'Oui' else 'non'
                self.menu_tree.item(item, tags=(tag,))
            self._refresh_menu_tree_alternating()
                
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des menus : {err}")

    def on_fonction_select(self, event):
        """Gestionnaire de sélection d'une fonction"""
        selected = self.fonction_tree.selection()
        if not selected:
            return
            
        item = self.fonction_tree.item(selected[0])
        self.selected_fonction_id = item['values'][0]
        self.load_menus(self.selected_fonction_id)
        # Réinitialiser la recherche
        self.search_menu.delete(0, "end")

    def on_checkbox_click(self, event):
        """Gestionnaire de clic sur les autorisations (simulation de checkbox)"""
        region = self.menu_tree.identify_region(event.x, event.y)
        if region == "cell":
            column = self.menu_tree.identify_column(event.x)
            if column == "#3":  # Colonne Autorisation
                item = self.menu_tree.identify_row(event.y)
                if item:  # Vérifier que l'item existe
                    current_value = self.menu_tree.item(item)['values'][2]
                    new_value = "Non" if current_value == "Oui" else "Oui"
                    values = list(self.menu_tree.item(item)['values'])
                    values[2] = new_value
                    self.menu_tree.item(item, values=values)
                    # Mettre à jour le tag
                    tag = 'oui' if new_value == 'Oui' else 'non'
                    self.menu_tree.item(item, tags=(tag,))
                    self._refresh_menu_tree_alternating()

    def save_autorisations(self):
        """Sauvegarde les autorisations en base de données"""
        if not self.selected_fonction_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner une fonction.")
            return
            
        if not self.cursor:
            messagebox.showerror("Erreur", "Pas de connexion à la base de données.")
            return
            
        try:
            # Supprimer les autorisations existantes pour cette fonction
            self.cursor.execute("DELETE FROM tb_autorisation WHERE idfonction = %s", 
                              (self.selected_fonction_id,))
            
            # Insérer les nouvelles autorisations
            for item in self.menu_tree.get_children():
                values = self.menu_tree.item(item)['values']
                menu_id = values[0]
                is_authorized = values[2] == "Oui"
                
                if is_authorized:
                    self.cursor.execute("""
                        INSERT INTO tb_autorisation (idfonction, idmenu)
                        VALUES (%s, %s)
                    """, (self.selected_fonction_id, menu_id))
            
            self.conn.commit()
            messagebox.showinfo("Succès", "Autorisations enregistrées avec succès!")
            
        except psycopg2.Error as err:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement : {err}")

    def __del__(self):
        """Destructeur pour fermer proprement les connexions"""
        if hasattr(self, 'cursor') and self.cursor:
            self.cursor.close()
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

# Pour tester la page individuellement
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    
    app = ctk.CTk()
    app.title("Gestion des Autorisations")
    app.geometry("1000x600")

    page = PageAutorisation(app)
    app.mainloop()
