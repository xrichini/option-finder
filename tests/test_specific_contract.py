#!/usr/bin/env python3
"""
Test spécifique pour récupérer les Greeks d'un contrat AAPL précis
AAPL CALL, exp 19/09/2025, strike 110$
"""

import os
import sys
import logging
from datetime import datetime

# Ajouter le répertoire racine au path pour importer les modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.enhanced_tradier_client import EnhancedTradierClient

# Configuration des logs pour voir tout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_specific_aapl_contract():
    """Test pour récupérer les données d'un contrat AAPL spécifique"""
    
    print("=" * 80)
    print("🎯 TEST SPÉCIFIQUE: AAPL CALL 110$ exp 19/09/2025")
    print("=" * 80)
    
    try:
        # Configuration automatique depuis Config
        client = EnhancedTradierClient(api_token="", sandbox=None)
        
        print(f"Environment: {'Sandbox' if client.sandbox else 'Production'}")
        print(f"Base URL: {client.base_url}")
        
        # Test avec AAPL
        symbol = "AAPL"
        target_expiration = "2025-09-19"
        target_strike = 110.0
        
        print(f"\n🔍 Recherche: {symbol} CALL {target_strike}$ exp {target_expiration}")
        
        # Récupérer la chaîne d'options pour cette expiration
        print("\n📡 Récupération de la chaîne d'options...")
        contracts = client.get_options_chains(symbol, target_expiration)
        
        print(f"   Contrats récupérés: {len(contracts)}")
        
        # Filtrer pour trouver le contrat spécifique
        target_contract = None
        for contract in contracts:
            if (contract.option_type.lower() == 'call' and 
                contract.strike == target_strike):
                target_contract = contract
                break
        
        if not target_contract:
            print(f"❌ Contrat non trouvé: {symbol} CALL {target_strike}$ exp {target_expiration}")
            print("   Strikes disponibles pour les CALL:")
            call_strikes = [c.strike for c in contracts if c.option_type.lower() == 'call']
            call_strikes.sort()
            for strike in call_strikes[:10]:  # Afficher les 10 premiers
                print(f"   - ${strike}")
            return False
        
        # Afficher les détails du contrat trouvé
        print(f"\n🎯 CONTRAT TROUVÉ: {target_contract.symbol}")
        print("=" * 60)
        
        # Informations de base
        print("📊 INFORMATIONS DE BASE:")
        print(f"   Symbole: {target_contract.symbol}")
        print(f"   Type: {target_contract.option_type.upper()}")
        print(f"   Strike: ${target_contract.strike}")
        print(f"   Expiration: {target_contract.expiration}")
        print(f"   Sous-jacent: {target_contract.underlying}")
        
        # Prix
        print("\n💰 PRIX:")
        print(f"   Dernier: ${target_contract.last:.2f}")
        print(f"   Bid: ${target_contract.bid:.2f}")
        print(f"   Ask: ${target_contract.ask:.2f}")
        print(f"   Mid: ${(target_contract.bid + target_contract.ask) / 2:.2f}")
        
        # Volume et OI
        print("\n📈 VOLUME & OPEN INTEREST:")
        print(f"   Volume: {target_contract.volume:,}")
        print(f"   Open Interest: {target_contract.open_interest:,}")
        print(f"   Vol/OI Ratio: {target_contract.volume / max(target_contract.open_interest, 1):.2f}")
        
        # Greeks - C'est ce qu'on veut comparer !
        print("\n🔬 GREEKS (données Tradier):")
        print(f"   Delta (Δ): {target_contract.delta:.6f}")
        print(f"   Gamma (Γ): {target_contract.gamma:.6f}")
        print(f"   Theta (Θ): {target_contract.theta:.6f}")
        print(f"   Vega (ν): {target_contract.vega:.6f}")
        print(f"   Rho (ρ): {target_contract.rho:.6f}")
        
        # IV
        print("\n📊 VOLATILITÉ IMPLICITE:")
        if target_contract.implied_volatility > 0:
            print(f"   IV: {target_contract.implied_volatility:.4f} ({target_contract.implied_volatility:.1f}%)")
        else:
            print("   IV: Non disponible (0)")
        
        # Métriques calculées
        print("\n📐 MÉTRIQUES CALCULÉES:")
        if target_contract.mid_price:
            print(f"   Prix médian: ${target_contract.mid_price:.2f}")
        if target_contract.spread:
            print(f"   Spread: ${target_contract.spread:.2f}")
        if target_contract.spread_percentage:
            print(f"   Spread %: {target_contract.spread_percentage:.2f}%")
        if target_contract.moneyness:
            print(f"   Moneyness: {target_contract.moneyness}")
        
        # Données brutes pour debug
        print("\n🔍 DONNÉES BRUTES (pour comparaison):")
        contract_dict = target_contract.to_dict()
        for key, value in contract_dict.items():
            if key in ['delta', 'gamma', 'theta', 'vega', 'rho', 'implied_volatility']:
                print(f"   {key}: {value}")
        
        print("\n✅ Test terminé - Comparez ces valeurs avec votre plateforme!")
        print("=" * 60)
        print("📝 RÉSUMÉ POUR COMPARAISON:")
        print(f"   Contrat: AAPL CALL ${target_contract.strike} exp {target_contract.expiration}")
        print(f"   Prix: ${target_contract.last:.2f} (Bid: ${target_contract.bid:.2f} / Ask: ${target_contract.ask:.2f})")
        print(f"   Delta: {target_contract.delta:.4f}")
        print(f"   Gamma: {target_contract.gamma:.4f}")
        print(f"   Theta: {target_contract.theta:.4f}")
        print(f"   Vega: {target_contract.vega:.4f}")
        print(f"   IV: {target_contract.implied_volatility:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ ERREUR DURANT LE TEST: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print(f"Démarrage du test à {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    success = test_specific_aapl_contract()
    if success:
        print("🎉 Test réussi!")
    else:
        print("💥 Test échoué!")