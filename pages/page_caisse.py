import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry
from tkinter import messagebox
import psycopg2
from datetime import datetime
import json
import os
from resource_utils import get_config_path, safe_file_read

# Imports ReportLab pour le PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# ── Thème iJeery ──────────────────────────────────────────────────────────────
try:
    from app_theme import Colors, Fonts, styled, Theme
    _T = True
except ImportError:
    _T = False


class _C:
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
    INFO_DARK      = "#16A085"
    INFO           = "#1ABC9C"
    TEXT_PRIMARY   = "#2C3E50"
    TEXT_SECONDARY = "#5D6D7E"
    TEXT_MUTED     = "#95A5A6"
    BORDER         = "#D5D8DC"
    DIVIDER        = "#E8EAED"


C = Colors if _T else _C

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _apply_tree_style():
    s = ttk.Style()
    try:
        s.theme_use("clam")
    except Exception:
        pass
    s.configure("Caisse.Treeview",
                 background=C.BG_CARD, foreground=C.TEXT_PRIMARY,
                 fieldbackground=C.BG_CARD, rowheight=22,
                 font=("Roboto" if _T else "Segoe UI", 9),
                 borderwidth=0)
    s.configure("Caisse.Treeview.Heading",
                 background=C.BG_HEADER, foreground="#FFFFFF",
                 font=("Roboto" if _T else "Segoe UI", 9, "bold"),
                 relief="flat", padding=(4, 3))
    s.map("Caisse.Treeview",
          background=[("selected", C.PRIMARY)],
          foreground=[("selected", "#FFFFFF")])


def _f(size=10, weight="normal"):
    return ctk.CTkFont(
        family="Roboto" if _T else "Segoe UI",
        size=size, weight=weight)


# ====================================================================
# PageCaisse
# ====================================================================

class PageCaisse(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master, fg_color=C.BG_PAGE)

        # ── État interne (identique à l'original) ─────────────────────────────
        self.modes_paiement_dict = {"Tous": None}
        self.donnees_pour_pdf    = []
        self.total_enc_periode   = 0
        self.total_dec_periode   = 0
        self.show_cumul          = False
        self.montants_docs       = {}
        self.montants_modes      = {}
        self.cadres_docs         = {}
        self.cadres_modes        = {}
        self.frames_docs         = {}
        self.frames_modes        = {}
        self.filtre_doc_actif    = None
        self.filtre_mode_actif   = None
        self.couleurs_docs       = {}
        self.couleurs_modes      = {}
        self._traitement_filtre_en_cours = False
        self._filtre_doc_en_attente      = None
        self._filtre_mode_en_attente     = None
        self.mode_ui_to_bd = {
            "Espèces": None, "Crédit": None, "Chèque": None,
            "Virement": None, "Autres": None, "Mvola": None,
            "Airtel Money": None, "Orange Money": None,
        }
        self.mode_bd_to_id   = {}
        self.donnees_tableau = []

        self.conn = self.connect_db()
        if self.conn:
            self.cursor = self.conn.cursor()
        else:
            messagebox.showerror("Erreur", "Connexion impossible.")
            return

        _apply_tree_style()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)   # treeview row

        self._build_header()
        self._build_badges()
        self._build_filters()
        self._build_treeview()
        self._build_table_actions()
        self._build_footer()

        self.charger_modes_paiement()
        self.appliquer_filtres()

    # ── helper font ──────────────────────────────────────────────────────────
    # ====================================================================
    # CONSTRUCTION UI — REFONTE DESIGN
    # ====================================================================

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=C.BG_HEADER, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            hdr, text="Gestion de la Caisse",
            font=_f(18, "bold"), text_color="#FFFFFF"
        ).pack(side="left", padx=16, pady=10)

    def _build_badges(self):
        """Deux rangées de badges cliquables (documents + modes de paiement)."""
        card = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=8)
        card.grid(row=1, column=0, sticky="ew", padx=12, pady=(6, 2))

        # ── Rangée Documents ──────────────────────────────────────────────────
        row_docs = ctk.CTkFrame(card, fg_color="transparent")
        row_docs.pack(fill="x", padx=8, pady=(8, 2))

        ctk.CTkLabel(
            row_docs, text="TYPES",
            font=_f(8, "bold"), text_color=C.TEXT_MUTED, width=42, anchor="w"
        ).pack(side="left", padx=(0, 4))

        docs_config = [
            ("Client",         "#7CB342"),
            ("Avoir",          "#F9A825"),
            ("Fournisseur",    "#1E88E5"),
            ("Personnel",      "#757575"),
            ("Dépenses",       "#E53935"),
            ("Encaissement",   "#43A047"),
            ("Paiement Crédit","#039BE5"),
        ]
        for doc, color in docs_config:
            self.creer_cadre_doc(row_docs, doc, color)

        # ── Rangée Modes ─────────────────────────────────────────────────────
        row_modes = ctk.CTkFrame(card, fg_color="transparent")
        row_modes.pack(fill="x", padx=8, pady=(2, 8))

        ctk.CTkLabel(
            row_modes, text="MODES",
            font=_f(8, "bold"), text_color=C.TEXT_MUTED, width=42, anchor="w"
        ).pack(side="left", padx=(0, 4))

        modes_config = [
            ("Espèces",      "#E65100"),
            ("Crédit",       "#1976D2"),
            ("Chèque",       "#0277BD"),
            ("Virement",     "#7B1FA2"),
            ("Autres",       "#C62828"),
            ("Mvola",        "#F57F17"),
            ("Airtel Money", "#827717"),
            ("Orange Money", "#00838F"),
        ]
        for mode, color in modes_config:
            self.creer_cadre_mode(row_modes, mode, color)

    def _build_filters(self):
        """Barre de filtres : dates, boutons, checkbox, recherche."""
        panel = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=8)
        panel.grid(row=2, column=0, sticky="ew", padx=12, pady=(2, 4))

        inner = ctk.CTkFrame(panel, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=7)

        # Dates
        ctk.CTkLabel(inner, text="Du :", font=_f(10),
                     text_color=C.TEXT_SECONDARY).pack(side="left", padx=(0, 2))
        self.entry_debut = DateEntry(inner, width=10, background=C.BG_HEADER,
                                     foreground="white", borderwidth=1,
                                     date_pattern="dd/mm/yyyy",
                                     font=("Segoe UI", 9))
        self.entry_debut.pack(side="left", padx=(0, 6))

        ctk.CTkLabel(inner, text="Au :", font=_f(10),
                     text_color=C.TEXT_SECONDARY).pack(side="left", padx=(0, 2))
        self.entry_fin = DateEntry(inner, width=10, background=C.BG_HEADER,
                                   foreground="white", borderwidth=1,
                                   date_pattern="dd/mm/yyyy",
                                   font=("Segoe UI", 9))
        self.entry_fin.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            inner, text="Valider",
            command=self.appliquer_filtres,
            fg_color=C.SUCCESS_DARK, hover_color=C.SUCCESS,
            text_color="#FFFFFF", height=28, width=80, font=_f(10, "bold")
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            inner, text="🖨️  PDF",
            command=self.generer_pdf,
            fg_color=C.INFO_DARK, hover_color=C.INFO,
            text_color="#FFFFFF", height=28, width=90, font=_f(10, "bold")
        ).pack(side="left", padx=(0, 12))

        # Checkbox Cumul
        self.check_cumul = ctk.CTkCheckBox(
            inner, text="Afficher Cumul",
            font=_f(10), text_color=C.TEXT_SECONDARY,
            checkbox_width=18, checkbox_height=18,
            command=self.toggle_cumul)
        self.check_cumul.pack(side="left", padx=(0, 16))

        # Séparateur
        ctk.CTkFrame(inner, width=1, height=22,
                     fg_color=C.BORDER).pack(side="left", padx=(0, 12))

        # Recherche
        ctk.CTkLabel(inner, text="🔍", font=_f(12),
                     text_color=C.TEXT_MUTED).pack(side="left", padx=(0, 4))
        self.entry_recherche = ctk.CTkEntry(
            inner,
            placeholder_text="Rechercher dans le tableau…",
            height=28, fg_color=C.BG_INPUT,
            border_color=C.BORDER, text_color=C.TEXT_PRIMARY, font=_f(10))
        self.entry_recherche.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.entry_recherche.bind("<KeyRelease>", self.filtrer_tableau_recherche)

    def _build_treeview(self):
        tbl = ctk.CTkFrame(self, fg_color=C.BG_CARD, corner_radius=8)
        tbl.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 4))
        tbl.grid_rowconfigure(0, weight=1)
        tbl.grid_columnconfigure(0, weight=1)

        self.colonnes = ("Date", "Référence", "Description",
                         "Encaissement", "Décaissement", "Cumul",
                         "Mode", "Utilisateur")

        self.tree = ttk.Treeview(tbl, columns=self.colonnes,
                                 show="headings", style="Caisse.Treeview")

        self.tree.tag_configure("odd",  background=C.BG_CARD)
        self.tree.tag_configure("even", background="#F0F4F8")

        col_cfg = {
            "Date":          (140, "center"),
            "Référence":     (110, "center"),
            "Description":   (250, "w"),
            "Encaissement":  (110, "e"),
            "Décaissement":  (110, "e"),
            "Cumul":         (0,   "e"),
            "Mode":          (110, "center"),
            "Utilisateur":   (100, "center"),
        }
        for col, (w, anc) in col_cfg.items():
            self.tree.heading(col, text=col)
            stretch = (col == "Description")
            self.tree.column(col, width=w, anchor=anc,
                             stretch=stretch,
                             minwidth=0 if w == 0 else 40)

        sy = ctk.CTkScrollbar(tbl, orientation="vertical",  command=self.tree.yview)
        sx = ctk.CTkScrollbar(tbl, orientation="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)

        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=(6, 0))
        sy.grid(row=0, column=1, sticky="ns",  pady=(6, 0))
        sx.grid(row=1, column=0, sticky="ew",  padx=(6, 0))

    def _build_table_actions(self):
        panel = ctk.CTkFrame(self, fg_color="transparent")
        panel.grid(row=4, column=0, sticky="ew", padx=12, pady=(2, 8))

        actions = ctk.CTkFrame(panel, fg_color="transparent")
        actions.pack(side="right")

        self.btn_encaissement = ctk.CTkButton(
            actions, text="＋  Encaissement",
            command=self.open_page_encaissement,
            fg_color=C.SUCCESS_DARK, hover_color=C.SUCCESS,
            text_color="#FFFFFF", height=34, width=160, font=_f(10, "bold"))
        self.btn_encaissement.pack(side="left", padx=(0, 8))

        self.btn_decaissement = ctk.CTkButton(
            actions, text="－  Décaissement",
            command=self.open_page_decaissement,
            fg_color=C.DANGER, hover_color=C.DANGER_DARK,
            text_color="#FFFFFF", height=34, width=160, font=_f(10, "bold"))
        self.btn_decaissement.pack(side="left")

    def _build_footer(self):
        pass

    # ====================================================================
    # BADGES (cadres cliquables) — design épuré
    # ====================================================================

    def creer_cadre_doc(self, parent, nom, couleur):
        """Crée un badge cliquable pour un type de document."""
        frame = ctk.CTkFrame(parent, fg_color=couleur, corner_radius=6,
                             width=128, height=50)
        frame.pack(side="left", padx=2, pady=1)
        frame.pack_propagate(False)

        label_nom = ctk.CTkLabel(
            frame, text=nom.upper(),
            font=_f(10, "normal"), text_color="#FFFFFF")
        label_nom.pack(pady=(5, 0))

        label_montant = ctk.CTkLabel(
            frame, text="0",
            font=_f(11, "bold"), text_color="#FFFFFF")
        label_montant.pack()

        self.cadres_docs[nom]  = label_montant
        self.frames_docs[nom]  = (frame, couleur, label_nom, label_montant)
        self.couleurs_docs[nom] = couleur

        def on_click(event=None, doc_nom=nom):
            self._traiter_clic_doc(doc_nom)

        def on_enter(event=None):
            if self.filtre_doc_actif != nom:
                frame.configure(fg_color=self._assombrir_couleur(couleur, 0.8))

        def on_leave(event=None):
            if self.filtre_doc_actif == nom:
                frame.configure(fg_color="#1a1a1a",
                                border_width=2, border_color="#FFD700")
            else:
                frame.configure(fg_color=couleur, border_width=0)

        for w in (frame, label_nom, label_montant):
            w.bind("<Button-1>", on_click)
            w.bind("<Enter>",    on_enter)
            w.bind("<Leave>",    on_leave)

    def creer_cadre_mode(self, parent, nom, couleur):
        """Crée un badge cliquable pour un mode de paiement."""
        frame = ctk.CTkFrame(parent, fg_color=couleur, corner_radius=6,
                             width=118, height=50)
        frame.pack(side="left", padx=2, pady=1)
        frame.pack_propagate(False)

        label_nom = ctk.CTkLabel(
            frame, text=nom.upper(),
            font=_f(10, "normal"), text_color="#FFFFFF")
        label_nom.pack(pady=(5, 0))

        label_montant = ctk.CTkLabel(
            frame, text="0",
            font=_f(11, "bold"), text_color="#FFFFFF")
        label_montant.pack()

        self.cadres_modes[nom]  = label_montant
        self.frames_modes[nom]  = (frame, couleur, label_nom, label_montant)
        self.couleurs_modes[nom] = couleur

        def on_click(event=None, mode_nom=nom):
            self._traiter_clic_mode(mode_nom)

        def on_enter(event=None):
            if self.filtre_mode_actif != nom:
                frame.configure(fg_color=self._assombrir_couleur(couleur, 0.8))

        def on_leave(event=None):
            if self.filtre_mode_actif == nom:
                frame.configure(fg_color="#1a1a1a",
                                border_width=2, border_color="#FFD700")
            else:
                frame.configure(fg_color=couleur, border_width=0)

        for w in (frame, label_nom, label_montant):
            w.bind("<Button-1>", on_click)
            w.bind("<Enter>",    on_enter)
            w.bind("<Leave>",    on_leave)

    # ====================================================================
    # LOGIQUE MÉTIER — inchangée
    # ====================================================================

    def filtrer_par_doc(self, doc):
        if self.filtre_doc_actif == doc:
            self.filtre_doc_actif = None
        else:
            self.filtre_doc_actif = doc
        self._mettre_a_jour_etat_cadres()
        self.appliquer_filtres()

    def _traiter_clic_doc(self, doc):
        if self._traitement_filtre_en_cours:
            self._filtre_doc_en_attente = doc
            return
        self._traitement_filtre_en_cours = True
        self.after(0, self._executer_clic_doc, doc)

    def _executer_clic_doc(self, doc):
        try:
            self.filtrer_par_doc(doc)
        finally:
            self._traitement_filtre_en_cours = False
            if self._filtre_doc_en_attente is not None:
                en_attente = self._filtre_doc_en_attente
                self._filtre_doc_en_attente = None
                self._traiter_clic_doc(en_attente)
            elif self._filtre_mode_en_attente is not None:
                en_attente = self._filtre_mode_en_attente
                self._filtre_mode_en_attente = None
                self._traiter_clic_mode(en_attente)

    def _traiter_clic_mode(self, mode):
        if self._traitement_filtre_en_cours:
            self._filtre_mode_en_attente = mode
            return
        self._traitement_filtre_en_cours = True
        self.after(0, self._executer_clic_mode, mode)

    def _executer_clic_mode(self, mode):
        try:
            self.filtrer_par_mode(mode)
        finally:
            self._traitement_filtre_en_cours = False
            if self._filtre_mode_en_attente is not None:
                en_attente = self._filtre_mode_en_attente
                self._filtre_mode_en_attente = None
                self._traiter_clic_mode(en_attente)
            elif self._filtre_doc_en_attente is not None:
                en_attente = self._filtre_doc_en_attente
                self._filtre_doc_en_attente = None
                self._traiter_clic_doc(en_attente)

    def filtrer_par_mode(self, mode):
        if self.filtre_mode_actif == mode:
            self.filtre_mode_actif = None
        else:
            self.filtre_mode_actif = mode
        self._mettre_a_jour_etat_cadres()
        self.appliquer_filtres()

    def _assombrir_couleur(self, couleur_hex, facteur=0.7):
        couleur_hex = couleur_hex.lstrip('#')
        r, g, b = tuple(int(couleur_hex[i:i+2], 16) for i in (0, 2, 4))
        r, g, b = int(r * facteur), int(g * facteur), int(b * facteur)
        return f'#{r:02x}{g:02x}{b:02x}'

    def _mettre_a_jour_etat_cadres(self):
        for nom, (frame, couleur_orig, label_nom, label_montant) in self.frames_docs.items():
            if self.filtre_doc_actif == nom:
                frame.configure(fg_color="#1a1a1a",
                                border_width=2, border_color="#FFD700")
            else:
                frame.configure(fg_color=couleur_orig, border_width=0)
        for nom, (frame, couleur_orig, label_nom, label_montant) in self.frames_modes.items():
            if self.filtre_mode_actif == nom:
                frame.configure(fg_color="#1a1a1a",
                                border_width=2, border_color="#FFD700")
            else:
                frame.configure(fg_color=couleur_orig, border_width=0)
        self.update_idletasks()

    def filtrer_tableau_recherche(self, event=None):
        recherche = self.entry_recherche.get().strip().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)
        if not recherche:
            for i, row in enumerate(self.donnees_tableau):
                tag = 'even' if (i % 2) else 'odd'
                try:
                    self.tree.insert("", "end", values=row, tags=(tag,))
                except TypeError:
                    self.tree.insert("", "end", values=row)
            return
        lignes_filtrees = [
            row for row in self.donnees_tableau
            if any(recherche in str(cell).lower() for cell in row)
        ]
        for i, row in enumerate(lignes_filtrees):
            tag = 'even' if (i % 2) else 'odd'
            try:
                self.tree.insert("", "end", values=row, tags=(tag,))
            except TypeError:
                self.tree.insert("", "end", values=row)

    def toggle_cumul(self):
        self.show_cumul = self.check_cumul.get() == 1
        if self.show_cumul:
            self.tree.column("Cumul", anchor="e", width=110, stretch=True)
        else:
            self.tree.column("Cumul", anchor="e", width=0, stretch=False)
        self.appliquer_filtres()

    def connect_db(self):
        try:
            config_path = get_config_path('config.json')
            if not os.path.exists(config_path):
                config_path = 'config.json'
            if not os.path.exists(config_path):
                messagebox.showerror("Erreur", "Fichier config.json manquant.")
                return None
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                db_config = config['database']
            conn = psycopg2.connect(
                host=db_config['host'], user=db_config['user'],
                password=db_config['password'],
                database=db_config['database'], port=db_config['port'],
                client_encoding='UTF8')
            return conn
        except Exception as err:
            messagebox.showerror("Erreur de connexion", f"Détails : {err}")
            return None

    def format_montant(self, v):
        return f"{v:,.0f}".replace(",", " ").replace(".", ",").replace(" ", ".")

    def format_montant_court(self, v):
        return self.format_montant(v)

    def charger_modes_paiement(self):
        try:
            self.cursor.execute(
                "SELECT idmode, modedepaiement FROM tb_modepaiement ORDER BY modedepaiement")
            rows = self.cursor.fetchall()
            for r in rows:
                idmode, modedepaiement = r
                self.mode_bd_to_id[modedepaiement] = idmode
            alias_mapping = {
                "Espèces":      ["Espèces", "Espece"],
                "Crédit":       ["Crédit", "Credit"],
                "Chèque":       ["Chèque", "Cheque", "Chèque bancaire"],
                "Virement":     ["Virement", "Virement bancaire"],
                "Autres":       ["Autres"],
                "Mvola":        ["Mvola", "MVOLA"],
                "Airtel Money": ["Airtel Money", "Airtel money"],
                "Orange Money": ["Orange Money", "Orange money"],
            }
            for nom_ui, alias_list in alias_mapping.items():
                for alias in alias_list:
                    for nom_bd, idmode in self.mode_bd_to_id.items():
                        if nom_bd.lower().strip() == alias.lower().strip():
                            self.mode_ui_to_bd[nom_ui] = nom_bd
                            self.modes_paiement_dict[nom_ui] = idmode
                            break
                    else:
                        continue
                    break
        except Exception as e:
            print(f"Erreur lors du chargement des modes: {e}")

    def calculer_montants_categories(self, date_d, date_f):
        d_str, f_str = date_d.strftime('%Y-%m-%d'), date_f.strftime('%Y-%m-%d')
        self.montants_docs = {
            "Client": 0, "Avoir": 0, "Fournisseur": 0, "Personnel": 0,
            "Dépenses": 0, "Encaissement": 0, "Paiement Crédit": 0}
        self.montants_modes = {}
        try:
            for table, key in [
                ("tb_pmtfacture",  "Client"),
                ("tb_pmtavoir",    "Avoir"),
                ("tb_pmtcom",      "Fournisseur"),
                ("tb_pmtcredit",   "Paiement Crédit"),
                ("tb_decaissement","Dépenses"),
                ("tb_encaissement","Encaissement"),
            ]:
                ref_col = "refavoir" if table == "tb_pmtavoir" else "refpmt"
                self.cursor.execute(f"""
                    SELECT SUM(CASE WHEN idtypeoperation=1 THEN mtpaye ELSE -mtpaye END)
                    FROM {table}
                    WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                """, [d_str, f_str])
                result = self.cursor.fetchone()
                self.montants_docs[key] = float(result[0]) if result and result[0] else 0

            self.cursor.execute("""
                SELECT SUM(CASE WHEN idtypeoperation=1 THEN mtpaye ELSE -mtpaye END)
                FROM (
                    SELECT idtypeoperation, mtpaye FROM tb_avancepers WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                    UNION ALL
                    SELECT idtypeoperation, mtpaye FROM tb_avancespecpers WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                    UNION ALL
                    SELECT idtypeoperation, mtpaye FROM tb_pmtsalaire WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                ) as pers
            """, [d_str, f_str, d_str, f_str, d_str, f_str])
            result = self.cursor.fetchone()
            self.montants_docs["Personnel"] = float(result[0]) if result and result[0] else 0

            # Inclure aussi les transferts caisse<->banque : ils doivent impacter la card "Espèces".
            params = [d_str, f_str] * 10
            self.cursor.execute("""
                SELECT COALESCE(t2.modedepaiement, 'Inconnu'),
                       SUM(CASE WHEN t1.idtypeoperation=1 THEN t1.mtpaye ELSE -t1.mtpaye END)
                FROM (
                    SELECT idmode, mtpaye, idtypeoperation FROM tb_pmtfacture WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                    UNION ALL SELECT idmode, mtpaye, idtypeoperation FROM tb_pmtcom WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                    UNION ALL SELECT idmode, mtpaye, idtypeoperation FROM tb_encaissement WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                    UNION ALL SELECT idmode, mtpaye, idtypeoperation FROM tb_decaissement WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                    UNION ALL SELECT idmode, mtpaye, idtypeoperation FROM tb_avancepers WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                    UNION ALL SELECT idmode, mtpaye, idtypeoperation FROM tb_avancespecpers WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                    UNION ALL SELECT idmode, mtpaye, idtypeoperation FROM tb_pmtsalaire WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                    UNION ALL SELECT idmode, mtpaye, idtypeoperation FROM tb_pmtavoir WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                    UNION ALL SELECT idmode, mtpaye, idtypeoperation FROM tb_pmtcredit WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                    UNION ALL SELECT idmode, mtpaye, idtypeoperation FROM tb_transfertcaisse WHERE datepmt::date BETWEEN %s AND %s
                ) t1
                LEFT JOIN tb_modepaiement t2 ON t1.idmode = t2.idmode
                GROUP BY t2.modedepaiement
            """, params)
            for row in self.cursor.fetchall():
                mode, solde = row
                self.montants_modes[mode] = float(solde) if solde else 0

            self.mettre_a_jour_cadres()
        except Exception as e:
            print(f"Erreur calcul montants: {e}")

    def mettre_a_jour_cadres(self):
        for doc, label in self.cadres_docs.items():
            label.configure(text=self.format_montant_court(
                self.montants_docs.get(doc, 0)))
        for mode_ui, label in self.cadres_modes.items():
            mode_bd = self.mode_ui_to_bd.get(mode_ui)
            montant = self.montants_modes.get(mode_bd, 0) if mode_bd else 0
            label.configure(text=self.format_montant_court(montant))

    def appliquer_filtres(self, _=None):
        mode_nom_ui = self.filtre_mode_actif
        mode_id     = None
        if mode_nom_ui:
            mode_bd = self.mode_ui_to_bd.get(mode_nom_ui)
            if mode_bd:
                mode_id = self.mode_bd_to_id.get(mode_bd)
        type_doc = self.filtre_doc_actif if self.filtre_doc_actif else "Tous"
        date_d   = self.entry_debut.get_date()
        date_f   = self.entry_fin.get_date()
        self.calculer_montants_categories(date_d, date_f)
        self.charger_donnees(date_d, date_f, mode_id, type_doc)

    def charger_donnees(self, date_d, date_f, mode_id=None, type_doc="Tous"):
        if not self.conn: return
        d_str, f_str = date_d.strftime('%Y-%m-%d'), date_f.strftime('%Y-%m-%d')
        for item in self.tree.get_children(): self.tree.delete(item)
        all_ops  = []
        sql_mode = ""
        mode_params = []
        if mode_id is not None:
            sql_mode    = " AND t1.idmode = %s"
            mode_params = [mode_id]

        def exec_query(query, params):
            try:
                self.cursor.execute(query, params)
                all_ops.extend(self.cursor.fetchall())
            except psycopg2.Error as e:
                print(f"Erreur query: {e}")
                self.conn.rollback()

        if type_doc in ["Tous", "Client"]:
            exec_query(f"SELECT t1.datepmt, t1.refpmt, t1.observation, t1.mtpaye, t1.idtypeoperation, COALESCE(t2.modedepaiement,'Inconnu'), COALESCE(t3.username,'Système') FROM tb_pmtfacture t1 LEFT JOIN tb_modepaiement t2 ON t1.idmode=t2.idmode LEFT JOIN tb_users t3 ON t1.iduser=t3.iduser WHERE t1.datepmt::date BETWEEN %s AND %s AND t1.id_banque IS NULL{sql_mode}", [d_str, f_str]+mode_params)
        if type_doc in ["Tous", "Paiement Crédit"]:
            exec_query(f"SELECT t1.datepmt, t1.refpmt, t1.observation, t1.mtpaye, t1.idtypeoperation, COALESCE(t2.modedepaiement,'Inconnu'), COALESCE(t3.username,'Système') FROM tb_pmtcredit t1 LEFT JOIN tb_modepaiement t2 ON t1.idmode=t2.idmode LEFT JOIN tb_users t3 ON t1.iduser=t3.iduser WHERE t1.datepmt::date BETWEEN %s AND %s AND t1.id_banque IS NULL{sql_mode}", [d_str, f_str]+mode_params)
        if type_doc in ["Tous", "Avoir"]:
            exec_query(f"SELECT t1.datepmt, t1.refavoir, t1.observation, t1.mtpaye, t1.idtypeoperation, COALESCE(t2.modedepaiement,'Inconnu'), COALESCE(t3.username,'Système') FROM tb_pmtavoir t1 LEFT JOIN tb_modepaiement t2 ON t1.idmode=t2.idmode LEFT JOIN tb_users t3 ON t1.iduser=t3.iduser WHERE t1.datepmt::date BETWEEN %s AND %s AND t1.id_banque IS NULL{sql_mode}", [d_str, f_str]+mode_params)
        if type_doc in ["Tous", "Fournisseur"]:
            exec_query(f"SELECT t1.datepmt, t1.refpmt, t1.observation, t1.mtpaye, t1.idtypeoperation, COALESCE(t2.modedepaiement,'Inconnu'), COALESCE(t3.username,'Système') FROM tb_pmtcom t1 LEFT JOIN tb_modepaiement t2 ON t1.idmode=t2.idmode LEFT JOIN tb_users t3 ON t1.iduser=t3.iduser WHERE t1.datepmt::date BETWEEN %s AND %s AND t1.id_banque IS NULL{sql_mode}", [d_str, f_str]+mode_params)
        if type_doc in ["Tous", "Encaissement"]:
            exec_query(f"SELECT t1.datepmt, t1.refpmt, t1.observation, t1.mtpaye, t1.idtypeoperation, COALESCE(t2.modedepaiement,'Inconnu'), COALESCE(t3.username,'Système') FROM tb_encaissement t1 LEFT JOIN tb_modepaiement t2 ON t1.idmode=t2.idmode LEFT JOIN tb_users t3 ON t1.iduser=t3.iduser WHERE t1.datepmt::date BETWEEN %s AND %s AND t1.id_banque IS NULL{sql_mode}", [d_str, f_str]+mode_params)
        if type_doc in ["Tous", "Dépenses"]:
            exec_query(f"SELECT t1.datepmt, t1.refpmt, t1.observation, t1.mtpaye, t1.idtypeoperation, COALESCE(t2.modedepaiement,'Inconnu'), COALESCE(t3.username,'Système') FROM tb_decaissement t1 LEFT JOIN tb_modepaiement t2 ON t1.idmode=t2.idmode LEFT JOIN tb_users t3 ON t1.iduser=t3.iduser WHERE t1.datepmt::date BETWEEN %s AND %s AND t1.id_banque IS NULL{sql_mode}", [d_str, f_str]+mode_params)
        if type_doc in ["Tous", "Personnel"]:
            for tbl in ("tb_avancepers", "tb_avancespecpers", "tb_pmtsalaire"):
                exec_query(f"SELECT t1.datepmt, t1.refpmt, t1.observation, t1.mtpaye, t1.idtypeoperation, COALESCE(t2.modedepaiement,'Inconnu'), COALESCE(t3.username,'Système') FROM {tbl} t1 LEFT JOIN tb_modepaiement t2 ON t1.idmode=t2.idmode LEFT JOIN tb_users t3 ON t1.iduser=t3.iduser WHERE t1.datepmt::date BETWEEN %s AND %s AND t1.id_banque IS NULL{sql_mode}", [d_str, f_str]+mode_params)
        if (not mode_id or mode_id == 1) and type_doc == "Tous":
            exec_query("SELECT t1.datepmt, t1.refpmt, t1.observation, t1.mtpaye, t1.idtypeoperation, COALESCE(t2.modedepaiement,'Espèces'), COALESCE(t3.username,'admin') FROM tb_transfertcaisse t1 LEFT JOIN tb_modepaiement t2 ON t1.idmode=t2.idmode LEFT JOIN tb_users t3 ON t1.iduser=t3.iduser WHERE t1.datepmt::date BETWEEN %s AND %s", [d_str, f_str])

        def get_datetime(op):
            dt = op[0]
            return dt if isinstance(dt, datetime) else datetime.combine(dt, datetime.min.time())

        all_ops.sort(key=get_datetime, reverse=True)
        self.donnees_pour_pdf    = []
        self.donnees_tableau     = []
        self.total_enc_periode   = 0
        self.total_dec_periode   = 0

        all_ops_asc  = list(reversed(all_ops))
        cumuls_dict  = {}
        cumul_courant = 0
        for idx, r in enumerate(all_ops_asc):
            enc = float(r[3]) if r[4] == 1 else 0
            dec = float(r[3]) if r[4] == 2 else 0
            cumul_courant += enc - dec
            cumuls_dict[idx] = cumul_courant

        try:
            for i, r in enumerate(all_ops):
                dt, ref, obs, mt, typ, mod, usr = r
                enc = float(mt) if typ == 1 else 0
                dec = float(mt) if typ == 2 else 0
                self.total_enc_periode += enc
                self.total_dec_periode += dec
                cumul_idx   = len(all_ops) - 1 - i
                cumul_val   = cumuls_dict.get(cumul_idx, 0)
                date_str    = dt.strftime("%d/%m/%Y %H:%M:%S") if isinstance(dt, datetime) else dt.strftime("%d/%m/%Y 00:00:00")
                cumul_str   = self.format_montant(cumul_val) if self.show_cumul else ""
                vals = (date_str, str(ref), str(obs),
                        self.format_montant(enc) if enc else "",
                        self.format_montant(dec) if dec else "",
                        cumul_str, mod, usr)
                tag = 'even' if (i % 2) else 'odd'
                try:
                    self.tree.insert("", "end", values=vals, tags=(tag,))
                except TypeError:
                    self.tree.insert("", "end", values=vals)
                self.donnees_pour_pdf.append(list(vals))
                self.donnees_tableau.append(vals)

            self.update_solde_global()
        except Exception as e:
            print(f"Erreur lors du chargement des données: {e}")

    def update_solde_global(self):
        try:
            self.cursor.execute("""
                SELECT SUM(CASE WHEN idtypeoperation=1 THEN mtpaye ELSE -mtpaye END)
                FROM (
                    SELECT idtypeoperation, mtpaye FROM tb_pmtfacture WHERE id_banque IS NULL
                    UNION ALL SELECT idtypeoperation, mtpaye FROM tb_pmtcom WHERE id_banque IS NULL
                    UNION ALL SELECT idtypeoperation, mtpaye FROM tb_encaissement WHERE id_banque IS NULL
                    UNION ALL SELECT idtypeoperation, mtpaye FROM tb_decaissement WHERE id_banque IS NULL
                    UNION ALL SELECT idtypeoperation, mtpaye FROM tb_avancepers WHERE id_banque IS NULL
                    UNION ALL SELECT idtypeoperation, mtpaye FROM tb_avancespecpers WHERE id_banque IS NULL
                    UNION ALL SELECT idtypeoperation, mtpaye FROM tb_pmtsalaire WHERE id_banque IS NULL
                    UNION ALL SELECT idtypeoperation, mtpaye FROM tb_transfertcaisse
                    UNION ALL SELECT idtypeoperation, mtpaye FROM tb_pmtavoir WHERE id_banque IS NULL
                    UNION ALL SELECT idtypeoperation, mtpaye FROM tb_pmtcredit WHERE id_banque IS NULL
                ) as total
            """)
            res   = self.cursor.fetchone()
            solde = float(res[0]) if res and res[0] is not None else 0.0
        except Exception as e:
            print(f"Erreur calcul solde global: {e}")

    def generer_pdf(self):
        if not self.donnees_pour_pdf:
            messagebox.showwarning("Vide", "Aucune donnée à imprimer.")
            return
        infos_societe = {"nom": "", "adresse": "", "ville": "", "contact": ""}
        try:
            self.cursor.execute(
                "SELECT nomsociete, adressesociete, villesociete, contactsociete FROM tb_infosociete LIMIT 1")
            res = self.cursor.fetchone()
            if res:
                infos_societe = {
                    "nom": res[0], "adresse": res[1],
                    "ville": res[2], "contact": res[3]}
        except Exception as e:
            print(f"Erreur recup infos societe: {e}")

        nom_fichier = f"Etat_Caisse_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        try:
            doc = SimpleDocTemplate(nom_fichier, pagesize=landscape(A4),
                                    rightMargin=30, leftMargin=30,
                                    topMargin=30, bottomMargin=30)
            elements = []
            styles   = getSampleStyleSheet()
            style_sn = ParagraphStyle('SocieteNom', parent=styles['Normal'],
                                      fontSize=14, leading=16, fontName='Helvetica-Bold')
            style_sd = ParagraphStyle('SocieteDetails', parent=styles['Normal'],
                                      fontSize=10, leading=12)
            if infos_societe["nom"]:
                elements.append(Paragraph(infos_societe["nom"].upper(), style_sn))
                elements.append(Paragraph(infos_societe["adresse"],     style_sd))
                elements.append(Paragraph(infos_societe["ville"],       style_sd))
                elements.append(Paragraph(f"Contact : {infos_societe['contact']}", style_sd))
            elements.append(Spacer(1, 20))
            filtre_doc  = self.filtre_doc_actif  or "Tous"
            filtre_mode = self.filtre_mode_actif or "Tous"
            elements.append(Paragraph(
                f"<b>ETAT DE CAISSE - {filtre_mode} ({filtre_doc})</b>",
                styles['Title']))
            elements.append(Paragraph(
                f"Période du {self.entry_debut.get()} au {self.entry_fin.get()}",
                styles['Normal']))
            elements.append(Spacer(1, 15))
            data = [self.colonnes] + self.donnees_pour_pdf
            solde_periode = self.total_enc_periode - self.total_dec_periode
            data.append(["", "", "TOTAL CUMULÉ",
                         self.format_montant(self.total_enc_periode),
                         self.format_montant(self.total_dec_periode), "", "", ""])
            data.append(["", "", "SOLDE DE LA PÉRIODE", "",
                         self.format_montant(solde_periode), "", "", ""])
            t = Table(data, repeatRows=1,
                      colWidths=[100, 80, 200, 90, 90, 70, 70, 70])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR',  (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN',      (2, 0), (2, -1),  'LEFT'),
                ('FONTNAME',   (0, 0), (-1, 0),  'Helvetica-Bold'),
                ('FONTSIZE',   (0, 0), (-1, -1),  8),
                ('GRID',       (0, 0), (-1, -3),  0.5, colors.black),
                ('BACKGROUND', (0, -2), (-1, -1), colors.lightgrey),
                ('FONTNAME',   (0, -2), (-1, -1), 'Helvetica-Bold'),
                ('GRID',       (2, -2), (4, -1),  1, colors.black),
                ('ALIGN',      (3, -2), (4, -1),  'RIGHT'),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 30))
            elements.append(Paragraph(
                f"Edité le : {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                styles['Italic']))
            doc.build(elements)
            os.startfile(nom_fichier)
        except Exception as e:
            messagebox.showerror("Erreur PDF", f"Détails : {e}")

    def open_page_decaissement(self):
        try:
            from page_decaissement import PageDecaissement
        except ImportError:
            from pages.page_decaissement import PageDecaissement
        win = PageDecaissement(self.master, username="VotreUsername")
        self.master.wait_window(win)
        self.appliquer_filtres()

    def open_page_encaissement(self):
        try:
            from page_encaissement import PageEncaissement
        except ImportError:
            from pages.page_encaissement import PageEncaissement
        win = PageEncaissement(self.master, username="VotreUsername")
        self.master.wait_window(win)
        self.appliquer_filtres()


# ── Test standalone ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    app = ctk.CTk()
    app.title("iJeery — Gestion Caisse")
    app.geometry("1200x760")
    if _T:
        Theme.apply(app)
    app.grid_rowconfigure(0, weight=1)
    app.grid_columnconfigure(0, weight=1)
    PageCaisse(app).grid(row=0, column=0, sticky="nsew")
    app.mainloop()
