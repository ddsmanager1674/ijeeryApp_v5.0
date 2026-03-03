import customtkinter as ctk
from tkinter import ttk, messagebox, StringVar, BooleanVar
import psycopg2, psycopg2.extras, json
from datetime import datetime, timedelta
from resource_utils import get_config_path

SQL_TOUS = """
WITH RECURSIVE
    facteur_conversion AS (
        SELECT u.idunite, u.idarticle, u.niveau, u.designationunite,
               1.0::double precision AS facteur_vers_base
        FROM tb_unite u WHERE u.niveau = 0 AND u.deleted = 0
        UNION ALL
        SELECT u.idunite, u.idarticle, u.niveau, u.designationunite,
               fc.facteur_vers_base * u.qtunite
        FROM tb_unite u
        JOIN facteur_conversion fc ON fc.idarticle = u.idarticle
                                  AND fc.niveau = u.niveau - 1
        WHERE u.deleted = 0
    ),
    unite_max AS (
        SELECT DISTINCT ON (u.idarticle)
            u.idarticle, u.idunite, u.codearticle,
            u.designationunite, fc.facteur_vers_base
        FROM tb_unite u
        JOIN facteur_conversion fc ON fc.idunite = u.idunite
        WHERE u.deleted = 0
        ORDER BY u.idarticle, u.niveau DESC
    ),
    tous_mouvements AS (
        SELECT lf.idunite, lf.idmag, lf.qtlivrefrs AS quantite, 1 AS signe
          FROM tb_livraisonfrs lf WHERE lf.deleted = 0
        UNION ALL
        SELECT u.idunite, inv.idmag, inv.qtinventaire, 1
          FROM tb_inventaire inv
          JOIN tb_unite u ON u.codearticle = inv.codearticle
                         AND u.niveau = 0 AND u.deleted = 0
        UNION ALL
        SELECT ad.idunite, ad.idmag, ad.qtavoir, 1
          FROM tb_avoirdetail ad JOIN tb_avoir av ON av.id = ad.idavoir
         WHERE ad.deleted = 0 AND av.deleted = 0
        UNION ALL
        SELECT dce.idunite, dce.idmagasin, dce.quantite_entree::double precision, 1
          FROM tb_detailchange_entree dce
          JOIN tb_changement chg ON chg.idchg = dce.idchg
        UNION ALL
        SELECT td.idunite, td.idmagentree, td.qttransfertentree, 1
          FROM tb_transfertdetail td
          JOIN tb_transfert t ON t.idtransfert = td.idtransfert
         WHERE td.deleted = 0 AND t.deleted = 0
        UNION ALL
        SELECT vd.idunite, vd.idmag, vd.qtvente, -1
          FROM tb_ventedetail vd JOIN tb_vente v ON v.id = vd.idvente
         WHERE vd.deleted = 0 AND v.deleted = 0 AND v.statut = 'VALIDEE'
        UNION ALL
        SELECT sd.idunite, sd.idmag, sd.qtsortie, -1
          FROM tb_sortiedetail sd JOIN tb_sortie s ON s.id = sd.idsortie
         WHERE sd.deleted = 0 AND s.deleted = 0
        UNION ALL
        SELECT cid.idunite, cid.idmag, cid.qtconsomme::double precision, -1
          FROM tb_consommationinterne_details cid
          JOIN tb_consommationinterne ci ON ci.id = cid.idconsommation
        UNION ALL
        SELECT dcs.idunite, dcs.idmagasin, dcs.quantite_sortie::double precision, -1
          FROM tb_detailchange_sortie dcs
          JOIN tb_changement chg ON chg.idchg = dcs.idchg
        UNION ALL
        SELECT td.idunite, td.idmagsortie, td.qttransfertsortie, -1
          FROM tb_transfertdetail td
          JOIN tb_transfert t ON t.idtransfert = td.idtransfert
         WHERE td.deleted = 0 AND t.deleted = 0
    ),
    -- Stock PAR article ET PAR magasin
    stock_par_mag AS (
        SELECT fc.idarticle, tm.idmag,
               COALESCE(SUM(tm.quantite * fc.facteur_vers_base * tm.signe), 0.0)
                   AS stock_base_mag
        FROM tous_mouvements tm
        JOIN facteur_conversion fc ON fc.idunite = tm.idunite
        GROUP BY fc.idarticle, tm.idmag
    ),
    lots_ranked AS (
        SELECT lp.id, lp.id_article, lp.id_unite, lp.idmag,
               lp.quantite, lp.date_peremption, lp.priorite,
               lp.date_entree, lp.note,
               SUM(lp.quantite) OVER (
                   PARTITION BY lp.id_article, lp.id_unite, lp.idmag
                   ORDER BY lp.priorite DESC, lp.date_entree DESC
                   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
               ) AS cumul_depuis_recents
        FROM tb_lot_peremption lp WHERE lp.deleted = 0
    )

-- Articles AVEC lots
SELECT
    um.codearticle,
    a.designation                                                                    AS designationarticle,
    um.designationunite                                                              AS unite,
    um.facteur_vers_base,
    m.designationmag                                                                 AS designationmag,
    lr.idmag,
    ROUND((COALESCE(sm.stock_base_mag,0.0)/um.facteur_vers_base)::numeric, 4)        AS stock_global,
    lr.id                                                                            AS id_lot,
    lr.id_article,
    lr.id_unite,
    lr.date_peremption,
    lr.date_entree,
    lr.priorite,
    lr.note,
    ROUND((lr.quantite / um.facteur_vers_base)::numeric, 4)                          AS qt_lot_unite,
    ROUND(
        (GREATEST(0.0, LEAST(
            lr.quantite,
            COALESCE(sm.stock_base_mag,0.0) - (lr.cumul_depuis_recents - lr.quantite)
        )) / um.facteur_vers_base)::numeric
    , 4)                                                                             AS qt_restante_unite,
    a.idarticle,
    TRUE                                                                             AS has_lot
FROM lots_ranked lr
JOIN tb_article  a  ON a.idarticle  = lr.id_article AND a.deleted = 0
JOIN unite_max   um ON um.idarticle = lr.id_article
LEFT JOIN tb_magasin m  ON m.idmag  = lr.idmag
LEFT JOIN stock_par_mag sm ON sm.idarticle = lr.id_article AND sm.idmag = lr.idmag

UNION ALL

-- Articles SANS lot, une ligne par magasin où le stock > 0
SELECT
    um.codearticle,
    a.designation                                                                    AS designationarticle,
    um.designationunite                                                              AS unite,
    um.facteur_vers_base,
    m.designationmag                                                                 AS designationmag,
    sm.idmag,
    ROUND((sm.stock_base_mag / um.facteur_vers_base)::numeric, 4)                   AS stock_global,
    NULL   AS id_lot,
    a.idarticle AS id_article,
    um.idunite  AS id_unite,
    NULL   AS date_peremption,
    NULL   AS date_entree,
    NULL   AS priorite,
    NULL   AS note,
    NULL   AS qt_lot_unite,
    NULL   AS qt_restante_unite,
    a.idarticle,
    FALSE  AS has_lot
FROM tb_article a
JOIN unite_max   um ON um.idarticle = a.idarticle
JOIN stock_par_mag sm ON sm.idarticle = a.idarticle AND sm.stock_base_mag > 0
JOIN tb_magasin  m  ON m.idmag = sm.idmag AND m.deleted = 0
WHERE a.deleted = 0
  AND NOT EXISTS (
      SELECT 1 FROM tb_lot_peremption lp
      WHERE lp.id_article = a.idarticle
        AND lp.idmag = sm.idmag
        AND lp.deleted = 0
  )

ORDER BY codearticle, designationmag, priorite ASC NULLS LAST, date_entree ASC NULLS LAST;
"""

SQL_MAGASINS = "SELECT idmag, designationmag FROM tb_magasin WHERE deleted=0 ORDER BY designationmag;"


class PageGestionPeremption(ctk.CTkFrame):

    def __init__(self, parent, iduser=1):
        super().__init__(parent)
        self.iduser       = iduser
        self.all_rows     = []
        self.item_meta    = {}
        self.magasins     = []   # [(idmag, nom), ...]
        self.search_timer = None
        self._sort_state  = {}
        self.setup_ui()
        self._load_magasins()
        self.charger_donnees()

    # ── DB ────────────────────────────────────────────────────────────────
    def connect_db(self):
        try:
            with open(get_config_path('config.json')) as f:
                cfg = json.load(f)['database']
            return psycopg2.connect(host=cfg['host'], user=cfg['user'],
                password=cfg['password'], database=cfg['database'], port=cfg['port'])
        except Exception as e:
            messagebox.showerror("Connexion", f"Erreur : {e}"); return None

    def _exec(self, sql, params=()):
        conn = self.connect_db()
        if not conn: return []
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            messagebox.showerror("SQL", str(e)); return []
        finally: conn.close()

    def _exec_write(self, sql, params=()):
        conn = self.connect_db()
        if not conn: return False
        try:
            with conn.cursor() as cur: cur.execute(sql, params)
            conn.commit(); return True
        except Exception as e:
            conn.rollback(); messagebox.showerror("SQL", str(e)); return False
        finally: conn.close()

    def _load_magasins(self):
        rows = self._exec(SQL_MAGASINS)
        self.magasins = [(r['idmag'], r['designationmag']) for r in rows]
        # Mettre à jour le combobox magasin
        noms = ["Tous les magasins"] + [m[1] for m in self.magasins]
        try:
            self.combo_mag['values'] = noms
        except Exception:
            pass

    # ── Chargement ────────────────────────────────────────────────────────
    def charger_donnees(self):
        self.lbl_titre.configure(text="Suivi Peremptions  —  chargement...")
        self.update()
        rows  = self._exec(SQL_TOUS)
        terme = self.entry_recherche.get().strip().lower()
        if terme:
            rows = [r for r in rows
                    if terme in str(r['codearticle']).lower()
                    or terme in str(r['designationarticle']).lower()]
        self.all_rows = rows
        self._populate(rows)
        self.lbl_titre.configure(
            text=f"Suivi Peremptions  —  {len(self.item_meta)} lignes")
        self.lbl_statut.configure(
            text=f"MAJ : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # ── Tag couleur ───────────────────────────────────────────────────────
    @staticmethod
    def _tag(row):
        if not row.get('has_lot'):
            return 'sans_lot'
        today    = datetime.today().date()
        date_per = row['date_peremption']
        qt_rest  = float(row['qt_restante_unite'] or 0)
        if qt_rest <= 0: return 'epuise'
        if isinstance(date_per, datetime): date_per = date_per.date()
        if not date_per:  return 'normal'
        if date_per <= today:                         return 'perime'
        if date_per <= today + timedelta(days=30):    return 'urgent'
        if date_per <= today + timedelta(days=60):    return 'proche'
        return 'normal'

    # ── Populate ──────────────────────────────────────────────────────────
    def _populate(self, rows):
        self.tree.delete(*self.tree.get_children())
        self.item_meta = {}
        today    = datetime.today().date()

        # Filtre état
        filt     = self.var_filter.get()
        filt_map = {'Perime':'perime','< 1 mois':'urgent','< 2 mois':'proche',
                    '> 2 mois':'normal','Epuise':'epuise','Sans peremption':'sans_lot'}
        required = filt_map.get(filt)

        # Filtre magasin
        mag_sel  = self.var_magasin.get()

        # Checkbox
        with_per_only = self.var_with_per.get()

        for r in rows:
            tag = self._tag(r)

            # Filtre magasin
            if mag_sel and mag_sel != "Tous les magasins":
                if str(r.get('designationmag','')) != mag_sel:
                    continue

            if with_per_only and tag == 'sans_lot':
                continue

            if required and tag != required:
                continue

            has_lot  = bool(r.get('has_lot'))
            date_per = r['date_peremption']
            if isinstance(date_per, datetime): date_per = date_per.date()
            de = r['date_entree']
            date_entree_s = de.strftime('%d/%m/%Y') if hasattr(de,'strftime') else (str(de) if de else '')

            if date_per:
                j = (date_per - today).days
                jours_s    = f"PERIME {j}j" if j < 0 else f"{j} j"
                date_per_s = date_per.strftime('%d/%m/%Y')
            else:
                jours_s    = ''
                date_per_s = '— Aucune peremption —' if not has_lot else ''

            qt_rest  = float(r['qt_restante_unite'] or 0) if has_lot else None
            qt_lot   = float(r['qt_lot_unite']      or 0) if has_lot else None
            stock_gl = float(r['stock_global']       or 0)
            prio_s   = str(r['priorite']) if r['priorite'] is not None else ''
            mag_s    = r.get('designationmag') or '—'

            values = (
                r['codearticle'],
                r['designationarticle'],
                r['unite'],
                mag_s,                                                    # ← MAGASIN
                f"{stock_gl:,.2f}".replace(',',' '),
                prio_s,
                date_entree_s,
                date_per_s,
                jours_s,
                f"{qt_lot:,.2f}".replace(',',' ')  if qt_lot  is not None else '',
                f"{qt_rest:,.2f}".replace(',',' ') if qt_rest is not None else '',
                r['note'] or '',
            )
            iid = self.tree.insert('', 'end', values=values, tags=(tag,))
            self.item_meta[iid] = dict(r)

        nb_lots = sum(1 for r in self.item_meta.values() if r.get('has_lot'))
        nb_sans = sum(1 for r in self.item_meta.values() if not r.get('has_lot'))
        self.lbl_total.configure(
            text=f"Affiches : {len(self.item_meta)}   |   Avec lots : {nb_lots}   |   Sans peremption : {nb_sans}")

    # ── Filtres ───────────────────────────────────────────────────────────
    def on_search_change(self, *_):
        if self.search_timer: self.after_cancel(self.search_timer)
        self.search_timer = self.after(400, self.charger_donnees)

    def on_filter_change(self, *_):
        self._populate(self.all_rows)

    def _sort_by(self, col):
        reverse = self._sort_state.get(col, False)
        self._sort_state[col] = not reverse
        key_map = {
            "Code":"codearticle","Designation":"designationarticle",
            "Unite":"unite","Magasin":"designationmag",
            "Stock global":"stock_global","Priorite":"priorite",
            "Date entree":"date_entree","Date peremption":"date_peremption",
            "Qt lot":"qt_lot_unite","Qt restante":"qt_restante_unite",
        }
        k = key_map.get(col)
        if k:
            try: self._populate(sorted(self.all_rows,
                    key=lambda r:(r[k] is None, r[k]), reverse=reverse))
            except Exception: pass

    # ── Double-clic ───────────────────────────────────────────────────────
    def on_double_click(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid or iid not in self.item_meta: return
        row = self.item_meta[iid]
        if row.get('has_lot'):
            self.ouvrir_gestion_lot(row)
        else:
            self.ouvrir_ajout_peremption(row)

    # ── Fenetre : ajout peremption (article sans lot) ─────────────────────
    def ouvrir_ajout_peremption(self, row):
        WIN_W, WIN_H = 520, 480
        try: win = ctk.CTkToplevel(self)
        except Exception:
            from tkinter import Toplevel; win = Toplevel(self)
        win.title(f"Ajouter une peremption — {row['codearticle']}")
        win.resizable(False, False); win.grab_set()
        win.update_idletasks()
        x = (win.winfo_screenwidth()//2)-(WIN_W//2)
        y = (win.winfo_screenheight()//2)-(WIN_H//2)
        win.geometry(f"{WIN_W}x{WIN_H}+{x}+{y}")

        root = ctk.CTkFrame(win, fg_color="transparent")
        root.pack(fill="both", expand=True, padx=20, pady=14)

        # En-tete
        hdr = ctk.CTkFrame(root, fg_color="transparent")
        hdr.pack(fill="x", pady=(0,8))
        ctk.CTkLabel(hdr, text="📦", font=ctk.CTkFont(size=26)).pack(side="left", padx=(0,10))
        box = ctk.CTkFrame(hdr, fg_color="transparent")
        box.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(box, text=str(row['designationarticle']),
                     font=ctk.CTkFont(size=14, weight="bold"), anchor="w").pack(fill="x")
        ctk.CTkLabel(box,
                     text=f"Code : {row['codearticle']}   •   Unité : {row['unite']}",
                     font=ctk.CTkFont(size=11), text_color="gray60", anchor="w").pack(fill="x")

        ctk.CTkFrame(root, height=1, fg_color="gray30").pack(fill="x", pady=(0,12))

        # Info stock + magasin (lecture seule)
        stock_gl = float(row['stock_global'] or 0)
        mag_nom  = row.get('designationmag') or '—'

        info = ctk.CTkFrame(root, corner_radius=8)
        info.pack(fill="x", pady=(0,14))
        info.columnconfigure((0,1,2), weight=1)

        def info_card(parent, col, lbl, val, col_val=None):
            ctk.CTkLabel(parent, text=lbl, font=ctk.CTkFont(size=10),
                         text_color="gray60").grid(
                row=0, column=col, padx=12, pady=(10,2), sticky="w")
            kw = {"font": ctk.CTkFont(size=13, weight="bold"), "anchor":"w"}
            if col_val: kw["text_color"] = col_val
            ctk.CTkLabel(parent, text=str(val), **kw).grid(
                row=1, column=col, padx=12, pady=(0,10), sticky="w")

        info_card(info, 0, "Magasin",          mag_nom)
        info_card(info, 1, "Stock (ce magasin)", f"{stock_gl:,.2f} {row['unite']}")
        info_card(info, 2, "Lots existants",   "Aucun", col_val="#9e9e9e")

        ctk.CTkFrame(root, height=1, fg_color="gray30").pack(fill="x", pady=(0,12))

        ctk.CTkLabel(root, text="Nouveau lot de peremption",
                     font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x")
        ctk.CTkLabel(root,
                     text="Vous pouvez enregistrer tout le stock ou une partie seulement.",
                     font=ctk.CTkFont(size=10), text_color="gray60", anchor="w").pack(
            fill="x", pady=(2,10))

        form = ctk.CTkFrame(root, corner_radius=8)
        form.pack(fill="x", pady=(0,12))
        form.columnconfigure((0,1), weight=1)

        ctk.CTkLabel(form, text=f"Quantite du lot  (max {stock_gl:,.2f})",
                     font=ctk.CTkFont(size=11, weight="bold"), anchor="w").grid(
            row=0, column=0, padx=12, pady=(12,2), sticky="w")
        ctk.CTkLabel(form, text="Date de peremption  (JJ/MM/AAAA)",
                     font=ctk.CTkFont(size=11, weight="bold"), anchor="w").grid(
            row=0, column=1, padx=12, pady=(12,2), sticky="w")

        var_qt   = StringVar(value=f"{stock_gl:.4f}" if stock_gl > 0 else '')
        var_date = StringVar()
        var_note = StringVar()

        ctk.CTkEntry(form, textvariable=var_qt,   height=34, justify="center").grid(
            row=1, column=0, padx=12, pady=(0,10), sticky="ew")
        ctk.CTkEntry(form, textvariable=var_date, height=34,
                     placeholder_text="ex: 31/12/2025", justify="center").grid(
            row=1, column=1, padx=12, pady=(0,10), sticky="ew")

        ctk.CTkLabel(form, text="Note (optionnel)",
                     font=ctk.CTkFont(size=11, weight="bold"), anchor="w").grid(
            row=2, column=0, columnspan=2, padx=12, pady=(0,2), sticky="w")
        ctk.CTkEntry(form, textvariable=var_note, height=32).grid(
            row=3, column=0, columnspan=2, padx=12, pady=(0,12), sticky="ew")

        btn_frm = ctk.CTkFrame(root, fg_color="transparent")
        btn_frm.pack(fill="x", side="bottom", pady=(4,0))

        def do_ajouter():
            try:
                qt = float(var_qt.get().replace(',','.'))
            except ValueError:
                messagebox.showerror("Erreur","La quantite doit etre un nombre."); return
            if qt <= 0:
                messagebox.showerror("Erreur","La quantite doit etre > 0."); return
            try:
                dp = datetime.strptime(var_date.get().strip(), '%d/%m/%Y').date()
            except ValueError:
                messagebox.showerror("Erreur","Date invalide — format JJ/MM/AAAA."); return
            if dp < datetime.today().date():
                if not messagebox.askyesno("Attention",
                    "La date saisie est dans le passe. Continuer ?"): return

            conn = self.connect_db()
            if not conn: return
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT COALESCE(MAX(priorite),0) FROM tb_lot_peremption "
                    "WHERE id_article=%s AND id_unite=%s AND idmag=%s AND deleted=0",
                    (row['id_article'], row['id_unite'], row['idmag']))
                max_prio = cur.fetchone()[0]
                facteur  = float(row.get('facteur_vers_base') or 1)
                cur.execute(
                    """INSERT INTO tb_lot_peremption
                       (id_article, id_unite, idmag, quantite, date_peremption,
                        priorite, date_entree, type_source, note)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, 'MANUEL', %s)""",
                    (row['id_article'], row['id_unite'], row['idmag'],
                     qt * facteur, dp, max_prio + 1,
                     datetime.today().date(), var_note.get() or None))
                conn.commit()
                messagebox.showinfo("Succes",
                    f"Lot cree avec succes.\n"
                    f"Magasin : {mag_nom}\n"
                    f"Quantite : {qt:,.2f} {row['unite']}\n"
                    f"Date : {dp.strftime('%d/%m/%Y')}")
                win.destroy(); self.charger_donnees()
            except Exception as e:
                conn.rollback(); messagebox.showerror("Erreur SQL", str(e))
            finally: conn.close()

        ctk.CTkButton(btn_frm, text="Fermer", command=win.destroy,
            fg_color="transparent", border_width=1, border_color="gray50",
            text_color=("gray10","gray90"), width=110, height=36).pack(side="left")
        ctk.CTkButton(btn_frm, text="Creer le lot",
            command=do_ajouter, fg_color="#2e7d32", hover_color="#1b5e20",
            width=160, height=36,
            font=ctk.CTkFont(size=13, weight="bold")).pack(side="right")

    # ── Fenetre : gestion lot existant ────────────────────────────────────
    def ouvrir_gestion_lot(self, row):
        WIN_W, WIN_H = 600, 580
        try: win = ctk.CTkToplevel(self)
        except Exception:
            from tkinter import Toplevel; win = Toplevel(self)
        win.title(f"Lot #{row['id_lot']}  —  {row['designationarticle']}")
        win.resizable(False, False); win.grab_set()
        win.update_idletasks()
        x = (win.winfo_screenwidth()//2)-(WIN_W//2)
        y = (win.winfo_screenheight()//2)-(WIN_H//2)
        win.geometry(f"{WIN_W}x{WIN_H}+{x}+{y}")

        root = ctk.CTkFrame(win, fg_color="transparent")
        root.pack(fill="both", expand=True, padx=20, pady=14)

        # En-tete
        hdr = ctk.CTkFrame(root, fg_color="transparent")
        hdr.pack(fill="x", pady=(0,8))
        ctk.CTkLabel(hdr, text=f"Lot #{row['id_lot']}",
                     font=ctk.CTkFont(size=17, weight="bold")).pack(side="left")
        ctk.CTkLabel(hdr,
                     text=f"   {row['designationarticle']}  ({row['codearticle']})",
                     font=ctk.CTkFont(size=12), text_color="gray60").pack(side="left")
        ctk.CTkFrame(root, height=1, fg_color="gray30").pack(fill="x", pady=(0,10))

        today    = datetime.today().date()
        date_per = row['date_peremption']
        if isinstance(date_per, datetime): date_per = date_per.date()
        jours    = (date_per - today).days if date_per else None
        j_txt    = (f"PERIME depuis {abs(jours)}j" if jours is not None and jours < 0
                    else f"{jours} jours restants"   if jours is not None else '?')
        j_col    = ("#e53935" if jours is not None and jours <= 0
                    else "#fb8c00" if jours is not None and jours <= 30 else None)
        qt_rest  = float(row['qt_restante_unite'] or 0)
        qt_lot   = float(row['qt_lot_unite']      or 0)
        stock_gl = float(row['stock_global']       or 0)
        mag_nom  = row.get('designationmag') or '—'

        def card(parent, col, lbl, val, col_val=None, ncols=4):
            f = ctk.CTkFrame(parent, corner_radius=8)
            f.grid(row=0, column=col, sticky="nsew",
                   padx=(0 if col==0 else 5, 5 if col < ncols-1 else 0))
            ctk.CTkLabel(f, text=lbl, font=ctk.CTkFont(size=10),
                         text_color="gray60").pack(anchor="w", padx=10, pady=(8,1))
            kw = {"font": ctk.CTkFont(size=12, weight="bold"), "anchor":"w"}
            if col_val: kw["text_color"] = col_val
            ctk.CTkLabel(f, text=str(val), **kw).pack(anchor="w", padx=10, pady=(0,8))

        # Ligne 1 : magasin + priorité + date + jours
        c1 = ctk.CTkFrame(root, fg_color="transparent")
        c1.pack(fill="x", pady=(0,6)); c1.columnconfigure((0,1,2,3), weight=1)
        card(c1, 0, "Magasin",        mag_nom)
        card(c1, 1, "Priorite FIFO",  f"#{row['priorite']}")
        card(c1, 2, "Date peremption",
             date_per.strftime('%d/%m/%Y') if date_per else '?', col_val=j_col)
        card(c1, 3, "Jours restants", j_txt, col_val=j_col)

        # Ligne 2 : stock + qt lot + qt restante
        c2 = ctk.CTkFrame(root, fg_color="transparent")
        c2.pack(fill="x", pady=(0,10)); c2.columnconfigure((0,1,2), weight=1)

        def card3(parent, col, lbl, val, col_val=None):
            f = ctk.CTkFrame(parent, corner_radius=8)
            f.grid(row=0, column=col, sticky="nsew",
                   padx=(0 if col==0 else 5, 5 if col<2 else 0))
            ctk.CTkLabel(f, text=lbl, font=ctk.CTkFont(size=10),
                         text_color="gray60").pack(anchor="w", padx=10, pady=(8,1))
            kw = {"font": ctk.CTkFont(size=12, weight="bold"), "anchor":"w"}
            if col_val: kw["text_color"] = col_val
            ctk.CTkLabel(f, text=str(val), **kw).pack(anchor="w", padx=10, pady=(0,8))

        card3(c2, 0, "Stock magasin",      f"{stock_gl:,.2f} {row['unite']}")
        card3(c2, 1, "Qt initiale du lot", f"{qt_lot:,.2f} {row['unite']}")
        card3(c2, 2, "Qt restante (FIFO)", f"{qt_rest:,.2f} {row['unite']}",
              col_val="#e53935" if qt_rest<=0 else "#2e7d32")

        ctk.CTkFrame(root, height=1, fg_color="gray30").pack(fill="x", pady=(0,8))

        # Note
        ctk.CTkLabel(root, text="Note / Observation",
                     font=ctk.CTkFont(size=11, weight="bold"), anchor="w").pack(fill="x")
        var_note = StringVar(value=row.get('note') or '')
        ctk.CTkEntry(root, textvariable=var_note, height=32).pack(fill="x", pady=(4,10))

        ctk.CTkFrame(root, height=1, fg_color="gray30").pack(fill="x", pady=(0,8))

        # Split
        sp = ctk.CTkFrame(root, corner_radius=8)
        sp.pack(fill="x", pady=(0,10)); sp.columnconfigure((0,1,2,3), weight=1)
        ctk.CTkLabel(sp, text="Diviser ce lot en deux",
                     font=ctk.CTkFont(size=11, weight="bold")).grid(
            row=0, column=0, columnspan=4, padx=12, pady=(10,4), sticky="w")
        for i, lbl in enumerate(["Qt lot A","Date A (jj/mm/aaaa)",
                                  "Qt lot B","Date B (jj/mm/aaaa)"]):
            ctk.CTkLabel(sp, text=lbl, font=ctk.CTkFont(size=10),
                         text_color="gray60").grid(
                row=1, column=i, padx=(12 if i==0 else 6), sticky="w")
        var_qa = StringVar()
        var_da = StringVar(value=date_per.strftime('%d/%m/%Y') if date_per else '')
        var_qb = StringVar(); var_db = StringVar()
        for i, var in enumerate([var_qa, var_da, var_qb, var_db]):
            ctk.CTkEntry(sp, textvariable=var, height=30).grid(
                row=2, column=i,
                padx=(12 if i==0 else 6, 12 if i==3 else 0),
                pady=(2,10), sticky="ew")

        # Boutons
        btn_frm = ctk.CTkFrame(root, fg_color="transparent")
        btn_frm.pack(fill="x", side="bottom", pady=(4,0))

        def do_note():
            if self._exec_write(
                "UPDATE tb_lot_peremption SET note=%s WHERE id=%s",
                (var_note.get(), row['id_lot'])):
                messagebox.showinfo("Succes","Note enregistree.")

        def do_supprimer():
            if not messagebox.askyesno("Confirmer",
                f"Supprimer le lot #{row['id_lot']} du magasin '{mag_nom}' ?"): return
            if self._exec_write(
                "UPDATE tb_lot_peremption SET deleted=1 WHERE id=%s",
                (row['id_lot'],)):
                messagebox.showinfo("Succes","Lot supprime.")
                win.destroy(); self.charger_donnees()

        def do_split():
            try:
                qa = float(var_qa.get().replace(',','.')); qb = float(var_qb.get().replace(',','.'))
            except ValueError:
                messagebox.showerror("Erreur","Quantites invalides."); return
            try:
                da  = datetime.strptime(var_da.get().strip(),'%d/%m/%Y').date()
                db_ = datetime.strptime(var_db.get().strip(),'%d/%m/%Y').date()
            except ValueError:
                messagebox.showerror("Erreur","Dates invalides (JJ/MM/AAAA)."); return
            if round(qa+qb,6) != round(qt_lot,6):
                if not messagebox.askyesno("Attention",
                    f"Somme ({qa+qb:.4f}) != Qt initiale ({qt_lot:.4f}).\nContinuer ?"): return
            conn = self.connect_db()
            if not conn: return
            try:
                cur = conn.cursor()
                cur.execute("UPDATE tb_lot_peremption SET deleted=1 WHERE id=%s",(row['id_lot'],))
                cur.execute(
                    "SELECT COALESCE(MAX(priorite),0) FROM tb_lot_peremption "
                    "WHERE id_article=%s AND id_unite=%s AND idmag=%s AND deleted=0",
                    (row['id_article'], row['id_unite'], row['idmag']))
                max_prio = cur.fetchone()[0]
                facteur  = float(row.get('facteur_vers_base') or 1)
                for qt_u, dp, prio, label in [(qa,da,row['priorite'],'A'),(qb,db_,max_prio+1,'B')]:
                    cur.execute(
                        """INSERT INTO tb_lot_peremption
                           (id_article,id_unite,idmag,quantite,date_peremption,
                            priorite,date_entree,type_source,id_split,note)
                           VALUES(%s,%s,%s,%s,%s,%s,%s,'SPLIT',%s,%s)""",
                        (row['id_article'],row['id_unite'],row['idmag'],
                         qt_u*facteur,dp,prio,
                         datetime.today().date(),row['id_lot'],
                         f"Split lot #{row['id_lot']} part {label}"))
                conn.commit()
                messagebox.showinfo("Succes","Lot divise avec succes.")
                win.destroy(); self.charger_donnees()
            except Exception as e:
                conn.rollback(); messagebox.showerror("Erreur SQL",str(e))
            finally: conn.close()

        ctk.CTkButton(btn_frm, text="Supprimer", command=do_supprimer,
            fg_color="#c62828", hover_color="#b71c1c", width=120, height=34).pack(side="left")
        ctk.CTkButton(btn_frm, text="Sauver note", command=do_note,
            fg_color="#1565c0", hover_color="#0d47a1", width=110, height=34).pack(side="left",padx=8)
        ctk.CTkButton(btn_frm, text="Diviser", command=do_split,
            fg_color="#6a1b9a", hover_color="#4a148c", width=110, height=34).pack(side="left")
        ctk.CTkButton(btn_frm, text="Fermer", command=win.destroy,
            fg_color="transparent", border_width=1, border_color="gray50",
            text_color=("gray10","gray90"), width=100, height=34).pack(side="right")

    # ── Setup UI ──────────────────────────────────────────────────────────
    def setup_ui(self):
        self.lbl_titre = ctk.CTkLabel(self, text="Suivi Peremptions",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"))
        self.lbl_titre.pack(pady=(14,6))

        # Barre outils
        bar = ctk.CTkFrame(self)
        bar.pack(fill="x", padx=20, pady=(0,4))

        ctk.CTkLabel(bar, text="Recherche:", font=ctk.CTkFont(size=12)).pack(
            side="left", padx=(10,4), pady=8)
        self.entry_recherche = ctk.CTkEntry(bar,
            placeholder_text="Code ou designation...", width=220)
        self.entry_recherche.pack(side="left", padx=(0,8), pady=8)
        self.entry_recherche.bind("<KeyRelease>", self.on_search_change)

        # Filtre état
        self.var_filter = StringVar(value="Tous")
        try:
            cb = ttk.Combobox(bar,
                values=["Tous","Perime","< 1 mois","< 2 mois",
                        "> 2 mois","Epuise","Sans peremption"],
                textvariable=self.var_filter, state="readonly", width=16)
            cb.pack(side="left", padx=(0,8))
            cb.bind("<<ComboboxSelected>>", self.on_filter_change)
        except Exception:
            ctk.CTkOptionMenu(bar,
                values=["Tous","Perime","< 1 mois","< 2 mois",
                        "> 2 mois","Epuise","Sans peremption"],
                command=lambda _: self.on_filter_change()).pack(side="left", padx=(0,8))

        # Filtre magasin
        ctk.CTkLabel(bar, text="Magasin:", font=ctk.CTkFont(size=12)).pack(
            side="left", padx=(0,4))
        self.var_magasin = StringVar(value="Tous les magasins")
        try:
            self.combo_mag = ttk.Combobox(bar,
                values=["Tous les magasins"],
                textvariable=self.var_magasin, state="readonly", width=18)
            self.combo_mag.pack(side="left", padx=(0,8))
            self.combo_mag.bind("<<ComboboxSelected>>", self.on_filter_change)
        except Exception:
            self.combo_mag = ctk.CTkOptionMenu(bar,
                values=["Tous les magasins"],
                command=lambda _: self.on_filter_change())
            self.combo_mag.pack(side="left", padx=(0,8))

        ctk.CTkButton(bar, text="Actualiser", command=self.charger_donnees,
            fg_color="#2e7d32", hover_color="#1b5e20", width=110, height=30).pack(side="left")

        # Checkbox
        self.var_with_per = BooleanVar(value=False)
        ctk.CTkCheckBox(bar,
            text="Avec peremption uniquement",
            variable=self.var_with_per,
            command=self.on_filter_change,
            font=ctk.CTkFont(size=11)
        ).pack(side="left", padx=12)

        
        # Tableau
        tbl = ctk.CTkFrame(self)
        tbl.pack(fill="both", expand=True, padx=20, pady=(0,8))

        cols = ("Code","Designation","Unite","Magasin","Stock global",
                "Priorite","Date entree","Date peremption","Jours rest.",
                "Qt lot","Qt restante","Note")
        self.tree = ttk.Treeview(tbl, columns=cols, show="headings", height=18)

        self.tree.tag_configure('perime',   foreground="#e53935", font=("Segoe UI",9,"bold"))
        self.tree.tag_configure('urgent',   foreground="#fb8c00", font=("Segoe UI",9,"bold"))
        self.tree.tag_configure('proche',   foreground="#2e7d32", font=("Segoe UI",9))
        self.tree.tag_configure('normal',   foreground="#212121", font=("Segoe UI",9))
        self.tree.tag_configure('epuise',   foreground="#9e9e9e", font=("Segoe UI",9,"italic"))
        self.tree.tag_configure('sans_lot', foreground="#546e7a", font=("Segoe UI",9,"italic"))

        largeurs = {
            "Code":100,"Designation":200,"Unite":80,"Magasin":120,
            "Stock global":95,"Priorite":60,"Date entree":95,
            "Date peremption":155,"Jours rest.":85,
            "Qt lot":85,"Qt restante":100,"Note":150,
        }
        for col in cols:
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_by(c))
            self.tree.column(col, width=largeurs.get(col,100), anchor="center")
        self.tree.column("Designation",      anchor="w")
        self.tree.column("Magasin",          anchor="w")
        self.tree.column("Date peremption",  anchor="w")
        self.tree.column("Note",             anchor="w")

        sy = ctk.CTkScrollbar(tbl, orientation="vertical",   command=self.tree.yview)
        sx = ctk.CTkScrollbar(tbl, orientation="horizontal",  command=self.tree.xview)
        self.tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        sy.grid(row=0, column=1, sticky="ns"); sx.grid(row=1, column=0, sticky="ew")
        tbl.grid_rowconfigure(0, weight=1); tbl.grid_columnconfigure(0, weight=1)
        self.tree.bind("<Double-Button-1>", self.on_double_click)

        # Pied
        foot = ctk.CTkFrame(self)
        foot.pack(fill="x", padx=20, pady=(0,10))
        self.lbl_total = ctk.CTkLabel(foot, text="",
            font=ctk.CTkFont(size=11, weight="bold"))
        self.lbl_total.pack(side="left", padx=12)
        # Légende visuelle dans le pied de page
        legend = ctk.CTkFrame(foot, fg_color="transparent")
        legend.pack(side="left", padx=8)
        for txt, col in [
            ("Sans peremp.", "#546e7a"),
            ("Epuise",       "#9e9e9e"),
            ("> 2 mois",     "#424242"),
            ("< 2 mois",     "#43a047"),
            ("< 1 mois",     "#fb8c00"),
            ("Perime",       "#e53935"),
        ]:
            ctk.CTkLabel(legend, text=txt, text_color=col,
                font=ctk.CTkFont(size=10, weight="bold")).pack(side="right", padx=5)
        self.lbl_statut = ctk.CTkLabel(foot, text="", font=ctk.CTkFont(size=11))
        self.lbl_statut.pack(side="right", padx=12)


if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("1420x800")
    app.title("Gestion des Peremptions")
    PageGestionPeremption(app).pack(fill="both", expand=True)
    app.mainloop()