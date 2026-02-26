import customtkinter as ctk
from tkinter import messagebox, ttk
import psycopg2
import json
from resource_utils import get_config_path, safe_file_read



class DBConnector:
    """
    Connecteur de base de données pour les unités.
    Classe nécessaire pour l'import dans page_infoArticle.py
    """
    def __init__(self, db_conn=None):
        self.db_conn = db_conn
    
    @staticmethod
    def connect_db():
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

def synchroniser_sequence_unite(self):
        """Recale le compteur d'ID pour la table des unités"""
        conn = self.connect_db()
        if not conn: return
        try:
            cursor = conn.cursor()
            # Synchronise la séquence pour 'idunite'
            cursor.execute("""
                SELECT setval(pg_get_serial_sequence('tb_unite', 'idunite'), 
                              COALESCE((SELECT MAX(idunite) FROM tb_unite), 0) + 1, 
                              false);
            """)
            conn.commit()
            cursor.close()
        except Exception as e:
            print(f"Erreur de synchro sequence: {e}")
        finally:
            conn.close()

class PageUnite(ctk.CTkFrame):
    """
    Frame pour ajouter, modifier et supprimer des unités d'article.
    VERSION FRAME pour intégration dans page_infoArticle.py
    """
    def __init__(self, master, db_connector=None, initial_idarticle=None):
        super().__init__(master, fg_color="white")
        
        # Récupérer l'ID article
        self.id_article = initial_idarticle
        self.db_connector = db_connector
        
        if not self.id_article:
            # Message si pas d'article sélectionné
            error_frame = ctk.CTkFrame(self, fg_color="#fff3cd", corner_radius=10)
            error_frame.pack(pady=50, padx=20, fill="both", expand=True)
            ctk.CTkLabel(
                error_frame, 
                text="⚠️ Aucun article sélectionné",
                font=("Arial", 20, "bold"),
                text_color="#856404"
            ).pack(pady=20)
            return
        
        # Configuration de la grille
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(5, weight=1)

        # Titre
        self.label_title = ctk.CTkLabel(
            self, 
            text=f"📦 Unités pour Article ID: {self.id_article}", 
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#2c3e50"
        )
        self.label_title.grid(row=0, column=0, columnspan=3, padx=20, pady=(20, 10), sticky="ew")

        # --- Champs de Saisie ---

        # Désignation
        ctk.CTkLabel(self, text="Désignation :", text_color="#555").grid(row=1, column=0, padx=20, pady=5, sticky="w")
        self.entry_designation = ctk.CTkEntry(self, width=250, placeholder_text="Ex: Carton de 12")
        self.entry_designation.grid(row=1, column=1, padx=20, pady=5, sticky="ew")

        # Quantité (QtUnite)
        ctk.CTkLabel(self, text="Quantité :", text_color="#555").grid(row=2, column=0, padx=20, pady=5, sticky="w")
        self.entry_quantite = ctk.CTkEntry(self, width=250, placeholder_text="Ex: 12")
        self.entry_quantite.grid(row=2, column=1, padx=20, pady=5, sticky="ew")

        # Poids
        ctk.CTkLabel(self, text="Poids (kg) :", text_color="#555").grid(row=3, column=0, padx=20, pady=5, sticky="w")
        self.entry_poids = ctk.CTkEntry(self, width=250, placeholder_text="Ex: 5.5")
        self.entry_poids.grid(row=3, column=1, padx=20, pady=5, sticky="ew")

        # --- Boutons (Ligne 4) ---
        
        self.frame_buttons = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_buttons.grid(row=4, column=0, columnspan=3, padx=20, pady=10, sticky="ew")
        self.frame_buttons.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.btn_ajouter = ctk.CTkButton(
            self.frame_buttons, 
            text="➕ Ajouter", 
            command=self.ajouter_unite,
            fg_color="#28a745",
            hover_color="#218838"
        )
        self.btn_ajouter.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        
        self.btn_modifier = ctk.CTkButton(
            self.frame_buttons, 
            text="✏️ Modifier", 
            command=self.modifier_unite,
            fg_color="#ffc107",
            hover_color="#e0a800",
            text_color="#000"
        )
        self.btn_modifier.grid(row=0, column=1, padx=10, pady=5, sticky="ew") 
        
        self.btn_supprimer = ctk.CTkButton(
            self.frame_buttons, 
            text="🗑️ Supprimer", 
            command=self.supprimer_unite,
            fg_color="#dc3545",
            hover_color="#c82333"
        )
        self.btn_supprimer.grid(row=0, column=2, padx=10, pady=5, sticky="ew")

        # --- Treeview pour Afficher les Unités (Ligne 5) ---
        
        self.frame_treeview = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_treeview.grid(row=5, column=0, columnspan=3, padx=20, pady=(10, 20), sticky="nsew")
        self.frame_treeview.grid_columnconfigure(0, weight=1)
        self.frame_treeview.grid_rowconfigure(0, weight=1)
        
        # Configure le style des Treeviews
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#FFFFFF", foreground="#000000", fieldbackground="#FFFFFF", borderwidth=0, rowheight=22, font=('Segoe UI', 8))
        style.configure("Treeview.Heading", background="#E8E8E8", foreground="#000000", font=('Segoe UI', 8, 'bold'))

        # Personnaliser le style du Treeview
        style = ttk.Style()
        style.theme_use("default")
        
        style.configure("Treeview", 
                        background="#FFFFFF", 
                        foreground="#000000",
                        rowheight=22,
                        fieldbackground="#FFFFFF",
                        font=('Segoe UI', 8),
                        borderwidth=0)
        style.map('Treeview', background=[('selected', '#3b8ed4')])
        
        style.configure("Treeview.Heading", 
                        background="#E8E8E8", 
                        foreground="#000000", 
                        font=('Segoe UI', 8, 'bold'),
                        relief="flat")

        # Définition des colonnes
        columns = ("idunite", "designationunite", "niveau", "qtunite", "poids", "codearticle")
        self.tree = ttk.Treeview(self.frame_treeview, columns=columns, show='headings', height=12)
        
        # Définition des en-têtes et des largeurs
        self.tree.heading("idunite", text="ID Unité")
        self.tree.column("idunite", width=80, anchor='center')
        self.tree.heading("designationunite", text="Désignation")
        self.tree.column("designationunite", width=200, anchor='w')
        self.tree.heading("niveau", text="Niveau")
        self.tree.column("niveau", width=80, anchor='center')
        self.tree.heading("qtunite", text="Quantité")
        self.tree.column("qtunite", width=100, anchor='e')
        self.tree.heading("poids", text="Poids (kg)")
        self.tree.column("poids", width=100, anchor='e')
        self.tree.heading("codearticle", text="Code Article")
        self.tree.column("codearticle", width=150, anchor='center')

        # Scrollbar verticale
        scrollbar = ttk.Scrollbar(self.frame_treeview, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Placement des widgets
        self.tree.grid(row=0, column=0, sticky='nsew', padx=(0, 5), pady=0)
        scrollbar.grid(row=0, column=1, sticky='ns', padx=(0, 0), pady=0)

        # Lier l'événement de sélection
        self.tree.bind("<<TreeviewSelect>>", self.on_unite_select)

        # Charger les données au démarrage
        self.charger_unites()


    def connect_db(self):
        """Connexion à la base de données"""
        if self.db_connector:
            return DBConnector.connect_db()
        return DBConnector.connect_db()


    def charger_unites(self):
        """
        Charge les unités pour l'article courant dans le Treeview.
        """
        # Effacer les données existantes
        for item in self.tree.get_children():
            self.tree.delete(item)

        conn = self.connect_db()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            query = """
            SELECT 
                idunite, 
                designationunite, 
                niveau, 
                qtunite, 
                poids, 
                codearticle
            FROM 
                tb_unite
            WHERE 
                idarticle = %s AND deleted = 0
            ORDER BY 
                niveau
            """
            cursor.execute(query, (self.id_article,))
            records = cursor.fetchall()

            if not records:
                # Insérer un message si aucune unité
                self.tree.insert('', 'end', values=("", "Aucune unité trouvée", "", "", "", ""))
            else:
                for row in records:
                    display_row = (
                        row[0],  # idunite
                        row[1],  # designationunite
                        row[2],  # niveau
                        f"{row[3]:.2f}",  # qtunite
                        f"{row[4]:.2f}",  # poids
                        row[5]  # codearticle
                    )
                    self.tree.insert('', 'end', values=display_row, tags=('data',))
            
            cursor.close()

        except psycopg2.Error as e:
            messagebox.showerror("Erreur DB", f"Erreur lors du chargement des unités : {e}")
        finally:
            if conn:
                conn.close()


    def on_unite_select(self, event):
        """
        Charge les données de l'unité sélectionnée dans les champs de saisie.
        """
        selected_item = self.tree.focus()
        if selected_item:
            values = self.tree.item(selected_item, 'values')
            
            # Vérifier que ce n'est pas le message "Aucune unité"
            if values and values[0]:
                self.entry_designation.delete(0, 'end')
                self.entry_quantite.delete(0, 'end')
                self.entry_poids.delete(0, 'end')
                
                self.entry_designation.insert(0, values[1])
                self.entry_quantite.insert(0, values[3])
                self.entry_poids.insert(0, values[4])


    def _generer_code_article_et_niveau(self, id_article, conn):
        """Génère le code article et le niveau suivant"""
        cursor = conn.cursor()
        try:
            query = """
            SELECT 
                t2.idca, 
                COALESCE(MAX(t1.niveau), -1) + 1 AS prochain_niveau
            FROM 
                tb_article t1_art
            JOIN 
                tb_categoriearticle t2 ON t1_art.idca = t2.idca
            LEFT JOIN
                tb_unite t1 ON t1.idarticle = t1_art.idarticle
            WHERE 
                t1_art.idarticle = %s
            GROUP BY 
                t2.idca
            """
            cursor.execute(query, (id_article,))
            result = cursor.fetchone()
            
            if not result:
                messagebox.showerror("Erreur Article", "Article introuvable ou ID Catégorie manquant.")
                return None, None

            idca, prochain_niveau = result
            
            # Génération du code
            idca_str = str(idca).zfill(3)
            idarticle_str = str(id_article).zfill(5)
            niveau_str = str(prochain_niveau).zfill(2)
            
            code_article = f"{idca_str}{idarticle_str}{niveau_str}"
            
            return code_article, prochain_niveau

        except Exception as e:
            messagebox.showerror("Erreur DB", f"Erreur lors de la génération du code/niveau : {e}")
            return None, None
        finally:
            cursor.close()


    def ajouter_unite(self):
        """Ajoute une nouvelle unité dans la table tb_unite."""
        designation = self.entry_designation.get().strip()
        qtunite_str = self.entry_quantite.get().strip()
        poids_str = self.entry_poids.get().strip()

        if not designation or not qtunite_str or not poids_str:
            messagebox.showerror("Erreur de Saisie", "Tous les champs sont obligatoires.")
            return

        try:
            qtunite = float(qtunite_str)
            poids = float(poids_str)
            if qtunite <= 0 or poids < 0:
                messagebox.showerror("Erreur de Saisie", "La Quantité doit être > 0 et le Poids >= 0.")
                return
        except ValueError:
            messagebox.showerror("Erreur de Saisie", "La Quantité et le Poids doivent être des nombres valides.")
            return

        conn = self.connect_db()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
        
            # AJOUT DE LA SYNCHRONISATION AVANT L'INSERTION
            cursor.execute("""
                SELECT setval(pg_get_serial_sequence('tb_unite', 'idunite'), 
                          COALESCE((SELECT MAX(idunite) FROM tb_unite), 0) + 1, 
                          false);
            """)             
                        
            codearticle, niveau = self._generer_code_article_et_niveau(self.id_article, conn)
            
            if codearticle is None:
                conn.close()
                return

            cursor = conn.cursor()
            insert_query = """
            INSERT INTO tb_unite 
                (idarticle, designationunite, niveau, qtunite, poids, codearticle, deleted)
            VALUES 
                (%s, %s, %s, %s, %s, %s, 0)
            """
            
            cursor.execute(insert_query, (self.id_article, designation, niveau, qtunite, poids, codearticle))
            
            conn.commit()
            messagebox.showinfo("Succès", f"✅ Unité ajoutée !\nCode: {codearticle}")
            
            self.charger_unites()
            
            # Effacer les champs
            self.entry_designation.delete(0, 'end')
            self.entry_quantite.delete(0, 'end')
            self.entry_poids.delete(0, 'end')

        except psycopg2.IntegrityError as e:
            conn.rollback()
            messagebox.showerror("Erreur SQL", f"Erreur d'intégrité de la base de données : {e}")
        except psycopg2.Error as e:
            conn.rollback()
            messagebox.showerror("Erreur SQL", f"Erreur lors de l'insertion de l'unité : {e}")
        finally:
            if conn:
                conn.close()


    def modifier_unite(self):
        """Modifie l'unité sélectionnée dans tb_unite."""
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Sélection requise", "Veuillez sélectionner une unité à modifier.")
            return

        values = self.tree.item(selected_item, 'values')
        if not values or not values[0]:
            messagebox.showwarning("Sélection invalide", "Sélection invalide.")
            return
            
        id_unite = values[0]
        
        designation = self.entry_designation.get().strip()
        qtunite_str = self.entry_quantite.get().strip()
        poids_str = self.entry_poids.get().strip()

        if not designation or not qtunite_str or not poids_str:
            messagebox.showerror("Erreur de Saisie", "Tous les champs sont obligatoires.")
            return

        try:
            qtunite = float(qtunite_str)
            poids = float(poids_str)
        except ValueError:
            messagebox.showerror("Erreur de Saisie", "La Quantité et le Poids doivent être des nombres valides.")
            return

        conn = self.connect_db()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            update_query = """
            UPDATE tb_unite
            SET designationunite = %s, qtunite = %s, poids = %s
            WHERE idunite = %s
            """
            cursor.execute(update_query, (designation, qtunite, poids, id_unite))
            conn.commit()
            messagebox.showinfo("Succès", f"✅ Unité ID {id_unite} modifiée avec succès.")
            
            self.charger_unites()
            
        except psycopg2.Error as e:
            conn.rollback()
            messagebox.showerror("Erreur SQL", f"Erreur lors de la modification de l'unité : {e}")
        finally:
            if conn:
                conn.close()


    def supprimer_unite(self):
        """Supprime logiquement l'unité sélectionnée (deleted = 1)."""
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Sélection requise", "Veuillez sélectionner une unité à supprimer.")
            return
        
        values = self.tree.item(selected_item, 'values')
        if not values or not values[0]:
            messagebox.showwarning("Sélection invalide", "Sélection invalide.")
            return
            
        id_unite = values[0]
        designation = values[1]

        if not messagebox.askyesno("Confirmation", f"Êtes-vous sûr de vouloir supprimer l'unité '{designation}' (ID: {id_unite}) ?"):
            return

        conn = self.connect_db()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            delete_query = "UPDATE tb_unite SET deleted = 1 WHERE idunite = %s"
            
            cursor.execute(delete_query, (id_unite,))
            conn.commit()
            messagebox.showinfo("Succès", f"✅ Unité ID {id_unite} supprimée avec succès.")
            
            self.charger_unites()
            
            # Vider les champs
            self.entry_designation.delete(0, 'end')
            self.entry_quantite.delete(0, 'end')
            self.entry_poids.delete(0, 'end')

        except psycopg2.Error as e:
            conn.rollback()
            messagebox.showerror("Erreur SQL", f"Erreur lors de la suppression de l'unité : {e}")
        finally:
            if conn:
                conn.close()


# === CLASSE TOPLEVEL POUR UTILISATION INDÉPENDANTE ===
class PageUniteToplevel(ctk.CTkToplevel):
    """
    Fenêtre Toplevel pour utilisation indépendante de PageUnite.
    """
    def __init__(self, master, id_article_selectionne):
        super().__init__(master)
        self.title("Gestion des Unités d'Article")
        self.geometry("900x700")
        
        # Créer le frame PageUnite à l'intérieur
        self.page_unite = PageUnite(self, db_connector=None, initial_idarticle=id_article_selectionne)
        self.page_unite.pack(fill="both", expand=True, padx=10, pady=10)


# === Exemple d'utilisation ===
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    
    class App(ctk.CTk):
        def __init__(self):
            super().__init__()
            self.title("Test PageUnite")
            self.geometry("300x150")
            
            self.id_article_pour_test = 1
            
            btn = ctk.CTkButton(
                self, 
                text=f"Ouvrir Unités Article {self.id_article_pour_test}", 
                command=self.open_unite_window
            )
            btn.pack(pady=20)
            
            self.toplevel_window = None

        def open_unite_window(self):
            if self.toplevel_window is None or not self.toplevel_window.winfo_exists():
                self.toplevel_window = PageUniteToplevel(self, self.id_article_pour_test)
                self.toplevel_window.focus()
            else:
                self.toplevel_window.focus()

    app = App()
    app.mainloop()