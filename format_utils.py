# -*- coding: utf-8 -*-

def format_entier(val):
    """Formate un nombre en entier naturel avec s?parateur '.' (affichage uniquement)."""
    try:
        if val is None:
            return '0'
        n = float(val)
    except Exception:
        return str(val)
    n = int(round(n))
    return f"{n:,}".replace(',', '.')
