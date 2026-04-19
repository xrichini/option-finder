"""
Service de screening - Logique métier pure
Extrait la logique de screening de dashboard.py pour la rendre testable et réutilisable
"""

from typing import List, Dict, Any, Optional, Callable
import asyncio
import logging
from datetime import datetime

from models.api_models import OptionsChainSnapshot, OptionsOpportunity
from data.enhanced_tradier_client import EnhancedTradierClient
from services.config_service import ConfigService
from services.unusual_whales_service import UnusualWhalesService
from services.history_service import history_service
from utils.config import Config
from utils.market_utils import get_sector, compute_sizzle_index, compute_moneyness

logger = logging.getLogger(__name__)


class ScreeningService:
    """Service de screening d'options sans dépendances UI"""

    def __init__(self):
        self.config_service = ConfigService()
        # EnhancedTradierClient se configure automatiquement via Config
        self.tradier_client = EnhancedTradierClient(api_token="", sandbox=None)
        # Service Unusual Whales avec analyse historique
        self.unusual_whales_service = UnusualWhalesService(enable_historical=True)

    async def screen_options_classic(
        self,
        symbols: List[str],
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> List[OptionsOpportunity]:
        """
        Screening classique des options

        Args:
            symbols: Liste des symboles à analyser
            progress_callback: Callback optionnel pour le suivi du progrès (current, total, message)

        Returns:
            Liste des opportunités trouvées
        """

        params = self.config_service.get_screening_params()
        opportunities = []

        logger.info(f"Démarrage screening classique sur {len(symbols)} symboles")
        logger.debug(f"Paramètres: {params}")

        # --- Récupération en bulk des quotes sous-jacents (prix + volume) ---
        underlying_quotes: Dict[str, Dict] = {}
        try:
            underlying_quotes = self.tradier_client.get_multiple_underlying_quotes(
                symbols
            )
        except Exception as e:
            logger.warning(f"Impossible de récupérer les quotes sous-jacents: {e}")

        # --- Analyse parallèle par lots de 10 (asyncio.to_thread pour les appels bloquants) ---
        BATCH_SIZE = 10
        total = len(symbols)

        for batch_start in range(0, total, BATCH_SIZE):
            batch = symbols[batch_start : batch_start + BATCH_SIZE]

            tasks = [
                asyncio.to_thread(
                    self._analyze_symbol_sync, sym, params, underlying_quotes
                )
                for sym in batch
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for j, (sym, result) in enumerate(zip(batch, batch_results)):
                global_idx = batch_start + j + 1
                logger.info(f"\u23f3 [{global_idx}/{total}] {sym}")
                if progress_callback:
                    await progress_callback(global_idx, total, f"Analyse {sym}...")

                if isinstance(result, Exception):
                    logger.error(f"Erreur lors de l'analyse de {sym}: {result}")
                elif result:
                    opportunities.extend(result)

            # Pause entre les lots pour ne pas saturer Tradier (10 appels en rafale)
            if batch_start + BATCH_SIZE < total:
                await asyncio.sleep(0.5)

        if progress_callback:
            await progress_callback(len(symbols), len(symbols), "Screening terminé")

        # Tri par whale_score décroissant
        opportunities.sort(key=lambda x: x.whale_score, reverse=True)

        logger.info(f"Screening terminé: {len(opportunities)} opportunités trouvées")

        # --- Feed historique + enrichissement comparatif ---
        try:
            saved_count = self.unusual_whales_service.save_scan_results(opportunities)
            if saved_count > 0:
                logger.info(
                    f"💾 UnusualWhales: {saved_count} opportunités sauvegardées"
                )
        except Exception as e:
            logger.warning(f"Erreur sauvegarde unusual_whales: {e}")

        # Feed options_history.db (UPSERT un scan par jour)
        try:
            hist_count = history_service.record_scan_results(opportunities)
            logger.info(f"📅 Historique: {hist_count} lignes dans options_history.db")
        except Exception as e:
            logger.warning(f"Erreur feed history: {e}")

        # Enrichissement comparatif (IV Rank, IV Pct, OI Spike, Vol Trend)
        try:
            history_service.enrich_with_history(opportunities)
        except Exception as e:
            logger.warning(f"Erreur enrich_with_history: {e}")

        # #5: PUT/CALL FLOW RATIO — Détecte les patterns de hedging/accumulation
        try:
            pc_bonuses = self._calculate_put_call_flow_ratio(opportunities)
            for opp in opportunities:
                pc_bonus = pc_bonuses.get(opp.option_symbol, 0.0)
                if pc_bonus != 0.0:
                    old_score = opp.whale_score
                    opp.whale_score = min(100.0, opp.whale_score + pc_bonus)
                    signal = (
                        f"Call accumulation (+{pc_bonus:.0f})"
                        if pc_bonus > 0
                        else f"Defensive hedging ({pc_bonus:.0f})"
                    )
                    opp.reasoning = f"{opp.reasoning} | {signal}".strip(" |")
                    logger.debug(
                        f"{opp.option_symbol}: PC Flow {old_score:.1f}→{opp.whale_score:.1f}"
                    )
            logger.info(f"✅ Put/Call Flow: bonuses appliqués à whale_score")
        except Exception as e:
            logger.warning(f"⚠️  Put/Call Flow non disponible ({e})")

        # #3: OI MOMENTUM — Détecte les nouvelles positions ouvertes
        try:
            oi_bonuses = self._calculate_oi_momentum(opportunities)
            for opp in opportunities:
                oi_bonus = oi_bonuses.get(opp.option_symbol, 0.0)
                if oi_bonus != 0.0:
                    old_score = opp.whale_score
                    opp.whale_score = min(100.0, opp.whale_score + oi_bonus)
                    signal = (
                        f"OI spike (+{oi_bonus:.0f})"
                        if oi_bonus > 0
                        else f"OI decline ({oi_bonus:.0f})"
                    )
                    opp.reasoning = f"{opp.reasoning} | {signal}".strip(" |")
                    logger.debug(
                        f"{opp.option_symbol}: OI Momentum {old_score:.1f}→{opp.whale_score:.1f}"
                    )
            logger.info(f"✅ OI Momentum: bonuses appliqués à whale_score")
        except Exception as e:
            logger.warning(f"⚠️  OI Momentum non disponible ({e})")

        return opportunities

    async def screen_options_with_ai(
        self,
        symbols: List[str],
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        top_n: int = 5,
    ) -> List[OptionsOpportunity]:
        """
        Screening avec analyse IA - Version améliorée

        1. Fait d'abord un screening classique complet
        2. Applique des critères IA renforcés
        3. Limite aux Top N meilleures opportunités

        Args:
            symbols: Liste des symboles à analyser
            progress_callback: Callback optionnel pour le suivi du progrès
            top_n: Nombre max d'opportunités à retourner

        Returns:
            Liste des meilleures opportunités avec analyse IA
        """

        if not Config.has_ai_capabilities():
            logger.warning(
                "Capacités IA non disponibles, utilisation du screening classique"
            )
            return await self.screen_options_classic(symbols, progress_callback)

        logger.info(f"Démarrage screening IA sur {len(symbols)} symboles (Top {top_n})")

        # Phase 1: Screening classique complet
        if progress_callback:
            await progress_callback(0, 3, "Phase 1: Screening classique initial...")

        all_opportunities = await self.screen_options_classic(symbols, None)

        if not all_opportunities:
            logger.info("Aucune opportunité trouvée lors du screening initial")
            return []

        # Phase 2: Analyse IA renforcée
        if progress_callback:
            await progress_callback(
                1, 3, f"Phase 2: Analyse IA de {len(all_opportunities)} opportunités..."
            )

        # Critères IA renforcés
        ai_filtered = self._apply_ai_analysis(all_opportunities)

        # Phase 3: Sélection du Top N
        if progress_callback:
            await progress_callback(
                2, 3, f"Phase 3: Sélection des {top_n} meilleures..."
            )

        # Tri par score IA composite
        ai_filtered.sort(key=lambda x: x.whale_score, reverse=True)

        # Limitation au Top N
        final_opportunities = ai_filtered[:top_n]

        if progress_callback:
            await progress_callback(3, 3, "Analyse IA terminée")

        logger.info(
            f"Screening IA terminé: {len(final_opportunities)} opportunités (Top {top_n})"
        )
        return final_opportunities

    async def get_ai_trade_recommendations(
        self, screening_config: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Génère des recommandations de trades IA basées sur l'analyse des meilleures opportunités

        Args:
            screening_config: Configuration optionnelle de screening

        Returns:
            Liste des recommandations de trades
        """

        try:
            logger.info("Génération des recommandations de trades IA...")

            # Obtenir les symboles depuis la configuration
            symbol_params = self.config_service.get_symbol_loading_params()
            symbols = await self.get_symbol_suggestions(
                min_market_cap=symbol_params["min_market_cap"],
                min_volume=symbol_params["min_stock_volume"],
            )

            # Obtenir les meilleures opportunités avec analyse IA
            opportunities = await self.screen_options_with_ai(
                symbols, None, top_n=15
            )  # Plus d'opportunités pour avoir plus de choix

            if not opportunities:
                logger.warning(
                    "Aucune opportunité trouvée pour générer des recommandations"
                )
                return []

            # Générer les recommandations basées sur ces opportunités
            recommendations = self._generate_trade_recommendations(opportunities)

            # Limiter aux 10 meilleures recommandations
            top_recommendations = recommendations[:10]

            logger.info(f"Généré {len(top_recommendations)} recommandations de trades")

            return top_recommendations

        except Exception as e:
            logger.error(f"Erreur lors de la génération des recommandations: {e}")
            raise

    async def _get_options_chains_bulk(self, symbols: List[str]) -> Dict[str, List]:
        """
        Récupère les chaînes d'options pour plusieurs symboles
        EnhancedTradierClient ne fait pas de bulk, donc on boucle

        Args:
            symbols: Liste des symboles

        Returns:
            Dictionnaire {symbol: [OptionsContract]}
        """
        result = {}

        for symbol in symbols:
            try:
                contracts = self.tradier_client.get_options_chains(symbol)
                result[symbol] = contracts if contracts else []
            except Exception as e:
                logger.error(f"Erreur récupération chaînes {symbol}: {e}")
                result[symbol] = []

        return result

    def _analyze_symbol_sync(
        self,
        symbol: str,
        params: Dict[str, Any],
        underlying_quotes: Dict[str, Any],
    ) -> List:
        """
        Analyse synchrone d'un symbole (destinée à être appelée via asyncio.to_thread).
        Retourne une liste d'OptionsOpportunity ou [] si rien trouvé.
        """
        try:
            options_contracts = self.tradier_client.get_options_chains(symbol)
            if not options_contracts:
                logger.debug(f"Pas de chaînes d'options pour {symbol}")
                return []

            filtered_chains = self._filter_contracts_by_dte(
                options_contracts, params["max_dte"]
            )
            if not filtered_chains:
                logger.debug(
                    f"Pas d'expiration valide pour {symbol} (max_dte={params['max_dte']})"
                )
                return []

            symbol_opps = self._analyze_options_chains(
                symbol,
                filtered_chains,
                params,
                underlying_quote=underlying_quotes.get(symbol.upper(), {}),
            )
            logger.debug(f"{symbol}: {len(symbol_opps)} opportunités trouvées")
            return symbol_opps

        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de {symbol}: {e}")
            return []

    def _filter_contracts_by_dte(
        self, contracts: List, max_dte: int
    ) -> List[Dict[str, Any]]:
        """
        Filtre les contrats OptionsContract par DTE
        """

        if not contracts:
            return []

        filtered_options = []
        today = datetime.now().date()

        for contract in contracts:
            try:
                # Calcul du DTE — compare dates (not datetimes) to avoid
                # intraday rounding: strptime gives midnight, datetime.now()
                # has hours → floor truncates 3.9 days to 3 instead of 4.
                exp_date = datetime.strptime(contract.expiration, "%Y-%m-%d").date()
                dte = (exp_date - today).days

                if 0 <= dte <= max_dte:
                    option_dict = {
                        "symbol": contract.symbol,
                        "option_type": contract.option_type,
                        "strike": contract.strike,
                        "expiration_date": contract.expiration,
                        "dte": dte,
                        "volume": contract.volume or 0,
                        "open_interest": contract.open_interest or 0,
                        "bid": contract.bid or 0,
                        "ask": contract.ask or 0,
                        "last": contract.last or 0,
                        "change_pct": contract.change_percentage or 0.0,  # ← propagé
                        # Greeks depuis l'OptionsContract
                        "delta": contract.delta,
                        "gamma": contract.gamma,
                        "theta": contract.theta,
                        "vega": contract.vega,
                        "rho": contract.rho,
                        "implied_volatility": contract.implied_volatility,
                    }
                    filtered_options.append(option_dict)

            except (ValueError, AttributeError) as e:
                logger.debug(f"Erreur de parsing du contrat: {e}")
                continue

        return filtered_options

    def _filter_expirations_by_dte(
        self, chains: OptionsChainSnapshot, max_dte: int
    ) -> List[Dict[str, Any]]:
        """
        Filtre les expirations par DTE

        Args:
            chains: Chaînes d'options
            max_dte: DTE maximum

        Returns:
            Liste des options filtrées par expiration
        """

        if not chains or not hasattr(chains, "options") or not chains.options:
            return []

        filtered_options = []
        today = datetime.now().date()

        for option in chains.options.option:
            try:
                # Calcul du DTE — same date-only fix as _filter_contracts_by_dte
                exp_date = datetime.strptime(option.expiration_date, "%Y-%m-%d").date()
                dte = (exp_date - today).days

                if 0 <= dte <= max_dte:
                    option_dict = {
                        "symbol": option.symbol,
                        "option_type": option.option_type,
                        "strike": option.strike,
                        "expiration_date": option.expiration_date,
                        "dte": dte,
                        "volume": option.volume or 0,
                        "open_interest": option.open_interest or 0,
                        "bid": option.bid or 0,
                        "ask": option.ask or 0,
                        "last": option.last or 0,
                    }
                    filtered_options.append(option_dict)

            except (ValueError, AttributeError) as e:
                logger.debug(f"Erreur de parsing d'option: {e}")
                continue

        return filtered_options

    def _analyze_options_chains(
        self,
        symbol: str,
        options: List[Dict[str, Any]],
        params: Dict[str, Any],
        underlying_quote: Optional[Dict[str, Any]] = None,
    ) -> List[OptionsOpportunity]:
        """
        Analyse les chaînes d'options pour identifier les opportunités
        """
        opportunities = []
        underlying_price = (underlying_quote or {}).get("last", 0.0) or 0.0
        stock_volume = int((underlying_quote or {}).get("volume", 0) or 0)
        sector = get_sector(symbol)

        for option in options:
            try:
                volume = option["volume"]
                open_interest = option["open_interest"]

                if volume < params["min_volume"] or open_interest < params["min_oi"]:
                    continue

                # whale score
                whale_score = self._calculate_whale_score(option)
                if whale_score < params["min_whale_score"]:
                    continue

                vol_oi_ratio = round(volume / max(open_interest, 1), 2)
                sizzle = compute_sizzle_index(option["symbol"], volume)
                moneyness_label, moneyness_pct = compute_moneyness(
                    option["option_type"], option["strike"], underlying_price
                )

                # Order flow signals
                flow_signals = self._detect_order_flow_signals(option)

                opportunity = OptionsOpportunity(
                    underlying_symbol=symbol,
                    option_symbol=option["symbol"],
                    option_type=option["option_type"],
                    strike=option["strike"],
                    expiration_date=option["expiration_date"],
                    dte=option["dte"],
                    volume=volume,
                    open_interest=open_interest,
                    bid=option["bid"],
                    ask=option["ask"],
                    last=option["last"],
                    whale_score=whale_score,
                    reasoning="Critères de volume et OI respectés",
                    # Greeks
                    delta=option.get("delta"),
                    gamma=option.get("gamma"),
                    theta=option.get("theta"),
                    vega=option.get("vega"),
                    rho=option.get("rho"),
                    implied_volatility=option.get("implied_volatility"),
                    # --- Champs enrichis ---
                    vol_oi_ratio=vol_oi_ratio,
                    change_pct=float(option.get("change_pct", 0.0) or 0.0),
                    stock_volume=stock_volume,
                    underlying_price=underlying_price,
                    sector=sector,
                    sizzle_index=sizzle,
                    moneyness=moneyness_label,
                    moneyness_pct=moneyness_pct,
                    # Order flow signals
                    has_block_trade=flow_signals["block_trade"],
                    spread_compression_pct=flow_signals["spread_pct"],
                    net_flow_direction=flow_signals["flow_direction"],
                )
                opportunities.append(opportunity)

            except Exception as e:
                logger.error(
                    f"Erreur analyse option {option.get('symbol', 'N/A')}: {e}"
                )
                continue

        return opportunities

    def _detect_order_flow_signals(self, option: Dict[str, Any]) -> Dict[str, Any]:
        """
        Détecte les signaux d'order flow pour une option.

        Retourne:
        {
            'block_trade': bool,
            'spread_pct': float,
            'flow_direction': str ('bullish'|'bearish'|'neutral')
        }
        """
        try:
            volume = option.get("volume", 0)
            bid = option.get("bid", 0)
            ask = option.get("ask", 0)
            last = option.get("last", 0)

            # Block Trade Detection
            block_trade = volume >= 100

            # Spread Compression
            spread_pct = 100.0
            if bid > 0 and ask > 0:
                mid_price = (bid + ask) / 2
                spread_pct = (
                    round((ask - bid) / mid_price * 100, 2) if mid_price > 0 else 100
                )

            # Net Flow Indicator
            flow_direction = "neutral"
            if last > 0 and bid > 0 and ask > 0:
                mid_price = (bid + ask) / 2
                distance_to_ask = abs(last - ask)
                distance_to_bid = abs(last - bid)

                if distance_to_ask < distance_to_bid:
                    flow_direction = "bullish"  # Last closer to ask = buying pressure
                elif distance_to_bid < distance_to_ask:
                    flow_direction = "bearish"  # Last closer to bid = selling pressure

            return {
                "block_trade": block_trade,
                "spread_pct": spread_pct,
                "flow_direction": flow_direction,
            }

        except Exception as e:
            logger.debug(f"Error detecting order flow signals: {e}")
            return {
                "block_trade": False,
                "spread_pct": 100.0,
                "flow_direction": "neutral",
            }

    def _calculate_whale_score(self, option: Dict[str, Any]) -> float:
        """
        Calcule le whale score pour une option avec signaux d'order flow.

        Basé sur:
        - Volume/OI ratio volatilité
        - Volume absolu
        - Open Interest
        - DTE penalty
        - Block Trade Detection (volume spike)
        - Spread Compression (liquidité institutionnelle)
        - Net Flow Indicator (bid/ask imbalance)

        Args:
            option: Données de l'option

        Returns:
            Score whale (0-100)
        """

        try:
            volume = option["volume"]
            open_interest = option["open_interest"]
            dte = option["dte"]
            bid = option.get("bid", 0)
            ask = option.get("ask", 0)
            last = option.get("last", 0)

            if volume <= 0 or open_interest <= 0:
                return 0.0

            # ============ BASE SCORE ============

            # Score basé sur le ratio volume/OI
            volume_oi_ratio = volume / max(open_interest, 1)

            # Bonus pour les volumes élevés
            volume_score = min(volume / 1000, 10)

            # Bonus pour les OI élevés
            oi_score = min(open_interest / 500, 10)

            # Malus pour les DTE très courts ou très longs
            dte_penalty = 1.0
            if dte < 1:
                dte_penalty = 0.5
            elif dte > 30:
                dte_penalty = 0.8

            raw_score = (volume_oi_ratio * 20 + volume_score + oi_score) * dte_penalty

            # ============ ORDER FLOW SIGNALS ============

            flow_bonus = 0.0

            # #1: BLOCK TRADE DETECTION
            # Volume spike = potentiel block trade
            if volume >= 100:  # Seuil minimum pour considérer un block trade
                flow_bonus += 3.0  # +3 points pour block trade potentiel

            # #4: SPREAD COMPRESSION
            # Spread faible % = meilleure liquidité = activity institutionnelle probable
            if bid > 0 and ask > 0:
                mid_price = (bid + ask) / 2
                spread_pct = ((ask - bid) / mid_price * 100) if mid_price > 0 else 100

                # Bonus décroissant selon la compression du spread
                if spread_pct < 0.5:
                    flow_bonus += 5.0  # Très serré = whale activity très probable
                elif spread_pct < 1.0:
                    flow_bonus += 3.5
                elif spread_pct < 2.0:
                    flow_bonus += 2.0
                elif spread_pct < 5.0:
                    flow_bonus += 1.0

            # #2: NET FLOW INDICATOR
            # Note: Sans données de bid/ask imbalance en temps réel,
            # on utilise une heuristique sur le dernier prix vs mid
            # (Simplifié: si last proche de ask = accumulation/buying)
            if last > 0 and bid > 0 and ask > 0:
                mid_price = (bid + ask) / 2
                distance_to_ask = abs(last - ask)
                distance_to_bid = abs(last - bid)

                # Si last plus proche de ask = buying pressure
                if distance_to_ask < distance_to_bid:
                    flow_bonus += 2.0

            # Score final avec bonus d'order flow
            final_score = raw_score + flow_bonus
            return min(final_score, 100.0)

        except Exception as e:
            logger.error(f"Erreur calcul whale score: {e}")
            return 0.0

    def _calculate_put_call_flow_ratio(
        self, opportunities: List[OptionsOpportunity]
    ) -> Dict[str, float]:
        """
        Calcule le ratio put/call par underlying et retourne les bonus pour chaque opp.

        Détecte les patterns de hedging/buying:
        - Put/Call ratio > 1.5 = Defensive buying (bearish signal, -1 bonus)
        - Put/Call ratio < 0.67 = Call accumulation (bullish signal, +2 bonus)
        - Put/Call ratio 0.67-1.5 = Normal (neutral, 0 bonus)

        Returns:
            Dict[option_symbol] -> bonus_points (float)
        """
        try:
            # Agrégation volumes par underlying et option_type
            underlying_flows: Dict[str, Dict[str, int]] = {}

            for opp in opportunities:
                und = opp.underlying_symbol
                if und not in underlying_flows:
                    underlying_flows[und] = {"call": 0, "put": 0}

                opt_type = str(opp.option_type).upper()
                if opt_type == "CALL":
                    underlying_flows[und]["call"] += opp.volume
                elif opt_type == "PUT":
                    underlying_flows[und]["put"] += opp.volume

            # Calcul bonus par option
            bonuses: Dict[str, float] = {}
            for opp in opportunities:
                und = opp.underlying_symbol
                call_vol = underlying_flows[und]["call"]
                put_vol = underlying_flows[und]["put"]

                ratio = put_vol / max(call_vol, 1)  # Avoid division by zero
                bonus = 0.0

                if ratio > 1.5:
                    # Hedging/defensive buying detected
                    bonus = -1.0 if str(opp.option_type).upper() == "CALL" else +1.5
                elif ratio < 0.67:
                    # Call accumulation detected
                    bonus = +2.0 if str(opp.option_type).upper() == "CALL" else -1.0

                bonuses[opp.option_symbol] = bonus

            logger.debug(
                f"Put/Call Flow: calculé pour {len(underlying_flows)} underlyings"
            )
            return bonuses

        except Exception as e:
            logger.warning(f"Erreur calcul put/call flow: {e}")
            return {}

    def _calculate_oi_momentum(
        self, opportunities: List[OptionsOpportunity]
    ) -> Dict[str, float]:
        """
        Calcule le momentum OI en comparant OI actuelle avec OI hier (depuis DB).

        Bonus:
        - OI +30%+ = +3 points (new big positions)
        - OI +15-30% = +1 point (moderate increase)
        - OI -20% ou moins = -2 points (positions closing)

        Returns:
            Dict[option_symbol] -> bonus_points (float)
        """
        try:
            bonuses: Dict[str, float] = {}

            for opp in opportunities:
                try:
                    # Query yesterday's OI from history_service
                    yesterday_oi = history_service.get_yesterday_oi(opp.option_symbol)

                    if yesterday_oi is None or yesterday_oi <= 0:
                        bonuses[opp.option_symbol] = 0.0
                        continue

                    # Calculate OI change %
                    oi_change_pct = (
                        (opp.open_interest - yesterday_oi) / yesterday_oi
                    ) * 100
                    bonus = 0.0

                    if oi_change_pct >= 30:
                        bonus = 3.0  # New big positions opening
                    elif oi_change_pct >= 15:
                        bonus = 1.0  # Moderate increase
                    elif oi_change_pct <= -20:
                        bonus = -2.0  # Positions closing

                    bonuses[opp.option_symbol] = bonus

                except Exception as e:
                    logger.debug(f"OI Momentum error for {opp.option_symbol}: {e}")
                    bonuses[opp.option_symbol] = 0.0

            logger.debug(f"OI Momentum: calculé pour {len(opportunities)} options")
            return bonuses

        except Exception as e:
            logger.warning(f"Erreur calcul OI momentum: {e}")
            return {}

    async def get_symbol_suggestions(
        self, min_market_cap: Optional[int] = None, min_volume: Optional[int] = None
    ) -> List[str]:
        """
        Récupère des suggestions de symboles basées sur les critères

        Args:
            min_market_cap: Capitalisation minimum
            min_volume: Volume minimum

        Returns:
            Liste de symboles suggérés
        """

        try:
            # Utilisation des paramètres de config si non fournis
            symbol_params = self.config_service.get_symbol_loading_params()

            if min_market_cap is None:
                min_market_cap = symbol_params["min_market_cap"]
            if min_volume is None:
                min_volume = symbol_params["min_stock_volume"]

            # Pour l'instant, retourne une liste statique
            # TODO: Implémenter la récupération dynamique depuis une API
            suggested_symbols = [
                "AAPL",
                "MSFT",
                "GOOGL",
                "AMZN",
                "TSLA",
                "META",
                "NVDA",
                "NFLX",
                "SPY",
                "QQQ",
                "AMD",
                "INTC",
                "BABA",
                "CRM",
                "UBER",
            ]

            logger.info(f"Suggestions de symboles: {len(suggested_symbols)} symboles")
            return suggested_symbols

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des suggestions: {e}")
            return []

    async def validate_symbols(self, symbols: List[str]) -> Dict[str, bool]:
        """
        Valide une liste de symboles

        Args:
            symbols: Liste des symboles à valider

        Returns:
            Dictionnaire {symbole: is_valid}
        """

        validation_results = {}

        for symbol in symbols:
            try:
                # Test de récupération des chaînes d'options
                contracts = self.tradier_client.get_options_chains(symbol)
                validation_results[symbol] = (
                    contracts is not None and len(contracts) > 0
                )
            except Exception as e:
                logger.debug(f"Symbole {symbol} invalide: {e}")
                validation_results[symbol] = False

        return validation_results

    def _apply_ai_analysis(
        self, opportunities: List[OptionsOpportunity]
    ) -> List[OptionsOpportunity]:
        """
        Applique des critères d'analyse IA renforcés

        Args:
            opportunities: Liste des opportunités du screening classique

        Returns:
            Liste filtrée et enrichie avec analyse IA
        """

        ai_opportunities = []

        for opp in opportunities:
            try:
                # Calcul du score IA composite
                ai_score = self._calculate_ai_score(opp)

                # Critères IA renforcés (plus stricts que le classique)
                if (
                    ai_score >= 70  # Score IA minimum
                    and opp.whale_score >= 40  # Whale score plus strict
                    and opp.volume >= 200  # Volume plus strict
                    and opp.open_interest >= 100  # OI plus strict
                ):
                    # Enrichissement avec analyse IA
                    opp.whale_score = ai_score  # Remplace par le score IA
                    opp.reasoning = self._generate_ai_reasoning(opp)
                    opp.ai_analysis = {
                        "confidence": min(ai_score / 100, 1.0),
                        "method": "enhanced_ai_screening",
                        "factors": self._get_ai_factors(opp),
                        "risk_level": self._assess_risk_level(opp),
                    }

                    ai_opportunities.append(opp)

            except Exception as e:
                logger.error(f"Erreur analyse IA pour {opp.option_symbol}: {e}")
                continue

        logger.info(
            f"Analyse IA: {len(ai_opportunities)}/{len(opportunities)} opportunités retenues"
        )
        return ai_opportunities

    def _calculate_ai_score(self, opp: OptionsOpportunity) -> float:
        """
        Calcule un score IA avec méthologie Unusual Whales v3 et analyse historique

        Args:
            opp: Opportunité à analyser

        Returns:
            Score IA (0-100)
        """

        try:
            # Utilisation de la méthodologie Unusual Whales v3
            whale_score_v3, scoring_details = (
                self.unusual_whales_service.calculate_whale_score_v3(
                    volume_1d=opp.volume,
                    open_interest=opp.open_interest,
                    option_symbol=opp.option_symbol,
                )
            )

            # Sauvegarde des détails d'analyse pour utilisation ultérieure
            # Utilisation d'un dictionnaire temporaire car OptionsOpportunity est immutable
            if not hasattr(opp, "_temp_uw_analysis"):
                setattr(opp, "_temp_uw_analysis", scoring_details)

            return whale_score_v3

        except Exception as e:
            logger.error(
                f"Erreur calcul score Unusual Whales pour {opp.option_symbol}: {e}"
            )
            return opp.whale_score  # Fallback vers le score original

    def _generate_ai_reasoning(self, opp: OptionsOpportunity) -> str:
        """
        Génère un raisonnement IA pour l'opportunité
        """

        reasons = []

        if opp.volume >= 500:
            reasons.append(f"Volume exceptionnel ({opp.volume:,})")
        elif opp.volume >= 200:
            reasons.append(f"Volume élevé ({opp.volume:,})")

        if opp.open_interest >= 500:
            reasons.append(f"OI important ({opp.open_interest:,})")

        if opp.open_interest > 0:
            ratio = opp.volume / opp.open_interest
            if ratio >= 2.0:
                reasons.append(f"Ratio V/OI exceptionnel ({ratio:.1f}x)")
            elif ratio >= 1.5:
                reasons.append(f"Ratio V/OI élevé ({ratio:.1f}x)")

        if 3 <= opp.dte <= 14:
            reasons.append(f"DTE optimal ({opp.dte}j)")

        base = f"IA: {opp.underlying_symbol} {opp.option_type.upper()}"
        if reasons:
            return f"{base} - {', '.join(reasons)}"
        else:
            return f"{base} - Critères IA respectés"

    def _get_ai_factors(self, opp: OptionsOpportunity) -> Dict[str, Any]:
        """
        Récupère les facteurs d'analyse IA
        """

        return {
            "volume_score": min(opp.volume / 1000 * 30, 30),
            "oi_score": min(opp.open_interest / 500 * 25, 25),
            "vol_oi_ratio": (
                opp.volume / opp.open_interest if opp.open_interest > 0 else 0
            ),
            "dte_optimal": 3 <= opp.dte <= 14,
            "spread_quality": (
                "good"
                if opp.bid > 0 and (opp.ask - opp.bid) / opp.bid < 0.15
                else "wide"
            ),
        }

    def _assess_risk_level(self, opp: OptionsOpportunity) -> str:
        """
        Évalue le niveau de risque
        """

        if opp.dte <= 2:
            return "high"  # Expiration très proche
        elif opp.dte >= 20:
            return "medium"  # Expiration lointaine
        elif opp.volume >= 500 and opp.open_interest >= 200:
            return "low"  # Volume et OI solides
        else:
            return "medium"

    def _generate_trade_recommendations(
        self, opportunities: List[OptionsOpportunity]
    ) -> List[Dict[str, Any]]:
        """
        Génère des recommandations de trades basées sur l'analyse IA

        Args:
            opportunities: Liste des opportunités analysées

        Returns:
            Liste des recommandations avec stratégies
        """

        recommendations = []

        for opp in opportunities:
            try:
                # Détermination de la stratégie recommandée
                strategy = self._determine_strategy(opp)

                # Calcul des niveaux de prix
                price_targets = self._calculate_price_targets(opp)

                # Évaluation du risk/reward
                risk_reward = self._assess_risk_reward(opp)

                # Déterminer l'action recommandée
                trade_action = self._determine_trade_action(opp)

                recommendation = {
                    # Informations de base
                    "symbol": opp.underlying_symbol,
                    "option_symbol": opp.option_symbol,
                    # Détails de l'option (données réelles)
                    "option_type": opp.option_type.upper(),  # CALL/PUT
                    "strike": opp.strike,
                    "expiration_date": opp.expiration_date,
                    "dte": opp.dte,
                    "volume": opp.volume,
                    "open_interest": opp.open_interest,
                    "bid": opp.bid,
                    "ask": opp.ask,
                    # Recommandation de trade
                    "trade_action": trade_action["action"],  # "ACHAT" ou "VENTE"
                    "trade_type": f"{trade_action['action']} {opp.option_type.upper()}",  # "ACHAT CALL"
                    "full_recommendation": f"{trade_action['action']} {opp.option_symbol}",
                    # Stratégie et timing
                    "strategy": strategy["name"],
                    "strategy_description": strategy["description"],
                    "entry_price": opp.last,
                    "time_horizon": f"{opp.dte} jours",
                    # Prix cibles (calculés)
                    "target_price": price_targets["target"],
                    "stop_loss": price_targets["stop_loss"],
                    "max_risk": price_targets["max_risk"],
                    "potential_return": price_targets["potential_return"],
                    # Métriques d'analyse
                    "risk_reward_ratio": risk_reward["ratio"],
                    "probability_success": risk_reward["probability"],
                    "confidence_level": (
                        opp.ai_analysis.get("confidence", 0.5)
                        if opp.ai_analysis
                        else 0.5
                    ),
                    # Analyse de marché
                    "market_outlook": self._get_market_outlook(opp),
                    "key_factors": self._get_key_factors(opp),
                    "warnings": self._get_trade_warnings(opp),
                }

                recommendations.append(recommendation)

            except Exception as e:
                logger.error(
                    f"Erreur génération recommandation pour {opp.option_symbol}: {e}"
                )
                continue

        # Tri par niveau de confiance décroissant (puis par potentiel de rendement)
        recommendations.sort(
            key=lambda x: (x["confidence_level"], x["potential_return"]), reverse=True
        )

        return recommendations

    def _determine_strategy(self, opp: OptionsOpportunity) -> Dict[str, str]:
        """
        Détermine la stratégie de trading recommandée
        """

        if opp.dte <= 3:
            return {
                "name": "Scalping",
                "description": "Position courte durée avec prise de profits rapide",
            }
        elif opp.dte <= 7:
            return {
                "name": "Swing Court",
                "description": "Position 1-7 jours, capitaliser sur les mouvements directionnels",
            }
        elif opp.dte <= 14:
            return {
                "name": "Swing Moyen",
                "description": "Position 1-2 semaines, profiter de la tendance",
            }
        else:
            return {
                "name": "Position Long",
                "description": "Position plus long terme avec gestion du theta",
            }

    def _calculate_price_targets(self, opp: OptionsOpportunity) -> Dict[str, float]:
        """
        Calcule les niveaux de prix cibles
        """

        entry_price = opp.last

        # Calculs basés sur la volatilité implicite ou des heuristiques
        if opp.dte <= 3:
            # Trading court terme - objectifs conservateurs
            target_multiplier = 1.5
            stop_multiplier = 0.7
        elif opp.dte <= 7:
            # Swing court - objectifs modérés
            target_multiplier = 2.0
            stop_multiplier = 0.6
        else:
            # Position plus longue - objectifs ambitieux
            target_multiplier = 3.0
            stop_multiplier = 0.5

        target_price = entry_price * target_multiplier
        stop_loss = entry_price * stop_multiplier
        max_risk = entry_price - stop_loss
        potential_return = target_price - entry_price

        return {
            "target": target_price,
            "stop_loss": stop_loss,
            "max_risk": max_risk,
            "potential_return": potential_return,
        }

    def _assess_risk_reward(self, opp: OptionsOpportunity) -> Dict[str, float]:
        """
        Évalue le ratio risque/rendement
        """

        price_targets = self._calculate_price_targets(opp)

        if price_targets["max_risk"] > 0:
            ratio = price_targets["potential_return"] / price_targets["max_risk"]
        else:
            ratio = 0

        # Probabilité de succès basée sur les métriques
        base_prob = 0.4  # Probabilité de base

        # Ajustements basés sur les indicateurs
        if opp.volume >= 500:
            base_prob += 0.1  # Volume élevé
        if opp.open_interest >= 200:
            base_prob += 0.1  # OI solide
        if opp.whale_score >= 80:
            base_prob += 0.15  # Score IA élevé

        # Pénalités
        if opp.dte <= 2:
            base_prob -= 0.1  # Expiration proche

        probability = min(base_prob, 0.85)  # Cap à 85%

        return {"ratio": ratio, "probability": probability}

    def _get_market_outlook(self, opp: OptionsOpportunity) -> str:
        """
        Détermine l'outlook de marché
        """

        if opp.option_type.lower() == "call":
            if opp.volume >= 500:
                return "Fortement haussier"
            else:
                return "Modérément haussier"
        else:
            if opp.volume >= 500:
                return "Fortement baissier"
            else:
                return "Modérément baissier"

    def _get_key_factors(self, opp: OptionsOpportunity) -> List[str]:
        """
        Identifie les facteurs clés avec méthodologie Unusual Whales
        """

        factors = []

        # Analyse Unusual Whales complète
        try:
            uw_analysis = self.unusual_whales_service.analyze_opportunity(opp)

            # Volume et blocs institutionnels
            if uw_analysis.get("institutional_signal"):
                factors.append(
                    f"{uw_analysis.get('block_category')} - Signal institutionnel"
                )
            elif opp.volume >= 1000:
                factors.append(
                    f"{uw_analysis.get('block_category')} - Volume élevé ({opp.volume:,})"
                )

            # Ratio Volume/OI
            vol_oi_ratio = uw_analysis.get("vol_oi_ratio", 0)
            if vol_oi_ratio == float("inf"):
                factors.append("♾️ Nouveau contrat (OI=0)")
            elif vol_oi_ratio >= 5.0:
                factors.append(f"🔥 Ratio V/OI exceptionnel ({vol_oi_ratio:.1f}x)")
            elif vol_oi_ratio >= 2.0:
                factors.append(f"Ratio V/OI élevé ({vol_oi_ratio:.1f}x)")

            # Anomalies historiques
            if hasattr(opp, "_temp_uw_analysis") and opp._temp_uw_analysis:
                if opp._temp_uw_analysis.get("volume_anomaly", 0) >= 70:
                    vol_stats = opp._temp_uw_analysis.get("historical_stats", {}).get(
                        "volume_stats", {}
                    )
                    if vol_stats.get("volume_ratio", 0) >= 3:
                        factors.append(
                            f"📈 Volume {vol_stats['volume_ratio']:.0f}x supérieur à la moyenne"
                        )

                if opp._temp_uw_analysis.get("oi_anomaly", 0) >= 50:
                    factors.append("📈 Open Interest inhabituel vs historique")

            # Activité inhabituelle
            if uw_analysis.get("unusual_activity"):
                factors.append("🚨 Activité inhabituelle détectée")

            # Nouvelles positions
            if uw_analysis.get("new_position"):
                factors.append("✅ Nouvelles positions probables")

        except Exception as e:
            logger.warning(f"Erreur analyse UW pour facteurs: {e}")
            # Fallback vers l'ancienne logique
            if opp.volume >= 1000:
                factors.append("Volume exceptionnel détecté")

        # Facteurs temporels
        if opp.dte <= 3:
            factors.append("⏰ Expiration imminente - effet gamma maximal")
        elif opp.dte <= 7:
            factors.append("🔥 Expiration proche - effet gamma important")

        return factors

    def _get_trade_warnings(self, opp: OptionsOpportunity) -> List[str]:
        """
        Génère les avertissements
        """

        warnings = []

        if opp.dte <= 2:
            warnings.append(
                "⚠️ Expiration très proche - risque de décote temporelle élevé"
            )

        if opp.bid <= 0 or opp.ask <= 0:
            warnings.append("⚠️ Spread large - attention à la liquidité")
        elif opp.bid > 0 and (opp.ask - opp.bid) / opp.bid > 0.2:
            warnings.append("⚠️ Spread élevé - coût de transaction important")

        if opp.volume < 100:
            warnings.append("⚠️ Volume faible - difficultés d'exécution possibles")

        if opp.open_interest < 50:
            warnings.append("⚠️ Open Interest faible - liquidité limitée")

        return warnings

    def _determine_trade_action(self, opp: OptionsOpportunity) -> Dict[str, str]:
        """
        Détermine l'action recommandée : Achat ou Vente

        Logique simple basée sur l'activité détectée :
        - Volume élevé + OI normal = Achat probable (nouveaux positions)
        - Volume modéré + OI élevé = Peut indiquer fermeture de positions existantes
        """

        vol_oi_ratio = opp.volume / max(opp.open_interest, 1)

        # Logique de détermination
        if vol_oi_ratio >= 1.5:  # Volume beaucoup plus élevé que OI
            if opp.volume >= 500:
                action = "ACHAT"  # Forte activité d'achat probable
                reason = "Volume exceptionnel suggère nouveaux achats"
            else:
                action = "ACHAT"  # Activité d'achat modérée
                reason = "Ratio V/OI élevé indique activité d'achat"
        else:
            # Volume plus équilibré avec OI
            if opp.volume >= 300:
                action = "ACHAT"  # Toujours privilégier l'achat pour simplifier
                reason = "Volume solide avec liquidité"
            else:
                action = "ACHAT"  # Par défaut : achat
                reason = "Position d'achat recommandée"

        return {"action": action, "reason": reason}
