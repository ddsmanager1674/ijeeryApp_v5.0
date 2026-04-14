from __future__ import annotations

import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from tkcalendar import DateEntry

from app_theme import Colors, Fonts, styled, Theme
from EtatsPDF_Mouvements import EtatPDFMouvements


def _apply_treeview_style():
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(
        "iJeery.Treeview",
        background=Colors.BG_CARD,
        foreground=Colors.TEXT_PRIMARY,
        fieldbackground=Colors.BG_CARD,
        rowheight=28,
        font=("Segoe UI", 9),
        borderwidth=0,
    )
    style.configure(
        "iJeery.Treeview.Heading",
        background=Colors.MIDNIGHT,
        foreground=Colors.TEXT_ON_DARK,
        font=("Segoe UI", 9, "bold"),
        relief="flat",
        borderwidth=0,
    )
    style.map(
        "iJeery.Treeview",
        background=[("selected", Colors.PRIMARY_LIGHT)],
        foreground=[("selected", Colors.TEXT_PRIMARY)],
    )


# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 3 — Backend modulaire (DB)
# Règles:
# - tb_livraisoncli       : livraisons réelles (historique, INSERT uniquement, jamais qtlivrecli=0)
# - tb_livraisoncli_attente: backlog BL (qt_a_livrer, qt_bl, statut)
# - vente = sortie stock immédiate (tb_ventedetail), donc BL n'impacte pas le stock
# ─────────────────────────────────────────────────────────────────────────────

def calcul_reste(qt_a_livrer: float, qt_bl: float) -> float:
    try:
        return max(float(qt_a_livrer or 0) - float(qt_bl or 0), 0.0)
    except Exception:
        return 0.0


class LivraisonClientRepo:
    """Fonctions DB isolées pour le module Livraison Client."""

    def __init__(self, connect_db_fn):
        self._connect_db = connect_db_fn

    def ensure_table(self) -> None:
        conn = self._connect_db()
        if not conn:
            return
        cur = None
        try:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS tb_livraisoncli_attente (
                    id SERIAL PRIMARY KEY,
                    refvente VARCHAR(50),
                    idarticle INTEGER,
                    idunite INTEGER,
                    idmag INTEGER,
                    idclient INTEGER,
                    qt_a_livrer DOUBLE PRECISION,
                    qt_bl DOUBLE PRECISION DEFAULT 0,
                    statut VARCHAR(20) DEFAULT 'EN_ATTENTE',
                    dateregistre TIMESTAMP,
                    iduser INTEGER
                );
                """
            )
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            try:
                if cur:
                    cur.close()
            except Exception:
                pass
            conn.close()

    def get_attentes(self, refvente: Optional[str] = None, statut: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self._connect_db()
        if not conn:
            return []
        cur = None
        try:
            cur = conn.cursor()
            sql = """
                SELECT refvente, idarticle, idunite, idmag, idclient,
                       COALESCE(qt_a_livrer,0) as qt_a_livrer,
                       COALESCE(qt_bl,0) as qt_bl,
                       COALESCE(statut,'EN_ATTENTE') as statut,
                       dateregistre, iduser
                FROM tb_livraisoncli_attente
                WHERE 1=1
            """
            params: List[Any] = []
            if refvente:
                sql += " AND refvente=%s"
                params.append(refvente)
            if statut:
                sql += " AND statut=%s"
                params.append(statut)
            sql += " ORDER BY dateregistre DESC NULLS LAST"
            cur.execute(sql, tuple(params))
            out: List[Dict[str, Any]] = []
            for r in cur.fetchall():
                out.append({
                    "refvente": r[0],
                    "idarticle": r[1],
                    "idunite": r[2],
                    "idmag": r[3],
                    "idclient": r[4],
                    "qt_a_livrer": float(r[5] or 0),
                    "qt_bl": float(r[6] or 0),
                    "statut": r[7],
                    "dateregistre": r[8],
                    "iduser": r[9],
                })
            return out
        except Exception:
            return []
        finally:
            try:
                if cur:
                    cur.close()
            except Exception:
                pass
            conn.close()

    def get_livraisons(self, refvente: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retourne l'historique BL (tb_livraisoncli). Ne fait que lire.
        """
        conn = self._connect_db()
        if not conn:
            return []
        cur = None
        try:
            cur = conn.cursor()
            sql = """
                SELECT reflivcli, refvente, idmag, idarticle, idunite,
                       COALESCE(qtlivrecli,0) as qtlivrecli,
                       dateregistre, iduser, idclient
                FROM tb_livraisoncli
                WHERE 1=1
            """
            params: List[Any] = []
            if refvente:
                sql += " AND refvente=%s"
                params.append(refvente)
            sql += " ORDER BY dateregistre DESC NULLS LAST, idlivcli DESC"
            cur.execute(sql, tuple(params))
            out: List[Dict[str, Any]] = []
            for r in cur.fetchall():
                out.append({
                    "reflivcli": r[0],
                    "refvente": r[1],
                    "idmag": r[2],
                    "idarticle": r[3],
                    "idunite": r[4],
                    "qtlivrecli": float(r[5] or 0),
                    "dateregistre": r[6],
                    "iduser": r[7],
                    "idclient": r[8],
                })
            return out
        except Exception:
            return []
        finally:
            try:
                if cur:
                    cur.close()
            except Exception:
                pass
            conn.close()

    def create_attente(
        self,
        refvente: str,
        idarticle: int,
        idunite: int,
        idmag: int,
        idclient: int,
        qt_a_livrer: float,
        iduser: int,
    ) -> None:
        """
        Upsert attente par (refvente,idarticle,idunite,idmag).
        Ne touche jamais tb_livraisoncli.
        """
        conn = self._connect_db()
        if not conn:
            raise RuntimeError("Connexion DB impossible.")
        cur = None
        try:
            cur = conn.cursor()
            q = float(qt_a_livrer or 0)
            if q < 0:
                q = 0.0
            # upsert (sans contrainte unique, on évite duplicates via update puis insert)
            cur.execute(
                """
                UPDATE tb_livraisoncli_attente
                   SET qt_a_livrer=%s,
                       statut=CASE
                           WHEN %s <= COALESCE(qt_bl,0) + 1e-9 THEN 'LIVRÉ'
                           WHEN %s <= 0 THEN 'ANNULEE'
                           ELSE 'EN_ATTENTE'
                       END,
                       iduser=%s
                 WHERE refvente=%s AND idmag=%s AND idarticle=%s AND idunite=%s
                """,
                (q, q, q, iduser, refvente, idmag, idarticle, idunite),
            )
            if cur.rowcount == 0:
                cur.execute(
                    """
                    INSERT INTO tb_livraisoncli_attente
                        (refvente,idarticle,idunite,idmag,idclient,qt_a_livrer,qt_bl,statut,dateregistre,iduser)
                    VALUES (%s,%s,%s,%s,%s,%s,0,'EN_ATTENTE',NOW(),%s)
                    """,
                    (refvente, idarticle, idunite, idmag, idclient, q, iduser),
                )
            conn.commit()
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            raise RuntimeError(str(e))
        finally:
            try:
                if cur:
                    cur.close()
            except Exception:
                pass
            conn.close()

    def cancel_attente(self, refvente: str, idarticle: int, idunite: int, idmag: int, iduser: int) -> None:
        conn = self._connect_db()
        if not conn:
            raise RuntimeError("Connexion DB impossible.")
        cur = None
        try:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE tb_livraisoncli_attente
                   SET statut='ANNULEE', iduser=%s
                 WHERE refvente=%s AND idmag=%s AND idarticle=%s AND idunite=%s
                """,
                (iduser, refvente, idmag, idarticle, idunite),
            )
            conn.commit()
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            raise RuntimeError(str(e))
        finally:
            try:
                if cur:
                    cur.close()
            except Exception:
                pass
            conn.close()

    def create_bl(
        self,
        refliv: str,
        refvente: str,
        idclient: int,
        iduser: int,
        lignes: List[Dict[str, Any]],
    ) -> None:
        """
        Crée un BL: INSERT dans tb_livraisoncli pour chaque ligne q>0,
        puis met à jour tb_livraisoncli_attente.qt_bl et le statut (PARTIEL/LIVRÉ).
        """
        conn = self._connect_db()
        if not conn:
            raise RuntimeError("Connexion DB impossible.")
        cur = None
        try:
            cur = conn.cursor()
            for l in lignes:
                q = float(l.get("qtlivrecli") or 0)
                if q <= 0:
                    continue  # règle critique

                idmag = int(l["idmag"])
                idarticle = int(l["idarticle"])
                idunite = int(l["idunite"])
                qtvente = float(l.get("qtvente") or 0)

                cur.execute(
                    """
                    INSERT INTO tb_livraisoncli
                        (reflivcli, refvente, idmag, idarticle, idunite,
                         qtvente, qtlivrecli, dateregistre, iduser, idclient)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,NOW(),%s,%s)
                    """,
                    (refliv, refvente, idmag, idarticle, idunite, qtvente, q, iduser, idclient),
                )

                # update backlog
                cur.execute(
                    """
                    UPDATE tb_livraisoncli_attente
                       SET qt_bl = COALESCE(qt_bl,0) + %s,
                           statut = CASE
                               WHEN (COALESCE(qt_a_livrer,0) - (COALESCE(qt_bl,0) + %s)) <= 1e-9 THEN 'LIVRÉ'
                               WHEN (COALESCE(qt_bl,0) + %s) > 0 THEN 'PARTIEL'
                               ELSE 'EN_ATTENTE'
                           END,
                           iduser = %s
                     WHERE refvente=%s AND idmag=%s AND idarticle=%s AND idunite=%s
                    """,
                    (q, q, q, iduser, refvente, idmag, idarticle, idunite),
                )

            conn.commit()
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            raise RuntimeError(str(e))
        finally:
            try:
                if cur:
                    cur.close()
            except Exception:
                pass
            conn.close()


class PageLivraisonClient(ctk.CTkFrame):
    """
    Règle 2 (sortie stock immédiate):
    - La vente (tb_ventedetail) sort le stock.
    - Le BL (tb_livraisoncli) est un document logistique.
    - Les demandes BL se gèrent dans tb_livraisoncli_attente.
    """

    def __init__(self, master, id_user_connecte: Optional[int] = None) -> None:
        super().__init__(master, fg_color=Colors.BG_PAGE)
        _apply_treeview_style()

        self.user_id = id_user_connecte
        if self.user_id is None:
            messagebox.showerror("Erreur", "Aucun utilisateur connecté. Veuillez vous reconnecter.")

        # Repo DB (backend modulaire)
        self.repo = LivraisonClientRepo(self.connect_db)
        self.repo.ensure_table()

        self.selected_ref_vente: Optional[str] = None
        self.selected_id_client: Optional[int] = None
        self.selected_id_mag: Optional[int] = None
        self.selected_id_vente: Optional[int] = None
        self.selected_nom_client: str = ""
        self.selected_magasin: str = ""

        self.mode_var = ctk.StringVar(value="HISTO")  # "HISTO" (étape 4). Les modes BL/ATTENTE seront rebranchés plus tard.

        self._ensure_attente_table()
        self.setup_ui()

    # ─────────────────────────────────────────────────────────────────────
    # DB
    # ─────────────────────────────────────────────────────────────────────
    def connect_db(self):
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(current_dir)
            config_path = os.path.join(root_dir, "config.json")
            with open(config_path, "r") as f:
                config = json.load(f)
                db_config = config["database"]
            return psycopg2.connect(**db_config)
        except Exception as e:
            messagebox.showerror("Connexion", f"Connexion DB impossible.\nErreur: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────
    # Z-INDEX helpers (messagebox au-dessus)
    # ─────────────────────────────────────────────────────────────────────
    def _lift_parent(self, parent=None) -> None:
        try:
            w = parent or self.winfo_toplevel()
            w.lift()
            w.focus_force()
            w.attributes("-topmost", True)
            w.after(150, lambda: w.attributes("-topmost", False))
        except Exception:
            pass

    def _make_toplevel(self, title: str, geometry: str, parent=None) -> ctk.CTkToplevel:
        """
        Crée un Toplevel cohérent (z-index) : au premier plan, transient du parent,
        topmost temporaire, et thème appliqué.
        """
        p = parent or self.winfo_toplevel()
        win = ctk.CTkToplevel(p)
        win.title(title)
        win.geometry(geometry)
        try:
            win.transient(p)
        except Exception:
            pass
        try:
            win.lift()
            win.focus_force()
            win.attributes("-topmost", True)
            win.after(200, lambda: win.attributes("-topmost", False))
        except Exception:
            pass
        Theme.apply_toplevel(win)
        return win

    def _ask_yes_no(self, title: str, message: str, parent=None) -> bool:
        self._lift_parent(parent)
        try:
            return bool(messagebox.askyesno(title, message, parent=parent or self.winfo_toplevel()))
        except Exception:
            return bool(messagebox.askyesno(title, message))

    def _info(self, title: str, message: str, parent=None) -> None:
        self._lift_parent(parent)
        try:
            messagebox.showinfo(title, message, parent=parent or self.winfo_toplevel())
        except Exception:
            messagebox.showinfo(title, message)

    def _warn(self, title: str, message: str, parent=None) -> None:
        self._lift_parent(parent)
        try:
            messagebox.showwarning(title, message, parent=parent or self.winfo_toplevel())
        except Exception:
            messagebox.showwarning(title, message)

    def _error(self, title: str, message: str, parent=None) -> None:
        self._lift_parent(parent)
        try:
            messagebox.showerror(title, message, parent=parent or self.winfo_toplevel())
        except Exception:
            messagebox.showerror(title, message)

    def _ensure_attente_table(self) -> None:
        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.tb_livraisoncli_attente (
                    id serial PRIMARY KEY,
                    refvente character varying(50) NOT NULL,
                    idmag integer NOT NULL,
                    idclient integer NOT NULL,
                    idarticle integer NOT NULL,
                    idunite integer NOT NULL,
                    qt_a_livrer double precision NOT NULL DEFAULT 0,
                    qt_bl double precision NOT NULL DEFAULT 0,
                    statut character varying(20) NOT NULL DEFAULT 'EN_ATTENTE',
                    dateregistre timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
                    iduser integer,
                    CONSTRAINT tb_livraisoncli_attente_uk UNIQUE (refvente, idmag, idarticle, idunite)
                );
            """)
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            try:
                cur.close()
            except Exception:
                pass
            conn.close()

    # ─────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────
    def _parse_float(self, s: Any) -> float:
        try:
            if s is None:
                return 0.0
            if isinstance(s, (int, float)):
                return float(s)
            txt = str(s).strip()
            if not txt:
                return 0.0
            return float(txt.replace(".", "").replace(",", "."))
        except Exception:
            return 0.0

    def _format(self, n: Any) -> str:
        try:
            return f"{float(n):,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")
        except Exception:
            return "0,00"

    def _generate_bl_ref(self) -> str:
        year = datetime.now().year
        conn = self.connect_db()
        if not conn:
            return f"{year}-BL-00001"
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM tb_livraisoncli WHERE EXTRACT(YEAR FROM dateregistre) = %s", (year,))
            count = (cur.fetchone() or [0])[0] + 1
            return f"{year}-BL-{count:05d}"
        except Exception:
            return f"{year}-BL-00001"
        finally:
            try:
                cur.close()
            except Exception:
                pass
            conn.close()

    def _configure_alternating(self, tree: ttk.Treeview) -> None:
        tree.tag_configure("row_even", background=Colors.BG_CARD)
        tree.tag_configure("row_odd", background=Colors.BG_ROW_ALT)

    def _refresh_alternating(self, tree: ttk.Treeview) -> None:
        for i, iid in enumerate(tree.get_children()):
            tree.item(iid, tags=("row_even" if i % 2 == 0 else "row_odd",))

    # ─────────────────────────────────────────────────────────────────────
    # UI
    # ─────────────────────────────────────────────────────────────────────
    def setup_ui(self):
        # ── Header ─────────────────────────────────────────────────────────
        header = styled.card(self)
        header.pack(fill="x", padx=18, pady=(16, 10))
        h = styled.frame(header)
        h.pack(fill="x", padx=18, pady=14)

        top_row = styled.frame(h)
        top_row.pack(fill="x")
        styled.label_title(top_row, text="🚚  Livraison Client").pack(side="left")
        styled.button_success(
            top_row,
            text="+ Créer Livraison",
            icon="➕",
            command=self.open_create_livraison_popup,  # étape 5
            width=190,
        ).pack(side="right")

        styled.label_muted(
            h,
            text="Historique unifié (attentes + BL). Règle: la vente sort le stock immédiatement.",
        ).pack(anchor="w", pady=(6, 0))

        # ── Filtres ─────────────────────────────────────────────────────────
        filters = styled.card(self)
        filters.pack(fill="x", padx=18, pady=(0, 10))
        f = styled.frame(filters)
        f.pack(fill="x", padx=18, pady=12)

        styled.label_muted(f, text="🔍 Recherche", width=110, anchor="w").pack(side="left")
        self.entry_search = styled.entry(f, placeholder="Facture ou client...")
        self.entry_search.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_search.bind("<KeyRelease>", lambda _e: self._filter_history())

        styled.label_muted(f, text="Statut", width=60, anchor="w").pack(side="left", padx=(0, 6))
        self.combo_statut = styled.combobox(
            f,
            values=["Tous", "EN_ATTENTE", "PARTIEL", "LIVRÉ", "ANNULEE"],
            command=lambda _v=None: self._filter_history(),
            width=150,
        )
        self.combo_statut.set("Tous")
        self.combo_statut.pack(side="left", padx=(0, 10))

        styled.button_secondary(f, text="Actualiser", icon="🔄", command=self.load_history, width=140).pack(side="right")

        # ── Tableau historique ─────────────────────────────────────────────
        table_card = styled.card(self)
        table_card.pack(fill="both", expand=True, padx=18, pady=(0, 16))
        tinner = styled.frame(table_card)
        tinner.pack(fill="both", expand=True, padx=12, pady=12)

        cols = ("refvente", "client", "statut", "total", "livre", "reste", "_idclient", "_idmag")
        self.tree_histo = ttk.Treeview(tinner, columns=cols, show="headings", height=18, style="iJeery.Treeview")
        self._configure_alternating(self.tree_histo)
        # Couleurs statuts (tags ttk)
        self.tree_histo.tag_configure("st_en_attente", foreground=Colors.WARNING_TEXT)
        self.tree_histo.tag_configure("st_partiel", foreground=Colors.PRIMARY)
        self.tree_histo.tag_configure("st_livre", foreground=Colors.SUCCESS_TEXT)
        self.tree_histo.tag_configure("st_annulee", foreground=Colors.DANGER_TEXT)

        headers = [
            ("refvente", "Facture", 140, "center"),
            ("client", "Client", 260, "w"),
            ("statut", "Statut", 110, "center"),
            ("total", "Total attendu", 120, "e"),
            ("livre", "Total livré", 120, "e"),
            ("reste", "Reste", 110, "e"),
        ]
        for k, t, w, a in headers:
            self.tree_histo.heading(k, text=t)
            self.tree_histo.column(k, width=w, anchor=a, stretch=False)

        for k in ("_idclient", "_idmag"):
            self.tree_histo.heading(k, text="")
            self.tree_histo.column(k, width=0, stretch=False)

        scroll_y = ttk.Scrollbar(tinner, orient="vertical", command=self.tree_histo.yview)
        self.tree_histo.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side="right", fill="y")
        self.tree_histo.pack(side="left", fill="both", expand=True)
        self.tree_histo.bind("<Double-1>", lambda _e: self.open_detail_popup())

        self.load_history()

    # ─────────────────────────────────────────────────────────────────────
    # ÉTAPE 5 — Popup "Créer Livraison" (création attente backlog)
    # ─────────────────────────────────────────────────────────────────────
    def open_create_livraison_popup(self) -> None:
        """
        Flux:
        1) choisir facture
        2) afficher lignes tb_ventedetail (cochées par défaut)
        3) éditer quantités
        4) Mettre en attente -> INSERT/UPDATE tb_livraisoncli_attente
        """
        if self.user_id is None:
            self._error("Erreur", "Aucun utilisateur connecté.")
            return

        win = self._make_toplevel("Créer Livraison (Attente BL)", "1200x760")
        try:
            win.minsize(980, 640)
        except Exception:
            pass

        card = styled.card(win)
        card.pack(fill="both", expand=True, padx=16, pady=16)
        inner = styled.frame(card)
        inner.pack(fill="both", expand=True, padx=16, pady=16)

        styled.label_heading(inner, text="Créer une attente de livraison (Backlog BL)").pack(anchor="w")
        styled.label_muted(
            inner,
            text="Toutes les lignes sont cochées par défaut. Décoche / ajuste les quantités si besoin, puis clique “Mettre en attente”.",
        ).pack(anchor="w", pady=(2, 12))

        # --- Actions (toujours visibles) ---
        top_actions = styled.frame(inner)
        top_actions.pack(fill="x", pady=(0, 10))
        styled.button_secondary(top_actions, text="Fermer", icon="✕", command=win.destroy, width=120).pack(side="left")

        # --- Split view: factures (gauche) / lignes vente (droite) ---
        split = styled.frame(inner)
        split.pack(fill="both", expand=True, pady=(0, 8))
        split.grid_rowconfigure(0, weight=1)
        # 50/50
        split.grid_columnconfigure(0, weight=1, uniform="split")
        split.grid_columnconfigure(1, weight=1, uniform="split")

        left = styled.card(split)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right = styled.card(split)
        right.grid(row=0, column=1, sticky="nsew")

        # Vars sélection facture
        self._popup_ref_var = ctk.StringVar(value="")
        self._popup_client_var = ctk.StringVar(value="")
        self._popup_mag_var = ctk.StringVar(value="")
        self._popup_idvente: Optional[int] = None
        self._popup_idclient: Optional[int] = None
        self._popup_idmag: Optional[int] = None

        # ---- GAUCHE : liste factures + filtres ----
        lf = styled.frame(left)
        lf.pack(fill="both", expand=True, padx=12, pady=12)
        lf.grid_rowconfigure(3, weight=1)
        lf.grid_columnconfigure(0, weight=1)

        styled.label_heading(lf, text="Factures").pack(anchor="w")
        filters = styled.frame(lf)
        filters.pack(fill="x", pady=(10, 10))

        self._fact_search = styled.entry(filters, placeholder="Recherche facture / client...")
        self._fact_search.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # Date range (début/fin)
        date_box = styled.frame(filters)
        date_box.pack(side="right")
        self._date_debut = DateEntry(date_box, width=10, date_pattern="yyyy-mm-dd", locale="fr_FR")
        self._date_debut.pack(side="left", padx=(0, 6))
        self._date_fin = DateEntry(date_box, width=10, date_pattern="yyyy-mm-dd", locale="fr_FR")
        self._date_fin.pack(side="left")

        btns_l = styled.frame(lf)
        btns_l.pack(fill="x", pady=(0, 10))
        styled.button_secondary(
            btns_l,
            text="Filtrer",
            icon="🔎",
            command=lambda: self._popup_load_factures(tree_fact),
            width=120,
        ).pack(side="right")

        tree_fact = ttk.Treeview(
            lf,
            columns=("ref", "client", "date", "mag", "idvente", "idcli", "idmag"),
            show="headings",
            height=14,
            style="iJeery.Treeview",
        )
        self._configure_alternating(tree_fact)
        for k, t, w, a in [
            ("ref", "Facture", 120, "center"),
            ("client", "Client", 200, "w"),
            ("date", "Date", 95, "center"),
            ("mag", "Magasin", 170, "w"),
        ]:
            tree_fact.heading(k, text=t)
            tree_fact.column(k, width=w, anchor=a, stretch=False)
        for k in ("idvente", "idcli", "idmag"):
            tree_fact.heading(k, text="")
            tree_fact.column(k, width=0, stretch=False)
        tree_fact.pack(fill="both", expand=True)

        # Recherche live
        def _on_search(_e=None):
            self._popup_filter_factures(tree_fact)
        self._fact_search.bind("<KeyRelease>", _on_search)

        # ---- DROITE : badges + lignes vendues ----
        rf = styled.frame(right)
        rf.pack(fill="both", expand=True, padx=12, pady=12)
        rf.grid_rowconfigure(2, weight=1)
        rf.grid_columnconfigure(0, weight=1)
        styled.label_heading(rf, text="Articles de la facture").pack(anchor="w")

        badges = styled.frame(rf)
        badges.pack(fill="x", pady=(10, 10))
        badge_ref = styled.badge(badges, text="Facture: ---", variant="neutral")
        badge_ref.pack(side="left")
        badge_cli = styled.badge(badges, text="Client: ---", variant="neutral")
        badge_cli.pack(side="left", padx=(8, 0))
        badge_mag = styled.badge(badges, text="Magasin: ---", variant="neutral")
        badge_mag.pack(side="left", padx=(8, 0))

        tinner = styled.frame(rf)
        tinner.pack(fill="both", expand=True)

        cols = ("check", "code", "designation", "unite", "qt_vendue", "qt_a_livrer", "_idarticle", "_idunite", "_idmag")
        tree_lines = ttk.Treeview(tinner, columns=cols, show="headings", height=16, style="iJeery.Treeview")
        self._configure_alternating(tree_lines)
        tree_lines.heading("check", text="✓")
        tree_lines.column("check", width=40, anchor="center", stretch=False)
        tree_lines.heading("code", text="Code")
        tree_lines.column("code", width=100, anchor="center", stretch=False)
        tree_lines.heading("designation", text="Désignation")
        tree_lines.column("designation", width=330, anchor="w", stretch=False)
        tree_lines.heading("unite", text="Unité")
        tree_lines.column("unite", width=90, anchor="center", stretch=False)
        tree_lines.heading("qt_vendue", text="Vendu")
        tree_lines.column("qt_vendue", width=110, anchor="e", stretch=False)
        tree_lines.heading("qt_a_livrer", text="Qté à livrer (attente)")
        tree_lines.column("qt_a_livrer", width=160, anchor="e", stretch=False)

        for k in ("_idarticle", "_idunite", "_idmag"):
            tree_lines.heading(k, text="")
            tree_lines.column(k, width=0, stretch=False)

        scroll_y = ttk.Scrollbar(tinner, orient="vertical", command=tree_lines.yview)
        tree_lines.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side="right", fill="y")
        tree_lines.pack(side="left", fill="both", expand=True)

        def _toggle_check(iid: str):
            v = list(tree_lines.item(iid).get("values") or [])
            if not v:
                return
            v[0] = "☐" if str(v[0]) == "☑" else "☑"
            tree_lines.item(iid, values=v)

        def _on_click(event):
            region = tree_lines.identify("region", event.x, event.y)
            if region != "cell":
                return
            col = tree_lines.identify_column(event.x)
            row = tree_lines.identify_row(event.y)
            if not row:
                return
            if col == "#1":  # check column
                _toggle_check(row)

        tree_lines.bind("<Button-1>", _on_click, add="+")
        tree_lines.bind("<Double-1>", lambda _e: self._popup_edit_qty(tree_lines))

        def _save_attentes():
            if not self._popup_ref_var.get():
                self._warn("Facture", "Veuillez choisir une facture.", parent=win)
                return
            if not self._popup_idclient or not self._popup_idmag:
                self._warn("Données", "Facture incomplète (client/magasin).", parent=win)
                return

            count = 0
            for iid in tree_lines.get_children():
                v = tree_lines.item(iid).get("values") or []
                if not v:
                    continue
                checked = (str(v[0]) == "☑")
                if not checked:
                    continue
                qt_vendue = self._parse_float(v[4])
                qt_a_livrer = self._parse_float(v[5])
                if qt_a_livrer < 0:
                    qt_a_livrer = 0.0
                if qt_a_livrer > qt_vendue + 1e-9:
                    qt_a_livrer = qt_vendue
                idarticle = int(v[6])
                idunite = int(v[7])
                idmag = int(v[8] or self._popup_idmag or 0)

                # create_attente (backlog)
                self.repo.create_attente(
                    refvente=self._popup_ref_var.get(),
                    idarticle=idarticle,
                    idunite=idunite,
                    idmag=idmag,
                    idclient=int(self._popup_idclient),
                    qt_a_livrer=qt_a_livrer,
                    iduser=int(self.user_id),
                )
                count += 1

            self._info("Succès", f"Attente enregistrée ({count} ligne(s)).", parent=win)
            self.load_history()
            win.destroy()

        styled.button_success(
            top_actions,
            text="Mettre en attente",
            icon="⏳",
            command=_save_attentes,
            width=180,
        ).pack(side="right")

        # Selection facture -> charger lignes
        def _select_facture(_e=None):
            sel = tree_fact.selection()
            if not sel:
                return
            v = tree_fact.item(sel[0]).get("values") or []
            if not v:
                return
            ref = v[0]; nom = v[1]; date = v[2]; mag = v[3]
            idvente = int(v[4]); idcli = int(v[5]) if v[5] is not None else None; idmag = int(v[6]) if v[6] is not None else None
            self._set_popup_facture(badge_ref, badge_cli, badge_mag, ref, nom, idvente, idcli, idmag, mag)
            self._popup_load_lignes(tree_lines)

        tree_fact.bind("<<TreeviewSelect>>", _select_facture)
        tree_fact.bind("<Double-1>", _select_facture)

        # Charger factures initialement
        self._popup_load_factures(tree_fact)

    def _set_popup_facture(
        self,
        badge_ref,
        badge_cli,
        badge_mag,
        refvente: str,
        nomcli: str,
        idvente: int,
        idcli: Optional[int],
        idmag: Optional[int],
        magasin: str,
    ) -> None:
        self._popup_ref_var.set(refvente)
        self._popup_client_var.set(nomcli or "")
        self._popup_mag_var.set(magasin or "")
        self._popup_idvente = idvente
        self._popup_idclient = idcli
        self._popup_idmag = idmag

        badge_ref.configure(text=f"Facture: {refvente}", fg_color=Colors.PRIMARY_LIGHT, text_color=Colors.PRIMARY)
        badge_cli.configure(text=f"Client: {nomcli or '---'}", fg_color=Colors.INFO_LIGHT, text_color=Colors.INFO_TEXT)
        badge_mag.configure(text=f"Magasin: {magasin or '---'}", fg_color=Colors.CLOUDS, text_color=Colors.TEXT_SECONDARY)

    def _popup_load_lignes(self, tree_lines: ttk.Treeview) -> None:
        for iid in tree_lines.get_children():
            tree_lines.delete(iid)
        if not self._popup_idvente:
            return

        conn = self.connect_db()
        if not conn:
            return
        cur = None
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    u.codearticle,
                    art.designation,
                    u.designationunite,
                    vd.qtvente,
                    vd.idarticle,
                    vd.idunite,
                    vd.idmag
                FROM tb_ventedetail vd
                INNER JOIN tb_article art ON vd.idarticle = art.idarticle
                INNER JOIN tb_unite u ON (vd.idarticle = u.idarticle AND vd.idunite = u.idunite)
                WHERE vd.idvente=%s AND COALESCE(vd.deleted,0)=0
                ORDER BY art.designation
                """,
                (self._popup_idvente,),
            )
            for r in cur.fetchall():
                code = r[0]
                des = r[1]
                unite = r[2]
                qt_vendue = float(r[3] or 0)
                idart = int(r[4])
                idun = int(r[5])
                idmag = int(r[6] or (self._popup_idmag or 0))

                tree_lines.insert(
                    "",
                    "end",
                    values=(
                        "☑",
                        code,
                        des,
                        unite,
                        self._format(qt_vendue),
                        self._format(qt_vendue),  # défaut = vendu
                        idart,
                        idun,
                        idmag,
                    ),
                )
            self._refresh_alternating(tree_lines)
        except Exception as e:
            self._error("Erreur", f"Chargement lignes échoué: {e}")
        finally:
            try:
                if cur:
                    cur.close()
            except Exception:
                pass
            conn.close()

    def _popup_edit_qty(self, tree_lines: ttk.Treeview) -> None:
        sel = tree_lines.selection()
        if not sel:
            return
        iid = sel[0]
        v = tree_lines.item(iid).get("values") or []
        if not v:
            return

        vendu = self._parse_float(v[4])
        cur_qty = self._parse_float(v[5])

        dlg = ctk.CTkToplevel(self)
        dlg.title("Modifier quantité (attente)")
        dlg.geometry("520x260")
        dlg.attributes("-topmost", True)
        Theme.apply_toplevel(dlg)

        card = styled.card(dlg)
        card.pack(fill="both", expand=True, padx=16, pady=16)
        inner = styled.frame(card)
        inner.pack(fill="both", expand=True, padx=18, pady=18)

        styled.label_heading(inner, text="Quantité en attente").pack(anchor="w")
        styled.label(inner, text=f"{v[1]} — {v[2]}", size=12, weight="bold").pack(anchor="w", pady=(6, 8))
        styled.label_muted(inner, text=f"Vendu: {self._format(vendu)}").pack(anchor="w", pady=(0, 10))

        row = styled.frame(inner)
        row.pack(fill="x")
        styled.label_muted(row, text="Qté à livrer", width=120, anchor="w").pack(side="left")
        ent = styled.entry(row, placeholder=str(cur_qty))
        ent.insert(0, str(cur_qty))
        ent.pack(side="left", fill="x", expand=True)
        ent.focus()

        def _ok():
            q = self._parse_float(ent.get())
            if q < 0:
                self._warn("Quantité", "Quantité négative interdite.", parent=dlg)
                return
            if q > vendu + 1e-9:
                self._warn("Quantité", "La quantité dépasse la quantité vendue.", parent=dlg)
                return
            nv = list(v)
            nv[5] = self._format(q)
            tree_lines.item(iid, values=nv)
            dlg.destroy()

        btns = styled.frame(inner)
        btns.pack(fill="x", pady=(12, 0))
        styled.button_secondary(btns, text="Annuler", icon="✕", command=dlg.destroy, width=120).pack(side="left")
        styled.button_success(btns, text="Valider", icon="✔", command=_ok, width=140).pack(side="right")

        ent.bind("<Return>", lambda _e: _ok())

    def _open_facture_picker(self, parent, on_select):
        """
        Mini-picker factures (réutilise la logique existante, mais isolé pour la popup étape 5).
        on_select(refvente, nomcli, idvente, idcli, idmag, magasin_label)
        """
        top = self._make_toplevel("Sélectionner Facture", "780x560", parent=parent)

        card = styled.card(top)
        card.pack(fill="both", expand=True, padx=16, pady=16)
        inner = styled.frame(card)
        inner.pack(fill="both", expand=True, padx=16, pady=16)

        styled.label_heading(inner, text="Choisir une facture").pack(anchor="w")

        frow = styled.frame(inner)
        frow.pack(fill="x", pady=(10, 10))
        styled.label_muted(frow, text="Date", width=60, anchor="w").pack(side="left")

        cal_container = styled.frame(frow)
        cal_container.pack(side="left", padx=(0, 10))
        ent_date = DateEntry(
            cal_container,
            width=12,
            background="darkblue",
            foreground="white",
            borderwidth=2,
            date_pattern="yyyy-mm-dd",
            locale="fr_FR",
        )
        ent_date.pack()

        tree_f = ttk.Treeview(
            inner,
            columns=("ref", "client", "date", "idvente", "idcli", "idmag", "mag"),
            show="headings",
            height=16,
            style="iJeery.Treeview",
        )
        self._configure_alternating(tree_f)
        for k, t, w in [("ref", "Facture", 140), ("client", "Client", 240), ("date", "Date", 120), ("mag", "Magasin", 220)]:
            tree_f.heading(k, text=t)
            tree_f.column(k, width=w, anchor="w" if k in ("client", "mag") else "center", stretch=False)
        for k in ("idvente", "idcli", "idmag"):
            tree_f.heading(k, text="")
            tree_f.column(k, width=0, stretch=False)
        tree_f.pack(fill="both", expand=True, pady=(0, 10))

        def charger(date_val: Optional[str] = None):
            for i in tree_f.get_children():
                tree_f.delete(i)

            conn = self.connect_db()
            if not conn:
                return

            cur = None
            try:
                cur = conn.cursor()
                base = """
                    SELECT v.refvente, COALESCE(c.nomcli,''), v.dateregistre, v.id, v.idclient, v.idmag, COALESCE(m.designationmag,'')
                    FROM tb_vente v
                    LEFT JOIN tb_client c ON v.idclient = c.idclient
                    LEFT JOIN tb_magasin m ON v.idmag = m.idmag
                    WHERE v.deleted = 0
                """
                if date_val:
                    cur.execute(
                        base + " AND CAST(v.dateregistre AS DATE) = %s ORDER BY v.dateregistre DESC",
                        (date_val,),
                    )
                else:
                    cur.execute(base + " ORDER BY v.dateregistre DESC LIMIT 80")

                for r in cur.fetchall():
                    d = r[2].strftime("%d/%m/%Y") if hasattr(r[2], "strftime") else str(r[2])
                    tree_f.insert("", "end", values=(r[0], r[1] or "", d, r[3], r[4], r[5], r[6]))
                self._refresh_alternating(tree_f)
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
            finally:
                try:
                    if cur:
                        cur.close()
                except Exception:
                    pass
                conn.close()

        def valider():
            sel = tree_f.selection()
            if not sel:
                self._warn("Sélection", "Veuillez sélectionner une facture.", parent=top)
                return
            v = tree_f.item(sel[0]).get("values") or []
            on_select(v[0], v[1], int(v[3]), int(v[4]) if v[4] is not None else None, int(v[5]) if v[5] is not None else None, v[6])
            top.destroy()

        b = styled.frame(inner)
        b.pack(fill="x")
        styled.button_secondary(b, text="Fermer", icon="✕", command=top.destroy, width=120).pack(side="left")
        styled.button_secondary(
            b,
            text="Filtrer",
            icon="🔎",
            command=lambda: charger(ent_date.get_date().strftime("%Y-%m-%d")),
            width=120,
        ).pack(side="left", padx=(8, 0))
        styled.button_success(b, text="Choisir", icon="✔", command=valider, width=140).pack(side="right")

        charger()

    def _popup_load_factures(self, tree_fact: ttk.Treeview) -> None:
        """Charge les factures dans le panel gauche (avec filtre date range)."""
        for iid in tree_fact.get_children():
            tree_fact.delete(iid)

        conn = self.connect_db()
        if not conn:
            return
        cur = None
        try:
            cur = conn.cursor()
            d1 = None
            d2 = None
            try:
                d1 = self._date_debut.get_date().strftime("%Y-%m-%d")
                d2 = self._date_fin.get_date().strftime("%Y-%m-%d")
            except Exception:
                d1 = None
                d2 = None

            sql = """
                SELECT v.refvente, COALESCE(c.nomcli,''), v.dateregistre, COALESCE(m.designationmag,''),
                       v.id, v.idclient, v.idmag
                FROM tb_vente v
                LEFT JOIN tb_client c ON v.idclient=c.idclient
                LEFT JOIN tb_magasin m ON v.idmag=m.idmag
                WHERE v.deleted=0
            """
            params: List[Any] = []
            if d1 and d2:
                sql += " AND CAST(v.dateregistre AS DATE) BETWEEN %s AND %s"
                params.extend([d1, d2])
            sql += " ORDER BY v.dateregistre DESC LIMIT 200"
            cur.execute(sql, tuple(params))
            for r in cur.fetchall():
                dt = r[2].strftime("%d/%m/%Y") if hasattr(r[2], "strftime") else (str(r[2]) if r[2] else "")
                tree_fact.insert("", "end", values=(r[0], r[1], dt, r[3], r[4], r[5], r[6]))
            self._refresh_alternating(tree_fact)
        except Exception as e:
            self._error("Erreur", f"Chargement factures échoué: {e}")
        finally:
            try:
                if cur:
                    cur.close()
            except Exception:
                pass
            conn.close()

        self._popup_filter_factures(tree_fact)

    def _popup_filter_factures(self, tree_fact: ttk.Treeview) -> None:
        """Filtre local (sans requery) sur recherche facture/client."""
        terme = (self._fact_search.get() or "").strip().lower() if hasattr(self, "_fact_search") else ""
        for iid in tree_fact.get_children():
            vals = tree_fact.item(iid).get("values") or []
            if not vals:
                continue
            ref = str(vals[0]).lower()
            cli = str(vals[1]).lower()
            ok = True if not terme else (terme in ref or terme in cli)
            if ok:
                tree_fact.reattach(iid, "", "end")
            else:
                tree_fact.detach(iid)

    # ─────────────────────────────────────────────────────────────────────
    # ÉTAPE 4 — Historique unifié (attentes + BL agrégés)
    # ─────────────────────────────────────────────────────────────────────
    def load_history(self) -> None:
        for iid in self.tree_histo.get_children():
            self.tree_histo.delete(iid)

        conn = self.connect_db()
        if not conn:
            return
        cur = None
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    a.refvente,
                    a.idclient,
                    a.idmag,
                    COALESCE(c.nomcli,'') AS nomcli,
                    SUM(COALESCE(a.qt_a_livrer, 0)) AS total_attendu,
                    SUM(COALESCE(a.qt_bl,0)) AS total_bl,
                    SUM(GREATEST(COALESCE(a.qt_a_livrer, 0) - COALESCE(a.qt_bl,0), 0)) AS reste,
                    SUM(CASE WHEN COALESCE(a.statut,'EN_ATTENTE')='ANNULEE' THEN 1 ELSE 0 END) AS nb_annulees,
                    COUNT(*) AS nb_lignes
                FROM tb_livraisoncli_attente a
                LEFT JOIN tb_client c ON a.idclient = c.idclient
                GROUP BY a.refvente, a.idclient, a.idmag, c.nomcli
                ORDER BY a.refvente DESC
                """
            )
            rows = cur.fetchall()
            for r in rows:
                refvente = r[0]
                idclient = int(r[1] or 0)
                idmag = int(r[2] or 0)
                nomcli = r[3] or ""
                total_attendu = float(r[4] or 0)
                total_bl = float(r[5] or 0)
                reste = float(r[6] or 0)
                nb_annulees = int(r[7] or 0)
                nb_lignes = int(r[8] or 0)

                # Statut global (affichage)
                if nb_lignes > 0 and nb_annulees == nb_lignes:
                    statut = "ANNULEE"
                elif total_attendu > 0 and reste <= 1e-9:
                    statut = "LIVRÉ"
                elif total_bl > 0:
                    statut = "PARTIEL"
                else:
                    statut = "EN_ATTENTE"

                tag = {
                    "EN_ATTENTE": "st_en_attente",
                    "PARTIEL": "st_partiel",
                    "LIVRÉ": "st_livre",
                    "ANNULEE": "st_annulee",
                }.get(statut, "")

                self.tree_histo.insert(
                    "",
                    "end",
                    values=(
                        refvente,
                        nomcli,
                        statut,
                        self._format(total_attendu),
                        self._format(total_bl),
                        self._format(reste),
                        idclient,
                        idmag,
                    ),
                    tags=(tag,) if tag else (),
                )
            self._refresh_alternating(self.tree_histo)
        except Exception as e:
            messagebox.showerror("Erreur", f"Chargement historique échoué: {e}")
        finally:
            try:
                if cur:
                    cur.close()
            except Exception:
                pass
            conn.close()

        self._filter_history()

    def _filter_history(self) -> None:
        terme = (self.entry_search.get() or "").strip().lower() if hasattr(self, "entry_search") else ""
        st = self.combo_statut.get() if hasattr(self, "combo_statut") else "Tous"

        for iid in self.tree_histo.get_children():
            vals = self.tree_histo.item(iid).get("values") or []
            if not vals:
                continue
            refvente = str(vals[0]).lower()
            client = str(vals[1]).lower()
            statut = str(vals[2])
            ok_search = True if not terme else (terme in refvente or terme in client)
            ok_statut = True if st == "Tous" else (statut == st)
            if ok_search and ok_statut:
                self.tree_histo.reattach(iid, "", "end")
            else:
                self.tree_histo.detach(iid)

    # ─────────────────────────────────────────────────────────────────────
    # ÉTAPE 6 — Détail livraison (double clic)
    # ─────────────────────────────────────────────────────────────────────
    def open_detail_popup(self) -> None:
        sel = self.tree_histo.selection()
        if not sel:
            return
        vals = self.tree_histo.item(sel[0]).get("values") or []
        if not vals:
            return

        refvente = str(vals[0])
        idclient = int(vals[6] or 0)
        idmag = int(vals[7] or 0)

        info = self._get_facture_info(refvente)
        nomcli = info.get("nomcli", str(vals[1] or ""))
        magasin = info.get("magasin", "")
        datevente = info.get("datevente", "")

        win = ctk.CTkToplevel(self)
        win.title(f"Détail Livraison — {refvente}")
        win.geometry("1180x720")
        win.attributes("-topmost", True)
        Theme.apply_toplevel(win)

        root = styled.frame(win)
        root.pack(fill="both", expand=True, padx=16, pady=16)
        # Layout haut/bas (au lieu de gauche/droite)
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=3)   # articles
        root.grid_rowconfigure(2, weight=2)   # historique BL

        # Header
        hdr = styled.card(root)
        hdr.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        h = styled.frame(hdr)
        h.pack(fill="x", padx=18, pady=14)
        styled.label_heading(h, text="Détail Livraison").pack(anchor="w")

        badges = styled.frame(h)
        badges.pack(fill="x", pady=(8, 0))
        styled.badge(badges, text=f"Facture: {refvente}", variant="primary").pack(side="left")
        styled.badge(badges, text=f"Client: {nomcli or '---'}", variant="info").pack(side="left", padx=(8, 0))
        styled.badge(badges, text=f"Magasin: {magasin or '---'}", variant="neutral").pack(side="left", padx=(8, 0))
        if datevente:
            styled.badge(badges, text=f"Date: {datevente}", variant="neutral").pack(side="left", padx=(8, 0))

        # Left: lignes
        panel_lines = styled.card(root)
        panel_lines.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        li = styled.frame(panel_lines)
        li.pack(fill="both", expand=True, padx=12, pady=12)
        styled.label_muted(li, text="Articles (attente / livré / reste / à livrer maintenant)").pack(anchor="w", pady=(0, 8))

        cols = ("code", "designation", "unite", "attente", "livre", "reste", "a_livrer", "_idarticle", "_idunite", "_idmag")
        tree = ttk.Treeview(li, columns=cols, show="headings", height=16, style="iJeery.Treeview")
        self._configure_alternating(tree)

        headers = [
            ("code", "Code", 90, "center"),
            ("designation", "Désignation", 320, "w"),
            ("unite", "Unité", 90, "center"),
            ("attente", "Attente", 110, "e"),
            ("livre", "Déjà livré", 110, "e"),
            ("reste", "Reste", 110, "e"),
            ("a_livrer", "À livrer", 110, "e"),
        ]
        for k, t, w, a in headers:
            tree.heading(k, text=t)
            tree.column(k, width=w, anchor=a, stretch=False)
        for k in ("_idarticle", "_idunite", "_idmag"):
            tree.heading(k, text="")
            tree.column(k, width=0, stretch=False)

        scroll_y = ttk.Scrollbar(li, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)

        # Bottom: historique BL
        panel_bl = styled.card(root)
        panel_bl.grid(row=2, column=0, sticky="nsew")
        ri = styled.frame(panel_bl)
        ri.pack(fill="both", expand=True, padx=12, pady=12)
        styled.label_muted(ri, text="Historique Bons de Livraison (BL) — lecture seule").pack(anchor="w", pady=(0, 8))

        cols2 = ("refliv", "date", "code", "qte")
        tree_bl = ttk.Treeview(ri, columns=cols2, show="headings", height=16, style="iJeery.Treeview")
        self._configure_alternating(tree_bl)
        for k, t, w, a in [
            ("refliv", "BL", 120, "center"),
            ("date", "Date", 120, "center"),
            ("code", "Code", 90, "center"),
            ("qte", "Qté", 90, "e"),
        ]:
            tree_bl.heading(k, text=t)
            tree_bl.column(k, width=w, anchor=a, stretch=False)
        scroll_y2 = ttk.Scrollbar(ri, orient="vertical", command=tree_bl.yview)
        tree_bl.configure(yscrollcommand=scroll_y2.set)
        scroll_y2.pack(side="right", fill="y")
        tree_bl.pack(side="left", fill="both", expand=True)

        # Bottom actions
        actions = styled.frame(root)
        actions.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        styled.button_secondary(actions, text="Fermer", icon="✕", command=win.destroy, width=120).pack(side="left")

        def _annuler_facture():
            if not self._ask_yes_no("Annuler", f"Annuler toutes les attentes pour la facture {refvente} ?", parent=win):
                return
            try:
                conn = self.connect_db()
                if not conn:
                    return
                cur = conn.cursor()
                cur.execute(
                    "UPDATE tb_livraisoncli_attente SET statut='ANNULEE', iduser=%s WHERE refvente=%s",
                    (self.user_id, refvente),
                )
                conn.commit()
                cur.close()
                conn.close()
                self.load_history()
                self._load_detail_tables(refvente, tree, tree_bl)
            except Exception as e:
                self._error("Erreur", str(e), parent=win)

        def _annuler_ligne():
            sel_line = tree.selection()
            if not sel_line:
                self._warn("Sélection", "Sélectionnez une ligne d'article à annuler.", parent=win)
                return
            vline = tree.item(sel_line[0]).get("values") or []
            if not vline:
                return
            idarticle = int(vline[7]); idunite = int(vline[8]); idmag_line = int(vline[9])
            if not self._ask_yes_no("Annuler", f"Annuler l'attente pour {vline[0]} — {vline[1]} ?", parent=win):
                return
            try:
                self.repo.cancel_attente(refvente, idarticle, idunite, idmag_line, int(self.user_id))
                self.load_history()
                self._load_detail_tables(refvente, tree, tree_bl)
            except Exception as e:
                self._error("Erreur", str(e), parent=win)

        styled.button_danger(actions, text="Annuler ligne", icon="🧾", command=_annuler_ligne, width=150).pack(side="right", padx=(8, 0))
        styled.button_danger(actions, text="Annuler facture", icon="🛑", command=_annuler_facture, width=170).pack(side="right", padx=(8, 0))

        def _creer_bl():
            self._detail_create_bl(
                refvente=refvente,
                idclient=idclient,
                tree_lines=tree,
                magasin_label=magasin,
                client_label=nomcli,
            )
            # refresh both views
            self._load_detail_tables(refvente, tree, tree_bl)
            self.load_history()

        styled.button_success(actions, text="Créer Bon de Livraison", icon="📄", command=_creer_bl, width=220).pack(side="right")

        # Load data into detail tables
        self._load_detail_tables(refvente, tree, tree_bl)
        tree.bind("<Double-1>", lambda _e: self._detail_edit_qty(tree))

    # ─────────────────────────────────────────────────────────────────────
    # ÉTAPE 7 — Génération BL + PDF A5 paysage
    # ─────────────────────────────────────────────────────────────────────
    def _detail_create_bl(
        self,
        refvente: str,
        idclient: int,
        tree_lines: ttk.Treeview,
        magasin_label: str,
        client_label: str,
    ) -> None:
        if self.user_id is None:
            self._error("Erreur", "Aucun utilisateur connecté.")
            return

        # Collecter lignes à livrer maintenant (q>0, q<=reste)
        lignes: List[Dict[str, Any]] = []
        for iid in tree_lines.get_children():
            v = tree_lines.item(iid).get("values") or []
            if not v:
                continue
            reste = self._parse_float(v[5])        # "Reste"
            q = self._parse_float(v[6])            # "À livrer"
            if q <= 0:
                continue
            if q > reste + 1e-9:
                q = reste
            if q <= 0:
                continue

            idarticle = int(v[7])
            idunite = int(v[8])
            idmag = int(v[9])

            lignes.append({
                "idmag": idmag,
                "idarticle": idarticle,
                "idunite": idunite,
                "qtlivrecli": float(q),
            })

        if not lignes:
            self._warn("BL", "Aucune quantité à livrer (à livrer = 0).")
            return

        if not self._ask_yes_no("Confirmation", f"Créer un Bon de Livraison pour la facture {refvente} ?"):
            return

        refliv = self._generate_bl_ref()

        # Enrichir avec qtvente de référence (pour tb_livraisoncli.qtvente)
        conn = self.connect_db()
        if not conn:
            self._error("DB", "Connexion DB impossible.")
            return
        cur = None
        operateur = ""
        try:
            cur = conn.cursor()
            try:
                cur.execute("SELECT nomuser, prenomuser FROM tb_users WHERE iduser=%s", (self.user_id,))
                u = cur.fetchone()
                if u:
                    operateur = f"{u[0] or ''} {u[1] or ''}".strip()
            except Exception:
                operateur = ""

            # idvente pour calcul qtvente
            cur.execute("SELECT id FROM tb_vente WHERE refvente=%s LIMIT 1", (refvente,))
            r = cur.fetchone()
            idvente = int(r[0]) if r and r[0] is not None else 0

            for l in lignes:
                try:
                    cur.execute(
                        """
                        SELECT COALESCE(SUM(qtvente),0)
                        FROM tb_ventedetail
                        WHERE idvente=%s AND idarticle=%s AND idunite=%s AND idmag=%s
                        """,
                        (idvente, l["idarticle"], l["idunite"], l["idmag"]),
                    )
                    l["qtvente"] = float((cur.fetchone() or [0])[0] or 0)
                except Exception:
                    l["qtvente"] = 0.0
        finally:
            try:
                if cur:
                    cur.close()
            except Exception:
                pass
            conn.close()

        # Écriture BL + MAJ attente (via repo)
        try:
            self.repo.create_bl(
                refliv=refliv,
                refvente=refvente,
                idclient=int(idclient or 0),
                iduser=int(self.user_id),
                lignes=lignes,
            )
        except Exception as e:
            self._error("Erreur", f"Création BL échouée: {e}")
            return

        # PDF A5 paysage (modèle bon réception/mouvements)
        try:
            etat = EtatPDFMouvements()
            etat.connect_db()
            colonnes = ("Code", "Désignation", "Unité", "Qté")

            # Recharger code/designation/unité pour le PDF
            pdf_rows: List[Tuple[str, str, str, str]] = []
            conn2 = self.connect_db()
            if conn2:
                cur2 = None
                try:
                    cur2 = conn2.cursor()
                    for l in lignes:
                        cur2.execute(
                            """
                            SELECT u.codearticle, a.designation, u.designationunite
                            FROM tb_unite u
                            INNER JOIN tb_article a ON u.idarticle=a.idarticle
                            WHERE u.idarticle=%s AND u.idunite=%s
                            LIMIT 1
                            """,
                            (l["idarticle"], l["idunite"]),
                        )
                        r = cur2.fetchone()
                        code = (r[0] if r else "") or ""
                        des = (r[1] if r else "") or ""
                        unite = (r[2] if r else "") or ""
                        pdf_rows.append((code, des, unite, str(l["qtlivrecli"])))
                finally:
                    try:
                        if cur2:
                            cur2.close()
                    except Exception:
                        pass
                    conn2.close()

            table_data = (colonnes, pdf_rows)
            output_path = os.path.join(os.getcwd(), f"Livraison_{refliv.replace('-', '_')}_A5.pdf")
            etat._build_pdf_a5(
                output_path=output_path,
                titre_entete="BON DE LIVRAISON",
                reference=refliv,
                date_operation=datetime.now().strftime("%d/%m/%Y"),
                magasin=magasin_label or "",
                operateur=operateur or "",
                table_data=table_data,
                description=f"Livraison client — Facture {refvente} — Client {client_label}",
                responsable_1="Livreur",
                responsable_2="Client",
            )
            try:
                etat.close_db()
            except Exception:
                pass
            try:
                if os.name == "nt":
                    os.startfile(output_path)  # type: ignore[attr-defined]
            except Exception:
                pass
        except Exception as e:
            # Le BL est déjà créé: on n'annule pas. On signale juste l'échec PDF.
            self._warn("PDF", f"BL créé, mais génération PDF échouée: {e}")

        self._info("Succès", f"BL {refliv} enregistré.")

    def _get_facture_info(self, refvente: str) -> Dict[str, str]:
        conn = self.connect_db()
        if not conn:
            return {}
        cur = None
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT COALESCE(c.nomcli,''), COALESCE(m.designationmag,''), v.dateregistre
                FROM tb_vente v
                LEFT JOIN tb_client c ON v.idclient=c.idclient
                LEFT JOIN tb_magasin m ON v.idmag=m.idmag
                WHERE v.refvente=%s
                LIMIT 1
                """,
                (refvente,),
            )
            r = cur.fetchone()
            if not r:
                return {}
            dt = r[2].strftime("%d/%m/%Y") if hasattr(r[2], "strftime") else (str(r[2]) if r[2] else "")
            return {"nomcli": r[0] or "", "magasin": r[1] or "", "datevente": dt}
        except Exception:
            return {}
        finally:
            try:
                if cur:
                    cur.close()
            except Exception:
                pass
            conn.close()

    def _load_detail_tables(self, refvente: str, tree_lines: ttk.Treeview, tree_bl: ttk.Treeview) -> None:
        for iid in tree_lines.get_children():
            tree_lines.delete(iid)
        for iid in tree_bl.get_children():
            tree_bl.delete(iid)

        # Attentes
        attentes = self.repo.get_attentes(refvente=refvente)
        # BL historiques
        livs = self.repo.get_livraisons(refvente=refvente)

        # Map BL agrégé par article/unité/mag
        bl_sum: Dict[Tuple[int, int, int], float] = {}
        for l in livs:
            k = (int(l["idarticle"]), int(l["idunite"]), int(l["idmag"]))
            bl_sum[k] = bl_sum.get(k, 0.0) + float(l["qtlivrecli"] or 0)

        # enrich lines with article info (code/designation/unité)
        conn = self.connect_db()
        cur = None
        art_map: Dict[Tuple[int, int], Tuple[str, str, str]] = {}
        try:
            if conn:
                cur = conn.cursor()
                # load designation/code/unite for attente + BL pairs
                cur.execute(
                    """
                    SELECT u.codearticle, a.designation, u.designationunite, u.idarticle, u.idunite
                    FROM tb_unite u
                    INNER JOIN tb_article a ON u.idarticle=a.idarticle
                    WHERE (u.idarticle, u.idunite) IN (
                        SELECT DISTINCT idarticle, idunite FROM tb_livraisoncli_attente WHERE refvente=%s
                        UNION
                        SELECT DISTINCT idarticle, idunite FROM tb_livraisoncli WHERE refvente=%s
                    )
                    """,
                    (refvente, refvente),
                )
                for r in cur.fetchall():
                    art_map[(int(r[3]), int(r[4]))] = (r[0] or "", r[1] or "", r[2] or "")
        except Exception:
            art_map = {}
        finally:
            try:
                if cur:
                    cur.close()
            except Exception:
                pass
            try:
                if conn:
                    conn.close()
            except Exception:
                pass

        for a in attentes:
            idarticle = int(a["idarticle"])
            idunite = int(a["idunite"])
            idmag = int(a["idmag"])
            code, des, unite = art_map.get((idarticle, idunite), ("", "", ""))
            qt_att = float(a["qt_a_livrer"] or 0)
            qt_livre = float(bl_sum.get((idarticle, idunite, idmag), 0.0))
            qt_reste = calcul_reste(qt_att, float(a["qt_bl"] or 0))

            tree_lines.insert(
                "",
                "end",
                values=(
                    code,
                    des,
                    unite,
                    self._format(qt_att),
                    self._format(qt_livre),
                    self._format(qt_reste),
                    self._format(qt_reste),
                    idarticle,
                    idunite,
                    idmag,
                ),
            )
        self._refresh_alternating(tree_lines)

        for l in livs:
            d = l["dateregistre"]
            ds = d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else (str(d) if d else "")
            code, _des, _un = art_map.get((int(l["idarticle"]), int(l["idunite"])), ("", "", ""))
            tree_bl.insert(
                "",
                "end",
                values=(l["reflivcli"], ds, code or str(l["idarticle"]), self._format(l["qtlivrecli"])),
            )
        self._refresh_alternating(tree_bl)

    def _detail_edit_qty(self, tree_lines: ttk.Treeview) -> None:
        sel = tree_lines.selection()
        if not sel:
            return
        iid = sel[0]
        v = tree_lines.item(iid).get("values") or []
        if not v:
            return
        reste = self._parse_float(v[5])
        cur_qty = self._parse_float(v[6])

        dlg = ctk.CTkToplevel(self)
        dlg.title("Modifier quantité à livrer")
        dlg.geometry("520x260")
        dlg.attributes("-topmost", True)
        Theme.apply_toplevel(dlg)

        card = styled.card(dlg)
        card.pack(fill="both", expand=True, padx=16, pady=16)
        inner = styled.frame(card)
        inner.pack(fill="both", expand=True, padx=18, pady=18)

        styled.label_heading(inner, text="À livrer maintenant (BL)").pack(anchor="w")
        styled.label(inner, text=f"{v[0]} — {v[1]}", size=12, weight="bold").pack(anchor="w", pady=(6, 8))
        styled.label_muted(inner, text=f"Reste: {self._format(reste)}").pack(anchor="w", pady=(0, 10))

        row = styled.frame(inner)
        row.pack(fill="x")
        styled.label_muted(row, text="Quantité", width=120, anchor="w").pack(side="left")
        ent = styled.entry(row, placeholder=str(cur_qty))
        ent.insert(0, str(cur_qty))
        ent.pack(side="left", fill="x", expand=True)
        ent.focus()

        def _ok():
            q = self._parse_float(ent.get())
            if q < 0:
                self._warn("Quantité", "Quantité négative interdite.", parent=dlg)
                return
            if q > reste + 1e-9:
                self._warn("Quantité", "La quantité dépasse le reste.", parent=dlg)
                return
            nv = list(v)
            nv[6] = self._format(q)
            tree_lines.item(iid, values=nv)
            dlg.destroy()

        btns = styled.frame(inner)
        btns.pack(fill="x", pady=(12, 0))
        styled.button_secondary(btns, text="Annuler", icon="✕", command=dlg.destroy, width=120).pack(side="left")
        styled.button_success(btns, text="Valider", icon="✔", command=_ok, width=140).pack(side="right")

        ent.bind("<Return>", lambda _e: _ok())

    # ─────────────────────────────────────────────────────────────────────
    # Mode
    # ─────────────────────────────────────────────────────────────────────
    def set_mode(self, mode: str) -> None:
        self.mode_var.set(mode)
        if mode == "BL":
            self.mode_hint.configure(text="Saisis la quantité à livrer (BL) sur les lignes en attente.")
            self.btn_save.configure(text="💾  Enregistrer BL & PDF")
        else:
            self.mode_hint.configure(text="Définis la quantité à mettre en attente BL (total).")
            self.btn_save.configure(text="💾  Enregistrer attente")
        self._reload_facture_lines()

    # ─────────────────────────────────────────────────────────────────────
    # Sélection facture
    # ─────────────────────────────────────────────────────────────────────
    def ouvrir_selection_facture(self):
        top = ctk.CTkToplevel(self)
        top.title("Sélectionner Facture")
        top.geometry("760x560")
        top.attributes("-topmost", True)
        Theme.apply_toplevel(top)

        card = styled.card(top)
        card.pack(fill="both", expand=True, padx=16, pady=16)
        inner = styled.frame(card)
        inner.pack(fill="both", expand=True, padx=16, pady=16)

        styled.label_heading(inner, text="Choisir une facture").pack(anchor="w")

        frow = styled.frame(inner)
        frow.pack(fill="x", pady=(10, 10))
        styled.label_muted(frow, text="Date", width=60, anchor="w").pack(side="left")

        cal_container = styled.frame(frow)
        cal_container.pack(side="left", padx=(0, 10))
        ent_date = DateEntry(
            cal_container,
                             width=12, 
            background="darkblue",
            foreground="white",
                             borderwidth=2,
            date_pattern="yyyy-mm-dd",
            locale="fr_FR",
        )
        ent_date.pack()

        btn_today = styled.button_secondary(
            frow,
            text="Filtrer",
            icon="🔎",
            command=lambda: charger(ent_date.get_date().strftime("%Y-%m-%d")),
            width=120,
        )
        btn_today.pack(side="left")

        tree_f = ttk.Treeview(inner, columns=("ref", "client", "date", "idvente", "idcli", "idmag", "mag"), show="headings", height=16, style="iJeery.Treeview")
        self._configure_alternating(tree_f)
        for k, t, w in [("ref", "Facture", 140), ("client", "Client", 220), ("date", "Date", 120), ("mag", "Magasin", 180)]:
            tree_f.heading(k, text=t)
            tree_f.column(k, width=w, anchor="w" if k in ("client", "mag") else "center", stretch=False)
        for k in ("idvente", "idcli", "idmag"):
            tree_f.heading(k, text="")
            tree_f.column(k, width=0, stretch=False)
        tree_f.pack(fill="both", expand=True, pady=(0, 10))

        def charger(date_val: Optional[str] = None):
            for i in tree_f.get_children():
                tree_f.delete(i)

            conn = self.connect_db()
            if not conn:
                return

            cur = None
            try:
                cur = conn.cursor()
                base = """
                    SELECT v.refvente, c.nomcli, v.dateregistre, v.id, v.idclient, v.idmag, COALESCE(m.designationmag,'')
                    FROM tb_vente v
                    LEFT JOIN tb_client c ON v.idclient = c.idclient
                    LEFT JOIN tb_magasin m ON v.idmag = m.idmag
                    WHERE v.deleted = 0
                """
                if date_val:
                    cur.execute(
                        base + " AND CAST(v.dateregistre AS DATE) = %s ORDER BY v.dateregistre DESC",
                        (date_val,),
                    )
                else:
                    cur.execute(base + " ORDER BY v.dateregistre DESC LIMIT 80")

                for r in cur.fetchall():
                    d = r[2].strftime("%d/%m/%Y") if hasattr(r[2], "strftime") else str(r[2])
                    tree_f.insert("", "end", values=(r[0], r[1] or "", d, r[3], r[4], r[5], r[6]))

                self._refresh_alternating(tree_f)

            except Exception as e:
                messagebox.showerror("Erreur", str(e))
            finally:
                try:
                    if cur:
                        cur.close()
                except Exception:
                    pass
                conn.close()
        
        def valider():
            sel = tree_f.selection()
            if not sel:
                messagebox.showwarning("Sélection", "Veuillez sélectionner une facture.")
                return
            v = tree_f.item(sel[0]).get("values") or []
            self._set_selected_facture(
                refvente=v[0],
                nomcli=v[1],
                idvente=int(v[3]),
                idcli=int(v[4]) if v[4] is not None else None,
                idmag=int(v[5]) if v[5] is not None else None,
                magasin=v[6],
            )
            top.destroy()

        b = styled.frame(inner)
        b.pack(fill="x")
        styled.button_secondary(b, text="Fermer", icon="✕", command=top.destroy, width=120).pack(side="left")
        styled.button_success(b, text="Choisir", icon="✔", command=valider, width=140).pack(side="right")
        
        charger()

    def _set_selected_facture(self, refvente: str, nomcli: str, idvente: int, idcli: Optional[int], idmag: Optional[int], magasin: str) -> None:
        self.selected_ref_vente = refvente
        self.selected_nom_client = nomcli or ""
        self.selected_id_vente = idvente
        self.selected_id_client = idcli
        self.selected_id_mag = idmag
        self.selected_magasin = magasin or ""

        self.badge_facture.configure(text=f"Facture: {refvente}", fg_color=Colors.PRIMARY_LIGHT, text_color=Colors.PRIMARY)
        self.badge_client.configure(text=f"Client: {self.selected_nom_client or '---'}", fg_color=Colors.INFO_LIGHT, text_color=Colors.INFO_TEXT)
        self.badge_magasin.configure(text=f"Magasin: {self.selected_magasin or '---'}", fg_color=Colors.CLOUDS, text_color=Colors.TEXT_SECONDARY)
        self._reload_facture_lines()

    # ─────────────────────────────────────────────────────────────────────
    # Chargement lignes facture (vendu + attente + BL)
    # ─────────────────────────────────────────────────────────────────────
    def _reload_facture_lines(self) -> None:
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        if not self.selected_ref_vente or not self.selected_id_vente:
            self._refresh_alternating(self.tree)
            return
        
        conn = self.connect_db()
        if not conn:
            return
        cur = None
        try:
            cur = conn.cursor()

            # 1) Lignes vendues
            cur.execute(
                """
                SELECT
                    u.codearticle,
                    art.designation,
                    u.designationunite,
                    vd.qtvente,
                    vd.idarticle,
                    vd.idunite,
                    vd.idmag
                FROM tb_ventedetail vd
                INNER JOIN tb_article art ON vd.idarticle = art.idarticle
                INNER JOIN tb_unite u ON (vd.idarticle = u.idarticle AND vd.idunite = u.idunite)
                WHERE vd.idvente=%s AND COALESCE(vd.deleted,0)=0
                ORDER BY art.designation
                """,
                (self.selected_id_vente,),
            )
            vente_rows = cur.fetchall()

            # 2) Attentes (qt_a_livrer)
            cur.execute(
                """
                SELECT
                    idarticle, idunite, idmag,
                    COALESCE(qt_a_livrer, 0) AS qt_attente,
                    COALESCE(qt_bl, 0) AS qt_bl,
                    COALESCE(statut, 'EN_ATTENTE') AS statut
                FROM tb_livraisoncli_attente
                WHERE refvente=%s
                """,
                (self.selected_ref_vente,),
            )
            att_map: Dict[Tuple[int, int, int], Tuple[float, float, str]] = {}
            for a in cur.fetchall():
                att_map[(int(a[0]), int(a[1]), int(a[2]))] = (float(a[3] or 0), float(a[4] or 0), str(a[5] or "EN_ATTENTE"))

            # 3) BL déjà faits (historique agrégé)
            cur.execute(
                """
                SELECT idarticle, idunite, idmag, COALESCE(SUM(qtlivrecli),0)
                FROM tb_livraisoncli
                WHERE refvente=%s
                GROUP BY idarticle, idunite, idmag
                """,
                (self.selected_ref_vente,),
            )
            bl_map: Dict[Tuple[int, int, int], float] = {
                (int(r[0]), int(r[1]), int(r[2])): float(r[3] or 0)
                for r in cur.fetchall()
            }

            mode = self.mode_var.get()
            for r in vente_rows:
                code = r[0]
                des = r[1]
                unite = r[2]
                qt_vendue = float(r[3] or 0)
                idart = int(r[4])
                idun = int(r[5])
                idmag = int(r[6] or 0)

                qt_attente, qt_bl_att, _statut = att_map.get((idart, idun, idmag), (0.0, 0.0, "EN_ATTENTE"))
                qt_bl_info = bl_map.get((idart, idun, idmag), 0.0)
                qt_restant = max(qt_attente - qt_bl_att, 0.0)

                if mode == "BL":
                    qt_action = qt_restant if qt_restant > 0 else 0.0
                else:
                    qt_action = qt_attente if qt_attente > 0 else qt_vendue

                self.tree.insert(
                    "",
                    "end",
                    values=(
                        code,
                        des,
                        unite,
                        self._format(qt_vendue),
                        self._format(qt_attente),
                        self._format(qt_bl_info),
                        self._format(qt_restant),
                        self._format(qt_action),
                        idart,
                        idun,
                        idmag,
                    ),
                )

            self._refresh_alternating(self.tree)

        except Exception as e:
            messagebox.showerror("Erreur", f"Chargement facture échoué: {e}")
        finally:
            try:
                if cur:
                    cur.close()
            except Exception:
                pass
            conn.close()

    def modifier_quantite(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        v = self.tree.item(iid).get("values") or []
        if not v:
            return
            
        mode = self.mode_var.get()
        titre = "Modifier quantité BL" if mode == "BL" else "Modifier quantité attente"

        dlg = ctk.CTkToplevel(self)
        dlg.title(titre)
        dlg.geometry("520x260")
        dlg.attributes("-topmost", True)
        Theme.apply_toplevel(dlg)

        card = styled.card(dlg)
        card.pack(fill="both", expand=True, padx=16, pady=16)
        inner = styled.frame(card)
        inner.pack(fill="both", expand=True, padx=18, pady=18)

        styled.label_heading(inner, text=titre).pack(anchor="w")
        styled.label(inner, text=f"{v[0]} — {v[1]} ({v[2]})", size=12, weight="bold").pack(anchor="w", pady=(6, 10))

        row = styled.frame(inner)
        row.pack(fill="x", pady=(0, 12))
        styled.label_muted(row, text="Quantité", width=120, anchor="w").pack(side="left")
        ent = styled.entry(row, placeholder=str(v[7]))
        ent.insert(0, str(v[7]))
        ent.pack(side="left", fill="x", expand=True)
        ent.focus()

        def _ok():
            q = self._parse_float(ent.get())
            if q < 0:
                messagebox.showwarning("Quantité", "La quantité ne peut pas être négative.")
                return
            # contraintes
            vendu = self._parse_float(v[3])
            reste = self._parse_float(v[6])
            if mode == "BL" and q > reste + 1e-9:
                messagebox.showwarning("Quantité", "La quantité dépasse le reste en attente.")
                return
            if mode == "ATTENTE" and q > vendu + 1e-9:
                messagebox.showwarning("Quantité", "La quantité dépasse la quantité vendue.")
                return

            nv = list(v)
            nv[7] = self._format(q)
            self.tree.item(iid, values=nv)
            dlg.destroy()

        btns = styled.frame(inner)
        btns.pack(fill="x", pady=(10, 0))
        styled.button_secondary(btns, text="Annuler", icon="✕", command=dlg.destroy, width=120).pack(side="left")
        styled.button_success(btns, text="Valider", icon="✔", command=_ok, width=140).pack(side="right")

        ent.bind("<Return>", lambda _e: _ok())

    # ─────────────────────────────────────────────────────────────────────
    # Save actions
    # ─────────────────────────────────────────────────────────────────────
    def on_save(self) -> None:
        if self.user_id is None:
            messagebox.showerror("Erreur", "Aucun utilisateur connecté.")
            return
        if not self.selected_ref_vente or not self.selected_id_vente:
            messagebox.showwarning("Facture", "Veuillez choisir une facture.")
            return
        if self.mode_var.get() == "ATTENTE":
            self._save_attente()
        else:
            self._save_bl()

    def _save_attente(self) -> None:
        conn = self.connect_db()
        if not conn:
            return
        cur = None
        try:
            cur = conn.cursor()
            changed = 0

            for iid in self.tree.get_children():
                v = self.tree.item(iid).get("values") or []
                if not v:
                    continue

                vendu = self._parse_float(v[3])
                qt_a_livrer = self._parse_float(v[7])
                if qt_a_livrer < 0:
                    qt_a_livrer = 0.0
                if qt_a_livrer > vendu + 1e-9:
                    qt_a_livrer = vendu

                idart = int(v[8])
                idun = int(v[9])
                idmag = int(v[10] or (self.selected_id_mag or 0))
                idcli = int(self.selected_id_client or 0)

                cur.execute(
                    """
                    INSERT INTO tb_livraisoncli_attente
                        (refvente, idarticle, idunite, idmag, idclient,
                         qt_a_livrer, qt_bl, statut, dateregistre, iduser)
                    VALUES (%s,%s,%s,%s,%s,%s,
                            COALESCE((SELECT qt_bl FROM tb_livraisoncli_attente WHERE refvente=%s AND idmag=%s AND idarticle=%s AND idunite=%s),0),
                            'EN_ATTENTE', NOW(), %s)
                    ON CONFLICT (refvente, idmag, idarticle, idunite)
                    DO UPDATE SET
                        qt_a_livrer = EXCLUDED.qt_a_livrer,
                        statut = CASE
                            WHEN EXCLUDED.qt_a_livrer <= COALESCE(tb_livraisoncli_attente.qt_bl,0) + 1e-9 THEN 'LIVRÉ'
                            WHEN EXCLUDED.qt_a_livrer <= 0 THEN 'ANNULÉ'
                            ELSE 'EN_ATTENTE'
                        END,
                        iduser = EXCLUDED.iduser
                    """,
                    (
                        self.selected_ref_vente,
                        idart,
                        idun,
                        idmag,
                        idcli,
                        qt_a_livrer,
                        self.selected_ref_vente,
                        idmag,
                        idart,
                        idun,
                        self.user_id,
                    ),
                )
                changed += 1

            conn.commit()
            messagebox.showinfo("Succès", f"Attente BL mise à jour ({changed} lignes).")
            self._reload_facture_lines()

        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            messagebox.showerror("Erreur", f"Enregistrement attente échoué: {e}")
        finally:
            try:
                if cur:
                    cur.close()
            except Exception:
                pass
            conn.close()

    def _save_bl(self) -> None:
        # collect lignes
        lignes: List[Dict[str, Any]] = []
        for iid in self.tree.get_children():
            v = self.tree.item(iid).get("values") or []
            if not v:
                continue
            reste = self._parse_float(v[6])
            q = self._parse_float(v[7])
            if q <= 0:
                continue
            if q > reste + 1e-9:
                q = reste
            # RÈGLE CRITIQUE: ne jamais insérer qtlivrecli = 0
            if q <= 0:
                continue
            lignes.append({
                "code": v[0],
                "designation": v[1],
                "unite": v[2],
                "qte": q,
                "idarticle": int(v[8]),
                "idunite": int(v[9]),
                "idmag": int(v[10] or (self.selected_id_mag or 0)),
            })

        if not lignes:
            messagebox.showwarning("BL", "Aucune quantité BL à enregistrer.")
            return

        refliv = self._generate_bl_ref()
        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()

            # nom opérateur
            operateur = ""
            try:
                cur.execute("SELECT nomuser, prenomuser FROM tb_users WHERE iduser=%s", (self.user_id,))
                u = cur.fetchone()
                if u:
                    operateur = f"{u[0] or ''} {u[1] or ''}".strip()
            except Exception:
                operateur = ""

            idcli = int(self.selected_id_client or 0)
            idvente = int(self.selected_id_vente or 0)
            idmag_def = int(self.selected_id_mag or 0)

            for l in lignes:
                q = float(l["qte"])
                idart = int(l["idarticle"])
                idun = int(l["idunite"])
                idmag = int(l["idmag"] or idmag_def)

                # vendu de référence
                cur.execute(
                    "SELECT COALESCE(SUM(qtvente),0) FROM tb_ventedetail WHERE idvente=%s AND idarticle=%s AND idunite=%s AND idmag=%s",
                    (idvente, idart, idun, idmag),
                )
                qtvente = float((cur.fetchone() or [0])[0] or 0)

                cur.execute(
                    """
                    INSERT INTO tb_livraisoncli
                    (reflivcli, refvente, idmag, idarticle, idunite, qtvente, qtlivrecli, dateregistre, iduser, idclient)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (refliv, self.selected_ref_vente, idmag, idart, idun, qtvente, q, datetime.now(), self.user_id, idcli),
                )

                cur.execute(
                    """
                    UPDATE tb_livraisoncli_attente
                       SET qt_bl = COALESCE(qt_bl,0) + %s,
                           iduser = %s,
                           statut = CASE
                                WHEN COALESCE(qt_a_livrer,0) <= (COALESCE(qt_bl,0) + %s) + 1e-9 THEN 'LIVRÉ'
                                WHEN (COALESCE(qt_bl,0) + %s) > 0 THEN 'PARTIEL'
                                ELSE 'EN_ATTENTE'
                           END
                     WHERE refvente=%s AND idmag=%s AND idarticle=%s AND idunite=%s
                    """,
                    (q, self.user_id, q, q, self.selected_ref_vente, idmag, idart, idun),
                )

            conn.commit()

            # PDF A5 paysage (modèle mouvements)
            try:
                etat = EtatPDFMouvements()
                etat.connect_db()
                colonnes = ("Code", "Désignation", "Unité", "Qté")
                data_rows = [(x["code"], x["designation"], x["unite"], str(x["qte"])) for x in lignes]
                table_data = (colonnes, data_rows)
                output_path = os.path.join(os.getcwd(), f"Livraison_{refliv.replace('-', '_')}_A5.pdf")
                etat._build_pdf_a5(
                    output_path=output_path,
                    titre_entete="BON DE LIVRAISON",
                    reference=refliv,
                    date_operation=datetime.now().strftime("%d/%m/%Y"),
                    magasin=self.selected_magasin,
                    operateur=operateur,
                    table_data=table_data,
                    description=f"Livraison client — Facture {self.selected_ref_vente}",
                    responsable_1="Livreur",
                    responsable_2="Client",
                )
                try:
                    etat.close_db()
                except Exception:
                    pass
                try:
                    if os.name == "nt":
                        os.startfile(output_path)  # type: ignore[attr-defined]
                except Exception:
                    pass
            except Exception:
                pass

            messagebox.showinfo("Succès", f"BL {refliv} enregistré.")
            self._reload_facture_lines()
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            messagebox.showerror("Erreur", f"Enregistrement BL échoué: {e}")
        finally:
            try:
                cur.close()
            except Exception:
                pass
            conn.close()

    def reinitialiser(self):
        self.selected_ref_vente = None
        self.selected_id_client = None
        self.selected_id_mag = None
        self.selected_id_vente = None
        self.selected_nom_client = ""
        self.selected_magasin = ""
        self.badge_facture.configure(text="Facture: ---", fg_color=Colors.CLOUDS, text_color=Colors.TEXT_SECONDARY)
        self.badge_client.configure(text="Client: ---", fg_color=Colors.CLOUDS, text_color=Colors.TEXT_SECONDARY)
        self.badge_magasin.configure(text="Magasin: ---", fg_color=Colors.CLOUDS, text_color=Colors.TEXT_SECONDARY)
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self._refresh_alternating(self.tree)


if __name__ == "__main__":
    root = ctk.CTk()
    root.title("Livraison Client")
    root.geometry("1100x720")
    Theme.apply(root)
    app = PageLivraisonClient(root, id_user_connecte=1)
    app.pack(fill="both", expand=True)
    root.mainloop()
