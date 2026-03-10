# -*- coding: utf-8 -*-
"""
PagePersonnelAjout — Liste compacte + formulaire en modal
Thème : iJeery (app_theme.py)
"""

import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import json
from datetime import datetime
from resource_utils import get_config_path
from app_theme import Colors, Fonts, styled, Layout


class ModalPersonnel(ctk.CTkToplevel):
    """Fenêtre modale pour ajout / modification d'un personnel."""

    def __init__(self, master, on_save, db_conn_fn, mode="ajout", personnel_data=None):
        super().__init__(master)

        self._on_save    = on_save
        self._connect_db = db_conn_fn
        self.mode        = mode          # "ajout" | "modification"
        self.personnel   = personnel_data  # dict avec les valeurs existantes

        self.fonction_dict = {}

        # ── Fenêtre ──────────────────────────────────────────────────────────
        titre = "Nouveau personnel" if mode == "ajout" else "Modifier le personnel"
        self.title(titre)
        self.geometry("560x460")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_PAGE)
        self.grab_set()           # modal bloquant
        self.focus_set()

        self._build_ui()
        self._load_fonctions()

        if mode == "modification" and personnel_data:
            self._prefill()

    # ── Construction de l'interface ──────────────────────────────────────────

    def _build_ui(self):
        # En-tête coloré
        header = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT,
                              corner_radius=0, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        icon = "➕" if self.mode == "ajout" else "✏️"
        titre = "Nouveau personnel" if self.mode == "ajout" else "Modifier le personnel"
        ctk.CTkLabel(
            header, text=f"  {icon}  {titre}",
            font=Fonts.heading(15), text_color=Colors.TEXT_ON_DARK,
            anchor="w"
        ).pack(side="left", padx=Layout.CARD_PADX, pady=0, fill="y")

        # Corps
        body = ctk.CTkFrame(self, fg_color=Colors.BG_CARD,
                            corner_radius=0)
        body.pack(fill="both", expand=True,
                  padx=Layout.CARD_PADX, pady=Layout.SECTION_GAP)

        # ── Grille 2 colonnes ─────────────────────────────────────────────
        body.grid_columnconfigure((1, 3), weight=1)

        def lbl(row, col, text, required=False):
            txt = f"{text} *" if required else text
            color = Colors.DANGER if required else Colors.TEXT_SECONDARY
            ctk.CTkLabel(body, text=txt, font=Fonts.label(11),
                         text_color=color, anchor="w"
                         ).grid(row=row, column=col, padx=(0, 6), pady=4, sticky="w")

        # Ligne 0 — Matricule / Nom *
        lbl(0, 0, "Matricule")
        self.entry_matricule = styled.entry(body, height=Layout.INPUT_H_SM)
        self.entry_matricule.grid(row=0, column=1, padx=(0, 16), pady=4, sticky="ew")

        lbl(0, 2, "Nom", required=True)
        self.entry_nom = styled.entry(body, placeholder="Nom de famille",
                                      height=Layout.INPUT_H_SM)
        self.entry_nom.grid(row=0, column=3, pady=4, sticky="ew")

        # Ligne 1 — Prénom / Sexe *
        lbl(1, 0, "Prénom")
        self.entry_prenom = styled.entry(body, placeholder="Prénom",
                                         height=Layout.INPUT_H_SM)
        self.entry_prenom.grid(row=1, column=1, padx=(0, 16), pady=4, sticky="ew")

        lbl(1, 2, "Sexe", required=True)
        self.combo_sexe = ctk.CTkComboBox(
            body, values=["M", "F"], state="readonly",
            height=Layout.INPUT_H_SM,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            button_color=Colors.PRIMARY, dropdown_fg_color=Colors.BG_CARD,
            font=Fonts.body(12)
        )
        self.combo_sexe.set("M")
        self.combo_sexe.grid(row=1, column=3, pady=4, sticky="ew")

        # Ligne 2 — Fonction * (pleine largeur)
        lbl(2, 0, "Fonction", required=True)
        self.combo_fonction = ctk.CTkComboBox(
            body, state="readonly",
            height=Layout.INPUT_H_SM,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            button_color=Colors.PRIMARY, dropdown_fg_color=Colors.BG_CARD,
            font=Fonts.body(12)
        )
        self.combo_fonction.grid(row=2, column=1, columnspan=3,
                                  padx=(0, 0), pady=4, sticky="ew")

        # Ligne 3 — Adresse / CIN
        lbl(3, 0, "Adresse")
        self.entry_adresse = styled.entry(body, placeholder="Adresse",
                                           height=Layout.INPUT_H_SM)
        self.entry_adresse.grid(row=3, column=1, padx=(0, 16), pady=4, sticky="ew")

        lbl(3, 2, "CIN")
        self.entry_cin = styled.entry(body, placeholder="N° CIN",
                                       height=Layout.INPUT_H_SM)
        self.entry_cin.grid(row=3, column=3, pady=4, sticky="ew")

        # Ligne 4 — Contact
        lbl(4, 0, "Contact")
        self.entry_contact = styled.entry(body, placeholder="Téléphone / Email",
                                           height=Layout.INPUT_H_SM)
        self.entry_contact.grid(row=4, column=1, pady=4, sticky="ew")

        # Note champs obligatoires
        ctk.CTkLabel(body, text="* Champs obligatoires",
                     font=Fonts.small(10),
                     text_color=Colors.TEXT_MUTED
                     ).grid(row=5, column=0, columnspan=4,
                            pady=(8, 0), sticky="w")

        # Séparateur + boutons
        styled.divider(body).grid(row=6, column=0, columnspan=4,
                                   pady=(10, 8), sticky="ew")

        btn_row = styled.frame(body)
        btn_row.grid(row=7, column=0, columnspan=4, sticky="e")

        styled.button_secondary(btn_row, text="Annuler", icon="✕",
                                  command=self.destroy, width=110
                                  ).pack(side="left", padx=(0, 8))

        lbl_save = "Enregistrer" if self.mode == "ajout" else "Mettre à jour"
        icon_save = "💾" if self.mode == "ajout" else "✔"
        styled.button_success(btn_row, text=lbl_save, icon=icon_save,
                               command=self._save, width=140
                               ).pack(side="left")

    # ── Données ──────────────────────────────────────────────────────────────

    def _load_fonctions(self):
        conn = self._connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT idfonction, designationfonction FROM tb_fonction "
                "WHERE deleted=0 ORDER BY designationfonction"
            )
            rows = cur.fetchall()
            self.fonction_dict = {r[1]: r[0] for r in rows}
            self.combo_fonction.configure(values=list(self.fonction_dict.keys()))
            if rows:
                self.combo_fonction.set(rows[0][1])
        finally:
            conn.close()

    def _prefill(self):
        p = self.personnel
        self.entry_matricule.configure(state="normal")
        self.entry_matricule.delete(0, "end")
        self.entry_matricule.insert(0, p.get("matricule", ""))
        self.entry_matricule.configure(state="readonly")

        self.entry_nom.delete(0, "end")
        self.entry_nom.insert(0, p.get("nom", ""))

        self.entry_prenom.delete(0, "end")
        self.entry_prenom.insert(0, p.get("prenom", "") or "")

        self.combo_sexe.set(p.get("sexe", "M") or "M")
        self.combo_fonction.set(p.get("fonction", ""))

        self.entry_adresse.delete(0, "end")
        self.entry_adresse.insert(0, p.get("adresse", "") or "")

        self.entry_cin.delete(0, "end")
        self.entry_cin.insert(0, p.get("cin", "") or "")

        self.entry_contact.delete(0, "end")
        self.entry_contact.insert(0, p.get("contact", "") or "")

    def _save(self):
        nom      = self.entry_nom.get().strip()
        sexe     = self.combo_sexe.get().strip()
        fonction = self.combo_fonction.get().strip()

        if not nom or not sexe or not fonction:
            messagebox.showwarning(
                "Champs obligatoires",
                "Veuillez remplir : Nom, Sexe et Fonction.",
                parent=self
            )
            return

        data = {
            "matricule": self.entry_matricule.get().strip() or None,
            "nom":       nom,
            "prenom":    self.entry_prenom.get().strip() or None,
            "adresse":   self.entry_adresse.get().strip() or None,
            "cin":       self.entry_cin.get().strip() or None,
            "contact":   self.entry_contact.get().strip() or None,
            "sexe":      sexe,
            "idfonction": self.fonction_dict.get(fonction),
        }

        conn = self._connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            if self.mode == "ajout":
                cur.execute(
                    """INSERT INTO tb_personnel
                       (matricule, nom, prenom, datenaissance, adresse, cin,
                        contact, sexe, idfonction, deleted)
                       VALUES (%s,%s,%s,NULL,%s,%s,%s,%s,%s,0)""",
                    (data["matricule"], data["nom"], data["prenom"],
                     data["adresse"], data["cin"], data["contact"],
                     data["sexe"], data["idfonction"])
                )
                msg = "Personnel ajouté avec succès !"
            else:
                cur.execute(
                    """UPDATE tb_personnel SET
                       matricule=%s, nom=%s, prenom=%s, adresse=%s, cin=%s,
                       contact=%s, sexe=%s, idfonction=%s
                       WHERE id=%s""",
                    (data["matricule"], data["nom"], data["prenom"],
                     data["adresse"], data["cin"], data["contact"],
                     data["sexe"], data["idfonction"],
                     self.personnel["id"])
                )
                msg = "Personnel mis à jour !"
            conn.commit()
            messagebox.showinfo("Succès", msg, parent=self)
            self._on_save()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erreur base de données", str(e), parent=self)
        finally:
            conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# PAGE PRINCIPALE
# ─────────────────────────────────────────────────────────────────────────────

class PagePeronnelAjout(ctk.CTkFrame):
    """
    Page Personnel — liste compacte avec filtres + modal ajout/modif.
    Compatible avec PageMainPersonnel.
    """

    def __init__(self, master, callback_liste=None, db_conn=None, session_data=None):
        super().__init__(master, fg_color=Colors.BG_PAGE)

        self.callback_liste = callback_liste
        self.db_conn        = db_conn
        self.session_data   = session_data
        self._fonction_filter_map = {}   # label → idfonction

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_filters()
        self._build_table()
        self._build_statusbar()

        self.load_personnels()
        self._load_fonction_filter()

    # ── Connexion DB ─────────────────────────────────────────────────────────

    def connect_db(self):
        try:
            with open(get_config_path('config.json')) as f:
                config = json.load(f)
                db = config['database']
            return psycopg2.connect(
                host=db['host'], user=db['user'],
                password=db['password'], database=db['database'],
                port=db['port']
            )
        except Exception as e:
            messagebox.showerror("Connexion", f"Erreur : {e}")
            return None

    # ── En-tête ──────────────────────────────────────────────────────────────

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=Colors.BG_CARD,
                              corner_radius=Layout.RADIUS)
        header.grid(row=0, column=0, padx=12, pady=(12, 6), sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        # Icône + titre
        title_frame = styled.frame(header)
        title_frame.grid(row=0, column=0, padx=Layout.CARD_PADX,
                         pady=14, sticky="w")

        ctk.CTkLabel(
            title_frame, text="👥",
            font=Fonts.title(22), text_color=Colors.PRIMARY
        ).pack(side="left", padx=(0, 10))

        info = styled.frame(title_frame)
        info.pack(side="left")
        styled.label_title(info, text="Gestion du Personnel", size=17
                           ).pack(anchor="w")
        styled.label_muted(info, text="Ajout, modification et suppression du personnel"
                           ).pack(anchor="w")

        # Bouton Nouveau
        styled.button_success(
            header, text="Nouveau personnel", icon="➕",
            command=self._ouvrir_modal_ajout, width=175, height=38
        ).grid(row=0, column=2, padx=Layout.CARD_PADX, pady=14)

    # ── Barre de filtres ─────────────────────────────────────────────────────

    def _build_filters(self):
        fbar = ctk.CTkFrame(self, fg_color=Colors.BG_CARD,
                             corner_radius=Layout.RADIUS)
        fbar.grid(row=1, column=0, padx=12, pady=(0, 6), sticky="ew")
        fbar.grid_rowconfigure(0, weight=0)

        # Recherche texte
        styled.label_muted(fbar, text="🔍  Recherche", anchor="w"
                           ).grid(row=0, column=0, padx=(16, 4), pady=10, sticky="w")
        self.entry_search = styled.entry(fbar, placeholder="Nom, prénom, matricule…",
                                          height=34, width=200)
        self.entry_search.grid(row=0, column=1, padx=(0, 20), pady=10, sticky="ew")
        self.entry_search.bind("<KeyRelease>", lambda e: self._apply_filters())

        # Filtre Fonction
        styled.label_muted(fbar, text="Fonction", anchor="w"
                           ).grid(row=0, column=2, padx=(0, 4), pady=10, sticky="w")
        self.combo_filter_fonction = ctk.CTkComboBox(
            fbar, values=["Toutes"], state="readonly",
            width=160, height=34,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            button_color=Colors.PRIMARY, font=Fonts.body(12),
            command=lambda v: self._apply_filters()
        )
        self.combo_filter_fonction.set("Toutes")
        self.combo_filter_fonction.grid(row=0, column=3, padx=(0, 20), pady=10)

        # Filtre Sexe
        styled.label_muted(fbar, text="Sexe", anchor="w"
                           ).grid(row=0, column=4, padx=(0, 4), pady=10, sticky="w")
        self.combo_filter_sexe = ctk.CTkComboBox(
            fbar, values=["Tous", "M", "F"], state="readonly",
            width=90, height=34,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            button_color=Colors.PRIMARY, font=Fonts.body(12),
            command=lambda v: self._apply_filters()
        )
        self.combo_filter_sexe.set("Tous")
        self.combo_filter_sexe.grid(row=0, column=5, padx=(0, 16), pady=10)

        # Bouton reset
        styled.button_secondary(
            fbar, text="Réinitialiser", icon="↺",
            command=self._reset_filters, width=120, height=34
        ).grid(row=0, column=6, padx=(0, 16), pady=10)

        fbar.grid_columnconfigure(1, weight=1)

    # ── Tableau ───────────────────────────────────────────────────────────────

    def _build_table(self):
        card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD,
                             corner_radius=Layout.RADIUS)
        card.grid(row=2, column=0, padx=12, pady=(0, 6), sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Style Treeview
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Personnel.Treeview",
            background=Colors.BG_CARD,
            foreground=Colors.TEXT_PRIMARY,
            fieldbackground=Colors.BG_CARD,
            rowheight=Layout.ROW_H,
            font=(Fonts._family if hasattr(Fonts, "_family") else "Segoe UI", 11),
            borderwidth=0,
        )
        style.configure(
            "Personnel.Treeview.Heading",
            background=Colors.MIDNIGHT,
            foreground=Colors.TEXT_ON_DARK,
            font=(Fonts._family if hasattr(Fonts, "_family") else "Segoe UI", 11, "bold"),
            relief="flat",
            padding=(8, 6),
        )
        style.map("Personnel.Treeview",
                  background=[("selected", Colors.PRIMARY_LIGHT)],
                  foreground=[("selected", Colors.TEXT_PRIMARY)])
        style.map("Personnel.Treeview.Heading",
                  background=[("active", Colors.MIDNIGHT_LIGHT)])

        cols = ("ID", "Matricule", "Nom", "Prénom", "Adresse", "CIN", "Contact", "Sexe", "Fonction")
        self.tree = ttk.Treeview(card, columns=cols, show="headings",
                                  style="Personnel.Treeview", selectmode="browse")

        col_cfg = {
            "ID":        (45,  "center"),
            "Matricule": (110, "w"),
            "Nom":       (130, "w"),
            "Prénom":    (120, "w"),
            "Adresse":   (150, "w"),
            "CIN":       (100, "center"),
            "Contact":   (110, "w"),
            "Sexe":      (55,  "center"),
            "Fonction":  (140, "w"),
        }
        for col, (w, anchor) in col_cfg.items():
            self.tree.heading(col, text=col,
                               command=lambda c=col: self._sort_by(c))
            self.tree.column(col, width=w, anchor=anchor, minwidth=40)

        # Tags alternance
        self.tree.tag_configure("even", background=Colors.BG_CARD)
        self.tree.tag_configure("odd",  background=Colors.BG_ROW_ALT)

        # Scrollbars
        vsb = ttk.Scrollbar(card, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(card, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=1, column=0, sticky="nsew", padx=(8, 0), pady=(0, 0))
        vsb.grid(row=1, column=1, sticky="ns")
        hsb.grid(row=2, column=0, sticky="ew", padx=(8, 0))

        # Double-clic → modifier
        self.tree.bind("<Double-1>", self._on_double_click)

        # Boutons contextuels sous le tableau
        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=3, column=0, columnspan=2,
                     padx=8, pady=(6, 10), sticky="w")

        styled.button_primary(
            actions, text="Modifier", icon="✏️",
            command=self._ouvrir_modal_modif, width=120, height=34
        ).pack(side="left", padx=(0, 8))

        styled.button_danger(
            actions, text="Supprimer", icon="🗑",
            command=self._supprimer, width=120, height=34
        ).pack(side="left")

        # Stocker toutes les données pour le filtrage côté client
        self._all_rows = []

    # ── Barre de statut ───────────────────────────────────────────────────────

    def _build_statusbar(self):
        bar = ctk.CTkFrame(self, fg_color=Colors.DIVIDER,
                            corner_radius=0, height=28)
        bar.grid(row=3, column=0, sticky="ew")
        bar.grid_propagate(False)

        self.lbl_status = ctk.CTkLabel(
            bar, text="Chargement…",
            font=Fonts.small(10),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        )
        self.lbl_status.pack(side="left", padx=16)

    # ── Chargement données ────────────────────────────────────────────────────

    def _load_fonction_filter(self):
        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT idfonction, designationfonction FROM tb_fonction "
                "WHERE deleted=0 ORDER BY designationfonction"
            )
            rows = cur.fetchall()
            self._fonction_filter_map = {r[1]: r[0] for r in rows}
            labels = ["Toutes"] + [r[1] for r in rows]
            self.combo_filter_fonction.configure(values=labels)
        finally:
            conn.close()

    def load_personnels(self):
        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute(
                """SELECT p.id, p.matricule, p.nom, p.prenom,
                          p.adresse, p.cin, p.contact, p.sexe,
                          f.designationfonction, p.idfonction
                   FROM tb_personnel p
                   LEFT JOIN tb_fonction f ON p.idfonction = f.idfonction
                   WHERE p.deleted = 0
                   ORDER BY p.nom"""
            )
            self._all_rows = cur.fetchall()
        finally:
            conn.close()

        self._apply_filters()

    def _apply_filters(self):
        search   = self.entry_search.get().strip().lower()
        filtre_f = self.combo_filter_fonction.get()
        filtre_s = self.combo_filter_sexe.get()

        # Vider
        for item in self.tree.get_children():
            self.tree.delete(item)

        count = 0
        for idx, row in enumerate(self._all_rows):
            pid, matricule, nom, prenom, adresse, cin, contact, sexe, fonction, idfonction = row

            # Filtre texte
            if search:
                hay = f"{nom or ''} {prenom or ''} {matricule or ''}".lower()
                if search not in hay:
                    continue

            # Filtre fonction
            if filtre_f != "Toutes":
                if self._fonction_filter_map.get(filtre_f) != idfonction:
                    continue

            # Filtre sexe
            if filtre_s != "Tous" and sexe != filtre_s:
                continue

            def v(x):
                return x if x else "-"

            tag = "even" if count % 2 == 0 else "odd"
            self.tree.insert("", "end", iid=str(pid), tags=(tag,),
                              values=(pid, v(matricule), v(nom), v(prenom),
                                      v(adresse), v(cin), v(contact), v(sexe),
                                      v(fonction)))
            count += 1

        total = len(self._all_rows)
        self.lbl_status.configure(
            text=f"  {count} personnel(s) affiché(s) sur {total} au total"
        )

    def _reset_filters(self):
        self.entry_search.delete(0, "end")
        self.combo_filter_fonction.set("Toutes")
        self.combo_filter_sexe.set("Tous")
        self._apply_filters()

    # ── Tri colonnes ─────────────────────────────────────────────────────────

    _sort_state = {}

    def _sort_by(self, col):
        col_idx = {"ID": 0, "Matricule": 1, "Nom": 2, "Prénom": 3,
                   "Adresse": 4, "CIN": 5, "Contact": 6, "Sexe": 7, "Fonction": 8}
        idx     = col_idx.get(col, 2)
        reverse = self._sort_state.get(col, False)
        self._sort_state[col] = not reverse

        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        data.sort(key=lambda t: t[0].lower(), reverse=reverse)

        for i, (_, k) in enumerate(data):
            self.tree.move(k, "", i)
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.item(k, tags=(tag,))

    # ── Actions ───────────────────────────────────────────────────────────────

    def _get_selected_data(self):
        sel = self.tree.selection()
        if not sel:
            return None
        values = self.tree.item(sel[0])["values"]
        # Chercher la ligne complète dans _all_rows pour récupérer idfonction
        pid = values[0]
        for row in self._all_rows:
            if row[0] == pid:
                return {
                    "id":         row[0],
                    "matricule":  row[1],
                    "nom":        row[2],
                    "prenom":     row[3],
                    "adresse":    row[4],
                    "cin":        row[5],
                    "contact":    row[6],
                    "sexe":       row[7],
                    "fonction":   row[8],   # désignation texte
                    "idfonction": row[9],
                }
        return None

    def _generer_matricule(self):
        """Génère un matricule automatique."""
        conn = self.connect_db()
        if not conn:
            return ""
        try:
            cur  = conn.cursor()
            annee = datetime.now().year
            cur.execute(
                "SELECT matricule FROM tb_personnel WHERE matricule LIKE %s "
                "ORDER BY id DESC LIMIT 1",
                (f"{annee}-P-%",)
            )
            last = cur.fetchone()
            num  = 1
            if last:
                try:
                    num = int(last[0].split("-")[-1]) + 1
                except Exception:
                    num = 1
            return f"{annee}-P-{num:05d}"
        finally:
            conn.close()

    def _ouvrir_modal_ajout(self):
        mat = self._generer_matricule()
        modal = ModalPersonnel(self, on_save=self.load_personnels,
                                db_conn_fn=self.connect_db, mode="ajout")
        # Injecter le matricule généré
        modal.entry_matricule.configure(state="normal")
        modal.entry_matricule.delete(0, "end")
        modal.entry_matricule.insert(0, mat)
        modal.entry_matricule.configure(state="readonly")

    def _ouvrir_modal_modif(self):
        data = self._get_selected_data()
        if not data:
            messagebox.showwarning("Sélection", "Sélectionnez d'abord un personnel.")
            return
        ModalPersonnel(self, on_save=self.load_personnels,
                        db_conn_fn=self.connect_db,
                        mode="modification", personnel_data=data)

    def _on_double_click(self, event):
        self._ouvrir_modal_modif()

    def _supprimer(self):
        data = self._get_selected_data()
        if not data:
            messagebox.showwarning("Sélection", "Sélectionnez d'abord un personnel.")
            return

        nom = data.get("nom", "")
        if not messagebox.askyesno(
            "Confirmation",
            f"Supprimer « {nom} » ?\nCette action est irréversible."
        ):
            return

        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute("UPDATE tb_personnel SET deleted=1 WHERE id=%s", (data["id"],))
            conn.commit()
            self.load_personnels()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
        finally:
            conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Test standalone
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from app_theme import Theme
    Theme.setup()

    root = ctk.CTk()
    root.title("Personnel — test")
    root.geometry("1150x700")
    Theme.apply(root)

    page = PagePeronnelAjout(root)
    page.pack(fill="both", expand=True)
    root.mainloop()