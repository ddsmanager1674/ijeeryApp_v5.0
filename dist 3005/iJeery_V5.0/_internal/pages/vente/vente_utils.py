# -*- coding: utf-8 -*-
"""Utilitaires partagés vente / impression."""


def nombre_en_lettres_fr(montant: float) -> str:
    """Convertit un montant numérique en lettres (français)."""
    from math import floor

    if montant is None:
        return ""
    try:
        montant = round(float(montant), 2)
    except ValueError:
        return ""

    unites = ["", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf"]
    dix_a_16 = ["dix", "onze", "douze", "treize", "quatorze", "quinze", "seize"]
    dizaines = [
        "", "dix", "vingt", "trente", "quarante", "cinquante",
        "soixante", "soixante", "quatre-vingt", "quatre-vingt",
    ]

    def _simple(n):
        if n == 0:
            return ""
        if n < 10:
            return unites[n]
        if n < 17:
            return dix_a_16[n - 10]
        if n < 20:
            return "dix-" + unites[n - 10]
        d, u = n // 10, n % 10
        p = dizaines[d]
        if d in (2,) and u == 1:
            p += " et"
        if d in (7, 9):
            return p + "-" + _simple(n - d * 10) if u else p + "-" + _simple(10)
        if u:
            if d > 6 and u == 1:
                p += " et"
            return p + "-" + unites[u]
        return p

    def _bloc(n):
        if n == 0:
            return ""
        if n < 100:
            return _simple(n)
        c, r = n // 100, n % 100
        s = ("" if c == 1 else _simple(c) + "-") + "cent"
        if r == 0 and c > 1:
            s += "s"
        return s + ("-" + _bloc(r) if r else "")

    entier = floor(montant)
    centimes = int(round((montant - entier) * 100))
    million = entier // 1_000_000
    mille = (entier % 1_000_000) // 1_000
    unite_r = entier % 1_000

    parts = []
    if million:
        parts.append(_bloc(million) + (" millions" if million > 1 else " million"))
    if mille:
        parts.append(_bloc(mille) + " mille")
    if unite_r:
        parts.append(_bloc(unite_r))
    if not parts:
        parts.append("zéro")

    res = " ".join(parts).strip().replace("  ", " ").replace("-", " ")
    if centimes:
        res += " et " + _bloc(centimes).replace("-", " ") + " centimes"

    return res.capitalize().replace(" et-", " et ")


def formater_nombre_pdf(n) -> str:
    """Format entier pour PDF."""
    try:
        return "{:,.0f}".format(float(n)).replace(",", ".")
    except Exception:
        return "0"
