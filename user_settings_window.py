# -*- coding: utf-8 -*-
import os
import customtkinter as ctk
from tkinter import messagebox, filedialog
import psycopg2

from app_theme import Colors, Fonts
from impression_pdf_utils import (
    KEY_DOSSIER_REL,
    KEY_ENREGISTRER,
    application_writable_root,
    default_pdf_export_settings,
    folder_to_relative_export_path,
    get_configured_export_directory_abs,
)
from settings_utils import (
    GLOBAL_PRINT_KEY,
    load_settings,
    save_settings,
)


class UserSettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, connect_db_callable, username_hint: str = ""):
        super().__init__(master)
        self._connect_db = connect_db_callable
        self._settings = load_settings()
        for _k, _v in default_pdf_export_settings().items():
            self._settings.setdefault(_k, _v)

        self.title("Paramètres utilisateurs")
        self.resizable(True, True)
        self.configure(fg_color=Colors.BG_PAGE)

        w, h = 760, 600
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        self.transient(master)
        self.grab_set()

        self._username_var = ctk.StringVar(value=(username_hint or "").strip())

        self._build_ui()
        self._refresh_user_info()

    def _build_ui(self):
        # Header
        hdr = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT, corner_radius=0, height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(
            hdr,
            text="⚙  Paramètres utilisateurs",
            font=Fonts.title(16),
            text_color=Colors.TEXT_ON_DARK,
        ).pack(side="left", padx=16)

        body = ctk.CTkFrame(self, fg_color=Colors.BG_PAGE, corner_radius=0)
        body.pack(fill="both", expand=True, padx=14, pady=14)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)

        # --- Card utilisateur ---
        card_user = ctk.CTkFrame(body, fg_color=Colors.BG_CARD, corner_radius=10)
        card_user.grid(row=0, column=0, sticky="nsew", padx=(0, 7), pady=(0, 10))
        card_user.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(card_user, text="Utilisateur", font=Fonts.bold(13), text_color=Colors.TEXT_PRIMARY).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 8)
        )

        ctk.CTkLabel(card_user, text="Username", font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(
            row=1, column=0, sticky="w", padx=14, pady=(0, 6)
        )
        self.entry_username = ctk.CTkEntry(
            card_user,
            textvariable=self._username_var,
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            height=34,
            corner_radius=8,
            font=Fonts.input(12),
        )
        self.entry_username.grid(row=1, column=1, sticky="ew", padx=14, pady=(0, 6))
        self.entry_username.bind("<Return>", lambda _e: self._refresh_user_info())

        self._user_info_var = ctk.StringVar(value="—")
        ctk.CTkLabel(
            card_user,
            textvariable=self._user_info_var,
            font=Fonts.body(11),
            text_color=Colors.TEXT_SECONDARY,
            justify="left",
            anchor="w",
        ).grid(row=2, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 12))

        ctk.CTkButton(
            card_user,
            text="🔄  Charger",
            font=Fonts.bold(11),
            fg_color=Colors.MIDNIGHT,
            hover_color=Colors.MIDNIGHT_LIGHT,
            height=34,
            corner_radius=8,
            command=self._refresh_user_info,
        ).grid(row=3, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 12))

        # --- Card mot de passe ---
        card_pwd = ctk.CTkFrame(body, fg_color=Colors.BG_CARD, corner_radius=10)
        card_pwd.grid(row=1, column=0, sticky="nsew", padx=(0, 7), pady=(0, 0))
        card_pwd.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(card_pwd, text="Changer le mot de passe", font=Fonts.bold(13), text_color=Colors.TEXT_PRIMARY).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 8)
        )

        def _lbl(r, t):
            ctk.CTkLabel(card_pwd, text=t, font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY).grid(
                row=r, column=0, sticky="w", padx=14, pady=(0, 6)
            )

        _lbl(1, "Ancien mot de passe")
        self.entry_old = ctk.CTkEntry(card_pwd, show="*", fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
                                      height=34, corner_radius=8, font=Fonts.input(12))
        self.entry_old.grid(row=1, column=1, sticky="ew", padx=14, pady=(0, 6))

        _lbl(2, "Nouveau mot de passe")
        self.entry_new = ctk.CTkEntry(card_pwd, show="*", fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
                                      height=34, corner_radius=8, font=Fonts.input(12))
        self.entry_new.grid(row=2, column=1, sticky="ew", padx=14, pady=(0, 6))

        _lbl(3, "Confirmer")
        self.entry_confirm = ctk.CTkEntry(card_pwd, show="*", fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
                                          height=34, corner_radius=8, font=Fonts.input(12))
        self.entry_confirm.grid(row=3, column=1, sticky="ew", padx=14, pady=(0, 10))

        ctk.CTkButton(
            card_pwd,
            text="✅  Enregistrer le mot de passe",
            font=Fonts.bold(11),
            fg_color=Colors.SUCCESS_DARK,
            hover_color=Colors.INFO_DARK,
            height=36,
            corner_radius=8,
            command=self._change_password,
        ).grid(row=4, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 12))

        # --- Card impression ---
        card_print = ctk.CTkFrame(body, fg_color=Colors.BG_CARD, corner_radius=10)
        card_print.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(7, 0), pady=(0, 0))
        card_print.grid_columnconfigure(0, weight=1)
        card_print.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(card_print, text="Options d'impression (PDF)", font=Fonts.bold(13), text_color=Colors.TEXT_PRIMARY).grid(
            row=0, column=0, sticky="w", padx=14, pady=(12, 8)
        )

        # Global impression
        self.var_global_print = ctk.BooleanVar(value=bool(self._settings.get(GLOBAL_PRINT_KEY, 1)))
        ctk.CTkSwitch(
            card_print,
            text="Impression/OUVERTURE automatique des états PDF (Oui/Non)",
            variable=self.var_global_print,
            onvalue=True,
            offvalue=False,
            font=Fonts.body(11),
            text_color=Colors.TEXT_PRIMARY,
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 10))

        # Dossier d'enregistrement des PDF / tickets (racine = dossier de l'application)
        pdf_export = ctk.CTkFrame(card_print, fg_color="transparent")
        pdf_export.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 8))
        pdf_export.grid_columnconfigure(0, weight=1)

        self.var_enregistrer_pdf = ctk.BooleanVar(
            value=bool(self._settings.get(KEY_ENREGISTRER, 1))
        )
        ctk.CTkSwitch(
            pdf_export,
            text="Enregistrer les PDF / tickets générés sur le disque",
            variable=self.var_enregistrer_pdf,
            onvalue=True,
            offvalue=False,
            font=Fonts.body(11),
            text_color=Colors.TEXT_PRIMARY,
            command=self._sync_pdf_export_ui,
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        ctk.CTkLabel(
            pdf_export,
            text="Si désactivé : fichier temporaire puis ouverture pour impression (aucune copie dans le dossier ci-dessous).",
            font=Fonts.body(10),
            text_color=Colors.TEXT_SECONDARY,
            wraplength=420,
            justify="left",
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", pady=(0, 6))

        ctk.CTkLabel(
            pdf_export,
            text="Dossier relatif (sous la racine d'exécution) — saisie ou bouton Parcourir :",
            font=Fonts.label(11),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
        ).grid(row=2, column=0, sticky="w", pady=(0, 4))

        path_row = ctk.CTkFrame(pdf_export, fg_color="transparent")
        path_row.grid(row=3, column=0, sticky="ew", pady=(0, 0))
        path_row.grid_columnconfigure(0, weight=1)

        self.entry_pdf_rel = ctk.CTkEntry(
            path_row,
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            height=32,
            corner_radius=8,
            font=Fonts.input(12),
        )
        self.entry_pdf_rel.insert(0, str(self._settings.get(KEY_DOSSIER_REL, ".") or "."))
        self.entry_pdf_rel.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.btn_browse_pdf = ctk.CTkButton(
            path_row,
            text="📁  Parcourir…",
            width=118,
            height=32,
            corner_radius=8,
            font=Fonts.bold(11),
            fg_color=Colors.MIDNIGHT,
            hover_color=Colors.MIDNIGHT_LIGHT,
            text_color=Colors.TEXT_ON_DARK,
            command=self._browse_pdf_export_folder,
        )
        self.btn_browse_pdf.grid(row=0, column=1, sticky="e")

        # Zone scrollable pour les switches (quand ça dépasse)
        scroll = ctk.CTkScrollableFrame(card_print, fg_color="transparent", corner_radius=0)
        scroll.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 0))
        scroll.grid_columnconfigure(0, weight=1)

        # Clés existantes (granularité)
        self._print_keys_a5 = [
            ("Vente - Confirmation", "Vente_ImpressionConfirmation", 1),
            ("Vente - Facture A5 (PDF)", "Vente_ImpressionA5", 1),
            ("Avoir - Confirmation", "Avoir_ImpressionConfirmation", 1),
            ("Avoir - A5 (PDF)", "Avoir_ImpressionA5", 1),
            ("Stock - Bon d'Entrée A5 (PDF) - Ouverture auto", "Entree_OpenA5", 1),
            ("Stock - Bon de Sortie A5 (PDF) - Ouverture auto", "Sortie_OpenA5", 1),
            ("Stock - Consommation interne A5 (PDF) - Ouverture auto", "Consommation_OpenA5", 1),
            ("Stock - Changement articles A5 (PDF) - Ouverture auto", "Changement_OpenA5", 1),
            ("Crédit - Acceptation A5 (PDF) - Ouverture auto", "Credit_Acceptation_OpenA5", 1),
            ("Crédit - État temporaire A5 (PDF) - Ouverture auto", "Credit_Temporaire_OpenA5", 0),
            ("Client créance - Ouverture A5 (PDF)", "Client_Creance_OpenA5", 0),
            ("Fournisseur Paiement dette - Ouverture A5 (PDF)", "Fournisseur_PmtDette_OpenA5", 0),
            ("Fournisseur dette - Ouverture A5 (PDF) (validation)", "Fournisseur_Dette_OpenA5", 0),
            ("Mouvements - Ouverture PDF A5", "Mouvements_ImpressionAutoOpen", 1),
        ]
        self._print_keys_ticket80 = [
            ("Vente - Ticket 80mm (texte) - Ouverture auto", "Vente_ImpressionTicket", 0),
            ("Avoir - Ticket 80mm", "Avoir_ImpressionTicket", 0),
            ("Client à payer - Ticket 80mm", "ClientAPayer_ImpressionTicket", 1),
            ("Facture - Paiement (Ticket 80mm PDF) - Ouverture auto", "Facture_Paiement_OpenTicket80Pdf", 1),
            ("Client Paiement à crédit - Ouverture Ticket 80mm (PDF)", "Client_PmtCredit_OpenTicket80", 0),
            ("Client Paiement crédit - Impression X80", "Client_PmtCredit_PrintX80", 0),
            ("Client créance - Ouverture Ticket 80mm (PDF)", "Client_Creance_OpenTicketPdf", 0),
            ("Fournisseur Paiement dette - Ouverture Ticket 80mm (PDF)", "Fournisseur_PmtDette_OpenTicket80", 0),
            ("Fournisseur dette - Ouverture Ticket 80mm (PDF)", "Fournisseur_Dette_OpenTicketPdf", 0),
        ]
        self._vars = {}

        def _section(title: str, row_idx: int) -> int:
            ctk.CTkLabel(
                scroll,
                text=title,
                font=Fonts.bold(12),
                text_color=Colors.TEXT_PRIMARY,
                anchor="w",
            ).grid(row=row_idx, column=0, sticky="ew", padx=8, pady=(6, 8))
            return row_idx + 1

        row = 0
        row = _section("Impressions A5 (PDF)", row)
        for label, key, default in self._print_keys_a5:
            v = ctk.BooleanVar(value=bool(self._settings.get(key, default)))
            self._vars[key] = v
            ctk.CTkSwitch(
                scroll,
                text=label,
                variable=v,
                onvalue=True,
                offvalue=False,
                font=Fonts.body(11),
                text_color=Colors.TEXT_SECONDARY,
            ).grid(row=row, column=0, sticky="w", padx=8, pady=(0, 8))
            row += 1

        row = _section("Tickets 80mm (PDF/Texte)", row)
        for label, key, default in self._print_keys_ticket80:
            v = ctk.BooleanVar(value=bool(self._settings.get(key, default)))
            self._vars[key] = v
            ctk.CTkSwitch(
                scroll,
                text=label,
                variable=v,
                onvalue=True,
                offvalue=False,
                font=Fonts.body(11),
                text_color=Colors.TEXT_SECONDARY,
            ).grid(row=row, column=0, sticky="w", padx=8, pady=(0, 8))
            row += 1

        ctk.CTkButton(
            card_print,
            text="💾  Enregistrer les options",
            font=Fonts.bold(11),
            fg_color=Colors.MIDNIGHT,
            hover_color=Colors.MIDNIGHT_LIGHT,
            height=36,
            corner_radius=8,
            command=self._save_print_settings,
        ).grid(row=4, column=0, sticky="ew", padx=14, pady=(10, 12))

        # Footer
        footer = ctk.CTkFrame(self, fg_color=Colors.BG_PAGE, corner_radius=0)
        footer.pack(fill="x", padx=14, pady=(0, 12))
        ctk.CTkButton(
            footer,
            text="Fermer",
            font=Fonts.bold(11),
            fg_color=Colors.DANGER,
            hover_color=Colors.DANGER_DARK,
            height=34,
            corner_radius=8,
            width=140,
            command=self.destroy,
        ).pack(side="right")

        self._sync_pdf_export_ui()

    def _browse_pdf_export_folder(self):
        """Ouvre l'explorateur pour choisir un dossier d'export (converti en chemin relatif)."""
        if not self.var_enregistrer_pdf.get():
            return
        try:
            cur = (self.entry_pdf_rel.get() or ".").strip()
            draft = {KEY_DOSSIER_REL: cur, KEY_ENREGISTRER: 1}
            start = get_configured_export_directory_abs(draft)
            if not os.path.isdir(start):
                start = application_writable_root()
        except Exception:
            start = application_writable_root()

        chosen = filedialog.askdirectory(
            parent=self,
            title="Choisir le dossier d'enregistrement des PDF / tickets",
            initialdir=start,
        )
        if not chosen:
            return
        rel = folder_to_relative_export_path(chosen)
        if rel is None:
            root = application_writable_root()
            messagebox.showerror(
                "Dossier invalide",
                "Le dossier choisi doit se trouver sous la racine d'exécution de l'application :\n\n"
                f"{root}\n\n"
                "Choisissez un sous-dossier de cet emplacement (ou ce dossier lui-même).",
                parent=self,
            )
            return
        self.entry_pdf_rel.configure(state="normal")
        self.entry_pdf_rel.delete(0, "end")
        self.entry_pdf_rel.insert(0, rel)

    def _sync_pdf_export_ui(self):
        """Désactive le dossier relatif si l'enregistrement sur disque est désactivé."""
        save = self.var_enregistrer_pdf.get()
        st = "normal" if save else "disabled"
        try:
            self.entry_pdf_rel.configure(state=st)
            self.btn_browse_pdf.configure(state=st)
        except Exception:
            pass

    def _refresh_user_info(self):
        username = (self._username_var.get() or "").strip()
        if not username:
            self._user_info_var.set("Veuillez saisir un username.")
            return

        conn = self._connect_db()
        if not conn:
            self._user_info_var.set("Impossible de se connecter à la base de données.")
            return

        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT iduser, nomuser, prenomuser, adresseuser, contactuser, username, idfonction, active
                FROM tb_users
                WHERE username = %s AND COALESCE(deleted, 0) = 0
                LIMIT 1
                """,
                (username,),
            )
            row = cur.fetchone()
            if not row:
                self._user_info_var.set("Utilisateur introuvable (ou supprimé).")
                return

            iduser, nom, prenom, adresse, contact, uname, idfonction, active = row
            actif_txt = "Oui" if int(active or 0) == 1 else "Non"
            self._user_info_var.set(
                f"ID: {iduser}\n"
                f"Nom: {nom or ''} {prenom or ''}\n"
                f"Adresse: {adresse or ''}\n"
                f"Contact: {contact or ''}\n"
                f"Fonction ID: {idfonction}\n"
                f"Actif: {actif_txt}"
            )
        except Exception as e:
            self._user_info_var.set(f"Erreur chargement utilisateur: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _change_password(self):
        username = (self._username_var.get() or "").strip()
        old_pwd = (self.entry_old.get() or "").strip()
        new_pwd = (self.entry_new.get() or "").strip()
        confirm = (self.entry_confirm.get() or "").strip()

        if not username:
            messagebox.showwarning("Attention", "Veuillez saisir un username.")
            return
        if not old_pwd or not new_pwd:
            messagebox.showwarning("Attention", "Veuillez remplir l'ancien et le nouveau mot de passe.")
            return
        if new_pwd != confirm:
            messagebox.showwarning("Attention", "La confirmation ne correspond pas.")
            return

        conn = self._connect_db()
        if not conn:
            messagebox.showerror("Erreur", "Connexion DB impossible.")
            return

        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT iduser
                FROM tb_users
                WHERE username = %s AND password = %s AND COALESCE(deleted, 0) = 0
                LIMIT 1
                """,
                (username, old_pwd),
            )
            row = cur.fetchone()
            if not row:
                messagebox.showerror("Erreur", "Ancien mot de passe incorrect (ou utilisateur introuvable).")
                return

            cur.execute(
                """
                UPDATE tb_users
                SET password = %s
                WHERE username = %s AND COALESCE(deleted, 0) = 0
                """,
                (new_pwd, username),
            )
            conn.commit()
            self.entry_old.delete(0, "end")
            self.entry_new.delete(0, "end")
            self.entry_confirm.delete(0, "end")
            messagebox.showinfo("Succès", "Mot de passe mis à jour.")
        except psycopg2.Error as e:
            try:
                conn.rollback()
            except Exception:
                pass
            messagebox.showerror("Erreur DB", str(e))
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            messagebox.showerror("Erreur", str(e))
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _save_print_settings(self):
        self._settings = load_settings()
        self._settings[GLOBAL_PRINT_KEY] = 1 if self.var_global_print.get() else 0
        self._settings[KEY_ENREGISTRER] = 1 if self.var_enregistrer_pdf.get() else 0
        self._settings[KEY_DOSSIER_REL] = (self.entry_pdf_rel.get() or ".").strip()
        for key, var in self._vars.items():
            self._settings[key] = 1 if var.get() else 0

        ok = save_settings(self._settings)
        if ok:
            messagebox.showinfo("Succès", "Options enregistrées dans settings.json.")
        else:
            messagebox.showerror("Erreur", "Impossible d'enregistrer settings.json.")

