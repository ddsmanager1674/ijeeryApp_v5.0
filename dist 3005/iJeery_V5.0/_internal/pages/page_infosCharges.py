# -*- coding: utf-8 -*-
"""
Page Infos Charges — iJeery
Texte aide-mémoire stocké dans tb_autre_infos (intitule='infos_charge').
"""

import customtkinter as ctk
from tkinter import messagebox
import psycopg2
import json
from resource_utils import get_config_path
from app_theme import Colors, Fonts, styled
from log_utils import AppLogger


class PageInfosCharges(ctk.CTkFrame):
    def __init__(self, parent, iduser, **kwargs):
        super().__init__(parent, fg_color=Colors.BG_PAGE, **kwargs)
        self.iduser = iduser
        self.session_data = getattr(parent, "session_data", None) or {"user_id": self.iduser}
        self._logger = AppLogger(session_data=self.session_data, fallback_user_id=self.iduser)

        self._infos_charge_value = ""

        self._build_ui()
        self._load_infos_charge()

    # ─────────────────────────────────────────────────────────────────────────
    # DB
    # ─────────────────────────────────────────────────────────────────────────
    def connect_db(self):

        try:

            from pages.db_helper import connect_page_db

            shared = (

                getattr(self, '_db_conn_shared', None)

                or getattr(self, '_db_conn_initial', None)

            )

            return connect_page_db(shared)

        except FileNotFoundError:
            messagebox.showerror("Erreur", "Fichier 'config.json' non trouvé.")
        except KeyError:
            messagebox.showerror("Erreur", "Clés DB manquantes dans 'config.json'.")
        except psycopg2.Error as e:
            messagebox.showerror("Connexion", f"Erreur PostgreSQL : {e}")
        except UnicodeDecodeError as e:
            messagebox.showerror("Encodage", f"Problème d'encodage : {e}")
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # UI
    # ─────────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        body = ctk.CTkFrame(self, fg_color=Colors.BG_PAGE)
        body.pack(fill="both", expand=True, padx=8, pady=6)

        card = ctk.CTkFrame(body, fg_color=Colors.BG_CARD,
                            corner_radius=8, border_width=1, border_color=Colors.BORDER)
        card.pack(fill="x", pady=(0, 4))

        tools = ctk.CTkFrame(card, fg_color="transparent")
        tools.pack(fill="x", padx=10, pady=(8, 6))

        ctk.CTkLabel(
            tools, text="🧾 Aide-mémoire",
            font=Fonts.bold(11), text_color=Colors.MIDNIGHT
        ).pack(side="left")

        self.btn_edit = styled.button_secondary(
            tools, text="Édition", width=90, height=26,
            command=self._edit_infos_charge
        )
        self.btn_edit.pack(side="right", padx=(6, 0))

        self.btn_save = styled.button_success(
            tools, text="Enregistrer", width=110, height=26,
            command=self._save_infos_charge
        )
        self.btn_save.pack(side="right")

        self.txt_infos_charge = ctk.CTkTextbox(
            card, height=140, fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER, font=Fonts.body(11),
            text_color=Colors.TEXT_PRIMARY
        )
        self.txt_infos_charge.pack(fill="x", padx=10, pady=(0, 10))
        self.txt_infos_charge.configure(state="disabled")

    # ─────────────────────────────────────────────────────────────────────────
    # Actions
    # ─────────────────────────────────────────────────────────────────────────
    def _load_infos_charge(self):
        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute("SELECT valeur FROM tb_autre_infos WHERE intitule=%s", ("infos_charge",))
            row = cur.fetchone()
            self._infos_charge_value = row[0] if row and row[0] else ""
        except Exception as e:
            messagebox.showerror("Erreur", f"Chargement infos charge : {e}")
            self._infos_charge_value = ""
        finally:
            cur.close()
            conn.close()

        self.txt_infos_charge.configure(state="normal")
        self.txt_infos_charge.delete("1.0", "end")
        if self._infos_charge_value:
            self.txt_infos_charge.insert("1.0", self._infos_charge_value)
        self.txt_infos_charge.configure(state="disabled")

    def _edit_infos_charge(self):
        self.txt_infos_charge.configure(state="normal")
        self.txt_infos_charge.focus_set()

    def _save_infos_charge(self):
        valeur = self.txt_infos_charge.get("1.0", "end").strip()
        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE tb_autre_infos SET valeur=%s WHERE intitule=%s",
                (valeur, "infos_charge")
            )
            conn.commit()
            try:
                self._logger.log(
                    action="Modification infos charges",
                    element="infos_charge",
                    details="Mise à jour texte infos charges",
                    value=f"{len(valeur)} caractères",
                )
            except Exception:
                pass
            self._infos_charge_value = valeur
            self.txt_infos_charge.configure(state="disabled")
            messagebox.showinfo("Succès", "Infos charges enregistrées.")
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur", f"Enregistrement infos charge : {e}")
        finally:
            cur.close()
            conn.close()

