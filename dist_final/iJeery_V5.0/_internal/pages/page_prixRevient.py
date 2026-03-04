import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import json
import threading


# ─────────────────────────────────────────────────────────────────────────────
#  Fenêtre de sélection de fournisseur
# ─────────────────────────────────────────────────────────────────────────────
class FournisseurSelectWindow(ctk.CTkToplevel):
    """Petite fenêtre modale pour choisir un fournisseur."""

    def __init__(self, parent, fournisseurs: list, on_select_callback):
        super().__init__(parent)
        self.title("Sélectionner un fournisseur")
        self.geometry("420x480")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.on_select_callback = on_select_callback
        self._all_fournisseurs = fournisseurs

        self.configure(fg_color="white")
        self._build_ui()
        self._populate(fournisseurs)

        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width()  - self.winfo_width())  // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{px}+{py}")

    def _build_ui(self):
        import tkinter as tk

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(12, 6))

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", self._on_search)
        entry = ctk.CTkEntry(top, textvariable=self._search_var,
                             placeholder_text="Filtrer…", height=32)
        entry.pack(fill="x")
        entry.focus_set()

        frame = ctk.CTkFrame(self, fg_color="white")
        frame.pack(fill="both", expand=True, padx=12, pady=4)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        vsb = ttk.Scrollbar(frame, orient="vertical")
        self._listbox = tk.Listbox(
            frame, selectmode="single",
            font=("Segoe UI", 10), relief="flat",
            activestyle="dotbox", bg="white", fg="#1a1a1a",
            selectbackground="#1f538d", selectforeground="white",
            yscrollcommand=vsb.set, bd=0, highlightthickness=0
        )
        vsb.config(command=self._listbox.yview)
        self._listbox.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self._listbox.bind("<Double-Button-1>", self._on_double_click)
        self._listbox.bind("<Return>",          self._on_double_click)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=12, pady=(4, 12))

        ctk.CTkButton(bottom, text="✔ Sélectionner", height=32,
                      fg_color="#034787", hover_color="#0565c9",
                      command=self._confirm).pack(side="left", padx=(0, 8))
        ctk.CTkButton(bottom, text="✖ Annuler", height=32,
                      fg_color="#888", hover_color="#555",
                      command=self.destroy).pack(side="left")
        ctk.CTkButton(bottom, text="✕ Tous", height=32,
                      fg_color="#e07b00", hover_color="#c06a00",
                      command=self._select_all).pack(side="right")

    def _populate(self, items):
        self._listbox.delete(0, "end")
        for item in items:
            self._listbox.insert("end", item)

    def _on_search(self, *_):
        term = self._search_var.get().lower()
        self._populate([f for f in self._all_fournisseurs if term in f.lower()])

    def _on_double_click(self, event=None):
        self._confirm()

    def _confirm(self):
        sel = self._listbox.curselection()
        if sel:
            self.on_select_callback(self._listbox.get(sel[0]))
            self.destroy()

    def _select_all(self):
        self.on_select_callback("")
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────
#  Fenêtre d'historique des prix de revient
# ─────────────────────────────────────────────────────────────────────────────
class HistoriquePrixWindow(ctk.CTkToplevel):

    def __init__(self, parent, connect_db_fn,
                 code_article: str, designation: str, unite: str, idunite: int):
        super().__init__(parent)
        self.title(f"Historique — {designation} ({unite})")
        self.geometry("780x480")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color="white")

        self._connect_db = connect_db_fn
        self._idunite    = idunite

        self._build_ui(code_article, designation, unite)
        self._load_historique()

        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width()  - self.winfo_width())  // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{px}+{py}")

    def _build_ui(self, code, designation, unite):
        header = ctk.CTkFrame(self, fg_color="#034787", corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(header, text=f"📦  {code}  —  {designation}",
                     font=("Segoe UI", 13, "bold"), text_color="white"
                     ).pack(side="left", padx=16, pady=10)
        ctk.CTkLabel(header, text=f"Unité : {unite}",
                     font=("Segoe UI", 11), text_color="#cce0ff"
                     ).pack(side="right", padx=16)

        tree_frame = ctk.CTkFrame(self, fg_color="white")
        tree_frame.pack(fill="both", expand=True, padx=12, pady=10)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")

        self._tree = ttk.Treeview(
            tree_frame,
            columns=("date", "ref", "fournisseur", "prix"),
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
        )
        vsb.config(command=self._tree.yview)
        hsb.config(command=self._tree.xview)

        self._tree.heading("date",        text="Date livraison")
        self._tree.heading("ref",         text="Réf. Facture / Réception")
        self._tree.heading("fournisseur", text="Fournisseur")
        self._tree.heading("prix",        text="Prix unitaire")

        self._tree.column("date",        width=140, anchor="center")
        self._tree.column("ref",         width=220, anchor="w")
        self._tree.column("fournisseur", width=200, anchor="w")
        self._tree.column("prix",        width=130, anchor="e")

        style = ttk.Style()
        style.configure("Treeview",         rowheight=22, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        self._tree.tag_configure("even",  background="#FFFFFF")
        self._tree.tag_configure("odd",   background="#E6EFF8")
        self._tree.tag_configure("first", background="#fffbe6")

        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self._lbl_status = ctk.CTkLabel(self, text="Chargement…",
                                        font=("Segoe UI", 10), text_color="#555")
        self._lbl_status.pack(pady=(0, 8))

    def _load_historique(self):
        threading.Thread(target=self._fetch_historique, daemon=True).start()

    def _fetch_historique(self):
        conn = self._connect_db()
        if not conn:
            self.after(0, lambda: self._lbl_status.configure(text="Erreur de connexion"))
            return
        try:
            cursor = conn.cursor()
            query = """
            SELECT
                lf.dateregistre,
                COALESCE(lf.factfrs,   '—') AS ref_facture,
                COALESCE(lf.reflivfrs, '—') AS ref_reception,
                COALESCE(f.nomFrs, 'Inconnu') AS fournisseur,
                cd.punitcmd
            FROM tb_livraisonfrs lf
            INNER JOIN tb_commande       com ON lf.idcom   = com.idcom
            INNER JOIN tb_commandedetail cd  ON cd.idcom   = com.idcom
                                             AND cd.idunite = lf.idunite
                                             AND cd.punitcmd IS NOT NULL
                                             AND cd.punitcmd <> 0
            LEFT  JOIN tb_fournisseur    f   ON com.idfrs  = f.idfrs
            WHERE lf.idunite  = %s
              AND lf.deleted  = 0
              AND com.deleted = 0
            ORDER BY lf.dateregistre DESC
            """
            cursor.execute(query, (self._idunite,))
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            self.after(0, lambda r=rows: self._populate_tree(r))
        except Exception as e:
            try: conn.close()
            except Exception: pass
            self.after(0, lambda ex=e: self._lbl_status.configure(text=f"Erreur : {ex}"))

    def _populate_tree(self, rows):
        for item in self._tree.get_children():
            self._tree.delete(item)
        for idx, row in enumerate(rows):
            date_str = row[0].strftime("%d/%m/%Y %H:%M") if row[0] else "—"
            ref = f"{row[1]}  /  {row[2]}"
            try:
                prix_fmt = (f"{float(row[4]):,.2f}"
                            .replace('.', '#').replace(',', '.').replace('#', ','))
            except Exception:
                prix_fmt = "0,00"
            tag = "first" if idx == 0 else ("even" if idx % 2 == 0 else "odd")
            self._tree.insert("", "end",
                              values=(date_str, ref, row[3], prix_fmt),
                              tags=(tag,))
        self._lbl_status.configure(
            text=f"{len(rows)} entrée(s)  —  ligne jaune = prix le plus récent")


# ─────────────────────────────────────────────────────────────────────────────
#  Page principale
# ─────────────────────────────────────────────────────────────────────────────
class PagePrixRevient(ctk.CTkFrame):

    _ROW_H  = 36    # hauteur de la ligne de contrôles
    _PAD_Y  = 7     # padding vertical dans le panel

    def __init__(self, parent, db_connector=None, iduser=1):
        super().__init__(parent)

        self.db_connector      = db_connector
        self.iduser            = iduser
        self.is_opening_window = False
        self._destroyed        = False
        self.code_mapping      = {}
        self.idunite_mapping   = {}
        self._fournisseurs_list = []

        self.configure(fg_color="white")

        # ── Layout : pack vertical (top fixe / middle flex / footer fixe) ────
        self._build_top_panel()
        self._build_footer()     # footer en premier avec side="bottom"
        self._build_treeview()   # treeview ensuite avec fill+expand

        self.after(100, self.load_data_async)
        self.after(100, self._load_fournisseurs_cache)
        self.bind("<Destroy>", self._on_destroy)

    def _on_destroy(self, event):
        if event.widget == self:
            self._destroyed = True

    # ─────────────────────────────────────────────────────────────────────────
    #  Panneau supérieur — hauteur fixe, une seule ligne
    # ─────────────────────────────────────────────────────────────────────────
    def _build_top_panel(self):
        panel = ctk.CTkFrame(self, fg_color="#f2f4f8", corner_radius=0)
        panel.pack(side="top", fill="x", padx=0, pady=0)

        # colonnes : icône | recherche (flex) | sep | "Fournisseur:" | input | 🔎 | ✕ | sep | checkbox | sep | reset
        panel.grid_columnconfigure(1, weight=1)   # recherche prend le reste
        for c in [0, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
            panel.grid_columnconfigure(c, weight=0)

        py = self._PAD_Y
        h  = self._ROW_H

        # ── icône loupe ───────────────────────────────────────────────────────
        ctk.CTkLabel(panel, text="🔍", font=("Segoe UI", 13),
                     width=28, anchor="center"
                     ).grid(row=0, column=0, padx=(12, 2), pady=py)

        # ── champ recherche ───────────────────────────────────────────────────
        self.entry_search = ctk.CTkEntry(
            panel,
            placeholder_text="Code article, désignation, fournisseur…",
            height=h, font=("Segoe UI", 10),
            border_width=1, corner_radius=5)
        self.entry_search.grid(row=0, column=1, sticky="ew",
                               padx=(0, 8), pady=py)
        self.entry_search.bind("<KeyRelease>", self.search_data)

        # ── séparateur 1 ──────────────────────────────────────────────────────
        ctk.CTkFrame(panel, width=1, fg_color="#c5cad6"
                     ).grid(row=0, column=2, sticky="ns",
                            pady=py + 4, padx=(0, 6))

        # ── label fournisseur ─────────────────────────────────────────────────
        ctk.CTkLabel(panel, text="Fournisseur :",
                     font=("Segoe UI", 10, "bold"), anchor="e"
                     ).grid(row=0, column=3, padx=(2, 4), pady=py, sticky="e")

        # ── input fournisseur (readonly) ──────────────────────────────────────
        self._frs_var = ctk.StringVar(value="")
        self.entry_fournisseur = ctk.CTkEntry(
            panel, textvariable=self._frs_var,
            placeholder_text="Tous",
            height=h, font=("Segoe UI", 10),
            width=180, state="readonly",
            border_width=1, corner_radius=5)
        self.entry_fournisseur.grid(row=0, column=4, padx=(0, 2), pady=py)

        # ── bouton loupe fournisseur ──────────────────────────────────────────
        ctk.CTkButton(panel, text="🔎",
                      width=h, height=h,
                      fg_color="#034787", hover_color="#0565c9",
                      font=("Segoe UI", 12), corner_radius=5,
                      command=self._open_fournisseur_picker
                      ).grid(row=0, column=5, padx=(0, 2), pady=py)

        # ── bouton effacer fournisseur ────────────────────────────────────────
        ctk.CTkButton(panel, text="✕",
                      width=h, height=h,
                      fg_color="#a0a8ba", hover_color="#7a8296",
                      font=("Segoe UI", 11), corner_radius=5,
                      command=self._clear_fournisseur
                      ).grid(row=0, column=6, padx=(0, 8), pady=py)

        # ── séparateur 2 ──────────────────────────────────────────────────────
        ctk.CTkFrame(panel, width=1, fg_color="#c5cad6"
                     ).grid(row=0, column=7, sticky="ns",
                            pady=py + 4, padx=(0, 6))

        # ── case à cocher ─────────────────────────────────────────────────────
        self._only_with_price = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            panel,
            text="Uniquement avec prix",
            variable=self._only_with_price,
            font=("Segoe UI", 10),
            checkbox_width=16, checkbox_height=16,
            corner_radius=3,
            fg_color="#034787", hover_color="#0565c9",
            command=self.load_data_async
        ).grid(row=0, column=8, padx=(4, 8), pady=py)

        # ── séparateur 3 ──────────────────────────────────────────────────────
        ctk.CTkFrame(panel, width=1, fg_color="#c5cad6"
                     ).grid(row=0, column=9, sticky="ns",
                            pady=py + 4, padx=(0, 6))

        # ── bouton Réinitialiser ──────────────────────────────────────────────
        ctk.CTkButton(
            panel, text="↺  Réinitialiser",
            height=h, font=("Segoe UI", 10),
            fg_color="#5a6478", hover_color="#3d4559",
            corner_radius=5,
            command=self._reset_all
        ).grid(row=0, column=10, padx=(0, 12), pady=py)

    # ─────────────────────────────────────────────────────────────────────────
    #  Treeview
    # ─────────────────────────────────────────────────────────────────────────
    def _build_treeview(self):
        tree_frame = ctk.CTkFrame(self, fg_color="white", corner_radius=0)
        tree_frame.pack(side="top", fill="both", expand=True)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("code", "designation", "unite", "fournisseur", "prix"),
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
        )
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        self.tree.heading("code",        text="Code Article")
        self.tree.heading("designation", text="Désignation")
        self.tree.heading("unite",       text="Unité")
        self.tree.heading("fournisseur", text="Fournisseur (dernier)")
        self.tree.heading("prix",        text="Prix de revient")

        self.tree.column("code",        width=130, anchor="center", minwidth=90)
        self.tree.column("designation", width=300, anchor="w",      minwidth=150)
        self.tree.column("unite",       width=120, anchor="center", minwidth=80)
        self.tree.column("fournisseur", width=210, anchor="w",      minwidth=120)
        self.tree.column("prix",        width=140, anchor="e",      minwidth=90)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Treeview",
                         background="#FFFFFF", foreground="#000000",
                         rowheight=23, fieldbackground="#FFFFFF",
                         font=("Segoe UI", 9))
        style.configure("Treeview.Heading",
                         background="#E2E8F0", foreground="#1a2030",
                         font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#1f538d")])

        self.tree.tag_configure("even",      background="#FFFFFF", foreground="#111")
        self.tree.tag_configure("odd",       background="#EEF3FA", foreground="#111")
        self.tree.tag_configure("even_zero", background="#FFFFFF", foreground="#cc3333")
        self.tree.tag_configure("odd_zero",  background="#EEF3FA", foreground="#cc3333")

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<Double-Button-1>", self._on_row_double_click)

    # ─────────────────────────────────────────────────────────────────────────
    #  Footer
    # ─────────────────────────────────────────────────────────────────────────
    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color="#e8ecf4", corner_radius=0, height=28)
        footer.pack(side="bottom", fill="x")
        footer.pack_propagate(False)
        footer.grid_columnconfigure(0, weight=1)

        self.lbl_count = ctk.CTkLabel(
            footer, text="Nombre d'articles : 0",
            font=("Segoe UI", 10), text_color="#444", anchor="w")
        self.lbl_count.grid(row=0, column=0, sticky="w", padx=14, pady=4)

        self.lbl_status = ctk.CTkLabel(
            footer, text="",
            font=("Segoe UI", 10, "italic"), text_color="#888", anchor="e")
        self.lbl_status.grid(row=0, column=1, sticky="e", padx=14, pady=4)

    # ─────────────────────────────────────────────────────────────────────────
    #  Actions filtres
    # ─────────────────────────────────────────────────────────────────────────
    def _open_fournisseur_picker(self):
        FournisseurSelectWindow(self, self._fournisseurs_list,
                                self._on_fournisseur_selected)

    def _on_fournisseur_selected(self, value: str):
        self._frs_var.set(value)
        self.load_data_async()

    def _clear_fournisseur(self):
        self._frs_var.set("")
        self.load_data_async()

    def _reset_all(self):
        """Efface tous les filtres et recharge depuis zéro."""
        self.entry_search.delete(0, "end")
        self._frs_var.set("")
        self._only_with_price.set(False)
        self.load_data_async()

    # ─────────────────────────────────────────────────────────────────────────
    #  Base de données
    # ─────────────────────────────────────────────────────────────────────────
    def connect_db(self):
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                db_cfg = config.get('database', {})
            return psycopg2.connect(
                host=db_cfg.get('host'),
                user=db_cfg.get('user'),
                password=db_cfg.get('password'),
                database=db_cfg.get('database'),
                port=db_cfg.get('port')
            )
        except FileNotFoundError:
            messagebox.showerror("Erreur config", "Fichier 'config.json' introuvable.")
        except psycopg2.Error as err:
            messagebox.showerror("Erreur connexion", str(err))
        except Exception as err:
            messagebox.showerror("Erreur", str(err))
        return None

    def _load_fournisseurs_cache(self):
        threading.Thread(target=self._fetch_fournisseurs, daemon=True).start()

    def _fetch_fournisseurs(self):
        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT nomFrs FROM tb_fournisseur "
                        "WHERE deleted = 0 ORDER BY nomFrs ASC")
            self._fournisseurs_list = [r[0] for r in cur.fetchall()]
            cur.close()
            conn.close()
        except Exception:
            if conn:
                conn.close()

    # ─────────────────────────────────────────────────────────────────────────
    #  Chargement des données
    # ─────────────────────────────────────────────────────────────────────────
    def load_data_async(self, search_term=""):
        # Appel depuis KeyRelease → search_term est un Event tkinter
        if not isinstance(search_term, str):
            search_term = self.entry_search.get().strip()
        self._safe_ui(lambda: self.lbl_status.configure(text="Chargement…"))
        threading.Thread(target=self.load_data, args=(search_term,), daemon=True).start()

    def load_data(self, search_term=""):
        conn = self.connect_db()
        if not conn:
            self._safe_ui(lambda: self.lbl_status.configure(text="Erreur de connexion"))
            return

        try:
            cursor = conn.cursor()

            query = """
            SELECT
                LPAD(u.codearticle::TEXT, 10, '0') AS code,
                a.designation,
                u.designationunite,
                COALESCE(f.nomFrs, 'Aucun fournisseur') AS fournisseur,
                COALESCE(last_lf.punitcmd, 0)           AS dernier_prix,
                u.idunite
            FROM tb_unite u
            INNER JOIN tb_article a ON u.idarticle = a.idarticle
            LEFT JOIN LATERAL (
                SELECT cd.punitcmd, com.idfrs
                FROM tb_livraisonfrs lf
                INNER JOIN tb_commande       com ON lf.idcom   = com.idcom
                INNER JOIN tb_commandedetail cd  ON cd.idcom   = com.idcom
                                                 AND cd.idunite = u.idunite
                                                 AND cd.punitcmd IS NOT NULL
                                                 AND cd.punitcmd <> 0
                WHERE lf.idunite = u.idunite
                  AND lf.deleted  = 0
                  AND com.deleted = 0
                ORDER BY lf.dateregistre DESC
                LIMIT 1
            ) last_lf ON TRUE
            LEFT JOIN tb_fournisseur f ON last_lf.idfrs = f.idfrs
            WHERE a.deleted = 0
              AND u.deleted = 0
            """

            params        = []
            where_clauses = []

            # Filtre fournisseur
            try:
                frs_sel = self._frs_var.get().strip()
            except Exception:
                frs_sel = ""
            if frs_sel:
                where_clauses.append("f.nomFrs = %s")
                params.append(frs_sel)

            # Filtre "uniquement avec prix"
            try:
                only_price = self._only_with_price.get()
            except Exception:
                only_price = False
            if only_price:
                where_clauses.append(
                    "last_lf.punitcmd IS NOT NULL AND last_lf.punitcmd <> 0")

            # Filtre texte
            if search_term:
                where_clauses.append("""(
                    LPAD(u.codearticle::TEXT, 10, '0') LIKE %s OR
                    LOWER(a.designation)      LIKE LOWER(%s) OR
                    LOWER(u.designationunite) LIKE LOWER(%s) OR
                    LOWER(f.nomFrs)           LIKE LOWER(%s)
                )""")
                p = f"%{search_term}%"
                params.extend([p, p, p, p])

            if where_clauses:
                query += " AND (" + " AND ".join(where_clauses) + ")"

            query += " ORDER BY a.designation ASC, u.codearticle ASC"

            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            self._safe_ui(lambda r=rows: self.update_treeview(r))

        except psycopg2.Error as err:
            self._safe_ui(lambda e=err: messagebox.showerror("Erreur SQL", str(e)))
            if conn: conn.close()
        except Exception as ex:
            self._safe_ui(lambda e=ex: messagebox.showerror("Erreur", str(e)))
            if conn: conn.close()

    def _safe_ui(self, fn):
        try:
            if not self._destroyed and self.winfo_exists():
                self.after(0, fn)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    #  Mise à jour treeview
    # ─────────────────────────────────────────────────────────────────────────
    def update_treeview(self, rows):
        if self._destroyed:
            return
        try:
            if not self.winfo_exists() or not self.tree.winfo_exists():
                return
        except Exception:
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        self.code_mapping    = {}
        self.idunite_mapping = {}

        for idx, row in enumerate(rows):
            if self._destroyed:
                return
            try:
                code        = row[0] or ""
                designation = row[1] or ""
                unite       = row[2] or ""
                fournisseur = row[3] or ""
                prix        = row[4] if row[4] is not None else 0
                idunite     = row[5]

                try:
                    prix_fmt = (f"{float(prix):,.2f}"
                                .replace('.', '#').replace(',', '.').replace('#', ','))
                except Exception:
                    prix_fmt = "0,00"

                try:
                    zero = float(prix) == 0
                except Exception:
                    zero = True

                tag = ("even_zero" if zero else "even") if idx % 2 == 0 \
                    else ("odd_zero"  if zero else "odd")

                iid = self.tree.insert("", "end",
                                       values=(code, designation, unite,
                                               fournisseur, prix_fmt),
                                       tags=(tag,))
                self.code_mapping[iid]    = code
                self.idunite_mapping[iid] = idunite
            except Exception:
                return

        try:
            n_str = f"{len(rows):,}".replace(",", "\u202f")
            self.lbl_count.configure(text=f"Nombre d'articles : {n_str}")
            self.lbl_status.configure(text="")
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    #  Recherche (KeyRelease)
    # ─────────────────────────────────────────────────────────────────────────
    def search_data(self, event=None):
        self.load_data_async(self.entry_search.get().strip())

    # ─────────────────────────────────────────────────────────────────────────
    #  Double-clic → historique
    # ─────────────────────────────────────────────────────────────────────────
    def _on_row_double_click(self, event):
        if self.is_opening_window:
            return
        sel = self.tree.selection()
        if not sel:
            return
        iid     = sel[0]
        values  = self.tree.item(iid, "values")
        idunite = self.idunite_mapping.get(iid)
        if not idunite:
            return

        self.is_opening_window = True
        try:
            HistoriquePrixWindow(self, self.connect_db,
                                 values[0], values[1], values[2], idunite)
        finally:
            self.after(400, lambda: setattr(self, 'is_opening_window', False))


# ─────────────────────────────────────────────────────────────────────────────
#  Test standalone
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Prix de Revient")
    root.geometry("1200x700")
    root.minsize(800, 500)

    page = PagePrixRevient(root, db_connector=None, iduser=1)
    page.pack(fill="both", expand=True)

    root.mainloop()