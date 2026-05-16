# -*- coding: utf-8 -*-
"""
Page Bon de Réception Fournisseur — iJeery
Refactorisé : thème app_theme, layout compact sans scrollbar, fournisseur unique auto-rempli.
Logique métier inchangée.
"""

import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import json
from datetime import datetime
from reportlab.lib.pagesizes import A5
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import os
from tkcalendar import DateEntry
from resource_utils import get_config_path, safe_file_read
from app_theme import Colors, Fonts, styled, Theme
from log_utils import AppLogger


# ─────────────────────────────────────────────────────────────────────────────
def _apply_treeview_style():
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("iJeery.Treeview",
                    background=Colors.BG_CARD, foreground=Colors.TEXT_PRIMARY,
                    fieldbackground=Colors.BG_CARD, rowheight=26,
                    font=("Segoe UI", 9), borderwidth=0)
    style.configure("iJeery.Treeview.Heading",
                    background=Colors.MIDNIGHT, foreground=Colors.TEXT_ON_DARK,
                    font=("Segoe UI", 9, "bold"), relief="flat", borderwidth=0)
    style.map("iJeery.Treeview",
              background=[("selected", Colors.PRIMARY_LIGHT)],
              foreground=[("selected", Colors.TEXT_PRIMARY)])
    style.map("iJeery.Treeview.Heading",
              background=[("active", Colors.MIDNIGHT_LIGHT)])


def _configure_alternating(tree):
    tree.tag_configure("row_even", background=Colors.BG_CARD)
    tree.tag_configure("row_odd",  background=Colors.BG_ROW_ALT)

def _refresh_alternating(tree):
    for i, iid in enumerate(tree.get_children()):
        tree.item(iid, tags=("row_even" if i % 2 == 0 else "row_odd",))


# ─────────────────────────────────────────────────────────────────────────────
class PageBonReception(ctk.CTkFrame):
    def __init__(self, parent, iduser):
        super().__init__(parent, fg_color=Colors.BG_PAGE)
        _apply_treeview_style()

        self.iduser   = iduser
        self.session_data = getattr(parent, "session_data", None) or {"user_id": self.iduser}
        self._logger = AppLogger(session_data=self.session_data, fallback_user_id=self.iduser)
        self.items_livraison  = []
        self.idcom_selectionne = None
        self.info_commande    = None
        self.infos_societe    = {}
        self.derniere_reflivfrs_enregistree = None
        self.var_a_payer = ctk.BooleanVar(value=False)

        self.setup_ui()
        self.generer_reference()
        self.charger_magasins()
        self.charger_infos_societe()

    # =========================================================================
    # DB
    # =========================================================================
    def connect_db(self):
        try:
            from pages.db_helper import connect_page_db
            return connect_page_db()
        except FileNotFoundError:
            messagebox.showerror("Erreur", "Fichier 'config.json' non trouvé.")
        except KeyError:
            messagebox.showerror("Erreur", "Clés DB manquantes dans 'config.json'.")
        except psycopg2.Error as e:
            messagebox.showerror("Connexion", f"Erreur PostgreSQL : {e}")
        except UnicodeDecodeError as e:
            messagebox.showerror("Encodage", f"Problème d'encodage : {e}")
        return None

    # =========================================================================
    # Helpers numériques (inchangés)
    # =========================================================================
    def formater_nombre(self, nombre):
        try:
            nombre = float(nombre)
            pi = int(nombre)
            pd = abs(nombre - pi)
            return f"{pi:,}".replace(',', '.') + "," + f"{pd:.2f}".split('.')[1]
        except:
            return "0,00"

    def parser_nombre(self, texte):
        try:
            return float(texte.replace('.', '').replace(',', '.'))
        except:
            return 0.0

    def nombre_en_lettres(self, nombre):
        try:
            from num2words import num2words
            entier = int(nombre)
            decimal = int(round((nombre - entier) * 100))
            texte = num2words(entier, lang='fr')
            if decimal > 0:
                texte += f" et {decimal:02d}/100"
            return texte.upper() + " ARIARY"
        except ImportError:
            return f"MONTANT À CONVERTIR: {self.formater_nombre(nombre)} ARIARY"
        except Exception:
            return ""

    # =========================================================================
    # UI — layout compact sans scrollbar
    # =========================================================================
    def setup_ui(self):
        # ── En-tête ──────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT, corner_radius=0, height=42)
        header.pack(fill="x")
        header.pack_propagate(False)

        # ── Toggle "Fournisseur à payer" ─────────────────────────────────────
        self.switch_a_payer = ctk.CTkSwitch(
            header,
            text="Fournisseur à payer",
            variable=self.var_a_payer,
            command=self._on_toggle_a_payer,
            font=Fonts.body(11),
            text_color=Colors.TEXT_ON_DARK,
            button_color=Colors.SUCCESS,
            progress_color=Colors.SUCCESS_DARK,
            switch_width=38, switch_height=20,
        )
        self.switch_a_payer.pack(side="left", padx=(14, 0))

        styled.button_secondary(header, text="🔄 Nouveau",
                                command=self.nouveau_bon_reception, width=100, height=28
                                ).pack(side="right", padx=8, pady=7)

        styled.button_info(
            header, text="Réception directe", icon="📥",
            command=self.ouvrir_reception_directe, width=160, height=28
        ).pack(side="right", padx=8, pady=7)

        # ── Corps ─────────────────────────────────────────────────────────────
        body = ctk.CTkFrame(self, fg_color=Colors.BG_PAGE)
        body.pack(fill="both", expand=True, padx=8, pady=6)

        self._build_section_infos(body)
        self._build_section_tableau(body)

    # ─────────────────────────────────────────────────────────────────────────
    # Section 1 — Informations (tout inline, compact)
    # ─────────────────────────────────────────────────────────────────────────
    def ouvrir_reception_directe(self):
        """
        Ouvre l'écran "Réception directe" (PageReceptionDirecte).
        Conçu pour être accessible depuis le menu "Bon de réception".
        """
        fen = ctk.CTkToplevel(self)
        fen.title("Réception directe")
        fen.geometry("1200x720")
        fen.resizable(True, True)
        fen.grab_set()

        try:
            Theme.apply_toplevel(fen)
        except Exception:
            pass

        try:
            from pages.page_receptiondirect import PageReceptionDirecte
        except ImportError:
            from page_receptiondirect import PageReceptionDirecte

        page = PageReceptionDirecte(fen, iduser=self.iduser)
        page.pack(fill="both", expand=True)

    def _build_section_infos(self, parent):
        card = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD,
                            corner_radius=8, border_width=1, border_color=Colors.BORDER)
        card.pack(fill="x", pady=(0, 4))

        # Ligne 1 : Réf | Charger commande | Fournisseur (readonly)
        r1 = ctk.CTkFrame(card, fg_color="transparent")
        r1.pack(fill="x", padx=10, pady=(6, 3))
        r1.columnconfigure(3, weight=1)

        ctk.CTkLabel(r1, text="📋 BR", font=Fonts.bold(11),
                     text_color=Colors.MIDNIGHT, width=36, anchor="w"
                     ).grid(row=0, column=0, sticky="w", padx=(0, 4))

        self.entry_ref = ctk.CTkEntry(r1, width=155, height=28,
                                      fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
                                      font=Fonts.body(11), state="readonly")
        self.entry_ref.grid(row=0, column=1, sticky="w", padx=(0, 8))

        ctk.CTkButton(r1, text="📂 Charger Commande", width=150, height=28,
                      fg_color=Colors.INFO, hover_color=Colors.INFO_DARK,
                      text_color="white", font=Fonts.body(10), corner_radius=6,
                      command=self.ouvrir_recherche_commande
                      ).grid(row=0, column=2, sticky="w", padx=(0, 12))

        ctk.CTkLabel(r1, text="Fournisseur :", font=Fonts.label(10),
                     text_color=Colors.TEXT_SECONDARY, anchor="w"
                     ).grid(row=0, column=3, sticky="w", padx=(0, 4))

        frs_f = ctk.CTkFrame(r1, fg_color="transparent")
        frs_f.grid(row=0, column=4, sticky="ew")
        r1.columnconfigure(4, weight=1)

        self.entry_fournisseur = ctk.CTkEntry(frs_f, height=28,
                                              fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
                                              font=Fonts.body(11), state="readonly")
        self.entry_fournisseur.pack(fill="x", expand=True)

        # Ligne 2 : Magasin | N° Facture
        r2 = ctk.CTkFrame(card, fg_color="transparent")
        r2.pack(fill="x", padx=10, pady=(0, 6))
        r2.columnconfigure(1, weight=1)
        r2.columnconfigure(3, weight=1)

        ctk.CTkLabel(r2, text="Magasin :", font=Fonts.label(10),
                     text_color=Colors.TEXT_SECONDARY, width=65, anchor="w"
                     ).grid(row=0, column=0, sticky="w", padx=(0, 4))

        self.combo_magasin = ctk.CTkComboBox(r2, height=28, state="readonly",
                                             fg_color=Colors.BG_INPUT,
                                             border_color=Colors.BORDER,
                                             font=Fonts.body(11))
        self.combo_magasin.grid(row=0, column=1, sticky="ew", padx=(0, 16))

        ctk.CTkLabel(r2, text="N° Facture :", font=Fonts.label(10),
                     text_color=Colors.TEXT_SECONDARY, width=75, anchor="w"
                     ).grid(row=0, column=2, sticky="w", padx=(0, 4))

        self.entry_factfrs = ctk.CTkEntry(r2, height=28,
                                          fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
                                          font=Fonts.body(11),
                                          placeholder_text="Saisir N° Facture Fournisseur")
        self.entry_factfrs.grid(row=0, column=3, sticky="ew")

    # ─────────────────────────────────────────────────────────────────────────
    # Section 2 — Tableau des articles livrés (expand)
    # ─────────────────────────────────────────────────────────────────────────
    def _build_section_tableau(self, parent):
        card = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD,
                            corner_radius=8, border_width=1, border_color=Colors.BORDER)
        card.pack(fill="both", expand=True, pady=(0, 0))

        # En-tête tableau
        thead = ctk.CTkFrame(card, fg_color="transparent")
        thead.pack(fill="x", padx=10, pady=(6, 4))

        ctk.CTkLabel(thead, text="📦 Articles Livrés",
                     font=Fonts.bold(11), text_color=Colors.MIDNIGHT
                     ).pack(side="left")

        self.label_total = ctk.CTkLabel(
            thead, text="Total : 0,00",
            font=Fonts.bold(12), text_color=Colors.SUCCESS_TEXT,
            fg_color=Colors.SUCCESS_LIGHT, corner_radius=6, padx=10, pady=3
        )
        self.label_total.pack(side="right")

        # Treeview
        tree_frame = ctk.CTkFrame(card, fg_color=Colors.BORDER, corner_radius=6)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 4))

        colonnes = ("Article", "Unité", "Date péremption", "Fournisseur", "Qté Livrée", "Prix Unit.", "Montant")
        self.tree = ttk.Treeview(tree_frame, columns=colonnes,
                                  show="headings", height=8, style="iJeery.Treeview")
        _configure_alternating(self.tree)

        col_widths = {"Article": 260, "Unité": 90, "Date péremption": 105,
                      "Fournisseur": 155, "Qté Livrée": 90, "Prix Unit.": 100, "Montant": 105}
        for col in colonnes:
            self.tree.column(col, width=col_widths.get(col, 90),
                             anchor="w" if col in ("Article", "Fournisseur") else "center",
                             minwidth=60)

        from treeview_sort_utils import attach_tree_sort
        attach_tree_sort(self.tree, list(colonnes), configure_columns=False)
        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Barre basse : Enregistrer à droite uniquement
        bot = ctk.CTkFrame(card, fg_color="transparent")
        bot.pack(fill="x", padx=10, pady=(0, 6))

        styled.button_success(bot, text="💾 Enregistrer",
                              command=self.enregistrer_livraison, width=140, height=28
                              ).pack(side="right")

    # =========================================================================
    # LOGIQUE MÉTIER — inchangée
    # =========================================================================

    def toggle_date_peremption(self):
        pass

    def charger_magasins(self):
        conn = self.connect_db()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT idmag, designationmag FROM tb_magasin WHERE deleted = 0 ORDER BY designationmag")
            rows = cursor.fetchall()
            self.magasins = {r[1]: r[0] for r in rows}
            self.combo_magasin.configure(values=list(self.magasins.keys()))
            if self.magasins:
                idmag_defaut = None
                cursor.execute("SELECT idmag FROM tb_users WHERE iduser = %s LIMIT 1", (self.iduser,))
                row_user = cursor.fetchone()
                if row_user:
                    idmag_defaut = row_user[0]
                nom_defaut = next((n for n, i in self.magasins.items() if i == idmag_defaut), None)
                self.combo_magasin.set(nom_defaut if nom_defaut else list(self.magasins.keys())[0])
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur chargement magasins: {e}")
        finally:
            cursor.close(); conn.close()

    def generer_reference(self):
        conn = self.connect_db()
        if not conn: return
        try:
            cursor = conn.cursor()
            annee = datetime.now().year
            cursor.execute("SELECT reflivfrs FROM tb_livraisonfrs WHERE reflivfrs LIKE %s ORDER BY reflivfrs DESC LIMIT 1",
                           (f"{annee}-BR-%",))
            r = cursor.fetchone()
            num = (int(r[0].split('-')[-1]) + 1) if r else 1
            ref = f"{annee}-BR-{num:05d}"
            self.entry_ref.configure(state="normal")
            self.entry_ref.delete(0, "end")
            self.entry_ref.insert(0, ref)
            self.entry_ref.configure(state="readonly")
        except Exception as e:
            messagebox.showerror("Erreur", f"Référence : {e}")
        finally:
            cursor.close(); conn.close()

    def ouvrir_recherche_commande(self):
        fen = ctk.CTkToplevel(self)
        fen.title("Sélectionner une commande")
        fen.geometry("900x500")
        fen.grab_set()
        Theme.apply_toplevel(fen)

        main = ctk.CTkFrame(fen, fg_color=Colors.BG_PAGE)
        main.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(main, text="Sélectionner une commande avec articles livrés",
                     font=Fonts.heading(14), text_color=Colors.MIDNIGHT).pack(pady=(0, 8))

        sf = ctk.CTkFrame(main, fg_color="transparent")
        sf.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(sf, text="🔍").pack(side="left", padx=6)
        entry_s = ctk.CTkEntry(sf, placeholder_text="Référence ou fournisseur...", height=32,
                               fg_color=Colors.BG_INPUT, border_color=Colors.BORDER, font=Fonts.body(11))
        entry_s.pack(side="left", fill="x", expand=True, padx=4)

        tf = ctk.CTkFrame(main, fg_color=Colors.BORDER, corner_radius=8)
        tf.pack(fill="both", expand=True, pady=(0, 8))
        cols = ("ID", "Référence BC", "Date", "Fournisseur", "Articles Livrés")
        tree = ttk.Treeview(tf, columns=cols, show="headings", height=12, style="iJeery.Treeview")
        _configure_alternating(tree)
        tree.column("ID", width=0, stretch=False)
        tree.column("Référence BC", width=130); tree.column("Date", width=110)
        tree.column("Fournisseur", width=260); tree.column("Articles Livrés", width=110, anchor="center")
        for c in cols: tree.heading(c, text=c)
        sb2 = ttk.Scrollbar(tf, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb2.set)
        tree.pack(side="left", fill="both", expand=True)
        sb2.pack(side="right", fill="y")

        lbl_c = ctk.CTkLabel(main, text="", font=Fonts.small(10), text_color=Colors.TEXT_MUTED)
        lbl_c.pack(pady=(0, 4))

        def charger_commandes(filtre=""):
            for i in tree.get_children(): tree.delete(i)
            conn = self.connect_db()
            if not conn: return
            try:
                cursor = conn.cursor()
                q = """
                    SELECT DISTINCT c.idcom, c.refcom, c.datemodif,
                           COALESCE(NULLIF((
                               SELECT string_agg(DISTINCT COALESCE(f2.nomfrs,''),', ' ORDER BY COALESCE(f2.nomfrs,''))
                               FROM tb_commandedetail d2
                               LEFT JOIN tb_fournisseur f2 ON d2.idfrs=f2.idfrs
                               WHERE d2.idcom=c.idcom),''),'Fournisseur non précisé') AS frs,
                           (SELECT COUNT(*) FROM tb_commandedetail d WHERE d.idcom=c.idcom AND d.qtlivre>0) as nb
                    FROM tb_commande c
                    WHERE c.deleted=0
                    AND EXISTS (SELECT 1 FROM tb_commandedetail d WHERE d.idcom=c.idcom AND d.qtlivre>0)
                """
                p = []
                if filtre:
                    q += " AND (LOWER(c.refcom) LIKE LOWER(%s))"
                    p = [f"%{filtre}%"]
                q += " ORDER BY c.datemodif DESC, c.refcom DESC"
                cursor.execute(q, p)
                rows = cursor.fetchall()
                for r in rows:
                    ds = r[2].strftime("%d/%m/%Y %H:%M") if r[2] else ""
                    tree.insert("", "end", values=(r[0], r[1], ds, r[3] or "", f"✅ {r[4]}"))
                _refresh_alternating(tree)
                lbl_c.configure(text=f"{len(rows)} commande(s)")
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
            finally:
                cursor.close(); conn.close()

        entry_s.bind('<KeyRelease>', lambda e: charger_commandes(entry_s.get()))

        def valider():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Attention", "Sélectionnez une commande.", parent=fen)
                return
            idcom = tree.item(sel[0])["values"][0]
            fen.destroy()
            self.charger_commande(idcom)

        def supprimer_commande():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning(
                    "Attention",
                    "Sélectionnez une commande à supprimer.",
                    parent=fen,
                )
                return
            vals = tree.item(sel[0])["values"]
            idcom = vals[0]
            refcom = vals[1] if len(vals) > 1 else str(idcom)
            if not messagebox.askyesno(
                "Confirmer la suppression",
                f"Supprimer la commande {refcom} ?\n\n"
                "Elle ne sera plus visible dans cette liste ni dans le "
                "chargement de commande du bon de commande.",
                parent=fen,
            ):
                return
            conn = self.connect_db()
            if not conn:
                return
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE tb_commande
                    SET deleted = 1, datemodif = %s
                    WHERE idcom = %s AND COALESCE(deleted, 0) = 0
                    """,
                    (datetime.now(), idcom),
                )
                if cursor.rowcount == 0:
                    conn.rollback()
                    messagebox.showerror(
                        "Erreur",
                        "Commande introuvable ou déjà supprimée.",
                        parent=fen,
                    )
                    return
                conn.commit()
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Erreur", f"Suppression : {e}", parent=fen)
                return
            finally:
                cursor.close()
                conn.close()

            if getattr(self, "idcom_selectionne", None) == idcom:
                self.reinitialiser_formulaire(generer_ref=False)
            charger_commandes(entry_s.get().strip())
            messagebox.showinfo(
                "Succès",
                f"Commande {refcom} supprimée.",
                parent=fen,
            )

        tree.bind("<Double-Button-1>", lambda e: valider())
        bf = ctk.CTkFrame(main, fg_color="transparent")
        bf.pack(fill="x")
        styled.button_danger(
            bf,
            text="Supprimer cette commande",
            icon="🗑",
            width=200,
            height=34,
            command=supprimer_commande,
        ).pack(side="left", padx=4)
        styled.button_success(
            bf, text="Charger", icon="📂", width=120, height=34, command=valider,
        ).pack(side="right", padx=4)
        charger_commandes()

    def charger_commande(self, idcom):
        conn = self.connect_db()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.idcom, c.refcom, c.datemodif, c.idfrs, f.nomfrs
                FROM tb_commande c
                LEFT JOIN tb_fournisseur f ON c.idfrs=f.idfrs
                WHERE c.idcom=%s AND c.deleted=0
            """, (idcom,))
            commande = cursor.fetchone()
            if not commande:
                messagebox.showerror("Erreur", "Commande non trouvée"); return

            cursor.execute("""
                SELECT d.id, d.idarticle, a.designation, u.designationunite, d.idunite,
                       d.qtlivre, d.punitcmd, d.dateperemption,
                       COALESCE(f_d.nomfrs, f_c.nomfrs, '') AS nomfrs
                FROM tb_commandedetail d
                INNER JOIN tb_commande c ON d.idcom=c.idcom
                INNER JOIN tb_article a ON d.idarticle=a.idarticle
                INNER JOIN tb_unite u ON d.idunite=u.idunite
                LEFT JOIN tb_fournisseur f_d ON d.idfrs=f_d.idfrs
                LEFT JOIN tb_fournisseur f_c ON c.idfrs=f_c.idfrs
                WHERE d.idcom=%s AND d.qtlivre>0
            """, (idcom,))
            details = cursor.fetchall()

            if not details:
                messagebox.showwarning("Attention", "Aucun article livré dans cette commande"); return

            self.reinitialiser_formulaire(generer_ref=False)
            self.idcom_selectionne = idcom
            self.info_commande = commande

            # ── Fournisseur unique : si tous les détails ont le même fournisseur, l'afficher ──
            noms_frs = set(d[8] for d in details if d[8])
            nom_frs_affiche = list(noms_frs)[0] if len(noms_frs) == 1 else (commande[4] or "")
            self.entry_fournisseur.configure(state="normal")
            self.entry_fournisseur.delete(0, "end")
            self.entry_fournisseur.insert(0, nom_frs_affiche)
            self.entry_fournisseur.configure(state="readonly")

            for d in details:
                (idcd, idar, desig, unite, idunite, qtlivre, punitcmd, datep, nomfrs_ligne) = d
                punitcmd = punitcmd or 0
                montant  = (qtlivre or 0) * punitcmd
                date_str = datep.strftime('%d/%m/%Y') if datep else '-'
                self.tree.insert("", "end", values=(
                    desig, unite, date_str, nomfrs_ligne or "",
                    self.formater_nombre(qtlivre or 0),
                    self.formater_nombre(punitcmd),
                    self.formater_nombre(montant)
                ))
                self.items_livraison.append({
                    'idcomdetail': idcd, 'idarticle': idar, 'idunite': idunite,
                    'fournisseur': nomfrs_ligne or "", 'qtlivre': qtlivre or 0,
                    'punitcmd': punitcmd, 'dateperemption': datep
                })
            _refresh_alternating(self.tree)
            self.calculer_total()
            messagebox.showinfo("Succès", f"Commande {commande[1]} chargée avec {len(details)} article(s) livré(s)")
        except Exception as e:
            messagebox.showerror("Erreur", f"Chargement : {e}")
        finally:
            cursor.close(); conn.close()

    def calculer_total(self):
        total = sum(i['qtlivre'] * i['punitcmd'] for i in self.items_livraison)
        self.label_total.configure(text=f"Total : {self.formater_nombre(total)}")

    def _on_toggle_a_payer(self):
        """Change la couleur du header selon l'état du switch Fournisseur à payer."""
        if self.var_a_payer.get():
            # ON → fond vert Success pour signaler visuellement
            self.switch_a_payer.master.configure(fg_color=Colors.SUCCESS_DARK)
            self.switch_a_payer.configure(text_color=Colors.TEXT_ON_DARK,
                                          button_color=Colors.TEXT_ON_DARK,
                                          progress_color=Colors.SUCCESS)
        else:
            # OFF → retour au fond MIDNIGHT
            self.switch_a_payer.master.configure(fg_color=Colors.MIDNIGHT)
            self.switch_a_payer.configure(text_color=Colors.TEXT_ON_DARK,
                                          button_color=Colors.SUCCESS,
                                          progress_color=Colors.SUCCESS_DARK)

    def enregistrer_livraison(self):
        if not self.idcom_selectionne:
            messagebox.showwarning("Attention", "Veuillez charger une commande"); return

        conn = self.connect_db()
        if not conn: return

        try:
            cursor = conn.cursor()
            numero_facture = self.entry_factfrs.get().strip()
            if not numero_facture:
                messagebox.showwarning("Attention", "Veuillez saisir le N° Facture Fournisseur."); return

            dateregistre = datetime.now()
            idmag = self.magasins.get(self.combo_magasin.get())
            a_payer = 1 if self.var_a_payer.get() else 0

            q_insert = """
                INSERT INTO tb_livraisonfrs
                (reflivfrs, idcom, idarticle, idunite, qtlivrefrs, dateregistre,
                 typemouvement, idmag, factfrs, iduser, dateperemption, a_payer)
                VALUES (%s,%s,%s,%s,%s,%s,1,%s,%s,%s,%s,%s)
            """
            items_avec_peremption = []

            for item in self.items_livraison:
                cursor.execute(q_insert, (
                    self.entry_ref.get(), self.idcom_selectionne,
                    item['idarticle'], item['idunite'], item['qtlivre'],
                    dateregistre, idmag, numero_facture, self.iduser,
                    item.get('dateperemption'), a_payer
                ))
                item_date_per = item.get('dateperemption')
                if item_date_per:
                    items_avec_peremption.append({
                        'idarticle': item['idarticle'], 'idunite': item['idunite'],
                        'qtlivre': item['qtlivre'], 'dateperemption': item_date_per,
                    })

            if items_avec_peremption:
                for ip in items_avec_peremption:
                    cursor.execute("""
                        SELECT COALESCE(MAX(priorite),0) FROM tb_lot_peremption
                        WHERE id_article=%s AND id_unite=%s AND idmag=%s AND deleted=0
                    """, (ip['idarticle'], ip['idunite'], idmag))
                    max_prio = cursor.fetchone()[0]
                    cursor.execute("""
                        INSERT INTO tb_lot_peremption
                            (id_article, id_unite, idmag, quantite, date_peremption,
                             priorite, date_entree, type_source, note)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,'LIVRAISON',%s)
                    """, (ip['idarticle'], ip['idunite'], idmag, ip['qtlivre'],
                          ip['dateperemption'], max_prio + 1, dateregistre.date(),
                          f"BL {self.entry_ref.get()} — fact. {numero_facture}"))

            conn.commit()
            self.derniere_reflivfrs_enregistree = self.entry_ref.get()
            try:
                self._logger.log(
                    action="Création livraison fournisseur",
                    element=str(self.derniere_reflivfrs_enregistree),
                    details=f"Livraison fournisseur enregistrée (commande_id={self.idcom_selectionne}, magasin_id={idmag}, lignes={len(self.items_livraison)}, factfrs='{numero_facture}', a_payer={a_payer})",
                    value=f"{len(self.items_livraison)} lignes",
                )
            except Exception:
                pass

            messagebox.showinfo("Succès",
                f"Enregistrement effectué avec succès.\nRéférence: {self.derniere_reflivfrs_enregistree}"
                + (f"\n{len(items_avec_peremption)} lot(s) de péremption créé(s)."
                   if items_avec_peremption else ""))

            # ── Génération PDF automatique ────────────────────────────────────
            try:
                data = self.get_data_bon_reception()
                if data:
                    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    etats_dir   = os.path.join(project_dir, "Etats Impression")
                    if not os.path.exists(etats_dir): os.makedirs(etats_dir)
                    filename = os.path.join(etats_dir, f"BR_{self.entry_ref.get().replace('-','_')}_A5.pdf")
                    cols = ("Code", "Désignation", "Unité", "Qté", "Fournisseur")
                    rows_pdf = []
                    for detail in data.get('details', []):
                        rows_pdf.append((detail.get('code',''), detail.get('designation',''),
                                         detail.get('unite',''), detail.get('qtlivre',0),
                                         detail.get('fournisseur','')))
                    operateur = (data.get('utilisateur',{}).get('prenomuser','') + ' ' +
                                 data.get('utilisateur',{}).get('nomuser','')).strip() or str(self.iduser)
                    try:
                        from EtatsPDF_Mouvements import EtatPDFMouvements
                        etat = EtatPDFMouvements()
                        try: etat.connect_db()
                        except: pass
                        success = etat._build_pdf_a5(
                            output_path=filename, titre_entete="BON DE RÉCEPTION",
                            reference=self.entry_ref.get(),
                            date_operation=data['reception'].get('dateregistre', datetime.now().strftime('%d/%m/%Y')),
                            magasin=data['reception'].get('magasin',''), operateur=operateur,
                            table_data=(cols, rows_pdf), description=numero_facture,
                            responsable_1="Le Responsable",
                            responsable_2=data['reception'].get('fournisseur','Fournisseur'))
                        try: etat.close_db()
                        except: pass
                        if success:
                            try: self.open_file(filename)
                            except: pass
                    except Exception as ep:
                        print(f"Erreur PDF BR: {ep}")
            except Exception as ep:
                print(f"Erreur données PDF: {ep}")

            self.reinitialiser_formulaire()

        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur", f"Enregistrement : {e}")
        finally:
            cursor.close(); conn.close()

    def nouveau_bon_reception(self):
        if self.items_livraison:
            if not messagebox.askyesno("Confirmation",
                    "Voulez-vous créer un nouveau bon ?\nLes données non enregistrées seront perdues."):
                return
        self.reinitialiser_formulaire()

    def reinitialiser_formulaire(self, generer_ref=True):
        if generer_ref: self.generer_reference()
        self.charger_magasins()
        self.items_livraison.clear()
        self.idcom_selectionne = None
        self.info_commande = None
        self.derniere_reflivfrs_enregistree = None
        for i in self.tree.get_children(): self.tree.delete(i)
        self.entry_fournisseur.configure(state="normal")
        self.entry_fournisseur.delete(0, "end")
        self.entry_fournisseur.configure(state="readonly")
        self.entry_factfrs.delete(0, "end")
        self.var_a_payer.set(False)
        self._on_toggle_a_payer()
        self.calculer_total()

    def charger_infos_societe(self):
        conn = self.connect_db()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT nomsociete, adressesociete, contactsociete, villesociete,
                       nifsociete, statsociete, cifsociete
                FROM tb_infosociete LIMIT 1
            """)
            r = cursor.fetchone()
            if r:
                self.infos_societe = {
                    'nomsociete': r[0] or 'SOCIÉTÉ', 'adressesociete': r[1] or 'N/A',
                    'contactsociete': r[2] or 'N/A', 'villesociete': r[3] or 'N/A',
                    'nifsociete': r[4] or 'N/A', 'statsociete': r[5] or 'N/A',
                    'cifsociete': r[6] or 'N/A'
                }
            else:
                self.infos_societe = {k: 'N/A' for k in
                    ['nomsociete','adressesociete','contactsociete','villesociete',
                     'nifsociete','statsociete','cifsociete']}
                self.infos_societe['nomsociete'] = 'SOCIÉTÉ'
        except Exception as e:
            print(f"Erreur infos société: {e}")
            self.infos_societe = {k: 'N/A' for k in
                ['nomsociete','adressesociete','contactsociete','villesociete',
                 'nifsociete','statsociete','cifsociete']}
        finally:
            if 'cursor' in locals(): cursor.close()
            if conn: conn.close()

    def get_data_bon_reception(self):
        data = {
            'societe': self.infos_societe,
            'reception': {
                'reflivfrs': self.entry_ref.get(),
                'dateregistre': datetime.now().strftime("%d/%m/%Y %H:%M"),
                'fournisseur': self.entry_fournisseur.get(),
                'magasin': self.combo_magasin.get(),
                'factfrs': self.entry_factfrs.get()
            },
            'utilisateur': {}, 'details': []
        }
        conn = self.connect_db()
        if not conn: return None
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT nomuser, prenomuser FROM tb_users WHERE iduser=%s", (self.iduser,))
            u = cursor.fetchone()
            if u: data['utilisateur'] = {'nomuser': u[0], 'prenomuser': u[1]}
            for item in self.items_livraison:
                cursor.execute("SELECT designation FROM tb_article WHERE idarticle=%s", (item['idarticle'],))
                desig = cursor.fetchone()
                cursor.execute("SELECT codearticle, designationunite FROM tb_unite WHERE idunite=%s", (item['idunite'],))
                unite_info = cursor.fetchone()
                if desig and unite_info:
                    data['details'].append({
                        'code': unite_info[0], 'designation': desig[0], 'unite': unite_info[1],
                        'fournisseur': item.get('fournisseur',''),
                        'qtlivre': item['qtlivre'], 'punitcmd': item['punitcmd']
                    })
            return data
        except Exception as e:
            messagebox.showerror("Erreur", f"Données impression : {e}"); return None
        finally:
            if 'cursor' in locals(): cursor.close()
            if conn: conn.close()

    def generer_pdf_a5(self):
        data = self.get_data_bon_reception()
        if not data: return
        filename = f"BR_{self.entry_ref.get().replace('-','_')}_A5.pdf"
        try:
            doc = SimpleDocTemplate(filename, pagesize=A5,
                                    leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
            styles = getSampleStyleSheet()
            elements = []
            societe = data['societe']
            style_h = styles['Normal']; style_h.fontSize = 8; style_h.alignment = 1

            elements.append(Paragraph(f"<b>{societe.get('nomsociete','NOM SOCIÉTÉ')}</b>", styles['Heading4']))
            elements.append(Paragraph(
                f"{societe.get('adressesociete','')}, {societe.get('villesociete','')} — Tél: {societe.get('contactsociete','')}",
                style_h))
            elements.append(Paragraph(
                f"NIF: {societe.get('nifsociete','')} | STAT: {societe.get('statsociete','')} | CIF: {societe.get('cifsociete','')}",
                style_h))
            elements.append(Spacer(1, 10))

            style_titre = styles['Heading3']; style_titre.alignment = 1
            elements.append(Paragraph(f"<u>BON DE RÉCEPTION N°{data['reception']['reflivfrs']}</u>", style_titre))
            elements.append(Spacer(1, 10))

            data_hdr = [
                [Paragraph(f"<b>Date:</b> {data['reception']['dateregistre']}", style_h),
                 Paragraph(f"<b>Fournisseur:</b> {data['reception']['fournisseur']}", style_h)],
                [Paragraph(f"<b>Magasin:</b> {data['reception']['magasin']}", style_h),
                 Paragraph(f"<b>Facture N°:</b> {data['reception']['factfrs']}", style_h)],
                [Paragraph(f"<b>Établi par:</b> {data['utilisateur'].get('prenomuser','')} {data['utilisateur'].get('nomuser','')}", style_h), ""]
            ]
            tbl_hdr = Table(data_hdr, colWidths=[185, 185])
            tbl_hdr.setStyle(TableStyle([
                ('ALIGN',(0,0),(-1,-1),'LEFT'), ('VALIGN',(0,0),(-1,-1),'TOP'),
                ('BOTTOMPADDING',(0,0),(-1,-1),4), ('GRID',(0,0),(-1,-1),0.2,colors.lightgrey)
            ]))
            elements.append(tbl_hdr); elements.append(Spacer(1, 10))

            table_data = [['Code','Désignation','Unité','Qté','P.U','Montant','Fournisseur']]
            total_g = 0
            for detail in data['details']:
                montant = detail['qtlivre'] * detail['punitcmd']
                total_g += montant
                table_data.append([
                    detail['code'], Paragraph(detail['designation'], styles['Normal']),
                    detail['unite'], self.formater_nombre(detail['qtlivre']),
                    self.formater_nombre(detail['punitcmd']), self.formater_nombre(montant),
                    Paragraph(detail.get('fournisseur',''), styles['Normal'])
                ])
            table_data.append(['','','','','','TOTAL:', self.formater_nombre(total_g)])

            tbl = Table(table_data, colWidths=[35,95,35,35,45,45,80])
            tbl.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#2c3e50')),
                ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
                ('ALIGN',(0,0),(-1,-1),'LEFT'), ('ALIGN',(3,1),(5,-1),'RIGHT'),
                ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
                ('GRID',(0,0),(-1,-2),0.5,colors.black),
                ('FONTSIZE',(0,0),(-1,-1),7), ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                ('BACKGROUND',(0,-1),(-1,-1),colors.lightgrey),
                ('FONTNAME',(0,-1),(-1,-1),'Helvetica-Bold'), ('FONTSIZE',(0,-1),(-1,-1),8),
            ]))
            elements.append(tbl); elements.append(Spacer(1,15))
            elements.append(Paragraph(f"<b>Arrêté le présent bon à la somme de :</b> {self.nombre_en_lettres(total_g)}",
                                       styles['Normal']))
            elements.append(Spacer(1,20))

            sig = Table([['','Le Responsable'],['','_________________']], colWidths=[200,170])
            sig.setStyle(TableStyle([('ALIGN',(1,0),(1,-1),'CENTER'),
                                      ('FONTNAME',(1,0),(1,0),'Helvetica-Bold'), ('FONTSIZE',(1,0),(1,-1),9)]))
            elements.append(sig)
            doc.build(elements)
            messagebox.showinfo("PDF", f"Bon de Réception généré :\n{filename}")
            self.open_file(filename)
        except Exception as e:
            messagebox.showerror("Erreur", f"Génération PDF : {e}")

    def generer_ticket_80mm(self):
        data = self.get_data_bon_reception()
        if not data: return
        filename = f"BR_{self.entry_ref.get().replace('-','_')}_80mm.txt"
        try:
            s = data['societe']; r = data['reception']
            u = data['utilisateur']; details = data['details']
            W = 40
            center = lambda t: t.center(W)
            line   = lambda: "-" * W
            content = []
            content += [center("Informations Société"), s.get('nomsociete',''),
                        s.get('adressesociete',''), s.get('villesociete',''),
                        s.get('contactsociete',''), line(),
                        center(f"NIF: {s.get('nifsociete','')}"),
                        center(f"STAT: {s.get('statsociete','')}"),
                        f"N° BR: {r['reflivfrs']}", f"Date: {r['dateregistre']}",
                        f"Fournisseur: {r['fournisseur']}", f"Magasin: {r['magasin']}",
                        f"N° Facture: {r['factfrs']}",
                        f"Opérateur: {u.get('prenomuser','')} {u.get('nomuser','')}", line(),
                        "ARTICLES REÇUS", line()]
            total_g = 0
            for idx, d in enumerate(details, 1):
                m = d['qtlivre'] * d['punitcmd']; total_g += m
                content += [f"{idx}. {d['designation'][:W]}",
                            f"{self.formater_nombre(d['qtlivre'])} {d['unite']} x {self.formater_nombre(d['punitcmd'])}",
                            f"  = {self.formater_nombre(m)}", ""]
            content += [line(), center(f"TOTAL: {self.formater_nombre(total_g)} Ar"), line()]
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
            messagebox.showinfo("Ticket 80mm", f"Généré :\n{filename}")
            self.open_file(filename)
        except Exception as e:
            messagebox.showerror("Erreur", f"Génération ticket : {e}")

    def open_file(self, filename):
        try:
            if os.name == 'nt':
                os.startfile(filename)
            else:
                import subprocess, sys
                subprocess.call(['open' if sys.platform == 'darwin' else 'xdg-open', filename])
        except:
            pass


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from app_theme import init_theme
    init_theme()
    app = ctk.CTk()
    app.geometry("1280x820")
    app.title("Bon de Réception — iJeery")
    Theme.apply(app)
    page = PageBonReception(app, iduser=1)
    page.pack(fill="both", expand=True)
    app.mainloop()