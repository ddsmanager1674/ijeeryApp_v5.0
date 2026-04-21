import customtkinter as ctk
from tkinter import messagebox, ttk
import psycopg2
import json
from datetime import datetime
from resource_utils import get_config_path
from log_utils import AppLogger


# ══════════════════════════════════════════════════════════════════════════════
#  FENÊTRE DÉTAIL TRANSPORTEUR (double-clic)
#  Sidebar gauche : infos + édition inline
#  Droite         : historique des commandes
# ══════════════════════════════════════════════════════════════════════════════

class FenetreDetailTransporteur(ctk.CTkToplevel):
    """Fenêtre affichant le profil d'un transporteur et son historique de commandes."""

    def __init__(self, parent, transporteur_data, connect_db_fn, formater_nombre_fn):
        super().__init__(parent)
        self.transporteur      = transporteur_data   # dict: id, nom, contact, adresse
        self.connect_db        = connect_db_fn
        self.formater_nombre   = formater_nombre_fn

        self.title(f"Transporteur — {self.transporteur['nom']}")
        self.geometry("1050x620")
        self.grab_set()
        self.resizable(True, True)

        self._build_ui()
        self._charger_historique()

    # ── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ─── SIDEBAR GAUCHE ─────────────────────────────────────────────
        self.sidebar = ctk.CTkFrame(self, width=280, fg_color="#F0F4FF",
                                    border_width=1, border_color="#CBD5E1")
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0, weight=1)

        # Avatar / Icône
        avatar = ctk.CTkLabel(self.sidebar, text="🚚",
                              font=ctk.CTkFont(size=48))
        avatar.grid(row=0, column=0, pady=(20, 5))

        nom_lbl = ctk.CTkLabel(self.sidebar, text=self.transporteur['nom'],
                               font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                               text_color="#1E3A5F", wraplength=240)
        nom_lbl.grid(row=1, column=0, padx=15, pady=(0, 15))

        ctk.CTkFrame(self.sidebar, height=1, fg_color="#CBD5E1").grid(
            row=2, column=0, sticky="ew", padx=15, pady=5)

        # Champs éditables
        def _make_field(parent, label, row, value, readonly=False):
            ctk.CTkLabel(parent, text=label,
                         font=ctk.CTkFont(size=10, weight="bold"),
                         text_color="#64748B").grid(row=row*2, column=0,
                                                     sticky="w", padx=15, pady=(8,0))
            entry = ctk.CTkEntry(parent, width=240,
                                 state="readonly" if readonly else "normal")
            entry.insert(0, value or "")
            if readonly:
                entry.configure(state="readonly")
            entry.grid(row=row*2+1, column=0, padx=15, pady=(2, 0))
            return entry

        self.entry_nom     = _make_field(self.sidebar, "Nom",     2, self.transporteur['nom'])
        self.entry_contact = _make_field(self.sidebar, "Contact", 3, self.transporteur['contact'])
        self.entry_adresse = _make_field(self.sidebar, "Adresse", 4, self.transporteur['adresse'])

        # Boutons actions
        frame_btns = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        frame_btns.grid(row=10, column=0, padx=15, pady=20, sticky="ew")
        frame_btns.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(frame_btns, text="💾 Sauvegarder",
                      fg_color="#27AE60", hover_color="#1E8449",
                      command=self._sauvegarder,
                      font=ctk.CTkFont(size=11)).grid(row=0, column=0, padx=3, sticky="ew")

        ctk.CTkButton(frame_btns, text="✕ Fermer",
                      fg_color="#636E72", hover_color="#2D3436",
                      command=self.destroy,
                      font=ctk.CTkFont(size=11)).grid(row=0, column=1, padx=3, sticky="ew")

        # ─── ZONE DROITE : HISTORIQUE ────────────────────────────────────
        right_frame = ctk.CTkFrame(self, fg_color="#FFFFFF",
                                   border_width=1, border_color="#CBD5E1")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right_frame.grid_rowconfigure(1, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        # Header droite
        hdr = ctk.CTkFrame(right_frame, fg_color="#2C3E50", corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(hdr, text="📦 Historique des commandes",
                     font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                     text_color="white").pack(side="left", padx=15, pady=10)

        self.lbl_nb_cmd = ctk.CTkLabel(hdr, text="",
                                       font=ctk.CTkFont(size=11),
                                       text_color="#BDC3C7")
        self.lbl_nb_cmd.pack(side="right", padx=15)

        # Treeview historique
        tree_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        cols = ("Référence", "Date", "Fournisseur", "Total", "Statut")
        self.tree_hist = ttk.Treeview(tree_frame, columns=cols, show="headings", height=18)

        style = ttk.Style()
        style.configure("Treeview",
                        rowheight=24,
                        font=('Segoe UI', 9),
                        background="#FFFFFF",
                        fieldbackground="#FFFFFF",
                        foreground="#2C3E50",
                        borderwidth=0)
        style.configure("Treeview.Heading",
                        background="#ECF0F1",
                        foreground="#2C3E50",
                        font=('Segoe UI', 9, 'bold'))
        style.map("Treeview", background=[('selected', '#D6EAF8')])

        self.tree_hist.tag_configure("row_even", background="#FFFFFF")
        self.tree_hist.tag_configure("row_odd",  background="#F8F9FA")
        self.tree_hist.tag_configure("livree",   foreground="#27AE60")
        self.tree_hist.tag_configure("attente",  foreground="#E67E22")

        widths = {"Référence": 120, "Date": 130, "Fournisseur": 200, "Total": 110, "Statut": 120}
        for col in cols:
            self.tree_hist.heading(col, text=col)
            self.tree_hist.column(col, width=widths[col],
                                  anchor="e" if col == "Total" else "w")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_hist.yview)
        self.tree_hist.configure(yscrollcommand=vsb.set)
        self.tree_hist.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        # Footer stats
        self.lbl_total_trans = ctk.CTkLabel(right_frame, text="",
                                             font=ctk.CTkFont(size=11, weight="bold"),
                                             text_color="#2C3E50")
        self.lbl_total_trans.grid(row=2, column=0, sticky="e", padx=15, pady=(0, 8))

    # ── Chargement historique ────────────────────────────────────────────────

    def _charger_historique(self):
        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    c.idcom,
                    c.refcom,
                    c.datecom,
                    COALESCE(f.nomfrs, 'Fournisseur non précisé') AS fournisseur,
                    COALESCE(c.totcmd, 0) AS total,
                    (SELECT COUNT(*) FROM tb_commandedetail d WHERE d.idcom = c.idcom) AS nb_lignes,
                    (SELECT COUNT(*) FROM tb_commandedetail d
                     WHERE d.idcom = c.idcom AND d.qtcmd > 0 AND d.qtlivre >= d.qtcmd) AS nb_livrees
                FROM tb_commande c
                LEFT JOIN tb_fournisseur f ON c.idfrs = f.idfrs
                WHERE c.idtransportuer = %s AND c.deleted = 0
                ORDER BY c.datecom DESC
            """, (self.transporteur['id'],))

            rows = cursor.fetchall()
            self.tree_hist.delete(*self.tree_hist.get_children())

            total_global = 0.0
            for idx, row in enumerate(rows):
                idcom, refcom, datecom, fournisseur, total, nb_lignes, nb_livrees = row
                date_str = datecom.strftime("%d/%m/%Y %H:%M") if datecom else "—"

                if nb_lignes > 0 and nb_livrees == nb_lignes:
                    statut = "✅ Livré"
                    extra_tag = "livree"
                elif nb_livrees > 0:
                    statut = "🔄 Partiel"
                    extra_tag = "attente"
                else:
                    statut = "⏳ En attente"
                    extra_tag = "attente"

                alt_tag = "row_even" if idx % 2 == 0 else "row_odd"
                self.tree_hist.insert("", "end",
                    values=(refcom or "—", date_str, fournisseur,
                            self.formater_nombre(total) + " Ar", statut),
                    tags=(alt_tag, extra_tag))
                total_global += float(total)

            nb = len(rows)
            self.lbl_nb_cmd.configure(
                text=f"{nb} commande{'s' if nb > 1 else ''}")
            self.lbl_total_trans.configure(
                text=f"Total transporté : {self.formater_nombre(total_global)} Ar")

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur chargement historique: {str(e)}")
        finally:
            if 'cursor' in locals():
                cursor.close()
            conn.close()

    # ── Sauvegarder modifications ────────────────────────────────────────────

    def _sauvegarder(self):
        nom     = self.entry_nom.get().strip()
        contact = self.entry_contact.get().strip()
        adresse = self.entry_adresse.get().strip()

        if not nom:
            messagebox.showwarning("Validation", "Le nom est obligatoire.")
            return

        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tb_transporteur
                SET nom = %s, contact = %s, adresse = %s
                WHERE idtransporteur = %s
            """, (nom, contact, adresse, self.transporteur['id']))
            conn.commit()
            messagebox.showinfo("Succès", "Transporteur mis à jour avec succès.")
            self.transporteur.update({'nom': nom, 'contact': contact, 'adresse': adresse})
            self.title(f"Transporteur — {nom}")
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de la mise à jour: {str(e)}")
        finally:
            if 'cursor' in locals():
                cursor.close()
            conn.close()


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE TRANSPORTEUR — CRUD + liste
# ══════════════════════════════════════════════════════════════════════════════

class PageTransporteur(ctk.CTkFrame):
    """
    Page de gestion des transporteurs.
    - Liste avec recherche
    - Formulaire création / modification
    - Suppression (soft delete)
    - Double-clic → FenetreDetailTransporteur
    """

    SQL_CREATE_TABLE = """
        CREATE TABLE IF NOT EXISTS tb_transporteur (
            idtransporteur SERIAL PRIMARY KEY,
            nom            VARCHAR(150) NOT NULL,
            contact        VARCHAR(100),
            adresse        VARCHAR(200),
            deleted        INTEGER DEFAULT 0
        );
    """

    def __init__(self, parent, iduser):
        super().__init__(parent)
        self.iduser         = iduser
        self.session_data = getattr(parent, "session_data", None) or {"user_id": self.iduser}
        self._logger = AppLogger(session_data=self.session_data, fallback_user_id=self.iduser)
        self.transporteur_selectionne = None   # dict courant pour édition

        self._assurer_table()
        self._build_ui()
        self.charger_transporteurs()

    # ── DB ──────────────────────────────────────────────────────────────────

    def connect_db(self):
        try:
            with open(get_config_path('config.json')) as f:
                config = json.load(f)
                db = config['database']
            return psycopg2.connect(
                host=db['host'], user=db['user'], password=db['password'],
                database=db['database'], port=db['port'])
        except Exception as e:
            messagebox.showerror("Connexion", f"Erreur DB: {str(e)}")
            return None

    def _assurer_table(self):
        """Crée la table tb_transporteur si elle n'existe pas encore."""
        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute(self.SQL_CREATE_TABLE)

            # Ajouter la colonne idtransportuer dans tb_commande si absente
            cur.execute("""
                ALTER TABLE tb_commande
                ADD COLUMN IF NOT EXISTS idtransportuer INTEGER;
            """)
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"[PageTransporteur] Erreur création table: {e}")
        finally:
            if 'cur' in locals():
                cur.close()
            conn.close()

    def formater_nombre(self, nombre):
        try:
            nombre = float(nombre)
            entier = int(nombre)
            dec    = abs(nombre - entier)
            s_ent  = f"{entier:,}".replace(',', '.')
            s_dec  = f"{dec:.2f}".split('.')[1]
            return f"{s_ent},{s_dec}"
        except:
            return "0,00"

    def _configure_alternating(self, tree):
        tree.tag_configure("row_even", background="#FFFFFF")
        tree.tag_configure("row_odd",  background="#F3F7FF")

    def _refresh_alternating(self, tree):
        for idx, item in enumerate(tree.get_children()):
            tree.item(item, tags=("row_even" if idx % 2 == 0 else "row_odd",))

    # ── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ═════════════ PANNEAU GAUCHE — Formulaire ═══════════════════════
        panel_left = ctk.CTkFrame(self, width=310, fg_color="#F8F9FA",
                                  border_width=1, border_color="#D5D8DC")
        panel_left.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)
        panel_left.grid_propagate(False)
        panel_left.grid_columnconfigure(0, weight=1)

        # Titre panneau gauche
        ctk.CTkLabel(panel_left,
                     text="🚚 Transporteur",
                     font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                     text_color="#2C3E50").grid(row=0, column=0, pady=(16, 4), padx=15, sticky="w")

        ctk.CTkFrame(panel_left, height=1, fg_color="#D5D8DC").grid(
            row=1, column=0, sticky="ew", padx=10, pady=4)

        # Champs du formulaire
        def _lbl(text, row):
            ctk.CTkLabel(panel_left, text=text,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color="#5D6D7E").grid(
                row=row, column=0, sticky="w", padx=15, pady=(10, 0))

        def _entry(row, placeholder=""):
            e = ctk.CTkEntry(panel_left, placeholder_text=placeholder,
                             height=34, width=270)
            e.grid(row=row, column=0, padx=15, pady=(2, 0), sticky="ew")
            return e

        _lbl("Nom *",    2);  self.entry_nom     = _entry(3,  "Ex: TRANS-EXPRESS")
        _lbl("Contact",  4);  self.entry_contact = _entry(5,  "Téléphone ou email")
        _lbl("Adresse",  6);  self.entry_adresse = _entry(7,  "Adresse complète")

        ctk.CTkFrame(panel_left, height=1, fg_color="#D5D8DC").grid(
            row=8, column=0, sticky="ew", padx=10, pady=12)

        # Boutons CRUD
        self.lbl_mode = ctk.CTkLabel(panel_left, text="➕ Nouveau transporteur",
                                     font=ctk.CTkFont(size=11, weight="bold"),
                                     text_color="#3498DB")
        self.lbl_mode.grid(row=9, column=0, padx=15, pady=(0, 6))

        btn_frame = ctk.CTkFrame(panel_left, fg_color="transparent")
        btn_frame.grid(row=10, column=0, padx=15, pady=4, sticky="ew")
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        self.btn_enregistrer = ctk.CTkButton(
            btn_frame, text="💾 Enregistrer",
            fg_color="#27AE60", hover_color="#1E8449",
            command=self.enregistrer_transporteur,
            font=ctk.CTkFont(size=12))
        self.btn_enregistrer.grid(row=0, column=0, padx=3, pady=3, sticky="ew")

        self.btn_annuler_form = ctk.CTkButton(
            btn_frame, text="✖ Annuler",
            fg_color="#636E72", hover_color="#2D3436",
            command=self.reinitialiser_formulaire,
            font=ctk.CTkFont(size=12))
        self.btn_annuler_form.grid(row=0, column=1, padx=3, pady=3, sticky="ew")

        self.btn_supprimer = ctk.CTkButton(
            panel_left, text="🗑️ Supprimer le transporteur",
            fg_color="#E74C3C", hover_color="#C0392B",
            command=self.supprimer_transporteur,
            state="disabled",
            font=ctk.CTkFont(size=11))
        self.btn_supprimer.grid(row=11, column=0, padx=15, pady=(6, 4), sticky="ew")

        # Info sélection
        self.lbl_selection = ctk.CTkLabel(
            panel_left, text="Aucune sélection",
            font=ctk.CTkFont(size=10), text_color="#95A5A6")
        self.lbl_selection.grid(row=12, column=0, padx=15, pady=(4, 0))

        # Astuce
        ctk.CTkLabel(panel_left,
                     text="💡 Double-clic sur un transporteur\npour voir son profil et historique.",
                     font=ctk.CTkFont(size=10),
                     text_color="#95A5A6",
                     justify="left").grid(row=20, column=0, padx=15, pady=(20, 10), sticky="sw")

        # ═════════════ PANNEAU DROIT — Liste + recherche ══════════════════
        panel_right = ctk.CTkFrame(self, fg_color="#FFFFFF",
                                   border_width=1, border_color="#D5D8DC")
        panel_right.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        panel_right.grid_rowconfigure(2, weight=1)
        panel_right.grid_columnconfigure(0, weight=1)

        # Header droit
        hdr_right = ctk.CTkFrame(panel_right, fg_color="#2C3E50", corner_radius=0)
        hdr_right.grid(row=0, column=0, sticky="ew")
        hdr_right.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr_right,
                     text="📋 Liste des transporteurs",
                     font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                     text_color="white").grid(row=0, column=0, padx=15, pady=10, sticky="w")

        self.lbl_count = ctk.CTkLabel(hdr_right, text="",
                                      font=ctk.CTkFont(size=11),
                                      text_color="#BDC3C7")
        self.lbl_count.grid(row=0, column=2, padx=15)

        # Barre recherche
        search_bar = ctk.CTkFrame(panel_right, fg_color="#F8F9FA",
                                  corner_radius=0, border_width=0)
        search_bar.grid(row=1, column=0, sticky="ew", padx=10, pady=8)
        search_bar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(search_bar, text="🔍",
                     font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=(5, 4))
        self.entry_search = ctk.CTkEntry(
            search_bar, placeholder_text="Rechercher par nom, contact ou adresse…",
            height=32)
        self.entry_search.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        self.entry_search.bind('<KeyRelease>', lambda e: self.charger_transporteurs())

        # Treeview
        tree_frame = ctk.CTkFrame(panel_right, fg_color="transparent")
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        cols = ("ID", "Nom", "Contact", "Adresse", "Nb Commandes")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
        self._configure_alternating(self.tree)

        style = ttk.Style()
        style.configure("Treeview",
                        rowheight=26, font=('Segoe UI', 9),
                        background="#FFFFFF", fieldbackground="#FFFFFF",
                        foreground="#2C3E50", borderwidth=0)
        style.configure("Treeview.Heading",
                        background="#ECF0F1", foreground="#2C3E50",
                        font=('Segoe UI', 9, 'bold'))
        style.map("Treeview", background=[('selected', '#D6EAF8')])

        widths = {"ID": 0, "Nom": 200, "Contact": 160, "Adresse": 260, "Nb Commandes": 110}
        anchors = {"ID": "w", "Nom": "w", "Contact": "w", "Adresse": "w", "Nb Commandes": "center"}
        for col in cols:
            self.tree.heading(col, text=col,
                              command=lambda c=col: self._sort_by(c))
            self.tree.column(col, width=widths[col],
                             stretch=(col != "ID"),
                             anchor=anchors[col])
        # Masquer colonne ID
        self.tree.column("ID", width=0, stretch=False, minwidth=0)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        # Bindings
        self.tree.bind('<<TreeviewSelect>>', self._on_select)
        self.tree.bind('<Double-Button-1>',  self._on_double_click)

        # Footer droit
        footer_right = ctk.CTkFrame(panel_right, fg_color="#F8F9FA",
                                    corner_radius=0)
        footer_right.grid(row=3, column=0, sticky="ew")
        ctk.CTkLabel(footer_right,
                     text="💡 Double-cliquez sur un transporteur pour voir son profil complet et ses commandes.",
                     font=ctk.CTkFont(size=10),
                     text_color="#95A5A6").pack(side="left", padx=12, pady=6)

    # ── Chargement liste ─────────────────────────────────────────────────────

    def charger_transporteurs(self, filtre=None):
        if filtre is None:
            filtre = self.entry_search.get().strip() if hasattr(self, 'entry_search') else ""

        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            query = """
                SELECT
                    t.idtransporteur,
                    t.nom,
                    COALESCE(t.contact, '—') AS contact,
                    COALESCE(t.adresse, '—') AS adresse,
                    COUNT(c.idcom) AS nb_commandes
                FROM tb_transporteur t
                LEFT JOIN tb_commande c
                    ON c.idtransportuer = t.idtransporteur AND c.deleted = 0
                WHERE t.deleted = 0
            """
            params = []
            if filtre:
                query += """
                    AND (
                        LOWER(t.nom)     LIKE LOWER(%s) OR
                        LOWER(COALESCE(t.contact, '')) LIKE LOWER(%s) OR
                        LOWER(COALESCE(t.adresse, '')) LIKE LOWER(%s)
                    )
                """
                like = f"%{filtre}%"
                params = [like, like, like]

            query += " GROUP BY t.idtransporteur, t.nom, t.contact, t.adresse ORDER BY t.nom"
            cursor.execute(query, params)
            rows = cursor.fetchall()

            self.tree.delete(*self.tree.get_children())
            for idx, row in enumerate(rows):
                tag = "row_even" if idx % 2 == 0 else "row_odd"
                self.tree.insert("", "end",
                    values=(row[0], row[1], row[2], row[3], row[4]),
                    tags=(tag,))

            n = len(rows)
            self.lbl_count.configure(
                text=f"{n} transporteur{'s' if n > 1 else ''}")

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur chargement: {str(e)}")
        finally:
            if 'cursor' in locals():
                cursor.close()
            conn.close()

    # ── Interactions UI ──────────────────────────────────────────────────────

    def _on_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0])['values']
        if not values:
            return

        self.transporteur_selectionne = {
            'id':      values[0],
            'nom':     values[1],
            'contact': values[2] if values[2] != '—' else '',
            'adresse': values[3] if values[3] != '—' else '',
        }
        # Remplir formulaire
        self.entry_nom.delete(0, "end");     self.entry_nom.insert(0, self.transporteur_selectionne['nom'])
        self.entry_contact.delete(0, "end"); self.entry_contact.insert(0, self.transporteur_selectionne['contact'])
        self.entry_adresse.delete(0, "end"); self.entry_adresse.insert(0, self.transporteur_selectionne['adresse'])

        self.lbl_mode.configure(text=f"✏️ Modifier : {self.transporteur_selectionne['nom'][:30]}",
                                text_color="#F39C12")
        self.btn_supprimer.configure(state="normal")
        self.lbl_selection.configure(
            text=f"ID #{self.transporteur_selectionne['id']} sélectionné",
            text_color="#3498DB")

    def _on_double_click(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        self._on_select()   # s'assurer que transporteur_selectionne est à jour
        if self.transporteur_selectionne:
            FenetreDetailTransporteur(
                self,
                self.transporteur_selectionne,
                self.connect_db,
                self.formater_nombre)

    def _sort_by(self, col):
        """Tri simple par colonne."""
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        items.sort()
        for idx, (_, k) in enumerate(items):
            self.tree.move(k, "", idx)
        self._refresh_alternating(self.tree)

    # ── CRUD ────────────────────────────────────────────────────────────────

    def enregistrer_transporteur(self):
        nom     = self.entry_nom.get().strip()
        contact = self.entry_contact.get().strip()
        adresse = self.entry_adresse.get().strip()

        if not nom:
            messagebox.showwarning("Validation", "Le nom du transporteur est obligatoire.")
            return

        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            if self.transporteur_selectionne:
                # UPDATE
                cursor.execute("""
                    UPDATE tb_transporteur
                    SET nom = %s, contact = %s, adresse = %s
                    WHERE idtransporteur = %s
                """, (nom, contact, adresse, self.transporteur_selectionne['id']))
                conn.commit()
                try:
                    self._logger.log(
                        action="Modification transporteur",
                        element=f"idtransporteur={self.transporteur_selectionne['id']}",
                        details=f"Transporteur modifié en '{nom}' (contact='{contact}', adresse='{adresse}')",
                        value=f"idtransporteur={self.transporteur_selectionne['id']}",
                    )
                except Exception:
                    pass
                messagebox.showinfo("Succès", f"Transporteur « {nom} » modifié avec succès.")
            else:
                # INSERT
                cursor.execute("""
                    INSERT INTO tb_transporteur (nom, contact, adresse, deleted)
                    VALUES (%s, %s, %s, 0)
                    RETURNING idtransporteur
                """, (nom, contact, adresse))
                new_id = cursor.fetchone()[0]
                conn.commit()
                try:
                    self._logger.log(
                        action="Création transporteur",
                        element=nom,
                        details=f"Transporteur créé (idtransporteur={new_id}, contact='{contact}', adresse='{adresse}')",
                        value=f"idtransporteur={new_id}",
                    )
                except Exception:
                    pass
                messagebox.showinfo("Succès",
                    f"Transporteur « {nom} » créé (ID #{new_id}).")

            self.reinitialiser_formulaire()
            self.charger_transporteurs()

        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement: {str(e)}")
        finally:
            if 'cursor' in locals():
                cursor.close()
            conn.close()

    def supprimer_transporteur(self):
        if not self.transporteur_selectionne:
            messagebox.showwarning("Attention", "Sélectionnez un transporteur.")
            return

        nom = self.transporteur_selectionne['nom']
        if not messagebox.askyesno("Confirmation",
                f"Supprimer le transporteur « {nom} » ?\n\n"
                "Les commandes associées ne seront pas supprimées."):
            return

        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tb_transporteur SET deleted = 1
                WHERE idtransporteur = %s
            """, (self.transporteur_selectionne['id'],))
            conn.commit()
            try:
                self._logger.log(
                    action="Suppression transporteur",
                    element=nom,
                    details="Suppression logique transporteur (deleted=1)",
                    value=f"idtransporteur={self.transporteur_selectionne['id']}",
                )
            except Exception:
                pass
            messagebox.showinfo("Succès", f"Transporteur « {nom} » supprimé.")
            self.reinitialiser_formulaire()
            self.charger_transporteurs()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur", f"Erreur suppression: {str(e)}")
        finally:
            if 'cursor' in locals():
                cursor.close()
            conn.close()

    def reinitialiser_formulaire(self):
        self.transporteur_selectionne = None
        for e in (self.entry_nom, self.entry_contact, self.entry_adresse):
            e.delete(0, "end")
        self.lbl_mode.configure(text="➕ Nouveau transporteur", text_color="#3498DB")
        self.btn_supprimer.configure(state="disabled")
        self.lbl_selection.configure(text="Aucune sélection", text_color="#95A5A6")
        self.tree.selection_remove(self.tree.selection())
