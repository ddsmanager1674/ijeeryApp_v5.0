import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import psycopg2
import json
import csv
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from resource_utils import get_config_path, safe_file_read


# IMPORTER LA CLASSE DE PAIEMENT
try:
    from pages.page_pmtCredit import PagePmtCredit
except ImportError:
    class PagePmtCredit:
        def __init__(self, master, paiement_data: Dict[str, Any]):
            messagebox.showerror("Erreur", "Le fichier 'page_pmtCredit.py' est manquant ou contient une erreur.")

class PageClientCrédit(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid(row=0, column=0, sticky="nsew")
        
        # 1. Configuration de la grille
        self.grid_rowconfigure(1, weight=1)      
        self.grid_columnconfigure(0, weight=1)   
        
        # 2. DÉFINITION DES VARIABLES
        self.total_montant_facture = ctk.StringVar(value="0,00 Ar")
        self.total_paye = ctk.StringVar(value="0,00 Ar")
        self.total_solde = ctk.StringVar(value="0,00 Ar")
        self.current_records = []
        self.dict_clients = {} 

        # 3. CRÉATION DE L'INTERFACE
        self.create_widgets()
        
        # 4. CHARGEMENT INITIAL
        self.load_clients() 
        self.load_data()

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

    def load_clients(self):
        """Charge les clients pour la Combobox d'ajout de créance"""
        conn = self.connect_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT idclient, nomcli FROM tb_client ORDER BY nomcli")
                rows = cursor.fetchall()
                self.dict_clients = {row[1]: row[0] for row in rows}
                self.client_combo.configure(values=list(self.dict_clients.keys()))
            except Exception as e:
                print(f"Erreur chargement clients: {e}")
            finally:
                conn.close()

    def save_autre_creance(self):
        """Ajoute une ligne dans tb_autrecreance"""
        client_nom = self.client_combo.get()
        num_fact = self.num_fact_entry.get().strip()
        montant_str = self.montant_entry.get().strip()

        if client_nom == "Sélectionner Client" or not num_fact or not montant_str:
            messagebox.showwarning("Champs vides", "Veuillez remplir tous les champs d'ajout.")
            return

        try:
            id_client = self.dict_clients[client_nom]
            montant = float(montant_str.replace(',', '.'))
            
            conn = self.connect_db()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO tb_autrecreance (idclient, dateregistre, numfact, montant)
                    VALUES (%s, %s, %s, %s)
                """, (id_client, datetime.now(), num_fact, montant))
                conn.commit()
                conn.close()
                
                messagebox.showinfo("Succès", "Créance manuelle ajoutée.")
                self.num_fact_entry.delete(0, 'end')
                self.montant_entry.delete(0, 'end')
                self.load_data()
        except Exception as e:
            messagebox.showerror("Erreur", f"Action impossible : {e}")

    def create_widgets(self):
        # Frame de contrôle supérieure
        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        
        # --- Ligne 1: Recherche ---
        self.search_entry = ctk.CTkEntry(control_frame, placeholder_text="Rechercher un client (Ventes ou Créances)...")
        self.search_entry.grid(row=0, column=0, columnspan=4, padx=10, pady=10, sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda e: self.load_data(self.search_entry.get()))

        # --- Ligne 2: Formulaire d'ajout rapide (Autres Créances) ---
        self.client_combo = ctk.CTkComboBox(control_frame, values=[], width=220)
        self.client_combo.set("Sélectionner Client")
        self.client_combo.grid(row=1, column=0, padx=10, pady=5)

        self.num_fact_entry = ctk.CTkEntry(control_frame, placeholder_text="N° Facture")
        self.num_fact_entry.grid(row=1, column=1, padx=10, pady=5)

        self.montant_entry = ctk.CTkEntry(control_frame, placeholder_text="Montant (Ar)")
        self.montant_entry.grid(row=1, column=2, padx=10, pady=5)

        btn_add = ctk.CTkButton(control_frame, text="Enregistrer Créance", fg_color="#27ae60", command=self.save_autre_creance)
        btn_add.grid(row=1, column=3, padx=10, pady=5)

        control_frame.grid_columnconfigure(0, weight=1)

        # Table (Treeview)
        tree_frame = ctk.CTkFrame(self)
        tree_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        columns = ("Nom du Client", "N° Facture / Ref", "Montant Initial", "Total Payé", "Solde Restant")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        self.tree.tag_configure("even", background="#FFFFFF", foreground="#000000")
        self.tree.tag_configure("odd", background="#E6EFF8", foreground="#000000")
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center")
        
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.on_double_click)

        # Barre de totaux
        bottom_frame = ctk.CTkFrame(self)
        bottom_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        ctk.CTkLabel(bottom_frame, text="Total Facturé:").grid(row=0, column=0, padx=5)
        ctk.CTkLabel(bottom_frame, textvariable=self.total_montant_facture, font=("Arial", 12, "bold")).grid(row=0, column=1, padx=20)
        
        ctk.CTkLabel(bottom_frame, text="Total Solde:").grid(row=0, column=2, padx=5)
        ctk.CTkLabel(bottom_frame, textvariable=self.total_solde, font=("Arial", 12, "bold"), text_color="#e74c3c").grid(row=0, column=3, padx=20)

    def load_data(self, filter_text=""):
        conn = self.connect_db()
        if not conn: return
    
        try:
            cursor = conn.cursor()
            # Requête corrigée: calcul des paiements pour CHAQUE source séparément
            query = """
                -- Ventes à crédit
                SELECT 
                    c.nomcli, 
                    v.refvente as ref, 
                    v.totmtvente as mt_initial, 
                    COALESCE(SUM(p.mtpaye), 0) as total_paye,
                    (v.totmtvente - COALESCE(SUM(p.mtpaye), 0)) as solde,
                    c.idclient
                FROM tb_vente v
                JOIN tb_client c ON v.idclient = c.idclient
                LEFT JOIN tb_pmtcredit p ON v.refvente = p.refvente
                WHERE v.idmode = 4
                GROUP BY c.nomcli, v.refvente, v.totmtvente, c.idclient
                HAVING (v.totmtvente - COALESCE(SUM(p.mtpaye), 0)) > 0

                UNION ALL

                -- Autres créances
                SELECT 
                    c.nomcli, 
                    a.numfact as ref, 
                    a.montant as mt_initial, 
                    COALESCE(SUM(p.mtpaye), 0) as total_paye,
                    (a.montant - COALESCE(SUM(p.mtpaye), 0)) as solde,
                    c.idclient
                FROM tb_autrecreance a
                JOIN tb_client c ON a.idclient = c.idclient
                LEFT JOIN tb_pmtcredit p ON a.numfact = p.refvente
                GROUP BY c.nomcli, a.numfact, a.montant, c.idclient
                HAVING (a.montant - COALESCE(SUM(p.mtpaye), 0)) > 0

                ORDER BY nomcli ASC
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            
            # Application du filtre de recherche
            if filter_text:
                self.current_records = [r for r in rows if filter_text.lower() in r[0].lower()]
            else:
                self.current_records = rows
            
            self.update_ui()
        except Exception as e:
            print(f"Erreur SQL: {e}")
            messagebox.showerror("Erreur", f"Erreur lors du chargement des données: {e}")
        finally:
            conn.close()

    def update_ui(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        t_fact = 0.0
        t_solde = 0.0
        
        for idx, row in enumerate(self.current_records):
            nom, ref, mt, paye, solde, id_cli = row
            tag = "even" if idx % 2 == 0 else "odd"
            self.tree.insert("", "end", values=(
                nom, ref, 
                f"{mt:,.2f} Ar", 
                f"{paye:,.2f} Ar", 
                f"{solde:,.2f} Ar"
            ), tags=(tag,))
            t_fact += float(mt)
            t_solde += float(solde)
            
        self.total_montant_facture.set(f"{t_fact:,.2f} Ar")
        self.total_solde.set(f"{t_solde:,.2f} Ar")

    def on_double_click(self, event):
        selected_item = self.tree.focus()
        if not selected_item: return
        idx = self.tree.index(selected_item)
        data = self.current_records[idx]

        paiement_data = {
            "refvente": data[1],
            "montant_total": data[4], 
            "client": data[0],
            "id_client_reel": data[5]
        }

        try:
            pmt_window = PagePmtCredit(self.master, paiement_data)
            if pmt_window.winfo_exists():
                self.master.wait_window(pmt_window)
            self.load_data(self.search_entry.get())
        except Exception as e:
            messagebox.showerror("Erreur", f"Ouverture paiement échouée : {e}")

    def export_to_excel(self):
        # Code d'exportation identique...
        pass

if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Système de Crédits")
    app.geometry("1000x600")
    PageClientCrédit(app)
    app.mainloop()
