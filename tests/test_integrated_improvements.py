#!/usr/bin/env python3
"""
Test d'intégration complète des améliorations du starter
Valide toutes les nouvelles fonctionnalités ajoutées
"""

import os
import sys
import time
import json
from datetime import datetime
from typing import Dict, Any
import logging

# Ajout du répertoire parent et data au path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data'))

# Imports des modules
try:
    from data.enhanced_tradier_client import EnhancedTradierClient, OptionsContract, OptionsSymbolParser
except ImportError:
    # Fallback pour les tests sans le module
    print("⚠️ Module enhanced_tradier_client non trouvé, certains tests seront ignorés")
    EnhancedTradierClient = None
    OptionsContract = None
    OptionsSymbolParser = None

try:
    from data.enhanced_options_alerts import (
        EnhancedOptionsAnalyzer, TradingRecommendationEngine,
        OptionsAlert, TradingRecommendation, AlertType, TradingAction, RiskLevel
    )
except ImportError:
    print("⚠️ Module enhanced_options_alerts non trouvé, certains tests seront ignorés")
    EnhancedOptionsAnalyzer = None

try:
    from data.integrated_screening_engine import IntegratedScreeningEngine
except ImportError:
    print("⚠️ Module integrated_screening_engine non trouvé, certains tests seront ignorés")
    IntegratedScreeningEngine = None

# Configuration logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IntegratedImprovementsTest:
    """Test complet des améliorations intégrées"""
    
    def __init__(self):
        self.test_results = {
            'tests_passed': 0,
            'tests_failed': 0,
            'test_details': []
        }
        
        # Configuration des clés API
        self.tradier_token = os.getenv('TRADIER_API_TOKEN')
        self.polygon_key = os.getenv('POLYGON_API_KEY')
        
        logger.info("Test d'intégration des améliorations initialisé")
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Lance tous les tests d'intégration"""
        print("🧪 TESTS D'INTÉGRATION - AMÉLIORATIONS DU STARTER")
        print("=" * 60)
        
        # 1. Test du parseur de symboles
        self.test_symbol_parser()
        
        # 2. Test du client Tradier amélioré
        if self.tradier_token:
            self.test_enhanced_tradier_client()
        else:
            self._log_test_skip("Client Tradier", "TRADIER_API_TOKEN manquant")
        
        # 3. Test du système d'alertes
        self.test_options_analyzer()
        
        # 4. Test du moteur de recommandations
        self.test_recommendation_engine()
        
        # 5. Test du moteur intégré (si tokens disponibles)
        if self.tradier_token:
            self.test_integrated_screening_engine()
        else:
            self._log_test_skip("Moteur intégré", "TRADIER_API_TOKEN manquant")
        
        # Résumé final
        self._print_final_summary()
        return self.test_results
    
    def test_symbol_parser(self):
        """Test du parseur de symboles d'options"""
        print("\n📋 Test du parseur de symboles d'options...")
        
        if OptionsSymbolParser is None:
            self._log_test_skip("Parseur de symboles", "Module non disponible")
            return
        
        try:
            parser = OptionsSymbolParser()
            
            # Test avec un symbole valide
            test_symbol = "AAPL240315C00150000"
            parsed = parser.parse_option_symbol(test_symbol)
            
            assert parsed is not None, "Parsing échoué"
            assert parsed['underlying'] == 'AAPL', f"Underlying incorrect: {parsed['underlying']}"
            assert parsed['expiration'] == '2024-03-15', f"Expiration incorrecte: {parsed['expiration']}"
            assert parsed['option_type'] == 'call', f"Type incorrect: {parsed['option_type']}"
            assert parsed['strike'] == 150.0, f"Strike incorrect: {parsed['strike']}"
            
            # Test avec un symbole PUT
            put_symbol = "TSLA240315P00200000"
            parsed_put = parser.parse_option_symbol(put_symbol)
            
            assert parsed_put is not None, "Parsing PUT échoué"
            assert parsed_put['option_type'] == 'put', "Type PUT incorrect"
            assert parsed_put['strike'] == 200.0, "Strike PUT incorrect"
            
            # Test avec un symbole invalide
            invalid_symbol = "INVALID"
            parsed_invalid = parser.parse_option_symbol(invalid_symbol)
            assert parsed_invalid is None, "Parsing invalide aurait dû échouer"
            
            self._log_test_success("Parseur de symboles", "Parsing correct des symboles OCC")
            
        except Exception as e:
            self._log_test_failure("Parseur de symboles", str(e))
    
    def test_enhanced_tradier_client(self):
        """Test du client Tradier amélioré"""
        print("\n🔗 Test du client Tradier amélioré...")
        
        if EnhancedTradierClient is None:
            self._log_test_skip("Client Tradier amélioré", "Module non disponible")
            return
        
        try:
            client = EnhancedTradierClient(self.tradier_token, sandbox=True)
            
            # Test 1: Récupération du sous-jacent
            underlying = client.get_underlying_quote("AAPL")
            assert underlying is not None, "Récupération sous-jacent échouée"
            assert 'price' in underlying, "Prix manquant dans les données sous-jacent"
            assert underlying['price'] > 0, "Prix sous-jacent invalide"
            
            # Test 2: Récupération des expirations
            expirations = client.get_options_expirations("AAPL")
            assert len(expirations) > 0, "Aucune expiration trouvée"
            assert all(isinstance(exp, str) for exp in expirations), "Format expirations incorrect"
            
            # Test 3: Récupération d'une chaîne d'options
            chains = client.get_options_chains("AAPL", expirations[0])
            assert len(chains) > 0, "Aucun contrat dans la chaîne"
            
            # Vérification d'un contrat
            first_contract = chains[0]
            assert isinstance(first_contract, OptionsContract), "Type de contrat incorrect"
            assert first_contract.symbol, "Symbole manquant"
            assert first_contract.underlying == "AAPL", "Sous-jacent incorrect"
            
            # Test 4: Calcul des métriques
            if first_contract.bid > 0 and first_contract.ask > 0:
                assert first_contract.mid_price is not None, "Prix médian non calculé"
                assert first_contract.spread is not None, "Spread non calculé"
            
            # Test 5: Cache
            # Deuxième appel doit utiliser le cache
            start_time = time.time()
            chains2 = client.get_options_chains("AAPL", expirations[0])
            cache_time = time.time() - start_time
            assert cache_time < 0.1, "Cache ne fonctionne pas (trop lent)"
            assert len(chains2) == len(chains), "Cache retourne des données différentes"
            
            self._log_test_success("Client Tradier", f"API fonctionnelle, {len(chains)} contrats récupérés")
            
        except Exception as e:
            self._log_test_failure("Client Tradier", str(e))
    
    def test_options_analyzer(self):
        """Test de l'analyseur d'options avancé"""
        print("\n🔍 Test de l'analyseur d'options...")
        
        if EnhancedOptionsAnalyzer is None:
            self._log_test_skip("Analyseur d'options", "Module non disponible")
            return
        
        try:
            analyzer = EnhancedOptionsAnalyzer()
            
            # Données de test pour un contrat avec volume élevé
            test_contract = {
                'symbol': 'AAPL240315C00150000',
                'underlying': 'AAPL',
                'strike': 150.0,
                'option_type': 'call',
                'expiration': '2024-03-15',
                'bid': 2.50,
                'ask': 2.55,
                'last': 2.52,
                'volume': 25000,  # Volume élevé pour déclencher une alerte
                'open_interest': 15000,
                'delta': 0.65
            }
            
            # Données du sous-jacent
            underlying_data = {
                'price': 148.50,
                'change_percent': 0.02
            }
            
            # Test d'analyse - première fois (pas d'historique)
            alert1 = analyzer.analyze_option_contract(test_contract, underlying_data)
            # Peut être None si pas assez d'historique
            
            # Ajout d'historique de volume pour déclencher une anomalie
            for i in range(10):
                test_volume = 1000 + (i * 100)  # Volumes normaux
                analyzer.volume_manager.add_volume(test_contract['symbol'], test_volume)
            
            # Maintenant avec un volume très élevé
            test_contract['volume'] = 50000  # 25x le volume normal
            alert2 = analyzer.analyze_option_contract(test_contract, underlying_data)
            
            assert alert2 is not None, "Alerte non générée pour volume anormal"
            assert isinstance(alert2, OptionsAlert), "Type d'alerte incorrect"
            assert alert2.severity > 0.3, f"Sévérité trop faible: {alert2.severity}"
            assert alert2.unusual_volume_ratio > 3.0, f"Ratio de volume incorrect: {alert2.unusual_volume_ratio}"
            assert alert2.alert_type in [AlertType.UNUSUAL_CALL_VOLUME, AlertType.ANOMALY_DETECTED], "Type d'alerte incorrect"
            
            # Test du Z-score
            z_score = analyzer.volume_manager.get_z_score(test_contract['symbol'])
            assert z_score is not None, "Z-score non calculé"
            assert z_score > 2.0, f"Z-score trop faible: {z_score}"
            
            self._log_test_success("Analyseur d'options", f"Alerte générée (sévérité: {alert2.severity:.2f})")
            
        except Exception as e:
            self._log_test_failure("Analyseur d'options", str(e))
    
    def test_recommendation_engine(self):
        """Test du moteur de recommandations"""
        print("\n💡 Test du moteur de recommandations...")
        
        try:
            engine = TradingRecommendationEngine()
            
            # Création d'une alerte de test
            test_alert = OptionsAlert(
                ticker="AAPL",
                contract="AAPL240315C00150000",
                alert_type=AlertType.UNUSUAL_CALL_VOLUME,
                severity=0.8,
                confidence=0.75,
                volume=25000,
                avg_volume=1000,
                open_interest=15000,
                price_change=0.05,
                unusual_volume_ratio=5.2,
                timestamp=datetime.now(),
                description="Volume inhabituel sur CALL $150",
                data_source='test',
                bid=2.50,
                ask=2.55,
                last_price=2.52,
                strike=150.0,
                expiration="2024-03-15",
                option_type="call",
                time_to_expiry=30
            )
            
            # Test de génération de recommandation
            recommendation = engine.generate_recommendation(test_alert)
            
            assert recommendation is not None, "Recommandation non générée"
            assert isinstance(recommendation, TradingRecommendation), "Type de recommandation incorrect"
            assert recommendation.ticker == "AAPL", "Ticker incorrect"
            assert recommendation.action in [TradingAction.BUY_CALL, TradingAction.MONITOR], "Action incorrect"
            assert recommendation.confidence > 0, "Confiance invalide"
            assert recommendation.risk_level in list(RiskLevel), "Niveau de risque invalide"
            
            # Test avec une alerte de faible sévérité
            low_severity_alert = test_alert
            low_severity_alert.severity = 0.2
            low_rec = engine.generate_recommendation(low_severity_alert)
            
            # Devrait recommander MONITOR pour faible sévérité
            if low_rec:
                assert low_rec.action == TradingAction.MONITOR, "Action incorrecte pour faible sévérité"
            
            self._log_test_success("Moteur de recommandations", 
                                 f"Recommandation: {recommendation.action.value} (confiance: {recommendation.confidence:.2f})")
            
        except Exception as e:
            self._log_test_failure("Moteur de recommandations", str(e))
    
    def test_integrated_screening_engine(self):
        """Test du moteur de screening intégré"""
        print("\n🚀 Test du moteur de screening intégré...")
        
        try:
            # Initialisation avec des paramètres de test légers
            engine = IntegratedScreeningEngine(
                tradier_token=self.tradier_token,
                polygon_api_key=self.polygon_key,
                tradier_sandbox=True
            )
            
            # Test avec une petite watchlist
            test_watchlist = ["AAPL"]  # Un seul symbole pour test rapide
            
            # Paramètres de test moins restrictifs
            test_params = {
                'min_volume': 10,
                'min_open_interest': 100,
                'max_days_to_expiry': 30,
                'max_concurrent_symbols': 1
            }
            
            print("  Lancement du screening de test...")
            start_time = time.time()
            
            # Lancement du screening
            results = engine.run_comprehensive_screening(
                watchlist=test_watchlist,
                custom_params=test_params
            )
            
            duration = time.time() - start_time
            
            # Vérifications des résultats
            assert isinstance(results, dict), "Format de résultats incorrect"
            assert 'session_info' in results, "Informations de session manquantes"
            assert 'statistics' in results, "Statistiques manquantes"
            assert 'alerts' in results, "Alertes manquantes"
            assert 'recommendations' in results, "Recommandations manquantes"
            
            # Vérification des statistiques
            stats = results['statistics']
            assert stats['symbols_analyzed'] >= 1, "Aucun symbole analysé"
            assert stats['end_time'] is not None, "Heure de fin manquante"
            
            # Vérification du contenu
            session_info = results['session_info']
            assert session_info['watchlist_size'] == 1, "Taille watchlist incorrecte"
            assert session_info['duration_seconds'] > 0, "Durée incorrecte"
            
            # Test de sauvegarde
            filename = engine.save_results(results, "test_integrated_results.json")
            assert os.path.exists(filename), "Fichier de résultats non créé"
            
            # Nettoyage
            if os.path.exists(filename):
                os.remove(filename)
            
            self._log_test_success("Moteur intégré", 
                                 f"Screening complété en {duration:.1f}s - {stats['contracts_analyzed']} contrats analysés")
            
        except Exception as e:
            self._log_test_failure("Moteur intégré", str(e))
    
    def _log_test_success(self, test_name: str, details: str):
        """Log un test réussi"""
        self.test_results['tests_passed'] += 1
        self.test_results['test_details'].append({
            'test': test_name,
            'status': 'PASSED',
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
        print(f"✅ {test_name}: {details}")
    
    def _log_test_failure(self, test_name: str, error: str):
        """Log un test échoué"""
        self.test_results['tests_failed'] += 1
        self.test_results['test_details'].append({
            'test': test_name,
            'status': 'FAILED',
            'error': error,
            'timestamp': datetime.now().isoformat()
        })
        print(f"❌ {test_name}: {error}")
    
    def _log_test_skip(self, test_name: str, reason: str):
        """Log un test sauté"""
        self.test_results['test_details'].append({
            'test': test_name,
            'status': 'SKIPPED',
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })
        print(f"⏭️  {test_name}: Sauté ({reason})")
    
    def _print_final_summary(self):
        """Affiche le résumé final des tests"""
        total_tests = self.test_results['tests_passed'] + self.test_results['tests_failed']
        passed = self.test_results['tests_passed']
        failed = self.test_results['tests_failed']
        
        print("\n" + "=" * 60)
        print("📊 RÉSUMÉ DES TESTS D'INTÉGRATION")
        print("=" * 60)
        print(f"Total des tests: {total_tests}")
        print(f"✅ Réussis: {passed}")
        print(f"❌ Échoués: {failed}")
        print(f"📈 Taux de réussite: {(passed/total_tests*100):.1f}%" if total_tests > 0 else "N/A")
        
        if failed == 0:
            print("\n🎉 TOUS LES TESTS SONT PASSÉS !")
            print("Les améliorations du starter sont correctement intégrées.")
        else:
            print(f"\n⚠️  {failed} test(s) ont échoué. Vérifiez les détails ci-dessus.")

def main():
    """Fonction principale"""
    tester = IntegratedImprovementsTest()
    
    try:
        results = tester.run_all_tests()
        
        # Sauvegarde des résultats de test
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        test_filename = f"test_integrated_improvements_{timestamp}.json"
        
        with open(test_filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Résultats de test sauvegardés: {test_filename}")
        
        # Code de sortie
        exit_code = 0 if results['tests_failed'] == 0 else 1
        sys.exit(exit_code)
        
    except Exception as e:
        logger.error(f"Erreur fatale pendant les tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()