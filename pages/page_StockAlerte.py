import customtkinter as ctk
from tkinter import ttk, messagebox, simpledialog, StringVar
import psycopg2
import json
import os
import threading
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

        self.item_ids = {}  # {tree_item_id: (idarticle, idunite)}
        self.item_stock = {}  # {tree_item_id: numeric_stock}
        self.item_alert = {}  # {tree_item_id: numeric_alert}
        self.all_items = []  # Liste de tous les item_ids pour le filtrage
        self.loading = False  # Flag pour le chargement
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
        """Lance le chargement en arrière-plan (non-bloquant)."""
        if not self.loading:
            self.loading = True
            self.label_statut.configure(text="⏳ Chargement...")
            thread = threading.Thread(target=self._charger_donnees_thread, daemon=True)
            thread.start()

    def _charger_donnees_thread(self):
        """Exécute la requête en arrière-plan."""
        try:
            conn = self.connect_db()
            if not conn:
                self.after(0, lambda: self._afficher_resultat(None, "Impossible de se connecter à la base."))
                return
            
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                  COALESCE(u.codearticle, '-') AS codearticle,
                  a.designation,
                  COALESCE(u.designationunite, '-') AS designationunite,
                  COALESCE(a.alert, 0) AS alert,
                  a.idarticle,
                  COALESCE(u.idunite, -1) AS idunite
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
            
            # Récupérer les stocks par (idarticle, idunite)
            stocks_dict = self._charger_stocks_par_unite(conn)
            
            # Enrichir les rows avec les stocks
            rows_enrichies = []
            for row in rows:
                idarticle, idunite = row[4], row[5]
                stock = stocks_dict.get((idarticle, idunite), 0)
                rows_enrichies.append((row[0], row[1], row[2], row[3], stock, idarticle, idunite))
            
            conn.close()
            self.after(0, lambda: self._afficher_resultat(rows_enrichies, None))
        except Exception as e:
            self.after(0, lambda: self._afficher_resultat(None, str(e)))

    def _charger_stocks_par_unite(self, conn):
        """Récupère les stocks globaux par (idarticle, idunite) en utilisant le pattern d'agrégation de mouvements.
        Retourne un dictionnaire {(idarticle, idunite): stock}.
        """
        try:
            cur = conn.cursor()
            query_stocks = """
            WITH unite_hierarchie AS (
                SELECT idarticle, idunite, niveau, qtunite
                FROM public.tb_unite
                WHERE deleted = 0
            ),
            unite_coeff AS (
                SELECT
                    idarticle,
                    idunite,
                    EXP(SUM(LN(NULLIF(COALESCE(qtunite,1),0)))
                        OVER (PARTITION BY idarticle ORDER BY niveau ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                    ) as coeff_hierarchique
                FROM unite_hierarchie
            ),
            rec AS (
                SELECT lf.idarticle, lf.idunite, lf.qtlivrefrs AS quantite
                FROM public.tb_livraisonfrs lf
                WHERE lf.deleted = 0
            ),
            ven AS (
                SELECT vd.idarticle, vd.idunite, -vd.qtvente AS quantite
                FROM public.tb_ventedetail vd
                INNER JOIN public.tb_vente v ON vd.idvente = v.id AND v.deleted = 0 AND v.statut = 'VALIDEE'
                WHERE vd.deleted = 0
            ),

            sor AS (
                SELECT sd.idarticle, sd.idunite, -sd.qtsortie AS quantite
                FROM public.tb_sortiedetail sd
                WHERE sd.deleted = 0
            ),
            inv AS (
                SELECT u.idarticle, u.idunite, i.qtinventaire AS quantite
                FROM public.tb_inventaire i
                INNER JOIN public.tb_unite u ON i.codearticle = u.codearticle
                WHERE u.deleted = 0
            ),
            avo AS (
                SELECT ad.idarticle, ad.idunite, ad.qtavoir AS quantite
                FROM public.tb_avoirdetail ad
                INNER JOIN public.tb_avoir av ON ad.idavoir = av.id AND av.deleted = 0
            ),
            conso AS (
                SELECT cid.idarticle, cid.idunite, -cid.qtconsomme AS quantite
                FROM public.tb_consommationinterne_details cid
                INNER JOIN public.tb_consommationinterne ci ON cid.idconsommation = ci.id
            ),
            ech_in AS (
                SELECT dce.idarticle, dce.idunite, dce.quantite_entree AS quantite
                FROM public.tb_detailchange_entree dce
                WHERE dce.idchg IS NOT NULL
            ),
            ech_out AS (
                SELECT dcs.idarticle, dcs.idunite, -dcs.quantite_sortie AS quantite
                FROM public.tb_detailchange_sortie dcs
                WHERE dcs.idchg IS NOT NULL
            ),
            mouvements_agreges AS (
                SELECT idarticle, idunite, quantite FROM rec UNION ALL
                SELECT idarticle, idunite, quantite FROM ven UNION ALL
                SELECT idarticle, idunite, quantite FROM sor UNION ALL
                SELECT idarticle, idunite, quantite FROM inv UNION ALL
                SELECT idarticle, idunite, quantite FROM avo UNION ALL
                SELECT idarticle, idunite, quantite FROM conso UNION ALL
                SELECT idarticle, idunite, quantite FROM ech_in UNION ALL
                SELECT idarticle, idunite, quantite FROM ech_out
            ),
            solde_par_unite AS (
                SELECT
                    ma.idarticle,
                    ma.idunite,
                    SUM(ma.quantite * COALESCE(uc.coeff_hierarchique, 1)) as solde_global
                FROM mouvements_agreges ma
                LEFT JOIN unite_coeff uc ON uc.idarticle = ma.idarticle AND uc.idunite = ma.idunite
                GROUP BY ma.idarticle, ma.idunite
            )
            SELECT idarticle, idunite, COALESCE(solde_global, 0) as stock FROM solde_par_unite
            """
            cur.execute(query_stocks)
            resultats = cur.fetchall()
            stocks_dict = {(row[0], row[1]): max(0, row[2]) for row in resultats}
            return stocks_dict
        except Exception as e:
            print(f"Erreur lors du calcul des stocks: {e}")
            return {}

    def _afficher_resultat(self, rows, erreur):
        """Met à jour l'UI avec les résultats (appelé depuis le thread principal)."""
        self.loading = False
        if erreur:
            messagebox.showerror("Erreur SQL", erreur)
            self.label_statut.configure(text="❌ Erreur de chargement")
        else:
            self.populate_table(rows)

    def filtrer_donnees(self, *args):
        """Filtre réactif des lignes en fonction du texte de recherche (onTextChanged).
        Réattache les éléments cachés si la recherche est vidée.
        """
        texte = self.var_recherche.get().lower()
        # récupérer filtre sélectionné
        selected_filter = None
        try:
            selected_filter = self.var_filter.get()
        except Exception:
            try:
                selected_filter = self.combo_filter.get()
            except Exception:
                selected_filter = "Tous"

        # Parcourir TOUS les items (même ceux détachés)
        for item in self.all_items:
            vals = self.tree.item(item, "values")
            # test texte
            text_ok = (texte == "" or any(texte in str(v).lower() for v in vals))
            # test filtre
            stock_val = self.item_stock.get(item, 0)
            alert_val = self.item_alert.get(item, 0)
            if selected_filter == "Rupture":
                filter_ok = (stock_val == 0)
            elif selected_filter == "En alerte":
                filter_ok = (stock_val > 0 and alert_val >= stock_val)
            else:
                filter_ok = True

            if text_ok and filter_ok:
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
        item_id = sel[0]
        if item_id not in self.item_ids:
            messagebox.showerror("Erreur", "ID article non trouvé.")
            return
        idarticle, idunite = self.item_ids[item_id]
        code = self.tree.item(item_id, "values")[0]
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
                "UPDATE public.tb_article SET alert = %s WHERE idarticle = %s",
                (new_val, idarticle)
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
        """Remplit le treeview avec les données fournies.
        Stocke les idarticle et idunite dans self.item_ids pour usage ultérieur.
        Conserve tous les item_ids dans self.all_items pour le filtrage.
        """
        self.tree.delete(*self.tree.get_children())
        self.item_ids = {}
        self.all_items = []
        for row in rows:
            # row = (codearticle, designation, designationunite, alert, stock, idarticle, idunite)
            # Formater le stock avec virgule décimale si nécessaire
            stock_val = row[4]
            stock_str = f"{stock_val:.2f}".replace('.', ',') if isinstance(stock_val, (int, float)) else '-'
            displayed_values = (row[0], row[1], row[2], row[3], stock_str)  # codearticle, design, unite, alert, stock
            idarticle, idunite = row[5], row[6]
            item_id = self.tree.insert('', 'end', values=displayed_values)
            # stock and alert numeric values for filtering/colouring
            try:
                numeric_alert = int(row[3]) if row[3] is not None else 0
            except Exception:
                try:
                    numeric_alert = int(float(row[3]))
                except Exception:
                    numeric_alert = 0
            try:
                numeric_stock = float(stock_val) if stock_val is not None else 0
            except Exception:
                numeric_stock = 0

            # assign tags based on conditions
            if numeric_stock == 0:
                self.tree.item(item_id, tags=('rupture',))
            elif numeric_alert >= numeric_stock:
                self.tree.item(item_id, tags=('alerte',))

            self.item_ids[item_id] = (idarticle, idunite)
            self.item_stock[item_id] = numeric_stock
            self.item_alert[item_id] = numeric_alert
            self.all_items.append(item_id)
        self.maj_compteurs()

    def maj_compteurs(self):
        """Met à jour les informations de bas de page"""
        total = len(self.tree.get_children())
        self.label_total.configure(text=f"Total lignes: {total}")
        if not self.loading:
            self.label_statut.configure(text=f"Dernière MAJ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def on_double_click(self, event):
        """Handler pour le double-clic sur une ligne du treeview.
        Ouvre la fenêtre d'édition pour l'article cliqué.
        """
        # Trouver l'item sous le curseur
        item = self.tree.identify_row(event.y)
        if not item:
            return
        # sélectionner l'item
        try:
            self.tree.selection_set(item)
        except Exception:
            pass
        self.open_article_editor(item)

    def open_article_editor(self, item_id):
        """Ouvre une fenêtre permettant de voir les infos de l'article
        et de modifier la valeur d'alerte.
        """
        if item_id not in self.item_ids:
            messagebox.showerror("Erreur", "Article introuvable pour édition.")
            return
        idarticle, idunite = self.item_ids[item_id]
        values = self.tree.item(item_id, "values")
        code = values[0]
        designation = values[1]
        unite = values[2]
        current_alert = values[3]
        stock = values[4]

        # Fenêtre modale
        try:
            win = ctk.CTkToplevel(self)
        except Exception:
            from tkinter import Toplevel
            win = Toplevel(self)
        win.title(f"Éditer alerte - {code}")
        win.grab_set()

        frm = ctk.CTkFrame(win)
        frm.pack(padx=12, pady=12, fill="both", expand=True)

        ctk.CTkLabel(frm, text=f"Code: {code}").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ctk.CTkLabel(frm, text=f"Désignation: {designation}").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        ctk.CTkLabel(frm, text=f"Unité: {unite}").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        ctk.CTkLabel(frm, text=f"Stock actuel: {stock}").grid(row=3, column=0, sticky="w", padx=6, pady=4)

        ctk.CTkLabel(frm, text="Quantité d'alerte:").grid(row=4, column=0, sticky="w", padx=6, pady=(12,4))
        var_alert = StringVar(value=str(current_alert))
        entry_alert = ctk.CTkEntry(frm, textvariable=var_alert, width=140)
        entry_alert.grid(row=5, column=0, sticky="w", padx=6, pady=4)

        btn_frame = ctk.CTkFrame(frm)
        btn_frame.grid(row=6, column=0, pady=(12,0), sticky="e")

        def do_save():
            v = var_alert.get()
            try:
                # accepter entier (ou entier vide)
                if v is None or v == "":
                    messagebox.showwarning("Valeur requise", "Veuillez renseigner une quantité d'alerte.")
                    return
                new_val = int(v)
            except Exception:
                messagebox.showerror("Format invalide", "La quantité d'alerte doit être un nombre entier.")
                return
            conn = self.connect_db()
            if not conn:
                return
            try:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE public.tb_article SET alert = %s WHERE idarticle = %s",
                    (new_val, idarticle)
                )
                conn.commit()
                messagebox.showinfo("Succès", "Quantité d'alerte mise à jour.")
                win.destroy()
                self.charger_donnees()
            except Exception as e:
                messagebox.showerror("Erreur SQL", str(e))
            finally:
                conn.close()

        def do_cancel():
            win.destroy()

        ctk.CTkButton(btn_frame, text="Enregistrer", command=do_save, fg_color="#2e7d32", width=100).pack(side="right", padx=6)
        ctk.CTkButton(btn_frame, text="Annuler", command=do_cancel, fg_color="#bdbdbd", width=100).pack(side="right")

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

        # filtre d'affichage: Tous / En alerte / Rupture
        from tkinter import StringVar as TkStringVar
        self.var_filter = TkStringVar(value="Tous")
        try:
            # utiliser ttk.Combobox pour stabilité
            self.combo_filter = ttk.Combobox(frame_filtres, values=["Tous", "En alerte", "Rupture"], textvariable=self.var_filter, state="readonly", width=16)
            self.combo_filter.bind("<<ComboboxSelected>>", lambda e: self.filtrer_donnees())
            self.combo_filter.pack(side="left", padx=8)
        except Exception:
            # fallback: option menu
            opt = ctk.CTkOptionMenu(frame_filtres, values=["Tous", "En alerte", "Rupture"], command=lambda v: self.filtrer_donnees())
            opt.set("Tous")
            opt.pack(side="left", padx=8)

        ctk.CTkButton(frame_filtres, text="✏️ Modifier alerte", command=self.modifier_alerte, fg_color="#f39c12", width=140).pack(side="right", padx=5)
        ctk.CTkButton(frame_filtres, text="🔄 Actualiser", command=self.charger_donnees, fg_color="#2e7d32", width=120).pack(side="right", padx=5)

        # tableau
        frame_tableau = ctk.CTkFrame(self)
        frame_tableau.pack(fill="both", expand=True, padx=20, pady=10)

        colonnes = ("Code Article", "Désignation", "Unité", "Alerte", "Stock")
        self.tree = ttk.Treeview(frame_tableau, columns=colonnes, show="headings", height=20)
        # Configurer les tags pour coloration conditionnelle (couleur du texte seulement)
        self.tree.tag_configure('rupture', foreground='#b71c1c')
        self.tree.tag_configure('alerte', foreground='#e65100')
        largeur = {"Code Article":120, "Désignation":300, "Unité":150, "Alerte":100, "Stock":80}
        for col in colonnes:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=largeur.get(col,120), anchor='center')

        scroll_y = ctk.CTkScrollbar(frame_tableau, orientation="vertical", command=self.tree.yview)
        scroll_x = ctk.CTkScrollbar(frame_tableau, orientation="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        # Bind double-click to open editor pour modification rapide
        self.tree.bind("<Double-1>", self.on_double_click)
        # Filtre rapide: combobox pour afficher Tous / En alerte / Rupture
        # (ajouté plus haut dans la fenêtre)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        frame_tableau.grid_rowconfigure(0, weight=1)
        frame_tableau.grid_columnconfigure(0, weight=1)

        frame_info = ctk.CTkFrame(self)
        frame_info.pack(fill="x", padx=20, pady=10)
        self.label_total = ctk.CTkLabel(frame_info, text="Total lignes: 0", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        self.label_total.pack(side="left", padx=20)
        # légende (deux lignes)
        legend_text = "Texte rouge: rupture de stock (stock = 0)\nTexte orange: en alerte (alerte >= stock)"
        self.label_legend = ctk.CTkLabel(frame_info, text=legend_text, font=ctk.CTkFont(family="Segoe UI", size=10))
        self.label_legend.pack(side="left", padx=10)
        self.label_statut = ctk.CTkLabel(frame_info, text="⏳ Chargement...", font=ctk.CTkFont(family="Segoe UI", size=12))
        self.label_statut.pack(side="right", padx=20)
