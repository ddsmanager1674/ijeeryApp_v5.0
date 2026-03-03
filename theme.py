# ============================================================
#  theme.py  —  Configuration centrale des fonts
#  Place ce fichier au même niveau que app_main.py
# ============================================================
import os
import sys
import customtkinter as ctk
from tkinter import font as tkfont

FONT_FAMILY = "Roboto"
FONT_SIZE   = 10

# ============================================================
#  Chargement de la police Roboto depuis le dossier /fonts
# ============================================================
def _resource_path(relative_path):
    """Compatible dev + PyInstaller"""
    try:
        base = sys._MEIPASS
    except AttributeError:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)

def load_roboto():
    """
    Charge les variantes Roboto depuis fonts/
    Appelle cette fonction APRÈS super().__init__() dans App.__init__()
    """
    font_files = [
        "fonts/Roboto-Regular.ttf",
        "fonts/Roboto-Bold.ttf",
        "fonts/Roboto-Italic.ttf",
        "fonts/Roboto-BoldItalic.ttf",
    ]
    loaded = False

    if sys.platform == "win32":
        import ctypes
        FR_PRIVATE = 0x10
        for f in font_files:
            path = _resource_path(f)
            if os.path.exists(path):
                result = ctypes.windll.gdi32.AddFontResourceExW(path, FR_PRIVATE, 0)
                if result > 0:
                    loaded = True
                    print(f"✅ Font chargée : {path}")
                else:
                    print(f"⚠️  Échec chargement : {path}")
            else:
                print(f"⚠️  Fichier introuvable : {path}")
    else:
        import shutil
        font_dir = os.path.expanduser("~/Library/Fonts" if sys.platform == "darwin" else "~/.fonts")
        os.makedirs(font_dir, exist_ok=True)
        for f in font_files:
            src = _resource_path(f)
            if os.path.exists(src):
                dst = os.path.join(font_dir, os.path.basename(src))
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)
                loaded = True

    if not loaded:
        print("⛔ Roboto introuvable — fallback sur police système")
    return loaded


# ============================================================
#  Fonts — appelées APRÈS la création de la fenêtre root
# ============================================================

# Pour CustomTkinter (CTkButton, CTkLabel, CTkEntry…)
# Usage : font=FONTS["label"]
def _make_fonts():
    return {
        "default":   ctk.CTkFont(family=FONT_FAMILY, size=FONT_SIZE),
        "bold":      ctk.CTkFont(family=FONT_FAMILY, size=FONT_SIZE, weight="bold"),
        "title":     ctk.CTkFont(family=FONT_FAMILY, size=20,        weight="bold"),
        "subtitle":  ctk.CTkFont(family=FONT_FAMILY, size=14,        weight="bold"),
        "small":     ctk.CTkFont(family=FONT_FAMILY, size=10),
        "button":    ctk.CTkFont(family=FONT_FAMILY, size=FONT_SIZE, weight="bold"),
        "label":     ctk.CTkFont(family=FONT_FAMILY, size=FONT_SIZE),
        "entry":     ctk.CTkFont(family=FONT_FAMILY, size=FONT_SIZE),
        "menu_main": ctk.CTkFont(family=FONT_FAMILY, size=14),
        "menu_sub":  ctk.CTkFont(family=FONT_FAMILY, size=FONT_SIZE),
        "mono":      ctk.CTkFont(family="Courier New", size=FONT_SIZE),
    }

# Pour Tkinter standard (tk.Label, ttk.Treeview, tk.Button…)
# Usage : font=FONT_TUPLE["label"]
FONT_TUPLE = {
    "default":   (FONT_FAMILY, FONT_SIZE),
    "bold":      (FONT_FAMILY, FONT_SIZE, "bold"),
    "title":     (FONT_FAMILY, 20,        "bold"),
    "subtitle":  (FONT_FAMILY, 14,        "bold"),
    "small":     (FONT_FAMILY, 10),
    "button":    (FONT_FAMILY, FONT_SIZE, "bold"),
    "label":     (FONT_FAMILY, FONT_SIZE),
    "entry":     (FONT_FAMILY, FONT_SIZE),
    "menu_main": (FONT_FAMILY, 14),
    "menu_sub":  (FONT_FAMILY, FONT_SIZE),
    "mono":      ("Courier New", FONT_SIZE),
}

# Dictionnaire global, peuplé par apply_global_font()
FONTS = {}


# ============================================================
#  Application globale du font sur tous les widgets
# ============================================================
def apply_global_font(root):
    """
    Appelle cette fonction UNE SEULE FOIS dans App.__init__()
    juste après super().__init__() et load_roboto().
    """
    import tkinter.ttk as ttk

    # 1. Peupler FONTS maintenant que la fenêtre root existe
    global FONTS
    FONTS.update(_make_fonts())

    # 2. Fonts nommés Tkinter
    for named in ("TkDefaultFont", "TkTextFont", "TkHeadingFont",
                  "TkCaptionFont", "TkMenuFont", "TkSmallCaptionFont",
                  "TkTooltipFont", "TkIconFont"):
        try:
            tkfont.nametofont(named).configure(family=FONT_FAMILY, size=FONT_SIZE)
        except Exception:
            pass
    try:
        tkfont.nametofont("TkFixedFont").configure(family="Courier New", size=FONT_SIZE)
    except Exception:
        pass

    # 3. option_add (couvre tous les widgets tk.*)
    root.option_add("*Font", (FONT_FAMILY, FONT_SIZE))

    # 4. Styles ttk
    style = ttk.Style()
    for w in ("TLabel", "TButton", "TEntry", "TCombobox", "TSpinbox",
              "TNotebook", "TNotebook.Tab", "Treeview", "Treeview.Heading",
              "TMenubutton", "TRadiobutton", "TCheckbutton"):
        try:
            style.configure(w, font=(FONT_FAMILY, FONT_SIZE))
        except Exception:
            pass

    print(f"✅ Font globale appliquée : {FONT_FAMILY} {FONT_SIZE}px")