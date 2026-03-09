import customtkinter as ctk
from tkinter import messagebox, ttk
import psycopg2
import json
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
    WARNING        = "#F39C12"
    WARNING_LIGHT_C= "#F1C40F"
    WARNING_LIGHT  = "#FEF9E7"
    WARNING_TEXT   = "#9A6A00"
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
    s.configure("Unite.Treeview",
                 background=C.BG_CARD, foreground=C.TEXT_PRIMARY,
                 fieldbackground=C.BG_CARD, rowheight=24,
                 font=("Roboto" if _T else "Segoe UI", 10),
                 borderwidth=0)
    s.configure("Unite.Treeview.Heading",
                 background=C.BG_HEADER, foreground="#FFFFFF",
                 font=("Roboto" if _T else "Segoe UI", 10, "bold"),
                 relief="flat", padding=(6, 4))
    s.map("Unite.Treeview",
          background=[("selected", C.PRIMARY)],
          foreground=[("selected", "#FFFFFF")])


# ====================================================================
# DBConnector — inchangé
# ====================================================================

class DBConnector:
    """Connecteur de base de données pour les unités."""
    def __init__(self, db_conn=None):
        self.db_conn = db_conn

    @staticmethod
    def connect_db():
        try:
            with open(get_config_path('config.json')) as f:
                config = json.load(f)
                db_config = config['database']
            conn = psycopg2.connect(
                host=db_config['host'], user=db_config['user'],
                password=db_config['password'],
                database=db_config['database'], port=db_config['port'])
            return conn
        except FileNotFoundError:
            messagebox.showerror("Erreur de configuration",
                                 "Fichier 'config.json' non trouvé.")
        except KeyError:
            messagebox.showerror("Erreur de configuration",
                                 "Clés de base de données manquantes.")
        except psycopg2.Error as err:
            messagebox.showerror("Erreur de connexion", str(err))
        except UnicodeDecodeError as err:
            messagebox.showerror("Erreur d'encodage", str(err))
        return None


def synchroniser_sequence_unite(self):
    conn = self.connect_db()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT setval(pg_get_serial_sequence('tb_unite','idunite'),
                          COALESCE((SELECT MAX(idunite) FROM tb_unite),0)+1,
                          false);
        """)
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"Erreur synchro sequence: {e}")
    finally:
        conn.close()


# ====================================================================
# PageUnite
# ====================================================================

class PageUnite(ctk.CTkFrame):
    """Frame gestion des unités — intégration dans page_infoArticle."""

    def __init__(self, master, db_connector=None, initial_idarticle=None):
        super().__init__(master, fg_color=C.BG_PAGE)

        self.id_article   = initial_idarticle
        self.db_connector = db_connector

        _apply_tree_style()

        if not self.id_article:
            self._build_no_article()
            return

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_form_card()
        self._build_treeview()
        self.charger_unites()

    # ── helper font ──────────────────────────────────────────────────────────
    def _f(self, size=11, weight="normal"):
        return ctk.CTkFont(
            family="Roboto" if _T else "Segoe UI",
            size=size, weight=weight)

    # ── Aucun article ─────────────────────────────────────────────────────────
    def _build_no_article(self):
        warn = ctk.CTkFrame(self, fg_color="#FEF9E7",
                            corner_radius=10, border_color="#F39C12",
                            border_width=1)
        warn.pack(pady=40, padx=20, fill="x")
        ctk.CTkLabel(
            warn, text="⚠️  Aucun article sélectionné",
            font=self._f(16, "bold"), text_color="#9A6A00"
        ).pack(pady=20)

    # ── En-tête ───────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=C.BG_HEADER, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            hdr,
            text=f"Unités — Article #{self.id_article}",
            font=self._f(16, "bold"), text_color="#FFFFFF"
        ).pack(side="left", padx=16, pady=10)

    # ── Card formulaire ───────────────────────────────────────────────────────
    def _build_form_card(self):
        card = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=8)
        card.grid(row=1, column=0, sticky="ew", padx=12, pady=6)
        card.grid_columnconfigure(1, weight=1)

        # ── Champs — 1 par ligne ──────────────────────────────────────────────
        ctk.CTkLabel(card, text="Désignation :", font=self._f(10), text_color=C.TEXT_SECONDARY, anchor="w", width=90).grid(row=0, column=0, padx=(12, 6), pady=(12, 4), sticky="w")
        self.entry_designation = ctk.CTkEntry(card, placeholder_text="Ex : Carton de 12", font=self._f(10), fg_color=C.BG_INPUT, border_color=C.BORDER, text_color=C.TEXT_PRIMARY, height=30)
        self.entry_designation.grid(row=0, column=1, padx=(0, 12), pady=(12, 4), sticky="ew")

        ctk.CTkLabel(card, text="Quantité :", font=self._f(10), text_color=C.TEXT_SECONDARY, anchor="w", width=90).grid(row=1, column=0, padx=(12, 6), pady=4, sticky="w")
        self.entry_quantite = ctk.CTkEntry(card, placeholder_text="Ex : 12", font=self._f(10), fg_color=C.BG_INPUT, border_color=C.BORDER, text_color=C.TEXT_PRIMARY, height=30)
        self.entry_quantite.grid(row=1, column=1, padx=(0, 12), pady=4, sticky="ew")

        ctk.CTkLabel(card, text="Poids (kg) :", font=self._f(10), text_color=C.TEXT_SECONDARY, anchor="w", width=90).grid(row=2, column=0, padx=(12, 6), pady=4, sticky="w")
        self.entry_poids = ctk.CTkEntry(card, placeholder_text="Ex : 5.5", font=self._f(10), fg_color=C.BG_INPUT, border_color=C.BORDER, text_color=C.TEXT_PRIMARY, height=30)
        self.entry_poids.grid(row=2, column=1, padx=(0, 12), pady=4, sticky="ew")

        # ── Boutons — pleine largeur ──────────────────────────────────────────
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.grid(row=3, column=0, columnspan=2, padx=12, pady=(8, 12), sticky="ew")
        btn_row.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(btn_row, text="➕  Ajouter",   command=self.ajouter_unite,   fg_color=C.SUCCESS_DARK, hover_color=C.SUCCESS,     text_color="#FFFFFF", height=34, font=self._f(10, "bold")).grid(row=0, column=0, padx=(0, 4), sticky="ew")
        ctk.CTkButton(btn_row, text="✏️  Modifier",  command=self.modifier_unite,  fg_color=C.WARNING,      hover_color="#E67E22",      text_color="#FFFFFF", height=34, font=self._f(10, "bold")).grid(row=0, column=1, padx=4,      sticky="ew")
        ctk.CTkButton(btn_row, text="🗑  Supprimer", command=self.supprimer_unite, fg_color=C.DANGER,       hover_color=C.DANGER_DARK,  text_color="#FFFFFF", height=34, font=self._f(10, "bold")).grid(row=0, column=2, padx=(4, 0), sticky="ew")
    # ── Treeview ──────────────────────────────────────────────────────────────
    def _build_treeview(self):
        tbl = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=8)
        tbl.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 8))
        tbl.grid_rowconfigure(0, weight=1)
        tbl.grid_columnconfigure(0, weight=1)

        cols = ("idunite", "designationunite", "niveau",
                "qtunite", "poids", "codearticle")

        self.tree = ttk.Treeview(
            tbl, columns=cols, show="headings",
            style="Unite.Treeview", height=12)

        self.tree.tag_configure("even", background=C.BG_CARD)
        self.tree.tag_configure("odd",  background="#F0F4F8")
        self.tree.tag_configure("data", background=C.BG_CARD)

        col_cfg = {
            "idunite":         ("ID Unité",    80,  "center", False),
            "designationunite":("Désignation", 0,   "w",      True),
            "niveau":          ("Niveau",      70,  "center", False),
            "qtunite":         ("Quantité",    90,  "e",      False),
            "poids":           ("Poids (kg)",  90,  "e",      False),
            "codearticle":     ("Code Article",140, "center", False),
        }
        for col, (head, w, anc, stretch) in col_cfg.items():
            self.tree.heading(col, text=head)
            self.tree.column(col, width=w if w else 180, anchor=anc,
                             stretch=stretch, minwidth=50)

        sy = ctk.CTkScrollbar(tbl, orientation="vertical",
                               command=self.tree.yview)
        self.tree.configure(yscrollcommand=sy.set)

        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        sy.grid(row=0, column=1, sticky="ns", pady=6)

        self.tree.bind("<<TreeviewSelect>>", self.on_unite_select)

    # ====================================================================
    # LOGIQUE MÉTIER — inchangée
    # ====================================================================

    def connect_db(self):
        return DBConnector.connect_db()

    def charger_unites(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT idunite, designationunite, niveau,
                       qtunite, poids, codearticle
                FROM tb_unite
                WHERE idarticle = %s AND deleted = 0
                ORDER BY niveau
            """, (self.id_article,))
            records = cursor.fetchall()
            if not records:
                self.tree.insert('', 'end',
                                 values=("", "Aucune unité trouvée",
                                         "", "", "", ""))
            else:
                for idx, row in enumerate(records):
                    tag = "even" if idx % 2 == 0 else "odd"
                    self.tree.insert('', 'end', values=(
                        row[0], row[1], row[2],
                        f"{row[3]:.2f}", f"{row[4]:.2f}", row[5]
                    ), tags=(tag,))
            cursor.close()
        except psycopg2.Error as e:
            messagebox.showerror("Erreur DB",
                                 f"Erreur chargement unités : {e}")
        finally:
            if conn:
                conn.close()

    def on_unite_select(self, event):
        selected_item = self.tree.focus()
        if selected_item:
            values = self.tree.item(selected_item, 'values')
            if values and values[0]:
                self.entry_designation.delete(0, 'end')
                self.entry_quantite.delete(0, 'end')
                self.entry_poids.delete(0, 'end')
                self.entry_designation.insert(0, values[1])
                self.entry_quantite.insert(0, values[3])
                self.entry_poids.insert(0, values[4])

    def _generer_code_article_et_niveau(self, id_article, conn):
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT t2.idca,
                       COALESCE(MAX(t1.niveau), -1) + 1 AS prochain_niveau
                FROM tb_article t1_art
                JOIN tb_categoriearticle t2 ON t1_art.idca = t2.idca
                LEFT JOIN tb_unite t1 ON t1.idarticle = t1_art.idarticle
                WHERE t1_art.idarticle = %s
                GROUP BY t2.idca
            """, (id_article,))
            result = cursor.fetchone()
            if not result:
                messagebox.showerror("Erreur Article",
                                     "Article introuvable ou catégorie manquante.")
                return None, None
            idca, prochain_niveau = result
            code_article = (f"{str(idca).zfill(3)}"
                            f"{str(id_article).zfill(5)}"
                            f"{str(prochain_niveau).zfill(2)}")
            return code_article, prochain_niveau
        except Exception as e:
            messagebox.showerror("Erreur DB",
                                 f"Erreur génération code/niveau : {e}")
            return None, None
        finally:
            cursor.close()

    def ajouter_unite(self):
        designation = self.entry_designation.get().strip()
        qtunite_str = self.entry_quantite.get().strip()
        poids_str   = self.entry_poids.get().strip()
        if not designation or not qtunite_str or not poids_str:
            messagebox.showerror("Erreur de Saisie",
                                 "Tous les champs sont obligatoires.")
            return
        try:
            qtunite = float(qtunite_str)
            poids   = float(poids_str)
            if qtunite <= 0 or poids < 0:
                messagebox.showerror("Erreur de Saisie",
                                     "Quantité > 0 et Poids >= 0 requis.")
                return
        except ValueError:
            messagebox.showerror("Erreur de Saisie",
                                 "Quantité et Poids doivent être des nombres.")
            return
        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT setval(pg_get_serial_sequence('tb_unite','idunite'),
                              COALESCE((SELECT MAX(idunite) FROM tb_unite),0)+1,
                              false);
            """)
            codearticle, niveau = self._generer_code_article_et_niveau(
                self.id_article, conn)
            if codearticle is None:
                return
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tb_unite
                    (idarticle, designationunite, niveau,
                     qtunite, poids, codearticle, deleted)
                VALUES (%s, %s, %s, %s, %s, %s, 0)
            """, (self.id_article, designation, niveau,
                  qtunite, poids, codearticle))
            conn.commit()
            messagebox.showinfo("Succès",
                                f"Unité ajoutée !\nCode : {codearticle}")
            self.charger_unites()
            self.entry_designation.delete(0, 'end')
            self.entry_quantite.delete(0, 'end')
            self.entry_poids.delete(0, 'end')
        except psycopg2.IntegrityError as e:
            conn.rollback()
            messagebox.showerror("Erreur SQL", str(e))
        except psycopg2.Error as e:
            conn.rollback()
            messagebox.showerror("Erreur SQL", str(e))
        finally:
            if conn:
                conn.close()

    def modifier_unite(self):
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Sélection requise",
                                   "Sélectionnez une unité à modifier.")
            return
        values = self.tree.item(selected_item, 'values')
        if not values or not values[0]:
            messagebox.showwarning("Sélection invalide", "Sélection invalide.")
            return
        id_unite    = values[0]
        designation = self.entry_designation.get().strip()
        qtunite_str = self.entry_quantite.get().strip()
        poids_str   = self.entry_poids.get().strip()
        if not designation or not qtunite_str or not poids_str:
            messagebox.showerror("Erreur de Saisie",
                                 "Tous les champs sont obligatoires.")
            return
        try:
            qtunite = float(qtunite_str)
            poids   = float(poids_str)
        except ValueError:
            messagebox.showerror("Erreur de Saisie",
                                 "Quantité et Poids doivent être des nombres.")
            return
        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tb_unite
                SET designationunite=%s, qtunite=%s, poids=%s
                WHERE idunite=%s
            """, (designation, qtunite, poids, id_unite))
            conn.commit()
            messagebox.showinfo("Succès",
                                f"Unité ID {id_unite} modifiée.")
            self.charger_unites()
        except psycopg2.Error as e:
            conn.rollback()
            messagebox.showerror("Erreur SQL", str(e))
        finally:
            if conn:
                conn.close()

    def supprimer_unite(self):
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Sélection requise",
                                   "Sélectionnez une unité à supprimer.")
            return
        values = self.tree.item(selected_item, 'values')
        if not values or not values[0]:
            messagebox.showwarning("Sélection invalide", "Sélection invalide.")
            return
        id_unite    = values[0]
        designation = values[1]
        if not messagebox.askyesno(
                "Confirmation",
                f"Supprimer l'unité '{designation}' (ID: {id_unite}) ?"):
            return
        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tb_unite SET deleted=1 WHERE idunite=%s",
                (id_unite,))
            conn.commit()
            messagebox.showinfo("Succès",
                                f"Unité ID {id_unite} supprimée.")
            self.charger_unites()
            self.entry_designation.delete(0, 'end')
            self.entry_quantite.delete(0, 'end')
            self.entry_poids.delete(0, 'end')
        except psycopg2.Error as e:
            conn.rollback()
            messagebox.showerror("Erreur SQL", str(e))
        finally:
            if conn:
                conn.close()


# ====================================================================
# PageUniteToplevel — inchangé
# ====================================================================

class PageUniteToplevel(ctk.CTkToplevel):
    def __init__(self, master, id_article_selectionne):
        super().__init__(master)
        self.title("Gestion des Unités d'Article")
        self.geometry("900x620")
        if _T:
            Theme.apply_toplevel(self)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        PageUnite(
            self, db_connector=None,
            initial_idarticle=id_article_selectionne
        ).grid(row=0, column=0, sticky="nsew")


# ── Test standalone ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    class App(ctk.CTk):
        def __init__(self):
            super().__init__()
            self.title("iJeery — Test PageUnite")
            self.geometry("300x160")
            if _T:
                Theme.apply(self)
            self.id_article_pour_test = 1
            self.toplevel_window = None
            ctk.CTkButton(
                self,
                text=f"Ouvrir Unités Article {self.id_article_pour_test}",
                command=self.open_unite_window,
                fg_color=C.PRIMARY, hover_color=C.PRIMARY_HOVER,
                font=ctk.CTkFont(
                    family="Roboto" if _T else "Segoe UI",
                    size=12, weight="bold")
            ).pack(pady=40, padx=20, fill="x")

        def open_unite_window(self):
            if (self.toplevel_window is None
                    or not self.toplevel_window.winfo_exists()):
                self.toplevel_window = PageUniteToplevel(
                    self, self.id_article_pour_test)
                self.toplevel_window.focus()
            else:
                self.toplevel_window.focus()

    App().mainloop()