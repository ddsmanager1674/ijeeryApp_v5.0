import json
import os
import queue
import threading
from dataclasses import dataclass

import customtkinter as ctk
import psycopg2
from tkinter import messagebox

from app_theme import Colors, Fonts, Layout, styled
from log_utils import AppLogger
from resource_utils import get_config_path


@dataclass(frozen=True)
class MenuGroup:
    title: str
    bloc: str
    items: tuple[str, ...]


class PageAutorisation(ctk.CTkFrame):
    """
    Page simple et stable :
    - ne se pack/grid jamais elle-meme, le conteneur parent s'en charge ;
    - aucune requete lente dans le thread Tk ;
    - aucun changement de layout apres affichage.
    """

    MENU_GROUPS = (
        MenuGroup("TABLEAU DE BORD", "BLOC: TABLEAU DE BORD", ("TABLEAU DE BORD",)),
        MenuGroup("CHAT INTERNE", "BLOC: CHAT INTERNE", ("CHAT INTERNE",)),
        MenuGroup(
            "COMMERCIALE",
            "BLOC: COMMERCIALE",
            (
                "Article Liste", "Client", "Fournisseur", "Magasin", "Ventes",
                "Ventes par Dépôt", "Facturation", "Liste Facture", "Stock Article",
                "Inventaire du Jour", "Stock Alerte", "Péremption d'article",
                "Stock Livraison", "Livraison Client", "Mouvement d'article",
                "Mouvement Stock", "Liste mouvements", "Suivi Commande",
                "Prix d'article", "Prix de revient", "Marge Commerciale",
            ),
        ),
        MenuGroup(
            "PERSONNEL",
            "BLOC: PERSONNEL",
            (
                "Liste Personnel", "Suivi de présence", "Gérer Personnels",
                "Présence Personnel", "Absence", "Présence", "Avance 15e",
                "Avance Spéciale", "Nouveau SB", "Etat de Salaire",
                "Salaire Horaire", "Taux Horaire", "Paiement Salaire",
            ),
        ),
        MenuGroup(
            "TRÉSORERIE",
            "BLOC: TRÉSORERIE",
            (
                "Caisse", "Facture Liste", "Fournisseur Dettes", "Banque",
                "Ajout Banque", "Transfert Banque", "Transfert Caisse",
                "Decaissement", "DecaissementBq", "Encaissement", "EncaissementBq",
            ),
        ),
        MenuGroup(
            "BASE DE DONNÉES",
            "BLOC: BASE DE DONNÉES",
            (
                "Autorisation", "Evenements", "Sauvegarde", "Fonction", "Utilisateurs",
                "Paramètres", "Menu", "Base Liste", "Autorisation Admin", "Init DB",
            ),
        ),
    )

    def __init__(self, master):
        super().__init__(master, fg_color=Colors.BG_PAGE, corner_radius=0)

        self.session_data = getattr(master, "session_data", None) or {}
        self._queue: queue.Queue = queue.Queue()
        self._save_queue: queue.Queue = queue.Queue()

        self.selected_fonction_id: int | None = None
        self._fonctions: list[tuple[int, str]] = []
        self._menu_id_by_name: dict[str, int] = {}
        self._authorized_by_fonction: dict[int, set[int]] = {}

        self._fonction_buttons: dict[int, ctk.CTkButton] = {}
        self._group_cards: dict[str, ctk.CTkFrame] = {}
        self._item_rows: dict[str, ctk.CTkFrame] = {}
        self._vars_by_menu_id: dict[int, ctk.BooleanVar] = {}
        self._widgets_by_name: dict[str, ctk.CTkBaseClass] = {}
        self._switches_by_bloc: dict[str, ctk.CTkSwitch] = {}
        self._checkboxes_by_item: dict[str, ctk.CTkCheckBox] = {}

        self._build_ui()
        self._set_ready(False)
        self.after(50, self._start_loading)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0, minsize=310)
        self.grid_columnconfigure(1, weight=1, minsize=520)

        self.left_panel = styled.card(self, width=310)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(16, 8), pady=16)
        self.left_panel.grid_propagate(False)

        self.right_panel = styled.card(self)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 16), pady=16)

        self._build_left_panel()
        self._build_right_panel()

    def _build_left_panel(self):
        styled.label_heading(self.left_panel, text="Fonctions", size=15).pack(
            anchor="w", padx=16, pady=(16, 8)
        )

        self.search_fonction = styled.entry(
            self.left_panel,
            placeholder="Rechercher une fonction",
            height=Layout.INPUT_H,
        )
        self.search_fonction.pack(fill="x", padx=16, pady=(0, 12))
        self.search_fonction.bind("<KeyRelease>", lambda _e: self._render_fonctions())

        self.fonctions_scroll = styled.scrollable_frame(self.left_panel)
        self.fonctions_scroll.pack(fill="both", expand=True, padx=12, pady=(0, 16))

    def _build_right_panel(self):
        header = styled.frame(self.right_panel, color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 8))
        styled.label_heading(header, text="Autorisations des menus", size=15).pack(side="left")
        self.status_badge = styled.badge(header, text="Chargement", variant="neutral")
        self.status_badge.pack(side="right")

        toolbar = styled.frame(self.right_panel, color="transparent")
        toolbar.pack(fill="x", padx=16, pady=(0, 12))

        self.search_menu = styled.entry(
            toolbar,
            placeholder="Rechercher un menu",
            height=Layout.INPUT_H,
        )
        self.search_menu.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.search_menu.bind("<KeyRelease>", lambda _e: self._filter_menus())

        self.btn_all = styled.button_primary(
            toolbar,
            text="Tout cocher",
            width=130,
            height=Layout.BTN_H,
            command=lambda: self._set_all(True),
        )
        self.btn_all.pack(side="left", padx=(0, 8))

        self.btn_none = styled.button_secondary(
            toolbar,
            text="Tout décocher",
            width=145,
            height=Layout.BTN_H,
            command=lambda: self._set_all(False),
        )
        self.btn_none.pack(side="left")

        styled.divider(self.right_panel).pack(fill="x", padx=16, pady=(0, 12))

        self.menus_scroll = styled.scrollable_frame(self.right_panel)
        self.menus_scroll.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.save_button = styled.button_success(
            self.right_panel,
            text="Enregistrer",
            height=Layout.BTN_H_LG,
            command=self._save_current,
        )
        self.save_button.pack(fill="x", padx=16, pady=(0, 16))

        self._show_placeholder("Chargement des autorisations...")

    def _show_placeholder(self, text: str):
        for child in self.menus_scroll.winfo_children():
            child.destroy()

        placeholder = styled.frame(self.menus_scroll, color="transparent")
        placeholder.pack(fill="both", expand=True, pady=40)
        styled.label_muted(placeholder, text=text, size=12).pack()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _start_loading(self):
        threading.Thread(target=self._load_data_worker, daemon=True).start()
        self.after(80, self._poll_load_queue)

    def _load_data_worker(self):
        conn = None
        try:
            conn = self._connect_db()
            with conn.cursor() as cur:
                menu_ids = self._ensure_required_menus(cur)

                cur.execute(
                    "SELECT idfonction, designationfonction "
                    "FROM tb_fonction ORDER BY designationfonction"
                )
                fonctions = [(int(row[0]), str(row[1])) for row in cur.fetchall()]

                cur.execute("SELECT idfonction, idmenu FROM tb_autorisation")
                auth: dict[int, set[int]] = {}
                for idfonction, idmenu in cur.fetchall():
                    if idfonction is not None and idmenu is not None:
                        auth.setdefault(int(idfonction), set()).add(int(idmenu))

            self._queue.put(("ok", fonctions, menu_ids, auth))
        except Exception as exc:
            self._queue.put(("error", str(exc)))
        finally:
            if conn:
                conn.close()

    def _poll_load_queue(self):
        try:
            result = self._queue.get_nowait()
        except queue.Empty:
            self.after(80, self._poll_load_queue)
            return

        if result[0] == "error":
            err = result[1] if len(result) > 1 else "Erreur inconnue"
            try:
                print(f"[Autorisation] Chargement échoué: {err}")
            except Exception:
                pass
            self.status_badge.configure(text="Erreur")
            self._show_placeholder(f"Impossible de charger les autorisations.\n{err}")
            return

        _, fonctions, menu_ids, auth = result
        self._fonctions = fonctions
        self._menu_id_by_name = menu_ids
        self._authorized_by_fonction = auth

        self._render_fonctions()
        self._render_menus()
        self.status_badge.configure(text="Sélectionnez une fonction")
        self._set_ready(False)

    def _connect_db(self):
        config_path = get_config_path("config.json")
        if not os.path.exists(config_path):
            config_path = "config.json"
        if not os.path.exists(config_path):
            raise FileNotFoundError("Fichier config.json manquant.")

        with open(config_path, "r", encoding="utf-8") as f:
            db = json.load(f)["database"]

        return psycopg2.connect(
            host=db["host"],
            user=db["user"],
            password=db["password"],
            database=db["database"],
            port=db["port"],
            connect_timeout=5,
        )

    def _required_menu_names(self):
        names = []
        for group in self.MENU_GROUPS:
            names.append(group.bloc)
            names.extend(group.items)
        return names

    def _ensure_required_menus(self, cur):
        self._sync_sequence(cur, "tb_menu_id_seq", "tb_menu", "id")
        cur.execute("SELECT id, designationmenu FROM tb_menu")
        existing = {str(name): int(menu_id) for menu_id, name in cur.fetchall() if name}

        for name in self._required_menu_names():
            if name in existing:
                continue
            cur.execute(
                "INSERT INTO tb_menu (designationmenu, page) VALUES (%s, %s) RETURNING id",
                (name, ""),
            )
            existing[name] = int(cur.fetchone()[0])

        cur.connection.commit()
        return existing

    def _sync_sequence(self, cur, seq_name: str, table: str, column: str):
        """
        Après une restauration, les séquences peuvent être désynchronisées (duplicate key).
        On aligne la séquence sur MAX(column)+1 sans casser les données.
        """
        cur.execute(
            f"""
            SELECT pg_catalog.setval(
                'public.{seq_name}',
                COALESCE((SELECT MAX({column}) FROM public.{table}), 0) + 1,
                false
            )
            """
        )

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def _render_fonctions(self):
        for child in self.fonctions_scroll.winfo_children():
            child.destroy()
        self._fonction_buttons.clear()

        term = (self.search_fonction.get() or "").strip().lower()
        rows = [f for f in self._fonctions if not term or term in f[1].lower()]

        if not rows:
            styled.label_muted(self.fonctions_scroll, text="Aucune fonction").pack(pady=16)
            return

        for fonction_id, designation in rows:
            button = ctk.CTkButton(
                self.fonctions_scroll,
                text=designation,
                anchor="w",
                height=34,
                corner_radius=6,
                fg_color=Colors.BG_CARD,
                hover_color=Colors.CLOUDS,
                text_color=Colors.TEXT_PRIMARY,
                font=Fonts.body(12),
                command=lambda fid=fonction_id: self._select_fonction(fid),
            )
            button.pack(fill="x", padx=4, pady=3)
            self._fonction_buttons[fonction_id] = button

        self._refresh_selected_function_style()

    def _render_menus(self):
        for child in self.menus_scroll.winfo_children():
            child.destroy()

        self._group_cards.clear()
        self._item_rows.clear()
        self._vars_by_menu_id.clear()
        self._widgets_by_name.clear()
        self._switches_by_bloc.clear()
        self._checkboxes_by_item.clear()

        for group in self.MENU_GROUPS:
            card = styled.card(self.menus_scroll)
            card.pack(fill="x", padx=4, pady=(0, 10))
            self._group_cards[group.bloc] = card

            head = styled.frame(card, color="transparent")
            head.pack(fill="x", padx=14, pady=(12, 8))
            styled.label_heading(head, text=group.title, size=13).pack(side="left")

            bloc_var = ctk.BooleanVar(value=False)
            bloc_id = self._menu_id_by_name.get(group.bloc)
            if bloc_id is not None:
                self._vars_by_menu_id[bloc_id] = bloc_var

            switch = styled.switch(
                head,
                text="Afficher le bloc",
                variable=bloc_var,
                command=lambda bloc=group.bloc: self._apply_group_state(bloc),
            )
            switch.pack(side="right")
            self._widgets_by_name[group.bloc] = switch
            self._switches_by_bloc[group.bloc] = switch

            styled.divider(card).pack(fill="x", padx=14, pady=(0, 10))

            body = styled.frame(card, color="transparent")
            body.pack(fill="x", padx=14, pady=(0, 10))

            for item in group.items:
                row = styled.frame(body, color="transparent")
                row.pack(fill="x", pady=3)
                self._item_rows[item] = row

                item_var = ctk.BooleanVar(value=False)
                item_id = self._menu_id_by_name.get(item)
                if item_id is not None:
                    self._vars_by_menu_id[item_id] = item_var

                checkbox = styled.checkbox(row, text=item, variable=item_var)
                checkbox.pack(anchor="w", fill="x")
                self._widgets_by_name[item] = checkbox
                self._checkboxes_by_item[item] = checkbox

        self._set_ready(False)

    def _filter_menus(self):
        term = (self.search_menu.get() or "").strip().lower()
        for group in self.MENU_GROUPS:
            group_match = term and term in group.title.lower()
            visible = 0
            for item in group.items:
                row = self._item_rows.get(item)
                if not row:
                    continue
                match = not term or group_match or term in item.lower()
                if match:
                    row.pack(fill="x", pady=3)
                    visible += 1
                else:
                    row.pack_forget()

            card = self._group_cards.get(group.bloc)
            if not card:
                continue
            if not term or group_match or visible:
                card.pack(fill="x", padx=4, pady=(0, 10))
            else:
                card.pack_forget()

    # ------------------------------------------------------------------
    # Interactions
    # ------------------------------------------------------------------

    def _select_fonction(self, fonction_id: int):
        self.selected_fonction_id = fonction_id
        selected_name = next((name for fid, name in self._fonctions if fid == fonction_id), "")
        self.status_badge.configure(text=selected_name or "Fonction sélectionnée")
        self.search_menu.delete(0, "end")
        self._filter_menus()
        self._set_ready(True)
        self._load_authorizations_into_vars()
        self._refresh_selected_function_style()

    def _refresh_selected_function_style(self):
        for fonction_id, button in self._fonction_buttons.items():
            active = fonction_id == self.selected_fonction_id
            button.configure(
                fg_color=Colors.PRIMARY if active else Colors.BG_CARD,
                text_color=Colors.TEXT_ON_DARK if active else Colors.TEXT_PRIMARY,
            )

    def _load_authorizations_into_vars(self):
        authorized = set(self._authorized_by_fonction.get(self.selected_fonction_id or 0, set()))

        fonction_id = self._menu_id_by_name.get("Fonction")
        database_bloc_id = self._menu_id_by_name.get("BLOC: BASE DE DONNÉES")
        if fonction_id in authorized and database_bloc_id is not None:
            authorized.add(database_bloc_id)

        for menu_id, var in self._vars_by_menu_id.items():
            var.set(menu_id in authorized)

        for group in self.MENU_GROUPS:
            self._apply_group_state(group.bloc)

    def _apply_group_state(self, bloc_name: str):
        bloc_id = self._menu_id_by_name.get(bloc_name)
        bloc_var = self._vars_by_menu_id.get(bloc_id) if bloc_id is not None else None
        enabled = bool(bloc_var and bloc_var.get())

        group = next((g for g in self.MENU_GROUPS if g.bloc == bloc_name), None)
        if not group:
            return

        for item in group.items:
            item_id = self._menu_id_by_name.get(item)
            item_var = self._vars_by_menu_id.get(item_id) if item_id is not None else None
            widget = self._checkboxes_by_item.get(item)
            if not widget:
                continue
            if enabled:
                widget.configure(state="normal")
            else:
                if item_var:
                    item_var.set(False)
                widget.configure(state="disabled")

    def _set_all(self, checked: bool):
        for var in self._vars_by_menu_id.values():
            var.set(checked)
        for group in self.MENU_GROUPS:
            self._apply_group_state(group.bloc)

    def _set_ready(self, ready: bool):
        state = "normal" if ready else "disabled"
        self.search_menu.configure(state=state)
        self.btn_all.configure(state=state)
        self.btn_none.configure(state=state)
        self.save_button.configure(state=state)

        if not ready:
            for widget in list(self._switches_by_bloc.values()) + list(self._checkboxes_by_item.values()):
                try:
                    widget.configure(state="disabled")
                except Exception:
                    pass
            return

        for group in self.MENU_GROUPS:
            switch = self._switches_by_bloc.get(group.bloc)
            if switch:
                switch.configure(state="normal")
            self._apply_group_state(group.bloc)

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _save_current(self):
        if not self.selected_fonction_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner une fonction.")
            return

        selected_ids = {menu_id for menu_id, var in self._vars_by_menu_id.items() if var.get()}
        fonction_id = self.selected_fonction_id

        self.save_button.configure(state="disabled", text="Enregistrement...")
        threading.Thread(
            target=self._save_worker,
            args=(fonction_id, selected_ids),
            daemon=True,
        ).start()
        self.after(80, self._poll_save_queue)

    def _save_worker(self, fonction_id: int, selected_ids: set[int]):
        conn = None
        try:
            conn = self._connect_db()
            with conn.cursor() as cur:
                self._sync_sequence(cur, "tb_autorisation_id_seq", "tb_autorisation", "id")
                cur.execute("DELETE FROM tb_autorisation WHERE idfonction = %s", (fonction_id,))
                for menu_id in selected_ids:
                    cur.execute(
                        "INSERT INTO tb_autorisation (idfonction, idmenu) VALUES (%s, %s)",
                        (fonction_id, menu_id),
                    )
            conn.commit()

            AppLogger(conn=conn, session_data=self.session_data).log(
                action="Modification autorisations",
                element=f"idfonction={fonction_id}",
                details=f"Autorisations menus enregistrées, autorisées={len(selected_ids)}",
                value=f"autorisees={len(selected_ids)}",
            )
            self._save_queue.put(("ok", fonction_id, selected_ids))
        except Exception as exc:
            if conn:
                conn.rollback()
            self._save_queue.put(("error", str(exc)))
        finally:
            if conn:
                conn.close()

    def _poll_save_queue(self):
        try:
            result = self._save_queue.get_nowait()
        except queue.Empty:
            self.after(80, self._poll_save_queue)
            return

        self.save_button.configure(text="Enregistrer")
        if result[0] == "ok":
            _, fonction_id, selected_ids = result
            self._authorized_by_fonction[fonction_id] = set(selected_ids)
            self._set_ready(True)
            messagebox.showinfo("Succès", "Autorisations enregistrées avec succès.")
        else:
            self._set_ready(True)
            messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement : {result[1]}")


if __name__ == "__main__":
    from app_theme import Theme, init_theme

    init_theme()
    app = ctk.CTk()
    app.title("Gestion des Autorisations")
    app.geometry("1100x650")
    Theme.apply(app)
    PageAutorisation(app).pack(fill="both", expand=True)
    app.mainloop()
