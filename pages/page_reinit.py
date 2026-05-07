import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
from psycopg2 import sql # Recommandé pour composer des requêtes SQL de manière sûre

class DBInitializerApp(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Initialiseur de Base de Données PostgreSQL")
        self.geometry("700x500") # Ajuster la taille

        self.db_connection = None
        self.table_names = []
        self.create_widgets()

    def create_widgets(self):
        # Cadre pour les paramètres de connexion
        self.conn_frame = ctk.CTkFrame(self)
        self.conn_frame.pack(pady=10, padx=10, fill="x")

        # Champs pour PostgreSQL
        ctk.CTkLabel(self.conn_frame, text="Hôte:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.host_entry = ctk.CTkEntry(self.conn_frame, width=120)
        self.host_entry.grid(row=0, column=1, padx=5, pady=2)
        self.host_entry.insert(0, "localhost")

        ctk.CTkLabel(self.conn_frame, text="Port:").grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.port_entry = ctk.CTkEntry(self.conn_frame, width=60)
        self.port_entry.grid(row=0, column=3, padx=5, pady=2)
        self.port_entry.insert(0, "5432")

        ctk.CTkLabel(self.conn_frame, text="Utilisateur:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.user_entry = ctk.CTkEntry(self.conn_frame, width=120)
        self.user_entry.grid(row=1, column=1, padx=5, pady=2)
        self.user_entry.insert(0, "postgres") # ou votre utilisateur par défaut

        ctk.CTkLabel(self.conn_frame, text="Mot de passe:").grid(row=1, column=2, padx=5, pady=2, sticky="w")
        self.password_entry = ctk.CTkEntry(self.conn_frame, width=120, show="*")
        self.password_entry.grid(row=1, column=3, padx=5, pady=2)

        ctk.CTkLabel(self.conn_frame, text="Base de données:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.dbname_entry = ctk.CTkEntry(self.conn_frame, width=120)
        self.dbname_entry.grid(row=2, column=1, padx=5, pady=2)
        self.dbname_entry.insert(0, "ma_base") # Remplacez par le nom de votre DB

        self.connect_button = ctk.CTkButton(self.conn_frame, text="Connecter", command=self.connect_db)
        self.connect_button.grid(row=2, column=2, columnspan=2, padx=5, pady=5)

        # Cadre pour les tables
        self.tables_frame = ctk.CTkFrame(self)
        self.tables_frame.pack(pady=10, padx=10, fill="both", expand=True)

        ctk.CTkLabel(self.tables_frame, text="Tables trouvées (décochez si non à vider):").pack(anchor="w")
        self.table_list_scrollable_frame = ctk.CTkScrollableFrame(self.tables_frame)
        self.table_list_scrollable_frame.pack(fill="both", expand=True, pady=5)
        self.table_checkboxes = {} # Pour stocker les CTkCheckBox et leurs variables

        # Option pour CASCADE (ATTENTION)
        self.cascade_var = ctk.BooleanVar(value=False)
        self.cascade_checkbox = ctk.CTkCheckBox(self, text="Utiliser TRUNCATE ... CASCADE (vide aussi les tables dépendantes)", variable=self.cascade_var)
        self.cascade_checkbox.pack(pady=5)

        # Bouton d'initialisation
        self.init_button = ctk.CTkButton(self, text="Initialiser la Base de Données (VIDER TOUT !)",
                                        command=self.initialize_database, fg_color="red", hover_color="#8B0000", state="disabled")
        self.init_button.pack(pady=10)

        # Zone de messages
        self.log_textbox = ctk.CTkTextbox(self, height=100)
        self.log_textbox.pack(pady=10, padx=10, fill="x")
        self.log_textbox.insert("end", "Prêt.\n")

    def log_message(self, message):
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")

    def connect_db(self):
        try:
            conn_params = {
                "host": self.host_entry.get(),
                "port": self.port_entry.get(),
                "user": self.user_entry.get(),
                "password": self.password_entry.get(),
                "dbname": self.dbname_entry.get()
            }
            self.db_connection = psycopg2.connect(**conn_params)
            self.db_connection.autocommit = False # Gérer les transactions manuellement
            self.log_message(f"Connecté à la base de données: {conn_params['dbname']}")
            self.init_button.configure(state="normal")
            self.load_tables()
        except Exception as e:
            self.log_message(f"Erreur de connexion: {e}")
            self.db_connection = None
            self.init_button.configure(state="disabled")

    def load_tables(self):
        if not self.db_connection:
            self.log_message("Pas de connexion à la base de données.")
            return

        for widget in self.table_list_scrollable_frame.winfo_children():
            widget.destroy()

        self.table_checkboxes = {}
        self.table_names = []

        try:
            cursor = self.db_connection.cursor()
            # Interroger pg_tables pour les noms de tables du schéma public
            cursor.execute("""
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename;
            """)
            tables = cursor.fetchall()
            cursor.close()

            if not tables:
                self.log_message("Aucune table trouvée dans le schéma 'public'.")
                return

            self.log_message("Tables trouvées:")
            for table_row in tables:
                table_name = table_row[0]
                self.table_names.append(table_name)
                checkbox_var = ctk.BooleanVar(value=True) # Sélectionner toutes les tables par défaut
                checkbox = ctk.CTkCheckBox(self.table_list_scrollable_frame, text=table_name, variable=checkbox_var)
                checkbox.pack(anchor="w", pady=2)
                self.table_checkboxes[table_name] = checkbox_var
                self.log_message(f"- {table_name}")

        except Exception as e:
            self.log_message(f"Erreur lors du chargement des tables: {e}")
            if self.db_connection:
                self.db_connection.rollback() # Annuler si une erreur survient pendant la lecture des tables

    def initialize_database(self):
        if not self.db_connection:
            self.log_message("Pas de connexion à la base de données pour l'initialisation.")
            return

        tables_to_truncate = [name for name, var in self.table_checkboxes.items() if var.get()]
        if not tables_to_truncate:
            self.log_message("Aucune table sélectionnée pour l'initialisation.")
            return

        cascade_option = " CASCADE" if self.cascade_var.get() else ""

        # Confirmation CRUCIALE
        confirm = messagebox.askyesno(
            title="Confirmer l'initialisation PostgreSQL",
            message=f"Êtes-vous SÛR de vouloir vider le contenu des tables suivantes ?\n\n{', '.join(tables_to_truncate)}\n\n"
                    f"CETTE ACTION EST IRRÉVERSIBLE !\n\n"
                    f"{'ATTENTION: L\'option CASCADE est activée et pourrait vider des tables additionnelles !' if self.cascade_var.get() else ''}",
            icon="warning"
        )

        if not confirm:
            self.log_message("Initialisation annulée par l'utilisateur.")
            return

        cursor = self.db_connection.cursor()
        try:
            self.log_message("Début de l'initialisation...")

            # Pour PostgreSQL, l'ordre est important si pas de CASCADE
            # Vous pourriez implémenter une logique pour trier les tables par dépendances
            # Mais pour un exemple simple, on les tronque dans l'ordre de la liste

            for table_name in tables_to_truncate:
                try:
                    # Utilisation de sql.Identifier pour protéger le nom de la table
                    truncate_query = sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY{}").format(
                        sql.Identifier(table_name),
                        sql.Literal(cascade_option) # Ajout de CASCADE si coché
                    )
                    self.log_message(f"Exécution: {truncate_query.as_string(self.db_connection)}...")
                    cursor.execute(truncate_query)
                    self.log_message(f"Table '{table_name}' tronquée avec succès.")
                except Exception as e:
                    self.log_message(f"Erreur lors de la troncature de '{table_name}': {e}")
                    # Ne pas arrêter le processus si une table échoue, mais loguer l'erreur
                    # Et ne pas faire de commit si une erreur est survenue (rollback implicite si pas de commit)

            self.db_connection.commit() # Important: Valider toutes les opérations TRUNCATE
            self.log_message("Base de données initialisée avec succès (contenu vidé).")

        except Exception as e:
            self.log_message(f"Erreur générale lors de l'initialisation: {e}")
            self.db_connection.rollback() # Annuler toutes les troncatures en cas d'erreur globale
        finally:
            cursor.close()

if __name__ == "__main__":
    ctk.set_appearance_mode("Light") # Modes: "System" (default), "Dark", "Light"
    ctk.set_default_color_theme("blue") # Thèmes: "blue" (default), "dark-blue", "green"
    app = DBInitializerApp()
    app.mainloop()