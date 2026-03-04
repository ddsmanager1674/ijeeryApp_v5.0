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


# Ensure the parent directory is in the Python path for absolute imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


class PageBanque(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.configure(fg_color="#f5f5f5")

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
        
        if not self.conn:
            messagebox.showerror("Erreur", "Connexion impossible.")
            return
        
        self.cursor = self.conn.cursor()
        
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
        tree.tag_configure("row_even", background="#FFFFFF")
        tree.tag_configure("row_odd", background="#F2D9EA")

    def _refresh_table_alternating_colors(self, tree):
        for idx, item in enumerate(tree.get_children()):
            tree.item(item, tags=("row_even" if idx % 2 == 0 else "row_odd",))

    def setup_ui(self):
        self.pack(expand=True, fill="both", padx=20, pady=20)

        # ---- UI TOP (Filtres) ----
        self.frame_top = ctk.CTkFrame(self, fg_color="#f5f5f5")
        self.frame_top.pack(pady=10, fill="x", padx=10)

        # Sélection de la Banque
        self.bank_combobox = ctk.CTkComboBox(self.frame_top, width=200, command=self.on_bank_selected, state="readonly")
        self.bank_combobox.pack(side="left", padx=10)
        
        self.label_solde = ctk.CTkLabel(self.frame_top, text="Solde : 0 Ar", text_color="#000", font=("Arial", 14, "bold"))
        self.label_solde.pack(side="left", padx=20)

        self.frame_filtre = ctk.CTkFrame(self.frame_top, fg_color="#f5f5f5")
        self.frame_filtre.pack(side="right", padx=10)

        self.entry_debut = DateEntry(self.frame_filtre, width=12, background='darkblue', date_pattern='dd/mm/yyyy')
        self.entry_debut.pack(side="left", padx=5)
        self.entry_fin = DateEntry(self.frame_filtre, width=12, background='darkblue', date_pattern='dd/mm/yyyy')
        self.entry_fin.pack(side="left", padx=5)

        # ComboBox Mode de Paiement
        self.combo_mode = ctk.CTkComboBox(self.frame_filtre, values=["Tous"], width=130)
        self.combo_mode.pack(side="left", padx=5)
        self.combo_mode.set("Tous")

        # ComboBox Documents (Comme en Caisse)
        self.combo_doc = ctk.CTkComboBox(
            self.frame_filtre, 
            values=["Tous", "Clients", "Avoir", "Fournisseurs", "Personnel", "Divers"], 
            width=130
        )
        self.combo_doc.pack(side="left", padx=5)
        self.combo_doc.set("Tous")

        ctk.CTkButton(self.frame_filtre, text="Valider", width=80, fg_color="#28a745", command=self.trigger_data_load).pack(side="left", padx=5)
        ctk.CTkButton(self.frame_filtre, text="Export Excel", width=100, fg_color="#17a2b8", command=self.exporter_excel).pack(side="left", padx=5)

        # ---- TREEVIEW (Colonnes alignées sur Caisse) ----
        self.colonnes = ("Date", "Référence", "Description", "Encaissement", "Décaissement", "Mode", "Utilisateur")
        self.frame_tree = ctk.CTkFrame(self)
        self.frame_tree.pack(fill="both", expand=True, padx=10, pady=5)

        self.tree = ttk.Treeview(self.frame_tree, columns=self.colonnes, show="headings")
        self._configure_table_alternating_colors(self.tree)
        for col in self.colonnes:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=110)
        self.tree.column("Description", width=250, anchor="w")

        self.scrollbar_y = ttk.Scrollbar(self.frame_tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar_y.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.scrollbar_y.grid(row=0, column=1, sticky="ns")
        self.frame_tree.grid_rowconfigure(0, weight=1)
        self.frame_tree.grid_columnconfigure(0, weight=1)

        # ---- BOTTOM (Totaux et Boutons) ----
        self.frame_bottom_container = ctk.CTkFrame(self, fg_color="#f5f5f5")
        self.frame_bottom_container.pack(pady=10, fill="x", padx=10, side="bottom")

        self.frame_totaux = ctk.CTkFrame(self.frame_bottom_container, fg_color="#f5f5f5")
        self.frame_totaux.pack(side="left", fill="y")

        self.label_total_encaissement = ctk.CTkLabel(self.frame_totaux, text="Total Encaissement: 0 Ar", font=("Arial", 13, "bold"))
        self.label_total_encaissement.grid(row=0, column=0, padx=20, sticky='w')
        self.label_total_decaissement = ctk.CTkLabel(self.frame_totaux, text="Total Décaissement: 0 Ar", font=("Arial", 13, "bold"))
        self.label_total_decaissement.grid(row=1, column=0, padx=20, sticky='w')

        self.frame_actions = ctk.CTkFrame(self.frame_bottom_container, fg_color="#f5f5f5")
        self.frame_actions.pack(side="right", fill="y", padx=20)

        self.btn_open_encaissement = ctk.CTkButton(self.frame_actions, text="+ Encaissement", fg_color="#28a745", width=150, command=self.open_page_encaissement)
        self.btn_open_encaissement.pack(side="left", padx=5)

        self.btn_open_decaissement = ctk.CTkButton(self.frame_actions, text="- Décaissement", fg_color="#dc3545", width=150, command=self.open_page_decaissement)
        self.btn_open_decaissement.pack(side="left", padx=5)

        # Charger les données initiales
        self.charger_modes_paiement()
        self.load_bank_names()

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
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def open_page_decaissement(self):
        if not self.selected_bank_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner une banque")
            return
        from pages.page_decaissementBq import PageDecaissementBq
        win = PageDecaissementBq(self.master, bank_id=self.selected_bank_id)
        win.grab_set()
        self.master.wait_window(win)
        self.trigger_data_load()

    def open_page_encaissement(self):
        if not self.selected_bank_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner une banque")
            return
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
