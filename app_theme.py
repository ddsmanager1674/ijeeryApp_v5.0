# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         iJeery — app_theme.py                              ║
║                   Système de thème centralisé v5.0                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Usage :                                                                    ║
║    from app_theme import Theme, Fonts, styled                               ║
║                                                                             ║
║    Theme.apply(root)          # Applique le thème à la fenêtre              ║
║    Fonts.load()               # Charge les polices Roboto                   ║
║    Fonts.body()               # CTkFont corps de texte                      ║
║    Fonts.heading()            # CTkFont titre                               ║
║    styled.button(frame, ...) # Bouton stylisé prêt à l'emploi              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import customtkinter as ctk

# ─────────────────────────────────────────────────────────────────────────────
# 1. PALETTE COMPLÈTE
# ─────────────────────────────────────────────────────────────────────────────

class Colors:
    """
    Toutes les couleurs du thème iJeery.
    Utilisation : Colors.ACCENT  ou  Colors.SUCCESS_LIGHT
    """

    # ── Structure & Texte ────────────────────────────────────────────────────
    MIDNIGHT        = "#2C3E50"   # Sidebar, headers, texte principal
    MIDNIGHT_LIGHT  = "#34495E"   # Variante plus claire pour hover sidebar
    MIDNIGHT_DARK   = "#1A252F"   # Variante encore plus sombre (active state)

    # ── Fonds & Zones ────────────────────────────────────────────────────────
    BG_PAGE         = "#ECF0F1"   # Clouds — arrière-plan général des pages
    BG_CARD         = "#FFFFFF"   # Fond des cards / panneaux
    BG_INPUT        = "#F4F6F8"   # Fond des champs de saisie
    BG_SIDEBAR      = "#2C3E50"   # Fond barre latérale
    BG_HEADER       = "#2C3E50"   # Fond en-têtes de tableaux
    BG_ROW_ALT      = "#F8F9FA"   # Lignes alternées de tableaux
    BG_HOVER_ROW    = "#EBF5FB"   # Survol ligne tableau
    SILVER          = "#BDC3C7"   # Bordures de tableaux, séparateurs
    CLOUDS          = "#ECF0F1"   # Zones neutres

    # ── Actions Primaires ────────────────────────────────────────────────────
    PRIMARY         = "#3498DB"   # Peter River — boutons Enregistrer/Rechercher
    PRIMARY_HOVER   = "#2980B9"   # Hover bouton primaire
    PRIMARY_LIGHT   = "#D6EAF8"   # Fond badge/tag primaire
    PRIMARY_TEXT    = "#FFFFFF"   # Texte sur fond primaire

    # ── Validation / Succès ──────────────────────────────────────────────────
    SUCCESS         = "#2ECC71"   # Emerald — stock entrant, conforme
    SUCCESS_DARK    = "#27AE60"   # Nephritis — hover succès
    SUCCESS_LIGHT   = "#D5F5E3"   # Fond badge succès
    SUCCESS_TEXT    = "#1E8449"   # Texte sur fond succès clair

    # ── Alertes / Danger ─────────────────────────────────────────────────────
    DANGER          = "#E74C3C"   # Alizarin — rupture stock, suppression
    DANGER_DARK     = "#C0392B"   # Pomegranate — hover danger
    DANGER_LIGHT    = "#FADBD8"   # Fond badge danger
    DANGER_TEXT     = "#922B21"   # Texte sur fond danger clair

    # ── Avertissement ────────────────────────────────────────────────────────
    WARNING         = "#F39C12"   # Orange — stock bas, commande en attente
    WARNING_LIGHT_C = "#F1C40F"   # Sun Flower (variante plus vive)
    WARNING_LIGHT   = "#FEF9E7"   # Fond badge avertissement
    WARNING_TEXT    = "#9A6A00"   # Texte sur fond warning clair

    # ── Information / Tech ───────────────────────────────────────────────────
    INFO            = "#1ABC9C"   # Turquoise — badges catégorie, stats
    INFO_DARK       = "#16A085"   # Green Sea — hover info
    INFO_LIGHT      = "#D1F2EB"   # Fond badge info
    INFO_TEXT       = "#0E6655"   # Texte sur fond info clair

    # ── Spécial / Premium ────────────────────────────────────────────────────
    PREMIUM         = "#9B59B6"   # Amethyst — Fournisseurs, export PDF
    PREMIUM_DARK    = "#8E44AD"   # Wisteria — hover premium
    PREMIUM_LIGHT   = "#F5EEF8"   # Fond badge premium
    PREMIUM_TEXT    = "#6C3483"   # Texte sur fond premium clair

    # ── Textes ───────────────────────────────────────────────────────────────
    TEXT_PRIMARY    = "#2C3E50"   # Texte principal (même que MIDNIGHT)
    TEXT_SECONDARY  = "#5D6D7E"   # Texte secondaire / labels
    TEXT_MUTED      = "#95A5A6"   # Texte discret / placeholders
    TEXT_ON_DARK    = "#FFFFFF"   # Texte sur fond sombre
    TEXT_ON_DARK_DIM= "#BDC3C7"   # Texte secondaire sur fond sombre

    # ── Bordures & Séparateurs ───────────────────────────────────────────────
    BORDER          = "#D5D8DC"   # Bordure standard
    BORDER_FOCUS    = "#3498DB"   # Bordure focus (= PRIMARY)
    BORDER_TABLE    = "#BDC3C7"   # Bordure tableau (= SILVER)
    DIVIDER         = "#E8EAED"   # Séparateur léger

    # ── États désactivés ─────────────────────────────────────────────────────
    DISABLED_BG     = "#EAECEE"
    DISABLED_FG     = "#AAB7B8"
    DISABLED_BORDER = "#D5D8DC"


# ─────────────────────────────────────────────────────────────────────────────
# 2. TYPOGRAPHIE — CHARGEMENT ET ACCÈS AUX POLICES ROBOTO
# ─────────────────────────────────────────────────────────────────────────────

class Fonts:
    """
    Gestion centralisée des polices Roboto.

    Appel unique au démarrage :
        Fonts.load()          # dans __init__ de la fenêtre principale

    Ensuite partout :
        Fonts.body()          # taille 12 normal
        Fonts.body(14)        # taille personnalisée
        Fonts.bold(13)        # bold
        Fonts.heading()       # 16 bold
        Fonts.title()         # 20 bold
        Fonts.small()         # 10 normal
        Fonts.label()         # 11 semi-lisible
        Fonts.sidebar()       # 13 medium pour sidebar
        Fonts.monospace()     # fallback Courier pour codes
    """

    _loaded: bool = False
    _family: str  = "Roboto"

    # Correspondance poids → fichier Roboto
    _WEIGHT_FILES = {
        "thin":        "Roboto-Thin.ttf",
        "extralight":  "Roboto-ExtraLight.ttf",
        "light":       "Roboto-Light.ttf",
        "regular":     "Roboto-Regular.ttf",
        "medium":      "Roboto-Medium.ttf",
        "semibold":    "Roboto-SemiBold.ttf",
        "bold":        "Roboto-Bold.ttf",
        "extrabold":   "Roboto-ExtraBold.ttf",
        "black":       "Roboto-Black.ttf",
    }

    @classmethod
    def _fonts_dir(cls) -> str:
        """Retourne le chemin absolu du dossier fonts/."""
        base = getattr(sys, "_MEIPASS", None) or os.path.dirname(
            os.path.abspath(__file__)
        )
        return os.path.join(base, "fonts")

    @classmethod
    def load(cls) -> bool:
        """
        Charge les fichiers TTF Roboto dans le système.
        À appeler UNE seule fois après la création de la fenêtre principale.
        Retourne True si au moins Regular a été chargé.
        """
        if cls._loaded:
            return True

        fonts_dir = cls._fonts_dir()
        if not os.path.isdir(fonts_dir):
            print(f"[Fonts] ⚠ Dossier fonts/ introuvable : {fonts_dir}")
            cls._family = "Segoe UI"
            cls._loaded = True
            return False

        loaded_count = 0

        # Chargement Windows (GDI)
        if os.name == "nt":
            try:
                from ctypes import windll
                for fname in cls._WEIGHT_FILES.values():
                    fpath = os.path.join(fonts_dir, fname)
                    if os.path.exists(fpath):
                        windll.gdi32.AddFontResourceExW(fpath, 0x10, 0)
                        loaded_count += 1
            except Exception as e:
                print(f"[Fonts] Avertissement GDI : {e}")

        # Chargement Linux via fontconfig (optionnel)
        elif sys.platform.startswith("linux"):
            try:
                import subprocess
                subprocess.run(["fc-cache", "-f", fonts_dir],
                               capture_output=True, timeout=5)
            except Exception:
                pass
            loaded_count = sum(
                1 for f in cls._WEIGHT_FILES.values()
                if os.path.exists(os.path.join(fonts_dir, f))
            )

        # macOS — les TTF sont trouvés automatiquement par Tk si dans ~/Library
        else:
            loaded_count = sum(
                1 for f in cls._WEIGHT_FILES.values()
                if os.path.exists(os.path.join(fonts_dir, f))
            )

        if loaded_count > 0:
            cls._family = "Roboto"
            print(f"[Fonts] ✓ {loaded_count} fichiers Roboto chargés.")
        else:
            cls._family = "Segoe UI"
            print("[Fonts] ⚠ Aucun fichier Roboto trouvé, fallback Segoe UI.")

        cls._loaded = True
        return loaded_count > 0

    # ── Constructeurs de polices ──────────────────────────────────────────────

    @classmethod
    def get(cls, size: int = 13, weight: str = "normal",
            italic: bool = False) -> ctk.CTkFont:
        """Constructeur générique."""
        return ctk.CTkFont(family=cls._family, size=size,
                           weight=weight, slant="italic" if italic else "roman")

    @classmethod
    def body(cls, size: int = 13) -> ctk.CTkFont:
        """Corps de texte standard."""
        return cls.get(size)

    @classmethod
    def medium(cls, size: int = 13) -> ctk.CTkFont:
        """Poids medium — sous-titres, valeurs importantes."""
        return cls.get(size, "normal")   # CTk n'expose pas "medium" nativement

    @classmethod
    def bold(cls, size: int = 13) -> ctk.CTkFont:
        """Texte gras — boutons, totaux, alertes."""
        return cls.get(size, "bold")

    @classmethod
    def label(cls, size: int = 13) -> ctk.CTkFont:
        """Étiquettes de champs, petits textes."""
        return cls.get(size)

    @classmethod
    def small(cls, size: int = 13) -> ctk.CTkFont:
        """Texte discret — footers, métadonnées."""
        return cls.get(size)

    @classmethod
    def heading(cls, size: int = 15) -> ctk.CTkFont:
        """Titre de section / card header."""
        return cls.get(size, "bold")

    @classmethod
    def title(cls, size: int = 18) -> ctk.CTkFont:
        """Grand titre de page."""
        return cls.get(size, "bold")

    @classmethod
    def sidebar(cls, size: int = 13) -> ctk.CTkFont:
        """Texte de la barre latérale."""
        return cls.get(size)

    @classmethod
    def sidebar_bold(cls, size: int = 13) -> ctk.CTkFont:
        """Item actif de la barre latérale."""
        return cls.get(size, "bold")

    @classmethod
    def table_header(cls, size: int = 13) -> ctk.CTkFont:
        """En-tête de colonne de tableau."""
        return cls.get(size, "bold")

    @classmethod
    def table_body(cls, size: int = 13) -> ctk.CTkFont:
        """Cellule de tableau."""
        return cls.get(size)

    @classmethod
    def badge(cls, size: int = 13) -> ctk.CTkFont:
        """Texte de badge/tag."""
        return cls.get(size, "bold")

    @classmethod
    def button(cls, size: int = 13) -> ctk.CTkFont:
        """Texte de bouton."""
        return cls.get(size, "bold")

    @classmethod
    def input(cls, size: int = 13) -> ctk.CTkFont:
        """Texte dans les champs de saisie."""
        return cls.get(size)

    @classmethod
    def tooltip(cls, size: int = 13) -> ctk.CTkFont:
        """Tooltip / aide contextuelle."""
        return cls.get(size, "normal", italic=True)

    @classmethod
    def monospace(cls, size: int = 13) -> ctk.CTkFont:
        """Codes, références, valeurs techniques."""
        return ctk.CTkFont(family="Courier New", size=size)


# ─────────────────────────────────────────────────────────────────────────────
# 3. THÈME GLOBAL — INITIALISATION CTK
# ─────────────────────────────────────────────────────────────────────────────

class Theme:
    """
    Initialise customtkinter et applique les réglages globaux.

    Usage :
        Theme.setup()                # avant de créer la fenêtre
        Theme.apply(root_window)     # après création de la fenêtre
    """

    @staticmethod
    def setup():
        """Configure customtkinter. À appeler avant toute création de widget."""
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

    @staticmethod
    def apply(window: ctk.CTk):
        """
        Applique le fond et charge les polices sur la fenêtre principale.
        À appeler dans __init__ après super().__init__().
        """
        window.configure(fg_color=Colors.BG_PAGE)
        Fonts.load()

    @staticmethod
    def apply_toplevel(window: ctk.CTkToplevel):
        """Même chose pour les fenêtres secondaires."""
        window.configure(fg_color=Colors.BG_PAGE)


# ─────────────────────────────────────────────────────────────────────────────
# 4. COMPOSANTS STYLISÉS PRÊTS À L'EMPLOI
# ─────────────────────────────────────────────────────────────────────────────

class styled:
    """
    Fabrique de widgets préconfigurés avec le thème iJeery.
    Tous les paramètres peuvent être surchargés via **kwargs.

    Exemple :
        btn = styled.button_primary(frame, text="Enregistrer",
                                    command=save, width=160)
        lbl = styled.label(frame, text="Quantité :", size=13)
        inp = styled.entry(frame, placeholder="ex: 100")
        card = styled.card(parent)
    """

    # ── Boutons ───────────────────────────────────────────────────────────────

    @staticmethod
    def button_primary(parent, text="", command=None, width=140,
                       height=30, icon="", **kwargs) -> ctk.CTkButton:
        """Bouton d'action principale — bleu Peter River."""
        return ctk.CTkButton(
            parent,
            text=f"{icon}  {text}".strip() if icon else text,
            command=command, width=width, height=height,
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
            text_color=Colors.TEXT_ON_DARK,
            font=Fonts.button(), corner_radius=8,
            **kwargs
        )

    @staticmethod
    def button_success(parent, text="", command=None, width=140,
                       height=30, icon="", **kwargs) -> ctk.CTkButton:
        """Bouton validation / enregistrement — vert Emerald."""
        return ctk.CTkButton(
            parent,
            text=f"{icon}  {text}".strip() if icon else text,
            command=command, width=width, height=height,
            fg_color=Colors.SUCCESS, hover_color=Colors.SUCCESS_DARK,
            text_color=Colors.TEXT_ON_DARK,
            font=Fonts.button(), corner_radius=8,
            **kwargs
        )

    @staticmethod
    def button_danger(parent, text="", command=None, width=140,
                      height=30, icon="", **kwargs) -> ctk.CTkButton:
        """Bouton suppression / danger — rouge Alizarin."""
        return ctk.CTkButton(
            parent,
            text=f"{icon}  {text}".strip() if icon else text,
            command=command, width=width, height=height,
            fg_color=Colors.DANGER, hover_color=Colors.DANGER_DARK,
            text_color=Colors.TEXT_ON_DARK,
            font=Fonts.button(), corner_radius=8,
            **kwargs
        )

    @staticmethod
    def button_warning(parent, text="", command=None, width=140,
                       height=30, icon="", **kwargs) -> ctk.CTkButton:
        """Bouton avertissement — orange."""
        return ctk.CTkButton(
            parent,
            text=f"{icon}  {text}".strip() if icon else text,
            command=command, width=width, height=height,
            fg_color=Colors.WARNING, hover_color="#D68910",
            text_color=Colors.TEXT_ON_DARK,
            font=Fonts.button(), corner_radius=8,
            **kwargs
        )

    @staticmethod
    def button_secondary(parent, text="", command=None, width=140,
                         height=30, icon="", **kwargs) -> ctk.CTkButton:
        """Bouton secondaire neutre — fond clair."""
        return ctk.CTkButton(
            parent,
            text=f"{icon}  {text}".strip() if icon else text,
            command=command, width=width, height=height,
            fg_color=Colors.CLOUDS, hover_color=Colors.SILVER,
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.button(), corner_radius=8,
            border_width=1, border_color=Colors.BORDER,
            **kwargs
        )

    @staticmethod
    def button_info(parent, text="", command=None, width=140,
                    height=30, icon="", **kwargs) -> ctk.CTkButton:
        """Bouton info / tech — Turquoise."""
        return ctk.CTkButton(
            parent,
            text=f"{icon}  {text}".strip() if icon else text,
            command=command, width=width, height=height,
            fg_color=Colors.INFO, hover_color=Colors.INFO_DARK,
            text_color=Colors.TEXT_ON_DARK,
            font=Fonts.button(), corner_radius=8,
            **kwargs
        )

    @staticmethod
    def button_premium(parent, text="", command=None, width=140,
                       height=30, icon="", **kwargs) -> ctk.CTkButton:
        """Bouton premium / export — Amethyst."""
        return ctk.CTkButton(
            parent,
            text=f"{icon}  {text}".strip() if icon else text,
            command=command, width=width, height=height,
            fg_color=Colors.PREMIUM, hover_color=Colors.PREMIUM_DARK,
            text_color=Colors.TEXT_ON_DARK,
            font=Fonts.button(), corner_radius=8,
            **kwargs
        )

    # ── Labels ────────────────────────────────────────────────────────────────

    @staticmethod
    def label(parent, text="", size=12, color=None,
              weight="normal", **kwargs) -> ctk.CTkLabel:
        """Label standard."""
        return ctk.CTkLabel(
            parent, text=text,
            font=Fonts.get(size, weight),
            text_color=color or Colors.TEXT_PRIMARY,
            **kwargs
        )

    @staticmethod
    def label_muted(parent, text="", size=11, **kwargs) -> ctk.CTkLabel:
        """Label discret — étiquettes de champs."""
        return ctk.CTkLabel(
            parent, text=text,
            font=Fonts.label(size),
            text_color=Colors.TEXT_MUTED,
            **kwargs
        )

    @staticmethod
    def label_heading(parent, text="", size=16, **kwargs) -> ctk.CTkLabel:
        """Titre de section."""
        return ctk.CTkLabel(
            parent, text=text,
            font=Fonts.heading(size),
            text_color=Colors.TEXT_PRIMARY,
            **kwargs
        )

    @staticmethod
    def label_title(parent, text="", size=20, **kwargs) -> ctk.CTkLabel:
        """Grand titre de page."""
        return ctk.CTkLabel(
            parent, text=text,
            font=Fonts.title(size),
            text_color=Colors.TEXT_PRIMARY,
            **kwargs
        )

    # ── Champs de saisie ─────────────────────────────────────────────────────

    @staticmethod
    def entry(parent, placeholder="", height=30,
              show=None, **kwargs) -> ctk.CTkEntry:
        """Champ de saisie standard."""
        kw = dict(
            height=height,
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            border_width=1,
            text_color=Colors.TEXT_PRIMARY,
            placeholder_text=placeholder,
            placeholder_text_color=Colors.TEXT_MUTED,
            font=Fonts.input(),
            corner_radius=8,
        )
        if show:
            kw["show"] = show
        kw.update(kwargs)
        e = ctk.CTkEntry(parent, **kw)
        # Focus coloré automatique
        e.bind("<FocusIn>",  lambda _: e.configure(border_color=Colors.BORDER_FOCUS))
        e.bind("<FocusOut>", lambda _: e.configure(border_color=Colors.BORDER))
        return e

    @staticmethod
    def date_entry(parent, width: int = 12, initial=None, **kwargs):
        """
        Sélecteur de date (dd/mm/yyyy) via tkcalendar.
        Retourne IjDatePicker : .get_date(), .set_date(), .get() → texte dd/mm/yyyy.
        """
        from date_picker_utils import IjDatePicker

        init = initial
        if init is None:
            from datetime import date as _d
            init = _d.today()
        picker = IjDatePicker(parent, width=width, initial=init, **kwargs)
        return picker

    @staticmethod
    def datetime_entry(parent, width: int = 11, initial=None, readonly_time: bool = False, **kwargs):
        """Date picker + champ heure (dd/mm/yyyy HH:MM:SS)."""
        from date_picker_utils import IjDateTimePicker
        from datetime import datetime as _dt

        init = initial if initial is not None else _dt.now()
        return IjDateTimePicker(
            parent, width=width, initial=init, readonly_time=readonly_time, **kwargs
        )

    @staticmethod
    def combobox(parent, values=None, command=None,
                 height=38, **kwargs) -> ctk.CTkComboBox:
        """ComboBox stylisée."""
        return ctk.CTkComboBox(
            parent,
            values=values or [],
            command=command,
            height=height,
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            border_width=1,
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.input(),
            corner_radius=8,
            button_color=Colors.PRIMARY,
            button_hover_color=Colors.PRIMARY_HOVER,
            dropdown_fg_color=Colors.BG_CARD,
            dropdown_text_color=Colors.TEXT_PRIMARY,
            dropdown_hover_color=Colors.BG_INPUT,
            dropdown_font=Fonts.body(),
            **kwargs
        )

    @staticmethod
    def textbox(parent, height=100, **kwargs) -> ctk.CTkTextbox:
        """Zone de texte multilignes."""
        return ctk.CTkTextbox(
            parent,
            height=height,
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            border_width=1,
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.input(),
            corner_radius=8,
            **kwargs
        )

    # ── Conteneurs ────────────────────────────────────────────────────────────

    @staticmethod
    def card(parent, padx=0, pady=0, **kwargs) -> ctk.CTkFrame:
        """Card blanche avec bordure et coins arrondis."""
        f = ctk.CTkFrame(
            parent,
            fg_color=Colors.BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=Colors.BORDER,
            **kwargs
        )
        if padx or pady:
            f.pack(padx=padx, pady=pady, fill="both", expand=True)
        return f

    @staticmethod
    def frame(parent, color=None, **kwargs) -> ctk.CTkFrame:
        """Frame transparente générique."""
        return ctk.CTkFrame(
            parent,
            fg_color=color or "transparent",
            **kwargs
        )

    @staticmethod
    def sidebar(parent, width=220, **kwargs) -> ctk.CTkFrame:
        """Barre latérale Midnight Blue."""
        return ctk.CTkFrame(
            parent,
            fg_color=Colors.BG_SIDEBAR,
            corner_radius=0,
            width=width,
            **kwargs
        )

    @staticmethod
    def divider(parent, vertical=False, **kwargs) -> ctk.CTkFrame:
        """Ligne de séparation."""
        if vertical:
            return ctk.CTkFrame(parent, width=1, fg_color=Colors.DIVIDER, **kwargs)
        return ctk.CTkFrame(parent, height=1, fg_color=Colors.DIVIDER, **kwargs)

    # ── Badges / Tags ─────────────────────────────────────────────────────────

    @staticmethod
    def badge(parent, text="", variant="primary", **kwargs) -> ctk.CTkLabel:
        """
        Badge coloré.
        variant: "primary" | "success" | "danger" | "warning" | "info" | "premium" | "neutral"
        """
        variants = {
            "primary": (Colors.PRIMARY_LIGHT,  Colors.PRIMARY),
            "success": (Colors.SUCCESS_LIGHT,  Colors.SUCCESS_TEXT),
            "danger":  (Colors.DANGER_LIGHT,   Colors.DANGER_TEXT),
            "warning": (Colors.WARNING_LIGHT,  Colors.WARNING_TEXT),
            "info":    (Colors.INFO_LIGHT,     Colors.INFO_TEXT),
            "premium": (Colors.PREMIUM_LIGHT,  Colors.PREMIUM_TEXT),
            "neutral": (Colors.CLOUDS,         Colors.TEXT_SECONDARY),
        }
        bg, fg = variants.get(variant, variants["neutral"])
        return ctk.CTkLabel(
            parent, text=f"  {text}  ",
            font=Fonts.badge(),
            fg_color=bg, text_color=fg,
            corner_radius=6,
            **kwargs
        )

    # ── Checkbox & Switch ─────────────────────────────────────────────────────

    @staticmethod
    def checkbox(parent, text="", variable=None,
                 command=None, **kwargs) -> ctk.CTkCheckBox:
        return ctk.CTkCheckBox(
            parent, text=text,
            variable=variable, command=command,
            font=Fonts.body(),
            text_color=Colors.TEXT_PRIMARY,
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            border_color=Colors.BORDER,
            checkmark_color=Colors.TEXT_ON_DARK,
            corner_radius=5,
            **kwargs
        )

    @staticmethod
    def switch(parent, text="", variable=None,
               command=None, **kwargs) -> ctk.CTkSwitch:
        return ctk.CTkSwitch(
            parent, text=text,
            variable=variable, command=command,
            font=Fonts.body(),
            text_color=Colors.TEXT_PRIMARY,
            progress_color=Colors.PRIMARY,
            button_color=Colors.BG_CARD,
            button_hover_color=Colors.CLOUDS,
            fg_color=Colors.SILVER,
            **kwargs
        )

    # ── Barre de progression ──────────────────────────────────────────────────

    @staticmethod
    def progressbar(parent, mode="determinate",
                    color=None, **kwargs) -> ctk.CTkProgressBar:
        return ctk.CTkProgressBar(
            parent, mode=mode,
            progress_color=color or Colors.PRIMARY,
            fg_color=Colors.BG_INPUT,
            height=8, corner_radius=4,
            **kwargs
        )

    # ── Scrollbar ─────────────────────────────────────────────────────────────

    @staticmethod
    def scrollable_frame(parent, **kwargs) -> ctk.CTkScrollableFrame:
        return ctk.CTkScrollableFrame(
            parent,
            fg_color="transparent",
            scrollbar_button_color=Colors.SILVER,
            scrollbar_button_hover_color=Colors.PRIMARY,
            **kwargs
        )


# ─────────────────────────────────────────────────────────────────────────────
# 5. HELPERS UTILITAIRES
# ─────────────────────────────────────────────────────────────────────────────

class ThemeUtils:
    """
    Utilitaires divers liés au thème.
    """

    @staticmethod
    def stock_status_color(qty: int, threshold_low: int = 5,
                           threshold_critical: int = 0) -> str:
        """
        Retourne une couleur selon le niveau de stock.
            qty == 0              → DANGER  (rupture)
            0 < qty <= threshold  → WARNING (stock bas)
            qty > threshold       → SUCCESS (conforme)
        """
        if qty <= threshold_critical:
            return Colors.DANGER
        elif qty <= threshold_low:
            return Colors.WARNING
        return Colors.SUCCESS

    @staticmethod
    def stock_badge_variant(qty: int, threshold_low: int = 5) -> str:
        """Retourne le variant badge selon le stock."""
        if qty <= 0:
            return "danger"
        elif qty <= threshold_low:
            return "warning"
        return "success"

    @staticmethod
    def order_status_color(status: str) -> str:
        """Couleur selon le statut d'une commande."""
        mapping = {
            "reçu":       Colors.SUCCESS,
            "en attente": Colors.WARNING,
            "annulé":     Colors.DANGER,
            "partiel":    Colors.INFO,
        }
        return mapping.get(status.lower(), Colors.TEXT_MUTED)

    @staticmethod
    def apply_entry_field(frame, label_text: str, value: str = "",
                          placeholder: str = "", show=None,
                          label_width: int = 140):
        """
        Crée une ligne label + entry dans un frame.
        Retourne l'entry créé.

        Usage :
            entry = ThemeUtils.apply_entry_field(
                frame, "Désignation :", value=article.nom
            )
        """
        row = styled.frame(frame)
        row.pack(fill="x", pady=(0, 8))

        styled.label_muted(row, text=label_text, anchor="w",
                           width=label_width).pack(side="left")

        e = styled.entry(row, placeholder=placeholder, show=show)
        e.pack(side="left", fill="x", expand=True)
        if value:
            e.insert(0, value)
        return e


# ─────────────────────────────────────────────────────────────────────────────
# 6. CONSTANTES DE MISE EN PAGE
# ─────────────────────────────────────────────────────────────────────────────

class Layout:
    """Constantes d'espacement et de dimensions réutilisables."""

    # Paddings intérieurs de card
    CARD_PADX       = 24
    CARD_PADY_TOP   = 20
    CARD_PADY_BOT   = 20

    # Espacements entre sections
    SECTION_GAP     = 16
    FIELD_GAP       = 8    # Entre deux champs consécutifs
    LABEL_GAP       = 4    # Entre label et son champ

    # Largeurs
    SIDEBAR_W       = 220
    LABEL_W         = 140  # Largeur standard d'un label de formulaire

    # Hauteurs des widgets
    BTN_H           = 38
    BTN_H_LG        = 44
    INPUT_H         = 38
    INPUT_H_SM      = 32
    ROW_H           = 36   # Hauteur ligne tableau

    # Rayons
    RADIUS          = 8
    RADIUS_LG       = 12
    RADIUS_SM       = 5


# ─────────────────────────────────────────────────────────────────────────────
# 7. POINT D'ENTRÉE — INITIALISATION GLOBALE
# ─────────────────────────────────────────────────────────────────────────────

def init_theme():
    """
    Raccourci d'initialisation globale.
    À appeler AVANT de créer la moindre fenêtre.

    Usage :
        from app_theme import init_theme
        init_theme()

        root = MyApp()
        root.mainloop()
    """
    Theme.setup()


# ─────────────────────────────────────────────────────────────────────────────
# 8. DÉMONSTRATION (exécution directe)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_theme()

    demo = ctk.CTk()
    demo.title("iJeery — Aperçu du thème")
    demo.geometry("820x640")
    Theme.apply(demo)

    scroll = styled.scrollable_frame(demo)
    scroll.pack(fill="both", expand=True, padx=20, pady=20)

    # ── Titre ────────────────────────────────────────────────────────────────
    styled.label_title(scroll, text="iJeery — Aperçu du thème").pack(anchor="w", pady=(0, 4))
    styled.label_muted(scroll, text="Toutes les couleurs, polices et composants disponibles.").pack(anchor="w", pady=(0, 16))
    styled.divider(scroll).pack(fill="x", pady=(0, 20))

    # ── Boutons ───────────────────────────────────────────────────────────────
    styled.label_heading(scroll, text="Boutons", size=14).pack(anchor="w", pady=(0, 10))
    btn_row = styled.frame(scroll)
    btn_row.pack(fill="x", pady=(0, 20))
    styled.button_primary(btn_row,  text="Enregistrer", icon="💾").pack(side="left", padx=(0, 8))
    styled.button_success(btn_row,  text="Valider",     icon="✔").pack(side="left", padx=(0, 8))
    styled.button_danger(btn_row,   text="Supprimer",   icon="🗑").pack(side="left", padx=(0, 8))
    styled.button_warning(btn_row,  text="Attention",   icon="⚠").pack(side="left", padx=(0, 8))
    styled.button_info(btn_row,     text="Filtrer",     icon="🔍").pack(side="left", padx=(0, 8))
    styled.button_premium(btn_row,  text="Exporter PDF",icon="📄").pack(side="left", padx=(0, 8))
    styled.button_secondary(btn_row,text="Annuler",     icon="✕").pack(side="left")

    styled.divider(scroll).pack(fill="x", pady=(0, 20))

    # ── Badges ────────────────────────────────────────────────────────────────
    styled.label_heading(scroll, text="Badges / Tags", size=14).pack(anchor="w", pady=(0, 10))
    badge_row = styled.frame(scroll)
    badge_row.pack(fill="x", pady=(0, 20))
    for variant, text in [("primary","Recherche"), ("success","Reçu"),
                           ("danger","Rupture"), ("warning","Stock bas"),
                           ("info","Catégorie"), ("premium","Fournisseur"),
                           ("neutral","Archivé")]:
        styled.badge(badge_row, text=text, variant=variant).pack(side="left", padx=(0, 8))

    styled.divider(scroll).pack(fill="x", pady=(0, 20))

    # ── Champs ────────────────────────────────────────────────────────────────
    styled.label_heading(scroll, text="Champs de saisie", size=14).pack(anchor="w", pady=(0, 10))
    card = styled.card(scroll)
    card.pack(fill="x", pady=(0, 20), ipady=12, ipadx=16)
    styled.label_muted(card, text="📦  Désignation article", anchor="w").pack(fill="x", padx=16, pady=(12, 3))
    styled.entry(card, placeholder="ex: Huile moteur 5W40").pack(fill="x", padx=16, pady=(0, 8))
    styled.label_muted(card, text="🔢  Quantité en stock", anchor="w").pack(fill="x", padx=16, pady=(0, 3))
    styled.entry(card, placeholder="ex: 150").pack(fill="x", padx=16, pady=(0, 12))

    styled.divider(scroll).pack(fill="x", pady=(0, 20))

    # ── Statut stock ──────────────────────────────────────────────────────────
    styled.label_heading(scroll, text="Couleurs de statut stock", size=14).pack(anchor="w", pady=(0, 10))
    stock_row = styled.frame(scroll)
    stock_row.pack(fill="x", pady=(0, 20))
    for qty, label in [(0,"Rupture (0)"), (3,"Stock bas (3)"), (42,"Conforme (42)")]:
        col = ThemeUtils.stock_status_color(qty)
        ctk.CTkLabel(stock_row, text=f"  {label}  ",
                     fg_color=col, text_color="white",
                     font=Fonts.bold(12), corner_radius=8).pack(side="left", padx=(0, 10))

    # ── Palette complète ──────────────────────────────────────────────────────
    styled.divider(scroll).pack(fill="x", pady=(0, 20))
    styled.label_heading(scroll, text="Palette complète", size=14).pack(anchor="w", pady=(0, 10))
    palette_frame = styled.frame(scroll)
    palette_frame.pack(fill="x", pady=(0, 20))
    palette = [
        (Colors.MIDNIGHT, "Midnight"), (Colors.PRIMARY, "Primary"),
        (Colors.SUCCESS, "Success"),   (Colors.DANGER, "Danger"),
        (Colors.WARNING, "Warning"),   (Colors.INFO, "Info"),
        (Colors.PREMIUM, "Premium"),   (Colors.SILVER, "Silver"),
    ]
    for color, name in palette:
        ctk.CTkLabel(palette_frame, text=f"  {name}\n  {color}  ",
                     fg_color=color,
                     text_color="white" if name not in ("Silver",) else Colors.MIDNIGHT,
                     font=Fonts.small(10), corner_radius=8,
                     width=90, height=52).pack(side="left", padx=(0, 8))

    demo.mainloop()
    
