# -*- coding: utf-8 -*-
"""Façade stock : snapshots et affichage unifiés."""

from __future__ import annotations

from typing import Any, Optional

from stock_snapshot import StockSnapshot, format_nombre_auto


def get_snapshot(idmagasin: int, conn=None) -> StockSnapshot:
    """Construit un snapshot de stock pour un magasin."""
    return StockSnapshot.build(int(idmagasin), conn=conn)


def stock_base(snapshot: StockSnapshot, idarticle: int) -> float:
    return float(snapshot.stock_base_par_article.get(int(idarticle), 0.0) or 0.0)


def stock_unite(snapshot: StockSnapshot, idarticle: int, idunite: int) -> float:
    return snapshot.stock_unite(int(idarticle), int(idunite))


def stock_display(snapshot: StockSnapshot, idarticle: int, idunite: int) -> str:
    return format_nombre_auto(stock_unite(snapshot, idarticle, idunite))
