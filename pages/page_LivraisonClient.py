import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import psycopg2.pool
import json
import os
from datetime import datetime
from reportlab.lib.pagesizes import A5
from reportlab.pdfgen import canvas
from tkcalendar import DateEntry
from typing import Optional, Dict, Any, List
import threading

from app_theme import Colors, Fonts, Layout, styled


class PageLivraisonClient(ctk.CTkFrame):
    # Pool de connexions partagé (évite de recréer une connexion à chaque opération)
    _connection_pool: Optional[psycopg2.pool.SimpleConnectionPool] = None

    def __init__(self, master, id_user_connecte: Optional[int] = None) -> None:
        super().__init__(master, fg_color=Colors.BG_PAGE, corner_radius=0)
        if id_user_connecte is None:
            messagebox.showerror("Erreur", "Aucun utilisateur connecté. Veuillez vous reconnecter.")
            self.id_user_connecte = None
        else:
            self.id_user_connecte = id_user_connecte
            print(f"✅ Utilisateur connecté - ID: {self.id_user_connecte}")

        self.user_id = self.id_user_connecte

        self.selected_ref_vente = None
        self.selected_id_client = None
        self.selected_id_mag = None

        # Cache du numéro BL pour éviter une requête DB à chaque réinitialisation
        self._bl_ref_cache: Optional[str] = None

        self.grid_columnconfigure(0, weight=1)
        self._init_pool()
        self.setup_ui()

    # ─────────────────────────────────────────────
    # Pool de connexions
    # ─────────────────────────────────────────────

    def _init_pool(self):
        """Initialise le pool de connexions une seule fois."""
        if PageLivraisonClient._connection_pool is not None:
            return
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(current_dir)
            config_path = os.path.join(root_dir, 'config.json')
            with open(config_path, 'r') as f:
                config = json.load(f)
                db_config = config['database']
            PageLivraisonClient._connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1, maxconn=5, **db_config
            )
        except Exception as e:
            messagebox.showerror("Erreur DB", f"Impossible d'initialiser le pool de connexions.\n{e}")

    def _get_conn(self):
        """Récupère une connexion depuis le pool."""
        if PageLivraisonClient._connection_pool:
            return PageLivraisonClient._connection_pool.getconn()
        return None

    def _release_conn(self, conn):
        """Restitue la connexion au pool."""
        if conn and PageLivraisonClient._connection_pool:
            PageLivraisonClient._connection_pool.putconn(conn)

    # Conservé pour compatibilité ascendante avec les autres méthodes non modifiées
    def connect_db(self):
        return self._get_conn()

    # ─────────────────────────────────────────────
    # Couleurs alternées
    # ─────────────────────────────────────────────

    def _configure_table_alternating_colors(self, tree):
        tree.tag_configure("row_even", background=Colors.BG_CARD)
        tree.tag_configure("row_odd", background=Colors.BG_ROW_ALT)

    def _refresh_table_alternating_colors(self, tree):
        for idx, item in enumerate(tree.get_children()):
            tags = tuple(t for t in tree.item(item, "tags") if t not in ("row_even", "row_odd"))
            alt_tag = "row_even" if idx % 2 == 0 else "row_odd"
            tree.item(item, tags=tags + (alt_tag,))

    # ─────────────────────────────────────────────
    # Génération BL
    # ─────────────────────────────────────────────

    def generate_bl_ref(self) -> str:
        """Génère la référence BL. Utilise un cache pour éviter des requêtes répétées."""
        if self._bl_ref_cache:
            return self._bl_ref_cache
        year = datetime.now().year
        conn = self._get_conn()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT COUNT(*) FROM tb_livraisoncli WHERE EXTRACT(YEAR FROM dateregistre) = %s",
                    (year,)
                )
                count = cur.fetchone()[0] + 1
                self._bl_ref_cache = f"{year}-BL-{count:05d}"
                return self._bl_ref_cache
            except Exception:
                pass
            finally:
                self._release_conn(conn)
        return f"{year}-BL-00001"

    def _invalidate_bl_cache(self):
        """Invalide le cache BL après un enregistrement."""
        self._bl_ref_cache = None

    # ─────────────────────────────────────────────
    # Ouverture directe depuis PageLivraisonEnAttente
    # ─────────────────────────────────────────────

    def ouvrir_depuis_attente(self, refvente: str, nomcli: str,
                               idclient: int, idmag: int):
        """
        Appelé par PageLivraisonEnAttente lors d'un double-clic.
        Charge directement la facture sans passer par la fenêtre de sélection.
        """
        self.charger_details_facture(refvente, nomcli, idclient, idmag)

    # ─────────────────────────────────────────────
    # Interface
    # ─────────────────────────────────────────────

    def setup_ui(self):
        self.configure(fg_color=Colors.BG_PAGE)
        self._configure_tree_style()

        header = styled.frame(self, color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 8))

        title_box = styled.frame(header, color="transparent")
        title_box.pack(side="left", fill="x", expand=True)
        styled.label_heading(title_box, text="Livraison Client", size=18).pack(anchor="w")
        styled.label_muted(
            title_box,
            text=f"Date: {datetime.now().strftime('%d/%m/%Y')}",
            size=11,
        ).pack(anchor="w", pady=(2, 0))

        self.bl_var = ctk.StringVar(value=self.generate_bl_ref())
        bl_box = styled.frame(header, color="transparent")
        bl_box.pack(side="left", padx=(12, 8))
        styled.label_muted(bl_box, text="BL N°", size=11).pack(anchor="w")
        self.ent_bl = styled.entry(
            bl_box,
            height=Layout.INPUT_H,
            textvariable=self.bl_var,
            state="readonly",
            width=150,
        )
        self.ent_bl.pack()

        styled.button_premium(
            header,
            text="Suivi Livraison",
            command=self.ouvrir_suivi_livraison,
            height=Layout.BTN_H,
            width=145,
        ).pack(side="right", padx=(8, 0))

        styled.button_primary(
            header,
            text="Charger Facture",
            command=self.ouvrir_selection_facture,
            height=Layout.BTN_H,
            width=145,
        ).pack(side="right", padx=(8, 0))

        info_frame = styled.card(self)
        info_frame.pack(fill="x", padx=16, pady=(0, 10))
        self.lbl_client = styled.label(info_frame, text="Client: ---", size=13, weight="bold")
        self.lbl_client.pack(side="left", padx=16, pady=12)
        self.lbl_facture = styled.badge(info_frame, text="N° Facture: ---", variant="neutral")
        self.lbl_facture.pack(side="right", padx=16, pady=12)

        self.tree_frame = styled.card(self)
        self.tree_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        cols = ("code", "nom", "unite", "qt_vente", "qt_livre", "id_art", "id_unite", "id_mag")
        self.tree = ttk.Treeview(self.tree_frame, columns=cols, show="headings", height=15)
        self.tree.configure(style="LivraisonClient.Treeview")
        self._configure_table_alternating_colors(self.tree)

        col_config = [
            ("code", "Code Article", 120),
            ("nom", "Désignation", 250),
            ("unite", "Unité", 100),
            ("qt_vente", "Qté Vendue", 100),
            ("qt_livre", "Qté à Livrer", 100),
        ]
        for col, text, width in col_config:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="center")
        for col in cols[5:]:
            self.tree.column(col, width=0, stretch=False)

        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True, side="left")

        self.tree.bind("<Double-1>", self.modifier_quantite)

        styled.label_muted(
            self,
            text="Double-cliquez sur une ligne pour modifier la quantité à livrer",
            size=11,
        ).pack(anchor="w", padx=20, pady=(0, 8))

        btn_frame = styled.frame(self, color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(0, 16))

        styled.button_danger(
            btn_frame,
            text="Annuler / Vider",
            command=self.reinitialiser, width=150
        ).pack(side="left", padx=5)
        styled.button_success(
            btn_frame,
            text="Enregistrer & Imprimer PDF",
            command=self.enregistrer_livraison, width=200
        ).pack(side="right", padx=5)

    def _configure_tree_style(self):
        style = ttk.Style()
        family = Fonts._family if getattr(Fonts, "_loaded", False) else "Segoe UI"
        style.configure(
            "LivraisonClient.Treeview",
            background=Colors.BG_CARD,
            foreground=Colors.TEXT_PRIMARY,
            fieldbackground=Colors.BG_CARD,
            rowheight=Layout.ROW_H,
            borderwidth=0,
            font=(family, 9),
        )
        style.configure(
            "LivraisonClient.Treeview.Heading",
            background=Colors.CLOUDS,
            foreground=Colors.TEXT_PRIMARY,
            font=(family, 9, "bold"),
        )
        style.map(
            "LivraisonClient.Treeview",
            background=[("selected", Colors.PRIMARY)],
            foreground=[("selected", Colors.TEXT_ON_DARK)],
        )

    # ─────────────────────────────────────────────
    # Sélection de la facture — optimisé
    # ─────────────────────────────────────────────

    def ouvrir_selection_facture(self):
        top = ctk.CTkToplevel(self)
        top.title("Sélectionner Facture")
        top.geometry("700x580")
        top.configure(fg_color=Colors.BG_PAGE)
        top.attributes('-topmost', True)

        header = styled.frame(top, color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 8))
        styled.label_heading(header, text="Sélectionner une facture", size=17).pack(anchor="w")
        styled.label_muted(header, text="Choisissez une facture avec un reste à livrer", size=11).pack(anchor="w")

        filter_frame = styled.card(top)
        filter_frame.pack(fill="x", padx=16, pady=(0, 10))

        styled.label_muted(filter_frame, text="Date", size=11).pack(side="left", padx=(14, 8), pady=12)

        cal_container = styled.frame(filter_frame, color="transparent")
        cal_container.pack(side="left", padx=(0, 8), pady=12)

        ent_date = DateEntry(
            cal_container, width=12,
            background='darkblue', foreground='white', borderwidth=2,
            date_pattern='yyyy-mm-dd', locale='fr_FR'
        )
        ent_date.pack(padx=2, pady=2)

        styled.button_primary(filter_frame, text="Filtrer", command=lambda: charger_async(ent_date.get_date()), width=90).pack(
            side="left", padx=(0, 8), pady=12
        )
        styled.button_secondary(filter_frame, text="Tout afficher",
                                command=lambda: charger_async(None), width=115).pack(side="left", pady=12)

        lbl_status = styled.label_muted(top, text="", size=11)
        lbl_status.pack(anchor="w", padx=18, pady=(0, 4))

        table_box = styled.card(top)
        table_box.pack(fill="both", expand=True, padx=16, pady=(0, 10))
        tree_f = ttk.Treeview(table_box, columns=("ref", "client", "date", "idcli", "idmag"), show="headings")
        tree_f.configure(style="LivraisonClient.Treeview")
        self._configure_table_alternating_colors(tree_f)

        for c, t, w in [("ref", "N° Facture", 150), ("client", "Nom Client", 250), ("date", "Date", 150)]:
            tree_f.heading(c, text=t)
            tree_f.column(c, width=w)
        tree_f.column("idcli", width=0, stretch=False)
        tree_f.column("idmag", width=0, stretch=False)
        tree_scroll = ttk.Scrollbar(table_box, orient="vertical", command=tree_f.yview)
        tree_f.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.pack(side="right", fill="y", pady=10)
        tree_f.pack(fill="both", expand=True, side="left", padx=10, pady=10)

        # ── Requête optimisée : remplace les 2 sous-requêtes corrélées par des JOIN agrégés ──
        QUERY_BASE = """
            SELECT
                v.refvente,
                c.nomcli,
                v.dateregistre,
                v.idclient,
                v.idmag
            FROM tb_vente v
            JOIN tb_client c ON v.idclient = c.idclient
            -- Somme des ventes (une seule jointure agrégée, non corrélée)
            JOIN (
                SELECT idvente, SUM(qtvente) AS total_vente
                FROM tb_ventedetail
                GROUP BY idvente
            ) vd_sum ON vd_sum.idvente = v.id
            -- Somme des livraisons (LEFT JOIN pour inclure les non encore livrées)
            LEFT JOIN (
                SELECT refvente, SUM(qtlivrecli) AS total_livre
                FROM tb_livraisoncli
                GROUP BY refvente
            ) lv_sum ON lv_sum.refvente = v.refvente
            -- Condition : reste encore quelque chose à livrer
            WHERE vd_sum.total_vente > COALESCE(lv_sum.total_livre, 0)
        """

        # Drapeau partagé : mis à True dès que top est fermé.
        # Le thread vérifie ce drapeau avant toute interaction avec l'UI.
        _top_detruit = [False]

        def _safe_ui(fn):
            """Exécute fn() dans le thread principal via after() SEULEMENT si top existe encore."""
            if not _top_detruit[0]:
                try:
                    top.after(0, fn)
                except Exception:
                    pass

        def charger(date_val=None):
            # Mettre à jour le statut depuis le thread via after()
            _safe_ui(lambda: lbl_status.configure(text="⏳ Chargement en cours…"))

            conn = self._get_conn()
            if not conn:
                _safe_ui(lambda: lbl_status.configure(text="❌ Erreur de connexion."))
                return
            try:
                cur = conn.cursor()
                if date_val:
                    cur.execute(
                        QUERY_BASE + " AND CAST(v.dateregistre AS DATE) = %s ORDER BY v.dateregistre DESC",
                        (date_val,)
                    )
                else:
                    cur.execute(QUERY_BASE + " ORDER BY v.dateregistre DESC LIMIT 50")

                rows = cur.fetchall()

                # Toutes les modifications UI passent par after() dans le thread principal
                def _peupler():
                    if _top_detruit[0]:
                        return
                    for i in tree_f.get_children():
                        tree_f.delete(i)
                    for r in rows:
                        date_formatted = r[2].strftime('%d/%m/%Y') if hasattr(r[2], 'strftime') else str(r[2])
                        tree_f.insert("", "end", values=(r[0], r[1], date_formatted, r[3], r[4]))
                    self._refresh_table_alternating_colors(tree_f)
                    lbl_status.configure(text=f"✅ {len(rows)} facture(s) trouvée(s).")

                _safe_ui(_peupler)

            except Exception as e:
                _safe_ui(lambda: lbl_status.configure(text="❌ Erreur lors du chargement."))
                print(f"Erreur chargement factures: {e}")
            finally:
                self._release_conn(conn)

        def charger_async(date_val=None):
            """Lance le chargement dans un thread séparé pour ne pas bloquer l'UI."""
            threading.Thread(target=charger, args=(date_val,), daemon=True).start()

        def valider():
            sel = tree_f.selection()
            if sel:
                v = tree_f.item(sel)['values']
                _top_detruit[0] = True   # signaler au thread avant destroy
                self.charger_details_facture(v[0], v[1], v[3], v[4])
                top.destroy()
            else:
                messagebox.showwarning("Sélection", "Veuillez sélectionner une facture.")

        tree_f.bind("<Double-1>", lambda e: valider())

        styled.button_success(top, text="Choisir cette facture", command=valider,
                              width=210, height=Layout.BTN_H).pack(pady=(0, 16))

        def _on_close_top():
            _top_detruit[0] = True   # signaler au thread avant destroy
            top.destroy()

        top.protocol("WM_DELETE_WINDOW", _on_close_top)

        # Chargement initial en arrière-plan
        charger_async()

    # ─────────────────────────────────────────────
    # Détails de la facture
    # ─────────────────────────────────────────────

    def charger_details_facture(self, ref, nom, idcli, idmag):
        self.selected_ref_vente = ref
        self.selected_id_client = idcli
        self.selected_id_mag = idmag

        self.lbl_client.configure(text=f"Client: {nom}")
        self.lbl_facture.configure(text=f"N° Facture: {ref}")

        for i in self.tree.get_children():
            self.tree.delete(i)

        conn = self._get_conn()
        if not conn:
            return
        try:
            cur = conn.cursor()

            # Récupère idvente et les détails en une seule requête
            query = """
                SELECT
                    u.codearticle,
                    a.designation,
                    u.designationunite,
                    vd.qtvente,
                    (vd.qtvente - COALESCE(lv_sum.total_livre, 0)) AS reste_a_livrer,
                    vd.idarticle,
                    vd.idunite,
                    vd.idmag
                FROM tb_vente v
                JOIN tb_ventedetail vd ON vd.idvente = v.id
                JOIN tb_article a ON vd.idarticle = a.idarticle
                JOIN tb_unite u ON vd.idunite = u.idunite
                LEFT JOIN (
                    SELECT idarticle, idunite, SUM(qtlivrecli) AS total_livre
                    FROM tb_livraisoncli
                    WHERE refvente = %s
                    GROUP BY idarticle, idunite
                ) lv_sum ON lv_sum.idarticle = vd.idarticle AND lv_sum.idunite = vd.idunite
                WHERE v.refvente = %s
                ORDER BY a.designation
            """
            cur.execute(query, (ref, ref))
            rows = cur.fetchall()

            if not rows:
                messagebox.showwarning("Aucune donnée", "Aucun article trouvé pour cette facture.")
            else:
                for r in rows:
                    reste = float(r[4])
                    if reste > 0:
                        self.tree.insert("", "end", values=(
                            r[0], r[1], r[2], r[3], reste, r[5], r[6], r[7]
                        ))
                self._refresh_table_alternating_colors(self.tree)
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des détails: {e}")
        finally:
            self._release_conn(conn)

    # ─────────────────────────────────────────────
    # Modification de quantité
    # ─────────────────────────────────────────────

    def modifier_quantite(self, event):
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        v = self.tree.item(item)['values']

        dialog = ctk.CTkToplevel(self)
        dialog.title("Modifier la quantité")
        dialog.geometry("400x200")
        dialog.configure(fg_color=Colors.BG_PAGE)
        dialog.attributes('-topmost', True)

        styled.label_heading(dialog, text="Modifier la quantité", size=16).pack(anchor="w", padx=16, pady=(16, 4))
        styled.label(dialog, text=f"Article: {v[1]}", size=12, weight="bold").pack(anchor="w", padx=16)
        styled.label_muted(dialog, text=f"Quantité vendue: {v[3]}", size=11).pack(anchor="w", padx=16, pady=(2, 8))

        frame = styled.card(dialog)
        frame.pack(fill="x", padx=16, pady=(0, 10))

        styled.label_muted(frame, text="Quantité à livrer", size=11).pack(side="left", padx=(14, 8), pady=12)
        entry = styled.entry(frame, width=100, height=Layout.INPUT_H)
        entry.insert(0, str(v[4]))
        entry.pack(side="left", padx=(0, 14), pady=12)
        entry.focus()

        def valider():
            try:
                val_new = float(entry.get())
                if val_new < 0:
                    messagebox.showwarning("Erreur", "La quantité ne peut pas être négative.")
                elif val_new > float(v[3]):
                    messagebox.showwarning(
                        "Erreur",
                        f"La quantité livrée ({val_new}) dépasse la quantité vendue ({v[3]})."
                    )
                else:
                    lst = list(v)
                    lst[4] = val_new
                    self.tree.item(item, values=lst)
                    dialog.destroy()
            except ValueError:
                messagebox.showerror("Erreur", "Veuillez entrer un nombre valide.")

        btn_frame = styled.frame(dialog, color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(0, 16))
        styled.button_success(btn_frame, text="Valider", command=valider, width=110).pack(side="right", padx=(8, 0))
        styled.button_secondary(btn_frame, text="Annuler", command=dialog.destroy, width=110).pack(side="right")
        entry.bind("<Return>", lambda e: valider())

    # ─────────────────────────────────────────────
    # Réinitialisation
    # ─────────────────────────────────────────────

    def reinitialiser(self):
        self.selected_ref_vente = None
        self.selected_id_client = None
        self.selected_id_mag = None
        self.lbl_client.configure(text="Client: ---")
        self.lbl_facture.configure(text="N° Facture: ---")
        for i in self.tree.get_children():
            self.tree.delete(i)
        self._invalidate_bl_cache()
        self.bl_var.set(self.generate_bl_ref())

    # ─────────────────────────────────────────────
    # Enregistrement
    # ─────────────────────────────────────────────

    def enregistrer_livraison(self):
        if self.user_id is None:
            messagebox.showerror("Erreur", "Aucun utilisateur connecté. Impossible d'enregistrer.")
            return
        if not self.selected_ref_vente:
            messagebox.showwarning("Attention", "Veuillez d'abord charger une facture.")
            return

        lignes = self.tree.get_children()
        if not lignes:
            messagebox.showwarning("Attention", "Aucun article à livrer.")
            return

        has_delivery = any(float(self.tree.item(i)['values'][4]) > 0 for i in lignes)
        if not has_delivery:
            messagebox.showwarning(
                "Attention",
                "Aucun article n'a de quantité à livrer (toutes les lignes sont à 0)."
            )
            return

        refliv = self.bl_var.get()
        conn = self._get_conn()
        if conn:
            try:
                cur = conn.cursor()
                now = datetime.now()
                data = [
                    (
                        refliv,
                        self.selected_ref_vente,
                        self.tree.item(i)['values'][7],   # idmag
                        self.tree.item(i)['values'][5],   # idarticle
                        self.tree.item(i)['values'][6],   # idunite
                        self.tree.item(i)['values'][3],   # qtvente
                        float(self.tree.item(i)['values'][4]),  # qtlivrecli
                        now,
                        self.user_id,
                        self.selected_id_client
                    )
                    for i in lignes
                ]
                # Insertion groupée (un seul aller-retour réseau)
                cur.executemany("""
                    INSERT INTO tb_livraisoncli
                    (reflivcli, refvente, idmag, idarticle, idunite, qtvente, qtlivrecli, dateregistre, iduser, idclient)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, data)
                conn.commit()

                self._invalidate_bl_cache()
                self.imprimer_pdf(refliv)
                messagebox.showinfo("Succès", f"Bon de livraison {refliv} enregistré avec succès !")
                self.reinitialiser()
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self._release_conn(conn)

    # ─────────────────────────────────────────────
    # Génération PDF
    # ─────────────────────────────────────────────

    def imprimer_pdf(self, refliv):
        try:
            path = f"Livraison_{refliv.replace('-', '_')}.pdf"
            c = canvas.Canvas(path, pagesize=A5)
            w, h = A5

            info_soc = {}
            nom_user = ""
            conn = self._get_conn()
            if conn:
                try:
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT nomsociete, adressesociete, contactsociete, villesociete, "
                        "nifsociete, statsociete, cifsociete FROM tb_infosociete LIMIT 1"
                    )
                    res = cur.fetchone()
                    if res:
                        info_soc = {
                            'nom': res[0], 'adr': res[1], 'tel': res[2],
                            'ville': res[3], 'nif': res[4], 'stat': res[5], 'cif': res[6]
                        }
                    cur.execute(
                        "SELECT nomuser, prenomuser FROM tb_users WHERE iduser = %s",
                        (self.user_id,)
                    )
                    u = cur.fetchone()
                    if u:
                        nom_user = f"{u[0]} {u[1]}"
                finally:
                    self._release_conn(conn)

            c.setFont("Helvetica-Bold", 12)
            c.drawString(30, h - 30, info_soc.get('nom', "MA SOCIÉTÉ").upper())

            c.setFont("Helvetica", 8)
            y_head = h - 42
            c.drawString(30, y_head, f"{info_soc.get('adr', '')} - {info_soc.get('ville', '')}")
            c.drawString(30, y_head - 10, f"Contact: {info_soc.get('tel', '')}")
            c.drawString(
                30, y_head - 20,
                f"NIF: {info_soc.get('nif', '')} | STAT: {info_soc.get('stat', '')} | CIF: {info_soc.get('cif', '')}"
            )

            c.setFont("Helvetica-Bold", 14)
            c.drawCentredString(w / 2, h - 85, "BON DE LIVRAISON")

            c.setFont("Helvetica", 9)
            c.drawString(30, h - 110, f"BL N°: {refliv}")
            c.drawString(30, h - 122, f"Facture: {self.selected_ref_vente}")
            c.drawString(w - 180, h - 110, f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            c.drawString(
                w - 180, h - 122,
                f"Client: {self.lbl_client.cget('text').replace('Client: ', '')}"
            )

            y_pre_table = h - 145
            c.setFont("Helvetica-Oblique", 9)
            c.drawString(30, y_pre_table, f"Etabli par: {nom_user}")

            y = y_pre_table - 15
            c.setLineWidth(1)
            c.line(30, y, w - 30, y)

            c.setFont("Helvetica-Bold", 9)
            c.drawString(35, y - 15, "Désignation")
            c.drawString(w - 150, y - 15, "Unité")
            c.drawString(w - 80, y - 15, "Qté Livrée")

            c.setLineWidth(0.5)
            c.line(30, y - 18, w - 30, y - 18)

            y -= 35
            c.setFont("Helvetica", 8)

            for i in self.tree.get_children():
                v = self.tree.item(i)['values']
                qt_livre = float(v[4])
                if qt_livre > 0:
                    c.drawString(35, y, str(v[1])[:35])
                    c.drawString(w - 150, y, str(v[2]))
                    c.drawString(w - 75, y, str(qt_livre))
                    y -= 15
                    if y < 60:
                        c.showPage()
                        y = h - 50

            c.setFont("Helvetica-Oblique", 8)
            c.drawString(30, 40, "Signature du livreur: _______________")
            c.drawString(w - 180, 40, "Signature du client: _______________")

            c.save()

            import sys
            if os.name == 'nt':
                os.startfile(path)
            else:
                import subprocess
                cmd = 'open' if sys.platform == 'darwin' else 'xdg-open'
                subprocess.call([cmd, path])

        except Exception as e:
            messagebox.showerror("Erreur PDF", f"Erreur lors de la génération du PDF: {e}")
            import traceback
            traceback.print_exc()


    def ouvrir_suivi_livraison(self):
        """Ouvre la fenêtre PageLivraisonEnAttente dans une fenêtre modale."""
        try:
            from .page_livraisonEnAttente import PageLivraisonEnAttente
        except ImportError:
            try:
                from page_livraisonEnAttente import PageLivraisonEnAttente
            except ImportError:
                messagebox.showerror(
                    "Erreur",
                    "Le fichier 'page_livraisonEnAttente.py' est introuvable."
                )
                return

        main_window = self.winfo_toplevel()
        main_window.update_idletasks()
        mw = max(main_window.winfo_width(), 1)
        mh = max(main_window.winfo_height(), 1)
        mx = main_window.winfo_x()
        my = main_window.winfo_y()

        win_w = max(1050, int(mw * 0.85))
        win_h = max(620,  int(mh * 0.85))
        pos_x = mx + (mw - win_w) // 2
        pos_y = my + (mh - win_h) // 2

        win = ctk.CTkToplevel(self)
        win.title("🚚 Livraisons en Attente")
        win.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
        win.resizable(True, True)

        # PageLivraisonEnAttente utilise pack en interne → pack ici aussi
        page = PageLivraisonEnAttente(win, iduser=self.id_user_connecte)
        page.pack(fill="both", expand=True)

        # Forcer l'affichage au premier plan sur Windows
        def _forcer_affichage():
            win.attributes("-topmost", True)
            win.lift()
            win.focus_force()
            win.after(200, lambda: win.attributes("-topmost", False))

        win.after(100, _forcer_affichage)


if __name__ == "__main__":
    root = ctk.CTk()
    root.title("Gestion des Livraisons Client")
    root.geometry("900x600")

    USER_ID = 1

    app = PageLivraisonClient(root, id_user_connecte=USER_ID)
    app.pack(fill="both", expand=True)
    root.mainloop()
