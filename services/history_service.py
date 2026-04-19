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
                "volume_30d_avg": "REAL DEFAULT 0",  # Phase 1: 30-day volume average
                "size_percentile": "REAL DEFAULT 0",  # Phase 1: top 1%/5%/25%
                "fill_velocity": "REAL DEFAULT 0",  # Phase 2: contracts/minute
                "iv_52w_avg": "REAL DEFAULT 0",  # Phase 2: 52-week IV average
                "order_flow_strength": "REAL DEFAULT 50",  # Phase 3: 0-100 bullish conviction
                "volatility_smile_width": "REAL DEFAULT 0",  # Phase 3: IV variance across strikes
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

    def get_size_percentile(
        self, option_symbol: str, current_vol: int, window_days: int = 30
    ) -> Tuple[float, float]:
        """
        Phase 1: Calculate size percentile for current volume.

        Returns:
            (size_percentile, vol_30d_avg)
            - size_percentile: 0-100, where 100 = top 1% of contracts by volume
            - vol_30d_avg: 30-day average volume

        Classification:
            > 2.0x (top 1%): 95+ percentile
            > 1.3x (top 5%): 80+ percentile
            > 1.0x (top 25%): 75+ percentile
            < 1.0x: < 75 percentile
        """
        if not current_vol:
            return (0.0, 0.0)

        con = self._open()
        if con is None:
            return (0.0, 0.0)

        try:
            cutoff = (datetime.now() - timedelta(days=window_days)).strftime("%Y-%m-%d")

            # Get 30-day average volume for this contract
            row = con.execute(
                """
                SELECT AVG(volume_1d) FROM option_history
                WHERE option_symbol = ? AND scan_date >= ? AND volume_1d > 0
                """,
                (option_symbol, cutoff),
            ).fetchone()

            vol_30d_avg = row[0] if row and row[0] else 0.0

            if vol_30d_avg <= 0:
                return (0.0, 0.0)

            # Calculate percentile: how much current_vol is vs 30-day average
            vol_ratio = current_vol / vol_30d_avg

            # Map ratio to percentile (0-100)
            if vol_ratio >= 2.0:
                size_percentile = 95.0  # Top 1%
            elif vol_ratio >= 1.3:
                size_percentile = 80.0  # Top 5%
            elif vol_ratio >= 1.0:
                size_percentile = 75.0  # Top 25%
            else:
                # Below average — scale down from 0-75
                size_percentile = max(0.0, (vol_ratio / 1.0) * 75.0)

            return (round(size_percentile, 1), round(vol_30d_avg, 0))

        except Exception as e:
            logger.debug(f"get_size_percentile({option_symbol}): {e}")
            return (0.0, 0.0)
        finally:
            con.close()

    def get_iv_crush_risk(
        self, option_symbol: str, current_iv: float, window_days: int = 252
    ) -> Tuple[float, str]:
        """
        Phase 2: Calculate IV crush risk.

        Returns:
            (iv_crush_ratio, iv_crush_signal)
            - iv_crush_ratio: current_iv / 52w_avg_iv (>1.5 = high risk)
            - iv_crush_signal: 'high_risk'|'normal'|'low_risk'

        High IV crush risk (>1.5x) = likely mean reversion to lower IV
        This suggests earnings or volatility event priced in.
        """
        if not current_iv or current_iv <= 0:
            return (0.0, "normal")

        con = self._open()
        if con is None:
            return (0.0, "normal")

        try:
            cutoff = (datetime.now() - timedelta(days=window_days)).strftime("%Y-%m-%d")

            # Get 52-week average IV for this contract
            row = con.execute(
                """
                SELECT AVG(implied_volatility) FROM option_history
                WHERE option_symbol = ? AND scan_date >= ? AND implied_volatility > 0
                """,
                (option_symbol, cutoff),
            ).fetchone()

            iv_52w_avg = row[0] if row and row[0] else None

            if not iv_52w_avg or iv_52w_avg <= 0:
                return (0.0, "normal")

            # Calculate crush risk: how much higher current IV is vs historical avg
            iv_crush_ratio = current_iv / iv_52w_avg

            # Classify risk
            if iv_crush_ratio >= 1.5:
                iv_crush_signal = "high_risk"  # Elevated IV, likely to compress
            elif iv_crush_ratio >= 1.2:
                iv_crush_signal = "normal"  # Moderately elevated
            else:
                iv_crush_signal = "low_risk"  # Below historical average

            return (round(iv_crush_ratio, 2), iv_crush_signal)

        except Exception as e:
            logger.debug(f"get_iv_crush_risk({option_symbol}): {e}")
            return (0.0, "normal")
        finally:
            con.close()

    def get_fill_velocity_metric(
        self, option_symbol: str, window_minutes: int = 5
    ) -> Tuple[float, str]:
        """
        Phase 2: Calculate fill velocity (contracts/minute).

        Returns:
            (fill_velocity, fill_velocity_signal)
            - fill_velocity: contracts/minute during recent window
            - fill_velocity_signal: 'high_velocity'|'normal'|'low_velocity'

        High velocity (>5000 contracts/min) = aggressive institutional buying
        Normal (1000-5000) = steady institutional interest
        Low (<1000) = quiet accumulation
        """
        if not option_symbol:
            return (0.0, "normal")

        con = self._open()
        if con is None:
            return (0.0, "normal")

        try:
            # Get total volume from recent history (approximate velocity)
            # We use volume_1d as proxy for activity level
            row = con.execute(
                """
                SELECT SUM(volume_1d) FROM option_history
                WHERE option_symbol = ? AND scan_date >= date('now', '-1 day')
                """,
                (option_symbol,),
            ).fetchone()

            total_vol = row[0] if row and row[0] else 0

            if total_vol <= 0:
                return (0.0, "normal")

            # Approximate velocity: assume 6.5 hours of trading
            # More refined when we have minute-level data
            fill_velocity = round(total_vol / 390, 0)  # 390 minutes in trading day

            # Classify velocity
            if fill_velocity >= 5000:
                velocity_signal = "high_velocity"  # Exceptional institutional interest
            elif fill_velocity >= 1000:
                velocity_signal = "normal"  # Steady activity
            else:
                velocity_signal = "low_velocity"  # Below average activity

            return (fill_velocity, velocity_signal)

        except Exception as e:
            logger.debug(f"get_fill_velocity_metric({option_symbol}): {e}")
            return (0.0, "normal")
        finally:
            con.close()

    def get_order_flow_strength(
        self,
        option_symbol: str,
        current_vol: int,
        current_oi: int,
        window_days: int = 30,
    ) -> Tuple[float, str]:
        """
        Phase 3: Calculate order flow strength (institutional conviction).

        Returns:
            (order_flow_strength, order_flow_direction)
            - order_flow_strength: 0-100 (>50=bullish)
            - order_flow_direction: 'strong_bullish'|'bullish'|'neutral'|'bearish'|'strong_bearish'

        Analysis:
            - Volume trending upward = institutional accumulation (bullish)
            - OI expanding with rising volume = conviction (building position)
            - OI contracting with volume = distribution (closing position)
        """
        if not option_symbol or (current_vol <= 0 and current_oi <= 0):
            return (50.0, "neutral")

        con = self._open()
        if con is None:
            return (50.0, "neutral")

        try:
            cutoff = (datetime.now() - timedelta(days=window_days)).strftime("%Y-%m-%d")

            # Get historical volume and OI trend
            history = con.execute(
                """
                SELECT volume_1d, open_interest, scan_date FROM option_history
                WHERE option_symbol = ? AND scan_date >= ? 
                ORDER BY scan_date ASC
                """,
                (option_symbol, cutoff),
            ).fetchall()

            if not history or len(history) < 3:
                return (50.0, "neutral")

            # Calculate trend: recent vs early
            recent_vol = sum(row[0] for row in history[-5:]) / max(1, len(history[-5:]))
            early_vol = sum(row[0] for row in history[:5]) / max(1, len(history[:5]))
            vol_trend = (recent_vol - early_vol) / max(1, early_vol)

            recent_oi = sum(row[1] for row in history[-5:]) / max(1, len(history[-5:]))
            early_oi = sum(row[1] for row in history[:5]) / max(1, len(history[:5]))
            oi_trend = (recent_oi - early_oi) / max(1, early_oi)

            # Volume/OI expansion:
            # - Vol up, OI up = accumulation (bullish)
            # - Vol up, OI down = liquidation (bearish)
            # - Vol down, OI up = quiet buying (bullish)
            # - Vol down, OI down = quiet selling (bearish)

            vol_score = min(100, max(0, (vol_trend * 100) + 50))  # 0-100
            oi_score = min(100, max(0, (oi_trend * 100) + 50))  # 0-100
            current_score = vol_score * 0.6 + oi_score * 0.4  # Weight vol higher

            # Classify direction
            if current_score >= 75:
                direction = "strong_bullish"
            elif current_score >= 60:
                direction = "bullish"
            elif current_score <= 25:
                direction = "strong_bearish"
            elif current_score <= 40:
                direction = "bearish"
            else:
                direction = "neutral"

            return (round(current_score, 1), direction)

        except Exception as e:
            logger.debug(f"get_order_flow_strength({option_symbol}): {e}")
            return (50.0, "neutral")
        finally:
            con.close()

    def get_volatility_smile_width(
        self, underlying_symbol: str, current_iv: float, window_days: int = 14
    ) -> Tuple[float, float]:
        """
        Phase 3: Calculate volatility smile width (IV dispersion across strikes).

        Returns:
            (smile_width, crush_probability)
            - smile_width: 0-100 (std dev of IV across strikes, normalized)
            - crush_probability: 0-100 (likelihood of mean reversion)

        Analysis:
            - High IV variance across strikes = smile detected (volatility event priced in)
            - This suggests IV may compress back to normal (crushing)
            - Correlated with earnings or uncertainty events
        """
        if not underlying_symbol or current_iv <= 0:
            return (0.0, 0.0)

        con = self._open()
        if con is None:
            return (0.0, 0.0)

        try:
            cutoff = (datetime.now() - timedelta(days=window_days)).strftime("%Y-%m-%d")

            # Get all IVs for all strikes of this underlying in recent period
            rows = con.execute(
                """
                SELECT implied_volatility, strike FROM option_history
                WHERE underlying = ? AND scan_date >= ? AND implied_volatility > 0
                ORDER BY scan_date DESC
                LIMIT 500
                """,
                (underlying_symbol, cutoff),
            ).fetchall()

            if not rows or len(rows) < 5:
                return (0.0, 0.0)

            # Extract IVs, calculate mean and std dev
            ivs = [float(row[0]) for row in rows if row[0] > 0]
            if len(ivs) < 5:
                return (0.0, 0.0)

            mean_iv = sum(ivs) / len(ivs)
            variance = sum((iv - mean_iv) ** 2 for iv in ivs) / len(ivs)
            std_dev_iv = variance**0.5

            # Normalize smile width to 0-100 scale
            # Assume typical std dev is 5% IV points, extreme is 20%
            smile_width = (
                min(100, (std_dev_iv / 5.0) * 33.33) if std_dev_iv > 0 else 0.0
            )

            # Crush probability: if current IV is high relative to mean
            # and smile is present, crush is likely
            iv_ratio = current_iv / mean_iv if mean_iv > 0 else 1.0

            # High IV + wide smile = high crush risk
            crush_prob = 0.0
            if iv_ratio >= 1.5:
                crush_prob = min(100, 50 + (smile_width * 0.5))  # 50-100
            elif iv_ratio >= 1.3:
                crush_prob = min(100, 35 + (smile_width * 0.3))  # 35-65
            elif iv_ratio >= 1.1:
                crush_prob = min(100, 20 + (smile_width * 0.2))  # 20-40
            else:
                crush_prob = smile_width * 0.15  # 0-15

            return (round(smile_width, 1), round(crush_prob, 1))

        except Exception as e:
            logger.debug(f"get_volatility_smile_width({underlying_symbol}): {e}")
            return (0.0, 0.0)
        finally:
            con.close()

    def get_yesterday_oi(self, option_symbol: str) -> Optional[float]:
        """
        Récupère l'Open Interest d'hier pour une option.
        Utilisé pour calculer le OI Momentum (OI change % day-over-day).

        Retourne None si pas de données hier ou si DB n'existe pas.
        """
        con = self._open()
        if con is None:
            return None
        try:
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            row = con.execute(
                """
                SELECT open_interest FROM option_history
                WHERE option_symbol = ? AND scan_date = ?
                LIMIT 1
                """,
                (option_symbol, yesterday),
            ).fetchone()
            return row[0] if row and row[0] else None
        except Exception as e:
            logger.debug(f"get_yesterday_oi({option_symbol}): {e}")
            return None
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

        # Enrichissement contrat par contrat (OI spike + vol trend + size percentile)
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

                # Phase 1: Size percentile tracking
                size_pct, vol_30d_avg = self.get_size_percentile(sym, vol)
                _set(opp, "size_percentile", size_pct)
                _set(opp, "volume_30d_avg", vol_30d_avg)

                # Phase 2: IV crush risk & fill velocity
                iv = float(_get(opp, "implied_volatility", 0) or 0)
                if iv > 0 and iv <= 1:
                    iv *= 100  # normalize to percentage if needed

                iv_crush_ratio, iv_crush_signal = self.get_iv_crush_risk(sym, iv)
                _set(opp, "iv_crush_risk", iv_crush_ratio)
                _set(opp, "iv_crush_signal", iv_crush_signal)

                fill_vel, vel_signal = self.get_fill_velocity_metric(sym)
                _set(opp, "fill_velocity", fill_vel)
                _set(opp, "fill_velocity_signal", vel_signal)

                # Phase 3: Order flow strength & volatility smile
                flow_strength, flow_direction = self.get_order_flow_strength(
                    sym, vol, oi
                )
                _set(opp, "order_flow_strength", flow_strength)
                _set(opp, "order_flow_direction", flow_direction)

                smile_width, crush_prob = self.get_volatility_smile_width(und, iv)
                _set(opp, "volatility_smile", smile_width)
                _set(opp, "crush_probability", crush_prob)

                # Detect crush catalyst
                crush_catalyst = "none"
                if opp.get("earnings_soon"):
                    crush_catalyst = "earnings"
                elif crush_prob >= 60:
                    crush_catalyst = "volatility_event"
                _set(opp, "crush_catalyst", crush_catalyst)

            except Exception as e:
                logger.debug(f"enrich_with_history item: {e}")

        return opportunities

    def get_score_sparklines(self, option_symbols: list, window_days: int = 7) -> dict:
        """
        Returns {option_symbol: [score_d1, ..., score_latest]} for each symbol.
        Ordered oldest → newest. Days with no data are skipped (no nulls).
        Requires ≥ 2 data points to be useful — single-point symbols are
        included so the caller can decide to skip them.
        """
        if not option_symbols or not os.path.exists(self.db_path):
            return {}

        cutoff = (datetime.now() - timedelta(days=window_days)).strftime("%Y-%m-%d")
        placeholders = ",".join("?" * len(option_symbols))

        con = self._open()
        if con is None:
            return {}
        try:
            rows = con.execute(
                f"""
                SELECT option_symbol, scan_date, whale_score
                FROM option_history
                WHERE option_symbol IN ({placeholders})
                  AND scan_date >= ?
                  AND whale_score > 0
                ORDER BY option_symbol, scan_date ASC
                """,
                option_symbols + [cutoff],
            ).fetchall()

            result: dict = {}
            for sym, _date, score in rows:
                if sym not in result:
                    result[sym] = []
                result[sym].append(round(float(score), 1))
            return result
        except Exception as exc:
            logger.debug(f"get_score_sparklines: {exc}")
            return {}
        finally:
            con.close()

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
