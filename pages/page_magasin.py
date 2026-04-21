import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime
import json
import os
from resource_utils import get_config_path, safe_file_read
from log_utils import AppLogger

# ── Thème iJeery ──────────────────────────────────────────────────────────────
try:
    from app_theme import Colors, Fonts, styled, Theme
    _T = True
except ImportError:
    _T = False


class _C:
    MIDNIGHT       = "#2C3E50"
    BG_PAGE        = "#ECF0F1"
    BG_CARD        = "#FFFFFF"
    BG_HEADER      = "#2C3E50"
    BG_INPUT       = "#F4F6F8"
    PRIMARY        = "#3498DB"
    PRIMARY_HOVER  = "#2980B9"
    SUCCESS        = "#2ECC71"
    SUCCESS_DARK   = "#27AE60"
    DANGER         = "#E74C3C"
    DANGER_DARK    = "#C0392B"
    TEXT_PRIMARY   = "#2C3E50"
    TEXT_SECONDARY = "#5D6D7E"
    TEXT_MUTED     = "#95A5A6"
    BORDER         = "#D5D8DC"
    DIVIDER        = "#E8EAED"


C = Colors if _T else _C


def _apply_tree_style():
    s = ttk.Style()
    try:
        s.theme_use("clam")
    except Exception:
        pass
    s.configure("Mag.Treeview",
                 background=C.BG_CARD, foreground=C.TEXT_PRIMARY,
                 fieldbackground=C.BG_CARD, rowheight=24,
                 font=("Roboto" if _T else "Segoe UI", 10),
                 borderwidth=0)
    s.configure("Mag.Treeview.Heading",
                 background=C.BG_HEADER, foreground="#FFFFFF",
                 font=("Roboto" if _T else "Segoe UI", 10, "bold"),
                 relief="flat", padding=(6, 4))
    s.map("Mag.Treeview",
          background=[("selected", C.PRIMARY)],
          foreground=[("selected", "#FFFFFF")])


def _f(size=11, weight="normal"):
    return ctk.CTkFont(
        family="Roboto" if _T else "Segoe UI",
        size=size, weight=weight)


# ====================================================================
# PageMagasin
# ====================================================================

class PageMagasin(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master, fg_color=C.BG_PAGE)

        self.conn = self.connect_db()
        if self.conn:
            self.cursor = self.conn.cursor()
            self.create_table()

        self.selected_mag_id = None
        self.session_data = getattr(master, "session_data", None) or {}
        self._logger = AppLogger(conn=self.conn, session_data=self.session_data)

        _apply_tree_style()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_form_card()
        self._build_treeview()

        self.load_magasin()

    # ── helper font ──────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=C.BG_HEADER, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            hdr, text="Gestion des Dépôts / Magasins",
            font=_f(18, "bold"), text_color="#FFFFFF"
        ).pack(side="left", padx=16, pady=10)

    def _build_form_card(self):
        card = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=8)
        card.grid(row=1, column=0, sticky="ew", padx=12, pady=6)
        card.grid_columnconfigure(1, weight=1)
        card.grid_columnconfigure(3, weight=1)

        # ── Champs ────────────────────────────────────────────────────────
        ctk.CTkLabel(card, text="Nom du dépôt :", font=_f(10),
                     text_color=C.TEXT_SECONDARY, anchor="w", width=100
                     ).grid(row=0, column=0, padx=(12, 6), pady=(12, 4), sticky="w")
        self.designationmag_entry = ctk.CTkEntry(
            card, placeholder_text="Ex : Dépôt Central",
            font=_f(10), fg_color=C.BG_INPUT,
            border_color=C.BORDER, text_color=C.TEXT_PRIMARY, height=30)
        self.designationmag_entry.grid(
            row=0, column=1, padx=(0, 16), pady=(12, 4), sticky="ew")

        ctk.CTkLabel(card, text="Adresse :", font=_f(10),
                     text_color=C.TEXT_SECONDARY, anchor="w", width=70
                     ).grid(row=0, column=2, padx=(0, 6), pady=(12, 4), sticky="w")
        self.adressemag_entry = ctk.CTkEntry(
            card, placeholder_text="Ex : Lot II C Tanà",
            font=_f(10), fg_color=C.BG_INPUT,
            border_color=C.BORDER, text_color=C.TEXT_PRIMARY, height=30)
        self.adressemag_entry.grid(
            row=0, column=3, padx=(0, 12), pady=(12, 4), sticky="ew")

        # ── Boutons pleine largeur ────────────────────────────────────────
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.grid(row=1, column=0, columnspan=4,
                     padx=12, pady=(6, 12), sticky="ew")
        btn_row.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkButton(
            btn_row, text="➕  Ajouter", command=self.add_magasin,
            fg_color=C.SUCCESS_DARK, hover_color=C.SUCCESS,
            text_color="#FFFFFF", height=32, font=_f(10, "bold")
        ).grid(row=0, column=0, padx=(0, 4), sticky="ew")

        ctk.CTkButton(
            btn_row, text="✏️  Modifier", command=self.modify_magasin,
            fg_color=C.PRIMARY, hover_color=C.PRIMARY_HOVER,
            text_color="#FFFFFF", height=32, font=_f(10, "bold")
        ).grid(row=0, column=1, padx=4, sticky="ew")

        ctk.CTkButton(
            btn_row, text="🗑  Supprimer", command=self.delete_magasin,
            fg_color=C.DANGER, hover_color=C.DANGER_DARK,
            text_color="#FFFFFF", height=32, font=_f(10, "bold")
        ).grid(row=0, column=2, padx=4, sticky="ew")

        ctk.CTkButton(
            btn_row, text="Vider", command=self.clear_fields,
            fg_color="transparent", hover_color=C.DIVIDER,
            text_color=C.TEXT_SECONDARY,
            border_width=1, border_color=C.BORDER,
            height=32, font=_f(10)
        ).grid(row=0, column=3, padx=(4, 0), sticky="ew")

    def _build_treeview(self):
        tbl = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=8)
        tbl.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 8))
        tbl.grid_rowconfigure(0, weight=1)
        tbl.grid_columnconfigure(0, weight=1)

        columns = ("Nom du dépôt", "Adresse")
        self.tree = ttk.Treeview(tbl, columns=columns, show="headings",
                                 style="Mag.Treeview", height=14)
        self.tree.tag_configure("even", background=C.BG_CARD)
        self.tree.tag_configure("odd",  background="#F0F4F8")

        self.tree.heading("Nom du dépôt", text="Nom du dépôt")
        self.tree.heading("Adresse",      text="Adresse")
        self.tree.column("Nom du dépôt",  width=250, anchor="w")
        self.tree.column("Adresse",       width=300, anchor="w", stretch=True)

        sy = ctk.CTkScrollbar(tbl, orientation="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sy.set)

        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        sy.grid(row=0, column=1, sticky="ns", pady=6)

        self.tree.bind("<<TreeviewSelect>>", self.on_select)

    # ====================================================================
    # LOGIQUE MÉTIER — inchangée
    # ====================================================================

    def connect_db(self):
        try:
            if not os.path.exists(get_config_path('config.json')):
                messagebox.showerror("Erreur de configuration",
                                     "Le fichier config.json est manquant.")
                return None
            with open(get_config_path('config.json')) as f:
                config = json.load(f)
                db_config = config['database']
            conn = psycopg2.connect(
                host=db_config['host'], user=db_config['user'],
                password=db_config['password'],
                database=db_config['database'], port=db_config['port'])
            return conn
        except psycopg2.Error as err:
            messagebox.showerror("Erreur de connexion", f"Erreur : {err}")
        except UnicodeDecodeError as err:
            messagebox.showerror("Erreur d'encodage", f"Problème d'encodage : {err}")
        except KeyError as err:
            messagebox.showerror("Erreur de configuration",
                                 f"Clé manquante dans config.json : {err}")
        return None

    def create_table(self):
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS tb_magasin (
                    idMag SERIAL PRIMARY KEY,
                    designationMag VARCHAR(50),
                    adresseMag VARCHAR(50),
                    livraison INT,
                    deleted INT
                )
            """)
            self.conn.commit()
        except psycopg2.Error as err:
            messagebox.showerror("Erreur",
                                 f"Erreur lors de la création de la table : {err}")

    def load_magasin(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        if not self.conn:
            return
        try:
            self.cursor.execute("""
                SELECT m.idmag, m.designationmag, m.adressemag
                FROM tb_magasin m
                ORDER BY m.designationmag DESC
            """)
            magasins = self.cursor.fetchall()
            for idx, mag in enumerate(magasins):
                tag = "even" if idx % 2 == 0 else "odd"
                self.tree.insert("", "end", iid=mag[0],
                                 values=(mag[1], mag[2]), tags=(tag,))
        except psycopg2.Error as err:
            messagebox.showerror("Erreur",
                                 f"Erreur lors du chargement des dépôts : {err}")

    def add_magasin(self):
        if not self.conn:
            messagebox.showerror("Erreur", "Connexion à la base de données perdue.")
            return
        try:
            designationmag = self.designationmag_entry.get()
            adressemag     = self.adressemag_entry.get()
            if not all([designationmag, adressemag]):
                messagebox.showwarning("Attention", "Tous les champs sont obligatoires.")
                return
            self.cursor.execute("""
                INSERT INTO tb_magasin (designationmag, adressemag)
                VALUES (%s, %s) RETURNING idmag
            """, (designationmag, adressemag))
            self.conn.commit()
            self.load_magasin()
            self.clear_fields()
            messagebox.showinfo("Succès", "Dépôt ajouté avec succès!")
            try:
                self._logger.log(
                    action="Création du dépôt/magasin",
                    element=designationmag,
                    details=f"Ajout dépôt, adresse='{adressemag}'",
                    value="aucune valeur",
                )
            except Exception:
                pass
        except psycopg2.Error as err:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de l'ajout : {err}")

    def modify_magasin(self):
        if not self.conn:
            messagebox.showerror("Erreur", "Connexion à la base de données perdue.")
            return
        if not self.selected_mag_id:
            messagebox.showwarning("Attention",
                                   "Veuillez sélectionner un dépôt à modifier.")
            return
        try:
            old_name = ""
            try:
                self.cursor.execute("SELECT designationmag FROM tb_magasin WHERE idmag=%s", (self.selected_mag_id,))
                r = self.cursor.fetchone()
                old_name = r[0] if r and r[0] else ""
            except Exception:
                old_name = ""
            designationmag = self.designationmag_entry.get()
            adressemag     = self.adressemag_entry.get()
            if not all([designationmag, adressemag]):
                messagebox.showwarning("Attention", "Tous les champs sont obligatoires.")
                return
            self.cursor.execute("""
                UPDATE tb_magasin
                SET designationmag = %s, adressemag = %s
                WHERE idmag = %s
            """, (designationmag, adressemag, self.selected_mag_id))
            self.conn.commit()
            self.load_magasin()
            self.clear_fields()
            messagebox.showinfo("Succès", "Dépôt modifié avec succès!")
            try:
                self._logger.log(
                    action="Modification du dépôt/magasin",
                    element=old_name or f"idmag={self.selected_mag_id}",
                    details=f"Dépôt modifié en '{designationmag}', adresse='{adressemag}'",
                    value=f"idmag={self.selected_mag_id}",
                )
            except Exception:
                pass
        except psycopg2.Error as err:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de la modification : {err}")

    def delete_magasin(self):
        if not self.conn:
            messagebox.showerror("Erreur", "Connexion à la base de données perdue.")
            return
        if not self.selected_mag_id:
            messagebox.showwarning("Attention",
                                   "Veuillez sélectionner un dépôt à supprimer.")
            return
        if not messagebox.askyesno("Confirmation",
                                    "Voulez-vous vraiment supprimer ce dépôt ?"):
            return
        try:
            mag_name = ""
            try:
                self.cursor.execute("SELECT designationmag FROM tb_magasin WHERE idmag=%s", (self.selected_mag_id,))
                r = self.cursor.fetchone()
                mag_name = r[0] if r and r[0] else ""
            except Exception:
                mag_name = ""
            self.cursor.execute(
                "DELETE FROM tb_magasin WHERE idmag = %s",
                (self.selected_mag_id,))
            self.conn.commit()
            self.load_magasin()
            self.clear_fields()
            messagebox.showinfo("Succès", "Dépôt supprimé avec succès!")
            try:
                self._logger.log(
                    action="Suppression du dépôt/magasin",
                    element=mag_name or f"idmag={self.selected_mag_id}",
                    details="Suppression dépôt (CRUD Magasin)",
                    value=f"idmag={self.selected_mag_id}",
                )
            except Exception:
                pass
        except psycopg2.Error as err:
            self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de la suppression : {err}")

    def on_select(self, event):
        if not self.conn:
            return
        selected = self.tree.selection()
        if not selected:
            self.clear_fields()
            return
        selected_iid = selected[0]
        mag_id       = selected_iid
        if not mag_id:
            self.clear_fields()
            return
        try:
            self.cursor.execute("""
                SELECT m.idmag, m.designationmag, m.adressemag
                FROM tb_magasin m WHERE m.idmag = %s
            """, (mag_id,))
            magasin = self.cursor.fetchone()
            if magasin:
                self.selected_mag_id = magasin[0]
                self.designationmag_entry.delete(0, "end")
                self.designationmag_entry.insert(0, magasin[1])
                self.adressemag_entry.delete(0, "end")
                self.adressemag_entry.insert(0, magasin[2])
            else:
                self.clear_fields()
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Erreur lors de la sélection : {err}")

    def clear_fields(self):
        self.designationmag_entry.delete(0, "end")
        self.adressemag_entry.delete(0, "end")
        self.selected_mag_id = None

    def __del__(self):
        if hasattr(self, 'conn') and self.conn:
            self.cursor.close()
            self.conn.close()


# ── Test standalone ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("iJeery — Gestion des Dépôts")
    app.geometry("700x520")
    if _T:
        Theme.apply(app)
    app.grid_rowconfigure(0, weight=1)
    app.grid_columnconfigure(0, weight=1)
    PageMagasin(app).grid(row=0, column=0, sticky="nsew")
    app.mainloop()