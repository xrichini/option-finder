#!/usr/bin/env python3
"""
Test pour trouver les strikes disponibles autour de 110$ pour AAPL exp 2025-09-19
"""

import os
import sys
import logging
from datetime import datetime

# Ajouter le répertoire racine au path pour importer les modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.enhanced_tradier_client import EnhancedTradierClient

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_aapl_strikes():
    """Test pour voir quels strikes sont disponibles pour AAPL"""
    
    print("=" * 80)
    print("🎯 TEST STRIKES AAPL - Expiration 2025-09-19")
    print("=" * 80)
    
    try:
        # Configuration automatique depuis Config
        client = EnhancedTradierClient(api_token="", sandbox=None)
        
        symbol = "AAPL"
        target_expiration = "2025-09-19"  # Date valide comme vous l'avez confirmé
        
        print(f"\n📡 Récupération de la chaîne d'options pour {symbol} exp {target_expiration}")
        
        contracts = client.get_options_chains(symbol, target_expiration)
        print(f"   Total contrats récupérés: {len(contracts)}")
        
        if not contracts:
            print("❌ Aucun contrat trouvé!")
            return False
        
        # Séparer calls et puts
        calls = [c for c in contracts if c.option_type.lower() == 'call']
        puts = [c for c in contracts if c.option_type.lower() == 'put']
        
        print(f"   Calls: {len(calls)}, Puts: {len(puts)}")
        
        # Lister les strikes des calls autour de 110
        call_strikes = sorted([c.strike for c in calls])
        
        print("\n💰 STRIKES DISPONIBLES POUR LES CALLS:")
        
        # Chercher les strikes autour de 110
        target_strike = 110.0
        nearby_strikes = []
        
        for strike in call_strikes:
            if abs(strike - target_strike) <= 20:  # Dans un range de ±20$
                nearby_strikes.append(strike)
        
        print(f"   Strikes proches de ${target_strike} (±20$):")
        for strike in nearby_strikes:
            call_contract = next((c for c in calls if c.strike == strike), None)
            if call_contract:
                iv_info = f"IV: {call_contract.implied_volatility:.1f}%" if call_contract.implied_volatility > 0 else "IV: N/A"
                vol_info = f"Vol: {call_contract.volume}" if call_contract.volume > 0 else "Vol: 0"
                oi_info = f"OI: {call_contract.open_interest}"
                print(f"   - ${strike} | {iv_info} | {vol_info} | {oi_info}")
        
        # Chercher le contrat le plus proche de 110$
        closest_strike = min(call_strikes, key=lambda x: abs(x - target_strike))
        print(f"\n🎯 Strike le plus proche de ${target_strike}: ${closest_strike}")
        
        # Récupérer ce contrat
        target_contract = next((c for c in calls if c.strike == closest_strike), None)
        
        if not target_contract:
            print("❌ Impossible de trouver le contrat cible!")
            return False
        
        print("\n" + "="*60)
        print(f"🔍 DÉTAILS DU CONTRAT: {target_contract.symbol}")
        print("="*60)
        
        # Informations de base
        print("📊 INFORMATIONS DE BASE:")
        print(f"   Symbole: {target_contract.symbol}")
        print(f"   Type: {target_contract.option_type.upper()}")
        print(f"   Strike: ${target_contract.strike}")
        print(f"   Expiration: {target_contract.expiration}")
        print(f"   Sous-jacent: {target_contract.underlying}")
        
        # Prix
        print("\n💰 PRIX:")
        print(f"   Dernier: ${target_contract.last:.4f}")
        print(f"   Bid: ${target_contract.bid:.4f}")
        print(f"   Ask: ${target_contract.ask:.4f}")
        if target_contract.bid > 0 and target_contract.ask > 0:
            mid = (target_contract.bid + target_contract.ask) / 2
            spread = target_contract.ask - target_contract.bid
            spread_pct = (spread / mid * 100) if mid > 0 else 0
            print(f"   Mid: ${mid:.4f}")
            print(f"   Spread: ${spread:.4f} ({spread_pct:.2f}%)")
        
        # Volume et OI
        print("\n📈 VOLUME & OPEN INTEREST:")
        print(f"   Volume: {target_contract.volume:,}")
        print(f"   Open Interest: {target_contract.open_interest:,}")
        if target_contract.open_interest > 0:
            vol_oi_ratio = target_contract.volume / target_contract.open_interest
            print(f"   Vol/OI Ratio: {vol_oi_ratio:.3f}")
        
        # Greeks - C'est ce qu'on veut valider !
        print("\n🔬 GREEKS (depuis API Tradier):")
        print(f"   Delta (Δ): {target_contract.delta:.6f}")
        print(f"   Gamma (Γ): {target_contract.gamma:.6f}")
        print(f"   Theta (Θ): {target_contract.theta:.6f}")
        print(f"   Vega (ν): {target_contract.vega:.6f}")
        print(f"   Rho (ρ): {target_contract.rho:.6f}")
        
        # IV - Point crucial !
        print("\n📊 VOLATILITÉ IMPLICITE:")
        if target_contract.implied_volatility > 0:
            print(f"   🎯 IV: {target_contract.implied_volatility:.4f} ({target_contract.implied_volatility:.2f}%)")
        else:
            print(f"   ❌ IV: Non disponible (valeur: {target_contract.implied_volatility})")
        
        # Comparer avec d'autres contrats qui ont une IV
        print("\n📈 COMPARAISON AVEC D'AUTRES CONTRATS:")
        iv_contracts = [c for c in calls if c.implied_volatility > 0]
        
        if iv_contracts:
            print(f"   Contrats CALL avec IV > 0: {len(iv_contracts)} / {len(calls)}")
            print("   Exemples de contrats avec IV:")
            
            for i, contract in enumerate(iv_contracts[:5]):  # 5 premiers
                print(f"   {i+1}. ${contract.strike} | IV: {contract.implied_volatility:.2f}% | Vol: {contract.volume} | OI: {contract.open_interest}")
        else:
            print("   ❌ Aucun contrat CALL n'a d'IV disponible!")
        
        print("\n" + "="*80)
        print("📝 RÉSUMÉ POUR COMPARAISON AVEC VOTRE PLATEFORME:")
        print(f"   Contrat testé: {target_contract.symbol}")
        print(f"   Strike: ${target_contract.strike}")
        print(f"   Expiration: {target_contract.expiration}")
        print(f"   Prix: Bid ${target_contract.bid:.4f} / Ask ${target_contract.ask:.4f}")
        print(f"   Delta: {target_contract.delta:.4f}")
        print(f"   Gamma: {target_contract.gamma:.6f}")
        print(f"   Theta: {target_contract.theta:.4f}")
        print(f"   Vega: {target_contract.vega:.4f}")
        print(f"   IV: {target_contract.implied_volatility:.2f}%" if target_contract.implied_volatility > 0 else "   IV: Non disponible")
        
        return True
        
    except Exception as e:
        print(f"❌ ERREUR DURANT LE TEST: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print(f"Démarrage du test à {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    success = test_aapl_strikes()
    if success:
        print("🎉 Test réussi!")
    else:
        print("💥 Test échoué!")