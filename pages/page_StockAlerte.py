import customtkinter as ctk
from tkinter import ttk, messagebox, simpledialog, StringVar
import psycopg2
import json
import os
from datetime import datetime


class PageStockAlerte(ctk.CTkFrame):
    """Interface permettant de surveiller et modifier les quantités d'alerte du stock."""

    def __init__(self, master, db_conn=None, session_data=None, iduser=None):
        super().__init__(master)
        # identifiant de l'utilisateur (pour audit ultérieur)
        if iduser is not None:
            self.iduser = iduser
        elif session_data and "user_id" in session_data:
            self.iduser = session_data["user_id"]
        else:
            self.iduser = 1

        self.setup_ui()
        self.charger_donnees()

    # ------------------------------------------------------------------
    # utilitaires base de données
    # ------------------------------------------------------------------
    def connect_db(self):
        """Retourne une connexion PostgreSQL en lisant config.json à la racine."""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(current_dir)
            config_path = os.path.join(root_dir, "config.json")
            with open(config_path, "r") as f:
                cfg = json.load(f)
                db_conf = cfg["database"]
            return psycopg2.connect(**db_conf)
        except Exception as e:
            messagebox.showerror("Erreur de connexion", f"Impossible de se connecter à la base : {e}")
            return None

    # ------------------------------------------------------------------
    # chargement / filtrage des informations
    # ------------------------------------------------------------------
    def charger_donnees(self):
        """Liste tous les articles avec l'unité de niveau max (si existante) et la valeur d'alerte.
        Résultat : codearticle, designation article, designation unité, alert, stock (placeholder '-')
        """
        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                  COALESCE(u.codearticle, '-') AS codearticle,
                  a.designation,
                  COALESCE(u.designationunite, '-') AS designationunite,
                  COALESCE(a.alert, 0) AS alert,
                  '-' AS stock
                FROM public.tb_article a
                LEFT JOIN public.tb_unite u
                  ON u.idarticle = a.idarticle
                  AND u.niveau = (
                    SELECT MAX(niveau) FROM public.tb_unite uu WHERE uu.idarticle = a.idarticle AND uu.deleted = 0
                  )
                WHERE a.deleted = 0
                ORDER BY a.designation
                """
            )
            rows = cur.fetchall()
            self.populate_table(rows)
        except Exception as e:
            messagebox.showerror("Erreur SQL", str(e))
        finally:
            conn.close()

    def filtrer_donnees(self, *args):
        """Filtre réactif des lignes en fonction du texte de recherche (onTextChanged)."""
        texte = self.var_recherche.get().lower()
        for item in self.tree.get_children():
            vals = self.tree.item(item, "values")
            if any(texte in str(v).lower() for v in vals):
                self.tree.reattach(item, '', 'end')
            else:
                self.tree.detach(item)
        self.maj_compteurs()

    # ------------------------------------------------------------------
    # mise à jour d'alerte
    # ------------------------------------------------------------------
    def modifier_alerte(self):
        """Ouvre une fenêtre de modification de la quantité d'alerte pour l'article sélectionné."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Sélection requise", "Veuillez sélectionner un article à modifier.")
            return
        code = self.tree.item(sel[0], "values")[0]
        # demande de nouvelle valeur
        new_val = simpledialog.askinteger("Nouvelle alerte", f"Nouvelle quantité d'alerte pour {code} :")
        if new_val is None:
            return
        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE public.tb_article
                SET alert = %s
                WHERE idarticle = (
                    SELECT idarticle FROM public.tb_unite WHERE codearticle = %s LIMIT 1
                )
                """,
                (new_val, code)
            )
            conn.commit()
            self.charger_donnees()
            messagebox.showinfo("Succès", "Quantité d'alerte mise à jour.")
        except Exception as e:
            messagebox.showerror("Erreur SQL", str(e))
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------
    def populate_table(self, rows):
        """Remplit le treeview avec les données fournies."""
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert('', 'end', values=row)
        self.maj_compteurs()

    def maj_compteurs(self):
        """Met à jour les informations de bas de page"""
        total = len(self.tree.get_children())
        self.label_total.configure(text=f"Total lignes: {total}")
        self.label_maj.configure(text=f"Dernière MAJ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

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
        self.var_recherche.trace("w", self.filtrer_donnees)
        self.entry_recherche = ctk.CTkEntry(frame_filtres, textvariable=self.var_recherche, placeholder_text="Code ou désignation...", width=300)
        self.entry_recherche.pack(side="left", padx=5)

        ctk.CTkButton(frame_filtres, text="✏️ Modifier alerte", command=self.modifier_alerte, fg_color="#f39c12", width=140).pack(side="right", padx=5)
        ctk.CTkButton(frame_filtres, text="🔄 Actualiser", command=self.charger_donnees, fg_color="#2e7d32", width=120).pack(side="right", padx=5)

        # tableau
        frame_tableau = ctk.CTkFrame(self)
        frame_tableau.pack(fill="both", expand=True, padx=20, pady=10)

        colonnes = ("Code Article", "Désignation", "Unité", "Alerte", "Stock")
        self.tree = ttk.Treeview(frame_tableau, columns=colonnes, show="headings", height=20)
        largeur = {"Code Article":120, "Désignation":300, "Unité":150, "Alerte":100, "Stock":80}
        for col in colonnes:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=largeur.get(col,120), anchor='center')

        scroll_y = ctk.CTkScrollbar(frame_tableau, orientation="vertical", command=self.tree.yview)
        scroll_x = ctk.CTkScrollbar(frame_tableau, orientation="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        frame_tableau.grid_rowconfigure(0, weight=1)
        frame_tableau.grid_columnconfigure(0, weight=1)

        frame_info = ctk.CTkFrame(self)
        frame_info.pack(fill="x", padx=20, pady=10)
        self.label_total = ctk.CTkLabel(frame_info, text="Total lignes: 0", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        self.label_total.pack(side="left", padx=20)
        self.label_maj = ctk.CTkLabel(frame_info, text="Dernière MAJ: --", font=ctk.CTkFont(family="Segoe UI", size=12))
        self.label_maj.pack(side="right", padx=20)
