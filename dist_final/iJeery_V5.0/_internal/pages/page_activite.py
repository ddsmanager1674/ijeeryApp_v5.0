# -*- coding: utf-8 -*-
import customtkinter as ctk
import psycopg2
from datetime import datetime
import sys
import tkinter.messagebox
import json
import os


class DatabaseManager:
    def __init__(self):
        self.db_params = self._load_db_config()
        self.conn = None

    def _load_db_config(self):
        """Loads database configuration from 'config.json'."""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
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
    
    def get_connection(self):
        """Establishes a new database connection."""
        if self.db_params is None:
            print("Cannot connect: Database configuration is missing.")
            return None
        
        try:
            self.conn = psycopg2.connect(
                host=self.db_params['host'],
                user=self.db_params['user'],
                password=self.db_params['password'],
                database=self.db_params['database'],
                port=self.db_params['port']
            )
            print("Connection to the database successful!")
            return self.conn
        except psycopg2.OperationalError as e:
            print(f"Error connecting to the database: {e}")
            self.conn = None
            return None

class PageActivite(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Nouvelle Activite")
        self.geometry("400x200")
        self.resizable(False, False)

        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (self.winfo_width() // 2)
        y = (screen_height // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

        # Nous allons passer la reference de la fenetre racine (master) pour la fermer correctement
        self.master_app_root = master
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.db_manager = DatabaseManager()
        self.create_widgets()

    def create_widgets(self):
        self.designation_label = ctk.CTkLabel(self, text="Designation de l'activite :")
        self.designation_label.pack(pady=10)

        self.designation_entry = ctk.CTkEntry(self, width=250)
        self.designation_entry.pack(pady=5)

        self.save_button = ctk.CTkButton(self, text="Enregistrer", command=self.save_activity)
        self.save_button.pack(pady=20)

    def save_activity(self):
        designation = self.designation_entry.get().strip()

        if not designation:
            tkinter.messagebox.showwarning("Champ vide", "Veuillez saisir la designation de l'activite.")
            return

        conn = self.db_manager.get_connection()
        if conn is None:
            tkinter.messagebox.showerror("Erreur de connexion", "Impossible de se connecter a la base de donnees.")
            return

        try:
            cur = conn.cursor()
            current_timestamp = datetime.now()

            sql = "INSERT INTO tb_activite (designationactivite, date) VALUES (%s, %s)"
            cur.execute(sql, (designation, current_timestamp))
            conn.commit()

            tkinter.messagebox.showinfo("Succes", "Activite enregistree avec succes !")
            self.designation_entry.delete(0, ctk.END)

        except psycopg2.Error as e:
            tkinter.messagebox.showerror("Erreur de Base de Donnees", f"Une erreur est survenue : {e}")
        finally:
            if conn:
                conn.close()

    def on_closing(self):
        if tkinter.messagebox.askokcancel("Quitter", "Voulez-vous vraiment quitter l'application ?"):
            self.destroy()  # Detruit la fenetre PageActivite
            # Arrete le mainloop de la fenetre racine et la detruit egalement
            if self.master_app_root:
                self.master_app_root.quit()  # Arrete le mainloop
                self.master_app_root.destroy()  # Detruit la fenetre racine
            sys.exit(0)  # Termine le processus Python

if __name__ == "__main__":
    app_root = ctk.CTk()
    app_root.withdraw()  # Cache la fenetre racine

    activity_window = PageActivite(app_root)  # Passe la reference de app_root
    app_root.mainloop()  # Lance la boucle d'evenements