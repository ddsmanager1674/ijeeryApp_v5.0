import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import json
import os
import sys
from resource_utils import get_config_path, safe_file_read
from app_theme import Colors, styled, Layout
from log_utils import AppLogger


# Ensure the parent directory is in the Python path for absolute imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


class PageBanqueNv(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.configure(fg_color=Colors.BG_PAGE)

        # Connexion à la base de données
        self.conn = self.connect_db()
        self.cursor = None
        
        if self.conn:
            self.cursor = self.conn.cursor()
            self.initialize_database()

        if self.conn:  # Seulement si la connexion a réussi
            self.create_widgets()
            self.afficher_banque()  # Afficher les données après la création des widgets
            self.session_data = getattr(parent, "session_data", None) or {}
            self._logger = AppLogger(conn=self.conn, session_data=self.session_data)
        else:
            # Afficher un message d'erreur si la connexion échoue
            error_label = ctk.CTkLabel(self, text="Erreur: Impossible de se connecter à la base de données", 
                                     font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                                     text_color="red")
            error_label.pack(pady=50)

    def connect_db(self):


        try:


            from pages.db_helper import connect_page_db


            shared = (


                getattr(self, '_db_conn_shared', None)


                or getattr(self, '_db_conn_initial', None)


            )


            return connect_page_db(shared)

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

    def create_widgets(self):
        """Crée et organise tous les widgets de l'interface."""

        self.pack(fill="both", expand=True, padx=Layout.CARD_PADX, pady=Layout.CARD_PADY_TOP)

        # --- Titre ---
        self.title_card = styled.card(self)
        self.title_card.pack(fill="x", pady=(0, Layout.SECTION_GAP))
        self.title_frame = styled.frame(self.title_card, color="transparent")
        self.title_frame.pack(fill="x", padx=Layout.CARD_PADX, pady=Layout.CARD_PADY_TOP)
        styled.label_title(self.title_frame, text="Gestion des Banques").pack(anchor="w")

        # --- Actions ---
        self.buttons_card = styled.card(self)
        self.buttons_card.pack(fill="x", pady=(0, Layout.SECTION_GAP))
        self.buttons_frame = styled.frame(self.buttons_card, color="transparent")
        self.buttons_frame.pack(fill="x", padx=Layout.CARD_PADX, pady=Layout.CARD_PADY_TOP)

        self.btn_ajouter = styled.button_success(self.buttons_frame, text="Ajouter", width=160, command=self.ajouter_banque)
        self.btn_ajouter.pack(side="left", padx=(0, 10))
        self.btn_modifier = styled.button_primary(self.buttons_frame, text="Modifier", width=160, command=self.modifier_banque)
        self.btn_modifier.pack(side="left", padx=(0, 10))
        self.btn_supprimer = styled.button_danger(self.buttons_frame, text="Supprimer", width=160, command=self.supprimer_banque)
        self.btn_supprimer.pack(side="left")

        # --- Contenu principal : table + formulaire ---
        self.main_card = styled.card(self)
        self.main_card.pack(side="top", fill="both", expand=True)

        self.main_content_frame = styled.frame(self.main_card, color="transparent")
        self.main_content_frame.pack(fill="both", expand=True, padx=Layout.CARD_PADX, pady=Layout.CARD_PADY_TOP)

        # Configuration de la grille pour le main_content_frame
        self.main_content_frame.grid_columnconfigure(0, weight=2)  # Treeview prend plus d'espace
        self.main_content_frame.grid_columnconfigure(1, weight=1)  # Formulaire prend moins d'espace
        self.main_content_frame.grid_rowconfigure(0, weight=1)

        # --- Cadre pour Treeview ---
        self.treeview_frame = styled.card(self.main_content_frame)
        self.treeview_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Configuration du Treeview
        self.tree = ttk.Treeview(self.treeview_frame, columns=("ID", "Nom banque", "Adresse", "Compte"), show="headings")
        self._configure_table_alternating_colors(self.tree)
        self.tree.heading("ID", text="ID")
        self.tree.heading("Nom banque", text="Nom banque")
        self.tree.heading("Adresse", text="Adresse")
        self.tree.heading("Compte", text="Compte")

        self.tree.column("ID", width=50, stretch=False)  # ID fixe
        self.tree.column("Nom banque", width=150, anchor="w")
        self.tree.column("Adresse", width=200, anchor="w")
        self.tree.column("Compte", width=120, anchor="w")
        
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)

        # Liaison de l'événement de sélection du Treeview à une méthode
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # Style pour le Treeview (standard ttk) — harmonisé avec le thème
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Treeview.Heading", 
                       font=('Segoe UI', 9, 'bold'), 
                       background=Colors.BG_HEADER, 
                       foreground=Colors.TEXT_ON_DARK)
        style.configure("Treeview", 
                       rowheight=Layout.ROW_H, 
                       font=('Segoe UI', 9), 
                       background=Colors.BG_CARD, 
                       foreground=Colors.TEXT_PRIMARY, 
                       fieldbackground=Colors.BG_CARD,
                       borderwidth=0)
        style.map("Treeview", background=[('selected', Colors.PRIMARY_LIGHT)])

        # --- Cadre pour Champ de Saisie (Formulaire) ---
        self.entry_frame = styled.card(self.main_content_frame)
        self.entry_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # Configuration de la grille pour les champs de saisie
        self.entry_frame.grid_columnconfigure(0, weight=0)  # Labels
        self.entry_frame.grid_columnconfigure(1, weight=1)  # Entries

        # Titre du formulaire
        form_title = styled.label_heading(self.entry_frame, text="Informations Banque", size=16)
        form_title.grid(row=0, column=0, columnspan=2, pady=(16, 18))

        self.label_nombanque = styled.label_muted(self.entry_frame, text="Nom banque :")
        self.label_nombanque.grid(row=1, column=0, padx=10, pady=10, sticky="w")

        self.entry_nombanque = styled.entry(self.entry_frame, placeholder="ex: BNI")
        self.entry_nombanque.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        self.label_adresse = styled.label_muted(self.entry_frame, text="Adresse :")
        self.label_adresse.grid(row=2, column=0, padx=10, pady=10, sticky="w")

        self.entry_adresse = styled.entry(self.entry_frame, placeholder="Adresse")
        self.entry_adresse.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        self.label_numcompte = styled.label_muted(self.entry_frame, text="Compte :")
        self.label_numcompte.grid(row=3, column=0, padx=10, pady=10, sticky="w")

        self.entry_numcompte = styled.entry(self.entry_frame, placeholder="Numéro de compte")
        self.entry_numcompte.grid(row=3, column=1, padx=10, pady=10, sticky="ew")

        # Bouton pour vider les champs
        self.btn_clear = styled.button_secondary(self.entry_frame, text="Vider les champs", width=220, command=self.clear_entry_fields)
        self.btn_clear.grid(row=4, column=0, columnspan=2, pady=(18, 16))

    def on_tree_select(self, event):
        """
        Gère l'événement de sélection d'une ligne dans le Treeview.
        Remplit les champs de saisie avec les données de la ligne sélectionnée.
        """
        selected_item = self.tree.selection()
        if selected_item:
            values = self.tree.item(selected_item)['values']
            # Assurez-vous que les indices correspondent aux colonnes de votre Treeview
            if len(values) >= 4:
                self.clear_entry_fields()
                self.entry_nombanque.insert(0, str(values[1]))  # Nom banque
                self.entry_adresse.insert(0, str(values[2]))    # Adresse
                self.entry_numcompte.insert(0, str(values[3]))  # Compte
        else:
            # Si aucune ligne n'est sélectionnée, vider les champs
            self.clear_entry_fields()

    def clear_entry_fields(self):
        """Vide tous les champs de saisie du formulaire."""
        self.entry_nombanque.delete(0, ctk.END)
        self.entry_adresse.delete(0, ctk.END)
        self.entry_numcompte.delete(0, ctk.END)

    def ajouter_banque(self):
        if not self.conn:
            messagebox.showerror("Erreur", "Pas de connexion à la base de données.")
            return

        nombanque = self.entry_nombanque.get().strip()
        adresse = self.entry_adresse.get().strip()
        numcompte = self.entry_numcompte.get().strip()

        if not nombanque or not adresse or not numcompte:
            messagebox.showwarning("Champ(s) vide(s)", "Veuillez remplir tous les champs.")
            return

        try:
            self.cursor.execute(
                "INSERT INTO tb_banque (nombanque, adresse, numcompte) VALUES (%s, %s, %s)",
                (nombanque, adresse, numcompte)
            )
            self.conn.commit()
            messagebox.showinfo("Succès", "Banque ajoutée avec succès.")
            try:
                self._logger.log(
                    action="Création banque",
                    element=nombanque,
                    details=f"Banque créée, adresse='{adresse}', compte='{numcompte}'",
                    value="aucune valeur",
                )
            except Exception:
                pass
            self.clear_entry_fields()
            self.afficher_banque()
        except psycopg2.Error as err:
            self.conn.rollback()
            messagebox.showerror("Erreur d'insertion", f"Erreur lors de l'ajout : {err}")
        except Exception as err:
            self.conn.rollback()
            messagebox.showerror("Erreur inattendue", f"Une erreur inattendue est survenue : {err}")

    def modifier_banque(self):
        if not self.conn:
            messagebox.showerror("Erreur", "Pas de connexion à la base de données.")
            return

        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Aucune sélection", "Veuillez sélectionner une banque à modifier.")
            return

        banque_id = self.tree.item(selected_item)['values'][0]  # L'ID est la première valeur

        new_nombanque = self.entry_nombanque.get().strip()
        new_adresse = self.entry_adresse.get().strip()
        new_numcompte = self.entry_numcompte.get().strip()

        if not new_nombanque or not new_adresse or not new_numcompte:
            messagebox.showwarning("Champ(s) vide(s)", "Veuillez remplir tous les champs pour la modification.")
            return

        try:
            old_name = ""
            try:
                self.cursor.execute("SELECT nombanque FROM tb_banque WHERE id_banque=%s", (banque_id,))
                r = self.cursor.fetchone()
                old_name = r[0] if r and r[0] else ""
            except Exception:
                old_name = ""
            self.cursor.execute(
                "UPDATE tb_banque SET nombanque = %s, adresse = %s, numcompte = %s WHERE id_banque = %s",
                (new_nombanque, new_adresse, new_numcompte, banque_id)
            )
            self.conn.commit()
            messagebox.showinfo("Succès", "Banque modifiée avec succès.")
            try:
                self._logger.log(
                    action="Modification banque",
                    element=old_name or f"id_banque={banque_id}",
                    details=f"Banque modifiée en '{new_nombanque}', adresse='{new_adresse}', compte='{new_numcompte}'",
                    value=f"id_banque={banque_id}",
                )
            except Exception:
                pass
            self.clear_entry_fields()
            self.afficher_banque()
        except psycopg2.Error as err:
            self.conn.rollback()
            messagebox.showerror("Erreur de mise à jour", f"Erreur lors de la modification : {err}")
        except Exception as err:
            self.conn.rollback()
            messagebox.showerror("Erreur inattendue", f"Une erreur inattendue est survenue : {err}")

    def supprimer_banque(self):
        if not self.conn:
            messagebox.showerror("Erreur", "Pas de connexion à la base de données.")
            return

        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Aucune sélection", "Veuillez sélectionner une banque à supprimer.")
            return

        banque_id = self.tree.item(selected_item)['values'][0]
        nom_banque = self.tree.item(selected_item)['values'][1]

        if messagebox.askyesno("Confirmer la suppression", 
                              f"Êtes-vous sûr de vouloir supprimer la banque '{nom_banque}' ?"):
            try:
                self.cursor.execute("DELETE FROM tb_banque WHERE id_banque = %s", (banque_id,))
                self.conn.commit()
                messagebox.showinfo("Succès", "Banque supprimée avec succès.")
                try:
                    self._logger.log(
                        action="Suppression banque",
                        element=nom_banque,
                        details="Suppression banque",
                        value=f"id_banque={banque_id}",
                    )
                except Exception:
                    pass
                self.clear_entry_fields()
                self.afficher_banque()
            except psycopg2.Error as err:
                self.conn.rollback()
                messagebox.showerror("Erreur de suppression", f"Erreur lors de la suppression : {err}")
            except Exception as err:
                self.conn.rollback()
                messagebox.showerror("Erreur inattendue", f"Une erreur inattendue est survenue : {err}")

    def afficher_banque(self):
        if not self.conn:
            return

        # Effacer toutes les lignes existantes dans le Treeview
        for row in self.tree.get_children():
            self.tree.delete(row)
        self._refresh_table_alternating_colors(self.tree)

        try:
            self.cursor.execute(
                "SELECT id_banque, nombanque, adresse, numcompte FROM tb_banque ORDER BY id_banque"
            )
            for banque in self.cursor.fetchall():
                self.tree.insert("", ctk.END, values=banque)
            self._refresh_table_alternating_colors(self.tree)
        except psycopg2.Error as err:
            messagebox.showerror("Erreur de lecture", f"Erreur lors de la récupération des données : {err}")
        except Exception as err:
            messagebox.showerror("Erreur inattendue", f"Une erreur inattendue est survenue : {err}")

    def destroy(self):
        """Ferme la connexion à la base de données quand l'instance de la page est détruite."""
        if self.conn:
            try:
                self.conn.close()
                print("Connexion à la base de données fermée.")
            except Exception as e:
                print(f"Erreur lors de la fermeture de la connexion: {e}")
        super().destroy()

# Point d'entrée de l'application principale
if __name__ == '__main__':
    # Initialisation de customtkinter
    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Gestion des Banques")
    root.geometry("1000x600")  # Taille de la fenêtre principale augmentée

    # Créer une instance de notre PageBanque et l'ajouter à la fenêtre principale
    banque_page = PageBanqueNv(root)
    banque_page.pack(fill="both", expand=True)  # Remplir toute la fenêtre principale

    root.mainloop()
