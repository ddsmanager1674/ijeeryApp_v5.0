# -*- coding: utf-8 -*-
"""Dialogs CustomTkinter partagés (vente, avoir, commandes, mouvements)."""

import customtkinter as ctk

from app_theme import Colors, Fonts, styled


def _center_window(win, width: int, height: int):
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = (sw // 2) - (width // 2)
    y = (sh // 2) - (height // 2)
    win.geometry(f"{width}x{height}+{x}+{y}")


class PasswordDialog(ctk.CTkToplevel):
    """Dialogue modal pour code d'autorisation (remise, avoir…)."""

    def __init__(self, title: str, text: str):
        super().__init__()
        self.title(title)
        self.geometry("320x160")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_CARD)
        self.result = None
        _center_window(self, 320, 160)

        ctk.CTkLabel(self, text=text, font=Fonts.body(12),
                     text_color=Colors.TEXT_PRIMARY).pack(pady=(18, 6), padx=20)

        self.entry = ctk.CTkEntry(self, show="*", font=Fonts.input(13),
                                  fg_color=Colors.BG_INPUT,
                                  border_color=Colors.BORDER, height=36)
        self.entry.pack(pady=(0, 10), padx=20, fill="x")
        self.entry.focus_set()
        self.entry.bind("<Return>", lambda _e: self._ok())

        styled.button_primary(self, text="Valider", command=self._ok,
                              width=120, height=36).pack(pady=(0, 14))
        self.grab_set()
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.wait_window()

    def _ok(self):
        self.result = self.entry.get()
        self.destroy()


class ErrorDialog(ctk.CTkToplevel):
    """Dialogue d'erreur centré."""

    def __init__(self, title: str, message: str):
        super().__init__()
        self.title(title)
        self.geometry("350x150")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_CARD)
        _center_window(self, 350, 150)

        ctk.CTkLabel(self, text=message, font=Fonts.body(12),
                     text_color=Colors.TEXT_PRIMARY, wraplength=300).pack(pady=(20, 10), padx=20)

        styled.button_danger(self, text="OK", command=self.destroy,
                             width=100, height=36).pack(pady=(0, 14))
        self.grab_set()
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.wait_window()


class MessageDialog(ctk.CTkToplevel):
    """Remplace messagebox showinfo/warning/error."""

    def __init__(self, title: str, message: str, type_: str = "info"):
        super().__init__()
        self.title(title)
        self.geometry("400x180")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_CARD)
        _center_window(self, 400, 200)

        icon_text = "ℹ️" if type_ == "info" else "⚠️" if type_ == "warning" else "❌"
        icon_color = (
            Colors.PRIMARY if type_ == "info"
            else Colors.WARNING if type_ == "warning"
            else Colors.DANGER
        )

        ctk.CTkLabel(self, text=icon_text, font=Fonts.heading(24),
                     text_color=icon_color).pack(pady=(20, 5))

        ctk.CTkLabel(self, text=message, font=Fonts.body(12),
                     text_color=Colors.TEXT_PRIMARY, wraplength=350,
                     justify="center").pack(pady=(0, 20), padx=20)

        styled.button_success(self, text="OK", command=self.destroy,
                              width=100, height=36).pack(pady=(0, 14))

        self.grab_set()
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.wait_window()


class YesNoDialog(ctk.CTkToplevel):
    """Remplace messagebox askyesno."""

    def __init__(self, title: str, message: str):
        super().__init__()
        self.title(title)
        self.geometry("400x180")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_CARD)
        self.result = False
        _center_window(self, 400, 180)

        ctk.CTkLabel(self, text="❓", font=Fonts.heading(24),
                     text_color=Colors.WARNING).pack(pady=(20, 5))

        ctk.CTkLabel(self, text=message, font=Fonts.body(12),
                     text_color=Colors.TEXT_PRIMARY, wraplength=350,
                     justify="center").pack(pady=(0, 20), padx=20)

        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(pady=(0, 14))
        styled.button_danger(bf, text="Non", command=self._no,
                             width=100, height=36).pack(side="left", padx=10)
        styled.button_success(bf, text="Oui", command=self._yes,
                              width=100, height=36).pack(side="right", padx=10)

        self.grab_set()
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.wait_window()

    def _yes(self):
        self.result = True
        self.destroy()

    def _no(self):
        self.result = False
        self.destroy()


class SimpleDialogWithChoice(ctk.CTkToplevel):
    """Choix format impression A5 ou ticket 80 mm."""

    def __init__(self, master, title: str, message: str):
        super().__init__(master)
        self.title(title)
        self.configure(fg_color=Colors.BG_CARD)
        self.transient(master)
        self.grab_set()
        self.result = None
        self.choice = ctk.StringVar(self, value="A5 PDF (Paysage)")

        ctk.CTkLabel(self, text=message, wraplength=350,
                     font=Fonts.body(12), text_color=Colors.TEXT_PRIMARY,
                     justify="left").pack(pady=12, padx=20)

        rf = ctk.CTkFrame(self, fg_color=Colors.BG_INPUT, corner_radius=8)
        rf.pack(pady=4, padx=20, fill="x")

        ctk.CTkRadioButton(rf, text="A5 PDF (Paysage)",
                           variable=self.choice, value="A5 PDF (Paysage)",
                           font=Fonts.body(12),
                           text_color=Colors.TEXT_PRIMARY).pack(pady=6, padx=12, anchor="w")
        ctk.CTkRadioButton(rf, text="Ticket de Caisse 80 mm",
                           variable=self.choice, value="Ticket 80mm",
                           font=Fonts.body(12),
                           text_color=Colors.TEXT_PRIMARY).pack(pady=6, padx=12, anchor="w")

        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(pady=12, padx=20)
        styled.button_danger(bf, text="Annuler", command=self._cancel,
                             width=120).pack(side="left", padx=6)
        styled.button_success(bf, text="Imprimer", command=self._ok,
                              width=120).pack(side="right", padx=6)

        self.wait_window(self)

    def _ok(self):
        self.result = self.choice.get()
        self.grab_release()
        self.destroy()

    def _cancel(self):
        self.result = None
        self.grab_release()
        self.destroy()
