import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import json
import threading

# page_prixSaisie doit rester optionnel
try:
    from pages.page_prixSaisie import PagePrixSaisie
except ImportError:
    PagePrixSaisie = None


class PagePrixListe(ctk.CTkFrame):
    def __init__(self, parent, db_connector=None, initial_idarticle=None, iduser=1):
        """
        parent          : conteneur parent (frame)
        db_connector    : optionnel (non utilisé directement ici, gardé pour compatibilité)
        initial_idarticle: code article (string ou int). Si fourni, la liste est filtrée sur ce code.
        iduser          : identifiant utilisateur (utilisé pour PagePrixSaisie)
        """
        super().__init__(parent)

        # Stocker les paramètres
        self.db_connector = db_connector
        # On préfère travailler avec le 'code article' : on accepte initial_idarticle comme tel
        self.code_article = str(initial_idarticle).zfill(10) if initial_idarticle else None
        self.iduser = iduser
        
        # Protection contre les double-clics multiples
        self.is_opening_window = False
        
        # Flag pour indiquer que le widget est en cours de destruction
        self._destroyed = False

        self.configure(fg_color="white")

        # Mapping item_id -> code_article (brut tel que dans DB)
        self.code_mapping = {}

        # Grille
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Widgets
        self.create_search_frame()
        self.create_treeview()

        # Label compteur
        self.lbl_count = ctk.CTkLabel(self, text="Nombre d'articles: 0", font=("Segoe UI", 11))
        self.lbl_count.grid(row=2, column=0, pady=10, sticky="w", padx=20)

        # Chargement initial asynchrone pour ne pas bloquer l'interface
        self.after(100, lambda: self.load_data_async())
        
        # Gérer la destruction propre du widget
        self.bind("<Destroy>", self._on_destroy)
    
    def _on_destroy(self, event):
        """Marquer le widget comme détruit"""
        if event.widget == self:
            self._destroyed = True

    def create_search_frame(self):
        """Créer le cadre de recherche"""
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.grid(row=0, column=0, pady=20, padx=20, sticky="ew")
        search_frame.grid_columnconfigure(1, weight=1)

        lbl_search = ctk.CTkLabel(search_frame, text="Rechercher:", font=("Segoe UI", 12, "bold"))
        lbl_search.grid(row=0, column=0, padx=(0, 10))

        self.entry_search = ctk.CTkEntry(
            search_frame,
            placeholder_text="Code Article, Nom, Unité ou Prix...",
            height=34,
            font=("Segoe UI", 11)
        )
        self.entry_search.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        self.entry_search.bind("<KeyRelease>", self.search_data)

        btn_search = ctk.CTkButton(
            search_frame,
            text="🔍 Rechercher",
            command=self.search_data,
            height=34,
            font=("Segoe UI", 11)
        )
        btn_search.grid(row=0, column=2)

    def create_treeview(self):
        """Créer le treeview avec les colonnes"""
        tree_frame = ctk.CTkFrame(self, fg_color="white")
        tree_frame.grid(row=1, column=0, pady=10, padx=20, sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("code", "nom", "unite", "prix"),
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            height=15
        )

        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        self.tree.heading("code", text="Code Article")
        self.tree.heading("nom", text="Nom d'article")
        self.tree.heading("unite", text="Unité")
        self.tree.heading("prix", text="Prix")

        self.tree.column("code", width=150, anchor="center")
        self.tree.column("nom", width=300, anchor="w")
        self.tree.column("unite", width=150, anchor="center")
        self.tree.column("prix", width=150, anchor="e")

        # mapping initialisé
        self.code_mapping = {}

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "Treeview",
            background="#FFFFFF",
            foreground="#000000",
            rowheight=22,
            fieldbackground="#FFFFFF",
            font=("Segoe UI", 9)
        )
        style.configure(
            "Treeview.Heading",
            background="#E8E8E8",
            foreground="#000000",
            font=("Segoe UI", 9, "bold")
        )
        style.map("Treeview", background=[("selected", "#1f538d")])
        self.tree.tag_configure("even", background="#FFFFFF", foreground="#000000")
        self.tree.tag_configure("odd", background="#E6EFF8", foreground="#000000")
        self.tree.tag_configure("even_zero", background="#FFFFFF", foreground="#f55f5f")
        self.tree.tag_configure("odd_zero", background="#E6EFF8", foreground="#f55f5f")

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # Double-clic avec protection
        self.tree.bind("<Double-Button-1>", self.on_double_click)

    def connect_db(self):
        """Connexion à la base de données PostgreSQL via config.json"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                db_config = config.get('database', {})
            conn = psycopg2.connect(
                host=db_config.get('host'),
                user=db_config.get('user'),
                password=db_config.get('password'),
                database=db_config.get('database'),
                port=db_config.get('port')
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

    def load_data_async(self, search_term=""):
        """Charger les données de manière asynchrone pour éviter de bloquer l'interface"""
        # Afficher un indicateur de chargement
        self.lbl_count.configure(text="Chargement en cours...")
        
        # Lancer le chargement dans un thread séparé
        thread = threading.Thread(target=self.load_data, args=(search_term,), daemon=True)
        thread.start()

    def load_data(self, search_term=""):
        """
        Charger les données :
        - si search_term non vide => recherche flexible
        - elif self.code_article fourni => filtrage exact sur code article (LPAD 10)
        - sinon => lister tout
        """
        conn = self.connect_db()
        if not conn:
            try:
                self.after(0, lambda: self.lbl_count.configure(text="Erreur de connexion"))
            except:
                pass
            return

        try:
            cursor = conn.cursor()

            # Requête OPTIMISÉE avec window function ROW_NUMBER (plus rapide que LATERAL)
            query = """
            SELECT 
                u.codearticle::TEXT,
                a.designation,
                u.designationunite,
                COALESCE(prix_recent.prix, 0) as prix
            FROM tb_unite u
            INNER JOIN tb_article a ON u.idarticle = a.idarticle
            LEFT JOIN (
                SELECT 
                    idunite, 
                    prix,
                    ROW_NUMBER() OVER (PARTITION BY idunite ORDER BY dateregistre DESC) as rn
                FROM tb_prix 
                WHERE deleted = 0
            ) prix_recent ON u.idunite = prix_recent.idunite AND prix_recent.rn = 1
            WHERE a.deleted = 0
            """

            params = []

            if search_term:
                # recherche insensible à la casse pour designation/unite, codearticle et prix (text)
                query += """
                AND (
                    LPAD(u.codearticle::TEXT, 10, '0') LIKE %s OR
                    LOWER(a.designation) LIKE LOWER(%s) OR
                    LOWER(u.designationunite) LIKE LOWER(%s) OR
                    COALESCE(prix_recent.prix, 0)::TEXT LIKE %s
                )
                """
                pattern = f"%{search_term}%"
                params = [pattern, pattern, pattern, pattern]
                cursor.execute(query + " ORDER BY a.designation ASC, u.codearticle ASC", params)

            elif self.code_article:
                # Filtrer exactement par code article (format 10 chiffres)
                query += " AND LPAD(u.codearticle::TEXT, 10, '0') = %s"
                params = [self.code_article.zfill(10)]
                cursor.execute(query + " ORDER BY a.designation ASC, u.codearticle ASC", params)
            else:
                cursor.execute(query + " ORDER BY a.designation ASC, u.codearticle ASC")

            rows = cursor.fetchall()

            # Vérifier que le widget existe toujours avant de mettre à jour
            try:
                if self.winfo_exists():
                    # Mettre à jour l'interface dans le thread principal
                    self.after(0, lambda r=rows: self.update_treeview(r))
            except:
                pass

            cursor.close()
            conn.close()

        except psycopg2.Error as err:
            try:
                self.after(0, lambda e=err: messagebox.showerror("Erreur", f"Erreur lors du chargement des données : {e}"))
            except:
                pass
            if conn:
                conn.close()
        except Exception as e:
            try:
                self.after(0, lambda ex=e: messagebox.showerror("Erreur", f"Erreur inattendue lors du chargement : {ex}"))
            except:
                pass
            if conn:
                conn.close()

    def update_treeview(self, rows):
        """Mettre à jour le treeview avec les résultats (appelé dans le thread principal)"""
        # Vérifier que le widget n'est pas détruit
        if self._destroyed:
            return
            
        # Vérifier que le widget existe toujours
        try:
            if not self.winfo_exists():
                return
        except:
            return
            
        # Vérifier que le tree existe toujours
        try:
            if not self.tree.winfo_exists():
                return
        except:
            return
            
        # vider treeview
        try:
            for item in self.tree.get_children():
                self.tree.delete(item)
        except:
            return
            
        self.code_mapping = {}

        for idx, row in enumerate(rows):
            if self._destroyed:
                return
                
            try:
                code_db = row[0] if row[0] is not None else ""
                nom = row[1] if row[1] is not None else ""
                unite = row[2] if row[2] is not None else ""
                prix = row[3] if row[3] is not None else 0

                # Format prix en français (1 234,56)
                try:
                    prix_format = f"{float(prix):,.2f}".replace('.', '#').replace(',', '.').replace('#', ',')
                except (ValueError, TypeError):
                    prix_format = "0,00"

                is_zero_price = False
                try:
                    is_zero_price = float(prix) == 0
                except (TypeError, ValueError):
                    is_zero_price = True

                if is_zero_price:
                    tag = "even_zero" if idx % 2 == 0 else "odd_zero"
                else:
                    tag = "even" if idx % 2 == 0 else "odd"

                item_id = self.tree.insert("", "end", values=(code_db, nom, unite, prix_format), tags=(tag,))
                self.code_mapping[item_id] = code_db
            except:
                # Si le tree a été détruit pendant l'insertion, arrêter
                return

        if self._destroyed:
            return
            
        try:
            count = len(rows)
            self.lbl_count.configure(text=f"Nombre d'articles: {count}")
        except:
            pass

    def search_data(self, event=None):
        search_term = self.entry_search.get().strip()
        # S'il y a un code_article fixé et que la recherche est vide, on conserve le filtre code_article.
        # si la recherche est non vide, on fait une recherche globale (remplace le filtre code_article)
        if search_term:
            self.load_data_async(search_term)
        else:
            # Si aucun terme et self.code_article présent, reload filtré
            self.load_data_async("")

    def on_double_click(self, event):
        # Protection contre les doubles clics multiples
        if self.is_opening_window:
            return
            
        selection = self.tree.selection()
        if not selection:
            return

        item_id = selection[0]
        code_article = self.code_mapping.get(item_id)

        if not code_article:
            messagebox.showwarning("Attention", "Impossible de récupérer le code article")
            return

        self.is_opening_window = True
        try:
            self.open_saisie_window(code_article)
        finally:
            # Réactiver après 500ms
            self.after(500, lambda: setattr(self, 'is_opening_window', False))

    def open_saisie_window(self, code_article):
        """Ouvrir la fenêtre de saisie des prix avec barre de progression"""
        if PagePrixSaisie is None:
            messagebox.showerror("Erreur", "Impossible d'importer page_prixSaisie.py. Veuillez vérifier l'existence du fichier.")
            return

        try:
            # Créer une fenêtre de progression
            progress_window = ctk.CTkToplevel(self)
            progress_window.title("Chargement...")
            progress_window.geometry("400x150")
            progress_window.resizable(False, False)
            
            # Centrer la fenêtre
            progress_window.transient(self.winfo_toplevel())
            progress_window.grab_set()
            
            # Frame de contenu
            content_frame = ctk.CTkFrame(progress_window, fg_color="white")
            content_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Label
            lbl_loading = ctk.CTkLabel(
                content_frame, 
                text=f"Chargement de la saisie des prix...\nArticle: {code_article}",
                font=("Segoe UI", 11)
            )
            lbl_loading.pack(pady=(10, 20))
            
            # Barre de progression
            progress_bar = ctk.CTkProgressBar(content_frame, width=350)
            progress_bar.pack(pady=10)
            progress_bar.set(0)
            
            # Fonction pour ouvrir la fenêtre dans un thread
            def load_saisie():
                try:
                    # Simuler la progression
                    for i in range(20, 60, 10):
                        progress_window.after(0, lambda val=i/100: progress_bar.set(val))
                        import time
                        time.sleep(0.05)
                    
                    # Créer la fenêtre de saisie dans le thread principal
                    def create_saisie():
                        try:
                            progress_bar.set(0.7)
                            
                            saisie_window = ctk.CTkToplevel(self)
                            saisie_window.title(f"Saisie Prix - {code_article}")
                            saisie_window.geometry("900x700")
                            
                            progress_bar.set(0.8)
                            
                            # Rendre la fenêtre modale
                            saisie_window.transient(self.winfo_toplevel())
                            saisie_window.grab_set()
                            
                            progress_bar.set(0.9)

                            # PagePrixSaisie : on transmet iduser puis code_article
                            page_saisie = PagePrixSaisie(saisie_window, self.iduser, code_article)
                            page_saisie.pack(fill="both", expand=True)
                            
                            progress_bar.set(1.0)

                            # Rafraîchir après fermeture
                            saisie_window.protocol("WM_DELETE_WINDOW", lambda: self.on_saisie_close(saisie_window))
                            
                            # Fermer la fenêtre de progression
                            progress_window.after(200, lambda: self.close_progress(progress_window))
                            
                        except Exception as err:
                            progress_window.after(0, lambda: self.close_progress(progress_window))
                            messagebox.showerror("Erreur", f"Erreur lors de l'ouverture de la fenêtre : {err}")
                            import traceback
                            traceback.print_exc()
                    
                    # Lancer la création dans le thread principal
                    progress_window.after(0, create_saisie)
                    
                except Exception as err:
                    progress_window.after(0, lambda: self.close_progress(progress_window))
                    messagebox.showerror("Erreur", f"Erreur lors du chargement : {err}")
                    import traceback
                    traceback.print_exc()
            
            # Lancer le chargement dans un thread séparé
            import threading
            thread = threading.Thread(target=load_saisie, daemon=True)
            thread.start()

        except Exception as err:
            messagebox.showerror("Erreur", f"Erreur lors de l'ouverture : {err}")
            import traceback
            traceback.print_exc()
    
    def close_progress(self, window):
        """Fermer la fenêtre de progression proprement"""
        try:
            window.grab_release()
            window.destroy()
        except Exception:
            pass

    def on_saisie_close(self, window):
        try:
            window.grab_release()
            window.destroy()
        except Exception:
            pass
        # Recharger: si un code_article est fixé, la reload prendra compte du filtre
        self.load_data_async()


# Test manuel
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Liste des Prix")
    root.geometry("1000x700")

    # Exemple 1 : sans filtre
    # page = PagePrixListe(root, db_connector=None, initial_idarticle=None, iduser=1)

    # Exemple 2 : filtrer sur code article (format 10 chiffres ou pas)
    # page = PagePrixListe(root, db_connector=None, initial_idarticle="1009", iduser=1)

    # Pour tester la page sans filtrage :
    page = PagePrixListe(root, db_connector=None, initial_idarticle=None, iduser=1)
    page.pack(fill="both", expand=True)

    root.mainloop()
