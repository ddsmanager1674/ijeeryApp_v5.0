# -*- coding: utf-8 -*-
"""
Datepicker iJeery — format affichage dd/MM/yyyy (tkcalendar).
Helpers de lecture/écriture compatibles CTkEntry et DateEntry.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional, Union

import customtkinter as ctk

try:
    from tkcalendar import DateEntry as TkDateEntry
except ImportError:
    TkDateEntry = None  # type: ignore

try:
    from app_theme import Colors, Fonts
except ImportError:
    class Colors:  # type: ignore
        PRIMARY = "#3498DB"
        PRIMARY_HOVER = "#2980B9"
        TEXT_ON_DARK = "#FFFFFF"
        TEXT_PRIMARY = "#2C3E50"
        BG_INPUT = "#F4F6F8"
        BORDER = "#D5D8DC"

    class Fonts:  # type: ignore
        @staticmethod
        def body(size=11):
            return ("Segoe UI", size)


DATE_PATTERN = "dd/mm/yyyy"
DATE_FMT_DISPLAY = "%d/%m/%Y"
DATE_FMT_ISO = "%Y-%m-%d"
DATETIME_FMT_DISPLAY = "%d/%m/%Y %H:%M:%S"


def parse_date(value: Any, default: Optional[date] = None) -> Optional[date]:
    """Parse une date saisie (dd/mm/yyyy, yyyy-mm-dd, date/datetime)."""
    if value is None or value == "":
        return default
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if not s:
        return default
    for fmt in (
        DATE_FMT_DISPLAY,
        "%d/%m/%y",
        DATE_FMT_ISO,
        "%Y/%m/%d",
        "%d-%m-%Y",
    ):
        try:
            return datetime.strptime(s[:10] if len(s) > 10 and fmt == DATE_FMT_ISO else s, fmt).date()
        except ValueError:
            continue
    # datetime complet dd/mm/yyyy HH:MM:SS
    try:
        return datetime.strptime(s, DATETIME_FMT_DISPLAY).date()
    except ValueError:
        pass
    try:
        return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S").date()
    except ValueError:
        pass
    return default


def parse_datetime(value: Any, default: Optional[datetime] = None) -> Optional[datetime]:
    if value is None or value == "":
        return default
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.now().time().replace(microsecond=0))
    s = str(value).strip()
    if not s:
        return default
    for fmt in (DATETIME_FMT_DISPLAY, "%d/%m/%Y %H:%M", DATE_FMT_ISO + " %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    d = parse_date(s)
    if d:
        return datetime.combine(d, datetime.min.time())
    return default


def format_date_fr(d: Union[date, datetime, None]) -> str:
    if d is None:
        return ""
    if isinstance(d, datetime):
        d = d.date()
    return d.strftime(DATE_FMT_DISPLAY)


def format_date_iso(d: Union[date, datetime, None]) -> str:
    if d is None:
        return ""
    if isinstance(d, datetime):
        d = d.date()
    return d.strftime(DATE_FMT_ISO)


def format_datetime_fr(d: Union[date, datetime, None]) -> str:
    if d is None:
        return ""
    if isinstance(d, date):
        return datetime.combine(d, datetime.now().time().replace(microsecond=0)).strftime(
            DATETIME_FMT_DISPLAY
        )
    return d.strftime(DATETIME_FMT_DISPLAY)


def default_date_entry_kwargs() -> dict:
    return dict(
        width=12,
        date_pattern=DATE_PATTERN,
        background=Colors.PRIMARY,
        foreground=Colors.TEXT_ON_DARK,
        borderwidth=1,
        selectbackground=Colors.PRIMARY_HOVER,
        selectforeground=Colors.TEXT_ON_DARK,
        normalbackground=Colors.BG_INPUT,
        normalforeground=Colors.TEXT_PRIMARY,
    )


def make_tk_date_entry(parent, width: int = 12, **kwargs) -> Any:
    """Crée un tkcalendar.DateEntry (dd/mm/yyyy)."""
    if TkDateEntry is None:
        raise RuntimeError("tkcalendar n'est pas installé (pip install tkcalendar).")
    kw = default_date_entry_kwargs()
    kw["width"] = width
    kw.update(kwargs)
    return TkDateEntry(parent, **kw)


def get_date_from_widget(widget: Any) -> Optional[date]:
    if widget is None:
        return None
    inner = getattr(widget, "_date_widget", None) or widget
    if hasattr(inner, "get_date"):
        try:
            return inner.get_date()
        except Exception:
            pass
    if hasattr(widget, "get_date"):
        try:
            return widget.get_date()
        except Exception:
            pass
    if hasattr(inner, "get"):
        return parse_date(inner.get())
    return None


def set_date_on_widget(widget: Any, value: Union[date, datetime, str, None]) -> None:
    if widget is None:
        return
    d = parse_date(value)
    if d is None:
        return
    inner = getattr(widget, "_date_widget", None) or widget
    if hasattr(inner, "set_date"):
        try:
            inner.set_date(d)
            return
        except Exception:
            pass
    if hasattr(widget, "set_date"):
        try:
            widget.set_date(d)
            return
        except Exception:
            pass
    if hasattr(inner, "set"):
        inner.set(format_date_fr(d))
    elif hasattr(inner, "delete") and hasattr(inner, "insert"):
        inner.delete(0, "end")
        inner.insert(0, format_date_fr(d))


def get_date_text_from_widget(widget: Any) -> str:
    d = get_date_from_widget(widget)
    return format_date_fr(d) if d else ""


def get_iso_date_from_widget(widget: Any) -> str:
    d = get_date_from_widget(widget)
    return format_date_iso(d) if d else ""


class IjDatePicker(ctk.CTkFrame):
    """
    Conteneur CTk pour un DateEntry tkcalendar.
    API : get_date(), set_date(), get() → texte dd/mm/yyyy.
    """

    def __init__(
        self,
        parent,
        width: int = 12,
        initial: Union[date, datetime, str, None] = None,
        **dateentry_kwargs,
    ):
        super().__init__(parent, fg_color="transparent")
        self._date_widget = make_tk_date_entry(self, width=width, **dateentry_kwargs)
        self._date_widget.pack(fill="x", expand=True)
        if initial is not None:
            set_date_on_widget(self, initial)
        elif TkDateEntry is not None:
            set_date_on_widget(self, date.today())

    def get_date(self) -> date:
        d = get_date_from_widget(self)
        return d or date.today()

    def set_date(self, value: Union[date, datetime, str, None]) -> None:
        set_date_on_widget(self, value)

    def get(self) -> str:
        return get_date_text_from_widget(self)

    def set(self, value: str) -> None:
        set_date_on_widget(self, value)


class IjDateTimePicker(ctk.CTkFrame):
    """Date (picker) + heure (HH:MM:SS) — affichage dd/mm/yyyy HH:MM:SS."""

    def __init__(
        self,
        parent,
        width: int = 11,
        initial: Union[datetime, str, None] = None,
        readonly_time: bool = False,
        **dateentry_kwargs,
    ):
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)

        dt = parse_datetime(initial) or datetime.now()
        self._date_picker = IjDatePicker(self, width=width, initial=dt.date(), **dateentry_kwargs)
        self._date_picker.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self._time_entry = ctk.CTkEntry(
            self,
            width=72,
            height=28,
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            font=Fonts.body(11) if callable(getattr(Fonts, "body", None)) else ("Segoe UI", 11),
            corner_radius=8,
            placeholder_text="HH:MM:SS",
        )
        self._time_entry.grid(row=0, column=1, sticky="e")
        self._time_entry.insert(0, dt.strftime("%H:%M:%S"))
        if readonly_time:
            self._time_entry.configure(state="readonly")

    def get_datetime(self) -> datetime:
        d = self._date_picker.get_date()
        t_s = (self._time_entry.get() or "00:00:00").strip()
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                t = datetime.strptime(t_s, fmt).time()
                return datetime.combine(d, t)
            except ValueError:
                continue
        return datetime.combine(d, datetime.min.time())

    def get(self) -> str:
        return self.get_datetime().strftime(DATETIME_FMT_DISPLAY)

    def set_datetime(self, value: Union[datetime, str, None]) -> None:
        dt = parse_datetime(value) or datetime.now()
        self._date_picker.set_date(dt.date())
        try:
            st = self._time_entry.cget("state")
            self._time_entry.configure(state="normal")
            self._time_entry.delete(0, "end")
            self._time_entry.insert(0, dt.strftime("%H:%M:%S"))
            self._time_entry.configure(state=st)
        except Exception:
            self._time_entry.delete(0, "end")
            self._time_entry.insert(0, dt.strftime("%H:%M:%S"))
