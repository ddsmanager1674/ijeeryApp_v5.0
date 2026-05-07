import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import psycopg2
import json
import os
import sys
from resource_utils import get_config_path, safe_file_read

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


# ── Style Treeview ────────────────────────────────────────────────────────────
def _apply_tree_style():
    s = ttk.Style()
    try:
        s.theme_use("clam")
    except Exception:
        pass
    s.configure("Cat.Treeview",
                 background=C.BG_CARD, foreground=C.TEXT_PRIMARY,
                 fieldbackground=C.BG_CARD, rowheight=26,
                 font=("Roboto" if _T else "Segoe UI", 10),
                 borderwidth=0)
    s.configure("Cat.Treeview.Heading",
                 background=C.BG_HEADER, foreground="#FFFFFF",
                 font=("Roboto" if _T else "Segoe UI", 10, "bold"),
                 relief="flat", padding=(6, 4))
    s.map("Cat.Treeview",
          background=[("selected", C.PRIMARY)],
          foreground=[("selected", "#FFFFFF")])


# ====================================================================
# PageCategorieArticle
# ====================================================================

class PageCategorieArticle(ctk.CTkFrame):

    def __init__(self, parent):
        super().__init__(parent, fg_color=C.BG_PAGE)

        self.conn = self.connect_db()
        if self.conn:
            self.cursor = self.conn.cursor()
            self.initialiser_table()
        else:
            return

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        _apply_tree_style()
        self._build_header()
        self._build_form_card()
        self._build_treeview()

        self.charger_categoriearticle()

    # ── helper font ──────────────────────────────────────────────────────────
    def _f(self, size=11, weight="normal"):
        return ctk.CTkFont(
            family="Roboto" if _T else "Segoe UI",
            size=size, weight=weight)

    # ── En-tête ───────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=C.BG_HEADER, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            hdr, text="Gestion des Catégories",
            font=self._f(18, "bold"), text_color="#FFFFFF"
        ).pack(side="left", padx=16, pady=10)

    # ── Card formulaire ───────────────────────────────────────────────────────
    def _build_form_card(self):
        card = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=8)
        card.grid(row=1, column=0, sticky="ew", padx=12, pady=6)
        card.grid_columnconfigure(1, weight=1)

        # Champ désignation
        ctk.CTkLabel(
            card, text="Désignation :",
            font=self._f(10), text_color=C.TEXT_SECONDARY, anchor="w"
        ).grid(row=0, column=0, padx=(12, 8), pady=(14, 4), sticky="w")

        self.entry_designationcat = ctk.CTkEntry(
            card,
            placeholder_text="Nom de la catégorie…",
            font=self._f(10),
            fg_color=C.BG_INPUT, border_color=C.BORDER,
            text_color=C.TEXT_PRIMARY, height=32)
        self.entry_designationcat.grid(
            row=0, column=1, padx=(0, 12), pady=(14, 4), sticky="ew")
        self.entry_designationcat.bind(
            "<KeyRelease>", self.rechercher_categorie_auto)

        # Boutons
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.grid(row=1, column=0, columnspan=2,
                     padx=12, pady=(6, 14), sticky="w")

        btn_specs = [
            ("Enregistrer", self.enregistrer,  C.SUCCESS_DARK, C.SUCCESS,      "#FFFFFF"),
            ("Modifier",    self.modifier,     C.PRIMARY,      C.PRIMARY_HOVER,"#FFFFFF"),
            ("Supprimer",   self.supprimer,    C.DANGER,       C.DANGER_DARK,  "#FFFFFF"),
            ("Vider",       self.vider,        "transparent",  C.DIVIDER,      C.TEXT_SECONDARY),
        ]
        for text, cmd, fg, hov, tc in btn_specs:
            kw = dict(border_width=1, border_color=C.BORDER) \
                 if fg == "transparent" else {}
            ctk.CTkButton(
                btn_row, text=text, command=cmd,
                fg_color=fg, hover_color=hov, text_color=tc,
                width=110, height=32, font=self._f(10, "bold"), **kw
            ).pack(side="left", padx=(0, 6))

    # ── Treeview ──────────────────────────────────────────────────────────────
    def _build_treeview(self):
        tbl = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=8)
        tbl.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 8))
        tbl.grid_rowconfigure(0, weight=1)
        tbl.grid_columnconfigure(0, weight=1)

        cols = ("idca", "designationcat")
        self.treeview = ttk.Treeview(
            tbl, columns=cols, show="headings",
            style="Cat.Treeview", height=14)

        self.treeview.tag_configure("even", background=C.BG_CARD)
        self.treeview.tag_configure("odd",  background="#F0F4F8")

        self.treeview.heading("idca",          text="ID")
        self.treeview.heading("designationcat",text="Désignation")
        self.treeview.column("idca",           width=60,  anchor="center", stretch=False)
        self.treeview.column("designationcat", width=200, anchor="w",      stretch=True)

        sy = ctk.CTkScrollbar(tbl, orientation="vertical",
                               command=self.treeview.yview)
        self.treeview.configure(yscrollcommand=sy.set)

        self.treeview.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        sy.grid(row=0, column=1, sticky="ns", pady=6)

        self.treeview.bind("<<TreeviewSelect>>", self.remplir_champs)

    # ====================================================================
    # LOGIQUE MÉTIER — inchangée
    # ====================================================================

    def connect_db(self):
        try:
            if not os.path.exists(get_config_path('config.json')):
                messagebox.showerror("Erreur", "Fichier config.json manquant.")
                return None
            with open(get_config_path('config.json')) as f:
                config = json.load(f)
                db_config = config['database']
            conn = psycopg2.connect(
                host=db_config['host'], user=db_config['user'],
                password=db_config['password'],
                database=db_config['database'], port=db_config['port'])
            return conn
        except Exception as err:
            messagebox.showerror("Erreur de connexion", f"Détails : {err}")
            return None

    def initialiser_table(self):
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS tb_categoriearticle (
                    idca INTEGER PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
                    designationcat VARCHAR(75)
                )
            """)
            self.conn.commit()
            self.cursor.execute("""
                SELECT setval(pg_get_serial_sequence('tb_categoriearticle','idca'),
                              COALESCE((SELECT MAX(idca) FROM tb_categoriearticle),0)+1,
                              false);
            """)
            self.conn.commit()
        except psycopg2.Error as err:
            messagebox.showerror("Erreur SQL", f"Erreur table : {err}")

    def charger_categoriearticle(self, filtre=""):
        for i in self.treeview.get_children():
            self.treeview.delete(i)
        try:
            if filtre:
                self.cursor.execute(
                    "SELECT idca, designationcat FROM tb_categoriearticle "
                    "WHERE LOWER(designationcat) LIKE LOWER(%s) ORDER BY idca",
                    (f"%{filtre}%",))
            else:
                self.cursor.execute(
                    "SELECT idca, designationcat "
                    "FROM tb_categoriearticle ORDER BY idca")
            for idx, row in enumerate(self.cursor.fetchall()):
                tag = "even" if idx % 2 == 0 else "odd"
                self.treeview.insert('', 'end', values=row, tags=(tag,))
        except Exception as e:
            print(f"Erreur de chargement: {e}")

    def rechercher_categorie_auto(self, event=None):
        filtre = self.entry_designationcat.get().strip()
        self.charger_categoriearticle(filtre=filtre)

    def enregistrer(self):
        designation = self.entry_designationcat.get().strip()
        if not designation:
            return
        try:
            self.cursor.execute(
                "INSERT INTO tb_categoriearticle (designationcat) VALUES (%s)",
                (designation,))
            self.conn.commit()
            self.charger_categoriearticle()
            self.vider()
            messagebox.showinfo("Succès", "Catégorie enregistrée !")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def modifier(self):
        selected = self.treeview.selection()
        if not selected:
            return
        idca        = self.treeview.item(selected[0])['values'][0]
        designation = self.entry_designationcat.get().strip()
        try:
            self.cursor.execute(
                "UPDATE tb_categoriearticle SET designationcat=%s "
                "WHERE idca=%s", (designation, idca))
            self.conn.commit()
            self.charger_categoriearticle()
            self.vider()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def supprimer(self):
        selected = self.treeview.selection()
        if not selected:
            return
        if messagebox.askyesno("Confirmation", "Supprimer cette catégorie ?"):
            idca = self.treeview.item(selected[0])['values'][0]
            self.cursor.execute(
                "DELETE FROM tb_categoriearticle WHERE idca=%s", (idca,))
            self.conn.commit()
            self.charger_categoriearticle()
            self.vider()

    def remplir_champs(self, event):
        selected = self.treeview.selection()
        if selected:
            values = self.treeview.item(selected[0])['values']
            self.entry_designationcat.delete(0, tk.END)
            self.entry_designationcat.insert(0, values[1])

    def vider(self):
        self.entry_designationcat.delete(0, tk.END)
        self.treeview.selection_remove(self.treeview.selection())

        # Badge d'export ajoute automatiquement via export_utils.enable_treeview_export_badge()


# ── Test standalone ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    app = ctk.CTk()
    app.title("iJeery — Gestion des Catégories")
    app.geometry("520x560")
    if _T:
        Theme.apply(app)
    app.grid_rowconfigure(0, weight=1)
    app.grid_columnconfigure(0, weight=1)
    PageCategorieArticle(app).grid(row=0, column=0, sticky="nsew")
    app.mainloop()
