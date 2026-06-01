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

import os
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import json
import threading
from resource_utils import get_config_path, get_session_path, safe_file_read
from log_utils import AppLogger

try:
    from pages.prix_article_config import get_afficher_variation_prix_defaut
except ImportError:
    from prix_article_config import get_afficher_variation_prix_defaut

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

COL_CODE = "Code Article"
COL_NOM = "Nom d'article"
COL_UNITE = "Unité"
COL_MINMAX = "Min.Prix - Max.Prix"
COL_MOY = "Moyenne.Prix"
COL_PRIX = "Prix"
ALL_COLS = (COL_CODE, COL_NOM, COL_UNITE, COL_MINMAX, COL_MOY, COL_PRIX)

# Poids relatifs pour la répartition proportionnelle de la largeur utile
_COL_WEIGHTS = {
    COL_CODE: 14,
    COL_NOM: 32,
    COL_UNITE: 12,
    COL_MINMAX: 20,
    COL_MOY: 14,
    COL_PRIX: 14,
}
_COL_MINWIDTH = {
    COL_CODE: 90,
    COL_NOM: 120,
    COL_UNITE: 80,
    COL_MINMAX: 130,
    COL_MOY: 85,
    COL_PRIX: 85,
}


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
        self.session_data = session_data or getattr(parent, "session_data", None) or {"user_id": self.iduser}
        self._logger = AppLogger(conn=db_conn, session_data=self.session_data, fallback_user_id=self.iduser)

        # Protection contre les double-clics
        self.is_opening_window = False
        self._destroyed        = False
        self._afficher_variation = get_afficher_variation_prix_defaut(
            self.iduser, default=False,
        )

        # Mapping item_id → (code_article brut, idunite)
        self.code_mapping = {}
        self._tbl_frame = None
        self._scroll_y = None
        self._resize_after_id = None
        self._ajustement_en_cours = False
        self._derniere_cle_colonnes = None

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
            with open(get_config_path('config.json'), 'r', encoding='utf-8') as f:
                cfg = json.load(f).get('database', {})
            from pages.db_helper import connect_page_db
            return connect_page_db()
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

    def _fmt_minmax(self, prix_min, prix_max) -> str:
        return f"{self._fmt_prix(prix_min)} - {self._fmt_prix(prix_max)}"

    def _colonnes_affichees(self):
        if self._afficher_variation:
            return (COL_CODE, COL_NOM, COL_UNITE, COL_MINMAX, COL_MOY, COL_PRIX)
        return (COL_CODE, COL_NOM, COL_UNITE, COL_PRIX)

    def _appliquer_colonnes_treeview(self):
        try:
            self.tree.configure(displaycolumns=self._colonnes_affichees())
            self._derniere_cle_colonnes = None
            self._planifier_ajustement_colonnes()
        except tk.TclError:
            pass

    def _largeur_zone_tableau(self) -> int:
        """Largeur utile pour les colonnes (zone treeview, hors scrollbar verticale)."""
        w = 0
        try:
            if self.tree.winfo_exists():
                w = self.tree.winfo_width()
        except tk.TclError:
            pass
        if w <= 1 and self._tbl_frame is not None:
            try:
                w = self._tbl_frame.winfo_width()
                if self._scroll_y is not None and self._scroll_y.winfo_ismapped():
                    w -= max(self._scroll_y.winfo_width(), 14)
            except tk.TclError:
                pass
        if w <= 1:
            return 0
        return max(w - 4, 200)

    @staticmethod
    def _largeurs_proportionnelles(colonnes, disponible: int):
        """Min. respectés, puis espace restant réparti selon les poids relatifs."""
        if not colonnes:
            return []
        mins = [_COL_MINWIDTH[c] for c in colonnes]
        poids = [_COL_WEIGHTS[c] for c in colonnes]
        somme_min = sum(mins)
        if disponible <= somme_min:
            return list(mins)

        reste = disponible - somme_min
        total_poids = sum(poids) or 1
        largeurs = [
            mins[i] + int(reste * poids[i] / total_poids)
            for i in range(len(colonnes))
        ]
        ecart = disponible - sum(largeurs)
        if ecart:
            idx = colonnes.index(COL_NOM) if COL_NOM in colonnes else len(colonnes) - 1
            largeurs[idx] += ecart
        return largeurs

    def _planifier_ajustement_colonnes(self):
        if self._resize_after_id is not None:
            try:
                self.after_cancel(self._resize_after_id)
            except tk.TclError:
                pass
        self._resize_after_id = self.after(25, self._ajuster_largeurs_colonnes)

    def _ajuster_largeurs_colonnes(self):
        """Répartit toujours 100 % de la largeur utile entre les colonnes visibles."""
        self._resize_after_id = None
        if self._destroyed or self._ajustement_en_cours:
            return
        try:
            if not self.winfo_exists() or not self.tree.winfo_exists():
                return
        except tk.TclError:
            return

        visible = self._colonnes_affichees()
        disponible = self._largeur_zone_tableau()
        if disponible <= 0:
            self._planifier_ajustement_colonnes()
            return

        largeurs = self._largeurs_proportionnelles(visible, disponible)
        cle = (visible, disponible, tuple(largeurs))
        if cle == self._derniere_cle_colonnes:
            return
        self._derniere_cle_colonnes = cle

        self._ajustement_en_cours = True
        try:
            for col in ALL_COLS:
                if col not in visible:
                    self.tree.column(col, width=0, minwidth=0, stretch=False)
            for col, larg in zip(visible, largeurs):
                mw = min(_COL_MINWIDTH[col], larg)
                self.tree.column(
                    col,
                    width=int(larg),
                    minwidth=mw,
                    stretch=False,
                )
        except tk.TclError:
            self._derniere_cle_colonnes = None
        finally:
            self._ajustement_en_cours = False

    def _on_tbl_configure(self, _event=None):
        self._planifier_ajustement_colonnes()

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
        # ── En-tête (titre + Paramètres / Configuration) ───────────────────────
        hdr = ctk.CTkFrame(self, fg_color=C.BG_HEADER, corner_radius=0, height=48)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(0, weight=1)

        bar = ctk.CTkFrame(hdr, fg_color="transparent", corner_radius=0)
        bar.grid(row=0, column=0, sticky="ew", padx=16, pady=(10, 10))
        bar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            bar, text="Prix Article",
            font=self._f(15, "bold"),
            text_color="#FFFFFF",
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        links = ctk.CTkFrame(bar, fg_color="transparent", corner_radius=0)
        links.grid(row=0, column=1, sticky="ne", padx=(12, 0))
        link_font = self._f(11)
        if _T:
            link_font = ctk.CTkFont(
                family=getattr(Fonts, "_family", "Segoe UI"),
                size=11, underline=True,
            )
        color_param = getattr(C, "PRIMARY_LIGHT", C.PRIMARY)
        color_conf = getattr(C, "INFO_LIGHT", C.PRIMARY)

        try:
            from pages.menu_auth_utils import (
                CLE_CONF_PRIX,
                CLE_PARAM_PRIX,
                est_lien_param_autorise,
                resolve_session_data,
            )
        except ImportError:
            from menu_auth_utils import (
                CLE_CONF_PRIX,
                CLE_PARAM_PRIX,
                est_lien_param_autorise,
                resolve_session_data,
            )
        _sd = resolve_session_data(self)

        self.lbl_parametres = ctk.CTkLabel(
            links, text="⚙  Paramètres",
            font=link_font, text_color=color_param, cursor="hand2",
        )
        if est_lien_param_autorise(_sd, CLE_PARAM_PRIX):
            self.lbl_parametres.pack(side="left", padx=(0, 14))
        self.lbl_parametres.bind("<Button-1>", lambda _e: self._ouvrir_parametres())

        self.lbl_configuration = ctk.CTkLabel(
            links, text="🔧  Configuration",
            font=link_font, text_color=color_conf, cursor="hand2",
        )
        if est_lien_param_autorise(_sd, CLE_CONF_PRIX):
            self.lbl_configuration.pack(side="left")
        self.lbl_configuration.bind("<Button-1>", lambda _e: self._ouvrir_configuration())

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
        self._tbl_frame = tbl

        self.tree = ttk.Treeview(
            tbl, columns=ALL_COLS, show="headings",
            style="Prix.Treeview", height=20,
        )

        # Tags
        self.tree.tag_configure("even",      background=C.BG_CARD)
        self.tree.tag_configure("odd",       background="#F0F4F8")
        self.tree.tag_configure("even_zero", background=C.BG_CARD,
                                foreground=C.DANGER)
        self.tree.tag_configure("odd_zero",  background="#F0F4F8",
                                foreground=C.DANGER)

        col_anchor = {
            COL_CODE: "center",
            COL_NOM: "w",
            COL_UNITE: "center",
            COL_MINMAX: "center",
            COL_MOY: "e",
            COL_PRIX: "e",
        }
        for col in ALL_COLS:
            self.tree.column(col, anchor=col_anchor[col], stretch=False)
        self._appliquer_colonnes_treeview()
        from treeview_sort_utils import attach_tree_sort
        _fr = {c: "fr_float" for c in (COL_MINMAX, COL_MOY, COL_PRIX)}
        attach_tree_sort(self.tree, ALL_COLS, column_types=_fr, configure_columns=False)

        self._scroll_y = ctk.CTkScrollbar(
            tbl, orientation="vertical", command=self.tree.yview,
        )
        self.tree.configure(yscrollcommand=self._scroll_y.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=(6, 0))
        self._scroll_y.grid(row=0, column=1, sticky="ns", pady=(6, 0))

        tbl.bind("<Configure>", self._on_tbl_configure)
        self.bind("<Configure>", self._on_tbl_configure)
        self.bind("<Map>", self._on_tbl_configure)
        self.tree.bind("<Double-Button-1>", self._on_double_click)

        self.after(80, self._planifier_ajustement_colonnes)

        # ── Footer ───────────────────────────────────────────────────────────
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=12, pady=(2, 8))
        footer.grid_columnconfigure(1, weight=1)

        self._lbl_count = ctk.CTkLabel(
            footer, text="0 article(s)",
            font=self._f(10, "bold"), text_color=C.PRIMARY,
        )
        self._lbl_count.grid(row=0, column=0, sticky="w")

        self._lbl_status = ctk.CTkLabel(
            footer, text="",
            font=self._f(9), text_color=C.TEXT_MUTED,
        )
        self._lbl_status.grid(row=0, column=1, sticky="e", padx=(8, 12))

        self._chk_variation = ctk.CTkCheckBox(
            footer,
            text="Afficher la variation du prix",
            font=self._f(10),
            checkbox_width=18,
            checkbox_height=18,
            command=self._on_toggle_variation,
        )
        self._chk_variation.grid(row=0, column=2, sticky="e")
        if self._afficher_variation:
            self._chk_variation.select()
        else:
            self._chk_variation.deselect()

    def _on_toggle_variation(self):
        self._afficher_variation = bool(self._chk_variation.get())
        self._derniere_cle_colonnes = None
        self._appliquer_colonnes_treeview()
        self.load_data_async(self._var_search.get().strip())

    def _ouvrir_parametres(self):
        try:
            from pages.menu_auth_utils import (
                CLE_PARAM_PRIX,
                est_lien_param_autorise,
            )
        except ImportError:
            from menu_auth_utils import (
                CLE_PARAM_PRIX,
                est_lien_param_autorise,
            )
        if not est_lien_param_autorise(self.session_data, CLE_PARAM_PRIX):
            messagebox.showwarning(
                "Accès refusé",
                "Votre fonction utilisateur n'est pas autorisée à ouvrir "
                "les paramètres du menu Prix Article.",
            )
            return
        path = get_config_path("settings.json")
        try:
            os.startfile(path)
        except Exception:
            messagebox.showinfo(
                "Paramètres",
                f"Fichier des paramètres (impression, options globales) :\n{path}",
            )

    def _on_configuration_saved(self):
        pref = get_afficher_variation_prix_defaut(self.iduser, default=False)
        self._afficher_variation = pref
        self._derniere_cle_colonnes = None
        if pref:
            self._chk_variation.select()
        else:
            self._chk_variation.deselect()
        self._appliquer_colonnes_treeview()
        self.load_data_async(self._var_search.get().strip())

    def _ouvrir_configuration(self):
        try:
            from pages.menu_auth_utils import (
                CLE_CONF_PRIX,
                est_lien_param_autorise,
            )
        except ImportError:
            from menu_auth_utils import (
                CLE_CONF_PRIX,
                est_lien_param_autorise,
            )
        if not est_lien_param_autorise(self.session_data, CLE_CONF_PRIX):
            messagebox.showwarning(
                "Accès refusé",
                "Votre fonction utilisateur n'est pas autorisée à ouvrir "
                "la configuration du menu Prix Article.",
            )
            return
        try:
            from pages.window_configuration_prix_article import (
                ConfigurationPrixArticleWindow,
            )
        except ImportError:
            from window_configuration_prix_article import (
                ConfigurationPrixArticleWindow,
            )
        ConfigurationPrixArticleWindow(
            self,
            id_user=self.iduser,
            on_saved=self._on_configuration_saved,
        )

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
                    u.idunite,
                    st.prix_min,
                    st.prix_max,
                    st.prix_moy
                FROM tb_unite u
                INNER JOIN tb_article a ON u.idarticle = a.idarticle
                LEFT JOIN (
                    SELECT idunite, prix,
                           ROW_NUMBER() OVER (
                               PARTITION BY idunite
                               ORDER BY dateregistre DESC) AS rn
                    FROM tb_prix WHERE deleted = 0
                ) p ON u.idunite = p.idunite AND p.rn = 1
                LEFT JOIN (
                    SELECT idunite,
                           MIN(prix) AS prix_min,
                           MAX(prix) AS prix_max,
                           AVG(prix) AS prix_moy
                    FROM tb_prix
                    WHERE deleted = 0
                    GROUP BY idunite
                ) st ON u.idunite = st.idunite
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
                prix     = row[3] if row[3] is not None else 0
                idunite  = row[4]
                prix_min = row[5]
                prix_max = row[6]
                prix_moy = row[7]

                prix_fmt = self._fmt_prix(prix)
                is_zero  = (float(prix) == 0) if prix else True

                if is_zero:
                    tag = "even_zero" if idx % 2 == 0 else "odd_zero"
                else:
                    tag = "even" if idx % 2 == 0 else "odd"

                if self._afficher_variation:
                    min_v = prix_min if prix_min is not None else 0
                    max_v = prix_max if prix_max is not None else 0
                    moy_v = prix_moy if prix_moy is not None else 0
                    values = (
                        code_db, nom, unite,
                        self._fmt_minmax(min_v, max_v),
                        self._fmt_prix(moy_v),
                        prix_fmt,
                    )
                else:
                    values = (code_db, nom, unite, "", "", prix_fmt)

                item_id = self.tree.insert("", "end", values=values, tags=(tag,))
                self.code_mapping[item_id] = (code_db, idunite)

            except Exception:
                return

        try:
            self._lbl_count.configure(text=f"{len(rows)} article(s)")
        except Exception:
            pass

        self._planifier_ajustement_colonnes()

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
            try:
                self._logger.log(
                    action="Ouverture saisie prix",
                    element=str(code_article),
                    details=f"Ouverture fenêtre saisie prix (idunite={idunite})",
                    value=f"idunite={idunite}",
                )
            except Exception:
                pass
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
