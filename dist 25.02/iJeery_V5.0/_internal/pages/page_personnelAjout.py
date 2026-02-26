import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import json
from datetime import datetime
from tkcalendar import DateEntry
from resource_utils import get_config_path, safe_file_read


from pages.page_personnel import PagePersonnel

class PagePeronnelAjout(ctk.CTkFrame):
    def __init__(self, master, callback_liste=None, db_conn=None, session_data=None):
        super().__init__(master)
        
        # Stocker les paramètres
        self.callback_liste = callback_liste  # ⭐ IMPORTANT : stocker le callback
        self.db_conn = db_conn
        self.session_data = session_data
        
        # Initialisation des variables
        self.selected_personnel = None
        self.mode_modification = False
        self.fonction_dict = {}
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self.create_widgets()
        self.load_fonction()
        self.generer_matricule()
        self.load_personnels()
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self.create_widgets()
        self.load_fonction()
        self.generer_matricule()
        self.load_personnels()
    
    def connect_db(self):
        try:
            with open(get_config_path('config.json')) as f:
                config = json.load(f)
                db_config = config['database']
            conn = psycopg2.connect(
                host=db_config['host'], user=db_config['user'],
                password=db_config['password'], database=db_config['database'],
                port=db_config['port']
            )
            return conn
        except Exception as e:
            messagebox.showerror("Erreur de connexion", f"Erreur : {e}")
            return None

    def _configure_table_alternating_colors(self, tree):
        """Configure des couleurs alternées: blanc + vert clair basé sur #036C6B."""
        tree.tag_configure("row_even", background="#FFFFFF")
        tree.tag_configure("row_odd", background="#D9EEED")

    def _refresh_table_alternating_colors(self, tree):
        """Réapplique l'alternance sur toutes les lignes du tableau."""
        for idx, item in enumerate(tree.get_children()):
            tree.item(item, tags=("row_even" if idx % 2 == 0 else "row_odd",))

    def create_widgets(self):
        form_frame = ctk.CTkFrame(self)
        form_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        form_frame.grid_columnconfigure((1, 3), weight=1)

        # Ligne 0 : Matricule & Nom
        ctk.CTkLabel(form_frame, text="Matricule:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.entry_matricule = ctk.CTkEntry(form_frame)
        self.entry_matricule.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        ctk.CTkLabel(form_frame, text="Nom:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.entry_nom = ctk.CTkEntry(form_frame)
        self.entry_nom.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        
        # Ligne 1 : Prénom & Date de naissance
        ctk.CTkLabel(form_frame, text="Prénom:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.entry_prenom = ctk.CTkEntry(form_frame)
        self.entry_prenom.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        ctk.CTkLabel(form_frame, text="Date de naissance:").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.entry_datenais = DateEntry(form_frame, width=12, background='darkblue',
                                        foreground='white', borderwidth=2, year=2000, 
                                        date_pattern='yyyy-mm-dd')
        self.entry_datenais.grid(row=1, column=3, padx=5, pady=5, sticky="ew")
        
        # Ligne 2 : Adresse & CIN
        ctk.CTkLabel(form_frame, text="Adresse:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.entry_adresse = ctk.CTkEntry(form_frame)
        self.entry_adresse.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        ctk.CTkLabel(form_frame, text="CIN:").grid(row=2, column=2, padx=5, pady=5, sticky="w")
        self.entry_cin = ctk.CTkEntry(form_frame)
        self.entry_cin.grid(row=2, column=3, padx=5, pady=5, sticky="ew")
        
        # Ligne 3 : Contact & Sexe
        ctk.CTkLabel(form_frame, text="Contact:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.entry_contact = ctk.CTkEntry(form_frame)
        self.entry_contact.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        
        ctk.CTkLabel(form_frame, text="Sexe:").grid(row=3, column=2, padx=5, pady=5, sticky="w")
        self.entry_sexe = ctk.CTkComboBox(form_frame, values=["M", "F"])
        self.entry_sexe.grid(row=3, column=3, padx=5, pady=5, sticky="ew")
        
        # Ligne 4 : Fonction
        ctk.CTkLabel(form_frame, text="Fonction:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.combo_fonction = ctk.CTkComboBox(form_frame, state="readonly")
        self.combo_fonction.grid(row=4, column=1, columnspan=3, padx=5, pady=5, sticky="ew")
        
        # Barre de boutons
        btn_frame = ctk.CTkFrame(form_frame)
        btn_frame.grid(row=5, column=0, columnspan=4, pady=10)
        
        ctk.CTkButton(btn_frame, text="Ajouter", command=self.ajouter_personnel).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Modifier", command=self.modifier_personnel).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Supprimer", command=self.supprimer_personnel, fg_color="red").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Nettoyer", command=self.nettoyer_formulaire).pack(side="left", padx=5)
        
        
        # Treeview
        tree_frame = ctk.CTkFrame(self)
        tree_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        
        columns = ("ID", "Matricule", "Nom", "Prénom", "Date Nais", "Adresse", "CIN", "Contact", "Fonction", "Sexe")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        self._configure_table_alternating_colors(self.tree)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

    def generer_matricule(self):
        if self.mode_modification: return 
        conn = self.connect_db()
        if not conn: return
        try:
            cursor = conn.cursor()
            annee = datetime.now().year
            cursor.execute("SELECT matricule FROM tb_personnel WHERE matricule LIKE %s ORDER BY id DESC LIMIT 1", (f"{annee}-P-%",))
            last = cursor.fetchone()
            num = 1
            if last:
                try: num = int(last[0].split('-')[-1]) + 1
                except: num = 1
            ref = f"{annee}-P-{num:05d}"
            self.entry_matricule.configure(state="normal")
            self.entry_matricule.delete(0, "end")
            self.entry_matricule.insert(0, ref)
            self.entry_matricule.configure(state="readonly")
        finally: conn.close()

    def ajouter_personnel(self):
        if self.mode_modification:
            messagebox.showwarning("Attention", "Vous êtes en mode modification. Cliquez sur Nettoyer pour ajouter.")
            return
        
        data = self.get_form_data()
        if not data: return
        
        conn = self.connect_db()
        if conn:
            try:
                cursor = conn.cursor()
                query = """INSERT INTO tb_personnel (matricule, nom, prenom, datenaissance, adresse, cin, contact, sexe, idfonction, deleted)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 0)"""
                cursor.execute(query, data)
                conn.commit()
                messagebox.showinfo("Succès", "Personnel ajouté !")
                self.load_personnels()
                self.nettoyer_formulaire()
            except Exception as e: messagebox.showerror("Erreur", str(e))
            finally: conn.close()

    def modifier_personnel(self):
        if not self.selected_personnel:
            messagebox.showwarning("Attention", "Sélectionnez un personnel dans la liste.")
            return
        
        data = self.get_form_data()
        if not data: return
        
        conn = self.connect_db()
        if conn:
            try:
                cursor = conn.cursor()
                query = """UPDATE tb_personnel SET matricule=%s, nom=%s, prenom=%s, datenaissance=%s, 
                           adresse=%s, cin=%s, contact=%s, sexe=%s, idfonction=%s WHERE id=%s"""
                cursor.execute(query, data + (self.selected_personnel,))
                conn.commit()
                messagebox.showinfo("Succès", "Informations mises à jour !")
                self.load_personnels()
                self.nettoyer_formulaire()
            except Exception as e: messagebox.showerror("Erreur", str(e))
            finally: conn.close()

    def supprimer_personnel(self):
        if not self.selected_personnel:
            messagebox.showwarning("Attention", "Sélectionnez un personnel à supprimer.")
            return
        
        if messagebox.askyesno("Confirmation", "Voulez-vous vraiment supprimer ce personnel ?"):
            conn = self.connect_db()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE tb_personnel SET deleted = 1 WHERE id = %s", (self.selected_personnel,))
                    conn.commit()
                    self.load_personnels()
                    self.nettoyer_formulaire()
                finally: conn.close()

    def get_form_data(self):
        nom = self.entry_nom.get().strip()
        f_nom = self.combo_fonction.get()
        if not nom or not f_nom:
            messagebox.showwarning("Erreur", "Le nom et la fonction sont obligatoires.")
            return None
        return (self.entry_matricule.get(), nom, self.entry_prenom.get(), self.entry_datenais.get_date(),
                self.entry_adresse.get(), self.entry_cin.get(), self.entry_contact.get(), 
                self.entry_sexe.get(), self.fonction_dict.get(f_nom))

    def nettoyer_formulaire(self):
        self.mode_modification = False
        self.selected_personnel = None
        for entry in [self.entry_nom, self.entry_prenom, self.entry_adresse, self.entry_cin, self.entry_contact]:
            entry.delete(0, 'end')
        self.entry_datenais.set_date(datetime.now())
        self.generer_matricule()

    def on_select(self, event):
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            v = item['values']
            self.selected_personnel = v[0]
            self.mode_modification = True
            self.entry_matricule.configure(state="normal")
            self.entry_matricule.delete(0, 'end'); self.entry_matricule.insert(0, v[1])
            self.entry_matricule.configure(state="readonly")
            self.entry_nom.delete(0, 'end'); self.entry_nom.insert(0, v[2])
            self.entry_prenom.delete(0, 'end'); self.entry_prenom.insert(0, v[3])
            try: self.entry_datenais.set_date(v[4])
            except: pass
            self.entry_adresse.delete(0, 'end'); self.entry_adresse.insert(0, v[5])
            self.entry_cin.delete(0, 'end'); self.entry_cin.insert(0, v[6])
            self.entry_contact.delete(0, 'end'); self.entry_contact.insert(0, v[7])
            self.combo_fonction.set(v[8]); self.entry_sexe.set(v[9])

    def load_fonction(self):
        conn = self.connect_db()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT idfonction, designationfonction FROM tb_fonction")
            fonctions = cursor.fetchall()
            self.fonction_dict = {f[1]: f[0] for f in fonctions}
            self.combo_fonction.configure(values=list(self.fonction_dict.keys()))
            conn.close()

    def load_personnels(self):
        conn = self.connect_db()
        if not conn: return
        for item in self.tree.get_children(): self.tree.delete(item)
        self._refresh_table_alternating_colors(self.tree)
        try:
            cursor = conn.cursor()
            cursor.execute("""SELECT p.id, p.matricule, p.nom, p.prenom, p.datenaissance, p.adresse, p.cin, p.contact, f.designationfonction, p.sexe
                              FROM tb_personnel p LEFT JOIN tb_fonction f ON p.idfonction = f.idfonction
                              WHERE p.deleted = 0 ORDER BY p.id DESC""")
            for row in cursor.fetchall(): self.tree.insert("", "end", values=row)
            self._refresh_table_alternating_colors(self.tree)
        finally: conn.close()
        
    def open_page_personnel(self):
        """Ouvre la page de liste du personnel"""
        if self.callback_liste:
            # Utiliser le callback pour naviguer vers la liste
            self.callback_liste()
        else:
            # Si pas de callback, afficher un message
            from tkinter import messagebox
            messagebox.showinfo(
                "Information", 
                "Utilisez le bouton de navigation pour accéder à la liste"
            )

# --- EXEMPLE D'UTILISATION (main.py simulé) ---
if __name__ == "__main__":
    def aller_a_liste():
        print("Navigation vers la liste demandée !")

    root = ctk.CTk()
    root.geometry("1100x700")
    page = PagePeronnelAjout(root, aller_a_liste)
    page.pack(fill="both", expand=True)
    root.mainloop()
