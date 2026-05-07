import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import psycopg2
import json
import csv
import os
from datetime import datetime, date
from typing import List
from resource_utils import get_config_path


class PageRetardCredit(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid(row=0, column=0, sticky="nsew")

        # 1. Configuration de la grille
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # 2. DÉFINITION DES VARIABLES
        self.total_montant = ctk.StringVar(value="0,00 Ar")
        self.total_retard_count = ctk.StringVar(value="0 client(s)")
        self.current_records: List = []

        # 3. CRÉATION DE L'INTERFACE
        self.create_widgets()

        # 4. CHARGEMENT INITIAL
        self.load_data()

    # ─────────────────────────────────────────────
    #  CONNEXION BASE DE DONNÉES
    # ─────────────────────────────────────────────
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

    # ─────────────────────────────────────────────
    #  CRÉATION DE L'INTERFACE
    # ─────────────────────────────────────────────
    def create_widgets(self):
        # ── Frame de contrôle supérieure ──
        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        control_frame.grid_columnconfigure(0, weight=1)

        # Titre
        ctk.CTkLabel(
            control_frame,
            text="⚠  Clients en Retard de Paiement Crédit",
            font=("Arial", 15, "bold"),
            text_color="#e74c3c"
        ).grid(row=0, column=0, columnspan=3, padx=10, pady=(10, 4), sticky="w")

        # Champ de recherche
        self.search_entry = ctk.CTkEntry(
            control_frame,
            placeholder_text="Rechercher un client...",
            width=350
        )
        self.search_entry.grid(row=1, column=0, padx=10, pady=(4, 10), sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda e: self.load_data(self.search_entry.get()))

        # Bouton Actualiser
        btn_refresh = ctk.CTkButton(
            control_frame,
            text="🔄 Actualiser",
            width=130,
            fg_color="#2980b9",
            command=lambda: self.load_data(self.search_entry.get())
        )
        btn_refresh.grid(row=1, column=1, padx=10, pady=(4, 10))

        # Bouton Exporter Excel
        btn_export = ctk.CTkButton(
            control_frame,
            text="📥 Exporter Excel",
            width=150,
            fg_color="#27ae60",
            command=self.export_to_excel
        )
        btn_export.grid(row=1, column=2, padx=10, pady=(4, 10))

        # ── Tableau (Treeview) — 8 colonnes ──
        tree_frame = ctk.CTkFrame(self)
        tree_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="nsew")

        columns = (
            "Client",
            "N° Facture",
            "Date Facture",
            "Montant (Ar)",
            "Total Payé (Ar)",
            "Solde Restant (Ar)",
            "Date Échéance",
            "Nb Jours Retard",
        )

        style = ttk.Style()
        style.configure("Retard.Treeview", rowheight=28, font=("Arial", 10))
        style.configure("Retard.Treeview.Heading", font=("Arial", 10, "bold"))

        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show='headings',
            style="Retard.Treeview"
        )

        # Tags de couleur
        self.tree.tag_configure("even",     background="#FFFFFF", foreground="#000000")
        self.tree.tag_configure("odd",      background="#FFF3F3", foreground="#000000")
        self.tree.tag_configure("critique", background="#FFCCCC", foreground="#8B0000")  # > 30 j
        self.tree.tag_configure("warning",  background="#FFF0C0", foreground="#7A5F00")  # 15-30 j

        # Largeurs de colonnes
        col_widths = {
            "Client":             180,
            "N° Facture":         130,
            "Date Facture":       110,
            "Montant (Ar)":       120,
            "Total Payé (Ar)":    120,
            "Solde Restant (Ar)": 130,
            "Date Échéance":      110,
            "Nb Jours Retard":    110,
        }
        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_by_column(c))
            self.tree.column(col, anchor="center", width=col_widths.get(col, 110))

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # ── Barre de totaux ──
        bottom_frame = ctk.CTkFrame(self)
        bottom_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(bottom_frame, text="Nombre de retards :").grid(row=0, column=0, padx=10, pady=6)
        ctk.CTkLabel(
            bottom_frame,
            textvariable=self.total_retard_count,
            font=("Arial", 12, "bold"),
            text_color="#e74c3c"
        ).grid(row=0, column=1, padx=20, pady=6)

        ctk.CTkLabel(bottom_frame, text="Montant total impayé :").grid(row=0, column=2, padx=10, pady=6)
        ctk.CTkLabel(
            bottom_frame,
            textvariable=self.total_montant,
            font=("Arial", 12, "bold"),
            text_color="#e74c3c"
        ).grid(row=0, column=3, padx=20, pady=6)

        # Légende
        ctk.CTkLabel(
            bottom_frame,
            text="  ● < 15 j   ● 15–30 j   ● > 30 j  ",
            font=("Arial", 10),
            text_color="#888888"
        ).grid(row=0, column=4, padx=30, pady=6, sticky="e")
        bottom_frame.grid_columnconfigure(4, weight=1)

    # ─────────────────────────────────────────────
    #  CHARGEMENT DES DONNÉES
    # ─────────────────────────────────────────────
    def load_data(self, filter_text: str = ""):
        conn = self.connect_db()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            today = date.today()

            query = """
                SELECT
                    c.nomcli                                       AS client,
                    v.refvente                                     AS num_facture,
                    v.dateregistre                                 AS date_facture,
                    v.totmtvente                                   AS montant_initial,
                    COALESCE(SUM(p.mtpaye), 0)                    AS total_paye,
                    (v.totmtvente - COALESCE(SUM(p.mtpaye), 0))  AS solde_restant,
                    pf.dateecheance                                AS date_echeance,
                    (%s::date - pf.dateecheance)                  AS nb_jours_retard
                FROM tb_vente v
                JOIN tb_client     c  ON v.idclient = c.idclient
                JOIN tb_pmtfacture pf ON v.refvente  = pf.refvente
                LEFT JOIN tb_pmtcredit p ON p.refvente = v.refvente
                WHERE v.idmode = 4
                  AND pf.dateecheance < %s::date
                GROUP BY c.nomcli, v.refvente, v.dateregistre,
                         v.totmtvente, pf.dateecheance
                HAVING (v.totmtvente - COALESCE(SUM(p.mtpaye), 0)) > 0
                ORDER BY nb_jours_retard DESC, c.nomcli ASC
            """
            cursor.execute(query, (today, today))
            rows = cursor.fetchall()

            if filter_text:
                rows = [r for r in rows if filter_text.lower() in str(r[0]).lower()]

            self.current_records = rows
            self.update_ui()

        except Exception as e:
            print(f"Erreur SQL: {e}")
            messagebox.showerror("Erreur", f"Erreur lors du chargement des données :\n{e}")
        finally:
            conn.close()

    # ─────────────────────────────────────────────
    #  MISE À JOUR DU TABLEAU
    # ─────────────────────────────────────────────
    def update_ui(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        total_solde = 0.0

        for idx, row in enumerate(self.current_records):
            client, num_fact, date_fact, montant, total_paye, solde_restant, date_ech, nb_jours = row

            date_fact_str = date_fact.strftime("%d/%m/%Y") if date_fact else "-"
            date_ech_str  = date_ech.strftime("%d/%m/%Y")  if date_ech  else "-"

            jours = int(nb_jours) if nb_jours is not None else 0
            if jours > 30:
                tag = "critique"
            elif jours >= 15:
                tag = "warning"
            else:
                tag = "even" if idx % 2 == 0 else "odd"

            self.tree.insert("", "end", values=(
                client,
                num_fact,
                date_fact_str,
                f"{float(montant):,.2f} Ar",
                f"{float(total_paye):,.2f} Ar",
                f"{float(solde_restant):,.2f} Ar",
                date_ech_str,
                f"{jours} jour(s)",
            ), tags=(tag,))

            total_solde += float(solde_restant)

        self.total_montant.set(f"{total_solde:,.2f} Ar")
        self.total_retard_count.set(f"{len(self.current_records)} client(s)")

    # ─────────────────────────────────────────────
    #  TRI PAR COLONNE
    # ─────────────────────────────────────────────
    def sort_by_column(self, col: str):
        col_index = {
            "Client":             0,
            "N° Facture":         1,
            "Date Facture":       2,
            "Montant (Ar)":       3,
            "Total Payé (Ar)":    4,
            "Solde Restant (Ar)": 5,
            "Date Échéance":      6,
            "Nb Jours Retard":    7,
        }.get(col, 0)

        try:
            self.current_records.sort(
                key=lambda r: (r[col_index] is None, r[col_index]),
                reverse=False
            )
        except TypeError:
            pass
        self.update_ui()

    # ─────────────────────────────────────────────
    #  EXPORTATION EXCEL (CSV)
    # ─────────────────────────────────────────────
    def export_to_excel(self):
        if not self.current_records:
            messagebox.showwarning("Aucune donnée", "Il n'y a aucune donnée à exporter.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Fichier CSV (Excel)", "*.csv"), ("Tous les fichiers", "*.*")],
            title="Exporter la liste des retards",
            initialfile=f"retards_credit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow([
                    "Client",
                    "N° Facture",
                    "Date Facture",
                    "Montant Initial (Ar)",
                    "Total Payé (Ar)",
                    "Solde Restant (Ar)",
                    "Date Échéance",
                    "Nb Jours Retard",
                ])
                for row in self.current_records:
                    client, num_fact, date_fact, montant, total_paye, solde_restant, date_ech, nb_jours = row
                    writer.writerow([
                        client,
                        num_fact,
                        date_fact.strftime("%d/%m/%Y") if date_fact else "",
                        f"{float(montant):,.2f}",
                        f"{float(total_paye):,.2f}",
                        f"{float(solde_restant):,.2f}",
                        date_ech.strftime("%d/%m/%Y") if date_ech else "",
                        int(nb_jours) if nb_jours is not None else 0,
                    ])

            messagebox.showinfo("Exportation réussie", f"Fichier exporté avec succès :\n{file_path}")
        except Exception as e:
            messagebox.showerror("Erreur d'exportation", f"Impossible d'exporter le fichier :\n{e}")


# ─────────────────────────────────────────────────
#  TEST STANDALONE
# ─────────────────────────────────────────────────
if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Retards de Paiement Crédit")
    app.geometry("1300x650")
    app.grid_rowconfigure(0, weight=1)
    app.grid_columnconfigure(0, weight=1)
    PageRetardCredit(app)
    app.mainloop()
