import customtkinter as ctk
import psycopg2
from tkinter import messagebox, ttk
import json
import pandas as pd
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from resource_utils import get_config_path, safe_file_read


# IMPORTER LA CLASSE DE PAIEMENT
try:
    from pages.page_pmtFrs import PagePmtFrs
except ImportError:
    class PagePmtFrs:
        def __init__(self, master, paiement_data: Dict[str, Any]):
            messagebox.showerror("Erreur", "Le fichier 'page_pmtFrs.py' est manquant ou contient une erreur.")

class PageFrsDette(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid(row=0, column=0, sticky="nsew")
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.data_df = pd.DataFrame() 
        
        # --- 1. Interface de Recherche et Export ---
        self.search_frame = ctk.CTkFrame(self)
        self.search_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            self.search_frame, 
            placeholder_text="Rechercher par Nom du Fournisseur...",
            width=400
        )
        self.search_entry.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.search_entry.bind("<Return>", self.search_dettes)
        
        self.search_button = ctk.CTkButton(
            self.search_frame, 
            text="Rechercher", 
            command=lambda: self.search_dettes(None)
        )
        self.search_button.grid(row=0, column=1, padx=(0, 10), pady=10)

        self.export_button = ctk.CTkButton(
            self.search_frame, 
            text="Export vers Excel", 
            command=self.export_to_excel,
            fg_color="green",
            hover_color="#006400"
        )
        self.export_button.grid(row=0, column=2, padx=(0, 10), pady=10)


        # --- 2. Tableau d'Affichage (ttk.Treeview) ---
        self.tree_frame = ctk.CTkFrame(self)
        self.tree_frame.grid(row=1, column=0, padx=20, pady=5, sticky="nsew")
        self.tree_frame.grid_columnconfigure(0, weight=1)
        self.tree_frame.grid_rowconfigure(0, weight=1)
        
        style = ttk.Style()
        style.theme_use("default") 

        current_mode = ctk.get_appearance_mode().lower()
        
        if current_mode == "dark":
            bg_color = "#2A2D2E"
            fg_color = "white"
            header_bg = "#383838"
            selected_bg = "#4A4D4E"
            text_sold_color = "#808080" # Gris pour le mode sombre
        else:
            bg_color = "#EBEBEB"
            fg_color = "black"
            header_bg = "#CFCFCF"
            selected_bg = "#A9A9A9"
            text_sold_color = "#A0A0A0" # Gris pour le mode clair

        style.configure("Treeview", 
                        background="#FFFFFF",
                        foreground="#000000",
                        rowheight=22,
                        fieldbackground="#FFFFFF",
                        borderwidth=0,
                        font=('Segoe UI', 8))
                        
        style.configure("Treeview.Heading",
                        background="#E8E8E8",
                        foreground="#000000",
                        font=('Segoe UI', 8, 'bold'))
        
        style.map('Treeview', 
                  background=[('selected', selected_bg)],
                  foreground=[('selected', fg_color)])

        columns = ("Fournisseur", "N° Commande", "N° Facture", "N° BR", "Montant Commande", "Payé", "Solde")
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings") 
        self.tree.tag_configure("even", background="#FFFFFF", foreground="#000000")
        self.tree.tag_configure("odd", background="#E6EFF8", foreground="#000000")

        # --- Tags de couleur ---
        self.tree.tag_configure('impaye', foreground='black') 
        self.tree.tag_configure('solde', foreground=text_sold_color) # Gris si payé
        
        self.tree.bind("<Double-1>", self.on_double_click)
        
        self.tree.heading("Fournisseur", text="Nom du Fournisseur")
        self.tree.heading("N° Commande", text="N° Commande")
        self.tree.heading("N° Facture", text="N° Facture")
        self.tree.heading("N° BR", text="N° BR")
        self.tree.heading("Montant Commande", text="Montant Commande")
        self.tree.heading("Payé", text="Payé")
        self.tree.heading("Solde", text="Solde")

        self.tree.column("Fournisseur", width=200, anchor=ctk.W)
        self.tree.column("N° Commande", width=120, anchor=ctk.CENTER)
        self.tree.column("N° Facture", width=120, anchor=ctk.CENTER)
        self.tree.column("N° BR", width=100, anchor=ctk.CENTER)
        self.tree.column("Montant Commande", width=150, anchor=ctk.E)
        self.tree.column("Payé", width=150, anchor=ctk.E)
        self.tree.column("Solde", width=150, anchor=ctk.E)

        vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")

        # --- 3. Section des Totaux ---
        self.total_frame = ctk.CTkFrame(self)
        self.total_frame.grid(row=2, column=0, padx=20, pady=(5, 20), sticky="ew") 
        self.total_frame.grid_columnconfigure(0, weight=1)
        
        self.total_cmd_label = ctk.CTkLabel(self.total_frame, text="Total Commandes: 0,00", font=ctk.CTkFont(family="Segoe UI", weight="bold"))
        self.total_cmd_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.total_paye_label = ctk.CTkLabel(self.total_frame, text="Total Payé: 0,00", font=ctk.CTkFont(family="Segoe UI", weight="bold"))
        self.total_paye_label.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        self.total_solde_label = ctk.CTkLabel(self.total_frame, text="Total Solde: 0,00", font=ctk.CTkFont(family="Segoe UI", weight="bold"), text_color="orange")
        self.total_solde_label.grid(row=0, column=2, padx=10, pady=10, sticky="w")
        
        self.load_all_dettes()

    def format_currency(self, value):
        try:
            sign = "-" if value < 0 else ""
            absolute_value = abs(value)
            integer_part, decimal_part = f"{round(absolute_value, 2):.2f}".split('.')
            formatted_integer = ""
            for i, digit in enumerate(reversed(integer_part)):
                if i > 0 and i % 3 == 0:
                    formatted_integer = ' ' + formatted_integer
                formatted_integer = digit + formatted_integer
            return f"{sign}{formatted_integer},{decimal_part}"
        except Exception:
            return "0,00"

    def on_double_click(self, event):
        selected_item = self.tree.focus()
        if not selected_item:
            return
        try:
            idx = self.tree.index(selected_item)
            row_data = self.data_df.iloc[idx]

            # --- CORRECTION : Empêcher le paiement si solde <= 0 ---
            if row_data["Solde"] <= 0.01:
                messagebox.showinfo("Action impossible", "Cette commande est déjà totalement réglée.")
                return

            paiement_data = {
                "refcom": row_data["N° Commande"],          
                "factfrs": row_data["N° Facture"] if row_data["N° Facture"] else row_data["N° Commande"], 
                "fournisseur": row_data["Fournisseur"],     
                "montant_total": f"{row_data['Solde']:.2f}".replace('.', ','),
                "id_cmd": row_data["N° Commande"],           
                "idfrs": row_data["ID Fournisseur"]
            }
            root = self.winfo_toplevel()
            self.popup_paiement = PagePmtFrs(root, paiement_data)
            root.wait_window(self.popup_paiement)
            self.load_all_dettes()
        except Exception as e:
            print(f"Erreur : {e}")

    def connect_db(self):
        try:
            with open(get_config_path('config.json')) as f:
                config = json.load(f)
                db_config = config['database']
            conn = psycopg2.connect(**db_config)
            return conn
        except Exception as e:
            messagebox.showerror("Erreur DB", str(e))
            return None
            
    def fetch_dettes(self, frs_name=""):
        conn = self.connect_db()
        if not conn:
            return []

        sql_query = """
        SELECT 
            tf.nomfrs,
            tf.idfrs,  
            tc.refcom,
            tlf.factfrs,
            tlf.reflivfrs,
            tc.totcmd,
            COALESCE(SUM(tp.mtpaye), 0.00) AS mtpaye,
            (tc.totcmd - COALESCE(SUM(tp.mtpaye), 0.00)) AS solde
        FROM 
            tb_commande tc
        JOIN 
            tb_fournisseur tf ON tf.idfrs = tc.idfrs
        LEFT JOIN 
            tb_livraisonfrs tlf ON tlf.idcom = tc.idcom
        LEFT JOIN 
            tb_pmtcom tp ON tp.refcom = tc.refcom
        WHERE 
            tlf.reflivfrs IS NOT NULL AND tlf.reflivfrs != ''
        """
        
        params = {}
        if frs_name:
            sql_query += " AND tf.nomfrs ILIKE %(frs_name)s"
            params['frs_name'] = f'%{frs_name}%'

        # Tri par refcom de manière décroissante
        # Le tri utilise NULLS LAST pour mettre les refs vides à la fin
        sql_query += """
        GROUP BY 
            tf.nomfrs, tf.idfrs, tc.refcom, tlf.factfrs, tlf.reflivfrs, tc.totcmd
        ORDER BY tc.refcom DESC;
        """
        
        data = []
        try:
            cur = conn.cursor()
            cur.execute(sql_query, params)
            data = cur.fetchall()
            cur.close()
        except psycopg2.Error as e:
            messagebox.showerror("Erreur DB", f"Erreur lors de la récupération : {e}")
        finally:
            conn.close()
        return data

    def load_all_dettes(self):
        self.process_and_display_data(self.fetch_dettes())

    def search_dettes(self, event):
        frs_name = self.search_entry.get().strip()
        data = self.fetch_dettes(frs_name)
        self.process_and_display_data(data)

    def process_and_display_data(self, data):
        for item in self.tree.get_children():
            self.tree.delete(item)

        columns = ["Fournisseur", "ID Fournisseur", "N° Commande", "N° Facture", "N° BR", "Montant Commande", "Payé", "Solde"]
        self.data_df = pd.DataFrame(data, columns=columns)
        
        if not self.data_df.empty:
            self.data_df['Montant Commande'] = pd.to_numeric(self.data_df['Montant Commande'], errors='coerce').fillna(0)
            self.data_df['Payé'] = pd.to_numeric(self.data_df['Payé'], errors='coerce').fillna(0)
            self.data_df['Solde'] = pd.to_numeric(self.data_df['Solde'], errors='coerce').fillna(0)

            for idx, row in self.data_df.iterrows():
                display_values = [
                    row['Fournisseur'],
                    row['N° Commande'],
                    row['N° Facture'],
                    row['N° BR'],
                    self.format_currency(row['Montant Commande']),
                    self.format_currency(row['Payé']),
                    self.format_currency(row['Solde'])
                ]
                
                # Gestion des tags visuels
                zebra_tag = 'even' if idx % 2 == 0 else 'odd'
                if row['Solde'] > 0.01:
                    tags = (zebra_tag, 'impaye')
                else:
                    tags = (zebra_tag, 'solde') # Applique la couleur grise
                    
                self.tree.insert('', 'end', values=display_values, tags=tags)
            
        self.update_totals()

    def update_totals(self):
        if not self.data_df.empty:
            total_cmd = self.data_df['Montant Commande'].sum()
            total_paye = self.data_df['Payé'].sum()
            total_solde = self.data_df['Solde'].sum()
        else:
            total_cmd = total_paye = total_solde = 0.0

        self.total_cmd_label.configure(text=f"Total Commandes: {self.format_currency(total_cmd)}")
        self.total_paye_label.configure(text=f"Total Payé: {self.format_currency(total_paye)}")
        self.total_solde_label.configure(text=f"Total Solde: {self.format_currency(total_solde)}")
        self.total_solde_label.configure(text_color="orange" if total_solde > 0.01 else "gray")

    def export_to_excel(self):
        if self.data_df.empty:
            messagebox.showinfo("Exportation", "Aucune donnée à exporter.")
            return
        try:
            total_row = {
                "Fournisseur": "TOTAL", "ID Fournisseur": None, "N° Commande": "", "N° Facture": "",
                "N° BR": "", "Montant Commande": self.data_df['Montant Commande'].sum(),
                "Payé": self.data_df['Payé'].sum(), "Solde": self.data_df['Solde'].sum(),
            }
            export_df = pd.concat([self.data_df, pd.DataFrame([total_row])], ignore_index=True).drop(columns=['ID Fournisseur'])
            filename = f"Dettes_Fournisseurs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            export_df.to_excel(filename, index=False)
            messagebox.showinfo("Succès", f"Exporté dans: {filename}")
        except Exception as e:
            messagebox.showerror("Erreur Export", str(e))

if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("1200x600")
    page = PageFrsDette(app)
    app.mainloop()
