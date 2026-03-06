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


SQL_STOCK_ALERTE = """
WITH RECURSIVE

    facteur_conversion AS (
        SELECT u.idunite, u.idarticle, u.niveau, u.designationunite,
               1.0::double precision AS facteur_vers_base
        FROM tb_unite u
        WHERE u.niveau = 0 AND u.deleted = 0

        UNION ALL

        SELECT u.idunite, u.idarticle, u.niveau, u.designationunite,
               fc.facteur_vers_base * u.qtunite AS facteur_vers_base
        FROM tb_unite u
        JOIN facteur_conversion fc
          ON fc.idarticle = u.idarticle AND fc.niveau = u.niveau - 1
        WHERE u.deleted = 0
    ),

    -- Unité de niveau MAX par article
    unite_max AS (
        SELECT DISTINCT ON (u.idarticle)
            u.idarticle,
            u.idunite,
            u.codearticle,
            u.designationunite,
            fc.facteur_vers_base
        FROM tb_unite u
        JOIN facteur_conversion fc ON fc.idunite = u.idunite
        WHERE u.deleted = 0
        ORDER BY u.idarticle, u.niveau DESC
    ),

    -- Tous les mouvements (entrées +1 / sorties -1)
    tous_mouvements AS (
        SELECT lf.idunite, lf.idmag, lf.qtlivrefrs AS quantite, 1 AS signe
        FROM tb_livraisonfrs lf WHERE lf.deleted = 0
        UNION ALL
        SELECT u.idunite, inv.idmag, inv.qtinventaire AS quantite, 1 AS signe
        FROM tb_inventaire inv
        JOIN tb_unite u ON u.codearticle = inv.codearticle AND u.niveau = 0 AND u.deleted = 0
        UNION ALL
        SELECT ad.idunite, ad.idmag, ad.qtavoir AS quantite, 1 AS signe
        FROM tb_avoirdetail ad
        JOIN tb_avoir av ON av.id = ad.idavoir
        WHERE ad.deleted = 0 AND av.deleted = 0
        UNION ALL
        SELECT dce.idunite, dce.idmagasin AS idmag,
               dce.quantite_entree::double precision AS quantite, 1 AS signe
        FROM tb_detailchange_entree dce
        JOIN tb_changement chg ON chg.idchg = dce.idchg
        UNION ALL
        SELECT td.idunite, td.idmagentree AS idmag,
               td.qttransfertentree AS quantite, 1 AS signe
        FROM tb_transfertdetail td
        JOIN tb_transfert t ON t.idtransfert = td.idtransfert
        WHERE td.deleted = 0 AND t.deleted = 0
        UNION ALL
        SELECT vd.idunite, vd.idmag, vd.qtvente AS quantite, -1 AS signe
        FROM tb_ventedetail vd
        JOIN tb_vente v ON v.id = vd.idvente
        WHERE vd.deleted = 0 AND v.deleted = 0 AND v.statut = 'VALIDEE'
        UNION ALL
        SELECT sd.idunite, sd.idmag, sd.qtsortie AS quantite, -1 AS signe
        FROM tb_sortiedetail sd
        JOIN tb_sortie s ON s.id = sd.idsortie
        WHERE sd.deleted = 0 AND s.deleted = 0
        UNION ALL
        SELECT cid.idunite, cid.idmag,
               cid.qtconsomme::double precision AS quantite, -1 AS signe
        FROM tb_consommationinterne_details cid
        JOIN tb_consommationinterne ci ON ci.id = cid.idconsommation
        UNION ALL
        SELECT dcs.idunite, dcs.idmagasin AS idmag,
               dcs.quantite_sortie::double precision AS quantite, -1 AS signe
        FROM tb_detailchange_sortie dcs
        JOIN tb_changement chg ON chg.idchg = dcs.idchg
        UNION ALL
        SELECT td.idunite, td.idmagsortie AS idmag,
               td.qttransfertsortie AS quantite, -1 AS signe
        FROM tb_transfertdetail td
        JOIN tb_transfert t ON t.idtransfert = td.idtransfert
        WHERE td.deleted = 0 AND t.deleted = 0
    ),

    -- Stock en unité de base par article × magasin (une seule passe)
    stock_base AS (
        SELECT fc.idarticle, tm.idmag,
               SUM(tm.quantite * fc.facteur_vers_base * tm.signe) AS stock_base_mag
        FROM tous_mouvements tm
        JOIN facteur_conversion fc ON fc.idunite = tm.idunite
        GROUP BY fc.idarticle, tm.idmag
    ),

    -- Stock général (tous magasins) par article
    stock_general AS (
        SELECT idarticle, SUM(stock_base_mag) AS stock_base_gen
        FROM stock_base
        GROUP BY idarticle
    )

SELECT
    um.codearticle,
    a.designation                                                           AS designationarticle,
    um.designationunite                                                     AS unite,
    m.designationmag,
    a.alertdepot                                                            AS alert_mag,
    ROUND((COALESCE(sbm.stock_base_mag, 0.0) / um.facteur_vers_base)::numeric, 4) AS stock_mag,
    a.alert                                                                 AS alert_gen,
    ROUND((COALESCE(sg.stock_base_gen,  0.0) / um.facteur_vers_base)::numeric, 4) AS stock_gen,
    a.idarticle,
    um.idunite,
    a.idmag
FROM tb_article a
JOIN unite_max um    ON um.idarticle = a.idarticle
JOIN tb_magasin m   ON m.idmag = a.idmag AND m.deleted = 0
LEFT JOIN stock_base sbm
       ON sbm.idarticle = a.idarticle AND sbm.idmag = a.idmag
LEFT JOIN stock_general sg
       ON sg.idarticle  = a.idarticle
WHERE a.deleted = 0
ORDER BY a.designation;
"""


class PageStockAlerte(ctk.CTkFrame):
    """UI skeleton for stock alert page; data logic removed."""

    def __init__(self, master, db_conn=None, session_data=None, iduser=None):
        super().__init__(master)
        self.item_ids = {}  # {tree_item_id: (idarticle, idunite, idmag)}
        self.all_rows = []  # Stocker les lignes brutes pour filtrage
        self.setup_ui()
        self.charger_donnees()

    def noop(self, *args, **kwargs):
        pass

    # ------------------------------------------------------------------
    # database utilities
    # ------------------------------------------------------------------
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
        """
        Charge tous les stocks en UN SEUL appel SQL (requête unifiée).
        Plus de thread, plus de StockManager — tout arrive en une passe.
        Colonnes retournées (index) :
          0  codearticle        5  stock_mag
          1  designationarticle 6  alert_gen
          2  unite              7  stock_gen
          3  designationmag     8  idarticle
          4  alert_mag          9  idunite   10 idmag
        """
        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute(SQL_STOCK_ALERTE)
            rows = cur.fetchall()
            self.all_rows = rows
            self.populate_table(rows)
            self.label_statut.configure(
                text=f"Dernière MAJ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            # mettre à jour options magasin après chargement des données
            self._refresh_magasin_filter()
        except Exception as e:
            messagebox.showerror("Erreur SQL", str(e))
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # table population  (plus de placeholder / thread)
    # ------------------------------------------------------------------
    def clear_table(self):
        self.tree.delete(*self.tree.get_children())
        self.item_ids = {}
        self.label_total.configure(text="Total lignes: 0")

    def populate_table(self, rows):
        """
        Insère les lignes dans le treeview avec les valeurs réelles
        (stock_mag et stock_gen déjà calculés) et applique les tags
        de coloration immédiatement.
        """
        self.tree.delete(*self.tree.get_children())
        self.item_ids = {}

        for row in rows:
            if len(row) < 11:
                continue

            (codearticle, designation, unite, designationmag,
             alert_mag, stock_mag, alert_gen, stock_gen,
             idarticle, idunite, idmag) = row

            # Sécuriser les conversions numériques
            try:
                v_stock_mag  = float(stock_mag  or 0)
                v_stock_gen  = float(stock_gen  or 0)
                v_alert_mag  = float(alert_mag  or 0)
                v_alert_gen  = float(alert_gen  or 0)
            except (TypeError, ValueError):
                v_stock_mag = v_stock_gen = v_alert_mag = v_alert_gen = 0.0

            # Coloration
            if v_stock_mag == 0 or v_stock_gen == 0:
                tag = 'rupture'
            elif v_stock_mag <= v_alert_mag:
                tag = 'alerte'
            elif v_stock_gen <= v_alert_gen:
                tag = 'warning'
            else:
                tag = ''

            displayed = (
                codearticle,
                designation,
                unite,
                designationmag,
                alert_mag,
                round(v_stock_mag, 2),
                alert_gen,
                round(v_stock_gen, 2),
            )

            item_id = self.tree.insert('', 'end', values=displayed,
                                       tags=(tag,) if tag else ())
            self.item_ids[item_id] = (idarticle, idunite, idmag)

        self.label_total.configure(text=f"Total lignes: {len(rows)}")

    # ------------------------------------------------------------------
    # filtres  (inchangés sauf suppression de l'appel StockManager)
    # ------------------------------------------------------------------
    def _apply_filters(self):
        """Applique simultanément le filtre de recherche et le filtre d'alerte."""
        search_text = self.var_recherche.get().lower().strip()
        filter_type = self.var_filter.get()
        # enlever les emojis/icônes pour la logique de filtrage
        for emoji in ("🟠", "🟡", "🔴", "⚫"):  # ceux ajoutés dans la liste
            filter_type = filter_type.replace(emoji, "")
        filter_type = filter_type.strip()
        filter_mag = self.var_magasin.get()

        def row_matches(row):
            if len(row) < 11:
                return False

            # Recherche textuelle sur code + désignation + unité + magasin
            if search_text:
                haystack = " ".join(str(x).lower() for x in row[0:4])
                if search_text not in haystack:
                    return False

            # Filtre par magasin sélectionné
            if filter_mag and filter_mag != "Tous":
                mag_name = str(row[3])
                if mag_name != filter_mag:
                    return False

            # Filtre par état stock/alerte — valeurs déjà dans la ligne
            if filter_type != "Tous":
                try:
                    v_stock_mag = float(row[5] or 0)
                    v_stock_gen = float(row[7] or 0)
                    v_alert_mag = float(row[4] or 0)
                    v_alert_gen = float(row[6] or 0)
                except (TypeError, ValueError):
                    return False

                if filter_type == "Alerte Magasin":
                    return 0 < v_stock_mag <= v_alert_mag
                if filter_type == "Alerte Générale":
                    return 0 < v_stock_gen <= v_alert_gen
                if filter_type == "Rupture Magasin":
                    return v_stock_mag == 0
                if filter_type == "Rupture Générale":
                    return v_stock_gen == 0

            return True

        filtered = [row for row in self.all_rows if row_matches(row)]
        self.populate_table(filtered)

    def _on_search_text_changed(self, *args):
        self._apply_filters()

    def _refresh_magasin_filter(self):
        """Recalcule la liste des magasins disponibles pour le filtre.
        Doit être appelé après chaque chargement de self.all_rows.
        """
        # extraire et trier les libellés de magasin présents
        mags = sorted({str(row[3]) for row in self.all_rows if len(row) > 3})
        values = ["Tous"] + mags
        if hasattr(self, 'combo_mag'):
            self.combo_mag['values'] = values
        if hasattr(self, 'opt_mag'):
            try:
                self.opt_mag.configure(values=values)
            except Exception:
                pass
        # réinitialiser la sélection
        self.var_magasin.set("Tous")

    # ------------------------------------------------------------------
    # interface graphique  (inchangée)
    # ------------------------------------------------------------------
    def setup_ui(self):
        titre = ctk.CTkLabel(
            self, text="⚠️ Stock Alerte",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold")
        )
        titre.pack(pady=10)

        frame_filtres = ctk.CTkFrame(self)
        frame_filtres.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(frame_filtres, text="🔍 Recherche:",
                     font=ctk.CTkFont(family="Segoe UI", size=12)).pack(side="left", padx=5)
        self.var_recherche = StringVar()
        self.var_recherche.trace("w", self._on_search_text_changed)
        self.entry_recherche = ctk.CTkEntry(
            frame_filtres, textvariable=self.var_recherche,
            placeholder_text="Code ou désignation...", width=300
        )
        self.entry_recherche.pack(side="left", padx=5)

        # filtre par alerte/rupture
        from tkinter import StringVar as TkStringVar
        self.var_filter = TkStringVar(value="Tous")
        # label explicatif
        ctk.CTkLabel(frame_filtres, text="État :",
                     font=ctk.CTkFont(family="Segoe UI", size=11)).pack(side="left", padx=(15,2))
        try:
            self.combo_filter = ttk.Combobox(
                frame_filtres,
                values=[
                    "Tous",
                    "🟠 Alerte Magasin",
                    "🟡 Alerte Générale",
                    "🔴 Rupture Magasin",
                    "⚫ Rupture Générale",
                ],
                textvariable=self.var_filter, state="readonly", width=22
            )
            self.combo_filter.pack(side="left", padx=2)
            self.combo_filter.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())
        except Exception:
            self.opt_filter = ctk.CTkOptionMenu(
                frame_filtres,
                values=[
                    "Tous",
                    "🟠 Alerte Magasin",
                    "🟡 Alerte Générale",
                    "🔴 Rupture Magasin",
                    "⚫ Rupture Générale",
                ],
                command=lambda v: self._apply_filters()
            )
            self.opt_filter.set("Tous")
            self.opt_filter.pack(side="left", padx=2)

        # filtre par magasin (sera rempli après chargement)
        self.var_magasin = TkStringVar(value="Tous")
        ctk.CTkLabel(frame_filtres, text="Magasin :",
                     font=ctk.CTkFont(family="Segoe UI", size=11)).pack(side="left", padx=(15,2))
        try:
            self.combo_mag = ttk.Combobox(
                frame_filtres,
                values=["Tous"],
                textvariable=self.var_magasin, state="readonly", width=22
            )
            self.combo_mag.pack(side="left", padx=2)
            self.combo_mag.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())
        except Exception:
            self.opt_mag = ctk.CTkOptionMenu(
                frame_filtres,
                values=["Tous"],
                command=lambda v: self._apply_filters()
            )
            self.opt_mag.set("Tous")
            self.opt_mag.pack(side="left", padx=2)


        frame_tableau = ctk.CTkFrame(self)
        frame_tableau.pack(fill="both", expand=True, padx=20, pady=10)

        colonnes = ("CodeArticle", "Désignation", "Unité (Sup)", "Magasin",
                    "Alerte Mag.", "Stock Mag.", "Alerte Gen.", "Stock Gen.")
        self.tree = ttk.Treeview(frame_tableau, columns=colonnes, show="headings", height=20)
        self.tree.tag_configure('rupture', foreground='#b71c1c')
        self.tree.tag_configure('alerte',  foreground='#e65100')
        self.tree.tag_configure('warning', foreground='#e6b800')

        largeur = {
            "CodeArticle": 120, "Désignation": 300, "Unité (Sup)": 150,
            "Magasin": 160, "Alerte Mag.": 100, "Stock Mag.": 100,
            "Alerte Gen.": 100, "Stock Gen.": 100
        }
        for col in colonnes:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=largeur.get(col, 120), anchor='center')

        scroll_y = ctk.CTkScrollbar(frame_tableau, orientation="vertical",
                                    command=self.tree.yview)
        scroll_x = ctk.CTkScrollbar(frame_tableau, orientation="horizontal",
                                    command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        frame_tableau.grid_rowconfigure(0, weight=1)
        frame_tableau.grid_columnconfigure(0, weight=1)

        frame_info = ctk.CTkFrame(self)
        frame_info.pack(fill="x", padx=20, pady=10)
        self.label_total = ctk.CTkLabel(
            frame_info, text="Total lignes: 0",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        self.label_total.pack(side="left", padx=20)
        legend_text = "Texte rouge: rupture de stock (stock = 0)\nTexte orange: en alerte (alerte >= stock)"
        self.label_legend = ctk.CTkLabel(
            frame_info, text=legend_text,
            font=ctk.CTkFont(family="Segoe UI", size=10)
        )
        self.label_legend.pack(side="left", padx=10)
        self.label_statut = ctk.CTkLabel(
            frame_info, text="",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.label_statut.pack(side="right", padx=20)

    # ------------------------------------------------------------------
    # double-click & article editor  (inchangés)
    # ------------------------------------------------------------------
    def on_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        if item not in self.item_ids:
            messagebox.showerror("Erreur", "Article introuvable.")
            return
        self.open_article_editor(item)

    def open_article_editor(self, item_id):
        if item_id not in self.item_ids:
            messagebox.showerror("Erreur", "Article introuvable pour édition.")
            return

        idarticle, idunite, idmag = self.item_ids[item_id]
        values = self.tree.item(item_id, "values")

        codearticle        = values[0]
        designation        = values[1]
        designationunite   = values[2]
        designationmag     = values[3]
        alertdepot_current = values[4]
        alert_current      = values[6]

        # ── Fenêtre principale ────────────────────────────────────────────────
        try:
            win = ctk.CTkToplevel(self)
        except Exception:
            from tkinter import Toplevel
            win = Toplevel(self)

        WIN_W, WIN_H = 520, 480
        win.title("Modifier les alertes")
        win.resizable(False, False)
        win.grab_set()

        # Centrage
        win.update_idletasks()
        x = (win.winfo_screenwidth()  // 2) - (WIN_W // 2)
        y = (win.winfo_screenheight() // 2) - (WIN_H // 2)
        win.geometry(f"{WIN_W}x{WIN_H}+{x}+{y}")

        # ── Contenu principal ─────────────────────────────────────────────────
        root_frm = ctk.CTkFrame(win, fg_color="transparent")
        root_frm.pack(fill="both", expand=True, padx=20, pady=16)

        # ── En-tête : icône + titre article ──────────────────────────────────
        header = ctk.CTkFrame(root_frm, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            header, text="📦",
            font=ctk.CTkFont(size=28)
        ).pack(side="left", padx=(0, 10))

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            title_box, text=str(designation),
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w"
        ).pack(fill="x")

        ctk.CTkLabel(
            title_box,
            text=f"Code : {codearticle}   •   Unité : {designationunite}",
            font=ctk.CTkFont(size=11),
            text_color="gray60",
            anchor="w"
        ).pack(fill="x")

        # ── Séparateur ───────────────────────────────────────────────────────
        ctk.CTkFrame(root_frm, height=1, fg_color="gray30").pack(fill="x", pady=(0, 14))

        # ── Magasin ──────────────────────────────────────────────────────────
        ctk.CTkLabel(
            root_frm, text="Magasin de rattachement",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        ).pack(fill="x", pady=(0, 4))

        magasins_list    = self._get_magasins()
        magasins_display = [m[1] for m in magasins_list]

        var_magasin = StringVar(value=designationmag)
        combo_mag = ttk.Combobox(
            root_frm,
            textvariable=var_magasin,
            values=magasins_display,
            state="readonly",
            font=("Segoe UI", 11),
            width=46,
        )
        combo_mag.pack(fill="x", ipady=4, pady=(0, 14))

        # ── Séparateur ───────────────────────────────────────────────────────
        ctk.CTkFrame(root_frm, height=1, fg_color="gray30").pack(fill="x", pady=(0, 14))

        # ── Alertes (2 colonnes côte à côte) ─────────────────────────────────
        alerts_row = ctk.CTkFrame(root_frm, fg_color="transparent")
        alerts_row.pack(fill="x", pady=(0, 16))
        alerts_row.columnconfigure(0, weight=1)
        alerts_row.columnconfigure(1, weight=1)

        # -- Alerte Magasin
        frm_left = ctk.CTkFrame(alerts_row, corner_radius=8)
        frm_left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ctk.CTkLabel(
            frm_left, text="🏪  Alerte Magasin",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        ).pack(anchor="w", padx=12, pady=(10, 2))

        ctk.CTkLabel(
            frm_left,
            text=f"(en {designationunite})",
            font=ctk.CTkFont(size=10),
            text_color="gray60",
            anchor="w"
        ).pack(anchor="w", padx=12, pady=(0, 4))

        var_alert_depot = StringVar(value=str(alertdepot_current))
        ctk.CTkEntry(
            frm_left,
            textvariable=var_alert_depot,
            font=ctk.CTkFont(size=13),
            justify="center",
            height=36,
        ).pack(fill="x", padx=12, pady=(0, 12))

        # -- Alerte Générale
        frm_right = ctk.CTkFrame(alerts_row, corner_radius=8)
        frm_right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        ctk.CTkLabel(
            frm_right, text="🌐  Alerte Générale",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        ).pack(anchor="w", padx=12, pady=(10, 2))

        ctk.CTkLabel(
            frm_right,
            text=f"(en {designationunite})",
            font=ctk.CTkFont(size=10),
            text_color="gray60",
            anchor="w"
        ).pack(anchor="w", padx=12, pady=(0, 4))

        var_alert_general = StringVar(value=str(alert_current))
        ctk.CTkEntry(
            frm_right,
            textvariable=var_alert_general,
            font=ctk.CTkFont(size=13),
            justify="center",
            height=36,
        ).pack(fill="x", padx=12, pady=(0, 12))

        # ── Boutons ───────────────────────────────────────────────────────────
        btn_frm = ctk.CTkFrame(root_frm, fg_color="transparent")
        btn_frm.pack(fill="x", side="bottom", pady=(4, 0))

        def do_save():
            try:
                new_alert_depot   = float(var_alert_depot.get())
                new_alert_general = float(var_alert_general.get())
            except ValueError:
                messagebox.showerror("Erreur", "Les valeurs d'alerte doivent être des nombres.")
                return

            selected_mag_id = idmag
            for mag_id, mag_name in magasins_list:
                if mag_name == var_magasin.get():
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
                messagebox.showinfo("Succès", "Alertes mises à jour avec succès.")
                win.destroy()
                self.charger_donnees()
            except Exception as e:
                messagebox.showerror("Erreur SQL", str(e))
            finally:
                conn.close()

        ctk.CTkButton(
            btn_frm, text="Fermer",
            command=win.destroy,
            fg_color="transparent",
            border_width=1,
            border_color="gray50",
            text_color=("gray10", "gray90"),
            width=110, height=36,
        ).pack(side="left")

        ctk.CTkButton(
            btn_frm, text="💾  Enregistrer",
            command=do_save,
            fg_color="#2e7d32",
            hover_color="#1b5e20",
            width=160, height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="right")

    def _get_magasins(self):
        conn = self.connect_db()
        if not conn:
            return []
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT idmag, designationmag FROM public.tb_magasin "
                "WHERE deleted = 0 ORDER BY designationmag"
            )
            return cur.fetchall()
        except Exception:
            return []
        finally:
            conn.close()
