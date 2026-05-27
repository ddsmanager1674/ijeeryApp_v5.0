# -*- coding: utf-8 -*-
"""Icône application iJeery — barre des tâches et barre de titre."""

from __future__ import annotations

import os
import sys
from typing import Any, Optional

try:
    from resource_utils import get_bundle_path
except ImportError:
    def get_bundle_path(relative_path: str) -> str:
        try:
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, relative_path)


APP_ICON_REL = os.path.join("icons", "iconeIjeery.ico")
_WINDOWS_APP_ID = "ijeery.application.v5.0"

_hooks_installed = False


def get_app_icon_path() -> Optional[str]:
    """Chemin absolu vers icons/iconeIjeery.ico (bundle PyInstaller ou dev)."""
    candidates = (
        get_bundle_path(APP_ICON_REL),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), APP_ICON_REL),
    )
    for path in candidates:
        if path and os.path.isfile(path):
            return os.path.abspath(path)
    return None


def init_windows_taskbar_app_id(app_id: str = _WINDOWS_APP_ID) -> None:
    """Icône correcte dans la barre des tâches Windows (AppUserModelID)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass


def apply_window_icon(window: Any, *, delay_ms: int = 0) -> None:
    """Applique iconeIjeery.ico sur une fenêtre Tk / CustomTkinter."""
    path = get_app_icon_path()
    if not path:
        return

    def _apply() -> None:
        for fn in (
            lambda: window.iconbitmap(default=path),
            lambda: window.wm_iconbitmap(default=path),
            lambda: window.iconbitmap(path),
        ):
            try:
                fn()
                return
            except Exception:
                continue
        try:
            from PIL import Image, ImageTk
            img = Image.open(path)
            photo = ImageTk.PhotoImage(img)
            window._ijeery_icon_photo = photo
            window.iconphoto(True, photo)
        except Exception:
            pass

    if delay_ms > 0 and hasattr(window, "after"):
        try:
            window.after(delay_ms, _apply)
            return
        except Exception:
            pass
    _apply()


def _patch_ctk_class(cls: type) -> None:
    if getattr(cls, "_ijeery_icon_patched", False):
        return
    original_init = cls.__init__

    def __init__(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        apply_window_icon(self, delay_ms=50)

    cls.__init__ = __init__
    cls._ijeery_icon_patched = True


def install_ctk_icon_hooks() -> None:
    """Applique l'icône à toutes les CTk / CTkToplevel créées ensuite."""
    global _hooks_installed
    if _hooks_installed:
        return
    try:
        import customtkinter as ctk
        _patch_ctk_class(ctk.CTk)
        _patch_ctk_class(ctk.CTkToplevel)
    except Exception:
        pass
    _hooks_installed = True


def init_app_icon() -> None:
    """À appeler une fois au démarrage (avant toute fenêtre)."""
    init_windows_taskbar_app_id()
    install_ctk_icon_hooks()
