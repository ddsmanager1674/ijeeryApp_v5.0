# -*- coding: utf-8 -*-

def _coerce_number(val):
    try:
        if val is None:
            return 0.0
        return float(val)
    except Exception:
        return None


def format_entier(val):
    """Formate un nombre en entier naturel avec separateur '.' (affichage uniquement)."""
    n = _coerce_number(val)
    if n is None:
        return str(val)
    n = int(round(n))
    return f"{n:,}".replace(",", ".")


def format_nombre(val, decimales=2):
    """Formate un nombre avec separateur de millier '.' et decimal ','.

    decimales=0 -> entier sans virgule.
    """
    n = _coerce_number(val)
    if n is None:
        return str(val)
    if decimales is None:
        decimales = 2
    try:
        decimales = int(decimales)
    except Exception:
        decimales = 2

    if decimales <= 0:
        n = int(round(n))
        return f"{n:,}".replace(",", ".")

    # 1,234.56 -> 1.234,56
    formatted = f"{n:,.{decimales}f}"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted


def format_montant(val, decimales=2):
    """Alias pour format_nombre."""
    return format_nombre(val, decimales=decimales)
