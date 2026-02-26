import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import psycopg2
import json
from PIL import Image, ImageTk
import os
import shutil
import sys
from resource_utils import get_config_path, safe_file_read


# --- IMPORTATIONS DES PAGES ---
try:
    from pages.page_infoArticle import PageInfoArticle
    print("✓ PageInfoArticle chargée avec succès")
except ImportError as e:
    # Classe de substitution si l'import échoue
    class PageInfoArticle(ctk.CTkFrame):
        def __init__(self, master, db_conn=None, session_data=None, initial_idarticle=None):
            super().__init__(master)
            self.pack(fill="both", expand=True)
            ctk.CTkLabel(self, text="Erreur: PageInfoArticle introuvable").pack()

class PageArticle(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.selected_article = None
        self.photo_label = None
        self.magasins_dict = {} 
        self.categories_dict = {}
        self.all_articles = []
        self.toplevel_unite = None 
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # Le Treeview prend l'espace
        
        self.create_widgets()
        self.load_categories()
        self.load_magasins()
        self.load_articles()
    
    def connect_db(self):
        try:
            # Assurez-vous que config.json est au bon endroit
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
            messagebox.showerror("Erreur de connexion", f"Erreur : {err}")
            return None

    def create_widgets(self):
        # --- SECTION FORMULAIRE ---
        form_frame = ctk.CTkFrame(self)
        form_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        form_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(form_frame, text="Désignation:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.entry_designation = ctk.CTkEntry(form_frame)
        self.entry_designation.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        
        ctk.CTkLabel(form_frame, text="Catégorie:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.combo_categorie = ctk.CTkComboBox(form_frame, state="readonly")
        self.combo_categorie.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        ctk.CTkLabel(form_frame, text="Magasin:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.combo_magasin = ctk.CTkComboBox(form_frame, state="readonly")
        self.combo_magasin.grid(row=2, column=1, padx=5, pady=2, sticky="ew")
        
        ctk.CTkLabel(form_frame, text="Alerte:").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.entry_alert = ctk.CTkEntry(form_frame)
        self.entry_alert.insert(0, "0")
        self.entry_alert.grid(row=3, column=1, padx=5, pady=2, sticky="ew")

        ctk.CTkLabel(form_frame, text="Alerte Dépôt:").grid(row=4, column=0, padx=5, pady=2, sticky="w")
        self.entry_alert_depot = ctk.CTkEntry(form_frame)
        self.entry_alert_depot.insert(0, "0")
        self.entry_alert_depot.grid(row=4, column=1, padx=5, pady=2, sticky="ew")
        
        btn_frame = ctk.CTkFrame(form_frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)
        
        self.btn_ajouter = ctk.CTkButton(btn_frame, text="Ajouter", command=self.ajouter_article, width=100)
        self.btn_ajouter.pack(side="left", padx=5)
        self.btn_modifier = ctk.CTkButton(btn_frame, text="Modifier", command=self.modifier_article, width=100)
        self.btn_modifier.pack(side="left", padx=5)
        self.btn_supprimer = ctk.CTkButton(btn_frame, text="Supprimer", command=self.supprimer_article, width=100, fg_color="#c62828")
        self.btn_supprimer.pack(side="left", padx=5)
        self.btn_nettoyer = ctk.CTkButton(btn_frame, text="Nettoyer", command=self.nettoyer_formulaire, width=100)
        self.btn_nettoyer.pack(side="left", padx=5)
        
        # --- CADRE PHOTO (Colonne 1) ---
        photo_container = ctk.CTkFrame(self)
        photo_container.grid(row=0, column=1, padx=10, pady=10, sticky="ne")
        
        photo_frame = ctk.CTkFrame(photo_container, width=220, height=220)
        photo_frame.pack(padx=5, pady=5)
        photo_frame.grid_propagate(False)
        
        self.photo_label = ctk.CTkLabel(photo_frame, text="Aucune Image", width=200, height=200, fg_color="gray25", corner_radius=10)
        self.photo_label.pack(expand=True, fill="both", padx=5, pady=5)
        
        self.btn_ajout_photo = ctk.CTkButton(photo_container, text="📸 Ajouter Photo", command=self.ajouter_photo, width=220)
        self.btn_ajout_photo.pack(pady=5)

        # --- SECTION RECHERCHE ---
        search_frame = ctk.CTkFrame(self)
        search_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=(5, 0), sticky="ew")
        
        ctk.CTkLabel(search_frame, text="🔍 Rechercher article:").pack(side="left", padx=10)
        self.entry_search = ctk.CTkEntry(search_frame, placeholder_text="Saisissez un designation...")
        self.entry_search.pack(side="left", fill="x", expand=True, padx=10, pady=5)
        self.entry_search.bind("<KeyRelease>", self.filter_articles)

        # --- SECTION TREEVIEW + SCROLLBAR ---
        tree_container = ctk.CTkFrame(self)
        tree_container.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        tree_container.grid_columnconfigure(0, weight=1)
        tree_container.grid_rowconfigure(0, weight=1)

        style = ttk.Style()
        style.configure("Treeview", rowheight=22, background="#FFFFFF", foreground="#000000", fieldbackground="#FFFFFF", borderwidth=0, font=('Segoe UI', 8))
        style.configure("Treeview.Heading", background="#E8E8E8", foreground="#000000", font=('Segoe UI', 8, 'bold'))
        
        self.tree = ttk.Treeview(tree_container, columns=("ID", "Désignation", "Catégorie", "Magasin", "Alerte", "Alerte Dépôt"), show="headings")
        self.tree.tag_configure("even", background="#FFFFFF", foreground="#000000")
        self.tree.tag_configure("odd", background="#E5F0F8", foreground="#000000")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Désignation", text="Désignation")
        self.tree.heading("Catégorie", text="Catégorie")
        self.tree.heading("Magasin", text="Magasin")
        self.tree.heading("Alerte", text="Alerte")
        self.tree.heading("Alerte Dépôt", text="Alerte Dépôt")
        
        for col in ["ID", "Alerte", "Alerte Dépôt"]: 
            self.tree.column(col, width=80, anchor="center")

        # Ajout de la Scrollbar
        self.scrollbar = ctk.CTkScrollbar(tree_container, orientation="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        # --- LIAISONS ---
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", self.ouvrir_gestion_unites)

    def filter_articles(self, event=None):
        """Filtre les résultats du treeview selon la saisie."""
        search_term = self.entry_search.get().strip().lower()
        if not search_term:
            filtered = self.all_articles
        else:
            filtered = [
                article for article in self.all_articles
                if search_term in str(article[1]).lower()
            ]
        self._populate_tree(filtered)

    def _populate_tree(self, articles):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for idx, article in enumerate(articles):
            tag = "even" if idx % 2 == 0 else "odd"
            self.tree.insert("", "end", values=article, tags=(tag,))

    def ajouter_article(self):
        designation = self.entry_designation.get().strip()
        if not designation:
            messagebox.showwarning("Erreur", "La désignation est obligatoire.")
            return

        idca = self.categories_dict.get(self.combo_categorie.get())
        idmag = self.magasins_dict.get(self.combo_magasin.get())
        
        try:
            alert = int(self.entry_alert.get())
            alertdepot = int(self.entry_alert_depot.get())
        except ValueError:
            messagebox.showerror("Erreur", "Les alertes doivent être des nombres.")
            return

        conn = self.connect_db()
        if conn:
            try:
                cursor = conn.cursor()
                query = """INSERT INTO tb_article (designation, idca, idmag, alert, alertdepot, deleted) 
                           VALUES (%s, %s, %s, %s, %s, 0)"""
                try:
                    cursor.execute(query, (designation, idca, idmag, alert, alertdepot))
                    conn.commit()
                except psycopg2.IntegrityError as ie:
                    # Gestion d'une clé dupliquée probable due à une séquence désynchronisée
                    conn.rollback()
                    msg = str(ie).lower()
                    if 'duplicate key' in msg or 'unique' in msg:
                        try:
                            # Récupérer le nom de la séquence liée à idarticle
                            cursor.execute("SELECT pg_get_serial_sequence('tb_article', 'idarticle')")
                            seq_row = cursor.fetchone()
                            seq_name = seq_row[0] if seq_row else None

                            # Trouver le max(idarticle) et remettre la séquence à cette valeur
                            cursor.execute("SELECT COALESCE(MAX(idarticle), 0) FROM tb_article")
                            max_row = cursor.fetchone()
                            max_id = int(max_row[0]) if max_row and max_row[0] is not None else 0

                            if seq_name:
                                # setval(seq, max_id) -> nextval renverra max_id+1
                                cursor.execute("SELECT setval(%s, %s)", (seq_name, max_id))
                                conn.commit()
                                # Réessayer l'insertion une seule fois
                                cursor.execute(query, (designation, idca, idmag, alert, alertdepot))
                                conn.commit()
                            else:
                                raise ie
                        except Exception as fix_e:
                            conn.rollback()
                            raise fix_e
                    else:
                        raise ie

                # --- NOTIFICATION ---
                messagebox.showinfo("Succès", f"L'article '{designation}' a été ajouté avec succès !")
                
                self.nettoyer_formulaire()
                self.load_articles()
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
            finally: 
                conn.close()

    # --- MÉTHODES EXISTANTES (Maintenues) ---
    def load_articles(self):
        conn = self.connect_db()
        if not conn: return
        try:
            cursor = conn.cursor()
            query = """
                SELECT a.idarticle, a.designation, c.designationcat, m.designationmag, a.alert, a.alertdepot
                FROM tb_article a
                LEFT JOIN tb_categoriearticle c ON a.idca = c.idca
                LEFT JOIN tb_magasin m ON a.idmag = m.idmag
                WHERE a.deleted = 0 ORDER BY a.designation
            """
            cursor.execute(query)
            self.all_articles = cursor.fetchall()
            self.filter_articles()
            cursor.close()
            conn.close()
        except Exception as err:
            messagebox.showerror("Erreur", f"Chargement articles: {err}")

    def on_select(self, event):
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            v = item['values']
            self.selected_article = v[0]
            self.entry_designation.delete(0, 'end')
            self.entry_designation.insert(0, v[1])
            self.combo_categorie.set(v[2] if v[2] else "")
            self.combo_magasin.set(v[3] if v[3] else "")
            self.entry_alert.delete(0, 'end')
            self.entry_alert.insert(0, v[4])
            self.entry_alert_depot.delete(0, 'end')
            self.entry_alert_depot.insert(0, v[5])
            self.load_photo(self.selected_article)

    def load_magasins(self):
        conn = self.connect_db()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT idmag, designationmag FROM tb_magasin ORDER BY designationmag")
            magasins = cursor.fetchall()
            self.magasins_dict = {m[1]: m[0] for m in magasins}
            mag_names = list(self.magasins_dict.keys())
            if mag_names:
                self.combo_magasin.configure(values=mag_names)
                self.combo_magasin.set(mag_names[0])
            cursor.close()
            conn.close()
        except: pass

    def load_categories(self):
        conn = self.connect_db()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT idca, designationcat FROM tb_categoriearticle ORDER BY designationcat")
            categories = cursor.fetchall()
            self.categories_dict = {cat[1]: cat[0] for cat in categories}
            if categories: 
                self.combo_categorie.configure(values=list(self.categories_dict.keys()))
            conn.close()
        except: pass

    def load_photo(self, idarticle):
        if not idarticle:
            self.clear_photo()
            return
        # Chemin simplifié pour l'exemple
        photo_folder = os.path.join(os.getcwd(), "PhotoArticle")
        photo_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
        photo_path = None
        for ext in photo_extensions:
            p = os.path.join(photo_folder, f"{idarticle}{ext}")
            if os.path.exists(p):
                photo_path = p
                break
        if photo_path:
            try:
                img = Image.open(photo_path)
                img.thumbnail((200, 200))
                photo = ImageTk.PhotoImage(img)
                self.photo_label.configure(image=photo, text="")
                self.photo_label.image = photo
            except: self.clear_photo()
        else: self.clear_photo()

    def clear_photo(self):
        self.photo_label.configure(image=None, text="Pas d'image")
        self.photo_label.image = None

    def nettoyer_formulaire(self):
        self.entry_designation.delete(0, 'end')
        self.entry_alert.delete(0, 'end')
        self.entry_alert.insert(0, "0")
        self.entry_alert_depot.delete(0, 'end')
        self.entry_alert_depot.insert(0, "0")
        self.selected_article = None
        self.clear_photo()

    def modifier_article(self):
        if not self.selected_article: return
        idca = self.categories_dict.get(self.combo_categorie.get())
        idmag = self.magasins_dict.get(self.combo_magasin.get())
        designation = self.entry_designation.get().strip()
        conn = self.connect_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("UPDATE tb_article SET designation=%s, idca=%s, idmag=%s WHERE idarticle=%s", 
                               (designation, idca, idmag, self.selected_article))
                conn.commit()
                self.load_articles()
                messagebox.showinfo("Succès", "Article mis à jour")
            finally: conn.close()

    def supprimer_article(self):
        if not self.selected_article: return
        if messagebox.askyesno("Confirmation", "Supprimer cet article ?"):
            conn = self.connect_db()
            if conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE tb_article SET deleted = 1 WHERE idarticle = %s", (self.selected_article,))
                conn.commit()
                conn.close()
                self.load_articles()
                self.nettoyer_formulaire()

    def ajouter_photo(self):
        if not self.selected_article:
            messagebox.showwarning("Attention", "Sélectionnez un article.")
            return
        file_path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.png *.jpeg")])
        if file_path:
            try:
                dest = os.path.join(os.getcwd(), "PhotoArticle")
                if not os.path.exists(dest): os.makedirs(dest)
                ext = os.path.splitext(file_path)[1]
                shutil.copy2(file_path, os.path.join(dest, f"{self.selected_article}{ext}"))
                self.load_photo(self.selected_article)
                messagebox.showinfo("Succès", "Photo enregistrée")
            except Exception as e: messagebox.showerror("Erreur", str(e))

    def ouvrir_gestion_unites(self, event):
        selection = self.tree.selection()
        if not selection: return
        id_article = self.tree.item(selection[0])['values'][0]
        if self.toplevel_unite is None or not self.toplevel_unite.winfo_exists():
            self.toplevel_unite = ctk.CTkToplevel(self)
            self.toplevel_unite.title(f"Détails Article: {id_article}")
            self.toplevel_unite.geometry("1000x600")
            info_page = PageInfoArticle(self.toplevel_unite, initial_idarticle=id_article)
            info_page.pack(fill="both", expand=True)
        else: self.toplevel_unite.focus()

if __name__ == "__main__":
    root = ctk.CTk()
    root.geometry("1100x800")
    page = PageArticle(root)
    page.pack(fill="both", expand=True)
    root.mainloop()
