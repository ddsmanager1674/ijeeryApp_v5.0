import customtkinter as ctk
from tkinter import ttk, messagebox, simpledialog, StringVar
import psycopg2
import json
import os
from datetime import datetime
import sys
import configparser
from typing import Dict, Any
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
try:
    from stock_manager import StockManager
except ImportError:
    StockManager = None


class PageStockAlerte(ctk.CTkFrame):
    """UI skeleton for stock alert page; data logic removed."""

    def __init__(self, master, db_conn=None, session_data=None, iduser=None):
        super().__init__(master)
        self.item_ids = {}  # {tree_item_id: (idarticle, idunite, idmag)}
        self.stock_manager = None  # Instance unique de StockManager
        self.threads = []  # Liste pour tracker les threads actifs
        self._init_stock_manager()  # Initialiser connexion une seule fois
        self.setup_ui()
        # load initial data
        self.charger_donnees()

    def _init_stock_manager(self):
        """Initialise une unique instance de StockManager pour la classe."""
        if StockManager is None:
            return
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(current_dir)
            config_path = os.path.join(root_dir, "config.ini")
            cfg = configparser.ConfigParser()
            cfg.read(config_path)
            db = cfg['database'] if 'database' in cfg else {}
            db_conf = {
                'host': db.get('host', 'localhost'),
                'port': int(db.get('port', 5432)),
                'dbname': db.get('dbname', ''),
                'user': db.get('user', 'postgres'),
                'password': db.get('password', ''),
            }
            self.stock_manager = StockManager(**db_conf)
        except Exception as e:
            print(f"Erreur initialisation StockManager: {e}")
            self.stock_manager = None

    def __del__(self):
        """Ferme la connexion StockManager à la destruction de l'objet."""
        if self.stock_manager:
            try:
                self.stock_manager.fermer_connexion()
            except Exception:
                pass

    def noop(self, *args, **kwargs):
        """No operation placeholder for disabled functionality."""
        pass

    # --------------------------------------------------------------
    # database utilities
    # --------------------------------------------------------------
    def connect_db(self):
        """Open a connection using config.json at project root."""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(current_dir)
            config_path = os.path.join(root_dir, "config.json")
            with open(config_path, "r") as f:
                cfg = json.load(f)
            db_conf = cfg.get("database", {})
            return psycopg2.connect(**db_conf)
        except Exception as e:
            messagebox.showerror("Erreur de connexion", f"Impossible de se connecter à la base : {e}")
            return None

    def charger_donnees(self):
        """Récupère la liste des articles (niveau max) avec alertes et met à jour le tableau."""
        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT u.codearticle,
                       a.designation,
                       u.designationunite,
                       m.designationmag,
                       a.alertdepot,
                       0::double precision AS stock_mag,
                       a.alert,
                       0::double precision AS stock_global,
                       a.idarticle,
                       u.idunite,
                       a.idmag
                FROM public.tb_article a
                JOIN public.tb_unite u
                  ON u.idarticle = a.idarticle
                 AND u.niveau = (
                       SELECT MAX(niveau)
                       FROM public.tb_unite uu
                       WHERE uu.idarticle = a.idarticle
                         AND uu.deleted = 0
                   )
                JOIN public.tb_magasin m
                  ON m.idmag = a.idmag
                WHERE a.deleted = 0
                  AND u.deleted = 0
                  AND m.deleted = 0
                ORDER BY a.designation
                """
            )
            rows = cur.fetchall()
            self.populate_table(rows)
            self.label_statut.configure(text=f"Dernière MAJ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            messagebox.showerror("Erreur SQL", str(e))
        finally:
            conn.close()

    def _get_stock_magasin_value(self, idarticle: int, idunite: int, idmagasin: int) -> str:
        """Récupère le stock réel d'un article/unité/magasin via l'instance unique de StockManager."""
        if not self.stock_manager:
            return "N/A"
        try:
            result = self.stock_manager.get_stock_article_par_unite(idarticle=idarticle, idunite=idunite, idmagasin=idmagasin)
            stock = result.get('stock_dans_unite', 0)
            designation_unite = result.get('designationunite', 'Unité')
            return f"{int(stock)} {designation_unite}"
        except Exception as e:
            return f"Erreur: {str(e)[:20]}"

    def _load_stock_for_row(self, item_id: str, idarticle: int, idunite: int, idmag: int):
        """Charge les stocks en arrière-plan et met à jour la ligne correspondante."""
        try:
            # Récupérer les stocks
            stock_mag = self._get_stock_magasin_value(idarticle, idunite, idmag)
            stock_global = self._get_stock_magasin_value(idarticle, idunite, 0)
            
            # Mettre à jour la ligne dans le treeview (thread-safe)
            if item_id in self.item_ids:
                current_values = self.tree.item(item_id, 'values')
                updated_values = (
                    current_values[0],  # codearticle
                    current_values[1],  # designation
                    current_values[2],  # designationunite
                    current_values[3],  # designationmag
                    current_values[4],  # alertdepot
                    stock_mag,          # Stock Mag. (calculé)
                    current_values[6],  # alert
                    stock_global        # Stock Gen. (calculé)
                )
                self.tree.item(item_id, values=updated_values)
        except Exception as e:
            print(f"Erreur lors du chargement du stock pour {item_id}: {e}")

    def clear_table(self):
        """Remove all rows from the treeview."""
        self.tree.delete(*self.tree.get_children())
        self.item_ids = {}
        self.label_total.configure(text="Total lignes: 0")

    def populate_table(self, rows):
        """Insert provided rows into the treeview and update count.
        Store idarticle, idunite, idmag as tuple for each row.
        Load stock values asynchronously in background threads.
        """
        self.tree.delete(*self.tree.get_children())
        self.item_ids = {}
        
        # Nettoyer les anciens threads s'il y en a
        self.threads = [t for t in self.threads if t.is_alive()]
        
        for row in rows:
            # row[0:8] = display values, row[8:11] = idarticle, idunite, idmag (if present)
            if len(row) >= 11:
                idarticle, idunite, idmag = row[8], row[9], row[10]
                # Build initial display with "Calcul en cours..." placeholders
                displayed = (
                    row[0],  # codearticle
                    row[1],  # designation
                    row[2],  # designationunite
                    row[3],  # designationmag
                    row[4],  # alertdepot
                    "Calcul en cours...",  # Stock Mag. (placeholder)
                    row[6],  # alert
                    "Calcul en cours..."   # Stock Gen. (placeholder)
                )
                item_id = self.tree.insert('', 'end', values=displayed)
                self.item_ids[item_id] = (idarticle, idunite, idmag)
                
                # Lancer un thread pour charger les stocks réels
                thread = threading.Thread(
                    target=self._load_stock_for_row,
                    args=(item_id, idarticle, idunite, idmag),
                    daemon=True
                )
                thread.start()
                self.threads.append(thread)
            else:
                displayed = row[:8]
                item_id = self.tree.insert('', 'end', values=displayed)
        
        self.label_total.configure(text=f"Total lignes: {len(rows)}")

    # ------------------------------------------------------------------
    # interface graphique
    # ------------------------------------------------------------------
    def setup_ui(self):
        titre = ctk.CTkLabel(self, text="⚠️ Stock Alerte", font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"))
        titre.pack(pady=10)

        # barre de filtres/recherche
        frame_filtres = ctk.CTkFrame(self)
        frame_filtres.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(frame_filtres, text="🔍 Recherche:", font=ctk.CTkFont(family="Segoe UI", size=12)).pack(side="left", padx=5)
        self.var_recherche = StringVar()
        self.var_recherche.trace("w", self.noop)
        self.entry_recherche = ctk.CTkEntry(frame_filtres, textvariable=self.var_recherche, placeholder_text="Code ou désignation...", width=300)
        self.entry_recherche.pack(side="left", padx=5)

        from tkinter import StringVar as TkStringVar
        self.var_filter = TkStringVar(value="Tous")
        try:
            self.combo_filter = ttk.Combobox(frame_filtres, values=["Tous", "En alerte", "Rupture"], textvariable=self.var_filter, state="readonly", width=16)
            self.combo_filter.pack(side="left", padx=8)
        except Exception:
            opt = ctk.CTkOptionMenu(frame_filtres, values=["Tous", "En alerte", "Rupture"], command=lambda v: None)
            opt.set("Tous")
            opt.pack(side="left", padx=8)

        ctk.CTkButton(frame_filtres, text="✏️ Modifier alerte", command=self.noop, fg_color="#f39c12", width=140).pack(side="right", padx=5)
        ctk.CTkButton(frame_filtres, text="🔄 Actualiser", command=self.charger_donnees, fg_color="#2e7d32", width=120).pack(side="right", padx=5)

        # tableau
        frame_tableau = ctk.CTkFrame(self)
        frame_tableau.pack(fill="both", expand=True, padx=20, pady=10)

        colonnes = ("CodeArticle", "Désignation", "Unité (Sup)", "Magasin", "Alerte Mag.", "Stock Mag.", "Alerte Gen.", "Stock Gen.")
        self.tree = ttk.Treeview(frame_tableau, columns=colonnes, show="headings", height=20)
        self.tree.tag_configure('rupture', foreground='#b71c1c')
        self.tree.tag_configure('alerte', foreground='#e65100')
        largeur = {"CodeArticle":120, "Désignation":300, "Unité (Sup)":150, "Magasin":160, "Alerte Mag.":100, "Stock Mag.":100, "Alerte Gen.":100, "Stock Gen.":100}
        for col in colonnes:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=largeur.get(col,120), anchor='center')

        scroll_y = ctk.CTkScrollbar(frame_tableau, orientation="vertical", command=self.tree.yview)
        scroll_x = ctk.CTkScrollbar(frame_tableau, orientation="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        frame_tableau.grid_rowconfigure(0, weight=1)
        frame_tableau.grid_columnconfigure(0, weight=1)

        frame_info = ctk.CTkFrame(self)
        frame_info.pack(fill="x", padx=20, pady=10)
        self.label_total = ctk.CTkLabel(frame_info, text="Total lignes: 0", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        self.label_total.pack(side="left", padx=20)
        legend_text = "Texte rouge: rupture de stock (stock = 0)\nTexte orange: en alerte (alerte >= stock)"
        self.label_legend = ctk.CTkLabel(frame_info, text=legend_text, font=ctk.CTkFont(family="Segoe UI", size=10))
        self.label_legend.pack(side="left", padx=10)
        self.label_statut = ctk.CTkLabel(frame_info, text="", font=ctk.CTkFont(family="Segoe UI", size=12))
        self.label_statut.pack(side="right", padx=20)

    # ------------------------------------------------------------------
    # double-click & article editor
    # ------------------------------------------------------------------
    def on_double_click(self, event):
        """Handle double-click on treeview row to open article editor."""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        if item not in self.item_ids:
            messagebox.showerror("Erreur", "Article introuvable.")
            return
        self.open_article_editor(item)

    def open_article_editor(self, item_id):
        """Open modal window to edit article info and alerts."""
        if item_id not in self.item_ids:
            messagebox.showerror("Erreur", "Article introuvable pour édition.")
            return
        
        idarticle, idunite, idmag = self.item_ids[item_id]
        values = self.tree.item(item_id, "values")
        
        codearticle = values[0]
        designation = values[1]
        designationunite = values[2]
        designationmag = values[3]
        alertdepot_current = values[4]
        alert_current = values[6]
        
        # Create modal window
        try:
            win = ctk.CTkToplevel(self)
        except Exception:
            from tkinter import Toplevel
            win = Toplevel(self)
        
        win.title("Infos Article/Alerte")
        win.geometry("500x400")
        win.grab_set()
        
        # Center window on screen
        win.update_idletasks()
        screen_width = win.winfo_screenwidth()
        screen_height = win.winfo_screenheight()
        x = (screen_width // 2) - (500 // 2)
        y = (screen_height // 2) - (400 // 2)
        win.geometry(f"+{x}+{y}")
        
        # Main frame
        main_frm = ctk.CTkFrame(win)
        main_frm.pack(padx=15, pady=15, fill="both", expand=True)
        
        # Panel 1: Article info (read-only)
        panel1 = ctk.CTkFrame(main_frm, fg_color="#2a2a2a")
        panel1.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(panel1, text="Code Article:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(8, 2))
        ctk.CTkLabel(panel1, text=str(codearticle), font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10, pady=(0, 8))
        
        ctk.CTkLabel(panel1, text="Nom Article:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(2, 2))
        ctk.CTkLabel(panel1, text=str(designation), font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10, pady=(0, 8))
        
        ctk.CTkLabel(panel1, text="Unité Supérieure:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(2, 2))
        ctk.CTkLabel(panel1, text=str(designationunite), font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10, pady=(0, 8))
        
        # Panel 2: Editable fields
        panel2 = ctk.CTkFrame(main_frm, fg_color="#2a2a2a")
        panel2.pack(fill="x", padx=10, pady=10)
        
        # Magasin dropdown
        ctk.CTkLabel(panel2, text="Magasin:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(8, 2))
        magasins_list = self._get_magasins()
        magasins_display = [m[1] for m in magasins_list]  # Display names
        magasins_ids = [m[0] for m in magasins_list]  # IDs
        
        var_magasin = StringVar(value=designationmag)
        try:
            combo_magasin = ttk.Combobox(panel2, textvariable=var_magasin, values=magasins_display, state="readonly", width=40)
            combo_magasin.pack(anchor="w", padx=10, pady=(0, 10))
        except Exception:
            opt_mag = ctk.CTkOptionMenu(panel2, values=magasins_display)
            opt_mag.set(designationmag)
            opt_mag.pack(anchor="w", padx=10, pady=(0, 10))
            combo_magasin = opt_mag
        
        # Alert depot (magasin)
        ctk.CTkLabel(panel2, text="Alerte Magasin:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(2, 2))
        var_alert_depot = StringVar(value=str(alertdepot_current))
        entry_alert_depot = ctk.CTkEntry(panel2, textvariable=var_alert_depot, width=200)
        entry_alert_depot.pack(anchor="w", padx=10, pady=(0, 10))
        
        # Alert general
        ctk.CTkLabel(panel2, text="Alerte Générale:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(2, 2))
        var_alert_general = StringVar(value=str(alert_current))
        entry_alert_general = ctk.CTkEntry(panel2, textvariable=var_alert_general, width=200)
        entry_alert_general.pack(anchor="w", padx=10, pady=(0, 10))
        
        # Buttons
        btn_frm = ctk.CTkFrame(main_frm)
        btn_frm.pack(fill="x", pady=15)
        
        def do_save():
            try:
                new_alert_depot = float(var_alert_depot.get())
            except ValueError:
                messagebox.showerror("Erreur", "Alerte Magasin doit être un nombre.")
                return
            
            try:
                new_alert_general = float(var_alert_general.get())
            except ValueError:
                messagebox.showerror("Erreur", "Alerte Générale doit être un nombre.")
                return
            
            # Get selected magasin ID
            selected_mag_name = var_magasin.get()
            selected_mag_id = idmag  # Default to current
            for mag_id, mag_name in magasins_list:
                if mag_name == selected_mag_name:
                    selected_mag_id = mag_id
                    break
            
            conn = self.connect_db()
            if not conn:
                return
            
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    UPDATE public.tb_article
                    SET alertdepot = %s, alert = %s, idmag = %s
                    WHERE idarticle = %s
                    """,
                    (new_alert_depot, new_alert_general, selected_mag_id, idarticle)
                )
                conn.commit()
                messagebox.showinfo("Succès", "Alertes mises à jour.")
                win.destroy()
                self.charger_donnees()
            except Exception as e:
                messagebox.showerror("Erreur SQL", str(e))
            finally:
                conn.close()
        
        def do_cancel():
            win.destroy()
        
        ctk.CTkButton(btn_frm, text="Enregistrer", command=do_save, fg_color="#2e7d32", width=120).pack(side="right", padx=10)
        ctk.CTkButton(btn_frm, text="Fermer", command=do_cancel, fg_color="#666666", width=120).pack(side="right", padx=5)
    
    def _get_magasins(self):
        """Fetch list of (idmag, designationmag) from database."""
        conn = self.connect_db()
        if not conn:
            return []
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT idmag, designationmag FROM public.tb_magasin WHERE deleted = 0 ORDER BY designationmag"
            )
            return cur.fetchall()
        except Exception:
            return []
        finally:
            conn.close()

