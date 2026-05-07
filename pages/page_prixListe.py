# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  iJeery — page_prixListe.py  (refonte v2)                  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  • Thème iJeery (app_theme) appliqué — même patron que page_ArticleMouvement║
║  • Chargement asynchrone (thread) pour ne pas bloquer l'UI                  ║
║  • Treeview stylisé Mouv.Treeview / en-têtes BG_HEADER                     ║
║  • Double-clic protégé + ouverture directe de la saisie prix               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import json
import threading
from resource_utils import get_session_path, safe_file_read

# page_prixSaisie doit rester optionnel
try:
    from pages.page_prixSaisie import PagePrixSaisie
except ImportError:
    PagePrixSaisie = None

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
    BG_ROW_ALT      = "#F0F4F8"
    PRIMARY         = "#3498DB"
    PRIMARY_HOVER   = "#2980B9"
    SUCCESS         = "#2ECC71"
    SUCCESS_DARK    = "#27AE60"
    DANGER          = "#E74C3C"
    DANGER_DARK     = "#C0392B"
    TEXT_PRIMARY    = "#2C3E50"
    TEXT_SECONDARY  = "#5D6D7E"
    TEXT_MUTED      = "#95A5A6"
    BORDER          = "#D5D8DC"
    DIVIDER         = "#E8EAED"
    SILVER          = "#BDC3C7"
    CLOUDS          = "#ECF0F1"
    DANGER_TEXT     = "#922B21"
    WARNING_TEXT    = "#9A6A00"


C = Colors if _T else _C


# ─────────────────────────────────────────────────────────────────────────────
# Page principale
# ─────────────────────────────────────────────────────────────────────────────
class PagePrixListe(ctk.CTkFrame):
    """
    Page Liste des Prix articles.

    Chargement asynchrone :
    - thread dédié pour la requête SQL
    - after() pour mettre à jour le treeview dans le thread principal
    """

    def __init__(self, parent, db_connector=None, db_conn=None,
                 initial_idarticle=None, iduser=None,
                 id_user_connecte=None, session_data=None):
        super().__init__(parent, fg_color=C.BG_PAGE)

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.db_connector  = db_connector if db_connector is not None else db_conn
        self.code_article  = (str(initial_idarticle).zfill(10)
                              if initial_idarticle else None)
        self.iduser        = self._resolve_iduser(
            parent=parent,
            iduser=iduser,
            session_data=session_data,
            id_user_connecte=id_user_connecte,
        )

        # Protection contre les double-clics
        self.is_opening_window = False
        self._destroyed        = False

        # Mapping item_id → (code_article brut, idunite)
        self.code_mapping = {}

        self._apply_tree_style()
        self._build_ui()

        # Chargement initial différé
        self.after(100, self.load_data_async)

        self.bind("<Destroy>", self._on_destroy)

    # ── helpers ──────────────────────────────────────────────────────────────
    def _on_destroy(self, event):
        if event.widget == self:
            self._destroyed = True

    def _resolve_iduser(self, parent, iduser, session_data, id_user_connecte=None):
        for src in (
            iduser,
            id_user_connecte,
            (session_data or {}).get("user_id") if isinstance(session_data, dict) else None,
            (session_data or {}).get("iduser") if isinstance(session_data, dict) else None,
            getattr(parent, "id_user_connecte", None),
            getattr(parent, "iduser", None),
        ):
            if src is not None:
                try:
                    return int(src)
                except (TypeError, ValueError):
                    pass
        try:
            session_file = get_session_path()
            raw, _enc = safe_file_read(session_file)
            data = json.loads(raw) if raw else {}
            sid = data.get("user_id") or data.get("iduser")
            return int(sid) if sid is not None else 1
        except Exception:
            return 1

    def _f(self, size=11, weight="normal"):
        return ctk.CTkFont(
            family="Roboto" if _T else "Segoe UI",
            size=size, weight=weight)

    def _connect(self):
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                cfg = json.load(f).get('database', {})
            return psycopg2.connect(
                host=cfg.get('host'), user=cfg.get('user'),
                password=cfg.get('password'), database=cfg.get('database'),
                port=cfg.get('port'))
        except FileNotFoundError:
            messagebox.showerror("Configuration",
                                 "Fichier 'config.json' introuvable.")
        except KeyError:
            messagebox.showerror("Configuration",
                                 "Clés DB manquantes dans 'config.json'.")
        except psycopg2.Error as err:
            messagebox.showerror("Connexion",
                                 f"Erreur PostgreSQL : {err}")
        return None

    @staticmethod
    def _fmt_prix(prix):
        """Formate un prix en notation française : 1 234,56"""
        try:
            return (f"{float(prix):,.0f}"
                    .replace('.', '#')
                    .replace(',', '.')
                    .replace('#', ','))
        except (ValueError, TypeError):
            return "0,00"

    # ── Style treeview ────────────────────────────────────────────────────────
    def _apply_tree_style(self):
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure("Prix.Treeview",
                    background=C.BG_CARD, foreground=C.TEXT_PRIMARY,
                    fieldbackground=C.BG_CARD, rowheight=24,
                    font=("Roboto" if _T else "Segoe UI", 10),
                    borderwidth=0)
        s.configure("Prix.Treeview.Heading",
                    background=C.BG_HEADER, foreground="#FFFFFF",
                    font=("Roboto" if _T else "Segoe UI", 10, "bold"),
                    relief="flat", padding=(6, 4))
        s.map("Prix.Treeview",
              background=[("selected", C.PRIMARY)],
              foreground=[("selected", "#FFFFFF")])

    # ── Construction UI ───────────────────────────────────────────────────────
    def _build_ui(self):
        # ── En-tête ──────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=C.BG_HEADER, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(hdr, text="Liste des Prix",
                     font=self._f(18, "bold"),
                     text_color="#FFFFFF"
                     ).pack(side="left", padx=16, pady=8)

        # ── Barre de filtres ─────────────────────────────────────────────────
        panel = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=8)
        panel.grid(row=1, column=0, sticky="ew", padx=12, pady=6)
        inner = ctk.CTkFrame(panel, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(inner, text="Rechercher :",
                     font=self._f(10),
                     text_color=C.TEXT_MUTED
                     ).pack(side="left", padx=(0, 4))

        self._var_search = ctk.StringVar()
        self._entry_search = ctk.CTkEntry(
            inner, textvariable=self._var_search,
            placeholder_text="Code Article, Nom, Unité ou Prix…",
            width=320, height=28,
            fg_color=C.BG_INPUT, border_color=C.BORDER,
            text_color=C.TEXT_PRIMARY, font=self._f(10))
        self._entry_search.pack(side="left", padx=(0, 6))
        self._entry_search.bind("<KeyRelease>", self._on_search)

        ctk.CTkButton(
            inner, text="🔍  Rechercher",
            command=self._on_search,
            fg_color=C.PRIMARY, hover_color=C.PRIMARY_HOVER,
            text_color="#FFFFFF", height=28, width=130,
            font=self._f(10, "bold")
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            inner, text="Reset",
            command=self._reset,
            fg_color="transparent", hover_color=C.DIVIDER,
            text_color=C.TEXT_SECONDARY,
            border_width=1, border_color=C.BORDER,
            height=28, width=60, font=self._f(10)
        ).pack(side="left")

        # ── Tableau ──────────────────────────────────────────────────────────
        tbl = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=8)
        tbl.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 4))
        tbl.grid_rowconfigure(0, weight=1)
        tbl.grid_columnconfigure(0, weight=1)

        cols = ("Code Article", "Nom d'article", "Unité", "Prix")
        self.tree = ttk.Treeview(tbl, columns=cols, show="headings",
                                 style="Prix.Treeview", height=20)

        # Tags
        self.tree.tag_configure("even",      background=C.BG_CARD)
        self.tree.tag_configure("odd",       background="#F0F4F8")
        self.tree.tag_configure("even_zero", background=C.BG_CARD,
                                foreground=C.DANGER)
        self.tree.tag_configure("odd_zero",  background="#F0F4F8",
                                foreground=C.DANGER)

        col_cfg = {
            "Code Article": (150, "center"),
            "Nom d'article": (340, "w"),
            "Unité":         (150, "center"),
            "Prix":          (150, "e"),
        }
        for col in cols:
            w, anchor = col_cfg[col]
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor=anchor)

        sy = ctk.CTkScrollbar(tbl, orientation="vertical",
                              command=self.tree.yview)
        sx = ctk.CTkScrollbar(tbl, orientation="horizontal",
                              command=self.tree.xview)
        self.tree.configure(yscrollcommand=sy.set,
                            xscrollcommand=sx.set)
        self.tree.grid(row=0, column=0, sticky="nsew",
                       padx=(6, 0), pady=(6, 0))
        sy.grid(row=0, column=1, sticky="ns", pady=(6, 0))
        sx.grid(row=1, column=0, sticky="ew", padx=(6, 0))

        self.tree.bind("<Double-Button-1>", self._on_double_click)

        # ── Footer ───────────────────────────────────────────────────────────
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=12, pady=(2, 8))
        self._lbl_count = ctk.CTkLabel(
            footer, text="0 article(s)",
            font=self._f(10, "bold"), text_color=C.PRIMARY)
        self._lbl_count.pack(side="left")
        self._lbl_status = ctk.CTkLabel(
            footer, text="",
            font=self._f(9), text_color=C.TEXT_MUTED)
        self._lbl_status.pack(side="right")

    # ── Chargement des données ────────────────────────────────────────────────
    def load_data_async(self, search_term=""):
        """Lance le chargement SQL dans un thread séparé."""
        self._lbl_count.configure(text="Chargement…")
        self._lbl_status.configure(text="")
        t = threading.Thread(target=self._load_data,
                             args=(search_term,), daemon=True)
        t.start()

    def _load_data(self, search_term=""):
        conn = self._connect()
        if not conn:
            self.after(0, lambda: self._lbl_count.configure(
                text="Erreur de connexion"))
            return
        try:
            cur = conn.cursor()
            query = """
                SELECT
                    u.codearticle::TEXT,
                    a.designation,
                    u.designationunite,
                    COALESCE(p.prix, 0) AS prix,
                    u.idunite
                FROM tb_unite u
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN (
                    SELECT idunite, prix,
                           ROW_NUMBER() OVER (
                               PARTITION BY idunite
                               ORDER BY dateregistre DESC) AS rn
                    FROM tb_prix WHERE deleted = 0
                ) p ON u.idunite = p.idunite AND p.rn = 1
                WHERE a.deleted = 0
            """
            params = []

            if search_term:
                query += """
                    AND (
                        LPAD(u.codearticle::TEXT, 10, '0') LIKE %s OR
                        LOWER(a.designation)      LIKE LOWER(%s) OR
                        LOWER(u.designationunite) LIKE LOWER(%s) OR
                        COALESCE(p.prix, 0)::TEXT LIKE %s
                    )
                """
                pat = f"%{search_term}%"
                params = [pat, pat, pat, pat]
            elif self.code_article:
                query += " AND LPAD(u.codearticle::TEXT, 10, '0') = %s"
                params = [self.code_article.zfill(10)]

            query += " ORDER BY a.designation ASC, u.codearticle ASC"
            cur.execute(query, params)
            rows = cur.fetchall()
            cur.close()
            conn.close()

            try:
                if self.winfo_exists():
                    self.after(0, lambda r=rows: self._update_treeview(r))
            except Exception:
                pass

        except psycopg2.Error as err:
            conn.close()
            self.after(0, lambda e=err: messagebox.showerror(
                "Erreur DB", f"Chargement impossible : {e}"))
        except Exception as err:
            conn.close()
            self.after(0, lambda e=err: messagebox.showerror(
                "Erreur", f"Erreur inattendue : {e}"))

    def _update_treeview(self, rows):
        """Met à jour le treeview (thread principal)."""
        if self._destroyed:
            return
        try:
            if not self.winfo_exists() or not self.tree.winfo_exists():
                return
        except Exception:
            return

        try:
            self.tree.delete(*self.tree.get_children())
        except Exception:
            return

        self.code_mapping = {}

        for idx, row in enumerate(rows):
            if self._destroyed:
                return
            try:
                code_db = row[0] or ""
                nom     = row[1] or ""
                unite   = row[2] or ""
                prix    = row[3] if row[3] is not None else 0
                idunite = row[4]

                prix_fmt  = self._fmt_prix(prix)
                is_zero   = (float(prix) == 0) if prix else True

                if is_zero:
                    tag = "even_zero" if idx % 2 == 0 else "odd_zero"
                else:
                    tag = "even" if idx % 2 == 0 else "odd"

                item_id = self.tree.insert(
                    "", "end",
                    values=(code_db, nom, unite, prix_fmt),
                    tags=(tag,))
                self.code_mapping[item_id] = (code_db, idunite)

            except Exception:
                return

        try:
            self._lbl_count.configure(text=f"{len(rows)} article(s)")
        except Exception:
            pass

    # ── Filtres ───────────────────────────────────────────────────────────────
    def _on_search(self, event=None):
        term = self._var_search.get().strip()
        self.load_data_async(term)

    def _reset(self):
        self._var_search.set("")
        self.load_data_async()

    # ── Double-clic → fenêtre saisie prix ────────────────────────────────────
    def _on_double_click(self, event=None):
        if self.is_opening_window:
            return
        sel = self.tree.selection()
        if not sel:
            return
        mapping = self.code_mapping.get(sel[0])
        if not mapping:
            messagebox.showwarning("Attention",
                                   "Impossible de récupérer le code article.")
            return
        code, idunite = mapping
        self.is_opening_window = True
        try:
            self._open_saisie(code, idunite)
        finally:
            self.after(500, lambda: setattr(self, 'is_opening_window', False))

    def _open_saisie(self, code_article, idunite):
        """Ouvre directement la fenêtre de saisie prix (sans fenêtre de progression)."""
        if PagePrixSaisie is None:
            messagebox.showerror(
                "Erreur",
                "Impossible d'importer page_prixSaisie.py.\n"
                "Vérifiez l'existence du fichier.")
            return

        try:
            saisie_win = ctk.CTkToplevel(self)
            saisie_win.title(f"Saisie Prix — {code_article}")
            saisie_win.geometry("900x700")
            saisie_win.transient(self.winfo_toplevel())
            saisie_win.grab_set()
            if _T:
                Theme.apply_toplevel(saisie_win)

            PagePrixSaisie(
                saisie_win, self.iduser, code_article, idunite
            ).pack(fill="both", expand=True)

            saisie_win.protocol(
                "WM_DELETE_WINDOW",
                lambda: self._on_saisie_close(saisie_win))
        except Exception as err:
            messagebox.showerror("Erreur",
                                 f"Ouverture impossible : {err}")
            import traceback
            traceback.print_exc()

    # ── Helpers fenêtres ──────────────────────────────────────────────────────
    @staticmethod
    def _close_toplevel(win):
        try:
            win.grab_release()
            win.destroy()
        except Exception:
            pass

    def _on_saisie_close(self, win):
        self._close_toplevel(win)
        self.load_data_async(self._var_search.get().strip())


# ── Test standalone ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        from app_theme import init_theme, Theme
        init_theme()
    except ImportError:
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Liste des Prix — iJeery")
    root.geometry("1000x700")
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)

    try:
        Theme.apply(root)
    except Exception:
        pass

    PagePrixListe(root).grid(row=0, column=0, sticky="nsew")
    root.mainloop()
