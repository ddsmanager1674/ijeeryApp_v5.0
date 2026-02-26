# -*- coding: utf-8 -*-
"""Outils génériques pour gérer les conversions d'unit\xc3\xa9s et le calcul de stock.

Ce module est volontairement d\xc3\xa9coupl\xc3\xa9 de la base de donn\xc3\xa9es.  Il travaille
avec des objets en m\xc3\xa9moire et illustre la logique suivante :

* Chaque unit\xc3\xa9 est associ\xc3\xa9e \xc3\xa0 une quantit\xc3\xa9 relative vis-\xc3\xa0-vis de son
  parent (coefficient).  L\'unit\xc3\xa9 de base a un coefficient de 1.
* Le coefficient cumul\xc3\xa9 d\'une unit\xc3\xa9 est le produit des coefficients de la
  cha\xc3\xaene qui la rattache \xc3\xa0 l\'unit\xc3\xa9 de base.
* Un mouvement porte toujours une quantit\xc3\xa9 dans une unit\xc3\xa9 quelconque.  Il
  peut s\'agir d\'une entr\xc3\xa9e ou d\'une sortie.
* Tous les calculs de stock se font en unit\xc3\xa9 de base et l\'affichage est simplement
  une division par le coefficient cumul\xc3\xa9 de l\'unit\xc3\xa9 choisie.

Le module propose 
:  `coefficient_cumule`, `convertir_vers_base` et `calculer_stock`.

Les classes ``Unite`` et ``Mouvement`` servent d\'exemple et facilitent les tests.

La mise en garde importante est qu\'on protège contre les boucles dans la hi\xc3\xa9rarchie
(d\'une unit\xc3\xa9 se r\xc3\xa9f\xc3\xa8re indirectement \xc3\xa0 elle-m\xc3\xaame) et que toute
quantit\xc3\xa9 non positive est trait\xc3\xa9e gracieusement.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Set, Iterable


@dataclass
class Unite:
    nom: str
    coefficient: float  # coefficient relatif au parent (1 pour l'unité de base)
    parent: Optional['Unite'] = None

    def __repr__(self):
        return f"Unite({self.nom!r}, coeff={self.coefficient}, parent={self.parent.nom if self.parent else None})"


@dataclass
class Mouvement:
    article: str
    type_mouvement: str  # "ENTREE" ou "SORTIE" (insensible à la casse)
    quantite: float
    unite: Unite

    def signe(self) -> float:
        # Les types d'entrées acceptés peuvent êre enrichis selon
        # besoin ("ENTREE", "IN", "+" etc.).
        t = self.type_mouvement.strip().lower()
        if t in ("entree", "entrée", "in", "+", "ajout", "+1"):
            return 1.0
        else:
            # tout ce qui n'est pas dans la liste est considéré comme
            # sortie / diminution
            return -1.0


# ---------------------------------------------------------------------------
# Fonctions métier
# ---------------------------------------------------------------------------

def coefficient_cumule(unite: Unite, visited: Optional[Set[int]] = None) -> float:
    """Retourne le coefficient par rapport \xc3\xa0 l'unit\xc3\xa9 de base.

    L'unit\xc3\xa9 de base doit avoir ``parent`` == ``None`` et un
    ``coefficient`` qui est normalement 1.0.  Pour les autres niveaux,
    on multiplie le coefficient de l'unit\xc3\xa9 par celui de son parent,
    puis du parent du parent, et ainsi de suite jusqu'\xc3\xa0 la racine.

    En cas de boucle (une unit\xc3\xa9 figure dans sa propre cha\xc3\xaene),
    on l\'interrompt proprement et on l\xc3\xa8ve ``ValueError`` pour que
    l'appelant puisse corriger la hi\xc3\xa9rarchie.

    Exemple
    -------
    >>> piece = Unite('Pi\xc3\xa8ce', 1)
    >>> paquet = Unite('Paquet', 10, piece)
    >>> carton = Unite('Carton', 5, paquet)
    >>> coefficient_cumule(carton)
    50
    """

    # on utilise l'id() de l'objet pour que l'ensemble soit hashable
    if visited is None:
        visited = set()
    obj_id = id(unite)
    if obj_id in visited:
        raise ValueError(f"Boucle d'unit\xc3\xa9 d\'tect\xc3\xa9e \xc3\xa0 {unite}")
    visited.add(obj_id)

    if unite.parent is None:
        # on accepte que la base ait un coefficient != 1 mais cela
        # n'a pas de sens : on renvoie au minimum 1.
        return max(unite.coefficient, 1.0)

    parent_coeff = coefficient_cumule(unite.parent, visited)
    return unite.coefficient * parent_coeff


def convertir_vers_base(quantite: float, unite: Unite) -> float:
    """Convertit ``quantite`` dans l'``unite`` fournie vers l'unite de base.

    La fonction se contente d'appeler ``coefficient_cumule`` et de multiplier.
    Des valeurs nulles ou n\'gatives sont g\xc3\xa9r\xc3\xa9es en retournant 0.
    """

    if quantite is None:
        return 0.0
    if quantite == 0:
        return 0.0
    coeff = coefficient_cumule(unite)
    return quantite * coeff


def convertir_depuis_base(stock_base: float, unite: Unite) -> float:
    """Transforme un stock exprim\xc3\xa9 en unit\xc3\xa9 de base vers ``unite``.

    Utile pour l'affichage.  Le calcul est l'inverse de
    ``convertir_vers_base``.
    """

    if stock_base is None:
        return 0.0
    coeff = coefficient_cumule(unite)
    if coeff == 0:
        return 0.0
    return stock_base / coeff


def calculer_stock(article: str, mouvements: Iterable[Mouvement]) -> float:
    """Calcule le stock final d'un article en unit\xc3\xa9 de base.

    ``mouvements`` est une collection de ``Mouvement``.  Le signe de chaque
    mouvement (entr\xc3\xa9e ou sortie) est d\xc3\xa9termin\xc3\xa9 par la m\xc3\xa9thode
    ``Mouvement.signe``.

    Retourne une valeur flottante pouvant \xc3\xaatre n\xc3\xa9gative si les sorties
    d\xc3\xa9passent les entr\xc3\xa9es (cas possible lorsqu'on r\xc3\xa9alise des
    ajustements).
    """

    total = 0.0
    for m in mouvements:
        quant_base = convertir_vers_base(m.quantite, m.unite)
        total += m.signe() * quant_base
    return total


# ---------------------------------------------------------------------------
# Quelques tests rapides (autovalidation) when module executed directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # démonstration rapide
    piece = Unite("Pi\xc3\xa8ce", 1)
    paquet = Unite("Paquet", 10, piece)
    carton = Unite("Carton", 5, paquet)
    print("Coeff carton -> base:", coefficient_cumule(carton))
    mouvements = [
        Mouvement("X", "ENTREE", 3, carton),
        Mouvement("X", "SORTIE", 4, paquet),
        Mouvement("X", "SORTIE", 6, piece),
    ]
    print("Stock final en base:", calculer_stock("X", mouvements))
