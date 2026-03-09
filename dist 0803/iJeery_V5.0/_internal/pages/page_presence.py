import customtkinter as ctk
from tkinter import ttk, messagebox, Toplevel
from datetime import datetime
import psycopg2
import pandas as pd
import os
from tkcalendar import Calendar
import json
import sys
from resource_utils import get_config_path, safe_file_read


# Configuration des chemins
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    
chemin_bureau = os.path.join(os.path.expanduser("~"), "Desktop")

class DatabaseManager:
    def __init__(self):
        self.db_params = self._load_db_config()
        self.conn = None

    def _load_db_config(self):
        try:
            config_path = get_config_path('config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config['database']
        except Exception as e:
            print(f"Erreur config: {e}")
            return None

    def connect(self):
        if self.db_params is None: return False
        try:
            self.conn = psycopg2.connect(**self.db_params)
            return True
        except Exception as e:
            print(f"Erreur connexion: {e}")
            return False

    def get_connection(self):
        if self.conn is None or self.conn.closed:
            self.connect()
        return self.conn

db_manager = DatabaseManager()
conn = db_manager.get_connection()

class PagePresence(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.pack(fill="both", expand=True)
        self.liste_personnels = {}  # { "Nom Prénom": id_prof }
        self.calendar_toplevel = None

        # --- Barre supérieure (Date) ---
        frame_top = ctk.CTkFrame(self)
        frame_top.pack(anchor='nw', padx=10, pady=10)

        ctk.CTkLabel(frame_top, text="Date :").pack(side="left")
        self.date_var = ctk.StringVar(value=datetime.today().strftime("%Y-%m-%d"))
        
        self.date_display_label = ctk.CTkLabel(frame_top, textvariable=self.date_var, width=120, 
                                               fg_color="gray30", corner_radius=6, cursor="hand2")
        self.date_display_label.pack(side="left", padx=5)
        self.date_display_label.bind("<Button-1>", self.open_calendar_from_label)

        # --- Zone de Recherche ---
        frame_search = ctk.CTkFrame(self)
        frame_search.pack(fill="x", padx=10, pady=5)

        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(frame_search, textvariable=self.search_var, 
                                         placeholder_text="Rechercher un nom à ajouter...")
        self.search_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        self.search_entry.bind("<Return>", self.on_enter_pressed)

        btn_reset = ctk.CTkButton(frame_search, text="Réinitialiser", width=100, 
                                  fg_color="gray", command=self.reset_search)
        btn_reset.pack(side="left", padx=5)

        # --- Treeview ---
        frame_tree = ctk.CTkFrame(self)
        frame_tree.pack(fill="both", expand=True, padx=10, pady=10)

        colonnes = ("Nom et Prénoms", "Nombre d'heures")
        self.tree = ttk.Treeview(frame_tree, columns=colonnes, show="headings")
        for col in colonnes:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=250 if col == "Nom et Prénoms" else 100, anchor="w")

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(frame_tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", self.on_double_click)

        # --- Boutons d'action ---
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=10)

        btn_enregistrer = ctk.CTkButton(btn_frame, text="Enregistrer la présence", fg_color="#2ecc71", 
                                        hover_color="#27ae60", command=self.enregistrer)
        btn_enregistrer.pack(side="left", padx=10)

        btn_exporter = ctk.CTkButton(btn_frame, text="Exporter Excel", command=self.exporter_excel)
        btn_exporter.pack(side="left", padx=10)

        self.update_treeview()

    def open_calendar_from_label(self, event=None):
        if self.calendar_toplevel is not None and self.calendar_toplevel.winfo_exists():
            return

        self.calendar_toplevel = Toplevel(self)
        self.calendar_toplevel.title("Choisir une date")
        self.calendar_toplevel.grab_set()

        cal = Calendar(self.calendar_toplevel, selectmode='day', date_pattern='y-mm-dd')
        cal.pack(pady=10, padx=10)

        def on_date_select():
            self.date_var.set(cal.get_date())
            self.calendar_toplevel.destroy()
            self.update_treeview()

        cal.bind("<<CalendarSelected>>", lambda e: on_date_select())

    def get_presence_for_date(self, date_recherche):
        """Récupère les présences déjà enregistrées pour la date."""
        if conn is None: return {}
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.nom || ' ' || p.prenom, pr.nbheure, p.id
                FROM tb_presencepers pr
                JOIN tb_personnel p ON pr.idpers = p.id
                WHERE pr.date = %s
            """, (date_recherche,))
            data = cursor.fetchall()
            # On met à jour la liste des IDs au passage
            for row in data:
                self.liste_personnels[row[0]] = row[2]
            return {row[0]: row[1] for row in data}
        except Exception as e:
            print(f"Erreur chargement présence: {e}")
            return {}

    def rechercher_personnel_global(self, nom_recherche):
        """Recherche dans tout le personnel pour permettre l'ajout."""
        if conn is None: return []
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, nom, prenom FROM tb_personnel
                WHERE nom ILIKE %s OR prenom ILIKE %s
                ORDER BY nom ASC LIMIT 15
            """, (f"%{nom_recherche}%", f"%{nom_recherche}%"))
            return cursor.fetchall()
        except Exception as e:
            return []

    def update_treeview(self, nom_recherche=""):
        """Met à jour l'affichage et gère l'ajout par recherche."""
        selected_date = self.date_var.get()

        if not nom_recherche:
            # Mode normal : On vide et on affiche les présents du jour
            for row in self.tree.get_children():
                self.tree.delete(row)
            
            presences = self.get_presence_for_date(selected_date)
            for nom, heures in presences.items():
                self.tree.insert("", "end", values=(nom, heures))
        else:
            # Mode recherche : On ajoute les résultats sans vider le reste
            resultats = self.rechercher_personnel_global(nom_recherche)
            for id_p, nom, prenom in resultats:
                full_name = f"{nom} {prenom}"
                # Vérifier les doublons visuels
                deja_dans_liste = any(self.tree.item(i)['values'][0] == full_name for i in self.tree.get_children())
                
                if not deja_dans_liste:
                    self.liste_personnels[full_name] = id_p
                    self.tree.insert("", 0, values=(full_name, ""), tags=('nouveau',))
            self.search_var.set("")

    def reset_search(self):
        """Vide la recherche et réinitialise la liste du jour."""
        self.search_var.set("")
        self.update_treeview()

    def on_enter_pressed(self, event):
        self.update_treeview(self.search_var.get())

    def enregistrer(self):
        """Enregistre toutes les lignes du tableau en base de données."""
        if conn is None: return
        date_sel = self.date_var.get()
        cursor = conn.cursor()

        try:
            for item in self.tree.get_children():
                nom_prenom, nbheure = self.tree.item(item)['values']
                idpers = self.liste_personnels.get(nom_prenom)

                if idpers and str(nbheure).strip() != "":
                    # Mise à jour ou Insertion (UPSERT)
                    cursor.execute("""
                        INSERT INTO tb_presencepers (idpers, nbheure, date)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (idpers, date) DO UPDATE SET nbheure = EXCLUDED.nbheure
                    """, (idpers, float(nbheure), date_sel))
                elif idpers:
                    # Si vide, on supprime la présence pour ce jour
                    cursor.execute("DELETE FROM tb_presencepers WHERE idpers = %s AND date = %s", (idpers, date_sel))
            
            conn.commit()
            messagebox.showinfo("Succès", "Présences enregistrées.")
            self.reset_search()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement: {e}")

    def on_double_click(self, event):
        item = self.tree.identify('item', event.x, event.y)
        column = self.tree.identify_column(event.x)
        if column == '#2' and item:
            self.edit_treeview_cell(item, column)

    def edit_treeview_cell(self, item, column_id):
        x, y, w, h = self.tree.bbox(item, column_id)
        current_val = self.tree.item(item, 'values')[1]
        entry = ctk.CTkEntry(self.tree, width=w, height=h)
        entry.place(x=x, y=y)
        entry.insert(0, current_val)
        entry.focus_force()

        def save_edit(event=None):
            new_val = entry.get()
            vals = list(self.tree.item(item, 'values'))
            vals[1] = new_val
            self.tree.item(item, values=vals)
            entry.destroy()

        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", save_edit)

    def exporter_excel(self):
        date_export = self.date_var.get()
        data = []
        for item in self.tree.get_children():
            data.append(self.tree.item(item)['values'])
        
        if data:
            df = pd.DataFrame(data, columns=["Nom et Prénom", "Nombre d'heures"])
            path = os.path.join(chemin_bureau, f"Presence_{date_export}.xlsx")
            df.to_excel(path, index=False)
            messagebox.showinfo("Export", f"Fichier créé : {path}")

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    app = ctk.CTk()
    app.title("Système de Présence")
    app.geometry("800x600")
    if conn:
        PagePresence(app)
        app.mainloop()