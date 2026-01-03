#!/usr/bin/env python3
"""
Integrated Options Screening Engine
Moteur de screening unifié combinant:
- Les bonnes idées du options_screening_starter.py
- Notre architecture hybride Tradier/Polygon.io
- Le système d'alertes avancé
- La détection d'anomalies ML
"""

import os
import sys
import time
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import des modules de notre architecture
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from enhanced_tradier_client import EnhancedTradierClient, OptionsContract
from enhanced_options_alerts import (
    EnhancedOptionsAnalyzer, 
    TradingRecommendationEngine,
    OptionsAlert,
    TradingRecommendation
)
from hybrid_data_manager import HybridDataManager
from advanced_anomaly_detector import AdvancedAnomalyDetector

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntegratedScreeningEngine:
    """
    Moteur de screening intégré combinant toutes nos améliorations
    """
    
    def __init__(self, tradier_token: str, polygon_api_key: Optional[str] = None, 
                 tradier_sandbox: bool = False):
        """
        Initialise le moteur de screening intégré
        
        Args:
            tradier_token: Token Tradier pour données temps réel
            polygon_api_key: Clé API Polygon.io pour historique (optionnel)
            tradier_sandbox: Utiliser l'environnement sandbox Tradier
        """
        self.tradier_token = tradier_token
        self.polygon_api_key = polygon_api_key
        self.tradier_sandbox = tradier_sandbox
        
        # Initialisation des composants
        self.tradier_client = EnhancedTradierClient(tradier_token, tradier_sandbox)
        self.hybrid_manager = HybridDataManager(tradier_token, polygon_api_key)
        self.options_analyzer = EnhancedOptionsAnalyzer()
        self.recommendation_engine = TradingRecommendationEngine()
        self.anomaly_detector = AdvancedAnomalyDetector()
        
        # Configuration par défaut
        self.default_watchlist = [
            'AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL', 'AMZN', 'META',
            'SPY', 'QQQ', 'IWM', 'NFLX', 'AMD', 'BABA', 'CRM'
        ]
        
        # Paramètres de screening
        self.screening_params = {
            'min_volume': 100,
            'min_open_interest': 500,
            'max_days_to_expiry': 60,
            'min_days_to_expiry': 1,
            'volume_ratio_threshold': 2.0,
            'max_spread_percentage': 50.0,
            'min_price': 0.05,
            'max_concurrent_symbols': 5
        }
        
        # Statistiques de session
        self.session_stats = {
            'symbols_analyzed': 0,
            'contracts_analyzed': 0,
            'alerts_generated': 0,
            'recommendations_generated': 0,
            'start_time': None,
            'end_time': None
        }
        
        logger.info("Moteur de screening intégré initialisé")
    
    def run_comprehensive_screening(self, watchlist: Optional[List[str]] = None,
                                  custom_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Lance une session de screening complète avec tous les modules
        
        Args:
            watchlist: Liste de symboles à analyser (défaut: watchlist par défaut)
            custom_params: Paramètres de screening personnalisés
        
        Returns:
            Résultats complets du screening
        """
        # Initialisation de la session
        self.session_stats['start_time'] = datetime.now()
        watchlist = watchlist or self.default_watchlist
        
        if custom_params:
            self.screening_params.update(custom_params)
        
        logger.info(f"=== DÉBUT SCREENING COMPLET - {len(watchlist)} symboles ===")
        
        try:
            # 1. Screening par symbole (parallélisé)
            all_alerts = []
            all_recommendations = []
            symbol_results = {}
            
            with ThreadPoolExecutor(max_workers=self.screening_params['max_concurrent_symbols']) as executor:
                # Soumission des tâches
                future_to_symbol = {
                    executor.submit(self._screen_single_symbol, symbol): symbol 
                    for symbol in watchlist
                }
                
                # Collecte des résultats
                for future in as_completed(future_to_symbol):
                    symbol = future_to_symbol[future]
                    try:
                        result = future.result(timeout=300)  # 5 minutes max par symbole
                        if result:
                            symbol_results[symbol] = result
                            all_alerts.extend(result.get('alerts', []))
                            all_recommendations.extend(result.get('recommendations', []))
                    except Exception as e:
                        logger.error(f"Erreur screening {symbol}: {e}")
                        continue
            
            # 2. Analyse des corrélations entre symboles
            correlations = self._analyze_cross_symbol_patterns(all_alerts)
            
            # 3. Ranking global et filtrage
            top_alerts = self._rank_and_filter_alerts(all_alerts)
            top_recommendations = self._rank_and_filter_recommendations(all_recommendations)
            
            # 4. Génération de stratégies de portefeuille
            portfolio_strategies = self._generate_portfolio_strategies(top_recommendations)
            
            # 5. Calcul des statistiques finales
            self._finalize_session_stats(len(watchlist), all_alerts, all_recommendations)
            
            # 6. Compilation des résultats
            results = {
                'session_info': {
                    'timestamp': datetime.now().isoformat(),
                    'watchlist_size': len(watchlist),
                    'symbols_processed': len(symbol_results),
                    'duration_seconds': (datetime.now() - self.session_stats['start_time']).total_seconds(),
                    'screening_params': self.screening_params
                },
                'statistics': self.session_stats.copy(),
                'alerts': {
                    'total_count': len(all_alerts),
                    'top_alerts': [alert.to_dict() if hasattr(alert, 'to_dict') else alert for alert in top_alerts],
                    'by_severity': self._group_alerts_by_severity(top_alerts)
                },
                'recommendations': {
                    'total_count': len(all_recommendations),
                    'top_recommendations': [rec.to_dict() if hasattr(rec, 'to_dict') else rec for rec in top_recommendations],
                    'by_action': self._group_recommendations_by_action(top_recommendations)
                },
                'correlations': correlations,
                'portfolio_strategies': portfolio_strategies,
                'symbol_results': symbol_results,
                'watchlist': watchlist
            }
            
            logger.info(f"=== SCREENING TERMINÉ - {len(all_alerts)} alertes, {len(all_recommendations)} recommandations ===")
            return results
            
        except Exception as e:
            logger.error(f"Erreur screening complet: {e}")
            raise
    
    def _screen_single_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Screening complet d'un symbole unique
        
        Returns:
            Résultats du screening pour ce symbole
        """
        logger.info(f"Analyse de {symbol}...")
        
        try:
            start_time = time.time()
            
            # 1. Récupération du sous-jacent
            underlying_data = self.tradier_client.get_underlying_quote(symbol)
            if not underlying_data:
                logger.warning(f"Impossible de récupérer les données de {symbol}")
                return None
            
            # 2. Récupération des chaînes d'options
            expirations = self.tradier_client.get_options_expirations(symbol)
            if not expirations:
                logger.warning(f"Aucune expiration trouvée pour {symbol}")
                return None
            
            # Filtre les expirations dans notre plage
            filtered_expirations = self._filter_expirations(expirations)
            
            # 3. Analyse des contrats d'options
            all_contracts = []
            for expiration in filtered_expirations[:3]:  # Max 3 expirations par symbole
                contracts = self.tradier_client.get_options_chains(symbol, expiration)
                all_contracts.extend(self._filter_contracts(contracts, underlying_data))
            
            if not all_contracts:
                logger.info(f"Aucun contrat qualifié pour {symbol}")
                return None
            
            # 4. Détection d'anomalies et génération d'alertes
            symbol_alerts = []
            for contract in all_contracts:
                # Analyse avec notre système d'alertes avancé
                alert = self.options_analyzer.analyze_option_contract(
                    contract.to_dict(), underlying_data
                )
                if alert:
                    symbol_alerts.append(alert)
            
            # 5. Génération de recommandations
            symbol_recommendations = []
            for alert in symbol_alerts:
                recommendation = self.recommendation_engine.generate_recommendation(alert)
                if recommendation:
                    symbol_recommendations.append(recommendation)
            
            # 6. Analyse ML des anomalies (si données suffisantes)
            ml_anomalies = []
            if len(all_contracts) >= 10:
                try:
                    # Prépare les données pour l'analyse ML
                    contract_data = pd.DataFrame([c.to_dict() for c in all_contracts])
                    anomalies = self.anomaly_detector.detect_anomalies_dataframe(
                        contract_data, 
                        volume_col='volume',
                        price_col='last'
                    )
                    ml_anomalies = anomalies.to_dict('records') if not anomalies.empty else []
                except Exception as e:
                    logger.warning(f"Erreur analyse ML pour {symbol}: {e}")
            
            # 7. Compilation des résultats du symbole
            processing_time = time.time() - start_time
            result = {
                'symbol': symbol,
                'underlying_data': underlying_data,
                'contracts_analyzed': len(all_contracts),
                'alerts': symbol_alerts,
                'recommendations': symbol_recommendations,
                'ml_anomalies': ml_anomalies,
                'processing_time_seconds': processing_time,
                'top_volume_contracts': self._get_top_volume_contracts(all_contracts, 5),
                'summary': {
                    'total_alerts': len(symbol_alerts),
                    'high_severity_alerts': len([a for a in symbol_alerts if a.severity >= 0.7]),
                    'actionable_recommendations': len([r for r in symbol_recommendations 
                                                     if r.action.value not in ['MONITOR', 'AVOID']]),
                    'max_volume_ratio': max([a.unusual_volume_ratio for a in symbol_alerts], default=1.0)
                }
            }
            
            # Mise à jour des statistiques
            self.session_stats['contracts_analyzed'] += len(all_contracts)
            self.session_stats['alerts_generated'] += len(symbol_alerts)
            self.session_stats['recommendations_generated'] += len(symbol_recommendations)
            
            logger.info(f"✅ {symbol}: {len(symbol_alerts)} alertes, {len(symbol_recommendations)} recommandations ({processing_time:.1f}s)")
            return result
            
        except Exception as e:
            logger.error(f"Erreur screening {symbol}: {e}")
            return None
    
    def _filter_expirations(self, expirations: List[str]) -> List[str]:
        """Filtre les expirations selon nos critères"""
        filtered = []
        today = datetime.now().date()
        
        for exp_str in expirations:
            try:
                exp_date = datetime.strptime(exp_str, '%Y-%m-%d').date()
                days_to_expiry = (exp_date - today).days
                
                if (self.screening_params['min_days_to_expiry'] <= days_to_expiry <= 
                    self.screening_params['max_days_to_expiry']):
                    filtered.append(exp_str)
            except Exception:
                continue
        
        return sorted(filtered)
    
    def _filter_contracts(self, contracts: List[OptionsContract], 
                         underlying_data: Dict[str, Any]) -> List[OptionsContract]:
        """Filtre les contrats selon nos critères de screening"""
        filtered = []
        underlying_price = underlying_data.get('price', 0)
        
        for contract in contracts:
            # Critères de base
            if contract.volume < self.screening_params['min_volume']:
                continue
            
            if contract.open_interest < self.screening_params['min_open_interest']:
                continue
            
            if contract.last < self.screening_params['min_price']:
                continue
            
            # Critères de spread (si données disponibles)
            if (contract.bid > 0 and contract.ask > 0 and 
                contract.spread_percentage and 
                contract.spread_percentage > self.screening_params['max_spread_percentage']):
                continue
            
            # Calcul des métriques dérivées
            if underlying_price > 0:
                contract.moneyness = contract.calculate_moneyness(underlying_price)
                contract.intrinsic_value = contract.calculate_intrinsic_value(underlying_price)
            
            filtered.append(contract)
        
        return filtered
    
    def _get_top_volume_contracts(self, contracts: List[OptionsContract], 
                                 limit: int) -> List[Dict[str, Any]]:
        """Récupère les contrats avec le plus fort volume"""
        sorted_contracts = sorted(contracts, key=lambda c: c.volume, reverse=True)
        return [c.to_dict() for c in sorted_contracts[:limit]]
    
    def _analyze_cross_symbol_patterns(self, all_alerts: List[OptionsAlert]) -> Dict[str, Any]:
        """Analyse les corrélations et patterns entre symboles"""
        correlations = {
            'sector_patterns': {},
            'expiration_clusters': {},
            'strike_patterns': {},
            'alert_type_distribution': {}
        }
        
        if not all_alerts:
            return correlations
        
        try:
            # Groupement par type d'alerte
            alert_types = {}
            for alert in all_alerts:
                alert_type = alert.alert_type.value if hasattr(alert.alert_type, 'value') else str(alert.alert_type)
                if alert_type not in alert_types:
                    alert_types[alert_type] = []
                alert_types[alert_type].append(alert)
            
            correlations['alert_type_distribution'] = {
                k: len(v) for k, v in alert_types.items()
            }
            
            # Analyse des expirations communes
            exp_counts = {}
            for alert in all_alerts:
                exp = getattr(alert, 'expiration', None)
                if exp:
                    exp_counts[exp] = exp_counts.get(exp, 0) + 1
            
            correlations['expiration_clusters'] = dict(sorted(
                exp_counts.items(), key=lambda x: x[1], reverse=True
            )[:5])
            
        except Exception as e:
            logger.warning(f"Erreur analyse corrélations: {e}")
        
        return correlations
    
    def _rank_and_filter_alerts(self, all_alerts: List[OptionsAlert], 
                               max_alerts: int = 50) -> List[OptionsAlert]:
        """Classe et filtre les meilleures alertes"""
        if not all_alerts:
            return []
        
        # Tri par score combiné (sévérité * confiance)
        ranked_alerts = sorted(
            all_alerts,
            key=lambda a: a.severity * a.confidence,
            reverse=True
        )
        
        return ranked_alerts[:max_alerts]
    
    def _rank_and_filter_recommendations(self, all_recommendations: List[TradingRecommendation],
                                       max_recommendations: int = 30) -> List[TradingRecommendation]:
        """Classe et filtre les meilleures recommandations"""
        if not all_recommendations:
            return []
        
        # Tri par confiance
        ranked_recs = sorted(
            all_recommendations,
            key=lambda r: r.confidence,
            reverse=True
        )
        
        return ranked_recs[:max_recommendations]
    
    def _generate_portfolio_strategies(self, recommendations: List[TradingRecommendation]) -> List[Dict[str, Any]]:
        """Génère des stratégies de portefeuille basées sur les recommandations"""
        strategies = []
        
        if not recommendations:
            return strategies
        
        try:
            # Stratégie aggressive (high confidence + high risk)
            aggressive_recs = [r for r in recommendations 
                             if r.confidence >= 0.7 and r.risk_level.value in ['HIGH', 'EXTREME']]
            
            if aggressive_recs:
                strategies.append({
                    'name': 'Stratégie Aggressive',
                    'description': 'Positions à fort potentiel et risque élevé',
                    'recommendations': [r.to_dict() for r in aggressive_recs[:5]],
                    'risk_level': 'HIGH',
                    'expected_return': 'HIGH'
                })
            
            # Stratégie conservatrice
            conservative_recs = [r for r in recommendations 
                               if r.confidence >= 0.6 and r.risk_level.value in ['LOW', 'MEDIUM']]
            
            if conservative_recs:
                strategies.append({
                    'name': 'Stratégie Conservatrice',
                    'description': 'Positions équilibrées risque/rendement',
                    'recommendations': [r.to_dict() for r in conservative_recs[:5]],
                    'risk_level': 'MEDIUM',
                    'expected_return': 'MEDIUM'
                })
            
        except Exception as e:
            logger.warning(f"Erreur génération stratégies: {e}")
        
        return strategies
    
    def _group_alerts_by_severity(self, alerts: List[OptionsAlert]) -> Dict[str, int]:
        """Groupe les alertes par niveau de sévérité"""
        groups = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        
        for alert in alerts:
            if alert.severity >= 0.7:
                groups['HIGH'] += 1
            elif alert.severity >= 0.4:
                groups['MEDIUM'] += 1
            else:
                groups['LOW'] += 1
        
        return groups
    
    def _group_recommendations_by_action(self, recommendations: List[TradingRecommendation]) -> Dict[str, int]:
        """Groupe les recommandations par type d'action"""
        groups = {}
        
        for rec in recommendations:
            action = rec.action.value if hasattr(rec.action, 'value') else str(rec.action)
            groups[action] = groups.get(action, 0) + 1
        
        return groups
    
    def _finalize_session_stats(self, watchlist_size: int, all_alerts: List, all_recommendations: List):
        """Finalise les statistiques de session"""
        self.session_stats.update({
            'symbols_analyzed': watchlist_size,
            'end_time': datetime.now(),
            'total_alerts': len(all_alerts),
            'total_recommendations': len(all_recommendations),
            'high_severity_alerts': len([a for a in all_alerts if hasattr(a, 'severity') and a.severity >= 0.7]),
            'actionable_recommendations': len([r for r in all_recommendations 
                                             if hasattr(r, 'action') and 
                                             (r.action.value if hasattr(r.action, 'value') else str(r.action)) 
                                             not in ['MONITOR', 'AVOID']])
        })
    
    def save_results(self, results: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        Sauvegarde les résultats en JSON
        
        Returns:
            Nom du fichier sauvegardé
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"integrated_screening_results_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Résultats sauvegardés: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde: {e}")
            raise

# Exemple d'utilisation
if __name__ == "__main__":
    # Configuration
    TRADIER_TOKEN = os.getenv('TRADIER_API_TOKEN')
    POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')
    
    if not TRADIER_TOKEN:
        logger.error("❌ TRADIER_API_TOKEN requis!")
        exit(1)
    
    # Initialisation du moteur
    engine = IntegratedScreeningEngine(
        tradier_token=TRADIER_TOKEN,
        polygon_api_key=POLYGON_API_KEY,
        tradier_sandbox=True  # Mode sandbox pour les tests
    )
    
    # Test avec une watchlist réduite
    test_watchlist = ['AAPL', 'TSLA', 'SPY']
    
    print("🚀 Démarrage du screening intégré...")
    print(f"📋 Watchlist de test: {test_watchlist}")
    
    try:
        # Lancement du screening
        results = engine.run_comprehensive_screening(
            watchlist=test_watchlist,
            custom_params={'min_volume': 50, 'max_concurrent_symbols': 2}
        )
        
        # Affichage des résultats
        print("\n" + "="*70)
        print("📊 RÉSULTATS DU SCREENING INTÉGRÉ")
        print("="*70)
        
        stats = results['statistics']
        print(f"⏱️  Durée: {stats.get('end_time', datetime.now()) - stats.get('start_time', datetime.now())}")
        print(f"📈 Symboles analysés: {stats['symbols_analyzed']}")
        print(f"📋 Contrats analysés: {stats['contracts_analyzed']}")
        print(f"🚨 Alertes générées: {stats['alerts_generated']}")
        print(f"💡 Recommandations: {stats['recommendations_generated']}")
        
        # Top alertes
        top_alerts = results['alerts']['top_alerts'][:5]
        if top_alerts:
            print("\n🚨 TOP 5 ALERTES:")
            for i, alert in enumerate(top_alerts, 1):
                print(f"{i}. {alert.get('ticker', 'N/A')} - {alert.get('description', 'N/A')} "
                      f"(Sévérité: {alert.get('severity', 0):.2f})")
        
        # Top recommandations
        top_recs = results['recommendations']['top_recommendations'][:5]
        if top_recs:
            print("\n💡 TOP 5 RECOMMANDATIONS:")
            for i, rec in enumerate(top_recs, 1):
                print(f"{i}. {rec.get('ticker', 'N/A')} - {rec.get('action', 'N/A')} "
                      f"(Confiance: {rec.get('confidence', 0):.2f})")
        
        # Sauvegarde
        filename = engine.save_results(results)
        print(f"\n✅ Résultats sauvegardés: {filename}")
        
    except Exception as e:
        logger.error(f"❌ Erreur pendant le screening: {e}")
        raise