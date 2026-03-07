# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     iJeery — login_window.py  (refonte v2)                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  • Thème iJeery (app_theme)                                                 ║
║  • Remember Me : username + password haché (bcrypt) dans remember.json     ║
║  • Auto-remplissage au démarrage si remember.json présent                  ║
║  • Notification flottante de succès (toast)                                 ║
║  • Effet secousse sur identifiants incorrects                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import customtkinter as ctk
from tkinter import messagebox
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
from resource_utils import (get_resource_path, get_config_path,
                             get_session_path, safe_file_read)

# ── Thème iJeery ──────────────────────────────────────────────────────────────
try:
    from app_theme import Colors, Fonts, Theme, init_theme
    _T = True
except ImportError:
    _T = False


class _C:
    BG_PAGE      = "#ECF0F1"
    BG_CARD      = "#FFFFFF"
    BG_HEADER    = "#2C3E50"
    BG_INPUT     = "#F4F6F8"
    PRIMARY      = "#3498DB"
    PRIMARY_HOVER= "#2980B9"
    SUCCESS      = "#2ECC71"
    SUCCESS_DARK = "#27AE60"
    DANGER       = "#E74C3C"
    DANGER_DARK  = "#C0392B"
    TEXT_PRIMARY = "#2C3E50"
    TEXT_MUTED   = "#95A5A6"
    BORDER       = "#D5D8DC"
    BORDER_FOCUS = "#3498DB"
    DIVIDER      = "#E8EAED"
    SILVER       = "#BDC3C7"
    CLOUDS       = "#ECF0F1"
    TEXT_MUTED2  = "#7F8C8D"


C = Colors if _T else _C

# ── Init thème ────────────────────────────────────────────────────────────────
if _T:
    init_theme()
else:
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Chemin remember.json ──────────────────────────────────────────────────────
_REMEMBER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "remember.json")

# ── Encodage / décodage mot de passe (base64 — obfusqué, réversible) ─────────
def _encode_password(plain: str) -> str:
    """Encode le mot de passe en base64 pour le stockage dans remember.json."""
    return base64.b64encode(plain.encode("utf-8")).decode("ascii")


def _decode_password(encoded: str) -> str:
    """Décode le base64 et retourne le mot de passe en clair."""
    return base64.b64decode(encoded.encode("ascii")).decode("utf-8")


def _save_remember(username: str, plain_password: str):
    """Enregistre username + password encodé (base64) dans remember.json."""
    data = {
        "username": username,
        "password_encoded": _encode_password(plain_password),
    }
    with open(_REMEMBER_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _load_remember() -> dict | None:
    """Retourne le contenu de remember.json ou None si absent/invalide."""
    try:
        with open(_REMEMBER_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _delete_remember():
    """Supprime remember.json s'il existe."""
    try:
        if os.path.exists(_REMEMBER_PATH):
            os.remove(_REMEMBER_PATH)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
#  LoginWindow
# ─────────────────────────────────────────────────────────────────────────────
class LoginWindow(ctk.CTk):

    _SHAKE_OFFSETS = [10, -10, 8, -8, 6, -6, 4, -4, 2, -2, 0]

    def __init__(self):
        super().__init__()

        self.configure(fg_color=C.BG_PAGE)
        self.title("iJeery — Connexion")
        self.geometry("420x520")
        self.resizable(False, False)

        self.username     = ctk.StringVar()
        self.password     = ctk.StringVar()
        self.remember_me  = ctk.BooleanVar(value=False)
        self.app_launched = False

        self._setup_ui()
        self._center_window(420, 520)
        self._load_remembered()

        self.bind("<Return>", lambda _: self.login())

    # ─────────────────────────────────────────────────────────────────────────
    #  UI
    # ─────────────────────────────────────────────────────────────────────────
    def _f(self, size=12, weight="normal"):
        return ctk.CTkFont(
            family="Roboto" if _T else "Segoe UI",
            size=size, weight=weight)

    def _setup_ui(self):
        # ── Card centrale ─────────────────────────────────────────────────────
        card = ctk.CTkFrame(self, fg_color=C.BG_CARD,
                            corner_radius=16,
                            border_width=1, border_color=C.BORDER)
        card.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.88)

        # ── Logo / titre ──────────────────────────────────────────────────────
        logo_frame = ctk.CTkFrame(card, fg_color="transparent")
        logo_frame.pack(pady=(28, 4))

        try:
            logo_path = get_resource_path("image/logo 3.png")
            self._logo_img = ctk.CTkImage(
                light_image=Image.open(logo_path),
                dark_image=Image.open(logo_path),
                size=(130, 55))
            ctk.CTkLabel(logo_frame, image=self._logo_img,
                         text="").pack()
        except Exception:
            ctk.CTkLabel(logo_frame, text="iJeery",
                         font=self._f(26, "bold"),
                         text_color=C.BG_HEADER).pack()

        ctk.CTkLabel(card,
                     text="Bienvenue — connectez-vous pour continuer",
                     font=self._f(10), text_color=C.TEXT_MUTED
                     ).pack(pady=(0, 18))

        # ── Séparateur ────────────────────────────────────────────────────────
        ctk.CTkFrame(card, height=1, fg_color=C.DIVIDER
                     ).pack(fill="x", padx=24)

        # ── Champs ────────────────────────────────────────────────────────────
        fields = ctk.CTkFrame(card, fg_color="transparent")
        fields.pack(fill="x", padx=28, pady=(18, 4))

        # Username
        ctk.CTkLabel(fields, text="Nom d'utilisateur",
                     font=self._f(11), text_color=C.TEXT_MUTED,
                     anchor="w").pack(fill="x", pady=(0, 3))
        self.username_entry = ctk.CTkEntry(
            fields,
            textvariable=self.username,
            height=36,
            fg_color=C.BG_INPUT, border_color=C.BORDER,
            border_width=1, text_color=C.TEXT_PRIMARY,
            font=self._f(12), corner_radius=8,
            placeholder_text="ex: admin")
        self.username_entry.pack(fill="x", pady=(0, 12))
        self.username_entry.bind(
            "<FocusIn>",
            lambda _: self.username_entry.configure(
                border_color=C.BORDER_FOCUS))
        self.username_entry.bind(
            "<FocusOut>",
            lambda _: self.username_entry.configure(
                border_color=C.BORDER))

        # Password
        ctk.CTkLabel(fields, text="Mot de passe",
                     font=self._f(11), text_color=C.TEXT_MUTED,
                     anchor="w").pack(fill="x", pady=(0, 3))
        self.password_entry = ctk.CTkEntry(
            fields,
            textvariable=self.password,
            show="•",
            height=36,
            fg_color=C.BG_INPUT, border_color=C.BORDER,
            border_width=1, text_color=C.TEXT_PRIMARY,
            font=self._f(12), corner_radius=8,
            placeholder_text="••••••••")
        self.password_entry.pack(fill="x", pady=(0, 8))
        self.password_entry.bind(
            "<FocusIn>",
            lambda _: self.password_entry.configure(
                border_color=C.BORDER_FOCUS))
        self.password_entry.bind(
            "<FocusOut>",
            lambda _: self.password_entry.configure(
                border_color=C.BORDER))

        # Remember me
        self.remember_checkbox = ctk.CTkCheckBox(
            fields,
            text="Se souvenir de moi",
            variable=self.remember_me,
            font=self._f(11), text_color=C.TEXT_PRIMARY,
            checkbox_width=16, checkbox_height=16,
            corner_radius=3,
            fg_color=C.PRIMARY, hover_color=C.PRIMARY_HOVER,
            command=self._on_remember_toggle)
        self.remember_checkbox.pack(anchor="w", pady=(0, 12))

        # ── Message d'erreur ──────────────────────────────────────────────────
        self.error_label = ctk.CTkLabel(
            fields, text="",
            font=self._f(11, "bold"),
            text_color=C.DANGER)
        self.error_label.pack(pady=(0, 4))

        # ── Bouton Connexion ──────────────────────────────────────────────────
        self.login_button = ctk.CTkButton(
            fields,
            text="Se connecter",
            command=self.login,
            height=40,
            fg_color=C.PRIMARY, hover_color=C.PRIMARY_HOVER,
            text_color="#FFFFFF",
            font=self._f(13, "bold"),
            corner_radius=8)
        self.login_button.pack(fill="x", pady=(0, 8))

        # ── Bouton Config DB ──────────────────────────────────────────────────
        self.database_login_button = ctk.CTkButton(
            fields,
            text="⚙  Configuration base de données",
            command=self.open_database_config,
            height=36,
            fg_color=C.CLOUDS, hover_color=C.SILVER,
            text_color=C.TEXT_PRIMARY,
            border_width=1, border_color=C.BORDER,
            font=self._f(11),
            corner_radius=8)
        self.database_login_button.pack(fill="x", pady=(0, 20))

    # ─────────────────────────────────────────────────────────────────────────
    #  Remember Me
    # ─────────────────────────────────────────────────────────────────────────
    def _load_remembered(self):
        """Pré-remplit les champs si remember.json existe."""
        data = _load_remember()
        if data and "password_encoded" in data:
            try:
                plain = _decode_password(data["password_encoded"])
                self.username.set(data.get("username", ""))
                self.password.set(plain)   # affiché sous •••• grâce au mask
                self.remember_me.set(True)
            except Exception:
                # Fichier corrompu → on l'ignore et on le supprime
                _delete_remember()

    def _on_remember_toggle(self):
        """Appelé quand la checkbox change d'état."""
        if not self.remember_me.get():
            _delete_remember()

    # ─────────────────────────────────────────────────────────────────────────
    #  Utilitaires fenêtre
    # ─────────────────────────────────────────────────────────────────────────
    def _center_window(self, w, h):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    def _show_error(self, message: str):
        self.error_label.configure(text=message)
        self.after(3500, lambda: self.error_label.configure(text=""))

    # ── Effet secousse ────────────────────────────────────────────────────────
    def _shake(self):
        x0 = (self.winfo_screenwidth()  - 420) // 2
        y0 = (self.winfo_screenheight() - 520) // 2

        def _step(offsets):
            if not offsets:
                self.geometry(f"420x520+{x0}+{y0}")
                return
            self.geometry(f"420x520+{x0 + offsets[0]}+{y0}")
            self.after(30, lambda: _step(offsets[1:]))

        _step(self._SHAKE_OFFSETS)

    # ── Toast succès ──────────────────────────────────────────────────────────
    def _show_toast(self, message: str = "Connexion réussie !"):
        toast = ctk.CTkToplevel(self)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        if _T:
            Theme.apply_toplevel(toast)

        frame = ctk.CTkFrame(toast,
                             fg_color=C.SUCCESS_DARK,
                             corner_radius=10)
        frame.pack(ipadx=20, ipady=10)
        ctk.CTkLabel(frame, text=f"✔  {message}",
                     font=self._f(12, "bold"),
                     text_color="#FFFFFF").pack(padx=20, pady=10)

        toast.update_idletasks()
        tw = toast.winfo_width()
        th = toast.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        toast.geometry(f"+{(sw - tw) // 2}+{sh - th - 60}")

        # Disparaît après 2 s
        self.after(2000, lambda: (toast.grab_release(),
                                   toast.destroy())
                   if toast.winfo_exists() else None)

    # ─────────────────────────────────────────────────────────────────────────
    #  Base de données
    # ─────────────────────────────────────────────────────────────────────────
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
            messagebox.showerror("Configuration",
                                 "config.json introuvable.")
        except KeyError as err:
            messagebox.showerror("Configuration",
                                 f"Clé manquante : {err}")
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
            messagebox.showerror("Erreur",
                                 f"Récupération menus : {err}")
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
            messagebox.showerror("Session",
                                 f"Sauvegarde session : {e}")

    # ─────────────────────────────────────────────────────────────────────────
    #  Connexion
    # ─────────────────────────────────────────────────────────────────────────
    def login(self):
        username = self.username.get().strip()
        raw_pwd  = self.password.get().strip()

        if not username or not raw_pwd:
            self._show_error("Veuillez remplir tous les champs.")
            self._shake()
            return

        conn = self.connect_db()
        if not conn:
            return

        try:
            cur = conn.cursor()
            # Authentification standard : le mot de passe en clair est dans
            # l'entry (saisi manuellement OU décodé depuis remember.json)
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

                # ── Remember Me ───────────────────────────────────────────
                if self.remember_me.get():
                    # Stocke le mot de passe encodé base64 dans remember.json
                    _save_remember(username, raw_pwd)
                else:
                    _delete_remember()

                # ── Succès ────────────────────────────────────────────────
                self.login_button.configure(state="disabled")
                self._show_toast(f"Bienvenue, {user[1]} !")
                self.after(700, lambda: self.launch_main_app_safely(
                    session_data))
            else:
                self._show_error("Identifiants incorrects.")
                self._shake()

        except psycopg2.Error as err:
            messagebox.showerror("Erreur DB", str(err))
        finally:
            conn.close()

    # ─────────────────────────────────────────────────────────────────────────
    #  Lancement app principale
    # ─────────────────────────────────────────────────────────────────────────
    def launch_main_app_safely(self, session_data):
        def run():
            try:
                time.sleep(0.4)
                script = os.path.join(os.path.dirname(__file__),
                                      "app_main.py")
                if os.path.exists(script):
                    subprocess.Popen([sys.executable, script])
                    self.after(800, self._close_login)
                else:
                    self.after(400, lambda: self._import_and_run(
                        session_data))
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
        self.login_button.configure(state="normal")
        messagebox.showerror("Erreur",
                             f"Impossible d'ouvrir l'application : {error}")
        import traceback; traceback.print_exc()

    def _close_login(self):
        try:
            self.quit()
            self.destroy()
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    #  Config DB
    # ─────────────────────────────────────────────────────────────────────────
    def open_database_config(self):
        w = ConfigDataBase()
        w.focus_force()
        w.mainloop()

    def start(self):
        self.mainloop()


if __name__ == "__main__":
    LoginWindow().start()