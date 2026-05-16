# -*- coding: utf-8 -*-
"""Journal fichier unique pour la production (ijeery_app.log)."""

from __future__ import annotations

import logging
import os
import sys
import threading
import traceback
from datetime import datetime
from typing import Optional, TextIO

_LOG_FILENAME = "ijeery_app.log"
_MAX_BYTES = 5 * 1024 * 1024
_initialized = False
_lock = threading.Lock()
_log_path: Optional[str] = None
_orig_excepthook = None
_stdio_wrappers: list = []


def _writable_root() -> str:
    try:
        from resource_utils import application_writable_root
        return application_writable_root()
    except Exception:
        if getattr(sys, "frozen", False):
            return os.path.dirname(os.path.abspath(sys.executable))
        return os.path.dirname(os.path.abspath(__file__))


def get_log_path() -> str:
    global _log_path
    if _log_path is None:
        _log_path = os.path.join(_writable_root(), _LOG_FILENAME)
    return _log_path


def _maybe_rotate(path: str) -> None:
    try:
        if os.path.isfile(path) and os.path.getsize(path) > _MAX_BYTES:
            backup = path + ".1"
            if os.path.isfile(backup):
                os.remove(backup)
            os.replace(path, backup)
    except OSError:
        pass


class _StreamToLogger:
    """Redirige stdout/stderr vers le logger fichier."""

    def __init__(self, level: int, original: TextIO):
        self._level = level
        self._original = original

    def write(self, message: str) -> None:
        if message and message.strip():
            logging.getLogger("ijeery").log(self._level, message.rstrip("\n"))
        try:
            self._original.write(message)
        except Exception:
            pass

    def flush(self) -> None:
        try:
            self._original.flush()
        except Exception:
            pass

    def isatty(self) -> bool:
        return False


def _setup_file_logger() -> logging.Logger:
    path = get_log_path()
    _maybe_rotate(path)
    root = logging.getLogger("ijeery")
    root.setLevel(logging.DEBUG)
    root.handlers.clear()
    handler = logging.FileHandler(path, encoding="utf-8", mode="a")
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.addHandler(handler)
    return root


def _excepthook(exc_type, exc_value, exc_tb):
    log_exception(exc_value, context="Uncaught exception")
    if _orig_excepthook:
        _orig_excepthook(exc_type, exc_value, exc_tb)


def init_runtime_log(*, redirect_stdio: Optional[bool] = None) -> str:
    """
    Initialise le journal (idempotent).
    redirect_stdio: True en EXE par défaut, False en dev sauf IJEERY_LOG_STDIO=1.
    """
    global _initialized, _orig_excepthook
    with _lock:
        if _initialized:
            return get_log_path()

        if redirect_stdio is None:
            redirect_stdio = bool(
                getattr(sys, "frozen", False)
                or os.environ.get("IJEERY_LOG_STDIO", "").strip() in ("1", "true", "yes")
            )

        logger = _setup_file_logger()
        _orig_excepthook = sys.excepthook
        sys.excepthook = _excepthook

        if redirect_stdio and sys.stdout and sys.stderr:
            if not isinstance(sys.stdout, _StreamToLogger):
                sys.stdout = _StreamToLogger(logging.INFO, sys.stdout)
            if not isinstance(sys.stderr, _StreamToLogger):
                sys.stderr = _StreamToLogger(logging.ERROR, sys.stderr)

        _initialized = True
        logger.info(
            "=== iJeery démarré | frozen=%s | exe=%s | cwd=%s | log=%s ===",
            getattr(sys, "frozen", False),
            sys.executable,
            os.getcwd(),
            get_log_path(),
        )
        return get_log_path()


def log_info(message: str, *args) -> None:
    logging.getLogger("ijeery").info(message, *args)


def log_warning(message: str, *args) -> None:
    logging.getLogger("ijeery").warning(message, *args)


def log_error(message: str, *args) -> None:
    logging.getLogger("ijeery").error(message, *args)


def log_exception(exc: BaseException, *, context: str = "") -> None:
    prefix = f"{context}: " if context else ""
    logging.getLogger("ijeery").error(
        "%s%s\n%s",
        prefix,
        exc,
        "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
    )
