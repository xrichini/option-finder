"""
History Service - Feed automatique de options_history.db après chaque scan
et calcul de métriques comparatives basées sur l'historique local.

Métriques disponibles :
  - Sizzle Index  : vol_today / avg_vol_30d  (déjà dans market_utils)
  - IV Rank       : (iv_now - iv_min_52w) / (iv_max_52w - iv_min_52w) × 100
  - IV Percentile : % de jours où iv_journalière_underlying < iv_now  (252j)
  - OI Spike      : oi_today / avg_oi_5d  (> 2 = spike notable)
  - Vol Trend     : vol_today / avg_vol_5d (> 2 = tendance haussière)

Les métriques IV se calculent par SOUS-JACENT (avg IV journalière des contrats).
Les métriques OI/Vol se calculent par CONTRAT (option_symbol).
Plus l'historique est riche, plus ces métriques sont précises.
"""

from __future__ import annotations

import os
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_DB_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "options_history.db")
)


class HistoryService:
    """
    Persistance historique des scans (options_history.db) + enrichissement comparatif.

    Pattern d'utilisation dans screening_service :
        history_service.record_scan_results(opportunities)   # feed
        history_service.enrich_with_history(opportunities)   # métriques
    """

    def __init__(self, db_path: str = _DB_PATH):
        self.db_path = db_path
        self._migrate()

    # ------------------------------------------------------------------
    # Migration du schéma — idempotente, ne détruit rien
    # ------------------------------------------------------------------

    def _migrate(self) -> None:
        """Ajoute les colonnes manquantes + index si la DB existe déjà."""
        if not os.path.exists(self.db_path):
            # La DB sera créée au premier record_scan_results()
            return
        try:
            con = sqlite3.connect(self.db_path)
            existing = {
                row[1]
                for row in con.execute("PRAGMA table_info(option_history)").fetchall()
            }
            new_cols = {
                "implied_volatility": "REAL DEFAULT 0",
                "strike": "REAL DEFAULT 0",
                "option_type": "TEXT DEFAULT ''",
            }
            for col, col_def in new_cols.items():
                if col not in existing:
                    con.execute(
                        f"ALTER TABLE option_history ADD COLUMN {col} {col_def}"
                    )
                    logger.info(f"DB migration: ajout colonne '{col}'")
            # Crée les index si absents
            con.execute(
                """CREATE UNIQUE INDEX IF NOT EXISTS idx_opthist_sym_date
                   ON option_history (option_symbol, scan_date)"""
            )
            con.execute(
                """CREATE INDEX IF NOT EXISTS idx_opthist_underlying
                   ON option_history (underlying, scan_date)"""
            )
            con.commit()
            con.close()
        except Exception as e:
            logger.warning(f"Migration options_history.db: {e}")

    # ------------------------------------------------------------------
    # Enregistrement post-scan (UPSERT — une ligne par contrat par jour)
    # ------------------------------------------------------------------

    def record_scan_results(self, opportunities: List[Any]) -> int:
        """
        Insère ou met à jour les résultats du scan du jour.
        Contrainte UNIQUE sur (option_symbol, scan_date) → pas de doublons.
        Retourne le nombre de lignes traitées.
        """
        if not opportunities:
            return 0

        today = datetime.now().strftime("%Y-%m-%d")

        rows = []
        for opp in opportunities:
            d = (
                opp.dict()
                if hasattr(opp, "dict")
                else (opp if isinstance(opp, dict) else {})
            )
            iv = float(d.get("implied_volatility") or 0)
            if 0 < iv <= 1:
                iv *= 100  # normalise en % si fourni en fraction

            rows.append(
                (
                    d.get("option_symbol") or d.get("symbol", ""),
                    d.get("underlying_symbol") or d.get("underlying", ""),
                    today,
                    int(d.get("volume") or 0),
                    int(d.get("open_interest") or 0),
                    float(d.get("last") or d.get("last_price") or 0),
                    float(d.get("whale_score") or 0),
                    float(d.get("vol_oi_ratio") or 0),
                    float(iv),
                    float(d.get("strike") or 0),
                    str(d.get("option_type") or ""),
                )
            )

        if not rows:
            return 0

        try:
            con = sqlite3.connect(self.db_path)
            # Crée la table + index si première utilisation
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS option_history (
                    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                    option_symbol      TEXT    NOT NULL,
                    underlying         TEXT    NOT NULL,
                    scan_date          DATE    NOT NULL,
                    volume_1d          INTEGER NOT NULL,
                    open_interest      INTEGER NOT NULL,
                    last_price         REAL,
                    whale_score        REAL,
                    vol_oi_ratio       REAL,
                    implied_volatility REAL    DEFAULT 0,
                    strike             REAL    DEFAULT 0,
                    option_type        TEXT    DEFAULT '',
                    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            con.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_opthist_sym_date
                ON option_history (option_symbol, scan_date)
            """
            )
            con.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_opthist_underlying
                ON option_history (underlying, scan_date)
            """
            )

            count = 0
            for row in rows:
                try:
                    con.execute(
                        """
                        INSERT INTO option_history
                            (option_symbol, underlying, scan_date,
                             volume_1d, open_interest, last_price,
                             whale_score, vol_oi_ratio,
                             implied_volatility, strike, option_type)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?)
                        ON CONFLICT(option_symbol, scan_date) DO UPDATE SET
                            volume_1d          = excluded.volume_1d,
                            open_interest      = excluded.open_interest,
                            last_price         = excluded.last_price,
                            whale_score        = excluded.whale_score,
                            vol_oi_ratio       = excluded.vol_oi_ratio,
                            implied_volatility = excluded.implied_volatility,
                            strike             = excluded.strike,
                            option_type        = excluded.option_type
                        """,
                        row,
                    )
                    count += 1
                except Exception:
                    pass

            con.commit()
            con.close()
            logger.info(f"💾 Historique: {count} lignes upsert dans options_history.db")
            return count

        except Exception as e:
            logger.error(f"record_scan_results error: {e}")
            return 0

    # ------------------------------------------------------------------
    # Métriques comparatives — requêtes SQL légères
    # ------------------------------------------------------------------

    def _open(self) -> Optional[sqlite3.Connection]:
        """Ouvre la DB si elle existe, sinon None."""
        if not os.path.exists(self.db_path):
            return None
        return sqlite3.connect(self.db_path)

    def get_iv_rank(
        self, underlying: str, current_iv: float, window_days: int = 252
    ) -> float:
        """
        IV Rank = (iv_now − iv_min) / (iv_max − iv_min) × 100
        Calculé à partir des IV moyennes journalières du sous-jacent.
        Retourne 0.0 si l'historique est insuffisant.
        """
        if not current_iv:
            return 0.0
        con = self._open()
        if con is None:
            return 0.0
        try:
            cutoff = (datetime.now() - timedelta(days=window_days)).strftime("%Y-%m-%d")
            row = con.execute(
                """
                SELECT MIN(avg_iv), MAX(avg_iv) FROM (
                    SELECT scan_date, AVG(implied_volatility) AS avg_iv
                    FROM option_history
                    WHERE underlying = ?
                      AND scan_date >= ?
                      AND implied_volatility > 0
                    GROUP BY scan_date
                )
                """,
                (underlying, cutoff),
            ).fetchone()
            if row and row[0] is not None and row[1] != row[0]:
                iv_min, iv_max = row
                return round(((current_iv - iv_min) / (iv_max - iv_min)) * 100, 1)
            return 0.0
        except Exception as e:
            logger.debug(f"get_iv_rank({underlying}): {e}")
            return 0.0
        finally:
            con.close()

    def get_iv_percentile(
        self, underlying: str, current_iv: float, window_days: int = 252
    ) -> float:
        """
        IV Percentile = % de jours historiques où iv_journalière < iv_actuelle.
        """
        if not current_iv:
            return 0.0
        con = self._open()
        if con is None:
            return 0.0
        try:
            cutoff = (datetime.now() - timedelta(days=window_days)).strftime("%Y-%m-%d")
            total, below = con.execute(
                """
                SELECT COUNT(*),
                       SUM(CASE WHEN avg_iv < ? THEN 1 ELSE 0 END)
                FROM (
                    SELECT scan_date, AVG(implied_volatility) AS avg_iv
                    FROM option_history
                    WHERE underlying = ?
                      AND scan_date >= ?
                      AND implied_volatility > 0
                    GROUP BY scan_date
                )
                """,
                (current_iv, underlying, cutoff),
            ).fetchone()
            if total and total > 0:
                return round((below or 0) / total * 100, 1)
            return 0.0
        except Exception as e:
            logger.debug(f"get_iv_percentile({underlying}): {e}")
            return 0.0
        finally:
            con.close()

    def get_oi_spike(
        self, option_symbol: str, current_oi: int, window_days: int = 5
    ) -> float:
        """
        Ratio OI aujourd'hui / moyenne OI sur window_days.
          > 1.5 → notable,  > 3 → spike fort
        """
        if not current_oi:
            return 0.0
        con = self._open()
        if con is None:
            return 0.0
        try:
            cutoff = (datetime.now() - timedelta(days=window_days)).strftime("%Y-%m-%d")
            row = con.execute(
                """
                SELECT AVG(open_interest) FROM option_history
                WHERE option_symbol = ? AND scan_date >= ? AND open_interest > 0
                """,
                (option_symbol, cutoff),
            ).fetchone()
            avg = row[0] if row and row[0] else None
            if avg and avg > 0:
                return round(current_oi / avg, 2)
            return 0.0
        except Exception as e:
            logger.debug(f"get_oi_spike({option_symbol}): {e}")
            return 0.0
        finally:
            con.close()

    def get_vol_trend(
        self, option_symbol: str, current_vol: int, window_days: int = 5
    ) -> float:
        """
        Ratio volume aujourd'hui / moyenne volume sur window_days.
          > 1.5 → tendance notable,  > 3 → très haussier
        """
        if not current_vol:
            return 0.0
        con = self._open()
        if con is None:
            return 0.0
        try:
            cutoff = (datetime.now() - timedelta(days=window_days)).strftime("%Y-%m-%d")
            row = con.execute(
                """
                SELECT AVG(volume_1d) FROM option_history
                WHERE option_symbol = ? AND scan_date >= ? AND volume_1d > 0
                """,
                (option_symbol, cutoff),
            ).fetchone()
            avg = row[0] if row and row[0] else None
            if avg and avg > 0:
                return round(current_vol / avg, 2)
            return 0.0
        except Exception as e:
            logger.debug(f"get_vol_trend({option_symbol}): {e}")
            return 0.0
        finally:
            con.close()

    # ------------------------------------------------------------------
    # Enrichissement batch — optimisé (une requête IV par underlying)
    # ------------------------------------------------------------------

    def enrich_with_history(self, opportunities: List[Any]) -> List[Any]:
        """
        Enrichit in-place une liste d'OptionsOpportunity (ou dicts) avec :
          iv_rank, iv_percentile, oi_spike_ratio, vol_trend_ratio.

        Optimisation : calcule iv_rank/pct par underlying une seule fois
        (évite N requêtes pour N contrats du même sous-jacent).
        """
        if not opportunities or not os.path.exists(self.db_path):
            return opportunities

        def _get(opp: Any, key: str, default=None):
            if hasattr(opp, key):
                return getattr(opp, key, default)
            return opp.get(key, default) if isinstance(opp, dict) else default

        def _set(opp: Any, key: str, value: Any):
            if (
                hasattr(opp, key)
                or isinstance(opp, object)
                and not isinstance(opp, dict)
            ):
                try:
                    object.__setattr__(opp, key, value)
                except Exception:
                    pass
            elif isinstance(opp, dict):
                opp[key] = value

        # Calcul IV metrics par underlying (batch)
        iv_cache: Dict[str, Tuple[float, float]] = {}
        for opp in opportunities:
            und = _get(opp, "underlying_symbol", "")
            if und and und not in iv_cache:
                iv_raw = _get(opp, "implied_volatility", 0) or 0
                iv = iv_raw * 100 if 0 < iv_raw <= 1 else iv_raw
                if iv > 0:
                    iv_cache[und] = (
                        self.get_iv_rank(und, iv),
                        self.get_iv_percentile(und, iv),
                    )
                else:
                    iv_cache[und] = (0.0, 0.0)

        # Enrichissement contrat par contrat (OI spike + vol trend)
        for opp in opportunities:
            try:
                und = _get(opp, "underlying_symbol", "")
                sym = _get(opp, "option_symbol", "")
                oi = int(_get(opp, "open_interest", 0) or 0)
                vol = int(_get(opp, "volume", 0) or 0)
                iv_rank, iv_pct = iv_cache.get(und, (0.0, 0.0))

                _set(opp, "iv_rank", iv_rank)
                _set(opp, "iv_percentile", iv_pct)
                _set(opp, "oi_spike_ratio", self.get_oi_spike(sym, oi))
                _set(opp, "vol_trend_ratio", self.get_vol_trend(sym, vol))
            except Exception as e:
                logger.debug(f"enrich_with_history item: {e}")

        return opportunities

    # ------------------------------------------------------------------
    # Stats / debug
    # ------------------------------------------------------------------

    def get_stats(self, underlying: Optional[str] = None) -> Dict[str, Any]:
        """Statistiques globales ou par sous-jacent."""
        con = self._open()
        if con is None:
            return {"error": "options_history.db introuvable", "db_path": self.db_path}
        try:
            total = con.execute("SELECT COUNT(*) FROM option_history").fetchone()[0]
            days = con.execute(
                "SELECT COUNT(DISTINCT scan_date) FROM option_history"
            ).fetchone()[0]
            underlyings = con.execute(
                "SELECT COUNT(DISTINCT underlying) FROM option_history"
            ).fetchone()[0]
            last_scan = con.execute(
                "SELECT MAX(scan_date) FROM option_history"
            ).fetchone()[0]
            stats: Dict[str, Any] = {
                "total_records": total,
                "distinct_scan_days": days,
                "distinct_underlyings": underlyings,
                "last_scan_date": last_scan,
                "db_path": self.db_path,
            }
            if underlying:
                row = con.execute(
                    """
                    SELECT COUNT(*), MIN(scan_date), MAX(scan_date),
                           ROUND(MAX(implied_volatility),1),
                           ROUND(MIN(CASE WHEN implied_volatility>0 THEN implied_volatility END),1)
                    FROM option_history WHERE underlying = ?
                    """,
                    (underlying,),
                ).fetchone()
                if row:
                    stats[underlying] = {
                        "records": row[0],
                        "first_date": row[1],
                        "last_date": row[2],
                        "iv_max": row[3],
                        "iv_min": row[4],
                    }
            return stats
        except Exception as e:
            return {"error": str(e)}
        finally:
            con.close()


# Singleton
history_service = HistoryService()
