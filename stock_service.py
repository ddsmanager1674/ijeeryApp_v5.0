# -*- coding: utf-8 -*-
"""Façade stock : snapshots, cache et affichage unifiés."""

from __future__ import annotations

from typing import Dict, Optional

from stock_snapshot import StockSnapshot, format_nombre_auto

_cache: Dict[int, StockSnapshot] = {}


def get_snapshot(idmagasin: int, conn=None) -> StockSnapshot:
    """Construit un snapshot de stock pour un magasin."""
    return StockSnapshot.build(int(idmagasin), conn=conn)


def get_snapshot_cached(
    idmagasin: int,
    conn=None,
    *,
    force: bool = False,
) -> StockSnapshot:
    """Retourne un snapshot en cache par magasin (recalcul si force ou absent)."""
    key = int(idmagasin)
    if not force and key in _cache:
        return _cache[key]
    snap = get_snapshot(key, conn=conn)
    _cache[key] = snap
    return snap


def invalidate_snapshot(idmagasin: Optional[int] = None) -> None:
    """Invalide le cache (un magasin ou tout)."""
    if idmagasin is None:
        _cache.clear()
    else:
        _cache.pop(int(idmagasin), None)


def stock_base(snapshot: StockSnapshot, idarticle: int) -> float:
    return float(snapshot.stock_base_par_article.get(int(idarticle), 0.0) or 0.0)


def stock_unite(snapshot: StockSnapshot, idarticle: int, idunite: int) -> float:
    return snapshot.stock_unite(int(idarticle), int(idunite))


def stock_display(snapshot: StockSnapshot, idarticle: int, idunite: int) -> str:
    return format_nombre_auto(stock_unite(snapshot, idarticle, idunite))


def stock_display_cached(
    idmagasin: int,
    idarticle: int,
    idunite: int,
    conn=None,
    *,
    force: bool = False,
) -> str:
    snap = get_snapshot_cached(idmagasin, conn=conn, force=force)
    return stock_display(snap, idarticle, idunite)
