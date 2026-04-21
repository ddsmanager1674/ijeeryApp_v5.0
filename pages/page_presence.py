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

# Thème UI iJeery (référence: page_suiviPresence.py)
from app_theme import Colors, Fonts, Theme, styled, Layout


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
        # [UI] Refonte visuelle alignée au thème iJeery (header + cards + boutons)
        # [LOGIQUE] Aucune modification des requêtes SQL/UPSERT ; uniquement mise en forme et style
        super().__init__(master, fg_color=Colors.BG_PAGE)
        self.pack(fill="both", expand=True)
        self.liste_personnels = {}  # { "Nom Prénom": id_prof }
        self.calendar_toplevel = None

        self._setup_treeview_style()

        # Layout global
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT, corner_radius=0, height=46)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)

        left = styled.frame(header)
        left.grid(row=0, column=0, padx=14, sticky="w")
        ctk.CTkLabel(left, text="✅", font=Fonts.heading(16), text_color=Colors.TEXT_ON_DARK).pack(side="left", padx=(0, 8))
        inner = styled.frame(left)
        inner.pack(side="left")
        ctk.CTkLabel(inner, text="Présence", font=Fonts.bold(13), text_color=Colors.TEXT_ON_DARK).pack(anchor="w")
        ctk.CTkLabel(inner, text="Saisie des heures de présence", font=Fonts.small(9), text_color=Colors.TEXT_ON_DARK_DIM).pack(anchor="w")

        # Card outils (date + recherche)
        tools = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        tools.grid(row=1, column=0, sticky="ew", padx=10, pady=(10, 6))
        tools.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(tools, text="Date :", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(row=0, column=0, padx=(12, 6), pady=10, sticky="w")
        self.date_var = ctk.StringVar(value=datetime.today().strftime("%Y-%m-%d"))
        self.date_display_label = ctk.CTkLabel(
            tools,
            textvariable=self.date_var,
            width=140,
            fg_color=Colors.BG_INPUT,
            text_color=Colors.TEXT_PRIMARY,
            corner_radius=8,
            cursor="hand2",
        )
        self.date_display_label.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="w")
        self.date_display_label.bind("<Button-1>", self.open_calendar_from_label)

        ctk.CTkLabel(tools, text="Recherche :", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(row=0, column=2, padx=(0, 6), pady=10, sticky="w")
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            tools,
            textvariable=self.search_var,
            height=32,
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            corner_radius=8,
            font=Fonts.body(11),
            placeholder_text="Nom ou prénom à ajouter…",
        )
        self.search_entry.grid(row=0, column=3, padx=(0, 10), pady=10, sticky="ew")
        self.search_entry.bind("<Return>", self.on_enter_pressed)

        styled.button_secondary(tools, text="Réinitialiser", icon="↺", width=130, height=32, command=self.reset_search).grid(row=0, column=4, padx=(0, 12), pady=10, sticky="e")

        # Card table
        table_card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        table_card.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 6))
        table_card.grid_columnconfigure(0, weight=1)
        table_card.grid_rowconfigure(0, weight=1)

        colonnes = ("Nom et Prénoms", "Nombre d'heures")
        self.tree = ttk.Treeview(table_card, columns=colonnes, show="headings", style="P.Treeview", selectmode="browse")
        self.tree.heading("Nom et Prénoms", text="Nom et Prénoms")
        self.tree.heading("Nombre d'heures", text="Nombre d'heures")
        self.tree.column("Nom et Prénoms", width=320, anchor="w")
        self.tree.column("Nombre d'heures", width=140, anchor="center")
        self.tree.tag_configure("row_even", background=Colors.BG_CARD)
        self.tree.tag_configure("row_odd", background=Colors.BG_ROW_ALT)

        vsb = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        vsb.grid(row=0, column=1, sticky="ns", pady=6)
        self.tree.bind("<Double-1>", self.on_double_click)

        # Card actions
        actions = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        actions.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 10))

        styled.button_success(actions, text="Enregistrer", icon="💾", width=170, height=32, command=self.enregistrer).pack(side="left", padx=10, pady=10)
        styled.button_premium(actions, text="Exporter Excel", icon="📊", width=160, height=32, command=self.exporter_excel).pack(side="left", padx=0, pady=10)

        self.update_treeview()

    def _setup_treeview_style(self):
        # [UI] Style Treeview cohérent avec les pages modernes (en-tête sombre + sélection primaire)
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure(
            "P.Treeview",
            background=Colors.BG_CARD,
            foreground=Colors.TEXT_PRIMARY,
            fieldbackground=Colors.BG_CARD,
            rowheight=26,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        s.configure(
            "P.Treeview.Heading",
            background=Colors.MIDNIGHT,
            foreground=Colors.TEXT_ON_DARK,
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padding=(6, 5),
        )
        s.map("P.Treeview", background=[("selected", Colors.PRIMARY_LIGHT)])
        s.map("P.Treeview.Heading", background=[("active", Colors.MIDNIGHT_LIGHT)])

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
            self._refresh_table_alternating_colors()
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
            self._refresh_table_alternating_colors()

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
        finally:
            # [UI] Rafraîchit l'alternance des lignes après opérations
            self._refresh_table_alternating_colors()

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
            try:
                from log_utils import AppLogger
                AppLogger(session_data=getattr(self, "session_data", {}) or {}).log(
                    action="Export Excel",
                    element="Présence",
                    details=f"export présence (date={date_export}), lignes={len(df)}, fichier={os.path.basename(path)}",
                    value=path,
                )
            except Exception:
                pass

    def _refresh_table_alternating_colors(self):
        # [UI] Applique l’alternance de lignes selon la palette du thème
        for idx, item in enumerate(self.tree.get_children()):
            tag = "row_even" if idx % 2 == 0 else "row_odd"
            existing = tuple(t for t in self.tree.item(item, "tags") if t not in ("row_even", "row_odd"))
            self.tree.item(item, tags=(tag,) + existing)

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    app = ctk.CTk()
    app.title("Système de Présence")
    app.geometry("800x600")
    if conn:
        PagePresence(app)
        app.mainloop()