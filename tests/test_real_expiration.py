#!/usr/bin/env python3
"""
Test corrigé pour vérifier les vraies dates d'expiration disponibles et tester un contrat réel
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

def test_real_aapl_contract():
    """Test avec de vraies dates d'expiration disponibles"""
    
    print("=" * 80)
    print("🎯 TEST CORRIGÉ: AAPL avec vraies dates d'expiration")
    print("=" * 80)
    
    try:
        # Configuration automatique depuis Config
        client = EnhancedTradierClient(api_token="", sandbox=None)
        
        print(f"Environment: {'Sandbox' if client.sandbox else 'Production'}")
        print(f"Base URL: {client.base_url}")
        
        symbol = "AAPL"
        
        print(f"\n🔍 Étape 1: Récupération des dates d'expiration pour {symbol}")
        
        # D'abord, récupérer les dates d'expiration disponibles
        url = f"{client.base_url}/markets/options/expirations"
        params = {
            'symbol': symbol,
            'includeAllRoots': 'true',
            'strikes': 'false'
        }
        
        response = client.session.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        expirations = []
        if 'expirations' in data and 'date' in data['expirations']:
            dates = data['expirations']['date']
            if isinstance(dates, list):
                expirations = dates
            else:
                expirations = [dates]
        
        print(f"   Dates d'expiration disponibles: {len(expirations)}")
        for i, exp_date in enumerate(expirations[:10]):  # Afficher les 10 premières
            print(f"   {i+1}. {exp_date}")
        
        if not expirations:
            print("❌ Aucune date d'expiration trouvée!")
            return False
        
        # Prendre une date d'expiration proche mais pas trop proche
        target_expiration = None
        today = datetime.now()
        
        for exp_date in expirations:
            try:
                exp_datetime = datetime.strptime(exp_date, '%Y-%m-%d')
                days_to_exp = (exp_datetime - today).days
                # Chercher une expiration entre 30 et 90 jours
                if 30 <= days_to_exp <= 90:
                    target_expiration = exp_date
                    break
            except:
                continue
        
        if not target_expiration:
            # Si pas trouvé, prendre la première disponible après aujourd'hui
            for exp_date in expirations:
                try:
                    exp_datetime = datetime.strptime(exp_date, '%Y-%m-%d')
                    if exp_datetime > today:
                        target_expiration = exp_date
                        break
                except:
                    continue
        
        if not target_expiration:
            print("❌ Aucune date d'expiration future trouvée!")
            return False
        
        exp_datetime = datetime.strptime(target_expiration, '%Y-%m-%d')
        days_to_exp = (exp_datetime - today).days
        
        print(f"\n📅 Date d'expiration sélectionnée: {target_expiration} ({days_to_exp} jours)")
        
        # Maintenant récupérer la chaîne d'options pour cette date
        print(f"\n🔍 Étape 2: Récupération de la chaîne d'options pour {target_expiration}")
        
        contracts = client.get_options_chains(symbol, target_expiration)
        print(f"   Contrats récupérés: {len(contracts)}")
        
        if not contracts:
            print("❌ Aucun contrat trouvé!")
            return False
        
        # Séparer les calls et puts et trouver des contrats ATM ou proches
        calls = [c for c in contracts if c.option_type.lower() == 'call']
        puts = [c for c in contracts if c.option_type.lower() == 'put']
        
        print(f"   Calls: {len(calls)}, Puts: {len(puts)}")
        
        # Trouver des contrats intéressants (avec volume et/ou IV)
        interesting_contracts = []
        
        for contract in contracts[:20]:  # Examiner les 20 premiers
            if (contract.volume > 0 or contract.open_interest > 50 or 
                contract.implied_volatility > 0):
                interesting_contracts.append(contract)
        
        print(f"\n📊 Contrats intéressants trouvés: {len(interesting_contracts)}")
        
        # Afficher les détails des 3 premiers contrats intéressants
        for i, contract in enumerate(interesting_contracts[:3]):
            print("\n" + "="*60)
            print(f"🎯 CONTRAT #{i+1}: {contract.symbol}")
            print("="*60)
            
            # Informations de base
            print("📊 INFORMATIONS DE BASE:")
            print(f"   Symbole: {contract.symbol}")
            print(f"   Type: {contract.option_type.upper()}")
            print(f"   Strike: ${contract.strike}")
            print(f"   Expiration: {contract.expiration}")
            print(f"   Sous-jacent: {contract.underlying}")
            
            # Prix
            print("\n💰 PRIX:")
            print(f"   Dernier: ${contract.last:.2f}")
            print(f"   Bid: ${contract.bid:.2f}")
            print(f"   Ask: ${contract.ask:.2f}")
            if contract.bid > 0 and contract.ask > 0:
                mid = (contract.bid + contract.ask) / 2
                spread = contract.ask - contract.bid
                spread_pct = (spread / mid * 100) if mid > 0 else 0
                print(f"   Mid: ${mid:.2f}")
                print(f"   Spread: ${spread:.2f} ({spread_pct:.1f}%)")
            
            # Volume et OI
            print("\n📈 VOLUME & OPEN INTEREST:")
            print(f"   Volume: {contract.volume:,}")
            print(f"   Open Interest: {contract.open_interest:,}")
            if contract.open_interest > 0:
                vol_oi_ratio = contract.volume / contract.open_interest
                print(f"   Vol/OI Ratio: {vol_oi_ratio:.2f}")
            
            # Greeks
            print("\n🔬 GREEKS:")
            print(f"   Delta (Δ): {contract.delta:.6f}")
            print(f"   Gamma (Γ): {contract.gamma:.6f}")
            print(f"   Theta (Θ): {contract.theta:.6f}")
            print(f"   Vega (ν): {contract.vega:.6f}")
            print(f"   Rho (ρ): {contract.rho:.6f}")
            
            # IV - point clé !
            print("\n📊 VOLATILITÉ IMPLICITE:")
            if contract.implied_volatility > 0:
                print(f"   🎯 IV: {contract.implied_volatility:.4f} ({contract.implied_volatility:.1f}%)")
            else:
                print("   ❌ IV: Non disponible (0)")
            
            # Moneyness
            if hasattr(contract, 'moneyness') and contract.moneyness:
                print(f"\n📐 MONEYNESS: {contract.moneyness}")
        
        print("\n" + "="*80)
        print("✅ RÉSUMÉ DU TEST:")
        print(f"   Symbole: {symbol}")
        print(f"   Expiration: {target_expiration} ({days_to_exp} jours)")
        print(f"   Total contrats: {len(contracts)}")
        print(f"   Contrats intéressants: {len(interesting_contracts)}")
        
        # Compter combien ont une IV
        iv_contracts = [c for c in contracts if c.implied_volatility > 0]
        print(f"   Contrats avec IV > 0: {len(iv_contracts)} / {len(contracts)} ({len(iv_contracts)/len(contracts)*100:.1f}%)")
        
        return True
        
    except Exception as e:
        print(f"❌ ERREUR DURANT LE TEST: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print(f"Démarrage du test à {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    success = test_real_aapl_contract()
    if success:
        print("🎉 Test réussi!")
    else:
        print("💥 Test échoué!")