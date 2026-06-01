import customtkinter as ctk
from tkinter import messagebox
import psycopg2
import json
from typing import Any

from resource_utils import get_config_path
from app_theme import Colors, Fonts, styled
from log_utils import AppLogger


class PageParametres(ctk.CTkFrame):
    """
    Page « Paramètres ».

    Pour le moment :
      - Onglet « Infos Entreprise » : CRUD sur tb_infosociete
    """

    def __init__(self, master):
        super().__init__(master, fg_color=Colors.BG_PAGE)

        self.conn = self._connect_db()
        self.cursor = self.conn.cursor() if self.conn else None
        self.session_data = getattr(master, "session_data", None) or {}
        self._logger = AppLogger(conn=self.conn, session_data=self.session_data) if self.conn else None

        self._infos_id: int | None = None
        self._widgets: dict[str, Any] = {}

        self._build_ui()
        self._load_infos_societe()

    def _connect_db(self):
        try:
            config_path = get_config_path("config.json")
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            db_config = config["database"]

            from pages.db_helper import connect_page_db
            return connect_page_db()
        except Exception as err:
            messagebox.showerror("Erreur de connexion", f"Connexion PostgreSQL impossible : {err}")
            return None

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color=Colors.MIDNIGHT, corner_radius=0, height=46)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        inner = styled.frame(header)
        inner.pack(side="left", padx=14, pady=6)

        ctk.CTkLabel(
            inner,
            text="⚙️",
            font=Fonts.heading(16),
            text_color=Colors.TEXT_ON_DARK,
        ).pack(side="left", padx=(0, 10))

        titles = styled.frame(inner)
        titles.pack(side="left")
        ctk.CTkLabel(
            titles,
            text="Paramètres",
            font=Fonts.bold(13),
            text_color=Colors.TEXT_ON_DARK,
        ).pack(anchor="w")
        ctk.CTkLabel(
            titles,
            text="Gestion des informations de l'entreprise",
            font=Fonts.small(9),
            text_color=Colors.TEXT_ON_DARK_DIM,
        ).pack(anchor="w")

        tabs_card = styled.card(self)
        tabs_card.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        tabs_card.grid_propagate(False)

        tabs_card.grid_rowconfigure(0, weight=1)
        tabs_card.grid_columnconfigure(0, weight=1)

        self.tabs = ctk.CTkTabview(tabs_card)
        self.tabs.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        tab_infos = self.tabs.add("Infos Entreprise")
        tab_infos.grid_columnconfigure(1, weight=1)

        form = ctk.CTkFrame(tab_infos, fg_color=Colors.BG_CARD, corner_radius=12, border_width=1, border_color=Colors.BORDER)
        form.pack(fill="both", expand=True, padx=12, pady=10)
        form.grid_columnconfigure(1, weight=1)

        # Champs tb_infosociete
        fields = [
            ("nomsociete", "Nom société"),
            ("adressesociete", "Adresse"),
            ("villesociete", "Ville"),
            ("contactsociete", "Contact"),
            ("nifsociete", "NIF"),
            ("statsociete", "STAT"),
            ("cifsociete", "CIF"),
            ("ambleme", "Amblème"),
            ("autre", "Autre"),
        ]

        row = 0
        for key, label in fields:
            styled.label_muted(form, text=f"{label} :").grid(
                row=row, column=0, sticky="w", padx=(14, 8), pady=8
            )
            self._widgets[key] = styled.entry(form, height=32)
            self._widgets[key].grid(row=row, column=1, sticky="ew", padx=(0, 14), pady=8)
            row += 1

        self._lbl_id = ctk.CTkLabel(
            tab_infos,
            text="ID infos société : (non chargé)",
            font=Fonts.small(11),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
        )
        self._lbl_id.pack(fill="x", padx=18, pady=(0, 2))

        btn_row = ctk.CTkFrame(tab_infos, fg_color="transparent")
        btn_row.pack(fill="x", padx=18, pady=(6, 10))
        btn_row.grid_columnconfigure(0, weight=1)

        styled.button_success(btn_row, text="Enregistrer", icon="💾", width=155, command=self.enregistrer).pack(
            side="left", padx=(0, 8)
        )
        styled.button_primary(btn_row, text="Modifier", icon="✏️", width=140, command=self.modifier).pack(
            side="left", padx=(0, 8)
        )
        styled.button_danger(btn_row, text="Supprimer", icon="🗑", width=150, command=self.supprimer).pack(
            side="left", padx=(0, 8)
        )
        styled.button_secondary(btn_row, text="Vider", icon="↺", width=120, command=self.vider).pack(
            side="right"
        )

    # ------------------------------------------------------------------
    # Données
    # ------------------------------------------------------------------
    def _get_form_values(self) -> dict[str, str]:
        values: dict[str, str] = {}
        for key in self._widgets.keys():
            raw = self._widgets[key].get().strip()
            values[key] = raw
        return values

    def _fetch_infos_societe(self) -> dict[str, Any] | None:
        if not self.cursor:
            return None
        self.cursor.execute(
            """
            SELECT id, nomsociete, adressesociete, villesociete, contactsociete,
                   nifsociete, statsociete, cifsociete, ambleme, autre
            FROM tb_infosociete
            LIMIT 1
            """
        )
        row = self.cursor.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "nomsociete": row[1] or "",
            "adressesociete": row[2] or "",
            "villesociete": row[3] or "",
            "contactsociete": row[4] or "",
            "nifsociete": row[5] or "",
            "statsociete": row[6] or "",
            "cifsociete": row[7] or "",
            "ambleme": row[8] or "",
            "autre": row[9] or "",
        }

    def _load_infos_societe(self):
        infos = self._fetch_infos_societe()
        if not infos:
            self._infos_id = None
            self._lbl_id.configure(text="ID infos société : (aucun enregistrement)")
            return

        self._infos_id = int(infos["id"])
        self._lbl_id.configure(text=f"ID infos société : {self._infos_id}")

        for key in self._widgets.keys():
            self._widgets[key].delete(0, "end")
            self._widgets[key].insert(0, str(infos.get(key, "")))

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def enregistrer(self):
        if not self.cursor or not self.conn:
            messagebox.showerror("Erreur", "Connexion à la base de données non établie.")
            return

        values = self._get_form_values()
        try:
            existing = self._fetch_infos_societe()
            if existing:
                self.cursor.execute(
                    """
                    UPDATE tb_infosociete
                    SET nomsociete=%s,
                        adressesociete=%s,
                        villesociete=%s,
                        contactsociete=%s,
                        nifsociete=%s,
                        statsociete=%s,
                        cifsociete=%s,
                        ambleme=%s,
                        autre=%s
                    WHERE id=%s
                    """,
                    (
                        values["nomsociete"],
                        values["adressesociete"],
                        values["villesociete"],
                        values["contactsociete"],
                        values["nifsociete"],
                        values["statsociete"],
                        values["cifsociete"],
                        values["ambleme"],
                        values["autre"],
                        existing["id"],
                    ),
                )
            else:
                self.cursor.execute(
                    """
                    INSERT INTO tb_infosociete
                        (nomsociete, adressesociete, villesociete, contactsociete,
                         nifsociete, statsociete, cifsociete, ambleme, autre)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        values["nomsociete"],
                        values["adressesociete"],
                        values["villesociete"],
                        values["contactsociete"],
                        values["nifsociete"],
                        values["statsociete"],
                        values["cifsociete"],
                        values["ambleme"],
                        values["autre"],
                    ),
                )

            self.conn.commit()
            self._load_infos_societe()

            if self._logger:
                self._logger.log(
                    action="CRUD Infos Entreprise",
                    element="tb_infosociete",
                    details=f"Enregistrement effectué (id={self._infos_id})",
                    value="ok",
                )

            messagebox.showinfo("Succès", "Infos entreprise enregistrées.")
        except Exception as err:
            if self.conn:
                self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement : {err}")

    def modifier(self):
        if not self.cursor or not self.conn:
            messagebox.showerror("Erreur", "Connexion à la base de données non établie.")
            return
        if not self._fetch_infos_societe():
            messagebox.showwarning("Attention", "Aucun enregistrement dans tb_infosociete à modifier.")
            return
        self.enregistrer()

    def supprimer(self):
        if not self.cursor or not self.conn:
            messagebox.showerror("Erreur", "Connexion à la base de données non établie.")
            return

        infos = self._fetch_infos_societe()
        if not infos:
            messagebox.showwarning("Attention", "Aucun enregistrement à supprimer.")
            return

        ok = messagebox.askyesno(
            "Confirmation",
            "Êtes-vous sûr de vouloir supprimer les infos entreprise ?\n\n"
            "Cela peut impacter la génération des PDF."
        )
        if not ok:
            return

        try:
            self.cursor.execute("DELETE FROM tb_infosociete WHERE id=%s", (infos["id"],))
            self.conn.commit()
            self._infos_id = None
            self.vider()

            if self._logger:
                self._logger.log(
                    action="CRUD Infos Entreprise",
                    element="tb_infosociete",
                    details=f"Suppression effectuée (id={infos['id']})",
                    value="ok",
                )

            messagebox.showinfo("Succès", "Infos entreprise supprimées.")
        except Exception as err:
            if self.conn:
                self.conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de la suppression : {err}")

    def vider(self):
        for key in self._widgets.keys():
            self._widgets[key].delete(0, "end")
        self._infos_id = None
        self._lbl_id.configure(text="ID infos société : (non chargé)")

    def __del__(self):
        try:
            if self.cursor:
                self.cursor.close()
        except Exception:
            pass
        try:
            if self.conn:
                self.conn.close()
        except Exception:
            pass

