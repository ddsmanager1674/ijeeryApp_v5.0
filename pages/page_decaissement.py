# page_decaissement.py
import customtkinter as ctk
from tkinter import messagebox, ttk
import psycopg2
from datetime import datetime
import json
import os
import sys
from reportlab.lib.pagesizes import portrait
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from resource_utils import get_config_path, safe_file_read


# Ensure the parent directory is in the Python path for absolute imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Now, the absolute import will work
from pages.page_categorieCompte import PageCategorieCompte


class PageDecaissement(ctk.CTkToplevel):
    def __init__(self, master, username="Système"):
        super().__init__(master)
        self.title("Décaissements")
        # Fenêtre plus grande pour inclure la liste
        self.geometry("900x680")
        self.transient(master)
        self.grab_set()
        self.center_window()

        self.master_app = master
        # Charger utilisateur/session
        loaded_username, loaded_user_id = self._load_user_session()
        # priorité: session -> paramètre -> défaut
        if loaded_username:
            self.current_user = loaded_username
        elif username and username != "Système":
            self.current_user = username
        else:
            self.current_user = username
        self.current_user_id = loaded_user_id

        self.categories = {}
        # Protection contre les double-clics
        self._processing = False
        self._finalized = False
        # ID de la ligne sélectionnée pour modification
        self.selected_id = None

        # Connexion à la base de données
        self.conn = self.connect_db()
        if self.conn:
            self.cursor = self.conn.cursor()
            self.create_widgets()
            # actualiser le label opérateur
            try:
                self.lbl_user.configure(text=f"Opérateur : {self.current_user}")
            except Exception:
                pass
            self.charger_categories()
            self.charger_liste()
        else:
            messagebox.showerror("Erreur", "Connexion échouée")
            self.destroy()

    def center_window(self):
        """Centre cette fenêtre sur l'écran."""
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _load_user_session(self):
        """Récupère (username, user_id) depuis session.json si possible."""
        try:
            session_path = get_config_path('session.json')
            if session_path and os.path.exists(session_path):
                with open(session_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    username = data.get('username') or data.get('user')
                    user_id = data.get('user_id') or data.get('id') or data.get('iduser')
                    return username, user_id
        except Exception as e:
            print(f"DEBUG: impossible de charger session.json: {e}")
        return None, None

    def connect_db(self):
        """Établit la connexion à la base de données à partir du fichier config.json"""
        try:
            config_path = get_config_path('config.json')
            if not os.path.exists(config_path):
                config_path = 'config.json'
                
            if not os.path.exists(config_path):
                messagebox.showerror("Erreur", "Fichier config.json manquant.")
                return None
                 
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                db_config = config['database']

            conn = psycopg2.connect(
                host=db_config['host'],
                user=db_config['user'],
                password=db_config['password'],
                database=db_config['database'],
                port=db_config['port'],
                client_encoding='UTF8'
            )
            print("Connection to the database successful!")
            return conn
        except Exception as err:
            messagebox.showerror("Erreur de connexion", f"Détails : {err}")
            return None

    def create_widgets(self):
        """Crée et positionne les widgets de l'interface utilisateur avec un design épuré."""
        # cadre principal
        main = ctk.CTkFrame(self, fg_color="#f0f0f0", corner_radius=10)
        main.pack(expand=True, fill="both", padx=20, pady=20)

        # ── PARTIE HAUTE : liste des décaissements ──────────────────────────
        list_frame = ctk.CTkFrame(main, fg_color="white", corner_radius=8)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        list_header = ctk.CTkFrame(list_frame, fg_color="transparent")
        list_header.pack(fill="x", padx=10, pady=(8, 0))

        ctk.CTkLabel(list_header, text="LISTE DES DÉCAISSEMENTS",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")

        # Champ de recherche
        search_frame = ctk.CTkFrame(list_header, fg_color="transparent")
        search_frame.pack(side="right")
        ctk.CTkLabel(search_frame, text="🔍 Recherche:").pack(side="left", padx=(0, 4))
        self.entry_search = ctk.CTkEntry(search_frame, width=200, placeholder_text="Réf, catégorie, description…")
        self.entry_search.pack(side="left")
        self.entry_search.bind("<KeyRelease>", lambda e: self.charger_liste())

        # Tableau (ttk.Treeview)
        tree_frame = ctk.CTkFrame(list_frame, fg_color="transparent")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=8)

        columns = ("id", "date", "reference", "categorie", "montant", "description", "operateur")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=8)

        # Style du tableau
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="white", foreground="black",
                        rowheight=24, fieldbackground="white", font=("Arial", 10))
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"),
                        background="#d0e4f7", foreground="#003366")
        style.map("Treeview", background=[("selected", "#3a7ebf")],
                  foreground=[("selected", "white")])

        # Définir les colonnes
        col_cfg = {
            "id":          ("ID",          50,  False),
            "date":        ("Date",        130, False),
            "reference":   ("Référence",   130, True),
            "categorie":   ("Catégorie",   140, True),
            "montant":     ("Montant (Ar)",110, False),
            "description": ("Description", 180, True),
            "operateur":   ("Opérateur",   100, True),
        }
        for col, (heading, width, stretch) in col_cfg.items():
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width, stretch=stretch, anchor="w")

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Sélection d'une ligne → remplir le formulaire
        self.tree.bind("<<TreeviewSelect>>", self.on_row_selected)

        # ── PARTIE BASSE : formulaire ────────────────────────────────────────
        form_outer = ctk.CTkFrame(main, fg_color="white", corner_radius=8)
        form_outer.pack(fill="x", padx=10, pady=(0, 5))

        ctk.CTkLabel(form_outer, text="NOUVEAU DÉCAISSEMENT / MODIFICATION",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(8, 4))

        form = ctk.CTkFrame(form_outer, fg_color="transparent")
        form.pack(fill="x", padx=15, pady=6)
        form.grid_columnconfigure(1, weight=1)

        # Catégorie
        ctk.CTkLabel(form, text="Catégorie:", anchor="w").grid(row=0, column=0, padx=5, pady=6, sticky='w')
        self.combo_categorie = ctk.CTkComboBox(form, width=200, values=[], state="readonly")
        self.combo_categorie.grid(row=0, column=1, padx=5, pady=6, sticky='ew')
        self.bouton_ajouter_categorie = ctk.CTkButton(form, text="+", width=30,
                                                      command=self.ouvrir_fenetre_categorie)
        self.bouton_ajouter_categorie.grid(row=0, column=2, padx=5, pady=6)

        # Montant
        ctk.CTkLabel(form, text="Montant:", anchor="w").grid(row=1, column=0, padx=5, pady=6, sticky='w')
        montant_frame = ctk.CTkFrame(form, fg_color="transparent")
        montant_frame.grid(row=1, column=1, columnspan=2, padx=5, pady=6, sticky='ew')
        montant_frame.grid_columnconfigure(0, weight=1)

        self.entry_montant = ctk.CTkEntry(montant_frame, width=200)
        self.entry_montant.grid(row=0, column=0, sticky='ew')
        self.entry_montant.bind("<KeyRelease>", lambda e: self.format_montant())
        self.entry_montant.bind("<FocusOut>", lambda e: self.format_montant())

        # Description
        ctk.CTkLabel(form, text="Description:", anchor="w").grid(row=2, column=0, padx=5, pady=6, sticky='w')
        self.entry_description = ctk.CTkEntry(form, width=200)
        self.entry_description.grid(row=2, column=1, columnspan=2, padx=5, pady=6, sticky='ew')

        # ── Bannière d'autorisation (visible uniquement en mode modification) ──
        self.banner_autorisation = ctk.CTkFrame(form_outer, fg_color="#FFF3CD", corner_radius=6)
        # packée dynamiquement selon le mode

        banner_inner = ctk.CTkFrame(self.banner_autorisation, fg_color="transparent")
        banner_inner.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(
            banner_inner,
            text="Tous les champs sont verrouilles. Saisissez le code d'autorisation pour modifier.",
            font=ctk.CTkFont(size=11),
            text_color="#856404",
        ).pack(side="left", padx=(0, 10))

        self.btn_unlock_global = ctk.CTkButton(
            banner_inner,
            text="Saisir le code",
            width=150, height=28,
            fg_color="#FF9500",
            hover_color="#cc7700",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.demander_code_autorisation,
        )
        self.btn_unlock_global.pack(side="right")

        # Boutons d'action
        button_frame = ctk.CTkFrame(form_outer, fg_color="transparent")
        button_frame.pack(pady=10)

        self.bouton_enregistrer = ctk.CTkButton(
            button_frame, text="Enregistrer", fg_color="#007AFF",
            hover_color="#005BB5", width=120, command=self._on_enregistrer_click)
        self.bouton_enregistrer.pack(side="left", padx=8)

        self.bouton_modifier = ctk.CTkButton(
            button_frame, text="Modifier", fg_color="#34C759",
            hover_color="#248A3D", width=120, command=self._on_modifier_click,
            state="disabled")
        self.bouton_modifier.pack(side="left", padx=8)

        self.bouton_nouveau = ctk.CTkButton(
            button_frame, text="Nouveau", fg_color="#5856D6",
            hover_color="#3A38B5", width=120, command=self.vider_formulaire)
        self.bouton_nouveau.pack(side="left", padx=8)

        self.bouton_annuler = ctk.CTkButton(
            button_frame, text="Fermer", fg_color="#FF3B30",
            hover_color="#C1271A", width=120, command=self.annuler)
        self.bouton_annuler.pack(side="left", padx=8)

        self.lbl_user = ctk.CTkLabel(form_outer,
                                     text=f"Operateur : {self.current_user}",
                                     font=ctk.CTkFont(size=10))
        self.lbl_user.pack(pady=(0, 6))

    # ── LISTE ────────────────────────────────────────────────────────────────

    def charger_liste(self):
        """Charge et affiche les décaissements, ordre décroissant (plus récents en premier)."""
        if not self.conn or not self.cursor:
            return
        try:
            keyword = self.entry_search.get().strip().lower() if hasattr(self, 'entry_search') else ""

            query = """
                SELECT d.id, d.datepmt, d.refpmt,
                       cc.categoriecompte, d.mtpaye, d.observation,
                       COALESCE(u.username, 'N/A') as operateur
                FROM tb_decaissement d
                LEFT JOIN tb_categoriecompte cc ON d.idcc = cc.idcc
                LEFT JOIN tb_users u ON d.iduser = u.iduser
                ORDER BY d.datepmt DESC, d.id DESC
            """
            self.cursor.execute(query)
            rows = self.cursor.fetchall()

            # Vider le tableau
            for item in self.tree.get_children():
                self.tree.delete(item)

            for row in rows:
                id_, datepmt, refpmt, categorie, mtpaye, observation, operateur = row
                date_str = datepmt.strftime("%d/%m/%Y %H:%M") if datepmt else ""
                montant_str = f"{float(mtpaye):,.0f}".replace(",", ".") if mtpaye else "0"
                categorie = categorie or "—"
                observation = observation or ""
                operateur = operateur or "N/A"

                # Filtre de recherche
                if keyword:
                    haystack = f"{refpmt} {categorie} {observation} {operateur}".lower()
                    if keyword not in haystack:
                        continue

                self.tree.insert("", "end", iid=str(id_),
                                 values=(id_, date_str, refpmt, categorie,
                                         montant_str, observation, operateur))

        except Exception as e:
            print(f"Erreur chargement liste: {e}")

    def on_row_selected(self, event):
        """Remplit le formulaire avec la ligne sélectionnée et verrouille tous les champs."""
        selection = self.tree.selection()
        if not selection:
            return
        item = self.tree.item(selection[0])
        values = item["values"]
        if not values:
            return

        # values: (id, date, reference, categorie, montant, description, operateur)
        self.selected_id = values[0]

        # Remplir catégorie
        categorie_nom = values[3]
        if categorie_nom in self.categories:
            self.combo_categorie.set(categorie_nom)

        # Remplir montant
        self._set_montant_value(str(values[4]).replace(".", "").replace(",", ""))

        # Remplir description
        self.entry_description.delete(0, "end")
        self.entry_description.insert(0, values[5])

        # Activer le bouton Modifier, désactiver Enregistrer
        self.bouton_modifier.configure(state="normal")
        self.bouton_enregistrer.configure(state="disabled")

        # Verrouiller TOUS les champs et afficher la bannière d'autorisation
        self._lock_all_fields()

    def _set_montant_value(self, value):
        """Insère une valeur dans le champ montant même s'il est disabled."""
        current_state = self.entry_montant.cget("state")
        self.entry_montant.configure(state="normal")
        self.entry_montant.delete(0, "end")
        self.entry_montant.insert(0, value)
        self.entry_montant.configure(state=current_state)

    def vider_formulaire(self):
        """Remet le formulaire à zéro pour une nouvelle saisie (tous les champs libres)."""
        self.selected_id = None
        if self.combo_categorie.cget("values"):
            self.combo_categorie.set(self.combo_categorie.cget("values")[0])
        self._set_montant_value("")
        self.entry_description.delete(0, "end")
        self._unlock_all_fields_free()  # tous les champs libres pour nouveau enregistrement
        self.bouton_modifier.configure(state="disabled")
        self.bouton_enregistrer.configure(state="normal")
        self.tree.selection_remove(self.tree.selection())

    # ── VERROUILLAGE GLOBAL (mode modification) ───────────────────────────────

    def _lock_all_fields(self):
        """Verrouille tous les champs du formulaire et affiche la bannière d'autorisation."""
        # Montant
        self.entry_montant.configure(state="disabled",
                                     fg_color="#e0e0e0",
                                     text_color="#888888")
        # Description
        self.entry_description.configure(state="disabled",
                                         fg_color="#e0e0e0",
                                         text_color="#888888")
        # Catégorie (readonly + grisé visuellement)
        self.combo_categorie.configure(state="disabled",
                                       fg_color="#e0e0e0",
                                       text_color="#888888")
        # Bouton "+" catégorie
        self.bouton_ajouter_categorie.configure(state="disabled")

        # Bouton Modifier désactivé jusqu'à déverrouillage
        self.bouton_modifier.configure(state="disabled")

        # Afficher la bannière d'autorisation
        self.banner_autorisation.pack(fill="x", padx=15, pady=(0, 6),
                                      before=self.bouton_modifier.master)
        self.btn_unlock_global.configure(text="Saisir le code d'autorisation",
                                          fg_color="#FF9500",
                                          hover_color="#cc7700",
                                          command=self.demander_code_autorisation)

    def _unlock_all_fields(self):
        """Déverrouille tous les champs après code d'autorisation (mode modification)."""
        # Montant
        self.entry_montant.configure(state="normal",
                                     fg_color=("white", "#2b2b2b"),
                                     text_color=("black", "white"))
        self.entry_montant.bind("<KeyRelease>", lambda e: self.format_montant())
        self.entry_montant.bind("<FocusOut>", lambda e: self.format_montant())
        # Description
        self.entry_description.configure(state="normal",
                                         fg_color=("white", "#2b2b2b"),
                                         text_color=("black", "white"))
        # Catégorie
        self.combo_categorie.configure(state="readonly",
                                        fg_color=("white", "#2b2b2b"),
                                        text_color=("black", "white"))
        # Bouton "+" catégorie
        self.bouton_ajouter_categorie.configure(state="normal")

        # Bouton Modifier activé
        self.bouton_modifier.configure(state="normal")

        # Mettre à jour la bannière pour signaler le déverrouillage
        self.btn_unlock_global.configure(text="Verrouiller a nouveau",
                                          fg_color="#34C759",
                                          hover_color="#248A3D",
                                          command=self._lock_all_fields)

    def _unlock_all_fields_free(self):
        """Libère tous les champs pour une nouvelle saisie (pas de verrou)."""
        # Montant
        self.entry_montant.configure(state="normal",
                                     fg_color=("white", "#2b2b2b"),
                                     text_color=("black", "white"))
        self.entry_montant.bind("<KeyRelease>", lambda e: self.format_montant())
        self.entry_montant.bind("<FocusOut>", lambda e: self.format_montant())
        # Description
        self.entry_description.configure(state="normal",
                                         fg_color=("white", "#2b2b2b"),
                                         text_color=("black", "white"))
        # Catégorie
        self.combo_categorie.configure(state="readonly",
                                        fg_color=("white", "#2b2b2b"),
                                        text_color=("black", "white"))
        # Bouton "+"
        self.bouton_ajouter_categorie.configure(state="normal")

        # Masquer la bannière d'autorisation
        self.banner_autorisation.pack_forget()

    # Compatibilité avec les anciens appels internes
    def _lock_montant(self):
        self._lock_all_fields()

    def _unlock_montant(self):
        self._unlock_all_fields()

    def _reset_montant_libre(self):
        self._unlock_all_fields_free()

    def demander_code_autorisation(self):
        """Ouvre une fenêtre modale pour saisir le code d'autorisation.
        En cas de succès, déverrouille tous les champs du formulaire."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Code d'autorisation requis")
        dialog.geometry("360x200")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        # Centrer sur la fenêtre parente
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 360) // 2
        y = self.winfo_y() + (self.winfo_height() - 200) // 2
        dialog.geometry(f"360x200+{x}+{y}")

        ctk.CTkLabel(
            dialog,
            text="Modification protegee",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#856404",
        ).pack(pady=(18, 2))

        ctk.CTkLabel(
            dialog,
            text="Saisissez le code d'autorisation pour\ndebler la modification de tous les champs.",
            font=ctk.CTkFont(size=11),
            text_color="#555555",
            justify="center",
        ).pack(pady=(0, 8))

        entry_code = ctk.CTkEntry(dialog, width=220, show="*",
                                   placeholder_text="Code d'autorisation")
        entry_code.pack(pady=4)
        entry_code.focus()

        def verifier():
            code = entry_code.get().strip()
            if not code:
                messagebox.showwarning("Attention", "Veuillez saisir un code.", parent=dialog)
                return
            try:
                self.cursor.execute(
                    "SELECT id FROM tb_codeautorisation WHERE code = %s AND deleted = 0",
                    (code,)
                )
                result = self.cursor.fetchone()
                if result:
                    dialog.destroy()
                    self._unlock_all_fields()
                    messagebox.showinfo(
                        "Acces autorise",
                        "Tous les champs sont maintenant modifiables.\n"
                        "Cliquez sur 'Modifier' pour enregistrer vos changements."
                    )
                else:
                    messagebox.showerror("Code refuse",
                                         "Code incorrect ou non autorise.", parent=dialog)
                    entry_code.delete(0, "end")
                    entry_code.focus()
            except Exception as e:
                messagebox.showerror("Erreur", str(e), parent=dialog)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Valider", width=110,
                      fg_color="#007AFF", command=verifier).pack(side="left", padx=6)
        ctk.CTkButton(btn_frame, text="Annuler", width=110,
                      fg_color="#FF3B30", command=dialog.destroy).pack(side="left", padx=6)
        entry_code.bind("<Return>", lambda e: verifier())

    # ── FORMULAIRE ───────────────────────────────────────────────────────────

    def ouvrir_fenetre_categorie(self):
        """Ouvre la fenêtre de catégorie et gère le retour en toute sécurité."""
        try:
            category_window = PageCategorieCompte(self)
            self.wait_window(category_window)
            if self.winfo_exists():
                self.charger_categories()
        except Exception as e:
            print(f"Erreur lors de la mise à jour : {e}")

    def format_montant(self):
        """Formate le montant en milliers (format français) et positionne le curseur en fin."""
        current = self.entry_montant.get()
        if not current:
            return
        cleaned = current.replace('.', '').replace(',', '').replace(' ', '')
        if not cleaned or not cleaned.isdigit():
            return
        formatted = ''
        for i, digit in enumerate(reversed(cleaned)):
            if i > 0 and i % 3 == 0:
                formatted = '.' + formatted
            formatted = digit + formatted
        self.entry_montant.delete(0, 'end')
        self.entry_montant.insert(0, formatted)
        self.entry_montant.icursor(len(formatted))

    def _on_enregistrer_click(self):
        """Wrapper pour empêcher les double-clics rapides sur le bouton Enregistrer."""
        if self._processing or self._finalized:
            messagebox.showwarning("Attention", "L'enregistrement est déjà en cours...")
            return
        try:
            self._processing = True
            self.bouton_enregistrer.configure(state="disabled")
            self.bouton_annuler.configure(state="disabled")
            self.enregistrer()
        finally:
            if self.winfo_exists() and not self._finalized:
                self._processing = False
                try:
                    self.bouton_enregistrer.configure(state="normal")
                    self.bouton_annuler.configure(state="normal")
                except:
                    pass

    def _on_modifier_click(self):
        """Enregistre les modifications sur la ligne sélectionnée.
        Refuse si les champs sont encore verrouillés (code d'autorisation non saisi)."""
        if self.selected_id is None:
            messagebox.showwarning("Attention", "Aucune ligne sélectionnée.")
            return

        # Vérifier que les champs ont bien été déverrouillés
        if self.entry_montant.cget("state") == "disabled":
            messagebox.showwarning(
                "Autorisation requise",
                "Vous devez saisir le code d'autorisation avant de pouvoir modifier."
            )
            self.demander_code_autorisation()
            return

        categorie_nom = self.combo_categorie.get()
        idcc = self.categories.get(categorie_nom)
        mtpaye_str = self.entry_montant.get()
        observation = self.entry_description.get()

        if not idcc or not observation:
            messagebox.showwarning("Attention", "Catégorie et description sont obligatoires.")
            return

        try:
            if not mtpaye_str:
                messagebox.showwarning("Attention", "Veuillez saisir un montant.")
                return
            mtpaye = float(mtpaye_str.replace('.', '').replace(',', ''))
            self.cursor.execute(
                """UPDATE tb_decaissement
                   SET idcc = %s, mtpaye = %s, observation = %s
                   WHERE id = %s""",
                (idcc, mtpaye, observation, self.selected_id)
            )

            self.conn.commit()
            messagebox.showinfo("Succes", f"Decaissement #{self.selected_id} modifie avec succes.")
            self.vider_formulaire()
            self.charger_liste()

        except ValueError:
            messagebox.showerror("Erreur", "Le montant doit etre un nombre valide.")
            self.conn.rollback()
        except Exception as e:
            messagebox.showerror("Erreur SQL", str(e))
            self.conn.rollback()

    def generer_reference(self):
        """Génère une référence unique pour le décaissement."""
        now = datetime.now()
        return "DEC-" + now.strftime("%Y%m%d%H%M%S")

    def charger_categories(self):
        """Charge les catégories depuis la base de données et met à jour le combobox."""
        if not self.conn or not self.cursor:
            messagebox.showwarning("Avertissement", "Connexion à la base de données non disponible.")
            return
        try:
            self.cursor.execute("SELECT idcc, categoriecompte FROM tb_categoriecompte ORDER BY categoriecompte")
            self.categories = {}
            category_names = []
            for row in self.cursor.fetchall():
                self.categories[row[1]] = row[0]
                category_names.append(row[1])
            self.combo_categorie.configure(values=category_names)
            if category_names:
                self.combo_categorie.set(category_names[0])
            else:
                self.combo_categorie.set("")
            print(f"DEBUG: {len(category_names)} catégories chargées")
        except psycopg2.Error as e:
            messagebox.showerror("Erreur SQL", f"Erreur lors du chargement des catégories : {e}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur inattendue : {e}")

    def get_type_operation(self):
        """Récupère l'ID numérique du type d'opération 'DEC'."""
        if not self.conn or not self.cursor:
            return None
        try:
            self.cursor.execute(
                "SELECT idtypeoperation FROM tb_typeoperation WHERE LOWER(typeoperation) = 'dec'")
            result = self.cursor.fetchone()
            return result[0] if result else None
        except psycopg2.Error as e:
            messagebox.showwarning("Avertissement",
                                   f"Impossible de récupérer l'ID du type d'opération : {e}.")
            return None

    def get_infos_societe(self):
        """Récupère les informations de la société depuis tb_infosociete"""
        if not self.conn or not self.cursor:
            return None
        try:
            self.cursor.execute("""
                SELECT nomsociete, adressesociete, contactsociete, villesociete 
                FROM tb_infosociete 
                LIMIT 1
            """)
            result = self.cursor.fetchone()
            if result:
                return {
                    'nom': result[0] or "Nom Société",
                    'adresse': result[1] or "Adresse",
                    'contact': result[2] or "Contact",
                    'ville': result[3] or "Ville"
                }
            return None
        except Exception as e:
            print(f"Erreur lors de la récupération des infos société: {e}")
            return None

    def generer_ticket_pdf(self, reference, categorie, montant, description, operateur):
        """Génère un ticket de caisse au format PDF 80mm"""
        try:
            infos_societe = self.get_infos_societe()
            if not infos_societe:
                infos_societe = {
                    'nom': "Nom Société",
                    'adresse': "Adresse",
                    'contact': "Contact",
                    'ville': "Ville"
                }

            largeur_ticket = 80 * mm
            hauteur_ticket = 200 * mm

            tickets_dir = os.path.join(os.path.expanduser("~"), "tickets_caisse")
            if not os.path.exists(tickets_dir):
                os.makedirs(tickets_dir)

            fichier_pdf = os.path.join(tickets_dir, f"ticket_{reference}.pdf")
            c = canvas.Canvas(fichier_pdf, pagesize=(largeur_ticket, hauteur_ticket))

            y = hauteur_ticket - 10 * mm
            x_centre = largeur_ticket / 2
            marge_gauche = 5 * mm

            c.setFont("Helvetica-Bold", 12)
            c.drawCentredString(x_centre, y, infos_societe['nom'])
            y -= 5 * mm

            c.setFont("Helvetica", 8)
            c.drawCentredString(x_centre, y, infos_societe['adresse'])
            y -= 4 * mm
            c.drawCentredString(x_centre, y, infos_societe['ville'])
            y -= 4 * mm
            c.drawCentredString(x_centre, y, f"Tél: {infos_societe['contact']}")
            y -= 7 * mm

            c.line(marge_gauche, y, largeur_ticket - marge_gauche, y)
            y -= 7 * mm

            c.setFont("Helvetica-Bold", 11)
            c.drawCentredString(x_centre, y, "TICKET DE DÉCAISSEMENT")
            y -= 7 * mm

            c.line(marge_gauche, y, largeur_ticket - marge_gauche, y)
            y -= 7 * mm

            c.setFont("Helvetica", 9)
            date_actuelle = datetime.now()
            c.drawString(marge_gauche, y, f"Date: {date_actuelle.strftime('%d/%m/%Y %H:%M')}")
            y -= 5 * mm
            c.drawString(marge_gauche, y, f"Réf: {reference}")
            y -= 5 * mm
            c.drawString(marge_gauche, y, f"Opérateur: {operateur}")
            y -= 7 * mm

            c.line(marge_gauche, y, largeur_ticket - marge_gauche, y)
            y -= 7 * mm

            c.setFont("Helvetica-Bold", 9)
            c.drawString(marge_gauche, y, "Catégorie:")
            y -= 4 * mm
            c.setFont("Helvetica", 9)
            c.drawString(marge_gauche + 3 * mm, y, categorie)
            y -= 7 * mm

            c.setFont("Helvetica-Bold", 9)
            c.drawString(marge_gauche, y, "Description:")
            y -= 4 * mm
            c.setFont("Helvetica", 8)

            max_largeur = largeur_ticket - 2 * marge_gauche - 3 * mm
            mots = description.split()
            ligne_actuelle = ""
            for mot in mots:
                test_ligne = ligne_actuelle + " " + mot if ligne_actuelle else mot
                largeur_texte = c.stringWidth(test_ligne, "Helvetica", 8)
                if largeur_texte <= max_largeur:
                    ligne_actuelle = test_ligne
                else:
                    c.drawString(marge_gauche + 3 * mm, y, ligne_actuelle)
                    y -= 4 * mm
                    ligne_actuelle = mot
            if ligne_actuelle:
                c.drawString(marge_gauche + 3 * mm, y, ligne_actuelle)
                y -= 7 * mm

            c.line(marge_gauche, y, largeur_ticket - marge_gauche, y)
            y -= 7 * mm

            c.setFont("Helvetica-Bold", 14)
            c.drawString(marge_gauche, y, "MONTANT:")
            montant_str = f"{montant:,.2f} Ar"
            c.drawRightString(largeur_ticket - marge_gauche, y, montant_str)
            y -= 10 * mm

            c.line(marge_gauche, y, largeur_ticket - marge_gauche, y)
            y -= 10 * mm

            c.setFont("Helvetica", 7)
            c.drawCentredString(x_centre, y, "Merci de votre confiance")
            y -= 4 * mm
            c.drawCentredString(x_centre, y, "Document non contractuel")

            c.save()
            return fichier_pdf

        except Exception as e:
            messagebox.showerror("Erreur PDF", f"Erreur lors de la génération du ticket: {e}")
            print(f"DEBUG: Erreur complète: {e}")
            return None

    def enregistrer(self):
        """Enregistre le décaissement avec l'utilisateur connecté."""
        if not self.conn or not self.cursor:
            return
        if not self.winfo_exists():
            return

        try:
            reference = self.generer_reference()
            categorie_nom = self.combo_categorie.get()
            idcc = self.categories.get(categorie_nom)
            mtpaye_str = self.entry_montant.get()
            observation = self.entry_description.get()

            if not idcc or not mtpaye_str or not observation:
                messagebox.showwarning("Attention", "Tous les champs doivent être remplis")
                return

            mtpaye = float(mtpaye_str.replace('.', ''))
            typeoperation_id = self.get_type_operation()
            datepmt = datetime.now()

            print(f"DEBUG: current_user = '{self.current_user}'")

            if getattr(self, 'current_user_id', None):
                iduser = self.current_user_id
                print(f"DEBUG: iduser depuis session = {iduser}")
            else:
                self.cursor.execute("SELECT iduser, username FROM tb_users")
                all_users = self.cursor.fetchall()
                print(f"DEBUG: Utilisateurs dans la base: {all_users}")

                self.cursor.execute(
                    "SELECT iduser FROM tb_users WHERE LOWER(TRIM(username)) = LOWER(TRIM(%s))",
                    (self.current_user,)
                )
                result = self.cursor.fetchone()
                if result:
                    iduser = result[0]
                    print(f"DEBUG: iduser trouvé = {iduser}")
                else:
                    print(f"ATTENTION: Utilisateur '{self.current_user}' introuvable")
                    self.cursor.execute("SELECT iduser FROM tb_users WHERE iduser = 1")
                    default_user = self.cursor.fetchone()
                    if default_user:
                        iduser = 1
                        print(f"DEBUG: Utilisation de l'utilisateur par défaut (ID=1)")
                    else:
                        messagebox.showerror("Erreur", "Aucun utilisateur trouvé dans la base de données")
                        return

            query = """
            INSERT INTO tb_decaissement (refpmt, idcc, mtpaye, observation, idtypeoperation, datepmt, iduser, idmode)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            print(f"DEBUG: Insertion avec iduser = {iduser}, idmode = 1 (Espèces)")
            self.cursor.execute(query, (reference, idcc, mtpaye, observation,
                                        typeoperation_id, datepmt, iduser, 1))
            self.conn.commit()
            self._finalized = True

            fichier_pdf = self.generer_ticket_pdf(
                reference=reference,
                categorie=categorie_nom,
                montant=mtpaye,
                description=observation,
                operateur=self.current_user
            )

            if fichier_pdf:
                messagebox.showinfo("Succès",
                    f"Décaissement enregistré avec succès!\n\n"
                    f"Référence: {reference}\n"
                    f"Ticket généré: {os.path.basename(fichier_pdf)}\n"
                    f"Emplacement: {os.path.dirname(fichier_pdf)}")
                try:
                    if sys.platform == "win32":
                        os.startfile(fichier_pdf)
                    elif sys.platform == "darwin":
                        os.system(f"open '{fichier_pdf}'")
                    else:
                        os.system(f"xdg-open '{fichier_pdf}'")
                except Exception as e:
                    print(f"Impossible d'ouvrir le PDF automatiquement: {e}")
                    try:
                        if sys.platform == "win32":
                            os.startfile(os.path.dirname(fichier_pdf))
                        elif sys.platform == "darwin":
                            os.system(f"open '{os.path.dirname(fichier_pdf)}'")
                        else:
                            os.system(f"xdg-open '{os.path.dirname(fichier_pdf)}'")
                    except:
                        pass
            else:
                messagebox.showinfo("Succès",
                    f"Décaissement enregistré avec succès!\n"
                    f"Référence: {reference}\n"
                    f"(Erreur lors de la génération du ticket)")

            # Réinitialiser
            self.vider_formulaire()
            self.charger_liste()
            self._finalized = False

        except ValueError:
            messagebox.showerror("Erreur", "Le montant doit être un nombre valide")
            self.conn.rollback()
        except Exception as e:
            messagebox.showerror("Erreur SQL", str(e))
            print(f"DEBUG: Exception complète: {e}")
            self.conn.rollback()

    def annuler(self):
        """Ferme la fenêtre."""
        self.destroy()

    def __del__(self):
        """Assure que la connexion à la base de données est fermée lorsque l'objet est détruit."""
        if hasattr(self, 'conn') and self.conn:
            try:
                self.cursor.close()
            except:
                pass
            try:
                self.conn.close()
            except:
                pass
            print("Database connection closed.")


if __name__ == "__main__":
    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")

    root_for_test = ctk.CTk()
    root_for_test.withdraw()

    def open_decaissement_page_test():
        decaissement_page = PageDecaissement(root_for_test)
        root_for_test.wait_window(decaissement_page)

    open_decaissement_page_test()
    root_for_test.destroy()