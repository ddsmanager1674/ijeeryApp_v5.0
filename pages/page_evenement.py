import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime
import json
from resource_utils import get_config_path
from app_theme import Colors, Fonts
from log_utils import AppLogger


class PageEvenement(ctk.CTkFrame):
    """Historique des actions utilisateur basé sur tb_log_evenements."""

    def __init__(self, master, db_conn=None, session_data=None, db_config=None, **kwargs):
        super().__init__(master, fg_color=Colors.BG_PAGE, **kwargs)
        self.db_conn = db_conn
        self.session_data = session_data
        self.db_config = db_config
        self.conn = self.connect_db()
        self.sort_column = "datetime"
        self.sort_desc = True
        self._logger = AppLogger(conn=self.conn, session_data=self.session_data or {})
        self._build_ui()
        self._apply_table_style()
        self._load_users_filter()
        self.refresh_data()

    def connect_db(self):
        try:
            with open(get_config_path("config.json"), "r", encoding="utf-8") as f:
                config = json.load(f)
            db_config = config["database"]
            return psycopg2.connect(
                host=db_config["host"],
                user=db_config["user"],
                password=db_config["password"],
                database=db_config["database"],
                port=db_config["port"],
            )
        except Exception as err:
            messagebox.showerror("Erreur de connexion", f"Connexion PostgreSQL impossible : {err}")
            return None

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 2))
        for col in range(10):
            header.grid_columnconfigure(col, weight=1)
        header.grid_columnconfigure(3, weight=2)

        ctk.CTkLabel(
            header,
            text="Historique des actions utilisateur",
            font=Fonts.heading(16),
            text_color=Colors.TEXT_PRIMARY,
        ).grid(row=0, column=0, columnspan=10, sticky="w", padx=10, pady=(8, 4))

        label_style = dict(font=Fonts.label(11), text_color=Colors.TEXT_SECONDARY, anchor="w")
        entry_style = dict(
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            height=32,
            corner_radius=6,
            font=Fonts.input(11),
        )

        ctk.CTkLabel(header, text="Recherche globale", **label_style).grid(row=1, column=0, padx=(10, 4), sticky="w")
        self.search_entry = ctk.CTkEntry(header, placeholder_text="Date, utilisateur, description...", **entry_style)
        self.search_entry.grid(row=2, column=0, columnspan=4, padx=(10, 4), pady=(0, 8), sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda _e: self.refresh_data())

        ctk.CTkLabel(header, text="Utilisateur", **label_style).grid(row=1, column=4, padx=4, sticky="w")
        self.user_filter = ctk.CTkComboBox(
            header,
            values=["Tous"],
            state="readonly",
            button_color=Colors.MIDNIGHT,
            dropdown_fg_color=Colors.BG_CARD,
            **entry_style,
        )
        self.user_filter.grid(row=2, column=4, padx=4, pady=(0, 8), sticky="ew")
        self.user_filter.set("Tous")
        self.user_filter.configure(command=lambda _v: self.refresh_data())

        ctk.CTkLabel(header, text="Date de (YYYY-MM-DD)", **label_style).grid(row=1, column=5, padx=4, sticky="w")
        self.date_from_entry = ctk.CTkEntry(header, placeholder_text="2026-01-01", **entry_style)
        self.date_from_entry.grid(row=2, column=5, padx=4, pady=(0, 8), sticky="ew")
        self.date_from_entry.bind("<KeyRelease>", lambda _e: self.refresh_data())

        ctk.CTkLabel(header, text="Date à (YYYY-MM-DD)", **label_style).grid(row=1, column=6, padx=4, sticky="w")
        self.date_to_entry = ctk.CTkEntry(header, placeholder_text="2026-12-31", **entry_style)
        self.date_to_entry.grid(row=2, column=6, padx=4, pady=(0, 8), sticky="ew")
        self.date_to_entry.bind("<KeyRelease>", lambda _e: self.refresh_data())

        ctk.CTkButton(
            header,
            text="Actualiser",
            font=Fonts.bold(11),
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            corner_radius=6,
            height=32,
            command=self._refresh_with_log,
        ).grid(row=2, column=7, padx=4, pady=(0, 8), sticky="ew")

        ctk.CTkButton(
            header,
            text="Réinitialiser",
            font=Fonts.bold(11),
            fg_color=Colors.TEXT_MUTED,
            hover_color=Colors.TEXT_SECONDARY,
            corner_radius=6,
            height=32,
            command=self._reset_with_log,
        ).grid(row=2, column=8, padx=4, pady=(0, 8), sticky="ew")

        table_wrap = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        table_wrap.grid(row=1, column=0, sticky="nsew")
        table_wrap.grid_columnconfigure(0, weight=1)
        table_wrap.grid_rowconfigure(0, weight=1)

        columns = ("datetime", "user", "description")
        self.tree = ttk.Treeview(table_wrap, columns=columns, show="headings", style="Evenements.Treeview")
        self.tree.heading("datetime", text="Date & Heure", command=lambda: self._toggle_sort("datetime"))
        self.tree.heading("user", text="Utilisateur", command=lambda: self._toggle_sort("user"))
        self.tree.heading("description", text="Description", command=lambda: self._toggle_sort("description"))
        self.tree.column("datetime", width=180, anchor="center")
        self.tree.column("user", width=180, anchor="w")
        self.tree.column("description", width=700, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)
        self.tree.tag_configure("row_even", background=Colors.BG_CARD)
        self.tree.tag_configure("row_odd", background=Colors.BG_ROW_ALT)

        y_scroll = ctk.CTkScrollbar(table_wrap, command=self.tree.yview)
        y_scroll.grid(row=0, column=1, sticky="ns", padx=(0, 8), pady=8)
        self.tree.configure(yscrollcommand=y_scroll.set)

        footer = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0)
        footer.grid(row=2, column=0, sticky="ew", padx=0, pady=(2, 0))
        footer.grid_columnconfigure(0, weight=1)
        self.result_count_label = ctk.CTkLabel(
            footer,
            text="0 résultat(s)",
            font=Fonts.small(11),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
        )
        self.result_count_label.grid(row=0, column=0, sticky="w", padx=10, pady=8)

    def _apply_table_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Evenements.Treeview",
            rowheight=24,
            font=("Segoe UI", 9),
            background=Colors.BG_CARD,
            foreground=Colors.TEXT_PRIMARY,
            fieldbackground=Colors.BG_CARD,
            borderwidth=0,
        )
        style.configure(
            "Evenements.Treeview.Heading",
            background=Colors.BG_HEADER,
            foreground=Colors.TEXT_ON_DARK,
            font=("Segoe UI", 9, "bold"),
            relief="flat",
        )
        style.map(
            "Evenements.Treeview",
            background=[("selected", Colors.PRIMARY)],
            foreground=[("selected", Colors.TEXT_ON_DARK)],
        )

    def _load_users_filter(self):
        if not self.conn:
            return
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT DISTINCT COALESCE("user", '')
                    FROM tb_log_evenements
                    ORDER BY COALESCE("user", '') ASC
                    """
                )
                users = [row[0] for row in cursor.fetchall() if row[0]]
            self.user_filter.configure(values=["Tous"] + users)
            self.user_filter.set("Tous")
        except Exception as err:
            messagebox.showerror("Erreur", f"Chargement des utilisateurs impossible : {err}")

    def _toggle_sort(self, column):
        if self.sort_column == column:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_column = column
            self.sort_desc = True
        self.refresh_data()

    def _refresh_row_colors(self):
        for idx, item in enumerate(self.tree.get_children()):
            self.tree.item(item, tags=("row_even" if idx % 2 == 0 else "row_odd",))

    def reset_filters(self):
        self.search_entry.delete(0, "end")
        self.user_filter.set("Tous")
        self.date_from_entry.delete(0, "end")
        self.date_to_entry.delete(0, "end")
        self.sort_column = "datetime"
        self.sort_desc = True
        self.refresh_data()

    def _refresh_with_log(self):
        try:
            self._logger.log(
                action="Consultation événements",
                element="Événements",
                details="Actualiser historique des actions utilisateur",
                value="refresh",
            )
        except Exception:
            pass
        self.refresh_data()

    def _reset_with_log(self):
        try:
            self._logger.log(
                action="Consultation événements",
                element="Événements",
                details="Réinitialiser filtres historique",
                value="reset_filters",
            )
        except Exception:
            pass
        self.reset_filters()

    def _build_where_clause(self):
        where_parts = []
        params = []

        search_text = self.search_entry.get().strip()
        if search_text:
            where_parts.append(
                """(
                    COALESCE(description, '') ILIKE %s
                    OR COALESCE("user", '') ILIKE %s
                    OR TO_CHAR(datetime, 'YYYY-MM-DD HH24:MI:SS') ILIKE %s
                )"""
            )
            like_value = f"%{search_text}%"
            params.extend([like_value, like_value, like_value])

        selected_user = self.user_filter.get().strip()
        if selected_user and selected_user != "Tous":
            where_parts.append('COALESCE("user", \'\') = %s')
            params.append(selected_user)

        date_from = self.date_from_entry.get().strip()
        if date_from:
            try:
                datetime.strptime(date_from, "%Y-%m-%d")
                where_parts.append("datetime >= %s::date")
                params.append(date_from)
            except ValueError:
                pass

        date_to = self.date_to_entry.get().strip()
        if date_to:
            try:
                datetime.strptime(date_to, "%Y-%m-%d")
                where_parts.append("datetime < (%s::date + INTERVAL '1 day')")
                params.append(date_to)
            except ValueError:
                pass

        if where_parts:
            return f"WHERE {' AND '.join(where_parts)}", params
        return "", params

    def refresh_data(self):
        if not self.conn:
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        order_map = {
            "datetime": "datetime",
            "user": 'COALESCE("user", \'\')',
            "description": "description",
        }
        order_by = order_map.get(self.sort_column, "datetime")
        order_dir = "DESC" if self.sort_desc else "ASC"
        where_clause, params = self._build_where_clause()

        query = f"""
            SELECT datetime, COALESCE("user", ''), description
            FROM tb_log_evenements
            {where_clause}
            ORDER BY {order_by} {order_dir}, id_log DESC
        """

        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()

            for row in rows:
                dt = row[0].strftime("%Y-%m-%d %H:%M:%S") if row[0] else ""
                self.tree.insert("", "end", values=(dt, row[1], row[2] or ""))

            self._refresh_row_colors()
            self.result_count_label.configure(text=f"{len(rows)} résultat(s)")
        except Exception as err:
            messagebox.showerror("Erreur", f"Chargement des événements impossible : {err}")

    def __del__(self):
        if hasattr(self, "conn") and self.conn:
            try:
                self.conn.close()
            except Exception:
                pass


if __name__ == "__main__":
    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("Historique des événements")
    app.geometry("1200x700")

    page = PageEvenement(app)
    page.pack(fill="both", expand=True)
    app.mainloop()