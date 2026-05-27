# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║               iJeery — login_window.py  (refonte v3 — mockup)              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  STYLE                                                                      ║
║  • Fenêtre sans bordure Windows (overrideredirect)                          ║
║  • Bouton ✕ custom dans le coin supérieur droit                             ║
║  • Fond blanc pur, champs "underline" (ligne du bas uniquement)             ║
║  • Icônes SVG canvas gauche des champs (👤 / 🔒)                           ║
║  • Toggle œil pour montrer/masquer le mot de passe                         ║
║  • Bouton "Se connecter" bleu plein, coins arrondis                         ║
║  • Séparateur  ─────  &  ─────  entre sections                              ║
║  • Toast succès bas d'écran + effet secousse sur erreur                     ║
║                                                                              ║
║  LOGIQUE MÉTIER — 100 % INTACTE                                             ║
║  • Remember Me (base64 remember.json)                                       ║
║  • connect_db / get_authorized_menus / save_user_session                    ║
║  • login() / launch_main_app_safely / _import_and_run                      ║
║  • ConfigDataBase                                                           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import customtkinter as ctk
from tkinter import messagebox
import tkinter as tk
import psycopg2
from PIL import Image
import os
import json
import sys
import time
import threading
import subprocess
import base64

from configDataBase import ConfigDataBase
from user_settings_window import UserSettingsWindow
from resource_utils import (get_resource_path, get_config_path,
                             get_session_path, safe_file_read)
from log_utils import AppLogger

try:
    from app_icon_utils import init_app_icon
    init_app_icon()
except Exception:
    pass

# ── Thème iJeery ──────────────────────────────────────────────────────────────
try:
    from app_theme import Colors, Fonts, Theme, init_theme
    _T = True
except ImportError:
    _T = False


class _C:
    """Palette locale — utilisée si app_theme absent."""
    BG_PAGE       = "#FFFFFF"
    BG_CARD       = "#FFFFFF"
    BG_HEADER     = "#2C3E50"
    BG_INPUT      = "transparent"
    PRIMARY       = "#1A4FA0"    # bleu mockup
    PRIMARY_HOVER = "#1540882"
    SUCCESS       = "#2ECC71"
    SUCCESS_DARK  = "#27AE60"
    DANGER        = "#E74C3C"
    DANGER_DARK   = "#C0392B"
    TEXT_PRIMARY  = "#1A1A2E"
    TEXT_MUTED    = "#95A5A6"
    BORDER        = "#D5D8DC"
    BORDER_FOCUS  = "#1A4FA0"
    DIVIDER       = "#E8EAED"
    SILVER        = "#BDC3C7"
    CLOUDS        = "#ECF0F1"
    TEXT_MUTED2   = "#7F8C8D"


C = Colors if _T else _C

# Surcharge locale pour l'UI login (indépendant du thème ERP)
_FONT_FAM    = "Roboto" if _T else "Segoe UI"
_PRIMARY     = C.PRIMARY
_PRIMARY_HOV = getattr(C, "PRIMARY_HOVER", "#15408A")
_LINE_COLOR  = C.BORDER
_LINE_FOCUS  = C.PRIMARY
_WIN_BG      = C.BG_PAGE


def _tk_font(size=11, weight="normal"):
    return (_FONT_FAM, size, weight)

# ── Init thème ────────────────────────────────────────────────────────────────
if _T:
    try:
        init_theme()
    except Exception:
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
else:
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Remember Me ─────────────────────────────────────────────────────────────────
from resource_utils import ensure_app_data_file, get_app_data_path, init_app_data_files

init_app_data_files()
try:
    from app_runtime_log import init_runtime_log
    init_runtime_log()
except Exception:
    pass

_REMEMBER_PATH = get_app_data_path("remember.json")
ensure_app_data_file("remember.json")


def _encode_password(plain: str) -> str:
    return base64.b64encode(plain.encode("utf-8")).decode("ascii")


def _decode_password(encoded: str) -> str:
    return base64.b64decode(encoded.encode("ascii")).decode("utf-8")


def _save_remember(username: str, plain_password: str):
    data = {"username": username,
            "password_encoded": _encode_password(plain_password)}
    with open(_REMEMBER_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _load_remember() -> dict | None:
    try:
        with open(_REMEMBER_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _delete_remember():
    try:
        if os.path.exists(_REMEMBER_PATH):
            os.remove(_REMEMBER_PATH)
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# WIDGET : Champ underline (ligne du bas seulement)
# ══════════════════════════════════════════════════════════════════════════════

class _UnderlineField(tk.Frame):
    """
    Champ de saisie style mockup :
    ─── [icône]  [placeholder / texte]  [bouton œil optionnel]  ───────────
    Seule la bordure du bas est visible (Canvas 1px).
    """

    def __init__(self, parent, icon_text: str, placeholder: str,
                 show_toggle: bool = False, show_char: str = "•", **kwargs):
        super().__init__(parent, bg=_WIN_BG)

        self._placeholder = placeholder
        self._show_char   = show_char
        self._is_password = show_toggle
        self._pw_visible  = False
        self._has_focus   = False

        # ── Ligne du bas (Canvas 1px) ─────────────────────────────────────
        self._line = tk.Canvas(self, height=1, bg=_LINE_COLOR,
                               highlightthickness=0, bd=0)
        self._line.pack(side="bottom", fill="x")

        # ── Conteneur horizontal ──────────────────────────────────────────
        row = tk.Frame(self, bg=_WIN_BG)
        row.pack(fill="x")

        # Icône gauche
        tk.Label(row, text=icon_text, font=(_FONT_FAM, 14),
                 bg=_WIN_BG, fg=C.TEXT_MUTED,
                 width=2).pack(side="left", padx=(0, 6))

        # Entry (fond transparent simulé)
        self.entry = tk.Entry(
            row,
            font=(_FONT_FAM, 12),
            fg=C.TEXT_MUTED,      # commence en placeholder couleur
            bg=_WIN_BG,
            bd=0, highlightthickness=0,
            insertbackground=_PRIMARY,
            relief="flat",
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=6)

        # Afficher le placeholder
        self._show_placeholder()

        # Bindings focus
        self.entry.bind("<FocusIn>",  self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)

        # Bouton toggle œil (password uniquement)
        if show_toggle:
            self._eye_lbl = tk.Label(
                row, text="🙈", font=(_FONT_FAM, 11),
                bg=_WIN_BG, fg=C.TEXT_MUTED, cursor="hand2")
            self._eye_lbl.pack(side="right", padx=(4, 0))
            self._eye_lbl.bind("<Button-1>", self._toggle_visibility)

    # ── Placeholder ───────────────────────────────────────────────────────
    def _show_placeholder(self):
        self.entry.delete(0, "end")
        self.entry.insert(0, self._placeholder)
        self.entry.configure(fg=C.TEXT_MUTED, show="")
        self._is_placeholder = True

    def _hide_placeholder(self):
        if self._is_placeholder:
            self.entry.delete(0, "end")
            self.entry.configure(
                fg=C.TEXT_PRIMARY,
                show=self._show_char if self._is_password and not self._pw_visible else "")
            self._is_placeholder = False

    def _on_focus_in(self, _=None):
        self._hide_placeholder()
        self._line.configure(bg=_LINE_FOCUS)

    def _on_focus_out(self, _=None):
        if not self.entry.get():
            self._show_placeholder()
        self._line.configure(bg=_LINE_COLOR)

    # ── Toggle visibilité mot de passe ────────────────────────────────────
    def _toggle_visibility(self, _=None):
        self._pw_visible = not self._pw_visible
        if not self._is_placeholder:
            self.entry.configure(
                show="" if self._pw_visible else self._show_char)
        self._eye_lbl.configure(
            text="👁" if self._pw_visible else "🙈")

    # ── API ───────────────────────────────────────────────────────────────
    def get(self) -> str:
        """Retourne le texte saisi (vide si placeholder affiché)."""
        if self._is_placeholder:
            return ""
        return self.entry.get()

    def set(self, value: str):
        """Pré-remplit le champ (ex: remember me)."""
        self._hide_placeholder()
        self.entry.delete(0, "end")
        self.entry.insert(0, value)
        # Maintenir le masque si mot de passe
        if self._is_password and not self._pw_visible:
            self.entry.configure(show=self._show_char)

    def shake_color(self):
        """Colore la ligne en rouge (erreur)."""
        self._line.configure(bg=C.DANGER)
        self.after(1500, lambda: self._line.configure(bg=_LINE_COLOR))


# ══════════════════════════════════════════════════════════════════════════════
# FENÊTRE DE LOGIN
# ══════════════════════════════════════════════════════════════════════════════

class LoginWindow(ctk.CTk):

    WIN_W = 440
    WIN_H = 520
    _SHAKE_OFFSETS = [14, -14, 10, -10, 7, -7, 4, -4, 2, -2, 0]

    def __init__(self):
        super().__init__()

        # ── Fenêtre sans bordure ──────────────────────────────────────────
        self.overrideredirect(True)          # supprime la barre titre Windows
        self.attributes("-topmost", True)    # z-index toujours au-dessus
        self.configure(fg_color=_WIN_BG)
        self.resizable(False, False)

        # Variables
        self.remember_me  = ctk.BooleanVar(value=False)
        self.app_launched = False

        self._drag_x = 0
        self._drag_y = 0

        self._setup_ui()
        self._center_window()
        self._load_remembered()

        # Fermeture Alt+F4 / clic ✕
        self.bind("<Alt-F4>", lambda _: self._close_window())
        self.bind("<Return>", lambda _: self.login())

    # ══════════════════════════════════════════════════════════════════════
    # CONSTRUCTION UI
    # ══════════════════════════════════════════════════════════════════════

    def _setup_ui(self):
        """
        Structure :
          ┌─────────────────────────────────────┐
          │  Bouton ✕                           │ ← Row 0 top-right
          │  Logo                               │ ← Row 1
          │  Champ Email (underline)            │ ← Row 2
          │  Champ Password (underline + œil)   │ ← Row 3
          │  Msg erreur                         │ ← Row 4
          │  Checkbox Remember Me               │ ← Row 5
          │  Bouton "Se connecter"              │ ← Row 6
          │  ─── & ───                          │ ← Row 7
          │  Bouton Config DB                   │ ← Row 8
          └─────────────────────────────────────┘
        """

        # ── Ombre légère via bordure Canvas externe ───────────────────────
        # (optionnel — uniquement visible si la fenêtre est sur fond clair)
        outer = tk.Frame(self, bg=C.BORDER, padx=1, pady=1)
        outer.place(relx=0, rely=0, relwidth=1, relheight=1)

        card = tk.Frame(outer, bg=_WIN_BG)
        card.pack(fill="both", expand=True)

        # ── Déplacement de la fenêtre au drag ─────────────────────────────
        card.bind("<ButtonPress-1>",   self._drag_start)
        card.bind("<B1-Motion>",       self._drag_motion)

        # ── Bouton ✕ coin haut droit ──────────────────────────────────────
        self._build_close_btn(card)

        # ── Logo ──────────────────────────────────────────────────────────
        self._build_logo(card)

        # ── Séparateur léger sous logo ────────────────────────────────────
        tk.Frame(card, height=1, bg=C.DIVIDER).pack(fill="x",
                                                     padx=40, pady=(0, 24))

        # ── Champs ────────────────────────────────────────────────────────
        fields_wrap = tk.Frame(card, bg=_WIN_BG)
        fields_wrap.pack(fill="x", padx=44)

        # Email / Nom d'utilisateur
        self._field_user = _UnderlineField(
            fields_wrap, icon_text="👤",
            placeholder="Nom d'utilisateur")
        self._field_user.pack(fill="x", pady=(0, 18))

        # Mot de passe
        self._field_pass = _UnderlineField(
            fields_wrap, icon_text="🔒",
            placeholder="Mot de passe",
            show_toggle=True)
        self._field_pass.pack(fill="x", pady=(0, 12))

        # ── Message d'erreur ──────────────────────────────────────────────
        self._err_var = tk.StringVar()
        self._err_lbl = tk.Label(
            fields_wrap,
            textvariable=self._err_var,
            font=_tk_font(10, "bold"),
            fg=C.DANGER, bg=_WIN_BG,
            anchor="w",
        )
        self._err_lbl.pack(fill="x", pady=(0, 6))

        # ── Remember Me ───────────────────────────────────────────────────
        rem_frame = tk.Frame(fields_wrap, bg=_WIN_BG)
        rem_frame.pack(fill="x", pady=(0, 16))

        self._rem_var = tk.BooleanVar(value=False)
        self.remember_me = self._rem_var     # alias pour compatibilité

        self._rem_cb = tk.Checkbutton(
            rem_frame,
            text="  Se souvenir de moi",
            variable=self._rem_var,
            font=_tk_font(10),
            fg=C.TEXT_SECONDARY if hasattr(C, "TEXT_SECONDARY") else C.TEXT_PRIMARY, bg=_WIN_BG,
            activebackground=_WIN_BG,
            selectcolor=_WIN_BG,
            bd=0, highlightthickness=0,
            command=self._on_remember_toggle,
        )
        self._rem_cb.pack(side="left")

        # ── Bouton Connexion ──────────────────────────────────────────────
        self._build_login_btn(fields_wrap)

        # ── Séparateur  ─── & ─── ─────────────────────────────────────────
        self._build_separator(card)

        # ── Bouton Configuration DB ───────────────────────────────────────
        self._build_config_btn(card)

        # ── Bouton Paramètres utilisateurs ───────────────────────────────
        self._build_user_settings_btn(card)

        # Padding bas
        tk.Frame(card, height=20, bg=_WIN_BG).pack()

    def _build_close_btn(self, parent):
        """Bouton ✕ discret en haut à droite."""
        top_bar = tk.Frame(parent, bg=_WIN_BG, height=36)
        top_bar.pack(fill="x")
        top_bar.pack_propagate(False)

        # Draggable sur la top bar
        top_bar.bind("<ButtonPress-1>", self._drag_start)
        top_bar.bind("<B1-Motion>",     self._drag_motion)

        close_btn = tk.Label(
            top_bar,
            text="✕",
            font=_tk_font(13, "bold"),
            fg=C.TEXT_MUTED, bg=_WIN_BG,
            cursor="hand2",
            padx=12, pady=6,
        )
        close_btn.pack(side="right")
        close_btn.bind("<Enter>",    lambda _: close_btn.configure(fg=C.TEXT_PRIMARY))
        close_btn.bind("<Leave>",    lambda _: close_btn.configure(fg=C.TEXT_MUTED))
        close_btn.bind("<Button-1>", lambda _: self._close_window())

    def _build_logo(self, parent):
        """Zone logo : image si dispo, sinon texte stylisé."""
        logo_frame = tk.Frame(parent, bg=_WIN_BG)
        logo_frame.pack(pady=(4, 12))

        try:
            logo_path = get_resource_path("image/logo 3.png")
            img = Image.open(logo_path)
            self._logo_img = ctk.CTkImage(
                light_image=img, dark_image=img, size=(150, 64))
            ctk.CTkLabel(logo_frame, image=self._logo_img,
                         text="", bg_color=_WIN_BG).pack()
        except Exception:
            # Fallback texte
            tk.Label(logo_frame, text="iJeery",
                     font=_tk_font(30, "bold"),
                     fg=_PRIMARY, bg=_WIN_BG).pack()
            tk.Label(logo_frame, text="ERP Solution",
                     font=_tk_font(10),
                     fg=C.TEXT_MUTED, bg=_WIN_BG).pack()

    def _build_login_btn(self, parent):
        """Bouton 'Se connecter' — bleu plein, coins arrondis via Canvas."""
        btn_frame = tk.Frame(parent, bg=_WIN_BG)
        btn_frame.pack(fill="x", pady=(4, 0))

        self._login_btn = ctk.CTkButton(
            btn_frame,
            text="Se connecter",
            command=self.login,
            height=42,
            fg_color=_PRIMARY,
            hover_color=_PRIMARY_HOV,
            text_color="#FFFFFF",
            font=ctk.CTkFont(family=_FONT_FAM, size=13, weight="bold"),
            corner_radius=6,
        )
        self._login_btn.pack(fill="x")

    def _build_separator(self, parent):
        """Séparateur ─────  &  ───── du mockup."""
        sep = tk.Frame(parent, bg=_WIN_BG)
        sep.pack(fill="x", padx=44, pady=(20, 8))

        left_line  = tk.Frame(sep, height=1, bg=C.BORDER)
        right_line = tk.Frame(sep, height=1, bg=C.BORDER)
        amp_lbl    = tk.Label(sep, text=" & ",
                              font=_tk_font(10),
                              fg=C.TEXT_MUTED, bg=_WIN_BG)

        left_line.pack(side="left",  fill="x", expand=True, pady=6)
        amp_lbl.pack(side="left")
        right_line.pack(side="left", fill="x", expand=True, pady=6)

    def _build_config_btn(self, parent):
        """Bouton configuration base de données."""
        btn_wrap = tk.Frame(parent, bg=_WIN_BG)
        btn_wrap.pack(fill="x", padx=44)

        self._db_btn = ctk.CTkButton(
            btn_wrap,
            text="⚙  Configuration base de données",
            command=self.open_database_config,
            height=36,
            fg_color="transparent",
            hover_color=C.BG_INPUT if hasattr(C, "BG_INPUT") else "#F0F0F0",
            text_color=C.TEXT_SECONDARY if hasattr(C, "TEXT_SECONDARY") else C.TEXT_PRIMARY,
            border_width=1,
            border_color=C.BORDER,
            font=ctk.CTkFont(family=_FONT_FAM, size=11),
            corner_radius=6,
        )
        self._db_btn.pack(fill="x")

    def _build_user_settings_btn(self, parent):
        """Bouton Paramètres utilisateurs (infos + mot de passe + impression)."""
        btn_wrap = tk.Frame(parent, bg=_WIN_BG)
        btn_wrap.pack(fill="x", padx=44, pady=(10, 0))

        self._user_settings_btn = ctk.CTkButton(
            btn_wrap,
            text="👤  Paramètres utilisateurs",
            command=self.open_user_settings,
            height=36,
            fg_color="transparent",
            hover_color=C.BG_INPUT if hasattr(C, "BG_INPUT") else "#F0F0F0",
            text_color=C.TEXT_SECONDARY if hasattr(C, "TEXT_SECONDARY") else C.TEXT_PRIMARY,
            border_width=1,
            border_color=C.BORDER,
            font=ctk.CTkFont(family=_FONT_FAM, size=11),
            corner_radius=6,
        )
        self._user_settings_btn.pack(fill="x")

    # ══════════════════════════════════════════════════════════════════════
    # DRAG (déplacement fenêtre sans barre titre)
    # ══════════════════════════════════════════════════════════════════════

    def _drag_start(self, event):
        self._drag_x = event.x_root - self.winfo_x()
        self._drag_y = event.y_root - self.winfo_y()

    def _drag_motion(self, event):
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.geometry(f"+{x}+{y}")

    # ══════════════════════════════════════════════════════════════════════
    # REMEMBER ME
    # ══════════════════════════════════════════════════════════════════════

    def _load_remembered(self):
        """Pré-remplit les champs si remember.json existe."""
        data = _load_remember()
        if data and "password_encoded" in data:
            try:
                plain = _decode_password(data["password_encoded"])
                self._field_user.set(data.get("username", ""))
                self._field_pass.set(plain)
                self._rem_var.set(True)
            except Exception:
                _delete_remember()

    def _on_remember_toggle(self):
        if not self._rem_var.get():
            _delete_remember()

    # ══════════════════════════════════════════════════════════════════════
    # UTILITAIRES FENÊTRE
    # ══════════════════════════════════════════════════════════════════════

    def _center_window(self):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - self.WIN_W) // 2
        y  = (sh - self.WIN_H) // 2
        self.geometry(f"{self.WIN_W}x{self.WIN_H}+{x}+{y}")

    def _close_window(self):
        try:
            self.quit()
            self.destroy()
        except Exception:
            pass

    def _show_error(self, msg: str):
        """Affiche le message d'erreur et le masque après 3,5 s."""
        self._err_var.set(msg)
        # Colorer les lignes des champs en rouge
        self._field_user.shake_color()
        self._field_pass.shake_color()
        self.after(3500, lambda: self._err_var.set(""))

    # ── Effet secousse ────────────────────────────────────────────────────
    def _shake(self):
        x0 = (self.winfo_screenwidth()  - self.WIN_W) // 2
        y0 = (self.winfo_screenheight() - self.WIN_H) // 2

        def _step(offsets):
            if not offsets:
                self.geometry(f"{self.WIN_W}x{self.WIN_H}+{x0}+{y0}")
                return
            self.geometry(f"{self.WIN_W}x{self.WIN_H}+{x0 + offsets[0]}+{y0}")
            self.after(28, lambda: _step(offsets[1:]))

        _step(self._SHAKE_OFFSETS)

    # ── Toast succès ──────────────────────────────────────────────────────
    def _show_toast(self, message: str = "Connexion réussie !"):
        """
        Notification flottante succès — fond vert SUCCESS_DARK,
        positionnée en bas au centre de l'écran.
        """
        toast = tk.Toplevel(self)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(bg=C.SUCCESS_DARK)

        # Contenu
        frame = tk.Frame(toast, bg=C.SUCCESS_DARK)
        frame.pack(ipadx=24, ipady=12)

        tk.Label(
            frame,
            text=f"✔  {message}",
            font=_tk_font(12, "bold"),
            fg="#FFFFFF",
            bg=C.SUCCESS_DARK,
        ).pack(padx=24, pady=12)

        # Coins arrondis simulés via highlight
        toast.configure(highlightbackground=C.SUCCESS_DARK,
                        highlightthickness=0)

        toast.update_idletasks()
        tw = toast.winfo_reqwidth()
        th = toast.winfo_reqheight()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        toast.geometry(f"{tw}x{th}+{(sw - tw) // 2}+{sh - th - 60}")

        # Animation apparition (fade-in simulé)
        toast.attributes("-alpha", 0.0)
        def _fade_in(alpha=0.0):
            if alpha < 1.0:
                toast.attributes("-alpha", min(alpha + 0.12, 1.0))
                toast.after(18, lambda: _fade_in(alpha + 0.12))
        _fade_in()

        # Disparaît après 2,2 s
        def _destroy():
            try:
                if toast.winfo_exists():
                    toast.destroy()
            except Exception:
                pass

        self.after(2200, _destroy)

    # ══════════════════════════════════════════════════════════════════════
    # BASE DE DONNÉES — logique métier 100 % intacte
    # ══════════════════════════════════════════════════════════════════════

    def connect_db(self):
        try:
            config_path = get_config_path('config.json')
            content, _ = safe_file_read(config_path)
            cfg = json.loads(content)['database']
            return psycopg2.connect(
                host=cfg['host'], user=cfg['user'],
                password=cfg['password'], database=cfg['database'],
                port=cfg['port'])
        except psycopg2.Error as err:
            messagebox.showerror("Connexion", f"Erreur : {err}")
        except FileNotFoundError:
            messagebox.showerror("Configuration", "config.json introuvable.")
        except KeyError as err:
            messagebox.showerror("Configuration", f"Clé manquante : {err}")
        except Exception as err:
            messagebox.showerror("Erreur", str(err))
        return None

    def get_authorized_menus(self, idfonction):
        conn = self.connect_db()
        if not conn:
            return []
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT m.designationmenu, m.page
                FROM tb_menu m
                JOIN tb_autorisation a ON m.id = a.idmenu
                WHERE a.idfonction = %s
                ORDER BY m.designationmenu
            """, (idfonction,))
            return cur.fetchall()
        except psycopg2.Error as err:
            messagebox.showerror("Erreur", f"Récupération menus : {err}")
            return []
        finally:
            conn.close()

    def save_user_session(self, user_data, menus):
        session = {
            "user_id":       user_data[0],
            "username":      user_data[1],
            "fonction_id":   user_data[2],
            "fonction_name": user_data[3],
            "menus":         [(m[0], m[1]) for m in menus],
        }
        try:
            with open(get_session_path(), "w", encoding="utf-8") as f:
                json.dump(session, f, indent=4, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Session", f"Sauvegarde session : {e}")

    # ══════════════════════════════════════════════════════════════════════
    # CONNEXION — logique métier 100 % intacte
    # ══════════════════════════════════════════════════════════════════════

    def login(self):
        username = self._field_user.get().strip()
        raw_pwd  = self._field_pass.get().strip()

        if not username or not raw_pwd:
            self._show_error("Veuillez remplir tous les champs.")
            self._shake()
            return

        conn = self.connect_db()
        if not conn:
            return

        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT u.iduser, u.username, u.idfonction,
                       f.designationfonction, u.active
                FROM tb_users u
                JOIN tb_fonction f ON u.idfonction = f.idfonction
                WHERE u.username = %s AND u.password = %s
            """, (username, raw_pwd))
            user = cur.fetchone()

            if user and user[4]:
                menus = self.get_authorized_menus(user[2])
                session_data = {
                    "user_id":       user[0],
                    "username":      user[1],
                    "fonction_id":   user[2],
                    "fonction_name": user[3],
                    "menus":         [(m[0], m[1]) for m in menus],
                }
                self.save_user_session(user, menus)
                try:
                    AppLogger(session_data=session_data).log(
                        action="Connexion",
                        element=user[1],
                        details=f"Connexion réussie (fonction='{user[3]}')",
                        value="login_ok",
                    )
                except Exception:
                    pass

                # Remember Me
                if self._rem_var.get():
                    _save_remember(username, raw_pwd)
                else:
                    _delete_remember()

                # Succès : désactiver le bouton + toast + lancer l'app
                self._login_btn.configure(state="disabled")
                self._show_toast(f"Bienvenue, {user[1]} !")
                self.after(700, lambda: self.launch_main_app_safely(
                    session_data))
            else:
                self._show_error("Identifiants incorrects.")
                try:
                    AppLogger(session_data={"username": username}).log(
                        action="Connexion",
                        element=username or "Inconnu",
                        details="Connexion échouée (identifiants incorrects ou compte inactif)",
                        value="login_failed",
                    )
                except Exception:
                    pass
                self._shake()

        except psycopg2.Error as err:
            messagebox.showerror("Erreur DB", str(err))
        finally:
            conn.close()

    # ══════════════════════════════════════════════════════════════════════
    # LANCEMENT APP PRINCIPALE — logique métier 100 % intacte
    # ══════════════════════════════════════════════════════════════════════

    def launch_main_app_safely(self, session_data):
        def run():
            try:
                time.sleep(0.4)
                script = os.path.join(os.path.dirname(__file__), "app_main.py")
                if os.path.exists(script):
                    subprocess.Popen([sys.executable, script])
                    self.after(800, self._close_window)
                else:
                    self.after(400, lambda: self._import_and_run(session_data))
            except Exception as e:
                self.after(0, lambda: self._handle_app_error(e))

        threading.Thread(target=run, daemon=True).start()

    def _import_and_run(self, session_data):
        try:
            import importlib.util
            if importlib.util.find_spec("app_main") is None:
                raise ImportError("Module app_main non trouvé")
            from app_main import App
            try:
                self.withdraw()
                self.update_idletasks()
            except Exception:
                pass
            try:
                self.destroy()
            except Exception:
                pass
            main_app = App(session_data)
            self.app_launched = True

            orig = main_app.destroy
            def safe_destroy():
                try:
                    orig()
                except Exception:
                    pass
                finally:
                    try:
                        self.quit()
                    except Exception:
                        pass
                    os._exit(0)

            main_app.destroy = safe_destroy
            main_app.protocol("WM_DELETE_WINDOW", safe_destroy)
            main_app.mainloop()
        except Exception as e:
            self._handle_app_error(e)

    def _handle_app_error(self, error):
        self.deiconify()
        self.app_launched = False
        self._login_btn.configure(state="normal")
        messagebox.showerror("Erreur",
                             f"Impossible d'ouvrir l'application : {error}")
        import traceback; traceback.print_exc()

    # ══════════════════════════════════════════════════════════════════════
    # CONFIG DB
    # ══════════════════════════════════════════════════════════════════════

    def open_database_config(self):
        w = ConfigDataBase()
        w.focus_force()
        w.mainloop()

    def open_user_settings(self):
        username_hint = ""
        try:
            username_hint = (self._field_user.get() or "").strip()
        except Exception:
            username_hint = ""
        w = UserSettingsWindow(self, self.connect_db, username_hint=username_hint)
        try:
            w.focus_force()
        except Exception:
            pass

    def start(self):
        self.mainloop()


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    LoginWindow().start()
