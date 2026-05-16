import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry
from tkinter import messagebox
import psycopg2
from datetime import datetime
import pandas as pd
import os
import json
import sys
from resource_utils import get_config_path, safe_file_read
from app_theme import Colors, Fonts, styled, Layout
from log_utils import AppLogger


# Ensure the parent directory is in the Python path for absolute imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


class PageBanque(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.configure(fg_color=Colors.BG_PAGE)

        # Connexion à la base de données
        self.conn = self.connect_db()
        self.cursor = None
        
        if self.conn:
            self.cursor = self.conn.cursor()
            self.initialize_database()

        self.modes_paiement_dict = {"Tous": None}
        self.bank_id_map = {}
        self.donnees_export = []
        self.selected_bank_id = None
        self._responsive_mode = None  # "wide" | "narrow"
        
        if not self.conn:
            messagebox.showerror("Erreur", "Connexion impossible.")
            return
        
        self.cursor = self.conn.cursor()
        self.session_data = getattr(master, "session_data", None) or {}
        self._logger = AppLogger(conn=self.conn, session_data=self.session_data)
        
        # CORRECTION PRINCIPALE : Appeler setup_ui() dans __init__
        self.setup_ui()

    def connect_db(self):
        """Établit la connexion à la base de données à partir du fichier config.json"""
        try:
            config_path = get_config_path('config.json')
            if not os.path.exists(config_path):
                config_path = 'config.json'
                
            if not os.path.exists(config_path):
                messagebox.showerror("Erreur", "Fichier config.json manquant.")
                return None
                 
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                db_config = config['database']

            conn = psycopg2.connect(
                host=db_config['host'],
                user=db_config['user'],
                password=db_config['password'],
                database=db_config['database'],
                port=db_config['port'],
                client_encoding='UTF8'
            )
            print("Connection to the database successful!")
            return conn
        except Exception as err:
            messagebox.showerror("Erreur de connexion", f"Détails : {err}")
            return None
    
    def initialize_database(self):
        """Initialise la connexion à la base de données et crée la table si nécessaire."""
        if not self.cursor:
            return False

    def _configure_table_alternating_colors(self, tree):
        tree.tag_configure("row_even", background=Colors.BG_CARD)
        tree.tag_configure("row_odd", background=Colors.BG_ROW_ALT)

    def _refresh_table_alternating_colors(self, tree):
        for idx, item in enumerate(tree.get_children()):
            tree.item(item, tags=("row_even" if idx % 2 == 0 else "row_odd",))

    def _apply_ttk_theme(self):
        """Style ttk.Treeview pour s'intégrer au thème courant."""
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "Treeview",
            background=Colors.BG_CARD,
            foreground=Colors.TEXT_PRIMARY,
            fieldbackground=Colors.BG_CARD,
            rowheight=Layout.ROW_H,
            borderwidth=0,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Treeview.Heading",
            background=Colors.BG_HEADER,
            foreground=Colors.TEXT_ON_DARK,
            font=("Segoe UI", 9, "bold"),
            borderwidth=0,
        )
        style.map(
            "Treeview",
            background=[("selected", Colors.PRIMARY_LIGHT)],
            foreground=[("selected", Colors.TEXT_PRIMARY)],
        )

    def _make_date_entry(self, parent):
        from date_picker_utils import make_tk_date_entry
        return make_tk_date_entry(parent, width=12)

    def _update_responsive_layout(self, width: int):
        mode = "narrow" if width < 980 else "wide"
        if mode == self._responsive_mode:
            return
        self._responsive_mode = mode

        # Repositionner les blocs de filtres / actions selon la largeur.
        if mode == "wide":
            self.top_left.grid(row=0, column=0, sticky="w", padx=(0, 12), pady=0)
            self.top_right.grid(row=0, column=1, sticky="e", padx=(12, 0), pady=0)
            self.top_container.grid_columnconfigure(0, weight=1)
            self.top_container.grid_columnconfigure(1, weight=1)
        else:
            self.top_left.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 10))
            self.top_right.grid(row=1, column=0, sticky="ew", padx=0, pady=0)
            self.top_container.grid_columnconfigure(0, weight=1)
            self.top_container.grid_columnconfigure(1, weight=0)

    def setup_ui(self):
        self.pack(expand=True, fill="both", padx=Layout.CARD_PADX, pady=Layout.CARD_PADY_TOP)
        self._apply_ttk_theme()

        # Conteneur principal
        self.container = styled.frame(self, color="transparent")
        self.container.pack(fill="both", expand=True)
        self.container.grid_columnconfigure(0, weight=1)

        # ---- TOP : Banque + Solde + Filtres ----
        self.top_card = styled.card(self.container)
        self.top_card.pack(fill="x", pady=(0, Layout.SECTION_GAP))

        self.top_container = styled.frame(self.top_card, color="transparent")
        self.top_container.pack(fill="x", padx=Layout.CARD_PADX, pady=Layout.CARD_PADY_TOP)
        self.top_container.grid_rowconfigure(0, weight=1)
        self.top_container.grid_columnconfigure(0, weight=1)
        self.top_container.grid_columnconfigure(1, weight=1)

        # Gauche : sélection banque + solde
        self.top_left = styled.frame(self.top_container, color="transparent")
        self.top_left.grid(row=0, column=0, sticky="w", padx=(0, 12))

        styled.label_muted(self.top_left, text="Banque", anchor="w").pack(anchor="w", pady=(0, 4))
        self.bank_combobox = styled.combobox(
            self.top_left,
            values=[],
            command=self.on_bank_selected,
            width=280,
            state="readonly",
        )
        self.bank_combobox.pack(anchor="w")

        self.label_solde = styled.badge(self.top_left, text="Solde : 0 Ar", variant="info")
        self.label_solde.pack(anchor="w", pady=(10, 0))

        # Droite : filtres
        self.top_right = styled.frame(self.top_container, color="transparent")
        self.top_right.grid(row=0, column=1, sticky="e", padx=(12, 0))

        self.filters_grid = styled.frame(self.top_right, color="transparent")
        self.filters_grid.pack(anchor="e")
        for c in range(8):
            self.filters_grid.grid_columnconfigure(c, weight=0)
        self.filters_grid.grid_columnconfigure(0, weight=0)

        styled.label_muted(self.filters_grid, text="Du", anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.entry_debut = self._make_date_entry(self.filters_grid)
        self.entry_debut.grid(row=0, column=1, sticky="w", padx=(0, 10))

        styled.label_muted(self.filters_grid, text="Au", anchor="w").grid(row=0, column=2, sticky="w", padx=(0, 6))
        self.entry_fin = self._make_date_entry(self.filters_grid)
        self.entry_fin.grid(row=0, column=3, sticky="w", padx=(0, 14))

        styled.label_muted(self.filters_grid, text="Mode", anchor="w").grid(row=0, column=4, sticky="w", padx=(0, 6))
        self.combo_mode = styled.combobox(self.filters_grid, values=["Tous"], width=160)
        self.combo_mode.grid(row=0, column=5, sticky="w", padx=(0, 14))
        self.combo_mode.set("Tous")

        styled.label_muted(self.filters_grid, text="Document", anchor="w").grid(row=0, column=6, sticky="w", padx=(0, 6))
        self.combo_doc = styled.combobox(
            self.filters_grid,
            values=["Tous", "Clients", "Avoir", "Fournisseurs", "Personnel", "Divers"],
            width=170,
        )
        self.combo_doc.grid(row=0, column=7, sticky="w", padx=(0, 0))
        self.combo_doc.set("Tous")

        self.filters_actions = styled.frame(self.top_right, color="transparent")
        self.filters_actions.pack(anchor="e", pady=(12, 0))
        styled.button_success(self.filters_actions, text="Valider", width=140, command=self.trigger_data_load).pack(side="left", padx=(0, 8))
        styled.button_premium(self.filters_actions, text="Export Excel", width=160, command=self.exporter_excel).pack(side="left")

        # ---- TABLE ----
        self.table_card = styled.card(self.container)
        self.table_card.pack(fill="both", expand=True, pady=(0, Layout.SECTION_GAP))

        self.frame_tree = styled.frame(self.table_card, color="transparent")
        self.frame_tree.pack(fill="both", expand=True, padx=Layout.CARD_PADX, pady=Layout.CARD_PADY_TOP)

        self.colonnes = ("Date", "Référence", "Description", "Encaissement", "Décaissement", "Mode", "Utilisateur")
        self.tree = ttk.Treeview(self.frame_tree, columns=self.colonnes, show="headings")
        self._configure_table_alternating_colors(self.tree)

        for col in self.colonnes:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=120)
        self.tree.column("Description", width=320, anchor="w")

        self.scrollbar_y = ttk.Scrollbar(self.frame_tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar_y.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.scrollbar_y.grid(row=0, column=1, sticky="ns")
        self.frame_tree.grid_rowconfigure(0, weight=1)
        self.frame_tree.grid_columnconfigure(0, weight=1)

        # ---- BOTTOM : totaux + actions ----
        self.bottom_card = styled.card(self.container)
        self.bottom_card.pack(fill="x")

        self.frame_bottom = styled.frame(self.bottom_card, color="transparent")
        self.frame_bottom.pack(fill="x", padx=Layout.CARD_PADX, pady=Layout.CARD_PADY_BOT)
        self.frame_bottom.grid_columnconfigure(0, weight=1)
        self.frame_bottom.grid_columnconfigure(1, weight=0)

        self.totals = styled.frame(self.frame_bottom, color="transparent")
        self.totals.grid(row=0, column=0, sticky="w")
        self.label_total_encaissement = styled.label(self.totals, text="Total Encaissement: 0 Ar", size=13, weight="bold")
        self.label_total_encaissement.grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.label_total_decaissement = styled.label(self.totals, text="Total Décaissement: 0 Ar", size=13, weight="bold")
        self.label_total_decaissement.grid(row=1, column=0, sticky="w")

        self.actions = styled.frame(self.frame_bottom, color="transparent")
        self.actions.grid(row=0, column=1, sticky="e")
        self.btn_open_encaissement = styled.button_success(
            self.actions, text="+ Encaissement", width=180, command=self.open_page_encaissement
        )
        self.btn_open_encaissement.pack(side="left", padx=(0, 8))
        self.btn_open_decaissement = styled.button_danger(
            self.actions, text="- Décaissement", width=180, command=self.open_page_decaissement
        )
        self.btn_open_decaissement.pack(side="left")

        # Charger les données initiales
        self.charger_modes_paiement()
        self.load_bank_names()
        self.bind("<Configure>", lambda e: self._update_responsive_layout(e.width))
        self._update_responsive_layout(self.winfo_width() or 1200)

    def format_montant(self, v):
        return f"{v:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")

    def charger_modes_paiement(self):
        try:
            self.cursor.execute("SELECT idmode, modedepaiement FROM tb_modepaiement ORDER BY modedepaiement")
            rows = self.cursor.fetchall()
            noms = ["Tous"]
            for r in rows:
                self.modes_paiement_dict[r[1]] = r[0]
                noms.append(r[1])
            self.combo_mode.configure(values=noms)
        except Exception as e:
            print(f"Erreur chargement modes: {e}")

    def load_bank_names(self):
        try:
            self.cursor.execute("SELECT id_banque, nombanque FROM tb_banque ORDER BY nombanque")
            banks = self.cursor.fetchall()
            if banks:
                self.bank_id_map = {name: id_b for id_b, name in banks}
                names = [b[1] for b in banks]
                self.bank_combobox.configure(values=names)
                self.bank_combobox.set(names[0])
                self.on_bank_selected(names[0])
            else:
                self.bank_combobox.configure(values=["Aucune banque"])
                self.bank_combobox.set("Aucune banque")
        except Exception as e:
            print(f"Erreur chargement banques: {e}")

    def on_bank_selected(self, selection):
        self.selected_bank_id = self.bank_id_map.get(selection)
        self.trigger_data_load()

    def trigger_data_load(self):
        if hasattr(self, 'selected_bank_id') and self.selected_bank_id:
            mode_id = self.modes_paiement_dict.get(self.combo_mode.get())
            type_doc = self.combo_doc.get()
            self.charger_donnees(self.entry_debut.get_date(), self.entry_fin.get_date(), self.selected_bank_id, mode_id, type_doc)

    def charger_donnees(self, date_d, date_f, bank_id, mode_id=None, type_doc="Tous"):
        d_str, f_str = date_d.strftime('%Y-%m-%d'), date_f.strftime('%Y-%m-%d')
        for item in self.tree.get_children(): self.tree.delete(item)
        self._refresh_table_alternating_colors(self.tree)
        
        all_ops = []
        sql_mode = " AND t1.idmode = %s" if mode_id else ""
        
        # Filtre par type de document (Référence)
        sql_ref = ""
        if type_doc == "Clients": sql_ref = " AND t1.refpmt ILIKE '%%PMTC%%'"
        elif type_doc == "Avoir": sql_ref = " AND t1.refpmt ILIKE '%%AV%%'"
        elif type_doc == "Fournisseurs": sql_ref = " AND t1.refpmt ILIKE '%%PMTF%%'"
        elif type_doc == "Personnel": sql_ref = " AND (t1.refpmt ILIKE '%%AVQ%%' OR t1.refpmt ILIKE '%%AVS%%' OR t1.refpmt ILIKE '%%SAL%%')"
        elif type_doc == "Divers": sql_ref = " AND (t1.refpmt ILIKE '%%ENC%%' OR t1.refpmt ILIKE '%%DEC%%')"

        tables = ["tb_encaissementbq", "tb_decaissementbq", "tb_pmtfacture", "tb_pmtcom", "tb_transfertbanque"]
        
        try:
            for table in tables:
                query = f"""
                    SELECT t1.datepmt::date, t1.refpmt, t1.observation, t1.mtpaye, t1.idtypeoperation, 
                           COALESCE(t2.modedepaiement, 'Banque'), COALESCE(t3.username, 'Système')
                    FROM {table} t1
                    LEFT JOIN tb_modepaiement t2 ON t1.idmode = t2.idmode
                    LEFT JOIN tb_users t3 ON t1.iduser = t3.iduser
                    WHERE t1.datepmt::date BETWEEN %s AND %s AND t1.id_banque = %s {sql_mode} {sql_ref}
                """
                params = [d_str, f_str, bank_id] + ([mode_id] if mode_id else [])
                self.cursor.execute(query, params)
                all_ops.extend(self.cursor.fetchall())

            all_ops.sort(key=lambda x: x[0], reverse=True)
            t_enc, t_dec = 0, 0
            self.donnees_export = []

            for r in all_ops:
                dt, ref, obs, mt, typ, mod, usr = r
                enc = float(mt) if typ == 1 else 0
                dec = float(mt) if typ == 2 else 0
                t_enc += enc
                t_dec += dec
                
                vals = (dt.strftime("%d/%m/%Y"), str(ref), str(obs), 
                        self.format_montant(enc) if enc else "", 
                        self.format_montant(dec) if dec else "", mod, usr)
                self.tree.insert("", "end", values=vals)
                self.donnees_export.append(vals)
            self._refresh_table_alternating_colors(self.tree)

            self.label_total_encaissement.configure(text=f"Total Encaissement: {self.format_montant(t_enc)} Ar")
            self.label_total_decaissement.configure(text=f"Total Décaissement: {self.format_montant(t_dec)} Ar")
            self.update_solde_global(bank_id)
        except Exception as e:
            print(f"Erreur SQL: {e}")

    def update_solde_global(self, bank_id):
        try:
            self.cursor.execute("""
                SELECT SUM(CASE WHEN idtypeoperation = 1 THEN mtpaye ELSE -mtpaye END) 
                FROM (
                    SELECT idtypeoperation, mtpaye FROM tb_encaissementbq WHERE id_banque = %s
                    UNION ALL SELECT idtypeoperation, mtpaye FROM tb_decaissementbq WHERE id_banque = %s
                    UNION ALL SELECT idtypeoperation, mtpaye FROM tb_pmtfacture WHERE id_banque = %s
                    UNION ALL SELECT idtypeoperation, mtpaye FROM tb_pmtcom WHERE id_banque = %s
                    UNION ALL SELECT idtypeoperation, mtpaye FROM tb_transfertbanque WHERE id_banque = %s
                ) as total
            """, (bank_id, bank_id, bank_id, bank_id, bank_id))
            res = self.cursor.fetchone()
            solde = res[0] if res and res[0] else 0
            # label_solde est un badge CTkLabel
            self.label_solde.configure(text=f"Solde : {self.format_montant(solde)} Ar")
        except Exception as e:
            print(f"Erreur calcul solde: {e}")

    def exporter_excel(self):
        if not self.donnees_export:
            messagebox.showwarning("Attention", "Aucune donnée à exporter")
            return
        try:
            df = pd.DataFrame(self.donnees_export, columns=self.colonnes)
            nom = f"Banque_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df.to_excel(nom, index=False)
            messagebox.showinfo("Succès", f"Exporté vers {nom}")
            try:
                from log_utils import AppLogger
                AppLogger(session_data=getattr(self, "session_data", {}) or {}).log(
                    action="Export Excel",
                    element="Banque",
                    details=f"export banque, lignes={len(self.donnees_export)}, fichier={os.path.basename(nom)}",
                    value=nom,
                )
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def open_page_decaissement(self):
        if not self.selected_bank_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner une banque")
            return
        try:
            self._logger.log(
                action="Ouverture décaissement bancaire",
                element=f"id_banque={self.selected_bank_id}",
                details="Ouverture page Décaissement Bq",
                value=f"id_banque={self.selected_bank_id}",
            )
        except Exception:
            pass
        from pages.page_decaissementBq import PageDecaissementBq
        win = PageDecaissementBq(self.master, bank_id=self.selected_bank_id)
        win.grab_set()
        self.master.wait_window(win)
        self.trigger_data_load()

    def open_page_encaissement(self):
        if not self.selected_bank_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner une banque")
            return
        try:
            self._logger.log(
                action="Ouverture encaissement bancaire",
                element=f"id_banque={self.selected_bank_id}",
                details="Ouverture page Encaissement Bq",
                value=f"id_banque={self.selected_bank_id}",
            )
        except Exception:
            pass
        from pages.page_encaissementBq import PageEncaissementBq
        win = PageEncaissementBq(self.master, bank_id=self.selected_bank_id)
        win.grab_set()
        self.master.wait_window(win)
        self.trigger_data_load()

    def close_connection(self):
        if self.conn:
            self.conn.close()
        self.master.destroy()


if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Gestion Banque")
    app.geometry("1150x700")
    page = PageBanque(app)
    page.pack(fill="both", expand=True)
    app.mainloop()
