# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  iJeery — page_prixSaisie.py  (refonte v2)                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  • Thème iJeery (app_theme) — même patron que page_ArticleMouvement         ║
║  • Code, Nom, Unité affichés en labels (lecture seule)                      ║
║  • Seul le champ Prix est une CTkEntry éditable                             ║
║  • Fenêtre auto-dimensionnée et centrée                                     ║
║  • Logique métier (enregistrer/modifier/supprimer/nouveau) inchangée        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime
import json
from resource_utils import get_config_path, get_session_path, safe_file_read

# ── Thème iJeery ──────────────────────────────────────────────────────────────
try:
    from app_theme import Colors, Fonts, styled, Theme
    _T = True
except ImportError:
    _T = False


class _C:
    """Fallback couleurs si app_theme absent."""
    MIDNIGHT        = "#2C3E50"
    BG_PAGE         = "#ECF0F1"
    BG_CARD         = "#FFFFFF"
    BG_HEADER       = "#2C3E50"
    BG_INPUT        = "#F4F6F8"
    PRIMARY         = "#3498DB"
    PRIMARY_HOVER   = "#2980B9"
    SUCCESS         = "#2ECC71"
    SUCCESS_DARK    = "#27AE60"
    DANGER          = "#E74C3C"
    DANGER_DARK     = "#C0392B"
    WARNING         = "#F39C12"
    INFO            = "#1ABC9C"
    INFO_DARK       = "#16A085"
    TEXT_PRIMARY    = "#2C3E50"
    TEXT_SECONDARY  = "#5D6D7E"
    TEXT_MUTED      = "#95A5A6"
    BORDER          = "#D5D8DC"
    DIVIDER         = "#E8EAED"
    SILVER          = "#BDC3C7"
    CLOUDS          = "#ECF0F1"


C = Colors if _T else _C


class PagePrixSaisie(ctk.CTkFrame):
    """
    Formulaire de saisie / historique des prix d'un article.

    Champs informatifs (labels) : Code Article, Nom, Unité
    Champ éditable             : Prix uniquement
    """

    def __init__(self, parent, iduser, codearticle=None, idunite=None):
        super().__init__(parent, fg_color=C.BG_PAGE)

        self.iduser      = iduser
        self.codearticle = str(codearticle) if codearticle is not None else None
        self.initial_idunite = int(idunite) if idunite is not None else None
        self.selected_id = None
        self.articles_dict = {}
        self.unites_dict   = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._apply_tree_style()
        self._build_ui()

        # Charger les données
        self.charger_articles()
        self.charger_unites()

        # Centrer + dimensionner la fenêtre parente une fois rendue
        self.after(50, self._fit_and_center)

    # ── helpers ──────────────────────────────────────────────────────────────
    def _f(self, size=12, weight="normal"):
        return ctk.CTkFont(
            family="Roboto" if _T else "Segoe UI",
            size=size, weight=weight)

    def _connect(self):
        try:
            with open(get_config_path('config.json')) as f:
                cfg = json.load(f)['database']
            return psycopg2.connect(
                host=cfg['host'], user=cfg['user'],
                password=cfg['password'], database=cfg['database'],
                port=cfg['port'])
        except FileNotFoundError:
            messagebox.showerror("Configuration",
                                 "Fichier 'config.json' introuvable.")
        except KeyError:
            messagebox.showerror("Configuration",
                                 "Clés DB manquantes dans 'config.json'.")
        except psycopg2.Error as err:
            messagebox.showerror("Connexion", f"Erreur PostgreSQL : {err}")
        return None

    # ── Style treeview ────────────────────────────────────────────────────────
    def _apply_tree_style(self):
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure("Saisie.Treeview",
                    background=C.BG_CARD, foreground=C.TEXT_PRIMARY,
                    fieldbackground=C.BG_CARD, rowheight=24,
                    font=("Roboto" if _T else "Segoe UI", 10),
                    borderwidth=0)
        s.configure("Saisie.Treeview.Heading",
                    background=C.BG_HEADER, foreground="#FFFFFF",
                    font=("Roboto" if _T else "Segoe UI", 10, "bold"),
                    relief="flat", padding=(6, 4))
        s.map("Saisie.Treeview",
              background=[("selected", C.PRIMARY)],
              foreground=[("selected", "#FFFFFF")])

    # ── Construction UI ───────────────────────────────────────────────────────
    def _build_ui(self):
        # ── En-tête ──────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=C.BG_HEADER, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(hdr, text="Gestion des Prix",
                     font=self._f(16, "bold"),
                     text_color="#FFFFFF"
                     ).pack(side="left", padx=16, pady=10)

        # ── Card formulaire ───────────────────────────────────────────────────
        card = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=10,
                            border_width=1, border_color=C.BORDER)
        card.grid(row=1, column=0, sticky="ew", padx=20, pady=(14, 6))
        card.grid_columnconfigure(1, weight=1)

        LABEL_W = 130
        PAD_X   = (16, 12)
        PAD_Y   = (10, 2)

        # ── Code Article ──────────────────────────────────────────────────────
        ctk.CTkLabel(card, text="Code Article",
                     font=self._f(11), text_color=C.TEXT_MUTED,
                     width=LABEL_W, anchor="w"
                     ).grid(row=0, column=0, sticky="w",
                            padx=PAD_X, pady=PAD_Y)
        self._lbl_code = ctk.CTkLabel(
            card, text="—",
            font=self._f(12, "bold"), text_color=C.TEXT_PRIMARY,
            anchor="w")
        self._lbl_code.grid(row=0, column=1, sticky="w",
                            padx=(0, 16), pady=PAD_Y)

        ctk.CTkFrame(card, height=1, fg_color=C.DIVIDER
                     ).grid(row=1, column=0, columnspan=2,
                            sticky="ew", padx=16)

        # ── Nom d'article ─────────────────────────────────────────────────────
        ctk.CTkLabel(card, text="Nom d'article",
                     font=self._f(11), text_color=C.TEXT_MUTED,
                     width=LABEL_W, anchor="w"
                     ).grid(row=2, column=0, sticky="w",
                            padx=PAD_X, pady=PAD_Y)
        self._lbl_nom = ctk.CTkLabel(
            card, text="—",
            font=self._f(12), text_color=C.TEXT_PRIMARY,
            anchor="w", wraplength=360)
        self._lbl_nom.grid(row=2, column=1, sticky="w",
                           padx=(0, 16), pady=PAD_Y)

        ctk.CTkFrame(card, height=1, fg_color=C.DIVIDER
                     ).grid(row=3, column=0, columnspan=2,
                            sticky="ew", padx=16)

        # ── Unité ─────────────────────────────────────────────────────────────
        ctk.CTkLabel(card, text="Unité",
                     font=self._f(11), text_color=C.TEXT_MUTED,
                     width=LABEL_W, anchor="w"
                     ).grid(row=4, column=0, sticky="w",
                            padx=PAD_X, pady=PAD_Y)
        self._lbl_unite = ctk.CTkLabel(
            card, text="—",
            font=self._f(12), text_color=C.TEXT_PRIMARY,
            anchor="w")
        self._lbl_unite.grid(row=4, column=1, sticky="w",
                             padx=(0, 16), pady=PAD_Y)

        ctk.CTkFrame(card, height=1, fg_color=C.DIVIDER
                     ).grid(row=5, column=0, columnspan=2,
                            sticky="ew", padx=16)

        # ── Prix (seul champ éditable) ────────────────────────────────────────
        ctk.CTkLabel(card, text="Prix",
                     font=self._f(11), text_color=C.TEXT_MUTED,
                     width=LABEL_W, anchor="w"
                     ).grid(row=6, column=0, sticky="w",
                            padx=PAD_X, pady=(10, 14))

        self.entry_prix = ctk.CTkEntry(
            card,
            placeholder_text="0.00",
            width=180, height=34,
            fg_color=C.BG_INPUT, border_color=C.BORDER,
            border_width=1,
            text_color=C.TEXT_PRIMARY,
            font=self._f(13, "bold"),
            corner_radius=8)
        self.entry_prix.grid(row=6, column=1, sticky="w",
                             padx=(0, 16), pady=(10, 14))
        self.entry_prix.bind(
            "<FocusIn>",
            lambda _: self.entry_prix.configure(border_color=C.PRIMARY))
        self.entry_prix.bind(
            "<FocusOut>",
            lambda _: self.entry_prix.configure(border_color=C.BORDER))

        # ── Boutons ───────────────────────────────────────────────────────────
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.grid(row=2, column=0, sticky="ew", padx=20, pady=(4, 6))

        BTN_H = 34

        self.btn_enregistrer = ctk.CTkButton(
            btn_bar, text="💾  Enregistrer",
            command=self.enregistrer,
            height=BTN_H, width=150,
            fg_color=C.SUCCESS_DARK, hover_color=C.SUCCESS,
            text_color="#FFFFFF", font=self._f(11, "bold"),
            corner_radius=8)
        self.btn_enregistrer.pack(side="left", padx=(0, 6))

        self.btn_modifier = ctk.CTkButton(
            btn_bar, text="✏  Modifier",
            command=self.modifier,
            height=BTN_H, width=130,
            fg_color=C.WARNING, hover_color="#D68910",
            text_color="#FFFFFF", font=self._f(11, "bold"),
            corner_radius=8)
        self.btn_modifier.pack(side="left", padx=(0, 6))

        self.btn_supprimer = ctk.CTkButton(
            btn_bar, text="🗑  Supprimer",
            command=self.supprimer,
            height=BTN_H, width=130,
            fg_color=C.DANGER, hover_color=C.DANGER_DARK,
            text_color="#FFFFFF", font=self._f(11, "bold"),
            corner_radius=8)
        self.btn_supprimer.pack(side="left", padx=(0, 6))

        self.btn_nouveau = ctk.CTkButton(
            btn_bar, text="＋  Nouveau",
            command=self.nouveau,
            height=BTN_H, width=120,
            fg_color=C.INFO, hover_color=C.INFO_DARK,
            text_color="#FFFFFF", font=self._f(11, "bold"),
            corner_radius=8)
        self.btn_nouveau.pack(side="left")

        # ── Section historique ────────────────────────────────────────────────
        hist_card = ctk.CTkFrame(self, fg_color=C.BG_CARD,
                                 corner_radius=10,
                                 border_width=1, border_color=C.BORDER)
        hist_card.grid(row=3, column=0, sticky="nsew",
                       padx=20, pady=(0, 16))
        hist_card.grid_rowconfigure(1, weight=1)
        hist_card.grid_columnconfigure(0, weight=1)

        # Sous-header historique
        hist_hdr = ctk.CTkFrame(hist_card, fg_color=C.MIDNIGHT,
                                corner_radius=0, height=34)
        hist_hdr.grid(row=0, column=0, columnspan=2, sticky="ew")
        hist_hdr.grid_propagate(False)
        ctk.CTkLabel(hist_hdr, text="Historique des Prix",
                     font=self._f(12, "bold"),
                     text_color="#FFFFFF"
                     ).pack(side="left", padx=14, pady=6)

        # Treeview historique
        self.tree = ttk.Treeview(
            hist_card,
            columns=("ID", "Date", "Prix", "Utilisateur"),
            show="headings",
            style="Saisie.Treeview",
            height=8)
        self.tree.tag_configure("even", background=C.BG_CARD)
        self.tree.tag_configure("odd",  background="#F0F4F8")

        for col, w, anchor in [
            ("ID",   60,  "center"),
            ("Date", 180, "center"),
            ("Prix", 120, "e"),
            ("Utilisateur", 160, "w"),
        ]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor=anchor)

        sy = ctk.CTkScrollbar(hist_card, orientation="vertical",
                              command=self.tree.yview)
        self.tree.configure(yscrollcommand=sy.set)

        self.tree.grid(row=1, column=0, sticky="nsew",
                       padx=(10, 0), pady=(6, 10))
        sy.grid(row=1, column=1, sticky="ns",
                padx=(0, 6), pady=(6, 10))

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

    # ── Dimensionner et centrer la fenêtre parente ────────────────────────────
    def _fit_and_center(self):
        try:
            win = self.winfo_toplevel()
            win.update_idletasks()
            w, h = 560, 620
            sw = win.winfo_screenwidth()
            sh = win.winfo_screenheight()
            x  = (sw - w) // 2
            y  = (sh - h) // 2
            win.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # LOGIQUE MÉTIER — inchangée
    # ─────────────────────────────────────────────────────────────────────────

    def charger_articles(self):
        try:
            conn = self._connect()
            if not conn:
                self.articles_dict = {}
                return
            cur = conn.cursor()
            if self.codearticle:
                if self.initial_idunite is not None:
                    cur.execute("""
                        SELECT a.idarticle, u.codearticle::TEXT,
                               a.designation, u.designationunite, u.idunite
                        FROM tb_unite u
                        INNER JOIN tb_article a ON u.idarticle = a.idarticle
                        WHERE u.codearticle::TEXT = %s
                          AND u.idunite = %s
                        ORDER BY u.codearticle
                    """, (self.codearticle, self.initial_idunite))
                else:
                    cur.execute("""
                        SELECT a.idarticle, u.codearticle::TEXT,
                               a.designation, u.designationunite, u.idunite
                        FROM tb_unite u
                        INNER JOIN tb_article a ON u.idarticle = a.idarticle
                        WHERE u.codearticle::TEXT = %s
                        ORDER BY u.codearticle
                    """, (self.codearticle,))
            else:
                cur.execute("""
                    SELECT a.idarticle, u.codearticle::TEXT,
                           a.designation, u.designationunite, u.idunite
                    FROM tb_unite u
                    INNER JOIN tb_article a ON u.idarticle = a.idarticle
                    WHERE a.deleted = 0
                    ORDER BY u.codearticle
                """)
            articles = cur.fetchall()
            cur.close()
            conn.close()

            if not articles and self.codearticle:
                self.articles_dict = {}
                messagebox.showerror(
                    "Article introuvable",
                    f"Le code '{self.codearticle}' n'existe pas dans tb_unite.")
                return

            self.articles_dict = {
                str(a[1]): (a[0], str(a[2] or ""), str(a[3] or ""), a[4])
                for a in articles if a[1] is not None
            }
            codes = list(self.articles_dict.keys())
            if codes:
                self._afficher_article(codes[0])

        except Exception as e:
            self.articles_dict = {}
            messagebox.showerror("Erreur",
                                 f"Chargement articles : {e}")

    def charger_unites(self):
        try:
            conn = self._connect()
            if not conn:
                return
            cur = conn.cursor()
            cur.execute("""
                SELECT idunite, designationunite
                FROM tb_unite WHERE deleted = 0
                ORDER BY designationunite
            """)
            unites = cur.fetchall()
            cur.close()
            conn.close()
            self.unites_dict = {
                str(u[1] or ""): u[0]
                for u in unites if u[1] is not None
            }
        except Exception as e:
            messagebox.showerror("Erreur",
                                 f"Chargement unités : {e}")

    def _afficher_article(self, code):
        """Met à jour les labels informatifs et charge l'historique."""
        if code not in self.articles_dict:
            return
        idarticle, designation, unite, idunite = self.articles_dict[code]
        self._lbl_code.configure(text=code or "—")
        self._lbl_nom.configure(text=designation or "—")
        self._lbl_unite.configure(text=unite or "—")
        self.charger_historique(idarticle, idunite)

    # Compat avec l'ancienne signature utilisée dans charger_articles
    def on_code_selected(self, choice):
        self._afficher_article(choice)

    def charger_historique(self, idarticle, idunite):
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            conn = self._connect()
            if not conn:
                return
            cur = conn.cursor()
            cur.execute("""
                SELECT
                    p.id,
                    p.dateregistre,
                    p.prix,
                    COALESCE(u.username, 'Système') AS utilisateur
                FROM tb_prix p
                LEFT JOIN tb_users u ON u.iduser = p.iduser
                WHERE p.idarticle = %s
                  AND p.idunite = %s
                  AND p.deleted = 0
                ORDER BY p.dateregistre DESC
            """, (idarticle, idunite))
            for i, row in enumerate(cur.fetchall()):
                date_str = (row[1].strftime("%d/%m/%Y %H:%M:%S")
                            if row[1] else "")
                prix_str = f"{row[2]:.2f}" if row[2] else "0.00"
                user_str = row[3] or "Système"
                tag = "even" if i % 2 == 0 else "odd"
                self.tree.insert("", "end",
                                 values=(row[0], date_str, prix_str, user_str),
                                 tags=(tag,))
            cur.close()
            conn.close()
        except Exception as e:
            messagebox.showerror("Erreur",
                                 f"Chargement historique : {e}")

    def on_tree_select(self, event=None):
        sel = self.tree.selection()
        if sel:
            values = self.tree.item(sel[0])['values']
            self.selected_id = values[0]
            prix = str(values[2]).replace(',', '.')
            self.entry_prix.delete(0, "end")
            self.entry_prix.insert(0, prix)

    # ── Validation ────────────────────────────────────────────────────────────
    def valider_formulaire(self):
        code = self._lbl_code.cget("text")
        if not code or code == "—" or code not in self.articles_dict:
            messagebox.showwarning("Attention", "Aucun article chargé.")
            return False
        prix_str = self.entry_prix.get().strip()
        if not prix_str:
            messagebox.showwarning("Attention", "Veuillez saisir un prix.")
            return False
        try:
            prix = float(prix_str.replace(',', '.'))
            if prix < 0:
                messagebox.showwarning("Attention",
                                       "Le prix ne peut pas être négatif.")
                return False
        except ValueError:
            messagebox.showwarning("Attention",
                                   "Le prix doit être un nombre valide.")
            return False
        return True

    def enregistrer(self):
        if not self.valider_formulaire():
            return
        try:
            conn = self._connect()
            if not conn:
                return
            cur = conn.cursor()
            code      = self._lbl_code.cget("text")
            idarticle = self.articles_dict[code][0]
            idunite   = self.articles_dict[code][3]
            prix      = float(self.entry_prix.get().replace(',', '.'))

            cur.execute("""
                SELECT setval(pg_get_serial_sequence('tb_prix', 'id'),
                       COALESCE((SELECT MAX(id) FROM tb_prix), 0) + 1, false)
            """)
            cur.execute("""
                INSERT INTO tb_prix
                    (idarticle, idunite, prix, dateregistre, iduser, deleted)
                VALUES (%s, %s, %s, %s, %s, 0)
            """, (idarticle, idunite, prix, datetime.now(), self.iduser))
            conn.commit()
            cur.close()
            conn.close()

            messagebox.showinfo("Succès", "Prix enregistré avec succès.")
            self.nouveau()

        except Exception as e:
            messagebox.showerror("Erreur",
                                 f"Enregistrement impossible : {e}")

    def modifier(self):
        if not self.selected_id:
            messagebox.showwarning("Attention",
                                   "Sélectionnez un prix à modifier.")
            return
        if not self.valider_formulaire():
            return
        try:
            code      = self._lbl_code.cget("text")
            idarticle = self.articles_dict[code][0]
            idunite   = self.articles_dict[code][3]
            prix      = float(self.entry_prix.get().replace(',', '.'))

            conn = self._connect()
            if not conn:
                return
            cur = conn.cursor()
            cur.execute("""
                UPDATE tb_prix
                SET prix = %s, idunite = %s, dateregistre = %s
                WHERE id = %s
            """, (prix, idunite, datetime.now(), self.selected_id))
            conn.commit()
            cur.close()
            conn.close()

            messagebox.showinfo("Succès", "Prix modifié avec succès.")
            self.charger_historique(idarticle, idunite)
            self.nouveau()

        except Exception as e:
            messagebox.showerror("Erreur",
                                 f"Modification impossible : {e}")

    def supprimer(self):
        if not self.selected_id:
            messagebox.showwarning("Attention",
                                   "Sélectionnez un prix à supprimer.")
            return
        if not messagebox.askyesno("Confirmation",
                                   "Supprimer ce prix de l'historique ?"):
            return
        try:
            code      = self._lbl_code.cget("text")
            idarticle = self.articles_dict[code][0]
            idunite   = self.articles_dict[code][3]

            conn = self._connect()
            if not conn:
                return
            cur = conn.cursor()
            cur.execute("UPDATE tb_prix SET deleted = 1 WHERE id = %s",
                        (self.selected_id,))
            conn.commit()
            cur.close()
            conn.close()

            messagebox.showinfo("Succès", "Prix supprimé avec succès.")
            self.charger_historique(idarticle, idunite)
            self.nouveau()

        except Exception as e:
            messagebox.showerror("Erreur",
                                 f"Suppression impossible : {e}")

    def nouveau(self):
        """Réinitialise le champ Prix et rafraîchit l'historique."""
        self.selected_id = None
        self.entry_prix.delete(0, "end")
        code = self._lbl_code.cget("text")
        if code and code != "—" and code in self.articles_dict:
            self.charger_historique(self.articles_dict[code][0], self.articles_dict[code][3])


# ── Test standalone ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        from app_theme import init_theme, Theme
        init_theme()
    except ImportError:
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Saisie Prix — iJeery")
    try:
        Theme.apply(root)
    except Exception:
        pass

    # Récupérer l'utilisateur connecté depuis la session (fallback = 1)
    session_user_id = 1
    try:
        raw, _enc = safe_file_read(get_session_path())
        session_data = json.loads(raw) if raw else {}
        session_user_id = (
            session_data.get("user_id")
            or session_data.get("iduser")
            or 1
        )
    except Exception:
        session_user_id = 1

    PagePrixSaisie(root, iduser=session_user_id).pack(fill="both", expand=True)
    root.mainloop()
