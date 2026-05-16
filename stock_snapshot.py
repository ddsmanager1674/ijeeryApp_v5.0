from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any

from db import get_connection, load_db_config
from stock_manager import StockManager


def format_nombre_auto(nombre: Any) -> str:
    """Format auto: 2 décimales sauf si ,00 => entier.

    - séparateur milliers: '.'
    - séparateur décimal: ','
    """
    try:
        x = float(nombre or 0.0)
        if abs(x - round(x)) < 1e-9:
            return f"{int(round(x)):,}".replace(",", ".")
        return (
            f"{x:,.2f}"
            .replace(",", " ")
            .replace(".", ",")
            .replace(" ", ".")
        )
    except Exception:
        return "0"


def read_db_config() -> Dict[str, Any]:
    """Compatibilité : délègue à db.load_db_config()."""
    cfg = load_db_config()
    if cfg is None:
        raise FileNotFoundError("config.json introuvable ou invalide")
    return cfg


def _fetch_facteurs_conversion(conn) -> Dict[int, float]:
    """Retourne {idunite: facteur_vers_base} pour toutes les unités."""
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH RECURSIVE facteur_conversion AS (
                SELECT
                    u.idunite,
                    u.idarticle,
                    u.niveau,
                    1.0::double precision AS facteur_vers_base
                FROM tb_unite u
                WHERE u.niveau = 0
                  AND u.deleted = 0

                UNION ALL

                SELECT
                    u.idunite,
                    u.idarticle,
                    u.niveau,
                    fc.facteur_vers_base * u.qtunite AS facteur_vers_base
                FROM tb_unite u
                JOIN facteur_conversion fc
                  ON fc.idarticle = u.idarticle
                 AND fc.niveau    = u.niveau - 1
                WHERE u.deleted = 0
            )
            SELECT idunite, facteur_vers_base
            FROM facteur_conversion
            """
        )
        return {int(idu): float(f) for (idu, f) in cur.fetchall()}


@dataclass(frozen=True)
class StockSnapshot:
    """Snapshot des stocks (en base) pour 1 magasin, + facteurs de conversion.

    - Ne clamp pas à 0: conserve les valeurs négatives.
    - Conversion: stock_unite = stock_base / facteur_vers_base(idunite)
    """

    idmagasin: int
    stock_base_par_article: Dict[int, float]
    facteur_vers_base_par_unite: Dict[int, float]

    @classmethod
    def build(cls, idmagasin: int, conn=None) -> "StockSnapshot":
        db = load_db_config()
        if db is None:
            raise FileNotFoundError("config.json introuvable ou invalide")

        # 1) facteurs de conversion (via SQL, une seule fois)
        own_conn = conn is None
        if own_conn:
            conn = get_connection()
        try:
            facteurs = _fetch_facteurs_conversion(conn)
        finally:
            if own_conn and conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

        # 2) stock base par article via StockManager (logique métier)
        sm = StockManager(
            host=db["host"],
            port=db["port"],
            dbname=db["database"],
            user=db["user"],
            password=db["password"],
        )
        try:
            lignes = sm.get_stock_tous_articles(idmagasin=int(idmagasin), date_fin=None)
            stock_base = {
                int(l["idarticle"]): float(l.get("stock_en_base", 0.0) or 0.0)
                for l in lignes
            }
        finally:
            try:
                sm.fermer_connexion()
            except Exception:
                pass

        return cls(
            idmagasin=int(idmagasin),
            stock_base_par_article=stock_base,
            facteur_vers_base_par_unite=facteurs,
        )

    def stock_unite(self, idarticle: int, idunite: int) -> float:
        base = float(self.stock_base_par_article.get(int(idarticle), 0.0) or 0.0)
        facteur = float(self.facteur_vers_base_par_unite.get(int(idunite), 1.0) or 1.0)
        if facteur == 0:
            return 0.0
        return base / facteur

