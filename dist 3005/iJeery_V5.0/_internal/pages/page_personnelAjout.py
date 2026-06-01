# -*- coding: utf-8 -*-
"""
PagePersonnelAjout — Liste compacte + modal ajout/modif
Thème : iJeery (app_theme.py) — UI dense & compacte
"""

import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import json
from datetime import datetime
from resource_utils import get_config_path
from app_theme import Colors, Fonts, styled, Layout
from log_utils import AppLogger
from pages.personnel_structure import (
    UNKNOWN_LABEL,
    ensure_personnel_structure,
    has_personnel_structure,
    personnel_poste_select,
)


# ─────────────────────────────────────────────────────────────────────────────
# MODAL
# ─────────────────────────────────────────────────────────────────────────────

class ModalCategoriesPostes(ctk.CTkToplevel):
    """Gestion CRUD des categories personnel et de leurs postes."""

    def __init__(self, master, db_conn_fn, on_close=None):
        super().__init__(master)
        self._connect_db = db_conn_fn
        self._on_close = on_close
        self.categories = []
        self.postes = []
        self.selected_categorie_id = None
        self.selected_poste_id = None

        self.title("Gérer Catégories et Postes")
        self.geometry("980x620")
        self.minsize(860, 540)
        self.configure(fg_color=Colors.BG_PAGE)
        self.grab_set()
        self.focus_set()
        self.protocol("WM_DELETE_WINDOW", self._close)

        self._build_ui()
        self.load_categories()

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT, corner_radius=0, height=50)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header,
            text="  🧩  Catégories et postes du personnel",
            font=Fonts.bold(14),
            text_color=Colors.TEXT_ON_DARK,
            anchor="w",
        ).pack(side="left", padx=18, fill="y")

        body = ctk.CTkFrame(self, fg_color=Colors.BG_PAGE, corner_radius=0)
        body.pack(fill="both", expand=True, padx=10, pady=10)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        cat_card = ctk.CTkFrame(body, fg_color=Colors.BG_CARD, corner_radius=8)
        cat_card.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        poste_card = ctk.CTkFrame(body, fg_color=Colors.BG_CARD, corner_radius=8)
        poste_card.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        for card in (cat_card, poste_card):
            card.grid_columnconfigure(0, weight=1)
            card.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(cat_card, text="Catégories", font=Fonts.bold(13), text_color=Colors.TEXT_PRIMARY).grid(
            row=0, column=0, padx=12, pady=(12, 4), sticky="w"
        )
        self.entry_cat_titre = self._entry(cat_card, "Titre de catégorie")
        self.entry_cat_titre.grid(row=1, column=0, padx=12, pady=(0, 6), sticky="ew")
        self.entry_cat_desc = self._entry(cat_card, "Description")
        self.entry_cat_desc.grid(row=1, column=1, padx=(0, 12), pady=(0, 6), sticky="ew")
        cat_card.grid_columnconfigure(1, weight=1)

        self.tree_categories = ttk.Treeview(
            cat_card, columns=("id", "titre", "description"), show="headings", style="P2.Treeview", selectmode="browse"
        )
        for col, txt, w in [("id", "ID", 45), ("titre", "Titre", 160), ("description", "Description", 230)]:
            self.tree_categories.heading(col, text=txt)
            self.tree_categories.column(col, width=w, anchor="w")
        self.tree_categories.grid(row=2, column=0, columnspan=2, padx=12, pady=6, sticky="nsew")
        self.tree_categories.bind("<<TreeviewSelect>>", self._on_category_select)

        cat_actions = ctk.CTkFrame(cat_card, fg_color="transparent")
        cat_actions.grid(row=3, column=0, columnspan=2, padx=12, pady=(4, 12), sticky="ew")
        ctk.CTkButton(cat_actions, text="Enregistrer", width=105, height=28, fg_color=Colors.SUCCESS,
                      hover_color=Colors.SUCCESS_DARK, font=Fonts.bold(11), command=self.save_category).pack(side="left", padx=(0, 6))
        ctk.CTkButton(cat_actions, text="Modifier", width=90, height=28, fg_color=Colors.PRIMARY,
                      hover_color=Colors.PRIMARY_HOVER, font=Fonts.bold(11), command=self.update_category).pack(side="left", padx=(0, 6))
        ctk.CTkButton(cat_actions, text="Supprimer", width=95, height=28, fg_color=Colors.DANGER,
                      hover_color=Colors.DANGER_DARK, font=Fonts.bold(11), command=self.delete_category).pack(side="left", padx=(0, 6))
        ctk.CTkButton(cat_actions, text="Vider", width=70, height=28, fg_color=Colors.CLOUDS,
                      hover_color=Colors.SILVER, text_color=Colors.TEXT_PRIMARY, font=Fonts.bold(11),
                      command=self.clear_category_form).pack(side="right")

        ctk.CTkLabel(poste_card, text="Postes de la catégorie sélectionnée", font=Fonts.bold(13),
                     text_color=Colors.TEXT_PRIMARY).grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")
        self.entry_poste_titre = self._entry(poste_card, "Titre du poste")
        self.entry_poste_titre.grid(row=1, column=0, padx=12, pady=(0, 6), sticky="ew")
        self.entry_poste_desc = self._entry(poste_card, "Description")
        self.entry_poste_desc.grid(row=1, column=1, padx=(0, 12), pady=(0, 6), sticky="ew")
        poste_card.grid_columnconfigure(1, weight=1)

        self.tree_postes = ttk.Treeview(
            poste_card, columns=("id", "titre", "description"), show="headings", style="P2.Treeview", selectmode="browse"
        )
        for col, txt, w in [("id", "ID", 45), ("titre", "Poste", 170), ("description", "Description", 230)]:
            self.tree_postes.heading(col, text=txt)
            self.tree_postes.column(col, width=w, anchor="w")
        self.tree_postes.grid(row=2, column=0, columnspan=2, padx=12, pady=6, sticky="nsew")
        self.tree_postes.bind("<<TreeviewSelect>>", self._on_poste_select)

        poste_actions = ctk.CTkFrame(poste_card, fg_color="transparent")
        poste_actions.grid(row=3, column=0, columnspan=2, padx=12, pady=(4, 12), sticky="ew")
        ctk.CTkButton(poste_actions, text="Enregistrer", width=105, height=28, fg_color=Colors.SUCCESS,
                      hover_color=Colors.SUCCESS_DARK, font=Fonts.bold(11), command=self.save_poste).pack(side="left", padx=(0, 6))
        ctk.CTkButton(poste_actions, text="Modifier", width=90, height=28, fg_color=Colors.PRIMARY,
                      hover_color=Colors.PRIMARY_HOVER, font=Fonts.bold(11), command=self.update_poste).pack(side="left", padx=(0, 6))
        ctk.CTkButton(poste_actions, text="Supprimer", width=95, height=28, fg_color=Colors.DANGER,
                      hover_color=Colors.DANGER_DARK, font=Fonts.bold(11), command=self.delete_poste).pack(side="left", padx=(0, 6))
        ctk.CTkButton(poste_actions, text="Fermer", width=80, height=28, fg_color=Colors.CLOUDS,
                      hover_color=Colors.SILVER, text_color=Colors.TEXT_PRIMARY, font=Fonts.bold(11),
                      command=self._close).pack(side="right")

    def _entry(self, parent, placeholder):
        return ctk.CTkEntry(parent, height=30, fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
                            font=Fonts.body(11), corner_radius=6, placeholder_text=placeholder)

    def _execute(self, sql, params=(), fetch=False):
        conn = self._connect_db()
        if not conn:
            return [] if fetch else None
        try:
            ensure_personnel_structure(conn)
            cur = conn.cursor()
            cur.execute(sql, params)
            rows = cur.fetchall() if fetch else None
            conn.commit()
            return rows
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur", str(e), parent=self)
            return [] if fetch else None
        finally:
            conn.close()

    def load_categories(self):
        rows = self._execute(
            "SELECT idcategorie, titre, COALESCE(description,'') FROM tb_categoriepersonnel "
            "WHERE COALESCE(deleted,0)=0 ORDER BY titre",
            fetch=True,
        )
        self.tree_categories.delete(*self.tree_categories.get_children())
        for row in rows:
            self.tree_categories.insert("", "end", iid=str(row[0]), values=row)
        if rows and self.selected_categorie_id is None:
            self.tree_categories.selection_set(str(rows[0][0]))
            self._on_category_select()
        elif self.selected_categorie_id:
            self.load_postes(self.selected_categorie_id)

    def load_postes(self, categorie_id):
        rows = self._execute(
            "SELECT idposte, titre, COALESCE(description,'') FROM tb_postepersonnel "
            "WHERE COALESCE(deleted,0)=0 AND idcategorie=%s ORDER BY titre",
            (categorie_id,),
            fetch=True,
        )
        self.tree_postes.delete(*self.tree_postes.get_children())
        for row in rows:
            self.tree_postes.insert("", "end", iid=str(row[0]), values=row)

    def _on_category_select(self, event=None):
        sel = self.tree_categories.selection()
        if not sel:
            return
        values = self.tree_categories.item(sel[0], "values")
        self.selected_categorie_id = int(values[0])
        self.entry_cat_titre.delete(0, "end"); self.entry_cat_titre.insert(0, values[1])
        self.entry_cat_desc.delete(0, "end"); self.entry_cat_desc.insert(0, values[2])
        self.clear_poste_form()
        self.load_postes(self.selected_categorie_id)

    def _on_poste_select(self, event=None):
        sel = self.tree_postes.selection()
        if not sel:
            return
        values = self.tree_postes.item(sel[0], "values")
        self.selected_poste_id = int(values[0])
        self.entry_poste_titre.delete(0, "end"); self.entry_poste_titre.insert(0, values[1])
        self.entry_poste_desc.delete(0, "end"); self.entry_poste_desc.insert(0, values[2])

    def save_category(self):
        titre = self.entry_cat_titre.get().strip()
        if not titre:
            messagebox.showwarning("Catégorie", "Veuillez saisir le titre.", parent=self)
            return
        self._execute("INSERT INTO tb_categoriepersonnel (titre, description, deleted) VALUES (%s,%s,0)",
                      (titre, self.entry_cat_desc.get().strip() or None))
        self.clear_category_form()
        self.load_categories()

    def update_category(self):
        if not self.selected_categorie_id:
            messagebox.showwarning("Catégorie", "Sélectionnez une catégorie.", parent=self)
            return
        titre = self.entry_cat_titre.get().strip()
        if not titre:
            return
        self._execute("UPDATE tb_categoriepersonnel SET titre=%s, description=%s WHERE idcategorie=%s",
                      (titre, self.entry_cat_desc.get().strip() or None, self.selected_categorie_id))
        self.load_categories()

    def delete_category(self):
        if not self.selected_categorie_id:
            return
        if not messagebox.askyesno("Confirmation", "Supprimer cette catégorie et masquer ses postes ?", parent=self):
            return
        self._execute("UPDATE tb_categoriepersonnel SET deleted=1 WHERE idcategorie=%s", (self.selected_categorie_id,))
        self._execute("UPDATE tb_postepersonnel SET deleted=1 WHERE idcategorie=%s", (self.selected_categorie_id,))
        self.selected_categorie_id = None
        self.clear_category_form()
        self.clear_poste_form()
        self.load_categories()

    def save_poste(self):
        if not self.selected_categorie_id:
            messagebox.showwarning("Poste", "Sélectionnez d'abord une catégorie.", parent=self)
            return
        titre = self.entry_poste_titre.get().strip()
        if not titre:
            messagebox.showwarning("Poste", "Veuillez saisir le titre du poste.", parent=self)
            return
        self._execute("INSERT INTO tb_postepersonnel (idcategorie, titre, description, deleted) VALUES (%s,%s,%s,0)",
                      (self.selected_categorie_id, titre, self.entry_poste_desc.get().strip() or None))
        self.clear_poste_form()
        self.load_postes(self.selected_categorie_id)

    def update_poste(self):
        if not self.selected_poste_id:
            return
        titre = self.entry_poste_titre.get().strip()
        if not titre:
            return
        self._execute("UPDATE tb_postepersonnel SET titre=%s, description=%s WHERE idposte=%s",
                      (titre, self.entry_poste_desc.get().strip() or None, self.selected_poste_id))
        self.load_postes(self.selected_categorie_id)

    def delete_poste(self):
        if not self.selected_poste_id:
            return
        if not messagebox.askyesno("Confirmation", "Supprimer ce poste ?", parent=self):
            return
        self._execute("UPDATE tb_postepersonnel SET deleted=1 WHERE idposte=%s", (self.selected_poste_id,))
        self.clear_poste_form()
        self.load_postes(self.selected_categorie_id)

    def clear_category_form(self):
        self.selected_categorie_id = None
        self.entry_cat_titre.delete(0, "end")
        self.entry_cat_desc.delete(0, "end")

    def clear_poste_form(self):
        self.selected_poste_id = None
        self.entry_poste_titre.delete(0, "end")
        self.entry_poste_desc.delete(0, "end")

    def _close(self):
        if self._on_close:
            self._on_close()
        self.destroy()

class ModalPersonnel(ctk.CTkToplevel):
    """Fenêtre modale compacte pour ajout / modification d'un personnel."""

    def __init__(self, master, on_save, db_conn_fn, mode="ajout", personnel_data=None):
        super().__init__(master)
        self._on_save    = on_save
        self._connect_db = db_conn_fn
        self.mode        = mode
        self.personnel   = personnel_data
        self.categorie_dict = {}
        self.poste_dict = {}
        self.poste_to_category = {}
        self.session_data = getattr(master, "session_data", None) or {}
        self._logger = AppLogger(session_data=self.session_data)

        titre = "Nouveau personnel" if mode == "ajout" else "Modifier le personnel"
        self.title(titre)
        self.geometry("560x400")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_PAGE)
        self.grab_set()
        self.focus_set()

        self._build_ui()
        self._load_categories_postes()
        if mode == "modification" and personnel_data:
            self._prefill()

    def _build_ui(self):
        # ── En-tête compact ──────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT,
                               corner_radius=0, height=42)
        header.pack(fill="x")
        header.pack_propagate(False)
        icon  = "➕" if self.mode == "ajout" else "✏️"
        titre = "Nouveau personnel" if self.mode == "ajout" else "Modifier le personnel"
        ctk.CTkLabel(header, text=f"  {icon}  {titre}",
                     font=Fonts.bold(13), text_color=Colors.TEXT_ON_DARK,
                     anchor="w").pack(side="left", padx=18, fill="y")

        # ── Corps ────────────────────────────────────────────────────────
        body = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        body.pack(fill="both", expand=True, padx=16, pady=10)
        body.grid_columnconfigure((1, 3), weight=1)

        def lbl(row, col, text, required=False):
            color = Colors.DANGER if required else Colors.TEXT_SECONDARY
            ctk.CTkLabel(body, text=f"{text} *" if required else text,
                         font=Fonts.label(10), text_color=color, anchor="w"
                         ).grid(row=row, column=col, padx=(0, 5), pady=3, sticky="w")

        def entry(parent, placeholder=""):
            return ctk.CTkEntry(parent, height=28, fg_color=Colors.BG_INPUT,
                                border_color=Colors.BORDER, font=Fonts.body(11),
                                corner_radius=6, placeholder_text=placeholder)

        def combo(parent, values, readonly=True):
            return ctk.CTkComboBox(parent, values=values,
                                   state="readonly" if readonly else "normal",
                                   height=28, fg_color=Colors.BG_INPUT,
                                   border_color=Colors.BORDER,
                                   button_color=Colors.PRIMARY,
                                   dropdown_fg_color=Colors.BG_CARD,
                                   font=Fonts.body(11))

        # Ligne 0 — Matricule / Nom *
        lbl(0, 0, "Matricule")
        self.entry_matricule = entry(body)
        self.entry_matricule.grid(row=0, column=1, padx=(0, 12), pady=3, sticky="ew")
        lbl(0, 2, "Nom", required=True)
        self.entry_nom = entry(body, "Nom de famille")
        self.entry_nom.grid(row=0, column=3, pady=3, sticky="ew")

        # Ligne 1 — Prénom / Sexe *
        lbl(1, 0, "Prénom")
        self.entry_prenom = entry(body, "Prénom")
        self.entry_prenom.grid(row=1, column=1, padx=(0, 12), pady=3, sticky="ew")
        lbl(1, 2, "Sexe", required=True)
        self.combo_sexe = combo(body, ["M", "F"])
        self.combo_sexe.set("M")
        self.combo_sexe.grid(row=1, column=3, pady=3, sticky="ew")

        # Ligne 2 — Catégorie / Poste
        lbl(2, 0, "Catégorie")
        self.combo_categorie = combo(body, [])
        self.combo_categorie.grid(row=2, column=1, padx=(0, 12), pady=3, sticky="ew")
        self.combo_categorie.configure(command=lambda v: self._on_category_change(v))
        lbl(2, 2, "Poste")
        self.combo_poste = combo(body, [])
        self.combo_poste.grid(row=2, column=3, pady=3, sticky="ew")

        # Ligne 3 — Adresse / CIN
        lbl(3, 0, "Adresse")
        self.entry_adresse = entry(body, "Adresse")
        self.entry_adresse.grid(row=3, column=1, padx=(0, 12), pady=3, sticky="ew")
        lbl(3, 2, "CIN")
        self.entry_cin = entry(body, "N° CIN")
        self.entry_cin.grid(row=3, column=3, pady=3, sticky="ew")

        # Ligne 4 — Contact
        lbl(4, 0, "Contact")
        self.entry_contact = entry(body, "Tél / Email")
        self.entry_contact.grid(row=4, column=1, pady=3, sticky="ew")

        # Note obligatoires
        ctk.CTkLabel(body, text="* Champs obligatoires - Catégorie/Poste peuvent rester inconnus",
                     font=Fonts.small(9), text_color=Colors.TEXT_MUTED
                     ).grid(row=5, column=0, columnspan=4, pady=(6, 0), sticky="w")

        # Séparateur + boutons
        ctk.CTkFrame(body, height=1, fg_color=Colors.DIVIDER
                     ).grid(row=6, column=0, columnspan=4, pady=(8, 6), sticky="ew")

        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.grid(row=7, column=0, columnspan=4, sticky="e")

        ctk.CTkButton(btn_row, text="✕  Annuler", width=100, height=28,
                      fg_color=Colors.CLOUDS, hover_color=Colors.SILVER,
                      text_color=Colors.TEXT_PRIMARY,
                      font=Fonts.bold(11), corner_radius=6,
                      border_width=1, border_color=Colors.BORDER,
                      command=self.destroy
                      ).pack(side="left", padx=(0, 8))

        lbl_save = "💾  Enregistrer" if self.mode == "ajout" else "✔  Mettre à jour"
        ctk.CTkButton(btn_row, text=lbl_save, width=130, height=28,
                      fg_color=Colors.SUCCESS, hover_color=Colors.SUCCESS_DARK,
                      text_color=Colors.TEXT_ON_DARK,
                      font=Fonts.bold(11), corner_radius=6,
                      command=self._save
                      ).pack(side="left")

    def _load_categories_postes(self):
        conn = self._connect_db()
        if not conn: return
        try:
            ensure_personnel_structure(conn)
            cur = conn.cursor()
            cur.execute(
                "SELECT idcategorie, titre FROM tb_categoriepersonnel "
                "WHERE COALESCE(deleted,0)=0 ORDER BY titre"
            )
            cats = cur.fetchall()
            self.categorie_dict = {r[1]: r[0] for r in cats}
            self.combo_categorie.configure(values=[UNKNOWN_LABEL] + [r[1] for r in cats])
            self.combo_categorie.set(UNKNOWN_LABEL)

            cur.execute(
                "SELECT idposte, idcategorie, titre FROM tb_postepersonnel "
                "WHERE COALESCE(deleted,0)=0 ORDER BY titre"
            )
            postes = cur.fetchall()
            self.poste_dict = {r[2]: r[0] for r in postes}
            self.poste_to_category = {r[0]: r[1] for r in postes}
            self._refresh_postes_for_category(None)
        finally:
            conn.close()

    def _refresh_postes_for_category(self, categorie_id):
        values = [UNKNOWN_LABEL]
        conn = self._connect_db()
        if not conn:
            self.combo_poste.configure(values=values)
            self.combo_poste.set(UNKNOWN_LABEL)
            return
        try:
            ensure_personnel_structure(conn)
            cur = conn.cursor()
            if categorie_id:
                cur.execute(
                    "SELECT idposte, titre FROM tb_postepersonnel "
                    "WHERE COALESCE(deleted,0)=0 AND idcategorie=%s ORDER BY titre",
                    (categorie_id,),
                )
            else:
                cur.execute(
                    "SELECT idposte, titre FROM tb_postepersonnel "
                    "WHERE COALESCE(deleted,0)=0 ORDER BY titre"
                )
            rows = cur.fetchall()
            self.poste_dict = {r[1]: r[0] for r in rows}
            values += [r[1] for r in rows]
        finally:
            conn.close()
        self.combo_poste.configure(values=values)
        self.combo_poste.set(UNKNOWN_LABEL)

    def _on_category_change(self, value):
        self._refresh_postes_for_category(self.categorie_dict.get(value))

    def _prefill(self):
        p = self.personnel
        self.entry_matricule.configure(state="normal")
        self.entry_matricule.delete(0, "end")
        self.entry_matricule.insert(0, p.get("matricule", "") or "")
        self.entry_matricule.configure(state="readonly")
        self.entry_nom.delete(0, "end");     self.entry_nom.insert(0, p.get("nom", "") or "")
        self.entry_prenom.delete(0, "end");  self.entry_prenom.insert(0, p.get("prenom", "") or "")
        self.combo_sexe.set(p.get("sexe", "M") or "M")
        self.combo_categorie.set(p.get("categorie", UNKNOWN_LABEL) or UNKNOWN_LABEL)
        self._refresh_postes_for_category(p.get("idcategorie"))
        self.combo_poste.set(p.get("poste", UNKNOWN_LABEL) or UNKNOWN_LABEL)
        self.entry_adresse.delete(0, "end"); self.entry_adresse.insert(0, p.get("adresse", "") or "")
        self.entry_cin.delete(0, "end");     self.entry_cin.insert(0, p.get("cin", "") or "")
        self.entry_contact.delete(0, "end"); self.entry_contact.insert(0, p.get("contact", "") or "")

    def _save(self):
        nom      = self.entry_nom.get().strip()
        sexe     = self.combo_sexe.get().strip()
        poste    = self.combo_poste.get().strip()
        if not nom or not sexe:
            messagebox.showwarning("Champs obligatoires",
                                   "Veuillez remplir : Nom et Sexe.",
                                   parent=self)
            return
        data = {
            "matricule":  self.entry_matricule.get().strip() or None,
            "nom":        nom,
            "prenom":     self.entry_prenom.get().strip() or None,
            "adresse":    self.entry_adresse.get().strip() or None,
            "cin":        self.entry_cin.get().strip() or None,
            "contact":    self.entry_contact.get().strip() or None,
            "sexe":       sexe,
            "idposte":    self.poste_dict.get(poste) if poste != UNKNOWN_LABEL else None,
        }
        conn = self._connect_db()
        if not conn: return
        try:
            ensure_personnel_structure(conn)
            cur = conn.cursor()
            if self.mode == "ajout":
                cur.execute(
                    "INSERT INTO tb_personnel "
                    "(matricule,nom,prenom,datenaissance,adresse,cin,contact,sexe,idposte,deleted) "
                    "VALUES (%s,%s,%s,NULL,%s,%s,%s,%s,%s,0)",
                    (data["matricule"], data["nom"], data["prenom"],
                     data["adresse"], data["cin"], data["contact"],
                     data["sexe"], data["idposte"])
                )
                msg = "Personnel ajouté avec succès !"
            else:
                cur.execute(
                    "UPDATE tb_personnel SET matricule=%s,nom=%s,prenom=%s,"
                    "adresse=%s,cin=%s,contact=%s,sexe=%s,idposte=%s WHERE id=%s",
                    (data["matricule"], data["nom"], data["prenom"],
                     data["adresse"], data["cin"], data["contact"],
                     data["sexe"], data["idposte"], self.personnel["id"])
                )
                msg = "Personnel mis à jour !"
            conn.commit()
            try:
                self._logger.log(
                    action="Création personnel" if self.mode == "ajout" else "Modification personnel",
                    element=str(data.get("matricule") or data.get("nom") or ""),
                    details=f"Personnel {'créé' if self.mode=='ajout' else 'modifié'} (nom='{data.get('nom')}', prenom='{data.get('prenom')}', sexe='{data.get('sexe')}', idposte={data.get('idposte')})",
                    value="aucune valeur",
                )
            except Exception:
                pass
            messagebox.showinfo("Succès", msg, parent=self)
            self._on_save()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erreur", str(e), parent=self)
        finally:
            conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# PAGE PRINCIPALE
# ─────────────────────────────────────────────────────────────────────────────

class PagePeronnelAjout(ctk.CTkFrame):
    def __init__(self, master, callback_liste=None, db_conn=None, session_data=None):
        super().__init__(master, fg_color=Colors.BG_PAGE)
        self.callback_liste = callback_liste
        self.db_conn        = db_conn
        self.session_data   = session_data
        self._categorie_filter_map = {}
        self._poste_filter_map = {}
        self._all_rows = []
        _sort_state    = {}

        self._personnel_structure_ready = self._ensure_structure()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_filters()
        self._build_table()
        self._build_statusbar()

        self.load_personnels()
        self._load_category_poste_filters()

    # ── DB ────────────────────────────────────────────────────────────────────

    def connect_db(self):


        try:


            from pages.db_helper import connect_page_db


            shared = (


                getattr(self, '_db_conn_shared', None)


                or getattr(self, '_db_conn_initial', None)


            )


            return connect_page_db(shared)

        except Exception as e:
            messagebox.showerror("Connexion", str(e))
            return None

    def _ensure_structure(self):
        conn = self.connect_db()
        if not conn:
            return False
        try:
            return ensure_personnel_structure(conn)
        except Exception as e:
            messagebox.showerror("Structure Personnel", str(e))
            return False
        finally:
            conn.close()

    # ── En-tête compact ───────────────────────────────────────────────────────

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT,
                            corner_radius=0, height=46)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)

        left = ctk.CTkFrame(hdr, fg_color="transparent")
        left.grid(row=0, column=0, padx=14, pady=0, sticky="w")
        ctk.CTkLabel(left, text="👥", font=Fonts.heading(16),
                     text_color=Colors.TEXT_ON_DARK).pack(side="left", padx=(0, 8))
        inner = ctk.CTkFrame(left, fg_color="transparent")
        inner.pack(side="left")
        ctk.CTkLabel(inner, text="Gestion du Personnel",
                     font=Fonts.bold(13), text_color=Colors.TEXT_ON_DARK
                     ).pack(anchor="w")
        ctk.CTkLabel(inner, text="Ajout, modification et suppression",
                     font=Fonts.small(9), text_color=Colors.TEXT_ON_DARK_DIM
                     ).pack(anchor="w")

        ctk.CTkButton(hdr, text="➕  Nouveau", width=110, height=28,
                      fg_color=Colors.SUCCESS, hover_color=Colors.SUCCESS_DARK,
                      font=Fonts.bold(11), corner_radius=6,
                      command=self._ouvrir_modal_ajout,
                      ).grid(row=0, column=2, padx=(0, 8))
        ctk.CTkButton(hdr, text="Gérer Catégories", width=145, height=28,
                      fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
                      font=Fonts.bold(11), corner_radius=6,
                      command=self._ouvrir_categories_postes,
                      ).grid(row=0, column=3, padx=(0, 14))

    # ── Filtres compacts ──────────────────────────────────────────────────────

    def _build_filters(self):
        fb = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=8)
        fb.grid(row=1, column=0, padx=8, pady=(6, 3), sticky="ew")
        fb.grid_columnconfigure(1, weight=1)

        def lbl(text, col, padl=10):
            ctk.CTkLabel(fb, text=text, font=Fonts.label(10),
                         text_color=Colors.TEXT_SECONDARY
                         ).grid(row=0, column=col, padx=(padl, 4), pady=7, sticky="w")

        lbl("🔍 Recherche :", 0)
        self.entry_search = ctk.CTkEntry(
            fb, height=28, width=200,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            font=Fonts.body(11), corner_radius=6,
            placeholder_text="Nom, prénom, matricule…"
        )
        self.entry_search.grid(row=0, column=1, padx=(0, 12), pady=7, sticky="ew")
        self.entry_search.bind("<KeyRelease>", lambda e: self._apply_filters())

        lbl("Catégorie :", 2, 0)
        self.combo_filter_categorie = ctk.CTkComboBox(
            fb, values=["Toutes"], state="readonly",
            width=145, height=28,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            button_color=Colors.PRIMARY, font=Fonts.body(11),
            command=lambda v: self._on_filter_category_change(v)
        )
        self.combo_filter_categorie.set("Toutes")
        self.combo_filter_categorie.grid(row=0, column=3, padx=(0, 10), pady=7)

        lbl("Poste :", 4, 0)
        self.combo_filter_poste = ctk.CTkComboBox(
            fb, values=["Tous"], state="readonly",
            width=135, height=28,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            button_color=Colors.PRIMARY, font=Fonts.body(11),
            command=lambda v: self._apply_filters()
        )
        self.combo_filter_poste.set("Tous")
        self.combo_filter_poste.grid(row=0, column=5, padx=(0, 10), pady=7)

        lbl("Sexe :", 6, 0)
        self.combo_filter_sexe = ctk.CTkComboBox(
            fb, values=["Tous", "M", "F"], state="readonly",
            width=80, height=28,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            button_color=Colors.PRIMARY, font=Fonts.body(11),
            command=lambda v: self._apply_filters()
        )
        self.combo_filter_sexe.set("Tous")
        self.combo_filter_sexe.grid(row=0, column=7, padx=(0, 10), pady=7)

        ctk.CTkButton(fb, text="↺ Reset", width=78, height=28,
                      fg_color=Colors.CLOUDS, hover_color=Colors.SILVER,
                      text_color=Colors.TEXT_PRIMARY,
                      font=Fonts.bold(11), corner_radius=6,
                      border_width=1, border_color=Colors.BORDER,
                      command=self._reset_filters,
                      ).grid(row=0, column=8, padx=(0, 10), pady=7)

    # ── Tableau ───────────────────────────────────────────────────────────────

    def _build_table(self):
        card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=8)
        card.grid(row=2, column=0, padx=8, pady=(0, 3), sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        # Style Treeview compact
        st = ttk.Style()
        st.theme_use("clam")
        st.configure("P2.Treeview",
                     background=Colors.BG_CARD, foreground=Colors.TEXT_PRIMARY,
                     fieldbackground=Colors.BG_CARD, rowheight=26,
                     font=("Segoe UI", 10), borderwidth=0)
        st.configure("P2.Treeview.Heading",
                     background=Colors.MIDNIGHT, foreground=Colors.TEXT_ON_DARK,
                     font=("Segoe UI", 10, "bold"), relief="flat", padding=(6, 5))
        st.map("P2.Treeview",
               background=[("selected", Colors.PRIMARY_LIGHT)],
               foreground=[("selected", Colors.TEXT_PRIMARY)])
        st.map("P2.Treeview.Heading",
               background=[("active", Colors.MIDNIGHT_LIGHT)])

        cols = ("ID", "Matricule", "Nom", "Prénom", "Adresse",
                "CIN", "Contact", "Sexe", "Catégorie", "Poste")
        self.tree = ttk.Treeview(card, columns=cols, show="headings",
                                  style="P2.Treeview", selectmode="browse")
        for col, w, anc in [
            ("ID", 38, "center"), ("Matricule", 105, "w"),
            ("Nom", 125, "w"), ("Prénom", 115, "w"),
            ("Adresse", 145, "w"), ("CIN", 95, "center"),
            ("Contact", 105, "w"), ("Sexe", 48, "center"),
            ("Catégorie", 130, "w"), ("Poste", 150, "w"),
        ]:
            self.tree.heading(col, text=col,
                               command=lambda c=col: self._sort_by(c))
            self.tree.column(col, width=w, anchor=anc, minwidth=30)

        self.tree.tag_configure("even", background=Colors.BG_CARD)
        self.tree.tag_configure("odd",  background=Colors.BG_ROW_ALT)

        vsb = ttk.Scrollbar(card, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(card, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(4, 0), pady=4)
        vsb.grid(row=1, column=1, sticky="ns", pady=4)
        hsb.grid(row=2, column=0, sticky="ew", padx=(4, 0))
        self.tree.bind("<Double-1>", self._on_double_click)

        # Boutons sous tableau
        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=3, column=0, columnspan=2, padx=8, pady=(4, 8), sticky="w")

        ctk.CTkButton(actions, text="✏️  Modifier", width=100, height=28,
                      fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
                      font=Fonts.bold(11), corner_radius=6,
                      command=self._ouvrir_modal_modif,
                      ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(actions, text="🗑  Supprimer", width=108, height=28,
                      fg_color=Colors.DANGER, hover_color=Colors.DANGER_DARK,
                      font=Fonts.bold(11), corner_radius=6,
                      command=self._supprimer,
                      ).pack(side="left")

    # ── Status bar ────────────────────────────────────────────────────────────

    def _build_statusbar(self):
        bar = ctk.CTkFrame(self, fg_color=Colors.DIVIDER, corner_radius=0, height=24)
        bar.grid(row=3, column=0, sticky="ew")
        bar.grid_propagate(False)
        self.lbl_status = ctk.CTkLabel(bar, text="Chargement…",
                                        font=Fonts.small(9),
                                        text_color=Colors.TEXT_MUTED, anchor="w")
        self.lbl_status.pack(side="left", padx=12)

    # ── Données ───────────────────────────────────────────────────────────────

    def _load_category_poste_filters(self):
        if not self._personnel_structure_ready:
            self.combo_filter_categorie.configure(values=["Toutes", UNKNOWN_LABEL])
            self.combo_filter_poste.configure(values=["Tous", UNKNOWN_LABEL])
            return
        conn = self.connect_db()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT idcategorie, titre FROM tb_categoriepersonnel "
                "WHERE COALESCE(deleted,0)=0 ORDER BY titre"
            )
            cats = cur.fetchall()
            self._categorie_filter_map = {r[1]: r[0] for r in cats}
            self.combo_filter_categorie.configure(values=["Toutes", UNKNOWN_LABEL] + [r[1] for r in cats])
            self._load_poste_filter_values(conn)
        finally:
            conn.close()

    def _load_poste_filter_values(self, conn=None):
        if not self._personnel_structure_ready:
            self.combo_filter_poste.configure(values=["Tous", UNKNOWN_LABEL])
            self.combo_filter_poste.set("Tous")
            return
        close_conn = False
        if conn is None:
            conn = self.connect_db()
            close_conn = True
        if not conn:
            return
        try:
            cur = conn.cursor()
            selected_cat = self.combo_filter_categorie.get()
            if selected_cat == "Toutes":
                cur.execute(
                    "SELECT idposte, titre FROM tb_postepersonnel "
                    "WHERE COALESCE(deleted,0)=0 ORDER BY titre"
                )
            elif selected_cat == UNKNOWN_LABEL:
                self._poste_filter_map = {}
                self.combo_filter_poste.configure(values=["Tous", UNKNOWN_LABEL])
                self.combo_filter_poste.set("Tous")
                return
            else:
                cur.execute(
                    "SELECT idposte, titre FROM tb_postepersonnel "
                    "WHERE COALESCE(deleted,0)=0 AND idcategorie=%s ORDER BY titre",
                    (self._categorie_filter_map.get(selected_cat),),
                )
            rows = cur.fetchall()
            self._poste_filter_map = {r[1]: r[0] for r in rows}
            self.combo_filter_poste.configure(values=["Tous", UNKNOWN_LABEL] + [r[1] for r in rows])
            self.combo_filter_poste.set("Tous")
        finally:
            if close_conn:
                conn.close()

    def _on_filter_category_change(self, value):
        self._load_poste_filter_values()
        self._apply_filters()

    def load_personnels(self):
        conn = self.connect_db()
        if not conn: return
        try:
            cur = conn.cursor()
            if self._personnel_structure_ready and has_personnel_structure(conn):
                cur.execute(personnel_poste_select() + " ORDER BY p.nom, p.prenom")
            else:
                self._personnel_structure_ready = False
                cur.execute(
                    """SELECT p.id, p.matricule, p.nom, p.prenom, p.adresse,
                              p.cin, p.contact, p.sexe,
                              %s AS categorie, %s AS poste,
                              NULL AS idposte, NULL AS idcategorie
                       FROM tb_personnel p
                       WHERE COALESCE(p.deleted,0)=0
                       ORDER BY p.nom, p.prenom""",
                    (UNKNOWN_LABEL, UNKNOWN_LABEL),
                )
            self._all_rows = cur.fetchall()
        finally:
            conn.close()
        self._apply_filters()

    def _apply_filters(self):
        search   = self.entry_search.get().strip().lower()
        filtre_c = self.combo_filter_categorie.get()
        filtre_p = self.combo_filter_poste.get()
        filtre_s = self.combo_filter_sexe.get()
        for item in self.tree.get_children():
            self.tree.delete(item)
        count = 0
        for row in self._all_rows:
            pid, mat, nom, prenom, adr, cin, contact, sexe, categorie, poste, idposte, idcategorie = row
            if search:
                hay = f"{nom or ''} {prenom or ''} {mat or ''}".lower()
                if search not in hay: continue
            if filtre_c != "Toutes":
                if filtre_c == UNKNOWN_LABEL:
                    if categorie != UNKNOWN_LABEL: continue
                elif self._categorie_filter_map.get(filtre_c) != idcategorie:
                    continue
            if filtre_p != "Tous":
                if filtre_p == UNKNOWN_LABEL:
                    if poste != UNKNOWN_LABEL: continue
                elif self._poste_filter_map.get(filtre_p) != idposte:
                    continue
            if filtre_s != "Tous" and sexe != filtre_s: continue
            v = lambda x: x if x else "-"
            tag = "even" if count % 2 == 0 else "odd"
            self.tree.insert("", "end", iid=str(pid), tags=(tag,),
                              values=(pid, v(mat), v(nom), v(prenom),
                                      v(adr), v(cin), v(contact), v(sexe),
                                      v(categorie), v(poste)))
            count += 1
        self.lbl_status.configure(
            text=f"  {count} personnel(s) affiché(s) sur {len(self._all_rows)} au total")

    def _reset_filters(self):
        self.entry_search.delete(0, "end")
        self.combo_filter_categorie.set("Toutes")
        self.combo_filter_poste.set("Tous")
        self.combo_filter_sexe.set("Tous")
        self._load_poste_filter_values()
        self._apply_filters()

    # ── Tri ───────────────────────────────────────────────────────────────────

    _sort_state = {}

    def _sort_by(self, col):
        col_idx = {"ID": 0, "Matricule": 1, "Nom": 2, "Prénom": 3,
                   "Adresse": 4, "CIN": 5, "Contact": 6, "Sexe": 7,
                   "Catégorie": 8, "Poste": 9}
        reverse = self._sort_state.get(col, False)
        self._sort_state[col] = not reverse
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        data.sort(key=lambda t: t[0].lower(), reverse=reverse)
        for i, (_, k) in enumerate(data):
            self.tree.move(k, "", i)
            self.tree.item(k, tags=("even" if i % 2 == 0 else "odd",))

    # ── Actions ───────────────────────────────────────────────────────────────

    def _get_selected_data(self):
        sel = self.tree.selection()
        if not sel: return None
        pid = self.tree.item(sel[0])["values"][0]
        for row in self._all_rows:
            if row[0] == pid:
                return {"id": row[0], "matricule": row[1], "nom": row[2],
                        "prenom": row[3], "adresse": row[4], "cin": row[5],
                        "contact": row[6], "sexe": row[7], "categorie": row[8],
                        "poste": row[9], "idposte": row[10], "idcategorie": row[11]}
        return None

    def _generer_matricule(self):
        conn = self.connect_db()
        if not conn: return ""
        try:
            cur = conn.cursor()
            annee = datetime.now().year
            cur.execute("SELECT matricule FROM tb_personnel WHERE matricule LIKE %s "
                        "ORDER BY id DESC LIMIT 1", (f"{annee}-P-%",))
            last = cur.fetchone()
            num  = 1
            if last:
                try: num = int(last[0].split("-")[-1]) + 1
                except: num = 1
            return f"{annee}-P-{num:05d}"
        finally:
            conn.close()

    def _ouvrir_modal_ajout(self):
        mat   = self._generer_matricule()
        modal = ModalPersonnel(self, on_save=self.load_personnels,
                                db_conn_fn=self.connect_db, mode="ajout")
        modal.entry_matricule.configure(state="normal")
        modal.entry_matricule.delete(0, "end")
        modal.entry_matricule.insert(0, mat)
        modal.entry_matricule.configure(state="readonly")

    def _ouvrir_categories_postes(self):
        ModalCategoriesPostes(
            self,
            db_conn_fn=self.connect_db,
            on_close=lambda: (self._load_category_poste_filters(), self.load_personnels()),
        )

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
        if not messagebox.askyesno("Confirmation",
                                    f"Supprimer « {data.get('nom', '')} » ?\n"
                                    "Cette action est irréversible."):
            return
        conn = self.connect_db()
        if not conn: return
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

if __name__ == "__main__":
    from app_theme import Theme
    Theme.setup()
    root = ctk.CTk()
    root.title("Personnel — test")
    root.geometry("1150x680")
    Theme.apply(root)
    PagePeronnelAjout(root).pack(fill="both", expand=True)
    root.mainloop()
