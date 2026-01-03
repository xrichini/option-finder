#!/usr/bin/env python3
"""
Test avec données simulées réalistes
Valide la logique métier sans dépendre des APIs externes
"""

import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, Any
import logging
import random
import pandas as pd

# Ajout du répertoire data au path
sys.path.append(os.path.join(os.path.dirname(__file__), 'data'))

# Configuration logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_realistic_options_data(symbol: str = "AAPL", underlying_price: float = 180.0) -> Dict[str, Any]:
    """Génère des données d'options réalistes pour les tests"""
    
    # Générer des expirations futures
    today = datetime.now().date()
    expirations = []
    for weeks in [1, 2, 4, 8, 12]:
        exp_date = today + timedelta(weeks=weeks)
        # Ajustement au vendredi (jour d'expiration typique)
        while exp_date.weekday() != 4:  # 4 = vendredi
            exp_date += timedelta(days=1)
        expirations.append(exp_date.strftime('%Y-%m-%d'))
    
    # Générer des strikes autour du prix actuel
    strikes = []
    for offset in range(-10, 11):
        strike = round(underlying_price + (offset * 5), 0)  # Strikes par incréments de $5
        if strike > 0:
            strikes.append(strike)
    
    # Données du sous-jacent
    underlying_data = {
        'symbol': symbol,
        'price': underlying_price,
        'bid': underlying_price - 0.05,
        'ask': underlying_price + 0.05,
        'change': random.uniform(-5.0, 5.0),
        'change_percentage': random.uniform(-3.0, 3.0),
        'volume': random.randint(50000, 200000)
    }
    
    # Générer les contrats d'options
    contracts = []
    for expiration in expirations[:3]:  # Limiter pour les tests
        days_to_exp = (datetime.strptime(expiration, '%Y-%m-%d').date() - today).days
        
        for strike in strikes:
            for option_type in ['call', 'put']:
                # Calcul de la moneyness
                if option_type == 'call':
                    itm = underlying_price > strike
                    moneyness = underlying_price - strike
                else:
                    itm = underlying_price < strike
                    moneyness = strike - underlying_price
                
                # Prix et volatilité basés sur moneyness et temps
                if itm:
                    intrinsic_value = max(0, moneyness)
                else:
                    intrinsic_value = 0
                
                time_value = max(0.01, random.uniform(0.1, 2.0) * (days_to_exp / 30))
                option_price = intrinsic_value + time_value
                
                # Volume basé sur moneyness (plus de volume près de ATM)
                distance_from_atm = abs(strike - underlying_price)
                volume_multiplier = max(0.1, 1.0 - (distance_from_atm / 50))
                base_volume = random.randint(100, 5000)
                volume = int(base_volume * volume_multiplier)
                
                # Parfois générer des volumes anormalement élevés
                if random.random() < 0.1:  # 10% de chance
                    volume = volume * random.randint(3, 15)  # Volume 3-15x normal
                
                # Open Interest
                open_interest = random.randint(volume // 2, volume * 3)
                
                # Greeks simulés
                delta = None
                gamma = None
                theta = None
                vega = None
                
                if option_type == 'call':
                    if itm:
                        delta = random.uniform(0.5, 0.9)
                    else:
                        delta = random.uniform(0.1, 0.5)
                else:
                    if itm:
                        delta = random.uniform(-0.9, -0.5)
                    else:
                        delta = random.uniform(-0.5, -0.1)
                
                gamma = random.uniform(0.001, 0.05)
                theta = random.uniform(-0.1, -0.01)
                vega = random.uniform(0.01, 0.3)
                
                # Construction du symbole OCC
                exp_str = datetime.strptime(expiration, '%Y-%m-%d').strftime('%y%m%d')
                option_symbol = f"{symbol}{exp_str}{'C' if option_type == 'call' else 'P'}{int(strike * 1000):08d}"
                
                contract = {
                    'symbol': option_symbol,
                    'underlying': symbol,
                    'expiration': expiration,
                    'strike': strike,
                    'option_type': option_type,
                    'bid': max(0.01, option_price - 0.05),
                    'ask': option_price + 0.05,
                    'last': option_price,
                    'volume': volume,
                    'open_interest': open_interest,
                    'delta': delta,
                    'gamma': gamma,
                    'theta': theta,
                    'vega': vega,
                    'implied_volatility': random.uniform(0.15, 0.50),
                    'change': random.uniform(-0.5, 0.5),
                    'change_percentage': random.uniform(-20, 20)
                }
                
                contracts.append(contract)
    
    return {
        'underlying': underlying_data,
        'expirations': expirations,
        'contracts': contracts,
        'timestamp': datetime.now().isoformat()
    }

def test_options_analyzer_with_simulated_data():
    """Test de l'analyseur avec données simulées"""
    print("🔍 Test de l'analyseur avec données simulées...")
    
    try:
        from enhanced_options_alerts import EnhancedOptionsAnalyzer, TradingRecommendationEngine
        
        analyzer = EnhancedOptionsAnalyzer()
        rec_engine = TradingRecommendationEngine()
        
        # Génération de données test
        print("  📊 Génération de données réalistes...")
        test_data = generate_realistic_options_data("AAPL", 175.0)
        
        underlying_data = test_data['underlying']
        contracts = test_data['contracts']
        
        print(f"  ✅ {len(contracts)} contrats simulés générés")
        
        # Simulation d'historique pour quelques contrats
        high_volume_contracts = sorted(contracts, key=lambda c: c['volume'], reverse=True)[:10]
        
        alerts_generated = 0
        recommendations_generated = 0
        
        print("  🔍 Analyse des contrats à volume élevé...")
        
        for contract in high_volume_contracts:
            # Simulation d'historique de volume normal
            symbol = contract['symbol']
            current_volume = contract['volume']
            
            # Ajout d'historique avec volumes plus faibles pour créer une anomalie
            for i in range(15):
                normal_volume = random.randint(50, 500)  # Volume normal bas
                analyzer.volume_manager.add_volume(symbol, normal_volume)
            
            # Analyse du contrat (avec le volume actuel élevé)
            alert = analyzer.analyze_option_contract(contract, underlying_data)
            
            if alert:
                alerts_generated += 1
                print(f"    🚨 Alerte: {alert.alert_type.value} - "
                      f"Sévérité: {alert.severity:.2f} - "
                      f"Ratio: {alert.unusual_volume_ratio:.1f}x")
                
                # Test de recommandation
                recommendation = rec_engine.generate_recommendation(alert)
                if recommendation:
                    recommendations_generated += 1
                    print(f"    💡 Rec: {recommendation.action.value} "
                          f"(Confiance: {recommendation.confidence:.2f}, "
                          f"Risque: {recommendation.risk_level.value})")
        
        print("  ✅ Analyse terminée:")
        print(f"    🚨 {alerts_generated} alertes générées")
        print(f"    💡 {recommendations_generated} recommandations générées")
        
        # Vérifications
        assert alerts_generated > 0, "Aucune alerte générée"
        assert recommendations_generated > 0, "Aucune recommandation générée"
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integrated_screening_with_simulated_data():
    """Test du moteur intégré avec données simulées"""
    print("\n🚀 Test du moteur de screening avec données simulées...")
    
    try:
        # Mock des clients pour éviter les appels API
        class MockTradierClient:
            def __init__(self, token, sandbox=True):
                self.test_data = {
                    'AAPL': generate_realistic_options_data('AAPL', 175.0),
                    'TSLA': generate_realistic_options_data('TSLA', 250.0)
                }
            
            def get_underlying_quote(self, symbol):
                return self.test_data.get(symbol, {}).get('underlying')
            
            def get_options_expirations(self, symbol):
                return self.test_data.get(symbol, {}).get('expirations', [])
            
            def get_options_chains(self, symbol, expiration=None):
                contracts = self.test_data.get(symbol, {}).get('contracts', [])
                if expiration:
                    contracts = [c for c in contracts if c['expiration'] == expiration]
                
                # Convertir en objets OptionsContract simulés
                from enhanced_tradier_client import OptionsContract
                option_contracts = []
                for c in contracts:
                    try:
                        contract = OptionsContract(
                            symbol=c['symbol'],
                            underlying=c['underlying'],
                            expiration=c['expiration'],
                            strike=c['strike'],
                            option_type=c['option_type'],
                            bid=c['bid'],
                            ask=c['ask'],
                            last=c['last'],
                            volume=c['volume'],
                            open_interest=c['open_interest'],
                            delta=c.get('delta'),
                            gamma=c.get('gamma'),
                            theta=c.get('theta'),
                            vega=c.get('vega'),
                            implied_volatility=c.get('implied_volatility')
                        )
                        option_contracts.append(contract)
                    except Exception:
                        continue
                
                return option_contracts
        
        # Mock du moteur intégré
        print("  🔧 Initialisation avec données simulées...")
        
        from enhanced_options_alerts import EnhancedOptionsAnalyzer, TradingRecommendationEngine
        from advanced_anomaly_detector import AdvancedAnomalyDetector
        
        # Composants réels
        options_analyzer = EnhancedOptionsAnalyzer()
        recommendation_engine = TradingRecommendationEngine()
        anomaly_detector = AdvancedAnomalyDetector()
        
        # Client mocké
        mock_client = MockTradierClient("fake_token")
        
        # Simulation de screening
        test_watchlist = ["AAPL", "TSLA"]
        print(f"  📋 Simulation screening: {test_watchlist}")
        
        all_alerts = []
        all_recommendations = []
        contracts_analyzed = 0
        
        start_time = time.time()
        
        for symbol in test_watchlist:
            print(f"    📈 Analyse {symbol}...")
            
            # Données du sous-jacent
            underlying = mock_client.get_underlying_quote(symbol)
            if not underlying:
                continue
            
            # Expirations
            expirations = mock_client.get_options_expirations(symbol)
            if not expirations:
                continue
            
            # Contrats d'options
            for expiration in expirations[:2]:  # Limiter pour test
                contracts = mock_client.get_options_chains(symbol, expiration)
                contracts_analyzed += len(contracts)
                
                # Analyse de chaque contrat
                for contract in contracts:
                    # Simulation d'historique
                    for i in range(10):
                        # Éviter l'erreur randint avec des volumes très faibles
                        max_normal_vol = max(50, contract.volume // 5)
                        normal_vol = random.randint(10, max_normal_vol)
                        options_analyzer.volume_manager.add_volume(contract.symbol, normal_vol)
                    
                    # Analyse
                    alert = options_analyzer.analyze_option_contract(contract.to_dict(), underlying)
                    if alert:
                        all_alerts.append(alert)
                        
                        # Recommandation
                        rec = recommendation_engine.generate_recommendation(alert)
                        if rec:
                            all_recommendations.append(rec)
        
        duration = time.time() - start_time
        
        # Résultats
        print(f"  ✅ Screening simulé terminé en {duration:.1f}s")
        print(f"    📋 Contrats analysés: {contracts_analyzed}")
        print(f"    🚨 Alertes générées: {len(all_alerts)}")
        print(f"    💡 Recommandations: {len(all_recommendations)}")
        
        # Top alertes
        if all_alerts:
            top_alerts = sorted(all_alerts, key=lambda a: a.severity * a.confidence, reverse=True)[:3]
            print("    🏆 Top 3 alertes:")
            for i, alert in enumerate(top_alerts, 1):
                print(f"      {i}. {alert.ticker} - {alert.alert_type.value} "
                      f"(Score: {alert.severity * alert.confidence:.2f})")
        
        # Vérifications
        assert contracts_analyzed > 0, "Aucun contrat analysé"
        assert len(all_alerts) > 0, "Aucune alerte générée"
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ml_anomaly_detection():
    """Test de détection d'anomalies ML"""
    print("\n🤖 Test de détection d'anomalies ML...")
    
    try:
        from advanced_anomaly_detector import AdvancedAnomalyDetector
        
        detector = AdvancedAnomalyDetector()
        
        # Génération de données de test
        print("  📊 Génération de dataset de test...")
        data = generate_realistic_options_data("AAPL", 180.0)
        contracts = data['contracts']
        
        # Conversion en DataFrame
        df = pd.DataFrame([
            {
                'symbol': c['symbol'],
                'volume': c['volume'],
                'last': c['last'],
                'open_interest': c['open_interest'],
                'implied_volatility': c.get('implied_volatility', 0.25),
                'strike': c['strike'],
                'option_type': c['option_type']
            }
            for c in contracts
        ])
        
        print(f"  ✅ {len(df)} contrats pour analyse ML")
        
        # Test de détection d'anomalies
        print("  🔍 Détection d'anomalies ML...")
        anomalies = detector.detect_anomalies_dataframe(
            df, 
            volume_col='volume',
            price_col='last'
        )
        
        print(f"  ✅ {len(anomalies)} anomalies détectées")
        
        if len(anomalies) > 0:
            print("    🏆 Top 3 anomalies ML:")
            top_anomalies = anomalies.head(3)
            for i, (idx, anomaly) in enumerate(top_anomalies.iterrows(), 1):
                print(f"      {i}. {anomaly['symbol']} - "
                      f"Z-score: {anomaly.get('volume_z_score', 'N/A'):.2f}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur ML: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Test principal avec données simulées"""
    print("🧪 TESTS COMPLETS AVEC DONNÉES SIMULÉES")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Analyseur d'options
    tests_total += 1
    if test_options_analyzer_with_simulated_data():
        tests_passed += 1
    
    # Test 2: Détection ML
    tests_total += 1
    if test_ml_anomaly_detection():
        tests_passed += 1
    
    # Test 3: Moteur intégré simulé
    tests_total += 1
    if test_integrated_screening_with_simulated_data():
        tests_passed += 1
    
    # Résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DES TESTS SIMULÉS")
    print("=" * 60)
    print(f"Tests passés: {tests_passed}/{tests_total}")
    print(f"Taux de réussite: {(tests_passed/tests_total*100):.1f}%")
    
    if tests_passed == tests_total:
        print("\n🎉 TOUS LES TESTS SIMULÉS SONT PASSÉS !")
        print("✅ La logique métier fonctionne parfaitement !")
        print("✅ Les améliorations du starter sont opérationnelles !")
        print("\n💡 Note: Pour les tests avec vraies APIs:")
        print("   - Vérifiez votre token Tradier dans .streamlit/secrets.toml")
        print("   - Le token doit être valide et activé")
    else:
        print(f"\n⚠️ {tests_total - tests_passed} test(s) ont échoué")
    
    return tests_passed == tests_total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)