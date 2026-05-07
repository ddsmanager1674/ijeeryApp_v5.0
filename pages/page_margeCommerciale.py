import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import json
from datetime import datetime, timedelta
import threading
from tkinter import ttk
from resource_utils import get_config_path, safe_file_read

# ── Thème iJeery ──────────────────────────────────────────────────────────────
try:
    from app_theme import Colors, Fonts, styled, Theme
    _T = True
except ImportError:
    _T = False


class _C:
    MIDNIGHT       = "#2C3E50"
    BG_PAGE        = "#ECF0F1"
    BG_CARD        = "#FFFFFF"
    BG_HEADER      = "#2C3E50"
    BG_INPUT       = "#F4F6F8"
    PRIMARY        = "#3498DB"
    PRIMARY_HOVER  = "#2980B9"
    SUCCESS        = "#2ECC71"
    SUCCESS_DARK   = "#27AE60"
    DANGER         = "#E74C3C"
    DANGER_DARK    = "#C0392B"
    WARNING        = "#F39C12"
    WARNING_LIGHT  = "#FEF9E7"
    WARNING_TEXT   = "#9A6A00"
    INFO           = "#1ABC9C"
    INFO_DARK      = "#16A085"
    TEXT_PRIMARY   = "#2C3E50"
    TEXT_SECONDARY = "#5D6D7E"
    TEXT_MUTED     = "#95A5A6"
    BORDER         = "#D5D8DC"
    DIVIDER        = "#E8EAED"


C = Colors if _T else _C


# ── Style Treeview ────────────────────────────────────────────────────────────
def _apply_tree_style():
    s = ttk.Style()
    try:
        s.theme_use("clam")
    except Exception:
        pass
    s.configure("Stock.Treeview",
                 background=C.BG_CARD, foreground=C.TEXT_PRIMARY,
                 fieldbackground=C.BG_CARD, rowheight=24,
                 font=("Roboto" if _T else "Segoe UI", 10),
                 borderwidth=0)
    s.configure("Stock.Treeview.Heading",
                 background=C.BG_HEADER, foreground="#FFFFFF",
                 font=("Roboto" if _T else "Segoe UI", 10, "bold"),
                 relief="flat", padding=(6, 4))
    s.map("Stock.Treeview",
          background=[("selected", C.PRIMARY)],
          foreground=[("selected", "#FFFFFF")])


# ── Importations des classes externes ─────────────────────────────────────────
from pages.page_peremption import PageGestionPeremption
from pages.page_inventaire import PageInventaire


# ====================================================================
# PageStock
# ====================================================================

class PageStock(ctk.CTkFrame):

    def __init__(self, master, db_conn=None, session_data=None, iduser=None):
        super().__init__(master, fg_color=C.BG_PAGE)
        self.clignotement_actif = False
        self.couleur_alerte     = C.DANGER

        if iduser is not None:
            self.iduser = iduser
        elif session_data and 'user_id' in session_data:
            self.iduser = session_data['user_id']
        else:
            self.iduser = 1

        self.magasins            = []
        self.colonnes_dynamiques = []
        self.filtre_magasin      = "Tous"
        self.filtre_marge        = "Toutes"
        self.combo_filtre_magasin = None
        self.combo_filtre_marge   = None
        self.all_data            = []
        self._col_visible_default = {
            "Prix d'achat": False,
            "Frais/Charges": False,
            "Marge (%)": False,
            "Fournisseur": False,          # ← caché par défaut
        }
        self._col_widths         = {}
        self._col_menu           = None
        self._col_listbox        = None
        self._magasin_cols       = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        _apply_tree_style()
        self.setup_ui()
        self.charger_magasins()
        self.charger_stocks()

    # ── helper font ──────────────────────────────────────────────────────────
    def _f(self, size=11, weight="normal"):
        return ctk.CTkFont(
            family="Roboto" if _T else "Segoe UI",
            size=size, weight=weight)

    # ====================================================================
    # setup_ui
    # ====================================================================

    def setup_ui(self):
        # ── En-tête ───────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=C.BG_HEADER, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            hdr, text="Marge Commerciale",
            font=self._f(18, "bold"), text_color="#FFFFFF"
        ).pack(side="left", padx=16, pady=10)

        # ── Barre filtres + actions ────────────────────────────────────────
        panel = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=8)
        panel.grid(row=1, column=0, sticky="ew", padx=12, pady=6)

        inner = ctk.CTkFrame(panel, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=8)

        # Recherche
        ctk.CTkLabel(
            inner, text="🔍", font=self._f(13), text_color=C.TEXT_MUTED
        ).pack(side="left", padx=(0, 4))

        self.entry_recherche = ctk.CTkEntry(
            inner,
            placeholder_text="Code, désignation…",
            width=280, height=30,
            fg_color=C.BG_INPUT, border_color=C.BORDER,
            text_color=C.TEXT_PRIMARY, font=self._f(10))
        self.entry_recherche.pack(side="left", padx=(0, 6))
        self.entry_recherche.bind('<KeyRelease>', lambda e: self.filtrer_stocks())

        ctk.CTkLabel(
            inner, text="Marge par magasin :", font=self._f(10),
            text_color=C.TEXT_SECONDARY
        ).pack(side="left", padx=(8, 4))

        self.combo_filtre_magasin = ctk.CTkComboBox(
            inner,
            values=["Tous"],
            width=190, height=30,
            fg_color=C.BG_INPUT, border_color=C.BORDER,
            button_color=C.PRIMARY, button_hover_color=C.PRIMARY_HOVER,
            text_color=C.TEXT_PRIMARY, font=self._f(10),
            command=self.on_filtre_magasin_change
        )
        self.combo_filtre_magasin.set("Tous")
        self.combo_filtre_magasin.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            inner, text="Filtre par marge :", font=self._f(10),
            text_color=C.TEXT_SECONDARY
        ).pack(side="left", padx=(2, 4))

        self.combo_filtre_marge = ctk.CTkComboBox(
            inner,
            values=["Toutes", "Perte", "Marge faible", "Marge moyenne", "Bonne marge"],
            width=170, height=30,
            fg_color=C.BG_INPUT, border_color=C.BORDER,
            button_color=C.PRIMARY, button_hover_color=C.PRIMARY_HOVER,
            text_color=C.TEXT_PRIMARY, font=self._f(10),
            command=self.on_filtre_marge_change
        )
        self.combo_filtre_marge.set("Toutes")
        self.combo_filtre_marge.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            inner, text="Réinitialiser",
            command=self.reinitialiser_filtre,
            fg_color="transparent", hover_color=C.DIVIDER,
            text_color=C.TEXT_SECONDARY,
            border_width=1, border_color=C.BORDER,
            height=30, width=110, font=self._f(10)
        ).pack(side="left", padx=(0, 4))

        ctk.CTkLabel(
            inner, text="Afficher :", font=self._f(10),
            text_color=C.TEXT_SECONDARY
        ).pack(side="left", padx=(8, 4))

        btn_afficher = ctk.CTkButton(
            inner, text="Sélection ▾",
            command=self._toggle_afficher_menu,
            fg_color=C.BG_INPUT, hover_color=C.DIVIDER,
            text_color=C.TEXT_PRIMARY,
            border_width=1, border_color=C.BORDER,
            height=30, width=110, font=self._f(10)
        )
        btn_afficher.pack(side="left", padx=(0, 8))

        self.btn_export = ctk.CTkButton(
            inner, text="📊  Export Excel",
            command=self.exporter_stocks,
            fg_color=C.INFO_DARK, hover_color=C.INFO,
            text_color="#FFFFFF",
            height=30, width=140, font=self._f(10, "bold"))
        self.btn_export.pack(side="right", padx=(6, 0))

        # ── Zone Treeview ─────────────────────────────────────────────────
        self.tree_frame_inner = ctk.CTkFrame(
            self, fg_color=C.BG_CARD, corner_radius=8)
        self.tree_frame_inner.grid(
            row=2, column=0, sticky="nsew", padx=12, pady=(0, 4))
        self.tree_frame_inner.grid_rowconfigure(0, weight=1)
        self.tree_frame_inner.grid_columnconfigure(0, weight=1)
        self.tree = None

        # ── Footer ────────────────────────────────────────────────────────
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=12, pady=(2, 8))

        self.label_total_articles = ctk.CTkLabel(
            footer, text="Total articles : 0",
            font=self._f(10, "bold"), text_color=C.PRIMARY)
        self.label_total_articles.pack(side="left")

        legende = ctk.CTkFrame(footer, fg_color="transparent")
        legende.pack(side="left", padx=(14, 0))

        def _item_legende(couleur, texte):
            bloc = ctk.CTkFrame(legende, fg_color="transparent")
            bloc.pack(side="left", padx=(0, 10))
            ctk.CTkLabel(
                bloc, text="■", font=self._f(11, "bold"), text_color=couleur
            ).pack(side="left", padx=(0, 3))
            ctk.CTkLabel(
                bloc, text=texte, font=self._f(9), text_color=C.TEXT_SECONDARY
            ).pack(side="left")

        _item_legende("#E74C3C", "Marge < 0 : Perte")
        _item_legende("#E67E22", "0% à 10% : Marge faible")
        _item_legende("#B7950B", "10% à 30% : Marge moyenne")
        _item_legende("#1E8449", "> 30% : Bonne marge")

        self.label_marge_beneficiaire = ctk.CTkLabel(
            footer, text="Marge Beneficiaire : 0,00 Ar",
            font=self._f(16, "bold"), text_color=C.TEXT_SECONDARY)
        self.label_marge_beneficiaire.pack(side="right")

    # ====================================================================
    # LOGIQUE MÉTIER
    # ====================================================================

    def connect_db(self):
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
        except Exception as err:
            messagebox.showerror("Erreur de connexion", f"Erreur : {err}")
            return None

    def formater_nombre(self, nombre):
        try:
            v = float(nombre)
            if v % 1 == 0:
                n = f"{int(v):,}"
                return n.replace(",", "X").replace(".", ",").replace("X", ".")
            else:
                n = f"{v:,.2f}"
                n = n.replace(",", "X").replace(".", ",").replace("X", ".")
                return n
        except:
            return "0,00"

    def formater_pourcentage(self, valeur):
        try:
            return f"{float(valeur):,.2f}%".replace(',', ' ').replace('.', ',').replace(' ', '.')
        except:
            return "0,00%"

    def parser_nombre(self, texte):
        try:
            s = str(texte).strip().replace('%', '')
            s = s.replace('.', '').replace(',', '.')
            return float(s) if s else 0.0
        except:
            return 0.0

    def creer_treeview(self):
        if self.tree:
            self.tree.destroy()

        # ── "Fournisseur" inséré en position 3, juste après "Unité" ──────
        colonnes_fixes = (
            "Code",
            "Désignation",
            "Unité",
            "Fournisseur",          # ← nouveau
            "Prix d'achat",
            "Frais/Charges",
            "Prix de revient",
            "Prix de vente",
            "Marge Unitaire",
            "Marge (%)"
        )
        colonnes_magasins = [mag[1] for mag in self.magasins]
        self._magasin_cols = list(colonnes_magasins)
        self.colonnes_dynamiques = colonnes_fixes + tuple(colonnes_magasins) + ("Total", "Marge Total")

        self.tree = ttk.Treeview(
            self.tree_frame_inner,
            columns=self.colonnes_dynamiques,
            show="headings",
            style="Stock.Treeview",
            selectmode="browse")

        self.tree.tag_configure("even",           background=C.BG_CARD,  foreground=C.TEXT_PRIMARY)
        self.tree.tag_configure("odd",            background="#F0F4F8",  foreground=C.TEXT_PRIMARY)
        self.tree.tag_configure("marge_loss_even",background=C.BG_CARD,  foreground="#E74C3C")
        self.tree.tag_configure("marge_loss_odd", background="#F0F4F8",  foreground="#E74C3C")
        self.tree.tag_configure("marge_low_even", background=C.BG_CARD,  foreground="#E67E22")
        self.tree.tag_configure("marge_low_odd",  background="#F0F4F8",  foreground="#E67E22")
        self.tree.tag_configure("marge_mid_even", background=C.BG_CARD,  foreground="#B7950B")
        self.tree.tag_configure("marge_mid_odd",  background="#F0F4F8",  foreground="#B7950B")
        self.tree.tag_configure("marge_good_even",background=C.BG_CARD,  foreground="#1E8449")
        self.tree.tag_configure("marge_good_odd", background="#F0F4F8",  foreground="#1E8449")

        self.tree.bind("<Double-1>", self.ouvrir_inventaire_double_clic)

        vsb = ctk.CTkScrollbar(self.tree_frame_inner, orientation="vertical",   command=self.tree.yview)
        hsb = ctk.CTkScrollbar(self.tree_frame_inner, orientation="horizontal",  command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=(6, 0))
        vsb.grid(row=0, column=1, sticky="ns",  pady=(6, 0))
        hsb.grid(row=1, column=0, sticky="ew",  padx=(6, 0))

        for col in self.colonnes_dynamiques:
            self.tree.heading(col, text=col)
            if col == "Désignation":
                self.tree.column(col, width=350, anchor="w",      minwidth=200)
            elif col == "Code":
                self.tree.column(col, width=150, anchor="center")
            elif col == "Fournisseur":
                self.tree.column(col, width=180, anchor="w",      minwidth=120)
            elif col in ("Prix d'achat", "Frais/Charges", "Prix de revient",
                         "Prix de vente", "Marge Unitaire", "Marge (%)", "Marge Total"):
                self.tree.column(col, width=120, anchor="e")
            elif col == "Total":
                self.tree.column(col, width=110, anchor="center", minwidth=90, stretch=True)
            else:
                self.tree.column(col, width=110, anchor="center")

        self.appliquer_filtre_colonnes_magasin()
        self._init_col_visibility()
        self._apply_column_visibility()

    # ── Visibilité des colonnes ──────────────────────────────────────────────
    def _init_col_visibility(self):
        if self._col_widths:
            return
        for col in self.colonnes_dynamiques:
            try:
                self._col_widths[col] = int(self.tree.column(col, "width"))
            except Exception:
                self._col_widths[col] = 110

    def _apply_column_visibility(self, visible_cols=None):
        if not self.tree:
            return
        if visible_cols is None and self._col_listbox and self._col_listbox.winfo_exists():
            visible_cols = set(self._col_listbox.get(i) for i in self._col_listbox.curselection())
        if visible_cols is None:
            visible_cols = set()
            for col in self.colonnes_dynamiques:
                if col in self._col_visible_default:
                    if self._col_visible_default[col]:
                        visible_cols.add(col)
                else:
                    visible_cols.add(col)

        for col in self.colonnes_dynamiques:
            if col in self._magasin_cols:
                continue
            visible = col in visible_cols
            if visible:
                width = self._col_widths.get(col, 110)
                self.tree.column(col, width=width, minwidth=40, stretch=True)
                self.tree.heading(col, text=col)
            else:
                self.tree.column(col, width=0, minwidth=0, stretch=False)
                self.tree.heading(col, text="")

        for col in self._magasin_cols:
            self.tree.column(col, width=0, minwidth=0, stretch=False)
            self.tree.heading(col, text="")

    def _toggle_afficher_menu(self):
        if self._col_menu and self._col_menu.winfo_exists():
            self._col_menu.destroy()
            self._col_menu = None
            return

        win = ctk.CTkToplevel(self)
        win.title("Afficher")
        win.geometry("220x160")
        win.resizable(False, False)
        if _T:
            Theme.apply_toplevel(win)
        win.transient(self.winfo_toplevel())
        win.grab_set()
        self._col_menu = win

        frm = ctk.CTkFrame(win, fg_color=C.BG_CARD, corner_radius=8)
        frm.pack(fill="both", expand=True, padx=10, pady=10)

        import tkinter as tk
        ctk.CTkLabel(
            frm, text="Colonnes visibles",
            font=self._f(10, "bold"), text_color=C.TEXT_PRIMARY
        ).pack(anchor="w", padx=6, pady=(4, 6))

        lb = tk.Listbox(
            frm, selectmode="multiple",
            height=8, exportselection=False,
            font=("Roboto" if _T else "Segoe UI", 10),
            relief="flat", activestyle="dotbox",
            bg=C.BG_CARD, fg=C.TEXT_PRIMARY,
            selectbackground=C.PRIMARY,
            selectforeground="#FFFFFF",
            bd=0, highlightthickness=1)
        for col in self.colonnes_dynamiques:
            if col in self._magasin_cols:
                continue
            lb.insert("end", col)
        lb.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self._col_listbox = lb

        for i, col in enumerate(self.colonnes_dynamiques):
            if col in self._col_visible_default:
                if self._col_visible_default[col]:
                    lb.selection_set(i)
            else:
                lb.selection_set(i)

        lb.bind("<<ListboxSelect>>", lambda _e: self._apply_column_visibility())
        self._apply_column_visibility()

    def charger_stocks_avec_progression(self):
        progress_window = ctk.CTkToplevel(self.root)
        progress_window.title("Chargement en cours...")
        progress_window.geometry("400x150")
        progress_window.transient(self.root)
        progress_window.grab_set()
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth()  // 2) - 200
        y = (progress_window.winfo_screenheight() // 2) - 75
        progress_window.geometry(f"400x150+{x}+{y}")
        label = ctk.CTkLabel(progress_window, text="Chargement des stocks...", font=self._f(12))
        label.pack(pady=20)
        progress_bar = ttk.Progressbar(progress_window, mode='indeterminate', length=300)
        progress_bar.pack(pady=10)
        progress_bar.start(10)
        ctk.CTkLabel(progress_window, text="Veuillez patienter...", font=self._f(9)).pack(pady=10)

        def charger_en_arriere_plan():
            try:
                self.charger_stocks()
                progress_window.after(0, progress_window.destroy)
            except Exception as e:
                progress_window.after(0, progress_window.destroy)
                messagebox.showerror("Erreur", f"Erreur lors du chargement: {str(e)}")

        threading.Thread(target=charger_en_arriere_plan, daemon=True).start()

    def charger_stocks(self):
        self.creer_treeview()
        self._charger_articles_unites_initiaux()
        threading.Thread(target=self._charger_stocks_calcules_async, daemon=True).start()

    def _charger_articles_unites_initiaux(self):
        """Affiche immédiatement les articles/unités avec stocks à 0."""
        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            # ── Sous-requête scalaire : dernier fournisseur par idunite ────
            cursor.execute("""
                SELECT
                    u.codearticle,
                    a.designation,
                    u.designationunite,
                    COALESCE(
                        (
                            SELECT f.nomfrs
                            FROM tb_commandedetail cd2
                            INNER JOIN tb_fournisseur f ON f.idfrs = cd2.idfrs
                            WHERE cd2.idunite = u.idunite
                              AND cd2.idfrs IS NOT NULL
                            ORDER BY cd2.id DESC
                            LIMIT 1
                        ),
                        'Aucun Fournisseur'
                    ) AS dernier_fournisseur,
                    COALESCE(pc.prix_achat, 0) AS prix_achat,
                    COALESCE(fc.frais_charge, 0) AS frais_charge,
                    COALESCE(dp.prix, 0) AS prix
                FROM tb_unite u
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN (
                    SELECT idunite, AVG(punitcmd) AS prix_achat
                    FROM tb_commandedetail
                    WHERE punitcmd IS NOT NULL
                    GROUP BY idunite
                ) pc ON pc.idunite = u.idunite
                LEFT JOIN (
                    SELECT idunite, AVG(montant_charge) AS frais_charge
                    FROM tb_commandedetail
                    WHERE montant_charge IS NOT NULL
                    GROUP BY idunite
                ) fc ON fc.idunite = u.idunite
                LEFT JOIN (
                    SELECT idunite, AVG(prix) AS prix
                    FROM tb_prix
                    WHERE deleted = 0
                    GROUP BY idunite
                ) dp ON dp.idunite = u.idunite
                WHERE a.deleted = 0 AND COALESCE(u.deleted, 0) = 0
                ORDER BY a.designation ASC, u.codearticle ASC
            """)
            base_rows = cursor.fetchall()
            self.all_data = []
            for code, designation, unite, fournisseur, prix_achat, frais_charge, prix in base_rows:
                prix_achat_val   = float(prix_achat   or 0)
                frais_charge_val = float(frais_charge or 0)
                prix_revient_val = prix_achat_val + frais_charge_val
                prix_vente_val   = float(prix          or 0)
                marge_benef      = prix_vente_val - prix_revient_val
                marge_pct        = ((marge_benef / prix_revient_val) * 100) if prix_revient_val != 0 else 100.0
                valeurs = [
                    code,
                    designation,
                    unite,
                    fournisseur,                              # ← position 3
                    self.formater_nombre(prix_achat_val),    # position 4
                    self.formater_nombre(frais_charge_val),  # position 5
                    self.formater_nombre(prix_revient_val),  # position 6
                    self.formater_nombre(prix_vente_val),    # position 7
                    self.formater_nombre(marge_benef),       # position 8
                    self.formater_pourcentage(marge_pct),    # position 9
                ]
                for _idmag, _nom_mag in self.magasins:
                    valeurs.append(self.formater_nombre(0))
                valeurs.append(self.formater_nombre(0))   # Total
                valeurs.append(self.formater_nombre(0))   # Marge Total
                self.all_data.append((valeurs, 0.0))
            self.recharger_treeview()
        except Exception as e:
            messagebox.showerror("Erreur de chargement", f"Détails : {str(e)}")
        finally:
            cursor.close()
            conn.close()

    def _charger_stocks_calcules_async(self):
        try:
            all_data_calculee = self._calculer_all_data_stocks()
            self.after(0, lambda: self._appliquer_all_data_calculee(all_data_calculee))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Erreur de chargement", f"Détails : {str(e)}"))

    def _calculer_all_data_stocks(self):
        """Exécute la requête consolidée et prépare all_data (avec Fournisseur)."""
        conn = self.connect_db()
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            query_optimisee = """
            WITH unite_hierarchie AS (
                SELECT idarticle, idunite, niveau, qtunite, designationunite
                FROM tb_unite WHERE deleted = 0
            ),
            unite_coeff AS (
                SELECT idarticle, idunite, niveau, qtunite, designationunite,
                    exp(sum(ln(NULLIF(CASE WHEN qtunite > 0 THEN qtunite ELSE 1 END, 0)))
                        OVER (PARTITION BY idarticle ORDER BY niveau
                              ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                    ) as coeff_hierarchique
                FROM unite_hierarchie
            ),
            base_unite_par_article AS (
                SELECT DISTINCT ON (idarticle) idarticle, idunite
                FROM tb_unite WHERE deleted = 0
                ORDER BY idarticle, qtunite ASC, idunite ASC
            ),
            rec  AS (SELECT lf.idarticle, lf.idunite, lf.idmag, SUM(lf.qtlivrefrs) AS quantite FROM tb_livraisonfrs lf WHERE lf.deleted=0 GROUP BY lf.idarticle, lf.idunite, lf.idmag),
            ven  AS (SELECT vd.idarticle, vd.idunite, v.idmag,  SUM(vd.qtvente)    AS quantite FROM tb_ventedetail vd INNER JOIN tb_vente v ON vd.idvente=v.id AND v.deleted=0 AND v.statut='VALIDEE' WHERE vd.deleted=0 GROUP BY vd.idarticle, vd.idunite, v.idmag),
            tin  AS (SELECT t.idarticle,  t.idunite,  t.idmagentree  AS idmag, SUM(t.qttransfert) AS quantite FROM tb_transfertdetail t WHERE t.deleted=0 GROUP BY t.idarticle, t.idunite, t.idmagentree),
            tout AS (SELECT t.idarticle,  t.idunite,  t.idmagsortie  AS idmag, SUM(t.qttransfert) AS quantite FROM tb_transfertdetail t WHERE t.deleted=0 GROUP BY t.idarticle, t.idunite, t.idmagsortie),
            sor  AS (SELECT sd.idarticle, sd.idunite, sd.idmag,                SUM(sd.qtsortie)   AS quantite FROM tb_sortiedetail sd GROUP BY sd.idarticle, sd.idunite, sd.idmag),
            inv  AS (SELECT bu.idarticle, bu.idunite, i.idmag,                 SUM(i.qtinventaire) AS quantite FROM tb_inventaire i INNER JOIN tb_unite u ON i.codearticle=u.codearticle INNER JOIN base_unite_par_article bu ON bu.idarticle=u.idarticle AND bu.idunite=u.idunite GROUP BY bu.idarticle, bu.idunite, i.idmag),
            avo  AS (SELECT ad.idarticle, ad.idunite, ad.idmag,                SUM(ad.qtavoir)    AS quantite FROM tb_avoir a INNER JOIN tb_avoirdetail ad ON a.id=ad.idavoir WHERE a.deleted=0 AND ad.deleted=0 GROUP BY ad.idarticle, ad.idunite, ad.idmag),
            conso AS (SELECT cd.idarticle, cd.idunite, cd.idmag,               SUM(cd.qtconsomme) AS quantite FROM tb_consommationinterne_details cd GROUP BY cd.idarticle, cd.idunite, cd.idmag),
            ech_in  AS (SELECT dce.idarticle, dce.idunite, dce.idmagasin AS idmag, SUM(dce.quantite_entree) AS quantite FROM tb_detailchange_entree dce GROUP BY dce.idarticle, dce.idunite, dce.idmagasin),
            ech_out AS (SELECT dcs.idarticle, dcs.idunite, dcs.idmagasin AS idmag, SUM(dcs.quantite_sortie) AS quantite FROM tb_detailchange_sortie dcs GROUP BY dcs.idarticle, dcs.idunite, dcs.idmagasin),
            mouvements_agreges AS (
                SELECT idarticle, idunite, idmag, quantite, 'reception'            AS type_mouvement FROM rec   UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'vente'                AS type_mouvement FROM ven   UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'transfert_in'         AS type_mouvement FROM tin   UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'transfert_out'        AS type_mouvement FROM tout  UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'sortie'               AS type_mouvement FROM sor   UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'inventaire'           AS type_mouvement FROM inv   UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'avoir'                AS type_mouvement FROM avo   UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'consommation_interne' AS type_mouvement FROM conso UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'echange_entree'       AS type_mouvement FROM ech_in  UNION ALL
                SELECT idarticle, idunite, idmag, quantite, 'echange_sortie'       AS type_mouvement FROM ech_out
            ),
            mouvements_bruts AS (
                SELECT ma.idarticle, ma.idmag,
                       COALESCE(uc.coeff_hierarchique,1) as coeff_source_vers_base,
                       ma.quantite, ma.type_mouvement
                FROM mouvements_agreges ma
                LEFT JOIN unite_coeff uc ON uc.idarticle=ma.idarticle AND uc.idunite=ma.idunite
            ),
            solde_base_par_mag AS (
                SELECT idarticle, idmag,
                    SUM(CASE type_mouvement
                        WHEN 'reception'            THEN  quantite*coeff_source_vers_base
                        WHEN 'transfert_in'         THEN  quantite*coeff_source_vers_base
                        WHEN 'inventaire'           THEN  quantite*coeff_source_vers_base
                        WHEN 'avoir'                THEN  quantite*coeff_source_vers_base
                        WHEN 'echange_entree'       THEN  quantite*coeff_source_vers_base
                        WHEN 'vente'                THEN -quantite*coeff_source_vers_base
                        WHEN 'sortie'               THEN -quantite*coeff_source_vers_base
                        WHEN 'transfert_out'        THEN -quantite*coeff_source_vers_base
                        WHEN 'consommation_interne' THEN -quantite*coeff_source_vers_base
                        WHEN 'echange_sortie'       THEN -quantite*coeff_source_vers_base
                        ELSE 0 END
                    ) as solde_base
                FROM mouvements_bruts GROUP BY idarticle, idmag
            ),
            dernier_prix AS (
                SELECT idunite, AVG(prix) AS prix
                FROM tb_prix
                WHERE deleted = 0
                GROUP BY idunite
            ),
            prix_achat_unite AS (
                SELECT idunite, AVG(punitcmd) AS prix_achat
                FROM tb_commandedetail
                WHERE punitcmd IS NOT NULL
                GROUP BY idunite
            ),
            frais_charge_unite AS (
                SELECT idunite, AVG(montant_charge) AS frais_charge
                FROM tb_commandedetail
                WHERE montant_charge IS NOT NULL
                GROUP BY idunite
            ),
            dernier_fournisseur_unite AS (
                -- Dernier fournisseur (par id DESC) pour chaque idunite
                SELECT DISTINCT ON (cd.idunite)
                    cd.idunite,
                    f.nomfrs
                FROM tb_commandedetail cd
                INNER JOIN tb_fournisseur f ON f.idfrs = cd.idfrs
                WHERE cd.idfrs IS NOT NULL
                ORDER BY cd.idunite, cd.id DESC
            )
            SELECT u.codearticle, a.designation, u.designationunite,
                COALESCE(dfu.nomfrs, 'Aucun Fournisseur')         AS dernier_fournisseur,
                COALESCE(pau.prix_achat, 0)          AS prix_achat,
                COALESCE(fcu.frais_charge, 0)        AS frais_charge,
                COALESCE(dp.prix, 0)                 AS prix,
                u.idarticle, u.idunite, m.idmag,
                COALESCE(sb.solde_base,0) / NULLIF(COALESCE(uc.coeff_hierarchique,1),0) as stock
            FROM tb_unite u
            INNER JOIN tb_article a ON u.idarticle=a.idarticle
            CROSS JOIN tb_magasin m
            LEFT JOIN solde_base_par_mag sb ON sb.idarticle=u.idarticle AND sb.idmag=m.idmag
            LEFT JOIN unite_coeff uc ON uc.idarticle=u.idarticle AND uc.idunite=u.idunite
            LEFT JOIN dernier_prix dp ON dp.idunite = u.idunite
            LEFT JOIN prix_achat_unite pau ON pau.idunite = u.idunite
            LEFT JOIN frais_charge_unite fcu ON fcu.idunite = u.idunite
            LEFT JOIN dernier_fournisseur_unite dfu ON dfu.idunite = u.idunite
            WHERE a.deleted=0 AND m.deleted=0
            ORDER BY a.designation ASC, u.codearticle ASC
            """
            cursor.execute(query_optimisee)
            resultats = cursor.fetchall()
            articles_dict = {}
            # résultat : code, desig, unite, fournisseur, prix_achat,
            #            frais_charge, prix, idarticle, idunite, idmag, stock
            for code, desig, unite, fournisseur, prix_achat, frais_charge, prix, idarticle, idunite, idmag, stock in resultats:
                key = (code, idunite)
                if key not in articles_dict:
                    articles_dict[key] = {
                        'code':          code,
                        'designation':   desig,
                        'unite':         unite,
                        'fournisseur':   fournisseur or 'Aucun Fournisseur',
                        'prix_achat':    prix_achat,
                        'frais_charge':  frais_charge,
                        'prix':          prix,
                        'stocks':        {},
                        'total':         0
                    }
                if idmag:
                    nom_mag   = next((m[1] for m in self.magasins if m[0] == idmag), f"Mag{idmag}")
                    stock_val = max(0, stock or 0)
                    articles_dict[key]['stocks'][nom_mag] = stock_val
                    articles_dict[key]['total'] += stock_val
            all_data = []
            for _idx, (_key, data) in enumerate(articles_dict.items()):
                prix_achat_val   = float(data['prix_achat']   or 0)
                frais_charge_val = float(data['frais_charge'] or 0)
                prix_revient_val = prix_achat_val + frais_charge_val
                prix_vente_val   = float(data['prix']         or 0)
                marge_benef      = prix_vente_val - prix_revient_val
                marge_pct        = ((marge_benef / prix_revient_val) * 100) if prix_revient_val != 0 else 100.0
                valeurs = [
                    data['code'],
                    data['designation'],
                    data['unite'],
                    data['fournisseur'],                      # ← position 3
                    self.formater_nombre(prix_achat_val),    # position 4
                    self.formater_nombre(frais_charge_val),  # position 5
                    self.formater_nombre(prix_revient_val),  # position 6
                    self.formater_nombre(prix_vente_val),    # position 7
                    self.formater_nombre(marge_benef),       # position 8
                    self.formater_pourcentage(marge_pct),    # position 9
                ]
                for _, nom_mag in self.magasins:
                    valeurs.append(self.formater_nombre(data['stocks'].get(nom_mag, 0)))
                valeurs.append(self.formater_nombre(data['total']))   # Total
                valeurs.append(self.formater_nombre(0))               # Marge Total
                all_data.append((valeurs, data['total']))
            return all_data
        except Exception as e:
            print(f"ERREUR DÉTAILLÉE: {e}")
            return []
        finally:
            cursor.close()
            conn.close()

    def _appliquer_all_data_calculee(self, all_data_calculee):
        self.all_data = all_data_calculee
        if self.entry_recherche.get().strip():
            self.filtrer_stocks()
        else:
            self.recharger_treeview()
        self.label_total_articles.configure(text=f"Total articles : {len(self.all_data)}")
        self.mettre_a_jour_badge_peremption()

    def calculer_stock_article(self, idarticle, idunite_cible, idmag=None):
        conn = self.connect_db()
        if not conn: return 0
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT idunite, codearticle, COALESCE(qtunite, 1), COALESCE(niveau, 0)
                FROM tb_unite WHERE idarticle = %s
                ORDER BY COALESCE(niveau, 0) ASC, idunite ASC
            """, (idarticle,))
            unites_liees = cursor.fetchall()
            coeffs_cumules = {}
            coeff_courant  = 1.0
            for idu, _code, qt_u, _niv in unites_liees:
                qt_safe = qt_u if qt_u and qt_u > 0 else 1
                coeff_courant *= qt_safe
                coeffs_cumules[idu] = coeff_courant
            qtunite_affichage = 1
            for idu, _code, _qt_u, _niv in unites_liees:
                if idu == idunite_cible:
                    qtunite_affichage = coeffs_cumules.get(idu, 1)
                    break
            total_stock_global_base = 0
            for idu_boucle, code_boucle, _qtunite_boucle, _niv in unites_liees:
                coeff_source = coeffs_cumules.get(idu_boucle, 1)
                q_rec = "SELECT COALESCE(SUM(qtlivrefrs), 0) FROM tb_livraisonfrs WHERE idarticle = %s AND idunite = %s AND deleted = 0"
                p_rec = [idarticle, idu_boucle]
                if idmag: q_rec += " AND idmag = %s"; p_rec.append(idmag)
                cursor.execute(q_rec, p_rec); receptions = cursor.fetchone()[0] or 0
                q_ven = "SELECT COALESCE(SUM(qtvente), 0) FROM tb_ventedetail WHERE idarticle = %s AND idunite = %s AND deleted = 0"
                p_ven = [idarticle, idu_boucle]
                if idmag: q_ven += " AND idmag = %s"; p_ven.append(idmag)
                cursor.execute(q_ven, p_ven); ventes = cursor.fetchone()[0] or 0
                q_sort = "SELECT COALESCE(SUM(qtsortie), 0) FROM tb_sortiedetail WHERE idarticle = %s AND idunite = %s"
                p_sort = [idarticle, idu_boucle]
                if idmag: q_sort += " AND idmag = %s"; p_sort.append(idmag)
                cursor.execute(q_sort, p_sort); sorties = cursor.fetchone()[0] or 0
                cursor.execute("SELECT COALESCE(SUM(qttransfert), 0) FROM tb_transfertdetail WHERE idarticle = %s AND idunite = %s AND deleted = 0" + (" AND idmagentree = %s" if idmag else ""), ([idarticle, idu_boucle, idmag] if idmag else [idarticle, idu_boucle]))
                t_in = cursor.fetchone()[0] or 0
                cursor.execute("SELECT COALESCE(SUM(qttransfert), 0) FROM tb_transfertdetail WHERE idarticle = %s AND idunite = %s AND deleted = 0" + (" AND idmagsortie = %s" if idmag else ""), ([idarticle, idu_boucle, idmag] if idmag else [idarticle, idu_boucle]))
                t_out = cursor.fetchone()[0] or 0
                q_inv = "SELECT COALESCE(SUM(qtinventaire), 0) FROM tb_inventaire WHERE codearticle = %s"
                p_inv = [code_boucle]
                if idmag: q_inv += " AND idmag = %s"; p_inv.append(idmag)
                cursor.execute(q_inv, p_inv); inv = cursor.fetchone()[0] or 0
                q_avoir = """
                    SELECT COALESCE(SUM(ad.qtavoir), 0)
                    FROM tb_avoirdetail ad INNER JOIN tb_avoir a ON ad.idavoir = a.id
                    WHERE ad.idarticle = %s AND ad.idunite = %s AND a.deleted = 0 AND ad.deleted = 0
                """
                p_avoir = [idarticle, idu_boucle]
                if idmag: q_avoir += " AND ad.idmag = %s"; p_avoir.append(idmag)
                cursor.execute(q_avoir, p_avoir); avoirs = cursor.fetchone()[0] or 0
                q_conso = "SELECT COALESCE(SUM(qtconsomme), 0) FROM tb_consommationinterne_details WHERE idarticle = %s AND idunite = %s"
                p_conso = [idarticle, idu_boucle]
                if idmag: q_conso += " AND idmag = %s"; p_conso.append(idmag)
                cursor.execute(q_conso, p_conso); consommations = cursor.fetchone()[0] or 0
                q_ech_in = "SELECT COALESCE(SUM(quantite_entree), 0) FROM tb_detailchange_entree WHERE idarticle = %s AND idunite = %s"
                p_ech_in = [idarticle, idu_boucle]
                if idmag: q_ech_in += " AND idmagasin = %s"; p_ech_in.append(idmag)
                cursor.execute(q_ech_in, p_ech_in); echange_entrees = cursor.fetchone()[0] or 0
                q_ech_out = "SELECT COALESCE(SUM(quantite_sortie), 0) FROM tb_detailchange_sortie WHERE idarticle = %s AND idunite = %s"
                p_ech_out = [idarticle, idu_boucle]
                if idmag: q_ech_out += " AND idmagasin = %s"; p_ech_out.append(idmag)
                cursor.execute(q_ech_out, p_ech_out); echange_sorties = cursor.fetchone()[0] or 0
                solde_unite = (receptions + t_in + inv + avoirs + echange_entrees
                               - ventes - sorties - t_out - consommations - echange_sorties)
                total_stock_global_base += (solde_unite * coeff_source)
            return max(0, total_stock_global_base / qtunite_affichage)
        except Exception as e:
            print(f"Erreur calcul stock consolidé : {e}")
            return 0
        finally:
            cursor.close()
            conn.close()

    def charger_magasins(self):
        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT idmag, designationmag FROM tb_magasin
                WHERE deleted = 0 ORDER BY designationmag
            """)
            self.magasins = cursor.fetchall()
            if self.combo_filtre_magasin is not None:
                options = ["Tous"] + [nom_mag for _, nom_mag in self.magasins]
                self.combo_filtre_magasin.configure(values=options)
                if self.filtre_magasin not in options:
                    self.filtre_magasin = "Tous"
                self.combo_filtre_magasin.set(self.filtre_magasin)
                self.appliquer_filtre_colonnes_magasin()
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger les magasins : {str(e)}")
        finally:
            cursor.close()
            conn.close()

    def on_filtre_magasin_change(self, valeur):
        self.filtre_magasin = (valeur or "Tous").strip() or "Tous"
        self.appliquer_filtre_colonnes_magasin()
        if self.entry_recherche.get().strip():
            self.filtrer_stocks()
        else:
            self.recharger_treeview()

    def on_filtre_marge_change(self, valeur):
        self.filtre_marge = (valeur or "Toutes").strip() or "Toutes"
        if self.entry_recherche.get().strip():
            self.filtrer_stocks()
        else:
            self.recharger_treeview()

    def appliquer_filtre_colonnes_magasin(self):
        if not self.tree:
            return
        colonnes_magasins = [nom_mag for _, nom_mag in self.magasins]
        afficher_total = (self.filtre_magasin == "Tous")
        for nom_col in colonnes_magasins:
            if self.filtre_magasin != "Tous" and nom_col == self.filtre_magasin:
                self.tree.column(nom_col, width=110, minwidth=80, stretch=True, anchor="center")
            else:
                self.tree.column(nom_col, width=0, minwidth=0, stretch=False, anchor="center")
        if afficher_total:
            self.tree.column("Total", width=110, minwidth=90, stretch=True, anchor="center")
        else:
            self.tree.column("Total", width=0, minwidth=0, stretch=False, anchor="center")

    def _valeurs_avec_marge_totale(self, valeurs):
        try:
            valeurs_out    = list(valeurs)
            idx_marge_benef = self.colonnes_dynamiques.index("Marge Unitaire")
            idx_total       = self.colonnes_dynamiques.index("Total")
            idx_marge_total = self.colonnes_dynamiques.index("Marge Total")
            marge_benef     = self.parser_nombre(valeurs_out[idx_marge_benef])

            if self.filtre_magasin == "Tous":
                stock_courant = self.parser_nombre(valeurs_out[idx_total])
            else:
                if self.filtre_magasin in self.colonnes_dynamiques:
                    idx_mag = self.colonnes_dynamiques.index(self.filtre_magasin)
                    stock_courant = self.parser_nombre(valeurs_out[idx_mag])
                else:
                    stock_courant = 0.0

            marge_totale = marge_benef * stock_courant
            valeurs_out[idx_marge_total] = self.formater_nombre(marge_totale)
            return valeurs_out
        except Exception:
            return list(valeurs)

    def _maj_label_marge_beneficiaire(self, total_marge):
        try:
            self.label_marge_beneficiaire.configure(
                text=f"Marge Beneficiaire : {self.formater_nombre(total_marge)} Ar"
            )
        except Exception:
            pass

    def _tag_marge(self, valeurs, idx):
        zebra = "even" if idx % 2 == 0 else "odd"
        try:
            idx_marge_pct = self.colonnes_dynamiques.index("Marge (%)")
            marge_pct = self.parser_nombre(valeurs[idx_marge_pct])
            if marge_pct < 0:
                return f"marge_loss_{zebra}"
            if marge_pct <= 10:
                return f"marge_low_{zebra}"
            if marge_pct <= 30:
                return f"marge_mid_{zebra}"
            return f"marge_good_{zebra}"
        except Exception:
            return zebra

    def _match_filtre_marge(self, valeurs):
        if self.filtre_marge == "Toutes":
            return True
        try:
            idx_marge_pct = self.colonnes_dynamiques.index("Marge (%)")
            marge_pct = self.parser_nombre(valeurs[idx_marge_pct])
            if self.filtre_marge == "Perte":
                return marge_pct < 0
            if self.filtre_marge == "Marge faible":
                return 0 <= marge_pct <= 10
            if self.filtre_marge == "Marge moyenne":
                return 10 < marge_pct <= 30
            if self.filtre_marge == "Bonne marge":
                return marge_pct > 30
            return True
        except Exception:
            return True

    def ouvrir_inventaire_double_clic(self, event):
        """Affiche le détail article, historiques de prix et simulateur."""
        selection = self.tree.selection()
        if not selection:
            return
        item = self.tree.item(selection[0])
        valeurs = item.get('values') or []
        if not valeurs or (len(valeurs) > 1 and "Aucun" in str(valeurs[1])):
            return

        # ── Indices mis à jour après insertion de "Fournisseur" en pos 3 ──
        code_article  = str(valeurs[0]).zfill(10)
        designation   = str(valeurs[1]) if len(valeurs) > 1 else ""
        unite         = str(valeurs[2]) if len(valeurs) > 2 else ""
        # valeurs[3] = Fournisseur  (ignoré ici, pas utilisé dans la modale)
        prix_achat    = self.parser_nombre(valeurs[4]) if len(valeurs) > 4 else 0.0
        frais_charge  = self.parser_nombre(valeurs[5]) if len(valeurs) > 5 else 0.0
        prix_revient  = self.parser_nombre(valeurs[6]) if len(valeurs) > 6 else prix_achat
        prix_vente    = self.parser_nombre(valeurs[7]) if len(valeurs) > 7 else 0.0
        marge_unitaire= self.parser_nombre(valeurs[8]) if len(valeurs) > 8 else (prix_vente - prix_revient)
        marge_pct     = self.parser_nombre(valeurs[9]) if len(valeurs) > 9 else 0.0

        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.idarticle, u.idunite, a.designation
                FROM tb_unite u INNER JOIN tb_article a ON u.idarticle = a.idarticle
                WHERE u.codearticle = %s LIMIT 1
            """, (str(code_article),))
            result = cursor.fetchone()
            if not result:
                messagebox.showwarning("Erreur", f"Article {code_article} introuvable")
                return
            idarticle, idunite, designation_db = result
            designation = designation_db or designation

            cursor.execute("""
                SELECT id, COALESCE(punitcmd, 0)
                FROM tb_commandedetail
                WHERE idunite = %s AND punitcmd IS NOT NULL
                ORDER BY id DESC LIMIT 200
            """, (idunite,))
            hist_achat = cursor.fetchall()

            cursor.execute("""
                SELECT id, COALESCE(montant_charge, 0)
                FROM tb_commandedetail
                WHERE idunite = %s AND montant_charge IS NOT NULL
                ORDER BY id DESC LIMIT 200
            """, (idunite,))
            hist_charge = cursor.fetchall()

            cursor.execute("""
                SELECT id, COALESCE(prix, 0), dateregistre
                FROM tb_prix
                WHERE idunite = %s AND deleted = 0
                ORDER BY dateregistre DESC, id DESC LIMIT 200
            """, (idunite,))
            hist_vente = cursor.fetchall()

            avg_achat  = (sum(float(v[1] or 0) for v in hist_achat)  / len(hist_achat))  if hist_achat  else 0.0
            avg_charge = (sum(float(v[1] or 0) for v in hist_charge) / len(hist_charge)) if hist_charge else 0.0
            avg_vente  = (sum(float(v[1] or 0) for v in hist_vente)  / len(hist_vente))  if hist_vente  else 0.0

            self._ouvrir_detail_article_modal(
                code_article=code_article,
                designation=designation,
                unite=unite,
                prix_achat=prix_achat,
                frais_charge=frais_charge,
                prix_revient=prix_revient,
                prix_vente=prix_vente,
                marge_unitaire=marge_unitaire,
                marge_pct=marge_pct,
                hist_achat=hist_achat,
                hist_charge=hist_charge,
                hist_vente=hist_vente,
                avg_achat=avg_achat,
                avg_charge=avg_charge,
                avg_vente=avg_vente,
            )
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'ouverture : {str(e)}")
        finally:
            cursor.close()
            conn.close()

    def _ouvrir_detail_article_modal(
        self,
        code_article, designation, unite,
        prix_achat, frais_charge, prix_revient, prix_vente,
        marge_unitaire, marge_pct,
        hist_achat, hist_charge, hist_vente,
        avg_achat, avg_charge, avg_vente,
    ):
        win = ctk.CTkToplevel(self)
        win.title("Détail Marge Commerciale")
        win.geometry("980x680")
        if _T:
            Theme.apply_toplevel(win)
        win.transient(self.winfo_toplevel())
        win.grab_set()

        main = ctk.CTkFrame(win, fg_color=C.BG_PAGE)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        info = ctk.CTkFrame(main, fg_color=C.BG_CARD, corner_radius=8)
        info.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            info,
            text=(
                f"Code: {code_article}   |   Désignation: {designation}   |   Unité: {unite}\n"
                f"Prix d'achat: {self.formater_nombre(prix_achat)} Ar   |   "
                f"Frais/Charges: {self.formater_nombre(frais_charge)} Ar   |   "
                f"Prix de revient: {self.formater_nombre(prix_revient)} Ar\n"
                f"Prix de vente: {self.formater_nombre(prix_vente)} Ar   |   "
                f"Marge unitaire: {self.formater_nombre(marge_unitaire)} Ar ({self.formater_pourcentage(marge_pct)})"
            ),
            justify="left", anchor="w",
            font=self._f(10, "bold"), text_color=C.TEXT_PRIMARY
        ).pack(fill="x", padx=12, pady=10)

        hist_wrap = ctk.CTkFrame(main, fg_color="transparent")
        hist_wrap.pack(fill="both", expand=True, pady=(0, 8))
        hist_wrap.grid_columnconfigure(0, weight=1)
        hist_wrap.grid_columnconfigure(1, weight=1)
        hist_wrap.grid_columnconfigure(2, weight=1)
        hist_wrap.grid_rowconfigure(0, weight=1)

        fr_achat = ctk.CTkFrame(hist_wrap, fg_color=C.BG_CARD, corner_radius=8)
        fr_achat.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        ctk.CTkLabel(fr_achat,
            text=f"Historique Prix d'achat (Moyenne: {self.formater_nombre(avg_achat)} Ar)",
            font=self._f(10, "bold"), text_color=C.TEXT_PRIMARY
        ).pack(anchor="w", padx=10, pady=(8, 4))
        tv_achat = ttk.Treeview(fr_achat, columns=("id", "val"), show="headings", height=12, style="Stock.Treeview")
        tv_achat.heading("id",  text="N°");         tv_achat.column("id",  width=80,  anchor="center")
        tv_achat.heading("val", text="Prix d'achat"); tv_achat.column("val", width=140, anchor="e")
        tv_achat.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        for _id, val in hist_achat:
            tv_achat.insert("", "end", values=(_id, self.formater_nombre(val)))

        fr_charge = ctk.CTkFrame(hist_wrap, fg_color=C.BG_CARD, corner_radius=8)
        fr_charge.grid(row=0, column=1, sticky="nsew", padx=(5, 5))
        ctk.CTkLabel(fr_charge,
            text=f"Historique Frais/Charges (Moyenne: {self.formater_nombre(avg_charge)} Ar)",
            font=self._f(10, "bold"), text_color=C.TEXT_PRIMARY
        ).pack(anchor="w", padx=10, pady=(8, 4))
        tv_charge = ttk.Treeview(fr_charge, columns=("id", "val"), show="headings", height=12, style="Stock.Treeview")
        tv_charge.heading("id",  text="N°");           tv_charge.column("id",  width=80,  anchor="center")
        tv_charge.heading("val", text="Frais/Charges"); tv_charge.column("val", width=140, anchor="e")
        tv_charge.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        for _id, val in hist_charge:
            tv_charge.insert("", "end", values=(_id, self.formater_nombre(val)))

        fr_vente = ctk.CTkFrame(hist_wrap, fg_color=C.BG_CARD, corner_radius=8)
        fr_vente.grid(row=0, column=2, sticky="nsew", padx=(5, 0))
        ctk.CTkLabel(fr_vente,
            text=f"Historique Prix de vente (Moyenne: {self.formater_nombre(avg_vente)} Ar)",
            font=self._f(10, "bold"), text_color=C.TEXT_PRIMARY
        ).pack(anchor="w", padx=10, pady=(8, 4))
        tv_vente = ttk.Treeview(fr_vente, columns=("id", "date", "val"), show="headings", height=12, style="Stock.Treeview")
        tv_vente.heading("id",   text="N°");            tv_vente.column("id",   width=70,  anchor="center")
        tv_vente.heading("date", text="Date");           tv_vente.column("date", width=120, anchor="center")
        tv_vente.heading("val",  text="Prix de vente"); tv_vente.column("val",  width=140, anchor="e")
        tv_vente.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        for _id, val, dte in hist_vente:
            dte_txt = dte.strftime("%d/%m/%Y") if dte else ""
            tv_vente.insert("", "end", values=(_id, dte_txt, self.formater_nombre(val)))

        sim = ctk.CTkFrame(main, fg_color=C.BG_CARD, corner_radius=8)
        sim.pack(fill="x")
        ctk.CTkLabel(sim, text="Simulateur", font=self._f(10, "bold"), text_color=C.TEXT_PRIMARY).pack(anchor="w", padx=10, pady=(8, 4))

        row = ctk.CTkFrame(sim, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkLabel(row, text="Prix d'achat",   font=self._f(9), text_color=C.TEXT_SECONDARY).pack(side="left")
        ent_achat = ctk.CTkEntry(row, width=110, height=28)
        ent_achat.insert(0, self.formater_nombre(prix_achat))
        ent_achat.pack(side="left", padx=(6, 10))

        ctk.CTkLabel(row, text="Frais/Charges",  font=self._f(9), text_color=C.TEXT_SECONDARY).pack(side="left")
        ent_charge = ctk.CTkEntry(row, width=110, height=28)
        ent_charge.insert(0, self.formater_nombre(frais_charge))
        ent_charge.pack(side="left", padx=(6, 10))

        ctk.CTkLabel(row, text="Prix de vente",  font=self._f(9), text_color=C.TEXT_SECONDARY).pack(side="left")
        ent_vente = ctk.CTkEntry(row, width=110, height=28)
        ent_vente.insert(0, self.formater_nombre(prix_vente))
        ent_vente.pack(side="left", padx=(6, 10))

        ctk.CTkLabel(row, text="Stock",          font=self._f(9), text_color=C.TEXT_SECONDARY).pack(side="left")
        ent_stock = ctk.CTkEntry(row, width=110, height=28)
        ent_stock.insert(0, "0,00")
        ent_stock.pack(side="left", padx=(6, 12))

        lbl_res = ctk.CTkLabel(row, text="", font=self._f(9, "bold"), text_color=C.TEXT_PRIMARY)
        lbl_res.pack(side="left", padx=(8, 0))

        def _simuler(*_):
            pa = self.parser_nombre(ent_achat.get())
            fc = self.parser_nombre(ent_charge.get())
            pv = self.parser_nombre(ent_vente.get())
            st = self.parser_nombre(ent_stock.get())
            pr = pa + fc
            mu = pv - pr
            pct = ((mu / pr) * 100) if pr != 0 else 100.0
            mt = mu * st
            lbl_res.configure(
                text=(
                    f"Marge unitaire: {self.formater_nombre(mu)} Ar ({self.formater_pourcentage(pct)})   |   "
                    f"Marge totale: {self.formater_nombre(mt)} Ar"
                )
            )

        for ent in (ent_achat, ent_charge, ent_vente, ent_stock):
            ent.bind("<KeyRelease>", _simuler)
        _simuler()

    def clignoter_bouton(self):
        if not hasattr(self, "btn_peremption"):
            return
        if not self.clignotement_actif:
            self.clignotement_actif = True

        def toggle_color():
            if self.clignotement_actif:
                couleur_actuelle = self.btn_peremption.cget("fg_color")
                nouvelle_couleur = "#ffffff" if couleur_actuelle == self.couleur_alerte else self.couleur_alerte
                self.btn_peremption.configure(fg_color=nouvelle_couleur)
                self.after(500, toggle_color)

        toggle_color()

    def filtrer_stocks(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        search_term = self.entry_recherche.get().lower().strip()
        if not search_term:
            self.recharger_treeview()
            return
        filtered_data = [
            (valeurs, total) for valeurs, total in self.all_data
            if search_term in (
                f"{valeurs[0]} {valeurs[1]} {valeurs[2]} {valeurs[3]} "
                f"{valeurs[4]} {valeurs[5]} {valeurs[6]} {valeurs[7]} "
                f"{valeurs[8]} {valeurs[9]}"
            ).lower()
        ]
        filtered_data = [
            (valeurs, total) for valeurs, total in filtered_data
            if self._match_filtre_marge(self._valeurs_avec_marge_totale(valeurs))
        ]
        if filtered_data:
            somme_marge = 0.0
            for idx, (valeurs, total) in enumerate(filtered_data):
                valeurs_aff = self._valeurs_avec_marge_totale(valeurs)
                self.tree.insert("", "end", values=valeurs_aff, tags=(self._tag_marge(valeurs_aff, idx),))
                idx_mt = self.colonnes_dynamiques.index("Marge Total")
                somme_marge += self.parser_nombre(valeurs_aff[idx_mt])
            self.label_total_articles.configure(text=f"Total articles : {len(filtered_data)}")
            self._maj_label_marge_beneficiaire(somme_marge)
        else:
            # 10 colonnes fixes désormais → padding ajusté en conséquence
            empty = ["", "Aucun résultat trouvé", "", "", "", "", "", "", "", ""] + [""] * (len(self.colonnes_dynamiques) - 10)
            self.tree.insert('', 'end', values=empty)
            self.label_total_articles.configure(text="Total articles : 0")
            self._maj_label_marge_beneficiaire(0.0)

    def reinitialiser_filtre(self):
        self.entry_recherche.delete(0, 'end')
        self.filtre_magasin = "Tous"
        self.filtre_marge   = "Toutes"
        if self.combo_filtre_magasin is not None:
            self.combo_filtre_magasin.set("Tous")
        if self.combo_filtre_marge is not None:
            self.combo_filtre_marge.set("Toutes")
        self.appliquer_filtre_colonnes_magasin()
        self.recharger_treeview()

    def recharger_treeview(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        if self.all_data:
            visibles    = 0
            somme_marge = 0.0
            for idx, (valeurs, total) in enumerate(self.all_data):
                valeurs_aff = self._valeurs_avec_marge_totale(valeurs)
                if not self._match_filtre_marge(valeurs_aff):
                    continue
                self.tree.insert("", "end", values=valeurs_aff, tags=(self._tag_marge(valeurs_aff, idx),))
                visibles += 1
                idx_mt = self.colonnes_dynamiques.index("Marge Total")
                somme_marge += self.parser_nombre(valeurs_aff[idx_mt])
            self.label_total_articles.configure(text=f"Total articles : {visibles}")
            self._maj_label_marge_beneficiaire(somme_marge)
        else:
            empty = ["", "Aucun article trouvé", "", "", "", "", "", "", "", ""] + [""] * (len(self.colonnes_dynamiques) - 10)
            self.tree.insert('', 'end', values=empty)
            self.label_total_articles.configure(text="Total articles : 0")
            self._maj_label_marge_beneficiaire(0.0)

    def exporter_stocks(self):
        try:
            from tkinter import filedialog
            import csv
            fichier = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile=f"margecommerciale_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            if not fichier:
                return
            with open(fichier, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(self.colonnes_dynamiques)
                for item in self.tree.get_children():
                    writer.writerow(self.tree.item(item)['values'])
            messagebox.showinfo("Succès", f"Marge commerciale exportée vers :\n{fichier}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'export: {str(e)}")

    def mettre_a_jour_tb_stock(self):
        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.idarticle, u.idunite, u.codearticle, u.designationunite, a.designation
                FROM tb_article a INNER JOIN tb_unite u ON a.idarticle = u.idarticle
                WHERE a.deleted = 0 ORDER BY a.designation ASC, u.codearticle ASC
            """)
            articles = cursor.fetchall()
            compteur_maj = compteur_ins = compteur_total = 0
            for idarticle, idunite, code_art, unite_desig, art_desig in articles:
                for idmag, nom_mag in self.magasins:
                    compteur_total += 1
                    stock_calcule  = self.calculer_stock_article(idarticle, idunite, idmag)
                    cursor.execute("SELECT qtstock FROM tb_stock WHERE codearticle = %s AND idmag = %s",
                                   (str(code_art), idmag))
                    resultat = cursor.fetchone()
                    if resultat:
                        if abs(float(resultat[0] or 0) - float(stock_calcule)) > 0.001:
                            cursor.execute("UPDATE tb_stock SET qtstock = %s WHERE codearticle = %s AND idmag = %s",
                                           (stock_calcule, str(code_art), idmag))
                            compteur_maj += 1
                    else:
                        cursor.execute("INSERT INTO tb_stock (codearticle, idmag, qtstock, qtalert, deleted) VALUES (%s, %s, %s, 0, 0)",
                                       (str(code_art), idmag, stock_calcule))
                        compteur_ins += 1
                    if (compteur_maj + compteur_ins) % 100 == 0:
                        conn.commit()
            conn.commit()
            messagebox.showinfo("Synchronisation réussie",
                                f"✅ {compteur_maj} mises à jour, {compteur_ins} créations, {compteur_total} lignes traitées.")
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur de synchronisation", str(e))
            import traceback; traceback.print_exc()
        finally:
            cursor.close()
            conn.close()

    def ouvrir_fenetre_peremption(self):
        self.fenetre_peremp = ctk.CTkToplevel(self)
        self.fenetre_peremp.title("Suivi des Péremptions")
        self.fenetre_peremp.geometry("1100x700")
        if _T:
            Theme.apply_toplevel(self.fenetre_peremp)
        self.fenetre_peremp.attributes('-topmost', True)
        self.fenetre_peremp.focus_set()
        self.page_peremp = PageGestionPeremption(self.fenetre_peremp, iduser=self.iduser)
        self.page_peremp.pack(fill="both", expand=True, padx=10, pady=10)

    def mettre_a_jour_badge_peremption(self):
        if not hasattr(self, "btn_peremption"):
            return
        conn = self.connect_db()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT l.idarticle, l.idunite, l.dateperemption FROM tb_livraisonfrs l WHERE l.dateperemption IS NOT NULL")
            lignes     = cursor.fetchall()
            aujourdhui = datetime.now().date()
            un_mois    = aujourdhui + timedelta(days=30)
            nb_perimes = nb_urgents = 0
            for id_art, id_uni, d_peremp in lignes:
                stock = self.calculer_stock_article(id_art, id_uni)
                if stock > 0:
                    if d_peremp <= aujourdhui: nb_perimes += 1
                    elif d_peremp <= un_mois:  nb_urgents += 1
            if nb_perimes > 0:
                self.btn_peremption.configure(text=f"🚨  PÉRIMÉS ({nb_perimes})")
                self.couleur_alerte = C.DANGER
                if not self.clignotement_actif:
                    self.clignoter_bouton()
            elif nb_urgents > 0:
                self.clignotement_actif = False
                self.btn_peremption.configure(
                    text=f"⚠️  Alerte ({nb_urgents})",
                    fg_color=C.WARNING, hover_color="#E67E22")
            else:
                self.clignotement_actif = False
                self.btn_peremption.configure(
                    text="🛡️  Articles Périmés",
                    fg_color=C.DANGER, hover_color=C.DANGER_DARK)
        except Exception as e:
            print(f"Erreur badge: {e}")
        finally:
            cursor.close()
            conn.close()


# ── Test standalone ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    app = ctk.CTk()
    app.title("iJeery — Marge Commerciale")
    app.geometry("1100x750")
    if _T:
        Theme.apply(app)
    app.grid_rowconfigure(0, weight=1)
    app.grid_columnconfigure(0, weight=1)
    PageStock(app, iduser=1).grid(row=0, column=0, sticky="nsew")
    app.mainloop()