import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import json
from datetime import datetime, timedelta
from resource_utils import get_config_path, safe_file_read


class PageGestionPeremption(ctk.CTkFrame):
    def __init__(self, parent, iduser=1):
        super().__init__(parent)
        self.iduser = iduser
        
        self.setup_ui()
        self.charger_donnees()

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
        except Exception as e:
            messagebox.showerror("Erreur de connexion", f"Erreur : {e}")
            return None

    def setup_ui(self):
        # Titre de la page
        self.titre = ctk.CTkLabel(self, text="🛡️ Suivi de Péremption par Article", 
                                 font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"))
        self.titre.pack(pady=15)

        # Barre d'outils et recherche
        frame_outils = ctk.CTkFrame(self)
        frame_outils.pack(fill="x", padx=20, pady=5)

        # Champ de recherche
        frame_recherche = ctk.CTkFrame(frame_outils, fg_color="transparent")
        frame_recherche.pack(side="left", padx=10, pady=10)
        
        ctk.CTkLabel(frame_recherche, text="🔍 Rechercher:", font=ctk.CTkFont(family="Segoe UI", size=12)).pack(side="left", padx=5)
        
        self.entry_recherche = ctk.CTkEntry(frame_recherche, placeholder_text="Code ou désignation d'article", width=250)
        self.entry_recherche.pack(side="left", padx=5)
        
        # Timer pour debounce de la recherche
        self.search_timer = None
        self.entry_recherche.bind("<KeyRelease>", self.on_search_change)

        btn_refresh = ctk.CTkButton(frame_outils, text="🔄 Actualiser", 
                                   command=self.charger_donnees,
                                   fg_color="#2e7d32", hover_color="#1b5e20",
                                   width=120)
        btn_refresh.pack(side="left", padx=10, pady=10)

        # Légende visuelle
        legend_frame = ctk.CTkFrame(frame_outils, fg_color="transparent")
        legend_frame.pack(side="right", padx=10)
        
        ctk.CTkLabel(legend_frame, text="Rouge: Périmé", text_color="#e53935", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).pack(side="right", padx=10)
        ctk.CTkLabel(legend_frame, text="Orange: < 1 mois", text_color="#fb8c00", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).pack(side="right", padx=10)
        ctk.CTkLabel(legend_frame, text="Vert: < 2 mois", text_color="#43a047", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).pack(side="right", padx=10)

        # Conteneur pour le tableau avec scrollbar horizontal
        frame_container = ctk.CTkFrame(self)
        frame_container.pack(fill="both", expand=True, padx=20, pady=10)

        # Tableau des péremptions (structure dynamique)
        self.tree = ttk.Treeview(frame_container, show="tree headings", height=15)
        
        # Scrollbars
        scrollbar_y = ttk.Scrollbar(frame_container, orient="vertical", command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(frame_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        
        frame_container.grid_rowconfigure(0, weight=1)
        frame_container.grid_columnconfigure(0, weight=1)

        # Configuration des tags de couleur
        self.tree.tag_configure('perime', foreground="#e53935", font=("Arial", 9, "bold"))
        self.tree.tag_configure('urgent', foreground="#fb8c00", font=("Arial", 9, "bold"))
        self.tree.tag_configure('proche', foreground="#43a047", font=("Arial", 9, "bold"))
        self.tree.tag_configure('normal', foreground="#000000")

        # Binding pour le double-clic
        self.tree.bind("<Double-Button-1>", self.on_double_click)

        # Dictionnaire pour stocker les données des cellules
        self.cellules_data = {}

    def get_all_data_optimized(self, cursor, terme_recherche=""):
        """Récupère toutes les données en une seule requête optimisée"""
        query = """
            WITH stock_calcul AS (
                SELECT 
                    u.idarticle,
                    u.idunite,
                    COALESCE(SUM(l.qtlivrefrs), 0) - 
                    COALESCE((SELECT SUM(v.qtvente) FROM tb_ventedetail v 
                              WHERE v.idarticle = u.idarticle AND v.idunite = u.idunite), 0) -
                    COALESCE((SELECT SUM(s.qtsortie) FROM tb_sortiedetail s 
                              WHERE s.idarticle = u.idarticle AND s.idunite = u.idunite), 0) as stock_actuel
                FROM tb_unite u
                LEFT JOIN tb_livraisonfrs l ON u.idarticle = l.idarticle AND u.idunite = l.idunite
                WHERE u.niveau = (SELECT MAX(niveau) FROM tb_unite u2 WHERE u2.idarticle = u.idarticle)
                GROUP BY u.idarticle, u.idunite
            ),
            peremptions AS (
                SELECT 
                    l.idarticle,
                    l.idunite,
                    l.dateperemption,
                    l.qtlivrefrs,
                    l.idlivfrs,
                    ROW_NUMBER() OVER (PARTITION BY l.idarticle, l.idunite ORDER BY l.dateperemption ASC) as rang
                FROM tb_livraisonfrs l
                WHERE l.dateperemption IS NOT NULL
            )
            SELECT 
                u.codearticle,
                a.designation,
                u.designationunite,
                a.idarticle,
                u.idunite,
                sc.stock_actuel,
                p.dateperemption,
                p.qtlivrefrs,
                p.idlivfrs,
                p.rang
            FROM tb_unite u
            JOIN tb_article a ON u.idarticle = a.idarticle
            JOIN stock_calcul sc ON u.idarticle = sc.idarticle AND u.idunite = sc.idunite
            LEFT JOIN peremptions p ON u.idarticle = p.idarticle AND u.idunite = p.idunite
            WHERE u.niveau = (SELECT MAX(niveau) FROM tb_unite u2 WHERE u2.idarticle = u.idarticle)
            AND sc.stock_actuel > 0
            AND p.dateperemption IS NOT NULL
        """
        
        if terme_recherche:
            query += """ AND (
                LOWER(u.codearticle) LIKE LOWER(%s) 
                OR LOWER(a.designation) LIKE LOWER(%s)
            )
            """
            cursor.execute(query + " ORDER BY u.codearticle, p.dateperemption", 
                          (f'%{terme_recherche}%', f'%{terme_recherche}%'))
        else:
            cursor.execute(query + " ORDER BY u.codearticle, p.dateperemption")
        
        return cursor.fetchall()

    def on_search_change(self, event):
        """Gère le changement dans le champ de recherche avec debounce"""
        # Annuler le timer précédent s'il existe
        if self.search_timer:
            self.after_cancel(self.search_timer)
        
        # Créer un nouveau timer pour exécuter la recherche après 500ms
        self.search_timer = self.after(500, self.charger_donnees)

    def charger_donnees(self):
        """Charge les données de manière optimisée"""
        # Afficher un indicateur de chargement
        self.titre.configure(text="🛡️ Suivi de Péremption par Article - Chargement...")
        self.update()
        
        # Nettoyer le treeview
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        self.cellules_data = {}

        conn = self.connect_db()
        if not conn: 
            self.titre.configure(text="🛡️ Suivi de Péremption par Article")
            return

        try:
            cursor = conn.cursor()
            
            # Récupérer le terme de recherche
            terme_recherche = self.entry_recherche.get().strip()
            
            # Récupérer toutes les données en une seule requête
            resultats = self.get_all_data_optimized(cursor, terme_recherche)
            
            if not resultats:
                self.titre.configure(text="🛡️ Suivi de Péremption par Article - Aucun article avec péremption")
                return
            
            # Organiser les données par article
            articles_dict = {}
            
            for row in resultats:
                code_art, design_art, design_unite, id_art, id_uni, stock_actuel, date_peremp, qt_livree, id_livraison, rang = row
                
                key = f"{id_art}_{id_uni}"
                
                if key not in articles_dict:
                    articles_dict[key] = {
                        'code': code_art,
                        'article': design_art,
                        'unite': design_unite,
                        'stock': stock_actuel,
                        'idarticle': id_art,
                        'idunite': id_uni,
                        'dates': []
                    }
                
                if date_peremp:
                    articles_dict[key]['dates'].append({
                        'date': date_peremp,
                        'qt': qt_livree,
                        'id_livraison': id_livraison
                    })
            
            # Filtrer les articles où stock >= quantité totale en péremption
            articles_valides = []
            for key, art in articles_dict.items():
                qt_total_peremp = sum([d['qt'] for d in art['dates']])
                if art['stock'] >= qt_total_peremp:
                    articles_valides.append(art)
            
            if not articles_valides:
                self.titre.configure(text="🛡️ Suivi de Péremption par Article - Aucun article valide")
                return
            
            # Trouver le nombre maximum de dates
            max_dates = max([len(art['dates']) for art in articles_valides])
            
            # Configurer les colonnes
            colonnes = ["code", "article", "unite", "stock"]
            colonnes += [f"date_peremp_{i+1}" for i in range(max_dates)]
            
            self.tree["columns"] = colonnes
            self.tree.column("#0", width=0, stretch=False)
            
            # Configurer les en-têtes
            self.tree.heading("code", text="Code Article")
            self.tree.heading("article", text="Article")
            self.tree.heading("unite", text="Unité")
            self.tree.heading("stock", text="Stock Actuel")
            
            for i in range(max_dates):
                self.tree.heading(f"date_peremp_{i+1}", text=f"Péremption {i+1}")
            
            # Configurer les largeurs
            self.tree.column("code", width=120, anchor="center")
            self.tree.column("article", width=250, anchor="w")
            self.tree.column("unite", width=100, anchor="center")
            self.tree.column("stock", width=100, anchor="center")
            
            for i in range(max_dates):
                self.tree.column(f"date_peremp_{i+1}", width=150, anchor="center")

            # Insérer les données
            aujourdhui = datetime.now().date()
            un_mois = aujourdhui + timedelta(days=30)
            deux_mois = aujourdhui + timedelta(days=60)
            
            for art in articles_valides:
                values = [
                    art['code'],
                    art['article'],
                    art['unite'],
                    f"{art['stock']:,.2f}".replace(',', ' ').replace('.', ',')
                ]
                
                couleurs_cellules = []
                for i, date_info in enumerate(art['dates']):
                    date_peremp = date_info['date']
                    qt_livree = date_info['qt']
                    id_livraison = date_info['id_livraison']
                    
                    cell_value = f"{date_peremp.strftime('%d/%m/%Y')}\n({qt_livree:,.2f})".replace(',', ' ').replace('.', ',')
                    values.append(cell_value)
                    
                    # Déterminer la couleur
                    if date_peremp <= aujourdhui:
                        couleur = 'perime'
                    elif date_peremp <= un_mois:
                        couleur = 'urgent'
                    elif date_peremp <= deux_mois:
                        couleur = 'proche'
                    else:
                        couleur = 'normal'
                    
                    couleurs_cellules.append(couleur)
                    
                    # Stocker les données de la cellule
                    cell_key = f"{art['idarticle']}_{art['idunite']}_{i}"
                    self.cellules_data[cell_key] = {
                        'id_livraison': id_livraison,
                        'date_peremp': date_peremp,
                        'qt_livree': qt_livree,
                        'idarticle': art['idarticle'],
                        'idunite': art['idunite'],
                        'code': art['code'],
                        'article': art['article']
                    }
                
                # Compléter avec des valeurs vides
                while len(values) < len(colonnes):
                    values.append("")
                
                # Déterminer le tag global
                if 'perime' in couleurs_cellules:
                    tag = 'perime'
                elif 'urgent' in couleurs_cellules:
                    tag = 'urgent'
                elif 'proche' in couleurs_cellules:
                    tag = 'proche'
                else:
                    tag = 'normal'
                
                # Insérer la ligne
                item_id = self.tree.insert("", "end", values=values, tags=(tag,))
                
                # Mettre à jour les données avec item_id
                for i in range(len(art['dates'])):
                    cell_key = f"{art['idarticle']}_{art['idunite']}_{i}"
                    if cell_key in self.cellules_data:
                        self.cellules_data[cell_key]['item_id'] = item_id
                        self.cellules_data[cell_key]['col_index'] = i + 4

            self.titre.configure(text=f"🛡️ Suivi de Péremption par Article - {len(articles_valides)} articles")

        except Exception as e:
            messagebox.showerror("Erreur de chargement", f"Erreur SQL : {e}")
            self.titre.configure(text="🛡️ Suivi de Péremption par Article - Erreur")
        finally:
            cursor.close()
            conn.close()

    def on_double_click(self, event):
        """Gère le double-clic sur une cellule"""
        # Identifier la cellule cliquée
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        
        column = self.tree.identify_column(event.x)
        row_id = self.tree.identify_row(event.y)
        
        if not row_id or not column:
            return
        
        # Extraire l'index de la colonne
        col_index = int(column.replace('#', '')) - 1
        
        # Vérifier si c'est une colonne de date de péremption (index >= 4)
        if col_index < 4:
            return
        
        # Récupérer les valeurs de la ligne
        values = self.tree.item(row_id)['values']
        
        if col_index >= len(values) or not values[col_index]:
            return
        
        # Trouver les données de cette cellule
        cell_data = None
        for key, data in self.cellules_data.items():
            if data.get('item_id') == row_id and data.get('col_index') == col_index:
                cell_data = data
                break
        
        if not cell_data:
            return
        
        # Ouvrir la fenêtre de confirmation
        self.ouvrir_fenetre_suppression(cell_data, row_id)

    def ouvrir_fenetre_suppression(self, cell_data, row_id):
        """Ouvre une fenêtre pour confirmer la suppression de la date de péremption"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Gestion de la péremption")
        dialog.geometry("500x300")
        dialog.transient(self)
        dialog.grab_set()
        
        # Centrer la fenêtre
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialog.winfo_screenheight() // 2) - (300 // 2)
        dialog.geometry(f"500x300+{x}+{y}")
        
        # Contenu
        frame_info = ctk.CTkFrame(dialog)
        frame_info.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(frame_info, text="Informations sur la péremption", 
                     font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold")).pack(pady=10)
        
        info_text = f"""
Article: {cell_data['code']} - {cell_data['article']}

Date de péremption: {cell_data['date_peremp'].strftime('%d/%m/%Y')}
Quantité livrée: {cell_data['qt_livree']:,.2f}

Cette ligne a été vérifiée ou réglée ?
Souhaitez-vous la supprimer de la liste de suivi ?
        """
        
        ctk.CTkLabel(frame_info, text=info_text, 
                     font=ctk.CTkFont(family="Segoe UI", size=12),
                     justify="left").pack(pady=20)
        
        # Boutons
        frame_buttons = ctk.CTkFrame(dialog, fg_color="transparent")
        frame_buttons.pack(pady=10)
        
        def supprimer_ligne():
            if messagebox.askyesno("Confirmation", 
                                   "Voulez-vous vraiment supprimer cette date de péremption de la liste de suivi ?\n\n"
                                   "Note: Cela supprimera la date de péremption de la livraison dans la base de données."):
                conn = self.connect_db()
                if conn:
                    try:
                        cursor = conn.cursor()
                        # Mettre à NULL la date de péremption dans tb_livraisonfrs
                        cursor.execute("""
                            UPDATE tb_livraisonfrs 
                            SET dateperemption = NULL 
                            WHERE idlivraisonfrs = %s
                        """, (cell_data['id_livraison'],))
                        conn.commit()
                        
                        messagebox.showinfo("Succès", "La date de péremption a été supprimée avec succès.")
                        dialog.destroy()
                        self.charger_donnees()  # Recharger les données
                        
                    except Exception as e:
                        conn.rollback()
                        messagebox.showerror("Erreur", f"Erreur lors de la suppression : {e}")
                    finally:
                        cursor.close()
                        conn.close()
        
        btn_supprimer = ctk.CTkButton(frame_buttons, text="✓ Supprimer de la liste", 
                                      command=supprimer_ligne,
                                      fg_color="#e53935", hover_color="#c62828",
                                      width=180)
        btn_supprimer.pack(side="left", padx=10)
        
        btn_annuler = ctk.CTkButton(frame_buttons, text="✗ Annuler", 
                                    command=dialog.destroy,
                                    fg_color="#757575", hover_color="#616161",
                                    width=180)
        btn_annuler.pack(side="left", padx=10)


if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("1200x700")
    app.title("Système de Gestion des Stocks - Suivi de Péremption")
    
    page = PageGestionPeremption(app)
    page.pack(fill="both", expand=True)
    
    app.mainloop()
