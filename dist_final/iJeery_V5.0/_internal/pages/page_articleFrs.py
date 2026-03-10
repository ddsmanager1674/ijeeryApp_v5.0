import customtkinter as ctk
import psycopg2
import json
import os
import sys
from tkinter import messagebox
from tkinter import ttk
from resource_utils import get_config_path, safe_file_read


# Configuration de base pour customtkinter
ctk.set_appearance_mode("Light")  
ctk.set_default_color_theme("blue")

# Définition des répertoires pour localiser config.json
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

class PageArticleFrs(ctk.CTkFrame):
    """
    Page d'affichage des fournisseurs d'un article avec connexion intégrée.
    """
    def __init__(self, master, initial_idarticle=None):
        super().__init__(master)
        
        self.initial_idarticle = initial_idarticle
        
        # Initialisation de la connexion
        self.conn = self.connect_db()
        
        # Configuration du layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) 
        
        # --- Cadre de Recherche (Row 0) ---
        self.frame_top = ctk.CTkFrame(self)
        self.frame_top.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.frame_top.columnconfigure(1, weight=1) 
        
        ctk.CTkLabel(self.frame_top, text="Code Article:").grid(row=0, column=0, padx=(10, 5), pady=10, sticky="w")
        self.entry_recherche = ctk.CTkEntry(self.frame_top, placeholder_text="Entrez le code article (ex: A001)")
        self.entry_recherche.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        
        self.btn_recherche = ctk.CTkButton(
            self.frame_top, 
            text="🔍 Rechercher", 
            command=self.ouvrir_recherche_article 
        )
        self.btn_recherche.grid(row=0, column=2, padx=10)
        
        # --- Cadre d'Informations Article (Row 1) ---
        self.frame_info = ctk.CTkFrame(self)
        self.frame_info.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.frame_info.columnconfigure((1, 3, 5), weight=1) 
        
        ctk.CTkLabel(self.frame_info, text="Code Article:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(self.frame_info, text="Nom Article:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(self.frame_info, text="Unité:").grid(row=0, column=4, padx=5, pady=5, sticky="w")

        self.lbl_code = ctk.CTkLabel(self.frame_info, text="N/A", text_color="blue")
        self.lbl_code.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        self.lbl_nom = ctk.CTkLabel(self.frame_info, text="N/A", text_color="blue")
        self.lbl_nom.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        
        self.lbl_unite = ctk.CTkLabel(self.frame_info, text="N/A", text_color="blue")
        self.lbl_unite.grid(row=0, column=5, padx=5, pady=5, sticky="w")

        # --- Cadre du Tableau (Row 2) ---
        self.scroll_frame_tableau = ctk.CTkScrollableFrame(self, label_text="Historique des Fournisseurs")
        self.scroll_frame_tableau.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="nsew")
        self.scroll_frame_tableau.columnconfigure((0, 1, 2, 3, 4), weight=1) 
        
        self.tableau_headers = [
            "Nom Fournisseur", "Référence", "Date", "Quantité", "Prix Unitaire"
        ]
        
        for i, header in enumerate(self.tableau_headers):
            lbl = ctk.CTkLabel(self.scroll_frame_tableau, text=header, 
                               font=ctk.CTkFont(family="Segoe UI", weight="bold"), 
                               fg_color="gray50", corner_radius=5)
            lbl.grid(row=0, column=i, padx=2, pady=2, sticky="ew")

        self.data_start_row = 1
        self.afficher_donnees_tableau([])
        
        if self.initial_idarticle:
            self.charger_article_initial()

    def connect_db(self):
        """Établit la connexion à la base de données à partir du fichier config.json"""
        try:
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
            return conn
        except Exception as err:
            messagebox.showerror("Erreur de connexion", f"Détails : {err}")
            return None

    def get_article_info(self, code_article):
        """Récupère les informations de base de l'article."""
        if not self.conn: return None
        sql_query = """
            SELECT tu.codearticle, ta.designation, tu.designationunite
            FROM tb_unite tu
            JOIN tb_article ta ON tu.idarticle = ta.idarticle
            WHERE tu.codearticle = %s;
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql_query, (code_article,))
            result = cursor.fetchone()
            return {"code": result[0], "nom": result[1], "unite": result[2]} if result else None
        except Exception as e:
            print(f"Erreur info article: {e}")
            return None

    def get_fournisseurs_article(self, code_article):
        """Récupère l'historique des commandes/livraisons."""
        if not self.conn: return []
        sql_query = """
            SELECT tf.nomfrs, tlf.reflivfrs, tc.datecom, tcd.qtlivre, tcd.punitcmd            
            FROM tb_commandedetail tcd
            JOIN tb_commande tc ON tcd.idcom = tc.idcom
            JOIN tb_fournisseur tf ON tc.idfrs = tf.idfrs
            LEFT JOIN tb_livraisonfrs tlf ON tlf.idcom = tc.idcom
            JOIN tb_unite tu ON tcd.idarticle = tu.idarticle 
            WHERE tu.codearticle = %s 
            ORDER BY tc.datecom DESC;
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql_query, (code_article,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Erreur historique frs: {e}")
            return []

    def ouvrir_recherche_article(self):
        """Ouvre une fenêtre popup pour rechercher un article"""
        fenetre = ctk.CTkToplevel(self)
        fenetre.title("Sélectionner un Article")
        fenetre.geometry("700x450")
        fenetre.grab_set()

        search_frame = ctk.CTkFrame(fenetre)
        search_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(search_frame, text="Filtrer :").pack(side="left", padx=5)
        entry_search = ctk.CTkEntry(search_frame, placeholder_text="Tapez le nom de l'article...")
        entry_search.pack(side="left", fill="x", expand=True, padx=5)

        columns = ("code", "nom", "unite")
        tree = ttk.Treeview(fenetre, columns=columns, show="headings")
        tree.heading("code", text="Code Article")
        tree.heading("nom", text="Nom Article")
        tree.heading("unite", text="Unité")
        tree.pack(fill="both", expand=True, padx=10, pady=5)

        def actualiser_liste(event=None):
            for item in tree.get_children(): tree.delete(item)
            if not self.conn: return
            
            filtre = entry_search.get()
            cursor = self.conn.cursor()
            query = """
                SELECT tu.codearticle, ta.designation, tu.designationunite 
                FROM tb_unite tu 
                JOIN tb_article ta ON tu.idarticle = ta.idarticle
                WHERE ta.designation ILIKE %s OR tu.codearticle ILIKE %s
            """
            cursor.execute(query, (f'%{filtre}%', f'%{filtre}%'))
            for row in cursor.fetchall():
                tree.insert("", "end", values=row)

        def selectionner_et_fermer(event=None):
            item_sel = tree.selection()
            if item_sel:
                valeurs = tree.item(item_sel[0], "values")
                self.entry_recherche.delete(0, "end")
                self.entry_recherche.insert(0, valeurs[0])
                self.lancer_recherche()
                fenetre.destroy()

        entry_search.bind("<KeyRelease>", actualiser_liste)
        tree.bind("<Double-Button-1>", selectionner_et_fermer)
        actualiser_liste()

    def lancer_recherche(self):
        code_article = self.entry_recherche.get().strip().upper()
        if not code_article:
            messagebox.showwarning("Alerte", "Veuillez entrer un code article.")
            return

        info = self.get_article_info(code_article)
        if info:
            self.lbl_code.configure(text=info["code"])
            self.lbl_nom.configure(text=info["nom"])
            self.lbl_unite.configure(text=info["unite"])
            
            donnees = self.get_fournisseurs_article(code_article)
            self.afficher_donnees_tableau(donnees)
        else:
            messagebox.showerror("Non trouvé", "Article non trouvé.")
            self.afficher_donnees_tableau([])

    def afficher_donnees_tableau(self, donnees):
        for widget in self.scroll_frame_tableau.winfo_children():
            if int(widget.grid_info().get("row", 0)) >= self.data_start_row:
                widget.destroy()

        if not donnees:
            ctk.CTkLabel(self.scroll_frame_tableau, text="Aucune donnée trouvée.", text_color="gray").grid(
                row=self.data_start_row, column=0, columnspan=5, pady=10)
            return
            
        for i, row_data in enumerate(donnees):
            for j, cell_data in enumerate(row_data):
                text_display = str(cell_data)
                cell_anchor = "w"
                header = self.tableau_headers[j]
                
                if header == "Prix Unitaire" and cell_data is not None:
                    text_display = f"{float(cell_data):_.2f} Ar".replace('.', ',').replace('_', ' ')
                    cell_anchor = "e"
                elif header == "Quantité" and cell_data is not None:
                    text_display = f"{int(cell_data):_}".replace('_', ' ')
                    cell_anchor = "e"
                elif header == "Date" and cell_data:
                    text_display = cell_data.strftime("%d/%m/%Y")

                lbl = ctk.CTkLabel(self.scroll_frame_tableau, text=text_display, anchor=cell_anchor)
                lbl.grid(row=i + self.data_start_row, column=j, padx=2, pady=1, sticky="ew")
                lbl.configure(fg_color=("gray85", "gray17") if i % 2 == 0 else ("gray90", "gray12"))

    def charger_article_initial(self):
        self.lbl_code.configure(text=f"ID: {self.initial_idarticle}")
        self.lbl_nom.configure(text="Entrez le code pour l'historique")

class PageArticleFrsPopup(ctk.CTkToplevel):
    def __init__(self, master, initial_idarticle=None):
        super().__init__(master)
        self.title("Fournisseurs par Article")
        self.geometry("850x600")
        self.transient(master)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.page_content = PageArticleFrs(self, initial_idarticle=initial_idarticle)
        self.page_content.grid(row=0, column=0, sticky="nsew")

if __name__ == "__main__":
    app = ctk.CTk()
    app.withdraw()
    page = PageArticleFrsPopup(app, initial_idarticle="2")
    app.mainloop()