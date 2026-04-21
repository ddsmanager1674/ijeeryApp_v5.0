from __future__ import annotations

import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import json
import os
from datetime import datetime
from typing import Optional, Tuple, List, Any, Dict

from app_theme import Colors, Fonts, styled, Theme
from EtatsPDF_Mouvements import EtatPDFMouvements

class PageStockLivraison(ctk.CTkFrame):
    def __init__(self, master, db_conn=None, session_data=None, iduser=None):
        super().__init__(master, fg_color=Colors.BG_PAGE)
        
        # Gestion de l'ID utilisateur
        if iduser is not None:
            self.iduser = iduser
        elif session_data and 'user_id' in session_data:
            self.iduser = session_data['user_id']
        else:
            self.iduser = 1
        
        self.magasins = []
        self._apply_treeview_style()
        self.setup_ui()
        self._ensure_attente_table()
        self.charger_magasins()
        self.charger_donnees()
    
    def connect_db(self):
        """Connexion qui remonte d'un niveau pour trouver config.json à la racine"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(current_dir)
            config_path = os.path.join(root_dir, 'config.json')
 
            with open(config_path, 'r') as f:
                config = json.load(f)
                db_config = config['database']
            return psycopg2.connect(**db_config)
        except Exception as e:
            messagebox.showerror("Erreur de chemin", f"Impossible de trouver config.json à la racine.\nErreur: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────
    # Schéma: table backlog BL (attente)
    # ─────────────────────────────────────────────────────────────────────
    def _ensure_attente_table(self) -> None:
        """
        Crée la table tb_livraisoncli_attente si elle n'existe pas.
        Règle métier: vente = sortie stock immédiate, BL = document logistique.
        """
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
            # Migration douce si ancienne colonne qt_demande existe
            cur.execute("""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema='public'
                          AND table_name='tb_livraisoncli_attente'
                          AND column_name='qt_demande'
                    ) AND NOT EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema='public'
                          AND table_name='tb_livraisoncli_attente'
                          AND column_name='qt_a_livrer'
                    ) THEN
                        ALTER TABLE public.tb_livraisoncli_attente ADD COLUMN qt_a_livrer double precision NOT NULL DEFAULT 0;
                        UPDATE public.tb_livraisoncli_attente SET qt_a_livrer = COALESCE(qt_demande,0) WHERE qt_a_livrer = 0;
                    END IF;
                END $$;
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_livcli_attente_statut
                    ON public.tb_livraisoncli_attente (statut);
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_livcli_attente_refvente
                    ON public.tb_livraisoncli_attente (refvente);
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
    
    def formater_nombre(self, nombre):
        """Formate les nombres pour l'affichage (ex: 1.250,00)"""
        try:
            return f"{float(nombre):,.2f}".replace(',', ' ').replace('.', ',').replace(' ', '.')
        except:
            return "0,00"

    def _parse_float(self, s: Any) -> float:
        try:
            if s is None:
                return 0.0
            if isinstance(s, (int, float)):
                return float(s)
            txt = str(s).strip()
            if not txt:
                return 0.0
            # "1.250,00" -> 1250.00
            return float(txt.replace(".", "").replace(",", "."))
        except Exception:
            return 0.0

    # ─────────────────────────────────────────────────────────────────────
    # UI / Treeview Style
    # ─────────────────────────────────────────────────────────────────────
    def _apply_treeview_style(self) -> None:
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
        style.map(
            "iJeery.Treeview.Heading",
            background=[("active", Colors.MIDNIGHT_LIGHT)],
        )

    def _configure_alternating(self, tree: ttk.Treeview) -> None:
        tree.tag_configure("row_even", background=Colors.BG_CARD)
        tree.tag_configure("row_odd", background=Colors.BG_ROW_ALT)

    def _refresh_alternating(self, tree: ttk.Treeview) -> None:
        for i, iid in enumerate(tree.get_children()):
            tags = tuple(t for t in tree.item(iid, "tags") if t not in ("row_even", "row_odd"))
            alt = "row_even" if i % 2 == 0 else "row_odd"
            tree.item(iid, tags=tags + (alt,))
    
    def setup_ui(self):
        # Header
        header = styled.card(self)
        header.pack(fill="x", padx=18, pady=(16, 10))
        inner = styled.frame(header)
        inner.pack(fill="x", padx=18, pady=14)

        styled.label_title(inner, text="🚚  Stock Livraison (BL en attente)").pack(anchor="w")
        styled.label_muted(
            inner,
            text="Backlog BL indépendant du stock (vente = sortie immédiate).",
        ).pack(anchor="w", pady=(2, 0))

        # Filtres + Actions
        filtres = styled.card(self)
        filtres.pack(fill="x", padx=18, pady=(0, 10))
        row = styled.frame(filtres)
        row.pack(fill="x", padx=18, pady=14)

        styled.label_muted(row, text="🔍 Recherche", width=110, anchor="w").pack(side="left")
        self.entry_recherche = styled.entry(row, placeholder="Code article, désignation, facture...")
        self.entry_recherche.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_recherche.bind("<KeyRelease>", self.filtrer_donnees)

        styled.label_muted(row, text="🏪 Magasin", width=90, anchor="w").pack(side="left", padx=(0, 6))
        self.combo_magasin = styled.combobox(row, values=["Tous"], command=lambda _v=None: self.filtrer_donnees())
        self.combo_magasin.set("Tous")
        self.combo_magasin.pack(side="left", padx=(0, 10))

        styled.label_muted(row, text="📌 Statut", width=70, anchor="w").pack(side="left", padx=(0, 6))
        self.combo_statut = styled.combobox(
            row,
            values=["EN_ATTENTE", "CLOTUREE", "ANNULEE", "Tous"],
            command=lambda _v=None: self.filtrer_donnees(),
            width=160,
        )
        self.combo_statut.set("EN_ATTENTE")
        self.combo_statut.pack(side="left", padx=(0, 10))

        styled.button_secondary(row, text="Actualiser", icon="🔄", command=self.charger_donnees, width=140).pack(side="right", padx=(8, 0))
        styled.button_premium(row, text="Export Excel", icon="📊", command=self.exporter_excel, width=140).pack(side="right")

        # Actions BL
        actions = styled.frame(self)
        actions.pack(fill="x", padx=18, pady=(0, 10))
        styled.button_success(actions, text="BL (facture)", icon="🧾", command=self.generer_bl_facture, width=160).pack(side="right", padx=(8, 0))
        styled.button_success(actions, text="BL (article)", icon="📦", command=self.generer_bl_article, width=160).pack(side="right", padx=(8, 0))
        styled.button_danger(actions, text="Annuler attente", icon="✕", command=self.annuler_attente, width=160).pack(side="left")

        # Tableau
        frame_tableau = styled.card(self)
        frame_tableau.pack(fill="both", expand=True, padx=18, pady=(0, 10))
        table_inner = styled.frame(frame_tableau)
        table_inner.pack(fill="both", expand=True, padx=12, pady=12)

        cols = (
            "refvente", "client", "code", "designation", "unite", "magasin",
            "qt_restant", "stock_theo",
            # hidden ids
            "_idvente", "_idclient", "_idmag", "_idarticle", "_idunite",
            "_qt_a_livrer", "_qt_bl",
        )
        self.tree = ttk.Treeview(table_inner, columns=cols, show="headings", height=18, style="iJeery.Treeview")
        self._configure_alternating(self.tree)

        headers = [
            ("refvente", "Facture", 130, "center"),
            ("client", "Client", 180, "w"),
            ("code", "Code", 95, "center"),
            ("designation", "Désignation", 280, "w"),
            ("unite", "Unité", 90, "center"),
            ("magasin", "Magasin", 150, "w"),
            ("qt_restant", "Reste BL", 110, "e"),
            ("stock_theo", "Stock Théo", 110, "e"),
        ]
        for key, text, width, anchor in headers:
            self.tree.heading(key, text=text)
            self.tree.column(key, width=width, anchor=anchor, stretch=False)

        for key in ("_idvente", "_idclient", "_idmag", "_idarticle", "_idunite", "_qt_a_livrer", "_qt_bl"):
            self.tree.heading(key, text="")
            self.tree.column(key, width=0, stretch=False)

        self.tree.bind("<Double-1>", lambda _e: self.generer_bl_article())

        scroll_y = ttk.Scrollbar(table_inner, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        # Footer
        footer = styled.card(self)
        footer.pack(fill="x", padx=18, pady=(0, 16))
        frow = styled.frame(footer)
        frow.pack(fill="x", padx=18, pady=12)
        self.label_total = styled.label(frow, text="Total lignes: 0", size=12, weight="bold")
        self.label_total.pack(side="left")
        self.label_maj = styled.label_muted(frow, text="Dernière MAJ: --", size=11)
        self.label_maj.pack(side="right")
    
    def charger_magasins(self):
        """Charge la liste des magasins pour le combobox"""
        conn = self.connect_db()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT idmag, designationmag 
                FROM tb_magasin 
                WHERE deleted = 0 
                ORDER BY designationmag
            """)
            self.magasins = cursor.fetchall()
            
            # Mise à jour du combobox
            valeurs_combo = ["Tous"] + [mag[1] for mag in self.magasins]
            self.combo_magasin.configure(values=valeurs_combo)
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur chargement magasins: {e}")
        finally:
            cursor.close()
            conn.close()
    
    def calculer_stock_theorique(self, idarticle, idunite, idmag):
        """
        Calcule le stock théorique d'un article pour un magasin
        (Réutilise la logique de page_stock.py)
        """
        conn = self.connect_db()
        if not conn:
            return 0
        
        try:
            cursor = conn.cursor()
            
            # Récupérer les unités de l'article
            cursor.execute("""
                SELECT idunite, COALESCE(qtunite, 1) as qtunite
                FROM tb_unite 
                WHERE idarticle = %s
                ORDER BY idunite ASC
            """, (idarticle,))
            unites_article = cursor.fetchall()
            
            if not unites_article:
                return 0
            
            idunite_base = unites_article[0][0]
            facteurs_conversion = {idunite_base: 1.0}
            
            facteur_cumul = 1.0
            for i, (id_unite, qt_unite) in enumerate(unites_article):
                if i == 0:
                    facteurs_conversion[id_unite] = 1.0
                else:
                    facteur_cumul *= qt_unite
                    facteurs_conversion[id_unite] = facteur_cumul
            
            stock_en_unite_base = 0
            
            # Calcul pour chaque unité
            for idunite_source, qtunite_source in unites_article:
                # Livraisons fournisseurs
                cursor.execute("""
                    SELECT COALESCE(SUM(qtlivrefrs), 0) 
                    FROM tb_livraisonfrs 
                    WHERE idarticle = %s AND idunite = %s AND idmag = %s
                """, (idarticle, idunite_source, idmag))
                total_livraison = cursor.fetchone()[0] or 0
                
                # Ventes
                cursor.execute("""
                    SELECT COALESCE(SUM(qtvente), 0) 
                    FROM tb_ventedetail 
                    WHERE idarticle = %s AND idunite = %s AND idmag = %s
                """, (idarticle, idunite_source, idmag))
                total_vente = cursor.fetchone()[0] or 0
                
                # Sorties
                cursor.execute("""
                    SELECT COALESCE(SUM(qtsortie), 0) 
                    FROM tb_sortiedetail 
                    WHERE idarticle = %s AND idunite = %s AND idmag = %s
                """, (idarticle, idunite_source, idmag))
                total_sortie = cursor.fetchone()[0] or 0
                
                # Transferts sortants
                cursor.execute("""
                    SELECT COALESCE(SUM(td.qttransfertsortie), 0)
                    FROM tb_transfertdetail td
                    INNER JOIN tb_transfert t ON td.idtransfert = t.idtransfert
                    WHERE td.idarticle = %s AND td.idunite = %s AND t.idmagsortie = %s
                """, (idarticle, idunite_source, idmag))
                total_transfert_sortie = cursor.fetchone()[0] or 0
                
                # Transferts entrants
                cursor.execute("""
                    SELECT COALESCE(SUM(td.qttransfertentree), 0)
                    FROM tb_transfertdetail td
                    INNER JOIN tb_transfert t ON td.idtransfert = t.idtransfert
                    WHERE td.idarticle = %s AND td.idunite = %s AND t.idmagentree = %s
                """, (idarticle, idunite_source, idmag))
                total_transfert_entree = cursor.fetchone()[0] or 0
                
                # Avoir
                cursor.execute("""
                    SELECT COALESCE(SUM(qtavoir), 0) 
                    FROM tb_avoirdetail 
                    WHERE idarticle = %s AND idunite = %s AND idmag = %s
                """, (idarticle, idunite_source, idmag))
                total_avoir = cursor.fetchone()[0] or 0
                
                stock_unite_source = (total_livraison + total_avoir + total_transfert_entree - 
                                     total_vente - total_sortie - total_transfert_sortie)
                
                facteur_vers_base = facteurs_conversion.get(idunite_source, 1.0)
                stock_en_unite_base += stock_unite_source * facteur_vers_base
            
            # Conversion vers l'unité cible
            facteur_cible = facteurs_conversion.get(idunite, 1.0)
            if facteur_cible == 0:
                return 0
            
            return stock_en_unite_base / facteur_cible
            
        except Exception as e:
            print(f"Erreur calcul stock théorique: {e}")
            return 0
        finally:
            cursor.close()
            conn.close()
    
    def charger_donnees(self):
        """Charge les données du tableau"""
        # Vider le tableau
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._refresh_alternating(self.tree)
        
        conn = self.connect_db()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            
            # Backlog BL (attente) = tb_livraisoncli_attente
            query = """
                SELECT
                    a.refvente,
                    COALESCE(c.nomcli, '') AS nomcli,
                    u.codearticle,
                    art.designation,
                    u.designationunite,
                    m.designationmag,
                    a.idclient,
                    a.idmag,
                    a.idarticle,
                    a.idunite,
                    COALESCE(a.qt_a_livrer, 0) AS qt_a_livrer,
                    COALESCE(a.qt_bl, 0) AS qt_bl,
                    GREATEST(COALESCE(a.qt_a_livrer, 0) - COALESCE(a.qt_bl, 0), 0) AS qt_restant
                FROM tb_livraisoncli_attente a
                INNER JOIN tb_article art ON a.idarticle = art.idarticle
                INNER JOIN tb_unite u ON (a.idarticle = u.idarticle AND a.idunite = u.idunite)
                INNER JOIN tb_magasin m ON a.idmag = m.idmag
                LEFT JOIN tb_client c ON a.idclient = c.idclient
                WHERE art.deleted = 0
                  AND COALESCE(a.qt_a_livrer,0) > COALESCE(a.qt_bl,0)
                  AND a.statut = 'EN_ATTENTE'
                ORDER BY a.refvente, u.codearticle, m.designationmag
            """
            
            cursor.execute(query)
            resultats = cursor.fetchall()
            
            for row in resultats:
                refvente = row[0]
                nom_client = row[1]
                code_art = row[2]
                designation = row[3]
                unite = row[4]
                magasin = row[5]
                idclient = row[6]
                idmag = row[7]
                idarticle = row[8]
                idunite = row[9]
                qt_a_livrer = float(row[10] or 0)
                qt_bl = float(row[11] or 0)
                reste_a_livrer = float(row[12] or 0)
                
                # Calculer le stock théorique
                stock_theorique = self.calculer_stock_theorique(idarticle, idunite, idmag)
                
                # Insertion dans le tableau
                values = (
                    refvente,
                    nom_client,
                    code_art,
                    designation,
                    unite,
                    magasin,
                    self.formater_nombre(reste_a_livrer),
                    self.formater_nombre(stock_theorique),
                    idclient,
                    idmag,
                    idarticle,
                    idunite,
                    qt_a_livrer,
                    qt_bl,
                )
                
                self.tree.insert("", "end", values=values, tags=())
            self._refresh_alternating(self.tree)
            
            # Mise à jour des labels
            self.label_total.configure(text=f"Total lignes: {len(resultats)}")
            self.label_maj.configure(text=f"Dernière MAJ: {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur chargement données: {e}")
            print(f"Détails erreur: {e}")
        finally:
            cursor.close()
            conn.close()
    
    def filtrer_donnees(self, event=None):
        """Filtre les données selon la recherche et le magasin sélectionné"""
        terme_recherche = self.entry_recherche.get().lower()
        magasin_filtre = self.combo_magasin.get()
        statut_filtre = self.combo_statut.get() if hasattr(self, "combo_statut") else "EN_ATTENTE"
        
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            
            # Filtrage par recherche
            refvente = str(values[0]).lower()
            client = str(values[1]).lower()
            code = str(values[2]).lower()
            designation = str(values[3]).lower()
            correspond_recherche = (
                (terme_recherche in refvente)
                or (terme_recherche in client)
                or (terme_recherche in code)
                or (terme_recherche in designation)
            ) if terme_recherche else True
            
            # Filtrage par magasin
            magasin = str(values[5])
            correspond_magasin = (magasin_filtre == "Tous" or magasin == magasin_filtre)

            correspond_statut = True
            if statut_filtre and statut_filtre != "Tous":
                # Ici la table affichée est déjà filtrée EN_ATTENTE, mais on garde le filtre pour extension.
                correspond_statut = (statut_filtre == "EN_ATTENTE")
            
            # Afficher/masquer l'item
            if correspond_recherche and correspond_magasin and correspond_statut:
                self.tree.reattach(item, '', 'end')
            else:
                self.tree.detach(item)

    # ─────────────────────────────────────────────────────────────────────
    # Actions (BL / Annulation)
    # ─────────────────────────────────────────────────────────────────────
    def _selected_row(self) -> Optional[Tuple[Any, ...]]:
        sel = self.tree.selection()
        if not sel:
            return None
        return tuple(self.tree.item(sel[0]).get("values") or [])

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

    def annuler_attente(self) -> None:
        row = self._selected_row()
        if not row:
            messagebox.showwarning("Sélection", "Sélectionnez une ligne.")
            return

        refvente = row[0]
        idmag = int(row[10])
        idarticle = int(row[11])
        idunite = int(row[12])

        if not messagebox.askyesno("Annuler", f"Annuler l'attente BL pour {refvente} / {row[2]} ?"):
            return

        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE tb_livraisoncli_attente
                   SET statut='ANNULEE', dateupdate=NOW(), iduser=%s
                 WHERE refvente=%s AND idmag=%s AND idarticle=%s AND idunite=%s
                """,
                (self.iduser, refvente, idmag, idarticle, idunite),
            )
            conn.commit()
            self.charger_donnees()
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            messagebox.showerror("Erreur", f"Annulation échouée: {e}")
        finally:
            try:
                cur.close()
            except Exception:
                pass
            conn.close()

    def generer_bl_article(self) -> None:
        row = self._selected_row()
        if not row:
            messagebox.showwarning("Sélection", "Sélectionnez une ligne.")
            return

        refvente = row[0]
        client = row[1]
        code = row[2]
        designation = row[3]
        unite = row[4]
        magasin = row[5]
        qt_restant = self._parse_float(row[6])

        idvente = int(row[8])
        idclient = int(row[9])
        idmag = int(row[10])
        idarticle = int(row[11])
        idunite = int(row[12])

        if qt_restant <= 0:
            messagebox.showwarning("Info", "Aucune quantité restante à livrer (BL).")
            return

        dlg = ctk.CTkToplevel(self)
        dlg.title("Générer BL (article)")
        dlg.geometry("520x260")
        dlg.attributes("-topmost", True)
        Theme.apply_toplevel(dlg)

        card = styled.card(dlg)
        card.pack(fill="both", expand=True, padx=16, pady=16)
        inner = styled.frame(card)
        inner.pack(fill="both", expand=True, padx=18, pady=18)

        styled.label_heading(inner, text="Bon de Livraison (article)").pack(anchor="w")
        styled.label_muted(inner, text=f"Facture: {refvente}   |   Client: {client}").pack(anchor="w", pady=(2, 10))
        styled.label(inner, text=f"{code} — {designation} ({unite})", size=12, weight="bold").pack(anchor="w")
        styled.label_muted(inner, text=f"Reste BL: {self.formater_nombre(qt_restant)}").pack(anchor="w", pady=(2, 10))

        row_in = styled.frame(inner)
        row_in.pack(fill="x", pady=(0, 12))
        styled.label_muted(row_in, text="Qté à livrer (BL)", width=140, anchor="w").pack(side="left")
        ent = styled.entry(row_in, placeholder=str(qt_restant))
        ent.insert(0, str(qt_restant))
        ent.pack(side="left", fill="x", expand=True)

        def _do():
            q = self._parse_float(ent.get())
            if q <= 0:
                messagebox.showwarning("Quantité", "Quantité invalide.")
                return
            if q > qt_restant + 1e-9:
                messagebox.showwarning("Quantité", "La quantité dépasse le reste BL.")
                return
            try:
                refliv = self._generate_bl_ref()
                self._save_bl(
                    refliv=refliv,
                    refvente=refvente,
                    idvente=idvente,
                    idclient=idclient,
                    idmag=idmag,
                    lignes=[{
                        "idarticle": idarticle,
                        "idunite": idunite,
                        "code": code,
                        "designation": designation,
                        "unite": unite,
                        "qte": q,
                    }],
                    magasin_label=magasin,
                )
                dlg.destroy()
                self.charger_donnees()
            except Exception as e:
                messagebox.showerror("Erreur", str(e))

        btns = styled.frame(inner)
        btns.pack(fill="x", pady=(8, 0))
        styled.button_secondary(btns, text="Fermer", icon="✕", command=dlg.destroy, width=120).pack(side="left")
        styled.button_success(btns, text="Enregistrer & PDF", icon="📄", command=_do, width=180).pack(side="right")

    def generer_bl_facture(self) -> None:
        row = self._selected_row()
        if not row:
            messagebox.showwarning("Sélection", "Sélectionnez une ligne (facture).")
            return
        refvente = row[0]

        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    a.idclient, a.idmag,
                    u.codearticle, art.designation, u.designationunite,
                    a.idarticle, a.idunite,
                    GREATEST(COALESCE(a.qt_a_livrer,0) - COALESCE(a.qt_bl,0), 0) AS qt_restant,
                    m.designationmag,
                    COALESCE(c.nomcli,'') AS nomcli
                FROM tb_livraisoncli_attente a
                INNER JOIN tb_article art ON a.idarticle = art.idarticle
                INNER JOIN tb_unite u ON (a.idarticle = u.idarticle AND a.idunite = u.idunite)
                INNER JOIN tb_magasin m ON a.idmag = m.idmag
                LEFT JOIN tb_client c ON a.idclient = c.idclient
                WHERE a.refvente=%s AND a.statut='EN_ATTENTE'
                  AND COALESCE(a.qt_a_livrer,0) > COALESCE(a.qt_bl,0)
                ORDER BY u.codearticle
                """,
                (refvente,),
            )
            rows = cur.fetchall()
            if not rows:
                messagebox.showwarning("Info", "Aucune attente BL restante pour cette facture.")
                return

            idclient, idmag = int(rows[0][0]), int(rows[0][1])
            magasin_label = rows[0][8]

            lignes = []
            for r in rows:
                q = float(r[7] or 0)
                if q <= 0:
                    continue
                lignes.append({
                    "idarticle": int(r[5]),
                    "idunite": int(r[6]),
                    "code": r[2],
                    "designation": r[3],
                    "unite": r[4],
                    "qte": q,
                })

            if not lignes:
                messagebox.showwarning("Info", "Aucune quantité à livrer (BL).")
                return

            if not messagebox.askyesno("Confirmation", f"Générer un BL pour toute la facture {refvente} ?"):
                return

            refliv = self._generate_bl_ref()
            self._save_bl(
                refliv=refliv,
                refvente=refvente,
                idclient=idclient,
                idmag=idmag,
                lignes=lignes,
                magasin_label=magasin_label,
            )
            self.charger_donnees()

        except Exception as e:
            messagebox.showerror("Erreur", f"Génération BL échouée: {e}")
        finally:
            try:
                cur.close()
            except Exception:
                pass
            conn.close()

    def _save_bl(
        self,
        refliv: str,
        refvente: str,
        idvente: int,
        idclient: int,
        idmag: int,
        lignes: List[Dict[str, Any]],
        magasin_label: str,
    ) -> None:
        conn = self.connect_db()
        if not conn:
            raise RuntimeError("Connexion DB impossible.")

        try:
            cur = conn.cursor()

            # Opérateur
            operateur = ""
            try:
                cur.execute("SELECT nomuser, prenomuser FROM tb_users WHERE iduser=%s", (self.iduser,))
                u = cur.fetchone()
                if u:
                    operateur = f"{u[0] or ''} {u[1] or ''}".strip()
            except Exception:
                operateur = ""

            # Insérer BL + MAJ attentes
            for l in lignes:
                q = float(l["qte"])
                if q <= 0:
                    continue

                # qtvente de référence (vendu) si dispo
                qtvente = None
                try:
                    cur.execute(
                        "SELECT COALESCE(SUM(qtvente),0) FROM tb_ventedetail WHERE idvente=%s AND idarticle=%s AND idunite=%s AND idmag=%s",
                        (idvente, l["idarticle"], l["idunite"], idmag),
                    )
                    qtvente = float((cur.fetchone() or [0])[0] or 0)
                except Exception:
                    qtvente = 0.0

                cur.execute(
                    """
                    INSERT INTO tb_livraisoncli
                    (reflivcli, refvente, idmag, idarticle, idunite, qtvente, qtlivrecli, dateregistre, iduser, idclient)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (refliv, refvente, idmag, l["idarticle"], l["idunite"], qtvente, q, datetime.now(), self.iduser, idclient),
                )

                cur.execute(
                    """
                    UPDATE tb_livraisoncli_attente
                       SET qt_bl = COALESCE(qt_bl,0) + %s,
                           dateupdate = NOW(),
                           iduser = %s
                     WHERE refvente=%s AND idmag=%s AND idarticle=%s AND idunite=%s
                    """,
                    (q, self.iduser, refvente, idmag, l["idarticle"], l["idunite"]),
                )
                cur.execute(
                    """
                    UPDATE tb_livraisoncli_attente
                       SET statut = CASE
                            WHEN COALESCE(qt_a_livrer,0) <= COALESCE(qt_bl,0) + 1e-9 THEN 'CLOTUREE'
                            ELSE 'EN_ATTENTE'
                       END
                     WHERE refvente=%s AND idmag=%s AND idarticle=%s AND idunite=%s
                    """,
                    (refvente, idmag, l["idarticle"], l["idunite"]),
                )

            conn.commit()

            # PDF A5 paysage (modèle mouvements)
            try:
                etat = EtatPDFMouvements()
                etat.connect_db()

                colonnes = ("Code", "Désignation", "Unité", "Qté")
                data_rows = [(x["code"], x["designation"], x["unite"], str(x["qte"])) for x in lignes if float(x["qte"]) > 0]
                table_data = (colonnes, data_rows)

                description = f"Livraison client — Facture {refvente}"
                output_path = os.path.join(os.getcwd(), f"Livraison_{refliv.replace('-', '_')}_A5.pdf")
                etat._build_pdf_a5(
                    output_path=output_path,
                    titre_entete="BON DE LIVRAISON",
                    reference=refliv,
                    date_operation=datetime.now().strftime("%d/%m/%Y"),
                    magasin=magasin_label,
                    operateur=operateur,
                    table_data=table_data,
                    description=description,
                    responsable_1="Livreur",
                    responsable_2="Client",
                )
                try:
                    etat.close_db()
                except Exception:
                    pass

                # Ouverture Windows
                try:
                    if os.name == "nt":
                        os.startfile(output_path)  # type: ignore[attr-defined]
                except Exception:
                    pass
            except Exception:
                pass

            messagebox.showinfo("Succès", f"BL {refliv} enregistré.")

        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            raise RuntimeError(f"Enregistrement BL échoué: {e}")
        finally:
            try:
                cur.close()
            except Exception:
                pass
            conn.close()
    
    def exporter_excel(self):
        """Exporte les données visibles vers un fichier Excel"""
        try:
            from tkinter import filedialog
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            
            # Vérifier s'il y a des données
            items_visibles = [item for item in self.tree.get_children() if self.tree.parent(item) == '']
            
            if not items_visibles:
                messagebox.showwarning("Attention", "Aucune donnée à exporter")
                return
            
            # Demander où enregistrer
            fichier = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                initialfile=f"stock_livraisons_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            )
            
            if not fichier:
                return
            
            # Créer le classeur Excel
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Stock et Livraisons"
            
            # Styles
            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF", size=12)
            border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            # En-têtes
            colonnes = [
                "Code Article",
                "Désignation Article",
                "Unité",
                "Magasin",
                "Nom Client",
                "Reste à Livrer",
                "Stock Théorique",
                "Stock Réel"
            ]
            
            for col_num, colonne in enumerate(colonnes, 1):
                cell = ws.cell(row=1, column=col_num)
                cell.value = colonne
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = border
            
            # Données
            for row_num, item in enumerate(items_visibles, 2):
                values = self.tree.item(item)['values']
                
                for col_num, value in enumerate(values, 1):
                    cell = ws.cell(row=row_num, column=col_num)
                    cell.value = value
                    cell.border = border
                    cell.alignment = Alignment(horizontal="center", vertical="center")
            
            # Ajuster la largeur des colonnes
            largeurs = {
                1: 15,  # Code Article
                2: 35,  # Désignation
                3: 12,  # Unité
                4: 20,  # Magasin
                5: 25,  # Nom Client
                6: 18,  # Reste à Livrer
                7: 18,  # Stock Théorique
                8: 15   # Stock Réel
            }
            
            for col_num, largeur in largeurs.items():
                ws.column_dimensions[openpyxl.utils.get_column_letter(col_num)].width = largeur
            
            # Ajouter des informations supplémentaires
            derniere_ligne = len(items_visibles) + 3
            ws.cell(row=derniere_ligne, column=1).value = f"Exporté le: {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}"
            ws.cell(row=derniere_ligne, column=1).font = Font(italic=True, size=9)
            
            ws.cell(row=derniere_ligne + 1, column=1).value = f"Total lignes: {len(items_visibles)}"
            ws.cell(row=derniere_ligne + 1, column=1).font = Font(bold=True, size=10)
            
            # Enregistrer
            wb.save(fichier)
            
            messagebox.showinfo(
                "Succès",
                f"Export réussi !\n\n{len(items_visibles)} lignes exportées vers:\n{fichier}"
            )
            try:
                from log_utils import AppLogger
                AppLogger(session_data=getattr(self, "session_data", {}) or {}).log(
                    action="Export Excel",
                    element="Stock Livraison",
                    details=f"export stock livraison, lignes={len(items_visibles)}, fichier={os.path.basename(fichier)}",
                    value=fichier,
                )
            except Exception:
                pass
            
        except ImportError:
            messagebox.showerror(
                "Erreur",
                "Le module 'openpyxl' n'est pas installé.\n\nInstallez-le avec:\npip install openpyxl"
            )
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'export Excel:\n{str(e)}")


# Test de la fenêtre
if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("1200x700")
    app.title("Gestion Stock et Livraisons")
    
    page = PageStockLivraison(app, iduser=1)
    page.pack(fill="both", expand=True)
    
    app.mainloop()