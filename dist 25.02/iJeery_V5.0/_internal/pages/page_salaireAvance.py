# -*- coding: utf-8 -*-
import customtkinter as ctk
import psycopg2
from datetime import datetime
import pandas as pd
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.pagesizes import letter
from tkinter import messagebox
import json
import os
import sys
from resource_utils import get_config_path, safe_file_read


# Ensure the parent directory is in the Python path for absolute imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# TEMPORAIREMENT DESACTIVE LES IMPORTATIONS PROBLEMATIQUES
# Remplacez False par True une fois que les fichiers sont corriges
ENABLE_OTHER_MODULES = False

PageSalaireBase = None
PageSalaireEtatSB = None
page_salaireEtatHoraire_ = None
page_avanceSpecial_ = None

if ENABLE_OTHER_MODULES:
    try:
        from pages.page_salaireBase_ import PageSalaireBase
        print("PageSalaireBase imported successfully")
    except Exception as e:
        print(f"Warning: Could not import PageSalaireBase: {e}")
        PageSalaireBase = None

    try:
        from pages.page_salaireEtatBase_ import PageSalaireEtatSB
        print("PageSalaireEtatSB imported successfully")
    except Exception as e:
        print(f"Warning: Could not import PageSalaireEtatSB: {e}")
        PageSalaireEtatSB = None

    try:
        from pages.page_salaireEtatHoraire_ import page_salaireEtatHoraire_
        print("page_salaireEtatHoraire_ imported successfully")
    except Exception as e:
        print(f"Warning: Could not import page_salaireEtatHoraire_: {e}")
        page_salaireEtatHoraire_ = None

    try:
        from pages.page_avanceSpecial_ import page_avanceSpecial_
        print("page_avanceSpecial_ imported successfully")
    except Exception as e:
        print(f"Warning: Could not import page_avanceSpecial_: {e}")
        page_avanceSpecial_ = None

class DatabaseManager:
    def __init__(self):
        self.db_params = self._load_db_config()
        self.conn = None
        self.cursor = None

    def _load_db_config(self):
        """Loads database configuration from 'config.json'."""
        try:
            config_path = get_config_path('config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config['database']
        except FileNotFoundError:
            print("Error: 'config.json' not found.")
            return None
        except KeyError:
            print("Error: 'database' key is missing in 'config.json'.")
            return None
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in 'config.json': {e}")
            return None
        except UnicodeDecodeError as e:
            print(f"Error: Encoding problem in 'config.json': {e}")
            return None

    def connect(self):
        """Establishes a new database connection."""
        if self.db_params is None:
            print("Cannot connect: Database configuration is missing.")
            return False

        try:
            self.conn = psycopg2.connect(
                host=self.db_params['host'],
                user=self.db_params['user'],
                password=self.db_params['password'],
                database=self.db_params['database'],
                port=self.db_params['port'],
                client_encoding='UTF8'
            )
            self.cursor = self.conn.cursor()
            print("Connection to the database successful!")
            return True
        except psycopg2.OperationalError as e:
            print(f"Error connecting to the database: {e}")
            self.conn = None
            self.cursor = None
            return False
        except Exception as e:
            print(f"Unexpected error connecting to database: {e}")
            self.conn = None
            self.cursor = None
            return False

    def get_connection(self):
        """Returns the database connection if connected, otherwise attempts to connect."""
        if self.conn is None or self.conn.closed:
            if self.connect():
                return self.conn
            else:
                return None
        return self.conn

    def close(self):
        """Closes the database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

def page_salaireAvance(master):
    frame = ctk.CTkFrame(master, fg_color="transparent")

    # Titre principal
    titre = ctk.CTkLabel(frame, text="GESTION DES SALAIRES ET AVANCES", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"))
    titre.pack(pady=10)

    # Variables pour la connexion a la base de donnees
    db_manager = None
    conn = None
    cursor = None

    # Connexion base de donnees
    try:
        db_manager = DatabaseManager()
        conn = db_manager.get_connection()
        
        if conn is None:
            messagebox.showerror("Erreur de connexion", "Impossible de se connecter a la base de donnees")
            return frame
            
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tb_avanceprof (
                id SERIAL PRIMARY KEY,
                reference VARCHAR(22),
                idprof INT,
                montant DOUBLE PRECISION,
                description VARCHAR(120),
                date TIMESTAMP,
                etat INT
            )
        """)
        conn.commit()
    except psycopg2.Error as err:
        messagebox.showerror("Erreur de connexion", f"Erreur : {err}")
        return frame
    except Exception as err:
        messagebox.showerror("Erreur", f"Erreur inattendue : {err}")
        return frame

    ligne_widgets = []

    def generer_reference():
        now = datetime.now()
        return now.strftime("REF%Y%m%d%H%M%S%f")[:-3]

    def charger_professeurs(filtre=""):
        if cursor is None:
            messagebox.showerror("Erreur", "Connexion a la base de donnees non disponible")
            return
            
        for widget in frame_treeview.winfo_children():
            widget.destroy()
        ligne_widgets.clear()

        filtre = filtre.lower()
        try:
            cursor.execute("SELECT id, nom, prenom FROM tb_professeur ORDER BY nom")
            data = cursor.fetchall()

            for i, (idprof, nom, prenom) in enumerate(data):
                if filtre and (filtre not in nom.lower() and filtre not in prenom.lower()):
                    continue

                ctk.CTkLabel(frame_treeview, text=nom, anchor="w", width=250).grid(row=i, column=0, padx=5, pady=2, sticky="w")
                ctk.CTkLabel(frame_treeview, text=prenom, anchor="w", width=200).grid(row=i, column=1, padx=5, pady=2, sticky="w")

                montant_entry = ctk.CTkEntry(frame_treeview, width=180)
                montant_entry.insert(0, "0")
                montant_entry.grid(row=i, column=2, padx=5, pady=2)

                desc_entry = ctk.CTkEntry(frame_treeview, width=250)
                desc_entry.grid(row=i, column=3, padx=5, pady=2)

                ligne_widgets.append((idprof, nom, prenom, montant_entry, desc_entry))
                
        except psycopg2.Error as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des professeurs : {e}")

    def enregistrer():
        if cursor is None or conn is None:
            messagebox.showerror("Erreur", "Connexion a la base de donnees non disponible")
            return
            
        try:
            enregistrements_valides = 0
            for idprof, nom, prenom, montant_entry, desc_entry in ligne_widgets:
                montant_str = montant_entry.get().replace(" ", "").replace(",", ".")
                
                try:
                    montant = float(montant_str)
                    if montant == 0:
                        continue
                except ValueError:
                    messagebox.showerror("Erreur", f"Montant invalide pour {nom} {prenom}")
                    return
                    
                description = desc_entry.get()
                ref = generer_reference()
                date = datetime.now()

                cursor.execute("""
                    INSERT INTO tb_avanceprof (reference, idprof, montant, description, date, etat)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (ref, idprof, montant, description, date, 1))
                enregistrements_valides += 1
                
            conn.commit()
            if enregistrements_valides > 0:
                messagebox.showinfo("Succes", f"{enregistrements_valides} avance(s) enregistree(s) avec succes !")
                charger_professeurs()
            else:
                messagebox.showinfo("Information", "Aucune avance a enregistrer (tous les montants sont a 0)")
                
        except psycopg2.Error as e:
            conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement : {e}")

    def exporter_excel():
        try:
            data = []
            for (_, nom, prenom, montant, desc) in ligne_widgets:
                montant_val = montant.get()
                if montant_val and montant_val != "0":
                    data.append([nom, prenom, montant_val, desc.get()])
                    
            if not data:
                messagebox.showinfo("Information", "Aucune donnee a exporter")
                return
                
            df = pd.DataFrame(data, columns=["Nom", "Prenom", "Montant", "Description"])
            filename = f"avances_professeurs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df.to_excel(filename, index=False)
            messagebox.showinfo("Exportation", f"Export Excel reussi : {filename}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'export Excel : {e}")

    def exporter_pdf():
        try:
            data = []
            for (_, nom, prenom, montant, desc) in ligne_widgets:
                montant_val = montant.get()
                if montant_val and montant_val != "0":
                    data.append([nom, prenom, montant_val, desc.get()])
                    
            if not data:
                messagebox.showinfo("Information", "Aucune donnee a exporter")
                return
                
            filename = f"avances_professeurs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf = pdf_canvas.Canvas(filename, pagesize=letter)
            pdf.drawString(100, 750, "Avances sur Salaire")
            pdf.drawString(100, 730, f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            
            y = 700
            pdf.drawString(100, y, "Nom")
            pdf.drawString(200, y, "Prenom")
            pdf.drawString(300, y, "Montant")
            pdf.drawString(400, y, "Description")
            y -= 20
            
            for nom, prenom, montant, desc in data:
                pdf.drawString(100, y, str(nom))
                pdf.drawString(200, y, str(prenom))
                pdf.drawString(300, y, str(montant))
                pdf.drawString(400, y, str(desc))
                y -= 20
                if y < 100:
                    pdf.showPage()
                    y = 750
            pdf.save()
            messagebox.showinfo("Exportation", f"Export PDF reussi : {filename}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'export PDF : {e}")

    def rechercher(event=None):
        charger_professeurs(entry_recherche.get())

    # Onglets
    tabs = ctk.CTkTabview(frame)
    tabs.pack(fill="both", expand=True)

    tab_avance = tabs.add("AVANCE")
    tab_salaire = tabs.add("SALAIRE")
    tab_etat_salaire_base = tabs.add("ETAT SALAIRE BASE")
    tab_etat_salaire_horaire = tabs.add("ETAT SALAIRE HORAIRE")
    tab_avance_special = tabs.add("AVANCE SPECIAL")

    # --- Onglet AVANCE (Fonctionnel) ---
    # Date
    ctk.CTkLabel(tab_avance, text=datetime.now().strftime("%d/%m/%Y"), font=ctk.CTkFont(family="Segoe UI", size=14)).pack(anchor="w", padx=10, pady=10)

    # Zone recherche
    search_frame = ctk.CTkFrame(tab_avance, fg_color="transparent")
    search_frame.pack(anchor="w", padx=10)
    entry_recherche = ctk.CTkEntry(search_frame, width=300, placeholder_text="Recherche...")
    entry_recherche.pack(side="left")
    entry_recherche.bind("<Return>", rechercher)

    # Boutons
    btn_frame = ctk.CTkFrame(tab_avance, fg_color="transparent")
    btn_frame.pack(anchor="w", padx=10, pady=5)

    ctk.CTkButton(btn_frame, text="Enregistrer", command=enregistrer).pack(side="left", padx=5)
    ctk.CTkButton(btn_frame, text="Exporter Excel", command=exporter_excel).pack(side="left", padx=5)
    ctk.CTkButton(btn_frame, text="Exporter PDF", command=exporter_pdf).pack(side="left", padx=5)

    # En-tetes
    header = ctk.CTkFrame(tab_avance, fg_color="transparent")
    header.pack(fill="x", padx=10)
    headers = ["Nom", "Prenom", "Montant", "Description"]
    widths = [250, 200, 180, 250]
    for i, (text, width) in enumerate(zip(headers, widths)):
        ctk.CTkLabel(header, text=text, font=ctk.CTkFont(family="Segoe UI", weight="bold"), width=width).grid(row=0, column=i, padx=5, sticky="w")

    # Zone scrollable
    scroll_frame = ctk.CTkFrame(tab_avance)
    scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)

    canvas = ctk.CTkCanvas(scroll_frame, bg="white", highlightthickness=0)
    scrollbar = ctk.CTkScrollbar(scroll_frame, orientation="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    frame_treeview = ctk.CTkFrame(canvas, fg_color="white")
    canvas.create_window((0, 0), window=frame_treeview, anchor="nw")

    def on_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    frame_treeview.bind("<Configure>", on_configure)

    # Charger les donnees initiales
    charger_professeurs()

    # --- Autres onglets (Temporairement desactives) ---
    def create_placeholder_tab(tab, module_name):
        container = ctk.CTkFrame(tab)
        container.pack(expand=True, fill="both", padx=20, pady=20)
        
        title_label = ctk.CTkLabel(container, 
                                  text=f"Module {module_name} temporairement desactive",
                                  font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"))
        title_label.pack(pady=20)
        
        info_label = ctk.CTkLabel(container,
                                 text="Ce module sera reactive une fois que les problemes d'encodage seront corriges.\n"
                                      "Pour reactiver, modifiez ENABLE_OTHER_MODULES = True dans le code.",
                                 font=ctk.CTkFont(family="Segoe UI", size=12))
        info_label.pack(pady=10)
        
        if ENABLE_OTHER_MODULES:
            status_label = ctk.CTkLabel(container, text="Status: ACTIVE", 
                                       text_color="green", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        else:
            status_label = ctk.CTkLabel(container, text="Status: DESACTIVE", 
                                       text_color="orange", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        status_label.pack(pady=5)

    # Onglet SALAIRE
    if ENABLE_OTHER_MODULES and PageSalaireBase is not None:
        try:
            page_salaire_base = PageSalaireBase(tab_salaire)
            page_salaire_base.pack(expand=True, fill="both")
        except Exception as e:
            ctk.CTkLabel(tab_salaire, text=f"Erreur: {str(e)}", 
                        font=ctk.CTkFont(family="Segoe UI", size=12)).pack(pady=20)
    else:
        create_placeholder_tab(tab_salaire, "PageSalaireBase")

    # Onglet ETAT SALAIRE BASE
    if ENABLE_OTHER_MODULES and PageSalaireEtatSB is not None:
        try:
            page_salaireEtatBase = PageSalaireEtatSB(tab_etat_salaire_base)
            page_salaireEtatBase.pack(expand=True, fill="both")
        except Exception as e:
            ctk.CTkLabel(tab_etat_salaire_base, text=f"Erreur: {str(e)}", 
                        font=ctk.CTkFont(family="Segoe UI", size=12)).pack(pady=20)
    else:
        create_placeholder_tab(tab_etat_salaire_base, "PageSalaireEtatSB")

    # Onglet ETAT SALAIRE HORAIRE
    if ENABLE_OTHER_MODULES and page_salaireEtatHoraire_ is not None:
        try:
            page_salaireEtatHoraire = page_salaireEtatHoraire_(tab_etat_salaire_horaire)
            page_salaireEtatHoraire.pack(expand=True, fill="both")
        except Exception as e:
            ctk.CTkLabel(tab_etat_salaire_horaire, text=f"Erreur: {str(e)}", 
                        font=ctk.CTkFont(family="Segoe UI", size=12)).pack(pady=20)
    else:
        create_placeholder_tab(tab_etat_salaire_horaire, "page_salaireEtatHoraire_")

    # Onglet AVANCE SPECIAL
    if ENABLE_OTHER_MODULES and page_avanceSpecial_ is not None:
        try:
            page_avanceSpecial = page_avanceSpecial_(tab_avance_special)
            page_avanceSpecial.pack(expand=True, fill="both")
        except Exception as e:
            ctk.CTkLabel(tab_avance_special, text=f"Erreur: {str(e)}", 
                        font=ctk.CTkFont(family="Segoe UI", size=12)).pack(pady=20)
    else:
        create_placeholder_tab(tab_avance_special, "page_avanceSpecial_")

    def on_closing():
        if db_manager:
            db_manager.close()

    try:
        frame.winfo_toplevel().protocol("WM_DELETE_WINDOW", on_closing)
    except:
        pass

    return frame