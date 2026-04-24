import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import os
import json
from resource_utils import get_config_path
from log_utils import AppLogger

from app_theme import Colors, Fonts, Layout, styled


class PageAutorisation(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        
        # Connexion à la base de données
        self.conn = self.connect_db()
        self.cursor = None
        
        if self.conn:
            self.cursor = self.conn.cursor()
        
        self.selected_fonction_id = None
        self.session_data = getattr(master, "session_data", None) or {}
        self._logger = AppLogger(conn=self.conn, session_data=self.session_data)
        self._ui_mode = None  # "wide" | "narrow"
        self._menu_id_by_designation: dict[str, int] = {}
        self._menu_vars_by_id: dict[int, ctk.BooleanVar] = {}
        self._menu_widgets_by_designation: dict[str, ctk.CTkCheckBox | ctk.CTkSwitch] = {}
        self._group_items_by_bloc: dict[str, list[str]] = {}
        self._all_menu_designations: list[str] = []

        self._build_menu_groups()
        self.setup_ui()
        self.configure_style()
        
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
                port=db_config['port']  
            )
            return conn
        except Exception as err:
            messagebox.showerror("Erreur de connexion", f"Détails : {err}")
            return None
    
    def configure_style(self):
        # Configuration du style pour les Treeview (liste des fonctions uniquement)
        style = ttk.Style()
        style.configure(
            "Treeview",
            background=Colors.BG_CARD,
            foreground=Colors.TEXT_PRIMARY,
            rowheight=Layout.ROW_H,
            fieldbackground=Colors.BG_CARD,
            borderwidth=0,
            font=(Fonts._family if getattr(Fonts, "_loaded", False) else "Segoe UI", 8),
        )
        style.configure(
            "Treeview.Heading",
            background=Colors.CLOUDS,
            foreground=Colors.TEXT_PRIMARY,
            font=(Fonts._family if getattr(Fonts, "_loaded", False) else "Segoe UI", 8, "bold"),
        )
        style.map("Treeview",
                 background=[('selected', Colors.SUCCESS)],
                 foreground=[('selected', Colors.TEXT_ON_DARK)])
                 
        if hasattr(self, 'fonction_tree'):
            self.fonction_tree.tag_configure('row_even', background=Colors.BG_CARD)
            self.fonction_tree.tag_configure('row_odd', background=Colors.BG_ROW_ALT)

    def _refresh_fonction_tree_alternating(self):
        for idx, item in enumerate(self.fonction_tree.get_children()):
            self.fonction_tree.item(item, tags=("row_even" if idx % 2 == 0 else "row_odd",))

    def setup_ui(self):
        self.pack(expand=True, fill="both", padx=20, pady=20)
        self.configure(fg_color=Colors.BG_PAGE)

        # Conteneur principal responsive (wide: 2 colonnes, narrow: 2 lignes)
        self.main = styled.frame(self, color="transparent")
        self.main.pack(fill="both", expand=True)
        self.main.bind("<Configure>", self._on_resize)

        # Grille stable (évite chevauchement)
        self.main.grid_rowconfigure(0, weight=1)
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_columnconfigure(1, weight=3)

        # Cards
        self.left_card = styled.card(self.main)
        self.right_card = styled.card(self.main)

        # ── Gauche : Fonctions
        header_left = styled.frame(self.left_card, color="transparent")
        header_left.pack(fill="x", padx=Layout.CARD_PADX, pady=(Layout.CARD_PADY_TOP, 8))
        styled.label_heading(header_left, text="Fonctions", size=14).pack(side="left")

        styled.label_muted(self.left_card, text="Rechercher", anchor="w").pack(
            fill="x", padx=Layout.CARD_PADX, pady=(0, 4)
        )
        self.search_fonction = styled.entry(self.left_card, placeholder="Tapez une fonction…", height=Layout.INPUT_H)
        self.search_fonction.pack(fill="x", padx=Layout.CARD_PADX, pady=(0, 12))
        self.search_fonction.bind("<KeyRelease>", self.filter_fonctions)

        list_frame = styled.frame(self.left_card, color="transparent")
        list_frame.pack(fill="both", expand=True, padx=Layout.CARD_PADX, pady=(0, Layout.CARD_PADY_BOT))
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        self.fonction_tree = ttk.Treeview(list_frame, columns=("ID", "Fonction"), show="headings")
        self.fonction_tree.heading("ID", text="ID")
        self.fonction_tree.heading("Fonction", text="Fonction")
        self.fonction_tree.column("ID", width=60, anchor="center")
        self.fonction_tree.column("Fonction", width=260, anchor="w")
        self.fonction_tree.grid(row=0, column=0, sticky="nsew")

        scrollbar_fonction = ttk.Scrollbar(list_frame, orient="vertical", command=self.fonction_tree.yview)
        scrollbar_fonction.grid(row=0, column=1, sticky="ns")
        self.fonction_tree.configure(yscrollcommand=scrollbar_fonction.set)

        # ── Droite : Autorisations groupées
        header_right = styled.frame(self.right_card, color="transparent")
        header_right.pack(fill="x", padx=Layout.CARD_PADX, pady=(Layout.CARD_PADY_TOP, 8))
        styled.label_heading(header_right, text="Autorisations des menus", size=14).pack(side="left")

        self._status_badge = styled.badge(header_right, text="Sélectionnez une fonction", variant="neutral")
        self._status_badge.pack(side="right")

        tools_row = styled.frame(self.right_card, color="transparent")
        tools_row.pack(fill="x", padx=Layout.CARD_PADX, pady=(0, 10))

        self.search_menu = styled.entry(tools_row, placeholder="Rechercher un menu…", height=Layout.INPUT_H)
        self.search_menu.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.search_menu.bind("<KeyRelease>", self.filter_menus)

        styled.button_primary(tools_row, text="Tout cocher", icon="✔", width=150,
                              height=Layout.BTN_H, command=lambda: self.toggle_all_checkboxes(True)).pack(side="left", padx=(0, 8))
        styled.button_secondary(tools_row, text="Tout décocher", icon="✕", width=160,
                                height=Layout.BTN_H, command=lambda: self.toggle_all_checkboxes(False)).pack(side="left")

        styled.divider(self.right_card).pack(fill="x", padx=Layout.CARD_PADX, pady=(0, 10))

        self.menus_scroll = styled.scrollable_frame(self.right_card)
        self.menus_scroll.pack(fill="both", expand=True, padx=Layout.CARD_PADX, pady=(0, 10))

        footer = styled.frame(self.right_card, color="transparent")
        footer.pack(fill="x", padx=Layout.CARD_PADX, pady=(0, Layout.CARD_PADY_BOT))

        self.save_button = styled.button_success(
            footer,
            text="Enregistrer",
            icon="💾",
            height=Layout.BTN_H_LG,
            command=self.save_autorisations,
        )
        self.save_button.pack(fill="x")
        self.save_button.configure(state="disabled")

        # Stockage des données non filtrées (fonctions uniquement)
        self.all_fonctions = []
        
        # Charger les données SEULEMENT si la connexion existe
        if self.conn and self.cursor:
            self.load_fonctions()
            self.fonction_tree.bind("<<TreeviewSelect>>", self.on_fonction_select)
            self._ensure_required_menus_exist()
            self._render_menu_groups()
        else:
            self.save_button.configure(state="disabled")

        # Layout initial
        self._apply_responsive_layout(force=True)

    # ──────────────────────────────────────────────────────────────────────
    # Responsive layout
    # ──────────────────────────────────────────────────────────────────────

    def _on_resize(self, event):
        self._apply_responsive_layout()

    def _apply_responsive_layout(self, force: bool = False):
        # Utiliser la largeur réelle du conteneur (plus fiable avec sidebar)
        width = self.main.winfo_width() or self.winfo_width() or 1000
        mode = "wide" if width >= 950 else "narrow"
        if (not force) and mode == self._ui_mode:
            return
        self._ui_mode = mode

        if mode == "wide":
            left_w = int(width * 0.25)
            left_w = max(300, min(left_w, 520))
            right_min = 420

            # Colonnes: gauche fixe-ish, droite flexible
            self.main.grid_rowconfigure(0, weight=1)
            self.main.grid_rowconfigure(1, weight=0)
            # Poids plus fort à droite pour éviter une "bande" étroite
            self.main.grid_columnconfigure(0, weight=1, minsize=left_w)
            self.main.grid_columnconfigure(1, weight=3, minsize=right_min)

            self.left_card.grid_propagate(False)
            self.left_card.configure(width=left_w)
            self.left_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
            self.right_card.grid_propagate(True)
            self.right_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
        else:
            # Une seule colonne, 2 lignes
            self.main.grid_columnconfigure(0, weight=1, minsize=0)
            self.main.grid_columnconfigure(1, weight=0, minsize=0)
            self.main.grid_rowconfigure(0, weight=0)
            self.main.grid_rowconfigure(1, weight=1)

            self.left_card.grid_propagate(True)
            self.left_card.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 12))
            self.right_card.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)

    # ──────────────────────────────────────────────────────────────────────
    # Menu grouping (from app_main.MENU_STRUCTURE)
    # ──────────────────────────────────────────────────────────────────────

    def _build_menu_groups(self):
        # Ordre et intitulés selon app_main.py (MENU_STRUCTURE)
        self.menu_groups = [
            {
                "key": "TABLEAU DE BORD",
                "title": "📊  TABLEAU DE BORD",
                "bloc_designation": "BLOC: TABLEAU DE BORD",
                "items": ["TABLEAU DE BORD"],
            },
            {
                "key": "CHAT INTERNE",
                "title": "💬  CHAT INTERNE",
                "bloc_designation": "BLOC: CHAT INTERNE",
                "items": ["CHAT INTERNE"],
            },
            {
                "key": "COMMERCIALE",
                "title": "🛒  COMMERCIALE",
                "bloc_designation": "BLOC: COMMERCIALE",
                "items": [
                    "Article Liste", "Client", "Fournisseur", "Magasin", "Ventes",
                    "Ventes par Dépôt", "Facturation", "Liste Facture", "Stock Article",
                    "Inventaire du Jour", "Stock Alerte", "Péremption d'article",
                    "Stock Livraison", "Livraison Client", "Mouvement d'article",
                    "Mouvement Stock", "Liste mouvements", "Suivi Commande",
                    "Prix d'article", "Prix de revient", "Marge Commerciale",
                ],
            },
            {
                "key": "PERSONNEL",
                "title": "👥  PERSONNEL",
                "bloc_designation": "BLOC: PERSONNEL",
                "items": [
                    "Liste Personnel", "Suivi de présence", "Gérer Personnels",
                    "Présence Personnel", "Absence", "Présence", "Avance 15e",
                    "Avance Spéciale", "Fonction", "Nouveau SB", "Etat de Salaire",
                    "Salaire Horaire", "Taux Horaire", "Paiement Salaire",
                ],
            },
            {
                "key": "TRESORERIE",
                "title": "💰  TRÉSORERIE",
                "bloc_designation": "BLOC: TRÉSORERIE",
                "items": [
                    "Caisse", "Facture Liste", "Fournisseur Dettes", "Banque",
                    "Ajout Banque", "Transfert Banque", "Transfert Caisse",
                    "Decaissement", "DecaissementBq", "Encaissement", "EncaissementBq",
                ],
            },
            {
                "key": "DATABASE",
                "title": "🗄️  BASE DE DONNÉES",
                "bloc_designation": "BLOC: BASE DE DONNÉES",
                "items": [
                    "Autorisation", "Evenements", "Sauvegarde", "Utilisateurs",
                    "Menu", "Base Liste", "Autorisation Admin", "Init DB",
                ],
            },
        ]

        self._all_menu_designations = []
        self._group_items_by_bloc = {}
        for g in self.menu_groups:
            self._all_menu_designations.append(g["bloc_designation"])
            self._all_menu_designations.extend(g["items"])
            self._group_items_by_bloc[g["bloc_designation"]] = list(g["items"])

    def _ensure_required_menus_exist(self):
        """
        Garantit que tous les items (y compris les blocs) existent dans tb_menu.
        On n'impose pas la colonne page (peut rester vide).
        """
        if not self.cursor:
            return

        self.cursor.execute("SELECT id, designationmenu FROM tb_menu")
        existing = {r[1]: r[0] for r in self.cursor.fetchall() if r and r[1]}

        missing = [d for d in self._all_menu_designations if d not in existing]
        if missing:
            for designation in missing:
                self.cursor.execute(
                    "INSERT INTO tb_menu (designationmenu, page) VALUES (%s, %s) RETURNING id",
                    (designation, ""),
                )
                new_id = self.cursor.fetchone()[0]
                existing[designation] = new_id
            self.conn.commit()

        self._menu_id_by_designation = existing

    def _render_menu_groups(self):
        # Clean
        for child in self.menus_scroll.winfo_children():
            child.destroy()

        self._menu_vars_by_id.clear()
        self._menu_widgets_by_designation.clear()

        for group in self.menu_groups:
            card = styled.card(self.menus_scroll)
            card.pack(fill="x", pady=(0, 12))

            head = styled.frame(card, color="transparent")
            head.pack(fill="x", padx=16, pady=(12, 6))

            styled.label_heading(head, text=group["title"], size=13).pack(side="left")

            # Switch "Afficher le bloc"
            bloc_id = self._menu_id_by_designation.get(group["bloc_designation"])
            bloc_var = ctk.BooleanVar(value=False)
            if bloc_id is not None:
                self._menu_vars_by_id[bloc_id] = bloc_var

            sw = styled.switch(
                head,
                text="Afficher le bloc",
                variable=bloc_var,
            )
            sw.pack(side="right")
            self._menu_widgets_by_designation[group["bloc_designation"]] = sw
            sw.configure(command=lambda b=group["bloc_designation"]: self._on_bloc_toggle(b))

            styled.divider(card).pack(fill="x", padx=16, pady=(0, 10))

            body = styled.frame(card, color="transparent")
            body.pack(fill="x", padx=16, pady=(0, 12))

            for designation in group["items"]:
                menu_id = self._menu_id_by_designation.get(designation)
                var = ctk.BooleanVar(value=False)
                if menu_id is not None:
                    self._menu_vars_by_id[menu_id] = var

                cb = styled.checkbox(body, text=designation, variable=var)
                cb.configure(font=Fonts.body(12))
                cb.pack(fill="x", pady=(0, 6), anchor="w")
                self._menu_widgets_by_designation[designation] = cb

        # Appliquer l'état disabled/enabled selon les blocs (utile au 1er rendu)
        self._apply_bloc_states()

    def _on_bloc_toggle(self, bloc_designation: str):
        """
        Si bloc décoché : désactive + décoche tous les sous-menus du groupe.
        Si bloc coché   : réactive les sous-menus (sans les auto-cocher).
        """
        bloc_id = self._menu_id_by_designation.get(bloc_designation)
        bloc_var = self._menu_vars_by_id.get(bloc_id) if bloc_id is not None else None
        bloc_enabled = bool(bloc_var.get()) if bloc_var is not None else False

        for designation in self._group_items_by_bloc.get(bloc_designation, []):
            menu_id = self._menu_id_by_designation.get(designation)
            var = self._menu_vars_by_id.get(menu_id) if menu_id is not None else None
            w = self._menu_widgets_by_designation.get(designation)
            if not w:
                continue

            if not bloc_enabled:
                if var is not None:
                    var.set(False)
                w.configure(state="disabled")
            else:
                w.configure(state="normal")

    def _apply_bloc_states(self):
        """Rejoue la logique bloc -> disabled/enabled pour tous les groupes."""
        for bloc in self._group_items_by_bloc.keys():
            self._on_bloc_toggle(bloc)

    def filter_fonctions(self, event=None):
        """Filtre la liste des fonctions selon le terme de recherche"""
        if not hasattr(self, 'all_fonctions'):
            return
            
        search_term = self.search_fonction.get().lower()
        self.fonction_tree.delete(*self.fonction_tree.get_children())
        
        for fonction in self.all_fonctions:
            if search_term in fonction[1].lower():
                self.fonction_tree.insert("", "end", values=fonction)
        self._refresh_fonction_tree_alternating()

    def filter_menus(self, event=None):
        """Filtre visuellement les menus (groupes + items)."""
        term = (self.search_menu.get() or "").strip().lower()
        if not term:
            self._render_menu_groups()
            self._reload_authorizations_into_vars()
            return

        # Re-render puis masquer ce qui ne matche pas (simple et fiable)
        self._render_menu_groups()
        self._reload_authorizations_into_vars()

        for group in self.menu_groups:
            # Les widgets sont dans une card; on masque item par item
            for designation in [group["bloc_designation"]] + group["items"]:
                w = self._menu_widgets_by_designation.get(designation)
                if not w:
                    continue
                if term in designation.lower() or term in group["title"].lower():
                    continue
                w.pack_forget()

    def toggle_all_checkboxes(self, state):
        """Coche ou décoche toutes les autorisations"""
        for var in self._menu_vars_by_id.values():
            try:
                var.set(bool(state))
            except Exception:
                pass

    def load_fonctions(self):
        """Charge la liste des fonctions depuis la base de données"""
        if not self.cursor:
            messagebox.showerror("Erreur", "Pas de connexion à la base de données.")
            return
            
        try:
            self.cursor.execute("SELECT idfonction, designationfonction FROM tb_fonction ORDER BY designationfonction")
            self.all_fonctions = self.cursor.fetchall()
            
            # Vider le treeview
            for item in self.fonction_tree.get_children():
                self.fonction_tree.delete(item)
                
            # Ajouter les nouvelles données
            for row in self.all_fonctions:
                self.fonction_tree.insert("", "end", values=row)
            self._refresh_fonction_tree_alternating()
                
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des fonctions : {err}")

    def load_menus(self, fonction_id):
        """Charge les autorisations pour la fonction sélectionnée dans les variables UI."""
        self.selected_fonction_id = fonction_id
        self._reload_authorizations_into_vars()

    def _reload_authorizations_into_vars(self):
        if not self.cursor or not self.selected_fonction_id:
            for var in self._menu_vars_by_id.values():
                var.set(False)
            return

        try:
            self.cursor.execute(
                "SELECT idmenu FROM tb_autorisation WHERE idfonction = %s",
                (self.selected_fonction_id,),
            )
            authorized_ids = {r[0] for r in self.cursor.fetchall() if r and r[0] is not None}
        except Exception:
            authorized_ids = set()

        for menu_id, var in self._menu_vars_by_id.items():
            var.set(menu_id in authorized_ids)
        # Si un bloc est désactivé, on force ses enfants en disabled
        self._apply_bloc_states()

    def on_fonction_select(self, event):
        """Gestionnaire de sélection d'une fonction"""
        selected = self.fonction_tree.selection()
        if not selected:
            return
            
        item = self.fonction_tree.item(selected[0])
        self.selected_fonction_id = item['values'][0]
        self.load_menus(self.selected_fonction_id)
        # Réinitialiser la recherche
        self.search_menu.delete(0, "end")
        self._status_badge.configure(text=f"Fonction ID: {self.selected_fonction_id}")
        self.save_button.configure(state="normal")

    def save_autorisations(self):
        """Sauvegarde les autorisations en base de données"""
        if not self.selected_fonction_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner une fonction.")
            return
            
        if not self.cursor:
            messagebox.showerror("Erreur", "Pas de connexion à la base de données.")
            return
            
        try:
            # Supprimer les autorisations existantes pour cette fonction
            self.cursor.execute("DELETE FROM tb_autorisation WHERE idfonction = %s", 
                              (self.selected_fonction_id,))
            
            # Insérer les nouvelles autorisations (menus requis + blocs)
            authorized = 0
            for menu_id, var in self._menu_vars_by_id.items():
                if var.get():
                    authorized += 1
                    self.cursor.execute(
                        "INSERT INTO tb_autorisation (idfonction, idmenu) VALUES (%s, %s)",
                        (self.selected_fonction_id, menu_id),
                    )
            
            self.conn.commit()
            messagebox.showinfo("Succès", "Autorisations enregistrées avec succès!")
            try:
                self._logger.log(
                    action="Modification autorisations",
                    element=f"idfonction={self.selected_fonction_id}",
                    details=f"Autorisations menus enregistrées, autorisées={authorized}",
                    value=f"autorisees={authorized}",
                )
            except Exception:
                pass
            
        except psycopg2.Error as err:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement : {err}")

    def __del__(self):
        """Destructeur pour fermer proprement les connexions"""
        if hasattr(self, 'cursor') and self.cursor:
            self.cursor.close()
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

# Pour tester la page individuellement
if __name__ == "__main__":
    from app_theme import init_theme, Theme
    init_theme()
    
    app = ctk.CTk()
    app.title("Gestion des Autorisations")
    app.geometry("1000x600")
    Theme.apply(app)

    page = PageAutorisation(app)
    app.mainloop()
