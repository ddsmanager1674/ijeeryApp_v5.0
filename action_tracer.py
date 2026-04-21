from datetime import datetime
from functools import wraps
from typing import Any, Callable, Optional

from log_utils import AppLogger


ACTION_KEYWORDS = (
    "add", "ajout", "create", "creer", "save", "enregistrer",
    "update", "modify", "modifier", "edit",
    "delete", "remove", "supprimer", "annuler",
    "valider", "validate", "payer", "payment", "paiement",
    "export", "imprimer", "print", "import",
)


def _safe_get_text(widget: Any) -> str:
    try:
        if hasattr(widget, "get"):
            value = widget.get()
            return str(value).strip()
    except Exception:
        pass
    return ""


def _infer_action_label(method_name: str) -> str:
    n = method_name.lower()
    if any(k in n for k in ("delete", "remove", "supprimer", "annuler")):
        return "Suppression/Annulation"
    if any(k in n for k in ("modify", "update", "edit", "modifier")):
        return "Modification"
    if any(k in n for k in ("add", "ajout", "create", "creer", "save", "enregistrer")):
        return "Création/Enregistrement"
    if any(k in n for k in ("export", "imprimer", "print", "import")):
        return "Export/Impression"
    if any(k in n for k in ("paiement", "payment", "payer")):
        return "Paiement"
    if any(k in n for k in ("valider", "validate")):
        return "Validation"
    return "Action utilisateur"


def _extract_context(instance: Any) -> tuple[str, str, str]:
    candidates = [
        "entry_designation", "designationmag_entry", "nomCli_entry", "nomFrs_entry",
        "entry_client", "entry_ref", "entry_reference", "entry_search",
    ]
    amount_candidates = [
        "entry_montant", "credit_entry", "entry_total", "entry_qte", "entry_prix",
    ]
    id_candidates = [
        "selected_article", "selected_cli_id", "selected_frs_id",
        "selected_mag_id", "iduser", "id_user_connecte",
    ]

    element = ""
    for attr in candidates:
        if hasattr(instance, attr):
            element = _safe_get_text(getattr(instance, attr))
            if element:
                break
    if not element:
        for attr in id_candidates:
            if hasattr(instance, attr):
                value = getattr(instance, attr)
                if value is not None and value != "":
                    element = f"{attr}={value}"
                    break
    if not element:
        element = instance.__class__.__name__

    value = ""
    for attr in amount_candidates:
        if hasattr(instance, attr):
            value = _safe_get_text(getattr(instance, attr))
            if value:
                value = f"{attr}={value}"
                break
    if not value:
        value = "aucune valeur"

    details = f"page={instance.__class__.__name__}"
    return element, details, value


def _should_trace_method(name: str, fn: Callable) -> bool:
    lname = name.lower()
    if lname.startswith("__"):
        return False
    if lname.startswith("_"):
        return False
    if "log" in lname:
        return False
    if any(k in lname for k in ACTION_KEYWORDS):
        return True
    return False


def _wrap_method(instance: Any, method_name: str, fn: Callable, logger: AppLogger):
    @wraps(fn)
    def _wrapped(*args, **kwargs):
        action = _infer_action_label(method_name)
        element, details, value = _extract_context(instance)
        started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            result = fn(*args, **kwargs)
            logger.log(
                action=action,
                element=element,
                details=f"{details}, méthode={method_name}, statut=succès, ts={started}",
                value=value,
            )
            return result
        except Exception as exc:
            logger.log(
                action=f"{action} (échouée)",
                element=element,
                details=f"{details}, méthode={method_name}, erreur={type(exc).__name__}",
                value=str(exc),
            )
            raise

    setattr(instance, method_name, _wrapped)


def enable_action_logging(instance: Any, session_data: Optional[dict] = None, fallback_user_id: Optional[int] = None):
    """Active un traçage auto des méthodes d'action pour une page."""
    logger = AppLogger(
        conn=getattr(instance, "conn", None),
        session_data=session_data or getattr(instance, "session_data", {}) or {},
        fallback_user_id=fallback_user_id,
    )
    if getattr(instance, "_action_logging_enabled", False):
        return

    for name in dir(instance):
        if name.startswith("__"):
            continue
        try:
            fn = getattr(instance, name)
        except Exception:
            continue
        if not callable(fn):
            continue
        if not _should_trace_method(name, fn):
            continue
        try:
            _wrap_method(instance, name, fn, logger)
        except Exception:
            continue

    setattr(instance, "_action_logging_enabled", True)
